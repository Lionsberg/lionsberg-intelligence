# 15 — The Box — Bounding an Agent's Work on the Chain

*How long one agent's task may run before it must hand back, argued from first principles. Part of the architecture set; see the [Index](<Index — The Architecture (2026-10-24).md>). It follows [14 — The Chain Before the Single Worker](<14 — The Chain Before the Single Worker (Lesson and Structure, 2026-10-25).md>) and stands on [03 — The Game Engine](<03 — The Game Engine (Architecture, 2026-10-24).md>), §2.7, §2.8 and §3.4. The engine rule in §4 is proposed, not yet built or settled.*

## The question

A [[Lean Project Delivery|lean]] principle of long projects holds that no task on a ten-year [[Critical Path]] may run longer than five days. What is the like bound for an agent? An hour seems a very long box for an agent: an hour of an agent's work is closer to two months of a crew's than to an hour of it. Should a fleet ever wait an hour on one agent? And what is the wiser way to think about the bound, since it will matter most when hundreds of millions of people and their agents play on one record?

The answer comes in five parts, each tied to what the kit already holds.

## 1. The unit is the handback

A crew's day was never the thing being bounded. It was a proxy for the moment a foreman could walk the site and see what was true: the wall is up or it is not. Time stood in for sight because sight was expensive and came once a day.

An agent's natural moment of sight is its **handback**: an artifact with a check. A test passed; an agreed shape filled (the contract of page 14, a list of names, one per line); a draft that a reader can score. A task is therefore bounded first by *what it hands back and how that is checked*. The clock is the fallback for when no one can see: when the work has no check, minutes are the only measure left, and a short box is the only safe one.

## 2. What is bounded is variance

Critical Chain practice asks for honest estimates, no padding inside tasks, and one [[Buffer]] at the end sized to the chain's aggregate variance (the Engine's halving rule, 03 §3.4). Read that way, "no task over five days" meant *no task whose variance can blind the manager before the buffer absorbs it*. Five days was the longest a task could run alone and still be wrong in a way the buffer could carry.

An agent's variance grows with each autonomous step, at a rate set by four variables:

- **Novelty of the work.** A routine build drifts slowly; a first design drifts with every choice.
- **Checkability.** Work that a machine can check (a test, a schema, a count) reveals its drift as it goes; work judged by taste reveals it only when a person looks.
- **Reversibility of its acts.** A draft in its own folder can be thrown away; a send cannot be unsent.
- **The agent's capability.** A stronger model drifts less per step on the same work.

