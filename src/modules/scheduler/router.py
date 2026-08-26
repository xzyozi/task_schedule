from fastapi import APIRouter

from modules.scheduler.routers import system, dashboard, filesystem, jobs, workflows, scheduler, config

router = APIRouter(prefix="/api")

router.include_router(system.router)
router.include_router(dashboard.router)
router.include_router(filesystem.router)
router.include_router(jobs.router)
router.include_router(workflows.router)
router.include_router(scheduler.router)
router.include_router(config.router)
