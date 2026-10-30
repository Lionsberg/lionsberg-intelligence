---
title: Navigation of Reality — Sightings, Elevation and the Ladders
description: How every Player+ reports what they see, how a cell lifts it by consent, and how decisions are made at the lowest holon able to make them well. Architecture document 11 of the LIØNSBERG Intelligence System.
---

# Navigation of Reality — Sightings, Elevation and the Ladders

*Every [[Player+]] is a navigator. What each one sees on the road is a [[Sighting]], written in the record of the [[Holon]] where it was seen. A [[Cell]] reads its members' Sightings and decides, by consent, what climbs. The shared map of reality is nothing but the fold of every Sighting that every holon has chosen to elevate. Decisions travel the same road in the other direction of need: each is made at the lowest holon able to make it well, and climbs only when it must, one level at a time. No center but [[ØNE]].*

The contract is `engine/SCHEMA.md` (schema v1), its section "Navigation of Reality", and the `sight`, `elevate`, `rfg` and `escalate` types in `engine/types.json`. What the fold computes from them is `sightings`, `questions` and `ladders` in `engine/STATE.md`.

## 1. The one idea

A navigation app that crowdsources the road ahead works because every driver is also a sensor: one tap marks a hazard, and the next driver is warned. The Game carries the same idea into every part of life, with two differences that make it its own.

**First, nothing is pooled at a center.** A Sighting lands in the record of the holon where it was seen, and stays there. It reaches a wider holon only when the holon that holds it publishes it upward, by consent, with a witness and a reason. The shared map of reality is not a database anyone owns; it is a computation, at every altitude, over what each holon has elevated into the holons it belongs to.

**Second, the map carries decisions as well as facts.** The same holarchy that lifts what was seen also routes what must be decided. Subsidiarity is the rule: a decision is made at the lowest holon able to make it well, and power is loaned upward only as needed ([[Sovereignty At Every Scale]]). A question that cannot be answered where it arose climbs as a [[Request For Guidance]]; a decision whose consequences reach beyond a holon's remit climbs as an escalation; both climb one level at a time and come back down to be taken up by the holon that sent them.

Three movements, then, on one record, and the act of raising beside them:

| Movement | Its line | Who may sign it | What it carries |
|---|---|---|---|
| **To see** | `sight` | the one who saw, or their agent at their word | what was seen, its kind, where, how far it may travel |
| **To lift** | `elevate` | a Living Intelligence of the holon (human-only) | which line, to which holon, why, and the witness |
| **To ask** | `rfg` | any member, or an agent within its delegation | the question, what it is about, to which holon, by when |
| **To raise** | `escalate` | a Living Intelligence of the holon (human-only) | what is to be decided, to which holon, the blast radius, the rung, the time limit |

All four are types in `types.json`. `elevate` and `escalate` are human-only; `rfg` and `sight` are not. The fold holds to it: an `elevate` written by an agent, or drawn from untrusted text, lifts nothing, and an `escalate` counts only when a person signs it in their own name.

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
- **`body.kind`**: one of the eight, or a kind the holon has declared.
- **`body.travel`**: the navigator's own limit on how far this Sighting may go. Said in words, it is *stay here* · *may travel without my name* · *may travel with my name*; `types.json` declares the field with four values, `holon` · `members` · `commons` · `public` (see Open). Elevation never exceeds it.
- **`ts`**: when the navigator says it was seen (a claim, never an order); `actor` and `for`; `audience` (default `holon`); `reason`; the signature.
- **`links`**: when this Sighting is a further sighting of an earlier one ("I see it too"), it links to the earlier one's id, and the fold folds it into that one (§3.5).

### 2.3 Where it lands

In the holon where it was seen. A thing noticed at a cell's gathering lands in the cell's record; a thing noticed on the walk home lands in the person's own home holon, and reaches the cell only when the person publishes it there. A navigator who belongs to many holons chooses which one saw it; the agent suggests the likeliest, and asks when unsure.

### 2.4 The navigator's moment

The HUD gives two ways in, both under ten seconds:

- **One tap.** The row of eight on every view, with the object and the time already filled when the Sighting is made at a card, a line or a place on the map. One more tap sets the travel word; the default is *stay here*.
- **One sentence to the agent.** "There is a fallen tree across the lower trail." The agent drafts the line (kind *blocked*, place *the lower trail*, travel *stay here*), says it back in one line, and writes it when the person says yes.

