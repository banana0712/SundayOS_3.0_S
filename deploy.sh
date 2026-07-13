#!/bin/bash
# Sunday OS — 云服务器一键部署脚本
# 适用于 Ubuntu 22.04 / Debian 12，在全新系统上运行：
#
#   chmod +x deploy.sh && sudo ./deploy.sh
#
# 会根据提示输入 API Key 和 DeepSeek Key，其余自动完成。
# 部署后 Sunday 运行在 http://你的服务器IP:8005（支持外网访问）。
# 服务通过 systemd 托管，重启自动恢复。

set -e

echo "============================================"
echo "  Sunday OS 云服务器部署"
echo "  目标：Ubuntu 22.04 / Debian 12"
echo "============================================"
echo ""

# ── 0. 检查是否为 root ──────────────────────
if [ "$EUID" -ne 0 ]; then
    echo "请用 sudo 运行：sudo ./deploy.sh"
    exit 1
fi

# ── 1. 输入配置 ─────────────────────────────
read -p "Sunday API Key（访问密码，如 sunday0712）: " SUNDAY_KEY
if [ -z "$SUNDAY_KEY" ]; then
    SUNDAY_KEY="sunday0712"
    echo "使用默认值: $SUNDAY_KEY"
fi

read -p "DeepSeek API Key（可选，不填则 mock 模式）: " DS_KEY
read -p "DeepSeek Base URL（默认 https://api.deepseek.com/v1）: " DS_URL
if [ -z "$DS_URL" ]; then
    DS_URL="https://api.deepseek.com/v1"
fi

APP_DIR="/opt/sundayos"
APP_USER="sunday"
echo ""
echo "配置确认："
echo "  安装目录 : $APP_DIR"
echo "  API Key  : $SUNDAY_KEY"
echo "  DeepSeek  : ${DS_KEY:-(mock 模式)}"
echo ""

# ── 2. 安装系统依赖 ─────────────────────────
echo ">>> 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl sqlite3 2>&1 | tail -3

# ── 3. 创建专用用户 ─────────────────────────
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd -r -m -d /home/$APP_USER -s /bin/bash $APP_USER
    echo "用户 $APP_USER 已创建"
fi

# ── 4. 克隆/更新代码 ────────────────────────
if [ -d "$APP_DIR" ]; then
    echo ">>> 更新已有代码..."
    cd "$APP_DIR"
    git pull origin main 2>/dev/null || echo "git pull 失败，使用当前代码"
else
    echo ">>> 克隆代码..."
    git clone https://github.com/banana0712/SundayOS_3.0_S.git "$APP_DIR"
    cd "$APP_DIR/backend"
fi

# ── 5. Python 虚拟环境 ──────────────────────
echo ">>> 配置 Python 环境..."
VENV="$APP_DIR/.venv"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$APP_DIR/backend/requirements.txt"

# ── 6. 创建 .env ────────────────────────────
ENV_FILE="$APP_DIR/backend/.env"
cat > "$ENV_FILE" <<EOF
# Sunday OS 服务器环境变量
SUNDAY_API_KEY=$SUNDAY_KEY
DEEPSEEK_API_KEY=$DS_KEY
DEEPSEEK_BASE_URL=$DS_URL
SUNDAY_DB_PATH=$APP_DIR/backend/sunday.db
SUNDAY_ALLOW_MOCK=true
EOF
chmod 600 "$ENV_FILE"
echo ".env 已创建 ($ENV_FILE)"

# ── 7. 设置权限 ─────────────────────────────
chown -R $APP_USER:$APP_USER "$APP_DIR"

# ── 8. 创建 systemd 服务 ────────────────────
SERVICE_FILE="/etc/systemd/system/sunday.service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Sunday OS Backend
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$VENV/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port 8005
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sunday.service
systemctl restart sunday.service

# ── 9. 开放防火墙（如果启用了 ufw）─────────
if command -v ufw &> /dev/null; then
    ufw allow 8005/tcp 2>/dev/null || true
    ufw allow 80/tcp 2>/dev/null || true
fi

# ── 10. 等待启动 ────────────────────────────
echo ""
echo ">>> 等待 Sunday 启动..."
sleep 4

# ── 11. 检查状态 ────────────────────────────
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8005/health | grep -q 200; then
    echo ""
    echo "============================================"
    echo "  ✅ Sunday OS 部署成功！"
    echo "============================================"
    echo ""
    echo "  外网地址：http://$(curl -s ifconfig.me 2>/dev/null || echo '你的服务器IP'):8005"
    echo "  API Key ：$SUNDAY_KEY"
    echo ""
    echo "  常用命令："
    echo "    sudo systemctl status sunday   # 查看状态"
    echo "    sudo systemctl restart sunday  # 重启"
    echo "    sudo journalctl -u sunday -f   # 查看日志"
    echo ""
else
    echo ""
    echo "⚠️  服务可能未正常启动，检查日志："
    echo "  sudo journalctl -u sunday -n 50"
fi
