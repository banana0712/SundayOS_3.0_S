#!/bin/bash
# SundayOS 自动部署脚本

SERVER="ubuntu@45.207.220.124"
REMOTE_PATH="/home/ubuntu/SundayOS"

echo "=== SundayOS 自动部署 ==="
echo ""

# 1. 使用 rsync 同步文件到服务器
echo "1. 同步文件到服务器..."
rsync -avz --delete \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='node_modules/' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='.next/' \
    backend/app/routers/logs.py \
    backend/app/main.py \
    $SERVER:$REMOTE_PATH/backend/app/

# 2. 重启服务
echo ""
echo "2. 重启服务..."
ssh $SERVER "sudo systemctl restart sunday.service"

# 3. 等待启动
sleep 2

# 4. 检查状态
echo ""
echo "3. 检查服务状态..."
ssh $SERVER "sudo systemctl status sunday.service --no-pager -l | head -20"

echo ""
echo "=== 部署完成 ==="
