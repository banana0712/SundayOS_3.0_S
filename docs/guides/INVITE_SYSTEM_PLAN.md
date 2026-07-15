# 邀请制个人实例 —— 实现指导计划

> **给下一个 AI 的交接文档。** 本文档描述如何把 SundayOS 从"注册对全世界开放"改造成
> "邀请制个人实例:owner + 受邀朋友,每人一套独立 Sunday"。
>
> **数据层骨架已经写好并验证** —— `backend/app/auth/invites.py`（`InviteStore`）。
> 你要做的是把它接进现有系统，改动都是**增量**，不破坏现有登录 / API Key 路径。
>
> 状态：**未接线**（写这份文档时 `InviteStore` 还没有任何地方 import）。
> 版本基线：v0.9.0。

---

## 0. 背景与决策（为什么这么设计）

三个已定的产品决策，别推翻：

1. **形态 = 邀请制个人实例**，不是对外多租户 SaaS。规模个位数~几十人，都是 owner 认识的朋友。
   所以：SQLite + 应用层隔离足够，**不需要** Postgres / RLS / 限流 / 撞库防护那套重家伙。
2. **朋友加入 = 邀请码**。owner 生成一次性码（`SUN-XXXX`）发给朋友，朋友注册时必填。码用过即失效。
3. **owner 身份 = 环境变量指定**。`.env` 里 `SUNDAY_OWNER_USERNAME=<你的用户名>`。
   该用户注册/登录时 role 自动置 `owner` 且免邀请码。静态 `API_KEY` 仍是后门（防锁死）。

架构定位：这是 **Pool 模型**（共享 DB、共享表、`user_id` 分区）。数据模型早已铺好 `user_id`，
本次不动数据分区，只动**准入控制**（谁能注册）和**角色**（谁是 owner）。

---

## 1. 已交付的骨架：`InviteStore`

文件：`backend/app/auth/invites.py`。已实现并单测验证的接口：

| 方法 | 作用 |
|------|------|
| `InviteStore(db_path)` | 打开/迁移 `invites` 表（WAL、幂等 CREATE） |
| `create(created_by, note="") -> Invite` | 生成一次性码，返回 `Invite` dataclass |
| `is_valid(code) -> bool` | 码存在且未用 |
| `redeem(code, used_by) -> bool` | 原子兑换：未用→标记已用返 True；已用/不存在→False |
| `revoke(code) -> bool` | 撤销未用的码；已用的返 False |
| `list_all() -> list[dict]` | owner 面板用，含状态与备注 |
| `get(code) -> Invite \| None` | 单查 |
| `close()` | 关连接 |

`invites` 表结构：
```
code TEXT PK | created_by TEXT | note TEXT | created_at TEXT | used_by TEXT(NULL=未用) | used_at TEXT
```

码格式：`SUN-` + 4 位无歧义大写字母数字（去掉 0/O/1/I/L），见 `_ALPHABET`。冲突自动重试。

**不要改这个文件的接口**，除非下面的接线暴露出真实缺口。

---

## 2. 需要改的共享代码（按顺序执行）

> 每步都给了当前基线的 file:line 锚点。**执行前先重读该文件确认行号没漂**（v0.9.0 之后可能已变）。

### 步骤 1 —— `users` 表加 `role` 列（幂等迁移）

文件：`backend/app/auth/__init__.py`，`UserStore._migrate()`（基线 ~L75-93）。

在 `CREATE TABLE users` 之后追加幂等的列添加。SQLite 不支持 `ADD COLUMN IF NOT EXISTS`，
必须先查 `PRAGMA table_info`：

```python
cols = {r[1] for r in self._conn.execute("PRAGMA table_info(users)").fetchall()}
if "role" not in cols:
    self._conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
self._conn.commit()
```

现有用户自动落 `'user'`，零迁移风险。

同时改：
- `User` dataclass（基线 ~L51-57）加 `role: str = "user"` 字段。
- 所有 `SELECT ... FROM users` 的地方（`verify_user` L128、`get_user_by_token` L154、
  `get_user_by_id` L169、`create_user` 的返回）把 `role` 读出来并塞进 `User(...)`。
  **注意 SELECT 的列顺序**——现在是 `id, username, password_hash, token, created_at`，
  加 role 后每个 `row[N]` 索引都要跟着改，逐个核对，别错位。
