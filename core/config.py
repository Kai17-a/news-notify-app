"""Application-wide configuration and constants."""

import logging

logging.basicConfig(
    # filename="app.log",
    # filemode="w",
    # encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    # force=True,
)
logger = logging.getLogger(__name__)


TRANSLATION_API_SUCCESS_STATUS = 200
TRANSLATION_API_URL = "https://api.mymemory.translated.net/get"
MAX_ARTICLES_PER_SITE = 10
