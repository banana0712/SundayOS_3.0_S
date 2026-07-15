#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sunday OS 自动部署脚本 (Python版)
自动SSH登录并部署
"""
import paramiko
import sys
import time
import io

# 修复Windows控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER = "45.207.220.124"
USER = "root"
PASSWORD = "FvzHPk2crcQ6"
PORT = 22

def run_command(ssh, command):
    """执行命令并打印输出"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if output:
        print(output)
    if error:
        print(error, file=sys.stderr)

    return exit_status == 0

def deploy():
    """执行完整部署流程"""
    print("=" * 50)
    print("  Sunday OS 完整部署")
    print("  本地 → GitHub → 服务器")
    print("=" * 50)
    print()

    # ========== 第一步：本地推送到 GitHub ==========
    print(">>> 第一步：推送本地代码到 GitHub")
    print()

    import subprocess
    import os

    # 检查是否有未提交的改动
    result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
    if result.stdout.strip():
        print("发现未提交的改动：")
        print(result.stdout)
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
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ 推送成功")
        print()
    else:
        # 检查是否已经是最新
        if 'Everything up-to-date' in result.stderr or 'up to date' in result.stderr.lower():
            print("✓ 已是最新（无需推送）")
            print()
        else:
            print("✗ 推送失败:")
            print(result.stderr)
            return False

    # ========== 第二步：服务器拉取并部署 ==========
    print(">>> 第二步：服务器部署")
    print()

    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(">>> 连接服务器...")
        ssh.connect(SERVER, PORT, USER, PASSWORD, timeout=10)
        print("✓ 连接成功")
        print()

        # 执行部署命令
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

        print("=" * 50)
        print("  ✅ 部署完成！")
        print("=" * 50)
        print()
        print("外网验证:")
        print("  curl http://45.207.220.124:8005/health")

    except paramiko.AuthenticationException:
        print("✗ 认证失败，请检查密码")
        return False
    except paramiko.SSHException as e:
        print(f"✗ SSH连接错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 部署失败: {e}")
        return False
    finally:
        ssh.close()

    return True

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
