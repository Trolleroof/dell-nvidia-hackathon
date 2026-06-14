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

        // ── Brand accents — restrained punctuation on the mono canvas ──────
        // Green is the hero accent (NVIDIA), blue is secondary (Dell). Used only
        // for live/interactive/brand emphasis; structure stays black & white.
        nvidia: { DEFAULT: "var(--nv)", bright: "var(--nv-bright)" },
        dell: { DEFAULT: "var(--dell)", bright: "var(--dell-bright)" },
        cloud: "var(--dell-bright)",

        // Neutral structural aliases.
        ink: "var(--background)",
        panel: "var(--background)",
        panel2: "var(--background)",
        line: "var(--border)",
        lineSoft: "var(--border-light)",
        text: "var(--foreground)",
        dim: "var(--muted-foreground)",
        faint: "var(--faint)",
        danger: "var(--foreground)",
        warn: "var(--foreground)",
      },
      fontFamily: {
        // Official brand spec: monospaced type throughout. Every alias resolves
        // to the same mono stack so existing class names stay in-system.
        display: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        serif: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        sans: ['"JetBrains Mono"', "ui-monospace", "monospace"],
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
