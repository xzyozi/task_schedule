# WIPブランチからの参考資料保管

このディレクトリは、削除済みのリモートブランチ `feat/20250921-temp`
（最終コミット 2025-09-21, "WIP"）から、コードとしてはそのまま使えないが
設計アイデアとして参考価値のある部分のみを保存したものです。

## 経緯

- `feat/20250921-temp` は `src/webgui/` 配下の旧構成（現行は
  `src/modules/scheduler/` 構成へリファクタリング済み）を前提にした
  WIPコミットで、11ヶ月間更新が止まっていました。
- ダッシュボードのタイムラインを自前実装（`dashboard.js` + カスタムCSS）
  で作る内容でしたが、現行の `src/webgui/static/timeline.js` は
  vis.js ベースの実装に置き換わっており、そのまま統合はできません。
- 一方で `doc/gui.md` に追記されていたタイムラインの
  **フィルタリング／ズーム／グルーピング／レスポンシブ対応**の改善提案は、
  現行ドキュメントに未反映のアイデアとして参考価値があるため保管します。

## ファイル一覧

- `dashboard.js`: 旧WIPのタイムライン描画スクリプト（そのまま動作はしません）
- `timeline_style.css`: 旧WIPのタイムラインCSS（`style.css`からタイムライン関連部分のみ抜粋）
- `gui_md_improvement_proposal.diff`: `doc/gui.md`に対する改善提案の差分
  （フィルタ・ズーム・クラスタリング・レスポンシブ対応の設計案）

## 今後の扱い

これらは実装への即時採用を意図したものではなく、将来ダッシュボードの
タイムライン機能を拡張する際の参考資料です。実装する場合は現行の
vis.js ベースの `timeline.js` / `src/modules/scheduler/router.py` の
`/api/timeline/data` に対して、`gui_md_improvement_proposal.diff` の
アイデアを移植する形になります。

元のブランチ (`origin/feat/20250921-temp`, `origin/temp/20250916`) は
削除済みです。
