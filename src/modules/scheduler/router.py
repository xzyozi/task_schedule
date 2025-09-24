import json, os
from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from apscheduler.jobstores.base import JobLookupError

from core.database import get_db
from modules.scheduler import models, schemas, loader
from modules.scheduler.service import job_definition_service
from modules.scheduler import scheduler_instance
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

#
# --- Dashboard Endpoints ---
#
@router.get("/dashboard/summary", response_model=schemas.DashboardSummary, tags=["Dashboard"], summary="Get Dashboard Summary", description="Provides a high-level summary of job statuses.")
def get_dashboard_summary(db: Session = Depends(get_db)):
    try:
        total_jobs = len(scheduler_instance.scheduler.get_jobs())
        running_jobs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'RUNNING').count()
        successful_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'COMPLETED').count()
        failed_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'FAILED').count()
        return schemas.DashboardSummary(total_jobs=total_jobs, running_jobs=running_jobs, successful_runs=successful_runs, failed_runs=failed_runs)
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard summary")

@router.get("/logs", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Dashboard"], summary="Get Execution Logs", description="Retrieves a paginated list of job execution logs.")
def get_execution_logs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        logs = db.query(models.ProcessExecutionLog).order_by(models.ProcessExecutionLog.start_time.desc()).offset(skip).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching execution logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution logs")

@router.get("/timeline/data", response_model=List[schemas.TimelineItem], tags=["Dashboard"], summary="Get Timeline Data", description="Provides data for the job execution timeline, including scheduled and historical runs.")
def get_timeline_data(db: Session = Depends(get_db)):
    try:
        timeline_items: List[schemas.TimelineItem] = []
        scheduled_jobs = scheduler_instance.scheduler.get_jobs()
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
#
@router.get("/jobs", response_model=List[schemas.JobConfig], tags=["Job Definitions"], summary="List All Job Definitions")
def read_jobs(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    jobs = job_definition_service.get_multi(db, skip=skip, limit=limit)
    return [schemas.JobConfig.model_validate(job) for job in jobs]

@router.post("/jobs", response_model=schemas.JobConfig, status_code=status.HTTP_201_CREATED, tags=["Job Definitions"], summary="Create a New Job Definition")
def create_job(job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    if job_definition_service.get(db, id=job_in.id):
        raise HTTPException(status_code=409, detail="Job with this ID already exists")
    db_job = job_definition_service.create_from_config(db, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.get("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def read_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return schemas.JobConfig.model_validate(db_job)

@router.put("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def update_job(job_id: str, job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job = job_definition_service.update_from_config(db, db_obj=db_job, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Job Definitions"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.remove(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    loader.sync_jobs_from_db()
    return


# --- Scheduler Control Endpoints ---
@router.get("/scheduler/jobs", response_model=List[schemas.JobInfo], tags=["Scheduler Control"])
def get_scheduled_jobs():
    jobs = scheduler_instance.scheduler.get_jobs()
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

# --- job edit Endpoints ---

@router.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler Control"])
def pause_scheduled_job(job_id: str):
    try:
        scheduler_instance.scheduler.pause_job(job_id)
        return {"message": f"Job '{job_id}' paused successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

@router.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler Control"])
def resume_scheduled_job(job_id: str):
    try:
        scheduler_instance.scheduler.resume_job(job_id)
        return {"message": f"Job '{job_id}' resumed successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

@router.post("/scheduler/jobs/{job_id}/run", tags=["Scheduler Control"])
def run_scheduled_job_immediately(job_id: str):
    try:
        scheduler_instance.scheduler.modify_job(job_id, next_run_time=datetime.now())
        return {"message": f"Job '{job_id}' scheduled for immediate execution."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.put("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def update_job(job_id: str, job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job = job_definition_service.update_from_config(db, db_obj=db_job, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Job Definitions"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.remove(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    loader.sync_jobs_from_db()
    return

@router.post("/jobs/bulk/delete", status_code=status.HTTP_200_OK, tags=["Job Definitions"])
def delete_bulk_jobs(payload: schemas.BulkJobUpdate, db: Session = Depends(get_db)):
    job_ids = payload.job_ids
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    deleted_count = 0
    for job_id in job_ids:
        if job_definition_service.remove(db, id=job_id):
            deleted_count += 1
    if deleted_count > 0:
        loader.sync_jobs_from_db()
    return {"message": f"Successfully deleted {deleted_count} jobs."}

@router.post("/scheduler/jobs/bulk/pause", tags=["Scheduler Control"])
def pause_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate):
    paused_ids = []
    failed_ids = {}
    for job_id in payload.job_ids:
        try:
            scheduler_instance.scheduler.pause_job(job_id)
            paused_ids.append(job_id)
        except JobLookupError:
            failed_ids[job_id] = "Not Found"
    if failed_ids:
        return {"message": "Partial success", "paused": paused_ids, "failed": failed_ids}
    return {"message": "All selected jobs paused successfully."}

@router.post("/scheduler/jobs/bulk/resume", tags=["Scheduler Control"])
def resume_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate):
    resumed_ids = []
    failed_ids = {}
    for job_id in payload.job_ids:
        try:
            scheduler_instance.scheduler.resume_job(job_id)
            resumed_ids.append(job_id)
        except JobLookupError:
            failed_ids[job_id] = "Not Found"
    if failed_ids:
        return {"message": "Partial success", "resumed": resumed_ids, "failed": failed_ids}
    return {"message": "All selected jobs resumed successfully."}

@router.get("/jobs/{job_id}/history", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Job Details"])
def get_job_execution_history(job_id: str, db: Session = Depends(get_db)):
    history = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.job_id == job_id).order_by(models.ProcessExecutionLog.start_time.desc()).all()
    return history




@router.get("/jobs_yaml", tags=["Configuration"])
def get_jobs_yaml_content():
    config_path = "jobs.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {config_path}")
    except Exception as e:
        logger.error(f"Error reading jobs.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read jobs.yaml")

NOTIFICATION_SETTINGS_FILE = "notification_settings.json"

@router.get("/settings/notifications", tags=["Settings"])
def get_notification_settings():
    if not os.path.exists(NOTIFICATION_SETTINGS_FILE):
        return {"email_recipients": "", "webhook_url": ""}
    try:
        with open(NOTIFICATION_SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        logger.error(f"Error reading notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read notification settings.")

@router.post("/settings/notifications", tags=["Settings"])
def update_notification_settings(email_recipients: str = "", webhook_url: str = ""):
    settings = {
        "email_recipients": email_recipients,
        "webhook_url": webhook_url
    }
    try:
        with open(NOTIFICATION_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        logger.info("Notification settings updated successfully.")
        return {"message": "Notification settings updated successfully."}
    except Exception as e:
        logger.error(f"Error writing notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update notification settings.")
