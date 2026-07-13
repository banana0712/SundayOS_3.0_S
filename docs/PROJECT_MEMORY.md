# PROJECT_MEMORY.md · Sunday OS 项目记忆

> 记录所有已完成的重大设计决策、技术选型和架构选择。这不是 ADR 的替代——ADR 记录「决策与理由」的过程，本文档是你快速查阅「我们做了什么决定」的索引。每个决策引用其 ADR 正文。

**版本** 1.0 · **最后更新** 2026-07-13

---

## 1. 架构决策总览

| # | 决策 | 一句话 | ADR |
|---|------|--------|-----|
| 1 | 双系统认知架构 | Talker (快) + Reasoner (慢)，而非单模型全量推理 | [001](3.0/adr/001-dual-process.md) |
| 2 | 三层递进记忆 | Storage → Reflection → Experience 递进共存 | [002](3.0/adr/002-three-tier-memory.md) |
| 3 | ReAct 执行单元 | Thought → Action → Observation 循环，幻觉率 6% vs CoT 14% | [003](3.0/adr/003-react-loop.md) |
| 4 | 渐进式演进 | 先单 Agent 验证价值，再按需演化（复杂度与价值成正比） | [004](3.0/adr/004-progressive-arch.md) |
| 5 | 六层纵深护栏 | L1-L6 多层防御，单层不可靠 | [005](3.0/adr/005-defense-in-depth.md) |
| 6 | 本地+云端混合 | iPhone 本地轻量模型 + 云端强模型（隐私×延迟平衡） | [006](3.0/adr/006-hybrid-mobile.md) |
| 7 | CPS 核心指标 | 以 Conversation-turns Per Session 衡量参与深度 | [007](3.0/adr/007-cps-metric.md) |
| 8 | ★ 认知引擎抽象层 | 统一 Provider 接口 + 五维动态路由（模型即引擎，可替换） | [008](3.0/adr/008-cognitive-engine-layer.md) |
| 9 | GitHub 真源 | 人格/技能/偏好版本化在 Git，运行时加载 | [009](3.0/adr/009-github-source-of-truth.md) |
| 10 | 本地零配置起步 | SQLite+ChromaDB 零外部服务起步，生产栈文档化 | [010](3.0/adr/010-local-first-storage.md) |
| 11 | 文档驱动上下文体系 | 三层文档体系 + 活文档纪律，聊天历史不可靠 | [011](adr/011-context-system.md) |

---

## 2. 关键设计选择及其影响

### 2.1 认知引擎抽象层（ADR-008）——头号决策

**我们做了什么**：
- 创建独立的 L1.5 层，所有 LLM 经统一 `EngineProvider` 接口接入
- 路由器按 5 个维度打分选最优引擎：**复杂度 × 成本 × 延迟 × 隐私 × 可用性**
- 新增引擎 = 写 Provider 子类 + 在 registry 登记，**零改上层代码**

**已落地的代码**：
- `backend/app/engines/base.py`：`EngineProvider` 抽象类 + `EngineMessage`/`EngineResponse`/`Complexity`
- `backend/app/engines/providers.py`：4 个具体引擎（OpenAICompatible / Anthropic / Mock）
- `backend/app/engines/registry.py`：`build_engines()` + `env()` 鲁棒读取
- `backend/app/engines/router.py`：`CognitiveRouter` 含候选过滤 → 多维评分 → 回退链 → 熔断器

**为什么这样做**：
- 直接兑现「身份≠模型」的核心理念
- 回退链保证 Sunday "永不死机"（优雅降级）
- 预算化自主：低风险便宜引擎浅思考，高风险强引擎深验证
- 四角色自然映射到不同引擎偏好（秘书=便宜，编码=强模型）

### 2.2 三层递进记忆（ADR-002）

**我们做了什么**：
- 定义三级：L1 Storage（原始轨迹）→ L2 Reflection（纠错+洞察）→ L3 Experience（跨轨迹抽象）
- L1 检索公式：`score = α·recency + β·importance + γ·relevance`
- 三个分量各自 min-max 归一化后再加权，确保跨维度可比
- 重要性 30 天半衰期
- 5 种记忆类型：EPISODIC / SEMANTIC / PROCEDURAL / REFLECTION / EXPERIENCE

**已落地的代码**：
- `backend/app/memory/schema.py`：`MemoryNode` + `effective_importance()` 衰减公式
- `backend/app/memory/store.py`：`MemoryStore` + 复合评分 `retrieve()`
- `backend/app/memory/embedding.py`：可插拔 embedder（默认 hash embedding）

**当前限制**：
- 仅 L1 Storage 已实现，L2 Reflection 和 L3 Experience 未实现
- 所有记忆在进程内存（重启即失）——持久化是最高优先任务

### 2.3 双系统认知（ADR-001）

