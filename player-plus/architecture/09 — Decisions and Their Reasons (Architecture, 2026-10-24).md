---
title: Decisions and Their Reasons
description: The register of the kit's design decisions, one row each, with its reason and what it rules out. Architecture document 09 of the LIØNSBERG Intelligence System.
---

# Decisions and Their Reasons

*Every design decision that documents [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)|00]] to [[08 — Security and Sovereignty (Architecture, 2026-10-24)|08]] and the code embody, one row each: what is decided, why, what it rules out, and where it lives. Anyone who wants to know why the kit is shaped as it is can find the reason here before reading the document that carries it. [[10 — The Reviewer's Guide (Architecture, 2026-10-24)]] says how to test each claim; [[Index — The Architecture (2026-10-24)|the Index]] maps the files.*

## How to read this register

- **Rules out** names the alternatives that were weighed and set aside.
- **Where** names the document and section (00 §6 is document 00, section 6) and the file in the kit (paths from `player-plus/`).
- Questions that are not settled are gathered under **Open** at the end, each with the default the kit carries meanwhile. What is designed but not built is gathered under **Not yet built**.
- Row ids (W1, R1, RD1, …) are labels for this register only; they are not identities in any record.

## RD. The record's guarantees

Eleven decisions that make the record hold under an adversary. Each refines the rows named in its last column.

| Row | Decision | Reason | Rules out | Refines |
|---|---|---|---|---|
| RD1 | **Signatures are verified in the fold**, against keys admitted to a holon by its `join` and `affirm` lines; a line whose signature does not verify against an admitted key for its `actor` does not count | If the fold checked ids only, anyone able to append one line could write any person's yes, delegation or publish, and a relay could forge | signatures checked only by a separate `verify` command; an allowed-signers file kept by hand | R7, R8; 03 §1 step 2 |
| RD2 | **An unsigned line is authoritative only at the paper floor, in the home record**: a person's own unsigned lines count in their own home; elsewhere an unsigned line is shown and never acts until it is signed or witnessed | Keeps the paper floor whole for one person and their notebook, and closes it as a way to write another's act in a shared holon | unsigned lines counting everywhere; unsigned lines never counting | R24 |
| RD3 | **A names-hidden export removes every signature and every `prev`, and the exporter attests the exported set with one signature**, until lines are carried in signed envelopes that allow elision with an unlinkable proof | An SSH signature carries the signer's public key, and a visible `prev` chains one actor's lines, so a kept signature names the speaker; a signature with the actor hidden proves only that some key signed | keeping signatures (verifiable by author, names recoverable); per-room keys; ring signatures | R4, M6; 02 §6 |
| RD4 | **A line is superseded only by the same actor, or by a person's `decide`**; a superseding line that is not itself valid (untrusted, out of delegation, wrong type) changes nothing; superseding a human-only line is itself human-only | If any line carrying a `supersedes` link removed its target, an untrusted agent line could erase a person's card, and an agent could rewrite a commitment it may not make | supersession by the same Living Intelligence (`for`), whatever the actor | R13 |
| RD5 | **Time by chain order**: delegation scope, expiry and revocation, claim expiry and "as of" are decided by each actor's `prev` chain and by links, and a reader's own clock bounds any declared time | A backdated line would dodge a revocation, and one line dated far ahead would expire every claim and delegation | the declared `ts`, compared as a string | R21, R23, R30 |
| RD6 | **A key per actor**: each actor signs with its own key; a person's line is never signed by a key not named for that person | If every actor on a machine signed with one default key, the agent's line and the person's would carry the same fingerprint | one key per machine | R12; 04 §2 |
| RD7 | **Every local endpoint sits behind a token and a Host check**: the proxy and the HUD's server require `Host` to be the loopback address and port, refuse a cross-origin request, and require a secret only the person's own page or process holds for any act, any judgment and any spend | Loopback alone is not a membrane: any local process or any web page in the person's browser could post a confirmed human act, a judgment in anyone's name, or spend the person's model key | loopback binding alone; a client-sent `confirmed` flag | H6, H7, P2 |
| RD8 | **Each holon's cards are scheduled on that holon's own calendar**, and each holder's minutes from it | If every cell were scheduled on the reader's calendar, two players folding the same lines would compute different dates | the reader's home calendar for everything | E8 |
| RD9 | **`discern` is human-only**: the person signs a judgment, or their agent signs it under their recorded consent (A2); a judgment from any other caller is a proposal | The person's discernment is theirs; an agent-written judgment must neither count nor be forgeable | the agent writes judgments `for` the person with `reason: human` | P11 |
| RD10 | **Only the named witness moves a commitment to kept**; a commitment that names no witness is verified by any fair witness who is not its keeper | If any member of a cell could turn a claim into kept, the count of commitments kept would mean nothing | anyone but the keeper | R27 |
| RD11 | **A time constraint carries a reason and an imposer**, or it is reported as a defect (E5) | — | — | E5 |

## W. The whole

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| W1 | Six layers over one [[The Record\|record]]: Membrane · Record · Proxy · Engine · Agent · ICE (the HUD, the dock, the Room) | One source of truth; every layer above the record can be deleted and rebuilt from it | separate products per function joined by integrations; one central database | 00 §2; `engine/SCHEMA.md` "The layers, one record" |
| W2 | Every [[Holon]] keeps its own record at every scale; a cell's record is its own, not the union of its members' | Sovereignty is holonic; a shape that holds at one scale holds at all | the cell as a view over members' records; one shared log for many holons | 00 §5, §6.1; 01 §1 |
| W3 | No center but [[ØNE]]: no holon commands another, and each holon's still point is its allegiance (every line signed by an Actor, every delegation ending in a [[Actor\|Living Intelligence]], every Living Intelligence oriented to the ØNE) | The first half without ØNE leaves a part with no orientation; a coordinating hub becomes the dependency everything breaks on | a coordinating hub; the first half alone, without ØNE | 00 §6.3; 06 §9; 07 preamble |
| W4 | Agent-optional: every process is an event or a calculation over events, and every number can be worked by pencil | The system must run with no AI, or on a sovereign local model; paper is the floor of graceful degradation | an agent required for operation | 00 §6.5; 01 §10; 03 §11 |
| W5 | The Supersuit ships three parts in one install (Agent, Engine, HUD); the agent is the tool layer | A Player+ needs every requisite of co-creation from one record; feature parity with existing project, chat and scheduling products is not the measure | the agent alone in the first week, with the Engine cut to its core and no screen | 00 §1, §8 |
| W7 | The proxy is a layer of the same record, writing `route` and `discern` lines under the same keys | Discernment evaporates unless it lands where everything else is kept | a separate service with its own logs | 00 §2; 05 §1, §3 |
| W8 | The HUD's Room layout over a shared holon's record **is** the collaboration surface | One record and one design, rather than a separate collaboration product beside the work | a separate pad or meeting product | 00 §2; 06 §2.3; `hud/DESIGN-ROOM.md` |
| W9 | A minimum interoperability floor between holons: the event line, one consistent seasonal signal, the weekly Turn offered and never required | A small floor admits any tool inside a holon; a large one becomes a time card | the Field's wider set of shared forms as the floor; no floor | 00 §7; 07 §5 |
| W10 | The whole is **The LIØNSBERG Intelligence System**; a Player+'s bundle (Agent · Engine · ICE) is **the Supersuit**; the surface is **the ICE, the Integrated Creation Environment** (the HUD's views, the dock, the Room), with the Proxy beneath it. The ICE and the Proxy are the kit's own, and the integrated experience follows from them | The IDE is the ICE's primitive forerunner: one person's integrated environment, where the ICE is co-creative | — | 00 §1, §2 |
| W13 | In live text the unit is a settled line, held as a hypothesis so it can be changed | Speech is fluid; what a person settles is what binds | the live document as the unit; the Change, a signed settled edit | 00 §3; 01 §2; 06 Open |
| W14 | Speech is not recorded; only what a Living Intelligence settles enters the record | Much that is said should not be kept; a transcript is not a record | transcripts as the record | 01 §2; 06 §4; `hud/DESIGN-ROOM.md` |
| W15 | The wearer's experience is accepted by the one-breath test | A suit its wearer cannot explain to a neighbour has failed, however capable | feature checklists | 00 §1; 06 §5; `hud/DESIGN.md` §9 |
| W16 | The one who assigns never audits | An assigner grading its own assignment is the oldest failure of review | self-review | 00 §6.10; 04 §5; 08 §2.11 |
| W17 | The word is *commitment* everywhere; the number is *commitments kept* | One word for one thing, held in every string, page and test | the retired word | all; `engine/tests/test_game.py` asserts its absence |
| W18 | A player's dealt cards are **The Deal**, its voice a plain briefing that opens "Here's the deal." | A briefing names what needs the person and why, in their own time | an earlier name drawn from a card game | 03 §6; 06 §1 |
| W19 | **A Player+'s agent runs on the Player+'s own machine from day one; hosting by a cell is a later service** | Every holon keeps its own record, and the person's home is the first holon: the record, the keys and the agent's working memory stay with the person from the first hour, and nothing depends on a host the person does not hold. A cell offering hosting is a convenience added later, never the ground | hosting every new Player+'s agent on a cell's machine from the first day | 00 §4; 02 §8; 04 §6; 05 §1; 06 §5 |

## M. The Membrane

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| M1 | The private network of admitted devices is the first membrane; being on it is reach, never trust | What a device can reach and what it may read are separate questions | public hosting with access control alone | 02 §2 |
| M2 | A self-hosted forge inside the private network; every person and every agent has an account of their own | An agent acting under its person's account cannot be told apart from its person | shared accounts; a hosted forge | 02 §3 |
| M3 | Audience is enforced by container (usually a repository), never by line: a line is written only into a container no wider than its audience | Git access is whole-repository; a per-line server check would make the server a hub | line-level encryption; a server that filters each line | 02 §4 |
| M4 | Proposed: the four audiences map to containers: the home repository · a related holon's `published/` · a commons repository · a public mirror | Makes M3 concrete | — | 02 §4 |
| M5 | An agent has no audience its person cannot read; agents may whisper, and the person each agent serves reads it all | A hidden channel between agents is a hidden channel past the person | private agent-to-agent channels | 02 §4; 04 §9 |
| M6 | Three export postures: names hidden (`names-hidden` in the code), open, sealed; a room's posture is a human-only `posture` line; a names-hidden export removes signatures and `prev` and is attested by the exporter (RD3) | Posture is agreed before a gathering, and the export keeps the proof whatever it hides | free-form redaction | 02 §6; `engine/record.py` export; `engine/types.json` posture |
| M7 | A curing period after a gathering, in which each participant may correct, retract or narrow what they said | Second thoughts deserve a window before anything leaves | none; export at once | 02 §6; 08 Open 7 |
| M8 | Entry by vouching; the [[The Trust Graph and the analog contact-tree\|trust graph]] is computed from `join` lines, never kept by hand | Provenance of every member, traceable to the first keeper | open signup | 02 §7 |
| M9 | An agent enters a room only by a present person's `affirm`, after it passes conformance | A person answers for their agent's presence | admission by the agent's own request | 02 §7; `engine/types.json` affirm; `engine/rooms.py` |
| M10 | Proposed: the keeper of the membrane is a Role held by a Living Intelligence, distinct from the keepers of the host | Whoever grants access is not whoever keeps the machines | the host's keepers as gatekeepers | 02 §9 |
| M11 | The record does not rely on the forge refusing what policy forbids; each repository proves itself in any clone | A record that proves itself does not depend on what any host agrees to run | relying on server-side refusal | 02 §3, Open 6 |
| M12 | The public door is read-only or by invitation. The first door: a Player+'s agent runs on their own machine from the first day; the install is one line pasted into the command-line harness and takes minutes; the agent speaks first and The Deal arrives by about minute ten; the phone reaches the agent on that machine afterward. A shared machine or a hosting cell are configurations in the same space, chosen by each house, never the default | The record, the keys and the agent stay with the person from the first hour (W19), and one pasted line is an install a friend can walk anyone through | a player who installs nothing, served by a hosted agent; an installer with many steps | 02 §8; 06 §5; 04 §6 |
| M13 | The membrane governs the future, never the past: replicated lines stay where they went | Recall cannot be enforced on a copy already taken; pretending otherwise misleads | revocable reads | 02 §3, §10 |

## R. The Record

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| R1 | One append-only file of JSON lines per [[Actor]] per holon | Two writers never touch the same bytes, so git merges by union and no merge conflict can occur | one shared log per holon; a database | 01 §1; `engine/SCHEMA.md`; `engine/record.py` actor_file |
| R2 | A line's id is the sha256 of its canonical form without `id` and `sig` | The signature is made over a stable identity, and a line can be countersigned without becoming another line | hashing the signature into the id | 01 §3 |
| R3 | The canonical form is JSON with sorted keys, separators `,` and `:`, UTF-8 | Readable by eye and computable by hand on every machine | deterministic CBOR, as in a signed-envelope standard | 01 §3, Open 6 |
| R4 | Salted digests per field: each body field, and `actor` and `for`, enter the hash as `sha256(field_salt + value)`, one salt per line, a derived salt per field | A line keeps the same id and a valid signature before and after any field is hidden; a low-entropy value cannot be guessed from its digest | eliding body fields only; per-room keys or ring signatures for full anonymity | 01 §3, §5; `engine/record.py`; `engine/SCHEMA.md` "Elision" |
| R5 | Every line the kit writes is salted by default | A non-consenting person's name can then be removed in place without breaking the id | plain unsalted lines | 01 §5 |
| R6 | A holon's id is the id of its inception line: a `join` by its keeper with an empty `holon` field | Identity is what the holon is, never where it lives; a moved holon keeps its id | a random id; the repository's address | 01 §1, §12 |
| R7 | Lines are signed with SSH ed25519 keys, `ssh-keygen -Y sign`, namespace `lionsberg-record`; the forge's account keys serve for the first week; the fold verifies every signature against admitted keys (RD1) | The tool is already on every machine and the forge already holds the keys | a signed-envelope standard's signatures now; other signing tools | 01 §4; `engine/record.py` sign_id, verify |
| R8 | Persons and agents have separate identities and keys, linked by `for` | Who signed, under whose delegation, must be readable forever | an agent signing as its person; a shared key | 01 §4; 04 §2 |
| R9 | Human-only types are marked `human_only` in the registry, and the registry is the whole list; among them `settle` · `commit` · `kept` · `witness` · `decide` · `ratify` · `delegate` · `revoke` · `join` · `leave` · `publish` · `turn` · `discern` · `posture` · `affirm` · `layout`. Such a line folds invalid from an agent, except under a recorded consent of its person (A2). `answer` stays open to agents | "An agent never ticks a human's box" is enforced by structure, not by a policy an agent could misread | policy text alone | 01 §4; 04 §1; `engine/types.json` |
| R10 | [[Delegation]] is a `delegate` line (types, holons, until), ended by `revoke`; an agent's line is valid only inside a live delegation | Explicit, scoped, time-bounded, revocable and recorded; an expired delegation is dead without anyone remembering to end it | permissions in a configuration file; standing grants with no expiry | 01 §4; 04 §3; `engine/record.py` delegation_for |
| R11 | First-week identities are disposable and labeled; real identities come with a ceremony | A ceremony done in haste is worse than a labeled placeholder | a ceremony before the first week | 01 §4; 08 §2.9 |
| R12 | One key per Actor (RD6); one key per body is the target | Lines can then be sorted by which body made them | one key everywhere, forever | 01 §4 |
| R13 | Nothing is edited or deleted; a correction is a `supersede`, both remain, and a line is superseded only by the same actor or a person's `decide` (RD4) | History that can be rewritten is no history | edits with a change log | 01 §5; 03 §1; `engine/record.py` |
| R14 | The one exception: a non-consenting person's name is removed wherever it was written, and the removal is recorded | Consent outranks completeness | eliding the name and keeping it under the digest | 01 §5; 07 §9 |
| R15 | Four audiences, `holon` · `members` · `commons` · `public`; never wider than the holon; within a holon only narrowing | Audience belongs to the holon, and a repository is sometimes the holon's container | per-person access lists | 01 §6; 02 §4 |
| R16 | Publication is a separate human-only `publish` line; the published lines are copied whole into the receiving holon's `published/`, id and signature intact | A line's own audience is signed and never changes; widening is its own recorded act | rewriting the audience field; agents publishing | 01 §6; 02 §5; `engine/holon.py` |
| R17 | What crosses by default is a holon's face and signals (`card` but never a bare activity, `commit`, `request`, `offer`, `answer`, `done`, `kept`, `witness`, `turn`, `flame`, `hand`, `claim`, `release`, `supersede`, `sight`) | The inner life of a holon stays home; dependencies cross as commitments | publishing the whole deck | 01 §6; `engine/holon.py` PUBLISHABLE |
| R18 | Replication is by relation, through git in 3.8.0; the kit's code pulls fast-forward only and never pushes | Pushing one's own lines out is a person's act | a sync service; automatic push | 01 §7; `engine/holon.py` |
| R19 | Signed commits by each Actor's forge key are a second chain beneath the lines | The record is provable twice, line by line and commit by commit | lines alone | 01 §7 |
| R20 | Items are folded, never stored; the type registry is data, and a new type is a new entry, not new code | The same lines give the same items everywhere, by script or by pencil | stored items; code per type | 01 §8; `engine/types.json`; `engine/record.py` fold |
| R21 | Order comes from links and each actor's `prev` chain; `ts` is a claim used only where nothing else orders, and a reader's own clock bounds it (RD5) | A forged time misleads only a reader who trusts times over links | timestamp order | 01 §8; `engine/record.py` |
| R22 | Readers keep fields and types they do not know | An older reader passes newer lines through unharmed | rejecting unknown input | 01 §8, §11; 07 §7 |
| R23 | Every computation says what it saw: per holon, the newest line, its time and the count read | Lag is visible instead of hidden behind a server | a single "last updated" | 01 §9; 03 §1; `engine/STATE.md` |
| R24 | Paper-floor lines are unsigned and unsalted, and count only in the person's own home record (RD2); a witnessed paper sheet beats the typed copy | The floor must be workable with a pencil | requiring a key | 01 §10 |
| R25 | A home's `.gitignore` ignores `cells/` as well as `state.json`, so a home never commits its clones of cells | Each cell is its own repository | committing cells into the home | 01 §12; `engine/SCHEMA.md`; `engine/holon.py` |
| R27 | **The keeper of a commitment claims `kept`; the named [[Witness]] verifies it with `witness`** (any fair witness who is not the keeper when none is named, RD10). The witness is never the item's own | Keeping and verifying are two acts by two people: the one who did the work is the first to know they think it is done, and a fair witness is the one who can say so for others | the witness alone writes kept; the receiver says kept (each puts the whole judgment in one hand) | 01 Open 4; 03 §5; `engine/SCHEMA.md` (a Commitment); `engine/types.json` kept, witness |
| R29 | TEA is kept on an immutable ledger | The ledger first; the full design of the TEA and LUV bank later | a chain-based ledger now | 01 Open 5 |
| R30 | A `claim` may carry `until`; when it passes and the claimer still holds the card, the card returns to `ready` and its previous holder; expiry is read by chain order (RD5) | A claim that never expires blocks the card in silence | claims with no expiry | `engine/record.py` fold |
| R31 | A commitment's status is read from the fold: claimed → kept-unwitnessed; witnessed → kept; declined → released; open past its by-when → broken | One mapping, written down, between the registry's states and what a person reads | separate status logic per view | `engine/STATE.md` |

## P. The Proxy

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| P1 | The proxy is optional; the harness reaches it by one base-URL setting the person installs by their own hand | Take the setting away and everything works as before | an SDK integration; a mandatory gateway | 05 §1 |
| P2 | One person, one proxy, local, bound to loopback, behind a token and a Host check (RD7); no flag widens it | A shared proxy tangles sovereignty and leaks between people | a shared proxy per cell | 05 §1; `engine/proxy.py` |
| P3 | Routing policy is data (`routes.json`): rules tried in order on model, tag, size and hour; first match wins | The person's to read and change, and never code | routing logic in code | 05 §2; `engine/routes.json` |
| P4 | A request tagged `private` goes only to the model on the same computer; the sample policy puts that rule first | Private stays home by default | trusting a vendor's own retention terms | 05 §2 |
| P5 | `route` and `discern` lines are written through the record's own writer (salted, chained, signed when a key is at hand), with a same-shape fallback file when the writer is unavailable | The proxy's lines are lines of the holon like any other | a separate proxy log | 05 §3; `engine/proxy.py` |
| P6 | Never a prompt body, completion, tool content, image, key or auth header; a fingerprint of request and completion, keyed by the holon's own salt, switched off by `hash_bodies: none` | A judgment must be matchable to its answer; a body must never be kept | keeping bodies; no fingerprint possible | 05 §3, Open 11; 01 Open 9 |
| P7 | Fusion as a council: off by default; the first member to answer is returned, with every member's answer in an extension field and its own route line | A council instead of an oracle, with cost said before it runs | a synthesizing model inside the proxy | 05 §4; `engine/proxy.py` |
| P10 | `discern` fields are `route_id` · `verdict` · `rating` · `note` in both the registry and the proxy | One vocabulary lets the fold attach a judgment to its route | the registry's earlier `route` · `choice` | 05 Open 3; `engine/types.json`; `engine/proxy.py` |
| P11 | A `discern` line is human-only (RD9): the person signs, or the agent signs under a recorded consent (A2); a judgment posted with the person's token is the person's, with the agent's token it is `untrusted`; discernment is counted only from a person | The person's discernment is theirs | the proxy writing judgments under its own actor with `reason` defaulting to `human` | 05 Open 4; 04 Open 5; `engine/proxy.py`; `engine/ledger.py` |
| P12 | Every translation drop between message shapes is counted on the route line and in a response header | Nothing silent | best-effort translation | 05 §5; `engine/proxy.py` |
| P13 | Sovereign inference climbs a ladder: one machine, a household's machines, a farm inside the membrane, many farms | Every rung writes the same lines, so evidence of quality carries across rungs | one leap to a farm | 05 §8 |

## E. The Engine

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| E1 | The Engine is pure functions over lines; `state.json` is derived, git-ignored and safe to delete; the HUD reads only it | One deck, one truth; nothing else computes a schedule | stored schedules; a scheduling service | 03 §10; `engine/engine.py`; `engine/STATE.md` |
| E2 | Minutes are the one unit; days are derived through an Actor's calendar, except where the world sets the duration | Effort belongs to the person; days belong to the calendar | hours; story points | 03 §0, §2.3 |
| E3 | The whole [[Critical Path\|critical path]] method: four relationship types with lags, constraints, retained logic for progress | The full engine, not a core cut down for speed | an engine cut to its core; progress override | 03 §2; `engine/schedule.py` |
| E4 | Negative float is reported and never clamped | The record's honesty, computed | clamping to zero | 03 §2.5 |
| E5 | **Imposed dates are time constraints, by default on milestones** (Constraint is one word with kinds: resource, information, agreement, time), carried on a card's `constraint` field: `{kind, date, reason, imposed_by, source}`, where kind is finish-by · start-no-earlier · finish-no-later · start-on · finish-on · as-late-as-possible, and source is commitment · world · law. **A constraint without a reason and an imposer is a defect.** The Engine reports negative float against a constraint and never moves the logic to hide it. Placing a constraint well is an art and a science of the Way | A date the world, a law or a commitment imposes is real and must be scheduled against; a date imposed with no reason and no one answering for it is the commonest way a schedule lies. Requiring both makes every imposed date accountable, and never clamping keeps the gap visible | dates as bare labels on milestones, computed by logic and never imposed (too weak for a date the world sets); the full constraint set with no accounting (too easy to abuse) | 03 §2.5, Open 1; `engine/SCHEMA.md` (a Work Card); `engine/schedule.py`; `engine/tests/test_schedule.py` `Constraints.test_constraints_report` |
| E6 | Critical means total float ≤ 0; the longest path is shown, not used as the definition | One rule, matched against the reference scheduler | the longest-path definition; multiple float paths | 03 §2.8; `engine/schedule.py` |
| E7 | Near-critical is 0 < total float ≤ 3 days, settable; the 3 days is an assumption | The band The Deal watches most closely | — | 03 §2.7 |
| E8 | A calendar counts all seven days by default (the Daily Way runs every day); minutes per day default to 480; each holon's cards are scheduled on that holon's own calendar (RD8) | Every number about a Living Actor is theirs to set | — | 03 §2.1, Open 4; `engine/schedule.py`; `engine/holon.py` default_calendar |
| E9 | The Gameclock: the season from turning to turning, two spans of 42 days, the new and full moons, the week and the day; [[OmniSpection]] is continual at varying depths (daily, at each new and full moon, at each turning) | Looking at the whole is never a single point in the season | OmniSpection at the turning alone, or between the spans | 03 §2.1; `engine/SCHEMA.md` calendar.json; `engine/schedule.py` rhythms |
| E10 | Turnings and moons are computed by standard astronomical algorithms, overridden by any dates the calendar gives | The paper floor and a local almanac must agree with the machine | typed dates only | `engine/schedule.py` |
| E11 | Local leveling only, one Actor in one holon; leveled dates stand beside logic dates | Leveling across holons would need a center holding everyone's capacity | global leveling | 03 §2.12 |
| E12 | A [[Commitment]] is the only edge that crosses a membrane; a published line enters another holon's schedule as a fixed-date interface milestone | Across a membrane there is no task: a supercell requests, a member offers and commits | linking to another holon's activities | 03 §3.1–3.2; 07 §3 |
| E13 | The widest holon's pass over every published milestone is the system path, and it publishes each milestone's float back | The whole can say what it waits on without a master | a master schedule | 03 §3.3, Open 11 |
| E14 | [[Buffer\|Buffers]] by the halving rule; green, yellow, red by consumed share against chain complete | The textbook default, reported and never imposed | root-sum-square sizing; buffers set by people | 03 §3.4, Open 5 |
| E15 | The drum is the Actor on the chain with the least free capacity; publishing it each season is proposed | The scarcest attention sets the pace | — | 03 §3.4, Open 6 |
| E16 | What is owed is computed, never remembered; lines written for an untrusted reason come back as proposals, never owed | Nothing depends on anyone's memory | a task list kept by hand | 03 §4; `engine/owed.py` |
| E17 | Commitments kept is the first number every holon sees: kept ÷ (kept + kept-unwitnessed + broken), empty when nothing fell due | A share of what fell due, describing commitments, never people | a score of persons | 03 §5; `engine/kept.py`; `engine/STATE.md` |
| E18 | The Deal's order (owed · threads · decisions · ready by leverage) and the leverage rule with named constants, the rule riding in every Deal; the constants are assumptions | A rule that can be argued with, tuned by evidence | due date alone; an opaque ranking model | 03 §6; `engine/deal.py` |
| E19 | Minutes dealt never exceed minutes available; what does not fit is counted under *beyond* | Five minutes is a real Deal | an unbounded list | 03 §6 |
| E20 | The standing question closes every Deal and costs no minutes | — | — | 03 §6; `engine/deal.py` |
| E21 | An agent is dealt only what a live delegation covers, and never a human-only act, a decision or a review | Structure, again, over policy | dealing agents everything | 03 §6; `engine/deal.py` |
| E23 | The Turn has depths: daily, lunar, seasonal, and weekly for holons that keep one; the person finishes and signs the `turn` line | Looking back is continual; its depth follows the day | one weekly Turn | 03 §7; `engine/turn.py` |
| E25 | The TEA ledger is never convertible (not into money, into one another, or into rank) and says so in every output; witness tiers are unwitnessed, the keeper, a supercell | Time, energy and attention are not a currency | a convertible points system | 03 §8; `engine/ledger.py` |
| E26 | [[The Score]] is earned value with minutes of TEA as the currency; no cost account, no rate | Throughput of the Goal, never cost | earned value in money | 03 §9; `engine/schedule.py` |
| E29 | One command line (`engine.py`) over modules, one per function | Each function testable alone; one door for the agent | one file per function only | `engine/engine.py` |
| E30 | Capabilities of commercial schedule engines are named as *refused* (by design) or *not yet* (just in time) | Anyone can see what is absent and why | silent omission | 03 §12 |
| E31 | A baseline freeze writes a new file and never overwrites one | Re-baselining is a recorded act, never a quiet overwrite | overwriting the current baseline | 03 §2.9; `engine/schedule.py` freeze |

## A. The Agent

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| A1 | Roles and Offices belong to Living Intelligence; an agent may hold an office's preparation, never its act | [[Artificial Intelligence]] serves Living Intelligence | agents as Players | 04 §0–1 |
| A2 | **An agent may sign one act in its person's name, with the person's consent recorded.** Two forms: a `delegate` with `once: true` for a single type and holon, signed by the person; or the person's spoken consent carried on the line itself (`body.consent`, their words, with `links.answers` to their `say` line when there is one). The agent signs with its own key, the line's `for` is the person, and the fold marks it `signed_for`; every view shows it as signed by the agent at the person's word. A human-only act is valid from an agent only under such a consent | A person should not have to touch a key for every yes, and an agent must never give a yes it was not given. Recording the consent, and signing with the agent's own key, keeps both true: who signed is never hidden, and whose word it was is on the line | the person signs every own act; the agent writes the line unsigned in the person's name (such a line cannot be told apart from one an agent wrote on its own) | 04 §1; `engine/SCHEMA.md` (a Delegation); `engine/record.py` (the fold's `signed_for` list and item mark) |
| A3 | Day one proposes one narrow delegation: `say`, `card`, `answer`, `thread` and `learn`, and `route` if the proxy is on, in the home only, a week out | Narrow first; widen only by the person's word | a broad first delegation | 04 §3; `skills/the-record/day-one.md` |
| A4 | The agent makes the home a holon on day one, after the waiver and the Field of Agreements, rather than the installer | The inception line is the keeper's act, and the keeper's handle is unknown at install | the installer makes it | `skills/the-record/day-one.md` |
| A5 | The daily offices are skills: plain-text procedures each saying what it writes, what it never does and how it degrades to paper | A new office is a skill, never hidden behaviour | behaviour in code or prompts | 04 §4; `skills/` |
| A6 | Work is cued pull first: the one who does the work makes the last plan; assignment is the fallback | Practice drawn from research on cueing work to the right Actor | push assignment | 04 §5 |
| A7 | The firewall by construction: the `reason` field, four hard stops, reversible work without asking, ask before anything leaves the holon | Structure enforces what text alone cannot | a policy page only | 04 §7; 08 §0, §2 |
| A8 | Six conformance checks, run locally with the network off, before a person affirms an agent into a room; the person affirms, the sheet informs | Competence by structure, shown on one sheet | admission on the agent's word | 04 §8; `engine/conformance.py` |
| A9 | Agents talk by writing events into a holon both hold; there is no side channel the record does not see | One record, one set of keys | direct agent-to-agent channels | 04 §9 |
| A10 | A correction becomes a `discern` line; the weekly retrospective is drafted by a reader that did not do the work; what would serve every Player+ is proposed to the kit | Every defect is a gift, embedded where future work meets it | self-grading | 04 §10 |
| A13 | The agent is called "your agent", your map and your guide, until its wearer names it; then its name is used. The word "agent" may reach a player's screen; "helper" is never used | One plain word, owned by the wearer | "helper" | 06 §1–§8; `hud/DESIGN.md` |

