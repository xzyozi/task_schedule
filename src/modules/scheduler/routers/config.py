from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from util import logger_util
from util.config_util import config, get_notification_settings, update_notification_settings

logger = logger_util.get_logger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)


@router.get("/ui", response_model=Dict[str, Any])
def get_ui_config() -> Dict[str, Any]:
    """
    Get the UI-specific configuration.
    """
    try:
        return config.task_ui_config
    except Exception as e:
        logger.error(f"Failed to retrieve UI configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve UI configuration")


@router.get("/notification-settings")
def get_settings() -> Dict[str, Any]:
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
    settings: Dict[str, str] = Body(
        ..., example={"email_recipients": "user@example.com", "webhook_url": "https://hooks.example.com/..."}
    ),
) -> Dict[str, str]:
    """
    Update notification settings.
    """
    try:
        update_notification_settings(settings)
        return {"message": "Notification settings updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update notification settings")
