# ワークフロー変数共有機能 実装計画

設計書 `doc/workflow_variable_handling.ja.md` に基づき、ワークフローの変数共有機能を実装するための計画を以下に提案します。

## 実装ステップ

この実装は、データベースの変更から始まり、中核となる実行ロジックの変更を経て完了します。以下のステップで進めます。

### ステップ1：データモデルとスキーマの更新

機能の基礎となるデータベースとデータ検証ルールを先に変更します。

1.  **`models.py` の変更:**
    *   `src/modules/scheduler/models.py` を編集します。
    *   `WorkflowStep` クラスに、ステップの出力結果を保存する変数名を指定するためのカラムを追加します。
        ```python
        output_variable_name = Column(String, nullable=True)
        ```

2.  **`schemas.py` の変更:**
    *   `src/modules/scheduler/schemas.py` を編集します。
    *   `WorkflowStepBase`, `WorkflowStepCreate`, `WorkflowStep` の各Pydanticスキーマに、対応する `output_variable_name` フィールドを追加します。
        ```python
        class WorkflowStepBase(BaseModel):
            # ... 既存のフィールド
            output_variable_name: Optional[str] = None
        ```

### ステップ2：Pythonジョブラッパーの機能強化

Python関数の戻り値を確実にキャプチャできるようにします。

1.  **`python_job_wrapper.py` の変更:**
    *   `src/modules/scheduler/python_job_wrapper.py` を編集します。
    *   実行した関数の戻り値 (`result`) をキャプチャします。
    *   `result` が `None` でない場合、`json.dumps()` を使ってJSON文字列にシリアライズします。
    *   最終的な出力を `{"return_value": ..., "stdout": ...}` のような構造化されたJSONオブジェクトとして標準出力（`stdout`）に書き出すように変更します。これにより、戻り値と通常の標準出力を明確に区別できます。
    *   JSONシリアライズに失敗した場合は、エラーとして処理します。

### ステップ3：ジョブ実行関数のリファクタリング

各ジョブ実行関数が、自身の実行結果を呼び出し元（`run_workflow`）に返すように変更します。

1.  **`job_executors.py` の変更:**
    *   `src/modules/scheduler/job_executors.py` を編集します。
    *   `execute_shell_job`: 内部で呼び出している `_execute_subprocess` の結果（`stdout`などを含む辞書）をそのまま `return` するように変更します。
    *   `execute_python_job`: `_execute_subprocess` から受け取った `stdout`（JSON文字列）をパースし、`return_value` を抽出して、他の結果と共に辞書として `return` するように変更します。

### ステップ4：中核となるワークフロー実行ロジックの実装

最も重要な部分です。`run_workflow` 関数を設計書通りにリファクタリングします。

1.  **`job_executors.py` の `run_workflow` 関数を大幅に修正:**
    *   **コンテキスト初期化:** ワークフロー開始時に、`WorkflowRun` レコードを空のコンテキスト `{}` で作成します。
    *   **ループ処理の変更:** ステップをループする `for` 文の内部で、以下の処理を追加します。
        1.  **テンプレート置換:**
            *   ステップのパラメータ (`step.task_parameters`) 内に含まれる `{{ context.variable }}` という形式の文字列を、現在のコンテキスト辞書の値で置き換える処理を実装します。
        2.  **ステップ実行と結果のキャプチャ:**
            *   値が置換されたパラメータを使って、`execute_python_job` などの実行関数を呼び出します。
            *   **重要:** 実行関数が返す結果の辞書を、変数に格納します。
        3.  **出力の保存:**
            *   現在のステップに `output_variable_name` が設定されているか確認します。
            *   設定されている場合、キャプチャした結果（Pythonジョブなら `return_value`、シェルジョブなら `stdout`）をコンテキスト辞書に保存します。
        4.  **コンテキストの永続化:**
            *   ステップの処理が完了するたびに、更新されたコンテキスト辞書をデータベースの `WorkflowRun` レコードに保存します。これにより、処理の途中経過が記録されます。

### ステップ5：サービス層の調整

APIからのデータフローを正しく処理できるようにします。

1.  **`service.py` の変更:**
    *   `src/modules/scheduler/service.py` を編集します。
    *   `WorkflowCRUD` サービス内の `create_with_steps` と `update_with_steps` メソッドを修正し、APIから渡される `output_variable_name` を正しく `WorkflowStep` モデルに保存できるようにします。

### ステップ6：テスト（推奨）

機能の品質を保証するためにテストを作成します。

1.  `test/test_workflow_variables.py` のような新しいテストファイルを作成します。
2.  Pythonステップの戻り値が、後続のステップで正しく使われることを確認する一連のワークフローテストを記述します。
3.  変数が存在しない場合など、エラーケースで正しく失敗することもテストします。

この計画に従うことで、設計書に沿った形で段階的かつ確実に機能を実装できます。
