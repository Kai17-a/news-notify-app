import itertools

import feedparser
import requests
from bs4 import BeautifulSoup
from sqlmodel import Session

from core.config import MAX_ARTICLES_PER_SITE, logger
from core.models.model import Article, Website
from core.repositories.article import ArticleRepository
from core.repositories.website import WebsiteRepository


class FetcherService:
    """記事取得."""

    def __init__(self, website: Website, session: Session) -> None:
        self.article_repository = ArticleRepository(session)
        self.website_repository = WebsiteRepository(session)
        self.website = website

    def __validate_url(self, url: str) -> str:
        """URLの検証と正規化."""
        if not url.startswith(("http://", "https://")):
            if (url.endswith("/") and not url.startswith("/")) or (
                not url.endswith("/") and url.startswith("/")
            ):
                return f"{url}{url}"
            return f"{url}/{url}"
        return url

    def __is_already_fetched(self, article: Article) -> bool:
        """過去に取得している記事か."""
        return self.article_repository.get_by_url(article.url) is not None

    def fetch_rss(self) -> list[Article]:
        """RSSフィードから記事を取得."""
        articles: list[Article] = []

        try:
            logger.info("RSSフィード取得開始: %s", self.website.name)
            feed = feedparser.parse(self.website.url)

            if feed.bozo:
                logger.warning(
                    "RSSフィードの解析に問題があります: %s",
                    self.website.name,
                )

            for entry in feed.entries[:MAX_ARTICLES_PER_SITE]:
                if hasattr(entry, "title") and hasattr(entry, "link"):
                    title = entry.title.strip()
                    link = self.__validate_url(entry.link)
                    if title and link:
                        articles.append(Article(title=title, url=link))

            logger.info("RSS記事取得完了: %s (%s件)", self.website.name, len(articles))

        except Exception:
            logger.exception("RSS記事取得エラー [%s]", self.website.name)
            raise
        else:
            return list(
                itertools.filterfalse(
                    lambda x: self.__is_already_fetched(x),
                    articles,
                ),
            )

    def fetch_scrap(self) -> list[Article]:
        """Webサイトから記事を取得."""
        articles: list[Article] = []

        try:
            logger.info("スクレイピング開始: %s", self.website.name)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            response = requests.get(self.website.url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            anchors = soup.select(self.website.selector or "")

            for anchor in anchors[:MAX_ARTICLES_PER_SITE]:
                href = anchor.get("href")
                if href:
                    title = anchor.get_text(strip=True)
                    if title:
                        url = self.__validate_url(href)
                        articles.append(Article(title=title, url=url))

            logger.info(
                "スクレイピング完了: %s (%s)",
                self.website.name,
                len(articles),
            )

        except requests.RequestException:
            logger.exception("HTTP リクエストエラー [%s]", self.website.name)
            raise
        except Exception:
            logger.exception("スクレイピングエラー [%s]", self.website.name)
            raise
        else:
            return list(
                itertools.filterfalse(lambda x: self.__is_already_fetched(x), articles),
            )
