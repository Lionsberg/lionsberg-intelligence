// talk-place.js: the Talk, the conversation-first place of the ICE (DESIGN-TALK.md, proposal).
//
// The first screen. You speak with one agent, your chief of staff; it asks you the few things that
// need you, one at a time, as turns in the conversation; it tasks workers on your sentence and
// brings back one line when one returns. Every other view sits behind More. One house: the same
// record, the same engine, the same server and the same dock component as every other place.
//
// One voice, and no cards (DESIGN-TALK.md): the page
// says little, never a count unasked, and draws no card, chip or button in the stream. The line at the
// top is her greeting ("Good afternoon. I am <her name>." on a first sitting), or one line of what changed
// on a return. Nothing is dealt until she asks ("what needs me?", "deal me", "next"); then each
// question is her words, answered by the person's words. Every ask is her line (or a worker's, under
// its name), answered the same way. Everything is one stream in time order, nothing pinned at the
// foot, and an answer never takes anything away.
//
// What it reads: ctx.state (the Deal's cards through deal.js `dealt` and the one owed line through
// `owedLine`, hud.bodies_live and hud.agents for who is at work and what each agent asks, threads
// for a line that arrived, hud.person for the person's name, hud.keepsakes through state.js
// read.keepsakes). What it writes: the Deal's own act for an answer (deal.js `actFor`, through
// ctx.act, the same Undo), a `keepsake` line in the person's own record when a card is finished
// here, a worker through ctx.launchBody on the person's yes, and one `study` line per measure per
// sitting. It never fetches. Kept on this device: when you last sat here, what was there when you
// left, and the page's own turns (as turns: the person's, the page's, the settled lines, each with
// its time), so a reload restores the conversation as it was said.
//
// Answers act: with a question up, the option's own words, its place ("the second") or "yes" for
// the suggested one settle it as a tap would. Your agent may propose the same as an ask of kind
// `act` ({card, option}); its Yes settles through `settleCard`, which this page hands the dock.
//
// Never swap her card mid-thought: a change in the record waits while the line to speak has words,
// and for twenty seconds after her last keystroke. After an answer the next question comes within
// two seconds of idleness (a dust "One more." says it is coming); the line to speak holding words
// holds it.

import createDock, { rememberedName } from "./dock.js";
import { askWords, noPaths } from "./dock-card.js";
import { dealt, actFor, owedLine } from "./deal.js";
import { store, setPref, setNamed, markAnswered, unmarkAnswered, agent as A } from "./state.js";

// The conversation is kept across leave and return (as the Agents room keeps its lines), so going
// to More and back costs no rebuild and no second stream; the page's own turns are kept with it.
const KEPT = { el: null, inst: null, local: [], answers: [], sent: 0, settled: [], asks: new Map(), markedOpen: false, folded: 0 };

const NEXT_MS = 2000;               // after an answer, the next question comes within this much idleness
const CALM_MS = 20000;              // a change in the record never swaps the question within this long of her last keystroke
const AWAY_MS = 60 * 60 * 1000;     // a return after an hour is met with one line of what changed
const DAY_MS = 24 * 60 * 60 * 1000; // a return after a day is met as a first sitting: a welcome
const RESUME_MS = 10 * 60 * 1000;   // a reload within this long of her last act is the same sitting: nothing folded
const SWITCH_MS = 10 * 60 * 1000;   // the ten-minute experiment
const KEEPSAKES_MAX = 60;
const TURNS_MAX = 60;
const MARKED_SHOWN = 3;             // more settled lines than this: the earlier ones fold into one quiet line

