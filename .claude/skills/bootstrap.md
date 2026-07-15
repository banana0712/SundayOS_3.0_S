# /bootstrap · SundayOS 开发会话启动

> 用法：在新会话中直接输入 `/bootstrap`，AI 会按流程对齐项目全貌，然后进入开发模式。

---

## 执行流程（严格按序）

### ① 阅读核心文档（一步并行 9 个 Read）

1. `docs/AI_CONTEXT.md` —— 唯一入口 + 文档地图
2. `docs/CURRENT_STATE.md` —— 诚实进度报告（做什么/不做什么）
3. `docs/ROADMAP.md` —— 路线图 + 进度快照
4. `docs/PROJECT_MEMORY.md` —— 已完成的所有重大决策
5. `docs/ARCHITECTURE.md` —— 六层架构
6. `docs/DESIGN_SYSTEM.md` —— Design Language 1.0
7. `backend/app/runtime.py` —— ★ 架构骨骼 + LINKAGE 联动图
8. `CLAUDE.md` —— 工程约定 + 运行命令
9. `docs/ENGINEERING_CONTRACT.md` —— ★ 开发契约（动手前必读的硬性规矩）

### ② 理解 Git 状态

```bash
git status && git log --oneline -10
```

### ③ 阅读最近 Commit

```bash
git log --stat -5
```

### ④ 检查未完成任务

检查 `docs/ROADMAP.md` 中的 🟡 项和收尾待办、`CURRENT_STATE.md` 中的 ❌ 标记、"当前阻塞" 节。

### ⑤ 阅读 ADR

读 `docs/adr/README.md`——确认 11 个 ADR 全部存在，列出关键决策清单。

### ⑥ 验证后端

```bash
cd backend && python -m pytest -q
```

### ⑦ 总结当前项目状态

以表格形式输出：

```
📊 SundayOS 当前状态

Phase 1     🟡 ~90% (具体数字从 docs 读取)
测试        N passed
嵌入        hash / semantic (Ollama)
文档        7 工程文档 + 5 指南 + 1 世界设定
服务器      小兔云 / 本地 8005
Git         (实际状态)
```

### ⑧ 给出三个建议任务

基于 ROADMAP + 当前阻塞，按优先级排序。每项带依赖项和预估工作量。

### ⑨ 等待用户确认后开始工作

> 👆 以上是今天的 Sunday Bootstrap 总结。请确认优先开发哪个任务。

---

## 执行约束

- **不依赖聊天历史**：所有上下文从文档读取
- **工具调用尽量并行**：步骤① 的 8 个文件在一次调用中同时 Read
- **展示关键摘要，不灌原文**：每个文档 2-4 句话概括
- **诚实报告**：测试失败说失败、未配置说未配置
- **跑 `python -m pytest -q`**
- **步骤⑧ 更新**：不要用写死的旧数据——必须从 CURRENT_STATE.md 和 ROADMAP.md 读最新状态
