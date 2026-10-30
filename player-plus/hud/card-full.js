// card-full.js: the full card: each thing presented is a card, and the full card opens to show
// all the detail of the card.
//
//   import { renderFullCard } from "./card-full.js";
//   const full = renderFullCard(ctx, id, { hint, acts, story });
//   sheet.append(full.el); full.load();          // load() reads the record's lines about it
//
// One component, opened by ctx.openCard(id, {from}) from every place a card is shown (the Deal,
// Threads and Mail, the Chain, the Map, the Queue, Bodies). A sheet from the bottom on a phone,
// from the right on the desk (DESIGN §4.2; the shell's sheet). It shows everything the state and
// the record hold about the thing, in this order, each section only when it has something to say:
//   1 the face (eyebrow · title · essence · the question and its options · the acts allowed)
//   2 where it stands (holder · by-when against the clock · minutes · days to spare · the chain ·
//     who waits on it · what it frees · what it waits on · what it serves · its commitments)
//   3 why it was dealt (section · the dealer's reason · what it unlocks · leverage · its place)
//   4 its stake (a pushed line's field, whose reading each value is)
//   5 its story (every line in the record about it, oldest first, signed or at the paper floor)
//   6 where it lives (its house · its id, with a copy button · as of, per record)
//   7 on paper (it prints as one sheet; print.css)
// Plain words only: no schema word reaches the screen (fixtures/test_strings.py). Data is set
// as text, never as markup. Gold is nowhere inside the sheet (card-full.css).

import { h, cardModel, renderCard, spareDays, DONE_STATES } from "./card.js";
import { actFor } from "./deal.js";
import { store, markAnswered, unmarkAnswered, agent as AGENT } from "./state.js";
import { renderAsk } from "./dock-card.js";
import { receiverPush } from "./mail.js";
import { whoOf, isElided, useStyle } from "./inks.js";

// ------------------------------------------------------------------ what is known about an id

function sightingsOf(st) {
  const s = st && st.sightings;
  if (Array.isArray(s)) return s;
  if (!s || typeof s !== "object") return [];
  return Object.values(s).flatMap((v) => (v && typeof v === "object")
    ? ["new", "held", "elevated", "folded"].flatMap((k) => (Array.isArray(v[k]) ? v[k] : [])) : []);
}

/** Everything the served state says about one id: the card, the dealt card and its place, what is
    owed, the commitments, a thread, a decision, a question, a sighting, an ask, a body. */
export function findThing(ctx, id, hint = {}) {
  const st = ctx.state || {}, R = ctx.read;
  const d = st.deal || {};
  const dealt = Array.isArray(d.cards) ? d.cards : [];
  const beyond = d.beyond && Array.isArray(d.beyond.cards) ? d.beyond.cards : [];
  let dc = dealt.find((x) => x && x.id === id) || null;
  const inHand = !!dc;
  if (!dc) dc = beyond.find((x) => x && x.id === id) || null;
  const owed = ((st.owed && st.owed.entries) || []).filter((e) => e && e.id === id);
  const commitment = (st.commitments || []).find((k) => k && k.id === id) || null;
  let card = R.card(st, id);
  if (!card && commitment && commitment.card) card = R.card(st, commitment.card);
  // a body card about giving a card to a body names the card in its id
  let body = null, bodyKind = null;
  if (typeof id === "string" && id.startsWith("body:")) {
    const rest = id.slice(5), cut = rest.lastIndexOf(":");
    if (rest.startsWith("give:")) { bodyKind = "give"; card = card || R.card(st, rest.slice(5)); }
    else if (cut > 0) { bodyKind = rest.slice(cut + 1); body = (st.bodies || []).find((b) => b && b.actor === rest.slice(0, cut)) || null; }
    else bodyKind = rest;
  }
  const handoff = owed.find((e) => e.kind === "handoff") || null;
  if (handoff && !body) body = (st.bodies || []).find((b) => b && b.handoff === id) || null;
  const commitments = (st.commitments || []).filter((k) => k && (k.id === id || (card && k.card === card.id)));
  const thread = (st.threads || []).find((x) => x && x.id === id) || null;
  const decision = (st.decisions || []).find((x) => x && x.id === id) || null;
  const question = (st.questions || []).find((x) => x && x.id === id) || null;
  const sighting = sightingsOf(st).find((x) => x && x.id === id) || null;
  const ask = ((st.hud && st.hud.agents) || []).flatMap((a) => (a && Array.isArray(a.asks) ? a.asks : [])).find((x) => x && x.id === id) || null;
  const mail = st.mail && Array.isArray(st.mail.items) ? st.mail.items.find((m) => m && (m.line_id === id || m.id === id)) || null : null;
  const holon = (dc && dc.holon) || (card && card.holon) || (owed[0] && owed[0].holon) || (thread && thread.holon)
    || (question && (question.to || question.from_holon)) || (sighting && sighting.holon) || (commitment && commitment.holon)
    || (decision && decision.holon) || (body && body.holon) || (mail && mail.holon) || hint.holon || null;
  const known = !!(card || dc || owed.length || commitment || thread || decision || question || sighting || ask || body || bodyKind || mail || hint.title);
  return { id, card, dc, inHand, owed, commitment, commitments, thread, decision, question, sighting, ask, body, bodyKind, handoff, mail, holon, known, hint };
}

