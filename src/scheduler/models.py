from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, RootModel, validator


class CronTrigger(BaseModel):
    type: str = 'cron'
    year: Optional[Union[int, str]] = None
    month: Optional[Union[int, str]] = None
    day: Optional[Union[int, str]] = None
    week: Optional[Union[int, str]] = None
    day_of_week: Optional[Union[int, str]] = None
    hour: Optional[Union[int, str]] = None
    minute: Optional[Union[int, str]] = None
    second: Optional[Union[int, str]] = None
    timezone: Optional[str] = 'UTC'

class IntervalTrigger(BaseModel):
    type: str = 'interval'
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    timezone: Optional[str] = 'UTC'

class JobConfig(BaseModel):
    id: str
    func: str
    trigger: Union[CronTrigger, IntervalTrigger]
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    replace_existing: bool = True
    max_instances: int = 1
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600

    @validator("trigger", pre=True)
    def validate_trigger_type(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Trigger must be a dictionary")
        trigger_type = v.get("type")
        if trigger_type == "cron":
            return CronTrigger(**v)
        elif trigger_type == "interval":
            return IntervalTrigger(**v)
        raise ValueError(f"Unsupported trigger type: {trigger_type}")

class Config(RootModel[List[JobConfig]]):
    """A root model for a list of job configurations."""
    pass
