// Bilingual dictionary (zh / en). One key → both languages.
// Add a key here, use t("key") anywhere. Missing key falls back to the key.

export type Lang = "zh" | "en";

export const DICT: Record<string, { zh: string; en: string }> = {
  // Brand / shell
  "brand.subtitle": { zh: "控制中心", en: "Control Center" },
  "status.online": { zh: "在线", en: "Online" },
  "search.placeholder": { zh: "搜索或跳转…", en: "Search or jump to…" },

  // Nav groups
  "group.Overview": { zh: "总览", en: "Overview" },
  "group.Cognition": { zh: "认知", en: "Cognition" },
  "group.Build": { zh: "构建", en: "Build" },
  "group.Operate": { zh: "运维", en: "Operate" },
  "group.System": { zh: "系统", en: "System" },

  // Nav items (by slug; "" = dashboard)
  "nav.chat": { zh: "对话", en: "Chat" },
  "nav.": { zh: "仪表盘", en: "Dashboard" },
  "nav.brain": { zh: "大脑", en: "Brain" },
  "nav.memory": { zh: "记忆", en: "Memory" },
  "nav.personality": { zh: "人格", en: "Personality" },
  "nav.emotion": { zh: "情绪", en: "Emotion" },
  "nav.relationship": { zh: "关系", en: "Relationship" },
  "nav.planner": { zh: "规划器", en: "Planner" },
  "nav.workflow": { zh: "工作流", en: "Workflow" },
  "nav.prompt": { zh: "提示工作室", en: "Prompt Studio" },
  "nav.knowledge": { zh: "知识库", en: "Knowledge" },
  "nav.mcp": { zh: "MCP", en: "MCP" },
  "nav.tools": { zh: "工具", en: "Tools" },
  "nav.model": { zh: "模型", en: "Model" },
  "nav.scheduler": { zh: "调度", en: "Scheduler" },
  "nav.events": { zh: "事件", en: "Events" },
  "nav.logs": { zh: "日志", en: "Logs" },
  "nav.evaluation": { zh: "评估", en: "Evaluation" },
  "nav.developer": { zh: "开发者", en: "Developer" },
  "nav.api": { zh: "API", en: "API" },
  "nav.settings": { zh: "设置", en: "Settings" },

  // Topbar
  "top.notifications": { zh: "通知", en: "Notifications" },
  "top.theme": { zh: "切换主题", en: "Toggle theme" },
  "top.console": { zh: "切换控制台", en: "Toggle console" },
  "top.inspector": { zh: "切换检查器", en: "Toggle inspector" },
  "top.lang": { zh: "切换语言", en: "Switch language" },

  // Chat
  "chat.title": { zh: "与 Sunday 对话", en: "Chat with Sunday" },
  "chat.subtitle": { zh: "一个心智，服务你的一切", en: "One mind for every task" },
  "chat.placeholder": { zh: "对 Sunday 说点什么…", en: "Say something to Sunday…" },
  "chat.send": { zh: "发送", en: "Send" },
  "chat.thinking": { zh: "Sunday 正在思考…", en: "Sunday is thinking…" },
  "chat.empty.title": { zh: "开始和 Sunday 聊天", en: "Start a conversation" },
  "chat.empty.hint": {
    zh: "问它任何事——写代码、记事、规划、或只是聊聊。",
    en: "Ask anything — code, notes, plans, or just chat.",
  },
  "chat.you": { zh: "你", en: "You" },
  "chat.newchat": { zh: "新对话", en: "New chat" },
  "chat.engine": { zh: "引擎", en: "engine" },
  "chat.system.talker": { zh: "快思考", en: "fast" },
  "chat.system.reasoner": { zh: "慢思考", en: "deep" },
  "chat.err.offline": {
    zh: "连不上后端。请确认后端已启动（见下方提示）。",
    en: "Can't reach the backend. Make sure it's running (see hint below).",
  },
  "chat.err.generic": { zh: "出错了，请重试。", en: "Something went wrong. Try again." },
  "chat.backend.down": { zh: "后端未连接", en: "Backend offline" },
  "chat.backend.up": { zh: "后端已连接", en: "Backend connected" },
  "chat.backend.hint": {
    zh: "在 backend 目录运行：python -m uvicorn app.main:app --port 8000",
    en: "In the backend folder run: python -m uvicorn app.main:app --port 8000",
  },
  "chat.mock.note": {
    zh: "当前是占位回复（未配 API Key）。填好 Key 重启后端即为真实回复。",
    en: "Placeholder reply (no API key set). Add a key and restart the backend for real answers.",
  },

  // Dashboard
  "dash.overview": { zh: "系统总览 · 认知模块运行正常", en: "System Overview · all cognitive modules nominal" },
  "dash.greeting": { zh: "下午好。Sunday 思路清晰。", en: "Good afternoon. Sunday is thinking clearly." },
  "dash.metric.messages": { zh: "今日消息", en: "Messages today" },
  "dash.metric.calls": { zh: "模型调用", en: "Model calls" },
  "dash.metric.tokens": { zh: "Token 用量", en: "Tokens" },
  "dash.metric.cost": { zh: "今日花费", en: "Cost (today)" },
  "dash.metric.memories": { zh: "记忆条数", en: "Memories" },
  "dash.metric.latency": { zh: "平均延迟", en: "Avg latency" },
  "dash.metric.tools": { zh: "活跃工具", en: "Active tools" },
  "dash.metric.success": { zh: "成功率", en: "Success rate" },
  "dash.activity": { zh: "活动", en: "Activity" },
  "dash.activity.sub": { zh: "请求 · 近 24 小时", en: "Requests · last 24h" },
  "dash.emotion": { zh: "情绪", en: "Emotion" },
  "dash.emotion.sub": { zh: "实时情感状态", en: "Live affective state" },
  "dash.health": { zh: "系统健康", en: "System Health" },
  "dash.health.sub": { zh: "运行时资源", en: "Runtime resources" },
  "dash.goal": { zh: "当前目标", en: "Current Goal" },
  "dash.goal.sub": { zh: "规划器 · 日本旅行", en: "Planner · trip to Japan" },
  "dash.events": { zh: "近期事件", en: "Recent Events" },
  "dash.events.all": { zh: "全部", en: "All" },

  // Brain
  "brain.title": { zh: "认知核心", en: "Cognitive Core" },
  "brain.subtitle": { zh: "实时观察 Sunday 的心智", en: "Real-time view of Sunday's mind" },
  "brain.thinking": { zh: "思考中", en: "thinking" },
  "brain.modules": { zh: "模块", en: "Modules" },
  "brain.load": { zh: "负载", en: "Load" },

  // Coming soon
  "soon.body": {
    zh: "该模块已映射到 Sunday OS 架构，正在开发队列中。所有界面遵循同一设计语言。",
    en: "This module is mapped to the Sunday OS architecture and is next in the build queue.",
  },
  "soon.back": { zh: "返回仪表盘", en: "Back to Dashboard" },
};
