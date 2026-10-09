import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  // Reverse-domain app identifier — required by both Google Play and the App
  // Store. Change "com.medreportai.app" to your own domain/org before actual
  // store submission (this cannot be changed later without a new app listing).
  appId: "com.medreportai.app",
  appName: "MedReport AI",
  webDir: "dist",
  server: {
    // Only used during local development against a device/emulator so the
    // app can reach your backend on your machine's LAN IP instead of
    // localhost (which refers to the device itself, not your computer).
    // Leave commented out for production builds — those load the bundled
    // dist/ files directly, same as the PWA does.
    // url: "http://192.168.1.X:5173",
    // cleartext: true,
    androidScheme: "https",
  },
  ios: {
    contentInset: "automatic",
  },
  android: {
    backgroundColor: "#F6F8F7",
  },
};

export default config;
