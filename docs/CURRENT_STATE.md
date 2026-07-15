# CURRENT_STATE.md · Sunday OS 当前开发状态

> 诚实、可验证的当前状态。每次功能开发完成后必须更新本文件。

**版本** 2.2 · **最后更新** 2026-07-15（v0.10.0）

---

## 1. 总览一眼

```
文档体系     ✅ 工程文档 + 指南 + 12 ADR + CHANGELOG + 开发契约 + /checkup 体检
3.0 设计集   ✅ 13 技术规范 + 12 ADR（001-012）+ 论文附录
后端实现     ✅ Phase 1 ~96%：引擎路由✅ 记忆三层✅ 反思✅ ReAct✅ SSE✅
              护栏✅ Chat UI✅ 账号系统✅ 反馈学习✅ 多气泡✅ 质量路由✅
              对话持久化✅ 语义 embedding（Qwen）✅ Dashboard 健康/事件真数据✅
前端口       86 测试全过（1.2s）
前端实现     ✅ Dashboard + Brain + Memory + Chat + 移动端全适配 + 登录 UI
防腐机制     ✅ ENGINEERING_CONTRACT（规矩）+ /checkup（裁判）闭环
版本管理     ✅ v0.10.0 · SemVer + Keep a Changelog
服务器       ✅ 小兔云香港 2H2G 24/7 · /console + / 双入口
```

---

## 2. 后端：能做什么 & 不能做什么

### ✅ 能做的

| 能力 | 代码位置 |
|------|---------|
| 启动 FastAPI 服务（43 路由） | `backend/app/main.py` |
| 动态路由（质量优先 + 5 维度评分） | `backend/app/engines/router.py` |
| 路由决策可追溯（RouteTrace） | 同上 |
| 引擎失败自动回退 + 熔断器 | 同上 + `tests/test_router.py` |
| 3 个真实引擎（DeepSeek×2 + 豆包 ×1）+ Mock 后备 | `backend/app/engines/registry.py` |
| 自定义引擎（CUSTOM_API_KEY 环境变量） | 同上 |
| 用户注册/登录/Token 认证（pbkdf2） | `backend/app/auth/__init__.py` |
| 会话内记忆检索（复合评分 + SQLite 持久化） | `backend/app/memory/sqlite_store.py` |
| 双系统切换（Talker/Reasoner 判据） | `backend/app/cognition/dispatch.py` |
| ReAct 循环（Thought→Action→Observation） | `backend/app/cognition/react_loop.py` |
| SSE 流式聊天 | `POST /api/chat/stream` |
| 注入/越狱拦截 + PII 脱敏 | `backend/app/guardrails/pipeline.py` |
| 结构运行日志（JSON + 轮转） | `backend/app/log_engine.py` |
| 自然多气泡消息（burst_split） | `backend/app/cognition/burst_split.py` |
| 反馈学习系统（👍👎 → 质量调整 + 偏好注入） | `backend/app/persona/feedback_parser.py` + `preferences.py` |
| 话题感知上下文组装 | `backend/app/cognition/context_builder.py` |
| 共情管道（UU 情感 + IRG 指导） | `backend/app/persona/empathy.py` |
| 反思引擎 + 体验抽象层 | `backend/app/memory/reflection.py` + `experience.py` |
| 技能注册中心（8 技能） | `backend/app/cognition/tools.py` |
| 人格系统（persona.yaml Git 版本化） | `backend/app/persona/__init__.py` |
| Web Chat UI（双语，同源）+ 登录/注册卡片 | `backend/app/webchat.py` |
| Console SPA（Next.js 15 静态导出） | `console/src/` |
| 调试端点：overview + env + routing + context | `backend/app/main.py` |
| 71 单元测试 | `backend/tests/` |
| 自有服务器 24/7 运行 | `45.207.220.124:8005` |

### ❌ 还不能做的

| 缺失 | 影响 | 优先级 | 计划 |
|------|------|--------|------|
| Token 无过期 + 无登出端点 | 安全性弱（个人使用可接受） | 🟡 中 | 下次 |
| 无撞库保护 | 同上 | 🟡 中 | 部署公网前 |
| main.py ~1380 行未拆分 | 维护性差 | 🟡 中 | 下次（APIRouter 拆域） |
| 前端未接真实后端数据 | 仪表盘全 mock | 🟡 中 | 下次 |
| 无前端自动化测试 | — | 🟢 低 | Phase 2 |
| runtime 未收口（模块级全局与 runtime.* 并存） | 双份真相源 | 🟡 中 | 下次 |
| i18n 硬编码 30+ 处 | Console 有中英混杂 | 🟢 低 | UI 审计时 |

---

## 3. 近期变更（2026-07-15）

| 模块 | 内容 |
|------|------|
| 对话持久化 | `SQLiteConversationStore` —— 会话/消息落 SQLite，重启不丢（`app/conversation/sqlite_store.py`） |
| 语义 Embedding | Qwen text-embedding-v3（1024-dim）接入 + 启动自动重嵌入 + `/health` 降级可见（`app/memory/embedding.py`） |
| 认证系统 | 注册/登录/Token 双轨制（`app/auth/__init__.py`） |
| 反馈学习 | NL 解析 → 偏好注入 prompt（ADR-012） |
| 多气泡 | burst_split 自然分段（Stephanie NAACL 2025） |
| 质量路由 | ADR-011 quality-first 权重表 |
| 自定义引擎 | CUSTOM_API_KEY → 豆包 doubao-seed-character-260628 |
| 移动端重设计 | 底部导航、sidebar overlay、44px 触摸、键盘适配 |
| 安全加固 | 会话/记忆所有权校验 + 错误消息净化 |
| 日志系统 | 结构化 JSON logger + /api/debug/routing |
| 工程优化 | .gitignore 补全、死代码清除、VERSION→0.8.0 |

---

## 4. 测试覆盖（86 passed / 1.2s）

| 测试文件 | 数量 | 覆盖范围 |
|---------|------|---------|
| `test_router.py` | 9 | 路由打分、隐私/工具约束、回退链、熔断器 |
| `test_memory.py` | 7 | 语义排序、重要性加成、recency 衰减、用户隔离 |
| `test_dispatch_guardrails.py` | 10 | 双系统判据、注入拦截、PII 脱敏、工具风险 |
| `test_conversation_persist.py` | 8 | 会话跨连接持久化、消息存活、删除落库、用户隔离 |
| `test_reembed.py` | 7 | 维度失配检测、重嵌入迁移、幂等性、检索恢复 |
| 其他 | 45 | 会话管理、共情、ReAct、护栏、体验层 |
| `npm run build` | ✅ | TypeScript 类型检查通过 |

---

## 5. 环境依赖

| 依赖 | 配置 |
|------|------|
| Python | 3.11+ |
| Node | 已装 |
| 数据库 | SQLite（sunday.db）—— WAL 模式 |
| 引擎 | DeepSeek×2 + 豆包（sunday-chat） |
| 服务器 | 45.207.220.124:8005 |
| Git | origin/main ← GitHub |

## 6. 验证命令

```bash
cd backend
python -m pytest -q                    # 71 passed
python -m uvicorn app.main:app --port 8000
curl http://localhost:8000/health

cd console
npm run build                          # 类型检查通过
```
