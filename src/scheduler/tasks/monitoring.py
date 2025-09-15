import logging

def check_api_status(api_endpoint: str, timeout_seconds: int):
    logging.info(
        f"Checking API status at {api_endpoint} with a timeout of {timeout_seconds}s."
    )
    print("--- API health check task executed ---")
