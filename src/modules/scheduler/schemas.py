import os
from typing import Any, Dict, List, Optional, Literal, Union, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, EmailStr, HttpUrl

from modules.scheduler import models

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

# --- Task-specific Parameter Schemas ---

class PythonJobParams(BaseModel):
    task_type: Literal["python"]
    module: str = Field(..., description="The Python module path, e.g., 'my_tasks.main'")
    function: str = Field(..., description="The function name to execute within the module")
    args: Optional[List[Any]] = Field(default_factory=list, description="Positional arguments for the function")
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Keyword arguments for the function")

class ShellJobParams(BaseModel):
    task_type: Literal["shell"]
    command: str = Field(..., description="The shell command to execute")
    cwd: Optional[str] = Field(None, description="Working directory for the command. Must be a relative path within the project's work dir.")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables for the command.")

    @field_validator('cwd')
    def validate_cwd(cls, v):
        if v is None:
            return v
        if os.path.isabs(v) or '..' in v:
            raise ValueError('CWD must be a relative path and cannot contain "..".')
        return v

class EmailJobParams(BaseModel):
    task_type: Literal["email"]
    to_email: EmailStr = Field(..., description="Recipient's email address")
    subject: str = Field(..., min_length=1, description="Email subject")
    template_name: Optional[str] = Field(None, description="Name of the Jinja2 template file")
    template_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Context data for the template")
    body: Optional[str] = Field(None, description="Direct email body (used if no template_name)")
    body_type: str = Field("plain", description="Type of email body (plain or html)")
    image_paths: Optional[List[str]] = Field(default_factory=list, description="List of image file paths to attach")

    @model_validator(mode='after')
    def check_body_or_template(self):
        if not self.template_name and not self.body:
            raise ValueError("Either 'template_name' or 'body' must be provided.")
        return self

# Discriminated union for all possible task parameters
AnyJobParams = Union[PythonJobParams, ShellJobParams, EmailJobParams]


# --- Core Job Schemas ---

class JobBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_enabled: bool = True
    trigger: CronTrigger | IntervalTrigger
    task_parameters: Annotated[AnyJobParams, Field(discriminator="task_type")]
    
    max_instances: int = 3
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600
    
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def assemble_from_db_model(cls, data: Any) -> Any:
        if not isinstance(data, models.JobDefinition):
            return data
        
        # Convert SQLAlchemy model to a dictionary
        model_dict = {c.name: getattr(data, c.name) for c in data.__table__.columns}
        
        # Assemble the 'trigger' field
        model_dict['trigger'] = {
            'type': model_dict.get('trigger_type'),
            **(model_dict.get('trigger_config') or {})
        }
        
        # Assemble the 'task_parameters' field for the discriminated union
        task_params = model_dict.get('task_parameters', {})
        if isinstance(task_params, dict):
            task_params['task_type'] = model_dict.get('task_type')
            model_dict['task_parameters'] = task_params
        
        return model_dict

class JobCreate(JobBase):
    id: Optional[str] = None

class JobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    trigger: Optional[CronTrigger | IntervalTrigger] = None
    task_parameters: Optional[Annotated[AnyJobParams, Field(discriminator="task_type")]] = None
    max_instances: Optional[int] = None
    coalesce: Optional[bool] = None
    misfire_grace_time: Optional[int] = None

class Job(JobBase):
    id: str
    next_run_time: Optional[datetime] = None

# Schemas for WorkflowStep
class WorkflowStepBase(BaseModel):
    name: str
    step_order: int
    job_type: str
    target: str
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    on_failure: str = "stop"
    timeout: Optional[int] = None
    run_in_background: bool = False

class WorkflowStepCreate(WorkflowStepBase):
    pass

class WorkflowStep(WorkflowStepBase):
    id: int
    workflow_id: int
    model_config = ConfigDict(from_attributes=True)

# Schemas for Workflow
class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    schedule: Optional[str] = None
    is_enabled: bool = True
    params_def: Optional[List[Dict[str, Any]]] = None

class WorkflowCreate(WorkflowBase):
    steps: List[WorkflowStepCreate]

class Workflow(WorkflowBase):
    id: int
    steps: List[WorkflowStep] = []
    runs: List['WorkflowRun'] = []
    model_config = ConfigDict(from_attributes=True)

class WorkflowRunCreate(BaseModel):
    params_val: Optional[Dict[str, Any]] = None

class WorkflowRun(BaseModel):
    id: int
    workflow_id: int
    status: str
    current_step: int
    start_time: datetime
    end_time: Optional[datetime] = None
    params_val: Optional[Dict[str, Any]] = None 
    model_config = ConfigDict(from_attributes=True)

class TimelineItem(BaseModel):
    id: str
    content: str
    start: datetime
    end: Optional[datetime] = None
    status: str
    group: Optional[str] = None

class BulkJobUpdate(BaseModel):
    job_ids: List[str]

class DashboardSummary(BaseModel):
    total_jobs: int
    running_jobs: int
    successful_runs: int
    failed_runs: int

class ProcessExecutionLogInfo(BaseModel):
    id: str
    job_id: Optional[str] = None
    workflow_run_id: Optional[int] = None
    command: str
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    detail: str

class UnifiedJobItem(BaseModel):
    id: str
    type: str  # 'job' or 'workflow'
    name: str
    description: Optional[str] = None
    is_enabled: bool
    schedule: Optional[str]
    next_run_time: Optional[datetime] = None
    status: str # 'enabled', 'disabled', 'paused'

# --- Schemas for Email Tasks ---
# Note: EmailJobParams is now the primary schema for creating email jobs.
# These schemas below are for specific, structured notification types.

class NotificationEmailParams(BaseModel):
    subject: str = Field(..., min_length=1, description="Email subject")
    main_message: str = Field(..., min_length=1, description="Main message content for the email body")
    to_email: EmailStr = Field("admin@example.com", description="Recipient's email address (defaults to admin)")
    details: Optional[Dict[str, str]] = Field(None, description="Key-value pairs for a details table in the email")
    error_message: Optional[str] = Field(None, description="Error message to display prominently")
    error_details: Optional[str] = Field(None, description="Detailed error information (e.g., traceback)")
    call_to_action_url: Optional[HttpUrl] = Field(None, description="URL for a call-to-action button")
    call_to_action_text: Optional[str] = Field(None, description="Text for the call-to-action button")
    recipient_name: Optional[str] = Field(None, description="Name for the email greeting (e.g., 'Dear [Name]')")
    image_paths: Optional[List[str]] = Field(None, description="List of image file paths to attach")

class TaskFailureNotificationParams(BaseModel):
    task_id: str = Field(..., min_length=1, description="ID of the failed task")
    error_message: str = Field(..., min_length=1, description="Concise error message for the failure")
    error_details: Optional[str] = Field(None, description="Detailed error information (e.g., traceback)")
    recipient_email: EmailStr = Field("admin@example.com", description="Recipient's email address (defaults to admin)")
    log_url: Optional[HttpUrl] = Field(None, description="URL to the task's log for more details")