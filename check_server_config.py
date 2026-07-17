#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查服务器上的引擎配置"""

import paramiko
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"

print("=== 检查服务器引擎配置 ===\n")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
    print("✓ 已连接\n")

    # 查看 registry.py 中豆包的配置
    print("1. 检查豆包配置...")
    cmd = f"cd {REMOTE_PATH} && grep -A 10 'id=\"doubao-chat\"' backend/app/engines/registry.py"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    print("\n2. 检查 DeepSeek 配置...")
    cmd = f"cd {REMOTE_PATH} && grep -A 10 'id=\"deepseek-chat\"' backend/app/engines/registry.py"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    print("\n3. 检查当前 Git 版本...")
    cmd = f"cd {REMOTE_PATH} && git log -1 --oneline"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    print(output)

    ssh.close()

except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
