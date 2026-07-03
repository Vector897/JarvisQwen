import type { Config } from "tailwindcss";
import containerQueries from "@tailwindcss/container-queries";

export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          base: "var(--color-surface-base)",
          raised: "var(--color-surface-raised)",
          sunken: "var(--color-surface-sunken)",
        },
        content: {
          primary: "var(--color-content-primary)",
          secondary: "var(--color-content-secondary)",
          muted: "var(--color-content-muted)",
        },
        action: {
          primary: "var(--color-action-primary)",
          "primary-hover": "var(--color-action-primary-hover)",
        },
        border: {
          subtle: "var(--color-border-subtle)",
        },
      },
      borderRadius: {
        elegant: "var(--radius-elegant)",
      },
      transitionTimingFunction: {
        "spring-gentle": "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "spring-snappy": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      spacing: {
        "fluid-sm": "clamp(0.5rem, 1vw, 1rem)",
        "fluid-md": "clamp(1rem, 2vw, 1.75rem)",
      },
    },
  },
  plugins: [containerQueries],
} satisfies Config;
