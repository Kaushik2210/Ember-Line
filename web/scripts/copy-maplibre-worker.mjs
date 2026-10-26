// MapLibre runs in a web worker whose file the bundler cannot resolve on its own. Copy the worker and
// its shared chunk next to the app so setWorkerUrl("/maplibre/maplibre-gl-worker.mjs") can find them.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(root, "node_modules", "maplibre-gl", "dist");
const to = join(root, "public", "maplibre");
mkdirSync(to, { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(from, f), join(to, f));
}
console.log("copied maplibre worker files to public/maplibre");
