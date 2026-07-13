# DESIGN_SYSTEM.md · Sunday OS 设计规范与改进建议

> 基于 `console/src/app/globals.css`、`tailwind.config.ts`、`console/src/components/` 和 `webchat.py` 中实际落地的设计 token 总结。并提出改进建议。

**版本** 2.0 · **最后更新** 2026-07-13

---

## 1. 设计气质

**Calm · Intelligent · Precise · Alive**

参考 Apple HIG / Linear / Raycast / Vercel。不是 AdminLTE / Bootstrap Dashboard。用户第一次打开应觉得「我在看一个懂我的心智在运行」，而非「一个后台管理系统」。

六条核心原则：
1. **Less, but Better** —— 每个组件都要有存在意义
2. **Content First** —— 界面服务认知，动画只表达状态变化
3. **Spatial Hierarchy** —— 靠留白建立层级，不靠颜色
4. **Motion Has Meaning** —— 动画表达状态/数据流动/思考过程
5. **Intelligence is Visible** —— AI 行为可观察
6. **禁彩虹/高饱和/霓虹** —— 克制是第一准则

---

## 2. 当前落地的 Design Token

### 2.1 配色（暗色默认）

这些 token 在 `globals.css` (CSS 变量)、`tailwind.config.ts` (Tailwind 类)、`webchat.py` 的 `<style>` 块（Chat UI 内联样式）三处 **完全一致**：

| 角色 | 值 | 用途 |
|------|-----|------|
| `--bg` | `#0B0B0C` | 页面背景 |
| `--surface` | `#151518` | 卡片/面板底色 |
| `--surface-2` | `#1B1B1F` | 次级表面（如选中态） |
| `--elevated` | `#232328` | 浮层（仅前端） |
| `--border` | `rgba(255,255,255,0.08)` | 默认边框 |
| `--border-strong` | `rgba(255,255,255,0.14)` | 强调边框（hover 时） |
| `--text-primary` | `#F5F5F7` | 正文 |
| `--text-secondary` | `rgba(245,245,247,0.62)` | 辅助文字 |
| `--text-tertiary` | `rgba(245,245,247,0.38)` | 弱化文字（caption/placeholder） |
| `--accent` | `#0A84FF` | 主强调色（按钮/链接/选中） |
| `--success` | `#30D158` | 成功/在线/健康 |
| `--warning` | `#FFD60A` | 警告 |
| `--danger` | `#FF453A` | 危险/错误 |

Light 主题开关已实现（`globals.css` 的 `.light` 类 + `ui.tsx` 的 `toggleTheme()`）。

**背景氛围**：
- 两处径向渐变（`body::before`）：右上角蓝色光晕 (`rgba(10,132,255,0.09)`) + 左下角绿色光晕 (`rgba(48,209,88,0.05)`)
- 前端和 Chat UI 均实现了相同的氛围效果
- **这两处渐变范围不完全一致**（前端 `0.09` / Chat UI `0.10`），建议统一

### 2.2 字体

| 层级 | 大小 | 字重 | 行高 | 使用场景 |
|------|------|------|------|---------|
| Display | 48px | 600 | 1.05 | 极少使用（首页大标题） |
| Heading | 32px | 600 | 1.1 | 页面标题 |
| Title | 24px | 600 | 1.15 | 区块标题 |
| Subtitle | 18px | 600 | 1.3 | 卡片标题 (Dashboard/Brain) |
| Body | 16px | 400 | 1.5 | 正文默认 |
| Caption | 13px | 400 | 1.4 | 辅助说明 |
| Code | 13px | 400 | 1.5 | 代码块 |

字族：`SF Pro Display` → `SF Pro Text` → `Inter` → system-ui (sans)；`JetBrains Mono` → `SFMono-Regular` (mono)

**数字用 tabular-nums** 确保对齐（metric value 列）。

### 2.3 间距（8pt Grid）

序列：4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 96 (px)

Tailwind 扩展映射：`p-1`=4px, `p-2`=8px, `p-3`=12px, `p-4`=16px, `p-6`=24px, `p-8`=32px, `p-10`=40px, `p-12`=48px, `p-16`=64px, `p-24`=96px

