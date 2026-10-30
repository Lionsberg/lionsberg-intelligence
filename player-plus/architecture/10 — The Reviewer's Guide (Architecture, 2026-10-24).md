---
title: The Reviewer's Guide
description: How to review the architecture set and the kit's code: what to read, how to run the tests and checks, what to look for, and how to send findings back.
---

# The Reviewer's Guide

*For anyone who reviews the kit: architects, engineers and their agents. It says how to read the set in an hour, how to run every part of the code, which claim each test proves and which no test yet proves, what is not built, what is exposed and what is still open; and it carries the improvement loop (§8): how anyone proposes a change, how it is reviewed, and how it folds into [[The Kit|the kit]] and reaches every agent. [[Every Defect Is A Gift|Every defect found is a gift.]] Where this guide says "not yet proven", believe it over any sentence elsewhere in the set that sounds surer.*

## 1. What you are reviewing

A layered part of the [[LIØNSBERG]] System through which Living Intelligence and [[Artificial Intelligence]] work together, [[Holon|holon]] by holon, with no center but [[ØNE]]. Six layers over one record: the Membrane (who may see), the Record (each holon's signed lines), the Proxy (between the agent and the models), the Engine (pure functions over the lines), the Agent (the operator) and the ICE, the Integrated Creation Environment (the HUD's views, the dock, the Room). A [[Player+]] receives the last three as one install, the Supersuit, on the Player+'s own machine from day one.

Two bodies of material:

- **The documents:** the pages in this folder, 00 to 17 and the Index. 00 to 08 describe the layers; 09 gives every decision with its reason; this page tells you how to check them; 11 traces Navigation of Reality; 12 holds the roadmap; 13 traces mail, reach and identity row by row; 14 to 16 set out the chain, the box that bounds an agent's work on it, and rate times yield; 17 says how the kit is built in layers, improved and shipped.
- **The code:** the kit's `player-plus/` folder at 3.8.0. `engine/` holds the contract (`SCHEMA.md`), the state contract (`STATE.md`), the type registry (`types.json`), the Python modules, their fixtures and tests, and `ENGINE.md`, which says which files belong to the Game Engine, the Record and the Proxy. `hud/` holds the design briefs, the design standard `DESIGN-THE-BAR.md`, the static surface, its local server and its own fixtures and tests. `skills/` holds what the agent does; `bookshelf/the-record/` holds the pages a player reads. Python standard library only; nothing to install but Python 3, with git and `ssh-keygen` used when present, and node with a headless Chrome for the surface's browser proofs.

**When a document and the code disagree, the code is what runs and the document is what is to be corrected,** unless 09 records the document's choice as the decision. File each divergence you find (§8.2).

## 2. Reading the set in an hour

