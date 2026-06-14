import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built dist/ serves from any path on the box
// (e.g. file://, a sub-folder behind a static server, etc.).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { host: true, port: 5173 },
  preview: { host: true, port: 4173 },
});
