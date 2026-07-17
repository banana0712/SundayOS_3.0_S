#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中止rebase并重新同步"""

import paramiko
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"

print("=== 重置服务器 Git 状态 ===\n")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
    print("✓ 已连接\n")

    # 1. 中止 rebase
    print("1. 中止当前 rebase...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git rebase --abort")
    stdout.channel.recv_exit_status()
    print("✓ 已中止\n")

    # 2. 强制重置到远程状态
    print("2. 重置到远程 main...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git fetch origin && git reset --hard origin/main")
    print(stdout.read().decode('utf-8'))

    # 3. 清理未跟踪文件
    print("3. 清理...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git clean -fd")
    print(stdout.read().decode('utf-8'))

    # 4. 查看最终状态
    print("4. 当前状态:")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && git status")
    print(stdout.read().decode('utf-8'))

    # 5. 重启服务
    print("\n5. 重启服务...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart sunday.service && sleep 2 && systemctl status sunday.service --no-pager | head -10")
    print(stdout.read().decode('utf-8'))

    ssh.close()
    print("\n✓ 服务器已重置到 GitHub 最新状态")
    print("✓ 现在可以重新部署了")

except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
