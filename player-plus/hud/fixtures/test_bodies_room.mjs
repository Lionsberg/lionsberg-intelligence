// test_bodies_room.mjs: the Bodies room (DESIGN-BODIES §13), proven in headless muted Chrome.
//
//   node hud/fixtures/test_bodies_room.mjs        (test_strings.py runs it when node and Chrome are here)
//
// A throwaway house under the system's temporary folder: one body stopped without closing (Vega,
// its claim naming a number no process holds), one finished (Rigel), a desk file, and an agents
// file with one agent for the dock. serve.py serves the deal-rich fixture on 127.0.0.1 at a port
// of its own, reading that house as its live block, with an empty sessions folder so no real
// conversation is read. Then the same view from a fixture file, where no server answers at all.
// Proves: the prime is first on the rail and marked; choosing a body fills the page with it; a
// body that cannot be reached shows the honest line and no line to speak; the dock's agent opens
// its conversation, with Words, Plain and the command line; the phone strip; no schema word on
// screen; gold nowhere. And the acts (2026-10-25): Task a New Worker says the cost before its one
// tap and refuses an empty task; each rail entry carries what it spent today, and the health line
// the house's day (from a planted cost ledger); Rigel's handoff is one card on the Deal, and its
// "Read it now" leaves the finished body saying "handoff read". Nothing is sent to any body;
// nothing leaves this machine; no sound.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import net from "node:net";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!fs.existsSync(CHROME)) { console.log("bodies room: Chrome not found, skipped"); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SCHEMA = /\b(events?|holons?|float|anchor(s|ed)?|settle[ds]?|settling|engine|schema|hash(es)?|process(es)?|forge|hooks?|tokens?|payload|jsonl?)\b/i;
const MACHINE_WORDS = /\b(subagents?|sessions?|pid|stream-json)\b/i;

// ---------------------------------------------------------------- the throwaway house
const tmp = fs.mkdtempSync(path.join(process.env.SCRATCH || os.tmpdir(), "bodies-room-"));
const house = path.join(tmp, "house"), bg = path.join(house, "bg");
fs.mkdirSync(path.join(bg, "bg-Vega"), { recursive: true });
fs.mkdirSync(path.join(bg, "bg-Rigel"), { recursive: true });
fs.mkdirSync(path.join(house, "desk"), { recursive: true });
fs.mkdirSync(path.join(tmp, "sessions"), { recursive: true });
fs.mkdirSync(path.join(tmp, "registry"), { recursive: true });
fs.writeFileSync(path.join(bg, "bg-Vega", "RUNNING"), "pid: 999999\nstart: 2026-10-25T13:00Z\ncard: —\n");
fs.writeFileSync(path.join(bg, "bg-Vega", "task.md"), "# Draw the bookshelf page\n\nThe shelf of the kit's books, one page.\n");
fs.writeFileSync(path.join(bg, "bg-Vega", "status.md"), "10:02 read the brief\n10:40 the first draft is done\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "DONE"), "done\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "task.md"), "# Gather the readings\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "handoff.md"), "What was done.\n\nreview_min: 4\n");
// a cost ledger: one session working in the house today, $1.25 so far (its running total rose from 0.75)
const day = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const ledger = path.join(tmp, "cost-ledger.jsonl");
fs.writeFileSync(ledger, [0.75, 1.25].map((c, i) => JSON.stringify({ ts: `${day}T0${7 + i}:00:00`, session: "77777777-7777-7777-7777-777777777777", cost_usd: c, model: "m", cwd: fs.realpathSync(house) })).join("\n") + "\n");
const desk = path.join(house, "desk", "on-deck.md");
fs.writeFileSync(desk, "holder: laptop\nsince: 2026-10-25T13:00Z\n");
const agents = path.join(tmp, "agents.json");
fs.writeFileSync(agents, JSON.stringify({ agents: [{ id: "your-agent", kind: "harness" }] }));

