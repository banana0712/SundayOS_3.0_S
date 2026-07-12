# 附录 · 论文实现级精华

> 本附录是设计的**实现级依据**，从 9 篇源论文 PDF 精读中提炼公式、数字、prompt 格式与算法。与《3.0 架构设计计划》第二章的高层 digest 互补——那里讲「贡献」，这里讲「怎么编码」。

## A. AI Agent Systems: Architectures, Applications, and Evaluation (2026)

**Agent Transformer**：`A = (πθ, M, T, V, E)`
- πθ=transformer 策略（LLM 核）；M=记忆子系统；T=typed 工具集；V=验证器/批评器（**在副作用发生前**校验）；E=环境。
- 迭代循环：`oₜ←Obs(E)` → `mₜ←Retrieve(M,oₜ)` → `ãₜ~πθ(·|oₜ,mₜ)` → `âₜ←Validate(V,ãₜ)` → `E←Exec(T,âₜ)`；`M←Update(...)`。
- **V 是操作语义核心，非可选**。动作按可逆性/影响分支：只读低风险最小审议；写/部署/支付高风险触发额外验证/取证/人工确认。
- **预算化自主**：LLM 是「预算化循环里的规划器/控制器」，受 时间/token/工具调用/副作用 显式上限约束，只在困难/高风险时分配「深思考」。无闭式公式，是自适应策略。

**评估**：6 维 ~19 指标（见 [11](11-evaluation.md)）。p95=Quantile₀.₉₅。SuccessRate=(1/N)Σsᵢ。LoopRate=mean(1−uniq(τ)/k)。ToolSelAcc=Σ1{âₜ=aₜ*}/Σkᵢ。基准：AgentBench/WebArena/ToolBench/SWE-bench/GAIA。

## B. Understanding the Planning of LLM Agents (2024)

**规划五分类**（`p=plan(E,g;θ,P)`）：
1. 任务分解：分解优先（HuggingGPT/Plan-and-Solve/ProgPrompt）vs 交错（CoT/ReAct/PAL）。分解优先减遗忘但脆；交错适应反馈但长轨迹易幻觉。
2. 多计划选择：Self-consistency（采样+投票）、ToT（BFS/DFS 树+LLM 评估）、GoT、RAP/LLM-MCTS、LLM-A*。
3. 外部规划器：符号（LLM+P→PDDL/Fast-Downward、LLM-DP、LLM+ASP→CLINGO）；神经（Decision Transformer、SwiftSage 双过程）。
4. 反思修正：**Self-Refine**（自反馈）、**Reflexion**（评估器+言语自省+持久记忆）、**CRITIC**（外部工具接地纠错）。
5. 记忆增强：RAG-based（Generative Agents/MemoryBank/MemGPT/REMEMBER）；Embodied（微调 CALM/AgentTuning）。

**关键数字**（text-davinci-003）：AlfWorld ReAct 0.57($152)→Reflexion 0.71($220)；HotpotQA ReAct 0.34→Reflexion 0.39。**Reflexion≈2× ReAct token**。更多 token→更好；复杂任务需 few-shot。

## C. The Landscape of Emerging AI Agent Architectures (2024)

**单 Agent**：ReAct（HotpotQA 幻觉 6% vs CoT 14%，易陷循环）、RAISE（+记忆 scratchpad）、Reflexion（言语自省，陷局部最优）、AutoGPT+P（PDDL）、LATS（MCTS+自省，最优但最贵）。

**多 Agent**：垂直（有 leader）vs 水平（平等）。有组织 leader 比无 leader **快 ~10%**；无 leader 花 **~50% 通信在互相下令**。**人类 leader 最有效**；动态团队+轮换领导最优。MetaGPT：结构化输出（非闲聊）+ 发布-订阅。风险：谄媚、雪球效应、闲聊浪费。**「提示足够健壮时，多 Agent 讨论未必增强推理。」**

## D. ReAct (ICLR 2023)

**格式**：动作空间增广 `Â=A∪L`，thought∈L 不产生 observation 只更新上下文。Thought→Action→Observation 交替。
- few-shot：**HotpotQA 6 / FEVER 3 / ALFWorld 3 / WebShop 1-2**。「更多示例无益。」
- 密集思维（推理类）vs 稀疏思维（决策类，模型自决何时思考）。
- 动作（Wikipedia）：`search[entity]`、`lookup[string]`、`finish[answer]`。
- 幻觉：ReAct 成功轨迹 94% 事实正确 vs CoT 86%；CoT 失败 56% 是幻觉，ReAct 0%。
- 回退：无答案则 HotpotQA 7 步 / FEVER 5 步后回退 CoT-SC。ReAct+CoT-SC 用 3-5 样本达 21 样本 CoT-SC 水平。
- 决策任务 1-2 shot ReAct：ALFWorld +34%、WebShop +10% 绝对成功率。

