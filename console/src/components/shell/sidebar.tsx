"use client";

import { motion } from "framer-motion";
import { Command, Circle } from "lucide-react";
import { NAV, NAV_GROUPS } from "@/config/nav";
import { useUI } from "@/store/ui";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/cn";

export function Sidebar() {
  const { view, setView, setPaletteOpen } = useUI();
  const { t } = useI18n();

  return (
    <aside className="relative z-20 flex w-[280px] shrink-0 flex-col border-r border-border bg-[var(--surface)]/40 backdrop-blur-[var(--glass-blur)]">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 pb-4 pt-5">
        <SundayMark />
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight">Sunday OS</div>
          <div className="text-caption text-tertiary">{t("brand.subtitle")}</div>
        </div>
        <div className="ml-auto flex items-center gap-1.5 rounded-full border border-border px-2 py-1">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
          </span>
          <span className="text-[10px] font-medium text-secondary">{t("status.online")}</span>
        </div>
      </div>

      {/* Command search */}
      <button
        onClick={() => setPaletteOpen(true)}
        className="mx-4 mb-3 flex items-center gap-2 rounded-[10px] border border-border bg-[var(--surface-2)] px-3 py-2 text-left text-secondary transition-colors duration-200 ease-spring hover:border-border-strong"
      >
        <Command className="h-3.5 w-3.5" />
        <span className="text-[13px]">{t("search.placeholder")}</span>
        <kbd className="ml-auto rounded-md border border-border px-1.5 py-0.5 text-[10px] text-tertiary">
          ⌘K
        </kbd>
      </button>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {NAV_GROUPS.map((group) => (
          <div key={group} className="mb-4">
            <div className="px-3 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-tertiary">
              {t(`group.${group}`)}
            </div>
            {NAV.filter((n) => n.group === group).map((item) => {
              const active = view === item.slug;
              const Icon = item.icon;
              return (
                <button
                  key={item.slug || "dashboard"}
                  onClick={() => setView(item.slug)}
                  className={cn(
                    "group relative flex w-full items-center gap-3 rounded-[10px] px-3 py-2 text-[14px] transition-colors duration-200 ease-spring",
                    active
                      ? "text-primary"
                      : "text-secondary hover:bg-[var(--surface-2)] hover:text-primary"
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-[10px] border border-[color:var(--accent)]/30 bg-[var(--accent-soft)]"
                      transition={{ type: "spring", stiffness: 400, damping: 34 }}
                    />
                  )}
                  {active && (
                    <span className="absolute left-0 top-1/2 h-4 -translate-y-1/2 rounded-full bg-accent w-[2.5px]" />
                  )}
                  <Icon
                    className={cn(
                      "relative h-[18px] w-[18px] shrink-0 transition-colors",
                      active ? "text-accent" : "text-tertiary group-hover:text-secondary"
                    )}
                  />
                  <span className="relative">{t(`nav.${item.slug}`)}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer — model + user */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-[10px] px-2 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#0a84ff] to-[#5e5ce6] text-[13px] font-semibold text-white">
            B
          </div>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-[13px] font-medium">Banana</div>
            <div className="flex items-center gap-1 text-[11px] text-tertiary">
              <Circle className="h-2 w-2 fill-success text-success" />
              claude-opus-4-8
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function SundayMark() {
  return (
    <div className="relative flex h-9 w-9 items-center justify-center">
      <div className="absolute inset-0 rounded-[11px] bg-gradient-to-br from-[#0a84ff] via-[#5e5ce6] to-[#30d158] opacity-90" />
      <div className="absolute inset-[1.5px] rounded-[9.5px] bg-[var(--surface)]" />
      <div className="relative h-3 w-3 rounded-full bg-gradient-to-br from-[#0a84ff] to-[#5e5ce6] animate-breathe" />
    </div>
  );
}
