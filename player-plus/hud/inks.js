// inks.js: the small shared readers of the Room's views (the Room, the Talk, the Table,
// the Page, the Ledger, the Turn, the Record). Plain reading and wording only: nothing here
// fetches, writes, or computes a figure the state lacks (DESIGN §8.2).
//
//   lineById(st, id)        the event line as written (state.lines, a proposal), or null
//   linesIn(st, holon)      every line held for a holon, as the state gives them
//   isElided(v)             true for {"elided": "<digest>"}
//   lineWho(ctx, ln, room)  the role that wrote a line ("you", "the keeper's agent", "a member"),
//                           or "hidden by the room" when the name was elided
//   agentOf(ctx, actor, room)  "your agent" · "the keeper's agent" · "a member's agent" · "a guest's agent"
//   eyebrow(ctx, type)      AGREED · DECIDED · CARD · COMMITMENT · ASKED · OFFERED … (small capitals)
//   lineText(ctx, ln)       what a line says, in plain words, elided fields left elided
//   verifiedMark(ctx, ln)   {mark, word, cls}: ✓ signed · ○ unsigned · "not yet arrived"
//   useStyle(href)          links a view's stylesheet once
//   local                   per-device storage that never throws (private windows)

import { h } from "./card.js";

export function useStyle(href) {
  if (document.querySelector(`link[data-view-style="${href}"]`)) return;
  const l = document.createElement("link");
  l.rel = "stylesheet"; l.href = href; l.dataset.viewStyle = href;
  // before print.css, so the paper sections win in print
  const print = document.querySelector('link[href="print.css"]');
  if (print) print.before(l); else document.head.append(l);
}

