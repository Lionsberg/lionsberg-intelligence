---
title: The Room
description: The design of the Room layout of the HUD, the one surface where people and their agents work together; on the person's face it is a space. Current best understanding; items under Open and Not yet built are undecided.
---

# The Room

*On the person's face a room is a **space**. In the record, the build, the files and the routes it stays `room`, as `body` stays for a worker. This page says Room where it speaks of the build, and every string it shows for the face says space.*

*The Room layout of the HUD is the one surface in which a group of Living Intelligences and their agents works together. It is the simple, elegant successor to the message, task and field-project products, all in one, and all of it one design, because a group should never have to copy its work from one tool to another. This page sets it out scene by scene.*

This page binds over [DESIGN.md](DESIGN.md) §3.3 (Room) and §4.6 (the Play by Play) wherever they differ. It reads from [engine/SCHEMA.md](../engine/SCHEMA.md), [engine/STATE.md](../engine/STATE.md) and [engine/types.json](../engine/types.json).

---

## 1. The one idea

**One table, three inks: everything the room says, keeps and agrees lies on one table in front of everyone, and the ink tells you which it is. Said lines pass in dust, kept lines stay in paper, agreed lines are recorded in full ink with their signature, and every card, commitment, turn and date on the table is the same record seen from where you sit, with your agent as the one who lifts your words into it.**

The three inks are the speech law made visible. Much that is said is not recorded, and should not be, because a record of everything would make every word guarded. *Said* is the default and evaporates in a rolling window on the machine; *kept* is marked by someone and stays on the machine; *recorded* is what enters the Record (a settlement, a decision, a card changed), promoted by someone other than the one who proposed it. The law needs no sentence on the screen. It is the typography itself: a person sees at a glance which lines will pass, which will stay, and which are the room's word. Typography leads.

**What it replaces, each as a view of the one record, in one surface:**

| The product class | What it gave a group | Where it lives in the Room | The record under it |
|---|---|---|---|
| The message product (talk) | channels, threads, mentions, presence | **The Talk**: the current part's lines in three inks; threads open under the line they belong to; whispers between agents, readable by each person served | `say` (said and kept stay off the record, on the machine); `thread`; `settle` |
| The task product (work) | tasks, boards, assignees, due dates | **The Table**: cards born from a line in one gesture, shown in the one card face | `card` · `claim` · `done` · `release` |
| The workflow product (whose turn) | status columns, approvals, hand-offs | **Your move**: the Table sorted by ball-in-court; the holder's role on every card; a yes waiting shown as a yes waiting | `hand` · `request` · `offer` · `answer` · `decide` · `ratify` |
| The schedule product (when) | calendars, timelines, reminders | **By when**, on every commitment and card; the room's hour counted in parts; the slice of the Chain this room touches | `commit` (by, size, witness) · the engine's `schedule` and `buffers` |
| The field-project product (requests, submittals, the daily record) | formal requests with answers due, a log of the site | requests and offers with by-when and witness; sightings; the Play by Play as the room's daily record | `request` · `answer` · `sight` · `witness` |

**The agent is the operator.** No one in the Room fills a form. A person speaks or types as they would to a friend; their own agent lifts what they meant into a typed line (a request, an offer, a commitment, a card) and shows it as a proposal; the person's yes records it. Each person's words reach the record through their own agent. The surface is the work, never a place to talk about it.

**The award bar, for the Room:**

| Principle | The Room's answer |
|---|---|
| 1. One continuous world | The Room is a place in the Map: entering is the camera moving into the room's field; leaving returns to the field. The Talk, the Table and the Page are one surface, never three apps. |
| 2. Every advance is the wearer's act | Nothing in the Room scrolls or advances on its own. New lines wait below a quiet "three new lines" when she has scrolled up. |
| 3. Real depth | Near: the Talk of this part. Middle: the Table and the Page of this room. Far: the cells and homes this room's record reaches after. |
| 4. Typography leads | The three inks; the commitment's five slots; roles in small capitals. |
| 5. Sound, opt-in | None from the HUD. The call's own voice belongs to the call. |
| 6. The loader is a scene | The room's page is shown from the last line held, at 60% ink, while the live record arrives. |
| 7. One micro-reward | Press and hold any recorded line: its axis shows, the chain from that line to the agent that lifted it, the Living Intelligence who answers for it, and the card or quest it serves. |
| 8. 60 fps on a phone | The Room is text and hairlines; it holds on a mid-range phone. |
| 9. Content is the hero | Hide every mark and the Page still tells a newcomer what this room agreed and who carries what. |
| 10. One idea | One table, three inks. |

---

## 2. A room's hour, scene by scene

*The example: a cell planning its first week. Present: the keeper, two members, a guest from a second house, and each person's agent. Roles throughout; a name appears nowhere on the face. A person's needs show under a role (a member, the keeper, a guest), never under a name, so that no one is exposed by what they need.*

### 2.1 Before: the room staged

*Two days before.* The keeper (or the keeper's agent, on the keeper's word) stages the room: its **purpose** in one line, the **parts** of the hour (counted, each with a question and minutes), **links** to what should be read, and the **posture** proposed.

