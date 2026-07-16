"use client";

import { createContext, useContext, useState, ReactNode } from "react";

export type ThemeConfig = {
  // 背景
  backgroundType: "gradient" | "image" | "solid";
  backgroundImage: string | null;
  backgroundGradient: string;
  backgroundSolid: string;
  backgroundBlur: number;

  // 液态玻璃效果
  glassOpacity: number;
  glassBlur: number;
  glassBorder: number;
  glassReflection: boolean;

  // 侧边栏
  sidebarWidth: number;
  sidebarOpacity: number;

  // 消息气泡
  bubbleRadius: number;
  bubbleUserColor: string;
  bubbleAiColor: string;
  bubbleOpacity: number;

  // 动画
  animationSpeed: number;
  enableAnimations: boolean;

  // 字体
  fontSize: number;
  lineHeight: number;
};

const defaultTheme: ThemeConfig = {
  backgroundType: "gradient",
  backgroundImage: null,
  backgroundGradient: "radial-gradient(800px 600px at 20% 10%, rgba(10, 132, 255, 0.12), transparent 60%), radial-gradient(600px 500px at 80% 90%, rgba(191, 90, 242, 0.10), transparent 55%)",
  backgroundSolid: "#1a1a1e",
  backgroundBlur: 0,

  glassOpacity: 0.08,
  glassBlur: 80,
  glassBorder: 0.15,
  glassReflection: true,

  sidebarWidth: 280,
  sidebarOpacity: 0.03,

  bubbleRadius: 18,
  bubbleUserColor: "#0a84ff",
  bubbleAiColor: "rgba(255, 255, 255, 0.12)",
  bubbleOpacity: 1,

  animationSpeed: 1,
  enableAnimations: true,

  fontSize: 15,
  lineHeight: 1.65,
};

type ThemeContextType = {
  theme: ThemeConfig;
  updateTheme: (updates: Partial<ThemeConfig>) => void;
  resetTheme: () => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeConfig>(defaultTheme);

  const updateTheme = (updates: Partial<ThemeConfig>) => {
    setTheme((prev) => ({ ...prev, ...updates }));
  };

  const resetTheme = () => {
    setTheme(defaultTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, updateTheme, resetTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
