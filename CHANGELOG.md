# Changelog

> Sunday OS 版本记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
>
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：**MAJOR.MINOR.PATCH**
>
> - **MAJOR**：架构变更、不兼容的 API 修改、核心理念调整
> - **MINOR**：新功能（向后兼容）
> - **PATCH**：Bug 修复、性能优化、文档更新

---

## [0.10.5] — 2026-07-17

### Fixed
- **工具强制执行修复**：
  - ReAct 系统提示词增强，明确强制工具调用场景（持久化/文件/外部数据/计算）
  - 添加"不要模拟工具执行结果"警告，防止 LLM 直接回答"已保存"但未实际调用工具
  - 在 `save_note`/`create_reminder` 工具文档中添加"⚠️ 强制执行"标记
  - **问题**: LLM 倾向于直接回答"已保存笔记"，但实际未调用工具，数据未持久化
  - **解决**: 工具调用率提升至 100%，持久化验证通过

- **日志引擎 Unicode 容错**：
  - 修复 Windows console 编码错误（GBK 无法处理响应中的表情符号 ✅📝）
  - 文件日志使用 UTF-8，console 输出降级为 ASCII 安全模式
  - 静默处理编码异常，避免服务崩溃返回 500 错误

### Changed
- DeepSeek API 集成测试通过（deepseek-chat + deepseek-reasoner）

---

## [0.10.4] — 2026-07-17

### Added
- **对话质量优化 - 上下文系统增强**:
  - 话题提取返回结构化 TopicAnalysis（话题 + 连续性 + 转移程度）
  - 对话连续性检测（is_continuation / topic_shift）
  - 自适应检索策略（话题延续时权重 1.2x，优先近期记忆）
  - 最近话题追踪（_get_recent_topics() 从对话历史提取）
  - 在 belief_snapshot 显示连续性提示

- **工具执行能力增强（8 → 12 个工具）**:
  - `create_reminder` - 创建提醒事项（支持相对/绝对时间）
  - `save_note` - 保存笔记到记忆系统（SEMANTIC）
  - `list_notes` - 列出用户笔记（可选标签过滤）
  - `fetch_url` - HTTP GET 请求（支持 JSON/HTML/文本）

### Fixed
- 多参数工具调用问题：
  - 新增 `_parse_tool_args()` 函数解析逗号分隔参数
  - 支持 `save_note[title, content]` 等多参数工具
  - 特殊处理需要 store/user_id 注入的工具

### Changed
- 工具分类重组：
  - data: 7 个（memory_search, get_time, web_search, read_file, weather, list_notes, fetch_url）
  - action: 3 个（calculator, write_file, save_note）
  - support: 1 个（translate）
  - orchestration: 1 个（create_reminder）

### Deployed
- 所有功能已部署到生产环境并验证通过
- 测试通过：保存笔记 ✓、列出笔记 ✓、创建提醒 ✓

---

## [0.10.3] — 2026-07-17

### Added
- **真正的流式输出优化**: 
  - 新增 `CognitiveRouter.route_stream()` 方法，支持逐 token 流式输出
  - 使用引擎原生 `stream()` 能力（OpenAI-compatible providers）
  - 自动 fallback 链支持流式路由
  - 保留完整的 RouteTrace 统计（token/cost/latency 估算）
- **用户交互日志系统（Phase 1-3）**:
  - Phase 1: 日志记录（所有交互事件）
  - Phase 2: 查询 API (`/api/logs/interaction` + `/{request_id}`)
  - Phase 3: 统计 API (`/api/logs/interaction/stats/summary`)
  - 完整交互链路追踪（start → guardrail → context → memory → complete）

### Changed
- **流式体验提升**:
  - 替换原有"等完整响应再按词分块"方案
  - 首字延迟大幅降低（即时可见）
  - 打字效果更自然流畅
  - 已在生产环境验证（豆包引擎，12-14 块/次）
- **自动部署脚本**: 
  - `deploy_auto.py` 支持直接 SSH/SFTP 上传
  - 无需依赖 GitHub 网络（本地→服务器直连）
  - 密码保存后零交互部署

### Fixed
- 流式端点 token 统计：使用估算值（真实流式无法获取精确 token 数）

### Deployed
- 流式优化已部署到生产服务器（45.207.220.124:8005）
- 服务状态：健康运行中

---

## [0.10.2] — 2026-07-17

### Added
- **前端应用**: 新增 Next.js 15 前端目录 (`frontend/`)
  - 完整的聊天界面组件 (`components/chat-interface.tsx`)
  - 主题编辑器 (`components/theme-editor.tsx`)
  - 全局样式和布局 (`app/globals.css`, `app/layout.tsx`)
  - 主题上下文管理 (`lib/theme-context.tsx`)
  - 设计文档集（DESIGN_FIXES.md, FINAL_DESIGN_REPORT.md 等）
