import logging

import feedparser
import requests
from bs4 import BeautifulSoup
from models.model import Article, Website
from repositories.website import WebsiteRepository
from sqlmodel import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_SITE = 10


class FetcherService:
    """記事取得."""

    def __init__(self, website: Website, session: Session) -> None:
        self.repository = WebsiteRepository(session)
        self.website = website

    def __validate_url(self) -> str:
        """URLの検証と正規化."""
        if not self.website.url.startswith(("http://", "https://")):
            if (
                self.website.url.endswith("/") and not self.website.url.startswith("/")
            ) or (
                not self.website.url.endswith("/") and self.website.url.startswith("/")
            ):
                return f"{self.website.url}{self.website.url}"
            return f"{self.website.url}/{self.website.url}"
        return self.website.url

    def fetch_rss(self) -> list[Article]:
        """RSSフィードから記事を取得."""
        articles = []

        try:
            logger.info("RSSフィード取得開始: %s", self.website.name)
            feed = feedparser.parse(self.website.url)

            if feed.bozo:
                logger.warning(
                    "RSSフィードの解析に問題があります: %s",
                    self.website.name,
                )

            articles = []
            for entry in feed.entries[:MAX_ARTICLES_PER_SITE]:
                if hasattr(entry, "title") and hasattr(entry, "link"):
                    title = entry.title.strip()
                    link = self.__validate_url(entry.link)
                    if title and link:
                        articles.append(Article(title=title, url=link))

            logger.info("RSS記事取得完了: %s (%s件)", self.website.name, len(articles))

        except Exception:
            logger.exception("RSS記事取得エラー [%s]", self.website.name)

        else:
            return articles

    def fetch_scrap(self) -> list[Article]:
        """Webサイトから記事を取得."""
        article = []

        try:
            logger.info("スクレイピング開始: %s", self.website.name)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            anchors = soup.select(self.selector or "")

            articles: list[Article] = []
            for anchor in anchors[:MAX_ARTICLES_PER_SITE]:
                href = anchor.get("href")
                if href:
                    title = anchor.get_text(strip=True)
                    if title:
                        url = self._validate_url(href)
                        articles.append(Article(title=title, url=url))

            logger.info(
                "スクレイピング完了: %s (%s)",
                self.website.name,
                len(article),
            )

        except requests.RequestException:
            logger.exception("HTTP リクエストエラー [%s]", self.website.name)
        except Exception:
            logger.exception("スクレイピングエラー [%s]", self.website.name)
        else:
            return articles
