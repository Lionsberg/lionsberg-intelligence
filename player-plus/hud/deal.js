// deal.js: The Deal, the hero (DESIGN §4.1), and its two companions on the Player layout:
// `commitments` (the two stacks) and `whole` (Show me the whole, the privacy line, paper).
// Each export is a view factory per the contract in shell.js.
//
// One gesture, one card: nothing advances on a timer. One tap or one key answers (the act is
// reversible by Undo for five seconds, so it is never confirmed: the bar, line 21). The answer
// settles at once into a quiet line beneath the card's place, with what will happen and its
// Undo, in the flow of the page: it never covers a card. From DESIGN-THE-BAR: cards in the order of their stake, the stake in one plain line, gold only on
// the one owed card, the rest state the field and one line.
// The count she consented to never changes under her: "2 of 2" stays "2 of 2".

import { h, cardModel, renderCard } from "./card.js";
import { store, setPref, markAnswered, unmarkAnswered, byStakeOrder, agent as AGENT } from "./state.js";
import { renderAsk } from "./dock-card.js";

const WIDE = "(min-width: 1024px)";
let openingPlayed = false;   // the opener plays once per page load
const settled = new Map();    // card id -> {label, p}: kept across remounts, so the Undo stays in sight
export const FRAME = (name) => `art/${name.split("/").pop()}.jpg`;   // e.g. "l-person-flow-a"


/* The as-of never goes backwards (never 5:21, then 5:15, after her own 5:27 act). The top line reads the newest of the records' as-of and store.ownAt, but ownAt was
   written only when the record took the act, after the undo window, and a reload forgot the last
   time shown. So the Deal marks her act at the tap: the latest of this module's memory, the
   store's, and the page's clock, kept for the session (state.js's own key) so a later draw, or a
   reload, never shows an earlier time than one already shown. */
let lastActAt = null;
function noteOwnAct(ctx) {
  const now = ctx.fmt.now();
  const at = [lastActAt, store.ownAt, now && now.toISOString()].filter((x) => x && !isNaN(Date.parse(x)))
    .sort((a, b) => Date.parse(a) - Date.parse(b)).pop() || null;
  if (!at) return;
  lastActAt = at; store.ownAt = at;
  try { sessionStorage.setItem("hud.own_at", JSON.stringify(at)); } catch { /* private window: this session's memory holds */ }
}

/* The record of her last act: the ribbon's time for that record and the printed card's footer
   read no earlier than store.ownAt for it, as the top line does (kept for the session, beside it). */
function noteOwnRecord(holon) {
  if (!holon) return;
  store.ownHolon = holon;
  try { sessionStorage.setItem("hud.own_holon", JSON.stringify(holon)); } catch { /* this session's memory holds */ }
}
function ownRecordAsOf(x) {
  const ts = x && x.as_of && x.as_of.ts;
  let holon = store.ownHolon;
  if (holon === undefined) { try { holon = JSON.parse(sessionStorage.getItem("hud.own_holon")); } catch { holon = null; } }
  if (!x || !store.ownAt || holon !== x.id || isNaN(Date.parse(store.ownAt))) return ts || null;
  return !ts || Date.parse(store.ownAt) > Date.parse(ts) ? store.ownAt : ts;
}

function ms(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v.endsWith("ms") ? parseFloat(v) : v.endsWith("s") ? parseFloat(v) * 1000 : parseFloat(v) || 0;
}
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
const wait = (n) => new Promise((r) => setTimeout(r, n));

/** A made frame, still and faint, under a quiet line (never behind a card being read). */
export function stillFrame(name) {
  return h("figure", { class: "still-frame", "aria-hidden": "true" }, h("img", { src: FRAME(name), alt: "", loading: "lazy", decoding: "async" }));
}

// ============================================================================ The Deal

/** A card's by-when: the state's card, then the owed entry, then the deal card's own. */
function byOf(ctx, dc) {
  const st = ctx.state;
  const c = ctx.read.card(st, dc.id);
  if (c && c.by) return c.by;
  const o = ((st.owed && st.owed.entries) || []).find((e) => e.id === dc.id && e.holder === st.actor);
  return (o && o.due) || dc.by || null;
}

/** Salience follows computed stake (DESIGN-THE-BAR §2, line 10): the owed card with the least
    float comes first. Past its by-when (float below zero) first, the most days past leading;
    then a card the whole is waiting on (on the system path, no float); then the nearest by-when;
    the engine's own order breaks every tie, so the order is the same on every visit. */
export function byStake(ctx, cards) {
  return byStakeOrder(ctx.state, cards);   // the one order, shared with the Map and every view (state.js)
}