In a Room, a said line can become a Sighting: *Make it a sighting* drafts it from the line, the people at the table choose its kind, and *Agree the sighting* puts it on the table. That gesture is built; it carries the kind, and not yet a travel word or a place.

### 2.5 The agent's part

**The agent never invents a Sighting.** It writes a `sight` only from what its person said or chose, with `reason: human`, and the line answers for that person.

**The agent may propose one.** When something its person said in passing sounds like a Sighting ("the bridge is icy again"), the agent may offer it as a draft: "Mark the bridge as a hazard?" A Sighting the agent drew from text it read (a message, a feed, a page) is written with `reason: untrusted` and folds as a proposal: visible to its person as "drafted from something I read", never counted, never elevated, until the person takes it up as their own. Where analysts run over a world store of public facts, their output is the same: drafted Sightings for a Living Intelligence to see, never Sightings in their own right.

## 3. How a cell processes Sightings

### 3.1 At the Turn and between

At [[The Turn]], the cell's week in review asks *What did we see that we did not expect?*, and the window's Sightings are already on the sheet: the Turn gathers them. That is the steady beat. Between Turns, a hazard, a blocked road or a pain sighting does not wait: it reaches the members whose Deal it touches at their next look, and any member may process it. The Deal deals a new Sighting to the keeper of its holon (see Open).

### 3.2 Hold, elevate, fold, and accept

Every Sighting the cell holds is in one of four states, each computed from lines, never typed:

| State | What made it so |
|---|---|
| **new** | no line yet acts on it |
| **held** | a member's `thread` note is anchored to it, saying why it is held; held is a legitimate state, not a failure |
| **elevated** | a person's `elevate` line names it, and the holon it went to |
| **folded** | it links to another Sighting of the same thing, and lives on as that one's further witness |

Each Sighting shows one state at a time: elevated over held, held over folded, folded over new.

The design carries a fifth state, **accepted**: the cell takes the Sighting as its own, when a [[Work Card]] is born that links to it (`serves` or `answers`), or a member's line accepts it. A Sighting may then be accepted and elevated both: the cell clears the fallen tree, and lifts the sighting so the next valley knows the storm came through. The fold does not compute it yet (see Not yet built).

A defect handed in as a gift keeps its whole arc: acknowledged within the day, reproduced before it is fixed, closed by the word of the one who saw it, and leaving a guard so it cannot return unseen.

### 3.3 The witness

An elevation carries a witness: a second Living Intelligence of the cell, other than the one who elevates, who confirms that this Sighting is what the cell means to lift and that lifting it keeps the cell's agreements. The one who assigns never audits; the one who lifts never witnesses their own lift. In a pair, the other is the witness; for a person alone in their home holon, publishing into a cell is the person's own act, and the cell's elevation onward carries the cell's witness.

### 3.4 Believability, read from the record

When a cell weighs a Sighting, the record can say how often this navigator's earlier Sightings of this kind were confirmed by others, and how often their commitments were kept and witnessed. That reading is **positive only**: confirmation adds weight; the absence of confirmation adds nothing and subtracts nothing. A first-time navigator's Sighting is read on its own merits, and a newcomer is never discounted for being new. The reading is visible to the navigator it describes, is never published as a ranking, and never becomes a score of a person. Confirmation counts only from independent sources: two Sightings from the same household, or a person and their own agent, are one source.

### 3.5 Duplicates, folded by link

Two navigators who see the same hazard write two lines. Neither is wrong, and neither is removed. When a navigator sees an existing mark and taps "I see it too", their line links to the first, and the fold folds it into the first when the link is `anchored_to`, `serves`, `supersedes` or `predecessor`. When the cell finds a duplicate at triage, a member links the later to the earlier (which line a member writes for it is open). The folded Sighting is counted in the one it folds into and shows once, with its count of independent witnesses and its freshest "as of". Nothing is edited or deleted.

### 3.6 What never elevates

- **A private person's particulars.** No person's name, home, health, movements, relationships or circumstances, unless that person has said yes to it in their own words; the non-consenting name is removed wherever it was written, and the removal is recorded (the one exception to append-only).
- **What the posture forbids.** A Sighting made in a room under a names-hidden or sealed posture leaves the room only as the posture allows: under names-hidden, through the elided export; under sealed, not at all.
- **What the navigator's travel word forbids.** *Stay here* stays.
- **What the agent drew from untrusted text** and no person has taken up.
- **A place finer than the navigator consented to.** At every climb the place may coarsen and never sharpen.

## 4. Elevation

### 4.1 Publication upward, by consent, one level at a time

