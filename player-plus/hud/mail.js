// mail.js: how a Conversation Card says it came by mail, and the receiver's reading of a carried
// field of stake (DESIGN-MAIL §4, rebuilt to DESIGN-THE-BAR). Mail is a sort of threads, never a
// mailbox; there is no sort word, so turn is the one order and threads.js draws every card.
//
// receiverPush(item) reads a carried item's field of stake in either shape serve.py gives:
// `push_recomputed` as engine/mail.recompute_push writes it ({sent, receiver: {blocks, critical,
// by, why_by, cost_if_late, weight, calibration}}) or the flatter form ({blocks, critical,
// calibration}). The receiver's own values win; the sender's are kept beside them.

// only mail is said on the face: the forge, the hook and the relay are the house's plumbing
const ARRIVED = ["mail"];

export function receiverPush(m) {
  const sent = (m && m.push) || null;
  const rc = (m && m.push_recomputed) || null;
  if (!rc) return { sent, rcv: null };
  if (rc.receiver !== undefined) return { sent: rc.sent || sent, rcv: rc.receiver || null };
  return { sent, rcv: rc };
}

/** "by mail · by the forge", from the transports that carried it; nothing when none said. */
export function arrivedWords(ctx, x) {
  if (!Array.isArray(x.arrived) || !x.arrived.length) return null;
  const seen = new Set();
  const words = [];
  for (const k of x.arrived) {
    if (!ARRIVED.includes(k)) continue;
    const w = ctx.t("mail.arrived." + k);
    if (!seen.has(w)) { seen.add(w); words.push(w); }
  }
  return words.join(" · ") || null;
}