/** One hand: walk the cards in order, taking each while it fits the time she has (the first
    always, so a long card is never stranded), never more than five. */
function fitHand(cards, available) {
  const hand = [];
  let used = 0;
  for (const c of cards) {
    if (hand.length >= 5) break;
    if (available !== "any" && available != null && used + (c.minutes || 0) > available && hand.length) break;
    hand.push(c); used += c.minutes || 0;
  }
  return hand;
}

/** The cards of today's deal, in the order of their stake, narrowed by the ribbon, fitted to
    the time she has by walking that order. `fits` is the deck she consented to; it does not
    shrink as she answers. Each later hand she asks for (store.hands, this session only, never
    written) takes the next cards the dealer ranked and did not deal: first today's cards that
    did not fit her minutes, then `deal.beyond.cards` in the dealer's own order, fitted afresh to
    the same minutes. `fits` is the union of the hands in order; `hand` the one now in front of
    her; `next` what the next hand would hold; `rest` what would still wait after it. */
export function dealt(ctx) {
  const d = ctx.state.deal;
  if (!d || !Array.isArray(d.cards)) return { all: [], open: [], fits: [], hand: [], minutes: 0, available: null, next: 0, rest: 0, unseen: 0 };
  const ranked = byStake(ctx, d.cards.slice());
  let all = ranked.slice(0, 5);   // never more than five
  if (ctx.filter) all = all.filter((c) => c.holon === ctx.filter);
  const available = store.prefs.minutes != null ? store.prefs.minutes : d.minutes_available;
  let hand = fitHand(all, available);
  const fits = hand.slice();
  const b = d.beyond || {};
  const today = new Set(d.cards.map((c) => c.id));
  const held = new Set(fits.map((c) => c.id));
  // a card answered here or folded in by the server is never dealt again: the next hand, the rest and
  // the lines that count them read only what is still open (never "Four more can wait" over an
  // empty day, or a "next" that deals nothing)
  const mine = (c) => c && (!ctx.filter || c.holon === ctx.filter) && !c.answered && !store.answered.has(c.id);
  const pool = ranked.filter((c) => mine(c) && !held.has(c.id))
    .concat((Array.isArray(b.cards) ? b.cards : []).filter((c) => mine(c) && !today.has(c.id)));
  let at = 0;
  for (let k = 0; k < (store.hands || 0); k++) {
    const more = fitHand(pool.slice(at), available);
    if (!more.length) break;
    fits.push(...more); hand = more; at += more.length;
  }
  const next = fitHand(pool.slice(at), available).length;
  // ranked but not carried (past the dealer's twenty, or an older state that carries only a count)
  const unseen = ctx.filter ? (Array.isArray(b.cards) ? 0 : b.count || 0)
    : Math.max(0, (b.count || 0) - (Array.isArray(b.cards) ? b.cards.length : 0));
  const rest = pool.length - at - next + unseen;
  const open = fits.filter((c) => !store.answered.has(c.id) && !c.answered);   // answered here, or folded in by the server
  const minutes = hand.reduce((s, c) => s + (c.minutes || 0), 0);
  return { all, fits, hand, open, minutes, available, next, rest, unseen };
}

/** The one owed line every place says (the Deal's opener, the Talk's "what needs me?", the Talk's
    question): how many things need her, from the one owed list (state.js read.owedByStake, after the
    fold of her own acts), and which is first, so the line, the card in front of her and the Talk's
    question name the same thing (never the Talk saying the harvest notes while the Deal
    says the folding chairs). The first is the one owed list's first (state.js read.firstOwed, as the
    Map reads it); `card` is its card when it is open in the hand she is dealt, else the hand's first.
    -> {count, card, entry, title, due, inHand} */
