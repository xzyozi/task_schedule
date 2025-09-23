from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core import database
from util import logger_util
from modules.scheduler.router import router as scheduler_router
from modules.scheduler import service, loader

logger_util.setup_logging(log_file_path="log/app.log")
logger = logger_util.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    database.init_db()
    database.Base.metadata.create_all(bind=database.engine)
    loader.seed_db_from_yaml("jobs.yaml")
    service.start_scheduler()
    loader.sync_jobs_from_db()
    watcher = loader.start_config_watcher(service.scheduler, "jobs.yaml")
    service.scheduler.add_job(loader.sync_jobs_from_db, "interval", seconds=60, id="db_sync")
    yield
    logger.info("Application shutdown...")
    watcher.stop()
    watcher.join()
    service.shutdown_scheduler()

app = FastAPI(title="Task Scheduler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5012", "http://127.0.0.1:5012"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(scheduler_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Task Scheduler API"}
