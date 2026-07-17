#!/usr/bin/env python3
"""Deploy compression feature + all dependencies to server"""

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

print("=== Full Deployment ===\n")

# All files to upload
files = [
    # Core deps
    ("backend/app/deps.py", f"{REMOTE_PATH}/backend/app/deps.py"),
    ("backend/app/main.py", f"{REMOTE_PATH}/backend/app/main.py"),

    # All routers
    ("backend/app/routers/__init__.py", f"{REMOTE_PATH}/backend/app/routers/__init__.py"),
    ("backend/app/routers/admin.py", f"{REMOTE_PATH}/backend/app/routers/admin.py"),
    ("backend/app/routers/auth.py", f"{REMOTE_PATH}/backend/app/routers/auth.py"),
    ("backend/app/routers/chat.py", f"{REMOTE_PATH}/backend/app/routers/chat.py"),
    ("backend/app/routers/conversations.py", f"{REMOTE_PATH}/backend/app/routers/conversations.py"),
    ("backend/app/routers/debug.py", f"{REMOTE_PATH}/backend/app/routers/debug.py"),
    ("backend/app/routers/logs.py", f"{REMOTE_PATH}/backend/app/routers/logs.py"),
    ("backend/app/routers/memory.py", f"{REMOTE_PATH}/backend/app/routers/memory.py"),
    ("backend/app/routers/misc.py", f"{REMOTE_PATH}/backend/app/routers/misc.py"),
    ("backend/app/routers/preferences.py", f"{REMOTE_PATH}/backend/app/routers/preferences.py"),

    # Compression feature
    ("backend/app/cognition/context_window.py", f"{REMOTE_PATH}/backend/app/cognition/context_window.py"),
    ("backend/app/cognition/context_builder.py", f"{REMOTE_PATH}/backend/app/cognition/context_builder.py"),
]

print("1. Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, 22, USERNAME, PASSWORD, timeout=10)
print("   Connected\n")

print("2. Uploading files...")
sftp = ssh.open_sftp()
success = 0
failed = 0

for local, remote in files:
    try:
        sftp.put(local, remote)
        print(f"   ✓ {local}")
        success += 1
    except Exception as e:
        print(f"   ✗ {local}: {e}")
        failed += 1

sftp.close()
print(f"\n   Uploaded: {success}/{len(files)} files\n")

print("3. Restarting service...")
ssh.exec_command("systemctl restart sunday.service")
print("   Restarted\n")

import time
time.sleep(5)

print("4. Checking service status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status sunday.service --no-pager | head -15")
status = stdout.read().decode('utf-8')
print(status)

if 'active (running)' in status:
    print("\n✓ Service is running!")
    print("\n5. Testing health endpoint...")
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8005/health | python3 -m json.tool")
    print(stdout.read().decode('utf-8'))
else:
    print("\n✗ Service failed to start. Checking logs...")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u sunday -n 20 --no-pager")
    print(stdout.read().decode('utf-8'))

ssh.close()
print("\n=== Deployment Complete ===")
