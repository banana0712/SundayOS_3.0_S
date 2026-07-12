# 07 · 技能与工具

> 工具不是外挂，是 Sunday 的身体。技能是可组合、可共享、可独立更新的能力包。参考 XiaoIce 230+ 技能、Anthropic Agent Skills、OpenAI 工具三类型。

## 7.1 工具三类型（OpenAI 分类）

| 类型 | 作用 | 示例 | 风险基线 |
|------|------|------|---------|
| **Data** 数据 | 检索上下文 | 查记忆、读文件、web 搜索、查数据库 | 低（只读） |
| **Action** 动作 | 改变/发送 | 发邮件、改日程、提交 GitHub、写文件 | 中/高 |
| **Orchestration** 编排 | 调用其他 Agent/技能 | 子 Agent as tool | 视被调而定 |

工具需**标准化定义**（typed schema），支持工具↔Agent 多对多。判断是否拆分 Agent 的标准不是工具**数量**而是**相似/重叠度**——>15 个清晰工具没问题，<10 个含糊工具就会选错。

## 7.2 技能架构

技能分类（对应四角色）：

| 类别 | 示例技能 | 触发 | 执行策略 |
|------|---------|------|---------|
| 内容创作 | 写作、文案、诗歌 | 意图匹配 | 底层 MDP 策略 |
| 深度参与 | 学习辅导、助眠、推荐 | 对话状态检测 | 话题管理器协调 |
| 任务完成 | 日程、邮件、检索、编码 | 指令 + 目标分解 | ReAct 循环 |
| 系统能力 | 文件、设备、Shortcuts、GitHub | 权限验证 + 工具路由 | 验证器门控 |
| 情感支持 | 情绪疏导、共情对话 | 情感状态检测 | 共情计算驱动 |

## 7.3 技能生命周期

```
注册 Register → 发现 Discover → 激活 Activate → 执行 Execute → 演化 Evolve → 共享 Share
```

1. **注册**：标准化 Schema 注册到 Skill Registry。
   ```python
   @dataclass
   class SkillSpec:
       name: str
       description: str            # 供发现匹配
       parameters: dict            # JSON Schema
       category: str
       risk: str = "low"           # low|medium|high
       requires: list[str] = field(default_factory=list)  # 依赖工具/权限
   ```
2. **发现**：据用户输入 + 对话上下文自动匹配相关技能（语义 + 关键词）。
3. **激活**：顶层 MDP 策略选择激活哪个技能（XiaoIce 层次化对话策略）。
4. **执行**：每个技能有独立低层策略，可内部用 ReAct 循环。
5. **演化**：低频技能自动降级，高频序列封装为程序原语。
6. **共享**：同一技能被多角色/场景复用。

## 7.4 程序原语化（Procedural Primitive）

参考 From Storage to Experience 的程序记忆（IPS/CASCADE/Trace2Skill）：
- **高频序列检测**：监控重复操作模式（≥N 次），识别可封装序列。
- **原语生成**：把操作序列转成可执行函数/代码块。
- **组合执行**：CASCADE 模式实现原语级联。
- **技能库演化**：Trace2Skill 把局部经验蒸馏为可迁移技能。

例：你每周一让 Sunday「拉取本周 GitHub issues → 按优先级排序 → 生成周计划」，重复三次后自动封装为 `weekly_planning` 原语，之后一句「排本周」即触发。

## 7.5 MCP 集成

通过 Model Context Protocol 连接外部工具/系统，标准化工具接入。iPhone Shortcuts 经 App Intents 暴露为工具（见 [09](09-api-and-integration.md)）。GitHub 作为一等工具，既是数据源（读仓库）也是动作目标（提交/PR），呼应「GitHub 为真源」。

## 7.6 调度器（Scheduler）

支持主动性的基础设施：
- 定时任务（每日简报、每周计划）
- 主动提醒（日程、待办）
- 记忆整理（夜间反思、巩固触发）
- 主动聊天（据关系状态与停滞检测）

## 7.7 单 vs 多 Agent（务实边界）

- **默认单 Agent + Skills**。Anthropic：多 Agent 消耗 **10-15× token**，交付周期从「周」变「月」，仅在复杂任务有 ROI。
- 拆多 Agent 的信号：提示里 if-then-else 分支不可维护；工具重叠导致选错。
- 多 Agent 时采用**垂直架构**（明确 leader + 动态团队 + 轮换领导，比无 leader 快 ~10%），子 Agent 作为工具，用 MetaGPT 式结构化输出 + 发布-订阅避免闲聊噪音。
- 起步：**单 Agent**，四角色靠 prompt 模板 + 技能切换实现，不引入多 Agent。
