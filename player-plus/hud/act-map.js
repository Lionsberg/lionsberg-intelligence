// act-map.js: one card, everywhere: the one act map. The line an act writes, for every place a card
// is shown (the Deal, the full card, the Room's deal sheet, the Talk, the Table, the Talk place, the
// Wall, Threads and Mail, Bodies, the Ledger, the dock). It reads the engine's `offers` first (each
// option's act, the line it writes, and whether it is the reader's); a card with no offers falls back
// to the act its option's place names (card.js fallbackKey) and writes the line that act writes below,
// as the registry's targets give it (types.json): the same line offers would carry. Pure: it touches
// no browser global at load, so a proof in node loads it alone; deal.js exports it under its old name.

import { optionAct, isOver, WORD_FIELDS, filledHere } from "./card.js";

const ID = (x) => (typeof x === "string" && x ? x : null);
const LINES = {
  "act.answer.accept": (id) => ({ type: "answer", body: { answer: "accept" }, links: { answers: [id] } }),
  "act.answer.decline": (id) => ({ type: "answer", body: { answer: "decline" }, links: { answers: [id] } }),
  "act.ratify": (id) => ({ type: "ratify", body: {}, links: { answers: [id] } }),
  "act.decide": (id) => ({ type: "decide", body: { text: null }, links: { answers: [id] } }),
  "act.kept": (id) => ({ type: "kept", body: { commitment: id }, links: {} }),
  "act.witness": (id) => ({ type: "witness", body: {}, links: id ? { witnesses: [id] } : {} }),
  "act.release": (id, kind) => ({ type: "release", body: kind === "commitment" ? { commitment: id } : { card: id }, links: {} }),
  "act.settle": (id) => ({ type: "settle", body: { text: null }, links: id ? { anchored_to: [id] } : {} }),   // a line said in a room has no item to name
  "act.claim": (id) => ({ type: "claim", body: { card: id }, links: {} }),
  "act.done": (id) => ({ type: "done", body: { card: id }, links: {} }),
  "act.hand": (id) => ({ type: "hand", body: { card: id, to: null }, links: {} }),
  "act.elevate": (id) => ({ type: "elevate", body: { what: id, to: null }, links: {} }),   // its `to` is the state's (filledHere)
  "act.say": (id) => ({ type: "say", body: { text: null }, links: { anchored_to: [id] } }),
  "act.say.ask": (id) => ({ type: "say", body: { text: null, intent: "ask" }, links: { anchored_to: [id] } }),
};
const WORDED = new Set(["say", "decide", "settle"]);   // the line types whose text is words
// the acts whose line may name no item: a witness that carries its handoff in its body, a room's agreement
const NO_ITEM = new Set(["act.witness", "act.settle"]);

const copy = (x) => JSON.parse(JSON.stringify(x));

/** The words a worded line carries when the person gave none: a close keeps the conversation's own
    title, a decision the proposal's own words, anything else the option's words. */
function wordsFor(line, dc, option, st) {
  const id = dc && dc.id;
  if (line.type === "settle") {
    const th = ((st && st.threads) || []).find((x) => x && x.id === id);
    return (th && th.title) || dc.title || option || dc.question || "";
  }
  if (line.type === "decide") {
    const d = ((st && st.decisions) || []).find((x) => x && x.id === id);
    return (d && (d.proposal || d.text || d.decision || d.title)) || option || dc.question || "";
  }
  return option || dc.title || dc.question || "";
}

/**
 * actFor(dc, choice, words, st) -> {type, body, links} | null
 *   dc      the card: a dealt card (its options and `offers`), or any thing with an id and a kind
 *   choice  one of dc.options (the engine's own word), its place, or an act key ("act.settle")
 *   words   the person's own words for a worded line (a reply, a question, a change); else the
 *           option's words, as the engine says (offers' needs_words)
 *   st      the served state, for the fallback's reading of whose commitment it is
 * null: the choice writes nothing (a "Not now", or an act that is not the reader's). A line the
 * HUD cannot complete (it names someone the person has not named) is written as the option's words,
 * a say on the card, for the agent to carry out.
 */
