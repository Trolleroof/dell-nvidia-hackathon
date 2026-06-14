/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#000000",
        panel: "#080C13",
        panel2: "#0C1019",
        line: "#172030",
        lineSoft: "#0F1820",
        text: "#D5E6F5",
        dim: "#6A7A8E",
        faint: "#3E5060",
        nvidia: { DEFAULT: "#76b900", bright: "#95e600" },
        dell: { DEFAULT: "#0a8fdc", bright: "#38b6ff" },
        cloud: "#b06bff",
        danger: "#ff5470",
        warn: "#ffb02e",
      },
      fontFamily: {
        sans: ['"Barlow"', '"Segoe UI"', "system-ui", "sans-serif"],
        condensed: ['"Barlow Condensed"', '"Segoe UI"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', 'ui-monospace', '"Cascadia Code"', "monospace"],
      },
    },
  },
  plugins: [],
};
