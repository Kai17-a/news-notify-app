import hashlib
import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from datetime import timedelta, timezone
from typing import Any

import feedparser
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pydantic import BaseModel

# 定数
REQUEST_TIMEOUT = 30
MAX_ARTICLES_PER_SITE = 10
DATABASE_PATH = "news_notify_app.db"
TRANSLATION_API_URL = "https://api.mymemory.translated.net/get"

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def translate_to_japanese(text: str) -> str:
    """テキストを日本語に翻訳"""
    if not text or not text.strip():
        return text

    # 既に日本語が含まれている場合はそのまま返す
    if any(
        "\u3040" <= char <= "\u309f"
        or "\u30a0" <= char <= "\u30ff"
        or "\u4e00" <= char <= "\u9faf"
        for char in text
    ):
        logger.debug(f"日本語が含まれているため翻訳をスキップ: {text[:50]}...")
        return text

    try:
        params = {
            "q": text,
            "langpair": "en|ja",
            "de": "your-email@example.com",  # MyMemory APIでは任意のメールアドレスを指定
        }

        response = requests.get(
            TRANSLATION_API_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        if data.get("responseStatus") == 200:
            translated_text = data.get("responseData", {}).get("translatedText", text)
            logger.info(f"翻訳成功: {text[:30]}... → {translated_text[:30]}...")
            return translated_text
        else:
            logger.warning(
                f"翻訳API応答エラー: {data.get('responseDetails', 'Unknown error')}"
            )
            return text

    except requests.RequestException as e:
        logger.error(f"翻訳APIリクエストエラー: {e}")
        return text
    except Exception as e:
        logger.error(f"翻訳処理エラー: {e}")
        return text


class Article(BaseModel):
    """記事を表すデータクラス"""

    title: str
    url: str
    original_title: str | None = None  # 翻訳前のオリジナルタイトル

    def to_embed_dict(self) -> dict[str, str]:
        """Discord埋め込み用の辞書に変換"""
        return {"title": self.title, "url": self.url}

    def get_hash(self) -> str:
        """記事のハッシュ値を生成（重複チェック用）"""
        # ハッシュ値はオリジナルタイトルで生成（翻訳による重複を防ぐ）
        original_title = self.original_title or self.title
        content = f"{original_title}|{self.url}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def translate_title(self) -> "Article":
        """タイトルを日本語に翻訳した新しいArticleインスタンスを返す"""
        if not self.original_title:
            # 初回翻訳の場合、現在のタイトルをオリジナルとして保存
            translated_title = translate_to_japanese(self.title)
            return Article(
                title=translated_title, url=self.url, original_title=self.title
            )
        else:
            # 既に翻訳済みの場合はそのまま返す
            return self


class Webhook(BaseModel):
    """Webhookを表すデータクラス"""

    id: int | None = None
    name: str
    endpoint: str
    service_type: str  # discord, slack, teams, etc.
    is_active: bool = True
    created_at: str | None = None


class NotificationService(ABC):
    """通知サービスの基底クラス"""

    def __init__(self, webhook: Webhook):
        self.webhook = webhook

    @abstractmethod
    def create_payload(
        self, website: "Website", articles: list[Article]
    ) -> dict[str, Any]:
        """サービス固有のペイロードを作成"""
        pass

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """サービス固有のヘッダーを取得"""
        pass

    def send_notification(self, website: "Website", articles: list[Article]) -> bool:
        """通知を送信"""
        if not articles:
            logger.info(
                f"投稿する記事がありません: {website.name} -> {self.webhook.name}"
            )
            return True

        payload = self.create_payload(website, articles)
        headers = self.get_headers()
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.webhook.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()

                logger.info(
                    f"{self.webhook.service_type}投稿成功: {website.name} -> {self.webhook.name} ({len(articles)}件)"
                )
                return True

            except requests.RequestException as e:
                logger.error(
                    f"{self.webhook.service_type}投稿エラー [{website.name} -> {self.webhook.name}] (試行 {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    time.sleep(1)
                else:
                    return False
            except Exception as e:
                logger.error(
                    f"予期しないエラー [{website.name} -> {self.webhook.name}]: {e}"
                )
                return False


class DiscordService(NotificationService):
    """Discord通知サービス"""

    def create_payload(
        self, website: "Website", articles: list[Article]
    ) -> dict[str, Any]:
        """Discord用のペイロードを作成"""
        embeds = [article.to_embed_dict() for article in articles]

        return {
            "username": website.name,
            "avatar_url": website.avatar,
            "content": f"*新着ニュース* ({len(articles)}件)",
            "embeds": embeds,
        }

    def get_headers(self) -> dict[str, str]:
        """Discord用のヘッダーを取得"""
        return {"Content-Type": "application/json"}


class SlackService(NotificationService):
    """Slack通知サービス"""

    def create_payload(
        self, website: "Website", articles: list[Article]
    ) -> dict[str, Any]:
        """Slack用のペイロードを作成"""
        blocks = []

        # ヘッダーブロック
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📰 {website.name} - 新着ニュース ({len(articles)}件)",
                },
            }
        )

        # 記事リスト
        for article in articles:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• <{article.url}|{article.title}>",
                    },
                }
            )

        return {"username": website.name, "icon_url": website.avatar, "blocks": blocks}

    def get_headers(self) -> dict[str, str]:
        """Slack用のヘッダーを取得"""
        return {"Content-Type": "application/json"}


