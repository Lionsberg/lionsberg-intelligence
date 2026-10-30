// chain.js: the Chain (DESIGN-THE-BAR §2).
// The person's goal: will we make it, what is eating the buffer, and what one thing moves the
// whole. Every figure is the engine's (buffers, path, cards[].ES/LS/TF, the pace-setter); this
// view only places and words them, and computes nothing the state does not already say.
//
//   full   the one breath · the fever chart (with its trail) · the one thing · the road across
//          every house held (the buffer, the pace-setter and the fixed stones on it) · the fold
//          by stream (what survives of the Board) · the pencil sheet for paper
//   aside  the slice: the one breath, the zone's word, the one thing in a line
//   map    the fold by stream for one house (the Map's "open its board")
//
// Salience follows what eats the buffer: Calm lights nothing; Watch sets the point and the one
// thing in full ink; Act alone spends the warning gold. The zone's word is always printed.

import { h, spareDays } from "./card.js";
import { ensureCss, ms, asOfWords, DONE } from "./views-b.js";
import { store } from "./state.js";

const SVGNS = "http://www.w3.org/2000/svg";
function s(tag, attrs, ...kids) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null && v !== false) el.setAttribute(k, v);
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  return el;
}

const ZONES = { calm: "calm", green: "calm", watch: "watch", amber: "watch", yellow: "watch", act: "act", red: "act" };
const RANK = { unknown: 0, calm: 1, watch: 2, act: 3 };
const zoneOf = (b) => (b && ZONES[String(b.signal || "").toLowerCase()]) || "unknown";
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lowerThe = (x) => (/^(The|A|An) /.test(x || "") ? x[0].toLowerCase() + x.slice(1) : x || "");
const upperFirst = (x) => (x ? x[0].toUpperCase() + x.slice(1) : "");

/** The share of the buffer used: the engine's consumed_share, else its consumed over its size. */
function usedShare(b) {
  if (!b) return null;
  if (b.consumed_share != null) return b.consumed_share;
  return b.size_days && b.consumed_days != null ? b.consumed_days / b.size_days : null;
}

/** How many whole days late a station is: its engine days to spare (spareDays) when negative,
    rounded once, else 0. The headline and the milestone station both call this, so the two can
    never say different numbers (never "one day" against "two days late"). */
export function milestoneLate(item) {
  return item && item.spare != null && item.spare < 0 ? Math.round(-item.spare) : 0;
}