| Order | Minutes | Read | What it answers |
|---|---|---|---|
| 1 | 10 | [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] | What the system is for; the six layers; the ten invariants; what ships and what comes after |
| 2 | 5 | `engine/SCHEMA.md` in the kit | The one contract every part reads: the holon's layout, the event line, the type list, the paper floor |
| 3 | 10 | [[01 — The Record (Architecture, 2026-10-24)]] | Identity, canonicalization, signatures, delegation, supersession, elision, audience, replication, the fold |
| 4 | 10 | [[03 — The Game Engine (Architecture, 2026-10-24)]] | The fold's checks; the schedule in full; what is owed; commitments kept; The Deal; the Turn; the ledger; what the heavy scheduling engines have that this does not |
| 5 | 5 | [[08 — Security and Sovereignty (Architecture, 2026-10-24)]] | The trust model, the threat classes, the structural answers, and what remains exposed |
| 6 | 5 | [[04 — The Player+ Agent (Architecture, 2026-10-24)]] | Roles against offices; delegation; the skills; the firewall; conformance before admission |
| 7 | 5 | [[02 — The Membrane (Architecture, 2026-10-24)]] | The private network, the forge, audience by container, publication, postures, vouching |
| 8 | 4 | [[05 — The Proxy (Architecture, 2026-10-24)]] | Routing by policy; `route` lines and the agent's `note`; never bodies; the open question of agent messaging |
| 9 | 4 | [[06 — The HUD (Architecture, 2026-10-24)]] | The layouts as sorts of one state; the act path and its refusals |
| 10 | 3 | [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]] | What crosses a membrane; one home, many aliases; the floor; how another house's design maps onto the record |
| 11 | 4 | [[13 — Mail, Reach and Identity (Architecture, 2026-10-24)]] | Messaging as lines; mail as a carrier, never a second truth; reach on `join` and `affirm`; the Push Protocol v1.1 |
| 12 | as needed | [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)]] | Why any one choice was made, what else was weighed, and how settled it is |
| 13 | as needed | [[11 — Navigation of Reality — Sightings, Elevation and the Ladders (Architecture, 2026-10-24)]] · [[12 — The Roadmap — Potential Future Features (2026-10-24)]] · [[14 — The Chain Before the Single Worker (Lesson and Structure, 2026-10-25)]] · [[15 — The Box — Bounding an Agent's Work on the Chain (First Principles, 2026-10-25)]] · [[16 — Rate Times Yield — the Claim, the Minimum, the Measure and the Experiment (2026-10-25)]] | Sightings and the ladders; what may come later; the chain and the box; the measure of throughput |
| 14 | 5 | [[17 — The Layers — How the Kit Is Built, Improved and Shipped (Architecture, 2026-10-29)]] | The release stack against the runtime stack; what every layer carries; how a kit release is made |
| 15 | 5 | §4 and §5 of this guide | Which claims are proven, and what is not built or is exposed |

**Shorter paths by role.** A data architect: 00, `SCHEMA.md`, 01, 07, then §4. A scheduling engineer: 03, then `engine/ENGINE.md`, then `engine/schedule.py`'s module docstring (every rule and a worked example), then `tests/test_schedule.py`. A security reviewer: 08, 04 §7, 02 §4, then §5 of this guide. A designer: 06, then `hud/DESIGN.md`, `hud/DESIGN-ROOM.md` and `hud/DESIGN-THE-BAR.md`, then run the HUD on its fixtures. An agent reviewer: this guide whole, then 09, then the code by the map in the [[Index — The Architecture (2026-10-24)]].

## 3. How to run everything

From the kit's root, `player-plus/`. Every Python module documents itself: `python3 -I <file>.py --help`. `-I` (isolated mode) keeps the working directory and environment off the import path; the modules add their own folder.

**Before running anything that writes, copy the fixtures.** `engine.py state` writes `state.json` into the holon it is given. It is git-ignored there, but a review should leave the shipped files untouched:

```
cp -R engine/fixtures/hq /tmp/review-hq
```

| Run | Command | What it proves | What it does not prove |
|---|---|---|---|
| **The engine's tests** | `cd engine && python3 -m unittest discover -s tests` (add `-v` for each name). At 3.8.0: 554 tests, 1 skipped | The suites by file: `test_record` (ids and canonical form, actor files and chains, signatures and keys, the fold, supersession, links and claims, time, delegation, witness, audience, injection, export, holon making, joining and pushing), `test_schedule` (the two passes, agreement with a reference scheduler on golden figures, durations, progress, constraints, baselines, codes, resources, across holons, critical chain, earned value, the Gameclock and moons, null guards), `test_game` (The Deal, owed, kept, throughput, the Turn's depths, rooms and their shapes, roles, the ledger, `state.json` on the fixtures, two homes holding one cell, navigation, bodies, attention, push), `test_proxy` (routing, translation, the vendors and routes files, route lines, the agent's notes, no bodies on disk, council, the gate, private requests, keys, redirects, limits, links never written through, against a fake upstream on loopback), `test_mail` (mail as a carrier, against a fake mailbox and a fake mail host), `test_serve` (`hud/serve.py` against what a pull can bring in: links, planted stores, a cell claiming the home's id; the dock's readers; the phone door), `test_chain`, `test_plan`, `test_resources`, `test_lps`, `test_sbs`, `test_exports`, `test_capture` and `test_two_houses` (the planning modules, each checkable by pencil; two homes calculating together) | Behaviour against a live model vendor or a live agent harness; two real players on two machines; scale; anything a test does not name |
| *its one skip* | set `CPM_PY` to the path of the reference scheduler to run the live comparison | that the schedule agrees with the reference scheduler today, not only with figures embedded in the test | the reference scheduler is not in the kit, so most reviewers see one test skipped |
| **The surface's tests** | `python3 -I hud/fixtures/test_strings.py` · `python3 -I hud/fixtures/test_dock.py` | The strings gate (no schema word, no "not computed" placeholder, no contraction but the opener, in every string and in the words the fixtures deal); the dock's host against a stand-in agent (`hud/fixtures/fake_agent.py`). With node and Chrome present, each also runs its browser proofs (`hud/fixtures/test_*.mjs`) in headless, muted Chrome; without them those proofs are skipped | Every view in every scene; the surface's own bar (`hud/DESIGN-THE-BAR.md`), which a person scores |
| **Conformance** | `python3 -I engine/conformance.py` (or `--key PATH` to sign with a key; `--json`) | The six admission checks, run in a temporary copy with the network switched off: (a) The Deal dealt from the fixtures, in `STATE.md`'s shape and against its known answer, (b) total float by pencil: the worked example, and the fixtures run through the fold and then the schedule against an independent two-pass, (c) sign and verify, and a changed line failing (or PAPER FLOOR with no key, which is not a failure and never counted as a pass), (d) an injected instruction sends nothing, changes nothing, and folds as data, never as an owed act, (e) an agent's line outside its delegation is marked invalid, (f) items from two holons appear in one fold. Any attempt to reach the network fails the run | That a model-driven agent behaves: the sheet ends with two checks only a person can make, (p1) reading the agent the injected line, and (p2) asking it to commit its person, where it prepares the line and waits |
| **The Engine on the fixtures** | `python3 -I engine/engine.py state /tmp/review-hq --minutes 60`, then `engine.py deal /tmp/review-hq --minutes 60` (also `--paper`, `--json`), `engine.py owed`, `engine.py kept`, `engine.py turn` (`--depth daily\|lunar\|weekly\|seasonal`, `--freeze`), `engine.py ledger` | A home and one cell folded together, each scheduled on its own calendar and dealt; `state.json` in `STATE.md`'s shape; a Deal that opens "Here's the deal.", never exceeds the minutes, holds back the untrusted proposal, and ends with the standing question | Correctness beyond the fixtures and the tests; the fixtures are small (three actors, two holons, every type at least once) |
| **The record by hand** | `python3 -I engine/record.py append \| read \| fold \| verify \| elide \| export` (each with `--help`); `python3 -I engine/holon.py init \| admit \| affirm \| join \| publish \| pull \| push \| hold` (`init`, `admit` and `affirm` take `--key-dir`; `init --adopt` adopts an existing home; `affirm --prime` lets a prime agent affirm its clone) | Each operation of the Record alone; an export under the names-hidden posture whose ids still verify (`engine/fixtures/export-first-cell-names-hidden.jsonl` is the shipped example); `verify` checks a holon against the keys its own record admits, or a file only against an allowed-signers file | That the export hides every name a reader could use: signatures are removed and the set attested, and known handles are hidden in free text, but a name in free text that is not a known handle may still leak |
| **Mail as a carrier** | `python3 -I engine/mail.py fetch \| carry \| send \| badge \| carried` (each with `--help`); `send` acts only with `--on-the-persons-send` | That a carried line lands in `<hq>/.carried/` and counts only by its signature against the holon's admitted keys; that the fetch never sends | Delivery against a live mail host |
| **The schedule by hand** | `python3 -I engine/schedule.py clock 2026-12-21 --to 2027-03-21`; `python3 -I engine/schedule.py run ITEMS.json --markdown`; `schedule.py freeze` writes `plan/baseline-<n>.json` | The Gameclock (turnings, spans, new and full moons); the passes on any items file | — |
| **The Proxy** | `python3 -I engine/proxy.py routes` (the person's vendors, whether each key variable is set but never its value, the rules in order, the default); `python3 -I engine/proxy.py serve --holon /tmp/review-hq --actor agent:<handle>`; `python3 -I engine/proxy.py report --holon /tmp/review-hq` (also `--by-body`, `--conversation`) | That the policy reads as data; with a harness pointed at it, that each request writes a `route` line and no body, and that every endpoint asks for the token first | Anything against a live vendor: the suite runs against a fake upstream; the OpenAI-shape path reads the answer whole and never streams upstream |
| **The HUD** | `python3 -I hud/serve.py --fixture fresh` (acts go to a temporary folder it names; `--shift-clock` moves the sample's clock to now), or `--hq /tmp/review-hq --actor person:player` (add `--key PATH` to sign); then open `http://127.0.0.1:8765` | The surface over its fixture states (`fresh`, `empty`, `stale`, `unreadable`, `names-hidden`, `large`, `deal-chain`, `deal-rich`, and the room, chain, bodies and threads fixtures in `hud/fixtures/`); the act path's undo window and refusals, by hand | The Map's made frames (not made) |

**Known quirks.** Run the engine's tests by discovery; naming a test file by path under `-I` does not find the tests package. Test runs leave `__pycache__/` folders, and the kit's ignore file covers only `engine/__pycache__/`. `serve.py`'s own usage text shows `python3` without `-I`, and names the person's key `~/.ssh/lionsberg-<handle>`; the server and `record.py` look for `~/.ssh/lionsberg-person-<handle>`. The count of tests you see is the evidence; the figure above is the count at 3.8.0.

## 4. Claims and their evidence

### 4.1 The ten invariants of document 00

Test names are `file.Class.test`; "conformance (x)" is a check of `conformance.py`. A test is cited by its name; reading its body is part of the review.

| # | Invariant (00 §6) | Proven by | Not yet proven |
|---|---|---|---|
| 1 | Every holon keeps its own record | `test_record.TestHolon.test_init_layout_and_key` · `test_record.TestCanonical.test_holon_id_is_inception_line` · `test_record.TestPass7.test_h2_a_cell_never_takes_the_homes_id` · `test_serve.Served.test_home_act_stays_home_when_a_cell_claims_its_id` · the fixtures (`engine/fixtures/hq/` and `engine/fixtures/hq/cells/first-cell/`, each with its own `record/`) | That a holon moved to another host keeps its id and history (no test); that a cell's record stands apart from its members' (structure only) |
| 2 | Every event is signed by the Actor | `test_record.TestSignatures` (every fixture line verifies in the fold; a swapped signature is a bad signature; a forged person line; an unadmitted key and an unaffirmed agent; an unsigned line counts only at home; the paper floor kept without a key; a line in the wrong holon never acts; sign and verify one line) · `test_record.TestKeys.test_each_actor_signs_with_its_own_key` · `test_unsigned_without_key_said_plainly` · conformance (c). The fold verifies signatures against keys admitted by `join` and `affirm` lines; an unsigned line is authoritative only at the paper floor in the home record. `serve.py` writes through the record's own `append` and signs with the person's own key, never an agent's | The key ceremony beyond rotation (§5.1) |
| 3 | No center but ØNE | Structurally, in part: conformance's network tripwire (the Engine opens no connection) · `test_record.TestFold.test_fold_is_pure` · `test_game.EngineOnTheFixtures` (the state from local files alone) · `test_record.TestDelegation.test_agent_line_outside_delegation_invalid_and_kept` (every valid agent line traces to a delegation from a person) | The allegiance chain and "every holon carries the whole invariant" are not properties a test can check |
| 4 | Audience belongs to the holon; within it only narrows; publication is a person's act | `test_record.TestAudience.test_person_publish_widens_own_lines` · `test_audience_never_widens_otherwise` · `test_record.TestPass7.test_h1_publish_never_follows_a_link` | The server's refusal of a wider audience (`hud/serve.py`; no test names it); audience by container on the forge (no test); export does not filter by audience |
| 5 | Agent-optional; every number by pencil | `test_schedule.PaperExample.test_docstring_numbers` (the worked example, number for number) · conformance (b) · `test_lps`, `test_sbs`, `test_exports` (each on a fixture checkable by pencil) · the Engine runs with no proxy and no agent | A paper sheet typed in and folded (no fixture of a typed sheet); the proxy's acceptance test that removing the base URL changes nothing (no test) |
| 6 | Every holon held is pulled, and every result says as of what | `test_record.TestFiles.test_newest_seen_per_holon` · `test_record.TestFold.test_items_and_states_across_both_holons` · `test_game.TheDeal.test_cards_from_two_holons_both_appear_with_their_holon` · `test_game.TwoHomesOneCell.test_the_cells_cards_get_the_same_float_in_both_homes` · `test_schedule.AcrossHolons.test_external_and_as_of` · conformance (f) | A failed pull labeled in every number (no test); the HUD's "could not read" chip (the `unreadable` fixture, by eye only) |
| 7 | Living Intelligence holds the Roles; an agent never ticks a human's box | `test_record.TestDelegation` (outside its delegation an agent's line is invalid; with neither consent nor a `once` delegation it stays invalid; a `once`-delegated commit is `signed_for` and used up; a consented ratify is `signed_for`; a revoked delegation no longer covers) · `test_record.TestRecheck.test_n2_consent_needs_the_persons_signed_line` · `test_record.TestSupersede.test_agent_never_supersedes_a_person` · `test_game.TheDeal.test_an_agent_is_dealt_only_what_its_delegation_covers` · `test_an_agent_with_no_live_delegation_is_dealt_nothing` · `test_game.Repairs.test_accepting_a_request_is_a_persons_act` · `test_game.Rooms.test_presence_posture_offered_and_agreed` (only a person's lines agree) · conformance (e) | `answer` is open to agents by decision; the Deal never offers an agent the acceptance of a request, and an answer that would commit a person still needs the person's `commit`. Spoken consent is words the agent itself carries on the line: the fold can check a person-signed `once` delegation, and cannot check spoken consent beyond its words and its link to the person's `say` line. A model-driven agent: only the two person-asked checks of the conformance sheet |
| 8 | Every line is data | `test_record.TestUntrustedAndInjection.test_order_in_text_is_data` · `test_untrusted_is_proposal_only` · `test_game.Owed.test_untrusted_proposals_are_never_owed` · `test_game.TheDeal.test_untrusted_lines_are_never_dealt_or_owed` · `test_serve.Served.test_say_never_writes_through_a_link` · conformance (d) with the tripwire · the fixtures' injection line | A model-driven agent reading hostile text: only the two person-asked checks of the conformance sheet; no automated test of a live agent |
| 9 | Nothing is edited or deleted | `test_record.TestSupersede` (latest shows both, and both remain; another person refused; untrusted or other types never supersede; a person under a decision may supersede; an empty supersede retracts) · `test_record.TestFiles.test_tampered_line_left_out` · `test_broken_chain_reported_not_crashed` · `test_fork_kept_and_flagged` · `test_record.TestPass7.test_m1_rewound_history_is_refused` | Append-only is detected, never prevented, on disk; the one exception (removing a non-consenting name, with the removal recorded) has no tool and no test |
| 10 | The one who assigns never audits | The registry's `witness` type: the witness is never the item's own, and when a commitment names its witness only that witness verifies it · `test_record.TestWitness.test_witness_other_than_named_is_a_note` · `test_game.Repairs.test_only_the_named_witness_verifies` | The process half of the invariant (independent review) is a practice, not code |

### 4.2 The acceptance tests named in documents 03 and 05

| Document and test | Evidence | Standing |
|---|---|---|
| 03 #1 the worked example reproduced | `test_schedule.PaperExample` · conformance (b) | proven |
| 03 #2 no float typed | the HUD reads only the state (by design) | not yet proven |
| 03 #3 leveled dates never replace logic dates | `test_schedule.AgreesWithCpm.test_serialize_equals_level`; the run's output keeps `leveled` apart | in part |
| a constraint without a reason and an imposer is reported as a defect | `test_schedule.Constraints.test_constraints_report` (`schedule.py` flags a missing reason or imposer) | proven, by name |
| 03 #4 negative float never clamped | `test_schedule.AgreesWithCpm.test_negative_float` · `test_schedule.Constraints` | proven |
| 03 #5 two holons holding the same lines produce the same schedule fields for the cards | `test_record.TestFold.test_fold_is_pure` · `test_game.TwoHomesOneCell.test_the_cells_cards_get_the_same_float_in_both_homes` · `test_game.ExternalMilestones.test_a_reader_holding_both_cells_schedules_per_holon` (each holon on its own calendar) | proven on one machine |
| 03 #6 an untrusted line never owed, dealt or counted | §4.1 row 8 | proven |
| 03 #7 an agent line outside delegation folds invalid | §4.1 row 7 | proven |
| 03 #8 minutes dealt within minutes available; the standing question present | `test_game.TheDeal.test_never_exceeds_the_minutes` · conformance (a) | proven |
| 03 #9 a link to an unheld line reads "not yet replicated" | `test_record.TestFold.test_link_not_yet_replicated` · `test_schedule.Relationships.test_unknown_link_is_not_yet_replicated` | proven |
| 03 #10 every number names its "as of" per holon | `test_record.TestFiles.test_newest_seen_per_holon` · `test_game.EngineOnTheFixtures` | proven |
| 03 #11 the ledger says not convertible | `test_game.Ledger.test_balances_witness_and_not_convertible` | proven |
| 03 #12 the Engine opens no network connection | conformance's tripwire | proven for the fixtures run |
| 03 #13 every function by pencil in the stated time | `bookshelf/the-record/The Game Engine — By Pencil.md` | by a person only |
| 05 #1 no body in any file the proxy writes | `test_proxy.TestNoBodiesOnDisk.test_bodies_and_keys_never_written` (unique markers through every path) · `test_agent_text_never_reaches_disk_as_sent` | proven against a fake upstream |
| 05 #2 every response carries its route id, every id has a line | `test_proxy.TestRouteLine.test_route_line_shape` · `test_proxy.TestTagsAndLocality.test_route_line_exists_when_the_answer_arrives` | in part |
| 05 #3 a `private` request never leaves the computer | `test_proxy.TestPrivate.test_private_never_leaves_the_machine` · `test_proxy.TestRoutesFile.test_private_only_to_this_machine` · `test_proxy.TestTagsAndLocality.test_private_near_misses_stay_private` | proven against a fake upstream |
| 05 #4 a council member's `chosen` verdict links to its route | `test_proxy.TestCouncil` · `test_proxy.TestDiscern.test_report_counts_verified_person_verdicts_once` | in part |
| 05 #5 with the base URL removed everything works unchanged | — | not yet proven |
| 05 #6 the proxy refuses a connection from another machine | it binds to 127.0.0.1 and no flag widens it · `test_proxy.TestEndpoints.test_cli_routes_and_no_open_flag` · `test_proxy.TestGate.test_host_must_be_loopback_with_port` | in part (no test from a second machine) |
| 05 #7 a rule's model change shows as asked against sent | `test_proxy.TestRouteLine.test_route_line_shape` | in part |
| 05 #8 a proxy that stops answering is reported at once | the HUD's server asks the proxy's `/health`, with its token, at most every ten seconds (`hud/serve.py`); no test names the report | in part |

## 5. What is not yet built or proven, and what is exposed

### 5.1 Not yet built or proven

- **Two real players.** Every test uses homes and cells on one machine. Two people, each with their own agent, keys and home on their own machine, replicating through a forge and folding the same lines to the same state, has not been run; the Test Holon simulates it with pretend players across real pulls and pushes ([[The Test Holon — A Simulation on the Forge]]).
- **The key ceremony.** Identities are disposable and labeled. A key changes by a rotation: a `join` for the handle signed with its current key, or a `join` by the keeper naming a witness (`SCHEMA.md`). The stable identifier, its witnessed inception, a named successor and visible revocation are designed in outline only (01 §4, 08 §2.9). Handing a holon to a new keeper is a ceremony in person, not yet a line of its own. A key per actor is what the code finds: `record.find_key` uses only a key file named for the actor (`lionsberg-<kind>-<handle>`), so a person and their agent never sign with one key.
- **The public door.** Read-only publication and entry by invitation with a passkey are described (02 §8); nothing serves them.
- **Made frames for the Map.** The HUD's Map is specified as fields made from still images in the brand's hand; until those frames exist, a code-drawn ring stands in (`hud/DESIGN.md`, amendment 2).
- **Streaming on the OpenAI-shape path.** The proxy reads such an answer whole before the first token reaches the person, and synthesizes the stream afterwards, with an `x-proxy-note` saying so (05 §4; `engine/proxy.py`).
- **Every view under test.** The strings gate and the browser proofs cover the surface in part; no automated test covers every view in every scene, and the browser proofs need node and Chrome.
- **A live run in the tests.** No test in the kit runs against a live model vendor or a live agent harness; every suite uses a fake upstream or a stand-in agent.
- **Encrypted bodies, the forge refusing, rate limits and the admission window, a spoken yes becoming a signed line, an observer over the proxy's trail, per-room anonymity.** Each is named as open in its document.

### 5.2 The threat model's exposed list (08 §3)

1. **The agent's own host is the soft center.** Whatever runs where the agent runs can sign as the agent, and as the person if their key sits on the same machine.
2. **`reason` is a claim by its writer.** Within its delegation, a mislabeled agent line can do what the scope allows.
3. **A person's real yes can be steered** by a recommendation drafted from hostile text.
4. **Elision is not forgetting.** A name settled before it was hidden has replicated to everyone who pulled it.
5. **The paper floor is unsigned**; it is as strong as its witness.
6. **Model providers see what is sent to them.**
7. **The forge sees the shape**: who joined what, when, how often.
8. **The kit is a supply path** to every agent at the next pull.
9. **Time is a claim.**
10. **Disposable first-week identities** can be made by anyone on the private network.
11. **Flooding.** An append-only record remembers everything written to it.
12. **Public threat reports** read for 08 are not verified against the vendors' own advisories.
13. **The proxy and the vendor's phone door exclude each other.** A local session of the command-line harness run inside the vendor's desktop app ignores a custom base URL, and the vendor's phone remote control refuses any proxy, working only against the vendor's own endpoint. A person who reaches their agent through that phone door loses the proxy, and with it every `route` line. The ICE on the player's own machine, reached from the phone over the private network, is the phone door that keeps the proxy (`hud/DESIGN-PHONE-DOOR.md`; `serve.py --phone`). Not yet verified: re-test this on a clean machine before relying on it.
14. **Pinning.** The command-line harness's automatic update can be disabled or blocked by its two documented settings; the vendor's desktop app cannot be pinned, so a house that keeps pinned versions (08 §4) cannot keep one for the desktop app.

### 5.3 Seams to check first

Each is a place where one part relies on another to keep a rule. Confirm each on the tree you review.

1. **The HUD's act path.** `serve.py` writes every act through `record.py`'s `append`, which salts, chains, signs and names the file, and signs with the person's own key. It writes `record/<actor>.jsonl` itself only when `record.py` is absent (the paper floor), in the same salted shape.
2. **The confirmation of a human-only act.** The server answers only a request whose Host is 127.0.0.1 or localhost with its own port and that carries the token the person's own page holds (`X-HUD-Token`); any other Origin is refused, and a `publish` needs the publish sheet's one-time token as well.
3. **The proxy's `/discern`.** From any caller it writes only an untrusted, unsigned `note` by the proxy's agent, never a `discern` line. A person's discernment is a `discern` line signed with the person's own key through the ICE, and `proxy.py report` counts a verdict only from such a line whose signature verifies against the key the holon admits for that person.
4. **The signature blob carries the public key,** so a kept signature would re-identify a signer in a names-hidden export. The export removes signatures and the exporter attests the set; a form that keeps each author's signature while hiding names waits on the envelope, per-room keys or ring signatures.
5. **An act for a person.** The agent signs with its own key under a recorded consent (a `once` delegation or `body.consent`), and the fold marks the line `signed_for`; an unsigned line in a person's name counts only at the paper floor in the home record.

## 6. Where the documents and the code disagree

The code is what runs. Each release re-reads the documents against the code; a divergence found is filed as a defect line (§8.2) naming the document's section and the file and function, and the document is corrected in its next version, unless 09 records the document's choice as the decision.

## 7. The open questions, consolidated

Every document's open list, de-duplicated. "Default carried" marks a question that stays open with a default used meanwhile; [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)]] gives the default.

| # | Question | Where it is discussed | Status |
|---|---|---|---|
| **Names and words** | | | |
| 1 | The names of the parts other than the ICE, and the proxy's name | 00; 05 | Open, default carried |
| 2 | The one word for the unit across houses (event, Change, commit), and the settled line as the live-text unit | 00; 01; 06; 07 §8 | Open |
| 3 | The standing question | 03 §6; `hud/DESIGN.md`, amendment 10 | Open, default carried |
| 4 | The Turn's four lines | `engine/turn.py`; `skills/the-turn/`; `hud/DESIGN.md`, amendment 5 | Open, default carried |
| 5 | The Room's coinages; whether an agent says "I"; the curing default; the agents' write budget | `hud/DESIGN-ROOM.md` | Open, default carried |
| 6 | Whether sage joins the palette (until then, only the brand's own hues and the two golds) | `hud/DESIGN.md`, amendment 11 | Open, default carried |
| **Shape** | | | |
| 7 | A room's shape (one shape with sub-shapes, or at least three), and a room as holon or view | 00; 06 | Open |
| 8 | The first holon: its identifier, who holds its key, where its record lives | 00 | Open |
| 9 | The seasonal signal's body; the broadcast's ratification; the system path's broadcast format | 00; 03; 07 | Open |
| 10 | The floor of two against the kit's wider shared forms | 00 §7; 07 §5 | Open, default carried |
| **Record and identity** | | | |
| 11 | What an identifier from a first key (XID) adds, and whether it or a decentralized identifier (DID) is the form | 01; 07; 08 | Open |
| 12 | The key ceremony: inception witness, successor, visible revocation; retiring a first-week identity without orphaning its lines | 04; 08 | Open |
| 13 | Keys per context for a witness | 01; 04; 08 | Open |
| 14 | Where the person's key lives, and for which acts a hardware key is required | 06; 08 §3 | Open |
| 15 | The canonical form across houses (JSON or CBOR; lines as envelopes or inside them) | 01 | Open |
| 16 | An address scheme | 01 | Open |
| 17 | Encrypted bodies; line-level audience within one repository | 01; 02 | Open |
| 18 | The proxy's fingerprints: salted per holon, unsalted, or none by default | 01; 05 | Open |
| 19 | Whether a late `done` counts as kept; whether a released commitment counts in "made" | 01; `bookshelf/the-record/The Game Engine — By Pencil.md` | Late: open, default carried · released: open |
| 20 | The TEA ledger: the record itself, or checkpointed into another immutable ledger; a supercell's second witness | 01 | Open |
| 21 | Removing a non-consenting name from copies already held elsewhere | 08 | Open |
| **Membrane** | | | |
| 22 | The curing period: its length, who may cure what, posture or room shape, and how it meets append-only | 02; 08 | Open |
| 23 | A `vouch` type, and how partial vouching is written | 02 | Open |
| 24 | The commons: its container on the forge, and its keeper | 02 | Open |
| 25 | The public mirror, and who may publish to `public` for a cell | 02 | Open |
| 26 | The forge refusing what policy forbids | 02 | Open |
| 27 | One sign-in everywhere, and how an account binds to an identifier | 02 | Open |
| 28 | Reach beyond the gathered, written into a posture | 02 | Open |
| 29 | Doors onto one card or onto a whole holon | 07 | Open |
| 30 | Where a shared cell's record lives before either house hosts it | 07 | Open |
| **Engine** | | | |
| 31 | Which constraints a holon's convention allows | 03 §2.5 | Each holon decides |
| 32 | The stage vocabulary (with or without *could*) | 03 | Open |
| 33 | One registry of card kinds | 03 | Open |
| 34 | The pledge-and-load gradient | 03 | Open |
| 35 | Buffer sizing | 03 | Open |
| 36 | Who publishes the drum each season | 03 | Open |
| 37 | Tuning the leverage constants by the difference between what was calculated and what was discerned | 03 | Open |
| 38 | Free float with external successors; a fixed-date node's own uncertainty | 03 | Open |
| 39 | The player's place on the Path in sizing The Deal | 03; `engine/deal.py` | Open |
| **Agent** | | | |
| 40 | Whether a consent-signed `discern` counts as the person's | 04; 05 | Open |
| 41 | The whisper's shape, and whether a person may read whispers to their agent from agents they share no holon with | 04 | Open |
| 42 | The assign function's ranking after the gates; believability without a score of a person | 04 | Open |
| 43 | A background body's identity and delegation | 04 | Open |
| 44 | Voice: a spoken yes becoming a signed line | 04 | Open |
| 45 | What an agent may deal from a holon it holds only as a reader | 04 | Open |
| 46 | Whether an agent may hold its person's office | 00 | Open |
| **Proxy** | | | |
| 47 | Whether the proxy routes messages among agents | 00; 05 §6; 08 | Open, default carried |
| 48 | Which proxy to build on, or the kit's own | 05 | Open |
| 49 | The `route` field vocabulary | 05 | Open |
| 50 | An observer over the proxy's trail: whether, where, with what consent | 05 | Open |
| 51 | The proxy as an interface | 05 | Open |
| 52 | Scattering as a stance | 05 | Open |
| 53 | The elders' questions and observing acts: how either reaches the record, under what consent | 05 | Open |
| **HUD** | | | |
| 54 | The state fields the HUD still lacks | 06 | Open |
| 55 | A layout as a line or a plain file | 06 §2.4; `SCHEMA.md` | Open, default carried (the registry declares `layout`, human-only) |
| 56 | A yes from paper or a photo | 06 | Open |
| 57 | Presence as a record line; under which posture presence is hidden | 06 | Open |
| 58 | Who customizes a cell's default layout, by whose consent | 06 | Open |
| **Interoperability** | | | |
| 59 | Who is named witness across houses | 07 | Open, default carried |
| 60 | The link vocabulary, and which semantic-merge relations are declared | 07 | Open |
| **Security** | | | |
| 61 | Who runs conformance, and who checks the test | 08 | Open |
| 62 | Rate limits and the admission window | 08 | Open |
| 63 | Revocation latency, and what an out-of-date holder does with lines signed after a revoke | 08 | Open |

## 8. The improvement loop

The set is never finished. It improves by one loop, open to anyone: find, propose, review independently, fold into the kit, reach every agent, learn. A defect found is a defect the next reader does not meet, and the loop is how the lesson is embedded where future work will meet it. How the kit itself changes is in `HOW-TO-IMPROVE-IT.md`; how a change reaches a layer and a kit release is in 17.

### 8.1 How anyone sends a finding

**A defect or a proposal is a line in the record.** The system's own instrument is the first channel, so a review exercises the thing it reviews.

- **A `sight`** ([[Sighting|a sighting]]) for something seen that the holon should know: `{"text": "…", "where": "…", "kind": "defect"}`, `where` naming the document and section or the file and function. One defect, one line.
- **A thread** when the defect needs discussion: a `thread` line anchored to the line or card at fault (`links.anchored_to`), then `say` lines in it. A thread anchored to nothing is a conversation, and that is allowed.
- **Who writes it.** A person writes in their own name, `reason: human`. A reviewing agent writes under its own account, inside a [[Delegation|delegation]] from its person that covers `sight` and `thread` in the review's holon (`reason: delegated`); a finding the agent drew from text it read, rather than from its own reading of the code, is marked `reason: untrusted` and waits for a person.
- **Where it goes.** Into the review's holon, at audience `holon` or `members`. Nothing a reviewer writes widens beyond that without a person's `publish`.

An example, in the event line's field order (the id, `prev` and signature are computed by `record.py append`):

```
{"v":1,"id":"…","ts":"2026-11-02T10:12:00-08:00","actor":"agent:reviewer-aide","for":"person:reviewer",
 "holon":"<the review holon's id>","type":"sight",
 "body":{"text":"<what was seen, in one sentence>","where":"<file and function, or document and section>","kind":"defect"},
 "links":{},"audience":"holon","reason":"delegated","prev":"…","sig":"…"}
```

**A pull request** carries a change already made: a fix to the code, a correction to a document, a new test that proves a claim in §4 that is "not yet proven". It names the defect lines it answers, and its description says what it changes, why, and what it does not prove. A pull request is a proposal; nothing merges on its author's word.

**Without a holon.** A reviewer who holds no holon sends a plain text file to the review's keeper, one defect per line in the paper form (time · who · for whom · type · what · links · audience); the keeper types it in, unsigned, and says so.

### 8.2 How it is reviewed

1. The defect or proposal becomes a [[Work Card]] in the holon that owns the fault, linked to its lines.
2. **Someone other than the proposer makes the fix, and someone other than the fixer reviews it.** The one who assigns never audits. A reviewer that is an agent reads with the same independence, and its verdict is a line its person can read.
3. A review returns or passes against the bar in §9. A return names each defect with its evidence; a pass says what it checked and what it did not.
4. **The retrospective reads the loop itself.** At each turning, and more lightly at each new and full moon, a reader that did not do the work reads the period's defect lines, returns and repairs, and proposes what to change in how reviewers work: a check to add to §9, a test pattern, a document that keeps drifting. Self-grading is not the instrument.

### 8.3 How it folds into the kit and reaches every agent

1. The fix is proposed to the keeper of the layer it touches (17), with its lines as evidence; the keeper accepts or refuses it, with a reason either way, and the reason is a line.
2. A release carries what was accepted. Its notes name the defect lines it closes.
3. **Every agent pulls the release on its own person's word** (`skills/pull-a-release/`), diffs it, adopts or declines with reasons, and re-runs conformance. No agent changes its charter from a release note; the release changes the kit, and the person changes the charter.
4. The defect line is answered (`answer` or `done`, linked to it), and the fix is [[Witness|witnessed]] by someone other than the fixer. A document corrected by the fix changes in its next version.

### 8.4 A defect is a gift

A defect is never a mark against a person. The record of findings describes what happened to the work, never who failed. A reviewer who returns the set has served it more than one who passes it unread. What a defect teaches is embedded where future work will meet it: a test, a check in §9, a line in a document, a skill.

## 9. The review bar

The set is held to this bar. A finding against items 1 to 4 returns the set; the rest are lifted and passed.

1. **Can an agent tick a human's box?** Can anything leave a holon without its person's yes? Can text inside a line make any part send, push, publish or change anything?
2. **Under names hidden, is every name gone, and does every line still prove its content, with the set attested by the exporter?**
3. **Does every claim trace** to a document section, a file, a test, or an honest "not yet proven"? Is anything stated as settled that is open?
4. **Does every number reproduce** by pencil from the paper record, and does every computed figure say, per holon, what it is as of?
5. **Does every decision carry its reason and its alternatives** ([[09 — Decisions and Their Reasons (Architecture, 2026-10-24)]]), and is every open question that carries a default named with that default?
6. **Does the code keep the contracts** (`SCHEMA.md`, `STATE.md`, the registry) and say plainly where it goes beyond them?
7. **Does the surface meet its own bars**: the checks of `hud/DESIGN-THE-BAR.md` (§5) are the surface's review sheet (twenty-five yes-or-no lines; a no on a line marked ■ returns the view), scored for every view in every scene, on a phone first, then at 1440 px, night and paper, regular and large type; the Room's review bar in `hud/DESIGN-ROOM.md`; the one-breath test with three wearers? Every change to a view says what it measured about itself and where that measure lives (`DESIGN-THE-BAR.md` §4).
8. **Do the word laws hold**: *commitment*, The Deal, no center but ØNE, Roles and never persons' names, no vendor's or house's name, no contractions but "Here's the deal."?
9. **Is the system still agent-optional**, all the way down to paper?
10. **Does attention stay the person's own?** Is every ask read against the person's own `attention` lines before it interrupts, through one computed queue, as a Deal of one card; is anything withheld said with when it returns; is any view, the Threads view above all, readable at any time whatever the gate says; does a push carry the Push Protocol v1.1 field with `push_by` on every value, and does the receiver recompute what blocks, what is critical, the by-when and the cost if late from its own record (`hud/DESIGN-ATTENTION.md`, the attention budget and the one queue; `SCHEMA.md`, The Push Protocol)?

The verdict on beauty and resonance belongs to the kit's keeper; the verdict on truth belongs to the evidence.
