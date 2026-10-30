---
title: The Bar
description: The design standard for every view of the ICE (The Deal · Threads and Mail · the Map · the Room · the Chain · Bodies · the dock), and the sheet a reviewer scores each view against.
license: CC BY-SA 4.0
---

# The Bar

*What the best working surfaces look and feel like, drawn from the fields that study interfaces for pilots, surgeons and control rooms; how each lesson lands in each view of the ICE; where the mythos lives; how the surface studies itself; and the sheet a reviewer scores. A film is held to a storytelling bar, and the brand's Award Bar stays the bar for stories and scenes. A surface a person works through every day for years is a different thing, and the knowledge of how to make one well is older than the web. For the working surface this page replaces the ten-principle bar of [DESIGN.md](DESIGN.md) §9. It builds on DESIGN.md, the record's schema in [engine/SCHEMA.md](../engine/SCHEMA.md), and the LIØNSBERG brand library.*

---

## 1. What the best look and feel like

In plain words, for a builder and a grandmother alike:

The best working surface is quiet. When all is well it shows almost nothing, and the person trusts the quiet because it has never lied. When something needs them, that one thing is the brightest thing on the screen, and it says what it is, what it blocks, and what to do. Everything is where it was last time. Nothing moves unless the movement means something. Nothing is there to be admired. The surface has already done the arithmetic: it shows what the facts mean and what comes next, never a pile of facts to work out. A grandmother would say: it tells me what needs me, shows me the rest when I ask, and never makes me hunt.

That is not taste. It is what these bodies of work found, over decades, where a bad interface costs lives. Each is named by author and work so a reader can check it.

**Situation awareness.** Mica Endsley, "Toward a Theory of Situation Awareness in Dynamic Systems" (*Human Factors*, 1995), and, with Debra Jones, *Designing for Situation Awareness* (second edition, 2012). The early studies were of fighter pilots; the method was carried into surgery, air traffic control and power plants. Three levels: **perception** of what is there, **comprehension** of what it means, **projection** of what comes next. The design rules, in summary (our reading of the work, not a quotation): design around the person's goals, never around the data; present level-2 and level-3 information directly, computed, instead of leaving the person to compute it from level-1 pieces; keep global situation awareness in view while the person works on a detail; make salience proportional to criticality; keep the person in the loop, since automation that hides its state produces a person who cannot take over; avoid attention narrowing and clutter; show how fresh and how trusted each piece of information is.

**Cognitive engineering.** The field that designs cockpits, astronaut training and the selection of aircrew holds that the interface and the training of the person are **one system**, designed around the operator's cognition under stress and fatigue, never around the screen alone. Workload, attention and situation awareness are **measured**, never assumed, with the people who will use the display, in the conditions they will use it. Our cockpit is a tired person on a phone at night.

**Ecological interface design.** Jens Rasmussen, "Skills, Rules, and Knowledge; Signals, Signs, and Symbols" (1983); Kim Vicente and Jens Rasmussen, "Ecological Interface Design: Theoretical Foundations" (1992); Kim Vicente, *Cognitive Work Analysis* (1999). Make the constraints of the work visible, so the person sees the situation the way an expert sees terrain. Support all three kinds of behaviour: the skilled glance, where the shape of the display is read without thought; the rule, where a sign says "when this, do that"; and knowledge, where something new happens and the person must reason, served by showing the real structure of the work, not a summary of it.

**The dark and quiet flight deck.** As commonly told: the "dark cockpit" philosophy of the Airbus A320 generation and the "quiet, dark" philosophy of the Boeing 757 and 767, and Earl Wiener's NASA study of glass-cockpit crews (1989). Nothing is lit when all is normal; a lit control means something is not in its normal state, so it is always worth a look. The primary flight display shows the same things in the same places on every flight, descended from the "basic T" of the 1930s, so the eye finds them without searching. Alerting is a strict hierarchy, warning, caution, advisory, each with its own colour, place and sound, and nothing else is allowed those colours. And the display shows **trend vectors**: where the speed will be in ten seconds, not only where it is. The pilot reads the future, not the number.

**The operating room and the checklist.** Atul Gawande, *The Checklist Manifesto* (2009); the WHO Surgical Safety Checklist (2008); James Reason, *Human Error* (1990). The one thing at the right moment, at a pause point, never the whole procedure; the killer items only. Confirmation is reserved for the irreversible, so that when it appears it is still read; Donald Norman, *The Design of Everyday Things*: a confirmation asked too often is answered without reading.

**Tufte.** Edward Tufte, *The Visual Display of Quantitative Information* (1983): data-ink; erase the ink that carries no data and the ink that repeats data. *Envisioning Information* (1990): layering and separation; small multiples; the smallest effective difference. *Beautiful Evidence* (2006): sparklines. The content is the interface; nothing decorative that carries no meaning.

**Rams.** Dieter Rams, the ten principles for good design, from his years at Braun: as little design as possible, "less, but better"; unobtrusive, honest, thorough to the last detail, long-lasting.

