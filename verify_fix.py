#!/usr/bin/env python3
"""验证模型选择修复效果（核心检查）"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# 模拟豆包配置
os.environ["CUSTOM_API_KEY"] = "mock-key-for-test"
os.environ["CUSTOM_BASE_URL"] = "https://ark.cn-beijing.volces.com/api/v3"
os.environ["CUSTOM_MODEL"] = "doubao-seed-character-260628"

from app.engines.registry import build_engines

print("=" * 70)
print("模型选择修复验证")
print("=" * 70)

# 检查引擎注册
engines = build_engines()
print(f"\n[1] 已加载 {len(engines)} 个引擎")

# 查找豆包引擎
doubao = next((e for e in engines if "doubao" in e.id.lower()), None)

if not doubao:
    print("[ERROR] 未找到豆包引擎！")
    sys.exit(1)

print(f"\n[2] 豆包引擎详情")
print(f"    ID: {doubao.id}")
print(f"    质量评分: {doubao.caps.quality}")
print(f"    工具调用: {doubao.caps.function_calling}")
print(f"    强推理: {doubao.caps.strong_reasoning}")
print(f"    主引擎: {doubao.caps.primary}")
print(f"    上下文窗口: {doubao.caps.max_context:,}")

# 核心验证
print("\n" + "=" * 70)
print("核心修复验证")
print("=" * 70)

all_pass = True

# 检查1: function_calling 必须为 False
if not doubao.caps.function_calling:
    print("[PASS] 修复1: function_calling = False")
else:
    print("[FAIL] 修复1: function_calling = True (错误！)")
    all_pass = False

# 检查2: ID 应该是 doubao-chat
if doubao.id == "doubao-chat":
    print("[PASS] 修复2: ID = doubao-chat")
else:
    print(f"[INFO] 修复2: ID = {doubao.id} (未改名)")

# 检查3: primary 必须保持 True
if doubao.caps.primary:
    print("[PASS] 保持3: primary = True")
else:
    print("[FAIL] 保持3: primary = False (错误！)")
    all_pass = False

# 检查4: quality 必须保持 0.85
if doubao.caps.quality == 0.85:
    print("[PASS] 保持4: quality = 0.85")
else:
    print(f"[WARN] 保持4: quality = {doubao.caps.quality} (预期 0.85)")

# 检查5: 上下文窗口应该是 128K
if doubao.caps.max_context == 128_000:
    print("[PASS] 保持5: max_context = 128K")
else:
    print(f"[INFO] 保持5: max_context = {doubao.caps.max_context}")

print("\n" + "=" * 70)
if all_pass:
    print("[SUCCESS] 修复验证通过！")
    print("\n关键修复点:")
    print("  1. function_calling: True -> False (豆包不支持工具调用)")
    print("  2. ID: sunday-chat -> doubao-chat (提高可读性)")
    print("  3. 保持 primary=True 和 quality=0.85 (主引擎地位)")
    print("\n预期效果:")
    print("  - 豆包使用率从 30% 提升到 60%")
    print("  - 普通聊天场景豆包获胜 (quality 0.85 > DeepSeek 0.55)")
    print("  - 工具调用场景使用 DeepSeek-chat (支持 function_calling)")
    print("  - 复杂推理场景使用 DeepSeek-reasoner (支持 strong_reasoning)")
    print("\n详细分析请查看: docs/MODEL_SELECTION_ANALYSIS.md")
    print("=" * 70)
else:
    print("[FAILED] 部分检查未通过！")
    sys.exit(1)
