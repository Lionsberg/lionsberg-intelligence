// shell.js: the HUD's frame. Routing, the three layouts, the top line, the holon ribbon,
// sheets, theming, large type, reduced motion, the `layout` event's fold, the hand
// customization menu, the toasts that carry every act's five seconds of Undo.
//
// ============================================================================
// THE PLUG-IN CONTRACT FOR VIEWS (DESIGN §8.2). The one place it is stated.
// ============================================================================
//
// A view is one ES module beside this file. Its default export is a factory:
//
//     export default function create() {
//       return {
//         mount(el, ctx)  { ... },   // el: an empty <section> the shell owns; draw into it
//         update(ctx)     { ... },   // the state, filter, layout or prefs changed; redraw
//         unmount()       { ... },   // stop timers and animations; the shell empties el
//         key(e, ctx)     { ... },   // optional: a keydown while no sheet is open and no
//                                    // field has focus; return true when handled
//       };
//     }
//
// A factory, never a shared object, because a view may be mounted twice at once (in a
// layout and in a sheet). The shell finds a view by its id:
//     deal · commitments · whole · queue        (deal.js, queue.js)
//     map · chain · board                       (map.js, chain.js, board.js)
//     room · ledger · turn · record             (play.js, ledger.js, turn.js, record.js)
// A missing module shows "This view is still being built." in its place, never a blank.
//
// The context `ctx` (read-only; a new object on every update):
//     ctx.state     the merged state (engine/STATE.md, plus the server's `hud` block)
//     ctx.filter    the holon id the ribbon narrowed to, or null for All
//     ctx.layout    the active layout {name, views, hidden, holons, type, theme, density}
//     ctx.slot      where this view sits: "main" · "aside" · "left" · "full" · "sheet"
//     ctx.density   "full" · "small" (folded, e.g. the Deal at the top of the Cell layout)
//     ctx.route     {name, arg, params}, e.g. {name: "board", arg: "<holon id>"}
//     ctx.prefs     {theme, type, motion, undo_ms, reducedMotion: bool, large: bool}
//     ctx.loading   true while the last known state is shown and a new one is read
//     ctx.offline   true when the stream dropped (show each record's "last heard")
//     ctx.selected  the selected card id (selection travels between views)
//     ctx.t(key, vars), ctx.fmt.*, ctx.read.*   strings, words for times, plain readers
//     ctx.act(type, body, links, holon, opts) -> a pending act with .undo() (state.js)
//          opts.confirmed must be true for a person's own acts (answer, settle, decide,
//          ratify, commit, kept, witness, publish...): pass it only from that person's tap.
//     ctx.select(id)          select a card (other views highlight it)
//     ctx.go(hash)            navigate, e.g. ctx.go("#/map")
//     ctx.openCard(id, {from, hint})   the full card (card-full.js) as a sheet over the current
//          view: everything the state and the record hold about it; `hint` {title, holon} when the
//          state may not carry the thing (a mail line)
//     ctx.openSheet({title, body, actions}) -> close()     a sheet in the house style
//     ctx.openPublish({holon, what, onPublish})            the one route outward (§4.10)
//     ctx.animate(el, keyframes, options) -> Animation | null   the Web Animations API,
//          already a no-op under reduced motion (use it for every scene-level motion)
//     ctx.card: { h, cardModel, renderCard }   the one card face (card.js)
//     ctx.launchBody({card}) opens the Bodies launch sheet (cost first); ({task, from_card,
//          confirmed: true}) starts the body on the person's yes
//     ctx.say(room, text, {parent, now, part})   the Talk's say (confirmed: true is sent);
//          kept on the device, "waiting to send", when the server has no /say
//     ctx.mail: { read(id), line(id), send(lineId, to) }   /mail/*, each on the person's tap
//     ctx.act(...).done resolves with the pending act, carrying lineId once written
//     ctx.dock: { open, setOpen(bool) }        the dock's pane, open or collapsed (DESIGN-DOCK §2.1)
//
// THE DOCK. The conversation pane, dock.js, is mounted once at boot in the slot
// "dock" (an <aside> beside <main>), in every layout, and is never unmounted by a remount, so
// what the player is typing survives a change of layout. Its open or collapsed state is kept
// in the `layout` event's `dock` field (written quietly, by the player's own tap).
//
// A view never fetches, never writes a file, never reads another view's internals, never
// computes a schedule or a figure the state lacks. Where the state lacks a field the view
// shows nothing for it (a fact not computed is absent; the about sheet says why once). The bar: never "Not computed yet" on screen.
// Every string from strings.json; every value from tokens.css.
// ============================================================================

import { store, load, connect, subscribe, onPending, t, fmt, read, act, setPref, loadStrings,
  latestPending, publishToken, FLAGS, claimPhone, cardStory } from "./state.js";
import { h, cardModel, renderCard } from "./card.js";
import { agentSettings } from "./dock.js";

const BUILTIN = {
  deal: () => import("./deal.js").then((m) => m.default),
  commitments: () => import("./deal.js").then((m) => m.commitments),
  whole: () => import("./deal.js").then((m) => m.whole),
  queue: () => import("./queue.js").then((m) => m.default),
  talk: () => import("./talk-place.js").then((m) => m.default),
};
const PLUGINS = { map: "./map.js", chain: "./chain.js", board: "./board.js", wall: "./wall.js", room: "./play.js",
  ledger: "./ledger.js", turn: "./turn.js", record: "./record.js",
  threads: "./threads.js", bodies: "./bodies.js" };

// The three default layouts (DESIGN §3). A `layout` event may reorder or hide; it can never
// remove "whole" (the privacy line and the way to the whole) nor the Back control.
const DEFAULT_LAYOUTS = {
  // the bar: the Deal's desk grows no dashboard rail; the commitments move to the aside at 1024+
  player: { name: "player", main: ["deal", "commitments", "whole"], aside: [], left: [] },
  cell: { name: "cell", main: ["deal", "board"], aside: ["commitments", "chain", "turn"], left: [], density: { deal: "small" } },
  room: { name: "room", main: ["deal", "room"], aside: [], left: [], density: { deal: "small" } },
};
const LOCKED = new Set(["whole"]);
const ROUTE_VIEWS = { talk: "talk", queue: "queue", map: "map", board: "chain", chain: "chain", wall: "wall", room: "room",
  ledger: "ledger", turn: "turn", record: "record", threads: "threads", bodies: "bodies" };

// The ICE's tabs (DESIGN.md): a few main views, each a sort of one record.
// The frame: the places stay at the bottom, Bodies among the main ones (never buried in a menu): six
// places, set once in the order of use and never re-sorted, at the foot beside the agent's door at
// every width; the rest behind the one quiet More. No top row. No Board place (the Chain folds it).
// The Talk (DESIGN-TALK.md, proposal): the same house with the other views behind one menu; the Talk
// is the first place. At the foot, at every width: Talk · Agents · More. Every other view behind More, in
// the order of use, set once.
const TABS = [["talk", "#/talk"], ["bodies", "#/bodies"]];
const MORE_PLACES = [["deal", "#/deal"], ["threads", "#/threads"], ["map", "#/map"], ["chain", "#/chain"], ["wall", "#/wall"], ["room", "#/room"],
  ["ledger", "#/ledger"], ["record", "#/record"]];
// The way back to the vendor's own app, behind More, when ours breaks (DESIGN-TALK §7). A home may
// name another in its layout event (`desktop_app`); the address is never shown on screen.
const DESKTOP_APP = "claude://";
const placeLabel = (id) => (id === "threads" ? t("threads.tab") : t("places." + id).startsWith("[") ? t("tabs." + id) : t("places." + id));

// A card is long enough to give to a body when your agent's minutes for it pass this line
// (DESIGN-BODIES §4.2: "more than about forty minutes of the agent's work"). The Fewer dial
// (DESIGN-ATTENTION §2: at "fewer" and below, nothing is offered to a body) can only lower it.
const LONG_CARD_MINUTES = 40;

const ui = {
  route: { name: "deal", arg: null, params: new URLSearchParams() },
  filter: null,
  selected: null,
  mounted: [],        // [{id, inst, el, slot, density}]
  sheet: null,
  layoutOverride: null,
  booted: false,
  dock: null,         // the dock's entry {id, inst, el, slot}
  dockOpen: false,
};

// ------------------------------------------------------------------ routes (§8.3)

function parseRoute() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, q] = raw.split("?");
  const params = new URLSearchParams(location.search);
  if (q) for (const [k, v] of new URLSearchParams(q)) params.set(k, v);
  const [name, ...rest] = (path || "talk").split("/");
  return { name: name || "talk", arg: rest.length ? decodeURIComponent(rest.join("/")) : null, params };
}
function go(hash) { if (location.hash !== hash) location.hash = hash; else onRoute(); }

