// bodies.js: the Bodies view, a fold of the Map (DESIGN-BODIES.md, its amendments first;
// DESIGN-THE-BAR §2, the Bodies row).
//
// The person's goal: is my agent awake and well, what is it spending, and does anything need my
// hand. The screen says it directly, in fixed places, top to bottom:
//
//   1. the health line, in the agent's voice ("Awake since 7:02 AM. Three bodies at work, and the
//      prime holds the desk."), with its as-of in dust
//   2. the one lit thing, or nothing: a desk collision or a stale claim, with one act; or the
//      launch card the person asked for (unlit), cost first, Yes where the right thumb is
//   3. a handoff waiting, as one unlit card with its minutes (several coalesce into one)
//   4. the field: the prime's made field turning as fast as it writes, each body a small field on
//      its membrane, its name and what it is on beside it, and one more word only when something
//      differs from normal. Under large type the field gives way to its twin, shown instead.
//   5. the week's usage: one quiet bar per window the plan reports, the day's spend as the fill,
//      the person's ceiling as a hairline, and one line of projection in words
//   6. two quiet acts at the foot: what each body spent (by body, session, model) and every figure
//      (the table, the machine's sleeps, and the printed sheet)
//
//   #/bodies                 the view
//   #/bodies?launch=<card>   the same, with the launch card in place 2 (the Deal's "Give this to a body")
//   #/bodies?task=<words>    the launch card for a task said in the dock
//
// It reads, and never fetches or writes on its own:
//   state.bodies, state.desk, state.cost (day, week, ceiling, limits), state.bodies_closeout
//   state.hud.bodies_live (serve.py, on this machine: newest write, writes in 30 min, heartbeat, usage)
// A line the state cannot support is not shown. Nothing glows, pulses or sounds; the warning colour
// (.is-owed) is spent only on the one fault.

import { h } from "./card.js";
import createDock, { letter } from "./dock.js";
import { talkTo, openWindow, reach as reachOf, handoffText } from "./bodies-talk.js";
import { store } from "./state.js";

// The made frame of a person's field and its geometry (hud/art/;
// the same measures map.js uses). Facts about the image, not design values.
const FRAME = { src: "art/b-field-person-c.jpg", hole: [0.5, 0.48], rx: 0.37, ry: 0.2 };
const SVGNS = "http://www.w3.org/2000/svg";
const OPEN = new Set(["claimed", "working", "hold", "handoff"]);
const WEEK_MS = 7 * 86400000;

