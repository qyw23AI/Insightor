#!/bin/bash
# =============================================================================
# Insightor Nginx + Let's Encrypt HTTPS Setup
# 前置: 1) 域名已解析到服务器 IP  2) setup.sh 已完成部署
# 用法: sudo bash deploy/setup_https.sh insightor.your-domain.com
# =============================================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: sudo bash setup_https.sh <你的域名>"
    echo "示例: sudo bash setup_https.sh insightor.example.com"
    exit 1
fi

DOMAIN="$1"
APP_PORT=8000

echo "=== Insightor HTTPS Setup ==="
echo "域名: $DOMAIN"

# ---------- 1. 安装 Nginx + Certbot ----------
echo "[1/4] 安装 Nginx + Certbot..."
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

# ---------- 2. 写入 Nginx 配置 ----------
echo "[2/4] 配置 Nginx..."
cat > "/etc/nginx/sites-available/insightor" << NGINX
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE 长连接支持
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/insightor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ---------- 3. Let's Encrypt 证书 ----------
echo "[3/4] 申请 Let's Encrypt 证书..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect

# ---------- 4. 验证自动续期 ----------
echo "[4/4] 设置自动续期..."
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
echo "=== 完成 ==="
echo "https://${DOMAIN}/  (HTTP → HTTPS 自动跳转)"
NGINX
