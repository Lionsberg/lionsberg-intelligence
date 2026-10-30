---
title: The Talk — design
description: The design of the Talk, the ICE's first place, where the person works with their own agent, sees everything it does, and enters the Game by asking. Current best understanding; items under Open and Not yet built are undecided.
---

# The Talk — design

*The conversation-first place of the ICE. You work with one agent, your chief of staff. It does what you ask, shows you everything it is doing while it does it, runs the other agents for you, and brings the Game in when you ask for it.*

This page builds on [DESIGN-THE-BAR.md](DESIGN-THE-BAR.md) (§1 to §3 and the sheet), [DESIGN-DOCK.md](DESIGN-DOCK.md) (the letter, asks, one breath), [DESIGN-BODIES.md](DESIGN-BODIES.md) (a worker, its cost said first, its handoff), [DESIGN.md](DESIGN.md) §4 (the card) and [the record's day one](../skills/the-record/day-one.md). Where they differ from this page, they bind.

## 1. The one idea

**The default is working with your agent.** The Talk opens as a conversation and nothing else. The person says what they want; the agent does it, shows that it is doing it, and says when it is done, the way a good agent in a terminal works. The Game is a harness for people and their agents: it guides gently and wisely when asked, and it never constrains unasked. The person enters it by asking, and it leaves when they do.

**One house**: one record, one engine, one server, one dock component. The Talk is a place, `#/talk`, and it is the first place. The frame at the foot reads **Talk · Agents · More**, centred, on every place and at every width. The dock's own door leaves the foot, because the Talk is the agent's door. Every other view (the Deal, Threads, the Map, the Chain, Spaces, the Ledger, the Record) waits behind More, in the order of use, set once.

**The one-breath test.** After the first minute, the person says to a neighbour, unprompted: *"It asks me what needs me, one thing at a time, and it tells the others what to do."*

In what follows, *she* and *her* are the agent; *the person* is the one she serves.

## 2. The phone, scene by scene

The phone is the first body, never a shrunken desk. One column, one screen, no page scroll, at 390 and at 320 points; the stream scrolls inside it.

### The arrival

Behind everything, one still frame from the brand's hand, dim, chosen by the hour and the state: the field gathered on one thing when something is late or the whole waits on it; the many fields when workers are at work; the person's field at rest, morning, afternoon or evening, when nothing waits. The frame is ground for a kind of thinking, never information (DESIGN-THE-BAR §3).

**The greeting is only a greeting**: the time of day, the person's name when the record holds it (`hud.person.name`, or the person's own entry among the actors), and her name, from the host or the agents file. *"Good afternoon. I am Iris."* Her name is remembered on the device, so no frame ever shows another face; a placeholder name ("Player") is no name. No card, no question, no count. Nothing is dealt on load or on a tap. The greeting and the scene are painted from the state in the first frame; the agent is never woken by a page load.

**The return.** A fresh device, a return after an hour, a return after a day, or a long quiet: everything said before folds above **Earlier**, and the first screen is the greeting or the return line. The return line is one line of what changed, never a replay and never a count: *"While you were away, Worker A came back with a handoff."* A reload within ten minutes of the person's last act folds nothing. The page keeps its own turns on the device as what they are (`person`, `page`, `settled`, each with its time) and restores them as such on a reload. An ask still open is never folded away.

### The stream

**The conversation is the page.** One stream holds, in time order and each at the time it came: her name once at its head, in small caps; the person's words; the page's own answers; her turns; the rows of what she does (§4); her asks and every other agent's asks; the questions of the Game when it is in play. Nothing in the stream is pinned. The owed question keeps its place for the whole of her turn, and a new turn comes below it.

**The foot.** The line to speak is fixed at the foot. Above it sit the rows of workers at work (§4.4) and Stop, in its own place, so the row never moves; Send never leaves the gutter, and the microphone sits beside it. Under the line to speak sits the status line (§4.1). On a phone the foot (Talk · Agents · More) has its own ground, and every place ends above it. The keyboard never hides the line to speak, and on a phone the frame steps away while the person types. An empty line to speak shrinks back on send.

**Keeping the person's place.** When the person sends, their line goes to the top of the view and the answer grows beneath it; their own scroll lets it go. Otherwise a redraw keeps the person's place, following the end only when they were already at the end. The stream's top edge fades a whole line, never slicing one. When the open question has scrolled away above, one quiet pill, *"The question, above"*, sits at the stream's foot until it is in view again.

**Words once set before the person are never taken back**, whatever follows them. An answer never takes anything away.

