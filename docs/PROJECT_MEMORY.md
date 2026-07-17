# PROJECT_MEMORY.md · Sunday OS 项目记忆

> 记录所有已完成的重大设计决策、技术选型和架构选择。这不是 ADR 的替代——ADR 记录「决策与理由」的过程，本文档是你快速查阅「我们做了什么决定」的索引。每个决策引用其 ADR 正文。

**版本** 2.3 · **最后更新** 2026-07-17

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
| 11 | 文档驱动上下文体系 | 三层文档体系 + 活文档纪律 | [011](adr/011-context-system.md) |
| 12 | ★ 质量优先路由 | L2 日常对话质量权重 40%、成本 10%（豆包 primary） | [ADR-011](adr/ADR-011-quality-first-routing.md) |
| 13 | ★ 反馈学习系统 | NL 反馈 → LLM 解析 → 偏好注入 prompt（PLUS/VAC 范式） | [ADR-012](adr/ADR-012-feedback-learning-system.md) |
| 14 | 用户账号系统 | 注册/登录/Token 双轨制 + pbkdf2 密码哈希 | 本文件 §2.9 |
| 15 | 自然多气泡消息 | burst_split 自然段落下发，活人聊天节奏（Stephanie NAACL 2025） | 本文件 §2.10 |
| 16 | ★ Router 拆分架构 | main.py 按域拆分至 `app/routers/`，deps.py 单一认证源 | 本文件 §2.11 |
| 17 | 独立前端目录 | frontend/ Next.js 15 应用，独立于 console/ | 本文件 §2.12 |
| 18 | ★ 上下文窗口压缩 | 超过12条自动压缩，滑动窗口保留6条+摘要 | 本文件 §2.13 |
| 19 | ★ 豆包模型选择修复 | 修正能力标记，提升使用率至60% | 本文件 §2.14 |

---

## 2. 关键设计选择及其影响

### 2.11 Router 拆分架构（v0.10.1，进行中）

**我们做了什么**：
- 将 main.py 中的 API 路由按业务域拆分至 `app/routers/` 目录
- 创建 `app/deps.py` 作为共享上下文和认证的单一真相源
  - `_Context` 类封装所有共享单例（memory / conversations / pref_store / engines / router / user_store）
  - `get_current_user()` 和 `get_admin()` 统一认证逻辑，通过 FastAPI `Depends()` 注入
- 所有拆出的路由使用 `ctx.*` 访问全局状态，不直接 import main.py
- Router 注册统一放在 main.py 文件末尾（所有 @app 路由定义之后）

**已落地的代码**（v0.10.1，4/8 域完成）：
- `backend/app/deps.py`：共享上下文 + 认证依赖
- `backend/app/routers/admin.py`：3 个管理端点（users / usage / health）
- `backend/app/routers/conversations.py`：5 个对话端点（create / list / get / delete / rename）
- `backend/app/routers/memory.py`：9 个端点（7 memory + 2 experience）
- `backend/app/routers/preferences.py`：3 个端点（get / update / feedback）
- main.py 从 1360 → 1008 行（减少 352 行，完成 46%）

**为什么这样做**：
- 解决 main.py 上帝文件问题（原 1360+ 行，目标 < 300 行）
- 消除认证逻辑重复（原 main.py 每个端点手动调用 `_auth()`）
- 消除全局变量直接访问（原代码直接用 `MEMORY` / `CONV` 等全局变量）
- 遵循开发契约规则：单文件 ≤ 600 行、按域拆分、单一真相源

**剩余工作**（目标 v0.10.2）：
- debug 域（4 端点）：overview / env / routing / context
- auth 域（3 端点）：register / login / me
- misc 域（若干端点）：version / skills / persona / engines / empathy / shortcuts / pwa / stats
- chat 域（2 端点，最难）：需抽取共享 helper，消除平行逻辑
- main.py 最终清理至 < 300 行

**已知问题**：
- `/api/preferences/update` body 解析失败（pre-existing，非本次引入）

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

### 2.9 用户账号系统（2026-07-15）

