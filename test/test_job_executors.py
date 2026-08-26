import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from modules.scheduler.job_executors import _execute_subprocess, _split_shell_command


@patch('subprocess.run')
def test_execute_subprocess_basic(mock_run):
    """Tests basic subprocess execution without cwd or env."""
    mock_run.return_value = MagicMock(stdout="OK", stderr="", returncode=0)
    
    result = _execute_subprocess(["echo", "Hello"])
    
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cwd"] is None
    assert result["exit_code"] == 0
    assert result["stdout"] == "OK"


@patch('os.environ.copy', return_value={"PARENT_VAR": "parent_value"})
@patch('util.config_util.config.resolve_sandboxed_path')
@patch('subprocess.run')
def test_cwd_and_env_handling(mock_run, mock_resolve_path, mock_env_copy):
    """Tests that cwd is resolved, created, and passed correctly, and env is merged."""
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    
    mock_resolved_path = MagicMock(spec=Path)
    mock_resolve_path.return_value = mock_resolved_path
    
    relative_cwd = "test_dir"
    test_env = {"CHILD_VAR": "child_value"}
    
    result = _execute_subprocess(["ls"], cwd=relative_cwd, env=test_env)
    
    mock_resolve_path.assert_called_with(relative_cwd)
    mock_resolved_path.mkdir.assert_called_with(parents=True, exist_ok=True)
    
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    
    assert call_kwargs["cwd"] == mock_resolved_path
    expected_env = {"PARENT_VAR": "parent_value", "CHILD_VAR": "child_value"}
    assert call_kwargs["env"] == expected_env


@patch('subprocess.run')
def test_file_not_found_error(mock_run):
    """Tests the handling of FileNotFoundError."""
    mock_run.side_effect = FileNotFoundError
    
    result = _execute_subprocess(["nonexistent_command"])
    
    assert result["exit_code"] == 127
    assert "Command not found" in result["stderr"]


def test_split_shell_command():
    """Tests shell command splitting for Windows paths."""
    cmd = r'python "C:\Program Files\script.py" --arg value'
    parts = _split_shell_command(cmd)
    assert parts == ['python', r'C:\Program Files\script.py', '--arg', 'value']
