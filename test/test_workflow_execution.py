import pytest
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import shutil

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

@pytest.fixture(scope="function")
def test_tasks_module(tmp_path):
    """Create a temporary Python module with task functions."""
    tasks_content = """
def produce_string():
    return "hello from workflow"

def consume_string(data: str):
    print(f"Consumed: {data}")
    return f"Consumed: {data}"
"""
    tasks_file = tmp_path / "temp_workflow_tasks.py"
    tasks_file.write_text(tasks_content)
    
    # Add the temp directory to sys.path so it can be imported
    sys.path.insert(0, str(tmp_path))
    yield "temp_workflow_tasks"
    sys.path.pop(0)


# --- Tests ---

def test_workflow_with_variable_passing(db_session, test_tasks_module):
    """
    Tests a complete workflow where one step produces a variable and a subsequent
    step consumes it.
    """
    # 1. Create the Workflow in the database
    workflow_in = schemas.WorkflowCreate(
        name="Variable Passing Test Workflow",
        description="A test for passing variables between steps.",
        is_enabled=True,
        steps=[
            schemas.WorkflowStepCreate(
                name="Producer Step",
                step_order=1,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="produce_string",
                ),
                output_variable_name="produced_data"
            ),
            schemas.WorkflowStepCreate(
                name="Consumer Step",
                step_order=2,
                task_parameters=schemas.PythonJobParams(
                    task_type="python",
                    module=test_tasks_module,
                    function="consume_string",
                    kwargs={"data": "{{ context.produced_data }}"}
                ),
            ),
        ]
    )
    
    created_workflow = service.workflow_service.create_with_steps(db=db_session, obj_in=workflow_in)
    assert created_workflow is not None
    assert len(created_workflow.steps) == 2

    # 2. Execute the workflow
    run_workflow(workflow_id=created_workflow.id)

    # 3. Verify the results
    db_session.commit() # Commit to make sure the run_workflow changes are visible
    workflow_run = db_session.query(models.WorkflowRun).filter_by(workflow_id=created_workflow.id).one()

    assert workflow_run is not None
    assert workflow_run.status == "COMPLETED"
    
    # Check the final context
    assert "produced_data" in workflow_run.context
    assert workflow_run.context["produced_data"] == "hello from workflow"

    # Check the logs for the consumer step
    consumer_step_log = db_session.query(models.ProcessExecutionLog).filter(
        models.ProcessExecutionLog.workflow_run_id == workflow_run.id,
        models.ProcessExecutionLog.job_id.like(f"%_2_Consumer Step")
    ).one()

    assert consumer_step_log is not None
    assert consumer_step_log.status == "COMPLETED"
    # The return value of the wrapper is what we check
    assert "'return_value': 'Consumed: hello from workflow'" in consumer_step_log.stdout
