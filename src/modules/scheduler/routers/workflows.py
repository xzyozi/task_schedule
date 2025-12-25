from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import models, schemas, loader, service
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter()

@router.post("/workflows", response_model=schemas.Workflow, status_code=status.HTTP_201_CREATED, tags=["Workflow Definitions"])
def create_workflow(workflow_in: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    existing_workflow = service.workflow_service.get_by_name(db, name=workflow_in.name)
    if existing_workflow:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow with name '{workflow_in.name}' already exists."
        )
    db_workflow = service.workflow_service.create_with_steps(db, obj_in=workflow_in)
    loader.schedule_workflow(db_workflow)
    return db_workflow

@router.get("/workflows", response_model=List[schemas.Workflow], tags=["Workflow Definitions"])
def read_workflows(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    workflows = service.workflow_service.get_multi(db, skip=skip, limit=limit)
    return workflows

@router.get("/workflows/{workflow_id}", response_model=schemas.Workflow, tags=["Workflow Definitions"])
def read_workflow(workflow_id: int, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.get(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow

@router.put("/workflows/{workflow_id}", response_model=schemas.Workflow, tags=["Workflow Definitions"])
def update_workflow(workflow_id: int, workflow_in: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.get(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db_workflow = service.workflow_service.update_with_steps(db, db_obj=db_workflow, obj_in=workflow_in)
    loader.schedule_workflow(db_workflow)
    return db_workflow

@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Workflow Definitions"])
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.remove(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Job not found")
    loader.remove_workflow_job(workflow_id)
    return

@router.post("/workflows/{workflow_id}/pause", tags=["Workflow Control"], summary="Pause a Workflow")
def pause_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """
    Pauses a workflow by removing its job from the scheduler and marking it as disabled.
    """
    service.update_workflow_enabled_status(db, workflow_id=workflow_id, is_enabled=False)
    try:
        loader.remove_workflow_job(workflow_id)
        return {"message": f"Workflow '{workflow_id}' paused successfully."}
    except Exception as e:
        logger.error(f"Error removing workflow job {workflow_id} from scheduler: {e}", exc_info=True)
        return {"message": f"Workflow '{workflow_id}' marked as disabled, but could not be removed from scheduler."}

@router.post("/workflows/{workflow_id}/resume", tags=["Workflow Control"], summary="Resume a Workflow")
def resume_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """
    Resumes a workflow by scheduling it and marking it as enabled.
    """
    db_workflow = service.update_workflow_enabled_status(db, workflow_id=workflow_id, is_enabled=True)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        loader.schedule_workflow(db_workflow)
        return {"message": f"Workflow '{db_workflow.name}' resumed successfully."}
    except Exception as e:
        logger.error(f"Error scheduling workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to schedule workflow {workflow_id}.")

@router.post("/workflows/{workflow_id}/run", tags=["Workflow Control"], summary="Run a Workflow Immediately")
def run_workflow_immediately(
    workflow_id: int,
    db: Session = Depends(get_db)
):
    """
    Triggers an immediate, one-off execution of a workflow.
    """
    db_workflow = service.workflow_service.get(db, id=workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        result = service.run_workflow_immediately(db, workflow_id=workflow_id)
        return result
    except Exception as e:
        logger.error(f"Error triggering immediate run for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow {workflow_id}.")

@router.get("/workflow-runs/{run_id}/logs", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Workflow Runs"])
def get_workflow_run_logs(run_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all execution logs for a specific workflow run.
    """
    logs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.workflow_run_id == run_id).order_by(models.ProcessExecutionLog.start_time).all()
    if not logs:
        raise HTTPException(status_code=404, detail="Logs for this workflow run not found")
    return logs
