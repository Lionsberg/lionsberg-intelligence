// threads.js: Threads and Mail.
// The person's goal here: who is waiting on me, what rides on it, and who is waiting on whom.
// Fixed frame: one sentence · Waiting on you (Conversation Cards, by the receiver's weight) ·
// You are waiting on (one quiet line each) · one foot word that regroups the same cards by house
// (one order: by turn; no sort word). Each card: from whom, where, how it arrived · the question · what
// rides on it in one sentence from the receiver's own record · their hope in their words · their
// record in words · one line to answer and Send · beneath it, what rides on the answer as the
// agent's reading, editable in place ("yours" once changed) · More, a sheet for the rare case.
//
// Reads STATE `threads[]` ({.., stake, push}), `questions[]`, `mail.items`, `lines` (when the
// state carries them), `calibration`. A fact the state does not carry is not said.

import { h } from "./card.js";
import { createComposer } from "./push.js";
import { arrivedWords, receiverPush } from "./mail.js";
import { useStyle, local, lineById, lineText, whoOf, isElided } from "./inks.js";

const FIELD = "art/l-person-flow-a.jpg";
const READ_AFTER_MS = 1500;

// ------------------------------------------------------------------ reading the state

function ourActors(st) {
  const me = st.actor;
  const agents = new Set((st.actors || []).filter((a) => a.kind === "agent" && a.for === me).map((a) => a.id));
  return (x) => x === me || agents.has(x);
}
function homeOf(ctx) {
  const st = ctx.state;
  return ctx.home || ((st.holons || []).find((x) => x.kind === "person" && x.keeper === st.actor) || {}).id;
}

/** Lines from other houses to the wearer or her agent, when the state carries line bodies. */
export function fromOtherHouses(ctx) {
  const st = ctx.state, ours = ourActors(st), home = homeOf(ctx);
  return (Array.isArray(st.lines) ? st.lines : []).filter((l) => l && l.holon !== home && typeof l.actor === "string"
    && !ours(l.actor) && (ours(l.for) || (l.body && ours(l.body.to))));
}

function answeredByUs(st, id, ours) {
  return (Array.isArray(st.lines) ? st.lines : []).some((l) => l && ours(l.actor) && l.links
    && [].concat(l.links.answers || [], l.links.anchored_to || []).includes(id));
}

/** A mail subject as the card's question: its by-when is said in the card's own words below. */
function plainSubject(x) { return typeof x === "string" ? x.replace(/\s*·\s*by\s+\d{4}-\d{2}-\d{2}\s*$/, "").trim() : ""; }