export function owedLine(ctx, d = dealt(ctx)) {
  const st = ctx.state || {};
  const owed = ctx.read.owedByStake(st);
  const open = d.open || [];
  // an owed entry and a Deal card are the same thing when they are about the same card (state.js
  // read.cardOfOwed: by id, else by holon and title), as the Map and the Deal compare their firsts
  const key = (x) => { const c = ctx.read.cardOfOwed(st, x); return (c && c.id) || x.id; };
  const openKeys = open.map((c) => key(c));
  const first = ctx.read.firstOwed(st);
  const at = first ? openKeys.indexOf(key(first)) : -1;
  const card = at >= 0 ? open[at] : open[0] || null;
  const full = (first && ctx.read.cardOfOwed(st, first)) || (card && ctx.read.cardOfOwed(st, card)) || null;
  const title = (first && first.title) || (full && full.title) || "";
  const due = (full && full.by) || (first && first.due) || (card && card.by) || null;
  // the count is what the Deal can deal her: the open hand, and every owed thing that is a card
  // still unanswered (in a later hand), each once; an owed thing that is not yet a card is counted
  // apart (`notCards`), said only when true. The welcome's tap, "what needs me?" and the card's
  // "1 of n" all say this one number (never "Five things" while the chairs are not dealt).
  const dealable = [...(st.deal && st.deal.cards) || [], ...((st.deal && st.deal.beyond && st.deal.beyond.cards) || [])]
    .filter((c) => c && !c.answered && !store.answered.has(c.id) && (!ctx.filter || c.holon === ctx.filter));
  const cardKeys = new Set(dealable.map((c) => key(c)));
  const keys = new Set(openKeys);
  let notCards = 0;
  for (const x of owed) { const k = key(x); if (cardKeys.has(k)) keys.add(k); else if (!keys.has(k)) notCards++; }
  return { count: keys.size, notCards, card, entry: first, title, due, inHand: at >= 0 };
}

function staleHolon(ctx) {
  return ctx.read.holons(ctx.state).find((y) => ctx.fmt.freshness(y.as_of && y.as_of.ts) === "older") || null;
}

/** The open commitments either way, as the two stacks count them. */
function openCommitments(ctx) {
  const st = ctx.state;
  return (st.commitments || []).filter((k) => k.status === "open" && (k.keeper === st.actor || k.witness === st.actor));
}

/** The rest state (nothing owed, or the deal played): the field, one line, nothing else. The
    shell's other Player views step back while it holds (base.css, html[data-rest]). */
function setRest(on) {
  const r = document.documentElement;
  if (on) r.dataset.rest = ""; else delete r.dataset.rest;
}

