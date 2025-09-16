from tenacity import retry, wait_fixed, stop_after_attempt, before_log, after_log, retry_if_exception_type

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base # Import declarative_base

from .config import settings
from util import logger

# Retry parameters
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds

# Define Base at module level
Base = declarative_base()

# These will be initialized by init_db
engine = None
SessionLocal = None

@retry(
    wait=wait_fixed(RETRY_DELAY),
    stop=stop_after_attempt(MAX_RETRIES),
    before=before_log(logger, 20), # INFO level
    after=after_log(logger, 30),  # WARNING level
    reraise=True,
    retry=retry_if_exception_type(OperationalError) # Only retry on OperationalError for connection
)
def _create_engine_with_retries():
    """
    Attempts to create the SQLAlchemy engine with retries on OperationalError.
    """
    logger.info("Attempting to connect to the database...")
    return create_engine(settings.DATABASE_URL)

def init_db():
    """
    Initializes the database and creates tables based on SQLAlchemy models, with retry logic for connection.
    """
    global engine, SessionLocal
    logger.info("Initializing database...")
    try:
        engine = _create_engine_with_retries()
        logger.info("Database engine created successfully.")

        # Create tables - this part doesn't typically need retries for connection issues
        # but might fail if the schema is invalid or permissions are wrong.
        # For now, we'll let it raise an exception immediately if it fails after connection.
        logger.info("Creating tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified.")

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SessionLocal created.")

    except Exception as e:
        logger.error(f"Failed to initialize database after {MAX_RETRIES} attempts (if connection failed): {e}")
        raise