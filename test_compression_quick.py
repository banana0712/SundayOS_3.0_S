#!/usr/bin/env python3
"""Quick compression test"""

import requests
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://45.207.220.124:8005"
API_KEY = "sunday0712"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

print("=== 快速压缩测试 ===\n")

# 1. 创建对话
print("1. 创建对话...")
resp = requests.post(f"{BASE_URL}/api/conversations", json={"title": "压缩测试2"}, headers=HEADERS)
conv_id = resp.json()["id"]
print(f"   ID: {conv_id}\n")

# 2. 发送3条消息看日志
print("2. 发送3条消息（检查日志输出）...")
for i in range(1, 4):
    print(f"   消息 {i}...", end=" ", flush=True)
    resp = requests.post(
        f"{BASE_URL}/api/chat",
        json={"conversation_id": conv_id, "message": f"测试{i}"},
        headers=HEADERS,
        timeout=120
    )
    print("✓" if resp.status_code == 200 else f"✗({resp.status_code})")

print("\n3. 查看服务器日志（查找 COMPRESSION_CHECK）...")
print("   请手动执行: ssh root@45.207.220.124")
print(f"   journalctl -u sunday --since '1 minute ago' | grep -E 'AFTER ADD|COMPRESSION_CHECK|{conv_id}'")

print("\n=== 完成 ===")
