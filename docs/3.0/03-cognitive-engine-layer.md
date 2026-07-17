# 03 · 认知引擎层（Cognitive Engine Layer）★

> 本层是 SundayOS 3.0 相对通用蓝图的**头号差异化组件**，直接实现你的核心要求：
> **「Sunday should treat AI models as interchangeable cognitive engines, not as its identity.」**

## 3.1 设计目标

1. **模型即引擎**：LLM 是可插拔的推理动力，不承载身份。身份在记忆/人格/目标。
2. **统一抽象**：所有引擎经同一接口暴露，上层代码不感知具体供应商。
3. **动态路由**：按 **复杂度 × 延迟 × 成本 × 隐私 × 可用性** 五维选引擎。
4. **优雅降级**：引擎故障/超时/超预算时按回退链自动降级，不中断心智。
5. **可观测**：每次路由决策可追溯（选了谁、为什么、花了多少）。

## 3.2 分层结构

```
        行动管理器 / 双系统 (L3)
                │  CognitiveRequest(prompt, tags, budget)
                ▼
        ┌───────────────────────┐
        │   CognitiveRouter      │  ① 复杂度分类  ② 预算化选择
        │   (router.py)          │  ③ 回退链      ④ 记账/追踪
        └───────────┬───────────┘
                    │ 选中 EngineProvider
        ┌───────────┼───────────────────────────┐
        ▼           ▼           ▼               ▼
   DeepSeek    OpenAI兼容   Anthropic        Ollama
   Provider    Provider     Provider        Provider
   (deepseek)  (qwen/ling/  (claude)        (本地)
                openai/gpt)
        └───────────┴───────────────────────────┘
                    │ 统一 EngineResponse
                    ▼
        CognitiveResponse(text, usage, engine_id, trace)
```

## 3.3 统一 Provider 接口

所有引擎实现同一抽象基类。接口刻意最小化，只暴露「一次认知」所需。

```python
# app/engines/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

@dataclass
class EngineMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None            # tool 名
    tool_call_id: str | None = None

@dataclass
class EngineCapabilities:
    function_calling: bool = False     # 原生工具调用
    streaming: bool = True
    max_context: int = 32_000          # token 上限
    strong_reasoning: bool = False     # 适合系统2
    local: bool = False                # 端侧/本地（隐私）
    languages: tuple[str, ...] = ("en", "zh")

@dataclass
class EngineResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = "stop"

class EngineProvider(ABC):
    """一个可替换的认知引擎。子类适配具体供应商。"""
    id: str                             # 唯一标识, e.g. "deepseek-chat"
    caps: EngineCapabilities
    # 成本（美元/百万 token），用于预算化路由
    price_in: float = 0.0
    price_out: float = 0.0
    # 观测到的滚动平均延迟（毫秒），由 Router 更新
    avg_latency_ms: float = 800.0

    @abstractmethod
    async def complete(self, messages: list[EngineMessage],
                       temperature: float = 0.7,
                       tools: list[dict] | None = None,
                       max_tokens: int | None = None) -> EngineResponse: ...

    @abstractmethod
    async def stream(self, messages: list[EngineMessage],
                     temperature: float = 0.7) -> AsyncIterator[str]: ...

    async def health(self) -> bool:
        """轻量健康探测，供路由可用性判断。"""
        return True
```

设计要点：
- **能力自描述**：`EngineCapabilities` 让路由器无需硬编码「谁能干什么」。
- **成本内建**：`price_in/out` 直接参与预算化路由打分。
- **延迟自学习**：`avg_latency_ms` 由路由器用滚动平均更新，反映真实网络状况。
- **OpenAI 兼容优先**：DeepSeek/Qwen/Ling/OpenAI/本地 vLLM 都兼容 OpenAI Chat 格式，因此一个 `OpenAICompatibleProvider` 覆盖大多数；Anthropic、Gemini 单独适配。

## 3.4 认知请求与复杂度分类

上层不直接选引擎，而是发出带标签的**认知请求**，由路由器决策。

```python
# app/engines/router.py (节选)
from dataclasses import dataclass
from enum import IntEnum

class Complexity(IntEnum):
    L1_INSTANT = 1     # 意图分类、情感分析、简单问答
    L2_DAILY   = 2     # 日常对话、信息检索、摘要
    L3_DEEP    = 3     # 多步规划、复杂决策、代码生成
    L4_CRITICAL= 4     # 高风险操作、合规审查、安全验证

@dataclass
class CognitiveRequest:
    messages: list[EngineMessage]
    complexity: Complexity | None = None   # None=自动分类
    require_tools: bool = False            # 需原生 function calling
    privacy_sensitive: bool = False        # 强制本地/可信引擎
    prefer_chinese: bool = False           # 中文任务偏好
    latency_budget_ms: int = 3000          # 延迟预算
    max_cost_usd: float | None = None      # 单次成本上限
    temperature: float = 0.7
```

**复杂度自动分类**：当 `complexity is None`，用最便宜的 L1 引擎做一次轻量分类（few-shot 提示，输出 1-4），或用启发式（长度、是否含代码块、是否含工具意图关键词）。这一步本身遵循「便宜优先」。

```python
CLASSIFY_PROMPT = """判断下面用户请求的认知复杂度，只输出一个数字：
1 = 简单（问候/情感/事实问答）
2 = 日常（普通对话/查询/摘要）
3 = 深度（多步推理/写代码/规划）
4 = 关键（涉及删除/支付/权限等高风险操作）
请求：{text}
复杂度："""
```

## 3.5 预算化路由算法

核心：把「预算化自主」（AI Agent Systems, 2026）落到引擎选择上——**便宜引擎浅思考，昂贵引擎按需激活**。

对每个**候选引擎** e（通过硬约束过滤后），计算加权得分，选最优：

