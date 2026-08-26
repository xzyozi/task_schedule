
-----

# **再利用性のためのリファクタリング：モジュラーアプローチ**

## 1\. はじめに＆設計思想

### **目標**

このリファクタリングの主な目的は、汎用的なアプリケーションフレームワークを、特定のドメインロジック（この場合はタスクスケジューリング）から完全に分離することです。`WebUI <-> FastAPI <-> データベース` というアーキテクチャパターンに基づいた、将来のアプリケーション開発で即座に再利用可能な、堅牢な「開発基盤」を構築することを目指します。

### **中心的な思想**

  - **機能は自己完結したモジュールである**: 「タスクスケジューリング」「通知」「ユーザー管理」のような個別の機能は、それぞれ専用のディレクトリに隔離します。このモジュールには、APIエンドポイント、ビジネスロジック、データベースモデル、APIスキーマ、そしてテストコードまで、その機能に関連するすべてが含まれます。
  - **`core`はドメインに依存しない**: アプリケーションの骨格（データベース接続、設定管理、汎用ヘルパーなど）を提供する`core`ライブラリを作成します。この`core`は、自身がどの特定の機能（ドメイン）を実行しているかを一切意識しません。これにより、`core`はどのプロジェクトにも持ち運び可能になります。
  - **依存性の注入（Dependency Injection）**: FastAPIの強力なDIシステムを全面的に活用し、データベースセッションや設定オブジェクトなどを各レイヤーに渡します。これにより、コンポーネントの疎結合が促進され、テストが極めて容易になります。

### **この設計が解決する問題（アンチパターン）**

  - **モノリシックな巨大ファイル**: すべてのAPIエンドポイントが `main.py` に記述され、数百、数千行に膨れ上がることを防ぎます。
  - **密結合なコード**: ある機能のモデルやロジックを別の機能が直接的かつ無秩序に参照し、変更が他に影響を及ぼす「スパゲッティコード」化を回避します。
  - **責任の所在が不明確**: どこに何が書かれているか分からなくなり、機能追加やデバッグの際に調査コストが増大する状況を防ぎます。

### **メリット**

  - **再利用性**: `core`と`webgui`を新しいプロジェクトにコピーするだけで、アプリケーション開発のスタートダッシュを切れます。
  - **保守性**: 機能ごとにコードが整理されているため、担当者が目的のコードを素早く見つけ、安全に修正できます。
  - **拡張性**: 既存のコードベースを一切変更することなく、新しいディレクトリを作成するだけで新機能を追加できます。
  - **関心の分離**: フレームワーク、各機能、UIの間に明確な境界が引かれ、それぞれの開発に集中できます。
  - **テスト容易性**: 機能モジュールを個別にテストすることができ、CI/CDプロセスとの親和性が高まります。

-----

## 2\. 提案アーキテクチャ (詳細解説版)

`src`ディレクトリを以下のように再構築します。ここでは各コンポーネントの責務と、それらがどのように連携するのかをより詳細に解説します。

```
src/
├── core/                  # 再利用可能で、ドメインに依存しないアプリケーションの骨格
│   ├── config.py          # ✅ 環境変数を管理するPydantic設定クラス
│   ├── database.py        # 汎用的なSQLAlchemyの設定（engine, SessionLocal, Base, get_db）
│   ├── crud.py            # ✅ 汎用的なCRUD操作のベースクラス (CRUDBase)
│   └── dependencies.py    # ✅ 共通の依存関係（例：認証ユーザー取得）
│
├── modules/               # すべての自己完結した機能モジュールを格納する場所
│   ├── scheduler/
│   │   └── ...
│   └── notes/             # 今回追加する「ノート」機能
│       ├── __init__.py
│       ├── router.py      # APIエンドポイントの定義
│       ├── models.py      # SQLAlchemyモデル
│       ├── schemas.py     # Pydanticスキーマ
│       ├── service.py     # ビジネスロジック (core.crud.CRUDBaseを継承)
│       └── tests/         # このモジュール専用のテストコード
│           ├── test_router.py
│           └── test_service.py
│
├── webgui/                # Web UI
│   └── ...
│
└── main.py                # アプリケーションのメインエントリーポイント
```

