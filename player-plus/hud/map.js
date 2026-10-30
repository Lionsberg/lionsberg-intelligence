// map.js: the Map, the toroidal field made visible (DESIGN §4.4, §2.3;
// hud/art/; the canon proposal "No Center But ØNE"): one picture.
//
// One perspective. The ØNE is the vanishing point of the picture: every field stands on its own
// ray from it, nearer fields lower, larger and brighter, farther fields higher, smaller and
// fainter. A field's axis is its ray; every axis reaches the same still point, where nothing is
// drawn. No field stands on another's ray, so no axis crosses another field and no two overlap.
//
// Each field is a made frame (the person field, the unit), placed, scaled, leaned and
// turned by code; a cell is several person fields inside one membrane. Nothing here draws light.
// Sightings are engraved seals on the membranes; tapping a field or a seal opens the field's
// sheet beside it, inside the scene. Nothing is a list under the picture: the list twin is kept
// for the screen reader (hidden) and for paper.
//
//   #/map            the whole
//   #/map/<holon>    one field's Board, in place (the sheet's "Open its board")

import { h } from "./card.js";
import { ensureCss, ms, css, homeId, asOfWords, DONE, unit } from "./views-b.js";
import createBoard from "./board.js";

// The unit frame and where its open hole sits, as fractions of the square (measured on the
// share copy: the ring's half-width and half-height, and the top of the lines that gather
// above the hole, where the drawn axis takes over from the frame's own).
const UNIT = { src: "art/l-person-flow-a.jpg", hole: [0.5, 0.48], rx: 0.38, ry: 0.2, top: 0.25 };
const MEMBERS = { person: [1, 1], pair: [2, 2], quest: [2, 4], room: [3, 6], cell: [3, 7], body: [7, 11] };
// How large each kind stands at the same distance (a body is great even when far).
// A field's size is its nearness and its stake (what waits there, computed), never its kind.
const STAKE_SCALE = (n) => 0.78 + 0.13 * Math.min(4, n);

// The composition: where each depth may stand, as fractions of the stage. Rays from the ØNE to
// these points are far enough apart that no field stands on another's ray.
const SLOTS = {
  desk: {
    one: 0.085,
    near: [[0.5, 0.715]],
    middle: [[0.19, 0.555], [0.8, 0.54], [0.1, 0.33], [0.91, 0.36], [0.33, 0.36], [0.67, 0.35]],
    far: [[0.8, 0.21], [0.2, 0.2], [0.63, 0.17], [0.37, 0.17]],
  },
  phone: {
    // on the phone y is a fraction of the picture's own span, from the still point (0) to the foot (1)
    near: [[0.5, 0.79]],
    middle: [[0.23, 0.31], [0.77, 0.29], [0.14, 0.15], [0.86, 0.14]],
    far: [[0.8, 0.06], [0.2, 0.05], [0.64, 0.03], [0.36, 0.03]],
  },
};

let lastFocus = null;     // the field the sheet last showed, kept across a trip to its Board

// ------------------------------------------------------------------ the frames' own masks
// A made frame is cut from its night by its own light: once, at load, its luminance becomes an
// alpha mask (the ground falls away; the engraved lines stay). This grades the still; it draws
// nothing. Until it is ready, the luminance mask in CSS stands in.
// The mask is made once per image for the life of the page (MASKS, below), and off the main
// thread where the browser allows it (a worker with an OffscreenCanvas), so the first visit to the
// Map never stalls the hand (the performance pass, 2026-10-25: 171 ms of pixel work at 4x).
const MASKS = new Map();
const MASK_WORKER = `
  self.onmessage = async (e) => {
    try {
      const bmp = await createImageBitmap(await (await fetch(e.data.src)).blob());
      const c = new OffscreenCanvas(bmp.width, bmp.height), g = c.getContext("2d", { willReadFrequently: true });
      g.drawImage(bmp, 0, 0);
      const d = g.getImageData(0, 0, bmp.width, bmp.height), px = d.data, lo = 0.13, hi = 0.42;
      for (let i = 0; i < px.length; i += 4) {
        const lum = (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
        let a = (lum - lo) / (hi - lo);
        a = a <= 0 ? 0 : a >= 1 ? 1 : a * a * (3 - 2 * a);
        px[i] = px[i + 1] = px[i + 2] = 0; px[i + 3] = Math.round(a * 255);
      }
      g.putImageData(d, 0, 0);
      self.postMessage({ blob: await c.convertToBlob({ type: "image/png" }) });
    } catch (err) { self.postMessage({ blob: null }); }
  };`;
function maskInWorker(src) {
  if (typeof Worker === "undefined" || typeof OffscreenCanvas === "undefined" || typeof createImageBitmap === "undefined") return null;
  return new Promise((resolve) => {
    let w = null, url = null;
    const end = (v) => { try { if (w) w.terminate(); if (url) URL.revokeObjectURL(url); } catch { /* gone */ } resolve(v); };
    try {
      url = URL.createObjectURL(new Blob([MASK_WORKER], { type: "text/javascript" }));
      w = new Worker(url);
      w.onmessage = (e) => end(e.data && e.data.blob ? URL.createObjectURL(e.data.blob) : undefined);
      w.onerror = () => end(undefined);
      w.postMessage({ src: new URL(src, location.href).href });
    } catch { end(undefined); }
  });
}
function prepareMask(src) {
  if (MASKS.has(src)) return MASKS.get(src) instanceof Promise ? MASKS.get(src) : Promise.resolve(MASKS.get(src));
  const off = maskInWorker(src);
  const p = (off || Promise.resolve(undefined)).then((u) => (u !== undefined ? (MASKS.set(src, u), u) : maskOnPage(src)));
  MASKS.set(src, p);
  return p;
}
/** The same mask made on the page, where no worker can make it. */
function maskOnPage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      try {
        const w = img.naturalWidth, h0 = img.naturalHeight;
        const c = document.createElement("canvas");
        c.width = w; c.height = h0;
        const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(img, 0, 0);
        const d = g.getImageData(0, 0, w, h0), px = d.data;
        const lo = 0.13, hi = 0.42;
        for (let i = 0; i < px.length; i += 4) {
          const lum = (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
          let a = (lum - lo) / (hi - lo);
          a = a <= 0 ? 0 : a >= 1 ? 1 : a * a * (3 - 2 * a);
          px[i] = px[i + 1] = px[i + 2] = 0; px[i + 3] = Math.round(a * 255);
        }
        g.putImageData(d, 0, 0);
        c.toBlob((b) => { const u = b ? URL.createObjectURL(b) : null; MASKS.set(src, u); resolve(u); }, "image/png");
      } catch { MASKS.set(src, null); resolve(null); }
    };
    img.onerror = () => { MASKS.set(src, null); resolve(null); };
    img.src = src;
  });
}
function maskStyle(src) {
  const u = MASKS.get(src);
  return typeof u === "string" ? `mask-image:url("${u}");-webkit-mask-image:url("${u}");mask-mode:alpha;` : `mask-image:url("${src}");-webkit-mask-image:url("${src}");mask-mode:luminance;`;
}

// ------------------------------------------------------------------ reading the state

function fields(ctx) {
  const st = ctx.state, home = homeId(st);
  const hs = ctx.read.holons(st);
  const near = hs.filter((x) => x.id === home);
  const far = hs.filter((x) => x.id !== home && x.kind === "body");
  const middle = hs.filter((x) => x.id !== home && x.kind !== "body");
  middle.sort((a, b) => String((b.as_of || {}).ts).localeCompare(String((a.as_of || {}).ts)));
  return { near, middle, far, unread: ctx.read.unreadable(st) };
}

