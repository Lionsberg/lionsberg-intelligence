// test_talk_place.mjs: the Talk (DESIGN-TALK.md, proposal), proven in headless muted Chrome.
//
//   node hud/fixtures/test_talk_place.mjs        (test_strings.py runs it when node and Chrome are here)
//
// A throwaway house under the system's temporary folder: one worker at work (Vega), one that came
// back with a handoff (Rigel), a desk file, and an agents file whose one agent is the stand-in
// (fake_agent.py). serve.py serves deal-rich on 127.0.0.1 at a port of its own for most of the proof,
// and a second serve.py serves `empty` for the rest state. Proves, each numbered as the
// brief numbers them: 1 one voice (a welcome on a first
// sitting, no count, no question on load; the page context sent with every line); 2 the question is
// a turn inside the stream, nothing cut off, Send inside the gutter; 3 a typed answer settles as a
// tap would; 4 no swap while she types, the next question only after the quiet; 5 the apparatus's
// words off her screen, More under twelve controls; 6 Stop while a turn runs, "stop" ends it, a
// person one tap from her name; 7 one count only when asked, the grammar of what waits; 8 the
// keepsake; 9 presence; 10 an ask never covers the question; 11 the same foot everywhere; 12 one
// gold; 18 "what needs me?" answered by the page. And, kept from the first cut: the frame, "who is
// working on what", the worker proposed and started on her tap, the return, the rest, the
// ten-minute offer. Then, each as the second brief numbers it, R1 to R13: asks are turns in the stream and No takes nothing away; local answers exact and
// single; every agent's asks in the Talk; voice from the first screen; the words; keepsakes in the
// record; nothing before the welcome on a fresh device; a reload restores the turns as turns; one
// first everywhere; the question stays through her turn; one head; no bare glyph. Nothing is sent to
// any worker beyond its own folder; nothing leaves this machine; no sound.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import net from "node:net";
import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!fs.existsSync(CHROME)) { console.log("talk: Chrome not found, skipped"); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SCHEMA = /\b(events?|holons?|float|anchor(s|ed)?|settle[ds]?|settling|engine|schema|hash(es)?|process(es)?|forge|hooks?|tokens?|payload|jsonl?)\b/i;
const S = JSON.parse(fs.readFileSync(path.join(HUD, "strings.json"), "utf8"));
// the apparatus's words that never reach her (item 5); the places keep their proper names behind More
const APPARATUS = /\b(Cell|deck|desk|record|Deal|Yes, for this kind|Terminal view|Command line|models?|Layouts|tokens?|session|fixture)\b/;

// ---------------------------------------------------------------- the throwaway house
const tmp = fs.mkdtempSync(path.join(process.env.SCRATCH || os.tmpdir(), "talk-place-"));
const house = path.join(tmp, "house"), bg = path.join(house, "bg");
for (const d of [path.join(bg, "bg-Vega"), path.join(bg, "bg-Rigel"), path.join(house, "desk"), path.join(tmp, "sessions"), path.join(tmp, "registry"), path.join(tmp, "hq"), path.join(tmp, "hq2")]) fs.mkdirSync(d, { recursive: true });
fs.writeFileSync(path.join(bg, "bg-Vega", "RUNNING"), `pid: ${process.pid}\nstart: 2026-10-25T13:00Z\n`);
fs.writeFileSync(path.join(bg, "bg-Vega", "task.md"), "# Draw the bookshelf page\n");
fs.writeFileSync(path.join(bg, "bg-Vega", "status.md"), "10:40 the first draft is done\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "DONE"), "done\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "task.md"), "# Gather the readings\n");
fs.writeFileSync(path.join(bg, "bg-Rigel", "handoff.md"), "What was done.\n\nreview_min: 4\n");
const desk = path.join(house, "desk", "on-deck.md");
fs.writeFileSync(desk, "holder: laptop\n");
const agents = path.join(tmp, "agents.json");
fs.writeFileSync(agents, JSON.stringify({ agents: [{ id: "yours", name: "Wren", of: "person:player", kind: "harness", actor: "agent:player-agent",
  command: ["python3", "-I", path.join(HUD, "fixtures", "fake_agent.py")], cwd: tmp }] }));

const free = () => new Promise((res) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
async function serve(fixture, hq, house = true) {
  const port = await free();
  const p = spawn("python3", ["-I", path.join(HUD, "serve.py"), "--fixture", fixture, "--port", String(port), "--agents", agents,
    ...(house ? ["--bg", bg, "--desk", desk] : []), "--sessions", path.join(tmp, "sessions"), "--harness-sessions", path.join(tmp, "registry"), "--hq", hq],
  { cwd: HUD, stdio: ["ignore", "ignore", "pipe"] });
  p.err = ""; p.stderr.on("data", (d) => { p.err += d; });
  for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${port}/token`); if (r.ok) break; } catch { /* not yet */ } await sleep(150); }
  p.base = `http://127.0.0.1:${port}`;
  return p;
}
const rich = await serve("deal-rich", path.join(tmp, "hq"));
const empty = await serve("empty", path.join(tmp, "hq2"), false);   // no workers: the rest is the rest
// whatever happens, this proof stops what it started: its servers, its Chrome, and the agent hosts under its folder
let chrome = null;
const stopMine = () => { for (const p of [rich, empty, chrome]) { try { if (p && p.exitCode == null) p.kill(); } catch { /* gone */ } } try { execFileSync("pkill", ["-f", tmp]); } catch { /* none left */ } };
process.on("exit", stopMine);
for (const ev of ["uncaughtException", "unhandledRejection"]) process.on(ev, (e) => { console.error(e); stopMine(); process.exit(1); });
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => { stopMine(); process.exit(130); });

// ---------------------------------------------------------------- Chrome, muted
const DBG = await free();
const prof = fs.mkdtempSync(path.join(tmp, "chrome-"));
chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${DBG}`, "--mute-audio", "--no-first-run",
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
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error" && !/favicon|\/voice/.test(msg.params.entry.url || "")) errors.push(msg.params.entry.text + " " + (msg.params.entry.url || ""));
});
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiters.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); return r.result?.result?.value; };
await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
// never a sound on this computer: every page muted, and the browser's own speech stubbed before any script
// runs (speechSynthesis in headless Chrome speaks through the system voice; --mute-audio does not stop it)
await send("Page.addScriptToEvaluateOnNewDocument", { source: `window.__lionsbergMuted = true;
  try { const quiet = { speak() {}, cancel() {}, pause() {}, resume() {}, getVoices() { return []; }, speaking: false, pending: false, paused: false, addEventListener() {}, removeEventListener() {} };
    Object.defineProperty(window, "speechSynthesis", { value: quiet, configurable: true }); } catch {}` });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }, { name: "prefers-reduced-motion", value: "reduce" }] });
const size = (w, h) => send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: w < 600 ? 2 : 1, mobile: w < 600 });
let nav = 0;
async function open(base, hash = "#/talk", seed = "") {
  errors = [];
  await send("Page.navigate", { url: `${base}/index.html?theme=night&probe=1&muted&n=${++nav}${hash}` });
  await sleep(1200);
  await js(`sessionStorage.clear(); localStorage.clear(); ${seed}; true`);
  await send("Page.reload", { ignoreCache: true });
  await sleep(2200);
}
const say = async (text) => {
  await js("(() => { const i = document.querySelector('.talk .dock-input'); i.focus(); i.value = ''; return true; })()");
  await send("Input.insertText", { text });
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await sleep(600);
};
// an answer said in her words (the Talk has nothing to tap)
const tapWord = async (w) => { await say(w); await sleep(300); };
const fails = [];
const check = (name, ok, detail) => { if (!ok) fails.push(`${name}${detail ? ": " + detail : ""}`); console.log(`${ok ? "pass" : "FAIL"}  ${name}${!ok && detail ? " — " + detail : ""}`); };
const GOLD_OUTSIDE = `(() => {
    const probe = document.createElement('i'); probe.style.color = 'var(--owed)'; document.body.append(probe);
    const gold = getComputedStyle(probe).color; probe.remove();
    const bad = [];
    for (const e of document.querySelectorAll('body *')) {
      if (e.closest('.owed') || !e.getClientRects().length) continue;
      const s = getComputedStyle(e);
      if (s.color === gold || s.backgroundColor === gold || (s.borderTopWidth !== '0px' && s.borderTopColor === gold) || (s.borderLeftWidth !== '0px' && s.borderLeftColor === gold)) bad.push(e.className || e.tagName);
    }
    return { bad: bad.slice(0, 5), owed: document.querySelectorAll('.owed').length };
  })()`;
const words = async (label) => {
  const text = await js("document.body.innerText");
  const hit = text.match(SCHEMA);
  check(`${label}: no schema word on screen`, !hit, hit && hit[0]);
  check(`${label}: no raw key`, !/\[[a-z_]+\.[A-Za-z0-9_.]+\]/.test(text), (text.match(/\[[a-z_]+\.[A-Za-z0-9_.]+\]/) || [])[0]);
  check(`${label}: no contraction`, !/\b[A-Za-z]+n't\b/.test(text));
  const g = await js(GOLD_OUTSIDE);
  check(`${label}: gold only on the one owed thing`, !g.bad.length && g.owed <= 1, JSON.stringify(g));
  check(`${label}: no script errors`, errors.length === 0, errors.join(" | "));
};
const oneScreen = async (label) => {
  const f = await js(`(() => { const q = document.querySelector('.talk-q') || document.querySelector('.talk-now'); const i = document.querySelector('.talk .dock-input');
    const r = (e) => e ? e.getBoundingClientRect() : null;
    const sb = document.querySelector('.talk .dock-send');
    return { sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, w: innerWidth, h: innerHeight,
      hasQ: !!document.querySelector('.talk-q'), send: sb ? r(sb).right : 0,
      q: !!document.querySelector('.talk-q') && r(document.querySelector('.talk-q')).top < innerHeight && r(document.querySelector('.talk-q')).bottom > 0, input: i && r(i).bottom <= innerHeight + 1,
      wide: [...document.querySelectorAll('.talk *')].filter((e) => e.getClientRects().length && !e.closest('.talk-scene')).some((e) => e.getBoundingClientRect().right > innerWidth + 1) }; })()`);
  check(`${label}: no horizontal scroll`, f.sw <= f.w && !f.wide, JSON.stringify(f));
  check(`${label}: one screen, no page scroll`, f.sh <= f.h + 1, JSON.stringify(f));
  check(`${label}: the line to speak is in view${f.hasQ ? ", the question too" : ""}`, (!f.hasQ || f.q) && f.input, JSON.stringify(f));
  check(`2 ${label}: Send inside the gutter`, f.send <= f.w - 15, JSON.stringify(f));
};
const dealOpen = "import('./deal.js').then((m) => m.dealt(window.__hudProbe.makeCtx({ slot: 'main' })).open.map((c) => c.id))";

// the apparatus's words on the Talk's own surface: card text, her and your words are the record's and stay out of the sweep
const sweep = async (label) => {
  const text = await js(`(() => { const c = document.querySelector('.talk').cloneNode(true);
    c.querySelectorAll('.talk-q-words, .talk-q-why, .talk-chip, .talk-quick, .dock-ask-words, .talk-ask-words, .talk-settled-q, .talk-settled-line, .dock-letter, .dock-turn--you, .dock-ask, .talk-scene').forEach((e) => e.remove());
    return c.innerText; })()`);
  const hit = text.match(APPARATUS);
  check(`5 ${label}: none of the apparatus's words`, !hit, hit && hit[0]);
};
// ---------------------------------------------------------------- the frame, at every width (11: the same foot everywhere)
for (const [w, h] of [[390, 844], [1440, 900]]) {
  await size(w, h);
  for (const hash of ["#/talk", "#/deal", "#/map"]) {
    await open(rich.base, hash);
    const f = await js(`({ top: [...document.querySelectorAll('.tabs .tab, header.top .wordmark')].filter((e) => e.getClientRects().length).length,
      foot: [...document.querySelectorAll('.places .tab')].filter((e) => e.getClientRects().length).map((e) => e.innerText.trim()),
      bar: [...document.querySelectorAll('.dock-bar')].filter((e) => e.getClientRects().length).length,
      dock: !!document.querySelector('#dock') && !!document.querySelector('#dock .dock-pane') && !!document.querySelector('#dock .dock-pane').getClientRects().length && location.hash === '#/talk' })`);
    check(`11 frame ${w} ${hash}: Talk · Agents · More at the foot, and nothing else there`, JSON.stringify(f.foot) === JSON.stringify([S["places.talk"], S["places.bodies"], S["app.more"]]) && f.bar === 0, JSON.stringify(f));
    if (hash === "#/talk") {
      check(`frame ${w}: no top row on the Talk`, f.top === 0, JSON.stringify(f));
      check(`frame ${w}: one conversation on screen`, !f.dock);
    }
  }
}
await size(390, 844);
await open(rich.base, "");
check("no address opens the Talk", await js("!!document.querySelector('.talk') && location.hash === ''"));


