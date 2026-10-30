---
title: Index — The Architecture
description: The map of the architecture set (00–17), the code and its tests, the kit pages and design briefs, and a glossary of the parts.
---

# Index — The Architecture

*The map of the set: every document in one line, every file of the code with what it is and what tests it, the kit pages and the design briefs, the contracts, and a glossary of the parts. A reader new to the set starts with [[10 — The Reviewer's Guide (Architecture, 2026-10-24)]], §2.*

## 1. The documents

| Doc | Title | In one line |
|---|---|---|
| 00 | [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] | The whole in one view: a layered part of the LIØNSBERG System through which Living Intelligence and Artificial Intelligence play the Great Game together, holon by holon, with no center but ØNE; six layers over one record, ten invariants, what ships in 3.8.0 and what comes after |
| 01 | [[01 — The Record (Architecture, 2026-10-24)]] | The ground layer every other layer reads and every number can be rebuilt from: holons as folders, the event line, canonicalization, keys, admission, the paper rule, clones, consent for one act, supersession, elision, audience, replication, the causal fold, "as of" and its known limits, the paper floor |
| 02 | [[02 — The Membrane (Architecture, 2026-10-24)]] | The outermost layer, deciding what passes into a holon and out; it governs who may see and reach, never what is true: the private network, the forge and its accounts, audience by container, publication, postures, vouching, the public door, the keeper of the membrane |
| 03 | [[03 — The Game Engine (Architecture, 2026-10-24)]] | The calculating layer, pure functions over a holon's record that a person with a pencil could reach on one sheet: the fold, the schedule in full, across holons, what is owed, commitments kept, The Deal, the Turn, the ledger, the Score, the state, the paper floor, what is refused and what is not yet built |
| 04 | [[04 — The Player+ Agent (Architecture, 2026-10-24)]] | The operator of the Supersuit: the person plays, the agent serves; Roles against offices, identity, delegation, the offices as skills (the attention gate and the push among them), pull-first cueing, day one, the firewall by construction, conformance, how agents talk, how the kit improves, clones as their own actors |
| 05 | [[05 — The Proxy (Architecture, 2026-10-24)]] | The layer between the agent and the models: routing by the house's policy, `route` and `discern` lines under the same keys (an agent's `note` apart), never bodies, the council, privacy, the ladder of sovereign inference, the open question of agent messaging |
| 06 | [[06 — The HUD (Architecture, 2026-10-24)]] | The views of the ICE, holding no data of their own: The Deal as hero and never the only door, the attention gate on interruptions, three layouts as sorts of one state, every view and what it reads (Threads and Mail; the Board folded into the Chain), the bar for the working surface, the Room as the collaboration surface, the first door, the act path, accessibility |
| 07 | [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]] | Holons of one house and of many on one record by the same means, no holon commanding another: joining, what crosses, ball-in-court, one home and many aliases, the floor, the same calculation at every scale, mapping other houses' designs, leaving |
| 08 | [[08 — Security and Sovereignty (Architecture, 2026-10-24)]] | Sovereignty is holonic; reading is the attack surface and capability is not authority: the trust model, sixteen threat classes, the structural answers, what remains exposed, a house's hygiene |
| 09 | [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)]] | Every design decision the documents and the code embody, one row each, with its reason, its alternatives, its status and where it lives; what is open |
| 10 | [[10 — The Reviewer's Guide (Architecture, 2026-10-24)]] | The Guild's guide: reading in an hour, running everything, claims against evidence, what is unbuilt and exposed, the open questions, the improvement loop, the review bar (the design standard's sheet for the surface) |
| 11 | [[11 — Navigation of Reality — Sightings, Elevation and the Ladders (Architecture, 2026-10-24)]] | Every Player+ a navigator: Sightings written where they were seen, elevated by consent one level at a time into the shared map of reality; decisions made at the lowest holon able to make them well, climbing as a request for guidance or an escalation |
| 12 | [[12 — The Roadmap — Potential Future Features (2026-10-24)]] | Candidates raised in design, kept so they are neither lost nor built before their time; the surface being rebuilt to the bar, in order, and measured by the surface studying itself |
| 13 | [[13 — Mail, Reach and Identity (Architecture, 2026-10-24)]] | Every hypothesis on mail, reach and identity traced: the claim, its status, where it lives, what would settle or falsify it |
| 14 | [[14 — The Chain Before the Single Worker (Lesson and Structure, 2026-10-25)]] | Why a chain of work must never wait on one worker, shown by a build that waited forty minutes on one; the four structural changes (a contract before a dependency, minutes beside cost and the overrun watch, the deck as the instrument, a separate eye on the arrangement) and the practice that follows |
| 15 | [[15 — The Box — Bounding an Agent's Work on the Chain (First Principles, 2026-10-25)]] | How long an agent may run alone, from first principles: the unit is the handback, not time; what is bounded is variance (novelty, checkability, reversibility, capability); observation replaces check-ins; the box is the float and the watch is the buffer (the engine rule proposed, not yet built); human attention is the drum; the practice; what the Engine does not yet do; the open questions |
| 16 | [[16 — Rate Times Yield — the Claim, the Minimum, the Measure and the Experiment (2026-10-25)]] | Whether a person with an agent in the Game does a hundredfold more of the right work: useful throughput is rate times yield, a supersuit raises rate and the Game raises yield; the five axioms of the box and the two speeds in brief; what the harnesses leave out (the chain); the estimate in words; the cap of what is not sped up; the minimum set; the measure as the Game unfolds; the experiment the first twenty can run |
| 17 | [[17 — The Layers — How the Kit Is Built, Improved and Shipped (Architecture, 2026-10-29)]] | How what a Player+ receives is made and shipped: the release stack (the PKAI base, Player+, the LIØNSBERG layer, the Game Engine, what comes next) apart from the runtime stack; we run what we ship, as checks that can fail; each layer's version, contract, tests, changes and keeper; a kit release as a manifest; pull never push, with a ledger of differences; one gate per kit release |
| — | Index — The Architecture (this page) | The map |

## 2. The code map

The engine's tests are in `engine/tests/` and run by discovery: `cd player-plus/engine && python3 -I -m unittest`. The HUD's own proofs are in `hud/fixtures/` and run by `python3 -I hud/fixtures/test_strings.py`. A class named here is `file.Class`.

### 2.1 The contracts and the state

| File | What it is | Proven by |
|---|---|---|
| `engine/SCHEMA.md` | The record contract (schema v1): the holon's layout, the event line, the type list, items, elision, the functions, the layers, the paper floor. Every part reads it | the whole suite; conformance |
| `engine/STATE.md` | The HUD's contract: the shape of `state.json` (holons and their "as of", cards with their schedule, commitments, owed, kept, The Deal, rooms, roles, the Turn's depths) | `test_game.EngineOnTheFixtures`; conformance (a) |
| `engine/types.json` | The type registry, as data: each type's fields, the item it folds into, its transitions, and whether it is human-only (twenty-five are) | `test_record` (the fold reads it); `test_record.TestFold.test_every_type_appears_in_fixtures` |

### 2.2 The Engine and the Record

| File | What it is | Proven by |
|---|---|---|
| `engine/record.py` | The Record: canonicalize, sign, verify, append, read, fold, elide, export; a library and a command line | `test_record` (ids, chains, fold, links and claims, delegation, audience, untrusted, injection, signing, export, CLI) |
| `engine/holon.py` | Make a holon (`init`, `--adopt` for an existing home), let in a person (`admit`) or an agent (`affirm`, `--prime` for a clone), join a cell, publish to it, pull from it, list what is held; keys in `--key-dir`; never pushes | `test_record.TestHolon` |
| `engine/schedule.py` | The schedule: the two passes, float, the critical path, constraints, baselines and variance, codes, load and local leveling, across holons, critical chain and the drum, earned value, the Gameclock and its moons, `rhythms()` | `test_schedule` (every class); conformance (b) |
| `engine/gamecore.py` | Shared helpers: reading the fold's shape, live delegations, who may act, commitment status | through `test_game` |
| `engine/deal.py` | The Deal: order, the leverage rule, sizing to minutes, authority, renderings (Markdown, JSON, paper) | `test_game.TheDeal` |
| `engine/owed.py` | What is owed, per actor or holon; untrusted lines as proposals | `test_game.Owed` |
| `engine/kept.py` | Commitments kept per holon and actor over a window; the gap; the learnings | `test_game.Kept` |
| `engine/turn.py` | The Turn at the depth the day calls for (daily, lunar, seasonal; weekly where kept) | `test_game.Turn` |
| `engine/ledger.py` | The TEA ledger: balances, witness tiers, never convertible; discernment totals | `test_game.Ledger` |
| `engine/rooms.py` | Who is in each room, its posture, what was offered and agreed; the Roles in each holon | `test_game.Rooms` |
| `engine/attention.py` | The person's attention budget from their own `attention` lines, and the gate on what may interrupt them now | `test_game.Attention` |
| `engine/push.py` | The Push Protocol v1.1: the field of stake the sender's agent proposes, the person's changes marked in `push_by`, the receiver's recomputation and weight, calibration per Living Intelligence | `test_game.Push`; `test_mail.TestPush` |
| `engine/mail.py` | Mail inside the private network as a carrier, never a second truth: `fetch`, `carry`, `send` (only on the person's own Send), `badge`, `carried`; the carried store at `<hq>/.carried/`; reach read from the holon | `test_mail` |
| `engine/bodies.py` | An agent's bodies (the prime and its clones), the desk, and what each body cost | `test_game.Bodies` |
| `engine/ladder.py` · `engine/sightings.py` | Where a decision is made and the questions that climb; a holon's triage of what its players saw | `test_game.Navigation` |
| `engine/engine.py` | The one command line: `state`, `deal`, `owed`, `kept`, `turn`, `ledger` over every holon held | `test_game.EngineOnTheFixtures`; conformance (a), (f) |
| `engine/conformance.py` | The six admission checks, network off, in a temporary copy | itself a check; run it |
| `engine/fixtures/make_fixtures.py` · `engine/fixtures/hq/` · `engine/fixtures/export-first-cell-names-hidden.jsonl` · `engine/fixtures/ids.json` | A deterministic sample: a home and one cell, three actors, every first-set type, a supersede, an invalid agent line, an untrusted line, an injection line; the names-hidden export | `test_record` builds them in a temporary folder; `test_record.TestExport` |

### 2.3 The Proxy

| File | What it is | Proven by |
|---|---|---|
| `engine/proxy.py` | The local proxy: routes by policy, records `route` and `discern` lines, never bodies; `serve`, `routes`, `report` | `test_proxy` (against a fake upstream on loopback) |
| `engine/routes.json` | The sample policy, as data; the private rule first; the council off | `test_proxy.TestRouteSelection.test_samples_load_and_drop_comments` |

### 2.4 The HUD

| File | What it is | Proven by |
|---|---|---|
| `hud/serve.py` | The tiny local server: `GET /state`, `GET /stream`, `POST /act`, `DELETE /act/<id>`, `POST /publish-sheet`; the undo window; the refusals | `test_serve` (what a pull can bring in: nothing written through a link, a home act stays home) |
| `hud/index.html` · `shell.js` · `state.js` · `card.js` · `deal.js` · `queue.js` | The static surface: the shell, the state store, the card face, The Deal, the Queue | the truth proofs in `hud/fixtures/` (`test_truth.mjs` and its siblings), in a headless browser when one is present |
| `hud/tokens.css` · `base.css` · `card.css` · `deal.css` · `print.css` | Tokens, base styles, the card, The Deal, print | no automated test |
| `hud/strings.json` | Every string the HUD shows | `hud/fixtures/test_strings.py` (the strings gate) |
| `hud/fonts/` | Vendored fonts with their licence | — |
| `hud/fixtures/` (`fresh`, `empty`, `stale`, `unreadable`, `names-hidden`, `large`, and their maker) | States to run the surface against: `serve.py --fixture <name>` | by eye |

## 3. The kit pages, skills and design briefs

**Design briefs and the design standard** (in `hud/`): `DESIGN-THE-BAR.md`, the design standard for the working surface (what the best look and feel like, how it lands in each view, where the mythos lives, the surface studying itself, and the sheet of checks in §5 that every view is scored against); `DESIGN-ATTENTION.md` (the attention budget, the one queue, the gate, binding over the other briefs on attention); `DESIGN-MAIL.md` (Threads and Mail, the carried store, the push); `DESIGN-DOCK.md`, `DESIGN-BODIES.md` and `DESIGN-WAY-IN.md` (the dock, the Bodies view, the way in); `DESIGN-TALK.md` (the Talk); `DESIGN-PHONE-DOOR.md` (the phone door, spoken over TLS); `DESIGN.md`, the HUD's brief (the one idea, the wearer's minutes, three layouts, every view composed, tokens, voice, accessibility and the paper mirror, the review bar); `DESIGN-ROOM.md`, the Room's brief (one table, three inks; a room's hour scene by scene; attention; agents in the Room; across houses; the review bar), binding over the HUD brief's Room sections.

**The seven skills of the record** (in `skills/`, each with `SKILL.md`, `LINEAGE.md`, `LICENSE.md`): `the-record` (with `day-one.md`, the first hour) · `the-deal` · `the-turn` · `join-a-cell` · `witness-a-commitment` · `a-gathering` · `the-proxy`. The kit's other skills are indexed by the kit itself.

**The bookshelf's practice pages** (in `bookshelf/the-record/`): `The Record — How Your Holon Remembers.md` · `The Deal.md` · `Joining a Cell.md` · `The Game Engine — By Pencil.md` · `Commitments Kept.md` · `Constraints — Time, the Art and the Science.md` · `The Test Holon — A Simulation on the Forge.md`. The concept pages they link to live in the kit's Field (`bookshelf/the-field/`).

## 4. Glossary of the parts

One line each. The concept pages, where they exist, live in the kit's Field.

| Part | In one line |
|---|---|
| [[Holon]] | A whole that is also part of a larger whole; here a folder, usually a git repository, that keeps its own record: a person's home, a pair, a [[Cell\|cell]], a room, a body of bodies |
| [[Actor]] | Whoever signs a line: a person (`person:`) or an agent (`agent:`) |
| [[Actor\|Living Intelligence]] | A being or a group of beings; holds every Role and Office, gives every yes, commits and witnesses, and may delegate to agents |
| [[Artificial Intelligence]] | Serves Living Intelligence; an agent acts within a delegation and never holds a Role |
| [[The Record\|Record]] | A holon's append-only lines, one file per Actor; the ground every other layer reads and can be rebuilt from |
| [[Event]] | One signed statement by an Actor: one line, identified by the hash of its content; in live text, a settled line |
| Item | What the fold computes from lines (a card, a commitment, a thread, a delegation, a TEA entry and the rest); never stored |
| [[Work Card]] | A unit of work, born by a `card` line: its holder, minutes, by-when, stage and state, its predecessors and successors as links |
| [[Commitment]] | A `commit` by a Living Intelligence: the card, by when, the conditions, the size and the witness; the keeper claims kept, the named witness verifies |
| Thread | A conversation anchored to a line or a card; a thread anchored to nothing is a conversation, and that is allowed |
| [[Delegation]] | A `delegate` line by a person to their agent: which types, which holons, until when; ended by `revoke`; or once, for a single act |
| [[Witness]] | A fair witness verifies a kept commitment or spent TEA; never the item's own; the named witness when one is named |
| Membrane | Who may see and reach a holon: the private network, the forge's accounts, audience by container, and publication |
| Audience | The widest reach a line may have: `holon` · `members` · `commons` · `public`; within a holon it only narrows |
| Publication | A person's `publish` line widening the lines it names; the lines are copied whole, still signed, into the receiving holon's `published/` |
| [[Elision]] | Hiding a field behind its salted digest so the line's id still holds; a names-hidden export hides every name |
| Ledger | The TEA ledger: balances per actor, holon, card and stream; witnessed; never convertible into money, into one another, or into rank |
| TEA | Time (in minutes), Energy and Attention (each 1 to 10), given toward a card by the one who gave it |
| [[The Deal]] | The few Work Cards that need a person now, sized to their minutes; opens "Here's the deal." and closes with the standing question |
| [[The Turn]] | Looking at what was said against what was done, at daily, lunar and seasonal depths; the person finishes its lines and signs it |
| [[OmniSpection]] | Looking at the whole, continually and at varying depths: daily, at each new and full moon, at each seasonal turning |
| Gameclock | The nest of rhythms every holon shares: the season from turning to turning, two spans of 42 days, the moons, the week, the day; computed, never typed |
| [[Buffer]] | Time held before a milestone, half its chain's duration; consumed against chain complete gives the signal; reported, never imposed |
| Drum | The Actor on a chain with the least free capacity: the scarcest attention sets the pace |
| Proxy | The local layer between an agent and the models: routes by policy, records where each request went and the person's judgment, never a body |
| [[Discernment]] | A person's judgment on an inference or a draft (chosen, corrected, rated), recorded as a `discern` line |
| ICE | The Integrated Creation Environment: the surface the house owns (the HUD's views, the dock, the Room), with the Proxy beneath it; its primitive forerunner is the IDE |
| HUD | The views of the ICE: reads the folded state, writes only through the act path; three default layouts (Player, Cell steward, Room) |
| [[Room]] | A holon for a gathering; its record is what is settled there; the Room layout over it is the collaboration surface |
| Supersuit | The [[Player+]]'s bundle of Agent, Engine and ICE in one install, on the Player+'s own machine from day one |
