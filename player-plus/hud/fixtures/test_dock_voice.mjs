// test_dock_voice.mjs: the layered voice in the dock (DESIGN-DOCK "The layered voice"), proven in
// headless muted Chrome on a phone's viewport (390 × 844, night) against serve.py and the stand-in
// agent (agents-fake.json). Nothing is ever played: Chrome runs with --mute-audio, the browser's
// listener and its voice are stand-ins set into the page before it loads, and every reading aloud
// is proven by what the stand-in voice was asked, never by ear.
//
//   node hud/fixtures/test_dock_voice.mjs        (test_dock.py runs it when node and Chrome are here)
//   PORT=8774 SHOTS=<folder> node hud/fixtures/test_dock_voice.mjs   also writes voice-*.png there
//
// Proves: the microphone is at the line to speak, 44 px; the first tap asks once, in words, with
// why; a tap keeps it listening, said in words ("Listening · Tap to stop"); holding it puts words
// not yet sure in dust and sure words in the line; letting go sends nothing unless the person chose
// "Send when I let go", and then sends once; with "Read your replies aloud" off nothing is read; on,
// a completed turn is read once, in the calmest voice on the device (never a novelty voice), with
// "Speaking · Tap to stop" on the turn, and a tap stops it; starting to speak stops her voice and
// the microphone was never open while she spoke; a page reopened on the conversation reads nothing;
// a page whose navigator.webdriver is true or opened ?muted reads nothing (this headless Chrome's own
// navigator.webdriver is false, so the guard is proven with it set true); with no listener anywhere the microphone is not shown. And voice
// mode, the hands-free loop: one switch at the head, asked once; three turns, each heard (Hearing…),
// sent as text after the pause, Thinking, then spoken whole (Speaking · tap to stop) with the
// microphone closed, then listening again; a tap on the conversation stops her at once and it
// listens again; a spoken "stop" ends the loop and is never sent; dimmed, the state stays
// readable over the dark ground; no switch on a page navigator.webdriver marks.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import net from "node:net";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!fs.existsSync(CHROME)) { console.log("dock voice: Chrome not found, skipped"); process.exit(0); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const S = JSON.parse(fs.readFileSync(path.join(HUD, "strings.json"), "utf8"));
const SHOTS = process.env.SHOTS || null;

// ---------------------------------------------------------------- the server and the stand-in agent
const tmp = fs.mkdtempSync(path.join(process.env.SCRATCH || os.tmpdir(), "dock-voice-"));
const free = () => new Promise((res) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
const PORT = Number(process.env.PORT) || await free();
const serve = spawn("python3", ["-I", path.join(HUD, "serve.py"), "--fixture", "fresh", "--port", String(PORT),
  "--agents", path.join(HUD, "fixtures", "agents-fake.json"), "--hq", path.join(tmp, "hq")], { cwd: HUD, stdio: ["ignore", "ignore", "pipe"] });
let serveErr = ""; serve.stderr.on("data", (d) => { serveErr += d; });
for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${PORT}/token`); if (r.ok) break; } catch { /* not yet */ } await sleep(150); }

// ---------------------------------------------------------------- Chrome, muted
const DBG = 9600 + Math.floor(Math.random() * 150);
const prof = fs.mkdtempSync(path.join(tmp, "chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${DBG}`, "--mute-audio", "--no-first-run",
  "--no-default-browser-check", `--user-data-dir=${prof}`, "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let ws, id = 0, errors = [];
const waiters = new Map();
for (let i = 0; i < 60 && !ws; i++) {
  try { const l = await (await fetch(`http://127.0.0.1:${DBG}/json/list`)).json(); const p = l.find((x) => x.type === "page"); if (p) ws = new WebSocket(p.webSocketDebuggerUrl); } catch { /* not yet */ }
  if (!ws) await sleep(200);
}
await new Promise((r) => ws.addEventListener("open", r));
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiters.has(msg.id)) { waiters.get(msg.id)(msg); waiters.delete(msg.id); return; }
  if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
});
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiters.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
await send("Runtime.enable"); await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });

// the stand-ins, set into every page before it loads: a listener held on the device, and a voice
// that only records what it was asked. ?wd=false makes navigator.webdriver false; ?no_sr removes the listener.
await send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => {
  const P = new URLSearchParams(location.search);
  window.__voice = { speaks: [], cancels: 0, recs: 0, webdriver_native: navigator.webdriver,
    end() { const u = window.__voice.last; window.speechSynthesis.speaking = false; window.__voice.last = null; if (u && u.onend) u.onend({}); } };
  if (P.get("wd") === "false" || P.get("wd") === "true") { const wd = P.get("wd") === "true"; Object.defineProperty(Navigator.prototype, "webdriver", { get: () => wd, configurable: true }); }
  window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; this.voice = null; this.lang = ""; this.rate = 1; this.pitch = 1; } };
  if (P.has("no_sr")) { delete window.SpeechRecognition; delete window.webkitSpeechRecognition;
    Object.defineProperty(window, "webkitSpeechRecognition", { value: undefined, configurable: true });
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, configurable: true }); }
  else {
    class FakeRec {
      constructor() { this.processLocally = false; window.__voice.recs++; }
      start() { this.on = true; window.__rec = this; window.__voice.listening = true; }
      stop() { this.on = false; window.__voice.listening = false; setTimeout(() => this.onend && this.onend(), 30); }
      abort() { this.stop(); }
      emit(parts) { const results = parts.map(([t, f]) => { const r = [{ transcript: t, confidence: 0.9 }]; r.isFinal = f; return r; });
        this.onresult && this.onresult({ results, resultIndex: 0 }); }
    }
    FakeRec.available = async (o) => (o && o.processLocally ? "available" : "unavailable");
    Object.defineProperty(window, "SpeechRecognition", { value: FakeRec, configurable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", { value: FakeRec, configurable: true });
  }
  const voices = [{ name: "Zarvox", lang: "en-US", localService: true, voiceURI: "Zarvox" },
    { name: "Google US English", lang: "en-US", localService: false, voiceURI: "net" },
    { name: "Samantha", lang: "en-US", localService: true, voiceURI: "Samantha", default: true },
    { name: "Thomas", lang: "fr-FR", localService: true, voiceURI: "Thomas" }];
  const synth = { speaking: false, pending: false, paused: false, getVoices: () => voices,
    speak(u) { window.__voice.speaks.push({ text: u.text, voice: u.voice && u.voice.name, mic_open: !!window.__voice.listening }); this.speaking = true; window.__voice.last = u; },
    cancel() { window.__voice.cancels++; this.speaking = false; }, pause() {}, resume() {}, addEventListener() {}, removeEventListener() {} };
  Object.defineProperty(window, "speechSynthesis", { get: () => synth, configurable: true });
})();` });

async function waitFor(fn, ms = 20000) { const end = Date.now() + ms; while (Date.now() < end) { if (await fn()) return true; await sleep(250); } return false; }
const fails = [];
const check = (name, ok, detail) => { if (!ok) fails.push(name); console.log(`${ok ? "pass" : "FAIL"}  ${name}${!ok && detail ? " — " + detail : ""}`); };
const shot = async (name) => {
  if (!SHOTS) return;
  const r = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(SHOTS, `voice-${name}.png`), Buffer.from(r.result.data, "base64"));
  console.log("shot", path.join(SHOTS, `voice-${name}.png`));
};
let visits = 0;   // each visit a new page, never a jump within the last one
async function open(q, clear = true) {
  errors = [];
  await send("Page.navigate", { url: `http://127.0.0.1:${PORT}/index.html?theme=night&visit=${++visits}${q ? "&" + q : ""}#/deal` });
  await sleep(1500);
  if (clear) { await js("localStorage.clear(); sessionStorage.clear(); true"); await send("Page.reload", { ignoreCache: true }); await sleep(1000); }
  await waitFor(() => js("!!document.querySelector('.dock-bar') && !document.querySelector('.dock').hidden"), 15000);
  await js("(() => { const b = document.querySelector('.dock-bar'); if (b) b.click(); return !!b; })()");
  await sleep(900);
}
const mic = () => js(`(() => { const m = document.querySelector('.dock-mic'); if (!m || m.hidden) return null; const r = m.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height, pressed: m.getAttribute('aria-pressed'), label: m.getAttribute('aria-label') }; })()`);
const mouse = (type, m) => send("Input.dispatchMouseEvent", { type, x: m.x, y: m.y, button: "left", buttons: type === "mousePressed" ? 1 : 0, clickCount: 1, pointerType: "mouse" });
const tap = async () => { const m = await mic(); await mouse("mousePressed", m); await sleep(60); await mouse("mouseReleased", m); await sleep(250); };
const said = () => js("(document.querySelector('.dock-voice-state') || {}).textContent || ''");
const line = () => js("document.querySelector('.dock-input').value");
const youTurns = () => js("[...document.querySelectorAll('.dock-turn--you')].map((e) => e.innerText.trim())");
const doneTurns = () => js("document.querySelectorAll('.dock-turn--agent .dock-quietfoot').length");
const voiceLog = () => js("window.__voice");
async function say(text) {
  const before = await doneTurns();
  await js(`(() => { const i = document.querySelector('.dock-input'); i.value = ${JSON.stringify(text)}; i.dispatchEvent(new Event('input')); document.querySelector('.dock-send').click(); return true; })()`);
  return waitFor(async () => (await doneTurns()) > before, 25000);
}

