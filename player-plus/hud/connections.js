// connections.js: the Connections view (STATE.md `connections`; the M2 brief). Plain first, the board on
// a pull. Every figure is the engine's (connections.py); this view places and words them and computes
// nothing the state lacks. It only reads: nothing here writes, sends or sounds, and every act goes
// through the Deal as it always has.
//
//   the summary     every connection live or not, and for each that is not, which one and why; everyone
//                   you exchanged commitments with keeping theirs to you or not, and you toward them
//   the key         what each color means, in words (and the amber of the small mark)
//   plain lines     one per holon, second person, under 25 words, worded here by plain.py's laws (the
//                   state carries `connections`, not plain.three): the holon's name (never an id; "a
//                   group" when none; cut by words when the line would run long), their Condition as a
//                   color with its meaning, the pulse in two short clauses, and the next step, said as
//                   what to tell your agent
//   in play         beside each holon a small mark with two ages in words: heard from them (the forge's
//                   answer, else their newest line held) and heard by them (their newest word that a line
//                   of ours arrived, `heard_by_at`). Each dot beats only while its age is under the
//                   Agreement's cadence (CSS only; no timers); a dead ear turns the mark amber and never
//                   touches the pulse
//   More            the whole table. A tap on a color lists its checks, each as one plain line of what
//                   it found, its reading and basis folded under "How this was read"; the same tap closes
//                   it. Every act says what it does on hover and in a "What these mean" fold.
//
// Every word comes from strings.json (keys `conn.*`); none is written here. A line whose words do not
// resolve (a time not read, a figure missing) is not drawn. Ids and actor tokens in the engine's own
// sentences are said as names or by their kind before they are shown.

import { h } from "./card.js";
import { ensureCss } from "./views-b.js";

const VIEW = "connections";
const DIRS = ["us_to_them", "them_to_us"];               // the pulse's two directed columns (connections.py)
// The words' keys for each column.
const K = {
  us_to_them: { fam: "conn.us.", unread: "conn.us.unread", green: "conn.us.green", other: "conn.us.other",
    short: "conn.short.us", tiny: "conn.tiny.us", act: "conn.do.us.", chip: "conn.chip.us", head: "conn.checks.head_us",
    ok: "conn.found.us.ok.", moved: "conn.found.us.moved." },
  them_to_us: { fam: "conn.them.", unread: "conn.them.unread", green: "conn.them.green", other: "conn.them.other",
    short: "conn.short.them", tiny: "conn.tiny.them", act: "conn.do.them.", chip: "conn.chip.them", head: "conn.checks.head_them",
    ok: "conn.found.them.ok.", moved: "conn.found.them.moved." },
};
const COLS = ["conn.col.holon", "conn.col.condition", "conn.col.us", "conn.col.them", "conn.col.ear", "conn.col.with",
  "conn.col.agreement", "conn.col.since"];
const LEVELS = ["inside", "yellow", "orange", "red"];    // connections.LEVELS, worst last
const LEVEL_COLOR = { inside: "green" };                 // connections.LEVEL_COLOR: every other level is its own color
const KEY = ["green", "yellow", "orange", "red", "grey"];   // the color key, in the scale's order (connections.COLORS, then grey)
const GREEN = "green", GREY = "grey";
const LIVE = ["green", "yellow"];                        // connections._summary: live is green or yellow, heard on time
const EAR_OK = "ok", EAR_NEVER = "never";                // connections.HEARD
const AG_NONE = "none";                                  // connections._row: no Agreement names both
const RECEIPTS = "receipts";                             // the check whose rows are our lines waiting on their word
const SHORT = "short", TINY = "tiny";                    // the plain line's shorter forms
const MAX_WORDS = 24;                                    // plain.MAX_WORDS: a plain line is under 25 words
const MAX_NAME_CHARS = 60;                               // a name longer than this is cut with an ellipsis (this view's own bound)
const SEP = "\u0000";
const MINUTE_S = 60, HOUR_S = 3600, DAY_S = 86400, SEASON_S = 7776000;   // a season is 90 days (subscriptions.words)
const HEX = /\b(?:[0-9a-fA-F]{12,}|(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{8,11})\b/g;   // an id or its short form (plain._HEX)
const ACTOR = /\b(?:person|agent):[A-Za-z0-9_.@+-]*[A-Za-z0-9_@+-]/g;           // an actor token (plain._ACTOR)
const AGENT = /^agent:/;
const AN_ID = /^(?:[0-9a-fA-F]{8,}|(?:person|agent):.*)$/;
const PLACEHOLDER = /\{\w+\}/;
const DAY_ONLY = /^(\d{4})-(\d{2})-(\d{2})/;

const list = (v) => (Array.isArray(v) ? v : []);
const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : {});
const str = (v) => (typeof v === "string" ? v.normalize() : "");
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const rank = (lv) => LEVELS.indexOf(lv);
const colorOfLevel = (lv) => LEVEL_COLOR[lv] || lv;
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const wordCount = (s) => String(s).split(/\s+/).filter(Boolean).length;

