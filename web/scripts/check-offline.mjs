#!/usr/bin/env node
/**
 * Fail the Vite build early if bundled snapshots are missing.
 * Vercel runs `npm run build` in web/ with no Python, so these JSON
 * files must already be committed under public/offline.
 */
import { existsSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dir = join(root, "public", "offline");
const required = [
  "status.json",
  "teams.json",
  "presets.json",
  "rankings.json",
  "boards.json",
  "history.json",
];

const missing = required.filter((name) => {
  const path = join(dir, name);
  return !existsSync(path) || statSync(path).size < 8;
});

if (missing.length) {
  console.error(
    [
      `Missing bundled offline snapshots in public/offline: ${missing.join(", ")}.`,
      "Commit those files (from `sixman-rank export-offline --out web/public/offline`)",
      "so `npm run build` succeeds on Vercel without a local Python server.",
    ].join("\n"),
  );
  process.exit(1);
}

for (const name of required) {
  const path = join(dir, name);
  console.log(`offline ${name} (${statSync(path).size} bytes)`);
}
