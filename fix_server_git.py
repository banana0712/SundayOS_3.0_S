#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复服务器 Git 状态"""

import paramiko
import sys
import io

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"

print("=== 修复服务器 Git 状态 ===\n")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
    print(f"✓ 已连接到 {SERVER}\n")

    # 1. 查看当前状态
    print("1. 检查当前状态...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git status")
    print(stdout.read().decode('utf-8'))

    # 2. 拉取远程变更
    print("\n2. 拉取远程变更...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git pull --rebase origin main")
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    print(output)
    if error:
        print("Error:", error)

    # 3. 推送到 GitHub
    print("\n3. 推送到 GitHub...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git push origin main")
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    print(output)
    if error and "up to date" not in error.lower():
        print("Error:", error)

    # 4. 重启服务
    print("\n4. 重启服务...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart sunday.service")
    stdout.channel.recv_exit_status()
    print("✓ 服务已重启")

    # 5. 检查服务状态
    print("\n5. 检查服务状态...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status sunday.service --no-pager -l | head -15")
    print(stdout.read().decode('utf-8'))

    ssh.close()
    print("\n=== 完成 ===")

except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
