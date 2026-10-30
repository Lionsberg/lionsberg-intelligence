// ledger.js: the Ledger (DESIGN §4.7; lifted to DESIGN-THE-BAR 2026-10-24): the time given
// toward the work, witnessed. The season in one sentence, then what is still only claimed, in
// words, then the one act, Add time (a `tea` line by her tap), all on the first screen. Then
// per holon, one row per entry (date · card · time in words · witness), the witness carried
// by the ink grammar (claimed in dust, witnessed by the cell in paper, witnessed beyond in
// full ink and weight) with its word beside it: no glyphs, no legend, no gold. Energy and
// attention stay in the entry as she gave them and are not drawn as bars. Non-convertible,
// said on its face. Then discernment, lightly, for the wearer only. A keeper sees Witness on a
// claimed entry.

import { h } from "./card.js";
import { useStyle, lineById, whoOf } from "./inks.js";

const WITNESS = { unwitnessed: "claimed", keeper: "cell", supercell: "beyond", claimed: "claimed", cell: "cell", beyond: "beyond" };

/** One sum, from which every figure the Ledger shows is read: the headline, each house's line,
    and what is still only claimed. With the entries, it is their sum (within the season when the
    season is given); the person's own time is counted apart from others' in the same house, so
    the headline is always the sum of the "given by you" in each house. Without the entries only
    the person's own total is known; each house's total counts everyone's time and cannot be
    split, so no house line is drawn rather than one that reads as a contradiction. Pure: no DOM,
    so fixtures/test_ledger_sum.mjs proves it. */
export function ledgerSums(tea, me, holonIds) {
  const entries = Array.isArray(tea && tea.entries) ? tea.entries : null;
  const season = tea && tea.season && tea.season.from ? tea.season : null;
  const out = { source: entries ? "entries" : "totals", season: !!season, mine: 0, witnessed: 0, claimed: 0, holons: {} };
  if (!entries) {
    const a = ((tea && tea.by_actor) || {})[me];
    if (a) { out.mine = Math.round(a.minutes || 0); out.witnessed = Math.round(a.witnessed_minutes || 0); }
    return out;
  }
  const inSeason = (ts) => !season || (String(ts).slice(0, 10) >= season.from && (!season.to || String(ts).slice(0, 10) <= season.to));
  for (const e of entries) {
    if (holonIds && !holonIds.includes(e.holon)) continue;
    if (!inSeason(e.ts)) continue;
    const m = Math.round(e.minutes || 0);
    const w = WITNESS[e.witness] || "claimed";
    const own = (e.actor || me) === me;
    const hh = out.holons[e.holon] || (out.holons[e.holon] = { mine: 0, theirs: 0, rows: [] });
    hh.rows.push(e);
    if (own) { hh.mine += m; out.mine += m; if (w === "claimed") out.claimed += 1; else out.witnessed += m; }
    else hh.theirs += m;
  }
  return out;
}

