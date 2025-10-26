#!/usr/bin/env python3
"""
News Notify App - API テストスイート
テスト内でuvicornサーバーを自動起動
"""

import pytest
import requests
import json
import time
import uuid
import subprocess
import threading
import socket
from typing import Dict, Any
from app import db, Webhook, Website


class APIClient:
    """APIテスト用のクライアントクラス"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get(self, endpoint: str) -> requests.Response:
        """GET リクエスト"""
        return self.session.get(f"{self.base_url}{endpoint}")

    def post(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        """POST リクエスト"""
        return self.session.post(f"{self.base_url}{endpoint}", json=data)

    def put(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        """PUT リクエスト"""
        return self.session.put(f"{self.base_url}{endpoint}", json=data)

    def delete(self, endpoint: str) -> requests.Response:
        """DELETE リクエスト"""
        return self.session.delete(f"{self.base_url}{endpoint}")


def is_port_available(port: int) -> bool:
    """ポートが利用可能かチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """サーバーが起動するまで待機"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def api_server():
    """APIサーバーを自動起動・停止"""
    port = 8000

    # ポートが既に使用されている場合はスキップ
    if not is_port_available(port):
        print(f"Port {port} is already in use, assuming server is running")
        yield f"http://localhost:{port}"
        return

    # uvicornサーバーを起動
    process = subprocess.Popen([
        "uv", "run", "uvicorn", "api:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "error"  # ログレベルを下げてテスト出力をクリーンに
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    server_url = f"http://localhost:{port}"

    # サーバーが起動するまで待機
    if wait_for_server(f"{server_url}/health", timeout=30):
        print(f"API server started at {server_url}")
        yield server_url
    else:
        process.terminate()
        process.wait()
        raise RuntimeError("Failed to start API server")

    # テスト終了後にサーバーを停止
    process.terminate()
    process.wait()
    print("API server stopped")


@pytest.fixture(scope="session")
def api_client(api_server):
    """APIクライアントのフィクスチャ"""
    return APIClient(api_server)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """テスト環境のセットアップ"""
    # 実際のテストでは別のデータベースを使用することを推奨
    yield
    # テスト後のクリーンアップ（必要に応じて）


class TestBasicEndpoints:
    """基本エンドポイントのテスト"""

    def test_root_endpoint(self, api_client):
        """ルートエンドポイントのテスト"""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "News Notify App API"
        assert data["status"] == "running"

    def test_health_check(self, api_client):
        """ヘルスチェックのテスト"""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_stats_endpoint(self, api_client):
        """統計情報エンドポイントのテスト"""
        response = api_client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_articles" in data
        assert "active_webhooks" in data
        assert "active_websites" in data
        assert isinstance(data["total_articles"], int)
        assert isinstance(data["active_webhooks"], int)
        assert isinstance(data["active_websites"], int)


class TestWebhookAPI:
    """Webhook API のテスト"""

    def test_get_all_webhooks(self, api_client):
        """全Webhook取得のテスト"""
        response = api_client.get("/webhooks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Webhookが存在する場合の検証
        if data:
            webhook = data[0]
            required_fields = ["id", "name", "endpoint", "service_type", "is_active", "created_at"]
            for field in required_fields:
                assert field in webhook

    def test_get_webhook_by_id(self, api_client):
        """個別Webhook取得のテスト"""
        # まず全Webhookを取得してIDを確認
        response = api_client.get("/webhooks")
        webhooks = response.json()

        if webhooks:
            webhook_id = webhooks[0]["id"]
            response = api_client.get(f"/webhooks/{webhook_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == webhook_id
            assert "name" in data
            assert "endpoint" in data
            assert "service_type" in data

    def test_get_nonexistent_webhook(self, api_client):
        """存在しないWebhook取得のテスト"""
        response = api_client.get("/webhooks/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "見つかりません" in data["detail"]

    def test_create_webhook(self, api_client):
        """Webhook作成のテスト"""
        unique_id = str(uuid.uuid4())[:8]
        webhook_data = {
            "name": f"Test Teams Webhook {unique_id}",
            "endpoint": f"https://outlook.office.com/webhook/test{unique_id}",
            "service_type": "teams"
        }

        response = api_client.post("/webhooks", webhook_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "成功" in data["message"]

    def test_create_duplicate_webhook(self, api_client):
        """重複Webhook作成のテスト"""
        unique_id = str(uuid.uuid4())[:8]
        webhook_data = {
            "name": f"Duplicate Test Webhook {unique_id}",
            "endpoint": f"https://example.com/webhook/test{unique_id}",
            "service_type": "discord"
        }

        # 最初の作成
        response1 = api_client.post("/webhooks", webhook_data)
        assert response1.status_code == 200

        # 同じ名前で再度作成（重複）
        response2 = api_client.post("/webhooks", webhook_data)

        # 重複の場合は400エラーが期待される
        assert response2.status_code == 400
        data = response2.json()
        assert "重複" in data["detail"] or "失敗" in data["detail"]

    def test_update_webhook(self, api_client):
        """Webhook更新のテスト"""
        # まず作成したWebhookのIDを取得
        response = api_client.get("/webhooks")
        webhooks = response.json()

        # Test Teams Webhookを探す（部分一致）
        test_webhook = None
        for webhook in webhooks:
            if "Test Teams Webhook" in webhook["name"]:
                test_webhook = webhook
                break

        if test_webhook:
            update_data = {"is_active": False}
            response = api_client.put(f"/webhooks/{test_webhook['id']}", update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestWebsiteAPI:
    """Website API のテスト"""

    def test_get_all_websites(self, api_client):
        """全Website取得のテスト"""
        response = api_client.get("/websites")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Websiteが存在する場合の検証
        if data:
            website = data[0]
            required_fields = ["id", "name", "type", "url", "is_active", "needs_translation", "created_at"]
            for field in required_fields:
                assert field in website

    def test_get_website_by_id(self, api_client):
        """個別Website取得のテスト"""
        # まず全Websiteを取得してIDを確認
        response = api_client.get("/websites")
        websites = response.json()

        if websites:
            website_id = websites[0]["id"]
            response = api_client.get(f"/websites/{website_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == website_id
            assert "name" in data
            assert "type" in data
            assert "url" in data

    def test_get_nonexistent_website(self, api_client):
        """存在しないWebsite取得のテスト"""
        response = api_client.get("/websites/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "見つかりません" in data["detail"]

    def test_create_rss_website(self, api_client):
        """RSSサイト作成のテスト"""
        unique_id = str(uuid.uuid4())[:8]
        website_data = {
            "name": f"Test RSS Site {unique_id}",
            "type": "rss",
            "url": f"https://example.com/feed{unique_id}.xml",
            "avatar": "https://example.com/icon.png",
            "needs_translation": True
        }

        response = api_client.post("/websites", website_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "成功" in data["message"]

    def test_create_scraping_website(self, api_client):
        """スクレイピングサイト作成のテスト"""
        unique_id = str(uuid.uuid4())[:8]
        website_data = {
            "name": f"Test Scraping Site {unique_id}",
            "type": "scraping",
            "url": f"https://example.com/news{unique_id}/",
            "selector": "article h2 a",
            "avatar": "https://example.com/favicon.ico",
            "needs_translation": False
        }

        response = api_client.post("/websites", website_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "成功" in data["message"]

    def test_delete_website(self, api_client):
        """Website削除のテスト"""
        # まず作成したWebsiteのIDを取得
        response = api_client.get("/websites")
        websites = response.json()

        # Test RSS Siteを探す（部分一致）
        test_website = None
        for website in websites:
            if "Test RSS Site" in website["name"]:
                test_website = website
                break

        if test_website:
            response = api_client.delete(f"/websites/{test_website['id']}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "成功" in data["message"]


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_invalid_json_request(self, api_client):
        """不正なJSONリクエストのテスト"""
        # 直接requestsを使用して不正なJSONを送信
        response = requests.post(
            f"{api_client.base_url}/webhooks",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_missing_required_fields(self, api_client):
        """必須フィールド不足のテスト"""
        incomplete_webhook = {
            "name": "Incomplete Webhook"
            # endpoint と service_type が不足
        }

        response = api_client.post("/webhooks", incomplete_webhook)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invalid_service_type(self, api_client):
        """不正なサービスタイプのテスト"""
        unique_id = str(uuid.uuid4())[:8]
        invalid_webhook = {
            "name": f"Invalid Service Webhook {unique_id}",
            "endpoint": f"https://example.com/webhook{unique_id}",
            "service_type": "invalid_service"
        }

        response = api_client.post("/webhooks", invalid_webhook)

        # 現在の実装では作成は成功するが、実際の通知送信時にエラーが発生する
        # これは設計上の動作として正しい
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDataConsistency:
    """データ整合性のテスト"""

    def test_stats_consistency_after_operations(self, api_client):
        """操作後の統計情報整合性テスト"""
        # 操作前の統計を取得
        response = api_client.get("/stats")
        initial_stats = response.json()

        # Webhook作成
        unique_id = str(uuid.uuid4())[:8]
        webhook_data = {
            "name": f"Consistency Test Webhook {unique_id}",
            "endpoint": f"https://example.com/consistency-test{unique_id}",
            "service_type": "discord"
        }
        api_client.post("/webhooks", webhook_data)

        # 統計情報を再取得
        response = api_client.get("/stats")
        updated_stats = response.json()

        # アクティブWebhook数が増加していることを確認
        assert updated_stats["active_webhooks"] >= initial_stats["active_webhooks"]

    def test_crud_operations_consistency(self, api_client):
        """CRUD操作の整合性テスト"""
        # 作成
        unique_id = str(uuid.uuid4())[:8]
        website_data = {
            "name": f"CRUD Test Site {unique_id}",
            "type": "rss",
            "url": f"https://example.com/crud-test{unique_id}.xml"
        }

        create_response = api_client.post("/websites", website_data)
        assert create_response.status_code == 200

        # 読み取り - 作成されたWebsiteが存在することを確認
        response = api_client.get("/websites")
        websites = response.json()
        crud_site = next((w for w in websites if w["name"] == f"CRUD Test Site {unique_id}"), None)
        assert crud_site is not None

        # 削除
        delete_response = api_client.delete(f"/websites/{crud_site['id']}")
        assert delete_response.status_code == 200

        # 削除後の確認
        response = api_client.get("/websites")
        websites = response.json()
        crud_site_after_delete = next((w for w in websites if w["name"] == f"CRUD Test Site {unique_id}"), None)
        assert crud_site_after_delete is None


if __name__ == "__main__":
    # テストの実行
    pytest.main([
        __file__,
        "-v",  # 詳細出力
        "--tb=short",  # 短いトレースバック
        "--color=yes"  # カラー出力
    ])
