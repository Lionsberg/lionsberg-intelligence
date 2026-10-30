// state.js: loads the merged state, keeps it current, and carries every act.
//
// The one source of truth for every view (one deck, one truth). A view never fetches;
// it reads `ctx.state` and calls `ctx.act(...)` (see shell.js for the context).
//
//   GET /state            the merged state (engine/STATE.md + the server's `hud` block)
//   GET /stream           server-sent events; `event: state` means read /state again
//   POST /act             held by the server for the undo window, then written
//   DELETE /act/<id>      Undo
//   /agent/*, /discern    the dock's calls (DESIGN-DOCK §8.2), each carrying the token
//   /phone/claim          on the phone door: a one-time code becomes this phone's own token
//
// Without a server (opened from static hosting with ?fixture=<name>), the fixture file
// is read directly and acts are kept on this device, marked as kept here, never
// pretended written (brand: no silent fallbacks).

export const FLAGS = {
  // The standing question that closes every Deal is held for the
  // keeper's yes. Set true (or open with ?flags=standing) only after that yes.
  standing_question: false,
};

const params = new URLSearchParams(location.search);
if ((params.get("flags") || "").split(",").includes("standing")) FLAGS.standing_question = true;

const LS = {
  get(k, d) { try { const v = localStorage.getItem("hud." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("hud." + k, JSON.stringify(v)); } catch { /* private window: preference lives for this visit */ } },
};
const SS = {
  get(k, d) { try { const v = sessionStorage.getItem("hud." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { sessionStorage.setItem("hud." + k, JSON.stringify(v)); } catch { /* ignore */ } },
};

// ------------------------------------------------------------------ strings

let STRINGS = {};
export async function loadStrings() {
  const r = await fetch("strings.json", { cache: "no-store" });
  STRINGS = await r.json();
  return STRINGS;
}
/** t("deal.of", {n: 1, total: 3}). A missing key shows itself in brackets, so the gap is seen. */
export function t(key, vars) {
  let s = STRINGS[key];
  if (s == null) return `[${key}]`;
  if (typeof s !== "string") return s;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] == null ? m : String(vars[k])));
  return s;
}

// ------------------------------------------------------------------ formatting (words, never decimals)

export const fmt = {
  now() {
    const n = store.state && store.state.hud && store.state.hud.now;
    return n ? new Date(n) : new Date();
  },
  date(x) { if (!x) return null; const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(x) ? x + "T12:00:00" : x); return isNaN(d) ? null : d; },
  number(n, lower) {
    const words = STRINGS[lower ? "numbers_lower" : "numbers"] || [];
    return Number.isInteger(n) && n >= 0 && n < words.length ? words[n] : String(Math.round(n));
  },
  /** Minutes in words: "About eight minutes". Rounded to five above fifteen. */
  aboutMinutes(m) {
    m = Math.max(1, Math.round(m || 0));
    if (m === 1) return t("time.about_one_minute");
    const r = m > 15 ? Math.round(m / 5) * 5 : m;
    return t("time.about_minutes", { n: fmt.number(r, true) });
  },
  dayName(d) { const days = STRINGS.days || []; return days[d.getDay()] || ""; },
  sameDay(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); },
  daysBetween(a, b) {
    const A = new Date(a.getFullYear(), a.getMonth(), a.getDate()), B = new Date(b.getFullYear(), b.getMonth(), b.getDate());
    return Math.round((B - A) / 86400000);
  },
  /** "today" · "yesterday" · "on Tuesday" · "on 12 October" */
  when(x) {
    const d = fmt.date(x); if (!d) return null;
    const n = fmt.now(), diff = fmt.daysBetween(d, n);
    if (diff === 0) return t("time.today");
    if (diff === 1) return t("time.yesterday");
    if (diff > 1 && diff < 7) return t("time.on_day", { day: fmt.dayName(d) });
    return t("time.on_day", { day: d.toLocaleDateString(undefined, { day: "numeric", month: "long" }) });
  },
  /** "by Saturday" for the coming week, else "by 12 November" */
  by(x) {
    const d = fmt.date(x); if (!d) return null;
    const diff = fmt.daysBetween(fmt.now(), d);
    if (diff === 0) return t("time.by_day", { day: t("time.today") });
    if (diff > 0 && diff < 7) return t("time.by_day", { day: fmt.dayName(d) });
    if (diff < 0) return diff === -1 ? t("time.day_past") : t("time.days_past", { n: fmt.number(-diff, true) });
    if (diff >= 7 && diff < 14 && STRINGS["time.by_next"]) return t("time.by_next", { day: fmt.dayName(d) });   // a day in words
    return t("time.by_day", { day: d.toLocaleDateString(undefined, { day: "numeric", month: "long" }) });
  },
  time(x) { const d = fmt.date(x); return d ? d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : null; },
  /** "as of 9:14", or "as of Tuesday" when not today */
  asOf(x) {
    const d = fmt.date(x); if (!d) return null;
    return t("top.as_of", { time: fmt.sameDay(d, fmt.now()) ? fmt.time(x) : fmt.dayName(d) });
  },
  /** hour · today · older · unread */
  freshness(x) {
    const d = fmt.date(x); if (!d) return "older";
    const n = fmt.now();
    if (n - d <= 3600000) return "hour";
    if (fmt.sameDay(d, n)) return "today";
    return "older";
  },
  /** whole days to spare, in words; never a decimal, never a bare negative */
  spare(days) {
    if (days == null || isNaN(days)) return null;
    const d = Math.round(days);
    if (d === 0) return t("time.no_days_to_spare");
    if (d < 0) return d === -1 ? t("time.one_day_late") : t("time.days_late", { n: fmt.number(-d, true) });
    return d === 1 ? t("time.one_day_to_spare") : t("time.days_to_spare", { n: fmt.number(d, true) });
  },
  short(id) { return typeof id === "string" ? id.slice(0, 4) + "…" : ""; },
};

