"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Zap, Clock, Database, Radio } from "lucide-react";
import { useUI } from "@/store/ui";
import { cn } from "@/lib/cn";

type Line = {
  id: number;
  t: string;
  level: "info" | "ok" | "warn" | "err";
  tag: string;
  msg: string;
};

const SEED: Omit<Line, "id" | "t">[] = [
  { level: "info", tag: "attention", msg: "focus → user.goal.trip_japan (weight 0.88)" },
  { level: "ok", tag: "memory", msg: "retrieved 7 episodic + 3 semantic in 41ms" },
  { level: "info", tag: "planner", msg: "decompose goal → 5 tasks" },
  { level: "ok", tag: "model", msg: "claude-opus-4-8 stream · 412ms · 1,204 tok" },
  { level: "info", tag: "tool", msg: "weather.get(tokyo) → 22°C, clear" },
  { level: "warn", tag: "model", msg: "fallback armed: gpt → claude (rate 0.02)" },
  { level: "ok", tag: "reflection", msg: "task#3 success · updated experience memory" },
  { level: "info", tag: "emotion", msg: "curiosity +0.04 (novel destination)" },
];

export function ConsoleDock() {
  const { consoleOpen, toggleConsole } = useUI();
  const [lines, setLines] = useState<Line[]>([]);
  const idRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const push = () => {
      const s = SEED[idRef.current % SEED.length];
      const d = new Date();
      const t = d.toLocaleTimeString("en-GB", { hour12: false }) + "." +
        String(d.getMilliseconds()).padStart(3, "0");
      const nextId = idRef.current++;
      setLines((prev) => {
        const next = [...prev, { ...s, id: nextId, t }];
        return next.slice(-60);
      });
    };
    push();
    const id = setInterval(push, 1800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <AnimatePresence initial={false}>
      {consoleOpen && (
        <motion.div
          initial={{ height: 0 }}
          animate={{ height: 208 }}
          exit={{ height: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 38 }}
          className="shrink-0 overflow-hidden border-t border-border bg-[var(--bg)]/80 backdrop-blur-[var(--glass-blur)]"
        >
          <div className="flex h-[208px] flex-col">
            {/* Console header */}
            <div className="flex items-center gap-4 border-b border-border px-4 py-2">
              <div className="flex items-center gap-2 text-[12px] font-semibold">
                <Radio className="h-3.5 w-3.5 text-accent" />
                Console
              </div>
              <span className="rounded-full border border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 px-1.5 py-0.5 text-[9px] text-warning">
                demo
              </span>
              <Stat icon={Zap} label="Token/s" value="312" />
              <Stat icon={Clock} label="Latency" value="412ms" tone="ok" />
              <Stat icon={Database} label="Mem writes" value="18" />
              <div className="ml-auto flex items-center gap-2">
                <span className="rounded-full border border-[color:var(--success)]/30 bg-[color:var(--success)]/10 px-2 py-0.5 text-[10px] font-medium text-success">
                  streaming
                </span>
                <button
                  onClick={toggleConsole}
                  aria-label="Collapse console"
                  className="flex h-6 w-6 items-center justify-center rounded-md text-tertiary transition-colors hover:bg-[var(--surface-2)] hover:text-primary"
                >
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Log stream */}
            <div className="flex-1 overflow-y-auto px-4 py-2 font-mono text-[12px] leading-relaxed">
              {lines.map((l) => (
                <div key={l.id} className="flex gap-3 py-0.5 animate-fade-up">
                  <span className="shrink-0 text-tertiary tnum">{l.t}</span>
                  <span className={cn("shrink-0 font-medium", levelColor(l.level))}>
                    {l.level.toUpperCase().padEnd(4)}
                  </span>
                  <span className="shrink-0 text-[#5e9eff]">[{l.tag}]</span>
                  <span className="text-secondary">{l.msg}</span>
                </div>
              ))}
              <div ref={endRef} />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function levelColor(l: Line["level"]) {
  return {
    info: "text-tertiary",
    ok: "text-success",
    warn: "text-warning",
    err: "text-danger",
  }[l];
}

function Stat({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone?: "ok";
}) {
  return (
    <div className="hidden items-center gap-1.5 text-[11px] text-tertiary md:flex">
      <Icon className="h-3.5 w-3.5" />
      {label}
      <span className={cn("font-medium tnum", tone === "ok" ? "text-success" : "text-secondary")}>
        {value}
      </span>
    </div>
  );
}
