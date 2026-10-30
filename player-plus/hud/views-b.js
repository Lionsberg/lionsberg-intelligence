// views-b.js: small helpers shared by three views (map.js, chain.js, board.js).
// Nothing here computes a figure the state lacks; these only read, word and place.
//
// Each view links its own stylesheet once, from here, and this does nothing when the line is
// already present in index.html.

export function ensureCss(href) {
  if (document.querySelector(`link[rel="stylesheet"][href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  const before = document.querySelector('link[href="print.css"]');
  if (before) before.before(link); else document.head.append(link);
}

export function ms(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v.endsWith("ms") ? parseFloat(v) : v.endsWith("s") ? parseFloat(v) * 1000 : parseFloat(v) || 0;
}
export function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

/** The wearer's home holon id (her own person holon), as the shell reads it. */
export function homeId(st) {
  const hs = (st && st.holons) || [];
  const home = hs.find((x) => x.keeper === st.actor && x.kind === "person") || hs[0];
  return home ? home.id : null;
}

/** "as of 9:14", or "last heard on Tuesday" when not today, for one holon. */
export function asOfWords(ctx, holon) {
  const ts = holon && holon.as_of && holon.as_of.ts;
  if (!ts) return ctx.t("app.not_computed");
  return ctx.fmt.freshness(ts) === "older" ? ctx.t("ribbon.fresh.older", { when: ctx.fmt.when(ts) || "" }) : ctx.fmt.asOf(ts);
}

/** Holons whose record could not be read (the server's sources), as {holon, name, readable}. */
export function unreadable(ctx) { return ctx.read.unreadable(ctx.state); }

/** Done-like states: nothing more is asked of anyone. */
export const DONE = new Set(["done", "kept", "released", "declined", "returned"]);

/** A tiny stable hash of a string to [0, 1), for placing a mark where the same id always lands. */
export function unit(id, salt = 0) {
  let x = 2166136261 ^ salt;
  for (const ch of String(id)) { x ^= ch.charCodeAt(0); x = Math.imul(x, 16777619); }
  return ((x >>> 0) % 100000) / 100000;
}

/** The card face's model for a card seen on the Board or the Chain. card.js's default eyebrow
    reason is "Waiting on you", which is true only of the wearer's own cards; for a card another
    holds, the eyebrow keeps its home and kind and drops that reason. */
export function boardModel(ctx, card) {
  const m = ctx.card.cardModel(ctx, { card });
  if (card && card.holder !== ctx.state.actor && m.reason === ctx.t("reason.waiting")) m.reason = null;
  return m;
}
