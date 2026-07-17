#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试豆包 API"""

import requests
import json
import os

url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('CUSTOM_API_KEY', 'YOUR_API_KEY_HERE')}"
}
data = {
    "model": "doubao-seed-character-260628",
    "messages": [
        {"role": "system", "content": "你是人工智能助手."},
        {"role": "user", "content": "你好"}
    ]
}

print("=== 测试豆包 API ===\n")
try:
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"状态码: {resp.status_code}")
    print(f"响应:\n{json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")
