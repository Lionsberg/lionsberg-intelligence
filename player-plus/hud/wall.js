// wall.js: the Wall, the pull plan drawn as stickies by week (the kit merge, step 3; Appendix 4's
// editable wall: "click, comment, act; every handoff drawn"). Every figure is the engine's
// (cards[].ES/EF/TF, predecessors, holder, stage); this view places and words them and computes nothing.
//
//   full   the filters (holder · stream · state) · a column per week from the data date · a sticky
//          per open card · every predecessor drawn as a line · a click opens the card in place,
//          under its sticky, with a comment and the acts; ×, Escape or the same sticky closes it,
//          and the scroll never moves
//   aside  the count of open cards this week and next, and the way to the whole wall
//
// Acts go through ctx.act (the kit's one door, with its undo hold): a comment is a `say` anchored
// to the card; done; raise a constraint; claim. A Will is a commitment, a person's own act, so it
// asks the person's confirmation before it is held.

import { h } from "./card.js";
import { ensureCss } from "./views-b.js";

const SVGNS = "http://www.w3.org/2000/svg";
const SORTS = ["resource", "information", "agreement", "time"];
const NEAR_DAYS = 5;   // a card with this many days to spare or fewer reads "near" (the RYG yellow line; lps.RYG)

/** The calendar week of a card's start, counted from the week of the earliest start shown (a column per week). */
function mondayOf(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}
/** A state written before cards carried `start`: the data date plus the early start, in calendar days (an older
    state's ES counted calendar days when its calendar did; said as an approximation only by being a fallback). */
function startOf(st, c) {
  const base = String(st.as_of || st.generated_at || "").slice(0, 10);
  if (!base || c.ES == null) return null;
  const d = new Date(base + "T12:00:00");
  d.setDate(d.getDate() + Math.floor(c.ES));
  return d.toISOString().slice(0, 10);
}
function stateOf(c) {
  if (c.TF == null) return "unscheduled";
  if (c.TF < 0) return "late";
  if (c.critical || c.TF === 0) return "critical";
  return c.TF <= NEAR_DAYS ? "near" : "free";
}

/** The wall's model, from the state alone: open cards with an early start, by week. */
export function wallModel(st, filter = {}) {
  const open = (st.cards || []).filter((c) => !["done", "released", "retracted", "declined"].includes(c.state)
    && c.ES != null && c.type !== "unit" && c.type !== "summary");   // a unit's dates are its cards': its cards stand for it
  const holders = [...new Set(open.map((c) => c.holder).filter(Boolean))].sort();
  const streams = [...new Set(open.map((c) => c.stream).filter(Boolean))].sort();
  const shown = open.filter((c) => (!filter.holder || c.holder === filter.holder)
    && (!filter.stream || c.stream === filter.stream) && (!filter.state || stateOf(c) === filter.state));
  const weeks = new Map();
  for (const c of shown.sort((a, b) => a.ES - b.ES || (a.TF ?? 1e9) - (b.TF ?? 1e9) || String(a.id).localeCompare(String(b.id)))) {
    const w = mondayOf(c.start || startOf(st, c)) || "";
    if (!weeks.has(w)) weeks.set(w, []);
    weeks.get(w).push(c);
  }
  return { open, shown, holders, streams, weeks: [...weeks.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0]))) };
}

