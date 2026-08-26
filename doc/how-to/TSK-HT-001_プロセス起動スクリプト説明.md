# プロセス起動スクリプト (`scripts/*.bat`) の説明

このドキュメントでは、プロジェクトで使用される `scripts/` ディレクトリ配下の主要な `.bat` ファイルについて説明します。
WebGUI は FastAPI アプリケーション (`src/main.py`) へ統合されたため、1つのプロセス起動でスケジューラバックエンドと WebGUI の両方が起動します。

## 1. `scripts/start_dev.bat`

**目的**: 開発環境用にタスクスケジューラアプリケーション（FastAPI + WebGUI統合版）を起動します。

**設定・挙動**:
* 仮想環境（`.venv\Scripts\activate.bat` または `venv\Scripts\activate.bat`）を自動検知してアクティベートします。
* `PYTHONPATH` に `src` ディレクトリを追加します。
* `PYTHONDONTWRITEBYTECODE=1` および `python -B src/main.py` により、`.pyc` ファイルを生成せずにアプリケーションを実行します。

**使用方法**:
```cmd
scripts\start_dev.bat
```
起動完了後、ブラウザから `http://127.0.0.1:8000` にアクセスして WebGUI を利用できます。

---

## 2. `scripts/start_debug.bat`

**目的**: デバッグ実行用にタスクスケジューラアプリケーションを起動します。

**設定・挙動**:
* `start_dev.bat` と同様に仮想環境（`.venv` / `venv`）をアクティベートして実行します。
* デバッグ時の環境変数 `PYTHONPATH` をクリーンに設定し、FastAPI サーバーを起動します。

**使用方法**:
```cmd
scripts\start_debug.bat
```

---

**補足**:
* これらの `.bat` ファイルは Windows 環境での使用を想定しています。
* `uv` 環境（`.venv`）および従来の `venv` の両方に対応しています。
* ジョブ設定はプロジェクトルートの `jobs.yaml` を参照します。