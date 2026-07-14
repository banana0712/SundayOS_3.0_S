# ADR-011 · 质量优先的多引擎路由策略

**日期**: 2026-07-15
**状态**: Accepted
**影响范围**: `app/engines/router.py`, `app/engines/base.py`, `app/engines/registry.py`

---

## 背景

v0.7 的路由权重表是以**成本**为主要决策维度的：

| L2 日常对话 | w_cap 0.3 | w_cost 0.4 | w_lat 0.3 | w_avail 0.3 |

这意味着**免费引擎永远排在付费引擎前面**，即使付费引擎的对话质量显著更好。

在部署豆包（`doubao-seed-character-260628`）后，实际情况验证了这个问题：
- 豆包中文对话质量明显优于 DeepSeek
- 但 88api 的 `gpt-4o` 不通时，系统自动回退到 DeepSeek
- 然而权重表中 40% 的成本权重意味着「被选中」不等于「排序第一」

用户反馈明确指出：**"陪伴和聊天不应该以成本作为最优解"**。

---

## 决策

将路由策略从**成本优先**改为**质量优先**（Quality-First Routing）。

### 新权重表

| 复杂度 | w_quality | w_capability | w_cost | w_latency | w_availability |
|--------|-----------|-------------|--------|-----------|----------------|
| L1 即时 | 0.25 | 0.15 | 0.30 | 0.20 | 0.30 |
| **L2 日常** | **0.40** | **0.20** | **0.10** | **0.15** | **0.30** |
| L3 深度 | 0.35 | 0.35 | 0.05 | 0.10 | 0.30 |
| L4 关键 | 0.50 | 0.30 | 0.00 | 0.05 | 0.35 |

关键变化：**L2 日常对话的成本权重从 40% 降到 10%**，质量权重新增为 40%。

### 引擎质量元数据

每个引擎通过 `EngineCapabilities` 新增两个字段：

1. **`quality`**（0.0-1.0）—— 引擎的对话质量评分
   - 由用户主观评估或人工标注，非自动计算
   - 默认 0.5；豆包/Claude/GPT 等级别可设为 0.85+
2. **`primary`**（bool）—— 是否用户的指定主力引擎
   - primary 引擎在评分中获得 0.15 加分
   - 始终排在 fallback 链最前面

### 评分公式

```
score(e) = w_quality · quality          // 用户感知质量（纯主观）
         + w_capability · capability    // 推理/工具/语言匹配
         − w_cost · norm_cost           // 归一化成本（软约束）
         − w_lat · norm_latency         // 归一化延迟（软约束）
         + w_availability · 1.0         // 健康度
```

其中 `capability` 包含：quality 贡献 0.5 + 推理能力 0.3 + 工具调用 0.1 + 中文支持 0.1 + primary 加分 0.15，总和不超过 1.0。

---

## 理论依据

2025-2026 年的多模型路由研究（FutureAGI、Microsoft Foundry、Redis）一致指出：

1. **Quality-Aware 路由**是 2026 年生产环境的标准模式——按任务适配度智能分发，而非单一维度优化。
2. **Cascade Routing** 的核心思想：先用最合适的模型，失败了才降级——成本是约束条件，不是目标函数。
3. 个人 AI 伴侣系统（如 SundayOS）的路由优先级应该是：**人格匹配 > 对话质量 > 延迟 > 成本**。

---

## 后果

### 正面
- ✅ 用户指定的 `primary` 引擎（豆包）在每次请求中被优先选中
- ✅ 质量高的引擎即使有成本也会排在前面（现实：豆包免费、DeepSeek 付费，成本不影响选择）
- ✅ 仍然保留完整的 fallback 链——豆包故障时自动降级到 DeepSeek
- ✅ 路由决策完全可追溯：Console `/api/debug/routing` 端点展示评分明细

### 负面
- ⚠️ `quality` 评分目前是人工设定，需要用户反馈驱动调优
- ⚠️ 如果 primary 引擎变慢，延迟权重（15%）不足以触发降级——需要引入 CircuitBreaker 的延迟边界判定（后续 ADR）

### 风险评估
- **低风险**：改动限制在路由层的打分逻辑，不影响上游 API 契约
- **可逆性**：仅需修改 WEIGHTS 表即可回滚到成本优先模式

---

## 参考

- FutureAGI (2026). *Evaluating LLM Routing Policies in 2026* — 质量感知路由的五轴评估框架
- Microsoft Foundry Agent Lab. *MODEL-ROUTER.md* — 单行部署的质量/成本/均衡模式
- Redis (2026). *LLM Router Architecture: Best Practices for 2026* — 级联路由 + 影子评估
- arXiv:2606.17949. *RouteBalance: Fused Model Routing and Load Balancing*

---

## 变更状态

- [x] `EngineCapabilities` 新增 `quality` 和 `primary` 字段
- [x] `WEIGHTS` 表重写为质量优先
- [x] `_score_all()` 支持 5 元组权重
- [x] `_capability()` 包含 quality + primary 加分
- [x] engine registry 给每个引擎分配 quality 分数
- [x] `/api/debug/routing` 端点显示 quality/primary
- [x] 启动日志包含每引擎的 quality/primary