// ------------------------------------------------------------------ prefs and theming

function systemLarge() {
  const px = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  return px >= 16 * 1.3;
}
function effectivePrefs(layout) {
  const p = store.prefs;
  const theme = p.theme !== "system" ? p.theme : (layout.theme && layout.theme !== "system" ? layout.theme : "system");
  const type = p.type === "large" || layout.type === "large" || systemLarge() ? "large" : "regular";
  const reducedMotion = p.motion === "reduce" || matchMedia("(prefers-reduced-motion: reduce)").matches;
  const undo_ms = Math.max(5000, Math.min(15000, layout.undo_ms || p.undo_ms || 5000));
  return { ...p, theme, type, large: type === "large", reducedMotion, undo_ms };
}
function applyTheme(prefs) {
  const root = document.documentElement;
  if (prefs.theme === "night" || prefs.theme === "paper") root.dataset.theme = prefs.theme;
  else delete root.dataset.theme;
  if (prefs.large) root.dataset.type = "large"; else delete root.dataset.type;
  if (store.prefs.motion === "reduce") root.dataset.motion = "reduce"; else delete root.dataset.motion;
  const meta = document.querySelector('meta[name="theme-color"]:not([media])');
  if (meta) meta.content = getComputedStyle(root).getPropertyValue("--ground").trim();
}

// ------------------------------------------------------------------ layouts (the fold of `layout` events)

function homeId(st) {
  const hs = read.holons(st);
  const home = hs.find((x) => x.keeper === st.actor && x.kind === "person") || hs[0];
  return home ? home.id : null;
}
function activeLayout() {
  const st = store.state || {};
  const want = ui.route.params.get("layout");
  const events = read.layouts(st);
  let ev = null;
  if (ui.layoutOverride) ev = ui.layoutOverride;
  else if (want) ev = events.find((l) => l.name === want) || null;
  else ev = events.find((l) => l.default) || null;
  const name = (ev && ev.name) || want || "player";
  const base = DEFAULT_LAYOUTS[name] || DEFAULT_LAYOUTS.player;
  let main = [...base.main], aside = [...base.aside], left = [...base.left];
  if (ev && Array.isArray(ev.views) && ev.views.length) {
    const asideSet = new Set(base.aside), leftSet = new Set(base.left);
    const ordered = ev.views.filter((v) => typeof v === "string");
    main = ordered.filter((v) => !asideSet.has(v) && !leftSet.has(v));
    aside = ordered.filter((v) => asideSet.has(v)).concat(base.aside.filter((v) => !ordered.includes(v)));
    left = ordered.filter((v) => leftSet.has(v)).concat(base.left.filter((v) => !ordered.includes(v)));
    for (const v of base.main) if (!main.includes(v) && !ordered.includes(v) && LOCKED.has(v)) main.push(v);
  }
  const hidden = new Set(((ev && ev.hidden) || []).filter((v) => !LOCKED.has(v)));
  return {
    name, event: ev, base,
    main: main.filter((v) => !hidden.has(v)), aside: aside.filter((v) => !hidden.has(v)), left: left.filter((v) => !hidden.has(v)),
    hidden: [...hidden], views: [...main, ...aside, ...left],
    holons: (ev && ev.holons) || [], type: (ev && ev.type) || "regular", theme: (ev && ev.theme) || "system",
    density: (ev && ev.density) || "calm", undo_ms: ev && ev.undo_ms, densities: base.density || {},
  };
}
function layoutNames() {
  const names = ["player", "cell", "room"];
  for (const l of read.layouts(store.state || {})) if (!names.includes(l.name)) names.push(l.name);
  return names;
}

/** A hand change: write a `layout` event to the home holon, by the person's own tap. */
function writeLayout(next, label) {
  const st = store.state;
  const L = activeLayout();
  const body = { name: L.name, views: next.views, hidden: next.hidden, holons: L.holons, type: next.type || L.type,
    theme: next.theme || L.theme, density: L.density, default: true, dock: ui.dockOpen ? "open" : "collapsed",
    ...(L.event && L.event.phone ? { phone: L.event.phone } : {}) };
  ui.layoutOverride = { ...body, id: null, actor: st.actor };
  const p = act("layout", body, {}, homeId(st), { confirmed: true, label: label || t("layout.saved"), undo_ms: ctxPrefs().undo_ms,
    onUndo: () => { ui.layoutOverride = null; remount(); } });
  p.done.then((r) => { if (r.status !== "holding") setTimeout(() => { if (r.status !== "undone") { /* the state catches up on its own */ } }, 0); });
  remount();
}

// ------------------------------------------------------------------ the context

let prefsCache = null;
function ctxPrefs() { return prefsCache || store.prefs; }

function makeCtx(entry) {
  const L = activeLayout();
  return Object.freeze({
    state: store.state || {},
    filter: ui.filter,
    layout: { name: L.name, views: L.views, hidden: L.hidden, holons: L.holons, type: L.type, theme: L.theme, density: L.density },
    slot: entry.slot,
    density: entry.density || "full",
    route: ui.route,
    prefs: ctxPrefs(),
    loading: store.status === "loading" || !!store.loadingAgain,
    offline: !!store.offline,
    selected: ui.selected,
    t, fmt, read, flags: FLAGS,
    act: (type, body, links, holon, opts = {}) => withLineId(act(type, body, links, holon, { undo_ms: ctxPrefs().undo_ms, ...opts })),
    select(id) { ui.selected = id; updateAll(); },
    go,
    openCard: (id, opts) => openCard(id, false, opts || {}),
    openSheet,
    openSettings: () => openSettings(),
    openPublish,
    animate,
    card: { h, cardModel, renderCard },
    launchBody,
    say,
    mail,
    longCard,
    home: homeId(store.state || {}),
    dock: { open: ui.dockOpen, setOpen: setDockOpen },
  });
}

// ------------------------------------------------------------------ the dock's pane (DESIGN-DOCK §2.1)

function applyDock() { document.documentElement.dataset.dock = ui.dockOpen ? "open" : "collapsed"; }
let dockTimer = null;
function setDockOpen(open) {
  open = !!open;
  if (open === ui.dockOpen) return;
  ui.dockOpen = open;
  applyDock();
  if (ui.dock && ui.dock.inst && ui.dock.inst.update) { try { ui.dock.inst.update(makeCtx(ui.dock)); } catch (e) { console.error("dock:", e); } }
  // remembered per layout, in the layout event; quietly, once the player's choice has settled
  clearTimeout(dockTimer);
  dockTimer = setTimeout(() => {
    const L = activeLayout();
    const want = ui.dockOpen ? "open" : "collapsed";
    if ((L.event && L.event.dock) === want || !store.server) return;
    const body = { name: L.name, views: L.views, hidden: L.hidden, holons: L.holons, type: L.type, theme: L.theme,
      density: L.density, default: true, dock: want, ...(L.event && L.event.phone ? { phone: L.event.phone } : {}) };
    act("layout", body, {}, homeId(store.state || {}), { confirmed: true, quiet: true });
  }, 1500);
}
async function mountDock() {
  if (ui.dock || !$.dock) return;
  const entry = { id: "dock", slot: "dock", density: "full", el: $.dock, inst: null };
  ui.dock = entry;
  try {
    const mod = await import("./dock.js");
    entry.inst = mod.default();
    entry.inst.mount($.dock, makeCtx(entry));
  } catch (e) {
    console.error("dock:", e);
    $.dock.textContent = "";
  }
}

function animate(el, keyframes, options) {
  if (!el || !el.animate || ctxPrefs().reducedMotion) return null;
  try { return el.animate(keyframes, options); } catch { return null; }
}
function cssMs(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v.endsWith("ms") ? parseFloat(v) : v.endsWith("s") ? parseFloat(v) * 1000 : parseFloat(v) || 0;
}
function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

// ------------------------------------------------------------------ the frame

const $ = {};

function buildFrame() {
  const app = document.getElementById("app");
  app.textContent = "";
  $.skip = h("a", { class: "skip", href: "#current-card" }, t("app.skip"));
  $.top = h("header", { class: "top", role: "banner" });
  $.main = h("main", { class: "views", id: "main" });
  $.toasts = h("div", { class: "toasts", "aria-live": "polite", "aria-atomic": "false" });
  $.live = h("div", { class: "sr-only", "aria-live": "polite" });
  $.dock = h("aside", { class: "dock", id: "dock", "aria-label": t("dock.label") });
  // the Undo line sits in the flow under the top line: it never covers a card
  app.append($.skip, $.top, $.toasts, $.main, $.dock, $.live);
  if (!document.querySelector('link[href="dock.css"]')) {
    const link = h("link", { rel: "stylesheet", href: "dock.css" });
    const print = document.querySelector('link[href="print.css"]');
    if (print) print.before(link); else document.head.append(link);
  }
  document.title = t("app.title");
}

