#!/usr/bin/env python3
"""Test compression feature on remote server"""

import requests
import time
import json
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://45.207.220.124:8005"
API_KEY = "sunday0712"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

print("=== 压缩功能测试 ===\n")

# 1. 创建对话
print("1. 创建新对话...")
resp = requests.post(
    f"{BASE_URL}/api/conversations",
    json={"title": "压缩测试对话"},
    headers=HEADERS
)
if resp.status_code != 200:
    print(f"   创建失败: {resp.status_code} - {resp.text}")
    sys.exit(1)

conv = resp.json()
conv_id = conv["id"]
print(f"   对话ID: {conv_id}\n")

# 2. 发送13条消息（触发压缩阈值12）
print("2. 发送13条消息（阈值12，应触发压缩）...")
print("   每条消息可能需要1-2分钟等待LLM响应...\n")

success_count = 0
for i in range(1, 14):
    print(f"   发送消息 {i}/13...", end=" ", flush=True)
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "conversation_id": conv_id,
                "message": f"测试消息 {i}"
            },
            headers=HEADERS,
            timeout=120  # 增加到2分钟
        )

        if resp.status_code == 200:
            print("✓")
            success_count += 1
        else:
            print(f"✗ ({resp.status_code})")
    except requests.exceptions.Timeout:
        print("✗ (超时)")
    except Exception as e:
        print(f"✗ ({e})")

    time.sleep(1)

print(f"\n   成功: {success_count}/13\n")

# 3. 查看压缩统计
print("3. 查看压缩统计...")
resp = requests.get(f"{BASE_URL}/api/debug/compression/stats", headers=HEADERS)
if resp.status_code == 200:
    stats = resp.json()
    print(f"   总压缩次数: {stats.get('total_compressions', 0)}")
    print(f"   总处理消息: {stats.get('total_messages_processed', 0)}")
    if stats.get('avg_compression_ratio'):
        print(f"   平均压缩比: {stats.get('avg_compression_ratio', 0):.2%}")
    print()
else:
    print(f"   获取统计失败: {resp.status_code}\n")

# 4. 查看该对话的压缩详情
print("4. 查看对话压缩详情...")
resp = requests.get(f"{BASE_URL}/api/debug/compression/{conv_id}", headers=HEADERS)
if resp.status_code == 200:
    details = resp.json()

    if details:
        print(f"   压缩次数: {details.get('compression_count', 0)}")
        print(f"   最后压缩时间: {details.get('last_compression_time', 'N/A')}")
        print(f"   压缩前消息数: {details.get('messages_before', 0)}")
        print(f"   压缩后消息数: {details.get('messages_after', 0)}")

        if details.get('facts_extracted'):
            print(f"\n   提取的事实:")
            for fact in details.get('facts_extracted', [])[:5]:
                print(f"     - {fact}")
    else:
        print("   未发生压缩")
else:
    print(f"   获取详情失败: {resp.status_code}")

# 5. 获取当前对话历史，验证消息数量
print("\n5. 验证当前消息数量...")
resp = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", headers=HEADERS)
if resp.status_code == 200:
    conv_data = resp.json()
    messages = conv_data.get("messages", [])
    print(f"   当前消息数: {len(messages)}")

    # 如果有摘要消息，显示出来
    for msg in messages:
        if msg.get("role") == "system" and "上下文摘要" in msg.get("content", ""):
            print(f"\n   找到摘要消息:")
            print(f"   {msg['content'][:200]}...")
            break

    if len(messages) <= 8:
        print(f"\n   ✓ 压缩成功（预期≤8条）")
    else:
        print(f"\n   ✗ 未压缩或压缩失败（预期≤8条）")
else:
    print(f"   获取对话失败: {resp.status_code}")

print("\n=== 测试完成 ===")
