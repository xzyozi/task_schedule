import logging
import yaml

from pydantic import ValidationError

import logging
import yaml

from pydantic import ValidationError

from scheduler.database import engine, SessionLocal # Changed import
from .models import JobDefinition, JobConfig


def sync_jobs_from_db():
    """Synchronizes jobs from the database with the scheduler."""
    # Import scheduler here to avoid circular dependency issues at module load time
    from .scheduler import scheduler 

    logging.info("Syncing jobs from database...")
    db = SessionLocal()
    try:
        # 1. Get the desired state from the database
        jobs_in_db = db.query(JobDefinition).all()
        desired_job_ids = {job.id for job in jobs_in_db}

        # 2. Get the current state from the scheduler
        scheduled_jobs = scheduler.get_jobs()
        scheduled_job_ids = {job.id for job in scheduled_jobs}

        # 3. Remove jobs that are in the scheduler but not in the database
        jobs_to_remove = scheduled_job_ids - desired_job_ids
        for job_id in jobs_to_remove:
            try:
                scheduler.remove_job(job_id)
                logging.info(f"Removed job '{job_id}' as it is no longer in the database.")
            except Exception as e:
                logging.error(f"Error removing job '{job_id}': {e}")

        # 4. Add or update jobs that are in the database
        for job_def in jobs_in_db:
            try:
                scheduler.add_job(
                    func=job_def.func,
                    trigger=job_def.trigger_type,
                    args=job_def.args,
                    kwargs=job_def.kwargs,
                    id=job_def.id,
                    replace_existing=True,  # This handles both add and update
                    max_instances=job_def.max_instances,
                    coalesce=job_def.coalesce,
                    misfire_grace_time=job_def.misfire_grace_time,
                    **job_def.trigger_config,
                )
                logging.info(f"Successfully added/updated job: {job_def.id}")
            except Exception as e:
                logging.error(f"Failed to add/update job {job_def.id}: {e}")
        
        logging.info("Job synchronization complete.")

    finally:
        db.close()


def seed_db_from_yaml(yaml_path: str):
    """Seeds the database with job definitions from a YAML file."""
    logging.info(f"Seeding database from {yaml_path}...")
    
    try:
        with open(yaml_path, 'r') as f:
            raw_configs = yaml.safe_load(f)
            if not raw_configs:
                logging.warning(f"YAML file {yaml_path} is empty. No jobs to seed.")
                return
    except FileNotFoundError:
        logging.error(f"YAML file not found: {yaml_path}")
        return
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
        return

    validated_jobs = []
    for raw_config in raw_configs:
        try:
            validated_jobs.append(JobConfig.model_validate(raw_config))
        except ValidationError as e:
            job_id = raw_config.get('id', 'unknown')
            logging.error(f"Validation failed for job '{job_id}' in {yaml_path}: {e}")
            continue
    
    if not validated_jobs:
        logging.error("No valid jobs found in YAML file after validation.")
        return

    db = SessionLocal()
    try:
        for job_config in validated_jobs:
            # Map the Pydantic object to the SQLAlchemy model
            trigger_config = job_config.trigger.copy()
            trigger_type = trigger_config.pop('type')

            job_definition = JobDefinition(
                id=job_config.id,
                func=job_config.func,
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
            logging.info(f"Merging job definition '{job_config.id}' into database.")

        db.commit()
        logging.info(f"Database seeding complete. {len(validated_jobs)} jobs merged.")
    except Exception as e:
        logging.error(f"An error occurred during database seeding: {e}")
        db.rollback()
    finally:
        db.close()

from .models import JobDefinition, JobConfig

# Create a configured "Session" class # Removed
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Removed

def sync_jobs_from_db():
    """Synchronizes jobs from the database with the scheduler."""
    # Import scheduler here to avoid circular dependency issues at module load time
    from .scheduler import scheduler 

    logging.info("Syncing jobs from database...")
    db = SessionLocal()
    try:
        # 1. Get the desired state from the database
        jobs_in_db = db.query(JobDefinition).all()
        desired_job_ids = {job.id for job in jobs_in_db}

        # 2. Get the current state from the scheduler
        scheduled_jobs = scheduler.get_jobs()
        scheduled_job_ids = {job.id for job in scheduled_jobs}

        # 3. Remove jobs that are in the scheduler but not in the database
        jobs_to_remove = scheduled_job_ids - desired_job_ids
        for job_id in jobs_to_remove:
            try:
                scheduler.remove_job(job_id)
                logging.info(f"Removed job '{job_id}' as it is no longer in the database.")
            except Exception as e:
                logging.error(f"Error removing job '{job_id}': {e}")

        # 4. Add or update jobs that are in the database
        for job_def in jobs_in_db:
            try:
                scheduler.add_job(
                    func=job_def.func,
                    trigger=job_def.trigger_type,
                    args=job_def.args,
                    kwargs=job_def.kwargs,
                    id=job_def.id,
                    replace_existing=True,  # This handles both add and update
                    max_instances=job_def.max_instances,
                    coalesce=job_def.coalesce,
                    misfire_grace_time=job_def.misfire_grace_time,
                    **job_def.trigger_config,
                )
                logging.info(f"Successfully added/updated job: {job_def.id}")
            except Exception as e:
                logging.error(f"Failed to add/update job {job_def.id}: {e}")
        
        logging.info("Job synchronization complete.")

    finally:
        db.close()


def seed_db_from_yaml(yaml_path: str):
    """Seeds the database with job definitions from a YAML file."""
    logging.info(f"Seeding database from {yaml_path}...")
    
    try:
        with open(yaml_path, 'r') as f:
            raw_configs = yaml.safe_load(f)
            if not raw_configs:
                logging.warning(f"YAML file {yaml_path} is empty. No jobs to seed.")
                return
    except FileNotFoundError:
        logging.error(f"YAML file not found: {yaml_path}")
        return
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
        return

    validated_jobs = []
    for raw_config in raw_configs:
        try:
            validated_jobs.append(JobConfig.model_validate(raw_config))
        except ValidationError as e:
            job_id = raw_config.get('id', 'unknown')
            logging.error(f"Validation failed for job '{job_id}' in {yaml_path}: {e}")
            continue
    
    if not validated_jobs:
        logging.error("No valid jobs found in YAML file after validation.")
        return

    db = SessionLocal()
    try:
        for job_config in validated_jobs:
            # Map the Pydantic object to the SQLAlchemy model
            trigger_config = job_config.trigger.copy()
            trigger_type = trigger_config.pop('type')

            job_definition = JobDefinition(
                id=job_config.id,
                func=job_config.func,
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
            logging.info(f"Merging job definition '{job_config.id}' into database.")

        db.commit()
        logging.info(f"Database seeding complete. {len(validated_jobs)} jobs merged.")
    except Exception as e:
        logging.error(f"An error occurred during database seeding: {e}")
        db.rollback()
    finally:
        db.close()