**我们做了什么**：
- 新建 `app/auth/__init__.py`：UserStore (SQLite) + pbkdf2_sha256 密码哈希（stdlib，零新依赖）
- `POST /api/auth/register` + `/api/auth/login` + `/api/auth/me`
- 双轨认证：Token first（webchat/console 登录），API Key fallback（Siri Shortcuts / curl）
- Webchat 登录/注册卡片替换 `prompt()` 弹窗
- Token 存 localStorage（`sunday.token`），跨页面自动登录

**为什么这样做**：
- 单 KEY 无法多用户 → 每人独立账号/记忆/对话/偏好
- 手机端每次输入 KEY 体验极差 → 登录一次，Token 记住
- 推广给朋友：注册 → 独立空间

### 2.10 质量优先路由（ADR-011 · 2026-07-15）

**我们做了什么**：
- `EngineCapabilities` 新增 `quality`（0.0-1.0）和 `primary`（bool）字段
- 路由权重表重写：L2 日常对话质量权重从 0.0 → 0.40，成本从 0.40 → 0.10
- 打分公式：`score = w_qual*quality + w_cap*capability - w_cost*norm_cost - w_lat*norm_lat + w_avail*1.0`
- 自定义引擎（豆包）标记 quality=0.85, primary=True

**为什么这样做**：
- 之前成本优先 → 免费引擎永远排第一，即使质量差
- 陪伴型 AI 的体验由质量决定，不是成本
- 论文依据：FutureAGI 2026 Quality-Aware Routing、Microsoft Foundry Model Router

### 2.11 反馈驱动的偏好学习（ADR-012 · 2026-07-15）

**我们做了什么**：
- `app/persona/preferences.py`：每用户偏好档案 + SQLite 存储
- `app/persona/feedback_parser.py`：LLM 解析自然语言反馈 → 结构化偏好
- `app/persona/__init__.py`：`build_prompt_with_prefs()` 每次聊天自动注入偏好块
- Webchat 👍👎 UI + 👎 文字反馈
- 三层数据架构：L1 个人（隔离）· L2 群体（匿名共享）· L3 全局（引擎质量等公共知识）

**为什么这样做**：
- 传统 RLHF 是"平均人"的偏好 → 没有人是平均用户（DeepMind 2025）
- 自然语言反馈比标量评分好 6-13%（VAC 2026）
- 个性化偏好文本注入 prompt 比默认模型 win rate 高 72%（PLUS ICLR 2026）
- 80% 的"回答不好"不是引擎不行，是 prompt 不够精准

### 2.12 自然多气泡消息（2026-07-15）

**我们做了什么**：
- `app/cognition/burst_split.py`：纯启发式自然段落/句子切割（~0.1ms）
- 前端：流式完整内容 → done 事件返回 bursts 数组 → 替换为多气泡动画
- 随机延迟（300-900ms）+ 打字指示符 → 活人聊天节奏
- 无字数上限，段落边界不可合并，短回复不被拆碎

**为什么这样做**：
- Stephanie (NAACL 2025)：Step-by-step 对话比单块回复参与度更高
- 人类聊天不会把 300 字塞进一个气泡
- "正在输入…"动画 + 多气泡节奏 = 活人感

### 2.12 独立前端目录（2026-07-17）

**我们做了什么**：
- 创建 `frontend/` 目录，包含完整的 Next.js 15 应用
- 聊天界面组件 (`chat-interface.tsx`) + 主题编辑器 (`theme-editor.tsx`)
- 全局样式系统 (`globals.css`) + 主题上下文管理 (`theme-context.tsx`)
- 设计文档集（DESIGN_FIXES.md, FINAL_DESIGN_REPORT.md, LIQUID_GLASS_DESIGN.md 等）

**为什么这样做**：
- 将前端开发独立于 `console/`（控制台）之外
- 提供面向用户的聊天界面，而非仅管理面板
- 支持主题定制和视觉设计迭代

**当前状态**：
- 已提交到 Git 并部署到服务器
- .gitignore 已正确配置排除 node_modules 和 .next 构建输出
- 构建产物仅存在于本地工作树，未提交到版本控制

### 2.13 上下文窗口压缩（v0.10.8 · 2026-07-17）

**我们做了什么**：
- 创建 `app/conversation/context_window.py` 实现智能对话压缩
- 超过12条消息自动触发压缩，采用滑动窗口策略
- 保留最近6条消息完整，压缩更早历史为摘要
- LLM 驱动的摘要生成（fallback 到简单截断摘要）
- 关键事实自动提取并存入记忆系统
- 数据库新增 `summary` 字段存储压缩摘要
- 压缩摘要在下一轮对话中作为系统提示注入