| When | What each wearer sees | What they do |
|---|---|---|
| The day before | In each member's own Deal, one card from this room, eyebrow **FOR THE SPACE ON MONDAY**: "Here's the deal." then "Two things before the space meets. About twelve minutes." | Reads the cards one at a time, in her own Deal, at her own pace. |
| Card one | "Read the draft plan before Monday? About eight minutes." Options: **Read it now** · **I will read it Sunday** · **Skip it**. Choosing *Sunday* writes nothing outward; her agent remembers to deal it again. | One tap. |
| Card two | A commitment due to this room: "You said you would bring the costs by Monday. Still on?" **Yes, on track** · **I need more time** · **Pass it on**. *I need more time* opens one line to say why and a new by-when; her agent drafts it, she agrees it. | One tap, perhaps one line. |
| The room's page | Before the hour the room's Page is readable by its members: purpose, parts, links. Anyone may comment on the agenda; only the keeper changes it. | May comment. |

**What is dealt here** is the room's Deal for each wearer (in the record, `deal(items, actor, minutes, room)`): sized to her available time and to who is coming, at most three cards, the cost said first.

### 2.2 The door: presence and posture

*The first thirty seconds. This is the scene a grandmother and a ten-year-old must pass alone.*

| Time | What she sees | What she does |
|---|---|---|
| 0–1 s | The room's page at 60% ink from the last line held, its name in small capitals, its purpose beneath in Cormorant italic: *"To choose what we do in our first week."* | Nothing. |
| 1–4 s | One quiet line beneath: **"Four people are here, and three agents."** Below it the presence row (§4.1): each person by role, each agent as a small ring joined to its person's mark. | Sees who is here before anything is asked. |
| 4–10 s | The posture card, the only thing asked at the door: **"This space is set to Names hidden. Ideas may leave this space. Names stay in it."** **Agree and enter** · **Ask the keeper**. Tapping the posture's name explains it in one line. | Taps *Agree and enter*. Her agreement is a line in the room's record (a `posture` event, §8.5). |
| 10–15 s | Her agent asks, in its own line, never by itself: **"Your agent asks to come in with you."** **Let it in** · **Not today**. An agent exists in the room only after its present person affirms it. | Taps *Let it in*. Her ring joins her mark in the row. |
| 15–30 s | The room opens: the part strip at the top ("Part one of four · Where we are · eight minutes"), the Talk filling the screen, the line to offer at the foot with a large microphone. | Speaks, types, or simply listens. |

**Identity at the door.** She arrives by a link her own agent sent; who she is comes from her own key, never typed and never defaulted to anyone else. A person can always enter without an agent: a phone and a link make a full participant.

**The first two minutes are the agents'**: while people greet each other in the call, each agent reads the Page and may offer one line. Those lines wait in the offered tray (§2.3); none is the room's word.

### 2.3 The work

**The Talk, in three inks.** Every line in the current part appears in the Talk as it is offered, newest at the foot (a conversation reads downward):

- **Said**: dust, body size, no mark. The default for every line. It passes: when the rolling window ends it leaves the screen and the machine. A said line can be deleted by the one who said it.
- **Kept**: paper, with a small open star at its left. Anyone presses **Keep** on any line; it then stays on that person's own machine under the room's posture. Keeping is private to the one who keeps and writes nothing to the record.
- **Agreed**: full ink, an eyebrow in small capitals naming what it is (AGREED · DECIDED · CARD · COMMITMENT · ASKED · OFFERED), and the verified mark ✓ at the right. It is in the room's record, signed by the person who agreed it.

**How a line becomes the room's word.** Any person presses **Agree** on a line someone else offered. The consequence is said once in a line beneath ("This goes into the space's record.") with five seconds of **Undo**. A line is agreed by a person who did not propose it; a person's own commitment is the exception, because only she can commit herself (`commit` is human-only).

**The motion of agreeing.** The line's ink deepens from dust to paper to full ink over 480 ms, the way wet ink dries, and its eyebrow sets in beside it. On wide screens the line then also appears at the top of the Play by Play on the Page. The motion means one thing: this line became the room's word. Nothing glows, blooms or lights; the change is in the ink.

**Threads open under the line they belong to.** Press **Reply** on any line: a thread opens beneath it, indented 16 px with a hairline at its left, inline in the Talk. A thread's own lines follow the same three inks. A thread can be agreed closed with one line, by a person other than the one who opened it. A collapsed thread shows its count and its last agreed line ("4 replies · agreed: Monday is the first test").

**A card born from a line, in one gesture.** Press and drag a line to the right (or press **Make it a card**): a card rises from the line onto the Table with the line as its title. The wearer's agent proposes the rest in the card's slots (who holds it, by when, minutes, which stream); each slot shows the agent's guess in italic until a person sets it. The card is born when a person agrees it. The line in the Talk keeps a small CARD eyebrow linking to the card (a `card` with `anchored_to` the line).

**A request, an offer, a commitment, spoken and recorded.** People speak naturally ("Could you have the costs by Thursday?"). The speaker's agent hears its own person, and only its own person, and offers the shape:

