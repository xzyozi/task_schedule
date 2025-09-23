from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from tenacity import retry, wait_fixed, stop_after_attempt, before_log, after_log, retry_if_exception_type

import logging

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = None
SessionLocal = None

@retry(
    wait=wait_fixed(3),
    stop=stop_after_attempt(5),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARNING),
    reraise=True,
    retry=retry_if_exception_type(OperationalError)
)
def _create_engine_with_retries():
    logger.info("Attempting to connect to the database...")
    return create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

def init_db():
    global engine, SessionLocal
    if engine is None:
        logger.info("Initializing database...")
        try:
            engine = _create_engine_with_retries()
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}", exc_info=True)
            raise

def get_db() -> Generator[sessionmaker, None, None]:
    if SessionLocal is None:
        init_db()
    
    if SessionLocal is None:
         raise RuntimeError("Database could not be initialized.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