### Plain work

She asks before an act only when the permission mode asks her to (§5), never to open a conversation.

**Owed now, once.** She brings a thing unasked only when it is owed now: a by-when has passed, or the whole is waiting on this person. It is one line at the end of her next reply, never a card, and never twice in a sitting: *"One thing before you go: the harvest count was due yesterday."*

### Entering the Game

*"Deal me"*, *"what needs me?"*, *"let us play"*, *"show me the chain"*, *"what is blocked?"*, *"next"*: each brings the Game into the stream as she would bring anything. From then on, in that sitting, the hand comes one question at a time. *"That is enough"*, *"back to work"*, or simply a new subject, and the Game folds to one quiet line.

**Her question is her words**: the card's own question, the choices in one sentence, the one she would choose and why. *"Which day should Cell Two meet this month? Thursday evening, Saturday morning, or ask the cell. Five of the seven said Saturday works, so I would say Saturday morning."* It is answered by a word or a tap. It carries the one gold hairline on the screen; everything around it is in ink. The Deal, with its full cards, is one tap behind More.

**One count.** The count is what the Deal can deal the person: the open hand and every owed thing that is a card still unanswered, each once (deal.js `owedLine.count`). "What needs me?" (in a few plain forms), the question's quiet *"1 of 7"* and the Deal's own card all say that one number. "What needs me?" is the page's to answer at once: the count and the first by its name, *"Four things. The first is …"*, with *past its day* when it is, and the question left to the card. An owed thing that is not yet a card is said apart, and only when true: *"And two more that are not yet cards."* What waits on a card reads as a sentence: *"Booking the hall waits on it, then the gathering."*

**One first.** The one owed list's first (`firstOwed`) is the question when it is a card the person can answer, in the hand or beyond it. "What needs me?" names that same card, and the Deal's opener and the card in front of the person are that one.

**The end of the hand.** At the end of the hand the Talk reads the hand as the Deal does: *"Four more can wait, or say next."*, and *next* deals it. Answered cards are never dealt again, so no line says that more can wait over nothing. *"That was the last one. Nothing else needs you now."* comes only when the owed list and every agent's asks are both empty.

### The person's words act

With a question up, the option's words (or the words that set one apart), its place (*the second*, *2*) or *yes* for the suggested one settle it as a tap would. A line that is exactly one open card's option settles that card even with no question on screen. The answer writes the same act the Deal writes, through the same `/act`, with the same five seconds of Undo; the Deal's count agrees at once, because it is the same store. Her agent is told through the page context (§6).

**The settled line.** The answered question stays as one quiet line, and beneath it what follows from the answer when the card says it (*"I will tell Cell Two it waits until next week."*), else the choice itself: *"Saturday morning, then."* Undo sits beside it as a quiet word. Never a filled *"Marked …"*. After three, the earlier settled lines fold into one quiet line (*"Three marked earlier · show"*). An option that leads somewhere (`go`, or "Read it now" on a handoff) is followed, and says nothing about marking.

**Her own proposals and marks.** When she proposes an answer, it arrives as the host's ask of kind `act` (`{card_id, option_index, option}`); on the person's yes it writes the act, and the dock tells the page (`ctx.settleCard({card, option, index, written: true})`), which marks it answered and paints the settled line with its keepsake, writing nothing twice. A mark she made on her own word (`decided`) settles the same way: *"Decided for you: Sunday morning."*, with Undo.

**The person's name for a card.** When the person keeps a name ("Let's call it The Gathering Day" → keep it), the host's answer returns `{named: {card, name}}`. The page keeps it per card in the fold (state.js `foldNames`, `read.cardName`), and the question, the Deal's card and the keepsake's caption carry it.

**The pace.** After an answer, tapped or typed, the next question comes within two seconds of idleness (the line to speak empty, no key and no tap); until then one dust line says *"One more."*. Never a stack. **The question on screen is never swapped mid-thought**: when the record changes while the person is typing, the question stays while the line to speak has focus or words and for twenty seconds after the last keystroke, and the change comes after nine seconds of quiet with the line empty (the current setting; see Open).

### Asks

