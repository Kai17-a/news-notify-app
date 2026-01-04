import argparse
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException, status
from sqlmodel import Session, create_engine

from core.models.model import Article, Webhook, Website
from core.services.article import ArticleService
from core.services.fetcher import FetcherService
from core.services.notification import NotificationService
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

# FastAPIアプリケーション
app = FastAPI(
    title="News Notify App API",
    description="ニュース通知アプリケーションの管理API",
    version="0.1.0",
    root_path="/api/v1",
)


class StatusResponse(BaseModel):
    message: str
    success: bool


# ヘルスチェック
@app.get("/")
async def root():
    return {"message": "News Notify App API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}


# 統計情報API
@app.get("/stats")
async def get_stats():
    """統計情報を取得"""
    try:
        with Session(engine) as session:
            article_service = ArticleService(session)
            webhook_service = WebhookService(session)
            website_service = WebsiteService(session)

            total_articles = article_service.get_article_count()
            webhook_count = len(webhook_service.get_webhook())
            website_count = len(website_service.get_website_with_active())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計情報取得エラー: {e!s}",
        )
    else:
        return {
            "total_articles": total_articles,
            "active_webhooks": webhook_count,
            "active_websites": website_count,
        }


# Article API
@app.delete("/articles", response_model=StatusResponse)
async def cleanup_articles():
    """登録記事削除"""
    try:
        with Session(engine) as session:
            service = ArticleService(session)
            deleted_article = service.delete_old_article()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Article削除エラー: {e!s}",
        )
    else:
        if deleted_article > 0:
            return StatusResponse(message="Article削除成功", success=True)
        else:
            return StatusResponse(
                message="削除対象の記事がありませんでした", success=True
            )


# Webhook API
@app.get("/webhooks", response_model=list[Webhook])
async def get_webhooks():
    """全てのWebhookを取得."""
    try:
        with Session(engine) as session:
            service = WebhookService(session)
            webhooks = service.get_webhook()

            results = [
                Webhook(
                    id=webhook.id,
                    name=webhook.name,
                    endpoint=webhook.endpoint,
                    service_type=webhook.service_type,
                    is_active=webhook.is_active,
                    created_at=webhook.created_at or "",
                )
                for webhook in webhooks
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook取得エラー: {e!s}",
        )
    else:
        return results


@app.get("/webhooks/{webhook_id}", response_model=Webhook)
async def get_webhook(webhook_id: int):
    """指定されたWebhookを取得"""
    try:
        with Session(engine) as session:
            service = WebhookService(session)
            result = service.get_webhook_by_id(webhook_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook取得エラー: {e!s}",
        )
    else:
        return result


# @app.post("/webhooks", response_model=StatusResponse)
# async def create_webhook(webhook_data: Webhook):
#     """新しいWebhookを作成"""
#     try:
#         webhook = Webhook(
#             name=webhook_data.name,
#             endpoint=webhook_data.endpoint,
#             service_type=webhook_data.service_type,
#             is_active=webhook_data.is_active,
#         )

#         if db.add_webhook(webhook):
#             return StatusResponse(message="Webhook作成成功", success=True)
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Webhook作成に失敗しました（名前が重複している可能性があります）",
#             )
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Webhook作成エラー: {e!s}",
#         )


# @app.put("/webhooks/{webhook_id}", response_model=StatusResponse)
# async def update_webhook(webhook_id: int, webhook_data: Webhook):
#     """Webhookを更新"""
#     try:
#         # 現在のWebhookを取得
#         webhooks = db.get_active_webhooks()
#         current_webhook = next((w for w in webhooks if w.id == webhook_id), None)

#         if not current_webhook:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhookが見つかりません")

#         # is_activeの更新のみサポート（他のフィールドは削除して再作成が必要）
#         if webhook_data.is_active is not None:
#             if db.update_webhook_status(webhook_id, webhook_data.is_active):
#                 return StatusResponse(message="Webhook更新成功", success=True)
#             else:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Webhook更新に失敗しました",
#                 )
#         else:
#             return StatusResponse(message="更新項目がありません", success=True)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Webhook更新エラー: {e!s}",
#         )


@app.delete("/webhooks/{webhook_id}", response_model=StatusResponse)
async def delete_webhook(webhook_id: int):
    """Webhookを削除"""
    try:
        with Session(engine) as session:
            service = WebhookService(session)
            service.delete_webhook_by_id(webhook_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook削除エラー: {e!s}",
        )
    else:
        return StatusResponse(message="Webhook削除成功", success=True)


# Website API
@app.get("/websites", response_model=list[Website])
async def get_websites():
    """全てのWebsiteを取得"""
    try:
        with Session(engine) as session:
            service = WebsiteService(session)
            websites = service.get_website_with_active()
            results = [
                Website(
                    id=website.id,
                    name=website.name,
                    type=website.type,
                    url=website.url,
                    avatar=website.avatar,
                    selector=website.selector,
                    is_active=website.is_active,
                    needs_translation=website.needs_translation,
                    target_webhook_ids=website.target_webhook_ids,
                    created_at=website.created_at or "",
                )
                for website in websites
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website取得エラー: {e!s}",
        )
    else:
        return results


@app.get("/websites/{website_id}", response_model=Website)
async def get_website(website_id: int):
    """指定されたWebsiteを取得"""
    try:
        with Session(engine) as session:
            service = WebsiteService(session)
            website = service.get_website_by_id(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Websiteが見つかりません"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website取得エラー: {e!s}",
        )
    else:
        return website


# @app.post("/websites", response_model=StatusResponse)
# async def create_website(website: Website):
#     """新しいWebsiteを作成"""
#     try:
#         with Session(engine) as session:
#             service = WebsiteService(session)
#             service.save(website)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Website作成エラー: {e!s}",
#         )
#     else:
#         return StatusResponse(message="Website作成成功", success=True)


# @app.put("/websites/{website_id}", response_model=StatusResponse)
# async def update_website(website_id: int, website_data: Website):
#     """Websiteを更新"""
#     try:
#         # 現在のWebsiteを取得
#         websites = db.get_active_websites()
#         current_website = next((w for w in websites if w.id == website_id), None)

#         if not current_website:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Websiteが見つかりません")

#         # is_activeの更新のみサポート（他のフィールドは削除して再作成が必要）
#         if website_data.is_active is not None:
#             if db.update_website_status(website_id, website_data.is_active):
#                 return StatusResponse(message="Website更新成功", success=True)
#             else:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Website更新に失敗しました",
#                 )
#         else:
#             return StatusResponse(message="更新項目がありません", success=True)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Website更新エラー: {e!s}",
#         )


@app.delete("/websites/{website_id}", response_model=StatusResponse)
async def delete_website(website_id: int):
    """Websiteを削除"""
    try:
        with Session(engine) as session:
            service = WebsiteService(session)
            service.delete_website(website_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website削除エラー: {e!s}",
        )
    else:
        return StatusResponse(message="Website削除成功", success=True)


def run_api():
    """APIサーバーを起動"""
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    run_api()
