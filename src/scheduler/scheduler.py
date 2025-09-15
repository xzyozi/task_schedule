import atexit
import logging
from datetime import datetime, timedelta

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Retry parameters
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30

# Configure job stores
jobstores = {
    "default": SQLAlchemyJobStore(url=settings.DATABASE_URL)
}

# Configure executors
executors = {
    "default": ThreadPoolExecutor(20),
    "processpool": ProcessPoolExecutor(5),
}

# Configure job defaults
job_defaults = {
    "coalesce": False,
    "max_instances": 3
}

# Initialize the scheduler
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults
)

def job_error_listener(event):
    """Listener for job execution errors, implementing retry logic."""
    job = scheduler.get_job(event.job_id)
    if event.exception and job:
        current_retries = job.kwargs.get('retry_count', 0)

        logger.error(f"Job {job.id} failed with exception: {event.exception}. Retry count: {current_retries}")

        if current_retries < MAX_RETRIES:
            new_kwargs = job.kwargs.copy()
            new_kwargs['retry_count'] = current_retries + 1

            retry_time = datetime.now() + timedelta(seconds=RETRY_DELAY_SECONDS)
            scheduler.add_job(
                job.func,
                'date',
                run_date=retry_time,
                args=job.args,
                kwargs=new_kwargs,
                id=f"{job.id}_retry_{current_retries + 1}", # Unique ID for retry job
                replace_existing=True # Important for persistent job stores
            )
            logger.info(f"Rescheduled job {job.id} for retry at {retry_time}. New retry count: {new_kwargs['retry_count']}")
        else:
            logger.error(f"Job {job.id} has reached the maximum number of retries ({MAX_RETRIES}). No more retries will be attempted.")

# Add the error listener to the scheduler
scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)


def start_scheduler():
    """Starts the scheduler and registers a shutdown hook."""
    logger.info("Starting scheduler...")
    scheduler.start()
    # Register a shutdown hook to gracefully stop the scheduler
    atexit.register(shutdown_scheduler)

def shutdown_scheduler():
    """Shuts down the scheduler."""
    logger.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown()