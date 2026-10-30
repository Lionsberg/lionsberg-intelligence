---
title: Navigation of Reality — Sightings, Elevation and the Ladders
description: How every Player+ reports what they see, how a cell lifts it by consent, and how decisions are made at the lowest holon able to make them well. Architecture document 11 of the LIØNSBERG Intelligence System.
---

# Navigation of Reality — Sightings, Elevation and the Ladders

*Every [[Player+]] is a navigator. What each one sees on the road is a [[Sighting]], written in the record of the [[Holon]] where it was seen. A [[Cell]] reads its members' Sightings and decides, by consent, what climbs. The shared map of reality is nothing but the fold of every Sighting that every holon has chosen to elevate. Decisions travel the same road in the other direction of need: each is made at the lowest holon able to make it well, and climbs only when it must, one level at a time. No center but [[ØNE]].*

The contract is `engine/SCHEMA.md` (schema v1), its section "Navigation of Reality", and the `sight`, `elevate`, `rfg` and `escalate` types in `engine/types.json`.

## 1. The one idea

A navigation app that crowdsources the road ahead works because every driver is also a sensor: one tap marks a hazard, and the next driver is warned. The Game carries the same idea into every part of life, with two differences that make it its own.

**First, nothing is pooled at a center.** A Sighting lands in the record of the holon where it was seen, and stays there. It reaches a wider holon only when the holon that holds it publishes it upward, by consent, with a witness and a reason. The shared map of reality is not a database anyone owns; it is a computation, at every altitude, over what each holon has elevated into the holons it belongs to.

**Second, the map carries decisions as well as facts.** The same holarchy that lifts what was seen also routes what must be decided. Subsidiarity is the rule: a decision is made at the lowest holon able to make it well, and power is loaned upward only as needed ([[Sovereignty At Every Scale]]). A question that cannot be answered where it arose climbs as a [[Request For Guidance]]; a decision whose consequences reach beyond a holon's remit climbs as an escalation; both climb one level at a time and come back down to be taken up by the holon that sent them.

Three movements, then, on one record, and the act of raising beside them:

| Movement | Its line | Who may sign it | What it carries |
|---|---|---|---|
| **To see** | `sight` | the one who saw, or their agent at their word | what was seen, its kind, where |
| **To lift** | `elevate` | a Living Intelligence of the holon (human-only) | which line, to which holon, why, and the witness |
| **To ask** | `rfg` | any member, or an agent within its delegation | the question, what it is about, to which holon, by when |
| **To raise** | `escalate` | a Living Intelligence of the holon (human-only) | what is to be decided, to which holon, the blast radius, the rung, the time limit |

All four are types in `types.json`. `elevate` and `escalate` are human-only; `rfg` and `sight` are not.

## 2. The Sighting

### 2.1 The eight kinds

There are eight kinds of Sighting, each a road word a ten-year-old can use:

| Kind | What it means |
|---|---|
| **defect** | something broken, or not as it should be (handed in as a gift: [[Every Defect Is A Gift]]) |
| **hazard** | something that could hurt |
| **blocked** | the road is closed here |
| **wonder** | something working, or beautiful, worth showing |
| **offer** | an offer seen in the world, sighted so it travels to whoever needs it |
| **request** | a need seen in the world, sighted so it reaches someone who can meet it |
| **question** | a question asked on the road |
| **witness** | something seen done; how kept work becomes believable |

Beside the row of eight stands one more door, kept apart on purpose: **the pain button**, a request for help that requires a response, never placed on the row of eight. A pain sighting is owed an answer by a person, and the Engine places it in what is owed at once.

The range runs from a hazard to a gift, and a gift is sighted as a *defect*: the broken thing, handed in so it can be mended. The names are still open (see Open). The kinds are data, never code: they are the values of the `kind` field in the type registry, so a holon may add a kind its land needs (a flood watch, a harvest ready) without a build.

### 2.2 What a sight line carries

A `sight` is one event line of SCHEMA v1, in the record of the holon where the thing was seen.

- **`body.text`** (required): what was seen, in the navigator's own words.
- **`body.where`**: the place, at the grain the navigator consents to: an address, a neighbourhood, a region, or nothing. A place is the place of the thing seen; it is never the navigator's own location unless they say so.
- **`body.kind`**: one of the holon's kinds.
- **`body.travel`**: the navigator's own limit on how far this Sighting may go; `types.json` declares `holon` · `members` · `commons` · `public`. Said in words, it is proposed as *stay here* · *may travel without my name* · *may travel with my name*. Elevation never exceeds it.
- **`ts`**: when the navigator says it was seen (a claim, never an order); `actor` and `for`; `audience` (default `holon`); `reason`; the signature.
- **`links.witnesses`**: when this Sighting confirms an earlier one ("I see it too"), the earlier one's id.

### 2.3 Where it lands

In the holon where it was seen. A thing noticed at a cell's gathering lands in the cell's record; a thing noticed on the walk home lands in the person's own home holon, and reaches the cell only when the person publishes it there. A navigator who belongs to many holons chooses which one saw it; the agent suggests the likeliest, and asks when unsure.

### 2.4 The navigator's moment

The HUD gives two ways in, both under ten seconds:

- **One tap.** The row of eight on every view, with the object and the time already filled when the Sighting is made at a card, a line or a place on the map. One more tap sets the travel word; the default is *stay here*.
- **One sentence to the agent.** "There is a fallen tree across the lower trail." The agent drafts the line (kind *blocked*, place *the lower trail*, travel *stay here*), says it back in one line, and writes it when the person says yes.

### 2.5 The agent's part

**The agent never invents a Sighting.** It writes a `sight` only from what its person said or chose, with `reason: human`, and the line answers for that person.

**The agent may propose one.** When something its person said in passing sounds like a Sighting ("the bridge is icy again"), the agent may offer it as a draft: "Mark the bridge as a hazard?" A Sighting the agent drew from text it read (a message, a feed, a page) is written with `reason: untrusted` and folds as a proposal: visible to its person as "drafted from something I read", never counted, never elevated, until the person takes it up as their own. Where analysts run over a world store of public facts, their output is the same: drafted Sightings for a Living Intelligence to see, never Sightings in their own right.

## 3. How a cell processes Sightings

### 3.1 At the Turn and between

At [[The Turn]], the cell's week in review asks *What did we see that we did not expect?*, and the window's Sightings are already on the sheet: the Turn gathers them. That is the steady beat. Between Turns, a hazard, a blocked road or a pain sighting does not wait: it reaches the members whose Deal it touches at their next look, and any member may process it.

### 3.2 Accept, hold, elevate

Every Sighting the cell holds is in one of five states, each computed from lines, never typed:

| State | What made it so |
|---|---|
| **new** | no line yet acts on it |
| **accepted** | the cell takes it as its own: a [[Work Card]] is born that links to it (`serves` or `answers`), or a member's `decide` accepts it |
| **held** | a member's `decide` holds it, with a why and a look-again date; held is a legitimate state, not a failure |
| **elevated** | an `elevate` line names it and the holon it went to |
| **folded** | it has been linked to an earlier Sighting of the same thing, and lives on as that one's further witness |

A Sighting may be accepted and elevated both: the cell clears the fallen tree, and lifts the sighting so the next valley knows the storm came through.

A defect handed in as a gift keeps its whole arc: acknowledged within the day, reproduced before it is fixed, closed by the word of the one who saw it, and leaving a guard so it cannot return unseen.

### 3.3 The witness

An elevation carries a witness: a second Living Intelligence of the cell, other than the one who elevates, who confirms that this Sighting is what the cell means to lift and that lifting it keeps the cell's agreements. The one who assigns never audits; the one who lifts never witnesses their own lift. In a pair, the other is the witness; for a person alone in their home holon, publishing into a cell is the person's own act, and the cell's elevation onward carries the cell's witness.

### 3.4 Believability, read from the record

When a cell weighs a Sighting, the record can say how often this navigator's earlier Sightings of this kind were confirmed by others, and how often their commitments were kept and witnessed. That reading is **positive only**: confirmation adds weight; the absence of confirmation adds nothing and subtracts nothing. A first-time navigator's Sighting is read on its own merits, and a newcomer is never discounted for being new. The reading is visible to the navigator it describes, is never published as a ranking, and never becomes a score of a person. Confirmation counts only from independent sources: two Sightings from the same household, or a person and their own agent, are one source.

### 3.5 Duplicates, folded by link

Two navigators who see the same hazard write two lines. Neither is wrong, and neither is removed. When a navigator sees an existing mark and taps "I see it too", their line carries `links.witnesses` to the first. When the cell finds a duplicate at triage, a member links the later to the earlier the same way (the type of the folding line is open). The folded Sighting shows once, with its count of independent witnesses and its freshest "as of". Nothing is edited or deleted.

### 3.6 What never elevates

- **A private person's particulars.** No person's name, home, health, movements, relationships or circumstances, unless that person has said yes to it in their own words; the non-consenting name is removed wherever it was written, and the removal is recorded (the one exception to append-only).
- **What the posture forbids.** A Sighting made in a room under a names-hidden or sealed posture leaves the room only as the posture allows: under names-hidden, through the elided export; under sealed, not at all.
- **What the navigator's travel word forbids.** *Stay here* stays.
- **What the agent drew from untrusted text** and no person has taken up.
- **A place finer than the navigator consented to.** At every climb the place may coarsen and never sharpen.

## 4. Elevation

### 4.1 Publication upward, by consent, one level at a time

An `elevate` line is a holon publishing one of its lines (a Sighting, or a decision) into the holon above it. Its body names **what** (the line's id), **to** (the receiving holon's id), **why** (in a sentence), and the **witness**. It is human-only: no standing delegation lets an agent lift on a cell's behalf. It goes one level: a cell elevates into its [[Supercell|supercell]], never past it. The supercell, reading what its cells lifted, decides for itself what it lifts further. Every level consents for itself.

The mechanics are SCHEMA's own: the elevating member's agent copies the line, whole and still signed (or as its elided export), into the receiving holon's `published/` or record, and the `elevate` line records the act beside it. A published line never widens its audience except by this separate act of a Living Intelligence.

### 4.2 What the supercell receives

**The face, not the inner record.** The supercell receives the Sighting's kind, its text, its place at the elevated grain, its first and freshest "as of", its count of independent witnesses, the cell it came from, and the cell's why. It does not receive the thread in which the cell discussed it, the members' names (unless each navigator's travel word allows it), or the lines around it. Where names are hidden, the elided export keeps the line's proof: the id and the signature still verify through the salted digests (SCHEMA, "Elision").

### 4.3 The map at every altitude

The shared map of reality is the same computation at every scale, as the [[Critical Path|critical path]] is (see [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]]):

| Altitude | Its map is the fold of |
|---|---|
| **A person** | their own Sightings, and everything elevated into every holon they belong to |
| **A cell** | its members' Sightings published into it, its own, and what its subcells elevated |
| **A body of bodies** | what its member holons elevated into it |

Two holons holding the same lines draw the same map. The map is a lens over sovereign records, never a store of its own: delete it and nothing is lost, because any holon can recompute it. The lens holds no authority.

### 4.4 "As of", and freshness

Every mark on the map says *as of* when it was last seen, in words ("seen this morning", "last confirmed nine days ago"). A Sighting ages by its kind: a hazard or a blocked road fades within days unless someone confirms it still stands; a wonder lasts a season; a question stands until it is answered; an offer or a request stands until it is met or withdrawn. A faded mark is shown as faded, never removed and never presented as current. A confirmation ("still there") is a further witness line, and restores it. Each horizon is data in the holon's agreements.

### 4.5 The world views

The world views are the map of what every holon has elevated, placed on the Earth by `where`. They keep three rules. Omniscience is coupled to focused attention at each holofractal level, never one view for all. Confirmation comes only from independent sources. The instrument informs while people discern. And every mark is there because a holon chose to lift it: the consent path runs beneath the whole view.

## 5. Decisions at the right level

### 5.1 Subsidiarity is the rule

Each decision belongs to the lowest holon able to make it well. The person decides what only the person can; the pair what the pair can; the cell what the cell can; the supercell only what no one of its cells can hold alone. A higher holon never reaches down to take what a lower one can hold; the seizure of competence by a higher level is the sign of drift the Pattern is built to resist ([[Structural Immunity]]). A higher holon never writes into a lower holon's record, and never overrides its state; it decides in its own record, and the lower holon takes the decision up in its own.

The first rung of every ladder is the pair a Player+ already is: a person and their agent. The agent's delegation is its remit. What the delegation covers, the agent does, and the line itself, signed by the agent with `reason: delegated` and the delegation it rests on, is the signed receipt of its authority: every delegated line carries one. What the delegation does not cover, the agent raises to its person: what is reversible and small gets done, what is irreversible or wide gets raised.

### 5.2 The ladder, as data in each holon's Field of Agreements

Each holon keeps its own ladder as a part of its [[Field of Agreements]], agreed by its people and folded like any other agreement. The ladders are data, never a center's rule. A ladder names, for each rung:

- **the holon** at that rung (this cell; its supercell's council; a wider body);
- **its remit**: which decisions are its own, read from the blast radius;
- **how it decides**: consent (the default), the keeper alone for the reversible and small, or another way its people chose;
- **its time limit**: how long a raised decision may wait there;
- **what happens at the limit** (§5.4).

A ladder is never imposed from above. A supercell may offer its cells a ladder; each cell adopts, amends or declines it by its own process. Where SCHEMA names no file for the Field of Agreements, the ladder lives as the holon's agreed lines, and a plain face beside `holon.json` may render it.

### 5.3 The request for guidance

A question a holon cannot answer well on its own climbs as an `rfg`: `question` · `about` (the card or line it concerns) · `to` (the holon one level up, or a [[Guide Cells|Guide Cell]] whose domain it is) · `by` (when the answer is needed). It is the building trades' request for information, kept for its one great virtue, a question with accountability, and joined to the canon's understanding: a request for guidance does not bind the receiver to answer, and guidance does not bind the asker to follow it; the asker remains the decider ([[Request For Guidance]]).

- **Ball-in-court.** From the moment the `rfg` is written, the receiving holon holds the ball: the Engine places the question in what is owed by that holon, with its by-when, and the asker sees it in what it waits on.
- **Closed by an `answer` or a `decide`.** An `answer` linked by `answers` gives guidance, with its confidence and its reasoning. A `decide` is used when the question was truly the receiver's to decide. Either closes it; the asker's own decision that follows links to both.
- **An overdue question.** Past its by-when, the question shows as overdue on both sides, and the asker's Deal offers three ways: decide here with what is known, the unanswered question linked as the record of having asked; ask again, with a new by-when; or climb one further level, with a new `rfg` linked to the first as its predecessor. An overdue question never climbs by itself unless the asking holon's ladder says so; where it does, the agent writes the climb within its delegation, and the asker sees it said. A change of whose turn it is reaches the people concerned; nothing nags.

### 5.4 Escalation by blast radius

A decision whose blast radius exceeds the holon's remit climbs as an `escalate`: `about` (the decision's card or line) · `to` (the holon at the next rung) · `blast_radius` (in words) · `rung` · `by` (the time limit).

**Blast radius** is how many it affects and how reversible it is. It is read in three questions: Whom does it touch: only us, other holons, or people outside the Game? Can it be undone, and at what cost? Does it spend what is held in common? A decision that touches only the holon and can be undone within the week is the holon's own. One that touches other holons, cannot be undone, or spends the commons climbs to the rung its ladder names. Who judges the radius is itself named in the ladder: a member's reading, confirmed by a witness; a rule may suggest the rung, and a person settles it.

**The rung** is the ladder's step for that radius. **The time limit** is the by-when on the decision at that rung.

**The way back down.** The higher holon decides in its own record (`decide`, linked by `answers` to the escalation). The holon that raised it takes the decision up as its own with a `ratify` in its own record. Ratification is the holon's consent; until it is given, the decision is a decision of the higher holon about a matter of the lower one, and both records say so. A holon that cannot ratify says why in a thread anchored to both lines; a disagreement is carried through governance, never resolved by copying the work and walking away, and leaving is always open.

**At the time limit** (proposed), the decision comes back down undecided, and the holon's ladder says what follows: what is reversible returns to the holon to decide by its own lights, with the escalation linked; what is irreversible is held until decided. Nothing irreversible is done because a clock ran out.

### 5.5 The Council: where a cell's remit ends

