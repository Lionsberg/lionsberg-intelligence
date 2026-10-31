"""One card, everywhere (Q2b): a card behaves the same way in every place of the HUD. One act map (hud/deal.js
actFor reads the engine's `offers` first), one face (hud/card.js, which the Chain and the Wall wrap and the Talk
draws), one tap (a card opens as the full card, in place), and every act says what it does (its label and meaning
from strings.json under the keys of acts.json, on hover and in a "What these mean" fold), only the reader's.

Each law is proven in a stub DOM over a Deal the engine deals here (deal.deal, with its `offers`): the same request
in the Deal, the full card, the Room's deal sheet and the Talk; a ratify, a thread's close, an owed commitment's
Kept and a pain's "Not now"; Take it and Done in the full card and on the Wall; the Queue, the Ledger, the sightings
map and Connections opening the card they name. Its own module: every card's tests live in their own file.

    python3 -I -m unittest discover -t . -s tests -p test_one_card.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
HUD = ENGINE.parent / "hud"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

import deal as deal_mod  # noqa: E402
import engine as engine_mod  # noqa: E402

NOW = "2026-10-31T12:00:00-07:00"
A, B = "holon-home", "holon-cell"
P, K = "person:player", "person:keeper"
HOLONS = [{"id": A, "name": "Home", "kind": "person", "keeper": P, "as_of": {"ts": NOW}},
          {"id": B, "name": "The Cell", "kind": "cell", "keeper": K, "as_of": {"ts": NOW}}]
# The one meaning strings.json says in other words than acts.json: the strings gate (hud/fixtures/test_strings.py)
# keeps a schema word off the screen, and acts.json's meaning for this act carries one. The engine's word to change.
GATE_FIXED = {"act.wallet.settle"}


def _card(i, holon=A, holder=P, state="ready", **kw):
    c = {"id": i, "kind": "card", "holon": holon, "title": "Card " + i, "minutes": 10, "holder": holder, "state": state,
         "body_kind": "activity", "actor": holder or P, "for": holder or P, "ts": "2026-10-20T09:00:00-07:00"}
    c.update(kw)
    return c


def items():
    """A request asked of the player, an owed commitment of theirs past its date, a decision to back, a thread, a
    pain and a ready card: the kinds whose acts differed from place to place (the Q1 inventory, table A2)."""
    return {"cards": [_card("a1", title="Paint the gate"),
                      _card("r1", holon=B, holder=P, state="open", asked="request", to=P, actor=K, title="Bring the soup",
                            **{"for": K})],
            "commitments": [{"id": "c-mine", "kind": "commitment", "holon": A, "card": "a1", "by": "2026-10-28", "state": "open",
                             "for": P, "actor": P, "committee": K, "ts": "2026-10-20T07:00:00-07:00"}],
            "threads": [{"id": "t1", "kind": "thread", "holon": B, "title": "Where we meet", "state": "open", "for": K, "actor": K,
                         "to": [P], "ts": "2026-10-30T07:00:00-07:00"}],
            "decisions": [{"id": "d1", "kind": "decision", "holon": A, "state": "decided", "for": P, "actor": P,
                           "decision": "Meet weekly", "decided_by": P, "title": "Meet weekly", "ts": "2026-10-30T07:00:00-07:00"}],
            "sightings": [{"id": "s1", "kind": "sighting", "holon": B, "sight_kind": "pain", "text": "The gate sticks", "state": "seen",
                           "for": K, "actor": K, "ts": "2026-10-30T07:00:00-07:00"}],
            "delegations": []}


def served_state():
    """The state the HUD is served for the player: the Deal as the engine deals it, and what the views read."""
    d = deal_mod.deal(items(), {}, P, 1000, now=NOW, holons=HOLONS)
    d = json.loads(json.dumps(d, default=str))
    cards = [dict(c, ES=0, TF=3, start="2026-10-27", predecessors=[], successors=[]) for c in items()["cards"]]
    cards += [_card("w-free", holder=None, state="ready", title="Sweep the hall", ES=1, TF=4, start="2026-10-27"),
              _card("w-other", holder=K, state="taken", title="Fix the latch", ES=1, TF=4, start="2026-10-27"),
              _card("w-done", holder=P, state="done", title="Order the paint", ES=1, TF=4, start="2026-10-27")]
    return {"actor": P, "holons": HOLONS, "deal": d, "cards": cards, "lines": [], "hud": {"now": NOW},
            "commitments": [{"id": "c-mine", "card": "a1", "status": "open", "holon": A, "committee": K}],
            "owed": {"entries": [{"id": "r1", "kind": "request", "holder": P, "holon": B, "title": "Bring the soup", "due": "2026-11-02"},
                                 {"id": "c-mine", "kind": "commitment", "holder": P, "holon": A, "title": "Paint the gate", "status": "past",
                                  "due": "2026-10-28"},
                                 {"id": "a1", "kind": "card", "holder": P, "holon": A, "title": "Paint the gate"},
                                 {"id": "q-none", "kind": "request", "holder": K, "holon": B, "title": "A row with no card"}]},
            "threads": [{"id": "t1", "title": "Where we meet", "holon": B}],
            "tea": {"entries": [{"id": "tea1", "line": "line-tea1", "card": "a1", "holon": A, "actor": K, "minutes": 30, "witness": "claimed",
                              "ts": "2026-10-30T09:00:00-07:00"}]},
            "map": {"kinds": ["pain", "defect"], "by_kind": {"pain": 1},
                    "by_place": {"the gate": {"pain": [{"id": "s1", "kind": "pain", "weight": 1, "open": True, "text": "The gate sticks"}]}},
                    "open": 1, "pains_open": 1}}


# A DOM just large enough for the HUD's views (card.js's h(), the Deal, the full card, the Room's deal sheet, the Talk,
# the Wall, the Queue, the Ledger, the sightings map, Connections), with the browser globals state.js reads at load;
# the words come from strings.json through state.js's own t(). Every act is stubbed: ctx.act records the line.
HARNESS = r"""
class CL { constructor(n) { this.n = n; } add(...c) { const s = new Set(this.n.className.split(" ").filter(Boolean)); c.forEach((x) => s.add(x)); this.n.className = [...s].join(" "); }
  remove(...c) { this.n.className = this.n.className.split(" ").filter((x) => x && !c.includes(x)).join(" "); }
  toggle(c, on) { if (on === undefined ? !this.contains(c) : on) this.add(c); else this.remove(c); } contains(c) { return this.n.className.split(" ").includes(c); } }
class N { constructor(tag) { this.tag = tag; this.kids = []; this.attrs = {}; this.dataset = {}; this.className = ""; this.on = {}; this.value = ""; this.parent = null; this.style = {}; this.hidden = false; this.classList = new CL(this); }
  append(...k) { for (const x of k) { if (x === null || x === undefined) throw new Error("appended " + x); if (x instanceof N) { if (x.parent) x.remove(); x.parent = this; } this.kids.push(x); } }
  prepend(...k) { for (const x of k.reverse()) { if (x instanceof N) x.parent = this; this.kids.unshift(x); } }
  before(x) { const p = this.parent; if (!p) return; x.parent = p; p.kids.splice(p.kids.indexOf(this), 0, x); }
  replaceWith(x) { const p = this.parent; if (!p) return; x.parent = p; p.kids[p.kids.indexOf(this)] = x; }
  replaceChildren(...k) { this.kids = []; this.append(...k); }
  remove() { const p = this.parent; if (p) p.kids = p.kids.filter((k) => k !== this); this.parent = null; }
  get parentElement() { return this.parent; } get childNodes() { return this.kids; } get isConnected() { return true; }
  get offsetLeft() { return 0; } get offsetTop() { return 0; } get offsetWidth() { return 100; } get offsetHeight() { return 20; }
  get scrollWidth() { return 1000; } get scrollHeight() { return 500; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return this.attrs[k] == null ? null : this.attrs[k]; } removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(e, f) { this.on[e] = f; } removeEventListener() {} focus() { this.focused = true; } scrollIntoView() {} animate() { return { finished: Promise.resolve() }; }
  querySelector() { return null; } querySelectorAll() { return []; } closest() { return null; } contains() { return false; } getBoundingClientRect() { return { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 }; }
  set textContent(v) { this.kids = v ? [new T(v)] : []; } get textContent() { return this.kids.map((k) => k.textContent).join(""); }
  get text() { return [...Object.values(this.attrs).filter((v) => typeof v === "string"), ...this.kids.map((k) => k.text)].join(" "); }
  get words() { return this.kids.map((k) => k.words).join(" "); } }
