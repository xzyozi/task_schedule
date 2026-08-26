import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from tenacity import after_log, before_log, retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = None
SessionLocal = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enables WAL mode for SQLite databases to improve concurrency."""
    # This check is to ensure this pragma is only set for SQLite databases
    if dbapi_connection.__class__.__module__ == "sqlite3":
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()
            logger.info("SQLite journal_mode set to WAL.")
        except Exception as e:
            logger.warning(f"Could not set journal_mode to WAL: {e}")


@retry(
    wait=wait_fixed(3),
    stop=stop_after_attempt(5),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARNING),
    reraise=True,
    retry=retry_if_exception_type(OperationalError),
)
def _create_engine_with_retries():
    logger.info("Attempting to connect to the database...")
    return create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 15})


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
