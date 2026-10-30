// record.js: the Record view (DESIGN §4.9; lifted to DESIGN-THE-BAR 2026-10-24): the truth under
// every view, readable by eye. Each line is set as the person's own words, newest first, by
// day, in one order: time. What a line is shows in its weight (what was agreed, decided,
// committed, kept or witnessed is set heavier than what was said, so the decisions read at a
// glance); whether it is signed shows in its ink (signed in full ink, unsigned in paper, a line
// whose link has not arrived in dust), with the word beside it for a screen reader and on hover:
// no glyphs, no legend. Who and when sit small above the words; the house is named only when a
// line comes from elsewhere; links read as words ("about Book the hall"), never as ids. "As of"
// is a time. Search and the two filters wait behind one word, Find, at the foot. Open a line for
// its links followed both ways and its raw form. Lines the fold refused are shown, never counted.

import { h } from "./card.js";
import { useStyle, linesIn, hasLines, lineById, lineWho, whoOf, eyebrow, lineText, verifiedMark, isElided } from "./inks.js";

const LINK_WORD = { predecessor: "record.link.predecessor", successor: "record.link.successor", serves: "record.link.serves",
  fulfils: "record.link.fulfils", answers: "record.link.answers", witnesses: "record.link.witnesses",
  anchored_to: "record.link.anchored_to", supersedes: "record.link.supersedes" };
const CLIMB = new Set(["elevate", "rfg", "escalate"]);
const AGREED = new Set(["settle", "decide", "ratify", "commit", "kept", "witness", "card", "done", "turn", "publish", "posture", "affirm"]);

