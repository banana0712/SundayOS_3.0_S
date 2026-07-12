import type { Config } from "tailwindcss";

// Sunday OS Design Language 1.0 — tokens
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Neutrals
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        elevated: "var(--elevated)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        // Text
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        tertiary: "var(--text-tertiary)",
        // Semantic
        accent: "var(--accent)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        // Design Language typographic scale
        display: ["48px", { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "600" }],
        heading: ["32px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "600" }],
        title: ["24px", { lineHeight: "1.15", letterSpacing: "-0.01em", fontWeight: "600" }],
        subtitle: ["18px", { lineHeight: "1.3", letterSpacing: "-0.01em", fontWeight: "600" }],
        body: ["16px", { lineHeight: "1.5" }],
        caption: ["13px", { lineHeight: "1.4" }],
        code: ["13px", { lineHeight: "1.5" }],
      },
      spacing: {
        // 8pt grid
        "1": "4px",
        "2": "8px",
        "3": "12px",
        "4": "16px",
        "6": "24px",
        "8": "32px",
        "10": "40px",
        "12": "48px",
        "16": "64px",
        "24": "96px",
      },
      borderRadius: {
        sm: "10px",
        md: "16px",
        lg: "24px",
        panel: "28px",
        glass: "32px",
      },
      boxShadow: {
        // Shadows: extremely light
        subtle: "0 1px 2px rgba(0,0,0,0.24)",
        card: "0 8px 30px rgba(0,0,0,0.18)",
        glow: "0 0 0 1px var(--border), 0 20px 60px rgba(0,0,0,0.35)",
      },
      backdropBlur: {
        glass: "28px",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      keyframes: {
        breathe: {
          "0%,100%": { transform: "scale(1)", opacity: "0.9" },
          "50%": { transform: "scale(1.06)", opacity: "1" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "dash-flow": {
          to: { strokeDashoffset: "-24" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        breathe: "breathe 4s ease-in-out infinite",
        "fade-up": "fade-up 250ms cubic-bezier(0.22,1,0.36,1) both",
        "dash-flow": "dash-flow 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
