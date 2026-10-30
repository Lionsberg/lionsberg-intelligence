// room.js: the Room layout's frame (DESIGN-ROOM §6, §8.1). One table, three inks.
//
// The phases (before · door · work · close · after), the top strip and the part strip, the
// presence row and its fold, the posture card, the agent's admission, the private chip
// "Your deal", "Show to the room", the curing line, and the arrangement: three columns at
// desk (the Page · the Talk · the Table), two at tablet (the Talk, and the Table or the Page
// by a segmented control), and on a phone the Talk as home with the Page and the Table as
// sheets. It mounts talk.js, table.js and play.js's Page with one shared context.
//
// Below 600 px the Room is rebuilt for the phone: the Talk
// is the whole screen; the one thing asked of the person rises as one card from the foot above
// the line to offer; presence is a ring of small fields at the top edge, felt and not listed;
// the Table (with what was settled and committed this sitting, then the page) is one word away.
// On the desk, presence is one sentence that opens the fold; no faces row.
//
// The shell finds the Room at play.js (its PLUGINS map); play.js's default export hands the
// Room here. A view never fetches: every figure is read from ctx.state; every write is
// ctx.act from a person's own tap.

import { h } from "./card.js";
import createTalk from "./talk.js";
import createTable, { yourMove } from "./table.js";
import { createPage } from "./play.js";
import { useStyle, local, roomIdFor, postureKey, agentOf, lineById, minutesUntil, isElided } from "./inks.js";

const PHASES = ["before", "door", "work", "close", "after"];

