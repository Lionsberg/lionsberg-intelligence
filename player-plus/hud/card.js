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
/** A card that is finished or taken back: it allows no act. A released or returned card is not over:
    it is free again for someone to take (types.json claim, from released and returned). */
const OVER = new Set(["done", "kept", "declined", "retracted"]);
export const isOver = (card) => !!(card && (OVER.has(card.state) || card.stage === "did"));

// ------------------------------------------------------------------ one card, everywhere: its acts

/** An act's words from strings.json, which mirrors the engine's acts.json under the same keys
    (act.<type>[.<when>]): the label is the key, its meaning the key with _means, and a kind's own
    words sit under .on_<kind>, and a role's own under .on_<kind>.as_<role> (the same act read from the
    other side of a commitment). A key with no words gives nulls, never a guess. */
export function actWords(ctx, key, kind = null, role = null) {
  const has = (k) => { const s = ctx.t(k); return typeof s === "string" && s !== "[" + k + "]"; };
  if (typeof key !== "string" || !key) return { label: null, meaning: null };
  const byRole = kind && role ? key + ".on_" + kind + ".as_" + role : null;
  const k0 = byRole && has(byRole) ? byRole : kind && has(key + ".on_" + kind) ? key + ".on_" + kind : key;
  return { label: has(k0) ? ctx.t(k0) : null, meaning: has(k0 + "_means") ? ctx.t(k0 + "_means") : null };
}

// What a Deal card's option writes when the engine sent no `offers` (an older Deal, or a fixture): the
// act key by the card's kind and the option's place, as the engine's own frames place them (deal.py:
// the option words stay the card's, the line is the act's). null: the option writes nothing.
const FALLBACK_KEYS = {
  request: ["act.answer.accept", "act.say", "act.answer.decline"],
  offer: ["act.answer.accept", "act.say.ask", "act.answer.decline"],
  ratify: ["act.ratify", null, "act.say.ask"],
  thread: ["act.say", "act.settle", null],
  pain: ["act.say", "act.say", null],
  sighting: ["act.elevate", null, null],
  receipt: ["act.say", null],
  claim: ["act.claim", "act.release"],
  committor: ["act.kept", "act.say.ask", "act.release"],
  committor_on_track: ["act.say", "act.say.ask", "act.release"],
  committee: ["act.say", "act.say.ask", "act.answer.decline"],
  ready: ["act.claim", "act.hand", "act.release"],
  taken: ["act.done", "act.hand", "act.release"],
};

/** The fallback act key of a dealt card's option at place i (no `offers`): the engine's old `acts`
    (a type name per option, the last writing none) first; then the frames above; a kind the frames
    do not name writes the option's own words as a say. */
export function fallbackKey(dc, i, st = null) {
  const opts = (dc && Array.isArray(dc.options)) ? dc.options : [];
  if (!dc || !Number.isInteger(i) || i < 0 || i >= opts.length) return null;
  if (Array.isArray(dc.acts) && i < dc.acts.length) {
    const a = dc.acts[i];
    if (a === null) return null;
    if (typeof a === "string") return "act." + a;
  }
  const me = st && st.actor;
  let row = FALLBACK_KEYS[dc.kind] || null;
  if (dc.kind === "commitment") {
    const k = ((st && st.commitments) || []).find((x) => x && x.id === dc.id) || {};
    const owed = ((st && st.owed && st.owed.entries) || []).find((e) => e && e.id === dc.id && e.holder === me) || {};
    row = k.committee && k.committee === me ? FALLBACK_KEYS.committee
      : owed.status === "past" ? FALLBACK_KEYS.committor : FALLBACK_KEYS.committor_on_track;
  } else if (dc.section === "ready") {
    const c = ((st && st.cards) || []).find((x) => x && x.id === dc.id);
    row = c && c.state === "taken" && c.holder === me ? FALLBACK_KEYS.taken : FALLBACK_KEYS.ready;
  } else if (dc.kind === "decide" || dc.section === "decision") {
    if (!row) return i < opts.length - 1 ? "act.decide" : null;   // each choice is a decision in its words; the last hands it on
  }
  if (!row) return "act.say";
  return i < row.length ? row[i] : null;
}

// The body fields a person fills with her own words (types.json: a field of kind text); any other field
// left empty names someone or something she has not named here.
export const WORD_FIELDS = ["text", "why", "note"];

/** A field the engine leaves for the HUD to name from the state, never asked of her: where a pass goes
    (elevate's `to`) is the wider circle around the card's group, its holon's parent. null: not known here. */