## H. The HUD

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| H1 | The HUD reads one file (the merged state) and writes through one door (the act path); it never computes a figure | A view that computes is a second engine | client-side computation | 06 §0, §9; `hud/serve.py` |
| H2 | Three default layouts: Player, Cell steward, Room; each a sort of the same state over every holon held | One world, one deck, many distances | per-holon apps | 06 §2 |
| H3 | [[The Deal]] is the hero of the Player layout; the count and the cost are said first so the wearer consents before starting | The two or three things that need you today, with the whole one gesture behind them | a dashboard | 06 §1 |
| H5 | Static files, no build step, no framework, no package manager; libraries vendored as one file with the version in its name; fonts vendored | Reads offline, and the supply path stays small | a framework and a bundler | 06 §6; `hud/DESIGN.md` §8.1 |
| H6 | A tiny standard-library server on loopback, behind a token and a Host check (RD7): `GET /state`, `GET /stream`, `POST /act`, `DELETE /act/<id>`, `POST /publish-sheet`; an act is held for an undo window of five seconds (up to fifteen) | Nothing written in haste; nothing written after Undo | a remote server; no undo | 06 §6; `hud/serve.py` |
| H7 | The server, not the view, refuses: an audience wider than `holon`, a human-only act without the token only the person's own page holds, a `publish` without the publish sheet's token, a holon not held | A control held only at the edge is a hope, not a guarantee | refusals in the views; a client-sent `confirmed` flag | 06 §6; `hud/serve.py` |
| H10 | Accessibility at WCAG 2.2 AA (AAA for body text where the palette allows); meaning never by colour alone; list and table twins; the words *holon, event, fold, engine, schema, float* never reach a Player's screen | A grandmother on her own phone is the user | — | 06 §8 |
| H11 | No sound; no badge, streak, ranking or currency symbol; nothing advances on a timer; the surface goes still when the Deal is played | The surface serves attention, never demands it | engagement mechanics | 06 §9 |
| H12 | No center is ever drawn: each holon is a field turning on its own axis, every axis pointing past the frame; the fields are made frames from the brand's hand, with a code-drawn ring standing in until the frames exist | No center but ØNE, made visible | a tree, an org chart, a root node | 06 §9; `hud/DESIGN.md` §4.4 |
| H13 | No drawn light in the opening or the loader | — | glow, bloom, ember | `hud/DESIGN.md` |
| H14 | Only the brand's own hues are used, with a darker gold (`#7a5f17`) proposed for gold text below 24 px, because the brand's gold-ink fails AA for small text | Legible gold at every size | — | `hud/DESIGN.md` §5.2 |
| H15 | The Room: one table, three inks (said, kept, agreed), so that the speech rule becomes typography | A stream of settled lines is a viewer for minutes; a table worked together is a place | a stream of settled lines | `hud/DESIGN-ROOM.md` |
| H16 | Said and kept speech live in a store on the machine, outside git and outside `record/`, deleted by the one who said it | Speech is not recorded | speech in the record | `hud/DESIGN-ROOM.md` |
| H18 | Only a person's own agent interrupts, about four times an hour, none closer than fifteen minutes; each agent has a write budget in a room | Agents must not produce more than humans can take in | free interruption | `hud/DESIGN-ROOM.md` |
| H19 | A room is a holon, so one record per room and every holon its own record are one statement | — | a room as a view over other holons | 00 §5; 06 Open |
| H20 | No contractions in any string except the opener "Here's the deal." | A plain, unhurried voice | — | `hud/DESIGN.md` |
| H21 | The printed Deal card follows the brand's card: the mark alone on the front, the Deal on the back | Paper is as good as the screen | — | `hud/DESIGN.md` |

