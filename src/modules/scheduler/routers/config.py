from fastapi import APIRouter, HTTPException

from util import logger_util, config_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

@router.get("/jobs_yaml", tags=["Configuration"])
def get_jobs_yaml_content():
    try:
        content = config_util.read_jobs_yaml_content()
        return {"content": content}
    except FileNotFoundError as e:
        logger.error(f"Error reading jobs.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading jobs.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read jobs.yaml")

@router.get("/settings/notifications", tags=["Settings"])
def get_notification_settings():
    try:
        settings = config_util.get_notification_settings()
        return settings
    except IOError as e:
        logger.error(f"Error reading notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read notification settings: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while reading notification settings.")

@router.post("/settings/notifications", tags=["Settings"])
def update_notification_settings(email_recipients: str = "", webhook_url: str = ""):
    settings = {
        "email_recipients": email_recipients,
        "webhook_url": webhook_url
    }
    try:
        config_util.update_notification_settings(settings)
        return {"message": "Notification settings updated successfully."}
    except IOError as e:
        logger.error(f"Error writing notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update notification settings: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while writing notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating notification settings.")
