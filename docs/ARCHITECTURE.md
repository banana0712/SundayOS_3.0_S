# ARCHITECTURE.md · Sunday OS 系统架构

> 基于对 `backend/` 和 `console/` 实际代码的完整分析。本文档描述系统**是什么**，决策理由见 [PROJECT_MEMORY.md](PROJECT_MEMORY.md) 和 [docs/adr/](adr/)。

**版本** 2.0 · **最后更新** 2026-07-13

---

## 1. 架构总览：六层 + 引擎抽象层

```
┌──────────────────────────────────────────────────────────────┐
│ L6 安全治理   六层护栏 · 预算化自主 · 隐私 · 审计              │
├──────────────────────────────────────────────────────────────┤
│ L5 应用技能   技能注册 · 工具路由 · 四角色配置（未实现）        │
├──────────────────────────────────────────────────────────────┤
│ L4 交互人格   共情计算 · 人格锚定 · 对话管理（未实现）          │
├──────────────────────────────────────────────────────────────┤
│ L3 认知引擎   双系统(Talker+Reasoner) · ReAct · 规划器          │
├──────────────────────────────────────────────────────────────┤
│ L1.5 引擎抽象  ★ 统一 Provider 接口 · 动态路由器 · 回退链     │
│               DeepSeek│Qwen│Claude│GPT│Ollama                 │
├──────────────────────────────────────────────────────────────┤
│ L2 数据记忆   Storage 层（已实现）→ Reflection 层（未实现）    │
│               → Experience 层（未实现）                        │
├──────────────────────────────────────────────────────────────┤
│ L1 基础设施   SQLite（未接）+ ChromaDB（未接）+ 进程内缓存      │
│               GitHub 真源（未实现）                             │
└──────────────────────────────────────────────────────────────┘
```

**实现状态**：
- L1.5 引擎抽象层、L2 记忆 L1 Storage、L3 双系统切换判据、L6 护栏已实现并通过 28 个测试。
- L3 ReAct 循环、L4 共情计算、L5 技能系统**未实现**。
- 记忆仅在内存（重启即失）——持久化是 Phase 1 收尾的第一优先任务。

---

## 2. 后端代码地图（实际文件）

```
backend/
├── app/
│   ├── main.py                    # FastAPI 入口：7 个端点 + CORS + 鉴权
│   ├── webchat.py                 # 自托管双语 Chat UI（HTML/CSS/JS，同源免 CORS）
│   ├── engines/                   # ★ L1.5 认知引擎抽象层
│   │   ├── base.py                #   EngineProvider 抽象 + EngineMessage/EngineResponse/Complexity
│   │   ├── providers.py           #   4 个具体引擎：OpenAICompatible / Anthropic / Mock
│   │   ├── registry.py            #   引擎注册：从环境变量构建引擎列表 + env() helper
│   │   └── router.py              #   CognitiveRouter：候选过滤 → 多维评分 → 回退链 + 熔断
│   ├── memory/                    # L2 数据记忆层
│   │   ├── schema.py              #   MemoryNode 数据模型（5 种类型 + 重要性衰减）
│   │   ├── store.py               #   MemoryStore：add/retrieve/delete + 复合评分检索
│   │   └── embedding.py           #   可插拔 Embedder（默认 hash embedding，无外部依赖）
│   ├── cognition/                 # L3 认知引擎层
│   │   ├── belief.py              #   BeliefState：用户信念模型（目标/任务/情绪/障碍）
│   │   └── dispatch.py            #   needs_reasoner()：双系统切换判据 + risk_level()
│   └── guardrails/                # L6 安全治理层
│       └── pipeline.py            #   输入护栏（L4）+ PII 脱敏（L3）+ 工具风险分级（L5）
└── tests/
    ├── test_router.py             # 11 测试：路由打分/候选过滤/回退链/熔断
    ├── test_memory.py             # 7 测试：复合评分/用户隔离/衰减/归档
    └── test_dispatch_guardrails.py # 10 测试：双系统判据/注入拦截/PII
```

### 2.1 引擎抽象层（L1.5）——实际实现

**核心抽象** (`engines/base.py`)：
```python
class EngineProvider(ABC):
    id: str                           # "deepseek-chat" / "claude-opus" / "mock-fast"
    caps: EngineCapabilities          # function_calling / streaming / strong_reasoning / local / languages
    price_in: float                   # USD/1M prompt tokens
    price_out: float                  # USD/1M completion tokens
    avg_latency_ms: float             # 滚动平均，路由器用于打分

    async def complete(messages, temperature, tools, max_tokens) -> EngineResponse
    async def stream(messages, temperature) -> AsyncIterator[str]
    async def health() -> bool
```