```
score(e) = w_cap · Capability(e, req)      # 能力匹配（是否强推理/工具/语言）
         − w_cost · NormCost(e, req)        # 归一化预估成本
         − w_lat  · NormLatency(e)          # 归一化延迟
         + w_avail· Availability(e)         # 近期健康度
```

**硬约束（先过滤，不满足直接剔除）**：
1. `require_tools` → 必须 `caps.function_calling`。
2. `privacy_sensitive` → 必须 `caps.local`（或标记为可信自建）。
3. `complexity == L3/L4` → 必须 `caps.strong_reasoning`。
4. `prefer_chinese` → `"zh" in caps.languages`（加分而非硬约束）。
5. 上下文长度 → `caps.max_context ≥ 预估 tokens`。

**默认权重与复杂度联动**（`max_cost` 为空时）：

| 复杂度 | w_cap | w_cost | w_lat | w_avail | 典型落点 |
|--------|-------|--------|-------|---------|---------|
| L1 即时 | 0.2 | 0.5 | 0.3 | 0.3 | 本地 / DeepSeek |
| L2 日常 | 0.3 | 0.4 | 0.3 | 0.3 | DeepSeek / Qwen |
| L3 深度 | 0.6 | 0.2 | 0.1 | 0.3 | Claude / GPT |
| L4 关键 | 0.8 | 0.05| 0.05| 0.4 | 最强模型 + 验证器 |

即：低复杂度**成本权重高**（省钱），高复杂度**能力权重高**（要对）。这与四角色天然对应——情感/秘书走便宜引擎，编码/学习走强引擎。

`NormCost(e, req) = (price_in·est_in + price_out·est_out) / cost_ceiling`；`est_*` 由消息 token 估算。

## 3.6 回退链（Fallback Chain）

引擎调用失败（超时/限流/5xx/超预算）时，不直接失败，而是沿回退链降级：

```
L4/L3 请求:  Claude Opus → GPT-4o → DeepSeek-Reasoner → DeepSeek-Chat → 本地
L2 请求:     DeepSeek-Chat → Qwen-Plus → 本地 → (降级为 L1 模板回复)
L1 请求:     本地 → DeepSeek-Chat → 规则模板
```

规则：
- 每次降级记录到 trace，`avg_latency_ms` 与可用性据实更新。
- 连续 N 次失败的引擎进入**熔断**（冷却期内不参与路由）。
- 降级到「模板回复」是最后兜底——保证心智永不「死机」，哪怕只能说「我现在思考有点慢，稍等」。

## 3.7 路由决策的可观测性

每次路由产出一条 `RouteTrace`，写入审计日志并可在 Console 的 Cognitive Engine 视图展示：

```json
{
  "request_id": "req_01H...",
  "complexity": 3,
  "candidates": ["claude-opus", "gpt-4o", "deepseek-reasoner"],
  "chosen": "claude-opus",
  "scores": {"claude-opus": 0.71, "gpt-4o": 0.63, "deepseek-reasoner": 0.48},
  "reason": "L3 强推理需求，能力权重主导",
  "fallbacks_used": [],
  "usage": {"prompt_tokens": 1204, "completion_tokens": 380, "cost_usd": 0.021},
  "latency_ms": 412
}
```

## 3.8 已适配的引擎（起步）

| Provider 类 | 引擎 id | 场景 | 强推理 | 工具 | 本地 | 质量 | 主引擎 |
|------------|---------|------|:---:|:---:|:---:|:---:|:---:|
| `OpenAICompatibleProvider` | `doubao-chat` | L1-L2 默认、中文优先 | | | | 0.85 | ✓ |
| `OpenAICompatibleProvider` | `deepseek-chat` | L2 需要工具调用 | | ✓ | | 0.55 | |
| `OpenAICompatibleProvider` | `deepseek-reasoner` | L3 性价比推理 | ✓ | | | 0.65 | |
| `OpenAICompatibleProvider` | `qwen-plus` | 中文日常回退 | | ✓ | | 0.60 | |
| `AnthropicProvider` | `claude-opus` | L3-L4 编码/学习 | ✓ | ✓ | | 0.92 | |
| `OpenAICompatibleProvider` | `gpt-4o` | L3 回退 | ✓ | ✓ | | 0.85 | |
| `OllamaProvider` | `qwen2.5:7b` 等 | 隐私/离线 | | | ✓ | 0.50 | |

**注意事项**（v0.10.9 更新）：
- **豆包（doubao-chat）**：标记为 `primary=True`，质量评分 0.85（最高），普通聊天场景优先选择
- **豆包不支持工具调用**：需要搜索、计算等工具场景自动降级到 DeepSeek-chat
- **豆包无强推理版本**：复杂推理场景（L3_DEEP）使用 DeepSeek-reasoner
- **配置方式**：豆包通过 `CUSTOM_API_KEY` 环境变量加载（而非 `DOUBAO_API_KEY`）
- **预期使用率**：豆包 ~60%，DeepSeek-chat ~10%，DeepSeek-reasoner ~30%

> 新增引擎 = 写一个 Provider 子类 + 在注册表登记能力/价格，**零改上层代码**。这正是「模型即引擎」的工程兑现。

## 3.9 与身份的关系（重申）

引擎层**不持有任何身份状态**。同一段对话，今天路由到 DeepSeek、明天路由到 Claude，用户感知到的仍是同一个 Sunday——因为：
- 人格来自 [06](06-personality-and-empathy.md) 的 Persona 锚定（存于记忆，注入每次 prompt）。
- 记忆来自 [04](04-memory-system.md)（跨引擎共享）。
- 目标来自 Planner 与 Goal Manager（跨引擎共享）。

引擎只是「这一次用哪台发动机」。车还是那辆车，司机还是那个司机。