/** Everything the view shows, read from the state in one place. Nothing here invents a figure. */
export function chainModel(ctx) {
  const st = ctx.state || {};
  const by = new Map((st.cards || []).map((c) => [c.id, c]));
  const path = st.path || {};
  const ids = [...new Set([...(path.system || []), ...(path.critical || [])])];
  const cards = ids.map((id) => by.get(id)).filter(Boolean);
  if (!cards.length) return { empty: true, zone: "unknown" };
  const sys = new Set(path.system || []);
  cards.sort((a, b) => (a.ES ?? 1e9) - (b.ES ?? 1e9) || (a.EF ?? 1e9) - (b.EF ?? 1e9)
    || (a.kind === "milestone") - (b.kind === "milestone") || String(a.title).localeCompare(String(b.title)));

  // the milestone the whole steers by: the last milestone on the system path, else on the road
  const ms0 = [...cards].reverse().find((c) => c.kind === "milestone" && sys.has(c.id))
    || [...cards].reverse().find((c) => c.kind === "milestone") || null;
  const buffers = Array.isArray(st.buffers) ? st.buffers : [];
  const main = (ms0 && buffers.find((b) => b.milestone === ms0.id))
    || [...buffers].sort((a, b) => RANK[zoneOf(b)] - RANK[zoneOf(a)])[0] || null;
  const milestone = (main && by.get(main.milestone)) || ms0;
  const zone = zoneOf(main);

  // the stations, with the stones placed before the card they hold back
  const ext = Array.isArray(path.external) ? path.external : [];
  const pace = (main && main.drum && main.drum.actor) || (path.drum && path.drum.actor) || (st.drum && st.drum.actor) || null;
  const items = [];
  const placed = new Set();
  for (const c of cards) {
    for (const x of ext.filter((e) => e.before === c.id && !placed.has(e.id))) {
      placed.add(x.id);
      items.push({ type: "stone", id: x.id, title: x.title, house: x.house, date: x.date, holon: null, stream: null });
    }
    for (const p of (c.predecessors || []).filter((p0) => !by.has(p0) && !placed.has(p0))) {
      placed.add(p);
      items.push({ type: "stone", id: p, title: null, missing: true, holon: null, stream: null });
    }
    // the buffer sits on the road just before the milestone it protects
    for (const b of buffers.filter((b0) => b0.milestone === c.id)) {
      items.push({ type: "buffer", id: "buf-" + c.id, buffer: b, holon: c.holon, stream: c.stream || "", zone: zoneOf(b) });
    }
    const done = DONE.has(c.state) || c.stage === "did";
    // answered on this device and not yet folded by the engine: never asked for again
    const answered = !done && !!(store.answered && store.answered.has(c.id));
    items.push({ type: "station", id: c.id, card: c, title: c.title, holon: c.holon, stream: c.stream || "",
      done, answered, milestone: c.kind === "milestone", mine: c.holder === st.actor, pace: !!pace && c.holder === pace && !done && c.kind !== "milestone",
      spare: done ? null : spareDays(ctx, c) });
  }
  for (const x of ext.filter((e) => !placed.has(e.id))) items.push({ type: "stone", id: x.id, title: x.title, house: x.house, date: x.date, holon: null, stream: null });

  // the one thing: the live card on the road with the least days to spare (work before milestones)
  const live = items.filter((i) => i.type === "station" && !i.done && !i.answered);
  const pick = (xs) => [...xs].sort((a, b) => (a.spare ?? 1e9) - (b.spare ?? 1e9) || (a.card.ES ?? 1e9) - (b.card.ES ?? 1e9))[0] || null;
  const one = pick(live.filter((i) => !i.milestone)) || pick(live);
  const mine = live.filter((i) => i.mine && !i.milestone);
  // the margin: the one computation the sentence, the word and every "slack" phrase derive from
  const size = main && main.size_days != null ? Math.round(main.size_days) : null;
  const used = main && main.consumed_days != null ? Math.round(main.consumed_days) : null;
  const margin = size != null && used != null ? { size, used: Math.min(used, size), left: Math.max(0, size - used), untouched: used <= 0 } : null;
  const msItem = milestone ? items.find((i) => i.type === "station" && i.id === milestone.id) || null : null;
  const late = milestoneLate(msItem);
  return { empty: false, items, milestone, msItem, late, main, zone, one, mine, pace, margin, others: buffers.filter((b) => b !== main) };
}

