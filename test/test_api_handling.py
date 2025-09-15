import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool # Use StaticPool for in-memory SQLite
import os
import sys

# srcディレクトリをパスに追加して、schedulerモジュールをインポートできるようにします
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scheduler.main import app, get_db
from scheduler.database import Base
import scheduler.models # モデルをBase.metadataに登録するためにインポート

# --- テスト用クライアントとデータベースのフィクスチャ ---
@pytest.fixture(scope="function")
def test_client_with_db():
    # 各テストのために新しいインメモリSQLiteデータベースを作成します
    # StaticPoolを使用することで、複数のスレッドから同じ接続を共有できます
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # モデルをBase.metadataに登録するためにインポートを確実に行います
    # import scheduler.models # 既にファイルの先頭でインポートされているため不要

    # テーブルを作成します
    Base.metadata.create_all(bind=engine)

    # 依存性を上書きします
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # テストクライアントをyieldします
    with TestClient(app) as client:
        yield client

    # テスト後にテーブルを削除し、依存性の上書きを元に戻します
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear() # 依存性の上書きをクリア

# --- テスト ---

def test_read_root(test_client_with_db):
    """ルートエンドポイントをテストします（JSONレスポンスを期待）。"""
    response = test_client_with_db.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Resilient Task Scheduler API!"}

def test_read_job_not_found(test_client_with_db):
    """
    存在しないジョブをリクエストした際に404 Not Foundエラーが返されることをテストします。
    これはAPIエラーハンドリングの確認テストです。
    """
    response = test_client_with_db.get("/jobs/non_existent_job_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}

def test_create_job_missing_data(test_client_with_db):
    """
    不足しているPydanticモデルデータでジョブを作成しようとした際に、422 Unprocessable Entityエラーが返されることをテストします。
    これは入力バリデーションハンドリングの確認テストです。
    """
    # 空のJSONボディをPOSTします。'id', 'func', 'trigger'はJobConfigで必須です。
    response = test_client_with_db.post("/jobs", json={})
    
    assert response.status_code == 422
    
    error_details = response.json()["detail"]
    
    # エラー詳細に特定の必須フィールドが含まれているかを確認
    # 'id', 'func', 'trigger'の各フィールドのエラーを期待します
    expected_missing_fields = {"id", "func", "trigger"}
    actual_missing_fields = set()
    for err in error_details:
        if "loc" in err and len(err["loc"]) >= 2 and err["loc"][0] == "body":
            actual_missing_fields.add(err["loc"][1])
    
    assert expected_missing_fields.issubset(actual_missing_fields)
