#!/bin/bash
# 一键部署命令 - 直接复制粘贴到终端执行

# 当提示输入密码时，输入: FvzHPk2crcQ6

ssh root@45.207.220.124 << 'ENDSSH'
cd /opt/sundayos

echo "=== 1. 当前状态 ==="
git status --short | head -20
git log --oneline -3

echo ""
echo "=== 2. 拉取本地最新提交 ==="
git fetch origin
git reset --hard origin/main

echo ""
echo "=== 3. 查看最新状态 ==="
git log --oneline -3

echo ""
echo "=== 4. 更新依赖 ==="
source .venv/bin/activate
pip install -q -r backend/requirements.txt

echo ""
echo "=== 5. 重启服务 ==="
systemctl restart sunday.service
sleep 3

echo ""
echo "=== 6. 检查服务 ==="
systemctl status sunday.service --no-pager -l | head -15

echo ""
echo "=== 7. 验证版本 ==="
curl -s http://localhost:8005/health | python3 -m json.tool | grep version

echo ""
echo "✅ 部署完成！"
ENDSSH
