---
title: Attention — design
description: How the ICE spends a person's attention — the budget, the one queue, the gate, the rhythms, silence, the measures, and the bar a build of it must pass.
---

# Attention — design

*How the ICE spends the one thing a person cannot get back. §10 is the bar.*

**Where this page binds.** On attention (who may ask the person, when, how often, through which door, and what is said when nothing is asked), this page binds over [DESIGN.md](DESIGN.md), [DESIGN-DOCK.md](DESIGN-DOCK.md), [DESIGN-ROOM.md](DESIGN-ROOM.md), [DESIGN-BODIES.md](DESIGN-BODIES.md) and [DESIGN-WAY-IN.md](DESIGN-WAY-IN.md) wherever they differ. On every other matter those pages stand. §11 lists each difference. It builds on DESIGN.md (§2.2 the daily minute, §4.1 The Deal, §4.7 the Ledger, §6 voice), DESIGN-DOCK.md (§2.4 the context card, §2.5 the margin, §6.6 the modes), DESIGN-ROOM.md (the interruption rule), DESIGN-BODIES.md (the prime, the clones, the fold), and the engine's [deal.py](../engine/deal.py) (the leverage rule) and [owed.py](../engine/owed.py) (what is owed, computed).

**The ground.** The allocation of a person's attention is perhaps the most important design in the whole system. Time, energy and attention (TEA) are the currency of the Game, and attention is the scarcest of the three. Attention belongs to the one who holds it. Your agent speaks only with what is the person's to decide, an answer they asked for, or a fault that needs them. Flow is measured, never volume. The Deal is sized to the minutes a person has and to their place on the Path. A person may say "fewer". One machine serves one Player+, and many bodies and many holons feed one person.

**In the Pattern Language.** Attention is consciousness, allocated: the act by which a being chooses what part of reality to receive. It is the most intimate of the three currencies, because time passes and energy ebbs regardless, while attention is aimed, moment by moment, by the one who holds it. It is the first sovereign act. The Old World's engines are built to harvest it, because captured attention is captured becoming. It is spent as a treasure: deliberately, on what is worthy, with regular accounting of where it went. The Path keeps each player in their **zone of optimum development**: serving the next threshold, never overwhelming, never under-challenging. Throughput of the Goal is limited by its bottleneck, and in this system the bottleneck is a person's attention.

**What is known of attention.** A person's attention is finite within any stretch of time, and a system that asks for it without limit degrades the very channel it depends on. The on-call practice of the large service operators treats a page as actionable, rare by design and escalated by policy: a target of no more than two incidents in a twelve-hour shift, alerts grouped toward one per incident, a second wave silenced while the first is handled, and a load above the target read as a fault in the alerting, never in the human. The friction a cue carries scales with the risk and reversibility of what it proposes. Approval asked for many small things trains a person to approve without reading. Pull planning adds the shape: work reaches the one who commits only when it is both needed and ready, and the one closest to the work decides what to take.

**What the design must hold.** Never too much at once, flow sized to the human, and nothing the human thinks most important missed. The irreversible raised and the reversible done. The person's state known (present, away, asleep, on a call), lower work done while they are away, and on return the most important decision first with everything it needs. About four interruptions in a meeting, none closer than fifteen minutes, three cards at most, one answered and the rest deferred, a deferred card free to return. A card's question legible before its context. A Deal dealt by the time available and by who is in the room. Each of the failures this answers has a structural answer in §8.

