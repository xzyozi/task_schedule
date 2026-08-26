# WebGUI 画面詳細仕様書 (TSK-DD-003)

## 1. 概要とアーキテクチャ

本ドキュメントは、タスクスケジューラ WebGUI の詳細画面仕様、フロントエンド JS モジュール動作仕様、API 通信仕様、および UI インタラクション基準を定義します。

### 1.1 アーキテクチャ概要
- **バックエンド**: FastAPI (`src/main.py`) による単一プロセス構成（WebGUI HTML/Jinja2 テンプレート + REST API を同一ポート `8000` で提供）。
- **フロントエンド**: Bootstrap 5 + Vanilla JS (ES Modules) による SPA 風リアルタイム可視化インターフェース。
- **通信方式**: `fetch` API による非同期 JSON 通信。`api_config.js` を介して動的に `API_BASE_URL` を解決。

---

## 2. 画面構造とコンポーネント詳細

### 2.1 画面一覧とパス

| 画面名 | パス | 対応Jinja2テンプレート | 主なJSモジュール | 概要 |
| :--- | :--- | :--- | :--- | :--- |
| **ダッシュボード** | `/` | `index.html` | `script.js`, `timeline.js`, `api_config.js` | 全体サマリー、ジョブ一覧、タイムライン表示 |
| **ジョブ管理** | `/jobs` | `jobs.html` | `jobs.js`, `api_config.js` | 登録ジョブ一覧、フィルタリング、一括操作、新規作成 |
| **ジョブ詳細** | `/jobs/{id}` | `job_detail.html` | `job_detail.js`, `api_config.js` | 個別ジョブ定義確認、実行履歴、ログ表示 |
| **ワークフロー管理** | `/workflows` | `workflows.html` | `workflows.js`, `api_config.js` | ワークフロー一覧、新規登録 |
| **ワークフロー詳細** | `/workflows/{id}` | `workflow_detail.html` | `workflow_detail.js`, `api_config.js` | ワークフロー構成ステップ、依存関係表示、ログ |
| **実行ログ** | `/logs` | `logs.html` | `logs.js`, `api_config.js` | システム全体の実行ログ検索・フィルター |
| **設定** | `/settings` | `settings.html` | `settings.js`, `api_config.js` | `jobs.yaml` 設定閲覧・直接更新・スケジューラ制御 |

---

## 3. 画面詳細仕様

### 3.1 ダッシュボード画面 (`/`)
- **サマリーカード**:
  - `Total Jobs` (青), `Running Jobs` (シアン), `Successful Runs` (緑), `Failed Runs` (赤) の 4 カードを配置。
  - `/api/dashboard/summary` から 5 秒間隔のポーリングでデータ更新。
- **タイムライン表示**:
  - `vis-timeline` ライブラリを使用して `Upcoming` および `Recent` ジョブの時系列表示。
- **統合ジョブテーブル**:
  - `/api/unified-jobs` から取得。単体ジョブとワークフローを一覧表示。
  - 各行に `Run` (即時実行), `Pause` (一時停止), `Resume` (再開) アクションボタンを配置。

### 3.2 ジョブ管理画面 (`/jobs`)
- **検索・フィルタリング**:
  - ジョブ名・IDでのテキスト検索インプット。
  - ステータス（`enabled`, `disabled`, `paused`）ドロップダウンフィルター。
- **一括操作機能**:
  - テーブル全選択/個別選択チェックボックス。
  - 選択した複数ジョブに対する「一括有効化」「一括一時停止」「一括削除」アクション。
- **新規ジョブ作成モーダル**:
  - `id`, `name`, `func`, `trigger_type` (cron/interval), `cron_expression`, `interval_seconds` フォーム入力。
  - バリデーションエラー時はモーダル内にインライン警告を表示。

### 3.3 設定画面 (`/settings`)
- **`jobs.yaml` エディタ**:
  - 現在のジョブ定義 YAML をテキストエリア表示。
  - 保存ボタン押下時、`/api/config/yaml` に `PUT` リクエストを送信しホットリロードを実施。
- **スケジューラ制御**:
  - スケジューラ全体の一時停止・再開・リロードボタン。

---

## 4. フロントエンド JS モジュール・通信仕様

### 4.1 JS モジュール構成と役割

```
src/webgui/static/
├── api_config.js      # 動的コンフィグ取得, API_BASE_URL 管理, escapeHtml(XSS対策)
├── script.js          # ダッシュボードサマリー & ジョブ一覧制御
├── jobs.js            # ジョブ一覧・検索・一括操作制御
├── job_detail.js      # 個別ジョブ詳細・ログ表示
├── workflows.js       # ワークフロー一覧制御
├── workflow_detail.js # ワークフローステップ可視化・ログ
├── logs.js            # ログ検索・フィルタリング
├── settings.js        # jobs.yaml エディタ & スケジューラ制御
├── timeline.js        # vis.js タイムラインレンダリング
└── style.css          # カスタムスタイル
```

### 4.2 API 通信とエラーハンドリング仕様
- **XSS 対策方針**:
  - 動的にテーブルや HTML 要素へ文字列を挿入する際は、必ず `api_config.js` 内の `escapeHtml()` を通してエスケープ処理を行う。
- **エラー時のリカバリ挙動**:
  - **4xx/5xx エラー**: コンソールエラーログ出力に加え、ユーザー向けに `alert` または UI 上の赤文字警告を表示。
  - **ネットワーク接続断**: 自動ポーリング時、カード等の数値を `N/A` 表示に変更し、接続復旧時に自動復帰。

---

## 5. UI インタラクション & デザイン標準

- **レスポンシブ**: Bootstrap 5 のグリッドシステムを使用し、モバイル/デスクトップ双方に対応。
- **ステータスバッジ**:
  - 有効 (`bg-success`), 無効 (`bg-secondary`), 一時停止 (`bg-warning`), 実行中 (`bg-info`), 失敗 (`bg-danger`)。
