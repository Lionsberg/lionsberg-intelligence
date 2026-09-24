---
status: current best understanding, loosely held · improved each week
tier: 1000
domain: The Operating System and Integrated Delivery
pillar: —
---
# Work Card

*One piece of work, carrying its own address, its dependencies, its float, its state and its history — state on the work, not on the worker.*

A Work Card is a card for a thing to be done. Its face says which body it belongs to, what it is, what must happen before it and what waits on it, how much slack it has, and where it stands. Its record holds every event that has touched it. Anyone who picks it up can tell what it is and what it needs without asking a person.

The reversal at its heart is worth naming. The obvious design puts the state on the worker — a list of what each person is doing. Mature systems put the state on the work, because work outlives whoever last touched it and must stay readable when they are unreachable. Three objects then sit on three clocks and are never conflated: the Work Card, fast and per-item, closed when the work closes; the [[Actor Charter]], slow and per-person, changed rarely; and a check-in, faster still, a line of readiness that expires to *unknown* rather than to *ready* ([[Condition]], [[Position]]).

It is load-bearing because it is what makes the Game calculable without anyone being surveilled. Cards with dependencies and durations can be computed into a [[Critical Path]] and a [[Float]] for every item; a person's own view is a sort of the cards rather than a report on them; and the same object a Cell plays is what a larger body reads by address, never by copy ([[Work Deck]], [[The Game Engine]]).

The card carries its own provenance as it moves, the way a label lets a parcel pass through many hands with nobody holding the whole route. That is also its guard: the card is its own audit trail, and the shared record only ever repeats what the card already said ([[The Record]], [[Provenance]]).

**Also called:** a card of work
**Stands on:** [[Card Types]] · [[The Record]] · [[An address]] · [[Float]]
**Opens onto:** [[Work Deck]] · [[The Board]] · [[Decline]] · [[Release]] · [[The Game Engine]] · [[Data Date]] · [[Critical Path]] · [[Feature · Deliverable · Task]] · [[Actor Charter]]
**In play:** the table — a row on the Board; at scale, only the depth changes
**Sources:** `Projects/the term pages/Work Card.md` · `Card Types.md` · `Projects/the term pages/Work Deck.md`, `Data Date.md`, `The Game Engine.md` (drafts) · lionsberg.wiki: Card Types
**Open:** Its state vocabulary — *open · taken · committed · done · declined · released* — is one of three live commitment vocabularies in the canon, and they cannot all be what the Record means ([[The states of a commitment]]). · The page asserts that the Playcard is received and never filled in, which stands against the seed's filled-and-stacked Playcard ([[The Playcard stack]]). · Its tiers — mechanical, meaning, sovereign — were named to decide how a claiming act resolves, and those acts were later struck as needless complication; what the tiers now decide is unstated.