const LS = {
  get(k, d) { try { const v = localStorage.getItem("hud.talk." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("hud.talk." + k, JSON.stringify(v)); } catch { /* this visit only */ } },
};
const SS = {
  get(k, d) { try { const v = sessionStorage.getItem("hud." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { sessionStorage.setItem("hud." + k, JSON.stringify(v)); } catch { /* this visit only */ } },
};

// The keepsake marks: one made frame per kind of card (hud/art/), shown at 24 px with its
// field centred. The code only chooses and places them.
const MARKS = {
  commitment: "art/b-field-person-a.jpg",
  request: "art/b-field-cell-a.jpg",
  thread: "art/b-field-cell-b.jpg",
  decide: "art/b-field-body-a.jpg",
  sighting: "art/l-person-flow-a.jpg",
  other: "art/b-field-person-b.jpg",
};
export function markFor(kind) { return MARKS[kind] || MARKS.other; }

// ------------------------------------------------------------------ what the record says (pure)

/** The workers at work, the ones that came back, and the ones that stopped, from what the server
    reads of this machine (hud.bodies_live.machine) and the agents the host started (hud.agents[].body). */
export function workersOf(st) {
  const live = (st && st.hud && st.hud.bodies_live) || {};
  const machine = Array.isArray(live.machine) ? live.machine : [];
  const out = { working: [], back: [], stopped: [] };
  const first = (s) => String(s || "").split("\n").map((x) => x.replace(/^#+\s*/, "").trim()).find(Boolean) || "";
  for (const e of machine) {
    if (!e || e.kind !== "background") continue;
    const w = { name: e.name || e.folder, task: first(e.task), last: first(e.status_last), key: `${e.folder}:${(e.handoff || {}).bytes || ""}`, started: e.started || null, machine: true };
    if (e.handoff && e.handoff.present && !e.handoff.reviewed) out.back.push(w);
    else if (e.state === "running") out.working.push(w);
    else if (e.state === "stale") out.stopped.push(w);
  }
  // a fixture's simpler list (bodies-*.json): a body with a write in the last half hour is at work
  if (!machine.length && Array.isArray(live.bodies)) {
    for (const b of live.bodies) if (b && b.process === "alive") out.working.push({ name: b.name, task: "", last: "", key: b.name });
  }
  for (const a of ((st && st.hud && st.hud.agents) || [])) {
    if (a && a.body && a.state !== "offline" && !out.working.some((w) => w.name === a.name)) {
      out.working.push({ name: a.name || a.id, task: first(a.body.task), last: "", key: a.id });
    }
  }
  return out;
}

const norm = (s) => String(s || "").toLowerCase().replace(/[’']/g, "").replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
const inList = (text, list) => [].concat(list || []).some((w) => norm(w) === text);

/** The intent of a line said here, or null when it goes to the agent unchanged. The page answers
    only what it knows: what needs me, who is working on what, a worker by sentence when no agent
    answers, and "ready" or "next". Everything else ("what’s blocked?", "what should I do?") is the
    agent's, with no line from the page. `words.ready` is the strings' list (talk_place.ready_words). */
export function intentOf(text, words = {}) {
  const s = String(text || "").trim();
  if (!s) return null;
  const n = norm(s);
  if (/^(next|next one|the next one|what is next|whats next|and next|go on|another)$/.test(n)) return { kind: "next" };
  if (/^(deal me( in)?|deal( me)? the (hand|cards)|deal|show me (the|my) hand|whats in my hand|what is in my hand|lets play)$/.test(n)) return { kind: "deal" };
  if (inList(n, words.ready || ["ready", "i am ready", "show me"])) return { kind: "ready" };
  // "what needs me?", asked a few plain ways: the page answers from the one owed line, before the agent
  if (/^(so\s+)?(what|which)\s+(needs|is waiting on|waits on|is owed by)\s+me(\s+(now|today|first))?$/.test(n)
    || /^what\s+(waits on me|is waiting for me|is waiting on me)(\s+(now|today))?$/.test(n)
    || /^how many(\s+things)?(\s+(wait|are waiting|need me|do i have|are there|are left|are owed))?(\s+(on|for) me)?(\s+(now|today))?$/.test(n)) return { kind: "needs" };
  const w = s.match(/^(?:please\s+)?(?:have|ask|get|let)\s+(?:a|another|one|the)\s+(?:new\s+)?worker\s+(?:to\s+)?(.+)$/i)
    || s.match(/^(?:task|give)\s+a\s+(?:new\s+)?worker\s*(?:to|with|on|:)?\s*(.+)$/i)
    || s.match(/^(?:start)\s+a\s+(?:new\s+)?worker\s+(?:to|on|for)\s+(.+)$/i);
  if (w) return { kind: "worker", task: w[1].trim().replace(/[.!]+$/, "") };
  if (/^(who|what)\b/i.test(s) && /\b(working|doing|at work|busy|up to)\b/i.test(s) && !/\byou\b/i.test(s)) return { kind: "who" };
  return null;
}

/** Which of a question's options a line names, or -1: the option's own words (or the words that
    set it apart from the others), its place ("the second", "2"), or "yes" for the suggested one. */
export function matchOption(text, options, recommendation, words = {}) {
  const opts = (options || []).map(norm);
  if (!opts.length) return -1;
  const n = norm(text);
  if (!n) return -1;
  const exact = opts.indexOf(n);
  if (exact >= 0) return exact;
  // the place: "the second", "second one", "number two", "2"
  const place = n.replace(/^(the|number|option|choice)\s+/, "").replace(/\s+(one|option|choice|please)$/, "").trim();
  const ords = words.ordinals || [["first", "one", "1"], ["second", "two", "2"], ["third", "three", "3"]];
  for (let i = 0; i < Math.min(ords.length, opts.length); i++) if ([].concat(ords[i]).map(norm).includes(place)) return i;
  // yes: the suggested one
  if (inList(n, words.yes || ["yes", "yes please", "ok", "okay", "sure"])) return (options || []).indexOf(recommendation);
  // the option's words: a short line inside one option alone, or one option inside a short line
  const toks = n.split(" ").filter((x) => x.length > 2 && !["the", "and", "for", "that", "this", "please", "lets", "let", "with"].includes(x));
  if (!toks.length || n.split(" ").length > 8) return -1;
  const inside = opts.map((o, i) => (toks.every((x) => o.split(" ").includes(x)) ? i : -1)).filter((i) => i >= 0);
  if (inside.length === 1) return inside[0];
  const holds = opts.map((o, i) => (o.length >= 4 && (" " + n + " ").includes(" " + o + " ") ? i : -1)).filter((i) => i >= 0);
  if (holds.length === 1) return holds[0];
  return -1;
}

/** What waits on a thing, in a sentence that parses: "Booking the hall, then the gathering" becomes
    "Booking the hall waits on it, then the gathering." */
export function waitsOnIt(t, unlocks) {
  const u = String(unlocks || "").trim().replace(/[.]+$/, "");
  if (!u) return "";
  const m = u.match(/^(.*?),\s*(then\s+.+)$/i);
  return m ? t("talk_place.line.blocks", { first: m[1], then: ", " + m[2] }) : t("talk_place.line.blocks", { first: u, then: "" });
}

/** An option said inside her sentence: its capital is kept only for a day, a month, "I", an
    initialism, or a name the card's own question capitalises mid-sentence. */
export function inSentence(option, question = "") {
  const o = String(option || "");
  const w = (o.match(/^[^\s,.;:]+/) || [""])[0];
  if (!w || w === "I" || /^[A-Z]{2,}/.test(w)) return o;
  if (/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|July|August|September|October|November|December)$/.test(w)) return o;
  if (new RegExp("[^.!?]\\s" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(String(question || ""))) return o;
  return o.charAt(0).toLowerCase() + o.slice(1);
}

/** A sentence that asks keeps its question mark: "Is it on track?" never becomes "Is it on track." */
export function endSentence(s) {
  const x = String(s || "").trim();
  if (!x) return "";
  return /[.?!…]["”’)]?$/.test(x) ? x : x + ".";
}

/** The part of the day, for her greeting. */
export function partOfDay(hour) { return hour >= 5 && hour < 12 ? "morning" : hour >= 12 && hour < 18 ? "afternoon" : "evening"; }

/** The scene for the hour and the state: one still frame, dim, behind. A frame from the brand's
    hand (hud/art/); the code only chooses and places it. */
export function sceneFor(owed, urgent, working, hour) {
  const night = hour >= 21 || hour < 5;
  if (urgent) return `art/i-person-alone-${night ? "b" : "a"}.jpg`;   // the field gathered on one thing
  if (working) return "art/j-body-of-bodies-a.jpg";                     // the others at work
  if (owed) return `art/i-person-alone-${night ? "b" : "a"}.jpg`;
  return `art/l-person-flow-${hour >= 5 && hour < 12 ? "a" : hour >= 12 && hour < 18 ? "b" : "c"}.jpg`;   // the person at rest
}

/** The settled lines to show and the ones folded: with more than `shown` settled lines, every one
    but the newest folds into one quiet line ("Three marked earlier · show"). Pure, over the page's
    turns ([{at, data: {kind}}]); -> {hidden: Set of items, foldAt, count}. */
export function foldMarked(items, open = false, shown = MARKED_SHOWN) {
  const settled = items.filter((x) => x && x.data && x.data.kind === "settled");
  if (open || settled.length <= shown) return { hidden: new Set(), foldAt: null, count: 0 };
  const hide = settled.slice(0, -1);
  return { hidden: new Set(hide), foldAt: hide[0].at, count: hide.length };
}

// ------------------------------------------------------------------ the place

export default function create() {
  let el = null, ctx = null;
  const $ = {};
  const S = {
    now: null,            // her current turn, in the stream at its time: {kind, ...}
    nowAt: 0,             // when it was first shown (its place in the stream)
    welcome: false,       // a first sitting (or a return after a day): her greeting says her name
    dealing: SS.get("talk.dealing", false),   // the hand is dealt only when she asks ("what needs me?", "deal me", "next"); this sitting
    revealed: false,
    nightShown: false,    // "Ask me anyway" at night
    arrival: null,        // {text, prefer}: the line of what changed, said once on a return
    foldBefore: 0,        // turns said before this moment are folded above "Earlier" (0: nothing folded)
    awaitNext: false,     // an answer settled: the next question comes after a breath of idleness
    answeredAt: 0,
    queued: false,        // the record changed while she typed: drawn once she is calm
    switchUntil: LS.get("switch_until", 0),
    paintedAt: null,
  };
  let typedAt = 0, activeAt = 0;
  const t = (k, v) => ctx.t(k, v);
  const h = (...a) => ctx.card.h(...a);
  const st = () => ctx.state || {};
  const lower = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : "");
  const upper = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");
  const words = () => ({ ready: t("talk_place.ready_words"), yes: t("talk_place.yes_words"), ordinals: t("talk_place.ordinals") });

  // ---------------------------------------------------------------- the facts, computed
  function deck() { return st().deal ? dealt(ctx) : { open: [], fits: [], all: [], next: 0, rest: 0 }; }
  function line() { return owedLine(ctx, deck()); }
  /** the one count of what waits: the state's owed list as the Deal reads it (state.js read.owedByStake,
      deal.js briefing), so "what needs me?", the card's "1 of n" and the host's `waiting` say the Deal's number */
  function owedCount() { return ctx.read.owedByStake(st()).length; }
  /** the question to ask: the one the owed line names first (the same first the Deal names) */
  function firstOpen() {
    const open = deck().open;
    const want = S.arrival && S.arrival.prefer;
    return (want && open.find((c) => c.id === want)) || firstOwedCard() || (st().deal ? line().card : null) || open[0] || null;
  }
  /** the one owed list's first (read.firstOwed), as a card she can answer here: in the hand, or dealt
      beyond it, never answered; else null. So the page's "the first", the question on screen and the
      note to her agent name one thing (never two firsts inside the Talk). */
  function firstOwedCard() {
    const s = st();
    const first = ctx.read.firstOwed(s);
    if (!first || !s.deal) return null;
    const key = (x) => { const c = ctx.read.cardOfOwed(s, x); return (c && c.id) || x.id; };
    const k = key(first);
    const open = deck().open;
    const pool = [...open, ...(s.deal.cards || []), ...((s.deal.beyond && s.deal.beyond.cards) || [])];
    return pool.find((c) => c && !c.answered && !store.answered.has(c.id) && key(c) === k && (c.options || []).length) || null;
  }
  function hour() { return ctx.fmt.now().getHours(); }
  function isNight() { const x = hour(); return x >= 22 || x < 5; }
  function stakeOf(dc) {
    const owed = ctx.read.owedByStake(st());
    const e = owed.find((o) => o.id === dc.id);
    const due = (e && e.due) || (ctx.read.card(st(), dc.id) || {}).by || dc.by || null;
    const days = due ? ctx.fmt.daysBetween(ctx.fmt.now(), ctx.fmt.date(due)) : null;
    return { due, late: days != null && days < 0, whole: !!dc.whole_waits };
  }
  function protectedNight(dc) { return isNight() && !S.nightShown && !(dc && (stakeOf(dc).late || stakeOf(dc).whole)); }
  function titleOf(dc) { return (dc && (dc.title || (ctx.read.card(st(), dc.id) || {}).title || dc.question)) || ""; }
  /** the owed entry's own title for a card (a name, never its question), or "" */
  function nameOfCard(dc) {
    if (!dc) return "";
    const hers = cardNameOf(dc.id);
    if (hers) return hers;
    const e = ctx.read.owedByStake(st()).find((o) => o.id === dc.id) || ((st().owed || {}).entries || []).find((o) => o && o.id === dc.id);
    return (e && e.title) || dc.title || (ctx.read.card(st(), dc.id) || {}).title || "";
  }
  /** the person's own agent: never a worker it started (a row with a `body`) */
  function mineAll() { return ((st().hud && st().hud.agents) || []).filter((x) => x.of === st().actor && x.kind !== "guest"); }
  function me() { return mineAll().slice().sort((a, b) => (a.body ? 1 : 0) - (b.body ? 1 : 0))[0] || null; }
  function herName() { const n = KEPT.inst && KEPT.inst.name; if (n) return n; const a = me(); return (a && a.name) || rememberedName() || null; }
  /** the person's own name, when the record says it (hud.person.name, or their entry among the actors) */
  function personName() {
    const s = st();
    const p = (s.hud && s.hud.person) || {};
    const self = (s.actors || []).find((x) => x && x.id === s.actor) || {};
    const n = String(p.name || self.name || "").trim();
    // a placeholder is no name: a sample house's "Player" is greeted with no name
    return n && !/^(player|the player|person|you|user|guest)$/i.test(n) ? n : null;
  }
  /** How much of her work is seen (figures on by default, with a plain view): the
      person's own choice on this device, else Working for everyone; Plain is one turn of the knob. */
  function depthNow() {
    const d = store.prefs.depth;
    return d === "plain" || d === "working" || d === "full" ? d : "working";
  }
  /** a first sitting may say once, in dust under the status line, how to turn the knob down */
  function depthHint() {
    if (store.prefs.depth || LS.get("depth_hint_at", 0)) return false;
    LS.set("depth_hint_at", Date.now());
    return true;
  }
  function setDepth(v) {
    if (!["plain", "working", "full"].includes(v)) return;
    setPref("depth", v);
    refresh();
  }
  /** "show me more" / "show me less" / "show me everything": the knob turned by a word, said back in one line */
  function depthWord(text) {
    const n = norm(text);
    const order = ["plain", "working", "full"];
    const cur = order.indexOf(depthNow());
    let to = null, more = true;
    if (inList(n, t("talk_place.depth_full_words"))) to = 2;
    else if (inList(n, t("talk_place.depth_more_words"))) to = Math.min(2, cur + 1);
    else if (inList(n, t("talk_place.depth_less_words"))) { to = n === "plain" || n === "keep it plain" ? 0 : Math.max(0, cur - 1); more = false; }
    if (to == null) return null;
    // the way the word turned the knob, not where it landed: "show me less" at Plain is the least line
    return { to: order[to], same: to === cur, more };
  }
  /** every open ask of every agent of the person (the host's `asks`): her own agent's and its workers' */
  function allAsks() { return mineAll().flatMap((a) => (a.asks || []).map((x) => ({ ...x, agent: a.id, agentName: a.name || null }))); }
  function othersAsks() { const m = me(); return allAsks().filter((x) => !m || x.agent !== m.id); }

  /** The one line at the top: her greeting, and on a first sitting her name ("Good afternoon. I am
      <her name>."), or one line of what changed on a return; never a count, never what waits (plain
      working with one's agent by default; the hand is entered by asking). */
  function lineParts() {
    if (S.arrival) return { text: S.arrival.text, ready: false };
    const name = personName();
    const hello = t(name ? "talk_place.hello_named" : "talk_place.hello_plain", { hello: t("talk_place.hello." + partOfDay(hour())), name });
    const her = herName();
    // the greeting keeps its second sentence as first drawn: a reload within the sitting restores the
    // name it said (never "Good evening." bare where "I am <her name>." had been)
    if (S.welcome && her && S.foldBefore) { const g = LS.get("greet", null); if (!g || g.at !== S.foldBefore || g.name !== her) LS.set("greet", { at: S.foldBefore, name: her }); }
    const said = S.welcome ? her : S.greetName;
    return { text: said ? hello + " " + t("talk_place.i_am", { name: said }) : hello, ready: false };
  }
  // ---------------------------------------------------------------- what changed while away
  function snapshot() {
    const w = workersOf(st());
    const s = st();
    LS.set("left", {
      at: Date.now(),
      owed: ctx.read.owedByStake(s).map((e) => e.id),
      back: w.back.map((x) => x.key),
      lines: (s.threads || []).filter((th) => (th.to || []).includes(s.actor)).map((th) => th.id + "@" + th.last_ts),
    });
  }
  /** One line of what changed, never a count; the question that follows is the card it names. */
  function awayLine() {
    const was = LS.get("left", null);
    if (!was || Date.now() - was.at < AWAY_MS) return null;
    const s = st(), w = workersOf(s);
    const open = deck().open;
    const parts = [];
    let prefer = null;
    const back = w.back.filter((x) => !(was.back || []).includes(x.key));
    if (back.length === 1) {
      parts.push(t("talk_place.away.back_one", { name: back[0].name }));
      const hc = open.find((c) => String(titleOf(c) + " " + (c.question || "")).includes(back[0].name));
      if (hc) prefer = hc.id;
    } else if (back.length > 1) parts.push(t("talk_place.away.back_many"));
    const owedNew = ctx.read.owedByStake(s).filter((e) => !(was.owed || []).includes(e.id));
    if (owedNew.length === 1) {
      parts.push(t("talk_place.away.owed_one", { what: lower(owedNew[0].title || "") }));
      if (!prefer && open.some((c) => c.id === owedNew[0].id)) prefer = owedNew[0].id;
    } else if (owedNew.length > 1) parts.push(t("talk_place.away.owed_many"));
    const lines = (s.threads || []).filter((th) => (th.to || []).includes(s.actor) && !(was.lines || []).includes(th.id + "@" + th.last_ts));
    if (lines.length === 1) parts.push(t("talk_place.away.line_one", { where: ctx.read.holonName(s, lines[0].holon) || lower(lines[0].title || "") }));
    else if (lines.length > 1) parts.push(t("talk_place.away.line_many"));
    if (!parts.length) return null;
    // what changed only: the first card is never offered unasked (the hand is entered by asking)
    const text = t("talk_place.away.lead", { what: parts.slice(0, 2).join(t("talk_place.away.and")) });
    const first = (prefer && open.find((c) => c.id === prefer)) || null;
    return { text, prefer: first ? first.id : null };
  }

  // ---------------------------------------------------------------- the surface studies itself
  function study(measure, value, once = true) {
    if (store.prefs.study === "off" || !store.server) return;
    const key = "talk.study." + measure;
    if (once && SS.get(key, false)) return;
    SS.set(key, true);
    ctx.act("study", { view: "talk", measure, value: Math.round(value), as_of: new Date().toISOString(), session: SS.get("study.session", "") },
      {}, ctx.home, { confirmed: true, quiet: true, label: "" });
  }

  // ---------------------------------------------------------------- what the page says, for her
  function said(you, page, extra = {}) {
    KEPT.answers.push({ at: new Date().toISOString(), you: you || "", said: page || "", ...extra });
    if (KEPT.answers.length > 24) { const cut = KEPT.answers.length - 24; KEPT.answers.splice(0, cut); KEPT.sent = Math.max(0, (KEPT.sent || 0) - cut); }
  }
  /** The page context sent with every line (the `page` of /agent/say): the line on screen, the
      question and its options, and what the page said here since the last line (each once, as her
      sentence: the host keeps them in the conversation as hers). No `settled`: the page's own
      "Marked" was hers to say, never a word the agent repeats at the head of its reply. */
  function pageContext() {
    const q = S.now && S.now.kind === "question" ? S.now.dc : null;
    const fresh = KEPT.answers.slice(KEPT.sent || 0);
    KEPT.sent = KEPT.answers.length;
    const f = firstOpen();
    const settled = KEPT.settled.splice(0);
    return {
      line: ($.line && $.line.innerText.trim()) || "",
      question: q ? (q.question || titleOf(q)) : null,
      recommendation: q && q.recommendation ? q.recommendation : null,
      options: q ? (q.options || []).slice() : [],
      local_answers: fresh.map((x) => x.said).filter(Boolean).slice(-4),
      // the first thing that waits, as the page names it, so her agent names the same first
      first: f ? { card: f.id, title: nameOfCard(f) || titleOf(f), question: f.question || null } : null,
      // the one count of what waits (the card's "1 of n", "what needs me?" and "how many" all say it)
      waiting: owedCount(), waiting_not_cards: line().notCards,
      // what her own words settled here since the last line (never "Marked": the card and the option),
      // so her agent never proposes a mark for what is already done
      settled,
    };
  }
  /** every line the page has said (so the host's echo of them is never drawn a second time) */
  function pageSaid() {
    return [...KEPT.local.filter((x) => x.data && x.data.kind !== "person").map((x) => x.data.text), ...KEPT.answers.map((x) => x.said)].filter(Boolean);
  }

  // ---------------------------------------------------------------- the page's own turns, kept as turns
  function persist() {
    LS.set("turns", KEPT.local.filter((x) => x.data).slice(-TURNS_MAX).map((x) => ({ ...x.data, at: x.at })));
  }
  /** a turn the page keeps: drawn in the stream at its time, and kept on this device as what it is */
  function addTurn(data, node) {
    const item = { at: data.at || Date.now(), node, data: { ...data } };
    delete item.data.at;
    KEPT.local.push(item);
    if (KEPT.local.length > TURNS_MAX) KEPT.local.splice(0, KEPT.local.length - TURNS_MAX);
    persist();
    LS.set("active_at", Date.now());
    refresh();
    toEnd();
    return item;
  }
  function nodeFor(d) {
    if (d.kind === "person") return you(d.text);
    if (d.kind === "settled") return settledNode(d, null).node;
    const turn = her(h("p", { class: "talk-her-line" }, d.text));
    if (d.link === "agents") turn.append(agentsLink());
    return turn;
  }
  /** a reload, or a mount after another view: the kept turns come back as turns, each in its place */
  function restore() {
    if (KEPT.local.length) return;
    const kept = LS.get("turns", []);
    for (const d of Array.isArray(kept) ? kept : []) {
      if (!d || typeof d.text !== "string" || !["person", "page", "settled"].includes(d.kind)) continue;
      const data = { ...d }; delete data.at;
      KEPT.local.push({ at: Number(d.at) || 0, node: nodeFor(data), data });
    }
  }

  // ---------------------------------------------------------------- the frame
  function build() {
    el.textContent = "";
    $.root = h("div", { class: "talk" });
    $.scene = h("figure", { class: "talk-scene", "aria-hidden": "true" }, h("img", { alt: "", decoding: "async" }));
    $.door = h("button", { class: "talk-door", type: "button", "aria-label": t("talk_place.door_label"), onclick: () => KEPT.inst && KEPT.inst.about() });
    $.voice = h("div", { class: "talk-voice", hidden: "" });
    $.line = h("h1", { class: "talk-line voice", id: "talk-line" });
    $.earlier = h("button", { class: "link-btn talk-earlier", type: "button", hidden: true, onclick: unfold }, t("talk_place.earlier"));
    $.now = h("section", { class: "talk-now", "aria-live": "polite", "aria-label": t("talk_place.now_label") });
    $.marked = h("p", { class: "talk-marked dust" });
    // the open question scrolled away above (a long answer, a worker's asks): one quiet pill at the
    // stream's foot brings it back; it holds no slot and is gone the moment the question is in view
    $.above = h("button", { class: "pill quiet talk-above", type: "button", hidden: "", onclick: () => {
      const q = newestAskNode(); if (q) { if (KEPT.inst && KEPT.inst.unpin) KEPT.inst.unpin(); q.scrollIntoView({ block: "start" }); requestAnimationFrame(aboveWatch); }
    } }, "↑ " + t("talk_place.q_above"));
    $.conv = h("div", { class: "talk-conv", role: "region", "aria-label": t("talk_place.stream_label") });
    $.head = h("header", { class: "talk-head" }, h("div", { class: "talk-headrow" }, $.door, $.voice), $.line);
    // the one status line at the foot, beneath the line to speak (the trust layer):
    // the dock draws it at the depth chosen; one tap opens every figure, the mode's word opens the modes
    $.status = h("p", { class: "talk-status dust", role: "status", hidden: "" });
    // a first sitting says once, in dust beneath it, how to turn the knob down; gone once the knob is turned
    $.hint = depthHint() ? h("p", { class: "talk-depth-hint dust" }, t("talk_place.depth_hint")) : null;
    $.root.append($.scene, $.head, $.earlier, $.conv, $.status, ...($.hint ? [$.hint] : []));
    el.append($.root);
    // the line to speak is the dock's; a line said here is read first for the intents and the answers
    $.root.addEventListener("keydown", onKeyCapture, true);
    $.root.addEventListener("click", onClickCapture, true);
    $.root.addEventListener("input", onTyping, true);
    $.root.addEventListener("pointerdown", () => { activeAt = Date.now(); }, true);
    $.root.addEventListener("focusout", () => setTimeout(calmCheck, 0), true);
  }

  /** One story of who brought her: the door's sheet reads the same source as the
      plain line, the host's house note as the host gives it to the page (hud.dock.brought_by), else the
      plain line's own words ("the one who gave you this"); never a name the fixture's record supplies. */
  function dockState() {
    const s = st(), hud = s.hud || {};
    const b = (hud.dock || {}).brought_by;
    const by = b && typeof b === "object" ? b : null;
    const person = Object.assign({}, hud.person || {}, { brought_by: by });
    const actors = Array.isArray(s.actors) ? s.actors.map((a) => (a && a.id === s.actor && a.brought_by ? Object.assign({}, a, { brought_by: null }) : a)) : s.actors;
    return Object.assign({}, s, { hud: Object.assign({}, hud, { person }), actors });
  }
  function dockCtx() { return Object.assign({}, ctx, { state: dockState(), dock: { open: true, setOpen() {} }, settleCard }); }
  function mountConversation() {
    if (!KEPT.inst) {
      KEPT.el = h("div", { class: "talk-dock" });
      KEPT.inst = createDock({
        inline: true,
        asksInStream: true,
        askWords: true,
        pageContext: () => (KEPT.page ? KEPT.page() : undefined),
        pageSaid: () => (KEPT.said ? KEPT.said() : []),
        localTurns: () => (KEPT.turns ? KEPT.turns() : KEPT.local),
        foldBefore: () => (KEPT.foldBefore ? KEPT.foldBefore() : 0),
        onFolded: (n) => { KEPT.folded = n; if (KEPT.onFolded) KEPT.onFolded(n); },
        modeSlot: () => KEPT.modeSlot || null,
        placeholder: () => (KEPT.placeholder ? KEPT.placeholder() : ""),
        aboutExtra: () => (KEPT.aboutExtra ? KEPT.aboutExtra() : null),
        // the trust layer (DESIGN-TALK.md): how much of her work is seen, the status line's slot,
        // and the workers this machine knows of beyond the host's own
        depth: () => (KEPT.depth ? KEPT.depth() : null),
        setDepth: (v) => KEPT.setDepth && KEPT.setDepth(v),
        statusSlot: () => KEPT.statusSlot || null,
        workers: () => (KEPT.workers ? KEPT.workers() : []),
      });
      // this mount's own readers first (the conversation outlives a mount; its hooks follow the page)
      hooks();
      KEPT.inst.mount(KEPT.el, dockCtx());
    } else {
      hooks();
      try { KEPT.inst.update(dockCtx()); } catch (e) { console.error("talk dock:", e); }
    }
    $.conv.append(KEPT.el);
    placeHead();
    const sc = KEPT.el.querySelector(".dock-scroll");
    if (sc && !sc.dataset.aboveWatch) { sc.dataset.aboveWatch = "1"; sc.addEventListener("scroll", () => requestAnimationFrame(() => KEPT.aboveWatch && KEPT.aboveWatch()), { passive: true }); }
    // the stream as drawn: an ask asked once, and the pill true, whenever its rows change
    if (sc && !sc.dataset.saidWatch) {
      sc.dataset.saidWatch = "1";
      let queued = false;
      new MutationObserver(() => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; saidAboveCheck(); if (KEPT.aboveWatch) KEPT.aboveWatch(); }); })
        .observe(sc, { childList: true, subtree: true, characterData: true });
    }
    // presence: while her turn streams the figure behind brightens, and settles when she stops
    const busy = () => {
      const b = KEPT.el.dataset.busy === "true";
      $.root.dataset.speaking = b ? "true" : "false";
      if (!b) calmCheck();
    };
    busy();
    S.busyWatch = new MutationObserver(busy);
    S.busyWatch.observe(KEPT.el, { attributes: true, attributeFilter: ["data-busy"] });
  }
  function hooks() {
    KEPT.page = pageContext;
    KEPT.said = pageSaid;
    KEPT.turns = turnsNow;
    KEPT.foldBefore = () => S.foldBefore;
    KEPT.onFolded = (n) => { if ($.earlier) $.earlier.hidden = !(n > 0 && S.foldBefore > 0); };
    KEPT.modeSlot = $.voice;
    KEPT.placeholder = placeholderWords;
    KEPT.aboutExtra = keepsakesRow;
    KEPT.aboveWatch = aboveWatch;
    KEPT.depth = depthNow;
    KEPT.setDepth = setDepth;
    KEPT.statusSlot = $.status;
    KEPT.workers = () => workersOf(st()).working.filter((w) => w.machine);
  }
  /** the stream's own turns, in time order: the kept turns (the earlier settled lines folded into one
      quiet line), every other agent's open asks at the time each was first seen, and her current turn */
  function turnsNow() {
    const fm = foldMarked(KEPT.local, KEPT.markedOpen);
    const out = KEPT.local.filter((x) => !fm.hidden.has(x));
    if (fm.count) {
      $.marked.textContent = "";
      $.marked.append(t("talk_place.marked_fold", { count: upper(ctx.fmt.number(fm.count, true)) }) + " · ",
        h("button", { class: "link-btn talk-marked-show", type: "button", onclick: () => { KEPT.markedOpen = true; refresh(); } }, t("talk_place.marked_show")));
      out.push({ at: fm.foldAt, node: $.marked });
    }
    for (const x of KEPT.asks.values()) out.push(x);
    if ($.now.childNodes.length) out.push({ at: S.nowAt || Date.now(), node: $.now });
    return out.sort((a, b) => a.at - b.at);
  }
  /** the head is the top of the stream: it scrolls away with the conversation, never holds a slot,
      and there is only ever one (a remount replaces it, never appends a second) */
  function placeHead() {
    const scroll = KEPT.el && KEPT.el.querySelector(".dock-scroll");
    if (!scroll) return;
    for (const x of scroll.querySelectorAll(":scope > .talk-head, :scope > .talk-earlier")) if (x !== $.head && x !== $.earlier) x.remove();
    if (scroll.firstChild !== $.head) scroll.prepend($.head);
    if ($.head.nextSibling !== $.earlier) $.head.after($.earlier);
  }
  function refresh() {
    if ($.hint && store.prefs.depth) { $.hint.remove(); $.hint = null; }
    if (KEPT.inst) { try { KEPT.inst.update(dockCtx()); } catch (e) { console.error("talk dock:", e); } }
    placeHead();
    requestAnimationFrame(aboveWatch);
  }
  function toEnd() {
    if (KEPT.inst && KEPT.inst.unpin) KEPT.inst.unpin();
    const scroll = KEPT.el && KEPT.el.querySelector(".dock-scroll");
    if (scroll) requestAnimationFrame(() => { scroll.scrollTop = scroll.scrollHeight; });
  }

  // ---------------------------------------------------------------- calm: never swap her card mid-thought
  function input() { return KEPT.inst ? KEPT.inst.input : null; }
  function hasWords() { const i = input(); return !!(i && i.value.trim()); }
  function calm() {
    const i = input();
    if (i && (document.activeElement === i || i.value.trim())) return false;
    return Date.now() - typedAt >= CALM_MS;
  }
  /** after an answer: idle for a breath (the line to speak empty, no key or tap for two seconds) */
  function idle() { const n = Date.now(); return !hasWords() && n - typedAt >= NEXT_MS && n - activeAt >= NEXT_MS && n - S.answeredAt >= NEXT_MS; }
  function calmCheck() {
    if (!el || !ctx) return;
    if (S.queued && calm()) { S.queued = false; draw(); }
    if (S.awaitNext && idle()) nextQuestion();
  }

  // ---------------------------------------------------------------- her current turn: one thing at a time
  function chooseNow() {
    if (S.now && ["worker", "switch", "switch_end"].includes(S.now.kind)) return;
    // the question on screen stays while its card is open; when it closed elsewhere, it waits for calm
    if (S.now && S.now.kind === "question") {
      if (deck().open.some((x) => x.id === S.now.dc.id)) return;
      if (!calm()) { S.queued = true; return; }
      S.now = null;
    }
    // after an answer, while the next comes: one dust line, so nothing waits unsaid
    if (S.awaitNext) { S.now = deck().open.length ? { kind: "coming" } : null; return; }
    if (S.dealing && S.switchUntil && Date.now() > S.switchUntil) { S.now = { kind: "switch_end" }; return; }
    // nothing is dealt until she asks for it (a page's own offers wait with it)
    if (!S.dealing) { S.now = null; return; }
    const dc = firstOpen();
    if (dc && !protectedNight(dc)) { S.now = { kind: "question", dc }; return; }
    if (dc) { S.now = { kind: "night" }; return; }
    if (switchDue()) { S.now = { kind: "switch" }; study("switch_offered", 1); return; }
    S.now = null;
  }

  function switchDue() {
    const today = ctx.fmt.now().toDateString();
    if (LS.get("switch_day", "") === today || S.switchUntil) return false;
    return (SS.get("talk.more", 0) >= 3) || (SS.get("talk.undos", 0) >= 2);
  }

  function drawNow() {
    const n = S.now;
    // her name for the card and the count are part of the turn: a change in either redraws it in place
    const extra = n && n.kind === "question" ? "|" + cardNameOf(n.dc.id) + "|" + owedCount() : "";
    const key = n ? n.kind + ":" + (n.dc ? n.dc.id : "") + ":" + (n.status || "") + extra : "";
    if ($.now.dataset.key === key) return;   // the same turn is never redrawn under her
    const was = $.now.dataset.key || "";
    $.now.dataset.key = key;
    $.now.dataset.kind = n ? n.kind : "";
    $.now.textContent = "";
    if (!n) return;
    // a new turn takes its place at the end of the stream; a status change keeps its place
    if (!was || was.split(":").slice(0, 2).join(":") !== key.split(":").slice(0, 2).join(":")) S.nowAt = Date.now();
    if (n.kind === "question") { S.qAt = { card: n.dc.id, at: S.nowAt }; drawQuestion(n.dc); }
    else if (n.kind === "coming") $.now.append(h("p", { class: "talk-coming dust" }, t("talk_place.coming")));
    else if (n.kind === "night") {
      $.now.append(her(h("div", { class: "talk-chips" }, h("button", { class: "link-btn talk-word", type: "button", onclick: () => { S.nightShown = true; S.now = null; draw(); } }, t("talk_place.night_show")))));
    } else if (n.kind === "worker") drawWorker(n);
    else if (n.kind === "switch") {
      $.now.append(her(h("p", { class: "talk-her-line" }, SS.get("talk.more", 0) >= 3 ? t("talk_place.switch.more") : t("talk_place.switch.undo")),
        h("div", { class: "talk-chips" },
          h("button", { class: "link-btn talk-word", type: "button", onclick: () => { S.switchUntil = Date.now() + SWITCH_MS; LS.set("switch_until", S.switchUntil); LS.set("switch_day", ctx.fmt.now().toDateString()); applyFocus(); study("switch_taken", 1); S.now = null; draw(); } }, t("talk_place.switch.yes")),
          h("button", { class: "link-btn talk-word", type: "button", onclick: () => { LS.set("switch_day", ctx.fmt.now().toDateString()); study("switch_declined", 1); S.now = null; draw(); } }, t("talk_place.switch.no")))));
    } else if (n.kind === "switch_end") {
      $.now.append(her(h("p", { class: "talk-her-line" }, t("talk_place.switch.end")),
        h("div", { class: "talk-chips" },
          h("button", { class: "link-btn talk-word", type: "button", onclick: () => { endSwitch(true); } }, t("talk_place.switch.keep")),
          h("button", { class: "link-btn talk-word", type: "button", onclick: () => { endSwitch(false); } }, t("talk_place.switch.back")))));
    }
    refresh();
    toEnd();
  }

  /** her turn, as the stream draws hers: her words, with nothing in the margin */
  function her(...kids) { return h("article", { class: "dock-turn dock-turn--agent talk-turn" }, ...kids); }
  function you(text) { return h("article", { class: "dock-turn dock-turn--you talk-turn" }, h("p", { class: "dock-words" }, text)); }

  /** The question as her words (no cards are presented; the surface is a conversation): the question, the choices in a sentence, the one she
      would choose and why. Answered by the person's words (an option, its place, "yes" for hers); the
      words are hers to type or say. No chips, no card, no link. */
  function questionWords(dc) {
    const q = endSentence(dc.question || titleOf(dc));
    const opts = (dc.options || []).map((o, i) => (i ? inSentence(o, dc.question) : o));
    const choices = opts.length > 2 ? opts.slice(0, -1).join(", ") + t("talk_place.q_or_last") + opts[opts.length - 1]
      : opts.join(t("talk_place.q_or"));
    const why = dc.why || (dc.unlocks ? waitsOnIt(t, dc.unlocks) : "");
    const late = stakeOf(dc).late && !/past|late|ago/i.test(why) ? t("talk_place.q_late") : "";
    const rec = dc.recommendation && (dc.options || []).includes(dc.recommendation) ? inSentence(dc.recommendation, dc.question) : "";
    const parts = [q];
    if (choices) parts.push(endSentence(choices));
    const reason = [why ? endSentence(why) : "", late].filter(Boolean).join(" ");
    if (rec) parts.push(reason ? reason.replace(/[.]$/, "") + t("talk_place.q_so", { option: rec }) : t("talk_place.q_would", { option: rec }));
    else if (reason) parts.push(reason);
    return parts.join(" ");
  }
  function drawQuestion(dc) {
    const q = h("article", { class: "dock-turn dock-turn--agent talk-turn talk-q owed", dataset: { card: dc.id } });
    // her own name for the card, and the one count ("1 of 7"): the welcome's "one thing waits" made true
    const named = ctx.read.cardName ? ctx.read.cardName(st(), dc.id) : "";
    const n = owedCount();
    const top = h("p", { class: "talk-q-top dust" });
    if (named) top.append(h("span", { class: "talk-q-named" }, named));
    if (n > 1) top.append(h("span", { class: "talk-q-count figures" }, t("deal.of", { n: 1, total: n })));
    if (top.childNodes.length) q.append(top);
    q.append(h("p", { class: "talk-her-line talk-q-words" }, questionWords(dc)));
    $.now.append(q);
  }

  function drawWorker(n) {
    if (!n.task) { $.now.append(her(h("p", { class: "talk-her-line" }, t("talk_place.task.empty")))); return; }
    const turn = her(h("p", { class: "talk-her-line" }, t("talk_place.task.ask", { task: n.task })),
      h("p", { class: "talk-q-why dust" }, t("talk_place.task.cost")));
    if (n.status) { turn.append(h("p", { class: "talk-her-line" }, n.status)); if (n.started) turn.append(agentsLink()); $.now.append(turn); return; }
    // answered in words ("yes", "not now")
    $.now.append(turn);
  }
  function agentsLink() {
    return h("p", null, h("button", { class: "link-btn", type: "button", onclick: () => ctx.go("#/bodies") }, t("talk_place.who.open")));
  }

  /** the exact step a worker's ask is about, in the shape of the dock's askStep (hud/dock.js, not
      exported): the command, the file, what is written, the change; paths by their last name below
      Full; the fence lines of a quoted block never shown. Empty when the ask carries none. */
  function stepOf(ask, full) {
    const out = [];
    const cut = (x) => { const l = String(x || "").split("\n"); const s = l.slice(0, 12).join("\n"); return (s.length > 900 ? s.slice(0, 900) : s) + (s.length > 900 || l.length > 12 ? "\n…" : ""); };
    const p = (x) => (full ? String(x) : noPaths(x));
    // a worker's ask carries its plain sentence as `step` and the machine's own call under `raw`
    const raw = ask.raw && typeof ask.raw === "object" ? ask.raw : {};
    const input = ask.input != null ? ask.input : raw.input != null ? raw.input : null;
    let v = null;
    if (input && typeof input === "object") v = input;
    else try { v = input ? JSON.parse(input) : null; } catch { v = null; }
    if (v && typeof v === "object") {
      if (typeof v.command === "string" && v.command.trim()) out.push(p(v.command.trim()));
      const file = v.file_path || v.path || v.notebook_path;
      if (typeof file === "string" && file) out.push(p(file));
      for (const k of ["content", "new_string", "text", "message", "body", "url"]) if (typeof v[k] === "string" && v[k].trim()) { out.push(cut(p(v[k].trim()))); break; }
    } else if (typeof input === "string" && input.trim()) out.push(cut(p(input.trim())));
    for (const c of (Array.isArray(ask.content) ? ask.content : Array.isArray(raw.content) ? raw.content : [])) {
      if (!c || c.type !== "diff") continue;
      const lines = [];
      if (c.path && !out.length) lines.push(p(c.path));
      for (const l of String(c.old || "").split("\n")) if (l) lines.push("− " + l);
      for (const l of String(c.new || "").split("\n")) if (l) lines.push("+ " + l);
      if (lines.length) out.push(cut(lines.join("\n")));
    }
    if (!out.length && raw.title) out.push(p(String(raw.title)));
    if (!out.length && ask.step != null) { const x = typeof ask.step === "string" ? ask.step : (ask.step && (ask.step.sentence || ask.step.text)) || ""; if (x.trim()) out.push(p(x.trim())); }
    if (!out.length && ask.title) out.push(p(String(ask.title)));
    return out.join("\n").replace(/^\s*```[\w-]*\s*$/gm, "").replace(/\n{3,}/g, "\n\n").trim();
  }
  /** the step beneath an ask's words: monospace at Working and Full, folded under "The exact step" at Plain */
  function stepNode(raw, d) {
    if (!raw) return null;
    return d === "working" || d === "full" ? h("pre", { class: "dock-raw dock-ask-step" }, raw)
      : h("details", { class: "dock-fold dock-ask-step" }, h("summary", { class: "dust" }, t("dock.ask_exactly")), h("pre", { class: "dock-raw" }, raw));
  }

  /** every other agent's ask (a worker's question for her), in the stream at the time it was first
      seen: the worker's words under its name, the exact step beneath, and the two answer words the
      Deal's asks have (No, Yes); answered by a tap here or by her next words alike */
  function drawAsks() {
    const open = othersAsks();
    const ids = new Set(open.map((x) => x.id));
    const d = depthNow();
    for (const [id, x] of KEPT.asks) if (!ids.has(id) || x.depth !== d) KEPT.asks.delete(id);
    const seen = LS.get("asks_seen", {});
    for (const x of open) {
      if (KEPT.asks.has(x.id)) continue;
      const at = Number(seen[x.id]) || Date.now();
      seen[x.id] = at;
      const all = [];
      const said = h("p", { class: "dust", role: "status" });
      const tap = async (yes) => {
        for (const b of all) b.disabled = true;
        const r = await A.answer(x.conversation, x.id, yes ? "yes" : "not_this").then((q) => ({ ok: q.ok, reason: q.out && q.out.refused }), () => ({ ok: false }));
        if (!r || !r.ok) { said.textContent = (r && r.reason) || t("dock.answer_failed"); for (const b of all) b.disabled = false; return; }
        draw();
      };
      const btn = (yes, label, cls) => { const b = h("button", { class: cls, type: "button", onclick: () => tap(yes) }, label); all.push(b); return b; };
      const node = h("div", { class: "dock-row talk-ask" }, h("article", { class: "dock-turn dock-turn--agent talk-turn talk-ask-words", dataset: { ask: x.id } },
        askFrom(x.agentName), h("p", { class: "talk-her-line" }, askWords(ctx, x)),
        stepNode(stepOf(x, d === "full"), d),
        x.untrusted ? h("p", { class: "dust" }, t("dock.from_something_read_line")) : null,
        x.leaves ? h("p", { class: "dust" }, t("dock.leaves_computer")) : null,
        h("div", { class: "dock-answers talk-ask-answers" }, btn(false, t("dock.answer.no"), "pill dock-no"), btn(true, t("dock.answer.yes"), "pill primary dock-yes")),
        said));
      KEPT.asks.set(x.id, { at, node, keep: true, depth: d });
    }
    LS.set("asks_seen", Object.fromEntries(Object.entries(seen).filter(([k]) => ids.has(k))));
  }

  /** asked once: when her own line just before her ask already ends on a question ("…Start
      it?"), the ask row draws no second question, only its step and its answers. The dock decides this
      from the turn before in its model; a tool row between them hid it, so the Talk reads the stream as
      drawn: the nearest turn above with words, skipping rows that carry none. */
  function saidAboveCheck() {
    const scroll = KEPT.el && KEPT.el.querySelector(".dock-scroll");
    if (!scroll) return;
    for (const art of scroll.querySelectorAll(".dock-ask-words:not(.is-said-above)")) {
      let row = art.closest(".dock-row") || art, said = false;
      for (let prev = row.previousElementSibling; prev; prev = prev.previousElementSibling) {
        if (prev.querySelector(".dock-ask-words, .talk-ask-words") || prev.matches(".talk-ask")) break;
        const turn = prev.matches(".dock-turn") ? prev : prev.querySelector(".dock-turn");
        if (!turn) continue;
        if (!turn.classList.contains("dock-turn--agent")) break;
        const words = [...turn.querySelectorAll("p, li")].map((n) => n.textContent.trim()).filter(Boolean);
        if (!words.length) continue;
        said = /\?["'”’)]*$/.test(words[words.length - 1]);
        break;
      }
      if (art.classList.contains("talk-said-above") !== said) art.classList.toggle("talk-said-above", said);
    }
  }

  /** who asks, above a worker's card: the worker's name in small caps, apart from her words */
  function askFrom(name) {
    if (!name) return h("p", { class: "talk-ask-from dust" }, t("talk_place.ask_from_unnamed"));
    const parts = t("talk_place.ask_from", { name: "\u0000" }).split("\u0000");
    return h("p", { class: "talk-ask-from dust" }, parts[0], h("span", { class: "talk-ask-name" }, name), parts[1] || "");
  }

  // ---------------------------------------------------------------- the line to speak's words: whole words, never cut
  /** "Talk to <her name>" where it fits on one line; "Talk to me" where it would wrap or clip (at 320
      wide it would wrap to "Talk to / <her name>" and cut the name) */
  let fitCanvas = null;
  function fitsInput(input, text) {
    const w = input && input.clientWidth;
    if (!w) return true;
    const cs = getComputedStyle(input);
    const room = w - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0) - 6;
    fitCanvas = fitCanvas || document.createElement("canvas");
    const g = fitCanvas.getContext("2d");
    g.font = cs.font || `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    return g.measureText(text).width <= room;
  }
  function placeholderWords() {
    const n = herName();
    const plain = t("talk_place.input_plain");
    if (!n) return plain;
    const full = t("talk_place.input", { name: n });
    return fitsInput(KEPT.el && KEPT.el.querySelector(".dock-input"), full) ? full : plain;
  }
  function fitPlaceholder() {
    const input = KEPT.el && KEPT.el.querySelector(".dock-input");
    if (!input) return;
    // the input narrows without a resize too (Stop beside Send, a worker's row): watch the input itself
    if (!input.dataset.fitWatch && typeof ResizeObserver !== "undefined") {
      input.dataset.fitWatch = "1";
      new ResizeObserver(() => requestAnimationFrame(() => KEPT.fitPlaceholder && KEPT.fitPlaceholder())).observe(input);
    }
    const p = placeholderWords();
    if (p && input.placeholder !== p) { input.placeholder = p; input.setAttribute("aria-label", p); }
  }
  KEPT.fitPlaceholder = fitPlaceholder;

  // ---------------------------------------------------------------- the question, above: one quiet pill when it has scrolled away
  /** the newest open ask in the stream (the pill never points past a worker's open ask to an
      older question): the page's question, a worker's ask, the dock's own open ask; the stream is in
      time order, so the newest is the last in the document */
  const OPEN_ASK = ".talk-q, .talk-ask .talk-ask-words, .dock-ask-words:not(.is-answered), .dock-row--ask";
  function newestAskNode() {
    const scroll = KEPT.el && KEPT.el.querySelector(".dock-scroll");
    const all = scroll ? [...scroll.querySelectorAll(OPEN_ASK)].filter((n) => n.isConnected && n.getClientRects().length) : [];
    return all.length ? all[all.length - 1] : $.now.querySelector(".talk-q");
  }
  function aboveWatch() {
    const scroll = KEPT.el && KEPT.el.querySelector(".dock-scroll");
    if (!scroll || !$.above) return;
    if ($.above.parentNode !== scroll || scroll.lastChild !== $.above) scroll.append($.above);
    fitPlaceholder();
    const q = newestAskNode();
    let away = 0;
    if (q && q.isConnected) {
      const r = q.getBoundingClientRect(), b = scroll.getBoundingClientRect(), pill = $.above.hidden ? 0 : $.above.getBoundingClientRect().height;
      // below counts as away until its first words (about two lines) are in sight, not a sliver of its name
      away = r.bottom < b.top + 8 ? -1 : r.top + Math.min(r.height, 56) > b.bottom - pill ? 1 : 0;
    }
    // a worker's ask scrolled away below (the view scrolled up to read) is pointed to as well
    const words = (away > 0 ? "↓ " + t("talk_place.q_below") : "↑ " + t("talk_place.q_above"));
    if (away && $.above.textContent !== words) $.above.textContent = words;
    $.above.hidden = !away;
  }

  // ---------------------------------------------------------------- keepsakes: in the person's own record
  function markNode(kind, title) {
    const m = h("span", { class: "talk-keep", role: "img", "aria-label": t("talk_place.keep_label", { what: title || "" }), title: t("talk_place.keep_label", { what: title || "" }) });
    m.style.backgroundImage = `url("${markFor(kind)}")`;
    return m;
  }
  function cardNameOf(id) { return id && ctx.read.cardName ? ctx.read.cardName(st(), id) : ""; }
  function keepsakes() { return ctx.read.keepsakes ? ctx.read.keepsakes(st()) : []; }
  function keepsakesRow() {
    const k = keepsakes().slice(-KEEPSAKES_MAX);
    const row = h("div", { class: "talk-keepsakes" });
    for (const x of k) {
      row.append(h("figure", { class: "talk-keepsake" }, markNode(x.mark, x.name || cardNameOf(x.card) || x.title),
        (x.name || cardNameOf(x.card)) ? h("figcaption", { class: "dust" }, x.name || cardNameOf(x.card)) : null));
    }
    return [h("p", { class: "eyebrow" }, t("talk_place.keepsakes")),
      k.length ? h("p", { class: "dust" }, t("talk_place.keepsakes_about")) : null,
      k.length ? row : h("p", { class: "dust" }, t("talk_place.keepsakes_none"))];
  }

  // ---------------------------------------------------------------- acts (each from the person's own tap or words)
  /** the line she reads when a card settles: what will happen when the card says so, else her choice */
  function settledText(dc, label, oi) {
    const consequence = Array.isArray(dc.consequences) && dc.consequences[oi] ? dc.consequences[oi] : null;
    return t("talk_place.marked", { option: upper(label) }) + (consequence ? " " + consequence : "");
  }
  function settledNode(d, undo) {
    const mark = d.undone ? null : markNode(d.mark, (d.card && cardNameOf(d.card)) || d.title);
    const rest = h("span", null, d.text);
    const acts = h("p", { class: "talk-settled-acts" });
    if (undo) acts.append(undo);
    const hers = d.card ? cardNameOf(d.card) : "";
    const node = her(hers ? h("p", { class: "talk-settled-q dust", title: d.question ? endSentence(d.question) : "" }, hers)
      : d.question ? h("p", { class: "talk-settled-q dust" }, endSentence(d.question)) : null,
      h("p", { class: "talk-her-line talk-settled-line" }, mark, rest), acts);
    node.classList.add("talk-settled");
    node.dataset.card = d.card || "";
    return { node, mark, rest, acts };
  }
  function answer(dc, label, oi, how, written = false) {
    const t0 = performance.now();
    const a0 = actFor(dc, label);
    const kind = dc.kind || "other";
    const what = nameOfCard(dc) || titleOf(dc);
    // an option that leads somewhere ("Read it now" on a worker's handoff) follows it and says
    // nothing about marking: it opens what was found
    const goes = (dc.go && oi === (dc.go_option != null ? dc.go_option : 0)) || (!dc.go && kind === "handoff" && oi === 0);
    let keepP = null, item = null, parts = null;
    const p = written ? { done: Promise.resolve({ status: "written" }), undo() {} } : ctx.act(a0.type, a0.body, a0.links, dc.holon, {
      confirmed: true, quiet: true, label: t("talk_place.marked_sr", { option: label }),
      onUndo: () => {
        unmarkAnswered(dc.id);
        if (keepP && keepP.undo) keepP.undo();
        SS.set("talk.undos", SS.get("talk.undos", 0) + 1);
        if (item && parts) {
          if (parts.mark) parts.mark.remove();
          parts.acts.textContent = "";
          item.data.text = t("talk_place.undone", { option: label });
          item.data.undone = true;
          parts.rest.textContent = item.data.text;
          persist();
        }
        said("", t("talk_place.undone", { option: label }), { card: dc.id, option: label, undone: true });
        S.awaitNext = false; S.now = null; draw();
      },
    });
    // the turn is let go and the next waits for the quiet before the store speaks, so the redraw its
    // emit causes never deals the next question above this answer
    if (S.now && S.now.kind === "question" && S.now.dc.id === dc.id) S.now = null;
    S.awaitNext = true; S.answeredAt = Date.now(); activeAt = Date.now();
    markAnswered(dc.id);   // the store emits; the Deal's count agrees at once
    S.revealed = true; LS.set("seen_at", Date.now());
    if (goes) {
      said(how === "typed" ? S.lastTyped || "" : "", "", { card: dc.id, option: label, how });
      draw();
      if (dc.go) ctx.go(dc.go); else ctx.openCard(dc.id, { from: "talk" });
      return { ok: true };
    }
    const text = how === "decided" ? t("talk_place.decided", { option: label }) : settledText(dc, label, oi);
    const undo = written ? null : h("button", { class: "link-btn talk-undo", type: "button", onclick: () => p.undo() }, "↺ " + t("deal.undo"));
    // the answered question stays as one quiet line above its answer, where the question was (a tap
    // or a key: its place; her typed words: after them); the next question comes beneath
    const data = { kind: "settled", text, card: dc.id, mark: kind, title: what, question: dc.question || titleOf(dc) || "",
      ...(how === "tap" || how === "key" ? { at: S.qAt && S.qAt.card === dc.id ? S.qAt.at : Date.now() } : {}) };
    parts = settledNode(data, undo);
    item = addTurn(data, parts.node);
    if (how === "typed") KEPT.settled.push({ card: dc.id, option: label, question: dc.question || what });
    p.done.then((q) => {
      if (undo && undo.isConnected && (!q || q.status !== "holding")) undo.remove();
      if (q && q.status === "refused") { unmarkAnswered(dc.id); S.now = null; draw(); }
    });
    // the keepsake: a home-only line in her own record, undone with the answer
    if (!written || !keepsakes().some((x) => x.card === dc.id)) {
      const name = cardNameOf(dc.id) || (ctx.read.card(st(), dc.id) || {}).named || dc.named || null;
      keepP = ctx.act("keepsake", { card: dc.id, title: what, ...(name ? { name } : {}), mark: kind }, {}, ctx.home,
        { confirmed: true, quiet: true, label: "" });
    }
    said(how === "typed" ? S.lastTyped || "" : "", text, { card: dc.id, question: dc.question || what, option: label, how });
    draw();
    study("first_answer_ms", performance.now() - (S.paintedAt || t0));
    SS.set("talk.answered", SS.get("talk.answered", 0) + 1);
    study("answered", SS.get("talk.answered", 0), false);
    return { ok: true };
  }
  /** your agent's act, allowed by the person's Yes on its ask (kind `act`). `written`: the ask's own
      card wrote the Deal's act already, so this marks it answered and says so, with its keepsake, and
      writes no second act; otherwise it settles the card as her tap would. */
  function settleCard({ card, option, index, written = false, decided = false } = {}) {
    if (!card) return { ok: false, reason: t("dock.ask_act_gone") };
    // once per card: a settled line already in the stream is the answer
    if (KEPT.local.some((x) => x.data && x.data.kind === "settled" && x.data.card === card && !x.data.undone)) return { ok: true };
    if (!written && store.answered.has(card)) return { ok: true };
    const dc = deck().open.find((c) => c.id === card) || ((st().deal || {}).cards || []).find((c) => c.id === card && (written || !c.answered));
    if (!dc) return { ok: false, reason: t("dock.ask_act_gone") };
    let i = Number.isInteger(index) && (dc.options || [])[index] === option ? index : (dc.options || []).indexOf(option);
    if (i < 0) i = matchOption(option, dc.options, dc.recommendation, words());
    if (i < 0) return { ok: false, reason: t("dock.ask_act_gone") };
    return answer(dc, dc.options[i], i, decided ? "decided" : "ask", written);
  }
  function sayPage(text, extra = {}, you = "") {
    addTurn({ kind: "page", text, ...extra }, nodeFor({ kind: "page", text, ...extra }));
    said(you, text);
  }
  /** after the quiet: the next card in the hand; at the end of the hand, what is true now (an ask
      still waits, the next hand can come on her word, or nothing needs her) */
  function nextQuestion() {
    S.awaitNext = false;
    S.now = null;
    if (!deck().open.length) {
      const d = deck();
      const bye = allAsks().length ? t("talk_place.next_asks") : d.next > 0 ? t("talk_place.next_more", { count: upper(ctx.fmt.number(d.next, true)) })
        : t("talk_place.next_none") + (isNight() ? " " + t("talk_place.sleep_well") : "");
      const last = KEPT.local[KEPT.local.length - 1];
      if (!(last && last.data && last.data.text === bye)) sayPage(bye);
    }
    draw();
  }
  /** "next": the next card; with the hand played, the next hand the Deal would deal (the same hand) */
  function nextHand() {
    if (!deck().open.length && deck().next) store.hands = (store.hands || 0) + 1;   // this sitting only, as the Deal
    nextQuestion();
  }
  async function startWorker(n) {
    n.status = t("bodies.launch_starting"); draw();
    const r = await ctx.launchBody({ task: n.task, from_card: null, confirmed: true });
    n.started = !!(r && r.ok);
    n.status = r && r.ok ? t("talk_place.task.started") : r && r.reason ? t("talk_place.task.refused", { why: r.reason }) : t("talk_place.task.no_host");
    if (n.started) study("worker_started", 1, false);
    said(n.you, n.status, { worker: n.task });
    draw();
  }

  function whoAnswer() {
    const w = workersOf(st());
    const out = [];
    const item = (x) => x.task ? t("talk_place.who.item", { name: x.name, task: lower(x.task) }) : x.name;
    if (!w.working.length) out.push(w.back.length || w.stopped.length ? t("talk_place.who.none_now") : t("talk_place.who.none"));
    else if (w.working.length === 1) out.push(t("talk_place.who.one", { list: item(w.working[0]) }));
    else out.push(t("talk_place.who.many", { count: ctx.fmt.number(w.working.length), list: w.working.map(item).join("; ") }));
    for (const x of w.back.slice(0, 2)) out.push(t("talk_place.who.back", { name: x.name }));
    for (const x of w.stopped.slice(0, 1)) out.push(x.task ? t("talk_place.who.stopped_on", { name: x.name, task: lower(x.task) }) : t("talk_place.who.stopped", { name: x.name }));
    return out.join(" ");
  }

  /** "what needs me?": the one owed line (the count the Deal says, and the same first), in words;
      the question itself is asked once, on the card that follows, never repeated in this line */
  function needsAnswer() {
    const ol = line();
    const n = owedCount();
    const asks = allAsks().length;
    if (!n) {
      const d = deck();
      const next = d.next > 0 ? t("talk_place.next_more", { count: upper(ctx.fmt.number(d.next, true)) }) : "";
      // an open question of hers comes first; the next hand, when there is one, in the same breath
      if (asks) return next ? t("talk_place.needs.asks") + " " + next : t("talk_place.needs.asks");
      return next || t("talk_place.needs.none");
    }
    // the first thing and the count of the rest in one breath: her agent promised one thing at a time
    const dc = firstOpen();
    const what = lower(nameOfCard(dc) || titleOf(dc) || ol.title).replace(/[.?!]+$/, "");
    const late = dc && stakeOf(dc).late;
    const due = (dc && stakeOf(dc).due) || ol.due;
    const by = late ? t("talk_place.needs.late") : due && ctx.fmt.by && ctx.fmt.by(due) ? ", " + ctx.fmt.by(due) : "";
    const first = what ? t(n === 1 ? "talk_place.needs.one" : "talk_place.needs.first", { what, late: by, by }) : t(n === 1 ? "talk_place.needs.one_plain" : "talk_place.needs.first_plain");
    if (n === 1) return first;
    return first + " " + (n === 2 ? t("talk_place.needs.more_one") : t("talk_place.needs.more_many", { count: upper(ctx.fmt.number(n - 1, true)) }));
  }

  /** "call this one X", "let's call the harvest count X", "name it X": the card she means (the one on
      screen for "this", "it", "that"; else the open card whose title holds her words), named X. */
  function nameFromWords(text) {
    const m = /^(?:(?:ok(?:ay)?|so|and|let'?s|let us|please|i'?ll|i will|we'?ll)[,\s]+)*(?:call|name)\s+(.+?)[.!]?$/i.exec(text.trim());
    if (!m) return false;
    const unq = (x) => x.trim().replace(/^(as\s+)/i, "").replace(/^["“'‘]|["”'’]$/g, "").trim();
    const here = S.now && S.now.kind === "question" ? S.now.dc : firstOpen();
    let dc = null, name = "";
    const self = /^(this one|this card|this|that one|that|it)\s+(.+)$/i.exec(m[1]);
    if (self) { dc = here; name = unq(self[2]); }
    else {
      // "the harvest count The Harvest Run": the longest run of her first words that a card's own words
      // hold is the card; the rest is her name for it
      const ws = m[1].split(/\s+/);
      const pool = [...deck().open, ...((st().deal && st().deal.cards) || [])].filter((c) => c && !c.answered);
      for (let k = ws.length - 1; k >= 1 && !dc; k--) {
        const ref = ws.slice(0, k).join(" ").replace(/^(the|my)\s+/i, "").replace(/\s+(card|one)$/i, "").toLowerCase();
        if (!ref || /^(the|my)$/i.test(ref)) continue;
        const hit = pool.find((c) => (nameOfCard(c) + " " + titleOf(c) + " " + (c.question || "")).toLowerCase().includes(ref));
        if (hit) { dc = hit; name = unq(ws.slice(k).join(" ")); }
      }
    }
    if (!dc || !name || name.length > 60) return false;
    return setNamed({ card: dc.id, name });
  }

  function agentHere() {
    return !!(store.server && mineAll().some((x) => !x.body && x.state !== "offline"));
  }

  // ---------------------------------------------------------------- the line to speak, read first
  function inputOf(target) { return target && target.classList && target.classList.contains("dock-input") ? target : null; }
  function onKeyCapture(e) {
    const inp = inputOf(e.target);
    if (!inp || e.key !== "Enter" || e.shiftKey || e.isComposing) return;
    if (handleLine(inp)) { e.preventDefault(); e.stopPropagation(); }
  }
  function onClickCapture(e) {
    const b = e.target && e.target.closest && e.target.closest(".dock-send");
    if (!b) return;
    const inp = input();
    if (inp && handleLine(inp)) { e.preventDefault(); e.stopPropagation(); }
  }
  function onTyping(e) { if (inputOf(e.target)) { typedAt = Date.now(); activeAt = typedAt; } }

  function reveal() { S.revealed = true; deal(); LS.set("seen_at", Date.now()); S.now = null; draw(); }
  /** she asked for the hand: from here this sitting deals it, one at a time */
  function deal() { S.dealing = true; SS.set("talk.dealing", true); }

  /** True when the line was answered here (the dock does not send it). */
  function handleLine(inp) {
    const text = inp.value.trim();
    if (!text) return false;
    const clear = () => { inp.value = ""; inp.style.height = ""; };
    LS.set("active_at", Date.now());
    // an open ask (her agent's, or a worker's) is answered by her words: yes, no, keep it, not now, start it
    const yn = yesNo(text);
    const ask = yn != null ? newestAsk() : null;
    if (ask) {
      clear(); typedAt = 0;
      addTurn({ kind: "person", text }, you(text));
      answerAsk(ask, yn);
      return true;
    }
    // the knob, by a word: "show me more", "show me less", "show me everything"
    const dw = depthWord(text);
    if (dw) {
      clear(); typedAt = 0;
      addTurn({ kind: "person", text }, you(text));
      if (!dw.same) setDepth(dw.to);
      sayPage(dw.same ? t(dw.more ? "talk_place.depth_said.most" : "talk_place.depth_said.least") : t("talk_place.depth_said." + dw.to), {}, text);
      return true;
    }
    // the page's own worker proposal (no agent here): "yes" starts it, "not now" lets it go
    if (yn != null && S.now && S.now.kind === "worker" && S.now.task && !S.now.status) {
      clear(); addTurn({ kind: "person", text }, you(text));
      if (yn) startWorker(S.now); else { S.now = null; draw(); }
      return true;
    }
    // her own name for a card ("call this one The Harvest Run"): kept at once, so every place the page
    // names that card says it; the line still goes on to her agent
    nameFromWords(text);
    // an answer to the question on screen: settled as a tap would, her words kept in the stream
    if (S.now && S.now.kind === "question") {
      const dc = S.now.dc;
      const i = matchOption(text, dc.options, dc.recommendation, words());
      if (i >= 0) {
        clear(); typedAt = 0;
        addTurn({ kind: "person", text }, you(text));
        S.lastTyped = text;
        answer(dc, dc.options[i], i, "typed");
        study("intent_answer", 1, false);
        return true;
      }
    }
    // no question on screen: her words that are exactly one open card's option (and no other's) settle it
    if (!S.now || S.now.kind !== "question") {
      const hits = deck().open.filter((c) => (c.options || []).some((o) => norm(o) === norm(text)));
      if (hits.length === 1 && norm(text).split(" ").length >= 2) {
        const dc = hits[0], i = dc.options.findIndex((o) => norm(o) === norm(text));
        clear(); typedAt = 0;
        addTurn({ kind: "person", text }, you(text));
        S.lastTyped = text;
        answer(dc, dc.options[i], i, "typed");
        study("intent_answer", 1, false);
        return true;
      }
    }
    let it = intentOf(text, words());
    // a worker is your agent's to propose when it can be reached (the cost said, then its ask card:
    // Start the worker · Not now); the Talk proposes it here only when no agent answers
    if (it && it.kind === "worker" && agentHere()) it = null;
    // "ready" with nothing waiting to be shown is "next", or a line for your agent
    if (it && it.kind === "ready" && S.dealing) it = S.awaitNext || !S.now ? { kind: "next" } : null;
    if (!it) {
      // a line for the agent: the conversation is its own from here
      if (S.now && S.now.kind === "worker") { S.now = null; draw(); }
      if (S.arrival) { S.arrival = null; drawLine(); }
      LS.set("seen_at", Date.now());
      study("first_line_ms", performance.now() - (S.paintedAt || 0));
      toEnd();
      return false;
    }
    clear();
    study("intent_" + it.kind, 1, false);
    addTurn({ kind: "person", text }, you(text));
    if (it.kind === "ready" || it.kind === "deal" || (it.kind === "next" && !S.dealing)) {
      if (!firstOpen()) { sayPage(needsAnswer(), {}, text); deal(); draw(); return true; }
      said(text, ""); reveal(); return true;
    }
    if (it.kind === "next") {
      if (S.now && S.now.kind === "night") S.nightShown = true;
      if (S.now && S.now.kind === "question") { sayPage(t("talk_place.next_here"), {}, text); return true; }   // the question is already here: said so, never silence
      nextHand();
      return true;
    }
    if (it.kind === "needs") {
      sayPage(needsAnswer(), {}, text);
      if (!S.dealing) reveal(); else if (!S.now || S.now.kind === "coming") { S.awaitNext = false; S.now = null; draw(); }
      return true;
    }
    if (it.kind === "who") { sayPage(whoAnswer(), { link: "agents" }, text); return true; }
    if (it.kind === "worker") { S.now = { kind: "worker", you: text, task: it.task }; draw(); }
    return true;
  }

  // ---------------------------------------------------------------- asks, answered in words
  /** yes (true), no (false), or neither (null) */
  function yesNo(text) {
    const n = norm(text);
    if (inList(n, t("talk_place.yes_words")) || inList(n, t("talk_place.ask_yes_words"))) return true;
    if (inList(n, t("talk_place.ask_no_words"))) return false;
    return null;
  }
  /** every open ask in front of her, newest last: her agent's, then each worker's */
  function openAsks() {
    const mine = KEPT.inst && KEPT.inst.openAsks ? KEPT.inst.openAsks().map((a) => ({ a, own: true, at: Date.parse(a.at || "") || 0 })) : [];
    const others = othersAsks().map((a) => ({ a, own: false, at: Number((LS.get("asks_seen", {}) || {})[a.id]) || Date.parse(a.at || "") || 0 }));
    return [...mine, ...others].sort((x, y) => x.at - y.at);
  }
  function newestAsk() { const all = openAsks(); return all.length ? all[all.length - 1] : null; }
  async function answerAsk(x, yes) {
    const r = x.own ? await KEPT.inst.answerAsk(x.a, yes) : await A.answer(x.a.conversation, x.a.id, yes ? "yes" : "not_this").then((q) => ({ ok: q.ok, reason: q.out && q.out.refused }));
    if (r && !r.ok && r.reason) sayPage(r.reason);
    draw();
  }

  // ---------------------------------------------------------------- earlier turns, folded
  function unfold() { S.foldBefore = 0; LS.set("fold_at", 0); $.earlier.hidden = true; refresh(); }

  // ---------------------------------------------------------------- the ten-minute way
  function applyFocus() {
    const on = S.switchUntil && Date.now() < S.switchUntil;
    if (on) document.documentElement.dataset.talkFocus = ""; else delete document.documentElement.dataset.talkFocus;
    clearTimeout(S.focusTimer);
    if (on) S.focusTimer = setTimeout(() => { S.now = null; draw(); }, S.switchUntil - Date.now() + 50);
  }
  function endSwitch(keepIt) {
    study(keepIt ? "switch_kept" : "switch_returned", 1);
    S.switchUntil = keepIt ? Date.now() + SWITCH_MS : 0;
    LS.set("switch_until", S.switchUntil);
    applyFocus();
    S.now = null; draw();
  }

  // ---------------------------------------------------------------- draw
  function drawScene() {
    const w = workersOf(st());
    const dc = firstOpen();
    const src = sceneFor(!!dc, !!(dc && (stakeOf(dc).late || stakeOf(dc).whole)), w.working.length > 0, hour());
    const img = $.scene.firstChild;
    if (img.getAttribute("src") !== src) img.setAttribute("src", src);
  }
  function drawLine() {
    const p = lineParts();
    const key = p.text + (p.ready ? "|ready" : "");
    if ($.line.dataset.key === key) return;
    $.line.dataset.key = key;
    $.line.textContent = p.text;
    if (p.ready) {
      $.line.append(" ", h("button", { class: "talk-ready", type: "button", "aria-label": t("talk_place.ready_label"),
        onclick: () => { said("", t("talk_place.ready")); reveal(); } }, t("talk_place.ready")));
    }
  }
  function draw() {
    if (!el || !ctx) return;
    drawLine();
    const name = herName() || t("talk_place.door_plain");
    if ($.door.dataset.name !== name) {
      $.door.dataset.name = name;
      $.door.textContent = "";
      $.door.append(h("span", { class: "talk-name" }, name));
    }
    drawScene();
    drawAsks();
    chooseNow();
    drawNow();
    refresh();
    $.root.dataset.rest = !firstOpen() ? "true" : "false";
    // everything dealt is answered: the scene dims slowly
    $.root.dataset.done = !firstOpen() && (deck().all || []).length ? "true" : "false";
  }

  // a phone put down and picked up an hour later is a return too: one line of what changed
  function onHide() {
    if (document.visibilityState === "hidden") { snapshot(); return; }
    const was = LS.get("left", null);
    if (was && Date.now() - was.at >= DAY_MS) { S.welcome = true; S.revealed = false; S.foldBefore = was.at; if (calm()) S.now = null; draw(); return; }
    const away = awayLine();
    if (away) { S.arrival = away; S.foldBefore = was ? was.at : Date.now(); draw(); }
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      build();
      restore();
      // a first sitting on this device, or a return after a day: a welcome, and the question waits
      const seen = LS.get("seen_at", 0);
      const mountedAt = Date.now();
      S.welcome = !seen || mountedAt - seen >= DAY_MS;
      if (!S.welcome) S.arrival = awayLine();
      // what was said before this sitting folds above "Earlier": on a welcome, on a return, and after
      // a long quiet; a reload in the middle of a conversation folds nothing and restores it as it was
      const active = LS.get("active_at", 0);
      // the fold opens only on her tap: a remount within the sitting (a crossing of the desk breakpoint,
      // More and back) keeps the sitting's own fold (it never opens itself on her first line)
      if (S.welcome || S.arrival || !active || mountedAt - active >= RESUME_MS) { S.foldBefore = mountedAt; LS.set("fold_at", mountedAt); }
      else S.foldBefore = Number(LS.get("fold_at", 0)) || 0;
      // the same sitting, reloaded: the greeting at the head of the stream says what it first said
      { const g = LS.get("greet", null); S.greetName = !S.welcome && !S.arrival && S.foldBefore && g && g.at === S.foldBefore && typeof g.name === "string" ? g.name : null; }
      activeAt = 0;
      mountConversation();
      draw();
      applyFocus();
      S.tick = setInterval(calmCheck, 500);
      // the page is useful before the agent speaks: the moment the line is on screen
      requestAnimationFrame(() => {
        S.paintedAt = performance.now();
        window.__talk = { paintMs: Math.round(S.paintedAt), question: !!$.now.querySelector(".talk-q"), welcome: S.welcome };
        study("first_question_ms", S.paintedAt);
      });
      document.addEventListener("visibilitychange", onHide);
      addEventListener("pagehide", snapshot);
    },
    update(c) {
      ctx = c;
      draw();
    },
    unmount() {
      snapshot();
      clearInterval(S.tick); clearTimeout(S.focusTimer);
      if (S.busyWatch) S.busyWatch.disconnect();
      document.removeEventListener("visibilitychange", onHide);
      removeEventListener("pagehide", snapshot);
      // the conversation is kept, never unmounted: its stream and its lines wait for the return; this
      // mount's own nodes leave with it, so a remount never finds a second head
      if ($.now) $.now.remove();
      if ($.head) $.head.remove();
      if ($.earlier) $.earlier.remove();
      if ($.above) $.above.remove();
      KEPT.modeSlot = null; KEPT.aboveWatch = null;
      if (KEPT.el) KEPT.el.remove();
      el.textContent = "";
    },
    key(e) {
      if (e.key === "t" || e.key === "T" || e.key === "/") {
        const i = input(); if (i) { i.focus(); return true; }
      }
      if (S.now && S.now.kind === "question" && /^[1-5]$/.test(e.key)) {
        const dc = S.now.dc, i = Number(e.key) - 1, o = (dc.options || [])[i];
        if (o != null) { answer(dc, o, i, "key"); return true; }
      }
      if ((e.key === "n" || e.key === "N") && S.awaitNext) { nextQuestion(); return true; }
      return false;
    },
  };
}
