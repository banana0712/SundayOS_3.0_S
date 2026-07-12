# SundayOS 3.0 · 技术文档集

> **"Sunday is not an AI for one task. It is one mind for every task."**
>
> Sunday 的身份来自 Memory、Personality、Goals、Planning 与 Cognitive Architecture —— 而非任何单一 LLM。大模型只是可随时替换的「认知引擎」。

本文档集是 SundayOS 3.0 的**个性化架构规范与实现指南**。它在《SundayOS 3.0 架构设计计划》（17 篇论文综合蓝图）之上，做了三件事：

1. **落地到实现级**：把论文中的公式、阈值、prompt 格式、护栏流水线、评估指标写成可直接编码的规范。
2. **个性化重构**：围绕你的四大角色（情绪伴侣 · 生活秘书 · 编码搭档 · 学习伙伴）与「一个心智服务全部任务」的理念组织架构。
3. **可运行验证**：配套 `backend/` 参考实现（认知引擎路由 + 三层记忆 + 双系统 + 护栏）。

## 阅读顺序

| # | 文档 | 内容 | 读者 |
|---|------|------|------|
| 01 | [愿景与个性化](01-vision-and-personalization.md) | 为什么是 Sunday，四角色，你的适配 | 所有人 |
| 02 | [系统架构](02-system-architecture.md) | 六层架构、数据流、组件交互 | 架构 / 工程 |
| 03 | [★认知引擎层](03-cognitive-engine-layer.md) | 统一模型抽象 + 动态路由（**核心差异点**） | 工程 |
| 04 | [记忆系统](04-memory-system.md) | Storage→Reflection→Experience 三层递进 | 工程 |
| 05 | [双系统认知](05-dual-process-cognition.md) | Talker+Reasoner、ReAct、信念状态 | 工程 |
| 06 | [人格与共情](06-personality-and-empathy.md) | 人格锚定 + 共情计算 CQU/UU/IRG | 工程 / 产品 |
| 07 | [技能与工具](07-skills-and-tools.md) | 技能生命周期、工具三类型、MCP | 工程 |
| 08 | [安全与自主](08-security-and-autonomy.md) | 六层护栏 + 预算化自主 + 隐私 | 安全 / 工程 |
| 09 | [API 与集成](09-api-and-integration.md) | REST/SSE/WS、iPhone、GitHub 真源、多端 | 工程 / 客户端 |
| 10 | [模型路由与基础设施](10-model-routing-and-infra.md) | L1-L4 路由表、选型、可观测性 | 运维 / 工程 |
| 11 | [评估体系](11-evaluation.md) | 19 指标评估向量 + CPS | 产品 / QA |
| 12 | [实施路线图](12-roadmap.md) | Phase 1-4 里程碑 | 所有人 |
| — | [ADR 架构决策记录](adr/) | 关键决策及理由 | 架构 |
| — | [论文实现级精华](appendix-paper-insights.md) | 公式/数字/prompt 依据 | 工程 |

## 设计原则（一句话版）

1. **记忆优先** —— 一切认知能力建立在统一记忆基础设施上。
2. **引擎可替换** —— 身份与模型解耦；模型是引擎，不是灵魂。
3. **双系统认知** —— 快思考常在线，慢思考按需激活。
4. **IQ+EQ+人格三位一体** —— 区分「工具」与「伙伴」。
5. **渐进式演进** —— 复杂度必须与已验证的价值成正比。
6. **安全内置** —— 护栏嵌入执行循环，而非事后附加。
7. **可解释可审计** —— 每个决策都有可追溯的思维链。
8. **体验驱动进化** —— 从「记录」到「抽象」的认知飞跃。

## 配套实现

参考实现见 [`../../backend/`](../../backend/)。它验证了本文档最核心的三块：认知引擎路由、三层记忆检索评分、双系统切换，以及六层护栏。运行方式见 backend 的 README。

## 安全须知

⚠️ 仓库根目录的 `readme.txt` / `其他.txt` 含**明文真实 API Key**。请**立即轮换**并加入 `.gitignore`。本项目所有密钥一律经 `.env` + 环境变量注入，永不硬编码。