// ------------------------------------------------------------------ the record's lines about an id

// a line of one of these kinds that names the thing carries its own story on: the lines that answer
// a commitment, a thread, a request or a question are the thing's story too
const CARRIES = new Set(["commit", "thread", "request", "rfg", "escalate", "kept", "decide", "offer"]);
const DIRECT_LINKS = ["answers", "anchored_to", "fulfils", "witnesses", "supersedes"];
const NEAR_LINKS = ["predecessor", "successor", "serves"];
const BODY_REFS = ["card", "about", "answers", "thread"];

function relation(l, ids) {
  if (ids.has(l.id)) return { self: true, direct: true };
  const b = l.body && typeof l.body === "object" ? l.body : {};
  for (const k of BODY_REFS) if (typeof b[k] === "string" && ids.has(b[k])) return { direct: true, by: k };
  const ln = l.links && typeof l.links === "object" ? l.links : {};
  for (const k of DIRECT_LINKS) if (Array.isArray(ln[k]) && ln[k].some((x) => ids.has(x))) return { direct: true, by: k };
  for (const k of NEAR_LINKS) if (Array.isArray(ln[k]) && ln[k].some((x) => ids.has(x))) return { direct: false, by: k };
  return null;
}

/** The lines about an id, oldest first: the line itself, every line naming it in its links or in
    its body (card · about · answers), and the lines answering a commitment, thread, request or
    question that names it. The same rule as serve.py's GET /card/<id>. */
export function linesAbout(lines, id) {
  const ids = new Set([id]);
  const out = new Map();
  const pool = (lines || []).filter((l) => l && typeof l === "object" && typeof l.id === "string");
  for (let pass = 0; pass < 4; pass++) {
    let grew = false;
    for (const l of pool) {
      if (out.has(l.id)) continue;
      const how = relation(l, ids);
      if (!how) continue;
      out.set(l.id, { line: l, how });
      if (how.direct && CARRIES.has(l.type) && !ids.has(l.id)) { ids.add(l.id); grew = true; }
    }
    if (!grew) break;
  }
  return [...out.values()].sort((a, b) => String(a.line.ts || "").localeCompare(String(b.line.ts || "")) || a.line.id.localeCompare(b.line.id));
}

/** Every line the served state carries: `lines` when present, and each card's own `lines`. */
function stateLines(st) {
  return [...(Array.isArray(st.lines) ? st.lines : []),
    ...((st.cards || []).flatMap((c) => (c && Array.isArray(c.lines) ? c.lines : [])))];
}

// ------------------------------------------------------------------ words

const up = (s) => (s ? String(s).charAt(0).toUpperCase() + String(s).slice(1) : s);
const sentence = (s) => { if (!s) return s; const x = up(String(s).trim()); return /[.?!”"]$/.test(x) ? x : x + "."; };
const label = (ctx, key) => { const s = ctx.t(key); return typeof s === "string" && s && !s.startsWith("[") ? s : null; };

function dayWords(ctx, x) {
  const d = ctx.fmt.date(x);
  return d ? d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }) : null;
}

/** The by-when against the clock: late by n days · due today · due tomorrow · in n days. */
function byWords(ctx, by, finished) {
  const t = ctx.t, f = ctx.fmt, d = f.date(by);
  if (!d) return null;
  const date = dayWords(ctx, by);
  if (finished) return t("card.full.finished", { date });
  const diff = f.daysBetween(f.now(), d);
  if (diff < 0) return diff === -1 ? t("card.full.late_one", { date }) : t("card.full.late_n", { n: f.number(-diff, true), date });
  if (diff === 0) return t("card.full.due_today", { date });
  if (diff === 1) return t("card.full.due_tomorrow", { date });
  return t("card.full.due_in_n", { date, n: f.number(diff, true) });
}

