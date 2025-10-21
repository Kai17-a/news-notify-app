import os
import requests
import feedparser
import threading
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL") or ""
DYNAMODB_TABLE_NAME = os.getenv("RSS_TABLE") or ""


class Article(BaseModel):
    title: str
    url: str


class Website(BaseModel):
    name: str
    type: str
    url: str
    avatar: str | None = None

    def fetch_articles(self) -> list[Article]:
        raise NotImplementedError("Subclasses must implement fetch_articles()")


class RssSite(Website):
    def fetch_articles(self) -> list[Article]:
        feed = feedparser.parse(self.url)

        articles = []
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            articles.append(Article(title=title, url=link))

        return articles


class ScrapingSite(Website):
    selector: str

    def fetch_articles(self) -> list[Article]:
        response = requests.get(self.url)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        anchors = soup.select(self.selector)
        articles: list[Article] = []
        for a in anchors:
            href = a.get("href")
            if href:
                title = a.get_text(strip=True)
                articles.append(Article(title=title, url=href))

        return articles


def post_message(website: Website, articles: list[Article]) -> None:
    headers = {"Content-Type": "application/json"}

    contents = []
    for article in articles:
        contents.append({"title": article.title, "url": article.url})

    body = {
        "username": website.name,
        "avatar_url": website.avatar,
        "content": "*新着ニュース*",
        "embeds": contents,
    }

    requests.post(WEBHOOK_URL, json=body, headers=headers)


def get_news_website_list() -> list[Website]:
    result: list[Website] = []
    # DynamoDBから取得するサイト情報を取得
    result.append(
        ScrapingSite(
            name="さくらのクラウドニュース",
            type="scraping",
            url="https://cloud.sakura.ad.jp/news/",
            avatar="https://www.sakura.ad.jp/resource/favicon/sakura_logo.png",
            selector="article h1 > a",
        )
    )
    result.append(
        RssSite(
            name="Let's Encrypt",
            type="rss",
            url="https://letsencrypt.org/feed.xml",
            avatar="https://logo.svgcdn.com/simple-icons/letsencrypt-dark.png",
        )
    )
    result.append(
        RssSite(
            name="TECH FEED",
            type="rss",
            url="https://techfeed.io/feeds/categories/all?userId=68f6e4c25ae1c535159e7996",
            avatar=None,
        )
    )

    return result


def process_site(site: Website):
    try:
        articles = site.fetch_articles()
        post_message(site, articles)
        print(f"[{site.name}] 投稿完了（{len(articles)}件）")
    except Exception as e:
        print(f"[{site.name}] エラー: {e}")


def lambda_handler(event, context) -> None:
    try:
        news_sites: list[Website] = get_news_website_list()

        threads = []

        for site in news_sites:
            t = threading.Thread(target=process_site, args=(site,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    except Exception as e:
        print(f"エラーだお（＾O＾）\n{e}")

    return None


lambda_handler(None, None)