**四个具体引擎** (`engines/providers.py`)：

| 引擎 | 适配方式 | 关键特征 |
|------|---------|---------|
| `OpenAICompatibleProvider` | AsyncOpenAI SDK | 覆盖 DeepSeek/Qwen/OpenAI/Ollama |
| `AnthropicProvider` | AsyncAnthropic SDK | 独立 system/turns 拆解逻辑 |
| `MockProvider` | 纯本地确定性 | hash-based echo，零外部依赖，28 个测试的基础 |

所有 SDK 都是 **lazy import**（首次调用时才加载），未配 Key 时后端仍可启动。

**引擎注册** (`engines/registry.py`)：
- `env(name)` —— 鲁棒的环境变量读取：按去空格后的名字匹配，容忍 `DEEPSEEK_API_KEY ` 尾部空格
- `build_engines()` —— 检查 DeepSeek / Qwen / OpenAI / Anthropic / Ollama 的 Key，实例化有 Key 的引擎
- **回退机制**：若一个引擎都没配（且 `SUNDAY_ALLOW_MOCK != "false"`），自动启用 2 个 MockProvider（`mock-fast` + `mock-strong`）

**路由选择** (`engines/router.py`)：

整个路由决策是**纯函数**（`plan()`），才做 I/O（`route()`）：
1. **复杂度分类**——`heuristic_complexity()` 用正则识别代码/工具/风险关键词，分 L1-L4
2. **候选过滤** (`_eligible`)——硬约束：熔断器、工具需求、隐私要求、推理能力、上下文窗口
3. **多维评分** (`_score_all`)——按复杂度档位取不同权重：
   - L1: 成本 50% + 延迟 30% + 能力 20%
   - L3: 能力 60% + 成本 20% + 延迟 10%
   - L4: 能力 80% + 成本 5% + 延迟 5%
4. **回退链** (`route()`)——按评分降序依次尝试，任一成功即返回；全失败则返回 `response=None`（优雅降级）
5. **熔断器**——连续 3 次失败后熔断 60 秒，之后半开探活

每个路由决策生成 `RouteTrace`：包含候选列表、评分、选中引擎、回退使用情况、错误详情、延迟、用量——全部透传至 API 响应。

### 2.2 记忆系统（L2）——实际实现

**数据模型** (`memory/schema.py`)：
- `MemoryNode`：content / user_id / type / importance(1-10) / embedding / tags / evidence_ids / access_count / frozen
- `MemoryType`：EPISODIC / SEMANTIC / PROCEDURAL / REFLECTION / EXPERIENCE
- `effective_importance()`：\( importance \times 0.5^{(days/30)} \times (1 + 0.1 \times access\_count) \) ——30 天半衰期

**记忆存储** (`memory/store.py`)：
- `MemoryStore` —— 进程内存字典 `dict[str, MemoryNode]`
- **复合评分检索**：\( score = \alpha \cdot recency_{norm} + \beta \cdot importance_{norm} + \gamma \cdot relevance_{norm} \)
  - Recency：\( 0.995^{hours} \)，每小时衰减 0.5%
  - Importance：用户设置值 / 10（归一化到 [0,1]）
  - Relevance：cosine(query_embedding, memory_embedding)
  - **三个分量各自 min-max 归一化到 [0,1] 后再加权求和**——确保维度间可比
- `archive_expired()`：低于阈值的非冻结、低重要性记忆自动清理
- 检索时自动 touch 记忆（更新 last_access + access_count）——访问即强化

**嵌入** (`memory/embedding.py`)：
- 默认 `_hash_embed()`：bag-of-tokens MD5 → 128 维 L2 归一化向量。确定性、无依赖、可测试。
- `set_embedder()` 可在生产环境替换为真实嵌入模型（如 text-embedding-3-small）。

### 2.3 双系统认知（L3）——实际实现

**系统1 / 系统2 切换判据** (`cognition/dispatch.py`)：

`needs_reasoner()` 返回 True 的条件（任一满足）：
- 意图词含 `plan/code/analyze/research/multi_step`
- 文本含工具关键词（搜索/运行/计算/规划…）
- 多步连接词 ≥ 1（先…然后…之后…Step 1…）
- `risk_level()` ≥ MEDIUM
- BeliefState 有未解决的障碍
- 长文本（>280 字符）含问号

