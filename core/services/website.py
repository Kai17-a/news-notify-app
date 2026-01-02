from sqlmodel import Session

from core.config import logger
from core.models.model import Website
from core.repositories.website import WebsiteRepository


class WebsiteService:
    """ウェブサイトサービスの基底クラス."""

    def __init__(self, session: Session) -> None:
        self.repository = WebsiteRepository(session)

    def save(self, website: Website) -> None:
        """Website情報を登録."""
        try:
            self.repository.save(website)
        except Exception:
            logger.exception("Website追加エラー")
            raise

    def get_website_with_active(self) -> list[Website]:
        """有効なWebsite情報取得."""
        try:
            return self.repository.get_all_with_active()
        except Exception:
            logger.exception("Website取得エラー")
            raise

    def update_website(self, website: Website) -> None:
        """Website情報を更新.

        Parameters:
        -----------
        website : Article
            更新する記事
        """
        try:
            self.repository.update(website)
        except Exception:
            logger.exception("Website更新エラー")
            raise

    def delete_website(self, website_id: int) -> None:
        """Website情報を削除.

        Parameters:
        -----------
        website_id : int
            削除する記事ID
        """
        try:
            self.repository.delete_by_id(website_id)
        except Exception:
            logger.exception("Website更新エラー")
            raise