-----

### **`core`コンポーネントの深掘り**

`core`はアプリケーションの心臓部であり、ドメイン知識を持つべきではありません。

#### **`core/config.py`: 設定管理**

Pydanticの`BaseSettings`を使い、環境変数や`.env`ファイルから設定を安全に読み込みます。これにより、設定値の型が保証され、コード補完も効くようになります。

```python
# src/core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # .envファイルから読み込む設定
    DATABASE_URL: str = "sqlite:///./default.db"
    SECRET_KEY: str = "your-secret-key"
    
    # 直接定義する設定
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "My Modular App"

    class Config:
        env_file = ".env" # .envファイルを読み込む設定

# アプリケーション全体でこのインスタンスをインポートして使用
settings = Settings()
```

#### **`core/crud.py`: 汎用CRUDクラスの実装**

多くのモジュールで必要となる基本的なCRUD操作を抽象化した`CRUDBase`クラスを提供します。これにより、各モジュールの`service.py`での定型的なコードを大幅に削減できます。

```python
# src/core/crud.py
from typing import Any, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import Base

# SQLAlchemyモデルとPydanticスキーマの型変数を定義
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        特定のSQLAlchemyモデルに対するCRUDオブジェクト。
        
        :param model: SQLAlchemyモデルクラス
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        obj_data = db_obj.__dict__
        update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
```

-----

### **`modules`コンポーネントの設計パターン**

#### **モジュール間の連携方法**

モジュールは自己完結しているべきですが、時には連携が必要になります。例えば、「タスク完了時に通知を送る」ケースを考えます。

**悪い例 ❌**: `scheduler`モジュールが`notifications`モジュールのモデルやルーターを直接インポートする。
**良い例 ✅**: `scheduler`モジュールは、`notifications`モジュールの\*\*`service.py`\*\*に定義されたインターフェース（関数）を呼び出します。

```python
# src/modules/notifications/service.py
# ... (他のコード)
def send_system_notification(db: Session, message: str, user_id: int):
    # 通知を作成し、DBに保存するロジック
    pass

# src/modules/scheduler/service.py
from sqlalchemy.orm import Session
# 他のモジュールのserviceをインポート
from modules.notifications import service as notification_service

def run_job(db: Session, job_id: int):
    # ... ジョブ実行ロジック ...
    
    # ジョブ完了後、notificationサービスを呼び出して通知を送る
    notification_service.send_system_notification(
        db=db,
        message=f"ジョブ {job_id} が完了しました。",
        user_id=1 # 仮のユーザーID
    )
    return {"status": "completed"}
```

この設計により、`notifications`モジュールの内部実装（APIの仕様やDBモデルの変更）が`scheduler`モジュールに影響を与えることを防ぎます。

-----

-----

## 3\. 開発者ガイド (実践編)

`core/crud.py` の `CRUDBase` を活用し、より洗練された形で「ノート」機能のCRUDを実装します。

-----

### **ステップ4：ビジネスロジックの実装（`CRUDBase`の活用）**

`CRUDBase`を継承することで、`service.py`が非常にシンプルになります。基本的なCRUD操作は`CRUDBase`が担当し、このモジュール固有のロジックのみを記述します。

**ファイル: `src/modules/notes/service.py` (リファクタリング版)**

```python
from sqlalchemy.orm import Session
from core.crud import CRUDBase
from . import models, schemas

class NoteCRUD(CRUDBase[models.Note, schemas.NoteCreate, schemas.NoteUpdate]):
    def get_notes_by_title(self, db: Session, *, title_keyword: str) -> list[models.Note]:
        """
        タイトルにキーワードを含むノートを検索する（このモジュール固有のロジック）。
        """
        return db.query(self.model).filter(self.model.title.contains(title_keyword)).all()

# service全体で利用するインスタンスを生成
note_service = NoteCRUD(models.Note)
```

