# Sunday OS 部署脚本使用指南

## 📁 可用脚本

| 脚本 | 用途 | 何时使用 |
|------|------|---------|
| `deploy_from_server.sh` | 完整同步+推送+部署 | **推荐**：从本地推送到服务器，再从服务器推送到GitHub |
| `manual_deploy.sh` | 快速手动部署 | 本地已推送到GitHub，只需服务器拉取+重启 |
| `quick_deploy.sh` | 仅重启服务 | 服务器代码已是最新，只需重启 |
| `deploy.sh` | 全新服务器部署 | 在全新Ubuntu服务器上首次安装 |

## 🚀 推荐部署流程

### 方案 A：从服务器推送到 GitHub（推荐，网络稳定）

```bash
# 在本地运行
./deploy_from_server.sh
```

**工作流程：**
1. 将本地代码 rsync 同步到服务器
2. 在服务器上 git commit + push 到 GitHub
3. 重启服务器上的 Sunday 服务
4. 验证健康状态

**优点：** 服务器在香港，连接 GitHub 更稳定

---

### 方案 B：传统推送（本地网络稳定时）

```bash
# 1. 本地推送到 GitHub
git push origin main

# 2. 服务器拉取并部署
./manual_deploy.sh
```

---

## 🔐 安全提示

**首次使用时，脚本会要求输入服务器密码。**

如果想免密码登录（推荐），设置 SSH 密钥：

```bash
# 在本地生成密钥（如果还没有）
ssh-keygen -t ed25519 -C "your-email@example.com"

# 复制公钥到服务器
ssh-copy-id root@45.207.220.124
```

---

## ✅ 验证部署

部署完成后，验证服务器状态：

```bash
# 检查健康端点
curl http://45.207.220.124:8005/health

# 查看服务日志
ssh root@45.207.220.124 'journalctl -u sunday -n 50'

# 检查服务状态
ssh root@45.207.220.124 'systemctl status sunday.service'
```

预期输出：
```json
{
    "status": "ok",
    "version": "0.10.0",
    "engines": ["deepseek-chat", "deepseek-reasoner", "sunday-chat"],
    ...
}
```

---

## 🤖 GitHub Actions 自动部署

配置完成后，每次 push 到 main 分支自动触发部署。

详见：`.github/workflows/README.md`

---

## 📊 服务器信息

- **地址**: 45.207.220.124:8005
- **位置**: 小兔云香港
- **配置**: 2H2G
- **服务**: systemd (sunday.service)
- **项目路径**: /opt/sundayos
