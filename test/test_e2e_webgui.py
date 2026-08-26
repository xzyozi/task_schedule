"""Playwright を使用した WebGUI の Python E2E ブラウザ自動化テスト。

TSK-TS-001 (WebGUIおよびJSテスト方針仕様書) Level 3 シナリオに対応。
"""

import threading
import time
import pytest
from fastapi.testclient import TestClient
import uvicorn

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app

SERVER_PORT = 8888
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


@pytest.fixture(scope="module")
def live_server():
    """E2Eテスト用にインメモリDBオーバーライドを設定し背景スレッドでローカルFastAPIサーバーを起動する。"""
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

    config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)  # サーバー起動待機
    yield BASE_URL
    server.should_exit = True
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.playwright
def test_e2e_dashboard_navigation(page, live_server):
    """E2E シナリオ 1: ダッシュボード画面へのアクセスと要素表示の検証。"""
    page.goto(live_server)

    # ページタイトルおよびメインヘッダーの検証
    assert "Dashboard" in page.title() or "ダッシュボード" in page.title() or "Task Scheduler" in page.title()
    assert page.is_visible("h1") or page.is_visible("h2")

    # サマリーカードの存在検証
    cards = page.locator(".card")
    assert cards.count() >= 1


@pytest.mark.playwright
def test_e2e_jobs_page_navigation(page, live_server):
    """E2E シナリオ 2: ジョブ管理画面への遷移とテーブル要素の確認。"""
    page.goto(f"{live_server}/jobs")

    assert page.is_visible("h1") or page.is_visible("h2")
    # 検索フィルター入力要素の存在検証
    assert page.is_visible("input") or page.is_visible("table")


@pytest.mark.playwright
def test_e2e_workflows_page_navigation(page, live_server):
    """E2E ワークフロー管理画面へのアクセス検証。"""
    page.goto(f"{live_server}/workflows")
    assert page.is_visible("h1") or page.is_visible("h2")


@pytest.mark.playwright
def test_e2e_settings_page_navigation(page, live_server):
    """E2E 設定画面へのアクセス検証。"""
    page.goto(f"{live_server}/settings")
    assert page.is_visible("h1") or page.is_visible("h2")