function kindWord(ctx, x) {
  if (x.id === homeId(ctx.state)) return ctx.t("map.kind.you");
  const k = ctx.t("map.kind." + x.kind);
  return k.startsWith("[") ? ctx.t("map.kind.cell") : k;
}

/** Whole days since the field was last heard from (0 today), or null when not computed. */
function daysQuiet(ctx, x) {
  const d = ctx.fmt.date && x.as_of && x.as_of.ts ? ctx.fmt.date(x.as_of.ts) : null;
  if (!d) return null;
  return Math.max(0, ctx.fmt.daysBetween(d, ctx.fmt.now()));
}

/** The turning: one revolution per (1800 / lines settled this week) seconds, held between 60 and
    600 (DESIGN §4.4); a field not heard from for days turns at half its pace. Null when the state
    does not say how busy the week was; 0 when nothing was settled (still). */
function turnSeconds(ctx, x) {
  const n = x.activity_7d;
  if (n == null || isNaN(n)) return null;
  if (n <= 0) return 0;
  const q = daysQuiet(ctx, x);
  return Math.max(60, Math.min(600, 1800 / n)) * (q != null && q > 1 ? 2 : 1);
}
function turnWords(ctx, x) {
  const s = turnSeconds(ctx, x);
  if (s == null) return ctx.t("map.turn_unknown");
  if (s === 0) return ctx.t("map.quiet", { when: ctx.fmt.when(x.as_of && x.as_of.ts) || "" });
  return x.activity_7d === 1 ? ctx.t("map.turn_one") : ctx.t("map.turn_lines", { n: ctx.fmt.number(x.activity_7d, true) });
}
/** A field heard from today is at full strength; yesterday a step down; older, two. */
function freshStep(ctx, x) {
  const q = daysQuiet(ctx, x);
  return q == null ? 2 : q === 0 ? 0 : q === 1 ? 1 : 2;
}
function freshWord(ctx, x) {
  if (x.unread) return ctx.t("ribbon.unread");
  const ts = x.as_of && x.as_of.ts;
  return ctx.fmt.freshness(ts) === "older" ? (ctx.fmt.when(ts) || ctx.t("app.not_computed")) : ctx.t("map.current");
}

function waitingOnYou(ctx, id) {
  return ((ctx.state.owed && ctx.state.owed.entries) || []).filter((e) => e.holon === id && e.holder === ctx.state.actor && e.status !== "done");
}
function onChain(ctx, id) {
  return (ctx.state.cards || []).filter((c) => c.holon === id && c.critical && !DONE.has(c.state));
}
/** Milestones that sit on a field's membrane (what it publishes). */
function milestones(ctx, id) {
  return (ctx.state.cards || []).filter((c) => c.holon === id && c.kind === "milestone");
}

/** Every sighting, flattened from STATE's per-holon {as_of, new, held, elevated, folded}; each row
    keeps its bucket as its status. Folded rows live on in the one they fold into, so they are never
    drawn. A v1 list (older fixtures) reads as rows whose status is not computed yet. */
function sightings(ctx) {
  const s = ctx.state.sightings;
  if (Array.isArray(s)) return s.filter((x) => x && x.holon);
  if (!s || typeof s !== "object") return [];
  const out = [];
  for (const [holon, b] of Object.entries(s)) {
    if (!b || typeof b !== "object") continue;
    for (const status of ["elevated", "new", "held"]) {
      for (const r of Array.isArray(b[status]) ? b[status] : []) out.push({ ...r, holon: r.holon || holon, status, as_of: r.as_of || b.as_of || null });
    }
  }
  return out;
}
function sightingsKnown(ctx) { return ctx.state.sightings != null; }
function sightKindWord(ctx, s) {
  if (!s.kind) return ctx.t("map.sight.kind_unknown");
  const w = ctx.t("map.sight.kind." + s.kind);
  return w.startsWith("[") ? s.kind : w;
}
function sightStatusWord(ctx, s) { return s.status ? ctx.t("map.sight.status." + s.status) : ctx.t("map.sight.status_unknown"); }

// ------------------------------------------------------------------ the engraved seals (SVG)

const SVGNS = "http://www.w3.org/2000/svg";
function s(tag, attrs) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  return el;
}
/** The eight Sightings, eight shapes a child could tell apart, and the milestone's diamond. Each
    is a hairline drawing on a small disc of the ground, so it sits on the membrane like a seal
    on a ribbon. Drawn in a 24-unit box centred on 0,0; no fill, no light. */
const GLYPH = {
  defect: "M-2 -8 L2 -2 L-2 2 L2 8",                                   // a crack
  hazard: "M0 -7 L7.5 6 L-7.5 6 Z M0 -2 V2 M0 4 V4.2",                  // a warning triangle
  blocked: "M-7 0 A7 7 0 1 0 7 0 A7 7 0 1 0 -7 0 Z M-5 0 H5",           // a barred circle
  wonder: "M0 0 A1.5 1.5 0 0 1 3 0 A3 3 0 0 1 -3 0 A4.5 4.5 0 0 1 6 0 A6 6 0 0 1 -6.5 0",   // a spiral
  offer: "M-7 -1 H7 A7 7 0 0 1 -7 -1 Z M-2 -4 A2 2 0 1 0 2 -4",        // a bowl, something in it
  request: "M-5.5 4 V-1 A5.5 5.5 0 0 1 5.5 -1 V4 H-7 H7 M-1.2 6.5 H1.2", // a bell
  question: "M-3.5 -3.5 A3.5 3.5 0 1 1 0.5 0 Q0 1 0 3 M0 5.8 V6",      // a question mark
  witness: "M-8 0 Q0 -7 8 0 Q0 7 -8 0 Z M-2.2 0 A2.2 2.2 0 1 0 2.2 0 A2.2 2.2 0 1 0 -2.2 0",   // an eye
  milestone: "M0 -6 L6 0 L0 6 L-6 0 Z",                                 // a diamond
  owed: "M-5 -7 H5 A1.5 1.5 0 0 1 6.5 -5.5 V5.5 A1.5 1.5 0 0 1 5 7 H-5 A1.5 1.5 0 0 1 -6.5 5.5 V-5.5 A1.5 1.5 0 0 1 -5 -7 Z M-3 -2 H3 M-3 1.5 H1.5",   // a card, waiting on you
  unknown: "M-5 0 H5 M0 -5 V5",
};
function seal(kind, x, y, scale, cls) {
  const g = s("g", { class: `seal ${cls || ""}`, transform: `translate(${x} ${y}) scale(${scale})` });
  g.append(s("circle", { r: 10.5, class: "seal-disc" }), s("path", { d: GLYPH[kind] || GLYPH.unknown, class: "seal-line" }));
  return g;
}
/** The same seal as a small inline picture, for the sheet (so the key is the picture itself). */
function sealIcon(kind, cls) {
  const svg = s("svg", { class: `seal-icon ${cls || ""}`, viewBox: "-12 -12 24 24", "aria-hidden": "true", focusable: "false" });
  svg.append(s("path", { d: GLYPH[kind] || GLYPH.unknown, class: "seal-line" }));
  return svg;
}

// ------------------------------------------------------------------ the view