**The craft of the best consumer tools.** Robert Miller, "Response Time in Man-Computer Conversational Transactions" (1968), carried into Jakob Nielsen's *Usability Engineering* (1993): a tenth of a second feels like the hand's own motion; a second keeps the thread of thought; ten seconds loses it. Fitts's law: the bigger and nearer, the faster to reach, so the primary act is the biggest and nearest. Fixed spatial memory: what moves between visits is relearned every visit. Apple's Human Interface Guidelines: one primary act per screen; the interface defers to the content. Bret Victor, "Magic Ink" (2006): information software answers the question before the person asks; interaction is a cost. Matthew Butterick, *Practical Typography*: hierarchy by size, weight and space, never by boxes and rules. Motion carries meaning (what moved, from where, to where) or it does not move.

---

## 2. How this lands in each view

The Engine already computes the level-2 and level-3 facts for every holon the person belongs to: **what is owed**, to whom, by whom, by when, and what it blocks; **stake**, each card's float and whether it lies on the system path; **the critical chain**, and buffer consumed against chain completed; **by-whens**; **calibration**, commitments kept as claimed and as verified; and **freshness**, as of which event from each neighbour. A fact the Engine computes is shown directly, in words or in a picture, never left for the person to assemble.

**The Deal.** *Goal:* decide what needs me today and give my word. *Shown directly:* the opener says in one breath what is owed and what it blocks; each card says why it is in the deal (waiting on you · due · the whole is waiting on this · someone asked you · you said you would), the stake in words, and its by-when. *Lit when normal:* nothing; once played, the surface goes still. *Primary act:* answer the card in front of you. *Never:* a panel reading "Not computed yet" (a line not computed is not shown); a decorative image beside a number; counts in buttons where one small picture of the two sides says more.

**Threads and Mail.** *Goal:* know who wrote, what they ask of me, and answer. *Shown directly:* whose turn it is in each thread; which asks are owed and by when; what each thread is anchored to; a badge that counts only what needs my word. *Lit when normal:* nothing. *Primary act:* answer in the thread. *Never:* a list sorted by time instead of by turn; folders; the words event, anchor, settle, holon; a person's name where the Role should be.

**The Map.** *Goal:* see the whole I belong to, and where what needs me sits in it. *Shown directly:* each field placed and sized so nearness, stake and freshness are read at a glance; the owed thing as the one lit point, in its field; a field holding a card on the system path marked as such; the chain shown inside each field it passes through, numbered in its order across the whole, in the ink's own weight, crossing from one field to another only where the two overlap through the person who belongs to both, never as a free line between fields, since there is no center but ØNE. *Lit when normal:* no field; the engraved ground is the information. *Primary act:* go into a field. *Never:* filter chips; a list beneath the picture that repeats it (the list is the large-type twin, shown instead, never beside); a glyph the picture does not explain; a scroll, since the whole is one screen or it is not a map.

**The Room.** *Goal:* work together and settle lines. *Shown directly:* what is on the table now; whose word it waits on; what was settled this sitting; the commitments made in the room with their by-whens, in the one ink grammar. *Lit when normal:* the line being settled. *Primary act:* settle a line, or give my yes. *Never:* the transcript as the hero; presence as a row of faces; the Play by Play as a feed.

**The Chain.** *Goal:* what is the whole waiting on, and is it me. *Shown directly:* the system path from my card to the interface milestone; buffer consumed against chain completed as one picture (the fever chart of critical chain practice, after Eliyahu Goldratt's *Critical Chain*, 1997); which Role holds the pacing attention this season. *Lit when normal:* nothing; the buffer lights only in its last third. *Primary act:* open the card that is the constraint. *Never:* a chart of every card; float as a decimal; a schedule drawn as if a master kept it, since there is no center but ØNE.

**Bodies.** *Goal:* know which of my agent's bodies is awake, which holds the desk, what each is spending, and stop or hand off. *Shown directly:* the desk holder; what each body is on, in one line; usage against the ceiling as a trend, as of when; a fault that needs my hand, with what to do. *Lit when normal:* a fault only. *Primary act:* hand off, or stop. *Never:* a log; a process name; a green light for "fine".

**The dock.** The conversation with the agent is the heart of the ICE, not a pane beside the display. *Goal:* speak with my agent and feel I spoke with someone. *Shown directly:* the first word within a breath; presence felt before it is read, the field turning as the agent thinks; the agent's words set like a letter, not a log; one voice, no tool chatter, the work it did shown as the record's margin; for any ask, its what and its why; at a long task, what it is doing and roughly how long, in words. The agent reaches the person, with a card or a word at the right moment, more often than the person reaches a prompt. *Lit when normal:* nothing; the silence is comfortable. *Primary act:* speak. *Never:* a scroll of equal bubbles; a spinner; a mode name; commands or tool names; a question the agent could have answered from the record. What a terminal cannot do, this does by restraint, timing and voice, never by drawn light or effects.

Across every view: **position is fixed** (the Deal, the ribbon, the agent's door and the back door sit where they sat last visit); **salience follows stake** (the brightest thing is the owed thing with the least float; the brand's gold is the warning colour and is spent on nothing else); **the hand is answered under a tenth of a second** (if the record takes longer, the surface says so in words).

---

## 3. Where the mythos lives

The surface has room for theatrics and mythos, in a beautiful, fun way. The dark cockpit and the canon's picture agree on where that room is.

The still images in the brand's hand (the toroidal field, the still point, the loader's mark) are **the ground and the first scene**: engraved, unlit, beneath everything. They never compete with the primary display, and no view's information is carried by them. The fields on the Map are made from these frames, with code only for position and turning.

