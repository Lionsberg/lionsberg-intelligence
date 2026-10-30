---
title: The Game Engine — architecture
description: The calculating layer of the kit — the schedule, the leveled chain, the Last Planner measures, what is owed, commitments kept, The Deal, the Turn, the ledger and the Score, as pure functions over the record.
---

# The Game Engine — architecture

*The Game Engine is the calculating layer of the LIØNSBERG Intelligence System: pure functions over a [[Holon]]'s [[The Record|record]] that say what is in play, what is next, what is owed, which commitments were kept, and what the gap was. It owns no state, no rule the Playbook does not give it, and no answer a person with a pencil could not reach on one sheet. It is one of three parts of the Supersuit; the [[Agent]] writes the lines it reads, and the ICE, the Integrated Creation Environment (the [[HUD]]'s views, the dock, the Room), renders what it returns.*

## 0. What it stands on

- **One engine, one layer.** The Game Engine is release layer 4 of the kit, version **game-engine 1.0.0**, with its own record of changes ([CHANGES-ENGINE.md](../engine/CHANGES-ENGINE.md)), its own contract and its own tests ([ENGINE.md](../engine/ENGINE.md); the layers themselves: [17 — The Layers](<17 — The Layers — How the Kit Is Built, Improved and Shipped (Architecture, 2026-10-29).md>)).
- **The record is the only input.** One signed line per event, one append-only file per actor per holon (the Record's contract, [SCHEMA.md](../engine/SCHEMA.md)). Items are folded, never stored. The Engine also reads each holon's `calendar.json` (`markers` and working days) and `holon.json` (`places`, `periods`, `home_place`, `capacity_assumed`, `targets`, `baseline`).
- **Minutes are the one unit.** Effort is minutes on the card. Days are derived as minutes over the holder's minutes a day, with the fraction kept and never rounded up, except where the world sets the duration.
- **No date is imposed on a Work Card.** Start and finish dates are calculated from the logic. A time constraint on a card is reported and never applied; a milestone keeps one date, its marker's target (§2.6).
- **A commitment never writes onto its card.** The card carries `committed_by`; the schedule reports each commitment whole, beside the card (§2.7).
- **`within` is the nesting edge.** Every card lies within one larger unit, and a card that holds others is a unit (§2.5).
- **The schedule is a pure function of the events.** Given the same lines, every holon, by script or by hand, computes the same answer. Every module keeps four rules: no dates, names or ids in code; computed, never typed; honest-empty; deterministic.
- **No center but ØNE.** There is no master schedule kept by a master; each holon runs the two passes over its own cards, and a dependency crosses a membrane only as a [[Commitment]].
- **Reported, never imposed.** Float, buffers, leveled dates and the drum are signals for Living Intelligence to read. The Engine never moves a date, assigns a person, or ticks a box.
- **Three layers make it a kit part:** the specification in plain words with a worked example, so paper gets the same dates; a conformance deck with known answers that any implementation must reproduce; and reference implementations judged by that deck.

### The boundary

`engine/` holds the code of three layers. The Game Engine's files are `schedule.py` (the two passes) · `plan.py` (the whole, in one call) · `chain.py` · `resources.py` · `lps.py` · `sbs.py` · `exports.py` · `capture.py` · `gamecore.py` · `deal.py` · `owed.py` · `kept.py` · `turn.py` · `ledger.py` · `ladder.py` · `sightings.py` · `attention.py` · `push.py` · `rooms.py` · `bodies.py` · `engine.py` (the state builder) · `STATE.md`. The Record's are `record.py`, `holon.py`, `conformance.py`, `types.json`, `SCHEMA.md` and `fixtures/`; the Proxy's are `proxy.py`, `routes.json`, `vendors.sample.json` and `mail.py`.

**The rule:** an Engine module imports only other Engine modules and the standard library. It reads the Record through the fold's output, and `types.json` as data, never through `record.py`'s insides. The one door between the layers is `engine.py`, the state builder, which calls the Record's read and fold.

## 1. What it reads: the fold

`fold(lines) → items` is the Record's; the Engine reads what it returns. The fold reads every line of every holon the player holds (their own home and each cell under `cells/`) and produces the items: [[Work Card]]s, commitments, threads, decisions, requests, offers, sightings, delegations, TEA entries, turns, baselines, discernments, pledges, constraints and misses. The type registry (`types.json`) says which event type creates or changes which item, with which fields and which state transitions; **a new type is declared as data, never built as code.**

What the fold checks, line by line:

1. **Identity.** The `id` is recomputed from the canonical line (sorted keys, no spaces, UTF-8, body strings through their salted digests) and must match. A line whose id does not verify is left out and reported in `problems`.
2. **Signature.** Verified in the fold against the actor's own key, each key admitted to the holon by a `join` or an `affirm` line. An empty signature is the [[Paper Floor]], shown as such, never as signed, and an unsigned line is authoritative only at the paper floor in the home record.
3. **Delegation.** A line by `agent:` anyone counts only when a live `delegate` from its Living Intelligence covers its type and its holon at its time, or when the person's recorded consent covers that one act. Outside that it folds as an invalid claim: shown, never counted.
4. **Human-only acts.** Every type the registry marks human-only is a Living Intelligence's own act, and no standing delegation covers it: `settle` · `commit` · `kept` · `witness` · `decide` · `ratify` · `delegate` · `revoke` · `join` · `leave` · `publish` · `turn` · `discern` · `posture` · `affirm` · `layout` · `elevate` · `escalate` · `attention` · `keepsake` · `study` · `shape` · `part` · `vote` · `pledge`. `answer` is not among them. The registry is the authority; this list is read from it.
5. **Reason.** A line with `reason: untrusted` folds as a *proposal*: visible, never owed, never dealt, never counted.
6. **Supersession.** A `supersede` line replaces the body of the line it links to; both remain; the latest shows. A line is superseded only by the same actor or by a person's `decide`.
7. **Elision.** An elided field folds as hidden and still verifies.
8. **Links, not times.** `ts` is the author's claim, never the order. Order comes from `prev` (each actor's chain) and from typed links. A link to a line not held reads **"not yet replicated"**, never broken.
9. **As of.** For every holon the fold records the newest line it saw: `{event, ts, lines}`. Every number downstream is as of those lines.

