// test_threads_truth.mjs: one count, one function. The badge on "Threads and Mail" and the view's
// first sentence must say the same number: the badge is badgeCount(ctx) (badges.threads_and_mail,
// else the unread lines from other houses), and the sentence says that number in words beside the
// count of what waits. Fails when they disagree, in every fixture that carries threads.
// Run: node hud/fixtures/test_threads_truth.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HUD = path.join(HERE, "..");
const S = JSON.parse(fs.readFileSync(path.join(HUD, "strings.json"), "utf8"));
const { conversations, topSentence, badgeCount } = await import(path.join(HUD, "threads.js"));

// the shell must read the badge from the same place badgeCount does
const shell = fs.readFileSync(path.join(HUD, "shell.js"), "utf8");
let ok = /b\.threads_and_mail/.test(shell) && /unreadFromOtherHouses/.test(shell);
if (!ok) console.log("FAIL shell.js no longer reads the badge from badges.threads_and_mail / unreadFromOtherHouses");

const t = (k, v = {}) => (k in S ? String(S[k]).replace(/\{(\w+)\}/g, (_, n) => (n in v ? v[n] : `{${n}}`)) : `[${k}]`);
function ctxFor(st) {
  const now = new Date((st.hud && st.hud.now) || st.generated_at || Date.now());
  const fmt = {
    now: () => now,
    date(x) { if (!x) return null; const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(x) ? x + "T12:00:00" : x); return isNaN(d) ? null : d; },
    number(n, lower) { const w = S[lower ? "numbers_lower" : "numbers"] || []; return Number.isInteger(n) && n >= 0 && n < w.length ? w[n] : String(n); },
    daysBetween(a, b) { const A = new Date(a.getFullYear(), a.getMonth(), a.getDate()), B = new Date(b.getFullYear(), b.getMonth(), b.getDate()); return Math.round((B - A) / 86400000); },
    by(x) { const d = fmt.date(x); return d ? "by " + d.toISOString().slice(0, 10) : null; },
    when(x) { return x ? "on " + String(x).slice(0, 10) : null; },
    aboutMinutes(m) { return "about " + m + " minutes"; },
  };
  const read = {
    holon: (s, id) => (s.holons || []).find((h) => h.id === id) || null,
    card: (s, id) => (s.cards || []).find((c) => c.id === id) || null,
    actorKind: (s, a) => (String(a).startsWith("agent:") ? "agent" : "person"),
    who: () => "a member", posture: () => "open", role: () => "member",
  };
  return { state: st, t, fmt, read, filter: null };
}

const word = (n) => [S.numbers_lower[n], S.numbers[n], String(n)];
function agrees(sentence, waiting, badge) {
  const counted = waiting === 0 ? /^Nobody/.test(sentence) : waiting === 1 ? / waits on your word/.test(sentence)
    : word(waiting).some((w) => sentence.startsWith(w + " wait on your word"));
  if (!counted) return "the sentence does not say how many wait (" + waiting + ")";
  const news = sentence.match(/(all of them new|(\w+) of them new|It is new|(\w+) lines? from other houses? (are|is) new|One line from another house is new)/);
  if (badge === 0) return news ? "the sentence says something is new; the badge says none" : null;
  if (!news) return "the badge says " + badge + "; the sentence says nothing of it";
  const said = news[1] === "all of them new" ? waiting : news[1] === "It is new" ? 1 : /^One line/.test(news[1]) ? 1
    : [news[2], news[3]].filter(Boolean).map((w) => Math.max(S.numbers_lower.indexOf(w), S.numbers.indexOf(w), Number(w) || -1))[0];
  return said === badge ? null : `the badge says ${badge}; the sentence says ${said}`;
}

let checked = 0;
for (const f of fs.readdirSync(HERE).filter((x) => x.endsWith(".json"))) {
  let st; try { st = JSON.parse(fs.readFileSync(path.join(HERE, f), "utf8")); } catch { continue; }
  if (!st || !Array.isArray(st.threads)) continue;
  const ctx = ctxFor(st);
  const { mine, theirs } = conversations(ctx);
  const badge = badgeCount(ctx);
  const s = topSentence(ctx, mine, theirs, badge);
  const why = agrees(s, mine.length, badge);
  checked++;
  if (why) { ok = false; console.log(`FAIL ${f}: ${why}\n  "${s}"`); } else console.log(`ok   ${f}: badge ${badge}, waiting ${mine.length}: "${s}"`);
  // the test can fail: the first build's sentence, which never said the badge, must be caught
  if (badge > 0 && !agrees(topSentence(ctx, mine, theirs, 0), mine.length, badge)) { ok = false; console.log(`FAIL ${f}: the test did not catch a sentence silent on the badge`); }
}
// a made disagreement must be caught too
const fake = { ...JSON.parse(fs.readFileSync(path.join(HERE, "room-work.json"), "utf8")) };
const fc = ctxFor(fake), fm = conversations(fc);
if (!agrees(topSentence(fc, fm.mine, fm.theirs, 2), fm.mine.length, 3)) { ok = false; console.log("FAIL the test did not catch badge 3 said as two"); }
console.log(ok ? `threads truth: all pass (${checked} fixtures)` : "threads truth: failures");
process.exit(ok ? 0 : 1);
