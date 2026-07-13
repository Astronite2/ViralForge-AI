import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? "0.0.0") },
  server: { proxy: { "/api": "http://localhost:8000", "/health": "http://localhost:8000", "/ready": "http://localhost:8000", "/opportunities": "http://localhost:8000" } },
});
