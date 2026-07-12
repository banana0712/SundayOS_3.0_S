"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  Database,
  HeartPulse,
  Bot,
  RefreshCw,
  Waypoints,
  Eye,
  Target,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { Card, Badge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";

type Node = {
  id: string;
  label: string;
  icon: LucideIcon;
  angle: number; // degrees
  color: string;
  state: string;
  load: number; // 0..1
  detail: string;
};

// Cognitive Core + Memory + Tool Runtime — per ARCHITECTURE §2/§3
const NODES: Node[] = [
  { id: "attention", label: "Attention", icon: Eye, angle: -90, color: "#0a84ff", state: "focusing", load: 0.88, detail: "Ranking salient signals. Top: user.goal.trip_japan." },
  { id: "planner", label: "Planner", icon: Bot, angle: -45, color: "#5e5ce6", state: "planning", load: 0.74, detail: "Decomposed goal into 5 tasks. Executing task 3/5." },
  { id: "memory", label: "Memory", icon: Database, angle: 0, color: "#64d2ff", state: "retrieving", load: 0.52, detail: "7 episodic + 3 semantic in working set." },
  { id: "reflection", label: "Reflection", icon: RefreshCw, angle: 45, color: "#30d158", state: "idle", load: 0.18, detail: "Last reflection 2m ago → experience updated." },
  { id: "goal", label: "Goal", icon: Target, angle: 90, color: "#ff9f0a", state: "tracking", load: 0.44, detail: "Long-term: help user grow. Short-term: plan trip." },
  { id: "relationship", label: "Relationship", icon: Waypoints, angle: 135, color: "#bf5af2", state: "stable", load: 0.36, detail: "Trust 0.83 · Friendship 0.79 with Banana." },
  { id: "emotion", label: "Emotion", icon: HeartPulse, angle: 180, color: "#ff453a", state: "warm", load: 0.61, detail: "Mood 0.72 · Curiosity 0.88 · Energy 0.61." },
  { id: "tools", label: "Tool Runtime", icon: Wrench, angle: 225, color: "#ffd60a", state: "ready", load: 0.29, detail: "11 tools online. weather · browser · github …" },
];

const SIZE = 560;
const CENTER = SIZE / 2;
const ORBIT = 208;

function nodePos(angleDeg: number) {
  const a = (angleDeg * Math.PI) / 180;
  return { x: CENTER + Math.cos(a) * ORBIT, y: CENTER + Math.sin(a) * ORBIT };
}

export function BrainView() {
  const { t } = useI18n();
  const [selected, setSelected] = useState<Node>(NODES[0]);
  const [pulse, setPulse] = useState<string | null>(null);

  // Randomly fire a signal along an edge, to feel alive.
  useEffect(() => {
    const id = setInterval(() => {
      setPulse(NODES[Math.floor(Math.random() * NODES.length)].id);
      setTimeout(() => setPulse(null), 900);
    }, 1600);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto grid max-w-[1400px] grid-cols-1 gap-4 px-6 py-6 xl:grid-cols-[1fr_340px]">
      {/* Canvas */}
      <Card className="relative overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div>
            <h1 className="text-subtitle text-primary">{t("brain.title")}</h1>
            <p className="text-caption text-tertiary">{t("brain.subtitle")}</p>
          </div>
          <Badge tone="ok">
            <span className="h-1.5 w-1.5 rounded-full bg-success" /> {t("brain.thinking")}
          </Badge>
        </div>

        <div className="relative flex items-center justify-center py-6">
          <BrainGraph selected={selected} onSelect={setSelected} pulse={pulse} />
        </div>
      </Card>

      {/* Inspector */}
      <div className="flex flex-col gap-4">
        <NodeDetail node={selected} />
        <ModuleList selected={selected} onSelect={setSelected} />
      </div>
    </div>
  );
}

function BrainGraph({
  selected,
  onSelect,
  pulse,
}: {
  selected: Node;
  onSelect: (n: Node) => void;
  pulse: string | null;
}) {
  const positions = useMemo(() => NODES.map((n) => ({ n, ...nodePos(n.angle) })), []);
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[560px]">
      <defs>
        <radialGradient id="core-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#0a84ff" stopOpacity="0.55" />
          <stop offset="45%" stopColor="#5e5ce6" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#5e5ce6" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(255,255,255,0.02)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0.14)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0.02)" />
        </linearGradient>
      </defs>

      {/* Orbit rings */}
      {[ORBIT, ORBIT - 60, ORBIT + 40].map((r) => (
        <circle key={r} cx={CENTER} cy={CENTER} r={r} fill="none" stroke="var(--border)" strokeWidth="1" strokeDasharray="2 6" />
      ))}

      {/* Edges core → node */}
      {positions.map(({ n, x, y }) => {
        const active = selected.id === n.id || pulse === n.id;
        return (
          <g key={`edge-${n.id}`}>
            <line
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              stroke={active ? n.color : "url(#edge)"}
              strokeWidth={active ? 1.6 : 1}
              strokeOpacity={active ? 0.8 : 0.5}
            />
            {/* animated signal packet */}
            {pulse === n.id && (
              <circle r="3.2" fill={n.color}>
                <animateMotion dur="0.9s" repeatCount="1" path={`M${CENTER},${CENTER} L${x},${y}`} />
              </circle>
            )}
            {/* flowing dashes on selected edge */}
            {selected.id === n.id && (
              <line
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                stroke={n.color}
                strokeWidth="1.4"
                strokeDasharray="1 10"
                className="animate-dash-flow"
                strokeLinecap="round"
              />
            )}
          </g>
        );
      })}

      {/* Core */}
      <circle cx={CENTER} cy={CENTER} r="150" fill="url(#core-glow)" className="animate-breathe" style={{ transformOrigin: "center" }} />
      <circle cx={CENTER} cy={CENTER} r="52" fill="var(--surface)" stroke="var(--border-strong)" strokeWidth="1" />
      <circle cx={CENTER} cy={CENTER} r="52" fill="none" stroke="#0a84ff" strokeWidth="1.5" strokeOpacity="0.5">
        <animate attributeName="r" values="52;58;52" dur="4s" repeatCount="indefinite" />
        <animate attributeName="stroke-opacity" values="0.5;0.1;0.5" dur="4s" repeatCount="indefinite" />
      </circle>
      <text x={CENTER} y={CENTER - 4} textAnchor="middle" className="fill-[color:var(--text-primary)] text-[15px] font-semibold">
        Sunday
      </text>
      <text x={CENTER} y={CENTER + 13} textAnchor="middle" className="fill-[color:var(--text-tertiary)] text-[10px]">
        core · v3.0
      </text>

      {/* Nodes */}
      {positions.map(({ n, x, y }) => {
        const Icon = n.icon;
        const isSel = selected.id === n.id;
        return (
          <g
            key={n.id}
            transform={`translate(${x},${y})`}
            onClick={() => onSelect(n)}
            className="cursor-pointer"
          >
            <circle r="30" fill="var(--surface)" stroke={isSel ? n.color : "var(--border)"} strokeWidth={isSel ? 2 : 1} />
            {isSel && <circle r="30" fill={n.color} fillOpacity="0.12" />}
            {/* load ring */}
            <circle
              r="26"
              fill="none"
              stroke={n.color}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 26}
              strokeDashoffset={2 * Math.PI * 26 * (1 - n.load)}
              transform="rotate(-90)"
              opacity="0.85"
            />
            <foreignObject x="-11" y="-11" width="22" height="22">
              <div className="flex h-full w-full items-center justify-center" style={{ color: n.color }}>
                <Icon className="h-[18px] w-[18px]" />
              </div>
            </foreignObject>
            <text y="46" textAnchor="middle" className={cn("text-[11px]", isSel ? "fill-[color:var(--text-primary)]" : "fill-[color:var(--text-secondary)]")}>
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function NodeDetail({ node }: { node: Node }) {
  const Icon = node.icon;
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-[12px] border border-border" style={{ color: node.color }}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="text-subtitle text-primary">{node.label}</div>
          <div className="text-caption text-tertiary capitalize">{node.state}</div>
        </div>
        <span className="ml-auto text-[13px] font-semibold tnum" style={{ color: node.color }}>
          {Math.round(node.load * 100)}%
        </span>
      </div>
      <p className="mt-4 text-[13px] leading-relaxed text-secondary">{node.detail}</p>
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-caption text-tertiary">
          <span>Load</span>
          <span className="tnum">{Math.round(node.load * 100)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
          <motion.div
            className="h-full rounded-full"
            style={{ background: node.color }}
            initial={{ width: 0 }}
            animate={{ width: `${node.load * 100}%` }}
            transition={{ type: "spring", stiffness: 200, damping: 30 }}
          />
        </div>
      </div>
    </Card>
  );
}

function ModuleList({ selected, onSelect }: { selected: Node; onSelect: (n: Node) => void }) {
  return (
    <Card className="p-3">
      <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-tertiary">
        Modules
      </div>
      <div className="space-y-0.5">
        {NODES.map((n) => {
          const Icon = n.icon;
          const isSel = selected.id === n.id;
          return (
            <button
              key={n.id}
              onClick={() => onSelect(n)}
              className={cn(
                "flex w-full items-center gap-3 rounded-[10px] px-2 py-2 text-left transition-colors",
                isSel ? "bg-[var(--surface-2)]" : "hover:bg-[var(--surface-2)]"
              )}
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-border" style={{ color: n.color }}>
                <Icon className="h-4 w-4" />
              </span>
              <span className="text-[13px] text-secondary">{n.label}</span>
              <span className="ml-auto flex items-center gap-2">
                <span className="text-[11px] text-tertiary tnum">{Math.round(n.load * 100)}%</span>
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: n.color }} />
              </span>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
