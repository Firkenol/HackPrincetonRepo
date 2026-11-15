// Records a walkthrough of the OffSpec console: drives headless Chrome over the DevTools
// protocol, captures frames with timestamps, and writes an ffmpeg concat list.
// Usage: node record.mjs <repo> <outDir>
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [repo, outDir] = process.argv.slice(2);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const W = 1440, H = 900, PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(path.join(outDir, "frames"), { recursive: true });

const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${path.join(outDir, "profile")}`,
  `--window-size=${W},${H}`, "--hide-scrollbars", "--no-first-run", "about:blank",
], { stdio: "ignore" });

let targets;
for (let i = 0; i < 50 && !targets; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); } catch { await sleep(200); }
}
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let nextId = 1;
const pending = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = nextId++;
  pending.set(id, (msg) => (msg.error ? reject(new Error(`${method}: ${msg.error.message}`)) : resolve(msg.result)));
  ws.send(JSON.stringify({ id, method, params }));
});
const ev = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? "evaluate failed");
  return r.result.value;
};

await send("Page.enable");

// ---- frame capture, with the time each frame was taken
const frames = [];
let recording = true;
const captureLoop = async () => {
  let n = 0;
  while (recording) {
    const started = Date.now();
    try {
      const shot = await Promise.race([send("Page.captureScreenshot", { format: "jpeg", quality: 88 }), sleep(4000).then(() => null)]);
      if (!shot) throw new Error("screenshot timed out");
      const { data } = shot;
      const name = `f${String(n++).padStart(5, "0")}.jpg`;
      fs.writeFileSync(path.join(outDir, "frames", name), Buffer.from(data, "base64"));
      frames.push({ name, t: started });
    } catch (error) { if (!capture.warned) { capture.warned = true; console.log('capture error: ' + error.message); } }
    await sleep(Math.max(0, 50 - (Date.now() - started)));
  }
};
const capture = { warned: false };
let capturing;

// ---- helpers used by the steps
const caption = (text) => ev(`(() => {
  let el = document.getElementById("demo-caption");
  if (!el) {
    el = document.createElement("div");
    el.id = "demo-caption";
    el.style.cssText = "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:9999;max-width:1100px;padding:12px 22px;border-radius:12px;background:rgba(8,12,19,.92);border:1px solid #2c3a52;color:#e7ecf3;font:500 19px/1.4 var(--font-plex-sans),system-ui,sans-serif;box-shadow:0 12px 40px rgba(0,0,0,.6);text-align:center;transition:opacity .25s";
    document.body.appendChild(el);
  }
  el.style.opacity = 0;
  setTimeout(() => { el.textContent = ${JSON.stringify(text)}; el.style.opacity = 1; }, 180);
})()`);
const scrollTo = (selector, offset = 90) => ev(`(() => {
  const el = document.querySelector(${JSON.stringify(selector)});
  if (!el) return false;
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - ${offset}, behavior: "smooth" });
  return true;
})()`);
const top = () => ev(`window.scrollTo({ top: 0, behavior: "smooth" })`);
const openFeed = (text) => ev(`(() => {
  const item = [...document.querySelectorAll('[data-testid="feed-item"]')].find((e) => e.textContent.includes(${JSON.stringify(text)}));
  if (!item) return false;
  item.scrollIntoView({ block: "center", behavior: "smooth" });
  setTimeout(() => item.click(), 450);
  return true;
})()`);
const must = (ok, what) => { if (!ok) throw new Error(`step failed: ${what}`); };

// ---- the walkthrough
await send("Page.navigate", { url: "http://127.0.0.1:3010/" });
await sleep(2500);
capturing = captureLoop();
await sleep(1500);
await caption("OffSpec checks a product listing's own claims against physics, and shows the math.");
await sleep(4000);

// 1. an impossible claim, checked live from pasted text
const listing = fs.readFileSync(path.join(repo, "fixtures", "fixture_01.txt"), "utf8");
await caption("Paste a listing or upload a screenshot. Nothing is scraped from any marketplace.");
await ev(`document.getElementById("listing-text").focus()`);
await sleep(600);
await send("Input.insertText", { text: listing });
await sleep(2600);
console.log("probe " + await ev(`(() => { const b = [...document.querySelectorAll("button")].find((x) => x.textContent.includes("Check listing")); const t = document.getElementById("listing-text"); return JSON.stringify({ found: !!b, disabled: b?.disabled, textLen: t?.value.length, active: document.activeElement?.id, feed: document.querySelectorAll('[data-testid="feed-item"]').length }); })()`));
must(await ev(`(() => { const b = [...document.querySelectorAll("button")].find((x) => x.textContent.includes("Check listing")); if (!b || b.disabled) return false; b.click(); return true; })()`), "Check listing");
await sleep(1500);
await caption("Three agents: one reads the listing, one runs the checks as plain code, one writes the report.");
must(await scrollTo("#trace-heading", 110), "trace");
await sleep(5500);
await caption("Impossible: the claim needs more energy than a cell of that size can hold. Routed as auto-resolvable.");
must(await scrollTo('[data-testid="verdict-card"]', 90), "verdict card");
await sleep(5000);
await caption("Every step of the arithmetic is shown, with the constant it used and where that constant comes from.");
must(await scrollTo('[data-testid="check"][data-check-id="form_factor_bound"]', 100), "form factor check");
await sleep(6500);

// 2. an honest listing passes
await top();
await sleep(700);
must(await openFeed("6,200 mAh"), "fixture 6");
await caption("An honest pack: label, dimensions and weight all agree. No red flags, no action needed.");
await sleep(1800);
must(await scrollTo('[data-testid="verdict-card"]', 90), "verdict card 6");
await sleep(4500);

// 3. a contradiction between the title and the product
await top();
await sleep(600);
must(await openFeed("alkaline battery, heavy duty"), "fixture 3");
await caption("Title says alkaline; the cells are marked R6 and R03, the codes for zinc-carbon. Flag: a person reviews it.");
await sleep(1800);
must(await scrollTo('[data-testid="verdict-card"]', 90), "verdict card 3");
await sleep(5200);

// 4. nothing to test
await top();
await sleep(600);
must(await openFeed("zinc-carbon battery, heavy duty"), "fixture 5");
await caption("No checkable claim: the listing states nothing a calculation can test, so the tool stays quiet.");
await sleep(1800);
must(await scrollTo('[data-testid="verdict-card"]', 90), "verdict card 5");
await sleep(4500);

// 5. a check pack for another category
await top();
await sleep(600);
must(await openFeed("4K headline, native 1,280"), "projector");
await caption("Check packs add other categories: projectors, magnifying glasses, monoculars.");
await sleep(1800);
must(await scrollTo('[data-testid="verdict-card"]', 90), "verdict card projector");
await sleep(5000);

// 6. batch
await top();
await sleep(600);
must(await ev(`(() => { const t = [...document.querySelectorAll('[role="tab"]')].find((x) => x.textContent.trim() === "Batch"); if (!t) return false; t.click(); return true; })()`), "Batch tab");
await caption("Batch mode: every listing in one run, split into what a calculation settles and what goes to a person.");
await sleep(6500);
await caption("OffSpec. Verdicts are about the claim, never the seller. Every number is reproducible.");
await sleep(4000);

recording = false;
await capturing;
// ffmpeg concat list: each frame lasts until the next one was taken
const lines = [];
for (let i = 0; i < frames.length; i++) {
  const d = ((frames[i + 1]?.t ?? frames[i].t + 100) - frames[i].t) / 1000;
  lines.push(`file 'frames/${frames[i].name}'`, `duration ${d.toFixed(3)}`);
}
lines.push(`file 'frames/${frames.at(-1).name}'`);
fs.writeFileSync(path.join(outDir, "frames.txt"), lines.join("\n") + "\n");
console.log(`frames ${frames.length}, seconds ${((frames.at(-1).t - frames[0].t) / 1000).toFixed(1)}`);
ws.close();
chrome.kill();
process.exit(0);
