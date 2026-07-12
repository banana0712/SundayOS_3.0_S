# 02 · 系统架构

## 2.1 六层架构总览

SundayOS 3.0 采用六层分层架构，自底向上责任递增，层间通过标准化接口通信。**注意本版与通用蓝图的关键差异：认知引擎层被提升为独立的 L1.5，横跨所有推理层 —— 因为「引擎可替换」是本设计的一等原则。**

```
┌──────────────────────────────────────────────────────────────┐
│  L6  安全与治理层   六层护栏 · 预算化自主 · 隐私 · 审计         │
├──────────────────────────────────────────────────────────────┤
│  L5  应用与技能层   技能注册中心 · 工具路由 · 行动管理器        │
│                     四角色配置（学习/编码/秘书/伴侣）          │
├──────────────────────────────────────────────────────────────┤
│  L4  交互与人格层   共情计算(CQU/UU/IRG) · 人格锚定 · 对话管理  │
├──────────────────────────────────────────────────────────────┤
│  L3  认知引擎层     双系统(Talker+Reasoner) · ReAct · 规划器   │
│                     信念状态 · 反思引擎                        │
├──────────────────────────────────────────────────────────────┤
│ L1.5 认知引擎抽象   ★ 统一 Provider 接口 · 动态路由器          │
│      (Cognitive     复杂度分类 · 预算化选择 · 回退链           │
│       Engine Layer) DeepSeek│Qwen│Claude│GPT│Gemini│Ollama    │
├──────────────────────────────────────────────────────────────┤
│  L2  数据与记忆层   Memory Stream · Reflection · Experience    │
│                     情景/语义/程序/工作 记忆                   │
├──────────────────────────────────────────────────────────────┤
│  L1  基础设施层     向量库 · 结构化库 · 缓存 · 消息队列 · 网关  │
│                     GitHub（source of truth）                 │
└──────────────────────────────────────────────────────────────┘
```

> 「Agent Transformer」形式化（AI Agent Systems, 2026）：`A = (πθ, M, T, V, E)`。SundayOS 的映射：**πθ** = L1.5 路由到的引擎；**M** = L2 记忆；**T** = L5 工具；**V** = L6 验证器/护栏；**E** = 用户 + 设备 + 外部服务环境。

## 2.2 各层职责

| 层 | 名称 | 核心职责 | 关键组件 | 参考实现 |
|----|------|---------|---------|---------|
| L1 | 基础设施 | 计算、存储、网络、模型服务、真源 | 向量库、SQL、缓存、MQ、API 网关、GitHub | `backend/`(SQLite+Chroma 起步) |
| L1.5 | **认知引擎抽象** | 统一模型接口 + 动态路由 | Provider 接口、Router、复杂度分类器 | `app/engines/` |
| L2 | 数据与记忆 | 记忆流、反思、体验抽象 | MemoryStore、ReflectionEngine、ExperienceAbstractor | `app/memory/` |
| L3 | 认知引擎 | 推理、规划、决策 | Talker、Reasoner、ReAct、BeliefState、Planner | `app/cognition/` |
| L4 | 交互与人格 | 对话管理、情感、人格 | EmpatheticModule、PersonaManager、DialogueManager | `app/persona/` |
| L5 | 应用与技能 | 任务执行、工具、内容生成 | SkillRegistry、ToolRouter、ActionManager | `app/skills/`(Phase2) |
| L6 | 安全与治理 | 护栏、隐私、审计、合规 | GuardrailPipeline、PolicyEngine、AuditLogger | `app/guardrails/` |

## 2.3 认知架构核心：双系统 + 全局工作空间

融合三项理论：Kahneman 双系统（Talker-Reasoner 工程化）、Baars 全局工作空间理论、认知架构蓝图的模块组织。

