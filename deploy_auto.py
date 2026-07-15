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
    """执行部署"""
    print("=" * 50)
    print("  Sunday OS 自动部署")
    print("  服务器:", SERVER)
    print("=" * 50)
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
