# ワークフロー変数受け渡し機能 実装計画書

## 1. 概要

本計画は、ワークフロー内のタスク間で値を受け渡すための変数機能の実装方針を定めるものです。
あるタスクの実行結果（例：シェルコマンドの標準出力）を後続のタスクのパラメータとして利用できるようにすることを目的とします。

## 2. 背景

現状のワークフローシステムでは、各タスクは独立して実行され、タスク間で動的に情報を共有する仕組みが存在しません。
例えば、「ファイル一覧を取得するタスク」の実行結果を、「ファイル名を変更するタスク」の入力として渡すような、連携処理を実現できません。
この制約により、複雑な自動化ワークフローの構築が困難になっています。

本機能を実装することで、より柔軟で強力なワークフローを定義できるようになります。

## 3. 実装方針

以下の3つの主要な仕組みを導入し、変数機能を実現します。

### 3.1. 変数定義と出力のマッピング

ワークフローの各ステップ（ジョブ）定義に、実行結果をどの変数に保存するかを指定するフィールドを追加します。

- **対象モデル**: `src/modules/scheduler/schemas.py` の `JobCreate`, `JobUpdate`, `Job` スキーマ
- **追加フィールド**:
    - `output_variable_name` (str, optional): 出力結果を保存する変数名を指定します。
    - `output_capture_source` (str, optional): どの出力をキャプチャするかを指定します（例: `stdout`, `return_value`）。デフォルトは `return_value` とします。

### 3.2. パラメータでの変数参照

後続タスクのパラメータ（引数）内で、保存された変数を参照するためのテンプレート構文を導入します。

- **構文**: `{{ variables.variable_name }}` の形式を採用します。
- **処理**: タスク実行直前に、このテンプレート構文を検出し、ワークフロー実行コンテキストに保存されている実際の値に置換します。

### 3.3. 実行エンジンの改修

変数（出力）の保存と、変数（入力）の置換処理を、ジョブ実行エンジンに組み込みます。

- **対象モジュール**: `src/modules/scheduler/job_executors.py`
- **改修内容**:
    1. **実行コンテキストの導入**: ワークフローの一連の実行を通じて変数を保持するための辞書型オブジェクト（実行コンテキスト）を導入します。このコンテキストは、ワークフローの開始時に初期化され、各ステップの実行時に引き回されます。
    2. **入力パラメータの置換処理**:
        - `execute_job` 関数の冒頭で、ジョブの `args` と `kwargs` を走査します。
        - `{{ variables.variable_name }}` 形式の文字列を見つけた場合、実行コンテキストから対応する値を取得して置換します。
    3. **出力結果の保存処理**:
        - ジョブ実行後、`output_variable_name` が指定されているかを確認します。
        - 指定されている場合、`output_capture_source` に基づいて実行結果（シェルの標準出力、Python関数の戻り値など）を取得します。
        - 取得した値を、`output_variable_name` で指定されたキーで実行コンテキストに保存します。

- **対象モジュール**: `src/modules/scheduler/service.py`
- **改修内容**:
    - `execute_workflow` 関数内で、ワークフロー実行単位のコンテキストを初期化し、各ステップの `execute_job` 呼び出し時に受け渡すように変更します。

## 4. 実装ステップ

1.  **[モデル/スキーマ変更]**
    - `src/modules/scheduler/schemas.py` の `JobCreate`, `JobUpdate`, `Job` に `output_variable_name`, `output_capture_source` フィールドを追加します。
    - `src/modules/scheduler/models.py` の `Job` モデルにも同様にカラムを追加し、マイグレーションを行います。（※Alembic等のマイグレーションツールを導入していない場合は、DBの手動変更や再作成で対応）

2.  **[サービス層の改修]**
    - `src/modules/scheduler/service.py` の `execute_workflow` 関数を改修し、空の辞書として実行コンテキスト (`execution_context`) を生成し、ループ内で `execute_job` に渡すようにします。

3.  **[実行エンジンの改修]**
    - `src/modules/scheduler/job_executors.py` の `execute_job` 関数のシグネチャを `(db, job, execution_context)` に変更します。
    - パラメータ内の変数置換を行う `_substitute_variables` 関数を実装し、`execute_job` の先頭で呼び出します。
    - `ShellJobExecutor` と `PythonJobExecutor` の中で、ジョブ実行後に `execution_context` に結果を保存するロジックを追加します。

4.  **[APIの改修]**
    - `src/modules/scheduler/routers/workflows.py` のワークフロー作成・更新APIを改修し、新しいフィールド (`output_variable_name`, `output_capture_source`) を受け取れるようにします。

5.  **[UIの改修]**
    - `src/webgui/templates/workflow_detail.html` と `src/webgui/static/workflow_detail.js` を変更します。
    - 各ステップの設定項目に「出力変数名」と「キャプチャ対象」の入力フィールドを追加します。
    - パラメータの入力欄で `{{ variables.xxx }}` という構文が利用可能であることをユーザーに示唆するUI上の工夫を追加します。

6.  **[テスト]**
    - 2つのステップからなるワークフローを作成します。
        - ステップ1: シェルジョブで `echo "hello world"` を実行し、`output_variable_name` に `greeting` を指定する。
        - ステップ2: Pythonジョブで、引数に `{{ variables.greeting }}` を指定し、受け取った値をログに出力する。
    - 上記ワークフローを実行し、ログに "hello world" が正しく出力されることを確認します。