**落地状态**：✅ 前端组件全部遵循（`dashboard.tsx` 用 `gap-4`=`16px`、`p-5`=`20px`…）；Chat UI 使用原始 px 值但数值对齐 8pt。

### 2.4 圆角

| Token | 值 | 用途 |
|-------|-----|------|
| `rounded-sm` | 10px | 按钮/输入框/小图标框 |
| `rounded-md` | 16px | 中等组件 |
| `rounded-lg` | 24px | 卡片 (card) |
| `rounded-panel` | 28px | 面板 |
| `rounded-glass` | 32px | 毛玻璃卡片 |

### 2.5 阴影与玻璃

- **阴影极轻**，更多靠留白 + 边框 + 透明度。
- `shadow-subtle`：`0 1px 2px rgba(0,0,0,0.24)`
- `shadow-card`：`0 8px 30px rgba(0,0,0,0.18)`
- `shadow-glow`：`0 0 0 1px var(--border), 0 20px 60px rgba(0,0,0,0.35)`
- 毛玻璃：`backdrop-filter: blur(28px) saturate(160%)` + `rgba(255,255,255,0.045)` 背景 + border
- **禁过度玻璃** —— 仅 Sidebar/Header/浮层使用

### 2.6 动效

**原则**：Fast · Natural · Interruptible · **Spring**

- 时长：150 / 200 / 250ms；页面切换 300ms
- Easing：`cubic-bezier(0.22, 1, 0.36, 1)` (spring)
- **已定义的关键帧**：
  - `breathe`：4s 呼吸循环（scale 1→1.06→1），用于 Brain core
  - `fade-up`：250ms spring 渐入
  - `dash-flow`：1.2s 虚线流动（Brain 连接线）
  - `shimmer`：shimmer 效果
- **绝对禁止**：Bounce / Elastic / Flash / Spin / 彩虹色动画
- 尊重 `prefers-reduced-motion`：✅ 已在 `globals.css` 实现

### 2.7 图标

**统一 Lucide**（v0.474.0），18-20px 为主。禁混用 Heroicons / Font Awesome / Material Icons。

### 2.8 布局

- **三栏**：Sidebar（280px，固定）· Content（flex-1）· Inspector（~340px，可折叠）
- **底部**：Console Dock（可折叠，⌘J）
- Sidebar 特征：图标 18px、文字 14px、hover surface 提升、当前页 accent border + accent-soft 背景

---

## 3. 当前设计落地的亮点

1. **Token 层一致性高**：CSS 变量 → Tailwind 扩展 → 组件使用，三层映射清晰无矛盾。
2. **Brain Visualization 是标志性设计**：SVG 手绘认知架构图，核心发光呼吸动画 + 8 节点负载环 + 信号脉冲动画——这是 Sunday 独有的视觉资产。
3. **Dashboard 布局成熟**：8 指标卡 + 折线图 + 雷达图 + 环形图 + 时间线——信息密度高但不显拥挤。
4. **Chat UI 与 Design System 对齐**：虽然是内联 HTML，但颜色/间距/圆角 token 与前端一致。
5. **无障碍起步**：prefers-reduced-motion、键盘导航（⌘K）、Light/Dark 主题均已实现。

---

## 4. 改进建议

### 4.1 🔴 高优先级——需要立即修复

| # | 问题 | 现状 | 建议 |
|---|------|------|------|
| 1 | **背景氛围渐变不一致** | 前端 `body::before` opacity `0.09`(蓝)/`0.05`(绿)，Chat UI 用 `0.10`(蓝)/`0.05`(绿) | 统一为 `0.09`，定义为 CSS 变量 |
| 2 | **前端 Chat UI (chat.tsx) 与内嵌 Chat UI (webchat.py) 风格不一致** | 前端 ChatView 用 Tailwind，webchat.py 用内联样式 | webchat.py 应作为「轻量预览版」，前端 ChatView 应作为「完整版」，明确两者定位 |
| 3 | **缺少 Brand 色彩定义** | Sunday 品牌色（渐变 `#0a84ff→#5e5ce6→#30d158`）散落在多处硬编码 | 定义为 `--brand-start`/`--brand-mid`/`--brand-end` CSS 变量 |

### 4.2 🟡 中优先级——改进体验

