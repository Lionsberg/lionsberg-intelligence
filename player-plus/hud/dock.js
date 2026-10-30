// dock.js: the dock, the conversation pane of the ICE (DESIGN-DOCK.md): a letter, not a log; the field turning while the agent works; the
// work it did folded into the margin; the ways behind one quiet button, the agent's own name).
//
// You speak with your agent beside The Deal, never instead of it. The shell mounts this pane
// once, in the slot "dock", in every layout (shell.js): a foot bar on a phone that opens as a
// sheet leaving The Deal's top line in view; a foot bar and a right-hand pane on a tablet; a
// rail at the right edge on a desktop that opens to a third column.
//
// What it reads: ctx.state.hud.agents, ctx.state.hud.dock, ctx.state.hud.phone, the Deal's
// cards and owed.proposals, and the conversation's own stream (state.js agent.stream). What it
// writes: record acts through ctx.act (a margin line agreed, from the person's own tap), and
// the dock's calls in state.js (agent.*, discern, phone.*). It never fetches itself.
//
// Two views of the same conversation, one button apart: the ICE view (turns, context cards, inks, the margin) and the
// terminal view (the same stream as a plain monospace transcript, raw tool lines included, with
// an input line), so nothing is lost and the raw stream is there when wanted. And a command
// line: a pseudo-terminal the host starts on the player's tap, in the same home, for the
// harness or any command. It is a second conversation with your agent in the same home, never
// the same live conversation, until the harness offers both at once; the pane says so.
//
// Everything your agent sends is data: set as text, never as markup; no image is fetched; a
// link shows its whole address. No sound unasked: her words are read aloud only when the person
// has turned that on, on this device, and never by a page a test drives (voiceSilenced). No drawn
// light: no spinner, no dots, no glow, and none for listening or speaking either.

import { agent as A, discern, phone as P, voice, ON_PHONE, store, setPref } from "./state.js";
import { renderAsk, question as askQuestion, plainLines, askWords, actYes, workerYes, noPaths } from "./dock-card.js";
import { renderMargin } from "./margin.js";
import { handoffText } from "./bodies-talk.js";

// The command line's output as plain text: a small line terminal. A cursor sent to a column
// (CSI n G, the way the harness draws its spaces) or moved forward (CSI n C) leaves the spaces it
// skips; a carriage return writes over the line; a cursor sent to a new row is a new line; an
// erase to the end of the line erases. Device-control and operating-system strings (ESC P … ST,
// ESC ] … BEL or ST, ESC _ ^ X … ST) and every other control sequence (CSI with any parameter
// bytes, ESC [ > 0 q among them) are dropped whole. A sequence split across two reads is held
// until it is whole. makeTerminal().write(text) returns the whole text so far.
export function makeTerminal(keep = 3000) {
  let lines = [""], col = 0, carry = "";
  const TOKEN = /\x1b[P_^X\]][\s\S]*?(?:\x1b\\|\x07)|\x1b\[([0-?]*)[ -\/]*([@-~])|\x1b[()*+][0-9A-Za-z]|\x1b[=>78DMc]|\r\n|[\s\S]/g;
  const PARTIAL = /\x1b(?:[P_^X\]](?:(?!\x1b\\|\x07)[\s\S])*|\[[0-?]*[ -\/]*|[()*+])?$/;
  const newline = () => { lines.push(""); col = 0; if (lines.length > keep) lines = lines.slice(-keep); };
  const put = (ch) => {
    let L = lines[lines.length - 1];
    if (L.length < col) L += " ".repeat(col - L.length);
    lines[lines.length - 1] = L.slice(0, col) + ch + L.slice(col + 1);
    col += 1;
  };
  function write(text) {
    let s = carry + String(text || "");
    const m = s.match(PARTIAL);
    carry = m ? m[0] : "";
    if (m) s = s.slice(0, s.length - m[0].length);
    for (const t of s.matchAll(TOKEN)) {
      const tok = t[0];
      if (t[2]) {                       // a control sequence: CSI params final
        const nums = (t[1] || "").replace(/[^0-9;]/g, "").split(";");
        const n = Math.max(1, Number(nums[0]) || 1);
        if (/[<=>?]/.test(t[1] || "")) continue;            // private sequences: dropped whole
        if (t[2] === "G" || t[2] === "`") col = Math.min(400, n - 1);
        else if (t[2] === "C") col = Math.min(400, col + n);
        else if (t[2] === "D") col = Math.max(0, col - n);
        else if (t[2] === "H" || t[2] === "f") { if (lines[lines.length - 1].trim()) newline(); col = Math.min(400, Math.max(1, Number(nums[1]) || 1) - 1); }
        else if (t[2] === "E" || t[2] === "B") newline();
        else if (t[2] === "K" && !(Number(nums[0]) > 0)) lines[lines.length - 1] = lines[lines.length - 1].slice(0, col);
        continue;
      }
      if (tok.length > 1 && tok !== "\r\n") continue;        // other escapes and strings
      if (tok === "\n" || tok === "\r\n") newline();
      else if (tok === "\r") col = 0;
      else if (tok === "\b") col = Math.max(0, col - 1);
      else if (tok === "\t") col = (Math.floor(col / 8) + 1) * 8;
      else if (tok < " " || tok === "\x7f") continue;
      else put(tok);
    }
    return lines.join("\n").replace(/[ \t]+$/gm, "").replace(/\n{3,}/g, "\n\n");
  }
  return { write };
}

// ---------------------------------------------------------------- the letter
// The only words in the conversation are the agent's words to the person. shapeTurn decides,
// from one agent turn's parts in the order they came ({text, chunks: [{text, at}]} or {tool}),
// what is set on the page now:
//   - a text part followed by a tool call before it was ever shown is the agent speaking to
//     itself on the way to a tool ("Running the record command now."): it is `interim`, said in
//     the presence line and folded after (a turn that ends on a tool keeps its last such words as
//     its words to the person). Words once set before the person are never taken back, whatever
//     comes after them (so "Yes, we go at your pace" never vanishes when a tool
//     follows her No);
//   - while the turn runs, the last part is set by the sentence: a sentence is set once it is
//     whole and has stood `hold` ms with no tool call after it; a pause of `pause` ms sets what
//     has come; `recheck` says when to look again;
//   - a sentence once set stays set while it is the answer (`shown`, a Set the caller keeps).
const ENDS = /[.!?:;…)"”’](?=\s|$)|\n/g;
export function shapeTurn(parts, { done = false, now = 0, hold = 600, pause = 1500, shown = new Set(), key = "" } = {}) {
  const said = [], interim = [];
  let recheck = null;
  const idx = parts.map((p, i) => (p.text != null ? i : -1)).filter((i) => i >= 0);
  for (const i of idx) {
    const part = parts[i];
    const k = key + ":" + i;
    const toolAfter = parts.slice(i + 1).some((p) => p.tool);
    const later = parts.slice(i + 1).length > 0;
    if (!String(part.text || "").trim()) continue;
    if (toolAfter && !shown.has(k)) { interim.push(part.text.trim()); continue; }
    let visible = part.text;
    if (!done && !later && !toolAfter && !shown.has(k + ":whole")) {
      const chunks = part.chunks && part.chunks.length ? part.chunks : [{ text: part.text, at: 0 }];
      const lastAt = chunks[chunks.length - 1].at || 0;
      if (now - lastAt >= pause) visible = part.text;
      else {
        // when each character arrived
        let text = "";
        const arrived = [];
        for (const c of chunks) { const s = c.text || ""; text += s; for (let j = 0; j < s.length; j++) arrived.push(c.at || 0); }
        let cut = 0, m;
        ENDS.lastIndex = 0;
        while ((m = ENDS.exec(text))) {
          const end = m.index + m[0].length;
          const age = now - arrived[end - 1];
          if (age >= hold) cut = end;
          else recheck = Math.min(recheck == null ? Infinity : recheck, hold - age + 5);
        }
        visible = text.slice(0, cut);
        recheck = Math.min(recheck == null ? Infinity : recheck, pause - (now - lastAt) + 5);
      }
    }
    if (visible.trim()) {
      shown.add(k);
      if (visible.length >= part.text.length) shown.add(k + ":whole");
      said.push(visible.trim());
    }
  }
  // a turn that ended on a tool: its last words on the way are its words to the person
  if (done && !said.length && interim.length) said.push(interim.pop());
  return { said, interim, recheck: recheck === Infinity ? null : recheck };
}

/** The work of one turn, by kind, in the order of first appearance: [[group, n]]. */
export function workOf(tools) {
  const group = (k) => (k === "read" || k === "search" ? k : k === "edit" || k === "delete" || k === "move" ? "edit"
    : k === "execute" ? "execute" : k === "fetch" ? "fetch" : k === "think" || k === "switch_mode" ? null : "other");
  const out = new Map();
  for (const x of tools || []) { const g = group(x.kind); if (g) out.set(g, (out.get(g) || 0) + 1); }
  return [...out.entries()];
}

/** The agent's words set as a letter: paragraphs, hanging lists, small-capital headings, italic
 *  and medium weight. Built from text nodes only; nothing the agent sent is ever markup. */
export function letter(h, text) {
  const out = [];
  const inline = (s) => {
    const nodes = [];
    const re = /\*\*([^*\n]+)\*\*|__([^_\n]+)__|\*([^*\n]+)\*|(?<![\w])_([^_\n]+)_(?![\w])|`([^`\n]+)`/g;
    let last = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > last) nodes.push(s.slice(last, m.index));
      if (m[1] || m[2]) nodes.push(h("strong", null, m[1] || m[2]));
      else if (m[3] || m[4]) nodes.push(h("em", null, m[3] || m[4]));
      else nodes.push(m[5]);
      last = m.index + m[0].length;
    }
    if (last < s.length) nodes.push(s.slice(last));
    return nodes;
  };
  const blocks = String(text || "").replace(/^```[^\n]*$/gm, "").split(/\n{2,}/);
  const LIST = /^\s*([-*•]|\d+[.)])\s+/;
  for (const b of blocks) {
    const lines = b.split("\n").filter((l) => l.trim());
    // runs of plain lines, list lines and headings, each set in its own form
    let run = [], kind = null;
    const flush = () => {
      if (!run.length) return;
      if (kind === "list") {
        const ordered = /^\s*\d/.test(run[0]);
        out.push(h(ordered ? "ol" : "ul", { class: "dock-list" }, run.map((l) => h("li", null, ...inline(l.replace(LIST, ""))))));
      } else out.push(h("p", { class: "dock-words" }, ...inline(run.join("\n"))));
      run = []; kind = null;
    };
    for (const l of lines) {
      if (/^#{1,6}\s+/.test(l)) { flush(); out.push(h("p", { class: "dock-h" }, ...inline(l.replace(/^#{1,6}\s+/, "")))); continue; }
      const k = LIST.test(l) ? "list" : "words";
      if (kind && k !== kind) flush();
      kind = k; run.push(l);
    }
    flush();
  }
  return out;
}

// ---------------------------------------------------------------- the layered voice (DESIGN-DOCK "The layered voice")
// Voice, then words, then the card: nothing is voice-only. The person speaks (hold the microphone
// and let go, or tap it to keep listening); the words appear in the line as they are heard, and go
// only when the person sends them (or on release, when the person has asked for that). Her turn is
// read aloud only when the person has turned it on, on this device, and only once it is whole.
// While her voice plays the microphone is closed; when the person starts speaking her voice stops.

/** True when this page must never speak: a page driven by a test or a headless browser
 *  (navigator.webdriver), or one opened with ?muted or window.__lionsbergMuted set by a fixture. */
export function voiceSilenced(w = globalThis) {
  try {
    return !w.navigator || w.navigator.webdriver === true || w.__lionsbergMuted === true
      || new URLSearchParams((w.location && w.location.search) || "").has("muted");
  } catch { return true; }
}

const NOVELTY = /^(albert|bad news|bahh|bells|boing|bubbles|cellos|good news|jester|organ|superstar|trinoids|whisper|wobble|zarvox|fred|junior|ralph|kathy|grandma|grandpa|eddy|flo|reed|rocko|sandy|shelley)\b/i;
const CALM = ["ava", "samantha", "allison", "susan", "serena", "moira", "karen", "tessa", "kate", "fiona", "zoe", "evan", "nathan", "daniel", "alex"];
/** The calmest voice on this device: the person's own choice when it is here; else a voice on the
 *  device itself (never one that reads over the network), in the page's language, a fuller voice
 *  before a compact one, never a novelty voice. */
export function calmestVoice(voices, lang = "en", chosen = null) {
  const list = (voices || []).filter((v) => v && v.name && !NOVELTY.test(v.name));
  if (chosen) { const c = list.find((v) => v.voiceURI === chosen || v.name === chosen); if (c) return c; }
  const L = String(lang || "en").toLowerCase(), base = L.split("-")[0];
  let best = null, top = -Infinity;
  for (const v of list) {
    const vl = String(v.lang || "").toLowerCase().replace("_", "-");
    if (vl && !vl.startsWith(base)) continue;
    const first = v.name.toLowerCase().split(/[\s(]/)[0];
    const calm = CALM.indexOf(first);
    const score = (v.localService ? 100 : 0) + (vl === L ? 30 : 20) + (/premium/i.test(v.name) ? 15 : /enhanced/i.test(v.name) ? 10 : 0)
      + (calm >= 0 ? 20 - calm : 0) + (v.default ? 2 : 0);
    if (score > top) { top = score; best = v; }
  }
  return best;
}

/** Her words as they are read aloud: what is drawn for the eye is left out (code, marks, addresses). */
export function speakable(text) {
  return String(text || "")
    .replace(/```[\s\S]*?(```|$)/g, " ")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/^\s*#{1,6}\s+/gm, "")
    .replace(/^\s*([-*•]|\d+[.)])\s+/gm, "")
    .replace(/\*\*([^*\n]+)\*\*|__([^_\n]+)__/g, "$1$2")
    .replace(/(^|[^\w*])\*([^*\n]+)\*(?=[^\w*]|$)/g, "$1$2")
    .replace(/(^|[^\w])_([^_\n]+)_(?=[^\w]|$)/g, "$1$2")
    .replace(/[ \t]+/g, " ")
    .replace(/\s*\n+\s*/g, "\n")
    .trim();
}

/** The line to speak while words are heard: what was there, then the words heard, one space between. */
export function joinWords(base, heard) {
  const a = String(base || "").replace(/\s+$/, ""), b = String(heard || "").trim();
  return a && b ? a + " " + b : a || b;
}

const FIELD = ["art/l-person-flow-a.jpg", "art/l-person-flow-b.jpg", "art/l-person-flow-c.jpg"];

// create({agentId, inline, onView, pageContext, localTurns, placeholder, aboutExtra}): the shell's dock takes no options.
// The Talk (talk-place.js) passes four more: `pageContext()` is what the page itself shows and said
// ({line, question, options, local_answers}), sent with every line so your agent knows it;
// `localTurns()` is the Talk's own turns ([{at, node}], at in ms), set into the stream in time order;
// `placeholder()` is the line to speak's words; `aboutExtra()` adds nodes to the sheet behind her
// name (the keepsakes). The Bodies room mounts a
// ------------------------------------------------------------------ the trust layer (pure)
// DESIGN-TALK.md, the trust layer: what her agent is doing, always seen,
// at the depth the person chose (plain · working · full). Each figure is the harness's own, or it is
// left out: a null is never shown as a dash or a zero.

export const DEPTHS = ["plain", "working", "full"];
const num = (x) => (typeof x === "number" && Number.isFinite(x) ? x : null);

/** One act's kind, as the rows group it: a worker launched is its own kind (the input names a worker type). */
export function actClass(x) {
  const k = String((x && x.kind) || "");
  if (/"subagent_type"\s*:/.test(String((x && x.input) || ""))) return "worker";
  if (["read", "search", "execute", "edit", "delete", "move", "fetch", "think"].includes(k)) return k;
  return k === "switch_mode" ? "think" : "other";
}

const done = (x) => /^(completed|failed)$/.test(String((x && x.status) || ""));

/** Consecutive acts of one kind, as one row (the terminal's grouped line): [{cls, tools, n, ms, running, failed, leaves}] */
export function actGroups(tools, turnDone = false) {
  const out = [];
  for (const x of tools || []) {
    const cls = actClass(x);
    let g = out[out.length - 1];
    if (!g || g.cls !== cls || cls === "worker") { g = { cls, tools: [], n: 0, sum: null, unknown: false, running: false, failed: false, leaves: cls === "fetch" }; out.push(g); }
    g.tools.push(x); g.n++;
    // each act's own time, one number at every depth: the time this page measured when it saw the act live (kept
    // for the sitting, so a reload or a turn of the knob says the same), else the host's stamps, whole seconds
    // only (they are stamped to the second, so under one they say nothing rather than a false 0.0 s)
    const ms = actMs(x);
    if (ms != null) g.sum = (g.sum || 0) + Math.max(0, ms); else if (done(x)) g.unknown = true;
    if (!done(x) && !turnDone) g.running = true;
    if (x.status === "failed") g.failed = true;
  }
  for (const g of out) g.ms = !g.running && !g.unknown && g.sum != null ? g.sum : null;
  return out;
}

const ACT_KEY = "hud.act_ms";
function actStore() { try { return JSON.parse(sessionStorage.getItem(ACT_KEY) || "{}") || {}; } catch { return {}; } }
/** Keep one act's measured time for the sitting (by its conversation and its id). */
export function keepActMs(conv, id, ms) {
  if (!conv || !id || num(ms) == null) return;
  try { const m = actStore(); m[conv + "|" + id] = Math.max(0, Math.round(ms)); const k = Object.keys(m); if (k.length > 400) delete m[k[0]]; sessionStorage.setItem(ACT_KEY, JSON.stringify(m)); } catch { /* storage closed */ }
}
/** One act's time: the host's own figure (its duration, or its stamps when they carry the part of a second),
    else the measure this page kept, else this page's live stamps, else the host's whole seconds; null when unknown.
    Live and replayed then say the same number whenever the host gives one. */
export function actMs(x) {
  if (!x) return null;
  const own = [x.duration_ms, x.elapsed_ms, x.ms].map(num).find((v) => v != null);
  if (own != null) return Math.max(0, own);
  if (x._t0 != null && x._t1 != null && x._sub) return Math.max(0, x._t1 - x._t0);
  if (num(x._ms) != null) return x._ms;
  if (x._p0 != null && x._p1 != null) return Math.max(0, x._p1 - x._p0);
  if (x._t0 != null && x._t1 != null && x._t1 - x._t0 >= 1000) return x._t1 - x._t0;
  return null;
}
/** a stamp that carries the part of a second ("12:00:01.009"), so a difference under one second is true */
const subSecond = (ts) => /T\d\d:\d\d:\d\d[.,]\d/.test(String(ts || ""));
/** seconds under ten, in the kit's words: one place, and "<0.1" for less than a tenth (never a false 0.0) */
export function tenths(ms) { return ms < 100 ? "<0.1" : (ms / 1000).toFixed(1); }

/** A length of time in the terminal's short words: "0.4 s", "12 s", "2 m 36 s", "1 h 4 m". */
export function durWords(ms, t) {
  const x = num(ms);
  if (x == null) return "";
  if (x < 1000) return t("dock.trust.dur.s", { s: tenths(x) });
  const s = Math.round(x / 1000);
  if (s < 60) return t("dock.trust.dur.s", { s });
  if (s < 3600) return t("dock.trust.dur.ms", { m: Math.floor(s / 60), s: s % 60 });
  return t("dock.trust.dur.hm", { h: Math.floor(s / 3600), m: Math.floor((s % 3600) / 60) });
}

