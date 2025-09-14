import logging

from sqlalchemy.orm import sessionmaker

# Import the scheduler instance directly
from .scheduler import scheduler
from .database import engine
from .models import JobDefinition

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def sync_jobs_from_db():
    """Synchronizes jobs from the database with the scheduler."""
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