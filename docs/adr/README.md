# 架构决策记录（ADR）· 权威索引

> Sunday OS 全部架构决策的**单一索引**。格式：背景 / 方案 / 决策 / 理由。新决策在此登记编号。

## 为什么有两处 ADR

- **实现级 ADR（001-010）** 诞生于 3.0 技术设计阶段，正文在 [`../3.0/adr/`](../3.0/adr/)，本索引引用它们，不重复正文。
- **项目级 ADR（011+）** 由长期 AI Software Architect 在此目录新建正文。

> 编号全局唯一、只增不改。撤销某决策 → 新开一条 ADR 标记 supersedes，不删旧的。

## 索引

| ADR | 决策 | 状态 | 正文 |
|-----|------|------|------|
| 001 | 双系统认知架构（Talker+Reasoner） | 采纳 | [3.0/adr/001](../3.0/adr/001-dual-process.md) |
| 002 | 三层递进记忆（Storage→Reflection→Experience） | 采纳 | [3.0/adr/002](../3.0/adr/002-three-tier-memory.md) |
| 003 | ReAct 作为基础执行单元 | 采纳 | [3.0/adr/003](../3.0/adr/003-react-loop.md) |
| 004 | 渐进式架构演进 | 采纳 | [3.0/adr/004](../3.0/adr/004-progressive-arch.md) |
| 005 | 六层纵深护栏 | 采纳 | [3.0/adr/005](../3.0/adr/005-defense-in-depth.md) |
| 006 | 本地+云端混合（iPhone） | 采纳 | [3.0/adr/006](../3.0/adr/006-hybrid-mobile.md) |
| 007 | CPS 作为核心参与度指标 | 采纳 | [3.0/adr/007](../3.0/adr/007-cps-metric.md) |
| 008 | ★ 认知引擎抽象层（引擎可替换） | 采纳 | [3.0/adr/008](../3.0/adr/008-cognitive-engine-layer.md) |
| 009 | GitHub 作为 source of truth | 采纳 | [3.0/adr/009](../3.0/adr/009-github-source-of-truth.md) |
| 010 | 起步本地零配置存储 | 采纳 | [3.0/adr/010](../3.0/adr/010-local-first-storage.md) |
| 011 | 文档驱动的持久上下文体系 | 采纳 | [011](011-context-system.md) |

## 新增 ADR 模板

```markdown
# ADR-NNN · <决策标题>
**状态**：提议 | 采纳 | 弃用 | 被 ADR-XXX 取代
## 背景  <问题与约束>
## 方案  A) … B) … C) …
## 决策  选 X
## 理由  <为什么，关联理念/论文/数据>
## 影响  <对架构/代码/文档的影响；需同步更新什么>
```
