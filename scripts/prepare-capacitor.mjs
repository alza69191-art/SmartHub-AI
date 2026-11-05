import { cp, mkdir, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(root, "www");
const excluded = new Set([".git", ".github", "api", "android", "docs", "node_modules", "scripts", "www"]);
const allowed = new Set([
  ".html", ".js", ".css", ".json", ".webmanifest", ".svg", ".png", ".jpg",
  ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".otf",
  ".txt", ".xml", ".mp3", ".wav", ".mp4", ".webm"
]);

async function copyTree(source, destination, relative = "") {
  await mkdir(destination, { recursive: true });
  const entries = await readdir(source, { withFileTypes: true });
  for (const entry of entries) {
    if (!relative && excluded.has(entry.name)) continue;
    const from = path.join(source, entry.name);
    const to = path.join(destination, entry.name);
    if (entry.isDirectory()) {
      await copyTree(from, to, path.join(relative, entry.name));
    } else if (entry.isFile() && allowed.has(path.extname(entry.name).toLowerCase())) {
      await cp(from, to);
    }
  }
}

await rm(output, { recursive: true, force: true });
await copyTree(root, output);
console.log("Prepared www/ from the static SmartHub website.");
