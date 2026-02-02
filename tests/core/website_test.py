import os

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from core.models.model import Website
from core.services.website import WebsiteService


@pytest.fixture(scope="module")
def engine():
    sqlite_file_name = "test_database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    engine = create_engine(sqlite_url, echo=False)
    SQLModel.metadata.create_all(engine)

    yield engine

    if os.path.isfile(sqlite_file_name):
        os.remove(sqlite_file_name)


class TestWebsite:
    def test_save(self, engine):
        website = Website(
            name="test_save",
            type="rss",
            url="https://letsencrypt.org/feed.xml",
        )

        with Session(engine) as session:
            service = WebsiteService(session)

            service.save(website)
            session.commit()

            result = session.exec(select(Website)).first()
            assert result is not None
            assert result.name == "test_save"

            session.delete(website)
            session.commit()

    def test_get_website_with_active(self, engine):
        active_website = Website(
            name="test_get_website_with_active",
            type="rss",
            url="https://example1.com",
            is_active=True,
        )
        inactive_website = Website(
            name="test_get_website_with_inactive",
            type="rss",
            url="https://example2.com",
            is_active=False,
        )

        with Session(engine) as session:
            session.add(active_website)
            session.add(inactive_website)
            session.commit()

            results = session.exec(select(Website)).all()
            assert len(results) == 2

            service = WebsiteService(session)
            results = service.get_website_with_active()
            assert len(results) == 1

            session.delete(active_website)
            session.delete(inactive_website)
            session.commit()

    def test_update_website(self, engine):
        website = Website(
            name="test_update_website",
            type="rss",
            url="https://example.com",
        )

        with Session(engine) as session:
            session.add(website)
            session.commit()

            results = session.exec(select(Website)).all()
            assert len(results) == 1

            service = WebsiteService(session)

            website.name = "updated"
            service.update_website(website)
            session.commit()

            result = session.exec(select(Website)).first()
            assert result is not None
            assert result.name == "updated"
            assert result.url == "https://example.com"

            session.delete(website)
            session.commit()

    def test_delete_website(self, engine):
        website = Website(
            name="test_delete_website",
            type="rss",
            url="https://example.com",
        )

        with Session(engine) as session:
            session.add(website)
            session.commit()

            results = session.exec(select(Website)).all()
            assert len(results) == 1

            service = WebsiteService(session)

            service.delete_website(1)
            session.commit()

            results = session.exec(select(Website)).all()
            assert len(results) == 0