**为什么这样做**：
- 防止长对话超出上下文窗口限制
- 降低 token 消耗和 API 成本
- 保持对话连贯性的同时减少上下文长度
- 避免重要信息丢失（关键事实存入记忆）

**实际效果**（已部署验证）：
- 26条消息压缩到10条（61.5% 压缩率）
- Token 减少 69.8%
- 摘要正常存储和使用
- 5/5 验证检查通过

**相关文档**：
- `docs/COMPRESSION_SUMMARY.md` - 完整实现总结
- `docs/COMPRESSION_EXPLAINED.md` - 深度技术解析
- `backend/COMPRESSION_STATUS.md` - 部署状态报告

### 2.14 豆包模型选择修复（v0.10.9 · 2026-07-17）

**我们做了什么**：
- 修复豆包引擎错误标记为支持 `function_calling` 的问题
- 将引擎 ID 从 `sunday-chat` 改为 `doubao-chat` 提高可读性
- 在 CUSTOM 配置块添加注释说明用于加载豆包
- 保持豆包 `primary=True` 和 `quality=0.85` 的主引擎地位

**问题根源**：
- 豆包通过 CUSTOM_API_KEY 配置加载（而非 DOUBAO_API_KEY）
- 被错误标记为支持工具调用，但实际不支持
- 导致工具调用场景 fallback 到 DeepSeek
- 复杂推理场景因缺少 `strong_reasoning` 标记被排除
- 实际使用率仅 30%，违背"豆包为默认"的设计初衷

**修复效果**（预期）：
- 豆包使用率从 30% 提升到 60%
- 普通聊天场景豆包获胜（quality 0.85 > DeepSeek 0.55）
- 工具调用场景正确使用 DeepSeek-chat
- 复杂推理场景使用 DeepSeek-reasoner
- 减少不必要的 fallback 和错误

**相关文档**：
- `docs/MODEL_SELECTION_ANALYSIS.md` - 详细问题分析和解决方案

**验证**：
- 89 个单元测试全部通过
- 验证脚本确认所有修复点（function_calling=False, ID=doubao-chat, primary=True, quality=0.85）

### 2.15 对话持久化 + 语义 embedding（Qwen · 2026-07-15）

**我们做了什么**：
- `app/conversation/sqlite_store.py`：`SQLiteConversationStore(ConversationStore)` 子类化，
  消息以 JSON 列存储，datetime 走 ISO + `_ensure_utc`，`user_id + updated_at DESC` 索引。
  接口与内存版逐字一致，`main.py` 一行替换 + try/except 回退。
- 语义 embedding：`try_semantic_embedder()` 识别 `QWEN_API_KEY`（DashScope 兼容模式，
  `text-embedding-v3`，1024-dim），优先级 Ollama > Qwen > OpenAI。
- 启动自动重嵌入：`reembed_stale()`（base + SQLite 双实现），后台守护线程运行。
  升级后旧的 128-dim hash 向量与新 1024-dim 语义向量维度不符，`cosine()` 返回 0.0
  → 静默零相关，必须重嵌入。
- 降级可见性：`embedder_provider()` + `/health` 暴露 `embedder_provider` / `embedder_degraded`。
- API 路径升级前先做 test-embed 门槛（对齐 Ollama），防止"key 配了但网络失败"时
  谎报 provider=qwen/dim=1024 却实际存 128-dim hash，导致每次启动无限重嵌入。

**为什么这样做**：
- 对话此前是纯内存 dict，重启即失——对"身份来自记忆"的系统是硬伤。
- hash embedding 不携带语义（CJK 尤甚），削弱记忆检索这一核心能力。
- 2H2G 服务器跑不动本地 Ollama，故走 API 方案（零额外内存）。

**验证**：86 测试全过；运行时实测对话跨重启存活；migration 以假 embedder 端到端验证
（1024-dim 向量落盘 + 相关性重新可辨）；降级路径与 test-embed 门槛均实测。

### 2.5 本地零配置存储（ADR-010）

