"""API エラーハンドリングおよび基本エンドポイントのテスト。"""

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Task Scheduler Dashboard" in response.text


def test_read_job_not_found(client):
    response = client.get("/api/jobs/non_existent_job_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_create_job_missing_data(client):
    response = client.post("/api/jobs", json={})
    assert response.status_code == 422