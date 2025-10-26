# News Notify App

ニュースサイトから記事を取得し、複数の通知サービスに投稿するアプリケーション。

## 機能

- RSSフィードとWebスクレイピングによる記事取得
- 重複記事の自動検出・除外
- 複数通知サービス対応（Discord、Slack、Microsoft Teams）
- SQLiteによるデータ管理
- 並行処理による高速化

## 必要な環境

- Python 3.13+
- 必要なライブラリ（requirements.txtを参照）

## インストール

### uvを使用する場合（推奨）
```bash
uv sync
```

### pipを使用する場合
```bash
pip install -r requirements.txt
```

## データベース初期化

アプリケーション初回実行時に`news_notify_app.db`が自動作成される。

## 設定

### Web API経由での設定（推奨）

#### Webhookの管理
```bash
# 一覧取得
curl http://localhost:8000/webhooks

# 作成
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Discord Main",
    "endpoint": "https://discord.com/api/webhooks/...",
    "service_type": "discord"
  }'

# 更新（アクティブ状態の変更）
curl -X PUT http://localhost:8000/webhooks/1 \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# 削除
curl -X DELETE http://localhost:8000/webhooks/1
```

#### Websiteの管理
```bash
# 一覧取得
curl http://localhost:8000/websites

# RSSサイトの作成
curl -X POST http://localhost:8000/websites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "サイト名",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "avatar": "https://example.com/icon.png",
    "needs_translation": false
  }'

# スクレイピングサイトの作成
curl -X POST http://localhost:8000/websites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "サイト名",
    "type": "scraping",
    "url": "https://example.com/news/",
    "avatar": "https://example.com/icon.png",
    "selector": "article h2 a",
    "needs_translation": false
  }'

# 更新（アクティブ状態の変更）
curl -X PUT http://localhost:8000/websites/1 \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# 削除
curl -X DELETE http://localhost:8000/websites/1
```

### Python経由での設定

```python
from app import db, Webhook, Website

# Webhook追加
webhook = Webhook(
    name="Discord Main",
    endpoint="https://discord.com/api/webhooks/...",
    service_type="discord"
)
db.add_webhook(webhook)

# Website追加
website = Website(
    name="サイト名",
    type="rss",
    url="https://example.com/feed.xml",
    needs_translation=False
)
db.add_website(website)
```

## 実行

### CLIアプリケーション（記事収集）

#### スケジューラー実行（定期実行）
```bash
# uvを使用する場合（推奨）
uv run app

# Pythonを直接使用する場合
python app.py
```

毎日9:00（日本時間）に記事を取得し、新着記事を通知サービスに投稿する。

#### 手動実行（1回のみ）
```bash
# uvを使用する場合（推奨）
uv run app-once

# Pythonを直接使用する場合
python -c "from app import run_once; run_once()"
```

即座にニュース収集を1回だけ実行する。テストや手動更新に便利。

### Web API（管理機能）
```bash
# uvを使用する場合（推奨）
uv run api

# Pythonを直接使用する場合
python api.py
```

http://localhost:8000 でWeb APIが起動し、Webhook・Websiteの管理が可能。

## データベース構造

### articles テーブル
- 取得した記事の保存
- 重複チェック用ハッシュ値

### webhooks テーブル
- 通知先の管理
- サービスタイプ別設定

### websites テーブル
- 記事取得元サイトの管理
- 翻訳要否フラグ

## 通知サービス

### Discord
- Webhook URL形式
- 埋め込み形式で投稿

### Slack
- Block Kit形式
- リンク付きリスト表示

### Microsoft Teams
- MessageCard形式
- アクティビティカード表示

## 設定管理

### Webhookの状態変更
```python
db.update_webhook_status(webhook_id, False)  # 無効化
```

### Websiteの状態変更
```python
db.update_website_status(website_id, False)  # 無効化
```

### データ削除
```python
db.delete_webhook(webhook_id)
db.delete_website(website_id)
```

## ログ

標準出力にINFOレベルでログを出力。処理状況と統計情報を確認可能。

## 実行例

```bash
# スケジューラー実行
$ uv run app
2025-10-25 11:35:10,743 - INFO - データベース初期化完了
2025-10-25 11:35:10,743 - INFO - スケジューラー開始
# 毎日9:00に以下のログが出力される
2025-10-26 09:00:00,000 - INFO - ニュース収集処理開始

# 手動実行
$ uv run app-once
2025-10-25 19:54:24,584 - INFO - ニュース収集を手動実行します
2025-10-25 19:54:24,584 - INFO - ニュース収集処理開始
2025-10-25 19:54:25,459 - INFO - ニュース収集の手動実行が完了しました
```

## トラブルシューティング

### Webhookが設定されていない場合
```
ERROR - 投稿先のWebhookが設定されていません
```
→ Webhookを追加してください

### Websiteが設定されていない場合
```
WARNING - データベースにアクティブなWebsiteが見つかりません
```
→ Websiteを追加してください

### 記事取得エラー
```
ERROR - HTTP リクエストエラー [サイト名]: ...
```
→ URLやセレクタを確認してください

## ファイル構成

```
news-notify-app/
├── app.py               # CLIアプリケーション（記事収集）
├── api.py               # Web API（管理機能）
├── pyproject.toml       # プロジェクト設定
├── news_notify_app.db   # SQLiteデータベース（自動生成）
├── requirements.txt     # 依存ライブラリ（pip用）
└── README.md           # このファイル
```

## API エンドポイント

### Webhook管理
- `GET /webhooks` - Webhook一覧取得
- `GET /webhooks/{id}` - 指定Webhook取得
- `POST /webhooks` - Webhook作成
- `PUT /webhooks/{id}` - Webhook更新
- `DELETE /webhooks/{id}` - Webhook削除

### Website管理
- `GET /websites` - Website一覧取得
- `GET /websites/{id}` - 指定Website取得
- `POST /websites` - Website作成
- `PUT /websites/{id}` - Website更新
- `DELETE /websites/{id}` - Website削除

### その他
- `GET /` - API状態確認
- `GET /health` - ヘルスチェック
- `GET /stats` - 統計情報取得

### API ドキュメント
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 翻訳機能

`needs_translation=True`に設定されたWebsiteの記事タイトルは自動的に日本語に翻訳される。

```python
# 翻訳が必要なWebsiteの追加例
website = Website(
    name="TechCrunch",
    type="rss",
    url="https://techcrunch.com/feed/",
    needs_translation=True  # 翻訳を有効化
)
```

- MyMemory Translation APIを使用（無料）
- 既に日本語が含まれている場合は翻訳をスキップ
- オリジナルタイトルは保持され、重複チェックに使用
