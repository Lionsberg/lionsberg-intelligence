// sightings.js: the living map (STATE.md `map`, `agreements`, `subscriptions`; the H2 brief). One view,
// three panels, in the Wall's idiom. Every figure is the engine's; this view places and words them and
// computes nothing the state lacks. It only reads: nothing here writes, sends or sounds, and every act
// goes through the Deal as it always has.
//
//   the map         places as rows, the kinds as columns (state.map.kinds, then any other kind the record
//                   holds); each cell the count of sightings there and their weight, an open pain marked.
//                   A tap on a cell lists its sightings under the table, each with its lifecycle state and
//                   its paper line; the same tap closes it.
//   agreements      one row per Agreement: with which holon, its state, what crosses, each cadence in
//                   words, and its clauses with their status
//   what I hear     one row per subscription: the source, its signals, each cadence in words, the surface,
//                   the bell, and whether a pull is due or overdue (state.subscriptions.due)
//
//   aside · small   the counts, and the way to the whole view
//
// Every word comes from strings.json (keys `smap.*`, `sight.kind.*`); none is written here.

import { h } from "./card.js";
import { ensureCss, homeId } from "./views-b.js";

const VIEW = "sightings";
const EVERY = "*";                  // agreement.EVERY_SIGNAL: one cadence for every signal
const PAIN = "pain";                // the kind whose open sightings are marked on the map
// Seconds as a person says a cadence: the same steps as subscriptions.words (a season is 90 days).
const SEASON_S = 7776000, DAY_S = 86400, HOUR_S = 3600, MINUTE_S = 60;

const list = (v) => (Array.isArray(v) ? v : []);
const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : {});
const str = (v) => (typeof v === "string" ? v.normalize() : "");
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** The map's model, from the state alone: the columns, and each place with its cells, heaviest first. */
export function mapModel(st) {
  const m = obj(st && st.map);
  const byPlace = obj(m.by_place);
  const kinds = list(m.kinds).map(str).filter(Boolean);
  const seen = new Set(kinds);
  const extra = new Set(Object.keys(obj(m.by_kind)).map(str).filter((k) => k && !seen.has(k)));
  const places = Object.keys(byPlace).map((place) => {
    const cells = {};
    let weight = 0, n = 0;
    for (const [k0, rows0] of Object.entries(obj(byPlace[place]))) {
      const k = str(k0);
      if (!k) continue;
      if (!seen.has(k)) extra.add(k);
      const rows = list(rows0).filter((r) => r && typeof r === "object");
      const w = rows.reduce((a, r) => a + (num(r.weight) == null ? 1 : r.weight), 0);
      cells[k] = { rows, n: rows.length, weight: w, pain: k === PAIN && rows.some((r) => r.open === true) };
      weight += w; n += rows.length;
    }
    return { place: str(place), cells, weight, n };
  }).filter((p) => p.place && p.n)
    .sort((a, b) => b.weight - a.weight || b.n - a.n || a.place.localeCompare(b.place));
  return { columns: kinds.concat([...extra].sort()), places,
    open: num(m.open) || 0, pains: num(m.pains_open) || 0, asOf: obj(m.as_of).newest || null,
    noPlace: str(m.no_place) || null, noKind: str(m.no_kind) || null };
}

