# SQLAlchemy models for the Scheduler module
from sqlalchemy import Boolean, Column, Integer, JSON, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from core.database import Base

class JobDefinition(Base):
    __tablename__ = 'job_definitions'

    id = Column(String, primary_key=True, index=True)
    func = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    job_type = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_config = Column(JSON, nullable=False)
    args = Column(JSON, default=list, nullable=False)
    kwargs = Column(JSON, default=dict, nullable=False)
    cwd = Column(String, nullable=True)
    max_instances = Column(Integer, default=1, nullable=False)
    coalesce = Column(Boolean, default=False, nullable=False)
    misfire_grace_time = Column(Integer, nullable=True, default=3600)

class WorkflowDefinition(Base):
    __tablename__ = 'workflow_definitions'

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    steps = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey('workflow_definitions.id'), nullable=False)
    status = Column(String, nullable=False, default='PENDING')
    current_step_index = Column(Integer, default=0)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

class ProcessExecutionLog(Base):
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
    status = Column(String, nullable=False)
