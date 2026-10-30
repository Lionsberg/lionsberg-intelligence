// play.js: the Page (DESIGN-ROOM §6.1, §8.1): the room's made document, written by
// agreement. Its Play by Play is no longer a feed (DESIGN-THE-BAR §2, the Room: "Never: the
// Play by Play as a feed"): it is two computed lists, "Settled this sitting", grouped by the
// part of the hour each line was agreed in, and "Committed, with by-whens", each commitment as
// who · what · by when, in by-when order, its ink by its status. Said and kept lines never
// enter it; an agent's line enters only once a person agrees it. Tap a settled line: its axis
// (the agent that lifted it, the person who answers for it, the card it serves). Then the
// purpose, the parts, what to read and the Big ideas. `createPage({sitting, rest})` draws the
// sitting, the rest, or both; on the phone the Room's one word, Table, opens the sitting first
// and the rest after the Table. Printable: the paper Page of §6.5.
//
// The shell's PLUGINS map sends the view id `room` to this file, so the default export hands
// the Room's frame (room.js) to the shell; the Page itself is `createPage`. When PLUGINS
// points `room` at room.js, the default export may become the Page.

import { h } from "./card.js";
import createRoom from "./room.js";
import { useStyle, lineById, lineWho, whoOf, agentOf, eyebrow, isElided, roomIdFor, postureKey } from "./inks.js";

export default function create() { return createRoom(); }

