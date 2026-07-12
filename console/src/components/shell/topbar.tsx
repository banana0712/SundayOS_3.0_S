"use client";

import { PanelRight, TerminalSquare, Sun, Moon, Bell, ChevronRight, Languages } from "lucide-react";
import { useUI, useNow } from "@/store/ui";
import { useI18n } from "@/i18n";
import { NAV } from "@/config/nav";
import { cn } from "@/lib/cn";

export function TopBar() {
  const { view, inspectorOpen, toggleInspector, consoleOpen, toggleConsole, theme, toggleTheme } =
    useUI();
  const { t, lang, toggleLang } = useI18n();
  const now = useNow();
  const current = NAV.find((n) => n.slug === view);

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[13px]">
        <span className="text-tertiary">Sunday OS</span>
        <ChevronRight className="h-3.5 w-3.5 text-tertiary" />
        <span className="font-medium text-primary">{t(`nav.${current?.slug ?? ""}`)}</span>
      </div>

      <div className="ml-auto flex items-center gap-1">
        <span className="mr-3 hidden text-[12px] tabular-nums text-tertiary sm:inline tnum">
          {now
            ? now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
            : "--:--:--"}
        </span>

        {/* Language toggle — 中 / EN */}
        <button
          onClick={toggleLang}
          aria-label={t("top.lang")}
          className="flex h-9 items-center gap-1.5 rounded-[10px] px-2.5 text-secondary transition-colors duration-200 ease-spring hover:bg-[var(--surface-2)] hover:text-primary"
        >
          <Languages className="h-[18px] w-[18px]" />
          <span className="text-[12px] font-medium">{lang === "zh" ? "中" : "EN"}</span>
        </button>

        <IconBtn label={t("top.notifications")}>
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-accent" />
        </IconBtn>

        <IconBtn label={t("top.theme")} onClick={toggleTheme}>
          {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </IconBtn>

        <IconBtn label={t("top.console")} active={consoleOpen} onClick={toggleConsole}>
          <TerminalSquare className="h-[18px] w-[18px]" />
        </IconBtn>

        <IconBtn label={t("top.inspector")} active={inspectorOpen} onClick={toggleInspector}>
          <PanelRight className="h-[18px] w-[18px]" />
        </IconBtn>
      </div>
    </header>
  );
}

function IconBtn({
  children,
  onClick,
  active,
  label,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
  label: string;
}) {
  return (
    <button
      aria-label={label}
      onClick={onClick}
      className={cn(
        "relative flex h-9 w-9 items-center justify-center rounded-[10px] text-secondary transition-colors duration-200 ease-spring hover:bg-[var(--surface-2)] hover:text-primary",
        active && "bg-[var(--surface-2)] text-primary"
      )}
    >
      {children}
    </button>
  );
}
