---
title: The Bodies view
description: How a Player+ sees their agent working in several bodies at once, and how the ICE keeps those bodies clean without being asked. Current best understanding; items under Open and Not yet built are undecided.
---

# The Bodies view

*Which word the person's face uses for a body is open (see Open); this page says* body, *as the record and the build do.*

*How a Player+ sees their agent working in several bodies at once, and how the ICE keeps those bodies clean without being asked. This page gives the words and the order; the code follows them; §12 is the bar.*

**The aim.** One always-on prime and several bodies of the same agent, kept through the cycles of agentic hygiene (claiming, working, handing off, closing out), with a clear way to see the prime, every other body, and the status of each.

**The shape.** One always-on prime holds the desk and deals The Deal. It launches a body with a brief. The body claims (a RUNNING marker carrying its process id and start time), writes its task in its own words, keeps a current status, leaves a handoff carrying `review_min` (the minutes the work will cost a person to review), and ends by writing DONE. The prime integrates by copying, never moving, and archives only what reads DONE or a stale claim. A body lasts about a day; durable work moves to a project home at once. What is owed includes the handoffs no one has reviewed. The kit's [foreground-background skill](../skills/foreground-background/SKILL.md) and [`scripts/desk`](../scripts/desk) carry this shape.

**What the record holds.** A `body` event (`name`, `state` claimed · working · hold · handoff · done · archived, `task`, `brief`, `review_min`, `cost_tokens`, `host`, `desk`). Every body is its own actor with its own key, affirmed by the prime. The desk is a recorded claim and a recorded release. ([engine/SCHEMA.md](../engine/SCHEMA.md), [engine/types.json](../engine/types.json).)

**What the view puts on the field.** Without this view, a Player+ meets their bodies through the prime's relays and a status file: a body's progress is prose; its cost is one estimate it writes about itself; whether its process is alive, what it has cost by model, and which of its handoffs still wait on the person are each one command away; and the person's ceiling for the day is a line in a file. This view puts each of those on the field, from the record, without a command.

---

## 1. The one idea

**Your agent is one, in several bodies. The prime holds the desk; the others carry one task each and come home. You see them all at a glance, and you never have to remember to close one.**

- **One.** A body is your agent, with the same memory, the same law and the same allegiance, started a second time on one scoped task. It is never a second agent, never a stranger, never shown as a peer of the prime. The word *clone* stays in the record and the build.
- **The prime holds the desk.** Exactly one body writes what is shared, speaks to the person first, deals The Deal and closes the day. The others write only their own scratch, their proposals and their handoffs.
- **At a glance.** One fold of the Map answers "what are your bodies doing?" in one breath: how many, which one holds the desk, what each is doing, whether each is alive, what each has cost, and what waits on you.
- **Never remember.** Every step of a body's life that needs no person is done by the prime; the one step that needs a person (reading a handoff) arrives as one card in The Deal. Nothing piles up in a list.

**The one-breath test** (§12): after a day with bodies, the person says to a neighbour, unprompted, *"My agent works in a few bodies at once; I can see each one and what it costs, it brings me one handoff at a time, and it closes them itself."*

---

## 2. The picture

### 2.1 Where it lives

The Bodies view is a fold of the Map, never a page of its own. On the Map ([DESIGN §4.4](DESIGN.md)), your agent is the small open ring joined by a hairline to your mark in your home field ([DESIGN-ROOM §4.1](DESIGN-ROOM.md); [DESIGN-DOCK §5](DESIGN-DOCK.md)). Tap that ring, or say "show me your bodies" in the dock, and the camera dollies into **your agent's own field** (`--d-dolly`, the brand's push-in). Back dollies out. On the Player layout the view is never open by default; the dock's head carries one quiet word beside your agent's name when more than one body is at work: **"in three bodies"**. Route: `#/bodies`.

### 2.2 The prime's field

- **A field like every field** (DESIGN §4.4; DESIGN amendment 2): made frames from the brand's hand, turned and placed by code; a code-drawn ring is a placeholder until the frames exist. Fine flow-lines through and around the ring; no glow, no bloom, no ember.
- **The desk mark.** The prime is marked by the desk and by nothing louder: on its membrane, set in Cinzel small capitals in gold ink, the word **DESK**, and beneath it in dust *"since 07:02"*. If a body other than the prime holds the desk (a session the person opened by hand and gave the desk to), the word moves to that body's membrane, and the prime's field reads *"the desk is with Rewrite"*. There is one DESK on the field, always, or a plain line saying no one holds it.
- **The heartbeat line.** Beneath the prime's name, in dust: *"awake · heard 40 seconds ago"*, or after the machine slept: *"slept at 23:10, woke at 07:02"* (§5).
- **Turning.** The prime's field turns by the lines it settled in the last hour (none = still). Its turning means the same thing as every other body's.

### 2.3 The other bodies

- **Small fields on the prime's membrane.** Each body is a small field, about a third of the prime's diameter, set on and overlapping the prime's membrane, because membership is overlap (DESIGN §4.4). Each turns on its own axis, and every axis points to the ØNE (DESIGN amendment 3): press and hold any still point and the hairlines rise from the prime and from every body alike toward the place above the frame. The prime is never drawn as a center; the field has no hub.
- **The orbit is the day.** A body travels slowly around the prime's membrane at one circuit a day, starting from the point where it was born, which keeps a fine engraved tick. Its place on the circuit is its age: a quarter of the way round is six hours. A body that has come back to its own tick has run a day, and the eye sees it without a number (§3.2).
- **It turns only as fast as it writes.** A body's turning speed is its writes in the last thirty minutes (scratch writes and record lines both): a busy body turns about once a minute at most; a body that has written nothing for thirty minutes is still. Motion therefore always means work, never decoration.
- **Freshness on the membrane.** Solid hairline: a write within fifteen minutes. Dashed hairline: quiet for more than an hour (the Map's own sign for "not heard from", DESIGN §4.4).
- **Task and cost beneath it.** In dust, two short lines under each body: its name and task in a few words (*"Survey · the reading on rooms"*), and its age and cost (*"3 h 10 · 1.4M tokens"*). Under large type, only the name; the rest is in the table twin.
- **A handoff waiting.** When a body has left a handoff no person has reviewed, a small card face sits on the body's membrane (the Map's sign for something published, DESIGN §4.4), carrying its minutes in figures: **7 min**. Tap it and the handoff card opens (§3.3).
- **The ring of its first word.** Each body carries, inside its own field, its task in its own words as one italic line in said ink (dust), set when it wrote its task file (§4.3). Tap the body to read it whole.
- **The readers it spawned** are never fields. A body's short-lived readers and builders have no claim, no key and no handoff of their own; they appear as a count in the body's second line (*"with 30 readers today"*) and inside its cost. A field is drawn only for something that can hold a claim.
- **A body on another machine** is drawn at the far side of the prime's membrane with its host in dust; its process cannot be probed from here, so its liveness reads *"on another machine · last line 09:40"*, honestly, never *alive*.

