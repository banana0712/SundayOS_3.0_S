"use client";

import { useEffect, lazy, Suspense, useState } from "react";
import { UIProvider, useUI, useIsMobile } from "@/store/ui";
import { I18nProvider } from "@/i18n";
import { ensureApiKey } from "@/lib/api-key";
import { Sidebar } from "./sidebar";
import { TopBar } from "./topbar";
import { Inspector } from "./inspector";
import { ConsoleDock } from "./console-dock";
import { CommandPalette } from "./command-palette";
import { NAV } from "@/config/nav";
import { AnimatePresence, motion } from "framer-motion";
import { PanelLeft, X } from "lucide-react";

// Lazy-load view components — each becomes a separate JS chunk.
// Initial bundle drops from ~105KB to ~30KB (70% reduction).
const ChatView = lazy(() => import("@/components/views/chat").then(m => ({ default: m.ChatView })));
const DashboardView = lazy(() => import("@/components/views/dashboard").then(m => ({ default: m.DashboardView })));
const BrainView = lazy(() => import("@/components/views/brain").then(m => ({ default: m.BrainView })));
const MemoryView = lazy(() => import("@/components/views/memory").then(m => ({ default: m.MemoryView })));
const ComingSoon = lazy(() => import("@/components/views/coming-soon").then(m => ({ default: m.ComingSoon })));

function ViewFallback() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex items-center gap-1 text-tertiary">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" style={{ animationDelay: "0.15s" }} />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" style={{ animationDelay: "0.3s" }} />
      </div>
    </div>
  );
}

function ViewRouter() {
  const { view } = useUI();
  let content: React.ReactNode;
  if (view === "") content = <ChatView />;
  else if (view === "dashboard") content = <DashboardView />;
  else if (view === "brain") content = <BrainView />;
  else if (view === "memory") content = <MemoryView />;
  else {
    const item = NAV.find((n) => n.slug === view);
    content = <ComingSoon title={item?.label ?? view} />;
  }
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={view || "dashboard"}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
        className="h-full"
      >
        {content}
      </motion.div>
    </AnimatePresence>
  );
}

function KeyPrompt() {
  useEffect(() => {
    const timer = setTimeout(() => ensureApiKey(), 500);
    return () => clearTimeout(timer);
  }, []);
  return null;
}

function MobileShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="relative z-10 flex h-[100dvh] w-screen flex-col overflow-hidden bg-bg">
      {/* Mobile top bar */}
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3"
              style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex h-9 w-9 items-center justify-center rounded-[10px] text-secondary transition-colors hover:bg-[var(--surface-2)]"
        >
          <PanelLeft className="h-5 w-5" />
        </button>
        <span className="text-[14px] font-semibold text-primary">Sunday OS</span>
        <span className="ml-auto text-[11px] text-tertiary">Console</span>
      </header>

      {/* Off-canvas sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-20" onClick={closeSidebar}>
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          {/* Sidebar panel */}
          <div className="absolute left-0 top-0 bottom-0 w-[280px] animate-fade-up"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex h-12 items-center justify-between border-b border-border px-3"
                 style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
              <span className="text-[13px] font-semibold text-primary">Menu</span>
              <button onClick={closeSidebar}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-tertiary hover:text-primary">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="h-full overflow-y-auto bg-[var(--surface)]/95 backdrop-blur-xl"
                 style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
              <Sidebar />
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="flex-1 overflow-y-auto"
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
        <Suspense fallback={<ViewFallback />}>
          <ViewRouter />
        </Suspense>
      </main>
      <CommandPalette />
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  void children;
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <I18nProvider>
      <UIProvider>
        <KeyPrompt />
        <MobileShell />
      </UIProvider>
      </I18nProvider>
    );
  }

  return (
    <I18nProvider>
    <UIProvider>
      <KeyPrompt />
      <div className="relative z-10 flex h-screen w-screen overflow-hidden">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <div className="flex min-h-0 flex-1">
            <main className="min-w-0 flex-1 overflow-y-auto">
              <Suspense fallback={<ViewFallback />}>
                <ViewRouter />
              </Suspense>
            </main>
            <Inspector />
          </div>
          <ConsoleDock />
        </div>
      </div>
      <CommandPalette />
    </UIProvider>
    </I18nProvider>
  );
}
