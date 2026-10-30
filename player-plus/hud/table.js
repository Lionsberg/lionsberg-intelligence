// table.js: the Table (DESIGN-ROOM §2.3, §6.1). The room's cards, in the one card face:
//   Your move · Waiting on others · Commitments made here (the five slots: who · what ·
//   by when · size · witness) · Yeses waiting on a person · The whole is waiting on.
// Cards born from a line arrive at the top as drafts, each slot honest-blank until a person
// sets it; the card is born when a person agrees it. Only the person named under WHO taps
// "Yes, I commit"; her agent cannot (schema: commit is human-only). Ball-in-court is a
// holder chip on every card ("with you", "with the keeper"), changing in front of everyone.
// Questions that climbed to this room (rfg, escalate; STATE `questions`) sit in the keeper's
// court with their by-when. A Sighting offered in the room becomes a `sight` here in one gesture.

import { h } from "./card.js";
import { lineById, lineWho, whoOf, agentOf, isElided, cssMs, cssVar, eyebrow, isAgentLine, local } from "./inks.js";

const CLOSED = new Set(["done", "kept", "released", "declined", "delivered"]);
const SIGHT_KINDS = ["defect", "hazard", "blocked", "wonder", "offer", "request", "question", "witness"];

/** What is with this wearer in a room: her cards, and what was asked of her (for the tab count). */
export function yourMove(ctx, rid) {
  const st = ctx.state, me = st.actor;
  const cards = (st.cards || []).filter((c) => c.holon === rid && c.holder === me && !CLOSED.has(c.state));
  const asked = ((st.owed && st.owed.entries) || []).filter((e) => e.holon === rid && e.kind === "request" && e.holder === me
    && !(st.commitments || []).some((k) => k.card === e.id && k.keeper === me));
  const qs = (st.questions || []).filter((q) => q.to === rid && q.holder === me && q.state === "open");
  const ids = new Set(asked.map((a) => a.id));
  return [...asked.map((e) => ({ kind: "asked", e })), ...cards.filter((c) => !ids.has(c.id)).map((c) => ({ kind: "card", c })),
    ...qs.map((q) => ({ kind: "question", q }))];
}

