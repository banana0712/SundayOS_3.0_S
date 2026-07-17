#!/usr/bin/env python3
"""Upload guardrails module to server"""

import paramiko
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.chdir("C:/Users/18176/Desktop/SundayOS")

SERVER = "45.207.220.124"
USERNAME = "root"
PASSWORD = "FvzHPk2crcQ6"
REMOTE_PATH = "/opt/sundayos"

print("=== Upload Guardrails Module ===\n")

files = [
    ("backend/app/guardrails/__init__.py", f"{REMOTE_PATH}/backend/app/guardrails/__init__.py"),
    ("backend/app/guardrails/pii.py", f"{REMOTE_PATH}/backend/app/guardrails/pii.py"),
    ("backend/app/guardrails/pipeline.py", f"{REMOTE_PATH}/backend/app/guardrails/pipeline.py"),
]

print("1. Connecting...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
print("   Connected\n")

print("2. Creating directory...")
ssh.exec_command(f"mkdir -p {REMOTE_PATH}/backend/app/guardrails")
print("   Created\n")

print("3. Uploading files...")
sftp = ssh.open_sftp()

for local, remote in files:
    try:
        sftp.put(local, remote)
        print(f"   ✓ {local}")
    except Exception as e:
        print(f"   ✗ {local}: {e}")

sftp.close()

print("\n4. Restarting service...")
ssh.exec_command("systemctl restart sunday.service")
print("   Restarted\n")

import time
time.sleep(5)

print("5. Checking status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status sunday.service --no-pager | head -15")
status = stdout.read().decode('utf-8')
print(status)

if 'active (running)' in status:
    print("\n✓ Service running!")
else:
    print("\n✗ Still failing. Last 10 log lines:")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u sunday -n 10 --no-pager")
    print(stdout.read().decode('utf-8'))

ssh.close()
print("\n=== Done ===")
