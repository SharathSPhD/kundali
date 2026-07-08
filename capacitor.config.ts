import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Remote-URL wrapper strategy (see docs/MOBILE.md): the native shell loads
 * the production web app directly, so mobile releases pick up every web
 * deploy instantly and the server-rendered Next.js app needs no static
 * export. `webDir` points at a tiny placeholder that is only shown if the
 * remote URL is unreachable on first launch.
 */
const config: CapacitorConfig = {
  appId: "com.technektar.kundali",
  appName: "Kundali",
  webDir: "mobile/www",
  server: {
    url: "https://kundali-five.vercel.app",
    cleartext: false,
  },
  android: {
    allowMixedContent: false,
  },
  ios: {
    contentInset: "automatic",
  },
};

export default config;
