---
title: The Dock
description: The design of the dock, the conversation with your agent as the conversation pane of the ICE, for anyone who builds on it or reviews it.
---

# The Dock

*The conversation with your agent, as the conversation pane of the ICE. This page is a design held loosely, in words and order; parts not yet built are marked as proposed; the code follows it; §9 is the bar it is judged against. Where it speaks of the agent's conversation it binds over [DESIGN.md](DESIGN.md); [DESIGN-ROOM.md](DESIGN-ROOM.md) and [DESIGN-WAY-IN.md](DESIGN-WAY-IN.md) bind over it wherever they differ.*

**The name.** The surface is **the ICE, the Integrated Creation Environment**: the HUD's views, the dock and the Room, the interface the kit owns, with the Proxy beneath. The IDE, the integrated development environment a builder works in, is its primitive forerunner. The whole is **The LIØNSBERG Intelligence System**; the Player+'s bundle (Agent · Engine · HUD) is **the Supersuit**. On this page, "the HUD" names the views and their files, as DESIGN.md does; "the ICE" names the whole surface the player lives in, of which **the dock is the conversation pane**.

**The ground this page is built on:**

- The ICE is the primary surface a Player+ lives in. The conversation with their agent is a pane inside it, **the dock**, speaking the **Agent Client Protocol**, so that any agent plugs in: the command-line harness, a local model, another house's agent.
- The vendor's chat window is a fallback.
- A Player+'s agent runs on their own machine. This is what keeps every Player+ sovereign and free. Hosting agents for other players is a service some cells may offer later.
- A local session inside the vendor's desktop app ignores a custom base URL, and the vendor's phone remote control refuses any proxy. So the only phone door that keeps the proxy is **the dock on the player's own machine, reached over the private network**.
- No sound unasked. No drawn light. The word is commitment. The cards are The Deal. The agent is "your agent" until the player names it.

---

## 1. The one idea

**One surface, the ICE: you speak with your agent beside The Deal, never instead of it, in the brand's voice, and you never leave the night ground to do it.**

- **One surface.** The Deal, the whole, the Room and the talk with your agent are one place, the ICE, with the Proxy beneath it. The vendor's window, the terminal and a message channel remain as doors when the ICE is closed (§3), and each of them writes into the same record.
- **Beside The Deal.** The Deal is the hero (DESIGN.md §1). The dock sits at its edge on every width and never covers it entirely: on a phone the top line of The Deal stays visible above the open dock ("Here's the deal · two need you"), and one tap on it drops the dock back down. The talk serves the deal; the deal never waits behind the talk.
- **In the brand's voice.** The dock's own words are the HUD's (second person, plain, warm, short). Your agent's words are your agent's, set in the same type, on the same ground, with the same calm: EB Garamond, the night or the paper ground, no chat bubbles, no avatars, no typing dots. A conversation here reads like a page being written between two people, never like a messenger.
- **On the night ground.** Speaking to your agent never leaves the ICE: it never opens another window, another app or another sky. The ground, the type and the motion of the dock are the ground, type and motion of The Deal (DESIGN.md §5).

**The one-breath test for the dock** (§9): after her first minute, a newcomer says to a neighbour, unprompted, *"I talk to my agent right there beside my deal, it asks me before anything that matters, and I can see what it put in my record."*

---

## 2. What the dock is

### 2.1 A pane in every layout

The dock is the ICE's conversation pane. The shell places it in every layout (DESIGN.md §3). A layout opens it or collapses it, and the player may collapse it to nothing.

| Width (DESIGN.md §5.7) | Collapsed | Open |
|---|---|---|
| **phone** 0–599 px | One bar at the foot, above the safe area: your agent's ring and its name (or "your agent"), then the line to speak, "Talk to your agent", 56 px tall. The Deal fills the screen above it. | A bottom sheet rising to leave The Deal's top line in view (about 85% of the height, `--r-sheet` corners). The keyboard pushes the sheet, never The Deal's line, off screen. Drag down, tap The Deal's line, or press Back to close. |
| **tablet** 600–1023 px | The same foot bar, across the main column. | A right-hand pane of 24 rem over the aside; The Deal stays whole in the main column. |
| **desktop** 1024–1439 px | A rail of 56 px at the right edge: the ring, and the name set vertically in small capitals. | A third column of 26 rem at the right; the Player layout's aside (the Turn, "The whole is waiting on") moves beneath the Deal or folds, as `density` says. |
| **wide** 1440 px and up | The rail. | The third column of 26 rem, inside the 1360 px content width. |
| **large type** (any width) | The foot bar at the large scale. | A full sheet with The Deal's top line held at the top; one column. |

- **Open or collapsed is remembered** per layout, in the `layout` event (a field `dock`: `open` · `collapsed`), so the player's own choice survives a reload and is a sort of the same state (DESIGN.md §3.4).
- **Two views of one conversation, one button apart.** A button on the dock switches the same session between the ICE view (turns, context cards, inks, the margin) and a terminal view of the same agent (the same stream as a plain monospace transcript, raw tool lines included, with an input line). Nothing is lost in either. A true command line is a separate thing: a pseudo-terminal the host starts on the player's tap, in the same home, for the harness or any command. It is a second session on the same home, never the same live conversation, and the pane says so plainly.
- **Room layout:** the dock is the player's private talk with their own agent, beside the Room's public Talk. It never shows in the Room's columns and never on a shared screen; "Show to the room" never includes it (DESIGN-ROOM.md §6). *(Proposed.)*
- **At the thing.** When a card is selected anywhere in the HUD, the dock's line to speak shows, in dust above it, "About: Bring the costs by Thursday", so the words are said at that card. One tap on the small × beneath it speaks about nothing in particular.