// ------------------------------------------------------------------ the store

const listeners = new Set();
const pendingListeners = new Set();

export const store = {
  state: null,
  status: "loading",          // loading · ready · error
  error: null,
  source: params.get("fixture") ? "fixture-file" : "server",
  server: false,              // true once /state answered
  pending: new Map(),         // id -> pending act
  answered: new Set(SS.get("answered", [])),   // card ids answered on this device this session
  own: new Map(SS.get("own", [])),              // id -> {type, links, body}: this session's own acts (foldOwn)
  raw: null,                                    // the state as served, before the fold
  hands: 0,                                     // the Deal's later hands asked for this session (memory only, never written)
  ownAt: SS.get("own_at", null),                // when the person's own last act was written: the served state folds it, so the as-of is at least this
  named: new Map(Object.entries(LS.get("named", {}) || {})),   // card id -> her name for it, as the host returned it (the ask of kind `keep`)
  prefs: {
    theme: params.get("theme") || LS.get("theme", "system"),       // system · night · paper
    type: params.get("type") || LS.get("type", "regular"),          // regular · large
    motion: params.get("motion") || LS.get("motion", "system"),     // system · reduce
    undo_ms: LS.get("undo_ms", 5000),
    minutes: SS.get("minutes", null),                               // the time chip, today only
    study: LS.get("study", "on"),                                   // the ICE studies itself on this machine (about sheet)
    depth: LS.get("depth", null),                                   // how much of her work the Talk shows: plain · working · full (null: the house's default)
  },
};

export function subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }
export function onPending(fn) { pendingListeners.add(fn); return () => pendingListeners.delete(fn); }
function emit() { for (const fn of listeners) { try { fn(store); } catch (e) { console.error(e); } } }
function emitPending(p) { for (const fn of pendingListeners) { try { fn(p); } catch (e) { console.error(e); } } }

export function setPref(k, v) {
  store.prefs[k] = v;
  if (k === "minutes") SS.set("minutes", v); else LS.set(k, v);
  emit();
}
// ------------------------------------------------------------------ one truth after an act

/** The person's own acts on this device this session, held or written, never undone or refused.
    Folded into the state every view reads (the same fold as serve.py's fold_own), so the top
    line, the Deal, the Map and Threads change together at the tap, and stay changed until the
    served state carries the act itself; never vanishing before it (the night test, step 2). */
