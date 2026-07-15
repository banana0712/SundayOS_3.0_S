# /checkup · SundayOS 项目体检

> **给项目主人的自检工具。** 在任意会话输入 `/checkup`，AI 会自动扫描项目健康状况，
> 用**大白话**给你一份体检报告——不需要你懂代码。
>
> 设计前提：主人不读代码、时间有限。所以每一条发现都必须回答三件事：
> **① 这是什么 ② 对你意味着什么 ③ 要不要管、怎么管。** 禁止甩术语不解释。
>
> 核心理念：软件不会"崩溃"，它会**慢慢腐烂**。这个体检就是定期闻一闻哪里开始发臭，
> 趁早处理。烂是可逆的——早发现就是小事。
>
> **本体检以 `docs/ENGINEERING_CONTRACT.md`（开发契约）为评判标准。** 契约定规矩，
> 本 skill 查违规。开查前先读一遍契约，按它的硬限制（单文件 ≤600 行、路由按域拆、
> 单一真相源、完成定义）逐项核对。

---

## 执行流程（严格按序，能并行的命令并行跑）

### ① 安全红线（🔴 最高优先，先查这个）

```bash
# 1. 明文密钥泄露：扫追踪中的文件里有没有像 API Key 的东西
git ls-files | grep -iE "readme|其他|\.env|secret|key|token" 
grep -rEn "sk-[a-zA-Z0-9]{16,}|[a-f0-9]{32}" --include="*.txt" --include="*.md" --include="*.py" . | grep -viE "example|test|fake|xxx|your-|placeholder" | head -20
# 2. .env 是否被 .gitignore 挡住
git check-ignore .env && echo ".env 已忽略 ✅" || echo "⚠️ .env 未被忽略"
# 3. .env 有没有被误提交进 git 历史
git ls-files | grep -E "\.env$" && echo "⚠️ .env 在版本控制里" || echo ".env 不在 git ✅"
```

判定：任何真实密钥出现在追踪文件里 = 🔴 立即轮换。`readme.txt`/`其他.txt` 已知含明文 key，
每次都要提醒主人轮换。

### ② 基本生命体征（能不能跑）

```bash
cd backend && python -m pytest -q 2>&1 | tail -5
cd ../console && npm run build 2>&1 | tail -8
```

判定：测试红 = 🔴（有东西坏了，别加新功能）。build 失败 = 🔴。全绿 = 🟢。
**这是主人最该盯的一条：不懂代码也能看懂"全绿 / 有红"。**

### ③ 屎山预警（腐烂指标）

```bash
# 最大的几个文件（行数）——上帝文件是腐烂的第一征兆
find backend/app console/src -name "*.py" -o -name "*.tsx" -o -name "*.ts" | xargs wc -l 2>/dev/null | sort -rn | head -12
# 后端路由集中度：一个文件塞了多少路由
grep -c "@app\." backend/app/main.py
# 未完成标记：TODO / FIXME / 占位 / 硬编码提示
grep -rEn "TODO|FIXME|XXX|占位|placeholder|hack|临时" backend/app console/src 2>/dev/null | wc -l
```

判定阈值（大白话解释给主人）：
- 单文件 > 800 行 = 🟡「这个文件太胖了，改它容易碰坏别的」；> 1200 行 = 🔴「该拆了」。
- `main.py` 路由数 > 30 = 🟡「所有功能挤在一个文件，迟早难维护」。
- TODO 类标记数量给出趋势（和上次比是多了还是少了，若无历史就报当前值）。

### ④ 演戏检测（假数据 / 骗自己）

```bash
# 前端写死的假数据、随机漂移、mock
grep -rEn "useDrift|mock|const .* = \[" console/src/components/views 2>/dev/null | grep -iE "mock|useDrift|todo|fake|demo|placeholder" | head -20
# 展示了但项目其实没用的组件（危险：让你以为系统是那个样子）
grep -rEn "Qdrant|Redis|Postgres|Kafka|Milvus|ChromaDB|MCP" console/src 2>/dev/null | head -10
```

然后 AI **实际读**可疑的前端视图文件，判断：这个数字/状态是真的从后端来的，还是写死演给人看的？
判定：展示不存在的组件/架构 = 🟡「你的界面在展示你实际没用的东西，会误导你自己对系统的判断」。

### ⑤ 双真相 / 代码漂移（隐蔽但危险）