export default function createDeal() {
  let el, ctx, cur = null, swipe = null, saidFixed = false;
  const root = h("div", { class: "deal" });

  function briefing(d) {
    const t = ctx.t, f = ctx.fmt, st = ctx.state;
    // the engine's sentence only while nothing in the deal is answered (the fold drops it after);
    // otherwise the opener reads the one owed list after the fold (state.js read.owedByStake, the
    // list the Map reads): its count, and its first with that card's own by-when against the clock,
    // so it never names an answered card and never says "today" of a thing due next week
    if (st.deal.briefing && !ctx.filter && d.open.length === d.fits.length) return st.deal.briefing;
    const owed = ctx.read.owedByStake(st);
    if (!owed.length) return d.open.length ? (d.open.length === 1 ? t("deal.count_one_plain") : t("deal.count_many_plain", { count: f.number(d.open.length) })) : null;
    // the one owed line: its count, and the first that is in front of her (owedLine)
    const ol = owedLine(ctx, d);
    const what = ol.title;
    const many = owed.length;   // the opener says the owed list's count, the Map's (the truth suite)
    const lower = what ? what.charAt(0).toLowerCase() + what.slice(1) : "";
    const by = ol.due && f.by(ol.due) ? ", " + f.by(ol.due) : "";
    if (!lower) return many === 1 ? t("deal.count_one_plain") : t("deal.count_many_plain", { count: f.number(many) });
    return many === 1 ? t("deal.opener_one", { what: lower, by })
      : t("deal.opener_many", { count: f.number(many), what: lower, by });
  }

  /** The cost as a quiet line under the opener (never a box); a tap says how much time she has. */
  function costLine(d) {
    const t = ctx.t;
    const cost = ctx.fmt.aboutMinutes(d.minutes);
    const btn = h("button", { class: "link-btn deal-cost figures", "aria-haspopup": "dialog", title: t("deal.cost_label"),
      "aria-label": `${cost}. ${t("deal.cost_label")}` }, cost);
    btn.addEventListener("click", () => {
      const opts = (t("deal.time_options") || []).map((n) => ({ v: n, label: t("deal.time_chip", { n }) }))
        .concat([{ v: "any", label: t("deal.time_any") }]);
      const close = ctx.openSheet({
        title: t("deal.time_chip_label"),
        body: h("ul", { class: "menu-list", role: "menu" }, opts.map((o) => h("li", null,
          h("button", { role: "menuitemradio", "aria-checked": String(o.v === d.available), onclick: () => { close(); cur = null; setPref("minutes", o.v); } }, o.label)))),
      });
    });
    return btn;
  }

  /** An answer, settled in the flow while its Undo holds: what she chose, what will happen. */
  function settledRow(dc, restOnly) {
    const t = ctx.t, s = settled.get(dc.id);
    if (!s || !s.p) return null;
    const holding = s.p.status === "holding";
    if (!holding && (restOnly || s.p.status === "undone" || s.p.status === "refused")) return null;
    return h("div", { class: "deal-settled", dataset: { card: dc.id } },
      h("p", { class: "deal-settled-text ink-said", title: s.consequence || "" }, h("span", { class: "deal-settled-mark", "aria-hidden": "true" }, "✓ "),
        t("deal.settled", { option: s.label }) + (s.consequence ? "." : ""), s.consequence ? h("span", { class: "deal-settled-then" }, " " + s.consequence) : null),
      // "Done · Undo" while the window holds; "Done" after, until the next answer takes the line
      h("span", { class: "deal-settled-done" }, t("deal.done")),
      holding ? h("button", { class: "link-btn", onclick: () => s.p.undo() }, "↺ " + t("deal.undo")) : null);
  }

  function restFrame() { const f = stillFrame("round-4/l-person-flow-a"); f.classList.add("is-turning"); return f; }

  function draw(animateOpening) {
    const t = ctx.t, st = ctx.state;
    root.textContent = "";
    root.classList.toggle("is-small", ctx.density === "small");

    if (ctx.density === "small") {   // folded at the top of the Cell and Room layouts
      const d = dealt(ctx);
      root.append(h("a", { class: "deal-small", href: "#/deal?layout=player" }, t("deal.small", { count: d.open.length })));
      return;
    }

    const greeting = st.deal && st.deal.greeting ? h("p", { class: "deal-greeting voice" }, st.deal.greeting) : null;
    if (greeting) root.append(greeting);
    const opening = h("h1", { class: "deal-opening voice" }, (st.deal && st.deal.opening) || t("deal.opening"));
    root.append(opening);

    // an ask your agent made is the Deal's top card too, so you meet it wherever you are (the dock's
    // fourth bar reading); answered here or in the dock, it is the same ask
    const asks = ((st.hud && st.hud.agents) || []).filter((a) => a.of === st.actor && a.kind !== "guest")
      .flatMap((a) => (a.asks || []).map((x) => ({ ...x })));
    if (asks.length) {
      // each ask opens as a full card too: the agent's question, what it would do, its context
      root.append(h("div", { class: "deal-asks" }, ...asks.map((x) => {
        const face = renderAsk(ctx, x, {
          onAnswer: async (ans) => { const r = await AGENT.answer(x.conversation, x.id, ans); return { ok: r.ok, reason: r.out && r.out.refused }; },
        });
        face.append(h("p", { class: "card-open" }, h("button", { class: "link-btn card-open-btn", type: "button", "aria-haspopup": "dialog",
          dataset: { openCard: x.id }, onclick: () => ctx.openCard(x.id, { from: "deal" }) }, t("card.open_full"))));
        return face;
      })));
    }

    if (!st.deal && st.hud && st.hud.fresh) {   // a home just adopted: the engine has not dealt yet, nothing failed
      setRest(false);
      root.append(h("p", { class: "deal-line" }, t("deal.fresh")));
      if (ctx.dock) root.append(h("div", { class: "actions owed" }, h("button", { class: "pill primary", type: "button", onclick: () => {
        ctx.dock.setOpen(true);
        window.dispatchEvent(new CustomEvent("lionsberg:dock-words", { detail: { text: t("deal.fresh_words") } }));
      } }, t("deal.fresh_ask"))));
      return;
    }
    if (!st.deal) {
      // say only what is true: "below" only when something is below (the quiet never lies);
      // and while the record holds lines the fold has not read yet, say that, never "nothing is
      // dealt" beside a margin that says a line is in the record
      const below = openCommitments(ctx).length > 0;
      const newer = st.hud && st.hud.record_newer;
      setRest(!below);
      root.append(h("p", { class: "deal-rest-line voice" }, newer ? (newer.by_agent ? t("deal.agent_wrote") : t("deal.record_moved"))
        : below ? t("deal.error_below") : t("deal.error")));
      if (!below) root.append(restFrame());
      return;
    }

    const d = dealt(ctx);
    const stage = h("div", { class: "deal-stage", id: "current-card" });

    if (!d.all.length || !d.open.length) {
      // the rest state: the field turning, one line in the agent's voice, nothing else
      setRest(true);
      // the next hand, when the dealer ranked more than she has seen: one act, and what still waits
      const line = d.next ? t("deal.played") : !d.all.length ? t("deal.empty")
        : d.unseen ? t("deal.played_beyond", { count: ctx.fmt.number(d.unseen) }) : t("deal.played");
      stage.append(h("p", { class: "deal-rest-line voice" }, line));
      if (d.next) {
        stage.append(h("div", { class: "actions deal-next" }, h("button", { class: "pill primary", type: "button", onclick: () => {
          store.hands = (store.hands || 0) + 1;   // this session only; nothing is written
          cur = null;
          draw(true);
        } }, t("deal.next_hand", { count: ctx.fmt.number(d.next, true) }))));
        if (d.rest > 0) stage.append(h("p", { class: "deal-next-rest dust" }, t("deal.next_rest", { rest: ctx.fmt.number(d.rest) })));
      }
      for (const dc of d.fits) { const r = settledRow(dc, true); if (r) stage.append(r); }
      if (d.all.length && ctx.flags.standing_question) stage.append(fixedCard());
      stage.append(restFrame());
      root.append(stage);
      if (animateOpening) playOpening([greeting, opening, stage]);
      return;
    }
    setRest(false);

    const head = h("div", { class: "deal-head" });
    const brief = briefing(d);
    if (brief) head.append(h("p", { class: "deal-line" }, brief));
    // the cost line's place holds the latest answer while its Undo holds: one line, so the card
    // below never moves (the bar, line 11), and the Undo stays where the eye already is
    const latest = [...settled.keys()].reverse().find((id) => d.hand.some((c) => c.id === id));   // this hand's own
    const holdingRow = latest ? settledRow(d.hand.find((c) => c.id === latest)) : null;
    head.append(holdingRow || costLine(d));
    root.append(head);

    // each fact said once, in the line above the card
    const unread = ctx.read.unreadable(st)[0];
    const stale = staleHolon(ctx);
    if (unread) root.append(h("p", { class: "deal-note dust" }, t("deal.unreadable", { holon: unread.name })));
    else if (stale) root.append(h("p", { class: "deal-note dust" }, t("deal.offline", { holon: stale.name, when: ctx.fmt.when(stale.as_of && stale.as_of.ts) })));
    if (!store.hands && d.fits.length < d.all.length) root.append(h("p", { class: "deal-note dust" }, t("deal.time_short", { count: ctx.fmt.number(d.fits.length, true) })));
    root.append(stage);

    // the card in front of her is the first the owed line names, so the line and the card agree
    if (!cur || !d.open.some((c) => c.id === cur)) cur = (owedLine(ctx, d).card || d.open[0]).id;
    const wide = matchMedia(WIDE).matches && !ctx.prefs.large;
    const shown = wide ? d.open.slice(0, 3) : [d.open.find((c) => c.id === cur)];
    const row = h("div", { class: `deal-cards${wide ? " is-wide" : ""}` });
    shown.forEach((dc, i) => {
      // counted against what she still has (never "1 of 5" beside "Three things"): its place
      // among the open cards, of the one count "what needs me?" says
      const owedCount = owedLine(ctx, d).count;
      const n = d.open.indexOf(dc) + 1;
      const m = cardModel(ctx, { deal: dc });
      const face = renderCard(ctx, m, {
        form: "large", from: "deal", index: n, total: Math.max(owedCount, d.open.length, n), selected: ctx.selected === dc.id, oneTap: true,
        onConfirm: (label, oi) => settle(dc, label, oi),
        onGive: ctx.longCard && ctx.launchBody && ctx.longCard(m.card)
          ? () => ctx.launchBody({ card: dc.id }) : null,
      });
      // her own name for the card, above its question, from the fold (the name she kept with Keep it)
      const named = ctx.read.cardName ? ctx.read.cardName(ctx.state, dc.id) : "";
      if (named) { const ti = face.querySelector(".card-title"); const nm = h("p", { class: "card-named" }, named); if (ti) ti.before(nm); else face.prepend(nm); }
      // the one owed thing on the screen: the card with the least float carries the gold
      if (i === 0) face.classList.add("owed");
      if (!wide) attachSwipe(face, d.open.length);
      row.append(face);
    });
    stage.append(row);
    if (!wide && d.open.length > 1) {
      const i = d.open.findIndex((c) => c.id === cur);
      stage.append(h("div", { class: "deal-nav" },
        h("button", { class: "link-btn", onclick: () => step(-1), disabled: i <= 0 }, "← " + t("deal.previous")),
        h("button", { class: "link-btn", onclick: () => step(1), disabled: i >= d.open.length - 1 }, t("deal.next") + " →")));
    }
    if (animateOpening) playOpening([greeting, opening, head, row]);
  }

  // The opening, after the Mark has given way: the agent's voice (an invitation), "Here's
  // the deal.", one plain sentence, then the first card rises. Each arrives at reading pace.
  async function playOpening(parts) {
    if (ctx.prefs.reducedMotion) return;
    const items = parts.filter(Boolean);
    const rise = css("--rise-card"), ease = css("--e-settle");
    const wps = parseFloat(css("--reading-wps") || "3.6");
    for (const x of items) x.style.opacity = "0";
    for (let i = 0; i < items.length; i++) {
      const x = items[i];
      x.style.opacity = "";
      ctx.animate(x, [{ opacity: 0, transform: `translateY(${rise})` }, { opacity: 1, transform: "none" }], { duration: ms("--d-card"), easing: ease, fill: "both" });
      if (i < items.length - 1) await wait(Math.min(ms("--d-beat-max"), ms("--d-breath") + ((x.textContent || "").split(/\s+/).length / wps) * 1000 * (i === items.length - 2 ? 0.5 : 1)));
    }
  }

  /** One tap answers (the act is reversible for five seconds, so it is never confirmed, bar
      line 21). The surface settles at once, optimistically: the settled line and the next
      card are drawn in the same frame as the tap; the record confirms later, and a refusal
      brings the card back. The tap's time to paint is kept on the view for the proof. */
  function settle(dc, label, oi) {
    const t = ctx.t, t0 = performance.now();
    const a0 = actFor(dc, label);
    const consequence = Array.isArray(dc.consequences) && dc.consequences[oi] ? dc.consequences[oi] : null;
    const p = ctx.act(a0.type, a0.body, a0.links, dc.holon, {
      confirmed: true, quiet: true,
      label: t("deal.settled_sr", { option: label }),
      onUndo: () => { settled.delete(dc.id); unmarkAnswered(dc.id); },
    });
    settled.set(dc.id, { label, p, consequence });
    p.done.then((q) => {
      if (q && q.status === "refused") { settled.delete(dc.id); unmarkAnswered(dc.id); return; }
      if (el && el.isConnected) draw(false);   // written: the line now reads "Done", and stays
    });
    cur = null;
    noteOwnAct(ctx);       // the as-of is at least this tap, before the store emits
    noteOwnRecord(dc.holon);   // and the record she acted in, so its own as-of reads no earlier
    markAnswered(dc.id);   // the store emits; the shell calls update()
    draw(false);
    // a card that leads somewhere on its first option (a body's handoff: "Read it now" opens the
    // body in the room with the handoff shown) is followed once the answer is written
    if (dc.go && oi === (dc.go_option != null ? dc.go_option : 0)) location.hash = dc.go;
    requestAnimationFrame(() => { document.documentElement.dataset.dealTapMs = String(Math.round(performance.now() - t0)); });
    const next = root.querySelector(".card--large"), line = root.querySelector(".deal-settled");
    if (line) ctx.animate(line, [{ opacity: 0 }, { opacity: 1 }], { duration: ms("--d-quick") || 120, easing: css("--e-settle") });
    if (next) ctx.animate(next, [{ opacity: 0, transform: `translateY(${css("--rise-card")})` }, { opacity: 1, transform: "none" }],
      { duration: ms("--d-card"), easing: css("--e-settle") });
  }

  function step(dir) {
    const d = dealt(ctx);
    const i = d.open.findIndex((c) => c.id === cur);
    const j = Math.max(0, Math.min(d.open.length - 1, i + dir));
    if (j === i) return;
    cur = d.open[j].id; draw(false);
    const face = root.querySelector(".card--large");
    if (face) {
      ctx.animate(face, [{ opacity: 0, transform: `translateX(${dir > 0 ? "" : "-"}${css("--rise-card")})` }, { opacity: 1, transform: "none" }],
        { duration: ms("--d-card"), easing: css("--e-settle") });
      face.focus({ preventScroll: true });
    }
  }

  function attachSwipe(face, total) {
    if (total < 2) return;
    face.addEventListener("pointerdown", (e) => { swipe = { x: e.clientX, y: e.clientY }; });
    face.addEventListener("pointerup", (e) => {
      if (!swipe) return;
      const dx = e.clientX - swipe.x, dy = e.clientY - swipe.y;
      swipe = null;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);   // left = next, right = back
    });
  }

  // The standing question (held behind FLAGS.standing_question)
  function fixedCard() {
    const t = ctx.t;
    const q = (ctx.state.deal && ctx.state.deal.question) || t("deal.fixed_question");
    const card = h("article", { class: "card card--large card--fixed", "aria-labelledby": "fixed-q" },
      h("h2", { class: "card-title", id: "fixed-q" }, q));
    if (saidFixed) { card.append(h("p", { class: "dust" }, t("deal.fixed_thanks"))); return card; }
    const area = h("textarea", { class: "fixed-input", rows: "3", "aria-labelledby": "fixed-q", placeholder: t("deal.fixed_placeholder") });
    card.append(area, h("div", { class: "card-options confirm" },
      h("button", { class: "pill primary", onclick: () => {
        const text = area.value.trim();
        if (!text) { area.focus(); return; }
        ctx.act("say", { text }, {}, ctx.home, { confirmed: true, label: t("deal.said_label"), onUndo: () => { saidFixed = false; draw(false); } });
        saidFixed = true; draw(false);
      } }, t("deal.fixed_send")),
      h("button", { class: "pill quiet", onclick: () => { saidFixed = true; card.remove(); } }, t("deal.fixed_later"))));
    return card;
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      el.append(root);
      draw(!openingPlayed);
      openingPlayed = true;
      el.append(printCard(ctx));
    },
    update(c) {
      ctx = c;
      draw(false);
      const old = el.querySelector(".deal-print");
      if (old) old.replaceWith(printCard(ctx));
    },
    unmount() { root.textContent = ""; if (ctx && ctx.density !== "small") setRest(false); },
    key(e) {
      if (ctx.density === "small") return false;
      const d = dealt(ctx);
      if (!d.open.length) return false;
      const k = e.key.toLowerCase();
      if (k === "j" || e.key === "ArrowRight") { step(1); return true; }
      if (k === "k" || e.key === "ArrowLeft") { step(-1); return true; }
      const dc = d.open.find((c) => c.id === cur) || d.open[0];
      if (/^[1-5]$/.test(e.key) && dc) {
        const i = Number(e.key) - 1, o = (dc.options || [])[i];
        if (o != null) { settle(dc, o, i); return true; }
      }
      return false;
    },
  };
}

