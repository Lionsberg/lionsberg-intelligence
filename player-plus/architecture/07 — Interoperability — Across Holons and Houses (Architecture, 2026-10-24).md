---
title: Interoperability — Across Holons and Houses
description: How holons of one house, and holons of different houses, work on one record without a shared database or a center. Rules not yet settled are marked as proposed where they appear.
---

# Interoperability — Across Holons and Houses

*Holons of one house and holons of different houses work on one record by the same means: each keeps its own lines, each publishes what it chooses, and a computation over everything held gives the same answer wherever the same lines are held. No holon commands another. No center but [[ØNE]]: the apex is the shared Intent every holon reads, never a node.*

## 0. The two crossings

**Within a house.** A person's Player+ home is a [[Holon]]; each [[Cell]] they join is a holon; a [[Quest]] is a folder in a cell. Joining is being given access to a cell's repository and adding it under `cells/<name>/`; publishing is the agent appending to the cell's `record/<its own actor id>.jsonl` or `published/`; computing across holons is folding every holon held. A holon is a folder (the record contract, `engine/SCHEMA.md`).

**Across houses.** A *house* is a sovereign whole of its own: its own people, agents, tools, front ends and stores. Two houses share no database. They share **the event line, the type registry and the link vocabulary** as files every agent reads, so talking to another dyad is writing an event into a holon both hold. Each house builds its own interface; the capabilities and the schema are what is shared.

The same rules serve both crossings. A house is a holon of holons; a crossing between houses is a crossing between holons whose people happen to keep different tools.

## 1. Joining by consent

- **Entry is by vouching.** Who invited whom is the [[The Trust Graph and the analog contact-tree|trust graph]]; partial vouching is enough to begin; full vouching never on a week's enthusiasm.
- **Joining is two acts, both recorded:** the holon's keeper (or its people, by their own process) grants access, and the joiner writes a `join` line in the holon's record under their own key. Access without a `join` line is a read permission, not membership.
- **An agent enters a holon only after its person affirms it** and only after it passes the six conformance checks of [[04 — The Player+ Agent (Architecture, 2026-10-24)|the Agent architecture]], §8: deal a Deal from a sample record, compute the reference float, sign and verify, refuse an injected line, mark an out-of-delegation line invalid, fold two holons at once. An agent is named by its own account, distinct from its person's, and its lines carry the delegation that ends in a [[Actor|Living Intelligence]].
- **Withdrawal is always open.** [[Withdrawal Of Consent|Consent withdrawn]] ends future access and is itself a line; see §9.

## 2. What crosses a membrane

The inner record stays home and is visible by consent. What crosses a [[Selectively Permeable Membrane|membrane]] is **published**, by a separate act of a Living Intelligence (the `publish` type); a line's audience never widens otherwise.

