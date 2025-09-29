import yaml
from pydantic import ValidationError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from importlib import import_module
from typing import List
from apscheduler.jobstores.base import JobLookupError

from core import database
from modules.scheduler import models, schemas, scheduler_instance
from util import logger_util


logger = logger_util.get_logger(__name__)

def load_and_validate_jobs(config_path: str) -> List[schemas.JobConfig]:
    try:
        with open(config_path, 'r') as f:
            raw_configs = yaml.safe_load(f) or []
        return [schemas.JobConfig.model_validate(c) for c in raw_configs]
    except (FileNotFoundError, yaml.YAMLError, ValidationError) as e:
        logger.error(f"Error loading jobs from {config_path}: {e}")
        return []

def _resolve_func_path(func_path: str):
    if ':' in func_path:
        module_path, func_name = func_path.rsplit(':', 1)
    else:
        module_path, func_name = func_path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, func_name)

def apply_job_config(scheduler, job_configs):
    new_ids = {job.id for job in job_configs}
    for job in scheduler.get_jobs():
        if job.id not in new_ids:
            scheduler.remove_job(job.id)
            logger.info(f"Removed job: {job.id}")

    COMMAND_JOB_TYPES = ['cmd', 'powershell', 'shell']

    for cfg in job_configs:
        try:
            trigger_dict = cfg.trigger.model_dump()
            trigger_type = trigger_dict.pop('type')

            job_args = []  # All args are passed via kwargs to wrappers
            job_kwargs = cfg.kwargs.copy()
            job_kwargs['job_id'] = cfg.id

            if cfg.job_type == 'python':
                wrapper_path = 'modules.scheduler.job_executors:execute_python_job'
                job_function = _resolve_func_path(wrapper_path)
                job_kwargs['target_func_path'] = cfg.func
                job_kwargs['target_args'] = cfg.args
                job_kwargs['target_kwargs'] = cfg.kwargs
            
            elif cfg.job_type in COMMAND_JOB_TYPES:
                wrapper_path = 'modules.scheduler.job_executors:execute_command_job'
                job_function = _resolve_func_path(wrapper_path)
                if 'command' not in job_kwargs:
                    job_kwargs['command'] = cfg.func.split()
                job_kwargs['job_type'] = cfg.job_type
                job_kwargs['cwd'] = cfg.cwd
                job_kwargs['env'] = cfg.env

            else:
                logger.error(f"Unknown job type '{cfg.job_type}' for job {cfg.id}")
                continue

            scheduler.add_job(
                func=job_function,
                trigger=trigger_type,
                args=job_args,
                kwargs=job_kwargs,
                id=cfg.id,
                replace_existing=True,
                max_instances=cfg.max_instances,
                coalesce=cfg.coalesce,
                misfire_grace_time=cfg.misfire_grace_time,
                **trigger_dict
            )
            if not cfg.is_enabled:
                scheduler.pause_job(cfg.id)
        except Exception as e:
            logger.error(f"Error applying job {cfg.id}: {e}", exc_info=True)

class ConfigChangeHandler(PatternMatchingEventHandler):
    def __init__(self, scheduler, path):
        super().__init__(patterns=[path])
        self.scheduler = scheduler
        self.path = path
    def on_modified(self, event):
        logger.info(f"Reloading jobs from {self.path}...")
        configs = load_and_validate_jobs(self.path)
        apply_job_config(self.scheduler, configs)

def start_config_watcher(scheduler, path):
    observer = Observer()
    observer.schedule(ConfigChangeHandler(scheduler, path), '.', recursive=False)
    observer.start()
    return observer

def sync_jobs_from_db():
    logger.info("Syncing jobs from database...")
    db = next(database.get_db())
    try:
        jobs_in_db = db.query(models.JobDefinition).all()
        job_configs = [schemas.JobConfig.model_validate(j) for j in jobs_in_db]
        apply_job_config(scheduler_instance.scheduler, job_configs)
    finally:
        db.close()

def seed_db_from_yaml(yaml_path: str):
    logger.info(f"Seeding database from {yaml_path}...")
    configs = load_and_validate_jobs(yaml_path)
    db = next(database.get_db())
    try:
        for cfg in configs:
            trigger_dict = cfg.trigger.model_dump()
            job_def = models.JobDefinition(
                id=cfg.id, func=cfg.func, description=cfg.description,
                is_enabled=cfg.is_enabled, job_type=cfg.job_type, trigger_type=trigger_dict.pop('type'),
                trigger_config=trigger_dict, args=cfg.args, kwargs=cfg.kwargs, cwd=cfg.cwd, env=cfg.env,
                max_instances=cfg.max_instances, coalesce=cfg.coalesce,
                misfire_grace_time=cfg.misfire_grace_time
            )
            db.merge(job_def)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"DB seeding error: {e}")
    finally:
        db.close()

def schedule_workflow(workflow: models.Workflow):
    """
    Schedules a workflow as a single job in APScheduler.
    The job will call the run_workflow executor.
    """
    job_id = f"workflow_{workflow.id}"

    if not workflow.is_enabled or not workflow.schedule:
        # If disabled or has no schedule, ensure it's not in the scheduler
        try:
            scheduler_instance.scheduler.remove_job(job_id)
        except JobLookupError:
            pass # It's fine if it doesn't exist
        return

    try:
        cron_parts = workflow.schedule.split()
        if len(cron_parts) != 5:
            raise ValueError("Invalid cron string format. Expected 5 parts.")
        
        minute, hour, day, month, day_of_week = cron_parts
        
        scheduler_instance.scheduler.add_job(
            'modules.scheduler.job_executors:run_workflow',
            trigger='cron',
            args=[workflow.id],
            id=job_id,
            replace_existing=True,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            misfire_grace_time=3600,
            max_instances=1,
        )
        logger.info(f"Scheduled workflow '{workflow.name}' with job ID '{job_id}'.")
    except Exception as e:
        logger.error(f"Failed to schedule workflow '{workflow.name}': {e}", exc_info=True)

def sync_workflows_from_db():
    """
    Loads all enabled workflows from the database and schedules them.
    """
    logger.info("Syncing workflows from database...")
    db = next(database.get_db())
    try:
        workflows = db.query(models.Workflow).filter(models.Workflow.is_enabled == True).all()
        for wf in workflows:
            schedule_workflow(wf)
    finally:
        db.close()

def remove_workflow_job(workflow_id: int):
    """Removes a workflow job from the scheduler."""
    job_id = f"workflow_{workflow_id}"
    try:
        scheduler_instance.scheduler.remove_job(job_id)
        logger.info(f"Removed scheduled job for workflow {workflow_id}.")
    except JobLookupError:
        pass # It's fine if it doesn't exist