`risk_level()` 三层：
- LOW：普通对话
- MEDIUM：含工具意图
- HIGH：含高风险词（删除/支付/转账/权限）

**信念状态** (`cognition/belief.py`)：
- `BeliefState`：current_goal / active_tasks / obstacles / motivations / emotional_state(mood/energy/stress) / preferences_touched
- `has_unresolved_obstacles()` —— 影响双系统切换判据
- 当前在 `main.py` 中每次对话新建临时的 BeliefState，未持久化

### 2.4 护栏系统（L6）——实际实现

**输入护栏** (`guardrails/pipeline.py`)：
- L4 层：长度上限 8000 字符 / 阻止注入（`ignore all previous instructions` 模式）/ 阻止越狱（`jailbreak`/`DAN mode`）
- 检测到即抛 `GuardrailTripwire` → HTTP 400

**输出护栏**：
- L3 PII 脱敏：正则匹配 + 替换 email / 手机号 / 信用卡 / 身份证号 → `[REDACTED_xxx]`

**工具风险分级**（L5，预定义映射）：

| 风险等级 | 示例工具 |
|---------|---------|
| low | search, web, read_file |
| medium | send_email, run_python, github, write_file |
| high | delete_file, pay, change_permission, delete_account |

`requires_confirmation(tool_name)` → high 级工具需要 HITL 确认。

### 2.5 API 层——实际端点

| 方法 | 路径 | 功能 | 鉴权 |
|------|------|------|------|
| GET | `/` | 自托管双语 Chat UI (HTML) | 无 |
| GET | `/health` | 健康检查 + 引擎列表 + 记忆条数 | 无 |
| GET | `/api/engines` | 各引擎能力/价格详情 | X-API-Key |
| GET | `/api/debug/env` | 环境变量诊断（名称+长度，不泄露值） | X-API-Key |
| POST | `/api/chat` | 对话：护栏→记忆检索→双系统判据→路由→PII脱敏→记忆写入 | X-API-Key |
| POST | `/api/memory/store` | 写入记忆 | X-API-Key |
| POST | `/api/memory/search` | 检索记忆（含评分分量） | X-API-Key |
| DELETE | `/api/memory/{id}` | 删除记忆 | X-API-Key |

对话流程（`POST /api/chat`）：
```
用户输入 → L6 输入护栏 → L2 记忆检索(6条) → L3 双系统判据(needs_reasoner)
→ L1.5 路由(CognitiveRouter.route) → L6 PII脱敏 → L2 记忆写入(异步)
→ 响应(含 reply/engine/system/complexity/risk/trace)
```

### 2.6 聊天 UI（webchat.py）

`CHAT_HTML` —— 内联在 Python 中的单文件 HTML/CSS/JS 聊天界面：
- 与后端同源，免 CORS
- 双语（中/EN），token 与后端 DESIGN_SYSTEM 对齐
- API Key 存储在浏览器 localStorage，不硬编码在 HTML
- 展示引擎信息（fast/deep 标签）、连接状态、健康检查轮询（8s）
- ~190 行，零外部依赖，直接由 FastAPI 服务

---

## 3. 前端代码地图（实际文件）

```
console/
├── src/
│   ├── app/
│   │   ├── globals.css            # CSS 变量（Design Language 1.0 token）+ Tailwind 基础样式
│   │   ├── layout.tsx             # 根布局：metadata + AppShell
│   │   └── page.tsx               # 页面入口（return null，由 AppShell SPA 路由接管）
│   ├── components/
│   │   ├── shell/
│   │   │   ├── app-shell.tsx      # SPA ViewRouter：按 view 状态切换 View 组件
│   │   │   ├── sidebar.tsx        # 280px 侧边栏：品牌/搜索/导航/用户信息
│   │   │   ├── topbar.tsx         # 顶部栏
│   │   │   ├── inspector.tsx      # 右侧 Inspector 面板
│   │   │   ├── console-dock.tsx   # 底部 Developer Console（可折叠）
│   │   │   └── command-palette.tsx # ⌘K 命令面板
│   │   ├── views/
│   │   │   ├── dashboard.tsx      # Dashboard：8 指标卡 + 活动图 + 情绪雷达 + 健康 + 目标 + 事件
│   │   │   ├── brain.tsx          # Brain Viz：SVG 认知架构图（核心+8节点+负载环+信号动画）
│   │   │   ├── chat.tsx           # 对话视图
│   │   │   └── coming-soon.tsx    # 占位视图
│   │   └── ui/
│   │       └── primitives.tsx     # 通用组件：Card/Sparkline/Donut/Radar/Badge/SectionTitle
│   ├── store/
│   │   └── ui.tsx                 # UI 状态管理（view/inspector/console/palette/theme）+ useDrift/useNow
│   ├── i18n/
│   │   ├── index.tsx              # I18nProvider：中/英切换，localStorage 持久化
│   │   └── dict.ts                # 翻译字典
│   └── config/
│       └── nav.ts                 # 导航配置（NAV / NAV_GROUPS）
├── tailwind.config.ts             # Tailwind 扩展：token→CSS 变量映射 + 字体层级 + 动效
└── package.json                   # Next.js 15 + React 19 + Tailwind 3 + Framer Motion + Lucide
```