export const local = {
  get(k, d) { try { const v = localStorage.getItem("hud.c." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("hud.c." + k, JSON.stringify(v)); } catch { /* this visit only */ } },
  sget(k, d) { try { const v = sessionStorage.getItem("hud.c." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  sset(k, v) { try { sessionStorage.setItem("hud.c." + k, JSON.stringify(v)); } catch { /* ignore */ } },
};

export function isElided(v) { return !!(v && typeof v === "object" && typeof v.elided === "string"); }

export function lineById(st, id) {
  if (!id || !st || !Array.isArray(st.lines)) return null;
  for (const l of st.lines) if (l && l.id === id) return l;
  return null;
}
export function linesIn(st, holon) {
  return (st && Array.isArray(st.lines) ? st.lines : []).filter((l) => l && (!holon || l.holon === holon));
}
export function hasLines(st) { return !!(st && Array.isArray(st.lines)); }

/** The room's own posture word key: open · names_hidden · sealed */
export function postureKey(ctx, holon) {
  const p = ctx.read.posture(ctx.state, holon);
  return p === "names-hidden" ? "names_hidden" : p === "sealed" ? "sealed" : "open";
}

/** "your agent" · "the keeper's agent" · "a member's agent" · "a guest's agent"; under a posture
    that hides names every other agent is "a member's agent". Never a handle. */
export function agentOf(ctx, actor, holon) {
  const st = ctx.state, t = ctx.t;
  const a = (st.actors || []).find((x) => x.id === actor);
  const person = a && a.for;
  if (person && person === st.actor) return t("app.agent_default");
  if (ctx.read.posture(st, holon) !== "open") return t("room.agent_of_member");
  const role = person ? ctx.read.role(st, person, holon) : null;
  const hol = ctx.read.holon(st, holon);
  if (role === "keeper" || (hol && person && hol.keeper === person)) return t("room.agent_of_keeper");
  if (role === "guest") return t("room.agent_of_guest");
  if (!person) return t("app.an_agent");
  return t("room.agent_of_member");
}

/** Who, by role, for any actor; elided names read "hidden by the room". */
export function whoOf(ctx, actor, holon) {
  if (isElided(actor)) return ctx.t("record.hidden");
  if (!actor) return "";
  if (ctx.read.actorKind(ctx.state, actor) === "agent") return agentOf(ctx, actor, holon);
  return ctx.read.who(ctx.state, actor, holon);
}

export function lineWho(ctx, ln, holon) {
  if (!ln) return "";
  // under a posture that hides names, an elided name reads as every other actor does: "a member"
  if (isElided(ln.actor)) return ctx.t("app.a_member");
  return whoOf(ctx, ln.actor, holon || ln.holon);
}

export function isAgentLine(ctx, ln) {
  return !!ln && typeof ln.actor === "string" && ctx.read.actorKind(ctx.state, ln.actor) === "agent";
}

const EYEBROW = { settle: "talk.ink.agreed", decide: "talk.ink.decided", card: "talk.ink.card", commit: "talk.ink.commitment",
  request: "talk.ink.asked", offer: "talk.ink.offered", ratify: "talk.ink.ratified", propose: "talk.ink.proposed",
  claim: "talk.ink.taken", hand: "talk.ink.handed", answer: "talk.ink.answered", witness: "talk.ink.witnessed",
  kept: "talk.ink.kept", publish: "talk.ink.published", posture: "talk.ink.posture", affirm: "talk.ink.affirmed",
  turn: "talk.ink.turn", tea: "talk.ink.time", say: "talk.ink.said", thread: "talk.ink.thread", done: "talk.ink.done",
  discern: "talk.ink.discern", sight: "talk.ink.sight", elevate: "talk.ink.elevate", rfg: "talk.ink.rfg",
  escalate: "talk.ink.escalate", elide: "talk.ink.elide", supersede: "talk.ink.supersede", release: "talk.ink.released" };
export function eyebrow(ctx, type) { return EYEBROW[type] ? ctx.t(EYEBROW[type]) : String(type || "").toUpperCase(); }

/** A plain sentence for a line, from its body; elided fields stay elided. */
export function lineText(ctx, ln) {
  if (!ln) return "";
  const t = ctx.t, b = ln.body || {}, st = ctx.state;
  const val = (v) => (isElided(v) ? t("record.hidden") : v);
  const cardTitle = (id) => { const c = ctx.read.card(st, id); return c ? c.title : null; };
  if (isElided(b.text)) return t("record.hidden");
  if (typeof b.text === "string" && b.text) return b.text;
  if (typeof b.title === "string" && b.title) return b.title;
  if (typeof b.question === "string" && b.question) return b.question;
  switch (ln.type) {
    case "elevate": return t("record.what.elevate", { why: val(b.why) || "" }).trim();
    case "escalate": return t("record.what.escalate", { radius: val(b.blast_radius) || "" });
    case "commit": {
      const title = cardTitle(b.card);
      return t("record.what.commit", { title: title || t("card.not_yet_arrived"), by: ctx.fmt.by(b.by) || t("table.slot_unset") });
    }
    case "affirm": return t("record.what.affirm", { agent: isElided(b.agent) ? t("record.hidden") : agentOf(ctx, b.agent, ln.holon) });
    case "posture": return t("record.what.posture", { posture: t("room.posture." + (b.posture === "names-hidden" ? "names_hidden" : b.posture || "open")) });
    case "tea": return t("record.what.tea", { minutes: Math.round(b.minutes || 0), title: cardTitle(b.card) || t("ledger.no_card") });
    case "kept": return t("record.what.kept", { note: val(b.note) || "" }).trim();
    case "witness": return val(b.note) || t("record.what.witness");
    case "discern": return t("record.what.discern", { verdict: t("ledger.verdict." + (b.verdict || "chosen")), about: val(b.note) || "" });
    case "turn": return val(b.text) || t("record.what.turn");
    case "publish": return t("record.what.publish", { n: Array.isArray(b.lines) ? b.lines.length : 0 });
    default: return val(b.note) || t("record.what.other");
  }
}

export function verifiedMark(ctx, ln) {
  const v = ln && ln.verified;
  if (v === "signed") return { mark: "✓", word: ctx.t("record.verified.signed"), cls: "v-signed" };
  if (v === "missing_link") return { mark: "◌", word: ctx.t("record.verified.missing_link"), cls: "v-missing" };
  if (v === "unsigned" || (ln && ln.sig === "")) return { mark: "○", word: ctx.t("record.verified.unsigned"), cls: "v-unsigned" };
  return { mark: "", word: ctx.t("record.verified.unknown"), cls: "v-unknown" };
}

/** The verified mark as an element, with its word for the screen reader (and on hover). */
export function markEl(ctx, ln) {
  const m = verifiedMark(ctx, ln);
  return h("span", { class: `vmark ${m.cls}`, title: m.word }, m.mark, h("span", { class: "sr-only" }, " " + m.word));
}

/** The room id this view should show: the route's, the ribbon's, or the first room held. */
export function roomIdFor(ctx) {
  const rooms = (ctx.state && ctx.state.rooms) || {};
  if (ctx.route && ctx.route.name === "room" && ctx.route.arg && rooms[ctx.route.arg]) return ctx.route.arg;
  if (ctx.filter && rooms[ctx.filter]) return ctx.filter;
  const ids = Object.keys(rooms);
  return ids.length ? ids[0] : (ctx.route && ctx.route.arg) || null;
}

/** Minutes between the clock and a time; the clock is read (fmt.now), never assumed. */
export function minutesUntil(ctx, iso) {
  const d = ctx.fmt.date(iso);
  if (!d) return null;
  return Math.round((d - ctx.fmt.now()) / 60000);
}

export function cssMs(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v.endsWith("ms") ? parseFloat(v) : v.endsWith("s") ? parseFloat(v) * 1000 : parseFloat(v) || 0;
}
export function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
