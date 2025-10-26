#!/usr/bin/env python3
"""
News Notify App - FastAPI Web API
Webhook と Website の管理API
"""

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app import db, Webhook, Website, ArticleDatabase

# FastAPIアプリケーション
app = FastAPI(
    title="News Notify App API",
    description="ニュース通知アプリケーションの管理API",
    version="0.1.0",
    root_path="/api/v1"
)

# レスポンス用モデル
class WebhookResponse(BaseModel):
    id: int
    name: str
    endpoint: str
    service_type: str
    is_active: bool
    created_at: str

class WebsiteResponse(BaseModel):
    id: int
    name: str
    type: str
    url: str
    avatar: str | None
    selector: str | None
    is_active: bool
    needs_translation: bool
    target_webhook_ids: str | None
    created_at: str

class WebhookCreate(BaseModel):
    name: str
    endpoint: str
    service_type: str
    is_active: bool = True

class WebhookUpdate(BaseModel):
    name: str | None = None
    endpoint: str | None = None
    service_type: str | None = None
    is_active: bool | None = None

class WebsiteCreate(BaseModel):
    name: str
    type: str
    url: str
    avatar: str | None = None
    selector: str | None = None
    is_active: bool = True
    needs_translation: bool = False
    target_webhook_ids: str | None = None

class WebsiteUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    url: str | None = None
    avatar: str | None = None
    selector: str | None = None
    is_active: bool | None = None
    needs_translation: bool | None = None

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

# Webhook API
@app.get("/webhooks", response_model=list[WebhookResponse])
async def get_webhooks():
    """全てのWebhookを取得"""
    try:
        webhooks = db.get_active_webhooks()
        return [
            WebhookResponse(
                id=webhook.id,
                name=webhook.name,
                endpoint=webhook.endpoint,
                service_type=webhook.service_type,
                is_active=webhook.is_active,
                created_at=webhook.created_at or ""
            )
            for webhook in webhooks
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook取得エラー: {str(e)}"
        )

@app.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: int):
    """指定されたWebhookを取得"""
    try:
        webhooks = db.get_active_webhooks()
        webhook = next((w for w in webhooks if w.id == webhook_id), None)

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhookが見つかりません"
            )

        return WebhookResponse(
            id=webhook.id,
            name=webhook.name,
            endpoint=webhook.endpoint,
            service_type=webhook.service_type,
            is_active=webhook.is_active,
            created_at=webhook.created_at or ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook取得エラー: {str(e)}"
        )

@app.post("/webhooks", response_model=StatusResponse)
async def create_webhook(webhook_data: WebhookCreate):
    """新しいWebhookを作成"""
    try:
        webhook = Webhook(
            name=webhook_data.name,
            endpoint=webhook_data.endpoint,
            service_type=webhook_data.service_type,
            is_active=webhook_data.is_active
        )

        if db.add_webhook(webhook):
            return StatusResponse(message="Webhook作成成功", success=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook作成に失敗しました（名前が重複している可能性があります）"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook作成エラー: {str(e)}"
        )

@app.put("/webhooks/{webhook_id}", response_model=StatusResponse)
async def update_webhook(webhook_id: int, webhook_data: WebhookUpdate):
    """Webhookを更新"""
    try:
        # 現在のWebhookを取得
        webhooks = db.get_active_webhooks()
        current_webhook = next((w for w in webhooks if w.id == webhook_id), None)

        if not current_webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhookが見つかりません"
            )

        # is_activeの更新のみサポート（他のフィールドは削除して再作成が必要）
        if webhook_data.is_active is not None:
            if db.update_webhook_status(webhook_id, webhook_data.is_active):
                return StatusResponse(message="Webhook更新成功", success=True)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Webhook更新に失敗しました"
                )
        else:
            return StatusResponse(message="更新項目がありません", success=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook更新エラー: {str(e)}"
        )

@app.delete("/webhooks/{webhook_id}", response_model=StatusResponse)
async def delete_webhook(webhook_id: int):
    """Webhookを削除"""
    try:
        if db.delete_webhook(webhook_id):
            return StatusResponse(message="Webhook削除成功", success=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhookが見つかりません"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook削除エラー: {str(e)}"
        )

# Website API
@app.get("/websites", response_model=list[WebsiteResponse])
async def get_websites():
    """全てのWebsiteを取得"""
    try:
        websites = db.get_active_websites()
        return [
            WebsiteResponse(
                id=website.id,
                name=website.name,
                type=website.type,
                url=website.url,
                avatar=website.avatar,
                selector=website.selector,
                is_active=website.is_active,
                needs_translation=website.needs_translation,
                target_webhook_ids=website.target_webhook_ids,
                created_at=website.created_at or ""
            )
            for website in websites
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website取得エラー: {str(e)}"
        )

@app.get("/websites/{website_id}", response_model=WebsiteResponse)
async def get_website(website_id: int):
    """指定されたWebsiteを取得"""
    try:
        websites = db.get_active_websites()
        website = next((w for w in websites if w.id == website_id), None)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Websiteが見つかりません"
            )

        return WebsiteResponse(
            id=website.id,
            name=website.name,
            type=website.type,
            url=website.url,
            avatar=website.avatar,
            selector=website.selector,
            is_active=website.is_active,
            needs_translation=website.needs_translation,
            target_webhook_ids=website.target_webhook_ids,
            created_at=website.created_at or ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website取得エラー: {str(e)}"
        )

@app.post("/websites", response_model=StatusResponse)
async def create_website(website_data: WebsiteCreate):
    """新しいWebsiteを作成"""
    try:
        website = Website(
            name=website_data.name,
            type=website_data.type,
            url=website_data.url,
            avatar=website_data.avatar,
            selector=website_data.selector,
            is_active=website_data.is_active,
            needs_translation=website_data.needs_translation,
            target_webhook_ids=website_data.target_webhook_ids
        )

        if db.add_website(website):
            return StatusResponse(message="Website作成成功", success=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website作成に失敗しました（名前が重複している可能性があります）"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website作成エラー: {str(e)}"
        )

@app.put("/websites/{website_id}", response_model=StatusResponse)
async def update_website(website_id: int, website_data: WebsiteUpdate):
    """Websiteを更新"""
    try:
        # 現在のWebsiteを取得
        websites = db.get_active_websites()
        current_website = next((w for w in websites if w.id == website_id), None)

        if not current_website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Websiteが見つかりません"
            )

        # is_activeの更新のみサポート（他のフィールドは削除して再作成が必要）
        if website_data.is_active is not None:
            if db.update_website_status(website_id, website_data.is_active):
                return StatusResponse(message="Website更新成功", success=True)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Website更新に失敗しました"
                )
        else:
            return StatusResponse(message="更新項目がありません", success=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website更新エラー: {str(e)}"
        )

@app.delete("/websites/{website_id}", response_model=StatusResponse)
async def delete_website(website_id: int):
    """Websiteを削除"""
    try:
        if db.delete_website(website_id):
            return StatusResponse(message="Website削除成功", success=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Websiteが見つかりません"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website削除エラー: {str(e)}"
        )

# 統計情報API
@app.get("/stats")
async def get_stats():
    """統計情報を取得"""
    try:
        total_articles = db.get_article_count()
        webhook_count = len(db.get_active_webhooks())
        website_count = len(db.get_active_websites())

        return {
            "total_articles": total_articles,
            "active_webhooks": webhook_count,
            "active_websites": website_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計情報取得エラー: {str(e)}"
        )

def run_api():
    """APIサーバーを起動"""
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    run_api()
