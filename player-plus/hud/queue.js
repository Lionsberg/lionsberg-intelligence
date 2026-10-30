// queue.js: The Queue (DESIGN §4.3). Everything waiting on the wearer across every record
// she holds, in the deal's order, with what fits the time she has; and, on the other tab,
// what is owed to her. A view factory per the contract in shell.js.

import { h, cardModel, renderCard } from "./card.js";
import { store } from "./state.js";

export default function createQueue() {
  let el, ctx, side = "me", fits = null;
  const root = h("div", { class: "queue" });

  function entries() {
    const st = ctx.state;
    const all = ((st.owed && st.owed.entries) || []).filter((e) => !ctx.filter || e.holon === ctx.filter);
    // one card, one row: an owed commitment and the card it is about are the same thing
    const keyOf = (e) => {
      if (e.kind === "commitment") { const k = (st.commitments || []).find((x) => x.id === e.id); if (k && k.card) return k.card; }
      return e.id;
    };
    const mine = all.filter((e) => e.holder === st.actor && !store.answered.has(e.id));
    const mineKeys = new Set(mine.map(keyOf));
    const seenOthers = new Set();
    const others = all.filter((e) => {
      if (e.holder === st.actor) return false;
      const k = keyOf(e);
      if (mineKeys.has(k) || seenOthers.has(k)) return false;
      seenOthers.add(k); return true;
    });
    // the deal's order first, then by due date (the engine's own order otherwise)
    const order = ((st.deal && st.deal.cards) || []).map((c) => c.id);
    const rank = (e) => { const i = order.indexOf(e.id); return i < 0 ? 999 : i; };
    const due = (e) => e.due || "9999";
    const sort = (a, b) => rank(a) - rank(b) || String(due(a)).localeCompare(String(due(b)));
    return { mine: mine.sort(sort), others: others.sort(sort) };
  }

  function draw() {
    const t = ctx.t, f = ctx.fmt, st = ctx.state;
    root.textContent = "";
    const { mine, others } = entries();
    const tabs = h("div", { class: "segmented", role: "tablist" },
      [["me", t("queue.waiting_on_me"), mine.length], ["others", t("queue.waiting_on_others"), others.length]].map(([k, label, n]) =>
        h("button", { role: "tab", "aria-selected": String(side === k), class: "seg", onclick: () => { side = k; draw(); } },
          label, h("span", { class: "dust figures" }, ` · ${n}`))));
    root.append(tabs);

    let list = side === "me" ? mine : others;
    if (side === "me") {
      const opts = [null, 5, 15, 30, 60];
      const chip = h("button", { class: "chip figures", onclick: () => { fits = opts[(opts.indexOf(fits) + 1) % opts.length]; draw(); } },
        fits ? t("queue.fits", { n: fits }) : t("queue.fits_any"));
      root.append(h("div", { class: "queue-tools" }, chip));
      if (fits) {
        let used = 0;
        const mins = (e) => { const mm = cardModel(ctx, { owed: e }); return mm.minutes || 0; };
        list = list.filter((e) => { const m = mins(e); if (used + m > fits) return false; used += m; return true; });
      }
    }

    if (!list.length) {
      root.append(h("p", { class: "placeholder" }, side === "me" ? t("queue.empty_me") : t("queue.empty_others")));
    } else {
      const ul = h("ul", { class: "queue-rows", role: "tabpanel" });
      for (const e of list) {
        const m = cardModel(ctx, { owed: e });
        if (side === "others") m.reason = t("reason.on_other", { who: ctx.read.who(st, e.holder, e.holon) });
        const row = renderCard(ctx, m, { form: "row", selected: ctx.selected === e.id,
          onOpen: () => (ctx.read.card(st, e.id) ? ctx.openCard(e.id) : ctx.go("#/deal")) });
        // overdue is said in words in the foot ("one day past"), never in red alone
        if (m.minutes) row.prepend(h("span", { class: "queue-min figures dust" }, t("time.minutes", { n: Math.round(m.minutes) })));
        ul.append(h("li", null, row));
      }
      root.append(ul);
    }
    const props = (st.owed && st.owed.proposals) || [];
    if (side === "me" && props.length) {
      root.append(h("p", { class: "dust queue-props-note" }, t("queue.proposals")));
      const ul = h("ul", { class: "queue-rows is-proposals" });
      for (const e of props) {
        const m = cardModel(ctx, { owed: e });
        m.reason = t("queue.noticed");
        ul.append(h("li", null, renderCard(ctx, m, { form: "row" })));
      }
      root.append(ul);
    }
  }

  return {
    mount(container, c) {
      el = container; ctx = c;
      const s = c.route && c.route.params && c.route.params.get("side");
      if (s === "others" || s === "me") side = s;
      el.append(root); draw();
    },
    update(c) { ctx = c; draw(); },
    unmount() { root.textContent = ""; },
  };
}