function renderTop() {
  const st = store.state || {};
  $.top.textContent = "";
  const isHome = ui.route.name === "deal";
  const line = h("div", { class: "top-line" });
  // no "Back to the deal": the Deal is the first place, always in the same spot
  line.append(h("span", { class: "wordmark", "aria-hidden": "true" }, t("app.wordmark")));
  const asOf = h("button", { class: "day figures as-of-btn", "aria-expanded": String(!!ui.ribbonOpen), "aria-controls": "ribbon",
    title: t("top.as_of_open"), onclick: () => { ui.ribbonOpen = !ui.ribbonOpen; renderTop(); } }, topLineText(st));
  line.append(asOf);
  // the one More: marked by weight when the place shown is one of those behind it
  line.append(h("button", { class: "link-btn top-more", onclick: openMenu, "aria-haspopup": "dialog",
    "aria-current": MORE_PLACES.some(([id]) => id === ui.route.name) ? "page" : null }, t("app.more")));
  $.top.append(line);
  $.top.append(renderTabs(st, "tabs"));
  // the places at the foot on a phone (CSS shows one or the other by width; same marks, same order)
  const foot = renderTabs(st, "places");
  if ($.places) $.places.replaceWith(foot); else document.getElementById("app").append(foot);
  $.places = foot;
  // "waiting on you" is the rail's one line (the dock), never a second line up here
  // the records she holds sit behind the "as of" line: one tap opens them (never on the first screen)
  if (ui.ribbonOpen && (read.holons(st).length || read.unreadable(st).length)) $.top.append(renderRibbon(st));
}

// ------------------------------------------------------------------ the tabs, and the numeral on Threads and Mail

let unreadFn = null;   // threads.js's unreadFromOtherHouses, loaded once
function threadsNumeral(st) {
  const b = st && st.badges;
  if (b && typeof b.threads_and_mail === "number") return b.threads_and_mail;
  if (!unreadFn) {
    import("./threads.js").then((m) => { unreadFn = m.unreadFromOtherHouses || (() => 0); renderTop(); }).catch(() => { unreadFn = () => 0; });
    return 0;
  }
  try { return unreadFn(makeCtx({ slot: "top", density: "full" })) || 0; } catch { return 0; }
}
function renderTabs(st, kind) {
  const cur = ui.route.name === "card" ? "deal" : ui.route.name === "board" ? "chain" : ui.route.name;
  const foot = kind === "places";
  const nav = h("nav", { class: foot ? "places" : "tabs", "aria-label": t("tabs.label") });
  for (const [id, href] of TABS) {
    const label = placeLabel(id);
    const n = id === "threads" ? threadsNumeral(st) : 0;
    nav.append(h("a", { class: "tab", href, "aria-current": cur === id ? "page" : null },
      n ? t("tabs.count", { label, n }) : label));
  }
  // on a phone the sixth mark is the one More (the places beyond the five, and the settings)
  if (foot) nav.append(h("button", { class: "tab", type: "button", "aria-haspopup": "dialog",
    "aria-current": MORE_PLACES.some(([id]) => id === cur) ? "page" : null, onclick: openMenu }, t("app.more")));
  return nav;
}

// ------------------------------------------------------------------ calls a view may not make itself

let TOKEN = null;
async function pageToken() {
  if (TOKEN || store.source !== "server") return TOKEN;
  try { const r = await fetch("/token", { cache: "no-store" }); if (r.ok) TOKEN = (await r.json()).token || null; } catch { /* no server */ }
  return TOKEN;
}
async function post(url, body) {
  const tk = await pageToken();
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", ...(tk ? { "X-HUD-Token": tk } : {}) },
    body: JSON.stringify(body) });
  return { r, out: await r.json().catch(() => ({})) };
}

/** ctx.launchBody({task, from_card, confirmed}): the person's own yes to start a body, after the
    Bodies view's launch sheet has said the cost (bodies.js offerBody). Called with no `confirmed`,
    it opens that sheet instead: ctx.launchBody({card}) from the Deal. */
async function launchBody(req = {}) {
  if (req.confirmed !== true) {
    const id = req.card && (req.card.id || req.card);
    go(`#/bodies?${id ? "launch=" + encodeURIComponent(id) : "task=" + encodeURIComponent(req.task || "")}`);
    return { ok: false, opened: true };
  }
  if (store.source !== "server") return { ok: false, reason: t("bodies.launch_no_host") };
  try {
    const { r, out } = await post("/agent/body", { task: req.task, from_card: req.from_card || null, confirmed: true });
    return r.ok ? { ok: true, out } : { ok: false, reason: out.refused || "" };
  } catch { return { ok: false, reason: "" }; }
}

/** ctx.say(room, text, {parent, now}): the Talk's say. Posted to /say when the server carries
    the live store; otherwise kept on this device, marked "waiting to send", in the Talk's own
    queue (so the Talk shows it and sends it when it can). Nothing said is written to the record. */
async function say(room, text, extra = {}) {
  text = String(text || "").trim();
  if (!room || !text) return { ok: false };
  if (store.source === "server") {
    try {
      // a view calls ctx.say only from the person's own tap (the contract); the yes is part of the call
      const { r, out } = await post("/say", { room, text, parent: extra.parent || null, now: !!extra.now,
        ...(extra.part != null ? { part: extra.part } : {}), confirmed: true });
      if (r.ok) return { ok: true, out };
      // a refusal in words is the server's answer; only a missing route keeps the line here
      if (out.refused || r.status !== 404) return { ok: false, reason: out.refused || "" };
    } catch { /* not reachable: keep it here */ }
  }
  const key = "hud.c.queue." + room;
  let q = [];
  try { q = JSON.parse(localStorage.getItem(key) || "[]"); } catch { q = []; }
  const now = fmt.now();
  if (!q.some((x) => x.text === text && x.parent === extra.parent && Math.abs(now - new Date(x.ts)) < 30000)) {
    const rm = ((store.state || {}).rooms || {})[room] || {};
    q.push({ id: "mine-" + Math.random().toString(16).slice(2, 10), text, ts: now.toISOString(), part: rm.current_part || null, ...extra });
    try { localStorage.setItem(key, JSON.stringify(q)); } catch { /* this visit only */ }
  }
  return { ok: false, queued: true };
}

/** ctx.mail: the three mail calls a view may not make itself (DESIGN-MAIL; serve.py /mail/*).
    Each is called only from the person's own tap: read (marks a carried item read on this
    machine), line (the yes to a line proposed from prose), send (mails a written line). */
const mail = {
  async read(id) {
    if (store.source !== "server" || !id) return { ok: false };
    try { const { r, out } = await post("/mail/read", { id }); return { ok: r.ok, ...out }; } catch { return { ok: false }; }
  },
  async line(id) {
    if (store.source !== "server" || !id) return { ok: false };
    try { const { r, out } = await post("/mail/line", { id, confirmed: true }); return { ok: r.ok, ...out }; } catch { return { ok: false }; }
  },
  async send(lineId, to) {
    if (store.source !== "server" || !lineId) return { ok: false };
    try { const { r, out } = await post("/mail/send", { line_id: lineId, to, confirmed: true }); return { ok: r.ok, ...out }; }
    catch { return { ok: false }; }
  },
};

// ------------------------------------------------------------------ the written line's id on every act
// pending.done resolves with the pending act carrying `lineId` (and `line_id`): the id of the
// line the server wrote, taken from /act's answer when it names one, else asked of /act/<id>
// once the undo window has passed. Send uses it to name the line it mails.
const actAnswers = new Map();   // server pending id -> /act's success body
if (!window.__hudActTap) {
  window.__hudActTap = true;
  const f0 = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const res = await f0(input, init);
    try {
      const url = typeof input === "string" ? input : input.url;
      if (/\/act$/.test(new URL(url, location.href).pathname) && init && init.method === "POST" && res.ok) {
        res.clone().json().then((out) => { if (out && out.pending) actAnswers.set(out.pending, out); }).catch(() => {});
      }
    } catch { /* never in the way of the call */ }
    return res;
  };
}
function withLineId(p) {
  if (!p || !p.done || p.__lineIdWrapped) return p;
  p.__lineIdWrapped = true;
  p.done = p.done.then(async (r) => {
    if (!r || r.status !== "written" || !r.serverId) return r;
    let id = (actAnswers.get(r.serverId) || {}).line_id || null;
    if (!id) {
      try {
        const tk = await pageToken();
        const res = await fetch(`/act/${encodeURIComponent(r.serverId)}`, { cache: "no-store", headers: tk ? { "X-HUD-Token": tk } : {} });
        if (res.ok) { const out = await res.json().catch(() => ({})); id = out.line_id || (out.line && out.line.id) || null; }
      } catch { /* the id is not known yet */ }
    }
    actAnswers.delete(r.serverId);
    r.lineId = id; r.line_id = id;
    return r;
  });
  return p;
}