export default function createMap() {
  let el, ctx, root, ro = null, anims = [], probe = null, still = false;
  let board = null, scene = null, trim = 0, trimmed = false;
  let focusId = null, focusSight = null, mode = null;    // mode: null · "axes" · "chain"
  ensureCss("map.css");

  function stopTurning() { for (const a of anims) { try { a.cancel(); } catch { /* gone */ } } anims = []; }

  function draw() {
    stopTurning();
    if (board) { try { board.unmount(); } catch { /* gone */ } board = null; }
    root.textContent = "";
    scene = null; mode = null;
    const holonId = ctx.route && ctx.route.name === "map" && ctx.route.arg;
    if (holonId && ctx.slot === "full") drawBoard(holonId);
    else drawWhole();
  }

  // ============================================================ the whole
  function drawWhole() {
    const t = ctx.t;
    const F = fields(ctx);
    const all = [...F.near, ...F.middle, ...F.far];
    if (!all.length && !F.unread.length) {
      root.append(h("p", { class: "map-title voice" }, t("map.title_line")),
        h("p", { class: "map-empty" }, ctx.loading ? t("app.reading") : t("app.not_computed")));
      return;
    }
    root.append(stage(F), twin(F), printKey(F));
    fitLabels();
    // one screen: whatever the page puts below the scene is measured once and taken from the scene
    const over = document.documentElement.scrollHeight - (window.innerHeight || 0);
    if (over > 2 && !trimmed) { trimmed = true; trim += over; draw(); return; }
    if (all.length === 1 && !F.unread.length) scene.say.textContent = t("map.empty");
    if (lastFocus && !focusId) { focusId = lastFocus; lastFocus = null; }
    if (focusId) focus(focusId, focusSight, false);
  }

  /** What is owed by the wearer, the one with the least float first: on the chain before off it,
      then the nearest by-when. */
  /** The card an owed entry is about: the same id, else the card of the same title in its holon. */
  function cardOf(e) {
    const cards = ctx.state.cards || [];
    return cards.find((c) => c.id === e.id) || cards.find((c) => c.holon === e.holon && c.title === e.title) || null;
  }
  function owedSorted() {
    const st = ctx.state;
    const crit = new Set((st.path && st.path.critical) || []);
    const rows = ((st.owed && st.owed.entries) || []).filter((e) => e.holder === st.actor && e.status !== "done");
    const order = ctx.read.owedByStake ? ctx.read.owedByStake(st).map((e) => e.id) : rows.map((e) => e.id);
    const big = 1e9;
    return rows.map((e) => {
      const c = cardOf(e) || {};
      return { ...e, card: c.id ? c : null, due: e.due || c.by || null, tf: typeof c.TF === "number" ? c.TF : big,
        critical: crit.has(e.id) || crit.has(c.id) || !!c.critical };
    }).sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));   // the one order (state.js read.owedByStake), shared with the Deal
  }
  function leadOwed() { return owedSorted()[0] || null; }
  /** What a card holds up: the last of the cards downstream of it, following successors. */
  function holdsUp(card) {
    if (!card) return null;
    const cards = ctx.state.cards || [], seen = new Set();
    let cur = card, last = null;
    while (cur && (cur.successors || []).length && !seen.has(cur.id)) {
      seen.add(cur.id);
      const nxt = cards.find((c) => c.id === cur.successors[0]);
      if (!nxt) break;
      last = nxt; cur = nxt;
    }
    return last;
  }
  const lowerThe = (x) => String(x || "").replace(/^The /, "the ");
  /** The one breath at the top: what is owed, the first of it, and what that holds up. */
  function breath() {
    const t = ctx.t, all = owedSorted(), lead = all[0];
    if (!lead) return t("map.breath.none");
    const where = ctx.read.holonName(ctx.state, lead.holon) || "";
    const by = lead.due ? ", " + ctx.fmt.by(lead.due) : "";
    const n = ctx.fmt.number(all.length, true);
    let line = all.length === 1 ? t("map.breath.one", { title: lead.title, where, by })
      : t("map.breath.many", { n: n.charAt(0).toUpperCase() + n.slice(1), title: lead.title, where, by });
    const up = holdsUp(lead.card);
    if (up) line += " " + t("map.breath.holds", { what: lowerThe(up.title) });
    else if (lead.critical) line += " " + t("map.breath.blocks");
    return line;
  }
  /** A card's place on the chain across the whole, counting from 1; 0 when it is not on it. */
  function chainIndex(id) {
    const crit = ((ctx.state.path && ctx.state.path.critical) || []).filter((k) => { const c = (ctx.state.cards || []).find((y) => y.id === k); return c && !DONE.has(c.state); });
    return crit.indexOf(id) + 1;
  }
  /** Stake in a field, computed: what waits on the wearer there, and the open cards of the chain there. */
  function stakeOf(id) { return waitingOnYou(ctx, id).length + onChain(ctx, id).length; }

  /** A name is never cut by the edge: each label is nudged inside the scene once it is measured.
      Every size is read first and every place written last, so the page lays out once (the
      performance pass, 2026-10-25: reading offsetWidth after each write forced a layout per label). */
  function fitLabels() {
    if (!scene) return;
    const W = scene.W, pad = 4;
    const ls = [...scene.wrap.querySelectorAll(".field-label")];
    const box = ls.map((lb) => ({ w: lb.offsetWidth, hg: lb.offsetHeight, x: parseFloat(lb.style.left) || 0, y: parseFloat(lb.style.top) || 0 }));
    for (const q of box) {
      const lo = q.w / 2 + pad, hi = W - q.w / 2 - pad;
      if (q.x < lo) q.x = lo; else if (q.x > hi) q.x = Math.max(lo, hi);
      if (q.y + q.hg > scene.H - pad) q.y = scene.H - pad - q.hg;
    }
    // two names never sit on one another: where they would, they part sideways, within the scene
    for (let pass = 0; pass < 6; pass++) {
      let moved = false;
      for (let i = 0; i < box.length; i++) for (let j = i + 1; j < box.length; j++) {
        const a = box[i], b = box[j];
        const ox = (a.w + b.w) / 2 + 8 - Math.abs(a.x - b.x);
        const oy = Math.min(a.y + a.hg, b.y + b.hg) - Math.max(a.y, b.y);
        if (ox > 0 && oy > 0) {
          const [l, r] = a.x <= b.x ? [a, b] : [b, a];
          const lx = Math.max(l.w / 2 + pad, l.x - ox / 2);
          const rx = Math.min(W - r.w / 2 - pad, r.x + ox / 2);
          l.x = lx; r.x = rx;
          moved = true;
        }
      }
      if (!moved) break;
    }
    ls.forEach((lb, i) => { lb.style.left = `${box[i].x}px`; lb.style.top = `${box[i].y}px`; });
  }

  /** How many person fields compose a holon: its people, from roles (agents are not fields). */
  function members(x) {
    const r = (ctx.state.roles || {})[x.id] || {};
    const n = Object.entries(r).filter(([a0, role]) => String(a0).startsWith("person:") && role !== "agent").length;
    const [lo, hi] = MEMBERS[x.kind] || MEMBERS.cell;
    return Math.max(lo, Math.min(hi, x.kind === "body" ? Math.max(n * 3, lo) : n || lo + 1));
  }

  /** The composition, in pixels. O is the ØNE. Each field: its hole (cx, cy), its lean toward O,
      the person fields that compose it, and its membrane (rx, ry). Sizes follow the perspective:
      a field's size grows with its distance below the still point. */
  function layout(F, W, H, phone, oy) {
    const S = phone ? SLOTS.phone : SLOTS.desk;
    const O = { x: W / 2, y: oy };
    const homeY = phone ? O.y + S.near[0][1] * (H - O.y) : S.near[0][1] * H;
    const homeRx = phone ? Math.min(W * 0.42, (H - oy) * 0.3) : Math.min(W * 0.165, H * 0.3);
    const items = [];
    // on the phone the words at the top take what height they need; the picture is laid out in
    // what is left between the still point and the foot
    const yAt = (fy) => (phone ? O.y + fy * (H - O.y) : fy * H);
    const place = (x, depth, fx, fy) => {
      const cx = fx * W, cy = yAt(fy);
      const persp = Math.max(0.12, (cy - O.y) / (homeY - O.y));
      const isHome = depth === "near";
      // on the phone in large type a field with nothing at stake stays small and unnamed; the dolly names it
      const quiet = phone && ctx.prefs.large && !isHome && !x.unread && stakeOf(x.id) === 0;
      const R = homeRx * persp * (isHome ? 1 : (x.unread ? 0.9 : STAKE_SCALE(stakeOf(x.id))) * (depth === "far" ? 1.6 : 1.12) * (quiet ? 0.7 : 1));
      const lean = Math.atan2(cx - O.x, cy - O.y) * 0.1;        // radians; the field leans a little toward its ray
      items.push({ x, depth, cx, cy, R: isHome ? R : Math.min(R, homeRx * 0.85), lean, persp, quiet });   // the near field stays the largest
    };
    F.near.forEach((x) => place(x, "near", S.near[0][0], S.near[0][1]));
    const mid = [...F.middle, ...F.unread.map((u) => ({ id: u.holon, name: u.name, kind: "cell", unread: u }))];
    mid.forEach((x, i) => {
      const sl = S.middle[i] || [0.5 + (i % 2 ? 1 : -1) * (0.08 + 0.05 * i), 0.3];
      place(x, "middle", sl[0], sl[1]);
    });
    F.far.forEach((x, i) => {
      const sl = S.far[i] || [0.5 + (i % 2 ? 1 : -1) * 0.12, 0.15];
      place(x, "far", sl[0], sl[1]);
    });
    for (const it of items) compose(it);
    // Home keeps the foot with room for its seals and its words beneath it
    const room = (phone ? 62 : 78) * (ctx.prefs.large ? 1.3 : 1) + 26;
    for (const it of items) if (it.depth === "near" && it.cy + it.ry + room > H) it.cy = H - it.ry - room;
    // nothing overlaps by accident: a field that would touch a nearer one gives way (smaller)
    for (let pass = 0; pass < 14; pass++) {
      let moved = false;
      for (const a of items) for (const b of items) {
        if (a === b || !(b.cy > a.cy)) continue;          // a is the farther
        const dx = Math.abs(a.cx - b.cx), dy = Math.abs(a.cy - b.cy);
        const ox = a.rx + b.rx + 8 - dx, oyy = a.ry + b.ry + b.top0 + 44 - dy;   // room for the farther one's name
        if (ox > 0 && oyy > 0 && a.R > b.R * 0.2) { a.R *= 0.93; compose(a); moved = true; }
      }
      if (!moved) break;
    }
    // and nothing is cut by the edge
    for (const it of items) {
      const m = 10;
      if (it.cx - it.rx < m || it.cx + it.rx > W - m) { it.R *= Math.max(0.5, (Math.min(it.cx, W - it.cx) - m) / it.rx); compose(it); }
    }
    return { O, items, W, H, phone };
  }

  /** The person fields that compose a field, loosely placed around no center (a stable hash of
      the holon id), and the membrane that holds them. */
  function compose(it) {
    const { x, R } = it;
    const k = x.unread ? 0 : members(x);
    const subs = [];
    if (k <= 1) subs.push({ dx: 0, dy: 0, size: (R / UNIT.rx) });
    else {
      const turn0 = unit(x.id, 3) * Math.PI * 2;
      const s0 = (R * (k > 6 ? 0.5 : 0.62)) / UNIT.rx;
      for (let j = 0; j < k; j++) {
        const a = turn0 + (2 * Math.PI * j) / k + (unit(x.id, j + 5) - 0.5) * 0.7;
        const r = R * (k > 6 ? 0.5 : 0.42) * (0.75 + 0.5 * unit(x.id, j + 11));
        subs.push({ dx: Math.cos(a) * r, dy: Math.sin(a) * r * 0.42, size: s0 * (0.8 + 0.35 * unit(x.id, j + 23)) });
      }
    }
    const ringRx = Math.max(...subs.map((q) => q.size * UNIT.rx)), ringRy = Math.max(...subs.map((q) => q.size * UNIT.ry));
    it.subs = subs;
    it.rx = x.unread ? R * 0.8 : Math.max(...subs.map((q) => Math.abs(q.dx))) + ringRx * (k <= 1 ? 1.06 : 1.04);
    it.ry = x.unread ? R * 0.34 : Math.max(...subs.map((q) => Math.abs(q.dy))) + ringRy * (k <= 1 ? 1.14 : 1.1);
    it.top0 = Math.max(0, Math.max(...subs.map((q) => q.size * (UNIT.hole[1] - UNIT.top))) - ringRy);   // the gathering lines above the ring
  }

  function stage(F) {
    const t = ctx.t;
    const W = Math.max(280, Math.round(root.clientWidth || el.clientWidth || 360));
    const phone = W < 600;
    const top = root.getBoundingClientRect().top + (window.scrollY || 0);
    const avail = (window.innerHeight || 800) - Math.max(0, top) - 8 - trim;
    let H = Math.round(phone ? Math.max(W * 1.5, avail - 56) : Math.max(560, Math.min(avail, W * 0.72)));   // one screen: the whole is in view or it is not a map

    const wrap = h("div", { class: `map-stage${phone ? " is-phone" : ""}`, style: `height:${H}px` });
    const actChain = h("button", { class: "map-act act-chain voice", onclick: (e) => { e.stopPropagation(); chainAct(); } }, t("map.to_chain"));
    const say = h("p", { class: "map-say voice", "aria-live": "polite" });
    // on the phone the second act and the agent's line sit under the words at the top, so the
    // whole picture is one screen and Home keeps the foot
    const actAxes = h("button", { class: "map-act act-axes voice", onclick: (e) => { e.stopPropagation(); axesAct(); } }, t("map.hold_button"));
    const title = h("div", { class: "map-title" }, h("p", { class: "map-breath" }, breath()), h("p", { class: "map-canon voice" }, t("map.title_line")),
      phone ? h("div", { class: "map-acts" }, actAxes, actChain) : null, phone ? say : null);
    wrap.append(title);
    root.append(wrap);                       // measured in place, then composed
    const tb = title.offsetTop + title.offsetHeight;
    const oy = phone ? tb + 30 : Math.max(SLOTS.desk.one * H, 40);
    root.removeChild(wrap);
    // the picture keeps its own height under the words; only where the screen cannot hold both
    // (large type on the smallest phone) does the page scroll, and then by a little
    if (phone && H < oy + W * (ctx.prefs.large ? 1.05 : 1.3)) { H = Math.round(oy + W * (ctx.prefs.large ? 1.05 : 1.3)); wrap.style.height = `${H}px`; }

    const L = layout(F, W, H, phone, oy);
    const cam = h("div", { class: "map-camera" });
    const art = h("div", { class: "map-art", "aria-hidden": "true" });
    const svgBack = s("svg", { class: "map-svg map-svg-back", viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true" });
    const svg = s("svg", { class: "map-svg", viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true" });
    const defs = s("defs");
    svgBack.append(defs);
    const labels = h("div", { class: "map-labels", "aria-hidden": "true" });
    const hits = h("div", { class: "map-hits" });
    cam.append(svgBack, art, svg, labels, hits);
    wrap.append(cam);

    const reduced = ctx.prefs.reducedMotion;
    const order = ["near", "middle", "far"];
    const sAll = sightings(ctx);
    const lead = leadOwed();
    const crit = (ctx.state.path && ctx.state.path.critical) || [];
    const chainOrder = crit.map((id) => (ctx.state.cards || []).find((c) => c.id === id)).filter((c) => c && !DONE.has(c.state));
    const paint = [...L.items].sort((a, b) => a.cy - b.cy);   // far fields painted first

    // ---- the axes: each from where its field's gathering lines end, up its ray to the ØNE.
    // They stop a breath short of the still point; nothing is drawn where they meet.
    const axes = s("g", { class: "axes" });
    svgBack.append(axes);
    paint.forEach((it, i) => {
      const up = it.top0 + it.ry * 0.9;
      const sx = it.cx + Math.sin(it.lean) * up, sy = it.cy - Math.cos(it.lean) * up;
      const dx = L.O.x - sx, dy = L.O.y - sy, len = Math.hypot(dx, dy), gap = phone ? 7 : 11;
      const ex = L.O.x - (dx / len) * gap, ey = L.O.y - (dy / len) * gap;
      const gid = `map-axis-${i}`;
      const grad = s("linearGradient", { id: gid, gradientUnits: "userSpaceOnUse", x1: sx, y1: sy, x2: ex, y2: ey });
      grad.append(s("stop", { offset: "0", class: "axis-stop-a" }), s("stop", { offset: "1", class: "axis-stop-b" }));
      defs.append(grad);
      const line = s("line", { x1: sx, y1: sy, x2: ex, y2: ey, class: `axis${ctx.filter && ctx.filter !== it.x.id ? " is-dim" : ""}`, stroke: `url(#${gid})`, "data-holon": it.x.id, "data-len": String(len) });
      axes.append(line);
    });

    // ---- each field
    let fadeIndex = 0;
    for (const it of paint) {
      const { x, cx, cy, rx, ry } = it;
      const step = x.unread ? 2 : freshStep(ctx, x);
      const dim = ctx.filter && ctx.filter !== x.id;
      const secs = x.unread ? null : turnSeconds(ctx, x);
      const group = h("div", { class: `field-group depth-${it.depth} fresh-${step}${dim ? " is-dim" : ""}`, dataset: { holon: x.id },
        style: `transform:rotate(${it.lean}rad);transform-origin:${cx}px ${cy}px` });
      art.append(group);
      it.subs.forEach((q, j) => {
        const size = q.size, k = UNIT.rx / UNIT.ry, origin = `50% ${UNIT.hole[1] * 100}%`;
        const left = cx + q.dx - size / 2, topY = cy + q.dy - UNIT.hole[1] * size;
        const field = h("div", { class: "field", style: `left:${left}px;top:${topY}px;width:${size}px;height:${size}px` });
        const lum = maskStyle(UNIT.src);
        const img1 = h("img", { src: UNIT.src, alt: "", decoding: "async", draggable: "false", style: lum });
        const band = h("div", { class: "field-static" }, img1);
        const rot = h("div", { class: "field-rot", style: `transform-origin:${origin}` },
          h("img", { src: UNIT.src, alt: "", decoding: "async", draggable: "false", style: `${lum}transform:scaleY(${k});transform-origin:${origin}` }));
        const turn = h("div", { class: "field-turn", style: `transform:scaleY(${1 / k});transform-origin:${origin}` }, rot);
        field.append(band, turn);
        group.append(field);
        if (secs && !reduced && !still) {
          const a = ctx.animate(rot, [{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }],
            { duration: secs * 1000 * (0.92 + 0.16 * unit(x.id, j + 41)), iterations: Infinity, easing: css("--e-turn") || "linear", iterationStart: unit(x.id, j + 53) });
          if (a) anims.push(a);
        }
        ctx.animate(field, [{ opacity: 0 }, { opacity: 1 }],
          { duration: ms("--d-card"), delay: (2 - order.indexOf(it.depth)) * ms("--d-settle") + fadeIndex * 50, easing: css("--e-settle"), fill: "backwards" });
        fadeIndex++;
      });

      // the membrane, leaned with its field; its seals ride on it
      const mg = s("g", { class: `membrane-g depth-${it.depth} fresh-${step}${dim ? " is-dim" : ""}`, transform: `rotate(${(it.lean * 180) / Math.PI} ${cx} ${cy})`, "data-holon": x.id });
      svg.append(mg);
      mg.append(s("ellipse", { cx, cy, rx, ry, class: `membrane${step === 2 || ctx.offline ? " is-dashed" : ""}${x.unread ? " is-unread" : ""}` }));
      // the pencil outline (print only): three inner rings round each open hole
      const pencil = s("g", { class: "pencil" });
      for (const q of it.subs) for (let r0 = 1; r0 <= 3; r0++) {
        pencil.append(s("ellipse", { cx: cx + q.dx, cy: cy + q.dy, rx: (q.size * UNIT.rx * r0) / 3, ry: (q.size * UNIT.ry * r0) / 3 }));
      }
      mg.append(pencil);

      const pt = (a, k = 1) => ({ x: cx + rx * k * Math.cos(a), y: cy + ry * k * Math.sin(a) });
      const turnPt = (p) => {   // a point on the leaned membrane, in stage coordinates (for the hit targets)
        const c = Math.cos(it.lean), sn = Math.sin(it.lean), X = p.x - cx, Y = p.y - cy;
        return { x: cx + X * c - Y * sn, y: cy + X * sn + Y * c };
      };
      const sc = Math.max(0.72, Math.min(1.15, 0.6 + it.persp * 0.55)) * (ctx.prefs.large ? 1.2 : 1);
      if (!x.unread) {
        // the chain, inside each field it passes through, numbered in its order across the whole;
        // no line is drawn from field to field (no center but ØNE). Then the milestones off the chain.
        const chainHere0 = chainOrder.filter((c) => c.holon === x.id);
        const offChain = milestones(ctx, x.id).filter((c) => !chainOrder.some((k) => k.id === c.id));
        const upper = [...chainHere0.map((c) => ({ c, k: chainOrder.indexOf(c) + 1 })), ...offChain.map((c) => ({ c, k: 0 }))].slice(0, 6);
        upper.forEach(({ c, k }, i) => {
          const a = Math.PI * (1.5 + Math.min(0.13, 0.5 / Math.max(1, upper.length - 1)) * (i - (upper.length - 1) / 2) * (upper.length > 1 ? 1 : 0));
          const p = pt(a);
          mg.append(seal("milestone", p.x, p.y, sc * 0.9, `is-milestone${k ? " is-chain" : ""}`));
          if (k) {
            const num = s("text", { x: p.x, y: p.y - 10.5 * sc - 5, class: "chain-num" });
            num.textContent = String(k);
            mg.append(num);
          }
          const q = turnPt(p);
          hits.append(markButton(q.x, q.y, k ? t("map.mark.chain", { n: String(k), title: c.title }) : t("map.mark.milestone", { title: c.title }), () => ctx.openCard(c.id)));
        });
        // what was seen, on the near (lower) arc, facing the wearer
        // on the phone in large type only Home carries its seals; the rest open with the dolly
        const seen = phone && ctx.prefs.large && it.depth !== "near" ? [] : sAll.filter((y) => y.holon === x.id);
        const n = Math.min(seen.length, 9);
        const sealStep = Math.min(0.24, Math.max(Math.min(0.15, 0.62 / Math.max(1, n - 1)), (25 * sc) / (rx * Math.PI)));
        seen.slice(0, 9).forEach((y, i) => {
          const a = Math.PI * (0.5 + (i - (n - 1) / 2) * sealStep);
          const p = pt(a);
          mg.append(seal(y.kind, p.x, p.y, sc, `is-sight is-${y.status || "unknown"}`));
          if ((!phone && it.depth !== "far") || (phone && !ctx.prefs.large && it.depth === "near")) {   // the key is the picture: each seal says its kind beneath it
            const w = s("text", { x: p.x, y: p.y + 10.5 * sc + 14, class: "seal-word" });
            w.textContent = sightKindWord(ctx, y);
            mg.append(w);
          }
          const q = turnPt(p);
          hits.append(markButton(q.x, q.y, sightLabel(y), () => focus(x.id, y.id, true), y.id));
        });
        // the one lit point: the thing owed by the wearer with the least float, where it sits, on
        // the near arc beside what was seen there; its words stand under the field's name
        if (lead && lead.holon === x.id) {
          const a = Math.PI * (n ? 0.5 + ((n - 1) / 2 + 0.85) * sealStep : 0.5), p = pt(a);
          mg.append(seal("owed", p.x, p.y, sc * 1.1, "is-owed"));
          const q = turnPt(p);
          hits.append(markButton(q.x, q.y, t("map.lead_label", { title: lead.title }), () => ctx.openCard((lead.card && lead.card.id) || lead.id)));
        }
      }

      // the name at the foot of the field, small capitals, its freshness in a word
      const foot = turnPt(pt(Math.PI / 2, 1));
      const marked = (phone && ctx.prefs.large && it.depth !== "near" ? false : sAll.some((y) => y.holon === x.id)) || (lead && lead.holon === x.id);
      const worded = sAll.some((y) => y.holon === x.id) && ((!phone && it.depth !== "far") || (phone && !ctx.prefs.large && it.depth === "near"));
      const ly = Math.min(L.H - 40, foot.y + (marked ? 13 * sc + (worded ? 24 : 6) : 6));
      // what the engine computed is said on the picture: what waits on her here, and the chain
      // with its by-when. Nothing is lit where nothing is owed (salience follows stake).
      const owes = x.unread ? [] : waitingOnYou(ctx, x.id), chainHere = x.unread ? [] : onChain(ctx, x.id);
      const by = chainHere.map((c) => c.due || c.by).filter(Boolean).sort()[0];
      if (!it.quiet) labels.append(h("div", { class: `field-label depth-${it.depth} fresh-${step}${dim ? " is-dim" : ""}${owes.length ? " is-owed" : ""}`, dataset: { holon: x.id }, style: `left:${foot.x}px;top:${ly}px` },
        h("span", { class: "caps" }, x.name),
        phone && step === 0 ? null : h("span", { class: "field-fresh" }, freshWord(ctx, x)),
        lead && lead.holon === x.id ? h("span", { class: "field-lead" }, lead.title + (lead.due ? ", " + ctx.fmt.by(lead.due) : "")) : null,
        owes.length && !(lead && lead.holon === x.id && (owes.length === 1 || phone)) ? h("span", { class: "field-owed" }, lead && lead.holon === x.id
          ? t("map.pic.owed_more", { n: ctx.fmt.number(owes.length - 1, true) })
          : owes.length === 1 ? t("map.pic.owed_one") : t("map.pic.owed", { n: ctx.fmt.number(owes.length, true) })) : null,
        chainHere.length && !phone ? h("span", { class: "field-chain" }, "◆ ", by ? t("map.pic.chain_by", { n: ctx.fmt.number(chainHere.length, true), by: ctx.fmt.by(by) || "" }) : t("map.pic.chain", { n: ctx.fmt.number(chainHere.length, true) })) : null));
      if (owes.length) group.classList.add("is-owed");

      // the field as a button (opens its sheet); its open hole, pressed and held, shows where every axis points
      const label = x.unread ? t("ribbon.unread_explain", { holon: x.name, reason: typeof x.unread.readable === "string" ? x.unread.readable : "" })
        : t("map.field_label", { name: x.name, kind: kindWord(ctx, x), fresh: asOfWords(ctx, x) });
      hits.append(h("button", { class: "field-hit", "aria-label": label, dataset: { holon: x.id },
        style: `left:${cx - rx}px;top:${cy - ry - it.top0 * 0.6}px;width:${rx * 2}px;height:${ry * 2 + it.top0 * 0.6}px;transform:rotate(${it.lean}rad);transform-origin:${rx}px ${ry + it.top0 * 0.6}px`,
        onclick: (e) => { e.stopPropagation(); focus(x.id, null, true); } }));
      if (!x.unread) hits.append(holeButton(x, cx, cy));
    }

    // ---- the ØNE: where every axis meets. Nothing is drawn there; the lines gather and stop.
    hits.append(h("button", { class: "one-hit", "aria-label": t("map.one_label"), style: `left:${L.O.x}px;top:${L.O.y}px`,
      onclick: (e) => { e.stopPropagation(); axesAct(); } }));

    // ---- the two acts, in the agent's voice, drawn into the scene
    // on the desk the first act stands beside the still point; on the phone, with the second, under the words
    if (!phone) actAxes.style.cssText = `left:${L.O.x + 26}px;top:${L.O.y}px;max-width:${Math.max(120, W - L.O.x - 32)}px`;
    const sheet = h("aside", { class: "map-sheet", "aria-label": t("map.sheet_label"), hidden: true, onclick: (e) => e.stopPropagation() });
    wrap.append(...[title, phone ? null : actAxes, phone ? null : actChain, phone ? null : say, sheet].filter(Boolean));

    wrap.addEventListener("click", () => { if (focusId) unfocus(true); else if (mode) clearMode(); });
    scene = { wrap, cam, axes, sheet, say, L, H, W, phone };
    if (anims.length) fpsProbe();
    return wrap;
  }

  function markButton(x, y, label, fn, sid) {
    return h("button", { class: "mark-hit", "aria-label": label, title: label, dataset: sid ? { sight: sid } : null, style: `left:${x}px;top:${y}px`,
      onclick: (e) => { e.stopPropagation(); fn(); } });
  }
  function sightLabel(y) {
    return ctx.t("map.sight.label", { kind: sightKindWord(ctx, y), status: sightStatusWord(ctx, y), text: y.text || "" });
  }

  function holeButton(x, cx, cy) {
    let timer = null, held = false;
    const b = h("button", { class: "hole-hit", tabindex: "-1", "aria-hidden": "true", style: `left:${cx}px;top:${cy}px` });
    b.addEventListener("pointerdown", () => { held = false; timer = setTimeout(() => { held = true; axesAct(); }, 550); });
    for (const ev of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(ev, () => clearTimeout(timer));
    b.addEventListener("click", (e) => { e.stopPropagation(); if (held) { held = false; return; } focus(x.id, null, true); });
    b.addEventListener("contextmenu", (e) => e.preventDefault());
    return b;
  }

  // ------------------------------------------------------------ the camera
  function setCamera(tx, ty, k, animate) {
    if (!scene) return;
    const to = `translate(${tx}px, ${ty}px) scale(${k})`;
    const from = scene.cam.style.transform || "translate(0px, 0px) scale(1)";
    scene.cam.style.transform = to;
    if (animate && from !== to) ctx.animate(scene.cam, [{ transform: from }, { transform: to }], { duration: ms("--d-dolly"), easing: css("--e-settle") });
  }

  /** Tap a field (or one of its seals): the camera dollies toward it and its sheet opens beside it. */
  function focus(id, sightId, animate) {
    if (!scene) return;
    const it = scene.L.items.find((i) => i.x.id === id);
    if (!it) { focusId = null; return; }
    if (mode) clearMode(true);
    const already = focusId === id;
    focusId = id; focusSight = sightId || null;
    const { W, H, phone } = scene;
    const large = ctx.prefs.large;
    const sheetW = phone ? W : Math.min(large ? 520 : 400, Math.round(W * (large ? 0.42 : 0.34)));
    const boxW = phone ? W : W - sheetW - 24, boxH = phone ? H * 0.46 : H;
    const fw = (it.rx * 2) / (boxW * (it.depth === "near" ? 0.92 : 0.66)), fh = (it.ry * 2 + it.top0) / (boxH * 0.6);
    const k = Math.max(1, Math.min(phone ? 2.4 : 1.9, 1 / Math.max(fw, fh)));
    const tx = boxW / 2 - it.cx * k, ty = boxH * (phone ? 0.42 : 0.54) - it.cy * k;
    setCamera(tx, ty, k, animate && !already);
    scene.wrap.dataset.focus = id;
    for (const n of scene.wrap.querySelectorAll("[data-holon]")) n.classList.toggle("is-away", n.dataset.holon !== id);
    fillSheet(it.x, sightId, animate && !already);
  }
  function unfocus(animate) {
    if (!scene) return;
    focusId = null; focusSight = null;
    setCamera(0, 0, 1, animate);
    delete scene.wrap.dataset.focus;
    for (const n of scene.wrap.querySelectorAll(".is-away")) n.classList.remove("is-away");
    scene.sheet.hidden = true;
    scene.sheet.textContent = "";
  }

  function fillSheet(x, sightId, rise) {
    const t = ctx.t, sh = scene.sheet;
    sh.textContent = "";
    sh.hidden = false;
    sh.append(h("button", { class: "link-btn map-sheet-close", onclick: () => unfocus(true) }, "← " + t("map.back_whole")),
      h("h2", { class: "caps map-sheet-name" }, x.name),
      h("p", { class: "map-sheet-meta" }, asOfWords(ctx, x)));
    if (x.unread) {
      sh.append(h("p", null, t("ribbon.unread_explain", { holon: x.name, reason: typeof x.unread.readable === "string" ? x.unread.readable : "" })));
      return;
    }
    sh.append(h("p", { class: "map-sheet-turn voice" }, turnWords(ctx, x)));
    const seen = sightings(ctx).filter((y) => y.holon === x.id);
    const chosen = sightId && seen.find((y) => y.id === sightId);
    if (chosen) sh.append(sightCard(chosen));

    const wait = waitingOnYou(ctx, x.id);
    sh.append(h("section", { class: "map-sheet-part" }, h("h3", { class: "eyebrow" }, t("map.sheet.waiting_title")),
      wait.length ? h("ul", { class: "map-sheet-lines" }, wait.map((e) => h("li", null,
        h("button", { class: "link-btn", onclick: () => ctx.openCard(e.id) }, e.title))))
        : h("p", { class: "dust" }, t("map.sheet.waiting_none"))));

    const chain = onChain(ctx, x.id).sort((a, b) => chainIndex(a.id) - chainIndex(b.id));
    if (chain.length) sh.append(h("section", { class: "map-sheet-part" }, h("h3", { class: "eyebrow" }, t("map.sheet.chain_title")),
      h("ul", { class: "map-sheet-lines" }, chain.map((c) => h("li", null, h("span", { class: "map-sheet-diamond", "aria-hidden": "true" }, `◆ ${chainIndex(c.id) || ""}`),
        h("button", { class: "link-btn", onclick: () => ctx.openCard(c.id) }, c.title))))));

    sh.append(h("section", { class: "map-sheet-part" }, h("h3", { class: "eyebrow" }, t("map.sight.here")),
      !sightingsKnown(ctx) ? h("p", { class: "dust" }, t("map.sight.none_state"))
        : seen.length ? h("ul", { class: "map-sheet-seen" }, seen.map((y) => h("li", { class: y.id === sightId ? "is-chosen" : null },
          h("button", { class: "map-seen-btn", "aria-pressed": String(y.id === sightId), onclick: () => focus(x.id, y.id, false) },
            sealIcon(y.kind, `is-${y.status || "unknown"}`),
            h("span", { class: "map-seen-words" }, h("span", { class: "map-seen-kind" }, `${sightKindWord(ctx, y)} · ${sightStatusWord(ctx, y)}`), h("span", null, y.text || ""))))))
          : h("p", { class: "dust" }, t("map.sight.none_here"))));

    sh.append(h("a", { class: "pill map-sheet-board", href: `#/map/${encodeURIComponent(x.id)}`, onclick: () => { lastFocus = x.id; } }, t("map.sheet.open_board")));
    if (rise) ctx.animate(sh, [{ opacity: 0, transform: scene.phone ? "translateY(16px)" : "translateX(16px)" }, { opacity: 1, transform: "none" }],
      { duration: ms("--d-card"), delay: ms("--d-settle"), easing: css("--e-settle"), fill: "backwards" });
    sh.scrollTop = 0;
  }

  function sightCard(y) {
    const t = ctx.t, st = ctx.state;
    const m = {
      id: y.id, holon: y.holon, holonName: ctx.read.holonName(st, y.holon), card: null, deal: null, owed: null, ink: null,
      reason: t("map.sight.eyebrow", { status: sightStatusWord(ctx, y) }), kindLabel: sightKindWord(ctx, y),
      title: y.text || "", essence: null, options: [], needsYes: false, holder: null, by: null, minutes: null,
      spare: null, onChain: false, wholeWaits: false, asOfTs: y.as_of || null, alsoIn: [], publishedBy: null,
    };
    const face = ctx.card.renderCard(ctx, m, { form: "compact", selected: true });
    const seenBy = y.actor ? t("map.sight.seen_by", { who: ctx.read.who(st, y.actor, y.holon), when: ctx.fmt.when(y.ts) || "" }) : null;
    const why = y.elevated ? t("map.sight.elevated_why", { who: ctx.read.who(st, y.elevated.by, y.holon), to: ctx.read.holonName(st, y.elevated.to) || "", why: y.elevated.why || "" })
      : y.held ? t("map.sight.held_note", { note: y.held.note || "" }) : null;
    return h("div", { class: "map-sight-card" },
      h("div", { class: "map-sight-head" }, sealIcon(y.kind, `is-${y.status || "unknown"}`)),
      face, seenBy ? h("p", { class: "dust" }, seenBy) : null, why ? h("p", null, why) : null,
      !y.as_of ? h("p", { class: "dust" }, t("map.sight.as_of_unknown")) : null);
  }

  // ------------------------------------------------------------ the two acts
  function saySomething(...kids) {
    if (!scene) return;
    scene.say.textContent = "";
    scene.say.append(...kids.filter(Boolean));
  }
  function clearMode(silent) {
    if (!scene) return;
    mode = null;
    delete scene.wrap.dataset.mode;
    for (const n of scene.wrap.querySelectorAll(".is-off")) n.classList.remove("is-off");
    scene.say.textContent = "";
    if (!silent && !focusId) setCamera(0, 0, 1, true);
  }

  /** "Where every axis points": the camera returns to the whole (from any field it was near), and
      every axis rises again from its field to the still point. */
  function axesAct() {
    if (!scene) return;
    if (focusId) unfocus(false);
    if (mode === "axes") { clearMode(); return; }
    clearMode(true);
    mode = "axes";
    scene.wrap.dataset.mode = "axes";
    setCamera(0, 0, 1, true);
    for (const line of scene.axes.querySelectorAll(".axis")) {
      const len = parseFloat(line.getAttribute("data-len")) || 0;
      line.style.strokeDasharray = `${len}`;
      line.style.strokeDashoffset = "0";
      ctx.animate(line, [{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: ms("--d-bloom") * 1.6, easing: css("--e-settle") });
    }
    saySomething(ctx.t("map.hold_line"));
  }

  /** "What the whole is waiting on": the fields holding the chain stay; the rest fall back; one
      line says how many and which comes first, with the way to the Chain. */
  function chainAct() {
    if (!scene) return;
    if (focusId) unfocus(false);
    if (mode === "chain") { clearMode(); return; }
    clearMode(true);
    mode = "chain";
    scene.wrap.dataset.mode = "chain";
    const t = ctx.t, st = ctx.state;
    const crit = ((st.path && st.path.critical) || []).map((id) => (st.cards || []).find((c) => c.id === id)).filter((c) => c && !DONE.has(c.state));
    const holding = new Set(crit.map((c) => c.holon));
    for (const n of scene.wrap.querySelectorAll("[data-holon]")) n.classList.toggle("is-off", !holding.has(n.dataset.holon || n.getAttribute("data-holon")));
    setCamera(0, 0, 1, true);
    if (!crit.length) { saySomething(t("map.chain_none")); return; }
    const first = crit[0];
    saySomething(t("map.chain_line", { n: ctx.fmt.number(crit.length, true), title: first.title, where: ctx.read.holonName(st, first.holon) || "" }), " ",
      h("a", { class: "map-say-link", href: "#/chain" }, t("map.chain_open")));
  }

  // 60 fps on a phone, or the still form (DESIGN §1 check 8): measure the first turning second
  function fpsProbe() {
    if (probe) cancelAnimationFrame(probe);
    let frames = 0, start = 0;
    const tick = (now) => {
      if (!start) start = now;
      frames++;
      if (now - start < 1500) { probe = requestAnimationFrame(tick); return; }
      probe = null;
      const fps = (frames * 1000) / (now - start);
      if (fps < 50) { still = true; stopTurning(); root.dataset.still = "true"; }
      root.dataset.fps = String(Math.round(fps));
    };
    setTimeout(() => { probe = requestAnimationFrame(tick); }, ms("--d-bloom"));
  }

  // ------------------------------------------------------------ the twin, for the screen reader
  function twin(F) {
    const t = ctx.t;
    const sec = h("section", { class: "sr-only map-twin", "aria-label": t("map.list_title") }, h("h3", null, t("map.list_title")));
    const ol = h("ol");
    const rows = [...F.near.map((x) => [x, "near"]), ...F.middle.map((x) => [x, "middle"]), ...F.far.map((x) => [x, "far"])];
    for (const [x, depth] of rows) {
      const wait = waitingOnYou(ctx, x.id).length, chain = onChain(ctx, x.id).length;
      const seen = sightings(ctx).filter((y) => y.holon === x.id);
      const bits = [kindWord(ctx, x), t("map.depth." + depth), asOfWords(ctx, x),
        wait ? t("map.list.waiting", { n: ctx.fmt.number(wait, true) }) : t("map.list.waiting_none"),
        chain ? t("map.list.on_chain", { n: ctx.fmt.number(chain, true) }) : null, turnWords(ctx, x)].filter(Boolean);
      ol.append(h("li", null,
        h("button", { onclick: () => focus(x.id, null, false) }, x.name), " ", bits.join(" · "),
        seen.length ? h("ul", null, seen.map((y) => h("li", null, h("button", { onclick: () => focus(x.id, y.id, false) }, sightLabel(y))))) : null));
    }
    for (const u of F.unread) ol.append(h("li", null, u.name, " ", t("ribbon.unread_explain", { holon: u.name, reason: typeof u.readable === "string" ? u.readable : "" })));
    sec.append(ol);
    return sec;
  }

  // ------------------------------------------------------------ the paper key (print only)
  function printKey(F) {
    const t = ctx.t;
    const rows = [...F.near, ...F.middle, ...F.far];
    const box = h("section", { class: "map-print-key", "aria-hidden": "true" }, h("h3", { class: "caps" }, t("map.list_title")));
    for (const x of rows) {
      const seen = sightings(ctx).filter((y) => y.holon === x.id);
      box.append(h("div", { class: "map-print-field" },
        h("p", null, h("strong", null, x.name), " · ", [asOfWords(ctx, x), turnWords(ctx, x)].join(" · ")),
        seen.length ? h("ul", null, seen.map((y) => h("li", null, sealIcon(y.kind), " ", `${sightKindWord(ctx, y)} · ${sightStatusWord(ctx, y)}: ${y.text || ""}`))) : null));
    }
    return box;
  }

  // ============================================================ one field's Board, in place
  function drawBoard(id) {
    const t = ctx.t, st = ctx.state;
    const x = ctx.read.holon(st, id);
    const back = h("button", { class: "pill quiet", onclick: () => { lastFocus = id; ctx.go("#/map"); } }, "← " + t("map.back_whole"));
    if (!x) {
      const u = fields(ctx).unread.find((y) => y.holon === id);
      root.append(h("div", { class: "map-close-head" }, back),
        h("p", null, u ? t("ribbon.unread_explain", { holon: u.name, reason: typeof u.readable === "string" ? u.readable : "" }) : t("map.not_held")));
      return;
    }
    root.append(h("div", { class: "map-close-head" }, back,
      h("h2", { class: "caps map-close-name" }, x.name),
      h("p", { class: "dust" }, [kindWord(ctx, x), asOfWords(ctx, x), turnWords(ctx, x)].join(" · "))));
    const boardEl = h("div", { class: "map-board" });
    root.append(boardEl);
    board = createBoard();
    board.mount(boardEl, { ...ctx, filter: id, slot: "map", route: { name: "board", arg: id, params: ctx.route.params } });
    ctx.animate(root, [{ opacity: 0, transform: `scale(${1 / (parseFloat(css("--push-in")) || 1.14)})` }, { opacity: 1, transform: "none" }],
      { duration: ms("--d-card"), easing: css("--e-settle") });
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      root = h("div", { class: "map" });
      el.append(root);
      draw();
      if (typeof MASKS.get(UNIT.src) !== "string" && MASKS.get(UNIT.src) !== null) {
        prepareMask(UNIT.src).then(() => { if (root.isConnected) draw(); });
      }
      if (typeof ResizeObserver !== "undefined") {
        let last = root.clientWidth;
        ro = new ResizeObserver(() => { const w = root.clientWidth; if (Math.abs(w - last) > 24) { last = w; trim = 0; trimmed = false; draw(); } });
        ro.observe(root);
      }
    },
    update(c) { ctx = c; draw(); },
    unmount() {
      stopTurning();
      if (probe) cancelAnimationFrame(probe);
      if (ro) ro.disconnect();
      if (board) { try { board.unmount(); } catch { /* gone */ } }
    },
    key(e, c) {
      ctx = c;
      const close = ctx.route && ctx.route.arg;
      if (e.key === "Escape" && close) { lastFocus = close; ctx.go("#/map"); return true; }
      if (e.key === "Escape" && (focusId || mode)) { if (focusId) unfocus(true); else clearMode(); return true; }
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key) || close) return false;
      const btns = [...root.querySelectorAll(".field-hit")];
      if (!btns.length) return false;
      const i = btns.indexOf(document.activeElement);
      const d = e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 1;
      btns[(i + d + btns.length) % btns.length].focus();
      return true;
    },
  };
}
