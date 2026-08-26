"""共通 Pytest フィクスチャおよびテストヘルパー定義。

複数のテストファイルで重複していた DB セッション、FastAPI TestClient、
および Playwright E2E ライブサーバーを conftest.py に集約。
"""

import socket
import threading
import time
from typing import Any, Generator

import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app

SERVER_PORT = 8888
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    """指定されたポートでサーバーがリスニング状態になるまで待機するヘルパー関数。"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.05)
    return False


@pytest.fixture(scope="function")
def db_engine() -> Generator[Any, None, None]:
    """テスト用 SQLite インメモリ DB エンジン。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine: Any) -> Generator[Session, None, None]:
    """テスト用クリーンな DB セッション。"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_engine: Any) -> Generator[TestClient, None, None]:
    """FastAPI TestClient (インメモリ DB オーバーライド適用済み)。"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db() -> Generator[Session, None, None]:
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def live_server() -> Generator[str, None, None]:
    """E2Eテスト用ライブFastAPIサーバー。ソケット接続による起動完了検知を行う。"""
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # time.sleep(1.5) の代わりにソケットポーリングで起動を動的検知
    if not wait_for_port(SERVER_PORT, timeout=5.0):
        raise RuntimeError("FastAPI live server failed to start within timeout.")

    yield BASE_URL

    server.should_exit = True
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