const free = () => new Promise((res) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
const PORT = await free();
const serve = spawn("python3", ["-I", path.join(HUD, "serve.py"), "--fixture", "deal-rich", "--port", String(PORT), "--agents", agents,
  "--bg", bg, "--desk", desk, "--sessions", path.join(tmp, "sessions"), "--harness-sessions", path.join(tmp, "registry"),
  "--cost-ledger", ledger, "--hq", path.join(tmp, "hq")],
  { cwd: HUD, stdio: ["ignore", "ignore", "pipe"] });
let serveErr = ""; serve.stderr.on("data", (d) => { serveErr += d; });
for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}/token`); if (r.ok) break; } catch { /* not yet */ } await sleep(150); }

// ---------------------------------------------------------------- Chrome, muted
const DBG = await free();
const prof = fs.mkdtempSync(path.join(tmp, "chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${DBG}`, "--mute-audio", "--no-first-run",
  "--no-default-browser-check", `--user-data-dir=${prof}`, "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let ws, id = 0;
const waiters = new Map();
let errors = [];
for (let i = 0; i < 60 && !ws; i++) {
  try { const list = await (await fetch(`http://127.0.0.1:${DBG}/json/list`)).json(); const pg = list.find((x) => x.type === "page"); if (pg) ws = new WebSocket(pg.webSocketDebuggerUrl); } catch { /* not yet */ }
  if (!ws) await sleep(200);
}
await new Promise((r) => ws.addEventListener("open", r));
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiters.has(msg.id)) { waiters.get(msg.id)(msg); waiters.delete(msg.id); return; }
  if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  // a refusal the room asked for (a body that cannot be read) and the missing favicon are not faults
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error" && !/favicon|\/bodies\/(talk|reach)/.test(msg.params.entry.url || "")) errors.push(msg.params.entry.text + " " + (msg.params.entry.url || ""));
});
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiters.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); return r.result?.result?.value; };
await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
// never a sound on this computer: the browser's own speech stubbed before any script runs (speechSynthesis
// in headless Chrome speaks through the system voice; --mute-audio does not stop it), and every page muted
await send("Page.addScriptToEvaluateOnNewDocument", { source: `window.__lionsbergMuted = true;
  try { const quiet = { speak() {}, cancel() {}, pause() {}, resume() {}, getVoices() { return []; }, speaking: false, pending: false, paused: false, addEventListener() {}, removeEventListener() {} };
    Object.defineProperty(window, "speechSynthesis", { value: quiet, configurable: true }); } catch {}` });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }, { name: "prefers-reduced-motion", value: "reduce" }] });
const size = (w, h) => send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: w < 600 ? 2 : 1, mobile: w < 600 });
let nav = 0;
async function open(base, query, hash = "#/bodies") {
  errors = [];
  await send("Page.navigate", { url: `${base}/index.html?theme=night&n=${++nav}${query || ""}${hash}` });
  await sleep(1500);
  await js("sessionStorage.clear(); localStorage.clear(); true");
  await send("Page.reload", { ignoreCache: true });
  await sleep(2600);
}
const click = (sel, re) => js(`(() => { const b = [...document.querySelectorAll(${JSON.stringify(sel)})].find((x) => ${re ? `/${re}/.test(x.innerText)` : "true"}); if (!b) return false; b.click(); return true; })()`);

const fails = [];
const check = (name, ok, detail) => { if (!ok) fails.push(`${name}${detail ? ": " + detail : ""}`); console.log(`${ok ? "pass" : "FAIL"}  ${name}${!ok && detail ? " — " + detail : ""}`); };
const GOLD_OUTSIDE = `(() => {
    const probe = document.createElement('i'); probe.style.color = 'var(--owed)'; document.body.append(probe);
    const gold = getComputedStyle(probe).color; probe.remove();
    const bad = [];
    for (const e of document.querySelectorAll('#main *')) {
      if (e.closest('.owed, .is-owed') || !e.getClientRects().length) continue;
      const s = getComputedStyle(e);
      if (s.color === gold || s.backgroundColor === gold || (s.borderTopWidth !== '0px' && s.borderTopColor === gold) || (s.borderLeftWidth !== '0px' && s.borderLeftColor === gold)) bad.push(e.className || e.tagName);
    }
    return bad.slice(0, 5);
  })()`;
const words = async (label) => {
  const main = await js("document.querySelector('#main').innerText");
  const hit = main.match(SCHEMA), mw = main.match(MACHINE_WORDS);
  check(`${label}: no schema word on screen`, !hit, hit && hit[0]);
  check(`${label}: no machine word on screen`, !mw, mw && mw[0]);
  check(`${label}: no raw key`, !/\[[a-z_]+\.[A-Za-z0-9_.]+\]/.test(main));
  const gold = await js(GOLD_OUTSIDE);
  check(`${label}: gold nowhere`, !gold.length, gold.join(", "));
  check(`${label}: no script errors`, errors.length === 0, errors.join(" | "));
};

