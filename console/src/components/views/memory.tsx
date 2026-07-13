"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Database, Search, RefreshCw, Sparkles, Trash2,
  Circle, Brain, type LucideIcon,
} from "lucide-react";
import { Card, Badge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";
import { apiFetch } from "@/lib/api-key";

type MemoryHit = {
  id: string;
  content: string;
  type: string;
  score: number;
  components?: { recency: number; importance: number; relevance: number };
};

type MemoryStats = {
  total_nodes: number;
  by_type: Record<string, number>;
  embedder: string;
  db_type: string;
};

type Reflection = {
  id: string;
  content: string;
  evidence_ids: string[];
  importance: number;
  created_at: string;
};

const TYPE_ICONS: Record<string, LucideIcon> = {
  episodic: Database,
  semantic: Brain,
  procedural: RefreshCw,
  reflection: Sparkles,
  experience: Sparkles,
};
const TYPE_COLORS: Record<string, string> = {
  episodic: "var(--accent)",
  semantic: "#64d2ff",
  procedural: "var(--warning)",
  reflection: "#bf5af2",
  experience: "var(--success)",
};

export function MemoryView() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemoryHit[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [selected, setSelected] = useState<MemoryHit | null>(null);
  const [searching, setSearching] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const r = await apiFetch("/api/memory/stats");
      if (r.ok) setStats(await r.json());
    } catch { /* ignore */ }
  }, []);

  const fetchReflections = useCallback(async () => {
    try {
      const r = await apiFetch("/api/memory/reflections?limit=10");
      if (r.ok) {
        const d = await r.json();
        setReflections(d.reflections || []);
      }
    } catch { /* ignore */ }
  }, []);

  const doSearch = useCallback(async (q: string) => {
    setSearching(true);
    try {
      const r = await apiFetch("/api/memory/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({query: q || "*", k: 20 }),
      });
      if (r.ok) {
        const d = await r.json();
        setResults(d.results || []);
      }
    } catch { /* ignore */ }
    finally { setSearching(false); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchReflections();
    doSearch("");
  }, [fetchStats, fetchReflections, doSearch]);

  const doReflect = async () => {
    try {
      await apiFetch("/api/memory/reflect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({force: true }),
      });
      fetchReflections();
      fetchStats();
    } catch { /* ignore */ }
  };

  const doConsolidate = async () => {
    try {
      await apiFetch("/api/memory/consolidate", { method: "POST" });
      fetchStats();
    } catch { /* ignore */ }
  };

  return (
    <div className="mx-auto flex h-full max-w-[1400px] gap-4 px-4 py-4">
      {/* left panel: search + list */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* header */}
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-gradient-to-br from-[#64d2ff] to-[#bf5af2]">
            <Database className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-subtitle text-primary">{t("nav.memory")}</h1>
            <p className="text-caption text-tertiary">
              {stats ? `${stats.total_nodes} nodes · ${stats.embedder} embedder · ${stats.db_type}` : "loading..."}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={doReflect}
              className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-[12px] text-secondary transition-colors hover:border-[color:#bf5af2] hover:text-[#bf5af2]"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Reflect
            </button>
            <button
              onClick={doConsolidate}
              className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-[12px] text-secondary transition-colors hover:border-border-strong hover:text-primary"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Consolidate
            </button>
          </div>
        </div>

        {/* search bar */}
        <div className="mb-3 flex items-center gap-2 rounded-[12px] border border-border bg-[var(--surface)] px-3 py-2 transition-colors focus-within:border-border-strong">
          <Search className="h-4 w-4 text-tertiary" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") doSearch(query); }}
            placeholder="搜索记忆... / Search memories..."
            className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
          />
        </div>

        {/* stats row */}
        {stats && (
          <div className="mb-3 flex gap-3">
            {Object.entries(stats.by_type || {}).map(([type, count]) => {
              const Icon = TYPE_ICONS[type] || Circle;
              return (
                <div key={type} className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-secondary">
                  <Icon className="h-3 w-3" style={{ color: TYPE_COLORS[type] || "var(--ter)" }} />
                  {type}: <span className="font-medium text-primary">{count}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* memory list */}
        <div className="flex-1 space-y-1 overflow-y-auto">
          {searching && (
            <div className="py-12 text-center text-caption text-tertiary">Searching...</div>
          )}
          {results.map((hit) => {
            const Icon = TYPE_ICONS[hit.type] || Circle;
            const color = TYPE_COLORS[hit.type] || "var(--ter)";
            const isSel = selected?.id === hit.id;
            return (
              <motion.button
                key={hit.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => setSelected(hit)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-[12px] px-3 py-2.5 text-left transition-colors",
                  isSel ? "bg-[var(--surface-2)] border border-border" : "hover:bg-[var(--surface-2)]"
                )}
              >
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border" style={{ color }}>
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] text-primary">{hit.content}</p>
                  <div className="mt-0.5 flex items-center gap-2 text-[10px] text-tertiary">
                    <span className="rounded-full border border-border px-1.5 py-0.5 capitalize">{hit.type}</span>
                    {hit.components && (
                      <>
                        <span>imp: {Math.round(hit.components.importance * 10)}/10</span>
                        <span>score: {hit.score.toFixed(2)}</span>
                      </>
                    )}
                  </div>
                </div>
              </motion.button>
            );
          })}
          {!searching && results.length === 0 && (
            <div className="py-12 text-center text-caption text-tertiary">
              No memories found. Chat with Sunday to create memories!
            </div>
          )}
        </div>

        {/* reflections footer */}
        {reflections.length > 0 && (
          <div className="mt-3 border-t border-border pt-3">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-[#bf5af2]" />
              <span className="text-[12px] font-medium text-secondary">Reflections ({reflections.length})</span>
            </div>
            <div className="space-y-2 max-h-[160px] overflow-y-auto">
              {reflections.slice(0, 5).map((r) => (
                <div key={r.id} className="rounded-[10px] border border-border bg-[var(--surface)] p-3">
                  <p className="text-[12px] leading-relaxed text-secondary">{r.content}</p>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-tertiary">
                    <span>{r.evidence_ids?.length || 0} sources</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* right detail panel */}
      {selected && (
        <Card className="flex w-[320px] shrink-0 flex-col p-4">
          <div className="mb-3 flex items-center gap-2">
            {(() => {
              const Icon = TYPE_ICONS[selected.type] || Circle;
              return <Icon className="h-4 w-4" style={{ color: TYPE_COLORS[selected.type] }} />;
            })()}
            <span className="text-caption font-medium text-secondary capitalize">{selected.type}</span>
            <span className="ml-auto text-[10px] text-tertiary">{selected.id}</span>
          </div>
          <p className="flex-1 text-[14px] leading-relaxed text-primary">{selected.content}</p>
          {selected.components && (
            <div className="mt-4 space-y-2">
              <DetailBar label="Recency" value={selected.components.recency} color="var(--accent)" />
              <DetailBar label="Importance" value={selected.components.importance} color="var(--success)" />
              <DetailBar label="Relevance" value={selected.components.relevance} color="#64d2ff" />
              <div className="flex items-center justify-between pt-2 text-[12px]">
                <span className="text-tertiary">Composite Score</span>
                <span className="font-semibold text-primary">{selected.score.toFixed(3)}</span>
              </div>
            </div>
          )}
          <p className="mt-3 text-[10px] text-tertiary">
            Memory ID: {selected.id}
          </p>
        </Card>
      )}
    </div>
  );
}

function DetailBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-tertiary">{label}</span>
        <span className="font-medium text-secondary tnum">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
        <div className="h-full rounded-full transition-all" style={{ width: `${value * 100}%`, background: color }} />
      </div>
    </div>
  );
}
