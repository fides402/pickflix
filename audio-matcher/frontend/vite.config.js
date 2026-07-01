import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1", // pin IPv4 explicitly: "localhost" can resolve to ::1 on
    // Windows, which then refuses connections made to 127.0.0.1 directly
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8123",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