/** Is this card long enough to offer to a body? Your agent's minutes against LONG_CARD_MINUTES,
    and never when the Fewer dial is at "fewer" or below. */
function longCard(card) {
  if (!card) return false;
  const st = store.state || {};
  const dial = st.attention && (st.attention.dial || st.attention.fewer);
  if (dial && dial !== "as set" && dial !== "as_set" && dial !== 0) return false;
  const m = card.agent_minutes != null ? card.agent_minutes : card.minutes;
  return typeof m === "number" && m > LONG_CARD_MINUTES;
}

let asOfShown = null;
function topLineText(st) {
  const day = fmt.dayName(fmt.now());
  if (store.status === "loading" || store.loadingAgain) return `${day} · ${t("app.reading")}`;
  // one "as of": the newest line read; a stale or unread record is said once, above the card
  // read from the state at every draw; the served state folds her own acts, so it is as of her last one too
  let newest = read.holons(st).map((x) => x.as_of && x.as_of.ts).filter(Boolean)
    .sort((a, b) => Date.parse(a) - Date.parse(b)).pop();
  if (store.ownAt && (!newest || Date.parse(store.ownAt) > Date.parse(newest))) newest = store.ownAt;
  // an as-of only moves forward: never earlier than the last one shown (never 2:37, then 2:31)
  if (newest && asOfShown && Date.parse(asOfShown) > Date.parse(newest)) newest = asOfShown;
  else if (newest && !(ui.route && ui.route.name === "bodies")) asOfShown = newest;
  // on Bodies, one as-of only, the oldest of what the screen shows (the records, the bodies, the cost)
  if (ui.route && ui.route.name === "bodies") newest = [newest, ...bodiesAsOfs(st)].filter(Boolean).sort()[0];
  const d = newest && fmt.date(newest);
  if (!d) return day;
  return t("top.day_as_of", { day, time: fmt.sameDay(d, fmt.now()) ? fmt.time(newest) : fmt.dayName(d) });
}

function orderedHolons(st) {
  const home = homeId(st);
  const hs = [...read.holons(st)];
  hs.sort((a, b) => (a.id === home ? -1 : b.id === home ? 1 : String((b.as_of || {}).ts).localeCompare(String((a.as_of || {}).ts))));
  return hs;
}

function bodiesAsOfs(st) {
  const live = st.hud && st.hud.bodies_live;
  return [live && live.as_of, st.cost && st.cost.day && st.cost.day.as_of, st.usage && st.usage.as_of].filter((x) => typeof x === "string");
}
/** A record's as-of, no earlier than store.ownAt when it is the record of her last act (the
    Deal's settle keeps which, beside ownAt): the same source the top line reads. */
function ownRecordAsOf(x) {
  const ts = x && x.as_of && x.as_of.ts;
  let holon = store.ownHolon;
  if (holon === undefined) { try { holon = JSON.parse(sessionStorage.getItem("hud.own_holon")); } catch { holon = null; } }
  if (!x || !store.ownAt || holon !== x.id || isNaN(Date.parse(store.ownAt))) return ts || null;
  return !ts || Date.parse(store.ownAt) > Date.parse(ts) ? store.ownAt : ts;
}
function renderRibbon(st) {
  const nav = h("nav", { class: "ribbon", id: "ribbon", "aria-label": t("ribbon.label") });
  // behind the one as-of on Bodies: each of its times, said once
  if (ui.route && ui.route.name === "bodies") for (const x of bodiesAsOfs(st)) nav.append(h("p", { class: "dust figures" }, t("ribbon.bodies_asof", { time: fmt.asOf(x) })));
  nav.append(h("button", { class: "chip", "aria-pressed": String(!ui.filter), onclick: () => setFilter(null) }, t("ribbon.all")));
  for (const x of orderedHolons(st)) {
    const ts = ownRecordAsOf(x);   // the record she just settled a card in: never earlier than her tap
    const fr = fmt.freshness(ts);
    const sr = fr === "older" ? t("ribbon.fresh.older", { when: fmt.when(ts) || "" }) : t("ribbon.fresh." + fr);
    const chip = h("button", { class: "chip", "aria-pressed": String(ui.filter === x.id),
      onclick: () => setFilter(ui.filter === x.id ? null : x.id), title: sr },
      h("i", { class: `fresh ${fr}`, "aria-hidden": "true" }), x.name,
      fr === "older" ? h("span", { class: "dust" }, fmt.when(ts)) : null,
      h("span", { class: "sr-only" }, ", " + sr));
    nav.append(chip);
  }
  for (const s of read.unreadable(st)) {
    nav.append(h("button", { class: "chip", onclick: () => explainUnread(s) },
      h("i", { class: "fresh unread", "aria-hidden": "true" }), s.name, h("span", { class: "dust" }, t("ribbon.unread"))));
  }
  return nav;
}

function explainUnread(s) {
  const close = openSheet({
    title: s.name,
    body: h("p", null, t("ribbon.unread_explain", { holon: s.name, reason: typeof s.readable === "string" ? s.readable : "" })),
    actions: [h("button", { class: "pill", onclick: () => { close(); load(); } }, t("app.try_again"))],
  });
}

function setFilter(id) { ui.filter = id; renderTop(); updateAll(); }

// ------------------------------------------------------------------ mounting views

async function loadView(id) {
  if (BUILTIN[id]) return BUILTIN[id]();
  const path = PLUGINS[id];
  if (!path) return null;
  try {
    const r = await fetch(path, { method: "HEAD", cache: "no-store" });
    if (r.status === 404) return null;
  } catch { /* static or file: try the import anyway */ }
  const mod = await import(path);
  return mod.default;
}

async function mountInto(container, id, slot, density) {
  const sec = h("section", { class: `view view--${id}`, dataset: { view: id }, "aria-label": t("view." + id) });
  if (!["deal", "whole"].includes(id) && slot !== "full" && slot !== "sheet") sec.append(viewHead(id));
  const body = h("div", { class: "view-body" });
  sec.append(body);
  container.append(sec);
  const entry = { id, el: body, sec, slot, density, inst: null };
  ui.mounted.push(entry);
  try {
    const factory = await loadView(id);
    if (!factory) {
      if (id === "map") { entry.inst = wholeFallback(); entry.inst.mount(body, makeCtx(entry)); return entry; }
      if (slot !== "full") { sec.remove(); ui.mounted.splice(ui.mounted.indexOf(entry), 1); return null; }
      body.append(h("p", { class: "placeholder" }, t("app.view_coming"))); return entry;
    }
    entry.inst = typeof factory === "function" ? factory() : factory;
    entry.inst.mount(body, makeCtx(entry));
    sec.classList.toggle("loading", store.status === "loading");
  } catch (e) {
    console.error(`view ${id}:`, e);
    body.textContent = "";
    if (id === "map") { entry.inst = wholeFallback(); entry.inst.mount(body, makeCtx(entry)); return entry; }
    if (slot !== "full") { sec.remove(); ui.mounted.splice(ui.mounted.indexOf(entry), 1); return null; }
    body.append(h("p", { class: "placeholder" }, t("app.view_failed")));
  }
  return entry;
}

/** The whole, until the Map is there: the made field, the line, and the plain list of what she
    belongs to (the list twin, DESIGN §4.4). Never "being built". */
function wholeFallback() {
  let el;
  return {
    mount(container, ctx) { el = container; this.update(ctx); },
    update(ctx) {
      el.textContent = "";
      const st = ctx.state;
      el.append(h("div", { class: "whole-fallback" },
        h("p", { class: "voice deal-played" }, t("whole.title_line")),
        h("figure", { class: "still-frame is-wide", "aria-hidden": "true" }, h("img", { src: "art/h-cell-overlap-sq-a.jpg", alt: "" })),
        h("h2", { class: "caps" }, t("whole.list_heading")),
        h("ul", { class: "whole-list" }, orderedHolons(st).map((x) => h("li", null,
          h("span", null, x.name), h("span", { class: "dust" }, " · " + (t("whole.kind." + x.kind).startsWith("[") ? "" : t("whole.kind." + x.kind))),
          x.as_of && x.as_of.ts ? h("span", { class: "dust figures" }, " · " + fmt.asOf(x.as_of.ts)) : null)))));
    },
    unmount() { if (el) el.textContent = ""; },
  };
}