/** A row's words: "Read three pages", "Ran a step", "Started a worker". */
export function actWords(g, t, fmt) {
  return g.n === 1 ? t(`dock.trust.act.${g.cls}_one`) : t(`dock.trust.act.${g.cls}`, { n: fmt.number(g.n, true) });
}

/** A turn's acts as one quiet line (Plain): "I read two pages and ran one step." "" when none. */
export function plainActs(tools, t, fmt) {
  const counts = new Map();
  for (const x of tools || []) { const c = actClass(x); counts.set(c, (counts.get(c) || 0) + 1); }
  const parts = [...counts.entries()].map(([c, n]) => (n === 1 ? t(`dock.trust.plain.${c}_one`) : t(`dock.trust.plain.${c}`, { n: fmt.number(n, true) })));
  if (!parts.length) return "";
  const and = t("dock.trust.plain.and");
  const acts = parts.length === 1 ? parts[0] : parts.slice(0, -1).join(", ") + and + parts[parts.length - 1];
  return t("dock.trust.plain.lead", { acts });
}

/** The model's name as a person says it: "claude-fable-5-1" → "Fable 5.1"; "Default (recommended)" → "Default". */
export function modelWords(m) {
  const s = String(m || "").trim();
  if (!s) return "";
  if (!/^[a-z0-9.-]+$/.test(s)) return s.replace(/\s*\(.*\)\s*$/, "");
  const parts = s.replace(/^claude-/, "").replace(/\[.*\]$/, "").split("-").filter(Boolean);
  let i = parts.length;
  while (i > 0 && /^\d+$/.test(parts[i - 1])) i--;
  const words = parts.slice(0, i).join(" ");
  const ver = parts.slice(i).join(".");
  return [words.charAt(0).toUpperCase() + words.slice(1), ver].filter(Boolean).join(" ");
}

/** A reset time, short: "Tue 5 AM", or "5 AM" today; "" when none or unreadable. */
export function resetWords(iso, now = new Date()) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const time = d.toLocaleTimeString("en-US", d.getMinutes() ? { hour: "numeric", minute: "2-digit" } : { hour: "numeric" });
  const today = d.toDateString() === now.toDateString();
  return today ? time : d.toLocaleDateString("en-US", { weekday: "short" }) + " " + time;
}

/** A share in words, nearest of a few (Plain): 34 → "a third". */
export function fractionKey(pct) {
  const steps = [10, 25, 33, 50, 67, 75, 90];
  let best = steps[0];
  for (const s of steps) if (Math.abs(s - pct) < Math.abs(best - pct)) best = s;
  return "dock.trust.plain.frac_" + best;
}

