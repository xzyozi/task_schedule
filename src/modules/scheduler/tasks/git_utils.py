import os
import subprocess
import sys
from util.process_util import run_command

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