**Every ask is a line.** An ask (keep, permission, a worker's, a Start, a Mark) is her line, or a worker's line under the worker's name in small caps, answered by the person's next words (yes, no, keep it, not now, start it). The page answers it through `/agent/answer`; the host does the same from `/agent/say` (`answered`). No quick-reply row. Answered, an ask stays as one quiet line (*"May I remember that we go slowly? · not this"*). The Agents place keeps its ask cards.

**Every agent's asks reach the Talk**: the asks the host holds for every agent of the person (`hud.agents[].asks`), her own in her conversation and each worker's beside it, with who asks (*"Worker B, one of your workers, asks you"*). The same ask is in the Deal; answered in either, it is answered.

**The question never gives way to an ask.** An ask takes its place in the stream; it never covers the question, and the page's own answers always paint where the person can see them.

### A worker, tasked in one sentence

*"Have a worker draw the map of the commons."* The line goes to her, and she only proposes, as a chief of staff does: the cost in words, then *"The task, in your words: draw the map of the commons."*, then *"Start it?"*. The host reads that form at the end of her turn and raises an ask of kind `worker`: the task and where it reaches, answered *"Start it"* or *"Later, in the Deal"*. While it is open it holds the place; any question waits behind it, never two at once. Start is the person's own word: it starts the worker (the same yes as Task a New Worker) and then answers the ask, so she hears it; Later answers it, and nothing starts. Where no agent can be reached, the page proposes the worker itself, with the same two answers.

**When the worker comes back**, its end is one line in the stream (*"Worker A has finished: …"*, *"Worker A finished · 7 min 33 s"*) with its handoff folded beneath and **Read it**, which reads the handoff (`/bodies/handoff`) into the stream as plain lines, never leaving the Talk. A worker's words are drawn under the worker's name, never inside hers. The handoff also arrives as a card in the Deal (the server's handoff fold), and so as one question in the Game: *"Read Worker A's handoff."*

### "Who is working on what?"

Answered by the page, in words, from what the server reads of this machine, never from the agent's memory: who is at work and on what, who came back with a handoff, who stopped without closing; then **Open Agents**, one tap. Agents is also always one tap away at the foot. The Agents place reads the record for its empty line: *your agent is here* when the host has one.

### The ten-minute switch

When the person has opened More three times in a sitting, or taken back two answers, she offers once: *"Shall we try ten minutes another way: I ask, you answer, and the rest stays out of sight?"* Declinable, and never twice a day. Taken, the frame steps away for ten minutes; then one line, *Keep it* or *Go back*. Each offer, yes and no is a `study` line (DESIGN-THE-BAR §4).

### Presence and the rest

While her turn streams, the field behind brightens slowly and settles when she stops; when everything dealt is answered it dims slowly. Reduced motion: no change.

When nothing is owed: the person's field, a little brighter. Asked, she says *"Nothing needs you. I am here when you want me."* Nothing gold. Nothing asked.

**At night, the late hours are protected** (the proposed default, not yet settled; see Open). After ten, a thing that is neither late nor holding the whole is said to wait for the morning, and asked only on *"Ask me anyway"*. After ten her last line ends *"Sleep well."* The night rule reads the record's clock.

### Keepsakes

A card answered in the Talk leaves a small made mark in its settled line, 24 px, drawn from the card's kind, with the person's own name for the card under it when they gave one. The keepsake is named in its label and explained once in her sheet; no gold. It is written to the person's record as a `keepsake` line (home-only, person-only: `{card, title, name, mark}`) through `/act`, and undone with the answer. The server serves the person's own as `hud.keepsakes`; state.js `read.keepsakes` adds the ones still in their Undo window. They sit in a row, **Keepsakes**, behind her name. Nothing of them is kept in the browser.

## 3. The desk

The same place, wider, never a dashboard: one column of the measure's width, centred; the scene larger behind it; the frame at the foot. No rail of panels, no figures beside the talk. The desk earns its width with more of the conversation in view, never with more things. The head is mounted once; a remount (a window crossing the desk breakpoint) replaces it, never adds one.

## 4. The trust layer: always visible, quiet

The person sees what is running: her agent, the workers, the context, the model, the effort, the cost. Everything below is already written by the harness; the Talk shows it and invents none of it. For this layer only, the status line and its sheet may say *token*, *session* and figures (§7).

**Depth is a knob.** The trust layer is shown at one of three depths, a personal preference kept per device and offered in her sheet in one word:

- **Plain**: her words only; the status line in words (*"about a third of the way through what I can hold today"*); the acts as one quiet line per turn (*"I read two pages and ran one step"*), the exact step still one tap away.
- **Working**, the terminal's shape: a folded row per act with its verb, count and time; the status line in figures (model and effort, context used, this sitting's cost, the week and its reset, the mode); workers with their elapsed time; thinking as a clock with any summary.
- **Full**: everything the harness gives: tokens in and out per turn, the cache, the version, the exact step and its whole result open, every event's time.

A newcomer's first sitting opens at Plain; the agent's owner opens at Working. The knob is one tap in her sheet, and remembered.

1. **The status line.** One line at the foot, under the line to speak, in dust, always there: her voice for the state, figures for the amounts. *"Fable 5.1, thinking hard · context 22% · this sitting $4.10 · your week 48%, resets Tuesday · asks before acting"*. Model and effort in words (*low · medium · high · very high · as hard as it can* become *thinking lightly … thinking as hard as it can*); context as a percentage; this sitting's cost and the week's use with its reset; the permission mode in words (*asks before acting · edits freely · plans first · acts on its own, checked*). The as-of reads from the state at every draw, is at least the person's own last act (which the served state folds in), and only moves forward. A tap opens the full sheet: every field of the harness's own status data and its as-of, the cache's warmth, the version, the session's name and where its transcript lives, and *"Show everything"*.
2. **Every act as a folded row.** In the stream, in time order, between her words: one dim row per act or per run of like acts, in plain verbs, with its time: *"Read three files · 2 s"*, *"Ran a command · 4 s"*, *"Searched for two patterns"*, *"Started a worker: draft the harvest notes"*, *"Wrote to status.md"*. A tap opens **the exact step**: the command, the file and its diff, the address fetched, and its result, in the monospace of the raw line. Nothing that changes something outside the person's own folder is ever only in the fold: that row says so in ink.
3. **Thinking, while she thinks.** A dim line where her words will come, *"Thinking · 12 s"*, the seconds counting, with the harness's thinking summaries streamed beneath it in dust when it sends them (not yet settled; see Open). When her words begin, it folds to *"thought for 12 s"*, one tap to read.
4. **Workers as rows.** Above the line to speak, one row per worker at work: its name, what it is on in a few words, its time running and what it has written so far (*"Worker A · reading the chain's handlers · 6 min · 259k"*). Tap a row for its own stream; Stop on each. Finished, the row becomes a line in the stream (§2, *When the worker comes back*). The Agents place remains the whole view.
5. **The end of a turn.** One dim line closes each turn: *"Worked for 2 min 36 s · done 3:58 PM · 2 workers still at work · 1 watch running"*. The terminal's playful verbs are left to her voice.
6. **What left this computer.** A small mark at the end of each turn, from the proxy's route lines: *"stayed here"*, or *"3 calls to the service I think with"*. A tap is DESIGN-DOCK §2.6's *"Where did that go?"*, unchanged. The mark shows only where the proxy records where words went; when the proxy is not in the path, the mark says so and stays until answered.
7. **Said plainly when it happens**, as her lines. Compaction: *"I folded our earlier talk into a summary to make room. I kept the plan, the open asks and the last three files."*, with the summary one tap away. Context near its end: *"We are near the edge of what I can hold. Shall I fold the earlier talk now, or start fresh?"* A usage window spent: *"Your week's use is spent until Tuesday at five. I will carry on then, unless you stop me."* An update waiting: in the sheet, never in the stream.
8. **Control, always.** **Stop** shows whenever anything runs: her turn, any worker, or voice mode. A typed or spoken *stop* ends the turn and the loop, and is never sent. **Undo** sits beside every row that wrote something, back to the state before the turn (the harness's checkpoint); what Undo cannot restore (a command's side effects, a worker's edits outside the person's own folder) says so in the row. The permission mode changes from the status line, in words, by tap or by word, at any time. A message typed while she works queues and shows as queued.

### Aliveness

1. **Words stream** as she writes them; nothing waits for a whole reply.
2. **The scene stirs on her turn**: the field behind brightens while she thinks and works, and settles when she stops.
3. **Time passing is shown**: the thinking clock, the act rows' seconds, the workers' running time, the end line's clock time.
4. **Her name** heads the stream once; **her voice**, when the person turns it on, speaks her words and never the rows.

## 5. Permissions are the harness's own

The Talk invents no permission layer. The mode is the harness's, with the same choices and names as the terminal and the desktop app; it is chosen in the Talk in words and shown in the status line. What the harness allows without asking, the Talk allows. A permission the harness asks reads first in plain words (*"May I save today's notes to your folder?"*), with the exact step (*"Write status.md, 14 lines"*) one tap below, never hidden and never first. It is answered by a word or a tap, with DESIGN-DOCK §2.4's three answers, *"Yes, for this kind"*, and a note. An act that leaves this computer is asked every time. The levels are the same on all three surfaces, because it is one working service.

## 6. The chief of staff's rules

The agent behind the Talk is the person's chief of staff; its character lives in [the chief-of-staff skill](../skills/the-chief-of-staff/SKILL.md). The surface holds it to these rules:

- **Unasked, only what is owed now, once**: one line at the end of a reply (§2, *Plain work*).
- **A handoff is folded into one question**: what came back, what it asks of the person, the options. Never the worker's transcript.
- **A worker is named by its own name and its task**, never by a process or a session.
- **No figures unless asked**, outside the trust layer. A count is said in words ("seven things"), a cost in time; percentages and charts wait for the question that wants them.
- **The record answers before the agent does, and the page answers only what it knows, once**: "What needs me?" (a few plain forms), "who is working on what", a worker by sentence when no agent answers, *ready* and *next*. Everything else ("what is blocked?", "what should I do?") goes to the agent with no line from the page. The host's five first-contact answers are painted once, as the host's; the page's own lines are never drawn a second time from the host's echo.
- **Every line sent carries the page's context** in the `/agent/say` body: `page: {line, question, options, local_answers, first, recommendation, settled}`. `local_answers` is what the page said here (`{at, you, said, card?, option?, how?}`), the last eight; `first` is the owed list's first card; `recommendation` is the question's suggested choice; `settled` is what the person's own words settled (card and option). The settled line is the page's; she never repeats it at the head of her reply.

## 7. The voice

Layered: **her words** (first person, warm, plain, short), **the record's facts inside them** (the card's own question, its why, its by-when in words, its consequence), and **nothing in schema words** (no event, holon, float, anchor, settle, engine, token, process). No contraction but the opener; no exclamation; no flattery.