export function actFor(dc, choice, words = null, st = null) {
  if (!dc || !ID(dc.id) && !NO_ITEM.has(choice)) return null;   // a line names its item, never [null]
  const opts = Array.isArray(dc.options) ? dc.options : [];
  const i = Number.isInteger(choice) ? choice : opts.indexOf(choice);
  const option = i >= 0 && i < opts.length ? opts[i] : null;
  const kind = (dc.offers && dc.offers.kind) || dc.kind || null;
  let line = null;
  if (option == null) {
    if (typeof choice !== "string" || !choice.startsWith("act.")) return null;
    // with the engine's offers, an act it does not offer this reader is refused, never written
    const offered = dc.offers && Array.isArray(dc.offers.acts) ? dc.offers.acts : null;
    const a = offered ? offered.find((x) => x && x.key === choice) : null;
    if (offered && !a) return null;
    line = a && a.writes ? copy(a.writes) : LINES[choice] ? LINES[choice](ID(dc.id), kind, dc, st) : null;
  } else {
    if (Array.isArray(dc.acts) && dc.acts[i] && typeof dc.acts[i] === "object" && dc.acts[i].type && !dc.offers) return copy(dc.acts[i]);
    const o = optionAct(dc, i, st);
    if (!o.offered || !o.key) return null;
    line = o.row && o.row.writes ? copy(o.row.writes) : LINES[o.key] ? LINES[o.key](dc.id, kind, dc, st) : null;
    if (line && !o.row && line.type === "decide" && line.body && line.body.text == null) line.body.text = option;   // its own words are the decision
  }
  if (!line || typeof line.type !== "string") return null;
  line.body = line.body && typeof line.body === "object" ? line.body : {};
  line.links = line.links && typeof line.links === "object" ? line.links : {};
  // a field the state names (where a pass goes: the wider circle), filled here, never asked of her
  for (const [k, v] of Object.entries(line.body)) if (v === null && filledHere(line.type, k, dc, st)) line.body[k] = filledHere(line.type, k, dc, st);
  if (Object.entries(line.body).some(([k, v]) => !WORD_FIELDS.includes(k) && v === null)) {
    line = LINES["act.say"](ID(dc.id));   // it names someone not named here: her words, for the agent to carry out
    if (option == null) return null;
  }
  const said = typeof words === "string" ? words.normalize("NFC").trim() : "";
  if (WORDED.has(line.type) && (line.body.text == null || said)) line.body.text = said || wordsFor(line, dc, option, st);
  if (said && line.type === "say") line.body.voice = "human-words";   // her own words, so said (types.json say voice)
  // a why or a note left for her: her words, else the option's own (a voice or an agent's path)
  for (const k of WORD_FIELDS) if (k !== "text" && k in line.body && line.body[k] === null) line.body[k] = said || option || "";
  return receiptDraft(dc, line, said) || line;
}

/** A receipt card's "Ask again": the engine's own drafted line (dc.draft, addressed to the one who
    has not said they have it), with the person's words where she gave them. */
function receiptDraft(dc, line, said) {
  const d = dc && dc.kind === "receipt" && dc.draft && typeof dc.draft === "object" ? dc.draft : null;
  if (!d || line.type !== "say" || d.type !== "say" || line.body.intent) return null;
  const out = { type: "say", body: { ...copy(d.body || {}) }, links: copy(d.links || {}) };
  if (said) out.body.text = said;
  return out;
}

const LOCAL_UNDO_MS = 5000;   // the bar's five seconds of Undo (the header), for an answer that writes nothing

/** Write what actFor gave through the one act path (ctx.act); a choice that writes nothing is held
    on this device alone, with the same Undo, so every gesture reads the same way. */
export function writeLine(ctx, line, holon, opts = {}) {
  if (line) return ctx.act(line.type, line.body, line.links, holon, opts);
  let status = "holding", resolve = null, timer = null;
  const p = {
    get status() { return status; },
    done: new Promise((r) => { resolve = r; }),
    undo() { if (status !== "holding") return; status = "undone"; clearTimeout(timer); if (opts.onUndo) opts.onUndo(); resolve(p); },
  };
  timer = setTimeout(() => { if (status === "holding") { status = "kept-here"; resolve(p); } }, opts.undo_ms || (ctx.prefs && ctx.prefs.undo_ms) || LOCAL_UNDO_MS);
  if (timer && typeof timer.unref === "function") timer.unref();
  return p;
}

// The registry's `from` for taking a card (types.json claim, kind card); Done has none (any state).
export const TAKE_FROM = ["ready", "open", "released", "returned"];

/** Take it and Done, under one rule for every place (the full card, the Wall): with the Deal's
    `offers` for the card, what they offer; else the registry's states. Take it is for a card
    another holds or no one holds; Done for the card in your hands; neither on a finished card.
    A released or returned card is free again, so Take it is offered on it, as the registry allows.
    -> [{key, means, type, line}] (key and means are strings.json keys, the words of acts.json). */
export function cardActs(st, card, dc = null) {
  const me = st && st.actor;
  if (!me || !card || !ID(card.id) || isOver(card)) return [];   // no reader named: nothing is hers to take
  const acts = dc && dc.offers && Array.isArray(dc.offers.acts) && Array.isArray(dc.offers.options) ? dc.offers.acts : null;
  const has = (k) => acts.some((a) => a && a.key === k);
  const out = [];
  const thing = { id: card.id, kind: "card", offers: dc && dc.offers };
  // with offers, as the engine offers it (a ready card in her own hands is taken up); without, a card
  // another holds or no one holds, in the registry's `from`
  if (acts ? has("act.claim") : card.holder !== me && TAKE_FROM.includes(card.state))
    out.push({ key: "act.claim", means: "act.claim_means", type: "claim", line: actFor(thing, "act.claim", null, st) });
  if (card.holder === me && (acts ? has("act.done") : true))
    out.push({ key: "act.done", means: "act.done_means", type: "done", line: actFor(thing, "act.done", null, st) });
  return out.filter((x) => x.line);
}

/** The line a person's Agree writes on what her agent offered in the margin (DESIGN-DOCK §2.5): a word said
    in the room is the one map's say; a commitment drafted on a card and a new card have no act in acts.json
    yet (commit, card), so they are written here as the registry's own lines, the one place they are made. */
export function offeredLine(it, st = null) {
  if (!it || typeof it !== "object" || typeof it.text !== "string" || !it.text.trim()) return null;
  if (it.kind === "said_in_room") return { type: "say", body: { text: it.text.normalize("NFC").trim(), voice: "human-words" }, links: {} };
  if (it.kind === "commitment" && ID(it.card)) return { type: "commit", body: { card: it.card, by: it.by }, links: {} };
  return { type: "card", body: { title: it.text, holder: st && st.actor, by: it.by }, links: {} };
}