class T { constructor(s) { this.s = String(s); } get text() { return this.s; } get words() { return this.s; } get textContent() { return this.s; } }
globalThis.Node = N;
globalThis.location = { search: "", hostname: "127.0.0.1", hash: "", href: "http://127.0.0.1/", replace() {} };
const mem = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
globalThis.localStorage = mem(); globalThis.sessionStorage = mem();
globalThis.document = { createElement: (t) => new N(t), createElementNS: (ns, t) => new N(t), createTextNode: (s) => new T(s), querySelector: () => null, querySelectorAll: () => [],
  head: { append() {} }, body: new N("body"), documentElement: { dataset: {}, style: {} }, addEventListener() {}, removeEventListener() {} };
globalThis.window = globalThis; globalThis.addEventListener = () => {}; globalThis.removeEventListener = () => {};
globalThis.matchMedia = () => ({ matches: false, addEventListener() {} });
globalThis.getComputedStyle = () => ({ getPropertyValue: () => "" });
globalThis.requestAnimationFrame = () => 0; globalThis.CSS = { escape: (s) => s }; globalThis.scrollTo = () => {}; globalThis.scrollX = 0; globalThis.scrollY = 0;
const [hud, words, ST] = JSON.parse(process.argv[1]);
globalThis.fetch = async () => ({ ok: true, json: async () => words });
const S = await import(hud + "/state.js");
await S.loadStrings();
const card = await import(hud + "/card.js"), deal = await import(hud + "/deal.js"), full = await import(hud + "/card-full.js");
const room = await import(hud + "/room.js"), talk = await import(hud + "/talk.js"), wall = await import(hud + "/wall.js");
const queue = await import(hud + "/queue.js"), ledger = await import(hud + "/ledger.js"), smap = await import(hud + "/sightings.js");
const tick = () => new Promise((r) => setTimeout(r, 5));
const find = (n, f, out = []) => { if (n instanceof N) { if (f(n)) out.push(n); n.kids.forEach((k) => find(k, f, out)); } return out; };
const has = (n, c) => n.className.split(" ").includes(c);
const said = (n) => n.words.replace(/\s+/g, " ").trim();
const clone = (x) => JSON.parse(JSON.stringify(x));
let wrote = [], opened = [], went = [];
const pending = () => ({ status: "holding", done: Promise.resolve({ status: "written" }), undo() {} });
const ctxOf = (st, extra = {}) => ({ state: st, t: S.t, fmt: S.fmt, read: S.read, prefs: {}, flags: {}, density: "full", slot: "main", home: st.holons[0].id,
  act: (type, body, links, holon) => { wrote.push({ type, body, links }); return pending(); },
  openCard: (id) => { opened.push(id); }, go: (h) => { went.push(h); }, openSheet: () => () => {}, animate() {}, card, select() {}, ...extra });
// what a place drew: each act's label and hover meaning, and the fold's lines beside them
const labelOf = (b) => { const l = find(b, (n) => has(n, "option-label"))[0]; return said(l || b); };   // a suggested option also says so
const acts = (root, pick) => find(root, (n) => n.tag === "button" && pick(n)).map((b) => ({ label: labelOf(b), title: b.attrs.title || null }));
const folds = (root) => find(root, (n) => n.tag === "details").map((d) => said(d));
const press = (root, pick, label) => { const b = find(root, (n) => n.tag === "button" && pick(n) && labelOf(n) === label)[0]; if (!b) throw new Error("no act " + label + " in: " + said(root).slice(0, 400)); b.on.click(); return b; };
const isOption = (n) => has(n, "option");
const WORDS = "My own words";
// her answer: tap the option; an act that carries her words asks for them first, and she gives them
const answerIn = (root, label) => {
  press(root, isOption, label);
  const box = find(root, (n) => n.tag === "textarea" && has(n, "card-words-input"))[0];
  if (box) { box.value = WORDS; const send = find(root, (n) => n.tag === "button" && (labelOf(n) === S.t("card.words_send") || n.attrs["data-confirm"] !== undefined))[0]; send.on.click(); return true; }
  return false;
};
const inline = (root) => find(root, (n) => has(n, "option-reason")).map((p) => said(p));
const only = (st, ids) => { const s = clone(st); s.deal.cards = s.deal.cards.filter((c) => ids.includes(c.id)); return s; };
const out = {};

// ---- the Deal: the card in front of her, its acts, and what each writes
async function inDeal(st, id, label) {
  S.store.answered.clear(); wrote = [];
  const host = new N("main"), v = deal.default();
  v.mount(host, ctxOf(only(st, [id])));
  const drawn = { acts: acts(host, isOption), folds: folds(host), inline: inline(host) };
  if (label) drawn.asked = answerIn(host, label);
  await tick();
  return { ...drawn, wrote, text: said(host) };
}
// ---- the full card, opened on the dealt card
async function inFull(st, id, label, actsIn = {}) {
  S.store.answered.clear(); wrote = [];
  const f = full.renderFullCard(ctxOf(clone(st)), id, { acts: actsIn });
  const drawn = { acts: acts(f.el, isOption), folds: folds(f.el), inline: inline(f.el), all: acts(f.el, () => true) };
  if (label) drawn.asked = answerIn(f.el, label);
  await tick();
  return { ...drawn, wrote };
}
// ---- the Room's "Your deal" sheet: choose, then "Yes, I will"
async function inRoom(st, id, label) {
  wrote = [];
  const C = ctxOf(clone(st));
  const host = room.dealCard(C, C.state.deal.cards.find((c) => c.id === id), 1, 1);
  const drawn = { acts: acts(host, isOption), folds: folds(host), inline: inline(host) };
  if (label) {
    press(host, isOption, label);
    drawn.chosenActs = acts(host, (n) => n.attrs["data-confirm"] !== undefined || has(n, "quiet")); drawn.chosenFolds = folds(host);
    const box = find(host, (n) => n.tag === "textarea")[0];
    if (box) { box.value = WORDS; drawn.asked = true; }
    find(host, (n) => n.tag === "button" && n.attrs["data-confirm"] !== undefined)[0].on.click();
  }
  await tick();
  return { ...drawn, wrote };
}
// ---- the Talk, on the phone: the one card a request asked of her in the room
let rooms = 0;
async function inTalk(st, label) {
  S.store.answered.clear(); wrote = [];
  const s = clone(st);
  // the Talk holds an answered card per room until the stream confirms it: each sitting here is a room of its own
  const rid = B + "#" + (++rooms);
  for (const e of s.owed.entries) if (e.holon === B) e.holon = rid;
  const C = ctxOf(s, { roomId: rid, room: { parts: [], offered: [], awaiting_yes: [], lines: [], current_part: null }, phone: true,
    shared: { on: () => () => {}, drafts: [], addDraft() {} } });
  const host = new N("section"), v = talk.default();
  v.mount(host, C);
  const tray = find(host, (n) => has(n, "tray"))[0];
  const drawn = { acts: acts(tray, isOption), folds: folds(tray), inline: inline(tray), all: acts(tray, () => true) };
  if (label) drawn.asked = answerIn(tray, label);
  await tick();
  return { ...drawn, wrote };
}
const A = "holon-home", B = "holon-cell", P = "person:player";
const st = ST;
const req = st.deal.cards.find((c) => c.id === "r1");
const accept = S.t("act.answer.accept");
out.request = { deal: await inDeal(st, "r1", accept), full: await inFull(st, "r1", accept), room: await inRoom(st, "r1", accept), talk: await inTalk(st, accept),
  options: req.options };
