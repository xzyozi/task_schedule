import os
import subprocess
import sys

def run_command(command: list[str]) -> None:
    """Helper to run a command and stream its output in real-time."""
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1 # Line-buffered
        )

        # Stream stdout
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                sys.stdout.flush()
        
        # Stream stderr
        if process.stderr:
            for line in iter(process.stderr.readline, ''):
                print(line, end='', file=sys.stderr)
                sys.stderr.flush()
            
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

    except FileNotFoundError:
        print(f"Error: Command '{command[0]}' not found. Please ensure it is installed and in the system's PATH.", file=sys.stderr)
        raise

def clone_or_pull_repo(repo_url: str):
    """
    Clones a git repository into the current working directory if it doesn't exist,
    or pulls the latest changes if it does.

    This function is designed to be called as a Python job step in a workflow.

    Args:
        repo_url: The URL of the git repository to clone or pull.
    """
    cwd = os.getcwd()
    git_dir = os.path.join(cwd, '.git')

    print(f"Executing git operation in working directory: {cwd}")

    try:
        if os.path.isdir(git_dir):
            print(f"Repository already exists. Pulling latest changes from {repo_url}...")
            run_command(['git', 'pull'])
        else:
            print(f"Cloning repository {repo_url} into current directory...")
            run_command(['git', 'clone', repo_url, '.'])
        
        print("Git operation completed successfully.")
        return "Git operation completed successfully."
    except subprocess.CalledProcessError as e:
        print(f"Error during git operation. Process exited with code {e.returncode}.", file=sys.stderr)
        # Re-raise the exception to ensure the scheduler marks the job as failed.
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        raise
