# Sunday OS 服务器部署信息

> 生产服务器的详细配置和访问信息。**权威记录，避免推理**。

---

## 服务器基本信息

| 项目 | 信息 |
|------|------|
| **平台** | 小兔云（Xiaotucloud） |
| **位置** | 香港 |
| **IP 地址** | 45.207.220.124 |
| **端口** | 8005 |
| **配置** | 2核 2GB 内存 |
| **操作系统** | Ubuntu（待确认具体版本） |
| **服务管理** | systemd (sunday.service) |

---

## 访问端点

### HTTP API
```
http://45.207.220.124:8005
```

### 健康检查
```bash
curl http://45.207.220.124:8005/health
```

**响应示例**（2026-07-17）：
```json
{
  "status": "ok",
  "version": "0.10.1",
  "engines": ["deepseek-chat", "deepseek-reasoner", "sunday-chat"],
  "memory_nodes": 77,
  "conversation_count": 8,
  "embedder": "semantic",
  "embedder_provider": "ollama",
  "embedder_degraded": false,
  "embedding_dim": 768
}
```

### Web 控制台
```
http://45.207.220.124:8005/console
```

### 前端应用
```
http://45.207.220.124:8005/
```

---

## SSH 访问

```bash
ssh root@45.207.220.124
```

**密码**: FvzHPk2crcQ6（存储在 `deploy_auto.py` 中）

⚠️ **安全提示**: 建议迁移到 SSH 密钥认证：
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
ssh-copy-id root@45.207.220.124
```

---

## 服务管理

### 查看服务状态
```bash
ssh root@45.207.220.124 'systemctl status sunday.service'
```

### 查看服务日志
```bash
ssh root@45.207.220.124 'journalctl -u sunday -n 50'
```

### 重启服务
```bash
ssh root@45.207.220.124 'systemctl restart sunday.service'
```

### 停止服务
```bash
ssh root@45.207.220.124 'systemctl stop sunday.service'
```

### 启动服务
```bash
ssh root@45.207.220.124 'systemctl start sunday.service'
```

---

## 部署流程

详见：
- `DEPLOYMENT.md` — 部署脚本使用指南
- `.claude/skills/deploy.md` — `/deploy` 技能说明
- `deploy_auto.py` — 自动化部署脚本

**推荐流程**（通过 `/deploy` 技能）：
1. 本地代码 → GitHub
2. GitHub → 服务器拉取
3. 服务器重启 sunday.service
4. 健康检查验证

---

## 常见问题

### Q: 为什么端口是 8005 而不是 8000？

A: 服务器上可能运行了多个服务，8005 是 Sunday OS 的专用端口。在本地开发时默认使用 8000。

### Q: 如何验证部署是否成功？

A: 运行健康检查命令：
```bash
curl http://45.207.220.124:8005/health
```
返回 `{"status": "ok", ...}` 表示服务正常。

### Q: 如何查看当前运行的版本？

A: 健康检查响应中的 `version` 字段显示当前版本号。

---

## 历史记录

| 日期 | 事件 |
|------|------|
| 2026-07-17 | 验证部署状态，服务器运行版本 0.10.1，健康状态正常 |
| 2024-xx-xx | 初始部署到小兔云香港服务器 |

---

## 相关文档

- `DEPLOYMENT.md` — 部署脚本详细说明
- `.claude/skills/deploy.md` — 一键部署技能
- `.github/workflows/README.md` — GitHub Actions 自动部署配置
- `docs/ERRATA.md` — 文档勘误表
