# The Game Engine — release layer 4

*What this layer is, where its boundary runs, and what it carries on its own. Architecture 17 gives the shape: every layer has its own version, lineage, record of changes, contract, tests and keeper.*

- **Version:** game-engine 1.0.0 (the first number, set when the one engine lands; `plan.VERSION`)
- **Lineage:**
  - It grows from the kit's engine of 3.6 (`schedule.py` and its siblings), with the planning modules joined to it under one contract.
  - The changes are pulled from this kit.
- **Keeper:** the kit's keeper.
- **Changes:** `CHANGES-ENGINE.md` beside this file, newest first, each with its why.
- **Contract:**
  - **With the ICE above it:** `STATE.md`, chiefly `cards`, `path`, `buffers`, `load` and `plan`.
  - **What it reads below it:** the Record's contract, `SCHEMA.md` (the lines, the types in `types.json`, the fold). It also reads `calendar.json` (`markers` and working days) and `holon.json` (`places`, `periods`, `home_place`, `capacity_assumed`, `targets`, `baseline`).
- **Tests:** `tests/test_schedule.py`, `test_plan.py`, `test_chain.py`, `test_resources.py`, `test_lps.py`, `test_sbs.py`, `test_exports.py`, `test_capture.py`, `test_two_houses.py` and `test_game.py`. The Record's and the Proxy's tests sit beside them and are theirs.

## The boundary: which files in `engine/` are this layer

`engine/` holds three layers' code today; architecture 17 §8 moves them apart gradually.

| layer | files |
|---|---|
| **The Game Engine (this layer)** | `schedule.py` (the two passes) · `plan.py` (the whole, in one call) · `chain.py` · `resources.py` · `lps.py` · `sbs.py` · `exports.py` · `capture.py` · `gamecore.py` · `deal.py` · `owed.py` · `kept.py` · `turn.py` · `ledger.py` · `ladder.py` · `sightings.py` · `attention.py` · `push.py` · `rooms.py` · `bodies.py` · `engine.py` (the state builder) · `STATE.md` |
| **The Record** | `record.py` · `holon.py` · `conformance.py` · `types.json` · `SCHEMA.md` · `fixtures/` |
| **The Proxy** | `proxy.py` · `routes.json` · `vendors.sample.json` · `mail.py` (its door to mail) |

**The rule:** an Engine module imports only other Engine modules and the standard library. It reads the Record through the fold's output and `types.json` as data, never through `record.py`'s insides. The exception today is `engine.py`, the state builder, which calls `record.read`/`fold`. That is the one door between the layers.

## The one engine: what it computes

`plan(items, calendar, data_date, registers)` runs:

1. **The two passes,** whole. Typed links with lags, a working calendar per holon, minutes as the one unit with fractions kept, `within` as the nesting edge with units routed to their entries and exits, no imposed date on a Work Card, and a milestone's target read from its marker in the calendar.
2. **Resources.** Actors by id; capacity from Pledges, else the assumed number, said as assumed; the level of commitment across every holon and Quest; TEA (the Living's alone), Fiat and Tokens per card and unit.
3. **The two passes again,** on each Actor's own minutes a day.
4. **The chain.** The leveled pour, the critical chain traced, root-sum-of-squares project and feeding buffers over the two estimates, the fever chart, release by pull, and the day: Should and Can per Actor, with unsized cards apart. Will is never computed.
5. **The Last Planner measures.** PPC, PRC, the commitment level, misses with their eight reason codes, the constraint log, make-ready over the six-week look-ahead, red-yellow-green, target value and the weekly work plan.
6. **The SpaceTime Breakdown Structure,** then the exports (MS Project XML, the wall page, CSV), and capture (rows read from a photo become proposals the person confirms).

**Every module keeps:**
- no dates, names or ids in code;
- computed, never typed;
- honest-empty;
- deterministic.

## The gate for this layer (architecture 17 §7)

1. Its tests pass.
2. The shadow run: any engine a house ran before beside this one on the same record, until every difference is explained.
3. The switch: the house plays on this layer.
4. The two-house test.
