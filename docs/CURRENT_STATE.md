# CURRENT_STATE.md · Sunday OS 当前开发状态

> 诚实、可验证的当前状态。每次功能开发完成后必须更新本文件。不要夸大——本文件是下一个 AI Agent 理解"现在能做什么、不能做什么"的唯一依据。

**版本** 1.0 · **最后更新** 2026-07-13

---

## 1. 总览一眼

```
文档体系     ✅ 7 文件工程文档体系（AI_CONTEXT / ARCHITECTURE / CURRENT_STATE / ROADMAP / DESIGN_SYSTEM / PROJECT_MEMORY）+ AGENTS + CLAUDE + SUNDAY_CONTEXT
3.0 设计集   ✅ 13 技术规范 + 11 ADR（001-011）+ 论文附录
后端实现     🟡 Phase 1 ~45%：引擎路由✅ 记忆检索✅ 双系统判据✅ 护栏✅ Chat UI✅ 诊断✅
             28 测试全过（0.04s，纯离线）。记忆仅内存、ReAct 未接、反思未实现、无 SSE 流式
前端实现     🟡 Dashboard + Brain Viz + ⌘K 原型（Next.js 15，纯前端，数据全是 mock）
iPhone 集成  📄 仅设计（1.0 Shortcuts 方案文档）
Git 状态     干净，main 分支，与 origin/main 同步
```

---

## 2. 后端：能做什么 & 不能做什么

### ✅ 能做的

| 能力 | 如何验证 | 代码位置 |
|------|---------|---------|
| 启动 FastAPI 服务（含 8 个端点） | `uvicorn app.main:app --port 8000` | `backend/app/main.py` |
| 按任务复杂度动态路由到不同引擎 | mock-fast / mock-strong 自动选择 | `backend/app/engines/router.py` |
| 路由决策全过程可追溯（RouteTrace） | API 响应含 `trace` 字段 | 同上 |
| 引擎失败自动回退（回退链） | 单元测试：failing→backup 切换 | 同上 + `tests/test_router.py` |
| 熔断器（3 次失败熔断 60s 后半开） | 单元测试：连续失败后 is_open | 同上 |
| 接入真实引擎（DeepSeek/Qwen/OpenAI/Claude/Ollama） | 在 `.env` 填 Key 重启 | `backend/app/engines/registry.py` |
| 未配 Key 时 mock 模式自动启用 | 不填 Key 启动 → `mock-fast` + `mock-strong` | 同上 |
| 环境变量鲁棒读取（尾部空格容忍） | `env("DEEPSEEK_API_KEY ") ` 正确读取 | `registry.py:env()` |
| 会话内记忆检索（复合评分） | `POST /api/memory/search` | `backend/app/memory/store.py` |
| 双系统切换（Talker/Reasoner 判据） | 含"查一下"→reasoner，含"你好"→talker | `backend/app/cognition/dispatch.py` |
| 注入/越狱拦截 | `ignore all previous instructions` → 400 | `backend/app/guardrails/pipeline.py` |
| 输出 PII 脱敏 | email/手机号/身份证 → `[REDACTED]` | 同上 |
| 环境变量诊断接口（不泄露值） | `GET /api/debug/env` | `backend/app/main.py` |
| Web Chat UI（双语，同源） | 浏览器打开 `http://localhost:8000/` | `backend/app/webchat.py` |
| 28 个单元测试全部通过（0.04s） | `python -m pytest -q` | `backend/tests/` |
| Railway 一键部署 | Procfile + railway.json + .python-version | 仓库根 |

### ❌ 还不能做的

| 缺失 | 影响 | 优先级 | 计划 |
|------|------|--------|------|
| 记忆持久化（SQLite + ChromaDB） | 重启即失忆——身份连续性断裂 | 🔴 最高 | Phase 1 收尾 #1 |
| Reasoner 的 ReAct 循环 + 真实工具执行 | System2 只是路由到强引擎直接回，不会真执行多步推理 | 🔴 最高 | Phase 1→2 过渡 #2 |
| 反思引擎（记忆 L1→L2） | 记忆只有存储，没有理解——四角色质变的关键 | 🟡 高 | Phase 2 |
| SSE 流式端点 | API 只能等完整回复，不能边想边出 | 🟡 中 | Phase 1 收尾 |
| Experience 层（L3） | 缺少跨轨迹抽象能力 | 🟢 中低 | Phase 3 |
| 共情计算（CQU/UU/IRG） | 情感层未实现 | 🟢 中低 | Phase 2 |
| 技能系统（Skill Registry） | 缺少统一工具注册与管理 | 🟡 中 | Phase 2 |
| 意图/情感分类接真实引擎 | 当前是关键词启发式，非模型判断 | 🟡 中 | Phase 1 收尾 |
| LLM 安全分类器 | 护栏缺少基于 LLM 的语义级 moderation | 🟡 中 | Phase 1 收尾 |
| Ollama 本地引擎 | Provider 已定义但需手动配置 | 🟢 低 | Phase 4 |
| 人格系统（初始化+演化+锚定） | 人格是固定的 system prompt | 🟢 低 | Phase 3 |

---

## 3. 前端：能做什么 & 不能做什么

### ✅ 能做的

