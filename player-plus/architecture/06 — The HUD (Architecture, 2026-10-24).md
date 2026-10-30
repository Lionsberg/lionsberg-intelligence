---
title: The HUD — architecture
description: The views a Player+ wears — The Deal, the three default layouts, every view and what it reads, the act path, and what the HUD never does.
---

# The HUD

*The HUD is the views of the ICE, the Integrated Creation Environment (the HUD, the dock, the Room): the surface a [[Player+]] wears. The [[The Game Engine|Engine]] folds [[The Record|the record]]; the [[Agent]] deals; the HUD shows. It holds no data of its own: every view is a sort of the one state the Engine folded from every [[Holon]] the wearer is part of. Hide every drawing and the words still tell one person the truth of their day.*

## 0. Where the HUD sits

Six layers, one record, one set of keys (SCHEMA, "The layers, one record"): the [[Selectively Permeable Membrane|Membrane]] (who may see) · the Record (the holon's lines) · the Proxy (between the agent and the models; records the person's [[Discernment|discernment]] as lines) · the Engine (pure functions over the lines) · the Agent (writes lines, deals [[The Deal]]) · the ICE (the HUD's views, the dock, the Room). In the LIØNSBERG Intelligence System, the Supersuit is a Player+'s bundle of Agent, Engine and ICE.

The HUD is the last layer and the thinnest. It reads one file, `state.json`, which the Engine writes over every holon held (the state contract, `engine/STATE.md`), plus the wearer's own `layout` lines. It writes only through one door, the act path (§6). It never computes a figure; it never fetches a holon on its own; it never holds a line the record does not hold. **One deck, one truth:** a view that needs a figure the state lacks shows the honest state ("Not computed yet"), and the field belongs in the state contract, never guessed.

The first-door plan is that for the first week the Agent is the HUD: The Deal arrives as a page in the player's viewer or a message on the phone, and the web HUD described here becomes a rendering over the same record after. Nothing in this page is needed for a Player+ to play; everything in it makes the play easier to see.

## 1. The Deal is the hero

**[[The Deal]]** is the few [[Work Card|Work Cards]] that need this player now, sized to the time they have, their place on the [[The Sovereign Path|Path]], and who is in the room. It opens every Player layout: "Here's the deal." Then the count and the cost are said first ("Two things need you today. About eight minutes.") so the wearer consents before starting. Each card is a question legible alone, with options, one marked *suggested* with its reason in one line; one tap or one key answers it. The last card is always the same: **"What did we miss that matters to you most?"**

Everything else is the same record seen from farther away: the Threads view is every open line to the wearer or to their agent; the Map is every field the wearer belongs to; the Chain is what the whole is waiting on, and it folds what a Board by stream would show (the HUD has no Board tab); the Room is the record being written live. One world, one deck, many distances.

**Reads** (STATE `deal`): `minutes_available` · `minutes_dealt` (never more than available) · `room` · `opening` · `cards[]` {`n`, `section` (owed · thread · decision · ready), `id`, `holon`, `holon_name`, `question`, `options`, `recommendation`, `why`, `unlocks`, `minutes`, `leverage`, `whole_waits`} · `beyond` {count, minutes} · `question` (the standing one, costing no dealt minutes) · `rule` · `as_of` per holon.

**The Deal is one view, never the only door.** The attention budget and its gate (the person's own `attention` lines, read through STATE's `attention`: `interrupt_now`, `margin`, `withheld` with each card's return time, `next_slot`, `quiet_now`) govern what *interrupts* the wearer; they never govern what the wearer may *read*. An interruption is a Deal of one card, in the same face, with the same options and the same Undo; what the gate withheld is said in one line with when it returns; reports that ask nothing are to become at most one margin line per body per hour, rewritten in place (proposed, not yet built; detail in `hud/DESIGN-ATTENTION.md` §3; the gate's defaults are proposed, and are the wearer's to set, with one card).

**Human acts.** A *will*, a *ratify*, a *decide* belong to a Living Intelligence: an agent never ticks a human's box. The card shows "A yes is yours to give" with your agent's draft beside it; the yes is signed with the wearer's key on the act path.

## 2. The three default layouts

A layout is an arrangement of views over the same state. All three draw from **every holon the wearer holds**, their own home and each cell joined; none is a per-holon app (SCHEMA: the Agent, the Engine and the HUD always pull from every holon the player is part of).

### 2.1 Player (everyone's default)

- **Shows:** The Deal (hero) · the two stacks at the foot, **What you committed to** and **Committed to you** · **Show me the whole** (opens the Map) · on wide screens, the Turn's four lines and the slice of the Chain that is the wearer's own cards on the system path.
- **Hides until asked:** the Threads view's quiet rows (what waits on others), the Ledger, the Record, the full Chain, every number but counts and minutes.
- **Its idea in one sentence:** the two or three things that need you today, with the whole one gesture behind them.

### 2.2 Cell steward

- **Shows:** the cell's cards by stream (hero) · **commitments kept** for the cell this week and this season (the first number every holon sees) · what is owed between members · [[Buffer|buffers]] at the cell's interface [[Milestone|milestones]] · the steward's own Deal, folded small ("2 need you").
- **Hides:** other cells' inner cards (never available: only published faces), the Ledger's detail, the Map (one tap away).
- **Its idea:** the work of the holon at once, and who waits on whom.

### 2.3 Room (the collaboration surface)

The Room layout over a shared holon's record **is** the collaboration surface. A room of people and their agents works over one record; the meeting record is a by-product of the work being done there. Its parts are in §4.

### 2.4 Default, then yours: customization as recorded events

A new Player+ inherits a default HUD, one to three layouts, and their agent customizes it for how they work. The customization is an act like any other:

- The wearer says it in her own words ("Put the commitments first", "Bigger letters", "Make me a layout for Sunday planning"). Her agent writes a **`layout` line** to the wearer's home holon, audience `holon`, reason `human`; the HUD folds the latest one per name.
- **Body** (`layout` is declared in `engine/types.json` as data, never as code, human-only and home-only): `name` · `views` (ordered view ids) · `hidden` · `theme` · `density` · `type_size` · `default` · `consent`. Not yet settled: a `holons` field (default all) and the values each field takes (for example regular · large, system · night · paper, calm · full).
- The HUD says the change once, quietly, for eight seconds: "Your agent moved the commitments to the top. Undo." (or the agent's name, once the wearer has named it). Undo writes a `supersede`; both lines remain.
- By hand: long-press a view's title → Move up · Move down · Hide; the same line, by her key.
- **A layout can never** widen an audience, show another person's inner record, turn on sound, or remove the privacy line and the Back control. A layout is a sort of the same state; it holds no data.
- Because layouts are lines in the wearer's own record, they travel with her: a new device, a new install, a paper print all fold the same layouts.

## 3. Every view, with its purpose and what it reads

One card face everywhere (`hud/card.js`): eyebrow (why it is here · its home holon · its kind) · the question · the essence line · options, one marked suggested with its reason · the foot (holder · by when in words · minutes · days to spare · as of) · **Open the card**, the full card (predecessors and successors, the thread, the lines that made it, its witness, and everything else the state and the record say about it). A card held in two holons shows its home and "also in …" (not yet built; its alias is described in [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]]).

Field names below are STATE's. Where a view needs a field STATE does not yet carry, it is marked **(not yet in STATE)** and listed under Not yet built.

| View | Purpose (one sentence) | Reads |
|---|---|---|
| **Top line and holon ribbon** | The wearer always knows which holons she sees and how fresh each is. | `generated_at` · `holons[]` {`id`, `name`, `kind`, `keeper`, `as_of` {`event`, `ts`, `lines`}} · (not yet in STATE) `heard`, `readable`, `posture`, `role` |
| **The Deal** | The few cards that need this player now. | `deal` (§1) · `owed.entries` for the two stacks · `commitments` |
| **The two stacks** | What I committed to, and what was committed to me, always in sight. | `commitments[]` {`id`, `holon`, `card`, `title`, `keeper`, `by`, `size`, `witness`, `status`, `gap_days`} · (not yet in STATE) the receiver of each commitment |
| **The Queue** | Everything waiting on the wearer across her holons, with what fits the time she has. | `owed.entries[]` {`kind` (commitment · request · thread · ratify · claim), `id`, `holon`, `title`, `holder`, `status`, `due`, `age_days`, `minutes`} · `owed.proposals` shown apart as "drafted from something I read", never counted as owed |
| **Threads and Mail** | Who wrote, whose turn it is, what each asks of the wearer, and the place to answer. | `threads[]` {`id`, `holon`, `anchored_to`, `title`, `lines`, `last_actor`, `last_ts`, `settled`, `to`, `stake` {`blocks`, `critical`, `by`, `holder`, `urgency`, `minutes`}, `push` {`sent`, `push_by`, `state`, `weight`, `by`, `why_by`, `blocks`, `critical`, `cost_if_late`, `own`, `calibration`}} · `calibration` · the server's `badges`, `mail` and `transports.mail` from the carried store (`<hq>/.carried/`); the badge counts only what needs the wearer's word |
| *The Board by stream* (folded into the Chain) | No tab of its own: a holon's cards by stream, least float first, are read from the Chain and from the steward's layout. | `cards[]` {`stream`, `state`, `holder`, `minutes`, `by`, `TF`, `critical`, `system_critical`, `holon`} |
| **The Map of cells and quests** | Every holon the wearer belongs to, as fields turning on their own axes, with what crosses their membranes. | `holons[]` · published faces in `cards[]` · `path.system` · (not yet in STATE) `activity_7d` |
| **The Chain** | What unlocks what, and what the whole is waiting on. | `path` {`critical`, `system`, `finish`} · `cards[]` {`ES`, `EF`, `LS`, `LF`, `TF`, `FF`, `predecessors`, `successors`} · `buffers[]` {`milestone`, `holon`, `size_days`, `consumed_days`, `chain_complete`, `signal`} |
| **commitments kept** (steward) | The holon's first number and each gap, as learning. | `kept` {`window`, `by_holon`, `by_actor`, `commitments`, `learning`}; each tally {`made`, `kept`, `kept_unwitnessed`, `broken`, `released`, `returned`, `open`, `share`} |
| **Owed between members** (steward) | Who waits on whom, for what, by when. | `owed.entries` by holder within the cell |
| **The Play by Play** (Room) | A room's settled lines as they are written, with their threads. | `threads[]` {`id`, `holon`, `anchored_to`, `title`, `lines`, `last_actor`, `last_ts`, `settled`, `to`} · `decisions[]` {`state` (open · decided · ratified), `ratifier`} · (not yet in STATE) recent settled lines, offered lines, yeses awaiting a person, presence |
| **The Ledger** | Time, energy and attention given toward the work, witnessed, never convertible. | `tea` {`by_actor`, `by_holon`, `by_card`, `by_stream`, `witness`, `convertible: false`, `chain`} · `discernments` {`count`, `by_route`, `by_verdict`}, visible to the wearer alone |
| **The Turn** | The week in four lines, and commitments kept. | `turn` {`last_weekly`, `last_seasonal`, `next_weekly_due`} · `kept` |
| **The Record view** | The truth under every view, readable by eye. | (not yet in STATE) the lines themselves with a verification mark (signed · unsigned paper · a link not yet arrived) and elided fields left elided |
| **The axis** (press and hold any still point) | The chain from an act to the Living Intelligence who answers for it. | `actors[]` {`id`, `kind`, `for`, `holons`, `delegation` {`from`, `scope`, `holons`, `until`, `live`}} |

Held in the state and not drawn by default: `score` (earned value per holon; never a score of a person), `load` (minutes asked per actor per day; a steward may open it), `sightings`.

## 4. The Room layout: the collaboration surface

A room is a holon (SCHEMA `kind: room`). Its record is written by the people present and their agents; the Room layout renders it live.

- **Speech is not kept; only what someone settles.** A small standing line under the room's name says so. Nothing in the Room is a transcript. In live text the unit is the settled line, a hypothesis stated so it can be changed. A line is *offered* (by a person, or by an agent, marked "offered by the keeper's agent", "offered by your agent") and becomes a `settle` line only by a person's tap.
- **Settled lines as events.** The Play by Play shows each settled line as a row: time · who (a Role or a name, as the posture allows) · its type when more than a line (DECIDED · WILL · CARD · ASKED) · the line. A line an agent wrote carries a small ring beside the mark of the person it answers for.
- **Threads anchored.** A thread is anchored to a line or a card (SCHEMA `anchored_to`); its count sits under the line; tapped, it opens inline beneath it. A thread anchored to nothing is a conversation, and nothing forces a card on it.
- **Presence.** One row: people as marks, agents as small rings attached to their person (an agent never attends in its person's place). Presence is shown, never stored as a record line, unless a check-in is settled.
- **Cards dealt in the room.** The Deal comes at the start and the end of a meeting: *Dealt here* holds the cards dealt to this room at its opening and its close. Each wearer's own Deal is one chip ("Your deal · 2") that opens as a sheet.
- **Yeses awaiting a person.** A pinned row: anything an agent drafted that only a Living Intelligence may say. Only the person named can give each yes.
- **The posture.** Open · Names hidden ([[Chatham House]]) · Members only. Under Names hidden, people are "a member" with neutral marks, and every exported line keeps its proof by [[Elision|elision]]; the export removes signatures and the exporter attests the set, until the envelope form, which keeps each author's signature while hiding names, is built.
- **Offline.** Offered lines queue on the device, marked "waiting to send", and are written in order when the room returns.

## 5. The first door

**The first door:** a Player+'s agent runs on their own machine from the first day. A friend [[20 Pass the Flame|passes the flame]]; the install is one line pasted into the command-line harness and takes minutes; the agent speaks first, in the player's words, language and pace, and The Deal arrives by about minute ten. Afterward the phone reaches the agent on that machine, by voice or message, and the HUD opens from a link the agent sends; a printed card serves whoever prefers paper. That is the default; a shared machine, or a cell hosting agents for others, are other configurations of the same space, chosen by the house.

**The one-breath test:** after the first minute the wearer can tell a neighbor, unprompted: "I have an agent who keeps track of what I committed to and what others committed to me, tells me the two things that need me today, shows me the whole when I ask, and never shares my words without asking." Each clause is an element she can point at: the two stacks · the opening line and its count · **Show me the whole** · the privacy line, **"Only you see this. Nothing leaves without your yes."**

**Voice.** Any line can be spoken: the standing question, a line offered in a room. Dictation stays on the device where the device allows; what is spoken is a draft until the speaker settles it.

**The paper mirror.** Every item has a paper form and every number can be worked by pencil (SCHEMA, "The paper floor"). The printed Deal card carries up to three questions with tick boxes and the standing question with ruled lines; its back carries the wearer's holons with their "as of" and a line for a witness's initials. Every view prints; the Chain prints as the two-pass pencil sheet; the Record prints as one line per event. A witnessed paper sheet beats the typed copy. Answers on paper return when the wearer tells her agent or shows it a photo (how such a yes is signed is in Open).

## 6. Static files, a local server, the act path

- **Static files, no build step.** Plain pages, styles and scripts loaded as written; no framework; no package manager; any library vendored as one file with its exact version in its name. Fonts vendored so the HUD reads offline.
- **A tiny local server**, standard library only, bound to the loopback address, behind a token and a Host check so that a web page or another local caller cannot act through it: serves the files, `GET /state` (the merged state), `GET /stream` (a push when any holon's state changes), `POST /act`.
- **The act path.** A view calls **act**(type, body, links, holon). The server holds the act as *pending* for the undo window (five seconds by default; lengthened to fifteen in a layout) and shows **Undo**. Within the window, Undo cancels it and nothing is written. After it, the server computes the line's `id`, sets `reason: human`, chains `prev`, **signs with the key the server was started with, which is the wearer's own and never an agent's**, and appends to `record/<actor>.jsonl` in the named holon. After the line is written, a correction is a new line that supersedes; nothing is edited.
- **What the server refuses:** any line whose audience is wider than its holon; any human-only type (will, ratify, decide, publish) not confirmed by the wearer's own act; any `publish` without the publish sheet's confirmation. The refusals live in the server, not in a view: a control held only at the edge is a hope, not a guarantee (see [[08 — Security and Sovereignty (Architecture, 2026-10-24)]]).
- **Two sheets every view uses.** The *publish sheet*: anything that would cross a [[Selectively Permeable Membrane|membrane]] says plainly what will be seen and by whom, with **Publish** and **Keep it here**; there is no other route outward. The *act sheet*: for any human-only act, your agent's draft, the consequence in one line, and the wearer's button.

## 7. Every holon held, "as of"

Time is a claim; order comes from links. Every computed figure carries, in its fold, *as of which line it last saw from each holon*; on its face, only the word ("as of 9:14"). Each holon's chip on the ribbon says its freshness in words ("all current", "Cell Two last heard Tuesday"). A holon that could not be read shows its chip with "could not read" and **Try again**, and everything else is shown. Loading shows the last known state dimmed, never a blank; an error names what failed and never substitutes; offline shows what the home record holds. A link to a line not yet held reads "not yet arrived", never "broken". Two wearers holding the same lines see the same figures; they differ only by replication lag, and the HUD says which.

## 8. Accessibility

The floor is WCAG 2.2 AA, and AAA for body text where the palette allows. Meaning is never carried by colour alone: every coloured state has its word. Everything is reachable by keyboard, with a visible focus ring; The Deal answers to single keys. The Map's list twin and the Chain's table twin are full views, complete in content, and are the screen-reader, large-type and reduced-data forms. Settled lines in the Room arrive in a polite live region; the undo window is announced. Large-type mode is a layout field. Under reduced motion nothing turns or travels; every change is a crossfade. Targets are at least 48 px; no gesture lacks a visible button doing the same. Plain language at a reading age of about twelve on the Player layout; the words *holon, event, fold, engine, schema, float* never reach a Player's screen (say "days to spare"). The agent is "your agent", your map and your guide, and once the player names it, its name is used; "helper" is never used. Nothing flashes more than once a second.

**The bar for the working surface** is `hud/DESIGN-THE-BAR.md`, which takes the place of the ten principles of `hud/DESIGN.md` §9 for the working surface; the brand's Award Bar stays the bar for stories and scenes. The bar: quiet when nothing is owed; the level-2 and level-3 facts the Engine computes (owed, stake, by-when, chain, calibration, freshness) shown directly; salience following computed stake, with the brand's gold spent only on the owed thing; position fixed across visits; a picture where a picture is owed, never a list beside it; tested with a tired person on a phone at night. Its §5 is the sheet every view is scored against, and its §4, the surface studies itself, is how every change to a view is measured (see [[12 — The Roadmap — Potential Future Features (2026-10-24)]]).

## 9. What the HUD never does

- **Compute a schedule.** Every float, path, buffer, owed list and commitments-kept figure comes from the Engine's fold; a view that computes one is a second engine and a defect.
- **Widen an audience.** Within a holon audience only narrows; crossing a membrane is a separate `publish` line by a Living Intelligence, through the publish sheet, refused by the server otherwise.
- **Play sound unasked.** No sound token exists. If the wearer turns on notifications, the phone's own settings decide.
- **Show a hidden name.** No name the room's posture hides, no line outside the viewer's audience, no other holon's inner record (only its published faces), no member's location.
- **Give a person's yes.** An agent drafts; only the person's own act, signed by their key, says will, ratify or decide.
- **Draw a center.** No root, no tree, no org chart, no ØNE as a node. Each field turns on its own axis; every still point points to the same stillness out of frame. No center but [[ØNE]].
- **Demand to be watched.** Nothing advances on a timer; when the deal is played, the surface goes still. No red badge, no streak, no ranking of people, no currency symbol.

## Open

1. **Where the wearer's signing key lives.** The local server signs with the person's key on the same machine where the agent runs; the human key and the agent key are distinct. Open: whether the person's key should sit on a separate device or secure element (see [[08 — Security and Sovereignty (Architecture, 2026-10-24)]]).
2. **A yes from paper or a photo.** The agent writes it with `reason: human` and "from the paper card"; it is not signed by the person's key. Open: whether it waits for the person's next signed act, or a witness's initials suffice.
3. **A room: holon or view.** SCHEMA makes it a holon. Open: whether it should be a view.
4. **The live-text unit.** The settled line as the event is a hypothesis. Open: whether the Change, a signed settled edit as the unit of authorship, replaces it (see [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]]).
5. **Presence.** Open: whether a check-in is ever a record line, and under which posture presence itself is hidden.
6. **Who customizes for a cell.** Open: whether a steward's layout can be offered as the cell's default, and by whose consent; and whether any layout can be offered to a cell as a published line and adopted by another wearer as her own new line.

## Not yet built

- **Fields STATE does not yet carry:** per holon `heard`, `readable`, `posture`, `role`, `activity_7d`; the receiver of each commitment (for "Committed to you"); per room presence, recent settled lines, offered lines, yeses awaiting a person; the lines themselves with a verification mark; the folded layouts. `hud/DESIGN.md` §8.4 names them under other field names; where both name a field, STATE wins.
- **The steward's cards by stream in the Chain.** The steward's layout still draws them with the Board's code; folding them into the Chain is not yet built (see [[12 — The Roadmap — Potential Future Features (2026-10-24)]]).
- **The "also in …" mark** for a card held in two holons: no type, link key or view writes or shows it yet.
- **The envelope form** for exports from a Names-hidden room.
