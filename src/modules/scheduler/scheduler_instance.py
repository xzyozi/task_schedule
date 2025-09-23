import atexit
from datetime import datetime, timedelta

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

from core.config import settings
from util import logger_util

logger = logger_util.get_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30

jobstores = {
    "default": SQLAlchemyJobStore(url=settings.DATABASE_URL)
}

executors = {
    "default": ThreadPoolExecutor(20),
    "processpool": ProcessPoolExecutor(5),
}

job_defaults = {
    "coalesce": False,
    "max_instances": 3
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults
)

def job_error_listener(event):
    job = scheduler.get_job(event.job_id)
    if event.exception and job:
        current_retries = job.kwargs.get('retry_count', 0)
        logger.error(f"Job {job.id} failed: {event.exception}. Retries: {current_retries}")
        if current_retries < MAX_RETRIES:
            new_kwargs = job.kwargs.copy()
            new_kwargs['retry_count'] = current_retries + 1
            job_func_kwargs = new_kwargs.copy()
            job_func_kwargs.pop('retry_count', None)
            retry_time = datetime.now() + timedelta(seconds=RETRY_DELAY_SECONDS)
            scheduler.add_job(
                job.func,
                'date',
                run_date=retry_time,
                args=job.args,
                kwargs=job_func_kwargs,
                id=f"{job.id}_retry_{current_retries + 1}",
                replace_existing=True
            )
            logger.info(f"Rescheduled {job.id} for retry at {retry_time}.")
        else:
            logger.error(f"Job {job.id} reached max retries.")

scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

def start_scheduler():
    logger.info("Starting scheduler...")
    scheduler.start()
    atexit.register(shutdown_scheduler)

def shutdown_scheduler():
    logger.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown()
