from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Boolean, Column, Integer, JSON, String

from .database import Base # Import Base from database.py

# --- SQLAlchemy Models ---

class JobDefinition(Base):
    """SQLAlchemy model for storing job definitions in the database."""
    __tablename__ = 'job_definitions'

    id = Column(String, primary_key=True, index=True)
    func = Column(String, nullable=False)
    
    # The trigger is split into type and its config for easier querying
    trigger_type = Column(String, nullable=False)
    trigger_config = Column(JSON, nullable=False)

    args = Column(JSON, default=list, nullable=False)
    kwargs = Column(JSON, default=dict, nullable=False)
    
    # APScheduler control settings
    max_instances = Column(Integer, default=1, nullable=False)
    coalesce = Column(Boolean, default=False, nullable=False)
    misfire_grace_time = Column(Integer, nullable=True, default=3600)

    def __repr__(self):
        return f"<JobDefinition(id='{self.id}', func='{self.func}')>"

# --- Pydantic Models ---
# This model will be useful for API validation and for representing job data.

class BaseTrigger(BaseModel):
    timezone: Optional[str] = 'UTC'

class CronTrigger(BaseTrigger):
    type: Literal['cron'] = 'cron'
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    week: Optional[str] = None
    day_of_week: Optional[str] = None
    hour: Optional[str] = None
    minute: Optional[str] = None
    second: Optional[str] = None

class IntervalTrigger(BaseTrigger):
    type: Literal['interval'] = 'interval'
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0

class JobConfigBase(BaseModel):
    """Base Pydantic model for job configuration."""
    id: str
    func: str
    trigger: Union[CronTrigger, IntervalTrigger] = Field(discriminator='type')
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    replace_existing: bool = True
    max_instances: int = 1
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600

class JobConfig(JobConfigBase):
    """Pydantic model for job configuration, used for validation from YAML."""
    pass

class JobConfigApi(JobConfigBase):
    """Pydantic model for job configuration for API, with from_attributes=True."""
    model_config = ConfigDict(from_attributes=True)


# --- Error Response Model ---
class ErrorResponse(BaseModel):
    """Pydantic model for consistent error responses."""
    detail: str