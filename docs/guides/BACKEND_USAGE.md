# 后端使用说明书 · BACKEND_USAGE

> Sunday OS 后端（`backend/`）怎么跑、怎么接真实模型、能做什么、**不能**做什么、怎么排错。诚实版。

**对应实现** Phase 1 骨架 · **最后更新** 2026-07-13

---

## 0. 它现在是什么（先看这段）

`backend/` 是**可运行的 Phase 1 参考实现**，用来验证 Sunday OS 最核心的四块设计：认知引擎路由、三层记忆检索、双系统切换、六层护栏。28 个单元测试全部离线通过。

**它能做**：
- 启动一个 FastAPI 服务，提供对话 / 记忆 / 引擎状态接口。
- 按任务复杂度**动态路由**到不同「认知引擎」，并返回决策 trace。
- 会话内**记忆检索**（recency×importance×relevance 复合评分）。
- **双系统切换**：简单请求走 Talker，多步/高风险走 Reasoner 档位。
- **护栏拦截**：注入攻击、超长输入被挡；输出 PII 脱敏；工具风险分级。
- **未配任何 API Key 也能跑**（mock 模式，确定性离线回复）。

**它还不能做（诚实边界）**：
- ❌ 记忆**不持久化**——只在内存，进程重启即失（Phase 1 收尾项）。
- ❌ Reasoner 的 **ReAct 循环与真实工具执行未接**——现在系统2 只是路由到强引擎直接回，不会真去查天气/跑代码/改 GitHub。
- ❌ **反思引擎 / Experience 层 / 人格演化 / 共情计算**尚未实现（Phase 2-3）。
- ❌ 意图/情感分类目前是关键词启发式，非真实模型判断。
- ❌ mock 模式的回复是**占位回声**，不是真实智能——要真实回复必须配 Key。
- ❌ 无鉴权之外的多用户隔离、无速率限制生产化、无 SSE 流式端点（设计有，未实现）。

> 一句话：**能演示核心机制、能做真实对话（配 Key 后），但还不是能托管你日常生活的成品。** 进度见 [../ROADMAP.md](../ROADMAP.md)。

## 1. 前置

- Python 3.11+（已在 3.14 上验证通过）。
- 可选：DeepSeek / Qwen / OpenAI / Anthropic / Ollama 的任一 API Key（不配则 mock 模式）。

## 2. 安装与运行

```bash
cd backend
python -m pip install -r requirements.txt

# 跑测试（离线，无需 Key）——应显示 28 passed
python -m pytest -q

# 配置（可选）
cp .env.example .env        # 编辑填入 Key；不填即 mock 模式

# 启动
export SUNDAY_API_KEY=dev-key          # Windows Git Bash 亦同；PowerShell 用 $env:
python -m uvicorn app.main:app --port 8000 --reload
```

健康检查：
```bash
curl http://localhost:8000/health
# {"status":"ok","engines":["mock-fast","mock-strong"],"memory_nodes":0}
```

> Windows 提示：终端可能把中文输出显示成乱码（控制台按 GBK 解码 UTF-8），这是**显示问题**，服务内部处理的是正确 UTF-8。用 Python httpx 客户端测试可避免。

## 3. 接入真实引擎（从 mock 切到真智能）

在 `.env` 填入任一 Key，重启即可，`registry.py` 会自动实例化并纳入路由：

```env
# 例：只用 DeepSeek（中文性价比高）
DEEPSEEK_API_KEY=sk-你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 例：加上 Claude 做深度推理/编码
ANTHROPIC_API_KEY=sk-ant-你的key
```

配了之后：L1-L2 日常走 DeepSeek，L3-L4 深度走 Claude（若配置），完全由路由器按复杂度×成本×延迟×隐私自动选。

> ⚠️ **绝不把 Key 写进代码或提交到 Git**。`.env` 已在 `.gitignore`。仓库根 `readme.txt`/`其他.txt` 里的明文 Key 请尽快轮换。

## 4. API 速查

鉴权：所有 `/api/*` 需请求头 `X-API-Key: <你的 SUNDAY_API_KEY>`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康 + 引擎列表 + 记忆条数 |
| GET | `/api/engines` | 各引擎能力/价格 |
| POST | `/api/chat` | 对话（自动双系统 + 路由） |
| POST | `/api/memory/store` | 写入记忆 |
| POST | `/api/memory/search` | 检索记忆（带评分分量） |
| DELETE | `/api/memory/{id}` | 删除记忆 |

对话示例（Python，避免终端编码问题）：
```python
import httpx
h = {"X-API-Key": "dev-key"}
r = httpx.post("http://localhost:8000/api/chat", headers=h,
               json={"message": "先查天气然后订酒店最后生成旅行计划", "user_id": "me"})
print(r.json())
# reply / engine(本轮引擎) / system(talker|reasoner) / complexity / risk / trace
```

响应里的 `engine`、`system`、`trace` 让你随时看清「这次谁在思考、为什么选它、花了多少」——引擎透明。

## 5. 常见问题排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `401 invalid or missing X-API-Key` | 没带或带错头 | 头里放 `X-API-Key`，值 = `SUNDAY_API_KEY` |
| 回复是 `[mock:...] echo(...)` | 没配任何真实 Key | 在 `.env` 填 Key 后重启 |
| `There was an error parsing the body`（curl） | Git Bash 对中文 JSON 的引号转义 | 改用 Python httpx，或 `--data-binary @file.json` |
| 重启后记忆没了 | 记忆仅在内存（当前设计） | 等 Phase 1 收尾的持久化，或先接受会话内有效 |
| 中文输出乱码 | Windows 控制台 GBK 解码 | 显示问题，非数据问题；用 httpx 客户端查看 |
| `ModuleNotFoundError` | 依赖没装 | `python -m pip install -r requirements.txt` |
| 引擎调用失败但没报错 | 路由回退链吞掉并降级 | 看响应 `trace.fallbacks_used`；全失败则返回兜底语 |

## 6. 下一步

要让它更接近成品，优先做（详见 [../ROADMAP.md](../ROADMAP.md)）：
1. 记忆持久化（SQLite + ChromaDB）。
2. Reasoner 的 ReAct 循环 + 真实工具执行。
3. 反思引擎（记忆 L1→L2）。
4. Console 接后端真实数据。
