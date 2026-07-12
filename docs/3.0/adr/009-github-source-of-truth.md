# ADR-009 · GitHub 作为 source of truth

**状态**：采纳（本个性化设计新增）

## 背景
用户明确：**「GitHub is the source of truth, while Sunday orchestrates all connected AI services.」** 需要跨设备一致、可审计、可回滚的身份状态，且不依赖任何单一云厂商。

## 考虑方案
- A) 数据库为唯一真源：查询快，但无版本历史、无 diff、跨端灾备弱、厂商锁定。
- B) 纯 GitHub 存全部状态：可版本化但高频记忆写 Git 不现实（性能/噪音）。
- C) **分层真源**：稳定身份（人格 `persona.yaml`、技能定义、稳定偏好、加密记忆快照）以 GitHub 为真源版本化；高频易变的情景/工作记忆留数据库，定期加密快照回写 GitHub。

## 决策
选 **C**。人格、技能、稳定语义偏好版本化在 GitHub，运行时加载；语义记忆定期加密快照回写。连接的 AI 服务是可替换引擎，真相在 Git。

## 理由
- 改人格/技能 = 一次 commit，可回滚、可 diff、可审计——与 ADR-008「引擎可替换」共同实现「身份稳定、引擎流动」。
- 跨设备一致 + 灾备：多端是同一心智的窗口，真源统一。
- 去厂商锁定：符合用户「不绑定单一供应商」的一贯立场。
- 安全前提：提交前密钥扫描（gitleaks），快照加密。详见 [09-api-and-integration](../09-api-and-integration.md) §9.3。
