# ROADMAP.md · Sunday OS 开发路线图

> 基于当前实际进度（见 [CURRENT_STATE.md](CURRENT_STATE.md)）制定的开发计划。

**版本** 1.1 · **最后更新** 2026-07-15

---

## 0. 进度快照

| 里程碑 | 状态 | 完成度 |
|--------|------|--------|
| 工程文档体系 | ✅ | 10 文件 + ADR 索引 + 调试说明书 |
| Phase 1 · 心智骨架 | ✅ | ~95% |
| Phase 1.5 · 反馈学习系统 (ADR-012) | 🟡 | ~60%（今晚完成核心通路） |
| Phase 2 · 认知增强 | ⬜ | 0% |
| Phase 3 · 体验进化 | ⬜ | 0% |

### 2026-07-15 变更摘要

| 模块 | 状态 | 说明 |
|------|------|------|
| 偏好档案存储 | ✅ | UserPreferences + PreferenceStore (SQLite) |
| NL 反馈解析器 | ✅ | LLM 驱动的 parse_feedback() |
| 偏好注入 prompt | ✅ | build_prompt_with_prefs() → 每次聊天自动注入 |
| 反馈 API | ✅ | POST /api/feedback + GET /api/preferences |
| 反馈 UI | ✅ | webchat 👍👎 按钮 + 文字反馈 |
| ADR-012 | ✅ | 完整架构决策文档 |
| 移动端重设计 | ✅ | 底部导航、sidebar overlay、键盘适配、44px 触摸 |
| 豆包引擎 | ✅ | sunday-chat (quality=0.85, primary=True) → 火山引擎 |
| 质量优先路由 | ✅ | ADR-011: L2 日常质量权重 40%、成本 10% |
| 运行日志 | ✅ | 结构化 JSON logger + /api/debug/routing 调试端点 |

### 长期路线图

#### Phase 2：隐式行为信号（当前未实现）
- [ ] 重问同样问题 → 自动 👎 信号
- [ ] 秒回下一条 → 自动 👍 信号
- [ ] 语义漂移检测（切话题 = 对上一个回复不满意）
- [ ] SSF（Self-Supervised Feedback）：AI 自评回复质量

#### Phase 3：闭环验证（当前未实现）
- [ ] CPS 跟踪面板：反馈前后对话轮次变化
- [ ] 偏好衰减：30 天未确认 → confidence → 0
- [ ] A/B 对比：同一 prompt 不同引擎输出对比

#### Phase 4：全栈自适应（当前未实现）
- [ ] Per-scenario 偏好矩阵（早晨 vs 晚上）
- [ ] 隐式偏好发现：LLM 定期分析聊天记录
- [ ] 偏好冲突检测与提醒

---

## Phase 1 · 心智骨架（MVP）🟡 ~85%

**目标**：验证「引擎可替换 + 记忆 + 对话」核心闭环。

### 已完成

| 模块 | 交付物 | 验证方式 |
|------|--------|---------|
| 认知引擎层 | Provider 抽象 + 4 引擎 + 动态路由 + 回退链 + 熔断 | 11 测试 + RouteTrace 可见 |
| 记忆 L1 Storage | Memory Stream + 复合评分检索 + **SQLite 持久化** + **语义 embedding（Qwen text-embedding-v3）+ 启动自动重嵌入** | 24 测试 + API 可调用 |
| 记忆 L2 Reflection | 反思引擎（Generative Agents 两步流程） | 自动触发 + 手动 API + 测试 |
| LLM 重要性打分 | Generative Agents 论文 1-10 自动评分 | chat 端点内联，异步非阻塞 |
| 双系统判据 | needs_reasoner() + risk_level() + BeliefState 数据模型 | 6 测试 |
| **ReAct 循环** | Thought→Action→Observation + 4 工具 + 护栏门控 | 9 测试 + react_steps 轨迹 |
| **SSE 流式** | `/api/chat/stream` + webchat + console 双前端消费 | 浏览器可见逐字/逐步输出 |
| 护栏基础 | L2-L4 规则（注入/越狱/长度）+ L3 PII 脱敏 + L5 工具风险 | 4 测试 |
| Chat UI | 双栏布局（会话侧边栏 + 聊天区）+ 4 视图切换 | 浏览器打开即用 |
| Console | Dashboard 实时数据 + Brain + Memory Center + Chat 流式 | 前端构建通过 |
| 会话管理 | ConversationStore + 6 端点 + **SQLite 持久化（跨重启存活）** + webchat/console 侧边栏 | 16 测试 |
| 调试体系 | `/api/debug/overview` + Swagger UI + 调试面板 + DEBUGGING.md | 文档 + API |
| 部署 | Railway 一键部署 | 已配置 |