| 能力 | 状态 | 代码位置 |
|------|------|---------|
| Dashboard 指标卡片（8 指标 + 迷你 sparkline） | ✅ 全 mock 数据 | `console/src/components/views/dashboard.tsx` |
| 活动量折线图（SVG 手绘 48 数据点） | ✅ 全 mock 数据 | 同上 `BigLine` |
| 情绪雷达图（6 轴 SVG） | ✅ `useDrift()` 模拟漂移 | 同上 `MoodCard` |
| 健康状态（3 个 Donut 环 + 4 服务健康行） | ✅ mock 数据 | 同上 `HealthCard` |
| 目标进度（任务列表 + 进度徽章） | ✅ mock 数据 | 同上 `GoalCard` |
| 事件时间线（5 条 mock 事件） | ✅ mock 数据 | 同上 `EventsCard` |
| Brain 认知架构可视化（SVG 核心+8节点+负载环+信号动画） | ✅ 静态定义 8 个模块 | `console/src/components/views/brain.tsx` |
| 侧边栏导航（分组+激活态+spring动画） | ✅ | `console/src/components/shell/sidebar.tsx` |
| ⌘K 命令面板 | ✅ 键盘快捷键 + UI | `console/src/components/shell/command-palette.tsx` |
| 三栏布局（Sidebar+Content+Inspector） | ✅ 响应式 | `console/src/components/shell/app-shell.tsx` |
| 中/英双语（localStorage 持久化） | ✅ 翻译字典完整 | `console/src/i18n/` |
| Light/Dark 主题切换 | ✅ CSS 变量 + class 切换 | `console/src/store/ui.tsx` |
| 通用组件库（Card/Sparkline/Donut/Radar/Badge/SectionTitle） | ✅ 6 个组件 | `console/src/components/ui/primitives.tsx` |
| Design Language 1.0 token 全落地 | ✅ CSS 变量 + Tailwind 扩展 | `globals.css` + `tailwind.config.ts` |
| 尊重 `prefers-reduced-motion` | ✅ | `globals.css` |
| TypeScript 类型检查通过 | ✅ | `npm run build` |

### ❌ 还不能做的

| 缺失 | 影响 |
|------|------|
| **前端未接后端 API** | 所有数据（指标/情绪/健康/目标/事件）都是硬编码或随机漂移，不反映真实后端状态 |
| Memory Center 页面 | 有导航入口但只有 ComingSoon 占位 |
| Emotion 分析页面 | 同上 |
| Developer Console（实际功能） | 底部 Console Dock 只有 UI 外壳 |
| 真实的流式渲染 | ChatView 有基本实现但未接后端 SSE |
| 用户认证 UI | 登录/注册流未实现 |

---

## 4. 测试覆盖

### 后端测试（28 passed / 0.04s）

| 测试文件 | 数量 | 覆盖范围 |
|---------|------|---------|
| `test_router.py` | 11 | 路由打分(L1偏好便宜/L3偏好强引擎/L3过滤弱引擎)、隐私约束、工具约束、回退链、熔断器、端到端 route |
| `test_memory.py` | 7 | 语义相关性排序、重要性加成、recency 衰减、访问强化、用户隔离、过期归档、有效重要性衰减 |
| `test_dispatch_guardrails.py` | 10 | 双系统判据(简单/工具/代码/多步/障碍/风险)、注入拦截、长度限制、PII 脱敏、工具风险分级 |

### 前端测试
- ❌ 无自动化测试
- ✅ `npm run build` (类型检查 + lint) 可通过

---

## 5. 最近变更（2026-07-13）

| Commit | 内容 |
|--------|------|
| `e240639` | feat: 新增自托管双语 Chat UI（`/` 根路径，同源免 CORS） |
| `d4246bd` | feat: RouteTrace 暴露引擎调用错误（诊断静默失败） |
| `1db17b0` | fix: 容忍 env var 名称中的尾部空格（Railway dashboard 输入问题） |
| `1ed513e` | merge: 合并 Railway 部署配置 |
| `dae833e` | feat: 新增 `/api/debug/env` 诊断端点（名称+长度，不泄露密钥） |

---

## 6. 当前阻塞

1. **记忆持久化**——所有记忆在内存，重启即失。这阻塞了"身份连续性"这一核心理念的验证。
2. **ReAct 循环未实现**——系统2 目前只是"路由到强引擎直接回答"，不是真正的多步推理 Agent。阻塞了"Sunday 能做事"的验证。
3. **前端未接后端**——前端 Dashboard/Brain 的可视化是纯 mock，无法反映真实心智状态。

---

## 7. 环境依赖

| 依赖 | 当前配置 |
|------|---------|
| Python | 3.11+（已验证 3.14） |
| Node | 已装（npm） |
| 数据库 | ❌ 无（仅内存，SQLite+Chroma 待接） |
| API Keys | 未配（mock 模式运行） |
| Railway | 已配部署（Procfile + railway.json + CORS） |
| Git remote | origin/main ← GitHub |

---

## 8. 如何验证当前状态

```bash
# 后端
cd backend
python -m pip install -r requirements.txt
python -m pytest -q                    # 应显示 28 passed
export SUNDAY_API_KEY=dev-key
python -m uvicorn app.main:app --port 8000 --reload
curl http://localhost:8000/health     # {"status":"ok","engines":["mock-fast","mock-strong"],"memory_nodes":0}

# 前端
cd console
npm install
npm run build                          # 类型检查 + lint 通过
npm run dev                            # http://localhost:3000
```