function viewHead(id) {
  const head = h("div", { class: "view-head" }, h("h2", { class: "caps" }, t("view." + id)));
  const btn = h("button", { class: "view-menu-btn", "aria-label": t("layout.view_menu", { view: t("view." + id) }),
    onclick: () => openArrange(id) }, "⋯");
  head.append(btn);
  // long-press the title: the same menu (DESIGN §3.4); the visible button does the same
  let timer = null;
  head.addEventListener("pointerdown", () => { timer = setTimeout(() => openArrange(id), 550); });
  for (const ev of ["pointerup", "pointerleave", "pointercancel"]) head.addEventListener(ev, () => clearTimeout(timer));
  return head;
}

function unmountAll() {
  for (const m of ui.mounted) { try { m.inst && m.inst.unmount && m.inst.unmount(); } catch (e) { console.error(e); } }
  ui.mounted = [];
  $.main.textContent = "";
}

async function remount() {
  unmountAll();
  document.documentElement.dataset.route = ui.route.name;
  // the Talk holds the conversation itself; the dock's pane joins every other place, once
  if (ui.booted && ui.route.name !== "talk") mountDock();
  const L = activeLayout();
  prefsCache = effectivePrefs(L);
  applyTheme(prefsCache);
  renderTop();
  const r = ui.route;
  if (store.needsPairing && !store.state) { $.main.append(renderPairing()); return; }
  if (store.status === "error" && !store.state) { $.main.append(renderError()); return; }
  if (r.name === "deal" || r.name === "card" || !ROUTE_VIEWS[r.name]) {
    if (L.name === "player" && matchMedia("(min-width: 1024px)").matches && L.main.includes("commitments")) {
      L.main = L.main.filter((v) => v !== "commitments"); L.aside = ["commitments", ...L.aside.filter((v) => v !== "commitments")];
    }
    const grid = h("div", { class: `layout${L.aside.length ? " has-aside" : ""}${L.left.length ? " has-left" : ""}`, dataset: { layout: L.name } });
    const cl = h("div", { class: "col-left", role: "complementary" });
    const cm = h("div", { class: "col-main" });
    const ca = h("aside", { class: "col-aside" });
    if (L.left.length) grid.append(cl);
    grid.append(cm);
    if (L.aside.length) grid.append(ca);
    $.main.append(grid);
    for (const id of L.left) await mountInto(cl, id, "left", L.densities[id]);
    for (const id of L.main) await mountInto(cm, id, "main", L.densities[id]);
    // the Player aside is for wide screens only; skip the work on a phone
    if (L.name !== "player" || matchMedia("(min-width: 1024px)").matches) for (const id of L.aside) await mountInto(ca, id, "aside", L.densities[id]);
  } else {
    await mountInto($.main, ROUTE_VIEWS[r.name], "full", "full");
  }
  if (r.name === "card" && r.arg) openCard(r.arg, true);
}

function updateAll() {
  if (ui.dock && ui.dock.inst && ui.dock.inst.update) { try { ui.dock.inst.update(makeCtx(ui.dock)); } catch (e) { console.error("dock:", e); } }
  for (const m of ui.mounted) {
    if (!m.inst || !m.inst.update) continue;
    try { m.inst.update(makeCtx(m)); } catch (e) { console.error(`view ${m.id}:`, e); }
    m.sec.classList.toggle("loading", store.status === "loading" || !!store.loadingAgain);
  }
}

// The phone door, before this phone has its own token: the one-time code from the computer.
function renderPairing() {
  const input = h("input", { class: "pair-code", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "6",
    "aria-label": t("dock.phone_code_label") });
  const said = h("p", { class: "dust", role: "status" });
  const go = async () => {
    said.textContent = "";
    const r = await claimPhone(input.value);
    if (!r.ok) { said.textContent = t("dock.phone_code_refused"); return; }
    await load(); await remount(); connect();
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  return h("div", { class: "loader pairing" },
    h("p", null, t("dock.phone_enter_code")), input,
    h("button", { class: "pill primary", onclick: go }, t("dock.phone_let_in")), said);
}

function renderError() {
  return h("div", { class: "loader" },
    h("div", { class: "still-point", "aria-hidden": "true" }, h("i")),
    h("p", null, t("app.state_failed")),
    h("button", { class: "pill", onclick: () => load() }, t("app.try_again")));
}

// ------------------------------------------------------------------ sheets

function openSheet({ title, body, actions = [], label, cls }) {
  closeSheet();
  const prevFocus = document.activeElement;
  const scrim = h("div", { class: "scrim", onclick: () => closeSheet() });
  const titleId = "sheet-title-" + Math.random().toString(16).slice(2, 8);
  const sheet = h("div", { class: `sheet${cls ? " " + cls : ""}`, role: "dialog", "aria-modal": "true", "aria-labelledby": titleId },
    h("div", { class: "sheet-head" }, h("h2", { id: titleId }, title || label || ""),
      h("button", { class: "link-btn", onclick: () => closeSheet() }, t("app.close"))),
    body || null,
    actions.length ? h("div", { class: "actions" }, actions) : null);
  document.body.append(scrim, sheet);
  animate(sheet, [{ opacity: 0, transform: `translateY(${cssVar("--rise-card")})` }, { opacity: 1, transform: "none" }],
    { duration: cssMs("--d-settle"), easing: cssVar("--e-settle") });
  const first = sheet.querySelector("button, a, input, textarea, [tabindex]");
  (first || sheet).focus();
  sheet.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    const f = [...sheet.querySelectorAll("button, a[href], input, textarea, select, [tabindex]:not([tabindex='-1'])")].filter((x) => !x.disabled);
    if (!f.length) return;
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  });
  ui.sheet = { scrim, sheet, prevFocus, mounted: [] };
  return closeSheet;
}
function closeSheet() {
  if (!ui.sheet) return;
  const { scrim, sheet, prevFocus, onClose, refind, isCard } = ui.sheet;
  ui.sheet = null;
  scrim.remove(); sheet.remove();
  // focus returns to what opened it; when a redraw replaced that element, to its successor
  const back = prevFocus && prevFocus.isConnected && prevFocus !== document.body ? prevFocus : refind ? refind() : null;
  if (back && back.focus) back.focus();
  if (onClose) onClose();
  if (isCard && ui.route.name === "card") {
    if (beforeCard != null) history.back();   // to the view it opened over, without a remount (onRoute)
    else location.hash = "#/deal";            // opened from a link: the Deal is the way home
  }
}

// ------------------------------------------------------------------ the full card (card-full.js)

let cardOpts = null;      // {id, from, hint}: what the opener said, for the route that follows
let beforeCard = null;    // the route the full card opened over, so closing it returns there unchanged
let cardSeq = 0;
const routeKey = (r) => (r ? `${r.name}|${r.arg || ""}|${location.search}` : "");

/** How to find the opener again after a redraw (a view may redraw on select, replacing the very
    button that was tapped): its card's open link, else a button like it, else one named by the
    card's title, else anything inside the card's face. */
function refinder(el, id) {
  const real = el && el !== document.body && el.nodeType === 1 ? el : null;
  const cls = real && real.className, text = real && real.textContent;
  const title = (read.card(store.state || {}, id) || {}).title;
  const buttons = () => [...document.querySelectorAll("#main button, #main a")];
  return () => document.querySelector(`[data-open-card="${CSS.escape(id)}"]`)
    || (real && buttons().find((b) => b.className === cls && b.textContent === text))
    || (title && buttons().find((b) => b.textContent.trim() === title))
    || document.querySelector(`#main [data-card="${CSS.escape(id)}"] button`) || null;
}

