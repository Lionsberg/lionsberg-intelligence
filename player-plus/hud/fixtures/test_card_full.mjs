// test_card_full.mjs: the full card (card-full.js). Each thing presented is a card, and the whole
// card opens to show all its detail. Proven in headless Chrome (muted,
// no sound) against deal-rich and deal-chain: from the Deal's first card, "Open the card" opens a
// sheet with the face, where it stands, why it was dealt, its story (at least one row) and its id;
// no schema word and no gold inside it; one column with no sideways scroll at 320 px; Escape
// closes it and focus returns to the opener; the same card opened from the Chain shows the same
// sections; a card of the next hand opens too; a sighting dealt in the hand opens as a card.
//
//   node hud/fixtures/test_card_full.mjs            (test_strings.py runs it when node and Chrome are here)
//
// A static server on 127.0.0.1 at a port above 9000 serves hud/ read-only; the page reads
// fixtures/<name>.json directly (the story from the fixture's cards[].lines), so nothing is
// written anywhere. Nothing leaves this machine.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import os from "node:os";

const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!fs.existsSync(CHROME)) { console.log("card full: Chrome not found, skipped"); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SCHEMA = /\b(events?|holons?|float|anchor(s|ed)?|settle[ds]?|settling|engine|schema|hash(es)?|process(es)?|forge|hooks?|tokens?|payload|jsonl?)\b/i;
const S = JSON.parse(fs.readFileSync(path.join(HUD, "strings.json"), "utf8"));
const SECTIONS = { stands: S["card.full.sec.stands"], why: S["card.full.sec.why"], story: S["card.full.sec.story"], prov: S["card.full.sec.provenance"] };

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".jpg": "image/jpeg", ".png": "image/png", ".woff2": "font/woff2", ".svg": "image/svg+xml" };
const server = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  let p = path.normalize(path.join(HUD, decodeURIComponent(u.pathname)));
  if (!p.startsWith(HUD)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, "index.html");
  if (!fs.existsSync(p) || /\.py$/.test(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream", "Cache-Control": "no-store" });
  fs.createReadStream(p).pipe(res);
});
let PORT = 0;
for (let i = 0; i < 20 && !PORT; i++) {
  const p = 9400 + Math.floor(Math.random() * 400);
  PORT = await new Promise((r) => { server.once("error", () => r(0)); server.listen(p, "127.0.0.1", () => r(p)); });
}
const DBG = 9800 + Math.floor(Math.random() * 150);
const prof = fs.mkdtempSync(path.join(process.env.SCRATCH || os.tmpdir(), "cardfull-chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${DBG}`, "--mute-audio", "--no-first-run",
  "--no-default-browser-check", `--user-data-dir=${prof}`, "--hide-scrollbars", "about:blank"], { stdio: "ignore" });

let ws, id = 0;
const waiters = new Map();
let errors = [];
for (let i = 0; i < 60 && !ws; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${DBG}/json/list`)).json();
    const pg = list.find((x) => x.type === "page");
    if (pg) ws = new WebSocket(pg.webSocketDebuggerUrl);
  } catch { /* not yet */ }
  if (!ws) await sleep(200);
}
await new Promise((r) => ws.addEventListener("open", r));
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiters.has(msg.id)) { waiters.get(msg.id)(msg); waiters.delete(msg.id); return; }
  if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error" && !/favicon/.test(msg.params.entry.url || "")) errors.push(msg.params.entry.text + " " + (msg.params.entry.url || ""));
});
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiters.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); return r.result?.result?.value; };
await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
// never a sound on this computer: the browser's own speech stubbed before any script runs (speechSynthesis
// in headless Chrome speaks through the system voice; --mute-audio does not stop it), and every page muted
await send("Page.addScriptToEvaluateOnNewDocument", { source: `window.__lionsbergMuted = true;
  try { const quiet = { speak() {}, cancel() {}, pause() {}, resume() {}, getVoices() { return []; }, speaking: false, pending: false, paused: false, addEventListener() {}, removeEventListener() {} };
    Object.defineProperty(window, "speechSynthesis", { value: quiet, configurable: true }); } catch {}` });
const phone = (w = 390) => send("Emulation.setDeviceMetricsOverride", { width: w, height: 844, deviceScaleFactor: 2, mobile: true });
await phone();
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }, { name: "prefers-reduced-motion", value: "reduce" }] });

async function open(fixture, hash = "#/deal") {
  errors = [];
  await send("Page.navigate", { url: `http://127.0.0.1:${PORT}/index.html?fixture=${fixture}&theme=night${hash}` });
  await sleep(1800);
  await js("sessionStorage.clear(); localStorage.clear(); true");
  await send("Page.reload", { ignoreCache: true });
  await sleep(2200);
}
const fails = [];
const check = (name, ok, detail) => { if (!ok) fails.push(`${name}${detail ? ": " + detail : ""}`); console.log(`${ok ? "pass" : "FAIL"}  ${name}${!ok && detail ? " — " + detail : ""}`); };