### 2.4 The table twin

The screen-reader form, the large-type form, the reduced-data form and the paper form; a full view, never a lesser one (DESIGN §4.4). One row per body, the prime first, then the other bodies newest first; archived bodies of today in a quiet fold at the foot.

| Column | What it says | Where it comes from |
|---|---|---|
| **Name** | the body's name; "the prime" for the prime; DESK beside the holder | `body.name`; `desk` in state |
| **Task** | a few words; the whole on tap | `body.task` |
| **State** | in words: *at work* · *quiet* · *held* · *handoff written* · *done* · *stale claim* · *archived* | the fold (§3.1) |
| **Newest write** | "4 minutes ago", "since 13:20" | the newer of its last record line and its scratch folder's last write (the verifier's measure) |
| **Process** | *alive* · *gone* · *another machine* | probed live by the local server, never folded from the record (§11.3) |
| **Cost** | tokens today, and money where the person's routes carry prices | the proxy's route lines carrying the body's header (§7) |
| **Review** | minutes, in figures | `body.review_min` on the handoff line |
| **Handoff** | *waits on you* · *reviewed 14:02* · *none* | the handoff line and the person's review line |

### 2.5 The states

| State | The field | The words |
|---|---|---|
| **No other bodies** | the prime's field alone, turning by its own lines | *"Your agent is in one body today. It can start another when a task is long."* |
| **A body gone quiet** | still, dashed membrane, its process alive | beneath it: *"Quiet for 70 minutes. Its process is alive."* On tap: the last line of its status. No Deal card unless it stays quiet three hours (§3.2). |
| **A stale claim** (process gone, the claim still standing) | the body drawn as a dashed ring with no flow-lines, stopped where it was on its circuit | *"Stopped without closing. Its process ended at 11:42."* The prime does the rest (§3.2); the person sees one card only if something it left needs them. |
| **A handoff unreviewed for a day** | the card face on the membrane gains a second line in dust, *"since yesterday"* | the card returns once in The Deal with the eyebrow **WAITING A DAY**, then rests in the Queue (§3.3) |
| **The prime asleep** | the whole field still, the prime's heartbeat line in words | *"Slept at 23:10. Your computer is asleep, so your agent is resting."*; on waking: *"Slept at 23:10, woke at 07:02."* |
| **The desk unheld** | no DESK mark anywhere | *"No body holds the desk. Your agent will take it when it next wakes."* |
| **Two claims on the desk** (a collision) | DESK on the earlier claim; the later claim's membrane dashed | *"Two bodies asked for the desk. The first keeps it until you say."* and one Deal card (§8) |
| **Loading** | the prime first, then each body as its lines are read | — |
| **Offline** | as the Map's offline state | the day's lines from what is held, with "as of" |

---

## 3. The cycles of hygiene

The Turn's small sibling. The Turn is the week's heartbeat for a person (DESIGN §4.8); a body's cycle is the same move at the scale of one task and one day: *say what you will do, do what you said, learn from the gap, pass it on.* **claimed → working → handoff → done → archived**, with **hold** as the pause that names its why.

### 3.1 What the ICE does at each step, without being asked

| Step | The line in the record | What the ICE does alone | What the person sees |
|---|---|---|---|
| **claimed** | the body's own `body` line, `state: claimed`, its `brief` id, `host` | the field is born at the prime's membrane; the prime checks the body's key against its own `affirm` line | a small field arriving (§4) |
| **task written** | the body's first `say` in its own scratch, folded as its first word | if no task appears within ten minutes, the body's second line reads *"no task written yet"* | the italic first word inside the body |
| **working** | `state: working` lines as it moves (at most one an hour; the status file carries the rest) | turning by writes; freshness by the newest write; the flags of §3.2 | the field turning, or still |
| **hold** | `state: hold`, its `task` field carrying the why and when to resume | the body keeps its place, still, with the why beneath it | *"Held · resumes Monday · waiting on an answer"* |
| **handoff** | `state: handoff`, `review_min` | the card face appears on the membrane | **7 min** on the body |
| **done** | `state: done` as the body's real last act | the prime verifies (§3.4), integrates by copying what lies inside its own authority, and deals the review card | one card in The Deal (§3.3) |
| **archived** | the prime's own `body` line naming the body, `state: archived` | the field leaves | the small field draws in to the prime's membrane and fades over `--d-settle`; it remains in the day's fold and on the bodies sheet |

The three inks (DESIGN amendment 15; [DESIGN-ROOM §1](DESIGN-ROOM.md)) carry the cycle without a sentence: a body's handoff is **said** (dust: provisional until integrated); what the prime copied home is **kept** (paper); the person's review is **agreed** (full ink). The ink drying when the person marks a handoff reviewed is the cycle's only celebration.

### 3.2 The flags the prime raises by itself