**The apparatus's words stay off the person's screen.** None of *Cell, deck, desk, record, Deal, Terminal view, Command line, models, Layouts, token, session, fixture* appears in what the Talk, her sheet or More say in their own words. A card's own text is the record's, and stays. The places behind More keep their proper names. The status line and its sheet are the one exception for *token*, *session* and figures (§4).

**The words.** A question keeps its question mark. The exact step shows `ask.step` only, one plain sentence, never a path or a file's front matter; `ask.raw` is never shown. "Confirm", never "Ratify". *"Cell Two's steward is the witness."* *"Your week's use"* for the week's allowance. The first card says its day once.

**No glyph that explains nothing.** No bare ring before a turn or on an ask; the field marks her turn only while she works; the keepsake beside a settled line is named in its label and explained in her sheet.

**One gold**: the owed question's hairline only.

**One name in every head**: her name from the agents file, on the Talk, its line to speak and voice mode's stage.

Every shown string lives in `strings.json` under `talk_place.*`.

## 8. Her sheet, More and Settings

**Her sheet** opens from her name, one tap. It holds who she is; where words go, in the host's one sentence (`dock.first.words`, or `dock.first.words_named` when the person's vendors file names the service), the same sentence the voice sheet uses; how to stop; a person to reach, with *Write to them* (`brought_by: {name|house, reach}` on `hud.person` or the person's actor entry; else *"the one who gave you this"*); the keepsakes; the depth of the trust layer (§4); and one choice, read aloud or not. At most eight controls, and Close. A sheet's head stays at its top edge, and what scrolls under it fades.

**More** holds the places by their proper names, the way to the desktop app, and **Settings**: ten controls with its Close.

**Settings** holds everything else: how she asks (Fewer questions), the voice's finer choices (among them *Keep my voice here*, which turns the browser's own listener off), the phone, and *"I can count your judgments…"* beside the study. The plain transcript and the command line live only in the Agents place's own switch.