基本的な`get`, `create`, `update`, `remove`は既に`note_service`インスタンスに実装されているため、記述する必要がありません。

-----

### **ステップ5：APIルーターの作成（高度な機能追加）**

FastAPIの機能を活用し、より堅牢でドキュメント化されたルーターを作成します。

**ファイル: `src/modules/notes/router.py` (リファクタリング・機能拡張版)**

```python
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from typing import List
from .service import note_service # serviceインスタンスをインポート
from . import schemas
from core.database import get_db

router = APIRouter(
    prefix="/api/notes",
    tags=["Notes"] # APIドキュメントでのグループ化
)

@router.post(
    "/",
    response_model=schemas.Note,
    status_code=status.HTTP_201_CREATED,
    summary="新しいノートの作成",
    description="ノートのタイトルと内容をPOSTして、新しいノートを作成します。"
)
def create_new_note(note: schemas.NoteCreate, db: Session = Depends(get_db)):
    return note_service.create(db=db, obj_in=note)

@router.get(
    "/",
    response_model=List[schemas.Note],
    summary="ノート一覧の取得"
)
def read_all_notes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, ge=1, le=200, description="取得する最大件数")
):
    """
    - **skip**: スキップする件数
    - **limit**: 取得する最大件数 (1-200)
    """
    return note_service.get_multi(db, skip=skip, limit=limit)

@router.get(
    "/{note_id}",
    response_model=schemas.Note,
    summary="特定のノートの取得"
)
def read_note(
    note_id: int = Path(..., ge=1, description="取得するノートのID"),
    db: Session = Depends(get_db)
):
    db_note = note_service.get(db, id=note_id)
    if db_note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return db_note

# ... PUTとDELETEも同様にnote_serviceを呼び出す形にリファクタリング ...
```

-----

### **ステップ7：モジュールのテスト（網羅性の向上）**

`service`層のユニットテストと、`router`層のE2Eテストを両方書くことで、品質をさらに高めます。

#### **サービステストの追加**

データベースへの依存をモック化し、ビジネスロジック単体をテストします。

**ファイル: `src/modules/notes/tests/test_service.py`**

```python
from unittest.mock import Mock
from src.modules.notes.service import NoteCRUD
from src.modules.notes.models import Note

def test_get_notes_by_title():
    # 偽のDBセッション（Mockオブジェクト）を作成
    mock_db = Mock()
    
    # Mockのクエリが返すダミーデータを設定
    mock_db.query.return_value.filter.return_value.all.return_value = [
        Note(id=1, title="Test Keyword", content="..."),
        Note(id=2, title="Another Keyword Test", content="...")
    ]
    
    # テスト対象のインスタンスを生成
    crud_instance = NoteCRUD(Note)
    
    # テスト対象のメソッドを実行
    result = crud_instance.get_notes_by_title(db=mock_db, title_keyword="Keyword")
    
    # 結果を検証
    assert len(result) == 2
    assert result[0].title == "Test Keyword"
    # mock_db.query().filter().all() が呼び出されたことを確認
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
```

-----

### **ステップ9：APIドキュメンテーションの充実化**

FastAPIはコードから自動でAPIドキュメント (`/docs`) を生成しますが、`Path`, `Query` や各エンドポイントの`summary`, `description` を記述することで、このドキュメントを格段に分かりやすくできます。

  - **`summary`**: API一覧で表示される短い要約。
  - **`description`**: 詳細な説明。Markdownが使用可能です。
  - **`Path`, `Query`, `Body`**: Pydanticモデルと組み合わせることで、パラメータの詳細な説明、バリデーションルール（例: `ge=1` は1以上）、デフォルト値などをドキュメントに明記できます。

開発者はコードを書くだけで、常に最新でインタラクティブなAPI仕様書をチームに提供できるのです。

-----

