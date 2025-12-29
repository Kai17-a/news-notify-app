import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from models.model import Article, Webhook, Website
from repositories.webhook import WebhookRepository
from sqlmodel import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class __NotificationServiceImpl(ABC):
    """通知サービスの基底クラス."""

    def __init__(self, webhook: Webhook) -> None:
        self.webhook = webhook

    @abstractmethod
    def create_payload(
        self,
        website: Website,
        articles: list[Article],
    ) -> dict[str, Any]:
        """サービス固有のペイロードを作成."""

    def send_notification(self, website: Website, articles: list[Article]) -> bool:
        """通知を送信."""
        if not articles:
            logger.info(
                "投稿する記事がありません: %s -> %s",
                website.name,
                self.webhook.name,
            )
            return True

        payload = self.create_payload(website, articles)
        headers = {"Content-Type": "application/json"}
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    url=self.webhook.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()

            except requests.RequestException:
                logger.exception(
                    "%s投稿エラー [%s -> %s] (試行 %d/%d)",
                    self.webhook.service_type,
                    website.name,
                    self.webhook.name,
                    attempt,
                    max_retries,
                )
                if attempt < max_retries:
                    time.sleep(1)
                else:
                    return False
            except Exception:
                logger.exception(
                    "予期しないエラー [%s -> %s]",
                    website.name,
                    self.webhook.name,
                )
                return False
            else:
                logger.info(
                    "%s投稿成功: %s -> %s (%d件)",
                    self.webhook.service_type,
                    website.name,
                    self.webhook.name,
                    len(articles),
                )
                return True
        return None


class DiscordService(__NotificationServiceImpl):
    """Discord通知サービス."""

    def create_payload(
        self,
        website: Webhook,
        articles: list[Article],
    ) -> dict[str, Any]:
        """Discord用のペイロードを作成."""
        embeds = [article.to_embed_dict() for article in articles]

        return {
            "username": website.name,
            "avatar_url": website.avatar,
            "content": f"*新着ニュース* ({len(articles)}件)",
            "embeds": embeds,
        }


class SlackService(__NotificationServiceImpl):
    """Slack通知サービス."""

    def create_payload(
        self,
        website: Website,
        articles: list[Article],
    ) -> dict[str, Any]:
        """Slack用のペイロードを作成."""
        blocks = []

        # ヘッダーブロック
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📰 {website.name} - 新着ニュース ({len(articles)}件)",
                },
            },
        )

        # 記事リスト
        for article in articles:
            blocks.extend(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• <{article.url}|{article.title}>",
                    },
                },
            )

        return {"username": website.name, "icon_url": website.avatar, "blocks": blocks}


class TeamsService(__NotificationServiceImpl):
    """Microsoft Teams通知サービス."""

    def create_payload(
        self,
        website: Website,
        articles: list[Article],
    ) -> dict[str, Any]:
        """Teams用のペイロードを作成(Adaptive Cards形式)."""
        content_body = [
            {
                "type": "TextBlock",
                "text": f"{website.name} - 新着ニュース",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True,
            },
        ]

        for article in articles:
            content_body.extend(
                {
                    "type": "TextBlock",
                    "text": f"- [{article.title}]({article.url})",
                    "wrap": True,
                    "markdown": True,
                },
            )

        return {
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": content_body,
                    },
                },
            ],
        }


class NotificationService:
    """通知サービスの管理クラス."""

    def __init__(self, session: Session) -> None:
        # webhookテーブルからurlを取得するため
        self.repository = WebhookRepository(session)

    def post_message(self, service: __NotificationServiceImpl) -> None:
        """Send a notification message via webhook.

        Parameters:
        -----------
        service : __NotificationServiceImpl
            The notification service used to send the message.

        Raises:
        -------
        requests.RequestException
            If sending the request to the webhook fails.
        """
        service.send_notification()
