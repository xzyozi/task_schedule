# JS/HTML整形ツール(Prettier)導入手順

## 背景

`ruff` はPythonコードの整形・lintを行うが、`src/webgui/static/*.js` や
`src/webgui/templates/*.html` はJavaScript/HTMLであり対象外。これらの
整形には別ツールが必要。

作業時点のローカル環境には Node.js / npm が未インストールのため、
このドキュメントでは導入手順のみ記録し、実際の適用（CIワークフロー
への追加、コード整形の実行）は未実施とする。

## 推奨ツール: Prettier

- JS/HTML/CSSなど幅広い言語に対応した定番フォーマッタ
- lintは行わず整形のみ（lintが必要な場合はESLint等を別途検討）
- `package.json` を作らず `npx` 経由でも実行可能なため、既存のPython
  中心プロジェクトに軽量に導入できる

代替候補として Biome（Rust製、Prettier互換で高速）も検討したが、
HTML対応が本稿作成時点では実験的段階のため見送った。

## 前提: Node.js / npm のインストール

1. https://nodejs.org/ からLTS版をインストール（Windows用インストーラ）
2. インストール後、確認:

```powershell
node --version
npm --version
```

- npmのサプライチェーン対策として、`project-basics.md` の方針に従い
  `~/.npmrc` に `min-release-age=3` を設定すること（npm v11.10.0以降）

## ローカルでの実行方法

プロジェクトルートで以下を実行（`package.json` 不要、都度ダウンロード実行）。

```powershell
# チェックのみ（差分があれば非ゼロ終了）
npx --yes prettier@3 --check "src/webgui/static/**/*.js" "src/webgui/templates/**/*.html"

# 実際に整形を適用
npx --yes prettier@3 --write "src/webgui/static/**/*.js" "src/webgui/templates/**/*.html"
```

頻繁に使う場合は `package.json` を作成し `devDependencies` に固定バージョンで
`prettier` を追加する方法もある（`npx` は毎回ダウンロードが発生するため）。

```json
{
  "devDependencies": {
    "prettier": "3.3.3"
  }
}
```

```powershell
npm install
npx prettier --check "src/webgui/static/**/*.js" "src/webgui/templates/**/*.html"
```

## CI (.github/workflows/ci.yml) への追加案

`ci` ジョブに以下のステップを追加する（Python側のステップの後ろに追記）。

```yaml
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Run Prettier (Formatter Check)
        run: |
          npx --yes prettier@3 --check "src/webgui/static/**/*.js" "src/webgui/templates/**/*.html"
```

## 未実施事項

- Node.js/npmのローカル環境構築（ユーザー環境に未インストール）
- 上記CIステップの `.github/workflows/ci.yml` への実際の追加
- `prettier --write` による既存JS/HTMLファイルへの初回整形適用
  （初回適用時は差分が大きくなるため、他の変更と分けて別コミット・別PR
  で行うことを推奨）

## 参考

- Prettier公式: https://prettier.io/
- Prettier CLI options: https://prettier.io/docs/en/cli.html
