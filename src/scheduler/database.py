import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base

# Create a synchronous engine instance
engine = create_engine(settings.DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initializes the database and creates tables based on SQLAlchemy models.
    """
    logging.info("Initializing database and creating tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Database initialization complete.")
    except Exception as e:
        logging.error(f"An error occurred during database initialization: {e}")
        raise
