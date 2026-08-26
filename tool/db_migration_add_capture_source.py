import os
import sqlite3
import sys

# Add project root to sys.path to allow finding config.yaml
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from util.config_util import config

TABLE_NAME = "workflow_steps"
COLUMN_NAME = "output_capture_source"


def migrate() -> None:
    """
    Adds the 'output_capture_source' column to the 'workflow_steps' table
    in the SQLite database if it doesn't already exist.
    """
    db_url = config.database_url
    if not db_url.startswith("sqlite:///"):
        print(f"This migration script is for SQLite only. Your database is: {db_url}")
        return

    # In "sqlite:///jobs.sqlite", the path is "jobs.sqlite"
    db_filename = db_url.split("sqlite:///", 1)[1]
    db_path = os.path.join(project_root, db_filename)

    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. A new one will be created on next run. No migration needed.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the column already exists
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        columns = [row[1] for row in cursor.fetchall()]

        if COLUMN_NAME in columns:
            print(f"Column '{COLUMN_NAME}' already exists in table '{TABLE_NAME}'. No migration needed.")
        else:
            print(f"Column '{COLUMN_NAME}' not found. Adding it to table '{TABLE_NAME}'...")
            # Add the column.
            # The default value in the model ('return_value') will be used for new rows.
            # Existing rows will have NULL, which the code handles gracefully.
            cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {COLUMN_NAME} VARCHAR")
            conn.commit()
            print(f"Migration successful: Added '{COLUMN_NAME}' column to '{TABLE_NAME}'.")

    except sqlite3.Error as e:
        print(f"An error occurred during migration: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()


if __name__ == "__main__":
    print("Running database migration for 'output_capture_source'...")
    migrate()