## X. Interoperability

A *house* is a sovereign whole of its own: its own people, agents, tools and stores ([[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|07]] §0).

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| X1 | Houses share files, never a database: the event line, the type registry and the link vocabulary | Each house builds its own interface; the schema and the capabilities are what is shared | a shared service | 07 §0 |
| X2 | Joining is two acts, both recorded: a grant of access, and the joiner's `join` line | Access without a `join` is a read permission, not membership | access as membership | 07 §1 |
| X3 | Only a request, an offer or a commitment carries work across a membrane; a task never does | Assignment happens only inside a holon, by the one who will do the work | cross-holon task assignment | 07 §2–3; 03 §3.1 |
| X4 | A card's identity is the hash of its `card` line; its home is a location; each house's handle is an alias | Identity never depends on where a card lives | numbering per house as identity | 07 §4 |
| X5 | Proposed: a card held by people of two houses lives in the cell its holders form, a full copy in each house | Hosting is a role, not ownership | one house hosts | 07 §4 |
| X6 | Holders change a card; others send a `propose` | — | anyone edits | 07 §4 |
| X7 | Proposed: a commitment across a membrane is recorded in both homes, each carrying the other's id; a mismatch is a finding | — | one copy | 07 §3 |
| X8 | A receiver says back what would work better, as a line | The standard follows practice | silent adaptation | 07 §7 |
| X9 | A design built on different tools is met by a bridge actor that translates and records the translation (a queue, the Change, signed envelopes with elision, semantic merge); proposed, not yet built | Neither side changes its tools | one side adopts the other's | 07 §8 |
| X10 | Leaving is a last line signed by the one who leaves (`leave`, a human-only type), a `release` for each held card, a `revoke` for each delegation | A leaver takes everything they wrote and cannot unsay a commitment made to others | deletion on leaving | 07 §9; `engine/SCHEMA.md`; `engine/rooms.py` |

