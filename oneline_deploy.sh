#!/bin/bash
# 超简单部署 - 一条命令搞定
# 使用方法: bash oneline_deploy.sh

echo "密码: FvzHPk2crcQ6"
echo ""
echo "即将在 3 秒后开始部署..."
sleep 3

ssh root@45.207.220.124 << 'ENDSSH'
cd /opt/sundayos && \
git pull origin main && \
cat VERSION && \
source .venv/bin/activate && \
pip install -q -r backend/requirements.txt && \
systemctl restart sunday.service && \
sleep 3 && \
curl -s http://localhost:8005/health | python3 -m json.tool && \
echo "✅ 部署完成"
ENDSSH