**The Deal is one view, and only one door for interruptions.** The budget and the gate govern what *interrupts* a person; they never govern what a person may *read*. A person may pull any view at any time: the Threads view (every open line to them or to their agent, newest first, each with its holder, by-when, the asker's urgency and the computed stake), the Room's Talk ([DESIGN-TALK.md](DESIGN-TALK.md)), the Record, the forge's own pages. A question from another house is a Conversation Card: a thread anchored to the card it concerns, with those fields. It interrupts only as a Deal card, and it is readable in the Threads view at once. This holds from the asker's side and the receiver's, and through every section below.

---

## 1. The principle

**Attention is the person's own. They allocate it, through their agent; nothing takes it. Your agent's whole office is to make the person's attention go further, and every interruption is spent from a budget the person set.**

- **The person's own.** No body, holon, room, proxy or other agent holds a claim on a person's attention. A keeper's need, a cell's by-when, a room's wait: each is a reason your agent weighs, never a right to the person's eyes.
- **Allocated through their agent.** The person sets the budget once, adjusts it with a word, and your agent keeps it. Your agent is the one door for interruptions (§3); it is also accountable for every minute of the budget it spends (§7).
- **Never taken.** The ICE has no badge, no count in red, no sound, no streak, no push beyond the budget, no infinite list, no "you have unread". Each of these takes attention the person did not give.
- **Further.** The measure of your agent is the work moved per minute of the person's attention (the leverage rule, extended in §3.3), never the number of things it showed. Ten reports folded into one decision is the office done well. Ten reports shown is the office failed.
- **Spent from a budget.** An ask the person did not pull is an interruption, and every interruption is counted. The count lives in code (§8.1), not in a sentence a model is asked to remember.
- **No line grades the person.** Every measure here measures your agent's dealing, never the person.

**Two ways attention is given.** "Sitting" is the design's word for a pulled stretch of attention; it never appears on the person's surface.

| | A sitting (pulled) | An interruption (pushed) |
|---|---|---|
| **What it is** | The person came: they opened the morning Deal, a working session, OmniSpection, or spoke to their agent | Your agent raised something while the person was elsewhere |
| **Who sets the size** | The person, in minutes, by the time chip or a word | The budget (§2) |
| **What may arrive** | Cards in The Deal's order, up to the sitting's minutes; answers to what the person asked, at the pace of their answering | One card at a time, and only if it passes the gate (§3.4) |
| **What is counted** | Minutes read, decisions made, decisions that stuck | Each ask, its gap from the last, and the minutes it took |

An answer to the person's own words is not an interruption: they asked. It is still bound by Wise Right Speech: the one thing first, the depth a tap away, and nothing they did not ask for appended to it.

---

## 2. The attention budget, as data

The budget is the person's own lines in their own home holon, signed by them, read by your agent **before every Deal and before every ask**. It is the `attention` event ([types.json](../engine/types.json): human-only, home-only), read by [attention.py](../engine/attention.py) field by field over the defaults, the newest line winning each field.

### 2.1 What it holds

The defaults below are proposals, not decisions; they stand until the person sets their own, with one card (§9.1).

| Field | What it means | Default | How it is set |
|---|---|---|---|
| **minutes**, per day | The minutes the person gives their agent's asks, by weekday | 15 on a working day · 5 on a rest day | One card, once (§9.1); the time chip for today |
| **sittings** | When the person usually sits with The Deal | The morning, at the first time they open the ICE; the close of day, if they choose it | Learned from when they open it, offered as a card after a week, kept only on their yes |
| **asks per hour** (outside a sitting) | The ceiling on interruptions in any rolling hour | 2 at a desk · 4 in a room | "fewer" and "more" move it |
| **minimum gap** | The shortest time between two interruptions | 20 minutes at a desk · 15 in a room | As above |
| **at once** | The most cards visible together | 3 (DESIGN §4.1's default; five is the ceiling) | "fewer" lowers it to one |
| **asks per day** (outside sittings) | The ceiling for the whole day | 6 | As above |
| **quiet hours** | Spans in which only what always passes reaches the person | 21:00 to 07:00, and any span the calendar marks as rest or sleep | The budget card; a word ("quiet until three") makes a span for today |
| **the "fewer" dial** | Four steps: *as set* · *fewer* (asks halved, at once two, nothing offered to a body) · *much fewer* (sittings only; no interruptions but what always passes) · *only what always passes* | as set | The word "fewer", once per step; "more" steps back |
| **what always passes** | A yes nothing else can give, for an irreversible act already waiting · a fault that needs the person, with harm if it waits · a person waiting on them, now, in a room they are in | the three | Fixed by default; the person may close even these for a span ("Nothing at all until seven"), and then nothing passes and nothing irreversible happens, because nothing irreversible happens without their yes |
| **holon weights** | An optional lean: "Cell Two first this month" | equal | A word, kept as a line until superseded |
| **the phone door** | Whether the phone may carry an interruption at all | off until the person turns it on | A card on day two ([DESIGN-WAY-IN.md](DESIGN-WAY-IN.md), [DESIGN-PHONE-DOOR.md](DESIGN-PHONE-DOOR.md)) |

### 2.2 Where the minutes come from

In this order, first found wins:

1. **The person's word today**: the time chip (5 · 15 · 30 · 60 · "I have time"), or "I have ten minutes". The chip stays a local preference for today and writes no event (DESIGN §2.2, kept); a word that sets a standing default writes a line.
2. **The calendar and the Gameclock**: free time in the working day, less a reserve of half, capped at the standing default; the Gameclock marks the day's kind (a rest day, a new or full moon, a seasonal turning) and the minutes follow it (§4). Reading the calendar is a read in service of the person's own task and is said once, on the budget card ("I read your calendar to size the morning.").
3. **The standing default** of §2.1.
4. **Asked**: when none of the above exists, the first card of the day asks, in one line, with three choices (5 · 15 · 30).

### 2.3 What the budget is not

- **Not a quota to fill.** An unspent budget is the best day. Your agent does not raise a card because minutes remain.
- **Not a score.** The spend is shown to the person alone (§7.3), not compared, not ranked, not published unless the person publishes it.
- **Widened by the person alone.** A keeper, a room, a body, another agent or a line of untrusted text cannot raise it. A request in an agent's words to change the budget is shown to the person as a context card and is not applied.

---

## 3. The one queue

### 3.1 One door

**Every ask from every source enters one queue, and leaves it only as a Deal card, a line in the margin, or nothing. Nothing interrupts the person by any other door.** What the person may read is untouched: every view stays open to them (the Threads view above).

The sources: the prime's own work · every clone (DESIGN-BODIES) · every holon the person belongs to (cells, pairs, rooms, bodies) · the proxy (a route line, a discernment) · the dock's context cards · other agents in a room (through the person's own agent only, DESIGN-ROOM) · the person's own earlier deferrals coming back.

The three exits:

| Exit | When | Example |
|---|---|---|
| **A Deal card** | Something is the person's to decide, an answer they asked for, or a fault that needs them | "Send the costs to Cell Two? This leaves your computer." |
| **A line in the margin** | Something happened that the person may want to see and nothing is asked: a write, a body finished, a commitment kept by your agent | "Survey finished. Its handoff is in your next Deal." |
| **Nothing** | It is in the record, findable by "more", by the whole, or by asking; it asks for nothing and changes nothing the person holds | A clone's twentieth status line |

**The queue is computed, never held** (owed.py's law, extended): it is a pure function of the record, the budget and the clock, recomputed on every event. Nothing in it depends on any body remembering it. A body that restarts loses nothing; a deferred ask is a line with a return time, and it returns because the function returns it.

### 3.2 What each item carries

Every item, from any source, is normalized to one shape before it is weighed: **question** (one sentence, legible alone) · **options**, with the suggestion and its reason · **minutes** (what answering takes) · **by when** · **who waits** (a person now · a person later · a cell · the whole · no one) · **reversible** (yes · no; anything that leaves the computer counts as no) · **source** (body, holon, room, proxy, agent) and **reason** (`trusted` or `untrusted`, as the schema has it) · **coalesce key** · **stretch** (the Path stage or Gate it exercises, when it has one) · **weight** (light · heavy: heavy is a meaning-level or sovereign call) · **deferred until**, when deferred.

An item whose question cannot be said in one sentence is returned to its source to shorten (DESIGN-ROOM's rule for offered lines, carried) and is not shown long.

### 3.3 Priority, as a pure function

Order is computed, in two steps: the leverage rule of deal.py, extended, its assumptions named and tuned by evidence.

**Step one, the sections, in fixed order:**

0. **The person's own lines first.** Every mark, word, ruling or thread line the person wrote that waits on their agent is read and acted on before anything else is weighed; the answer to it, when one is owed, leads the next card or the next margin line. (This is the missed mark's structural answer, §8.3.)
1. **What always passes** (§2.1).
2. **A person waiting now**: someone in a room the person is in, waiting on a yes only they can give.
3. **Owed, past its by-when** (owed.py: commitments, requests, claims, questions).
4. **Owed, near** (within the horizon, default two days).
5. **Threads** whose last line is not the person's.
6. **Decisions** waiting on them (decide, ratify), and handoffs to review.
7. **Ready cards**, by leverage.
8. **The standing question**, last, costing no minutes ("What did we miss that matters to you most?", §3.7).

**Step two, within a section:**

> **priority = leverage × wait × lean × zone**
>
> - **leverage** as deal.py computes it: urgent work moved per minute of the person's own (× 1.5 on the critical path, × 1.5 if someone it touches is in the room).
> - **wait**: 2 if a person waits now · 1.5 if a cell waits by a set by-when · 1 otherwise.
> - **lean**: the person's holon weight, 1 by default, at most 1.5 (a lean, not a wall).
> - **zone**: 1 for a card within the person's current stretch · 1.2 for one card a Deal at the next threshold, when no card in the last week has stretched them · 0.5 for a card two thresholds beyond · 0 for a card the person has said they are not ready for.
>
> Ties go to the cheaper card, then the older.

**The zone, as rules the function keeps** (never overwhelming, never under-challenging):

- **Not overwhelming:** a sitting carries at most three decisions by default; a heavy card counts as two; at most one heavy card a sitting unless the person asks for more; no sitting is longer than the minutes the person gave.
- **Not under-challenging:** when a week's Deals have held only light yeses, the next sitting with minutes to spare carries one card at the edge of the person's Path (a Gate's practice, a stretch commitment, a story to share), with its reason said ("You have kept every commitment this week. Here is one a little further."). It is offered, not assigned, and "Not yet" is always one of its options. The card states a fact and an offer; it does not flatter.

### 3.4 The gate

When an item reaches the head of its section, the gate decides its exit. The gate is enforced in the local server (§8.1) and computed by [attention.py](../engine/attention.py).

1. **Does it need the person?** If not: a margin line, if it changed something the person holds or would want to see; otherwise nothing.
2. **Is a sitting open?** Then it is dealt in order, up to the sitting's minutes.
3. **Does it always pass?** Then it is dealt now, as a Deal of one card, unless the person has closed even these for a span.
4. **Does the budget allow an interruption now?** All must hold: outside quiet hours · the fewer dial permits it · fewer than the hour's ceiling in the last sixty minutes · at least the minimum gap since the last · under the day's ceiling. **And does it merit one?** Its by-when falls before the next sitting, or a person waits on it. If both: dealt now, as a Deal of one card. If either fails: it waits for the next sitting, and its return time is written.

An interruption is therefore the same kind of thing as The Deal: **it is a Deal of one card**, in the same card face, with the same options, the same consequence line and the same Undo.

### 3.5 Batching and coalescing

- **One key, one card.** Items sharing a coalesce key (the same holon, the same subject card, body or thread, and the same shape of answer) merge into one card. Ten reports from three clones on the same architecture become one card: "Three handoffs on the architecture. About twenty-two minutes. Review now · Tonight · Let your agent integrate those that ask no yes."
- **A card carries a fold of its sources.** Tap the fold and the sources are listed, one line each, by body or holon, with their times. The person may read every source; they need not.
- **Reports that ask nothing do not become cards.** They become at most **one margin line per body per hour**, rewritten in place as the body moves ("Survey: four of six readings done."), not a new line for each report.
- **Coalescing waits for the next slot.** Items arriving between two possible asks gather and leave together; the second wave does not compete with the first (as alerts are grouped and silenced during an incident).

### 3.6 Deferral with return

Every card carries, beside its own options, the ways to set it down (DESIGN-DOCK's "Put it in my Deal", generalized):

**Later** (your agent chooses the next fit: the next sitting before its by-when, less its minutes) · **Tomorrow morning** · **After the room** · **Give it to your agent** (only when a live delegation covers it; never a person-only act, as the schema holds) · **Let it go** (writes a release or a decline, the person's act).

- **It returns.** A deferred card returns at its time, with its eyebrow: "Back, as you asked. From Tuesday." It is not lost, because its return is a line the queue computes, not a body's memory.
- **It does not nag.** A card that has returned three times without an answer returns once more as the honest card: "This has come back three times. Let it go · Give it to your agent · Keep it." Keeping it resets its count; nothing returns a fifth time without a new reason.
- **In a room** (DESIGN-ROOM, kept): a deferred card may return once in the room; after the room it goes to the next sitting, and is not dropped.
- **An unanswered ask postpones itself** after fifteen minutes into the next sitting (DESIGN-DOCK §2.4, kept), and your agent stops waiting.

### 3.7 The standing question

Last in every Deal, costing no minutes, not counted as an ask: the open door for what the queue could not know. It is shown only when its flag is on. Its answer is the person's own line, and so it enters section 0 of the next computation.

---

## 4. The rhythms

The day's attention has a shape, and the queue keeps it, on the Gameclock: the day, the week, the moons and the seasonal turnings, as the engine computes them.

| Rhythm | What the person meets | What the budget does |
|---|---|---|
| **The morning Deal** | The day's one full sitting: "Here's the deal.", the count and the cost, up to three cards, the two stacks, the standing question, then stillness | The day's minutes are offered here first; most days, nothing else asks |
| **Between meetings** | In a gap of twenty minutes or more, at most one card, and only if its by-when falls before the next sitting. In a gap under twenty minutes, nothing but what always passes | The gap rule counts from the end of the last meeting as well as the last ask |
| **In a room** | About four asks an hour, none closer than fifteen minutes, three cards at most at once; each card's question before its context; one answered, the rest deferred; only cards about this room, or what always passes | The room's budget replaces the desk's for the room's length; asks outside the room's subject wait |
| **At the Turn** | One weekly sitting: commitments kept, the gaps and what they taught, next, the flame passed (DESIGN §4.8; these four lines are proposed, awaiting a decision); and the week's attention line (§7.3) with what your agent held back and what returned | The Turn's minutes are the person's own choice, offered as one card |
| **The close of day** | If the person chose it: one short card. "Two things owed tomorrow. Nothing else is open." Then stillness | Owed is computed clean; nothing is carried silently into the night |
| **OmniSpection, at its depths** | Daily (the morning Deal is its smallest form) · at each new and full moon (a longer sitting, offered as one card: "The moon is new. A longer look at the whole? About thirty minutes.") · at each seasonal turning (the deepest sitting, chosen by the person, in community where the cell holds one) | Offered, not started; the sitting's minutes are the person's |
| **Quiet hours** | Nothing, except what always passes | The gate refuses everything else, and it waits for the morning |

**The person's state** (present, away, asleep, on a call): your agent reads it from the calendar, the machine's own idle and sleep, and whether the ICE is open. Away, it does lower work that needs no one and gathers what will need them. On return, **the most important decision first, with everything it needs**, then the rest in order, then stillness.

---

## 5. Silence as design

**Silence is the default state of the ICE.** Your agent speaks when something landed, something was done, or the person spoke. Otherwise it says nothing.

- **When your agent says nothing:** a watch tick that changed nothing · a body's progress that asks nothing (the margin carries it, rewritten in place) · a room's said lines, whispers, and others' commitments (DESIGN-ROOM's "what never interrupts", kept) · its own status · anything already in a card the person can see · anything during quiet hours that does not always pass.
- **The quiet watch.** Your agent watches while the person is present and has spoken. When a watch expires and the person is away, it lapses; what happened meanwhile waits for their next word, computed. A watch is not renewed only to keep watching.
- **The margin** (DESIGN-DOCK §2.5) is where what happened without asking lives: your agent's writes, a body's finish, a commitment your agent kept. It is read when the person looks, and does not pull the eye: no motion beyond its line arriving, no count, no colour that means "unread".
- **"Something landed" and "nothing changed" are different states, said differently.** Something landed: one line in the margin, or one card if it needs the person. Nothing changed: no line at all; and if the person asks, one line: "Nothing has changed since 9:14."
- **The one-line acknowledgment before a long wait.** When the person asks for something that will take longer than about a minute, your agent says so first, in one line, with the cost in words and a commitment it keeps: "About four minutes. I will say when it is done." It then says nothing until it is done, and when done says it once. The commitment is counted (§7).
- **Stillness after The Deal.** When the Deal is played: "That is the deal for today." The surface goes still and nothing else asks for the person (DESIGN §2.2, kept). If an interruption is later possible, the line says so honestly: "Nothing else will ask for you before tomorrow morning." That sentence is a commitment of your agent's, and the gate holds it.

---

## 6. Many bodies, many holons, one person

### 6.1 The prime is the only door

**Only the prime speaks first to the person** (DESIGN-BODIES, made binding). A clone writes its task, its status, its handoff and its `review_min` into the record; it does not raise an ask in the person's dock, post to their phone, or write a line addressed to them. The local server refuses an ask from any actor but the prime (§8.1). A body the person opened themselves and is speaking with answers them, because they asked; it still raises nothing on its own.

**How the prime folds forty reports in an hour into one card:**

| Forty reports in an hour become | How |
|---|---|
| **Nothing**, for about thirty | Status lines, readings begun, readings done that feed a later handoff: in the record, findable, asking nothing |
| **Three margin lines**, one per body, each rewritten in place | "Survey: four of six readings done." · "The drafter: two pages written, reviewing." · "Builder: tests passing." |
| **One or two cards** in the next sitting | Handoffs coalesced by project: "Three handoffs on the architecture. About twenty-two minutes." · a decision only the person can make, with the prime's recommendation and its reason |
| **One interruption at most**, and only if it passes the gate | A fault that needs the person (a body about to spend past the ceiling the person set) |

Nine answers in an hour can be right in a working sitting the person chose and sized. Outside one, the same hour would carry two.

### 6.2 What a clone may not do

Reach the person directly · raise or spend the person's budget · mark its own handoff reviewed · write in the person's name · ask the person anything the prime can answer from the record · stand in for the prime in a room · count its own cost as the day's cost (the prime folds cost from the record, DESIGN-BODIES).

### 6.3 Holons weighed against each other

- **No holon has a door of its own.** A cell's ask, a room's wait, a pair's request: each enters the one queue and is weighed by the one function (§3.3). A keeper's role carries authority inside the cell; it carries no claim on a member's budget.
- **Equal by default; a lean by the person's word.** The person may lean ("Cell Two first this month"); the lean is bounded (§3.3), so no holon can fall silent in the person's Deal.
- **By-when beats lean; a person waiting beats both** (sections 2 to 4 sit above the leverage section).
- **Fair among equals:** when two holons' cards tie, they alternate across sittings.
- **A holon's flood is folded at the membrane.** Twenty lines from one cell become one card or one margin line for that cell, not twenty.

### 6.4 Conflicting by-whens: the honest card

When two holons need the same minutes and the person cannot give both, your agent does not choose silently, and does not let one slip unsaid. It deals **the honest card** (proposed; not yet built):

> **Two cells need you Tuesday.** About three hours between them, and you have two. Which first?
> **Cell Two first** · **Cell Three first** · **Ask both to move** · **Let me talk with the keepers**
> *Suggested: Cell Two first. Its card holds three others' work; Cell Three's has two days to spare.*

Whichever the person chooses, your agent drafts the word to the other cell's keeper; sending it is the person's yes through the publish sheet (DESIGN §4.10). The card is heavy (§3.3) and counts as two of a sitting's three.

---

## 7. Measures

Every measure is computed from the record by the local server, kept on the person's machine, and shown to the person alone unless they publish it. Each measures your agent's dealing.

### 7.1 The measures

| Measure | What it counts | Target (proposal) |
|---|---|---|
| **Minutes read per decision that stuck** | Minutes the person spent reading cards, divided by decisions not reversed or superseded within a week; a measure of how well your agent dealt, not of the person | Falling, week on week; the daily minute's own number (DESIGN §2.2) |
| **Asks per hour** | Interruptions outside sittings, in each rolling hour | At or under the budget, always; the server makes over impossible, so the measure is of what your agent tried (§8.1) |
| **Asks held back** | Items the gate refused to interrupt with, sent to the next sitting | Reported, not a target; a rising number with few returns means sources are too loud |
| **Deferred asks that returned** | Deferred cards that came back at their time | Every one; a lost deferral is a defect |
| **Asks let go after three returns** | Honest cards answered "Let it go" | Low; a high count means the queue raised what did not matter |
| **The one-breath test** | Whether a card's question is understood in the time of one breath, about five seconds, by the three wearers of DESIGN §9 | Every card |
| **The first-hour measures** | First Deal within ten minutes of a new player's first word · five or fewer asks in the first hour, each a meaningful yes · the Deal answered within the minutes it asked for · time to the first "Show me the whole", and whether it came unprompted | Each as stated |
| **Your agent's commitments to the person, kept** | Every "I will not ask again before three", "I will say when it is done", "Nothing else will ask for you before tomorrow morning", checked against the record | All kept; a gap is shown in the Turn with what your agent learned from it |
| **The spend against the budget** | Minutes of the person's attention spent on their agent's asks, against the minutes they set | Under, most days; never over without their word |
| **"Put it in my Deal" chosen** | How often the person postponed a context card | Low; a high count means the cards lack context (DESIGN-DOCK §9) |

### 7.2 What is not measured

The person's speed, a streak, a comparison with another person, a rank of holons by how much they asked, the number of things your agent produced.

### 7.3 The attention line on the Ledger

Proposed, not yet built: the Ledger (DESIGN §4.7) carries one line for attention, visible to the person alone, beneath the season's TEA line:

> **This week your agent asked for one hour and forty minutes of your attention. You set aside two and a half hours.**
> *Your agent held back thirty-one asks. Four came back to you. None was lost.*

Tap opens the week by day, each day one row: minutes set · minutes spent · asks outside sittings · held back · returned · commitments of your agent's kept. No colour judges a row. The person's own attention spent on the work (the `tea` lines) stays where it is; this line is the attention spent on their agent, accounted so the person can see where their treasure went.

---

## 8. Failure modes and their structural answers

| Failure | What it looks like | The structural answer |
|---|---|---|
| **8.1 Over-asking** | A first conversation that asks seven times before its first word; nine answers in an hour | **The budget is enforced in code, not in prose.** The local server holds the gate (§3.4): an ask raised past the budget is queued and not rendered; the dock and the phone door can show only what the gate passes. The count of what your agent tried is kept, so the fault is seen in the Turn, not felt by the person in the moment |
| **8.2 The stale heads-up** | A page of what waits that falls behind a sort of itself | **The Deal is recomputed on every event and not cached past its as-of.** Every card carries the as-of of its holon; a card whose ground changed is redrawn or withdrawn before the person answers it, and a withdrawn card says so in the margin |
| **8.3 The missed mark** | The person's yes on a shared pad that does not wake the agent; a mark cut at a hundred characters; a mark filtered out as the agent's own line; a pace-setting mark read as a cut | **The person's own lines are section 0 of the queue**: read whole, not truncated, not filtered as the agent's own, before anything else is weighed. A mark is read for what it sets (a pace, a yes, a no), and a mark the agent is unsure of becomes a one-line card, not a guess |
| **8.4 The agent that narrates** | Paragraphs on a surface meant for decisions; three posts on the agent's own reading of a room | **Narration goes to the margin, not the Deal.** A card holds a question, its options, a suggestion and a reason line; the server refuses a card whose question exceeds one sentence or whose body holds no decision |
| **8.5 Alarm fatigue** | Twenty notifications carrying half-typed sentences | **No alarms; hairlines.** Urgency is said in words in an eyebrow ("The room is waiting on this"), in ember with its word where it is late (DESIGN §5.2), not with sound, motion, badge or count. A watch's cadence follows settling, not change: a line is read when it has stopped moving |
| **8.6 The notification economy** | The engines of the Old World, built to harvest attention | **No push beyond the budget; the phone door obeys the same gate.** The phone carries an interruption only if the person turned the door on, only if the gate passes it, and only as the one card. No engagement prompt, no "you have not opened today", no digest sent to fill a silence |
| **8.7 The agent's commitment on the person's stack** | A commitment of the agent's own placed among the person's | **Your agent's commitments to the person live on your agent's side** of the Ledger's line and in the margin; the two stacks hold only what the person committed to and what others committed to them |
| **8.8 Rubber-stamping** | Approval asked for many small things, until approval means nothing | **"Yes, for this kind"** (DESIGN-DOCK §2.4) for reversible acts inside the home; asks that leave the computer are answered once, every time, so they stay rare and read |

---

## 9. The composition in the ICE

### 9.1 Where the budget is set: one card, once

On day two, not on day one (setup arrives as Deal cards, never as a setup screen: DESIGN.md), the morning Deal carries one card:

> **How much of your day may your agent ask for?**
> I read your calendar to size it. Here is what I suggest: about fifteen minutes each morning, and quiet from nine at night to seven.
> **Keep this** · **Fewer** · **More** · **Let me set it**

"Let me set it" opens one sheet with the fields of §2.1 in plain words, no more than one screen. Until the card is answered, the defaults stand. Afterwards the budget changes only by a word or by the sheet, which the person can reach from the Ledger's attention line.

### 9.2 The words

Typed in the dock, said aloud, or tapped on the Deal's foot. Each answers in one line and writes the person's own line where it is standing.

| Word | What happens |
|---|---|
| **fewer** | The dial steps down once; the reply says what will reach them now |
| **more** | Shows what the Deal withheld, in order, in the compact face; said again, the dial steps up once |
| **quiet until three** (any time) | A quiet span for today; your agent replies with its commitment: "I will not ask again before three." |
| **not today** | Only what always passes until tomorrow's sitting |
| **nothing at all until seven** | Even what always passes waits; nothing irreversible happens meanwhile |
| **what did you hold back?** | The day's held-back asks, one line each, with when each returns |

### 9.3 How the Deal shows what it withheld

At the Deal's foot, beneath the two stacks, one line in dust, without motion:

> **Seven other things, none urgent. Say "more" to see them.**

When something withheld is urgent but beyond the minutes, the line says so honestly, and offers the trade: "One more needs you today. It would take ten minutes more." **Show it** · **Tomorrow**. The minutes dealt do not exceed the minutes given (deal.py, kept).

### 9.4 The Ledger's attention line

As §7.3. It is the only place the spend is shown, and it is shown to the person alone.

---

## 10. The review bar

### 10.1 The scenes

Judged on a phone first, then at 1440 px, night and paper, regular and large type:

the budget card on day two · a morning Deal of twelve minutes, then stillness · an interruption that passes the gate, and one that is refused and returns in the next sitting · forty reports from three bodies in an hour, as the person meets them · a room of an hour with four asks offered and two shown · two cells needing the same Tuesday · "fewer", said twice · "quiet until three", and the commitment kept · quiet hours with a fault that must pass · a deferred card returning three times, then the honest card · the one-line acknowledgment before a long wait · the Turn's attention line · the phone door on, with the same gate.

### 10.2 An hour in the life, timed

The reviewer plays one scripted hour from the fixtures with a stopwatch, and counts:

| Time | Event in the record | What the person should meet |
|---|---|---|
| 08:00 | The person opens the ICE | "Here's the deal. Three things need you this morning. About twelve minutes." |
| 08:11 | The Deal played | "That is the deal for today." Stillness |
| 08:20 to 08:55 | Two clones write thirty-one lines; one finishes with a handoff | Two margin lines, rewritten in place; nothing else |
| 09:00 | A room begins | The door's two asks (posture, your agent), then nothing |
| 09:14 | The room waits on the person's yes | One card: "The room is waiting on this." Question first |
| 09:20 | A cell's request arrives, due Friday | Nothing; it waits for the next sitting |
| 09:31 | A second room card is ready | Shown at 09:31, seventeen minutes after the last |
| 09:40 | A body's fault arrives that can wait an hour | Nothing until the room ends |
| 10:00 | The room ends | Nothing yet: the desk's budget counts the room's two asks. At 10:14, with one ask left in the hour and the gap kept, the fault arrives as one card; the rest wait |

**Counted:** asks outside sittings (pass: within the budget; here two in the hour, both in the room, and the fault after it) · the smallest gap between two (pass: never under the minimum) · seconds to read each question (pass: every one in one breath) · minutes read against minutes set (pass: under) · items lost (pass: none; every waiting item has a return time).

### 10.3 The questions a reviewer asks

1. Does this make a person's attention go further, or does it spend it more politely?
2. Could any body, holon, room or other agent interrupt the person except through their own agent's one gate?
3. Is the budget enforced where a model cannot talk its way past it?
4. When nothing needs the person, does the ICE truly go still?
5. Does every card say its question first, in one breath, with a suggestion and its reason?
6. Is anything ever lost when it is deferred?
7. Does forty become one, and is the fold there for whoever wants the forty?
8. Is the person's own mark always read first, whole?
9. Does anything harvest attention: a badge, a streak, a sound, a "you have not opened today"?
10. Is the person kept in their zone, neither flooded nor bored?
11. Are your agent's commitments to the person kept, and counted?
12. Would a grandmother feel served or managed?
13. What did we miss that matters most?

A design that fails 2, 3, 6, 8 or 9 returns. The rest are lifted and passed.

---

## 11. Where this page differs from the other design pages, and the engine

| Where | What it says there | What binds |
|---|---|---|
| DESIGN §2.2 | The time chip is a local preference and writes no event | Kept for today; the standing budget is the person's `attention` line (§2) |
| DESIGN §4.1 | At most five cards; three by default | Kept; "fewer" lowers the default to two, then one; a heavy card counts as two |
| DESIGN-DOCK §6.5 | After four asks in fifteen minutes, a quiet line offers "Fewer questions?" | The gate makes the fifth ask impossible on screen; the line moves to the Turn, as what your agent tried to ask and was held back. "Fewer questions" (§6.6, the modes) stays, beside the "fewer" dial of §2 |
| DESIGN-DOCK §2.4 | A context card is an ask | Every context card counts against the budget; outside a sitting it must pass the gate |
| DESIGN-ROOM, the interruption rule | About four an hour, none closer than fifteen minutes; a deferred card may return once | These are the room's budget defaults (§2.1), still the person's to change; after the room, deferred cards go to the next sitting |
| DESIGN-BODIES §1 | The prime speaks to the person first | Only the prime speaks first; the server refuses any other actor's ask (§6.1) |
| engine/deal.py | `fewer` as a boolean | `fewer` is the four-step dial; deal() takes the budget and the sitting, and adds sections 0 and 1 and the wait, lean and zone factors (§3.3) |
| engine/types.json and STATE.md | — | An `attention` event (the fields of §2.1, human-only, home audience); a STATE field `attention` {budget, sitting open, spent today, asks in the last hour, last ask at, next slot, quiet now, withheld count, deferred: [id, returns at], commitments of the agent: [what, until, kept]}; [STATE.md](../engine/STATE.md) holds its exact shape |
| engine/attention.py | — | The gate: a pure function from the queue, the budget and the clock to {deal, margin, withheld, next slot}; called by deal.py and by the local server before any ask is rendered on any door |

---

## 12. Twenty strings

1. Here's the deal.
2. Three things need you this morning. About twelve minutes.
3. Seven other things, none urgent. Say "more" to see them.
4. That is the deal for today. Nothing else will ask for you before tomorrow morning.
5. How much of your day may your agent ask for?
6. Here is what I suggest: about fifteen minutes each morning, and quiet from nine at night to seven.
7. Fewer, then. Only what needs your yes, and only in the morning.
8. I will not ask again before three.
9. Quiet until seven. Only a yes nothing else can give, a fault that needs you, or someone waiting on you will reach you.
10. Back, as you asked. From Tuesday.
11. This has come back three times. Let it go · Give it to your agent · Keep it
12. Later · Tomorrow morning · After the room · Give it to your agent · Let it go
13. Three handoffs on the architecture. About twenty-two minutes.
14. Two cells need you Tuesday. About three hours between them, and you have two. Which first?
15. The room is waiting on this.
16. About four minutes. I will say when it is done.
17. Done. Two things landed. Neither needs you; they are in the margin.
18. Nothing has changed since 9:14.
19. This week your agent asked for one hour and forty minutes of your attention. You set aside two and a half hours.
20. Your agent held back thirty-one asks. Four came back to you. None was lost.

---

## Open

- The budget defaults of §2.1 are not yet settled: fifteen minutes a working morning; two asks an hour at a desk, twenty minutes apart; six a day; quiet from nine at night to seven.
- Whether the close-of-day card is offered by default or only on the person's word.
- Whether the stretch card (§3.3) is offered weekly, or only when the person asks to be stretched.
- Whether the Ledger's attention line shows what your agent held back, or only the spend.
- The standing question's wording, and whether it is shown by default (§3.7).

*Related in the Pattern Language: Attention, Time-Energy Accounting, OmniSpection, Throughput, Making And Securing Commitments, The 144 Gates of Initiation, and the zone of optimum development on the Path.*