```
ASKED                                   from the keeper · to a member
Bring the costs for the first week
WHO   a member        BY WHEN   Thursday        SIZE   about an hour
WITNESS   the keeper
                                  Yes, I commit  ·  Not yet  ·  Pass it on
```

The **commitment card** carries five slots, always in this order: **who · what · by when · size · witness**. Only the person named under WHO can tap **Yes, I commit**; her agent cannot, because an agent never ticks a human's box (`commit` is human-only). Until she does, it sits on the Table as ASKED, with the ball in her court. An empty slot shows an honest blank ("by when: not set"), never a guess.

**Ball-in-court, moving in front of everyone.** Every card on the Table shows its holder's role in a chip at the card's foot: "with the keeper", "with a member", "with you". When a card passes (a `hand`, a `claim`, an answer), the chip changes and the card moves within the Table's **Your move** sort over 240 ms; in the presence row, the receiving person's mark gains a small count of cards now with them. The whole room sees whose move it is without asking. The record does the workflow product's job.

**The Play by Play is the room's own memory.** It lives on the Page and holds only agreed lines, **newest first**, each with its time, its part, its eyebrow and the role that agreed it. Said and kept lines never enter it. Agent lines never enter it until a person agrees them. This binds over DESIGN.md §4.6's "newest at the foot", which applies only to the Talk.

**What each agent proposes is shown as a proposal.** An agent's offered line is set in italic, carries its ring and its owner ("offered by the keeper's agent"), and stays in the **offered tray** above the line to offer until a person agrees it or sets it aside (**Not this**). An agent's line whose reason came from text it read rather than from its person carries a second small mark and the words "from something it read" (`reason: untrusted` is a proposal only).

**The human's yes is the only thing that records.** No timer, quorum of agents, or silence records a line. If no person agrees an offered line, it stays offered and then passes with the said lines when the part ends.

**A made thing on the table.** A page, a drawing, a sheet or a file can be laid on the Table as a card of kind *draft* (drag it in, or ask your agent to bring it). Its face shows its title, its kind and who brought it; **Open** hands it to the device's own app for that kind. Comments on it are threads; changes to another person's text are offered as comments, never made in place.

### 2.4 The close

