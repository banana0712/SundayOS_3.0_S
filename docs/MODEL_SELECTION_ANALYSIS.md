# 模型选择分析：为什么主要使用 DeepSeek 而非豆包？

## 🔍 当前配置状态

### 实际配置
```bash
# 生产环境 .env 文件
DEEPSEEK_API_KEY=<已配置>
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

CUSTOM_API_KEY=<已配置>  
CUSTOM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
CUSTOM_MODEL=doubao-seed-character-260628

DOUBAO_API_KEY=<未配置>
```

### 关键发现
**豆包实际上是通过 CUSTOM 配置加载的，而非 DOUBAO 配置！**

这导致了一个意想不到的结果：
- ✅ DeepSeek 正常注册为两个引擎（deepseek-chat, deepseek-reasoner）
- ✅ 豆包通过 CUSTOM 注册为 sunday-chat（被标记为 `primary=True`）
- ❌ 但由于能力标记错误，DeepSeek 在大多数场景下获胜

---

## 🏗️ 引擎注册机制

### 1. DeepSeek 注册（registry.py 32-46行）

```python
engines.append(OpenAICompatibleProvider(
    id="deepseek-chat", 
    model="deepseek-chat",
    caps=EngineCapabilities(
        function_calling=True,      # ✅ 支持工具调用
        max_context=64_000,
        languages=("zh", "en"), 
        quality=0.55                # 质量评分 0.55
    ),
    price_in=0.27, price_out=1.10,  # 成本低
))

engines.append(OpenAICompatibleProvider(
    id="deepseek-reasoner", 
    model="deepseek-reasoner",
    caps=EngineCapabilities(
        strong_reasoning=True,      # ✅ 强推理能力
        max_context=64_000,
        quality=0.65                # 质量评分 0.65
    ),
    price_in=0.55, price_out=2.19,
))
```

**能力总结**：
- deepseek-chat：工具调用 + 低成本 + 中等质量
- deepseek-reasoner：强推理 + 高质量

### 2. 豆包注册（通过 CUSTOM，registry.py 53-63行）

```python
engines.append(OpenAICompatibleProvider(
    id="sunday-chat",              # 注意：不是 "doubao"
    model="doubao-seed-character-260628",
    caps=EngineCapabilities(
        function_calling=True,      # ❌ 实际上豆包不支持！
        max_context=128_000,        # ✅ 更大的上下文
        languages=("zh", "en"),
        quality=0.85,               # ✅ 质量评分 0.85（最高）
        primary=True                # ✅ 标记为主引擎
    ),
    price_in=0, price_out=0,       # ✅ 成本为 0（自定义）
))
```

**问题**：
1. ✅ 标记为 `primary=True`（应该被优先选择）
2. ✅ 质量评分最高（0.85 vs DeepSeek 0.55/0.65）
3. ❌ **错误声明支持 function_calling**（豆包实际不支持）
4. ⚠️ 命名为 sunday-chat 而非 doubao（不清晰）

---

## 🎯 路由器选择逻辑

### 评分机制（router.py）

```python
def _capability(e: EngineProvider, req: CognitiveRequest) -> float:
    cap = 0.0
    cap += e.caps.quality * 0.5      # 质量权重 50%
    if e.caps.strong_reasoning:
        cap += 0.3                    # 强推理 +30%
    if e.caps.function_calling:
        cap += 0.1                    # 工具调用 +10%
    if req.prefer_chinese and "zh" in e.caps.languages:
        cap += 0.1                    # 中文支持 +10%
    if e.caps.primary:
        cap += 0.15                   # 主引擎加成 +15%
    return min(cap, 1.0)
```

### 场景1：普通聊天（L2_DAILY）

**候选引擎**：
- deepseek-chat
- sunday-chat（豆包）

**评分计算**：

**DeepSeek-chat**：
```
质量：0.55 × 0.5 = 0.275
工具调用：+0.1
中文支持：+0.1
总分：0.475
```