### 3.1 前端架构特征

- **SPA 风格视图切换**：Next.js 路由仅有 `/`，内部用 `useUI().view` 状态切换 5 个视图（Dashboard / Brain / Chat / Memory / Developer），配合 Framer Motion AnimatePresence。
- **三栏布局**：Sidebar(280px) · Content · Inspector(~340px) + 底部 Console Dock。
- **设计 token 已落地**：所有颜色/间距/圆角/阴影/动效在 `globals.css` + `tailwind.config.ts` 中定义，与 DESIGN_SYSTEM.md 100% 对齐。
- **前端未接后端**：当前所有数据（指标、情绪、健康、目标、事件）都是**硬编码 mock 数据**或 `useDrift()` 生成的随机漂移值。没有 `fetch()` 调用。

---

## 4. 技术栈

| 层 | 技术 | 备注 |
|----|------|------|
| 后端框架 | FastAPI 0.115 + Uvicorn 0.34 | Python 3.11+，类型注解齐全 |
| 引擎 SDK | openai 1.58 + anthropic 0.42 | 均为 lazy import，非运行时必需 |
| 数据验证 | Pydantic 2.10 | 请求/响应模型 |
| 测试 | pytest 8.3 + pytest-asyncio 0.25 | 28 测试，0.04s 全过，纯离线 |
| 前端框架 | Next.js 15.1 + React 19 | App Router |
| 样式 | Tailwind CSS 3.4 + CSS 变量 | Design Language 1.0 |
| 动效 | Framer Motion 12.42 | Spring 为主 |
| 图标 | Lucide React 0.474 | 唯一图标库，禁止混用 |
| 运行时存储 | 进程内存（dict） | 未持久化，重启即失 |

---

## 5. 数据流（实际）

```
用户消息
  → POST /api/chat {message, user_id}
  → GuardrailPipeline.check_input()         # L6 输入护栏
      ↳ 长度检查(>8000→拒绝)
      ↳ 注入/越狱模式匹配 → GuardrailTripwire
  → MemoryStore.retrieve(query, user_id, k=6)  # L2 检索
      ↳ 复合评分(recency×importance×relevance)
  → needs_reasoner(role_hint, message, belief) # L3 双系统判据
  → CognitiveRouter.route(CognitiveRequest)    # L1.5 路由
      ↳ heuristic_complexity() → L1-L4
      ↳ _eligible() → 候选过滤
      ↳ _score_all() → 多维评分
      ↳ for engine in ranked → try complete()
      ↳ 成功 → CognitiveResult(response, RouteTrace)
      ↳ 全失败 → CognitiveResult(None, RouteTrace)
  → redact_pii(response.text)                  # L6 输出 PII 脱敏
  → MemoryStore.add(MemoryNode)                # L2 异步记忆写入
  → {"reply": ..., "engine": ..., "system": ..., "trace": {...}}
```

---

## 6. 安全架构（已实现部分）

| 层级 | 机制 | 状态 |
|------|------|------|
| L4 规则层 | 长度上限 (8000 chars) | ✅ |
| L4 规则层 | 注入/越狱模式匹配 (blocklist regex) | ✅ |
| L3 PII 过滤 | 输出 PII 正则脱敏 (email/手机/信用卡/身份证) | ✅ |
| L5 工具风险 | 工具风险预定义映射 (low/medium/high) | ✅（定义就绪，工具执行未接） |
| L6 HITL | 高风险工具确认 (requires_confirmation) | ✅（定义就绪，执行循环未接） |
| 鉴权 | X-API-Key 头校验 | ✅（所有 /api/* 端点） |
| LLM 安全分类器 | 基于 LLM 的 moderation 判断 | ❌（接口留空，待接） |
| 密钥管理 | .env + 环境变量 | ✅ |
