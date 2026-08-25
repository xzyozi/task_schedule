# プロセス起動スクリプト (`.bat`ファイル) の説明

このドキュメントでは、プロジェクトで使用される主要な`.bat`ファイルについて説明します。これらのスクリプトは、アプリケーションの異なるコンポーネントを起動するために使用されます。

## 1. `start_flask_server.bat`

**目的**: FlaskベースのWeb GUIアプリケーションを起動します。このスクリプトは、Webインターフェースのみを提供し、スケジューラバックエンドとは独立して動作します。

**設定**:
*   `python src/webgui/app.py`: `src/webgui/app.py`にあるFlaskアプリケーションを直接実行します。
*   **環境変数 `FLASK_PORT`**: Flaskサーバーがリッスンするポートを指定できます。指定しない場合、デフォルトで`5012`が使用されます。
    例: `set FLASK_PORT=8080 && python src/webgui/app.py`

**使用方法**:
Web GUIのみを起動し、スケジューラバックエンドは別途起動する場合（または既に起動している場合）に使用します。

## 2. `start_gui_scheduler.bat`

**目的**: FastAPIベースのスケジューラバックエンドとFlaskベースのWeb GUIの両方を同時に起動します。これは、開発時やアプリケーション全体を一度に起動したい場合に便利です。

**設定**:
*   `start /B uvicorn src.scheduler.main:app --reload --port 8000`: FastAPIスケジューラバックエンドをバックグラウンドで起動します。
    *   `--reload`: コード変更時に自動的にリロードします。
    *   `--port 8000`: ポート8000でリッスンします。
*   `start /B python src/webgui/app.py`: Flask Web GUIをバックグラウンドで起動します。
    *   **環境変数 `FLASK_PORT`**: Flaskサーバーのポートを指定できます（上記`start_flask_server.bat`と同様）。

**使用方法**:
スケジューラとWeb GUIの両方を一度に起動して、フル機能のアプリケーション環境をセットアップする場合に使用します。

## 3. `start_webgui_only.bat`

**目的**: `start_flask_server.bat`と同様に、FlaskベースのWeb GUIアプリケーションのみを起動します。スクリプトの内容は`start_flask_server.bat`と同一である可能性があります。

**設定**:
*   `python src/webgui/app.py`: `src/webgui/app.py`にあるFlaskアプリケーションを直接実行します。
*   **環境変数 `FLASK_PORT`**: Flaskサーバーがリッスンするポートを指定できます。

**使用方法**:
`start_flask_server.bat`と同じ目的で使用されます。ファイル名が異なるだけで、機能的には同じである可能性が高いです。

---

**補足**:
*   これらの`.bat`ファイルはWindows環境での使用を想定しています。
*   `start /B`コマンドは、新しいコマンドプロンプトウィンドウを開かずにバックグラウンドでプロセスを実行します。これにより、複数のコンポーネントを1つのスクリプトから起動できます。
*   `jobs.yaml`ファイルは、スケジューラが管理するジョブの定義に使用されます。通常、プロジェクトのルートディレクトリに配置されます。