// ---------------------------------------------------------------- the pure readings
const pure = await js(`Promise.all([import('./talk-place.js'), import('./dock-card.js')]).then(([m, dc]) => {
  const tt = (k, v) => ({ "talk_place.line.blocks": "{first} waits on it{then}." })[k].replace(/\\{(\\w+)\\}/g, (_, x) => v[x]);
  const o = ["Thursday evening", "Saturday morning", "Ask the cell"];
  const items = [1, 2, 3, 4].map((i) => ({ at: i, data: { kind: "settled" } })).concat([{ at: 5, data: { kind: "person" } }]);
  const fm = m.foldMarked(items), fm3 = m.foldMarked(items.slice(1));
  return {
    grammar: m.waitsOnIt(tt, "Booking the hall, then the gathering"),
    plain: m.waitsOnIt(tt, "The safety of the lane"),
    second: m.matchOption("the second", o, "Saturday morning"), two: m.matchOption("2", o), saturday: m.matchOption("Saturday", o),
    yes: m.matchOption("yes", o, "Saturday morning"), whole: m.matchOption("saturday morning please", o),
    none: m.matchOption("I am not sure, what do you think?", o), long: m.matchOption("Thursday evening works but let me ask everyone first please and then", o),
    needs: (m.intentOf("what needs me?") || {}).kind, blocked: m.intentOf("What’s blocked?"), todo: m.intentOf("what do I need to do right now?"),
    who: (m.intentOf("who is working on what?") || {}).kind,
    ask: m.endSentence("Is it on track?"), stop: m.endSentence("The tables are a day late"),
    fold: [fm.count, fm.foldAt, fm.hidden.size], fold3: fm3.count,
    path: dc.noPaths("Read /private/tmp/x/-Users-someone/ice-demo/skills/foreground-background/SKILL.md"),
    front: dc.withoutFrontMatter("---\\nname: go-slowly\\ntype: feedback\\n---\\nShe asked to go slowly."),
    step: dc.plainStep("Write memory/we-go-slowly.md\\n+ **Why:** she asked to go slowly"), stepPlain: dc.plainStep("I will remember: we go slowly, one thing at a time."),
    stepRaw: dc.plainStep({ title: "Write memory/x.md", input: { file_path: "/a/b/memory/x.md" } }),
    draft: dc.plainLines("---\\ntitle: x\\n---\\n# Harvest notes\\n\\n- **Beans**: forty jars, see [the list](/Users/someone/ice-demo/list.md)\\n- *Squash* stored in \\x60the barn\\x60"),
  }; })`);
check("T23 a worker's draft is read as plain lines: no #, *, **, `, front matter or address", pure.draft === "Harvest notes\n\nBeans: forty jars, see the list\nSquash stored in the barn", JSON.stringify(pure.draft));
check("T2 \"The exact step\" is a plain sentence: never a path, a + or **", !/[\/+*]|\.md\b/.test(pure.step) && pure.stepPlain === "I will remember: we go slowly, one thing at a time." && pure.stepRaw === "", JSON.stringify([pure.step, pure.stepRaw]));
check("7 what waits on it, in a sentence that parses", pure.grammar === "Booking the hall waits on it, then the gathering." && pure.plain === "The safety of the lane waits on it.", JSON.stringify(pure));
check("3 an answer by its place, its number, its words, or yes for the suggested one", pure.second === 1 && pure.two === 1 && pure.saturday === 1 && pure.yes === 1 && pure.whole === 1, JSON.stringify(pure));
check("3 a line that names no option is not taken for one", pure.none === -1 && pure.long === -1, JSON.stringify(pure));
check("18 \"what needs me?\" is the page's to answer", pure.needs === "needs" && pure.who === "who", JSON.stringify(pure));
check("R2 \"what’s blocked?\" and \"what do I need to do?\" are the agent's, with no line from the page", pure.blocked === null && pure.todo === null, JSON.stringify(pure));
check("R5 a question keeps its question mark; a statement gets its full stop", pure.ask === "Is it on track?" && pure.stop === "The tables are a day late.", JSON.stringify(pure));
check("R2 more than three settled lines: all but the newest fold into one", JSON.stringify(pure.fold) === JSON.stringify([3, 1, 3]) && pure.fold3 === 0, JSON.stringify(pure));
check("R5 the exact step never shows a path, only the step's words", pure.path === "Read SKILL.md", pure.path);
check("R5 a file's front matter never reaches her", pure.front === "She asked to go slowly.", pure.front);

// ---------------------------------------------------------------- 1 · a first sitting: a welcome, no count, no question on load
await open(rich.base);
const arrival = await js(`({ line: document.querySelector('.talk-line').innerText, q: !!document.querySelector('.talk-q'), talk: window.__talk,
  ready: !!document.querySelector('.talk-line .talk-ready') })`);
check("1 a first sitting opens on a welcome by the time of day", /^Good (morning|afternoon|evening)[.,]/.test(arrival.line), arrival.line);
check("P3 the welcome is a greeting only: her name, never what waits, nothing to tap", /I am Wren\.$/.test(arrival.line) && !arrival.ready && !/wait/i.test(arrival.line), arrival.line);
check("T4 a placeholder name is no name: the welcome never says \"Player\"", !/\bPlayer\b/.test(arrival.line), arrival.line);
check("1 the welcome carries no count", !/\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\b/i.test(arrival.line) && !/things wait/i.test(arrival.line), arrival.line);
check("1 no question on the load of a first sitting", !arrival.q && arrival.talk && arrival.talk.welcome === true, JSON.stringify(arrival));
check("no agent is woken by the page load", (await js("performance.getEntriesByType('resource').filter((e) => /agent\\/(wake|say)/.test(e.name)).length")) === 0);
await words("welcome 390");
await sweep("welcome 390");
await oneScreen("welcome 390");
// R4 · voice from the first screen: the microphone beside Send, the switch in the head, one name
const voice = await js(`(async () => { await new Promise((r) => setTimeout(r, 400));
  const m = document.querySelector('.talk .dock-mic'), s = document.querySelector('.talk .dock-send');
  return { mic: !!m && !m.hidden && !!m.getClientRects().length, beside: !!m && m.nextElementSibling === s, sr: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    mode: !!document.querySelector('.talk-head .talk-voice .dock-voice-mode'), door: document.querySelector('.talk-door').innerText.trim(),
    ph: document.querySelector('.talk .dock-input').placeholder, stage: (document.querySelector('.talk .dock-voice-stage-name') || {}).textContent || '' }; })()`);
check("R4 the microphone sits beside Send from the first screen", !voice.sr || (voice.mic && voice.beside), JSON.stringify(voice));
check("R4 the Voice mode switch is in the head", !voice.sr || voice.mode, JSON.stringify(voice));
check("T6 her name is remembered on this device, so no frame shows a second face", (await js("JSON.parse(localStorage.getItem('hud.agent_name') || 'null')")) === "Wren" && !/your agent/i.test(voice.door), JSON.stringify(voice));
check("R4 one name in every head: the door, the line to speak, voice mode's stage", /^wren$/i.test(voice.door) && voice.ph === "Talk to Wren" && (!voice.stage || voice.stage === "Wren"), JSON.stringify(voice));
if (voice.mic) {
  await js("(() => { const m = document.querySelector('.talk .dock-mic'); m.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 1 })); m.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 1 })); return true; })()");
  await sleep(500);
  const sheet = await js("document.querySelector('.sheet') ? document.querySelector('.sheet').innerText : ''");
  check("R4 the first tap asks \"May I listen?\", with the honest line about the browser's maker", sheet.includes(S["dock.voice.ask_title"]) && sheet.includes(S["dock.voice.vendor_warn"]) && sheet.includes(S["dock.first.words"]), sheet.slice(0, 300));
  check("R4 nothing listened before the yes", await js("!document.querySelector('.talk .dock-mic.is-listening')"));
  await js("[...document.querySelectorAll('.sheet button')].find((b) => b.innerText.trim() === " + JSON.stringify(S["dock.voice.ask_no"]) + ").click(); true"); await sleep(300);
}

// a tap on her sentence brings the first question, inside the stream: the same first the Deal names (R9)
const deck = await js(dealOpen);
// `owed` is the one count the page says (ec1829f: the state's owed list, read.owedByStake, as the Deal's briefing reads it)
const OL = "import('./deal.js').then((m) => { const c = window.__hudProbe.makeCtx({ slot: 'main' }); const ol = m.owedLine(c); return { count: ol.count, owed: c.read.owedByStake(c.state).length, card: ol.card && ol.card.id, title: ol.title }; })";
// "One thing first: …. Five more when you want them." → { first, more } (more: the number word as a digit; 0 when none is said)
const needsParts = (text) => { const m = /\b([A-Z][a-z]+) more when you want (?:them|it)\.$/.exec(String(text || "").trim()); const i = m ? S.numbers.indexOf(m[1]) : -1;
  return { first: /^One thing( first)?[:.]/.test(String(text || "")), more: m ? (i >= 0 ? i : Number(m[1])) : 0 }; };
const ol0 = await js(OL);
check("P3 nothing is dealt on load", !(await js("!!document.querySelector('.talk-q')")));
await say("deal me"); await sleep(300);
const inStream = await js(`(() => { const q = document.querySelector('.talk-q'); const sc = document.querySelector('.talk .dock-scroll');
  return { q: q && q.dataset.card, inside: !!(q && sc && sc.contains(q)), head: !!(sc && sc.contains(document.querySelector('.talk-head'))) }; })()`);
check("1 a tap on \"one thing waits\" brings the first question", !!inStream.q && deck.includes(inStream.q), JSON.stringify(inStream));
check("R9 the Talk's question is the first the owed line names (the Deal's own first)", inStream.q === ol0.card, JSON.stringify([inStream.q, ol0]));
check("2 the question is a turn inside the conversation stream", inStream.inside, JSON.stringify(inStream));
check("2 the stream is the page: the head scrolls with it", inStream.head, JSON.stringify(inStream));
const qTop = await js("(document.querySelector('.talk-q .talk-q-count') || {}).innerText || ''");
check("T16 the welcome's \"one thing\" is made true at the tap: the question says \"1 of n\" when more wait", ol0.owed <= 1 ? qTop === "" : qTop === `1 of ${ol0.owed}`, JSON.stringify([qTop, ol0.owed]));
const qw = await js(`(() => { const q = document.querySelector('.talk-q'); return { text: q.innerText, buttons: q.querySelectorAll('button, a').length,
  pills: document.querySelectorAll('.talk .pill:not(.dock-send):not(.dock-stop):not(.dock-voice-mode):not(.talk-above)').length }; })()`);
check("P1 the question is her words, no card: no chip, no button, no \"Open the card\"", qw.buttons === 0 && qw.pills === 0 && !qw.text.includes(S["card.open_full"]), JSON.stringify(qw));
const qo = await js(`import('./state.js').then((m) => { const id = document.querySelector('.talk-q').dataset.card; const all = [...(m.store.state.deal.cards || []), ...((m.store.state.deal.beyond || {}).cards || [])]; return (all.find((c) => c.id === id) || {}).options || []; })`);
check("P1 the choices said in her sentence, and the one she would choose", qo.length >= 2 && qo.every((o) => qw.text.toLowerCase().includes(o.toLowerCase())) && /I would say/.test(qw.text), JSON.stringify([qw, qo]));
check("12 the question is the one owed thing", await js("document.querySelectorAll('.owed').length === 1 && !!document.querySelector('.talk-q.owed')"));
const goldChips = await js(`(() => { const probe = document.createElement('i'); probe.style.color = 'var(--owed)'; document.body.append(probe);
  const g = getComputedStyle(probe).color; probe.remove();
  return [...document.querySelectorAll('.talk-q .talk-q-words')].filter((e) => { const s = getComputedStyle(e);
    return s.color === g || s.borderTopColor === g || s.backgroundColor === g; }).length; })()`);