/** Every open conversation that touches the wearer: {mine: [...], theirs: [...]}. */
export function conversations(ctx) {
  const st = ctx.state, ours = ourActors(st), home = homeOf(ctx);
  const byId = new Map();
  const put = (x) => {
    const was = byId.get(x.id);
    byId.set(x.id, was ? { ...was, ...Object.fromEntries(Object.entries(x).filter(([, v]) => v != null)) } : x);
  };

  for (const th of st.threads || []) {
    if (!th || th.settled) continue;
    const to = th.to || [];
    const sk = th.stake || {}, p = th.push || null;
    const holder = "holder" in sk ? sk.holder : (ours(th.last_actor) ? to[0] || null : st.actor);
    const touches = to.some(ours) || ours(th.last_actor) || ours(holder);
    if (!touches || (p && p.state === "retracted")) continue;
    put({ id: th.id, kind: "thread", holon: th.holon, title: th.title,
      about: Array.isArray(th.anchored_to) ? th.anchored_to[0] : th.anchored_to,
      ts: th.last_ts, from: th.last_actor, holder, mine: !!holder && ours(holder) && !ours(th.last_actor),
      by: (p && p.by) || sk.by || null, why_by: (p && p.why_by) || null,
      blocks: p && Array.isArray(p.blocks) ? p.blocks : Array.isArray(sk.blocks) ? sk.blocks : null,
      critical: p && p.critical != null ? !!p.critical : sk.critical != null ? !!sk.critical : null,
      hope: sk.urgency || (p && p.sent && p.sent.asked) || null, weight: p && typeof p.weight === "number" ? p.weight : null,
      cal: p ? p.calibration : null, sent: p ? p.sent : null, push_by: p ? p.push_by : null,
      toAgent: to.some((x) => x !== st.actor && ours(x)), other: th.holon !== home && !ours(th.last_actor), lineId: th.id });
  }
  for (const q of st.questions || []) {
    if (!q || !(q.state === "open" || q.state === "climbed")) continue;
    if (q.holder !== st.actor && q.asker !== st.actor) continue;
    put({ id: q.id, kind: "question", holon: q.to || q.from_holon, title: isElided(q.question) ? ctx.t("record.hidden") : q.question,
      about: q.about, ts: q.ts, from: q.asker, holder: q.holder, mine: q.holder === st.actor, by: q.by || null,
      blocks: null, critical: null, hope: null, other: false, lineId: q.id });
  }
  const items = st.mail && Array.isArray(st.mail.items) ? st.mail.items : [];
  for (const m of items) {
    if (!m || m.withdrawn || m.kind === "bad") continue;
    if (m.line_id && answeredByUs(st, m.line_id, ours)) continue;
    const { sent, rcv } = receiverPush(m);
    put({ id: m.line_id || m.id, kind: m.kind === "prose" ? "prose" : "mail", mailId: m.id, holon: m.holon,
      title: m.question || plainSubject(m.subject) || (m.prose ? String(m.prose).split("\n")[0] : ""),
      about: m.card || null, ts: m.ts || m.received_at, from: m.from_actor, fromRole: m.from_role || null, fromHouse: m.from_house || null,
      holder: st.actor, mine: true, by: (rcv && rcv.by) || (sent && sent.by) || null, why_by: (rcv && rcv.why_by) || (sent && sent.why_by) || null,
      blocks: rcv && Array.isArray(rcv.blocks) ? rcv.blocks : null, critical: rcv && rcv.critical != null ? !!rcv.critical : null,
      hope: sent && sent.asked ? sent.asked : null, weight: rcv && typeof rcv.weight === "number" ? rcv.weight : null,
      cal: (rcv && rcv.calibration) || null, sent, push_by: (m.line && m.line.body && m.line.body.push_by) || m.push_by || null,
      arrived: m.carried_by && m.carried_by.length ? m.carried_by : m.arrived || null, read: !!m.read, verified: m.verified,
      carried: !!m.carried, prose: m.prose || null, proposed: m.proposed_line || null, suspect: m.suspect || [], other: true,
      lineId: m.line_id || null });
  }
  for (const l of fromOtherHouses(ctx)) {
    if (byId.has(l.id) || answeredByUs(st, l.id, ours)) continue;
    const b = l.body || {};
    put({ id: l.id, kind: "line", holon: l.holon, title: lineText(ctx, l), about: b.card || null, ts: l.ts, from: l.actor, holder: st.actor, mine: true,
      by: b.by || null, blocks: null, critical: null, hope: (b.push && b.push.asked) || b.urgency || null, sent: b.push || null,
      push_by: b.push_by || null, other: true, lineId: l.id });
  }
  const all = [...byId.values()];
  const mine = all.filter((x) => x.mine).sort((a, b) => weigh(ctx, b) - weigh(ctx, a) || String(b.ts).localeCompare(String(a.ts)));
  const theirs = all.filter((x) => !x.mine).sort((a, b) => String(b.ts).localeCompare(String(a.ts)));
  return { mine, theirs };
}

/** The receiver's weight: by-when today or past, then the chain, then days to spare, then what waits.
    The sender's own words (their hope) never move it. */
function daysLeft(ctx, by) {
  const d = by ? ctx.fmt.date(by) : null;
  return d ? ctx.fmt.daysBetween(ctx.fmt.now(), d) : null;
}
function weigh(ctx, x) {
  const d = daysLeft(ctx, x.by);
  return (d != null && d <= 0 ? 4000 : 0) + (x.critical ? 2000 : 0) + (d != null ? Math.max(0, 60 - d) * 20 : 0)
    + (Array.isArray(x.blocks) ? Math.min(x.blocks.length, 9) * 10 : 0) + (typeof x.weight === "number" ? Math.min(Math.max(x.weight, 0), 9) : 0);
}

