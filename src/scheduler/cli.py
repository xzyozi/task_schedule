import time
import logging

from .loader import load_jobs_from_config
from .scheduler import start_scheduler, scheduler

CONFIG_PATH = "jobs.yaml"

def main():
    """The main entry point for the scheduler service."""
    start_scheduler()
    load_jobs_from_config(scheduler, CONFIG_PATH)

    print("Scheduler started. Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive
        while scheduler.running:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped by user.")
        # The shutdown hook registered in start_scheduler will handle cleanup
        pass

if __name__ == "__main__":
    main()
