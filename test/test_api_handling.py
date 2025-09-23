import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.core.database import Base, get_db

# --- Test Client and Database Fixture ---
@pytest.fixture(scope="function")
def test_client_with_db():
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

# --- Tests ---

def test_read_root(test_client_with_db):
    response = test_client_with_db.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Task Scheduler API"}

def test_read_job_not_found(test_client_with_db):
    response = test_client_with_db.get("/api/jobs/non_existent_job_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}

def test_create_job_missing_data(test_client_with_db):
    response = test_client_with_db.post("/api/jobs", json={})
    assert response.status_code == 422