So the box follows the variables. A routine build with tests may run long, because every test is a handback. A novel design judged by taste hands back every few minutes, because only a person can see it. Anything outward or irreversible has a box of zero: it is asked every time, as rule 10 of the [chief of staff's skill](../skills/the-chief-of-staff/SKILL.md) already holds (a worker never acts outward).

## 3. Observation replaces check-ins

A handback is a check-in at the end of a box. When every act is visible and machine-readable as it happens, the watcher need not wait for the end. The Talk's trust layer ([`hud/DESIGN-TALK.md`](../hud/DESIGN-TALK.md)) shows each act as a row, and each worker as a row with its minutes and what it has written. A structure that reads those rows can intervene on drift: a worker reading files far from its task, a test failing three times, a write outside its folder.

The box then becomes the *time to notice*, which can be seconds. This is the [[Andon (the clocked pull)]] pulled by the structure itself: the window is matched to the work's own rhythm, the pull rises one level on silence, and a person is called only for a decision that is theirs.

## 4. The Game already computes the box

The box is the [[Float]], and the watch is the buffer. A worker's task is a [[Work Card]] with predecessors and successors; the Engine already computes its total float (03 §2.7). A card on the chain with no float gets the tightest box, because any slip moves the finish. A card with float may run longer, because its slip is absorbed before it moves anyone. Buffer consumption against chain complete is the watch the Engine already draws, the chain's fever chart: green, yellow, red. It is fractal across holons: each cell watches its own chain, each [[Supercell]] aggregates the feeding buffers of its cells, and attention is spent only where a buffer goes red.

**Proposed, not yet built or settled.** The Engine would set each worker card's box from two inputs:

- *Float.* Zero or negative float: the floor box. Float within the near-critical band: twice the floor. Float beyond it: the box may grow toward a share of the float itself (a third is the first guess), never past the next handback.
- *Checkability.* A card whose handback is machine-checked (a test, a schema) takes the box above. A card judged by taste takes the floor whatever its float, because no float protects work that no one can see. An outward act takes zero.

A worker's row in the Agents place and in the Talk would then show three things beside its name and task: **its box** (minutes, and the minutes run), **its float** (in words: *on the chain*, *near it*, *a day to spare*), and **the buffer it feeds** (green, yellow or red). The overrun watch of page 14 would fire on the computed box, not a guessed one.

Until the Engine computes the box, the chief of staff's rule 25, about five minutes, is **the floor**: the smallest unit that yields a usable result, used for every card on the chain while float and checkability are not yet read.

## 5. Human attention is the binding constraint

At the scale of hundreds of millions, agents are many and cheap; the attention of [[Actor|Living Intelligence]] is the drum, the scarcest resource on every chain (03 §3.4). The measure is therefore *attention spent per unit of [[Value]]*. The structure's work is to convert an agent's hours into few, well-timed decisions, each arriving when the person can act on it.

Everything an agent has produced and no one has checked is **inventory**: unverified work in flight. Little's Law states that [[Throughput]] equals work in flight divided by cycle time. A fleet with long cycles and much work in flight is not fast; it is holding risk, because every unchecked hour can be wrong and every wrong hour has others built on it. Short boxes with checked handbacks keep inventory low and throughput honest. [[Spending Attention]] wisely means a person sees a decision, never a pile.

## Current best understanding

1. An agent's task is bounded by what it hands back and how that handback is checked; the clock bounds only what cannot be seen.
2. The bound is on variance, which grows with each step alone at a rate set by novelty, checkability, reversibility and the agent's capability.
3. When every act is visible as it happens, the box shrinks to the time to notice drift, and the structure pulls the cord before a person must.
4. The Engine already holds the box and the watch: float sets how long a card may run, and buffer consumption says where attention belongs.
5. Human attention is the drum, and unchecked agent work is inventory; the wise box is the one that turns the most work into the fewest well-timed decisions.

## Current best practice

- Name every task's handback and its check before its minutes.
- On the chain, about five minutes is the default box, the house's to set and the evidence's to revise, until the Engine computes one; taste-judged work keeps the floor whatever its float.
- The check sets the floor of the box. An action whose only check is a five-minute suite cannot be a five-minute action: give it one targeted check, or make the suite fast. (Seen in practice: most overruns are spent waiting on a slow proof suite.)
- The box binds the one who assigns as much as the one who works. An addition to a running worker is a new action with its own box, never a message that grows the old one. (Seen in practice: a box grown by additions runs far past its limit and returns much of its work undone.)
- Anything outward or irreversible has a box of zero: asked every time.
- Watch the rows, not the clock: intervene on drift the moment it shows.
- Spend a person's attention only where a buffer goes red or a decision is theirs.

## Open

1. Whether a third of float is the right ceiling for a checked card's box, or the box should be sized by the chain's own variance (03, Open 5).
2. How checkability is declared: by the proposer, by the kind of handback, or learned from each worker's record of drift.
3. What counts as drift in the act rows, and who sets the threshold for each holon.
4. At the scale of a supercell, whose attention is the drum, and whether it is published each season (03, Open 6).
5. Whether a long, unchecked study that nothing waits on counts as inventory at all, or as exploration, which is not waste.

## Not yet built

- The Engine does not carry worker tasks as cards, so it computes no float for them; the host's box is still a stated number (page 14).
- It does not read a card's checkability; the record contract has no field for it.
- It does not draw a buffer for a build of workers; the fever chart exists for cards and milestones only.
- It does not watch the act rows for drift; the overrun watch reads minutes alone.
