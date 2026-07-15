# Dashboard 真实数据接线 · 执行指导书

> **给下一个 AI 的施工手册。** 目标:把 Console Dashboard 里"演戏"的部分换成真实后端数据。
> 每一步精确到文件与行号,标注了哪些是"接线即可"、哪些"后端缺数据源需先补"。
>
> **动手前先读**:`CLAUDE.md` 启动流程 → `docs/CURRENT_STATE.md` → 本文件。
> 作者勘察时间:2026-07-15 · 基于 v0.9.0。行号可能随代码变动漂移,以符号搜索为准。

---

## 0. 为什么做这件事

Dashboard 是产品门面,但目前**半真半假**,假的部分直接伤害"这是个真系统"的信任:

- 情绪雷达 6 维里 3 维随机漂移、3 维写死。
- 健康卡展示 **Qdrant / Redis / Postgres / MCP** 四个绿灯 —— **这些组件项目根本没用**(实际是 SQLite + hash/Qwen embedding)。这是在展示不存在的架构,最危险。
- 目标卡是写死的"东京旅行"任务。
- 事件时间线是写死的假事件 —— 但**后端其实已经返回真实事件**,只是没接。

好消息:Dashboard 顶部指标、Metric 网格、Memory 页、Chat 页**都已经是真数据**。这次只需收拾剩下的 4 张卡。

---

## 1. 现状全景(勘察结论,已核对代码)

### 前端文件
`console/src/components/views/dashboard.tsx`(单文件,所有卡片都在里面)

| 卡片 | 函数 | 当前状态 | 数据源 |
|------|------|---------|--------|
| 数据源横幅 + 顶部指标 | `DashboardView` / `buildMetrics` | ✅ **已真** | `/api/stats/dashboard` |
| Metric 网格 | `MetricCard` | ✅ **已真** | 同上 |
| 活动图 | `ActivityCard` | ⚠️ 待核 | 需确认是否 useDrift |
| **情绪雷达** | `MoodCard` (~L274) | ❌ **假** | `useDrift` ×3 + 写死 `0.68/0.79/0.83` (L280) |
| **健康卡** | `HealthCard` (~L300) | ❌ **假** | `useDrift` CPU/RAM + 写死 4 个绿灯 (L329-332) |
| **目标卡** | `GoalCard` (~L351) | ❌ **假** | 写死东京旅行任务 (L353-359) |
| **事件卡** | `EventsCard` (~L400) | ❌ **假** | 写死事件 (L402-408) |

### 后端已有的真数据源(关键!)

**`GET /api/stats/dashboard`**(`backend/app/main.py` ~L412)已返回:
```json
{
  "messages_today", "model_calls", "tokens_used", "cost_today",
  "memory_nodes", "avg_latency_ms", "active_tools",
  "engines": [{"id","calls","strong","local"}],
  "conv_count", "reflect_count", "experience_count",
  "recent_events": [{"time","event"}]     // ← 事件卡的真数据，已在返回里！
}
```

**`GET /api/admin/health`**(`backend/app/main.py` ~L400,**需 owner/API Key**)已返回:
```json
{
  "server": {"version","python"},
  "db": {"type":"sqlite","users","memories","conversations"},
  "engines": [{"id","quality","healthy","calls"}],
  "embedder": "semantic"|"hash",
  "embedder_provider": "qwen"|"hash"|...,
  "embedder_degraded": true|false,
  "embedding_dim": 1024|128
}
```

---

## 2. ⚠️ 必读:两个数据源缺口(不是接线能解决的)

在动手前必须理解,否则会白做:

### 缺口 A:情绪状态从不持久化
`BeliefState`(`backend/app/cognition/belief.py`)**每次聊天请求新建、用完即弃**(见 `main.py:885` 和 `1075`,都是 `belief = BeliefState(user_id=...)`)。共情管道(`persona/empathy.py`)会在单次请求内更新 `belief.emotional_state`,但**没有任何地方把它存下来**。

**含义**:情绪雷达(MoodCard)**没有可查询的真实情绪数据源**。你不能只写个 `GET /api/belief` 去读——它读不到东西。见 §4 的决策路径。

