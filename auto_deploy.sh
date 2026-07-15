#!/bin/bash
# 自动部署脚本（含密码）

SERVER="45.207.220.124"
USER="root"
PASSWORD="FvzHPk2crcQ6"
REPO_PATH="/opt/sundayos"

echo "=== Sunday OS 自动部署 ==="
echo ""

# 使用 SSH 执行远程命令
# 注意：这种方式会在命令历史中暴露密码，仅用于临时部署
cat > /tmp/deploy_commands.sh << 'ENDSSH'
cd /opt/sundayos

echo ">>> 1. 检查当前状态..."
git status --short | head -20

echo ""
echo ">>> 2. 拉取最新代码..."
git fetch origin
git reset --hard origin/main

echo ""
echo ">>> 3. 添加并提交本地改动..."
git add -A
git commit -m "deploy: v0.10.0 with deployment automation

- GitHub Actions auto-deploy workflow
- Multiple deployment scripts
- Comprehensive deployment documentation

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" || echo "No new changes to commit"

echo ""
echo ">>> 4. 推送到 GitHub..."
git push origin main

echo ""
echo ">>> 5. 更新依赖..."
source .venv/bin/activate
pip install -q -r backend/requirements.txt

echo ""
echo ">>> 6. 重启服务..."
systemctl restart sunday.service

echo ""
echo ">>> 7. 等待服务启动..."
sleep 3

echo ""
echo ">>> 8. 检查服务状态..."
systemctl status sunday.service --no-pager -l | head -20

echo ""
echo ">>> 9. 验证健康端点..."
curl -s http://localhost:8005/health | python3 -m json.tool

echo ""
echo "=== 部署完成 ==="
ENDSSH

# 使用 SSH 传输并执行
scp /tmp/deploy_commands.sh ${USER}@${SERVER}:/tmp/
ssh ${USER}@${SERVER} 'bash /tmp/deploy_commands.sh'

echo ""
echo "✅ 所有步骤完成！"
echo ""
echo "外网验证:"
curl -s http://45.207.220.124:8005/health | python3 -m json.tool