function ensureCss(href) {
  if (document.querySelector(`link[rel="stylesheet"][href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet"; link.href = href;
  const before = document.querySelector('link[href="print.css"]');
  if (before) before.before(link); else document.head.append(link);
}
function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function ms(name) {
  const v = cssVar(name);
  return v.endsWith("ms") ? parseFloat(v) : v.endsWith("s") ? parseFloat(v) * 1000 : parseFloat(v) || 0;
}
function s(tag, attrs) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  return el;
}
/** A stable place in [0, 1) for an id, so a body is always born at the same point. */
function unit(id, salt = 0) {
  let x = 2166136261 ^ salt;
  for (const ch of String(id)) { x ^= ch.charCodeAt(0); x = Math.imul(x, 16777619); }
  return ((x >>> 0) % 100000) / 100000;
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const num = (v) => (typeof v === "number" && isFinite(v) ? v : null);

// The made frame cut from its night by its own light (map.js's method): once, at load, its
// luminance becomes an alpha mask, so only the engraved lines remain. Grades the still; draws nothing.
let MASK = null, MASK_P = null;
function prepareMask() {
  if (MASK_P) return MASK_P;
  MASK_P = new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      try {
        const c = document.createElement("canvas");
        c.width = img.naturalWidth; c.height = img.naturalHeight;
        const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(img, 0, 0);
        const d = g.getImageData(0, 0, c.width, c.height), px = d.data;
        const lo = 0.13, hi = 0.42;
        for (let i = 0; i < px.length; i += 4) {
          const lum = (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
          let a = (lum - lo) / (hi - lo);
          a = a <= 0 ? 0 : a >= 1 ? 1 : a * a * (3 - 2 * a);
          px[i] = px[i + 1] = px[i + 2] = 0; px[i + 3] = Math.round(a * 255);
        }
        g.putImageData(d, 0, 0);
        c.toBlob((b) => { MASK = b ? URL.createObjectURL(b) : null; resolve(MASK); }, "image/png");
      } catch { resolve(null); }
    };
    img.onerror = () => resolve(null);
    img.src = FRAME.src;
  });
  return MASK_P;
}
function maskStyle() {
  return MASK ? `mask-image:url("${MASK}");-webkit-mask-image:url("${MASK}");mask-mode:alpha;`
    : `mask-image:url("${FRAME.src}");-webkit-mask-image:url("${FRAME.src}");mask-mode:luminance;`;
}

// ------------------------------------------------------------------ words

function W(ctx) {
  const t = ctx.t, f = ctx.fmt;
  const minutesAgo = (x) => { const d = f.date(x); return d ? Math.max(0, Math.round((f.now() - d) / 60000)) : null; };
  return {
    /** tokens in words, or null when there is no figure */
    tokens(n) {
      if (num(n) == null) return null;
      if (n <= 0) return t("bodies.tokens_none");
      if (n < 1000) return t("bodies.tokens_few");
      if (n < 1e6) { const k = n >= 1e5 ? Math.round(n / 1e4) * 10 : Math.round(n / 1e3); return t("bodies.tokens_thousand", { n: k }); }
      const m = n / 1e6;
      return t("bodies.tokens_million", { n: m >= 10 ? String(Math.round(m)) : String(Math.round(m * 10) / 10) });
    },
    money(v, unitWord) {
      if (num(v) == null) return null;
      if (unitWord && unitWord !== "dollars") return t("bodies.money_other", { n: Math.round(v), unit: unitWord });
      if (v < 1) return t("bodies.money_less");
      const n = Math.round(v);
      return n === 1 ? t("bodies.money_one") : t("bodies.money", { n: f.number(n, true) });
    },
    /** "4 minutes ago", "since 1:20 PM", "since yesterday"; null when unknown */
    newest(x) {
      const m = minutesAgo(x);
      if (m == null) return null;
      if (m < 1) return t("bodies.ago_now");
      if (m === 1) return t("bodies.ago_one");
      if (m < 60) return t("bodies.ago_minutes", { n: m });
      if (f.sameDay(f.date(x), f.now())) return t("bodies.since_time", { time: f.time(x) });
      return t("bodies.since_when", { when: f.when(x) });
    },
    minutesAgo,
    time: (x) => f.time(x) || "",
    count(n) { return n === 1 ? t("bodies.h.one_work") : n === 0 ? t("bodies.h.none_work") : t("bodies.h.n_work", { n: f.number(n) }); },
  };
}

// ------------------------------------------------------------------ reading the state

/** Every body of today, the state's fold joined to the machine's live reading. */
/** Before the record has folded any body, what this machine itself sees: the prime by its
    heartbeat, and each body folder by its name, newest write and process. Never more. */
function fromLive(ctx, lb) {
  if (!lb || (!lb.heartbeat && !(Array.isArray(lb.bodies) && lb.bodies.length))) return null;
  const hb = lb.heartbeat || {};
  const out = [{ name: "the prime", actor: "prime", kind: "prime", state: "working", newest_line: hb.last || null, task: null, flags: [] }];
  for (const x of lb.bodies || []) {
    const name = String(x.name || "");
    out.push({ name: name.charAt(0).toUpperCase() + name.slice(1), actor: x.actor || name, kind: "clone",
      state: x.process === "gone" ? "stale" : "working", claimed_at: x.claimed_at || null, newest_line: null, task: null,
      lines_30m: 0, flags: [], from_live: true });
  }
  return out;
}

/** This machine's own bodies, read by serve.py from the house's files and the process table
    (hud.bodies_live.machine): the prime always first, alive or not; each background body with its
    task, its newest write and what it last said; the dock and any other window apart, never as
    fields; the finished folded away. Every age is taken against the machine's own clock (as_of),
    never the page's, so a sample's clock cannot age a live body. */
function fromMachine(ctx, lb) {
  if (!lb || !Array.isArray(lb.machine)) return null;
  const mnow = ctx.fmt.date(lb.as_of) || ctx.fmt.now();
  const writes = new Map((lb.bodies || []).map((x) => [String(x.name || "").toLowerCase(), x.writes_30m || 0]));
  const ageMin = (x) => (num(x.newest_age_s) != null ? Math.round(x.newest_age_s / 60) : null);
  const bodies = [], others = [];
  let archivedN = 0;
  for (const x of lb.machine) {
    const subs = Array.isArray(x.subagents) ? x.subagents.filter((a) => a && a.running) : [];
    if (x.kind === "prime") {
      bodies.unshift({ name: "the prime", actor: "prime", kind: "prime", state: x.alive ? "working" : "stale",
        alive: !!x.alive, holds_desk: !!x.holds_desk, desk_holder: x.desk_holder || null, since: x.since || null,
        claimed_at: x.started || null, newest_line: x.newest_write || null, quiet_min: ageMin(x), task: null,
        flags: [], subagents: subs, from_machine: true, mnow, window: !!x.window, spent: x.spent_today || null });
    } else if (x.kind === "background" && x.folder) {
      const st = x.state === "running" ? "working" : x.state === "stale" ? "stale" : x.state === "elsewhere" ? "working" : "archived";
      if (st === "archived") archivedN++;
      bodies.push({ name: x.name, actor: "body:" + String(x.name).toLowerCase(), kind: "clone", state: st, alive: !!x.alive,
        host: x.state === "elsewhere" ? (x.host || "elsewhere") : null, task: x.task || null, claimed_at: x.started || null,
        newest_line: x.newest_write || null, quiet_min: ageMin(x), status_last: x.status_last || null,
        lines_30m: writes.get(String(x.folder).toLowerCase()) || 0, handoff_present: !!(x.handoff && x.handoff.present),
        status_lines: Array.isArray(x.status_lines) ? x.status_lines : null,
        // a handoff on this machine: waiting until the person's own witness line names it (serve.py's fold)
        handoff: x.handoff && x.handoff.present ? (x.handoff.card || "file") : null, handoff_card: (x.handoff && x.handoff.card) || null,
        handoff_bytes: x.handoff ? x.handoff.bytes : null, folder: x.folder,
        reviewed: !!(x.handoff && x.handoff.reviewed), handoff_archived: !!(x.handoff && x.handoff.reviewed === "archived"),
        review_min: x.handoff && x.handoff.review_min != null ? x.handoff.review_min : null,
        spent: x.spent_today || null,
        flags: [], subagents: subs, from_machine: true, mnow, window: !!x.window });
    } else {
      others.push({ name: x.name, kind: x.kind, pid: x.pid ?? null, started: x.started || null, task: x.task || null, subagents: subs, window: !!x.window, spent: x.spent_today || null });
    }
  }
  if (!bodies.length || bodies[0].kind !== "prime") return null;
  const loose = (lb.house_helpers || []).filter((a) => a && a.running);
  return { bodies, others, archivedN, loose, mnow };
}

/** The bodies started from the ICE (agent_host.py's POST /body): running on this computer through
    the agent host, with no terminal window. Their state is the host's own, never a folder's. */
function hostedOf(ctx) {
  const st = ctx.state;
  return ((st.hud && st.hud.agents) || []).filter((a) => a && a.body && a.of === st.actor).map((a) => {
    const running = ["waking", "ready", "thinking", "waiting"].includes(a.state);
    return { name: a.body.name || a.name, actor: "body:" + String(a.body.name || a.name).toLowerCase(), kind: "clone", hosted: true,
      agentId: a.id, agentState: a.state, state: running ? "working" : "stale", alive: running, task: a.body.task || null,
      claimed_at: a.body.started || null, newest_line: null, flags: [], subagents: [], spent: a.body.spent_today || null };
  });
}

/** The line when no body folder is read: true to the record. When your own agent is here (the
    host's agents, or a conversation it has had), it says so; only with no agent at all does it wait
    for the first lines (never "no agent has written yet" while one has). */
function emptyLine(ctx) {
  const st = ctx.state || {}, t = ctx.t;
  const mineA = ((st.hud && st.hud.agents) || []).filter((a) => a && a.of === st.actor && a.kind !== "guest");
  const spoke = ((st.hud && st.hud.dock && st.hud.dock.conversations) || []).some((c) => mineA.some((a) => a.id === c.agent));
  if (!mineA.length && !spoke) return t("bodies.missing");
  const name = mineA[0] && mineA[0].name;
  return name ? t("bodies.no_workers_named", { name }) : t("bodies.no_workers");
}

function model(ctx) {
  const st = ctx.state, now = ctx.fmt.now();
  const liveB = st.hud && st.hud.bodies_live;
  const machine = !(Array.isArray(st.bodies) && st.bodies.length) ? fromMachine(ctx, liveB) : null;
  let folded = machine ? machine.bodies
    : Array.isArray(st.bodies) && st.bodies.length ? st.bodies : fromLive(ctx, liveB);
  if (!folded) return null;
  const hosted = hostedOf(ctx);
  if (hosted.length) {   // a hosted body's folder (if it wrote one) is the same body: the host's state wins, the folder's handoff is kept
    const byName = new Map(hosted.map((x) => [String(x.name).toLowerCase(), x]));
    folded = folded.map((b) => {
      const x = b.kind !== "prime" && byName.get(String(b.name).toLowerCase());
      if (!x) return b;
      byName.delete(String(b.name).toLowerCase());
      return { ...b, ...x, handoff: b.handoff, handoff_card: b.handoff_card, handoff_bytes: b.handoff_bytes, folder: b.folder,
        reviewed: b.reviewed, handoff_archived: b.handoff_archived, review_min: b.review_min, from_machine: b.from_machine, mnow: b.mnow };
    }).concat([...byName.values()]);
  }
  const liveBlock = st.hud && st.hud.bodies_live;
  const live = (liveBlock && Array.isArray(liveBlock.bodies)) ? liveBlock.bodies : [];
  const words = W(ctx);
  const hb = liveBlock && liveBlock.heartbeat;
  const out = folded.map((b) => {
    const lv = live.find((x) => x.actor && x.actor === b.actor)
      || live.find((x) => x.name && String(x.name).toLowerCase() === String(b.name).toLowerCase()) || null;
    const elsewhere = !!(b.host && b.host !== "this machine" && b.kind !== "prime");
    let gone = false;
    if (b.kind === "prime") gone = !!(hb && hb.open && hb.open.kind === "stopped");
    else if (!elsewhere && lv) gone = lv.process === "gone";
    const times = [b.newest_line, lv && lv.newest_write].filter(Boolean).map((x) => ctx.fmt.date(x)).filter(Boolean);
    const newest = times.length ? new Date(Math.max(...times)).toISOString() : null;
    const writes = (b.kind === "prime" ? (b.lines_1h ?? null) : null) ?? (((lv && lv.writes_30m) || 0) + (b.lines_30m || 0));
    const quietMin = b.quiet_min != null ? b.quiet_min : words.minutesAgo(newest);
    let word;
    if (b.state === "archived") word = "archived";
    else if (b.state === "stale" || (gone && OPEN.has(b.state) && b.state !== "hold")) word = "stale";
    else if (b.state === "hold") word = "held";
    else if (b.state === "done") word = "done";
    else if (b.state === "handoff") word = "handoff";
    else if (quietMin != null && quietMin > 60) word = "quiet";
    else word = "work";
    let age = b.age_hours;
    if (age == null && b.claimed_at) { const d = ctx.fmt.date(b.claimed_at); if (d) age = (now - d) / 3600000; }
    const flags = new Set(b.flags || []);
    const waitingHandoff = !!(b.handoff && !b.reviewed);
    const handoffDay = waitingHandoff && (flags.has("handoff_day") || (() => {
      const ln = (st.lines || []).find((l) => l.id === b.handoff);
      const d = ln && ctx.fmt.date(ln.ts);
      return d ? (now - d) >= 86400000 : false;
    })());
    const endedAt = (lv && (lv.ended_at || lv.newest_write)) || b.newest_line || null;
    return { ...b, live: lv, newest, writes, quietMin, word, age, flags, waitingHandoff, handoffDay, elsewhere, endedAt };
  });
  const prime = out.find((b) => b.kind === "prime") || null;
  const clones = out.filter((b) => b.kind !== "prime" && b.word !== "archived");
  clones.sort((a, b) => String(b.claimed_at || "").localeCompare(String(a.claimed_at || "")));
  const archived = out.filter((b) => b.kind !== "prime" && b.word === "archived");
  if (machine) {   // running first, then on another machine, then the stopped
    const rank = (b) => (b.word === "stale" ? 2 : b.elsewhere ? 1 : 0);
    clones.sort((a, b) => rank(a) - rank(b) || String(b.claimed_at || "").localeCompare(String(a.claimed_at || "")));
  }
  return { prime, clones, archived, all: out, live: liveBlock || null, machine };
}

/** A moment in words against the machine's clock: "11:38 AM", "yesterday at 9:10 PM",
    "Thursday at 11:38 AM", "on 20 September". */
function whenM(ctx, x, mnow) {
  const f = ctx.fmt, d = f.date(x);
  if (!d) return "";
  const n = mnow || f.now(), days = f.daysBetween(d, n);
  if (days <= 0) return f.time(x) || "";
  if (days === 1) return ctx.t("bodies.m.yesterday_at", { time: f.time(x) });
  if (days < 7) return ctx.t("bodies.m.day_at", { day: f.dayName(d), time: f.time(x) });
  return ctx.t("bodies.m.on_date", { date: d.toLocaleDateString(undefined, { month: "long", day: "numeric" }) });
}
/** How long, in figures: "12 min", "3 h 10". */
function spanM(ctx, x, mnow) {
  const d = ctx.fmt.date(x);
  if (!d) return null;
  const m = Math.max(0, Math.round(((mnow || ctx.fmt.now()) - d) / 60000));
  return m < 60 ? ctx.t("bodies.m.span_min", { n: m }) : ctx.t("bodies.m.span_h", { h: Math.floor(m / 60), m: String(m % 60).padStart(2, "0") });
}
/** "4 minutes ago", "at 1:20 PM", "on 20 September", from minutes or a moment. */
function wroteM(ctx, b, mnow) {
  const m = b.quietMin;
  if (m == null) return null;
  if (m < 1) return ctx.t("bodies.ago_now");
  if (m === 1) return ctx.t("bodies.ago_one");
  if (m < 60) return ctx.t("bodies.ago_minutes", { n: m });
  const d = ctx.fmt.date(b.newest);
  if (d && ctx.fmt.daysBetween(d, mnow || ctx.fmt.now()) <= 0) return ctx.t("bodies.m.at_time", { time: ctx.fmt.time(b.newest) });
  return whenM(ctx, b.newest, mnow);
}

function nameOf(ctx, b) { return b.kind === "prime" ? ctx.t("bodies.the_prime") : b.name; }
/** The name on the first screen, in the person's words: "your agent", never "the prime". */
function faceName(ctx, b, cap) { return b.kind === "prime" ? ctx.t(cap ? "bodies.face.agent_cap" : "bodies.face.agent") : b.name; }
function byActor(M, actor) { return M.all.find((b) => b.actor === actor) || null; }

/** The turning: one revolution per (1800 / writes) seconds, held between 60 and 600, the Map's
    own mapping (DESIGN §4.4) applied to a body's writes. 0 = still. */
function turnSeconds(n) {
  if (n == null || isNaN(n) || n <= 0) return 0;
  return clamp(1800 / n, 60, 600);
}

/** The plan's windows, from the engine's `cost.limits`, else the machine's live reading. */
function windows(ctx) {
  const st = ctx.state, c = st.cost || {}, lim = c.limits, u = st.hud && st.hud.bodies_live && st.hud.bodies_live.usage;
  const ceil = c.ceiling || {};
  let seven = null, five = null, asOf = null;
  if (lim && (num(lim.seven_day_used_pct) != null || num(lim.five_hour_used_pct) != null)) {
    const r = lim.resets_at || {};
    if (num(lim.seven_day_used_pct) != null) seven = { used: lim.seven_day_used_pct, resets: r.seven_day || null };
    if (num(lim.five_hour_used_pct) != null) five = { used: lim.five_hour_used_pct, resets: r.five_hour || null };
    asOf = lim.as_of || (u && u.as_of) || null;
    if (num(lim.ceiling_pct) != null && seven) seven.ceiling = lim.ceiling_pct;
  } else if (u) {
    if (u.seven_day && num(u.seven_day.used_pct) != null) seven = { used: u.seven_day.used_pct, resets: u.seven_day.resets_at || null };
    if (u.five_hour && num(u.five_hour.used_pct) != null) five = { used: u.five_hour.used_pct, resets: u.five_hour.resets_at || null };
    asOf = u.as_of || null;
  }
  if (seven && num(ceil.seven_day_pct) != null) seven.ceiling = ceil.seven_day_pct;
  if (five && num(ceil.five_hour_pct) != null) five.ceiling = ceil.five_hour_pct;
  if (seven) {
    // the day's share of the week's use, in the route lines' own proportion
    const sum = (x) => x ? (num(x.tokens) != null ? x.tokens
      : Object.values(x.by_body || {}).reduce((a, b) => a + (b || 0), 0) + (x.unattributed || 0)) : null;
    const d = sum(c.day), wk = sum(c.week);
    if (d != null && wk) seven.today = seven.used * clamp(d / wk, 0, 1);
    // where the week is heading at this pace (the level-3 fact): use so far over the share of the window gone
    const r = ctx.fmt.date(seven.resets);
    if (r) {
      const gone = 1 - (r - ctx.fmt.now()) / WEEK_MS;
      if (gone > 0.05 && gone < 1) seven.pace = seven.used / gone;
    }
  }
  return seven || five ? { seven, five, asOf } : null;
}

// ------------------------------------------------------------------ the view

// What the room had chosen, kept for this page's life, so a remount by the shell (a change of
// theme, of type, of layout) comes back to the same body.
const KEPT = { chosen: null };
// Each terminal body's conversation as received, kept for this page's life (so the
// view never freezes on return): its lines, the transcript line to resume from, and its mounted element, so
// leaving Bodies and coming back reattaches what was drawn and asks the server only for what is new.
const TERMS = new Map();          // entry key -> the conversation object (see mountConv)
const TURNS_SHOWN = 40;           // the last forty turns are drawn; "Earlier" draws forty more

export default function createBodies() {
  let el, ctx, root, ro = null, width = 0;
  const anims = new Map();        // actor -> {anim, secs}
  const angles = new Map();       // actor -> degrees reached, so a change of pace never jumps
  let seen = null;                // actors drawn last time (for birth and archiving)
  let lastStates = new Map();
  let launchFor = null, launchClosed = false, rewardTimer = null;
  const said = new Map();         // fault key -> words said, after the person's act
  let room = null;                // the room's parts: rail, slot, head, conv, paper
  let chosen = KEPT.chosen;       // the rail entry chosen: "prime", "body:<name>", "agent:<id>", "window:<…>", "glance", "archive"
  let conv = null;                // the conversation mounted for the chosen entry, kept across redraws
  let handoffOpen = null;         // the entry whose handoff is open in the page, as text in Plain
  let routeSig = null;            // the route's ?body=&handoff= last applied (the Deal's "Read it now")
  const localReviewed = new Map();  // handoff card -> "read" | "archived": the person's own tap, until the server folds it
  let pendingChoose = null;       // a body just started from Give a task: chosen when it reaches the rail
  ensureCss("dock.css");
  ensureCss("bodies.css");

  function keepAngles() {
    for (const [actor, a] of anims) {
      try {
        const ct = a.anim.currentTime || 0;
        angles.set(actor, ((angles.get(actor) || 0) + (ct / (a.secs * 1000)) * 360) % 360);
        a.anim.cancel();
      } catch { /* gone */ }
    }
    anims.clear();
  }

  // ---------------------------------------------------------------- the room (DESIGN-BODIES §13)
  // The bodies sit on a rail; the one chosen fills the page as its conversation. The rail and the
  // page head are drawn again on every change of the state; the conversation is mounted once per
  // chosen body and kept, so a line half typed and the stream it reads survive every redraw.
  const focusKey = () => { const a = document.activeElement; return a && root && root.contains(a) && a.dataset ? a.dataset.fk || null : null; };
  const refocus = (k) => { if (!k) return; const n = root.querySelector(`[data-fk="${CSS.escape(k)}"]`); if (n) n.focus({ preventScroll: true }); };

  function draw() {
    keepAngles();
    const t = ctx.t;
    const M = model(ctx);
    readLaunch();
    if (!M) {
      destroyConv(); room = null;
      root.textContent = "";
      root.append(h("h1", { class: "sr-only" }, t("bodies.title")));
      const head = h("div", { class: "bodies-health" }, h("p", { class: "bodies-line voice" }, ctx.loading ? t("app.reading") : emptyLine(ctx)));
      root.append(head);
      const lc = launchCard(); if (lc) root.append(h("div", { class: "bodies-slot" }, lc));
      return;
    }
    const fk = focusKey();
    ensureRoom();
    const E = entries(M);
    const rp = ctx.route && ctx.route.params;
    const want = rp && rp.get("body"), wantHo = !!(rp && rp.get("handoff"));
    const sig = want ? want + "|" + (wantHo ? 1 : 0) : null;
    if (sig && sig !== routeSig) {      // asked for by the route (the Deal's "Read it now"): applied once
      routeSig = sig;
      const w = want.toLowerCase();
      const hit = E.find((e) => e.talk && String(e.talk).toLowerCase() === w)
        || (M.archived.find((b) => String(b.name).toLowerCase() === w || String(b.folder || "").toLowerCase() === w) ? { key: "body:" + w } : null);
      if (hit) { chosen = KEPT.chosen = hit.key; if (wantHo) handoffOpen = hit.key; }
    }
    if (pendingChoose) {
      const hit = E.find((e) => e.b && e.b.hosted && String(e.b.name).toLowerCase() === pendingChoose);
      if (hit) { chosen = KEPT.chosen = hit.key; pendingChoose = null; }
    }
    if (!chosen) chosen = E.length ? E[0].key : "glance";
    if (chosen !== "glance" && chosen !== "archive" && !E.find((e) => e.key === chosen)) {
      const arch = M.archived.find((b) => "body:" + String(b.name).toLowerCase() === chosen);
      if (!arch) chosen = E.length ? E[0].key : "glance";
    }
    renderRail(M, E);
    renderPage(M, E);
    room.paper.textContent = "";
    room.paper.append(paper(M));
    seen = new Set(M.all.map((b) => b.actor));
    lastStates = new Map(M.all.map((b) => [b.actor, b.word]));
    refocus(fk);
    requestAnimationFrame(fit);
  }

  function ensureRoom() {
    if (room && room.wrap.isConnected) return;
    root.textContent = "";
    const t = ctx.t;
    room = {};
    room.rail = h("nav", { class: "bodies-rail", "aria-label": t("bodies.room.rail_label") });
    room.slot = h("div", { class: "bodies-slot" });
    room.head = h("header", { class: "bodies-page-head" });
    room.conv = h("div", { class: "bodies-conv" });
    room.page = h("section", { class: "bodies-page", "aria-live": "off" }, room.slot, room.head, room.conv);
    room.wrap = h("div", { class: "bodies-room" }, room.rail, room.page);
    room.paper = h("div", { class: "bodies-paper-box" });
    root.append(h("h1", { class: "sr-only" }, t("bodies.title")), room.wrap, room.paper);
  }

  /** The room fills the height that is left under the frame, so the conversation scrolls inside it. */
  function fit() {
    if (!room || !room.wrap.isConnected) return;
    const phone = innerWidth < 760;
    const top = (phone ? room.page : room.wrap).getBoundingClientRect().top + window.scrollY;
    const foot = phone ? 56 + 16 : 24;
    root.style.setProperty("--room-h", Math.max(360, Math.round(innerHeight - top - foot)) + "px");
  }

  /** Every entry of the rail, in its one order: the prime; the running, newest last; the dock's
      agent and other windows; the stopped. Each knows what it is called on the talk interface. */
  function entries(M) {
    const st = ctx.state, E = [];
    if (M.prime) E.push({ key: "prime", kind: "prime", group: "prime", b: M.prime, talk: "prime", window: !!M.prime.window });
    const byStart = (a, b) => String(a.claimed_at || "").localeCompare(String(b.claimed_at || ""));
    for (const b of M.clones.filter((x) => x.word !== "stale").sort(byStart)) {
      E.push({ key: "body:" + String(b.name).toLowerCase(), kind: "clone", group: "running", b, talk: b.name, window: !!b.window });
    }
    const others = (M.machine && M.machine.others) || [];
    const docks = others.filter((o) => o.kind === "dock");
    const mine = ((st.hud && st.hud.agents) || []).filter((a) => a && a.of === st.actor && a.kind !== "guest" && !a.body);
    mine.forEach((a, i) => E.push({ key: "agent:" + a.id, kind: "dock", group: "open", agent: a, o: docks[i] || null }));
    if (!mine.length) docks.forEach((o, i) => E.push({ key: "dock:" + i, kind: "dock", group: "open", agent: null, o }));
    for (const o of others.filter((x) => x.kind !== "dock")) {
      const talk = o.name || "window";
      E.push({ key: "window:" + talk + ":" + (o.pid != null ? o.pid : o.started || ""), kind: "window", group: "open", o, talk, window: !!o.window });
    }
    for (const b of M.clones.filter((x) => x.word === "stale").sort(byStart)) {
      E.push({ key: "body:" + String(b.name).toLowerCase(), kind: "clone", group: "stopped", b, talk: b.name, window: !!b.window });
    }
    return E;
  }

  /** The first meaningful line of a task, short enough for one line of the rail. */
  function firstLine(task, max = 96) {
    const line = String(task || "").split("\n").map((x) => x.replace(/^[#>*\-\s]+/, "").replace(/[*_`]/g, "").trim()).find(Boolean) || "";
    if (line.length <= max) return line;
    const cut = line.lastIndexOf(" ", max - 4);
    return line.slice(0, cut > 40 ? cut : max - 4) + "…";
  }
  function subsOf(e) { return ((e.b && e.b.subagents) || (e.o && e.o.subagents) || []).length; }
  function subsWords(n) { return n === 1 ? ctx.t("bodies.room.subs_one") : n > 1 ? ctx.t("bodies.room.subs_n", { n: ctx.fmt.number(n, true) }) : null; }
  function mnowOf(M) { return (M.machine && M.machine.mnow) || ctx.fmt.now(); }

  function entryName(e) {
    const t = ctx.t;
    if (e.kind === "prime") return t("bodies.m.prime");
    if (e.kind === "dock") return (e.agent && e.agent.name) || t("bodies.m.dock");
    if (e.kind === "window") return e.o.kind === "background" && e.o.name ? e.o.name : t("bodies.m.window");
    return e.b.name;
  }

  /** The state in a word or two, for the rail: "Running · wrote 2 minutes ago". */
  function entryState(e, M) {
    const t = ctx.t, mnow = mnowOf(M);
    if (e.kind === "prime") {
      const P = e.b;
      if (P.alive === false || P.word === "stale") return t("bodies.m.not_running");
      const w = wroteM(ctx, P, mnow);
      return [t("bodies.m.running"), w ? t("bodies.room.wrote", { when: w }) : null].filter(Boolean).join(" · ");
    }
    if (e.kind === "dock" || e.kind === "window") {
      const st = e.agent && e.agent.state && ["waiting", "waking", "thinking"].includes(e.agent.state) ? t("bodies.room.agent." + e.agent.state) : null;
      const open = e.o && e.o.started ? t("bodies.m.open_since", { when: whenM(ctx, e.o.started, mnow) }) : null;
      return [st, open].filter(Boolean).join(" · ") || t("bodies.room.beside_every_view");
    }
    const b = e.b, w = wroteM(ctx, b, mnow);
    const ho = handoffWords(b);
    if (b.hosted) {
      const st = ["waiting", "waking", "thinking"].includes(b.agentState) ? t("bodies.room.agent." + b.agentState) : null;
      return [b.word === "stale" ? t("bodies.m.not_running") : st || t("bodies.m.running"), ho].filter(Boolean).join(" · ");
    }
    if (b.word === "stale") return [t("bodies.m.stopped_wrote", { when: w || "" }), ho].filter(Boolean).join(" · ");
    if (b.elsewhere) return t("bodies.w.elsewhere");
    return [b.word === "quiet" ? t("bodies.room.quiet") : t("bodies.m.running"), w ? t("bodies.room.wrote", { when: w }) : null, ho].filter(Boolean).join(" · ");
  }

  /** A machine body's handoff in a few words: waiting, read, or set aside; nothing when none. */
  function handoffWords(b) {
    if (!b || !b.from_machine || !b.handoff) return null;
    const t = ctx.t, here = b.handoff_card ? localReviewed.get(b.handoff_card) : null;
    if (!b.reviewed && !here) return t("bodies.room.handoff_waits");
    return t(b.handoff_archived || (!b.reviewed && here === "archived") ? "bodies.room.handoff_archived" : "bodies.room.handoff_read");
  }

  /** What one body spent today, as one quiet figure: "$0.42 today", "12K units of work today", or
      "not counted". Never a guess (serve.py: the cost ledger, else the body's own transcript). */
  function spentWords(x) {
    const t = ctx.t;
    if (x && typeof x.usd === "number") return t("bodies.cost.today", { figure: money2(x.usd) });
    if (x && typeof x.tokens === "number" && x.tokens > 0) return t("bodies.cost.today", { figure: t("bodies.cost.units", { n: compact(x.tokens) }) });
    return t("bodies.cost.none");
  }
  function money2(v) { try { return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(v); } catch { return "$" + v.toFixed(2); } }
  function compact(n) { try { return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n); } catch { return String(n); } }
  function spentOf(e) { return (e.b && e.b.spent) || (e.o && e.o.spent) || (e.agent && e.agent.body && e.agent.body.spent_today) || null; }

  function deskWords(P, mnow) {
    const t = ctx.t;
    if (P.holds_desk) return P.since ? t("bodies.m.holds_since", { when: whenM(ctx, P.since, mnow) }) : t("bodies.m.holds");
    if (P.desk_holder) return t("bodies.m.desk_with", { holder: P.desk_holder });
    const d = ctx.state.desk;
    if (d && d.holder === P.actor) return t("bodies.m.holds");
    return P.from_machine ? t("bodies.m.desk_none") : null;
  }

  function choose(key) {
    if (chosen === key) return;
    chosen = KEPT.chosen = key;
    draw();
    // on the phone the chosen chip is brought into the strip's view
    requestAnimationFrame(() => { const c = room && room.rail.querySelector(".br.is-chosen"); if (c && c.scrollIntoView && innerWidth < 760) c.scrollIntoView({ block: "nearest", inline: "nearest" }); });
  }

  function renderRail(M, E) {
    const t = ctx.t, mnow = mnowOf(M);
    const rail = room.rail;
    rail.textContent = "";
    rail.append(h("div", { class: "bodies-rail-head" },
      h("h2", { class: "eyebrow" }, t("bodies.room.rail_title")),
      h("button", { class: "link-btn bodies-give-link", type: "button", "data-fk": "give", onclick: giveTask }, t("bodies.give.act")),
      h("button", { class: "link-btn bodies-glance-link" + (chosen === "glance" ? " is-chosen" : ""), type: "button", "data-fk": "glance",
        "aria-current": chosen === "glance" ? "true" : null, onclick: () => choose("glance") }, t("bodies.room.at_a_glance"))));
    const ul = h("ul", { class: "bodies-rail-list" });
    let group = null;
    for (const e of E) {
      if (e.group !== group) {
        group = e.group;
        if (group === "open") ul.append(h("li", { class: "bodies-rail-group" }, t("bodies.room.also_open")));
        if (group === "stopped") ul.append(h("li", { class: "bodies-rail-group" }, t("bodies.room.stopped")));
      }
      const n = subsOf(e);
      const isChosen = chosen === e.key;
      const cls = ["br", "br--" + e.kind, e.group === "stopped" ? "br--stopped" : "", isChosen ? "is-chosen" : ""].filter(Boolean).join(" ");
      const nameEl = e.kind === "prime" ? h("span", { class: "br-name caps" }, entryName(e)) : h("span", { class: "br-name" }, entryName(e));
      const lines = [];
      if (e.kind === "prime") { const dw = deskWords(e.b, mnow); if (dw) lines.push(h("span", { class: "br-task" }, dw)); }
      else if (e.b && e.b.task) lines.push(h("span", { class: "br-task" }, firstLine(e.b.task)));
      lines.push(h("span", { class: "br-state" }, entryState(e, M)));
      // what it spent today, one quiet figure (only where this computer can count it: the room, not a file)
      if (M.machine || (e.b && e.b.hosted)) lines.push(h("span", { class: "br-cost figures dust" }, spentWords(spentOf(e))));
      ul.append(h("li", null, h("button", { class: cls, type: "button", "data-fk": e.key, "aria-current": isChosen ? "true" : null,
        "aria-label": [entryName(e), ...lines.map((x) => x.textContent), subsWords(n)].filter(Boolean).join(" · "),
        onclick: () => choose(e.key) },
        nameEl, n ? h("span", { class: "br-n figures", "aria-hidden": "true" }, String(n)) : null, ...lines)));
    }
    if (M.archived.length) {
      const k = M.archived.length;
      ul.append(h("li", null, h("button", { class: "br br--archive" + (chosen === "archive" ? " is-chosen" : ""), type: "button", "data-fk": "archive",
        "aria-current": chosen === "archive" ? "true" : null, onclick: () => choose("archive") },
        h("span", { class: "br-long" }, k === 1 ? t("bodies.m.archived_one") : t("bodies.m.archived_n", { n: ctx.fmt.number(k, true) })),
        h("span", { class: "br-short" }, t("bodies.room.finished_n", { n: ctx.fmt.number(k) })))));
    }
    // on the phone, the plan's limits and the two quiet acts wait behind More
    ul.append(h("li", { class: "bodies-rail-more" }, h("button", { class: "br br--more", type: "button", "data-fk": "more", onclick: () => openMore(M) }, t("bodies.room.more"))));
    rail.append(ul);
    const foot = h("div", { class: "bodies-rail-foot" });
    const u = usage(M); if (u) foot.append(u);
    foot.append(h("div", { class: "bodies-foot" },
      h("button", { class: "link-btn", type: "button", onclick: () => openSpent(M) }, t("bodies.act.spent")),
      h("button", { class: "link-btn", type: "button", onclick: () => openFigures(M) }, t("bodies.act.figures"))));
    rail.append(foot);
  }

  function openMore(M) {
    const t = ctx.t;
    let close = null;
    const body = h("div", { class: "bodies-sheet" });
    const u = usage(M); if (u) body.append(u);
    close = ctx.openSheet({ title: t("bodies.room.more"), body, actions: [
      h("button", { class: "pill quiet", type: "button", onclick: () => { close && close(); openSpent(M); } }, t("bodies.act.spent")),
      h("button", { class: "pill quiet", type: "button", onclick: () => { close && close(); openFigures(M); } }, t("bodies.act.figures"))] });
  }

  function renderPage(M, E) {
    const t = ctx.t;
    // the one lit thing, the launch card asked for, a handoff waiting: above whatever is chosen
    room.slot.textContent = "";
    const f = fault(M); if (f) room.slot.append(f);
    const lc = launchCard(); if (lc) room.slot.append(lc);
    const hc = handoffCard(M); if (hc) room.slot.append(hc);
    room.slot.hidden = !room.slot.childNodes.length;
    room.head.textContent = "";
    room.page.dataset.chosen = chosen === "glance" || chosen === "archive" ? chosen : "body";
    if (chosen === "glance") {
      destroyConv();
      healthLine(M, room.head);
      room.conv.textContent = "";
      const box = h("div", { class: "bodies-field" });
      room.conv.append(box);
      if (ctx.prefs.large) box.append(twin(M));
      else { box.append(stage(M, box), h("p", { class: "bodies-reward voice", "aria-live": "polite" }), srList(M)); }
      return;
    }
    if (chosen === "archive") {
      destroyConv();
      room.head.append(h("h2", { class: "bodies-room-health voice" }, t("bodies.room.archive_head")));
      room.conv.textContent = "";
      const mnow = mnowOf(M);
      const ul = h("ul", { class: "bodies-archive" });
      for (const b of [...M.archived].sort((a, b2) => String(b2.newest || "").localeCompare(String(a.newest || "")))) {
        const w = wroteM(ctx, b, mnow);
        ul.append(h("li", null, h("button", { class: "link-btn", type: "button", onclick: () => choose("body:" + String(b.name).toLowerCase()) }, b.name),
          h("span", { class: "dust" }, [w ? t("bodies.room.wrote", { when: w }) : null, handoffWords(b) || (b.handoff_present ? t("bodies.room.left_handoff") : null)].filter(Boolean).map((x) => " · " + x).join(""))));
      }
      room.conv.append(ul);
      return;
    }
    let e = E.find((x) => x.key === chosen);
    if (!e) {
      const b = M.archived.find((x) => "body:" + String(x.name).toLowerCase() === chosen);
      e = { key: chosen, kind: "clone", group: "archived", b, talk: b.name, window: false };
    }
    pageHead(e, M);
    if (handoffOpen === e.key && e.b && e.b.from_machine && e.b.handoff) mountHandoff(e, M);
    else { if (handoffOpen === e.key) handoffOpen = null; mountConv(e, M); }
  }

  /** One line in her voice, the acts the record allows, and the switch between the two views. */
  function pageHead(e, M) {
    const t = ctx.t, mnow = mnowOf(M);
    const parts = [entryName(e)];
    if (e.kind === "prime") {
      const dw = deskWords(e.b, mnow); if (dw) parts.push(dw);
      if (e.b.alive === false) parts.push(t("bodies.room.not_running"));
      else { const w = wroteM(ctx, e.b, mnow); parts.push(w ? t("bodies.room.running_wrote", { when: w }) : t("bodies.room.running")); }
    } else if (e.kind === "clone") {
      const b = e.b;
      if (b.task) parts.push(firstLine(b.task, 120));
      if (b.word === "archived") parts.push(t("bodies.room.finished"));
      else if (b.word === "stale") parts.push(t("bodies.m.stopped_when", { when: wroteM(ctx, b, mnow) || "" }));
      else if (b.elsewhere) parts.push(t("bodies.w.elsewhere"));
      else parts.push(b.claimed_at ? t("bodies.room.running_since", { when: whenM(ctx, b.claimed_at, mnow) }) : t("bodies.room.running"));
    } else {
      parts.push(entryState(e, M));
    }
    const sw = subsWords(subsOf(e)); if (sw) parts.push(sw);
    const line = h("p", { class: "bodies-room-health voice" }, parts.join(" · "));
    const acts = h("div", { class: "bodies-room-acts" });
    const b = e.b;
    const waiting = b && b.waitingHandoff && !(b.handoff_card && localReviewed.has(b.handoff_card));
    if (handoffOpen !== e.key) {
      if (waiting) acts.append(h("button", { class: "pill", type: "button", "data-fk": "act:handoff", onclick: () => openHandoff(b) }, t("bodies.room.act_handoff")));
      else if (b && b.from_machine && b.handoff) acts.append(h("button", { class: "pill quiet", type: "button", "data-fk": "act:handoff", onclick: () => openHandoff(b) }, t("bodies.room.act_handoff")));
    }
    // on the prime: a new body for a task, its cost said first (the rail's head carries the same act)
    if (e.kind === "prime" && b.alive !== false) acts.append(h("button", { class: "pill quiet", type: "button", "data-fk": "act:task", onclick: giveTask }, t("bodies.give.act")));
    if (b && b.word === "stale" && !b.hosted) {
      const key = "close:" + b.actor;
      if (said.has(key)) acts.append(h("span", { class: "dust", role: "status" }, said.get(key)));
      else acts.append(h("button", { class: "pill quiet", type: "button", "data-fk": "act:close", onclick: () => {
        const say = t("bodies.f.close_say", { name: b.name });
        ctx.act("say", { text: say }, {}, ctx.home, { confirmed: true, label: say });
        said.set(key, t("bodies.f.said"));
        draw();
      } }, t("bodies.room.act_close")));
    }
    if (e.kind !== "dock" && e.window) {
      const key = "window:" + e.talk;
      acts.append(h("button", { class: "pill quiet", type: "button", "data-fk": "act:window", onclick: async () => {
        said.delete(key);
        const r = await openWindow(e.talk);
        if (!r.ok) { said.set(key, r.refused || t("bodies.room.window_refused")); draw(); }
      } }, t("bodies.room.open_window")));
      if (said.has(key)) acts.append(h("span", { class: "dust", role: "status" }, said.get(key)));
    }
    acts.append(viewSwitch(e));
    room.head.append(line, acts);
  }

  function prefView() {
    const p = store.prefs.bodies_view;
    if (p === "plain" || p === "words") return p;
    try { const v = JSON.parse(localStorage.getItem("hud.bodies_view") || "null"); return v === "plain" ? "plain" : "words"; } catch { return "words"; }
  }
  function currentView(e) {
    if (conv && conv.key === e.key && conv.kind === "dock" && conv.inst) {
      const v = conv.inst.view;
      return v === "terminal" ? "plain" : v === "line" ? "line" : "words";
    }
    return prefView();
  }
  function setView(e, v) {
    // kept on this device (store.prefs, as setPref keeps it), never in the record; quietly, so the
    // shell does not remount every view for a choice only this one reads
    if (v === "words" || v === "plain") { store.prefs.bodies_view = v; try { localStorage.setItem("hud.bodies_view", JSON.stringify(v)); } catch { /* private window */ } }
    if (conv && conv.kind === "dock" && conv.inst) conv.inst.setView(v === "plain" ? "terminal" : v === "line" ? "line" : "ice");
    else if (conv) renderTerm(conv);
    draw();
  }
  function viewSwitch(e) {
    const t = ctx.t, cur = currentView(e);
    const segs = [["words", t("bodies.room.view_words")], ["plain", t("bodies.room.view_plain")]];
    if (e.kind === "dock") segs.push(["line", t("bodies.room.view_line")]);
    const box = h("div", { class: "bodies-switch", role: "group", "aria-label": t("bodies.room.view_label") });
    for (const [v, label] of segs) {
      box.append(h("button", { class: "bodies-seg" + (cur === v ? " is-on" : ""), type: "button", "data-fk": "view:" + v,
        "aria-pressed": String(cur === v), onclick: () => { if (currentView(e) !== v) setView(e, v); } }, label));
    }
    return box;
  }

  /** The cost of a body, said first (DESIGN-BODIES §4.2): the week's allowance used so far over the
      hours of the week gone gives the pace an hour, from the plan's own figures (the engine's
      cost.limits, else this machine's reading); and what is left. Said in words when unknown. */
  function giveCost() {
    const t = ctx.t, U = windows(ctx), S7 = U && U.seven;
    if (!S7 || num(S7.used) == null) return t("bodies.give.cost_unknown");
    const pct = (v) => (v < 0.1 ? t("bodies.give.pct_small") : t("bodies.give.pct", { n: v < 10 ? String(Math.round(v * 10) / 10) : String(Math.round(v)) }));
    const left = t("bodies.give.pct_left", { n: String(Math.round(Math.max(0, 100 - S7.used))) });
    const r = ctx.fmt.date(S7.resets);
    const hours = r ? (WEEK_MS - (r - ctx.fmt.now())) / 3600000 : null;
    if (hours == null || hours < 1 || hours > 168) return t("bodies.give.left_only", { m: left });
    return t("bodies.give.cost", { n: pct(S7.used / hours), m: left });
  }

  /** Give a task: one field for the task in the person's words, the cost said before the one tap,
      then the person's own yes starts a body through the agent host (POST /agent/body, confirmed). */
  function giveTask() {
    const t = ctx.t;
    let close = null;
    const input = h("textarea", { class: "dock-input bodies-task-input", rows: "3", "aria-label": t("bodies.give.prompt"), placeholder: t("bodies.give.prompt") });
    const status = h("p", { class: "dust bodies-give-status", role: "status", "aria-live": "polite" });
    const start = h("button", { class: "pill primary bodies-give-start", type: "button", onclick: async () => {
      const task = input.value.trim();
      if (!task) { status.textContent = t("bodies.give.empty"); input.focus(); return; }
      if (typeof ctx.launchBody !== "function") { status.textContent = t("bodies.launch_no_host"); return; }
      start.disabled = true; status.textContent = t("bodies.give.starting");
      let r = null;
      try { r = await ctx.launchBody({ task, confirmed: true }); } catch { r = null; }
      if (r && r.ok) {
        const name = (r.out && r.out.name) || "";
        if (name) pendingChoose = name.toLowerCase();
        status.textContent = t("bodies.give.started", { name });
        setTimeout(() => { close && close(); draw(); }, 900);
      } else {
        start.disabled = false;
        status.textContent = t("bodies.give.refused", { why: (r && r.reason) || t("bodies.room.not_heard") });
      }
    } }, t("bodies.give.start"));
    close = ctx.openSheet({ title: t("bodies.give.title"), body: h("div", { class: "bodies-sheet bodies-give" },
      h("p", { class: "bodies-cost-first" }, giveCost()), input, status), actions: [start] });
    setTimeout(() => input.focus(), 40);
  }

  // ---------------------------------------------------------------- the conversation, mounted in place
  function dockCtx() { return Object.assign({}, ctx, { dock: { open: true, setOpen() {} } }); }

  function destroyConv() {
    if (!conv) return;
    try { if (conv.inst) conv.inst.unmount(); } catch { /* gone */ }
    try { if (conv.talk) conv.talk.close(); } catch { /* gone */ }
    conv.talk = null;
    if (conv.el) conv.el.remove();
    if (conv.kind === "terminal") { cancelAnimationFrame(conv.raf); clearTimeout(conv.idle); conv.raf = 0; }
    conv = null;
  }

  function mountConv(e, M) {
    if (conv && conv.key === e.key) {
      if (!conv.el.isConnected) { room.conv.textContent = ""; room.conv.append(conv.el); }
      conv.e = e; conv.M = M;
      if (conv.kind === "dock") { try { conv.inst.update(dockCtx()); } catch (err) { console.error("bodies dock:", err); } }
      else renderTerm(conv);         // draws only when its lines, reach or view changed
      return;
    }
    destroyConv();
    room.conv.textContent = "";
    if (e.kind === "dock" || (e.b && e.b.hosted)) {
      // the dock's agent, or a body the agent host started: an agent over the Agent Client Protocol,
      // so its conversation is the dock's own component, mounted with that agent's id
      const el = h("div", { class: "bodies-talk bodies-talk--dock" });
      room.conv.append(el);
      const c = { key: e.key, kind: "dock", el, e, M, inst: null };
      c.inst = createDock({ agentId: e.agent ? e.agent.id : e.b && e.b.hosted ? e.b.agentId : null, inline: true,
        onView: () => { if (conv === c && room) { const old = room.head.querySelector(".bodies-switch"); if (old) old.replaceWith(viewSwitch(c.e)); } } });
      conv = c;
      try { c.inst.mount(el, dockCtx()); } catch (err) { console.error("bodies dock:", err); }
      if (prefView() === "plain") c.inst.setView("terminal");
      return;
    }
    const kept = TERMS.get(e.key);
    if (kept) {                        // drawn before: reattached as it was, and only what is new is asked for
      kept.e = e; kept.M = M;
      room.conv.append(kept.el);
      conv = kept;
      connectTerm(kept);
      renderTerm(kept);
      return;
    }
    const el = h("div", { class: "bodies-talk bodies-talk--terminal" });
    const c = { key: e.key, kind: "terminal", el, e, M, lines: [], n: 0, reach: null, speak: null, talk: null, $: {},
      turns: [], parsed: 0, shownFrom: null, drawn: null, sig: null, raf: 0, idle: 0, caught: false };
    c.$.scroll = h("div", { class: "bodies-talk-scroll", tabindex: "-1" });
    c.$.input = h("textarea", { class: "dock-input", rows: "1", "data-fk": "talk:" + e.key, "aria-label": ctx.t("bodies.room.talk", { name: entryName(e) }), placeholder: ctx.t("bodies.room.talk", { name: entryName(e) }) });
    c.$.send = h("button", { class: "pill primary dock-send", type: "button", onclick: () => sendTo(c) }, ctx.t("bodies.room.send"));
    c.$.said = h("p", { class: "dust", role: "status" });
    c.$.input.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); sendTo(c); } });
    c.$.input.addEventListener("input", () => { c.$.input.style.height = "auto"; c.$.input.style.height = Math.min(c.$.input.scrollHeight, 200) + "px"; });
    c.$.foot = h("div", { class: "dock-foot bodies-talk-foot" }, h("div", { class: "dock-inputrow" }, c.$.input, c.$.send), c.$.said);
    el.append(c.$.scroll, c.$.foot);
    room.conv.append(el);
    conv = c;
    if (e.group !== "archived") TERMS.set(e.key, c);
    connectTerm(c);
    renderTerm(c);
  }

  /** Opens (or reopens) a terminal body's stream from the line it last received. Lines arriving
      together (a whole transcript on connect) are drawn once, on the next frame, never one by one. */
  function connectTerm(c) {
    const e = c.e;
    if (e.group === "archived") { c.reach = { reachable: false, why: "finished" }; return; }
    if (c.talk) return;
    const later = () => { if (!c.raf) c.raf = requestAnimationFrame(() => { c.raf = 0; if (conv === c) renderTerm(c); }); };
    c.talk = talkTo(e.talk, {
      since: c.n,
      onLine: (l) => { c.lines.push(l); c.n = Math.max(c.n, (l.n || 0) + 1); later(); },
      onCaughtUp: (next) => {
        if (typeof next === "number") c.n = Math.max(c.n, next);
        c.caught = true;
        // the last turn is drawn as a letter once nothing more has come for a moment
        clearTimeout(c.idle);
        c.idle = setTimeout(() => { if (c.turns.length) { c.turns[c.turns.length - 1].done = true; later(); } }, 1500);
        later();
      },
      onReach: (r) => { c.reach = r; later(); },
    });
    // reading and speaking differ: words go only to a body whose own inbox is open here
    reachOf(e.talk).then((r) => { c.speak = r; later(); });
  }

  /** The turns of a conversation, folded from its lines once each, as they arrive. A turn is the
      person's line, or the body's words of one turn; a turn ends when the next one begins. */
  function foldTurns(c) {
    for (; c.parsed < c.lines.length; c.parsed++) {
      const l = c.lines[c.parsed];
      const last = c.turns[c.turns.length - 1];
      if (l.kind === "user") {
        if (last) last.done = true;
        c.turns.push({ you: true, text: String(l.text || ""), done: true, rev: 1, lines: [l] });
      } else if (l.kind === "agent") {
        if (last && !last.you && last.turn === l.turn) {
          // the same turn goes on: plain again until it is quiet, then one letter (never one per line)
          last.text += (last.text ? "\n\n" : "") + String(l.text || ""); last.rev++; last.lines.push(l); last.done = false;
        } else {
          if (last) last.done = true;
          c.turns.push({ you: false, turn: l.turn, text: String(l.text || ""), done: false, rev: 1, lines: [l] });
        }
      } else if (last) last.lines.push(l);
      else c.turns.push({ you: false, turn: l.turn, text: "", done: false, rev: 0, lines: [l], bare: true });
    }
  }

  /** A machine body's handoff, as text in Plain, read through GET /bodies/handoff; then the person's
      own review: "I have read it" or "Archive it", a `witness` line in the person's home naming the
      body and the handoff's size, through the record's own act path (the Deal's card then goes). */
  function mountHandoff(e, M) {
    const t = ctx.t, b = e.b, key = "handoff:" + e.key;
    if (conv && conv.key === key) {
      if (!conv.el.isConnected) { room.conv.textContent = ""; room.conv.append(conv.el); }
      return;
    }
    destroyConv();
    room.conv.textContent = "";
    const el = h("div", { class: "bodies-talk bodies-talk--handoff" });
    const sc = h("div", { class: "bodies-talk-scroll", tabindex: "-1" }, h("p", { class: "dust" }, t("bodies.ho.loading")));
    const said = h("p", { class: "dust", role: "status" });
    const foot = h("div", { class: "bodies-acts bodies-handoff-acts" });
    el.append(sc, foot, said);
    room.conv.append(el);
    const c = { key, kind: "handoff", el };
    conv = c;
    const back = () => { handoffOpen = null; destroyConv(); draw(); };
    handoffText(b.folder || b.name).then((r) => {
      if (conv !== c) return;
      sc.textContent = "";
      if (!r.ok) {
        sc.append(h("p", { class: "voice bodies-away-line" }, t("bodies.ho.refused", { why: r.why || t("bodies.room.not_heard") })));
        foot.append(h("button", { class: "link-btn", type: "button", onclick: back }, t("bodies.ho.back")));
        return;
      }
      const pre = document.createElement("pre");
      pre.className = "dock-terminal bodies-plain bodies-handoff-text";
      pre.textContent = r.text;          // data: set as text, never as markup
      sc.append(h("p", { class: "voice bodies-handoff-head" }, t("bodies.ho.read_head", { name: b.name })), pre);
      if (r.cut) sc.append(h("p", { class: "dust" }, t("bodies.ho.cut")));
      const card = r.card || b.handoff_card;
      const review = (archived) => () => {
        const note = t(archived ? "bodies.ho.note_archived" : "bodies.ho.note_read", { name: b.name });
        const body = { note, handoff_of: r.folder || b.folder, handoff_bytes: r.bytes, card };
        if (archived) body.archived = true;
        ctx.act("witness", body, {}, ctx.home, { confirmed: true, label: note });
        if (card) localReviewed.set(card, archived ? "archived" : "read");
        said.textContent = t(archived ? "bodies.ho.done_archived" : "bodies.ho.done_read");
        foot.textContent = "";
        foot.append(h("button", { class: "link-btn", type: "button", onclick: back }, t("bodies.ho.back")));
        draw();
      };
      const done = b.reviewed || (card && localReviewed.has(card));
      if (!done) {
        foot.append(h("button", { class: "link-btn", type: "button", onclick: review(true) }, t("bodies.ho.archive")),
          h("button", { class: "pill primary bodies-big", type: "button", onclick: review(false) }, t("bodies.ho.mark_read")));
      } else foot.append(h("button", { class: "link-btn", type: "button", onclick: back }, t("bodies.ho.back")));
      requestAnimationFrame(() => { sc.scrollTop = 0; });
    });
  }

  async function sendTo(c) {
    const text = c.$.input.value.trim();
    if (!text || !c.talk) return;
    c.$.send.disabled = true;
    c.$.said.textContent = "";
    const r = await c.talk.send(text);
    c.$.send.disabled = false;
    if (r.ok) { c.$.input.value = ""; c.$.input.style.height = "auto"; }
    else c.$.said.textContent = r.reason ? ctx.t("bodies.room.not_taken", { why: r.reason }) : ctx.t("bodies.room.not_heard");
  }

  function hhmmss(ts) { const m = String(ts || "").match(/T(\d\d:\d\d:\d\d)/); return m ? m[1] : "        "; }

  /** A terminal body's conversation: Words (the dock's letter grammar) or Plain (every line as it
      came, with its time), or, when it cannot be reached, the honest page. Drawn incrementally:
      only new turns are appended; a turn still streaming is plain text, set as a letter once, when
      it is done; the last forty turns are shown, with "Earlier" for more. A redraw of the view that
      changes nothing here touches nothing here (its signature is unchanged). */
  function renderTerm(c) {
    const t = ctx.t, e = c.e, b = e.b, M = c.M || model(ctx);
    const sc = c.$.scroll, view = prefView();
    c.el.dataset.view = view;
    const speak = !!(c.speak && c.speak.reachable);
    const away = !c.reach ? "reaching" : !c.reach.reachable ? "away:" + (b && b.word) + ":" + (b && (b.status_last || "")) + ":" + ((b && b.subagents) || []).length : "talk";
    const sig = [away, view, speak, !!c.speak].join("|");
    if (away !== "talk") {
      if (sig === c.sig) return;
      c.sig = sig; c.drawn = null;
      sc.textContent = "";
      c.$.foot.hidden = true;
      if (away === "reaching") { sc.append(h("p", { class: "dust bodies-talk-reaching" }, t("bodies.room.reaching"))); return; }
      const box = h("div", { class: "bodies-away" });
      const gone = b && (b.word === "stale" || b.alive === false);
      box.append(h("p", { class: "voice bodies-away-line" }, e.group === "archived" ? t("bodies.room.finished_line")
        : gone ? t("bodies.room.not_running_line") : t("bodies.room.own_window")));
      if (b && b.task) box.append(h("p", { class: "eyebrow" }, t("bodies.room.task_head")), h("p", { class: "bodies-away-task" }, b.task));
      const lines = [];
      if (b && Array.isArray(b.status_lines)) lines.push(...[...b.status_lines].reverse());
      else if (b && b.status_last) lines.push(b.status_last);
      if (lines.length) box.append(h("p", { class: "eyebrow" }, t("bodies.room.status_head")),
        h("ul", { class: "bodies-away-status" }, lines.map((x) => h("li", { class: "ink-said" }, x))));
      if (b && b.handoff_present) box.append(h("p", { class: "dust" }, t("bodies.room.left_handoff_line")));
      const subs = (b && b.subagents) || (e.o && e.o.subagents) || [];
      const sl = subList(subs, mnowOf(M)); if (sl) box.append(sl);
      sc.append(box);
      return;
    }
    foldTurns(c);
    c.$.foot.hidden = !speak;
    const atEnd = sc.scrollHeight - sc.scrollTop - sc.clientHeight < 48;
    // a change of view or of reach starts the drawing afresh; otherwise only what is new is drawn
    if (sig !== c.sig || !c.drawn) {
      c.sig = sig;
      sc.textContent = "";
      if (!speak && c.speak) sc.append(h("p", { class: "dust bodies-talk-readonly" }, t("bodies.room.read_only")));
      c.$.empty = h("p", { class: "dust bodies-talk-empty" }, t("bodies.room.plain_empty"));
      c.$.earlier = h("button", { class: "link-btn bodies-earlier", type: "button", onclick: () => earlier(c) }, t("bodies.room.earlier"));
      c.$.body = view === "plain" ? h("pre", { class: "dock-terminal bodies-plain" }) : h("div", { class: "dock-turns" });
      c.$.presence = h("p", { class: "dock-presence dust", role: "status" });
      sc.append(c.$.empty, c.$.earlier, c.$.body, c.$.presence);
      c.shownFrom = Math.max(0, c.turns.length - TURNS_SHOWN);
      c.drawn = { view, els: new Map(), upto: c.shownFrom };
    }
    const D = c.drawn;
    c.$.empty.hidden = c.lines.length > 0;
    c.$.earlier.hidden = c.shownFrom <= 0;
    for (let i = c.shownFrom; i < c.turns.length; i++) drawTurn(c, i, false);
    D.upto = c.turns.length;
    const last = c.lines[c.lines.length - 1];
    c.$.presence.textContent = view !== "plain" && last && last.kind === "state" && last.text ? String(last.text) : "";
    if (atEnd || !c.scrolled) { c.scrolled = true; sc.scrollTop = sc.scrollHeight; }
  }

  function plainLine(l) {
    const tm = hhmmss(l.ts), k = l.kind, text = String(l.text == null ? "" : l.text);
    if (k === "user") return `${tm} > ${text}`;
    if (k === "agent") return `${tm} < ${text}`;
    return `${tm} [${k || "line"}] ${text}`;
  }

  /** One turn, drawn or brought up to date: nothing when it has not changed since it was drawn. */
  function drawTurn(c, i, before) {
    const D = c.drawn, T = c.turns[i];
    let r = D.els.get(i);
    const state = (T.done ? "d" : "s") + T.rev + ":" + T.lines.length;
    if (r && r.state === state) return;
    if (D.view === "plain") {
      if (!r) { r = { el: document.createElement("span"), n: 0, state: "" }; if (before) c.$.body.prepend(r.el); else c.$.body.append(r.el); D.els.set(i, r); }
      // the lines of a turn are appended as they come, as plain text
      let add = "";
      for (; r.n < T.lines.length; r.n++) add += (c.$.body.textContent || r.n || i > c.shownFrom ? "\n" : "") + plainLine(T.lines[r.n]);
      if (add) r.el.append(document.createTextNode(add));
      r.state = state;
      return;
    }
    if (T.bare || (!T.you && !T.text)) { r = r || { el: null, state }; r.state = state; D.els.set(i, r); return; }
    if (!r) {
      r = { el: h("article", { class: "dock-turn " + (T.you ? "dock-turn--you" : "dock-turn--agent") }), state: "" };
      if (before) { const first = [...D.els.values()].find((x) => x.el && x.el.isConnected); c.$.body.insertBefore(r.el, first ? first.el : null); }
      else c.$.body.append(r.el);
      D.els.set(i, r);
    }
    r.el.textContent = "";
    if (T.you) r.el.append(h("p", { class: "dock-words" }, T.text));
    else if (T.done) r.el.append(h("span", { class: "dock-ring dock-turnring", "aria-hidden": "true" }), h("div", { class: "dock-letter" }, ...letter(h, T.text)));
    else r.el.append(h("span", { class: "dock-ring dock-turnring", "aria-hidden": "true" }), h("div", { class: "dock-letter dock-letter--streaming" }, h("p", { class: "dock-plainstream" }, T.text)));
    r.state = state;
  }

  /** "Earlier": forty more turns, drawn above, the reading place kept. */
  function earlier(c) {
    const sc = c.$.scroll, h0 = sc.scrollHeight;
    const from = Math.max(0, c.shownFrom - TURNS_SHOWN);
    for (let i = c.shownFrom - 1; i >= from; i--) drawTurn(c, i, true);
    c.shownFrom = from;
    c.$.earlier.hidden = from <= 0;
    sc.scrollTop += sc.scrollHeight - h0;
  }

  // ---------------------------------------------------------------- 1. the health line
  function awakeSince(M) {
    const f = ctx.fmt, hb = M.live && M.live.heartbeat, now = f.now();
    const long = ((hb && hb.slept) || []).filter((g) => {
      const a = f.date(g.from), b = f.date(g.to);
      return a && b && f.sameDay(b, now) && (b - a) >= 3600000;
    }).pop();
    if (long) return long.to;
    const c = M.prime && f.date(M.prime.claimed_at);
    if (c && f.sameDay(c, now)) return M.prime.claimed_at;
    return null;
  }

  /** The health line from this machine's own reading: the prime, the desk, the bodies at work,
      the short tasks running under them, and the stopped. */
  function machineHealth(M) {
    const t = ctx.t, f = ctx.fmt, P = M.prime, parts = [];
    if (!P || !P.alive) parts.push(t("bodies.m.h.prime_gone"));
    else if (P.holds_desk) parts.push(t("bodies.m.h.prime_desk"));
    else if (P.desk_holder) parts.push(t("bodies.m.h.prime_desk_with", { holder: P.desk_holder }));
    else parts.push(t("bodies.m.h.prime"));
    const working = M.clones.filter((b) => b.word === "work" || b.word === "quiet").length;
    parts.push(W(ctx).count(working) + ".");
    const subs = [P, ...M.clones].filter(Boolean).reduce((a, b) => a + (b.subagents || []).length, 0)
      + M.machine.others.reduce((a, o) => a + o.subagents.length, 0) + M.machine.loose.length;
    if (subs === 1) parts.push(t("bodies.m.h.subs_one"));
    else if (subs > 1) parts.push(t("bodies.m.h.subs_n", { n: f.number(subs) }));
    const stale = M.clones.filter((b) => b.word === "stale").length;
    if (stale === 1) parts.push(t("bodies.m.h.stale_one"));
    else if (stale > 1) parts.push(t("bodies.m.h.stale_n", { n: f.number(stale) }));
    // the day's total: every session this computer's ledger saw working in the house today
    const day = M.live && M.live.spent_today;
    if (day && typeof day.usd === "number") parts.push(t("bodies.cost.h_total", { figure: money2(day.usd) }));
    else if (day && day.tokens) parts.push(t("bodies.cost.h_total", { figure: t("bodies.cost.units", { n: compact(day.tokens) }) }));
    else parts.push(t("bodies.cost.h_none"));
    return parts.join(" ");
  }

  function healthLine(M, box) {
    const t = ctx.t, st = ctx.state, w = W(ctx), f = ctx.fmt;
    if (M.machine) { box.append(h("p", { class: "bodies-line voice" }, machineHealth(M))); return; }
    const hb = M.live && M.live.heartbeat;
    const parts = [];
    if (hb && hb.asleep) {
      parts.push(t("bodies.h.resting", { time: w.time(hb.asleep.from) }));
    } else if (hb && hb.open && hb.open.kind === "stopped") {
      parts.push(t("bodies.h.stopped", { time: w.time(hb.open.from) }));
    } else {
      const since = awakeSince(M);
      if (since) parts.push(t("bodies.h.awake_since", { time: w.time(since) }));
      const working = M.clones.filter((b) => b.word === "work" || b.word === "quiet").length;
      const d = st.desk;
      const count = M.clones.length ? w.count(working) : t("bodies.h.one_body");
      if (!d) parts.push(t("bodies.h.count", { count }));
      else if (d.collision) parts.push(t("bodies.h.count_collision", { count }));
      else if (!d.holder) parts.push(t("bodies.h.count_unheld", { count }));
      else {
        const hbody = byActor(M, d.holder);
        const isPrime = !hbody || hbody.kind === "prime";
        // "Your agent" once per line: after the waking sentence it is "It"
        const holder = isPrime ? (since ? t("bodies.face.it") : t("bodies.face.agent_cap")) : faceName(ctx, hbody, true);
        parts.push(t("bodies.h.count_desk", { count, holder }));
      }
    }
    box.append(h("p", { class: "bodies-line voice" }, parts.join(" ")));
    const dust = [];
    const asOf = (M.live && M.live.as_of) || (st.cost && st.cost.day && st.cost.day.as_of) || st.generated_at;
    // one as-of on the screen, the oldest, in the top line (shell.js); the rest open behind it
    if (!M.live) dust.push(t("bodies.h.from_held"));
    if (st.bodies_closeout && st.bodies_closeout.at) {
      dust.push(st.bodies_closeout.at_rest ? t("bodies.closed_rest", { time: w.time(st.bodies_closeout.at) })
        : t("bodies.closed", { time: w.time(st.bodies_closeout.at) }));
    }
    if (dust.length) box.append(h("p", { class: "dust figures" }, dust.join(" · ")));
  }

  // ---------------------------------------------------------------- 2. the one lit thing
  /** The fault that needs the person's hand: a desk collision first, then a stale claim. */
  function fault(M) {
    const t = ctx.t, st = ctx.state, w = W(ctx);
    const d = st.desk;
    const eyebrow = t("bodies.f.eyebrow");
    let key = null, text = null, primary = null, quiet = null;
    if (d && d.collision) {
      const later = (d.claims || []).filter((c) => c.live && c.actor !== d.holder).pop();
      const lb = later && byActor(M, later.actor);
      const first = byActor(M, d.holder);
      const firstName = first ? faceName(ctx, first) : t("bodies.face.agent");
      const firstCap = first ? faceName(ctx, first, true) : t("bodies.face.agent_cap");
      const name = lb ? faceName(ctx, lb) : t("app.agent_default");
      key = "desk:" + (later ? later.actor + later.at : "");
      text = t("bodies.f.collision", { first: firstCap, since: w.time(d.since), name, at: later ? w.time(later.at) : "" });
      primary = { label: t("bodies.f.keep", { first: firstName }), say: t("bodies.f.keep_say", { first: firstName }) };
      quiet = { label: t("bodies.give_to", { name }), say: t("bodies.f.give_say", { name }) };
    } else {
      const stale = M.machine ? null : M.clones.find((b) => b.word === "stale");
      if (stale) {
        key = "stale:" + stale.actor;
        const time = w.time(stale.endedAt);
        text = stale.waitingHandoff && stale.review_min != null
          ? t("bodies.f.stale_left", { name: stale.name, time, minutes: ctx.fmt.aboutMinutes(stale.review_min).toLowerCase() })
          : t("bodies.f.stale", { name: stale.name, time });
        primary = { label: stale.waitingHandoff ? t("bodies.f.close_keep") : t("bodies.f.close"),
          say: t("bodies.f.close_say", { name: stale.name }) };
      }
    }
    if (!key) return null;
    const card = h("section", { class: "bodies-card is-owed bodies-fault", "aria-label": eyebrow });
    card.append(h("p", { class: "eyebrow" }, eyebrow), h("p", { class: "bodies-q" }, text));
    if (said.has(key)) { card.append(h("p", { class: "dust", role: "status" }, said.get(key))); return card; }
    const act = (x) => () => {
      ctx.act("say", { text: x.say }, {}, ctx.home, { confirmed: true, label: x.say });
      said.set(key, t("bodies.f.said"));
      draw();
    };
    card.append(h("div", { class: "bodies-acts" },
      quiet ? h("button", { class: "link-btn", type: "button", onclick: act(quiet) }, quiet.label) : h("span"),
      h("button", { class: "pill primary bodies-big", type: "button", onclick: act(primary) }, primary.label)));
    return card;
  }

  // ---------------------------------------------------------------- 2. the launch card (asked for, so unlit)
  function readLaunch() {
    const p = ctx.route && ctx.route.params;
    const key = p ? (p.get("launch") || p.get("task")) : null;
    if (!key) { launchFor = null; return; }
    if (launchFor && launchFor.key === key) return;
    launchFor = { key, card: p.get("launch"), task: p.get("task") };
    launchClosed = false;
  }
  function launchCard() {
    if (!launchFor || launchClosed) return null;
    return launchBody(ctx, { card: launchFor.card, task: launchFor.task, onClose: () => { launchClosed = true; draw(); } });
  }

  // ---------------------------------------------------------------- 3. a handoff waiting, one card
  function handoffCard(M) {
    const t = ctx.t;
    const waiting = M.clones.filter((b) => b.waitingHandoff && b.word !== "stale");
    if (!waiting.length) return null;
    const first = waiting[0];
    const total = waiting.reduce((a, b) => a + (b.review_min || 0), 0);
    const card = h("section", { class: "bodies-card bodies-handoff", "aria-label": t("bodies.handoff_title") });
    card.append(h("p", { class: "eyebrow" }, first.handoffDay ? t("bodies.eyebrow_day") : t("bodies.ho.eyebrow")));
    if (waiting.length === 1) {
      card.append(h("p", { class: "bodies-q" }, t("bodies.handoff_q", { name: first.name, task: first.task || t("bodies.ho.its_task") }),
        first.review_min != null ? h("span", { class: "dust" }, " " + ctx.fmt.aboutMinutes(first.review_min) + ".") : null));
    } else {
      card.append(h("p", { class: "bodies-q" }, t("bodies.ho.many", { n: ctx.fmt.number(waiting.length), minutes: ctx.fmt.aboutMinutes(total).toLowerCase() })));
    }
    card.append(h("div", { class: "bodies-acts" }, h("span"),
      h("button", { class: "pill primary bodies-big", type: "button", onclick: () => openHandoff(first) },
        waiting.length === 1 ? t("bodies.opt_read") : t("bodies.ho.read_first"))));
    return card;
  }

  // ---------------------------------------------------------------- 3b. the house, in words (this machine)
  /** One line per short task running under a body: what it does · its model · how long. */
  function subList(list, mnow) {
    if (!list || !list.length) return null;
    const t = ctx.t;
    const ul = h("ul", { class: "bodies-subs", "aria-label": t("bodies.m.sub_head") });
    for (const a of list) {
      const model = a.model ? String(a.model).charAt(0).toUpperCase() + String(a.model).slice(1) : null;
      ul.append(h("li", null, [a.description || t("bodies.m.sub_unnamed"), model, spanM(ctx, a.started, mnow)].filter(Boolean).join(" · ")));
    }
    return h("div", { class: "bodies-subs-box" }, h("p", { class: "eyebrow" }, t("bodies.m.sub_head")), ul);
  }

  // ---------------------------------------------------------------- 4. the field
  function geometry(Wd) {
    const phone = Wd < 600;
    const size = phone ? Wd * 0.84 : Math.min(Wd * 0.78, 720);
    return { phone, size, rx: FRAME.rx * size, ry: FRAME.ry * size, small: size / 3, cx: Wd / 2, cy: 0 };
  }

  /** Where each body sits on the prime's membrane: its birth point, advanced by its age, one circuit a day. */
  function place(b, G) {
    const birth = unit(b.actor || b.name) * Math.PI * 2 - Math.PI / 2;
    const age = b.age != null ? b.age : 0;
    let a = birth + (Math.min(age, 48) / 24) * Math.PI * 2;
    if (b.elsewhere) a = Math.PI / 2;
    return { a, birth, x: G.cx + G.rx * Math.cos(a), y: G.cy + G.ry * Math.sin(a) };
  }

  /** The one word beside a body, only when something differs from normal. */
  function differs(b) {
    const t = ctx.t, w = W(ctx), d = ctx.state.desk;
    if (b.word === "stale" && b.from_machine) return t("bodies.m.stopped_when", { when: wroteM(ctx, b, b.mnow) || "" });
    if (b.word === "stale") return t("bodies.w.stopped", { time: w.time(b.endedAt) });
    if (d && d.collision && (d.claims || []).some((c) => c.live && c.actor === b.actor && c.actor !== d.holder)) return t("bodies.desk_asked");
    if (d && d.holder === b.actor && b.kind !== "prime") return t("bodies.w.holds_desk");
    if (b.word === "held") return b.why ? t("bodies.w.held_why", { why: b.why }) : t("bodies.w.held");
    if (b.word === "handoff") return b.waitingHandoff ? t("bodies.w.finished") : t("bodies.w.finished_read");
    if (b.word === "done") return t("bodies.w.finished_read");
    if (b.word === "quiet") return t("bodies.w.quiet", { time: w.time(b.newest) });
    if (b.elsewhere) return t("bodies.w.elsewhere");
    if (b.flags.has("past_day")) return t("bodies.w.past_day");
    if (b.from_live) return t("bodies.w.from_machine");
    if (b.flags.has("no_task") || (!b.task && !b.first_word)) return t("bodies.w.no_task");
    return null;
  }

  /** Words beside each body, placed so no two cross: each moves outward until it is clear. */
  function labelBoxes(M, G, places, Wd) {
    const half = Math.min(G.phone ? 60 : 104, Wd / 2 - 4);
    const lh = (px) => Math.ceil(px * 1.2) + 2;
    const fit = (text, charW) => Math.max(1, Math.ceil((String(text).length * charW) / (half * 2)));
    const big = ctx.prefs.large ? 1.3 : 1;
    const boxes = M.clones.map((b, i) => {
      const p = places[i];
      const cry = FRAME.ry * G.small;
      const above = p.y < G.cy - 2;
      const task = b.task || "";
      const third = differs(b) || "";
      const hgt = (lh(15) + (task ? fit(task, 5.9) * lh(13) : 0) + (third ? fit(third, 5.9) * lh(13) : 0)) * big;
      const lx = clamp(p.x, half + 4, Wd - half - 4);
      const y0 = above ? p.y - cry - 4 - hgt : p.y + cry + 4;
      return { i, b, above, task, third, lx, half, top: y0, h: hgt };
    });
    const order = [...boxes].sort((a, b) => Math.abs(a.top - G.cy) - Math.abs(b.top - G.cy));
    const placed = [];
    for (const bx of order) {
      for (let guard = 0; guard < 20; guard++) {
        const hit = placed.find((o) => Math.abs(o.lx - bx.lx) < o.half + bx.half && bx.top < o.top + o.h + 4 && o.top < bx.top + bx.h + 4);
        if (!hit) break;
        bx.top = bx.above ? hit.top - bx.h - 6 : hit.top + hit.h + 6;
      }
      placed.push(bx);
    }
    return boxes;
  }

  function frameEl(holeY, extraClass) {
    const k = FRAME.rx / FRAME.ry;
    const origin = `50% ${holeY * 100}%`;
    const lum = maskStyle();
    const img1 = h("img", { src: FRAME.src, alt: "", decoding: "async", draggable: "false", style: lum });
    const band = h("div", { class: "bf-static" }, img1);
    const rot = h("div", { class: "bf-rot", style: `transform-origin:${origin}` },
      h("img", { src: FRAME.src, alt: "", decoding: "async", draggable: "false", style: `${lum}transform:scaleY(${k});transform-origin:${origin}` }));
    const turn = h("div", { class: "bf-turn", style: `transform:scaleY(${1 / k});transform-origin:${origin}` }, rot);
    const field = h("div", { class: `bf ${extraClass || ""}` }, band, turn);
    return { field, rot, img: img1 };
  }

  function spin(actor, rot, secs) {
    if (!secs || ctx.prefs.reducedMotion) return;
    const from = angles.get(actor) || 0;
    const a = ctx.animate(rot, [{ transform: `rotate(${from}deg)` }, { transform: `rotate(${from + 360}deg)` }],
      { duration: secs * 1000, iterations: Infinity, easing: cssVar("--e-turn") || "linear" });
    if (a) {
      anims.set(actor, { anim: a, secs });
      try { a.playbackRate = 0.25; setTimeout(() => { try { a.updatePlaybackRate ? a.updatePlaybackRate(1) : (a.playbackRate = 1); } catch { /* gone */ } }, ms("--d-settle")); } catch { /* fine */ }
    }
  }

  function stage(M, box) {
    const t = ctx.t;
    const avail = (box && box.clientWidth) || root.clientWidth || el.clientWidth || 360;
    const Wd = Math.max(280, Math.round(avail));
    width = Wd;
    const G = geometry(Wd);
    let places = M.clones.map((b) => place(b, G));
    let boxes = labelBoxes(M, G, places, Wd);
    const pad = 8;
    const fieldTop = -(G.ry + G.small * 0.3), fieldBottom = G.ry + G.small * 0.3;
    const minTop = Math.min(fieldTop, ...boxes.map((b) => b.top));
    const maxBottom = Math.max(fieldBottom, ...boxes.map((b) => b.top + b.h));
    const dy = pad - minTop;
    G.cy = dy;
    const H = Math.round(maxBottom - minTop + 2 * pad);
    places = places.map((p) => ({ ...p, y: p.y + dy }));
    boxes = boxes.map((b) => ({ ...b, top: b.top + dy }));

    const wrap = h("div", { class: "bodies-stage", style: `height:${H}px`, "aria-hidden": "true" });
    const art = h("div", { class: "bodies-art" });
    const svg = s("svg", { class: "bodies-svg", viewBox: `0 0 ${Wd} ${H}`, width: Wd, height: H });
    const labels = h("div", { class: "bodies-labels" });
    const hits = h("div", { class: "bodies-hits" });
    wrap.append(art, svg, labels, hits);
    const asleep = M.live && M.live.heartbeat && M.live.heartbeat.asleep;
    const st = ctx.state;
    const items = [];

    // -- the prime: a field like every field, never drawn as a center
    const P = M.prime;
    {
      const { field, rot, img } = frameEl(FRAME.hole[1], "bf-prime");
      field.style.cssText = `left:${G.cx - G.size / 2}px;top:${G.cy - FRAME.hole[1] * G.size}px;width:${G.size}px;height:${G.size}px`;
      img.addEventListener("error", () => { field.classList.add("is-fallback"); fallback(svg, G.cx, G.cy, G.rx, G.ry); });
      art.append(field);
      if (P && !asleep) spin(P.actor, rot, turnSeconds(P.writes));
      if (seen == null) ctx.animate(field, [{ opacity: 0 }, { opacity: 1 }], { duration: ms("--d-card"), easing: cssVar("--e-settle"), fill: "backwards" });
      svg.append(s("ellipse", { cx: G.cx, cy: G.cy, rx: G.rx, ry: G.ry, class: "bm" }));
      items.push({ x: G.cx, y: G.cy });
      const holds = st.desk && st.desk.holder && P && st.desk.holder === P.actor;
      labels.append(h("div", { class: "bprime", style: `left:${G.cx}px;top:${G.cy - G.ry * 0.04}px` },
        h("span", { class: "caps" }, t("bodies.face.agent")),
        holds ? h("span", { class: "dust" }, t("bodies.w.holds_desk")) : null,
        P && P.word === "stale" ? h("span", { class: "dust" }, t("bodies.w.stopped_plain")) : null));
      if (P) hits.append(h("button", { class: "b-hit", tabindex: "-1", style: `left:${G.cx - G.rx * 0.7}px;top:${G.cy - G.ry * 0.7}px;width:${G.rx * 1.4}px;height:${G.ry * 1.4}px`,
        onclick: () => openBody(P) }));
      hits.append(holeButton(G.cx, G.cy - G.ry * 0.05));
    }

    // -- the bodies: small fields on the prime's membrane
    M.clones.forEach((b, i) => {
      const p = places[i], bx = boxes[i];
      const sz = G.small, crx = FRAME.rx * sz, cry = FRAME.ry * sz;
      const stale = b.word === "stale";
      if (!stale) {
        const { field, rot, img } = frameEl(FRAME.hole[1], "bf-clone");
        field.style.cssText = `left:${p.x - sz / 2}px;top:${p.y - FRAME.hole[1] * sz}px;width:${sz}px;height:${sz}px`;
        img.addEventListener("error", () => { field.classList.add("is-fallback"); fallback(svg, p.x, p.y, crx, cry); });
        art.append(field);
        if (!asleep) spin(b.actor, rot, turnSeconds(b.writes));
        const born = seen && !seen.has(b.actor);
        if (born) ctx.animate(field, [{ opacity: 0, transform: "scale(.6)" }, { opacity: 1, transform: "none" }], { duration: ms("--d-card"), easing: cssVar("--e-settle") });
        else if (seen == null) ctx.animate(field, [{ opacity: 0 }, { opacity: 1 }], { duration: ms("--d-card"), delay: ms("--d-settle") * (i + 1), easing: cssVar("--e-settle"), fill: "backwards" });
      }
      // a stopped body is its membrane alone, still: the field has left it
      svg.append(s("ellipse", { cx: p.x, cy: p.y, rx: crx, ry: cry, class: `bm bm-clone${stale ? " is-empty" : ""}` }));
      items.push({ x: p.x, y: p.y });
      // a label above its field is anchored by its foot, so it sits on the field whatever its height
      labels.append(h("div", { class: `bl${bx.above ? " is-above" : ""}`, style: `left:${bx.lx}px;top:${bx.above ? bx.top + bx.h : bx.top}px;width:${bx.half * 2}px` },
        h("span", { class: "bl-name" }, b.name),
        bx.task ? h("span", { class: "bl-task" }, bx.task) : null,
        bx.third ? h("span", { class: "dust" }, bx.third) : null));
      hits.append(h("button", { class: "b-hit", tabindex: "-1", style: `left:${p.x - crx}px;top:${p.y - cry}px;width:${crx * 2}px;height:${cry * 2}px`,
        onclick: () => openBody(b) }));
    });

    // -- the archived of a moment ago: drawn in to the membrane, and gone (once)
    if (seen) {
      for (const b of M.archived) {
        if (lastStates.get(b.actor) && lastStates.get(b.actor) !== "archived") {
          const p = place(b, G);
          const ghost = h("div", { class: "bghost", style: `left:${p.x}px;top:${p.y + G.cy}px;width:${G.small * 0.6}px;height:${G.small * 0.3}px` });
          art.append(ghost);
          const a = ctx.animate(ghost, [{ opacity: 1, transform: "translate(-50%,-50%) scale(1)" }, { opacity: 0, transform: "translate(-50%,-50%) scale(.3)" }],
            { duration: ms("--d-settle"), easing: cssVar("--e-leave"), fill: "forwards" });
          if (!a) ghost.remove(); else a.onfinish = () => ghost.remove();
        }
      }
    }
    wrap._items = items; wrap._svg = svg; wrap._H = H;
    // the words' heights were estimated; once they are set, trim what they did not use
    requestAnimationFrame(() => trim(wrap, [art, svg, labels, hits], pad));
    return wrap;
  }

  function trim(wrap, layers, pad) {
    if (!wrap.isConnected) return;
    const box = wrap.getBoundingClientRect();
    const rects = [...wrap.querySelectorAll(".bl, .bprime")].map((n) => n.getBoundingClientRect());
    rects.push(...[...wrap.querySelectorAll(".bf")].map((n) => {
      const r = n.getBoundingClientRect();   // a field's drawn lines sit in the middle band of its frame
      return { top: r.top + r.height * 0.16, bottom: r.bottom - r.height * 0.16 };
    }));
    if (!rects.length) return;
    const top = Math.min(...rects.map((r) => r.top)) - box.top - pad;
    const bottom = box.bottom - Math.max(...rects.map((r) => r.bottom)) - pad;
    const up = Math.max(0, Math.floor(top)), down = Math.max(0, Math.floor(bottom));
    if (up < 2 && down < 2) return;
    wrap.style.height = `${wrap._H - up - down}px`;
    for (const l of layers) l.style.transform = `translateY(${-up}px)`;
    wrap._shift = up;
  }

  function fallback(svg, cx, cy, rx, ry) {
    for (let i = 1; i <= 4; i++) svg.append(s("ellipse", { cx, cy, rx: rx * i / 4, ry: ry * i / 4, class: "bfallback" }));
  }

  /** Press and hold the prime's still point: every axis rises toward one place above the frame. */
  function holeButton(x, y) {
    let timer = null, held = false;
    const b = h("button", { class: "b-hole", tabindex: "-1", style: `left:${x}px;top:${y}px` });
    b.addEventListener("pointerdown", () => { held = false; timer = setTimeout(() => { held = true; reward(); }, 550); });
    for (const ev of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(ev, () => clearTimeout(timer));
    b.addEventListener("click", () => { if (held) { held = false; return; } reward(); });
    b.addEventListener("contextmenu", (e) => e.preventDefault());
    return b;
  }
  function reward() {
    const wrap = root.querySelector(".bodies-stage");
    if (!wrap || !wrap._items) return;
    const svg = wrap._svg;
    svg.querySelectorAll(".baxis").forEach((n) => n.remove());
    const P = { x: width / 2, y: -wrap._H * 1.2 };
    for (const it of wrap._items) {
      const line = s("line", { x1: it.x, y1: it.y, x2: P.x, y2: P.y, class: "baxis" });
      svg.append(line);
      const len = Math.hypot(P.x - it.x, P.y - it.y);
      line.style.strokeDasharray = `${len}`;
      const a = ctx.animate(line, [{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: ms("--d-bloom"), easing: cssVar("--e-settle"), fill: "both" });
      if (!a) line.style.strokeDashoffset = "0";
    }
    const say = root.querySelector(".bodies-reward");
    if (say) say.textContent = ctx.t("map.hold_line");
    clearTimeout(rewardTimer);
    rewardTimer = setTimeout(() => { svg.querySelectorAll(".baxis").forEach((n) => n.remove()); if (say) say.textContent = ""; }, ms("--d-notice"));
  }

  /** A body in one line of words: its name, what it is on, and the one differing word. */
  function oneLine(b) {
    const d = ctx.state.desk;
    const extra = b.kind === "prime" ? (d && d.holder === b.actor ? ctx.t("bodies.w.holds_desk") : null) : differs(b);
    return { name: faceName(ctx, b, true), task: b.kind === "prime" ? null : (b.task || null), extra };
  }
  /** The field in words, for the screen reader (the picture is hidden from it). */
  function srList(M) {
    const ul = h("ul", { class: "sr-only" });
    for (const b of [M.prime, ...M.clones].filter(Boolean)) {
      const L = oneLine(b);
      ul.append(h("li", null, h("button", { type: "button", onclick: () => openBody(b) }, [L.name, L.task, L.extra].filter(Boolean).join(" · "))));
    }
    return ul;
  }
  /** Large type: the field's twin, shown instead of the field, never beside it. */
  function twin(M) {
    const ul = h("ul", { class: "bodies-twin-list" });
    for (const b of [M.prime, ...M.clones].filter(Boolean)) {
      const L = oneLine(b);
      ul.append(h("li", null, h("button", { class: "bodies-twin-row", type: "button", onclick: () => openBody(b) },
        h("span", { class: "bl-name" }, L.name),
        L.task ? h("span", { class: "bl-task" }, L.task) : null,
        L.extra ? h("span", { class: "dust" }, L.extra) : null)));
    }
    return ul;
  }

  // ---------------------------------------------------------------- 5. the week's usage
  function usage(M) {
    const t = ctx.t, w = W(ctx);
    const U = windows(ctx);
    if (!U) return null;
    const box = h("section", { class: "bodies-usage", "aria-label": t("bodies.u.title") });
    box.append(h("h2", { class: "eyebrow" }, t("bodies.u.title")));
    const renew = (x) => {
      const d = ctx.fmt.date(x);
      if (!d) return null;
      return ctx.fmt.sameDay(d, ctx.fmt.now()) ? t("bodies.renews_at", { time: w.time(x) }) : t("bodies.renews_on", { when: ctx.fmt.dayName(d), time: w.time(x) });
    };
    const bar = (label, x, isWeek) => {
      const used = clamp(x.used, 0, 100);
      const today = isWeek && x.today != null ? clamp(x.today, 0, used) : null;
      const before = today != null ? used - today : null;
      const track = h("span", { class: "bu-track", "aria-hidden": "true" },
        today != null ? h("i", { class: "bu-before", style: `width:${before}%` }) : null,
        h("i", { class: "bu-fill", style: today != null ? `left:${before}%;width:${today}%` : `width:${used}%` }),
        x.ceiling != null ? h("b", { class: "bu-ceil", style: `left:${clamp(x.ceiling, 0, 100)}%` }) : null);
      const words = [today != null ? t("bodies.u.used_today", { n: Math.round(used), d: Math.round(today) })
        : t(isWeek ? "bodies.u.used_week" : "bodies.u.used", { n: Math.round(used) }),
        x.ceiling != null ? t("bodies.u.line", { n: Math.round(x.ceiling) }) : null, renew(x.resets)].filter(Boolean).join(" · ");
      return h("li", { class: "bu" }, h("span", { class: "bu-name" }, label), track, h("span", { class: "dust figures bu-words" }, words));
    };
    const ul = h("ul", { class: "bu-list" });
    if (U.seven) ul.append(bar(t("bodies.limit_week"), U.seven, true));
    if (U.five) ul.append(bar(t("bodies.limit_five"), U.five, false));
    box.append(ul);
    const S7 = U.seven;
    if (S7 && S7.pace != null) {
      const line = S7.ceiling != null ? (S7.pace > S7.ceiling ? t("bodies.u.pace_over") : t("bodies.u.pace_under"))
        : (S7.pace > 100 ? t("bodies.u.pace_out") : t("bodies.u.pace_lasts"));
      box.append(h("p", { class: "bodies-pace" }, line));
    }
    if (U.asOf) box.append(h("p", { class: "dust figures asof-more" }, t("bodies.limits_asof", { as_of: ctx.fmt.asOf(U.asOf) })));
    return box;
  }

  // ---------------------------------------------------------------- sheets
  function costOf(b) {
    const st = ctx.state, w = W(ctx);
    const day = st.cost && st.cost.day;
    const tokens = day && day.by_body && day.by_body[b.actor] != null ? day.by_body[b.actor] : b.cost_tokens;
    const money = day && day.money && day.money.by_body ? w.money(day.money.by_body[b.actor], day.money.unit) : null;
    return [w.tokens(tokens), money].filter(Boolean).join(" · ");
  }

  /** A body touched in the picture at a glance: chosen in the room. */
  function openBody(b) {
    if (!b) return;
    choose(b.kind === "prime" ? "prime" : "body:" + String(b.name).toLowerCase());
  }

  function openHandoff(b) {
    if (b && b.from_machine && b.handoff) {
      const key = "body:" + String(b.name).toLowerCase();
      handoffOpen = key;
      if (chosen !== key) choose(key); else draw();
      return;
    }
    const t = ctx.t, st = ctx.state, w = W(ctx);
    const ln = (st.lines || []).find((l) => l.id === b.handoff) || null;
    const minutes = b.review_min != null ? ctx.fmt.aboutMinutes(b.review_min) : "";
    let close = null;
    const say = (text) => ctx.act("say", { text }, { anchored_to: [b.handoff] }, b.holon || ctx.home, { confirmed: true, label: text });
    const reviewed = () => {
      close && close();
      ctx.act("witness", {}, { witnesses: [b.handoff] }, b.holon || ctx.home, { confirmed: true, label: t("bodies.reviewed") });
    };
    const body = h("div", { class: "bodies-sheet" },
      h("p", { class: "eyebrow" }, b.handoffDay ? t("bodies.eyebrow_day") : t("bodies.ho.eyebrow")),
      h("p", { class: "bodies-q" }, t("bodies.handoff_q", { name: b.name, task: b.task || t("bodies.ho.its_task") }), " ", minutes ? h("span", { class: "dust" }, minutes + ".") : null),
      ln ? h("p", { class: "dust" }, t("bodies.handoff_line", { time: w.time(ln.ts) })) : h("p", { class: "dust" }, t("bodies.handoff_with_agent")));
    const read = h("button", { class: "pill primary", type: "button", onclick: () => {
      body.append(h("div", { class: "bodies-read" },
        h("p", { class: "ink-said" }, t("bodies.read_said", { task: b.task || t("bodies.ho.its_task") })),
        h("p", { class: "dust" }, t("bodies.read_kept")),
        h("button", { class: "pill", type: "button", onclick: reviewed }, t("bodies.mark_reviewed"))));
      read.disabled = true;
    } }, t("bodies.opt_read"));
    close = ctx.openSheet({
      title: t("bodies.handoff_title"),
      body,
      actions: [read,
        h("button", { class: "pill quiet", type: "button", onclick: () => { close(); say(t("bodies.opt_deal")); } }, t("bodies.opt_deal")),
        h("button", { class: "pill quiet", type: "button", onclick: () => { close(); say(t("bodies.opt_judge")); } }, t("bodies.opt_judge"))],
    });
  }

  /** The bars of what was spent: by body, by session, by model; words beside every bar. */
  function spentBlock(M) {
    const t = ctx.t, w = W(ctx), st = ctx.state;
    const box = h("div", { class: "bodies-spent" });
    const c = st.cost, day = c && c.day;
    if (!day) { box.append(h("p", { class: "dust" }, t("bodies.spent_none"))); return box; }
    const total = num(day.tokens) != null ? day.tokens : Object.values(day.by_body || {}).reduce((a, b) => a + (b || 0), 0) + (day.unattributed || 0);
    const n = 1 + M.clones.length;
    box.append(h("p", { class: "bodies-q" }, n === 1 ? t("bodies.cost_today_one", { words: w.tokens(total) || t("bodies.tokens_none") })
      : t("bodies.cost_today", { words: w.tokens(total) || t("bodies.tokens_none"), n: ctx.fmt.number(n, true) })));
    const bars = (title, entries) => {
      const max = Math.max(1, ...entries.map((e) => e.v));
      const ul = h("ul", { class: "bbars" });
      for (const e of entries) {
        ul.append(h("li", { class: "bbar" },
          h("span", { class: "bbar-name" }, e.label),
          h("span", { class: "bbar-track", "aria-hidden": "true" }, h("i", { style: `width:${(e.v / max) * 100}%` })),
          h("span", { class: "bbar-fig figures dust" }, e.words)));
      }
      return h("div", { class: "bbars-box" }, h("h3", { class: "eyebrow" }, title), ul);
    };
    const order = [M.prime, ...M.clones, ...M.archived].filter(Boolean);
    const byBody = order.filter((b) => day.by_body && day.by_body[b.actor] != null)
      .map((b) => ({ label: nameOf(ctx, b), v: day.by_body[b.actor], words: costOf(b) }));
    if (day.unattributed) byBody.push({ label: t("bodies.unattributed"), v: day.unattributed, words: w.tokens(day.unattributed) });
    if (byBody.length) box.append(bars(t("bodies.cost_by_body"), byBody));
    if (Array.isArray(day.by_session) && day.by_session.length) {
      box.append(bars(t("bodies.cost_by_session"), day.by_session.map((x) => {
        const b = byActor(M, x.body);
        const who = b ? nameOf(ctx, b) : t("bodies.unattributed");
        const span = x.first && x.last ? t("bodies.session_span", { from: w.time(x.first), to: w.time(x.last) }) : t("bodies.session");
        return { label: `${who} · ${span}`, v: x.tokens || 0, words: w.tokens(x.tokens) || "" };
      })));
    }
    if (day.by_model && Object.keys(day.by_model).length) {
      box.append(bars(t("bodies.cost_by_model"), Object.entries(day.by_model).map(([m, v]) => ({ label: m, v, words: w.tokens(v) || "" }))));
    }
    const asof = day.as_of ? ctx.fmt.asOf(day.as_of) : null;
    if (asof) box.append(h("p", { class: "dust figures asof-more" }, day.route_lines != null ? t("bodies.cost_asof", { as_of: asof, n: Number(day.route_lines).toLocaleString() }) : asof));
    return box;
  }

  function openSpent(M) {
    ctx.openSheet({ title: ctx.t("bodies.act.spent"), body: h("div", { class: "bodies-sheet" }, spentBlock(M)) });
  }

  // ---------------------------------------------------------------- every figure: the table, behind one act
  function handoffWord(b) {
    const t = ctx.t, w = W(ctx);
    if (b.reviewed) return b.reviewed_at ? t("bodies.handoff.reviewed_at", { time: w.time(b.reviewed_at) }) : t("bodies.handoff.reviewed");
    if (b.handoff) return b.handoffDay ? t("bodies.handoff.waits_day") : t("bodies.handoff.waits");
    return "";
  }
  function table(M, withInitials) {
    const t = ctx.t, w = W(ctx), st = ctx.state;
    const cols = ["name", "task", "state", "newest", "cost", "review", "handoff"];
    const head = h("thead", null, h("tr", null, cols.map((c) => h("th", { scope: "col" }, t("bodies.col." + c))),
      withInitials ? h("th", { scope: "col", class: "bodies-print-only" }, t("bodies.col.initials")) : null));
    const row = (b) => {
      const isDesk = st.desk && st.desk.holder === b.actor;
      const why = b.kind === "prime" ? null : differs(b);
      return h("tr", { class: `bt-row is-${b.word}` },
        h("th", { scope: "row", "data-col": t("bodies.col.name") }, h("span", { class: "bt-name" }, nameOf(ctx, b)),
          isDesk ? h("span", { class: "dust bt-sub" }, t("bodies.w.holds_desk")) : null),
        h("td", { "data-col": t("bodies.col.task") }, b.task || ""),
        h("td", { "data-col": t("bodies.col.state") }, why || t("bodies.state." + b.word)),
        h("td", { "data-col": t("bodies.col.newest"), class: "figures" }, w.newest(b.newest) || ""),
        h("td", { "data-col": t("bodies.col.cost"), class: "figures" }, costOf(b)),
        h("td", { "data-col": t("bodies.col.review"), class: "figures" }, b.review_min != null ? t("time.minutes", { n: b.review_min }) : ""),
        h("td", { "data-col": t("bodies.col.handoff"), class: b.reviewed ? "ink-agreed" : b.handoff ? "ink-said" : "" }, handoffWord(b)),
        withInitials ? h("td", { class: "bodies-print-only", "data-col": t("bodies.col.initials") }) : null);
    };
    const rows = [M.prime, ...M.clones, ...M.archived].filter(Boolean).map(row);
    return h("table", { class: "bodies-table" }, h("caption", { class: "sr-only" }, t("bodies.table_caption")), head, h("tbody", null, rows));
  }
  function machineDay(M) {
    const t = ctx.t, f = ctx.fmt, w = W(ctx);
    const hb = M.live && M.live.heartbeat;
    const box = h("div", { class: "bodies-machine" }, h("h3", { class: "eyebrow" }, t("bodies.machine_title")),
      h("p", { class: "dust" }, t("bodies.machine_kept")));
    if (!hb) return box;
    const now = f.now();
    const recent = (x) => { const d = f.date(x.to); return d && (now - d) < 24 * 3600000; };
    const slept = (hb.slept || []).filter(recent), stopped = (hb.stopped || []).filter(recent);
    if (hb.asleep) box.append(h("p", null, t("bodies.machine_asleep", { from: w.time(hb.asleep.from) })));
    if (!slept.length && !stopped.length && !hb.asleep) box.append(h("p", null, t("bodies.machine_awake")));
    if (slept.length) box.append(h("p", null, t("bodies.machine_slept"), " ",
      h("span", { class: "figures" }, slept.map((g) => t("bodies.gap", { from: w.time(g.from), to: w.time(g.to) })).join(" · "))));
    if (stopped.length) box.append(h("p", null, t("bodies.machine_stopped"), " ",
      h("span", { class: "figures" }, stopped.map((g) => t("bodies.gap", { from: w.time(g.from), to: w.time(g.to) })).join(" · "))));
    return box;
  }
  function openFigures(M) {
    const t = ctx.t;
    ctx.openSheet({
      title: t("bodies.act.figures"),
      body: h("div", { class: "bodies-sheet bodies-figures" }, h("p", { class: "dust" }, t("bodies.kit_words")),
        h("div", { class: "bodies-twin" }, table(M, false)), machineDay(M)),
      actions: [h("button", { class: "pill quiet", type: "button", onclick: printSheet }, t("bodies.print"))],
    });
  }

  /** The printed form: hidden on the screen, the whole sheet on paper (DESIGN-BODIES §9.3). */
  function paper(M) {
    const t = ctx.t;
    const box = h("section", { class: "bodies-paper", hidden: true },
      h("h2", { class: "caps" }, t("bodies.title")),
      h("div", { class: "bodies-twin" }, table(M, true)));
    const u = usage(M); if (u) box.append(u);
    box.append(spentBlock(M), machineDay(M));
    return box;
  }

  function printSheet() {
    document.documentElement.dataset.print = "bodies";
    const done = () => { delete document.documentElement.dataset.print; window.removeEventListener("afterprint", done); };
    window.addEventListener("afterprint", done);
    window.print();
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      root = h("div", { class: "bodies" });
      el.append(root);
      draw();
      window.addEventListener("resize", fit);
      if (!MASK) prepareMask().then((u) => { if (u && root && root.isConnected) draw(); });
      if (typeof ResizeObserver !== "undefined") {
        let rw = Math.round(root.clientWidth);
        ro = new ResizeObserver(() => { const w0 = Math.round(root.clientWidth); if (Math.abs(w0 - rw) > 24) { rw = w0; draw(); } });
        ro.observe(root);
      }
    },
    update(c) { ctx = c; draw(); },
    unmount() { keepAngles(); destroyConv(); room = null; if (ro) ro.disconnect(); clearTimeout(rewardTimer); window.removeEventListener("resize", fit); },
  };
}