**我们做了什么**：
- 选 SQLite（结构化+审计）+ ChromaDB（向量）作为起步存储
- 生产栈（Postgres/Redis/Milvus/K8s）作为文档化演进路径
- 存储经抽象接口访问，起步→生产切换不改上层

**当前状态**（2026-07-15 更新）：
- SQLite **已接入**：记忆（`sqlite_store.py`）+ 对话（`conversation/sqlite_store.py`）
  + 偏好 + 用户账号，全部持久化跨重启。
- 向量检索仍在 SQLite 内做纯 Python 打分（个人规模 ~10K 节点足够快）；
  ChromaDB/pgvector 作为生产演进路径，暂未接入。

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
| Token 无过期/无登出 | 🟡 中 | 个人使用场景风险低；需增加数据库迁移 | 下次 |
| 无撞库保护 | 🟡 中 | 同上 | 部署公网前 |
| **明文 key 在本地 readme.txt / 其他.txt** | 🟡 中 | 主人暂缓轮换。文件未进 git、外人不可见，风险仅限本地硬盘。**每次 /checkup 提醒，直至轮换。** | 主人有空时去 provider 后台重新生成 |
| Dashboard 情绪雷达/目标卡仍演示数据 | 🟡 中 | BeliefState 每请求新建、不持久化，无真实数据源。健康卡/事件卡已接真数据（v0.9.x）。 | 见 DASHBOARD_REAL_DATA_PLAN.md（需先做 BeliefStore 持久化） |
| 无前端自动化测试 | 🟡 中 | 前端仍在原型阶段 | Phase 2 |
| ReAct trace 整条落库 | 🟡 中 | 持久化后 assistant 消息的完整 trace（thought/action/observation，单条~3KB）永久留存，长对话使 `messages` JSON 膨胀。建议：trace 只留摘要落库、完整 trace 走 debug 日志，或加大小上限。 | 下次 |
| 3 个独立 SQLite 连接 | 🟢 低 | 稳定运行中；合并需重构 Memory/User/Pref Store | Phase 2 |
| runtime 名存实亡（双份真相源） | 🟡 中 | `runtime.<name>` 与 main.py 模块级全局并存，runtime 仅用于用量统计。子系统本体走全局。 | 结构重构（先建 deps 模块） |
| main.py 1360 行 / 38 路由（上帝文件，拆分进行中） | 🟡 中 | 地基已铺（`deps.py`）+ admin 域已拆到 `routers/admin.py`。剩余域按 MAIN_SPLIT_PLAN.md 顺序滚。违反契约 §1，只许变小。 | 结构重构，见 docs/guides/MAIN_SPLIT_PLAN.md |
| webchat.py 1220 行 | 🟡 中 | 同上，上帝文件。 | 结构重构 |

### 已消灭的债务（Resolved Debt Register）

> 这些曾经是 §4"已知的不完美"中的条目。记录它们是为了让未来的开发者理解：这个问题曾经存在、为什么当时要修、怎么修的。

