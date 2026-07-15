#!/bin/bash
# 快速部署脚本 - 仅推送和重启（假设代码已在服务器上）

SERVER="45.207.220.124"
USER="root"

echo "=== Sunday OS 快速部署 ==="

ssh -t ${USER}@${SERVER} << 'ENDSSH'
cd /opt/sundayos

# Git 操作
git status --short
git add -A
git commit -m "deploy: update from local" || echo "No changes to commit"
git push origin main

# 重启服务
source .venv/bin/activate
pip install -q -r backend/requirements.txt
sudo systemctl restart sunday.service
sleep 3

# 验证
curl -s http://localhost:8005/health | python3 -m json.tool
echo ""
echo "✅ 部署完成"
ENDSSH
