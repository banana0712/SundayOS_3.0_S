#!/bin/bash
# Sunday OS 手动部署脚本
# 在你的本地电脑运行，会 SSH 到服务器执行部署

set -e

SERVER="45.207.220.124"
USER="root"

echo "==================================="
echo "  Sunday OS 手动部署"
echo "  目标服务器: $SERVER"
echo "==================================="
echo ""

# 提示用户确认
read -p "按 Enter 继续，Ctrl+C 取消..."

# SSH 连接并执行部署命令
ssh -t ${USER}@${SERVER} << 'EOF'
echo ">>> 进入项目目录..."
cd /opt/sundayos

echo ">>> 拉取最新代码..."
git pull origin main

echo ">>> 更新依赖..."
source .venv/bin/activate
pip install -q -r backend/requirements.txt

echo ">>> 重启服务..."
sudo systemctl restart sunday.service

echo ">>> 等待服务启动..."
sleep 3

echo ">>> 检查服务状态..."
sudo systemctl status sunday.service --no-pager -l

echo ""
echo ">>> 验证健康端点..."
curl -s http://localhost:8005/health | python3 -m json.tool

echo ""
echo "=== 部署完成 ==="
EOF

echo ""
echo "✅ 部署成功！"
echo ""
echo "验证："
echo "  curl http://45.207.220.124:8005/health"