export default function createWall() {
  let el, ctx, root, board, svg, filter = {}, openId = null, draft = "";
  ensureCss("wall.css");
  const t = (k, v) => ctx.t(k, v);
  const who = (c) => (ctx.read && ctx.read.who ? ctx.read.who(ctx.state, c.holder, c.holon) : c.holder) || t("wall.no_holder");

  function select(name, values, label) {
    const s = h("select", { "aria-label": label, onchange: (e) => { filter[name] = e.target.value || null; openId = null; draw(); } },
      h("option", { value: "" }, label), ...values.map((v) => h("option", { value: v, selected: filter[name] === v ? "" : null }, v)));
    return s;
  }

  function act(type, body, links, opts = {}) {
    if (!ctx.act) return;
    ctx.act(type, body, links || {}, null, opts);
  }

  function detail(c, note) {
    const box = h("div", { class: "wall-detail", role: "dialog", "aria-label": c.title });
    const close = h("button", { class: "wall-x", "aria-label": t("wall.close"), onclick: (e) => { e.stopPropagation(); openId = null; box.remove(); } }, "×");
    const text = h("textarea", { class: "wall-say", rows: "2", placeholder: t("wall.comment"), oninput: (e) => { draft = e.target.value; } });
    text.value = draft;   // a refresh of the state never wipes what is being typed
    const me = ctx.state && ctx.state.actor;
    const mine = !!me && c.holder === me;
    const free = !c.holder || c.state === "ready";
    const sort = h("select", { "aria-label": t("wall.constraint_sort") }, ...SORTS.map((s0) => h("option", { value: s0 }, t("wall.sort." + s0))));
    const row = (k, v) => (v == null || v === "" ? null : h("div", { class: "wall-row" }, h("span", { class: "dust" }, t(k)), h("span", {}, String(v))));
    box.append(close,
      h("p", { class: "wall-title" }, c.title),
      row("wall.f.holder", who(c)), row("wall.f.stage", c.stage), row("wall.f.float", c.TF),
      row("wall.f.before", (c.predecessors || []).length), row("wall.f.after", (c.successors || []).length),
      text,
      h("div", { class: "wall-acts" },
        h("button", { onclick: () => { const s0 = text.value.trim(); if (s0) { act("say", { text: s0 }, { anchored_to: [c.id] }); text.value = draft = ""; } } }, t("wall.act.say")),
        // done is the holder's own word; taking a card is for one nobody holds (review E, M7)
        free && !mine ? h("button", { onclick: () => act("claim", { card: c.id }) }, t("wall.act.claim")) : null,
        mine ? h("button", { onclick: () => act("done", { card: c.id }) }, t("wall.act.done")) : null,
        h("span", { class: "wall-cons" }, sort,
          h("button", { onclick: () => { const w = text.value.trim(); if (w) { act("constraint", { card: c.id, sort: sort.value, what: w }); text.value = draft = ""; } } }, t("wall.act.constraint"))),
        h("button", { onclick: () => ctx.openCard && ctx.openCard(c.id) }, t("wall.act.full"))));
    const col = note.parentElement;   // a note sits in its week's column (positioned); the box sits on the board
    box.style.left = Math.max(4, Math.min(col.offsetLeft + note.offsetLeft, board.scrollWidth - 340)) + "px";
    box.style.top = (col.offsetTop + note.offsetTop + note.offsetHeight + 4) + "px";
    return box;
  }

  function lines(m) {
    svg.textContent = "";
    svg.setAttribute("width", board.scrollWidth); svg.setAttribute("height", board.scrollHeight);
    const at = new Map([...board.querySelectorAll(".wall-note")].map((n) => [n.dataset.id, n]));
    for (const c of m.shown) {
      const to = at.get(c.id);
      for (const p of c.predecessors || []) {
        const from = at.get(p);
        if (!from || !to) continue;
        const l = document.createElementNS(SVGNS, "path");
        const fc = from.parentElement, tc = to.parentElement;
        if (fc === tc) {   // the same week: an arc along the column's left edge, never across the notes
          const x = from.offsetLeft + fc.offsetLeft, y1 = from.offsetTop + fc.offsetTop + from.offsetHeight / 2;
          const y2 = to.offsetTop + tc.offsetTop + to.offsetHeight / 2, bow = Math.min(12, 4 + Math.abs(y2 - y1) / 40);
          l.setAttribute("d", `M${x},${y1} C${x - bow},${y1} ${x - bow},${y2} ${x},${y2}`);
        } else {
          const x1 = fc.offsetLeft + from.offsetLeft + from.offsetWidth, y1 = fc.offsetTop + from.offsetTop + from.offsetHeight / 2;
          const x2 = tc.offsetLeft + to.offsetLeft, y2 = tc.offsetTop + to.offsetTop + to.offsetHeight / 2;
          l.setAttribute("d", `M${x1},${y1} C${x1 + 24},${y1} ${x2 - 24},${y2} ${x2},${y2}`);
        }
        l.setAttribute("class", "wall-link" + (c.critical ? " is-critical" : ""));
        svg.append(l);
      }
    }
  }

  function draw() {
    const keepX = board ? board.scrollLeft : 0, keepY = window.scrollY;
    root.textContent = "";
    const st = ctx.state || {};
    const m = wallModel(st, filter);
    if (!m.open.length) { root.append(h("p", { class: "dust" }, t("wall.empty"))); return; }
    if (ctx.slot === "aside" || ctx.density === "small") {
      const n0 = m.weeks.slice(0, 2).reduce((a, [, cs]) => a + cs.length, 0);
      root.append(h("p", {}, t("wall.slice", { n: n0 })), h("a", { href: "#/wall" }, t("wall.see_all")));
      return;
    }
    root.append(h("div", { class: "wall-filters" },
      select("holder", m.holders, t("wall.filter.holder")), select("stream", m.streams, t("wall.filter.stream")),
      select("state", ["late", "critical", "near", "free"], t("wall.filter.state")),
      h("span", { class: "dust" }, t("wall.count", { shown: m.shown.length, open: m.open.length }))));
    board = h("div", { class: "wall-board" });
    svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("class", "wall-lines"); svg.setAttribute("aria-hidden", "true");
    board.append(svg);
    for (const [w, cs] of m.weeks) {
      const thisMon = mondayOf((ctx.state && (ctx.state.as_of || ctx.state.generated_at) || new Date().toISOString()).slice(0, 10));
      const n0 = w ? Math.round((new Date(w + "T12:00:00") - new Date(thisMon + "T12:00:00")) / 864e5 / 7) : null;
      const col = h("div", { class: "wall-col" }, h("h3", { class: "eyebrow" },
        n0 == null ? t("wall.week.none") : n0 <= 0 ? t("wall.week.this") : t("wall.week.n", { n: n0 })));
      for (const c of cs) {
        const n = h("button", { class: `wall-note is-${stateOf(c)}`, dataset: { id: c.id }, title: c.title },
          h("span", { class: "wall-note-title" }, c.title), h("span", { class: "dust" }, who(c) + " · " + (c.TF == null ? "" : (ctx.fmt && ctx.fmt.spare ? ctx.fmt.spare(c.TF) : t("wall.float", { d: Math.round(c.TF) })))));
        n.addEventListener("click", () => {
          const was = openId === c.id;
          if (!was) draft = "";
          board.querySelectorAll(".wall-detail").forEach((d) => d.remove());
          openId = was ? null : c.id;
          if (!was) board.append(detail(c, n));
        });
        col.append(n);
      }
      board.append(col);
    }
    root.append(board);
    requestAnimationFrame(() => { lines(m); board.scrollLeft = keepX; window.scrollTo(window.scrollX, keepY);
      if (openId) { const n = board.querySelector(`.wall-note[data-id="${CSS.escape(openId)}"]`); const c = m.shown.find((x) => x.id === openId); if (n && c) board.append(detail(c, n)); } });
  }

  const onKey = (e) => { if (e.key === "Escape" && openId) { openId = null; board && board.querySelectorAll(".wall-detail").forEach((d) => d.remove()); } };

  return {
    mount(container, c) { el = container; ctx = c; root = h("div", { class: "wall" }); el.append(root); document.addEventListener("keydown", onKey); draw(); },
    update(c) { ctx = c; draw(); },
    unmount() { document.removeEventListener("keydown", onKey); },
  };
}
