// test_ledger_sum.mjs: the Ledger's figures are one sum. The headline's time given is the sum of
// the "given by you" of every house shown; the time witnessed is never more than the time given;
// "still only claimed" counts exactly the person's own rows marked claimed. Fails if they differ.
//   node hud/fixtures/test_ledger_sum.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const HUD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = fs.readFileSync(path.join(HUD, "ledger.js"), "utf8");
const w = src.match(/const WITNESS = [^\n]*\n/)[0];
const fn = src.match(/export function ledgerSums[\s\S]*?\n}\n/)[0].replace("export ", "");
const ledgerSums = new Function(w + fn + "; return ledgerSums;")();
let ok = true;
const fail = (name, msg) => { ok = false; console.log("FAIL", name, msg); };
for (const name of ["truth", "room-work", "fresh", "large", "names-hidden", "empty"]) {
  const f = path.join(HUD, "fixtures", name + ".json");
  if (!fs.existsSync(f)) continue;
  const st = JSON.parse(fs.readFileSync(f, "utf8"));
  const tea = st.tea || {};
  const ids = (st.holons || []).map((x) => x.id);
  const s = ledgerSums(tea, st.actor, ids);
  const byHouse = Object.values(s.holons).reduce((a, x) => a + x.mine, 0);
  if (s.source === "entries" && byHouse !== s.mine) fail(name, `headline ${s.mine} min, houses ${byHouse} min`);
  if (s.source === "totals" && Object.keys(s.holons).length) fail(name, "a house line drawn without its entries");
  if (s.witnessed > s.mine) fail(name, `witnessed ${s.witnessed} > given ${s.mine}`);
  const claimedRows = Object.values(s.holons).flatMap((x) => x.rows).filter((e) => (e.actor || st.actor) === st.actor
    && !["keeper", "supercell", "cell", "beyond"].includes(e.witness)).length;
  if (claimedRows !== s.claimed) fail(name, `claimed said ${s.claimed}, rows ${claimedRows}`);
}
// a known fault: fourteen hours above a house row of twenty-two
const bad = ledgerSums({ by_actor: { me: { minutes: 840, witnessed_minutes: 660 } }, by_holon: { h: { minutes: 1290 } } }, "me", ["h"]);
if (Object.keys(bad.holons).length) fail("truth-fault", "a house total of everyone's time drawn under the person's own headline");
console.log(ok ? "ledger sum: all pass" : "ledger sum: FAILED");
process.exit(ok ? 0 : 1);
