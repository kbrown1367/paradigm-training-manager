/*
 * Copyright © 2026 Paradigm Strategic Partners, LLC.
 * All Rights Reserved.
 *
 * Paradigm Training Manager™ is proprietary and confidential software.
 * Unauthorized copying, modification, distribution, or use is prohibited.
 * Software ID: PTM-PSP-2026
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const appVersion = readFileSync(
  resolve(__dirname, "../VERSION"),
  "utf8"
).trim();

export default defineConfig({
  define: {
    __PTM_VERSION__: JSON.stringify(appVersion),
  },
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5050",
        changeOrigin: true,
      },
    },
  },
});
