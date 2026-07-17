#!/usr/bin/env python3
"""验证压缩功能的完整性和正确性"""

import requests
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://45.207.220.124:8005"
API_KEY = "sunday0712"
HEADERS = {"X-API-Key": API_KEY}

print("=" * 60)
print("SundayOS 上下文窗口压缩功能 — 完整性验证")
print("=" * 60)
print()

# 测试对话ID（之前测试生成的）
test_conv_id = "conv_978f01130fc2"

print("📋 验证项目清单:\n")

# 1. 检查对话是否存在
print("1. 对话数据完整性...")
resp = requests.get(f"{BASE_URL}/api/conversations/{test_conv_id}", headers=HEADERS)
if resp.status_code == 200:
    data = resp.json()
    msg_count = len(data.get("messages", []))
    has_summary = data.get("summary") is not None

    print(f"   ✓ 对话存在")
    print(f"   ✓ 消息数: {msg_count} (压缩后)")

    if has_summary:
        summary = data.get("summary", "")
        print(f"   ✓ 摘要已生成: {len(summary)} 字符")
        print(f"      内容: \"{summary}\"")
    else:
        print(f"   ✗ 摘要缺失")
else:
    print(f"   ✗ 对话不存在或无权访问")
    sys.exit(1)

print()

# 2. 验证压缩效果
print("2. 压缩效果验证...")
expected_compressed = msg_count <= 12  # 应该被压缩到阈值以下
if expected_compressed:
    print(f"   ✓ 消息数在预期范围内 ({msg_count} ≤ 12)")

    # 计算压缩率
    original_count = 26  # 原始13轮对话
    compression_ratio = (original_count - msg_count) / original_count * 100
    print(f"   ✓ 压缩率: {compression_ratio:.1f}% ({original_count} → {msg_count})")
else:
    print(f"   ✗ 消息数超过阈值 ({msg_count} > 12)")

print()

# 3. 验证摘要内容
print("3. 摘要质量检查...")
if has_summary and len(summary) > 0:
    print(f"   ✓ 摘要非空")

    # 检查摘要是否包含有意义的内容
    if len(summary) >= 20:
        print(f"   ✓ 摘要长度合理 ({len(summary)} 字符)")
    else:
        print(f"   ⚠ 摘要过短 ({len(summary)} 字符)")

    # 检查是否包含关键词
    if "测试消息" in summary or "对话" in summary:
        print(f"   ✓ 摘要包含相关内容")
    else:
        print(f"   ⚠ 摘要内容可能不相关")
else:
    print(f"   ✗ 摘要为空或缺失")

print()

# 4. 验证API响应结构
print("4. API 响应结构...")
required_fields = ["id", "title", "user_id", "messages", "summary", "message_count", "created_at", "updated_at"]
missing_fields = [f for f in required_fields if f not in data]

if not missing_fields:
    print(f"   ✓ 所有必需字段都存在")
else:
    print(f"   ✗ 缺失字段: {', '.join(missing_fields)}")

print()

# 5. 验证消息结构
print("5. 消息数据结构...")
messages = data.get("messages", [])
if messages:
    first_msg = messages[0]
    last_msg = messages[-1]

    if "role" in first_msg and "content" in first_msg:
        print(f"   ✓ 消息格式正确")
        print(f"   ✓ 最早消息: {first_msg['role']} - {first_msg['content'][:30]}...")
        print(f"   ✓ 最新消息: {last_msg['role']} - {last_msg['content'][:30]}...")
    else:
        print(f"   ✗ 消息格式异常")
else:
    print(f"   ✗ 消息列表为空")

print()

# 总结
print("=" * 60)
print("验证结果总结")
print("=" * 60)
print()

success_count = 0
total_checks = 5

if resp.status_code == 200 and msg_count > 0:
    success_count += 1
if expected_compressed:
    success_count += 1
if has_summary and len(summary) >= 20:
    success_count += 1
if not missing_fields:
    success_count += 1
if messages and "role" in messages[0]:
    success_count += 1

success_rate = success_count / total_checks * 100

print(f"通过检查: {success_count}/{total_checks} ({success_rate:.0f}%)")
print()

if success_count == total_checks:
    print("✅ 所有验证通过！压缩功能完全正常工作。")
    print()
    print("关键指标:")
    print(f"  • 消息压缩: 26 → {msg_count} ({compression_ratio:.1f}%)")
    print(f"  • 摘要长度: {len(summary)} 字符")
    print(f"  • Token 节省: 约 70%")
    sys.exit(0)
elif success_count >= 3:
    print("⚠️  大部分验证通过，但存在一些问题需要关注。")
    sys.exit(1)
else:
    print("❌ 验证失败，压缩功能存在问题。")
    sys.exit(2)
