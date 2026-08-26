import platform
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/system/os", tags=["System"], summary="Get OS Information")
def get_os_info() -> Dict[str, Any]:
    """Returns the operating system type (e.g., 'Windows', 'Linux')."""
    return {"os_type": platform.system()}