## 9. Voice

A tap is the first way to answer, and a line typed in the conversation goes to her, which reads the same record. Voice is the line to speak, spoken: where the server has a speech model, the dock's own voice path fills the line.

The microphone sits beside Send wherever the device can listen (a secure page, this computer's own address included), and the Voice mode switch sits in the head beside her name. *"May I listen?"* is said once, at the first hold; when the listener in use is the browser's own, it says in one line that it may send the person's voice to its maker. After the first yes it is never said again. The listener is found before the sheet is drawn.

## 10. Better than the terminal and the desktop app, and no worse anywhere

**Better, where it can be.** Several sessions as one place: Agents shows every body and worker on this machine with what it is on, its model, its time, its cost and its asks. The record of what was decided: a commitment made in talk is a line in the record, not lost in a transcript. The phone, with the proxy kept (DESIGN-DOCK §4). The voice. The trust mark on every turn: what left the computer, which neither shows. Plain words first and the exact step beneath, where the terminal gives only the exact step and the desktop app hides it.

**No worse anywhere.** Every terminal element, and where it lives in the Talk:

| Terminal | In the Talk |
|---|---|
| Prompt line, streamed words | the stream |
| Tool row, grouped line, `⎿` result | the act row and its exact step (§4.2) |
| Ctrl+O transcript viewer | the exact step per row; *"Show everything"* in the status sheet |
| Spinner verb, clock, ↓ tokens | the thinking line (§4.3); the sitting's figures in the status line |
| `Thinking…` / thinking summaries | §4.3 |
| Worker panel, `/tasks`, "Agent … finished" | worker rows (§4.4); Agents |
| Monitor events, "N monitors still running" | a watch's line in the stream; the end line (§4.5) |
| "Sautéed for … · done …" | the end line (§4.5) |
| Status line (model, context, windows, cost) | the status line (§4.1) |
| Mode badge, Shift+Tab | the mode in words, changed from the status line (§4.8) |
| Permission prompt (Yes · do not ask again · switch to auto · No, comment) | the permission ask (§5), with *"Yes, for this kind"* and a note |
| Esc · Ctrl+X Ctrl+K | Stop, per turn and per worker |
| `/rewind`, checkpoints | Undo (§4.8) |
| Compaction notice, context warning | said plainly (§4.7) |
| Recap on return | the return line (§2) |
| Usage-limit wait | said plainly (§4.7) |
| Queued messages | shown queued (§4.8) |
| `/usage`, `/context`, `/model`, `/effort` | the status sheet; asking her in words |
| Ctrl+T to-do list | her plan, folded under her turn when she has one |
| Update notice, tips | the status sheet |
| Agent view | Agents |

## 11. The surface studies itself

One `study` line per measure per sitting, to the person's own record on this machine: `first_question_ms` (from the page's start to the first question painted), `first_answer_ms`, `answered`, `first_line_ms`, `intent_next` · `intent_who` · `intent_worker`, `worker_started`, `switch_offered` · `switch_taken` · `switch_declined` · `switch_kept` · `switch_returned`. The view's name is `talk`; the shell's own measures (first act, reversals, switches between places) count it as a place.

