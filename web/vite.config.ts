import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  // `./` for Capacitor / local preview. GitHub Pages sets VITE_BASE=/ranking-tool/
  base: process.env.VITE_BASE || "./",
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 43128,
    proxy: {
      "/api": "http://127.0.0.1:43127",
    },
  },
});
