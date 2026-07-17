#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试生产环境的模型路由"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER = "http://45.207.220.124:8005"

print("=== 测试生产环境模型路由 ===\n")

# 1. 先注册一个测试用户
print("1. 注册测试用户...")
register_resp = requests.post(f"{SERVER}/api/auth/register", json={
    "username": f"test_routing_{int(__import__('time').time())}",
    "password": "test1234"
})

if register_resp.status_code == 200:
    token = register_resp.json()["token"]
    print(f"✓ 获得 token: {token[:20]}...\n")
else:
    print(f"✗ 注册失败: {register_resp.text}")
    sys.exit(1)

# 2. 发送测试消息
print("2. 发送测试消息...")
test_messages = [
    "你好",
    "今天天气真不错",
    "帮我写一个Python函数",
]

for i, msg in enumerate(test_messages, 1):
    print(f"\n--- 测试 {i}: {msg} ---")

    chat_resp = requests.post(
        f"{SERVER}/api/chat/stream",
        headers={
            "X-Sunday-Token": token,
            "Content-Type": "application/json"
        },
        json={
            "message": msg,
            "conversation_id": "test_conv"
        },
        stream=True
    )

    if chat_resp.status_code != 200:
        print(f"✗ 请求失败: {chat_resp.status_code}")
        continue

    # 解析 SSE 流
    engine_used = None
    reply_text = ""

    for line in chat_resp.iter_lines():
        if not line:
            continue

        line = line.decode('utf-8')
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if data.get('type') == 'text':
                    reply_text += data.get('content', '')
                elif data.get('type') == 'done':
                    engine_used = data.get('engine')
                    print(f"引擎: {engine_used}")
                    print(f"回复: {reply_text[:100]}...")
            except:
                pass

print("\n=== 测试完成 ===")
