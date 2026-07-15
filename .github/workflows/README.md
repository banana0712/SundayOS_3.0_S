# GitHub Actions 自动部署配置

## 设置步骤

1. 在 GitHub 仓库页面，进入 **Settings** → **Secrets and variables** → **Actions**

2. 点击 **New repository secret**，添加以下 3 个 secrets：

### SERVER_HOST
```
45.207.220.124
```

### SERVER_USER
```
root
```

### SERVER_SSH_KEY
```
（粘贴你的 SSH 私钥内容）
```

**获取 SSH 私钥的方法：**

如果服务器上还没有 SSH 密钥对，先生成一个：

```bash
# 在小兔云服务器上执行：
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions -N ""

# 将公钥添加到 authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# 查看私钥（复制这个内容到 GitHub Secrets）
cat ~/.ssh/github_actions
```

如果已经有密钥，直接用现有的私钥（通常在 `~/.ssh/id_rsa` 或 `~/.ssh/id_ed25519`）。

## 工作原理

- **自动触发**：每次 push 到 main 分支时自动部署
- **手动触发**：在 GitHub Actions 页面点击 "Run workflow" 手动部署
- **部署流程**：
  1. SSH 连接到服务器
  2. git pull 拉取最新代码
  3. 更新 Python 依赖
  4. 重启 sunday.service
  5. 验证健康端点

## 验证部署

部署完成后，访问：
- http://45.207.220.124:8005/health
- http://45.207.220.124:8005/console

检查 `version` 字段是否更新。

## 故障排查

如果部署失败：

1. 查看 GitHub Actions 日志
2. SSH 到服务器查看服务日志：
   ```bash
   sudo journalctl -u sunday -n 100
   ```
3. 手动验证服务状态：
   ```bash
   systemctl status sunday.service
   ```
