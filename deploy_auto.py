#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SundayOS 一键自动部署脚本（零交互）
流程：本地 → 服务器 → GitHub
服务器在香港，网络更稳定，由服务器推送到 GitHub
"""

import paramiko
import os
import sys
import subprocess
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

def get_changed_files():
    """获取本地 git 变更的文件列表"""
    try:
        result = subprocess.run(['git', 'diff', '--name-only', 'origin/main'],
                              capture_output=True, text=True, encoding='utf-8')
        files = result.stdout.strip().split('\n')
        files = [f for f in files if f and not f.startswith('.')]
        return files
    except Exception as e:
        print(f"  ⚠ 无法获取 git diff: {e}")
        return []

def upload_file(sftp, local_path, remote_path):
    """上传单个文件"""
    try:
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except:
            # 目录不存在，递归创建
            dirs = []
            while remote_dir and remote_dir != '/':
                dirs.append(remote_dir)
                remote_dir = os.path.dirname(remote_dir)
            dirs.reverse()
            for d in dirs:
                try:
                    sftp.stat(d)
                except:
                    sftp.mkdir(d)

        sftp.put(local_path, remote_path)
        print(f"  ✓ {local_path}")
        return True
    except Exception as e:
        print(f"  ✗ {local_path}: {e}")
        return False

def main():
    print("=== SundayOS 自动部署 ===")
    print("流程: 本地 → 服务器 → GitHub (服务器推送)\n")

    # 1. 加载密码
    load_or_save_password()

    # 2. 获取要上传的文件
    print("\n1. 检测变更文件...")
    changed_files = get_changed_files()

    if not changed_files:
        print("  ⚠ 没有检测到变更文件，将上传关键文件")
        # 使用固定列表
        changed_files = [
            "backend/app/webchat.py",
            "backend/app/main.py",
            "backend/app/engines/registry.py",
            "backend/app/conversation/context_window.py",
        ]

    print(f"  ✓ 将上传 {len(changed_files)} 个文件")

    # 3. 连接服务器
    print("\n2. 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(SERVER, PORT, USERNAME, PASSWORD, timeout=10)
        print(f"  ✓ 已连接到 {SERVER}")
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        sys.exit(1)

    # 4. 上传文件
    print("\n3. 上传文件...")
    sftp = ssh.open_sftp()

    success_count = 0
    for local_file in changed_files:
        if os.path.exists(local_file):
            remote_file = f"{REMOTE_PATH}/{local_file}"
            if upload_file(sftp, local_file, remote_file):
                success_count += 1

    sftp.close()
    print(f"  完成: {success_count}/{len(changed_files)} 个文件")

    # 5. 服务器端 Git 提交并推送到 GitHub
    print("\n4. 服务器提交变更到 Git...")
    commands = [
        f"cd {REMOTE_PATH}",
        "git add -A",
        "git status --short",
    ]

    stdin, stdout, stderr = ssh.exec_command(" && ".join(commands))
    git_status = stdout.read().decode('utf-8')

    if git_status.strip():
        print(f"  变更文件:\n{git_status}")

        # 提交变更
        commit_msg = f"deploy: auto-deploy from server at $(date '+%Y-%m-%d %H:%M:%S')\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
        commit_cmd = f"cd {REMOTE_PATH} && git commit -m '{commit_msg}'"
        stdin, stdout, stderr = ssh.exec_command(commit_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print("  ✓ Git 提交成功")
        else:
            error = stderr.read().decode('utf-8')
            print(f"  ⚠ Git 提交: {error}")
    else:
        print("  ℹ 服务器端没有新变更")

    # 6. 推送到 GitHub
    print("\n5. 推送到 GitHub...")
    push_cmd = f"cd {REMOTE_PATH} && git push origin main 2>&1"
    stdin, stdout, stderr = ssh.exec_command(push_cmd)
    push_output = stdout.read().decode('utf-8')
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0 or "up to date" in push_output.lower():
        print("  ✓ 推送到 GitHub 成功")
        if "up to date" in push_output.lower():
            print("  ℹ GitHub 已是最新")
    else:
        print(f"  ⚠ 推送失败: {push_output}")

    # 7. 重启服务
    print("\n6. 重启服务...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart sunday.service")
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("  ✓ 服务已重启")
    else:
        print(f"  ⚠ 重启命令返回: {exit_code}")

    # 8. 检查状态
    print("\n7. 检查服务状态...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status sunday.service --no-pager -l | head -15")
    status = stdout.read().decode('utf-8')
    print(status)

    ssh.close()

    print("\n=== 部署完成 ===")
    print(f"API 地址: http://{SERVER}:8005")
    print(f"GitHub: https://github.com/banana0712/SundayOS_3.0_S")
    print(f"\n✨ 代码已自动同步到 GitHub（服务器推送）")

if __name__ == "__main__":
    main()
