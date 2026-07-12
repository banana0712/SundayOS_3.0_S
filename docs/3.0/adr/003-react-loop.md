# ADR-003 · ReAct 作为基础执行单元

**状态**：采纳（继承自《3.0 架构设计计划》）

## 背景
Agent 需标准化的推理-行动模式驱动任务执行，需经验证且可扩展。

## 方案
A) CoT（纯推理）；B) 纯工具调用（无显式推理）；C) ReAct（推理+行动交替）。

## 决策
选 **C**。系统2 所有任务遵循 Thought → Action → Observation 循环。

## 理由
ReAct 幻觉率 6% vs 纯 CoT 14%，推理轨迹天然可解释，Thought Editing 提供优雅干预。已被 Reflexion/LATS 验证扩展。仅需 3-6 few-shot。详见 [05](../05-dual-process-cognition.md) §5.3。