check("12 one gold: her words are in ink, only the hairline is gold", goldChips === 0, String(goldChips));
await words("question 390");
await oneScreen("question 390");
for (const [w, hh, large] of [[360, 640, true], [320, 568, false], [320, 568, true]]) {
  await size(w, hh);
  if (large) await js("document.documentElement.dataset.type = 'large'; true");
  await sleep(500);
  await oneScreen(`question ${w}${large ? " large" : ""}`);
  await js("delete document.documentElement.dataset.type; true");
}
await size(390, 844); await sleep(300);

// ---------------------------------------------------------------- 3 · a typed answer settles as a tap would; R6 its keepsake in her record
await js(`window.__says = []; { const f = window.fetch; window.fetch = (u, o) => { if (/agent\\/say/.test(String(u))) window.__says.push(o && o.body); return f(u, o); }; } true`);
const q1 = await js(`(async () => { const q = document.querySelector('.talk-q'); if (!q) return null; const m = await import('./state.js');
  const all = [...((m.store.state.deal || {}).cards || []), ...(((m.store.state.deal || {}).beyond || {}).cards || [])];
  const dc = all.find((c) => c.id === q.dataset.card) || {}; return { id: q.dataset.card, go: dc.go || null, opts: dc.options || [] }; })()`);
await say("the second");
const pend = await js(`import('./state.js').then((m) => [...m.store.pending.values()].map((p) => ({ type: p.type, links: p.links, body: p.body })))`);
const settledText = await js("[...document.querySelectorAll('.talk-settled')].map((e) => e.innerText).join(' | ')");
check("3 \"the second\" writes the Deal's own act for the second option", pend.some((p) => p.type !== "study" && p.type !== "keepsake" && JSON.stringify(p.links || {}).includes(q1.id) && JSON.stringify(p.body).includes(q1.opts[1])), JSON.stringify(pend));
check("R6 a keepsake line goes to her own record with the answer", pend.some((p) => p.type === "keepsake" && p.body && p.body.card === q1.id && typeof p.body.mark === "string"), JSON.stringify(pend));
check("R6 the keepsake is not kept in this browser", (await js("localStorage.getItem('hud.talk.keepsakes')")) === null);
check("3 the stream says what follows, never \"Marked\", with Undo", settledText.length > 0 && !/\bMarked\b/.test(settledText) && /undo/i.test(settledText), settledText);
check("T3 the Undo for a typed answer is in view, not only for a screen reader", await js("(() => { const u = [...document.querySelectorAll('.talk-settled .talk-undo')].pop(); return !!u && !!u.getClientRects().length && getComputedStyle(u).visibility === 'visible' && u.getBoundingClientRect().height >= 24; })()"));
check("T13 the answered question stays as one quiet line above its answer", await js("(() => { const s = [...document.querySelectorAll('.talk-settled')].pop(); const q = s && s.querySelector('.talk-settled-q'); return !!q && !!q.innerText.trim() && !!(q.compareDocumentPosition(s.querySelector('.talk-settled-line')) & Node.DOCUMENT_POSITION_FOLLOWING); })()"));
check("3 her own words stay in the stream", (await js("[...document.querySelectorAll('.talk .dock-turn--you')].map((e) => e.innerText).join('|')")).includes("the second"));
check("3 the answer was the page's, never sent to the agent", (await js("window.__says.length")) === 0);
check("8 a keepsake mark sits in her settled line", await js("!!document.querySelector('.talk-settled .talk-keep') && document.querySelector('.talk-settled .talk-keep').getBoundingClientRect().width === 24"));
const after = await js(dealOpen);
check("the Deal's count agrees: one fewer, the answered card gone", after.length === deck.length - 1 && !after.includes(q1.id), JSON.stringify([deck.length, after.length]));

// ---------------------------------------------------------------- R2 · the next card after a typed answer: within two seconds of idleness, "One more." until then
await js("(() => { const i = document.querySelector('.talk .dock-input'); i.focus(); return true; })()");
await send("Input.insertText", { text: "hm" });
await sleep(400);
check("R2 while the next comes, one dust line says so", (await js("(document.querySelector('.talk-coming') || {}).innerText || ''")) === S["talk_place.coming"]);
await sleep(3600);
check("4 no next question while the line to speak has words in it", !(await js("!!document.querySelector('.talk-q')")));
await js("(() => { const i = document.querySelector('.talk .dock-input'); i.value = ''; return true; })()");
const tNext = Date.now();
let nextQ = null;
for (let i = 0; i < 40 && !nextQ; i++) { await sleep(150); nextQ = await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null"); }
const ol1 = await js(OL);
check("R2 the next question comes within two seconds of idleness after a typed answer (focus kept)", !!nextQ && Date.now() - tNext < 2900, String(Date.now() - tNext));
check("R9 and it is the owed line's first", nextQ === ol1.card, JSON.stringify([nextQ, ol1]));
// a change in the record while she types never swaps the card on screen
await js("(() => { const i = document.querySelector('.talk .dock-input'); i.focus(); return true; })()");
await send("Input.insertText", { text: "let me think" });
await js(`import('./state.js').then((m) => { m.markAnswered(${JSON.stringify(nextQ)}); return true; })`);
await sleep(1500);
check("4 the card on screen is not swapped mid-thought", (await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null")) === nextQ);
await js(`import('./state.js').then((m) => { m.unmarkAnswered(${JSON.stringify(nextQ)}); const i = document.querySelector('.talk .dock-input'); i.value = ''; i.blur(); return true; })`);

// ---------------------------------------------------------------- 18 · "what needs me?": the page, at once, the Deal's count and first, the question said once
const qWords = await js("(document.querySelector('.talk-q .talk-q-words') || {}).innerText || ''");
const t18 = Date.now();
await say("what needs me?");
const needs = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).filter((x) => !/^what needs me/.test(x)).pop() || ''");
const olN = await js(OL);
const np = needsParts(needs);
check("18 \"what needs me?\" is answered by the page within two seconds", np.first && Date.now() - t18 < 2600, needs);
check("R2 the count is the one owed list's: the first thing and the rest make the count", np.first && np.more === olN.owed - 1, JSON.stringify([needs, olN.owed]));
const qCount = await js("(document.querySelector('.talk-q .talk-q-count') || {}).innerText || ''");
check("T7 the card's \"1 of n\" and \"what needs me?\" say one number", olN.owed <= 1 ? qCount === "" && np.more === 0 : qCount === `1 of ${np.more + 1}` && np.more + 1 === olN.owed, JSON.stringify([qCount, needs, olN.owed]));
await say("how many?");
const many = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).filter((x) => !/^how many/.test(x)).pop() || ''");
check("\"how many?\" is the page's, and says the same one number", needsParts(many).first && needsParts(many).more === np.more, JSON.stringify([many, needs, olN.owed]));
check("R9 the first it names is the Deal's first", !olN.title || needs.toLowerCase().includes(olN.title.toLowerCase().replace(/[.?!]+$/, "")), JSON.stringify([needs, olN.title]));
check("R5 the line never repeats the card's question, and never turns its ? into .", !(qWords && needs.includes(qWords.replace(/[?.]$/, ""))) && !/\?\./.test(needs), JSON.stringify([needs, qWords]));
check("18 and never sent to the agent", (await js("window.__says.length")) === 0);

// ---------------------------------------------------------------- R2 · "what’s blocked?" goes to the agent, with no line from the page
// the page's own turns: neither hers nor an ask her agent raised (since ff698d5 the harness's mode asks a command of her, in words)
const pageTurns = () => js("document.querySelectorAll('.talk .talk-turn:not(.dock-turn--you):not(.dock-ask-words)').length");
const pt0 = await pageTurns();
await say("what’s blocked?");
await sleep(600);
check("R2 \"what’s blocked?\" is sent to the agent", (await js("window.__says.length")) === 1);
check("R2 and the page says nothing of its own", (await pageTurns()) === pt0, String(await pageTurns()));
// its command ("find bg -name status.md") is asked of her in words; her no answers it, and the turn ends
if (await js("!!document.querySelector('.talk .dock-ask-words:not(.is-answered)')")) { await say("no"); for (let i = 0; i < 20 && !(await js("document.querySelector('.talk .dock-stop').hidden")); i++) await sleep(300); }
check("R2 the command her agent tried is asked in words and answered by her no", !(await js("!!document.querySelector('.talk .dock-ask-words:not(.is-answered)')")));

// ---------------------------------------------------------------- who is working on what
await say("who is working on what?");
const who = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).slice(-1)[0] || ''");
check("\"who is working on what\" is answered in words from the bodies", /Vega/.test(who) && /bookshelf/i.test(who) && /Rigel/.test(who) && /Open Agents/.test(who), who);
check("the question was never sent to the agent", (await js("window.__says.length")) === 1);
await words("who");

