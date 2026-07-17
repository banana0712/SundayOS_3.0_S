# /deploy · SundayOS 一键部署

> 用法：在任意会话输入 `/deploy`，自动完成「本地提交 → 服务器部署」全流程。

---

## 执行流程

### 完整部署步骤

1. **提交本地改动**（如果有未提交的文件）
   - `git add` 相关文件
   - `git commit` 带时间戳和 Co-Authored-By
   - `git push origin main`（可选，如果 GitHub 网络可用）

2. **自动上传到服务器**
   - 使用 `deploy_auto.py` 脚本
   - 通过 SSH + SFTP 直接上传修改的文件
   - 无需依赖 GitHub（网络不稳定也能部署）

3. **重启服务**
   - `systemctl restart sunday.service`
   - 检查服务状态

4. **验证部署**
   - 显示服务运行状态
   - 可选：测试关键 API 端点

---

## AI 执行指令

当用户输入 `/deploy` 时，按以下步骤执行：

### 1. 检查未提交的改动

```bash
git status --short
```

如果有改动，提交：

```bash
git add <修改的文件>
git commit -m "deploy: auto-deploy from local at $(date '+%Y-%m-%d %H:%M:%S')

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### 2. 尝试推送到 GitHub（可选）

```bash
git push origin main
```

如果失败（网络问题），继续执行下一步（不阻塞部署）。

### 3. 执行自动部署脚本

```bash
python deploy_auto.py
```

脚本会：
- 连接服务器（root@45.207.220.124，密码已内置）
- 上传修改的文件到 /opt/sundayos
- 重启 sunday.service
- 显示服务状态

### 4. 部署成功提示

输出：
- ✓ 文件上传完成
- ✓ 服务已重启
- 服务状态（Active: active (running)）
- API 地址：http://45.207.220.124:8005

---

## 前提条件

- `deploy_auto.py` 存在于项目根目录
- Python 3.x 已安装
- paramiko 库已安装（`pip install paramiko`）
- 服务器密码已配置在脚本中

---

## 输出示例

```
==================================================
  Sunday OS 完整部署
  本地 → GitHub → 服务器
==================================================

>>> 第一步：推送本地代码到 GitHub

>>> 添加所有改动...
✓ 已添加

>>> 提交改动...
✓ 已提交

>>> 推送到 GitHub...
✓ 推送成功

>>> 第二步：服务器部署

>>> 连接服务器...
✓ 连接成功

>>> 进入项目目录...
/opt/sundayos
✓ 进入项目目录完成

>>> 拉取最新代码...
Updating abc123..def456
✓ 拉取最新代码完成

>>> 检查版本...
0.10.0
✓ 检查版本完成

>>> 重启服务...
✓ 重启服务完成

>>> 验证健康端点...
{
    "status": "ok",
    "version": "0.10.0",
    ...
}
✓ 验证健康端点完成

==================================================
  ✅ 部署完成！
==================================================
```

---

## 执行约束

- **自动提交消息**：包含时间戳 + Co-Authored-By Claude
- **失败处理**：任一步骤失败立即中止并报错
- **幂等性**：如果本地已是最新（无改动），只执行服务器部署
- **不做危险操作**：不会 force push、不会删除文件、不会修改服务器配置

---

## 故障排查

如果部署失败，AI 会输出详细错误信息。常见问题：

1. **Git push 失败**：检查网络、GitHub Token 是否有效
2. **SSH 连接失败**：检查服务器密码、IP 是否正确
3. **服务重启失败**：检查服务器日志 `journalctl -u sunday -n 50`
4. **健康检查失败**：检查服务是否正常启动

---

## 安全提示

⚠️ 服务器密码明文存储在 `deploy_auto.py` 中，仅供个人项目使用。

建议后续改为 SSH 密钥认证：
```bash
ssh-copy-id root@45.207.220.124
```