## 2. The schedule

`schedule(items, calendar, data_date) → early and late dates, total and free float, the critical path, variance against the named baseline, buffers, load, earned value`. It is the Critical Path Method of 1957, whole, with the bookkeeping that makes it honest at the edges.

### 2.1 Time: the Gameclock and calendars

- **The Gameclock** is the nest of rhythms every holon shares: the **season** (turning to turning, solstice and equinox) · inside it **two spans of 42 days** · the **new and full moons** · the **week**, the Heartbeat · the **day**. **[[OmniSpection]]** is continual, at varying depths: daily, at each new and full moon, and at each seasonal turning. The Gameclock is computed from the turnings, the moons and the calendar, never typed (`schedule.py` `gameclock()` and `rhythms()`); a calendar may carry its own turnings and moons.
- **Temporal markers stand apart from milestones.** An equinox is a temporal marker on the clock, a rhythm; a milestone is work. A holon's markers live in its calendar, `calendar.json` `markers`: `{id, name, date, state: open | passed}`. A milestone names its marker in its `marker` field, and its target is read from there, never from the card or from code.
- **Each holon keeps its calendar** (`calendar.json`), and each holon's cards are scheduled on that holon's own calendar: working days, and each Actor's minutes per day. The default counts all seven days (the Daily Way runs every day) and 480 minutes (32 of the day's 96 quarter-hours); 480 is an assumed value, used only where no Pledge and no calendar number gives one. Every number about a Living Actor is theirs to set; an assumed value says so. The state says whether its days are `working-days` or `calendar-days`.

### 2.2 The data date

The moment the schedule is true as of: day 0, today at every run unless named. A whole day index means the morning of that day: early start is the morning work may begin, early finish the morning after the last day of work, and a target date is the morning of that day. A fractional index is part-way through that working day; its date is that day.

### 2.3 Activity types and durations

- **Types:** activity (every card kind not named below: decision, review, draft, research, birth, quest) · **milestone** (zero duration) · **level of effort** (spans from its predecessors' earliest start to its successors' latest finish; drives nothing) · **summary** (rolls up a scope-tree node; drives nothing) · **unit** (a card that holds others, §2.5).
- **The minutes-to-days rule:** a duration the world sets (`dur_days`) is used as given; a milestone is zero; otherwise days = minutes ÷ the holder's minutes per day, in working days with the fraction kept (a 2-hour card on a 480-minute day is 0.25 days, and its successor starts the same day, a quarter of the way in). The time indexes keep six places, a minute's worth of a day, so a 30-minute card never shows a false float. A card with neither minutes nor a set duration, or a holder with 0 minutes a day, is zero days and is named in the warnings: honest-empty, never guessed.

### 2.4 The four relationship types

Finish-to-start (the default), start-to-start, finish-to-finish and start-to-finish, each with a lag in whole working days (halves away from zero), positive or negative. Predecessors and successors are links on the card; type and lag ride beside them. Forward: FS = P.EF + lag · SS = P.ES + lag · FF = P.EF + lag − duration · SF = P.ES + lag − duration. A lag counts on the predecessor's calendar.

### 2.5 The holarchy: `within`

Every card lies within one larger unit, named by its `within` link; a card that names more than one is read within the first, and says so. A card that holds others is a **unit**: its dates, minutes and percent complete roll up from its cards. A link to or from a unit is routed to its own cards: a link from a unit leaves by its exits (the cards nothing inside it waits on) for FS and FF, by its entries for SS and SF; a link to a unit arrives at its entries (the cards that wait on nothing inside it) for FS and SS, at its exits for FF and SF. Nested units route all the way down, and each row carries its routed `preds`, the logic as run. A `within` that names a card not yet held reads "not yet replicated"; one that would close a loop is reported and read as none; a link between a card and a unit that holds it is read as nothing.