export function filledHere(type, field, dc, st) {
  if (type !== "elevate" || field !== "to") return null;
  const x = ((st && st.holons) || []).find((y) => y && dc && y.id === dc.holon);
  return x && typeof x.parent === "string" && x.parent ? x.parent : null;
}

/** What a dealt card's option at place i does, read from the engine's `offers` first: its act key,
    whether it is the reader's to take (`offered`), the engine's row, and whether its line carries
    the option's own words (a say, a decision in its words, or a line the HUD cannot complete). */
export function optionAct(dc, i, st = null) {
  const opts = (dc && Array.isArray(dc.options)) ? dc.options : [];
  const option = Number.isInteger(i) && i >= 0 && i < opts.length ? opts[i] : null;
  const offers = dc && dc.offers && typeof dc.offers === "object" && Array.isArray(dc.offers.options) ? dc.offers : null;
  if (option == null) return { option: null, i, key: null, kind: null, row: null, offered: false, own: true };
  if (!offers) return { option, i, key: fallbackKey(dc, i, st), kind: null, row: null, offered: true, own: true };
  const rows = offers.options;
  const row = (rows[i] && rows[i].option === option) ? rows[i] : rows.find((r) => r && r.option === option) || null;
  const kind = typeof offers.kind === "string" ? offers.kind : null;
  if (!row || !row.key) return { option, i, key: null, kind, row, offered: true, own: true };
  if (!row.offered || !row.writes) return { option, i, key: row.key, kind, row, offered: false, own: true };
  const body = row.writes.body && typeof row.writes.body === "object" ? row.writes.body : {};
  // a field left for her: her words (text, why, note), or someone she must name (to): then it is asked for
  const open = Object.entries(body).some(([k, v]) => !WORD_FIELDS.includes(k) && v === null && !filledHere(row.writes.type, k, dc, st));
  const own = open || row.writes.type === "say" || (row.writes.type === "decide" && body.text === option);
  return { option, i, key: open ? "act.say" : row.key, kind, role: typeof offers.role === "string" ? offers.role : null, row, offered: true, own, asked: open,
    words: open || !!row.needs_words || Object.entries(body).some(([k, v]) => WORD_FIELDS.includes(k) && k !== "text" && v === null) };
}

/** The acts a dealt card's options offer this reader, drawn: the reader's only (an option the
    engine says is the other side's is not drawn), each with its label (the act's words, or the
    option's own when its line carries them) and its meaning. */
export function optionsOf(ctx, dc) {
  if (!dc || !Array.isArray(dc.options)) return [];
  const out = [];
  dc.options.forEach((label, i) => {
    const o = optionAct(dc, i, ctx.state);
    if (o.offered === false) return;
    const w = o.key && !o.asked ? actWords(ctx, o.key, o.kind || dc.kind, o.role) : { label: null, meaning: null };
    const shown = o.own || !w.label ? label : w.label;
    out.push({ label: shown, option: label, i, key: o.key, meaning: meaningOf(ctx, o, shown, w.meaning),
      words: !!o.words, suggested: !!(dc.recommendation && label === dc.recommendation),
      reason: dc.recommendation && label === dc.recommendation ? dc.why : null });
  });
  return out;
}

/** One meaning per drawn act, never a generic shared by two: the act's own words from acts.json, and
    where the line carries the option's words (a say, a decision in its words) or asks for hers, those
    words named in it; a choice that writes nothing says so by its own name. */
function meaningOf(ctx, o, option, actMeaning) {
  const t = ctx.t;
  const type = o.row && o.row.writes ? o.row.writes.type : (o.key || "").split(".")[1];
  if (o.asked) return t("act.asked_means", { option });
  if (!o.key) return t("act.none_option_means", { option });
  if (o.words && o.key === "act.say.ask") return t("act.say.ask.yours_means", { option });
  if (o.words && type === "say") return t("act.say.yours_means", { option });
  if (o.words) return t("act.words_means", { option, means: actMeaning || "" }).trim();
  if (o.own && type === "say") return t("act.say.words_means", { words: option });
  if (o.own && type === "decide") return t("act.decide.words_means", { words: option });
  return actMeaning || t("act.none_option_means", { option });
}

