# Sunday OS · 文档中心

> 本目录是 Sunday OS 的**权威文档体系**。所有 AI Agent 与人类协作者以此为准，不依赖聊天历史。

## 从哪开始

- 第一次接触项目 → 仓库根 [SUNDAY_CONTEXT.md](../SUNDAY_CONTEXT.md)
- 我是 AI Agent → [AGENTS.md](../AGENTS.md)
- 我是 Claude Code → [CLAUDE.md](../CLAUDE.md)

## 目录结构

```
docs/
├── README.md              # 本文件：导航
├── ARCHITECTURE.md        # 顶层系统架构（权威）
├── DESIGN_SYSTEM.md       # 设计规范（配色/字体/栅格/组件/动效）
├── ROADMAP.md             # 开发路线图 + 当前进度
├── adr/                   # 架构决策记录（Why it is the way it is）
│   ├── README.md          #   ADR 索引
│   └── NNN-*.md           #   各条决策
├── guides/                # 使用与操作手册
│   └── BACKEND_USAGE.md   #   后端使用说明书
└── 3.0/                   # 实现级技术规范（详）
    ├── 00-README.md       #   3.0 文档集导航
    ├── 01..12-*.md        #   愿景/架构/引擎/记忆/双系统/人格/技能/安全/API/基建/评估/路线
    ├── adr/               #   3.0 阶段的实现级 ADR（被顶层 adr/ 索引引用）
    └── appendix-paper-insights.md  # 论文实现级精华
```

## 三个层次（怎么分工）

| 层次 | 文档 | 用途 | 变更频率 |
|------|------|------|---------|
| **上下文层** | 根 SUNDAY_CONTEXT / CLAUDE / AGENTS | 让任何 Agent 快速对齐 | 低（地基） |
| **权威层** | docs/ARCHITECTURE · DESIGN_SYSTEM · ROADMAP · adr/ | 项目级真相，稳定 | 中 |
| **实现层** | docs/3.0/* | 可编码的细节规范 | 随实现演进 |

顶层文档指向实现层；实现层展开细节。避免重复——同一事实只在一处权威定义，其余引用它。

## 索引

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 六层 + 引擎抽象层、数据流、组件、演进 |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Design Language 1.0 全套 token 与组件规范 |
| [ROADMAP.md](ROADMAP.md) | Phase 1-4 里程碑 + 当前进度标注 |
| [adr/README.md](adr/README.md) | 全部架构决策索引 |
| [guides/BACKEND_USAGE.md](guides/BACKEND_USAGE.md) | 后端如何跑、如何接真实引擎、局限、排错 |
| [3.0/00-README.md](3.0/00-README.md) | 实现级技术规范集入口 |
