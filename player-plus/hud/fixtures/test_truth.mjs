// test_truth.mjs: the quiet never lies. Each of five known contradictions, the bar's
// "no placeholder", the schema-word gate on what reaches the screen, the gold on the one owed
// thing only, and the hand answered within a tenth of a second, proven in headless Chrome
// (muted, no sound) against the fixtures that carry each fault's cause.
//
//   node hud/fixtures/test_truth.mjs            (test_strings.py runs it when node and Chrome are here)
//
// A static server on 127.0.0.1 at a port above 9000 serves hud/ read-only; the page reads
// fixtures/<name>.json directly, so no act is written anywhere. Nothing leaves this machine.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import os from "node:os";

const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!fs.existsSync(CHROME)) { console.log("truth: Chrome not found, skipped"); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// the schema words that may never reach the screen (DESIGN-THE-BAR §5 line 17);
// "decision" and "milestone" are allowed, being words a person uses
export const SCHEMA = /\b(events?|holons?|float|anchor(s|ed)?|settle[ds]?|settling|engine|schema|hash(es)?|process(es)?|forge|hooks?|tokens?|payload|jsonl?)\b/i;

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
// a free port above 9000 (other servers may share the machine)
let PORT = 0;
for (let i = 0; i < 20 && !PORT; i++) {
  const p = 9400 + Math.floor(Math.random() * 400);
  PORT = await new Promise((r) => { server.once("error", () => r(0)); server.listen(p, "127.0.0.1", () => r(p)); });
}
const DBG = 9800 + Math.floor(Math.random() * 150);
const prof = fs.mkdtempSync(path.join(process.env.SCRATCH || os.tmpdir(), "truth-chrome-"));
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
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }, { name: "prefers-reduced-motion", value: "reduce" }] });

async function open(fixture, hash = "#/deal", extra = "") {
  errors = [];
  await send("Page.navigate", { url: `http://127.0.0.1:${PORT}/index.html?fixture=${fixture}&theme=night${extra}${hash}` });
  await sleep(1800);
  await js("sessionStorage.clear(); localStorage.clear(); true");
  await send("Page.reload", { ignoreCache: true });
  await sleep(2200);
}
const text = () => js("document.querySelector('#main') ? document.querySelector('#main').innerText : document.body.innerText");

const fails = [];
const check = (name, ok, detail) => { if (!ok) fails.push(`${name}${detail ? ": " + detail : ""}`); console.log(`${ok ? "pass" : "FAIL"}  ${name}${!ok && detail ? " — " + detail : ""}`); };
const common = async (label) => {
  const body = await js("document.body.innerText");
  check(`${label}: no script errors`, errors.length === 0, errors.join(" | "));
  check(`${label}: no missing keys`, !/\[[a-z_]+\.[a-z_.]+\]/.test(body), (body.match(/\[[a-z_]+\.[a-z_.]+\]/) || [])[0]);
  check(`${label}: no horizontal scroll`, await js("document.documentElement.scrollWidth <= innerWidth && [...document.querySelectorAll('#main *')].every((e) => e.getBoundingClientRect().right <= innerWidth + 1 || getComputedStyle(e).position === 'fixed' || !!e.closest('.places, .tabs, .still-frame'))"));
  check(`${label}: no "Not computed"`, !/not computed/i.test(body));
};

// every element lit in the owed gold that is not inside the one owed thing
const GOLD_OUTSIDE = `(() => {
    const probe = document.createElement('i'); probe.className = 'owed'; probe.style.color = 'var(--owed)'; document.body.append(probe);
    const gold = getComputedStyle(probe).color; probe.remove();
    const bad = [];
    for (const e of document.querySelectorAll('#main *, header *')) {
      if (e.closest('.owed, .is-owed') || !e.getClientRects().length) continue;
      const s = getComputedStyle(e);
      if ([s.color, s.borderTopColor, s.backgroundColor, s.outlineColor].includes(gold) && (s.color === gold || s.borderTopWidth !== '0px' || s.backgroundColor === gold)) bad.push(e.className || e.tagName);
    }
    return bad.slice(0, 5);
  })()`;