### 2.2 The first word under ten seconds

The dock is judged by its first word (DESIGN-WAY-IN.md §3.4 for the waking clock).

- **Warm:** from Send to your agent's first word, **under ten seconds**, and **no ask before the first word**. Your agent greets without a tool.
- **The waking:** if your agent is asleep, the first tap says so at once and plainly, with its time: "Your agent is waking. About a minute." The waking is a scene told in words; never a spinner, a bar or a countdown.
- **The agent host outlives the HUD.** The agent process lives in its own small host on the machine, which the HUD only speaks to, so a reload, a restart of `serve.py` or a closed tab never ends a conversation or lapses an open ask (§8).

### 2.3 The Agent Client Protocol is the plug

- **What the dock shows is only what the agent declares** at `initialize` and after: its modes, its commands, its configuration options, whether it takes images or audio, whether it can resume a conversation, its plan, its tool calls and their diffs, its usage. What an agent does not declare does not appear as a dead control; it is simply absent. The dock shows what is declared, supplies what it can itself, and leaves out the rest cleanly.
- **What the dock supplies itself, for every agent:** the context card around a permission request (§2.4); the record margin (§2.5); "Where did that go?" (§2.6); the discernment gesture (§2.7); search across your own conversations; postponing into The Deal; the phone door (§4).
- **The dock asks nothing of the agent that the protocol does not carry.** It declares no file-system or terminal capability of its own to the agent by default: the agent works with its own tools under its own permissions, and the HUD is never a file server for it (a security rule, §8.4).
- **Everything the agent sends is data.** Its words are rendered as text with plain formatting, never as markup the browser runs; no image is fetched from a remote address; a link shows its full address before it is followed.

### 2.4 A permission request arrives as a context card

When your agent asks before it acts, the ask arrives as a card above the line to speak, in the card face of The Deal (`card.js`, compact form):

