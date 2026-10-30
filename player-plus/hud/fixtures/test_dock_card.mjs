// test_dock_card.mjs: the ask card's face is in words (dock-card.js). A step's raw command and the
// harness's step name ("Newest session logs by mtime") sit behind one fold, "The exact step", never
// on the face; a step that only looks says so in words; a mark the agent proposed reads "Mark
// Saturday morning?", and its Yes writes the Deal's own act, then answers the ask.
// Run: node hud/fixtures/test_dock_card.mjs hud/dock-card.js hud/strings.json (test_dock.py runs it).
import fs from "node:fs";
const src = fs.readFileSync(process.argv[2], "utf8").replace(/import \{ actFor \} from "\.\/deal\.js";/, "const actFor = globalThis.__actFor;");
const strings = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
globalThis.__actFor = (dc, label) => ({ type: "decide", body: { text: label }, links: { answers: [dc.id] } });
class El {
  constructor(tag) { this.tag = tag; this.kids = []; this.attrs = {}; this.textContent = ""; this.listeners = {}; }
  append(...k) { for (const x of k) if (x != null) this.kids.push(x); }
  setAttribute(k, v) { this.attrs[k] = v; }
  addEventListener(e, f) { this.listeners[e] = f; }
  set className(v) { this.attrs.class = v; }
}
globalThis.document = { createElement: (t) => new El(t) };
const h = (tag, attrs, ...kids) => { const e = new El(tag); Object.assign(e.attrs, attrs || {}); for (const k of kids.flat()) if (k != null) e.kids.push(k); return e; };
const t = (k, v = {}) => { let s = strings[k]; if (typeof s !== "string") return "[" + k + "]"; for (const [a, b] of Object.entries(v)) s = s.replaceAll("{" + a + "}", b); return s; };
const text = (e, skipFold) => typeof e === "string" ? e : (skipFold && e.tag === "details") ? "" : [e.textContent, ...e.kids.map((k) => text(k, skipFold))].join(" ");
const find = (e, pred) => { if (typeof e === "string") return null; if (pred(e)) return e; for (const k of e.kids) { const f = find(k, pred); if (f) return f; } return null; };
const { renderAsk } = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));

let ok = true;
const check = (name, cond, got) => { if (!cond) { ok = false; console.log("FAIL", name, got === undefined ? "" : JSON.stringify(got)); } };
const ctx = (extra = {}) => ({ card: { h }, t, ...extra });

// a step that only looks, with a step name and a raw command: the face is words only
const findAsk = { id: "a-1", kind: "execute", title: "find bg -name '*.md' -mtime -2 -exec stat -f %m {} +",
  input: JSON.stringify({ command: "find bg -name '*.md' -mtime -2", description: "Newest session logs by mtime" }),
  said: "", leaves: false, options: [{ id: "once", kind: "allow_once" }, { id: "no", kind: "reject_once" }] };
let card = renderAsk(ctx(), findAsk, { onAnswer: async () => ({ ok: true }) });
const face = text(card, true);
check("a look is asked in words", face.includes("May I look at this house's files to answer?"), face);
for (const w of ["find", "mtime", "Newest session logs", "-name", "stat"]) check("no raw step on the face: " + w, !face.includes(w), face);
const fold = find(card, (e) => e.tag === "details");
check("one fold", !!fold);
check("the fold is The exact step", fold && text(fold).includes("The exact step"), fold && text(fold));
check("the step name sits in the fold", fold && text(fold).includes("Newest session logs by mtime"));
check("the command sits in the fold", fold && text(fold).includes("find bg -name"));

// a step that changes something: a plain default
const runAsk = { ...findAsk, id: "a-2", title: "npm install left-pad", input: JSON.stringify({ command: "npm install left-pad" }) };
card = renderAsk(ctx(), runAsk, { onAnswer: async () => ({ ok: true }) });
check("a step is asked in words", text(card, true).includes("May I run a step on this computer?"), text(card, true));
check("no command on the face", !text(card, true).includes("npm"), text(card, true));

// the agent's own reason stays on the face
card = renderAsk(ctx(), { ...runAsk, why: "To set up the page you asked for." }, { onAnswer: async () => ({ ok: true }) });
check("its reason on the face", text(card, true).includes("To set up the page you asked for."));

// a mark the agent proposed: Mark Saturday morning? Yes writes the Deal's act, then answers
const dc = { id: "card-meet", kind: "decide", section: "decision", holon: "cell-two", question: "Which day should Cell Two meet this month?",
  options: ["Thursday evening", "Saturday morning", "Ask the cell"] };
const actAsk = { id: "a-3", kind: "act", card_id: "card-meet", option_index: 1, option: "Saturday morning", question: dc.question,
  options: [{ id: "yes", kind: "allow_once" }, { id: "not_that", kind: "reject_once" }] };
const acts = [], answers = [];
const live = ctx({ state: { deal: { cards: [dc] } }, act: (...a) => { acts.push(a); return { done: Promise.resolve({ status: "written" }) }; } });
card = renderAsk(live, actAsk, { onAnswer: async (x) => { answers.push(x); return { ok: true }; } });
check("Mark {option}?", text(card).includes("Mark Saturday morning?"), text(card));
check("over the card's own question", text(card).includes(dc.question));
const buttons = []; (function walk(e) { if (typeof e === "string") return; if (e.tag === "button") buttons.push(e); e.kids.forEach(walk); })(card);
check("two answers: Not that, Yes", JSON.stringify(buttons.map((b) => text(b).trim())) === JSON.stringify(["Not that", "Yes"]), buttons.map((b) => text(b).trim()));
await buttons[1].listeners.click();
check("Yes writes the Deal's own act", acts.length === 1 && acts[0][0] === "decide" && acts[0][1].text === "Saturday morning"
  && acts[0][2].answers[0] === "card-meet" && acts[0][3] === "cell-two" && acts[0][4].confirmed === true, acts);
check("then answers the ask", JSON.stringify(answers) === JSON.stringify(["yes"]), answers);

// a card the Deal no longer holds marks nothing
const acts2 = [], answers2 = [];
card = renderAsk(ctx({ state: { deal: { cards: [] } }, act: (...a) => { acts2.push(a); } }), actAsk, { onAnswer: async (x) => { answers2.push(x); return { ok: true }; } });
const b2 = []; (function walk(e) { if (typeof e === "string") return; if (e.tag === "button") b2.push(e); e.kids.forEach(walk); })(card);
await b2[1].listeners.click();
check("a gone card writes nothing", acts2.length === 0 && answers2.length === 0, { acts2, answers2 });
check("and says so", text(card).includes(strings["dock.ask_act_gone"]));

console.log(ok ? "dock card: all pass" : "dock card: FAILED");
process.exit(ok ? 0 : 1);