## S. Security and Sovereignty

| Row | Decision | Reason | Rules out | Where |
|---|---|---|---|---|
| S1 | Instructions about what an agent may do come only from the Living Intelligence it serves and its charter; everything else is data | Reading is the attack surface | trusting authenticated senders | 08 §0; 04 §7 |
| S2 | Reason-origin gating: an act whose reason came from untrusted text is a proposal until a human acts, however reversible | Capability is not authority | trusting the agent's judgment on reversible acts | 08 §2.2 |
| S3 | Sixteen threat classes, each answered by structure | A named threat can be tested | — | 08 §1–2 |
| S4 | Private network first; every server binds to loopback, behind a token and a Host check (RD7); nothing public unless a person published it | — | public services from the start | 08 §2.7 |
| S5 | Relays are never the truth: a relay can withhold or delay, never forge; withholding shows as staleness | Every computation says as of what | trusting the relay | 08 §2.8 |
| S7 | Hygiene for every house: pinned versions, untrusted repositories opened only in sandboxed folders, narrow short-lived tokens, no secret in any record, key backups with a named successor, muted by default | — | — | 08 §4 |
| S9 | Proposed: signed kit releases, and review by someone other than the proposer | The kit is a supply path to every agent | — | 08 §3 |

## Open

Each question with the default the kit carries until it is settled.