const OWN_LINKS = ["answers", "anchored_to", "settles"];
const OWN_TYPES = new Set(["answer", "ratify", "decide", "say", "settle", "commit", "kept", "witness"]);
export function foldOwn(raw, acts) {
  if (!raw || typeof raw !== "object") return raw;
  const targets = new Set();
  for (const a of acts || []) {
    if (!a || !OWN_TYPES.has(a.type)) continue;
    for (const k of OWN_LINKS) for (const i of ((a.links || {})[k] || [])) if (typeof i === "string") targets.add(i);
    if (a.body && typeof a.body.card === "string") targets.add(a.body.card);
  }
  if (!targets.size) return raw;
  const st = JSON.parse(JSON.stringify(raw));
  const actor = st.actor;
  const titles = new Set((st.cards || []).filter((c) => c && targets.has(c.id)).map((c) => String(c.title || "").trim().toLowerCase()).filter(Boolean));
  let changed = false;
  const hands = [...((st.deal && st.deal.cards) || []), ...((st.deal && st.deal.beyond && st.deal.beyond.cards) || [])];   // the next hand is answered the same way
  for (const dc of hands) if (dc && targets.has(dc.id) && !dc.answered) { dc.answered = true; changed = true; }
  if (changed) st.deal.briefing = null;   // the engine's sentence describes the deal before the answer
  for (const e of (st.owed && st.owed.entries) || []) {
    if (e && e.holder === actor && (targets.has(e.id) || titles.has(String(e.title || "").trim().toLowerCase()))) e.status = "done";
  }
  for (const th of st.threads || []) if (th && targets.has(th.id)) { th.last_actor = actor; th.to = (th.to || []).filter((x) => x !== actor); }
  for (const d of st.decisions || []) if (d && (targets.has(d.id) || titles.has(String(d.title || "").trim().toLowerCase()))) d.state = "decided";
  for (const q of st.questions || []) if (q && targets.has(q.id)) q.state = "answered";
  return st;
}
/** Her names for cards, folded in like her own acts: the host's (hud.named, {card: name}, when it serves
    them) and the ones the host returned to this page when she said Keep it ({named: {card, name}}), so
    the card's face, its question in the Talk and its keepsake carry the name at once. */
export function foldNames(st) {
  if (!st || typeof st !== "object") return st;
  const served = (st.hud && st.hud.named && typeof st.hud.named === "object") ? st.hud.named : {};
  const names = new Map([...Object.entries(served), ...store.named]);
  if (!names.size) return st;
  const put = (c) => { if (c && typeof c.id === "string" && names.has(c.id)) { const n = String(names.get(c.id) || "").trim(); if (n) c.named = n; } };
  for (const c of st.cards || []) put(c);
  for (const c of (st.deal && st.deal.cards) || []) put(c);
  for (const c of (st.deal && st.deal.beyond && st.deal.beyond.cards) || []) put(c);
  return st;
}
/** A name she gave a card, from the host's answer (`{named: {card, name}}`, or the same inside `local`). */
export function setNamed(named) {
  const n = named && typeof named === "object" ? named : null;
  const card = n && typeof n.card === "string" ? n.card.trim() : "";
  const name = n && typeof n.name === "string" ? n.name.trim().slice(0, 80) : "";
  if (!card || !name) return false;
  store.named.set(card, name);
  LS.set("named", Object.fromEntries(store.named));
  if (store.state) foldNames(store.state);
  emit();
  return true;
}
function ownActs() { return [...store.own.values(), ...[...store.pending.values()].map((p) => ({ type: p.type, links: p.links, body: p.body }))]; }
function refold() { if (store.raw) store.state = foldNames(foldOwn(store.raw, ownActs())); }

export function markAnswered(id) {
  store.answered.add(id); SS.set("answered", [...store.answered]); emit();
}
export function unmarkAnswered(id) {
  store.answered.delete(id); SS.set("answered", [...store.answered]); emit();
}

export async function load() {
  token();
  const prev = store.state;
  store.status = prev ? "ready" : "loading";
  try {
    const url = store.source === "fixture-file" ? `fixtures/${encodeURIComponent(params.get("fixture"))}.json` : "/state";
    const r = ON_PHONE ? await authed(url, { cache: "no-store" }) : await fetch(url, { cache: "no-store" });
    if (ON_PHONE && r.status === 403) { store.needsPairing = true; throw new Error("pair"); }
    if (!r.ok) throw new Error(String(r.status));
    store.needsPairing = false;
    store.raw = await r.json();
    store.state = foldNames(foldOwn(store.raw, ownActs()));
    store.server = store.source === "server";
    store.status = "ready";
    store.error = null;
  } catch (e) {
    store.error = e;
    store.status = prev ? "ready" : "error";   // keep the last known state; never a blank
    store.stale = !!prev;
  }
  emit();
  return store;
}