function openCard(id, fromRoute, opts = {}) {
  if (!fromRoute) {
    cardOpts = { id, ...opts };
    if (ui.route.name !== "card") { beforeCard = routeKey(ui.route); go(`#/card/${encodeURIComponent(id)}`); }
    else location.replace(`#/card/${encodeURIComponent(id)}`);   // card to card: closing still returns to the view beneath
    return;
  }
  ui.selected = id;
  // a card opened from inside another keeps the first opener, so focus returns to the view
  const prev = ui.sheet;
  const keep = prev ? prev.prevFocus : document.activeElement;
  const refind = prev ? prev.refind : refinder(keep, (keep && keep.dataset && keep.dataset.openCard) || id);
  if (prev) { ui.sheet = null; prev.scrim.remove(); prev.sheet.remove(); }
  const o = cardOpts && cardOpts.id === id ? cardOpts : {};
  cardOpts = null;
  const seq = ++cardSeq;
  import("./card-full.js").then(({ renderFullCard }) => {
    if (seq !== cardSeq || ui.route.name !== "card") return;
    const ctx = makeCtx({ slot: "sheet", density: "full" });
    const full = renderFullCard(ctx, id, { hint: o.hint || {}, story: store.server ? cardStory : null, acts: {
      claim: (c) => cardAct("claim", c), done: (c) => cardAct("done", c), ask: (c) => askOnCard(c), answered: () => closeSheet() } });
    openSheet({ title: full.title, body: full.el, cls: "sheet--card" });
    Object.assign(ui.sheet, { prevFocus: keep, refind, isCard: true });
    const head = ui.sheet.sheet.querySelector(".sheet-head h2");
    if (head) head.classList.add("sr-only");
    full.load();
    updateAll();
  }).catch((e) => console.error("card:", e));
}
function cardAct(type, c) {
  act(type, { card: c.id }, {}, c.holon, { confirmed: true, label: t("card.act_" + type, { title: c.title }), undo_ms: ctxPrefs().undo_ms });
  closeSheet();
}
function askOnCard(c) {
  const area = h("textarea", { class: "fixed-input", rows: "3", placeholder: t("card.ask_placeholder"), "aria-label": t("card.ask_placeholder") });
  const close = openSheet({ title: c.title, body: area, actions: [
    h("button", { class: "pill primary", onclick: () => {
      const text = area.value.trim();
      if (!text) { area.focus(); return; }
      act("say", { text }, { anchored_to: [c.id] }, c.holon, { confirmed: true, label: t("card.act_ask"), undo_ms: ctxPrefs().undo_ms });
      close();
    } }, t("card.ask_send"))] });
}

/** The publish sheet: the one route outward (DESIGN §4.10). */
function openPublish({ holon, what, lines = [], onPublish }) {
  const name = read.holonName(store.state || {}, holon);
  const close = openSheet({
    title: t("sheet.publish_title"),
    body: h("p", null, t("sheet.publish_will_see", { holon: name, what })),
    actions: [
      h("button", { class: "pill primary", onclick: async () => {
        const token = await publishToken();
        const p = act("publish", { lines, audience: "members", to: holon }, {}, homeId(store.state), { confirmed: true, sheet_token: token,
          label: t("sheet.publish"), undo_ms: ctxPrefs().undo_ms });
        close();
        if (onPublish) onPublish(p);
      } }, t("sheet.publish")),
      h("button", { class: "pill quiet", onclick: () => close() }, t("sheet.keep_here")),
    ],
  });
}

// ------------------------------------------------------------------ More: the places, the way back, Settings
// More holds the places by their own names,
// the way to the desktop app, and one word, Settings. Nothing else; fewer than twelve controls.

function openMenu() {
  const body = h("div");
  const curName = ui.route.name;
  // the Talk counts each opening of More in a sitting (DESIGN-TALK §6: three, and it offers another way)
  SS_set("talk.more", (SS_get("talk.more") || 0) + 1);
  const st0 = store.state || {};
  body.append(h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, t("places.more_title")),
    h("ul", { class: "menu-list", role: "menu" }, MORE_PLACES.map(([id, href]) => {
      const n = id === "threads" ? threadsNumeral(st0) : 0;
      return h("li", null, h("button", { role: "menuitem", "aria-current": curName === id ? "page" : null, onclick: () => { closeSheet(); go(href); } },
        n ? t("tabs.count", { label: placeLabel(id), n }) : placeLabel(id)));
    }))));
  // if this page breaks: the vendor's own app, one tap, behind More (never on the first screen)
  { const ev = activeLayout().event || {};
    body.append(h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, t("talk_place.desktop_title")),
      h("p", { class: "dust" }, t("talk_place.desktop_note")),
      h("ul", { class: "menu-list", role: "menu" }, h("li", null, h("button", { role: "menuitem", onclick: () => {
        closeSheet(); location.href = typeof ev.desktop_app === "string" && /^[a-z][a-z0-9+.-]*:\/\//i.test(ev.desktop_app) ? ev.desktop_app : DESKTOP_APP;
      } }, t("talk_place.desktop_app")))))); }
  body.append(h("ul", { class: "menu-list", role: "menu" }, h("li", null, h("button", { role: "menuitem", class: "menu-settings", onclick: () => { closeSheet(); openSettings(); } }, t("settings.title")))));
  openSheet({ title: t("top.menu"), body });
}

/** Settings: the ground, the letters, motion, time to undo, the keys (on a keyboard), what the
    screen leaves out and the study; the arranging of the other places one step further in. */
function openSettings() {
  const L = activeLayout();
  const body = h("div");
  const group = (label, items) => h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, label), h("ul", { class: "menu-list", role: "menu" }, items));
  const radio = (label, checked, fn) => h("li", null, h("button", { role: "menuitemradio", "aria-checked": String(checked), onclick: fn }, label));
  // at most ten controls at first sight; the rest fold under a plain heading
  // each, closed until a tap (the dock's own fold class, so the sheet reads as one list)
  const fold = (label, kids) => h("details", { class: "dock-settings-fold settings-fold" }, h("summary", { class: "link-btn" }, label), ...kids);
  body.append(fold(t("settings.fold_looks"), [
    group(t("settings.theme"), ["system", "night", "paper"].map((v) =>
      radio(t("settings.theme." + v), store.prefs.theme === v, () => { setPref("theme", v); closeSheet(); remount(); }))),
    group(t("settings.type"), ["regular", "large"].map((v) =>
      radio(t("settings.type." + v), (store.prefs.type || "regular") === v, () => { setPref("type", v); closeSheet(); remount(); }))),
    group(t("settings.motion"), ["system", "reduce"].map((v) =>
      radio(t("settings.motion." + v), (store.prefs.motion || "system") === v, () => { setPref("motion", v); closeSheet(); remount(); }))),
  ]));
  body.append(fold(t("settings.fold_behaves"), [
    group(t("settings.undo"), [5000, 15000].map((v) =>
      radio(t("settings.undo." + v / 1000), (store.prefs.undo_ms || 5000) === v, () => { setPref("undo_ms", v); closeSheet(); remount(); }))),
    h("div", { class: "menu-group" }, h("ul", { class: "menu-list", role: "menu" },
      h("li", null, h("button", { onclick: () => { closeSheet(); openArrangePlaces(L); } }, t("settings.arrange_more"))))),
  ]));
  const fine = !(window.matchMedia && matchMedia("(pointer: coarse)").matches);
  if (fine) body.append(fold(t("top.keys"), [h("div", { class: "menu-group" }, h("ul", { class: "menu-list", role: "menu" },
    h("li", null, h("button", { onclick: openKeys }, t("top.keys")))))]));
  // her choices, moved here from the sheet behind her name: how she asks, the voice's
  // finer choices, the phone; the counting of your judgments sits with the study, below
  const her = agentSettings(() => closeSheet());
  if (her.agent.length) body.append(h("div", { class: "menu-group settings-agent" }, h("span", { class: "eyebrow" }, her.name || t("settings.agent_plain")), ...her.agent));
  if (her.judgment.length) body.append(h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, t("dock.discern_title")), ...her.judgment));
  // the about lines: what the screen leaves out on purpose, said once, here and nowhere else
  body.append(h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, t("about.title")),
    h("p", { class: "dust" }, t("deal.privacy")), h("p", { class: "dust" }, t("about.absent")), h("p", { class: "dust" }, t("about.token")),
    h("p", { class: "dust" }, t("about.study_note")),
    h("ul", { class: "menu-list", role: "menu", "aria-label": t("about.study") }, ["on", "off"].map((v) =>
      radio(t("about.study") + " · " + t("about.study_" + v), (store.prefs.study || "on") === v, () => { setPref("study", v); closeSheet(); })))));
  // a closed fold keeps its controls out of the layout entirely (Chrome lays out a closed <details>'
  // content with a size of its own, and a class's display outlasts `hidden`), for the dock's folds here as well as the shell's
  for (const d of body.querySelectorAll("details")) {
    const shut = () => { for (const k of d.children) if (k.tagName !== "SUMMARY") k.style.display = d.open ? "" : "none"; };
    shut(); d.addEventListener("toggle", shut);
  }
  openSheet({ title: t("settings.title"), body });
}

