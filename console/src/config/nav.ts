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

export type ModuleStatus = "done" | "partial" | "planned";

export type NavItem = {
  slug: string;
  label: string;
  icon: LucideIcon;
  group: string;
  status: ModuleStatus;
};

// Mirrors Console 设计文档 · Sidebar. slug "" = Chat (default landing).
export const NAV: NavItem[] = [
  { slug: "", label: "Chat", icon: MessagesSquare, group: "Overview", status: "done" },
  { slug: "dashboard", label: "Dashboard", icon: LayoutDashboard, group: "Overview", status: "partial" },
  { slug: "brain", label: "Brain", icon: Brain, group: "Overview", status: "partial" },

  { slug: "memory", label: "Memory", icon: Database, group: "Cognition", status: "partial" },
  { slug: "personality", label: "Personality", icon: UserCog, group: "Cognition", status: "planned" },
  { slug: "emotion", label: "Emotion", icon: HeartPulse, group: "Cognition", status: "planned" },
  { slug: "relationship", label: "Relationship", icon: Waypoints, group: "Cognition", status: "planned" },
  { slug: "planner", label: "Planner", icon: Bot, group: "Cognition", status: "planned" },

  { slug: "workflow", label: "Workflow", icon: Workflow, group: "Build", status: "planned" },
  { slug: "prompt", label: "Prompt Studio", icon: Sparkles, group: "Build", status: "planned" },
  { slug: "knowledge", label: "Knowledge", icon: BookOpen, group: "Build", status: "planned" },
  { slug: "mcp", label: "MCP", icon: Plug, group: "Build", status: "planned" },
  { slug: "tools", label: "Tools", icon: Wrench, group: "Build", status: "partial" },
  { slug: "model", label: "Model", icon: Boxes, group: "Build", status: "partial" },

  { slug: "scheduler", label: "Scheduler", icon: CalendarClock, group: "Operate", status: "planned" },
  { slug: "events", label: "Events", icon: Activity, group: "Operate", status: "planned" },
  { slug: "logs", label: "Logs", icon: ScrollText, group: "Operate", status: "planned" },
  { slug: "evaluation", label: "Evaluation", icon: Gauge, group: "Operate", status: "planned" },

  { slug: "developer", label: "Developer", icon: Code2, group: "System", status: "planned" },
  { slug: "api", label: "API", icon: Webhook, group: "System", status: "planned" },
  { slug: "settings", label: "Settings", icon: Settings, group: "System", status: "planned" },
];

export const NAV_GROUPS = ["Overview", "Cognition", "Build", "Operate", "System"];