function readSet() { return new Set(local.get("threads.read", [])); }
function isUnread(x, seen) { return !!x.other && x.read !== true && !seen.has(x.id); }

/** The badge for the "Threads and Mail" tab, when the state carries no `badges`: unread from other houses. */
export function unreadFromOtherHouses(ctx) {
  const seen = readSet();
  try { return conversations(ctx).mine.filter((x) => isUnread(x, seen)).length; } catch { return 0; }
}

// ------------------------------------------------------------------ words

/** "When they name a day, it has held nine times in ten." Positive only; absent when too few. */
export function calibrationWords(ctx, cal) {
  if (!cal || typeof cal !== "object") return null;
  const n = (v) => ctx.fmt.number(v, true);
  if (typeof cal.by_held === "number" && typeof cal.of === "number") return cal.of >= 3 ? ctx.t("threads.cal.held", { held: n(cal.by_held), of: n(cal.of) }) : null;
  const p = cal.person || {}, a = cal.agent || {};
  if ((p.measured || 0) + (a.measured || 0) < 2) return null;
  if (p.measured && a.measured) return ctx.t("threads.cal.both", { p: n(p.real), pof: n(p.measured), a: n(a.real), aof: n(a.measured) });
  const r = p.measured ? p : a;
  return ctx.t(p.measured ? "threads.cal.held" : "threads.cal.agent", { held: n(r.real), of: n(r.measured) });
}

function cardTitle(ctx, id) {
  const st = ctx.state;
  const c = id ? ctx.read.card(st, id) : null;
  if (c) return c.title;
  const l = id ? lineById(st, id) : null;
  return l ? lineText(ctx, l) : null;
}

/** "“Bring soup for the room” and one more card wait on it, held by a member and you." */
function blocksWords(ctx, x) {
  if (!Array.isArray(x.blocks)) return null;
  const st = ctx.state, t = ctx.t;
  if (!x.blocks.length) return t("threads.rides.none");
  const cards = x.blocks.map((id) => ctx.read.card(st, id)).filter(Boolean);
  const first = cards[0] ? cards[0].title : null;
  const more = x.blocks.length - 1;
  const holders = [...new Set(cards.map((c) => c.holder).filter(Boolean))].slice(0, 3)
    .map((a) => (a === st.actor ? t("app.you") : whoOf(ctx, a, x.holon)));
  const uniq = [...new Set(holders)];
  const whom = uniq.length ? t("threads.rides.held", { who: uniq.length > 1 ? uniq.slice(0, -1).join(", ") + " " + t("threads.and") + " " + uniq.at(-1) : uniq[0] }) : "";
  const what = !first ? (x.blocks.length === 1 ? t("threads.rides.one_card") : t("threads.rides.n_cards", { n: ctx.fmt.number(x.blocks.length, true) }))
    : more === 0 ? t("threads.rides.first", { card: first }) : more === 1 ? t("threads.rides.first_one_more", { card: first })
    : t("threads.rides.first_n_more", { card: first, n: ctx.fmt.number(more, true) });
  return what + whom + ".";
}

/** "today" for today (never "by today"), else the house's own "by Saturday". */
function byShort(ctx, by) {
  if (!by) return null;
  return daysLeft(ctx, by) === 0 ? ctx.t("time.today") : ctx.fmt.by(by);
}
function byWords(ctx, x) {
  if (!x.by) return null;
  const w = byShort(ctx, x.by);
  if (!w) return null;
  const cap = w.charAt(0).toUpperCase() + w.slice(1);
  return x.why_by ? ctx.t("threads.by_because", { by: cap, why: x.why_by }) : cap + ".";
}

/** The receiver's sentence: by-when and what waits; "the whole is waiting on this" only of the
    one thread that holds the least float (the first), never of two at once. */
