import pytest

from core.models.model import Website
from core.services.fetcher import FetcherService


@pytest.fixture(scope="module")
def engine():
    yield engine


class TestFetcher:
    def test_fetch_rss(self):
        website = Website(
            name="Let's encrypt",
            type="rss",
            url="https://letsencrypt.org/feed.xml",
        )
        service = FetcherService(website, None)
        articles = service.fetch_rss()

        assert len(articles) > 0

    def test_fetch_scrap(self):
        website = Website(
            name="さくらのクラウドニュース",
            type="scraping",
            url="https://cloud.sakura.ad.jp/news/",
            avatar="https://www.sakura.ad.jp/resource/favicon/sakura_logo.png",
            selector="article h1 > a",
        )
        service = FetcherService(website, None)
        articles = service.fetch_scrap()

        assert len(articles) > 0
