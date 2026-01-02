"""Application-wide utils."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from core.config import TRANSLATION_API_SUCCESS_STATUS, TRANSLATION_API_URL, logger


def is_older_days(date, days: str = 30) -> bool:  # noqa: ANN001
    """指定された日時文字列が指定日付よりも古いかチェック.

    時刻部分は無視し、日付のみで比較する。

    Parameters
    ----------
        date : str
            "%Y-%m-%d %H:%M:%S" 形式の日時文字列(JST)
        days : str
            日付差分

    Returns:
        bool: 指定日数以上であれば True、そうでなければ False
    """
    jst = ZoneInfo("Asia/Tokyo")
    today = datetime.now(jst).date()
    threshold_date = today - timedelta(days=days)

    return date <= threshold_date


def translate_jp(text: str) -> str:
    """指定された文字列を日本語に翻訳.

    Parameters
    ----------
        text : str
            テキスト

    Returns:
        str: 翻訳語テキスト
    """
    if not text or not text.strip():
        return text

    if any(
        "\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9faf" for char in text
    ):
        logger.debug("日本語が含まれているため翻訳をスキップ: %s...", text[:50])
        return text

    try:
        params = {
            "q": text,
            "langpair": "en|ja",
            "de": "your-email@example.com",  # MyMemory APIでは任意のメールアドレスを指定
        }

        response = requests.get(
            TRANSLATION_API_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("responseStatus") == TRANSLATION_API_SUCCESS_STATUS:
            translated_text = data.get("responseData", {}).get(
                "translatedText",
                text,
            )
            logger.info("翻訳成功: %s... → %s...", text[:30], translated_text[:30])
            return translated_text
        logger.warning(
            "翻訳API応答エラー: %s",
            data.get("responseDetails", "Unknown error"),
        )

    except requests.RequestException:
        logger.exception("翻訳APIリクエストエラー")
        raise
    except Exception:
        logger.exception("翻訳処理エラー")
        raise
    else:
        return text