```
              SundayOS Conscious Workspace (全局工作空间)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Emotion Module        Planner Module       Attention Module
    (情感计算)            (规划引擎)            (注意力管理)
        │                     │                     │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
 Episodic  Semantic  Procedural Working    Focus    Salience
  Memory    Memory     Memory    Memory    Manager  Detector
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                        Reflection Engine (反思引擎)
                              │
                        Personality (人格锚定层)
                              │
                        Action Manager (行动管理器)
                              │
              Cognitive Engine Layer (L1.5 · 引擎路由)
                              │
        DeepSeek │ Qwen │ Claude │ GPT │ Gemini │ Ollama
```

**与蓝图的差异**：底部不再是「LLM + Tools」的固定绑定，而是**认知引擎层**——行动管理器发出的是「认知请求」（含复杂度/风险/延迟/隐私标签），由路由器决定用哪个引擎。

## 2.4 标准执行循环（数据流）

遵循 ReAct 循环范式，增加双系统切换、引擎路由与记忆管理维度：

```
用户输入 (任意端: iPhone/桌面/云)
   │
   ▼
[L6] 输入护栏流水线 (长度→规则→moderation→相关性+安全) ──✗──> 拒绝
   │ ✓
   ▼
[L3] 系统1(Talker) 快速解析意图 + 情感  ← [L2] 检索用户画像摘要+近期记忆
   │
   ├─ 简单/情感任务 ────────────────────────────┐
   │                                            │
   ▼ 复杂/高风险任务                             │
[L3] 激活系统2(Reasoner)                         │
   │  ReAct 循环: Thought → Action → Observation │
   │      │                                      │
   │      ▼ 每个 Action                          │
   │  [L1.5] 引擎路由 (复杂度×成本×延迟×隐私)     │
   │  [L6] 验证器 V 检查 Action 安全性 ──✗──> HITL│
   │  [L5] 执行工具调用                          │
   │  [L3] 更新信念状态 (Belief)                 │
   │      └──── 循环直至 finish 或 max_steps ────┤
   │                                            │
   ▼                                            ▼
[L4] 人格 + 共情包装响应 ◄───────────────────────┘
   │
   ▼
[L6] 输出护栏 (PII 过滤 + 品牌对齐)
   │
   ▼
返回响应 → 异步: 写入记忆流 + 触发反思(达阈值时) + 更新画像
```

**关键增强点**（相对纯 ReAct）：
1. **双系统切换**：系统1 判断是否需要系统2（见 [05](05-dual-process-cognition.md) §切换判据）。
2. **引擎路由**：每次认知请求动态选引擎（见 [03](03-cognitive-engine-layer.md)）。
3. **验证器前置**：Action 执行前经 V 校验，高风险触发 HITL（见 [08](08-security-and-autonomy.md)）。
4. **异步记忆闭环**：响应后异步写记忆、反思、更新画像，不阻塞用户。

## 2.5 组件交互原则

- **记忆总线**：系统1、系统2、反思引擎、人格层都通过统一记忆接口读写，实现双系统协调。
- **引擎无状态**：认知引擎层无状态，可水平扩展；所有状态在记忆层与信念状态中。
- **护栏并发**：护栏与主推理**乐观并发**执行，违规抛 tripwire 异常（借鉴 OpenAI Agents SDK）。
- **降级优雅**：引擎不可用时按回退链降级（强→中→弱→本地），而非直接失败。
- **真源同步**：人格配置、技能定义、结构化偏好以 GitHub 为真源，运行时加载。

## 2.6 与 1.0 的演进关系

1.0 已有：FastAPI + 四层记忆（Redis/PG/Chroma/程序）+ 多供应商 OpenAI 兼容 SDK + iPhone Shortcuts。3.0 的演进：

- 四层记忆 → **三层递进记忆**（Storage→Reflection→Experience），四类记忆（情景/语义/程序/工作）正交存在。
- 多供应商 SDK → **认知引擎层**（抽象 + 路由 + 预算化 + 回退），从「能切换」升级到「自动选最优」。
- 单模型对话 → **双系统认知**（Talker 常在线 + Reasoner 按需）。
- 无护栏 → **六层护栏 + 预算化自主**。
- 起步存储从 Redis/PG 简化为 **SQLite + ChromaDB 零配置**，生产选型见 [10](10-model-routing-and-infra.md)。
