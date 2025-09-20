from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import Boolean, Column, Integer, JSON, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from .database import Base # Import Base from database.py

# --- SQLAlchemy Models ---

class JobDefinition(Base):
    """SQLAlchemy model for storing individual job definitions."""
    __tablename__ = 'job_definitions'

    id = Column(String, primary_key=True, index=True)
    func = Column(String, nullable=False)
    description = Column(String, nullable=True) # For GUI
    is_enabled = Column(Boolean, default=True, nullable=False) # For GUI control
    
    trigger_type = Column(String, nullable=False)
    trigger_config = Column(JSON, nullable=False)

    args = Column(JSON, default=list, nullable=False)
    kwargs = Column(JSON, default=dict, nullable=False)
    
    max_instances = Column(Integer, default=1, nullable=False)
    coalesce = Column(Boolean, default=False, nullable=False)
    misfire_grace_time = Column(Integer, nullable=True, default=3600)

    def __repr__(self):
        return f"<JobDefinition(id='{self.id}', func='{self.func}')>"

class WorkflowDefinition(Base):
    """SQLAlchemy model for defining a sequence of jobs (a workflow)."""
    __tablename__ = 'workflow_definitions'

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    steps = Column(JSON, nullable=False) # e.g., [{"job_id": "task_a", "on_fail": "stop"}, {"job_id": "task_b"}]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkflowRun(Base):
    """SQLAlchemy model for tracking an instance of a workflow execution."""
    __tablename__ = 'workflow_runs'

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey('workflow_definitions.id'), nullable=False)
    status = Column(String, nullable=False, default='PENDING') # PENDING, RUNNING, SUCCESS, FAILED, STOPPED
    current_step_index = Column(Integer, default=0)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

class ProcessExecutionLog(Base):
    """SQLAlchemy model for logging the execution of external processes."""
    __tablename__ = 'process_execution_logs'

    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey('job_definitions.id'), nullable=False)
    workflow_run_id = Column(String, ForeignKey('workflow_runs.id'), nullable=True)
    
    command = Column(String, nullable=False)
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False) # RUNNING, COMPLETED, FAILED, TIMED_OUT

# --- Pydantic Models ---

class BaseTrigger(BaseModel):
    type: str
    timezone: Optional[str] = 'UTC'

class CronTrigger(BaseTrigger):
    type: str = 'cron'
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    week: Optional[str] = None
    day_of_week: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    second: Optional[str] = None

class IntervalTrigger(BaseTrigger):
    type: str = 'interval'
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0

class JobConfig(BaseModel):
    """Pydantic model for job configuration, used for validation and API."""
    id: str
    func: str
    description: Optional[str] = None
    is_enabled: bool = True
    trigger: CronTrigger | IntervalTrigger
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    max_instances: int = 1
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600
    replace_existing: bool = True

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def assemble_trigger_from_db_model(cls, data: Any) -> Any:
        """Allows validation from a JobDefinition SQLAlchemy model.
        Pydantic can't automatically map trigger_type + trigger_config to trigger,
        so we do it manually here if the input is our DB model.
        """
        if isinstance(data, JobDefinition):
            # Convert the SQLAlchemy model instance to a dict
            model_dict = {c.name: getattr(data, c.name) for c in data.__table__.columns}
            
            # Assemble the 'trigger' field for the Pydantic model
            model_dict['trigger'] = {
                'type': model_dict.get('trigger_type'),
                **(model_dict.get('trigger_config') or {})
            }
            return model_dict
        return data # Keep original data if it's not our DB model

class ProcessExecutionLogInfo(BaseModel):
    """Pydantic model for process execution log entries."""
    id: str
    job_id: str
    command: str
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


# --- Error Response Model ---
class ErrorResponse(BaseModel):
    """Pydantic model for consistent error responses."""
    detail: str