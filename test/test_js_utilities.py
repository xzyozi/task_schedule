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
