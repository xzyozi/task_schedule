from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import service
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter()

import jinja2

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@jinja2.pass_context
def _url_for(context: dict, name: str, **path_params: Any) -> str:
    """Flask 互換の url_for 関数。filename 引数を Starlette の path 引数に変換。"""
    request: Request = context["request"]
    if name == "static" and "filename" in path_params and "path" not in path_params:
        path_params["path"] = path_params.pop("filename")
    return str(request.url_for(name, **path_params))


templates.env.globals["url_for"] = _url_for


@router.get("/webgui-config", response_class=JSONResponse, name="webgui_config")
def webgui_config() -> Dict[str, str]:
    """フロントエンド JS に API のベース URL (同一オリジン) を返す。"""
    return {"API_BASE_URL": ""}


@router.get("/", response_class=HTMLResponse, name="index")
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """ダッシュボード画面。"""
    summary_data: Dict[str, Any] = {"total_jobs": 0, "running_jobs": 0, "successful_runs": 0, "failed_runs": 0}
    try:
        summary_obj = service.get_dashboard_summary(db)
        summary_data = summary_obj.model_dump()
    except Exception as e:
        logger.error(f"Failed to fetch dashboard summary for WebGUI: {e}", exc_info=True)

    return templates.TemplateResponse(
        request=request, name="index.html", context={"summary": summary_data}
    )


@router.get("/logs", response_class=HTMLResponse, name="logs")
def logs(request: Request) -> HTMLResponse:
    """実行ログ画面。"""
    return templates.TemplateResponse(request=request, name="logs.html")


@router.get("/jobs", response_class=HTMLResponse, name="jobs")
def jobs(request: Request) -> HTMLResponse:
    """ジョブ管理画面。"""
    return templates.TemplateResponse(request=request, name="jobs.html")


@router.get("/workflows", response_class=HTMLResponse, name="workflows")
def workflows(request: Request) -> HTMLResponse:
    """ワークフロー管理画面。"""
    return templates.TemplateResponse(request=request, name="workflows.html")


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse, name="workflow_detail")
def workflow_detail(request: Request, workflow_id: int) -> HTMLResponse:
    """ワークフロー詳細画面。"""
    return templates.TemplateResponse(
        request=request, name="workflow_detail.html", context={"workflow_id": workflow_id}
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse, name="job_detail")
def job_detail(request: Request, job_id: str) -> HTMLResponse:
    """ジョブ詳細画面。"""
    return templates.TemplateResponse(
        request=request, name="job_detail.html", context={"job_id": job_id}
    )


@router.get("/settings", response_class=HTMLResponse, name="settings")
def settings(request: Request) -> HTMLResponse:
    """設定画面。"""
    return templates.TemplateResponse(request=request, name="settings.html")
