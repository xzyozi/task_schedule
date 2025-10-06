import os
import subprocess
import sys
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
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True, encoding='utf-8')
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
        else:
            print(f"Cloning repository {repo_url} into current directory...")
            result = subprocess.run(['git', 'clone', repo_url, '.'], capture_output=True, text=True, check=True, encoding='utf-8')
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
        
        print("Git operation completed successfully.")
        return "Git operation completed successfully."
    except subprocess.CalledProcessError as e:
        print(f"Error during git operation. Process exited with code {e.returncode}.", file=sys.stderr)
        print(f"STDOUT: {e.stdout}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        # Re-raise the exception to ensure the scheduler marks the job as failed.
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        raise