/** The arranging of the other places (the Deal's layouts, by name, and the order of its views). */
function openArrangePlaces(L) {
  const body = h("div");
  const names = layoutNames();
  const group = (label, items) => h("div", { class: "menu-group" }, h("span", { class: "eyebrow" }, label), h("ul", { class: "menu-list", role: "menu" }, items));
  const radio = (label, checked, fn) => h("li", null, h("button", { role: "menuitemradio", "aria-checked": String(checked), onclick: fn }, label));
  // up to three layouts by name; a fourth turns the group into a list (§3.4)
  body.append(group(t("layout.menu_title"), names.map((n) => radio(t("layout." + n).startsWith("[") ? n : t("layout." + n), n === L.name, () => {
    const p = new URLSearchParams(location.search); p.set("layout", n);
    history.replaceState(null, "", `?${p.toString()}${location.hash}`); ui.layoutOverride = null; closeSheet(); onRoute();
  }))));
  // arrange this layout by hand: each change writes a `layout` event by the person's tap
  const arr = L.views.filter((v) => !LOCKED.has(v));
  body.append(group(t("layout.arrange"), arr.map((v) => h("li", null, h("button", { onclick: () => openArrange(v) }, t("view." + v))))));
  if (L.hidden.length) body.append(group(t("layout.hidden"), L.hidden.map((v) => h("li", null,
    h("button", { onclick: () => { closeSheet(); writeLayout({ views: L.views, hidden: L.hidden.filter((x) => x !== v) }, t("layout.show", { view: t("view." + v) })); } },
      t("layout.show", { view: t("view." + v) }))))));
  openSheet({ title: t("settings.arrange_title"), body });
}

function openArrange(id) {
  const L = activeLayout();
  if (LOCKED.has(id)) return;
  const views = [...L.main, ...L.aside, ...L.left];
  const i = views.indexOf(id);
  const move = (d) => {
    const next = [...views];
    const j = i + d;
    if (j < 0 || j >= next.length) return;
    [next[i], next[j]] = [next[j], next[i]];
    closeSheet();
    writeLayout({ views: next, hidden: L.hidden }, t("layout.notice_moved", { view: t("view." + id) }));
  };
  openSheet({
    title: t("layout.view_menu", { view: t("view." + id) }),
    body: h("ul", { class: "menu-list", role: "menu" },
      h("li", null, h("button", { onclick: () => move(-1), disabled: i <= 0 }, t("layout.move_up"))),
      h("li", null, h("button", { onclick: () => move(1), disabled: i < 0 || i >= views.length - 1 }, t("layout.move_down"))),
      h("li", null, h("button", { onclick: () => { closeSheet(); writeLayout({ views: views.filter((v) => v !== id), hidden: [...L.hidden, id] }, t("layout.notice_hidden", { view: t("view." + id) })); } }, t("layout.hide")))),
  });
}

function openKeys() {
  const rows = [["J", t("keys.next")], ["K", t("keys.previous")], ["1–3", t("keys.choose")], ["Enter", t("keys.confirm")], ["T", t("keys.dock")],
    ["U", t("keys.undo")], ["Esc", t("keys.close")], ["?", t("keys.help")]];
  openSheet({ title: t("keys.title"), body: h("div", { class: "keys" }, rows.flatMap(([k, v]) => [h("kbd", null, k), h("span", null, v)])) });
}

// ------------------------------------------------------------------ toasts: every act's Undo

const toasts = new Map();
function onAct(p) {
  // what a screen reader hears is said in full; what the eye sees is only "Undo"
  if (p.status === "holding" && p.label) $.live.textContent = p.quiet ? p.label : `${p.label} ${t("deal.written_soon")}`;
  // once the act is no longer held, the ear hears no Undo that the eye cannot see: the announcement
  // falls back to the act's first sentence
  if (p.status !== "holding" && p.label) {
    const first = p.label.split(". ")[0];
    if ($.live.textContent.startsWith(first) && /Undo/.test($.live.textContent)) $.live.textContent = first.endsWith(".") ? first : first + ".";
  }
  if (p.quiet) return;
  if (p.status === "holding") {
    for (const [id, old] of toasts) { old.remove(); toasts.delete(id); }   // never stacked
    const el = h("div", { class: "toast" }, h("button", { class: "link-btn", onclick: () => p.undo() }, "↺ " + t("deal.undo")));
    toasts.set(p.id, el);
    $.toasts.append(el);
    animate(el, [{ opacity: 0 }, { opacity: 1 }], { duration: cssMs("--d-settle"), easing: cssVar("--e-settle") });
    return;
  }
  const el = toasts.get(p.id);
  toasts.delete(p.id);
  if (el) el.remove();
  // only what she must know stays: a refusal, or that it waits on this device
  if (p.status === "refused" || p.status === "kept-here") {
    const note = h("div", { class: "toast" }, h("span", { class: "msg dust" }, p.status === "refused" ? t("deal.refused") : t("deal.held_local")));
    for (const [id, old] of toasts) { old.remove(); toasts.delete(id); }
    $.toasts.append(note);
    setTimeout(() => note.remove(), cssMs("--d-notice"));
  }
}

// The agent's layout change: one quiet line for eight seconds with Undo (DESIGN §3.4).
function seenLayouts() { try { return new Set(JSON.parse(localStorage.getItem("hud.seen_layouts") || "[]")); } catch { return new Set(); } }
function markSeen(ids) { try { localStorage.setItem("hud.seen_layouts", JSON.stringify([...ids])); } catch { /* ignore */ } }
function noticeAgentLayouts() {
  const st = store.state || {};
  const seen = seenLayouts();
  for (const l of read.layouts(st)) {
    if (!l.id || seen.has(l.id) || !String(l.actor || "").startsWith("agent:")) continue;
    seen.add(l.id);
    const text = l.views && l.views[0] === "commitments" ? t("layout.notice_commitments_top") : t("layout.notice_generic");
    const el = h("div", { class: "toast", role: "status" }, h("span", { class: "msg" }, text),
      h("button", { class: "link-btn", onclick: () => {
        act("supersede", {}, { supersedes: [l.id] }, homeId(st), { confirmed: true, label: t("layout.undo") });
        el.remove();
      } }, "↺ " + t("layout.undo")));
    $.toasts.append(el);
    setTimeout(() => el.remove(), cssMs("--d-notice"));
  }
  markSeen(seen);
}

// ------------------------------------------------------------------ keys (§7)

function onKey(e) {
  const tag = (e.target && e.target.tagName) || "";
  const typing = /INPUT|TEXTAREA|SELECT/.test(tag) || (e.target && e.target.isContentEditable);
  if (e.key === "Escape" && ui.sheet) { e.preventDefault(); closeSheet(); return; }
  if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === "?") { e.preventDefault(); openKeys(); return; }
  if ((e.key === "u" || e.key === "U") && latestPending()) { e.preventDefault(); latestPending().undo(); return; }
  if (ui.sheet) return;
  if (ui.dock && ui.dock.inst && ui.dock.inst.key) { try { if (ui.dock.inst.key(e, makeCtx(ui.dock))) { e.preventDefault(); return; } } catch (err) { console.error(err); } }
  for (const m of ui.mounted) {
    if (m.inst && m.inst.key) { try { if (m.inst.key(e, makeCtx(m))) { e.preventDefault(); return; } } catch (err) { console.error(err); } }
  }
}

// ------------------------------------------------------------------ boot

function sceneTheme() {
  const th = ctxPrefs().theme;
  if (th === "night" || th === "paper") return th;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "night" : "paper";
}
function showLoader() {
  $.main.textContent = "";
  // the first scene is a made frame: the engraved Mark on its ground;
  // the light lives only inside the frame; the code only fades it
  // the Mark frame, scaled down in code; on a phone the Name alone, because the
  // action line cannot be read at that size; the frame's edges fade into the graded ground
  const paper = sceneTheme() === "paper";
  const src = paper ? "art/m-loader-paper-a.jpg" : "art/m-loader-night-a.jpg";
  const nameOnly = !matchMedia("(min-width: 600px)").matches;
  const img = h("img", { src, alt: "", decoding: "async" });
  $.scene = h("div", { class: `scene-loader is-${paper ? "paper" : "night"}`, role: "status", "aria-label": t("app.reading") },
    h("div", { class: `scene-mark${nameOnly ? " is-name" : ""}` }, img),
    h("p", { class: "sr-only" }, t("app.reading")));
  document.body.append($.scene);
  const frames = Array.from({ length: 13 }, (_, i) => ({ opacity: Math.sin((i / 12) * Math.PI / 2) }));
  animate($.scene, frames, { duration: cssMs("--d-bloom"), easing: "linear", fill: "both" });
}
async function endLoader() {
  const sc = $.scene;
  if (!sc) return;
  $.scene = null;
  const frames = Array.from({ length: 13 }, (_, i) => ({ opacity: Math.cos((i / 12) * Math.PI / 2) }));
  const a = animate(sc, frames, { duration: cssMs("--d-scene-fade"), easing: "linear", fill: "both" });
  if (a) await a.finished.catch(() => {});
  sc.remove();
}

