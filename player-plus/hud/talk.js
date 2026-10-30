// talk.js: the Talk (DESIGN-ROOM §2.3, §3, §6.4). The current part's lines in three inks:
// said (dust; passes when the rolling window ends), kept (paper with an open star; on this
// device only, never written), agreed (full ink, its eyebrow and ✓; in the room's record,
// signed by the person who agreed it). Newest at the foot. Threads open under the line they
// belong to. The offered tray holds at most three lines. The line to offer, typed or spoken
// (dictation only where the device keeps it on the device). Five seconds of Undo come with
// every act (ctx.act). The offline queue marks each line "waiting to send".
//
// Said lines and whispers belong to the live store of DESIGN-ROOM §8.2 (outside git and
// outside the record). Until the server carries it, the Talk reads what the state's
// `hud.talk[room]` holds and keeps this wearer's own offered lines on this device, marked
// waiting to send. Nothing said is ever written to the record by the Talk; only a person's
// Agree writes, as a `settle`.

import { h } from "./card.js";
import { local, lineById, lineWho, isAgentLine, eyebrow, verifiedMark, agentOf, whoOf, cssMs, cssVar, isElided } from "./inks.js";
import { yourMove } from "./table.js";

const AGREED_TYPES = new Set(["settle", "decide", "card", "commit", "request", "offer", "ratify", "answer", "hand", "claim", "done"]);

const KEPT = {};   // per room: the answered card and the asks confirmed on this screen

