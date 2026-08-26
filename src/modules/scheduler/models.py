# SQLAlchemy models for the Scheduler module
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


class JobDefinition(Base):
    __tablename__ = "job_definitions"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False, server_default="Unnamed Job")
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    task_type: Mapped[str] = mapped_column(nullable=False)
    task_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    trigger_type: Mapped[str] = mapped_column(nullable=False)
    trigger_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    max_instances: Mapped[int] = mapped_column(default=1, nullable=False)
    coalesce: Mapped[bool] = mapped_column(default=False, nullable=False)
    misfire_grace_time: Mapped[Optional[int]] = mapped_column(nullable=True, default=3600)


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schedule: Mapped[Optional[str]] = mapped_column(nullable=True)  # e.g., Cron string
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    params_def: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    steps: Mapped[List["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="workflow", cascade="all, delete-orphan"
    )
    runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="workflow")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    task_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # Unified task definition
    on_failure: Mapped[str] = mapped_column(default="stop", nullable=False)
    timeout: Mapped[Optional[int]] = mapped_column(nullable=True)
    run_in_background: Mapped[bool] = mapped_column(default=False, nullable=False)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="PENDING")
    current_step: Mapped[Optional[int]] = mapped_column(default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    logs: Mapped[List["ProcessExecutionLog"]] = relationship("ProcessExecutionLog", back_populates="workflow_run")
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")


class ProcessExecutionLog(Base):
    __tablename__ = "process_execution_logs"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    workflow_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)
    command: Mapped[str] = mapped_column(nullable=False)
    exit_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)

    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="logs")