export function createPage(opts = {}) {
  const withSitting = opts.sitting !== false, withRest = opts.rest !== false;
  let el = null, C = null;
  const axisOpen = new Set();

  function mount(host, ctx) { useStyle("room.css"); el = host; C = ctx; el.classList.add("page"); render(); }
  function update(ctx) { C = ctx; render(); }
  function unmount() { el = null; }

  function render() {
    if (!el) return;
    const t = C.t, st = C.state, f = C.fmt;
    const rid = C.roomId || roomIdFor(C);
    const room = C.room || (st.rooms || {})[rid] || {};
    el.textContent = "";
    const hol = C.read.holon(st, rid);

    // the paper head: only in print (the screen has the room's strip)
    el.append(h("div", { class: "print-only page-paper-head" },
      h("h1", { class: "caps" }, room.name || C.read.holonName(st, rid)),
      h("p", null, t("room.posture." + postureKey(C, rid)) + (hol && hol.as_of ? " · " + (f.asOf(hol.as_of.ts) || "") : ""))));

    if (withSitting) el.append(...sitting(room, rid));
    if (!withRest) return;
    el.append(h("h3", { class: "caps page-title" }, t("play.page")));
    if (room.purpose) el.append(h("section", { class: "page-sec" }, h("h4", { class: "eyebrow" }, t("play.purpose")), h("p", { class: "voice page-purpose" }, room.purpose)));

    const parts = Array.isArray(room.parts) ? room.parts : [];
    if (parts.length) el.append(h("section", { class: "page-sec" }, h("h4", { class: "eyebrow" }, t("play.parts")),
      h("ol", { class: "page-parts" }, parts.map((p) => h("li", { class: p.n === room.current_part ? "is-now" : p.ended ? "is-done" : "" },
        h("span", null, p.title), " ", h("span", { class: "dust" }, "· " + t("play.part_minutes", { n: f.number(p.minutes || 0, true) })),
        p.question ? h("span", { class: "dust page-part-q" }, p.question) : null)))));

    const links = Array.isArray(room.links) ? room.links : [];
    if (links.length) el.append(h("section", { class: "page-sec" }, h("h4", { class: "eyebrow" }, t("play.links_n", { n: f.number(links.length, true) })),
      h("ul", { class: "page-links" }, links.map((l) => h("li", null, l.href ? h("a", { href: l.href, rel: "noopener" }, l.title) : l.title)))));

    const big = (Array.isArray(room.big_ideas) ? room.big_ideas : []).map((id) => lineById(st, id)).filter(Boolean);
    if (big.length) el.append(h("section", { class: "page-sec" }, h("h4", { class: "eyebrow" }, t("play.big_ideas_n", { n: f.number(big.length, true) })),
      h("ol", { class: "page-big" }, big.map((l) => h("li", { class: "ink-agreed" }, text(l))))));

    // the paper form of the commitments: a ruled table a room without screens can run on (§6.5)
    const made = (st.commitments || []).filter((k) => k.holon === rid);
    const who = (a) => (!a ? "" : isElided(a) ? t("record.hidden") : a === st.actor ? t("app.you") : whoOf(C, a, rid));
    el.append(h("section", { class: "print-only page-sec" }, h("h4", { class: "eyebrow" }, t("play.paper_commitments")),
      h("table", { class: "paper-table" },
        h("thead", null, h("tr", null, ["who", "what", "by", "size", "witness", "initials"].map((k) => h("th", null, t("table.slot." + k))))),
        h("tbody", null, [...made.map((k) => h("tr", null, h("td", null, who(k.keeper)), h("td", null, k.title), h("td", null, f.by(k.by) || ""),
          h("td", null, k.size ? t("card.minutes", { n: Math.round(k.size) }) : ""), h("td", null, who(k.witness)), h("td", null, ""))),
          ...[0, 1, 2].map(() => h("tr", { class: "paper-blank" }, [0, 1, 2, 3, 4, 5].map(() => h("td", null, ""))))]))));
    el.append(h("div", { class: "page-foot" },
      h("button", { class: "link-btn", onclick: printPage }, t("play.print"))));
  }

  function text(l) {
    const b = l.body || {};
    if (isElided(b.text) || isElided(b.title)) return C.t("record.hidden");
    if (b.text) return b.text;
    if (b.title) return b.title;
    if (l.type === "commit") {
      const c = C.read.card(C.state, b.card);
      return C.t("talk.commit_line", { title: c ? c.title : C.t("card.not_yet_arrived"), by: C.fmt.by(b.by) || C.t("table.slot_unset") });
    }
    return C.t("record.what.other");
  }

  /** The part of the hour a line was agreed in: the room's own note, else the part whose span holds its time. */
  function partOf(l, room) {
    const meta = (room.line_meta || {})[l.id];
    if (meta && meta.part != null) return meta.part;
    const at = new Date(l.ts).getTime();
    for (const p of Array.isArray(room.parts) ? room.parts : []) {
      const a = p.started ? new Date(p.started).getTime() : null, b = p.ended ? new Date(p.ended).getTime() : Infinity;
      if (a != null && at >= a && at < b) return p.n;
    }
    return null;
  }

  /** Settled this sitting (by part) and Committed, with by-whens: the Play by Play, computed. */
  function sitting(room, rid) {
    const t = C.t, st = C.state, f = C.fmt;
    const ids = Array.isArray(room.lines) ? room.lines : [];
    const lines = ids.map((id) => lineById(st, id)).filter(Boolean);
    const settled = lines.filter((l) => l.type !== "commit");
    const parts = Array.isArray(room.parts) ? room.parts : [];
    const sec = h("section", { class: "page-sec pbp", "aria-label": t("play.settled") }, h("h3", { class: "caps page-title" }, t("play.settled")));
    if (!settled.length) sec.append(h("p", { class: "dust" }, ids.length && !Array.isArray(st.lines) ? t("play.lines_absent") : t("play.settled_none")));
    const groups = new Map();
    for (const l of settled) { const n = partOf(l, room); if (!groups.has(n)) groups.set(n, []); groups.get(n).push(l); }
    const order = [...parts.map((p) => p.n), null].filter((n) => groups.has(n));
    for (const n of order) {
      const p = parts.find((x) => x.n === n);
      const at = (l) => { const d = new Date(l.ts); return isNaN(d) ? 0 : d.getTime(); };
      sec.append(h("h4", { class: "eyebrow pbp-part" }, p ? t("play.part_head", { n: f.number(p.n, true), title: p.title }) : t("play.earlier")),
        h("ol", { class: "pbp-list" }, groups.get(n).sort((a, b) => at(a) - at(b)).map((l) => settledRow(l, room, rid))));
    }
    const made = (st.commitments || []).filter((k) => k.holon === rid)
      .sort((a, b) => String(a.by || "9999").localeCompare(String(b.by || "9999")));
    const who = (a) => (!a ? "" : isElided(a) ? t("app.a_member") : a === st.actor ? t("app.you") : whoOf(C, a, rid));
    const com = h("section", { class: "page-sec pbp", "aria-label": t("play.committed") }, h("h3", { class: "caps page-title" }, t("play.committed")));
    if (!made.length) com.append(h("p", { class: "dust" }, t("play.committed_none")));
    else com.append(h("ul", { class: "pbp-list" }, made.map((k) => {
      const ink = k.status === "kept" ? "ink-agreed" : k.status === "kept-unwitnessed" ? "ink-kept" : "ink-said";
      return h("li", { class: `pbp-commit ${ink}` },
        h("span", { class: "pbp-text" }, k.title),
        h("span", { class: "dust pbp-meta" }, [who(k.keeper), f.by(k.by), k.status !== "open" ? t("table.status." + k.status.replace(/-/g, "_")) : null].filter(Boolean).join(" · ")));
    })));
    return [sec, com];
  }

  function settledRow(l, room, rid) {
    const t = C.t, f = C.fmt;
    const agreedBy = ((room.agreed_by || {})[l.id] || [])[0] || l.actor;
    const who = isElided(agreedBy) ? t("app.a_member") : agreedBy === C.state.actor ? t("app.you") : agreedBy === l.actor ? lineWho(C, l, rid) : whoOf(C, agreedBy, rid);
    const li = h("li", { class: "pbp-line ink-agreed" },
      h("button", { class: "pbp-text", "aria-expanded": String(axisOpen.has(l.id)), onclick: () => toggle(l.id) }, text(l)),
      h("span", { class: "dust pbp-meta" }, [l.type === "decide" ? eyebrow(C, l.type) : null,
        l.type === "request" ? t("play.asked_by", { who: lineWho(C, l, rid) }) : t("play.agreed_by", { who }), f.time(l.ts)].filter(Boolean).join(" · ")));
    if (axisOpen.has(l.id)) li.append(axis(l, rid));
    return li;
  }

  function toggle(id) { if (axisOpen.has(id)) axisOpen.delete(id); else axisOpen.add(id); render(); }

  function axis(l, rid) {
    const t = C.t, st = C.state;
    const rows = [];
    if (typeof l.actor === "string" && C.read.actorKind(st, l.actor) === "agent") rows.push(t("play.axis_lifted", { agent: agentOf(C, l.actor, rid) }));
    rows.push(t("play.axis_answers", { who: isElided(l.for) ? t("record.hidden") : l.for === st.actor ? t("app.you") : C.read.who(st, l.for, rid) }));
    const anchors = [...((l.links && l.links.anchored_to) || []), ...((l.links && l.links.serves) || [])];
    const cardId = (l.body && typeof l.body.card === "string" && l.body.card) || anchors.find((a) => C.read.card(st, a));
    const card = cardId ? C.read.card(st, cardId) : null;
    if (card) rows.push(t("play.axis_serves", { title: card.title }));
    else if (anchors.length) rows.push(t("play.axis_anchored", { what: lineById(st, anchors[0]) ? text(lineById(st, anchors[0])) : t("card.not_yet_arrived") }));
    return h("ul", { class: "pbp-axis dust" }, rows.map((r) => h("li", null, r)));
  }

  function printPage() {
    document.documentElement.dataset.print = "room";
    const done = () => { delete document.documentElement.dataset.print; removeEventListener("afterprint", done); };
    addEventListener("afterprint", done);
    window.print();
  }

  return { mount, update, unmount };
}
