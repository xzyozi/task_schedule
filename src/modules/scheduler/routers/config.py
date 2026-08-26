from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from util.config_util import config, get_notification_settings, update_notification_settings
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)

@router.get("/ui", response_model=Dict[str, Any])
def get_ui_config():
    """
    Get the UI-specific configuration.
    """
    try:
        return config.task_ui_config
    except Exception as e:
        logger.error(f"Failed to retrieve UI configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve UI configuration")

@router.get("/notification-settings")
def get_settings():
    """
    Get current notification settings (email recipients, webhook URL).
    """
    try:
        settings = get_notification_settings()
        return settings
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get notification settings")

@router.post("/notification-settings")
def update_settings(
    settings: Dict[str, str] = Body(..., example={"email_recipients": "user@example.com", "webhook_url": "https://hooks.example.com/..."})
):
    """
    Update notification settings.
    """
    try:
        update_notification_settings(settings)
        return {"message": "Notification settings updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update notification settings")