export default function createChain(opts = {}) {
  let el, ctx, root, m0 = null, folded = !!opts.fold, anim = 0;
  ensureCss("chain.css");

  const t = (k, v) => ctx.t(k, v);
  const open = (id) => { ctx.select(id); ctx.openCard(id); };
  const houseName = (id) => ctx.read.holonName(ctx.state, id) || "";
  const who = (c) => ctx.read.who(ctx.state, c.holder, c.holon);
  /** A station's slack in words, from the same margin as the sentence: a card on the road with
      no float of its own is protected by the spare days when any are left, never "no days to spare"
      beside a calm chart. */
  const spareWords = (i) => {
    if (i.answered) return t("chain.road.answered");
    if (i.spare == null) return null;
    if (Math.round(i.spare) === 0 && m0 && m0.margin && m0.margin.left > 0) return t("chain.no_slack");
    return ctx.fmt.spare(i.spare);
  };
  const dayMonth = (x) => { const d = ctx.fmt.date(x); return d ? d.toLocaleDateString(undefined, { day: "numeric", month: "long" }) : ""; };
  const roughDone = (x) => (x == null ? null : t("chain.done." + ["none", "quarter", "half", "three_quarters", "all"][Math.round(clamp(x, 0, 1) * 4)]));
  const eating = (m) => m.zone === "watch" || m.zone === "act";

  // ---------------------------------------------------------------- the one breath

  function verdict(m) {
    const ms0 = m.milestone;
    const name = ms0 ? ms0.title : upperFirst(t("chain.the_whole"));
    const fin = ctx.state.path && ctx.state.path.finish;
    const when = ms0 && ms0.by ? ctx.fmt.by(ms0.by) : fin ? ctx.fmt.by(fin) : null;
    const g = m.margin, n = (x) => ctx.fmt.number(x, true);
    // in Act the headline says how late the milestone will be, from milestoneLate(): the same
    // number its station on the road prints
    const one = m.one;
    if (m.zone === "act" && one && when) {
      const day = when.replace(/^by /, "");
      const days = (x) => (x === 1 ? t("chain.one_day") : t("chain.n_days", { n: n(x) }));
      return m.late > 0 ? t("chain.verdict.act_over", { milestone: name, day, over: days(m.late), one: one.card.title })
        : t("chain.verdict.act_only_if", { milestone: name, by: when, one: one.card.title });
    }
    const key = m.zone === "calm" && g ? (g.untouched ? "calm_untouched" : "calm_left") : m.zone;
    return t("chain.verdict." + key + (when ? "" : "_undated"), { milestone: name, by: when || "", size: g ? n(g.size) : "", left: g ? n(g.left) : "" });
  }

  /** The second line: what eats the margin; or, when calm and the next step has no slack of its
      own, that the spare days are what protect it. */
  function secondLine(m) {
    if (eating(m)) return t("chain.eats." + m.zone);
    const i = m.one;
    if (m.zone === "calm" && i && i.spare != null && Math.round(i.spare) === 0 && m.margin && m.margin.left > 0) return t("chain.calm_no_slack", { title: i.card.title });
    return null;
  }

  // ---------------------------------------------------------------- the fever chart

  /** Buffer used (up) against chain done (across). The two hairlines are the engine's own rule:
      Calm at or under the diagonal, Watch within a third above it, Act beyond. */
  function fever(m) {
    const b = m.main;
    const L = 12, R = 102, T = 4, B = 90;          // the plot's square in a 104 x 100 frame
    const X = (x) => L + clamp(x, 0, 1) * (R - L);
    const Y = (y) => B - (clamp(y, 0, 1.1) / 1.1) * (B - T);
    const used = usedShare(b), done = b.chain_complete;
    const svg = s("svg", { viewBox: "0 0 104 100", class: "fever-svg", "aria-hidden": "true", focusable: "false" });
    svg.append(s("path", { d: `M${X(0)} ${Y(1.1)} V${Y(0)} H${X(1)}`, class: "fever-axis" }));
    svg.append(s("line", { x1: X(0), y1: Y(0), x2: X(1), y2: Y(1), class: "fever-rule" }));
    svg.append(s("line", { x1: X(0), y1: Y(1 / 3), x2: X(0.7667), y2: Y(1.1), class: "fever-rule" }));
    svg.append(s("text", { x: X(0.97), y: Y(0.05), class: "fever-region", "text-anchor": "end" }, t("chain.zone.calm")));
    svg.append(s("text", { x: X(0.97), y: Y(0.99), class: "fever-region", "text-anchor": "end" }, t("chain.zone.watch")));
    svg.append(s("text", { x: X(0.03), y: Y(1.0), class: "fever-region" }, t("chain.zone.act")));
    svg.append(s("text", { x: X(0), y: 98, class: "fever-tick" }, t("chain.chart.begun")));
    svg.append(s("text", { x: X(1), y: 98, class: "fever-tick", "text-anchor": "end" }, t("chain.chart.done")));
    svg.append(s("text", { x: X(0.5), y: 98, class: "fever-tick", "text-anchor": "middle" }, t("chain.chart.x")));
    svg.append(s("text", { x: 6, y: Y(0.55), class: "fever-tick", "text-anchor": "middle", transform: `rotate(-90 6 ${Y(0.55)})` }, t("chain.chart.y")));
    // the other buffers held, small and quiet, each named on a hold
    for (const o of m.others) {
      const u = usedShare(o), z = zoneOf(o);
      if (u == null || o.chain_complete == null || z === "unknown") continue;
      const name = o.title || (ctx.read.card(ctx.state, o.milestone) || {}).title || "";
      svg.append(s("g", { class: "fever-other" }, s("title", null, t("chain.chart.other", { milestone: name, zone: t("chain.zone." + z) })),
        s("circle", { cx: X(o.chain_complete), cy: Y(u), r: 1.5 }),
        s("text", { x: X(o.chain_complete) + (o.chain_complete < 0.6 ? 2.6 : -2.6), y: Y(u) - 2, class: "fever-tick fever-other-name", "text-anchor": o.chain_complete < 0.6 ? "start" : "end" }, name)));
    }
    // the trail: where the point stood over the past week, oldest first, ending at now
    const trail = Array.isArray(b.trail) ? b.trail.filter((p) => p && p.consumed_share != null && p.chain_complete != null) : [];
    if (trail.length) {
      const pts = trail.concat([{ consumed_share: used, chain_complete: done }]);
      svg.append(s("polyline", { points: pts.map((p) => `${X(p.chain_complete)},${Y(p.consumed_share)}`).join(" "), class: "fever-trail" }));
      const ago = ctx.fmt.now().getTime() - 7 * 86400000;
      const near = [...trail].sort((a, c) => Math.abs(new Date(a.ts) - ago) - Math.abs(new Date(c.ts) - ago))[0];
      svg.append(s("circle", { cx: X(near.chain_complete), cy: Y(near.consumed_share), r: 1.6, class: "fever-then" }));
      const right = near.chain_complete < 0.6;
      svg.append(s("text", { x: X(near.chain_complete) + (right ? 3 : -3), y: Y(near.consumed_share) + 1.2, class: "fever-tick", "text-anchor": right ? "start" : "end" }, t("chain.chart.week_ago")));
    }
    svg.append(s("circle", { cx: X(done), cy: Y(used), r: 2.6, class: "fever-now" }));
    return svg;
  }

  function chartWords(m) {
    const b = m.main;
    const parts = [];
    const g = m.margin;
    if (g) parts.push(g.untouched ? t("chain.chart.untouched", { size: ctx.fmt.number(g.size, true) })
      : g.left <= 0 ? t("chain.chart.spent", { size: ctx.fmt.number(g.size, true) })
      : t("chain.chart.used", { used: ctx.fmt.number(g.used, true), size: ctx.fmt.number(g.size, true) }));
    const d = roughDone(b.chain_complete);
    if (d) parts.push(t("chain.chart.chain", { done: d }));
    return parts.join("; ");
  }

  function asOfLine(holonId) {
    const x = ctx.read.holon(ctx.state, holonId);
    if (!x) return null;
    const stale = ctx.offline || ctx.fmt.freshness(x.as_of && x.as_of.ts) === "older";
    return h("p", { class: "chain-asof dust" }, t("chain.asof", { house: x.name, asof: asOfWords(ctx, x) }), stale ? " " + t("chain.behind") : null);
  }

  const charted = (m) => !!m.main && usedShare(m.main) != null && m.main.chain_complete != null && m.zone !== "unknown";

  function chartBlock(m) {
    if (!charted(m)) return null;
    const zword = t("chain.zone." + m.zone);
    const words = chartWords(m);
    return h("figure", { class: "fever" },
      h("div", { class: "fever-plot", role: "img", "aria-label": t("chain.chart.label", { milestone: (m.milestone && m.milestone.title) || "", zone: zword, words }) }, fever(m)),
      h("figcaption", { class: "fever-caption" },
        h("p", { class: "fever-word" }, zword),
        h("p", { class: "fever-words" }, upperFirst(words) + "."),
        asOfLine(m.main.holon)));
  }

  // ---------------------------------------------------------------- the one thing

  function oneThing(m, compact) {
    const i = m.one;
    if (!i) return null;
    const c = i.card;
    const target = m.milestone && m.milestone.id !== c.id ? lowerThe(m.milestone.title) : t("chain.the_whole");
    const line = h("p", { class: "one-line voice" }, t("chain.one.line", { title: c.title, milestone: target }));
    if (compact) return h("div", { class: "one is-compact" }, line);
    const tail = [c.by && !(i.spare < 0) ? ctx.fmt.by(c.by) : null, spareWords(i)].filter(Boolean).join(", ");
    const whose = i.mine ? t("chain.one.yours", { tail }) : t("chain.one.theirs", { who: upperFirst(who(c)), house: houseName(c.holon), tail });
    const label = t(eating(m) ? "chain.one.eyebrow_eating" : "chain.one.eyebrow");
    return h("section", { class: "one", "aria-label": label },
      h("p", { class: "eyebrow one-eyebrow" }, label),
      line,
      h("p", { class: "one-whose" }, whose),
      h("button", { class: "one-act", onclick: () => open(c.id) }, t("chain.one.open")),
      mineLine(m));
  }

  /** "Is it me": what of the wearer's is on the road, unless the one thing already said so. */
  function mineLine(m) {
    const xs = m.mine.filter((i) => i !== m.one);
    const oneMine = !!(m.one && m.one.mine);
    if (!xs.length) return oneMine ? null : h("p", { class: "one-mine dust" }, t("chain.mine.none"));
    const first = xs[0];
    const key = (oneMine ? "chain.mine.also_" : "chain.mine.") + (xs.length === 1 ? "one" : "many");
    return h("p", { class: "one-mine" }, t(key, { title: first.title, by: first.card.by ? ctx.fmt.by(first.card.by) : "", n: ctx.fmt.number(xs.length, true) }));
  }

  // ---------------------------------------------------------------- the road

  function station(i, prevHouse) {
    if (i.type === "stone") {
      const words = i.missing ? t("chain.road.not_here") : t("chain.road.stone", { date: dayMonth(i.date), house: lowerThe(i.house || "") });
      return h("li", { class: "road-item road-stone", dataset: { node: i.id } },
        h("span", { class: "road-mark", "aria-hidden": "true" }),
        h("p", { class: "road-title" }, i.title || t("chain.road.unknown_title")),
        h("p", { class: "road-meta dust" }, words));
    }
    if (i.type === "buffer") {
      const b = i.buffer, share = clamp(usedShare(b) ?? 0, 0, 1);
      const words = [i.zone === "unknown" ? null : t("chain.zone." + i.zone),
        b.size_days != null && b.consumed_days != null
          ? (Math.round(b.consumed_days) <= 0 ? t("chain.chart.untouched", { size: ctx.fmt.number(Math.round(b.size_days), true) })
            : Math.round(b.consumed_days) >= Math.round(b.size_days) ? t("chain.chart.spent", { size: ctx.fmt.number(Math.round(b.size_days), true) })
            : t("chain.road.buffer", { used: ctx.fmt.number(Math.round(b.consumed_days), true), size: ctx.fmt.number(Math.round(b.size_days), true) })) : null];
      return h("li", { class: `road-item road-buffer zone-${i.zone}`, style: `--grow:${clamp(Math.round(b.size_days || 1), 1, 6)}` },
        h("span", { class: "road-band", "aria-hidden": "true" }, h("span", { class: "road-band-used", style: `--used:${Math.round(share * 100)}%` })),
        h("p", { class: "road-meta" }, words.filter(Boolean).join(" · ")));
    }
    const c = i.card;
    const x = ctx.read.holon(ctx.state, c.holon);
    const stale = x && ctx.fmt.freshness(x.as_of && x.as_of.ts) === "older";
    const lateBy = milestoneLate(i);
    const meta = i.done ? t("chain.road.done")
      : i.milestone ? (lateBy > 0 ? ctx.fmt.spare(-lateBy) : [c.by ? ctx.fmt.by(c.by) : null, spareWords(i)].filter(Boolean).join(" · "))
      : [i.mine ? t("app.you") : who(c), spareWords(i)].filter(Boolean).join(" · ");
    const isEating = m0 && m0.one === i && eating(m0);
    const cls = ["road-item", "road-station", i.done && "is-done", i.milestone && "is-milestone", i.mine && "is-mine", isEating && "is-eating"].filter(Boolean).join(" ");
    return h("li", { class: cls, dataset: { node: c.id, late: String(lateBy) } },
      h("span", { class: "road-mark", "aria-hidden": "true" }),
      c.holon !== prevHouse ? h("p", { class: "road-house eyebrow" }, houseName(c.holon), stale ? h("span", { class: "dust" }, " · " + asOfWords(ctx, x)) : null) : null,
      h("button", { class: "road-title", onclick: () => open(c.id) }, c.title),
      h("p", { class: "road-meta dust" }, meta),
      i.pace ? h("p", { class: "road-pace dust" }, t("chain.road.pace")) : null);
  }

  function road(m) {
    const ol = h("ol", { class: "road", "aria-label": t("chain.road.label", { milestone: m.milestone ? m.milestone.title : "" }) });
    let prev = null;
    for (const i of m.items) {
      ol.append(station(i, prev));
      if (i.type === "station") prev = i.card.holon;
    }
    return ol;
  }

  /** The fold by stream: the same stations in lanes, one per stream and house, the order kept. */
  function fold(m, onlyHouse) {
    const lanes = new Map();
    const n = m.items.length;
    m.items.forEach((i, k) => {
      if (onlyHouse && i.holon !== onlyHouse) return;
      const key = i.type === "stone" ? "_stones" : `${i.holon || ""}|${i.stream || ""}`;
      if (!lanes.has(key)) lanes.set(key, []);
      lanes.get(key).push([i, k]);
    });
    const wrap = h("div", { class: "fold", style: `--cols:${n}` });
    if (!lanes.size) { wrap.append(h("p", { class: "dust" }, t("chain.fold.none", { house: houseName(onlyHouse) }))); return wrap; }
    for (const [key, xs] of lanes) {
      const [hid, stream] = key.split("|");
      const name = key === "_stones" ? t("chain.fold.stones") : `${stream || t("chain.fold.no_stream")} · ${houseName(hid)}`;
      const row = h("ol", { class: "fold-row", "aria-label": name });
      for (const [i, k] of xs) {
        const li = station(i, i.holon);
        const hl = li.querySelector(".road-house");
        if (hl) hl.remove();
        li.style.setProperty("--col", String(k + 1));
        li.prepend(h("span", { class: "fold-step dust" }, t("chain.fold.step", { n: ctx.fmt.number(k + 1, true), of: ctx.fmt.number(n, true) })));
        row.append(li);
      }
      wrap.append(h("section", { class: "fold-lane" }, h("h4", { class: "fold-name eyebrow" }, name), row));
    }
    return wrap;
  }

  // ---------------------------------------------------------------- the pencil sheet (paper)

  function pencil(m) {
    const by = new Map((ctx.state.cards || []).map((c) => [c.id, c]));
    const day = (x) => {
      if (x == null) return "";
      const n = Math.round(x);
      return n < 0 ? t(n === -1 ? "chain.day_before_one" : "chain.day_before", { n: ctx.fmt.number(-n, true) }) : t("chain.day", { n: String(n) });
    };
    const rows = m.items.filter((i) => i.type === "station");
    const caption = [charted(m) ? t("chain.pencil_point", { zone: t("chain.zone." + m.zone), words: upperFirst(chartWords(m)) }) : null,
      m.main && ctx.read.holon(ctx.state, m.main.holon) ? t("chain.asof", { house: houseName(m.main.holon), asof: asOfWords(ctx, ctx.read.holon(ctx.state, m.main.holon)) }) + "." : null].filter(Boolean).join(" ");
    const cols = ["card", "waits", "es", "ls", "spare", "check"];
    return h("div", { class: "chain-pencil", id: "chain-pencil" },
      h("p", { class: "pencil-verdict" }, verdict(m)),
      h("table", { class: "pencil" },
        h("caption", null, caption),
        h("thead", null, h("tr", null, cols.map((k) => h("th", { scope: "col" }, t("chain.col." + k))))),
        h("tbody", null, rows.map((i) => h("tr", null,
          h("th", { scope: "row" }, i.card.title, h("span", { class: "dust" }, " · " + houseName(i.card.holon))),
          h("td", { "data-label": t("chain.col.waits") }, (i.card.predecessors || []).map((p) => (by.get(p) ? by.get(p).title : t("chain.road.not_here"))).join("; ") || t("chain.col.nothing")),
          h("td", { "data-label": t("chain.col.es") }, day(i.card.ES)),
          h("td", { "data-label": t("chain.col.ls") }, day(i.card.LS)),
          h("td", { "data-label": t("chain.col.spare") }, i.done ? t("chain.road.done") : (spareWords(i) || "")),
          h("td", { class: "pencil-box", "data-label": t("chain.col.check") }, ""))))),
      h("p", { class: "dust pencil-rule" }, t("chain.pencil_rule")));
  }

  // ---------------------------------------------------------------- the slow dolly (phone)

  function scroller(node) {
    for (let p = node.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const o = getComputedStyle(p).overflowY;
      if ((o === "auto" || o === "scroll") && p.scrollHeight > p.clientHeight) return p;
    }
    return document.scrollingElement || document.documentElement;
  }
  function dolly(target) {
    cancelAnimationFrame(anim);
    const sc = scroller(target);
    const doc = sc === document.scrollingElement || sc === document.documentElement;
    const top0 = sc.scrollTop;
    const goal = top0 + target.getBoundingClientRect().top - (doc ? 0 : sc.getBoundingClientRect().top) - 16;
    const reduce = (ctx.prefs && ctx.prefs.reducedMotion) || matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { sc.scrollTop = goal; target.focus({ preventScroll: true }); return; }
    const dur = ms("--d-dolly") || 2000, t0 = performance.now();
    const step = (now) => {
      const k = clamp((now - t0) / dur, 0, 1);
      sc.scrollTop = top0 + (goal - top0) * (1 - Math.pow(1 - k, 3));
      if (k < 1) anim = requestAnimationFrame(step); else target.focus({ preventScroll: true });
    };
    anim = requestAnimationFrame(step);
  }

  // ---------------------------------------------------------------- drawing

  function drawFull(m) {
    const onlyHouse = ctx.route && ctx.route.name === "board" ? ctx.route.arg || null : null;
    const roadSec = h("section", { class: "road-sec", tabindex: "-1", "aria-label": t("chain.road.title") },
      h("div", { class: "road-head" },
        h("h3", { class: "eyebrow" }, t("chain.road.title")),
        h("button", { class: "quiet-act", "aria-pressed": String(folded), onclick: () => { folded = !folded; draw(); } }, t(folded ? "chain.fold.close" : "chain.fold.open"))),
      folded ? fold(m, onlyHouse) : road(m),
      m.pace ? h("p", { class: "road-pace-line dust" }, t("chain.road.pace_line", { who: ctx.read.who(ctx.state, m.pace, m.main ? m.main.holon : null) })) : null);
    const sheet = pencil(m);
    sheet.classList.add("is-folded");
    const sheetBtn = h("button", { class: "quiet-act pencil-btn", "aria-expanded": "false", "aria-controls": "chain-pencil" }, t("chain.pencil_open"));
    sheetBtn.addEventListener("click", () => {
      const was = sheetBtn.getAttribute("aria-expanded") === "true";
      sheetBtn.setAttribute("aria-expanded", String(!was));
      sheet.classList.toggle("is-folded", was);
      sheetBtn.textContent = t(was ? "chain.pencil_open" : "chain.pencil_close");
    });
    const chart = chartBlock(m);
    root.append(
      h("div", { class: "breath" },
        h("p", { class: "breath-verdict voice", dataset: { late: String(m.late || 0) } }, verdict(m)),
        secondLine(m) ? h("p", { class: "breath-eats" }, secondLine(m)) : null),
      h("div", { class: `chain-top${chart ? "" : " no-chart"}` }, chart,
        h("div", { class: "chain-side" }, oneThing(m), h("button", { class: "quiet-act to-road", onclick: () => dolly(roadSec) }, t("chain.road.go")))),
      roadSec, sheetBtn, sheet);
    for (const u of ctx.read.unreadable(ctx.state)) root.append(h("p", { class: "dust" }, t("chain.unread", { holon: u.name })));
  }

  function drawSlice(m) {
    root.append(h("p", { class: "breath-verdict" }, verdict(m)));
    if (m.zone !== "unknown") root.append(h("p", { class: "slice-zone" }, t("chain.zone." + m.zone)));
    const one = oneThing(m, true);
    if (one) root.append(one);
    root.append(h("a", { class: "chain-more", href: "#/chain" }, t("chain.see_all")));
  }

  function draw() {
    root.textContent = "";
    if (ctx.loading && !ctx.state.cards) { root.className = "chain"; root.append(h("p", { class: "dust" }, t("app.reading"))); return; }
    const m = chainModel(ctx);
    m0 = m;
    root.className = `chain zone-${m.zone}${ctx.slot === "aside" ? " is-slice" : ""}${ctx.slot === "map" ? " is-map" : ""}`;
    if (m.empty) {
      root.append(h("p", { class: "chain-empty" }, t("chain.empty")));
      for (const u of ctx.read.unreadable(ctx.state)) root.append(h("p", { class: "dust" }, t("chain.unread", { holon: u.name })));
      return;
    }
    if (ctx.slot === "map") { root.append(fold(m, ctx.filter || (ctx.route && ctx.route.arg) || null)); return; }
    if (ctx.slot === "aside" || ctx.density === "small") drawSlice(m); else drawFull(m);
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      if (c.route && c.route.name === "board") folded = true;
      root = h("div", { class: "chain" }); el.append(root); draw();
    },
    update(c) { ctx = c; draw(); },
    unmount() { cancelAnimationFrame(anim); },
  };
}
