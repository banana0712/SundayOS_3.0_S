#!/bin/bash
# SundayOS 一键自动部署脚本（无需交互）

set -e

SERVER="45.207.220.124"
USER="root"
REMOTE_PATH="/opt/sundayos"
PASSWORD_FILE="$HOME/.sundayos_deploy_password"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== SundayOS 自动部署 ==="

# 检查密码文件
if [ ! -f "$PASSWORD_FILE" ]; then
    echo "首次使用，请输入服务器密码（只需输入一次）："
    read -s password
    echo "$password" > "$PASSWORD_FILE"
    chmod 600 "$PASSWORD_FILE"
    echo -e "${GREEN}✓ 密码已保存${NC}"
fi

PASSWORD=$(cat "$PASSWORD_FILE")

# 1. 上传修改的文件
echo ""
echo "1. 上传文件到服务器..."

# 使用 sftp 批量上传
cat > /tmp/sftp_commands << SFTP_EOF
put backend/app/routers/logs.py $REMOTE_PATH/backend/app/routers/logs.py
put backend/app/main.py $REMOTE_PATH/backend/app/main.py
bye
SFTP_EOF

expect << EXPECT_EOF
set timeout 30
spawn sftp -b /tmp/sftp_commands $USER@$SERVER
expect {
    "password:" {
        send "$PASSWORD\r"
        exp_continue
    }
    eof
}
EXPECT_EOF

rm /tmp/sftp_commands

echo -e "${GREEN}✓ 文件上传完成${NC}"

# 2. 重启服务
echo ""
echo "2. 重启服务..."

expect << EXPECT_EOF
set timeout 10
spawn ssh $USER@$SERVER "systemctl restart sunday.service"
expect {
    "password:" {
        send "$PASSWORD\r"
        exp_continue
    }
    eof
}
EXPECT_EOF

echo -e "${GREEN}✓ 服务已重启${NC}"

# 3. 检查状态
echo ""
echo "3. 检查服务状态..."

expect << EXPECT_EOF
set timeout 10
spawn ssh $USER@$SERVER "systemctl status sunday.service --no-pager -l | head -15"
expect {
    "password:" {
        send "$PASSWORD\r"
        exp_continue
    }
    eof
}
EXPECT_EOF

echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo "API 地址: http://45.207.220.124:8005"
