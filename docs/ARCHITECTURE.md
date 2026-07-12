# ARCHITECTURE.md · Sunday OS 系统架构（权威）

> 顶层架构真相。概念与边界在此定义；**实现级细节**在 [3.0/](3.0/) 展开，本文件只做索引。决策理由见 [adr/](adr/)。

**版本** 1.0 · **最后更新** 2026-07-13 · **负责** AI Software Architect

---

## 1. 架构信条

见 [SUNDAY_CONTEXT.md §1](../SUNDAY_CONTEXT.md) 的七条理念。对架构最关键的两条：

- **身份与模型解耦**：身份在 Memory/Personality/Goals/Planning/Cognitive Architecture，不在 LLM。
- **渐进式演进**：复杂度必须与已验证价值成正比（先单 Agent + 骨架）。

形式化锚点（AI Agent Systems, 2026）：`A = (πθ, M, T, V, E)`——πθ=路由到的引擎，M=记忆，T=工具，V=验证器/护栏，E=环境。

## 2. 六层 + 引擎抽象层

```
┌────────────────────────────────────────────────────────────┐
│ L6 安全治理   六层护栏 · 预算化自主 · 隐私 · 审计            │
│ L5 应用技能   技能注册 · 工具路由 · 行动管理 · 四角色配置    │
│ L4 交互人格   共情计算(CQU/UU/IRG) · 人格锚定 · 对话管理     │
│ L3 认知引擎   双系统(Talker+Reasoner) · ReAct · 规划 · 反思  │
│ L1.5 引擎抽象 ★ 统一 Provider 接口 · 动态路由               │
│              DeepSeek│Qwen│Claude│GPT│Gemini│Ollama         │
│ L2 数据记忆   Storage → Reflection → Experience 三层递进     │
│ L1 基础设施   向量库 · 结构化库 · 缓存 · GitHub(真源)        │
└────────────────────────────────────────────────────────────┘
```

| 层 | 职责 | 关键组件 | 细节文档 | 代码 |
|----|------|---------|---------|------|
| L1 | 计算/存储/真源 | 向量库、SQL、缓存、GitHub | [3.0/10](3.0/10-model-routing-and-infra.md) | `backend/`(SQLite+Chroma 起步) |
| L1.5 | 模型抽象 + 路由 | Provider、Router、复杂度分类 | [3.0/03](3.0/03-cognitive-engine-layer.md) | `backend/app/engines/` |
| L2 | 记忆 | MemoryStore、Reflection、Experience | [3.0/04](3.0/04-memory-system.md) | `backend/app/memory/` |
| L3 | 推理/规划 | Talker、Reasoner、ReAct、Belief | [3.0/05](3.0/05-dual-process-cognition.md) | `backend/app/cognition/` |
| L4 | 情感/人格 | Empathy、Persona、Dialogue | [3.0/06](3.0/06-personality-and-empathy.md) | `backend/app/persona/`(待建) |
| L5 | 技能/工具 | SkillRegistry、ToolRouter | [3.0/07](3.0/07-skills-and-tools.md) | `backend/app/skills/`(待建) |
| L6 | 安全 | GuardrailPipeline、Policy、Audit | [3.0/08](3.0/08-security-and-autonomy.md) | `backend/app/guardrails/` |

## 3. 认知架构核心：双系统 + 全局工作空间

```
        Conscious Workspace (全局工作空间)
                     │
   ┌─────────────────┼─────────────────┐
 Emotion          Planner          Attention
   │                 │                 │
 Episodic/Semantic/Procedural/Working Memory
   └─────────────────┼─────────────────┘
              Reflection Engine
                     │
                Personality (人格锚定)
                     │
              Action Manager
                     │
        Cognitive Engine Layer (L1.5 路由)
```

- **系统1 Talker**：轻量、常在线，处理日常/情感/意图，走便宜引擎。
- **系统2 Reasoner**：强模型、按需激活，ReAct 循环 + 工具 + 信念状态，走强引擎。
- 二者经**共享记忆总线**协调；切换判据见 [3.0/05 §5.6](3.0/05-dual-process-cognition.md)。

## 4. 标准执行循环（数据流）

```
用户输入(任意端)
 → [L6] 输入护栏 ──✗→ 拒绝
 → [L3] 系统1 意图+情感   ← [L2] 检索画像+近期
 → needs_reasoner?
     否 → 系统1 直接响应
     是 → 系统2 ReAct: Thought→[L1.5 路由选引擎]→Action→[L6 验证器 V]→执行→更新 Belief …→finish
 → [L4] 人格/共情包装
 → [L6] 输出护栏(PII)
 → 返回 → 异步写记忆 + 触发反思
```

四点增强（相对纯 ReAct）：双系统切换、引擎动态路由、验证器前置、异步记忆闭环。详见 [3.0/02 §2.4](3.0/02-system-architecture.md)。

## 5. 认知引擎层（差异化核心）

模型即可替换引擎。`EngineProvider` 抽象自描述能力/价格；`CognitiveRouter` 按 **复杂度×成本×延迟×隐私×可用性** 打分选优（成本/延迟在候选集内 min-max 归一化），带回退链 + 熔断。新增引擎 = 子类 + registry 登记，零改上层。完整规范 [3.0/03](3.0/03-cognitive-engine-layer.md)，决策 [adr/008](adr/008-cognitive-engine-layer.md)。

## 6. 记忆系统（身份基础）

三层递进：**Storage**（原始轨迹，检索 = α·recency+β·importance+γ·relevance）→ **Reflection**（纠错+洞察）→ **Experience**（跨轨迹抽象）。四类记忆（情景/语义/程序/工作）正交存在。有效重要性 30 天半衰期。完整规范 [3.0/04](3.0/04-memory-system.md)，决策 [adr/002](adr/002-three-tier-memory.md)。

## 7. 部署形态

- **起步**（当前）：单机 FastAPI + SQLite + ChromaDB，零外部服务（[adr/010](adr/010-local-first-storage.md)）。
- **生产**（路线）：K8s + Postgres + Redis + Milvus + 可观测栈，见 [3.0/10](3.0/10-model-routing-and-infra.md)。
- **多端**：iPhone(Shortcuts/App Intents) + 桌面 + 云，心智状态以云 + GitHub 为中心（[3.0/09](3.0/09-api-and-integration.md)）。

## 8. 与 1.0 的演进

四层记忆 → 三层递进；多供应商 SDK → 认知引擎层（能切换 → 自动选优）；单模型 → 双系统；无护栏 → 六层护栏 + 预算化自主。详见 [3.0/02 §2.6](3.0/02-system-architecture.md)。

## 9. 关联决策

[adr/](adr/) 全部；架构相关重点：001 双系统、002 三层记忆、003 ReAct、004 渐进演进、005 纵深护栏、006 端云混合、008 引擎层、009 GitHub 真源、010 本地优先。