const LIVE = `http://127.0.0.1:${PORT}`;
// ---------------------------------------------------------------- the desk, 1440 × 900
await size(1440, 900);
await open(LIVE);
const rail = await js(`[...document.querySelectorAll('.bodies-rail-list > li')].map((li) => li.classList.contains('bodies-rail-group') ? '#' + li.innerText.trim() : (li.querySelector('.br') || {}).className + '|' + (li.innerText || '').split('\\n')[0])`);
check("the rail is drawn", Array.isArray(rail) && rail.length >= 4, JSON.stringify(rail));
check("the prime is first on the rail", rail && /br--prime/.test(rail[0]), rail && rail[0]);
check("the prime is chosen when the room opens", await js("document.querySelector('.br--prime').getAttribute('aria-current') === 'true'"));
check("the prime carries its hairline and the word Prime", await js("(() => { const b = document.querySelector('.br--prime'); return parseFloat(getComputedStyle(b).borderLeftWidth) > 0 && /prime/i.test(b.querySelector('.br-name').innerText) && getComputedStyle(b.querySelector('.br-name')).textTransform === 'uppercase'; })()"));
check("the prime says who holds the desk", /holds the desk/i.test(await js("document.querySelector('.br--prime').innerText")));
const order = (rail || []).map((x) => x.startsWith("#") ? x.slice(1).toLowerCase() : /br--dock/.test(x) ? "dock" : /br--stopped/.test(x) ? "stopped-body" : /br--archive/.test(x) ? "archive" : /br--prime/.test(x) ? "prime" : /br--more/.test(x) ? "more" : "body");
const at = (k) => order.indexOf(k);
check("the rail's one order: prime, also open, stopped, the finished", at("prime") === 0 && at("also open") > 0 && at("dock") > at("also open") && at("stopped") > at("dock") && at("stopped-body") > at("stopped") && at("archive") > at("stopped-body"), JSON.stringify(order));
check("the stopped body is dashed", await js("getComputedStyle(document.querySelector('.br--stopped')).borderTopStyle === 'dashed'"));
check("the finished are one line", /1 finished|one finished/i.test(await js("document.querySelector('.br--archive').innerText")));
check("the page shows the prime", /^prime/i.test((await js("document.querySelector('.bodies-room-health').innerText")) || ""));
check("the field is not the page; it waits behind At a glance", await js("!document.querySelector('.bodies-page .bodies-stage') && !!document.querySelector('.bodies-glance-link')"));
check("an unreachable prime shows the honest line, never a conversation", await js("!!document.querySelector('.bodies-away-line') && !document.querySelector('.bodies-talk--terminal .dock-turns, .bodies-plain')"));
await words("the prime chosen");

// choose the stopped body: the page fills with it; the honest line; its task and what it last said; no line to speak
check("choosing a body", await click(".br", "Vega"));
await sleep(1200);
const vega = await js(`({ head: (document.querySelector('.bodies-room-health') || {}).innerText || '', chosen: (document.querySelector('.br.is-chosen') || {}).innerText || '',
  away: (document.querySelector('.bodies-away-line') || {}).innerText || '', page: (document.querySelector('.bodies-conv') || {}).innerText || '',
  speak: !!document.querySelector('.bodies-talk-foot:not([hidden])') })`);
check("choosing a body fills the page with it", /^Vega/.test(vega.head) && /Vega/.test(vega.chosen), JSON.stringify(vega).slice(0, 200));
check("a body that cannot be reached says so plainly", /not running now|in its own window/i.test(vega.away), vega.away);
// the live block carries the status file's last line (status_lines, newest first, when it carries more)
check("its task and what it last said are shown", /bookshelf page/i.test(vega.page) && /first draft is done/.test(vega.page), vega.page.slice(0, 200));
check("no line to speak to a body that cannot hear", !vega.speak);
check("a stopped body offers Close it", /close it/i.test(await js("document.querySelector('.bodies-room-acts').innerText")));
check("Words and Plain at the head of a terminal body", JSON.stringify(await js("[...document.querySelectorAll('.bodies-seg')].map((b) => b.innerText.trim())")) === '["Words","Plain"]');
await words("a stopped body chosen");

