# 用户交互日志系统设计方案

> **问题**: AI 智能体上下文理解能力弱，容易丢失上下文。需要完整的操作日志记录用户端+后端的所有交互。

---

## 现状分析

### 已有的日志系统
- **log_engine.py**: 仅记录后端引擎层
  - ✅ 路由决策 (route_decision)
  - ✅ 引擎调用 (engine_call)
  - ✅ 错误和回退 (engine_error, engine_fallback)
  - ❌ **缺少用户交互层**：用户输入、完整请求、完整响应

### 关键问题
1. **用户说了什么** → 只记录了 `msg_len`，没有完整内容
2. **系统返回了什么** → 只记录了 `reply_len`，没有完整响应
3. **上下文是什么** → 没有记录对话历史、记忆检索结果
4. **中间过程** → 没有记录护栏检查、工具调用、记忆写入

**结果**: 事后无法重现问题，智能体无法从日志中理解完整交互流程。

---

## 设计方案

### 1. 日志层级架构

```
┌─────────────────────────────────────────┐
│  User Interaction Log (新增)            │  ← 完整用户会话
│  - 用户输入 (完整消息)                   │
│  - 系统输出 (完整响应)                   │
│  - 上下文 (记忆/历史)                    │
│  - 中间步骤 (工具调用/护栏)              │
├─────────────────────────────────────────┤
│  Engine Layer Log (已有)                │  ← 引擎技术细节
│  - 路由决策                              │
│  - 引擎调用                              │
│  - token/成本统计                        │
└─────────────────────────────────────────┘
```

### 2. 新增日志方法

在 `log_engine.py` 中扩展 `Logger` 类：

```python
# ── 用户交互完整记录 ────────────────────────────────────

def interaction_start(
    self, 
    session_id: str,
    user_id: str, 
    request_id: str,
    timestamp: str,
    user_message: str,
    conversation_id: str = None,
    metadata: dict = None
) -> None:
    """记录用户请求开始"""
    _emit("INFO", "interaction_start",
          session_id=session_id,
          user_id=user_id,
          request_id=request_id,
          timestamp=timestamp,
          user_message=user_message,
          conversation_id=conversation_id,
          metadata=metadata or {})

def context_retrieved(
    self,
    request_id: str,
    memory_nodes: list[dict],
    conversation_history: list[dict],
    retrieved_count: int
) -> None:
    """记录检索到的上下文"""
    _emit("INFO", "context_retrieved",
          request_id=request_id,
          memory_nodes=memory_nodes,
          conversation_history=conversation_history,
          retrieved_count=retrieved_count)

def guardrail_check(
    self,
    request_id: str,
    stage: str,  # "input" | "output" | "tool"
    passed: bool,
    reason: str = "",
    redacted_fields: list = None
) -> None:
    """记录护栏检查结果"""
    _emit("INFO" if passed else "WARN", "guardrail",
          request_id=request_id,
          stage=stage,
          passed=passed,
          reason=reason,
          redacted_fields=redacted_fields or [])

def tool_call(
    self,
    request_id: str,
    tool_name: str,
    tool_args: dict,
    tool_result: any,
    success: bool,
    latency_ms: float,
    error: str = None
) -> None:
    """记录工具调用"""
    _emit("INFO" if success else "ERROR", "tool_call",
          request_id=request_id,
          tool_name=tool_name,
          tool_args=tool_args,
          tool_result=str(tool_result)[:500],  # 截断避免过长
          success=success,
          latency_ms=latency_ms,
          error=error)

def memory_write(
    self,
    request_id: str,
    node_id: str,
    node_type: str,  # "interaction" | "reflection" | "experience"
    content_preview: str,
    importance: float = None
) -> None:
    """记录记忆写入"""
    _emit("INFO", "memory_write",
          request_id=request_id,
          node_id=node_id,
          node_type=node_type,
          content_preview=content_preview[:200],
          importance=importance)

def interaction_complete(
    self,
    request_id: str,
    user_id: str,
    system_response: str,
    total_latency_ms: float,
    tokens_used: int,
    cost_usd: float,
    engine_used: str,
    success: bool,
    error: str = None
) -> None:
    """记录完整交互结束"""
    _emit("INFO" if success else "ERROR", "interaction_complete",
          request_id=request_id,
          user_id=user_id,
          system_response=system_response,
          total_latency_ms=total_latency_ms,
          tokens_used=tokens_used,
          cost_usd=cost_usd,
          engine_used=engine_used,
          success=success,
          error=error)
```

### 3. 日志文件结构

```
/var/log/sundayos/
├── engine.log          # 现有的引擎日志 (5MB rotate)
├── interaction.log     # 新增：完整用户交互 (20MB rotate)
├── interaction.log.1
├── interaction.log.2
└── interaction.log.3
```

