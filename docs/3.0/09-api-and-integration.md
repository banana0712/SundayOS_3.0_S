# 09 · API 与集成

> iPhone/桌面/云皆为一等公民，GitHub 为 source of truth。本章定义对外接口与多端集成模型。

## 9.1 REST / SSE / WebSocket API

延续 1.0 的 `X-API-Key` 鉴权。核心端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 单轮对话（双系统自动路由） |
| POST | `/api/chat/stream` | SSE 流式对话（打字机） |
| WS | `/ws/chat` | 全双工，支持系统2「思考中」推送 |
| POST | `/api/memory/store` | 写入记忆（记忆胶囊） |
| POST | `/api/memory/search` | 语义检索记忆 |
| DELETE | `/api/memory/{id}` | 删除记忆（隐私遗忘） |
| GET | `/api/engines` | 引擎状态 + 路由统计（可观测性） |
| GET | `/api/engines/trace/{req_id}` | 单次路由决策详情（RouteTrace） |
| GET | `/api/daily-brief/{user_id}` | 每日简报（秘书角色） |
| GET | `/api/skills/available` | 可用技能列表 |
| GET | `/health` | 健康检查 |

### `/api/chat` 请求/响应

```jsonc
// 请求
{
  "message": "帮我规划下周日本旅行",
  "user_id": "banana",
  "role_hint": "secretary",     // 可选: 提示角色，影响路由
  "voice_input": false
}
// 响应
{
  "reply": "好的～先问几个问题：预算大概多少？...",
  "engine": "deepseek-chat",    // 本轮实际使用的引擎
  "system": "reasoner",         // talker | reasoner
  "belief_updated": true,
  "memory_writes": 2,
  "request_id": "req_01H...",
  "latency_ms": 412
}
```

响应显式回传 `engine` 与 `system`——让你随时看到「这次谁在思考」，兑现引擎透明。

## 9.2 iPhone 集成

延续 1.0 的 Shortcuts 方案，3.0 升级为 App Intents 能力矩阵：

| Intent | 功能 | 参数 | 离线支持 |
|--------|------|------|:---:|
| AskSunday | 对话/提问 | query | 部分（本地模型） |
| ScheduleTask | 创建/改日程 | title, time, duration | 否 |
| SearchMemory | 搜个人记忆 | query, timeRange | 否 |
| GenerateContent | 生成文本/诗 | prompt, style | 部分 |
| MoodCheck | 情感检测回应 | mode | 部分（本地模型） |
| PlanTask | 分解复杂任务 | goal | 否 |
| CaptureMemory | 记忆胶囊 | content, type | 本地缓存后同步 |

交互层级：
- **Widget**（WidgetKit）：日程预览、状态、快捷入口 —— 离线可用。
- **Siri + Shortcuts**（App Intents）：语音触发技能 —— 离线/在线混合。
- **主应用**（SwiftUI）：完整对话、任务、设置 —— 在线为主。
- **通知 + Live Activity**：主动提醒、进度追踪 —— 在线推送。

隐私（iPhone 侧）：本地模型优先处理敏感数据；差分隐私上传；E2E 加密；严守 ATT。

## 9.3 GitHub 作为 source of truth

```
                    GitHub (真源)
          ┌──────────────┼──────────────┐
   persona.yaml     skills/*.yaml   memory-snapshots/
   (人格配置)       (技能定义)      (稳定语义记忆快照)
          └──────────────┼──────────────┘
                         │ 运行时加载 / 定时快照回写
                    SundayOS 云端心智
                         │ 编排
        ┌────────────────┼────────────────┐
   DeepSeek           Claude            本地模型
   (连接的 AI 服务，非真源)
```

- **版本化的身份**：人格、技能、稳定偏好以文件形式版本化，改动走 commit，可回滚、可审计、可 diff。
- **快照回写**：语义记忆定期快照到 GitHub（加密），实现跨设备一致与灾备。
- **编排而非依赖**：连接的 AI 服务是可替换引擎，真相始终在 Git。

## 9.4 多端一致性

| 端 | 角色 | 本地能力 | 云端依赖 |
|----|------|---------|---------|
| iPhone/iPad | 主入口、随身 | 本地模型（情感/意图）、Widget | 深度推理、全量记忆 |
| 桌面 | 编码/学习主战场 | 文件/Shell/本地模型 | 深度推理、GitHub 编排 |
| 云 | 连续心智、调度 | — | 全部 |

心智状态（记忆/信念/人格）以云 + GitHub 为中心，各端是同一心智的不同「窗口」，而非各自独立的实例。