export default function createTable() {
  let el = null, C = null, rid = null, off = null;
  const prevHolder = new Map();
  const draftValues = new Map();
  const arrived = new Set();

  function mount(host, ctx) {
    el = host; C = ctx; rid = ctx.roomId;
    el.classList.add("table");
    off = C.shared.on(() => render());
    render();
  }
  function update(ctx) { C = ctx; rid = ctx.roomId; render(); }
  function unmount() { if (off) off(); el = null; }

  function render() {
    if (!el) return;
    const t = C.t, st = C.state, me = st.actor;
    el.textContent = "";
    const room = C.room || {};

    // drafts: cards and sightings born from a line
    for (const d of C.shared.drafts) el.append(draftCard(d));

    const mine = yourMove(C, rid);
    el.append(section(t("table.your_move"), mine.length, mine.length ? mine.map((x) =>
      x.kind === "asked" ? askedCard(x.e) : x.kind === "question" ? questionCard(x.q) : cardFace(x.c)) : [h("p", { class: "dust" }, t("table.your_move_none"))],
      mine.length ? t("table.your_move_line") : null));

    // the phone has no tray: what is offered for anyone to agree waits here, beyond the one card
    if (C.phone) {
      const offered = offeredHere();
      if (offered.length) el.append(section(t("talk.tray_title"), offered.length, offered.map(offeredCard)));
    }

    const others = (st.cards || []).filter((c) => c.holon === rid && c.holder && c.holder !== me && !CLOSED.has(c.state) && c.kind !== "draft");
    const askedOthers = ((st.owed && st.owed.entries) || []).filter((e) => e.holon === rid && e.kind === "request" && e.holder !== me);
    const qs = (st.questions || []).filter((q) => q.to === rid && q.holder !== me && q.state === "open");
    const otherItems = [...qs.map(questionCard), ...askedOthers.map(askedCard), ...others.filter((c) => !askedOthers.some((e) => e.id === c.id)).map(cardFace)];
    el.append(section(t("table.waiting_others"), otherItems.length, otherItems.length ? otherItems : [h("p", { class: "dust" }, t("table.waiting_none"))]));

    const made = (st.commitments || []).filter((k) => k.holon === rid);
    el.append(section(t("table.commitments"), made.length, made.length ? made.map(commitCard) : [h("p", { class: "dust" }, t("table.commitments_none"))]));

    const yeses = (room.awaiting_yes || []).map((id) => lineById(st, id) || { id, missing: true });
    el.append(section(t("table.yeses"), yeses.length, yeses.length
      ? [h("p", { class: "dust" }, yeses.length === 1 ? t("table.yeses_one") : t("table.yeses_n", { n: C.fmt.number(yeses.length) })), ...yeses.map(yesRow)]
      : [h("p", { class: "dust" }, t("table.yeses_none"))]));

    const drafts = (st.cards || []).filter((c) => c.holon === rid && c.kind === "draft" && !CLOSED.has(c.state));
    if (drafts.length) el.append(section(t("table.laid"), drafts.length, drafts.map(cardFace)));

    const whole = (st.cards || []).filter((c) => c.holon === rid && c.system_critical && !CLOSED.has(c.state));
    el.append(section(t("table.whole"), whole.length, whole.length ? whole.map(cardFace) : [h("p", { class: "dust" }, t("table.whole_none"))]));
  }

  function section(title, n, kids, line) {
    return h("section", { class: "table-sec" },
      h("h3", { class: "caps table-sec-title" }, n ? t2(title, n) : title),
      line ? h("p", { class: "voice table-line" }, line) : null,
      h("div", { class: "table-cards" }, kids));
  }
  function t2(title, n) { return C.t("table.count", { title, n: String(n) }); }

  /** Lines offered in this room not yet agreed, set aside on this device, or the wearer's own agent's. */
  function offeredHere() {
    const st = C.state, room = C.room || {};
    const aside = new Set(local.sget("aside." + rid, []));
    const settled = new Set();
    for (const l of st.lines || []) if (l.type === "settle" && l.links && Array.isArray(l.links.anchored_to)) l.links.anchored_to.forEach((x) => settled.add(x));
    return (room.offered || []).filter((o) => !aside.has(o.line) && !settled.has(o.line) && !(room.lines || []).includes(o.line) && lineById(st, o.line));
  }

  function offeredCard(o) {
    const t = C.t, st = C.state;
    const ln = lineById(st, o.line);
    const agentL = isAgentLine(C, ln);
    const text = (ln.body && (ln.body.text || ln.body.title)) || "";
    const by = isElided(ln.actor) ? t("app.a_member") : agentL ? agentOf(C, ln.actor, rid) : C.read.who(st, ln.actor, rid);
    return h("article", { class: "card card--compact offered-card" },
      h("p", { class: "eyebrow" }, t(ln.type === "sight" ? "talk.sighted_by" : "talk.offered_by", { who: by })),
      h("p", { class: `card-title${agentL ? " agent-text" : ""}` }, isElided(text) ? t("record.hidden") : text),
      o.reason === "untrusted" ? h("p", { class: "dust" }, t("talk.untrusted")) : null,
      h("div", { class: "card-options confirm" },
        o.for === st.actor ? h("p", { class: "dust" }, t("talk.others_agree"))
          : h("button", { class: "pill", onclick: () => C.act("settle", { text }, { anchored_to: [o.line] }, rid, { confirmed: true, label: t("talk.agree_consequence") }) }, t("talk.agree")),
        h("button", { class: "pill quiet", onclick: () => { const a = new Set(local.sget("aside." + rid, [])); a.add(o.line); local.sset("aside." + rid, [...a]); render(); } }, t("talk.not_this"))));
  }

  // ------------------------------------------------------------------ faces

  function holderChip(actor, holon) {
    const t = C.t;
    if (!actor) return h("span", { class: "holder-chip dust" }, t("table.with_nobody"));
    const who = actor === C.state.actor ? t("app.you") : whoOf(C, actor, holon || rid);
    return h("span", { class: `holder-chip${actor === C.state.actor ? " is-me" : ""}` }, t("table.with", { who }));
  }

  function cardFace(c) {
    const m = C.card.cardModel(C, { card: c });
    const face = C.card.renderCard(C, m, { form: "compact", selected: C.selected === c.id });
    // in the sitting's one frame the card already says who holds it: no chip beneath
    if (!C.phone || c.href) face.append(h("div", { class: "card-chips" }, C.phone ? null : holderChip(c.holder, c.holon),
      c.href ? h("a", { class: "pill quiet", href: c.href, target: "_blank", rel: "noopener" }, C.t("table.open")) : null));
    const before = prevHolder.get(c.id);
    if (before !== undefined && before !== c.holder) {
      // the card changing hands slides within the Table, in front of everyone (240 ms)
      requestAnimationFrame(() => C.animate(face, [{ transform: `translateY(calc(-1 * ${cssVar("--rise-line")}))`, opacity: .6 }, { transform: "none", opacity: 1 }],
        { duration: cssMs("--d-settle"), easing: cssVar("--e-settle") }));
    }
    prevHolder.set(c.id, c.holder);
    return face;
  }

  function size(m) {
    const t = C.t;
    if (!m) return null;
    if (m >= 60 && m % 60 === 0) return m === 60 ? t("table.size_hour") : t("table.size_hours", { n: C.fmt.number(m / 60, true) });
    return C.fmt.aboutMinutes(m).toLowerCase();
  }

  function slots(rows) {
    return h("dl", { class: "slots" }, rows.flatMap(([k, v, guess]) => [
      h("dt", { class: "eyebrow" }, C.t("table.slot." + k)),
      h("dd", { class: v ? (guess ? "slot-guess" : "") : "slot-unset dust" }, v || C.t("table.slot_unset"))]));
  }

  /** ASKED: the commitment card before its yes. Only the named person may commit. */
  function askedCard(e) {
    const t = C.t, st = C.state, me = st.actor;
    const card = C.read.card(st, e.id);
    const reqLine = (st.lines || []).find((l) => l.holon === rid && l.type === "request" && l.body && (l.body.title === e.title));
    const from = reqLine ? lineWho(C, reqLine, rid) : null;
    const witness = (reqLine && reqLine.body && reqLine.body.witness) || null;
    const art = h("article", { class: "card card--compact commit-card ink-said" },
      h("div", { class: "card-top" }, h("p", { class: "eyebrow card-eyebrow" },
        [eyebrow(C, "request"), from ? t("table.from_to", { from, to: e.holder === me ? t("app.you") : whoOf(C, e.holder, rid) }) : null].filter(Boolean).join(" · "))),
      h("h4", { class: "card-title" }, e.title),
      // one sentence in the sitting's frame; the five slots only where the form is the work
      C.phone ? h("p", { class: "dust" }, [C.fmt.by(e.due), size(e.minutes || (card && card.minutes)),
        witness && !isElided(witness) ? t("talk.one.witness", { who: whoOf(C, witness, rid) }) : null].filter(Boolean).join(" · "))
        : slots([["who", e.holder === me ? t("app.you") : whoOf(C, e.holder, rid)], ["what", e.title], ["by", C.fmt.by(e.due)],
        ["size", size(e.minutes || (card && card.minutes))], ["witness", witness ? whoOf(C, witness, rid) : null]]));
    if (e.holder === me) {
      if (!C.phone) art.append(h("p", { class: "commit-say" }, t("table.commit_say", { what: e.title, by: C.fmt.by(e.due) || t("table.slot_unset") })));
      art.append(h("div", { class: "card-options confirm" },
          h("button", { class: "pill primary", onclick: () => C.act("commit", { card: e.id, by: e.due, size: e.minutes || (card && card.minutes) || undefined,
            witness: witness && !isElided(witness) ? witness : undefined }, {}, rid, { confirmed: true, label: t("table.committed", { what: e.title }) }) }, t("table.yes_commit")),
          h("button", { class: "pill quiet", onclick: (ev) => { ev.currentTarget.closest("article").classList.add("is-deferred"); } }, t("table.not_yet")),
          h("button", { class: "pill quiet", onclick: () => C.act("answer", { answer: "decline", text: t("table.pass_on") }, { answers: [e.id] }, rid,
            { confirmed: true, label: t("table.passed", { what: e.title }) }) }, t("table.pass_on"))));
    } else {
      art.append(h("p", { class: "dust" }, t("table.only_named")));
    }
    if (!C.phone) art.append(h("div", { class: "card-chips" }, holderChip(e.holder, rid)));
    return art;
  }

  function commitCard(k) {
    const t = C.t, st = C.state;
    const ink = k.status === "kept" ? "ink-agreed" : k.status === "kept-unwitnessed" ? "ink-kept" : "ink-said";
    return h("article", { class: `card card--compact commit-card ${ink}` },
      h("div", { class: "card-top" }, h("p", { class: "eyebrow card-eyebrow" }, [eyebrow(C, "commit"), t("table.status." + k.status.replace(/-/g, "_"))].join(" · "))),
      slots([["who", k.keeper === st.actor ? t("app.you") : whoOf(C, k.keeper, rid)], ["what", k.title], ["by", C.fmt.by(k.by)],
        ["size", size(k.size)], ["witness", k.witness ? (k.witness === st.actor ? t("app.you") : whoOf(C, k.witness, rid)) : null]]),
      h("div", { class: "card-chips" }, holderChip(k.status === "open" ? k.keeper : k.status === "kept-unwitnessed" ? k.witness : null, rid)));
  }

  function questionCard(q) {
    const t = C.t;
    return h("article", { class: "card card--compact question-card" },
      h("div", { class: "card-top" }, h("p", { class: "eyebrow card-eyebrow" },
        [eyebrow(C, q.type), q.rung && q.rung.name ? t("table.rung", { rung: q.rung.name }) : null].filter(Boolean).join(" · "))),
      h("h4", { class: "card-title" }, isElided(q.question) ? t("record.hidden") : q.question),
      q.blast_radius ? h("p", { class: "dust" }, t("table.blast", { radius: q.blast_radius })) : null,
      h("p", { class: "card-foot dust figures" }, [q.asker ? t("table.asked_by", { who: whoOf(C, q.asker, rid) }) : null, C.fmt.by(q.by)].filter(Boolean).join(" · ")),
      h("div", { class: "card-chips" }, holderChip(q.holder, rid)));
  }

  /** A yes only a person may give: an agent's draft of a decide (or a will, a ratify). */
  function yesRow(l) {
    const t = C.t, st = C.state;
    if (l.missing) return h("p", { class: "dust" }, t("card.not_yet_arrived"));
    const draftOf = l.body && l.body.drafts ? t("table.drafts." + l.body.drafts) : t("table.drafts.decide");
    const forMe = l.for === st.actor;
    const by = typeof l.actor === "string" && C.read.actorKind(st, l.actor) === "agent" ? agentOf(C, l.actor, rid) : lineWho(C, l, rid);
    return h("article", { class: "card card--compact yes-card" },
      h("p", { class: "eyebrow" }, draftOf),
      h("p", { class: "agent-text card-title" }, h("span", { class: "ring-mark", "aria-hidden": "true" }), (l.body && l.body.text) || ""),
      h("p", { class: "dust" }, t("table.drafted_by", { who: by })),
      forMe ? h("button", { class: "pill primary", onclick: () => C.act("decide", { text: l.body.text }, { answers: [l.id] }, rid,
        { confirmed: true, label: t("talk.agree_consequence") }) }, t("table.yes_decide"))
        : h("p", { class: "dust" }, isElided(l.for) ? t("table.waits_on_person") : t("table.waits_on", { who: whoOf(C, l.for, rid) })));
  }

  // ------------------------------------------------------------------ a card (or a sighting) born from a line

  function draftCard(d) {
    const t = C.t, st = C.state;
    const v = draftValues.get(d.id) || { holder: "", by: "", minutes: "", kind: d.sightKind || "" };
    draftValues.set(d.id, v);
    const isSight = d.as === "sight";
    const art = h("article", { class: "card card--compact draft-card is-arriving" },
      h("p", { class: "eyebrow" }, isSight ? t("table.draft_sight") : t("table.draft_card")),
      h("h4", { class: "card-title" }, d.title));
    if (isSight) {
      const chips = h("div", { class: "kind-chips", role: "radiogroup", "aria-label": t("table.sight_kind") },
        SIGHT_KINDS.map((k) => h("button", { class: "chip", role: "radio", "aria-checked": String(v.kind === k),
          onclick: () => { v.kind = k; render(); } }, t("sight.kind." + k))));
      art.append(h("p", { class: "eyebrow" }, t("table.sight_kind")), chips);
    } else {
      const people = ((C.room && C.room.present) || []).filter((p) => p.kind === "person");
      const sel = h("select", { "aria-label": t("table.slot.who"), onchange: (e) => { v.holder = e.target.value; } },
        h("option", { value: "" }, t("table.slot_unset")),
        people.map((p) => h("option", { value: p.actor, selected: v.holder === p.actor }, p.actor === st.actor ? t("app.you") : C.read.who(st, p.actor, rid))));
      const by = h("input", { type: "date", value: v.by, "aria-label": t("table.slot.by"), onchange: (e) => { v.by = e.target.value; } });
      const mins = h("input", { type: "number", min: "1", step: "5", value: v.minutes, inputmode: "numeric", "aria-label": t("table.slot.size"),
        onchange: (e) => { v.minutes = e.target.value; } });
      art.append(h("div", { class: "draft-slots" },
        h("label", null, h("span", { class: "eyebrow" }, t("table.slot.who")), sel),
        h("label", null, h("span", { class: "eyebrow" }, t("table.slot.by")), by),
        h("label", null, h("span", { class: "eyebrow" }, t("table.slot.size_minutes")), mins)),
        h("p", { class: "dust" }, t("table.draft_question")));
    }
    art.append(h("div", { class: "card-options confirm" },
      h("button", { class: "pill primary", onclick: () => {
        const links = d.anchor ? { anchored_to: [d.anchor] } : {};
        if (isSight) C.act("sight", { text: d.title, kind: v.kind || undefined }, links, rid, { confirmed: true, label: t("table.sight_born") });
        else C.act("card", { title: d.title, kind: "activity", holder: v.holder || undefined, by: v.by || undefined,
          minutes: v.minutes ? Number(v.minutes) : undefined }, links, rid, { confirmed: true, label: t("table.card_born") });
        C.shared.dropDraft(d.id);
      } }, isSight ? t("table.agree_sight") : t("table.agree_card")),
      h("button", { class: "pill quiet", onclick: () => C.shared.dropDraft(d.id) }, t("talk.not_this"))));
    if (arrived.has(d.id)) art.classList.remove("is-arriving");
    else requestAnimationFrame(() => {
      arrived.add(d.id);
      art.classList.remove("is-arriving");
      C.animate(art, [{ transform: `translateY(${cssVar("--rise-card")})`, opacity: 0 }, { transform: "none", opacity: 1 }],
        { duration: cssMs("--d-card"), easing: cssVar("--e-settle") });
    });
    return art;
  }

  return { mount, update, unmount };
}