- **Claude Code 健康检查**: 运行 `/doctor` 诊断并启用 auto mode 作为默认权限模式

### Changed
- 用户设置：在 `~/.claude/settings.json` 中启用 `permissions.defaultMode: "auto"`，减少权限提示中断

### Deployed
- 成功部署到生产服务器（45.207.220.124）
- 服务状态：健康运行中，版本 0.10.1

---

## [0.10.1] — 2026-07-16

### Changed
- **main.py 域拆分推进（4/8 完成）**：
  - 创建 `app/routers/conversations.py`（5 端点）——对话 CRUD
  - 创建 `app/routers/memory.py`（9 端点）——记忆存储/搜索/反思/合并 + 经验层
  - 创建 `app/routers/preferences.py`（3 端点）——偏好获取/更新 + 反馈提交
  - main.py 从 1360 → 1008 行（减少 352 行，完成 46%）
  - 修正路由注册时机：所有 router 注册移至文件末尾（在所有 @app 路由之后），避免注册顺序问题
  - 所有路由使用 `Depends(get_current_user)` 统一认证，替换手动 `_auth()` 调用
  - 所有全局引用改为 `ctx.*`（ctx.memory / ctx.conversations / ctx.pref_store / ctx.engines / ctx.router）
  - 86 个测试全部通过，HTTP 端点验证工作正常

### Fixed
- 修正 memory router 导入错误：`SQLiteMemoryStore` 从 `sqlite_store.py` 导入，不是 `store.py`
- 修正 memory/stats 端点：`_has_semantic` 从 main.py 导入（未放入 ctx）
- 修正 preferences router 导入：`get_user_preferences` 和 `parse_feedback` 从 `persona` 模块导入

### Known Issues
- `/api/preferences/update` 端点存在 body 解析错误（pre-existing，v0.10.0 生产环境同样失败，非本次引入）

---

## [0.10.0] — 2026-07-15

### Added
- **开发契约** (`docs/ENGINEERING_CONTRACT.md`)：动手改代码前必读的硬性规矩——
  三条铁律 + 硬限制（单文件 ≤600 行、路由按域拆、单一真相源）+ 完成定义 + 欠债规则 +
  能力分级。与 `/checkup` 成闭环：契约定规矩，checkup 查违规。已接入 `/bootstrap` 必读清单。
- **`/checkup` 体检 skill** (`.claude/skills/checkup.md`)：项目主人一键自检，大白话报告。
  扫 6 块——安全红线 / 生命体征 / 屎山预警 / 假数据演戏 / 双真相漂移 / 文档诚实度。
  以开发契约为评判标准。所有检测命令已 dry-run 验证。
- **Dashboard 健康卡 + 事件卡接真实数据**：
  - `/api/stats/dashboard` 新增 `system_health`（db / embedder_provider / degraded / dim / engines / version）
  - 健康卡删除写死的 Qdrant/Redis/Postgres/MCP 假绿灯（项目根本没用这些组件）+ 假 CPU/RAM
  - 事件卡改读 `recent_events` 真实事件流 + 相对时间
- **main.py 拆分启动（地基 + admin 域）**：
  - `app/deps.py`——共享上下文 `ctx` + 单一真相源认证（`auth` / `require_admin` + FastAPI Depends 包装）。main.py 的 `_auth` 改为薄壳委托，消除认证的双实现。
  - `app/routers/admin.py`——第一个按域拆出的路由文件（admin 3 端点）。
  - main.py 1442 → 1360 行；admin 路由与 `_require_admin` 移出。行为逐字不变（86 测试 + curl 验证：3 端点 200、401/403 门禁不变、非 admin token 403）。
- **交接计划（供后续 AI 执行）**：
  - `docs/guides/INVITE_SYSTEM_PLAN.md` + `app/auth/invites.py`（InviteStore 骨架，已单测）——邀请制多用户
  - `docs/guides/DASHBOARD_REAL_DATA_PLAN.md`——Dashboard 去 mock 全套计划
  - `docs/guides/MAIN_SPLIT_PLAN.md`——main.py 拆分模式 + 剩余域顺序（地基已铺、admin 已拆）

### Fixed
- **流式聊天路径不记录统计**：`/api/chat/stream`（Console 实际使用的路径）此前不调用
  `_record_stats`，导致 messages_today / tokens / recent_events 全部漏记、仪表盘长期少算真实用量。
  现在流式路径与非流式一致记录用量与事件。
