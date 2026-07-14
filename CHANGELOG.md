# Changelog

> Sunday OS 版本记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
>
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：**MAJOR.MINOR.PATCH**
>
> - **MAJOR**：架构变更、不兼容的 API 修改、核心理念调整
> - **MINOR**：新功能（向后兼容）
> - **PATCH**：Bug 修复、性能优化、文档更新

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