// 1 · the Deal: schema words, gold only on the owed card, order by stake, one tap within 0.1 s
for (const fx of ["fresh", "stale", "names-hidden", "deal-chain", "deal-rich", "empty", "undealt", "invitation", "large", "unreadable"]) {
  await open(fx);
  await common(`deal ${fx}`);
  const main = await text();
  const hit = main.match(SCHEMA);
  check(`deal ${fx}: no schema word on screen`, !hit, hit && hit[0]);
  const owedOutside = await js(GOLD_OUTSIDE);
  check(`deal ${fx}: gold only on the owed thing`, !owedOutside.length, owedOutside.join(", "));
  const owedCount = await js("document.querySelectorAll('.card--large.owed').length");
  const open1 = await js("document.querySelectorAll('.card--large').length");
  check(`deal ${fx}: one owed card when any is shown`, open1 === 0 ? owedCount === 0 : owedCount === 1, `${owedCount} of ${open1}`);
  if (fx === "undealt") check("undealt: never says below over nothing", !/below/i.test(main), main.slice(0, 120));
  if (fx === "empty") check("empty: rest state is the field and one line", await js("!!document.documentElement.hasAttribute('data-rest') && document.querySelectorAll('#main .deal-rest-line').length === 1 && ![...document.querySelectorAll('#main .stack, #main .whole-pill, #main .card')].some((e) => e.getClientRects().length)"));
  if (fx === "fresh") {
    check("fresh: the past-due gate comes first (least float)", /gate/i.test(await js("document.querySelector('.card--large .card-title').innerText")));
    // the hand: tap the first answer, the settled line paints within a tenth of a second
    await js("document.querySelector('.card--large .option').click(); true");
    await sleep(400);
    const ms = Number(await js("document.documentElement.dataset.dealTapMs"));
    check("fresh: tap to settled paint under 100 ms", ms >= 0 && ms < 100, `${ms} ms`);
    check("fresh: the settled line carries Undo in the flow", await js("!!document.querySelector('.deal-settled .link-btn')"));
    check("fresh: nothing wider than the phone once settled", await js("[...document.querySelectorAll('#main *')].every((e) => e.getBoundingClientRect().right <= innerWidth + 1 || !!e.closest('.still-frame, .deal-settled-text'))"));
    // the card's "n of m" is what she still has, the number "what needs me?" says
    const cc = await js("(document.querySelector('.card-count')||{}).innerText||''");
    check("fresh: the card's count is what she still has (two dealt, one answered: of 1)", /of 1$/.test(cc), cc);
  }
  if (fx === "deal-chain") {
    check("deal-chain: the chain-blocking card reads heavier (weight)", await js("(() => { const c = document.querySelector('.card--large.owed'); return c && c.classList.contains('is-path') && getComputedStyle(c.querySelector('.card-title')).fontWeight >= 500 && !!c.querySelector('.card-stake'); })()"));
    check("deal-chain: the stake says what it blocks and for whom", /waits on this/i.test(await js("(document.querySelector('.card-stake')||{}).innerText||''")));
  }
}

// 1b · the frame: Talk · Agents · More at the foot at every width, every other place behind More, no
// top row; no raw key (DESIGN-TALK.md: the other places sit behind More, the Talk the first place)
for (const [w, h] of [[390, 844], [1440, 900]]) {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: w < 600 ? 2 : 1, mobile: w < 600 });
  for (const hash of ["#/talk", "#/deal", "#/threads", "#/map", "#/chain", "#/room", "#/record", "#/bodies", "#/ledger"]) {
    await open("fresh", hash);
    const body = await js("document.body.innerText");
    const raw = body.match(/\[[a-z_]+\.[A-Za-z0-9_.]+\]/);
    check(`frame ${w} ${hash}: no raw key on screen`, !raw, raw && raw[0]);
    const f = await js(`({ top: [...document.querySelectorAll('.tabs .tab')].filter((e) => e.getClientRects().length).map((e) => e.innerText),
      foot: [...document.querySelectorAll('.places .tab')].filter((e) => e.getClientRects().length).map((e) => e.innerText),
      back: !!document.querySelector('.top .back') })`);
    check(`frame ${w} ${hash}: no top row; Talk, Agents and More at the foot`, f.top.length === 0 && f.foot.length === 3, JSON.stringify(f));
    check(`frame ${w} ${hash}: no Back to the deal`, !f.back);
  }
}
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });

// 1c · one truth: one first everywhere; the opener never names an
// answered card; after an answer the Map, Threads and the Deal agree; the margin and the Deal never
// contradict (the record moved: the Deal says so, never "nothing is dealt")
const firsts = `import('./state.js').then((m) => {
  const st = m.store.state, f = m.read.firstOwed(st);
  const face = document.querySelector('.card--large.owed');
  const dc = face && ((st.deal && st.deal.cards) || []).find((c) => c.id === face.dataset.card);
  const dcard = dc ? m.read.cardOfOwed(st, dc) : null;
  return { map: f ? ((f.card && f.card.id) || f.id) : null, deal: dc ? ((dcard && dcard.id) || dc.id) : null, title: dcard ? dcard.title : null };
})`;
for (const fx of ["fresh", "stale", "deal-chain", "names-hidden", "deal-rich"]) {
  await open(fx);
  const f = await js(firsts);
  check(`${fx}: the Map's first is the Deal's first`, f.map && f.map === f.deal, JSON.stringify(f));
  // answer the first card, then read the opener, the Map and back
  // the as-of never goes backwards: after an answer, and after a reload,
  // the time shown is not earlier than before the answer, nor than the page's clock at the tap
  const asOfMin = `import('./state.js').then((m) => { const x = (document.querySelector('.as-of-btn') || {}).innerText || '';
    const k = x.match(/(\\d{1,2}):(\\d{2})\\s*([AP]M)?/i); if (!k) return null;
    return ((+k[1] % 12) + (k[3] && /p/i.test(k[3]) ? 12 : (k[3] ? 0 : Math.floor(+k[1] / 12) * 12))) * 60 + +k[2]; })`;
  const tapMin = await js("import('./state.js').then((m) => { const d = m.fmt.now(); return d.getHours() * 60 + d.getMinutes(); })");
  const before = await js(asOfMin);
  await js("document.querySelector('.card--large.owed .option').click(); true");
  await sleep(500);
  const after = await js(asOfMin);
  const opener = await js("(document.querySelector('.deal-line') || {}).innerText || ''");
  const word = (f.title || "").toLowerCase().split(/\s+/).filter((w) => w.length > 4).slice(0, 2);
  check(`${fx}: the opener never names the answered card`, !word.length || !word.every((w) => opener.toLowerCase().includes(w)), opener);
  check(`${fx}: the answer stays in sight as Done`, /done/i.test(await js("(document.querySelector('.deal-settled') || {}).innerText || ''")));
  // the by-when word comes from the first card's own by-when against the clock, never a default
  const due = await js("import('./state.js').then((m) => { const f = m.read.firstOwed(m.store.state); const d = f && ((f.card && f.card.by) || f.due); return d ? { by: m.fmt.by(d), today: m.fmt.daysBetween(m.fmt.now(), m.fmt.date(d)) === 0 } : null; })");
  check(`${fx}: the opener's by-when is the card's own`, !due || opener.includes(due.by), `${opener} / ${due && due.by}`);
  check(`${fx}: never "today" of a thing not due today`, !/\btoday\b/i.test(opener) || (due && due.today), opener);
  await js("location.hash = '#/map'; true"); await sleep(1500);
  const f2 = await js(firsts);
  check(`${fx}: the Map no longer leads with the answered card`, f2.map !== f.map, JSON.stringify(f2));
  const mapLine = await js("(document.querySelector('.map-breath') || {}).innerText || ''");
  const w0 = (x) => (x.trim().split(/\s+/)[0] || "").toLowerCase();
  check(`${fx}: after the act the Deal's count is the Map's count`, w0(opener) === w0(mapLine) || (/^nothing/i.test(mapLine) && !opener), `${opener} | ${mapLine}`);
  await js("location.hash = '#/deal'; true"); await send("Page.reload", { ignoreCache: true }); await sleep(2200);
  const reloaded = await js(asOfMin);
  check(`${fx}: after an answer the as-of is not earlier than before it, nor than the act, nor after a reload`,
    after != null && (before == null || after >= before) && after >= tapMin && reloaded != null && reloaded >= after,
    `before ${before} · after ${after} · reloaded ${reloaded} · act ${tapMin}`);
}
// 1d · the next hand (there is a way to deal the next most important things): on deal-rich, no act while the hand is open; after the five are answered,
// one act deals the next hand, fitted to the same minutes; the card the dealer ranked sixth leads,
// counted in its own hand; the opener says the true count of what is owed; nothing else is lit
{
  const rich = JSON.parse(fs.readFileSync(path.join(HUD, "fixtures", "deal-rich.json"), "utf8"));
  const rest = rich.deal.beyond.cards, avail = rich.deal.minutes_available;
  const fit = (cs) => { const hand = []; let u = 0; for (const c of cs) { if (hand.length >= 5 || (u + c.minutes > avail && hand.length)) break; hand.push(c); u += c.minutes; } return hand; };
  const hand2 = fit(rest), left = rest.length - hand2.length;
  await open("deal-rich");
  check("deal-rich: no next-hand act while the hand is open", !(await js("!!document.querySelector('.deal-next')")));
  for (let i = 0; i < rich.deal.cards.length; i++) {
    await js("(() => { const o = document.querySelector('.card--large .option'); if (o) o.click(); return true; })()");
    await sleep(400);
  }
  const words = await js(`import('./state.js').then((m) => ({ next: m.fmt.number(${hand2.length}, true), left: m.fmt.number(${left}) }))`);
  const act = await js("[...document.querySelectorAll('#main .deal-next button')].map((b) => b.innerText.trim())");
  check("deal-rich: after the five, one act deals the next hand", act.length === 1 && act[0] === `Deal the next ${words.next}`, JSON.stringify(act));
  const restLine = await js("(document.querySelector('#main .deal-next-rest') || {}).innerText || ''");
  check("deal-rich: what still waits is said once, in dust", left ? restLine === `${words.left} more can wait for another day.` : !restLine, restLine);
  check("deal-rich: the played line does not repeat the count", !/more can wait/.test(await js("(document.querySelector('#main .deal-rest-line') || {}).innerText || ''")));
  const goldPlayed = await js(GOLD_OUTSIDE);
  check("deal-rich: the act is not gold", !goldPlayed.length, goldPlayed.join(", "));
  await js("document.querySelector('#main .deal-next button').click(); true");
  await sleep(900);
  const first = await js("(document.querySelector('.card--large .card-title') || {}).innerText || ''");
  check("deal-rich: the next hand leads with the card ranked sixth", first.trim() === rest[0].question, first);
  check("deal-rich: the next hand is counted in itself", new RegExp(`1 of ${hand2.length}\\b`).test(await js("(document.querySelector('.card-count') || {}).innerText || ''")),
    await js("(document.querySelector('.card-count') || {}).innerText || ''"));
  const told = await js("import('./state.js').then((m) => { const n = m.read.owedByStake(m.store.state).length; return { n, word: m.fmt.number(n), line: (document.querySelector('.deal-line') || {}).innerText || '' }; })");
  check("deal-rich: the opener says the true count of owed things", told.n > 0 && told.line.startsWith(told.word + " "), JSON.stringify(told));
  check("deal-rich: one owed card in the next hand", await js("document.querySelectorAll('.card--large.owed').length") === 1);
  const goldNext = await js(GOLD_OUTSIDE);
  check("deal-rich: gold only on the owed thing in the next hand", !goldNext.length, goldNext.join(", "));
  const hit = (await text()).match(SCHEMA);
  check("deal-rich: no schema word in the next hand", !hit, hit && hit[0]);
  await common("deal-rich next hand");
}