// every option of the request, in each place, writes the same line
out.requestAll = {};
for (const o of card.optionsOf(ctxOf(st), req)) {
  out.requestAll[o.label] = { deal: (await inDeal(st, "r1", o.label)).wrote, full: (await inFull(st, "r1", o.label)).wrote,
    room: (await inRoom(st, "r1", o.label)).wrote, talk: (await inTalk(st, o.label)).wrote };
}
// ---- law 2: a ratify, a thread's close, an owed commitment's Kept, a pain's "Not now"
const firstLabel = (id, key) => card.optionsOf(ctxOf(st), st.deal.cards.find((c) => c.id === id)).find((o) => o.key === key);
const lbl = (id, key) => (firstLabel(id, key) || {}).label;
out.ratify = { deal: await inDeal(st, "d1", lbl("d1", "act.ratify")), room: await inRoom(st, "d1", lbl("d1", "act.ratify")) };
out.settle = { deal: await inDeal(st, "t1", lbl("t1", "act.settle")), room: await inRoom(st, "t1", lbl("t1", "act.settle")),
  threadsLine: deal.actFor({ id: "t1", kind: "thread" }, "act.settle", "Where we meet", st) };
out.kept = { deal: await inDeal(st, "c-mine", lbl("c-mine", "act.kept")), room: await inRoom(st, "c-mine", lbl("c-mine", "act.kept")) };
out.handBack = await inDeal(st, "c-mine", lbl("c-mine", "act.release"));
const pain = st.deal.cards.find((c) => c.id === "s1");
out.pain = { deal: await inDeal(st, "s1", pain.options[2]), room: await inRoom(st, "s1", pain.options[2]), options: pain.options };
// the same laws with no offers (an older Deal): the fallback writes what offers would
const bare = (dc) => { const x = clone(dc); delete x.offers; return x; };
out.fallback = {
  request: [0, 1, 2].map((i) => deal.actFor(bare(req), i, null, st)),
  ratify: deal.actFor({ id: "d1", kind: "ratify", section: "decision", options: ["Confirm", "Read the thread first", "Return it with one change"] }, 0, null, st),
  thread: deal.actFor({ id: "t1", kind: "thread", section: "thread", options: ["Reply now", "Settle it as it stands", "Hand it to someone else"] }, 1, null, st),
  kept: deal.actFor({ id: "c-mine", kind: "commitment", section: "owed", options: ["Kept", "Renegotiate", "Release it"] }, 0, null, st),
  onTrack: deal.actFor({ id: "c-other", kind: "commitment", section: "owed", options: ["On track", "Renegotiate", "Release it"] }, 0, null, st),
  painNotNow: deal.actFor({ id: "s1", kind: "pain", options: ["Respond now", "Pass it on", "Not now"], acts: ["say", "elevate", null] }, 2, null, st),
  painStrings: deal.actFor({ id: "s1", kind: "pain", options: ["Respond now", "Pass it on", "Not now"], acts: ["say", "say", null] }, 1, null, st),
  receipt: deal.actFor({ id: "receipt:x:person:keeper", kind: "receipt", options: ["Ask again", "Let it go"],
    draft: { type: "say", body: { to: ["person:keeper"], text: "Checking that it reached you." }, links: { anchored_to: ["x"] } } }, 0, null, st),
};
// which of each dealt card's options are drawn, by their own words: only the reader's
out.drawnOptions = Object.fromEntries(st.deal.cards.map((c) => [c.id, card.optionsOf(ctxOf(st), c).map((o) => o.option)]));
// what the Deal's fixtures without offers draw: every option, its words
out.fallbackDrawn = card.optionsOf(ctxOf(st), bare(req)).map((o) => [o.label, o.key, !!o.meaning]);

// ---- law 3: Take it and Done under one rule, in the full card and on the Wall
const both = {};
const noop = { claim() {}, done() {}, say() {}, ask() {} };
const takeDone = (xs) => xs.filter((a) => [S.t("card.claim"), S.t("card.done")].includes(a.label));
for (const c of st.cards) {
  const f = await inFull(st, c.id, null, noop);
  const s = clone(st);   // the Wall reads the same Deal: a dealt card's offers decide both
  const host = new N("main"), v = wall.default();
  v.mount(host, ctxOf(s));
  const note = find(host, (n) => n.tag === "button" && has(n, "wall-note") && n.dataset.id === c.id)[0];
  let w = null;
  if (note) { note.on.click(); w = takeDone(acts(host, (n) => !has(n, "wall-note"))); }
  both[c.id] = { full: takeDone(f.all), wall: w, state: c.state, holder: c.holder,
    wallFold: note ? folds(host) : [], sticky: note ? said(note) : null };
}
out.takeDone = both;
// with the Deal's offers, the full card's Take it follows them (a1 is dealt and ready)
out.takeOffered = deal.cardActs(st, st.cards.find((c) => c.id === "a1"), st.deal.cards.find((c) => c.id === "a1")).map((a) => [a.key, a.line]);
// a written Take it: the Wall's line is the full card's line
{
  const s = clone(st); s.deal.cards = []; wrote = [];
  const host = new N("main"), v = wall.default();
  v.mount(host, ctxOf(s));
  find(host, (n) => n.tag === "button" && n.dataset.id === "w-free")[0].on.click();
  press(host, () => true, S.t("card.claim"));
  out.wallTake = wrote;
  out.fullTake = deal.cardActs(st, st.cards.find((c) => c.id === "w-free"), null).map((a) => a.line);
}

