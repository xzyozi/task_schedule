# カスタムスクリプトのジョブ登録とログ追跡

このドキュメントでは、PythonスクリプトおよびPython以外のスクリプトをタスクスケジューラにジョブとして登録する方法、およびそれらの実行ログを追跡する方法について説明します。

## 1. Pythonスクリプトの登録

タスクスケジューラは、Pythonの関数を直接実行するジョブをサポートしています。

### 1.1. 登録方法

1.  **Pythonスクリプトの作成**: 
    プロジェクト内の任意の場所にPythonファイル（例: `my_custom_module.py`）を作成し、その中に実行したい関数を定義します。
    ```python
    # my_custom_module.py
    import datetime

    def my_python_job(name="World", count=1):
        """カスタムPythonジョブの例"""
        print(f"[{datetime.datetime.now()}] Hello, {name}! This is run number {count}.")
        # ここにジョブの実際の処理を記述します
        # 例: データベース操作、API呼び出し、ファイル処理など
        if count % 2 == 0:
            print("Even count, job successful.")
        else:
            raise ValueError("Odd count, simulating a job failure.")

    def another_job_function():
        print("This is another simple Python job.")
    ```

2.  **ジョブの登録**: 
    Web UIのジョブ作成フォーム、または`jobs.yaml`ファイルで、`func`フィールドにその関数の完全なパスを指定します。パスは、Pythonモジュールパスと関数名をコロン `:` で区切って指定します。

    *   **例1: プロジェクトルート直下のファイルの場合**
        `my_custom_module.py`がプロジェクトのルートディレクトリにある場合:
        `func: my_custom_module:my_python_job`

    *   **例2: サブディレクトリ内のファイルの場合**
        `my_custom_module.py`が`src/tasks/`ディレクトリにある場合:
        `func: src.tasks.my_custom_module:my_python_job`

    *   **引数 (`args`, `kwargs`) の指定**: 
        関数に引数を渡す必要がある場合は、`args`（位置引数）や`kwargs`（キーワード引数）フィールドを使用します。
        例: `args: ["Gemini"]`, `kwargs: {"count": 5}`

### 1.2. ログの追跡

Pythonジョブの`print()`出力や標準エラー出力（`stderr`）は、スケジューラのログシステムによって捕捉され、データベースに保存されます。

*   **Web UI**: 
    *   **ジョブ詳細画面 (今後実装)**: 各ジョブの実行履歴から、個々の実行の`stdout`と`stderr`を直接確認できるようになります。
    *   **実行ログ画面 (`/logs`)**: すべてのジョブの実行ログが一覧表示され、フィルタリング機能で特定のジョブのログを検索できます。
*   **バックエンドログ**: 
    スケジューラバックエンドのコンソール出力やログファイル（設定されている場合）にも、ジョブの実行に関する情報が出力されます。

## 2. Python以外のスクリプト（シェルスクリプト、バッチファイルなど）の登録

タスクスケジューラは、外部プロセスを実行するジョブもサポートしています。これにより、Python以外の言語で書かれたスクリプトや、既存のシェルコマンド、バッチファイルなどをジョブとして登録できます。

### 2.1. 登録方法

`func`フィールドには、実行したいコマンドまたはスクリプトへのパスを指定します。この場合、`func`はPython関数へのパスではなく、システムコマンドとして解釈されます。

1.  **スクリプトの準備**: 
    実行したいシェルスクリプト（例: `my_script.sh`）やバッチファイル（例: `my_batch.bat`）を作成し、実行権限を付与します（Linux/macOSの場合）。

    ```bash
    # my_script.sh
    #!/bin/bash
    echo "Hello from shell script at $(date)"
    echo "Arguments received: $@"
    exit 0
    ```

    ```batch
    :: my_batch.bat
    @echo off
    echo Hello from batch file at %DATE% %TIME%
    echo Arguments received: %*
    exit /b 0
    ```

2.  **ジョブの登録**: 
    Web UIのジョブ作成フォーム、または`jobs.yaml`ファイルで、`func`フィールドにスクリプトのパス（またはコマンド）を指定します。

    *   **例1: シェルスクリプトの実行 (Linux/macOS)**
        `func: /path/to/my_script.sh`
        `args: ["arg1", "arg2"]`

    *   **例2: バッチファイルの実行 (Windows)**
        `func: C:\path\to\my_batch.bat`
        `args: ["param1", "param2"]`

    *   **例3: システムコマンドの実行**
        `func: echo`
        `args: ["Hello from echo command!"]`

    *   **注意点**: 
        *   `func`に指定するパスは、スケジューラが実行される環境からアクセス可能である必要があります。
        *   Windows環境で`.bat`ファイルを実行する場合、`func`に直接ファイルパスを指定するだけで動作することが多いですが、環境によっては`cmd.exe /c C:\path\to\my_batch.bat`のように明示的にシェルを呼び出す必要があるかもしれません。
        *   `args`や`kwargs`は、コマンドライン引数としてスクリプトに渡されます。

### 2.2. ログの追跡

Python以外のスクリプトの標準出力（`stdout`）と標準エラー出力（`stderr`）も、スケジューラのログシステムによって捕捉され、データベースに保存されます。

*   **Web UI**: 
    *   **ジョブ詳細画面 (今後実装)**: 各ジョブの実行履歴から、個々の実行の`stdout`と`stderr`を直接確認できるようになります。
    *   **実行ログ画面 (`/logs`)**: すべてのジョブの実行ログが一覧表示され、フィルタリング機能で特定のジョブのログを検索できます。
*   **バックエンドログ**: 
    スケジューラバックエンドのコンソール出力やログファイルにも、ジョブの実行に関する情報が出力されます。

---
