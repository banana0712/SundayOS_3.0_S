# CLAUDE.md

> 供 **Claude Code** 阅读的项目工作说明。每次会话开始，按下方「启动流程」执行，**不要依赖聊天历史**。

## 启动流程（每次会话必做）

1. 读 [SUNDAY_CONTEXT.md](SUNDAY_CONTEXT.md) —— 项目全貌与七条核心理念。
2. 读 [AGENTS.md](AGENTS.md) —— 确认你当前扮演的角色与边界。
3. 按任务需要查 [docs/](docs/)（架构 / 3.0 规范 / ADR / 设计 / 路线图）。
4. 检查记忆目录（若可用）中的相关条目。
5. 再开始动手。

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