### 缺口 B:目标/任务同样不持久化
`BeliefState.active_tasks` / `current_goal` 也是每请求新建,默认空。目标卡(GoalCard)**同样没有真实数据源**。见 §5。

---

## 3. 卡片一:健康卡(HealthCard)—— 最高优先,接线即可

**这是性价比最高、最该先做的一张。** 数据源真实存在,只需接线 + 删假数据。

### 3.1 后端:让 stats 端点带上健康摘要(推荐)
Dashboard 已经在轮询 `/api/stats/dashboard`(每 15s)。与其让前端再打一个需要 admin 权限的 `/api/admin/health`,不如把**非敏感**的健康字段并进 stats 返回,避免前端二次鉴权。

在 `backend/app/main.py` 的 `dashboard_stats`(~L412)返回体里追加:
```python
from .memory.embedding import embedding_dim as edim, embedder_provider as eprov
# ... 在 return {...} 里加:
    "system_health": {
        "db": "sqlite" if isinstance(MEMORY, SQLiteMemoryStore) else "memory",
        "embedder_provider": eprov(),          # "qwen" | "hash" | ...
        "embedder_degraded": eprov() == "hash",
        "embedding_dim": edim(),
        "engines_healthy": len(ENGINES),        # 简单起步：全部视为健康
        "version": _version_str,
    },
```
> 注意:`isinstance` 需要 `SQLiteMemoryStore` 已 import(文件顶部已有)。

### 3.2 前端:重写 HealthCard(`dashboard.tsx` ~L300)
**删掉**这些写死的假组件:
- L329-332 的 `<HealthRow label="Vector DB · Qdrant" ok />` 等 4 行 —— 这些组件不存在,必须删。
- CPU/RAM 的 `useDrift` donut(L302-303, L308-320):项目跑在 2H2G 服务器,前端拿不到真实 CPU/RAM。**要么删,要么**接一个新的后端字段(需后端加 `psutil`,见下方可选项)。作者建议:**先删,别演假的**。

**换成**真实健康行,数据从 `stats.system_health` 读:
```tsx
function HealthCard({ stats }: { stats: Record<string, any> | null }) {
  const h = stats?.system_health;
  return (
    <Card className="h-full p-5">
      <h3 className="text-subtitle text-primary">系统健康</h3>
      <div className="mt-4 space-y-2 border-t border-border pt-4">
        <HealthRow label={`数据库 · ${h?.db ?? "—"}`} ok={!!h} />
        <HealthRow
          label={`Embedder · ${h?.embedder_provider ?? "—"} (${h?.embedding_dim ?? "?"}d)`}
          ok={h ? !h.embedder_degraded : false}
        />
        <HealthRow label={`引擎 · ${h?.engines_healthy ?? 0} 个在线`} ok={!!h?.engines_healthy} />
      </div>
    </Card>
  );
}
```
> **注意**:`HealthCard` 现在需要 `stats` 作为 prop。在 `DashboardView`(L113)把 `<HealthCard />` 改成 `<HealthCard stats={stats} />`。

**收益**:健康卡从"展示不存在的 Qdrant/Redis/Postgres"变成真实反映 SQLite + Qwen/hash + 引擎状态。而且 v0.9.0 新做的 **embedder 降级可见性**在这里露出——降级时那一行变红,一眼可见。

### 3.3(可选)真实 CPU/RAM
若想保留 CPU/RAM donut,后端加 `psutil`(需 `pip install psutil` + 写进 `requirements.txt`),在 `system_health` 加 `"cpu": psutil.cpu_percent()/100`、`"ram": psutil.virtual_memory().percent/100`。**非必需,作者建议初版跳过。**

---

## 4. 卡片二:事件卡(EventsCard)—— 接线即可,数据已存在

**后端已经返回 `recent_events`,前端却在用写死的假事件。这是纯遗漏,补上即可。**

### 4.1 确认后端在记什么事件
`runtime.record_call(...)` 的 `event` 参数会写进 `runtime.recent_events`(见 `backend/app/runtime.py:89-91`,保留最近 20 条)。`/api/stats/dashboard` 已把前 8 条作为 `recent_events` 返回。

