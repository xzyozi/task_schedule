import atexit
import logging

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def start_scheduler():
    """Starts the scheduler and registers a shutdown hook."""
    logging.info("Starting scheduler...")
    scheduler.start()
    # Register a shutdown hook to gracefully stop the scheduler
    atexit.register(shutdown_scheduler)

def shutdown_scheduler():
    """Shuts down the scheduler."""
    logging.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown()

