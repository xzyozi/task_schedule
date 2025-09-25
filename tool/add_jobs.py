import os
from pathlib import Path
import sys

# プロジェクトのルートディレクトリをPythonのパスに追加
# このスクリプトがtoolディレクトリにあることを考慮
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.modules.scheduler import loader
from src.core import database

# データベースを初期化
database.init_db()

# データベーススキーマを再作成（開発環境向け）
# 既存のjobs.sqliteを削除した場合に必要
database.Base.metadata.create_all(bind=database.engine)

# jobs.yaml ファイルのパス
jobs_yaml_path = project_root / "jobs.yaml"

if not jobs_yaml_path.exists():
    print(f"Error: jobs.yaml not found at {jobs_yaml_path}")
else:
    print(f"Seeding database from {jobs_yaml_path}...")
    loader.seed_db_from_yaml(str(jobs_yaml_path))
    print("Database seeding complete.")