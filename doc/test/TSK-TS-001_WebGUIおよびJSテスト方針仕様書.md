# WebGUI および JS テスト方針仕様書 (TSK-TS-001)

## 1. 概要

本ドキュメントは、タスクスケジューラ WebGUI および JavaScript フロントエンドのテスト戦略、テスト分類、自動テスト仕様、および CI 統合方針を定義します。

---

## 2. テスト階層とテストピラミッド

WebGUI の品質維持のため、以下の 3 レベルでテストを実施・整備します。

```
       / \
      / E2E \       Level 3: Playwright による E2E ブラウザ自動化テスト
     /-------r\
    / JS Unit  \    Level 2: JS フロントエンドユーティリティ検証
   /------------\
  / FastAPI Test \  Level 1: FastAPI TestClient による API/静的ファイルテスト
 /----------------\
```

| テスト階層 | テスト対象 | 主要ツール | 目的・検証内容 |
| :--- | :--- | :--- | :--- |
| **Level 1: API / ルーティングテスト** | FastAPI WebGUI エンドポイント | `pytest` + `fastapi.testclient.TestClient` | 静的ファイル・Jinja2テンプレート返却ステータス 200 や JSON 構造の正常性 |
| **Level 2: JS ロジックテスト** | `api_config.js` ユーティリティ | `vitest` / `node:test` (オプション) | XSS エスケープ (`escapeHtml`) や API URL 動的生成の単体テスト |
| **Level 3: E2E ブラウザテスト** | 画面全体・UI操作・JS非同期動作 | `playwright` (Python/Node.js) | ブラウザでの実際のボタンクリック、モーダル操作、データ更新、表示崩れの自動検証 |

---

## 3. テスト仕様と具体的なシナリオ

### 3.1 Level 1: FastAPI TestClient テスト (`test/test_webgui_router.py`)
- **テストケース一覧**:
  - `test_webgui_index_page`: ダッシュボード (`/`) にアクセスし 200 OK および "ダッシュボード" 文字列が含まれること。
  - `test_webgui_logs_page`: ログ画面 (`/logs`) のレスポンス検証。
  - `test_webgui_jobs_page`: ジョブ画面 (`/jobs`) のレスポンス検証。
  - `test_webgui_workflows_page`: ワークフロー画面 (`/workflows`) のレスポンス検証。
  - `test_webgui_settings_page`: 設定画面 (`/settings`) のレスポンス検証。
  - `test_webgui_config_endpoint`: `/webgui-config` が正常な JSON 構成を返却すること。

### 3.2 Level 2: Playwright E2E テストシナリオ案
- **シナリオ 1: ジョブ一覧表示とアクションボタンの検証**:
  1. `http://127.0.0.1:8000/` へアクセス。
  2. サマリーカード（Total Jobs等）に数値が表示されることを確認。
  3. `Run` ボタンをクリックし、成功メッセージまたはステータス更新を確認。
- **シナリオ 2: 新規ジョブ作成フォーム（モーダル）操作**:
  1. `/jobs` 画面へ遷移。
  2. 「新規作成」ボタンをクリックしてモーダルを開く。
  3. 必須項目（ジョブID, ジョブ名, 関数名）を入力して保存。
  4. テーブルに追加された新ジョブが表示されることを確認。
- **シナリオ 3: エラーハンドリング検証**:
  1. 無効なジョブ操作リクエスト時にエラーアラート/通知が表示されること。

---

## 4. CI/CD 統合および自動実行方針

### 4.1 ローカル実行コマンド
```bash
# 1. FastAPI バックエンド & ルーティングテスト
uv run pytest test/test_webgui_router.py

# 2. 全テスト実行
uv run pytest
```

### 4.2 E2E テスト環境の導入手順（将来導入時）
```bash
# Playwright パッケージインストール
uv add --dev pytest-playwright
uv run playwright install chromium
```

---

## 5. 品質評価基準 (Quality Gate)

- **ビルド・テスト通過条件**:
  - すべての Pytest (`uv run pytest`) が 100% 成功すること。
  - WebGUI ルーティングテストで 4xx/5xx レスポンスが発生しないこと。
- **コードスタイルの遵守**:
  - Python 側: `uv run ruff check src test`
  - JS 側: XSS 対策 (`escapeHtml`) の徹底。