export default function createLedger() {
  let el = null, C = null;
  function mount(host, ctx) { useStyle("ledger.css"); el = host; C = ctx; render(); }
  function update(ctx) { C = ctx; render(); }
  function unmount() { el = null; }

  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function hours(min) {
    const t = C.t, f = C.fmt;
    const hrs = Math.round((min || 0) / 60);
    if (min < 60) return min === 1 ? t("ledger.one_minute") : t("ledger.minutes", { n: f.number(Math.round(min), true) });
    return hrs === 1 ? t("ledger.one_hour") : t("ledger.hours", { n: f.number(hrs, true) });
  }

  function render() {
    if (!el) return;
    const t = C.t, f = C.fmt, st = C.state, me = st.actor;
    const tea = st.tea || {};
    el.textContent = "";
    const wrap = h("div", { class: "ledger" });
    el.append(wrap);

    // one sum for every figure on this page
    const holons = C.read.holons(st).filter((x) => !C.filter || x.id === C.filter);
    const sum = ledgerSums(tea, me, holons.map((x) => x.id));
    if (!sum.mine && sum.source === "totals" && !(tea.by_actor || {})[me]) wrap.append(h("p", { class: "voice ledger-season" }, t("ledger.empty")));
    else wrap.append(h("p", { class: "voice ledger-season" },
      t(sum.season ? "ledger.season" : "ledger.held", { given: hours(sum.mine), witnessed: hours(sum.witnessed) })));

    // what of hers is still only claimed, counted from the same rows; then the one act
    if (sum.claimed) {
      const s = sum.claimed === 1 ? t("ledger.claimed_mine_one") : t("ledger.claimed_mine_n", { n: f.number(sum.claimed, true) });
      wrap.append(h("p", { class: "ledger-claimed" }, cap(s)));
    }
    wrap.append(h("div", { class: "ledger-acts" }, h("button", { class: "pill primary", onclick: addTime }, t("ledger.add"))));

    for (const x of holons) {
      const hh = sum.holons[x.id];
      if (!hh || !hh.rows.length) continue;
      const rows = [...hh.rows].sort((a, b) => String(b.ts).localeCompare(String(a.ts)));
      const keeper = C.read.role(st, me, x.id) === "keeper" || x.keeper === me;
      const tbl = h("table", { class: "ledger-table" },
        h("caption", { class: "sr-only" }, t("ledger.caption", { holon: x.name })),
        h("thead", null, h("tr", null, ["date", "card", "time", "witness"].map((k) =>
          h("th", { scope: "col" }, t("ledger.col." + k))))),
        h("tbody", null, rows.map((e) => row(e, x, keeper))));
      const line = hh.theirs ? t("ledger.holon_mine_theirs", { mine: hours(hh.mine), theirs: hours(hh.theirs) })
        : t("ledger.holon_mine", { mine: hours(hh.mine) });
      wrap.append(h("section", { class: "ledger-holon" },
        h("h3", { class: "caps" }, x.name),
        h("p", { class: "dust ledger-holon-sum" }, cap(line) + " · " + (f.asOf(x.as_of && x.as_of.ts) || "")),
        h("div", { class: "ledger-scroll" }, tbl)));
    }

    // what points are, behind one word (doctrine, not data)
    const about = h("details", { class: "ledger-about" }, h("summary", { class: "dust" }, t("ledger.about_points")),
      h("p", { class: "dust ledger-law" }, t("ledger.kept_never_sold")),
      tea.convertible === false ? h("p", { class: "dust ledger-law" }, t("ledger.not_convertible")) : null);
    wrap.append(about);

    // discernment, lightly: for the wearer only
    const d = st.discernments || {};
    const by = d.by_verdict || {};
    const lines = Array.isArray(d.lines) ? d.lines : [];
    const dis = h("section", { class: "ledger-discern" }, h("h3", { class: "caps" }, t("ledger.discern_title")),
      h("p", { class: "dust" }, t("ledger.discern_private")));
    if (d.count) dis.append(h("p", null, t("ledger.discern_counts", {
      chosen: f.number(by.chosen || 0, true), corrected: f.number(by.corrected || 0, true), rated: f.number(by.rated || 0, true) })));
    if (lines.length) dis.append(h("ul", { class: "discern-lines" }, lines.map((x) => h("li", null,
      [t("ledger.verdict." + x.verdict), x.about, f.when(x.ts)].filter(Boolean).join(" · ")))));
    else if (!d.count) dis.append(h("p", { class: "dust" }, t("ledger.discern_none")));
    wrap.append(dis);

    wrap.append(h("div", { class: "print-only ledger-paper" }, h("h3", { class: "caps" }, t("ledger.paper_title")),
      h("table", { class: "paper-table" }, h("thead", null, h("tr", null, ["date", "card", "minutes", "energy", "attention", "witness"].map((k) => h("th", null, t("ledger.col." + k))))),
        h("tbody", null, Array.from({ length: 8 }, () => h("tr", { class: "paper-blank" }, Array.from({ length: 6 }, () => h("td", null, ""))))))));
    wrap.append(h("div", { class: "page-foot" }, h("button", { class: "link-btn", onclick: () => window.print() }, t("ledger.print"))));
  }

  function row(e, x, keeper) {
    const t = C.t, f = C.fmt, st = C.state;
    const w = WITNESS[e.witness] || "claimed";
    const card = C.read.card(st, e.card);
    const ink = w === "beyond" ? "ink-agreed" : w === "cell" ? "ink-kept" : "ink-said";
    return h("tr", { class: ink },
      h("td", { class: "figures" }, f.when(e.ts) || ""),
      h("td", null, card ? card.title : t("ledger.no_card"), e.actor && e.actor !== st.actor ? h("span", { class: "dust" }, " · " + t("ledger.row_theirs", { who: whoOf(C, e.actor, x.id) })) : null),
      h("td", { class: "ledger-time" }, hours(Math.round(e.minutes || 0))),
      h("td", null, h("span", { class: `wmark w-${w}` }, t("ledger.witness." + w)),
        keeper && w === "claimed" && e.actor !== st.actor && e.line ? h("button", { class: "link-btn", onclick: () =>
          C.act("witness", { note: t("ledger.witnessed_note") }, { witnesses: [e.line] }, x.id, { confirmed: true, label: t("ledger.witnessed") }) }, t("ledger.witness_btn")) : null));
  }

  function addTime() {
    const t = C.t, st = C.state;
    const cards = (st.cards || []).filter((c) => c.holder === st.actor);
    const holons = C.read.holons(st);
    const card = h("select", { "aria-label": t("ledger.col.card") }, h("option", { value: "" }, t("ledger.no_card")),
      cards.map((c) => h("option", { value: c.id }, c.title)));
    const mins = h("input", { type: "number", min: "1", step: "5", value: "30", inputmode: "numeric" });
    const en = h("input", { type: "range", min: "1", max: "10", value: "6" });
    const at = h("input", { type: "range", min: "1", max: "10", value: "6" });
    const body = h("div", { class: "ledger-form" },
      h("label", null, h("span", { class: "eyebrow" }, t("ledger.col.card")), card),
      h("label", null, h("span", { class: "eyebrow" }, t("ledger.col.minutes")), mins),
      h("label", null, h("span", { class: "eyebrow" }, t("ledger.col.energy")), en),
      h("label", null, h("span", { class: "eyebrow" }, t("ledger.col.attention")), at),
      h("p", { class: "dust" }, t("ledger.add_line")));
    let close = null;
    close = C.openSheet({ title: t("ledger.add"), body, actions: [
      h("button", { class: "pill primary", onclick: () => {
        const c = C.read.card(st, card.value);
        const holon = (c && c.holon) || C.home || (holons[0] && holons[0].id);
        C.act("tea", { minutes: Number(mins.value) || 0, energy: Number(en.value), attention: Number(at.value), card: card.value || undefined },
          {}, holon, { confirmed: true, label: t("ledger.added") });
        close();
      } }, t("ledger.add_confirm")),
      h("button", { class: "pill quiet", onclick: () => close() }, t("ledger.add_cancel"))] });
  }

  return { mount, update, unmount };
}
