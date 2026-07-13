"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type Theme = "dark" | "light";

type UIState = {
  view: string; // active nav slug
  setView: (slug: string) => void;

  inspectorOpen: boolean;
  toggleInspector: () => void;

  consoleOpen: boolean;
  toggleConsole: () => void;

  paletteOpen: boolean;
  setPaletteOpen: (v: boolean) => void;

  theme: Theme;
  toggleTheme: () => void;
};

const Ctx = createContext<UIState | null>(null);

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [view, setView] = useState("");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [consoleOpen, setConsoleOpen] = useState(true);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>("dark");

  // ⌘K / Ctrl+K — Command Palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if (e.key === "Escape") setPaletteOpen(false);
      // ⌘J toggles console (DevTools-ish)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setConsoleOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.classList.toggle("light", theme === "light");
  }, [theme]);

  const value = useMemo<UIState>(
    () => ({
      view,
      setView: (s) => {
        setView(s);
        setPaletteOpen(false);
      },
      inspectorOpen,
      toggleInspector: () => setInspectorOpen((v) => !v),
      consoleOpen,
      toggleConsole: () => setConsoleOpen((v) => !v),
      paletteOpen,
      setPaletteOpen,
      theme,
      toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")),
    }),
    [view, inspectorOpen, consoleOpen, paletteOpen, theme]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useUI() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useUI must be used within UIProvider");
  return ctx;
}

// Shared live-clock hook for "alive" feel (client only, avoids SSR mismatch)
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

// Static display — live data comes from backend polling, not client-side drift.
// Previously used setInterval(120ms) × 5 instances = 40+ phantom re-renders/sec.
export function useDrift(base: number, _amp = 0, _periodMs = 4000) {
  return base;  // stable value, no state updates
}
