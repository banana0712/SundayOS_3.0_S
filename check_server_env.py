#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查服务器环境变量"""

import paramiko
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"

print("=== 检查服务器环境变量 ===\n")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
    print("✓ 已连接\n")

    print("1. 检查 backend/.env 文件是否存在...")
    cmd = f"ls -la {REMOTE_PATH}/backend/.env"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    if error:
        print(f"✗ .env 文件不存在: {error}")
    else:
        print(f"✓ 文件存在:\n{output}")

    print("\n2. 检查 .env 中的 CUSTOM_API_KEY...")
    cmd = f"grep CUSTOM_API_KEY {REMOTE_PATH}/backend/.env 2>/dev/null || echo '未找到 CUSTOM_API_KEY'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    print("\n3. 检查 .env 中的 CUSTOM_BASE_URL...")
    cmd = f"grep CUSTOM_BASE_URL {REMOTE_PATH}/backend/.env 2>/dev/null || echo '未找到 CUSTOM_BASE_URL'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    print("\n4. 检查 .env 中的 CUSTOM_MODEL_CHAT...")
    cmd = f"grep CUSTOM_MODEL_CHAT {REMOTE_PATH}/backend/.env 2>/dev/null || echo '未找到 CUSTOM_MODEL_CHAT'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    print("\n5. 检查 systemd 服务配置...")
    cmd = "cat /etc/systemd/system/sundayos.service | grep Environment || echo '无 Environment 配置'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    ssh.close()

except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
