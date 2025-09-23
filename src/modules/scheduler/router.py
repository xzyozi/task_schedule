import json, os
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import models, schemas, service, loader
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

# --- Dashboard Endpoints ---

@router.get("/dashboard/summary", response_model=schemas.DashboardSummary, tags=["Dashboard"])
def get_dashboard_summary(db: Session = Depends(get_db)):
    try:
        total_jobs = db.query(models.JobDefinition).count()
        running_jobs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'RUNNING').count()
        successful_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'COMPLETED').count()
        failed_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'FAILED').count()
        return schemas.DashboardSummary(
            total_jobs=total_jobs, running_jobs=running_jobs, 
            successful_runs=successful_runs, failed_runs=failed_runs
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard summary")

@router.get("/logs", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Dashboard"])
def get_execution_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        logs = db.query(models.ProcessExecutionLog).order_by(models.ProcessExecutionLog.start_time.desc()).offset(skip).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching execution logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution logs")

@router.get("/timeline/data", response_model=List[schemas.TimelineItem], tags=["Dashboard"])
def get_timeline_data(db: Session = Depends(get_db)):
    try:
        timeline_items: List[schemas.TimelineItem] = []
        scheduled_jobs = service.scheduler.get_jobs()
        for job in scheduled_jobs:
            if job.next_run_time:
                start_time_aware = job.next_run_time.replace(tzinfo=timezone.utc) if job.next_run_time.tzinfo is None else job.next_run_time
                timeline_items.append(schemas.TimelineItem(
                    id=f"scheduled-{job.id}-{start_time_aware.isoformat()}",
                    content=f"{job.id} (Scheduled)", start=start_time_aware, status="scheduled", group=job.id
                ))
        recent_logs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.start_time >= datetime.now(timezone.utc) - timedelta(days=7)).order_by(models.ProcessExecutionLog.start_time.asc()).all()
        for log in recent_logs:
            item_status = log.status.lower()
            start = log.start_time.replace(tzinfo=timezone.utc) if log.start_time.tzinfo is None else log.start_time
            end = None
            if log.end_time:
                end = log.end_time.replace(tzinfo=timezone.utc) if log.end_time.tzinfo is None else log.end_time
            elif item_status == 'running':
                end = datetime.now(timezone.utc)
            timeline_items.append(schemas.TimelineItem(
                id=f"log-{log.id}", content=f"{log.job_id} ({item_status.capitalize()})",
                start=start, end=end, status=item_status, group=log.job_id
            ))
        timeline_items.sort(key=lambda item: item.start)
        return timeline_items
    except Exception as e:
        logger.error(f"Error fetching timeline data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Job Definition Endpoints ---

@router.get("/jobs", response_model=List[schemas.JobConfig], tags=["Job Definitions"])
def read_jobs(db: Session = Depends(get_db)):
    jobs = db.query(models.JobDefinition).all()
    return [schemas.JobConfig.model_validate(job) for job in jobs]

@router.post("/jobs", response_model=schemas.JobConfig, status_code=status.HTTP_201_CREATED, tags=["Job Definitions"])
def create_job(job: schemas.JobConfig, db: Session = Depends(get_db)):
    if db.query(models.JobDefinition).filter(models.JobDefinition.id == job.id).first():
        raise HTTPException(status_code=409, detail="Job with this ID already exists")
    trigger_dict = job.trigger.dict()
    db_job = models.JobDefinition(
        id=job.id, func=job.func, trigger_type=trigger_dict.pop('type'), trigger_config=trigger_dict,
        args=job.args, kwargs=job.kwargs, max_instances=job.max_instances, coalesce=job.coalesce,
        misfire_grace_time=job.misfire_grace_time, is_enabled=job.is_enabled, description=job.description
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

# --- Scheduler Control Endpoints (APScheduler Instance) ---

@router.get("/scheduler/jobs", response_model=List[schemas.JobInfo], tags=["Scheduler Control"])
def get_scheduled_jobs():
    """Returns a list of all jobs currently scheduled in the scheduler."""
    jobs = service.scheduler.get_jobs()
    job_infos = []
    for job in jobs:
        try:
            trigger_dict = {"type": "unknown"}
            trigger_class_name = job.trigger.__class__.__name__.lower()

            if "cron" in trigger_class_name:
                trigger_dict["type"] = "cron"
                for field in job.trigger.fields:
                    trigger_dict[field.name] = str(field)
            elif "interval" in trigger_class_name:
                trigger_dict["type"] = "interval"
                td = job.trigger.interval
                trigger_dict['weeks'] = td.days // 7
                trigger_dict['days'] = td.days % 7
                trigger_dict['hours'] = td.seconds // 3600
                trigger_dict['minutes'] = (td.seconds // 60) % 60
                trigger_dict['seconds'] = td.seconds % 60

            func_repr = job.func
            if not isinstance(func_repr, str):
                func_repr = f"{job.func.__module__}:{job.func.__name__}"

            job_info = schemas.JobInfo(
                id=job.id, func=func_repr, trigger=trigger_dict, args=list(job.args),
                kwargs=job.kwargs, max_instances=job.max_instances, coalesce=job.coalesce,
                misfire_grace_time=job.misfire_grace_time, next_run_time=job.next_run_time
            )
            job_infos.append(job_info)
        except Exception as e:
            logger.error(f"Error processing job '{job.id}' for API response: {e}", exc_info=True)
    return job_infos
