"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Braces, Layers, Wrench, GitBranch } from "lucide-react";
import { useUI } from "@/store/ui";
import { cn } from "@/lib/cn";

const TABS = [
  { id: "json", label: "JSON", icon: Braces },
  { id: "state", label: "State", icon: Layers },
  { id: "tools", label: "Tools", icon: Wrench },
  { id: "trace", label: "Trace", icon: GitBranch },
];

export function Inspector() {
  const { inspectorOpen } = useUI();
  const [tab, setTab] = useState("json");

  return (
    <AnimatePresence initial={false}>
      {inspectorOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 340, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 36 }}
          className="relative z-10 shrink-0 overflow-hidden border-l border-border bg-[var(--surface)]/40 backdrop-blur-[var(--glass-blur)]"
        >
          <div className="flex h-full w-[340px] flex-col">
            <div className="flex items-center gap-1 border-b border-border px-3 py-2.5">
              {TABS.map((t) => {
                const Icon = t.icon;
                const active = tab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] transition-colors duration-200 ease-spring",
                      active
                        ? "bg-[var(--surface-2)] text-primary"
                        : "text-tertiary hover:text-secondary"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between px-4 pb-1 pt-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-tertiary">
                Inspector · {tab}
              </span>
              <span className="rounded-full border border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 px-2 py-0.5 text-[10px] text-warning">
                [demo]
              </span>
            </div>

            <div className="flex-1 overflow-y-auto px-4 pb-4">
              {tab === "json" ? <JsonView /> : <Placeholder label={tab} />}
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function JsonView() {
  return (
    <pre className="mt-2 whitespace-pre-wrap rounded-[14px] border border-border bg-[var(--bg)]/60 p-3 font-mono text-[12px] leading-relaxed text-secondary">
      <span className="text-tertiary">{"{"}</span>
      {"\n  "}
      <K>state</K>: <S>&quot;thinking&quot;</S>,{"\n  "}
      <K>attention</K>: <S>&quot;user.goal.trip_japan&quot;</S>,{"\n  "}
      <K>emotion</K>: {"{"}
      {"\n    "}
      <K>mood</K>: <N>0.72</N>, <K>energy</K>: <N>0.61</N>,{"\n    "}
      <K>curiosity</K>: <N>0.88</N>{"\n  "}
      {"}"},{"\n  "}
      <K>active_memory</K>: <N>7</N>,{"\n  "}
      <K>model</K>: <S>&quot;claude-opus-4-8&quot;</S>,{"\n  "}
      <K>latency_ms</K>: <N>412</N>
      {"\n"}
      <span className="text-tertiary">{"}"}</span>
    </pre>
  );
}

const K = ({ children }: { children: React.ReactNode }) => (
  <span className="text-[#5e9eff]">{children}</span>
);
const S = ({ children }: { children: React.ReactNode }) => (
  <span className="text-success">{children}</span>
);
const N = ({ children }: { children: React.ReactNode }) => (
  <span className="text-warning">{children}</span>
);

function Placeholder({ label }: { label: string }) {
  return (
    <div className="mt-6 flex flex-col items-center gap-2 text-center text-tertiary">
      <div className="h-10 w-10 rounded-full border border-dashed border-border" />
      <p className="text-[12px]">
        {label} stream will surface here as Sunday runs.
      </p>
    </div>
  );
}
