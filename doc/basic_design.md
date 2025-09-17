# 基本設計書: 拡張タスクスケジューラシステム

## 1. 目的

本設計書は、既存のタスクスケジューラシステムを拡張し、複数のタスクを順次実行する「シナリオ（ワークフロー）」機能および外部プロセスの管理機能を追加することを目的とします。これにより、より複雑な業務プロセスの自動化と、システム全体の拡張性・柔軟性の向上を目指します。最終的なジョブ管理はSQLデータベースを介して行われることを前提とします。

## 2. 既存システム概要

現在のタスクスケジューラは、FastAPIをベースとしたAPIとAPSchedulerを核とするバックグラウンドスケジューラで構成されています。

*   **ジョブ定義:** `jobs.yaml`ファイルまたはAPI経由で定義され、SQLAlchemy ORMを介してSQLiteデータベースに永続化されます。
*   **スケジューリング:** APSchedulerがジョブを実行します。
*   **同期:** データベースとスケジューラ間のジョブ同期機能（`sync_jobs_from_db`）を持ちます。
*   **ホットリロード:** `jobs.yaml`の変更を監視し、ジョブ設定を動的に再適用する機能、およびUvicornによるアプリケーションコードのホットリロード機能を持ちます。
*   **ロギング:** カスタムロギングユーティリティを通じて、コンソールとファイルにログを出力します。

## 3. 新機能要件

### 3.1. シナリオ（ワークフロー）管理

*   **定義:** 複数の既存のジョブ（`JobDefinition`）を順序付けられたステップとして含む「シナリオ」を定義できること。
*   **実行:** シナリオはAPSchedulerによって単一のジョブとしてスケジュールされ、実行時にそのステップを順次処理すること。
*   **依存関係:** 各ステップは前のステップの完了を待ってから開始されること。
*   **状態管理:** シナリオ全体の実行状態（実行中、成功、失敗など）および各ステップの実行状態を追跡できること。
*   **エラーハンドリング:** シナリオ内のステップが失敗した場合の挙動（停止、スキップ、再試行など）を定義できること。

### 3.2. プロセス管理

*   **外部コマンド実行:** スケジューラから任意の外部コマンドやスクリプトを実行できる汎用的なジョブタイプを提供すること。
*   **監視:** 実行された外部プロセスの標準出力、標準エラー出力、終了コードをキャプチャし、ログに記録できること。
*   **状態報告:** 外部プロセスの成功/失敗をスケジューラに報告できること。
*   **タイムアウト:** 外部プロセスの実行にタイムアウトを設定できること。

## 4. アーキテクチャ概要

既存のコンポーネントを維持しつつ、シナリオとプロセス管理のための新しいレイヤーを追加します。

```
+-------------------+       +-------------------+       +-------------------+
|   User/Admin      |       |   FastAPI API     |       |   APScheduler     |
| (Browser/CLI)     |       |                   |       |                   |
+---------+---------+       +---------+---------+       +---------+---------+
          |                           |                           |
          | (HTTP/CLI)                | (DB Operations)           | (Job Execution)
          v                           v                           v
+---------------------------------------------------------------------------+
|                           Scheduler Core                                  |
| +-----------------------------------------------------------------------+ |
| |                       Workflow Executor (New)                         | |
| | +-------------------+ +-------------------+ +---------------------+ | |
| | | Workflow Manager  | | Step Orchestrator | | Process Runner (New)| | |
| | | (DB interaction)  | | (Sequential Logic)| | (subprocess module) | | |
| | +-------------------+ +-------------------+ +---------------------+ | |
| +-----------------------------------------------------------------------+ |
|                                                                           |
| +-------------------+ +-------------------+ +---------------------------+ |
| | Job Loader        | | Job Synchronizer  | | Job Definitions (Existing)| |
| | (jobs.yaml)       | | (DB <-> Scheduler)| |                           | |
| +-------------------+ +-------------------+ +---------------------------+ |
+---------------------------------------------------------------------------+
          |
          | (SQLAlchemy ORM)
          v
+-------------------+
|   SQL Database    |
| (SQLite/PostgreSQL)|
+-------------------+
```

**主要な追加コンポーネント:**

*   **Workflow Executor:** APSchedulerによってスケジュールされるメインのジョブ。`WorkflowDefinition`を読み込み、そのステップを順次実行します。
*   **Process Runner:** 外部コマンドを実行し、その結果を管理するための汎用的なタスク関数。
*   **Workflow Manager:** データベース内の`WorkflowDefinition`のCRUD操作を管理するロジック。

## 5. データモデル設計

### 5.1. `JobDefinition` (既存)

変更なし。個々のタスクの定義。

### 5.2. `WorkflowDefinition` (新規)

複数のジョブを順次実行するシナリオの定義。

*   `id`: string (Primary Key) - ワークフローの一意の識別子
*   `name`: string - ワークフローの表示名
*   `description`: string (Optional) - ワークフローの説明
*   `steps`: JSON - 実行するステップのリスト。各ステップは、`JobDefinition`のIDと、そのステップ固有のパラメータ（例: `args`, `kwargs`の上書き、エラーハンドリング設定）を含む辞書として定義されます。
    *   例: `[{"job_id": "task_a", "on_fail": "stop"}, {"job_id": "task_b"}]`
*   `created_at`: datetime
*   `updated_at`: datetime

### 5.3. `WorkflowRun` (新規)

実行中のシナリオのインスタンスと状態を追跡するためのモデル。

