import pytest
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.joinpath("src")))

from core.database import Base
from modules.scheduler import models, schemas, service
from modules.scheduler.job_executors import run_workflow

# --- Test Setup and Fixtures ---

@pytest.fixture(scope="session")
def SessionLocal():
    """Create a sessionmaker for a temporary in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session(SessionLocal):
    """Yield a new database session for a test, rolling back changes afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

import os

@pytest.fixture(scope="function")
def test_tasks_module(tmp_path, monkeypatch):
    """Create a temporary Python module with task functions."""
    tasks_content = """
def step_one(*args, **kwargs):
    print("step one executed")
    return "ok"

def step_two(*args, **kwargs):
    print("step two executed")
    return "ok"

def failing_step(*args, **kwargs):
    raise RuntimeError("intentional failure")
"""
    tasks_file = tmp_path / "temp_workflow_tasks.py"
    tasks_file.write_text(tasks_content)

    # Add the temp directory to sys.path and PYTHONPATH so child processes can import it
    sys.path.insert(0, str(tmp_path))
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    new_pythonpath = str(tmp_path) + os.path.pathsep + current_pythonpath if current_pythonpath else str(tmp_path)
    monkeypatch.setenv("PYTHONPATH", new_pythonpath)
    yield "temp_workflow_tasks"
    sys.path.pop(0)


# --- Tests ---

def test_workflow_sequential_execution(db_session, test_tasks_module):
    """
    ワークフローが登録されたステップ(shell/python)を順番に実行することを確認する。
    ステップ間の変数受け渡し・テンプレート機能はスコープ外。
    """
    workflow_in = schemas.WorkflowCreate(
        name="Sequential Execution Test Workflow",
        description="複数ステップを順番に実行するだけの単純なワークフロー",
        is_enabled=True,
        steps=[
            schemas.WorkflowStepCreate(
                name="Step One",
                step_order=1,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="step_one",
                ),
            ),
            schemas.WorkflowStepCreate(
                name="Step Two",
                step_order=2,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="step_two",
                ),
            ),
        ]
    )

    created_workflow = service.workflow_service.create_with_steps(db=db_session, obj_in=workflow_in)
    assert created_workflow is not None
    assert len(created_workflow.steps) == 2

    run_workflow(workflow_id=created_workflow.id, db=db_session)

    db_session.commit()
    workflow_run = db_session.query(models.WorkflowRun).filter_by(workflow_id=created_workflow.id).one()

    assert workflow_run is not None
    assert workflow_run.status == "COMPLETED"

    logs = db_session.query(models.ProcessExecutionLog).filter(
        models.ProcessExecutionLog.workflow_run_id == workflow_run.id
    ).order_by(models.ProcessExecutionLog.start_time).all()

    assert len(logs) == 2
    assert all(log.status == "COMPLETED" for log in logs)


def test_workflow_stops_on_failure(db_session, test_tasks_module):
    """
    on_failure='stop'(デフォルト)の場合、あるステップが失敗すると
    後続のステップは実行されずワークフローがFAILEDになることを確認する。
    """
    workflow_in = schemas.WorkflowCreate(
        name="Stop On Failure Test Workflow",
        description="失敗したら止まることを確認するワークフロー",
        is_enabled=True,
        steps=[
            schemas.WorkflowStepCreate(
                name="Failing Step",
                step_order=1,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="failing_step",
                ),
                on_failure="stop",
            ),
            schemas.WorkflowStepCreate(
                name="Should Not Run Step",
                step_order=2,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="step_two",
                ),
            ),
        ]
    )

    created_workflow = service.workflow_service.create_with_steps(db=db_session, obj_in=workflow_in)

    run_workflow(workflow_id=created_workflow.id, db=db_session)

    db_session.commit()
    workflow_run = db_session.query(models.WorkflowRun).filter_by(workflow_id=created_workflow.id).one()

    assert workflow_run.status == "FAILED"

    logs = db_session.query(models.ProcessExecutionLog).filter(
        models.ProcessExecutionLog.workflow_run_id == workflow_run.id
    ).all()

    # 失敗したステップのみ実行され、後続のステップは実行されていないこと
    assert len(logs) == 1
    assert logs[0].status == "FAILED"
