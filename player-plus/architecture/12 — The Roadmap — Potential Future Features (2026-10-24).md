---
title: The Roadmap — potential future features
description: Candidate features for the Player+ Kit, kept so they are neither lost nor built before a holon commits to them.
---

# The Roadmap — potential future features

*Candidates, kept here so they are neither lost nor built. A row moves to a plan only when a holon commits to it with a by-when. Nothing on this page is a commitment, and nothing here is settled until it is built.*

## Candidates

| Candidate | What it would give | What it rests on |
|---|---|---|
| The agent's first words in the Story's voice, placed on the Path | A new player hears where they stand and the next stretch, in lines selected from the canon, never composed | the canon's lines; the Path's gates in the record |
| The night ground as tonight's sky | The real moon and the next turning on the ICE's night | the Gameclock's turnings and moons, already computed |
| The flame as a visible line | When a player passes the flame, the new field appears beside theirs, joined by one engraved line | the Map; a `flame` line in the record |
| "The whole is waiting on this" | A card on the system's critical path shows the chain across holons | the Chain; cross-holon externals |
| Ink drying as the only celebration | A witnessed commitment goes from paper to full ink; the field turns a quarter at the Turn | the three inks; the Turn |
| A Room across languages | Two houses each seeing settled lines in their own language, translated through the Proxy | the Proxy; a translation route |
| Voice from the phone | A Sighting spoken into the phone lands on the Map; The Deal read back aloud in the player's language | local transcription; the phone door |
| The world's Sightings tonight | The Map's widest view: what every holon elevated today | elevation; the shared map of reality |
| The paper card that works | A printed Deal answered in pencil, read back by an agent from a photo | the paper mirror; the invitation card |
| The live arc on a stage | A commitment made, kept and witnessed across two houses in ten minutes, the export verified on screen; a candidate first demonstration | the whole |
| Conversation first, everywhere | The first screen is the conversation with your own agent; the views of the cards are one tap away behind More and never required. The frame's top level is Agents · Talk · More | the dock; the Talk place |
| The phone as a first-class surface | Most people meet their agent on a phone. The ICE on the player's own machine, reached from the phone over the private network, is the door that keeps the proxy, so the phone experience has to be world class, never a shrunken desk | the phone door; the Proxy |
| Other harnesses | The agent host speaks the Agent Client Protocol, so a row in the agents file may start any harness that speaks it. The command-line harness runs through its adapter today; OpenCode, Codex and Gemini are candidates to prove, one row each, with the same dock and the same record | the agent host; the agents file |
| A directory | A way for a group of holons to find who is in it and how to reach them (a house, an address, a key). Today the record's `join` and `affirm` lines with `reach` carry this per holon; a directory across holons, with the postures respected, is a feature to design, not a server to install | `join`, `affirm`, `reach`; the postures |
| Discernment in conversation, not dashboards | The few things to discern now, said in conversation, in place of a wall of figures. The Deal and the Talk place carry this; the Ledger and the Chain stay one tap away | the Deal; the Talk place |

## The measure of every surface change

Every surface change is measured by the surface studying itself (`hud/DESIGN-THE-BAR.md` §4): time to first act, errors and reversals, attention switches between views, the person's one breath after a scene, and workload in the person's own words, kept beside the record's measures.

The Turn reads these measures and proposes one change to one view, with its why; a change to a view is itself a line with its why. A view that cannot say what it measured about itself, and where that measure lives, is not finished. Before any view is called finished, it is handed to a tired person on a phone at night, and their one breath is written down.

**Not yet built: the `study` line.** A `study` line would carry the view and scene, the device and the hour, the condition in the person's words, the measure and its value, and as of which event. It would be written to the person's own record on their own machine and never leave the holon. The `study` type is not yet in the registry.

The views are measured against the bar in `hud/DESIGN-THE-BAR.md` §5.

**Not yet built: the Board folds into the Chain.** The frame has no Board tab; the Chain is to be the one view of what the whole is waiting on, with one fever chart of buffer consumed against chain completed and one path, and calibration moves to the Turn. Until the Chain absorbs them, the cell steward's cards by stream are drawn with the Board's code.

**Not yet built: the surface rebuild to the bar.** Its design intent, view by view:

- **The Deal:** a lift.
- **Threads and Mail:** one column ordered by turn, the agent's draft in place.
- **The Map:** the picture carries the computed facts; the chips and the repeating list removed; one fixed screen.
- **The Chain:** one fever chart and one path, absorbing the Board; calibration to the Turn.
- **Bodies:** the ceiling as a trend, the console words gone.
- **The Room:** rebuilt on the phone, lifted at the desk.