*   `id`: string (Primary Key) - ワークフロー実行の一意の識別子
*   `workflow_id`: string (Foreign Key to `WorkflowDefinition.id`) - 実行中のワークフローの定義
*   `status`: string - ワークフローの現在の状態（例: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `STOPPED`）
*   `current_step_index`: integer - 現在実行中のステップのインデックス
*   `start_time`: datetime
*   `end_time`: datetime (Optional)
*   `last_error`: string (Optional) - 最後のステップで発生したエラーメッセージ
*   `log_output`: JSON (Optional) - ワークフロー実行全体のログやサマリー

### 5.4. `ProcessExecutionLog` (新規)

外部プロセス実行の詳細を記録するためのモデル。

*   `id`: string (Primary Key)
*   `job_id`: string (Foreign Key to `JobDefinition.id`) - 関連するジョブのID
*   `workflow_run_id`: string (Foreign Key to `WorkflowRun.id`, Optional) - ワークフローの一部として実行された場合の関連ワークフロー実行ID
*   `command`: string - 実行されたコマンド
*   `exit_code`: integer (Optional) - プロセスの終了コード
*   `stdout`: text (Optional) - 標準出力
*   `stderr`: text (Optional) - 標準エラー出力
*   `start_time`: datetime
*   `end_time`: datetime
*   `status`: string - プロセスの状態（例: `RUNNING`, `COMPLETED`, `FAILED`, `TIMED_OUT`）

## 6. 機能設計

### 6.1. ワークフロー定義とストレージ

*   **APIエンドポイント:** `/workflows`エンドポイントを追加し、`WorkflowDefinition`のCRUD操作（作成、読み取り、更新、削除）を可能にします。
*   **データ永続化:** `WorkflowDefinition`は`JobDefinition`と同様にSQLデータベースに永続化されます。

### 6.2. ワークフロー実行

*   **Workflow Executor Job:**
    *   APSchedulerに登録される特別なジョブ（例: `scheduler.workflow_executor.execute_workflow`）。
    *   このジョブは`workflow_id`をパラメータとして受け取ります。
    *   実行時、対応する`WorkflowDefinition`をデータベースからロードします。
    *   `WorkflowRun`エントリを作成し、状態を`RUNNING`に設定します。
    *   `steps`リストをループし、各ステップのジョブをトリガーします。
    *   **シーケンシャル実行の制御:**
        *   各ステップのジョブは、実行完了時に`WorkflowRun`のステータスを更新し、次のステップの実行をトリガーするコールバックメカニズムを持つことができます。
        *   または、Workflow Executorが各ステップの完了をポーリングし、完了後に次のステップに進むことも考えられます（ただし、ポーリングはリソースを消費します）。
        *   より高度な方法として、各ステップのジョブが完了時に特定のイベントを発行し、Workflow Executorがそのイベントをリッスンして次のステップに進むイベント駆動型のアプローチも検討できます。
    *   ステップの成功/失敗に応じて`WorkflowRun`の`status`と`last_error`を更新します。
    *   すべてのステップが完了したら、`WorkflowRun`の`status`を`SUCCESS`または`FAILED`に設定します。

### 6.3. プロセス実行タスク

*   **汎用タスク関数:** `src/scheduler/tasks/process_runner.py`のような新しいファイルに、`run_command(command: str, args: List[str], cwd: str = None, timeout: int = None)`のような関数を実装します。
*   **`subprocess`モジュール:** この関数はPythonの`subprocess`モジュールを使用して外部コマンドを実行します。
*   **結果のキャプチャ:** `stdout`, `stderr`, `exit_code`をキャプチャし、`ProcessExecutionLog`モデルに保存します。
*   **エラーハンドリング:** コマンドの実行失敗、タイムアウト、非ゼロ終了コードなどを適切に処理します。

### 6.4. APIエンドポイントの拡張

*   `/workflows`: `WorkflowDefinition`のリスト取得、作成。
*   `/workflows/{workflow_id}`: 特定の`WorkflowDefinition`の取得、更新、削除。
*   `/workflows/{workflow_id}/run`: 特定のワークフローを手動で実行開始。
*   `/workflow_runs`: `WorkflowRun`のリスト取得。
*   `/workflow_runs/{run_id}`: 特定の`WorkflowRun`の詳細取得（状態、ログ、ステップごとの結果など）。
*   `/process_logs`: `ProcessExecutionLog`のリスト取得。
*   `/process_logs/{log_id}`: 特定の`ProcessExecutionLog`の詳細取得。

## 7. 技術スタック

*   **Python:** 3.8+
*   **FastAPI:** Web APIフレームワーク
*   **APScheduler:** タスクスケジューリング
*   **SQLAlchemy:** ORM (データベース操作)
*   **Pydantic:** データバリデーション
*   **SQLite:** 開発/テスト用データベース (本番ではPostgreSQLなどを想定)
*   **`subprocess`モジュール:** プロセス実行
*   **`watchdog`:** ファイル変更監視 (既存)

## 8. 今後の課題/考慮事項

*   **トランザクション管理:** ワークフローのステップ間でのデータ整合性を保証するためのトランザクション戦略。
*   **冪等性:** ワークフローの再試行や再実行時の冪等性の確保。
*   **リソース管理:** 多数の同時実行プロセスやワークフローがシステムリソースを枯渇させないようにするためのメカニズム。
*   **認証・認可:** APIエンドポイントへのアクセス制御。
*   **監視とアラート:** ワークフローの失敗やプロセスの異常終了を検知し、通知する仕組み。
*   **UI:** 将来的なWeb UIの統合。
*   **`jobs.yaml`の役割の再定義:** SQL管理が主となるため、`jobs.yaml`は初期シード専用とするか、そのホットリロード機能を無効にするか、あるいは別の目的（例: テンプレート）に限定するかを決定する必要があります。

---