// the dock's agent: its conversation, mounted in place; Words, Plain, Command line
check("the dock's agent is on the rail", await click(".br--dock"));
await sleep(1500);
const dock = await js(`({ mounted: !!document.querySelector('.bodies-talk--dock .dock-pane'), input: !!document.querySelector('.bodies-talk--dock .dock-input'),
  segs: [...document.querySelectorAll('.bodies-seg')].map((b) => b.innerText.trim()), bar: (() => { const b = document.querySelector('.bodies-talk--dock .dock-bar'); return b ? getComputedStyle(b).display : 'none'; })() })`);
check("the dock's agent entry opens its conversation", dock.mounted && dock.input, JSON.stringify(dock));
check("the conversation is in place, never a second bar", dock.bar === "none");
check("Words, Plain and Command line for the dock's agent", JSON.stringify(dock.segs) === '["Words","Plain","Command line"]', JSON.stringify(dock.segs));
await click(".bodies-seg", "Plain"); await sleep(600);
check("Plain shows the same conversation as lines", await js("!!document.querySelector('.bodies-talk--dock .dock-terminal') && document.querySelector('.bodies-seg.is-on').innerText.trim() === 'Plain'"));
check("the choice is kept on this device, not in the record", await js("localStorage.getItem('hud.bodies_view') === '\"plain\"'"));
await click(".bodies-seg", "Words"); await sleep(600);
check("Words again", await js("!document.querySelector('.bodies-talk--dock .dock-terminal') && document.querySelector('.bodies-seg.is-on').innerText.trim() === 'Words'"));
await words("the dock's agent chosen");

// at a glance: the field, behind the link
await click(".bodies-glance-link"); await sleep(1200);
check("At a glance shows the field", await js("!!document.querySelector('.bodies-page .bodies-stage, .bodies-page .bodies-twin-list')"));
check("the health line says the day's total", /Today so far: \$1\.25/.test(await js("(document.querySelector('.bodies-line') || {}).innerText || ''")),
  await js("(document.querySelector('.bodies-line') || {}).innerText || ''"));

// each rail entry: what it spent today, one quiet figure (nothing counted here for these bodies: said so)
const costs = await js("[...document.querySelectorAll('.br .br-cost')].map((x) => x.innerText.trim())");
check("each body on the rail says what it spent today", costs.length >= 2 && costs.every((x) => /today$|^not counted$/.test(x)), JSON.stringify(costs));
check("the figure is set in tabular figures", await js("getComputedStyle(document.querySelector('.br .br-cost')).fontVariantNumeric.includes('tabular-nums')"));

// Task a New Worker: the cost said first, then one tap; an empty task is refused and nothing is sent
await js("(() => { window.__bodyPosts = 0; const f = window.fetch; window.fetch = (u, o) => { if (String(u).includes('/agent/body')) window.__bodyPosts++; return f(u, o); }; return 1; })()");
check("the rail head carries Task a New Worker", await click(".bodies-give-link", "Task a New Worker"));
await sleep(500);
const give = await js(`(() => { const sh = document.querySelector('.sheet'); if (!sh) return null; const cost = sh.querySelector('.bodies-cost-first'); const start = [...sh.querySelectorAll('button')].find((b) => /Start the worker/.test(b.innerText));
  return { cost: cost ? cost.innerText : '', before: !!(cost && start && (cost.compareDocumentPosition(start) & Node.DOCUMENT_POSITION_FOLLOWING)), title: (sh.querySelector('h2') || {}).innerText }; })()`);
