# 10 · 模型路由与基础设施

## 10.1 L1-L4 模型路由表

据任务复杂度、延迟、成本、隐私、可用性动态选择（详见 [03](03-cognitive-engine-layer.md)）：

| 层级 | 任务类型 | 引擎选择 | 延迟目标 | 成本 |
|------|---------|---------|---------|------|
| L1 即时 | 意图分类、情感分析、简单问答 | 本地(Ollama) / DeepSeek-Chat | <100ms（本地）/<500ms | 极低 |
| L2 日常 | 对话、检索、摘要 | DeepSeek-Chat / Qwen-Plus / Ling | <800ms | 低 |
| L3 深度 | 多步规划、复杂决策、代码 | Claude Opus / GPT-4o / DeepSeek-Reasoner | <3s | 中 |
| L4 关键 | 高风险、合规、安全验证 | 最强模型 + 验证器 + 人工确认 | <5s | 高 |

路由决策流程：
1. 复杂度分类器（轻量引擎）评估任务 → 分配层级。
2. 预算化自主据风险 + token 预算调整选择。
3. 回退：L3 超时/不确定 → 回退 L2 + 用户确认。
4. 边缘优先：可离线任务优先本地引擎（隐私 + 低延迟）。

## 10.2 技术选型

| 域 | 起步（本地零配置） | 生产 | 理由 |
|----|------------------|------|------|
| 后端框架 | FastAPI + Uvicorn | 同 | 延续 1.0，异步、类型安全 |
| 引擎 SDK | openai / anthropic SDK | + google-genai | OpenAI 兼容覆盖多数 |
| 向量库 | ChromaDB | Milvus / Pinecone | 起步零依赖，生产可扩展 |
| 结构化库 | SQLite | Postgres | 起步单文件 |
| 知识图谱 | —（延后） | Neo4j | 逻辑约束推理 |
| 缓存 | 进程内 | Redis | 工作记忆热数据 |
| 消息队列 | —（延后） | Kafka / RabbitMQ | 异步事件驱动 |
| API 网关 | —（延后） | Kong / Envoy | 限流、认证 |
| 护栏 | 内置流水线 | + AutoHarness 自研 | 自动合成验证代码 |
| 可观测 | 结构化日志 | OpenTelemetry + Grafana + Prometheus | 全链路追踪、token 监控 |
| 审计 | SQLite 追加表 | ClickHouse / ELK | 不可变日志 |
| 部署 | 单机 / Railway | Kubernetes + GPU | 弹性伸缩 |

**起步原则**：最小依赖跑通（SQLite + Chroma + FastAPI），生产选型作为演进路径，避免过度设计（Anthropic「Start Simple」）。

## 10.3 可观测性栈

必须超越普通日志，覆盖 Agent 特有维度：
- **提示链 / 决策路径 / 检索上下文** 可视化。
- **Token 消耗** 按引擎/角色/请求维度统计（对接成本核算）。
- **RouteTrace**：每次引擎路由决策可追溯（[03](03-cognitive-engine-layer.md) §3.7）。
- **ReAct 轨迹回放**：Thought/Action/Observation 全序列。
- 对接 Console 的 Dashboard / Cognitive Engine / Developer 视图。

## 10.4 上下文管理

- 工具响应上限 **~25,000 token**，防上下文耗尽。
- **上下文编辑**：接近 token 上限时自动清理陈旧工具调用/结果，保留流程连续性。
- 工具级分页、范围选择、过滤、截断，设合理默认。

## 10.5 成本预算参考

- 多 Agent 消耗 **10-15×** 单 Agent token —— 默认单 Agent。
- Reflexion ≈ **2×** ReAct token —— 仅失败时触发。
- 日常走免费/低价引擎（DeepSeek/Ling/Qwen），强模型按需 —— 与四角色天然契合。
