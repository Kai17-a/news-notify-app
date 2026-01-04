from sqlmodel import Session

from core.config import logger
from core.models.model import Webhook, Website
from core.repositories.webhook import WebhookRepository


class WebhookService:
    """Webhookサービスの基底クラス."""

    def __init__(self, session: Session) -> None:
        self.repository = WebhookRepository(session)

    def check_default_webhooks(self) -> bool:
        """デフォルトのWebhookを初期化."""
        try:
            webhooks = self.get_webhook()
            if not webhooks:
                logger.info(
                    "Webhookが設定されていません。データベースにWebhookを追加してください。",
                )
                return False
        except Exception:
            logger.exception("Webhook取得エラー")
            raise
        return True

    def get_webhook(self) -> list[Webhook]:
        """Webhook情報を登録."""
        webhooks = []
        try:
            webhooks = self.repository.get_all()
        except Exception:
            logger.exception("Webhook取得エラー")
            raise
        else:
            return webhooks

    def get_webhook_by_id(self, webhook_id: int) -> Webhook:
        """IDでWebhook情報を取得."""
        try:
            webhook = self.repository.get_by_id(webhook_id)
        except Exception:
            logger.exception("Webhook取得エラー")
            raise
        else:
            return webhook

    def get_target_webhook(self, website: Website) -> list[Webhook]:
        """送信対象Webhook情報を登録."""
        webhooks = self.get_webhook()

        if not hasattr(website, "target_webhook_ids") or not website.target_webhook_ids:
            return webhooks

        target_ids = [
            target_webhook_id.strip()
            for target_webhook_id in website.target_webhook_ids.split(",")
            if target_webhook_id.strip()
        ]

        return [webhook for webhook in webhooks if str(webhook.id) in target_ids]
