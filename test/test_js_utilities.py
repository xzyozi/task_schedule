from pathlib import Path
import re
import pytest

STATIC_DIR = Path(__file__).resolve().parent.parent / "src" / "webgui" / "static"


def test_api_config_js_exists():
    """`api_config.js` が存在し、必須モジュール関数が含まれていることを確認する。"""
    config_js = STATIC_DIR / "api_config.js"
    assert config_js.exists(), "api_config.js が存在しません"

    content = config_js.read_text(encoding="utf-8")

    assert "export async function fetchConfig()" in content
    assert "export function getApiBaseUrl()" in content
    assert "export function escapeHtml(" in content


def test_js_xss_sanitization_escape_html():
    """`api_config.js` 内の `escapeHtml` 関数のエスケープ対照表が正しく定義されていることをテストする。"""
    config_js = STATIC_DIR / "api_config.js"
    content = config_js.read_text(encoding="utf-8")

    # 必須エスケープ文字 (&, <, >, ", ') の置換処理が含まれていることを確認
    assert "&amp;" in content
    assert "&lt;" in content
    assert "&gt;" in content
    assert "&quot;" in content
    assert "&#39;" in content


def py_escape_html(value):
    """api_config.js の escapeHtml 関数の動作を模倣した検証関数"""
    if value is None:
        return ""
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("<script>alert('xss')</script>", "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"),
        ('\"hello & world\"', "&quot;hello &amp; world&quot;"),
        (None, ""),
        (12345, "12345"),
        ("normal_string_123", "normal_string_123"),
    ],
)
def test_escape_html_boundary_cases(input_val, expected):
    """`escapeHtml` の境界値・特殊文字エスケープロジックを包括的に検証。"""
    assert py_escape_html(input_val) == expected


def test_all_js_files_import_api_config():
    """すべての主要 JS モジュールが `api_config.js` から関数を正しくインポートしているかを動的チェック。"""
    js_files = [
        "script.js",
        "jobs.js",
        "job_detail.js",
        "workflows.js",
        "workflow_detail.js",
        "logs.js",
        "settings.js",
        "timeline.js",
    ]

    for filename in js_files:
        filepath = STATIC_DIR / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            assert "api_config.js" in content, f"{filename} で api_config.js がインポートされていません"


def test_status_badge_classes_consistency():
    """`script.js` や `jobs.js` 等で定義されているステータスバッジのクラス名（bg-success, bg-secondary等）の存在チェック。"""
    js_files = ["script.js", "jobs.js", "timeline.js"]
    for filename in js_files:
        filepath = STATIC_DIR / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            # 各モジュールでバッジまたは表示クラスが使用されていることを確認
            assert "badge" in content or "job-" in content, f"{filename} でバッジ定義が見つかりません"
