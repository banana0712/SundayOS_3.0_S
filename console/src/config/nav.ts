import {
  LayoutDashboard,
  Brain,
  MessagesSquare,
  Database,
  UserCog,
  HeartPulse,
  Waypoints,
  Bot,
  Workflow,
  Sparkles,
  BookOpen,
  Plug,
  Wrench,
  Boxes,
  CalendarClock,
  Activity,
  ScrollText,
  Gauge,
  Settings,
  Code2,
  Webhook,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  slug: string;
  label: string;
  icon: LucideIcon;
  group: string;
};

// Mirrors Console 设计文档 · Sidebar. slug "" = Chat (default landing).
export const NAV: NavItem[] = [
  { slug: "", label: "Chat", icon: MessagesSquare, group: "Overview" },
  { slug: "dashboard", label: "Dashboard", icon: LayoutDashboard, group: "Overview" },
  { slug: "brain", label: "Brain", icon: Brain, group: "Overview" },

  { slug: "memory", label: "Memory", icon: Database, group: "Cognition" },
  { slug: "personality", label: "Personality", icon: UserCog, group: "Cognition" },
  { slug: "emotion", label: "Emotion", icon: HeartPulse, group: "Cognition" },
  { slug: "relationship", label: "Relationship", icon: Waypoints, group: "Cognition" },
  { slug: "planner", label: "Planner", icon: Bot, group: "Cognition" },

  { slug: "workflow", label: "Workflow", icon: Workflow, group: "Build" },
  { slug: "prompt", label: "Prompt Studio", icon: Sparkles, group: "Build" },
  { slug: "knowledge", label: "Knowledge", icon: BookOpen, group: "Build" },
  { slug: "mcp", label: "MCP", icon: Plug, group: "Build" },
  { slug: "tools", label: "Tools", icon: Wrench, group: "Build" },
  { slug: "model", label: "Model", icon: Boxes, group: "Build" },

  { slug: "scheduler", label: "Scheduler", icon: CalendarClock, group: "Operate" },
  { slug: "events", label: "Events", icon: Activity, group: "Operate" },
  { slug: "logs", label: "Logs", icon: ScrollText, group: "Operate" },
  { slug: "evaluation", label: "Evaluation", icon: Gauge, group: "Operate" },

  { slug: "developer", label: "Developer", icon: Code2, group: "System" },
  { slug: "api", label: "API", icon: Webhook, group: "System" },
  { slug: "settings", label: "Settings", icon: Settings, group: "System" },
];

export const NAV_GROUPS = ["Overview", "Cognition", "Build", "Operate", "System"];