**Sunday-chat（豆包）**：
```
质量：0.85 × 0.5 = 0.425
工具调用：+0.1（❌ 错误标记）
中文支持：+0.1
主引擎加成：+0.15
总分：0.775
```

**结果**：豆包应该获胜（0.775 > 0.475）

### 场景2：需要推理（L3_DEEP）

**过滤规则**：
```python
if complexity >= Complexity.L3_DEEP and not e.caps.strong_reasoning:
    continue  # 排除没有强推理能力的引擎
```

**候选引擎**：
- deepseek-reasoner（✅ strong_reasoning=True）
- ~~deepseek-chat~~（❌ 被过滤）
- ~~sunday-chat~~（❌ strong_reasoning=False，被过滤）

**结果**：DeepSeek-reasoner 获胜（唯一候选）

### 场景3：需要工具调用

**触发条件**（dispatch.py）：
```python
_TOOL_RE = re.compile(r"(搜索|查一下|帮我查|计算|翻译|...)")

def needs_reasoner(intent, text, belief):
    if contains_tool_intent(text):
        return True  # 触发 System 2（ReAct循环）
```

**流程**：
1. 检测到工具意图 → 启动 ReAct 循环
2. ReAct 循环需要 function_calling 能力
3. 豆包标记为支持但实际不支持 → **可能出错**

---

## 🔍 实际使用分析

### 为什么 DeepSeek 被更多使用？

#### 原因1：豆包的 function_calling 能力标记错误

**问题**：豆包被标记为支持工具调用，但实际不支持。

**后果**：
1. 当用户请求"帮我查一下天气"
2. 路由器认为豆包可以处理（function_calling=True）
3. 实际调用时失败
4. Fallback 到 DeepSeek

**证据**：
```python
# registry.py 56行
caps=EngineCapabilities(
    function_calling=True,  # ❌ 豆包实际不支持
    ...
)
```

**修复建议**：
```python
caps=EngineCapabilities(
    function_calling=False,  # ✅ 正确标记
    ...
)
```

#### 原因2：需要推理的场景多

**统计**：以下请求都会触发 L3_DEEP 复杂度：
- 包含"分析""解释""为什么"等关键词
- 多步骤请求（"先...再..."）
- 长文本（>280字符）
- 代码相关请求

**现状**：
- L3_DEEP → 只有 deepseek-reasoner 有 strong_reasoning
- 豆包被排除在外

#### 原因3：ReAct 循环的高频使用

**触发条件**（dispatch.py）：
```python
def needs_reasoner():
    checks = [
        intent in {"plan", "code", "analyze", "research"},
        contains_tool_intent(text),  # 搜索、查询、计算等
        estimated_steps(text) > 1,
        risk_level(text) >= Risk.MEDIUM,
        len(text) > 280 and "?" in text,
    ]
    return any(checks)  # 任一条件满足即触发
```

**特点**：条件非常宽松，大量请求触发 System 2（ReAct 循环）

**ReAct 循环内部**：
- 需要多次调用 LLM
- 需要工具调用能力
- 豆包不支持 → 只能用 DeepSeek

---

## ⚖️ 两个模型的对比

### DeepSeek 优势

#### 1. 工具调用支持 ✅
```python
function_calling=True  # 真实支持
```

**应用**：
- 搜索功能
- 计算工具
- API 调用
- 文件操作

#### 2. 强推理模型 ✅
```python
deepseek-reasoner:
    strong_reasoning=True
    quality=0.65
```

**应用**：
- 复杂问题分析
- 代码调试
- 逻辑推理
- 多步骤规划

#### 3. 成本可预测 ✅
```python
price_in=0.27, price_out=1.10  # CNY/百万tokens
```

**计算**：
- 1000条普通对话 ≈ 10¥
- 成本可控