// ---- law 5: one tap opens the full card, in the Queue (title and foot), the Ledger, the sightings map, Connections
{
  opened = []; went = [];
  const host = new N("main"), v = queue.default();
  v.mount(host, ctxOf(clone(st), { route: { params: new Map() } }));
  const rows = find(host, (n) => has(n, "card--row"));
  out.queue = rows.map((r) => {
    opened = []; went = [];
    find(r, (n) => has(n, "card-row-open"))[0].on.click();
    const t1 = opened.slice();
    const foot = find(r, (n) => n.tag === "button" && has(n, "card-foot"))[0];
    opened = [];
    if (foot) foot.on.click();
    return { id: r.dataset.card, title: t1, foot: opened.slice(), went: went.slice() };
  });
}
{
  opened = [];
  const host = new N("main"), v = ledger.default();
  const s = clone(st); s.roles = { [A]: { [P]: "keeper" } };
  v.mount(host, ctxOf(s, { filter: null }));
  const b = find(host, (n) => n.tag === "button" && has(n, "ledger-card"))[0];
  if (b) b.on.click();
  out.ledger = { opened: opened.slice(), title: b ? b.attrs.title : null, folds: folds(host) };
}
{
  opened = [];
  const host = new N("main"), v = smap.default();
  v.mount(host, ctxOf(clone(st)));
  find(host, (n) => n.tag === "button" && has(n, "smap-count"))[0].on.click();
  const b = find(host, (n) => n.tag === "button" && has(n, "smap-open"))[0];
  if (b) b.on.click();
  out.sightings = { opened: opened.slice(), title: b ? b.attrs.title : null, folds: folds(host) };
}
// ---- the repair's laws: a released card is free to take; an act key the offers refuse is refused; no reader, no act;
// a line never names [null]; the Table answers a request as the Deal does; Threads' close and the Talk's Agree settle
const free = (state) => ({ id: "x-" + state, kind: "card", state, holder: null, title: "Free again" });
out.freeAgain = ["released", "returned", "done", "retracted"].map((s0) => [s0, deal.cardActs(st, free(s0), null).map((a) => a.key)]);
out.noReader = deal.cardActs({ ...st, actor: null }, free("ready"), null).map((a) => a.key);
const d1 = st.deal.cards.find((c) => c.id === "d1");
out.refused = { decide: deal.actFor(d1, "act.decide", "x", st), done: deal.actFor(d1, "act.done", null, st), ratify: deal.actFor(d1, "act.ratify", null, st) };
out.nullId = [deal.actFor({ id: 5 }, "act.say", "x", st), deal.actFor({ id: null }, "act.claim", null, st), deal.actFor({ id: null }, "act.settle", "x", st)];
{
  const table = await import(hud + "/table.js");
  wrote = [];
  const s = clone(st); const rid = B + "#table";
  for (const e of s.owed.entries) if (e.holon === B) e.holon = rid;
  const C = ctxOf(s, { roomId: rid, room: { parts: [], offered: [], awaiting_yes: [], lines: [] }, phone: false, shared: { on: () => () => {}, drafts: [], addDraft() {} } });
  const host = new N("section"), v = table.default();
  v.mount(host, C);
  const yes = S.t("act.answer.accept");
  const tacts = acts(host, (n) => [yes, S.t("table.not_yet"), S.t("act.answer.decline")].includes(labelOf(n)));
  out.table = { acts: tacts, folds: folds(host) };
  press(host, () => true, yes);
  out.table.wrote = wrote.slice();
}
{
  const threads = await import(hud + "/threads.js");
  wrote = []; let sheet = null;
  const s = clone(st);
  s.threads = [{ id: "t1", title: "Where we meet", holon: B, to: [P], last_actor: "person:keeper", last_ts: "2026-10-30T07:00:00-07:00" }];
  const C = ctxOf(s, { openSheet: (o) => { sheet = o; return () => {}; } });
  const host = new N("main"), v = threads.default();
  try {
    v.mount(host, C);
    find(host, (n) => n.tag === "button" && has(n, "conv2-more"))[0].on.click();
    const close = (sheet.actions || []).find((b) => labelOf(b) === S.t("act.settle"));
    out.threads = { title: close && close.attrs.title, folds: folds(sheet.body) };
    close.on.click();
    out.threads.wrote = wrote.slice();
  } catch (e) { out.threads = { error: String(e.stack || e).slice(0, 600) }; }
}
{
  wrote = [];
  const s = clone(st); const rid = B + "#agree";
  const ln = { id: "line-o1", type: "say", actor: "person:keeper", holon: rid, ts: "2026-10-31T09:00:00-07:00", body: { text: "We meet at the hall" } };
  s.lines = [ln];
  const C = ctxOf(s, { roomId: rid, room: { parts: [], offered: [{ line: "line-o1", for: "person:keeper" }], awaiting_yes: [], lines: [] }, phone: false,
    shared: { on: () => () => {}, drafts: [], addDraft() {} } });
  const host = new N("section"), v = talk.default();
  try {
    v.mount(host, C);
    const tray = find(host, (n) => has(n, "tray"))[0];
    out.agree = { folds: folds(tray) };
    press(tray, () => true, S.t("talk.agree"));
    await tick();
    out.agree.wrote = wrote.slice();
  } catch (e) { out.agree = { error: String(e.stack || e).slice(0, 600) }; }
}
{
  const margin = await import(hud + "/margin.js");
  opened = []; const agreed = [];
  const C = ctxOf(clone(st));
  const el = margin.renderMargin(C, [{ id: "o1", kind: "commitment", text: "Paint the gate by Friday", ink: "said", card: "a1" }], { onAgree: (it) => agreed.push(it.id), onDecline() {} });
  find(el, (n) => n.tag === "button" && has(n, "dock-mwords"))[0].on.click();
  press(el, () => true, S.t("dock.margin.agree"));
  out.margin = { opened: opened.slice(), agreed, acts: acts(el, (n) => n.tag === "button" && !has(n, "dock-mwords")), folds: folds(el) };
}
{
  const chain = await import(hud + "/chain.js");
  opened = [];
  const s = clone(st);
  s.cards = s.cards.map((c) => ({ ...c, critical: true }));
  s.path = { critical: s.cards.filter((c) => c.state !== "done").map((c) => c.id) };
  try {
    const host = new N("main"), v = chain.default();
    v.mount(host, ctxOf(s));
    const b = find(host, (n) => n.tag === "button" && has(n, "road-title"))[0];
    b.on.click();
    out.chain = { opened: opened.slice(), title: b.attrs.title, face: has(b.parent, "card--station") };
  } catch (e) { out.chain = { error: String(e.stack || e).slice(0, 600) }; }
}
// ---- the cold read: the Deal opens with the three answers, a pile counted from one, a stake that takes its clause
{
  S.store.answered.clear();
  const host = new N("main"), v = deal.default();
  v.mount(host, ctxOf(clone(st)));
  out.opens = { three: find(host, (n) => has(n, "deal-three-line")).map(said), line: find(host, (n) => has(n, "deal-line")).map(said),
    count: find(host, (n) => has(n, "card-count")).map(said), stake: find(host, (n) => has(n, "card-stake")).map(said),
    pile: deal.pileOf(ctxOf(st)).length };
}
console.log(JSON.stringify(out));
"""

# Connections, drawn over the fixture's state as test_views draws it, with a connection that names its agreement.
CONN = r"""
class N { constructor(tag) { this.tag = tag; this.kids = []; this.attrs = {}; this.dataset = {}; this.className = ""; this.on = {}; }
  append(...k) { for (const x of k) { if (x === null || x === undefined) throw new Error("appended " + x); this.kids.push(x); } }
  setAttribute(k, v) { this.attrs[k] = v; } addEventListener(e, f) { this.on[e] = f; }
  set textContent(v) { this.kids = v ? [new T(v)] : []; }
  get text() { return [...Object.values(this.attrs).filter((v) => typeof v === "string"), ...this.kids.map((k) => k.text)].join(" "); } }
