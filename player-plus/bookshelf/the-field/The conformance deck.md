---
status: current best understanding, loosely held · improved each week
tier: 1000
domain: The Operating System and Integrated Delivery
pillar: —
---
# The conformance deck

*A small set of cards with known answers that any implementation of the engine must reproduce — how a rule stays one rule.*

Write a rule in words and two honest people will implement it two ways. The conformance deck closes that gap without anybody having to police it: a handful of worked examples — these cards, these dependencies, this date, and here is exactly what the answer must be. Anything that reproduces them is the engine. Anything that does not, is not, and says so itself before anyone is misled.

It is load-bearing because a body that intends to run without a centre still has to agree on arithmetic. The usual solutions are an official implementation everyone must use, which creates a dependency and a gatekeeper, or a standards body, which creates a committee. A test deck creates neither. It is a page of examples anybody can hold, in any language, on any machine or on paper, and it makes conformance a fact rather than a permission ([[Technology Sovereignty]], [[Interoperability]], [[The open web]]).

It also makes improvement safe. When the rule changes, the deck changes with it and the new expected answers are published together; every implementation then discovers at once, and specifically, what it must now do differently. A change to a shared rule that arrives without its examples is a change nobody can implement confidently ([[Proposal]], [[The edition]]).

Its discipline is that the deck is small and adversarial. A hundred easy cases prove nothing; a dozen cases chosen at the edges — the zero-length item, the two paths of equal length, the promise returned twice — prove almost everything. The deck is where a body writes down the cases that once caught it out ([[Every Defect Is A Gift]], [[The guard]]).

**Also called:** the test deck
**Stands on:** [[The Game Engine]] · [[Work Deck]] · [[Interoperability]]
**Opens onto:** [[Minimum standards of interoperability]] · [[The guard]] · [[Every Defect Is A Gift]] · [[Screens and paper]] · [[Technology Sovereignty]] · [[The edition]]
**In play:** Home · beyond — run by whoever builds an engine, before anyone relies on it
**Sources:** `Projects/the term pages/The Game Engine.md` · lionsberg.wiki: Float
**Open:** Named once, never written; no cards, no answers, and no statement of who publishes the deck or how a correction to it travels.
