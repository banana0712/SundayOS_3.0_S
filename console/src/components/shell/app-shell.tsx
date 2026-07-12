"use client";

import { UIProvider, useUI } from "@/store/ui";
import { I18nProvider } from "@/i18n";
import { Sidebar } from "./sidebar";
import { TopBar } from "./topbar";
import { Inspector } from "./inspector";
import { ConsoleDock } from "./console-dock";
import { CommandPalette } from "./command-palette";
import { ChatView } from "@/components/views/chat";
import { DashboardView } from "@/components/views/dashboard";
import { BrainView } from "@/components/views/brain";
import { ComingSoon } from "@/components/views/coming-soon";
import { NAV } from "@/config/nav";
import { AnimatePresence, motion } from "framer-motion";

function ViewRouter() {
  const { view } = useUI();
  let content: React.ReactNode;
  if (view === "") content = <ChatView />;
  else if (view === "dashboard") content = <DashboardView />;
  else if (view === "brain") content = <BrainView />;
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

export function AppShell({ children }: { children: React.ReactNode }) {
  // children (route content) is unused for the SPA-style view switch,
  // kept so the root layout composes normally.
  void children;
  return (
    <I18nProvider>
    <UIProvider>
      <div className="relative z-10 flex h-screen w-screen overflow-hidden">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <div className="flex min-h-0 flex-1">
            <main className="min-w-0 flex-1 overflow-y-auto">
              <ViewRouter />
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