export default function createConnections() {
  let el, ctx, root, more = false, openChecks = null;
  ensureCss(VIEW + ".css");
  const t = (k, v) => ctx.t(k, v);
  const has = (k) => { const s = t(k); return typeof s === "string" && !s.startsWith("["); };
  const firstKey = (keys) => keys.find(has) || null;
  const word = (prefix, v) => (has(prefix + v) ? t(prefix + v) : String(v));
  const numWord = (n) => (has("conn.num." + n) ? t("conn.num." + n) : String(n));
  /** The words of a key with every placeholder filled, or null: a line that cannot be said is not drawn. */
  const say = (k, v) => {
    if (v && Object.values(v).some((x) => x == null || x === "")) return null;
    const s = t(k, v);
    return typeof s === "string" && !s.startsWith("[") && !PLACEHOLDER.test(s) ? s : null;
  };
  const line = (cls, k, v) => { const s = say(k, v); return s ? h("p", cls ? { class: cls } : null, s) : null; };
  const colorKnown = (c) => KEY.includes(c);
  const cw = (c) => { c = colorKnown(c) ? c : GREY; return t("conn.cw", { color: t("conn.color_name." + c), meaning: t("conn.color." + c) }); };
  const cwTiny = (c) => { c = colorKnown(c) ? c : GREY; return t("conn.cw", { color: t("conn.color_name." + c), meaning: t("conn.color_tiny." + c) }); };
  const colorClass = (c) => "is-" + (colorKnown(c) ? c : GREY);
  const swatch = () => h("span", { class: "conn-swatch", "aria-hidden": "true" });

  // ---------------------------------------------------------------- words for times

  function ago(sec) {
    if (sec == null) return null;
    if (sec < MINUTE_S) return t("conn.ago.now");
    if (sec < HOUR_S) { const m = Math.floor(sec / MINUTE_S); return m === 1 ? t("conn.ago.minute") : t("conn.ago.minutes", { n: m }); }
    if (sec < DAY_S) { const x = Math.floor(sec / HOUR_S); return x === 1 ? t("conn.ago.hour") : t("conn.ago.hours", { n: x }); }
    if (sec < 2 * DAY_S) return t("conn.ago.yesterday");
    return t("conn.ago.days", { n: Math.round(sec / DAY_S) });      // whole days, to the nearest
  }
  const ageOf = (ts, clock) => { const x = Date.parse(str(ts)); return Number.isFinite(x) && clock != null ? Math.max(0, (clock - x) / 1000) : null; };
  function dateWords(v) {
    const m = DAY_ONLY.exec(str(v));
    if (!m) return null;
    const mo = Number(m[2]);
    return has("conn.month." + mo) ? t("conn.date", { day: Number(m[3]), month: t("conn.month." + mo), year: m[1] }) : null;
  }
  /** Seconds as a person says a span; null when there is no span to say. */
  function cadence(s) {
    s = num(s);
    if (s == null || s <= 0 || !Number.isInteger(s)) return null;
    if (s === SEASON_S) return t("conn.cadence.season");
    if (s % DAY_S === 0) return s === DAY_S ? t("conn.cadence.day") : t("conn.cadence.days", { n: s / DAY_S });
    if (s % HOUR_S === 0) return s === HOUR_S ? t("conn.cadence.hour") : t("conn.cadence.hours", { n: s / HOUR_S });
    if (s % MINUTE_S === 0) return s === MINUTE_S ? t("conn.cadence.minute") : t("conn.cadence.minutes", { n: s / MINUTE_S });
    return s === 1 ? t("conn.cadence.second") : t("conn.cadence.seconds", { n: s });
  }

  // ---------------------------------------------------------------- names, never ids

  function nameOf(st, id, given) {
    const g = str(given);
    let n = g && !AN_ID.test(g) ? g : "";
    if (!n) {
      const hx = list(st.holons).map(obj).find((x) => str(x.id) && str(x.id) === str(id));
      n = hx ? str(hx.name) : "";
      if (!n && str(id) && ctx.read && ctx.read.holonName) n = str(ctx.read.holonName(st, id));
    }
    if (!n || AN_ID.test(n)) return t("conn.a_group");
    return n.length > MAX_NAME_CHARS ? n.slice(0, MAX_NAME_CHARS).trimEnd() + "…" : n;
  }
  /** Every id this connection's sentences may carry, with the word it is said by: holons by their names,
      the Agreement, commitments, asks and sightings by their kind. */
  function known(st, rows) {
    const home = str(obj(st.connections).home);
    const out = home ? [{ id: home, name: t("conn.your_home") }] : [];
    for (const x of list(st.holons).map(obj)) if (str(x.id) && str(x.id) !== home) out.push({ id: str(x.id), name: nameOf(st, x.id, x.name) });
    for (const r of rows) {
      if (str(r.holon)) out.push({ id: str(r.holon), name: nameOf(st, r.holon, r.name) });
      for (const a of [obj(r.agreement).id, obj(obj(r.pulse).agreement).id]) if (str(a)) out.push({ id: str(a), name: t("conn.id.agreement") });
      for (const d of DIRS) for (const c of list(obj(obj(r.pulse)[d]).checks).map(obj)) for (const x of list(c.rows)) {
        if (typeof x === "string") out.push({ id: x, name: t("conn.id.line") });
        const o = obj(x);
        if (str(o.commitment)) out.push({ id: str(o.commitment), name: t("conn.id.commitment") });
        if (str(o.ask)) out.push({ id: str(o.ask), name: t("conn.id.ask") });
        if (str(o.sighting)) out.push({ id: str(o.sighting), name: t("conn.id.sighting") });
      }
    }
    for (const a of list(obj(st.agreements).rows).map(obj)) if (str(a.id)) out.push({ id: str(a.id), name: t("conn.id.agreement") });
    return out.map((x) => ({ id: x.id.toLowerCase(), name: x.name }));
  }
  /** An engine sentence with every actor token and id said in words, and the kit's terms said plainly. */
  function scrub(text, ids) {
    let s = str(text)
      .replace(ACTOR, (m) => t(AGENT.test(m) ? "conn.an_agent" : "conn.a_person"))
      .replace(HEX, (m) => { const lo = m.toLowerCase(); const x = ids.find((k) => k.id.startsWith(lo)); return x ? x.name : t("conn.id.line"); });
    for (const pair of list(t("conn.plain_words"))) if (Array.isArray(pair) && typeof pair[0] === "string" && typeof pair[1] === "string") s = s.split(pair[0]).join(pair[1]);
    return s;
  }

  // ---------------------------------------------------------------- a connection, in words

  function conditionWords(cond, tiny) {
    if (cond.stale === true) return t("conn.cw", { color: t("conn.color_name." + GREY), meaning: tiny ? t("conn.cond.stale_tiny") : t("conn.cond.stale") });
    const c = str(cond.color);
    if (c && c !== GREY && colorKnown(c)) return tiny ? cwTiny(c) : t("conn.cond.said", { cw: cw(c) });
    return tiny ? cwTiny(GREY) : cw(GREY);
  }
  /** The worst check in a column (the first of the engine's order on a tie), or null when all are inside. */
  function worstOf(col) {
    let best = null;
    list(obj(col).checks).map(obj).forEach((c) => { const r = rank(str(c.level)); if (r > 0 && (!best || r > best.r)) best = { r, c }; });
    return best;
  }
  function countOf(c) {
    const rows = list(c.rows).map(obj);
    const past = rows.filter((r) => r.past_usual === true).length;
    const moved = rows.filter((r) => str(r.level) && str(r.level) !== LEVELS[0]).length;
    return past || moved || rows.length || 1;
  }
  const colOf = (row, d) => obj(row.pulse)[d];
  const colRead = (col) => col && typeof col === "object" && !Array.isArray(col) && colorKnown(str(col.color));
  function clause(d, col, form) {
    const k = K[d];
    if (!colRead(col)) return t(k.unread);
    if (form === SHORT) return t(k.short, { cw: cw(str(col.color)) });
    if (form === TINY) return t(k.tiny, { cw: cwTiny(str(col.color)) });
    const w = worstOf(col);
    if (!w) return t(k.green);
    const base = k.fam + str(w.c.check), lv = str(w.c.level), n = countOf(w.c);
    const key = firstKey((n > 1 ? [base + "." + lv + "_n", base + "_n"] : []).concat([base + "." + lv, base])) || k.other;
    return t(key, { n: numWord(n) });
  }
  /** One plain line under 25 words: the whole form, a shorter, the shortest, then the name cut by words. */
  function sentence(row, st) {
    const make = (name, form) => t("conn.line", { name, condition: conditionWords(obj(row.condition), form === TINY),
      us: cap(clause(DIRS[0], colOf(row, DIRS[0]), form)), them: clause(DIRS[1], colOf(row, DIRS[1]), form) });
    const name = nameOf(st, row.holon, row.name);
    for (const form of [null, SHORT, TINY]) { const s = make(name, form); if (wordCount(s) <= MAX_WORDS) return s; }
    const ws = name.split(/\s+/).filter(Boolean);
    for (let n = ws.length - 1; n >= 1; n--) {
      const s = make(ws.slice(0, n).join(" ").replace(/[,;:.]+$/, "") + "…", TINY);
      if (wordCount(s) <= MAX_WORDS) return s;
    }
    return make((ws[0] || t("conn.a_group")) + "…", TINY);
  }
  /** The next step, said as what to tell your agent; null when nothing waits. */
  function nextStep(row) {
    const p = obj(row.pulse);
    if (!DIRS.some((d) => colRead(p[d]))) return t("conn.do.unread");
    let pick = null;
    for (const d of DIRS) { const w = worstOf(p[d]); if (w && (!pick || w.r > pick.w.r)) pick = { d, w }; }
    if (pick) { const k = K[pick.d].act + str(pick.w.c.check); return has(k) ? t(k) : t("conn.do.other"); }
    const cond = obj(row.condition), c = str(cond.color);
    if (cond.stale !== true && colorKnown(c) && c !== GREEN && c !== GREY) return t("conn.do.condition");
    if (str(obj(row.ear).heard) !== EAR_OK) return t("conn.do.ear");
    return null;
  }

  /** The in-play mark: heard from them, heard by them, each its age in words; amber when our ear is dead. */
  function inPlay(row, st, clock, name) {
    const ear = obj(row.ear), cad = num(obj(row.pulse).cadence_s);
    const hx = list(st.holons).map(obj).find((x) => str(x.id) && str(x.id) === str(row.holon));
    const newest = str(obj(obj(obj(st.connections).as_of).per_holon)[str(row.holon)]) || (hx ? str(obj(hx.as_of).ts) : "");
    const pulled = str(ear.pulled_at) && Number.isFinite(Date.parse(str(ear.pulled_at)));
    const ages = [pulled ? (num(ear.age_s) != null ? ear.age_s : ageOf(ear.pulled_at, clock)) : null,
      newest ? ageOf(newest, clock) : null].filter((x) => x != null);
    const heardAge = ages.length ? Math.min(...ages) : null;
    const heard = heardAge != null ? say("conn.play.heard", { when: ago(heardAge) })
      : newest || pulled ? t("conn.play.heard_noclock") : t("conn.play.heard_never");
    const deaf = str(ear.heard) !== EAR_OK;
    const back = list(obj(colOf(row, DIRS[1])).checks).map(obj).find((c) => str(c.check) === RECEIPTS);
    const waits = list(back && back.rows).map(obj);
    const sent = num(row.sent), lastAt = str(row.heard_by_at), lastAge = lastAt ? ageOf(lastAt, clock) : null;
    let by;
    if (lastAt) by = lastAge != null ? say("conn.play.by_at", { when: ago(lastAge) }) : t("conn.play.by_at_noclock");
    else if (waits.length || (sent != null && sent > 0)) by = t("conn.play.by_never");
    else if (sent === 0) by = t("conn.play.by_none");               // only when the record proves nothing of ours was sent
    else by = t("conn.play.by_unread");
    const oldest = waits.length ? ago(Math.max(...waits.map((r) => num(r.age_hours) || 0)) * HOUR_S) : null;
    const beat = (age) => age != null && cad != null && cad > 0 && age < cad;
    return h("p", { class: "conn-play", role: "group", "aria-label": t("conn.play.label", { name }) },
      h("span", { class: "conn-mark" + (deaf ? " is-deaf" : ""), "aria-hidden": "true" },
        h("span", { class: "conn-dot" + (beat(heardAge) ? " is-beating" : "") }),
        h("span", { class: "conn-dot" + (beat(lastAge) ? " is-beating" : "") })),
      h("span", { class: "conn-heard" }, heard),
      deaf ? h("span", { class: "conn-ear" }, t("conn.play.ear", { ear: cap(word("conn.ear.", str(ear.heard) || EAR_NEVER)) })) : null,
      by ? h("span", { class: "conn-heard-by" }, say("conn.play.heard_by", { what: by })) : null,
      waits.length ? h("span", { class: "conn-waiting" }, cap(say("conn.play.waiting", { n: numWord(waits.length), when: oldest }))) : null);
  }
  const chips = (row) => h("p", { class: "conn-chips" }, ...DIRS.map((d) => {
    const col = colOf(row, d), c = colRead(col) ? str(col.color) : null;
    return h("span", { class: "conn-chip " + colorClass(c) }, swatch(), t(K[d].chip, { cw: c ? cw(c) : t("conn.chip.unread") }));
  }));

  // ---------------------------------------------------------------- the summary and the key

  function notLive(conn, rows) {
    const s = obj(conn.summary);
    if (Array.isArray(s.not_live)) return s.not_live.map(str).filter(Boolean);
    return rows.filter((r) => !LIVE.includes(str(obj(r.pulse).color)) || str(obj(r.ear).heard) !== EAR_OK).map((r) => str(r.holon));
  }
  /** Why one connection is not live, in words: what is between you, and our ear. */
  function whyNotLive(row) {
    if (!row) return t("conn.sum.why_unknown");
    const parts = [], c = str(obj(row.pulse).color), heard = str(obj(row.ear).heard) || EAR_NEVER;
    if (!colorKnown(c)) parts.push(t("conn.sum.why_unread"));
    else if (!LIVE.includes(c)) parts.push(t("conn.sum.why_pulse", { cw: cw(c) }));
    if (heard !== EAR_OK) parts.push(has("conn.sum.why_ear." + heard) ? t("conn.sum.why_ear." + heard) : t("conn.sum.why_ear.never"));
    return parts.length ? parts.join(t("conn.and")) : t("conn.sum.why_unknown");
  }
  function summary(conn, st, rows) {
    const s = obj(conn.summary);
    const rowOf = (id) => rows.find((x) => str(x.holon) === str(id));
    const names = (ids) => list(ids).map((id) => { const r = rowOf(id); return nameOf(st, id, r && r.name); }).join(t("conn.sep"));
    const off = notLive(conn, rows);
    const parts = off.length ? off.map((id) => t("conn.sum.not_live", { name: nameOf(st, id, (rowOf(id) || {}).name), why: whyNotLive(rowOf(id)) }))
      .concat([t("conn.sum.live_means")]) : [t("conn.sum.live")];
    const exchanged = rows.some((r) => num(obj(r.with_us).commitments_given) || num(obj(r.with_us).commitments_received));
    if (!exchanged) parts.push(t("conn.sum.no_commitments"));
    else {
      const theirs = list(s.not_yellow_or_better), ours = list(s.ours_not_yellow_or_better);
      parts.push(theirs.length ? t("conn.sum.theirs_not", { names: names(theirs) }) : t("conn.sum.theirs_ok"));
      parts.push(ours.length ? t("conn.sum.ours_not", { names: names(ours) }) : t("conn.sum.ours_ok"));
    }
    return h("p", { class: "conn-summary" }, parts.join(" "));
  }
  const theKey = () => h("div", { class: "conn-key", role: "note", "aria-label": t("conn.key.title") },
    h("p", { class: "eyebrow" }, t("conn.key.title")),
    h("ul", null, ...KEY.map((c) => h("li", { class: "conn-chip " + colorClass(c) }, swatch(), cw(c))),
      h("li", { class: "conn-chip is-amber" }, h("span", { class: "conn-key-mark", "aria-hidden": "true" }),
        t("conn.cw", { color: t("conn.color_name.amber"), meaning: t("conn.key.amber") }))));
  /** What each act here does (the acts law): the reader's own acts only, both of them reading acts. */
  const theActs = () => h("details", { class: "conn-acts" }, h("summary", null, t("conn.acts.title")),
    h("ul", null, h("li", null, t("conn.act.more")), h("li", null, t("conn.act.color"))));

  // ---------------------------------------------------------------- the board, on a pull

  function agreementCadence(st, row) {
    const id = str(obj(row.agreement).id);
    const ag = id ? list(obj(st.agreements).rows).map(obj).find((r) => str(r.id) === id) : null;
    const cad = obj(ag && ag.cadence);
    const parts = Object.keys(cad).sort().map((sig) => say("conn.cadence.of", { signal: sig === "*" ? t("conn.every_signal") : word("conn.signal.", sig), cadence: cadence(cad[sig]) })).filter(Boolean);
    return parts.length ? parts.join(t("conn.sep")) : null;
  }
  function checksOf(row, d, st, ids) {
    const col = obj(colOf(row, d)), name = nameOf(st, row.holon, row.name);
    const head = t(K[d].head, { name });
    return h("div", { class: "conn-checks", role: "region", "aria-label": head },
      h("p", { class: "conn-checks-head" }, head),
      h("ul", null, ...list(col.checks).filter((c) => c && typeof c === "object" && !Array.isArray(c)).map((c) => {
        const check = str(c.check), lv = str(c.level), moved = rank(lv) > 0, color = colorOfLevel(lv);
        const fk = (moved ? K[d].moved : K[d].ok) + check;
        const found = has(fk) ? say(fk, { n: numWord(list(c.rows).length || 1) }) : say("conn.found.other", { check: word("conn.check.", check), cw: cw(color) });
        const act = moved && has(K[d].act + check) ? say("conn.do_line", { do: t(K[d].act + check) }) : null;
        const how = [str(c.reading) ? line("dust", "conn.checks.reading", { reading: scrub(c.reading, ids) }) : null,
          str(c.basis) ? line("dust", "conn.checks.basis", { basis: scrub(c.basis, ids) }) : null].filter(Boolean);
        return h("li", { class: "conn-check" },
          h("p", { class: "conn-check-head" }, h("span", null, word("conn.check.", check)),
            h("span", { class: "conn-chip " + colorClass(color) }, swatch(), cw(color))),
          found ? h("p", { class: "conn-found" }, found) : null,
          act ? h("p", { class: "conn-do" }, act) : null,
          how.length ? h("details", { class: "conn-how" }, h("summary", null, t("conn.checks.how")), ...how) : null);
      })));
  }
  function board(st, rows, clock, ids) {
    const head = h("tr", null, ...COLS.map((k) => h("th", { scope: "col" }, t(k))));
    let listed = null;
    const body = rows.map((row) => {
      const name = nameOf(st, row.holon, row.name), cond = obj(row.condition), ear = obj(row.ear), w = obj(row.with_us), ag = obj(row.agreement);
      const color = (d) => {
        const col = colOf(row, d);
        if (!colRead(col)) return h("td", null, t("conn.chip.unread"));
        const id = str(row.holon) + SEP + d, on = openChecks === id, c = str(col.color);
        if (on) listed = checksOf(row, d, st, ids);
        return h("td", null, h("button", { class: "conn-color conn-chip " + colorClass(c), "aria-pressed": String(on),
          title: t("conn.act.color_means"), onclick: () => { openChecks = on ? null : id; draw(); } }, swatch(), cw(c)),
          h("p", { class: "dust" }, clause(d, col, null)));
      };
      const agCad = str(ag.id) ? agreementCadence(st, row) || (str(ag.cadence) ? scrub(ag.cadence, ids) : null) : null;
      const until = dateWords(cond.until);
      return h("tr", null,
        h("th", { scope: "row", class: "conn-name" }, name),
        h("td", null, h("p", null, conditionWords(cond, false)),
          str(cond.why) ? line("dust", "conn.cond.why", { why: scrub(cond.why, ids) }) : null,
          str(cond.said) ? line("dust", "conn.cond.said_when", { when: ago(ageOf(cond.said, clock)) }) : null,
          str(cond.said) ? (until ? line("dust", "conn.cond.until", { date: until }) : line("dust", "conn.cond.no_until")) : null),
        color(DIRS[0]), color(DIRS[1]),
        h("td", null, h("p", null, word("conn.ear.", str(ear.heard) || EAR_NEVER)),
          str(ear.pulled_at) ? line("dust", "conn.ear.fetched", { when: ago(ageOf(ear.pulled_at, clock)) }) : null,
          line("dust", "conn.ear.every", { cadence: cadence(ear.cadence_s) })),
        h("td", null,
          line(null, "conn.with.commitments", { given: num(w.commitments_given), received: num(w.commitments_received) }),
          line(null, "conn.with.asks", { out: num(w.asks_waiting_on_them), in: num(w.asks_waiting_on_us) }),
          line("dust", "conn.with.crossed", { window: cadence(w.window_s), n: num(w.lines_crossed) })),
        h("td", null, h("p", null, word("conn.ag.", str(ag.state) || AG_NONE)),
          agCad ? line("dust", "conn.ag.cadence", { cadence: agCad }) : null,
          line("dust", "conn.ag.until", { date: dateWords(ag.until) })),
        h("td", { class: "conn-since" }, (str(row.since) && say("conn.since", { when: ago(ageOf(row.since, clock)) })) || t("conn.since_none")));
    });
    return h("section", { class: "conn-board", "aria-label": t("conn.board.title") },
      h("h3", { class: "eyebrow" }, t("conn.board.title")),
      h("p", { class: "dust" }, t("conn.board.tap")),
      h("div", { class: "conn-scroll" }, h("table", { class: "conn-table" }, h("thead", null, head), h("tbody", null, ...body))),
      listed);
  }

  // ---------------------------------------------------------------- the whole

  function draw() {
    root.textContent = "";
    const st = ctx.state || {};
    const conn = obj(st.connections);
    const read = Array.isArray(conn.rows);                // a section with no list of rows is not read, never guessed
    const rows = list(conn.rows).filter((r) => r && typeof r === "object" && !Array.isArray(r));
    // the clock the connections were read at: the section's own as_of (kept as `own` under the state's stamp)
    const clock = (() => { const a = conn.as_of, x = Date.parse(str(obj(a).own) || str(a) || str(obj(a).clock) || str(st.generated_at)); return Number.isFinite(x) ? x : null; })();
    if (ctx.slot === "aside" || ctx.density === "small") {
      root.append(h("p", null, read ? t("conn.slice", { n: rows.length, live: rows.length - notLive(conn, rows).length }) : t("conn.unread")),
        h("a", { href: "#/" + VIEW }, t("conn.see_all")));
      return;
    }
    if (!read) { root.append(h("p", { class: "conn-empty" }, t("conn.unread"))); return; }
    if (!rows.length) { root.append(h("p", { class: "conn-empty" }, t("conn.empty"))); return; }
    if (openChecks && !rows.some((r) => DIRS.some((d) => openChecks === str(r.holon) + SEP + d && colRead(colOf(r, d))))) openChecks = null;
    const ids = known(st, rows);
    root.append(...[summary(conn, st, rows), theKey(),
      h("ul", { class: "conn-list" }, ...rows.map((row) => {
        const name = nameOf(st, row.holon, row.name), step = nextStep(row);
        return h("li", { class: "conn-holon" },
          h("p", { class: "conn-plain" }, sentence(row, st)),
          h("p", { class: "conn-do" }, step ? t("conn.do_line", { do: step }) : t("conn.do_none")),
          inPlay(row, st, clock, name), chips(row));
      })),
      h("p", { class: "conn-more-line" }, h("button", { class: "conn-more", "aria-expanded": String(more), title: t("conn.act.more_means"),
        onclick: () => { more = !more; if (!more) openChecks = null; draw(); } }, more ? t("conn.more_open") : t("conn.more")),
        more ? null : h("span", { class: "dust" }, t("conn.more_hint"))),
      theActs(),
      more ? board(st, rows, clock, ids) : null].filter(Boolean));
  }

  return {
    mount(container, c) { el = container; ctx = c; root = h("div", { class: "conn" }); el.append(root); draw(); },
    update(c) { ctx = c; draw(); },
    unmount() { more = false; openChecks = null; },
  };
}
