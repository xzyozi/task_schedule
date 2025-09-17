import subprocess
import sys
import os
from util import logger

def start_flask_webgui(port: int = 5000):
    """Starts the Flask WebGUI as a subprocess."""
    logger.info(f"Attempting to start Flask WebGUI on port {port}...")
    try:
        # Set FLASK_APP environment variable to the module path
        env = os.environ.copy()
        env['FLASK_APP'] = 'webgui.app' # Reference the Flask app by its module path
        env['FLASK_RUN_PORT'] = str(port)

        # Use sys.executable to ensure the correct Python interpreter is used
        # The -m flask run command is more robust than direct script execution
        process = subprocess.Popen(
            [sys.executable, "-m", "flask", "run", "--host", "0.0.0.0", "--port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True # Capture output as text
        )
        logger.info(f"Flask WebGUI process started with PID: {process.pid}")
        # You might want to store the process object or PID if you need to manage it later
        # For now, just log its startup.

        # Read stdout/stderr in a non-blocking way or in separate threads if needed
        # For simplicity, we'll just log a message indicating it's running.
        # The Flask app will keep running in its own process.

    except Exception as e:
        logger.error(f"Failed to start Flask WebGUI: {e}", exc_info=True)


if __name__ == '__main__':
    # Example usage if run directly
    start_flask_webgui(port=5001)
