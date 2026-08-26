"""WebGUI ルーティングおよび HTML テンプレートレンダリングのテスト。"""


def test_webgui_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "ダッシュボード" in response.text


def test_webgui_job_detail_page(client):
    response = client.get("/jobs/test_job_123")
    assert response.status_code == 200
    assert "test_job_123" in response.text


def test_webgui_workflow_detail_page(client):
    response = client.get("/workflows/1")
    assert response.status_code == 200
    assert "ワークフロー" in response.text or "Workflow" in response.text


def test_webgui_logs_page(client):
    response = client.get("/logs")
    assert response.status_code == 200
    assert "実行ログ" in response.text


def test_webgui_jobs_page(client):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert "ジョブ管理" in response.text


def test_webgui_workflows_page(client):
    response = client.get("/workflows")
    assert response.status_code == 200
    assert "ワークフロー" in response.text


def test_webgui_settings_page(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert "設定" in response.text


def test_webgui_config_endpoint(client):
    response = client.get("/webgui-config")
    assert response.status_code == 200
    assert response.json() == {"API_BASE_URL": ""}
