// push.js: composing a pushed line, with its field of stake shown BEFORE Send (the Push
// Protocol carries values the agent suggests; the person can change any of them).
// The agent's reading fills by, why, size, what waits, on the chain, who waits, blast radius and
// cost if late; the person's own words are kind, asked, alternatives and expires. Every value is
// editable in place and carries a small mark of whose it is ("your agent's reading" · "yours").
// Send writes the line with `body.push` and `body.push_by: {field: "agent"|"person"}` by the
// person's tap. Also `pushMarks(ctx, push_by, field)` for received cards (a missing map: agent).
//
// The agent's reading here is read from the state (the card's own by, minutes, successors,
// critical flag and holder's role); nothing is guessed: an empty value stays empty.

import { h } from "./card.js";
import { whoOf } from "./inks.js";

const KINDS = ["request", "thread", "rfg", "escalate", "offer"];
const PERSON_FIELDS = new Set(["kind", "asked", "alternatives", "expires"]);

export function whoseMark(ctx, whose) {
  return h("span", { class: `push-mark push-mark--${whose}` }, whose === "person" ? ctx.t("threads.push.mark_person") : ctx.t("threads.push.mark_agent"));
}
/** For a received card: whose a value is, from the line's `push_by` (missing means agent). */
export function pushWhose(pushBy, field) { return pushBy && pushBy[field] === "person" ? "person" : "agent"; }

