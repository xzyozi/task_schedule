import sys
import time
import atexit

import uvicorn

from .database import init_db
from .loader import sync_jobs_from_db, seed_db_from_yaml, load_and_validate_jobs, apply_job_config, start_config_watcher
from .scheduler import start_scheduler, scheduler
from .main import app # Import the FastAPI app
from util import logger

def main():
    """The main entry point for the scheduler service."""
    # Initialize the database first, as both seeding and running need it.
    init_db()

    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'seed':
        config_path = "jobs.yaml"
        seed_db_from_yaml(config_path)
        return  # Exit after seeding

    # --- Default execution: start the scheduler and API ---
    start_scheduler()

    config_path = "jobs.yaml" # Define the path to your job configuration file

    # Load and apply initial job configurations from YAML
    logger.info(f"Loading initial job configurations from {config_path}...")
    initial_jobs = load_and_validate_jobs(config_path)
    if initial_jobs:
        apply_job_config(scheduler, initial_jobs)
        logger.info("Initial job configurations applied.")
    else:
        logger.warning("No initial job configurations loaded from YAML.")

    # Start watching the job configuration file for changes
    logger.info(f"Starting file watcher for {config_path}...")
    watcher = start_config_watcher(scheduler, config_path)
    atexit.register(lambda: watcher.stop())
    logger.info("File watcher started.")

    # Perform an initial sync on startup
    logger.info("Performing initial job sync...")
    try:
        sync_jobs_from_db()
    except Exception as e:
        logger.critical(f"Initial job sync failed: {e}", exc_info=True)

    # Schedule the sync function to run periodically
    scheduler.add_job(
        sync_jobs_from_db,
        "interval",
        seconds=60,  # This can be made configurable
        id="internal_db_sync",
        replace_existing=True,
    )
    logger.info("Scheduled periodic job sync every 60 seconds.")

    print("Scheduler and API started. Press Ctrl+C to exit.")

    # Start the FastAPI application using uvicorn
    # This call is blocking and will keep the main thread alive
    uvicorn.run("scheduler.main:app", host="0.0.0.0", port=8000, reload=True)

    # The atexit.register(shutdown_scheduler) in scheduler.py will handle cleanup
    # when the process exits (e.g., on Ctrl+C)