An `elevate` line is a holon publishing one of its lines (a Sighting, or a decision) into the holon above it. Its body names **what** (the line's id), **to** (the receiving holon's id), **why** (in a sentence), and the **witness**. It is human-only: no standing delegation lets an agent lift on a cell's behalf, and the Engine drafts the line unsigned for a person to sign. It goes one level: a cell elevates into its [[Supercell|supercell]], never past it. The supercell, reading what its cells lifted, decides for itself what it lifts further. Every level consents for itself.

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

Each holon keeps its own ladder as a part of its [[Field of Agreements]], agreed by its people. The ladders are data, never a center's rule. A ladder names, for each rung:

- **the holon** at that rung (this cell; its supercell's council; a wider body);
- **its remit**: which decisions are its own, read from the blast radius;
- **how it decides**: consent (the default), the keeper alone for the reversible and small, or another way its people chose;
- **its time limit**: how long a raised decision may wait there;
- **what happens at the limit** (§5.4).

A ladder is never imposed from above. A supercell may offer its cells a ladder; each cell adopts, amends or declines it by its own process.

**Where it lives, and the default.** A holon's ladder is `ladder.json` beside its `calendar.json`, else a `ladder` list inside `calendar.json`. Each rung there is its step, its name, its remit (the widest blast radius it may decide) and its time limit in days. A holon that has written none reads the default ladder the kit ships:

| Rung | Name | Its remit | Its time limit |
|---|---|---|---|
| 0 | **person** | what touches only the person | 1 day |
| 1 | **cell** | what touches the pair, the room or the cell | 7 days |
| 2 | **council** | what touches several cells, the supercell | 14 days |
| 3 | **body** | what touches the wider body, the commons, the public | 30 days |

### 5.3 The request for guidance

A question a holon cannot answer well on its own climbs as an `rfg`: `question` · `about` (the card or line it concerns) · `to` (the holon one level up, or a [[Guide Cells|Guide Cell]] whose domain it is) · `by` (when the answer is needed). It is the building trades' request for information, kept for its one great virtue, a question with accountability, and joined to the canon's understanding: a request for guidance does not bind the receiver to answer, and guidance does not bind the asker to follow it; the asker remains the decider ([[Request For Guidance]]).

- **Ball-in-court.** From the moment the `rfg` is written, the receiving holon holds the ball: the Engine places the question in what is owed by that holon, held by its keeper, with its by-when, and the asker sees it in what it waits on. Its by-when is the line's own `by`, else the time it was asked plus the time limit of the receiving holon's rung.
- **Closed by an answer or a `decide`.** A person's `say`, `settle` or `answer` that names the question (by `answers` or `anchored_to`) gives guidance, and the question reads *answered*. A `decide` is used when the question was truly the receiver's to decide, and the question reads *decided*. Either closes it; the asker's own decision that follows links to both. A line from an agent, or drawn from untrusted text, closes nothing.
- **An overdue question.** Past its by-when, the question shows as overdue on both sides, and the asker's Deal offers three ways: decide here with what is known, the unanswered question linked as the record of having asked; ask again, with a new by-when; or climb one further level, with a new `rfg` whose `about` names the first, and the first reads *climbed*. An overdue question never climbs by itself unless the asking holon's ladder says so; where it does, the agent writes the climb within its delegation, and the asker sees it said. A change of whose turn it is reaches the people concerned; nothing nags.

### 5.4 Escalation by blast radius

A decision whose blast radius exceeds the holon's remit climbs as an `escalate`: `about` (the decision's card or line) · `to` (the holon at the next rung) · `blast_radius` (in words) · `rung` · `by` (the time limit).

**Blast radius** is how many it affects and how reversible it is. It is read in three questions: Whom does it touch: only us, other holons, or people outside the Game? Can it be undone, and at what cost? Does it spend what is held in common? A decision that touches only the holon and can be undone within the week is the holon's own. One that touches other holons, cannot be undone, or spends the commons climbs to the rung its ladder names. Who judges the radius is itself named in the ladder: a member's reading, confirmed by a witness; a rule may suggest the rung, and a person settles it.

The Engine reads the blast radius, in plain words, as a rung: *person*, *me* or *self* at the person; *pair*, *room* or *cell* at the cell; *cells*, *supercell* or *council* at the council; *body*, *all*, *commons* or *public* at the body. A radius it cannot read reads as the widest, never the narrowest.

