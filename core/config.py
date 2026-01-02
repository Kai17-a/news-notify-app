"""Application-wide configuration and constants."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


TRANSLATION_API_SUCCESS_STATUS = 200
TRANSLATION_API_URL = "https://api.mymemory.translated.net/get"
MAX_ARTICLES_PER_SITE = 15
