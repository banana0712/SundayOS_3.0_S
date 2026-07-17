# 服务器部署指南 - 交互日志系统

> 部署交互日志系统到生产服务器（小兔云香港 45.207.220.124）

---

## 部署步骤

### 1. SSH 连接到服务器

```bash
ssh root@45.207.220.124
```

### 2. 进入项目目录并拉取最新代码

```bash
cd /opt/sundayos
git pull origin main
```

### 3. 配置环境变量

编辑 systemd 服务文件：

```bash
nano /etc/systemd/system/sunday.service
```

在 `[Service]` 部分添加交互日志配置：

```ini
[Service]
# ... 现有配置 ...

# 交互日志系统配置
Environment="SUNDAY_LOG_INTERACTION=true"
Environment="SUNDAY_LOG_FULL_CONTENT=true"
Environment="SUNDAY_LOG_MAX_MESSAGE_LEN=10000"
Environment="SUNDAY_LOG_REDACT_PII=true"
Environment="SUNDAY_INTERACTION_LOG_PATH=/var/log/sundayos-interaction.log"
```

### 4. 创建日志目录并设置权限

```bash
# 确保日志目录存在
sudo mkdir -p /var/log

# 设置权限（假设服务以 root 运行，或替换为实际用户）
sudo touch /var/log/sundayos-interaction.log
sudo chmod 644 /var/log/sundayos-interaction.log
```

### 5. 重新加载并重启服务

```bash
# 重新加载 systemd 配置
systemctl daemon-reload

# 重启 Sunday 服务
systemctl restart sunday.service

# 查看服务状态
systemctl status sunday.service
```

### 6. 验证部署

#### 查看服务日志
```bash
journalctl -u sunday -f
```

#### 测试 API
```bash
curl -X POST http://localhost:8005/api/chat \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"测试交互日志"}'
```

#### 查看交互日志
```bash
# 实时查看
tail -f /var/log/sundayos-interaction.log

# 查看最近 20 条
tail -n 20 /var/log/sundayos-interaction.log

# 按 request_id 查找完整交互
grep "req_abc123" /var/log/sundayos-interaction.log
```

---

## 日志格式示例

每次完整交互会产生 5-6 条日志记录：

```json
{"ts": "2026-07-17 19:00:00", "level": "INFO", "cat": "interaction_start", "session_id": "conv_123", "user_id": "user_001", "request_id": "req_abc123def456", "user_message": "用户输入内容", "conversation_id": "conv_123", "metadata": {}}

{"ts": "2026-07-17 19:00:00", "level": "INFO", "cat": "guardrail", "request_id": "req_abc123def456", "stage": "input", "passed": true, "reason": "all checks passed", "redacted_fields": []}

{"ts": "2026-07-17 19:00:01", "level": "INFO", "cat": "context_retrieved", "request_id": "req_abc123def456", "memory_nodes": [...], "conversation_history": [], "retrieved_count": 3}

{"ts": "2026-07-17 19:00:02", "level": "INFO", "cat": "memory_write", "request_id": "req_abc123def456", "node_id": "mem_a1b2c3d4", "node_type": "episodic", "content_preview": "...", "importance": 6}

{"ts": "2026-07-17 19:00:03", "level": "INFO", "cat": "interaction_complete", "request_id": "req_abc123def456", "user_id": "user_001", "system_response": "系统响应内容", "total_latency_ms": 2340.5, "tokens_used": 1520, "cost_usd": 0.0045, "engine_used": "deepseek-chat", "success": true, "error": null}
```

---

## 日志分析命令

### 统计今天的交互次数
```bash
grep "interaction_start" /var/log/sundayos-interaction.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

### 查找失败的交互
```bash
grep "interaction_complete" /var/log/sundayos-interaction.log | \
  jq 'select(.success==false)'
```

### 查找护栏拦截
```bash
grep "guardrail" /var/log/sundayos-interaction.log | \
  jq 'select(.passed==false)'
```

### 统计最常用的引擎
```bash
grep "interaction_complete" /var/log/sundayos-interaction.log | \
  jq -r '.engine_used' | sort | uniq -c | sort -rn
```

### 计算平均响应时间
```bash
grep "interaction_complete" /var/log/sundayos-interaction.log | \
  jq '.total_latency_ms' | \
  awk '{sum+=$1; count++} END {print sum/count " ms"}'
```

---

## 日志轮转配置

交互日志会自动轮转：
- 主文件：`/var/log/sundayos-interaction.log` (最大 20MB)
- 备份：`/var/log/sundayos-interaction.log.1`, `.2`, `.3`

可以配置 logrotate 进行更细粒度的管理：

```bash
# 创建 logrotate 配置
sudo nano /etc/logrotate.d/sundayos-interaction

# 内容：
/var/log/sundayos-interaction.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

---

## 故障排查

### 日志文件未生成

1. 检查环境变量：
```bash
systemctl show sunday.service | grep SUNDAY_LOG
```

2. 检查目录权限：
```bash
ls -la /var/log/sundayos*
```

3. 查看服务日志中的错误：
```bash
journalctl -u sunday -n 100 | grep -i error
```

### 日志内容为空

1. 确认交互日志已启用：
```bash
curl http://localhost:8005/health
# 应该返回 v0.10.2 或更高版本
```

2. 检查代码版本：
```bash
cd /opt/sundayos
git log --oneline -1
# 应该显示最新的 commit
```

### 性能问题

如果日志记录影响性能：

1. 禁用完整内容记录：
```bash
# 在 sunday.service 中设置
Environment="SUNDAY_LOG_FULL_CONTENT=false"
```

2. 减小消息长度限制：
```bash
Environment="SUNDAY_LOG_MAX_MESSAGE_LEN=1000"
```

3. 完全禁用交互日志：
```bash
Environment="SUNDAY_LOG_INTERACTION=false"
```

---

## 安全注意事项

1. **日志包含敏感信息** - 虽然已经自动脱敏 PII，但日志仍包含用户对话内容
2. **访问控制** - 确保只有授权人员能访问 `/var/log/sundayos-interaction.log`
3. **定期清理** - 考虑设置日志保留策略（建议 30 天）
4. **备份** - 如需长期保存，定期备份到安全位置

---

## 版本信息

- **部署版本**: v0.10.2
- **Commit**: 2cf6558
- **部署时间**: 2026-07-17
- **功能**: 交互日志系统 Phase 1 & 2
