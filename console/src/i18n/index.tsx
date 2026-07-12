"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { DICT, type Lang } from "./dict";

type I18nState = {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggleLang: () => void;
  t: (key: string) => string;
};

const Ctx = createContext<I18nState | null>(null);

const STORAGE_KEY = "sunday.lang";
const DEFAULT_LANG: Lang = "zh"; // 默认中文（可一键切换）

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);

  // hydrate from localStorage after mount (avoid SSR mismatch)
  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as Lang | null;
    if (saved === "zh" || saved === "en") setLangState(saved);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    window.localStorage.setItem(STORAGE_KEY, l);
    document.documentElement.lang = l;
  };

  const value = useMemo<I18nState>(
    () => ({
      lang,
      setLang,
      toggleLang: () => setLang(lang === "zh" ? "en" : "zh"),
      t: (key: string) => DICT[key]?.[lang] ?? key,
    }),
    [lang]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
