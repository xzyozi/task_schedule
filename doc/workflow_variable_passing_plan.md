# ワークフロー変数渡し機能 実装計画書

## 1. 概要

本計画は、ワークフロー内の異なるステップ（タスク）間で出力を受け渡し、後続ステップの入力として利用するための「変数渡し機能」の実装方針を定めるものである。これにより、例えば「ファイル一覧を取得するステップ」の出力を、「各ファイルを処理するステップ」に渡すといった、より動的で連携性の高いワークフローの構築を可能にする。

## 2. コアコンセプト

### 2.1. ワークフローコンテキスト

- 各ワークフロー実行 (`WorkflowRun`) ごとに、ステップの出力を保存するための共有ストレージ（コンテキスト）を導入する。
- このコンテキストは、キー（変数名）と値（ステップの出力）のペアを保持するJSON形式のデータとする。

### 2.2. 変数参照構文

- 後続ステップの引数内で、先行ステップの出力を参照するための特別な構文を定義する。
- 構文案: `{{ steps.<step_id>.outputs.<output_name> }}`
  - `steps`: 固定プレフィックス
  - `<step_id>`: 出力元となるステップのID
  - `outputs`: 固定プレフィックス
  - `<output_name>`: 出力の種類を示す名前（例: `stdout`, `result`）

## 3. データベーススキーマの変更

- `src/modules/scheduler/models.py` に定義されている `WorkflowRun` モデルに、ワークフローコンテキストを保存するためのフィールドを追加する。
- **提案:** `context` という名前の `JSON` 型フィールドを追加する。
  ```python
  class WorkflowRun(Base):
      # ... existing fields
      context = Column(JSON, nullable=True, default=dict)
  ```

## 4. バックエンド実装

### 4.1. ワークフロー実行サービス (`service.py`)

- `src/modules/scheduler/service.py` のワークフロー実行ループを修正する。
- **ステップ実行前:**
  - ステップの引数（`args`, `kwargs`）を走査し、`{{ ... }}` 構文のプレースホルダーを `WorkflowRun.context` に保存されている実際の値で置換する。
- **ステップ実行後:**
  - 実行結果（`stdout` やPython関数の戻り値）を取得する。
  - 取得した結果を、ステップIDと出力名をキーとして `WorkflowRun.context` に保存し、データベースを更新する。

### 4.2. ジョブ実行基盤 (`job_executors.py`)

- `src/modules/scheduler/job_executors.py` の各Executorクラスを修正し、実行結果を返すようにする。
- `ShellJobExecutor`: `stdout`, `stderr`, `return_code` を含む辞書を返す。
- `PythonJobExecutor`: Python関数の戻り値を `result` として含む辞書を返す。

## 5. APIの変更

- 基本的に、既存のワークフロー作成・更新API (`/api/workflows`) をそのまま利用する。
- 変数参照構文 `{{ ... }}` は、通常の文字列として `args` や `kwargs` の値に埋め込まれるため、APIスキーマ (`schemas.py`) の直接的な変更は不要。
- フロントエンドがこの構文を含むJSONを送信し、バックエンドがそれを受け取る形となる。

## 6. フロントエンド実装

- `src/webgui/templates/workflow_detail.html` および `static/workflow_detail.js` を修正する。
- **UI:**
  - ステップのパラメータ入力欄の近くに、「先行ステップの出力を挿入」ボタンを設置する。
  - ボタンをクリックすると、モーダルやドロップダウンが表示され、同じワークフロー内の先行ステップとその出力（例: `steps.step1.outputs.stdout`）を選択できる。
  - 選択すると、対応する変数参照構文がカーソル位置の入力フィールドに挿入される。
- **データフロー:**
  - ワークフロー定義を読み込む際に、各ステップのIDと順序を解析し、UIで参照可能な出力のリストを構築する。

## 7. 関連する不具合の修正

- `dashboard.py` の `get_timeline_data` 関数で発生している `AttributeError: 'NoneType' object has no attribute 'name'` を修正する。
- **原因調査:** `WorkflowRun` オブジェクトに対応する `Workflow` オబ్జెక్ట్が紐付いていない（`run.workflow` が `None` になっている）ことが原因と考えられる。データ登録時の不備、あるいはカスケード削除設定の漏れなどが考えられる。
- **対策:**
  - `WorkflowRun` モデルの `workflow_id` に `nullable=False` 制約と適切な外部キーリレーションシップを強制する。
  - 既存のデータで `workflow_id` が `NULL` になっているものがあれば修正する。
  - ワークフロー削除時に、関連する実行履歴が正しく処理されることを確認する。
