"use client";

import { motion } from "framer-motion";
import {
  MessageSquare,
  Coins,
  Timer,
  Database,
  Cpu,
  MemoryStick,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Activity,
  Sparkles,
  Brain,
  Wrench,
  Users,
  ArrowUpRight,
} from "lucide-react";
import { Card, Donut, Radar, Badge, Sparkline } from "@/components/ui/primitives";
import { useDrift } from "@/store/ui";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";

import type { Variants } from "framer-motion";

const fade: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.04, type: "spring", stiffness: 260, damping: 28 },
  }),
};

export function DashboardView() {
  const { t } = useI18n();
  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      {/* Header */}
      <motion.div variants={fade} custom={0} initial="hidden" animate="show" className="mb-6">
        <div className="flex items-center gap-2 text-caption text-tertiary">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
          </span>
          {t("dash.overview")}
        </div>
        <h1 className="mt-1 text-heading text-primary text-balance">
          {t("dash.greeting")}
        </h1>
      </motion.div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
        {METRICS.map((m, i) => (
          <motion.div key={m.key} variants={fade} custom={i + 1} initial="hidden" animate="show">
            <MetricCard labelKey={m.key} value={m.value} delta={m.delta} icon={m.icon} color={m.color} data={m.data} />
          </motion.div>
        ))}
      </div>

      {/* Second row: activity chart + mood + goal */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <motion.div variants={fade} custom={8} initial="hidden" animate="show" className="lg:col-span-2">
          <ActivityCard />
        </motion.div>
        <motion.div variants={fade} custom={9} initial="hidden" animate="show">
          <MoodCard />
        </motion.div>
      </div>

      {/* Third row: health + timeline + events */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <motion.div variants={fade} custom={10} initial="hidden" animate="show">
          <HealthCard />
        </motion.div>
        <motion.div variants={fade} custom={11} initial="hidden" animate="show">
          <GoalCard />
        </motion.div>
        <motion.div variants={fade} custom={12} initial="hidden" animate="show">
          <EventsCard />
        </motion.div>
      </div>
    </div>
  );
}

/* ── Metric definitions ─────────────────────────────────── */
const spark = (seed: number) =>
  Array.from({ length: 16 }, (_, i) => 40 + Math.sin(i / 2 + seed) * 18 + (i % 3) * 6 + seed * 2);

const METRICS = [
  { key: "dash.metric.messages", value: "1,284", delta: +12.4, icon: MessageSquare, color: "var(--accent)", data: spark(1) },
  { key: "dash.metric.calls", value: "3,921", delta: +6.1, icon: Sparkles, color: "#5e5ce6", data: spark(2) },
  { key: "dash.metric.tokens", value: "1.42M", delta: +18.9, icon: Coins, color: "#bf5af2", data: spark(3) },
  { key: "dash.metric.cost", value: "$8.74", delta: -3.2, icon: TrendingUp, color: "var(--success)", data: spark(1.5) },
  { key: "dash.metric.memories", value: "48,301", delta: +2.0, icon: Database, color: "#64d2ff", data: spark(4) },
  { key: "dash.metric.latency", value: "412ms", delta: -8.7, icon: Timer, color: "var(--warning)", data: spark(2.5) },
  { key: "dash.metric.tools", value: "11", delta: 0, icon: Wrench, color: "#ff9f0a", data: spark(3.2) },
  { key: "dash.metric.success", value: "99.2%", delta: +0.4, icon: CheckCircle2, color: "var(--success)", data: spark(0.5) },
] as const;

function MetricCard({
  labelKey,
  value,
  delta,
  icon: Icon,
  color,
  data,
}: {
  labelKey: string;
  value: string;
  delta: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  data: number[];
}) {
  const { t } = useI18n();
  const up = delta > 0;
  const flat = delta === 0;
  return (
    <Card className="group overflow-hidden p-4">
      <div className="flex items-start justify-between">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-border"
          style={{ color }}
        >
          <Icon className="h-[18px] w-[18px]" />
        </div>
        <span
          className={cn(
            "flex items-center gap-0.5 text-[11px] font-medium tabular-nums tnum",
            flat ? "text-tertiary" : up ? "text-success" : "text-danger"
          )}
        >
          {!flat && (up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />)}
          {flat ? "—" : `${up ? "+" : ""}${delta}%`}
        </span>
      </div>
      <div className="mt-3 text-[26px] font-semibold leading-none tracking-tight tnum">{value}</div>
      <div className="mt-1 text-caption text-tertiary">{t(labelKey)}</div>
      <div className="-mx-4 -mb-4 mt-3 opacity-70 transition-opacity group-hover:opacity-100">
        <Sparkline data={data} color={color} height={40} />
      </div>
    </Card>
  );
}

/* ── Activity (line) ────────────────────────────────────── */
function ActivityCard() {
  const { t } = useI18n();
  const series = Array.from({ length: 48 }, (_, i) =>
    52 + Math.sin(i / 3.4) * 22 + Math.sin(i / 1.3) * 8 + (i > 30 ? (i - 30) * 1.1 : 0)
  );
  return (
    <Card className="h-full p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-subtitle text-primary">{t("dash.activity")}</h3>
          <p className="text-caption text-tertiary">{t("dash.activity.sub")}</p>
        </div>
        <div className="flex gap-1 rounded-full border border-border p-0.5 text-[11px]">
          {["24h", "7d", "30d"].map((range, i) => (
            <button
              key={range}
              className={cn(
                "rounded-full px-2.5 py-1 transition-colors",
                i === 0 ? "bg-[var(--surface-2)] text-primary" : "text-tertiary hover:text-secondary"
              )}
            >
              {range}
            </button>
          ))}
        </div>
      </div>
      <BigLine data={series} />
      <div className="mt-4 grid grid-cols-3 gap-3 border-t border-border pt-4">
        <MiniStat label="Peak" value="1,204 / hr" />
        <MiniStat label="p95 latency" value="618 ms" tone="warn" />
        <MiniStat label="Errors" value="0.8%" tone="ok" />
      </div>
    </Card>
  );
}

function BigLine({ data }: { data: number[] }) {
  const w = 640;
  const h = 180;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1);
  const pts = data.map((d, i) => [i * step, h - ((d - min) / span) * (h - 20) - 10]);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none" style={{ height: 180 }}>
      <defs>
        <linearGradient id="act-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.24" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line key={g} x1="0" y1={h * g} x2={w} y2={h * g} stroke="var(--border)" strokeWidth="1" />
      ))}
      <path d={area} fill="url(#act-grad)" />
      <path d={line} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="3.5" fill="var(--accent)" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="7" fill="var(--accent)" fillOpacity="0.2" />
    </svg>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div>
      <div className="text-caption text-tertiary">{label}</div>
      <div
        className={cn(
          "mt-0.5 text-[15px] font-semibold tnum",
          tone === "ok" ? "text-success" : tone === "warn" ? "text-warning" : "text-primary"
        )}
      >
        {value}
      </div>
    </div>
  );
}