- **What, in plain words** (from the agent's own title for the act, rewritten by nothing).
- **Why**, in the agent's own words, labelled as its words: "Your agent says: …".
- **Exactly what would happen**, folded: the command, or the file and its change as a diff. Monospace only inside the fold (DESIGN.md §5.1, raw lines).
- **Where it reaches**, always said in one line: **"This stays on your computer."** or, in full ink, **"This leaves your computer."** (a send, a post, a push, a publish, anything that reaches another person or service).
- **The Lexicon's line for any id** in it, on hover or long-press.
- **What your agent said just before**, one line, so the card stands alone.

**Three answers, always:**

| Answer | What it does |
|---|---|
| **Yes** (once) · **Yes, for this kind** (the scope said in words before it is chosen: "every read inside your home folder") · **Not this** | The agent's own options, as it offers them. "For this kind" is never offered for anything that leaves your computer: an act outward is answered once, every time. |
| **Explain first** | Declines for now and asks your agent why, in its next turn. |
| **Put it in my Deal** | Declines for now; the ask becomes a card in your next Deal ("Your agent asked to send the costs to Cell Two. Postponed from Tuesday."), and your agent is told not to wait. |

- **An ask left fifteen minutes** postpones itself into The Deal, so no agent waits on an absent person (fifteen minutes, per agent).
- **An ask whose reason came from something the agent read** (a page, a message) carries the Room's second mark and the words **"from something it read"** (DESIGN-ROOM.md §2.3; `reason: untrusted`).
- **Waiting on you is shown beyond the dock** only as one line at the HUD's top strip ("Your agent is waiting on you"), and in full ink on the collapsed bar. No badge, no count in red, no sound.

### 2.5 The agent's acts on the record, in the dock's margin

When your agent writes to the record, or offers to (a commitment drafted, a card made, a line said in a room, a memory kept), a line appears in the dock's **margin**: the edge of the dock that faces The Deal, aligned with the turn that made it. On a phone it sits beneath that turn, indented 16 px with a hairline at its left.

Each margin line carries an eyebrow in small capitals (COMMITMENT · CARD · SAID IN THE ROOM · KEPT · ASKED), its words, and **its ink**, in the one ink grammar the whole HUD uses (DESIGN.md; DESIGN-ROOM.md §1):

| Ink | In the dock it means |
|---|---|
| **said** (dust, italic) | Your agent offered or drafted it. It is not in the record. |
| **kept** (the step between ink and ground) | It stays on this computer: a memory, a note, a line kept off the record. |
| **agreed** (full ink, with ✓) | It is in the record, signed by you. |

- **Only a person agrees** ([STATE.md](../engine/STATE.md): "Only a person's lines agree to anything"). A said line in the margin carries **Agree** · **Not this**; agreeing it writes through `ctx.act(…, {confirmed: true})` from your own tap, with the five seconds of Undo, and the ink dries over `--d-ink` as everywhere: the product's only celebration.
- **Tap a margin line** and its card opens as a sheet over The Deal (`ctx.openCard`), so the talk and the deal are one record seen twice.
- **What the margin never shows:** a count of what your agent produced, a tool's raw output, or any line whose audience is narrower than you.

### 2.6 The proxy underneath, invisible unless asked

The proxy routes your agent's requests to its models and writes a `route` line for each ([the Proxy's architecture](<../architecture/05 — The Proxy (Architecture, 2026-10-24).md>) §1–§3). In the dock it has **no face at rest**: no model name, no vendor, no meter. The proxy as an interface of its own is set aside (the architecture's Open 7).

- **"Where did that go?"** sits in each finished turn's quiet foot (§6.4). It opens a sheet in plain words, from the route lines of that turn: "Your words went to a model on this computer. Nothing left it." or "Three requests: two to a frontier model, one kept on this computer because it was marked private." With the time each took, and, in a fold, the rule each matched. **Never a prompt or a reply**, because the route line holds none.
- **The proxy's absence is said once**, never hidden: when the base-URL setting is gone or the proxy is not answering, the foot carries one line in dust, "Your agent is speaking to its models directly. Nothing about where your words go is being recorded.", until the player answers it (**Turn it back on** · **Leave it**). The proxy's absence never looks quiet (the architecture's acceptance test 8).
- **Turns are joined to their route lines** by the turn's time window, and the sheet says "matched by time" (§8.2).

### 2.7 Discernment in one gesture

Your judgment of what your agent gave back is a resource that evaporates (the Proxy's architecture §0). The dock captures it in **one gesture, without ceremony**, and only after the player has said yes to capturing it at all: an offer, never a fait accompli (the architecture §7).

| Verdict | The gesture | What is written |
|---|---|---|
| **chosen** | When your agent offers two or more versions, tapping one is the choice. | `discern`, verdict chosen, linked to that turn's route |
| **corrected** | Edit any words of your agent's turn in place and send: the edit is your reply and your correction at once. "No, Thursday" typed as a reply also offers, in dust beneath it, "Count this as a correction" for one tap. | `discern`, verdict corrected, the note your own words |
| **rated** | With the turn focused, a number key 1 to 9 (0 is ten); on a phone, long-press the turn and choose a number. | `discern`, verdict rated |

- `discern` is human-only and signed by you ([SCHEMA.md](../engine/SCHEMA.md); the architecture §3). Your agent never rates itself.
- No stars, no thumbs, no prompt after every turn asking how it did. The gestures are there when the player reaches for them, and silent when not.
- The week's count shows in the Ledger (DESIGN.md §4.7, `discernments`), never in the dock.

---

## 3. The degradation ladder

The dock never assumes one harness, one vendor or one network. It works across agents, degrading gracefully down to a local agent on a machine of unknown capability. Every rung writes into the same record and reads the same Deal.

| Rung | What answers | What the player keeps | What the player loses |
|---|---|---|---|
| **1. The dock over the protocol, inside the ICE** | your agent on your machine, through the agent host | everything on this page: context cards, the margin, "Where did that go?", one-gesture discernment, the phone door, postponing into The Deal | nothing |
| **2. The command-line harness in a terminal pane** | the same agent, in a terminal window beside the HUD (or a terminal pane the shell opens, where the device allows) | the proxy (the base-URL setting holds); the margin, because the HUD reads the record and shows the agent's lines as they land; The Deal | the context card (asks become the terminal's own prompts); postponing into The Deal; the discernment gesture (a `discern` is written by asking the agent, in words, or by the proxy's own door) |
| **3. The vendor's desktop app beside the HUD** | the vendor's app, on the same machine and the same home folder | The Deal; the record, written by the kit's own scripts | **the proxy** (a local session there ignores a custom base URL): no `route` lines, so no "Where did that go?" and no discernment linked to an answer; the context card; the margin until the agent writes |
| **4. A message channel** | a channel the player already uses, answered by the agent on the machine | the proxy (the agent behind the channel is the same harness on the same machine); The Deal in text, the-deal's grammar, options answered by number | everything visual: cards, ink, the margin, the whole; asks become a numbered question in text |
| **5. Plain-text threads on paper** | any body, or a person with a pencil | **the printed Deal** and the record's plain lines; answers written on paper return when the player tells their agent or shows it a photo (DESIGN.md §7) | the agent itself |

**What never changes, on any rung:** the record (one holon, one chain of signed lines); The Deal (dealt from the record, the same on every rung); the keys (a person's yes is signed by that person's key); the audience (nothing widens without the publish sheet); and the speech ruling (what is said is said; only what a person agrees enters the record) (DESIGN-ROOM.md §1).

The dock says which rung the player is on only when it changes, in one line: "Your agent is answering in the terminal now. Your asks will appear there." *(Proposed; not yet in the strings.)*

---

## 4. The phone

The phone door is a space of configurations. The ICE reached over the private network keeps the proxy (§4.1); the vendor's remote control is another configuration, and it loses the proxy (§4.3).

### 4.1 The door that keeps the proxy

*The door's security, its certificate and the trust step are designed in [DESIGN-PHONE-DOOR.md](DESIGN-PHONE-DOOR.md) (§6 is what the sheet shows); this section keeps only the dock's side of it.*

The vendor's phone remote control refuses any proxy. So the phone door the dock offers is **the dock itself, served by the player's own machine, reached from the phone's browser over the private network**.

- **On the player's word, never before.** The phone is a day-two card (DESIGN-WAY-IN.md §3.5, §4): *"Reach me from your phone? About five minutes."* Nothing about the phone exists on night one.
- **What the player does, once.** On the computer, the card opens a sheet: **"Your phone becomes a window into this computer. Your computer stays on."** Then three steps in plain words: the private network on both devices (the kit's own step names the network the player's cell uses; this page names only its role); on the computer, **Let my phone in**; on the phone, open the address the sheet shows, or point the camera at its code.
- **What the machine does.** `serve.py` starts a second listener bound to the machine's **private-network address only**, never to every address, and never to the open internet (§8.4). The sheet shows a one-time pairing code; the phone that presents it receives **its own device token**, held as a hash on the computer and revocable by itself. The phone's browser keeps the token; every write carries it, as every write on the computer carries the page's token.
- **The proxy stays on loopback.** The agent still runs on the computer and still calls its models through the proxy at `127.0.0.1`. The phone is only a window. Every `route` line, every `discern`, every card is written on the computer, exactly as from the desk.
- **The phone's dock** is the phone layout of §2.1: The Deal, the foot bar, the sheet. Large type follows the phone's own text size.
- **The phone lists in the computer's HUD** under the about sheet: "Your phone · added Sunday · last seen this morning · **Let it go**". Letting it go revokes its token at once.

### 4.2 Voice notes in

The same agent answers a spoken sentence on a walk.

- **The phone's own dictation** works in the line to speak at once, with nothing built: the keyboard's microphone key.
- **A voice note**: a **Speak** pill beside Send. The door is served over https (DESIGN-PHONE-DOOR.md), so the microphone opens there and the layered voice of §10 is the first path. Where a browser refuses the microphone, the phone records with its own recorder (the browser's file capture, which still works there). The audio goes to the computer; **a local speech model on the computer** turns it into words; the words appear in the line to speak, **for the player to read and send**. Nothing is sent to the agent until the player sends it.
- **The audio is said-kind speech** (the speech ruling, DESIGN-ROOM.md §1): it is deleted on the computer once its words are shown, unless the player taps **Keep the recording**. It never enters the record and never leaves the machine.
- **Recording shows in words**: "Recording · 0:12" and a **Stop** pill. No pulsing dot, no glowing ring, no waveform drawn as light.
- **Replies are text** by default. They are read aloud only when the player turns that on (§10).

### 4.3 The fallback that loses the proxy

When the private network is not in reach, the vendor's phone remote control remains a door to the same agent on the same computer ([the phone-path skill](../skills/phone-path/SKILL.md)). The dock names it plainly, once, on the phone card: **"If this page cannot reach your computer, the vendor's own app can. It works without the record of where your words go."** The skill's warning holds there: the button for a new session on the vendor's computer is not your agent.

### 4.4 When the computer sleeps

The phone cannot reach an agent whose computer is off (the phone-path skill; DESIGN-WAY-IN.md §7). The phone keeps the last Deal it held and shows it with its "as of"; words typed while the computer sleeps wait on the phone and are sent once, when it answers, with their state shown ("Waiting for your computer · sent when it wakes").

---

## 5. Many agents, one person

The Room's law is the dock's law: **an agent is never free-standing; it is always joined to the person it serves** (DESIGN-ROOM.md §4.1).

- **Your agent** is a small open ring joined by a hairline to your own mark, at the head of the dock. Its label is the name you gave it, or "your agent" until you do (DESIGN.md; DESIGN-WAY-IN.md §3.2). The name lives in your home's record (`actors[].name`, asked of STATE by DESIGN-WAY-IN.md §9) and is shown to you alone.
- **A second agent** (a cell's facilitating agent, a guest's agent from another house) appears as **a second ring joined to its own person's mark**, or to the cell's mark when it serves the whole cell, never to yours. Its label is possessive and by role: "the keeper's agent", "a guest's agent", "the cell's agent" (DESIGN-ROOM.md §4.1). Under Names hidden, "a member's agent".
- **Where a second agent speaks.** In a room, in the Room's Talk, never in your dock. Your dock is the conversation between you and the agents that are yours. A second agent of your own (a local model for private work, say) is a second ring joined to your mark, chosen in the dock's switcher by the name you gave it.
- **Whispers are readable by the person served.** Tap your agent's ring: **"Everything your agent said, to anyone, is yours to read."** The sheet lists what it offered, what it whispered and to whom (by role), and what was whispered to it (DESIGN-ROOM.md §4.3). No whisper reaches a person who is neither its sender's principal nor its receiver's.
- **A guest's agent never sees your dock**, your margin, your asks or your discernments. What crosses between houses is only what a person brings (DESIGN-ROOM.md §5).

---

## 6. Composition

### 6.1 Hierarchy, top to bottom of the open dock

1. **The head:** your agent's ring joined to your mark, its name, and its state in words (§6.5). Beside it, the switcher (conversations by their first words and their day) and the about-this-agent sheet.
2. **What waits on you:** an open context card, pinned just above the line to speak, so the eye finds it where the hand already is.
3. **The line to speak**, with "About: …" above it when a card is selected.
4. **Your agent's latest turn**, then earlier turns above it (a conversation reads downward; newest at the foot, as the Room's Talk does).
5. **The margin**, on the edge facing The Deal.
6. **The quiet foot** of each finished turn (§6.4), shown on focus or hover, and on long-press on a phone.

### 6.2 The input

- **Text:** Enter sends; Shift+Enter is a new line; ↑ recalls your last words; words said while your agent works reach it at once where it takes them, and wait for its turn's end where it does not. The box always says what your agent is doing.
- **Dictation:** the device's own key, and the Speak pill for a voice note (§4.2).
- **Images and files:** paste or drop, only when the agent declares it takes them (§2.3).
- **`/`** opens the agent's own declared commands, in its own words. **`@`** points at a page or card, when the agent declares it can take one; otherwise the dock inlines the card's title and text.
- **Stop:** a small **Stop** beside Send while your agent works, and Esc.
- **Keys** (joining DESIGN.md §7): `T` opens the dock and puts the cursor in the line to speak · Esc stops a running turn, and on a still dock collapses it · ⇧Tab steps through the agent's declared modes, named in plain words (§6.6) · `?` shows the keys.

### 6.3 Your agent's turn

- **Type:** EB Garamond 400 at `--t-body`, measure 34 rem at most; the player's own words in roman, your agent's in roman too, set apart by the ring at the start of its turn and a hairline above it. Italic is kept for what is offered and not yet agreed, as in the Room (DESIGN-ROOM.md §4.1).
- **Streaming:** words arrive as they come, without a fade per word and without a cursor drawn as light.
- **Thinking folds** to one line in dust ("Thought for about twenty seconds"); open on tap.
- **Tool calls** are rows in dust, one line each, in your agent's own titles ("Reading your notes"), with a diff folded beneath any edit. A row never shows a raw path the player did not ask for (the phone-path skill: do not narrate file paths).
- **The plan**, when declared, is a short checklist, ticked as it goes.

### 6.4 The quiet foot of a finished turn

In dust, at `--t-small`, shown on focus, hover or long-press, never at rest: **Where did that go?** · **Copy** · **Put it in my Deal** (make a card of this turn) · and the discernment gestures of §2.7. Nothing here asks for attention.

### 6.5 States

| State | What the player sees |
|---|---|
| **Ready** | The ring at rest and the line to speak, "Talk to your agent". Nothing moves. |
| **Thinking** | One line in dust under the last turn, in your agent's own words for what it is doing, updated in place; after ten seconds the time in words ("about twenty seconds so far"). No spinner, no dots, no pulse. |
| **Waiting on you** | The context card, pinned above the line to speak; the HUD's top strip reads "Your agent is waiting on you". |
| **Waking** | "Your agent is waking. About a minute." Words only. |
| **Offline** | "Your agent cannot reach its models right now. The Deal below is dealt from what is here." Where the proxy has a route to a model on this computer: "Your agent can still think on this computer, more slowly." And the printed Deal offered: said in one line, with the paper offered. |
| **The agent away** (its process not running, or its computer asleep from the phone) | "Your agent is resting." with **Wake it** on the computer; from the phone, "Your computer is asleep, so your agent cannot hear you." (§4.4) |
| **The agent over-asking** | After four asks in fifteen minutes, once, a quiet line above the card: "Your agent has asked four times in fifteen minutes. Fewer questions?" The asks are counted so the number can be driven down. |

### 6.6 "Fewer questions"

The agent's declared modes, renamed in plain words in the dock's head, and remembered per player per agent:

- **Ask me about everything**
- **Ask me before changes**
- **Ask me only about what leaves this computer**

The dock offers only the modes the agent declares, mapped to the nearest of these three words. A mode that asks about nothing is never on the player's face; it is a steward's setting, behind a steward's key. Whatever the mode, an act that leaves the computer is asked every time (§2.4).

### 6.7 Motion, light and type

- **The dock opens** as a sheet rising over `--d-settle` (240 ms) with `--e-settle`, and leaves with `--e-leave`. The rail widens to the column over the same 240 ms.
- **The ink dries** in the margin over `--d-ink`. Nothing else in the dock celebrates.
- **No drawn light** (DESIGN.md): the ring is a hairline, unlit; no glow for listening, recording or thinking; no halo on a waiting card; no ember. Depth comes from the surface step and the 1 px `--line` edge (DESIGN.md §5.3).
- **No sound**, ever, unasked (DESIGN.md §5.6).
- **Reduced motion:** the sheet appears; the ink changes at once.
- **Large type:** the large scale of DESIGN.md §5.1 (`--t-body` 22 px; the line to speak at 22 px; the context card's buttons 56 px tall); the dock as a full sheet; nothing below 16 px.
- **Contrast:** dust on night 5.4 : 1, as DESIGN.md §5.2 measures it; every state has its word, never colour alone.

---

## 7. Voice

The dock's own copy is the HUD's chrome: second person, plain, warm, short (DESIGN.md §6). Your agent speaks in the first person in its own turns (DESIGN.md §6; `strings.json` `_about`); whether an agent says "I" inside a room's offered line is open (DESIGN-ROOM.md §7), and the dock does not decide it. No contractions except "Here's the deal."; no exclamation; no "not X but Y"; no flattery; "commitment", never the older word; "your agent", never "helper". Every string lives in [`strings.json`](strings.json) under `dock.*`.

**Twenty strings:**

The dock's own copy:

1. Talk to your agent
2. Your agent is waking. About a minute.
3. Your agent is waiting on you.
4. This stays on your computer.
5. This leaves your computer. Your agent will ask you every time.
6. Yes · Yes, for this kind · Not this · Explain first · Put it in my Deal
7. Your agent asked to send the costs to Cell Two. Postponed from Tuesday.
8. Agree · Not this
9. Your words went to a model on this computer. Nothing left it.
10. Your agent is speaking to its models directly. Nothing about where your words go is being recorded.
11. Your agent has asked four times in fifteen minutes. Fewer questions?
12. Ask me about everything · Ask me before changes · Ask me only about what leaves this computer
13. Everything your agent said, to anyone, is yours to read.
14. Your phone becomes a window into this computer. Your computer stays on.
15. Your computer is asleep, so your agent cannot hear you. What you write waits here until it wakes.
16. Your agent cannot reach its models right now. The Deal below is dealt from what is here.

Your agent's opening words (its own, at its first turn of a day; each one written by the agent in its voice; these are the pattern):

17. Good morning. Here's the deal. Two things need you today, about ten minutes, and I will keep the rest.
18. I heard your note from the walk. I wrote it as one line for you to keep or let go.
19. Before I send anything to Cell Two, I will show you the words. Nothing leaves without your yes.
20. That is all I need from you today. I am here when you want me.

**Words the dock never puts on a player's screen:** the agent's protocol, session, token, process, base URL, proxy (say "where your words go"), route, model names, vendor names, prompt, permission (say "asks"), bypass, error codes, holon, event, and the older word for commitment.

---

## 8. What the dock adds to the build

*DESIGN.md §8.1 holds the ground rules (static files, no build step, no framework, every string from `strings.json`, every value from `tokens.css`, fixtures first, stdlib Python only). This section says what the dock adds.*

### 8.1 Files

| File | What it holds |
|---|---|
| [`dock.js`](dock.js) | The pane: the shell mounts it in every layout through the view contract (`create()` → `{mount, update, unmount, key}`), in the slot `"dock"`. The head, the switcher, the turns, the line to speak, the states, the quiet foot, the discernment gestures, "Fewer questions", the ICE and terminal views. It reads `ctx.state.hud.agents` and the conversation stream; it writes only through `ctx.act` (record acts) and through the dock's own calls in `state.js` (§8.2), never by fetching itself. |
| [`dock.css`](dock.css) | The pane's widths, the sheet, the rail, the margin, the ring and its hairline (shared with `room.css`), large type. |
| [`dock-card.js`](dock-card.js) | The context card: built on `card.js`'s compact face; the three answers; the scope sentence for "for this kind"; the "leaves your computer" line; the untrusted mark; the fifteen-minute postponement. |
| [`margin.js`](margin.js) | The record margin: the agent's lines from the state's `lines` and `owed.proposals`, aligned to the turn that made them, with the three ink classes of `base.css` (`.ink-said`, `.ink-kept`, `.ink-agreed`); Agree and Not this through `ctx.act(…, {confirmed: true})`. |
| [`agent_host.py`](agent_host.py) (stdlib) | The long-lived agent host: speaks the Agent Client Protocol (JSON-RPC 2.0, one object per line over the agent's stdin and stdout) to each agent process; keeps each conversation's events on the machine, outside git and outside `record/` (said-kind speech, the speech ruling); listens only on a local socket readable by the player's own user; spawns an agent only when `serve.py` passes the player's confirmed word. |
| [`serve.py`](serve.py) | The bridge: `/agent/*` routes to the host (§8.2); `/discern` passed to the proxy; the phone listener (§8.3); the voice routes (§10). |
| [`state.js`](state.js) | The dock's calls, each carrying the token: `agentSay`, `agentAnswer`, `agentStop`, `agentMode`, `agentWake`, `discern`, `routesOf(turn)`; and the subscription to the conversation stream. |
| [`shell.js`](shell.js) | The `"dock"` slot in every layout, at the widths of §2.1; the collapsed bar and rail; `T` and Esc; the top strip's "waiting on you" line; The Deal's top line held above the open sheet on phones. |
| [`strings.json`](strings.json) | `dock.*`, the twenty strings of §7 among them. |
| [`fixtures/`](fixtures/make_fixtures.py) | Through `make_fixtures.py`: a dock in each state of §6.5; an agent declaring everything and one declaring only text; an ask staying on the computer and one leaving it; an ask from untrusted text; a margin with all three inks; a turn with route lines matched by time; the proxy absent; a guest's agent in a room; the phone paired and the computer asleep; large type. |

### 8.2 The routes

All on `serve.py`, all requiring the page's token (`X-HUD-Token`), all JSON:

- `GET /agent/list` → the agents in `agents.json` with their declared capabilities and state.
- `POST /agent/wake` {agent, confirmed: true} → starts the agent through the host. Refused without `confirmed`.
- `POST /agent/say` {conversation, text, about?} · `POST /agent/stop` {conversation} · `POST /agent/mode` {agent, mode}.
- `GET /agent/stream?conversation=&since=` → server-sent events: the agent's turns, tool rows, plan, asks, state.
- `POST /agent/answer` {ask, answer: yes · yes_kind · not_this · explain · postpone}. A `postpone` writes a card to the player's home through `record.append` (the card's kind `asked`), so it is dealt in the next Deal.
- `POST /discern` {route, verdict, rating?, note?, confirmed: true} → passed to the proxy's own `POST /discern`, signed with the player's key (human-only).
- `GET /agent/routes?conversation=&turn=` → the route lines of that turn, read from the record; never a body. The turn is matched to its route lines by its time window, and the answer carries `matched: "time"`.

### 8.3 The phone binding

- `serve.py --phone` starts, **on the player's confirmed word from the computer's own HUD**, a second listener bound to the machine's private-network address (the address of the private network's interface, found by the kit, never `0.0.0.0`). It is off by default and off after every restart unless the player's layout says `phone: on`.
- **Pairing:** `POST /phone/pair` (from the computer, with the page's token) returns a one-time code, valid for five minutes, shown on the computer's screen as text and as a code for the camera. `POST /phone/claim` {code} from the phone returns a device token; the computer keeps its hash in `<HQ>/.hud-devices` (mode 0600). `DELETE /phone/<device>` revokes it.
- **The phone listener's guards:** Host must be the machine's private-network address or name at its port; Origin its own; every write carries the device token; the same body caps and refusals as the loopback listener.
- **Voice notes:** `POST /voice` (device token, an audio file) → the host runs the local speech model and returns words; the audio is deleted unless `keep: true`.

### 8.4 The security rules

1. **The token.** Every write from the dock carries the page's token on the computer, or the device token on the phone. No route of the dock answers without one.
2. **The agent process is spawned only on the player's word**: a confirmed tap in the HUD, never a page load, never a request from an agent, never anything read.
3. **The dock never widens an audience.** It writes at `holon`; only the publish sheet widens (DESIGN.md §4.10).
4. **An act that leaves the computer is asked every time**; "for this kind" is never offered for it, and no mode suppresses it.
5. **The phone listener binds only to the private-network address**, only on the player's word, and is never reachable from the open internet. The proxy never leaves loopback.
6. **A person's yes is signed with that person's key**, after the undo window; the agent's own lines are signed as the agent's.
7. **Everything an agent sends is data**: rendered as text, never run; no remote image fetched; a request in the agent's words to change a mode, an allowlist, a route or the dock itself is shown to the player as a context card, never applied.
8. **Conversations stay on the machine**, outside git and outside `record/`; only what the player agrees enters the record (the speech ruling).
9. **No sound**: the dock has no audio output path of its own. The one exception is §10's read-aloud, which plays only a reply the player has asked to hear.

### 8.5 State the dock needs

From the server's own `hud` block, proposed (these fields are not yet built):

- `hud.agents`: [{`id`, `name` (the player's name for it, else null), `of` (the person it serves), `kind` (harness · local · guest), `state` (asleep · waking · ready · thinking · waiting · offline · away), `declared` {modes, commands, image, audio, embedded_context, load_session, plan}, `mode`, `asks_open`, `asks_last_15m`, `proxy` {on, last_heard}, `discern_offered` (true once the player has said yes)}]
- `hud.dock`: {`conversations`: [{id, agent, first_words, day}], `rung` (1–5, §3)}
- `hud.phone`: {`listening` (false, or the address), `devices`: [{id, name, added, last_seen}]}

From [STATE.md](../engine/STATE.md): `discernments`, `owed.proposals`, `roles`, `rooms[].present`, `lines`. Asked of STATE.md's open list: `actors[].name` (with DESIGN-WAY-IN.md §9), and `lines[].conversation` where an agent's line was written from a conversation, so the margin aligns without guessing.

**Done when:** on a phone and at 1440 px, from the fixtures and then with a real agent on the machine: the first word arrives in under ten seconds warm with no ask before it; an ask arrives as a card and is answered, explained, and postponed into the next Deal; an agent's drafted commitment appears in the margin in said ink and dries to full ink on the player's Agree; "Where did that go?" names a model on the computer for a private request; a correction in place writes one `discern`; a restart of `serve.py` loses no conversation; the phone pairs, speaks a voice note, and writes through the computer's proxy; the computer asleep is said on the phone; the vendor's desktop app and the terminal each show the rung's line.

---

## 9. The review bar

Judged scene by scene, on a phone in the hand first, then at 1440 px, in night and paper, regular and large type, reduced motion on and off, with the **real** agent, never a stand-in. A stand-in agent proves the shapes; it never proves the experience. The reviewer reads DESIGN.md §9 and the brand's Award Bar first.

**The scenes:** the first word of a new day · an ask that stays on the computer · an ask that leaves it · an ask postponed into the Deal and met again tomorrow · a commitment drafted and agreed from the margin · "Where did that go?" after a private request · a correction made in place · the over-asking line and "Fewer questions" · the agent waking · offline · the proxy absent · the HUD restarted mid-conversation · the phone paired, then a voice note on a walk · the computer asleep, seen from the phone · a room with a guest's agent, and the whisper sheet · each rung of §3 · large type on a phone.

**The first-word clock.** From Send to the first word, warm, timed five times at each of three levels (an experienced player's · a ten-year-old's · a grandmother's on her own phone). Pass: every time under ten seconds; zero asks before the first word. Also measured: asks in the first hour (target five or fewer), seconds from an ask's arrival to its answer, and how often the player chose "Put it in my Deal" (a high number means the cards lack context).

**The one-breath test for "talk to your agent."** After the first minute, without help, each of the three says to a neighbour in one breath what the dock is. Pass: three clauses unprompted: *I talk to my agent right beside my deal* · *it asks me before anything that matters* · *I can see what it put in my record.*

**For every scene, the questions a reviewer asks:**

1. Is The Deal still in view, or did the talk replace it?
2. Did the player leave the ICE or the night ground for anything: another window, another app, another sky?
3. Is anything drawn as light: a glowing ring, a pulsing dot, a halo on a waiting card? Does anything sound?
4. Does the dock look like a messenger (bubbles, avatars, typing dots, read receipts, unread counts)?
5. Would a grandmother know what each ask is asking, and what happens if she says yes, in five seconds?
6. Can anything leave the computer without the player's yes, asked that time? Can an agent agree to anything?
7. Is every agent joined to its own person? Is any other person's agent ever shown as yours?
8. Is every whisper readable by the person its agent serves?
9. On the phone, did every word go through the computer's proxy? Is the vendor's remote control named as the fallback that loses it?
10. Does any line read as an AI wrote it: "not X but Y", flattery, an exclamation, a contraction other than the opener, "helper", the older word for commitment?
11. Is the proxy silent at rest and plain when asked? Is its absence ever quiet?
12. Is discernment captured in one gesture, or did it become a survey?
13. What did we miss that matters most?

A scene that fails 1, 2, 3, 6 or 7 returns. The rest are lifted and passed. The final verdict on beauty and resonance belongs to the player.

---

## 10. The layered voice

The easiest thing is conversation, and most people meet their agent on a phone. The dock carries the best voice it can now, to be improved over time.

### 10.1 Three layers, and nothing voice-only

**Voice, then words, then the card.** Whatever is said aloud is also on the page: the person's words land in the line and then as their turn; your agent's turn streams as text and is read aloud only when it is whole; a question your agent asks aloud still shows its chips, and a chip tapped is the same act as an answer spoken. A person who cannot hear, or will not, loses nothing.

### 10.2 Speak to it

- **The microphone** sits at the line to speak, 44 px, a hairline ring in the ink of the text. **Hold it and let go** to say one thing; **tap it** to keep listening hands-free, and tap again when done.
- **The words appear as they are heard.** Words not yet sure are in dust above the line; sure words are in the line, in ink. The person always sees the words before they go and may change them. **"Send when I let go"** is a preference on this device, off by default.
- **Asked once, in words, with why** ("May I listen?"), before the browser's own question; never on load.
- **Listening is said in words** ("Listening · Tap to stop" hands-free; "Listening · Your words stay on this computer." while held, or "Listening · Let go when you are done" where that would not be true; "Hearing…" while this computer turns a recording into words); the ring fills with ink while it listens. No glow, no pulse, no drawn wave.
- **Where the voice goes, best first:** the browser's own listener held on the device (`processLocally`, where the browser offers it) · the browser's recorder, its audio sent only to this computer's speech command (`serve.py --speech`; deleted after) · the browser's listener that may reach its maker, only when the person has said "Use it anyway" under a plain warning · the phone's own recorder app (a file, when the browser refuses the microphone) · none, and then no microphone is shown. Whether the device path is open is decided by `isSecureContext`, never by the address: over the https phone door (DESIGN-PHONE-DOOR.md) the microphone opens.
- **"Your words stay on this computer."** is said only where it is true; on the phone's own on-device listener, "Your words stay on this phone."; over a listener that may reach its maker, it is not said at all.

### 10.3 Hear it

- **Off by default, kept per device** ("Read your replies aloud" · "Words only", in the about sheet). Never on load: only a turn the person spoke into being from this page is read, so a page opened on a conversation reads nothing of its past.
- **Read when whole, never mid-stream**, once; a question your agent asks is read when it is asked.
- **The voice:** the computer's own, when `serve.py` is started with `--voice` (preferred, as the more natural voice; the contract is in `serve.py`'s header: the words are the command's last argument, it prints the path of a new WAV, the server answers its bytes on `POST /voice/say` and deletes the file); else the device's own synthesis, in the calmest voice on the device (a voice on the device itself, never one that reads over the network; the page's language; a fuller voice before a compact one; never a novelty voice), and the person may pick another ("My voice").
- **"Speaking · Tap to stop"** in dust on the turn being read; a tap stops it.
- **Never in a test:** a page whose `navigator.webdriver` is true, or opened `?muted`, or with `window.__lionsbergMuted` set, never speaks. Chrome's new headless mode, driven over its debugging port, reports `navigator.webdriver` false, so a fixture must set `?muted` (or the flag) and run Chrome with `--mute-audio`; the dock's test proves the guard with `webdriver` set true.

### 10.4 The earpiece rule

While your agent's voice plays, the microphone is closed, so your agent never hears itself. When the person starts speaking (the microphone pressed, or a tap anywhere on the conversation), its voice stops at once. If the person is already speaking when a turn completes, it does not talk over them.

### 10.5 Voice mode: the hands-free loop

- **One switch at the head**, "Voice mode", kept per device, off by default, never offered to a page a test drives, asked once before it first listens. A page opened with it on says "Voice mode · tap Voice mode to listen" and waits for the tap (a microphone never opens on load).
- **The loop:** listening · the words shown, then sent when the person pauses (0.8 seconds by default; "The pause that ends your turn" is a preference: 0.5, 0.8, 1.2 or 2 seconds) · your agent's turn streamed as text · spoken when complete · listening again. Over the server's speech command the loop records short pieces and ends each on the same pause, read from the sound's level (never played; at most thirty seconds a piece).
- **States in words, one at a time,** in large dust: "Listening" · "Hearing…" · "Thinking" · "Speaking · tap to stop".
- **Interruptible:** a tap anywhere on the conversation, or the microphone, stops your agent's voice and listens again. A spoken "stop" or "wait" (alone, or with one other word; the words live in `strings.json` as `dock.voice.mode_stop_words`, so they translate) ends the loop and is never sent.
- **Dim:** "Dim the screen in voice mode" turns the screen to the dark ground with the one state still readable; the screen is held awake while the loop runs (`navigator.wakeLock`, where the browser has it).
- **Leave voice mode**, a quiet link under the state, ends it at once.

---

## Open

1. Whether the dock is open or collapsed by default on a desktop on day one.
2. Whether an agent says "I" inside a room's offered line (DESIGN-ROOM.md §7); the dock's own turns use the first person, as DESIGN.md §6 does.
3. The words "Put it in my Deal".
4. Whether the over-asking line appears at four asks in fifteen minutes, or at another count.
5. Whether discernment capture is offered on day one, or dealt as a later card.
6. The kit's choice of private network, which this page names only by its role.
7. Which voice is your agent's: the computer's own voice (`--voice`), a chosen local voice, or the device's calmest.
8. Whether your agent should ever hear the room (a space's live talk), and on whose word.
9. Whether "Send when I let go" should be on by default on a phone.
10. Whether the pause that ends a turn should learn from the person instead of being set.

## Not yet built

- Joining a turn to its route lines by the conversation's id and turn number, carried to the proxy by the harness's custom-header setting where the harness has one, and written on the `route` line as two optional fields, `conversation` and `turn`. Until then every turn is matched by its time window.
- A home-screen copy of the page that holds the last state, for the phone while the computer sleeps.
- A wake word (the microphone opens only on the person's tap).
- A vendor's voice or a vendor's listener as a default.
- Hearing the person while your agent speaks. True barge-in needs the device's echo cancellation proven first; until then the microphone is closed while your agent speaks, and a tap interrupts.
- Streaming your agent's voice sentence by sentence before the turn is whole.
- Installing a language for the on-device listener (a browser download, said and asked before it happens).
