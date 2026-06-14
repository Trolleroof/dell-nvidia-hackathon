/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ── Minimalist Monochrome (dark base) ──────────────────────────────
        // Single source of truth lives in :root (index.css). Black IS the
        // canvas; white IS the accent. Inversion = black-on-white for emphasis.
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        border: "var(--border)",
        "border-light": "var(--border-light)",
        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",
        ring: "var(--ring)",

        // ── Legacy aliases → collapsed to monochrome ───────────────────────
        // Any class the redesign misses degrades to mono instead of breaking
        // the "no color, ever" rule. Brand hues are intentionally neutralized.
        ink: "var(--background)",
        panel: "var(--background)",
        panel2: "var(--background)",
        line: "var(--border)",
        lineSoft: "var(--border-light)",
        text: "var(--foreground)",
        dim: "var(--muted-foreground)",
        faint: "var(--faint)",
        nvidia: { DEFAULT: "var(--foreground)", bright: "var(--foreground)" },
        dell: { DEFAULT: "var(--foreground)", bright: "var(--foreground)" },
        cloud: "var(--foreground)",
        danger: "var(--foreground)",
        warn: "var(--foreground)",
      },
      fontFamily: {
        // Serif is the hero. Sans is aliased to the body serif so default text
        // stays in-system; mono carries metadata/labels.
        display: ['"Playfair Display"', "Georgia", "serif"],
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"Source Serif 4"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        // Sharp everything. Non-negotiable.
        none: "0",
        DEFAULT: "0",
        sm: "0",
        md: "0",
        lg: "0",
        xl: "0",
        "2xl": "0",
        "3xl": "0",
        full: "0",
      },
    },
  },
  plugins: [],
};
