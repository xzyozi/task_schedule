from typing import Generator, List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import JobDefinition, JobConfig
from .scheduler import scheduler 
app = FastAPI(title="Resilient Task Scheduler API")

# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Resilient Task Scheduler API!"}


# --- Job Management Endpoints ---

@app.get("/jobs", response_model=List[JobConfig], tags=["Jobs"])
def read_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobDefinition).all()
    return [JobConfig.model_validate(job) for job in jobs]

@app.post("/jobs", response_model=JobConfig, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
def create_job(job: JobConfig, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job.id).first()
    if db_job:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job with this ID already exists")
    
    # Map JobConfig Pydantic model to JobDefinition SQLAlchemy model
    trigger_config = job.trigger.copy()
    trigger_type = trigger_config.pop('type')

    db_job = JobDefinition(
        id=job.id,
        func=job.func,
        trigger_type=trigger_type,
        trigger_config=trigger_config,
        args=job.args,
        kwargs=job.kwargs,
        max_instances=job.max_instances,
        coalesce=job.coalesce,
        misfire_grace_time=job.misfire_grace_time,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return JobConfig.model_validate(db_job)

@app.get("/jobs/{job_id}", response_model=JobConfig, tags=["Jobs"])
def read_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobConfig.model_validate(job)

@app.put("/jobs/{job_id}", response_model=JobConfig, tags=["Jobs"])
def update_job(job_id: str, job: JobConfig, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Update fields
    db_job.func = job.func
    
    trigger_config = job.trigger.copy()
    db_job.trigger_type = trigger_config.pop('type')
    db_job.trigger_config = trigger_config

    db_job.args = job.args
    db_job.kwargs = job.kwargs
    db_job.max_instances = job.max_instances
    db_job.coalesce = job.coalesce
    db_job.misfire_grace_time = job.misfire_grace_time

    db.commit()
    db.refresh(db_job)
    return JobConfig.model_validate(db_job)

@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Jobs"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    db.delete(db_job)
    db.commit()
    return
