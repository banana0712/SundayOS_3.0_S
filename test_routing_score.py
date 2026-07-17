#!/usr/bin/env python3
"""测试路由评分计算"""

# L2_DAILY 权重
w_qual, w_cap, w_cost, w_lat, w_avail = 0.40, 0.20, 0.10, 0.15, 0.30

# 豆包配置
doubao_quality = 0.85
doubao_primary = True
doubao_function_calling = False
doubao_strong_reasoning = False
doubao_price_in = 0
doubao_price_out = 0
doubao_latency = 800

# DeepSeek配置
deepseek_quality = 0.55
deepseek_primary = False
deepseek_function_calling = True
deepseek_strong_reasoning = False
deepseek_price_in = 0.27
deepseek_price_out = 1.1
deepseek_latency = 800

# 计算 capability score
def calc_capability(quality, strong_reasoning, function_calling, primary, prefer_chinese=True):
    cap = 0.0
    cap += quality * 0.5  # Base quality
    if strong_reasoning:
        cap += 0.3
    if function_calling:
        cap += 0.1
    if prefer_chinese:  # 假设是中文请求
        cap += 0.1
    if primary:
        cap += 0.15  # Primary bonus
    return min(cap, 1.0)

# 豆包 capability
doubao_cap = calc_capability(doubao_quality, doubao_strong_reasoning, doubao_function_calling, doubao_primary)
print(f"豆包 capability: {doubao_cap:.4f}")
print(f"  - Base quality (0.85 * 0.5) = {doubao_quality * 0.5:.4f}")
print(f"  - Strong reasoning = 0")
print(f"  - Function calling = 0")
print(f"  - Chinese preference = 0.1")
print(f"  - Primary bonus = 0.15")

# DeepSeek capability
deepseek_cap = calc_capability(deepseek_quality, deepseek_strong_reasoning, deepseek_function_calling, deepseek_primary)
print(f"\nDeepSeek capability: {deepseek_cap:.4f}")
print(f"  - Base quality (0.55 * 0.5) = {deepseek_quality * 0.5:.4f}")
print(f"  - Strong reasoning = 0")
print(f"  - Function calling = 0.1")
print(f"  - Chinese preference = 0.1")
print(f"  - Primary bonus = 0")

# 假设成本和延迟归一化都是 0.5（相似）
cost_norm_doubao = 0.0  # 免费
cost_norm_deepseek = 1.0  # 最贵
lat_norm = 0.5  # 延迟相同

# 最终评分
doubao_score = (w_qual * doubao_quality) + (w_cap * doubao_cap) - (w_cost * cost_norm_doubao) - (w_lat * lat_norm) + (w_avail * 1.0)
deepseek_score = (w_qual * deepseek_quality) + (w_cap * deepseek_cap) - (w_cost * cost_norm_deepseek) - (w_lat * lat_norm) + (w_avail * 1.0)

print(f"\n=== L2_DAILY 权重 ===")
print(f"质量={w_qual}, 能力={w_cap}, 成本={w_cost}, 延迟={w_lat}, 可用={w_avail}")

print(f"\n=== 最终评分 ===")
print(f"豆包: {doubao_score:.4f}")
print(f"  = (0.40 * {doubao_quality}) + (0.20 * {doubao_cap:.4f}) - (0.10 * {cost_norm_doubao}) - (0.15 * {lat_norm}) + (0.30 * 1.0)")
print(f"  = {w_qual * doubao_quality:.4f} + {w_cap * doubao_cap:.4f} - {w_cost * cost_norm_doubao:.4f} - {w_lat * lat_norm:.4f} + {w_avail * 1.0:.4f}")

print(f"\nDeepSeek: {deepseek_score:.4f}")
print(f"  = (0.40 * {deepseek_quality}) + (0.20 * {deepseek_cap:.4f}) - (0.10 * {cost_norm_deepseek}) - (0.15 * {lat_norm}) + (0.30 * 1.0)")
print(f"  = {w_qual * deepseek_quality:.4f} + {w_cap * deepseek_cap:.4f} - {w_cost * cost_norm_deepseek:.4f} - {w_lat * lat_norm:.4f} + {w_avail * 1.0:.4f}")

print(f"\n=== 结果 ===")
if doubao_score > deepseek_score:
    print(f"✓ 豆包获胜（{doubao_score:.4f} > {deepseek_score:.4f}，差距 {doubao_score - deepseek_score:.4f}）")
else:
    print(f"✗ DeepSeek获胜（{deepseek_score:.4f} > {doubao_score:.4f}，差距 {deepseek_score - doubao_score:.4f}）")
