import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app


@pytest.fixture(scope="function")
def test_client():
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


def test_webgui_index_page(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert "ダッシュボード" in response.text


def test_webgui_job_detail_page(test_client):
    response = test_client.get("/jobs/test_job_123")
    assert response.status_code == 200
    assert "test_job_123" in response.text


def test_webgui_workflow_detail_page(test_client):
    response = test_client.get("/workflows/1")
    assert response.status_code == 200


def test_webgui_logs_page(test_client):
    response = test_client.get("/logs")
    assert response.status_code == 200
    assert "実行ログ" in response.text or "logs" in response.text.lower()


def test_webgui_jobs_page(test_client):
    response = test_client.get("/jobs")
    assert response.status_code == 200
    assert "ジョブ管理" in response.text or "job" in response.text.lower()


def test_webgui_workflows_page(test_client):
    response = test_client.get("/workflows")
    assert response.status_code == 200
    assert "ワークフロー" in response.text or "workflow" in response.text.lower()


def test_webgui_settings_page(test_client):
    response = test_client.get("/settings")
    assert response.status_code == 200
    assert "設定" in response.text or "settings" in response.text.lower()


def test_webgui_config_endpoint(test_client):
    response = test_client.get("/webgui-config")
    assert response.status_code == 200
    assert response.json() == {"API_BASE_URL": ""}
