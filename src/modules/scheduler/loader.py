import yaml
from pydantic import ValidationError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from typing import List
from apscheduler.jobstores.base import JobLookupError

from core import database
from modules.scheduler import models, schemas, scheduler_instance, service
from util import logger_util
from util.config_util import config

logger = logger_util.get_logger(__name__)

def apply_job_config(scheduler, job_configs: List[schemas.Job]):
    """
    Applies a list of job configurations to the scheduler, adding, updating,
    and removing jobs as necessary.
    """
    logger.info(f"Applying {len(job_configs)} job configs to the scheduler.")
    new_ids = {job.id for job in job_configs}
    
    if config.delete_orphaned_jobs_on_sync:
        for job in scheduler.get_jobs():
            if job.id not in new_ids and not job.id.startswith('workflow_'):
                scheduler.remove_job(job.id)
                logger.info(f"Removed orphaned job from scheduler: {job.id}")

    for cfg in job_configs:
        try:
            trigger_dict = cfg.trigger.model_dump()
            trigger_type = trigger_dict.pop('type')

            # The executor's kwargs now just contain the job_id and the specific params model.
            job_kwargs = {
                'job_id': cfg.id,
                'task_params': cfg.task_parameters.model_dump()
            }
            
            task_type = cfg.task_parameters.task_type
            
            if task_type == 'python':
                wrapper_path = 'modules.scheduler.job_executors:execute_python_job'
            elif task_type == 'shell':
                wrapper_path = 'modules.scheduler.job_executors:execute_shell_job'
            elif task_type == 'email':
                wrapper_path = 'modules.scheduler.job_executors:execute_email_job'
            else:
                logger.error(f"Unknown task type '{task_type}' for job {cfg.id}")
                continue

            scheduler.add_job(
                func=wrapper_path,
                trigger=trigger_type,
                kwargs=job_kwargs,
                id=cfg.id,
                name=cfg.name,
                replace_existing=True,
                max_instances=cfg.max_instances,
                coalesce=cfg.coalesce,
                misfire_grace_time=cfg.misfire_grace_time,
                **trigger_dict
            )
            
            if not cfg.is_enabled:
                scheduler.pause_job(cfg.id)
            else:
                # Ensure paused jobs in DB are resumed if they are now enabled
                existing_job = scheduler.get_job(cfg.id)
                if existing_job and existing_job.next_run_time is None:
                    scheduler.resume_job(cfg.id)

        except Exception as e:
            logger.error(f"Error applying job config for '{cfg.id}': {e}", exc_info=True)

def sync_jobs_from_db():
    """
    Loads all job definitions from the database and applies them to the scheduler.
    """
    logger.info("Syncing jobs from database to scheduler...")
    db = next(database.get_db())
    try:
        jobs_in_db = db.query(models.JobDefinition).all()
        # The model_validator in schemas.Job handles the conversion
        job_configs = [schemas.Job.model_validate(j) for j in jobs_in_db]
        apply_job_config(scheduler_instance.scheduler, job_configs)
        logger.info(f"Successfully synced {len(job_configs)} jobs from DB.")
    except Exception as e:
        logger.error(f"Failed to sync jobs from database: {e}", exc_info=True)
    finally:
        db.close()

def seed_db_from_yaml(yaml_path: str):
    """
    Seeds the database from a YAML file.
    """
    logger.info(f"Seeding database from YAML file: {yaml_path}")
    db = next(database.get_db())
    try:
        with open(yaml_path, 'r') as f:
            job_configs = yaml.safe_load(f)

        if not job_configs:
            logger.info("YAML file is empty. No jobs to seed.")
            return

        logger.info(f"Found {len(job_configs)} jobs in YAML file.") # DEBUG

        for job_data in job_configs:
            try:
                logger.info(f"Processing job: {job_data.get('id')}") # DEBUG
                # Transform old format to new JobCreate schema
                if 'func' in job_data and job_data.get('job_type') == 'python':
                    module, function = job_data['func'].rsplit('.', 1)
                    task_params = schemas.PythonJobParams(
                        task_type='python',
                        module=module,
                        function=function,
                        args=job_data.get('args', []),
                        kwargs=job_data.get('kwargs', {})
                    )
                # Add other transformations for shell, email, etc. if needed
                else:
                    logger.warning(f"Skipping job with unsupported format in YAML: {job_data.get('id')}")
                    continue

                job_in = schemas.JobCreate(
                    id=job_data.get('id'),
                    name=job_data.get('id'),  # Use id as name
                    description=job_data.get('description'),
                    is_enabled=job_data.get('is_enabled', True),
                    trigger=job_data.get('trigger'),
                    task_parameters=task_params,
                    max_instances=job_data.get('max_instances', 3),
                    coalesce=job_data.get('coalesce', False),
                    misfire_grace_time=job_data.get('misfire_grace_time', 3600)
                )

                existing_job = service.job_definition_service.get(db, id=job_data['id'])
                if existing_job:
                    if job_data.get('replace_existing', False):
                        logger.info(f"Updating job from YAML: {job_in.name}")
                        job_update_data = job_in.model_dump(exclude_unset=True, exclude={'id'})
                        job_update = schemas.JobUpdate(**job_update_data)
                        service.update_job_from_schema(db, db_obj=existing_job, job_in=job_update)
                    else:
                        logger.info(f"Skipping existing job from YAML: {job_in.name}")
                else:
                    logger.info(f"Creating new job from YAML: {job_in.name}")
                    service.create_job_from_schema(db, job_in=job_in)

            except (ValidationError, KeyError, AttributeError) as e:
                logger.error(f"Error processing job config from YAML: {job_data.get('id')}. Details: {e}", exc_info=True)

    except FileNotFoundError:
        logger.error(f"YAML file not found at {yaml_path}")
    except Exception as e:
        logger.error(f"Failed to seed database from YAML: {e}", exc_info=True)
    finally:
        db.close()

class ConfigChangeHandler(PatternMatchingEventHandler):
    def __init__(self, scheduler, path):
        super().__init__(patterns=[path])
        self.scheduler = scheduler
        self.path = path
    def on_modified(self, event):
        logger.info(f"YAML file {self.path} was modified, but auto-reloading from YAML is disabled. Syncing from DB instead.")
        sync_jobs_from_db()

def start_config_watcher(scheduler, path):
    observer = Observer()
    observer.schedule(ConfigChangeHandler(scheduler, path), '.', recursive=False)
    observer.start()
    return observer

def schedule_workflow(workflow: models.Workflow):
    """
    Schedules a workflow as a single job in APScheduler.
    The job will call the run_workflow executor.
    """
    logger.info(f"Attempting to schedule workflow '{workflow.name}' (ID: {workflow.id}).")
    job_id = f"workflow_{workflow.id}"

    if not workflow.is_enabled or not workflow.schedule:
        logger.warning(f"Workflow '{workflow.name}' is disabled or has no schedule. Removing from scheduler if present.")
        try:
            scheduler_instance.scheduler.remove_job(job_id)
        except JobLookupError:
            pass 
        return

    try:
        logger.info(f"Parsing schedule for workflow '{workflow.name}': '{workflow.schedule}'")
        cron_parts = workflow.schedule.split()
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron string format for workflow '{workflow.name}'. Expected 5 parts, got {len(cron_parts)}.")
            return

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
            jobstore='default'
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