/* ── Mood (radar, live) ─────────────────────────────────── */
function MoodCard() {
  const { t } = useI18n();
  const happy = useDrift(0.72, 0.06, 5200);
  const energy = useDrift(0.61, 0.08, 6100);
  const curiosity = useDrift(0.88, 0.04, 4800);
  const axes = ["Happy", "Energy", "Curiosity", "Calm", "Focus", "Trust"];
  const values = [happy, energy, curiosity, 0.68, 0.79, 0.83];
  return (
    <Card className="flex h-full flex-col p-5">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h3 className="text-subtitle text-primary">{t("dash.emotion")}</h3>
          <p className="text-caption text-tertiary">{t("dash.emotion.sub")}</p>
        </div>
        <Badge tone="accent">
          <Activity className="h-3 w-3" /> mood {Math.round(happy * 100)}
        </Badge>
      </div>
      <div className="flex flex-1 items-center justify-center">
        <Radar axes={axes} values={values} size={220} color="var(--accent)" />
      </div>
    </Card>
  );
}

/* ── Health (CPU/RAM/etc) ───────────────────────────────── */
function HealthCard() {
  const { t } = useI18n();
  const cpu = useDrift(0.34, 0.08, 3000);
  const ram = useDrift(0.58, 0.05, 4200);
  return (
    <Card className="h-full p-5">
      <h3 className="text-subtitle text-primary">{t("dash.health")}</h3>
      <p className="mb-4 text-caption text-tertiary">{t("dash.health.sub")}</p>
      <div className="flex items-center justify-around">
        <div className="flex flex-col items-center gap-2">
          <Donut value={cpu} color="var(--accent)" label="CPU" />
          <div className="flex items-center gap-1 text-caption text-tertiary">
            <Cpu className="h-3 w-3" /> CPU
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <Donut value={ram} color="#5e5ce6" label="RAM" />
          <div className="flex items-center gap-1 text-caption text-tertiary">
            <MemoryStick className="h-3 w-3" /> RAM
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <Donut value={0.992} color="var(--success)" label="Uptime" />
          <div className="flex items-center gap-1 text-caption text-tertiary">
            <CheckCircle2 className="h-3 w-3" /> Uptime
          </div>
        </div>
      </div>
      <div className="mt-5 space-y-2 border-t border-border pt-4">
        <HealthRow label="Vector DB · Qdrant" ok />
        <HealthRow label="Redis cache" ok />
        <HealthRow label="Postgres" ok />
        <HealthRow label="MCP gateway" ok />
      </div>
    </Card>
  );
}