**The rung** is the ladder's step for that radius: the lowest rung whose remit covers it, never below the holon's own. **The time limit** is the by-when on the decision at that rung: the line's own `by`, else the time it was raised plus the rung's time limit.

**The way back down.** The higher holon decides in its own record (`decide`, linked by `answers` to the escalation). The holon that raised it takes the decision up as its own with a `ratify` in its own record. Ratification is the holon's consent; until it is given, the decision is a decision of the higher holon about a matter of the lower one, and both records say so. A holon that cannot ratify says why in a thread anchored to both lines; a disagreement is carried through governance, never resolved by copying the work and walking away, and leaving is always open.

**At the time limit**, the decision comes back down undecided, and the holon's ladder says what follows: what is reversible returns to the holon to decide by its own lights, with the escalation linked; what is irreversible is held until decided. Nothing irreversible is done because a clock ran out.

### 5.5 The Council: where a cell's remit ends

The rung above a cell is the **Council** of its supercell, rung 2 of the default ladder, the third: the holon formed by the supercell's member cells, each sending one of its members by its own process, the seat rotating. The Council decides what no one cell can hold alone, and only that. The canon's [[Wisdom Council]] (three to thirteen advisors, reaffirmed every ninety days) stands beside it to advise on significant decisions; it guides, protects and shepherds, and does not command. A Council's remit is written in the supercell's Field of Agreements by the consent of its cells, and every cell may withdraw from it.

### 5.6 Believability-weighted approval: an option, never a default

A holon may adopt believability-weighted approval for a class of decisions: each voice weighted by what the record shows of that person's judgment in that domain (commitments kept and witnessed, Sightings confirmed, guidance that proved sound). It is an option written into a holon's ladder by the holon's own consent, never a default and never imposed by a supercell. Where adopted, the weights are read positive only, visible to the person weighted, recomputed from the record at each decision, and never published as a ranking. The default way of deciding remains discernment and consent around proposals.

## 6. What crosses houses

A *house* is a sovereign whole with its own people, agents and tools (see [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]]). Navigation crosses houses on the same path as everything else.

- **Sightings elevated across membranes.** Two houses share no database. A Sighting crosses into another house only by being elevated into a holon both houses hold: a cell of their own, each house keeping a full copy of its record. The `elevate` line is the crossing; the [[Selectively Permeable Membrane|membrane]] holds everywhere else.
- **The shared map between two houses** is the fold of what each has elevated into the holon they share. Each house draws it with its own tools; holding the same lines, both draw the same marks. A kind one house uses and the other has not declared is shown as written, kept, and folded into nothing until declared.
- **Who witnesses across.** An elevation into a shared holon carries a witness from the elevating house. A Sighting confirmed by a navigator of the other house is marked *seen by both houses*, the strongest confirmation the map knows, because the sources are independent by construction. Whether a cross-house elevation also needs a witness from the receiving house is open, with the wider question of witnessing across houses.
- **Escalations and requests for guidance across houses** go to a shared holon, never into another house's own record. A house is never a rung on another house's ladder unless both have written it so.

## 7. The engine

The Engine stays a set of pure functions over lines, the same by pencil (see [[03 — The Game Engine (Architecture, 2026-10-24)|The Game Engine]]). The fold carries `sightings`, `questions` and `ladders` in STATE v1, and the Turn gathers the Sightings. Triage is `engine/sightings.py`; the ladder and the questions that climb are `engine/ladder.py`. The map is not yet built.

- **`triage(items, holon, lines) → [sighting, …]`.** Each of the holon's Sightings in exactly one state, new · held · elevated · folded, computed from the lines that act on it (§3.2), each with its kind, text, place, who saw it and when; a held one carries its thread and note, an elevated one who lifted it, to where, why and its witness, a folded one the Sighting it folds into. **`by_holon(triaged, holons)`** groups them per holon with its as of: that is STATE's `sightings`.
- **`elevate_line(sighting, to, why, witness, actor, now)`** drafts the `elevate` line, unsigned, for a person to sign; **`hold_line(sighting, note, actor, now)`** drafts the `thread` note, anchored to the Sighting, that holds it.
- **`load_ladder(holon_dir) → [rung, …]`** reads the holon's ladder (§5.2), else the default. **`rung(decision, holon_remit, blast_radius, ladder) → rung`**: from a decision's blast radius in words and the holon's ladder as agreed, the lowest rung able to decide it, never below the holon's own, with its name, remit and time limit, whether it climbs, and the rung it climbs from. It suggests; a person settles. Given the same ladder and the same words, every holon computes the same rung.
- **`questions(lines, holons, now, ladders) → [question, …]`.** Every `rfg` and every `escalate` folded as a question that climbs: from which holon, to which, about what, its blast radius and rung, its holder (the keeper of the holon it climbed to), its by-when, its asker, and its state, *open* · *answered* · *decided* · *climbed*, with the line that closed it or the one that carried it further, and whether it is past its by-when. That is STATE's `questions`.
- **The overdue questions in what is owed.** `owed` carries one kind, `question`, covering both an `rfg` and an `escalate` past its by-when and not yet answered or decided: it is owed by the holon it climbed to, held by that holon's keeper. Its by-when is the line's own, else the rung's time limit; an overdue one reaches the Deal of the person who holds it. The asker's side shows what it waits on.
- **The map.** `map(items, altitude) → marks`: the fold of elevated Sightings into the holons at that altitude, folded by witness, placed by `where`, faded by kind, each with its as of.