// 1e · the one shape (DESIGN-ROOM §10, a proposal): the door asks the posture first and nothing
// else; the part is said in her voice; the great room shows its proposals; the switch shows only to
// the facilitator; the vote counts "of"; the close asks confirmation and names the curing day; no
// schema word; gold nowhere but the one owed thing
{
  const shapeOf = (fx) => { const st = JSON.parse(fs.readFileSync(path.join(HUD, "fixtures", fx + ".json"), "utf8")); return Object.values(st.rooms)[0].shape; };
  const NOT_SAID = /\b(phase|state machine|engine|tally|facilitator's switch)\b/i;
  for (const fx of ["room-shape-lobby", "room-shape-great", "room-shape-vote", "room-shape-vote-facilitator", "room-shape-writing", "room-shape-reflect", "room-shape-close"]) {
    await open(fx, "#/room");
    await common(fx);
    const main = await text();
    const hit = main.match(SCHEMA) || main.match(NOT_SAID);
    check(`${fx}: no schema word on screen`, !hit, hit && hit[0]);
    const gold = await js(GOLD_OUTSIDE);
    check(`${fx}: gold only on the owed thing`, !gold.length, gold.join(", "));
    check(`${fx}: at most one owed thing`, (await js("document.querySelectorAll('#main .owed').length")) <= 1);
    const sh = shapeOf(fx);
    const sw = await js("document.querySelectorAll('#main .shape-switch').length");
    if (fx === "room-shape-lobby") {
      check("shape lobby: the door asks the posture first", /This space meets under Chatham House\./.test(main) && (await js("!!document.querySelector('.shape-door .owed .pill.primary')")), main.slice(0, 160));
      check("shape lobby: nothing else of the room until then", !(await js("!!document.querySelector('.shape-part, .shape-body, .shape-proposal')")));
      await js("document.querySelector('.shape-door .pill.primary').click(); true"); await sleep(500);
      await js("(document.querySelector('.shape-door .pill.quiet') || { click() {} }).click(); true"); await sleep(600);
      check("shape lobby: after agreeing, the lobby is said", /^The lobby\.$/.test(await js("(document.querySelector('.shape-part') || {}).innerText || ''")));
    } else {
      check(`${fx}: the part is said`, (await js("(document.querySelector('.shape-part') || {}).innerText || ''")).length > 0 && !!(await js("(document.querySelector('.shape-voice') || {}).innerText || ''")));
    }
    if (fx === "room-shape-great") {
      check("shape great: the part is said in her voice", /The great room\./.test(main) && /Anyone may propose\. The facilitator opens the vote when the circle is ready\./.test(main));
      const n = await js("document.querySelectorAll('#main .shape-proposal').length");
      check("shape great: every proposal shows as a card", n === sh.proposals.length && n > 0, `${n} of ${sh.proposals.length}`);
      check("shape great: anyone present may propose", (await js("[...document.querySelectorAll('#main .shape-acts .pill')].map((b) => b.innerText.trim())")).includes("Propose"));
    }
    if (fx === "room-shape-vote") {
      check("shape vote: the switch is not shown to anyone but the facilitator", sw === 0, `${sw}`);
      const words = await js(`import('./state.js').then((m) => ({ choose: m.fmt.number(${sh.vote.rule.choose}, true), total: m.fmt.number(${sh.proposals.length}, true) }))`);
      const title = await js("(document.querySelector('.shape-vote .card-title') || {}).innerText || ''");
      check("shape vote: the vote counts of", title === `Choose ${words.choose} of ${words.total}.`, title);
      check("shape vote: her vote is the owed thing", await js("!!document.querySelector('.shape-vote.owed')"));
      for (const i of [0, 1]) { await js(`document.querySelectorAll('.shape-tick')[${i}].click(); true`); await sleep(200); }
      check("shape vote: the ticks count of the rule", /^Two of three chosen\.$/.test(await js("(document.querySelector('.shape-vote .card-options') || {}).previousElementSibling.innerText")));
    }
    if (fx === "room-shape-vote-facilitator") check("shape vote: the facilitator sees the one switch", sw === 1 && /Close the vote/.test(main), `${sw}`);
    if (fx === "room-shape-writing") {
      const n = await js("document.querySelectorAll('#main .shape-writeup').length");
      check("shape writing: the chosen as cards with holders", n === sh.vote.chosen.length && (await js("document.querySelectorAll('#main .shape-writeup .holder-chip').length")) === n);
    }
    if (fx === "room-shape-close") {
      const day = await js(`import('./state.js').then((m) => m.fmt.dayName(m.fmt.date(${JSON.stringify(sh.posture.cure_until)})))`);
      check("shape close: the one act is the confirmation", (await js("(document.querySelector('.shape-confirm.owed .pill.primary') || {}).innerText || ''")).trim() === "Confirm the posture you agreed to");
      check("shape close: the curing day is said in dust", (await js("(document.querySelector('.shape-confirm .dust') || {}).innerText || ''")) === `You may change your mind until ${day}.`, day);
    }
    if (fx !== "room-shape-vote-facilitator" && fx !== "room-shape-vote") check(`${fx}: no switch for one who does not facilitate`, sw === 0);
  }
}

await open("agent-wrote");
const aw = await text();
check("agent-wrote: the Deal says the record moved, never 'not dealt'", /just wrote/i.test(aw) && !/not dealt/i.test(aw), aw.slice(0, 160));
await open("fresh", "#/threads");
const ta = await js("!!document.querySelector('.conv2-answer textarea, .conv2-answer input')");
if (ta) {
  await js(`(() => { const i = document.querySelector('.conv2-answer textarea, .conv2-answer input'); i.value = 'I can bring the soup.'; i.dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('.conv2-send').click(); return true; })()`);
  await sleep(700);
  const tx = await js(`({ top: (document.querySelector('.threads2-sentence') || {}).innerText || '',
    heads: [...document.querySelectorAll('.threads2-head')].map((e) => e.innerText.trim().toLowerCase()) })`);
  check("threads: never 'nobody is waiting' above 'waiting on you'", !(/nobody is waiting/i.test(tx.top) && tx.heads.includes("waiting on you")), JSON.stringify(tx));
}

// 2 · the contradictions, each where its cause lives
await open("truth", "#/chain");
const spareRows = await js(`[...document.querySelectorAll('.chain-spare-title')].filter((h) => /with days to spare/i.test(h.innerText)).map((h) => h.nextElementSibling ? h.nextElementSibling.innerText : '').join(' | ')`);
check("chain: nothing past or late under 'with days to spare'", !/past|late/i.test(spareRows || ""), spareRows);

const CELL = JSON.parse(fs.readFileSync(path.join(HUD, "fixtures", "truth.json"), "utf8")).holons.find((x) => x.kind === "cell").id;
await open("truth", "#/board/" + CELL);
const boardFeet = await js(`[...document.querySelectorAll('.card-foot')].map((f) => f.innerText)`) || [];
check("board: no foot says both past and to spare", !boardFeet.some((x) => /past|late/i.test(x) && /to spare/i.test(x)), boardFeet.find((x) => /past/.test(x) && /spare/.test(x)));

await open("truth", "#/turn");
const turn = await text();
check("turn: kept-of-all never stands above a late gap unsaid", !(/3 of 3/.test(turn) && /late/i.test(turn)) || /kept late/i.test(turn), turn.slice(0, 200));

await open("truth", "#/room");
const room = await text();
const said = (room.match(/The hall is the biggest cost, so I would start there\./g) || []).length;
check("room: a line said twice in thirty seconds shows once", said <= 1, `${said} times`);

ws.close(); chrome.kill(); server.close();
await sleep(500);
try { fs.rmSync(prof, { recursive: true, force: true, maxRetries: 5 }); } catch { /* Chrome still closing; the scratch folder is its own */ }
console.log(fails.length ? `truth: ${fails.length} failing` : "truth: all pass");
process.exit(fails.length ? 1 : 0);