function HealthRow({ label, ok }: { label: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[13px]">
      <span className="text-secondary">{label}</span>
      <span className={cn("flex items-center gap-1.5 text-[11px]", ok ? "text-success" : "text-danger")}>
        <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-success" : "bg-danger")} />
        {ok ? "healthy" : "down"}
      </span>
    </div>
  );
}

/* ── Goal ───────────────────────────────────────────────── */
function GoalCard() {
  const { t } = useI18n();
  const tasks = [
    { t: "Query weather · Tokyo", done: true },
    { t: "Draft 7-day itinerary", done: true },
    { t: "Estimate budget", done: false, active: true },
    { t: "Shortlist hotels", done: false },
    { t: "Generate final plan", done: false },
  ];
  const done = tasks.filter((x) => x.done).length;
  return (
    <Card className="h-full p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-subtitle text-primary">{t("dash.goal")}</h3>
          <p className="text-caption text-tertiary">{t("dash.goal.sub")}</p>
        </div>
        <Badge tone="accent">{done}/{tasks.length}</Badge>
      </div>
      <div className="mt-4 space-y-2.5">
        {tasks.map((task) => (
          <div key={task.t} className="flex items-center gap-2.5 text-[13px]">
            <span
              className={cn(
                "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                task.done
                  ? "border-success bg-success/15 text-success"
                  : task.active
                    ? "border-accent text-accent"
                    : "border-border text-tertiary"
              )}
            >
              {task.done ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : task.active ? (
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              ) : null}
            </span>
            <span className={cn(task.done ? "text-tertiary line-through" : task.active ? "text-primary" : "text-secondary")}>
              {task.t}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── Recent events (timeline) ───────────────────────────── */
function EventsCard() {
  const { t } = useI18n();
  const events = [
    { icon: Brain, label: "Reflection completed", meta: "2m ago", tone: "text-accent" },
    { icon: Database, label: "Memory consolidated (+14)", meta: "9m ago", tone: "text-[#64d2ff]" },
    { icon: Users, label: "Trust +0.03 with Banana", meta: "21m ago", tone: "text-success" },
    { icon: Wrench, label: "Tool: github.pr opened", meta: "38m ago", tone: "text-[#ff9f0a]" },
    { icon: Sparkles, label: "Model switched → opus-4.8", meta: "1h ago", tone: "text-[#5e5ce6]" },
  ];
  return (
    <Card className="h-full p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-subtitle text-primary">{t("dash.events")}</h3>
        <button className="flex items-center gap-0.5 text-caption text-tertiary transition-colors hover:text-secondary">
          {t("dash.events.all")} <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
      <div className="relative space-y-4 pl-1">
        <div className="absolute bottom-2 left-[10px] top-2 w-px bg-border" />
        {events.map((e) => {
          const Icon = e.icon;
          return (
            <div key={e.label} className="relative flex items-center gap-3">
              <span className={cn("relative z-10 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-[var(--surface)]", e.tone)}>
                <Icon className="h-3 w-3" />
              </span>
              <div className="flex-1">
                <div className="text-[13px] text-secondary">{e.label}</div>
              </div>
              <span className="text-[11px] text-tertiary tnum">{e.meta}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
