# DESIGN_SYSTEM.md · Sunday OS 设计规范

> Sunday OS Design Language 1.0 的权威落地。前端一切视觉/交互以此为准。已在 `console/` 落为 CSS 变量与 Tailwind token。

**气质关键词**：Calm · Intelligent · Precise · Alive。参考 Apple HIG / Linear / Raycast / Vercel，**不是** AdminLTE / Bootstrap Dashboard。用户第一次打开应觉得「我在看一个懂我的心智在运行」，而非「一个后台」。

**版本** 1.0 · **最后更新** 2026-07-13 · **负责** Design System Guardian

---

## 1. 核心原则

1. **Less, but Better** —— 每个组件都要有存在意义；非高频不默认展示。
2. **Content First** —— 界面服务认知，动画只表达状态变化。
3. **Spatial Hierarchy** —— 用留白（margin/padding/typography/alignment）建立层级，不靠颜色。
4. **Motion Has Meaning** —— 动画表达状态/数据流动/思考过程，不做装饰。
5. **Intelligence is Visible** —— AI 行为（检索/思考/规划/反思/工具调用）都应可观察。

## 2. 配色（5-7 主色，禁彩虹/渐变背景/高饱和/霓虹）

| 角色 | 值（暗色默认） |
|------|--------------|
| Background | `#0B0B0C` |
| Surface | `#151518` |
| Surface-2 | `#1B1B1F` |
| Border | `rgba(255,255,255,0.08)` |
| Border-strong | `rgba(255,255,255,0.14)` |
| Text Primary | `#F5F5F7` |
| Text Secondary | `rgba(245,245,247,0.62)` |
| Text Tertiary | `rgba(245,245,247,0.38)` |
| Accent | `#0A84FF` |
| Success | `#30D158` |
| Warning | `#FFD60A` |
| Danger | `#FF453A` |

支持 Light 主题（见 `console/src/app/globals.css` 的 `.light`）。

## 3. 字体

- 字族：SF Pro Display / SF Pro Text / Inter / JetBrains Mono（代码）。
- 层级（px）：Display 48 · Heading 32 · Title 24 · Subtitle 18 · Body 16 · Caption 13 · Code 13。
- 标题字重 600，正文 400。**禁大面积粗体**。数字用 tabular-nums。

## 4. 栅格与间距

- **8pt Grid**。间距序列：4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 96。
- 所有组件必须对齐，**不允许随机间距**。

## 5. 圆角

Small 10 · Medium 16 · Large 24 · Panel 28 · Glass Card 32。全站统一。

## 6. 阴影与玻璃

- 阴影**极轻**，更多靠留白 + 边框 + 透明度建立层次。
- 毛玻璃：透明度 10-18%，Blur 20-40px。**禁过度玻璃**。

## 7. 图标

统一 **Lucide**。禁混用 Heroicons / Font Awesome / Material Icons。图标 18-20px。

## 8. 动效（Motion）

- 原则：Fast · Natural · Interruptible · **Spring**。
- 时长：150 / 200 / 250ms；页面切换 300ms。
- **禁** Bounce / Elastic / Flash / Spin。
- 尊重 `prefers-reduced-motion`。

## 9. 布局

- **三栏**：Sidebar（280px）· Content · Inspector（~340px）。
- 底部：Developer Console，可折叠。
- Sidebar：图标 20px、文字 14px、hover surface 提升、当前页 accent border、支持 Command Search（⌘K）。

## 10. 标志性页面

- **Dashboard** = System Overview（非聊天）：卡片布局，指标 + 图表 + 时间线 + 健康。
- **Brain Visualization**（最具特色）：中央 Sunday Core + 周围认知节点（Memory/Emotion/Planner/Reflection/Relationship/Attention/Goal/Tool Runtime）+ 动态连接线 + 呼吸动画 + 实时状态。
- **Memory Center**：Timeline + Inspector。
- **Emotion**：Radar + Line + History。
- **Developer**：IDE 风（Console/Trace/JSON/Logs/Timeline/Inspector）。

## 11. 组件库

Button · Icon Button · Card · Glass Card · Sidebar · Navbar · Tabs · Timeline · Status Badge · Flow Node · Inspector · Console · Command Palette · Search · Tree · Chart · Tooltip · Dialog · Toast · Table · Graph · Avatar · Memory Card · Mood Card · Planner Card · Tool Card · Model Card。

## 12. 无障碍与性能

- Light/Dark · 键盘导航 · Command Palette · 屏幕阅读器 · 高对比 · Reduce Motion。
- 首屏 <2s · 页面切换 <200ms · 动画 60fps · Lazy Loading · Virtual List · Streaming Rendering。

## 13. Token 落地位置

- CSS 变量：`console/src/app/globals.css`
- Tailwind 扩展：`console/tailwind.config.ts`
- 改 token 先改这两处 + 本文件，保持单一真相。
