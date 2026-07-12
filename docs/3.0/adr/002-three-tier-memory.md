# ADR-002 · 三层递进记忆

**状态**：采纳（继承自《3.0 架构设计计划》）

## 背景
传统记忆要么只做存储（MemGPT），要么缺从存储到理解的跃升路径。需既能记录又能理解。

## 方案
A) 单一向量存储；B) 双层（存储+反思）；C) 三层递进（存储+反思+体验）。

## 决策
选 **C**。L1 Storage 原始轨迹，L2 Reflection 纠错+洞察，L3 Experience 跨轨迹抽象。

## 理由
参考 From Storage to Experience：三层递进共存而非替代。Experience 层的跨轨迹抽象是持续学习与个性化进化的关键。详见 [04](../04-memory-system.md)。