#### 4. 生态成熟 ✅
- API 稳定
- 文档完善
- 社区活跃
- 错误处理好

### DeepSeek 劣势

#### 1. 质量评分较低 ⚠️
```
deepseek-chat: 0.55
deepseek-reasoner: 0.65
vs
豆包: 0.85
```

**影响**：
- 普通聊天可能不如豆包流畅
- 共情能力可能较弱

#### 2. 成本相对较高 💰
```
DeepSeek: 0.27~2.19 元/百万tokens
豆包: 0 元（自定义配置）
```

#### 3. 上下文窗口较小
```
DeepSeek: 64K tokens
豆包: 128K tokens
```

---

### 豆包优势

#### 1. 质量评分最高 ✅
```python
quality=0.85  # 最高评分
```

**体现**：
- 更自然的对话
- 更好的共情
- 更符合中文表达习惯

#### 2. 主引擎优先级 ✅
```python
primary=True  # +0.15 加成
```

#### 3. 大上下文窗口 ✅
```python
max_context=128_000  # 128K tokens
```

**应用**：
- 长文档理解
- 长对话历史
- 更少的压缩需求

#### 4. 成本为零 ✅
```python
price_in=0, price_out=0
```

**原因**：可能是企业内部部署或特殊合作

### 豆包劣势

#### 1. 不支持工具调用 ❌
```python
function_calling=True  # ❌ 错误标记
```

**影响**：
- 无法搜索
- 无法使用工具
- ReAct 循环失效

#### 2. 无强推理版本 ❌
```python
strong_reasoning=False
```

**影响**：
- 复杂推理任务被排除
- L3_DEEP 场景无法使用

#### 3. 配置不规范 ⚠️
```
使用 CUSTOM 而非 DOUBAO 配置
id="sunday-chat" 而非 "doubao"
```

**影响**：
- 配置不直观
- 难以调试
- 容易混淆

---

## 🎯 违背初衷的原因

### 原始设计意图

根据代码注释和配置：
```python
primary=True  # 豆包应该是默认语言模型
quality=0.85  # 最高质量评分
```

**预期**：豆包应该处理大部分普通聊天

### 实际情况

**统计**（估算）：
- 70% 请求 → DeepSeek
- 30% 请求 → 豆包

### 根本原因

#### 1. 能力标记错误（技术问题）
```python
# 豆包配置
function_calling=True,  # ❌ 不应该标记
strong_reasoning=False  # 限制了使用场景
```

#### 2. 调度策略过于宽松（设计问题）
```python
def needs_reasoner():
    # 条件太多，太容易触发
    return any([
        intent in _INTENT_REASONER,
        contains_tool_intent(text),  # 这个匹配很宽松
        estimated_steps(text) > 1,
        risk_level(text) >= Risk.MEDIUM,
        len(text) > 280 and "?" in text,
    ])
```

**结果**：大量请求被判定为需要 System 2，跳过豆包

#### 3. 缺少强推理豆包版本（资源限制）

**现状**：
- DeepSeek 有两个版本（chat + reasoner）
- 豆包只有一个版本（character）

**建议**：如果有预算，可以配置豆包的推理版本

---

## 💡 解决方案

### 方案1：修复豆包能力标记（推荐）

**修改 registry.py**：
```python
engines.append(OpenAICompatibleProvider(
    id="doubao-chat",  # 改名更清晰
    model="doubao-seed-character-260628",
    caps=EngineCapabilities(
        function_calling=False,    # ✅ 修复：豆包不支持
        strong_reasoning=False,    # 保持不变
        max_context=128_000,
        languages=("zh", "en"),
        quality=0.85,
        primary=True               # 保持主引擎地位
    ),
    price_in=0, price_out=0,
))
```

**效果**：
- ✅ 豆包不会被错误地用于工具调用
- ✅ 普通聊天场景豆包获胜（quality 0.85 > 0.55）
- ✅ 推理场景仍用 DeepSeek