export default function createRoom() {
  let root = null, ctx = null, rid = null, key = null;
  const subs = { talk: null, table: null, page: null };
  const sheetSubs = [];
  const mode = { shown: local.sget("room.shown", false), panel: local.sget("room.panel", "table"), tab: null };
  const shared = makeShared();
  const closers = [];
  const narrow = typeof matchMedia === "function" ? matchMedia("(max-width: 599px)") : null;
  const onNarrow = () => { if (root && ctx) build(); };

  function cx(c) {
    const room = (c.state.rooms || {})[rid] || null;
    return Object.freeze({ ...c, roomId: rid, room, shared, shown: mode.shown, phase: phaseOf(c, room),
      // one frame for the sitting at every width: the one card, the Talk as its ground,
      // the Table (with who is here) behind one act; no columns of panels
      phone: true, narrow: !!(narrow && narrow.matches), openTable: () => openPanel(ctx, "table") });
  }

  function phaseOf(c, room) {
    if (!room) return "none";
    if (room.shape) return shapeDoor(c, room).length ? "door" : "shape";
    const p = PHASES.includes(room.phase) ? room.phase : room.closed ? "after" : room.opened ? "work" : "before";
    if ((p === "work" || p === "door" || p === "close") && doorNeeds(c, room).length) return "door";
    return p === "door" ? "work" : p;
  }

  /** What the door still asks of this wearer: the posture, then her agent. */
  function doorNeeds(c, room) {
    const st = c.state, me = st.actor, d = local.sget("door." + rid, {});
    const out = [];
    const post = room.posture;
    if (post && !(post.agreed_by || []).includes(me) && !d.posture) out.push("posture");
    const mine = myAgent(c);
    const inRoom = (room.present || []).some((p) => p.actor === mine);
    if (mine && !inRoom && !d.affirm && !d.declined) out.push("affirm");
    return out;
  }
  function myAgent(c) {
    const a = (c.state.actors || []).find((x) => x.kind === "agent" && x.for === c.state.actor);
    return a ? a.id : null;
  }

  function mount(el, c) {
    useStyle("room.css");
    root = el;
    ctx = c;
    rid = roomIdFor(c);
    if (narrow) narrow.addEventListener("change", onNarrow);
    build();
  }

  function update(c) {
    ctx = c;
    const next = roomIdFor(c);
    if (next !== rid) { rid = next; key = null; }
    const k = structureKey(cx(c));
    if (k !== key) { build(); return; }
    const C = cx(c);
    if (C.room && C.room.shape) return;
    renderStrip(C);
    for (const s of Object.values(subs)) if (s) s.update(C);
    for (const s of [...sheetSubs]) {
      if (s.el.isConnected) s.inst.update(C);
      else { s.inst.unmount(); sheetSubs.splice(sheetSubs.indexOf(s), 1); }
    }
    renderTabs(C);
  }

  function unmount() {
    if (narrow) narrow.removeEventListener("change", onNarrow);
    // a sheet never outlives its place
    for (const c of closers.splice(0)) { try { c(); } catch { /* already closed */ } }
    for (const s of Object.values(subs)) if (s) s.unmount();
    for (const s of sheetSubs) s.inst.unmount();
    sheetSubs.length = 0;
    subs.talk = subs.table = subs.page = null;
    root = null;
  }

  function structureKey(C) { return [rid, C.phase, mode.shown, !!C.room, C.prefs.large, C.phone, shapeKey(C)].join("|"); }

  // ------------------------------------------------------------------ the frame

  let $strip = null, $tabs = null, $grid = null;

  function build() {
    for (const s of Object.values(subs)) if (s) s.unmount();
    subs.talk = subs.table = subs.page = null;
    root.textContent = "";
    const C = cx(ctx);
    key = structureKey(C);
    const t = C.t;

    if (!C.room) {
      const unread = C.read.unreadable(C.state).find((s) => s.holon === rid);
      root.append(h("div", { class: "room room--none" },
        h("p", { class: "voice room-empty" }, unread ? t("room.error") : t("room.none")),
        unread ? h("button", { class: "pill", onclick: () => location.reload() }, t("app.try_again")) : null));
      return;
    }

    if (C.room.shape) { root.append(renderShape(C)); $strip = null; $tabs = null; $grid = null; return; }

    const wrap = h("div", { class: `room${mode.shown ? " is-shown" : ""}`, dataset: { phase: C.phase, panel: mode.panel } });
    if (C.loading) wrap.classList.add("is-reading");
    $strip = h("header", { class: "room-strip" });
    wrap.append($strip);
    renderStrip(C);

    if (C.phase === "door") {
      wrap.append(renderDoor(C));
      root.append(wrap);
      return;
    }

    // the phone, in a sitting: the top edge, then the Talk as the whole screen (its foot holds
    // the one card and the line to offer)
    if (C.phase === "work" || C.phase === "close") {
      wrap.classList.add("room--phone");
      const talkHost = h("div", { class: "room-col room-talk", role: "region", "aria-label": t("room.talk") });
      wrap.append(talkHost);
      root.append(wrap);
      subs.talk = createTalk(); subs.talk.mount(talkHost, C);
      $tabs = null; $grid = null;
      return;
    }

    $grid = h("div", { class: "room-grid", dataset: { panel: mode.panel } });
    const colPage = h("div", { class: "room-col room-page", role: "region", "aria-label": t("room.page") });
    const colTalk = h("div", { class: "room-col room-talk", role: "region", "aria-label": t("room.talk") });
    const colTable = h("div", { class: "room-col room-table", role: "region", "aria-label": t("room.table") });
    const seg = h("div", { class: "room-seg", role: "tablist", "aria-label": t("room.panel_label") },
      ["table", "page"].map((p) => h("button", { role: "tab", class: "chip", "aria-selected": String(mode.panel === p),
        onclick: () => { mode.panel = p; local.sset("room.panel", p); $grid.dataset.panel = p; wrap.dataset.panel = p;
          seg.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-selected", String(["table", "page"][i] === p))); } },
      t("room." + p))));
    const side = h("div", { class: "room-side" }, seg, colTable, colPage);
    $grid.append(colPage, colTalk, side);
    wrap.append($grid);

    if (C.phase === "after") wrap.insertBefore(renderAfter(C), $grid);
    if (C.phase === "before") wrap.insertBefore(renderBefore(C), $grid);

    $tabs = h("nav", { class: "room-tabs", "aria-label": t("room.tabs_label") });
    wrap.append($tabs);
    root.append(wrap);

    subs.page = createPage(); subs.page.mount(colPage, C);
    subs.table = createTable(); subs.table.mount(colTable, C);
    if (C.phase === "work" || C.phase === "close") { subs.talk = createTalk(); subs.talk.mount(colTalk, C); }
    else colTalk.append(h("p", { class: "dust room-talk-still" }, C.phase === "before" ? t("room.talk_before") : t("room.talk_after")));
    renderTabs(C);
  }

  // ------------------------------------------------------------------ the top strip

  function renderStrip(C) {
    if (!$strip) return;
    const t = C.t, f = C.fmt, room = C.room, st = C.state;
    $strip.textContent = "";
    if (C.phase === "work" || C.phase === "close") { renderEdge(C); return; }
    const pk = postureKey(C, rid);
    const line1 = h("div", { class: "room-strip-line" },
      h("h2", { class: "caps room-name" }, room.name || C.read.holonName(st, rid)),
      h("button", { class: `chip posture-chip posture--${pk}`, onclick: () => explainPosture(C),
        "aria-label": t("room.posture_chip_sr", { posture: t("room.posture." + pk) }) }, t("room.posture." + pk)),
      partStrip(C),
      h("span", { class: "room-strip-gap" }),
      !mode.shown ? privateChip(C) : null,
      C.phase !== "door" ? h("button", { class: "link-btn show-room", "aria-pressed": String(mode.shown),
        onclick: () => { mode.shown = !mode.shown; local.sset("room.shown", mode.shown); build(); } },
        mode.shown ? t("room.show_end") : t("room.show")) : null);
    $strip.append(line1);
    if (mode.shown) $strip.append(h("p", { class: "room-shown-line", role: "status" }, t("room.shown_line")));
    if (room.purpose) $strip.append(h("p", { class: "voice room-purpose" }, room.purpose));
    if (C.phase === "before") {
      $strip.append(h("p", { class: "dust" }, t("room.before_line")));
      return;
    }
    $strip.append(presence(C));
    if (room.play_by_play_keeper && C.phase !== "after") {
      $strip.append(h("p", { class: "dust pbp-keeper" }, t("room.pbp_keeper", { who: whoAny(C, room.play_by_play_keeper) })));
    }
    if (C.phase === "close") {
      $strip.append(h("div", { class: "room-close-bar" },
        h("button", { class: "pill primary", onclick: () => openLeaves(C) }, t("room.leaves_open"))));
    }
    if (C.loading) $strip.append(h("p", { class: "dust" }, t("app.reading")));
    if (C.offline) $strip.append(h("p", { class: "dust room-offline" }, t("room.offline")));
  }

  /** The part on the table now, and its clock in words. A clock run past twice its part's length
      tells nothing true about this sitting (a live room on old part times read "38 minutes past"
      beside a talk stamped 9:19), so it is not shown. */
  function partNow(C) {
    const t = C.t, f = C.fmt, room = C.room;
    const parts = Array.isArray(room.parts) ? room.parts : [];
    const cur = parts.find((p) => p.n === room.current_part);
    if (!cur) return null;
    let left = null;
    if (cur.started && cur.minutes && f.date(cur.started)) {
      const end = new Date(f.date(cur.started).getTime() + cur.minutes * 60000).toISOString();
      const m = minutesUntil(C, end);
      if (m != null && m <= cur.minutes && -m <= cur.minutes) left = m > 1 ? t("room.minutes_left", { n: f.number(m) }) : m === 1 ? t("room.one_minute_left")
        : m === 0 ? t("room.no_minutes_left") : t("room.minutes_over", { n: f.number(-m, true) });
    }
    return { cur, parts, left };
  }

  function partStrip(C) {
    const t = C.t, f = C.fmt, p = partNow(C);
    if (!p) return null;
    return h("span", { class: "part-strip dust" },
      [t("room.part_of", { n: f.number(p.cur.n, true), total: f.number(p.parts.length, true) }), p.cur.title, p.left].filter(Boolean).join(" · "));
  }

  // ------------------------------------------------------------------ the phone's top edge

  function renderEdge(C) {
    const t = C.t, p = partNow(C);
    $strip.classList.add("room-edge");
    $strip.append(
      h("p", { class: "edge-part" }, h("span", { class: "caps edge-room" }, C.room.name || C.read.holonName(C.state, rid)),
        p ? h("span", { class: "edge-title" }, p.cur.title) : null,
        p && p.left ? h("span", { class: "dust" }, " · " + p.left) : null),
      h("button", { class: "link-btn edge-table", onclick: () => openPanel(C, "table"), "aria-label": t("room.table") + ". " + countWords(C) }, t("room.table")));
    if (mode.shown) $strip.append(h("p", { class: "room-shown-line", role: "status" }, t("room.shown_line")));
    if (C.offline) $strip.append(h("p", { class: "dust room-offline" }, t("room.offline")));
  }

  function countWords(C) {
    const t = C.t, f = C.fmt;
    const present = Array.isArray(C.room.present) ? C.room.present : [];
    const people = present.filter((p) => p.kind === "person"), agents = present.filter((p) => p.kind === "agent");
    if (!people.length) return t("room.nobody");
    return (people.length === 1 ? t("room.count.people_one") : t("room.count.people", { n: f.number(people.length) }))
      + (agents.length === 0 ? t("room.count.agents_none") : agents.length === 1 ? t("room.count.agents_one")
        : t("room.count.agents", { n: f.number(agents.length, true) }));
  }

  /** Who is here, as a fold: each person by role with what they are doing and their agent; the
      room's setting; Show to the room. The same fold on the phone (the ring) and the desk (the sentence). */
  function openPresence(C) {
    const close = C.openSheet({ title: C.room.name || C.read.holonName(C.state, rid), body: presenceBody(C) });
    if (typeof close === "function") closers.push(close);
  }

  /** Who is here, and the room's private acts (your deal, show to the room), as a block. */
  function presenceBody(C) {
    const t = C.t, st = C.state, room = C.room;
    const present = Array.isArray(room.present) ? room.present : [];
    const agents = present.filter((p) => p.kind === "agent");
    const rows = present.filter((p) => p.kind === "person").map((p) => {
      const me = p.actor === st.actor;
      const ag = agents.filter((a) => a.for === p.actor);
      return h("li", null,
        h("span", null, me ? t("app.you") : C.read.who(st, p.actor, rid)),
        p.state ? h("span", { class: "dust" }, " · " + t("room.state." + p.state.replace(/ /g, "_"))) : null,
        p.house === "second" ? h("span", { class: "dust" }, " · " + t("room.from_second_house")) : null,
        ag.map((a) => {
          const words = t("room.with_agent", { agent: agentOf(C, a.actor, rid), state: a.state ? t("room.state." + a.state.replace(/ /g, "_")) : t("room.state.listening") });
          // only your own agent's account opens (everything it said here is yours to read, §4.3)
          return a.for === st.actor && !mode.shown ? h("button", { class: "link-btn fold-agent", onclick: () => openAccount(C, a) }, words)
            : h("p", { class: "dust fold-agent" }, words);
        }));
    });
    const pk = postureKey(C, rid);
    const body = h("div", { class: "room-fold room-sheet-part" },
      h("p", null, countWords(C)),
      h("ul", { class: "fold-people" }, rows),
      room.play_by_play_keeper ? h("p", { class: "dust" }, t("room.pbp_keeper", { who: whoAny(C, room.play_by_play_keeper) })) : null,
      h("p", { class: "dust" }, t("room.posture_line", { posture: t("room.posture." + pk) }), " ",
        h("button", { class: "link-btn", onclick: () => explainPosture(C) }, t("room.posture_what", { posture: t("room.posture." + pk) }))));
    const d = roomDeal(C);
    const closeAll = () => { for (const c of closers.splice(0)) { try { c(); } catch { /* closed */ } } };
    body.append(h("div", { class: "fold-acts" },
      d && d.cards.length && !mode.shown && C.phase !== "after" ? h("button", { class: "pill", onclick: () => { closeAll(); openDeal(C); } },
        t("deal.small", { count: String(d.cards.length) })) : null,
      h("button", { class: "pill quiet", onclick: () => { mode.shown = !mode.shown; local.sset("room.shown", mode.shown); closeAll(); build(); } },
        mode.shown ? t("room.show_end") : t("room.show"))));
    return body;
  }

  function explainPosture(C) {
    const pk = postureKey(C, rid);
    C.openSheet({ title: C.t("room.posture." + pk), body: h("p", null, C.t("room.posture_explain." + pk)) });
  }

  function whoAny(C, actor) {
    if (!actor || isElided(actor)) return C.t("record.hidden");
    return C.read.actorKind(C.state, actor) === "agent" ? agentOf(C, actor, rid) : C.read.who(C.state, actor, rid);
  }

  // ------------------------------------------------------------------ presence

  function presence(C) {
    // the desk: one sentence, which opens the fold (no faces row; DESIGN-THE-BAR §2, the Room)
    const present = Array.isArray(C.room.present) ? C.room.present : [];
    if (!present.some((p) => p.kind === "person")) return h("div", { class: "presence-wrap" }, h("p", { class: "dust" }, C.t("room.nobody")));
    return h("div", { class: "presence-wrap" }, h("button", { class: "link-btn room-count", onclick: () => openPresence(C) }, countWords(C)));
  }

  /** Tap your agent's ring: everything it said here, to anyone, is yours to read (§4.3). */
  function openAccount(C, a) {
    const t = C.t, st = C.state, room = C.room;
    const talk = ((st.hud && st.hud.talk && st.hud.talk[rid]) || []);
    const offeredMine = (room.offered || []).filter((o) => o.by === a.actor).map((o) => lineById(st, o.line)).filter(Boolean);
    const said = talk.filter((s) => s.by === a.actor);
    const toIt = talk.filter((s) => s.whisper && Array.isArray(s.to) && s.to.includes(a.actor));
    const list = (label, items, fn) => h("section", { class: "account-sec" }, h("h3", { class: "eyebrow" }, label),
      items.length ? h("ul", { class: "account-list" }, items.map((x) => h("li", null, fn(x)))) : h("p", { class: "dust" }, t("room.account_none")));
    const affirm = (st.lines || []).find((l) => l.type === "affirm" && l.holon === rid && l.actor === st.actor && l.body && l.body.agent === a.actor);
    const body = h("div", { class: "account" },
      h("p", { class: "voice" }, t("room.account_line")),
      list(t("room.account_offered"), offeredMine, (l) => h("span", { class: "agent-text" }, l.body && l.body.text)),
      list(t("room.account_whispered"), said.filter((s) => s.whisper), (s) => [h("span", { class: "agent-text" }, s.text),
        h("span", { class: "dust" }, " · " + t("room.whisper_to", { who: (s.to || []).map((x) => whoAny(C, x)).join(", ") }))]),
      list(t("room.account_said"), said.filter((s) => !s.whisper), (s) => h("span", { class: "agent-text" }, s.text)),
      list(t("room.account_to_it"), toIt, (s) => [h("span", { class: "agent-text" }, s.text), h("span", { class: "dust" }, " · " + t("room.whisper_from", { who: whoAny(C, s.by) }))]));
    const actions = affirm ? [h("button", { class: "pill quiet", onclick: () => {
      C.act("supersede", {}, { supersedes: [affirm.id] }, rid, { confirmed: true, label: t("room.agent_leaves") });
      close();
    } }, t("room.agent_leave"))] : [];
    const close = C.openSheet({ title: t("app.agent_default"), body, actions });
  }

  // ------------------------------------------------------------------ the private chip: your deal

  function roomDeal(C) {
    const room = C.room;
    const d = C.phase === "close" && room.deal_close ? room.deal_close : room.deal_open;
    if (d && Array.isArray(d.cards)) return d;
    const own = C.state.deal;
    if (own && Array.isArray(own.cards)) return { ...own, cards: own.cards.filter((x) => x.holon === rid) };
    return null;
  }

  function privateChip(C) {
    const d = roomDeal(C);
    const n = d ? d.cards.length : 0;
    if (!n || C.phase === "after") return null;
    return h("button", { class: "chip private-chip", onclick: () => openDeal(C) }, C.t("deal.small", { count: String(n) }));
  }

  function openDeal(C) {
    const t = C.t, f = C.fmt, d = roomDeal(C);
    if (!d) return;
    const mins = d.cards.reduce((a, x) => a + (x.minutes || 0), 0);
    const body = h("div", { class: "room-deal" },
      h("p", { class: "voice deal-opening" }, t("deal.opening")),
      h("p", null, C.phase === "close" ? t("room.deal_close_count", { cost: f.aboutMinutes(mins) })
        : t("room.deal_open_count", { count: f.number(d.cards.length), cost: f.aboutMinutes(mins).toLowerCase() })),
      h("p", { class: "dust" }, t("room.private_line")));
    d.cards.forEach((dc, i) => body.append(dealCard(C, dc, i + 1, d.cards.length)));
    C.openSheet({ title: t("room.your_deal"), body });
  }

  function dealCard(C, dc, n, total) {
    const host = h("div", { class: "room-deal-card" });
    let chosen = null;
    const draw = () => {
      host.textContent = "";
      const m = C.card.cardModel(C, { deal: dc });
      host.append(C.card.renderCard(C, m, { form: "large", index: n, total, chosen,
        onChoose: (label) => { chosen = label; draw(); },
        onNotYet: () => { chosen = null; draw(); },
        onConfirm: (label) => { answerAct(C, dc, label); host.replaceChildren(h("p", { class: "dust" }, C.t("deal.answered_label_home", { option: label }))); } }));
    };
    draw();
    return host;
  }

  // An answer's event, as The Deal reads it: a commitment's first option is the
  // person's commitment; a decision's first option her decision; otherwise her words, anchored.
  function answerAct(C, dc, label) {
    const i = (dc.options || []).indexOf(label);
    const card = C.read.card(C.state, dc.id);
    const opts = { confirmed: true, label: C.t("deal.answered_label", { holon: C.read.holonName(C.state, dc.holon), option: label }) };
    if ((dc.kind === "commitment" || dc.kind === "request") && i === 0 && card) {
      return C.act("commit", { card: dc.id, by: card.by, size: card.minutes }, {}, dc.holon, opts);
    }
    if (dc.section === "decision" && i === 0) return C.act("decide", { text: label }, { answers: [dc.id] }, dc.holon, opts);
    return C.act("say", { text: label }, { anchored_to: [dc.id] }, dc.holon, opts);
  }

  // ------------------------------------------------------------------ the door (§2.2)

  function renderDoor(C) {
    const t = C.t, st = C.state, room = C.room;
    const needs = doorNeeds(C, room);
    const box = h("section", { class: "room-door", "aria-live": "polite" });
    if (needs[0] === "posture") {
      const pk = postureKey(C, rid);
      box.append(h("article", { class: "card door-card" },
        h("p", { class: "eyebrow" }, t("room.door_eyebrow")),
        h("h3", { class: "card-title" }, t("room.door_posture." + pk)),
        h("button", { class: "link-btn", onclick: () => explainPosture(C) }, t("room.posture_what", { posture: t("room.posture." + pk) })),
        h("div", { class: "card-options confirm" },
          h("button", { class: "pill primary", onclick: () => {
            C.act("posture", { posture: room.posture.posture, curing_days: room.posture.curing_days }, {}, rid,
              { confirmed: true, label: t("room.door_agreed") });
            const d = local.sget("door." + rid, {}); d.posture = true; local.sset("door." + rid, d); update(ctx);
          } }, t("room.door_agree")),
          h("button", { class: "pill quiet", onclick: () => C.openSheet({ title: t("room.door_ask"), body: h("p", null, t("room.door_ask_line")) }) }, t("room.door_ask")))));
    } else if (needs[0] === "affirm") {
      const agent = myAgent(C);
      box.append(h("article", { class: "card door-card" },
        h("p", { class: "eyebrow" }, t("room.door_eyebrow")),
        h("h3", { class: "card-title agent-text" }, t("room.door_affirm")),
        h("div", { class: "card-options confirm" },
          h("button", { class: "pill primary", onclick: () => {
            C.act("affirm", { agent, room: rid }, {}, rid, { confirmed: true, label: t("room.door_affirmed") });
            const d = local.sget("door." + rid, {}); d.affirm = true; local.sset("door." + rid, d); update(ctx);
          } }, t("room.door_let_in")),
          h("button", { class: "pill quiet", onclick: () => {
            const d = local.sget("door." + rid, {}); d.declined = true; local.sset("door." + rid, d); update(ctx);
          } }, t("room.door_not_today")))));
    }
    box.append(h("p", { class: "dust door-foot" }, t("room.door_foot")));
    return box;
  }

  // ------------------------------------------------------------------ before and after

  function renderBefore(C) {
    const t = C.t;
    const d = roomDeal(C);
    const box = h("section", { class: "room-before" });
    if (d && d.cards.length) {
      const mins = d.cards.reduce((a, x) => a + (x.minutes || 0), 0);
      box.append(h("p", { class: "voice deal-opening" }, t("deal.opening")),
        h("p", null, t("room.before_count", { count: C.fmt.number(d.cards.length), cost: C.fmt.aboutMinutes(mins).toLowerCase() })));
      d.cards.forEach((dc, i) => box.append(dealCard(C, dc, i + 1, d.cards.length)));
    }
    return box;
  }

  function renderAfter(C) {
    const t = C.t, st = C.state, room = C.room;
    const box = h("section", { class: "room-after" }, h("p", { class: "voice room-still" }, t("room.after_line")));
    if (room.curing_until) {
      const d = C.fmt.date(room.curing_until);
      box.append(h("p", { class: "dust" }, t("room.curing", { day: d ? C.fmt.dayName(d) : room.curing_until })));
    }
    const mine = (st.commitments || []).filter((k) => k.holon === rid && k.keeper === st.actor);
    const toMe = (st.commitments || []).filter((k) => k.holon === rid && k.witness === st.actor);
    const cards = (st.cards || []).filter((c) => c.holon === rid && c.holder === st.actor && !["done", "kept"].includes(c.state));
    const list = (label, items, text) => items.length ? h("div", { class: "carry" }, h("h3", { class: "eyebrow" }, label),
      h("ul", null, items.map((x) => h("li", null, text(x))))) : null;
    box.append(h("h3", { class: "caps" }, t("room.carry")),
      list(t("commitments.by_me"), mine, (k) => `${k.title} · ${C.fmt.by(k.by) || ""}`) || null,
      list(t("room.carry_cards"), cards, (c) => `${c.title} · ${C.fmt.by(c.by) || ""}`) || null,
      list(t("commitments.to_me"), toMe, (k) => k.title) || null);
    if (!mine.length && !cards.length && !toMe.length) box.append(h("p", { class: "dust" }, t("room.carry_none")));
    return box;
  }

  // ------------------------------------------------------------------ what leaves the room (§2.4)

  function openLeaves(C) {
    const t = C.t, st = C.state, room = C.room;
    const ids = Array.isArray(room.lines) ? room.lines : [];
    const hidden = postureKey(C, rid) !== "open";
    const items = ids.map((id) => lineById(st, id)).filter(Boolean);
    const body = h("div", { class: "leaves" },
      h("p", null, hidden ? t("room.leaves_line_hidden") : t("room.leaves_line")),
      h("ul", { class: "leaves-list" }, items.map((l) => h("li", null,
        h("span", { class: "dust" }, (hidden ? t("app.a_member") : whoAny(C, l.actor)) + " · "),
        (l.body && typeof l.body.text === "string" ? l.body.text : (l.body && l.body.title) || t("record.hidden")),
        l.verified === "signed" ? h("span", { class: "vmark v-signed", title: t("record.verified.signed") }, " ✓") : null))),
      h("p", { class: "dust" }, t("room.leaves_to")),
      room.posture && room.posture.curing_days ? h("p", { class: "dust" }, t("room.curing_days", { n: C.fmt.number(room.posture.curing_days, true) })) : null);
    let close = null;
    close = C.openSheet({ title: t("room.leaves_title"), body, actions: [
      h("button", { class: "pill primary", onclick: () => C.openPublish({ holon: rid, lines: ids,
        what: hidden ? t("room.publish_what_hidden", { n: C.fmt.number(ids.length, true) }) : t("room.publish_what", { n: C.fmt.number(ids.length, true) }) }) }, t("sheet.publish")),
      h("button", { class: "pill quiet", onclick: () => close && close() }, t("sheet.keep_here"))] });
  }

  // ------------------------------------------------------------------ the one shape (§10, a proposal)
  //
  // A room in one shape: the lobby, the great room, the vote, the writing, reflection, under a
  // participation posture agreed at the door and confirmed at the close. Everything shown is
  // state.rooms[id].shape, folded by the engine from the room's lines; what this screen did
  // before the stream returns is held on this device ("shape.<room>") and shown as done. The
  // facilitator's switch is the only act that moves the room; one part fills the screen at every
  // width, so the phone has one screen per part.

  const POSTURES = ["chatham-house", "fishbowl", "open", "off-the-record"];
  const SWITCH_NEXT = { gather: "propose", propose: "vote", vote: "write", write: "reflect", reflect: "close" };
  let shapeDraft = "";

  function mineLocal() { return local.sget("shape." + rid, {}); }
  function setLocal(patch) { local.sset("shape." + rid, { ...mineLocal(), ...patch }); }

  function shapeDoor(c, room) {
    const sh = room.shape;
    if (!sh || sh.closed) return [];
    const mine = sh.mine || {}, loc = local.sget("shape." + rid, {}), d = local.sget("door." + rid, {});
    if (!mine.agreed && !loc.agreed) return ["posture"];
    const agent = myAgent(c);
    if (agent && !(room.present || []).some((p) => p.actor === agent) && !d.affirm && !d.declined) return ["affirm"];
    return [];
  }

  function shapeKey(C) {
    const sh = C.room && C.room.shape;
    if (!sh) return "";
    const v = sh.vote || {}, p = sh.posture || {};
    return JSON.stringify([sh.part, sh.closed, (sh.proposals || []).length, v.cast, v.closed, sh.mine,
      (sh.writeups || []).map((w) => w.holder), (sh.reflections || []).length, (p.confirmed || []).length,
      (p.changes || []).length, mineLocal()]);
  }

  function postureWord(C, name) {
    return POSTURES.includes(name) ? C.t("room.shape.posture." + name.replace(/-/g, "_")) : String(name || "");
  }

  function postureExplain(C, name) {
    const t = C.t, word = postureWord(C, name);
    const key = POSTURES.includes(name) ? "room.shape.explain." + name.replace(/-/g, "_") : "room.shape.explain.other";
    C.openSheet({ title: word, body: h("p", null, t(key)) });
  }

  /** "the facilitator" · "you" · the role under the room's posture; never a name. */
  function shapeWho(C, actor) {
    const sh = C.room.shape;
    if (actor === C.state.actor) return C.t("app.you");
    if (actor && actor === sh.facilitator) return C.t("room.shape.facilitator");
    return whoAny(C, actor);
  }

  function partIndex(sh) {
    const i = (sh.parts || []).findIndex((p) => p.name === sh.part);
    return i < 0 ? null : i + 1;
  }

  function renderShape(C) {
    const t = C.t, f = C.fmt, sh = C.room.shape;
    const door = C.phase === "door";
    const does = sh.part_does || "gather";
    const wrap = h("div", { class: "room room--shape", dataset: { phase: door ? "door" : "shape", part: door ? "door" : does } });
    const word = postureWord(C, sh.posture && sh.posture.name);
    const head = h("header", { class: "shape-head" },
      h("p", { class: "shape-room-line" },
        h("span", { class: "caps room-name" }, C.room.name || C.read.holonName(C.state, rid)),
        h("button", { class: "link-btn shape-posture", onclick: () => postureExplain(C, sh.posture.name),
          "aria-label": t("room.shape.what", { posture: word }) }, word)));
    wrap.append(head);
    if (door) { wrap.append(renderShapeDoor(C)); return wrap; }

    const fac = sh.facilitator === C.state.actor;
    const rule = (sh.vote && sh.vote.rule) || { choose: 3, advance: 2 };
    const voiceKey = "room.shape.voice." + does + (fac && (does === "gather" || does === "propose") ? "_you" : "");
    const n = partIndex(sh);
    const step = [n ? t("room.part_of", { n: f.number(n, true), total: f.number((sh.parts || []).length, true) }) : null,
      sh.since && f.time(sh.since) ? t("room.shape.since", { time: f.time(sh.since) }) : null,
      countWords(C).replace(/\.$/, "")].filter(Boolean).join(" · ");
    head.append(
      h("h2", { class: "shape-part" }, t("room.shape.head." + does)),
      h("p", { class: "voice shape-voice" }, t(voiceKey, { choose: f.number(rule.choose, true), advance: f.number(rule.advance, true) })),
      h("p", { class: "dust shape-step" }, step));
    if (C.room.purpose && does === "gather") head.append(h("p", { class: "voice room-purpose" }, C.room.purpose));

    const body = h("section", { class: "shape-body", "aria-live": "polite" });
    ({ gather: shapeLobby, propose: shapeGreat, vote: shapeVote, write: shapeWriting, reflect: shapeReflect, close: shapeClose }[does] || shapeLobby)(C, body);
    wrap.append(body);
    if (fac && SWITCH_NEXT[does]) wrap.append(shapeSwitch(C, does));
    if (does === "write" || does === "reflect" || does === "close") wrap.append(shapePlayByPlay(C));
    return wrap;
  }

  function renderShapeDoor(C) {
    const t = C.t, sh = C.room.shape, needs = shapeDoor(C, C.room);
    const word = postureWord(C, sh.posture.name);
    const box = h("section", { class: "room-door shape-door", "aria-live": "polite" });
    if (needs[0] === "posture") {
      box.append(h("article", { class: "card door-card owed" },
        h("p", { class: "eyebrow" }, t("room.door_eyebrow")),
        h("h3", { class: "card-title" }, t("room.shape.door", { posture: word })),
        h("button", { class: "link-btn", onclick: () => postureExplain(C, sh.posture.name) }, t("room.shape.what", { posture: word })),
        h("div", { class: "card-options confirm" },
          h("button", { class: "pill primary", onclick: () => {
            C.act("posture", { posture: sh.posture.name, at: "open" }, {}, rid, { confirmed: true, label: t("room.shape.door_agreed", { posture: word }) });
            setLocal({ agreed: true }); build();
          } }, t("room.shape.door_act")))));
      box.append(h("p", { class: "dust door-foot" }, t("room.shape.door_foot")));
    } else if (needs[0] === "affirm") {
      box.append(h("article", { class: "card door-card" },
        h("p", { class: "eyebrow" }, t("room.door_eyebrow")),
        h("h3", { class: "card-title agent-text" }, t("room.door_affirm")),
        h("div", { class: "card-options confirm" },
          h("button", { class: "pill primary", onclick: () => {
            C.act("affirm", { agent: myAgent(C), room: rid }, {}, rid, { confirmed: true, label: t("room.door_affirmed") });
            const d = local.sget("door." + rid, {}); d.affirm = true; local.sset("door." + rid, d); build();
          } }, t("room.door_let_in")),
          h("button", { class: "pill quiet", onclick: () => {
            const d = local.sget("door." + rid, {}); d.declined = true; local.sset("door." + rid, d); build();
          } }, t("room.door_not_today")))));
      box.append(h("p", { class: "dust door-foot" }, t("room.door_foot")));
    }
    return box;
  }

  // the lobby: who is here, and how many have agreed to take part
  function shapeLobby(C, body) {
    const t = C.t, f = C.fmt, sh = C.room.shape, p = sh.posture || {};
    const people = (C.room.present || []).filter((x) => x.kind === "person");
    const agreed = new Set([...(p.agreed_open || []), ...(mineLocal().agreed ? [C.state.actor] : [])]);
    body.append(h("p", { class: "shape-line" }, t("room.shape.agreed_count", {
      n: f.number(people.filter((x) => agreed.has(x.actor)).length), total: f.number(people.length, true), posture: postureWord(C, p.name) })));
  }

  // the great room: the proposals as cards, and Propose for anyone present
  function shapeGreat(C, body) {
    const t = C.t, f = C.fmt, sh = C.room.shape;
    const props = [...(sh.proposals || []), ...(mineLocal().proposed || []).map((text, i) => ({ id: "local-" + i, text, by: C.state.actor, local: true }))];
    body.append(h("p", { class: "shape-line" }, props.length === 0 ? t("room.shape.proposals_none")
      : props.length === 1 ? t("room.shape.proposals_one") : t("room.shape.proposals_n", { n: f.number(props.length) })));
    body.append(h("ol", { class: "shape-proposals" }, props.map((p) => h("li", null,
      h("article", { class: "card shape-proposal" },
        h("h3", { class: "card-title" }, p.text),
        h("p", { class: "dust" }, t("room.shape.by", { who: shapeWho(C, p.by) })))))));
    const here = (C.room.present || []).some((x) => x.actor === C.state.actor) || (sh.mine && sh.mine.agreed);
    if (here) body.append(h("div", { class: "shape-acts" }, h("button", { class: "pill", onclick: () => openPropose(C) }, t("room.shape.propose"))));
  }

  function openPropose(C) {
    const t = C.t;
    const ta = h("textarea", { class: "shape-input", rows: "3", "aria-label": t("room.shape.propose_hint"), placeholder: t("room.shape.propose_hint"),
      oninput: (e) => { shapeDraft = e.target.value; } });
    ta.value = shapeDraft;
    let close = null;
    close = C.openSheet({ title: t("room.shape.propose_title"), body: h("div", { class: "shape-sheet" }, ta), actions: [
      h("button", { class: "pill primary", onclick: () => {
        const text = ta.value.trim();
        if (!text) { ta.focus(); return; }
        C.act("propose", { text }, {}, rid, { confirmed: true, label: t("room.shape.proposed") });
        setLocal({ proposed: [...(mineLocal().proposed || []), text] });
        shapeDraft = ""; if (close) close(); build();
      } }, t("room.shape.propose"))] });
  }

  function minutesWords(C, iso) {
    const t = C.t, m = minutesUntil(C, iso);
    if (m == null) return null;
    return m > 1 ? t("room.shape.vote_left", { n: C.fmt.number(m) }) : m === 1 ? t("room.shape.vote_left_one") : t("room.shape.vote_time_up");
  }

  // the vote: each proposal with a tick, "three of nine", the window's clock; the tally once closed
  function shapeVote(C, body) {
    const t = C.t, f = C.fmt, sh = C.room.shape, v = sh.vote || {}, rule = v.rule || { choose: 3, advance: 2 };
    if (v.closed) { shapeTally(C, body); return; }
    const props = sh.proposals || [];
    const loc = mineLocal();
    const cast = loc.voted || (sh.mine && sh.mine.vote) || null;
    const picks = new Set(loc.picks || cast || []);
    const changing = !!loc.changing;
    const owed = !cast || changing;
    const card = h("article", { class: `card shape-vote${owed ? " owed" : ""}` });
    card.append(
      h("h3", { class: "card-title" }, t("room.shape.vote_line", { choose: f.number(rule.choose, true), total: f.number(props.length, true) })),
      h("p", { class: "dust shape-clock" }, [v.closes ? minutesWords(C, v.closes) : null,
        t("room.shape.turnout", { n: f.number(v.cast || 0), total: f.number(v.of || 0, true) })].filter(Boolean).join(" · ")));
    const list = h("ul", { class: "shape-ticks" });
    props.forEach((p) => {
      const on = picks.has(p.id);
      list.append(h("li", null, h("button", { class: `shape-tick${on ? " is-on" : ""}`, "aria-pressed": String(on), disabled: !owed,
        onclick: () => {
          const next = new Set(mineLocal().picks || cast || []);     // read afresh: a tap never acts on a stale screen
          if (next.has(p.id)) next.delete(p.id); else if (next.size < rule.choose) next.add(p.id); else return;
          setLocal({ picks: [...next] }); build();
        } }, h("span", { class: "tick-mark", "aria-hidden": "true" }, on ? "✓" : ""), h("span", { class: "tick-text" }, p.text))));
    });
    card.append(list);
    if (owed) {
      card.append(h("p", { class: "dust" }, picks.size ? t("room.shape.chosen_count", { n: f.number(picks.size), choose: f.number(rule.choose, true) }) : t("room.shape.chosen_none", { choose: f.number(rule.choose, true) })),
        h("div", { class: "card-options confirm" }, h("button", { class: "pill primary", disabled: picks.size === 0, onclick: () => {
          C.act("vote", { choices: [...picks] }, {}, rid, { confirmed: true, label: t("room.shape.cast_label") });
          setLocal({ voted: [...picks], picks: null, changing: false }); build();
        } }, t("room.shape.cast"))));
    } else {
      card.append(h("p", { class: "shape-line" }, t("room.shape.cast_done")),
        h("button", { class: "link-btn", onclick: () => { setLocal({ changing: true, picks: [...picks] }); build(); } }, t("room.shape.change_vote")));
    }
    body.append(card);
  }

  function votesWord(C, n) {
    return n === 0 ? C.t("room.shape.votes_none") : n === 1 ? C.t("room.shape.votes_one") : C.t("room.shape.votes_n", { n: C.fmt.number(n, true) });
  }

  // the count, as the engine tallied it; a tie said plainly, never broken
  function shapeTally(C, body, withCards) {
    const t = C.t, f = C.fmt, sh = C.room.shape, v = sh.vote || {};
    const chosen = v.chosen || [];
    const byId = Object.fromEntries((sh.proposals || []).map((p) => [p.id, p]));
    body.append(h("p", { class: "shape-line" }, chosen.length === 1 ? t("room.shape.closed_one") : t("room.shape.closed_line", { n: f.number(chosen.length) })));
    if (v.tie) body.append(h("p", { class: "shape-line shape-tie" }, t("room.shape.tie", { n: f.number(v.tie.proposals.length), votes: f.number(v.tie.votes, true) })));
    if (withCards) return chosen.map((id) => byId[id]).filter(Boolean);
    body.append(h("ol", { class: "shape-chosen" }, chosen.map((id) => byId[id]).filter(Boolean).map((p) => h("li", null,
      h("article", { class: "card shape-proposal" }, h("h3", { class: "card-title" }, p.text), h("p", { class: "dust" }, votesWord(C, p.votes)))))));
    shapeOthers(C, body, chosen);
    return null;
  }

  function shapeOthers(C, body, chosen) {
    const t = C.t, sh = C.room.shape;
    const rest = (sh.proposals || []).filter((p) => !chosen.includes(p.id) && !((sh.vote.tie || {}).proposals || []).includes(p.id))
      .sort((a, b) => (b.votes || 0) - (a.votes || 0));
    if (!rest.length) return;
    body.append(h("details", { class: "shape-others" }, h("summary", { class: "dust" }, t("room.shape.others")),
      h("ul", null, rest.map((p) => h("li", { class: "dust" }, p.text + " · " + votesWord(C, p.votes || 0))))));
  }

  // the writing: the chosen as cards with holders and by-whens (the Table's face)
  function shapeWriting(C, body) {
    const t = C.t, f = C.fmt, sh = C.room.shape;
    const chosen = shapeTally(C, body, true) || [];
    const loc = mineLocal();
    const list = h("ol", { class: "shape-chosen" });
    chosen.forEach((p) => {
      const w = (sh.writeups || []).find((x) => x.proposal === p.id);
      const holder = w && (w.holder || (loc.held || []).includes(w.card) && C.state.actor);
      list.append(h("li", null, h("article", { class: "card shape-writeup" },
        h("p", { class: "eyebrow" }, votesWord(C, p.votes)),
        h("h3", { class: "card-title" }, (w && w.title) || p.text),
        w && w.title ? h("p", { class: "dust" }, p.text) : null,
        h("p", { class: "card-foot" },
          holder ? h("span", { class: "chip holder-chip" }, t("room.shape.held_by", { who: shapeWho(C, holder) })) : h("span", { class: "dust" }, t("room.shape.unheld")),
          w && w.by ? h("span", { class: "dust" }, " · " + f.by(w.by)) : null),
        w && !holder ? h("div", { class: "card-options" }, h("button", { class: "pill", onclick: () => {
          C.act("claim", { card: w.card }, {}, rid, { confirmed: true, label: t("room.shape.held_label") });
          setLocal({ held: [...(loc.held || []), w.card] }); build();
        } }, t("room.shape.hold_it"))) : null)));
    });
    body.append(list);
    shapeOthers(C, body, chosen.map((p) => p.id));
  }

  // reflection: one line each, the wearer's own to say
  function shapeReflect(C, body) {
    const t = C.t, sh = C.room.shape, loc = mineLocal();
    const lines = [...(sh.reflections || [])];
    if (loc.said && !lines.some((r) => r.by === C.state.actor)) lines.push({ by: C.state.actor, text: loc.said });
    body.append(lines.length ? h("ul", { class: "shape-reflections" }, lines.map((r) => h("li", null,
      h("p", { class: "shape-reflection" }, r.text), h("p", { class: "dust" }, shapeWho(C, r.by)))))
      : h("p", { class: "dust" }, t("room.shape.reflections_none")));
    if (lines.some((r) => r.by === C.state.actor)) return;
    const ta = h("textarea", { class: "shape-input", rows: "2", "aria-label": t("room.shape.your_line"), placeholder: t("room.shape.reflect_hint"),
      oninput: (e) => { shapeDraft = e.target.value; } });
    ta.value = shapeDraft;
    body.append(h("div", { class: "shape-say" }, ta, h("button", { class: "pill", onclick: () => {
      const text = ta.value.trim();
      if (!text) { ta.focus(); return; }
      C.act("say", { text }, {}, rid, { confirmed: true, label: t("room.shape.said_label") });
      setLocal({ said: text }); shapeDraft = ""; build();
    } }, t("room.shape.say"))));
  }

  // the close: confirm the posture you agreed to, then the curing window in dust
  function shapeClose(C, body) {
    const t = C.t, f = C.fmt, sh = C.room.shape, p = sh.posture || {}, loc = mineLocal();
    const word = postureWord(C, p.name);
    const until = f.date(p.cure_until);
    const day = until ? (f.daysBetween(f.now(), until) < 7 ? f.dayName(until) : until.toLocaleDateString(undefined, { day: "numeric", month: "long" })) : null;
    const mine = sh.mine || {};
    const agreed = mine.agreed || loc.agreed;
    const confirmed = mine.confirmed || loc.confirmed;
    const changed = mine.withdrawn || loc.changed;
    if (agreed && !confirmed && !changed && p.curing) {
      body.append(h("article", { class: "card shape-confirm owed" },
        h("h3", { class: "card-title" }, t("room.shape.confirm_title", { posture: word })),
        h("div", { class: "card-options confirm" }, h("button", { class: "pill primary", onclick: () => {
          C.act("posture", { posture: p.name, at: "close", cure_until: p.cure_until }, {}, rid, { confirmed: true, label: t("room.shape.confirm_label") });
          setLocal({ confirmed: true }); build();
        } }, t("room.shape.confirm"))),
        day ? h("p", { class: "dust" }, t("room.shape.cure", { day })) : null));
    } else if (agreed) {
      body.append(h("p", { class: "shape-line" }, changed ? t("room.shape.changed_label") : t("room.shape.confirmed", { posture: word })));
      if (day) body.append(h("p", { class: "dust" }, p.curing ? t("room.shape.cure", { day }) : t("room.shape.cure_over", { day })));
      if (p.curing && !changed) body.append(h("button", { class: "link-btn", onclick: () => openChange(C, day) }, t("room.shape.change")));
    }
    const people = (p.agreed_open || []).length;
    const still = (p.confirmed || []).filter((x) => !(p.withdrawn || []).includes(x)).length + (loc.confirmed && !mine.confirmed ? 1 : 0);
    body.append(h("p", { class: "dust" }, t("room.shape.confirmed_count", { n: f.number(still), total: f.number(people, true) })));
    const ch = (p.changes || []).length;
    if (ch) body.append(h("p", { class: "dust" }, ch === 1 ? t("room.shape.changes_one") : t("room.shape.changes_n", { n: f.number(ch) })));
  }

  function openChange(C, day) {
    const t = C.t, sh = C.room.shape;
    let close = null;
    const go = (body) => () => {
      C.act("posture", { withdraw: true, ...body }, {}, rid, { confirmed: true, label: t("room.shape.changed_label") });
      setLocal({ changed: true }); if (close) close(); build();
    };
    const acts = [];
    if (sh.posture.name !== "off-the-record") acts.push(h("button", { class: "pill", onclick: go({ posture: "off-the-record" }) }, t("room.shape.narrow")));
    acts.push(h("button", { class: "pill quiet", onclick: go({}) }, t("room.shape.withdraw")));
    close = C.openSheet({ title: t("room.shape.change"), body: h("p", null, t("room.shape.change_line", { day: day || "" })), actions: acts });
  }

  // the facilitator's switch: one pill only the facilitator sees; the only act that moves the room
  function shapeSwitch(C, does) {
    const t = C.t, sh = C.room.shape, next = SWITCH_NEXT[does];
    const part = next === "close" ? "close" : ((sh.parts || []).find((p) => p.does === next) || {}).name;
    const rule = (sh.vote && sh.vote.rule) || { choose: 3, advance: 2, minutes: 20 };
    return h("section", { class: "shape-switch-wrap" },
      h("button", { class: "pill shape-switch", onclick: () => {
        const now = C.fmt.now(), body = { part };
        if (next === "vote") Object.assign(body, { opens: now.toISOString(), closes: new Date(now.getTime() + (rule.minutes || 20) * 60000).toISOString(),
          rule: { choose: rule.choose, advance: rule.advance } });
        if (next === "close") body.cure_until = new Date(now.getTime() + ((sh.posture && sh.posture.cure_days) || 3) * 86400000).toISOString();
        C.act("part", body, {}, rid, { confirmed: true, label: t("room.shape.moved") });
      } }, t("room.shape.switch." + does)),
      h("p", { class: "dust" }, t("room.shape.switch_line")));
  }

  // the play by play: each move of the room, newest first, in her words
  function shapePlayByPlay(C) {
    const t = C.t, f = C.fmt, sh = C.room.shape;
    const does = Object.fromEntries((sh.parts || []).map((p) => [p.name, p.does]));
    const rule = (sh.vote && sh.vote.rule) || { choose: 3, advance: 2 };
    const rows = (sh.moves || []).map((m) => ({ at: m.at, text: t("room.shape.move." + (m.part === "close" ? "close" : does[m.part] || "gather"),
      { choose: f.number(rule.choose, true), advance: f.number(rule.advance, true) }) }));
    if (sh.vote && sh.vote.closed && sh.vote.closed_at) rows.push({ at: sh.vote.closed_at, text: (sh.vote.chosen || []).length === 1 ? t("room.shape.closed_one") : t("room.shape.closed_line", { n: f.number((sh.vote.chosen || []).length) }) });
    rows.sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
    return h("section", { class: "shape-pbp" }, h("h3", { class: "eyebrow" }, t("room.shape.pbp")),
      h("ol", null, rows.map((r) => h("li", null, h("span", { class: "dust" }, (f.time(r.at) || "") + " · "), r.text))));
  }

  // ------------------------------------------------------------------ phone tabs: Page · Table

  function renderTabs(C) {
    if (!$tabs) return;
    const t = C.t;
    const n = yourMove(C, rid).length;
    $tabs.textContent = "";
    $tabs.append(
      h("button", { class: "chip", onclick: () => openPanel(C, "page") }, t("room.page")),
      h("button", { class: "chip", onclick: () => openPanel(C, "table") }, n ? t("room.table_count", { n: String(n) }) : t("room.table")));
  }

  function openPanel(C, which) {
    const host = h("div", { class: `room-sheet room-sheet--${which}` });
    const c = cx(ctx);
    if (which === "table") host.append(presenceBody(c));
    const close = C.openSheet({ title: C.t("room." + which), body: host });
    if (typeof close === "function") closers.push(close);
    const parts = which === "page" ? [createPage()]
      : c.phone ? [createPage({ rest: false }), createTable(), createPage({ sitting: false })] : [createTable()];
    for (const inst of parts) {
      const slot = h("div", { class: "room-sheet-part" });
      host.append(slot);
      inst.mount(slot, c);
      sheetSubs.push({ el: slot, inst });
    }
  }

  return { mount, update, unmount };
}

/** The bus between the Talk and the Table: a card born from a line (§2.3). */
function makeShared() {
  const listeners = new Set();
  const s = {
    drafts: [],
    agreeing: new Set(),      // line ids whose ink is drying on this screen
    on(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    emit() { for (const fn of listeners) { try { fn(); } catch (e) { console.error(e); } } },
    addDraft(d) { s.drafts.unshift(d); s.emit(); },
    dropDraft(id) { s.drafts = s.drafts.filter((d) => d.id !== id); s.emit(); },
  };
  return s;
}