// ---------------------------------------------------------------- 1. speak to it
await open("wd=false");
let m = await mic();
check("the microphone is at the line to speak", !!m && (await js("!!document.querySelector('.dock-inputrow .dock-mic')")), JSON.stringify(m));
check("the microphone is 44 px", m && Math.round(m.w) === 44 && Math.round(m.h) === 44, m && `${m.w}×${m.h}`);
await tap();
const ask = await js("(() => { const s = document.querySelector('.sheet'); return s ? s.innerText : ''; })()");
check("the first tap asks once, in words", ask.includes(S["dock.voice.ask_title"]) && ask.includes(S["dock.voice.ask_body"]), ask.slice(0, 120));
check("the ask says why", ask.includes(S["dock.voice.ask_why"]));
check("the ask says the words stay here", ask.includes(S["dock.voice.stays"]));
check("nothing listened before the yes", (await voiceLog()).recs === 0);
await js(`(() => { const b = [...document.querySelectorAll('.sheet button')].find((x) => x.textContent.trim() === ${JSON.stringify(S["dock.voice.ask_yes"])}); b.click(); return true; })()`);
await sleep(500);
m = await mic();
check("after the yes it listens, hands-free", m && m.pressed === "true", JSON.stringify(m));
check("listening is said in words, with how to stop", (await said()) === `${S["dock.voice.listening"]} · ${S["dock.voice.tap_to_stop"]}`, await said());
await js("window.__rec.emit([['What needs me', true], [' this morning', false]])");
await sleep(200);
await shot("listening-390-night");
await tap();
await sleep(200);
check("a tap stops it; the words heard stay in the line to read", (await line()) === "What needs me this morning", await line());
check("the microphone is closed after", (await mic()).pressed === "false");
check("nothing was sent on a tap with the preference off", (await youTurns()).length === 0);
await js("(() => { const i = document.querySelector('.dock-input'); i.value = ''; return true; })()");

// hold to talk: dust while unsure, ink in the line when sure; let go sends nothing by default
m = await mic();
await mouse("mousePressed", m);
await sleep(500);
await js("window.__rec.emit([['what needs', false]])");
await sleep(150);
const dust = await js(`(() => { const e = document.querySelector('.dock-voice-interim'); const p = document.createElement('i'); p.className = 'dust'; document.body.append(p);
  const c = getComputedStyle(p).color; p.remove(); return e && !e.hidden ? { text: e.textContent, dust: getComputedStyle(e).color === c } : null; })()`);
check("while held, words not yet sure are in dust", dust && dust.text === "what needs" && dust.dust, JSON.stringify(dust));
check("while held, the line holds only sure words", (await line()) === "", await line());
check("while held, listening is said in words", (await said()).startsWith(S["dock.voice.listening"]), await said());
await js("window.__rec.emit([['What needs me today?', true]])");
await sleep(150);
check("sure words are in the line", (await line()) === "What needs me today?", await line());
check("the dust empties when the words are sure", await js("document.querySelector('.dock-voice-interim').hidden"));
await mouse("mouseReleased", m);
await sleep(400);
check("let go: the words wait in the line, nothing sent", (await youTurns()).length === 0 && (await line()) === "What needs me today?", JSON.stringify(await youTurns()));

// with "Send when I let go": sent once, on release
await js("localStorage.setItem('hud.voice_send', 'true'); document.querySelector('.dock-input').value = ''; true");
m = await mic();
await mouse("mousePressed", m);
await sleep(500);
await js("window.__rec.emit([['Good morning.', true]])");
await mouse("mouseReleased", m);
const sent = await waitFor(async () => (await youTurns()).some((x) => x.includes("Good morning.")), 8000);
check("with the preference on, let go sends the words once", sent && (await youTurns()).filter((x) => x.includes("Good morning.")).length === 1, JSON.stringify(await youTurns()));
await waitFor(async () => (await doneTurns()) >= 1, 20000);
await sleep(600);
check("with reading aloud off, a finished turn is not read", (await voiceLog()).speaks.length === 0, JSON.stringify((await voiceLog()).speaks));