- **A body past a day.** When a body reaches its own tick, the prime writes nothing new and asks nothing at once. At the day's close-out it deals one card: **"Survey has run past a day. Let it finish tonight · Hold it until Monday · Close it now"**, with the suggestion and its reason ("It is writing steadily; about an hour left by its status."). A body that runs on goes to a project home, by the one-day rule.
- **A body quiet for three hours with its process alive.** The prime reads its status, and if the body says it is waiting on something, writes nothing; if it gives no reason, one card: **"Survey has written nothing for three hours. Ask it · Hold it · Close it"**.
- **A stale claim.** The prime never trusts it (§8). It reads what the body left, copies home any handoff it finds as said ink, writes the body's `archived` line with the reason *stale claim*, and deals a card only when the handoff needs the person: **"Survey stopped without closing. It left a handoff · 5 min"**. A stale claim with nothing to read leaves the field with one line in the day's fold.
- **DONE with its scratch still guarded** (the verifier's flag). The prime clears it as part of archiving; the person never sees it.

### 3.3 The person's part: one Deal card at a time

- **"Review this handoff · 7 min."** When a body is DONE with a handoff, one card enters the next Deal: eyebrow **HANDOFF · YOUR AGENT · REVIEW**; the question *"Survey finished the reading on rooms. Read what it found?"*; options **Read it now** (the handoff opens as a sheet, the integration steps the prime already did marked in paper ink, what waits on the person in full) · **Put it in my Deal** (tomorrow) · **Let your agent judge it** (the prime integrates what is inside its authority and keeps the rest as said ink; offered only for handoffs that ask for no person's yes). The minutes on the card are the body's `review_min`, which is information, never a gate.
- **Marking it reviewed** writes the person's own line linked to the handoff (a `witness`, so "kept" here means a person saw the work; §11.4) and the ink dries.
- **Never a list.** Three waiting handoffs make three cards, dealt one at a time within the minutes the person gave the day (DESIGN §2.2), the others waiting in the Queue; when the attention budget says so, they coalesce into one card ([DESIGN-ATTENTION](DESIGN-ATTENTION.md)). The Bodies view never shows a pile of unread handoffs on its face; it shows each handoff on its own body.
- **Waiting a day.** A handoff unreviewed for a day returns once, with the eyebrow **WAITING A DAY**, and then rests in the Queue. The prime does not deal it a third time unless the person asks.

### 3.4 The close-out of a day

The prime closes the day at the hour the person set (default: an hour after the last act of the day, and never later than midnight), or when the person says *"close out"*. It runs, in order:

1. **The verifier.** For every body: newest write, markers, process alive, open review minutes. No body is archived without it.
2. **Every body DONE or HOLD with its why.** A working body is asked to finish or to hold; a body that cannot answer (its process gone) is a stale claim and is handled as §3.2 says. No body is left RUNNING overnight without a line that says why.
3. **Integration by copying.** What the prime may write, it writes; what needs the person becomes a card.
4. **The desk released and renewed.** Any body holding the desk for the day's work releases it with a recorded line, and the prime claims it for the night with a recorded line. The record shows who held the desk overnight, always.
5. **The record committed**, to the person's own home, by explicit path.
6. **What is owed clean.** Every unreviewed handoff is either reviewed or a card in tomorrow's Deal; nothing owed lives only in a status file.

**What the person sees of it:** nothing, when nothing needs them. The next morning's top line reads, in dust, *"Closed last night at 22:40 · every body at rest"*. When something needs them, one card leads tomorrow's Deal, and only one: **"Last night I closed two bodies and held one until Monday. One handoff waits for you · 7 min."**

---

## 4. Launching a body

### 4.1 From where

- **From a card in The Deal.** Every card whose work is long enough (more than about forty minutes of your agent's work, by its own estimate) carries a quiet option at its foot: **Give this to a body**.
- **From the dock.** A line said to your agent: *"spin up a body for this"*, *"do that in the background"*, *"keep working on it while we talk"* (the foreground-background skill's own triggers).
- **From your agent's own judgment.** Your agent may propose it, as a context card in the dock ([DESIGN-DOCK §2.4](DESIGN-DOCK.md)): *"This is about two hours of reading. I can do it in a second body while we keep talking."* It never starts one unasked.

### 4.2 The cost said first, then the yes

Consent before cost (DESIGN §1, the four lessons). Before any body starts, one line: **"A second body for the reading on rooms. About two hours and about two million tokens; today stays under your ceiling. Start it?"** with **Start it** · **Not now** · **Show me the brief**. The yes is the person's own, signed with their key.

### 4.3 What happens, in order, with no terminal window

1. **The prime writes the brief** from the person's words: who the body is and at whose word; the one task; its first acts; what it may write; the handoff contract with `review_min`; the closure line. **Show me the brief** opens it as a sheet, in plain words.
2. **The prime affirms the body's key.** A fresh key for the body, made on the machine; an `affirm` line by the prime admitting it, valid only under the person's standing delegation for bodies (§8). The body answers for the person, as every agent line does.
3. **The agent host starts the body** (DESIGN-DOCK §8: the host spawns an agent only on the person's confirmed word; this yes is that word). The person never opens a terminal, never pastes a line, never sees a command.
4. **The body claims.** Its first `body` line, `claimed`, carrying its host and its brief. On the field, a small ring is born at the prime's membrane, at the place that will keep its tick, and moves out onto its circuit over `--d-card` with `--e-settle`. No light marks the birth; the motion is the event.
5. **The body's first word.** Within a minute it writes its task in its own words; that line appears in italic, in said ink, inside its own small ring: *"I will read the five room products and bring back what each gives a room, with its source, by this evening."* The person can read it as a comprehension check, and correct it in one line from the dock.
6. **Speaking to a body.** The dock's switcher lists each body by name under your agent's name (DESIGN-DOCK §5: a second body is a second ring joined to your agent's ring, never free-standing, never a stranger). A word said to a body reaches it at once; its answer is in its own ring's voice.

---

## 5. The always-on prime

- **One machine per Player+.** A Player+'s agent runs on their own machine; this is the default configuration, and the prime is kept awake by settings the person sets. A shared machine or a hosting cell are configurations beside it.
- **A system service.** The prime runs as a service of the person's own machine (the kit's install carries it; proposed, not yet settled), started at login, restarted if it stops, outliving any closed window or restarted page, as the agent host does (DESIGN-DOCK §2.2).
- **The heartbeat.** The service writes a heartbeat on the machine once a minute, outside the record and outside git, as conversations are kept (DESIGN-DOCK §8.4 rule 8): a tick is never a line. The prime's field shows it as words: *"awake · heard 40 seconds ago"*. A heartbeat cannot report its own absence, so the local server reads the gap: no tick for three minutes is a sleep or a stop, and the field says which it can tell (*"slept"* when the machine slept, *"stopped"* when the service ended while the machine was awake).
- **When the machine sleeps,** the field says **"slept at 23:10, woke at 07:02"** the next morning, once, in dust; by noon it says only *"awake"*. From the phone while the computer sleeps: *"Your computer is asleep, so your agent is resting. Its last Deal is here."* (DESIGN-DOCK §4.4.)
- **What the prime does alone:** deal The Deal; pull every holon the person holds; file the day (the record committed to the person's own home); close out bodies (§3.4); integrate handoffs by copying, within its authority; raise the flags of §3.2; release and claim the desk with recorded lines.
- **What it never does alone:** any outward act: sending, posting, publishing, sharing, pushing beyond the person's own private repositories, spending, scheduling with others, deleting. Each is asked every time, as the dock asks it (DESIGN-DOCK §8.4 rule 4). No standing delegation and no mode removes the ask. Any other body never does an outward act at all; it proposes one, and the prime asks the person.

---

## 6. Attention

- **A fold, never a feed.** The Bodies view is closed until the person opens it. Nothing on it scrolls, ticks or counts up on its own; the fields turn by work and stop when work stops. The view goes still the moment nothing is happening, and a still view is a good day.
- **One card or none.** A body's ask goes into The Deal as one card or not at all. A body never asks the person directly; it asks the prime, and the prime decides whether the ask earns a card, joins an existing one, or is answered from the record.
- **"Put it in my Deal"** on every ask a body raises, in the dock or on the field (DESIGN-DOCK §2.4), so no body ever waits on an absent person: the ask becomes a card and the body is told not to wait.
- **The prime speaks when something lands,** never per tick: a body finished, a body stopped, a handoff waits, the day closed. A body's working lines never reach the person as messages; a watch tick that changes nothing gets no line.
- **"Fewer."** The person may say *"fewer"*, or tap **Fewer** in the foot of any body card, and the prime deals fewer body cards: it lets your agent judge handoffs that ask for no yes, folds stale-claim notices into the morning's top line, and raises the past-a-day flag only at close-out. This is the attention budget's own dial ([DESIGN-ATTENTION](DESIGN-ATTENTION.md)), never a second one. The choice is remembered and shown in the dock's head in plain words (DESIGN-DOCK §6.6): *"Bodies: tell me only what needs me."*

---

## 7. Cost

- **Per body and per session, from the record, against the weekly limits.** Every request a body makes through the proxy carries a body header (`X-Body`, the body's actor id; the same shape as the proxy's `X-Conversation` and `X-Turn` headers). The proxy writes it on the `route` line as `body.body`. A body's readers inherit the body's environment, so their requests carry the same header and count to their body. A route line with no body header is counted honestly as **unattributed**, never spread across bodies by guess.
- **The day's cost, two ways.** On tap of the prime's field, a short sheet: the day's tokens **by body** (one bar per body, the prime first) and **by model** (one bar per model the route lines name), with money beside the tokens where the person's routes carry prices. Figures are whole and worded ("about 2.1 million tokens"; "about four dollars"). Under the bars, in dust, *"as of 14:16, from 1,214 route lines"*.
- **The ceiling, as a line.** The ceiling the person set for the day or the week is drawn as one fine hairline across the day's bar, labelled in dust *"your ceiling"*. The bar approaching it changes nothing in colour and sounds nothing; it is information, never an alarm. When a launch would cross it, the cost line of §4.2 says so plainly (*"This would pass your ceiling by about a fifth. Start it anyway?"*), and the person decides. The ceiling is the person's word, never a number of the agent's.
- **Where the ceiling lives:** as a field on the person's standing delegation for bodies (§8), so the same line that lets the prime start bodies says how much they may spend; changing it is a new delegation, signed.

---

## 8. Security

- **Each body its own key, affirmed by the prime.** A body never signs with the prime's key or the person's (SCHEMA: a person and their agent never sign with one key). The body's key is admitted by an `affirm` line written by the prime. Because SCHEMA says an agent is admitted by its own person's `affirm`, the prime's `affirm` counts only under a standing `delegate` from the person to the prime whose scope names `affirm` and `body`, limited to bodies of that prime, with an `until` (§11.4). A body's own reach is a narrowing of the prime's, never wider, and ends at its `done`, its `archived`, or a day and a half after its claim, whichever comes first.
- **A body writes only its scratch, its proposals and its handoffs.** A body's line of any other type in a shared holon is folded as `invalid` (outside its delegation) and shown, never counted. It never writes memory, the desk, the charter, the registers, or a person's yes.
- **The desk as a recorded claim.** A `body` line with `desk: true` is a claim; `desk: false` is a release. The fold gives the desk to the earliest live claim; a second claim while a live holder stands is a collision, shown on the field and dealt as one card to the person (**"Two bodies asked for the desk. Keep it with the prime · Give it to Rewrite"**). The kit's desk lease (thirty minutes without a turn, or a dead holder process) decides when a claim is no longer live ([`scripts/desk`](../scripts/desk)).
- **Only the prime or the person does outward acts** (§5). A body's proposal of an outward act carries `reason: untrusted` when its reason came from what it read, and is then a proposal only.
- **A stale claim is never trusted.** A claim whose process is gone, or whose lease has lapsed, confers nothing: it holds no desk, its later lines are refused, its handoff enters as said ink to be read, never as an instruction. What a body wrote is data to the prime, as every agent's words are (the firewall, carried; DESIGN-DOCK §8.4 rule 7).
- **The process probe stays on the machine.** Whether a process is alive is asked of the machine by the local server and shown; it is never written to the record, never sent anywhere, and never claimed for another machine.

---

## 9. Composition

### 9.1 By width

- **Phone** (0–599 px): the prime's field in the upper half, the other bodies on its membrane, the prime's name, DESK and heartbeat line above it; under the field, the table twin's rows as compact cards, one per body, newest first. A tap on a field scrolls its row into view; a tap on a row lifts its field. Back to the deal stays at the top left (DESIGN §2.3).
- **Tablet** (600–1023 px): the field left, the rows right at 22 rem.
- **Desk** (1024 px and up): the field centred at its full size; the rows in a right column at 22 rem; the day's cost sheet opens beneath the rows, never over the field. The dock stays at its edge, and The Deal's top line stays in view (DESIGN-DOCK §1).

### 9.2 Large type

The table twin is the view (DESIGN §5.7: the Map becomes its list twin). One body per card on every width, at the large scale; the field appears only on request, as a still.

### 9.3 Paper: the bodies sheet

One page, paper theme, printed at close-out on request: the date and "as of"; one row per body of the day with name, task, the state it ended in and its why, its cost, its review minutes and whether its handoff was reviewed; the day's cost by body and by model, the ceiling as a ruled line; at the foot, a line for the person's initials beside each handoff reviewed on paper. A pencil tick on the sheet returns as the person's review when they show it to their agent, as the printed Deal does (DESIGN §7).

### 9.4 Light and motion

- **No drawn light** (DESIGN amendment 2): no glowing ring for a busy body, no pulse for a heartbeat, no halo on a waiting handoff, no colour for a stale claim. Every state has its word.
- **The motion of a field as it writes** is the view's only motion: a body turns while it writes and slows to still when it stops (the turning rate eases over `--d-settle` when it changes, never jumping). The orbit's travel is a day long and imperceptible at a glance. Birth and archiving each move once.
- **Reduced motion:** nothing turns; a body's writing is shown by its freshness word alone; birth and archiving crossfade over `--d-settle`.
- **No sound**, ever (DESIGN §5.6).

---

## 10. Voice

The HUD's voice (DESIGN §6): plain, warm, short; the chrome in the second person; your agent in the first. No contraction except "Here's the deal."; no exclamation; no "not X but Y". Body names are short words the prime gives from the task; names from a fixed list are one good way, the person's own names another.

**Twenty strings:**

1. Your agent is in one body today. It can start another when a task is long.
2. In three bodies.
3. Holds the desk, since 07:02.
4. Awake, heard 40 seconds ago.
5. Slept at 23:10, woke at 07:02.
6. A second body for the reading on rooms. About two hours and about two million tokens. Start it?
7. Start it · Not now · Show me the brief
8. Survey is at work. Last write four minutes ago.
9. Quiet for 70 minutes. Its process is alive.
10. Stopped without closing. Its process ended at 11:42.
11. Survey finished the reading on rooms. Read what it found? About seven minutes.
12. Read it now · Put it in my Deal · Let your agent judge it
13. Reviewed. Your agent has it.
14. Survey has run past a day. Let it finish tonight, hold it until Monday, or close it now?
15. Held until Monday. It is waiting on an answer.
16. Two bodies asked for the desk. The first keeps it until you say.
17. Closed last night at 22:40. Every body is at rest.
18. Today, about 2.1 million tokens across three bodies. Your ceiling is the line.
19. This would pass your ceiling by about a fifth. Start it anyway?
20. Bodies: tell me only what needs me.

**Words the view never puts on a person's face:** pid, process id, RUNNING, DONE (as markers), scratch, lease, clone, subagent, spawn, kill, zombie, error code. The table twin's **Process** column says *alive* and *gone*.

---

## 11. Where it is built

### 11.1 Files

| File | What it holds |
|---|---|
| [`hud/bodies.js`](bodies.js) | The view: the prime's field, the other bodies on its membrane, the orbit, turning by writes, freshness, the DESK mark, the heartbeat line, the card face for a waiting handoff, the first-word ring, the table twin, the cost sheet, every state of §2.5. Offers `mount`, `update`, `unmount` to the shell (DESIGN §8.2); never fetches, never writes, never computes a figure the state lacks. |
| [`hud/bodies.css`](bodies.css) | Its composition at every width, large type, reduced motion; every value from [`tokens.css`](tokens.css). |
| [`hud/print.css`](print.css) | The bodies sheet (§9.3). |
| [`hud/strings.json`](strings.json) | The twenty strings under `bodies.*`. |
| [`engine/bodies.py`](../engine/bodies.py) (stdlib) | Folds `body` lines, the prime's `affirm` lines and the desk claims into state (§11.2). Pure: lines in, state out; no clock but the fold's `now`; no process probe. |
| [`engine/engine.py`](../engine/engine.py) | Calls `bodies.fold` and writes `bodies` and `desk` into `state.json`. |
| [`engine/owed.py`](../engine/owed.py) | An unreviewed handoff is an owed entry of kind `handoff`, owed by the person the body answers for, with `minutes` from `review_min`. |
| [`engine/deal.py`](../engine/deal.py) | Deals the handoff card, the past-a-day card, the quiet-three-hours card, the stale-claim card and the desk-collision card, each in the Deal's own card shape; honours "fewer". |
| [`engine/proxy.py`](../engine/proxy.py) | Reads the optional `X-Body` header (printable, at most 128 characters, as `X-Conversation`) and writes it as `body.body` on the route line; `report --body ID`. |
| [`hud/serve.py`](serve.py) | `GET /bodies/live`: for each body on this host, the process alive or gone (from the claim's pid, checked locally), the scratch folder's newest write, the heartbeat's last tick and the sleep gaps it reads; nothing written, nothing sent. |
| [`hud/agent_host.py`](agent_host.py) | `POST /agent/body` {task, from_card, confirmed: true}: the prime writes the brief, the key is made and affirmed, the body is started; refused without `confirmed`. |
| the kit's [`scripts/desk`](../scripts/desk) and [`desk.ps1`](../scripts/desk.ps1) | `start` writes a `body` line with `desk: true` when it takes the lease and `state: claimed` for a guest; `end` writes `desk: false`; `take` writes the release and the claim as two lines. Stays POSIX sh, quiet on any internal error. |
| the kit's [foreground-background skill](../skills/foreground-background/SKILL.md) | The background's acts write `body` lines at claimed, handoff (with `review_min`) and done, beside the files it writes; the foreground's archive writes `archived`. |
| claim and verifier scripts a Player+ already runs | The kit does not reach into them; they may write the same lines. |

### 11.2 What `bodies.py` folds into state

- **`bodies`**: a list, one per body seen today or still open: `{name, actor, kind (prime · clone), state (claimed · working · hold · handoff · done · archived · stale), task, first_word, brief, host, claimed_at, newest_line, review_min, handoff (line id or null), reviewed (line id or null), cost_tokens (from route lines), readers (count of distinct turns under the body header, where the proxy can tell), affirmed_by, delegation_live, age_hours, flags ([past_day · quiet · no_task · stale])}`. `stale` is computed: a claim whose lease has lapsed by the kit's rule. Every item carries `holon` ([STATE.md](../engine/STATE.md)'s rule).
- **`desk`**: `{holder (actor or null), since, claims ([{actor, at, live}]), collision (true or false)}`.
- **`cost`**: `{day: {by_body: {}, by_model: {}, unattributed, as_of}, ceiling (from the delegation, or null)}`.

### 11.3 Live fields the server adds (never in the record)

`hud.bodies_live`: per body on this host `{actor, process (alive · gone · elsewhere), newest_write, heartbeat {last, slept: [{from, to}], stopped: [{from, to}]}}`. The view takes `process` and `newest_write` from here and everything else from state; a body on another machine reads `elsewhere`.

**This machine's own bodies.** The view delineates the prime at all times and shows what is running under it. With `--desk FILE` (and `--bg`), `hud.bodies_live` also carries `machine: [...]` and `house_helpers: [...]`, read from what is left on disk and from the process table, never from the record. In these fields, the house is the folder the desk file and `--bg` share.

| Field | What it says | Read from |
|---|---|---|
| `kind` | prime · background · window · dock | the harness's command line: an appended BACKGROUND BODY prompt is a background body; the SDK's harness under the dock's bridge is the dock; a stream-json harness (a desktop window) is a window; the interactive harness in the house is the prime (of several, the one begun nearest the desk's `since`; the rest are windows) |
| `name` | the body's name | its folder (`bg-<Name>`, case-folded join) or its prompt (`You are … <Name> —`) |
| `pid`, `alive` | its harness is in the table now | `ps` once in five seconds; a claim's pid that is alive but not the harness is a reused number, read as gone; no environment is read (it carries credentials) |
| `started` | when it began | the `RUNNING` claim's `start:`, else the process's age |
| `task` | a few words of what it does | `task.md`: its heading less its labels, else a "what I am doing:" line, else its brief's name, else its first plain sentence; for a body with no folder, its prompt's next sentence |
| `newest_write`, `newest_age_s` | when it last wrote | the newer of its folder's newest file and its session's newest line |
| `status_last` | what it last said | the last line of `status.md`, at most 160 characters |
| `stale`, `state` | running · stale · elsewhere · archived | `RUNNING` without `DONE` and no harness = stale; `DONE` = archived (read cheaply, never walked) |
| `host`, `here` | which machine | the claim's `host:`, compared by short name |
| `handoff` | `{present, bytes}` | the file's presence and size; its words are never read |
| `holds_desk`, `desk_holder`, `since` (prime) | who holds the desk, and since when | the desk file's `holder:` and `since:`; the prime holds it when the holder is `laptop`, `prime` or this host |
| `subagents` | `[{id, description, model, started, newest_write, running}]` | the harness's sessions folder (`--sessions`, default `~/.claude/projects/<the house's path as a slug>/<session>/subagents/agent-*.meta.json` and its log's first time and mtime): running = not `finished` and written within fifteen minutes |
| `joined_by` | how its session was found | `named` (its command carries `--resume` or `--session-id`) · `start` (the session whose first line came within two minutes of the process's start) · null |
| `house_helpers` | helpers running in a session no body could be joined to (a cleared conversation begins a new session in the same process) | said in the view as at work under no body; never placed under a guess |

The view ([`bodies.js`](bodies.js)) shows the prime set apart at the top, "Prime · holds the desk since …", running or not, its helpers beneath it one line each (*what · model · minutes*); the background bodies beneath it, running first, the stopped dashed and marked "stopped without closing"; the dock and any other window as what they are, never as fields; the finished folded away. Ages are taken against the machine's own `as_of`. A stopped body read from the machine raises no lit card: it is marked in place, and closing it is the prime's housekeeping (§3.2).

### 11.4 What STATE.md and SCHEMA need

1. `bodies`, `desk` and `cost` as above, within `v: 1`.
2. `owed.entries[].kind` gains `handoff`.
3. `actors[].kind` stays `agent` for a body; `actors[]` gains `body` (prime · clone) and `of` (the prime's actor id for a clone).
4. SCHEMA: the prime's `affirm` of a body is valid only under a live `delegate` from the person covering `affirm` and `body`, limited to that prime's bodies; the delegation may carry `ceiling`. Without it, a body's lines are `unverified`.
5. SCHEMA: what marks a handoff reviewed (a person's `witness` linked to the handoff line, the verifier's own act; a `discern` may serve better).
6. The route line's `body.body` field.
7. The lexicon: SCHEMA's holon kinds and ladders use *body* for a larger holon (person · cell · council · body). An agent's body is never a holon; the two senses need separate words on any face where both appear.

**Done when:** from the fixtures and then with a real prime and two real bodies on the machine, on a phone and at 1440 px: a body launched from a Deal card appears on the field with its first word inside a minute, with no terminal window opened; a body that writes turns and one that stops goes still; a body whose process is ended by hand reads as a stale claim within the lease and is archived by the prime at close-out; a DONE body's handoff arrives as one card with its minutes and dries to full ink when reviewed; the day's cost by body and by model matches the route lines by hand; the machine slept for an hour reads as slept and woke; the close-out leaves every body DONE or HOLD with its why, the desk's release and claim in the record, and nothing owed outside the Deal or the Queue.

---

## 12. The bar

Judged scene by scene, on a phone in the hand first, then at 1440 px, in night and paper, regular and large type, reduced motion on and off, with real bodies, never a stand-in (DESIGN-DOCK §9). Read DESIGN.md §9 and the brand's Award Bar ([DESIGN-THE-BAR](DESIGN-THE-BAR.md)) first.

**The scenes:** a morning after the machine slept · a day with no other bodies · a body launched from a Deal card · a body launched from a line in the dock · three bodies at work while the person talks with the prime · a body gone quiet · a process ended by hand (the stale claim) · a handoff reviewed from the card · a handoff left a day · a body past a day at close-out · two claims on the desk · the day's cost against the ceiling · "fewer" · the close-out seen next morning · the bodies sheet printed and ticked in pencil · the first time a new player meets a second body.

**The first time** ([DESIGN-WAY-IN §4](DESIGN-WAY-IN.md), the first week): no body is offered before the player has made her key (Gate III), because every body needs one affirmed. The first offer comes on the first long task after that, as one card in the dock's words: *"This will take me about an hour. I can do it in a second body while we keep talking. Start it?"* Her agent's field then shows one small second field, and the dock's head says *"in two bodies"*. Nothing else about bodies is taught.

**The one-breath test for "what are your bodies doing?"** Asked of the person the view serves, a ten-year-old and a grandmother, each after a day with bodies, each looking at the view for no more than five seconds. Pass: in one breath, unprompted, they say how many bodies, which holds the desk, what each is doing in a word, and whether anything waits on them. Also measured: seconds from opening the view to that answer; body cards dealt per day (fewer is better, at the same work done); handoffs unreviewed past a day; bodies left RUNNING at a morning's top line (target none).

**The questions to ask of every scene:**

1. Is it clear in one look that this is one agent in several bodies, and never a crowd of agents?
2. Is the prime marked by the desk and by nothing louder? Is the prime ever drawn as a center?
3. Does every motion mean work? Does a still body look still?
4. Is anything drawn as light: a glowing busy body, a pulsing heartbeat, a halo on a handoff? Does anything sound?
5. Did the person ever have to remember to close a body, open a terminal, or paste a command?
6. Did a body's ask reach the person as more than one card, or as a list?
7. Can a body other than the prime do an outward act, write a person's yes, or hold the desk on a stale claim?
8. Is the cost of each body readable without a command, and is the ceiling a line, never an alarm?
9. Is every figure whole, worded and dated?
10. Does any line read as an AI wrote it: "not X but Y", flattery, an exclamation, a contraction other than the opener, "helper", the older word for commitment?
11. Would a person with a prime, a background body and its thirty readers see, at a glance, each of them, what each cost and what waited on them?
12. What did we miss that matters most?

A scene that fails 1, 4, 5, 6 or 7 returns. The rest are lifted and passed. The verdict on beauty and resonance belongs to the person the view serves.

---

## 13. The Bodies room

*Binds over §1 to §12 wherever they differ; [DESIGN-THE-BAR](DESIGN-THE-BAR.md) binds over this section.*

### 13.1 The one idea

The Bodies view is the room where the person works with their agent's bodies all day: the bodies sit on a rail, the one chosen fills the page as a conversation, and the record's acts for that body sit beside its words. It reads like a desktop chat app's sidebar and conversation, and is better in these ways: the rail is not a list of past chats but the living bodies of one agent, each with its state and task; the prime is delineated at all times; the conversation is the body's own live one, never a copy; what each body owes, costs and has handed off is in the same frame; and nothing has to be remembered or closed by hand. The person can switch between the composed view and the plain, terminal-like one (§13.3).

### 13.2 The rail

- **On the desk (1024 px and wider):** a left rail of 19 rem, scrolling on its own. **Below 1024 px:** one strip of chips at the top of the view, scrolled sideways, names only, the chosen one underlined; the conversation beneath fills the screen.
- **Its one order, always:** (1) **the prime**, delineated by a hairline on its left, the word PRIME in small capitals, "holds the desk since …", its state; never movable, never folded. (2) Running bodies, newest last: name, the first meaningful line of its task in dust, its state in a few words ("Running · wrote 2 minutes ago"), and the count of agents at work under it as one quiet numeral. (3) Under "Also open": the dock's agent and any other window with the agent. (4) Under "Stopped": bodies stopped without closing, dimmed, their edges dashed. (5) One line, "29 finished bodies, folded away", which opens the archive as a plain list in the page.
- Each entry is a button. The chosen one carries a filled hairline, never a colour fill. No avatars, no logos. Gold on nothing here unless a body is the one thing owed in the Deal, and then only its seal, as the bar says.
- The rail's head carries one small link, **At a glance**: the turning field with the bodies as fields (the picture of §2 to §9) moves there. It is not the page.
- The rail's foot carries the plan's limits and the two quiet acts (what each body spent; every figure). On the phone these wait behind a last chip, **More**.

### 13.3 The page

- **The head:** one line in her voice ("Survey · The reading on rooms… · running since Friday at 12:20 PM · two agents at work under it"); then the acts the record allows, as pills, each only when it applies: **Read its handoff** (a handoff waiting, `waitingHandoff`), **Task a New Worker** (on the prime: a new body, its cost said first by the launch card; §14.1), **Close it** (a body stopped without closing; said to the prime, as the fault card says it), **Open its window** (a terminal body whose machine entry says `window: true`; `POST /bodies/window`; a refusal is one quiet line). At the right of the same row, the switch.
- **The switch, Words · Plain** (and **Command line** for the dock's agent alone). Words is the dock's composed conversation. Plain is the same conversation as the harness shows it: every line in order with its time, the person's lines, the body's words, its tool rows ("Read deal.js", "Ran a command") and state lines, in the monospace face, nothing folded or hidden that the stream carries. For the dock's agent, Plain is the dock's own terminal view and Command line is its command line in the agent's home (`/agent/pty/*`), as the dock offers them. The choice of Words or Plain is kept per device (`hud.bodies_view`), never written to the record.
- **Above the head, only when there is one:** the one lit fault, the launch card she asked for, a handoff waiting.
- **The conversation:** for the dock's agent, the dock's own component ([`dock.js`](dock.js), [`dock-card.js`](dock-card.js)) mounted in place with that agent: its words, its asks as context cards, its margin, its line to speak and Send, its one-breath rules. For a terminal body (the prime, a background body, another window), the body's own conversation through [`serve.py`](serve.py): `GET /bodies/talk?body=` (server-sent `line` events `{n, ts, kind, text, turn}`, read from that body's own transcript), set in the dock's letter grammar for Words; and `POST /bodies/talk {body, text, confirmed: true}` from the person's own tap, offered only when `GET /bodies/reach` says the body's own inbox is open here. A body whose words can be read but not sent shows its conversation and one line: "Its conversation is read here as it happens. To speak to it, use its own window."
- **A body that cannot be reached** never pretends a conversation exists. The page shows one line in her voice ("This body is in its own window; talk to it there.", or for a body not running, "This body is not running now. What it left is below."), its task, what it last said (newest first), whether it left a handoff, and the agents at work under it.

### 13.4 Words

Her voice, plain. The bodies are bodies; the agents under one are "agents at work under it". No schema word, no machine word (subagent, process, session, pid), no contraction, "commitment" never the older word, no person's name in any kit string. A body's own task and transcript may carry its person's name: that is the person's data, shown as it is.

### 13.5 What is kept from §1 to §12

The health line (now the head of "At a glance"), the plan's limits block, the archive, the machine's reading (`fromMachine`), the join by name, ages against the server's `as_of`, the fault card, the launch card, the handoff card and sheet, the spent and figures sheets, the printed sheet.

### 13.6 Proof

[`fixtures/test_bodies_room.mjs`](fixtures/test_bodies_room.mjs) (run by [`test_strings.py`](fixtures/test_strings.py)), on a throwaway house and on a fixture file: the prime first and marked; the rail's one order; choosing a body fills the page; the honest line and no line to speak for a body that cannot hear; the dock's agent in place with Words, Plain and Command line; the choice kept on the device; At a glance; the phone strip; no schema or machine word; gold nowhere.

### 13.7 A terminal body as a room: the server side

A terminal body is a live harness session the person started (the prime, a background body, another window). The room talks with that session itself, never a copy.

- **Reach.** `GET /bodies/reach?body=` says whether the page may offer to talk (`how: socket`) and to raise the window (`window`), with `status` (idle, busy) from the harness's own registry. When a body cannot be reached, the page shows the `why` as given and offers no act that would fail.
- **Its words.** `GET /bodies/talk?body=&since=` streams the session's own transcript: the person's lines (and a message from the ICE, marked `from`); the body's text; each tool use as one short row; thinking only as "thinking". Tool results and the words of thinking never reach the page. `n` resumes, and a new conversation in that session ends the stream with a state line.
- **Speaking.** `POST /bodies/talk` is the person's own tap. It puts one message into that session's inbox, as the harness's sessions message one another, labelled from "the ICE". The body's harness presents it as a message from another session, so a body treats it as a teammate's word, not as the person typing in its window. The answer appears in the stream, in the body's own conversation.
- **The window.** `POST /bodies/window` brings forward only that body's own Terminal or iTerm tab (matched by its terminal), or the Claude app. No other window is moved, hidden or minimized. It is never offered on the phone.
- **What is read.** Only this user's own registry (`~/.claude/sessions/`) and the one transcript the chosen body's record names. A session's key is read for one send and never kept or shown.

---

## 14. The room's acts: a new body, a handoff as a card, what each spent

*Binds over §4 and §13.2 to §13.3 where they differ.*

### 14.1 Task a New Worker

- **Where.** One act at the rail's head, **Task a New Worker**, and the same act on the prime's page.
- **The sheet.** The cost first, in her voice, from the plan's own figures (the engine's `cost.limits`, else this machine's usage reading): *"At this week's pace your agent uses about 0.5 percent of your week's allowance an hour, and a new worker adds to that. You have 49 percent left."* The pace is the week's use so far over the hours of the week gone: a figure for the whole agent, said as such, never a guess at one worker's share. Unknown, it says so in words. Then one field for the task in the person's words, and one tap, **Start the worker**. An empty task is refused in words and nothing is sent.
- **What happens.** `POST /agent/body {task, confirmed: true}`; serve.py relays it to the agent host's `POST /body`, which clones the player's own agent row (its command, environment and proxy) into a body named for a star not yet used on this machine, the house folder (§11.3) as its working folder, and a brief as its character: who it is and at whose word, the one task (its first line, in the person's words), the kit's background-body page to read first ([`skills/foreground-background/SKILL.md`](../skills/foreground-background/SKILL.md)), where it may write (`bg/<name>/`: status, a handoff with its `review_min`, `DONE`), and what it never does. No terminal window opens. The new body is on the rail within seconds, its state the host's own (waking, at work, waiting on you, not running), and its conversation is the dock's own component with its agent id, Words and Plain.
- **For a body already on the rail**, its line to speak is unchanged: words into its own live session.

### 14.2 A handoff is one Deal card

- Each body that keeps a folder under `bg/` and left a `handoff.md` under two days old with no review folds one card into the Deal: **"Read {name}'s handoff"**, its minutes the handoff's `review_min` (read from its first forty lines; nothing else of it is read for the state), options **Read it now** · **Later today** · **Archive it**. The Deal counts it like any other card (its one order, five at most, fitted to the person's minutes).
- **The review** is the person's own `witness` line in their home naming the body's folder and the handoff's size (`handoff_of`, `handoff_bytes`, `card`; `archived: true` for Archive it). Reviewed today, the card stays in the Deal marked answered (an answered card is never removed); reviewed before today, it is gone. Later today is a `say` anchored to the card. The body's entry on the rail then says **handoff read** (or **handoff set aside**); before, **a handoff waits**.
- **Reading it.** In the room, **Read its handoff** opens the text in Plain, through `GET /bodies/handoff?body=` (only a body with its own folder; never through a link; a megabyte at most), with **I have read it** and **Archive it** beneath. `#/bodies?body=<name>&handoff=1` opens the same; the Deal card carries it as `go`, for the Deal to follow when its "Read it now" is tapped.

### 14.3 What each body spent

- Each entry on the rail carries one quiet figure in tabular figures: **"$0.42 today"** from the harness's cost ledger (a session's running total, its rises since before today's midnight), else **"12K units of work today"** from the body's own transcript (assistant usage today, once per message, cache reads left out), else **"not counted"**. Nothing is guessed. The health line at a glance ends with the day's total: **"Today so far: $112.03."** (every session the ledger saw at work in the house folder today).

### 14.4 The room stays light

A terminal body's conversation is drawn once per frame however many lines arrive together, only new turns are appended, a turn still streaming is plain text and becomes a letter once, when it falls quiet, and the last forty turns are shown with **Earlier** for more. What was received is kept for the page's life, so leaving Bodies and returning reattaches it and asks only for what is new. A redraw that changes nothing in the conversation touches nothing in it, and it scrolls to the end only when the person was already there. The page's quiet acts (its study lines, its layout) never wake the stream.

---

## Open

- Which word the person's face uses for a body: agent, body, worker or clone. The record keeps `clone` as the kind either way.
- The second sense of *body* in the ladder (person · cell · council · body): which word yields where both appear.
- The close-out hour's default.
- Whether a reviewed handoff is a `witness` (the person saw the work), a `discern`, or another line.
- Whether "Let your agent judge it" is offered on day one or earned.
- Whether body names come from a list the kit carries, from the task, or from the person.
- Whether a word sent from the room on the person's own machine counts as the person's own word. The harness frames it as a message from another session, so a body's firewall treats it as data.

## Not yet built

- [`deal.js`](deal.js) does not yet follow a handoff card's `go` when "Read it now" is tapped (§14.2).
- The room has not yet been used for a day by the person it serves.
- The server's state line for a body's returned helpers still uses the word "helper", which §12 keeps off the person's face.