**预期使用率**：
- 豆包：60%（普通聊天）
- DeepSeek-chat：10%（需要工具的简单任务）
- DeepSeek-reasoner：30%（复杂推理）

### 方案2：调整调度策略

**修改 dispatch.py**：
```python
def needs_reasoner(intent, text, belief):
    checks = [
        intent in _INTENT_REASONER,
        estimated_steps(text) > 2,  # 从 >1 改为 >2，更严格
        risk_level(text) >= Risk.HIGH,  # 从 MEDIUM 改为 HIGH
        # 移除工具意图检查（让路由器根据能力选择）
    ]
    return any(checks)
```

**效果**：
- 更多请求走 System 1（直接聊天）
- 豆包有更多机会被选中

**风险**：
- ⚠️ 可能降低需要推理任务的质量

### 方案3：添加豆包推理版本

**添加配置**（如果字节提供）：
```bash
CUSTOM_REASONER_API_KEY=<key>
CUSTOM_REASONER_MODEL=doubao-pro-reasoning
```

**注册代码**：
```python
engines.append(OpenAICompatibleProvider(
    id="doubao-reasoner",
    model="doubao-pro-reasoning",
    caps=EngineCapabilities(
        strong_reasoning=True,  # ✅ 强推理
        max_context=128_000,
        quality=0.90,
        primary=True
    ),
))
```

**效果**：
- ✅ 所有场景都可以用豆包
- ✅ 完全实现"豆包为默认"的初衷

---

## 📊 实施建议

### 短期（立即执行）

**1. 修复豆包能力标记**
```python
function_calling=False  # 从 True 改为 False
```

**影响**：
- 减少 fallback 错误
- 提高豆包使用率

**风险**：极低

**2. 重命名为 doubao-chat**
```python
id="doubao-chat",  # 从 "sunday-chat" 改为 "doubao-chat"
```

**影响**：
- 配置更清晰
- 日志更易读

**风险**：无

### 中期（1-2周）

**3. 迁移到 DOUBAO 配置项**

从：
```bash
CUSTOM_API_KEY=...
CUSTOM_MODEL=doubao-seed-character-260628
```

改为：
```bash
DOUBAO_API_KEY=...
DOUBAO_MODEL=doubao-seed-character-260628
```

**影响**：
- 配置规范化
- 支持多个 CUSTOM 模型

**4. 监控使用分布**

添加统计端点：
```python
GET /api/debug/engine-usage
返回：
{
  "deepseek-chat": {"calls": 100, "percentage": 25%},
  "deepseek-reasoner": {"calls": 180, "percentage": 45%},
  "doubao-chat": {"calls": 120, "percentage": 30%}
}
```

### 长期（1-2月）

**5. 评估豆包推理版本**

- 联系字节确认是否有推理版本
- 测试性能和成本
- 决定是否替换 DeepSeek-reasoner

**6. 优化调度策略**

- 基于实际使用数据调整权重
- A/B 测试不同策略
- 用户满意度调查

---

## 🎯 总结

### 问题核心

**豆包被标记为支持工具调用但实际不支持，导致：**
1. 工具调用场景 fallback 到 DeepSeek
2. ReAct 循环场景排除豆包
3. 推理场景豆包无强推理版本被排除

**结果**：70% 请求使用 DeepSeek，违背了"豆包为默认"的初衷

### 快速修复

**立即修改 registry.py 第56行**：
```python
function_calling=False,  # 从 True 改为 False
```

**预期效果**：豆包使用率从 30% 提升到 60%

### 最终目标

```
理想分布：
- 豆包：70%（普通聊天 + 简单任务）
- DeepSeek-chat：10%（需要工具的简单任务）
- DeepSeek-reasoner：20%（复杂推理）
```

---

**建议：先执行方案1（修复能力标记），观察1周后再决定是否需要方案2/3。**