// The event an answer writes (shared with the full card, card-full.js). STATE v1 gives options as words, not acts; until the engine
// names each option's act (a proposed field: deal.cards[].acts), the HUD writes the
// typed act only where the registry makes it unambiguous, and otherwise the person's own
// words as a `say` anchored to the card, for the agent to carry out.
export function actFor(dc, label) {
  const i = (dc.options || []).indexOf(label);
  const anchored = { anchored_to: [dc.id] };
  if (Array.isArray(dc.acts) && dc.acts[i] && dc.acts[i].type) return dc.acts[i];
  if (dc.kind === "request" && i === 0) return { type: "answer", body: { answer: "accept" }, links: { answers: [dc.id] } };
  if (dc.kind === "request" && i === 2) return { type: "answer", body: { answer: "decline" }, links: { answers: [dc.id] } };
  if (dc.kind === "ratify" && i === 0) return { type: "ratify", body: {}, links: { answers: [dc.id] } };
  if ((dc.kind === "decide" || dc.section === "decision") && i >= 0 && i < (dc.options || []).length - 1)
    return { type: "decide", body: { text: label }, links: { answers: [dc.id] } };
  return { type: "say", body: { text: label }, links: anchored };
}

// ============================================================================ the printed Deal card (§7)
// Front: the Mark alone. Back: the Deal: the opener, the date, up to three cards with tick
// boxes, the standing question when its flag is on, each record's as of, a witness's initials.

