# 04 · 记忆系统

> 记忆是 Sunday 身份的**首要来源**。引擎可换，记忆不可失。本章把 Generative Agents 的检索评分、From Storage to Experience 的三层递进、XiaoIce 的长期建模落到可编码的公式与 schema。

## 4.1 三层递进架构

记忆演化不是容量扩展，而是**信息密度增强 + 认知抽象升维**（From Storage to Experience, 2026）。三层递进共存，而非替代：

| 层 | 名称 | 形式化 | 存储内容 | 检索方式 |
|----|------|--------|---------|---------|
| L1 | **Storage 存储** | `M_raw = {τ_i}` | 原始交互轨迹（时间戳+内容+重要性） | recency × importance × relevance 复合评分 |
| L2 | **Reflection 反思** | `m'_i = F_ref(τ_i \| φ)` | 修正后记忆 + 高层洞察 | 语义相似匹配 + 环境校准 |
| L3 | **Experience 体验** | `K = F_exp(T_batch)` | 通用规则/技能/行为模式 | 零样本策略先验（去检索化） |

- **L1** 忠实记录「发生了什么」。
- **L2** 定期反思，纠错并抽象出「这意味着什么」。
- **L3** 跨轨迹归纳出「以后该怎么做」——满足最小描述长度原则，是持续学习的关键。

## 4.2 四类记忆（正交于三层）

| 类型 | 定义 | 存储结构 | 衰减策略 |
|------|------|---------|---------|
| 情景记忆 Episodic | 具体交互经历 | Memory Stream + 向量库 | Ebbinghaus 衰减，因子 0.995/会话 |
| 语义记忆 Semantic | 偏好、知识、事实、用户画像 | 结构化 + 知识图谱 | 慢衰减（长期有效） |
| 程序记忆 Procedural | 操作技能、工作流 | 程序原语库 | 版本管理，淘汰低频 |
| 工作记忆 Working | 当前任务上下文 | 上下文窗口（≤25K token） | 任务结束清空 |

## 4.3 记忆对象 Schema

```python
# app/memory/schema.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    REFLECTION = "reflection"      # L2 产物
    EXPERIENCE = "experience"      # L3 产物

class Importance(int, Enum):       # 1-10 量表（Generative Agents 用 1-10）
    TRIVIAL = 1
    LOW = 3
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10                  # 永不自动归档

@dataclass
class MemoryNode:
    id: str
    user_id: str
    type: MemoryType
    content: str                   # 自然语言描述
    embedding: list[float] | None = None
    importance: int = 5            # 1-10, 由 LLM 打分
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_access: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    # 反思树：指向支撑本节点的下层记忆
    evidence_ids: list[str] = field(default_factory=list)
    # 来源引用（可审计）
    source: str = "chat"           # chat | voice_capsule | reflection | tool
    frozen: bool = False           # 冻结=不参与衰减/合并
```

## 4.4 检索评分公式（核心）

借鉴 Generative Agents 的复合评分。检索时对候选记忆计算：

```
score(m) = α · recency(m) + β · importance(m) + γ · relevance(m, query)
```

各分量（均归一化到 [0,1]）：

1. **recency（近期性）**——指数衰减，衰减因子 0.995/小时（Generative Agents 原文用 0.99/游戏小时；SundayOS 用会话/时间双轨）：
   ```
   recency(m) = decay ^ hours_since_last_access,   decay = 0.995
   ```
2. **importance（重要性）**——LLM 在写入时打的 1-10 分，归一化：
   ```
   importance(m) = score_1to10 / 10
   ```
   打分提示：`"在 1(纯日常琐事) 到 10(极重要的核心记忆) 之间，为下面这条记忆的重要性打分，只输出数字：{content}"`
3. **relevance（相关性）**——query 嵌入与记忆嵌入的余弦相似度：
   ```
   relevance(m) = cosine(embed(query), m.embedding)
   ```

**权重**：起步取 `α = β = γ = 1`（Generative Agents 的默认），各分量先各自 min-max 归一化再加权求和。可按角色调：情感对话调高 recency，学习/编码调高 relevance。

