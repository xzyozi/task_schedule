"""ワークフローのステップ設定・パラメータ定義・CRUD API の包括的テスト。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app


@pytest.fixture(scope="function")
def client():
    """インメモリ SQLite データベースを使用するテストクライアント。"""
    engine = create_engine(
        "sqlite:///:memory:",
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

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_get_available_tasks(client):
    """`/api/available-tasks` がワークフロー構築に必要なタスク定義（Python, Shell等）を返却することを確認する。"""
    response = client.get("/api/available-tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    # 必須フィールドの検証
    for task in tasks:
        assert "id" in task
        assert "name" in task
        assert "task_type" in task
        assert "parameters" in task


def test_workflow_create_with_complex_step_configurations(client):
    """
    動的パラメータ定義（params_def）および複数ステップ（python/shell, on_failure, run_in_background）を
    含むワークフローが正しく作成・保存されることを確認する。
    """
    payload = {
        "name": "Complex Step Workflow",
        "description": "ステップ設定と動的パラメータのテスト",
        "schedule": "0 12 * * *",
        "is_enabled": True,
        "params_def": [
            {"name": "input_dir", "label": "入力ディレクトリ"},
            {"name": "retry_limit", "label": "リトライ回数上限"},
        ],
        "steps": [
            {
                "step_order": 1,
                "name": "Step 1: Python Data Processing",
                "task_parameters": {
                    "task_type": "python",
                    "module": "modules.sample",
                    "function": "process_data",
                    "args": ["input_dir"],
                },
                "on_failure": "continue",
                "run_in_background": False,
            },
            {
                "step_order": 2,
                "name": "Step 2: Shell Cleanup",
                "task_parameters": {
                    "task_type": "shell",
                    "command": "echo 'Cleanup complete'",
                },
                "on_failure": "stop",
                "run_in_background": True,
            },
        ],
    }

    response = client.post("/api/workflows", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "Complex Step Workflow"
    assert len(data["params_def"]) == 2
    assert len(data["steps"]) == 2

    # ステップ1の個別設定検証
    step1 = sorted(data["steps"], key=lambda x: x["step_order"])[0]
    assert step1["name"] == "Step 1: Python Data Processing"
    assert step1["on_failure"] == "continue"
    assert step1["run_in_background"] is False

    # ステップ2の個別設定検証
    step2 = sorted(data["steps"], key=lambda x: x["step_order"])[1]
    assert step2["name"] == "Step 2: Shell Cleanup"
    assert step2["on_failure"] == "stop"
    assert step2["run_in_background"] is True


def test_workflow_update_step_configurations(client):
    """既存のワークフローのステップ設定（順序変更・ステップ削除・パラメータ更新）が正常に行われることを検証する。"""
    # 1. 初期ワークフローの作成
    initial_payload = {
        "name": "Initial Workflow",
        "description": "初期定義",
        "schedule": "0 0 * * *",
        "is_enabled": True,
        "steps": [
            {
                "step_order": 1,
                "name": "Original Step 1",
                "task_parameters": {"task_type": "shell", "command": "echo 1"},
                "on_failure": "stop",
                "run_in_background": False,
            }
        ],
    }
    create_res = client.post("/api/workflows", json=initial_payload)
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    # 2. ステップ設定の更新 (ステップ追加と設定変更)
    update_payload = {
        "name": "Updated Workflow",
        "description": "更新後の説明",
        "schedule": "*/15 * * * *",
        "is_enabled": False,
        "params_def": [{"name": "target_env", "label": "対象環境"}],
        "steps": [
            {
                "step_order": 1,
                "name": "Updated Step 1",
                "task_parameters": {"task_type": "shell", "command": "echo updated"},
                "on_failure": "continue",
                "run_in_background": True,
            },
            {
                "step_order": 2,
                "name": "New Step 2",
                "task_parameters": {"task_type": "shell", "command": "echo step2"},
                "on_failure": "stop",
                "run_in_background": False,
            },
        ],
    }

    update_res = client.put(f"/api/workflows/{wf_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()

    assert updated_data["name"] == "Updated Workflow"
    assert updated_data["is_enabled"] is False
    assert len(updated_data["steps"]) == 2


def test_workflow_create_duplicate_name_fails(client):
    """同名のワークフロー重複作成時に 409 Conflict エラーが返ることを確認する。"""
    payload = {
        "name": "Duplicate Test Workflow",
        "description": "重複テスト",
        "schedule": "0 0 * * *",
        "is_enabled": True,
        "steps": [],
    }

    res1 = client.post("/api/workflows", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/workflows", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]