// ------------------------------------------------------------------ the surface studies itself (DESIGN-THE-BAR §4)
// One `study` line, the person's own, written through /act to the home record on this machine (a
// home-only type: it never leaves the holon): a view's first act of the session (first_act_ms,
// from the view's opening), the first undo in a view (reversals), the first switch to a view
// within five seconds of the last (attention_switches). Never more than one line per view per
// measure per session; "Let the ICE study itself on this machine" in the about sheet turns it off.
const STUDY_VIEWS = new Set(["talk", "deal", "threads", "map", "chain", "room", "bodies", "ledger", "turn", "record"]);
const studySession = SS_get("study.session") || (() => { const x = Math.random().toString(16).slice(2, 10); SS_set("study.session", x); return x; })();
const studied = new Set(SS_get("study.done") || []);
const studyClock = { view: null, opened: 0, lastSwitch: 0, undos: SS_get("study.undos") || {} };
function SS_get(k) { try { return JSON.parse(sessionStorage.getItem("hud." + k)); } catch { return null; } }
function SS_set(k, v) { try { sessionStorage.setItem("hud." + k, JSON.stringify(v)); } catch { /* private window: the session is this page */ } }
function studyView() { const n = ui.route && ui.route.name === "card" ? "deal" : ui.route && ui.route.name; return STUDY_VIEWS.has(n) ? n : null; }
// first_act_ms is one line. reversals and attention_switches are counts for the session (report
// 03): the first event writes a line; as the count grows a new line supersedes the last one, at
// most once a minute (a later count waits for the minute, and the newest count is what is written),
// so there is one live line per view per measure and the Turn reads the newest.
const STUDY_COUNTS = new Set(["reversals", "attention_switches"]);
const studyLive = SS_get("study.live") || {};   // key -> {value, lineId, at}
const studyTimers = {};
function studyWrite(view, measure, value) {
  const key = `${view}.${measure}`, prev = studyLive[key];
  const links = prev && prev.lineId ? { supersedes: [prev.lineId] } : {};
  studyLive[key] = { value, lineId: prev ? prev.lineId : null, at: Date.now() };
  SS_set("study.live", studyLive);
  const p = act("study", { view, measure, value: Math.round(value), as_of: new Date().toISOString(), session: studySession }, links,
    homeId(store.state || {}), { confirmed: true, quiet: true, label: "" });
  if (p && p.done) p.done.then((q) => { const id = q && (q.lineId || q.line_id); if (id) { studyLive[key].lineId = id; SS_set("study.live", studyLive); } });
}
function study(view, measure, value) {
  if (!view || store.prefs.study === "off") return;
  const key = `${view}.${measure}`;
  if (!STUDY_COUNTS.has(measure)) {
    if (studied.has(key)) return;
    studied.add(key); SS_set("study.done", [...studied]);
    studyWrite(view, measure, value);
    return;
  }
  const prev = studyLive[key];
  if (prev && prev.value === value) return;
  const wait = prev ? prev.at + 60000 - Date.now() : 0;
  if (wait <= 0) { studyWrite(view, measure, value); return; }
  clearTimeout(studyTimers[key]);
  studyTimers[key] = setTimeout(() => { if (store.prefs.study !== "off") studyWrite(view, measure, value); }, wait);
}
function studyOnAct(p) {
  if (!p || p.type === "study" || p.type === "layout") return;
  if (p.status === "undone") SS_set("talk.undos", (SS_get("talk.undos") || 0) + 1);   // the Talk's second sign of difficulty
  const v = studyView();
  if (p.status === "holding" && v === studyClock.view) study(v, "first_act_ms", performance.now() - studyClock.opened);
  if (p.status === "undone" && v) { studyClock.undos[v] = (studyClock.undos[v] || 0) + 1; SS_set("study.undos", studyClock.undos); study(v, "reversals", studyClock.undos[v]); }
}
const studySwitches = SS_get("study.switches") || {};
function countSwitch(v) {
  studySwitches[v] = (studySwitches[v] || 0) + 1; SS_set("study.switches", studySwitches);
  study(v, "attention_switches", studySwitches[v]);
}

function onRoute() {
  const prev = ui.route;
  ui.route = parseRoute();
  const sv = studyView(), nowMs = performance.now();
  if (sv && sv !== studyClock.view) {
    if (studyClock.view && nowMs - studyClock.lastSwitch < 5000) countSwitch(sv);
    studyClock.view = sv; studyClock.opened = nowMs; studyClock.lastSwitch = nowMs;
  }
  const h0 = ui.route.params.get("holon");
  if (h0) ui.filter = h0;
  if (ui.route.name === "card" && prev && ui.booted && ui.mounted.length) {
    openCard(ui.route.arg, true);   // over the current view, or in place of the card before it
    return;
  }
  if (prev && prev.name === "card" && ui.route.name !== "card") {
    // the browser's Back closes the full card; any other sheet (the Ask sheet) stays
    if (ui.sheet && ui.sheet.isCard) { const s = ui.sheet; ui.sheet = null; s.scrim.remove(); s.sheet.remove(); }
    const same = beforeCard != null && beforeCard === routeKey(ui.route);
    beforeCard = null;
    if (same && ui.booted && ui.mounted.length) return;   // back where it opened: nothing to redraw
  }
  if (ui.booted) remount();
}

let lastLayoutKey = null;
/** One key for "the layout changed", read at load and on every state the same way, so the first
    state of a session never remounts every view (the performance pass, 2026-10-25: the load built
    it without type and theme, and the first /stream event rebuilt the whole page). */
const layoutKey = (L) => JSON.stringify(L.views) + L.name + L.type + L.theme;
async function boot() {
  await loadStrings();
  buildFrame();
  ui.route = parseRoute();
  studyClock.view = studyView(); studyClock.opened = studyClock.lastSwitch = performance.now();   // the first view's opening
  prefsCache = effectivePrefs({});
  applyTheme(prefsCache);
  document.documentElement.dataset.route = ui.route.name;
  renderTop();
  // the Talk is useful before anything plays: no loader scene, no hold (DESIGN-TALK §2, instant arrival)
  const instant = ui.route.name === "talk";
  if (!instant) showLoader();
  const started = performance.now();
  const pair = new URLSearchParams(location.search).get("pair");
  if (pair) {   // the phone opened the address the computer showed, code and all
    await claimPhone(pair);
    const q = new URLSearchParams(location.search); q.delete("pair");
    history.replaceState(null, "", `${location.pathname}${q.toString() ? "?" + q : ""}${location.hash}`);
  }
  await load();
  // the loader is the first scene: the Mark is held long enough to be seen, then gives way
  const wait = instant ? 0 : Math.max(0, (ctxPrefs().reducedMotion ? cssMs("--d-settle") : cssMs("--d-scene-hold")) - (performance.now() - started));
  if (wait) await new Promise((r) => setTimeout(r, wait));
  ui.booted = true;
  lastLayoutKey = layoutKey(activeLayout());
  { const ev = activeLayout().event; ui.dockOpen = !!(ev && ev.dock === "open"); applyDock(); }
  if (!instant) await endLoader();
  await remount();
  if (ui.route.name !== "talk") mountDock();
  noticeAgentLayouts();
  connect();
  subscribe(() => {
    const L = activeLayout();
    if (ui.layoutOverride && read.layouts(store.state || {}).some((l) => l.actor === (store.state || {}).actor && JSON.stringify(l.views) === JSON.stringify(ui.layoutOverride.views))) ui.layoutOverride = null;
    const key = layoutKey(L);
    if (key !== lastLayoutKey) { lastLayoutKey = key; remount(); }
    else { renderTop(); updateAll(); }
    noticeAgentLayouts();
  });
  onPending(onAct);
  onPending(studyOnAct);
  addEventListener("hashchange", onRoute);
  addEventListener("keydown", onKey);
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => applyTheme(ctxPrefs()));
  matchMedia("(min-width: 1024px)").addEventListener("change", () => remount());
}

// a probe for the headless proofs only (?probe=1): the context as a view would receive it
if (new URLSearchParams(location.search).get("probe") === "1") window.__hudProbe = { makeCtx };

boot();