**The paper floor.** Navigation runs with no machine at all.

- **A sightings sheet**, one Sighting per line: time · who · kind · what · where · travel · state (new · held · elevated · folded, and accepted) · witness · to. A cell works it at the Turn with a pencil; an elevation is a line copied onto the supercell's sheet, initialled by the witness.
- **A ladder drawn on one page**: the rungs as rows, and for each its holon, its remit, how it decides and its time limit; above them, the three blast-radius questions as a short path to follow down the page. A question asked of another holon is a line on the sheet with its by-when and whose turn it is; the overdue are circled at the Turn.

A witnessed paper sheet beats the typed copy.

## 8. The HUD

The HUD shows; it never computes (see [[06 — The HUD (Architecture, 2026-10-24)|The HUD]]).

- **Sightings as marks on the field, in the Map.** The Map carries what was seen as its navigation layer, read from the fold's `sightings`, with a filter to show or hide it. Each mark in the Map of cells and quests and in the world views carries its kind by shape and word, never by colour alone, and its state in a word: *new*, *held*, or *raised* for an elevated one. An elevated mark sits on the membrane; a folded one is counted in the one it folds into and not drawn, and the mark it folds into shows the count of witnesses. Freshness is a fade with its words ("seen this morning"). Pressing a mark opens its face: what, where, as of, from which holon, and why it was lifted. The list twin carries the same marks as rows for every reader. No mark ever shows a member's location or a name the navigator's travel word withholds.
- **The Deal card that asks "elevate?".** When a Sighting in the wearer's cell is new and its kind or its witnesses suggest it matters beyond the cell, the Deal may carry one card: *A sighting from this week: the lower trail is blocked. Lift it to the supercell?* Options: **Lift it** (with the why drafted and a witness to ask) · **Keep it in the cell** · **Hold it**, one marked *suggested* with its reason in a line. The lift is the wearer's own act, signed by their key on the act path, through the publish sheet that says plainly who will see it. The same card shape serves a question that came due, *Your question to the supercell is two days overdue*, and a decision returned for ratification. The cards the Deal deals are in Open.
- **The Council's view.** For a holon at a Council's rung: the escalations and requests for guidance addressed to it, ordered by time limit, each with its blast radius in words and the holon that raised it; what it decided, and which holons have ratified; and the map of what its member cells elevated this season. It shows faces only: never a member cell's inner record.

## Open

