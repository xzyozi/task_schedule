import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Mock config before it's imported by job_executors
from util.config_util import AppConfig

mock_config_instance = MagicMock(spec=AppConfig)
with patch.dict('sys.modules', {'util.config_util': MagicMock(config=mock_config_instance)}):
    from src.modules.scheduler.job_executors import execute_shell_command


@patch('subprocess.run')
def test_execute_shell_command_basic(mock_run):
    """Tests basic shell command execution without cwd or env."""
    mock_run.return_value = MagicMock(stdout="OK", stderr="", returncode=0)
    
    result = execute_shell_command("echo", "Hello")
    
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cwd"] is None
    assert result["exit_code"] == 0
    assert result["stdout"] == "OK"


@patch('os.environ.copy', return_value={"PARENT_VAR": "parent_value"})
@patch('subprocess.run')
def test_cwd_and_env_handling(mock_run, mock_env_copy):
    """Tests that cwd is resolved, created, and passed correctly, and env is merged."""
    # 1. Setup Mocks
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    
    # Mock the config to return a specific work_dir
    mock_base_path = MagicMock(spec=Path)
    mock_config_instance.scheduler_work_dir = mock_base_path
    
    # Mock the path resolution and creation
    mock_resolved_path = MagicMock(spec=Path)
    mock_base_path.joinpath.return_value.resolve.return_value = mock_resolved_path
    
    relative_cwd = "test_dir"
    test_env = {"CHILD_VAR": "child_value"}
    
    # 2. Call the function under test
    execute_shell_command("ls", cwd=relative_cwd, env=test_env)
    
    # 3. Assertions
    mock_base_path.joinpath.assert_called_with(relative_cwd)
    mock_resolved_path.mkdir.assert_called_with(parents=True, exist_ok=True)
    
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    
    # Assert that subprocess.run was called with the resolved absolute path
    assert call_kwargs["cwd"] == mock_resolved_path
    
    # Assert that the environment was correctly merged
    expected_env = {"PARENT_VAR": "parent_value", "CHILD_VAR": "child_value"}
    assert call_kwargs["env"] == expected_env


@patch('subprocess.run')
def test_file_not_found_error(mock_run):
    """Tests the handling of FileNotFoundError."""
    mock_run.side_effect = FileNotFoundError
    
    result = execute_shell_command("nonexistent_command")
    
    assert result["exit_code"] == 127
    assert "Command not found" in result["stderr"]


@patch('subprocess.run')
def test_permission_error(mock_run):
    """Tests the handling of PermissionError."""
    mock_run.side_effect = PermissionError
    
    # The absolute_cwd is now calculated inside the function, so we don't pass it directly.
    # We rely on the mock from the test_cwd_and_env_handling to simulate the path.
    result = execute_shell_command("cat", "file", cwd="some_dir")
    
    assert result["exit_code"] == 126
    assert "Permission denied" in result["stderr"]


@patch('subprocess.run')
def test_kwargs_passing(mock_run):
    """Tests that kwargs are correctly formatted and passed, while internal ones are skipped."""
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    
    execute_shell_command("my_script", "pos_arg", cwd="a_dir", env={"k": "v"}, custom_arg="value", job_id="123")
    
    mock_run.assert_called_once()
    call_args, _ = mock_run.call_args
    
    command_list = call_args[0]
    assert command_list[0] == "my_script"
    assert command_list[1] == "pos_arg"
    
    # Check that the custom kwarg is passed as --key value
    assert "--custom_arg" in command_list
    assert "value" in command_list
    
    # Check that internal kwargs (job_id, cwd, env) are NOT passed as command line args
    assert "--job_id" not in command_list
    assert "--cwd" not in command_list
    assert "--env" not in command_list
