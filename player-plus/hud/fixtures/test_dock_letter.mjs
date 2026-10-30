// test_dock_letter.mjs: the letter (dock.js shapeTurn, workOf). The only words in the conversation
// are the agent's words to the person: a line it says to itself on the way to a tool never reaches
// the page; words arrive by the sentence; nothing set on the page is taken back.
// Run: node hud/fixtures/test_dock_letter.mjs hud/dock.js (test_dock.py runs it when node is here).
import fs from "node:fs";
const src = fs.readFileSync(process.argv[2], "utf8");
const m = src.match(/const ENDS = [\s\S]*?\nexport function workOf[\s\S]*?\n}\n/);
const { shapeTurn, workOf } = new Function(m[0].replace(/export /g, "") + "; return { shapeTurn, workOf };")();
let ok = true;
const eq = (name, got, want) => { const g = JSON.stringify(got), w = JSON.stringify(want); if (g !== w) { ok = false; console.log("FAIL", name, g, "want", w); } };
const text = (s, at = 0) => ({ text: s, chunks: [{ text: s, at }] });
const chunks = (...cs) => ({ text: cs.map((c) => c[0]).join(""), chunks: cs.map(([text, at]) => ({ text, at })) });

// a tool-heavy turn: the chatter before each tool is interim, only the answer is said
const heavy = [text("Running the record command now."), { tool: { kind: "execute" } }, text("Now checking the next file."),
  { tool: { kind: "read" } }, { tool: { kind: "edit" } }, text("Your notes say the hall costs about two hundred.")];
const r1 = shapeTurn(heavy, { done: true, now: 9e9 });
eq("heavy said", r1.said, ["Your notes say the hall costs about two hundred."]);
eq("heavy interim", r1.interim, ["Running the record command now.", "Now checking the next file."]);

// by the sentence: a sentence is set once whole and settled; the half-sentence waits
const live = [chunks(["Good morning. ", 0], ["Two things need", 900])];
const r2 = shapeTurn(live, { now: 1000, hold: 600, pause: 1500 });
eq("by sentence", r2.said, ["Good morning."]);
eq("recheck soon", r2.recheck != null && r2.recheck < 1500, true);
// a pause sets what has come
eq("pause sets", shapeTurn(live, { now: 900 + 1600 }).said, ["Good morning. Two things need"]);
// a sentence followed at once by a tool is never set
const shown = new Set();
const early = [text("Let me look.", 0)];
eq("not yet", shapeTurn(early, { now: 100, shown, key: "k" }).said, []);
eq("then a tool", shapeTurn([...early, { tool: { kind: "read" } }], { now: 400, shown, key: "k" }).said, []);
// words once set before her are never taken back, whatever follows them
const kept = new Set();
const said = [text("Here is the plan.", 0)];
eq("set", shapeTurn(said, { now: 1000, shown: kept, key: "j" }).said, ["Here is the plan."]);
eq("stays when a tool follows", shapeTurn([...said, { tool: { kind: "read" } }, text("Done.")], { done: true, now: 2000, shown: kept, key: "j" }).said, ["Here is the plan.", "Done."]);
// a turn that ends on a tool keeps its last words on the way as its words to her
eq("ends on a tool", shapeTurn([text("I put it in your record."), { tool: { kind: "execute" } }], { done: true, now: 9e9 }).said, ["I put it in your record."]);

// the work line counts by kind, thought left out
eq("work", workOf([{ kind: "read" }, { kind: "read" }, { kind: "execute" }, { kind: "think" }, { kind: "edit" }]), [["read", 2], ["execute", 1], ["edit", 1]]);

console.log(ok ? "letter: all pass" : "letter: FAILED");
process.exit(ok ? 0 : 1);
