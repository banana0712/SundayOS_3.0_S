"use client";

import { useEffect, lazy, Suspense } from "react";
import { UIProvider, useUI } from "@/store/ui";
import { I18nProvider } from "@/i18n";
import { ensureApiKey } from "@/lib/api-key";
import { Sidebar } from "./sidebar";
import { TopBar } from "./topbar";
import { Inspector } from "./inspector";
import { ConsoleDock } from "./console-dock";
import { CommandPalette } from "./command-palette";
import { NAV } from "@/config/nav";
import { AnimatePresence, motion } from "framer-motion";

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

export function AppShell({ children }: { children: React.ReactNode }) {
  // children (route content) is unused for the SPA-style view switch,
  // kept so the root layout composes normally.
  void children;
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
