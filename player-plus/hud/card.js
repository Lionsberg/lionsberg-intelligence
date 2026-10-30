// card.js: the one card face (DESIGN §4: one deck, one truth). A Work Card looks the
// same in The Deal, the Board, the Queue, the Map, the Chain and the Room.
//
//   import { h, cardModel, renderCard } from "./card.js";
//   const m = cardModel(ctx, { card, deal, owed });      // any of the three, by id
//   el.append(renderCard(ctx, m, { form: "large" | "compact" | "row", ... }));
//
// Anatomy, top to bottom: eyebrow (why · home · kind) · title · essence line · options
// (one marked suggested, its reason beneath) · foot (holder · by when · minutes · days to
// spare · as of) · "Open the card": the full card (card-full.js) holds what the fold once held,
// and everything else the state and the record say about it (the full card opens to show all
// its detail).
// Every string from strings.json via ctx.t; every value from tokens.css. Data is set as
// text, never as markup.

/** h("p", {class: "x", onclick: fn}, "text", child) — a tiny DOM builder. */
export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false || kid === "") continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

// A card in one of these states is finished: it has no by-when left to miss and no days to spare.
export const DONE_STATES = new Set(["done", "kept", "released", "declined", "returned"]);

/** Days to spare, computed so the words never contradict each other: a finished card has none
    to show (null); a card past its by-when is late by that many days (negative), whatever its
    float on the plan says; otherwise the engine's float (TF). One source for every view. */
export function spareDays(ctx, card, by) {
  if (!card) return null;
  if (DONE_STATES.has(card.state) || card.stage === "did") return null;
  const d = (by || card.by) ? ctx.fmt.date(by || card.by) : null;
  const past = d ? -ctx.fmt.daysBetween(ctx.fmt.now(), d) : 0;
  if (past > 0) return -past;
  return card.TF != null ? card.TF : null;
}

const REASON_BY_OWED = { request: "reason.asked", claim: "reason.word", commitment: "reason.committed",
  ratify: "reason.yes", decide: "reason.yes", thread: "reason.asked" };

/** The card's view model, from whichever of a state card, a Deal card and an owed entry is at hand. */
export function cardModel(ctx, { card = null, deal = null, owed = null } = {}) {
  const st = ctx.state, t = ctx.t, f = ctx.fmt, R = ctx.read;
  const id = (deal && deal.id) || (card && card.id) || (owed && owed.id);
  card = card || R.card(st, id);
  if (!owed) owed = ((st.owed && st.owed.entries) || []).find((e) => e.id === id && e.holder === st.actor) || null;
  // an owed commitment points at its card: one card, one face, one set of figures
  if (!card && owed && owed.kind === "commitment") {
    const k = (st.commitments || []).find((x) => x.id === owed.id);
    if (k && k.card) card = R.card(st, k.card);
  }
  const holon = (deal && deal.holon) || (card && card.holon) || (owed && owed.holon) || null;
  const holonName = (deal && deal.holon_name) || R.holonName(st, holon);
  const done = !!(card && (DONE_STATES.has(card.state) || card.stage === "did"));
  const by = done ? null : ((card && card.by) || (owed && owed.due) || null);
  const wholeWaits = !!((deal && deal.whole_waits) || (card && card.system_critical));
  const onPath = wholeWaits || !!(card && card.critical) || ((st.path && st.path.critical) || []).includes(id);
  const byDate = by ? f.date(by) : null;
  const daysPast = byDate ? Math.max(0, -f.daysBetween(f.now(), byDate)) : 0;

  // why it is here: one short eyebrow (DESIGN §2.2)
  let reasonKey = "reason.waiting", reasonVars = null;
  if (deal && deal.section === "thread") reasonKey = "reason.asked";
  else if (deal && REASON_BY_OWED[deal.kind]) reasonKey = REASON_BY_OWED[deal.kind];
  else if (owed && REASON_BY_OWED[owed.kind]) reasonKey = REASON_BY_OWED[owed.kind];
  else if (by) {
    const d = f.date(by), diff = d ? f.daysBetween(f.now(), d) : 99;
    if (diff >= 0 && diff <= 3) { reasonKey = "reason.due"; reasonVars = { day: diff === 0 ? t("time.today") : f.dayName(d) }; }
  }
  // the stake, computed: what it blocks and for whom (the engine's `unlocks`, the holon it serves)
  const unlocks = deal && typeof deal.unlocks === "string" && deal.unlocks.trim() ? deal.unlocks.trim() : null;
  const forWhom = holon && holon === homeId(st) ? t("app.you") : holonName;
  const stake = unlocks ? t(wholeWaits ? "deal.stake_whole" : "deal.stake",
    { what: unlocks.charAt(0).toUpperCase() + unlocks.slice(1), what_lower: unlocks.charAt(0).toLowerCase() + unlocks.slice(1), holon: forWhom || "" }) : null;
  // the plain reason (the Deal's face, where the stake line already says the whole waits); the
  // other faces keep "the whole is waiting on this" as their reason
  const reasonPlain = t(reasonKey, reasonVars);
  if (wholeWaits) { reasonKey = "reason.system"; reasonVars = null; }
  const kind = (card && card.kind) || (deal && deal.kind && deal.kind !== "decide" ? deal.kind : null) || (deal && deal.section === "decision" ? "decision" : null) || (owed && owed.kind) || null;

  const options = ((deal && deal.options) || []).map((label) => ({
    label, suggested: !!(deal.recommendation && label === deal.recommendation),
    reason: deal.recommendation && label === deal.recommendation ? deal.why : null,
  }));

  const h0 = R.holon(st, holon);
  const asOfTs = h0 && h0.as_of && h0.as_of.ts;
  const aliases = (card && Array.isArray(card.aliases)) ? card.aliases.filter((a) => a !== holon) : [];
  const needsYes = !!(deal && (deal.section === "decision" || deal.kind === "ratify" || deal.kind === "decide"));

  // the ink grammar: said (open) · kept (claimed, not yet witnessed) · agreed (witnessed)
  const commitment = ((st.commitments || []).find((k) => k.card === id || k.id === id || (card && k.card === card.id))) || null;
  const posture = R.posture ? R.posture(st, holon) : "open";
  const ink = !commitment ? null : commitment.status === "kept" ? "agreed"
    : commitment.status === "kept-unwitnessed" ? "kept" : commitment.status === "open" ? "said" : null;

  return {
    id, holon, holonName, card, deal, owed, ink,
    postureLabel: posture && posture !== "open" ? t("posture." + posture) : null,
    reason: t(reasonKey, reasonVars), reasonPlain,
    kindLabel: kind ? t("kind." + kind) : null,
    title: (deal && deal.question) || (card && card.title) || (owed && owed.title) || "",
    essence: deal && deal.why && !options.some((o) => o.suggested) ? deal.why : null,
    options,
    needsYes,
    holder: card ? card.holder : (owed ? owed.holder : null),
    // one source for a card's minutes: the state's card, then the owed entry, then the deal's
    by, minutes: (card && card.minutes) || (owed && owed.minutes) || (deal && deal.minutes) || null,
    spare: done ? null : daysPast > 0 ? -daysPast : (card && card.TF != null ? card.TF : null),
    onChain: !!(card && card.critical),
    onPath, done, daysPast, stake, leverage: deal && typeof deal.leverage === "number" ? deal.leverage : null,
    wholeWaits,
    asOfTs,
    alsoIn: aliases.map((a) => R.holonName(st, a)).filter(Boolean),
    publishedBy: card && card.published_by ? R.holonName(st, card.published_by) : null,
  };
}