- `list_all()`（L183）在返回 dict 里加 `"role": r[...]`。

### 步骤 2 —— `UserStore` 加角色方法

在 `UserStore` 里加：

```python
def create_user(self, username, password, role="user"):   # 加 role 参数
    ...
    # INSERT 时带上 role 列

def get_role(self, user_id) -> str:
    row = self._conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    return row[0] if row else "user"

def set_role(self, user_id, role) -> None:
    self._conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    self._conn.commit()
```

### 步骤 3 —— 启动装配：InviteStore + owner bootstrap

文件：`backend/app/main.py`，`USER_STORE = UserStore(_DB_PATH)` 之后（基线 ~L112）。

```python
from .auth.invites import InviteStore
INVITE_STORE = InviteStore(_DB_PATH)          # 复用同一个 db 文件

# owner bootstrap：环境变量指定
OWNER_USERNAME = os.getenv("SUNDAY_OWNER_USERNAME", "").strip()
if OWNER_USERNAME:
    u = USER_STORE.get_user_by_username(OWNER_USERNAME)   # 你可能要加这个查询方法
    if u and u.role != "owner":
        USER_STORE.set_role(u.id, "owner")     # 已存在则纠正 role（防改了 env 不同步）
```

> `get_user_by_username` 现在没有，加一个（照 `get_user_by_id` 抄）。

### 步骤 4 —— 注册端点加邀请码门槛（**核心安全收口**）

文件：`backend/app/main.py`，`AuthRequest`（基线 ~L336）和 `auth_register`（~L341）。

`AuthRequest` 加可选字段：
```python
class AuthRequest(BaseModel):
    username: str
    password: str
    invite_code: str | None = None   # 注册时用；登录忽略
```

`auth_register` 改逻辑：
```python
username = req.username.strip()
is_owner = OWNER_USERNAME and username == OWNER_USERNAME

if is_owner:
    role = "owner"                    # owner 免邀请码
else:
    if not req.invite_code or not INVITE_STORE.is_valid(req.invite_code):
        raise HTTPException(status_code=403, detail="需要有效的邀请码")
    role = "user"

try:
    user = USER_STORE.create_user(username, req.password, role=role)
except ValueError as e:
    raise HTTPException(status_code=409, detail=str(e))

if not is_owner:
    INVITE_STORE.redeem(req.invite_code, user.id)   # 建号成功后才消耗码
```

> **顺序很重要**：先建号、成功了再 `redeem`。反过来会出现"码消耗了但建号失败"的状态。
> 边界：`create_user` 抛 ValueError（用户名重复）时码不能被消耗——上面的顺序已保证。
> 潜在竞态（两人同时用一个码）在个人实例规模可忽略；真要严谨就把 redeem 做成
> `UPDATE ... WHERE used_by IS NULL` 判 rowcount，`InviteStore.redeem` 已经是这个语义。

### 步骤 5 —— `_require_admin` 改成 role-based

文件：`backend/app/main.py`，`_require_admin`（基线 ~L688-694）。

```python
def _require_admin(x_api_key, x_sunday_token) -> str:
    user_id = _auth(x_api_key, x_sunday_token)       # 先认证（复用现有）
    # 后门：静态 API Key 直接放行（防 owner 把自己锁死）
    if x_api_key == API_KEY or x_sunday_token == API_KEY:
        return user_id
    # 正常路径：查 role
    if USER_STORE.get_role(user_id) == "owner":
        return user_id
    raise HTTPException(status_code=403, detail="需要管理员权限")
```

这一步同时消掉了旧设计里"owner 不在用户表、admin 判据是裸 key 比对"的技术债
（见 PROJECT_MEMORY §4）。

### 步骤 6 —— owner-only 邀请管理端点

文件：`backend/app/main.py`，admin 端点区（`/api/admin/health` 之后，基线 ~L792）。

三个端点，全走 `_require_admin`：