The `holarchy` report gives the units, the cards at the top (within nothing held), every `within` not yet held, and every open end: a card nothing comes before, or nothing comes after. Every card lies within one unit and has at least one card before and after it; an open end is reported, never filled by guess.

### 2.6 Constraints

**Constraint** is one word with sorts: resource, information, agreement and time. The resource, information and agreement sorts (what must clear before work is ready) are read by the Last Planner measures (§3.5); the schedule reads only the time sort. **A time constraint is an imposed date.** It lives in the card's `constraint` field, one or a list: `{sort, kind, date, reason, imposed_by, source}`, where kind is finish-by · finish-no-later · start-no-earlier · start-on · finish-on · as-late-as-possible, and source is commitment · world · law. The simple forms (`by`, `start_no_earlier`, `finish_no_later`, `must_start_on`, `must_finish_on`, `alap: true`) still read.

- **No date is imposed on a Work Card.** A time constraint on a card is reported and never applied: it moves none of the card's dates. Start-on, finish-on and start-no-earlier are applied to no card.
- **A milestone keeps one date: its marker's target.** Its finish-by (a finish-on is read as a finish-by) bounds its late finish, in the backward pass alone. A marker not in the calendar, a marker that has passed, or a marker named by a card that is not a milestone is a warning, and no work is measured against it.
- **As-late-as-possible is a release rule, not a date,** and is kept: it delays the card by its free float, never past its total float.
- **Negative float is reported and never clamped.** When the logic cannot meet a milestone's target, the number goes negative and stays visible, against the constraint, never hidden by moving it. That is the record's honesty, computed.
- **The constraints report** counts every time constraint: how many, the share of cards constrained, hard (start-on, finish-on) against soft, those on activities rather than milestones, which were applied, the negative float and the delay each would cause, and the defects. A time constraint without a reason or an imposer, without a date, or with a source other than commitment, world or law is a defect, and is reported as one.
- The calculation reads the full set of kinds the heavy scheduling engines offer, and a holon's own convention may restrict which constraints its cards carry.

### 2.7 Commitments on a card

A [[Commitment]] never writes onto its card. The card carries `committed_by`, and the schedule reports each commitment made on it whole: its committor and committee; its direction, `given` or `received`, as seen by the reader; `delivered_by` (the card); its due date; the card's computed finish (its last day of work); the buffer, the due date less that day in calendar days, negative when the network cannot keep it; the buffer the committor stated (minutes, read in the holder's working days); the signal (`cannot keep` · `inside its buffer` · `safe`); its state (`delivered` is the committor's word, `kept` the committee's); and as of which day. A released, declined or retracted commitment is shown and never compared, and it dates no work, in its own holon or in another.

### 2.8 The two passes, with retained logic

- **Forward:** ES = the latest of 0 and each predecessor's constraint (and, for a card in another holon's graph, each fixed-date external, §4.2); EF = ES + duration.
- **Backward:** the late end is the latest of every EF and every applied finish-by; LF = the milestone's target when it has one, else the late end, then the least of each successor's constraint (FS: S.LS − lag · SS: S.LS − lag + duration · FF: S.LF − lag · SF: S.LF − lag + duration); LS = LF − duration.
- **Progress, by retained logic.** Complete work (done, kept or delivered; stage *did*; an actual finish; 100 percent) drops out of the logic and constrains nothing further. Released and declined cards leave with their links. Work in progress schedules only its remaining duration, from the data date, and **unfinished predecessors still hold it**: a commitment not kept is the record's signal, so the Engine does not let started work jump its logic. A start-to-start or start-to-finish lag from started work counts from its actual start.

### 2.9 Float

**Total float** TF = LS − ES: how far a card may slip before it moves the finish or breaks a milestone's target. **Free float**: how far it may slip before it moves any successor (FS: S.ES − lag − EF · SS: S.ES − lag − ES · FF: S.EF − lag − EF · SF: S.EF − lag − ES), or its own target, or with no successor the late end; then held between 0 and total float. Free float never exceeds total float, and negative float lives in total float alone. **Near-critical**: 0 < TF ≤ a threshold (three days by default), the band [[The Deal]] watches most closely.

### 2.10 The critical path

The cards with TF ≤ 0. When a milestone's target cannot be met, the whole chain to it shows the same negative number. The *system* path is the same calculation done by the widest holon over every published milestone (§4.3); a card on it carries `system_critical`, and The Deal may say: *the whole is waiting on this.*

### 2.11 Baselines and variance

`freeze(items, name)` writes `plan/baseline-<n>.json`, a frozen copy of the plan (n the next integer; an existing baseline is never touched), the same at every depth, and the Agent drafts a `baseline` line for the person to sign. **The Engine writes the plan; nothing else does.** The current baseline is the highest *n* unless one is named. Variance = current minus baseline in working days, positive when later. The seasonal [[The Turn|Turn]] freezes one at each turning, and so does the weekly Turn in a holon that keeps one; the freeze is written by `engine.py turn --depth seasonal --freeze` (or `--depth weekly`), which says plainly when nothing was written. Variance is measured; re-baselining is a recorded act, never a quiet overwrite.

