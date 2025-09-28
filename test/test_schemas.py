import pytest
from pydantic import ValidationError
from src.modules.scheduler.schemas import JobConfig

# Minimal valid job config for testing the validator
def get_minimal_job_config(**kwargs):
    base_config = {
        "id": "test_job",
        "func": "test.func",
        "trigger": {"type": "interval", "seconds": 10}
    }
    base_config.update(kwargs)
    return base_config

def test_validate_cwd_valid():
    """Tests that a valid relative path passes validation."""
    config = get_minimal_job_config(cwd="my/relative/path")
    job_config = JobConfig.model_validate(config)
    assert job_config.cwd == "my/relative/path"


def test_validate_cwd_none():
    """Tests that a None cwd passes validation."""
    config = get_minimal_job_config(cwd=None)
    job_config = JobConfig.model_validate(config)
    assert job_config.cwd is None


def test_validate_cwd_rejects_absolute_posix():
    """Tests that an absolute POSIX-style path is rejected."""
    with pytest.raises(ValidationError, match='CWD must be a relative path'):
        config = get_minimal_job_config(cwd="/an/absolute/path")
        JobConfig.model_validate(config)


def test_validate_cwd_rejects_absolute_windows():
    """Tests that an absolute Windows-style path is rejected."""
    with pytest.raises(ValidationError, match='CWD must be a relative path'):
        config = get_minimal_job_config(cwd="C:\\an\\absolute\\path")
        JobConfig.model_validate(config)


def test_validate_cwd_rejects_traversal():
    """Tests that a path with directory traversal is rejected."""
    with pytest.raises(ValidationError, match='CWD must be a relative path'):
        config = get_minimal_job_config(cwd="../some/path")
        JobConfig.model_validate(config)
