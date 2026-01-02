import os

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.models.model import Webhook, Website
from core.services.webhook import WebhookService


@pytest.fixture(scope="module")
def engine():
    sqlite_file_name = "test_database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    engine = create_engine(sqlite_url, echo=True)
    SQLModel.metadata.create_all(engine)

    yield engine

    if os.path.isfile(sqlite_file_name):
        os.remove(sqlite_file_name)


class TestWebhook:
    def test_check_default_webhooks(self, engine):
        with Session(engine) as session:
            service = WebhookService(session)
            assert not service.check_default_webhooks()

        with Session(engine) as session:
            webhook = Webhook(
                name="test_check_default_webhooks",
                endpoint="https://example.com",
                service_type="discord",
            )
            session.add(webhook)
            session.commit()

            service = WebhookService(session)
            assert service.check_default_webhooks()

            session.delete(webhook)
            session.commit()

    def test_get_webhook(self, engine):
        with Session(engine) as session:
            webhook = Webhook(
                name="test_get_webhook",
                endpoint="https://example1.com",
                service_type="discord",
            )
            session.add(webhook)
            session.commit()

            service = WebhookService(session)
            webhooks = service.get_webhook()
            assert len(webhooks) == 1

            session.delete(webhook)
            session.commit()

    def test_get_target_webhook(self, engine):
        with Session(engine) as session:
            target_webhook = Webhook(
                name="test_get_target_webhook_target_webhook",
                endpoint="https://example.com/1",
                service_type="discord",
            )
            another_webhook = Webhook(
                name="test_get_target_webhook_another_webhook",
                endpoint="https://example.com/2",
                service_type="discord",
            )
            session.add(target_webhook)
            session.add(another_webhook)
            session.commit()

            service = WebhookService(session)

            one_website = Website(
                name="test_get_target_webhook",
                type="rss",
                url="https://example.com",
                target_webhook_ids="1",
            )
            webhooks = service.get_target_webhook(one_website)
            assert len(webhooks) == 1

            all_website = Website(
                name="test_get_target_webhook",
                type="rss",
                url="https://example.com",
            )
            webhooks = service.get_target_webhook(all_website)
            assert len(webhooks) == 2

            session.delete(target_webhook)
            session.delete(another_webhook)
            session.commit()
