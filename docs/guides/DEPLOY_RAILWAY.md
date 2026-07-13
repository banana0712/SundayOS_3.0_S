# 部署到 Railway · 云端常在线

> 把 Sunday 后端部署到 Railway，让 AI 服务 7×24 在线，随时可调用（iPhone 快捷指令、网页、curl 都能连）。

## 前提
- 代码已推到 GitHub（`banana0712/SundayOS_3.0_S`）。
- 一个 [Railway](https://railway.app) 账号（用 GitHub 登录最省事）。
- 一个 DeepSeek API Key（真实回复需要）。

## 关键配置（已为你准备好）
仓库 `backend/` 里已包含：
- `railway.json` —— 启动命令 + 健康检查（`/health`）+ 失败自动重启。
- `Procfile` —— `uvicorn app.main:app --host 0.0.0.0 --port $PORT`（绑定 Railway 动态端口）。
- `.python-version` —— 固定 Python 3.12。
- `requirements.txt` —— 依赖清单，Railway 自动安装。

## 部署步骤（网页点几下）

1. **New Project** → `Deploy from GitHub repo` → 选 `SundayOS_3.0_S`。（首次需授权 Railway 访问你的 GitHub。）

2. **⚠️ 设置根目录（最关键的一步）**
   进入服务 → `Settings` → `Root Directory` 填 **`backend`**。
   > 因为这是个 monorepo（同时有 backend 后端和 console 前端）。不设根目录，Railway 会不知道要跑哪个。

3. **设置环境变量**：`Variables` 标签，加这几个（**Key 只填这里，绝不进代码**）：
   | 变量 | 值 |
   |------|-----|
   | `SUNDAY_API_KEY` | 你自定义的一串密码（调用时要带，别人不知道就调不了） |
   | `DEEPSEEK_API_KEY` | 你的 DeepSeek key（`sk-...`） |
   | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` |
   | `SUNDAY_ALLOW_MOCK` | `false`（配了真 key 后关掉占位模式） |

4. **生成公网域名**：`Settings` → `Networking` → `Generate Domain`。
   你会得到一个类似 `https://sundayos-xxxx.up.railway.app` 的地址。

5. **等待部署**：Railway 自动安装依赖、启动。看到 healthcheck `/health` 变绿即成功。

## 验证上线

浏览器打开：`https://你的域名/health`
应看到：`{"status":"ok","engines":["deepseek-chat","deepseek-reasoner"],...}`
（`engines` 里出现 `deepseek` 就说明真实引擎已接上，不再是 mock。）

发一句真实对话（把域名和 key 换成你的）：
```bash
curl -X POST https://你的域名/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 你设的SUNDAY_API_KEY" \
  -d '{"message":"你好Sunday","user_id":"me"}'
```

## 让网页控制台连到云端后端（可选）
如果你也想部署 `console/` 前端，或让本地前端连云端后端：
- 前端环境变量 `SUNDAY_BACKEND_URL` = 你的 Railway 域名；`SUNDAY_API_KEY` = 同一串密码。
- 前端通过服务端代理调用，key 不暴露到浏览器。

## iPhone 快捷指令连云端
把快捷指令里的 API 地址填成 `https://你的域名/api/chat`，请求头加 `X-API-Key`。详见 [1.0/USER_GUIDE.md](../../1.0/USER_GUIDE.md) 的快捷指令配置。

## 花费与限制
- Railway 免费额度有限（约每月 $5 用量/500 小时），个人常在线的小服务通常够用；超了会休眠或需付费。
- ⚠️ **当前记忆只在内存里**：Railway 重新部署/重启后，之前聊天记忆会清空。要持久记忆，需接数据库（路线图 Phase 1 收尾项：SQLite/Postgres + 挂载卷）。
- 建议在 Railway 加一个 **Volume**（持久磁盘）挂到 `/app/data`，并把 `SUNDAY_DB_PATH` 指过去——等记忆持久化实现后即可保留记忆。

## 排错
| 现象 | 原因 | 解决 |
|------|------|------|
| 部署失败 / 找不到 app | 没设 Root Directory | `Settings → Root Directory` 填 `backend` |
| `/health` 里 engines 是 mock | 没配 DeepSeek key 或没关 mock | 检查 `DEEPSEEK_API_KEY`，设 `SUNDAY_ALLOW_MOCK=false` |
| 调用返回 401 | 没带对 `X-API-Key` | 头里的值要和 `SUNDAY_API_KEY` 一致 |
| 健康检查超时 | 启动慢/端口错 | 确认用了 `$PORT`（已在 Procfile/railway.json 配好） |