| # | 问题 | 现状 | 建议 |
|---|------|------|------|
| 4 | **缺少 Loading/Skeleton 状态规范** | 对话只有 typing dots，数据加载无统一骨架屏 | 定义 Skeleton 组件（`bg-[var(--surface-2)] animate-pulse rounded`） |
| 5 | **缺少 Empty State 规范** | Dashboard 无空状态设计，Chat UI 有空状态 | 统一空状态组件（图标+标题+描述+CTA），在所有视图中复用 |
| 6 | **缺少 Error State 规范** | 错误信息散落在各处，无不统一 | 定义 ErrorBanner 组件（`danger` 色调 + icon + message + retry） |
| 7 | **Inspector 面板未充分利用** | 右侧 Inspector 只有 UI 外壳 | 当选中 Brain 节点时，Inspector 显示详情；当查看记忆时显示记忆详情 |
| 8 | **缺少 Responsive 断点规范** | Dashboard grid 有响应式断点 (`grid-cols-2 md:grid-cols-3 xl:grid-cols-4`)，但无文档 | 定义 4 个断点：Mobile(<520px) / Tablet(768px) / Desktop(1280px) / Wide(1600px) |

### 4.3 🟢 低优先级——未来方向

| # | 问题 | 现状 | 建议 |
|---|------|------|------|
| 9 | **Design Token 与 Figma 同步** | 无 Figma 文件 | 建立 Figma 组件库 → CSS 变量同步脚本 |
| 10 | **录音/语音交互 UI** | 无设计 | 设计语音胶囊 UI（配合 `voice_input: true` 参数） |
| 11 | **记忆时间线可视化** | Memory Center 只有 ComingSoon | 参考 Apple Health 的时间线设计语言 |
| 12 | **数据看板夜间模式优化** | colors 在 dark 下已验证，light 下有定义但未充分测试 | 补充 light 模式截图审查 |
| 13 | **动画 token 集中管理** | 动画参数散落在 framer-motion variants 中 | 抽取为共享 token (`transition.spring` / `transition.fast` / `transition.page`) |

---

## 5. 组件库清单

### 已实现的组件

| 组件 | 文件 | 变体 | 状态 |
|------|------|------|------|
| Card | `primitives.tsx` | default / glass | ✅ |
| Badge | `primitives.tsx` | neutral / ok / warn / danger / accent | ✅ |
| Sparkline | `primitives.tsx` | 可自定义颜色和高度 | ✅ |
| Donut | `primitives.tsx` | 可自定义 size/stroke/color | ✅ |
| Radar | `primitives.tsx` | 可自定义 axes/values/size/color | ✅ |
| SectionTitle | `primitives.tsx` | title + hint + action | ✅ |
| Sidebar | `sidebar.tsx` | 带分组导航 + spring 活动态 | ✅ |
| Command Palette | `command-palette.tsx` | ⌘K 触发 | ✅ |
| TopBar | `topbar.tsx` | — | ✅ |
| Inspector | `inspector.tsx` | — | ✅ |
| Console Dock | `console-dock.tsx` | 可折叠 | ✅ |

### 待实现的组件

| 组件 | 说明 | 优先级 |
|------|------|--------|
| Skeleton | 加载骨架屏 | 🔴 |
| EmptyState | 空状态统一组件 | 🟡 |
| ErrorBanner | 错误提示横幅 | 🟡 |
| Toast | 操作反馈提示 | 🟡 |
| Dialog/Modal | 确认弹窗（HITL 需要） | 🟡 |
| Timeline | 记忆时间线（Memory Center） | 🟢 |
| Memory Card | 记忆卡片（Memory Center） | 🟢 |
| Tool Card | 工具卡片（技能管理） | 🟢 |
| Model Card | 引擎卡片（引擎管理） | 🟢 |
| Mood Card | 情绪卡片（Emotion 页面） | 🟢 |
```

## 6. 设计维护纪律

1. **改 token 先改 `globals.css` + `tailwind.config.ts`**，再改本文件。
2. **新增组件必须使用已有 token**，不允许引入新的颜色/间距/圆角值。
3. **新增页面/视图需经 Design Guardian 审查** 视觉一致性。
4. **Chat UI (webchat.py) 的 token 需与前端同步** —— 改一边要改另一边。
5. 每季度做一次 **全局视觉审查**，发现偏离 token 的硬编码并修正。