export default function createTalk() {
  let el = null, C = null, rid = null;
  let $list = null, $tray = null, $form = null, $newPill = null, $live = null, $away = null;
  let seenIds = new Set(), firstRender = true, offset = 0, selfAdded = false;
  const open = new Set();          // rows whose actions are open
  const threadsOpen = new Set();
  const replying = new Set();
  const agreeing = new Map();      // id -> {text, type, at, fresh, pending}: drying in the flow, with its Undo
  // the one card, answered: it stays in place, its ink deepening, "Yes · Undo", until the stream
  // confirms. Held per room outside this instance, so a remount of the view (the shell remounts on
  // some acts) redraws the answered card instead of asking again.
  const K = () => KEPT[rid] || (KEPT[rid] = { answered: null, done: new Set() });
  let showAll = false;             // the whole talk of this part, or only its last lines (the ground)
  let unsubscribe = null;

  function mount(host, ctx) {
    el = host; C = ctx; rid = ctx.roomId;
    el.classList.add("talk");
    const t = C.t;
    $away = h("p", { class: "talk-away", role: "status", hidden: true });
    $list = h("ol", { class: "talk-list", "aria-label": t("room.talk") });
    $newPill = h("button", { class: "pill quiet talk-new", hidden: true, onclick: () => { scrollToFoot(); $newPill.hidden = true; } });
    $tray = h("section", { class: "tray", "aria-label": t("talk.tray_label") });
    $form = renderForm();
    $live = h("div", { class: "sr-only", "aria-live": "polite" });
    // on the phone (DESIGN-ROOM, "The Room on the phone"): no head (the top edge says the part),
    // and the foot holds the one card and the line to offer, in fixed places
    if (C.phone) {
      el.classList.add("talk--phone");
      el.append($away, $tray, $list, $newPill, h("div", { class: "talk-foot" }, $form), $live);
    } else el.append(h("div", { class: "talk-head" }, h("h3", { class: "caps" }, partTitle())), $away, $list, $newPill, $tray, $form, $live);
    $list.addEventListener("scroll", () => { if (atFoot()) $newPill.hidden = true; });
    unsubscribe = C.shared.on(() => render());
    showAway();
    render();
  }
  function update(ctx) { C = ctx; rid = ctx.roomId; render(); }
  function unmount() {
    if (unsubscribe) unsubscribe();
    remember();
    el = null;
  }

  // ------------------------------------------------------------------ what lies on the table

  function room() { return C.room || {}; }
  function parts() { return Array.isArray(room().parts) ? room().parts : []; }
  function current() { return parts().find((p) => p.n === room().current_part) || null; }
  function partTitle() {
    const p = current();
    return p ? C.t("talk.head", { title: p.title }) : C.t("room.talk");
  }
  function partOf(id) { const m = room().line_meta && room().line_meta[id]; return m ? m.part : null; }

  /** The rolling window for said lines: the room's length plus a day (proposal, §8.2). */
  function windowStart() {
    const mins = parts().reduce((a, p) => a + (p.minutes || 0), 0);
    return new Date(C.fmt.now().getTime() - (mins + 24 * 60) * 60000);
  }

  function queue() {
    const q = local.get("queue." + rid, []);
    const from = windowStart();
    const kept = q.filter((x) => new Date(x.ts) >= from);
    if (kept.length !== q.length) local.set("queue." + rid, kept);
    return kept;
  }
  function keptSet() { return new Set(local.get("kept." + rid, [])); }
  function setAside() { return new Set(local.sget("aside." + rid, [])); }

  /** Every line of the current part, oldest first (a conversation reads downward). */
  function items() {
    const st = C.state, cur = current(), r = room();
    const out = [];
    const from = windowStart();
    const talk = foldRepeats((st.hud && st.hud.talk && st.hud.talk[rid]) || []);
    for (const s of talk) {
      if (s.whisper) continue;                           // whispers live in each agent's account (§4.3)
      if (cur && s.part != null && String(s.part) !== String(cur.n)) continue;
      if (s.parent) continue;                            // replies show under their line's thread
      if (new Date(s.ts) < from) continue;
      // a said line the keeper kept (serve.py's /keep) is in the record now: full ink
      if (s.kept && s.kept.line) {
        if ((r.lines || []).includes(s.kept.line)) continue;   // the agreed line itself stands for it, once
        out.push({ kind: "agreeing", id: "kept-" + s.id, ts: s.ts, by: s.kept.by, text: s.text, type: "settle" }); continue;
      }
      out.push({ kind: "said", id: s.id, ts: s.ts, by: s.by, text: s.text, mine: s.by === st.actor });
    }
    const agreedIds = Array.isArray(r.lines) ? r.lines : [];
    for (const id of agreedIds) {
      const ln = lineById(st, id);
      if (!ln || !AGREED_TYPES.has(ln.type)) continue;
      const p = partOf(id);
      if (cur && p != null && p !== cur.n) continue;
      if (cur && p == null && cur.started && ln.ts < cur.started) continue;
      out.push({ kind: "agreed", id, ts: ln.ts, by: ln.actor, line: ln, text: textOf(ln) });
    }
    // a question with a by-when climbed to (or from) this room shows as a question (STATE `questions`)
    for (const q of st.questions || []) {
      if (q.to !== rid && q.from_holon !== rid) continue;
      if (q.state !== "open" && q.state !== "climbed") continue;
      // never a time later than now: a stamp from the future reads as now, and shows no time
      const future = C.fmt.date(q.ts) && C.fmt.date(q.ts) > C.fmt.now();
      out.push({ kind: "question", id: "q-" + q.id, ts: future ? C.fmt.now().toISOString() : q.ts, noTime: future, by: q.asker, text: isElided(q.question) ? C.t("record.hidden") : q.question,
        qtype: q.type, due: q.by, line: lineById(st, q.id) });
    }
    for (const q of queue()) out.push({ kind: "queued", id: q.id, ts: q.ts, by: st.actor, text: q.text, mine: true, now: q.now, parent: q.parent });
    for (const [id, a] of agreeing) {
      if (out.some((x) => x.kind === "agreed" && x.text === a.text)) { agreeing.delete(id); continue; }
      out.push({ kind: "agreeing", id: "agreeing-" + id, key: id, ts: a.at, by: a.by, text: a.text, type: a.type || "settle", fresh: a.fresh, pending: a.pending });
      a.fresh = false;
    }
    // a line agreed while it was said shows once: the agreed line stands for the said one
    const agreedText = new Set(out.filter((x) => x.kind === "agreed" || x.kind === "agreeing").map((x) => x.text));
    const kept = out.filter((x) => !(x.kind === "said" && agreedText.has(x.text)));
    // by the moment each was said (stamps in different zones sort wrongly as text)
    const at = (x) => { const d = new Date(x.ts); return isNaN(d) ? 0 : d.getTime(); };
    return kept.filter((x) => !x.parent).sort((a, b) => at(a) - at(b));
  }

  /** The same line twice within thirty seconds is one line (§4.4), however it arrived: a
      double tap, a retry after a slow answer, or two servers of one room. The fold that once
      held only for the device's own queue now holds for said lines too. */
  function foldRepeats(rows) {
    const out = [];
    for (const r of rows) {
      const twin = out.find((x) => x.by === r.by && x.text === r.text && (x.parent || null) === (r.parent || null)
        && Math.abs(new Date(x.ts) - new Date(r.ts)) < 30000);
      if (twin) { if (r.kept && !twin.kept) twin.kept = r.kept; continue; }
      out.push({ ...r });
    }
    return out;
  }

  function textOf(ln) {
    const b = ln.body || {};
    if (isElided(b.text) || isElided(b.title)) return C.t("record.hidden");
    if (b.text) return b.text;
    if (b.title) return b.title;
    if (ln.type === "commit") {
      const c = C.read.card(C.state, b.card);
      return C.t("talk.commit_line", { title: c ? c.title : C.t("card.not_yet_arrived"), by: C.fmt.by(b.by) || C.t("table.slot_unset") });
    }
    return C.t("record.what.other");
  }

  // ------------------------------------------------------------------ render

  function render() {
    if (!el) return;
    const t = C.t, st = C.state;
    const wasAtFoot = atFoot();
    const list = items();
    const kept = keptSet();
    $list.textContent = "";

    // the ground: in the one-column sitting the Talk shows its last lines; the whole is one tap away
    const GROUND = 3;
    const hidden = C.phone && !showAll ? Math.max(0, list.length - GROUND) : 0;
    if (hidden) $list.append(h("li", { class: "talk-earlier" }, h("button", { class: "link-btn dust", onclick: () => { showAll = true; render(); } },
      hidden === 1 ? t("talk.earlier_one") : t("talk.earlier_n", { n: C.fmt.number(hidden, true) }))));
    // earlier parts, folded to one line each
    const cur = current();
    for (const p of parts().filter((p) => cur && p.n < cur.n && (!C.phone || showAll))) {
      const agreed = (room().lines || []).filter((id) => partOf(id) === p.n);
      const li = h("li", { class: "talk-part" });
      const btn = h("button", { class: "talk-part-btn dust", "aria-expanded": String(threadsOpen.has("part" + p.n)),
        onclick: () => { toggle(threadsOpen, "part" + p.n); render(); } },
        t("talk.part_folded", { n: C.fmt.number(p.n, true), title: p.title, count: agreedCount(agreed.length) }));
      li.append(btn);
      if (threadsOpen.has("part" + p.n)) {
        li.append(h("ul", { class: "talk-part-lines" }, agreed.map((id) => {
          const ln = lineById(st, id);
          return ln ? h("li", { class: "ink-agreed", title: verifiedMark(C, ln).word }, h("span", { class: "eyebrow" }, eyebrow(C, ln.type)), " ", textOf(ln), srWord(ln)) : null;
        })));
      }
      $list.append(li);
    }
    if (C.phase === "close") $list.append(h("li", { class: "talk-room-line voice" }, t("room.close_line")));

    if (!list.length) $list.append(h("li", { class: "talk-empty dust" }, t("talk.empty")));
    const fresh = [];
    // lit when normal: the newest said line, and nothing else in the Talk
    const newest = C.phone ? list[list.length - 1] : [...list].reverse().find((x) => x.kind === "said" || x.kind === "queued");
    for (const it of list.slice(hidden)) {
      const li = row(it, kept);
      if (newest && it.id === newest.id) li.classList.add("is-newest");
      $list.append(li);
      if (!seenIds.has(it.id) && !firstRender) fresh.push(it);
    }
    // announce agreed lines politely; said lines are not announced unless asked (§6.4)
    const agreedFresh = fresh.filter((x) => x.kind === "agreed" || x.kind === "agreeing");
    if (agreedFresh.length) $live.textContent = agreedFresh.map((x) => t("talk.announce", { text: x.text })).join(" ");
    if (fresh.length && !firstRender) {
      if (wasAtFoot || selfAdded) scrollToFoot();
      else {
        $newPill.hidden = false;
        $newPill.textContent = (fresh.length === 1 ? t("talk.new_one") : t("talk.new_many", { n: C.fmt.number(fresh.length) })) + " ↓";
      }
    }
    if (firstRender) { requestAnimationFrame(scrollToFoot); setTimeout(scrollToFoot, 400); }   // again once room.css has laid the list out
    seenIds = new Set(list.map((x) => x.id));
    firstRender = false;
    selfAdded = false;
    if (C.phone) renderOne(); else renderTray();
    remember();
  }

  /** The verification word, for a screen reader and on hover; the ink carries it for the eye. */
  function srWord(ln) { return h("span", { class: "sr-only" }, ", " + verifiedMark(C, ln).word); }

  function agreedCount(n) { return n === 0 ? C.t("talk.agreed_none") : n === 1 ? C.t("talk.agreed_one") : C.t("talk.agreed_n", { n: C.fmt.number(n, true) }); }

  function row(it, kept) {
    const t = C.t, st = C.state;
    const isKept = it.kind === "said" && kept.has(it.id) && !C.shown;
    const agreed = it.kind === "agreed" || it.kind === "agreeing";
    const ink = agreed ? "ink-agreed" : isKept ? "ink-kept" : "ink-said";
    const agentLine = it.line ? isAgentLine(C, it.line) : (typeof it.by === "string" && C.read.actorKind(st, it.by) === "agent");
    const who = it.line ? lineWho(C, it.line, rid)
      : it.by === st.actor ? t("app.you") : agentLine ? agentOf(C, it.by, rid) : C.read.who(st, it.by, rid);
    const li = h("li", { class: `tline ${ink}${agentLine ? " is-agent" : ""}${open.has(it.id) ? " is-open" : ""}`, dataset: { id: it.id } });
    const meta = h("div", { class: "tline-meta" },
      agentLine ? h("span", { class: "ring-mark", "aria-hidden": "true" }) : null,
      isKept ? h("span", { class: "star", title: t("talk.kept"), "aria-label": t("talk.kept") }, "☆") : null,
      h("span", { class: "tline-who" }, who),
      agreed ? h("span", { class: C.phone ? "sr-only" : "eyebrow tline-eyebrow" }, eyebrow(C, it.line ? it.line.type : it.type)) : null,
      it.kind === "question" ? h("span", { class: C.phone ? "sr-only" : "eyebrow tline-eyebrow tline-question" }, eyebrow(C, it.qtype || "rfg")) : null,
      (it.kind === "question" && it.due) || (it.line && it.line.type === "request" && it.line.body && typeof it.line.body.by === "string")
        ? h("span", { class: "tline-due" }, C.t("talk.question_by", { by: C.fmt.by(it.due || it.line.body.by) || "" })) : null,
      h("span", { class: "tline-time figures dust" }, it.noTime ? "" : C.fmt.time(it.ts) || ""),
      it.kind === "queued" ? h("span", { class: "tline-wait dust" }, it.now ? t("talk.waiting_now") : t("talk.waiting")) : null);
    const body = h("button", { class: "tline-body", "aria-expanded": String(open.has(it.id)),
      onclick: () => { toggle(open, it.id); render(); } }, it.text);
    // no tick: the ink is the verification (DESIGN-THE-BAR: nothing lit but the owed thing)
    const undo = it.kind === "agreeing" && it.pending && it.pending.status === "holding"
      ? h("button", { class: "link-btn tline-undo", onclick: (e) => { e.stopPropagation(); it.pending.undo(); } }, t("talk.undo")) : null;
    li.append(meta, h("div", { class: "tline-main" }, body, it.line ? srWord(it.line) : null, undo));
    if (it.line) li.title = verifiedMark(C, it.line).word;
    if (it.line && it.line.reason === "untrusted") li.append(h("p", { class: "dust untrusted" }, "◇ " + t("talk.untrusted")));
    if (it.kind === "agreeing" && it.fresh) dry(li);

    // actions: Keep · Agree · Reply · Make it a card (· Delete for the sayer's own unsent line)
    const acts = h("div", { class: "tline-acts" });
    if (it.kind === "said" && !C.shown) acts.append(h("button", { class: "link-btn", "aria-pressed": String(isKept),
      onclick: () => { const k = keptSet(); k.has(it.id) ? k.delete(it.id) : k.add(it.id); local.set("kept." + rid, [...k]); render(); } },
      isKept ? t("talk.unkeep") : t("talk.keep")));
    if (it.kind === "said" && !it.mine && !agentLine) acts.append(h("button", { class: "link-btn", onclick: () => agree(it.id, it.text, null, it.by) }, t("talk.agree")));
    if (it.kind === "said" && it.mine) acts.append(h("span", { class: "dust" }, t("talk.others_agree")));
    acts.append(h("button", { class: "link-btn", onclick: () => { toggle(replying, it.id); open.add(it.id); render(); } }, t("talk.reply")));
    acts.append(h("button", { class: "link-btn", onclick: () => makeCard(it) }, t("talk.make_card")));
    if (!C.phone && (it.kind === "said" || it.kind === "queued")) acts.append(h("button", { class: "link-btn", onclick: () => makeCard(it, "sight") }, t("talk.make_sight")));
    if (it.kind === "queued") acts.append(h("button", { class: "link-btn", onclick: () => { local.set("queue." + rid, queue().filter((x) => x.id !== it.id)); render(); } }, t("talk.delete")));
    li.append(acts);

    // threads under the line they belong to
    const th = threadsFor(it);
    const live = ((C.state.hud && C.state.hud.talk && C.state.hud.talk[rid]) || []).filter((x) => x.parent === it.id && !x.whisper);
    const replies = [...live, ...queue().filter((q) => q.parent === it.id)];
    if (th || replies.length) li.append(threadBlock(it, th, replies));
    if (replying.has(it.id)) li.append(replyForm(it));
    return li;
  }

  /** The ink drying: dust to full ink over 480 ms; nothing glows. */
  function dry(li) {
    requestAnimationFrame(() => {
      C.animate(li.querySelector(".tline-body"), [{ color: cssVar("--ink-said") }, { color: cssVar("--ink-kept"), offset: .5 }, { color: cssVar("--ink-agreed") }],
        { duration: cssMs("--d-card"), easing: cssVar("--e-settle") });
    });
  }

  function threadsFor(it) {
    const st = C.state;
    const anchors = new Set([it.id]);
    if (it.line && it.line.body && typeof it.line.body.card === "string") anchors.add(it.line.body.card);
    return (st.threads || []).find((x) => anchors.has(x.anchored_to)) || null;
  }

  function threadBlock(it, th, replies) {
    const t = C.t, st = C.state;
    const key = "t:" + it.id;
    const tlines = th ? (st.lines || []).filter((l) => l.links && Array.isArray(l.links.anchored_to) && l.links.anchored_to.includes(th.id))
      .sort((a, b) => String(a.ts).localeCompare(String(b.ts))) : [];
    const n = (th ? tlines.length || th.lines || 0 : 0) + replies.length;
    const lastAgreed = [...tlines].reverse().find((l) => l.type === "settle");
    const box = h("div", { class: "thread" });
    box.append(h("button", { class: "link-btn thread-count", "aria-expanded": String(threadsOpen.has(key)),
      onclick: () => { toggle(threadsOpen, key); render(); } },
      [n === 1 ? t("talk.reply_one") : t("talk.replies", { n: C.fmt.number(n, true) }),
        lastAgreed ? t("talk.thread_agreed", { text: textOf(lastAgreed) }) : null].filter(Boolean).join(" · ")));
    if (threadsOpen.has(key)) {
      const ul = h("ul", { class: "thread-lines" });
      for (const l of tlines) {
        const agreed = l.type === "settle";
        ul.append(h("li", { class: agreed ? "ink-agreed" : "ink-said" },
          h("span", { class: "tline-who" }, lineWho(C, l, rid)), " ",
          agreed ? h("span", { class: "eyebrow" }, eyebrow(C, "settle")) : null, " ", textOf(l), srWord(l)));
      }
      for (const q of replies) ul.append(h("li", { class: "ink-said" }, h("span", { class: "tline-who" }, q.by && q.by !== st.actor ? C.read.who(st, q.by, rid) : t("app.you")), " ", q.text,
        q.by ? null : h("span", { class: "dust" }, " " + t("talk.waiting"))));
      if (!tlines.length && !replies.length) ul.append(h("li", { class: "dust" }, t("talk.thread_not_held")));
      box.append(ul);
    }
    return box;
  }

  function replyForm(it) {
    const t = C.t;
    const ta = h("textarea", { rows: "2", class: "offer-input", "aria-label": t("talk.reply_label"), placeholder: t("talk.reply_placeholder") });
    const f = h("form", { class: "reply-form", onsubmit: (e) => {
      e.preventDefault();
      const text = ta.value.trim(); if (!text) return;
      send(text, { parent: it.id }); selfAdded = true;
      replying.delete(it.id); threadsOpen.add("t:" + it.id); render();
    } }, ta, h("button", { class: "pill", type: "submit" }, t("talk.offer")));
    requestAnimationFrame(() => ta.focus());
    return f;
  }

  // ------------------------------------------------------------------ the offered tray (§2.3, §3)

  function offeredNow() {
    const st = C.state, r = room();
    const aside = setAside();
    const settledAnchors = new Set();
    for (const l of st.lines || []) if (l.type === "settle" && l.links && Array.isArray(l.links.anchored_to)) l.links.anchored_to.forEach((x) => settledAnchors.add(x));
    return (r.offered || []).filter((o) => !aside.has(o.line) && !agreeing.has(o.line) && !settledAnchors.has(o.line)
      && !(r.lines || []).includes(o.line));
  }

  function renderTray() {
    const t = C.t, st = C.state;
    $tray.textContent = "";
    const all = offeredNow();
    if (!all.length) { $tray.hidden = true; return; }
    $tray.hidden = false;
    if (offset >= all.length) offset = 0;
    const shown = all.slice(offset, offset + 3);
    const more = all.length - shown.length;
    $tray.append(h("p", { class: "eyebrow" }, t("talk.tray_title")));
    const ul = h("ul", { class: "tray-list" });
    for (const o of shown) {
      const ln = lineById(st, o.line);
      if (!ln) { ul.append(h("li", { class: "dust" }, t("card.not_yet_arrived"))); continue; }
      const agentL = isAgentLine(C, ln);
      const by = isElided(ln.actor) ? t("record.hidden") : agentL ? agentOf(C, ln.actor, rid) : C.read.who(st, ln.actor, rid);
      const mineAgent = o.for === st.actor;
      const isSight = ln.type === "sight";
      const li = h("li", { class: `tray-item${agentL ? " is-agent" : ""}` },
        isSight ? h("p", { class: "eyebrow" }, eyebrow(C, "sight") + (ln.body && typeof ln.body.kind === "string" ? " · " + t("sight.kind." + ln.body.kind) : "")) : null,
        h("p", { class: `tray-text${agentL ? " agent-text" : ""}` }, agentL ? h("span", { class: "ring-mark", "aria-hidden": "true" }) : null, textOf(ln)),
        h("p", { class: "dust" }, t(isSight ? "talk.sighted_by" : "talk.offered_by", { who: by })),
        o.reason === "untrusted" ? h("p", { class: "dust untrusted" }, "◇ " + t("talk.untrusted")) : null,
        h("div", { class: "tray-acts" },
          mineAgent ? h("span", { class: "dust" }, t("talk.others_agree"))
            : h("button", { class: "pill", onclick: () => agree(o.line, textOf(ln), o.line, ln.actor) }, t("talk.agree")),
          isSight ? h("button", { class: "pill", onclick: () => makeCard({ text: textOf(ln), line: ln, kind: "agreed", id: ln.id }, "sight") }, t("talk.make_sight")) : null,
          h("button", { class: "pill quiet", onclick: () => { const a = setAside(); a.add(o.line); local.sset("aside." + rid, [...a]); render(); } }, t("talk.not_this"))));
      ul.append(li);
    }
    $tray.append(ul);
    if (more > 0) $tray.append(h("button", { class: "link-btn tray-more", onclick: () => { offset += 3; renderTray(); } },
      more === 1 ? t("talk.more_one") : t("talk.more_n", { n: C.fmt.number(more, true) })));
    $tray.append(h("p", { class: "dust tray-law" }, t("talk.tray_law")));
  }

  // ------------------------------------------------------------------ the one card (the phone)

  /** What is asked of this person, in order: a commitment asked of her; a yes only she can
      give; a question she holds; else the first line offered by another for anyone to agree.
      Each with what it is, what to do, and the act the biggest thing on the screen. */
  function asks() {
    const st = C.state, me = st.actor, r = room();
    const later = new Set([...local.sget("later." + rid, []), ...K().done]);
    const out = [];
    const mine = yourMove(C, rid);
    for (const x of mine) if (x.kind === "asked" && !later.has(x.e.id) && !agreeing.has("ask-" + x.e.id)) out.push({ kind: "asked", id: x.e.id, e: x.e, owed: true });
    for (const id of r.awaiting_yes || []) {
      const l = lineById(st, id);
      if (l && l.for === me && !later.has(id) && !agreeing.has("yes-" + id)) out.push({ kind: "yes", id, l, owed: true });
    }
    for (const x of mine) if (x.kind === "question" && !later.has(x.q.id)) out.push({ kind: "question", id: x.q.id, q: x.q, owed: true });
    for (const o of offeredNow()) {
      if (o.for === me) continue;
      const ln = lineById(st, o.line);
      if (ln && !K().done.has(o.line)) out.push({ kind: "offer", id: o.line, o, ln, owed: false });
    }
    return out;
  }

  function renderOne() {
    const t = C.t, st = C.state, me = st.actor;
    $tray.textContent = "";
    // an answered card stays where the hand is until the stream confirms it (or it was undone)
    if (K().answered) {
      const status = K().answered.pending ? K().answered.pending.status : "holding";
      const still = asks().some((x) => x.id === K().answered.id);
      if (status === "undone" || status === "refused") K().answered = null;
      // kept on this device (a file fixture, no server) is treated as written: the yes stays in place
      // until the ask is gone, exactly as when served
      else if ((status === "written" || status === "kept-here") && !still) { K().done.add(K().answered.id); K().answered = null; }
    }
    if (K().answered) { $tray.hidden = false; $tray.append(answeredCard()); return; }
    const all = asks();
    if (!all.length) { $tray.hidden = true; return; }
    $tray.hidden = false;
    const a = all[0];
    const more = all.length - 1;
    const later = () => { const s = new Set(local.sget("later." + rid, [])); s.add(a.id); local.sset("later." + rid, [...s]); render(); };
    let eyebrowText = "", title = "", sub = null, acts = [];
    const answer = (type, body, links, words, label) => yes(a.id, type, body, links, words, label, { id: a.id, eyebrow: eyebrowText, title, words });
    if (a.kind === "asked") {
      const e = a.e, card = C.read.card(st, e.id);
      const req = (st.lines || []).find((l) => l.holon === rid && l.type === "request" && l.body && l.body.title === e.title);
      const witness = (req && req.body && req.body.witness) || null;
      const size = e.minutes || (card && card.minutes) || null;
      eyebrowText = [t("talk.one.asked"), C.fmt.by(e.due)].filter(Boolean).join(" · ");
      title = e.title;
      const sizeWords = !size ? null : size >= 60 && size % 60 === 0 ? (size === 60 ? t("table.size_hour") : t("table.size_hours", { n: C.fmt.number(size / 60, true) }))
        : C.fmt.aboutMinutes(size).toLowerCase();
      sub = [req ? t("talk.one.from", { who: lineWho(C, req, rid) }) : null, sizeWords,
        witness && !isElided(witness) ? t("talk.one.witness", { who: whoOf(C, witness, rid) }) : null].filter(Boolean).join(" · ");
      acts = [h("button", { class: "pill primary one-act", onclick: () => answer("commit",
          { card: e.id, by: e.due, size: size || undefined, witness: witness && !isElided(witness) ? witness : undefined }, {},
          t("talk.one.done_commit", { what: e.title.charAt(0).toLowerCase() + e.title.slice(1), by: C.fmt.by(e.due) || "" }).replace(/, \./, "."), t("table.committed", { what: e.title })) }, t("table.yes_commit")),
        h("button", { class: "pill quiet", onclick: later }, t("table.not_yet"))];
    } else if (a.kind === "yes") {
      const l = a.l;
      eyebrowText = t("talk.one.yes");
      title = (l.body && l.body.text) || "";
      sub = t("table.drafted_by", { who: isAgentLine(C, l) ? agentOf(C, l.actor, rid) : lineWho(C, l, rid) });
      acts = [h("button", { class: "pill primary one-act", onclick: () => answer("decide", { text: title }, { answers: [l.id] }, t("talk.one.done_decide", { text: title }), t("talk.agree_consequence")) }, t("table.yes_decide")),
        h("button", { class: "pill quiet", onclick: later }, t("table.not_yet"))];
    } else if (a.kind === "question") {
      const q = a.q;
      eyebrowText = [eyebrow(C, q.type || "rfg"), C.fmt.by(q.by)].filter(Boolean).join(" · ");
      title = isElided(q.question) ? t("record.hidden") : q.question;
      sub = q.asker ? t("table.asked_by", { who: whoOf(C, q.asker, rid) }) : null;
      acts = [h("button", { class: "pill primary one-act", onclick: () => { const id = "q-" + q.id; replying.add(id); open.add(id); render();
          const li = $list.querySelector(`[data-id="${CSS.escape(id)}"]`); if (li) li.scrollIntoView({ block: "center" }); } }, t("talk.one.answer")),
        h("button", { class: "pill quiet", onclick: later }, t("table.not_yet"))];
    } else {
      const ln = a.ln, agentL = isAgentLine(C, ln);
      eyebrowText = t(ln.type === "sight" ? "talk.sighted_by" : "talk.offered_by", { who: isElided(ln.actor) ? t("app.a_member") : agentL ? agentOf(C, ln.actor, rid) : C.read.who(st, ln.actor, rid) }).replace(/\.$/, "");
      title = textOf(ln);
      sub = a.o.reason === "untrusted" ? t("talk.untrusted") : null;
      acts = [h("button", { class: "pill primary one-act", onclick: () => answer("settle", { text: textOf(ln) }, { anchored_to: [a.o.line] }, t("talk.one.done_agree", { text: textOf(ln) }), t("talk.agree_consequence")) }, t("talk.agree")),
        h("button", { class: "pill quiet", onclick: () => { const s = setAside(); s.add(a.o.line); local.sset("aside." + rid, [...s]); render(); } }, t("talk.not_this"))];
    }
    const card = h("article", { class: `one-card${a.owed ? " owed" : ""}${a.kind === "offer" && isAgentLine(C, a.ln) ? " is-agent" : ""}`, "aria-label": eyebrowText },
      h("div", { class: "one-top" }, h("p", { class: "eyebrow one-eyebrow" }, eyebrowText),
        more > 0 && typeof C.openTable === "function" ? h("button", { class: "link-btn one-more", onclick: () => C.openTable() },
          more === 1 ? t("talk.one.more_one") : t("talk.one.more_n", { n: C.fmt.number(more, true) })) : null),
      h("p", { class: "one-title" }, title),
      sub ? h("p", { class: "dust one-sub" }, sub) : null,
      h("div", { class: "one-acts" }, acts));
    if (!$tray.dataset.shown || $tray.dataset.shown !== a.id) {
      // the card rises from the foot when it is new: what moved (a new ask), from where (below)
      requestAnimationFrame(() => C.animate(card, [{ transform: `translateY(${cssVar("--rise-line")})`, opacity: 0 }, { transform: "none", opacity: 1 }],
        { duration: cssMs("--d-settle"), easing: cssVar("--e-settle") }));
      $tray.dataset.shown = a.id;
    }
    $tray.append(card);
  }

  /** The answered card, in place: the gold released, its ink deepening, what she said yes to in
      words, and "Yes · Undo" until the hold ends; then "Yes" with where it went, until the stream
      confirms and the next ask rises. Drawn in the same task as the tap: within a tenth of a second. */
  function answeredCard() {
    const t = C.t, a = K().answered;
    const holding = a.pending && a.pending.status === "holding";
    const card = h("article", { class: "one-card is-answered", role: "status" },
      h("div", { class: "one-top" }, h("p", { class: "eyebrow one-eyebrow" }, a.eyebrow)),
      h("p", { class: "one-title" }, a.title),
      h("p", { class: "one-said" }, "✓ " + a.words),
      h("div", { class: "one-acts one-yes-row" }, h("span", { class: "one-yes" }, t("talk.one.yes_word")),
        holding ? [h("span", { class: "dust", "aria-hidden": "true" }, " · "), h("button", { class: "link-btn one-undo", onclick: () => a.pending.undo() }, t("talk.undo"))]
          : h("span", { class: "dust" }, " · " + t("talk.one.recording"))));
    if (a.fresh) {
      a.fresh = false;
      // the ink deepens where the hand is: paper to full ink (DESIGN-ROOM §2.3)
      requestAnimationFrame(() => C.animate(card.querySelector(".one-title"), [{ color: cssVar("--ink-kept") }, { color: cssVar("--ink-agreed") }],
        { duration: cssMs("--d-card"), easing: cssVar("--e-settle") }));
    }
    return card;
  }

  // ------------------------------------------------------------------ acts

  /** A person's Agree: a `settle` in the room's record (human-only; five seconds of Undo). */
  function agree(key, text, anchor, by) {
    yes(key, "settle", { text }, anchor ? { anchored_to: [anchor] } : {}, text, C.t("talk.agree_consequence"));
  }

  /** A person's yes, in the flow: the line drops into the Talk where it belongs, drying to full
      ink, with Undo written in the line itself for the hold (no toast, no confirm). */
  function yes(key, type, body, links, text, label, inCard) {
    const t = C.t;
    if (inCard) {
      // the yes is answered where it was asked: the card stays, and nothing moves elsewhere
      K().answered = { ...inCard, pending: null, fresh: true };
      const mine = K().answered;
      const p = C.act(type, body, links, rid, { confirmed: true, quiet: true, label, onUndo: () => { if (K().answered === mine) K().answered = null; render(); } });
      mine.pending = p;
      p.done.then(() => render());
      render();
      if (C.offline) $live.textContent = t("talk.yes_waits");
      return;
    }
    const entry = { text, type, by: C.state.actor, at: C.fmt.now().toISOString(), fresh: true, pending: null };
    agreeing.set(key, entry);
    selfAdded = true;
    const p = C.act(type, body, links, rid, { confirmed: true, quiet: true, label, onUndo: () => { agreeing.delete(key); render(); } });
    entry.pending = p;
    p.done.then((r) => { if (r.status === "refused") agreeing.delete(key); render(); });
    open.delete(key);
    render();
    if (C.offline) $live.textContent = t("talk.yes_waits");
  }

  function makeCard(it, as) {
    C.shared.addDraft({ id: "draft-" + Math.random().toString(16).slice(2, 8), title: it.text, as: as || "card",
      sightKind: it.line && it.line.body && typeof it.line.body.kind === "string" ? it.line.body.kind : null,
      anchor: it.line ? it.line.id : (it.kind === "agreed" ? it.id : null) });
    open.delete(it.id);
    render();
    if (C.phone && typeof C.openTable === "function") C.openTable();   // the draft is on the Table
  }

  /** The Talk's say: through ctx.say (serve.py's /say, a said line in the room's live store,
      never the record); kept on this device, waiting to send, when the shell has no say. */
  function send(text, extra = {}) {
    if (typeof C.say !== "function") { enqueue(text, extra); return; }
    C.say(rid, text, extra).then((r) => {
      if (r && r.ok === false && r.reason) { $live.textContent = C.t("talk.not_sent", { reason: r.reason }); hintLine(C.t("talk.not_sent", { reason: r.reason })); }
      render();
    }).catch(() => { enqueue(text, extra); render(); });
  }
  let hintLine = () => {};

  function enqueue(text, extra = {}) {
    const q = queue();
    const now = C.fmt.now();
    // the same line twice within thirty seconds is one line (§4.4)
    if (q.some((x) => x.text === text && x.parent === extra.parent && Math.abs(now - new Date(x.ts)) < 30000)) return;
    q.push({ id: "mine-" + Math.random().toString(16).slice(2, 10), text, ts: now.toISOString(), part: room().current_part || null, ...extra });
    local.set("queue." + rid, q);
  }

  // ------------------------------------------------------------------ the line to offer

  function renderForm() {
    const t = C.t;
    const ta = h("textarea", { rows: "1", class: "offer-input", id: "offer-" + Math.random().toString(16).slice(2, 6),
      placeholder: t("talk.placeholder"), "aria-label": t("talk.offer_label") });
    const hint = h("p", { class: "dust offer-hint", hidden: true });
    hintLine = (msg) => { hint.hidden = false; hint.textContent = msg; };
    const mic = h("button", { class: "mic", type: "button", "aria-label": t("talk.speak"), title: t("talk.speak") }, micIcon());
    let rec = null;
    mic.addEventListener("click", async () => {
      const R = window.SpeechRecognition || window.webkitSpeechRecognition;
      // dictation only where the device keeps it on the device (DESIGN §4.6)
      if (R && "processLocally" in R.prototype) {
        try {
          if (rec) { rec.stop(); rec = null; mic.setAttribute("aria-pressed", "false"); return; }
          rec = new R();
          rec.processLocally = true;
          rec.lang = document.documentElement.lang || "en";
          rec.interimResults = false;
          rec.onresult = (e) => { ta.value = (ta.value ? ta.value + " " : "") + e.results[0][0].transcript; ta.focus(); };
          rec.onend = () => { rec = null; mic.setAttribute("aria-pressed", "false"); };
          rec.onerror = () => { hint.hidden = false; hint.textContent = t("talk.mic_keyboard"); };
          mic.setAttribute("aria-pressed", "true");
          rec.start();
          return;
        } catch { rec = null; }
      }
      hint.hidden = false;
      hint.textContent = t("talk.mic_keyboard");
      ta.focus();
    });
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + "px"; });
    const f = h("form", { class: "offer", onsubmit: (e) => {
      e.preventDefault();
      const text = ta.value.trim();
      if (!text) return;
      send(text);
      selfAdded = true;
      ta.value = ""; ta.style.height = "";
      render();
      scrollToFoot();
    } },
      h("div", { class: "offer-row" }, ta, mic, h("button", { class: "pill primary", type: "submit" }, t("talk.offer"))),
      hint,
      C.phone ? null : h("div", { class: "offer-foot" },
        h("button", { class: "link-btn need-now", type: "button", onclick: () => {
          const text = ta.value.trim() || t("talk.need_now_line");
          send(text, { now: true }); selfAdded = true; ta.value = ""; render(); scrollToFoot();
        } }, t("talk.need_now")),
        h("span", { class: "dust offer-note" }, C.offline ? t("room.error") : t("talk.queue_note"))));
    ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); f.requestSubmit(); } });
    return f;
  }

  function micIcon() {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 20 20"); svg.setAttribute("width", "20"); svg.setAttribute("height", "20"); svg.setAttribute("aria-hidden", "true");
    for (const d of ["M10 2.5a2.5 2.5 0 0 0-2.5 2.5v5a2.5 2.5 0 0 0 5 0V5A2.5 2.5 0 0 0 10 2.5z", "M5 9.5a5 5 0 0 0 10 0", "M10 14.5v3"]) {
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", d); p.setAttribute("fill", "none"); p.setAttribute("stroke", "currentColor");
      p.setAttribute("stroke-width", "1.5"); p.setAttribute("stroke-linecap", "round");
      svg.append(p);
    }
    return svg;
  }

  // ------------------------------------------------------------------ scrolling and returning

  function scrollable() { return $list && $list.scrollHeight > $list.clientHeight + 1 && getComputedStyle($list).overflowY !== "visible"; }
  function atFoot() {
    if (!$list) return true;
    if (scrollable()) return $list.scrollTop + $list.clientHeight >= $list.scrollHeight - 48;
    return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 48 || firstRender;
  }
  function scrollToFoot() {
    if (!$list) return;
    if (scrollable()) $list.scrollTop = $list.scrollHeight;
    else if (C && C.phone) window.scrollTo(0, document.documentElement.scrollHeight);   // the phone: the page is the Talk
  }

  /** "While you were away": one line on return, from what this device last saw (§3). */
  function showAway() {
    const t = C.t, st = C.state;
    const seen = local.get("seen." + rid, null);
    if (!seen || !seen.at) return;
    const away = C.fmt.now() - new Date(seen.at);
    if (!(away > 10 * 60000)) return;
    const agreedNew = (room().lines || []).filter((id) => !(seen.lines || []).includes(id)).map((id) => lineById(st, id)).filter(Boolean);
    const decisions = agreedNew.filter((l) => l.type === "decide").length;
    const others = agreedNew.length - decisions;
    const cardsNow = (st.cards || []).filter((c) => c.holon === rid && c.holder === st.actor && !(seen.cards || []).includes(c.id)).length;
    const bits = [];
    if (decisions) bits.push(decisions === 1 ? t("talk.away_decision_one") : t("talk.away_decisions", { n: C.fmt.number(decisions, true) }));
    if (others) bits.push(others === 1 ? t("talk.away_agreed_one") : t("talk.away_agreed", { n: C.fmt.number(others, true) }));
    if (cardsNow) bits.push(cardsNow === 1 ? t("talk.away_card_one") : t("talk.away_cards", { n: C.fmt.number(cardsNow, true) }));
    if (!bits.length) return;
    $away.hidden = false;
    $away.textContent = t("talk.away", { what: bits.length > 1 ? bits.slice(0, -1).join(", ") + t("talk.and") + bits[bits.length - 1] : bits[0] });
  }
  function remember() {
    if (!C || !rid) return;
    const st = C.state;
    local.set("seen." + rid, { at: C.fmt.now().toISOString(), lines: room().lines || [],
      cards: (st.cards || []).filter((c) => c.holon === rid && c.holder === st.actor).map((c) => c.id) });
  }

  return { mount, update, unmount };
}

function toggle(set, k) { if (set.has(k)) set.delete(k); else set.add(k); }
