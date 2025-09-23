import yaml
from pydantic import ValidationError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from importlib import import_module
from typing import List

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
    module_path, func_name = func_path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, func_name)

def apply_job_config(scheduler, job_configs):
    new_ids = {job.id for job in job_configs}
    for job in scheduler.get_jobs():
        if job.id not in new_ids:
            scheduler.remove_job(job.id)
            logger.info(f"Removed job: {job.id}")
    for cfg in job_configs:
        try:
            trigger_dict = cfg.trigger.dict()
            trigger_type = trigger_dict.pop('type')
            final_kwargs = cfg.kwargs.copy()
            final_kwargs['job_id'] = cfg.id
            scheduler.add_job(
                func=_resolve_func_path(cfg.func),
                trigger=trigger_type,
                args=cfg.args, kwargs=final_kwargs, id=cfg.id,
                replace_existing=True, max_instances=cfg.max_instances,
                coalesce=cfg.coalesce, misfire_grace_time=cfg.misfire_grace_time,
                **trigger_dict
            )
            if not cfg.is_enabled:
                scheduler.pause_job(cfg.id)
        except Exception as e:
            logger.error(f"Error applying job {cfg.id}: {e}")

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
        apply_job_config(scheduler_instance.scheduler, [schemas.JobConfig.model_validate(j) for j in jobs_in_db])
    finally:
        db.close()

def seed_db_from_yaml(yaml_path: str):
    logger.info(f"Seeding database from {yaml_path}...")
    configs = load_and_validate_jobs(yaml_path)
    db = next(database.get_db())
    try:
        for cfg in configs:
            trigger_dict = cfg.trigger.dict()
            job_def = models.JobDefinition(
                id=cfg.id, func=cfg.func, description=cfg.description,
                is_enabled=cfg.is_enabled, trigger_type=trigger_dict.pop('type'),
                trigger_config=trigger_dict, args=cfg.args, kwargs=cfg.kwargs,
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