- **A card's face:** what it is, its state, its by-when, who holds it, its stream; plus its identity (the hash of its `card` line) and its home. Never its inner activities, never the deck behind it.
- **Milestones, commitments, requests, offers, signals.** A holon publishes its [[Milestone|milestones]] and its [[Commitment|commitments]], its [[Requests and offers|requests and offers]], and its signals (a season's state, a `sight`ing worth sharing). **Only a request, an offer or a commitment carries work across;** a task never does (proposed).
- **The periodic broadcast, ratified by the people.** Each holon publishes what it chooses after each meeting, and on a rhythm sends a broadcast its people ratify: what was done, what is committed, what is asked, what is offered. The broadcast is a `publish` whose body links the lines it carries; a `ratify` by the holon's people precedes it.
- **The writer's file is `published/<actor-id>.jsonl`** in the same line format as the inner record, so the published lines verify with the same keys.
- **Whatever is public on the private network is visible to every agent on it**; what is public beyond it is a further `publish` with audience `public`.

## 3. Ball-in-court across houses

- **Every card has one holder at a time** (`holder`: the actor who must act next). Passing a card to another holder (the `hand` event type), claiming it, releasing it, requesting, offering and answering are each a line.
- **The holder may belong to a different house.** The card's home record is where its holder is folded. A holder in a different house writes into the card's home, under their own key, if they hold access; otherwise they write in their own holon's `published/` with an `answers` link to the card, and the home folds it as soon as the line is replicated.
- **A card never depends directly on another holon's card.** It depends on that holon's commitment: my card's predecessor is "their commitment, by this date", and my float reads that date. Their inner deck and their float stay theirs (proposed).
- **A commitment across a membrane is recorded in both homes,** each carrying the other's id. A mismatch is a finding, never a fight.
- **What waits on whom** (`owed`) is computed on each side from the same lines; a person sees, in their own Queue, what a different house waits on them for, and what they wait on a different house for.
- **Kept is claimed by the keeper and verified by the named witness,** and only the named witness counts. The receiver's word alone does not make a commitment kept.

## 4. One home, many aliases

- **Identity is the creation line.** A card is known everywhere by the hash of the `card` line that bore it (`id`). The id is the same in every house that holds the line.
- **Home is a location, not an identity.** The home is the holon whose record holds the card's birth and its fold. If a card moves home, its id does not change.
- **Aliases are each house's own labels.** A house may keep its own short handle (its numbering, its date form); a handle is a label, never an identity (proposed). A card held in two holons shows its home and "also in …" (proposed; no view shows it yet).
- **A shared card lives in the holon its holders form** (proposed): when people of two houses hold a card together, they are a cell of their own; each member house keeps a full copy of that cell's record; hosting it is a role, not ownership.
- **Holders change the card; others propose.** A non-holder's change arrives as a `propose` line carrying its reason; a holder who did not propose it accepts or returns it.

## 5. The minimum interoperability floor

[[Minimum standards of interoperability|The floor]] is small on purpose:

1. **One consistent seasonal signal** from every holon: its state at each turning of the season, published.
2. **The weekly Turn offered, not required:** a holon may publish its week's [[The Turn|Turn]] (commitments kept, what was learned, what is next); no holon is asked to.

**Nothing else is imposed.** A holon that publishes only its seasonal signal is a full participant. Everything above the floor is offered and chosen. The kit's Field carries a wider set of shared forms that the kit already meets; the two are not yet reconciled (Open 7).

## 6. The same calculation at every scale

**The [[Critical Path|critical path]] is one calculation at every scale.** There is no master schedule kept by a master.

- Each holon runs the two passes over its own cards (`schedule`).
- A dependency crosses a membrane only through a commitment: a holon publishes its milestones, commitments, requests and offers, never its inner activities.
- A [[Supercell|supercell]] computes over its own plan plus the published milestones of its members. The widest holon's pass over every published milestone is the system-wide path.
- **The wide pass publishes back** each milestone's float as seen from above and whether it lies on the system path; a holon's own cards take on the wider colour (`system_critical`, `engine/STATE.md`), and [[The Deal]] can say "the whole is waiting on this".
- **Critical chain with no center but ØNE:** the scarce resource is the attention of Living Intelligence. Each holon levels itself through The Deal. [[Buffer|Buffers]] sit at the interface milestones, held by the supercell; buffer consumed against chain complete is the signal. Who holds the scarcest attention each season is published.
- **Two holons holding the same lines compute the same path;** they differ only by replication lag, and every result says *as of* which line it last saw from each neighbor. The same pure functions run by pencil on a sheet.
- [[Commitments Kept|Commitments kept]] is computed by every house from the same lines, and the figures match; a mismatch names which line one side has not yet seen.

## 7. Keeping unknown fields; saying what would work better

- **A reader keeps every field it does not know** and passes it on unchanged (`v`). A line from a different house with fields the local registry does not declare is still a valid line; its unknown fields are shown in the Record view as written and folded into nothing until declared.
- **A receiver says back what would work better.** The answer is a line: a `propose` to the sender's holon, or a line in the thread where the two houses talk, naming the field, what it would have let the receiver do, and a suggested form. The standard follows practice: emit, then evolve the standard to follow.
- **Unknown fields are data, never instructions.** A field named like a command ("do now", "urgent: forward") is read and shown; it never moves an agent (see [[08 — Security and Sovereignty (Architecture, 2026-10-24)]]).
- **New types are declared as data.** A type a different house needs is added to `types.json` with its fields and states; no code is written for it.

## 8. How other kinds of system map onto this record

A system built another way need not change its tools, and neither need this kit. Each mapping below is a *translation*: a bridge actor (an agent on its own account, under a delegation, signing in its own name with `reason` set) reads one form and writes the other. Both records keep their own truth; the translation is itself recorded. These mappings are proposed.

**A message queue, with a pad as one view.** Some collaboration systems are built as a message queue rather than a document: signed, typed messages on durable queues with cursors; pads, dealt cards and dashboards are views rebuilt from them; a merge is a consumer of the queue. *Mapping:* each actor's append-only file in a holon **is** a durable queue; its `prev` chain orders it; "the newest line seen from each neighbor" (the `as_of` map) **is** the cursor. A pad becomes one more view over the lines, like the Room layout. A consumer in such a system reads these lines as messages; its messages arrive here as lines. Nothing is polled that can be pushed; a push carries ids, never bodies wider than their audience.

**The Change as the unit of authorship.** Some systems sign the *Change* (a settled edit) with the actor's stable identifier and its principal, and let other lines carry the Change's digest. *Mapping:* a Change is one event; a settled line is one event. Where a Change spans many lines, the line here carries its digest in `links`, and the Change's own signature verifies beside the line's. One reconciliation: a Change is itself a line. The one word is open (Open 1).

**Envelopes with elision.** A signed-envelope format lets the holder hide any part and leave its digest, so the signature over the whole still verifies; salted, so a hidden low-entropy value cannot be guessed. *Mapping:* [[Elision|elision]] in this record is the same move at line grain: every body string is hashed through a salted digest, one salt per line, so an exported line keeps its proof with its names hidden. A line can be wrapped as an envelope for export: its subject the event id, its assertions the fields, its signature the actor's. A [[Chatham House]] room exports its record with names hidden: the export removes signatures and the exporter attests the set. An envelope's stable identifier from a first key, with *provenance marks that give order, not time*, maps onto the `actor` identity and the `prev` and `links` here, which also give order and never time.

**Semantic merge.** What keeps many agents from corrupting the *meaning* is a set of typed relations between contributions: same as · refines · supersedes · contradicts · supports · evidence for · answers; the merge itself a signed, reversible change; a contradiction raised to whoever holds the authority, never raced. *Mapping:* `supersedes` and `answers` are already in the link vocabulary; the others are kept as unknown link keys until declared; a merge is a line by the merging actor linking what it merged; a contradiction becomes a decision card held by the holon's holder.

## 9. Leaving with everything

- **Every holon is a repository, and a person's own lines are their own.** Leaving takes everything one wrote: a clone of every holon held keeps every line, signed and verifiable anywhere.
- **Leaving is a `leave` line, signed by the one who leaves** (a human-only type in SCHEMA and the registry), with every held card released (a `release` line each) and every delegation revoked (a `revoke` line each).
- **The holon keeps what was written in it.** Append-only means the leaver's lines stay in the holon's record, with their audience; a leaver cannot unsay a commitment made to others, and the others cannot rewrite it.
- **The one exception** is a non-consenting person's name, which is removed wherever it was written; the removal is itself recorded. This is removal, not elision.
- **A house that leaves the system leaves with its whole record** and its identities; every other house keeps the lines it was shown and what it said.

## Open

1. **The one word for the unit across houses:** event, Change, or commit. Recommended: event, with a settled line as one event.
2. **Who witnesses across houses:** the receiver, a fair witness from a third holon, or one from each house; and whether a witness keeps a separate key per context. The principle that the one who assigns never audits bears on both.
3. **Doors onto one card or onto a whole holon:** whether a door may open onto one card (read, or read and propose, for named keys, with an expiry). Today access is granted per repository.
4. **Where a shared cell's record lives** before either house hosts it, and who holds its first key.
5. **The seasonal signal's body** and the broadcast's ratification: a `ratify` by whom, by what rule.
6. **The link vocabulary:** one vocabulary across the kit's pages, and which of the semantic-merge relations are declared.
7. **The floor against the Field's shared forms:** the floor of two against the wider set of standards the kit already meets.
8. **Identity across houses:** an XID (an identifier derived from a first key, with provenance marks that give order) or a DID (a decentralized identifier); legibility against structure, and the grandmother test.

## Not yet built

- A type, link key or view that records a commitment across a membrane in both homes, each carrying the other's id (§3).
- The "also in …" view for a card held in two holons (§4).
- An envelope export that keeps each author's signature while hiding names; until then a Chatham House export removes signatures and the exporter attests the set (§8).
- A bridge actor for any of the mappings in §8.