// ------------------------------------------------------------------ launching a body (§4.2)

/**
 * The launch card: the cost first, then the yes. Not now at the left; Yes, start it at the right,
 * the larger, where the right thumb is. The yes goes to ctx.launchBody({task, from_card,
 * confirmed: true}) (the shell's call to the agent host's POST /agent/body); without it, the card
 * says so and starts nothing.
 */
function launchBody(ctx, { card = null, task = null, onClose = null } = {}) {
  const t = ctx.t, st = ctx.state;
  const c = card ? ((st.cards || []).find((x) => x.id === card) || null) : null;
  const what = (c && c.title) || task || "";
  if (!what) return null;
  const minutes = c ? (c.agent_minutes ?? c.minutes) : null;
  const tokens = c ? c.tokens_estimate : null;
  const words = W(ctx);
  const hours = minutes != null ? (minutes >= 90 ? t("bodies.about_hours", { n: ctx.fmt.number(Math.round(minutes / 60), true) })
    : minutes >= 50 ? t("bodies.about_hour") : ctx.fmt.aboutMinutes(minutes).toLowerCase().replace(/^about /, "")) : null;
  const day = st.cost && st.cost.day, ceil = st.cost && st.cost.ceiling;
  let ceilingWords = "";
  if (tokens != null && day && ceil && ceil.day_tokens) {
    const total = num(day.tokens) != null ? day.tokens : Object.values(day.by_body || {}).reduce((a, b) => a + (b || 0), 0) + (day.unattributed || 0);
    const over = total + tokens - ceil.day_tokens;
    ceilingWords = over > 0 ? t("bodies.launch_over", { share: over / ceil.day_tokens < 0.3 ? t("bodies.share_fifth") : t("bodies.share_more") })
      : t("bodies.launch_under");
  }
  const cost = hours && tokens != null ? t("bodies.launch_cost", { time: hours, tokens: words.tokens(tokens) })
    : hours ? t("bodies.launch_time_only", { time: hours }) : t("bodies.launch_no_estimate");
  const status = h("p", { class: "dust", "aria-live": "polite" });
  const box = h("section", { class: "bodies-card bodies-launch", "aria-label": t("bodies.launch_title") });
  const yes = h("button", { class: "pill primary bodies-big", type: "button" }, t("bodies.opt_start"));
  const no = h("button", { class: "pill quiet", type: "button", onclick: () => onClose && onClose() }, t("bodies.opt_not_now"));
  const briefBox = h("ol", { class: "bodies-brief", hidden: true },
    h("li", null, t("bodies.brief_who")), h("li", null, t("bodies.brief_task", { task: what })), h("li", null, t("bodies.brief_first")),
    h("li", null, t("bodies.brief_write")), h("li", null, t("bodies.brief_handoff")), h("li", null, t("bodies.brief_close")));
  const brief = h("button", { class: "link-btn bodies-brief-btn", type: "button", "aria-expanded": "false", onclick: () => {
    briefBox.hidden = !briefBox.hidden; brief.setAttribute("aria-expanded", String(!briefBox.hidden));
  } }, t("bodies.opt_brief"));
  yes.onclick = async () => {
    if (typeof ctx.launchBody !== "function") { status.textContent = t("bodies.launch_no_host"); return; }
    yes.disabled = true; no.disabled = true;
    status.textContent = t("bodies.launch_starting");
    try {
      const r = await ctx.launchBody({ task: what, from_card: card || null, confirmed: true });
      status.textContent = r && r.ok ? t("bodies.launch_started") : t("bodies.launch_refused", { why: (r && r.reason) || "" });
      if (!(r && r.ok)) { yes.disabled = false; no.disabled = false; }
    } catch { status.textContent = t("bodies.launch_refused", { why: "" }); yes.disabled = false; no.disabled = false; }
  };
  box.append(h("p", { class: "eyebrow" }, t("bodies.launch_title")),
    h("p", { class: "bodies-q" }, t("bodies.launch_what", { task: what })),
    h("p", { class: "bodies-cost-first" }, [cost, ceilingWords].filter(Boolean).join(" ")),
    brief, briefBox, status,
    h("div", { class: "bodies-acts" }, no, yes));
  return box;
}

/** offerBody(ctx, {card, task}): the same launch card, in a sheet, for a caller outside the view. */
export function offerBody(ctx, { card = null, task = null } = {}) {
  let close = null;
  const body = launchBody(ctx, { card, task, onClose: () => close && close() });
  if (!body) return;
  close = ctx.openSheet({ title: ctx.t("bodies.launch_title"), body });
}