```bash
# 找几乎重复的路由（一个功能两条路，容易走偏——比如一条记了统计另一条忘了）
# 去掉 /stream 后缀后看哪些路径成对出现 = 有平行实现
grep -oE "@app\.(get|post|put|delete)\(\"[^\"]+\"" backend/app/main.py | grep -oE "\"[^\"]+\"" | tr -d '"' | sed -E 's#/stream$##' | sort | uniq -d
# 注意：同一路径的 GET+POST（如 /api/conversations 列表+新建）是正常 REST，不算重复；
# AI 要判断的是"两段代码做同一件事"（如 /api/chat 和 /api/chat/stream 各写一遍聊天逻辑）
# runtime 是否被架空：模块级全局单例 vs runtime.* 的使用比例
grep -c "^[A-Z_]* = " backend/app/main.py
grep -c "runtime\." backend/app/main.py
```

AI 判断：有没有"两套做同一件事"的代码？（这次体检的历史教训：`/api/chat` 和 `/api/chat/stream`
两条路，流式那条曾忘了记统计，导致仪表盘少算。重复代码早晚走偏。）
判定：发现平行路径 = 🟡「有两段代码做几乎一样的事，改了一个忘了另一个就会出现"数据不对但不报错"的问题」。

### ⑥ 文档诚实度（地图对不对得上地形）

```bash
# 版本号三处是否一致
cat VERSION
grep -m1 "## \[" CHANGELOG.md
grep -m1 "版本" docs/CURRENT_STATE.md
# 测试数量：CURRENT_STATE 声称的 vs 实际
grep -iE "passed|测试" docs/CURRENT_STATE.md | head -3
# 未提交的改动（漂了没记）
git status --short
git log --oneline -5
```

AI 判断：CURRENT_STATE / ROADMAP 里写的"能做什么"，和代码实际状态对得上吗？
版本号 VERSION / CHANGELOG / CURRENT_STATE 三处一致吗？有没有一堆改动没提交、没记文档？
判定：文档吹牛或滞后 = 🟡「你的文档是未来 AI 唯一能信的地图。地图和实际不符，下一个 AI 就会走错路」。

### ⑦ 依赖健康（可选，较慢，主人要求时才跑）

```bash
cd backend && pip list --outdated 2>/dev/null | head -15
cd ../console && npm outdated 2>/dev/null | head -15
```

判定：只报"有 N 个依赖可更新"，不强制。安全相关的（含 CVE）才标 🟡。

---

## 输出格式：给主人的体检报告

**用中文、大白话、体检报告的口吻。** 结构如下：

```
🏥 SundayOS 体检报告 · <日期> · v<版本>

总体：🟢 健康 / 🟡 有几处该关注 / 🔴 有急事要处理

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 急事（如果有——先说这个）
  · <一句话说清楚：什么问题 + 对你什么影响 + 建议动作>

🟡 该关注（不急，但别放太久）
  · <同上格式，每条都要有"这对你意味着什么">

🟢 健康的部分（让主人安心）
  · 测试 N 个全绿 —— 核心功能没坏
  · <其他好消息>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 逐项明细（主人想细看时）
  ① 安全红线：<结果>
  ② 生命体征：测试 <N passed> · 前端构建 <过/failed>
  ③ 屎山预警：最大文件 <名字 N 行> · main.py <N 路由>
  ④ 演戏检测：<有无假数据>
  ⑤ 双真相：<有无平行路径>
  ⑥ 文档诚实度：<版本一致？文档对得上？>

💡 我的建议（最多 3 条，按该不该现在做排序）
  1. <具体到"让下一个 AI 做 X"，主人能直接复制去用>
  2. ...
```

---

## 执行约束（重要）

- **主人不读代码。** 每条发现必须翻译成"这对你意味着什么"。禁止只说
  "main.py 1383 行"就完事——要说"这个核心文件太胖了，以后改动越来越危险，建议拆分"。
- **红事优先、报喜也报忧。** 先说急事，但也要明确告诉主人哪些是健康的——
  否则他只看到问题会焦虑。健康的部分要真实列出来让他安心。
- **命令失败不等于项目有病。** 分清"检查工具本身没跑起来"（环境问题）和"项目真有问题"。
  跑不动的检查就如实说"这项没测成"，别瞎判。
- **不自动修。** 体检只诊断、不动手。发现问题给出"建议让 AI 做什么"，由主人决定。
  （安全红线如密钥泄露可以主动强烈提醒，但轮换 key 本身要主人去 provider 后台做。）
- **诚实。** 测试失败就说失败并附输出；文档滞后就点명。这个 skill 存在的唯一意义
  就是当那个"偶尔诚实告诉你哪里开始发臭"的人。粉饰太平等于没做。
- **给可执行的下一步。** 建议要具体到主人能直接说给下一个 AI："照 checkup 报告的第 2 条，
  把 XX 拆分"。别给"建议优化代码结构"这种没法执行的空话。
- **环境提醒**：后端从 `.env` 读配置（dotenv override=True），测 API 相关的用 `.env` 里的值，
  别指望 shell export（见 memory `backend-env-gotchas`）。

