from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core import database
from util import logger_util
from util.config_util import config
from modules.scheduler.router import router as scheduler_router
from modules.scheduler import scheduler_instance, loader

logger_util.setup_logging(log_file_path="log/app.log")
logger = logger_util.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    database.init_db()
    database.Base.metadata.create_all(bind=database.engine)
    loader.seed_db_from_yaml("jobs.yaml")
    scheduler_instance.start_scheduler()
    loader.sync_jobs_from_db()
    loader.sync_workflows_from_db()
    watcher = loader.start_config_watcher(scheduler_instance.scheduler, "jobs.yaml")
    if config.enable_db_sync:
        scheduler_instance.scheduler.add_job(loader.sync_jobs_from_db, "interval", seconds=60, id="db_sync", replace_existing=True)
    yield
    logger.info("Application shutdown...")
    watcher.stop()
    watcher.join()
    scheduler_instance.shutdown_scheduler()

app = FastAPI(title="Task Scheduler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.webgui_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scheduler_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Task Scheduler API"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        reload_includes=["*.yaml"],
    )
