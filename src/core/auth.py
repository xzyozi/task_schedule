"""
最低限のAPIキー認証。

Shellジョブ(任意コマンド実行)を登録できるAPIが認証なしで公開される
リスクを避けるため、X-API-Key ヘッダーによる簡易な検証を提供する。

config.yaml の api.api_key (環境変数 API_KEY) が未設定の場合は認証を
無効化し、起動時に警告を出す（ローカル専用運用を前提とした緩和策）。
"""

from fastapi import Header, HTTPException, status

from util import logger_util
from util.config_util import config

logger = logger_util.get_logger(__name__)

_warned_no_api_key = False


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    FastAPI の Depends から利用する認証チェック。
    api.api_key が設定されている場合のみ、リクエストヘッダーとの一致を要求する。
    """
    global _warned_no_api_key

    expected_key = config.api_key
    if not expected_key:
        if not _warned_no_api_key:
            logger.warning(
                "API_KEY is not set. API authentication is DISABLED. "
                "This is only safe when api.host is bound to 127.0.0.1 (local-only access)."
            )
            _warned_no_api_key = True
        return

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
