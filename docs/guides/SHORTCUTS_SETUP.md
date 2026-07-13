# SHORTCUTS_SETUP.md · iPhone 快捷指令接入指南

> 让 Sunday 出现在你的 iPhone 上——通过快捷指令 + Siri 语音调用。

---

## 前置条件

1. 记住你的 API Key（`.env` 里的 `SUNDAY_API_KEY`）
2. 手机能访问外网即可——使用 Railway 部署地址
3. 默认公网地址：`https://sundayos30s-production.up.railway.app`
   （如果这个地址变了，去 Railway Dashboard → Settings → Domains 查看最新 URL）

---

## 快捷指令配置（3 步）

### 步骤 1：新建快捷指令

打开 iPhone 上的 **快捷指令** App → 点右上角 **＋** → 点顶部标题重命名为 "Ask Sunday"。

### 步骤 2：添加操作

依次添加以下 4 个操作：

#### 操作 ① — 获取输入
```
搜索添加： "要求输入"
→ 提示文字：对 Sunday 说点什么
→ 输入类型：文本
```

#### 操作 ② — 发送请求
```
搜索添加： "获取 URL 内容"
→ URL：https://sundayos30s-production.up.railway.app/api/shortcuts/chat
→ 方法：POST
→ 头部：
    Content-Type    application/json
    X-API-Key       sunday0712
→ 请求体：JSON
    message         [提供的输入]（点一下选「提供的输入」）
    voice_input     true
```

#### 操作 ③ — 解析回复
```
搜索添加： "获取词典值"
→ 词典：[内容]（上一步的返回结果）
→ 键：reply
```

#### 操作 ④ — 朗读回复
```
搜索添加： "朗读文本"
→ 文本：[词典值]（上一步取出的 reply）
```

### 步骤 3：添加到主屏幕（可选）

点底部分享按钮 → 「添加到主屏幕」→ 设置图标和名称 → 桌面上就有 Sunday 的入口了。

---

## Siri 语音调用

快捷指令创建好后，直接对 Siri 说：

> **"Hey Siri，Ask Sunday"**

Siri 会弹出文本输入框（或直接语音输入），你说的话发送给 Sunday，Sunday 回复后 Siri 朗读出来。

---

## 高级配置

### 纯语音对话模式

把操作 ① 替换为：

```
搜索添加： "听写文本"
→ 语言：中文（中国大陆）
```

这样 Siri 调用 "Ask Sunday" 后直接进入听写模式，你说完自动发送，Sunday 回复后朗读。

### 连续对话

在操作 ④ 后面加：

```
搜索添加： "运行快捷指令"
→ 快捷指令：Ask Sunday
→ 勾选「运行前显示」
```

这样一次对话结束后自动提示下一轮，实现连续对话。

---

## API 说明

### 端点

```
POST /api/shortcuts/chat
Content-Type: application/json
X-API-Key: sunday0712

请求体：
{
  "message": "今天天气怎么样",
  "voice_input": true
}

响应：
{
  "reply": "今天是晴天，22-28°C，很适合出门！",
  "mode": "talker"
}
```

| 字段 | 说明 |
|------|------|
| `reply` | Sunday 的回复文本（已脱敏，适合朗读） |
| `mode` | `"talker"` = 快思考，`"reasoner"` = 慢思考（ReAct） |

### 与普通 chat 端点的区别

| | `/api/chat` | `/api/shortcuts/chat` |
|---|---|---|
| 响应格式 | 完整 trace + react_steps + 引擎信息 | 仅 reply + mode |
| 记忆存储 | 按传入的 user_id | 固定 user_id="shortcuts" |
| 记忆检索 | k=6 | k=4（更快） |
| ReAct 步数上限 | 7 | 5（语音场景更快） |
| 超时 | 120s | 60s |

---

## 常见问题

| 问题 | 解决 |
|------|------|
| 快捷指令报"无法连接到服务器" | 手机和电脑是否在同一 WiFi？后端是否启动？防火墙是否拦截？ |
| 回复太长 Siri 读不完 | Sunday 在 voice_input 模式下会自动缩短回复 |
| 想换个 API Key | 改快捷指令里的 X-API-Key 头部即可 |
| 想从外网访问 | 需要部署到公网服务器或配置内网穿透 |