1. **The kinds' names.** Eight kinds (defect · hazard · blocked · wonder · offer · request · question · witness), with the pain button apart, and a gift sighted as a defect. The kind *witness* shares its word with the `witness` event type, and the kinds *offer* and *request* share theirs with the holon's own `offer` and `request` types; each pair needs either distinct words or a sentence that holds them apart.
2. **The rung count.** The kit ships a default ladder of four rungs, person · cell · council · body; each holon may differ. Whether the person-and-agent pair is the first rung in its own right, or the person rung covers it, is open.
3. **Time limits.** The defaults are the default ladder's (1 · 7 · 14 · 30 days); a request for guidance takes the time limit of the rung of the holon it is sent to. Open: what happens at the limit, beyond reversible returns and irreversible holds.
4. **Believability's formula.** What it reads (kept and witnessed commitments, confirmed Sightings, guidance proved sound), over what window, in which domains, and how independence of sources is decided.
5. **What the first week elevates.** Recommended: nothing by default; cells practise sighting and triage at their Turn, and the first lifts are defects in the kit itself, handed to the holon that builds it.
6. **Who judges blast radius.** Rule, person, or both; the design here is a member's reading with a witness, a rule only suggesting.
7. **The folding line and the accept line.** Which line a member writes to fold a duplicate found at triage, since the fold reads the link on the later Sighting itself; whether "I see it too" also folds by `links.witnesses`, which SCHEMA declares and the fold does not read as a fold; and which line records *accept*.
8. **The travel word.** The `travel` field on `sight` is declared with the four audiences (`holon` · `members` · `commons` · `public`), which say how far a Sighting may go but not whether the navigator's name goes with it. Open: how the three travel words (*stay here* · *may travel without my name* · *may travel with my name*) map onto the four, and whether the travel word is also a setting of the person.
9. **The Council's composition.** One seat per cell, rotating; how it relates to the canon's Wisdom Council and to a supercell's keeper is open.
10. **The ladder as agreement.** A holon's ladder is read from `ladder.json` (or `calendar.json`); whether it is also carried as agreed lines in the record, so that its adoption is witnessed and folded like any other agreement, is open, with the wider question of where a holon's Field of Agreements lives.
11. **Witnessing across houses**, for elevations into a shared holon, as in [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]].
12. **The face's words for the climb.** The face says *raised* for an elevated Sighting ("Raised to a wider house"); *lift* is the word the design uses, and *raise* is kept for an escalation. The face says "Take it to the wider circle" for an escalation carried to another house, and "moved it up a rung" for an escalation on a card. The Deal says "Pass this on to the circle?", with *Pass it on* · *Keep it here* · *Not yet*, for a new Sighting, and *Pass it to the wider circle* for a question that climbs further. One set of words is to be chosen, and *a wider house* is to be held apart from a supercell within one house.
13. **The Deal's cards for navigation.** What is built: every new Sighting is dealt to the keeper of the holon it was seen in, as "Pass this on to the circle? Someone saw this: …" (for a hazard, "Someone saw a danger: …"), with *Pass it on* · *Keep it here* · *Not yet*; *Pass it on* is marked suggested for a hazard, *Keep it here* otherwise. A question that climbed is dealt to its holder as "A question for you:" (a request for guidance, with *Answer it* · *Decide it here* · *Pass it to the wider circle*) or "A decision for you:" (an escalation, with *Decide it here* · *Ask for more first* · *Pass it to the wider circle*); once past its by-when it is dealt from what is owed, in the same words. The asker's side has no overdue card, and the card for a decision returned for ratification is the Deal's ordinary ratify card. Not yet settled: whether the design's card (only the Sightings whose kind or witnesses suggest they matter beyond the cell, *Lift it* · *Keep it in the cell* · *Hold it*, to the wearer) replaces the built one, and whether the asker's Deal carries the three ways for an overdue question.
14. **Who processes between Turns.** What is built: a new Sighting reaches the keeper of its holon at their next look, and the lift is a person's act. Open: whether any member may process it, and whether a hazard, a blocked road or a pain sighting reaches every member its Deal touches without waiting.

## Not yet built

- The one-tap row of eight on every view, the travel word set at the tap, and the agent drafting a Sighting from one sentence.
- The *accepted* state of triage, and the *received* list of what a holon took in by elevation from below.
- The look-again date on a held Sighting.
- The pain button, and its place in what is owed.
- The fold's checks on an elevation beyond its being a person's own act: a why and a witness on every lift (the registry requires only *what* and *to*), a witness other than the one who lifts, one level only, never past the travel limit.
- The count of independent witnesses on a folded Sighting, and the mark *seen by both houses*.
- A ladder's *how it decides* and *what happens at the limit*, and the climb of an overdue question by the ladder's word.
- Guidance that carries its confidence and its reasoning as fields of their own.
- The map at every altitude, with freshness fading by kind.
- Believability read from the record, and believability-weighted approval.
- The world views, and the Council's view.

*Siblings: [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)|The System]] · [[01 — The Record (Architecture, 2026-10-24)|The Record]] · [[02 — The Membrane (Architecture, 2026-10-24)|The Membrane]] · [[03 — The Game Engine (Architecture, 2026-10-24)|The Game Engine]] · [[04 — The Player+ Agent (Architecture, 2026-10-24)|The Player+ Agent]] · [[06 — The HUD (Architecture, 2026-10-24)|The HUD]] · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]] · [[08 — Security and Sovereignty (Architecture, 2026-10-24)|Security and Sovereignty]] · [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)|Decisions and Their Reasons]] · [[Index — The Architecture (2026-10-24)|The Architecture]].*
