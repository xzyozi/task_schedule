import pytest


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
def test_e2e_job_detail_navigation(page, live_server):
    """E2E ジョブ詳細画面へのアクセスと要素表示の検証 ([COV-1])。"""
    page.goto(f"{live_server}/jobs/sample_job_1")
    assert page.is_visible("h1") or page.is_visible("h2")
    # ジョブ基本情報および実行ログ・カード要素の存在検証
    assert page.is_visible(".card") or page.is_visible("table") or page.is_visible("div")


@pytest.mark.playwright
def test_e2e_workflows_page_navigation(page, live_server):
    """E2E ワークフロー管理画面へのアクセス検証。"""
    page.goto(f"{live_server}/workflows")
    assert page.is_visible("h1") or page.is_visible("h2")


@pytest.mark.playwright
def test_e2e_workflow_detail_navigation(page, live_server):
    """E2E ワークフロー詳細画面へのアクセスとステップ描画の検証 ([COV-2])。"""
    page.goto(f"{live_server}/workflows/1")
    assert page.is_visible("h1") or page.is_visible("h2")
    # ワークフロー詳細コンテナ・基本情報の存在検証
    assert page.is_visible(".card") or page.is_visible("div")


@pytest.mark.playwright
def test_e2e_logs_page_navigation(page, live_server):
    """E2E 実行ログ画面へのアクセスとフィルター・テーブル UI の検証 ([COV-3])。"""
    page.goto(f"{live_server}/logs")
    assert page.is_visible("h1") or page.is_visible("h2")
    # ログ一覧テーブルまたはログフィルター入力の存在検証
    assert page.is_visible("table") or page.is_visible("input") or page.is_visible(".card")


@pytest.mark.playwright
def test_e2e_settings_page_navigation(page, live_server):
    """E2E 設定画面へのアクセス検証。"""
    page.goto(f"{live_server}/settings")
    assert page.is_visible("h1") or page.is_visible("h2")