The rung above a cell is the **Council** of its supercell (proposed): the holon formed by the supercell's member cells, each sending one of its members by its own process, the seat rotating. The Council decides what no one cell can hold alone, and only that. The canon's [[Wisdom Council]] (three to thirteen advisors, reaffirmed every ninety days) stands beside it to advise on significant decisions; it guides, protects and shepherds, and does not command. A Council's remit is written in the supercell's Field of Agreements by the consent of its cells, and every cell may withdraw from it.

### 5.6 Believability-weighted approval: an option, never a default

A holon may adopt believability-weighted approval for a class of decisions: each voice weighted by what the record shows of that person's judgment in that domain (commitments kept and witnessed, Sightings confirmed, guidance that proved sound). It is an option written into a holon's ladder by the holon's own consent, never a default and never imposed by a supercell. Where adopted, the weights are read positive only, visible to the person weighted, recomputed from the record at each decision, and never published as a ranking. The default way of deciding remains discernment and consent around proposals.

## 6. What crosses houses

A *house* is a sovereign whole with its own people, agents and tools (see [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]]). Navigation crosses houses on the same path as everything else.

- **Sightings elevated across membranes.** Two houses share no database. A Sighting crosses into another house only by being elevated into a holon both houses hold: a cell of their own, each house keeping a full copy of its record. The `elevate` line is the crossing; the [[Selectively Permeable Membrane|membrane]] holds everywhere else.
- **The shared map between two houses** is the fold of what each has elevated into the holon they share. Each house draws it with its own tools; holding the same lines, both draw the same marks. A kind one house uses and the other has not declared is shown as written, kept, and folded into nothing until declared.
- **Who witnesses across.** An elevation into a shared holon carries a witness from the elevating house. A Sighting confirmed by a navigator of the other house is marked *seen by both houses*, the strongest confirmation the map knows, because the sources are independent by construction (proposed). Whether a cross-house elevation also needs a witness from the receiving house is open, with the wider question of witnessing across houses.
- **Escalations and requests for guidance across houses** go to a shared holon, never into another house's own record. A house is never a rung on another house's ladder unless both have written it so.

## 7. The engine

