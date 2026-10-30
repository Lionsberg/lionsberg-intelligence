// margin.js: the record margin of the dock (DESIGN-DOCK §2.5).
//
// When your agent writes to the record, or offers to, a line appears in the margin, the edge
// of the dock that faces The Deal, aligned with the turn that made it (beneath it on a phone).
// Each line: an eyebrow in small capitals (COMMITMENT · CARD · SAID IN THE ROOM · KEPT · ASKED),
// its words, and its ink (base.css):
//   said    (.ink-said)    offered or drafted by your agent; not in the record
//   kept    (.ink-kept)    it stays on this computer
//   agreed  (.ink-agreed)  in the record, signed by you, with ✓
// Only a person agrees: a said line carries Agree · Not this, and Agree writes through
// ctx.act(..., {confirmed: true}) from the person's own tap, with its five seconds of Undo.
// The ink dries over --d-ink; nothing else celebrates. Tap a line and its card opens.
// Never shown: a count of what your agent produced, a tool's raw output, or a line whose
// audience is narrower than you.
// A line your agent wrote to the record itself (source "record", seen by the host's watch of
// the record files) says so in dust beneath it; it can be agreed here only when it is a
// commitment drafted on a card, since a card it made is already in the record.

const EYEBROW = { commitment: "dock.margin.commitment", card: "dock.margin.card", said_in_room: "dock.margin.said_in_room",
  kept: "dock.margin.kept", asked: "dock.margin.asked", proposal: "dock.margin.proposal" };

/**
 * renderMargin(ctx, items, {onAgree(item), onDecline(item)}) -> Element | null
 *   items: [{id, kind, text, ink: said|kept|agreed, state?: agreeing|declined, card?, untrusted?}]
 */
export function renderMargin(ctx, items, { onAgree, onDecline } = {}) {
  const { h } = ctx.card;
  const t = ctx.t;
  const shown = (items || []).filter((x) => x && x.text && x.state !== "declined");
  if (!shown.length) return null;
  const list = h("ul", { class: "dock-margin", "aria-label": t("dock.margin.label") });
  for (const it of shown) {
    const ink = it.ink === "agreed" ? "agreed" : it.ink === "kept" ? "kept" : "said";
    const li = h("li", { class: `dock-mline ink-${ink}`, dataset: { offer: it.id || "" } });
    li.append(h("span", { class: "eyebrow" }, t(EYEBROW[it.kind] || "dock.margin.card"),
      it.untrusted ? " · " + t("dock.from_something_read") : null));
    const words = h(it.card ? "button" : "span", { class: "dock-mwords" + (it.card ? " link-btn" : ""), type: it.card ? "button" : null },
      it.text, ink === "agreed" ? h("span", { class: "dock-check", "aria-label": t("dock.margin.agreed_sr") }, " ✓") : null);
    if (it.card) words.addEventListener("click", () => ctx.openCard(it.card));
    li.append(words);
    if (ink === "kept") li.append(h("span", { class: "dust dock-mnote" }, t("dock.margin.kept_note")));
    else if (it.source === "record" && ink === "said") li.append(h("span", { class: "dust dock-mnote" }, t("dock.margin.in_record_note")));
    if (ink === "said" && it.agreeable !== false && onAgree) {
      const row = h("span", { class: "dock-mactions" });
      const yes = h("button", { class: "link-btn", type: "button", disabled: it.state === "agreeing" }, t("dock.margin.agree"));
      const no = h("button", { class: "link-btn quiet", type: "button", disabled: it.state === "agreeing" }, t("dock.margin.not_this"));
      yes.addEventListener("click", () => onAgree(it));
      no.addEventListener("click", () => onDecline && onDecline(it));
      row.append(yes, no);
      li.append(row);
      if (it.state === "agreeing") li.append(h("span", { class: "dust" }, t("dock.margin.agreeing")));
    }
    list.append(li);
  }
  return list;
}
