# Changelog

> Sunday OS 版本记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
>
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：**MAJOR.MINOR.PATCH**
>
> - **MAJOR**：架构变更、不兼容的 API 修改、核心理念调整
> - **MINOR**：新功能（向后兼容）
> - **PATCH**：Bug 修复、性能优化、文档更新

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