function ridesSentence(ctx, x, whole) {
  return [byWords(ctx, x), blocksWords(ctx, x), whole && x.critical ? ctx.t("threads.rides.chain") : null].filter(Boolean).join(" ");
}

function whoWords(ctx, x) {
  if (x.fromRole) return x.fromRole;
  if (!x.from) return ctx.t("threads.someone");
  if (x.from === ctx.state.actor) return ctx.t("app.you");
  return whoOf(ctx, x.from, x.holon) || ctx.t("threads.someone");
}
export function whereWords(ctx, x) {
  const hol = ctx.read.holon(ctx.state, x.holon);
  if (x.fromHouse && (!hol || hol.kind === "person")) return x.fromHouse;
  if (!hol) return x.fromHouse || null;
  if (hol.kind === "person") return hol.keeper === ctx.state.actor ? ctx.t("threads.where.home") : ctx.t("threads.where.house");
  return hol.kind === "room" ? ctx.t("threads.where.room", { name: hol.name }) : hol.name;
}

/** The agent's reading of what rides on an answer: the cards the answer lets move. */
function answerReading(ctx, x) {
  if (!Array.isArray(x.blocks) || !x.blocks.length) return x.by ? ctx.t("threads.answer_rides.by", { by: ctx.fmt.by(x.by) }) : "";
  const first = cardTitle(ctx, x.blocks[0]);
  const more = x.blocks.length - 1;
  if (!first) return ctx.t("threads.answer_rides.n", { n: ctx.fmt.number(x.blocks.length, true) });
  return more === 0 ? ctx.t("threads.answer_rides.one", { card: first }) : more === 1 ? ctx.t("threads.answer_rides.one_more", { card: first })
    : ctx.t("threads.answer_rides.more", { card: first, n: ctx.fmt.number(more, true) });
}

/** The badge's number, from the one place the shell reads it: `badges.threads_and_mail`, else
    the unread lines from other houses on this device. The sentence says this same number. */
export function badgeCount(ctx) {
  const b = ctx.state && ctx.state.badges;
  return b && typeof b.threads_and_mail === "number" ? b.threads_and_mail : unreadFromOtherHouses(ctx);
}

/** The words for the badge's number beside the count of what waits, so the two never disagree. */
function newWords(ctx, total, badge) {
  const t = ctx.t, n = (v) => ctx.fmt.number(v, true), N = (v) => ctx.fmt.number(v);
  if (!badge) return { inline: "", after: "" };
  if (total > 1 && badge === total) return { inline: t("threads.top.new_all"), after: "" };
  if (total > 1 && badge < total) return { inline: t("threads.top.new_some", { n: n(badge) }), after: "" };
  if (total === 1 && badge === 1) return { inline: "", after: " " + t("threads.top.new_it") };
  return { inline: "", after: " " + (badge === 1 ? t("threads.top.new_one") : t("threads.top.new_n", { n: N(badge) })) };
}

/** The one sentence. `badge` is badgeCount(ctx): the tab's numeral, said in words. */
export function topSentence(ctx, mine, theirs, badge = 0) {
  const t = ctx.t;
  const waitOn = theirs.length ? " " + (theirs.length === 1 ? t("threads.top.you_wait_one") : t("threads.top.you_wait_n", { n: ctx.fmt.number(theirs.length, true) })) : "";
  const nw = newWords(ctx, mine.length, badge);
  if (!mine.length) return t("threads.top.rest") + nw.after + waitOn;
  // one breath: how many (and how many of them are new from other houses), then the first
  const x = mine[0];
  const by = byShort(ctx, x.by);
  const n = Array.isArray(x.blocks) ? x.blocks.length : 0;
  const waits = n === 1 ? t("threads.top.waits_one") : n > 1 ? t("threads.top.waits_n", { n: ctx.fmt.number(n, true) }) : null;
  const tail = by && waits ? ": " + by + ", " + t("threads.and") + " " + waits : by || waits ? ": " + (by || waits) : "";
  const who = whoWords(ctx, x), what = x.title || t("threads.untitled");
  if (mine.length === 1) return t("threads.top.one", { who: who.charAt(0).toUpperCase() + who.slice(1), what, tail }) + nw.after + waitOn;
  return t("threads.top.n", { n: ctx.fmt.number(mine.length), news: nw.inline, who, what, tail }) + nw.after + waitOn;
}

