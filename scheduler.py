import argparse
import threading
from datetime import timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlmodel import Session, create_engine

from app import SlackService
from core.config import logger
from core.models.model import Website, WebsiteType
from core.services.article import ArticleService
from core.services.fetcher import FetcherService
from core.services.notification import (
    DiscordService,
    NotificationService,
)

# from core.services.webhook import WebhookService
from core.services.webhook import WebhookService
from core.services.website import WebsiteService

# デバッグモードを指定するオプション
# 有効にすると SQLModel のデバッグログが出力される
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="デバッグモード")
args = parser.parse_args()

sqlite_file_name = "news_notify_app.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=args.debug)


def process_site(website: Website, session: Session) -> bool:
    """サイトの記事を処理して投稿."""
    try:
        article_service = ArticleService(session)
        fetcher_service = FetcherService(website, session)
        notification_service = NotificationService(session)
        logger.info(f"サイト処理開始: {website.name}")

        # 記事を取得
        articles = []
        if website.type == WebsiteType.RSS.value:
            articles = fetcher_service.fetch_rss()
        elif website.type == WebsiteType.SCRAPING.value:
            articles = fetcher_service.fetch_scrap()
        else:
            msg = f"想定しないウェブサイトタイプ: {website.name}"
            logger.exception(msg)
            return False

        webhook_service = WebhookService(session)
        webhooks = webhook_service.get_target_webhook(website)

        if not webhooks:
            logger.warning("対象となるwebhook情報が見つかりません: %s", website.name)
            return False

        success_count = 0
        for webhook in webhooks:
            webhook_service_map = {
                "discord": DiscordService,
                "slack": SlackService,
                # "teams": TeamsService,
            }

            service_class = webhook_service_map.get(webhook.service_type.lower())
            if not service_class:
                msg = f"サポートされていないサービスタイプ: {webhook.service_type}"
                logger.warning(msg)
                return False

            target_webhook_service = service_class(webhook)

            notification_service.post_message(target_webhook_service, website, articles)
            success_count += 1

        # 投稿成功後、記事をデータベースに保存
        if success_count > 0:
            saved_count = article_service.save_article(articles, website.name)
            msg = f"投稿完了: {website.name} ({success_count}/{len(webhooks)} Webhook成功, {saved_count}件DB保存)"
            logger.info(msg)
        else:
            msg = f"全てのWebhookで投稿に失敗: {website.name}"
            logger.exception(msg)
            return False

    except Exception:  # noqa: BLE001
        logger.exception("サイト処理中の予期しないエラー [%s]", website.name)
        return False
    else:
        return True


def main() -> None:
    """メイン処理: 全サイトの記事を並行処理で取得・投稿."""
    with Session(engine) as session:
        article_service = ArticleService(session)
        website_service = WebsiteService(session)

        # 古い記事のクリーンアップ
        deleted_article_num = article_service.delete_old_article()
        logger.info("前処理: %d件の記事を削除しました", deleted_article_num)

        logger.info("ニュース収集処理開始")
        # 取得するサイト情報取得
        websites = website_service.get_website_with_active()
        if not websites:
            logger.exception("処理対象のサイトがありません")
            return

        threads = []
        results = {}

        def thread_wrapper(website: Website) -> None:
            """スレッド用のラッパー関数."""
            with Session(engine) as session:
                results[website.name] = process_site(website, session)
                session.commit()

        # 各サイトを並行処理
        for website in websites:
            thread = threading.Thread(
                target=thread_wrapper,
                args=(website,),
                name=f"Thread-{website.name}",
            )
            thread.start()
            threads.append(thread)

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()

        # 結果の集計
        successful = sum(1 for success in results.values() if success)
        total = len(results)

        logger.info(f"ニュース収集処理完了: {successful}/{total} サイト成功")

        session.commit()


def run_scheduler() -> None:
    """スケジューラー実行."""
    try:
        logger.info("スケジューラー開始")
        scheduler = BlockingScheduler()
        # 日本時間(UTC+9)のタイムゾーン
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
    except Exception as e:  # noqa: BLE001
        logger.error(f"スケジューラーエラー: {e}")


def run_once() -> None:
    """ニュース収集を1回だけ実行."""
    logger.info("ニュース収集を手動実行します")
    try:
        main()
        logger.info("ニュース収集の手動実行が完了しました")
    except Exception as e:  # noqa: BLE001
        logger.error(f"手動実行エラー: {e}")


if __name__ == "__main__":
    run_scheduler()