function printCard(ctx) {
  const t = ctx.t, st = ctx.state, f = ctx.fmt;
  const action = t("mark.action");
  const front = h("section", { class: "deal-print-face deal-print-front", "aria-hidden": "true" },
    h("div", { class: "mark" },
      h("p", { class: "mark-name" }, t("mark.name")),
      h("p", { class: "mark-narrative" }, t("mark.narrative")),
      h("hr", { class: "mark-rule" }),
      h("p", { class: "mark-action" }, (Array.isArray(action) ? action : []).flatMap((a, i) => i ? [h("span", { class: "mark-bar" }), h("span", null, a)] : [h("span", null, a)]))));
  const now = f.now();
  const cards = ((st.deal && st.deal.cards) || []).slice(0, 3);
  const back = h("section", { class: "deal-print-face deal-print-back" },
    h("p", { class: "dp-opening" }, (st.deal && st.deal.opening) || t("deal.opening")),
    h("p", { class: "dp-date" }, t("print.date", { day: f.dayName(now), date: now.toLocaleDateString(undefined, { day: "numeric", month: "long" }) })),
    h("ol", { class: "dp-cards" }, cards.map((c) => h("li", null,
      h("p", { class: "dp-q" }, c.question),
      h("ul", { class: "dp-options" }, (c.options || []).map((o) => h("li", null, h("span", { class: "dp-box", "aria-hidden": "true" }), o,
        c.recommendation === o ? h("em", { class: "dp-suggested" }, " " + t("print.suggested")) : null)))))),
    ctx.flags.standing_question ? h("div", { class: "dp-fixed" }, h("p", { class: "dp-q" }, (st.deal && st.deal.question) || t("deal.fixed_question")),
      h("span", { class: "dp-rule" }), h("span", { class: "dp-rule" })) : null,
    h("p", { class: "dp-foot" }, ctx.read.holons(st).map((x) => [x, ownRecordAsOf(x)]).map(([x, ts]) => t("print.holons_as_of", { holon: x.name,
      time: ts ? (f.sameDay(f.date(ts), now) ? f.time(ts) : f.dayName(f.date(ts))) : "" })).filter((x) => !/,\s*as of\s*$/.test(x)).join(" · ")),
    h("p", { class: "dp-witness" }, h("span", null, t("print.witness")), h("span", { class: "dp-rule short" })),
    h("p", { class: "dp-note" }, t("print.back_note")));
  return h("div", { class: "deal-print print-only" }, front, back);
}