// ---------------------------------------------------------------- P4 · every step she takes is seen: a quiet row each, with the time it took
{
  // Working is everyone's default; Plain is one turn of the knob down, by her word
  await say("show me less");
  await say("what is in the notes about the hall?");
  let rows = [];
  // at Plain: one quiet line per turn, the steps one tap below
  for (let i = 0; i < 40; i++) { await sleep(500); rows = await js("[...document.querySelectorAll('.talk .dock-acts--plain .dock-act-line')].filter((e) => e.getClientRects().length).map((e) => e.innerText)"); if (rows.length && await js("document.querySelector('.talk .dock-stop').hidden")) break; }
  check("P4 her agent's steps are seen: at Plain one quiet line of what she did, never hidden", rows.length >= 1 && rows.some((r) => /^I (read|searched|ran|wrote)\b.*\.$/.test(r)), JSON.stringify(rows));
  check("P4 a step's row names no folder", !rows.some((r) => /\/Users\//.test(r)), JSON.stringify(rows));
}

// ---------------------------------------------------------------- 1 · the agent answers a line, and is told what the page says; 6 · Stop
let idle = false;
for (let i = 0; i < 40 && !idle; i++) { await sleep(500); idle = await js("document.querySelector('.talk .dock-stop').hidden"); }
const stopNow = await js(`(() => { const i = document.querySelector('.talk .dock-input'); i.focus(); i.value = 'Good morning';
  document.querySelector('.talk .dock-send').click();
  const s = document.querySelector('.talk .dock-stop'), b = document.querySelector('.talk .dock-send');
  const r = (e) => e.getBoundingClientRect();
  return { stop: !!s && !s.hidden && !!s.getClientRects().length, sendRight: r(b).right, w: innerWidth, sendW: r(b).width }; })()`);
check("6 Stop is in view the moment a turn runs", stopNow.stop, JSON.stringify(stopNow));
check("13 Send stays inside the gutter while Stop shows", stopNow.sendRight <= stopNow.w - 15, JSON.stringify(stopNow));
let reply = "";
for (let i = 0; i < 40 && !/Good (morning|afternoon|evening)\. I am here/.test(reply); i++) { await sleep(500); reply = await js("[...document.querySelectorAll('.talk .dock-turn--agent .dock-letter')].map((e) => e.innerText).join(' ')"); }
check("the stand-in agent answers in the conversation", reply.length > 0, reply);
const page = await js("(() => { try { return JSON.parse(window.__says[window.__says.length - 1]).page || null; } catch { return null; } })()");
check("1 the line goes with the page context: the line, the question, its options, what the page said", !!page && typeof page.line === "string" && "question" in page && Array.isArray(page.options) && Array.isArray(page.local_answers), JSON.stringify(page));
check("R2 the page context carries what the page said", !!page && (await js("window.__says.some((b) => { try { return (JSON.parse(b).page.local_answers || []).some((x) => /Vega/.test(x)); } catch { return false; } })")), JSON.stringify(page));
check("T3 her typed answer is told to the host as `settled` (card and option, never \"Marked\"), so her agent proposes no mark for it", !!page && Array.isArray(page.settled)
  && (await js("window.__says.map((b) => { try { return JSON.parse(b).page.settled || []; } catch { return []; } }).flat().some((x) => x.card === " + JSON.stringify(q1.id) + " && x.option === " + JSON.stringify(q1.opts[1]) + ")")), JSON.stringify(page && page.settled));
check("T12 the page tells the host its first, by card and title: the question on screen", !!page && !!page.first && page.first.card === (await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null")) && typeof page.first.title === "string" && page.first.title.length > 0, JSON.stringify(page && page.first));
check("1 the page's own answers are not drawn twice in the stream", (await js("[...document.querySelectorAll('.talk .dock-turns')].map((e) => (e.innerText.match(/Vega/g) || []).length)[0]")) === 1);
check("R2 no reply of the agent's begins with a bare \"Marked.\"", !(await js("[...document.querySelectorAll('.talk .dock-turn--agent .dock-letter')].some((e) => /^Marked\\.?$/.test(e.innerText.trim().split('\\n')[0]))")));
let stopGone = false;
for (let i = 0; i < 30 && !stopGone; i++) { stopGone = await js("!!document.querySelector('.talk .dock-stop').hidden"); if (!stopGone) await sleep(400); }
check("6 Stop leaves when the turn ends", stopGone, await js("JSON.stringify({ busy: document.querySelector('[data-busy]')?.dataset.busy, live: document.querySelector('.talk .dock-live')?.innerText || '' })"));
const tall = await js(`(async () => { const i = document.querySelector('.talk .dock-input'); const h0 = i.getBoundingClientRect().height;
  i.focus(); i.value = 'one ' + 'longer line that wraps across the width of the phone '.repeat(4); i.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 50)); const h1 = i.getBoundingClientRect().height;
  i.value = 'stop'; document.querySelector('.talk .dock-send').click(); await new Promise((r) => setTimeout(r, 100));
  return { h0, h1, h2: i.getBoundingClientRect().height, v: i.value }; })()`);
check("T18 the empty line to speak shrinks back on send", tall.h1 > tall.h0 && Math.abs(tall.h2 - tall.h0) < 2 && tall.v === "", JSON.stringify(tall));
// Send does not move when the line to speak takes or loses focus
const moves = await js(`(async () => { const i = document.querySelector('.talk .dock-input'), b = document.querySelector('.talk .dock-send');
  i.blur(); await new Promise((r) => setTimeout(r, 120)); const a = b.getBoundingClientRect();
  i.focus(); await new Promise((r) => setTimeout(r, 120)); const c = b.getBoundingClientRect(); i.blur();
  return { dy: Math.abs(a.top - c.top), dx: Math.abs(a.left - c.left) }; })()`);
check("16 Send never moves on focus or blur", moves.dx < 1 && moves.dy < 1, JSON.stringify(moves));
// R10 · the question stays in its place for the whole of her turn; then a typed "stop" ends it, never sent
const says0 = await js("window.__says.length");
await say("slow, please take your time");
await sleep(2500);
const during = await js("({ busy: !document.querySelector('.talk .dock-stop').hidden, q: !!document.querySelector('.talk-q') && !!document.querySelector('.talk-q').getClientRects().length })");
check("R10 the owed question stays in the stream while her turn runs", during.busy && during.q, JSON.stringify(during));
await say("stop");
await sleep(400);
check("6 a typed \"stop\" asks the turn to stop, and is never sent", (await js("window.__says.length")) === says0 + 1
  && (await js("performance.getEntriesByType('resource').filter((e) => /agent\\/stop/.test(e.name)).length")) >= 1, String(await js("window.__says.length")));
let stopped = false;
for (let i = 0; i < 30 && !stopped; i++) { await sleep(500); stopped = await js("!!document.querySelector('.talk .dock-stop').hidden"); }
check("6 the turn ends, and Stop leaves with it", stopped);
check("10 the question keeps its place after her turn", await js("!!document.querySelector('.talk-q') && !!document.querySelector('.talk-q').getClientRects().length"));

// ---------------------------------------------------------------- R2 · "who are you?": the host's own answer, painted once; no page line for it
const locals0 = await js("document.querySelectorAll('.talk .dock-turn--local').length");
const pt1 = await pageTurns();
await say("who are you?");
let locals = locals0;
for (let i = 0; i < 20 && locals === locals0; i++) { await sleep(300); locals = await js("document.querySelectorAll('.talk .dock-turn--local').length"); }
await sleep(1500);
check("R2 \"who are you?\" is answered once, in the host's own words", (await js("document.querySelectorAll('.talk .dock-turn--local').length")) === locals0 + 1, String(await js("document.querySelectorAll('.talk .dock-turn--local').length")));
check("R2 and the page adds no line of its own for it", (await pageTurns()) === pt1, String(await pageTurns()));
let quiet = false;
for (let i = 0; i < 40 && !quiet; i++) { await sleep(500); quiet = await js("document.querySelector('.talk .dock-stop').hidden"); }

// ---------------------------------------------------------------- 6 and 5 · her name opens who she is, where words go, how to stop, a person; R6 the keepsakes from her record
await sleep(1500);
await js("document.querySelector('.talk-door').click(); true"); await sleep(400);
const about = await js("document.querySelector('.sheet') ? document.querySelector('.sheet').textContent : ''");
check("6 a person is one tap from her name", about.includes(S["dock.about.reach_title"]) && (about.includes(S["dock.about.reach_unnamed"]) || /brought you here/.test(about)), about.slice(0, 300));
check("5 the sheet says where words go and how to stop", about.includes(S["dock.first.words"]) && about.includes(S["dock.about.stop"]));
check("R6 the keepsakes row reads from her record (hud.keepsakes)", about.includes(S["talk_place.keepsakes"]) && await js("!!document.querySelector('.sheet .talk-keep')")
  && (await js(`import('./state.js').then((m) => (m.store.state.hud.keepsakes || []).some((k) => k.card === ${JSON.stringify(q1.id)}))`)), about.slice(-300));
check("R12 the keepsake is explained once in her sheet", about.includes(S["talk_place.keepsakes_about"]));
check("5 no view of the machine behind her name", !/Terminal view|Command line/.test(about));
const sheetCtl = await js("[...document.querySelectorAll('.sheet button, .sheet a[href], .sheet input, .sheet select, .sheet textarea')].filter((e) => e.getClientRects().length).map((e) => e.innerText.trim())");
check("T1 the sheet behind her name: at most eight controls and Close", sheetCtl.filter((x) => x !== S["app.close"]).length <= 8 && sheetCtl.includes(S["app.close"]), JSON.stringify(sheetCtl));
check("T1 it keeps who she is, where words go, how to stop, a person, the keepsakes, and one read-aloud choice", [S["dock.about.words_title"], S["dock.about.stop_title"], S["dock.about.reach_title"], S["talk_place.keepsakes"], S["dock.voice.read_on"]].every((x) => about.includes(x)), about.slice(0, 200));
check("T1 the settings wall left it: no pause picker, no judgment, no fewer questions, no send-on-release", ![S["dock.voice.pause"], S["dock.discern_title"], S["dock.discern_offer"], S["dock.fewer_questions"], S["dock.voice.send_on"], S["dock.voice.dim_on"]].some((x) => about.includes(x)), about.slice(-400));
check("T8 her sheet speaks in the first person, never \"Your agent\"", !/Your agent/.test(about), about.slice(0, 200));
const sheetEdge = await js(`(() => { const hd = document.querySelector('.sheet > .sheet-head'); const sc = document.querySelector('.talk .dock-scroll');
  const m = getComputedStyle(sc).maskImage || getComputedStyle(sc).webkitMaskImage || '';
  return { sticky: getComputedStyle(hd).position, fade: (m.match(/(\\d+)px\\)\\s*$/) || m.match(/(\\d+)px/g) || []).toString() }; })()`);
check("T9 a sheet's head stays at its edge, and what scrolls under it fades", sheetEdge.sticky === "sticky", JSON.stringify(sheetEdge));
await js("document.querySelector('.sheet .dock-to-settings').click(); true"); await sleep(500);
const settingsText = await js("document.querySelector('.sheet') ? document.querySelector('.sheet').innerText : ''");
const settingsAll = await js("document.querySelector('.sheet') ? document.querySelector('.sheet').textContent : ''");
check("T1 the rest lives in Settings, behind More: the voice's finer choices and the counting of judgments, beside the study", settingsAll.includes(S["dock.voice.send_on"]) && settingsAll.includes(S["dock.discern_offer"]) && settingsText.includes(S["about.study"]), settingsText.slice(0, 300));
check("the voice's fine choices and the judgments fold under one heading each, opened on a tap", settingsText.includes(S["dock.trust.settings.voice"]) && !settingsText.includes(S["dock.voice.send_on"]) && !settingsText.includes(S["dock.discern_offer"]), settingsText.slice(0, 300));
const herControls = await js("[...document.querySelectorAll('.sheet .settings-agent button, .sheet .settings-agent summary, .sheet .dock-settings-fold:not(.settings-fold) > summary')].filter((e) => e.getClientRects().length).map((e) => e.innerText.trim()).filter(Boolean)");
check("her part of Settings at first sight: the ways of acting, Voice and the judgments, each one tap", herControls.length <= 4 && herControls.includes(S["dock.trust.settings.voice"]), JSON.stringify(herControls));
check("T8 \"Your agent can count your judgments\" is gone: she says it herself", !/Your agent can count/.test(settingsText) && /^I can count/.test(S["dock.discern_offer"]));
const aboutHit = about.match(APPARATUS);
check("5 the sheet behind her name speaks none of the apparatus's words", !aboutHit, aboutHit && aboutHit[0]);
await js("document.querySelector('.scrim') && document.querySelector('.scrim').click(); true"); await sleep(300);

// ---------------------------------------------------------------- T5 · a long answer never pushes her question off: her line held at the top
{
  await size(360, 640); await js("document.documentElement.dataset.type = 'large'; true"); await sleep(500);
  await say("tell me the long version please");
  let done5 = false;
  for (let i = 0; i < 40 && !done5; i++) { await sleep(400); done5 = await js("document.querySelector('.talk .dock-stop').hidden && /how the week looks/.test(document.querySelector('.talk .dock-turns').innerText)"); }
  await sleep(300);
  const held = await js(`(() => { const sc = document.querySelector('.talk .dock-scroll'); const b = sc.getBoundingClientRect();
    const you = [...document.querySelectorAll('.talk .dock-turn--you')].pop(); const r = you.getBoundingClientRect();
    return { text: you.innerText, top: Math.round(r.top - b.top), inView: r.top >= b.top && r.bottom <= b.bottom, longer: sc.scrollHeight - sc.scrollTop > sc.clientHeight + 4 }; })()`);
  check("T5 after her line, her line sits at the top of the view and the long answer grows beneath it", /long version/.test(held.text) && held.inView && held.top < 80 && held.longer, JSON.stringify(held));
  const pill = await js(`(() => { const sc = document.querySelector('.talk .dock-scroll').getBoundingClientRect(); const q = document.querySelector('.talk-q'); const p = document.querySelector('.talk-above');
    return { q: !!q, above: !!q && q.getBoundingClientRect().bottom < sc.top + 8, pill: !!p && !p.hidden && !!p.getClientRects().length }; })()`);
  check("T22 the open question scrolled away above: one quiet pill \"The question, above\" at the stream's foot", !pill.q || pill.above === pill.pill, JSON.stringify(pill));
  if (pill.pill) {
    await js("document.querySelector('.talk-above').click(); true"); await sleep(900);
    const back22 = await js("(() => { const sc = document.querySelector('.talk .dock-scroll').getBoundingClientRect(); const r = document.querySelector('.talk-q').getBoundingClientRect(); return { top: Math.round(r.top - sc.top), h: Math.round(sc.height), hidden: document.querySelector('.talk-above').hidden }; })()");
    check("T22 the pill brings the question back into view, and leaves", back22.top >= -1 && back22.top < back22.h && back22.hidden, JSON.stringify(back22));
  }
  await js("delete document.documentElement.dataset.type; true"); await size(390, 844); await sleep(400);
}

// ---------------------------------------------------------------- R1 · an ask is a turn in the stream; her newest line in view; No takes nothing away
await say("can we go slowly?");
let keepAsk = null;
for (let i = 0; i < 40 && !keepAsk; i++) { await sleep(300); keepAsk = await js("(() => { const c = document.querySelector('.talk .dock-turns .dock-ask-words'); return c ? c.innerText : null; })()"); }
check("R1 the ask arrives as a turn in the stream, never pinned at the foot", !!keepAsk && (await js("!document.querySelector('.talk .dock-asks .dock-ask')")), keepAsk);
check("P2 every ask is her words: no card, no button", await js("(() => { const a = document.querySelector('.talk .dock-ask-words'); return !!a && !a.querySelector('button') && !document.querySelector('.talk .dock-ask'); })()"));
check("P3 no quick-reply row: nothing to tap but the line to speak", !(await js("!!document.querySelector('.talk-quick')")));
check("R1 its face shows no file, no front matter", !!keepAsk && !/\.md\b|---|name:|type:/.test(keepAsk), keepAsk);
const beforeNo = await js("[...document.querySelectorAll('.talk .dock-turn--agent .dock-letter')].map((e) => e.innerText).join(' ')");
await say("thank you, that is enough for today");
await sleep(500);
const inView = await js(`(() => { const sc = document.querySelector('.talk .dock-scroll').getBoundingClientRect();
  const you = [...document.querySelectorAll('.talk .dock-turn--you')].pop(); const r = you.getBoundingClientRect();
  return { text: you.innerText, top: r.top >= sc.top - 1, bottom: r.bottom <= sc.bottom + 1 }; })()`);
check("R1 her newest line is in view while an ask waits", /enough for today/.test(inView.text) && inView.top && inView.bottom, JSON.stringify(inView));
await say("no");
await sleep(2500);
if (await js("!!document.querySelector('.talk .dock-ask-words')")) { await say("no"); await sleep(2500); }
const afterNo = await js("[...document.querySelectorAll('.talk .dock-turn--agent .dock-letter')].map((e) => e.innerText).join(' ')");
check("R1 No never removes anything already said", !/We go at your pace/.test(beforeNo) || /We go at your pace/.test(afterNo), JSON.stringify([beforeNo.slice(-120), afterNo.slice(-200)]));
check("R1 the answered ask stays in its place as her line, with no second answer beside it", (await js("document.querySelectorAll('.talk .dock-ask-words.is-answered').length")) >= 1 && !(await js("[...document.querySelectorAll('.talk .dock-ask-words.is-answered')].some((e) => / · (yes|no|not this)$/i.test(e.innerText.trim()))")));
quiet = false;
for (let i = 0; i < 40 && !quiet; i++) { await sleep(500); quiet = await js("document.querySelector('.talk .dock-stop').hidden"); }

// ---------------------------------------------------------------- T2 · her name for a card: the host's answer to a keep ask returns it; the card shows it
{
  const qNow = await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null");
  const named = await js(`(async () => { const f = window.fetch; window.fetch = (u, o) => /agent\\/answer/.test(String(u))
      ? Promise.resolve(new Response(JSON.stringify({ ok: true, named: { card: ${JSON.stringify(qNow)}, name: "The Gathering Day" } }), { status: 200, headers: { "Content-Type": "application/json" } })) : f(u, o);
    const m = await import('./state.js'); const r = await m.agent.answer('c-test', 'a-test', 'yes'); window.fetch = f;
    await new Promise((r) => setTimeout(r, 300));
    return { ok: r.ok, face: (document.querySelector('.talk-q .talk-q-named') || {}).innerText || '', fold: m.read.cardName(m.store.state, ${JSON.stringify(qNow)}) }; })()`);
  check("T2 Keep it with a name: the card's face shows her name above the question, from the fold", !!qNow && named.face === "The Gathering Day" && named.fold === "The Gathering Day", JSON.stringify(named));
  await js("location.hash = '#/deal'; true"); await sleep(1200);
  const dealNamed = await js(`[...document.querySelectorAll('.card-named')].map((e) => e.innerText)`);
  await js("location.hash = '#/talk'; true"); await sleep(1200);
  check("T2 and the Deal's card shows the same name", !qNow || dealNamed.includes("The Gathering Day") || !(await js(`import('./deal.js').then((m) => m.dealt(window.__hudProbe.makeCtx({ slot: 'main' })).open.slice(0, 1).map((c) => c.id))`)).includes(qNow), JSON.stringify(dealNamed));
  globalThis.__namedCard = qNow;
}

// ---------------------------------------------------------------- 10 · a worker by sentence: the ask in the stream, after the question; R3 the worker's own asks reach the Talk
// an ask asked once (ce0a9c2): when her letter just above ends on its question, the ask row keeps only its
// step and its answers, and the words are her letter's; the ask is the row, its words its own or the letter's
const askOf = (re, sel = ".dock-ask-words") => `(() => { const re = ${re};
  const said = (x) => { for (let p = (x.closest('.dock-row') || x).previousElementSibling; p; p = p.previousElementSibling) { const t = p.matches('.dock-turn') ? p : p.querySelector('.dock-turn'); if (!t || !t.innerText.trim()) continue; return t.classList.contains('dock-turn--agent') ? t.innerText : ''; } return ''; };
  return [...document.querySelectorAll('.talk .dock-turns ${sel}')].map((x) => ({ x, words: re.test(x.innerText) ? x.innerText : (x.matches('.talk-said-above, .is-said-above') && re.test(said(x)) ? said(x).trim().split('\\n').pop() : null) })).filter((o) => o.words); })()`;
await say("have a worker draw the map of the commons");
let wk = null;
for (let i = 0; i < 30 && !wk; i++) { await sleep(400); wk = await js(`(${askOf("/map of the commons/")}.map((o) => o.words)[0] || null)`); }
check("the agent's proposal arrives as an ask card in the stream", !!wk && /draw the map of the commons/.test(wk), wk);

check("the proposal is her words, answered by words, no button", await js("![...document.querySelectorAll('.talk .dock-ask-words')].some((x) => x.querySelector('button'))"));
const order = await js(`(() => { const q = document.querySelector('.talk-q'), a = [...document.querySelectorAll('.talk .dock-ask-words')].pop(), sc = document.querySelector('.talk .dock-scroll');
  return { q: !!q && !!q.getClientRects().length, below: !!(q && a && (q.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING)), inStream: !!(a && sc.contains(a)) }; })()`);
check("10 the question keeps its place; the ask sits beneath it, in the stream", order.q && order.below && order.inStream, JSON.stringify(order));
check("nothing is started before the tap", (await js("performance.getEntriesByType('resource').filter((e) => /agent\\/body/.test(e.name)).length")) === 0);
await say("start it");
let started = false;
for (let i = 0; i < 30 && !started; i++) { await sleep(400); started = await js(`${askOf("/map of the commons/", ".dock-ask-words.is-answered")}.length > 0`); }
check("Start the worker starts it and answers the ask", started && (await js("performance.getEntriesByType('resource').filter((e) => /agent\\/body/.test(e.name)).length")) === 1);
// asked once: when her letter above ends on "Start it?", that letter is the one line, and the answered row stays beneath it, drawing no second question
check("R1 the answered worker ask stays in its place as one quiet line", (await js(`${askOf("/draw the map/", ".dock-ask-words.is-answered")}.length`)) === 1);
check("her \"start it\" is drawn once", (await js("[...document.querySelectorAll('.talk .dock-turn--you')].filter((e) => /^start it$/i.test(e.innerText.trim())).length")) === 1);
// the worker, once started, asks something of its own (the stand-in asks two permissions on "two changes")
let worker = null;
for (let i = 0; i < 30 && !worker; i++) { await sleep(500); worker = await js(`import('./state.js').then((m) => { const a = ((m.store.state.hud || {}).agents || []).find((x) => x.body); return a ? a.id : null; })`); }
if (worker) {
  await js(`(async () => { const tk = (await (await fetch('/token')).json()).token; await fetch('/agent/say', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-HUD-Token': tk },
    body: JSON.stringify({ agent: ${JSON.stringify(worker)}, text: 'please make two changes to the map', confirmed: true }) }); return true; })()`);
  let wa = null;
  for (let i = 0; i < 40 && !wa; i++) { await sleep(500); wa = await js("(() => { const c = document.querySelector('.talk .talk-ask'); return c ? c.innerText : null; })()"); }
  check("R3 the worker's own ask reaches the Talk, in the stream, saying who asks; its only taps are its two words", !!wa && /asks you/.test(wa) && (await js("!!document.querySelector('.talk .dock-scroll .talk-ask .talk-ask-words') && [...document.querySelectorAll('.talk .talk-ask button')].every((b) => b.closest('.talk-ask-answers')) && [...document.querySelectorAll('.talk .talk-ask')].every((a) => a.querySelectorAll('.talk-ask-answers button').length === 2)")), wa);
  check("T20 a worker's card is the worker's: its name in small caps above it, none of her words inside it", await js("(() => { const a = document.querySelector('.talk .talk-ask'); const why = a && a.querySelector('.dock-ask-why'); return !!(a && a.querySelector('.talk-ask-name')) && !(why && /^Very well|Good (morning|afternoon|evening)\\. I am here/.test(why.innerText)); })()"));
  check("R3 the Deal shows the same ask", await js(`import('./state.js').then((m) => ((m.store.state.hud || {}).agents || []).some((a) => a.body && (a.asks || []).length))`));
  for (let k = 0; k < 4 && (await js("!!document.querySelector('.talk .talk-ask')")); k++) { await say("no"); await sleep(2500); }
} else check("R3 a worker row appears for the started worker", false, "no worker in hud.agents");

// ---------------------------------------------------------------- 3 · your agent's own act, allowed by her Yes (the host's ask of kind `act`)
await say("please mark Saturday for the meeting day");
let act = null;
for (let i = 0; i < 25 && !act; i++) { await sleep(400); act = await js(`(${askOf("/Saturday/")}.map((o) => o.words)[0] || null)`); }   // asked once (ce0a9c2): the words may be her letter's
if (act) {
  await say("yes");
  await sleep(1500);
  check("3 her Yes on the agent's act settles the card, with its mark", /Saturday morning/.test(await js("[...document.querySelectorAll('.talk-settled')].map((e) => e.innerText).join(' | ')")));
} else console.log("  (the host raised no `act` ask for \"mark Saturday\": the agent side's, not proven here)");

// ---------------------------------------------------------------- T· her agent decides the suggested choice on its own word: settled here, with Undo
{
  const before = await js("document.querySelectorAll('.talk-settled').length");
  await say("decide what you can");
  let dec = null;
  for (let i = 0; i < 30 && !dec; i++) { await sleep(400); dec = await js("(() => { const s = [...document.querySelectorAll('.talk-settled')].find((e) => /Decided for you/.test(e.innerText)); return s ? s.innerText : null; })()"); }
  check("decided: her agent's mark of the suggested choice settles the card here, \"Decided for you\", with Undo", !!dec && /Undo/.test(dec) && (await js("document.querySelectorAll('.talk-settled').length")) > before, dec);
  for (let i = 0; i < 30; i++) { await sleep(400); if (await js("document.querySelector('.talk .dock-stop').hidden")) break; }
}
// the ask's face is the host's own words, for every kind; a worker's ask carries neither "later" nor "yes for this kind"
{
  const face = await js(`import('./dock-card.js').then((m) => { const el = m.renderAsk(window.__hudProbe.makeCtx({ slot: 'main' }), { id: 'x', kind: 'edit', question: 'Vega would like to change the draft of the harvest notes?',
    from_worker: 'Vega', step: 'Change the draft of the harvest notes. Nothing leaves this computer.', preview: '# Notes\\n**Beans**: forty jars', input: null,
    options: [{ id: 'a', kind: 'allow_once' }, { id: 'b', kind: 'reject_once' }, { id: 'c', kind: 'allow_always' }] }, { onAnswer: async () => ({ ok: true }) });
    document.body.append(el); el.querySelector('details') && (el.querySelector('details').open = true); const t = el.innerText; el.remove(); return t; })`);
  check("host words: the ask's face is its `question`, the preview plain, the step one sentence", /^Vega would like to change the draft/.test(face) && /Beans: forty jars/.test(face) && !/[#*]/.test(face) && face.includes("Nothing leaves this computer"), face);
  check("a worker's ask: no \"later\", no \"yes for this kind\"", !face.includes(S["dock.answer.postpone"]) && !face.includes(S["dock.answer.yes_kind"]), face);
}

// ---------------------------------------------------------------- R2 · the hand to its end: "Read it now" follows; the earlier settled lines fold; R9 the rest line reads the next hand
const answerUntil = async (stop) => {
  for (let i = 0; i < 14; i++) {
    let q = null;
    for (let k = 0; k < 30 && !q; k++) { await sleep(200); q = await js(`(async () => { const q = document.querySelector('.talk-q'); if (!q) return null; const m = await import('./state.js');
  const all = [...((m.store.state.deal || {}).cards || []), ...(((m.store.state.deal || {}).beyond || {}).cards || [])];
  const dc = all.find((c) => c.id === q.dataset.card) || {}; return { id: q.dataset.card, go: dc.go || null, opts: dc.options || [] }; })()`); }
    if (!q) return null;
    if (stop && q.opts.includes(stop)) return q;
    // a card whose first option leads somewhere ("Read it now") is answered by its second here, so the walk stays in the Talk
    await tapWord(q.opts[q.go || q.opts[0] === "Read it now" ? 1 : 0]);
    await sleep(300);
  }
  return null;
};
let handoff = await answerUntil("Read it now");
if (!handoff) {
  const rest = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''");
  const dNext = await js("import('./deal.js').then((m) => m.dealt(window.__hudProbe.makeCtx({ slot: 'main' })).next)");
  check("R9 at the end of the hand the Talk reads the next hand, as the Deal does", dNext > 0 ? /more can wait, or say next/.test(rest) : true, JSON.stringify([rest, dNext]));
  await say("next");
  handoff = await answerUntil("Read it now");
}
if (handoff) {
  await tapWord("Read it now");
  await sleep(1500);
  const opened = await js("({ hash: location.hash, card: !!document.querySelector('.sheet--card') })");
  const kept = await js("JSON.parse(localStorage.getItem('hud.talk.turns') || '[]')");
  check("R2 \"Read it now\" opens what was found (the card's own way, else the full card)", handoff.go ? opened.hash === handoff.go : /^#\/card\//.test(opened.hash) && opened.card, JSON.stringify([opened, handoff.go]));
  check("R2 and says nothing about marking", !kept.some((x) => x.card === handoff.id), JSON.stringify(kept.filter((x) => x.card === handoff.id)));
  await js("location.hash = '#/talk'; true"); await sleep(1500);
  // closing the full card steps back in history; with the Deal visited earlier that can land off the Talk
  if ((await js("location.hash")) !== "#/talk") { await js("location.hash = '#/talk'; true"); await sleep(1500); }
} else check("R2 the worker's handoff card was dealt", false);
await answerUntil(null);
await sleep(2600);
const marked = await js(`({ fold: (document.querySelector('.talk-marked') || {}).innerText || '', shown: [...document.querySelectorAll('.talk-settled')].filter((e) => e.getClientRects().length).length,
  all: document.querySelectorAll('.talk-settled').length })`);
check("R2 after three, the earlier settled lines fold into one quiet line", /marked earlier/.test(marked.fold) && marked.shown === 1, JSON.stringify(marked) + " " + (await js("location.hash + ' talk:' + !!document.querySelector('.talk') + ' sheet:' + !!document.querySelector('.sheet')")) + " " + errors.join(" | "));
await js("document.querySelector('.talk-marked .link-btn') && document.querySelector('.talk-marked .link-btn').click(); true"); await sleep(300);
check("R2 \"show\" opens them again", (await js("[...document.querySelectorAll('.talk-settled')].filter((e) => e.getClientRects().length).length")) > 1);

// T17 · a chip answer: the settled line keeps the question's place; the next question comes beneath it
{
  const before = await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null");
  if (before) {
    const o17 = (await js(`(async () => { const q = document.querySelector('.talk-q'); if (!q) return null; const m = await import('./state.js');
  const all = [...((m.store.state.deal || {}).cards || []), ...(((m.store.state.deal || {}).beyond || {}).cards || [])];
  const dc = all.find((c) => c.id === q.dataset.card) || {}; return { id: q.dataset.card, go: dc.go || null, opts: dc.options || [] }; })()`)).opts[0];
    await tapWord(o17);
    let nq = null; for (let i = 0; i < 30 && !nq; i++) { await sleep(200); nq = await js("(document.querySelector('.talk-q') || { dataset: {} }).dataset.card || null"); }
    const ord = await js(`(() => { const s = [...document.querySelectorAll('.talk-settled')].find((e) => e.dataset.card === ${JSON.stringify(before)}), q = document.querySelector('.talk-q');
      return { s: !!s, q: !!q, below: !!(s && q && (s.compareDocumentPosition(q) & Node.DOCUMENT_POSITION_FOLLOWING)) }; })()`);
    check("T17 the settled line stays where the question was; the next question comes beneath it", !ord.q || ord.below, JSON.stringify(ord));
  }
}
await answerUntil(null);
await sleep(2600);
// T11 · at rest: one count. The rest line, "what needs me?" and "next" read one source, and "next" never loops
{
  const restNow = await js("import('./deal.js').then((m) => { const c = window.__hudProbe.makeCtx({ slot: 'main' }); const d = m.dealt(c); return { open: d.open.length, next: d.next, owed: c.read.owedByStake(c.state).length }; })");
  await say("what needs me?");
  const n1 = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''");
  await say("next"); await sleep(2600);
  const a1 = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''");
  const q2 = await js("!!document.querySelector('.talk-q')");
  check("T11 at rest, \"what needs me?\" says the same count the rest line reads", restNow.open > 0 || (restNow.owed > 0 ? needsParts(n1).first && needsParts(n1).more === restNow.owed - 1 : restNow.next > 0 ? /more can wait/.test(n1) : n1 === S["talk_place.needs.none"]), JSON.stringify([n1, restNow]));
  check("T11 \"next\" deals the next hand, or says that is everything; never \"more can wait\" over nothing", q2 || !/more can wait/.test(a1), JSON.stringify([a1, q2, restNow]));
  if (!q2) {
    await say("next"); await sleep(2600);
    const a2 = await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''");
    check("T11 a second \"next\" never loops on a count", !/more can wait/.test(a2), a2);
  }
  await answerUntil(null); await sleep(2600);
}
if (globalThis.__namedCard) {
  const kept = await js(`import('./state.js').then((m) => (m.read.keepsakes(m.store.state) || []).find((k) => k.card === ${JSON.stringify(globalThis.__namedCard)}) || null)`);
  check("T2 the keepsake carries her name as its caption", !!kept && kept.name === "The Gathering Day", JSON.stringify(kept));
}

// ---------------------------------------------------------------- R8 · a reload in the middle of the conversation restores her turns as turns
await send("Page.reload", { ignoreCache: true }); await sleep(3000);
const restored = await js(`({ you: [...document.querySelectorAll('.talk .dock-turn--you')].map((e) => e.innerText),
  glued: [...document.querySelectorAll('.talk .dock-turn--local')].map((e) => e.innerText).filter((x) => /You chose|things\\. The first|marked/.test(x)),
  needs: [...document.querySelectorAll('.talk .talk-turn:not(.dock-turn--you)')].some((e) => /^[A-Z][a-z]+ things\\.|^One thing/.test(e.innerText)),
  earlier: !document.querySelector('.talk-earlier').hidden, heads: document.querySelectorAll('.talk-head').length })`);
check("R8 her own lines come back as her turns", restored.you.includes("the second") && restored.you.includes("what needs me?"), JSON.stringify(restored.you));
check("R8 the page's answers come back as its own turns, never glued under the agent", restored.needs && !restored.glued.length, JSON.stringify(restored));
check("R8 a reload mid-conversation folds nothing", !restored.earlier, JSON.stringify(restored));

// ---------------------------------------------------------------- R5 · the Deal: its lines never under the foot; its as-of read from the state at every draw
await js("location.hash = '#/deal'; true"); await sleep(1200);
const dealFoot = await js(`(() => { const p = document.querySelector('.places'); const bg = getComputedStyle(p).backgroundImage + getComputedStyle(p).backgroundColor;
  const m = parseFloat(getComputedStyle(document.getElementById('main')).paddingBottom); return { bg, pad: m, bar: p.getBoundingClientRect().height,
  asof: (document.querySelector('.as-of-btn') || {}).innerText || '' }; })()`);
check("R5 the foot has its own ground on a phone, and every place ends above it", /gradient/.test(dealFoot.bg) && dealFoot.pad >= dealFoot.bar, JSON.stringify(dealFoot));
const ownAt = await js("import('./state.js').then((m) => m.store.ownAt)");
check("R5 the as-of is at least her last act", !!ownAt && dealFoot.asof.includes(await js(`import('./state.js').then((m) => m.fmt.time(${JSON.stringify(ownAt)}))`)), JSON.stringify([dealFoot.asof, ownAt]));
const back14 = await js(`(async () => { const m = await import('./state.js'); const was = m.store.ownAt; m.store.ownAt = new Date(Date.parse(was || new Date().toISOString()) - 3600e3).toISOString();
  location.hash = '#/map'; await new Promise((r) => setTimeout(r, 900)); const txt = (document.querySelector('.as-of-btn') || {}).innerText || ''; m.store.ownAt = was; return txt; })()`);
check("T14 the as-of never goes backwards", !!back14 && back14 === dealFoot.asof, JSON.stringify([dealFoot.asof, back14]));
await js("location.hash = '#/talk'; true"); await sleep(900);

// ---------------------------------------------------------------- R11 · one head, however often the window crosses the desk breakpoint
for (const [w, hh] of [[1440, 900], [390, 844], [1440, 900], [390, 844]]) { await size(w, hh); await sleep(700); }
check("R11 one head after crossing the breakpoint four times", (await js("document.querySelectorAll('.talk-head').length")) === 1 && (await js("document.querySelectorAll('#talk-line').length")) === 1);
// R12 · no bare glyph: no ring before a turn, no mark beside a finished turn of hers
check("R12 no bare ring and no mark on a finished turn", await js(`![...document.querySelectorAll('.talk .dock-turnring, .talk .dock-ring, .talk .talk-ring')].some((e) => e.getClientRects().length)
  && ![...document.querySelectorAll('.talk .dock-turn--agent:not(.is-live) .dock-turnmark')].some((e) => e.getClientRects().length)`));

// ---------------------------------------------------------------- R7 · a fresh device: nothing before the welcome; the conversation under "Earlier"
// (an ask still open waits on her and is never folded: in words since the Talk draws no cards, .dock-ask-words or a worker's .talk-ask-words)
await js("localStorage.clear(); sessionStorage.clear(); true");
await send("Page.reload", { ignoreCache: true }); await sleep(3000);
const fresh = await js(`({ shown: [...document.querySelectorAll('.talk .dock-turns > *')].filter((e) => e.getClientRects().length && !e.querySelector('.dock-ask, .dock-ask-words:not(.is-answered), .talk-ask-words')).length,
  earlier: !document.querySelector('.talk-earlier').hidden, line: document.querySelector('.talk-line').innerText })`);
check("R7 a fresh device shows no turns before the welcome", fresh.shown === 0 && /^Good (morning|afternoon|evening)/.test(fresh.line), JSON.stringify(fresh));
check("R7 the earlier turns wait under \"Earlier\"", fresh.earlier, JSON.stringify(fresh));
for (const [w, hh] of [[1440, 900], [390, 844]]) { await size(w, hh); await sleep(800); }
check("T13 on a fresh device, a crossing of the breakpoint keeps \"Earlier\" closed", await js("!document.querySelector('.talk-earlier').hidden && [...document.querySelectorAll('.talk .dock-turns > *')].filter((e) => e.getClientRects().length && !e.querySelector('.dock-ask, .dock-ask-words:not(.is-answered), .talk-ask-words')).length === 0"));
await js("document.querySelector('.talk-earlier').click(); true"); await sleep(400);
check("R7 \"Earlier\" opens them", (await js("[...document.querySelectorAll('.talk .dock-turns > *')].filter((e) => e.getClientRects().length).length")) > 0);

// ---------------------------------------------------------------- 5 · More: the places, the way back, Settings; under twelve controls
await js("document.querySelector('.places button.tab').click(); true"); await sleep(600);
const more = await js(`(() => { const s = document.querySelector('.sheet'); return { text: s ? s.innerText : '',
  controls: s ? [...s.querySelectorAll('button, a[href], input, select, textarea')].filter((e) => e.getClientRects().length).length : 99,
  places: s ? [...s.querySelectorAll('.menu-group:first-child button')].map((b) => b.innerText) : [] }; })()`);
for (const k of ["places.deal", "places.map", "places.chain", "places.room"]) check(`More holds ${S[k]}`, more.text.includes(S[k]));
check("More holds the way to the desktop app", more.text.includes(S["talk_place.desktop_app"]));
check("5 More holds Settings, in one word", more.text.includes(S["settings.title"]) && !more.text.includes("Layouts"));
check("5 More has fewer than twelve controls", more.controls < 12, String(more.controls));
const moreRest = more.text.split("\n").filter((l) => !more.places.includes(l.trim())).join("\n");
const moreHit = moreRest.match(APPARATUS);
check("5 More speaks none of the apparatus's words (the places keep their names)", !moreHit, moreHit && moreHit[0]);
await js("document.querySelector('.sheet .link-btn').click(); true"); await sleep(300);

// ---------------------------------------------------------------- a return after an hour: one line, no count; the earlier turns folded
await js("location.hash = '#/deal'; true"); await sleep(900);
await js(`localStorage.setItem('hud.talk.left', JSON.stringify({ at: Date.now() - 2 * 3600 * 1000, owed: [], back: [], lines: [] })); localStorage.setItem('hud.talk.seen_at', String(Date.now() - 2 * 3600 * 1000)); true`);
await send("Page.reload", { ignoreCache: true }); await sleep(2200);
await js("location.hash = '#/talk'; true"); await sleep(2400);
const back = await js(`({ line: document.querySelector('.talk-line').innerText, earlier: !!document.querySelector('.talk-earlier:not([hidden])'),
  shown: [...document.querySelectorAll('.talk .dock-turns > *')].filter((e) => e.getClientRects().length && !e.querySelector('.dock-ask, .dock-ask-words:not(.is-answered), .talk-ask-words') && !e.classList.contains('talk-now')).length })`);
check("a return says what changed in one line", /^While you were away/.test(back.line), back.line);
check("7 the return line carries no count", !/\b(two|three|four|five|six|seven|\d+)\b/i.test(back.line), back.line);
check("the earlier turns are folded above Earlier", back.earlier && back.shown === 0, JSON.stringify(back));
await words("return");

// ---------------------------------------------------------------- the rest state
await open(empty.base, "#/talk", "localStorage.setItem('hud.talk.seen_at', String(Date.now()))");
const rest = await js(`({ line: document.querySelector('.talk-line').innerText, q: !!document.querySelector('.talk-q'), rest: document.querySelector('.talk').dataset.rest })`);
check("the rest state: a greeting, and nothing is asked", /^Good (morning|afternoon|evening)/.test(rest.line) && !rest.q && rest.rest === "true", JSON.stringify(rest));
const restGold = await js(GOLD_OUTSIDE);
check("the rest state: nothing gold", restGold.owed === 0 && !restGold.bad.length, JSON.stringify(restGold));
await words("rest");
await open(empty.base);
check("1 a first sitting with nothing waiting: a greeting, and nothing asked", /^Good (morning|afternoon|evening)[^]*I am Wren\.$/.test(await js("document.querySelector('.talk-line').innerText")) && !(await js("!!document.querySelector('.talk-q')")));

// ---------------------------------------------------------------- the ten-minute offer, once a day
await open(empty.base, "#/talk", "localStorage.setItem('hud.talk.seen_at', String(Date.now())); sessionStorage.setItem('hud.talk.more', '3'); sessionStorage.setItem('hud.talk.dealing', 'true')");
const offer = await js("(document.querySelector('.talk-now') || {}).innerText || ''");
check("after three openings of More, one offer of another way", offer.includes(S["talk_place.switch.yes"]) && offer.includes(S["talk_place.switch.no"]), offer);
await js("[...document.querySelectorAll('.talk-now button')].find((b) => b.innerText === " + JSON.stringify(S["talk_place.switch.no"]) + ").click(); true");
await send("Page.reload", { ignoreCache: true }); await sleep(2200);
check("declined, it is not offered again today", !(await js("(document.querySelector('.talk-now') || {}).innerText || ''")).includes(S["talk_place.switch.yes"]));


// ---------------------------------------------------------------- A4 · the trust layer at its three depths (DESIGN-TALK.md:
// it shows what the body is doing at all times). The stand-in's figures.
{
  const waitFor = async (expr, ms = 15000) => { let v; for (let i = 0; i < ms / 250; i++) { v = await js(expr); if (v) return v; await sleep(250); } return v; };
  const status = () => js("(() => { const s = document.querySelector('.talk-status'); return s && !s.hidden ? s.innerText.replace(/\\s+/g, ' ').trim() : ''; })()");
  const idleNow = () => waitFor("document.querySelector('.talk .dock-stop').hidden", 30000);
  const setDepth = async (d) => { await js(`localStorage.setItem('hud.depth', JSON.stringify(${JSON.stringify(d)})); true`); await send("Page.reload", { ignoreCache: true }); await sleep(2600); };
  const noNull = (label, text) => check(`${label}: a null is left out, never a dash, a zero or a word for nothing`, !/(null|undefined|NaN|—|\[)/.test(text) && !/ · · /.test(text), text);

  // 7 · the knob's default (figures on by default, with a plain view): Working for everyone, Plain one turn down
  await open(rich.base, "#/talk");
  check("A4-7 / 36-1 a first sitting opens at Working, whoever brought them", await js("!localStorage.getItem('hud.depth')") && (await js("document.querySelector('.talk-status')?.dataset.depth")) === "working");
  check("36-1 a first sitting says once, in dust under the status line, how to see less", (await js("document.querySelector('.talk-depth-hint.dust')?.innerText || ''")) === S["talk_place.depth_hint"]);
  await send("Page.reload", { ignoreCache: true }); await sleep(2200);
  check("36-1 the hint is said once, never again", !(await js("!!document.querySelector('.talk-depth-hint')")));
  await open(empty.base, "#/talk", "localStorage.setItem('hud.talk.seen_at', String(Date.now()))");
  check("A4-7 the owner's house opens at Working", (await js("document.querySelector('.talk-status')?.dataset.depth")) === "working");
  // 2 · the status line is true at rest: figures, never a state she is not in
  await open(rich.base, "#/talk", "localStorage.setItem('hud.depth', JSON.stringify('working'))");
  await idleNow();
  const rest = await waitFor("(() => { const s = document.querySelector('.talk-status'); return s && !s.hidden && s.innerText.trim() ? s.innerText.replace(/\\s+/g, ' ').trim() : null; })()", 15000);
  check("36-2 at rest the line shows the figures and never \"thinking\"", !!rest && /context \d+%/.test(String(rest)) && !/thinking/i.test(String(rest)), String(rest));

  // Working: the status line in figures, the acts as folded rows as they happen, the live line, the end line
  await open(rich.base, "#/talk", "localStorage.setItem('hud.depth', JSON.stringify('working'))");
  await idleNow();
  await say("notes");
  const liveRow = await waitFor("(() => { const r = [...document.querySelectorAll('.talk .dock-acts .dock-act-line')].map((e) => e.innerText); return r.length && document.querySelector('.talk .dock-stop') && !document.querySelector('.talk .dock-stop').hidden ? r : null; })()", 12000);
  check("A4-2 Working: a row appears while the turn still runs (not only at its end)", Array.isArray(liveRow) && liveRow.length >= 1, JSON.stringify(liveRow));
  const live = await js("document.querySelector('.talk .dock-live')?.innerText || ''");
  check("A4-3 Working: the live line says what she is doing now and counts", /^(Thinking|Reading|Searching|Running a step|Writing|Writing to you|Working)[^·]* · \d+(\.\d)? s/.test(live), live);
  check("A4-3 never a spinner: no element turns or pulses on the live line", await js("(() => { const l = document.querySelector('.talk .dock-live'); return !l || getComputedStyle(l).animationName === 'none'; })()"));
  await idleNow();
  const acts = await js("[...document.querySelectorAll('.talk .dock-acts')].pop()?.innerText.split('\\n').filter(Boolean) || []");
  check("A4-2 Working: a verb and a count with the time, under ⎿ (\"Read two pages · 0.4 s\")", acts.some((r) => /^⎿\s*Read two pages · \d+(\.\d)? s$/.test(r)) && acts.some((r) => /^⎿\s*Searched once · /.test(r)) && acts.some((r) => /^⎿\s*Ran a step · /.test(r)) && acts.some((r) => /^⎿\s*Wrote a page · /.test(r)), JSON.stringify(acts));
  check("A4-2 Working: the rows are folded; the exact step is one tap away", await js("[...document.querySelectorAll('.talk .dock-act-fold')].every((d) => !d.open)"));
  const lastActs = "[...document.querySelectorAll('.talk ul.dock-acts')].pop()";
  await js(`${lastActs}.querySelector('.dock-act-fold summary').click(); true`); await sleep(200);
  const step = await js(`${lastActs}.querySelector('.dock-act-fold .dock-act-steps')?.innerText || ''`);
  check("A4-2 the tap opens the exact step, word for word", /^Read \/Users\/player\/notes\/hall-costs\.md/.test(step) && /Read \/Users\/player\/notes\/bread-rota\.md/.test(step), step);
  check("36-5 a stand-in's placeholder is never printed as what came back", !/the tool's raw output/.test(step), step);
  const actTimes = (sel) => js(`[...document.querySelectorAll('${sel}')].pop()?.innerText.split('\\n').filter((r) => /^⎿/.test(r)).map((r) => r.replace(/\\s+/g, ' ').trim()) || []`);
  const workingTimes = await actTimes(".talk ul.dock-acts");
  const end = await js("[...document.querySelectorAll('.talk .dock-end')].pop()?.innerText || ''");
  check("A4-4 Working: the end line \"Worked for 14 s · done 3:12 PM\"", /^Worked for \d+(\.\d)? s · done \d{1,2}:\d{2}\s?(AM|PM)$/.test(end), end);
  const line = await status();
  check("A4-1 Working: the status line in figures (model, effort in words, context, this sitting, the week and its reset, the mode)",
    /^Stand in model 1 · effort high · context \d+% · this sitting \$\d+\.\d{2,3} · your week 48%, resets \w{3} \d{1,2}(:\d{2})? (AM|PM) · Manual$/.test(line), line);
  check("36-2 effort is said as \"effort high\", never as a state (\"thinking hard\")", /· effort high ·/.test(line) && !/thinking/.test(line), line);
  check("36-3 the mode by the harness's own name, as the harness gave it", (await js("document.querySelector('.talk-status-mode')?.innerText || ''")) === "Manual");
  check("A4-1 Working: its figures in tabular numerals", await js("getComputedStyle(document.querySelector('.talk-status-line')).fontVariantNumeric.includes('tabular-nums')"));
  noNull("A4-1 Working", line);
  await words("A4 working");

  // 1 · one tap opens the sheet with every figure the host gave and its as-of; the mode's word opens the harness's modes
  await js("document.querySelector('.talk-status-line').click(); true"); await sleep(500);
  const sheet = await js("(() => { const s = document.querySelector('.sheet'); return s ? { text: s.innerText, rows: s.querySelectorAll('.dock-figures dt').length, raw: !!s.querySelector('.dock-figures-raw') } : null; })()");
  check("A4-1 the status sheet: every figure the host gave, and its as-of", sheet && sheet.rows >= 10 && /As of \d{1,2}:\d{2}/.test(sheet.text) && /a stand-in, not a real agent/.test(sheet.text) && sheet.raw, JSON.stringify(sheet && { rows: sheet.rows, text: sheet.text.slice(0, 300) }));
  const raw = await waitFor("(() => { const p = document.querySelector('.sheet .dock-figures-raw'); return p && /\"raw\"/.test(p.textContent) ? p.textContent : null; })()", 4000);
  check("A4-1 and everything the harness gave, raw, one fold away (GET /agent/figures)", !!raw && /usage_update/.test(raw), String(raw).slice(0, 200));
  check("A4-7 the knob is in the status sheet too: Plain · Working · Full", (await js("[...document.querySelectorAll('.sheet .dock-depth button')].map((b) => b.innerText).join(' · ')")) === "Plain · Working · Full");
  await js("document.querySelector('.sheet .sheet-head .link-btn').click(); true"); await sleep(400);
  await js("document.querySelector('.talk-status-mode').click(); true");
  const modes = await waitFor("(() => { const b = [...document.querySelectorAll('.sheet [role=menuitemradio]')]; return b.length ? b.map((x) => x.innerText + (x.getAttribute('aria-checked') === 'true' ? ' *' : '')) : null; })()", 4000);
  check("A4-1 the mode's word opens the harness's own modes, in words, the current one marked; none that asks about nothing", Array.isArray(modes) && modes.length >= 2 && modes.some((m) => / \*$/.test(m)) && !modes.some((m) => /Bypass/i.test(m)), JSON.stringify(modes));
  const modeNames = await js("[...document.querySelectorAll('.sheet [role=menuitemradio] .dock-mode-name')].map((x) => x.innerText)");
  check("36-3 every mode the host puts on a page's face, by the harness's own name, never renamed", JSON.stringify(modeNames) === JSON.stringify(["Manual", "Accept edits", "Plan", "Auto"]), JSON.stringify(modeNames));
  check("36-3 the sheet says in one line that model and effort are not set here", (await js("document.querySelector('.sheet .dock-modes-fixed')?.innerText || ''")) === S["dock.trust.modes.fixed"]);
  await js("document.querySelector('.sheet .sheet-head .link-btn').click(); true"); await sleep(400);

  // 3 · the thinking clock counts, dim, from the first second
  await say("slow");
  const t1 = await waitFor("(() => { const x = document.querySelector('.talk .dock-live')?.innerText || ''; return /^Thinking · \\d/.test(x) ? x : null; })()", 1500);
  await sleep(2100);
  const t2 = await js("document.querySelector('.talk .dock-live')?.innerText || ''");
  const sec = (x) => Number((String(x).match(/· (\d+(\.\d)?) s/) || [])[1]);
  check("A4-3 \"Thinking · 1 s\" within a second and a half of the turn starting", !!t1, String(t1));
  check("A4-3 the seconds count while she thinks", sec(t2) > sec(t1), `${t1} → ${t2}`);
  check("A4-3 the thinking line is dim (dust)", await js("document.querySelector('.talk .dock-live').classList.contains('dust')"));
  check("A4-8 Stop is in view while her turn runs", await js("!document.querySelector('.talk .dock-stop').hidden"));
  check("36-4 while her turn runs, its label is \"Stop\"", (await js("document.querySelector('.talk .dock-stop').innerText")) === S["dock.stop"]);
  await idleNow();

  // 6 · notices as her plain lines
  await say("fold the talk");
  const folded = await waitFor(`[...document.querySelectorAll('.talk .dock-turn--notice')].map((e) => e.innerText.trim()).find((x) => x === ${JSON.stringify(S["dock.status.notice.compacted"])})`, 8000);
  check("A4-6 compaction is said in her one plain line", !!folded, String(folded));
  await idleNow();
  await say("spent");
  const spent = await waitFor("[...document.querySelectorAll('.talk .dock-turn--notice')].map((e) => e.innerText).find((x) => /cannot go on/.test(x))", 8000);
  check("A4-6 a spent window is said plainly, and never promises to carry on", !!spent && !/carry on/.test(spent), String(spent));
  await idleNow();

  // Full: the Working line and tokens in and out, the cache, the version; every row open with its raw step; the end line with tokens and cost
  await setDepth("full");
  const fline = await status();
  check("A4-1 Full: the Working line, then in and out this sitting, the cache and the adapter's version",
    /^Stand in model 1 · effort high · context \d+% · this sitting \$[\d.]+ · your week 48%, resets .+ · [\d.]+[kM]? of [\d.]+[kM]? held · [\d.]+k? in, [\d.]+k? out this sitting · cache \d+% read · adapter 0\.1 · a stand-in, not a real agent · Manual$/.test(fline), fline);
  noNull("A4-1 Full", fline);
  const fullTimes = (await js(`[...document.querySelectorAll('.talk ul.dock-acts')].map((u) => [...u.querySelectorAll('.dock-act-line')].map((r) => r.innerText.replace(/\\s+/g, ' ').trim()))`)).find((rows) => rows.some((r) => /Read two pages/.test(r))) || [];
  check("36-5 the same acts show the same times at Working and at Full", workingTimes.length >= 4 && JSON.stringify(workingTimes) === JSON.stringify(fullTimes), JSON.stringify([workingTimes, fullTimes]));
  check("36-5 no act claims 0.0 s it did not take", !fullTimes.some((r) => / 0\.0 s$/.test(r)), JSON.stringify(fullTimes));
  check("A4-2 Full: every row open with its raw step", await js("(() => { const d = [...document.querySelectorAll('.talk .dock-acts .dock-act-fold')]; return d.length > 0 && d.every((x) => x.open && x.querySelector('.dock-act-raw')); })()"));
  const fend = await js("[...document.querySelectorAll('.talk .dock-end')].map((e) => e.innerText).find((x) => / in · /.test(x)) || ''");
  check("A4-4 Full: the end line with tokens in and out and the cost", /^Worked for .+ · done .+ · [\d.]+k? in · [\d.]+k? out · \$[\d.]+$/.test(fend), fend);

  // Plain: words, no figures; one quiet line per turn; no end line unless something left
  await setDepth("plain");
  const pline = await status();
  check("A4-1 / 36-2 Plain: the status line in words, one voice, true at rest (\"About a tenth of what I can hold is in use; the week is half used\")",
    /^(Little of what I can hold is in use|About [a-z ]+ of what I can hold is in use|Near the edge of what I can hold); the week is [a-z ]+ used$/.test(pline) && !/thinking|today/.test(pline), pline);
  check("Plain: the line opens no table of figures", await js("!document.querySelector('.talk-status button')"));
  check("A4-1 Plain: no figure on its face", !/\d/.test(pline), pline);
  check("A4-2 Plain: one quiet line per turn of acts, no rows", await js("!document.querySelector('.talk ul.dock-acts') && [...document.querySelectorAll('.talk .dock-acts--plain')].length >= 1"));
  check("A4-4 Plain: no end line when nothing left this computer", await js("!document.querySelector('.talk .dock-end')"));
  await words("A4 plain");

  // 7 · the knob by a word, and in her sheet
  await say("show me more");
  check("A4-7 \"show me more\" turns Plain to Working, said back in one line", (await js("JSON.parse(localStorage.getItem('hud.depth'))")) === "working"
    && (await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''")).includes(S["talk_place.depth_said.working"]));
  check("A4-7 and the status line follows at once", (await js("document.querySelector('.talk-status')?.dataset.depth")) === "working");
  await say("show me less");
  check("A4-7 \"show me less\" turns it back to Plain", (await js("JSON.parse(localStorage.getItem('hud.depth'))")) === "plain");
  await say("show me less");
  check("\"show me less\" at Plain says the least line, never \"everything\"", (await js("[...document.querySelectorAll('.talk .talk-turn')].map((e) => e.innerText).pop() || ''")).includes(S["talk_place.depth_said.least"]));
  await js("document.querySelector('.talk-door').click(); true"); await sleep(500);
  const knob = await js("[...document.querySelectorAll('.sheet .dock-depth button')].map((b) => b.innerText + (b.getAttribute('aria-checked') === 'true' ? ' *' : ''))");
  check("A4-7 her sheet holds the knob in one word each: \"How much you see: Plain · Working · Full\"", JSON.stringify(knob) === JSON.stringify(["Plain *", "Working", "Full"]) && (await js("document.querySelector('.sheet').innerText")).toLowerCase().includes(S["dock.depth.title"].toLowerCase()), JSON.stringify(knob));
  const controls = await js("[...document.querySelectorAll('.sheet button, .sheet a')].filter((e) => e.getClientRects().length).length");
  check("A4-7 her sheet stays at most eight controls and Close, with the knob", controls <= 9, String(controls));
  await js("[...document.querySelectorAll('.sheet .dock-depth button')].find((b) => b.innerText === 'Working').click(); true"); await sleep(400);
  check("A4-7 the knob's tap is kept on this device", (await js("JSON.parse(localStorage.getItem('hud.depth'))")) === "working");

  // 5 · a worker as a row beneath the stream: its name, what it is on, its time running, Stop; folded away when none
  await idleNow();
  await say("have a worker draft the notes");
  await idleNow();
  await say("start it");
  const wrow = await waitFor("(() => { const r = document.querySelector('.talk .dock-workers:not([hidden]) .dock-worker'); return r ? r.innerText.replace(/\\s+/g, ' ') : null; })()", 10000);
  check("A4-5 a worker at work is a row: name · what it is on · its time", !!wrow && /draft the notes/.test(wrow) && /· \d+(\.\d)? s|· \d+ m \d+ s/.test(wrow) && /Stop/.test(wrow), String(wrow));
  check("36-4 one Stop per thing: one worker's row carries its Stop, and the main Stop stays out", (await js("document.querySelectorAll('.talk .dock-worker-stop').length")) === 1 && await js("document.querySelector('.talk .dock-stop').hidden"));
  await js("document.querySelector('.talk .dock-worker-stop').click(); true");
  const gone = await waitFor("!document.querySelector('.talk .dock-workers .dock-worker') || document.querySelector('.talk .dock-workers').hidden", 12000);
  check("A4-5 its Stop stops it, and the rows fold away when none runs", !!gone);
  await words("A4 working, after a worker");
  await oneScreen("A4 working");
}

// ---------------------------------------------------------------- 5 · the strings the Talk owns speak none of the apparatus's words; R5 the words
const own = Object.entries(S).filter(([k, v]) => typeof v === "string" && (/^talk_place\./.test(k) || /^dock\.about\./.test(k) || ["top.menu", "settings.title", "dock.over_asking", "dock.put_in_deal", "dock.stop", "dock.send"].includes(k)));
const ownHits = own.filter(([k, v]) => k !== "talk_place.desktop_app" && APPARATUS.test(v)).map(([k, v]) => `${k}: ${v}`);
check("5 the Talk's own strings speak none of the apparatus's words", !ownHits.length, ownHits.join(" | "));
check("R5 where words go is one sentence everywhere: the voice sheet says the host's own", S["dock.voice.stays"] === S["dock.first.words"]);
const allowance = Object.entries(S).filter(([, v]) => typeof v === "string" && /\ballowance\b/i.test(v)).map(([k]) => k);
check("R5 \"allowance\" is \"your week's use\"", !allowance.length, allowance.join(", "));
check("T18 the worker's card says \"Start it\"; the ask's later is \"Later, in the Deal\"", S["dock.answer.start_worker"] === "Start it" && S["dock.answer.postpone"] === "Later, in the Deal");
check("T8 her presence line is \"Thinking · twenty seconds\", never the machine", S["dock.work.working"] === "Thinking" && S["dock.thinking_for"] === "{n} seconds");
const rich0 = fs.readFileSync(path.join(HUD, "fixtures", "deal-rich.json"), "utf8");
check("R5 the sample's words: \"Confirm\", and the witness named by role", !/\bRatify\b/.test(rich0) && !/steward is your witness/.test(rich0));
check("R5 the first card says its day once", !/It was asked for by Friday/.test(rich0));

ws.close(); chrome.kill(); rich.kill(); empty.kill();
// the agent host the stand-in ran under is this proof's own: stopped by its folder
try { execFileSync("pkill", ["-f", tmp]); } catch { /* none left */ }
await sleep(500);
try { fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 5 }); } catch { /* Chrome still closing */ }
if (fails.length) console.log((rich.err + empty.err).slice(-800));
console.log(fails.length ? `talk: ${fails.length} failing` : "talk: all pass");
process.exit(fails.length ? 1 : 0);
