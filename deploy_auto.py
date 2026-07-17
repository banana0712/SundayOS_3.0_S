#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SundayOS 一键自动部署脚本（零交互）"""

import paramiko
import os
import sys
from pathlib import Path

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ========== 配置区（首次使用请修改） ==========
SERVER = "45.207.220.124"
PORT = 22
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"
# =============================================

CONFIG_FILE = Path.home() / ".sundayos_deploy_config"

def load_or_save_password():
    """加载或保存密码"""
    global PASSWORD
    if CONFIG_FILE.exists():
        PASSWORD = CONFIG_FILE.read_text().strip()
        print("✓ 已加载保存的密码")
    else:
        if not PASSWORD:
            import getpass
            PASSWORD = getpass.getpass("请输入服务器密码（仅首次需要）: ")
        CONFIG_FILE.write_text(PASSWORD)
        CONFIG_FILE.chmod(0o600)
        print("✓ 密码已保存，下次无需输入")

def upload_file(sftp, local_path, remote_path):
    """上传单个文件"""
    try:
        sftp.put(local_path, remote_path)
        print(f"  ✓ {local_path}")
        return True
    except Exception as e:
        print(f"  ✗ {local_path}: {e}")
        return False

def main():
    print("=== SundayOS 自动部署 ===\n")

    # 1. 加载密码
    load_or_save_password()

    # 2. 连接服务器
    print("\n1. 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(SERVER, PORT, USERNAME, PASSWORD, timeout=10)
        print(f"  ✓ 已连接到 {SERVER}")
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        sys.exit(1)

    # 3. 上传文件
    print("\n2. 上传文件...")
    sftp = ssh.open_sftp()

    files_to_upload = [
        ("backend/app/engines/router.py", f"{REMOTE_PATH}/backend/app/engines/router.py"),
        ("backend/app/main.py", f"{REMOTE_PATH}/backend/app/main.py"),
    ]

    success_count = 0
    for local, remote in files_to_upload:
        if upload_file(sftp, local, remote):
            success_count += 1

    sftp.close()
    print(f"  完成: {success_count}/{len(files_to_upload)} 个文件")

    # 4. 重启服务
    print("\n3. 重启服务...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart sunday.service")
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("  ✓ 服务已重启")
    else:
        print(f"  ⚠ 重启命令返回: {exit_code}")

    # 5. 检查状态
    print("\n4. 检查服务状态...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status sunday.service --no-pager -l | head -15")
    status = stdout.read().decode('utf-8')
    print(status)

    ssh.close()

    print("\n=== 部署完成 ===")
    print(f"API 地址: http://{SERVER}:8005")
    print(f"\n提示: 下次运行只需执行 'python deploy_auto.py' 即可")

if __name__ == "__main__":
    main()