| When | What the room sees |
|---|---|
| Ten minutes before the end | The part strip turns to the closing part on its own minute, as the keeper set it, and one line appears in the Talk: **"Ten minutes left. What will each of us commit to before we close?"** The Table shows every ASKED card still waiting on a yes, sorted by whose it is. |
| Commitments spoken | Each person says hers; her agent offers the five slots; she taps **Yes, I commit**. The room watches the commitments arrive on the Table, each with its witness. |
| The cards dealt at the end | Each wearer receives her closing Deal, privately, in her own chip: **"Here's the deal."** then "From this space: two commitments and one card. About a minute to confirm." She confirms each, or changes a by-when. The standing last question of every Deal is held open; until it is settled, its default wording closes this Deal too: **What did we miss that matters to you most?** |
| What leaves the room | The publish sheet, for the group together: **"Before the space closes: this is what leaves it, with names hidden."** It lists what will cross (the agreed lines, the cards and commitments, the Page) and to whom (each member's home, the cell). **Publish** · **Keep it here**. Publishing is a recorded act by a person (`publish`, human-only). |
| Posture re-confirmed | Under a posture that hides names, the publish sheet shows the record as it will leave, with every name elided, each line still proving its content, signatures removed and the set attested by the exporter. |
| The curing days | One line beneath: **"Anyone may change their mind about what leaves this space until Thursday."** For those days a person may narrow what they offered. The room sets the length; three days is the proposed default. |
| The room goes still | **"That is the space for today."** The Talk's said lines pass. The Page and the Table remain, readable by the members. |

### 2.5 After: what each wearer's home received

No one processes the call for an hour afterwards; the record was made during the hour.

- **Her commitments made here**, each with its home in the room and an alias in her own home, so her Deal and her two stacks (**Your commitments** · **Committed to you**) carry them from tomorrow (every item carries `holon`; aliases).
- **Cards she holds** from this room, in her Queue, with "from the space on Monday" in the eyebrow.
- **What others committed to her** in this room, in **Committed to you**.
- **What she kept**, on her own machine only, under the room's posture.
- **The room's record**, published to its members if the room chose so, in the Record view under the room's holon.
- **Her agent's own account** of what it offered and whispered in the room, readable by her alone (§4.3).
- **The Turn** picks all of this up at the week's end, in its four lines (proposed, not yet settled): **Kept · The gap, and what it taught · Next · The Flame passed**.

---

## 3. Attention in a room

**The flow is sized to the humans.**

- **The room's pace is a human's.** An agent may offer; it never sets the pace. The offered tray shows **at most three** offered lines at once; more wait behind a quiet count ("four more offered"). Each agent has a live-write budget per part, set by the room's posture.
- **One line first, the rest a step away.** An agent's offered line is one sentence; its reasons and sources are in its fold. Long agent text is refused by the surface and returned to the agent to shorten (proposed, not yet settled).
- **Each person enters at her own cycle speed.** A member who steps away returns to one line at the top of the Talk: "While you were away: one decision, and one card is now with you." Then the Talk where she left it.

**The interruption rule.** Only a person's own agent may interrupt her, and only through her private chip.

- A card's **question comes before its context**: the question is legible alone, the context is one tap away.
- **Few and spaced:** about four in an hour, none closer than fifteen minutes, three cards at most at once; she answers one and defers the rest; a deferred card may return once.
- What may break the spacing: a yes only she can give that the whole room is waiting on, said in its eyebrow ("The room is waiting on this").

**What never interrupts:** a said line; another person's thread; agent-to-agent whispers; another person's commitment; a line agreed elsewhere in the room; a card moving between others; the Play by Play; an agent's own status. None of these makes a sound, a badge, a bounce or a count in red. A person who wants to speak now signals **"I need to say this now"**, which reaches the room at once and waits on no agent.

---

## 4. Agents in the Room

### 4.1 Distinct at a glance, by role, and whose each is

- **A person's mark:** a paper circle holding the role's first letter in small capitals (K for the keeper, M for a member, G for a guest, and "you" for herself), with the role beneath in dust. Under Open posture a person may show the name she chose, in the presence fold only.
- **An agent's mark:** a smaller open ring joined to its person's mark by a hairline. It is never free-standing. Its label is always possessive: **your agent** · **the keeper's agent** · **a member's agent**. To its wearer it is "your agent" until she names it; then it carries her name for it, for her alone. Agents are named by whose they are, never by a bare display name.
- **Their lines differ in register:** a person's lines in EB Garamond roman; an agent's in EB Garamond italic with its ring. A line by a facilitating agent that serves the room, rather than a person, carries the room's mark instead of a person's.
- **States, in words beside the mark:** a person is *here* · *speaking* · *away* · *on a break* · *wants to speak*. An agent is *listening* · *keeping the Play by Play* · *offering*. An agent whose person has left is shown leaving with them; an agent writes only while its person is present.

### 4.2 Admission

An agent enters only after its present person affirms it at the door (§2.2), and the affirmation is a line in the room's record (an `affirm` event, §8.5). A person can dismiss her agent from the room at any moment with one tap on its ring (**Ask it to leave**). A guest's agent from a second house is affirmed by its own person, never by the keeper.

### 4.3 Whispers

Agents may whisper to one agent, to several, or to all agents in the room. Whispers are said-kind speech: they pass in the rolling window and never enter the record. **Every whisper is readable by the person each agent serves.** Tap your agent's ring: a sheet opens, **"Everything your agent said here, to anyone, is yours to read."** It lists what your agent offered, what it whispered and to whom (by role), and what was whispered to it. No whisper reaches a person who is neither its sender's principal nor its receiver's.

### 4.4 Collisions prevented

- **One note-taker per moment.** The Play by Play has one keeper at a time, named in the presence row ("keeping the Play by Play: the keeper's agent"). It is a Role held by a person, who may delegate it to her agent: Living Intelligence holds the Roles, and Artificial Intelligence serves Living Intelligence. The role passes by a visible hand-off; two agents can never hold it at once.
- **Comment, never edit.** No agent changes another's line or another person's text. It offers a comment under it. A person's own correction is a new line that supersedes, shown beside the original (`supersede`).
- **A stale change fails.** A change to a shared page names the line it changes and the version it saw; if that line changed meanwhile, the change is refused and returned.
- **The same line twice is one line.** A repeated offer within thirty seconds folds into the first.

---

## 5. The Room across houses

A room is a holon, and like every holon it has its own record. Two houses in one room work over one record, each from its own home.

- **One home, many aliases.** The room's record has one home, a repository the keeper chooses. Each house that joins adds it beside its own cells and pulls it (joining is being given access and adding the repository). Every house's HUD folds the same lines and may draw them differently; the record is the agreement.
- **Each actor writes its own file** in the room's record, signed with its own key, which lives in its own house; a person's commitment is signed by the person (one append-only file per actor; events signed by the actor).
- **What crosses each membrane after:**

| From | To | What crosses | By whose act |
|---|---|---|---|
| A house | The room | Only what a member brings: a card's face, a page laid on the table, a line she offers | Her own act in the room |
| The room | Each member's home | Her own commitments and cards (as aliases), what was committed to her, the room's record if published to members | The fold, on her machine |
| The room | A cell or the commons | The agreed record, names elided per posture | A person's **Publish** in the publish sheet |
| A member's home | Anywhere | Nothing of the room's beyond what the room published | Never by an agent alone |

- **What never crosses:** said lines, kept lines, whispers, a member's private Deal, her agent's account, another house's inner record. A line is sent only to those its audience allows; a line a viewer may not see answers exactly as a missing one.
- **Houses are never named on the face.** A guest from a second house is "a guest"; her house appears as "a second house" in the presence fold only.

---

## 6. Composition

### 6.1 The layouts

**Desk (1024 px and up): three columns over one table.**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ THE FIRST WEEK · Names hidden · Part two of four · The budget · 12 min left      │
│ (K)○  (M)○  (M)  (G)○  (you)○        keeping the Play by Play: the keeper's agent│
├──────────────────┬──────────────────────────────────────┬────────────────────────┤
│ THE PAGE         │ THE TALK · The budget                │ THE TABLE              │
│ Purpose          │ said lines in dust …                 │ Your move · 2          │
│ Links · 3        │ kept lines in paper ☆ …              │  [card] with you       │
│ Big ideas · 4    │ AGREED  Monday is the first test ✓   │  [card] with you       │
│ Play by Play     │   └ 3 replies                        │ Waiting on others · 3  │
│  (newest first,  │ offered by your agent (italic) …     │ Commitments made here  │
│   agreed only)   │ ── offered tray (at most three) ──   │ Yeses waiting · 2      │
│                  │ [ the line to offer ……… ]  (mic)     │ The whole waits on · 1 │
└──────────────────┴──────────────────────────────────────┴────────────────────────┘
```

- **The Page** (left, 20 rem): the room's made document, written by agreement: purpose · links · **Big ideas** (numbered, one line each, the section people actually read) · the Play by Play, newest first. The Page is what remains when the room goes still; it is the minutes, made during the work.
- **The Talk** (centre, a reading measure of 34 rem): the current part. Earlier parts fold to one line each above it ("Part one · Where we are · three agreed"), open on tap.
- **The Table** (right, 22 rem): **Your move** first (cards and asks with the viewer), then **Waiting on others**, **Commitments made here**, **Yeses waiting on a person**, and the room's slice of the Chain (**The whole is waiting on**). Every card in the one card face ([DESIGN.md](DESIGN.md) §4).

**Tablet (600–1023 px): two columns.** The Talk at left; at right one panel that switches between **Table** and **Page** with a segmented control, the Table by default.

**Phone (0–599 px): the Talk is home.** A slim top strip (the space's name · posture · part strip with minutes left); the presence row beneath, scrolling never sideways (it wraps to a count, "and three more"); the Talk filling the screen; the offered tray and the line to offer at the foot, with the microphone the largest target on screen (56 px). Above the line, two tabs: **Page** and **Table · 2** (the count is your move). Each opens as a sheet from the bottom over the Talk, and a swipe down returns. Her private chip **Your deal · 2** sits at the top right, opening as a sheet only she sees.

### 6.2 Hierarchy

1. What needs **your** yes or **your** move (Table, Your move; the private chip).
2. The **current part**'s question and the Talk.
3. What the room has **agreed** (the full-ink lines; the Play by Play).
4. Who is **here** and what they are doing.
5. Everything else, one tap away.

### 6.3 The primary action in each state

| State | The one primary action |
|---|---|
| Before | **Read before the space meets** (her room Deal) |
| The door | **Agree and enter** |
| The work | **The line to offer**: speak or type |
| A yes is hers | **Yes, I commit** / **Agree**, in the card that asks |
| The close | **Confirm your commitments** (her closing Deal) |
| After | **What you carry from this space** (opens her home's new items) |

### 6.4 The live line's motion

- A said line arrives at the foot, rising 8 px and fading in over 240 ms. It passes by fading to nothing over 2 s when the window ends; under reduced motion it simply goes.
- Agreeing deepens a line's ink over 480 ms (settle easing) and sets its eyebrow; on wide screens a copy rises into the top of the Play by Play over the same 480 ms.
- A card born from a line rises from the line onto the Table (a single 480 ms move, the line's text becoming the card's title).
- A card changing hands slides within the Table over 240 ms; the holder chip's words change at its end.
- Nothing moves at rest. Nothing pulses, glows, blooms, shimmers or bounces. No dot, halo or ember marks the live line; the ink and the position carry it.
- If she has scrolled up, nothing jumps; a quiet **"Three new lines below ↓"** appears. A screen reader hears agreed lines in a polite live region; said lines are not announced unless she asks.

### 6.5 States

- **Empty (the room just opened):** "Nothing agreed yet. Speak or type the first line." The Page shows purpose and parts.
- **Loading:** the room's page from the last line held, at 60% ink, with "reading…" in the top strip. Never a spinner or a blank.
- **Error:** "The space's record could not be reached. What you offer is kept on this device until it returns." Everything held is shown.
- **Offline:** offered lines queue on the device, each marked "waiting to send", sent in order on return. Her yeses wait too, said plainly: "Your yes will be recorded when the space returns." A send shows its state and never sends twice.
- **A house unreachable:** its people stay in the presence row with "last heard 9:42"; what it wrote before is shown.
- **Paper:** the Page printed: purpose, parts, Big ideas, the Play by Play in time order, the commitments as a ruled table (who · what · by when · size · witness · initials), names elided per posture. A group without screens can run on this sheet; a witnessed sheet beats the typed copy (the paper floor).
- **Large type:** one column on every width; the Talk and the Table alternate by the two tabs; the commitment card's five slots stack one per line.
- **Shown to everyone:** when her screen is shared, she taps **Show to everyone here** and the private chip, her agent's account and her kept lines fold away until she ends it.

### 6.6 What the Room never shows

A transcript or any recording of the call · a typing indicator · read receipts · unread counts or red badges · channels (the room has parts and threads, and that is all) · emoji reactions (agreement and difference are lines: "I agree" · "I see it differently") · a count of what any agent produced · a ranking, score or comparison of people · a person's presence outside this room · a name the posture hides · a house's name · an agent line in the Play by Play that no person agreed · a member's private Deal, her kept lines or her agent's whispers on anyone else's screen · a line outside the viewer's audience.

---

## 7. Voice

The brand's voice in the Room: a person speaking plainly to a group of people, warm, with flow. Never "not X but Y" or "not X, only Y"; never an exclamation; never flattery or a pat on the head; never "helper"; the word is **commitment**; no contractions in any string except the opener **"Here's the deal."** The chrome speaks in the second person; an agent speaks in the first only inside its own offered line. Times in words ("by Thursday", "twelve minutes left"). Every string lives in [strings.json](strings.json) under `room.*`, `talk.*`, `table.*` and `play.*`.

Open: whether an agent says "I" at all.

**Twenty strings:**

1. Here's the deal.
2. Two things before the space meets. About twelve minutes.
3. Four people are here, and three agents.
4. This space is set to Names hidden. Ideas may leave this space. Names stay in it.
5. Agree and enter · Ask the keeper
6. Your agent asks to come in with you. · Let it in · Not today
7. Part two of four · The budget · Twelve minutes left
8. Keep · Agree · Reply · Make it a card
9. This goes into the space's record.
10. Offered by the keeper's agent. It is in the record once a person agrees it.
11. Who will carry this, and by when?
12. You will bring the costs to the space by Thursday. About an hour. The keeper will witness it. · Yes, I commit · Not yet · Pass it on
13. It is your move.
14. Two yeses are waiting on a person.
15. While you were away: one decision, and one card is now with you.
16. Ten minutes left. What will each of us commit to before we close?
17. Before the space closes: this is what leaves it, with names hidden. · Publish · Keep it here
18. Anyone may change their mind about what leaves this space until Thursday.
19. Everything your agent said here, to anyone, is yours to read.
20. The space's record could not be reached. What you offer is kept on this device until it returns.

**Words the Room never puts on a wearer's screen:** settle (say *agree*), event, line id, holon (say the space's name), audience (say *who may see*), elide (say *names hidden*), posture on its own (say the posture's name), agent handles, house names, transcript, and the word the kit retired for commitment.

---

## 8. The build

*[DESIGN.md](DESIGN.md) §8 holds the ground rules: static files, no build step, every string from [strings.json](strings.json), every value from [tokens.css](tokens.css), fixtures first. This section says what is particular to the Room.*

### 8.1 Files

| File | What it holds |
|---|---|
| [play.js](play.js) | The Page: purpose, links, Big ideas, and the Play by Play (agreed lines only, newest first, each with time, part, eyebrow, role, ✓). The offered tray, presence and yeses live in the files below. It carries the print section. |
| [room.js](room.js) | The Room layout's frame: the phases (before · door · work · close · after), the top strip and part strip, the presence row and its fold, the posture card, agent affirmation, the curing line, **Show to everyone here**, the three-column / two-column / phone arrangement; mounts `talk.js`, `table.js` and `play.js` with the shared context. |
| [talk.js](talk.js) | The Talk: said, kept and agreed inks; threads inline; the line to offer (typed, and device dictation where the device keeps it on the device); Keep, Agree, Reply, Make it a card; the offered tray (at most three, the count behind); the five-second Undo; the offline queue and once-only send; "three new lines below". |
| [table.js](table.js) | The Table: Your move · Waiting on others · Commitments made here (the five-slot commitment card) · Yeses waiting on a person · The whole is waiting on; holder chips; the card-from-line arrival; a made thing laid on the table with **Open**. Uses [card.js](card.js) for every face. |
| [room.css](room.css) | The three inks as tokens it reads from `tokens.css`, the presence marks, the agent ring and its hairline, the commitment card's slots, the motions of §6.4. |
| [strings.json](strings.json) | The `room.*`, `talk.*`, `table.*`, `play.*` keys, the twenty strings of §7 among them. |
| [print.css](print.css) | The Room's paper section (§6.5). |
| `fixtures/` | A room holon in each phase (before, door, work, close, after), under Open and Names hidden, with a guest from a second house, an agent offering from untrusted text, a stale change refused, and offline. |

### 8.2 Tokens and the server

- **Tokens** in [tokens.css](tokens.css): `--ink-said` (dust), `--ink-kept` (paper at 88% on night; ink at 80% on paper), `--ink-agreed` (paper; ink), each passing contrast at its size (said in dust is 5.4 : 1 on night, as DESIGN.md §5.2 measures).
- **[serve.py](serve.py):** a live store for said speech **outside git and outside the record**, on the machine (the newest 500 lines of each room). Routes: `GET /talk?room=` (the room's said lines, each marked `kept` once kept), `POST /say` (a present person's said line, on their own tap; refused when they are not present), `POST /keep` (the room's keeper agrees another's said line, writing a `settle` in the room's record as the keeper's own line), `GET /presence?room=` (who is present). Every said line and keep sends `event: talk` on `/stream`.
- **[state.js](state.js):** the Room reads the said lines and presence from the served state (`hud.talk`, `hud.presence`), which `/stream` refreshes.

### 8.3 State the Room reads from STATE.md

`holons` (the room with `kind: room`, its `as_of`) · `actors` (`kind` person or agent, `for`, `delegation` with `live`) · `cards` (`holder`, `by`, `state`, `minutes`, `holon`, `system_critical`) · `commitments` (`keeper`, `by`, `size`, `witness`, `status`) · `threads` (`anchored_to`, `lines`, `last_actor`, `settled`) · `decisions` (`state`, `ratifier`) · `owed.entries` and `owed.proposals` (agent lines from untrusted text) · `deal` (with `room`) · `path.system`.

### 8.4 The shapes the Room asks of STATE.md

`rooms` and `roles` are in [STATE.md](../engine/STATE.md); the shapes below are what the Room asks of them and of the state around them.

- **`rooms`**: per room holon `{id, purpose, posture, posture_agreed: [actor], phase, parts: [{n, title, question, minutes, started, ended}], current_part, keeper, play_by_play_keeper, present: [{actor, kind, for, role, state, since}], affirmed: [{agent, by, at}], offered: [{line, by, for, reason, part}], curing_until, published: [{line, audience, by}]}`.
- **`roles`**: per holon, the Roles held by each person in it (`keeper`, `member`, `guest`, and any named for this room), and which are delegated to whose agent.
- **The room's Deal at its opening and at its close**, per wearer: `deals_by_room: {room: {opening, closing}}`.
- **Agreed-line metadata** for the Play by Play: per agreed line, `part`, `agreed_by`, `proposed_by`, `eyebrow`.
- **Holder role** on each card in a room (the face shows a role, and `holder` gives an actor).

### 8.5 Event types

- `posture`: a room's posture set by its keeper, and each person's agreement to it `{posture, agree}`. Declared in [types.json](../engine/types.json), human-only.
- `affirm`: a present person admits her agent to a room `{agent}`. Declared in `types.json`, human-only.
- `part`: the room's agenda part begun or ended `{n, title, question, minutes}`. Declared in `types.json`.
- `role`: a Role given to a person in a holon `{role, to}`, delegable by the existing `delegate`. Not yet declared.
- The **keep** move, presence, said lines and whispers are **not** event types: they live in the live store of §8.2 and never in the record.

**Done when:** a room of three browsers on the fixtures plays the hour of §2: each enters through the door and affirms an agent; a said line passes; a kept line stays on one machine only; a line offered in one browser is agreed by a person in another and deepens to full ink in all three; a commitment is spoken with its five slots and committed by the named person only; a card changes hands in front of everyone; the closing Deal arrives privately; the publish sheet shows the record with names hidden, each line proving its content and the set attested by the exporter; and the after-state of §2.5 is in each home.

---

## 9. The bar the Room is judged by

Judged on a phone in the hand first, then at 1440 px, night and paper, regular and large type, reduced motion on and off, with a group of at least three people and their agents for ten minutes, and once with a guest from a second house.

**The scenes:** the room staged (the day before) · the door · the first two minutes (the agents' offering) · a line agreed · a thread opened and closed · a card born from a line · a commitment spoken, with its five slots · a card changing hands · a member stepping away and returning · the closing ten minutes · the publish sheet under Names hidden · after, in one wearer's home · offline mid-room · the printed Page.

**The questions asked of every scene:**

1. Would a grandmother on her own phone, and a ten-year-old, each know what to do in the first minute, without a word they must learn and without help?
2. Would someone who runs meetings in the message, task, workflow and schedule products recognize that this is all of them, and better: the talk, the work, whose turn and when, on one table, with nothing to copy from one to another?
3. Is this a place people would choose to work in, or a viewer for minutes? Is a made thing (the Page, a laid card) being worked on together?
4. Can you tell, at a glance and from across the room, what was said, what was kept, and what the group agreed?
5. Can any agent's line become the room's word without a person's yes? Can an agent commit a person, or agree on her behalf?
6. Did the agents produce more than the humans could take in? Count the offered lines per part, and the minutes a person would need to read them.
7. Did the room end with sized, spoken commitments, each with who, what, by when, size and witness?
8. Under Names hidden, is every name gone from every screen and every export, with every line still proving its content and the set attested? Is a role on the face of every need, and a person's name nowhere it should not be?
9. Is every whisper readable by the person its agent serves? Did two agents ever write the same thing, or undo each other?
10. Does anything private (a Deal, a kept line, an agent's account) ever appear on a shared screen?
11. Does anything glow, pulse, sound, or move without meaning? Is the ink alone carrying the live line?
12. Does any string read as an AI wrote it: "not X but Y", a clipped fragment, a coach's question, a contraction other than the opener, "helper", the retired word for commitment?
13. Is the paper Page as good as the screen, and could a group with no screens run on it?
14. Does each house keep its own sovereignty: its keys at home, its inner record unseen, nothing leaving without a person's yes?
15. Is the Room's idea, one table, three inks, said in one sentence and seen in every scene?

A scene that fails 1, 2, 3, 5, 8 or 10 returns. The rest are lifted and passed.

---

## 10. The one shape

*On the face the room is a space; "the great room" keeps its name, being a room inside the space. Before any engine for meetings there is one shape only, with several parts, simple enough to work and safe enough to try. A shape is a little language for describing how a meeting might unfold; this is the first sentence in that language.*

### 10.1 The shape and its parts

| Part | What happens | Who moves it on |
|---|---|---|
| **The lobby** | The circle gathers. Each person agrees to the room's posture at the door before anything else of the room is shown. | The facilitator opens the great room. |
| **The great room** | Anyone present may propose, in one line. Each proposal lies on the table as a card. A present person's agent may propose for them under a live delegation. | The facilitator opens the vote when the circle is ready. |
| **The vote** | Each person ticks up to the rule's number of proposals (vote for three; the top two go on), inside a window of so many minutes. While it is open the screen says how many have voted, never the count, so no one votes with the crowd. A later vote replaces the earlier. | The window's clock, or the facilitator's switch, closes it. |
| **The writing** | The chosen proposals become one, two or three pieces of work: cards with a holder and a by-when, on the Table. A tie across the line is said plainly; the count never breaks it, the circle chooses. | The facilitator begins the reflection. |
| **Reflection** | One line each. The Play by Play of the room's moves beneath. | The facilitator closes the space. |
| **The close** | Each person confirms the posture they agreed to. Then the curing window: a few days in which anyone may narrow what they agreed to, or withdraw it. That change is their last word. | No one: the window ends by its date. |

The facilitator's switch is the only act that moves the space, one pill that only the facilitator sees ("Open the vote"); everyone else sees the part change on their own screen as the line arrives. The head of the space says the part in its voice: **"The great room. Anyone may propose. The facilitator opens the vote when the circle is ready."** One part fills the screen at every width, so a phone has one screen per part. The one owed thing (the door, her vote, the confirmation at the close) is the only thing in gold.

### 10.2 The postures and the curing period

Participation postures are agreed before the meeting starts, confirmed again when it ends, and followed by a curing period of a few days in which anyone may change their mind. The first four:

| Posture | What it says | It leaves the room as |
|---|---|---|
| Chatham House | What is said here may be used outside the space. Who said it, and who was here, stays in the space. | names hidden |
| Fishbowl | A few speak in an inner circle while the rest listen, and anyone may take a seat in the circle. Names may be seen. | open |
| Open | Names may be seen, and what leaves the space carries them. | open |
| Off the record | Nothing said here leaves the space. | sealed |

A circle may name another; the record leaves under the narrowest reading (sealed) until the circle says how it leaves. At the close: **"Confirm the posture you agreed to"** as the one act, then **"You may change your mind until Tuesday."** in dust. The curing window is three days by default (proposed; see Open).

A reader that takes a room's posture from its lines (mail) knows only the three postures of export; it maps a participation posture to one of them (`rooms.export_posture`) before it carries a line.

### 10.3 The record under it

`shape` (the keeper gives the room its shape, its facilitator, its posture and the vote's rule) · `part` (the facilitator's switch, with the vote's window) · `propose` (as it was) · `vote` (one line per person, up to the rule's number, a later one superseding) · `card`, `claim`, `hand` (the write-ups) · `say` (reflection) · `posture` with `at: open`, `at: close` and `withdraw` (the curing window). Person-only where a person must act: the posture, the vote, the facilitator's switch. The engine folds the shape into the room's state ([engine/STATE.md](../engine/STATE.md), A room's shape): the current part and since when, the proposals with their votes once the vote has closed, the tie said and never broken, the write-ups, the postures (who agreed, who confirmed, who has not, the window and what changed in it), and what the room owes. Everything the view shows is in that state.

### 10.4 Not yet built

- Several shapes, or a way to compose one (the language has one sentence).
- Breakouts, and any part that splits the circle.
- A facilitator who is an agent. The facilitator is a person only.
- Sound, timers that speak, a countdown that moves.
- A shape changed in the middle of a meeting beyond the keeper writing it again.
- The view of the said lines inside a shaped room. The Talk is the unshaped room's; a shaped room speaks through its parts.
- In the said-speech store: a rolling window of the room's length plus a day, deletion by the one who said it (`DELETE /say/<id>`), a stream of its own carrying whispers to the viewer's own agent, and `POST /presence`.

### 10.5 Open

- The names of the parts: whether lobby, great room, the vote, the writing and reflection are the words, and whether "great room" is the name or a working title. A part may be renamed without changing what it does.
- How long the cure lasts by default, and whether a person's change of mind may narrow what was already published inside the window.
- Whether the count is ever shown while the vote is open. It is hidden until the vote closes.
- The posture word itself: whether "posture", on the screen in "Confirm the posture you agreed to", is the word, or "the way this room meets".
