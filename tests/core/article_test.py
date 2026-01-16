import os

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from core.models.model import Article
from core.services.article import ArticleService


@pytest.fixture(scope="module")
def engine():
    sqlite_file_name = "test_database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    engine = create_engine(sqlite_url, echo=False)
    SQLModel.metadata.create_all(engine)

    yield engine

    if os.path.isfile(sqlite_file_name):
        os.remove(sqlite_file_name)


class TestArticle:
    def test_get_article_with_offset(self, engine):
        test_article_data = [
            Article(
                hash="",
                title="test_get_article_with_offset1",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
            Article(
                hash="",
                title="test_get_article_with_offset2",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
            Article(
                hash="",
                title="test_get_article_with_offset3",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
            Article(
                hash="",
                title="test_get_article_with_offsett4",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
            Article(
                hash="",
                title="test_get_article_with_offset5",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
        ]

        with Session(engine) as session:
            service = ArticleService(session)
            service.save_article(test_article_data, "test_site")
            session.commit()

            articles = service.get_articles_with_offset(1, 3)
            assert len(articles) == 3
            articles = service.get_articles_with_offset(2, 3)
            assert len(articles) == 2
            articles = service.get_articles_with_offset(3, 3)
            assert len(articles) == 0

            for article in test_article_data:
                session.delete(article)
            session.commit()

    def test_save_article(self, engine):
        test_article_data = Article(
            hash="", title="test", url="https://example.com", site_name="", created_at="2000-01-01"
        )

        with Session(engine) as session:
            service = ArticleService(session)
            service.save_article([test_article_data], "test_site")
            session.commit()

            article = session.exec(select(Article)).first()
            assert article is not None
            assert article.title == "test"
            assert article.site_name == "test_site"

            session.delete(article)
            session.commit()

    def test_delete_old_article(self, engine):
        test_article_data = [
            Article(
                hash="",
                title="delete_test1",
                url="https://example.com",
                site_name="",
                created_at="2024-01-01 12:00:00",
            ),
            Article(
                hash="",
                title="not_delete_test2",
                url="https://example.com",
                site_name="",
                created_at="2026-01-01 12:00:00",
            ),
        ]

        with Session(engine) as session:
            service = ArticleService(session)
            service.save_article(test_article_data, "test_site")
            session.commit()

            result = service.delete_old_article()
            articles = session.exec(select(Article)).all()

            assert result == 1
            assert len(articles) == 1
            assert articles[0].title == "not_delete_test2"
