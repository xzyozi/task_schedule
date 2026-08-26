"""Playwright を使用した WebGUI の Python E2E ブラウザ自動化テスト。

TSK-TS-001 (WebGUIおよびJSテスト方針仕様書) Level 3 シナリオに対応。
"""

import threading
import time
import pytest
from fastapi.testclient import TestClient
import uvicorn

from main import app

SERVER_PORT = 8888
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


@pytest.fixture(scope="module")
def live_server():
    """E2Eテスト用に背景スレッドでローカルFastAPIサーバーを起動する。"""
    config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)  # サーバー起動待機
    yield BASE_URL
    server.should_exit = True


@pytest.mark.playwright
def test_e2e_dashboard_navigation(page, live_server):
    """E2E シナリオ 1: ダッシュボード画面へのアクセスと要素表示の検証。"""
    page.goto(live_server)

    # ページタイトルおよびメインヘッダーの検証
    assert "ダッシュボード" in page.title() or "タスクスケジューラ" in page.title()
    assert page.is_visible("h1")

    # サマリーカードの存在検証
    cards = page.locator(".card")
    assert cards.count() >= 4


@pytest.mark.playwright
def test_e2e_jobs_page_navigation(page, live_server):
    """E2E シナリオ 2: ジョブ管理画面への遷移とテーブル要素の確認。"""
    page.goto(f"{live_server}/jobs")

    assert page.is_visible("h1")
    # 検索フィルター入力要素の存在検証
    assert page.is_visible("input") or page.is_visible("table")


@pytest.mark.playwright
def test_e2e_workflows_page_navigation(page, live_server):
    """E2E ワークフロー管理画面へのアクセス検証。"""
    page.goto(f"{live_server}/workflows")
    assert page.is_visible("h1")


@pytest.mark.playwright
def test_e2e_settings_page_navigation(page, live_server):
    """E2E 設定画面へのアクセス検証。"""
    page.goto(f"{live_server}/settings")
    assert page.is_visible("h1")