### 2.12 Progress

Stated by the one who did the work, at the Turn or when it happens: `done`, an actual start or finish, remaining minutes or days, or a percent. No meter, no timesheet approval: the claim is the Actor's, and a witness verifies what matters (§6). Remaining duration is, in order: stated days, stated minutes through the calendar, the duration less the stated percent, the full duration, each with the fraction kept.

### 2.13 The scope tree and codes

A card's `codes` are paths (`Pillar/Stream/Package`), a single path, or a map of classifications (`key:value` as the first segment). Every prefix of every path is a node; the rollup gives each node its cards, minutes, percent complete, earliest start, latest finish and least float. This is how a deliverable breakdown and a functional taxonomy live together: one is the [[Work Breakdown Structure]] and obeys the hundred-percent rule (every scope element in exactly one branch); the twelve Pillars and any other cross-cutting family are codes, so interwoven work is coded and never duplicated.

### 2.14 The worked example (the paper conformance deck, in miniature)

Five cards, data date day 0, calendar days. A 3 days; B, 2 days, after A; C 4 days after A; D 1 day after B and C; E a milestone after D, whose marker's target is day 7.

| | ES | EF | LF | LS | TF | FF |
|---|---|---|---|---|---|---|
| A | 0 | 3 | 2 | −1 | −1 | 0 |
| B | 3 | 5 | 6 | 4 | +1 | 1 |
| C | 3 | 7 | 6 | 2 | −1 | 0 |
| D | 7 | 8 | 7 | 6 | −1 | 0 |
| E | 8 | 8 | 7 | 7 | −1 | 0 |

The late end is the latest of EF 8 and the target 7, so 8. B's free float is the least of D.ES 7 − EF 5 = 2 and its total float 1, so 1. Critical: A C D E, a day late against the target; B has a day of float. A person does this by pencil in minutes; `tests/test_schedule.py` reproduces it.

## 3. The whole engine

`plan(items, calendar, data_date, registers)` runs the whole Game Engine in one pure call over the folded record, in the order of its dependencies: the two passes; resources; the two passes again on each Actor's own minutes a day, so the logic and the leveled pour agree; the chain; the Last Planner measures; the SpaceTime Breakdown Structure. The registers it reads come from the record and the holon's own files, never guessed: commitments, misses, constraints and pledges are lines; markers live in the calendar; places, periods and the home place in `holon.json`; actors are the holon's admitted participants. What it lacks it names in `missing` (no Pledge; no card with two estimates, so no buffer can be sized).

### 3.1 Resources and capacity

- **Actors** are anyone in the chain, living or artificial, known by opaque id, never by a name. An id beginning `agent:` is artificial unless the register says otherwise; class (actor · player · player+) comes from the register.
- **A Pledge** is a commitment of TEA, fiat and tokens for a period, to a holon or a unit. Level `season` is the baseline, to a holon; level `quest` is a share of it, to a Quest or other unit; Quest Pledges subdivide the Season's. A Pledge with no readable level, an unknown period or a negative number is reported and never guessed.
- **Capacity**, in minutes per working day, is the greater of the season-level and the quest-level Pledges per week over the Actor's working days per week, with the fraction kept. Without a Pledge it is the holon's assumed number, said `assumed`; else none.
- **The level of commitment** is read across every holon and Quest the Actor is engaged in, never one.
- **TEA · Fiat · Tokens**, the three things work consumes, per card and per unit. TEA is the Living's alone, in minutes; a card's TEA defaults to its own minutes for a living holder. An artificial Actor's work is counted in Tokens (`tokens_m`, with `platform`), never TEA. Fiat is per currency. A unit's sums are over its leaves, each counted once.

### 3.2 Leveling

- **Load:** each card's remaining minutes spread evenly over the holder's working days between its early start and early finish, against the holder's minutes per day: `{actor, date, minutes, capacity}`. Milestones carry no load. Read as a gauge, never used to impose.
- **Local leveling in the schedule:** on request, one Actor's cards in one holon are chained finish-to-start in order of least late start, and both passes run again.
- **The leveled pour in the chain:** serial, in the order of the logic. Among the open cards whose predecessors are all leveled, take the least late finish, then the least total float, then the id; from its logic early start and its predecessors' leveled dates, the holder's remaining focused minutes are poured into the holder's days with room, at their capacity, each day filling from its morning. Leveled float = the logic late finish − the leveled early finish. A milestone, a card with no minutes left, a card whose duration the world sets, and a card whose holder has no capacity are not poured, and each is listed in `unleveled` with its reason.
- **Leveled dates stand beside logic dates, never instead of them.** Neither is "the" schedule; the record carries both.
- **No global leveling.** Leveling across holons would need a center that holds everyone's capacity. The system levels itself holon by holon, and each person levels their own day through The Deal, which never deals more minutes than they have.

### 3.3 The critical chain, its buffers, the fever chart and release

