# 回復力のあるタスクスケジューラ (Resilient Task Scheduler)

本番環境での利用を想定して設計された、回復力、永続性、管理性を備えたタスクスケジューリングサービスです。このプロジェクトは、単純なタスクスケジューラを、堅牢なAPI駆動のサービスへと進化させたものです。

設計思想として、このシステムは単なるスクリプトではなく、ステートフルで観測可能性を備え、柔軟な運用が可能なサービスとして構築されています。

## 主な特徴

*   **回復力と永続性**: `APScheduler`と`SQLAlchemyJobStore`（SQLite, PostgreSQL対応）をバックエンドに採用。アプリケーションの再起動やクラッシュ後もジョブとスケジュールが維持されます。
*   **動的なジョブ定義**: 人間が読み書きしやすい`jobs.yaml`ファイルでジョブを管理。スケジュールの変更にコード修正や再デプロイは不要です。
*   **ホットリロード**: `jobs.yaml`への変更をリアルタイムに検知し、サービスを停止することなく自動的にスケジューラへ反映させます（ゼロダウンタイムでの設定更新）。
*   **Web GUI**: スケジューラを視覚的に管理・監視するためのWebインターフェースを搭載。
    *   システムの状態とジョブのタイムラインを表示するダッシュボード
    *   ジョブの一覧、フィルタリング、新規作成、一時停止、手動実行などの管理機能
    *   ジョブごとの実行履歴とログ（標準出力/エラー）の詳細表示
*   **REST APIによる制御**: FastAPIベースのREST APIを提供し、外部システムとの連携やプログラムによる完全な制御を可能にします。
*   **拡張可能なジョブタイプ**: Python関数だけでなく、外部のコマンドやスクリプト（シェルスクリプト、バッチファイル等）もネイティブにサポートします。
*   **高度なスケジューリング**: cron形式、インターバル形式、日付指定形式のスケジュールに対応し、`max_instances`（最大同時実行数）や`misfire_grace_time`（実行許容時間）などの細かい実行制御が可能です。

## 技術スタック

*   **バックエンド**: Python 3.8+
*   **スケジューリング**: APScheduler
*   **API**: FastAPI
*   **Web GUI**: Flask
*   **データベース/ORM**: SQLAlchemy
*   **設定ファイル**: PyYAML (`jobs.yaml`), Pydantic (バリデーション)
*   **ファイル監視**: Watchdog

## セットアップ方法

### 1. インストール

リポジトリをクローンし、`pyproject.toml`を使ってプロジェクトをインストールします。

```bash
git clone <repository-url>
cd task_schedule
pip install .
```

開発用に、オプションの依存関係をインストールすることもできます。
```bash
pip install .[dev]
```

### 2. アプリケーションの実行

インストール後、単一のコマンドでスケジューラとWeb API/GUIを起動できます。

```bash
task-scheduler
```

デフォルトでは、FastAPIサーバーが `http://localhost:8000` で起動します。Web GUIは設定に応じて別のポート（例: `http://localhost:5012`）でアクセス可能になります。

## 使用方法

### `jobs.yaml`でのジョブ定義

ジョブはプロジェクトルートの`jobs.yaml`ファイルにリスト形式で定義します。

**記述例1: Python関数ジョブ**

5分ごとにPython関数を実行するジョブです。

```yaml
- id: 'api_health_check'
  func: 'modules.scheduler.tasks.monitoring.check_api_status'
  description: '5分ごとにAPIのヘルスチェックを実行します。'
  is_enabled: true
  trigger:
    type: 'interval'
    minutes: 5
  kwargs:
    api_endpoint: 'http://127.0.0.1:8000/'
  replace_existing: true
```

**記述例2: 外部スクリプトジョブ**

cronスケジュールでシェルスクリプトを実行するジョブです。

```yaml
- id: 'daily_backup'
  func: '/path/to/your/backup_script.sh'
  description: '日次バックアップのシェルスクリプトを実行します。'
  is_enabled: true
  trigger:
    type: 'cron'
    day_of_week: 'mon-sun'
    hour: '2'
    minute: '30'
  replace_existing: true
```

### Webインターフェースの利用

Web GUIにブラウザでアクセスすることで、以下の操作を直感的に行うことができます。

- 全ジョブのステータス確認
- ジョブの手動実行、一時停止、再開
- フォームを使った新しいジョブの作成
- 各ジョブの実行履歴とログの確認

## プロジェクト構造

- `jobs.yaml`: ジョブ定義のメイン設定ファイル。
- `pyproject.toml`: プロジェクトの定義、依存関係、パッケージング情報。
- `src/`: アプリケーションのソースコード。
  - `src/core/`: データベース設定やCRUD処理などの中核コンポーネント。
  - `src/modules/scheduler/`: ジョブローダー、ルーター、タスクを含むAPSchedulerのメインロジック。
  - `src/webgui/`: FlaskベースのWebインターフェース。
- `doc/`: プロジェクトの設計・アーキテクチャ関連ドキュメント。
- `test/`: テストファイル。
