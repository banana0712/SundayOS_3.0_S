# main.py 拆分 · 执行指导书

> **给下一个 AI 的施工手册。** 把 `backend/app/main.py`（上帝文件）按域拆进 `routers/`。
> **地基已铺好、第一个域（admin）已拆完并验证** —— 你照同一个模式滚剩下的域即可。
>
> 动手前必读：`docs/ENGINEERING_CONTRACT.md`（尤其 §1 路由按域拆、§2 单一真相源、§3 完成定义）。
> 基线：v0.10.0，main.py 1360 行 / 38 路由。

---

## 0. 已经做完的（别重做）

- **`app/deps.py`** —— 共享上下文 + 单一真相源认证。已建好：
  - `ctx`：持有 `user_store / memory / conversations / pref_store / runtime / engines / api_key / owner_username / version`。main.py 启动时 `set_context(...)` 填充。
  - `auth()` / `require_admin()`：认证逻辑的唯一实现。
  - `get_current_user` / `get_admin`：FastAPI `Depends` 包装，路由直接用。
  - main.py 的 `_auth` 已改成委托 `deps.auth` 的薄壳（31 个旧调用点还在用，随域迁移逐步换成 `Depends`）。
- **`app/routers/admin.py`** —— 第一个拆出的域（admin 3 端点）。**这就是你要照抄的范例。**
- main.py 里 admin 路由和 `_require_admin` 已删，改为 `app.include_router(_admin_router.router)`。

---

## 1. 拆一个域的标准动作（照 admin 范例）

以拆 `conversations` 为例：

### ① 新建 `app/routers/conversations.py`
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..deps import ctx, get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class ConversationCreateRequest(BaseModel):   # 请求模型跟着搬过来
    title: str = "新对话"

@router.post("")   # 注意：prefix 已含 /api/conversations，这里用 "" 或 "/{id}"
async def conversation_create(req: ConversationCreateRequest,
                              user_id: str = Depends(get_current_user)) -> dict:
    conv = ctx.conversations.create(user_id, req.title)   # CONV → ctx.conversations
    return {...}
```

### ② 改造要点（每条都要做）
- **路由装饰器**：`@app.post("/api/conversations")` → `@router.post("")`（prefix 已含路径前缀）。
- **认证**：删掉函数体里的 `user_id = _auth(x_api_key, x_sunday_token)` 和那两个 Header 参数，
  改成 `user_id: str = Depends(get_current_user)`（admin 域用 `Depends(get_admin)`）。
- **全局引用换 ctx**：`CONV` → `ctx.conversations`，`MEMORY` → `ctx.memory`，
  `USER_STORE` → `ctx.user_store`，`PREF_STORE` → `ctx.pref_store`，`runtime` → `ctx.runtime`，
  `ENGINES` → `ctx.engines`，`_version_str` → `ctx.version`。
- **请求模型**：把该域的 `BaseModel` 一起搬进 router 文件（或统一放 `app/schemas.py`，二选一别混）。
- **共享 helper**：`_record_stats` 目前在 main.py。搬 chat 域时把它移到 `deps.py`（单一实现），
  别在 router 里复制一份（契约 §2）。

### ③ 从 main.py 删掉这些路由，注册 router
```python
from .routers import conversations as _conv_router
app.include_router(_conv_router.router)
```

### ④ 验证（每拆完一个域立刻做，别攒着）
```bash
cd backend && python -m pytest -q              # 必须仍全绿（86）
python -c "import app.main; print(len(app.main.app.routes))"   # 路由总数不变
# 起服务器，curl 打这个域的每个端点，对比拆前的状态码和响应体
```
**路由总数少了 = 漏搬；多了 = 重复注册。必须和拆前一致。**

---

## 2. 建议拆分顺序（从易到难，依赖从少到多）

| 顺序 | 域 | 端点数 | 说明 / 坑 |
|------|-----|--------|-----------|
| ✅ 0 | admin | 3 | **已完成**，范例 |
| 1 | conversations | 5 | 纯 CRUD，最干净，先拿它练手 |
| 2 | memory | 7 | 含 store/search/reflect/consolidate/experience，会调后台任务 |
| 3 | preferences + feedback | 3 | 调 `parse_feedback`、`PREF_STORE` |
| 4 | debug | 4 | 读多个子系统状态，注意别把内部细节暴露成公开 API |
| 5 | auth | 3 | register/login/me。**做这个时顺带接邀请系统**（见 INVITE_SYSTEM_PLAN.md），两件事在同一批改 |
| 6 | misc | 若干 | version/skills/persona/engines/empathy/shortcuts/pwa/stats |
| 7 | **chat** | 2 | **最后做，最难** —— 见 §3 |

**每批一个域，拆完验证、提交心智上的"这一域完成"，再下一个。别一次拆多个。**（契约 §4）

### 留在 main.py 的（不拆）
- `app` 创建、CORS、`load_dotenv`、版本读取
- 所有单例构建 + `set_context(...)`（这是装配层，本就该在入口）
- `/`、`/health`、`/console` 挂载、`/manifest.json`、`/api/pwa/icon` 这些基础设施端点
- 目标：main.py 最终只剩"装配 + include_router 列表 + 少量根路由"，理想 < 300 行

---

## 3. chat 域的特别警告（最后做，单独一节）

`/api/chat` 和 `/api/chat/stream` 是**整个系统最复杂、耦合最深**的两个端点:
护栏 → 共情 → 上下文组装 → 双系统判据 → 路由/ReAct → 记忆写入 → 会话持久化 → 统计。

**关键教训（v0.10.0 踩过的坑）**：这两条路**逻辑几乎重复**，曾导致流式那条忘记记统计、
仪表盘静默少算。拆 chat 时**必须**把共享步骤（护栏/共情/上下文/记忆写入/统计）抽成
`routers/chat.py` 里的**共享 helper 函数**，两条路都调它 —— 绝不允许两段平行代码各写一遍
（契约 §2）。这是拆 chat 的**首要目标**，不只是搬家。

拆完 chat 后 `_record_stats` 应已移入 `deps.py`，main.py 里不再有它。

---

## 4. 硬约束（checkup 会查）

- 每个 router 文件 ≤ 600 行（契约 §1）。
- router **只从 `app.deps` 拿状态**，绝不 `import ...main`（循环 + 双真相）。
- 认证只有一个实现（`deps.auth` / `deps.require_admin`），不复制。
- 每拆一个域，`pytest` 全绿 + 路由总数不变 + curl 验证该域。
- 全部拆完后跑 `/checkup`，确认 main.py 行数达标、无平行路径残留。

---

## 5. 完成后文档同步

- CHANGELOG：记每批拆了哪个域。
- CURRENT_STATE / PROJECT_MEMORY 技术债表：main.py 行数更新；全部拆完则把该债移入
  "已消灭的债务"，记教训（上帝文件是怎么拆干净的）。
- 若 chat 域完成了共享 helper 抽取，在 PROJECT_MEMORY 记一条决策（消除双真相）。
