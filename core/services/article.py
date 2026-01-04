from sqlmodel import Session

from core.config import logger
from core.models.model import Article
from core.repositories.article import ArticleRepository


class ArticleService:
    """記事サービスの管理クラス."""

    title: str
    url: str
    original_title: str | None = None  # 翻訳前のオリジナルタイトル

    def __init__(self, session: Session) -> None:
        # webhookテーブルからurlを取得するため
        self.repository = ArticleRepository(session)

    def get_article_count(self) -> int:
        """登録された記事件数を取得

        Returns:
            int: 登録された記事数
        """
        try:
            return self.repository.get_count()
        except Exception:
            logger.exception("登録記事件数取得エラー")
            raise

    def save_article(self, articles: list[Article], site_name: str) -> None:
        """取得した記事を登録.

        Parameters:
        -----------
        articles : list[Article]
            登録する記事一覧

        """
        for article in articles:
            article.hash = article.calc_hash()
            article.site_name = site_name
            self.repository.save(article)

    def delete_old_article(self) -> int:
        """古い記事を削除."""
        try:
            return self.repository.delete_old_articles(days=60)
        except Exception:
            logger.exception("定期削除エラー")
            raise
