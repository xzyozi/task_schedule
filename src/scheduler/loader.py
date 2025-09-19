import yaml
from pydantic import ValidationError
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from importlib import import_module
from typing import List

import scheduler.database as database
from .models import JobDefinition, JobConfig
from .scheduler import scheduler # Import scheduler here to avoid circular dependency issues at module load time
from util import logger


def load_and_validate_jobs(config_path: str) -> List[JobConfig]:
    """YAMLファイルを読み込み、Pydanticモデルでバリデーションする"""
    try:
        with open(config_path, 'r') as f:
            raw_configs = yaml.safe_load(f)
        
        if raw_configs is None: # Handle empty YAML file
            logger.warning(f"YAML file {config_path} is empty. No jobs to load.")
            return []

        validated_jobs = [JobConfig.model_validate(config) for config in raw_configs]
        return validated_jobs
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return []
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        return []
    except ValidationError as e:
        logger.error(f"Configuration validation error: {e}")
        return []

def _resolve_func_path(func_path: str):
    """Resolves a string function path to a callable function object."""
    try:
        module_path, func_name = func_path.rsplit('.', 1)
        module = import_module(module_path)
        func_obj = getattr(module, func_name)
        return func_obj
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to resolve function path {func_path}: {e}")
        raise

def apply_job_config(scheduler_instance, job_configs):
    """設定ファイルからジョブをスケジューラに適用する"""
    if not job_configs:
        logger.warning("No valid job configurations to apply.")
        return

    new_job_ids = {job.id for job in job_configs}
    current_job_ids = {job.id for job in scheduler_instance.get_jobs()}

    # 削除されるべきジョブを特定して削除
    jobs_to_remove = current_job_ids - new_job_ids
    for job_id in jobs_to_remove:
        try:
            scheduler_instance.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")

    # 新規追加または更新されるべきジョブを適用
    for job_config in job_configs:
        try:
            trigger_dict = job_config.trigger.dict()
            trigger_type = trigger_dict.pop('type')
            
            func_obj = _resolve_func_path(job_config.func)

            # Inject job_id into kwargs for the task function
            final_kwargs = job_config.kwargs.copy()
            final_kwargs['job_id'] = job_config.id

            scheduler_instance.add_job(
                func=func_obj,
                trigger=trigger_type,
                args=job_config.args,
                kwargs=final_kwargs,
                id=job_config.id,
                replace_existing=job_config.replace_existing,
                max_instances=job_config.max_instances,
                coalesce=job_config.coalesce,
                misfire_grace_time=job_config.misfire_grace_time,
                **trigger_dict
            )
            logger.info(f"Added/Updated job: {job_config.id}")
        except Exception as e:
                logger.error(f"Error adding/updating job {job_config.id}: {e}")


class ConfigChangeHandler(PatternMatchingEventHandler):
    def __init__(self, scheduler_instance, config_path):
        super().__init__(patterns=[config_path], ignore_directories=True)
        self.scheduler = scheduler_instance
        self.config_path = config_path

    def on_modified(self, event):
        logger.info(f"Configuration file {event.src_path} has been modified. Reloading jobs...")
        # ファイルの読み込みとバリデーション
        job_configs = load_and_validate_jobs(self.config_path)
        if job_configs is not None:
            # スケジューラに設定を適用
            apply_job_config(self.scheduler, job_configs)

def start_config_watcher(scheduler_instance, config_path):
    """設定ファイルの監視を開始する"""
    event_handler = ConfigChangeHandler(scheduler_instance, config_path)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    logger.info(f"Started watching {config_path} for changes.")
    return observer


def sync_jobs_from_db():
    """Synchronizes jobs from the database with the scheduler."""
    # Import scheduler here to avoid circular dependency issues at module load time
    from .scheduler import scheduler 

    logger.info("Syncing jobs from database...")
    db = database.SessionLocal()
    try:
        # 1. Get the desired state from the database
        jobs_in_db = db.query(JobDefinition).all()
        desired_job_ids = {job.id for job in jobs_in_db}

        # 2. Get the current state from the scheduler
        scheduled_jobs = scheduler.get_jobs()
        scheduled_job_ids = {job.id for job in scheduled_jobs}

        # 3. Remove jobs that are in the scheduler but not in the database
        jobs_to_remove = desired_job_ids.difference(scheduled_job_ids)
        for job_id in jobs_to_remove:
            try:
                scheduler.remove_job(job_id)
                logger.info(f"Removed job '{job_id}' as it is no longer in the database.")
            except Exception as e:
                logger.error(f"Error removing job '{job_id}': {e}")

        # 4. Add or update jobs that are in the database
        for job_def in jobs_in_db:
            try:
                # Inject job_id into kwargs for the task function
                final_kwargs = job_def.kwargs.copy()
                final_kwargs['job_id'] = job_def.id

                scheduler.add_job(
                    func=job_def.func,
                    trigger=job_def.trigger_type,
                    args=job_def.args,
                    kwargs=final_kwargs,
                    id=job_def.id,
                    replace_existing=True,  # This handles both add and update
                    max_instances=job_def.max_instances,
                    coalesce=job_def.coalesce,
                    misfire_grace_time=job_def.misfire_grace_time,
                    **job_def.trigger_config,
                )
                logger.info(f"Successfully added/updated job: {job_def.id}")
            except Exception as e:
                logger.error(f"Failed to add/update job {job_def.id}: {e}")
        
        logger.info("Job synchronization complete.")

    finally:
        db.close()


def seed_db_from_yaml(yaml_path: str):
    """Seeds the database with job definitions from a YAML file."""
    logger.info(f"Seeding database from {yaml_path}...")
    
    try:
        with open(yaml_path, 'r') as f:
            raw_configs = yaml.safe_load(f)
            if not raw_configs:
                logger.warning(f"YAML file {yaml_path} is empty. No jobs to seed.")
                return
    except FileNotFoundError:
        logger.error(f"YAML file not found: {yaml_path}")
        return
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        return

    validated_jobs = []
    for raw_config in raw_configs:
        try:
            validated_jobs.append(JobConfig.model_validate(raw_config))
        except ValidationError as e:
            job_id = raw_config.get('id', 'unknown')
            logger.error(f"Validation failed for job '{job_id}' in {yaml_path}: {e}")
            continue
    
    if not validated_jobs:
        logger.error("No valid jobs found in YAML file after validation.")
        return

    db = database.SessionLocal()
    try:
        for job_config in validated_jobs:
            # Map the Pydantic object to the SQLAlchemy model
            trigger_config = job_config.trigger.copy()
            trigger_type = trigger_config.pop('type')

            job_definition = JobDefinition(
                id=job_config.id,
                func=job_config.func,
                description=job_config.description,
                is_enabled=job_config.is_enabled,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
                args=job_config.args,
                kwargs=job_config.kwargs,
                max_instances=job_config.max_instances,
                coalesce=job_config.coalesce,
                misfire_grace_time=job_config.misfire_grace_time,
            )
            # Use merge to perform an "upsert" (insert or update)
            db.merge(job_definition)
            logger.info(f"Merging job definition '{job_config.id}' into database.")

        db.commit()
        logger.info(f"Database seeding complete. {len(validated_jobs)} jobs merged.")
    except Exception as e:
        logger.error(f"An error occurred during database seeding: {e}")
        db.rollback()
    finally:
        db.close()