**交互日志示例**:
```json
{
  "ts": "2026-07-17 18:30:45",
  "level": "INFO",
  "cat": "interaction_start",
  "session_id": "sess_abc123",
  "user_id": "user_001",
  "request_id": "req_xyz789",
  "user_message": "帮我分析一下最近的内存使用情况",
  "conversation_id": "conv_456",
  "metadata": {"client": "web", "ip": "192.168.1.100"}
}

{
  "ts": "2026-07-17 18:30:45",
  "level": "INFO",
  "cat": "context_retrieved",
  "request_id": "req_xyz789",
  "memory_nodes": [
    {"id": "mem_001", "content": "用户关心系统性能", "importance": 0.8},
    {"id": "mem_002", "content": "上次讨论过内存优化", "importance": 0.6}
  ],
  "conversation_history": [
    {"role": "user", "content": "系统最近有点慢"},
    {"role": "assistant", "content": "我来帮你检查一下"}
  ],
  "retrieved_count": 2
}

{
  "ts": "2026-07-17 18:30:46",
  "level": "INFO",
  "cat": "guardrail",
  "request_id": "req_xyz789",
  "stage": "input",
  "passed": true,
  "reason": "all checks passed"
}

{
  "ts": "2026-07-17 18:30:47",
  "level": "INFO",
  "cat": "tool_call",
  "request_id": "req_xyz789",
  "tool_name": "memory_search",
  "tool_args": {"query": "内存使用", "limit": 5},
  "tool_result": "[{...}, {...}]",
  "success": true,
  "latency_ms": 120.5
}

{
  "ts": "2026-07-17 18:30:48",
  "level": "INFO",
  "cat": "interaction_complete",
  "request_id": "req_xyz789",
  "user_id": "user_001",
  "system_response": "根据我的分析，最近内存使用主要集中在...",
  "total_latency_ms": 2340.5,
  "tokens_used": 1520,
  "cost_usd": 0.0045,
  "engine_used": "deepseek-chat",
  "success": true
}
```

### 4. 集成点

需要在以下位置插入日志调用：

| 位置 | 日志方法 | 时机 |
|------|---------|------|
| `main.py:chat_endpoint` 开始 | `interaction_start()` | 收到用户请求 |
| `context_builder.py` | `context_retrieved()` | 检索上下文后 |
| `guardrails/pipeline.py` | `guardrail_check()` | 每次检查后 |
| `cognition/react_loop.py` | `tool_call()` | 工具调用前后 |
| `memory/sqlite_store.py` | `memory_write()` | 写入记忆节点 |
| `main.py:chat_endpoint` 结束 | `interaction_complete()` | 返回响应前 |

### 5. 日志查询工具

新增 API 端点用于查询日志：

```python
# GET /api/debug/logs/interaction?request_id=xxx
# GET /api/debug/logs/interaction?user_id=xxx&limit=10
# GET /api/debug/logs/session?session_id=xxx

@router.get("/debug/logs/interaction")
async def get_interaction_logs(
    request_id: str = None,
    user_id: str = None,
    session_id: str = None,
    limit: int = 100
):
    """查询用户交互日志"""
    # 解析 interaction.log
    # 按条件筛选
    # 返回 JSON 数组
```

---

## 收益

### 对 AI 智能体
1. ✅ **完整上下文** - 可以查看完整对话历史和记忆
2. ✅ **问题重现** - 看到用户输入什么、系统返回什么
3. ✅ **调试工具调用** - 看到工具参数和返回值
4. ✅ **理解护栏拦截** - 看到为什么某些请求被拦截

### 对开发者
1. ✅ **用户反馈调试** - "AI 回答不对" → 查日志看上下文
2. ✅ **性能分析** - 看哪个环节慢
3. ✅ **成本追踪** - 每次交互的 token 和费用
4. ✅ **异常诊断** - 完整的错误堆栈和上下文

---

## 隐私和安全

### 敏感信息处理
1. **PII 自动脱敏** - 日志中的电话、邮箱、身份证号用 `***` 替换
2. **API Key 脱敏** - 只记录前4位和后4位
3. **日志加密存储** - 可选：敏感环境启用日志文件加密
4. **访问控制** - `/api/debug/logs/*` 需要管理员权限

### 配置选项
```python
# .env
SUNDAY_LOG_INTERACTION=true           # 是否启用交互日志
SUNDAY_LOG_FULL_CONTENT=true          # 是否记录完整消息内容
SUNDAY_LOG_MAX_MESSAGE_LEN=10000      # 消息最大长度（超过截断）
SUNDAY_LOG_RETENTION_DAYS=30          # 日志保留天数
SUNDAY_LOG_REDACT_PII=true            # 是否自动脱敏 PII
```

---

## 实施步骤

### Phase 1: 核心日志方法 (1-2h)
- [ ] 扩展 `log_engine.py` 添加 6 个新方法
- [ ] 支持独立的 `interaction.log` 文件
- [ ] 添加配置选项

### Phase 2: 集成日志调用 (2-3h)
- [ ] `main.py` 添加 start/complete
- [ ] `context_builder.py` 添加 context_retrieved
- [ ] `guardrails` 添加 guardrail_check
- [ ] `react_loop.py` 添加 tool_call
- [ ] `memory` 添加 memory_write

### Phase 3: 查询 API (1-2h)
- [ ] 新增 `/api/debug/logs/interaction` 端点
- [ ] 新增 `/api/debug/logs/session` 端点
- [ ] 添加权限检查

### Phase 4: 前端展示 (可选, 2-3h)
- [ ] Console 新增"交互日志"页面
- [ ] 按会话展示完整流程
- [ ] 支持搜索和筛选

---

## 相关文档

- `backend/app/log_engine.py` - 现有日志引擎
- `docs/guides/DEBUGGING.md` - 调试指南
- `docs/3.0/08-security-and-autonomy.md` - 安全规范
