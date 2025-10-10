from typing import List
from fastapi import APIRouter, HTTPException, Query

from modules.scheduler import service
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

@router.get("/filesystem/list-dirs", response_model=List[str], tags=["Filesystem"], summary="List Subdirectories in Work Directory")
def list_work_dir_subdirectories(path: str = Query("", description="The relative path within the work directory to scan.")):
    """
    Lists subdirectories within the configured scheduler work_dir.
    This is useful for providing autocompletion for the 'cwd' field in a UI.
    """
    try:
        return service.list_subdirectories(relative_path=path)
    except Exception as e:
        logger.error(f"Error listing subdirectories for path '{path}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list directories")