The Engine stays a set of pure functions over lines, the same by pencil (see [[03 — The Game Engine (Architecture, 2026-10-24)|The Game Engine]]). The fold carries `sightings` in STATE v1, and the Turn gathers them. Triage and the ladder are built (`engine/sightings.py`, `engine/ladder.py`, where the ladder's function is `rung`); the shapes below are proposed, and the map is not yet built.

- **`triage(items, holon) → {new, accepted, held, elevated, folded}`.** Each of the holon's Sightings in exactly one state, computed from the lines that act on it (§3.2), each with its kind, place, freshness, count of independent witnesses and as of. A Sighting the holon received by elevation from below is listed apart, as *received*.
- **`ladder(decision, field) → {rung, holon, by, how}`.** A pure function: from a decision's blast radius (its three answers) and the holon's ladder as agreed, which rung the decision belongs to, at which holon, with what time limit and how that holon decides. It suggests; a person settles. Given the same ladder and the same answers, every holon computes the same rung.
- **The overdue questions in what is owed.** `owed` carries one kind, `question`, covering both an `rfg` and an `escalate` past its by-when and not yet answered or decided: it is owed by the holon it climbed to, held by that holon's keeper. Its by-when is the line's own, else the rung's time limit; an overdue one reaches the Deal of the person who holds it. The asker's side shows what it waits on.
- **The map.** `map(items, altitude) → marks`: the fold of elevated Sightings into the holons at that altitude, folded by witness, placed by `where`, faded by kind, each with its as of.

**The paper floor.** Navigation runs with no machine at all.

- **A sightings sheet**, one Sighting per line: time · who · kind · what · where · travel · state (new · accepted · held · elevated · folded) · witness · to. A cell works it at the Turn with a pencil; an elevation is a line copied onto the supercell's sheet, initialled by the witness.
- **A ladder drawn on one page**: the rungs as rows, and for each its holon, its remit, how it decides and its time limit; above them, the three blast-radius questions as a short path to follow down the page. A question asked of another holon is a line on the sheet with its by-when and whose turn it is; the overdue are circled at the Turn.

A witnessed paper sheet beats the typed copy.

## 8. The HUD

The HUD shows; it never computes (see [[06 — The HUD (Architecture, 2026-10-24)|The HUD]]).

- **Sightings as marks on the field, in the Map.** Each mark in the Map of cells and quests and in the world views carries its kind by shape and word, never by colour alone; freshness is a fade with its words ("seen this morning"); a folded mark shows its count of witnesses. Pressing a mark opens its face: what, where, as of, from which holon, and why it was lifted. The list twin carries the same marks as rows for every reader. No mark ever shows a member's location or a name the navigator's travel word withholds.
- **The Deal card that asks "elevate?".** When a Sighting in the wearer's cell is new and its kind or its witnesses suggest it matters beyond the cell, the Deal may carry one card: *A sighting from this week: the lower trail is blocked. Lift it to the supercell?* Options: **Lift it** (with the why drafted and a witness to ask) · **Keep it in the cell** · **Hold it**, one marked *suggested* with its reason in a line. The lift is the wearer's own act, signed by their key on the act path, through the publish sheet that says plainly who will see it. The same card shape serves a question that came due, *Your question to the supercell is two days overdue*, and a decision returned for ratification.
- **The Council's view** (proposed). For a holon at a Council's rung: the escalations and requests for guidance addressed to it, ordered by time limit, each with its blast radius in words and the holon that raised it; what it decided, and which holons have ratified; and the map of what its member cells elevated this season. It shows faces only: never a member cell's inner record.

## Open

1. **The kinds' names.** Eight kinds (defect · hazard · blocked · wonder · offer · request · question · witness), with the pain button apart, and a gift sighted as a defect. The kind *witness* shares its word with the `witness` event type, and the kinds *offer* and *request* share theirs with the holon's own `offer` and `request` types; each pair needs either distinct words or a sentence that holds them apart.
2. **The rung count.** Person-and-agent · holon · Council · wider body. Each holon may differ; whether a default ladder ships in the kit, and with how many rungs, is open.
3. **Time limits.** The default by-when for a request for guidance and for an escalation at each rung; and what happens at the limit, beyond reversible returns and irreversible holds.
4. **Believability's formula.** What it reads (kept and witnessed commitments, confirmed Sightings, guidance proved sound), over what window, in which domains, and how independence of sources is decided.
5. **What the first week elevates.** Recommended: nothing by default; cells practise sighting and triage at their Turn, and the first lifts are defects in the kit itself, handed to the holon that builds it.
6. **Who judges blast radius.** Rule, person, or both; the design here is a member's reading with a witness, a rule only suggesting.
7. **The folding line and the triage lines.** Which type folds a duplicate, and which records *accept* and *hold* (this page reads them as `decide`; the decide body is not yet specified).
8. **The travel word.** The `travel` field on `sight` is declared with the four audiences (`holon` · `members` · `commons` · `public`), which say how far a Sighting may go but not whether the navigator's name goes with it. Open: how the three travel words map onto it, and whether the travel word is also a setting of the person.
9. **The Council's composition.** One seat per cell, rotating; how it relates to the canon's Wisdom Council and to a supercell's keeper is open.
10. **Where the ladder lives.** SCHEMA names no file for a holon's Field of Agreements.
11. **Witnessing across houses**, for elevations into a shared holon, as in [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]].

## Not yet built

- The *accepted* and *received* states of triage.
- The map at every altitude, with freshness fading by kind.
- Believability read from the record, and believability-weighted approval.
- The world views.

*Siblings: [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)|The System]] · [[01 — The Record (Architecture, 2026-10-24)|The Record]] · [[02 — The Membrane (Architecture, 2026-10-24)|The Membrane]] · [[03 — The Game Engine (Architecture, 2026-10-24)|The Game Engine]] · [[04 — The Player+ Agent (Architecture, 2026-10-24)|The Player+ Agent]] · [[06 — The HUD (Architecture, 2026-10-24)|The HUD]] · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]] · [[08 — Security and Sovereignty (Architecture, 2026-10-24)|Security and Sovereignty]] · [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)|Decisions and Their Reasons]] · [[Index — The Architecture (2026-10-24)|The Architecture]].*
