from fastapi import APIRouter

from modules.scheduler.routers import config, dashboard, filesystem, jobs, scheduler, system, workflows

router = APIRouter(prefix="/api")

router.include_router(system.router)
router.include_router(dashboard.router)
router.include_router(filesystem.router)
router.include_router(jobs.router)
router.include_router(workflows.router)
router.include_router(scheduler.router)
router.include_router(config.router)
