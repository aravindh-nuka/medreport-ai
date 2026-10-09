import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/favicon-32.png", "icons/apple-touch-icon.png"],
      manifest: {
        name: "MedReport AI — Medical Report Interpreter",
        short_name: "MedReport AI",
        description:
          "Understand your medical report in plain language, in Patient, Student, or Doctor mode, in English or Telugu.",
        theme_color: "#0E3A3D",
        background_color: "#F6F8F7",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Cache the app shell (HTML/CSS/JS) so the app opens instantly on repeat
        // visits, even offline. API calls (report data, AI explanations) are
        // deliberately NOT cached here — medical data should always be fetched
        // fresh, never served stale from a cache.
        globPatterns: ["**/*.{js,css,html,png,svg,woff2}"],
        navigateFallback: "index.html",
        runtimeCaching: [
          {
            // Google Fonts used for the app's serif/sans/mono type system —
            // safe to cache since font files never change once fetched.
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts-cache",
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
      devOptions: {
        enabled: false, // avoid service-worker caching interfering with `npm run dev`
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true, // listen on all network interfaces, not just localhost, so
                // the dev server is reachable from a phone on the same WiFi
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true, // same reason — `npm run preview` (used for PWA testing on
                // a phone) needs to accept connections from other devices
    port: 4173,
    proxy: {
      // preview does NOT automatically inherit server.proxy above — without
      // this, API calls would silently fail when testing the built app
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