- **The critical chain is traced, never guessed:** for each open end milestone and each milestone a marker names, walk back along the predecessor that set its leveled start, a logic predecessor or a resource one (the card the leveling placed it after on the same holder).
- **Buffers, by the root of the sum of squares.** A card with two estimates (`minutes` and `minutes_safe`) has a safety of max(0, minutes_safe − minutes). A **project buffer** per traced chain is √(Σ safety²) in minutes, and in days √(Σ (safety ÷ its holder's minutes a day)²). A **feeding buffer** stands where a non-chain predecessor joins a chain card, sized the same way over the side chain. A chain with no two estimates has no buffer yet, and says so.
- **The fever chart,** per project buffer: done share = minutes done ÷ minutes of the chain; consumed share = the working days the milestone's leveled finish has moved past its baseline leveled finish, over the buffer's days. Red above 0.30 + 0.70 × done, yellow above 0.15 + 0.55 × done, green on or below the line.
- **Release by pull.** A card on a chain is released on its leveled start; any other on the later of its early start and its late start less its feeding buffer. A side chain starts late by design.

### 3.4 The day: Should and Can

Per Actor with capacity: **Should** is the Actor's cards whose leveled start lies on the data date, the chain first, then the least leveled float, then the id, up to the minutes the Actor has for the day (always one, if there is any). **Can** is the part of it whose stage is `can` or whose predecessors are all complete. Unsized cards stand apart. **Will is never computed:** it is the Player's own choice.

### 3.5 The Last Planner measures

How reliably the plan is kept, after the [[Last Planner System]]:

- **PPC** (Percent Plan Complete): of the commitments due by the data date, the share delivered on or before their due date; all time, by week, and by committor. **PRC** (Percent Required Completed): the same, over commitments on critical cards only.
- **The commitment level** over the next seven days: the open critical cards that start in them, and those carrying a live commitment or standing at stage `will`.
- **Misses,** each with its reason for plan failure, one of eight codes (prerequisite · definition · estimate · capacity · priority · external · conditions · other), from the `miss` lines, never parsed from free text; else "not yet given".
- **The constraint log** (the `constraint` and `clear` lines, then constraint cards, then a card's own non-time constraint), with need-by, days to need and overdue; **make-ready**: the open cards starting inside the six-week look-ahead that still carry an open constraint or conditions, so their removal can be assigned before the work comes.
- **Red-yellow-green** per unit on its total float (red below 0 days, yellow below 5); **target value** per unit with a target in minutes; and **the weekly work plan**: the week's Wills, made and kept on time, its PPC so far, and the day's Should and Can.

A commitment is due when its due date is on or before the data date and it is not released, declined or retracted; it is complete when delivered on or before its due date, by the committor's word or the committee's.

### 3.6 The SpaceTime Breakdown Structure

The Work Breakdown says what the work is; the SpaceTime Breakdown says where and when it lands. It has two holarchies: **space**, places within places, and **time**, periods within periods, each checked and never repaired (one root, no loop, every `within` held, every span readable and inside its parent). A card's place is its own `where`, else its nearest enclosing unit's, else the home place, else `unplaced`; a place is location, never identity. Its period is the smallest period that holds its last day of work, computed, never typed, so it moves with the plan. The matrix gives every open card per place and period: the cards, minutes, least total float and how many are critical.

### 3.7 Exports and capture

- **Exports:** Microsoft Project XML (every scheduled row a task, outline level along `within`, a predecessor link per link), one self-contained HTML wall (a column per week, a sticky per open card coloured by state, every link drawn, no network), and CSV. The same inputs give the same bytes.
- **Capture:** rows the agent reads from a photo of a paper pull-plan wall become **proposals** (`reason: untrusted`), matched against the cards already held, and nothing is written until the person chooses which to keep; each chosen row then becomes one act in the person's own name. A link to a title held nowhere stays a named open end.

## 4. Across holons

### 4.1 Commitments are the only crossing edge

A holon publishes its card **faces** (what it is, its state, its by-when, who holds it, its stream), its milestones, its commitments, its requests and its offers, never its inner activities. A dependency on another holon is never a link to their activity; it is a commitment they made, or a request we made that they answered. Across a membrane there is no task: a supercell *requests*, a subcell *offers* and *commits*, and assignment happens only inside a holon, by the one who will do the work. (After [[Networks of Commitments]] and the [[Last Planner System]].)

**Only a live commitment, or a milestone's marker target, crosses between holons with a date.** A holon's graph is its own cards, plus the published milestones and committed cards of the other holons it holds, and every card from a holon it does not hold, all as fixed-date externals, never as live cards. Each external's date is the commitment's due date (with two live commitments on one card, the earliest governs) or the milestone's target; every other date field is cleared first. A card appears once, under its home holon, so two players holding the same cell compute the same float for its cards.

### 4.2 Interface milestones

An external enters the schedule as a **fixed-date node**: a card that names it as predecessor starts no earlier than its date; an external that names our card as its predecessor gives that card a finish-no-later-than. An external with no date is a warning. A milestone flagged `interface`, or linked to another holon or an external line, is an **interface milestone**. That is how practice already integrates sovereign schedules that share no database; no mainstream engine computes a critical path across them, and that absence is the space the Game occupies.

### 4.3 The wide pass publishes back

A supercell computes over its own cards plus its members' published milestones. The widest holon's pass over every published milestone is the system path. It publishes back each milestone's float as seen from above and whether it lies on the system path (an external line whose body lists `system_path` or `critical` marks those cards), so a member's own cards take on the wider color. The apex is the shared Intent every holon reads, never a node that commands.

### 4.4 The schedule's buffers and the drum

- **Critical chain in the schedule, reported, never imposed.** Beside the chain's leveled buffers (§3.3), the schedule reports its own: a chain is the longest path to a milestone by full original durations, and its buffer is half the chain's duration (the halving rule of critical chain practice). A **project buffer** sits before each end milestone; a **feeding buffer** at each interface milestone, held by the supercell. The buffer occupies the days just before the milestone's target (with none, the days just after its baseline finish). Placing the feeding buffer before the interface milestone's target, with durations not cut, is the Game's adaptation of critical chain practice, not the textbook placement.
- **The signal:** buffer consumed against chain complete. Green while the consumed share is no greater than the complete share; yellow within a third more; red beyond.
- **The drum:** the Actor on the chain with the least free capacity. The scarce resource is the attention of Living Intelligence; the scarcest attention in the system sets the pace.

### 4.5 As of

Two holons holding the same lines compute the same path; they differ only by replication lag, and every result says as of which line it last saw from each holon. A pull that failed is named, and its part of every number is labeled as of the last pull. The whole is as current as its replication, and the Engine makes that lag visible instead of hiding it behind a server.

## 5. What is owed

`owed(items, actor) → what waits on whom`, computed, never remembered. Across every holon:

| kind | owed when |
|---|---|
| commitment | open and past its by-when, or due within the horizon (two days by default) |
| request | no one has answered it |
| thread | its last line is not the holder's (addressed to them, or one they spoke in) |
| ratify | a decision made and waiting for a person's ratification (the keeper unless named) |
| decide | a proposal put to a person by name |
| claim | a claim whose time ran out while the card is not done |
| handoff | an agent body's handoff no person has reviewed, owed by the person it answers for |
| question | an `rfg` or `escalate` past its by-when, owed by the holon it climbed to |

Each entry carries kind · id · holon · title · holder · status (past · near · waiting) · due · age in days · minutes to answer. Lines an agent wrote for an untrusted reason are never owed; they come back as **proposals**, for a person to take up or let go.

## 6. Commitments kept, and the gap

`kept(items, holon, window) → commitments kept, the gap per commitment, the learning`.

- **A commitment** is a `commit` by a Living Intelligence: the card, by when, conditions, size in minutes, its committee, the buffer it states, and a witness. The cycle is should · can · will · did, and **only the person chooses will.**
- **Kept is claimed, then verified.** The committor claims kept (`kept`); a witness verifies (`witness`): the named [[Witness]] or the committee, never the committor. Status: open · kept (claimed and witnessed) · kept-unwitnessed · broken (past its by-when, not kept; rendered *not kept by the by-when*) · released (let go openly). `returned` (handed back) is reserved, not a live status.
- **The gap** = the keeping time minus the by-when, in days; negative is early; empty while open. Computed, never softened.
- **The share** = kept ÷ (kept + kept-unwitnessed + broken), empty when nothing fell due. **Commitments kept** is the first number every holon sees, per holon and per actor, over a window (a week by default). Beside it, `share_claimed` counts the keepers' own claims too.
- **Breaking a commitment is a process,** so the chain holds: release or return it openly, and the successors see it at once.
- **The learning** is the `learn` lines attached to a commitment or its card.
- **The words describe what happened to a commitment, never a person.** The one who assigns, or who did the work, never witnesses it.

## 7. The Deal

`deal(items, actor, minutes, room) → The Deal`: the few Work Cards that need this person now, sized to the minutes they have.

- **Order:** what is owed of them · threads waiting on their word · decisions waiting on them · ready cards ranked by leverage. Always last, at no cost in minutes, the standing question: **"What did we miss that matters to you most?"**
- **Leverage within authority.** Leverage = (own minutes × urgency of own float + Σ downstream minutes × urgency of their float) × 1.5 on the critical path × 1.5 when someone it touches is in the room, ÷ own minutes; urgency = 1 ÷ (1 + float ÷ 3) up to 14 days of float, 0 beyond, 0.25 when unknown. Leverage is urgent work moved per minute of the person's own: at float 0, a 5-minute card that frees 120 minutes downstream scores (5 + 120) ÷ 5 = 25, and a 60-minute card that frees the same scores 3, so the smaller card ranks higher; ties go to the cheaper card. These are **named assumptions, tuned by evidence, never by feeling**; the rule rides in every Deal so it can be argued with. A person may be dealt anything; an agent is dealt only what a live delegation covers, and never a human-only act or a decision or review card.
- **Sized to minutes.** Cards are taken first fit, in order: each card that fits the minutes left is taken; the rest are counted under *beyond*. Minutes dealt never exceed minutes available. Five minutes is a real Deal.
- **Each card is a question legible alone:** what it is, why it is theirs now (it waits on them; its float is gone; the whole waits on it), the options, a recommendation with its reason, the minutes, what it unlocks, and how to answer in one key or one line.
- **The Engine computes; the Agent shapes and delivers** (the briefing voice, the door the person chose). Answers return as lines. The Engine never ticks the box.

## 8. The Turn

The look at what was said against what was done, at the depth the day calls for: daily, lunar (at each new and full moon) and seasonal, and weekly in a holon that keeps one (`engine.py turn --depth daily|lunar|weekly|seasonal`, with `--freeze`). The Engine's part: freeze the baseline (§2.11); count commitments kept and each gap for the window (§6); gather the window's `learn` lines, the answers to the standing question, and the `discern` lines where the person corrected their agent; and report the last weekly and seasonal `turn` lines and when the next weekly is due. The person finishes the four lines (what I did · the gap · what I learned · what I will do) and signs the `turn` line; the Agent proposes what crosses to each cell. **The interoperability floor:** one consistent seasonal signal from every holon; the weekly Turn offered, never required; nothing else imposed.

## 9. The ledger

`ledger(items, holon) → TEA balances`.

- A `tea` line is written by the one who spent it: minutes, energy (1–10), attention (1–10), and the card it served. TEA is the Living's alone.
- **Witnessed:** unwitnessed · by the holon's keeper · and again by a [[Supercell]]. Each actor's `prev` chain is checked when the raw lines are at hand; otherwise the report says it was not checked.
- Sums minutes and averages energy and attention per actor, holon, card and stream.
- **Non-convertible:** not into money, not into one another, not into rank. Every output says so. The ledger comes first; the full design of the bank comes later.
- Discernment, lightly: `discern` lines counted by route and by verdict, and only a person's `discern` line is counted.

## 10. The Score as earned value's currency

Earned value with the currency changed from money to minutes of TEA. Budget per card = its baseline minutes. **Planned value** = budget × the share of its baseline span elapsed by the data date. **Earned value** = budget × percent complete. **Actual** = TEA minutes spent on it. SPI = EV ÷ PV; CPI = EV ÷ AC. Rolled up per holon and through the scope tree. Beside it stand [[The Score]]'s other lines: commitments kept over commitments made, TEA invested, value sighted. There is no cost account and no rate: throughput of the Goal, never cost.

## 11. The state the HUD reads

`engine.py state HQ_DIR` writes `state.json` ([STATE.md](../engine/STATE.md), state v1): derived, safe to delete, rebuilt from the record, git-ignored. `engine.py` is the one command line (`state`, `deal`, `owed`, `kept`, `turn`, `ledger`). **The HUD reads only the state, and nothing else computes a schedule.** Its rules: times with offsets; minutes as numbers; every list item carries its `holon`; ids are event ids; a missing value is null, never guessed; actors as the record names them, roles never names. It holds the holons with their as-of, the actors with their live delegations, cards with their schedule (each with its `type`, its `within` and its fractional day indexes), commitments, threads, decisions, sightings, the ledger, discernments, The Deal, what is owed (with proposals apart), commitments kept, the Score, buffers, load, the critical and system paths, the Turn, and `plan`: the whole engine per holon held (capacity, level of commitment, the leveled dates, the critical chain, its buffers, the fever chart, release, the day, the Last Planner measures, the SpaceTime placement and matrix, and what is missing). The Wall view (`hud/wall.js`) reads only `cards`. Fields are added, never renamed, within a version.

## 12. The paper floor

Every function by pencil, on the same sheet the record is kept on.

| Function | By hand |
|---|---|
| fold | read the sheet top to bottom; a card is the first line that names it plus every later line that points to it |
| schedule | the two passes over the cards in a table; thirty cards in an hour |
| float, critical path | subtract; circle every row at zero or below |
| baseline | copy the dated table and keep it; never erase |
| owed | list every open line that names you, oldest first |
| kept | count kept, kept-unwitnessed and broken in the week; write each gap in days |
| The Deal | list what waits on you in every group; keep what fits today's minutes; ask the last question |
| the Turn | the four lines on last week's sheet beside this week's |
| ledger | sum the minutes column; the keeper initials each line |
| Score | budgeted minutes × share elapsed; × share done; divide |

A witnessed paper sheet beats the typed copy.

## 13. What the heavy scheduling engines have that this does not yet

Named plainly. *Refused* means by design; *not yet* means just in time, when a holon first needs it.

- **Multiple float paths and the longest-path definition of critical.** We define critical as TF ≤ 0 only; the chain is traced separately (§3.3). *Not yet.*
- **Progress override** for out-of-sequence work (started work ignores unfinished predecessors). We hold retained logic only. *Not yet, perhaps never.*
- **Duration types and percent-complete types** (fixed duration and units, fixed units per time, physical versus duration percent). We hold one rule, minutes through the holder's minutes a day. *Not yet.*
- **Hours and shifts.** A working day is its minutes, with the fraction kept; there are no shift calendars. *Refused for now:* the Daily Way is the smallest complete unit of life.
- **Calendars per activity** and calendar exceptions beyond working days. We hold per holon and per Actor. *Not yet.*
- **Resources as the heavy scheduling engines know them:** roles against named resources, multiple resources per activity, units per time, resource curves, rates, non-labor and material resources. We hold one holder per card, its minutes, capacity from Pledges, and TEA · Fiat · Tokens per card. *Not yet,* and rates *refused* (no cost).
- **Global leveling** with priorities, leveling within or beyond float, across projects. *Refused:* it needs a center. Leveling holon by holon only.
- **Cost loading, cost accounts, budgets in money.** *Refused:* TEA and LUV. Fiat is counted per card, by currency, as one of the three things work consumes; there is no cost account.
- **Schedule risk analysis** (Monte Carlo over duration ranges, probabilistic finish dates). *Not yet;* the buffers stand in.
- **Many baselines compared side by side,** with per-field baseline dates. We keep many and compare against one. *Not yet.*
- **Suspend and resume, expected finish, external early start and late finish dates.** Partly: externals as fixed dates. *Not yet* for the rest.
- **What-if copies merged back (reflection), global change.** By hand today. *Not yet.*
- **Timesheet workflows with approval.** *Refused* as approval; the witness verifies what matters.
- **Thresholds, issues and risk registers** tied to the schedule. Partly: the constraint log, make-ready and red-yellow-green on float (§3.5); sightings carry hazards and blockages. *Not yet* for risk registers.
- **Scale and interchange.** The plan exports as Microsoft Project XML and CSV (§3.7). Millions of activities in one database: our scale is every holon computing its own and meeting at commitments. *Not yet;* when there are millions, a service any holon can run locally, never a center.
- **Multi-user check-out and locking.** *Refused, and unneeded:* one append-only file per actor means there is nothing to merge.

Where this engine already differs from them on purpose: the late-end convention (a distant target on one milestone gives float to every unconstrained card, as the reference scheduler does and the commercial engines do not); no imposed date on any Work Card; an Actor's own working days shape load and the leveled pour, never the logic dates; fractional days.

## 14. Acceptance tests

1. The worked example (§2.14) is reproduced exactly by every implementation. 2. No float is typed: every float shown equals the Engine's after a run. 3. Leveled dates never replace logic dates. 4. Negative float is never clamped. 5. Two holons holding the same lines produce the same schedule fields on every card, given the same data date and each holon's own calendar. 6. A line with `reason: untrusted` is never owed, never dealt, never counted. 7. An agent line outside a live delegation folds as invalid. 8. Minutes dealt never exceed minutes available, and the standing question is always present. 9. A link to an unheld line reads "not yet replicated". 10. Every number in the state names, per holon, the line it is as of. 11. The ledger says *not convertible* in every output. 12. The Engine opens no network connection (the conformance tripwire). 13. Every function above can be worked from the paper record by a person in the time the table says. 14. A time constraint on a Work Card moves none of its dates. 15. A commitment writes nothing onto its card, and a released, declined or retracted commitment dates no work.

The Engine's own tests live in `engine/tests/`, one file per module, with a test of two holons computing over the same lines.

## Open

1. **The stage vocabulary.** The Record's contract reads *should · can · will · did*; the Engine's card types (`engine/types.json`) already accept a typed stage *could* as well. Open: whether the Record's contract adopts *could*.
2. **Card kinds.** Two lists of card kinds differ (constraint, ask, spec, verification, check against quest, decision). The Record's registry is what runs; open: how the two are cohered in one registry.
3. **Buffer sizing.** The chain sizes buffers by the root of the sum of squares over two estimates; the schedule's own buffers still use the halving rule. Open: which governs, or whether a supercell's people set them.
4. **The leverage rule's constants** (1.5, 1.5, three days, fourteen days, a quarter for unknown) are assumptions; the evidence that tunes them is the Calculated-against-Discerned difference.
5. **Free float for cards with external successors,** and how a fixed-date node's own uncertainty enters the buffer, are unspecified.

## Not yet built

- Publishing who the drum is, each season.
- Measuring the Calculated-against-Discerned difference that tunes the leverage rule.
- The system path's broadcast format (what a supercell publishes back, how often, signed by whom), named in principle and not yet a type.

*Concepts: [[Critical Path]] · [[Float]] · [[Data Date]] · [[Milestone]] · [[Season]] · [[OmniSpection]] · [[Capacity]] · [[Load]] · [[Resource Leveling]] · [[Bottleneck]] · [[Buffer]] · [[Throughput]] · [[Last Planner System]] · [[Networks of Commitments]] · [[Committor]] · [[Sighting]] · [[Cell]] · [[Player+]] · [[The Kit]].*
