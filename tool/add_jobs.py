import os
from pathlib import Path
import sys

# プロジェクトのルートディレクトリをPythonのパスに追加
# このスクリプトがtoolディレクトリにあることを考慮
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.modules.scheduler import loader
from src.core import database

print("Initializing database...")
database.init_db()
print(f"Database engine: {database.engine}")

print("Tables in metadata before create_all:")
for table in database.Base.metadata.tables:
    print(f"- {table}")

# データベーススキーマを再作成（開発環境向け）
# 既存のjobs.sqliteを削除した場合に必要
print("Creating database schema...")
database.Base.metadata.create_all(bind=database.engine)
print("Schema creation command executed.")

# jobs.yaml ファイルのパス
jobs_yaml_path = project_root / "jobs.yaml"

if not jobs_yaml_path.exists():
    print(f"Error: jobs.yaml not found at {jobs_yaml_path}")
else:
    print(f"Seeding database from {jobs_yaml_path}...")
    loader.seed_db_from_yaml(str(jobs_yaml_path))
    print("Database seeding complete.")