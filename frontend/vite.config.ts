import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api is proxied to the FastAPI backend; in production the backend
// serves the built frontend itself, so everything stays same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
