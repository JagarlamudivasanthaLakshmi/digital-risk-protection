import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { spawn } from "node:child_process";
import process from "node:process";

const statePath = resolve(".netlify/state.json");
let siteId = process.env.NETLIFY_SITE_ID;

if (!siteId && existsSync(statePath)) {
  const state = JSON.parse(readFileSync(statePath, "utf8"));
  siteId = state.siteId;
}

if (!siteId || !/^[a-zA-Z0-9-]+$/.test(siteId)) {
  console.error(
    "No linked Netlify site was found. Run `npx netlify link`, then rerun `npm run identity:enable`.",
  );
  process.exitCode = 1;
} else {
  const settingsUrl = `https://app.netlify.com/projects/${siteId}/identity`;
  const command = process.platform === "win32" ? "cmd.exe" : "open";
  const args = process.platform === "win32"
    ? ["/d", "/c", "start", "", settingsUrl]
    : [settingsUrl];
  const browser = spawn(command, args, { stdio: "ignore", windowsHide: true });
  browser.on("error", (error) => {
    console.error(`Could not open Netlify Identity settings: ${error.message}`);
    process.exitCode = 1;
  });
  console.log(`Opened ${settingsUrl}. Select “Enable Identity” in the site dashboard to finish setup.`);
}
