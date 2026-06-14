/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#000000",
        panel: "#0c0f14",
        panel2: "#11151c",
        line: "#1c2430",
        lineSoft: "#161c25",
        dim: "#8a98a8",
        faint: "#56636f",
        nvidia: { DEFAULT: "#76b900", bright: "#95e600" },
        dell: { DEFAULT: "#0a8fdc", bright: "#38b6ff" },
        cloud: "#b06bff",
        danger: "#ff5470",
        warn: "#ffb02e",
      },
      fontFamily: {
        sans: ['"Segoe UI"', "Inter", "system-ui", "sans-serif"],
        mono: ['ui-monospace', '"Cascadia Code"', "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