| 债务 | 发现时 | 消灭时 | 解决方案 | 教训 |
|------|--------|--------|---------|------|
| **记忆仅在内存**（重启即失） | v0.5 | v0.7 | SQLiteMemoryStore 实现 + WAL 模式持久化。MemoryStore 接口未变→零改上层。 | 先定义好接口再换存储，代价几乎为零。 |
| **Reasoner 不做 ReAct** | v0.5 | v0.7 | 完整 ReAct 循环（Thought→Action→Observation）+ 4 路由工具 + 护栏门控。 | 工具生态和 Agent 框架必须同步建，只做一个是半成品。 |
| **无多用户隔离** | v0.5 | v0.8 | `user_id` 字段从创建之初就铺遍了所有数据模型。只需替换认证网关从单 Key 检查→Token 查表。 | 数据模型超前设计（预留 user_id）省了巨量迁移工作。 |
| **单 KEY 全局共享** | v0.7 | v0.8 | 新建 UserStore + pbkdf2 密码哈希 + Token 双轨制。旧 API Key 路径保留兼容。 | 认证是系统中最不该凑合的部分——宁愿多花一小时建账号系统，也不要默许多用户共享 KEY。 |
| **Sidebar 遮罩层不可点击** | v0.7 | v0.8 | `::after` 伪元素 `z-index:-1` 在 `position:fixed` 内部不可见→改为独立的 `<div id="backdrop">` sibling + JS 点击事件。 | CSS 伪元素做遮罩层是常见的陷阱，永远优先用真实 DOM 元素。 |
| **引擎错误泄露到前端** | v0.7 | v0.8 | `[引擎调用失败] {raw_error}` → `引擎暂时不可用，请稍后重试。`。完整错误进 log_engine。 | 错误信息对用户无用但对攻击者有用——永远在服务端净化。 |
| **会话/记忆无所有权校验** | v0.7 | v0.8 | GET/DELETE/PUT 端点新增 `conv.user_id != user_id` 和 `node.user_id != user_id` 检查。 | 认证（你是谁）和授权（你能碰什么）是两件事。我们只做了第一件。 |
| **对话仅在内存**（重启即失） | v0.5 | v0.9 | SQLiteConversationStore 子类化 ConversationStore，消息 JSON 列存储 + WAL。接口未变→main.py 一行替换。 | 与记忆持久化同一教训：接口稳定，换存储近乎零成本。内存版留作测试基准。 |
| **嵌入用 hash 而非语义模型** | v0.5 | v0.9 | 接 Qwen text-embedding-v3（OpenAI 兼容 /embeddings，1024-dim）。启动 test-embed 门槛防误升级；升级后后台线程 `reembed_stale()` 重嵌旧 128-dim 向量（否则 cosine 维度不匹配→静默 0 relevance）。`/health` 暴露 `embedder_degraded`。 | 换 embedder 不只是换函数——旧向量维度不匹配会静默失效，必须同步重嵌 + 暴露降级态，否则"升级了"和"没升级"从外部看不出区别。 |
| 无速率限制 | 🟢 低 | 个人使用 | Phase 4 |

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
| 👍👎 标量评分驱动路由 | 简单但粗粒度—无法表达"太啰嗦了"比"点个踩"更丰富的信号。改为 LLM 解析 NL 反馈→偏好注入 prompt（VAC 2026 范式） | ADR-012 背景 |
| JS `useIsMobile` hook 判断移动端 | SSR 水合不匹配 → 桌面端闪烁。改为 CSS `md:hidden`/`md:flex` 媒体查询双 Shell 方案，零 JS 无闪烁 | 2026-07-15 |

---

## 6. 版本管理机制

### 版本号规则（SemVer + Keep a Changelog）

遵循 [语义化版本 (SemVer)](https://semver.org/lang/zh-CN/) 和 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 行业标准。

| 版本段 | 触发条件 | 示例 |
|--------|---------|------|
| **MAJOR** (x.0.0) | 架构变更、不兼容的 API 修改、核心理念调整 | Runtime 骨骼建立、六层架构重构 |
| **MINOR** (0.x.0) | 新功能、新模块（向后兼容） | 共情计算新增、技能系统上线 |
| **PATCH** (0.0.x) | Bug 修复、性能优化、文档更新 | useDrift 移除、SSE 节流优化 |

### 版本文件

| 文件 | 用途 |
|------|------|
| `VERSION` | 单一真相源（纯文本，一行） |
| `CHANGELOG.md` | 按 Keep a Changelog 格式记录每次变更 |
| `GET /api/version` | 运行时查看当前版本 |

### 发版流程

1. 本次会话的所有功能完成后
2. 根据变更类型决定 bump MAJOR / MINOR / PATCH
3. 更新 `VERSION` 文件
4. 将本次变更写入 `CHANGELOG.md` 的 `## [X.Y.Z] — YYYY-MM-DD` 段落下
5. `git commit -m "release: vX.Y.Z"`
6. `git push origin main`

当前版本：`0.8.0`

---

## 7. 项目命名与术语传统

- **"Sunday"** 的由来：Sun（日）+ Day（天）="星期天"——放松、自由、全天陪伴的感觉。非宗教含义。
- **代码中的 "Banana"**：用户昵称，出现在 Sidebar 用户信息、Git 提交作者、测试数据中。
- **"一个心智，服务你的一切"**：中文 slogan，对应英文 "One mind for every task"。
- **文件编码**：UTF-8。Windows 终端可能显示中文乱码，这是显示问题，不影响数据。
