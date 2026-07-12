# ADR-010 · 起步本地零配置存储

**状态**：采纳（本个性化设计新增）

## 背景
1.0 文档规划了 Redis + Postgres + ChromaDB 三存储，但对个人项目起步而言部署门槛高。需在「立即可跑」与「生产可扩展」间取舍。同时用户重视隐私，本地处理是长期方向。

## 考虑方案
- A) 直接上生产栈（Redis+PG+Milvus+K8s）：能力强但起步部署重、迭代慢、过度设计。
- B) **本地零配置起步（SQLite + ChromaDB + 进程内缓存），生产栈作为文档化演进路径**。
- C) 纯内存：最简但重启丢数据，不可用于持续心智。

## 决策
选 **B**。backend 起步用 SQLite（结构化 + 审计）+ ChromaDB（向量）+ 进程内工作记忆，`pip install` 即跑。生产选型（Postgres/Redis/Milvus/Neo4j/K8s）写入 [10-model-routing-and-infra](../10-model-routing-and-infra.md) 作为演进路径。

## 理由
- Anthropic「Start Simple, Scale Intelligently」：复杂度与已验证价值成正比。
- 个人项目要能「今天就跑起来」验证核心闭环（引擎路由 + 记忆 + 双系统）。
- 存储经抽象接口访问，起步→生产切换不改上层。
- 本地存储天然契合隐私优先（敏感记忆本地留存）。