## 12. The bar

The sheet of DESIGN-THE-BAR §5, on a phone first, at night, with regular and large type. Three of its lines judge this place above the rest: **5** (one breath: the line), **12** (the primary act is the biggest, nearest thing), **25** (after one exchange, did the person speak with someone). And the one-breath test of §1. Beside them:

1. The first screen is a greeting and nothing else: no card, count or question.
2. In the first five minutes of plain work, nothing from the Game appears unless asked, or owed now, once.
3. Every act she takes is a row in the stream before the turn ends; none is missing against the harness's transcript.
4. Any row's exact step is one tap away and matches the transcript word for word.
5. The status line is always visible, names model and effort in words, and its figures match the harness's status data at that moment.
6. While she thinks, time is visibly passing within one second of the turn starting.
7. A running worker is visible with its task and time, and can be stopped, without leaving the Talk.
8. Stop ends a turn within a tenth of a second; Undo restores a file she wrote.
9. Compaction, context near its end and a spent window are each said in one plain sentence when they happen.
10. A person who lives in the terminal, given the Talk for an hour, says they could see everything they see there; a newcomer, the same hour, met no file name they did not tap for.

## 13. Open

- Whether the Talk is the first place for every Player+, or a choice at the door with the Deal as the other.
- Whether the night rule protects the hours after ten by default, or only when the person asks.
- Which other ways belong in the ten-minute switch beside questions only: voice only, the paper Deal, the Map.
- Whether the vendor's app, as the way back, is one fixed address behind More or a choice made at the door.
- Whether nine seconds of quiet is the right wait before a changed record replaces the question on screen.
- Whether thinking summaries stream beneath the thinking line, or stay one tap away.
- Whether cost is shown in dollars at list price, as the week's share, or both.
- Whether *the Talk* stays the name of a place that is now simply working with your agent.

## 14. Not yet built

- Undo for what she wrote: the host offers no checkpoint to return to.
- A typed message shown as queued while she works.
- The person's name and who brought them: read only when the server serves `hud.person`, which it does not yet do.
- Speech out.
- The shape-when-needed picture inside the conversation; the Deal's full card, behind More, serves instead.
- Directories, and other harnesses over the agent protocol.
- The night rule reads the record's clock, not the person's own sleep.