/** "What these mean": the fold beside a row of acts, since a phone has no hover. pairs: [[label, meaning]]. */
export function actsFold(ctx, pairs, cls = "acts-fold") {
  const xs = (pairs || []).filter((p) => p && p[0] && p[1]);
  if (!xs.length) return null;
  return h("details", { class: cls }, h("summary", { class: "cf-label" }, ctx.t("card.say_fold_title")),
    h("ul", { class: "cf-list" }, xs.map(([a, m]) => h("li", null, ctx.t("card.say_fold_line", { act: a, means: m })))));
}

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
  // the stake takes the engine's clause whole: a clause that is itself a sentence ("nothing waits on it
  // yet") is said as one, never folded into "... waits on this"
  const stake = !unlocks ? null : /^nothing\b/i.test(unlocks) ? t("deal.stake_none", { what: unlocks.charAt(0).toUpperCase() + unlocks.slice(1) })
    : t(wholeWaits ? "deal.stake_whole" : "deal.stake",
      { what: unlocks.charAt(0).toUpperCase() + unlocks.slice(1), what_lower: unlocks.charAt(0).toLowerCase() + unlocks.slice(1), holon: forWhom || "" });
  // the plain reason (the Deal's face, where the stake line already says the whole waits); the
  // other faces keep "the whole is waiting on this" as their reason
  const reasonPlain = t(reasonKey, reasonVars);
  if (wholeWaits) { reasonKey = "reason.system"; reasonVars = null; }
  const kind = (card && card.kind) || (deal && deal.kind && deal.kind !== "decide" ? deal.kind : null) || (deal && deal.section === "decision" ? "decision" : null) || (owed && owed.kind) || null;

  // the acts its options offer this reader, each with its words and meaning (optionsOf, from `offers`)
  const options = deal ? optionsOf(ctx, deal) : [];

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
 *   form: "large" (The Deal) · "compact" (the Board, the Map) · "row" (the Queue) · "station" (the
 *         Chain's road) · "sticky" (the Wall): the last two the one face inside a place of another shape
 *   index, total: for "1 of 3"
 *   chosen: the option label chosen (shows the consequence)
 *   onChoose(option, i, label), onConfirm(option, i, label), onNotYet(), onOpen(): the view's handlers;
 *   option is the engine's own word (what actFor reads), label the word drawn, i its place
 *   selected: true when the shell's selected card is this one
 */
export function renderCard(ctx, m, opts = {}) {
  const t = ctx.t, f = ctx.fmt, st = ctx.state;
  const form = opts.form || "compact";
  if (form === "station" || form === "sticky") return slimFace(ctx, m, form, opts);
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
    el.append(h("button", { class: "card-row-open", "aria-haspopup": "dialog", title: t("card.open_full_means"), onclick: () => opts.onOpen(m) }, title));
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
      : h("button", { class: "card-foot dust figures", "aria-haspopup": "dialog", title: t("card.open_full_means"),
        dataset: { openCard: m.id }, onclick: openFull }, footBits.join(" · "));
  }
  if (large && canOpen) {
    opener = h("p", { class: "card-open" }, h("button", { class: "link-btn card-open-btn", type: "button", "aria-haspopup": "dialog",
      title: t("card.open_full_means"), dataset: { openCard: m.id }, onclick: openFull }, t("card.open_full")));
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
      // an act whose line carries her own words asks for them first, then writes them (offers' needs_words)
      let box = null;
      const ask = (o) => {
        if (box) box.remove();
        const area = h("textarea", { class: "fixed-input card-words-input", rows: "2", "aria-label": t("card.words_label", { option: o.label }), placeholder: t("card.words_placeholder") });
        const send = () => { const w = area.value.trim(); if (!w) { area.focus(); return; } box.remove(); box = null; opts.onConfirm && opts.onConfirm(o.option, o.i, o.label, w); };
        box = h("div", { class: "card-words" }, h("p", { class: "dust" }, t("card.words_for", { option: o.label })), area,
          h("div", { class: "card-options confirm" }, h("button", { class: "pill primary", title: o.meaning, onclick: send }, t("card.words_send")),
            h("button", { class: "pill quiet", title: t("card.words_cancel_means"), onclick: () => { box.remove(); box = null; } }, t("card.words_cancel"))));
        list.after ? list.after(box) : el.append(box);
        if (area.focus) area.focus();
      };
      // each act says what it does: its meaning on hover, and on the face (the suggested one beneath it,
      // the rest in the fold beside them), since a phone has no hover
      m.options.forEach((o, n) => {
        const b = h("button", { class: `pill option${o.suggested ? " is-suggested" : ""}`, dataset: { key: String(n + 1), act: o.key || "" }, title: o.meaning,
          onclick: () => opts.oneTap ? (o.words ? ask(o) : opts.onConfirm && opts.onConfirm(o.option, o.i, o.label)) : (opts.onChoose && opts.onChoose(o.option, o.i, o.label)) },
          h("span", { class: "option-label" }, o.label),
          o.suggested ? h("span", { class: "option-suggested" }, t("deal.suggested")) : null);
        list.append(b);
        if (o.suggested) list.append(h("p", { class: "option-reason dust" }, [o.reason, o.meaning].filter(Boolean).join(". ")));
      });
      el.append(list);
    } else {
      const ch = m.options.find((o) => o.option === opts.chosen) || { option: opts.chosen, i: -1, label: opts.chosen, meaning: null };
      el.append(h("p", { class: "card-chosen" }, h("span", { class: "pill option is-suggested is-chosen", "aria-hidden": "true", title: ch.meaning }, ch.label)));
      el.append(h("p", { class: "card-consequence", role: "status" }, opts.consequence || ch.meaning ||
        (m.holon && m.holon === ctx.home ? t("deal.consequence_home") : t("deal.consequence", { holon: m.holonName || t("app.you") }))));
      // her words first, where the chosen act carries them; then "Yes, I will" writes them
      const area = ch.words ? h("textarea", { class: "fixed-input card-words-input", rows: "2", "aria-label": t("card.words_label", { option: ch.label }), placeholder: t("card.words_placeholder") }) : null;
      if (area) el.append(h("p", { class: "dust" }, t("card.words_for", { option: ch.label })), area);
      const yes = () => { const w = area ? area.value.trim() : null; if (area && !w) { area.focus(); return; } opts.onConfirm && opts.onConfirm(ch.option, ch.i, ch.label, w); };
      el.append(h("div", { class: "card-options confirm" },
        h("button", { class: "pill primary", "data-confirm": "", title: t("deal.confirm_yes_means"), onclick: yes }, t("deal.confirm_yes")),
        h("button", { class: "pill quiet", title: t("deal.confirm_not_yet_means"), onclick: () => opts.onNotYet && opts.onNotYet() }, t("deal.confirm_not_yet"))),
        actsFold(ctx, [[t("deal.confirm_yes"), t("deal.confirm_yes_means")], [t("deal.confirm_not_yet"), t("deal.confirm_not_yet_means")]], "card-means"));
    }
  }

  // the third act on a long card: give it to a body (DESIGN-BODIES §4.2); the cost is said first there
  if (large && opts.onGive && opts.chosen == null) {
    el.append(h("p", { class: "card-give" }, h("button", { class: "link-btn", title: t("deal.give_body_means"), onclick: () => opts.onGive(m) }, t("deal.give_body"))));
  }
  // "What these mean", beside the acts drawn on the face (a phone has no hover)
  if (large && opts.chosen == null) {
    // the fold holds only the acts not explained on the face already (the suggested one says its meaning beneath it)
    const fold = actsFold(ctx, [...m.options.filter((o) => !o.suggested).map((o) => [o.label, o.meaning]), opts.onGive ? [t("deal.give_body"), t("deal.give_body_means")] : null], "card-means");
    if (fold) el.append(fold);
  }

  if (!large && foot) el.append(foot);
  return el;
}

