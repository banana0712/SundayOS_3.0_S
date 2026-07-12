# SUNDAY_CONTEXT.md

> **所有 AI Agent 的首读文档。** 无论你是 Claude Code、ChatGPT、Cursor、还是任何接入本项目的智能体，开始工作前**先读本文件**，再读你的角色说明（[AGENTS.md](AGENTS.md)），然后按需查阅 [docs/](docs/)。**不要依赖聊天历史**——上下文以文档为准。

**文档版本**：1.0 · **最后更新**：2026-07-13 · **维护者**：AI Software Architect（长期角色，见 AGENTS.md）

---

## 0. 一句话

Sunday OS 是一个个人 AI 操作系统层。**"Sunday is not an AI for one task. It is one mind for every task."**

## 1. 核心理念（不可动摇的地基）

1. **身份 ≠ 模型。** Sunday 的身份来自 **Memory + Personality + Goals + Planning + Cognitive Architecture**。LLM 只是可随时替换的「认知引擎」。今天用 DeepSeek、明天换 Claude，Sunday 还是 Sunday。
2. **混合多供应商。** 统一模型抽象层之上，按 **复杂度 × 延迟 × 成本 × 隐私 × 可用性** 动态路由。不绑定任何单一模型或厂商。
3. **一个心智，四大角色。** 情绪伴侣 · 生活秘书 · 编码搭档 · 学习伙伴——同一心智在不同认知配置下的表现，共享同一份记忆/人格/目标。
4. **GitHub 是 source of truth。** 人格、技能、稳定偏好版本化在 Git；Sunday 编排各连接的 AI 服务，但真相在仓库里。
5. **多端一等公民。** iPhone/iPad、桌面、云都是同一心智的窗口。
6. **渐进式演进。** 复杂度必须与已验证的价值成正比。先骨架，后血肉。
7. **安全内置、可解释、可审计。** 护栏嵌入执行循环；每个决策可追溯。

> 这七条是判断任何提案是否「符合 Sunday」的试金石。与之冲突的设计，默认拒绝或先讨论。

## 2. 当前状态（Where we are）

| 领域 | 状态 | 位置 |
|------|------|------|
| 3.0 技术设计文档集 | ✅ 完成（13 文档 + 10 ADR + 附录） | [docs/3.0/](docs/3.0/) |
| 后端参考实现 | 🟡 Phase 1 骨架可运行（引擎路由/三层记忆/双系统雏形/护栏；28 测试通过） | [backend/](backend/) |
| Web 控制台 | 🟡 Dashboard + Brain 可视化 + ⌘K 外壳（前端原型，未接后端） | [console/](console/) |
| 上下文文档体系 | ✅ 本次建立（本文件 + CLAUDE.md + AGENTS.md + docs/） | 仓库根 + docs/ |
| iPhone 集成 | 📄 仅设计（1.0 有 Shortcuts 方案文档） | [docs/3.0/09](docs/3.0/09-api-and-integration.md) |

**后端诚实边界**：记忆仅在内存（重启即失）；Reasoner 的 ReAct 工具执行、反思引擎、Experience 层、持久化尚未实现；未配 API Key 时用 mock 引擎产生确定性占位回复。详见 [docs/guides/BACKEND_USAGE.md](docs/guides/BACKEND_USAGE.md)。

## 3. 架构速览

六层 + 独立的认知引擎抽象层（L1.5）：

```
L6 安全治理  | 六层护栏 · 预算化自主 · 隐私 · 审计
L5 应用技能  | 技能注册 · 工具路由 · 四角色配置
L4 交互人格  | 共情计算(CQU/UU/IRG) · 人格锚定 · 对话管理
L3 认知引擎  | 双系统(Talker+Reasoner) · ReAct · 规划器 · 反思
L1.5 引擎抽象| ★ 统一 Provider 接口 · 动态路由（复杂度×成本×延迟×隐私×可用性）
L2 数据记忆  | Storage → Reflection → Experience 三层递进
L1 基础设施  | 向量库 · 结构化库 · 缓存 · GitHub(真源)
```

完整架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，实现级细节见 [docs/3.0/](docs/3.0/)。

## 4. 关键决策（Why it is the way it is）

所有重大决策记录在 [docs/adr/](docs/adr/)。最该先知道的：
- **ADR-008 认知引擎抽象层**：模型可替换是头号原则。
- **ADR-009 GitHub 作为真源**：身份状态版本化。
- **ADR-001 双系统认知**、**ADR-002 三层记忆**、**ADR-003 ReAct**、**ADR-010 本地优先存储**。

## 5. 文档地图（读什么去哪）

| 你想… | 读 |
|-------|----|
| 理解项目全貌与理念 | 本文件 |
| 作为 AI Agent 明确职责 | [AGENTS.md](AGENTS.md) |
| 作为 Claude Code 干活 | [CLAUDE.md](CLAUDE.md) |
| 看系统架构 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 看实现级规范（引擎/记忆/双系统等） | [docs/3.0/](docs/3.0/) |
| 看设计规范（配色/组件/动效） | [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) |
| 看开发路线与当前进度 | [docs/ROADMAP.md](docs/ROADMAP.md) |
| 看关键决策及理由 | [docs/adr/](docs/adr/) |
| 跑起来后端 | [docs/guides/BACKEND_USAGE.md](docs/guides/BACKEND_USAGE.md) |

## 6. 术语表（Glossary）

| 术语 | 含义 |
|------|------|
| 认知引擎 (Cognitive Engine) | 可替换的 LLM。经 L1.5 抽象层统一接入。 |
| Talker / Reasoner | 系统1（快思考，常在线）/ 系统2（慢思考，按需激活）。 |
| Memory Stream | 按时间记录全部交互的记忆流；检索用 recency×importance×relevance。 |
| Reflection / Experience | 记忆三层递进的中层（反思洞察）/ 高层（跨轨迹抽象）。 |
| Belief State | Reasoner 维护的结构化用户信念模型。 |
| 预算化自主 | 按风险自适应调整规划深度、验证强度、引擎档位。 |
| CPS | Conversation-turns Per Session，核心参与度指标。 |
| 真源 (Source of Truth) | GitHub 上版本化的人格/技能/稳定偏好。 |
| RouteTrace | 一次引擎路由决策的可追溯记录。 |

## 7. 安全红线

- ⚠️ **绝不硬编码密钥。** 一律 `.env` + 环境变量。当前 `readme.txt` / `其他.txt` 含明文真实 Key，**待轮换 + 加 .gitignore**。
- 不把项目代码/密钥/用户数据发往未经用户明确同意的第三方。
- 高风险操作（删除、支付、权限变更）必须人工确认（HITL）。
- 处理敏感记忆优先本地引擎与本地存储。

## 8. 更新纪律

本上下文体系是**活文档**。当以下发生时，负责的 Agent 必须同步更新对应文件：
- 架构变化 → 更新 ARCHITECTURE.md + 新增 ADR。
- 重大决策 → 新增 ADR，并在本文件 §4 提及。
- 进度推进 → 更新本文件 §2 与 ROADMAP.md。
- 新增 Agent 角色 → 更新 AGENTS.md。
