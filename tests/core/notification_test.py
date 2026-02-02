import os

from dotenv import load_dotenv
import pytest

from core.models.model import Article, Webhook, Website
from core.services.notification import DiscordService, SlackService


@pytest.fixture(scope="module")
def engine():
    yield engine


load_dotenv()

article = Article(
    title="test",
    url="https://example.com",
    site_name="test",
)

website = Website(
    name="テスト",
    type="rss",
    url="https://letsencrypt.org/feed.xml",
)


class TestNotification:
    def test_discord(self):
        webhook = Webhook(
            name="Discord",
            endpoint=os.environ.get("TEST_WEBHOOK_DISCORD"),
            service_type="discord",
        )
        service = DiscordService(webhook)
        result = service.send_notification(website, articles=[article])

        assert result

    def test_slack(self):
        webhook = Webhook(
            name="slack",
            endpoint=os.environ.get("TEST_WEBHOOK_SLACK"),
            service_type="slack",
        )
        service = SlackService(webhook)
        result = service.send_notification(website, articles=[article])

        assert result

    # 環境がないため実施しない
    # def test_teams():
    #     pass
