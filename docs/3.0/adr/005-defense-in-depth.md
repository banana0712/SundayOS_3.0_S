# ADR-005 · 六层纵深护栏

**状态**：采纳（继承自《3.0 架构设计计划》）

## 背景
Agent 自主决策带来显著安全风险，需全面防护体系。

## 方案
A) 仅 LLM 内容过滤；B) 规则+LLM 双层；C) 六层纵深防御。

## 决策
选 **C**：代码 Harness 自动合成 + LLM 安全分类器 + PII 过滤 + 规则护栏 + 工具风险评估 + HITL。

## 理由
参考 OpenAI 多层护栏、AutoHarness、AI Agent Systems 端到端安全。单层易被绕过，纵深防御是安全工程基本原则。护栏与主推理乐观并发，tripwire 中止。详见 [08](../08-security-and-autonomy.md)。
