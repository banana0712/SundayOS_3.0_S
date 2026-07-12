# SundayOS 3.0 · Backend

> One mind for every task. 参考实现，验证 3.0 设计最核心的四块：
> **认知引擎路由 · 三层记忆检索 · 双系统切换 · 六层护栏**。

对应设计文档：[`../docs/3.0/`](../docs/3.0/)。本实现覆盖路线图 Phase 1 的引擎层 + 记忆 + 双系统雏形 + 护栏。

## 特点

- **零外部依赖起步**（ADR-010）：无需 Redis/Postgres/向量服务。未配任何 API Key 时自动进入 **mock 模式**（确定性、离线），可直接跑通记忆/路由/双系统/护栏。
- **模型即引擎**（ADR-008）：新增引擎 = 写一个 `EngineProvider` 子类 + 在 `registry.py` 登记能力/价格，零改上层。
- **纯逻辑可测**：检索评分、路由决策、双系统切换、护栏均为纯函数，28 个单测全部离线通过。

## 快速开始

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env          # 可选：填入 DeepSeek/Claude 等 Key；不填则 mock 模式

# 运行测试（离线，无需任何 Key）
python -m pytest -q            # → 28 passed

# 启动服务
export SUNDAY_API_KEY=dev-key  # Windows: set / $env:
python -m uvicorn app.main:app --port 8000 --reload
```

## 试一试

```python
import httpx
h = {"X-API-Key": "dev-key"}
# 简单问候 → 系统1 (talker) + 便宜引擎
httpx.post("http://localhost:8000/api/chat", headers=h,
           json={"message": "你好呀", "user_id": "me"}).json()
# 多步任务 → 系统2 (reasoner) + 强引擎
httpx.post("http://localhost:8000/api/chat", headers=h,
           json={"message": "先查天气然后订酒店最后生成旅行计划", "user_id": "me"}).json()
```

响应包含 `engine`（本轮用了哪台引擎）、`system`（talker/reasoner）、`complexity`、`risk`、`trace`（路由候选/打分/回退/用量）——引擎透明，一眼看清「这次谁在思考」。

## 结构

```
app/
  engines/        认知引擎层 (L1.5)
    base.py         EngineProvider 抽象 + 能力/复杂度
    providers.py    OpenAICompatible(DeepSeek/Qwen/OpenAI/Ollama) + Anthropic + Mock
    router.py       复杂度分类 + 预算化打分 + 回退链 + 熔断
    registry.py     从环境变量构建引擎集
  memory/         记忆系统 (L2)
    schema.py       MemoryNode + 有效重要性衰减
    embedding.py    可插拔嵌入（默认离线哈希嵌入）
    store.py        复合检索评分 α·recency+β·importance+γ·relevance
  cognition/      认知 (L3)
    belief.py       信念状态
    dispatch.py     双系统切换判据
  guardrails/     安全 (L6)
    pipeline.py     输入护栏 + PII 脱敏 + 工具风险分级
  main.py         FastAPI：/api/chat /api/memory /api/engines /health
tests/            28 个离线单测
```

## 从 mock 切到真实引擎

在 `.env` 填入任一 Key（如 `DEEPSEEK_API_KEY`），重启即可。`registry.py` 会自动实例化已配置的引擎并纳入路由。**绝不硬编码密钥**——一律走 `.env` + 环境变量。

## 下一步（Phase 2）

反思引擎（记忆 L1→L2）、共情计算 CQU/UU/IRG、Reasoner 的 ReAct 循环 + 工具执行、Skill Registry、SQLite/Chroma 持久化。详见 [`../docs/3.0/12-roadmap.md`](../docs/3.0/12-roadmap.md)。