export function createComposer(ctx, { onDone } = {}) {
  let C = ctx;
  const st = () => C.state;
  const v = { kind: "request", card: "", text: "", to: "", by: "", why_by: "", size: "", blocks: [], critical: false,
    who_waits: "", blast: "", cost_if_late: "", asked: "", alternatives: "", expires: "" };
  const whose = { kind: "person", asked: "person", alternatives: "person", expires: "person" };
  const host = h("article", { class: "card card--compact push-card" });

  function agentReading() {
    const S = st();
    const c = C.read.card(S, v.card);
    if (!c) return;
    const set = (k, val) => { if (whose[k] !== "person") { v[k] = val; whose[k] = "agent"; } };
    set("by", c.by || "");
    set("size", c.minutes ? String(Math.round(c.minutes)) : "");
    set("blocks", Array.isArray(c.successors) ? [...c.successors] : []);
    set("critical", !!(c.critical || c.system_critical));
    if (!v.to && c.holder && c.holder !== S.actor) v.to = c.holder;
    const n = (S.cards || []).filter((x) => x.holon === c.holon && x.holder && x.holder !== S.actor && (c.successors || []).includes(x.id)).length;
    set("who_waits", n ? C.t(n === 1 ? "threads.push.who_waits_one" : "threads.push.who_waits_n", { n: C.fmt.number(n, true) }) : "");
  }

  function field(key, input, noMark) {
    const w = PERSON_FIELDS.has(key) ? "person" : (whose[key] || "agent");
    return h("label", { class: "push-field" },
      h("span", { class: "push-field-head" }, h("span", { class: "eyebrow" }, C.t("threads.push.f." + key)), noMark ? null : whoseMark(C, w)), input);
  }
  function text(key, opts = {}) {
    return h("input", { type: opts.type || "text", value: v[key] || "", inputmode: opts.inputmode, min: opts.min,
      oninput: (e) => { v[key] = e.target.value; if (!PERSON_FIELDS.has(key)) { whose[key] = "person"; mark(e.target, "person"); } } });
  }
  function mark(input, w) {
    const m = input.closest(".push-field").querySelector(".push-mark");
    m.className = `push-mark push-mark--${w}`;
    m.textContent = w === "person" ? C.t("threads.push.mark_person") : C.t("threads.push.mark_agent");
  }

  function draw() {
    const t = C.t, S = st();
    host.textContent = "";
    host.append(h("p", { class: "eyebrow" }, t("threads.push.title")));
    // kind: the person's own word
    host.append(field("kind", h("div", { class: "kind-chips", role: "radiogroup" }, KINDS.map((k) => h("button", { type: "button", class: "chip", role: "radio",
      "aria-checked": String(v.kind === k), onclick: () => { v.kind = k; draw(); } }, t("threads.push.kind." + k))))));
    const mine = (S.cards || []).filter((c) => !["done", "kept", "released", "declined"].includes(c.state));
    host.append(field("card", h("select", { onchange: (e) => { v.card = e.target.value; agentReading(); draw(); } },
      h("option", { value: "" }, t("table.slot_unset")), mine.map((c) => h("option", { value: c.id, selected: v.card === c.id }, c.title))), true));
    const ta = h("textarea", { rows: "2", class: "offer-input", placeholder: t("threads.push.text_placeholder"), oninput: (e) => { v.text = e.target.value; } });
    ta.value = v.text;
    host.append(h("label", { class: "push-field" }, h("span", { class: "eyebrow" }, t("threads.push.f.text")), ta));
    const c = C.read.card(S, v.card);
    if (v.kind !== "rfg" && v.kind !== "escalate") {
      const people = (S.actors || []).filter((a) => a.kind === "person" && a.id !== S.actor && (!c || (a.holons || []).includes(c.holon)));
      host.append(h("label", { class: "push-field" }, h("span", { class: "eyebrow" }, t("threads.push.f.to")),
        h("select", { onchange: (e) => { v.to = e.target.value; } }, h("option", { value: "" }, t("table.slot_unset")),
          people.map((p) => h("option", { value: p.id, selected: v.to === p.id }, whoOf(C, p.id, c ? c.holon : null))))));
    }
    // the field of stake, before Send: the agent's reading, every value editable in place
    const stake = h("div", { class: "push-stake" }, h("p", { class: "eyebrow" }, t("threads.push.stake_title")));
    stake.append(field("by", text("by", { type: "date" })), field("why_by", text("why_by")),
      field("size", text("size", { type: "number", min: "1", inputmode: "numeric" })));
    const blocks = h("div", { class: "push-blocks" }, (c && Array.isArray(c.successors) ? c.successors : []).map((id) => {
      const s = C.read.card(S, id);
      return h("label", { class: "push-check" }, h("input", { type: "checkbox", checked: v.blocks.includes(id), onchange: (e) => {
        v.blocks = e.target.checked ? [...v.blocks, id] : v.blocks.filter((x) => x !== id); whose.blocks = "person"; mark(e.target, "person");
      } }), s ? s.title : t("card.not_yet_arrived"));
    }));
    if (!blocks.childNodes.length) blocks.append(h("span", { class: "dust" }, t("threads.push.blocks_none")));
    stake.append(field("blocks", blocks));
    stake.append(field("critical", h("label", { class: "push-check" }, h("input", { type: "checkbox", checked: !!v.critical, onchange: (e) => {
      v.critical = e.target.checked; whose.critical = "person"; mark(e.target, "person"); } }), t("threads.push.on_chain"))));
    stake.append(field("who_waits", text("who_waits")), field("blast", text("blast")), field("cost_if_late", text("cost_if_late")));
    stake.append(h("p", { class: "eyebrow push-own" }, t("threads.push.own_title")));
    stake.append(field("asked", text("asked")), field("alternatives", text("alternatives")), field("expires", text("expires", { type: "date" })));
    host.append(stake);
    host.append(h("div", { class: "card-options confirm" },
      h("button", { class: "pill primary", onclick: send }, t("threads.push.send")),
      h("button", { class: "pill quiet", onclick: () => onDone && onDone() }, t("threads.not_now"))),
      h("p", { class: "dust push-law" }, t("threads.push.law")));
  }

  function send() {
    const t = C.t, S = st();
    const c = C.read.card(S, v.card);
    if (!v.text.trim() && !c) return;
    const holon = c ? c.holon : C.home;
    const push = { kind: v.kind, by: v.by || undefined, why_by: v.why_by || undefined, size: v.size ? Number(v.size) : undefined,
      blocks: v.blocks, critical: !!v.critical, who_waits: v.who_waits || undefined, blast: v.blast || undefined,
      cost_if_late: v.cost_if_late || undefined, asked: v.asked || undefined, alternatives: v.alternatives || undefined, expires: v.expires || undefined };
    const push_by = {};
    for (const k of Object.keys(push)) if (push[k] !== undefined) push_by[k] = PERSON_FIELDS.has(k) ? "person" : (whose[k] || "agent");
    const words = v.text.trim() || (c ? c.title : "");
    let type = v.kind, body = {}, links = {};
    if (type === "request") body = { to: v.to || undefined, title: words, card: c ? c.id : undefined, by: v.by || undefined, minutes: push.size };
    else if (type === "offer") body = { to: v.to || undefined, title: words, card: c ? c.id : undefined, minutes: push.size };
    else if (type === "thread") { body = { title: words }; if (c) links = { anchored_to: [c.id] }; }
    else if (type === "rfg") body = { question: words, about: c ? c.id : undefined, to: holon, by: v.by || undefined };
    else body = { about: c ? c.id : undefined, to: holon, blast_radius: v.blast || words, by: v.by || undefined };
    body.push = push; body.push_by = push_by;
    C.act(type, body, links, holon, { confirmed: true, label: t("threads.push.sent") });
    if (onDone) onDone();
  }

  return { el: host, draw, update(ctx2) { C = ctx2; }, set(card) { v.card = card; agentReading(); draw(); } };
}