**先验证真有事件**:如果 `recent_events` 常年为空,说明调用方没传 `event=` 文案。搜 `record_call(` 看有没有传 event。若没有,需要在关键动作处补 event 文案(如聊天完成、反思触发、记忆固化),否则事件卡会是空的——那也比假数据诚实。

### 4.2 前端:重写 EventsCard(`dashboard.tsx` ~L400)
**删掉** L402-408 写死的 `events` 数组。改为从 `stats.recent_events` 读:
```tsx
function EventsCard({ stats }: { stats: Record<string, any> | null }) {
  const events = (stats?.recent_events ?? []) as { time: string; event: string }[];
  return (
    <Card className="h-full p-5">
      <h3 className="mb-4 text-subtitle text-primary">近期事件</h3>
      {events.length === 0 ? (
        <p className="text-caption text-tertiary">暂无事件记录</p>
      ) : (
        <div className="relative space-y-4 pl-1">
          <div className="absolute bottom-2 left-[10px] top-2 w-px bg-border" />
          {events.map((e, i) => (
            <div key={i} className="relative flex items-center gap-3">
              <span className="relative z-10 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-[var(--surface)] text-accent">
                <Activity className="h-3 w-3" />
              </span>
              <div className="flex-1 text-[13px] text-secondary">{e.event}</div>
              <span className="text-[11px] text-tertiary tnum">{fmtAgo(e.time)}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
```
- 需要一个 `fmtAgo(isoString)` 小工具把 ISO 时间转成 "2m ago"(自己写或用现成的相对时间函数)。
- 同样在 `DashboardView`(L119)把 `<EventsCard />` 改成 `<EventsCard stats={stats} />`。

---

## 5. 卡片三:目标卡(GoalCard)—— 需先决策(无数据源)

见 §2 缺口 B:目标/任务不持久化,**没有真实数据源**。三条路,按推荐排序:

**路 A(推荐 · 诚实降级)**:既然没有真实目标数据,**暂时移除这张卡**,或改成一张有真数据的卡(如"记忆构成":用 stats 里的 `reflect_count` / `experience_count` / `memory_nodes` 画个分布)。不要留着假的东京旅行。

**路 B(中等工作量 · 补数据源)**:给 `BeliefState` 做持久化——新建 `BeliefStore`(SQLite,照 `conversation/sqlite_store.py` 的 pattern),每次 chat 后把 `belief` 存进去,加 `GET /api/belief` 读最新。目标卡接它。**注意这会连带解决 §6 情绪雷达**,因为情绪也在 BeliefState 里。是这两张卡的共同解法。

**路 C(不推荐)**:维持现状。会一直是假数据,与"真实系统"定位冲突。

> 作者判断:如果只做一次交付,选**路 A**(快、诚实);如果愿意投入,选**路 B**——它一次性把目标卡 + 情绪雷达都盘活,是根治。

---

## 6. 卡片四:情绪雷达(MoodCard)—— 需先决策(无数据源)

见 §2 缺口 A。同样三条路:

**路 A(推荐首选 · 根治)**:走 §5 路 B 的 `BeliefStore` 持久化,加 `GET /api/belief` 返回 `emotional_state`(mood/energy/stress 都是真值)。前端 MoodCard(`dashboard.tsx:280`)把 `useDrift` 和写死的 `0.68/0.79/0.83` 全换成读真值。

**路 B(轻量近似)**:不做持久化,而是每次 chat 的 SSE `done` 事件里带上本轮 `emotional_state` 快照,前端缓存最近一次显示。**缺点**:刷新页面就没了,且 Dashboard 不在聊天页看不到。

**路 C(诚实降级)**:BeliefState 只有 mood/energy/stress **3 个真维度**,而 UI 画了 6 维。可以把雷达砍成 3 维真实维度,删掉 Calm/Focus/Trust 这 3 个本就编造的。比演 6 维假数据诚实。

> 作者判断:**路 A 最好**(和目标卡共用 `BeliefStore`,一次投入解决两张卡)。若不想碰持久化,**路 C** 也比现状强。