```python
class InviteCreateRequest(BaseModel):
    note: str = ""

@app.post("/api/admin/invites")
async def admin_create_invite(req: InviteCreateRequest, x_api_key=..., x_sunday_token=...):
    owner_id = _require_admin(x_api_key, x_sunday_token)
    inv = INVITE_STORE.create(owner_id, note=req.note)
    return {"code": inv.code, "note": inv.note, "created_at": inv.created_at}

@app.get("/api/admin/invites")
async def admin_list_invites(x_api_key=..., x_sunday_token=...):
    _require_admin(x_api_key, x_sunday_token)
    return {"invites": INVITE_STORE.list_all()}

@app.delete("/api/admin/invites/{code}")
async def admin_revoke_invite(code: str, x_api_key=..., x_sunday_token=...):
    _require_admin(x_api_key, x_sunday_token)
    return {"revoked": INVITE_STORE.revoke(code)}
```

> Header 参数照抄现有 admin 端点那一长串 `Header(default=None, alias=...)`。
> （若届时已做了 `Depends` 化重构，用依赖注入替代。）

### 步骤 7 —— 前端注册框加"邀请码"输入

**没有这步朋友无法注册，功能是断的。**

- **webchat**（`backend/app/webchat.py`）：注册卡片加一个邀请码 input，
  POST `/api/auth/register` 时带上 `invite_code`。搜 `register` 定位卡片 HTML/JS。
- **Console**（可选，非必需）：`console/src/components/views/admin-panel.tsx` 加"邀请"tab，
  调三个新端点。owner 也可以先用 curl 发码，这步可延后。

---

## 3. 验证清单（做完必须跑）

**单测**（新建 `backend/tests/test_invites.py`，`InviteStore` 骨架已可直接测）：
- 生成码 → `is_valid` True
- 兑换一次 True，第二次 False
- 兑换后 `is_valid` False
- 撤销未用码 True，撤销已用码 False
- role 迁移幂等：对已有 users.db 跑两次 `_migrate` 不报错、不重复加列

**运行时端到端**（起服务器，curl 驱动，别只跑单测）：
1. owner 用 `SUNDAY_OWNER_USERNAME` 那个名字注册 → 成功，无需码，`/api/auth/me` 或 `get_role` 显示 owner
2. 陌生人无码注册 → **403 需要有效的邀请码**
3. owner 打 `POST /api/admin/invites` → 拿到 `SUN-XXXX`
4. 朋友用该码注册 → 成功，role=user
5. 同一个码再注册 → **403**（已消耗）
6. 朋友 token 打 `/api/admin/invites` → **403 需要管理员权限**
7. owner token（或 API Key 后门）打 admin 端点 → 200

**回归**：`cd backend && python -m pytest -q` 全绿；`cd console && npm run build` 通过。

> 环境提醒：`.env` 用 `override=True`，shell export 的同名变量会被 `.env` 覆盖。
> 测 owner bootstrap 时改 `.env` 里的 `SUNDAY_OWNER_USERNAME`，别指望 export。
> 详见 memory `backend-env-gotchas`。

---

## 4. 完成后要更新的文档

按 CLAUDE.md 会话结束纪律：
- VERSION：MINOR bump（新功能，向后兼容）→ 0.9.0 → 0.10.0
- CHANGELOG.md：Added 段记邀请系统
- CURRENT_STATE.md：§2 能做的表加"邀请制注册 + role"；把"注册对全世界开放"从隐患移除
- PROJECT_MEMORY.md：新增决策条目（邀请制 + role-based admin）；
  Resolved Debt 里记掉"owner 不在用户表 / admin 裸 key 比对"
- ROADMAP.md：邀请系统移入已完成

---

## 5. 明确不做的（范围边界，别扩）

- ❌ Postgres / RLS —— 个人实例规模不需要，SQLite + 应用层隔离足够
- ❌ 撞库防护 / 限流 —— 受邀朋友非匿名攻击面，Phase 后期再说
- ❌ 邀请码有效期 / 多次可用码 —— 一次性够用，YAGNI
- ❌ 邮件发码 —— owner 手动把 `SUN-XXXX` 发给朋友即可
- ❌ 数据分区改动 —— `user_id` 隔离已就绪，本次只碰准入控制

如果做的过程中发现这些边界里某条其实必须做，停下来先问 owner，别自行扩范围。
