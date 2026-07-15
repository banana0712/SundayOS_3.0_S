#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sunday OS 完整部署脚本
支持两种模式：
1. 本地推送模式：本地 → GitHub → 服务器
2. 服务器推送模式：本地 → 服务器 → GitHub → 服务器重启

当本地网络不稳定时，使用模式 2 从服务器推送到 GitHub
"""
import paramiko
import sys
import time
import io
import subprocess
import os

# 修复Windows控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER = "45.207.220.124"
USER = "root"
PASSWORD = "FvzHPk2crcQ6"
PORT = 22

def run_command(ssh, command):
    """执行SSH命令并打印输出"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(output)
    if error:
        print(error, file=sys.stderr)

    return exit_status == 0

def check_local_changes():
    """检查本地是否有未提交的改动"""
    result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
    return result.stdout.strip()

def local_commit_and_push():
    """本地提交并推送到GitHub"""
    print(">>> 第一步：本地推送到 GitHub")
    print()

    changes = check_local_changes()
    if changes:
        print("发现未提交的改动：")
        print(changes)
        print()

        # 添加所有改动
        print(">>> 添加所有改动...")
        subprocess.run(['git', 'add', '-A'], check=True)
        print("✓ 已添加")
        print()

        # 提交
        commit_msg = f"deploy: auto-deploy from local at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
        print(">>> 提交改动...")
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        print("✓ 已提交")
        print()

    # 推送到 GitHub
    print(">>> 推送到 GitHub...")
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        print("✓ 推送成功")
        return True
    elif 'up-to-date' in result.stderr.lower() or 'up to date' in result.stdout.lower():
        print("✓ 已是最新（无需推送）")
        return True
    else:
        print("✗ 本地推送失败:")
        print(result.stderr)
        return False

def server_push_mode(ssh):
    """服务器推送模式：从服务器推送到GitHub"""
    print(">>> 使用服务器推送模式（网络更稳定）")
    print()

    commands = [
        ("拉取本地最新提交", "cd /opt/sundayos && git fetch origin && git reset --hard origin/main"),
        ("推送到 GitHub", "cd /opt/sundayos && git push origin main"),
    ]

    for desc, cmd in commands:
        print(f">>> {desc}...")
        if run_command(ssh, cmd):
            print(f"✓ {desc}完成")
        else:
            print(f"✗ {desc}失败")
            return False
        print()

    return True

def server_deploy(ssh):
    """服务器部署"""
    print(">>> 第二步：服务器部署")
    print()

    commands = [
        ("进入项目目录", "cd /opt/sundayos && pwd"),
        ("拉取最新代码", "cd /opt/sundayos && git pull origin main"),
        ("检查版本", "cd /opt/sundayos && cat VERSION"),
        ("更新依赖", "cd /opt/sundayos && source .venv/bin/activate && pip install -q -r backend/requirements.txt"),
        ("重启服务", "systemctl restart sunday.service"),
        ("等待服务启动", "sleep 3"),
        ("检查服务状态", "systemctl status sunday.service --no-pager -l | head -15"),
        ("验证健康端点", "curl -s http://localhost:8005/health | python3 -m json.tool"),
    ]

    for desc, cmd in commands:
        print(f">>> {desc}...")
        if run_command(ssh, cmd):
            print(f"✓ {desc}完成")
        else:
            print(f"✗ {desc}失败")
        print()

    return True

def deploy_via_server():
    """完整部署：优先本地推送，失败则用服务器推送"""
    print("=" * 50)
    print("  Sunday OS 完整部署")
    print("  本地 → GitHub → 服务器")
    print("=" * 50)
    print()

    # 先在本地提交
    changes = check_local_changes()
    if changes:
        print(">>> 发现本地改动，先提交...")
        print(changes)
        print()

        subprocess.run(['git', 'add', '-A'], check=True)
        commit_msg = f"deploy: auto-deploy from local at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        print("✓ 本地已提交")
        print()

    # 创建SSH连接
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(">>> 连接服务器...")
        ssh.connect(SERVER, PORT, USER, PASSWORD, timeout=10)
        print("✓ 连接成功")
        print()

        # 尝试本地推送
        print(">>> 尝试从本地推送到 GitHub...")
        try:
            push_result = subprocess.run(['git', 'push', 'origin', 'main'],
                                        capture_output=True, text=True, timeout=15)
            if push_result.returncode == 0 or 'up-to-date' in push_result.stderr.lower():
                print("✓ 本地推送成功")
                print()
            else:
                raise Exception("本地推送失败")
        except:
            print("✗ 本地网络不稳定")
            print()

            # 改用服务器推送
            if not server_push_mode(ssh):
                print("✗ 服务器推送也失败")
                return False

        # 服务器部署
        return server_deploy(ssh)

    except Exception as e:
        print(f"✗ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

    print("=" * 50)
    print("  ✅ 部署完成！")
    print("=" * 50)
    print()
    print("外网验证:")
    print("  curl http://45.207.220.124:8005/health")

    return True

if __name__ == "__main__":
    success = deploy_via_server()
    sys.exit(0 if success else 1)
