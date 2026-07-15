#!/bin/bash
# Sunday OS - 从服务器推送到 GitHub 并部署
# 用法: ./deploy_from_server.sh

set -e

SERVER="45.207.220.124"
USER="root"
REPO_PATH="/opt/sundayos"

echo "========================================="
echo "  Sunday OS 服务器部署与同步"
echo "  服务器: $SERVER"
echo "========================================="
echo ""

# 1. 先将本地改动推送到服务器
echo ">>> 第一步: 同步本地代码到服务器..."
echo ""

# 使用 rsync 同步代码（排除 .git、虚拟环境等）
read -p "是否要将本地代码同步到服务器? (y/n): " SYNC_CODE
if [ "$SYNC_CODE" == "y" ]; then
    echo "同步中..."
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='node_modules' \
        --exclude='.next' \
        --exclude='sunday.db' \
        ./ ${USER}@${SERVER}:${REPO_PATH}/
    echo "✓ 代码同步完成"
fi

echo ""
echo ">>> 第二步: 在服务器上提交并推送到 GitHub..."
echo ""

# 2. SSH 到服务器，提交并推送
ssh -t ${USER}@${SERVER} << 'ENDSSH'
cd /opt/sundayos

echo ">>> 当前 Git 状态:"
git status --short | head -20

echo ""
echo ">>> 添加所有改动..."
git add -A

echo ""
echo ">>> 提交改动..."
git commit -m "deploy: sync from local + v0.10.0 deployment configs

- Added GitHub Actions auto-deploy workflow
- Added manual deployment script
- Synced latest changes from local development

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" || echo "没有新的改动需要提交"

echo ""
echo ">>> 推送到 GitHub..."
git push origin main

echo ""
echo "✓ 推送完成"
ENDSSH

echo ""
echo ">>> 第三步: 重启服务..."
echo ""

# 3. 重启服务
ssh -t ${USER}@${SERVER} << 'ENDSSH'
cd /opt/sundayos

echo ">>> 更新依赖..."
source .venv/bin/activate
pip install -q -r backend/requirements.txt

echo ">>> 重启 Sunday 服务..."
sudo systemctl restart sunday.service

echo ">>> 等待服务启动..."
sleep 3

echo ">>> 检查服务状态..."
sudo systemctl status sunday.service --no-pager -l | head -20

echo ""
echo ">>> 验证健康端点..."
curl -s http://localhost:8005/health | python3 -m json.tool

echo ""
echo "=== 部署完成 ==="
ENDSSH

echo ""
echo "========================================="
echo "  ✅ 所有步骤完成！"
echo "========================================="
echo ""
echo "验证部署："
echo "  curl http://45.207.220.124:8005/health"
echo ""
echo "查看日志:"
echo "  ssh root@45.207.220.124 'journalctl -u sunday -n 50'"