/**
 * renderCard(ctx, model, opts) -> <article class="card">
 *   form: "large" (The Deal) · "compact" (the Board, the Map, the Chain) · "row" (the Queue)
 *   index, total: for "1 of 3"
 *   chosen: the option label chosen (shows the consequence)
 *   onChoose(label, i), onConfirm(label), onNotYet(), onOpen(): the view's handlers
 *   selected: true when the shell's selected card is this one
 */
export function renderCard(ctx, m, opts = {}) {
  const t = ctx.t, f = ctx.fmt, st = ctx.state;
  const form = opts.form || "compact";
  const large = form === "large";
  const headId = `card-${form}-${m.id ? m.id.slice(0, 12) : Math.random().toString(16).slice(2)}`;
  const el = h("article", { class: `card card--${form}${opts.selected ? " is-selected" : ""}${m.wholeWaits ? " is-whole" : ""}${large && m.onPath ? " is-path" : ""}${large && m.daysPast ? " is-late" : ""}`,
    "aria-labelledby": headId, dataset: { card: m.id || "" }, tabindex: large ? "-1" : null });

  // the foot's facts: holder · by when · minutes · days to spare · as of  (a large face shows
  // only why and by-when; the rest is in the full card)
  const footBits = [];
  const put = (x, faceToo) => { if (x && (!large || faceToo)) footBits.push(x); };
  if (m.holder) put(m.holder === st.actor ? t("card.holder_you") : t("card.holder", { holder: ctx.read.who(st, m.holder, m.holon) }));
  if (large) put(m.stake && m.wholeWaits ? m.reasonPlain : m.reason, true);
  if (m.by) put(f.by(m.by), true);
  if (m.minutes && form !== "row") put(t("card.minutes", { n: Math.round(m.minutes) }));
  if (m.onChain && !large) put("◆ " + t("time.on_the_chain"));
  else if (m.spare != null && !large && !(m.daysPast > 0)) put("◇ " + f.spare(m.spare));   // a late card says "past" once, by its by-when
  if (m.asOfTs) put(f.asOf(m.asOfTs));
  if (m.alsoIn && m.alsoIn.length) put(t("card.also_in", { holon: m.alsoIn.join(", ") }), !large);
  if (m.publishedBy) put(t("card.published_by", { holon: m.publishedBy }), !large);
  if (large && m.postureLabel) put(m.postureLabel, true);

  if (large) {
    // the Deal's face (DESIGN-THE-BAR §2): the count, quiet; the question; the stake in one
    // plain line; why it is here and its by-when; the answers, the suggested one first in weight
    if (opts.total) el.append(h("p", { class: "card-count figures dust" }, t("deal.of", { n: opts.index, total: opts.total })));
  } else {
    // eyebrow: one reason, its home, and only a word that helps (never the same word twice)
    const seen = new Set();
    const parts = [m.reason, m.holonName, m.kindLabel, m.postureLabel].filter((x) => {
      if (!x) return false;
      const k = String(x).toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k); return true;
    });
    el.append(h("div", { class: "card-top" }, h("p", { class: "eyebrow card-eyebrow" }, parts.join(" · "))));
    if (m.wholeWaits && form !== "row") el.append(h("p", { class: "card-whole" }, t("deal.whole_waits")));
  }

  const titleTag = form === "row" ? "h3" : "h2";
  const title = h(titleTag, { class: `card-title${m.ink && !large ? " ink-" + m.ink : ""}`, id: headId }, m.title);
  if (form === "row" && opts.onOpen) {
    el.append(h("button", { class: "card-row-open", onclick: () => opts.onOpen(m) }, title));
  } else el.append(title);

  // the foot: on the Deal's face a plain line (why · by-when) with "Open the card" beneath it;
  // on a compact or row face the foot itself opens the full card. Inside the full card's own
  // sheet (opts.inSheet) nothing opens again.
  let foot = null, opener = null;
  const canOpen = !opts.inSheet && m.id && ctx.openCard;
  const openFull = () => ctx.openCard(m.id, { from: opts.from || form });
  // inside the full card the foot's facts are said once, in "Where it stands", never twice
  if (footBits.length && !(large && opts.inSheet)) {
    foot = large || !canOpen
      ? h("p", { class: `card-foot dust figures${large ? " card-why" : ""}` }, footBits.join(" · "))
      : h("button", { class: "card-foot dust figures", "aria-haspopup": "dialog", title: t("card.open_full"),
        dataset: { openCard: m.id }, onclick: openFull }, footBits.join(" · "));
  }
  if (large && canOpen) {
    opener = h("p", { class: "card-open" }, h("button", { class: "link-btn card-open-btn", type: "button", "aria-haspopup": "dialog",
      dataset: { openCard: m.id }, onclick: openFull }, t("card.open_full")));
  }

  if (large) {
    if (m.stake) el.append(h("p", { class: "card-stake" }, m.stake));
    if (foot) el.append(foot);
    if (opener) el.append(opener);   // where the fold's "More about this card" was
  }

  if (m.essence && form !== "row") el.append(h("p", { class: "card-essence voice" }, m.essence));

  // options (The Deal), or the consequence once one is chosen (the Room's two-step face)
  if (large && m.options.length) {
    if (opts.chosen == null) {
      // said once: the why line already says "a yes is yours to give" on the Deal's face
      if (m.needsYes && !(large && (m.stake && m.wholeWaits ? m.reasonPlain : m.reason) === t("reason.yes"))) el.append(h("p", { class: "card-yes dust" }, t("deal.yours_to_give")));
      const list = h("div", { class: "card-options", role: "group", "aria-label": m.title });
      m.options.forEach((o, i) => {
        const b = h("button", { class: `pill option${o.suggested ? " is-suggested" : ""}`, dataset: { key: String(i + 1) },
          onclick: () => opts.oneTap ? (opts.onConfirm && opts.onConfirm(o.label, i)) : (opts.onChoose && opts.onChoose(o.label, i)) },
          h("span", { class: "option-label" }, o.label),
          o.suggested ? h("span", { class: "option-suggested" }, t("deal.suggested")) : null);
        list.append(b);
        if (o.suggested && o.reason) list.append(h("p", { class: "option-reason dust" }, o.reason));
      });
      el.append(list);
    } else {
      el.append(h("p", { class: "card-chosen" }, h("span", { class: "pill option is-suggested is-chosen", "aria-hidden": "true" }, opts.chosen)));
      el.append(h("p", { class: "card-consequence", role: "status" }, opts.consequence ||
        (m.holon && m.holon === ctx.home ? t("deal.consequence_home") : t("deal.consequence", { holon: m.holonName || t("app.you") }))));
      el.append(h("div", { class: "card-options confirm" },
        h("button", { class: "pill primary", "data-confirm": "", onclick: () => opts.onConfirm && opts.onConfirm(opts.chosen) }, t("deal.confirm_yes")),
        h("button", { class: "pill quiet", onclick: () => opts.onNotYet && opts.onNotYet() }, t("deal.confirm_not_yet"))));
    }
  }

  // the third act on a long card: give it to a body (DESIGN-BODIES §4.2); the cost is said first there
  if (large && opts.onGive && opts.chosen == null) {
    el.append(h("p", { class: "card-give" }, h("button", { class: "link-btn", onclick: () => opts.onGive(m) }, t("deal.give_body"))));
  }

  if (!large && foot) el.append(foot);
  return el;
}

function homeId(st) {
  const h0 = (st.holons || []).find((x) => x.keeper === st.actor && x.kind === "person");
  return h0 ? h0.id : null;
}