**我们做了什么**：
- 系统1 (Talker)：轻量常在线，处理日常/情感对话
- 系统2 (Reasoner)：强模型按需激活，处理复杂/多步/高风险任务
- 切换判据：意图词 + 工具关键词 + 多步连接词 + 风险等级 + 未解决障碍

**已落地的代码**：
- `backend/app/cognition/dispatch.py`：`needs_reasoner()` / `risk_level()` / `estimated_steps()`
- `backend/app/cognition/belief.py`：`BeliefState` 数据模型（目标/任务/障碍/情绪）

**当前限制**：
- Reasoner 激活后只是路由到强引擎直接回答，**没有 ReAct 循环**
- BeliefState 每次对话临时新建，未持久化

### 2.4 六层纵深护栏（ADR-005）

**我们做了什么**：
- L2-L4 规则层（长度/注入/越狱模式匹配）+ L3 PII 脱敏 + L5 工具风险分级 + L6 HITL
- 检测即抛 `GuardrailTripwire`，不尝试修复
- 工具风险预定义映射（low/medium/high），high 级需确认

**已落地的代码**：
- `backend/app/guardrails/pipeline.py`：`check_input()` / `redact_pii()` / `tool_risk()` / `requires_confirmation()`

**当前限制**：
- LLM 安全分类器（语义级 moderation）未实现，当前只有规则匹配

### 2.5 本地零配置存储（ADR-010）

**我们做了什么**：
- 选 SQLite（结构化+审计）+ ChromaDB（向量）作为起步存储
- 生产栈（Postgres/Redis/Milvus/K8s）作为文档化演进路径
- 存储经抽象接口访问，起步→生产切换不改上层

**当前限制**：
- SQLite 和 ChromaDB **尚未接入**——当前只用内存 dict

### 2.6 文档驱动的上下文体系（ADR-011）

**我们做了什么**：
- 建立三层文档体系：上下文层（SUNDAY_CONTEXT/CLAUDE/AGENTS）→ 权威层（docs/）→ 实现层（docs/3.0/）
- 设立 AI Software Architect 长期角色守护体系
- 活文档纪律：架构/决策/进度变化即时同步

**本次会话建立的工程文档**（2026-07-13）：
- `docs/AI_CONTEXT.md` —— 唯一入口
- `docs/ARCHITECTURE.md` —— 基于实际代码的系统架构
- `docs/CURRENT_STATE.md` —— 诚实进度报告
- `docs/ROADMAP.md` —— 路线图
- `docs/DESIGN_SYSTEM.md` —— 设计规范与改进建议
- `docs/PROJECT_MEMORY.md` —— 本文档

### 2.7 Runtime 骨骼固化（无 ADR 编号，工程决策）

**我们做了什么**：
- 新建 `app/runtime.py`：将所有子系统（引擎、路由、记忆、对话、工具、技能）收敛到一个带类型的 `Runtime` dataclass 中
- 从 `main.py` 的 10 个分散模块级变量收敛为一条 `runtime = Runtime(...)`
- 内建 LINKAGE 图（ASCII 依赖图 + 6 条数据流描述），每次修改模块时必须更新

**已落地的代码**：
- `backend/app/runtime.py`：`Runtime` dataclass（60 行） + LINKAGE graph（80 行文档）

**为什么这样做**：
- 功能增多后模块之间的联动关系必须可追溯、可审计
- 新增子系统 = 在 Runtime 加一个字段 + 在 LINKAGE 加一条记录
- 交接项目 → 看 Runtime 就知道有什么组件 → 看 LINKAGE 就知道它们怎么交互

### 2.8 ContextBuilder — 话题感知跨会话上下文

**我们做了什么**：
- 替换单纯的 `MEMORY.retrieve(k=6)` 为结构化上下文组装流水线
- 话题提取（廉价 LLM）→ 跨会话话题网络检索 → 时间锚定排序 → 分类组装
- 上下文上限 ~3000 tokens（依据 Engram 论文：9.6K 精选 > 79K 全量）

**已落地的代码**：
- `backend/app/cognition/context_builder.py`：`build_context()` + `AssembledContext`
- 上下文分四段注入：`[用户画像]` `[当前状态]` `[相关洞察]` `[相关记忆]`

**为什么这样做**：
- 论文数据：精简检索的 9.6K token 上下文比全量 79K token 精度高 10.4 个百分点
- 对话之间不再孤立——"三天前聊的跑步"和"刚才问的伤病"自动关联到同一话题
- 时间锚定让 LLM 知道「这是三个月前说的」vs「这是刚才说的」

---

## 3. 技术选型记录