检索后取 Top-K（默认 K=12），并叠加**主动记忆感知**：由系统1 判断本轮是否真的需要检索（省 token），空查询直接跳过。

## 4.5 反思引擎（L1→L2）

反思是记忆从「被动记录」跃升到「主动理解」的关键。

**触发条件**（任一）：
- 最近 events 的重要性总分超过阈值 θ（Generative Agents 用 150；SundayOS 起步 θ=100，可配）。
- 每日定时（如凌晨，配合调度器）。
- 会话结束且本会话累计重要性 > 30。

**两步生成流程**（Generative Agents 原法）：
```
1. 取最近 100 条记忆
2. LLM 生成「最值得追问的 3 个高层问题」
   提示: "仅根据以上信息，我们可以回答关于该用户的哪 3 个最显著的高层问题？"
3. 对每个问题，以其为 query 检索相关记忆
4. LLM 综合这些记忆生成 Insight，并给出 evidence（指向源记忆 id）
5. Insight 作为 MemoryType.REFLECTION 节点写回记忆流
```

**反思递归**：反思可基于其他反思，形成抽象层次递增的「反思树」（`evidence_ids` 记录支撑关系）。

**环境反馈校准**：每次工具操作后评估结果，更新内部世界模型（区分预期与实际）。

**偏好感知更新**：区分短期波动与长期趋势，用滑动窗口 + 显著性检验避免对临时情绪过拟合。

## 4.6 体验抽象（L2→L3）

参考 From Storage to Experience 的 Experience 阶段与 Hybrid Experience。

- **跨轨迹归纳** `K = F_exp(T_batch)`：对一批相似轨迹（成功+失败）做归纳，抽出通用规则/技能。满足最小描述长度——用最短描述覆盖最多情形。
- **对比归纳**：利用成功与失败操作的对比，精确界定行为策略边界（「什么情况下这么做，什么情况下别」）。
- **程序原语封装**：高频操作序列（≥N 次重复）自动封装为原子技能（见 [07](07-skills-and-tools.md)）。
- **混合体验循环**：显式回放缓冲区（保留高价值探索轨迹，即时检索）+ 周期性参数内部化（选择性微调，把显式经验压进权重）。起步只做显式回放缓冲区，微调作为未来项。

## 4.7 记忆巩固（Consolidation）

定时（每晚）或达阈值时运行：
```
1. 计算记忆间相似度（嵌入余弦）
2. 合并高度相似（>0.92）的记忆为单节点，累加 access_count
3. 对过期低重要度记忆（effective_importance < 阈值）归档（软删除，不物理删）
4. 从近期记忆提取新语义知识，写入语义记忆/知识图谱
5. CRITICAL(10) 与 frozen 节点永不自动归档
```

**有效重要性**（延续 1.0 的衰减算法，与四类衰减策略协同）：
```
effective_importance = base_importance × decay^(days/30) × (1 + 0.1 × access_count)
```
——30 天半衰期，频繁访问的记忆衰减更慢。

## 4.8 存储选型

| 阶段 | 情景（向量） | 语义/结构化 | 工作记忆 | 原始轨迹 |
|------|------------|-----------|---------|---------|
| 起步（本地零配置） | ChromaDB | SQLite | 进程内/SQLite | SQLite |
| 生产 | Milvus/Pinecone | Postgres + Neo4j | Redis | S3 + Postgres |

**GitHub 作为真源**：语义记忆中「稳定的用户画像/偏好/人格配置」以结构化文件（YAML/JSON）版本化在 GitHub，运行时加载并可审计变更历史；高频易变的情景记忆留在数据库。

## 4.9 隐私

- 敏感记忆（情感、健康、私人对话）标记 `privacy_sensitive`，优先本地引擎处理与本地存储。
- 记忆数据 E2E 加密（AES-256-GCM）。
- 隐私感知遗忘：用户可随时请求删除特定记忆/全部记忆（硬删除 + 向量库同步清除）。
- 社交圈层隔离：区分朋友/同事/陌生人，不同圈层可见不同记忆粒度。详见 [08](08-security-and-autonomy.md)。
