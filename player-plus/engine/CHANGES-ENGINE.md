# The Game Engine — changes

*Newest first; each change with its why. This layer's own record of changes (architecture 17 §4). The kit's CHANGES.md names the release that carries it.*

## game-engine 1.0.0 — 2026-10-29 — the one engine

**Why:** two engines had grown side by side, and the best work lived in two places and drifted apart (architecture 17 §1). The two are now one, on the kit's base, held to one contract on dates, commitments and minutes.

**The contract:**
- **No date is imposed on a Work Card.** A time constraint on a card is reported and never applied. A milestone keeps only its marker's target, read from `calendar.json` `markers` by the milestone's `marker` field.
- **A commitment never writes onto its card.** The card carries `committed_by`. The schedule reports each commitment whole: committor, committee, direction, delivered_by, due date, computed finish, buffer against the buffer stated, signal, state and as_of.
  - A released, declined or retracted commitment is shown and never compared.
  - It dates no work in its own house or across.
  - Only a commitment, or a milestone's marker target, crosses between houses with a date.
- **Minutes are the one unit.** A duration is minutes over the holder's minutes a day, with the fraction kept and never rounded up. The time indexes keep 6 places.
- **`within` is the nesting edge.**
  - A card that holds others is a unit, and its dates, minutes and percent complete roll up.
  - A link to or from a unit is routed to its entries and exits.
  - The `holarchy` report gives the units, the top, any `within` not held, and every open end.
  - Rows carry their routed `preds`.

**The whole engine** (`plan.py`), with five new modules and capture:
- `resources`, `chain`, `lps`, `sbs` and `exports`, each with its tests;
- `capture`, with its tests;
- `run_plan` in the state builder and `plan` in STATE.md.

The two passes run again on each Actor's own minutes a day, so the logic and the leveled pour agree.

**Tests:** 554 in the engine (1 skipped); 141 more than 3.7.0.

**What it asks of the Record** (offered to the Record's keeper, architecture 17 §4):
- the lines `pledge`, `miss`, `constraint` and `clear`;
- on `commit`, `committee` and `buffer`;
- `release` and `answer` acting on a commitment, by its committee;
- `within` as a link kind;
- a miss's `reason` kept on the fold's entry;
- the card fields `minutes_safe`, `marker`, `where`, `conditions`, `tea`, `fiat`, `tokens_m` and `platform`, and the stage `could`.

**What it gives the ICE:** the `plan` object in STATE.md, and the Wall view (`hud/wall.js`), which reads only `cards`.