### 待完成（仅剩 2 项）

| # | 项目 | 工作量 | 说明 |
|---|------|--------|------|
| 1 | web_search 真实实现 | 小（1h） | 当前是占位符，需接搜索 API Key |
| 2 | Ollama 本地引擎验证 | 小（1h） | Provider 已定义，需验证 + 文档 |
| 诊断工具 | `/api/debug/env` + RouteTrace errors 字段 | API 可调用 |
| 部署 | Railway 一键部署 | 已配置 |

### 待完成（按优先级排序）

#### 🔴 P0 — 记忆持久化（SQLite + ChromaDB）
- **为什么优先**：记忆仅内存，重启即失——这是"身份连续性"的前提。没有它，Sunday 就是无记忆的聊天机器人。
- **工作量**：中（3-5h）
- **依赖**：无阻塞依赖。MemoryStore 已有清晰接口，只需实现 SQLite 子类 + ChromaDB 向量存储。
- **验收**：重启后端后记忆仍在；1000+ 条记忆检索 < 200ms。
- **对应 ADR**：[ADR-010](3.0/adr/010-local-first-storage.md)

#### 🔴 P0 — Reasoner 的 ReAct 循环 + 真实工具执行
- **为什么优先**：系统2 目前只是"路由到强引擎直接回答"，Sunday 还不是 Agent。ReAct 是实现"能做事"的前提。
- **工作量**：大（6-10h）
- **依赖**：记忆持久化（更优体验，非硬依赖）
- **子任务**：
  1. ReAct 循环框架（Thought → Action → Observation → 更新 Belief → 循环 → finish）
  2. 3-5 个核心工具（搜索/browser/计算器/文件读/天气查询）
  3. 工具执行器 + 结果注入记忆
  4. 最大步数限制 + 超时
- **验收**：用户说"先查天气然后订酒店" → Sunday 实际调用工具 → 返回结果
- **对应 ADR**：[ADR-003](3.0/adr/003-react-loop.md)

#### 🟡 P1 — 反思引擎（记忆 L1→L2）
- **依赖**：记忆持久化
- **工作量**：中（3-4h）
- **验收**：高频交互模式被自动抽象为 insight；用户画像自动更新
- **对应 ADR**：[ADR-002](3.0/adr/002-three-tier-memory.md)

#### 🟡 P1 — Console 接后端真实数据
- **依赖**：后端 API 已就绪（`/api/chat`, `/api/memory/search`, `/api/engines`）
- **工作量**：中（3-5h）
- **子任务**：
  1. 创建 API client 层（`console/src/api/`）
  2. Dashboard 指标替换为真实数据
  3. Brain Visualization 节点状态反映真实认知模块
  4. 健康检查轮询接入
- **验收**：Brain 页面显示真实引擎状态、记忆数量、最近记忆内容

#### 🟢 P2 — 其他收尾

| 项目 | 工作量 | 说明 |
|------|--------|------|
| SSE 流式端点（`/api/chat/stream`） | 中（2-3h） | 现有 `stream()` 方法已定义，需加端点 + 前端消费 |
| 意图/情感分类接真实引擎 | 中（2-3h） | 替换关键词启发式为 LLM 分类 |
| LLM 安全分类器（moderation） | 小（1-2h） | guardrails/pipeline.py 中接口已留空 |
| Ollama 本地引擎集成 | 小（1h） | Provider 已定义，需验证 + 文档 |

