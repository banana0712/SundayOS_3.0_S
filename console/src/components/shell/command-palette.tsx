"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Search, CornerDownLeft } from "lucide-react";
import { NAV } from "@/config/nav";
import { useUI } from "@/store/ui";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen, setView } = useUI();
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return NAV;
    return NAV.filter((n) => {
      const label = t(`nav.${n.slug}`).toLowerCase();
      return label.includes(query) || n.label.toLowerCase().includes(query) ||
        n.group.toLowerCase().includes(query);
    });
  }, [q, t]);

  useEffect(() => {
    if (paletteOpen) {
      setQ("");
      setActive(0);
    }
  }, [paletteOpen]);

  useEffect(() => {
    if (!paletteOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((a) => Math.min(a + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = results[active];
        if (item) setView(item.slug);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [paletteOpen, results, active, setView]);

  return (
    <AnimatePresence>
      {paletteOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[16vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setPaletteOpen(false)}
          />
          <motion.div
            initial={{ scale: 0.97, y: 8, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.98, y: 4, opacity: 0 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            className="glass relative w-full max-w-[560px] overflow-hidden rounded-[20px] shadow-glow"
          >
            <div className="flex items-center gap-3 border-b border-border px-4 py-3.5">
              <Search className="h-[18px] w-[18px] text-tertiary" />
              <input
                autoFocus
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setActive(0);
                }}
                placeholder={t("search.placeholder")}
                className="w-full bg-transparent text-[15px] text-primary outline-none placeholder:text-tertiary"
              />
              <kbd className="rounded-md border border-border px-1.5 py-0.5 text-[10px] text-tertiary">
                ESC
              </kbd>
            </div>

            <div className="max-h-[46vh] overflow-y-auto p-2">
              {results.length === 0 && (
                <div className="px-3 py-8 text-center text-[13px] text-tertiary">
                  No results for “{q}”
                </div>
              )}
              {results.map((item, i) => {
                const Icon = item.icon;
                const isActive = i === active;
                return (
                  <button
                    key={item.slug || "dashboard"}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => setView(item.slug)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-[12px] px-3 py-2.5 text-left transition-colors",
                      isActive ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]"
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg border border-border",
                        isActive ? "text-accent" : "text-tertiary"
                      )}
                    >
                      <Icon className="h-[18px] w-[18px]" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-[14px] text-primary">{t(`nav.${item.slug}`)}</div>
                      <div className="text-[11px] text-tertiary">{t(`group.${item.group}`)}</div>
                    </div>
                    {isActive && (
                      <CornerDownLeft className="ml-auto h-4 w-4 text-tertiary" />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-4 border-t border-border px-4 py-2.5 text-[11px] text-tertiary">
              <Hint keys="↑↓" label="navigate" />
              <Hint keys="↵" label="open" />
              <Hint keys="esc" label="close" />
              <span className="ml-auto">Sunday OS Console</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Hint({ keys, label }: { keys: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px]">{keys}</kbd>
      {label}
    </span>
  );
}
