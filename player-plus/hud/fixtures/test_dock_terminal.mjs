// test_dock_terminal.mjs: the command line's small terminal (dock.js makeTerminal) keeps the spaces
// a harness draws by moving the cursor, and drops control strings whole, even split across reads.
// Run: node hud/fixtures/test_dock_terminal.mjs hud/dock.js (test_dock.py runs it when node is here).
import fs from "node:fs";
const src = fs.readFileSync(process.argv[2], "utf8");
const m = src.match(/export function makeTerminal[\s\S]*?\n}\n/);
const makeTerminal = new Function(m[0].replace("export ", "") + "; return makeTerminal;")();
const E = "\x1b";
const one = (s) => makeTerminal().write(s);
const cases = [
  // the harness's own trust screen, as it drew it on 2026-10-24: spaces by absolute column
  [`\r\r\n${E}[2GQuick${E}[8Gsafety${E}[15Gcheck:${E}[22GIs${E}[25Gthis${E}[30Ga${E}[32Gproject?`, "\n Quick safety check: Is this a project?"],
  [`Quick${E}[1Csafety${E}[1Ccheck:`, "Quick safety check:"],
  [`${E}[>0q${E}[?2004hHello${E}[0m world`, "Hello world"],
  [`${E}P>|xterm${E}\\A${E}]0;title${E}\\B${E}]8;;http://x${E}\x07C`, "ABC"],
  [`one${E}[2;1Htwo`, "one\ntwo"],
  [`50%\r75%\r100%`, "100%"],
];
let ok = true;
for (const [i, o] of cases) { const got = one(i); if (got !== o) { ok = false; console.log("FAIL", JSON.stringify(got), "want", JSON.stringify(o)); } }
const term = makeTerminal();
const a = term.write(`Yes${E}[`), b = term.write(`>0q, I trust`);
if (a !== "Yes" || b !== "Yes, I trust") { ok = false; console.log("FAIL split", JSON.stringify(a), JSON.stringify(b)); }
console.log(ok ? "terminal: all pass" : "terminal: failures");
process.exit(ok ? 0 : 1);
