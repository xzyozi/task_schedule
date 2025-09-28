# 機能拡張: CWDサンドボックスと環境変数サポート

## 1. 目的

`shell_command`ジョブのセキュリティと管理性を向上させるため、作業ディレクトリ（CWD）を特定の管理下ディレクトリ（サンドボックス）に限定します。また、ジョブごとに環境変数を設定する機能を追加します。

これにより、以下の点が実現されます。

*   **セキュリティ向上**: ジョブの実行ディレクトリを意図しない場所に設定されるのを防ぎ、システムを保護します。
*   **管理性の向上**: `config.yaml`で定義された単一のベースディレクトリ配下で、すべてのジョブディレクトリを管理します。
*   **柔軟な設定**: ジョブごとに環境変数を渡すことで、秘匿情報や設定を安全に利用できます。

## 2. 提案された解決策

### 2.1. CWDサンドボックスの実装

1.  **`config.yaml` / `util/config_util.py`**
    *   `config.yaml`に、サンドボックスのベースディレクトリとなる`scheduler.work_dir`を追加します（デフォルト: `~/.task_schedule/work_list`）。
    *   `config_util.py`でこの値を読み込み、パスの解決とディレクトリの自動作成を行うプロパティを実装します。

2.  **`src/modules/scheduler/schemas.py`**
    *   `cwd`のバリデーションロジックを更新します。
    *   `cwd`には、`work_dir`からの**相対パス**を指定します。
    *   バリデーターは、パスが`work_dir`の配下にあることを検証し、安全な絶対パスに解決します。

3.  **`src/modules/scheduler/models.py`, `service.py`, `loader.py`, `job_executors.py`**
    *   これらのファイルは、解決済みの絶対パスを透過的に扱うため、大きな変更は不要です。

### 2.2. 環境変数のサポート

1.  **`schemas.py` / `models.py`**: `env: Optional[Dict[str, str]]`フィールドをジョブ定義に追加します。
2.  **`service.py` / `loader.py`**: `env`フィールドの永続化とスケジューラへの受け渡しを実装します。
3.  **`job_executors.py`**: `subprocess.run`に`env`引数を渡し、既存の環境変数とマージしてサブプロセスを実行します。

## 3. 使用例

`config.yaml`で`scheduler.work_dir`がデフォルト値に設定されていると仮定します。
ユーザーは`~/.task_schedule/work_list/my-project`というディレクトリを事前に作成しておく必要があります。

**例: `jobs.yaml`でサンドボックス内のGitリポジトリを更新する**

```yaml
- id: "update-my-project-repo"
  func: "git"
  description: "プロジェクトのリポジトリをプルして最新の状態に更新します。"
  job_type: "shell_command"
  trigger:
    type: "cron"
    hour: "3"
  args:
    - "pull"
  # work_dirからの相対パスを指定
  cwd: "my-project"
  # ジョブ固有の環境変数を設定
  env:
    GIT_SSH_COMMAND: "ssh -i ~/.ssh/id_rsa_git"
  is_enabled: true
```

## 4. 注意事項

*   **CWDのパス形式**:
    *   `cwd`に指定するパスは、`config.yaml`で定義された`scheduler.work_dir`からの**相対パス**である必要があります。
    *   絶対パスや、親ディレクトリに遡る`..`のような指定は、セキュリティエラーとなります。

*   **ディレクトリの作成**:
    *   `scheduler.work_dir`で指定されたベースディレクトリは自動で作成されますが、その配下のサブディレクトリ（例: `my-project`）は、ユーザーが手動で作成する必要があります。

*   **アクセス権限**:
    *   スケジューラを実行しているユーザーが、指定された作業ディレクトリに対する読み取り・実行権限を持っている必要があります。

## 5. アーキテクチャに関する補足

*   **永続化 (Persistence)**: ジョブ定義（`cwd`や`env`を含む）は、SQLiteデータベースに永続化されます。
*   **スケジューラオブジェクトへのアクセス (Scheduler Access)**: `scheduler_instance.py`を通じて、シングルトンのスケジューラにアクセスする設計が採用されています。