class TeamsService(NotificationService):
    """Microsoft Teams通知サービス"""

    def create_payload(
        self, website: "Website", articles: list[Article]
    ) -> dict[str, Any]:
        """Teams用のペイロードを作成（Adaptive Cards形式）"""
        content_body = [
            {
                "type": "TextBlock",
                "text": f"{website.name} - 新着ニュース",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True,
            }
        ]

        for article in articles:
            content_body.append(
                {
                    "type": "TextBlock",
                    "text": f"- [{article.title}]({article.url})",
                    "wrap": True,
                    "markdown": True,
                }
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
                }
            ]
        }

    def get_headers(self) -> dict[str, str]:
        """Teams用のヘッダーを取得"""
        return {"Content-Type": "application/json"}


class Website(BaseModel):
    """ウェブサイトの基底クラス"""

    id: int | None = None
    name: str
    type: str
    url: str
    avatar: str | None = None
    selector: str | None = None  # スクレイピング用セレクタ
    is_active: bool = True
    needs_translation: bool = False  # 翻訳が必要かのフラグ,
    target_webhook_ids: str | None = None
    created_at: str | None = None

    def fetch_articles(self) -> list[Article]:
        """記事を取得する抽象メソッド"""
        raise NotImplementedError("Subclasses must implement fetch_articles()")

    def _validate_url(self, url: str) -> str:
        """URLの検証と正規化"""
        if not url.startswith(("http://", "https://")):
            if self.url.endswith("/") and not url.startswith("/"):
                return f"{self.url}{url}"
            elif not self.url.endswith("/") and url.startswith("/"):
                return f"{self.url}{url}"
            else:
                return f"{self.url}/{url}"
        return url