/** What the open sheet shows: its section labels, title, story rows, id, words, gold, width. */
const SHEET = `(() => {
  const sh = document.querySelector('.sheet.sheet--card');
  if (!sh) return null;
  const probe = document.createElement('i'); probe.className = 'owed'; probe.style.color = 'var(--owed)'; document.body.append(probe);
  const gold = getComputedStyle(probe).color; probe.remove();
  const goldIn = [...sh.querySelectorAll('*')].filter((e) => e.getClientRects().length).filter((e) => {
    const s = getComputedStyle(e);
    return s.color === gold || (s.borderTopWidth !== '0px' && s.borderTopColor === gold) || s.backgroundColor === gold;
  }).map((e) => e.className || e.tagName).slice(0, 5);
  return {
    sections: [...sh.querySelectorAll('.cf-sec')].map((s) => s.getAttribute('aria-label')),
    face: !!sh.querySelector('.cf-face .card-title, .cf-face .dock-ask-q') && (sh.querySelector('.cf-face .card-title, .cf-face .dock-ask-q').innerText || '').trim(),
    eyebrow: (sh.querySelector('.cf-eyebrow') || {}).innerText || '',
    rows: sh.querySelectorAll('.cf-row').length,
    id: (sh.querySelector('.cf-id') || {}).innerText || '',
    text: sh.innerText,
    gold: goldIn,
    wide: sh.scrollWidth > sh.clientWidth + 1 || [...sh.querySelectorAll('*')].some((e) => e.getBoundingClientRect().right > innerWidth + 1),
    focusIn: sh.contains(document.activeElement),
  };
})()`;
const sheet = () => js(SHEET);
const esc = async () => {
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await sleep(700);
};
const common = (label, s) => {
  check(`${label}: no script errors`, errors.length === 0, errors.join(" | "));
  const raw = s && s.text.match(/\[[a-z_]+\.[A-Za-z0-9_.]+\]/);
  check(`${label}: no missing key in the sheet`, !raw, raw && raw[0]);
  const hit = s && s.text.match(SCHEMA);
  check(`${label}: no schema word in the sheet`, !hit, hit && hit[0]);
  check(`${label}: no gold inside the sheet`, s && !s.gold.length, s && s.gold.join(", "));
  check(`${label}: no contraction`, s && !/\b[A-Za-z]+n't\b/.test(s.text));
};

for (const fx of ["deal-rich", "deal-chain"]) {
  await phone();
  await open(fx);
  const first = await js("(() => { const c = document.querySelector('.card--large.owed'); return c ? { id: c.dataset.card, opener: !!c.querySelector('.card-open-btn') } : null; })()");
  check(`${fx}: the Deal's first card carries "Open the card"`, first && first.opener, JSON.stringify(first));
  check(`${fx}: no fold left on the face`, !(await js("!!document.querySelector('.card-fold')")));
  await js("(() => { const b = document.querySelector('.card--large.owed .card-open-btn'); b.focus(); b.click(); return true; })()");
  await sleep(1200);
  const s = await sheet();
  check(`${fx}: the full card opens as a sheet`, !!s);
  if (!s) continue;
  check(`${fx}: the face shows its title`, !!s.face, s.face);
  check(`${fx}: the face says why it is here and its home`, s.eyebrow.length > 0, s.eyebrow);
  for (const k of ["stands", "why", "story", "prov"]) check(`${fx}: "${SECTIONS[k]}" is shown`, s.sections.includes(SECTIONS[k]), s.sections.join(" | "));
  check(`${fx}: the story has at least one row`, s.rows >= 1, String(s.rows));
  check(`${fx}: its id in full`, s.id === first.id, s.id);
  check(`${fx}: focus moved into the sheet`, s.focusIn);
  check(`${fx}: the hash names the card`, (await js("location.hash")) === "#/card/" + encodeURIComponent(first.id));
  common(fx, s);
  // one column, no sideways scroll at 320 px
  await phone(320); await sleep(400);
  const narrow = await sheet();
  check(`${fx}: no horizontal scroll at 320 px`, narrow && !narrow.wide);
  await phone(); await sleep(300);
  // Escape closes; focus returns to the opener
  await esc();
  check(`${fx}: Escape closes the sheet`, !(await js("!!document.querySelector('.sheet--card')")));
  const back = await js(`(() => { const a = document.activeElement; return a ? { open: a.dataset.openCard || null, card: (a.closest('[data-card]') || {}).dataset?.card || null } : null; })()`);
  check(`${fx}: focus returns to the opener`, back && (back.open === first.id || back.card === first.id), JSON.stringify(back));
  check(`${fx}: the hash returns to the Deal`, /^#\/deal/.test(await js("location.hash")) || (await js("location.hash")) === "");

  // the same card from the Chain shows the same sections: the first dealt card on the road
  // (deal-chain's first is; deal-rich's first is off the chain, so its meeting day is used)
  await js("location.hash = '#/chain'; true"); await sleep(1500);
  const road = await js("[...document.querySelectorAll('.road-title')].map((b) => b.innerText.trim())");
  const pick = await js(`import('./state.js').then((m) => { const st = m.store.state; const road = ${JSON.stringify(road || [])};
    const dc = (st.deal.cards || []).find((c) => { const k = m.read.card(st, c.id); return k && road.includes(k.title); });
    return dc ? { id: dc.id, title: m.read.card(st, dc.id).title } : null; })`);
  check(`${fx}: a dealt card is on the road`, !!pick, JSON.stringify(road));
  if (pick) {
    await js("location.hash = '#/deal'; true"); await sleep(1200);
    await js(`location.hash = '#/card/${pick.id}'; true`); await sleep(1200);
    const ref = await sheet();
    await esc();
    await js("location.hash = '#/chain'; true"); await sleep(1500);
    const clicked = await js(`(() => { const b = [...document.querySelectorAll('.road-title')].find((x) => x.innerText.trim() === ${JSON.stringify(pick.title)}); if (!b) return false; b.focus(); b.click(); return true; })()`);
    await sleep(1200);
    const c = clicked ? await sheet() : null;
    check(`${fx}: the card opens from the Chain`, !!c);
    if (c && ref) {
      check(`${fx}: the Chain's full card shows the same sections as the Deal's`, JSON.stringify(c.sections) === JSON.stringify(ref.sections), `${c.sections.join(" | ")} vs ${ref.sections.join(" | ")}`);
      check(`${fx}: the Chain's full card is the same card`, c.id === pick.id, c.id);
      check(`${fx}: the Chain's full card has its story`, c.rows >= 1, String(c.rows));
      common(`${fx} from the Chain`, c);
      await esc();
      check(`${fx}: closing from the Chain leaves the Chain`, /^#\/chain/.test(await js("location.hash")), await js("location.hash"));
      const back = await js("(document.activeElement || {}).className || ''");
      check(`${fx}: focus returns to the Chain's road`, /road-title/.test(back), back + " / " + (await js("(document.activeElement || {}).outerHTML.slice(0, 160)")));
    }
  }
}

// a card of the next hand opens too; a sighting dealt in the hand opens as a card
{
  const rich = JSON.parse(fs.readFileSync(path.join(HUD, "fixtures", "deal-rich.json"), "utf8"));
  await phone();
  await open("deal-rich");
  const sight = rich.deal.cards.find((c) => c.kind === "sighting");
  if (sight) {
    await js(`location.hash = '#/card/${sight.id}'; true`); await sleep(1200);
    const s = await sheet();
    check("deal-rich: a dealt sighting opens as a card", !!s && s.sections.includes(SECTIONS.stands) && s.sections.includes(SECTIONS.why), s && s.sections.join(" | "));
    if (s) common("deal-rich sighting", s);
    await esc();
  }
  for (let i = 0; i < rich.deal.cards.length; i++) {
    await js("(() => { const o = document.querySelector('.card--large .option'); if (o) o.click(); return true; })()");
    await sleep(400);
  }
  await js("(() => { const b = document.querySelector('#main .deal-next button'); if (b) b.click(); return true; })()");
  await sleep(900);
  const next = await js("(() => { const c = document.querySelector('.card--large.owed'); return c ? c.dataset.card : null; })()");
  check("deal-rich: the next hand is dealt", next === rich.deal.beyond.cards[0].id, next);
  await js("(() => { const b = document.querySelector('.card--large.owed .card-open-btn'); if (b) { b.focus(); b.click(); } return true; })()");
  await sleep(1200);
  const s = await sheet();
  check("deal-rich: the next hand's card opens", !!s && s.id === next, s && s.id);
  if (s) {
    check("deal-rich: the next hand's card says it waits beyond today's hand", /Beyond today/.test(s.text), "");
    for (const k of ["stands", "why", "prov"]) check(`deal-rich next hand: "${SECTIONS[k]}" is shown`, s.sections.includes(SECTIONS[k]), s.sections.join(" | "));
    common("deal-rich next hand", s);
  }
  await esc();
}

ws.close(); chrome.kill(); server.close();
await sleep(500);
try { fs.rmSync(prof, { recursive: true, force: true, maxRetries: 5 }); } catch { /* Chrome still closing */ }
console.log(fails.length ? `card full: ${fails.length} failing` : "card full: all pass");
process.exit(fails.length ? 1 : 0);