// ---------------------------------------------------------------- 2. hear it
await js("localStorage.setItem('hud.voice_read', 'true'); true");
check("a turn finished", await say("Who are you?"));
await sleep(500);
let v = await voiceLog();
check("with reading aloud on, the finished turn is read once", v.speaks.length === 1, JSON.stringify(v.speaks));
check("in the calmest voice on the device", v.speaks[0] && v.speaks[0].voice === "Samantha", v.speaks[0] && v.speaks[0].voice);
check("the microphone was closed while she spoke", v.speaks.every((x) => !x.mic_open));
const mark = await js("(() => { const b = document.querySelector('.dock-voice-speaking'); return b ? b.innerText.trim() : null; })()");
check("the turn carries Speaking · Tap to stop", mark === `${S["dock.voice.speaking"]} · ${S["dock.voice.tap_to_stop"]}`, mark);
await shot("speaking-390-night");
await js("document.querySelector('.dock-voice-speaking').click(); true");
await sleep(200);
v = await voiceLog();
check("a tap stops her voice", v.cancels >= 1 && !(await js("!!document.querySelector('.dock-voice-speaking')")));
// the earpiece rule: she stops when the person starts speaking
check("a second turn finished", await say("Tell me the deal."));
await sleep(400);
v = await voiceLog();
check("each turn is read once, never twice", v.speaks.length === 2, String(v.speaks.length));
const cancels = v.cancels;
m = await mic();
await mouse("mousePressed", m);
await sleep(300);
v = await voiceLog();
check("starting to speak stops her voice", v.cancels > cancels && !(await js("!!document.querySelector('.dock-voice-speaking')")));
check("and then it listens", (await mic()).pressed === "true");
await mouse("mouseReleased", m);
await sleep(300);
await js("document.querySelector('.dock-input').value = ''; true");
check("no script errors while speaking and listening", errors.length === 0, errors.join(" | "));