| 决策 | 选择 | 替代方案 | 理由 | 发生时间 |
|------|------|---------|------|---------|
| 后端框架 | FastAPI | Flask / Django | 异步原生、类型安全、自动 OpenAPI、社区活跃 | Phase 1 开始时 |
| 前端框架 | Next.js 15 (App Router) | Vite+React / Remix | 全栈能力、SSR/SSG 可选、React 19 支持 | Phase 1 开始时 |
| 样式方案 | Tailwind CSS 3.4 | CSS Modules / styled-components | 与 Design Token 天然对齐、零运行时 | Phase 1 开始时 |
| 动效库 | Framer Motion 12 | react-spring / CSS animations | 声明式 API、布局动画、AnimatePresence | Phase 1 开始时 |
| 图标库 | Lucide React | Heroicons / Font Awesome | 统一性、tree-shaking、Apple HIG 气质 | Phase 1 开始时 |
| Python SDK | openai 1.58 + anthropic 0.42 | langchain / 原生 HTTP | 轻量、lazy import、覆盖全部商用引擎 | Phase 1 开始时 |
| 嵌入方案 | Hash-based 128 维 (默认) | text-embedding-3-small / bge | 零依赖、确定性、可测试；生产可换 | Phase 1 开始时 |
| 测试框架 | pytest 8.3 + pytest-asyncio | unittest | 简洁、fixture 生态、异步原生 | Phase 1 开始时 |
| 部署平台 | Railway | Vercel / Fly.io | Monorepo 支持、Nixpacks、简单 | 2026-07-13 |
| 代码风格 | Python: 类型注解全 + 纯逻辑/I/O 分离 | — | 便于离线单测 | Phase 1 开始时 |
| 文档语言 | 中文（代码标识符英文） | — | 项目惯例 | 项目开始时 |

---

## 4. 已知的"不完美"（Technical Debt）

这些是故意留下的技术债务，不是因为忘了，而是因为渐进式演进——当前阶段不值得投入。

| 债务 | 严重度 | 为什么允许 | 计划何时还 |
|------|--------|-----------|-----------|
| 记忆仅在内存 | 🔴 高 | Phase 1 骨架验证核心逻辑优先；MemoryStore 接口已就绪，换存储零改上层 | Phase 1 收尾（下一步） |
| Reasoner 不做 ReAct | 🔴 高 | 双系统判据本身已可验证切换逻辑；ReAct 需要工具生态奠基 | Phase 1→2 过渡 |
| 意图/情感是关键词启发式 | 🟡 中 | 验证判据框架优先于精度；LLM 分类器已留接口 | Phase 1 收尾 |
| 前端数据全是 mock | 🟡 中 | 先验证设计与交互；后端 API 已就绪，对接是接线工作 | Phase 1 收尾 |
| 无前端自动化测试 | 🟡 中 | 前端仍在原型阶段，频繁重构；稳定后补 | Phase 2 |
| BeliefState 每次重建 | 🟢 低 | 当前缺少持久化基础，持久化后会一并解决 | Phase 2 |
| 嵌入用 hash 而非模型 | 🟢 低 | 可插拔设计，生产环境一行 `set_embedder()` 替换 | Phase 2 |
| 无多用户隔离 | 🟢 低 | 当前个人使用场景，生产化时加 | Phase 4 |
| 无速率限制 | 🟢 低 | 同上 | Phase 4 |

---

## 5. 已放弃的方案（避免重蹈覆辙）

| 方案 | 为什么放弃 | 记录 |
|------|-----------|------|
| 单模型全量推理（纯 ReAct） | 延迟过高，无法满足实时对话与深度推理的并存需求 | ADR-001 方案 A |
| 纯云端架构（iPhone） | 隐私风险大、延迟高，用户明确要求本地化选项 | ADR-006 方案 A |
| 直接上生产栈（Redis+PG+Milvus+K8s） | 个人项目起步部署门槛高，过度设计，违反渐进原则 | ADR-010 方案 A |
| 单层护栏（仅 LLM 内容过滤） | 单层易被绕过，安全工程基本原则是纵深防御 | ADR-005 方案 A |
| 单一巨型 README | 单文件臃肿、难导航、难分工、难增量更新 | ADR-011 方案 B |
| 硬编码 if-else 选模型 | 耦合、难扩展、无成本/可用性感知 | ADR-008 方案 B |
| 静态配置单模型切换（1.0 做法） | 无法按任务自动选优、无回退 | ADR-008 方案 A |

---

## 6. 项目命名与术语传统

- **"Sunday"** 的由来：Sun（日）+ Day（天）="星期天"——放松、自由、全天陪伴的感觉。非宗教含义。
- **代码中的 "Banana"**：用户昵称，出现在 Sidebar 用户信息、Git 提交作者、测试数据中。
- **"一个心智，服务你的一切"**：中文 slogan，对应英文 "One mind for every task"。
- **文件编码**：UTF-8。Windows 终端可能显示中文乱码，这是显示问题，不影响数据。
