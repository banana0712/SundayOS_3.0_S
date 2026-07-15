# CLAUDE.md

> 供 **Claude Code** 阅读的项目工作说明。每次会话开始，按下方「启动流程」执行，**不要依赖聊天历史**。

## 启动流程（每次会话必做）

**最快方式**：在对话中输入 `/bootstrap`，AI 自动按 10 步流程对齐项目全貌（详见 `.claude/skills/bootstrap.md`）。

手动流程：
1. 读 [SUNDAY_CONTEXT.md](SUNDAY_CONTEXT.md) —— 项目全貌与七条核心理念。
2. 读 [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) —— 唯一入口 + 文档地图。
3. 读 [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) —— 诚实进度报告。
4. 读 [backend/app/runtime.py](backend/app/runtime.py) —— ★ 架构骨骼 + LINKAGE 联动图。
5. 按任务需要查 [docs/](docs/)（架构 / 3.0 规范 / ADR / 设计 / 路线图 / 调试）。
6. 再开始动手。

## 项目体检（给主人的自检工具）

在任意会话输入 `/checkup`，AI 会自动扫描项目健康状况（安全红线 / 测试 / 屎山预警 /
假数据 / 双真相 / 文档诚实度），用大白话给出体检报告——**不需要懂代码**。
详见 `.claude/skills/checkup.md`。建议每做几个功能或每隔一段时间跑一次。

## 每次会话结束时必须更新的文档

```
今天的开发已完成。

请更新：
- VERSION（根据变更类型 bump MAJOR / MINOR / PATCH）
- CHANGELOG.md（按 Keep a Changelog 格式记录本次变更）
- CURRENT_STATE.md
- ROADMAP.md
- PROJECT_MEMORY.md
- 如果架构有变化，同步更新 ARCHITECTURE.md
- 如果有新增模块/文档，同步更新 AI_CONTEXT.md
- 如果有新增调试入口，同步更新 DEBUGGING.md

版本号规则（SemVer）：
- MAJOR（x.0.0）：架构变更、不兼容的 API 修改、核心理念调整
- MINOR（0.x.0）：新功能、新模块（向后兼容）
- PATCH（0.0.x）：Bug 修复、性能优化、文档更新

然后总结今天的进展，为下一次开发会话做好准备。
```

## 这是什么项目

Sunday OS —— 个人 AI 操作系统层。理念：**"one mind for every task"**，身份来自记忆/人格/目标而非某个 LLM。详见 SUNDAY_CONTEXT.md。

## 仓库布局

```
SundayOS/
├── SUNDAY_CONTEXT.md      # 所有 Agent 首读
├── CLAUDE.md              # 本文件
├── AGENTS.md              # AI Agent 职责定义
├── docs/                  # 文档体系（权威）
│   ├── README.md          #   导航
│   ├── ARCHITECTURE.md    #   顶层架构
│   ├── DESIGN_SYSTEM.md   #   设计规范
│   ├── ROADMAP.md         #   路线图 + 进度
│   ├── adr/               #   架构决策记录
│   ├── guides/            #   使用/操作手册
│   └── 3.0/               #   实现级技术规范（13 文档 + 附录）
├── backend/               # FastAPI 参考实现（Python 3.11+）
├── console/               # Next.js 15 Web 控制台（前端原型）
└── 1.0/                   # 历史文档（仅文档，无代码）
```

## 运行命令

**后端**（Python 3.11+）：
```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest -q                                  # 28 测试，离线通过
export SUNDAY_API_KEY=dev-key                         # Windows Git Bash 同此
python -m uvicorn app.main:app --port 8000 --reload   # 未配 Key → mock 模式
```

**前端**（Node 已装）：
```bash
cd console
npm install
npm run dev      # http://localhost:3000
npm run build    # 类型 + lint 检查
```

详细用法见 [docs/guides/BACKEND_USAGE.md](docs/guides/BACKEND_USAGE.md)。

## 工程约定

- **语言**：文档与注释用中文（与既有一致）；代码标识符用英文。
- **后端**：Python 3.11+，类型注解齐全，纯逻辑与 I/O 分离（便于离线单测）。新增引擎 = 写 `EngineProvider` 子类 + 在 `registry.py` 登记，**零改上层**。
- **前端**：TS + Tailwind + Framer Motion，遵循 [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) 的 token。
- **测试**：改动核心逻辑（路由/记忆/双系统/护栏）必须补/跑 `pytest`。提交前后端跑 `pytest`、前端跑 `npm run build`。
- **风格**：读周围代码，匹配其命名与惯用法，不引入新库除非必要。

## 安全红线（必须遵守）

- **绝不硬编码密钥**；一律 `.env` + 环境变量。`.env` 已在 `.gitignore`。
- ⚠️ `readme.txt` / `其他.txt` 含明文真实 API Key —— 提醒用户轮换，不要把值写进任何代码或文档。
- 高风险操作（删文件/支付/权限/删库）先向用户确认。
- 不做破坏性 git 操作（force push / reset --hard）除非用户明确要求。
- 不把代码/密钥发往第三方，除非用户明确要求。

## 变更后维护上下文

若你的改动影响架构/决策/进度，**同步更新**对应文档：
- 架构变化 → `docs/ARCHITECTURE.md` + 新 ADR。
- 重大决策 → `docs/adr/` 新增，并在 `SUNDAY_CONTEXT.md` §4 提及。
- 进度推进 → 更新 `SUNDAY_CONTEXT.md` §2 + `docs/ROADMAP.md`。

## 当前工作纪律

- 默认**先设计后编码**：多文件/不明确的改动先给方案再动手。
- 复杂或跨文件研究优先派子 Agent，保住主上下文。
- 报告结果如实：测试失败就说失败并附输出；跳过的步骤要讲。
