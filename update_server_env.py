#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新服务器 .env 文件"""

import paramiko
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos/backend"

print("=== 更新服务器 .env ===\n")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
    print("✓ 已连接\n")

    # 添加 CUSTOM_MODEL_CHAT
    print("添加 CUSTOM_MODEL_CHAT 配置...")
    cmd = f'''cd {REMOTE_PATH} && grep -q "CUSTOM_MODEL_CHAT" .env || echo "CUSTOM_MODEL_CHAT=doubao-seed-character-260628" >> .env'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()

    # 如果已存在但值不对，更新它
    cmd = f'''cd {REMOTE_PATH} && sed -i 's/^CUSTOM_MODEL_CHAT=.*/CUSTOM_MODEL_CHAT=doubao-seed-character-260628/' .env'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()

    print("✓ 已更新\n")

    # 验证配置
    print("验证 .env 配置...")
    cmd = f"grep CUSTOM_ {REMOTE_PATH}/.env"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    # 重启服务
    print("\n重启服务...")
    cmd = "systemctl restart sunday.service"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()
    print("✓ 服务已重启\n")

    ssh.close()

except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
