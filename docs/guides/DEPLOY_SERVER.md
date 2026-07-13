# DEPLOY_SERVER.md · 云服务器部署指南

> 把 Sunday OS 部署到云服务器，24 小时在线，手机/电脑/平板随时访问。

---

## 0. 你需要什么

| 项目 | 要求 |
|------|------|
| 服务器 | 2H2G（已选小兔云香港），Ubuntu 22.04 或 Debian 12 |
| IP | 云服务商会给你公网 IPv4 |
| 端口 | 8005（Sunday 后端）+ 可选 80（Nginx） |
| 域名 | ❌ 不需要（直接用 IP 访问） |

---

## 1. 登录服务器

打开终端（Mac/Linux 用 Terminal，Windows 用 Git Bash 或 PowerShell）：

```bash
ssh root@你的服务器IP
```

输入小兔云给你的 root 密码，首次登录。

---

## 2. 部署（一键脚本）

把仓库里的部署脚本上传到服务器，或者直接下载：

```bash
# 方式一：从 GitHub 下载
apt-get update && apt-get install -y git
git clone https://github.com/banana0712/SundayOS_3.0_S.git /tmp/sundayos
cd /tmp/sundayos
chmod +x deploy.sh
sudo ./deploy.sh
```

脚本会问三个问题：
```
Sunday API Key（访问密码，如 sunday0712）: sunday0712
DeepSeek API Key（可选，不填则 mock 模式）: sk-你的key
DeepSeek Base URL（默认 https://api.deepseek.com/v1）: [直接回车]
```

等待 3-5 分钟，Python 和所有依赖安装完成后，看到 `✅ Sunday OS 部署成功！` 就完成了。

---

## 3. 安装 Ollama（语义 Embedding）

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
```

详见 [OLLAMA_SETUP.md](OLLAMA_SETUP.md)。不装也能用——Sunday 自动回退到 hash embedder。

---

## 4. 验证

```bash
# 服务器上验证
curl http://localhost:8005/health
# 返回 {"status":"ok","engines":["deepseek-chat","deepseek-reasoner"],...}

# 从任何设备打开浏览器访问
http://你的服务器IP:8005
```

---

## 4. 手机/平板使用

浏览器打开 `http://你的服务器IP:8005`，输入 Key `sunday0712`，就能和 Sunday 聊天了。

快捷指令配置详见 [SHORTCUTS_SETUP.md](SHORTCUTS_SETUP.md)，把 URL 改成 `http://你的服务器IP:8005/api/shortcuts/chat`。

---

## 5. 常用运维命令

```bash
# 查看 Sunday 状态
sudo systemctl status sunday

# 重启 Sunday（代码更新后需要）
sudo systemctl restart sunday

# 查看实时日志
sudo journalctl -u sunday -f

# 查看最近 50 条日志
sudo journalctl -u sunday -n 50

# 停止 Sunday
sudo systemctl stop sunday

# 查看端口是否在监听
ss -tlnp | grep 8005

# 查看内存使用
free -h

# 查看磁盘使用
df -h
```

---

## 6. 更新代码

服务器上的 Sunday 通过 `deploy.sh` 会自动 clone GitHub 仓库。要更新到最新版本：

```bash
cd /opt/sundayos
git pull origin main
sudo systemctl restart sunday
```

---

## 7. （可选）Nginx 反向代理

加上 Nginx 可以用域名访问、自动 HTTPS、隐藏端口号。

```bash
# 安装 Nginx
sudo apt-get install -y nginx

# 创建配置
sudo tee /etc/nginx/sites-available/sunday <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;           # 重要：SSE 流式需要关闭缓冲
        proxy_cache off;
    }
}
EOF

# 启用
sudo ln -s /etc/nginx/sites-available/sunday /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

生效后直接访问 `http://你的IP`（不需要加端口号）。

---

## 8. 安全建议

| 优先级 | 建议 |
|--------|------|
| 🔴 | 改 SSH 端口（默认 22 被扫得太厉害） |
| 🔴 | 禁用 root 密码登录，改用 SSH 密钥 |
| 🟡 | 换一个复杂的 Sunday API Key（不要用 sunday0712） |
| 🟡 | 配 ufw 防火墙，只开放 22/80/8005 |
| 🟢 | 定期备份 `/opt/sundayos/backend/sunday.db` |

```bash
# 快速防火墙配置
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 8005/tcp
sudo ufw enable
```

---

## 9. 故障排查

| 现象 | 诊断命令 | 原因 |
|------|---------|------|
| 无法访问 8005 | `sudo systemctl status sunday` | 服务没启动 |
| 访问返回 502 | `sudo journalctl -u sunday -n 20` | Python 代码异常 |
| 回复是 mock echo | `.env` 没配 DeepSeek Key | mock 模式运行 |
| 回复是"引擎不可用" | `cat /opt/sundayos/backend/.env` | DeepSeek Key 过期或无效 |
| git clone 失败 | `ping github.com` | 服务器连不上 GitHub |
