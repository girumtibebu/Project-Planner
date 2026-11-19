import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// Output goes directly into the app's public/frontend folder so
// `bench build` picks it up and copies it to sites/assets/event_planner/frontend
export default defineConfig({
  plugins: [vue()],
  base: "/assets/event_planner/frontend/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: path.resolve(
      __dirname,
      "../event_planner/public/frontend"
    ),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    port: 8080,
    proxy: {
      // Proxy Frappe API calls to the local bench in dev
      "/api": {
        target: "http://dev.local:8000",
        changeOrigin: true,
        cookieDomainRewrite: "localhost",
      },
    },
  },
});
