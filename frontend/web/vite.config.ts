/// <reference types="vitest" />
/// <reference types="vite/client" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
  },
  optimizeDeps: {
    include: ['@cloudscape/components'],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./testing/setup.ts"],
    globals: true,
  },
  define: {
    "import.meta.env.REACT_APP_ENVIRONMENT": JSON.stringify(
      process.env.REACT_APP_ENVIRONMENT
    ),
  },
});
