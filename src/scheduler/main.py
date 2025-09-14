from typing import Generator

from fastapi import FastAPI
from sqlalchemy.orm import Session

from .database import SessionLocal

app = FastAPI(title="Resilient Task Scheduler API")

# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Resilient Task Scheduler API!"}