// ============================================================================ the two stacks

export function commitments() {
  let el, ctx;
  const root = h("div", { class: "stacks" });
  function draw() {
    const t = ctx.t, st = ctx.state;
    root.textContent = "";
    if (ctx.density === "small") root.classList.add("is-small");
    const list = (st.commitments || []).filter((k) => k.status === "open" && (!ctx.filter || k.holon === ctx.filter));
    // answered on this device and not yet folded by the engine: a yes to a request is a new commitment
    const owed = (st.owed && st.owed.entries) || [];
    const fresh = [...store.answered].filter((id) => owed.some((e) => e.id === id && e.kind === "request") &&
      !list.some((k) => k.card === id && k.keeper === st.actor)).length;
    const byMe = list.filter((k) => k.keeper === st.actor).length + fresh;
    const toMe = list.filter((k) => k.keeper !== st.actor && k.witness === st.actor).length;
    // quiet lines, never boxes (the bar, line 19): each opens its side of the Queue
    const stack = (side, label, count) => h("a", { class: "stack", href: `#/queue?side=${side}` },
      t("commitments.count", { label, count }));
    if (byMe) root.append(stack("me", t("commitments.by_me"), byMe));
    if (toMe) root.append(stack("others", t("commitments.to_me"), toMe));
    // at the desk, the week in one sentence (the Turn said, never a number beside a picture)
    const tally = ((st.kept || {}).by_actor || {})[st.actor];
    const due = tally ? (tally.kept || 0) + (tally.kept_unwitnessed || 0) + (tally.broken || 0) : 0;
    if (ctx.slot === "aside" && due) {
      const late = ctx.read.keptLate ? ctx.read.keptLate(st, st.actor, null) : 0;
      const n = (x) => ctx.fmt.number(x, true);
      root.append(h("p", { class: "stacks-week dust" }, late
        ? t("commitments.turn_line_late", { kept: n(tally.kept || 0), due: n(due), late: n(late) })
        : t("commitments.turn_line", { kept: n(tally.kept || 0), due: n(due) })));
    }
    root.closest && el && el.closest(".view") && el.closest(".view").classList.toggle("is-quiet", !byMe && !toMe);
  }
  return {
    mount(container, c) { el = container; ctx = c; el.append(root); draw(); },
    update(c) { ctx = c; draw(); },
    unmount() { root.textContent = ""; },
  };
}

// ============================================================================ Show me the whole, and the privacy line

export function whole() {
  let el, ctx;
  const root = h("div", { class: "whole" });
  function draw() {
    const t = ctx.t;
    root.textContent = "";
    // the way to the whole is the Map, a place in the frame on every view; a second act here
    // would compete with the card's (the bar, line 12). The privacy line and paper stay.
    root.append(
      h("p", { class: "privacy dust" }, t("deal.privacy")),
      h("p", { class: "paper-links" },
        h("button", { class: "link-btn", onclick: () => printDeal(false) }, t("deal.print")),
        h("button", { class: "link-btn", onclick: () => printDeal(true) }, t("deal.print_light"))));
  }
  return {
    mount(container, c) { el = container; ctx = c; el.append(root); draw(); },
    update(c) { ctx = c; draw(); },
    unmount() { root.textContent = ""; },
  };
}

function printDeal(light) {
  const root = document.documentElement;
  root.dataset.print = "deal";
  if (light) root.dataset.printLight = ""; else delete root.dataset.printLight;
  const done = () => { delete root.dataset.print; delete root.dataset.printLight; removeEventListener("afterprint", done); };
  addEventListener("afterprint", done);
  print();
}
