#!/bin/bash

# News Notify App デプロイスクリプト

set -e

# 色付きログ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 引数チェック
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <server_ip>"
    echo "Example: $0 203.0.113.1"
    exit 1
fi

SERVER_IP=$1
SSH_USER="ubuntu"
APP_DIR="/opt/news-notify-app"

log_info "Starting deployment to $SERVER_IP"

# SSH接続テスト
log_info "Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $SSH_USER@$SERVER_IP exit 2>/dev/null; then
    log_error "SSH connection failed. Please check:"
    log_error "1. Server IP is correct"
    log_error "2. SSH key is properly configured"
    log_error "3. Your IP is in allowed_ssh_cidrs"
    exit 1
fi

log_info "SSH connection successful"

# アプリケーションファイルの転送
log_info "Uploading application files..."
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='*.db' \
    ./ $SSH_USER@$SERVER_IP:$APP_DIR/

# リモートでのセットアップ実行
log_info "Setting up application on remote server..."
ssh $SSH_USER@$SERVER_IP << 'EOF'
set -e

cd /opt/news-notify-app

# 権限設定
sudo chown -R ubuntu:ubuntu /opt/news-notify-app

# 依存関係のインストール
if [ ! -f ~/.cargo/bin/uv ]; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

export PATH="$HOME/.cargo/bin:$PATH"

# プロジェクトの同期
uv sync

# データベースの初期化（存在しない場合のみ）
if [ ! -f news_notify_app.db ]; then
    echo "Initializing database..."
    python3 -c "from app import db; print('Database initialized')"
fi

# Supervisorサービスの再起動
echo "Restarting services..."
sudo supervisorctl restart news-notify-cli || echo "CLI service not running, will start automatically"
sudo supervisorctl restart news-notify-api || echo "API service not running, will start automatically"

# サービス状態確認
sleep 5
sudo supervisorctl status

# Nginxの設定テストと再起動
sudo nginx -t
sudo systemctl reload nginx

echo "Deployment completed successfully!"
EOF

log_info "Checking service status..."
ssh $SSH_USER@$SERVER_IP "curl -s http://localhost:8000/health || echo 'API not ready yet'"

log_info "Deployment completed!"
log_info "API URL: http://$SERVER_IP:8000"
log_info "Health check: http://$SERVER_IP/health"
log_info "API docs: http://$SERVER_IP:8000/docs"

log_warn "Note: It may take a few minutes for all services to start up completely."