// ------------------------------------------------------------------ the view

export default function createThreads() {
  let el = null, C = null;
  const unfolded = new Set();    // cards beyond the first, opened by a tap
  const drafts = new Map();      // id -> what the person has typed (kept across redraws)
  const rides = new Map();       // id -> the person's own words for what rides on the answer
  const sent = new Map();        // id -> the answer sent on this device, until the record carries it on
  let lastSaid = null;           // {x, text, pend}: the latest answer, kept in sight with its Undo until the next
  const timers = new Map();
  let observer = null;

  function mount(host, ctx) { useStyle("threads.css"); el = host; C = ctx; render(); }
  function update(ctx) {
    C = ctx;
    const a = document.activeElement;
    if (el && a && el.contains(a) && a.matches("input, textarea") && a.value) return;   // never redraw under a hand that is typing
    render();
  }
  function unmount() { if (observer) observer.disconnect(); observer = null; for (const tm of timers.values()) clearTimeout(tm); timers.clear(); el = null; }

  function markRead(x) {
    const s = readSet();
    if (s.has(x.id)) return;
    s.add(x.id); local.set("threads.read", [...s]);
    const live = C.state.hud && C.state.hud.mode === "live";
    if (live && x.mailId && C.mail && typeof C.mail.read === "function") C.mail.read(x.mailId);
  }

  function watchRead(node, x) {
    if (typeof IntersectionObserver !== "function") return;
    if (!observer) observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const id = e.target.dataset.conv;
        if (e.isIntersecting && !timers.has(id)) timers.set(id, setTimeout(() => { const it = e.target._conv; if (it) markRead(it); }, READ_AFTER_MS));
        if (!e.isIntersecting && timers.has(id)) { clearTimeout(timers.get(id)); timers.delete(id); }
      }
    }, { threshold: 0.5 });
    node._conv = x;
    observer.observe(node);
  }

  function render() {
    if (!el) return;
    const t = C.t;
    if (observer) observer.disconnect();
    for (const tm of timers.values()) clearTimeout(tm);
    timers.clear();
    const { mine: all, theirs: allTheirs } = conversations(C);
    const mine = all.filter((x) => !C.filter || x.holon === C.filter);
    const theirs = allTheirs.filter((x) => !C.filter || x.holon === C.filter);
    const open = mine.filter((x) => !sent.has(x.id));
    el.textContent = "";
    const wrap = h("div", { class: `threads2${open.length ? "" : " is-rest"}` });
    const lead = h("div", { class: "threads2-lead" });
    if (!open.length) lead.append(h("div", { class: "threads2-field", "aria-hidden": "true" },
      h("img", { src: FIELD, alt: "", width: "112", height: "112", decoding: "async" })));
    lead.append(h("p", { class: "threads2-sentence", role: "status" }, topSentence(C, open, theirs, badgeCount(C))));
    wrap.append(lead);

    const seen = readSet();
    const first = open[0] || null;
    const main = h("div", { class: "threads2-main" });
    // the latest answer stays where the card was, in her own words, with its Undo while it holds
    // (never her words gone with Undo floating alone)
    if (lastSaid && !(lastSaid.pend && (lastSaid.pend.status === "undone" || lastSaid.pend.status === "refused"))) {
      const holding = lastSaid.pend && lastSaid.pend.status === "holding";
      main.append(h("p", { class: "conv2-said", role: "status" }, "✓ " + t("threads.you_said", { text: lastSaid.text }),
        holding ? [" · ", h("button", { class: "link-btn conv2-undo", onclick: () => lastSaid.pend.undo() }, t("deal.undo"))] : null));
    }
    if (mine.length) {
      // the heading reads from the same list as the top sentence: never "waiting on you" under "nobody is waiting"
      main.append(h("h2", { class: "threads2-head" }, t(open.length ? "threads.head.mine" : "threads.head.answered")),
        h("ol", { class: "threads2-cards" }, mine.map((x) => h("li", null, card(x, first === x, seen)))));
    }
    wrap.append(main);
    if (theirs.length) wrap.append(h("aside", { class: "threads2-aside" },
      h("h2", { class: "threads2-head" }, t("threads.head.theirs")), waitList(theirs)));
    el.append(wrap);
  }

  function waitList(list) {
    const t = C.t;
    return h("ul", { class: "threads2-wait" }, list.map((x) => {
      const with_ = x.holder && x.holder !== C.state.actor ? whoOf(C, x.holder, x.holon) : null;
      const since = C.fmt.when(x.ts);
      return h("li", null, h("span", { class: "threads2-wait-what" }, x.title || t("threads.untitled")),
        h("span", { class: "threads2-wait-meta" }, [with_ ? t("threads.wait.with", { who: with_ }) : null,
          x.by ? C.fmt.by(x.by) : since ? t("threads.wait.since", { when: since }) : null].filter(Boolean).join(" · ")));
    }));
  }

  function card(x, first, seen) {
    const t = C.t;
    const unread = isUnread(x, seen);
    // only the first thread is open; the rest are one line each (headline and by-when), opened by a tap
    if (!first && !unfolded.has(x.id) && !sent.has(x.id) && !drafts.get(x.id)) {
      const by = byShort(C, x.by);
      const art = h("article", { class: `conv2 is-folded${unread ? " is-unread" : ""}`, "data-conv": x.id },
        h("button", { class: "conv2-fold", "aria-expanded": "false", onclick: () => { unfolded.add(x.id); render(); } },
          h("span", { class: "conv2-fold-q" }, x.title || t("threads.untitled")),
          by ? h("span", { class: "conv2-fold-by" }, by) : null));
      if (x.other && unread) watchRead(art, x);
      return art;
    }
    const art = h("article", { class: `conv2${first ? " is-owed is-first" : ""}${unread ? " is-unread" : ""}`, "data-conv": x.id });
    const from = [whoWords(C, x) + (x.toAgent ? " " + t("threads.to_agent") : ""), whereWords(C, x), arrivedWords(C, x)].filter(Boolean).join(" · ");
    art.append(h("p", { class: "conv2-from" }, from));
    art.append(h("h3", { class: `conv2-q${x.kind === "prose" ? " is-prose" : ""}` }, x.title || t("threads.untitled")));
    if (sent.has(x.id)) {
      art.append(h("p", { class: "conv2-sent" }, t("threads.you_answered", { text: sent.get(x.id) })));
      return art;
    }
    const about = x.about && !(Array.isArray(x.blocks) && x.blocks[0] === x.about) ? cardTitle(C, x.about) : null;
    // what it is about opens as its full card when the state holds that card
    if (about) art.append(h("p", { class: "conv2-about" }, C.read.card(C.state, x.about)
      ? h("button", { class: "link-btn conv2-about-open", type: "button", "aria-haspopup": "dialog",
        onclick: () => C.openCard(x.about, { from: "threads" }) }, t("threads.about", { what: about }))
      : t("threads.about", { what: about })));
    const rs = ridesSentence(C, x, first);
    if (rs) art.append(h("p", { class: "conv2-rides" }, rs));
    if (x.hope) art.append(h("p", { class: "conv2-hope" }, t("threads.hope", { words: x.hope })));
    const cal = calibrationWords(C, x.cal);
    if (cal) art.append(h("p", { class: "conv2-cal" }, cal));
    if (x.kind === "prose" && x.proposed) {
      const what = x.proposed.title || x.proposed.text || "";
      if (what) art.append(h("p", { class: "conv2-cal" }, t("threads.prose_reading", { what })));
    }
    if (Array.isArray(x.suspect) && x.suspect.length) art.append(h("p", { class: "conv2-cal" }, t("mail.suspect")));
    art.append(answerLine(x, first));
    if (x.other && unread) watchRead(art, x);
    return art;
  }

  function answerLine(x, first) {
    const t = C.t;
    const input = h("input", { type: "text", class: "conv2-input", enterkeyhint: "send", autocomplete: "off",
      "aria-label": t("threads.answer_label"), placeholder: t("threads.answer_placeholder"), value: drafts.get(x.id) || "",
      oninput: (e) => drafts.set(x.id, e.target.value),
      onkeydown: (e) => { if (e.key === "Enter") { e.preventDefault(); send(x); } } });
    const form = h("div", { class: "conv2-answer" }, input,
      h("button", { class: "pill conv2-send", onclick: () => send(x) }, t("threads.send")));
    // what rides on the answer is the sentence above; the person's own change of it shows here, marked yours
    const foot = h("div", { class: "conv2-ridesline" });
    const left = h("p", { class: "conv2-ridesleft" });
    if (rides.has(x.id)) left.append(t("threads.answer_rides.label") + " " + rides.get(x.id) + " ",
      h("span", { class: "push-mark push-mark--person" }, t("threads.push.mark_person")));
    foot.append(left, h("span", { class: "conv2-foot-acts" },
      h("button", { class: "link-btn conv2-open", type: "button", "aria-haspopup": "dialog", dataset: { openCard: x.id },
        onclick: () => C.openCard(x.id, { from: "threads", hint: { title: x.title, holon: x.holon } }) }, t("card.open_full")),
      h("button", { class: "link-btn conv2-more", onclick: () => more(x, first) }, t("threads.more"))));
    return h("div", { class: "conv2-act" }, form, foot);
  }

  function send(x) {
    const t = C.t;
    const text = (drafts.get(x.id) || "").trim();
    if (!text) { const i = el && el.querySelector(`[data-conv="${CSS.escape(x.id)}"] .conv2-input`); if (i) i.focus(); return; }
    const own = rides.has(x.id);
    const reading = answerReading(C, x);
    // the answer's field of stake (Push Protocol v1.1): the agent's reading, the person's where she changed it
    const push = { v: 1, kind: "information" };
    const push_by = { kind: "agent" };
    if (Array.isArray(x.blocks)) { push.blocks = x.blocks; push_by.blocks = "agent"; }
    if (x.critical != null) { push.critical = !!x.critical; push_by.critical = "agent"; }
    if (own || reading) { push.cost_if_late = own ? rides.get(x.id) : reading; push_by.cost_if_late = own ? "person" : "agent"; }
    const body = { text, push, push_by };
    let links = {}, holon = x.holon || homeOf(C);
    if (x.kind === "thread" || x.kind === "question") links = { anchored_to: [x.id] };
    else if (x.lineId) links = { answers: [x.lineId] };
    else holon = homeOf(C);
    const pend = C.act("say", body, links, holon, { confirmed: true, quiet: true, label: t("threads.answered") });
    lastSaid = { x, text, pend };
    if (pend && pend.done) pend.done.then((p) => {
      if (p && (p.status === "undone" || p.status === "refused")) { sent.delete(x.id); drafts.set(x.id, text); if (lastSaid && lastSaid.x === x) lastSaid = null; render(); return; }
      render();   // the window has passed: the line keeps her words, without its Undo
      // the same tap is the Send: once written, a line that came by mail goes back by mail
      if ((x.kind === "mail" || x.kind === "prose") && p && p.status === "written" && p.lineId && C.mail && typeof C.mail.send === "function") C.mail.send(p.lineId, x.from);
    }).catch(() => {});
    sent.set(x.id, text);
    drafts.delete(x.id);
    markRead(x);
    render();
  }

  /** The rare case: the whole field of stake in sentences, and the long acts. */
  function more(x, first) {
    const t = C.t;
    const body = h("div", { class: "conv2-sheet" });
    // what rides on the answer: the agent's reading, editable in place; once changed it is the person's
    const reading = answerReading(C, x);
    if (reading || rides.has(x.id)) {
      const mark = h("span", { class: `push-mark${rides.has(x.id) ? " push-mark--person" : ""}` }, rides.has(x.id) ? t("threads.push.mark_person") : "");
      body.append(h("label", { class: "conv2-ridesfield" }, h("span", { class: "conv2-ridesline-label" }, t("threads.answer_rides.label")),
        h("input", { type: "text", class: "conv2-ridesedit", value: rides.get(x.id) || reading,
          oninput: (e) => { const v = e.target.value.trim(); if (v && v !== reading) { rides.set(x.id, v); mark.textContent = t("threads.push.mark_person"); mark.className = "push-mark push-mark--person"; } else { rides.delete(x.id); mark.textContent = ""; mark.className = "push-mark"; } },
          onchange: () => render() }), mark));
    }
    const p = x.sent || null;
    const whose = (k) => (x.push_by && x.push_by[k] === "person" ? t("threads.push.mark_sender") : t("threads.push.mark_sender_agent"));
    const rows = [];
    const rs = ridesSentence(C, x, first);
    if (rs) rows.push([rs, t("threads.your_record")]);
    if (p) {
      if (p.size) rows.push([t("threads.f.size", { size: C.fmt.aboutMinutes(p.size) }), whose("size")]);
      if (p.who_waits) rows.push([t("threads.f.who_waits", { who: p.who_waits }), whose("who_waits")]);
      if (p.blast || p.blast_radius) rows.push([t("threads.f.reach", { what: p.blast || p.blast_radius }), whose("blast")]);
      if (p.cost_if_late) rows.push([t("threads.f.late", { what: p.cost_if_late }), whose("cost_if_late")]);
      if (p.alternatives) rows.push([t("threads.f.else", { what: p.alternatives }), t("threads.push.mark_sender")]);
      if (p.expires) rows.push([t("threads.f.expires", { when: C.fmt.by(p.expires) || p.expires }), t("threads.push.mark_sender")]);
      if (Array.isArray(p.blocks) && Array.isArray(x.blocks) && p.blocks.length !== x.blocks.length)
        rows.push([t("mail.differ", { theirs: C.fmt.number(p.blocks.length, true), yours: C.fmt.number(x.blocks.length, true) }), t("threads.your_record")]);
    }
    if (x.verified === "verified") rows.push([t("threads.f.signed"), ""]);
    else if (x.other && x.verified) rows.push([x.verified === "bad" ? t("mail.bad") : t("threads.f.unsigned"), ""]);
    if (x.carried) rows.push([t("threads.f.carried"), ""]);
    if (rows.length) body.append(h("ul", { class: "conv2-field" }, rows.map(([s, w]) => h("li", null, s, w ? h("span", { class: "push-mark" }, " " + w) : null))));
    if (x.prose) body.append(h("blockquote", { class: "mail-prose" }, x.prose));
    if (Array.isArray(x.suspect)) for (const s of x.suspect) body.append(h("p", { class: "conv2-cal" }, h("q", null, s.quote || ""), s.said ? " " + s.said : ""));
    const actions = [];
    let close = null;
    if (x.kind === "prose" && x.proposed && x.mailId) actions.push(h("button", { class: "pill", onclick: () => {
      if (C.mail && typeof C.mail.line === "function") C.mail.line(x.mailId);
      if (close) close();
    } }, t("mail.make_line")));
    if (x.kind === "thread" && x.from && x.from !== C.state.actor) actions.push(h("button", { class: "pill", onclick: () => {
      C.act("settle", { text: x.title }, { anchored_to: [x.id] }, x.holon, { confirmed: true, label: t("threads.closed") });
      if (close) close();
    } }, t("threads.close")));
    const compose = h("div", { class: "conv2-compose" });
    actions.push(h("button", { class: "pill quiet", onclick: () => {
      const comp = createComposer(C, { onDone: () => { if (close) close(); } });
      compose.textContent = ""; compose.append(comp.el);
      if (x.about && C.read.card(C.state, x.about)) comp.set(x.about); else comp.draw();
    } }, t("threads.ask_whole")));
    body.append(compose);
    close = C.openSheet({ title: x.title || t("threads.untitled"), body, actions });
  }

  return { mount, update, unmount };
}