## The way in with the desktop app only

A player may have only the vendor's desktop app, with no terminal harness.

- **The ICE needs no terminal harness.** The agent host starts the player's agent through the protocol adapter, and the adapter bundles its own harness for macOS and Windows (x64 and arm64). It needs only Node and the adapter's package, plus the player's sign-in. The day-one path: open the house folder in the desktop app, say the first line, and the agent starts the ICE on this computer; from then on the browser is the way in, Talk first.
- **Several sessions are the Agents place**, and it is built: the prime and the workers, each with its task, on a rail.
- **Not yet built: a one-line check early in the way in** for whether a terminal harness is present; if not, the agent says "desktop app only" is the way and never offers the launch word that opens a terminal.
- **Not yet built: the adapter's install as a step the agent runs on the player's yes** (`npm install` of the adapter in the house), with the cost said. Later, the desktop app's own bundled harness used directly, so Node is not needed either.

## Measuring the Game as it unfolds

*Potential features.*

Useful throughput is rate times yield, and a faster agent without the Game is a faster way to do the wrong thing. To check that as the Game is played, rather than claim it:

- **A hypothesis as a line in the record.** A holon states what it expects (a rate, a yield, a thing unblocked) with the measure, the date and what would falsify it. The Turn reads the open hypotheses each week against the record and marks each held, struck or still open. Nothing is claimed that the record cannot read back.
- **Four measures the record already holds, computed per holon per week beside the Score:** rate (acts per person-hour, from every act's time and actor); yield (commitments kept as said against commitments made, the last planner's percent-plan-complete, with supersedes, undos and returns counted as rework); waiting (float consumed, buffer colour); cost (the harness's figures per sitting). Their product is Throughput of the Goal, shown where the Score is shown and said in one sentence on the Talk when asked.
- **The qualitative, by its own instruments.** A sighting carries a person's seeing of a change, with its magnitude in words and a witness's second judgment; a discernment carries the person's own rating of an answer or a route; the study line carries the one sentence of the day. These land in the record beside the figures, and the Story carries them where figures cannot.
- **The signature of an unlock.** "Blocked for a year, unlocked in an afternoon" has a quantitative shadow: a card whose float was deeply negative moves to positive, and every card downstream regains float. The dealer's leverage already measures this (urgent work moved per minute of the person's own). The engine can mark a step change in a milestone's late finish as an unlock, and the sighting that names it is linked to the cards that moved.
- **Natural experiments.** Holons adopt the Game's parts at different times; the record's as-of gives a before and after per holon, so the parts' effects can be read without a trial anyone had to design.

## An experiment the first twenty can run

*A design, not yet settled.*

Whether a person with an agent in the Game does more of the right work than alone is an empirical claim. With ten or twenty people it can be tested validly, without a trial anyone would recognise as a laboratory:

- **The record is the pre-registration.** Before any data, each holon writes its hypotheses, measures and analysis as signed, dated lines. They cannot be changed after the fact without the change being a line too. That is a stronger pre-registration than most journals ask for.
- **The design is staggered onset, within person.** Each player runs a baseline sitting with their agent and no Game for a period; then the Game's parts are turned on at a time drawn by lot for each player. The effect is the change at onset, replicated across players at different times. This is the multiple-baseline design, an accepted quasi-experiment when between-person trials are underpowered; with twenty people it has real inferential weight, and reversals (a part turned off for a week) add more where a player consents.
- **Outcomes are machine-recorded and named in advance.** Primary: yield (commitments kept as said against made; rework as supersedes, undos and returns) and cycle time (a card made to a card done). Secondary: rate (acts per person-hour), waiting (float consumed), cost. The agent's own version and the kit's release are lines too, so the agent getting better is separated from the Game's effect in the analysis.
- **The subjective is measured with instruments, not impressions.** A weekly one-item measure of whether the week moved the person toward what matters, a short workload scale, and the sightings with a witness, coded afterwards by two readers who did not play, with their agreement reported.
- **The analysis is said in advance.** A mixed model with the person as a random effect and the onset as the intervention, effect sizes with intervals; with small numbers, a Bayesian posterior for the multiplier is the honest form. The threats are named: novelty, the enthusiasm of the first twenty, the agent improving weekly, no blinding. Each is met by the design or declared.
- **Open data, open code, open kit.** The record is plain text and signed; the analysis is a script; the kit is public. Another group can replicate with its own twenty, which is what makes it science rather than a story.

What this cannot do: prove a hundredfold. It can measure the multiplier, with its interval, and say whether the model held.