check("the sheet says the cost before the tap", give && /week's use/i.test(give.cost) && give.before, JSON.stringify(give));
check("the sheet is named Task a New Worker", give && give.title === "Task a New Worker", give && give.title);
await click(".sheet button", "Start the worker"); await sleep(400);
check("an empty task is refused, in words, and nothing is sent", /Say the task first/.test(await js("(document.querySelector('.bodies-give-status') || {}).innerText || ''")) && (await js("window.__bodyPosts")) === 0);
await js("(() => { const b = [...document.querySelectorAll('.sheet button')].find((x) => /close/i.test(x.innerText)); b && b.click(); return 1; })()");
await words("Task a New Worker");

// the finished body that left a handoff says it waits
await click(".br--archive"); await sleep(800);
check("the finished body with a handoff says a handoff waits", /Rigel[\s\S]*a handoff waits/.test(await js("document.querySelector('.bodies-archive').innerText")));

// ---------------------------------------------------------------- a handoff is one Deal card
await open(LIVE, "", "#/deal");
let found = false;
for (let i = 0; i < 9 && !found; i++) {
  found = /Read Rigel's handoff/.test(await js("document.querySelector('#main').innerText"));
  if (found) break;
  // not in this hand: answer the card in front, then ask for the next hand when it is offered
  if (!(await click(".deal-next button")) && !(await click(".card-options .option"))) break;
  await sleep(900);
}
check("the handoff is one card on the Deal", found);
const ho = await js(`(() => { const c = [...document.querySelectorAll('.card')].find((x) => /Read Rigel's handoff/.test(x.innerText)); return c ? { opts: [...c.querySelectorAll('.option-label')].map((o) => o.innerText.trim()), text: c.innerText } : null; })()`);
check("its options: Read it now, Later today, Archive it", ho && JSON.stringify(ho.opts) === '["Read it now","Later today","Archive it"]', JSON.stringify(ho && ho.opts));
// its minutes are read from the dealt card itself (the face's "n of m" once happened to carry the 4; it is now the count she still has)
const hoMin = await js("import('./state.js').then((m) => { const all = [...((m.store.state.deal || {}).cards || []), ...(((m.store.state.deal || {}).beyond || {}).cards || [])]; const c = all.find((x) => /Rigel/.test(x.title || x.question || '')); return c ? c.minutes : null; })");
check("its minutes are its review_min", hoMin === 4, String(hoMin));
await words("the handoff card");
await js(`(() => { const c = [...document.querySelectorAll('.card')].find((x) => /Read Rigel's handoff/.test(x.innerText)); const b = c && [...c.querySelectorAll('.option')].find((o) => /Read it now/.test(o.innerText)); b && b.click(); return !!b; })()`);
await sleep(7500);    // the undo window passes and the witness is written to the scratch home
await open(LIVE);
await click(".br--archive"); await sleep(800);
check("after the review the finished body says handoff read", /Rigel[\s\S]*handoff read/.test(await js("document.querySelector('.bodies-archive').innerText")));
const served = await (await fetch(`${LIVE}/state`)).json();
check("after the review the card is answered on the Deal", (served.deal.cards || []).some((c) => c.section === "handoff" && c.answered));

// ---------------------------------------------------------------- the phone, 390 × 844
await size(390, 844);
await open(LIVE);
const strip = await js(`(() => { const l = document.querySelector('.bodies-rail-list'); const first = l.querySelector('.br');
  return { flex: getComputedStyle(l).display, first: first.className, wide: document.documentElement.scrollWidth <= innerWidth,
    taskHidden: [...document.querySelectorAll('.br-task')].every((e) => !e.getClientRects().length) }; })()`);
check("the phone: a strip of chips, the prime first", strip.flex === "flex" && /br--prime/.test(strip.first), JSON.stringify(strip));
check("the phone: no horizontal page scroll", strip.wide);
check("the phone: the chips carry names only", strip.taskHidden);
await click(".br", "Vega"); await sleep(1000);
check("the phone: the chosen chip is underlined", await js("(() => { const c = document.querySelector('.br.is-chosen'); return !!c && /Vega/.test(c.innerText) && parseFloat(getComputedStyle(c).borderBottomWidth) >= 2; })()"));
check("the phone: the limits wait behind More", await js("!!document.querySelector('.br--more') && ![...document.querySelectorAll('.bodies-rail-foot')].some((e) => e.getClientRects().length)"));
await words("the phone");

// ---------------------------------------------------------------- no server at all: every terminal body is honest
await size(1440, 900);
await open(LIVE, "&fixture=bodies-well");
await click(".br", "Survey"); await sleep(1200);
check("from a file, a body is in its own window, said plainly", /in its own window/i.test(await js("(document.querySelector('.bodies-away-line') || {}).innerText || ''")));
await words("from a file");

ws.close(); chrome.kill(); serve.kill();
await sleep(500);
try { fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 5 }); } catch { /* Chrome still closing; the folder is its own */ }
if (fails.length && serveErr) console.log(serveErr.slice(-800));
console.log(fails.length ? `bodies room: ${fails.length} failing` : "bodies room: all pass");
process.exit(fails.length ? 1 : 0);
