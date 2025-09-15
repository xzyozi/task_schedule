from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, ConfigDict
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

class JobConfig(BaseModel):
    """Pydantic model for job configuration, used for validation."""
    id: str
    func: str
    trigger: Dict[str, Any]
    args: Optional[List[Any]] = Field(default_factory=list)
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    max_instances: int = 1
    coalesce: bool = False
    misfire_grace_time: Optional[int] = 3600

    model_config = ConfigDict(from_attributes=True)

# --- Error Response Model ---
class ErrorResponse(BaseModel):
    """Pydantic model for consistent error responses."""
    detail: str