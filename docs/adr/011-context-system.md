# ADR-011 · 文档驱动的持久上下文体系

**状态**：采纳（2026-07-13，长期上下文体系建立时的首条项目级决策）

## 背景
Sunday OS 是长期演进的项目，会有多个 AI Agent（Claude Code / ChatGPT / Cursor 等）在不同会话、不同时间接入。若上下文依赖聊天历史：
- 历史会被截断、丢失、无法跨 Agent 共享。
- 新会话/新 Agent 无法快速对齐理念与现状。
- 决策理由散落在对话里，无法追溯。

用户明确要求：**建立永久开发上下文，每次启动优先读文档而非依赖聊天历史。**

## 方案
- A) 依赖聊天历史 + 偶尔口头总结。
- B) 单一巨型 README 塞入全部信息。
- C) **分层文档上下文体系**：根级「首读入口」（SUNDAY_CONTEXT / CLAUDE / AGENTS）+ 权威层（docs/ARCHITECTURE / DESIGN_SYSTEM / ROADMAP / adr）+ 实现层（docs/3.0/*）。

## 决策
选 **C**。确立三层文档体系与固定启动流程：任何 Agent 先读 SUNDAY_CONTEXT.md → 角色（AGENTS.md）→ 按需查 docs/。设「活文档纪律」：架构/决策/进度变化即时同步对应文件。设立长期 **AI Software Architect** 角色守护该体系。

## 理由
- 上下文成为**可版本化、可审计、可跨 Agent 共享**的项目资产，与 [ADR-009 GitHub 真源](../3.0/adr/009-github-source-of-truth.md) 一脉相承——身份与知识都不依赖易失的会话。
- 分层避免单文件臃肿：入口层快速对齐，实现层承载细节，各司其职。
- 单一真相原则：同一事实只在一处权威定义，其余引用，减少矛盾。

## 影响
- 新增/维护：`SUNDAY_CONTEXT.md`、`CLAUDE.md`、`AGENTS.md`、`docs/README.md`、`docs/ARCHITECTURE.md`、`docs/DESIGN_SYSTEM.md`、`docs/ROADMAP.md`、`docs/adr/`、`docs/guides/`。
- 纪律约束：此后所有 Agent 遵守启动流程与活文档纪律（见各文件与 AGENTS.md 通用协议）。
- 不改任何业务代码（本次仅建文档体系）。
