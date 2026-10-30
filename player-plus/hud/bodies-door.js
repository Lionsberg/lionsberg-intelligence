// bodies-door.js: the Bodies view's own door (bodies.html).
//
// A small host that gives bodies.js the context the shell gives every view (the plug-in contract
// in shell.js's header), from the same state.js, so the view moves into index.html unchanged when
// `bodies: "./bodies.js"` is added to PLUGINS and `bodies: "bodies"` to ROUTE_VIEWS.
// Until then this door is how #/bodies is reached. It carries the one
// call a view may not make itself: ctx.launchBody, the person's own yes to start a body, sent to
// the agent host's POST /agent/body with confirmed: true and the page's token.

import { store, load, connect, subscribe, t, fmt, read, act, loadStrings, FLAGS } from "./state.js";
import { h, cardModel, renderCard } from "./card.js";
import createBodies from "./bodies.js";

const params = new URLSearchParams(location.search);
let inst = null, mounted = false, sheet = null;

function parseRoute() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, q] = raw.split("?");
  const p = new URLSearchParams(location.search);
  if (q) for (const [k, v] of new URLSearchParams(q)) p.set(k, v);
  const [name, ...rest] = (path || "bodies").split("/");
  return { name: name || "bodies", arg: rest.length ? decodeURIComponent(rest.join("/")) : null, params: p };
}

function prefs() {
  const p = store.prefs;
  const px = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const large = p.type === "large" || px >= 16 * 1.3;
  const reducedMotion = p.motion === "reduce" || matchMedia("(prefers-reduced-motion: reduce)").matches;
  return { ...p, type: large ? "large" : "regular", large, reducedMotion, undo_ms: p.undo_ms || 5000 };
}
function applyTheme(pr) {
  const root = document.documentElement;
  if (pr.theme === "night" || pr.theme === "paper") root.dataset.theme = pr.theme; else delete root.dataset.theme;
  if (pr.large) root.dataset.type = "large"; else delete root.dataset.type;
  if (store.prefs.motion === "reduce") root.dataset.motion = "reduce"; else delete root.dataset.motion;
}
function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function cssMs(n) { const v = cssVar(n); return v.endsWith("ms") ? parseFloat(v) : parseFloat(v) * 1000 || 0; }

function animate(el, kf, opt) {
  if (!el || !el.animate || prefs().reducedMotion) return null;
  try { return el.animate(kf, opt); } catch { return null; }
}

function closeSheet() {
  if (!sheet) return;
  const s = sheet; sheet = null;
  s.scrim.remove(); s.el.remove();
  if (s.prev && s.prev.focus) s.prev.focus();
}
function openSheet({ title, body, actions = [] }) {
  closeSheet();
  const prev = document.activeElement;
  const scrim = h("div", { class: "scrim", onclick: closeSheet });
  const id = "sheet-title-" + Math.random().toString(16).slice(2, 8);
  const el = h("div", { class: "sheet", role: "dialog", "aria-modal": "true", "aria-labelledby": id },
    h("div", { class: "sheet-head" }, h("h2", { id }, title || ""), h("button", { class: "link-btn", onclick: closeSheet }, t("app.close"))),
    body || null, actions.length ? h("div", { class: "actions" }, actions) : null);
  document.body.append(scrim, el);
  animate(el, [{ opacity: 0, transform: `translateY(${cssVar("--rise-card")})` }, { opacity: 1, transform: "none" }],
    { duration: cssMs("--d-settle"), easing: cssVar("--e-settle") });
  (el.querySelector("button, a, [tabindex]") || el).focus();
  el.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
  sheet = { scrim, el, prev };
  return closeSheet;
}

let TOKEN = null;
async function launchBody(req) {
  if (store.source !== "server") return { ok: false, reason: t("bodies.launch_no_host") };
  try {
    if (!TOKEN) { const r = await fetch("/token", { cache: "no-store" }); if (r.ok) TOKEN = (await r.json()).token || null; }
    const r = await fetch("/agent/body", { method: "POST", headers: { "Content-Type": "application/json", ...(TOKEN ? { "X-HUD-Token": TOKEN } : {}) },
      body: JSON.stringify({ task: req.task, from_card: req.from_card, confirmed: true }) });
    const out = await r.json().catch(() => ({}));
    return r.ok ? { ok: true, out } : { ok: false, reason: out.refused || "" };
  } catch { return { ok: false, reason: "" }; }
}

function home() {
  const st = store.state || {};
  const hs = read.holons(st);
  const x = hs.find((y) => y.keeper === st.actor && y.kind === "person") || hs[0];
  return x ? x.id : null;
}

function ctx() {
  const pr = prefs();
  return Object.freeze({
    state: store.state || {}, filter: null, layout: { name: "player" }, slot: "full", density: "full",
    route: parseRoute(), prefs: pr, loading: store.status === "loading" || !!store.loadingAgain, offline: !!store.offline,
    selected: null, t, fmt, read, flags: FLAGS,
    act: (type, body, links, holon, opts = {}) => act(type, body, links, holon, { undo_ms: pr.undo_ms, ...opts }),
    select() {}, go: (hash) => { location.hash = hash; }, openCard() {}, openSheet, openPublish() {},
    animate, card: { h, cardModel, renderCard }, home: home(), launchBody,
  });
}

function frame() {
  const app = document.getElementById("app");
  app.textContent = "";
  const top = h("header", { class: "top", role: "banner" },
    h("div", { class: "top-line" },
      h("a", { class: "pill quiet back", href: "index.html" + location.search + "#/deal" }, "← " + t("deal.back_to_deal")),
      h("span", { class: "day figures" }, fmt.dayName(fmt.now()))));
  const main = h("main", { class: "views", id: "main" });
  const sec = h("section", { class: "view view--bodies", "aria-label": t("view.bodies") });
  const body = h("div", { class: "view-body" });
  sec.append(body); main.append(sec);
  app.append(top, main);
  return body;
}

async function boot() {
  await loadStrings();
  document.title = t("bodies.page_title");
  applyTheme(prefs());
  await load();
  const body = frame();
  inst = createBodies();
  inst.mount(body, ctx());
  mounted = true;
  subscribe(() => { applyTheme(prefs()); if (mounted) inst.update(ctx()); });
  addEventListener("hashchange", () => inst.update(ctx()));
  connect();
}
boot().catch((e) => { console.error(e); const app = document.getElementById("app"); if (app) app.textContent = t("app.state_failed"); });
