# 05 · 双系统认知

> 借鉴 Kahneman 双系统理论（由 DeepMind Talker-Reasoner 工程化）：系统1 快思考常在线，系统2 慢思考按需激活。二者通过共享记忆协调。

## 5.1 双系统分工

| 特性 | 系统1 Talker（快思考） | 系统2 Reasoner（慢思考） |
|------|----------------------|------------------------|
| 响应速度 | 毫秒级，始终在线 | 秒级，按需激活 |
| 推理深度 | 直觉、模式匹配 | 逻辑、多步推理 |
| 场景 | 日常对话、简单查询、情感回应 | 复杂规划、多步任务、高风险决策 |
| 引擎（经路由） | L1-L2（豆包/DeepSeek） | L3-L4（DeepSeek-reasoner/Claude） |
| 记忆访问 | 近期记忆 + 画像摘要 | 全量检索 + 反思 + Experience |
| 输出 | 对话表达（Utterance） | 思维轨迹（Thought）+ 信念更新（Belief） |

对应四角色：**情感伴侣/秘书**主要走系统1；**编码/学习**主要走系统2；但同一会话可来回切换。

## 5.2 系统1：Talker

始终在线的前端认知模块。原则：**快速、流畅、情感化**。

核心能力：
1. **意图快速分类** + 情感分析（轻量引擎，L1）。
2. **记忆摘要访问**：读画像摘要 + 近期关键记忆（不做全量检索，省延迟）。
3. **情感响应生成**：据用户情绪调语气（对接共情计算，[06](06-personality-and-empathy.md)）。
4. **话题管理**：检测对话停滞，主动引导（XiaoIce Topic Manager）。
5. **系统2 触发判断**：识别需深度推理的任务，激活 Reasoner。
6. **等待模式**：Reasoner 推理期间维持交互（「我想想…」），避免冷场。

## 5.3 系统2：Reasoner

按需激活的深度模块。原则：**准确、可靠、可解释**。核心是 ReAct 循环。

### ReAct 循环（精确格式）

动作空间增广 `Â = A ∪ L`：思维（thought∈L）不产生环境观察，只更新上下文。循环单元：

```
Thought: <推理，决定下一步做什么>
Action: <工具名>[<参数>]
Observation: <工具返回>
... (重复) ...
Thought: <综合>
Action: finish[<最终答案>]
```

- **few-shot**：3-6 个人工标注轨迹作示例（ReAct 原文：HotpotQA 6 shot、FEVER 3 shot；「更多示例无益」）。
- **稀疏思维**：决策类任务让模型自行决定何时显式思考（省 token）；推理类任务密集思维（每步 Thought-Action-Obs 交替）。
- **终止动作**：`finish[answer]`（返回结果）与 `ask[question]`（信息不足时反问用户，即 HITL 的温和形式）。
- **步数上限**：默认 max_steps=7（HotpotQA 用 7，FEVER 用 5）；超限回退到纯推理（CoT-SC）出一个尽力答案。
- **幻觉收益**：ReAct 结构使幻觉率 6% vs 纯 CoT 14%（工具观察消除幻觉）。

### 动作空间（起步工具集）

| Action | 说明 | 风险 |
|--------|------|------|
| `search[query]` | 语义检索记忆/知识 | 低 |
| `web[query]` | 联网搜索 | 低 |
| `read_file[path]` | 读文件 | 低 |
| `run_python[code]` | 沙盒执行 | 中 |
| `github[op, args]` | GitHub 操作（真源） | 中/高 |
| `calendar[op, args]` | 日程 | 中 |
| `ask[question]` | 反问用户 | — |
| `finish[answer]` | 终止 | — |

### 子目标分解与规划策略（可插拔）

Reasoner 内置可插拔的规划策略（对应 Planning Survey 五分类），按任务选择：

| 策略 | 何时用 | 方法 |
|------|--------|------|
| 交错分解 | 默认，多数任务 | ReAct 式边规划边执行 |
| 分解优先 | 依赖清晰的复杂任务 | Plan-and-Solve：先出完整计划再执行 |
| 多计划选择 | 高风险决策 | ToT/LATS 树搜索 + 状态评估 |
| 反思修正 | 失败后 | Reflexion：评估器 + 言语自省，重试（≈2× token，但复杂任务大涨） |
| 外部规划器 | 强约束任务（未来） | PDDL/符号求解器 |

起步实现「交错分解（ReAct）+ 失败触发 Reflexion」，树搜索留给高风险场景。

## 5.4 信念状态（Belief State）

Reasoner 维护结构化的用户信念模型（Talker-Reasoner 的显式信念建模）。JSON schema：

```json
{
  "user_id": "banana",
  "current_goal": {"desc": "规划日本旅行", "horizon": "short"},
  "active_tasks": [
    {"id": "t3", "desc": "估算预算", "status": "in_progress"}
  ],
  "obstacles": ["预算未知", "签证时间紧"],
  "motivations": ["想在樱花季去", "第一次出国"],
  "emotional_state": {"mood": 0.72, "energy": 0.61, "stress": 0.3},
  "preferences_touched": ["喜欢自由行胜过跟团"],
  "updated_by": "reasoner",
  "updated_at": "2026-07-13T10:22:00Z"
}
```

信念状态是双系统协调的**共享数据结构**：Reasoner 更新后通知 Talker，Talker 据此调对话策略。

## 5.5 双系统协调机制

通过共享记忆总线协调（Talker-Reasoner 共享记忆设计）：

1. **共享记忆总线**：系统1/2 通过统一记忆接口读写，无直接耦合。
2. **信念状态同步**：Reasoner 更新 Belief → 通知 Talker。
3. **增强动作空间**：`Â = A ∪ T ∪ B ∪ U`（工具 + 思维 + 信念更新 + 对话）统一双系统输出。
4. **覆盖机制**：Reasoner 的深度结论可覆盖 Talker 的直觉判断。
5. **上下文压缩**：系统2 完成后，把结果压成摘要注入系统1 上下文（≤25K token 上限）。

## 5.6 切换判据（Dispatch）

系统1 决定是否激活系统2。判据（任一命中即激活）：

```python
# app/cognition/dispatch.py 逻辑
def needs_reasoner(intent, text, belief) -> bool:
    return any([
        intent in {"plan", "code", "analyze", "research", "multi_step"},
        contains_tool_intent(text),          # 需要工具（查/算/改）
        estimated_steps(text) > 1,           # 多步
        risk_level(text) >= MEDIUM,          # 中风险及以上
        belief.has_unresolved_obstacles(),   # 存在待解障碍
        len(text) > 280 and has_question(text),
    ])
```

否则由系统1 直接生成响应。这个判据本身用轻量引擎（L1）跑，成本极低。

## 5.7 完整对话时序

```
用户输入
  → [护栏] 输入检查
  → [系统1] 意图+情感分类 (L1 引擎)  ← [记忆] 画像摘要+近期
  → needs_reasoner?
      否 → [系统1] 生成响应 (L2 引擎) → [人格/共情] 包装
      是 → [系统1] 进入等待模式，回「让我想想」
          → [系统2] ReAct 循环:
              Thought → [路由] 选 L3 引擎
                     → Action → [护栏] 验证器 V → 执行工具
                     → Observation → 更新 Belief
              ... 直到 finish/max_steps ...
          → [系统2] 压缩结论 → 注入系统1 上下文
          → [系统1] 用最终结论 + 人格/共情生成响应
  → [护栏] 输出检查 (PII)
  → 返回 + 异步写记忆/反思
```
