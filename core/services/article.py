import hashlib
import logging

import requests
from models.model import Article
from repositories.article import ArticleRepository
from sqlmodel import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TRANSLATION_API_SUCCESS_STATUS = 200
TRANSLATION_API_URL = "https://api.mymemory.translated.net/get"


class ArticleService:
    """記事サービスの管理クラス."""

    title: str
    url: str
    original_title: str | None = None  # 翻訳前のオリジナルタイトル

    def __init__(self, session: Session) -> None:
        # webhookテーブルからurlを取得するため
        self.repository = ArticleRepository(session)

    def __translate_to_japanese(self, text: str) -> str:
        """テキストを日本語に翻訳."""
        if not text or not text.strip():
            return text

        if any(
            "\u3040" <= char <= "\u309f"
            or "\u30a0" <= char <= "\u30ff"
            or "\u4e00" <= char <= "\u9faf"
            for char in text
        ):
            logger.debug("日本語が含まれているため翻訳をスキップ: %s...", text[:50])
            return text

        try:
            params = {
                "q": text,
                "langpair": "en|ja",
                "de": "your-email@example.com",  # MyMemory APIでは任意のメールアドレスを指定
            }

            response = requests.get(
                TRANSLATION_API_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("responseStatus") == TRANSLATION_API_SUCCESS_STATUS:
                translated_text = data.get("responseData", {}).get(
                    "translatedText",
                    text,
                )
                logger.info("翻訳成功: %s... → %s...", text[:30], translated_text[:30])
                return translated_text
            logger.warning(
                "翻訳API応答エラー: %s",
                data.get("responseDetails", "Unknown error"),
            )

        except requests.RequestException:
            logger.exception("翻訳APIリクエストエラー")
            return text
        except Exception:
            logger.exception("翻訳処理エラー")
            return text
        else:
            return text

    def __to_embed_dict(self) -> dict[str, str]:
        """Discord埋め込み用の辞書に変換."""
        return {"title": self.title, "url": self.url}

    def __get_hash(self) -> str:
        """記事のハッシュ値を生成(重複チェック用).

        ハッシュ値はオリジナルタイトルで生成して翻訳による重複を防ぐ。
        """
        original_title = self.original_title or self.title
        content = f"{original_title}|{self.url}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def __translate_title(self) -> Article:
        """タイトルを日本語に翻訳した新しいArticleインスタンスを返す."""
        if not self.original_title:
            # 初回翻訳の場合、現在のタイトルをオリジナルとして保存
            translated_title = self.__translate_to_japanese(self.title)
            return Article(
                title=translated_title,
                url=self.url,
                original_title=self.title,
            )
        # 既に翻訳済みの場合はそのまま返す
        return self

    def save_article(self, articles: list[Article]) -> None:
        """取得した記事を登録.

        Parameters:
        -----------
        articles : list[Article]
            登録する記事一覧

        """
        for article in articles:
            self.repository.save(article)