class T { constructor(s) { this.s = String(s); } get text() { return this.s; } }
globalThis.Node = N;
globalThis.document = { createElement: (t) => new N(t), createTextNode: (s) => new T(s), querySelector: () => ({}), head: { append() {} } };
const [view, st, words] = JSON.parse(process.argv[1]);
const t = (k, v) => { let s = words[k]; if (s == null) return "[" + k + "]"; if (v && typeof s === "string") s = s.replace(/\{(\w+)\}/g, (m, x) => (v[x] == null ? m : String(v[x]))); return s; };
const m = await import(view);
const find = (n, f, out = []) => { if (n instanceof N) { if (f(n)) out.push(n); n.kids.forEach((k) => find(k, f, out)); } return out; };
const cls = (c) => (n) => n.className.split(" ").includes(c);
const opened = [];
const el = new N("section"), v = m.default();
v.mount(el, { state: st, t, slot: "full", density: "full", read: { holonName: () => "" }, fmt: {}, openCard: (id) => opened.push(id) });
find(el, cls("conn-more"))[0].on.click();
const b = find(el, cls("conn-open"))[0];
if (b) b.on.click();
console.log(JSON.stringify({ opened, title: b ? b.attrs.title : null, acts: find(el, cls("conn-acts")).map((n) => n.text).join(" ") }));
"""


def engine_dealt():
    """Dealt cards whose acts the engine now names (acts.json, 2026-10-31): a sighting's and a keeper's pain card's
    Pass it on (elevate), and a body's handoff (Mark it read, a witness), each with its `offers` as the Deal attaches
    them; and the state they are read in, its group inside a wider circle."""
    import acts
    from gamecore import normalize
    holons = [dict(h, parent="holon-commons") if h["id"] == B else h for h in HOLONS]
    s2 = {"id": "s2", "kind": "sighting", "holon": B, "sight_kind": "odd", "text": "A loose board", "state": "seen", "for": P, "actor": P,
          "ts": "2026-10-30T08:00:00-07:00"}
    ctx = deal_mod.acts_context(normalize({"sightings": [s2], "holons": holons}), holons)
    out = []
    for c in ({"id": "s2", "kind": "sighting", "section": "decision", "holon": B, "question": "Pass this on?",
               "options": ["Pass it on", "Keep it here", "Not yet"], "recommendation": "Pass it on"},
              {"id": "s2", "kind": "pain", "section": "owed", "holon": B, "question": "Someone asks for help",
               "options": ["Respond now", "Pass it on", "Not now"], "recommendation": "Respond now", "acts": ["say", "elevate", None]}):
        o = acts.offered(s2, K, folded=ctx, now=NOW, card=c)
        o["options"] = acts.options_for(c, o)
        out.append(dict(c, offers=o))
    h = {"id": "h1", "kind": "handoff", "holon": A, "question": "Read the handoff", "options": ["Mark it read", "Read it now"],
         "recommendation": "Mark it read"}
    o = acts.offered({"id": "h1", "kind": "handoff", "holon": A, "for": P}, P, folded=deal_mod.acts_context(normalize({"holons": HOLONS}), HOLONS),
                     now=NOW, card=h)
    o["options"] = acts.options_for(h, o)
    out.append(dict(h, offers=o))
    return json.loads(json.dumps(out)), holons


ENGINE_ACTS = r"""
const [hud, words, ST, CARDS, HOLONS2] = JSON.parse(process.argv[1]);
globalThis.document = { createElement: () => ({}), createTextNode: () => ({}) };
const store = new Map(); globalThis.localStorage = globalThis.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.location = { search: "", hostname: "127.0.0.1", hash: "" };
const map = await import(hud + "/act-map.js"), card = await import(hud + "/card.js");
const t = (k, v) => { let s = words[k]; if (s == null) return "[" + k + "]"; if (v) s = s.replace(/\{(\w+)\}/g, (m, x) => (v[x] == null ? m : String(v[x]))); return s; };
const ctx = (st) => ({ state: st, t });
const keeper = { ...ST, actor: "person:keeper", holons: HOLONS2 };
const lost = { ...keeper, holons: HOLONS2.map((h) => ({ ...h, parent: undefined })) };
const [sight, pain, handoff] = CARDS;
const out = {
  sight: { line: map.actFor(sight, 0, null, keeper), drawn: card.optionsOf(ctx(keeper), sight).map((o) => [o.label, o.meaning, o.key]),
    lost: (() => { const x = JSON.parse(JSON.stringify(sight)); x.offers.options[0].writes.body.to = null; return map.actFor(x, 0, null, lost); })() },
  pain: { line: map.actFor(pain, 1, null, keeper), drawn: card.optionsOf(ctx(keeper), pain).map((o) => [o.label, o.key]) },
  handoff: { line: map.actFor(handoff, "act.witness", null, ST), drawn: card.optionsOf(ctx(ST), handoff).map((o) => [o.label, o.meaning, o.key]),
    agent: map.actFor({ ...handoff, offers: { ...handoff.offers, acts: [] } }, "act.witness", null, ST) },
  margin: [{ id: "o1", kind: "commitment", text: "Paint it", card: "a1", by: "2026-11-02" }, { id: "o2", kind: "said_in_room", text: "We meet Friday" },
    { id: "o3", kind: "card", text: "Book the hall", by: "2026-11-05" }, { id: "o4", kind: "card", text: "  " }].map((x) => map.offeredLine(x, ST)),
};
console.log(JSON.stringify(out));
"""


def _strings():
    return json.loads((HUD / "strings.json").read_text(encoding="utf-8"))


def _acts_json():
    return json.loads((ENGINE / "acts.json").read_text(encoding="utf-8"))


class OneCardEverywhere(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("no node on this machine")
        cls.st = served_state()
        cls.w = _strings()
        arg = json.dumps([HUD.as_uri(), cls.w, cls.st])
        out = subprocess.run([node, "--input-type=module", "-e", HARNESS, arg], capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            raise AssertionError(out.stderr[-3000:])
        cls.r = json.loads(out.stdout)

    def dealt(self, i):
        return next(c for c in self.st["deal"]["cards"] if c["id"] == i)

    # law 1 ------------------------------------------------------------------------------------------------

    def test_the_same_request_offers_the_same_acts_everywhere(self):
        r, w = self.r["request"], self.w
        places = ("deal", "full", "room", "talk")
        drawn = {p: r[p]["acts"] for p in places}
        for p in places:
            self.assertEqual(drawn[p], drawn["deal"], p)                  # the same acts, labels and meanings
        self.assertEqual([a["label"] for a in drawn["deal"]], [w["act.answer.accept"], r["options"][1], w["act.answer.decline"]])
        other = r["options"][1]
        self.assertEqual([a["title"] for a in drawn["deal"]],
                         [w["act.answer.accept_means"], w["act.say.yours_means"].replace("{option}", other), w["act.answer.decline_means"]])
        self.assertEqual(len({a["title"] for a in drawn["deal"]}), 3)    # one meaning per act, never one shared by two

    def test_the_same_request_writes_answer_everywhere(self):
        want = {"type": "answer", "body": {"answer": "accept"}, "links": {"answers": ["r1"]}}
        for p in ("deal", "full", "room", "talk"):
            self.assertEqual(self.r["request"][p]["wrote"], [want], p)
        for label, by in self.r["requestAll"].items():
            self.assertTrue(by["deal"], label)
            for p in ("full", "room", "talk"):
                self.assertEqual(by[p], by["deal"], (label, p))           # every option: one line, wherever it is given
        decline = self.r["requestAll"][self.w["act.answer.decline"]]["deal"][0]
        self.assertEqual((decline["type"], decline["body"]), ("answer", {"answer": "decline"}))
        other = self.r["requestAll"][self.r["request"]["options"][1]]["deal"][0]
        # her own words, asked for before anything is written (offers' needs_words), and said as hers
        self.assertEqual(other, {"type": "say", "body": {"text": "My own words", "voice": "human-words"}, "links": {"anchored_to": ["r1"]}})
        for p in ("deal", "room", "talk"):
            for line in sum((by[p] for by in self.r["requestAll"].values()), []):
                self.assertNotEqual(line["type"], "commit", p)            # never a commit for an answer

    # law 2 ------------------------------------------------------------------------------------------------

    def test_a_ratify_never_writes_decide(self):
        for p in ("deal", "room"):
            self.assertEqual(self.r["ratify"][p]["wrote"], [{"type": "ratify", "body": {}, "links": {"answers": ["d1"]}}], p)
        self.assertEqual(self.r["fallback"]["ratify"]["type"], "ratify")

    def test_a_thread_closes_with_settle(self):
        want = {"type": "settle", "body": {"text": "Where we meet"}, "links": {"anchored_to": ["t1"]}}
        for p in ("deal", "room"):
            self.assertEqual(self.r["settle"][p]["wrote"], [want], p)
        self.assertEqual(self.r["settle"]["threadsLine"], want)          # Threads and Mail's close: the same map
        self.assertEqual(self.r["fallback"]["thread"]["type"], "settle")

    def test_an_owed_commitments_kept_writes_kept(self):
        for p in ("deal", "room"):
            self.assertEqual(self.r["kept"][p]["wrote"], [{"type": "kept", "body": {"commitment": "c-mine"}, "links": {}}], p)
        labels = [a["label"] for a in self.r["kept"]["deal"]["acts"]]
        self.assertIn(self.w["act.kept"], labels)
        self.assertNotIn(self.w["act.witness"], labels)                   # the committee's confirm is never the committor's
        self.assertNotIn(self.w["act.release.on_commitment"], labels)    # nor the committee's words for a release
        rel = next(o for o in self.dealt("c-mine")["offers"]["options"] if o["key"] == "act.release")
        if rel["offered"]:                                                 # the registry lets the committor hand it back
            self.assertIn(self.w["act.release.on_commitment.as_committor"], labels)
        self.assertEqual(len(labels), sum(1 for o in self.dealt("c-mine")["offers"]["options"] if o["offered"] or not o["key"]))

    def test_only_the_readers_acts_are_drawn(self):
        for cid in ("r1", "c-mine", "d1", "s1", "a1"):
            dc = self.dealt(cid)
            want = [o["option"] for o in dc["offers"]["options"] if o["offered"] or not o["key"]]
            self.assertEqual([o for o in self.r["drawnOptions"][cid]], want, cid)
        refused = [o for o in self.dealt("a1")["offers"]["options"] if o["key"] and not o["offered"]]
        self.assertTrue(refused)                                           # a ready card: its release is not hers yet
        self.assertNotIn(refused[0]["option"], self.r["drawnOptions"]["a1"])
        self.assertEqual(self.r["fallback"]["kept"], {"type": "kept", "body": {"commitment": "c-mine"}, "links": {}})
        self.assertEqual(self.r["fallback"]["onTrack"]["type"], "say")   # "On track" is a word, never a claim it was kept

    def test_a_pains_not_now_writes_nothing(self):
        for p in ("deal", "room"):
            self.assertEqual(self.r["pain"][p]["wrote"], [], p)
        self.assertIn(self.r["pain"]["options"][2], [a["label"] for a in self.r["pain"]["deal"]["acts"]])
        self.assertIsNone(self.r["fallback"]["painNotNow"])
        self.assertEqual(self.r["fallback"]["painStrings"]["type"], "say")   # the engine's acts, read as type names

    def test_the_fallback_writes_what_offers_would(self):
        f = self.r["fallback"]
        self.assertEqual([x and x["type"] for x in f["request"]], ["answer", "say", "answer"])
        self.assertEqual([x["body"].get("answer") for x in (f["request"][0], f["request"][2])], ["accept", "decline"])
        self.assertEqual(f["receipt"]["body"]["to"], ["person:keeper"])   # the receipt's draft, addressed, is the line
        self.assertEqual(f["receipt"]["body"]["text"], "Checking that it reached you.")
        self.assertTrue(all(m for _, _, m in self.r["fallbackDrawn"]))     # with no offers, every option still says what it does

    # law 3 ------------------------------------------------------------------------------------------------

    def test_take_it_and_done_under_one_rule(self):
        w = self.w
        seen = set()
        for cid, x in self.r["takeDone"].items():
            if x["wall"] is None:
                continue                                                   # not on the Wall (finished): nothing to compare
            self.assertEqual(x["wall"], x["full"], cid)                   # the same acts, the same words, the same meanings
            seen |= {a["label"] for a in x["full"]}
        self.assertEqual(seen, {w["act.claim"], w["act.done"]})           # the words of acts.json, one set
        free, other, mine = self.r["takeDone"]["w-free"], self.r["takeDone"]["w-other"], self.r["takeDone"]["a1"]
        self.assertEqual([a["label"] for a in free["full"]], [w["act.claim"]])
        self.assertEqual([a["label"] for a in other["full"]], [])          # taken: not in the registry's `from` for a take
        self.assertEqual([a["label"] for a in mine["full"]], [w["act.claim"], w["act.done"]])   # dealt and ready in her hands: taken up, or done
        self.assertEqual(self.r["takeDone"]["w-done"]["full"], [])
        self.assertEqual(self.r["wallTake"], self.r["fullTake"])          # the Wall writes the full card's line
        self.assertEqual(self.r["wallTake"], [{"type": "claim", "body": {"card": "w-free"}, "links": {}}])
        self.assertEqual([k for k, _ in self.r["takeOffered"]], ["act.claim", "act.done"])   # as the Deal's offers give them

    def test_a_released_or_returned_card_is_free_to_take(self):
        self.assertEqual(dict(self.r["freeAgain"]), {"released": ["act.claim"], "returned": ["act.claim"], "done": [], "retracted": []})
        self.assertEqual(self.r["noReader"], [])                          # no reader named: nothing is hers to take

    def test_an_act_the_offers_refuse_is_refused(self):
        f = self.r["refused"]
        self.assertIsNone(f["decide"])                                    # d1 is decided: its offers hold no decide
        self.assertIsNone(f["done"])                                      # nor a card's done on a decision
        self.assertEqual(f["ratify"]["type"], "ratify")
        self.assertEqual(self.r["nullId"][:2], [None, None])               # a line never names [null]
        self.assertEqual(self.r["nullId"][2]["links"], {})                 # a room's agreement names no item

    def test_the_table_answers_a_request_as_the_deal_does(self):
        t, w = self.r["table"], self.w
        self.assertEqual(t["wrote"], [{"type": "answer", "body": {"answer": "accept"}, "links": {"answers": ["r1"]}}])
        self.assertEqual([a["label"] for a in t["acts"]], [w["act.answer.accept"], w["table.not_yet"], w["act.answer.decline"]])
        for a in t["acts"]:
            self.assertTrue(a["title"])
            self.assertIn(w["card.say_fold_line"].replace("{act}", a["label"]).replace("{means}", a["title"]), " ".join(t["folds"]))

    def test_threads_close_and_the_talks_agree_write_settle(self):
        th, ag, w = self.r["threads"], self.r["agree"], self.w
        self.assertNotIn("error", th, th.get("error"))
        self.assertEqual(th["wrote"], [{"type": "settle", "body": {"text": "Where we meet"}, "links": {"anchored_to": ["t1"]}}])
        self.assertEqual(th["title"], w["act.settle_means"])
        self.assertIn(w["act.settle"] + ": " + w["act.settle_means"], " ".join(th["folds"]))   # the Threads fold
        self.assertNotIn("error", ag, ag.get("error"))
        self.assertEqual(ag["wrote"], [{"type": "settle", "body": {"text": "We meet at the hall"}, "links": {"anchored_to": ["line-o1"]}}])
        self.assertIn(w["talk.agree"] + ": " + w["talk.agree_means"], " ".join(ag["folds"]))
        self.assertNotIn(w["talk.make_sight"], " ".join(ag["folds"]))     # the fold holds only the acts drawn

    def test_the_margin_and_the_chain_open_their_cards(self):
        m, c, w = self.r["margin"], self.r["chain"], self.w
        self.assertEqual((m["opened"], m["agreed"]), (["a1"], ["o1"]))
        for a in m["acts"]:
            self.assertIn(w["card.say_fold_line"].replace("{act}", a["label"]).replace("{means}", a["title"]), " ".join(m["folds"]))
        self.assertNotIn("error", c, c.get("error"))
        self.assertTrue(c["opened"])                                       # the station's title opens the full card
        self.assertTrue(c["face"])                                         # the station wraps the one face
        self.assertEqual(c["title"], w["card.open_full_means"])

    def test_the_bodies_acts_say_what_they_do(self):
        src = (HUD / "bodies.js").read_text(encoding="utf-8")
        for k in ("bodies.ho.mark_read", "bodies.ho.archive", "bodies.opt_read", "bodies.mark_reviewed", "bodies.opt_deal", "bodies.opt_judge"):
            self.assertRegex(src, r'actsFold\(ctx, \[[^;]*t\("%s"\)' % re.escape(k), k)   # each in a fold beside its act
        self.assertEqual(src.count('actFor(thing, "act.witness"') + src.count('"act.witness", null, ctx.state'), 3)

    # the engine's acts, wired (acts.json now names them) -------------------------------------------------------

    def engine_acts(self):
        if not hasattr(self, "_ea"):
            cards, holons = engine_dealt()
            out = subprocess.run([shutil.which("node"), "--input-type=module", "-e", ENGINE_ACTS,
                                  json.dumps([HUD.as_uri(), self.w, self.st, cards, holons])], capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            type(self)._ea = json.loads(out.stdout)
        return self._ea

    def test_pass_it_on_writes_elevate_to_the_wider_circle(self):
        r, w = self.engine_acts(), self.w
        self.assertEqual(r["sight"]["line"], {"type": "elevate", "body": {"what": "s2", "to": "holon-commons"}, "links": {}})
        self.assertEqual(r["sight"]["drawn"][0], [w["act.elevate"], w["act.elevate_means"], "act.elevate"])   # acts.json's words
        self.assertEqual([d[0] for d in r["sight"]["drawn"]], [w["act.elevate"], "Keep it here", "Not yet"])
        self.assertEqual(r["sight"]["lost"]["type"], "say")                # no wider circle known: asked of her agent, never to null
        self.assertEqual(r["pain"]["line"], {"type": "elevate", "body": {"what": "s2", "to": "holon-commons"}, "links": {}})
        self.assertIn([w["act.elevate"], "act.elevate"], r["pain"]["drawn"])

    def test_bodies_mark_it_read_is_the_engines_witness(self):
        r, w = self.engine_acts(), self.w
        self.assertEqual(r["handoff"]["line"], {"type": "witness", "body": {}, "links": {"witnesses": ["h1"]}})
        self.assertEqual(r["handoff"]["drawn"][0], [w["act.witness.on_handoff"], w["act.witness.on_handoff_means"], "act.witness"])
        self.assertIsNone(r["handoff"]["agent"])                           # not offered to this reader: refused, never written
        src = (HUD / "bodies.js").read_text(encoding="utf-8")
        self.assertEqual(src.count('"act.witness"'), 4)                    # both of Bodies' witness lines, through the one map
        self.assertIn("st.deal.cards) || []).find((c) => c && c.id === b.handoff)", src)

    def test_the_committors_hand_back_carries_her_why(self):
        w = self.w
        label = w["act.release.on_commitment.as_committor"]
        self.assertIn(label, [a["label"] for a in self.r["kept"]["deal"]["acts"]])
        self.assertEqual(self.r["handBack"]["asked"], True)                # her why is asked for before anything is written
        self.assertEqual(self.r["handBack"]["wrote"], [{"type": "release", "body": {"commitment": "c-mine", "why": "My own words"}, "links": {}}])

    def test_the_margins_agree_writes_through_the_one_map(self):
        r = self.engine_acts()["margin"]
        self.assertEqual(r[0], {"type": "commit", "body": {"card": "a1", "by": "2026-11-02"}, "links": {}})
        self.assertEqual(r[1], {"type": "say", "body": {"text": "We meet Friday", "voice": "human-words"}, "links": {}})
        self.assertEqual(r[2]["type"], "card")
        self.assertIsNone(r[3])                                            # no words: nothing to agree to
        dock = (HUD / "dock.js").read_text(encoding="utf-8")
        self.assertIn("const line = offeredLine(it, s);", dock)
        self.assertNotIn('ctx.act("commit"', dock)

    # the cold read ----------------------------------------------------------------------------------------

    def test_the_deal_opens_with_the_three_answers(self):
        o, w = self.r["opens"], self.w
        self.assertEqual(len(o["three"]), 2)                                # connected, then (after the opener) waiting
        self.assertEqual(o["three"][0], w["deal.three.connected_none"])
        self.assertTrue(o["three"][1].startswith("You are waiting on"))
        self.assertEqual(len(o["line"]), 1)
        self.assertIn("five cards here", o["line"][0])                     # the opener says the pile's own count
        self.assertEqual(o["count"], ["1 of %d" % o["pile"]])              # the pile is counted from one, of itself
        self.assertEqual(o["stake"], ["Nothing waits on it yet."])          # a clause that is a sentence, said as one
        for k in ("deal.stake", "deal.stake_whole"):
            self.assertNotIn("waits on this", w[k])                       # the stake takes a clause; never "... waits on this"

    # law 4 ------------------------------------------------------------------------------------------------

    def test_every_act_drawn_says_what_it_does(self):
        w = self.w
        line = w["card.say_fold_line"]
        groups = [self.r["request"][p] for p in ("deal", "full", "room", "talk")] + [self.r[k][p] for k in ("ratify", "settle", "kept", "pain") for p in ("deal", "room")]
        groups += [{"acts": x["wall"], "folds": x["wallFold"], "inline": []} for x in self.r["takeDone"].values() if x["wall"]]
        groups += [{"acts": self.r["request"]["room"]["chosenActs"], "folds": self.r["request"]["room"]["chosenFolds"], "inline": []}]
        for g in groups:
            self.assertTrue(g["acts"])
            fold, inline = " ".join(g["folds"]), " ".join(g.get("inline") or [])
            for a in g["acts"]:
                self.assertTrue(a["title"], a)                             # on hover
                in_fold = line.replace("{act}", a["label"]).replace("{means}", a["title"]) in fold
                self.assertTrue(in_fold or a["title"] in inline, a)       # and on the face: beneath it, or in the fold
                self.assertFalse(in_fold and a["title"] in inline, a)     # never both: the fold holds what is not said inline
            if any(line.replace("{act}", a["label"]).replace("{means}", a["title"]) in fold for a in g["acts"]):
                self.assertIn(w["card.say_fold_title"], fold)
            titles = [a["title"] for a in g["acts"]]
            self.assertEqual(len(titles), len(set(titles)), titles)       # one meaning per act

    def test_strings_carry_every_key_of_acts_json(self):
        w, aj = self.w, _acts_json()
        for sec in ("acts", "roles"):
            for k, v in aj[sec].items():
                self.assertEqual(w.get(k), v["label"], k)
                if k not in GATE_FIXED:
                    self.assertEqual(w.get(k + "_means"), v["meaning"], k)
                self.assertTrue(w.get(k + "_means"), k)
                for kind, kv in (v.get("kinds") or {}).items():
                    if kv.get("label"):
                        self.assertEqual(w.get(k + ".on_" + kind), kv["label"], (k, kind))
                    if kv.get("meaning"):
                        self.assertEqual(w.get(k + ".on_" + kind + "_means"), kv["meaning"], (k, kind))
                    for who, av in (kv.get("as") or {}).items():
                        self.assertEqual(w.get(k + ".on_" + kind + ".as_" + who), av["label"], (k, kind, who))
                        self.assertEqual(w.get(k + ".on_" + kind + ".as_" + who + "_means"), av["meaning"], (k, kind, who))
        self.assertNotIn("settled", w["act.wallet.settle_means"])

    # law 5 ------------------------------------------------------------------------------------------------

    def test_a_tap_opens_the_full_card(self):
        q = self.r["queue"]
        self.assertTrue(q)
        for row in q:
            self.assertEqual(row["title"], [row["id"]], row)               # the title opens the full card, even with no card
            self.assertEqual(row["foot"], [row["id"]], row)                # the foot goes to the same place
            self.assertEqual(row["went"], [], row)                         # never leaves for another view
        self.assertIn("c-mine", [row["id"] for row in q])                  # no state card by its id: the title once left for the Deal
        self.assertEqual(self.r["ledger"]["opened"], ["a1"])
        self.assertEqual(self.r["ledger"]["title"], self.w["card.open_full_means"])
        self.assertEqual(self.r["sightings"]["opened"], ["s1"])
        self.assertEqual(self.r["sightings"]["title"], self.w["card.open_full_means"])
        self.assertTrue(self.r["sightings"]["folds"])

    def test_connections_open_the_card_they_name(self):
        node = shutil.which("node")
        src = ENGINE / "fixtures" / "hq"
        if not src.is_dir():
            self.skipTest("no fixtures/hq beside the engine")
        tmp = tempfile.mkdtemp(prefix="one-card-conn-")
        try:
            hq = os.path.join(tmp, "hq")
            shutil.copytree(src, hq, symlinks=True)
            st = json.loads(json.dumps(engine_mod.build_state(hq, now=NOW), default=str))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rows = st["connections"]["rows"]
        self.assertTrue(rows)
        rows[0].setdefault("agreement", {})["id"] = rows[0].get("agreement", {}).get("id") or "agreement-one"
        want = rows[0]["agreement"]["id"]
        out = subprocess.run([node, "--input-type=module", "-e", CONN, json.dumps([(HUD / "connections.js").as_uri(), st, self.w])],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        r = json.loads(out.stdout)
        self.assertEqual(r["opened"], [want])
        self.assertEqual(r["title"], self.w["conn.act.open_means"])
        self.assertIn(self.w["conn.act.open"], r["acts"])

    # one face ------------------------------------------------------------------------------------------------

    def test_the_wall_and_the_chain_wrap_the_one_face(self):
        for cid, x in self.r["takeDone"].items():
            if x["sticky"] is not None:
                self.assertIn(next(c["title"] for c in self.st["cards"] if c["id"] == cid), x["sticky"])
        chain = (HUD / "chain.js").read_text(encoding="utf-8")
        wall = (HUD / "wall.js").read_text(encoding="utf-8")
        self.assertIn('form: "station"', chain)
        self.assertIn('form: "sticky"', wall)
        self.assertNotIn('h("button", { class: "road-title"', chain)     # the station never redraws the face's title
        self.assertNotIn('class: "wall-note-title"', wall)


# law 6: the words ----------------------------------------------------------------------------------------------

def _source(path):
    s = Path(path).read_text(encoding="utf-8")
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"(?m)^\s*//.*$", "", s)
    return re.sub(r"(?m)\s//\s.*$", "", s)          # a comment after the code on its line


def _literals(src):
    return [a or b or c for a, b, c in re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`]*)`', src)]


def _css_classes():
    out = set()
    for f in HUD.glob("*.css"):
        out |= set(re.findall(r"\.([A-Za-z_][\w-]*)", re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)))
    return out


# The regions this brief edited, each [start, end) in its file: every literal in them is a strings.json key, a key
# family, CSS classes, or one of the data tokens below, never a word on the screen.
REGIONS = {
    "act-map.js": [("const ID = (x)", None)],
    "card.js": [("export const isOver", "export function spareDays("), ("function slimFace(", "function homeId("),
                ("const list = h(\"div\", { class: \"card-options\"", "if (!large && foot)")],
    "deal.js": [("export function pileOf(", "export function owedLine("), ("const three = threeLines(ctx);", "root.append(head);"),
                ("function settle(dc, option", "function step(dir)"), ("const pile = pileOf(ctx, d);", "async function playOpening(")],
    "card-full.js": [("const onFace = new Set(", "root.append(face);"), ("function answer(lbl, i, words", "const sec = section(ctx, \"card.full.sec.stands\")")],
    "room.js": [("export function dealCard(", None)],
    "talk.js": [("function renderOne()", "function answeredCard()"), ("function agree(", "function yes("),
                ("const sights = shown.some(", "function asks()")],
    "talk-place.js": [("const opts = (dc.options || []).filter(", "const choices ="), ("const a0 = actFor(dc, oi", "const kind = dc.kind")],
    "table.js": [("function offeredCard(o)", "function holderChip("), ("const dc = ((st.deal", "if (!C.phone) art.append(h(\"div\""),
                 ("forMe ? h(\"button\"", "function draftCard(")],
    "wall.js": [("function detail(c, note)", "const col = note.parentElement;")],
    "chain.js": [("renderCard(ctx, cardModel(ctx, { card: c })", "i.pace ?")],
    "threads.js": [("const means = [];", "close = C.openSheet(")],
    "bodies.js": [("const dealt = (((ctx.state", "if (card) localReviewed"), ("const read = actWords(", "} else foot.append("),
                  ("const thing = ((st.deal", "close = ctx.openSheet({")],
    "margin.js": [("export function renderMargin(", None)],
    "queue.js": [("export default function createQueue()", None)],
    "sightings.js": [("function sightingsOf(", "function theMap(")],
    "connections.js": [("const theActs = () =>", "function agreementCadence(")],
    "ledger.js": [("const witnessW", "for (const x of holons)"), ("function row(e, x, keeper)", "function addTime()")],
    "dock-card.js": [("const a0 = actFor(dc, label, null, st);", "return { ok: true };\n}")],
    "shell.js": [("function cardAct(type, c, line)", "function sayOnCard(")],
    "dock.js": [("const line = offeredLine(it, s);", "S.local.set(it.id")],
}
# Tokens the edited code compares against the record or the DOM and never shows: the registry's line types, fields
# and values, the act keys' prefix, card states, the DOM's words, CSS escapes.
DATA = {"answer", "accept", "decline", "ratify", "decide", "kept", "witness", "release", "settle", "claim", "done", "hand",
        "elevate", "say", "ask", "commitment", "card", "text", "intent", "string", "object", "function", "number", "thread",
        "request", "decision", "tea", "handoff", "holding", "undone", "kept-here", "ready", "open", "released", "returned",
        "taken", "past", "receipt", "act.", "button", "details", "dialog", "aria-haspopup", "NFC", "talk", "wall", "queue",
        "ledger", "large", "compact", "row", "sticky", "station", "main", "me", "others", "tablist", "tab", "tabpanel",
        "aria-selected", "true", "false", "side", "deal", "_means", ".on_", "[", "]", "hud.", "", " ", "q-", "agent", "said",
        "agreed", "said_in_room", "sight", "queued", "BUTTON", "ink-", ".as_", "pain", "region", "aria-label", "data-confirm", "status",
        "sightings", "connections", "aria-pressed", "section", "group", "ask-", "yes-", "later.", "aside.", "kind", "one-card",
        "record", "aria-expanded",
        # the DOM's tags and events, separators and glyphs the views already draw, CSS custom properties and selectors
        "div", "li", "ul", "p", "span", "article", "summary", "td", "tr", "select", "textarea", "click", "center", " · ", " ✓", "×",
        "--d-card", "--d-quick", "--e-settle", "--d-settle", ".card--large", ".deal-settled",
        # the record's states and kinds these views compare against
        "did", "retracted", "refused", "none", "asked", "question", "rfg", "written", "yes", "constraint", "prose", "agreeing",
        "declined", "beyond", "cell", "claimed",
        # class names the views already set, with no rule of their own
        "conv2-compose", "ledger-time",
        # her words' voice and the fields she fills (types.json), a joiner, the colors' names, glyphs, the DOM's attributes
        "human-words", "note", "why", "commit", "to", ". ", "aria-hidden", "grey", " →", "← ", ".card-title", "title"}


class TheWords(unittest.TestCase):

    def test_every_key_in_the_edited_files_resolves(self):
        keys = set(_strings())
        bad = []
        for name in REGIONS:
            src = _source(HUD / name)
            for k in re.findall(r'\bt\(\s*"([^"]+)"', src):
                if not (k in keys or (k.endswith((".", "_")) and any(x.startswith(k) for x in keys))):
                    bad.append((name, k))
        self.assertEqual(bad, [])
        self.assertEqual(len(REGIONS), 20)                                  # every file this card's work edited

    def test_no_words_in_the_edited_code(self):
        keys, classes = set(_strings()), _css_classes()
        bad = []
        for name, regions in REGIONS.items():
            src = _source(HUD / name)
            for start, end in regions:
                i = src.index(start)
                part = src[i:src.index(end, i) if end else len(src)]
                for lit in sorted(set(_literals(part))):
                    if lit in keys or lit in DATA or re.fullmatch(r"[\d.]*", lit) or "${" in lit:
                        continue
                    if lit.endswith((".", "_")) and any(k.startswith(lit) for k in keys):
                        continue
                    if lit.split() and all(tok in classes for tok in lit.split()):
                        continue
                    if re.fullmatch(r"#/[a-z]+", lit) or re.fullmatch(r"[a-z]+:", lit):
                        continue
                    bad.append((name, lit))
                for k in re.findall(r'\bt\(\s*"([^"]+)"', part):
                    if not (k in keys or (k.endswith((".", "_")) and any(x.startswith(k) for x in keys))):
                        bad.append((name, "t: " + k))
        self.assertEqual(bad, [])

    def test_the_new_words_keep_the_kits_voice(self):
        w = _strings()
        mine = {k: v for k, v in w.items() if isinstance(v, str) and (k.startswith("act.") or k.startswith("role.") or k.endswith("_means"))}
        self.assertTrue(mine)
        for k, v in mine.items():
            self.assertIsNone(re.search(r"\b[A-Za-z]+n't\b|\b(it|that|there|what|who)'s\b|\b(I|you|we|they)'(d|ll|re|ve|m)\b", v, re.I), k)
            self.assertNotIn("promise", v.lower(), k)
            self.assertIsNone(re.search(r"person:|agent:|\bholons?\b|\bhouse\b|\bestate\b", v, re.I), k)


if __name__ == "__main__":
    unittest.main()