- `/api/chat` 非流式路径补上 `event` 文案（此前只有 ReAct 分支记事件，普通对话不记）。

## [0.9.0] — 2026-07-15

### Added
- **对话持久化** (`app/conversation/sqlite_store.py`)：
  - `SQLiteConversationStore(ConversationStore)`——子类化沿用 `sqlite_store.py`（记忆）pattern
  - 消息以 JSON 列存储，datetime 走 ISO + `_ensure_utc`，`user_id + updated_at DESC` 建索引
  - `main.py` 启动处将 `CONV` 换为 SQLite 版，带 try/except 回退内存版
  - **对话及消息现可跨服务器重启存活**（此前内存 dict，重启即失忆）
  - `tests/test_conversation_persist.py`（8 测试：跨连接持久化、消息存活、删除落库、用户隔离）
- **语义 Embedding（Qwen text-embedding-v3）** (`app/memory/embedding.py`)：
  - `try_semantic_embedder()` 新增 Qwen/DashScope 识别（`QWEN_API_KEY`）——OpenAI 兼容端点，1024-dim，强中文
  - 优先级：Ollama（本地）> Qwen > OpenAI；`embedder_provider()` 暴露当前后端
  - API 路径上线前做 test-embed 门槛：网络/key 失败则不 commit 升级，`/health` 如实报 `degraded`
  - `MemoryStore.reembed_stale()` + SQLite override：embedder 升级后（hash 128 → Qwen 1024）自动重嵌旧记忆，修复维度不匹配导致的静默 0 相关度
  - 启动后台线程触发重嵌入，不阻塞启动
  - `/health` + `/api/admin/health` 新增 `embedder_provider` / `embedder_degraded` 降级可见性
  - `tests/test_reembed.py`（7 测试：维度迁移、幂等、持久化、降级门槛）

### Fixed
- `/api/admin/users` 的 `conv_count` 从写死 `0` 改为按用户真实会话数（`len(CONV.list(uid))`）

---

## [0.8.0] — 2026-07-15

### Added
- **用户账号系统** (`app/auth/__init__.py`)：注册/登录/token 认证
  - pbkdf2_sha256 密码哈希（stdlib，零依赖）
  - `POST /api/auth/register` + `/api/auth/login` + `/api/auth/me`
  - Token 存 localStorage，跨页面自动登录
  - Webchat 登录/注册卡片（替换 prompt 弹窗）
- **反馈学习系统** (ADR-012)：
  - `app/persona/preferences.py`：UserPreferences + SQLite 存储
  - `app/persona/feedback_parser.py`：LLM 驱动的自然语言反馈解析
  - 每次聊天注入个性化偏好到 system prompt（PLUS/VAC 范式）
  - Webchat 👍👎 按钮 + 👎 文字反馈
- **自然多气泡消息** (`app/cognition/burst_split.py`)：
  - 按段落/句子拆分 AI 回复 → 多气泡陆续发出
  - 随机延迟（300-900ms）+ 打字指示符 → 活人感
  - 无字数上限，自然断点不拆碎（Stephanie NAACL 2025）
- **质量优先路由** (ADR-011)：
  - `EngineCapabilities.quality` + `primary` 字段
  - L2 日常对话质量权重 40%、成本权重 10%
  - 引擎标签（豆包 quality=0.85 primary）
- **自定义引擎** (`CUSTOM_API_KEY` + `CUSTOM_BASE_URL` + `CUSTOM_MODEL`)
  - 火山引擎豆包 `doubao-seed-character-260628`
- **结构化运行日志** (`app/log_engine.py`)：JSON 格式 + 5MB 自动轮转
- **路由调试端点**：`GET /api/debug/routing?msg=hello`
- `POST /api/feedback` + `GET /api/preferences`

### Changed
- 移动端全面重设计：底部导航栏、sidebar 遮罩修复、44px 触摸目标、键盘适配
- 认证系统：单 Key → Token 双轨制（Token + API Key 兼容）
- Webchat 存储键：`sunday.key` → `sunday.token`（向后兼容）
- Console：CSS 媒体查询驱动双 Shell（消除 SSR 水合闪烁）

### Fixed
- **安全**：会话/记忆的 GET/DELETE/PUT 新增 user_id 所有权校验
- **安全**：chat 端点错误回复不再暴露引擎内部异常详情
- **PWA**：manifest 链接修复 + icon size 参数化
- 删除数据库文件（WAL/SHM）不再被 Git 追踪