// ---------------------------------------------------------------- 3. voice mode: the hands-free loop
await open("wd=false");
const stage = () => js("(() => { const s = document.querySelector('.dock-voice-stage'); return s && !s.hidden ? s.querySelector('.dock-voice-stage-word').textContent : null; })()");
const modeOn = () => js("(document.querySelector('.dock-voice-mode') || {}).getAttribute?.('aria-pressed') || null");
const recs0 = async () => (await voiceLog()).recs;
check("voice mode is one switch at the head", (await js("!!document.querySelector('.dock-head .dock-voice-mode')")) && (await modeOn()) === "false");
await js("document.querySelector('.dock-voice-mode').click(); true");
await sleep(400);
check("voice mode asks once before it listens", (await js("(document.querySelector('.sheet') || {}).innerText || ''")).includes(S["dock.voice.ask_title"]));
await js(`(() => { [...document.querySelectorAll('.sheet button')].find((x) => x.textContent.trim() === ${JSON.stringify(S["dock.voice.ask_yes"])}).click(); return true; })()`);
await sleep(500);
check("voice mode is on", (await modeOn()) === "true");
check("state: Listening", (await stage()) === S["dock.voice.listening"], await stage());
await shot("mode-listening-390-night");
const turns0 = await doneTurns();
const loopTurn = async (words, label) => {
  const n = (await voiceLog()).speaks.length;
  await js(`window.__rec.emit([[${JSON.stringify(words.slice(0, 6))}, false]])`);
  await sleep(150);
  const hearing = await stage();
  if (label === 1) await shot("mode-hearing-390-night");
  await js(`window.__rec.emit([[${JSON.stringify(words)}, true]])`);
  const sawThinking = await waitFor(async () => (await stage()) === S["dock.voice.thinking"], 3000);
  if (label === 1 && sawThinking) await shot("mode-thinking-390-night");
  const spoke = await waitFor(async () => (await voiceLog()).speaks.length > n, 25000);
  return { hearing, sawThinking, spoke };
};
let r = await loopTurn("Who are you?", 1);
check("turn 1: Hearing… while words come", r.hearing === S["dock.voice.hearing"], r.hearing);
check("turn 1: the words are sent after the pause, as text", (await youTurns()).some((x) => x.includes("Who are you?")));
check("turn 1: Thinking", r.sawThinking);
check("turn 1: her turn is spoken when complete", r.spoke);
check("turn 1: Speaking · tap to stop", (await stage()) === S["dock.voice.mode_speaking"], await stage());
check("turn 1: the microphone is closed while she speaks", !(await voiceLog()).listening && (await voiceLog()).speaks.every((x) => !x.mic_open));
await shot("mode-speaking-390-night");
let recs = await recs0();
await js("window.__voice.end(); true");
await sleep(300);
check("turn 1: then listening again", (await stage()) === S["dock.voice.listening"] && (await recs0()) === recs + 1 && (await voiceLog()).listening);
r = await loopTurn("Tell me the deal.", 2);
check("turn 2: spoken", r.spoke);
const c0 = (await voiceLog()).cancels;
await js("document.querySelector('.dock-scroll').click(); true");
await sleep(300);
check("turn 2: a tap on the conversation stops her at once", (await voiceLog()).cancels > c0 && (await stage()) === S["dock.voice.listening"], await stage());
check("turn 2: and it listens again", (await voiceLog()).listening);
r = await loopTurn("What is due today?", 3);
check("turn 3: spoken", r.spoke);
await js("window.__voice.end(); true");
await sleep(300);
check("three turns landed as text in the conversation", (await doneTurns()) >= turns0 + 3, `${await doneTurns()} after ${turns0}`);
await js("window.__rec.emit([['Stop.', true]])");
await waitFor(async () => (await modeOn()) === "false", 3000);
check("a spoken stop ends voice mode", (await modeOn()) === "false" && (await stage()) === null);
check("the stop is not sent to your agent", !(await youTurns()).some((x) => /^stop\.?$/i.test(x)));
check("the microphone is closed after the loop", !(await voiceLog()).listening);
await js("localStorage.setItem('hud.voice_dim', 'true'); document.querySelector('.dock-voice-mode').click(); true");
await sleep(600);
const dim = await js("(() => { const s = document.querySelector('.dock-voice-stage'); const cs = getComputedStyle(s); return { fixed: cs.position === 'fixed', ground: cs.backgroundColor, word: s.innerText }; })()");
check("dimmed: the stage covers the screen, the state still readable", dim.fixed && dim.word.includes(S["dock.voice.listening"]), JSON.stringify(dim));
await shot("mode-dim-390-night");
await js("document.querySelector('.dock-voice-leave').click(); true");
await sleep(300);
check("Leave voice mode ends it", (await modeOn()) === "false");
check("no script errors in voice mode", errors.length === 0, errors.join(" | "));

// ---------------------------------------------------------------- 4. the guards
await open("wd=false", false);
await sleep(2500);
check("a page reopened on the conversation reads nothing on load", (await voiceLog()).speaks.length === 0, JSON.stringify((await voiceLog()).speaks));
await open("", false);
v = await voiceLog();
// found 2026-10-25: Chrome --headless=new driven over the debugging port says navigator.webdriver
// is false, so the guard is proven with it set true; ?muted is the flag a fixture sets
console.log(`note  this headless Chrome's own navigator.webdriver: ${v.webdriver_native}`);
await open("wd=true", false);
check("navigator.webdriver true: no voice mode switch", !(await js("!!document.querySelector('.dock-voice-mode')")));
check("a turn finished under webdriver", await say("Who are you?"));
await sleep(600);
check("navigator.webdriver true: nothing is read, though reading aloud is on", (await voiceLog()).speaks.length === 0, JSON.stringify((await voiceLog()).speaks));
await open("wd=false&muted=1", false);
check("a turn finished, muted", await say("Who are you?"));
await sleep(600);
check("?muted: nothing is read", (await voiceLog()).speaks.length === 0);
await open("wd=false&no_sr", false);
check("no listener on the device and none on the computer: no microphone", (await mic()) === null);
check("no script errors", errors.length === 0, errors.join(" | "));

ws.close(); chrome.kill(); serve.kill();
// the stand-in agent's host was started on the first word: stop it too
try { const h = JSON.parse(fs.readFileSync(path.join(tmp, "hq", ".agent-host"), "utf8")); if (h.pid) process.kill(h.pid, "SIGTERM"); } catch { /* not started */ }
await sleep(500);
try { fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 5 }); } catch { /* Chrome still closing */ }
if (fails.length && serveErr) console.log(serveErr.slice(-800));
console.log(fails.length ? `dock voice: ${fails.length} failing` : "dock voice: all pass");
process.exit(fails.length ? 1 : 0);
