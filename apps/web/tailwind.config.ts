import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        orbsys: {
          void:         "#0a0a0b",
          surface:      "#111113",
          raised:       "#17171a",
          border:       "#22222a",
          text:         "#e8e8f0",
          muted:        "#6b6b7e",
          dim:          "#3a3a48",
          gold:         "#c8a84b",
          "gold-dim":   "#7a6530",
          green:        "#4ea860",
          "green-dim":  "#1a2e1e",
          red:          "#c85a5a",
          "red-dim":    "#2e1a1a",
          blue:         "#5a82c8",
          "blue-dim":   "#1a2040",
          amber:        "#c89040",
          "amber-dim":  "#2e2010",
        },
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        body:    ["Inter", "sans-serif"],
        mono:    ["DM Mono", "monospace"],
      },
      borderRadius: { DEFAULT: "6px" },
    },
  },
  plugins: [],
};

export default config;