## E. OpenAI · A Practical Guide to Building Agents

- **三要素**：Model + Tools + Instructions。
- **选型**：先用**最强模型**建基线 + 建 evals → 逐任务换小模型，精度可接受就留。
- **工具三类**：Data / Action / Orchestration。拆 Agent 看工具**相似/重叠度**而非数量（>15 清晰 OK，<10 含糊出错）。
- **指令**：从 SOP/文档派生，拆小编号步骤，每步对应具体动作/输出，覆盖边界情况。
- **编排**：run 循环到 final-output 工具被调 或 无工具调用 或 max turns。用 prompt 模板（策略变量）管复杂度，先别上多 Agent。
- **多 Agent**：Manager（子 Agent as tool，中心委派）vs Handoff（对等，转移执行+状态）。
- **护栏流水线**：长度→规则/正则/黑名单→Moderation→LLM 相关性+安全(gpt-4o-mini)→is_safe→执行。乐观并发 + tripwire 异常。工具按 low/med/high 风险分级。
- **HITL 触发**：超失败阈值；高风险动作。

## F. Anthropic · Building Effective AI Agents

- **Start Simple, Scale Intelligently**；模型按 能力/速度/成本 匹配任务。
- **Agent Skills**：模块化能力包，可组合（技能调技能）、可共享。上多 Agent 前先给单 Agent 加 Skills。
- **数字**：多 Agent **10-15× token**；复杂任务多 Agent 胜单 Agent **90.2%**；单 Agent 遇 **≥2 干扰域**急剧下降；工具响应上限 **~25,000 token**；评估器-优化器 **2-4 轮**；单 Agent「周」级、多 Agent「月」级交付。
- **工作流模式**：Sequential（确定、可审计）、Parallel（fan-out/fan-in，含 voting）、Evaluator-optimizer（2-4 轮）、动态生成/网络（新兴）。
- **四问决策框架**：需要控制度？域复杂度？资源约束？深度专业？
- **上下文管理**：context editing 自动清陈旧、memory tools 文件持久化、工具分页/过滤/截断。

## G. Generative Agents (UIST 2023)

- **检索评分**：`score = α·recency + β·importance + γ·relevance`，起步 α=β=γ=1，各分量 min-max 归一化。
- **recency**：指数衰减 decay^hours，decay=0.99（游戏小时）。
- **importance**：LLM 打 **1-10** 分。提示：「在 1(纯日常) 到 10(极重要) 打分」。
- **relevance**：query 与记忆嵌入余弦。
- **反思**：重要性总分超 **150** 触发；取近 100 条 → LLM 生成 **3 个高层问题** → 各自检索 → 综合 Insight（带 evidence）→ 写回。反思可递归成树。
- Persona：seed memories 初始化，反思演化。

## H. XiaoIce (2019)

- **IQ+EQ+Personality 三位一体**；三层架构（体验/引擎/数据）。
- **共情计算三段式**：CQU（~15 类 NER + 指代 + 句子补全）→ UU（话题 + **~11 对话行为** + **5 情绪** + 观点）→ IRG（共情向量 eR，eQ×eR）。
- 层次化 MDP：顶层全局策略 + 底层技能策略。230+ 技能。
- **CPS**：第 1 代 5 轮 → 第 6 代 **23 轮**（人类对话 ~9 轮）。6.6 亿活跃用户。
- 情感演进：探索功能 → 分享兴趣 → 视为朋友 → 首选倾诉对象。

## I. From Storage to Experience (2026)

- **三阶段**：Storage `M_raw={τ}` → Reflection `m'=F_ref(τ|φ)` → Experience `K=F_exp(T_batch)`（满足最小描述长度）。
- 记忆不是容量扩展，是**信息密度 + 认知抽象升维**。
- **混合体验**：显式回放缓冲区 + 周期性参数内部化；对比归纳（成功 vs 失败界定策略边界）；程序原语封装（IPS/CASCADE/Trace2Skill）。
- 四类记忆：情景（Ebbinghaus 衰减 0.995/会话）、语义（慢衰减）、程序（版本管理）、工作（任务后清空）。
- 人格锚定：核心特质持久化，跨会话一致；主动记忆感知（自主判断何时检索）。