| Row | The question | The default carried | Where |
|---|---|---|---|
| W9 | The interoperability floor's size: the floor of two (one seasonal signal, the weekly Turn offered) against the wider set of shared forms the Field already names | the floor of two; the wider set presented as forms the kit already meets | 00 §7; 07 §5, Open 9 |
| W12 | Whether the unit across houses is called *event*, *change* or *commit* | *event*, with a settled line as one event | 00 Open; 01 Open 1; 07 Open 1 |
| W13 | Whether the Change, a signed settled edit, replaces the settled line as the unit in live text | the settled line | 06 Open |
| M7 | The curing period's length, and who may cure what | three days in the Room design; the registry's `curing_days` carries any number | 02 §6, Open 2; 08 Open 7; `hud/DESIGN-ROOM.md` |
| M8 | Whether vouching gets a `vouch` type of its own | the trust graph computed from `join` lines | 02 §7 |
| M11 | Whether the forge runs a server-side check of each repository's policy | each repository proves itself in any clone | 02 Open 6 |
| R3 | Whether the canonical form across houses is JSON or deterministic CBOR | JSON with sorted keys | 01 Open 6 |
| R11 | The form of a real identity | disposable, labeled identities | 01 §4 |
| R28 | Whether a late `done` counts as kept | the kit's pages count kept only when done by the by-when and witnessed; the Engine computes the gap either way | 01 Open 4; `bookshelf/the-record/Commitments Kept.md` |
| R29 | Whether the signed, witnessed lines are the TEA ledger, or are checkpointed into another | the lines themselves | 01 Open 5 |
| P6 | Whether the request and completion fingerprints stay | on, keyed by the holon's salt; off with `hash_bodies: none` | 05 Open 11; 01 Open 9 |
| P8 | Whether the proxy also routes messages among agents | separate planes, joined only by the record | 05 §6; 00 Open |
| P9 | Whether the reference proxy stays the kit's own simplest honest version, or an existing router or open proxy project is adopted | the kit's own | 05 Open 2 |
| P11 | Whether a `discern` the agent signs at the person's recorded consent counts as the person's | counted only from a person | 05 Open 4; 04 Open 5 |
| E8 | How the pledge-and-load gradient sets a calendar's minutes | 480 minutes per day, all seven days | 03 Open 4 |
| E13 | The format in which the system path broadcasts each milestone's float | — | 03 Open 11 |
| E14 | Whether the halving rule stays the buffer sizing | the halving rule | 03 Open 5 |
| E20 | The wording of the standing question that closes every Deal | "What did we miss that matters to you most?" | 03 §6; `engine/deal.py`; `hud/DESIGN.md` |
| E24 | The Turn's four lines | three wordings coexist, in the Engine's draft, the skill and the HUD's design | `engine/turn.py`; `skills/the-turn/`; `hud/DESIGN.md` |
| E27 | The stage vocabulary: should · can · will · did, or with *could*; whether *could* returns as a computed stage | should · can · will · did | 03 Open 2 |
| E28 | Whether there is one registry of card kinds | — | 03 Open 3 |
| A9 | The shape of a whisper between agents | a line in a holon both agents hold, read by each agent's person | 04 §9 |
| A11 | Whether foreground and background bodies sign as one actor under one delegation, or each as a separate actor under a narrower delegation | one actor, one delegation | 04 §11, Open 7 |
| A12 | Whether an agent may hold its person's office | an agent holds an office's preparation, never its act (A1) | 00 Open |
| H4 | A wearer's layout as a line in the record or as a plain file | a `layout` line in the home (human-only in the registry), folded by the HUD's server, undone by a `supersede` | 06 §2.4; `engine/SCHEMA.md`; `hud/serve.py` |
| H8 | Where the person's signing key lives relative to the agent's host: the same device, a separate device, or a secure element | the same device, with distinct human and agent keys | 06 Open; 08 §3, Open 1 |
| H9 | Whether a yes from paper or a photo waits for the person's next signed act, or a witness's initials suffice | written `reason: human`, "from the paper card", unsigned | 06 Open |
| H14 | Whether the derived colour sage is used | not used | `hud/DESIGN.md` §5.2 |
| H15 | The Room's words (the three inks, the Page, the Table, the Talk, Your move), and whether an agent says "I" | used in the Room design as working words | `hud/DESIGN-ROOM.md` |
| H18 | The interruption and write-budget numbers | about four an hour, none closer than fifteen minutes | `hud/DESIGN-ROOM.md` |
| H19 | Whether a room should be a view rather than a holon | a holon | 06 Open |
| X11 | Who is named witness for a commitment kept across houses (the named witness alone verifies, R27) | open between the receiver, a fair witness of a third holon, and one from each house | 07 Open 2 |
| X12 | Doors onto one card, or onto a whole holon | per repository; per card with expiry is the alternative | 07 Open 4 |
| X13 | Identity across houses: an identifier from a first key (XID), or a decentralized identifier (DID) | — | 07 Open 8; 08 Open 4 |
| X14 | The link vocabulary, and which semantic-merge relations are declared | — | 07 Open 7 |
| S6 | Whether human acts require hardware-held keys: now, for irreversible acts only, or later | not required; premature except for irreversible acts | 08 §3, Open 1 |
| S10 | Who runs conformance, and who checks the test (the one who assigns never audits) | — | 08 Open 5 |

