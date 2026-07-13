# AI_CONTEXT.md · Sunday OS 项目唯一入口

> **所有 AI Agent（Claude Code / ChatGPT / Cursor / 任何接入本项目的智能体）的唯一入口。** 开始工作前，先读本文件。不要依赖聊天历史——上下文以本文档体系为准。

**版本** 2.0 · **最后更新** 2026-07-13 · **维护者** AI Software Architect

---

## 0. 这是什么项目

**Sunday OS** —— 个人 AI 操作系统层。

> Sunday is not an AI for one task. It is one mind for every task.

核心理念：**身份 ≠ 模型**。Sunday 的身份来自 Memory + Personality + Goals + Planning + Cognitive Architecture。LLM 只是可随时替换的「认知引擎」。今天用 DeepSeek、明天换 Claude，Sunday 还是 Sunday。

七条地基原则（任何提案必须通过这七条的检验）：
1. 身份 ≠ 模型
2. 混合多供应商，动态路由
3. 一个心智，四大角色（情绪伴侣 · 生活秘书 · 编码搭档 · 学习伙伴）
4. GitHub 是 source of truth
5. 多端一等公民（iPhone / 桌面 / 云）
6. 渐进式演进——复杂度与已验证价值成正比
7. 安全内置、可解释、可审计

---

## 1. 仓库布局

```
SundayOS/
├── SUNDAY_CONTEXT.md          # 项目全貌（人类可读的概述）
├── CLAUDE.md                  # Claude Code 工程约定（运行命令/安全红线）
├── AGENTS.md                  # AI Agent 角色定义与协作协议
├── docs/                      # ★ 权威文档体系
│   ├── AI_CONTEXT.md          #   ← 本文件：唯一入口
│   ├── ARCHITECTURE.md        #   系统架构（六层 + 引擎抽象层）
│   ├── CURRENT_STATE.md       #   当前开发状态（诚实评估）
│   ├── ROADMAP.md             #   开发路线图
│   ├── DESIGN_SYSTEM.md       #   设计规范与改进建议
│   ├── PROJECT_MEMORY.md      #   已完成的重大设计决策
│   ├── adr/                   #   架构决策记录（ADR 索引）
│   ├── guides/                #   使用与操作手册
│   │   ├── BACKEND_USAGE.md   #     后端运行/配置/排错
│   │   └── DEPLOY_RAILWAY.md  #     Railway 部署指南
│   └── 3.0/                   #   实现级技术规范（13 文档 + 10 ADR）
├── backend/                   # FastAPI 参考实现（Python 3.11+）
├── console/                   # Next.js 15 Web 控制台（前端原型）
└── 1.0/                       # 历史文档（仅文档，无代码）
```

---

## 2. 文档阅读指南——什么时候该读什么

### 每次会话必读

| 优先级 | 读什么 | 为什么 |
|--------|--------|--------|
| ① | **本文件**（AI_CONTEXT.md） | 建立项目全局认知 |
| ② | **CURRENT_STATE.md** | 知道现在做到哪了、什么能跑、什么还不能 |
| ③ | **PROJECT_MEMORY.md** | 所有重大决策的索引，避免重蹈覆辙 |

### 按任务类型选读

| 你的任务 | 必须读 | 选读 |
|----------|--------|------|
| 写后端代码 | ARCHITECTURE.md §2-4 · CURRENT_STATE.md §3 | docs/3.0/ 对应章节 |
| 写前端代码 | DESIGN_SYSTEM.md · CURRENT_STATE.md §4 | console/src/ 现有代码 |
| 做架构决策 | ARCHITECTURE.md · PROJECT_MEMORY.md | docs/adr/ 索引 → 相关 ADR |
| 规划路线 | ROADMAP.md · CURRENT_STATE.md | docs/3.0/12-roadmap.md |
| 设计 UI/UX | DESIGN_SYSTEM.md | console/src/app/globals.css · tailwind.config.ts |
| 写测试 | CURRENT_STATE.md §3 | backend/tests/ 现有测试 |
| 部署/运维 | docs/guides/DEPLOY_RAILWAY.md · docs/guides/BACKEND_USAGE.md | — |
| 安全审查 | ARCHITECTURE.md §6 · PROJECT_MEMORY.md §4 | docs/3.0/08-security-and-autonomy.md |
| 新成员入职 | 本文件 → CURRENT_STATE.md → ARCHITECTURE.md | SUNDAY_CONTEXT.md（理解理念） |

### 文档层级关系

```
AI_CONTEXT.md （唯一入口）
  ├── 指向 → CURRENT_STATE.md    （什么时候需要了解现状）
  ├── 指向 → ARCHITECTURE.md     （什么时候需要理解架构）
  ├── 指向 → ROADMAP.md          （什么时候需要规划未来）
  ├── 指向 → DESIGN_SYSTEM.md    （什么时候需要设计规范）
  ├── 指向 → PROJECT_MEMORY.md   （什么时候需要查历史决策）
  └── 指向 → docs/adr/           （什么时候需要深究某个决策的理由）
```

---

## 3. 工程红线

1. **绝不硬编码密钥。** 一律 `.env` + 环境变量。`.env` 已在 `.gitignore`。
2. ⚠️ `readme.txt` / `其他.txt` 含明文真实 API Key——提醒用户轮换，不要把值写进任何代码或文档。
3. 高风险操作（删文件/支付/权限/删库）先向用户确认。
4. 不做破坏性 git 操作（force push / reset --hard）除非用户明确要求。
5. 不把代码/密钥发往第三方，除非用户明确要求。
6. 修改核心逻辑（路由/记忆/双系统/护栏）必须补/跑 `pytest`。

## 4. 如何更新文档

当以下发生时，必须同步更新：

| 变化 | 更新哪份文档 |
|------|------------|
| 架构变化 | ARCHITECTURE.md + 新增 ADR |
| 功能完成/进度变化 | CURRENT_STATE.md + ROADMAP.md |
| 重大决策 | PROJECT_MEMORY.md + 新增 ADR |
| 设计规范变化 | DESIGN_SYSTEM.md + globals.css + tailwind.config.ts |
| 新增关键依赖/文件 | CURRENT_STATE.md §2（文件清单） |

## 5. 术语速查

| 术语 | 含义 |
|------|------|
| 认知引擎 (Cognitive Engine) | 可替换的 LLM。经 L1.5 抽象层统一接入 |
| Talker / Reasoner | 系统1（快思考，常在线）/ 系统2（慢思考，按需激活） |
| Memory Stream | 按时间记录全部交互的记忆流 |
| Reflection / Experience | 记忆三层递进的中层（反思洞察）/ 高层（跨轨迹抽象） |
| Belief State | Reasoner 维护的结构化用户信念模型 |
| 预算化自主 | 按风险自适应调整规划深度、验证强度、引擎档位 |
| CPS | Conversation-turns Per Session，核心参与度指标 |
| 真源 (Source of Truth) | GitHub 上版本化的人格/技能/稳定偏好 |
| RouteTrace | 一次引擎路由决策的可追溯记录 |
| Provider | 认知引擎的抽象基类，所有模型供应商实现此接口 |