---

## Phase 2 · 认知增强 ⬜

**目标**：双系统完整化 + 情感 + 技能系统。

| 模块 | 交付 | 预估工作量 | 前置依赖 |
|------|------|-----------|---------|
| 双系统完整化 | Talker+Reasoner 分离进程 + 共享记忆总线 + Belief 持久化 | 大 | Phase 1 记忆持久化 |
| 共情计算 | CQU+UU+IRG 三段式共情 | 中 | 意图分类 |
| 人格系统 | Persona 初始化（从 `persona.yaml`） + 对话注入 | 中 | GitHub 真源 | 📋 已预留 |
| 技能系统 | Skill Registry + 10 核心技能 + 工具路由 | 大 | ReAct 循环 |
| 引擎路由升级 | L1-L3 分层路由 + 预算化选择完整化 | 中 | 引擎层已有 |
| iPhone 增强 | Widget 支持 + Shortcuts API 就绪（`/api/shortcuts/chat`） | 中 | 技能系统 |

---

## Phase 3 · 体验进化 ⬜

**目标**：Experience 层 + 人格演化 + 主动性。

| 模块 | 交付 | 说明 |
|------|------|------|
| Experience 层 | 跨轨迹抽象 + 程序原语 + 混合体验循环 | L2→L3 质变 |
| 人格演化 | Persona 反思更新 + 锚定机制 | 系统1/2 共享人格 |
| 主动探索 | 好奇心驱动 + 模式发现 + 主动建议 | 从被动到主动 |
| 树搜索 | 高风险决策 LATS | 替代简单 ReAct |
| GitHub 真源 | persona/skills/记忆快照版本化 + 跨设备同步 | 对应 ADR-009 |

---

## Phase 4 · 生态完善 ⬜

**目标**：技能生态 + 安全治理 + 生产就绪。

| 模块 | 交付 |
|------|------|
| 技能生态 | 50+ 技能 + 第三方 SDK |
| AutoHarness | 自动护栏合成流水线 |
| 评估体系 | 19 指标自动化管道 + 红队测试 |
| 多模态 | 图像/音频理解 + 生成 |
| 生产就绪 | K8s + Postgres + Redis + Milvus + 监控 + SLA 99.9% |

---

## 里程碑依赖图

```
Phase 1 MVP
├── 引擎路由 ✅
├── 记忆检索 ✅
├── 双系统判据 ✅
├── 护栏 ✅
├── Chat UI ✅
├── 记忆持久化 🔴 ← 当前最高优先
├── ReAct 循环 🔴 ← 当前最高优先
├── SSE 流式 🟡
└── Console 接后端 🟡
      ↓
Phase 2
├── 双系统完整化（依赖记忆持久化）
├── 反思引擎（依赖记忆持久化）
├── 共情计算（依赖意图分类）
├── 技能系统（依赖 ReAct）
└── iPhone 增强
      ↓
Phase 3
├── Experience 层（依赖反思引擎）
├── 人格演化（依赖 Experience 层）
└── GitHub 真源（依赖人格+记忆体系）
      ↓
Phase 4
├── 技能生态（依赖技能系统）
└── 生产就绪（依赖全部）
```

---

## 建议今天做的三件事

基于当前状态和依赖关系，每次开发会话可以从以下三项中选择（与 [CURRENT_STATE.md](CURRENT_STATE.md) §6 的阻塞项对应）：

1. **记忆持久化（SQLite + ChromaDB）** —— 最无争议的下一步，依赖为零，收益巨大。
2. **Reasoner 的 ReAct 循环 + 真实工具执行** —— 让 Sunday 从"会聊"到"能做"的质变。
3. **Console Brain Visualization 接后端真实数据** —— 让前端可视化反映真实心智，不再是 mock。