export default function createRecord() {
  let el = null, C = null;
  const ui = { q: "", type: "", actor: "", open: new Set(), find: false };

  function mount(host, ctx) { useStyle("record.css"); el = host; C = ctx; render(); }
  function update(ctx) {
    C = ctx;
    if (el && el.contains(document.activeElement) && document.activeElement.classList.contains("record-search")) return;
    render();
  }
  function unmount() { el = null; }

  function holonId() {
    if (C.route && C.route.name === "record" && C.route.arg) return C.route.arg;
    if (C.filter) return C.filter;
    return null;   // all holons held
  }

  function clip(s, n = 56) { s = String(s || ""); return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s; }

  function render() {
    if (!el) return;
    const t = C.t, f = C.fmt, st = C.state;
    const hid = holonId();
    const hol = hid ? C.read.holon(st, hid) : null;
    el.textContent = "";
    const wrap = h("div", { class: "record" });
    el.append(wrap);

    // head: whose record, and as of when (a time, never a line id)
    const when = (x) => { const d = f.date(x); if (!d) return null; return f.sameDay(d, f.now()) ? f.time(x) : f.when(x); };
    const asOf = (x) => x && x.as_of && when(x.as_of.ts) ? (hid ? t("record.as_of_only", { when: when(x.as_of.ts) }) : t("record.as_of_time", { holon: x.name, when: when(x.as_of.ts) })) : null;
    wrap.append(h("div", { class: "record-head" },
      h("h3", { class: "caps" }, hol ? hol.name : t("record.all")),
      h("p", { class: "dust record-asof" }, (hid ? [asOf(hol)] : C.read.holons(st).map(asOf)).filter(Boolean).join(" · "))));
    const unread = C.read.unreadable(st).find((s) => s.holon === hid);
    if (unread) wrap.append(h("p", { class: "record-error" }, t("record.unreadable", { holon: unread.name })));

    if (!hasLines(st)) {
      wrap.append(h("p", { class: "dust" }, t("record.lines_absent")));
      return;
    }
    const all = linesIn(st, hid);
    const body = h("div", { class: "record-body" });
    wrap.append(body);

    // refused by the fold: shown, never counted
    const invalid = (st.invalid || []).filter((x) => !hid || x.holon === hid);
    if (invalid.length) wrap.append(h("section", { class: "record-invalid" }, h("h4", { class: "eyebrow" }, t("record.refused")),
      h("ul", null, invalid.map((x) => h("li", { class: "dust" }, [eyebrow(C, x.type), whoOf(C, x.actor, x.holon), x.invalid_reason].filter(Boolean).join(" · "))))));

    // Find: search and the two filters, behind one word at the foot
    const types = [...new Set(all.map((l) => l.type))].sort();
    const actors = [...new Set(all.map((l) => (isElided(l.actor) ? "elided" : l.actor)))];
    const finding = ui.find || ui.q || ui.type || ui.actor;
    const foot = h("div", { class: "record-foot" });
    if (finding) {
      const search = h("input", { type: "search", class: "record-search", value: ui.q, placeholder: t("record.search"), "aria-label": t("record.search"),
        oninput: (e) => { ui.q = e.target.value; draw(); } });
      const typeSel = h("select", { "aria-label": t("record.filter_type"), onchange: (e) => { ui.type = e.target.value; draw(); } },
        h("option", { value: "" }, t("record.every_type")), types.map((x) => h("option", { value: x, selected: ui.type === x }, eyebrow(C, x))));
      const actorSel = h("select", { "aria-label": t("record.filter_actor"), onchange: (e) => { ui.actor = e.target.value; draw(); } },
        h("option", { value: "" }, t("record.everyone")),
        actors.map((a) => h("option", { value: a, selected: ui.actor === a }, a === "elided" ? t("record.hidden") : a === st.actor ? t("app.you") : whoOf(C, a, hid || ""))));
      foot.append(h("div", { class: "record-filters" }, search, typeSel, actorSel),
        h("button", { class: "link-btn", onclick: () => { ui.find = false; ui.q = ui.type = ui.actor = ""; render(); } }, t("record.find_close")));
      if (ui.find === "focus") { ui.find = true; requestAnimationFrame(() => search.focus()); }
    } else {
      foot.append(h("button", { class: "link-btn", onclick: () => { ui.find = "focus"; render(); } }, t("record.find")));
    }
    foot.append(h("button", { class: "link-btn", onclick: () => window.print() }, t("record.print")));
    wrap.append(foot);

    function draw() {
      body.textContent = "";
      const q = ui.q.trim().toLowerCase();
      const at = (l) => { const d = new Date(l.ts); return isNaN(d) ? 0 : d.getTime(); };
      const rows = all.filter((l) => (!ui.type || l.type === ui.type)
        && (!ui.actor || (ui.actor === "elided" ? isElided(l.actor) : l.actor === ui.actor))
        && (!q || lineText(C, l).toLowerCase().includes(q) || eyebrow(C, l.type).toLowerCase().includes(q)))
        .sort((a, b) => at(b) - at(a));
      if (!rows.length) { body.append(h("p", { class: "dust" }, all.length ? t("record.none_match") : t("record.empty"))); return; }
      let day = null, ol = null;
      for (const l of rows) {
        const d = f.date(l.ts);
        const dk = d ? d.toDateString() : "";
        if (dk !== day) {
          day = dk;
          body.append(h("h4", { class: "record-day eyebrow" }, d ? (f.sameDay(d, f.now()) ? t("time.today") : `${f.dayName(d)} · ${d.toLocaleDateString(undefined, { day: "numeric", month: "long" })}`) : ""));
          ol = h("ol", { class: "record-lines" });
          body.append(ol);
        }
        ol.append(row(l, hid));
      }
    }
    draw();
  }

  /** The words a link points at: a line's words or a card's title, clipped; never an id. */
  function aboutWords(l) {
    const st = C.state, links = l.links || {};
    for (const k of ["anchored_to", "answers", "serves", "fulfils", "witnesses", "supersedes", "predecessor", "successor"]) {
      const ids = Array.isArray(links[k]) ? links[k] : [];
      for (const id of ids) {
        const x = lineById(st, id), c = C.read.card(st, id);
        const words = c ? c.title : x ? lineText(C, x) : null;
        if (words && words !== lineText(C, l)) return C.t(k === "anchored_to" ? "record.about" : LINK_WORD[k] ? "record.link_words" : "record.about",
          { what: clip(words), how: C.t(LINK_WORD[k] || "record.link.other") });
      }
    }
    return null;
  }

  function row(l, hid) {
    const t = C.t, f = C.fmt, st = C.state;
    const agentFor = (C.state.actors || []).find((a) => a.id === l.actor && a.kind === "agent");
    const forWho = isElided(l.for) ? t("record.hidden") : l.for === l.actor || !l.for || (agentFor && agentFor.for === l.for) ? null : l.for === st.actor ? t("app.you") : whoOf(C, l.for, l.holon);
    const who = isElided(l.actor) ? t("record.hidden") : l.actor === st.actor ? t("app.you") : lineWho(C, l, l.holon);
    const elsewhere = !hid && l.holon && l.holon !== C.home ? C.read.holonName(st, l.holon) : null;
    const v = verifiedMark(C, l);
    const open = ui.open.has(l.id);
    const weight = AGREED.has(l.type) ? " is-agreed" : "";
    const about = aboutWords(l);
    const meta = [f.time(l.ts), who + (forWho ? " " + t("record.for", { who: forWho }) : ""),
      elsewhere ? t("record.from_house", { house: elsewhere }) : null,
      l.audience && l.audience !== "holon" ? t("record.audience." + l.audience) : null].filter(Boolean).join(" · ");
    const li = h("li", { class: `rline ${v.cls}${weight}${CLIMB.has(l.type) ? " is-climb" : ""}` },
      h("button", { class: "rline-btn", "aria-expanded": String(open), title: v.word,
        onclick: () => { open ? ui.open.delete(l.id) : ui.open.add(l.id); render(); } },
        h("span", { class: "rline-meta dust" }, meta,
          l.type !== "say" ? h("span", { class: "eyebrow rline-type" }, " " + eyebrow(C, l.type)) : null),
        h("span", { class: "rline-what" }, lineText(C, l)),
        about ? h("span", { class: "rline-about dust" }, about) : null,
        h("span", { class: "sr-only" }, ", " + v.word)));
    if (open) li.append(fold(l));
    return li;
  }

  function fold(l) {
    const t = C.t, f = C.fmt, st = C.state;
    const back = (st.lines || []).filter((x) => x.links && Object.values(x.links).some((v) => Array.isArray(v) && v.includes(l.id)));
    const fwd = Object.entries(l.links || {}).flatMap(([k, v]) => (Array.isArray(v) ? v : []).map((id) => ({ k, id })));
    const raw = { ...l };
    delete raw.verified;
    return h("div", { class: "rline-fold" },
      h("p", { class: "dust" }, verifiedMark(C, l).word),
      h("div", { class: "fold-row" }, h("span", { class: "eyebrow" }, t("record.links_out")),
        fwd.length ? h("ul", null, fwd.map(({ k, id }) => { const x = lineById(st, id); const c = C.read.card(st, id);
          return h("li", null, t(LINK_WORD[k] || "record.link.other") + " ", x ? lineText(C, x) : c ? c.title : h("span", { class: "dust" }, t("card.not_yet_arrived"))); }))
          : h("p", { class: "dust" }, t("card.no_links"))),
      h("div", { class: "fold-row" }, h("span", { class: "eyebrow" }, t("record.links_in")),
        back.length ? h("ul", null, back.map((x) => h("li", null, eyebrow(C, x.type) + " · " + lineText(C, x)))) : h("p", { class: "dust" }, t("card.no_links"))),
      l.elided && l.elided.length ? h("p", { class: "dust" }, t("record.elided_note", { n: f.number(l.elided.length, true) })) : null,
      h("details", { class: "rline-raw" }, h("summary", null, t("record.raw")), h("pre", null, JSON.stringify(raw, null, 1))));
  }

  return { mount, update, unmount };
}