## Not yet built

- **One key per body** (R12): each actor holds one key today.
- **The removal tool** for a non-consenting person's name (R14).
- **Encrypted bodies** for lines only a home may read (01 Open 8; 02 Open 1): not designed.
- **The curing period** (M7), as a step before a gathering's export.
- **One `route` vocabulary**: the registry's three fields and the proxy's richer body still differ (P10).
- **The Deal reading the player's place on the Path**: the Deal's order (E18) does not yet weigh it.
- **A supercell's second witness** on the TEA ledger, which needs a registry transition (E25).
- **The made frames** of the holon fields; a code-drawn ring stands in (H12).
- **The store for said and kept speech** (H16).
- **Rate limits per identity, and an admission window**, against flooding an append-only record (08 §3, Open 6).
- **Signed envelopes** that allow elision with an unlinkable proof, after which a names-hidden export may keep each author's signature (RD3).

*The set: [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] · [[01 — The Record (Architecture, 2026-10-24)]] · [[02 — The Membrane (Architecture, 2026-10-24)]] · [[03 — The Game Engine (Architecture, 2026-10-24)]] · [[04 — The Player+ Agent (Architecture, 2026-10-24)]] · [[05 — The Proxy (Architecture, 2026-10-24)]] · [[06 — The HUD (Architecture, 2026-10-24)]] · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]] · [[08 — Security and Sovereignty (Architecture, 2026-10-24)]] · [[10 — The Reviewer's Guide (Architecture, 2026-10-24)]] · [[Index — The Architecture (2026-10-24)]]. Concepts: [[Holon]] · [[Actor]] · [[Actor|Living Intelligence]] · [[Artificial Intelligence]] · [[The Record]] · [[Commitment]] · [[Delegation]] · [[Witness]] · [[Elision]] · [[The Deal]] · [[The Turn]] · [[OmniSpection]] · [[Buffer]] · [[Critical Path]] · [[The Score]] · [[Discernment]] · [[Selectively Permeable Membrane]] · [[ØNE]].*
