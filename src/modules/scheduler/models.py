# SQLAlchemy models for the Scheduler module
from sqlalchemy import Boolean, Column, Integer, JSON, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
    env = Column(JSON, nullable=True)
    max_instances = Column(Integer, default=1, nullable=False)
    coalesce = Column(Boolean, default=False, nullable=False)
    misfire_grace_time = Column(Integer, nullable=True, default=3600)

class Workflow(Base):
    __tablename__ = 'workflows'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    schedule = Column(String, nullable=True) # e.g., Cron string
    is_enabled = Column(Boolean, default=True, nullable=False)
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowStep(Base):
    __tablename__ = 'workflow_steps'
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False)
    step_order = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    job_type = Column(String, nullable=False)
    target = Column(Text, nullable=False)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    on_failure = Column(String, default='stop', nullable=False)
    timeout = Column(Integer, nullable=True)
    workflow = relationship("Workflow", back_populates="steps")

class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False)
    status = Column(String, nullable=False, default='PENDING')
    current_step = Column(Integer, default=0)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)

class ProcessExecutionLog(Base):
    __tablename__ = 'process_execution_logs'

    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, nullable=True)
    workflow_run_id = Column(Integer, ForeignKey('workflow_runs.id'), nullable=True)
    command = Column(String, nullable=False)
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False)