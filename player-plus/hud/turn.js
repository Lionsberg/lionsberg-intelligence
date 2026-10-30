// turn.js: the Turn (DESIGN §4.8; lifted to DESIGN-THE-BAR).
// The week in one sentence the gaps can never contradict ("Two kept on time, and one a day
// late."), computed from the kept tally with the late ones counted out of it. Then the week's
// story as the four lines (Kept · The gap, and what it taught · Next · The Flame
// passed), set like a letter, each only when the engine drafted it; a line the engine did not
// draft is not shown, and a record with nothing drafted says when the first turn comes and
// nothing else. A tap on a line puts it in the person's own words. The one act, "This is my
// week", sits on the first screen and writes a `turn` by her hand. Its consequence is the
// Turn's one scene: the made field frame turns a quarter and ends still; it never
// plays while something is owed, and under reduced motion it is its last frame. Each gap, in
// words with what it taught, and the depth the day calls for, in words, follow.

import { h } from "./card.js";
import { useStyle, cssMs, cssVar, local } from "./inks.js";

const FOUR = ["kept", "gap", "next", "flame"];
const FIELD_FRAME = "art/b-field-person-c.jpg";

export default function createTurn() {
  let el = null, C = null;
  let quarter = local.get("turn.quarter", 0);
  const words = {};
  const editing = new Set();
  let closed = null;      // the pending act once she says "This is my week"

  function mount(host, ctx) { useStyle("turn.css"); el = host; C = ctx; render(); }
  function update(ctx) {
    C = ctx;
    // a person typing keeps her caret: no redraw while one of her lines has the focus
    if (el && el.contains(document.activeElement) && document.activeElement.tagName === "TEXTAREA") return;
    render();
  }
  function unmount() { el = null; }

  function scope() {
    const st = C.state, k = st.kept || {};
    if (C.filter && (k.by_holon || {})[C.filter]) return { tally: k.by_holon[C.filter], holon: C.filter, name: C.read.holonName(st, C.filter) };
    return { tally: (k.by_actor || {})[st.actor] || null, holon: null, name: null };
  }

  /** The commitments kept late in the tally's window, the same set read.keptLate counts. */
  function lateOnes(sc) {
    const st = C.state, kept = st.kept || {};
    const ids = Array.isArray(kept.commitments) ? new Set(kept.commitments) : null;
    return (st.commitments || []).filter((k) => (k.status === "kept" || k.status === "kept-unwitnessed")
      && k.gap_days != null && k.gap_days > 0
      && (sc.holon ? k.holon === sc.holon : k.keeper === st.actor)
      && (!ids || ids.has(k.id) || k.keeper === st.actor));
  }

  /** "Two kept on time, and one a day late." Every count in words, and the parts always add up. */
  function weekSentence(tally, late) {
    const t = C.t, f = C.fmt;
    const kept = (tally.kept || 0) + (tally.kept_unwitnessed || 0);
    const nLate = C.read.keptLate ? Math.min(kept, C.read.keptLate(C.state, C.state.actor, scope().holon)) : late.length;
    const onTime = Math.max(0, kept - nLate);
    const broken = tally.broken || 0;
    if (!nLate && !broken) return onTime === 1 ? t("turn.week.one_on_time") : t("turn.week.all_on_time", { n: f.number(onTime, true) });
    const bits = [];
    if (onTime) bits.push(t("turn.week.on_time", { n: f.number(onTime, true) }));
    if (nLate === 1) {
      const d = Math.round((late[0] && late[0].gap_days) || 1);
      bits.push(d === 1 ? t("turn.week.late_one_day") : t("turn.week.late_one_days", { d: f.number(d, true) }));
    } else if (nLate) bits.push(t("turn.week.late_n", { n: f.number(nLate, true) }));
    if (broken) bits.push(broken === 1 ? t("turn.week.broken_one") : t("turn.week.broken_n", { n: f.number(broken, true) }));
    const s = bits.length > 1 ? bits.slice(0, -1).join(t("turn.week.comma")) + t("turn.week.and") + bits[bits.length - 1] : bits[0];
    return s.charAt(0).toUpperCase() + s.slice(1) + ".";
  }

  /** The engine's drafted four lines, keyed by their names; absent, nothing. */
  function drafted() {
    const turn = C.state.turn || {};
    const d = turn.draft && typeof turn.draft === "object" && !Array.isArray(turn.draft) ? turn.draft : {};
    const out = {};
    for (const k of FOUR) {
      const x = d[k];
      const text = x && typeof x === "object" ? x.text : typeof x === "string" ? x : null;
      if (typeof text === "string" && text.trim()) out[k] = { text: text.trim(), draft: !(x && x.status === "settled") };
    }
    return out;
  }

  function owedNow() {
    const st = C.state;
    return ((st.owed && st.owed.entries) || []).some((e) => e.holder === st.actor && e.status === "open");
  }

  function render() {
    if (!el) return;
    const t = C.t, f = C.fmt, st = C.state;
    el.textContent = "";
    const wrap = h("div", { class: "turn" });
    el.append(wrap);
    const turn = st.turn || {};
    const kept = st.kept || {};
    const sc = scope();
    const tally = sc.tally;
    const due = tally ? (tally.kept || 0) + (tally.kept_unwitnessed || 0) + (tally.broken || 0) : 0;
    const late = lateOnes(sc);
    const lines = drafted();
    const nDrafted = Object.keys(lines).length;

    // the week, in one breath
    const head = h("header", { class: "turn-head" });
    if (sc.name) head.append(h("p", { class: "eyebrow" }, t("turn.kept_in", { holon: sc.name })));
    if (!tally || !due) {
      const first = !turn.last_weekly;
      const nd = f.date(turn.next_weekly_due);
      head.append(h("p", { class: "voice turn-week" }, first
        ? (nd ? t("turn.first_day", { day: f.dayName(nd) }) : t("turn.first")) : t("turn.nothing_due")));
      // a new record: when the first turn comes, and nothing else
      if (first && !nDrafted) { wrap.append(head); return; }
    } else {
      head.append(h("p", { class: "voice turn-week" }, weekSentence(tally, late)));
      if (tally.kept_unwitnessed) { const w = t("turn.awaiting_witness", { n: f.number(tally.kept_unwitnessed, true) }); head.append(h("p", { class: "dust" }, w.charAt(0).toUpperCase() + w.slice(1))); }
    }
    const day = (x) => { const d = f.date(x); if (!d) return x; return f.sameDay(d, f.now()) ? t("time.today") : d.toLocaleDateString(undefined, { day: "numeric", month: "long" }); };
    if (kept.window && due) head.append(h("p", { class: "dust" }, t("turn.window", { from: day(kept.window.from), to: day(kept.window.to) })));
    wrap.append(head);

    // the week's story: the four lines, each only where the engine drafted it
    if (nDrafted) {
      const story = h("section", { class: "turn-story", "aria-label": t("turn.four_title") });
      for (const k of FOUR) {
        if (!lines[k]) continue;
        const mine = words[k] != null;
        const val = mine ? words[k] : lines[k].text;
        const row = h("div", { class: `turn-row${mine ? " is-mine" : " is-draft"}` }, h("p", { class: "eyebrow" }, t("turn.line." + k)));
        if (editing.has(k) && !closed) {
          const ta = h("textarea", { rows: "2", class: "turn-line", "aria-label": t("turn.line." + k),
            oninput: (e) => { words[k] = e.target.value; },
            onblur: () => { editing.delete(k); if (words[k] != null && !words[k].trim()) delete words[k]; render(); } });
          ta.value = val;
          row.append(ta);
          requestAnimationFrame(() => { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); });
        } else {
          row.append(h("button", { class: "turn-text", disabled: !!closed, "aria-label": t("turn.change_sr", { line: t("turn.line." + k), text: val }),
            onclick: () => { editing.add(k); render(); } }, val));
        }
        row.append(h("span", { class: "print-only turn-paper-lines" }));
        story.append(row);
      }
      wrap.append(story);

      // the one act, on the first screen
      const acts = h("div", { class: "turn-acts" });
      if (closed) acts.append(h("p", { class: "voice turn-closed" }, t("turn.closed_line")));
      else {
        acts.append(h("button", { class: "pill primary turn-act", onclick: close }, t("turn.mine")),
          h("p", { class: "dust turn-hint" }, Object.keys(words).length ? t("turn.yours_hint") : t("turn.draft_hint")));
        if (sc.holon && sc.holon !== C.home) acts.append(h("button", { class: "pill quiet", onclick: () => C.openPublish({ holon: sc.holon,
          what: t("turn.publish_what"), lines: [] }) }, t("turn.publish", { holon: sc.name })));
      }
      wrap.append(acts);
      if (closed && !owedNow()) wrap.append(scene());
    }

    // each gap, in words, with what it taught
    const gaps = (st.commitments || []).filter((k) => (sc.holon ? k.holon === sc.holon : k.keeper === st.actor)
      && (k.status === "broken" || (k.gap_days != null && k.gap_days > 0)));
    if (gaps.length) {
      const learning = Array.isArray(kept.learning) ? kept.learning : [];
      wrap.append(h("section", { class: "turn-gaps" }, h("h3", { class: "eyebrow" }, gaps.length === 1 ? t("turn.gap_title_one") : t("turn.gaps")),
        h("ul", null, gaps.map((k) => {
          const learned = learning.find((l) => l.about === k.id);
          const gapWords = k.status === "broken" ? t("turn.gap_open") : k.gap_days === 1 ? t("time.one_day_late") : t("time.days_late", { n: f.number(Math.round(k.gap_days), true) });
          return h("li", { class: k.status === "kept" ? "ink-agreed" : k.status === "kept-unwitnessed" ? "ink-kept" : "ink-said" },
            h("span", null, t("turn.gap_line", { title: k.title, gap: gapWords })),
            learned ? h("span", { class: "turn-learned" }, t("turn.taught", { text: learned.text })) : null);
        }))));
    }

    // the depth the day calls for, in words
    const depth = ["daily", "lunar", "seasonal"].includes(turn.depth_due) ? turn.depth_due : "daily";
    const nd = f.date(turn.next_weekly_due);
    wrap.append(h("p", { class: "dust turn-depth" }, [t("turn.depth_line." + depth),
      nd ? t("turn.weekly_due", { when: f.by(turn.next_weekly_due) || turn.next_weekly_due }) : null].filter(Boolean).join(" ")));

    // discernment, lightly (DESIGN §4.8)
    const n = (st.discernments && st.discernments.count) || 0;
    if (n) wrap.append(h("p", { class: "dust turn-discern" }, h("a", { href: "#/ledger" },
      n === 1 ? t("turn.learned_once") : t("turn.learned_n", { n: f.number(n, true) }))));

    wrap.append(h("div", { class: "page-foot" }, h("button", { class: "link-btn", onclick: () => window.print() }, t("turn.print"))));
  }

  /** The Turn's one scene: the field turns a quarter and ends still. Nothing lit. */
  function scene() {
    const img = h("img", { class: "turn-field-img", src: FIELD_FRAME, alt: "", width: "1200", height: "1200", decoding: "async" });
    img.style.transform = `rotate(${quarter * 90}deg)`;
    const fig = h("figure", { class: "turn-field", "aria-hidden": "true" }, img);
    if (closed && closed.fresh) {
      closed.fresh = false;
      requestAnimationFrame(() => C.animate(img, [{ transform: `rotate(${(quarter - 1) * 90}deg)` }, { transform: `rotate(${quarter * 90}deg)` }],
        { duration: cssMs("--d-dolly"), easing: cssVar("--e-settle") }));
    }
    return fig;
  }

  function close() {
    const t = C.t, st = C.state;
    const lines = drafted();
    const text = FOUR.filter((k) => lines[k] || (words[k] && words[k].trim()))
      .map((k) => `${t("turn.line." + k)}: ${(words[k] != null ? words[k] : lines[k].text).trim()}`).join("\n");
    const holon = C.filter || C.home;
    editing.clear();
    const p = C.act("turn", { span: "week", depth: (st.turn && st.turn.depth_due) || "daily", text }, {}, holon,
      { confirmed: true, label: t("turn.settled"), onUndo: () => { closed = null; turnBack(); render(); } });
    closed = { p, fresh: true };
    quarter = (quarter + 1) % 4;
    local.set("turn.quarter", quarter);
    p.done.then((r) => { if (r.status === "refused") { closed = null; turnBack(); render(); } });
    render();
  }
  function turnBack() {
    quarter = (quarter + 3) % 4;
    local.set("turn.quarter", quarter);
  }

  return { mount, update, unmount };
}