let es = null;
export function connect() {
  if (store.source !== "server") return;
  if (ON_PHONE) {
    // an EventSource cannot carry the device token: read the stream with fetch instead
    if (es) es.close();
    if (store.needsPairing) return;   // nothing to hear until this phone has its own token
    es = sse("/stream", (ev) => { if (ev.event === "state") load(); },
      { onOpen: () => { if (store.offline) { store.offline = false; load(); } }, onDrop: () => { store.offline = true; emit(); } });
    return;
  }
  if (typeof EventSource === "undefined") return;
  if (es) es.close();
  es = new EventSource("/stream");
  es.addEventListener("state", () => { load(); });
  es.onerror = () => { store.offline = true; emit(); };
  es.onopen = () => { if (store.offline) { store.offline = false; load(); } };
}

// ------------------------------------------------------------------ the page's token
// serve.py gives its token only to the page's own first read (same host, no Origin);
// every act carries it as X-HUD-Token, so no other local process can act.
let TOKEN = null;
// The phone door (DESIGN-DOCK §4): the page is served on the machine's private-network address,
// never loopback. There the page's token is never given; this phone's own device token, given
// once for a one-time pairing code, rides on every request as X-HUD-Device.
export const ON_PHONE = store.source === "server" && !["127.0.0.1", "localhost"].includes(location.hostname);
async function token() {
  if (ON_PHONE) return null;
  if (TOKEN || store.source !== "server") return TOKEN;
  try { const r = await fetch("/token", { cache: "no-store" }); if (r.ok) TOKEN = (await r.json()).token || null; } catch { /* no server */ }
  return TOKEN;
}
async function authed(url, init = {}) {
  const send = async () => {
    const tk = await token();
    const dev = ON_PHONE ? LS.get("device", null) : null;
    return fetch(url, { ...init, headers: { ...(init.headers || {}), ...(tk ? { "X-HUD-Token": tk } : {}),
      ...(dev && dev.token ? { "X-HUD-Device": dev.token } : {}) } });
  };
  const r = await send();
  // serve.py writes a new token when it restarts; read it once more and try again (the dock's
  // conversation outlives the server, so the page must too)
  if (r.status === 403 && !ON_PHONE && TOKEN && typeof init.body !== "object") { TOKEN = null; return send(); }
  return r;
}

/** Claim this phone's own token with the one-time code shown on the computer. */
export async function claimPhone(code) {
  try {
    const r = await fetch("/phone/claim", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: String(code || "").trim(), name: "your phone" }) });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, reason: out.refused || String(r.status) };
    LS.set("device", { token: out.token, device: out.device });
    return { ok: true };
  } catch { return { ok: false, reason: "" }; }
}

/**
 * sse(url, onEvent, {onOpen, onDrop}) -> {close()}: server-sent events read with fetch, so the
 * token travels as a header, never in the address. Reconnects after three seconds.
 */
export function sse(url, onEvent, { onOpen, onDrop, onHello } = {}) {
  let stopped = false, ctrl = null;
  const run = async () => {
    while (!stopped) {
      ctrl = new AbortController();
      try {
        const r = await authed(typeof url === "function" ? url() : url, { cache: "no-store", signal: ctrl.signal });
        if (!r.ok || !r.body) throw new Error(String(r.status));
        if (onOpen) onOpen();
        const reader = r.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let i;
          while ((i = buf.indexOf("\n\n")) >= 0) {
            const block = buf.slice(0, i); buf = buf.slice(i + 2);
            let event = "message", data = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              else if (line.startsWith("data:")) data += line.slice(5).trim();
            }
            if (!data) continue;
            let obj = null; try { obj = JSON.parse(data); } catch { continue; }
            try { if (event === "hello" && onHello) onHello(obj); else onEvent({ event, data: obj }); } catch (e) { console.error(e); }
          }
        }
      } catch (e) { if (stopped) return; }
      if (stopped) return;
      if (onDrop) onDrop();
      await new Promise((res) => setTimeout(res, 3000));
    }
  };
  run();
  return { close() { stopped = true; if (ctrl) ctrl.abort(); } };
}

// ------------------------------------------------------------------ the dock's calls (DESIGN-DOCK §8.2)
// Every one carries the token. The dock never fetches itself; it calls these.