/** The one face inside a place of another shape: a station on the Chain's road, a sticky on the
    Wall. The place wraps it and never redraws it. The face is the card's title (on a station, the
    button that opens the full card: opts.onOpen) and, on a sticky, its holder and days to spare in
    the face's own words; a sticky's wrapper is the place's button, so nothing in it is a button. */
function slimFace(ctx, m, form, opts) {
  const t = ctx.t, f = ctx.fmt, st = ctx.state;
  const el = h("article", { class: `card card--${form}${opts.selected ? " is-selected" : ""}`, dataset: { card: m.id || "" } });
  const cls = ["card-title", opts.titleClass, m.ink ? "ink-" + m.ink : null].filter(Boolean).join(" ");
  el.append(form === "station" && opts.onOpen
    ? h("button", { class: cls, type: "button", "aria-haspopup": "dialog", title: t("card.open_full_means"), dataset: { openCard: m.id || "" },
      onclick: () => opts.onOpen(m) }, m.title)
    : h("span", { class: cls }, m.title));
  if (form === "sticky") {
    const bits = [m.holder ? (m.holder === st.actor ? t("card.holder_you") : t("card.holder", { holder: ctx.read.who(st, m.holder, m.holon) })) : null,
      m.spare != null ? f.spare(m.spare) : null].filter(Boolean);
    if (bits.length) el.append(h("span", { class: "card-foot dust figures" }, bits.join(" · ")));
  }
  return el;
}

function homeId(st) {
  const h0 = (st.holons || []).find((x) => x.keeper === st.actor && x.kind === "person");
  return h0 ? h0.id : null;
}