class ArticleDatabase:
    """記事データベース管理クラス"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """データベースとテーブルを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 記事テーブル
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hash TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        site_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Webhookテーブル
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS webhooks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        endpoint TEXT NOT NULL,
                        service_type TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Websiteテーブル
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS websites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL,
                        url TEXT NOT NULL,
                        avatar TEXT,
                        selector TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        needs_translation BOOLEAN DEFAULT 0,
                        target_webhook_ids TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # インデックス作成
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_hash ON articles(hash)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_site_created ON articles(site_name, created_at)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_webhook_active ON webhooks(is_active)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_website_active ON websites(is_active)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_website_type ON websites(type)
                """
                )

                conn.commit()
                logger.info("データベース初期化完了")
        except sqlite3.Error as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise

    def is_article_exists(self, article: Article) -> bool:
        """記事が既に存在するかチェック"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM articles WHERE hash = ? LIMIT 1",
                    (article.get_hash(),),
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"記事存在チェックエラー: {e}")
            return False

    def save_article(self, article: Article, site_name: str) -> bool:
        """記事をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO articles (hash, title, url, site_name)
                    VALUES (?, ?, ?, ?)
                """,
                    (article.get_hash(), article.title, article.url, site_name),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"記事保存エラー: {e}")
            return False

    def save_articles(self, articles: list[Article], site_name: str) -> int:
        """複数の記事を一括保存"""
        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for article in articles:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO articles (hash, title, url, site_name)
                        VALUES (?, ?, ?, ?)
                    """,
                        (article.get_hash(), article.title, article.url, site_name),
                    )
                    if cursor.rowcount > 0:
                        saved_count += 1
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"記事一括保存エラー: {e}")
        return saved_count

    def filter_new_articles(self, articles: list[Article]) -> list[Article]:
        """新しい記事のみをフィルタリング"""
        new_articles = []
        for article in articles:
            if not self.is_article_exists(article):
                new_articles.append(article)
        return new_articles

    def get_article_count(self, site_name: str | None = None) -> int:
        """記事数を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if site_name:
                    cursor.execute(
                        "SELECT COUNT(*) FROM articles WHERE site_name = ?",
                        (site_name,),
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM articles")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"記事数取得エラー: {e}")
            return 0

    def cleanup_old_articles(self, days: int = 30) -> int:
        """古い記事を削除（デフォルト30日以上前）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM articles
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days)
                )
                conn.commit()
                deleted_count = cursor.rowcount
                logger.info(f"古い記事を削除: {deleted_count}件")
                return deleted_count
        except sqlite3.Error as e:
            logger.error(f"古い記事削除エラー: {e}")
            return 0

    # Webhook管理メソッド
    def add_webhook(self, webhook: Webhook) -> bool:
        """Webhookを追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO webhooks (name, endpoint, service_type, is_active)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        webhook.name,
                        webhook.endpoint,
                        webhook.service_type,
                        webhook.is_active,
                    ),
                )
                conn.commit()
                logger.info(f"Webhook追加: {webhook.name} ({webhook.service_type})")
                return True
        except sqlite3.IntegrityError:
            logger.error(f"Webhook名が重複しています: {webhook.name}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Webhook追加エラー: {e}")
            return False

    def get_active_webhooks(self) -> list[Webhook]:
        """アクティブなWebhookを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, name, endpoint, service_type, is_active, created_at
                    FROM webhooks
                    WHERE is_active = 1
                    ORDER BY created_at
                """
                )

                webhooks = []
                for row in cursor.fetchall():
                    webhook = Webhook(
                        id=row[0],
                        name=row[1],
                        endpoint=row[2],
                        service_type=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                    )
                    webhooks.append(webhook)

                return webhooks
        except sqlite3.Error as e:
            logger.error(f"Webhook取得エラー: {e}")
            return []

    def update_webhook_status(self, webhook_id: int, is_active: bool) -> bool:
        """Webhookのアクティブ状態を更新"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE webhooks SET is_active = ? WHERE id = ?
                """,
                    (is_active, webhook_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Webhook状態更新エラー: {e}")
            return False

    def delete_webhook(self, webhook_id: int) -> bool:
        """Webhookを削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Webhook削除エラー: {e}")
            return False

    # Website管理メソッド
    def add_website(self, website: Website) -> bool:
        """Websiteを追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO websites (name, type, url, avatar, selector, is_active, needs_translation, target_webhook_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        website.name,
                        website.type,
                        website.url,
                        website.avatar,
                        website.selector,
                        website.is_active,
                        website.needs_translation,
                        website.target_webhook_ids,
                    ),
                )
                conn.commit()
                logger.info(f"Website追加: {website.name} ({website.type})")
                return True
        except sqlite3.IntegrityError:
            logger.error(f"Website名が重複しています: {website.name}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Website追加エラー: {e}")
            return False

    def get_active_websites(self) -> list[Website]:
        """アクティブなWebsiteを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, name, type, url, avatar, selector, is_active, needs_translation, target_webhook_ids, created_at
                    FROM websites
                    WHERE is_active = 1
                    ORDER BY created_at
                """
                )

                websites = []
                for row in cursor.fetchall():
                    website = Website(
                        id=row[0],
                        name=row[1],
                        type=row[2],
                        url=row[3],
                        avatar=row[4],
                        selector=row[5],
                        is_active=bool(row[6]),
                        needs_translation=bool(row[7]),
                        target_webhook_ids=row[8],
                        created_at=row[9],
                    )
                    websites.append(website)

                return websites
        except sqlite3.Error as e:
            logger.error(f"Website取得エラー: {e}")
            return []

    def update_website_status(self, website_id: int, is_active: bool) -> bool:
        """Websiteのアクティブ状態を更新"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE websites SET is_active = ? WHERE id = ?
                """,
                    (is_active, website_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Website状態更新エラー: {e}")
            return False

    def delete_website(self, website_id: int) -> bool:
        """Websiteを削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM websites WHERE id = ?", (website_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Website削除エラー: {e}")
            return False


class RssSite(Website):
    """RSSフィードから記事を取得するサイト"""

    def fetch_articles(self) -> list[Article]:
        """RSSフィードから記事を取得"""
        try:
            logger.info(f"RSSフィード取得開始: {self.name}")
            feed = feedparser.parse(self.url)

            if feed.bozo:
                logger.warning(f"RSSフィードの解析に問題があります: {self.name}")

            articles = []
            for entry in feed.entries[:MAX_ARTICLES_PER_SITE]:
                if hasattr(entry, "title") and hasattr(entry, "link"):
                    title = entry.title.strip()
                    link = self._validate_url(entry.link)
                    if title and link:
                        articles.append(Article(title=title, url=link))

            logger.info(f"RSS記事取得完了: {self.name} ({len(articles)}件)")
            return articles

        except Exception as e:
            logger.error(f"RSS記事取得エラー [{self.name}]: {e}")
            return []


class ScrapingSite(Website):
    """Webスクレイピングで記事を取得するサイト"""

    def fetch_articles(self) -> list[Article]:
        """Webスクレイピングで記事を取得"""
        try:
            logger.info(f"スクレイピング開始: {self.name}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(self.url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            anchors = soup.select(self.selector or "")

            articles: list[Article] = []
            for anchor in anchors[:MAX_ARTICLES_PER_SITE]:
                href = anchor.get("href")
                if href:
                    title = anchor.get_text(strip=True)
                    if title:
                        url = self._validate_url(href)
                        articles.append(Article(title=title, url=url))

            logger.info(f"スクレイピング完了: {self.name} ({len(articles)}件)")
            return articles

        except requests.RequestException as e:
            logger.error(f"HTTP リクエストエラー [{self.name}]: {e}")
            return []
        except Exception as e:
            logger.error(f"スクレイピングエラー [{self.name}]: {e}")
            return []


# グローバルデータベースインスタンス
db = ArticleDatabase()


def create_website_instance(website: Website) -> Website:
    """WebsiteデータからWebsiteインスタンスを作成"""
    if website.type == "rss":
        return RssSite(
            id=website.id,
            name=website.name,
            type=website.type,
            url=website.url,
            avatar=website.avatar,
            selector=website.selector,
            is_active=website.is_active,
            needs_translation=website.needs_translation,
            target_webhook_ids=website.target_webhook_ids,
            created_at=website.created_at,
        )
    elif website.type == "scraping":
        return ScrapingSite(
            id=website.id,
            name=website.name,
            type=website.type,
            url=website.url,
            avatar=website.avatar,
            selector=website.selector,
            is_active=website.is_active,
            needs_translation=website.needs_translation,
            target_webhook_ids=website.target_webhook_ids,
            created_at=website.created_at,
        )
    else:
        raise ValueError(f"サポートされていないWebsiteタイプ: {website.type}")


def create_notification_service(webhook: Webhook) -> NotificationService:
    """Webhookのサービスタイプに応じて通知サービスを作成"""
    service_map = {
        "discord": DiscordService,
        "slack": SlackService,
        "teams": TeamsService,
    }

    service_class = service_map.get(webhook.service_type.lower())
    if not service_class:
        raise ValueError(f"サポートされていないサービスタイプ: {webhook.service_type}")

    return service_class(webhook)


def _send_to_webhook(
    webhook: Webhook, website: "Website", articles: list[Article]
) -> bool:
    """単一のWebhookに通知を送信"""
    try:
        service = create_notification_service(webhook)
        return service.send_notification(website, articles)
    except ValueError as e:
        logger.error(f"サービス作成エラー [{webhook.name}]: {e}")
        return False
    except Exception as e:
        logger.error(f"投稿エラー [{webhook.name}]: {e}")
        return False


def _get_target_webhooks(webhooks: list[Webhook], website: "Website") -> list[Webhook]:
    """対象となるWebhookリストを取得"""
    if not hasattr(website, "target_webhook_ids") or not website.target_webhook_ids:
        # target_webhook_ids が設定されていない場合、全てのWebhookが対象
        return webhooks

    # target_webhook_ids が設定されている場合、指定されたIDのWebhookのみ
    target_ids = [
        id.strip() for id in website.target_webhook_ids.split(",") if id.strip()
    ]
    return [webhook for webhook in webhooks if str(webhook.id) in target_ids]


def post_message(website: "Website", articles: list[Article]) -> bool:
    """全てのアクティブなWebhookに記事を投稿"""
    if not articles:
        logger.info(f"投稿する記事がありません: {website.name}")
        return True

    # アクティブなWebhookを取得
    all_webhooks = db.get_active_webhooks()
    if not all_webhooks:
        logger.error("投稿先のWebhookが設定されていません")
        return False

    # 対象となるWebhookを絞り込み
    target_webhooks = _get_target_webhooks(all_webhooks, website)
    if not target_webhooks:
        logger.warning(f"対象となるWebhookが見つかりません: {website.name}")
        return False

    # 各Webhookに並行して通知送信
    success_count = 0
    for webhook in target_webhooks:
        if _send_to_webhook(webhook, website, articles):
            success_count += 1

    # 投稿成功後、記事をデータベースに保存
    if success_count > 0:
        saved_count = db.save_articles(articles, website.name)
        logger.info(
            f"投稿完了: {website.name} ({success_count}/{len(target_webhooks)} Webhook成功, {saved_count}件DB保存)"
        )
        return True
    else:
        logger.error(f"全てのWebhookで投稿に失敗: {website.name}")
        return False


def get_news_website_list() -> list[Website]:
    """ニュースサイトのリストをデータベースから取得"""
    website_data_list = db.get_active_websites()

    if not website_data_list:
        logger.warning("データベースにアクティブなWebsiteが見つかりません")
        return []

    websites: list[Website] = []
    for website_data in website_data_list:
        try:
            website_instance = create_website_instance(website_data)
            websites.append(website_instance)
        except ValueError as e:
            logger.error(f"Website作成エラー: {e}")
            continue

    logger.info(f"ニュースサイト数: {len(websites)}")
    return websites


def process_site(site: "Website") -> bool:
    """サイトの記事を処理してDiscordに投稿"""
    try:
        logger.info(f"サイト処理開始: {site.name}")

        # 記事を取得
        all_articles = site.fetch_articles()
        if not all_articles:
            logger.info(f"取得記事なし: {site.name}")
            return True

        # 新しい記事のみをフィルタリング
        new_articles = db.filter_new_articles(all_articles)
        if not new_articles:
            logger.info(
                f"新着記事なし: {site.name} (取得: {len(all_articles)}件, 既存: {len(all_articles)}件)"
            )
            return True

        logger.info(
            f"新着記事発見: {site.name} (取得: {len(all_articles)}件, 新着: {len(new_articles)}件)"
        )

        # 翻訳が必要な場合はタイトルを翻訳
        if site.needs_translation:
            logger.info(f"記事タイトルを翻訳中: {site.name}")
            translated_articles = []
            for article in new_articles:
                translated_article = article.translate_title()
                translated_articles.append(translated_article)
            new_articles = translated_articles

        # 新しい記事のみを投稿
        success = post_message(site, new_articles)
        if success:
            logger.info(f"サイト処理完了: {site.name} ({len(new_articles)}件投稿)")
        else:
            logger.error(f"サイト処理失敗: {site.name}")

        return success

    except Exception as e:
        logger.error(f"サイト処理中の予期しないエラー [{site.name}]: {e}")
        return False


def initialize_default_webhooks() -> None:
    """デフォルトのWebhookを初期化"""
    webhooks = db.get_active_webhooks()
    if not webhooks:
        logger.info(
            "Webhookが設定されていません。データベースにWebhookを追加してください。"
        )


def main() -> None:
    """メイン処理：全サイトの記事を並行処理で取得・投稿"""
    try:
        logger.info("ニュース収集処理開始")

        # デフォルトWebhookの初期化
        initialize_default_webhooks()

        # データベース統計情報を出力
        total_articles = db.get_article_count()
        webhook_count = len(db.get_active_webhooks())
        logger.info(
            f"データベース記事数: {total_articles}件, アクティブWebhook数: {webhook_count}件"
        )

        # 古い記事のクリーンアップ（30日以上前の記事を削除）
        if total_articles > 1000:  # 記事数が多い場合のみクリーンアップ
            db.cleanup_old_articles(30)

        news_sites = get_news_website_list()
        if not news_sites:
            logger.warning("処理対象のサイトがありません")
            return

        threads = []
        results = {}

        def thread_wrapper(site: "Website"):
            """スレッド用のラッパー関数"""
            results[site.name] = process_site(site)

        # 各サイトを並行処理
        for site in news_sites:
            thread = threading.Thread(
                target=thread_wrapper, args=(site,), name=f"Thread-{site.name}"
            )
            thread.start()
            threads.append(thread)

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()

        # 結果の集計
        successful = sum(1 for success in results.values() if success)
        total = len(results)

        # サイト別の記事数統計
        for site in news_sites:
            site_count = db.get_article_count(site.name)
            logger.info(f"[{site.name}] 登録記事数: {site_count}件")

        logger.info(f"ニュース収集処理完了: {successful}/{total} サイト成功")

    except Exception as e:
        logger.error(f"メイン処理でエラーが発生しました: {e}")


def run_scheduler() -> None:
    """スケジューラーを実行"""
    try:
        logger.info("スケジューラー開始")
        scheduler = BlockingScheduler()
        # 日本時間（UTC+9）のタイムゾーン
        jst = timezone(timedelta(hours=9))

        scheduler.add_job(
            main,
            "cron",
            hour=9,
            minute=0,
            timezone=jst,
            id="news_collector",
            max_instances=1,  # 同時実行を防ぐ
            misfire_grace_time=300,
            coalesce=False,
        )
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("スケジューラーが停止されました")
    except Exception as e:
        logger.error(f"スケジューラーエラー: {e}")


def run_once() -> None:
    """ニュース収集を1回だけ実行"""
    logger.info("ニュース収集を手動実行します")
    try:
        main()
        logger.info("ニュース収集の手動実行が完了しました")
    except Exception as e:
        logger.error(f"手動実行エラー: {e}")


if __name__ == "__main__":
    run_scheduler()