async function call(method, url, body) {
  if (store.source !== "server") return { ok: false, status: 0, away: true, out: {} };
  try {
    const r = await authed(url, method === "GET" ? { cache: "no-store" }
      : { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const out = await r.json().catch(() => ({}));
    return { ok: r.ok, status: r.status, out };
  } catch { return { ok: false, status: 0, away: true, out: {} }; }
}
export const agent = {
  list: () => call("GET", "/agent/list"),
  /** wake and say are sent only from the player's own tap: confirmed is part of the call. */
  wake: (agentId, conversation) => call("POST", "/agent/wake", { agent: agentId, conversation, confirmed: true }),
  // `page` (the Talk): what the page itself shows and said, so your agent knows it: {line, question, options, local_answers}
  say: (agentId, conversation, text, about, page) => call("POST", "/agent/say", { agent: agentId, conversation, text, about, page, confirmed: true }),
  stop: (conversation) => call("POST", "/agent/stop", { conversation }),
  mode: (agentId, mode) => call("POST", "/agent/mode", { agent: agentId, mode }),
  /** the harness's own modes {current, modes: [{id, name, description, words, face}]} (DESIGN-TALK.md, the trust layer) */
  modes: (agentId) => call("GET", `/agent/mode?agent=${encodeURIComponent(agentId)}`),
  /** the whole figures block with every raw field the harness gave (the trust layer's Full depth) */
  figures: (agentId) => call("GET", `/agent/figures?agent=${encodeURIComponent(agentId)}`),
  /** her answer to an ask; a `keep` answered Keep it may return the name she gave a card ({named: {card, name}}),
      kept per card in the fold so the card shows it at once */
  answer: async (conversation, ask, answer) => {
    const r = await call("POST", "/agent/answer", { conversation, ask, answer });
    if (r.ok && r.out) setNamed(r.out.named || (r.out.local && r.out.local.named));
    return r;
  },
  offer: (conversation, offer, state, line) => call("POST", "/agent/offer", { conversation, offer, state, line }),
  prefs: (agentId, prefs) => call("POST", "/agent/prefs", { agent: agentId, ...prefs }),
  routes: (conversation, turn) => call("GET", `/agent/routes?conversation=${encodeURIComponent(conversation)}&turn=${encodeURIComponent(turn)}`),
  /** The command line: a pseudo-terminal in the same home, started only on the player's tap;
      a second conversation with the agent, never the live one. Never offered on the phone door. */
  ptyOpen: (agentId) => call("POST", "/agent/pty/open", { agent: agentId, confirmed: true }),
  ptyWrite: (pty, data) => call("POST", "/agent/pty/write", { pty, data }),
  ptyClose: (pty) => call("POST", "/agent/pty/close", { pty }),
  ptyStream(pty, onEvent) {
    if (store.source !== "server") return { close() {} };
    let n = 0;
    return sse(() => `/agent/pty/stream?pty=${encodeURIComponent(pty)}&since=${n}`,
      ({ data }) => { if (data && typeof data.n === "number") n = data.n + 1; onEvent(data); }, {});
  },
  /** the conversation's events; calls onEvent(ev) for each, onHello({epoch, count}) on every (re)connect */
  stream(conversation, since, onEvent, onHello, onDrop) {
    if (store.source !== "server") return { close() {} };
    let n = since || 0;
    return sse(() => `/agent/stream?conversation=${encodeURIComponent(conversation)}&since=${n}`,
      ({ data }) => { if (data && typeof data.n === "number") n = data.n + 1; onEvent(data); },
      { onHello: (h) => { const reset = onHello ? onHello(h) : false; if (reset) n = 0; }, onDrop });
  },
};
/** A person's judgment of an answer (human-only): sent only from the person's own gesture. */
/** GET /card/<id>: the record's lines about one card, read-only (the full card's story). */
export const cardStory = (id) => call("GET", "/card/" + encodeURIComponent(id));
export const discern = (route, verdict, rating, note) => call("POST", "/discern", { route, verdict, rating, note, confirmed: true });
/** A voice note from the phone: the computer's own speech model turns it into words, for the
    player to read and send. The audio is deleted on the computer unless keep is true. */
export async function voice(file, keep) {
  try {
    const r = await authed(`/voice${keep ? "?keep=true" : ""}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file });
    const out = await r.json().catch(() => ({}));
    return { ok: r.ok, status: r.status, out };
  } catch { return { ok: false, status: 0, out: {} }; }
}
export const phone = {
  listen: (on) => call("POST", "/phone/listen", { on, confirmed: true }),
  pair: () => call("POST", "/phone/pair", {}),
  revoke: (device) => call("DELETE", `/phone/${encodeURIComponent(device)}`),
};

// ------------------------------------------------------------------ act()

// A mirror of engine/types.json's human_only types (2026-10-24). The server reads the
// registry itself and refuses any of these not confirmed by the person; this list only lets
// the HUD refuse early and say so.
const HUMAN_ONLY = new Set(["settle", "commit", "kept", "witness", "decide", "ratify", "delegate",
  "revoke", "join", "publish", "turn", "discern", "posture", "affirm", "shape", "part", "vote"]);

/**
 * act(type, body, links, holon, opts) -> a pending act
 *   opts.confirmed  true when a person's own tap confirmed it (required for a person's own acts)
 *   opts.sheet_token for publish (from openPublishSheet in shell.js)
 *   opts.label      the line the toast shows
 *   opts.onUndo     called when the person undoes it
 * The pending act: {id, type, holon, status, writesAt, label, undo(), done}
 *   status: holding · written · undone · refused · kept-here
 */
export function act(type, body = {}, links = {}, holon = null, opts = {}) {
  const undoMs = Math.max(5000, Math.min(15000, opts.undo_ms || store.prefs.undo_ms || 5000));
  const p = {
    id: "local-" + Math.random().toString(16).slice(2, 10),
    type, holon, body, links, label: opts.label || "",
    status: "holding", serverId: null,
    writesAt: Date.now() + undoMs, undoMs,
    onUndo: opts.onUndo || null,
    quiet: opts.quiet === true,     // the dock's own layout change: no toast (the dock is its own notice)
  };
  if (HUMAN_ONLY.has(type) && opts.confirmed !== true) {
    p.status = "refused"; p.reason = "a person's own act needs the person's confirmation";
    emitPending(p);
    p.done = Promise.resolve(p);
    return p;
  }
  let resolveDone;
  p.done = new Promise((res) => { resolveDone = res; });
  store.pending.set(p.id, p);
  refold();
  emit();   // every view reads the folded state at the tap

  const finish = (status) => {
    if (p.status !== "holding") return;
    p.status = status;
    clearTimeout(p.timer);
    store.pending.delete(p.id);
    // written or kept here: it stays folded in; undone or refused: the fold lets it go
    if (status !== "undone" && status !== "refused" && OWN_TYPES.has(p.type)) {
      store.own.set(p.id, { type: p.type, links: p.links, body: p.body });
      SS.set("own", [...store.own.entries()].slice(-200));
      store.ownAt = fmt.now().toISOString(); SS.set("own_at", store.ownAt);   // the page's own clock (a fixture's, when served one)
    }
    refold();
    emit();
    emitPending(p);
    resolveDone(p);
  };

  p.undo = async () => {
    if (p.status !== "holding") return false;
    if (p.serverId) {
      try { await authed(`/act/${p.serverId}`, { method: "DELETE" }); } catch { /* the window is local too */ }
    } else {
      const q = LS.get("kept_here", []).filter((x) => x.id !== p.id);
      LS.set("kept_here", q);
    }
    if (p.onUndo) p.onUndo(p);
    finish("undone");
    return true;
  };

  const payload = { type, holon, body, links, audience: "holon", hold_ms: undoMs, confirmed: opts.confirmed === true };
  if (opts.sheet_token) payload.sheet_token = opts.sheet_token;

  const keepHere = () => {
    p.local = true;
    const q = LS.get("kept_here", []);
    q.push({ id: p.id, at: new Date().toISOString(), ...payload });
    LS.set("kept_here", q);
    p.timer = setTimeout(() => finish("kept-here"), undoMs);
  };

  if (store.source !== "server") {
    keepHere();
  } else {
    authed("/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      .then(async (r) => {
        const out = await r.json().catch(() => ({}));
        if (!r.ok) { p.reason = out.refused || String(r.status); finish("refused"); return; }
        p.serverId = out.pending;
        const left = Math.max(0, new Date(out.writes_at).getTime() - Date.now());
        p.writesAt = Date.now() + (isNaN(left) ? undoMs : left);
        // once the hold has passed, ask what the act became: p.line_id is the written line's id
        p.timer = setTimeout(async () => {
          for (let i = 0; i < 4 && p.status === "holding"; i++) {
            try {
              const o = await (await authed(`/act/${p.serverId}`, { cache: "no-store" })).json();
              if (o.status === "written") { p.line_id = o.line_id || null; p.signed = !!o.signed; break; }
              if (o.status === "refused") { p.reason = o.refused || "the record refused the line"; finish("refused"); return; }
              if (o.status !== "holding") break;
            } catch { break; }
            await new Promise((res) => setTimeout(res, 400));
          }
          finish("written");
        }, (isNaN(left) ? undoMs : left) + 200);
      })
      .catch(() => keepHere());
  }
  emitPending(p);
  return p;
}

/** Ask the server for the publish sheet's one-time token (the only route outward). */
export async function publishToken() {
  if (store.source !== "server") return null;
  try { const r = await authed("/publish-sheet", { method: "POST" }); return (await r.json()).token || null; } catch { return null; }
}

/** The pending act for the most recent hold, for the U key. */
export function latestPending() {
  let last = null;
  for (const p of store.pending.values()) if (!last || p.writesAt > last.writesAt) last = p;
  return last;
}

// ------------------------------------------------------------------ plain readers (no computing)

// ------------------------------------------------------------------ the one order of what is owed

/** What one owed thing (an owed entry or a Deal card) weighs: its card, its by-when in days from
    now (negative when past), and whether the whole waits on it. */
function stakeOf(st, item) {
  const cards = (st && st.cards) || [];
  const c = cards.find((k) => k.id === item.id) || (item.title ? cards.find((k) => k.holon === item.holon && k.title === item.title) : null) || null;
  const owed = ((st && st.owed && st.owed.entries) || []).find((e) => e.id === item.id && e.holder === st.actor) || null;
  const by = (c && c.by) || (owed && owed.due) || item.due || item.by || null;
  const d = by ? fmt.date(by) : null;
  const path = new Set([...((st.path && st.path.critical) || []), ...((st.path && st.path.system) || [])]);
  return { card: c, by, days: d ? fmt.daysBetween(fmt.now(), d) : null,
    whole: !!(item.whole_waits || (c && (c.system_critical || c.critical)) || path.has(item.id) || (c && path.has(c.id))) };
}
/** The one order (so the Map and the Deal never name different firsts): past its by-when
    first, the most days past leading; then what the whole waits on; then the nearest by-when;
    then the id, so the order is the same on every view and every visit. */
export function byStakeOrder(st, items) {
  return items.map((x) => ({ x, k: stakeOf(st, x) })).sort((a, b) => {
    const la = a.k.days != null && a.k.days < 0, lb = b.k.days != null && b.k.days < 0;
    if (la !== lb) return la ? -1 : 1;
    if (la && lb && a.k.days !== b.k.days) return a.k.days - b.k.days;
    if (a.k.whole !== b.k.whole) return a.k.whole ? -1 : 1;
    const da = a.k.days == null ? 1e9 : a.k.days, db = b.k.days == null ? 1e9 : b.k.days;
    if (da !== db) return da - db;
    return String(a.x.id).localeCompare(String(b.x.id));
  }).map((y) => y.x);
}

export const read = {
  /** What is owed by the wearer, open, in the one order. Every view that counts or names what
      waits on the person reads this list (after the fold of her own acts). */
  owedByStake(st) {
    const rows = ((st && st.owed && st.owed.entries) || []).filter((e) => e && e.holder === st.actor && e.status !== "done" && e.status !== "kept");
    return byStakeOrder(st, rows);
  },
  /** first_owed: the first of that list, and the card it is about (or null). */
  firstOwed(st) {
    const e = read.owedByStake(st)[0];
    return e ? { ...e, card: stakeOf(st, e).card } : null;
  },
  /** The person's keepsakes, oldest first: the `keepsake` lines of her own record as the server serves
      them (hud.keepsakes: [{card, title, name, mark, at}]), and those she made this sitting that are
      still in their Undo window, so a mark shows at the tap and lives in her record after it. One per card. */
  keepsakes(st) {
    const served = (st && st.hud && Array.isArray(st.hud.keepsakes)) ? st.hud.keepsakes : [];
    const held = [...store.pending.values()].filter((p) => p.type === "keepsake" && p.status === "holding")
      .map((p) => ({ ...(p.body || {}), at: new Date(p.writesAt - p.undoMs).toISOString(), holding: true }));
    const out = [], seen = new Set();
    for (const k of [...served, ...held]) {
      if (!k || typeof k !== "object") continue;
      const key = typeof k.card === "string" && k.card ? k.card : JSON.stringify(k);
      if (seen.has(key)) continue;
      seen.add(key); out.push(k);
    }
    return out;
  },
  /** The card a Deal card or owed entry is about, for comparing "firsts" across views. */
  cardOfOwed(st, item) { return item ? stakeOf(st, item).card : null; },
  holons(st) { return (st && Array.isArray(st.holons)) ? st.holons : []; },
  holon(st, id) { return read.holons(st).find((h) => h.id === id) || null; },
  holonName(st, id) {
    const h = read.holon(st, id);
    if (h) return h.name;
    const s = ((st && st.hud && st.hud.sources) || []).find((x) => x.holon === id);
    return s ? s.name : "";
  },
  card(st, id) { return ((st && st.cards) || []).find((c) => c.id === id) || null; },
  /** her own name for a card, when she gave one (the fold's `named`), else "" */
  cardName(st, id) {
    if (!id) return "";
    const hit = [read.card(st, id), ...((st && st.deal && st.deal.cards) || []), ...((st && st.deal && st.deal.beyond && st.deal.beyond.cards) || [])]
      .find((c) => c && c.id === id && c.named);
    return (hit && String(hit.named).trim()) || store.named.get(id) || "";
  },
  sources(st) { return (st && st.hud && Array.isArray(st.hud.sources)) ? st.hud.sources : []; },
  unreadable(st) { return read.sources(st).filter((s) => s.readable !== true); },
  /** open · names-hidden · sealed, from state.rooms[holon].posture (STATE v1); open when none */
  posture(st, holonId) {
    const r = st && st.rooms && st.rooms[holonId];
    const p = r && r.posture && (typeof r.posture === "string" ? r.posture : r.posture.posture);
    return p || "open";
  },
  /** the actor's role in a holon, from state.roles (STATE v1): keeper · member · guest · agent */
  role(st, actor, holonId) { const r = st && st.roles && st.roles[holonId]; return (r && r[actor]) || null; },
  actorKind(st, actor) { return typeof actor === "string" && actor.startsWith("agent:") ? "agent" : "person"; },
  /** An actor is shown by role, never by name, unless the viewer is that actor:
      "you" · "the keeper" · "your agent" · "an agent" · "a member". Under a posture that hides names
      (names-hidden, sealed) every other actor reads "a member". */
  who(st, actor, holonId) {
    if (!actor) return "";
    if (actor === st.actor) return t("app.you");
    if (read.posture(st, holonId) !== "open") return t("app.a_member");
    if (read.actorKind(st, actor) === "agent") {
      const a = ((st && st.actors) || []).find((x) => x.id === actor);
      return a && a.for === st.actor ? t("app.agent_default") : t("app.an_agent");
    }
    const role = read.role(st, actor, holonId);
    const h = read.holon(st, holonId);
    if (role === "keeper" || (!role && h && h.keeper === actor)) return t("app.the_keeper");
    if (role === "guest") return t("app.a_guest");
    return t("app.a_member");
  },
  layouts(st) { return (st && st.hud && Array.isArray(st.hud.layouts)) ? st.hud.layouts : []; },
  /** The kept tally the Turn and the Deal's desk line say, with the late ones counted out of it,
      so "three of three kept" never stands above a gap that says one was a day late. Kept late
      means kept (or claimed kept) with gap_days above zero; only commitments in the tally's own
      list (`kept.commitments`) and, when the list is absent, the keeper's own are counted. */
  keptLate(st, actor, holon) {
    const kept = (st && st.kept) || {};
    const ids = Array.isArray(kept.commitments) ? new Set(kept.commitments) : null;
    return ((st && st.commitments) || []).filter((k) => (k.status === "kept" || k.status === "kept-unwitnessed")
      && k.gap_days != null && k.gap_days > 0
      && (holon ? k.holon === holon : k.keeper === actor)
      && (!ids || ids.has(k.id) || k.keeper === actor)).length;
  },
};
