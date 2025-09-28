import pytest
import os
from unittest.mock import patch, MagicMock
from src.modules.scheduler.job_executors import execute_shell_command

@patch('subprocess.run')
def test_execute_shell_command_basic(mock_run):
    """Tests basic shell command execution."""
    mock_run.return_value = MagicMock(stdout="OK", stderr="", returncode=0)
    
    result = execute_shell_command("echo", "Hello")
    
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args
    assert call_args[0] == ["echo", "Hello"]
    assert result["exit_code"] == 0
    assert result["stdout"] == "OK"

@patch('os.environ.copy')
@patch('subprocess.run')
def test_execute_shell_command_with_cwd_and_env(mock_run, mock_environ_copy):
    """Tests that cwd and env are correctly passed to subprocess.run."""
    mock_environ_copy.return_value = {"PARENT_VAR": "parent_value"}
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    
    test_cwd = "/tmp/test"
    test_env = {"CHILD_VAR": "child_value"}
    
    execute_shell_command("ls", "-l", cwd=test_cwd, env=test_env)
    
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    
    assert call_kwargs["cwd"] == test_cwd
    
    expected_env = {"PARENT_VAR": "parent_value", "CHILD_VAR": "child_value"}
    assert call_kwargs["env"] == expected_env

@patch('subprocess.run')
def test_execute_shell_command_file_not_found(mock_run):
    """Tests the handling of FileNotFoundError."""
    mock_run.side_effect = FileNotFoundError
    
    result = execute_shell_command("nonexistent_command")
    
    assert result["exit_code"] == 127
    assert "Command not found" in result["stderr"]

@patch('subprocess.run')
def test_execute_shell_command_permission_error(mock_run):
    """Tests the handling of PermissionError."""
    mock_run.side_effect = PermissionError
    
    test_cwd = "/root/secret"
    result = execute_shell_command("cat", "file", cwd=test_cwd)
    
    assert result["exit_code"] == 126
    assert "Permission denied" in result["stderr"]
    assert test_cwd in result["stderr"]

@patch('subprocess.run')
def test_command_with_kwargs(mock_run):
    """Tests that kwargs are correctly formatted and passed, while internal ones are skipped."""
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    
    execute_shell_command("my_script", "pos_arg", cwd="/tmp", custom_arg="value", job_id="123")
    
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args
    
    # Check that positional args are correct
    assert call_args[0][0] == "my_script"
    assert call_args[0][1] == "pos_arg"
    
    # Check that the custom kwarg is passed as --key value
    assert "--custom_arg" in call_args[0]
    assert "value" in call_args[0]
    
    # Check that internal kwargs (job_id, cwd, env) are NOT passed as command line args
    assert "--job_id" not in call_args[0]
    assert "--cwd" not in call_args[0]
    
    # Check that cwd was passed as a kwarg to subprocess.run
    assert call_kwargs["cwd"] == "/tmp"
