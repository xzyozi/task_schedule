import argparse
import uvicorn

def main():
    """The main entry point for the scheduler service."""
    parser = argparse.ArgumentParser(description="Resilient Task Scheduler CLI.")
    # This file is now only a lightweight launcher for the Uvicorn process.
    # Application setup (DB, scheduler, etc.) is handled in main.py's lifespan.
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the API server on."
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to run the API server on."
    )
    args = parser.parse_args()

    uvicorn.run(
        "scheduler.main:app",
        host=args.host,
        port=args.port,
    )
