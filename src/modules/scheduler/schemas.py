import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator, validator

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

class JobConfig(BaseModel):
    id: str
    func: str
    description: Optional[str] = None
    is_enabled: bool = True
    job_type: str = Field("python_function", pattern="^(python_function|shell_command)$")
    trigger: CronTrigger | IntervalTrigger
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    cwd: Optional[str] = None
    max_instances: int = 1
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600
    replace_existing: bool = True
    model_config = ConfigDict(from_attributes=True)

    @validator('cwd')
    def validate_cwd(cls, v):
        if v is None:
            return v
        
        # 絶対パスかどうかを検証
        if not os.path.isabs(v):
            raise ValueError('CWD must be an absolute path.')
        
        # ディレクトリが存在するかを検証
        if not os.path.isdir(v):
            raise ValueError(f'CWD directory not found: {v}')
            
        return v

    @model_validator(mode='before')
    @classmethod
    def assemble_trigger_from_db_model(cls, data: Any) -> Any:
        if isinstance(data, models.JobDefinition):
            model_dict = {c.name: getattr(data, c.name) for c in data.__table__.columns}
            model_dict['trigger'] = {
                'type': model_dict.get('trigger_type'),
                **(model_dict.get('trigger_config') or {})
            }
            return model_dict
        return data

class TimelineItem(BaseModel):
    id: str
    content: str
    start: datetime
    end: Optional[datetime] = None
    status: str
    group: Optional[str] = None

class JobInfo(JobConfig):
    next_run_time: Optional[datetime] = None

class BulkJobUpdate(BaseModel):
    job_ids: List[str]

class DashboardSummary(BaseModel):
    total_jobs: int
    running_jobs: int
    successful_runs: int
    failed_runs: int

class ProcessExecutionLogInfo(BaseModel):
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

class ErrorResponse(BaseModel):
    detail: str