function costWords(ctx, n) {
  const t = ctx.t;
  if (typeof n !== "number" || !isFinite(n)) return null;
  if (n <= 0) return t("card.full.cost_none");
  if (n < 1000) return t("card.full.cost_few");
  if (n < 1e6) return t("card.full.cost_thousand", { n: n >= 1e5 ? Math.round(n / 1e4) * 10 : Math.round(n / 1e3) });
  const m = n / 1e6;
  return t("card.full.cost_million", { n: m >= 10 ? String(Math.round(m)) : String(Math.round(m * 10) / 10) });
}

function lineWords(l) {
  const b = l.body && typeof l.body === "object" ? l.body : {};
  for (const k of ["text", "title", "question", "answer", "decision", "note"]) {
    const v = b[k];
    if (isElided(v)) return null;
    if (typeof v === "string" && v.trim()) return v.trim().length > 140 ? v.trim().slice(0, 140) + "…" : v.trim();
  }
  return null;
}

/** What happened, in words, for one line of the thing's story. */
function didWords(ctx, l, how, id) {
  const t = ctx.t, text = lineWords(l), b = l.body && typeof l.body === "object" ? l.body : {};
  const withText = (k, plain) => (text ? t(k, { text }) : t(plain || "card.full.did.other"));
  if (!how.direct && l.type === "card") {
    const title = text ? "“" + text + "”" : t("card.not_yet_arrived");
    return t(how.by === "predecessor" ? "card.full.did.card_waits" : how.by === "successor" ? "card.full.did.card_before" : "card.full.did.card_serves", { title });
  }
  switch (l.type) {
    case "card": return t("card.full.did.card");
    case "claim": return t("card.full.did.claim");
    case "say": case "settle": return withText("card.full.did.say");
    case "commit": return b.by && dayWords(ctx, b.by) ? t("card.full.did.commit", { by: dayWords(ctx, b.by) }) : t("card.full.did.commit_plain");
    case "kept": return t("card.full.did.kept");
    case "witness": return t("card.full.did.witness");
    case "answer": return withText("card.full.did.answer", "card.full.did.answer_plain");
    case "supersede": return l.body && Object.keys(l.body).filter((k) => k !== "body_salt").length ? t("card.full.did.supersede") : t("card.full.did.retract");
    case "done": return t("card.full.did.done");
    case "release": return t("card.full.did.release");
    case "hand": return t("card.full.did.hand");
    case "request": return withText("card.full.did.request");
    case "thread": return withText("card.full.did.thread");
    case "decide": return withText("card.full.did.decide", "card.full.did.decide_plain");
    case "ratify": return t("card.full.did.ratify");
    case "rfg": return withText("card.full.did.rfg");
    case "escalate": return t("card.full.did.escalate");
    case "publish": return t("card.full.did.publish");
    case "tea": return t("card.full.did.tea", { n: ctx.fmt.number(Math.round(Number(b.minutes) || 0), true) });
    case "offer": return withText("card.full.did.offer");
    case "propose": return withText("card.full.did.propose");
    case "sight": return withText("card.full.did.sight");
    case "elevate": return t("card.full.did.elevate");
    default: return how.self || how.direct ? (text ? t("card.full.did.say", { text }) : t("card.full.did.other")) : t("card.full.did.linked");
  }
}

// ------------------------------------------------------------------ building blocks

function section(ctx, key, cls) {
  const sec = h("section", { class: `cf-sec${cls ? " " + cls : ""}`, "aria-label": ctx.t(key) });
  sec.append(h("h3", { class: "cf-label cf-sec-head" }, ctx.t(key)));
  return sec;
}
/** A list of facts: a label in small caps, its value in the text face. */
function facts() { return h("dl", { class: "cf-facts" }); }
function fact(dl, ctx, key, ...value) {
  const v = value.flat().filter((x) => x != null && x !== false && x !== "");
  if (!v.length) return;
  dl.append(h("div", { class: "cf-fact" }, h("dt", { class: "cf-label" }, ctx.t(key)), h("dd", { class: "cf-value figures" }, ...v)));
}
/** A quiet button that opens another card's full card in the same sheet. */
function cardLink(ctx, id, words) {
  return h("button", { class: "cf-link", type: "button", onclick: () => ctx.openCard(id, { from: "card" }) }, words);
}
function list(items) {
  const xs = items.filter(Boolean);
  if (!xs.length) return null;
  return xs.length === 1 ? xs[0] : h("ul", { class: "cf-list" }, xs.map((x) => h("li", null, x)));
}