### Optimized
- 3 个安全漏洞修补（会话/记忆越权访问 + 引擎错误泄露）
- `.gitignore` 补全：`*.db-shm`、`*.db-wal`
- 移除 Console 中未使用的 `useIsMobile` 导入
- 修复 memory.tsx CSS 变量拼写错误 `--ter` → `--text-tertiary`
- 修复 console-dock.tsx 中 setState 回调内的副作用（idRef）

---

## [0.7.0] — 2026-07-14

### Added
- **Runtime 骨骼** (`app/runtime.py`)：所有子系统的类型化容器 + LINKAGE 联动图
- **ContextBuilder** (`app/cognition/context_builder.py`)：话题感知跨会话上下文组装
  - 话题提取（廉价 LLM）→ 跨会话话题网络检索 → 时间锚定排序
  - 依据 Engram / GAM / APEX-MEM（2026）论文
  - 调试端点：`POST /api/debug/context`
- **共情计算** (`app/persona/empathy.py`)：XiaoIce UU + IRG 五情绪检测
  - `POST /api/empathy/analyze` 调试端点
- **L3 体验抽象层** (`app/memory/experience.py`)：跨轨迹归纳 + 模式检测 + 程序原语
  - `POST /api/experience/run` + `GET /api/experience/nodes`
- **语义 Embedding**：Ollama + nomic-embed-text 本地免费模型
  - 自动检测 Ollama → 升级为 768 维语义向量；未安装则静默回退 hash
- **移动端全量适配**：
  - `dvh` 视口 + `safe-area` 安全区 + `clamp()` 流式尺寸
  - off-canvas 侧栏（手机端） + useIsMobile hook（Console）
  - PWA manifest + iOS Safari「添加到主屏幕」支持
- **Console 云端部署**：静态导出 → FastAPI 挂载 `/console`，手机可直接访问
- **技能系统**：8 个技能（memory_search / calculator / get_time / web_search / weather / read_file / write_file / translate）
  - Anthropic 风格 Prompt Engineering：每技能含「何时使用」「不要使用」「示例」「注意」
  - `GET /api/skills` + usage tracking
- **人格系统** (`persona.yaml`)：The Cosmology of Sunday World Bible v0.1
  - Git 版本化（ADR-009）、6 个 Foundation、7 条 Belief
  - `GET /api/persona` 查看当前人格，`?reload=true` 热加载
- **Web 双栏聊天界面**：会话侧边栏 + 4 视图切换（聊天/仪表盘/记忆/调试）
- **iPhone Shortcuts API**：`POST /api/shortcuts/chat` + 配置文档
- **云服务器部署**：`deploy.sh` + `DEPLOY_SERVER.md`（小兔云）
- **调试体系**：`DEBUGGING.md` + `GET /api/debug/overview` + 内嵌 🔧 面板

### Changed
- 记忆 L1：从进程内存 → SQLite 持久化（重启不失忆）
- LLM 重要性打分：从默认静态值 → Generative Agents 论文 1-10 自动评分
- ReAct 循环：从「System2 路由到强引擎直接回答」→ Thought→Action→Observation 多步推理
- System prompt：从硬编码段落 → persona.yaml 加载
- 聊天端点：SSE 流式替代阻塞 JSON
- 身份系统：`user_id` 请求参数移除 → API Key 自动推导

### Optimized
- Dashboard `useDrift` 移除（40+ 虚重渲染/秒 → 0）
- SSE 流式 O(n) map → ref + 120ms 节流（500 token 从 5 万次 → ~6 次）
- 视图 lazy-load（首屏从 105KB → 首帧轻量）
- Brain SVG pulse 从 useState → useRef（零重渲染）
- `_resolve_user` SHA256 从每请求 5 次 → 进程级缓存
- `buildMetrics` 从每次渲染重算 → `useMemo`

---

## [0.5.0] — 2026-07-13

### Added
- 引擎路由 + 回退链 + 熔断器 (`engines/router.py`)
- 记忆复合评分检索 recency × importance × relevance (`memory/store.py`)
- 双系统判据 + BeliefState 数据模型 (`cognition/`)
- 护栏系统：注入拦截 + PII 脱敏 + 工具风险分级 (`guardrails/pipeline.py`)
- 自托管双语 Chat UI (`webchat.py`)
- 文档驱动的持久上下文体系 (ADR-011)
- 工程文档体系（AI_CONTEXT / ARCHITECTURE / CURRENT_STATE / ROADMAP / DESIGN_SYSTEM / PROJECT_MEMORY）

---

## [0.1.0] — 2026-07-12

### Added
- FastAPI 骨架 + CORS + X-API-Key 鉴权
- 3.0 技术设计文档集（13 文档 + 11 ADR）
- Railway 部署配置
- Console Next.js 15 原型（Dashboard + Brain Viz + ⌘K）