export default function createSightings() {
  let el, ctx, root, openCell = null;
  ensureCss(VIEW + ".css");
  const t = (k, v) => ctx.t(k, v);
  /** A word from a family of keys, or the value itself when the family has no word for it. */
  const word = (prefix, v) => { const s = t(prefix + v); return typeof s === "string" && !s.startsWith("[") ? s : String(v); };
  const n = (x) => (ctx.fmt && ctx.fmt.number ? ctx.fmt.number(x, true) : String(x));
  const holonName = (id) => (ctx.read && ctx.read.holonName ? ctx.read.holonName(ctx.state, id) : "")
    || (ctx.fmt && ctx.fmt.short ? ctx.fmt.short(id) : str(id));

  function cadence(s) {
    s = num(s);
    if (s == null || s <= 0 || !Number.isInteger(s)) return t("smap.cadence.none");
    if (s === SEASON_S) return t("smap.cadence.season");
    if (s % DAY_S === 0) return s === DAY_S ? t("smap.cadence.day") : t("smap.cadence.days", { n: n(s / DAY_S) });
    if (s % HOUR_S === 0) return s === HOUR_S ? t("smap.cadence.hour") : t("smap.cadence.hours", { n: n(s / HOUR_S) });
    if (s % MINUTE_S === 0) return s === MINUTE_S ? t("smap.cadence.minute") : t("smap.cadence.minutes", { n: n(s / MINUTE_S) });
    return s === 1 ? t("smap.cadence.second") : t("smap.cadence.seconds", { n: n(s) });
  }
  const cadences = (cad) => Object.keys(obj(cad)).sort().map((sig) =>
    t("smap.cadence.of", { signal: sig === EVERY ? t("smap.every_signal") : word("smap.signal.", sig), cadence: cadence(cad[sig]) }));
  const joined = (xs) => (xs.length ? xs.join(t("smap.sep")) : t("smap.none"));
  // the engine's names for a sighting with no place or no kind (state.map.no_place, no_kind), said in words
  let sentinel = { place: null, kind: null };
  const kindWord = (k) => (k && k === sentinel.kind ? t("smap.no_kind") : word("sight.kind.", k));
  const placeWord = (p) => (p && p === sentinel.place ? t("smap.no_place") : p);
  const panel = (title, ...kids) => h("section", { class: "smap-panel", "aria-label": title }, h("h3", { class: "eyebrow" }, title), ...kids);

  // ---------------------------------------------------------------- the map

  function sightingsOf(cell, place, kind) {
    const head = t("smap.map.list", { kind: kindWord(kind), place: placeWord(place) });
    return h("div", { class: "smap-list", role: "region", "aria-label": head },
      h("p", { class: "smap-list-head" }, head),
      h("ul", null, ...cell.rows.map((r) => h("li", { class: "smap-sighting" + (r.open === true ? "" : " is-ended") },
        h("span", { class: "smap-life" }, (str(r.life) ? word("smap.life.", str(r.life)) : t("smap.life.seen"))),
        num(r.weight) > 1 ? h("span", { class: "dust" }, t("smap.map.weight", { w: n(r.weight) })) : null,
        r.needs_response === true ? h("span", { class: "smap-wait" }, t("smap.map.needs_response")) : null,
        // the paper line (kind · where · what was seen, sightings.paper), its kind and place in words
        h("span", { class: "smap-paper" }, [kindWord(str(r.kind) || sentinel.kind), placeWord(str(r.where) || sentinel.place),
          str(r.text)].filter(Boolean).join(t("smap.sep")))))));
  }

  function theMap(m) {
    if (!m.places.length) return panel(t("smap.map.title"), h("p", { class: "dust" }, t("smap.map.empty")));
    const head = h("tr", null, h("th", { scope: "col", class: "smap-place" }, t("smap.map.place")),
      ...m.columns.map((k) => h("th", { scope: "col" }, kindWord(k))));
    let listed = null;
    const body = m.places.map((p) => h("tr", null, h("th", { scope: "row", class: "smap-place" }, placeWord(p.place)),
      ...m.columns.map((k) => {
        const c = p.cells[k];
        if (!c || !c.n) return h("td", { class: "smap-cell is-empty" });
        const id = p.place + "\u0000" + k;
        const on = openCell === id;
        if (on) listed = sightingsOf(c, p.place, k);
        return h("td", { class: "smap-cell" + (c.pain ? " is-pain" : "") + (on ? " is-open" : "") },
          h("button", { class: "smap-count", "aria-pressed": String(on),
            "aria-label": t(c.pain ? "smap.map.cell_pain" : "smap.map.cell", { n: c.n, w: c.weight, kind: kindWord(k), place: placeWord(p.place) }),
            onclick: () => { openCell = on ? null : id; draw(); } },
          String(c.n), c.weight > c.n ? h("small", null, t("smap.map.weight", { w: c.weight })) : null));
      })));
    return panel(t("smap.map.title"),
      h("p", { class: "dust" }, t(m.pains === 1 ? "smap.map.totals_one_pain" : "smap.map.totals", { open: n(m.open), pains: n(m.pains) })),
      h("div", { class: "smap-scroll" }, h("table", { class: "smap-table" }, h("thead", null, head), h("tbody", null, ...body))),
      listed);
  }

  // ---------------------------------------------------------------- agreements

  function agreements(st) {
    const rows = list(obj(st.agreements).rows).filter((r) => r && typeof r === "object");
    if (!rows.length) return panel(t("smap.ag.title"), h("p", { class: "dust" }, t("smap.ag.empty")));
    const home = homeId(st);
    const titleOf = (id) => { const c = list(st.cards).find((x) => x && x.id === id); return (c && str(c.title)) || t("smap.ag.clause_untitled"); };
    return panel(t("smap.ag.title"), h("ul", { class: "smap-rows" }, ...rows.map((r) => {
      const others = list(r.sides).map(str).filter((x) => x && x !== home);
      const withWhom = (others.length ? others : [str(r.with)].filter(Boolean)).map(holonName);
      const clauses = list(r.clauses).filter((c) => c && typeof c === "object");
      return h("li", { class: "smap-row" + (r.live === true ? " is-live" : "") },
        h("p", { class: "smap-row-head" }, h("span", null, t("smap.ag.with", { who: joined(withWhom) })),
          h("span", { class: "smap-state" }, (str(r.state) ? word("smap.ag.state.", str(r.state)) : t("smap.ag.state.proposed")))),
        h("p", { class: "dust" }, t("smap.ag.crosses", { what: joined(list(r.crosses).map(str).filter(Boolean).map((x) => word("smap.signal.", x))) })),
        h("p", { class: "dust" }, t("smap.ag.cadence", { cadence: joined(cadences(r.cadence)) })),
        clauses.length
          ? h("ul", { class: "smap-clauses", "aria-label": t("smap.ag.clauses") }, ...clauses.map((c) => h("li", null,
            h("span", null, titleOf(c.card)), h("span", { class: "smap-state" }, (str(c.status) ? word("smap.clause.", str(c.status)) : t("smap.clause.open"))),
            c.by && ctx.fmt && ctx.fmt.by ? h("span", { class: "dust" }, ctx.fmt.by(c.by)) : null)))
          : h("p", { class: "dust" }, t("smap.ag.no_clauses")),
        h("p", { class: "dust smap-note" }, t(r.live === true ? "smap.ag.live" : "smap.ag.not_live")));
    })));
  }

  // ---------------------------------------------------------------- what I hear

  function hearing(st) {
    const s = obj(st.subscriptions);
    const rows = list(s.rows).filter((r) => r && typeof r === "object" && str(r.source));
    if (!rows.length) return panel(t("smap.hear.title"), h("p", { class: "dust" }, t("smap.hear.empty")));
    const due = list(s.due).filter((d) => d && typeof d === "object");
    return panel(t("smap.hear.title"), h("ul", { class: "smap-rows" }, ...rows.map((r) => {
      const mine = due.filter((d) => str(d.source).toLowerCase() === str(r.source).toLowerCase());
      const late = mine.filter((d) => num(d.overdue_s) > 0).length;
      const when = late ? t("smap.hear.overdue", { n: n(late) }) : mine.length ? t("smap.hear.due", { n: n(mine.length) }) : t("smap.hear.not_due");
      const bell = list(r.bell).map(str).filter(Boolean).map((k) => { const b = word("smap.bell.", k); return b === k ? kindWord(k) : b; });
      return h("li", { class: "smap-row" + (late ? " is-overdue" : mine.length ? " is-due" : "") },
        h("p", { class: "smap-row-head" }, h("span", null, holonName(str(r.source))), h("span", { class: "smap-state" }, when)),
        h("p", { class: "dust" }, t("smap.hear.signals", { what: joined(list(r.signals).map(str).filter(Boolean).map((x) => word("smap.signal.", x))) })),
        h("p", { class: "dust" }, t("smap.hear.cadence", { cadence: joined(cadences(r.cadence)) })),
        h("p", { class: "dust" }, t("smap.hear.surface", { surface: word("smap.surface.", str(r.surface)) }),
          t("smap.sep"), bell.length ? t("smap.hear.bell", { what: joined(bell) }) : t("smap.hear.no_bell")),
        str(r.basis) ? h("p", { class: "dust" }, word("smap.basis.", str(r.basis))) : null);
    })));
  }

  // ---------------------------------------------------------------- the whole

  function draw() {
    root.textContent = "";
    const st = ctx.state || {};
    const m = mapModel(st);
    const ag = list(obj(st.agreements).rows).length, hear = list(obj(st.subscriptions).rows).length;
    sentinel = { place: m.noPlace, kind: m.noKind };
    if (ctx.slot === "aside" || ctx.density === "small") {
      root.append(h("p", null, t("smap.slice", { open: n(m.open), pains: n(m.pains), agreements: n(ag), heard: n(hear) })),
        h("a", { href: "#/" + VIEW }, t("smap.see_all")));
      return;
    }
    if (openCell && !m.places.some((p) => m.columns.some((k) => p.cells[k] && openCell === p.place + "\u0000" + k))) openCell = null;
    root.append(h("p", { class: "smap-line" }, t("smap.title_line")), theMap(m), agreements(st), hearing(st));
  }

  return {
    mount(container, c) { el = container; ctx = c; root = h("div", { class: "smap" }); el.append(root); draw(); },
    update(c) { ctx = c; draw(); },
    unmount() { openCell = null; },
  };
}