// ------------------------------------------------------------------ the full card

/**
 * renderFullCard(ctx, id, {hint, acts, story, close}) -> {el, title, load()}
 *   hint:  {title, holon} from the opener, when the state may not carry the thing (a mail line)
 *   acts:  {claim(card), done(card), ask(card), answered()} from the shell (each the person's tap)
 *   story: (id) -> Promise<{ok, out: {lines}}>   GET /card/<id>, when a server is there
 */
export function renderFullCard(ctx, id, { hint = {}, acts = {}, story = null } = {}) {
  useStyle("card-full.css");
  const t = ctx.t, f = ctx.fmt, st = ctx.state || {}, R = ctx.read;
  const x = findThing(ctx, id, hint);
  const root = h("div", { class: "cf", dataset: { fullCard: id } });
  let m = null;   // the card's model, once the thing is known (provenance reads its "also in")
  const titleOf = () => (x.dc && x.dc.question) || (x.card && x.card.title) || (x.thread && x.thread.title)
    || (x.question && (isElided(x.question.question) ? t("record.hidden") : x.question.question)) || (x.sighting && x.sighting.text)
    || (x.owed[0] && x.owed[0].title) || (x.commitment && x.commitment.title) || (x.decision && x.decision.title)
    || (x.mail && (x.mail.question || x.mail.subject)) || hint.title || "";

  if (!x.known) {
    root.append(h("p", { class: "cf-unknown" }, t("card.full.unknown")));
    root.append(provenance());
    return { el: root, title: t("card.full.title"), load: () => Promise.resolve() };
  }

  const me = st.actor;
  const owedMine = x.owed.find((e) => e.holder === me) || null;
  m = cardModel(ctx, { card: x.card, deal: x.dc, owed: owedMine });
  if (!m.title) m.title = titleOf();
  const answered = store.answered.has(id) || (x.dc && x.dc.answered);
  if (answered) m.options = [];

  // 1 · the face
  const face = h("div", { class: "cf-face" });
  const kindWord = x.ask ? null : x.body || x.bodyKind ? t("card.full.body_eyebrow") : x.handoff ? t("card.full.handoff_eyebrow")
    : x.sighting ? t("card.full.sighting_eyebrow") : x.question ? t("card.full.question_eyebrow")
    : x.thread && !x.card ? t("card.full.thread_eyebrow") : m.kindLabel && !m.kindLabel.startsWith("[") ? m.kindLabel : null;
  const seen = new Set();
  // why it is here: the dealer's reason; a card someone else holds waits on them, not on you
  const other = !x.dc && !owedMine && m.holder && m.holder !== me;
  const why = other ? t("reason.on_other", { who: whoOf(ctx, m.holder, x.holon) }) : x.dc || x.card || owedMine ? m.reason : null;
  const brow = (x.ask ? [t("card.full.ask_eyebrow")] : [why, m.holonName, kindWord, m.postureLabel])
    .filter((w) => { if (!w) return false; const k = String(w).toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; });
  if (brow.length) face.append(h("p", { class: "cf-eyebrow cf-label" }, brow.join(" · ")));
  if (x.ask) {
    face.append(renderAsk(ctx, x.ask, { onAnswer: async (ans) => {
      const r = await AGENT.answer(x.ask.conversation, x.ask.id, ans);
      if (r.ok && acts.answered) acts.answered();
      return { ok: r.ok, reason: r.out && r.out.refused };
    } }));
  } else {
    face.append(renderCard(ctx, m, { form: "large", inSheet: true, oneTap: true, selected: false,
      onConfirm: (lbl, i) => answer(lbl, i) }));
  }
  // the acts the card's state allows (take it · done · ask), each the person's own tap
  const c = x.card;
  if (c && (acts.claim || acts.done || acts.ask)) {
    const row = [];
    const can = (s0) => s0.includes(c.state);
    if (acts.claim && c.holder !== me && can(["ready", "open"])) row.push(h("button", { class: "pill", type: "button", onclick: () => acts.claim(c) }, t("card.claim")));
    if (acts.done && c.holder === me && can(["ready", "open", "taken"])) row.push(h("button", { class: "pill", type: "button", onclick: () => acts.done(c) }, t("card.done")));
    if (acts.ask) row.push(h("button", { class: "pill quiet", type: "button", onclick: () => acts.ask(c) }, t("card.ask")));
    if (row.length) face.append(h("div", { class: "cf-acts actions" }, row));
  }
  root.append(face);

  // the answer from inside the sheet: the same act the Deal writes, held for Undo by the toast
  function answer(lbl, i) {
    const dc = x.dc;
    if (!dc) return;
    const a = actFor(dc, lbl);
    ctx.act(a.type, a.body, a.links, dc.holon, { confirmed: true, label: t("deal.settled_sr", { option: lbl }),
      onUndo: () => unmarkAnswered(dc.id) });
    markAnswered(dc.id);
    if (acts.answered) acts.answered();
  }

  // 2 · where it stands
  {
    const sec = section(ctx, "card.full.sec.stands"), dl = facts();
    const holder = (c && c.holder) || (owedMine && owedMine.holder) || (x.thread && x.thread.stake && x.thread.stake.holder)
      || (x.question && x.question.holder) || (x.commitment && x.commitment.keeper) || (x.decision && x.decision.holder) || null;
    if (holder) fact(dl, ctx, "card.full.l.holder", up(whoOf(ctx, holder, x.holon)));
    const finished = !!(c && (DONE_STATES.has(c.state) || c.stage === "did"));
    const by = (c && c.by) || (owedMine && owedMine.due) || (x.dc && x.dc.by) || (x.commitment && x.commitment.by)
      || (x.question && x.question.by) || (x.thread && ((x.thread.push && x.thread.push.by) || (x.thread.stake && x.thread.stake.by))) || null;
    if (by) fact(dl, ctx, "card.full.l.by", byWords(ctx, by, finished));
    const mins = m.minutes, agentMin = c && typeof c.agent_minutes === "number" ? c.agent_minutes : null;
    fact(dl, ctx, "card.full.l.minutes", list([
      mins ? ((c ? c.holder === me : !!owedMine) ? t("card.full.min_person", { about: f.aboutMinutes(mins) }) : f.aboutMinutes(mins)) : null,
      agentMin ? t("card.full.min_agent", { about: f.aboutMinutes(agentMin) }) : null]));
    const spare = c ? spareDays(ctx, c, by) : null;
    if (spare != null && spare >= 0) fact(dl, ctx, "card.full.l.spare", up(f.spare(spare)));
    if (c) {
      const ms = c.critical || c.system_critical ? leadsTo(c) : null;
      fact(dl, ctx, "card.full.l.chain", c.critical || c.system_critical || m.onPath
        ? (ms ? t("card.full.chain_to", { milestone: "“" + ms.title + "”" }) : t("card.full.chain_yes")) : t("card.full.chain_no"));
      if (m.wholeWaits) fact(dl, ctx, "card.full.l.weight", t("card.full.whole_waits"));
      else if (c.critical) fact(dl, ctx, "card.full.l.weight", t("card.full.critical"));
    }
    // who waits on it now: the holders of what it frees, and anyone in the room waiting now
    const succ = c ? (c.successors || []).map((s) => R.card(st, s)).filter((s) => s && !DONE_STATES.has(s.state)) : [];
    const waiting = [...new Set(succ.map((s) => s.holder).filter(Boolean))].map((a) => up(whoOf(ctx, a, s0holon(a, succ))));
    if (x.dc && x.dc.who_waits === "now") waiting.unshift(t("card.full.room_now"));
    if (x.question && x.question.asker && x.question.asker !== me) waiting.push(up(whoOf(ctx, x.question.asker, x.question.from_holon)));
    fact(dl, ctx, "card.full.l.waits_now", list([...new Set(waiting)]));
    // what it frees, what it waits on, what it serves
    const freesIds = c ? (c.successors || []) : x.thread ? ((x.thread.push && x.thread.push.blocks) || (x.thread.stake && x.thread.stake.blocks) || []) : [];
    fact(dl, ctx, "card.full.l.frees", list(freesIds.map((s) => {
      const k = R.card(st, s);
      if (!k) return h("span", { class: "cf-dust" }, t("card.not_yet_arrived"));
      return cardLink(ctx, s, k.holder ? t("card.full.held_by", { title: "“" + k.title + "”", who: whoOf(ctx, k.holder, k.holon) }) : "“" + k.title + "”");
    })));
    fact(dl, ctx, "card.full.l.waits_on", list((c ? c.predecessors || [] : []).map((p) => {
      const k = R.card(st, p);
      if (!k) return h("span", { class: "cf-dust" }, t("card.not_yet_arrived"));
      const doneK = DONE_STATES.has(k.state) || k.stage === "did";
      return cardLink(ctx, p, t(doneK ? "card.full.is_done" : "card.full.not_done", { title: "“" + k.title + "”" }));
    })));
    fact(dl, ctx, "card.full.l.serves", list((c ? c.serves || [] : []).map((s) => {
      const k = R.card(st, s);
      return k ? cardLink(ctx, s, "“" + k.title + "”") : h("span", { class: "cf-dust" }, t("card.not_yet_arrived"));
    })));
    // its commitments, said in words
    fact(dl, ctx, "card.full.l.commitment", list(x.commitments.map((k) => {
      const w = k.witness ? whoOf(ctx, k.witness, k.holon) : null;
      if (k.status === "kept") return t("card.full.commit_kept", { witness: w || "" });
      if (k.status === "kept-unwitnessed") return t("card.full.commit_unwitnessed", { witness: w || t("app.a_member") });
      if (k.status === "broken") return t("card.full.commit_broken");
      if (k.status === "released" || k.status === "returned") return t("card.full.commit_released");
      const who = up(whoOf(ctx, k.keeper, k.holon));
      const byk = dayWords(ctx, k.by) || "";
      return w ? t("card.full.commit_open", { who, by: byk, witness: w }) : t("card.full.commit_open_nowitness", { who, by: byk });
    })));
    // a body: its task, what it is doing now, what it has cost, and its handoff
    const b = x.body;
    if (b || x.handoff) {
      fact(dl, ctx, "card.full.l.task", (b && b.task) || (x.handoff && x.handoff.task) || null);
      if (b && b.state) fact(dl, ctx, "card.full.l.state", label(ctx, "card.full.bstate." + b.state));
      const spent = b ? ((st.cost && st.cost.by_body && st.cost.by_body[b.actor]) ?? b.cost_tokens) : null;
      if (typeof spent === "number") fact(dl, ctx, "card.full.l.cost", costWords(ctx, spent));
      if (b) fact(dl, ctx, "card.full.l.handoff", b.handoff ? (b.reviewed ? t("card.full.handoff_read") : t("card.full.handoff_waiting")) : t("card.full.handoff_none"));
      else if (x.handoff) fact(dl, ctx, "card.full.l.handoff", t("card.full.handoff_waiting"));
    }
    // an ask: when it was asked and what was said just before
    if (x.ask) {
      if (x.ask.at) fact(dl, ctx, "card.full.l.asked", t("card.full.ask_at", { when: up(f.when(x.ask.at) || ""), time: f.time(x.ask.at) || "" }));
      if (x.ask.why && x.ask.said) fact(dl, ctx, "card.full.l.context", t("card.full.ask_said", { text: x.ask.said }));
    }
    // a sighting: who saw it, when and where
    if (x.sighting) {
      const who = up(whoOf(ctx, x.sighting.actor, x.sighting.holon) || t("app.a_member"));
      fact(dl, ctx, "card.full.l.seen", x.sighting.where
        ? t("card.full.seen_by", { who, when: f.when(x.sighting.ts) || "", where: x.sighting.where })
        : t("card.full.seen_by_nowhere", { who, when: f.when(x.sighting.ts) || "" }));
    }
    // a question: who asked, and where it climbed
    if (x.question) {
      if (x.question.asker) fact(dl, ctx, "card.full.l.asked", t("card.full.asked_by", { who: up(whoOf(ctx, x.question.asker, x.question.from_holon)), when: f.when(x.question.ts) || "" }));
      const rung = x.question.rung && x.question.rung.name;
      if (x.question.from_holon && x.question.to) fact(dl, ctx, "card.full.l.climbed", t("card.full.climbed",
        { from: R.holonName(st, x.question.from_holon) || "", to: R.holonName(st, x.question.to) || "", rung: rung || "" }));
    }
    if (dl.childNodes.length) { sec.append(dl); root.append(sec); }
  }
  function s0holon(actor, cards) { const k = cards.find((y) => y.holder === actor); return k ? k.holon : x.holon; }
  function leadsTo(card) {
    const q = [...(card.successors || [])], seenIds = new Set();
    while (q.length && seenIds.size < 60) {
      const sid = q.shift();
      if (seenIds.has(sid)) continue;
      seenIds.add(sid);
      const k = R.card(st, sid);
      if (!k) continue;
      if (k.kind === "milestone") return k;
      q.push(...(k.successors || []));
    }
    return null;
  }

  // 3 · why it was dealt
  if (x.dc) {
    const dc = x.dc, sec = section(ctx, "card.full.sec.why"), dl = facts();
    fact(dl, ctx, "card.full.l.section", label(ctx, "card.full.section." + dc.section));
    if (dc.why) fact(dl, ctx, "card.full.l.reason", sentence(dc.why));
    if (typeof dc.unlocks === "string" && dc.unlocks.trim()) fact(dl, ctx, "card.full.l.unlocks", sentence(dc.unlocks));
    if (typeof dc.leverage === "number") fact(dl, ctx, "card.full.l.leverage",
      t(dc.leverage >= 8 ? "card.full.lev_high" : dc.leverage >= 3 ? "card.full.lev_mid" : "card.full.lev_low"));
    const d = st.deal || {}, dealt = d.cards || [], beyond = (d.beyond && d.beyond.cards) || [];
    if (x.inHand) fact(dl, ctx, "card.full.l.place", t("card.full.place_dealt",
      { n: f.number(dealt.indexOf(dc) + 1, true), total: f.number(dealt.length, true) }));
    else fact(dl, ctx, "card.full.l.place", t("card.full.place_beyond",
      { n: f.number(dc.n || dealt.length + beyond.indexOf(dc) + 1, true), all: f.number(dealt.length + ((d.beyond && d.beyond.count) || beyond.length), true) }));
    if (dl.childNodes.length) { sec.append(dl); root.append(sec); }
  }

  // 4 · its stake, when a pushed line carries one: each value with whose reading it is
  {
    let sent = null, by_ = null, rcv = null;
    if (x.thread && x.thread.push) { sent = x.thread.push.sent || null; by_ = x.thread.push.push_by || null; rcv = x.thread.push; }
    else if (x.mail) { const r = receiverPush(x.mail); sent = r.sent; rcv = r.rcv; by_ = (x.mail.line && x.mail.line.body && x.mail.line.body.push_by) || x.mail.push_by || null; }
    if (sent && typeof sent === "object") {
      const sec = section(ctx, "card.full.sec.stake"), dl = facts();
      const whose = (k) => h("span", { class: "cf-whose" }, " · " + (by_ && by_[k] === "person" ? t("card.full.whose_person") : t("card.full.whose_agent")));
      const theirs = (k, words) => (words ? [words, whose(k)] : null);
      fact(dl, ctx, "card.full.l.stake_by", theirs("by", sent.by ? sentence(byWords(ctx, sent.by, false) + (sent.why_by ? " " + sent.why_by : "")) : null));
      fact(dl, ctx, "card.full.l.stake_size", theirs("size", sent.size ? f.aboutMinutes(sent.size) : null));
      fact(dl, ctx, "card.full.l.stake_who", theirs("who_waits", typeof sent.who_waits === "string" ? sentence(sent.who_waits) : null));
      const reach = sent.blast_radius || sent.blast;
      fact(dl, ctx, "card.full.l.stake_reach", theirs("blast_radius", typeof reach === "string" ? sentence(reach) : null));
      fact(dl, ctx, "card.full.l.stake_late", theirs("cost_if_late", typeof sent.cost_if_late === "string" ? sentence(sent.cost_if_late) : null));
      if (typeof sent.alternatives === "string") fact(dl, ctx, "card.full.l.stake_else", sentence(sent.alternatives), h("span", { class: "cf-whose" }, " · " + t("card.full.whose_person")));
      if (sent.expires) fact(dl, ctx, "card.full.l.stake_expires", up(f.by(sent.expires) || dayWords(ctx, sent.expires) || ""), h("span", { class: "cf-whose" }, " · " + t("card.full.whose_person")));
      if (rcv && Array.isArray(rcv.blocks)) {
        const n = rcv.blocks.length;
        fact(dl, ctx, "card.full.l.stake_blocks", n === 0 ? t("card.full.blocks_none") : n === 1 ? t("card.full.blocks_one") : t("card.full.blocks_n", { n: up(f.number(n, true)) }),
          h("span", { class: "cf-whose" }, " · " + t("card.full.whose_yours")));
      }
      if (dl.childNodes.length) { sec.append(dl); root.append(sec); }
    }
  }

  // 5 · its story: filled from the state at once, then from the record when the server answers
  const storySec = section(ctx, "card.full.sec.story", "cf-story");
  const storyList = h("ol", { class: "cf-rows" });
  storySec.append(storyList);
  let storyPlaced = false;
  const placeStory = (rows) => {
    storyList.textContent = "";
    if (!rows.length) { if (storyPlaced) storySec.remove(); storyPlaced = false; return; }
    for (const { line: l, how } of rows) {
      const signed = typeof l.sig === "string" ? l.sig.length > 0 : !!l.signed;
      const when = l.ts ? t("card.full.when_at", { when: up(f.when(l.ts) || ""), time: f.time(l.ts) || "" }) : "";
      const who = isElided(l.actor) ? t("record.hidden") : up(whoOf(ctx, l.actor, l.holon) || t("app.a_member"));
      storyList.append(h("li", { class: "cf-row" },
        h("span", { class: "cf-row-when figures" }, when),
        h("span", { class: "cf-row-what" }, h("span", { class: "cf-row-who" }, who), " ", didWords(ctx, l, how, id)),
        h("span", { class: `cf-row-sig${signed ? " is-signed" : ""}` }, signed ? "✓ " + t("card.full.signed") : "○ " + t("card.full.paper_floor"))));
    }
    if (!storyPlaced) { provSec.before(storySec); storyPlaced = true; }
  };

  // 6 · where it lives
  const provSec = provenance();
  root.append(provSec);

  // 7 · on paper
  {
    const sec = section(ctx, "card.full.sec.paper", "cf-paper");
    sec.append(h("p", { class: "cf-value" }, h("button", { class: "cf-link", type: "button", onclick: printCard }, t("card.full.print")),
      h("span", { class: "cf-dust" }, " " + t("card.full.paper_note"))));
    root.append(sec);
  }

  function provenance() {
    const sec = section(ctx, "card.full.sec.provenance", "cf-prov"), dl = facts();
    const name = x.holon ? R.holonName(st, x.holon) : null;
    const pub = x.card && x.card.published_by ? R.holonName(st, x.card.published_by) : null;
    if (name) fact(dl, ctx, "card.full.l.house", pub ? t("card.full.house_published", { name, by: pub }) : name,
      m && m.alsoIn && m.alsoIn.length ? h("span", { class: "cf-dust" }, " · " + t("card.also_in", { holon: m.alsoIn.join(", ") })) : null);
    const said = h("span", { class: "cf-dust cf-copied", role: "status" });
    const idText = h("code", { class: "cf-id figures" }, id);
    const copy = h("button", { class: "cf-link cf-copy", type: "button", onclick: async () => {
      try { await navigator.clipboard.writeText(id); said.textContent = " " + t("card.full.copied"); }
      catch { said.textContent = " " + t("card.full.copy_failed"); const r = document.createRange(); r.selectNodeContents(idText); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }
    } }, t("card.full.copy"));
    fact(dl, ctx, "card.full.l.id", idText, h("span", { class: "cf-id-acts" }, copy, said));
    const rows = R.holons(st).map((y) => {
      if (!y.as_of) return null;
      const d = f.date(y.as_of.ts);
      const when = d && f.sameDay(d, f.now()) ? t("time.at", { time: f.time(y.as_of.ts) }) : f.when(y.as_of.ts);
      return t("ribbon.as_of_fold", { holon: y.name, line: f.short(y.as_of.event), when: when || "" });
    }).filter(Boolean);
    fact(dl, ctx, "card.full.l.as_of", list(rows));
    sec.append(dl);
    return sec;
  }

  function printCard() {
    const r = document.documentElement;
    r.dataset.print = "card";
    const done = () => { if (r.dataset.print === "card") delete r.dataset.print; removeEventListener("afterprint", done); };
    addEventListener("afterprint", done);
    print();
  }

  async function load() {
    const pool = stateLines(st);
    placeStory(linesAbout(pool, id));
    if (typeof story !== "function") return;
    let r = null;
    try { r = await story(id); } catch { r = null; }
    const got = r && r.ok && r.out && Array.isArray(r.out.lines) ? r.out.lines : [];
    if (!got.length || !root.isConnected) return;
    const byId = new Map(pool.map((l) => [l && l.id, l]));
    for (const l of got) if (l && l.id && !byId.has(l.id)) byId.set(l.id, l);
    placeStory(linesAbout([...byId.values()], id));
  }

  return { el: root, title: t("card.full.title"), load };
}