---

## 7. 施工顺序建议

按"性价比 / 是否需补后端"排:

1. **健康卡**(§3)—— 最高优先。数据源现成,接线 + 删假绿灯。立刻见效,顺带露出 embedder 降级。
2. **事件卡**(§4)—— 数据已在返回里,纯补前端。注意先验证 `recent_events` 真的有内容。
3. **决策点**:是否投入做 `BeliefStore` 持久化(§5 路 B)?
   - **做** → 目标卡 + 情绪雷达一起盘活(§5 路 B + §6 路 A)。
   - **不做** → 目标卡走 §5 路 A(换成记忆构成卡或移除),情绪雷达走 §6 路 C(砍成 3 真维度)。

不要为了"填满仪表盘"而保留任何假数据。**空卡 + "暂无数据" 比假数据可信。**

---

## 8. 验证清单(照 verify 纪律,必须跑真 app)

改完后**不是**跑测试就算完,要起服务器、开浏览器实测:

**后端**(先跑):
```bash
cd backend && python -m pytest -q          # 不得回归（当前 86 passed）
python -m uvicorn app.main:app --port 8000
curl -s localhost:8000/api/stats/dashboard -H "X-Api-Key: <key>" | python -m json.tool
# ↑ 确认 system_health / recent_events 字段真出现且有值
```

**前端**:
```bash
cd console && npm run build                 # 类型检查必须过
npm run dev                                 # 开 localhost:3000/console
```
浏览器逐项核对:
- [ ] 健康卡:显示真实 "SQLite / Embedder: qwen 或 hash / N 引擎",**不再有 Qdrant/Redis/Postgres/MCP**。
- [ ] 把后端的 Qwen key 去掉重启 → 健康卡 Embedder 行变红显示 "hash / 降级"。(验证降级可见)
- [ ] 事件卡:显示真实近期事件,或"暂无事件记录";**不再有写死的 "Trust +0.03 with Banana"** 等假事件。
- [ ] 目标卡 / 情绪雷达:按所选路径核对——要么是真数据,要么诚实降级,**不再有东京旅行 / 随机漂移**。
- [ ] 截图留证(verify 纪律:运行时观察才是证据)。

---

## 9. 收尾:文档同步(CLAUDE.md 会话结束纪律)

改完更新:
- `VERSION`:体验优化属 MINOR 或 PATCH(接线为主 → PATCH;若做了 BeliefStore 新模块 → MINOR)。
- `CHANGELOG.md`:Keep a Changelog 格式记录。
- `docs/CURRENT_STATE.md`:§2 把"仪表盘部分 mock"这条更新/移除。
- `docs/ROADMAP.md`:相应条目。
- `docs/PROJECT_MEMORY.md`:若做了 BeliefStore,记一条决策;若发现新债务(如 CPU/RAM 仍缺),记进技术债表。
- 若删除了假的 Qdrant/Redis/Postgres 展示,值得在 PROJECT_MEMORY "已消灭的债务" 记一笔——它曾误导观者以为系统用了这些组件。

---

## 附:关键 file:line 速查(勘察时点,以搜索为准)

| 位置 | 内容 |
|------|------|
| `console/src/components/views/dashboard.tsx` L274-297 | MoodCard(情绪雷达,假) |
| 同上 L299-336 | HealthCard(含 L329-332 假绿灯) |
| 同上 L350-397 | GoalCard(写死东京旅行) |
| 同上 L399-436 | EventsCard(写死事件) |
| 同上 L113-120 | DashboardView 里 4 张卡的挂载点(要加 stats prop) |
| `backend/app/main.py` ~L412 | `dashboard_stats` 端点(加 system_health) |
| `backend/app/main.py` ~L400 | `admin_health` 端点(健康数据参考) |
| `backend/app/main.py` L885, L1075 | `BeliefState(...)` 每请求新建(缺口根源) |
| `backend/app/cognition/belief.py` | BeliefState / EmotionalState 定义 |
| `backend/app/runtime.py` L76-91 | `record_call` 写 recent_events |