/** A count of the harness's units, short: 2400 → "2.4k", 1250000 → "1.3M". */
export function countWords(n) {
  const x = num(n);
  if (x == null) return "";
  if (x >= 1e6) return (x / 1e6).toFixed(x >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
  if (x >= 1e3) return (x / 1e3).toFixed(x >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "k";
  return String(Math.round(x));
}

/** Dollars at list price: "3.20"; under a cent, "0.004". */
export function usdWords(x) {
  const v = num(x);
  if (v == null) return "";
  return v > 0 && v < 0.01 ? v.toFixed(3) : v.toFixed(2);
}

/**
 * The status line's parts, at a depth, from the figures block (each null left out):
 *   working  "Fable 5.1 · effort high · context 42% · this sitting $3.20 · your week 65%, resets Tue 5 AM · Manual"
 *   plain    "About a third of what I can hold is in use; the week is two thirds used" (no figure, no mode, no table)
 *   full     the working line, then tokens in and out this sitting, the cache, the adapter's version
 * Returns [{text, mode?: true}] (the mode's part opens the harness's own modes) and the separator.
 */
export function statusParts(f, depth, { t, name = "", modeWord = "", now = new Date() } = {}) {
  f = f || {};
  const parts = [];
  const effort = f.effort && f.effort !== "default" ? t("dock.status.effort." + f.effort) : "";
  const effortOk = effort && !/^\[/.test(effort);
  const ctxPct = num(f.context_used_pct), week = num(f.week_pct);
  if (depth === "plain") {
    // never the effort (a setting, not a state) and never a figure; her name only when nothing else is known
    if (ctxPct != null) parts.push({ text: ctxPct < 6 ? t("dock.trust.plain.context_low") : ctxPct >= 85 ? t("dock.trust.plain.context_edge") : t("dock.trust.plain.context", { frac: t(fractionKey(ctxPct)) }) });
    if (week != null) parts.push({ text: week < 6 ? t("dock.trust.plain.week_low") : week >= 98 ? t("dock.trust.plain.week_spent") : t("dock.trust.plain.week", { frac: t(fractionKey(week)) }) });
    if (!parts.length && name) parts.push({ text: t("dock.trust.plain.lead_here", { name }) });
    if (parts.length) parts[0] = { text: parts[0].text.charAt(0).toUpperCase() + parts[0].text.slice(1) };
    return { parts, sep: "; " };
  }
  const model = modelWords(f.model);
  if (model) parts.push({ text: model });
  if (effortOk) parts.push({ text: effort });
  if (ctxPct != null) parts.push({ text: t("dock.status.context", { pct: Math.round(ctxPct) }) });
  if (num(f.cost_session) != null) parts.push({ text: t("dock.status.cost_sitting", { usd: usdWords(f.cost_session) }) });
  if (week != null) {
    const when = resetWords(f.week_resets, now);
    parts.push({ text: when ? t("dock.status.week", { pct: Math.round(week), when }) : t("dock.trust.week_only", { pct: Math.round(week) }) });
  }
  if (depth === "full") {
    // the window beside the figure ("36k of 1M held"), so a percent is read against the window it was measured in
    const held = num(f.context_tokens);
    if (held != null && ctxPct > 0) parts.push({ text: t("dock.trust.full.window", { held: countWords(held), size: countWords(Math.round((held * 100) / ctxPct / 1000) * 1000) }) });
    if (num(f.tokens_in) != null || num(f.tokens_out) != null) parts.push({ text: t("dock.trust.full.io", { in: countWords(f.tokens_in) || "0", out: countWords(f.tokens_out) || "0" }) });
    const c = f.cache && num(f.cache.read_pct);
    if (c != null) parts.push({ text: t("dock.trust.full.cache", { pct: Math.round(c) }) });
    if (f.version) parts.push({ text: t("dock.trust.full.version", { v: String(f.version).split(/\s+/).pop().replace(/^v/, "").split(".").slice(0, 2).join(".") }) });
    if (f.stand_in) parts.push({ text: t("dock.status.stand_in") });
  }
  if (modeWord) parts.push({ text: modeWord, mode: true });
  return { parts, sep: " · " };
}

// second, inline copy in place (bodies.js, DESIGN-BODIES §13): `agentId` is the agent it speaks
// with, `inline` keeps it open with no bar, no close and no window listener, and `onView(view)`
// tells the room when the view changes, so its Words · Plain · Command line switch follows;
// `setView(view)` is how the room changes it.
// Every dock mounted on this page (the shell's, and the Talk's inline one): Settings (shell.js, behind
// More) asks the one in view for her choices, so the sheet behind her name stays short.
const LIVE = new Set();
/** Her choices for Settings, from the dock in view (the Talk's inline one first): {agent: [nodes],
    judgment: [nodes]}; empty when no dock is mounted. `close` closes the Settings sheet. */
export function agentSettings(close) {
  const all = [...LIVE].filter((d) => d.connected());
  const d = all.find((x) => x.inline) || all[0] || [...LIVE][0];
  return d ? d.settings(close) : { agent: [], judgment: [], name: null };
}
// Her one name, remembered on this device once the host or the agents file has said it, so no frame
// before the first word shows a second face ("YOUR AGENT"); the host's name always wins when it speaks.
const NAME_KEY = "hud.agent_name";
export function rememberedName() { try { const v = localStorage.getItem(NAME_KEY); return v ? JSON.parse(v) : null; } catch { return null; } }
function rememberName(n) { try { if (n && rememberedName() !== n) localStorage.setItem(NAME_KEY, JSON.stringify(n)); } catch { /* this visit only */ } }

export default function create(opts = {}) {
  const INLINE = !!opts.inline;
  let el = null, ctx = null;
  const S = {
    agentId: null, conv: null, epoch: null, events: [], stream: null, streamConv: null,
    clock: null, outbox: [], refusal: null, view: "ice", about: null, aboutCleared: null, sentLocal: new Set(),
    thinkingSince: null, tick: null, recall: "", pty: null, ptyStream: null, ptyText: "", term: null,
    local: new Map(), // offer id -> agreeing | declined (this page's own taps)
    rated: new Map(), // turn -> verdict said
    drafts: new Map(), // a worker's handoff -> its text, once read here
    editing: null,
    shown: new Set(), // text parts once set in the letter (never taken back)
    holdTimer: null,
    // the layered voice: way undefined until found (device · record · vendor · file · null)
    voice: { way: undefined, info: null, listening: false, mode: null, intent: null, base: "", final: "", interim: "",
      rec: null, media: null, chunks: [], hearing: false, note: "", downAt: 0, stopOnUp: false, sendOnEnd: false,
      speaking: null, audio: null, mine: new Set(), spoken: new Map(), askSpoken: new Set(),
      // voice mode: a hands-free loop (listening · hearing · thinking · speaking, then listening again)
      loop: { on: false, phase: null }, pauseTimer: null, silence: null, wake: null },
  };
  const V = S.voice;
  // the trust layer (DESIGN-TALK.md): the depth the page holding the conversation chose, or
  // null where no page asks for it (the dock beside the Deal, the Bodies room keep their own rows)
  const depth = () => { if (!opts.depth) return null; try { const d = opts.depth(); return DEPTHS.includes(d) ? d : null; } catch { return null; } };
  S.live = null;           // the live line's node and its turn: its clock is counted each second without a redraw
  S.folds = new Map();     // a fold the person opened or closed, kept across redraws (key -> open)
  S.statusKey = "";
  let ui_asking = false;   // the "May I listen?" sheet is open
  const $ = {};
  const h = (...a) => ctx.card.h(...a);
  const t = (k, v) => ctx.t(k, v);

  // ---------------------------------------------------------------- the facts
  const st = () => ctx.state || {};
  const agents = () => ((st().hud && st().hud.agents) || []);
  // the person's own agent first; a worker it started (a row with a `body`) is never the one spoken with
  const mine = () => agents().filter((a) => a.of === st().actor && a.kind !== "guest").sort((a, b) => (a.body ? 1 : 0) - (b.body ? 1 : 0));
  // the state is read live from the conversation's own stream when it has spoken since the
  // last read of the state, so "thinking" and "waiting on you" never lag the agent
  const me = () => {
    const a = (opts.agentId && agents().find((x) => x.id === opts.agentId)) || mine().find((x) => x.id === S.agentId) || mine()[0] || null;
    if (!a) return null;
    const live = [...S.events].reverse().find((e) => e.kind === "state");
    const open = [...model().asks.values()].filter((x) => x.open).length;
    // her one name: the host's, carried by every `state` event and by /say, else the agents file's
    const named = [...S.events].reverse().find((e) => (e.kind === "state" || e.kind === "hello") && typeof e.name === "string" && e.name.trim());
    const name = (named && named.name.trim()) || S.sayName || (typeof a.name === "string" && a.name.trim()) || null;
    if (name && !a.body) rememberName(name);
    return { ...a, name: name || (a.body ? null : rememberedName()), state: live ? live.state : a.state, asks_open: S.events.length ? open : a.asks_open };
  };
  const dockFacts = () => (st().hud && st().hud.dock) || {};
  const nameOf = (a) => (a && a.name) || t("app.agent_default");
  // where her words go: the one true sentence, the host's own (dock.first.words), naming the service
  // when the person's vendors file names it (hud.dock.vendor); said the same way everywhere
  const wordsLine = () => { const v = S.vendor || dockFacts().vendor; return typeof v === "string" && v.trim() ? t("dock.first.words_named", { vendor: v.trim() }) : t("dock.first.words"); };
  const isOpen = () => INLINE || !!(ctx.dock && ctx.dock.open);
  // a turn runs: her words are out, or the agent is thinking or waking
  const busy = () => { const x = me(); return !!(S.thinkingSince || S.outbox.some((o) => !o.waiting) || (x && (x.state === "thinking" || x.state === "waking"))); };
  // Stop, tapped, typed or spoken: the turn ends, the voice loop ends, she stops speaking
  function stopAll() {
    if (S.conv && busy()) A.stop(S.conv);
    // nothing of hers runs but her workers: Stop stops them (each row has its own Stop too)
    else if (depth()) for (const w of hostWorkersRunning()) {
      const c = w.conversation || ((agents().find((x) => x.id === w.agent) || {}).conversation);
      if (c) { const t0 = Date.parse(w.started || "") || null; markStopped(w, t0 ? Date.now() - t0 : null); A.stop(c); }
    }
    S.thinkingSince = null;
    if (V.loop.on) endLoop();
    stopSpeaking(true);
    render();
  }

  function chooseConversation() {
    const a = me();
    if (!a) return;
    S.agentId = a.id;
    if (!S.conv) {
      const latest = (dockFacts().conversations || []).find((c) => c.agent === a.id);
      S.conv = a.conversation || (latest && latest.id) || null;
    }
    if (S.conv && S.streamConv !== S.conv) openStream(S.conv);
  }

  function openStream(conv) {
    if (S.stream) S.stream.close();
    S.streamConv = conv;
    S.events = [];
    S.stream = A.stream(conv, 0, onEvent, (hello) => {
      const reset = !!(S.epoch && hello.epoch !== S.epoch);
      S.epoch = hello.epoch;
      if (reset) S.events = [];
      return reset;
    });
  }

  function onEvent(ev) {
    if (!ev || typeof ev.n !== "number") return;
    if (S.events.length && ev.n < S.events.length) return;   // already held
    ev._at = performance.now();
    // seen as it happened (not replayed on a load): only then is this page's own clock the act's time
    ev._live = !ev.ts || Math.abs(Date.now() - Date.parse(ev.ts)) < 4000;
    ev.seen = Date.now();   // page time: the host's stamps may run on a shifted clock
    S.events.push(ev);
    if (ev.kind === "user" && S.outbox.some((o) => o.text === ev.text)) V.mine.add(ev.turn);   // a turn spoken from this page
    if (ev.kind === "user") S.outbox = S.outbox.filter((o) => o.text !== ev.text);
    // her agent marked the suggested choice on its own word: the page settles it as her tap would, with
    // Undo ("Decided for you"); only a mark said in this sitting (a replay on another device marks nothing again)
    if (ev.kind === "decided" && typeof ctx.settleCard === "function" && (!ev.ts || Date.now() - Date.parse(ev.ts) < 5 * 60 * 1000)) {
      try { ctx.settleCard({ card: ev.card_id, option: ev.option, index: ev.option_index, decided: true }); } catch { /* the page's own */ }
    }
    if (ev.kind === "agent" && S.clock && S.clock.turn === ev.turn && !S.clock.ms) {
      S.clock.ms = Math.round(performance.now() - S.clock.t0);
      const asksBefore = S.events.some((e) => e.kind === "ask" && e.turn === ev.turn && e.n < ev.n) ? 1 : 0;
      (window.__dockClock = window.__dockClock || []).push({ ms: S.clock.ms, asks_before: asksBefore, turn: ev.turn });
    }
    // only the end of the turn just sent clears "thinking" (a late end of the turn before must not,
    // or Stop leaves and a typed "stop" is sent while her turn runs)
    if (ev.kind === "ask" || (ev.kind === "turn_end" && !(S.clock && (S.clock.turn == null || ev.turn < S.clock.turn)))) S.thinkingSince = null;
    render();
    if (ev.kind === "turn_end" || (ev.kind === "ask" && ev.ask)) {
      // her turn read aloud once it is whole; a question she asks, aloud, its chips kept
      const began = voiceTurn(ev.turn, ev.kind === "ask" ? ev.ask : null);
      if (!began && V.loop.on && V.mine.has(ev.turn) && !V.speaking) loopListen();   // voice mode: listening again
    }
  }

  // ---------------------------------------------------------------- the model of the conversation
  function model() {
    const items = [], asks = new Map(), offers = new Map(), workers = new Map();
    let block = null, fig = null;
    const agentBlock = (turn) => {
      if (block && block.turn === turn && items[items.length - 1] === block) return block;
      block = { who: "agent", turn, text: "", tools: [], parts: [], plan: null, thought: 0, done: false, offers: [], raw: [], ts: curTs };
      items.push(block);
      return block;
    };
    let curTs = null;
    for (const e of S.events) {
      curTs = e.ts || curTs;
      switch (e.kind) {
        case "user": block = null; items.push({ who: "you", turn: e.turn, text: e.text, about: e.about, ts: e.ts }); break;
        case "agent": {
          if (!e.worker && block && block.turn === e.turn && block.thoughtText && !block.thoughtEnd) block.thoughtEnd = e.ts || null;
          // a worker's words are the worker's: their own turn under its name, never inside hers
          if (e.worker) {
            const last = items[items.length - 1];
            if (last && last.who === "worker" && last.name === e.worker && last.turn === e.turn) last.text += e.text || "";
            else { block = null; items.push({ who: "worker", name: String(e.worker), turn: e.turn, text: e.text || "", ts: e.ts }); }
            break;
          }
          const b = agentBlock(e.turn);
          if (b.gap && b.text) b.text += "\n\n";
          const last = b.parts[b.parts.length - 1];
          const chunk = { text: e.text || "", at: e._at || 0 };
          if (last && last.text != null && !b.gap) { last.text += e.text || ""; last.chunks.push(chunk); }
          else b.parts.push({ text: e.text || "", chunks: [chunk] });
          b.gap = false; b.text += e.text || "";
          break;
        }
        case "thought": { const b = agentBlock(e.turn); b.thought += (e.text || "").length; b.thoughtText = (b.thoughtText || "") + (e.text || ""); break; }
        case "tool": { const b = agentBlock(e.turn); const kept = actStore()[S.conv + "|" + (e.tool || {}).id]; const t0 = (e.tool || {}).started || e.ts; const x = { ...e.tool, _t0: Date.parse(t0 || "") || null, _sub: subSecond(t0), _p0: e._live ? e._at : null, _ms: num(kept) }; b.tools.push(x); b.parts.push({ tool: x }); break; }
        case "tool_update": {
          const b = agentBlock(e.turn);
          const x = b.tools.find((y) => y.id === (e.tool || {}).id);
          if (x) Object.assign(x, Object.fromEntries(Object.entries(e.tool || {}).filter(([, v]) => v != null)));
          if (x && !x._t1 && /^(completed|failed)$/.test(String(x.status || ""))) { const t1 = (e.tool || {}).ended || e.ts; x._t1 = Date.parse(t1 || "") || null; x._sub = !!(x._sub && subSecond(t1)); x._p1 = e._live && x._p0 != null ? e._at : null; if (x._p1 != null && x._ms == null) { x._ms = x._p1 - x._p0; keepActMs(S.conv, x.id, x._ms); } }
          break;
        }
        case "plan": agentBlock(e.turn).plan = e.entries || []; break;
        case "ask":
          asks.set(e.ask.id, { ...e.ask, open: true });
          if (block) block.gap = true;
          // an ask is a turn in the stream, in its place (the Talk): never pinned at the foot
          if (opts.asksInStream) { block = null; items.push({ who: "ask", id: e.ask.id, ts: e.ts }); }
          break;
        case "answered": { const a = asks.get(e.ask); if (a) { a.open = false; a.answer = e.answer; } break; }
        case "offer": { const o = { ...e.offer }; offers.set(o.id, o); agentBlock(o.turn || e.turn || 0).offers.push(o); break; }
        case "offer_state": { const o = offers.get(e.offer); if (o) o.final = e.state; break; }
        case "turn_end":
          for (const it of items) if (it.who === "agent" && it.turn === e.turn) it.done = true;
          block = null;
          // the end line of every turn (the trust layer): drawn by depth; never twice for one turn
          if (!items.some((x) => x.who === "end" && x.turn === e.turn)) items.push({ who: "end", turn: e.turn, data: e, ts: e.ts });
          break;
        // said plainly when it happens (§2.7): her own line, the host's words (dock.status.notice.*)
        case "notice": block = null; items.push({ who: "notice", notice: e.notice, words: e.words || "", key: e.key || "", ts: e.ts }); break;
        case "figures": case "state": if (e.figures && typeof e.figures === "object") fig = { f: e.figures, ts: e.ts || null }; break;
        // the rows of her workers (§2.4); a worker that turns done leaves its row for one line in the stream
        case "workers": {
          for (const w of Array.isArray(e.workers) ? e.workers : []) {
            if (!w || !w.agent) continue;
            const was = workers.get(w.agent);
            if (workerEnded(w) && was && !workerEnded(was)) items.push({ who: "finished", agent: w.agent, name: w.name || w.agent, ms: w.elapsed_ms, ts: e.ts, stopped: workerStopped(w) });
            workers.set(w.agent, { ...w, seen: e._at || 0 });
          }
          break;
        }
        case "note": block = null; items.push({ who: "note", key: e.key }); break;
        // a worker came back: one line of hers, with its draft to read here (the host's `done`:
        // {agent, name, line, draft, go}); never inside another card, never a second page
        case "done": block = null; items.push({ who: "done", id: e.n, name: e.worker || e.body || e.name || null, line: e.line || "", draft: e.draft || "",
          handoff: (e.go && typeof e.go === "object" && e.go.handoff) || null, go: typeof e.go === "string" ? e.go : null, ts: e.ts }); break;
        // a mark her agent made on its own word ("Decided: …"), for the suggested choice: the page settles
        // it as her tap would, with Undo, and says "Decided for you" (drawn by the page, in its place)
        case "decided": break;
        // the host's own answer, said at once (first contact) with the page's answers it carried: the
        // page's own lines are already in the stream, so only what the host added is drawn
        case "local": {
          // the page's own lines (kind "page") are the page's to draw, as its own turns, in their
          // place: drawn here only what the host added for a first-contact kind, and once
          const kinds = Array.isArray(e.kinds) ? e.kinds : [];
          if (kinds.length && kinds.every((k) => k === "page")) { block = null; break; }
          let text = String(e.text || "");
          const said = new Set(S.sentLocal);
          try { for (const x of (opts.pageSaid ? opts.pageSaid() || [] : [])) said.add(String(x)); } catch { /* the page's own */ }
          if (Array.isArray(e.lines) && kinds.includes("page")) {
            // the host returns the page's lines first, then its own: keep only its own (by the count of
            // the page's lines when the host says it, so a device that never saw them never glues them in)
            text = (Number.isInteger(e.page_lines) ? e.lines.slice(e.page_lines) : e.lines.filter((x) => !said.has(String(x)))).join(" ");
          } else if (kinds.includes("page") && typeof e.own === "string") text = e.own;
          for (const x of said) if (x) text = text.split(x).join(" ");
          text = text.replace(/\s+/g, " ").trim();
          block = null;
          if (text && !items.some((x) => x.who === "local" && x.turn === e.turn)) items.push({ who: "local", turn: e.turn, text, ts: e.ts });
          break;
        }
        default: break;
      }
    }
    return { items, asks, offers, fig, workers };
  }

  function offerItem(o) {
    const local = S.local.get(o.id);
    const final = o.final || (local === "declined" ? "declined" : null);
    const fromRecord = o.source === "record";
    return { id: o.id, kind: o.kind, text: o.text, card: o.card, holon: o.holon, by: o.by, source: o.source,
      ink: final === "agreed" ? "agreed" : o.ink === "kept" ? "kept" : "said",
      agreeable: fromRecord ? (o.kind === "commitment" && !!o.card) : undefined,
      state: final === "declined" ? "declined" : local === "agreeing" ? "agreeing" : null };
  }

  // ---------------------------------------------------------------- acts
  async function send(textArg) {
    const a = me();
    const text = (textArg != null ? textArg : $.input.value).trim();
    if (!text || !a) return;
    // "stop", typed or spoken while a turn runs or the voice loop listens: it ends them; nothing is sent
    if (isStopWord(text) && (busy() || V.loop.on)) { if (textArg == null) { $.input.value = ""; grow(); } stopAll(); return; }
    if (ON_PHONE && ctx.offline) {      // the computer sleeps: the words wait here and go once, when it answers
      S.outbox.push({ text, waiting: true });
      $.input.value = "";
      render();
      return;
    }
    S.recall = text;
    if (textArg == null) { $.input.value = ""; grow(); }   // the empty line shrinks back on send
    S.refusal = null;
    S.outbox.push({ text });
    S.thinkingSince = Date.now();
    const about = S.about && S.about.title;
    S.clock = { t0: performance.now(), turn: null, ms: null };
    // her line goes to the top of the view and the answer grows beneath it: a long answer never
    // pushes her question off; released when she scrolls, or the page moves on
    S.pin = true;
    render();
    let page;
    try { page = opts.pageContext ? opts.pageContext() || undefined : undefined; } catch { page = undefined; }
    if (page && Array.isArray(page.local_answers)) for (const x of page.local_answers) S.sentLocal.add(String(x));
    const r = await A.say(a.id, S.conv, text, about || undefined, page);
    if (!r.ok) {
      S.outbox = S.outbox.filter((o) => o.text !== text);
      S.thinkingSince = null;
      S.refusal = r.away ? t("dock.no_host") : (r.out && r.out.refused) || t("dock.not_heard");
      $.input.value = text;
      render();
      return;
    }
    // the host took her short line as the answer to the open ask (yes, no, keep it, not now, start it):
    // no new turn runs; a mark she said yes to is written here, as the Yes did, and said in her line
    const ans = r.out && r.out.answered;
    if (ans && typeof ans === "object") {
      S.thinkingSince = null;
      if (ans.kind === "act" && ans.answer === "yes" && typeof ctx.settleCard === "function") {
        try { ctx.settleCard({ card: ans.card_id, option: ans.option, index: ans.option_index }); } catch { /* the page's own */ }
      }
      render();
    }
    S.clock.turn = r.out.turn;
    // a turn that ended before this reply came back (a greeting answered at once): its end already sits in
    // the stream and was not counted above, so count it now, or Stop stays
    if (r.out.turn != null && S.events.some((e) => e.kind === "turn_end" && e.turn === r.out.turn)) { S.thinkingSince = null; render(); }
    if (typeof r.out.name === "string" && r.out.name.trim()) S.sayName = r.out.name.trim();
    if (r.out.turn != null) V.mine.add(r.out.turn);
    if (r.out.conversation && r.out.conversation !== S.conv) { S.conv = r.out.conversation; openStream(S.conv); }
  }

  async function wake() {
    const a = me();
    if (!a) return;
    S.refusal = null;
    const r = await A.wake(a.id, S.conv);
    if (r.ok && r.out.conversation) { if (r.out.conversation !== S.conv) { S.conv = r.out.conversation; openStream(S.conv); } }
    else S.refusal = (r.out && r.out.refused) || t("dock.no_host");
    render();
  }

  function agree(it) {
    const s = st();
    const holon = it.holon || (it.card && ctx.read.card(s, it.card) && ctx.read.card(s, it.card).holon) || ctx.home;
    let p;
    const label = t("dock.margin.agreed_label", { what: it.text });
    if (it.kind === "commitment" && it.card) p = ctx.act("commit", { card: it.card, by: it.by }, {}, holon, { confirmed: true, label });
    else if (it.kind === "said_in_room") p = ctx.act("say", { text: it.text }, {}, holon, { confirmed: true, label });
    else p = ctx.act("card", { title: it.text, holder: s.actor, by: it.by }, {}, holon, { confirmed: true, label });
    S.local.set(it.id, "agreeing");
    render();
    p.done.then((r) => {
      S.local.delete(it.id);
      if (r.status === "written" || r.status === "kept-here") A.offer(S.conv, it.id, "agreed", r.serverId || undefined);
      render();
    });
  }
  function decline(it) { S.local.set(it.id, "declined"); A.offer(S.conv, it.id, "declined"); render(); }

  async function answer(ask, ans) {
    // an act your agent proposed (the host's ask of kind `act`: {card_id, option_index, option}): its
    // card (dock-card.js) writes the Deal's own act on the person's Yes and then answers here; the
    // page that shows the card (the Talk) is told, so it marks the card answered and says so in her
    // settled line, with its keepsake. Told, never asked to write it again; a page that cannot is ignored.
    if (ask && ask.kind === "act" && ans === "yes" && typeof ctx.settleCard === "function") {
      try { ctx.settleCard({ card: ask.card_id || ask.card, option: ask.option, index: ask.option_index, written: true }); } catch { /* the page's own */ }
    }
    const r = await A.answer(S.conv, ask.id, ans);
    return { ok: r.ok, reason: r.out && r.out.refused };
  }

  // "Where did that go?" — the route lines of one turn, in plain words; never a prompt or a reply
  async function whereDidThatGo(turn) {
    const a = me();
    const r = await A.routes(S.conv, turn);
    const body = h("div", { class: "dock-where" });
    const routes = (r.ok && r.out.routes) || [];
    if (!routes.length) {
      body.append(h("p", null, a && a.proxy && a.proxy.on ? t("dock.route.none") : t("dock.proxy_absent")));
    } else {
      const here = routes.filter((x) => x.place === "here"), front = routes.filter((x) => x.place === "frontier"),
        away = routes.filter((x) => x.place === "elsewhere");
      if (!front.length && !away.length) body.append(h("p", null, t("dock.route.all_here")));
      else {
        const parts = [];
        const n = (k) => ctx.fmt.number(k, true);
        if (front.length) parts.push(t("dock.route.frontier", { n: n(front.length) }));
        if (away.length) parts.push(t("dock.route.elsewhere", { n: n(away.length) }));
        const priv = here.filter((x) => x.private), plain = here.filter((x) => !x.private);
        if (plain.length) parts.push(t("dock.route.here", { n: n(plain.length) }));
        if (priv.length) parts.push(t("dock.route.here_private", { n: n(priv.length) }));
        body.append(h("p", null, t("dock.route.count", { n: ctx.fmt.number(routes.length), parts: parts.join(", ") })));
      }
      const list = h("ul", { class: "dock-where-list" });
      for (const x of routes) {
        const secs = x.latency_ms == null ? null : Math.max(1, Math.round(x.latency_ms / 1000));
        list.append(h("li", null, t("dock.route.place." + x.place),
          secs ? h("span", { class: "dust" }, " · " + t(secs === 1 ? "dock.route.one_second" : "dock.route.seconds", { n: ctx.fmt.number(secs, true) })) : null));
      }
      body.append(list);
      body.append(h("details", { class: "dock-fold" }, h("summary", { class: "dust" }, t("dock.route.rules")),
        h("ul", null, routes.map((x) => h("li", { class: "dust" }, x.rule || t("dock.route.default_rule"))))));
      if (r.out.matched === "time") body.append(h("p", { class: "dust" }, t("dock.route.matched_by_time")));
    }
    ctx.openSheet({ title: t("dock.where_title"), body });
  }

  async function judge(turn, verdict, rating, note) {
    const r = await A.routes(S.conv, turn);
    const routes = (r.ok && r.out.routes) || [];
    if (!routes.length) { S.rated.set(turn, t("dock.discern_nothing")); render(); return; }
    const d = await discern(routes[routes.length - 1].route, verdict, rating, note);
    S.rated.set(turn, d.ok ? t(verdict === "rated" ? "dock.discern_rated" : "dock.discern_counted", { n: ctx.fmt.number(rating || 0, true) })
        + (d.out && d.out.signed === false ? " ○ " + t("record.verified.unsigned") + ". " + (d.out.said || "") : "")
      : (d.out && d.out.refused) || t("dock.discern_nothing"));
    render();
  }

  // ---------------------------------------------------------------- sheets
  /** every door to the ways of acting opens the harness's own modes, by their own names */
  function openModes() { return openHarnessModes(); }

  /** The person who brought you, from the record when it says (the witness of your `join` line, by
      name or house, with how to reach them): state.hud.person.brought_by, or your own entry among
      the actors. Absent, the sheet names "the one who gave you this". */
  function broughtBy() {
    const s = st();
    const p = (s.hud && s.hud.person) || {};
    const self = (s.actors || []).find((x) => x && x.id === s.actor) || {};
    const b = p.brought_by || self.brought_by || null;
    if (!b || typeof b !== "object") return null;
    const who = String(b.name || b.house || "").trim();
    const reach = typeof b.reach === "string" && /^(mailto:|https:\/\/)/i.test(b.reach.trim()) ? b.reach.trim() : null;
    return who || reach ? { who, reach } : null;
  }

  // The sheet behind her name (never a settings wall of a dozen controls): who
  // she is, where your words go, how to stop, how to reach a person, the keepsakes, and one choice,
  // read aloud or not; then one way to the rest, in Settings. At most eight controls and Close.
  // No view of the machine is here (the plain transcript and the command line live in the Agents room).
  function openAbout() {
    const a = me();
    const name = a && a.name;
    const body = h("div", { class: "dock-about-sheet" });
    body.append(h("p", null, name ? t("dock.about.who_named", { name }) : t("dock.about.who")));
    // where your words go: the one sentence the host also says at first contact (dock.first.words)
    body.append(h("p", { class: "eyebrow" }, t("dock.about.words_title")), h("p", null, wordsLine()));
    if (a && a.proxy && a.proxy.on) body.append(h("p", { class: "dust" }, t("dock.about.words_noted")));
    body.append(h("p", { class: "eyebrow" }, t("dock.about.stop_title")), h("p", null, t("dock.about.stop")));
    const by = broughtBy();
    body.append(h("p", { class: "eyebrow", id: "dock-about-reach" }, t("dock.about.reach_title")));
    if (by && by.who) body.append(h("p", null, t("dock.about.reach_named", { who: by.who })));
    else body.append(h("p", null, t("dock.about.reach_unnamed")));
    if (by && by.reach) body.append(h("p", null, h("a", { class: "link-btn dock-reach-link", href: by.reach, target: "_blank", rel: "noopener noreferrer" }, t("dock.about.write_to_them"))));
    if (opts.aboutExtra) { try { for (const n of [].concat(opts.aboutExtra() || [])) if (n) body.append(n); } catch { /* the page's own */ } }
    // how much you see of her work: Plain · Working · Full, kept on this device
    body.append(...depthKnob(() => close()));
    // the one choice kept here: whether she reads her replies aloud on this device
    body.append(...readAloud(() => close()));
    // everything else (how she asks, the voice's finer choices, the phone, your judgments) is in Settings
    if (typeof ctx.openSettings === "function") {
      body.append(h("p", { class: "dock-ways" }, h("button", { class: "link-btn dock-to-settings", type: "button", onclick: () => { close(); ctx.openSettings(); } }, t("dock.about.more_choices"))));
    }
    const close = ctx.openSheet({ title: name || t("dock.about.title_plain"), body });
  }

  /** Her choices for Settings (behind More): how she asks, the voice's finer choices, the phone; and,
      apart, the counting of your judgments, which sits with the study in Settings. */
  function settingsNodes(close) {
    const a = me();
    const agent = [];
    if (a && (a.modes || []).length) agent.push(h("p", { class: "dock-ways" }, h("button", { class: "link-btn", type: "button", onclick: () => { close(); openModes(); } }, t("dock.fewer_questions"))));
    // the fine choices fold under one heading each, opened on a tap, so Settings is a short list at first sight
    const folded = (label, kids) => { const d = h("details", { class: "dock-settings-fold" }, h("summary", { class: "link-btn" }, label), ...kids); return d; };
    const voice = voicePrefs(() => close());
    if (voice.length) agent.push(folded(t("dock.trust.settings.voice"), voice));
    const ph = st().hud && st().hud.phone;
    if (ph && ph.enabled && !ON_PHONE) {
      const kids = [h("button", { class: "link-btn", onclick: () => { close(); openPhone(); } }, t("dock.phone_card"))];
      for (const d of ph.devices || []) {
        kids.push(h("p", { class: "dust" }, t("dock.phone_device", { added: ctx.fmt.when(d.added) || "", seen: ctx.fmt.when(d.last_seen) || "" }), " · ",
          h("button", { class: "link-btn", onclick: async () => { await P.revoke(d.id); close(); } }, t("dock.phone_let_go"))));
      }
      agent.push(folded(t("dock.phone_title"), kids));
    }
    const judgment = [];
    if (a) {
      judgment.push(h("details", { class: "dock-settings-fold" }, h("summary", { class: "link-btn" }, t("dock.trust.settings.judgments")), h("p", { class: "dust" }, t("dock.discern_offer")),
        h("div", { class: "actions" },
          h("button", { class: "pill" + (a.discern_offered ? " primary" : ""), "aria-pressed": String(!!a.discern_offered),
            onclick: async () => { await A.prefs(a.id, { discern_offered: true }); close(); } }, t("dock.discern_yes")),
          h("button", { class: "pill quiet", "aria-pressed": String(!a.discern_offered),
            onclick: async () => { await A.prefs(a.id, { discern_offered: false }); close(); } }, t("dock.discern_no")))));
    }
    return { agent, judgment, name: (a && a.name) || null };
  }

  function openPhone() {
    const said = h("div", { class: "dock-pair", role: "status" });
    const body = h("div", null, h("p", null, t("dock.phone_window")),
      h("ol", { class: "dock-steps" }, h("li", null, t("dock.phone_step1")), h("li", null, t("dock.phone_step2")), h("li", null, t("dock.phone_step3"))),
      h("p", { class: "dust" }, t("dock.phone_fallback")), said);
    const letIn = h("button", { class: "pill primary", onclick: async () => {
      letIn.disabled = true;
      const l = await P.listen(true);
      if (!l.ok) { said.textContent = (l.out && l.out.refused) || ""; letIn.disabled = false; return; }
      const p = await P.pair();
      said.textContent = "";
      if (!p.ok) { said.textContent = (p.out && p.out.refused) || ""; letIn.disabled = false; return; }
      // the secure door (DESIGN-PHONE-DOOR §6): trust this computer once on the phone's plain page,
      // comparing the fingerprint in groups of four; then the door opens over its https address
      const trust = (st().hud && st().hud.phone && st().hud.phone.trust) || {};
      const fp = String(p.out.fingerprint || trust.fingerprint || "").replace(/[^0-9a-f]/gi, "").toUpperCase();
      if (trust.changed) said.append(h("p", { class: "dock-notice" }, t("dock.phone_renewed")));
      said.append(h("p", null, t("dock.phone_trust_once")), h("p", null, t("dock.phone_open_this")), h("p", { class: "dock-address" }, p.out.address));
      if (fp) said.append(h("p", { class: "dust" }, t("dock.phone_compare")),
        h("p", { class: "dock-fingerprint figures" }, (fp.match(/.{1,4}/g) || []).join(" ")));
      if (p.out.door) said.append(h("p", null, t("dock.phone_then_door")), h("p", { class: "dock-address" }, p.out.door));
      said.append(h("p", null, t("dock.phone_or_code")), h("p", { class: "dock-code figures" }, p.out.code),
        h("p", { class: "dust" }, t("dock.phone_code_minutes")));
    } }, t("dock.phone_let_in"));
    ctx.openSheet({ title: t("dock.phone_title"), body, actions: [letIn] });
  }

  async function speak(file) {   // a voice note from the phone's own recorder: words come back to read and send
    V.hearing = true; renderVoice();
    const r = await voice(file, false);
    V.hearing = false;
    V.note = r.ok ? "" : (r.out && r.out.refused) || t("dock.voice.failed");
    if (r.ok && r.out.text) { $.input.value = joinWords($.input.value, r.out.text); grow(); $.input.focus(); }
    renderVoice();
  }

  // ---------------------------------------------------------------- the layered voice
  const HOLD_MS = 350;
  const PIN_GAP = 24;      // her held line sits this far below the stream's fading top edge
  // a preference kept on this device (state.js's store, written through setPref to this browser only)
  const vpref = (k, d) => {
    if (store.prefs[k] !== undefined) return store.prefs[k];
    try { const v = localStorage.getItem("hud." + k); return v == null ? d : JSON.parse(v); } catch { return d; }
  };
  const lang = () => document.documentElement.lang || navigator.language || "en";
  // The two voice routes, with the page's token (or this phone's own): the same headers state.js's
  // calls carry, kept here because its fetch helper is not exported.
  let vtoken = null;
  async function vcall(path, init = {}) {
    const headers = { ...(init.headers || {}) };
    if (ON_PHONE) {
      try { const d = JSON.parse(localStorage.getItem("hud.device") || "null"); if (d && d.token) headers["X-HUD-Device"] = d.token; } catch { /* none */ }
    } else {
      if (!vtoken) { try { const r = await fetch("/token", { cache: "no-store" }); if (r.ok) vtoken = (await r.json()).token; } catch { /* no server */ } }
      if (vtoken) headers["X-HUD-Token"] = vtoken;
    }
    return fetch(path, { ...init, headers, cache: "no-store" });
  }
  async function voiceInfo() {
    if (V.info) return V.info;
    if (store.source !== "server") return (V.info = { hear: false, say: false });   // a file opened without a server: nothing to ask
    try { const r = await vcall("/voice/info"); V.info = r.ok ? await r.json() : { hear: false, say: false }; }
    catch { V.info = { hear: false, say: false }; }
    return V.info;
  }
  const Recognizer = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;
  // How this device can hear the person, best first: the browser's own listener held on the device
  // (processLocally) · the browser's recorder, its audio sent only to this computer's speech command
  // · the browser's listener that may reach its maker: offered from the first screen wherever the
  // page is a secure one (or this computer's own address), and used only after the "May I listen?"
  // sheet, which says so in one line on its first tap; never when the person chose "Keep my voice
  // here" · the phone's own recorder app (the file capture, which needs no certificate) · none.
  async function voiceWay() {
    if (V.way !== undefined) return V.way;
    const SR = Recognizer(), secure = window.isSecureContext !== false;
    let local = false;
    if (SR && secure && !V.deviceFailed) {
      try {
        if (typeof SR.available === "function") local = (await SR.available({ langs: [lang()], processLocally: true })) === "available";
        else local = "processLocally" in (SR.prototype || {});
      } catch { local = false; }
    }
    const info = await voiceInfo();
    const canRecord = secure && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) && typeof window.MediaRecorder === "function";
    V.way = local ? "device" : info.hear && canRecord ? "record" : SR && secure && vpref("voice_vendor", null) !== false ? "vendor"
      : info.hear ? "file" : null;
    V.vendorPossible = !!(SR && secure && !local);
    return V.way;
  }

  function micDown(e) {
    if (e && e.button > 0) return;
    if (e) { e.preventDefault(); try { $.mic.setPointerCapture(e.pointerId); } catch { /* not a pointer */ } }
    V.downAt = performance.now();
    if (V.loop.on) { V.downAt = 0; if (!interrupt() && V.listening) stopListening({ send: true }); else if (!V.listening && !V.speaking && V.loop.phase !== "thinking") loopListen(); return; }
    if (V.listening) { V.stopOnUp = true; return; }
    V.stopOnUp = false;
    V.intent = "hold";
    if (V.way === "file" || V.way === null) return;
    if (!vpref("voice_asked", false)) { V.intent = null; askToListen(); return; }
    startListening();
  }
  function micUp(cancelled) {
    if (!V.downAt) return;
    const held = performance.now() - V.downAt;
    V.downAt = 0;
    if (V.way === null) { V.note = t("dock.voice.no_way"); renderVoice(); return; }
    if (V.way === "file") { if (!cancelled) $.voiceFile.click(); return; }
    if (V.stopOnUp) { V.stopOnUp = false; stopListening({ send: !cancelled && !!vpref("voice_send", false) }); return; }
    if (cancelled) { stopListening({ send: false }); return; }
    if (held < HOLD_MS) { V.intent = "free"; V.mode = "free"; renderVoice(); return; }   // a tap: keep listening, hands-free
    V.intent = "release";
    stopListening({ send: !!vpref("voice_send", false) });                               // a hold let go
  }
  function micKey(e) {
    if ((e.key === " " || e.key === "Enter") && !e.repeat) {
      e.preventDefault();
      if (V.listening) { stopListening({ send: !!vpref("voice_send", false) }); return; }
      if (V.way === "file") { $.voiceFile.click(); return; }
      if (V.way === null) { V.note = t("dock.voice.no_way"); renderVoice(); return; }
      if (!vpref("voice_asked", false)) { askToListen(); return; }
      V.intent = "free"; startListening("free");
    }
  }

  // asked once, in words, with why; the browser's own question follows the yes
  async function askToListen(then) {
    // the way is found before the sheet is drawn (a first tap can come before it is known), so the
    // line about the browser's maker is said whenever that is the path in use, and only then
    await voiceWay();
    if (ui_asking) return;
    ui_asking = true;
    const yes = h("button", { class: "pill primary", type: "button", onclick: () => {
      setPref("voice_asked", true); if (V.way === "vendor") setPref("voice_vendor", true); close();
      if (then) then(); else { V.intent = "free"; startListening("free"); }
    } }, t("dock.voice.ask_yes"));
    const no = h("button", { class: "pill quiet", type: "button", onclick: () => close() }, t("dock.voice.ask_no"));
    // where words go: the one true sentence (the host's own, dock.first.words), and on the browser's
    // own listener the honest line about its maker
    const stays = ON_PHONE ? t("dock.voice.stays_phone") : wordsLine();
    const body = h("div", { class: "dock-voice-ask" }, h("p", null, t("dock.voice.ask_body")), h("p", null, t("dock.voice.ask_why")),
      V.way === "vendor" ? h("p", null, t("dock.voice.vendor_warn")) : null, h("p", { class: "dust" }, stays));
    const shut = ctx.openSheet({ title: t("dock.voice.ask_title"), body, actions: [yes, no] });
    const close = () => { ui_asking = false; shut(); };
    no.addEventListener("click", () => { ui_asking = false; });
  }

  async function startListening(mode) {
    stopSpeaking();                                   // the earpiece rule: she stops when the person starts
    const way = await voiceWay();
    if (mode !== "loop" && V.intent === "release") return;     // let go before the listener could open
    if (mode !== "loop" && V.intent === null) return;
    if (mode === "loop" && !V.loop.on) return;
    V.base = mode === "loop" ? "" : $.input.value; V.final = ""; V.interim = ""; V.note = ""; V.sendOnEnd = false;
    V.mode = mode || (V.intent === "free" ? "free" : "hold");
    if (mode === "loop") { $.input.value = ""; V.loop.phase = "listening"; }
    if (way === "device" || way === "vendor") {
      const SR = Recognizer();
      const rec = new SR();
      if (way === "device") try { rec.processLocally = true; } catch { /* the property is the browser's */ }
      rec.lang = lang(); rec.interimResults = true; rec.continuous = true; rec.maxAlternatives = 1;
      rec.onresult = (ev) => {
        let fin = "", inter = "";
        for (let i = 0; i < ev.results.length; i++) { const r = ev.results[i]; if (r.isFinal) fin += r[0].transcript; else inter += r[0].transcript; }
        V.final = fin.trim(); V.interim = inter.trim();
        $.input.value = joinWords(V.base, V.final); grow();
        if (V.mode === "loop") {                      // the end of her turn is a pause the person sets
          clearTimeout(V.pauseTimer);
          if (V.final || V.interim) V.pauseTimer = setTimeout(() => { if (V.listening && V.mode === "loop") stopListening({ send: true }); }, pauseMs());
        }
        renderVoice();
      };
      rec.onerror = (ev) => {
        const err = ev && ev.error;
        if (err === "not-allowed" || err === "service-not-allowed") { V.note = t("dock.voice.denied"); if (V.loop.on) endLoop(true); }
        else if (err === "no-speech") V.note = t("dock.voice.nothing_heard");
        else if (err === "aborted") V.note = "";
        else { V.note = t("dock.voice.failed"); if (way === "device") { V.deviceFailed = true; V.way = undefined; } }
      };
      rec.onend = () => finishListening();
      V.rec = rec;
      try { rec.start(); } catch { V.rec = null; V.note = t("dock.voice.failed"); renderVoice(); return; }
    } else if (way === "record") {
      try {
        V.media = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch { V.note = t("dock.voice.denied"); if (V.loop.on) endLoop(true); renderVoice(); return; }
      if (mode !== "loop" && V.intent === "release") { V.media.getTracks().forEach((x) => x.stop()); V.media = null; return; }
      V.chunks = [];
      const mr = new MediaRecorder(V.media);
      mr.ondataavailable = (ev) => { if (ev.data && ev.data.size) V.chunks.push(ev.data); };
      mr.onstop = async () => {
        if (V.media) V.media.getTracks().forEach((x) => x.stop());
        V.media = null; V.rec = null; V.listening = false;
        const blob = new Blob(V.chunks, { type: mr.mimeType || "audio/webm" });
        V.chunks = [];
        if (!blob.size || V.discard) { V.discard = false; V.mode = null; V.intent = null; renderVoice(); return; }
        V.hearing = true; renderVoice();
        const r = await voice(blob, false);
        V.hearing = false;
        if (r.ok && r.out.text) { $.input.value = joinWords(V.base, r.out.text); grow(); }
        else V.note = (r.out && r.out.refused) || t("dock.voice.failed");
        finishListening(true);
      };
      V.rec = mr;
      mr.start();
      if (V.mode === "loop") watchSilence(V.media, () => { if (V.listening && V.mode === "loop") stopListening({ send: true }); });
    } else return;
    V.listening = true;
    renderVoice();
  }

  function stopListening({ send = false, discard = false } = {}) {
    V.sendOnEnd = send; V.discard = discard;
    clearTimeout(V.pauseTimer);
    if (V.silence) { V.silence(); V.silence = null; }
    if (!V.rec) { V.listening = false; renderVoice(); return; }
    try { V.rec.stop(); } catch { finishListening(); }
  }

  function finishListening(recorded) {
    if (!recorded && V.rec && V.rec.state === "recording") return;   // the recorder finishes in its own onstop
    const loop = V.mode === "loop";
    V.rec = null; V.listening = false; V.mode = null; V.intent = null;
    if (V.interim) { $.input.value = joinWords($.input.value, V.interim); V.interim = ""; grow(); }   // the last words heard stay in the line
    if (loop && V.loop.on) {
      const words = $.input.value.trim();
      V.sendOnEnd = false; V.discard = false;
      if (!words) { setTimeout(loopListen, 60); return; }                    // nothing said: keep listening
      if (isStopWord(words)) { $.input.value = ""; grow(); stopAll(); return; } // a spoken "stop" or "wait" ends the turn and the loop
      V.loop.phase = "thinking"; renderVoice();
      send().then(() => { if (S.refusal && V.loop.on) endLoop(true); });
      return;
    }
    const go = V.sendOnEnd && $.input.value.trim();
    V.sendOnEnd = false;
    renderVoice();
    if (go) send(); else if ($.input.value) $.input.focus();
  }

  // ---------------------------------------------------------------- her voice
  const readOn = () => !!vpref("voice_read", false);
  // a turn is read only when the person spoke it into being from this page, so a page opened on a
  // conversation never reads its past (nothing auto-plays on load)
  function voiceTurn(turn, ask) {
    if (!(readOn() || V.loop.on) || voiceSilenced(window) || !V.mine.has(turn)) return false;
    const it = model().items.find((x) => x.who === "agent" && x.turn === turn);
    const said = it ? shapeTurn(it.parts, { done: true, shown: new Set(), key: "voice" }).said.join("\n\n") : "";
    const words = speakable(said);
    const key = S.conv + ":" + turn;
    const already = V.spoken.get(key) || 0;
    let rest = words.slice(already).trim();
    if (ask && ask.title && !V.askSpoken.has(ask.id)) { V.askSpoken.add(ask.id); rest = (rest ? rest + "\n" : "") + speakable(ask.title); }
    V.spoken.set(key, words.length);
    if (!rest) return false;
    sayAloud(rest, turn);
    return true;
  }

  async function sayAloud(text, turn) {
    if (voiceSilenced(window)) return;
    if (V.listening || V.hearing) return;    // the person is speaking: she does not talk over them
    stopSpeaking(true);
    V.speaking = { turn, conv: S.conv };
    if (V.loop.on) V.loop.phase = "speaking";
    render();
    const done = () => {
      if (!V.speaking || V.speaking.turn !== turn) return;
      V.speaking = null; render();
      if (V.loop.on) loopListen();                // then listening again
    };
    const info = await voiceInfo();
    if (info.say) {
      try {
        const r = await vcall("/voice/say", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
        if (r.ok && V.speaking && V.speaking.turn === turn) {
          const url = URL.createObjectURL(await r.blob());
          const audio = new Audio(url);
          V.audio = audio;
          audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); if (V.audio === audio) V.audio = null; done(); };
          await audio.play();
          return;
        }
      } catch { /* the computer's voice did not answer: the device's own reads it */ }
      if (!V.speaking || V.speaking.turn !== turn) return;
    }
    const synth = window.speechSynthesis;
    if (!synth || typeof window.SpeechSynthesisUtterance !== "function") { done(); return; }
    const u = new SpeechSynthesisUtterance(text);
    const v = calmestVoice(synth.getVoices ? synth.getVoices() : [], lang(), vpref("voice_name", null));
    try { if (v) { u.voice = v; u.lang = v.lang; } else u.lang = lang(); } catch { u.lang = lang(); }
    u.rate = 0.96; u.pitch = 1;
    u.onend = u.onerror = done;
    synth.speak(u);
  }

  function stopSpeaking(quiet) {
    const was = !!V.speaking;
    V.speaking = null;
    if (V.audio) { try { V.audio.pause(); } catch { /* gone */ } V.audio = null; }
    try { if (window.speechSynthesis && (was || window.speechSynthesis.speaking)) window.speechSynthesis.cancel(); } catch { /* none */ }
    if (was && !quiet) render();
  }

  // ---------------------------------------------------------------- voice mode: the hands-free loop
  const pauseMs = () => Math.round(1000 * Math.max(0.3, Math.min(5, Number(vpref("voice_pause", 0.8)) || 0.8)));
  function isStopWord(text) {
    const said = String(text || "").toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
    const stops = [].concat(t("dock.voice.mode_stop_words") || []).map((w) => String(w).toLowerCase());
    return said.length > 0 && said.length <= 2 && said.some((w) => stops.includes(w));
  }
  async function startLoop() {
    if (voiceSilenced(window)) return;                 // never in a test or a headless page
    const way = await voiceWay();
    if (!way || way === "file") { V.note = t("dock.voice.no_way"); renderVoice(); return; }
    if (!vpref("voice_asked", false)) { askToListen(() => startLoop()); return; }
    setPref("voice_mode", true);
    V.loop.on = true; V.note = "";
    try { if (navigator.wakeLock) V.wake = await navigator.wakeLock.request("screen"); } catch { V.wake = null; }
    render();
    loopListen();
  }
  function loopListen() {
    if (!V.loop.on || V.listening || V.speaking) return;
    V.loop.phase = "listening";
    startListening("loop");
  }
  function endLoop(keepPref) {
    if (!V.loop.on) return;
    V.loop.on = false; V.loop.phase = null;
    if (!keepPref) setPref("voice_mode", false);
    if (V.listening) stopListening({ discard: true });
    stopSpeaking(true);
    try { if (V.wake) V.wake.release(); } catch { /* gone */ }
    V.wake = null;
    V.note = V.note || t("dock.voice.mode_ended");
    render();
    // said once, then gone: "Voice mode has ended." never lingers under the line
    const ended = t("dock.voice.mode_ended");
    setTimeout(() => { if (V.note === ended && !V.loop.on) { V.note = ""; renderVoice(); } }, 4000);
  }
  // a tap on the conversation, or the microphone, stops her at once; in the loop it listens again
  function interrupt() {
    if (!V.speaking) return false;
    stopSpeaking();
    if (V.loop.on) loopListen();
    return true;
  }
  // the server's speech path in the loop: a short recording ends on a pause (read from the level
  // of the sound, never played: the analyser is joined to nothing that sounds)
  function watchSilence(stream, onPause) {
    let ctxA = null, timer = null;
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      ctxA = new AC();
      const an = ctxA.createAnalyser(); an.fftSize = 1024;
      ctxA.createMediaStreamSource(stream).connect(an);
      const buf = new Float32Array(an.fftSize);
      let heard = false, quiet = 0;
      const began = performance.now();
      timer = setInterval(() => {
        an.getFloatTimeDomainData(buf);
        let sum = 0; for (const x of buf) sum += x * x;
        const loud = Math.sqrt(sum / buf.length) > 0.02;
        const now = performance.now();
        if (loud) { if (!heard) { heard = true; V.loop.phase = "hearing"; renderVoice(); } quiet = 0; }
        else if (heard) { quiet = quiet || now; if (now - quiet >= pauseMs()) onPause(); }
        if (now - began > 30000) onPause();           // a short chunk: never more than thirty seconds
      }, 100);
    } catch { /* no level to read: the person ends the turn with the microphone */ }
    V.silence = () => { clearInterval(timer); try { ctxA && ctxA.close(); } catch { /* closed */ } };
  }
  function loopWords() {
    if (!V.loop.on) return vpref("voice_mode", false) && !voiceSilenced(window) ? t("dock.voice.mode_resume") : "";
    if (V.speaking) return t("dock.voice.mode_speaking");
    if (V.hearing || (V.listening && (V.final || V.interim)) || V.loop.phase === "hearing") return t("dock.voice.hearing");
    if (V.loop.phase === "thinking") return t("dock.voice.thinking");
    return t("dock.voice.listening");
  }

  function speakingMark(it) {
    if (!V.speaking || V.speaking.turn !== it.turn || V.speaking.conv !== S.conv) return null;
    return h("button", { class: "link-btn dock-voice-speaking", type: "button", "aria-label": t("dock.voice.stop_label"), onclick: () => stopSpeaking() },
      t("dock.voice.speaking") + " · " + t("dock.voice.tap_to_stop"));
  }

  // the listening state, in words beside the line to speak (no glow, no pulse, no drawn wave)
  function renderVoice() {
    if (!$.mic) return;
    const way = V.way;
    $.mic.hidden = way === null || way === undefined || S.view !== "ice";
    $.mic.classList.toggle("is-listening", !!V.listening);
    $.mic.setAttribute("aria-pressed", String(!!V.listening));
    $.mic.setAttribute("aria-label", V.listening ? t("dock.voice.tap_to_stop") : way === "file" ? t("dock.voice.recorder") : t("dock.voice.mic_label"));
    $.heard.textContent = V.listening && V.interim ? V.interim : "";
    $.heard.hidden = !$.heard.textContent;
    let line = "";
    const lw = loopWords();
    el.classList.toggle("is-voice-mode", V.loop.on);
    el.classList.toggle("is-voice-dim", V.loop.on && !!vpref("voice_dim", false));
    if ($.stageWord) { $.stage.hidden = !V.loop.on; $.stageWord.textContent = lw; if ($.stageName) $.stageName.textContent = nameOf(me()); }
    if ($.modeBtn) { $.modeBtn.setAttribute("aria-pressed", String(V.loop.on)); $.modeBtn.classList.toggle("primary", V.loop.on); }
    if (lw) line = lw;
    else if (V.hearing) line = t("dock.voice.hearing");
    else if (V.listening) line = t("dock.voice.listening") + " · " + (V.mode === "free" ? t("dock.voice.tap_to_stop") : t("dock.voice.let_go")); else if (V.note) line = V.note;
    $.voiceSaid.textContent = line;
    $.voiceSaid.classList.toggle("is-listening", !!V.listening);
  }

  // a choice kept per device: two pills, the chosen one filled
  function prefPair(k, on, off, d, close) {
    const changed = (x) => { if (x === "voice_vendor") { V.way = undefined; voiceWay().then(renderVoice); } };
    const v = !!vpref(k, d);
    return h("div", { class: "actions" },
      h("button", { class: "pill" + (v ? " primary" : ""), "aria-pressed": String(v), onclick: () => { setPref(k, true); changed(k); close(); } }, on),
      h("button", { class: "pill quiet", "aria-pressed": String(!v), onclick: () => { if (k === "voice_read") stopSpeaking(); setPref(k, false); changed(k); close(); } }, off));
  }
  // the one voice choice behind her name: read aloud, or words only
  function readAloud(close) {
    return [h("p", { class: "eyebrow" }, t("dock.voice.prefs_title")), h("p", { class: "dust" }, t("dock.voice.read_help")),
      prefPair("voice_read", t("dock.voice.read_on"), t("dock.voice.read_off"), false, close)];
  }
  // the voice's finer choices, in Settings: kept per device
  function voicePrefs(close) {
    const out = [];
    const pair = (k, on, off, d) => prefPair(k, on, off, d, close);
    if (V.way && V.way !== "file") out.push(h("p", { class: "dust" }, t("dock.voice.send_help")), pair("voice_send", t("dock.voice.send_on"), t("dock.voice.send_off"), false));
    const synth = window.speechSynthesis;
    const voices = (synth && synth.getVoices ? synth.getVoices() : []).filter((v) => v.localService && !NOVELTY.test(v.name)
      && String(v.lang || "").toLowerCase().startsWith(lang().toLowerCase().split("-")[0]));
    if (V.info && V.info.say) out.push(h("p", { class: "dust" }, t("dock.voice.computer_voice")));
    else if (voices.length > 1) {
      const pick = calmestVoice(voices, lang(), vpref("voice_name", null));
      const sel = h("select", { class: "dock-voice-pick", "aria-label": t("dock.voice.which") },
        voices.map((v) => h("option", { value: v.voiceURI, ...(pick && pick.voiceURI === v.voiceURI ? { selected: "" } : {}) }, v.name)));
      sel.addEventListener("change", () => setPref("voice_name", sel.value));
      out.push(h("label", { class: "dock-voice-which" }, h("span", { class: "dust" }, t("dock.voice.which")), sel));
    }
    if (V.way && V.way !== "file") {
      out.push(h("p", { class: "dust" }, t("dock.voice.mode_help")));
      const sel = h("select", { class: "dock-voice-pick", "aria-label": t("dock.voice.pause") },
        [0.5, 0.8, 1.2, 2].map((n) => h("option", { value: String(n), ...(Number(vpref("voice_pause", 0.8)) === n ? { selected: "" } : {}) },
          t("dock.voice.pause_s", { n: String(n) }))));
      sel.addEventListener("change", () => setPref("voice_pause", Number(sel.value)));
      out.push(h("label", { class: "dock-voice-which" }, h("span", { class: "dust" }, t("dock.voice.pause")), sel),
        pair("voice_dim", t("dock.voice.dim_on"), t("dock.voice.dim_off"), false));
    }
    if (V.vendorPossible && V.way !== "device") {
      out.push(h("p", { class: "dust" }, t("dock.voice.vendor_warn")),
        pair("voice_vendor", t("dock.voice.vendor_on"), t("dock.voice.vendor_off"), false));
    }
    return out.length ? [h("p", { class: "eyebrow" }, t("dock.voice.prefs_title")), ...out] : out;
  }

  // ---------------------------------------------------------------- the command line (a second conversation, same home)
  async function openCommandLine() {
    const a = me();
    if (!a) return;
    S.view = "line";
    render();
    if (S.pty) return;
    const r = await A.ptyOpen(a.id);
    if (!r.ok) { S.ptyText = ""; S.refusal = (r.out && r.out.refused) || t("dock.line_refused"); S.view = "ice"; render(); return; }
    S.pty = r.out.pty;
    S.ptyText = ""; S.term = makeTerminal();
    S.ptyStream = A.ptyStream(S.pty, (ev) => {
      if (ev.kind === "out") S.ptyText = S.term.write(ev.text);
      if (ev.kind === "exit") { S.ptyText += "\n" + t("dock.line_ended") + "\n"; S.pty = null; if (S.ptyStream) S.ptyStream.close(); }
      renderLine();
    });
  }
  function closeCommandLine() {
    if (S.pty) A.ptyClose(S.pty);
    if (S.ptyStream) S.ptyStream.close();
    S.pty = null; S.ptyStream = null;
    S.view = "ice";
    render();
  }

  // a microphone drawn in one hairline, in the ink of the text (no light, no fill but when listening)
  function micGlyph() {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("width", "20"); svg.setAttribute("height", "20"); svg.setAttribute("aria-hidden", "true");
    for (const d of ["M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z", "M5.5 11a6.5 6.5 0 0 0 13 0", "M12 17.5V21", "M9 21h6"]) {
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", d); path.setAttribute("fill", "none"); path.setAttribute("stroke", "currentColor");
      path.setAttribute("stroke-width", "1.5"); path.setAttribute("stroke-linecap", "round");
      svg.append(path);
    }
    return svg;
  }

  // ---------------------------------------------------------------- the frame
  function build() {
    el.textContent = "";
    $.bar = h("button", { class: "dock-bar", type: "button", onclick: () => open(true) });
    $.pane = h("div", { class: "dock-pane", role: "region", "aria-label": t("dock.label") });
    $.dealLine = h("button", { class: "dock-dealline", type: "button", onclick: () => open(false) });
    $.head = h("header", { class: "dock-head" });
    $.scroll = h("div", { class: "dock-scroll", tabindex: "-1" });
    $.turns = h("div", { class: "dock-turns", "aria-live": "polite" });
    $.scroll.append($.turns);
    $.line = h("div", { class: "dock-line" });
    $.notices = h("div", { class: "dock-notices" });
    $.asks = h("div", { class: "dock-asks" });
    $.about = h("p", { class: "dock-aboutline dust" });
    $.input = h("textarea", { class: "dock-input", rows: "1", "aria-label": t("dock.talk"), placeholder: t("dock.talk") });
    $.input.addEventListener("keydown", onInputKey);
    $.input.addEventListener("input", () => { grow(); renderCommands(); });
    $.commands = h("ul", { class: "dock-commands", role: "listbox" });
    $.send = h("button", { class: "pill primary dock-send", type: "button", onclick: () => send() }, t("dock.send"));
    $.stop = h("button", { class: "pill quiet dock-stop", type: "button", hidden: "", onclick: () => stopAll() }, t("dock.stop"));
    $.voiceFile = h("input", { type: "file", accept: "audio/*", capture: "", class: "sr-only", tabindex: "-1",
      onchange: () => { if ($.voiceFile.files[0]) speak($.voiceFile.files[0]); $.voiceFile.value = ""; } });
    // the microphone, at the line to speak: hold and let go, or tap to keep listening (44 px)
    $.mic = h("button", { class: "dock-mic", type: "button", hidden: "", "aria-pressed": "false", "aria-label": t("dock.voice.mic_label") }, micGlyph());
    $.mic.addEventListener("pointerdown", micDown);
    $.mic.addEventListener("pointerup", (e) => { e.preventDefault(); micUp(false); });
    $.mic.addEventListener("pointercancel", () => micUp(true));
    $.mic.addEventListener("contextmenu", (e) => e.preventDefault());
    $.mic.addEventListener("keydown", micKey);
    $.heard = h("p", { class: "dock-voice-interim dust", "aria-live": "polite", hidden: "" });
    $.voiceSaid = h("p", { class: "dock-voice-state dust", role: "status" });
    $.state = h("p", { class: "dock-state dust", role: "status" });
    // the row never moves: Stop has its own place above it, Send is never resized, and a press on
    // Send never takes the focus from the line (so nothing shifts between the press and the tap)
    $.send.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse" || document.activeElement === $.input) e.preventDefault(); });
    $.stop.addEventListener("pointerdown", (e) => e.preventDefault());
    const row = h("div", { class: "dock-inputrow" }, $.input, $.mic, $.send);
    $.stopRow = h("div", { class: "dock-stoprow" }, $.stop);
    $.modeSlot = h("div", { class: "dock-voice-slot", hidden: "" });
    // her workers at work, beneath the stream and above the line to speak (the trust layer)
    $.workers = h("ul", { class: "dock-workers", "aria-label": t("dock.trust.worker.label"), hidden: "" });
    $.foot = h("div", { class: "dock-foot" }, $.notices, $.asks, $.about, $.workers, $.commands, $.heard, $.stopRow, row, $.voiceFile, $.voiceSaid, $.modeSlot, $.state);
    // voice mode's stage: the one state in large dust; dimmed to the dark ground when the person asks
    $.stageWord = h("p", { class: "dock-voice-stage-word", role: "status", "aria-live": "polite" });
    $.stageName = h("p", { class: "dock-voice-stage-name" });
    $.stage = h("div", { class: "dock-voice-stage", hidden: "" }, $.stageName, $.stageWord,
      h("button", { class: "link-btn dock-voice-leave", type: "button", onclick: (e) => { e.stopPropagation(); endLoop(); } }, t("dock.voice.mode_leave")));
    $.stage.addEventListener("click", () => interrupt());
    $.scroll.addEventListener("click", () => interrupt());   // a tap anywhere on the conversation stops her
    // her own scroll releases the hold on her line
    for (const ev of ["wheel", "touchmove"]) $.scroll.addEventListener(ev, () => { S.pin = false; }, { passive: true });
    $.scroll.addEventListener("keydown", (e) => { if (/^(Arrow|Page|Home|End| )/.test(e.key)) S.pin = false; });
    $.pane.append($.dealLine, $.head, $.scroll, $.line, $.stage, $.foot);
    el.append($.bar, $.pane);
    // the clocks count each second without a redraw (the live line, the workers' time); the older presence line every five
    let ticks = 0;
    S.tick = setInterval(() => {
      ticks++;
      if (depth()) {
        if (S.live && S.live.el.isConnected) { const x = liveText(S.live.it, S.live.t0); if (x && S.live.el.textContent !== x) S.live.el.textContent = x; }
        for (const c of S.workerClocks || []) if (c.el.isConnected) c.el.textContent = " · " + durWords(Date.now() - c.t0, t);
      } else if (ticks % 5 === 0 && S.thinkingSince && S.view === "ice") render();
    }, 1000);
    // words another view hands the dock (The Deal's first act): set in the line to speak, sent only by the player
    S.onWords = (e) => { const w = e && e.detail && e.detail.text; if (!w || !$.input) return; $.input.value = w; grow(); setTimeout(() => $.input.focus(), 40); };
    if (!INLINE) window.addEventListener("lionsberg:dock-words", S.onWords);
  }

  function open(v) {
    if (INLINE) { if (v) setTimeout(() => $.input && $.input.focus(), 30); return; }
    if (!ctx.dock) return;
    ctx.dock.setOpen(v);
    if (v) setTimeout(() => $.input && $.input.focus(), 30);
  }

  function grow() { if (!$.input.value) { $.input.style.height = ""; return; } $.input.style.height = "auto"; $.input.style.height = Math.min($.input.scrollHeight, 200) + "px"; }

  function onInputKey(e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); return; }
    if (e.key === "ArrowUp" && !$.input.value && S.recall) { e.preventDefault(); $.input.value = S.recall; grow(); return; }
    if (e.key === "Escape") {
      e.preventDefault();
      const a = me();
      if (busy() || V.loop.on) stopAll(); else open(false);
    }
  }

  function renderCommands() {
    const a = me();
    $.commands.textContent = "";
    const v = $.input.value;
    if (!a || !v.startsWith("/") || v.includes(" ") || !(a.commands || []).length) return;
    for (const c of a.commands.filter((x) => ("/" + x.name).startsWith(v)).slice(0, 8)) {
      $.commands.append(h("li", null, h("button", { type: "button", onclick: () => { $.input.value = "/" + c.name + " "; $.commands.textContent = ""; $.input.focus(); } },
        "/" + c.name, c.description ? h("span", { class: "dust" }, " · " + c.description) : null)));
    }
  }

  // ---------------------------------------------------------------- render
  function stateWords(a) {
    // a state word only when it matters; at rest and at work the head says nothing (the field says it)
    if (!a) return "";
    if (ON_PHONE && ctx.offline) return t("dock.state.computer_asleep");
    if (a.asks_open > 0) return t("dock.state.waiting");
    return ["waiting", "waking", "offline", "away"].includes(a.state) ? t("dock.state." + a.state) : "";
  }

  function ringJoin(a) {
    return h("span", { class: "dock-join", "aria-hidden": "true" }, h("i", { class: "dock-mark" }), h("i", { class: "dock-hair" }), h("i", { class: "dock-ring" }));
  }

  function render() {
    if (!el || !ctx) return;
    const s = st();
    const a = me();
    el.hidden = !s.actor;
    el.classList.toggle("is-open", isOpen());
    if (el.dataset.view !== S.view && opts.onView) { try { opts.onView(S.view); } catch { /* the room's own */ } }
    el.dataset.view = S.view;

    // the collapsed bar or rail
    $.bar.textContent = "";
    const waiting = a && (a.state === "waiting" || a.asks_open > 0);
    $.bar.append(ringJoin(a), h("span", { class: "dock-name" }, nameOf(a)),
      h("span", { class: "dock-bartalk" + (waiting ? " is-waiting" : "") }, waiting ? t("dock.waiting_on_you") : t("dock.talk")));
    $.bar.setAttribute("aria-expanded", String(isOpen()));

    // The Deal's top line, held above the open sheet on a phone
    const n = ((s.deal && s.deal.cards) || []).filter((c) => !c.answered).length;
    $.dealLine.textContent = n === 0 ? t("dock.deal_line_none") : n === 1 ? t("dock.deal_line_one") : t("dock.deal_line", { n: ctx.fmt.number(n, true) });

    renderHead(a);
    if (S.view === "line") { renderLine(); return; }
    $.line.textContent = "";
    if (S.view === "terminal") renderTerminal(); else renderTurns(a);
    renderNotices(a);
    renderAsks(a);
    renderAbout();
    renderState();
    renderVoice();
    renderWorkers();
    renderStatus();
    // Stop is in view whenever a turn runs, a worker of hers runs (the trust layer), or voice mode is on
    // one Stop per thing: the input row's stops her turn (or voice mode) and is seen only then; each worker's is on its row
    $.stop.hidden = !(busy() || V.loop.on);
    el.dataset.busy = busy() ? "true" : "false";
    if (opts.placeholder) { const p = opts.placeholder(); if (p && $.input.placeholder !== p) { $.input.placeholder = p; $.input.setAttribute("aria-label", p); } }
    if (opts.onRender) { try { opts.onRender(); } catch { /* the page's own */ } }
  }

  function renderHead(a) {
    $.head.textContent = "";
    // one quiet button: the agent's own name opens the sheet about it: who she is, where your words
    // go, how to stop, how to reach a person, and Fewer questions
    const ring = h("button", { class: "dock-who", type: "button", onclick: openAbout, "aria-label": t("dock.about_agent") }, ringJoin(a),
      h("span", { class: "dock-name" }, nameOf(a)), h("span", { class: "dock-more" }, t("dock.about_word")));
    const words = stateWords(a);
    const state = h("span", { class: "dock-statewords" + (a && (a.state === "waiting" || a.asks_open > 0) ? "" : " dust") }, words);
    const back = S.view !== "ice" && !INLINE
      ? h("button", { class: "link-btn dock-back", type: "button", onclick: () => (S.view === "line" ? closeCommandLine() : (S.view = "ice", render())) }, t("dock.view_ice"))
      : null;
    const close = h("button", { class: "link-btn dock-close", type: "button", onclick: () => open(false) }, t("dock.close"));
    // voice mode: one switch, kept on this device, never offered to a page a test drives
    const canLoop = V.way && V.way !== "file" && S.view === "ice" && (INLINE || !voiceSilenced(window));
    $.modeBtn = canLoop ? h("button", { class: "pill quiet dock-voice-mode" + (V.loop.on ? " primary" : ""), type: "button", "aria-pressed": String(V.loop.on),
      onclick: () => (V.loop.on ? endLoop() : startLoop()) }, t("dock.voice.mode")) : null;
    // inline (the Talk, the Bodies room) the head is the host's, often hidden: the switch sits at the foot
    $.head.append(ring, state, back || "", INLINE ? "" : $.modeBtn || "", INLINE ? "" : close);
    // the page that holds the conversation may give the switch a place in its own head (the Talk)
    let host = null;
    try { host = opts.modeSlot ? opts.modeSlot() : null; } catch { host = null; }
    if (host) { host.textContent = ""; if (INLINE && $.modeBtn) host.append($.modeBtn); host.hidden = !(INLINE && $.modeBtn); }
    if ($.modeSlot) { $.modeSlot.textContent = ""; if (!host && INLINE && $.modeBtn) $.modeSlot.append($.modeBtn); $.modeSlot.hidden = !(!host && INLINE && $.modeBtn); }
  }

  // the person's field: the made frames, still at rest, turning (one crossing into the next) while
  // the agent is at work. Engraved, unlit; under reduced motion it is still.
  function field(turning, size) {
    const f = h("span", { class: "dock-field" + (turning ? " is-turning" : "") + (size ? " dock-field--" + size : ""), "aria-hidden": "true" });
    for (const src of FIELD) f.append(h("img", { src, alt: "", decoding: "async", width: "96", height: "96" }));
    return f;
  }

  function renderTurns(a) {
    const { items } = model();
    // a redraw keeps the person's place: it follows the end only when they were at the end
    const sc = $.scroll;
    const atEnd = !sc.clientHeight || sc.scrollHeight - sc.scrollTop - sc.clientHeight < 48;
    // within about one screen of the end: a worker's hand-back that lands is brought into view (panel 4, o)
    const nearEnd = !sc.clientHeight || sc.scrollHeight - sc.scrollTop - sc.clientHeight < Math.max(48, sc.clientHeight);
    const backs = items.filter((x) => x.who === "done" || x.who === "finished").length;
    const newBack = S.backs != null && S.backsConv === S.conv && backs > S.backs;
    S.backs = backs; S.backsConv = S.conv;
    let lastBack = null;
    const keepTop = sc.scrollTop;
    $.turns.textContent = "";
    const s = st();
    if (!a) {
      $.turns.append(h("p", { class: "dock-empty dust" }, t("dock.not_set_up")));
      return;
    }
    const now = performance.now();
    let recheck = null;
    if (!items.length && !S.outbox.length) {
      // the rest state of a new conversation: the field, still; the agent's greeting from the record, when there is one
      const greet = s.deal && s.deal.greeting;
      $.turns.append(h("div", { class: "dock-rest" }, field(false, "rest"), greet ? h("div", { class: "dock-letter" }, ...letter(h, greet)) : null));
    }
    const lastAgent = [...items].reverse().find((x) => x.who === "agent");
    const working = !!(S.thinkingSince || (a && (a.state === "thinking" || a.state === "waking")));
    // the page's own turns (the Talk's questions, its answers, its settled lines), set in time order
    let local = [];
    try { local = opts.localTurns ? (opts.localTurns() || []) : []; } catch { local = []; }
    local = local.slice().sort((x, y) => x.at - y.at);
    // what was said before this sitting is folded above "Earlier" (the page says from when); never drawn first
    let before = 0;
    try { before = opts.foldBefore ? Number(opts.foldBefore()) || 0 : 0; } catch { before = 0; }
    let folded = 0;
    const old = (ms) => before > 0 && ms != null && !Number.isNaN(ms) && ms < before;
    // a turn the page marks `keep` (an ask still open) is never folded away
    // nor is a settled line whose Undo still holds: it stays in sight for the whole undo window
    const undoHolds = (x) => !!(x.node && x.node.querySelector && x.node.querySelector(".talk-undo"));
    local = local.filter((x) => { if (!x.keep && !undoHolds(x) && old(x.at)) { folded++; return false; } return true; });
    let li = 0;
    const flushLocal = (until) => { while (li < local.length && (until == null || local[li].at < until)) $.turns.append(local[li++].node); };
    let lastAt = null;
    for (const it of items) {
      const at = it.ts ? Date.parse(it.ts) : null;
      if (at != null && !Number.isNaN(at)) lastAt = at;
      // an ask still open is never folded away: it waits on her, so it stays in view
      const openAsk = it.who === "ask" && (model().asks.get(it.id) || {}).open;
      if (old(lastAt) && !openAsk) { if (it.who !== "note") folded++; continue; }
      // the page's own lines (her "start it", a settled yes) go in by time before every stamped item, so a
      // worker's words or its end line follow the yes that started it, replayed as they came live
      if (at != null && !Number.isNaN(at)) flushLocal(at);
      if (it.who === "note") { $.turns.append(h("p", { class: "dock-note dust" }, t(it.key || "dock.note_left"))); continue; }
      if (it.who === "local") { $.turns.append(h("div", { class: "dock-row" }, h("article", { class: "dock-turn dock-turn--agent dock-turn--local" }, h("div", { class: "dock-letter" }, ...letter(h, it.text))))); continue; }
      if (it.who === "ask") { const n = askTurn(it.id, items[items.indexOf(it) - 1]); if (n) $.turns.append(n); continue; }
      if (it.who === "done") { lastBack = doneTurn(it); $.turns.append(lastBack); continue; }
      if (it.who === "end" || it.who === "notice" || it.who === "finished") { const n = depth() ? trustItem(it, items) : null; if (n) { $.turns.append(n); if (it.who === "finished") lastBack = n; } continue; }
      if (it.who === "worker") {
        $.turns.append(h("div", { class: "dock-row" }, h("article", { class: "dock-turn dock-turn--worker" },
          h("p", { class: "talk-ask-from dust" }, h("span", { class: "talk-ask-name" }, it.name)), h("div", { class: "dock-letter" }, ...letter(h, it.text)))));
        continue;
      }
      if (it.who === "you") {
        const turn = h("article", { class: "dock-turn dock-turn--you" },
          it.about ? h("p", { class: "dust dock-aboutsaid" }, t("dock.about_line", { title: it.about })) : null,
          h("p", { class: "dock-words" }, it.text));
        if (me().discern_offered && /^\s*no\b/i.test(it.text)) {
          const prev = items.slice(0, items.indexOf(it)).reverse().find((x) => x.who === "agent");
          if (prev && !S.rated.has(prev.turn)) turn.append(h("button", { class: "link-btn dust", type: "button",
            onclick: () => judge(prev.turn, "corrected", null, it.text) }, t("dock.count_as_correction")));
        }
        $.turns.append(turn);
        continue;
      }
      const r = agentTurn(it, it === lastAgent, a, now, working);
      if (r.recheck != null) recheck = Math.min(recheck == null ? Infinity : recheck, r.recheck);
      $.turns.append(r.row);
    }
    flushLocal(null);
    if (opts.onFolded) { try { opts.onFolded(folded); } catch { /* the page's own */ } }
    for (const o of S.outbox) $.turns.append(h("article", { class: "dock-turn dock-turn--you is-sending" },
      h("p", { class: "dock-words" }, o.text), o.waiting ? h("p", { class: "dust" }, t("dock.waiting_for_computer")) : null));
    // her words are out and nothing of the agent's has come yet: the field appears where its words will be, turning
    const lastItem = items[items.length - 1];
    if (working && (S.outbox.length || (lastItem && lastItem.who === "you"))) {
      $.turns.append(h("div", { class: "dock-row" }, h("article", { class: "dock-turn dock-turn--agent is-live" },
        h("div", { class: "dock-turnmark" }, field(true, "live")), depth() ? liveLine(null) : presenceLine(null))));
    }
    // (lines the agent proposed from something it read are dealt in The Deal, never repeated at the foot of the talk)
    clearTimeout(S.holdTimer);
    if (recheck != null) S.holdTimer = setTimeout(render, Math.max(30, recheck));
    if (isOpen() && newBack && nearEnd && lastBack) {
      // the hand-back's foot at the foot of the view (never past the end); her pin yields to it
      S.pin = false;
      const node = lastBack;
      requestAnimationFrame(() => {
        const r = node.getBoundingClientRect(), v = $.scroll.getBoundingClientRect();
        if (r.bottom <= v.bottom && r.top >= v.top) return;
        const top = $.scroll.scrollTop + r.bottom - v.bottom + 8;
        $.scroll.scrollTop = Math.max(0, Math.min(top, $.scroll.scrollHeight - $.scroll.clientHeight));
      });
    } else if (isOpen()) {
      if (S.pin) requestAnimationFrame(holdPin);
      else if (atEnd) requestAnimationFrame(() => { $.scroll.scrollTop = $.scroll.scrollHeight; }); else $.scroll.scrollTop = keepTop;
    }
  }
  /** her newest line at the top of the view (a breath below the fading edge), never past the end */
  function holdPin() {
    if (!S.pin || !$.scroll) return;
    const you = [...$.turns.querySelectorAll(".dock-turn--you")].pop();
    if (!you) return;
    const top = $.scroll.scrollTop + you.getBoundingClientRect().top - $.scroll.getBoundingClientRect().top - PIN_GAP;
    S.pinning = true;
    $.scroll.scrollTop = Math.max(0, Math.min(top, $.scroll.scrollHeight - $.scroll.clientHeight));
    requestAnimationFrame(() => { S.pinning = false; });
  }

  // what the agent is doing, in words, once ten seconds have passed with it at work (at once under reduced motion)
  function presenceLine(it) {
    const secs = S.thinkingSince ? Math.round((Date.now() - S.thinkingSince) / 1000) : 0;
    const reduced = document.documentElement.dataset.motion === "reduce" || (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
    const said = it && it._shaped && it._shaped.interim.length;
    if (secs < 10 && !reduced && !said) return null;
    let doing = null;
    if (it) {
      const shaped = it._shaped;
      if (shaped && shaped.interim.length) doing = shaped.interim[shaped.interim.length - 1].replace(/[.…:]+$/, "");
      else if (it.tools.length) doing = t("dock.work.working");
    }
    let line = doing || t("dock.work.with_you");
    if (secs >= 10) line += " · " + t("dock.thinking_for", { n: ctx.fmt.number(Math.round(secs / 10) * 10, true) });
    return h("p", { class: "dock-presence dust", role: "status" }, line);
  }

  // the margin speaks the record's words only (card, commitment, kept, said, written), never a
  // tool's: what the agent read, searched or ran is not a margin line; a file it changed on this
  // computer is one line, WRITTEN, in kept ink, the change folded (the fourth bar reading)
  function workLine(it) {
    const edits = (it.tools || []).filter((x) => x.kind === "edit" || x.kind === "delete" || x.kind === "move");
    if (!edits.length) return null;
    const n = edits.length;
    const sentence = t(n === 1 ? "dock.work.written_one" : "dock.work.written", { n: ctx.fmt.number(n, true) });
    const steps = h("ul", { class: "dock-steps-list" });
    for (const x of edits) {
      const diff = (x.content || []).find((c) => c.type === "diff");
      const name = String((diff && diff.path) || x.title || "").split(/[\\/]/).pop().replace(/^(Edit|Write|Delete|Move)\s+/, "");
      const li = h("li", { class: "dust" }, name || t("dock.tool_untitled"));
      if (diff) {
        const pre = document.createElement("pre"); pre.className = "dock-raw dock-diff";
        pre.textContent = [...String(diff.old || "").split("\n").filter(Boolean).map((l) => "− " + l), ...String(diff.new || "").split("\n").filter(Boolean).map((l) => "+ " + l)].join("\n");
        li.append(h("details", { class: "dock-fold" }, h("summary", { class: "dust" }, t("dock.tool_change")), pre));
      }
      steps.append(li);
    }
    return h("details", { class: "dock-work ink-kept" },
      h("summary", null, h("span", { class: "eyebrow" }, t("dock.work.eyebrow")), h("span", { class: "dock-mwords" }, sentence)),
      steps);
  }

  function agentTurn(it, latest, a, now, working) {
    const row = h("div", { class: "dock-row" });
    const live = latest && !it.done;
    const turn = h("article", { class: "dock-turn dock-turn--agent" + (live ? " is-live" : ""), tabindex: "0", dataset: { turn: String(it.turn) } });
    const askOpen = [...model().asks.values()].some((x) => x.open && x.turn === it.turn);
    // the field marks her latest turn only (it turns while she works); an older turn carries no glyph
    if (latest) turn.append(h("div", { class: "dock-turnmark" }, field(live && working && !askOpen, live ? "live" : null)));
    // every step her agent took in this turn, one quiet row each, with the time it took (what is
    // running is seen; a tool row is never hidden)
    if ((it.tools || []).length) { const n = depth() ? actsNode(it) : toolRows(it.tools); if (n) turn.append(n); }
    if (depth()) { const tf = thoughtFold(it); if (tf) turn.append(tf); }
    if (it.plan && it.plan.length) turn.append(h("ul", { class: "dock-plan" }, it.plan.map((p) => h("li", { class: p.status === "completed" ? "done" : "" },
      (p.status === "completed" ? "✓ " : "· ") + (p.content || "")))));
    const shaped = shapeTurn(it.parts, { done: it.done, now, shown: S.shown, key: S.conv + ":" + it.turn });
    it._shaped = shaped;
    const editing = S.editing === it.turn;
    const said = shaped.said.join("\n\n");
    const words = h("div", { class: "dock-letter" }, ...letter(h, said));
    if (editing) {
      const ed = h("p", { class: "dock-words" }, said);
      ed.contentEditable = "true";
      setTimeout(() => ed.focus(), 0);
      turn.append(ed, h("div", { class: "dock-quietfoot is-shown" },
        h("button", { class: "link-btn", type: "button", onclick: () => { const v = ed.textContent.trim(); S.editing = null; judge(it.turn, "corrected", null, v); send(v); } }, t("dock.send_correction")),
        h("button", { class: "link-btn", type: "button", onclick: () => { S.editing = null; render(); } }, t("dock.cancel"))));
    } else {
      if (said) turn.append(words);
      const sm = speakingMark(it);
      if (sm) turn.append(sm);
      if (live) { const p = depth() ? liveLine(it) : presenceLine(it); if (p) turn.append(p); }
    }
    if (!editing && it.done) {
      const foot = h("div", { class: "dock-quietfoot" },
        h("button", { class: "link-btn", type: "button", onclick: () => whereDidThatGo(it.turn) }, t("dock.where")),
        h("button", { class: "link-btn", type: "button", onclick: () => { try { navigator.clipboard.writeText(said); } catch { /* no clipboard */ } } }, t("dock.copy")),
        h("button", { class: "link-btn", type: "button", onclick: () => ctx.act("card", { title: firstWords(said), holder: st().actor }, {}, ctx.home,
          { confirmed: true, label: t("dock.put_in_deal_label") }) }, t("dock.put_in_deal")));
      if (a.discern_offered) {
        foot.append(h("button", { class: "link-btn", type: "button", onclick: () => { S.editing = it.turn; render(); } }, t("dock.correct")));
        const rate = h("span", { class: "dock-rate" }, h("span", { class: "dust" }, t("dock.rate")));
        for (let i = 1; i <= 10; i++) rate.append(h("button", { class: "link-btn", type: "button", "aria-label": t("dock.rate_n", { n: i }),
          onclick: () => judge(it.turn, "rated", i) }, String(i)));
        foot.append(rate);
      }
      turn.append(foot);
      if (S.rated.has(it.turn)) turn.append(h("p", { class: "dust" }, S.rated.get(it.turn)));
      turn.addEventListener("keydown", (e) => {
        if (!a.discern_offered || e.metaKey || e.ctrlKey || e.altKey) return;
        if (/^[0-9]$/.test(e.key)) { e.preventDefault(); e.stopPropagation(); judge(it.turn, "rated", e.key === "0" ? 10 : Number(e.key)); }
      });
    }
    // the margin, beneath the turn: what it did (kept ink), then what it put toward the record
    const col = h("div", { class: "dock-margincol" });
    const work = workLine(it);
    if (work) col.append(work);
    const margin = renderMargin(ctx, it.offers.map(offerItem), { onAgree: agree, onDecline: decline });
    if (margin) col.append(margin);
    row.append(turn);
    if (col.childNodes.length) row.append(col);
    return { row, recheck: shaped.recheck };
  }

  function toolRows(tools) {
    const ul = h("ul", { class: "dock-tools dust" });
    for (const x of tools) {
      const title = noPaths(String(x.title || "").split("\n")[0]).slice(0, 120) || t("dock.tool_untitled");
      const ms = actMs(x);
      const when = ms != null ? t("dock.tool_took", { s: ms < 10000 ? tenths(ms) : String(Math.round(ms / 1000)) })
        : /^(completed|failed)$/.test(String(x.status || "")) ? "" : t("dock.tool_running");
      ul.append(h("li", { class: "dock-tool" + (x.status === "failed" ? " is-failed" : "") }, title, when ? h("span", { class: "dock-tool-time figures" }, " · " + when) : null));
    }
    return ul;
  }

  // ---------------------------------------------------------------- the trust layer: what she is doing, seen
  /** a fold that keeps the person's choice across redraws (open at Full unless they closed it) */
  function fold(key, summary, body, openByDefault, cls = "") {
    const d = h("details", { class: "dock-act-fold" + (cls ? " " + cls : "") }, summary, body);
    d.open = S.folds.has(key) ? S.folds.get(key) : openByDefault;
    d.addEventListener("toggle", () => S.folds.set(key, d.open));
    return d;
  }
  /** the exact step of one act, in the monospace of the raw line: its title, its input, what came back */
  function exactStep(x) {
    const raw = [String(x.title || "")];
    if (x.input) raw.push(String(x.input));
    // a stand-in's output is not a result: nothing came back from a real step, so none is printed as one
    const standIn = !!((figures().f || {}).stand_in);
    for (const c of x.content || []) {
      if (standIn && c.type !== "diff") continue;
      if (c.type === "diff") raw.push([`${c.path || ""}`, ...String(c.old || "").split("\n").filter(Boolean).map((l) => "− " + l), ...String(c.new || "").split("\n").filter(Boolean).map((l) => "+ " + l)].join("\n"));
      else if (c.text) raw.push(String(c.text));
    }
    const pre = document.createElement("pre");
    pre.className = "dock-raw dock-act-raw";
    pre.textContent = raw.filter(Boolean).join("\n") || t("dock.trust.step_none");
    return pre;
  }
  /** her acts in one turn: Working, a folded row per run of like acts (verb, count, time) under ⎿;
      Plain, one quiet line once the turn is done; Full, every row open with its raw step */
  function actsNode(it) {
    const d = depth();
    const tools = it.tools || [];
    if (!tools.length) return null;
    if (d === "plain") {
      if (!it.done) return null;
      const line = plainActs(tools, t, ctx.fmt);
      const steps = h("div", { class: "dock-act-steps" }, ...tools.map((x) => exactStep(x)));
      return h("div", { class: "dock-acts dock-acts--plain dust" }, fold(`p:${it.turn}`, h("summary", { class: "dock-act-line" }, line), steps, false));
    }
    const ul = h("ul", { class: "dock-acts dust", "aria-label": t("dock.trust.step") });
    actGroups(tools, it.done).forEach((g, i) => {
      const words = actWords(g, t, ctx.fmt) + (g.cls === "worker" && g.tools[0].title ? ": " + noPaths(String(g.tools[0].title).split("\n")[0]).slice(0, 80) : "");
      const time = g.running ? t("dock.tool_running") : g.ms != null ? durWords(g.ms, t) : "";
      const summary = h("summary", { class: "dock-act-line" }, h("span", { class: "dock-act-hook", "aria-hidden": "true" }, "⎿"),
        h("span", { class: "dock-act-words" }, words), time ? h("span", { class: "dock-act-time figures" }, " · " + time) : null);
      const body = h("div", { class: "dock-act-steps" }, g.leaves ? h("p", { class: "dock-act-leaves" }, t("dock.trust.leaves")) : null, ...g.tools.map((x) => exactStep(x)));
      ul.append(h("li", { class: "dock-act" + (g.failed ? " is-failed" : "") + (g.leaves ? " is-leaving" : "") + (g.running ? " is-running" : "") },
        fold(`w:${it.turn}:${i}`, summary, body, d === "full")));
    });
    return ul;
  }
  /** when the turn began: her own line's time, else the moment this page sent it */
  function turnStart(turn) {
    const u = [...S.events].reverse().find((e) => e.kind === "user" && (turn == null || e.turn === turn));
    const at = u && Date.parse(u.ts || "");
    if (S.thinkingSince && (turn == null || !at || S.thinkingSince > at || (S.clock && turn === S.clock.turn))) return S.thinkingSince;
    return at && !Number.isNaN(at) ? at : S.thinkingSince || Date.now();
  }
  /** the live line's words: what she is doing now (the running act, her words arriving, or thinking) and the clock */
  /** the turn's asks of hers: whether the newest event is one still open, and the time she spent answering the closed ones */
  function askWait(turn) {
    const evs = S.events.filter((e) => turn == null || e.turn === turn || e.kind === "answered");
    const done = new Map(S.events.filter((e) => e.kind === "answered").map((e) => [e.ask, e.seen || Date.parse(e.ts || "")]));
    let waited = 0;
    for (const e of evs) if (e.kind === "ask" && e.ask && done.has(e.ask.id)) { const a = e.seen || Date.parse(e.ts || ""), b = done.get(e.ask.id); if (a && b && b > a) waited += b - a; }
    const own = evs.filter((e) => e.kind !== "answered");
    const last = own[own.length - 1];
    return { open: !!(last && last.kind === "ask" && last.ask && !done.has(last.ask.id)), waited };
  }
  function liveText(it, t0) {
    const d = depth();
    // an open ask of hers is her own waiting, never counted against her agent: no clock until she answers
    const w = askWait(it ? it.turn : null);
    if (w.open) return t("dock.status.waiting_for_you");
    // the turn's clock counts whole seconds from the first ("Thinking · 1 s", "2 s"...); the tenths are an act's own time, never this
    const time = durWords(Math.max(1000, Date.now() - t0 - w.waited), t);
    const running = it ? [...(it.tools || [])].reverse().find((x) => !/^(completed|failed)$/.test(String(x.status || ""))) : null;
    // her words are arriving: the newest part is words, and a piece of them came within the last breath
    const lastPart = it && it.parts && it.parts[it.parts.length - 1];
    const lastChunk = lastPart && lastPart.chunks ? lastPart.chunks[lastPart.chunks.length - 1] : null;
    const speaking = !running && !!(lastChunk && performance.now() - (lastChunk.at || 0) < 1500);
    if (d === "plain" && (running || speaking)) return "";
    let line = running ? t("dock.trust.live.doing", { doing: t("dock.trust.now." + actClass(running)), time })
      : speaking ? t("dock.trust.live.doing", { doing: t("dock.trust.now.words"), time }) : t("dock.trust.live.thinking", { time });
    if (d === "full") { const f = figures().f; if (f && f.context_tokens != null) line += " · " + t("dock.trust.live.held", { n: countWords(f.context_tokens) }); }
    return line;
  }
  /** the live line while a turn runs (the trust layer: it shows what the body is doing at all times): dim, its seconds counting, any thought summary beneath in dust; never a spinner */
  function liveLine(it) {
    const t0 = turnStart(it ? it.turn : null);
    const text = liveText(it, t0);
    if (!text) { S.live = null; return null; }
    const p = h("p", { class: "dock-live dust", role: "status" }, text);
    S.live = { el: p, it, t0 };
    const thought = it && it.thoughtText ? String(it.thoughtText).trim() : "";
    if (!thought || (it && it.text)) return p;
    return h("div", { class: "dock-live-wrap" }, p, h("p", { class: "dock-thought dust" }, thought.length > 240 ? "…" + thought.slice(-240) : thought));
  }
  /** once her words begin, the thought folds to "thought for 12 s", one tap to read (the trust layer) */
  function thoughtFold(it) {
    const d = depth();
    const thought = it && it.thoughtText ? String(it.thoughtText).trim() : "";
    if (!thought || !it.text || d === "plain") return null;
    const u = [...S.events].find((e) => e.kind === "user" && e.turn === it.turn);
    const ms = u && it.thoughtEnd ? Date.parse(it.thoughtEnd) - Date.parse(u.ts) : null;
    const secs = ms != null && !Number.isNaN(ms) ? Math.max(1, Math.round(ms / 1000)) : null;
    const label = secs != null ? t("dock.status.thought", { seconds: secs }) : t("dock.trust.act.think_one");
    return fold(`th:${it.turn}`, h("summary", { class: "dock-act-line dust" }, label), h("p", { class: "dock-thought dust" }, thought), d === "full", "dock-thought-fold");
  }
  /** a turn's end, a notice, a worker finished: lines in the stream at the depth chosen */
  function trustItem(it, items) {
    const d = depth();
    if (it.who === "notice") {
      const words = it.words || "";
      if (!words) return null;
      return h("div", { class: "dock-row" }, h("article", { class: "dock-turn dock-turn--agent dock-turn--notice" }, h("p", { class: "dock-words" }, words)));
    }
    if (it.who === "finished") {
      if (d === "plain") return null;
      // a worker stopped says it stopped, never that it finished: the host's end state, live and replayed alike
      const stopped = it.stopped || (S.stoppedHere && S.stoppedHere.has(it.agent));
      return h("p", { class: "dock-end dock-finished dust" }, t(stopped ? "dock.trust.worker.stopped" : "dock.trust.worker.finished", { name: it.name, time: durWords(it.ms, t) || "" }).replace(/\s·\s$/, ""));
    }
    // the end line: "Worked for 2 m 36 s · done 3:12 PM" (Working), with tokens and cost (Full); at Plain only what left
    const e = it.data || {};
    const left = e.left_computer === true && e.left_known !== false;
    const parts = [];
    if (d !== "plain") {
      const dur = durWords(e.duration_ms, t);
      const doneAt = e.done_at || e.ts;
      const time = doneAt ? ctx.fmt.time(doneAt) : "";
      if (dur && time) parts.push(t("dock.status.turn_end", { duration: dur, time }));
      const running = [...workerRows().values()].filter((w) => !workerEnded(w)).length;
      const isLast = ![...items].reverse().find((x) => x.who === "end" && x !== it && x.turn > it.turn);
      if (running && isLast) parts.push(running === 1 ? t("dock.trust.end.workers_one") : t("dock.status.workers_running", { n: ctx.fmt.number(running, true) }));
      if (d === "full") {
        if (e.tokens_in != null || e.tokens_out != null) parts.push(t("dock.trust.end.io", { in: countWords(e.tokens_in) || "0", out: countWords(e.tokens_out) || "0" }));
        if (e.cost != null) parts.push(t("dock.trust.end.cost", { usd: usdWords(e.cost) }));
      }
    }
    if (!parts.length && !left) return null;
    const p = h("p", { class: "dock-end dust" }, parts.join(" · "));
    if (left) p.append(parts.length ? " · " : "", h("button", { class: "link-btn dock-end-left", type: "button", onclick: () => whereDidThatGo(it.turn) }, t("dock.trust.end.left")));
    return p;
  }
  /** the figures as the host last gave them: the newest `figures` or `state` event, else /status's */
  function figures() {
    const m = model().fig;
    if (m && m.f) return m;
    const a = me();
    return { f: (a && a.figures) || null, ts: null };
  }
  /** her workers: the host's rows (the newest `workers` event over /status's), by agent id */
  function workerRows() {
    const rows = new Map();
    const a0 = me();
    for (const a of agents()) {
      if (!a || !a.body || !a.worker || (a0 && a.body.of_agent && a.body.of_agent !== a0.id)) continue;
      rows.set(a.id, { ...a.worker, agent: a.id, name: a.name || a.id, conversation: a.conversation || null, seen: 0 });
    }
    for (const [id, w] of model().workers) rows.set(id, { ...(rows.get(id) || {}), ...w });
    return rows;
  }
  const taskKey = (x) => String(x || "").toLowerCase().replace(/\s+/g, " ").trim().slice(0, 120);
  function hostWorkersRunning() { return [...workerRows().values()].filter((w) => w.state && !workerEnded(w)); }
  /** a worker's end, by the host's state: done, or stopped (the host's `stopped` state or flag) */
  function workerEnded(w) { return !!w && (w.state === "done" || w.state === "stopped" || w.state === "cancelled"); }
  /** stopped, not finished: the host's word when it gives one; else this device's own record of the person's Stop
      (kept across a reload, by the worker and its start), so the replay says what the live line said */
  const STOP_KEY = "hud.worker_stopped";
  const stopKey = (w) => String(w.agent || "") + "|" + String(Date.parse(w.started || "") || w.started || "");
  function stopStore() { try { return JSON.parse(localStorage.getItem(STOP_KEY) || "{}") || {}; } catch { return {}; } }
  function workerStopped(w) {
    if (!w) return false;
    if (w.state === "stopped" || w.state === "cancelled" || w.stopped === true || w.end === "stopped" || w.stop === "cancelled") return true;
    if (w.state === "done" && (w.stopped === false || w.end === "done")) return false;
    return !!stopStore()[stopKey(w)];
  }
  /** the person stopped this worker: its clock frozen at once, its line to say it stopped, live and after a reload */
  function markStopped(w, ms) {
    if (!w || !w.agent) return;
    (S.stoppedHere = S.stoppedHere || new Set()).add(w.agent);
    (S.stoppingAt = S.stoppingAt || new Map()).set(w.agent, ms);
    try { const m = stopStore(); m[stopKey(w)] = Date.now(); const k = Object.keys(m); if (k.length > 200) delete m[k[0]]; localStorage.setItem(STOP_KEY, JSON.stringify(m)); } catch { /* storage closed */ }
  }
  /** the workers at work, as rows beneath the stream (§2.4): name, what it is on, its time running, its
      tokens at Full, and Stop; folded away when none. A worker the page knows from the machine (opts.workers) too. */
  function renderWorkers() {
    if (!$.workers) return;
    $.workers.textContent = "";
    const d = depth();
    if (!d) { $.workers.hidden = true; return; }
    const rows = hostWorkersRunning().map((w) => ({ name: w.name, task: w.task, started: Date.parse(w.started || "") || (w.elapsed_ms != null ? (w.seen ? Date.now() - (performance.now() - w.seen) : Date.now()) - w.elapsed_ms : null),
      agent: w.agent, tokens: w.tokens, state: w.state, startedAt: w.started, conversation: w.conversation || ((agents().find((a) => a.id === w.agent) || {}).conversation) || null }));
    let extra = [];
    try { extra = opts.workers ? opts.workers() || [] : []; } catch { extra = []; }
    for (const x of extra) if (x && x.name && !rows.some((r) => r.name === x.name)) rows.push({ name: x.name, task: x.task, started: Date.parse(x.started || "") || null, state: "working" });
    // a row is drawn only once the worker started (the host's stamp, after her "start it"): a worker still
    // only proposed (an open ask of kind `worker` for its task, no start) is her chief's words, never a row;
    // a started worker is always its row, even beside an older open ask for the same task
    const asked = new Set([...model().asks.values()].filter((x) => x && x.open && x.kind === "worker").map((x) => taskKey(x.task)).filter(Boolean));
    for (let i = rows.length - 1; i >= 0; i--) if (!rows[i].started && !rows[i].state && asked.has(taskKey(rows[i].task))) rows.splice(i, 1);
    $.workers.hidden = !rows.length;
    if (!rows.length) return;
    S.workerClocks = [];
    for (const w of rows) {
      const task = String(w.task || "").split("\n").map((x) => x.replace(/^#+\s*/, "").trim()).find(Boolean) || "";
      const clock = h("span", { class: "dock-worker-time figures" });
      const bits = [h("span", { class: "dock-worker-name" }, w.name)];
      if (task) bits.push(h("span", { class: "dock-worker-task" }, " · " + noPaths(task).slice(0, 80)));
      if (w.state === "waiting") bits.push(h("span", { class: "dock-worker-state" }, " · " + t("dock.trust.worker.waiting")));
      const frozen = S.stoppingAt && w.agent ? S.stoppingAt.get(w.agent) : null;
      if (d !== "plain" && frozen != null) { bits.push(clock); clock.textContent = " · " + durWords(frozen, t); }
      else if (d !== "plain" && w.started) { bits.push(clock); S.workerClocks.push({ el: clock, t0: w.started }); clock.textContent = " · " + durWords(Date.now() - w.started, t); }
      if (d === "full" && w.tokens != null) bits.push(h("span", { class: "figures" }, " · " + countWords(w.tokens)));
      const stop = w.conversation && frozen == null ? h("button", { class: "link-btn dock-worker-stop", type: "button", "aria-label": t("dock.trust.worker.stop_label", { name: w.name }),
        onclick: async () => {
          // its clock stops at once, and its line will say it stopped (here and after a reload)
          markStopped({ agent: w.agent, started: w.startedAt }, w.started ? Date.now() - w.started : null);
          S.workerClocks = (S.workerClocks || []).filter((c) => c.el !== clock);
          renderWorkers();
          await A.stop(w.conversation); render();
        } }, t("dock.trust.worker.stop")) : null;
      $.workers.append(h("li", { class: "dock-worker dust" }, h("span", { class: "dock-worker-line" }, ...bits), stop));
    }
  }
  /** the mode by the harness's own name (Manual, Accept edits, Plan, Auto), never renamed; its plain words only when it gave no name */
  function modeWord(a, f) {
    const id = (f && f.mode) || (a && a.mode) || null;
    if (!id) return "";
    const row = ((a && a.modes) || []).find((m) => m.id === id);
    if (row && row.name) return row.name;
    // the harness's name only, from the first paint: ask /agent/mode once for the names, and say nothing until they come
    const known = S.modeNames && S.modeNames[id];
    if (known) return known;
    if (a && A.modes && !S.modeAsked) {
      S.modeAsked = true;
      A.modes(a.id).then((r) => {
        const list = r && r.ok && r.out && Array.isArray(r.out.modes) ? r.out.modes : [];
        S.modeNames = Object.fromEntries(list.filter((m) => m && m.id && m.name).map((m) => [m.id, m.name]));
        if (Object.keys(S.modeNames).length) { S.statusKey = null; renderStatus(); }
      }).catch(() => {});
    }
    return "";
  }
  /** a mode's plain words, beside its name: the host's `plain` when it is words, else the Talk's words for the harness's id, else its description */
  function modePlain(m) {
    const p = typeof m.plain === "string" && /\s/.test(m.plain) ? m.plain : "";
    return p || m.words || m.description || "";
  }
  /** the one status line at the foot (by depth): one tap opens every figure; the mode's word opens the modes */
  function renderStatus() {
    let slot = null;
    try { slot = opts.statusSlot ? opts.statusSlot() : null; } catch { slot = null; }
    const d = depth();
    if (!slot) return;
    if (!d) { slot.hidden = true; return; }
    slot.dataset.depth = d;
    const a = me();
    let { f } = figures();
    // the window changed mid-turn (a 200k then a 1M window): the percent keeps the turn's first window until the turn ends
    const size = f && num(f.context_tokens) != null && num(f.context_used_pct) > 0 ? Math.round(f.context_tokens * 100 / f.context_used_pct) : null;
    if (busy() && size) {
      if (!S.ctxHold) S.ctxHold = { size, pct: f.context_used_pct };
      else if (Math.abs(size - S.ctxHold.size) / S.ctxHold.size > 0.2) f = { ...f, context_used_pct: S.ctxHold.pct };
      else S.ctxHold.pct = f.context_used_pct;
    } else if (!busy()) S.ctxHold = null;
    const mw = modeWord(a, f);
    const { parts, sep } = statusParts(f || {}, d, { t, name: (a && a.name) || "", modeWord: mw });
    const key = d + "|" + parts.map((x) => x.text).join(sep);
    if (S.statusKey === key && slot.firstChild) { slot.hidden = !parts.length; return; }
    S.statusKey = key;
    slot.textContent = "";
    slot.hidden = !parts.length;
    if (!parts.length) return;
    const mode = parts.find((x) => x.mode);
    const modeIdx = parts.indexOf(mode);
    const lead = parts.slice(0, modeIdx < 0 ? parts.length : modeIdx);
    // each segment is one unbreakable unit carrying the separator after it, so the line wraps only between segments
    // and a wrapped line never starts or ends on a lone separator
    const segs = lead.map((x, i) => [h("span", { class: "talk-status-seg" }, x.text + (i < lead.length - 1 || mode ? sep.trimEnd() : "")), i < lead.length - 1 ? " " : null]).flat().filter(Boolean);
    // at Plain the line is words only and opens nothing (the table of figures belongs to Working and Full)
    if (d === "plain") slot.append(h("span", { class: "talk-status-line" }, ...segs));
    // an inline span, not a button (a button is an atomic box, so the mode's word fell to a line of its own)
    else if (segs.length) slot.append(h("span", { class: "talk-status-line figures", role: "button", tabindex: "0", "aria-label": t("dock.trust.status.open"), onclick: openStatus,
      onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openStatus(); } } }, ...segs));
    if (mode) slot.append(segs.length ? " " : "", h("button", { class: "talk-status-mode talk-status-seg", type: "button", "aria-label": t("dock.trust.status.mode"), onclick: openHarnessModes }, mode.text));
  }
  /** the knob: "How much you see: Plain · Working · Full", kept on this device */
  function depthKnob(close) {
    const d = depth();
    if (!d || !opts.setDepth) return [];
    const row = h("div", { class: "actions dock-depth", role: "radiogroup", "aria-label": t("dock.depth.title") });
    for (const v of DEPTHS) row.append(h("button", { class: "pill" + (v === d ? " primary" : " quiet"), type: "button", role: "radio", "aria-checked": String(v === d), dataset: { depth: v },
      onclick: () => { opts.setDepth(v); if (close) close(); render(); } }, t("dock.depth." + v)));
    return [h("p", { class: "eyebrow" }, t("dock.depth.title")), row];
  }
  /** the status sheet: every figure the host gave and its as-of; at Full, everything the harness gave, raw */
  function openStatus() {
    const a = me();
    const { f, ts } = figures();
    const body = h("div", { class: "dock-status-sheet" });
    const shown = Object.entries(f || {}).filter(([, v]) => v != null && v !== "");
    if (!shown.length) body.append(h("p", { class: "dust" }, t("dock.trust.sheet.none")));
    else {
      const dl = h("dl", { class: "dock-figures" });
      for (const [k, v] of shown) {
        let val = v;
        if (k === "model") val = modelWords(v) + (modelWords(v) !== v ? " (" + v + ")" : "");
        else if (k === "effort") { const w = t("dock.status.effort." + v); val = w && !/^\[/.test(w) && v !== "default" ? w : v; }
        else if (k === "mode") val = (modeWord(a, f) || v) + " (" + v + ")";
        else if (/_pct$/.test(k)) val = Math.round(v * 10) / 10 + "%";
        else if (/_resets$/.test(k)) val = resetWords(v) || v;
        else if (/^cost_/.test(k)) val = "$" + usdWords(v);
        else if (k === "cache" && typeof v === "object") val = t("dock.trust.sheet.cache", { read: countWords(v.read) || "0", write: countWords(v.write) || "0", pct: v.read_pct != null ? Math.round(v.read_pct) : "0" });
        else if (k === "stand_in") val = t("dock.status.stand_in");
        else if (k === "version") val = String(v).split(/\s+/).pop().replace(/^v/, "").split(".").slice(0, 2).join(".");
        else if (typeof v === "number") val = v.toLocaleString("en-US");
        else if (typeof v === "object") val = JSON.stringify(v);
        dl.append(h("dt", null, t("dock.trust.sheet.k." + k)), h("dd", { class: "figures" }, String(val)));
      }
      body.append(dl);
    }
    if (ts) body.append(h("p", { class: "dust" }, t("dock.trust.sheet.as_of", { time: ctx.fmt.time(ts) || ts })));
    body.append(...depthKnob(() => close()));
    if (a && (a.modes || []).length) body.append(h("p", { class: "dock-ways" }, h("button", { class: "link-btn", type: "button", onclick: () => { close(); openHarnessModes(); } }, t("dock.trust.status.mode"))));
    // everything the harness gave, raw, one fold away (open at Full)
    const pre = document.createElement("pre"); pre.className = "dock-raw dock-figures-raw";
    const raw = fold("status-raw", h("summary", { class: "dust" }, t("dock.trust.sheet.raw")), pre, depth() === "full");
    body.append(raw);
    pre.textContent = JSON.stringify(f || {}, null, 2);
    if (a && A.figures) A.figures(a.id).then((r) => { if (r && r.ok && r.out) pre.textContent = JSON.stringify(r.out, null, 2); }).catch(() => {});
    const close = ctx.openSheet({ title: t("dock.trust.sheet.title"), body });
  }
  /** the harness's own modes, in words (permissions are the harness's own); a mode that asks about nothing is not offered here */
  async function openHarnessModes() {
    const a = me();
    if (!a) return;
    const list = h("ul", { class: "menu-list", role: "menu" });
    const body = h("div", null, list, h("p", { class: "dust" }, t("dock.mode.outward_always")), h("p", { class: "dust dock-modes-fixed" }, t("dock.trust.modes.fixed")));
    const close = ctx.openSheet({ title: t("dock.trust.modes.title"), body });
    let all = a.modes || [];
    let current = (figures().f || {}).mode || a.mode;
    if (A.modes) { const r = await A.modes(a.id).catch(() => null); if (r && r.ok && r.out && Array.isArray(r.out.modes)) { all = r.out.modes; current = r.out.current || current; } }
    const modes = all.filter((m) => m.face !== false);
    // a mode the host holds back from the face is named at the foot, by the harness's own name, never hidden silently
    const held = all.filter((m) => m && m.face === false).map((m) => m.name || m.id).filter(Boolean);
    if (held.length) body.append(h("p", { class: "dust dock-modes-held" }, held.length === 1 ? t("dock.trust.modes.held", { name: held[0] }) : t("dock.trust.modes.held_n", { names: held.join(", ") })));
    if (!modes.length) { list.replaceWith(h("p", { class: "dust" }, t("dock.trust.modes.none"))); return; }
    for (const m of modes) {
      const name = m.name || m.id, plain = modePlain(m);
      list.append(h("li", null, h("button", { role: "menuitemradio", type: "button", "aria-checked": String(current === m.id), dataset: { mode: m.id },
        onclick: async () => { close(); await A.mode(a.id, m.id); S.statusKey = ""; render(); } },
        h("span", { class: "dock-mode-name" }, name), plain && plain !== name ? h("span", { class: "dust dock-mode-plain" }, " · " + plain) : null)));
    }
  }

  function firstWords(text) { const w = String(text || "").split(/\s+/).slice(0, 12).join(" "); return w.length < String(text || "").length ? w + "…" : w; }

  function renderTerminal() {
    // the same stream, raw: every event as one plain line, tool input and output included
    $.turns.textContent = "";
    const pre = document.createElement("pre");
    pre.className = "dock-terminal";
    const out = [];
    let cur = null;
    for (const e of S.events) {
      if (e.kind === "agent") { if (cur !== "agent") out.push(`${String(e.ts || "").slice(11, 19)} < `); out[out.length - 1] += e.text || ""; cur = "agent"; continue; }
      cur = e.kind;
      const tm = String(e.ts || "").slice(11, 19);
      if (e.kind === "user") out.push(`${tm} > ${e.text}`);
      else if (e.kind === "tool" || e.kind === "tool_update") out.push(`${tm} [${(e.tool || {}).kind || "tool"}] ${(e.tool || {}).title || ""} ${(e.tool || {}).status || ""}${(e.tool || {}).input ? "\n    " + e.tool.input : ""}${((e.tool || {}).content || []).map((c) => "\n    " + (c.text || ((c.old || "") + " → " + (c.new || "")))).join("")}`);
      else if (e.kind === "ask") out.push(`${tm} [ask] ${e.ask.title} · ${e.ask.leaves ? "leaves the computer" : "stays on the computer"}${e.ask.input ? "\n    " + e.ask.input : ""}`);
      else if (e.kind === "answered") out.push(`${tm} [answer] ${e.answer}`);
      else if (e.kind === "offer") out.push(`${tm} [offer ${e.offer.kind}] ${e.offer.text}`);
      else if (e.kind === "plan") out.push(`${tm} [plan] ${(e.entries || []).map((x) => x.content).join(" · ")}`);
      else if (e.kind === "turn_end") out.push(`${tm} [end of turn ${e.turn}]`);
      else if (e.kind === "state") out.push(`${tm} [${e.state}]`);
      else out.push(`${tm} [${e.kind}]`);
    }
    pre.textContent = out.join("\n");
    $.turns.append(h("p", { class: "dust" }, t("dock.terminal_same")), pre);
    if (isOpen()) requestAnimationFrame(() => { $.scroll.scrollTop = $.scroll.scrollHeight; });
  }

  function renderLine() {
    $.turns.textContent = "";
    $.notices.textContent = ""; $.asks.textContent = ""; $.about.textContent = ""; $.state.textContent = "";
    $.line.textContent = "";
    const pre = document.createElement("pre");
    pre.className = "dock-terminal dock-pty";
    pre.textContent = S.ptyText || t("dock.line_starting");
    const input = h("input", { class: "dock-ptyinput", "aria-label": t("dock.line_input"), autocomplete: "off", spellcheck: "false" });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); if (S.pty) A.ptyWrite(S.pty, input.value + "\r"); input.value = ""; }
    });
    $.line.append(
      h("p", { class: "dock-linesaid" }, t("dock.line_second")),
      pre,
      h("div", { class: "dock-inputrow" }, input,
        h("button", { class: "pill quiet", type: "button", onclick: () => S.pty && A.ptyWrite(S.pty, "\x03") }, t("dock.line_interrupt")),
        h("button", { class: "pill quiet", type: "button", onclick: closeCommandLine }, t("dock.line_close"))));
    requestAnimationFrame(() => { pre.scrollTop = pre.scrollHeight; });
    $.stop.hidden = true;
  }

  function renderNotices(a) {
    $.notices.textContent = "";
    if (!a) return;
    if (ON_PHONE && ctx.offline) { $.notices.append(h("p", { class: "dock-notice" }, t("dock.computer_asleep"))); return; }
    if (S.refusal) $.notices.append(h("p", { class: "dock-notice" }, S.refusal));
    if (a.state === "offline") $.notices.append(h("p", { class: "dock-notice" }, t("dock.offline")));
    if (a.state === "away") $.notices.append(h("p", { class: "dock-notice" }, t("dock.away")));
    if ((a.asks_15m != null ? a.asks_15m : a.asks_last_15m) >= 4) {
      $.notices.append(h("p", { class: "dock-notice dust" }, t("dock.over_asking"), " ",
        h("button", { class: "link-btn", type: "button", onclick: openModes }, t("dock.fewer_questions_q"))));
    }
  }

  /** An ask in its place in the stream (opts.asksInStream): open, its card; answered, one quiet line
      that says what was asked and the answer, so an answer never takes anything away. */
  /** a worker's end, as her one line: "Vega has finished: …", and "Read it" opens the draft here, as
      plain lines, folded under her line; a draft not carried opens where the host says, as a last resort */
  function doneTurn(it) {
    const name = String(it.name || "").trim();
    const first = String(it.line || "").replace(/^#+\s*/, "").replace(/\*\*|__|`/g, "").trim().replace(/[.]+$/, "");
    const words = name && first ? t("dock.done.line", { name, line: first + "." }) : t("dock.done.line_plain", { name: name || t("talk_place.ask_from_unnamed") });
    const turn = h("article", { class: "dock-turn dock-turn--agent dock-done" }, h("p", { class: "talk-her-line" }, words));
    const fill = (text) => { draft.textContent = ""; for (const para of plainLines(text).split(/\n{2,}/)) if (para.trim()) draft.append(h("p", null, para.replace(/\n/g, " "))); };
    const draft = h("div", { class: "dock-draft", hidden: "" });
    if (it.draft) fill(it.draft);
    if (it.draft || it.handoff) {
      const said = h("p", { class: "dust", role: "status" });
      const btn = h("button", { class: "pill quiet dock-done-read", type: "button", "aria-expanded": "false", onclick: async () => {
        const open = draft.hidden;
        if (open && !draft.childNodes.length && it.handoff) {
          btn.disabled = true;
          const r = await handoffText(it.handoff);
          btn.disabled = false;
          if (!r || !r.ok) { said.textContent = (r && r.why) || t("dock.answer_failed"); return; }
          fill(r.text); S.drafts.set(it.handoff, r.text);
        }
        draft.hidden = !open; btn.setAttribute("aria-expanded", String(open));
        btn.textContent = open ? t("dock.done.close") : t("dock.done.read");
        if (open) { S.pin = false; requestAnimationFrame(() => turn.scrollIntoView({ block: "start" })); }
      } }, t("dock.done.read"));
      if (!it.draft && it.handoff && S.drafts.has(it.handoff)) fill(S.drafts.get(it.handoff));
      turn.append(h("div", { class: "talk-chips" }, btn), said, draft);
    } else if (it.go && typeof it.go === "string" && it.go.startsWith("#/")) {
      turn.append(h("div", { class: "talk-chips" }, h("button", { class: "pill quiet", type: "button", onclick: () => ctx.go(it.go) }, t("dock.done.read"))));
    }
    return h("div", { class: "dock-row" }, turn);
  }

  /** the exact step an ask is about, as the machine has it: the command, the file and what is written,
      the change; paths by their last name below Full. Empty when the ask carries no step. */
  function askStep(ask, full) {
    const out = [];
    const cut = (x) => { const l = String(x || "").split("\n"); const s = l.slice(0, 12).join("\n"); return (s.length > 900 ? s.slice(0, 900) : s) + (s.length > 900 || l.length > 12 ? "\n…" : ""); };
    const p = (x) => (full ? String(x) : noPaths(x));
    let v = null;
    try { v = ask.input ? JSON.parse(ask.input) : null; } catch { v = null; }
    if (v && typeof v === "object") {
      if (typeof v.command === "string" && v.command.trim()) out.push(p(v.command.trim()));
      const file = v.file_path || v.path || v.notebook_path;
      if (typeof file === "string" && file) out.push(p(file));
      for (const k of ["content", "new_string", "text", "message", "body", "url"]) if (typeof v[k] === "string" && v[k].trim()) { out.push(cut(p(v[k].trim()))); break; }
    } else if (typeof ask.input === "string" && ask.input.trim()) out.push(cut(p(ask.input.trim())));
    for (const c of ask.content || []) {
      if (c && c.type === "diff") {
        const lines = [];
        if (c.path && !out.length) lines.push(p(c.path));
        for (const l of String(c.old || "").split("\n")) if (l) lines.push("− " + l);
        for (const l of String(c.new || "").split("\n")) if (l) lines.push("+ " + l);
        if (lines.length) out.push(cut(lines.join("\n")));
      }
    }
    if (!out.length && ask.step != null) { const s = typeof ask.step === "string" ? ask.step : (ask.step && (ask.step.sentence || ask.step.text)) || ""; if (s.trim()) out.push(p(s.trim())); }
    if (!out.length && ask.title) out.push(p(String(ask.title)));
    return out.join("\n").replace(/^\s*```[\w-]*\s*$/gm, "").replace(/\n{3,}/g, "\n\n").trim();
  }

  function askTurn(id, prev) {
    const ask = model().asks.get(id);
    if (!ask) return null;
    // the Talk draws no cards: an open ask is her line, answered by the
    // person's next words (yes, no, keep it, not now, start it); the page reads them first
    // answered, it stays as she said it, and her answer is drawn once, as her own words by the page (never "· yes" again here)
    if (opts.askWords) {
      // drawn once (panel 4, l): when her own letter just above already asks it (it ends on a question),
      // her letter is the line and this row carries only the step beneath; else her line is the ask's words
      const prevText = prev && prev.who === "agent" ? String(prev.text || "").trim() : "";
      const saidAbove = !!prevText && /\?["'”’)]*$/.test(prevText);
      const d = depth();
      const raw = ask.kind === "worker" || ask.kind === "act" || ask.kind === "keep" ? "" : askStep(ask, d === "full");
      const step = !raw ? null : d === "working" || d === "full"
        ? h("pre", { class: "dock-raw dock-ask-step" }, raw)
        : h("details", { class: "dock-fold dock-ask-step" }, h("summary", { class: "dust" }, t("dock.ask_exactly")), h("pre", { class: "dock-raw" }, raw));
      return h("div", { class: "dock-row" }, h("article", { class: "dock-turn dock-turn--agent talk-turn dock-ask-words" + (ask.open ? "" : " is-answered") + (saidAbove ? " is-said-above" : ""), dataset: { ask: ask.id } },
        saidAbove ? null : h("p", { class: "talk-her-line" }, askWords(ctx, ask)),
        step,
        ask.open && ask.untrusted ? h("p", { class: "dust" }, t("dock.from_something_read_line")) : null,
        ask.open && ask.leaves ? h("p", { class: "dust" }, t("dock.leaves_computer")) : null));
    }
    if (ask.open) return h("div", { class: "dock-row dock-row--ask" }, renderAsk(ctx, ask, { onAnswer: (ans) => answer(ask, ans) }));
    const q = typeof ask.question === "string" && ask.question.trim() ? String(ask.question) : ask.kind === "worker" ? t("dock.ask_q.worker", { task: String(ask.task || "").trim() })
      : ask.kind === "act" ? t("dock.ask_q.act", { option: String(ask.option || "").trim() }) : askQuestion(ctx, ask);
    const said = t("dock.ask_answer." + (ask.answer || "lapsed"));
    return h("p", { class: "dock-ask-done dust" }, q + " · " + (said.startsWith("[") ? t("dock.ask_answer.lapsed") : said));
  }

  function renderAsks(a) {
    $.asks.textContent = "";
    if (!a || opts.asksInStream) return;
    const { asks } = model();
    for (const ask of asks.values()) if (ask.open) $.asks.append(renderAsk(ctx, ask, { onAnswer: (ans) => answer(ask, ans) }));
  }

  function renderAbout() {
    const s = st();
    const sel = ctx.selected && ctx.read.card(s, ctx.selected);
    $.about.textContent = "";
    if (sel && S.aboutCleared !== sel.id) {
      S.about = { id: sel.id, title: sel.title };
      $.about.append(t("dock.about_line", { title: sel.title }), " ",
        h("button", { class: "link-btn", type: "button", "aria-label": t("dock.about_clear"), onclick: () => { S.aboutCleared = sel.id; S.about = null; render(); } }, "×"));
    } else S.about = null;
  }

  function renderState() {
    const a = me();
    $.state.textContent = a && a.state === "waking" ? t("dock.waking") : "";
  }

  const self = {
    inline: INLINE,
    connected() { return !!(el && el.isConnected); },
    settings(close) { return settingsNodes(close); },
    mount(e, c) {
      el = e; ctx = c; LIVE.add(self); build(); chooseConversation(); render(); voiceWay().then(() => render());
      // the service her words go to, by the name the person's vendors file gives it (/agent/list's dock.vendor)
      if (store.source === "server" && A.list) A.list().then((r) => { const v = r && r.ok && r.out && r.out.dock && r.out.dock.vendor; if (typeof v === "string" && v.trim()) S.vendor = v.trim(); }).catch(() => {});
    },
    update(c) {
      const wasOffline = ctx && ctx.offline;
      ctx = c;
      chooseConversation();
      if (ON_PHONE && wasOffline && !ctx.offline && S.outbox.some((o) => o.waiting)) {
        const q = S.outbox.filter((o) => o.waiting); S.outbox = S.outbox.filter((o) => !o.waiting);
        (async () => { for (const o of q) await send(o.text); })();
      }
      render();
    },
    unmount() {
      LIVE.delete(self);
      if (V.loop.on) endLoop(true);
      stopSpeaking(true);
      if (V.rec) stopListening({ discard: true });
      if (S.stream) S.stream.close();
      if (S.ptyStream) S.ptyStream.close();
      clearInterval(S.tick);
      if (S.onWords) window.removeEventListener("lionsberg:dock-words", S.onWords);
    },
    /** the room's switch: "ice" (Words) · "terminal" (Plain) · "line" (the command line) */
    setView(v) {
      if (v === S.view) return;
      if (S.view === "line" && v !== "line") { closeCommandLine(); if (v === "ice") return; }
      if (v === "line") { openCommandLine(); return; }
      S.view = v === "terminal" ? "terminal" : "ice";
      render();
    },
    get view() { return S.view; },
    /** the sheet behind her name, and Stop: for a page that holds the conversation inline (the Talk) */
    about() { openAbout(); },
    /** the open asks of her conversation, oldest first (the Talk answers the newest by the person's words) */
    openAsks() { return [...model().asks.values()].filter((x) => x.open); },
    /** an ask answered by words: yes (a mark written, a worker started first, as the card's Yes does) or no */
    async answerAsk(ask, yes) {
      if (!ask) return { ok: false };
      if (yes && ask.kind === "act") {
        // the page that shows the card settles it as her tap would: the Deal's act, with its Undo in
        // sight for the record's whole undo window; only a page that cannot writes it here, Undo by the toast
        let settled = null;
        if (typeof ctx.settleCard === "function") {
          try { settled = ctx.settleCard({ card: ask.card_id || ask.card, option: ask.option, index: ask.option_index }); } catch { settled = null; }
        }
        if (!(settled && settled.ok)) { const r = actYes(ctx, ask); if (!r.ok) return r; }
        else { const r = await A.answer(S.conv, ask.id, "yes"); return { ok: r.ok, reason: r.out && r.out.refused }; }
      }
      if (yes && ask.kind === "worker") { const r = await workerYes(ctx, ask); if (!r.ok) return r; }
      return answer(ask, yes ? "yes" : "not_this");
    },
    /** the page moved the stream itself (a turn of its own at the end): her held line is let go */
    unpin() { S.pin = false; },
    stop() { stopAll(); },
    get busy() { return busy(); },
    /** her one name, as every head says it (the host's, else the agents file's), or null */
    get name() { const a = me(); return (a && a.name) || null; },
    /** the input row: the line to speak (the Talk reads it before the dock sends it) */
    get input() { return $.input || null; },
    key(e, c) {
      ctx = c;
      if (e.key === "t" || e.key === "T") { open(true); return true; }
      if (e.key === "Escape" && isOpen()) {
        const a = me();
        if (a && a.state === "thinking" && S.conv) A.stop(S.conv); else open(false);
        return true;
      }
      return false;
    },
  };
  return self;
}