**A scene may play** when nothing is owed and something is worth marking: the first ten seconds of the first visit, the loader as the still point arriving; the Turn, when the four lines are read; a commitment kept, when a witness verifies and the ink dries; a gate passed on the Path. A scene is short, is the wearer's act or its consequence, has one idea, and ends in stillness.

**A scene may not play** while anything is owed. If a card is waiting on the person, the surface is a cockpit and the owed thing is the only thing lit. None on a daily open before the deal is played; none while a Room is settling a line; none to cover a wait. Under reduced motion every scene is its last frame. The mythos is the ground the work rests on and the celebration when the work is kept; it is never the work's clothing.

The feeling of speaking with a magical being lives here too, and the dark cockpit and the magic agree on how: the magic is in restraint, timing and voice, the first word within a breath, the field turning while the agent thinks, a letter where a log would be, and a scene only at the moments above. Drawn light and effects make a product; a presence that answers well and then keeps a comfortable silence makes a being.

---

## 4. The surface studies itself

This standard is current best understanding, and the ICE is built to be studied, so that from it we can continuously study, morph and improve. The measures the field uses are kept, not guessed: time to first act; errors and reversals; attention switches between views; what the person said in one breath after a scene; workload in the person's own words ("too much", "about right", "I had to hunt"). The `layout` and `attention` lines already exist. A **`study`** line, not yet built, carries the view and scene, the device and the hour, the condition in the person's words, the measure and its value, and as of which event. It is written to the person's own record on their own machine. It never leaves the holon and is never sent to anyone.

The Turn, at each of its three depths, reads the surface's own measures beside the record's and proposes one change to one view, with its why. A change to a view is itself a line with its why, so the surface's history is as legible as the record's. Calibration with a few of the people the surface serves, measured over weeks in the conditions they live in, replaces split testing on strangers, because the people a view fails are the people it was made for, and they can be asked. A view that cannot say what it measured about itself, and where that measure lives, is not finished.

---

## 5. The checks

A reviewer scores every view in every scene of [DESIGN.md](DESIGN.md) §9, on a phone first, then at 1440 px, night and paper, regular and large type. Each line is yes or no, with a place to point. A **no** on a line marked ■ returns the view; the rest are lifted and passed.

**Quiet**
1. ■ Is anything lit when nothing is owed?
2. Is an alert colour spent on something that is not an alert?
3. Is a scene playing while something is owed?
4. Does anything move without meaning (what moved, from where, to where)?

**Computed, not left to compute**
5. ■ Can the person say, in one breath, what is owed and what it blocks?
6. ■ Is any level-2 or level-3 fact the Engine computes (owed, stake, by-when, chain, calibration, freshness) left for the person to assemble?
7. Does every figure say as of when, and from which holon?
8. Is a number shown where a trend or a word reads faster?
9. Is a placeholder shown where a fact is not yet computed?

**Salience and position**
10. ■ Does salience follow computed stake: is the brightest thing the owed thing with the least float?
11. ■ Is spatial position fixed across visits and devices?
12. Is the primary act the biggest, nearest thing, and the only one?
13. Is the whole in view, in a glance, while the person works on a detail?

**The picture and the list**
14. ■ Is there a list where a picture was owed, or a list beside a picture that repeats it?
15. Is there a filter chip, tab row or sort control where the truth has one order?
16. Is any glyph unexplained by the picture it sits in?
17. Does a schema word (event, holon, float, anchor, settle, engine) reach the screen?

**Craft**
18. Does the response the hand expects land under a tenth of a second, with no spinner?
19. Does the type carry the hierarchy, with no box or rule doing its work?
20. Is anything there that carries no meaning (decoration, drawn light, a frame around a frame)?
21. Is confirmation asked for anything reversible?
22. Hide every drawing: do the words alone still tell one person the truth of their day?

**Tested, not assumed**
23. ■ Was this view tested with a person in the condition it is meant for (tired, on a phone, at night), and what did they say in one breath?
24. What does this view measure about itself, and where does the measure live?
25. ■ After one exchange with the agent, would the person say they spoke with someone, or that they operated something?

Scored last and never alone: **would a pilot, a surgeon or a grandmother trust this surface to tell them when something needs them, and otherwise leave them in peace?**

---

*When a line here fails a view that was plainly right, the line changes, with its why.*
