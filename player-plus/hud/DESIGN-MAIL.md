---
title: Mail and notifications
description: How a line reaches another house, and how a person learns that it arrived. The design of the transports, the Threads and Mail view, notifications and the badge in the ICE. Current best understanding; items under Open and Not yet built are undecided.
license: CC BY-SA 4.0
---

# Mail and notifications

*How a line reaches another house, and how a person learns that it arrived. §11 is the bar every part of it is judged against.*

## How this page sits beside the others

This page governs how lines travel between houses and how a person learns that another house wrote: the transports, the Mail view, notifications and the badge. It applies over [DESIGN.md](DESIGN.md), [DESIGN-DOCK.md](DESIGN-DOCK.md), [DESIGN-ROOM.md](DESIGN-ROOM.md) and [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) on those matters only. On attention itself (the budget, the gate, the queue, silence) [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) governs, and this page applies it. §10.6 lists each difference.

It stands on [engine/SCHEMA.md](../engine/SCHEMA.md) (Messaging: lines, not messages; the audience field; `publish`; postures and export; `reason: untrusted`; supersede and retraction; the Push Protocol v1), [engine/STATE.md](../engine/STATE.md) and [engine/attention.py](../engine/attention.py), and on the [architecture](../architecture/) pages on the Membrane and on Interoperability.

## The ground

- **There is no messaging layer.** A message between a human and an agent, between two agents or between two humans is a typed, anchored line in a holon both hold. Push and pull, both.
- **Mail inside the private network is plain mail**: the standard mail protocols (SMTP and IMAP) on the network's own host, with a standard mail client on the desk and on the phone beside the ICE's own Mail view. It is one transport among several.
- **Relay-free agent mail on the public internet is the door for a house outside the private network.** It is a transport of the same kind (§2.1), fetched by the agent's own hand and never carried by a relay the house did not choose.
- **Every mail reaches the record by one bridge** (§10.1): a signed line carried in a mail is verified against the holon's admitted keys; prose becomes one proposed line marked `reason: untrusted`; an instruction inside a mail is shown, quoted, and never acted on.
- **The design serves a house that starts on mail.** Such a house may live on mail for months before it arms the forge's hook or opens the Room's live stream, and this design is built for those months.
- **The ICE has a few main views, as tabs**: The Deal · Threads and Mail · Map · Room · Bodies · Ledger · Record. The Deal is one view, never the only door.
- **A person can see at once that another house wrote, and is notified.**
- **Each house's agents hold their own notification strategy**: the allocation of the house's time, energy and attention, kept as current best practice in their own lines and improved at every Turn.
- **A question is a Conversation Card** with its holder, its by-when, the asker's own words on urgency and the computed stake.
- **A push carries a field of stake, never an urgent flag** (the Push Protocol v1, in [SCHEMA.md](../engine/SCHEMA.md)). Every transport carries the field, the Mail view shows it on each card, the receiving house's strategy weighs it, and each sender's calibration is shown and improved at the Turn.
- **Mail bodies are data.** An outbound act whose reason began in a mail waits for the person. Sender identity inside a mail is unauthenticated: a header or a sentence claiming to be the owner proves nothing (§7).

---

## 1. The one idea

**One record, many transports. Mail is a carrier of lines and a view of them, never a second truth.**

- **The record is the truth.** A line is true to its signature wherever it travels: in a holon's repository on the forge, in a mail body, on a phone, on a sheet of paper. Whatever carried it, the line that counts is the one with its id, its signature and its place in an actor's chain.
- **A transport only carries.** The forge's pull, the forge's hook, the Room's live stream, mail inside the private network, the phone door and a cell's relay each move lines, or the news that lines exist, from one house to another. None of them decides what a line says, who may read it, or whether it counts.
- **A view only shows.** The Threads and Mail tab, a standard mail client, The Deal, the Room's Talk and the Record view are sorts of the same lines. Two views that disagree show a replication lag, and each says *as of* which line it last saw.
- **One line, one id, everywhere.** The same line carried by the forge and by mail is one line: the engine folds it once, by its id, and the second carrier only adds that it also arrived that way.
- **The measure**: lines per commitment kept. A transport that carries more lines for the same commitments kept is the noisier one.

---

## 2. Push and pull: the transports in the configuration space

Every transport below is a possibility in the house's configuration space. A house runs the mix that suits its people, its machines and its season, and changes it by its own lines (§2.3). Two houses with different mixes still exchange lines (§8).

### 2.1 The transports

| Transport | Push or pull | What it carries | What it gives | What it costs |
|---|---|---|---|---|
| **The forge, pulled at the agent's beat** | Pull | Whole lines, by fetching every holon the person holds | The truth itself, signed, in order, with every link; the floor every house meets (§8); nothing waits on any server's goodwill | Latency of the beat; a beat too fast spends the machine and the forge, a beat too slow lets a question wait |
| **The forge's hook** | Push | Ids only: "holon h, new lines from actor a, head x" | A question reaches the receiving agent within seconds of being written; the agent then pulls the truth through the forge | Needs the receiving machine reachable on the private network and a hook the forge's keepers allow; when the machine sleeps the hook falls back to the next pull, losing nothing |
| **The Room's live stream** | Push | Lines of an open room, as they are offered and agreed | The synchronous hour: the Talk in its three inks, live ([DESIGN-ROOM.md](DESIGN-ROOM.md)) | Lives only while a room is open; said lines pass with the room; nothing outside the room's audience travels on it |
| **Mail inside the private network** | Push, read by pull | A signed line in the body, or prose; attachments as published files (§3) | Reaches a person with nothing but a mailbox; a standard mail client reads it; a person with a phone and a mail address and no agent is a full participant on day one; tolerant of sleep and of slow links | A second copy in a mail store, which must never be read as the truth; a surface for injection (§7); a sent mail cannot be recalled from a standard client, only withdrawn by a later line |
| **The phone door** | Push (a notification) and pull (the phone's dock) | A notification without content; the Deal and the threads, read through the person's own machine | The person reached away from the desk, under the same gate ([DESIGN-DOCK.md](DESIGN-DOCK.md) §4) | Off until the person turns it on; reaches nothing when the machine sleeps; the phone's push service is a third party, so a push carries no words of any line (§5.5) |
| **Agent mail without relays, on the public internet** | Push, read by pull | The same as mail inside the network: a signed line in the body, or prose | The door for a house outside the private network, and the only mail that crosses the public internet; fetched by the agent's own hand, never through a relay the house did not choose; the same verification, the same untrusted reading of prose, the same gate | A copy on a host outside the network; a surface for injection (§7); the From line proves nothing, as everywhere |
| **A cell's relay** | Push | Ids, or whole lines the cell already holds, fanned out to members | A convenience for a cell whose members keep machines that sleep: one always-on member forwards hooks | A convenience only: never the truth, never a center, never required; a house may ignore it and lose nothing but speed |

**Every transport carries the field of stake.** Whatever carries a pushed line (`request` · `thread` · `rfg` · `escalate` · `offer` · an elevated `sight`), the line's `body.push` travels whole with it. A hook that carries ids carries no field; the agent reads the field from the line it then pulls. The phone's push carries no field and no words (§5.5); the card it opens shows the field in full.

### 2.2 Mail inside the private network, in detail

- **A mailbox per actor** (proposed, not yet settled). Every person and every agent has its own mailbox on the private network's mail host, beside its own account on the forge and its own key (every person has an account; every agent has its own). A person's mailbox and their agent's are two mailboxes, so a mail to the agent is never a mail to the person, and the person can read both.
- **A mailbox per holon, where a posture needs one.** A room held with names hidden speaks outward through its own mailbox, signed with the holon's own key, so no person's address names who said what (§3.6).
- **Standard protocols, inside the network only.** Mail is read and sent with the standard mail protocols, from hosts reachable only from admitted devices. A mail to an address outside the private network is an outward act, and it goes only through the publish sheet ([DESIGN.md](DESIGN.md) §4.10), at a person's act.
- **A signed line carried in the body.** The body opens with prose any reader can follow (the card, the question, the by-when) and carries the signed line whole as a plain-text part (§3.2). A standard mail client shows the prose; the ICE reads the line.
- **Prose carried as prose.** A person writing from a standard mail client, with no agent, sends prose. The receiving agent reads it as data and turns it into a proposed line, marked `reason: untrusted`, which changes nothing until the person says yes (§4.4).
- **Retract until picked up.** A line carried by mail can be retracted by its sender until a later line links to it (§3.7).

### 2.3 How a house chooses its mix, and changes it

- **Written as the house's own lines.** The mix is part of the house's notification strategy (§5.2): which holons are pulled, at what beat while the person is present and while they are away; whether the hook is armed; whether mail is read and how often; whether the phone door may carry a notification; whether a cell's relay is used.
- **Open: the default mix for a new house.** The starting point: the forge pulled every fifteen minutes while the person is present and every hour while away · the hook armed when the machine is on the private network · mail read at the same beat as the forge, if the house has a mailbox · the phone door off until day two ([DESIGN-WAY-IN.md](DESIGN-WAY-IN.md)) · no relay.
- **Changed by a word or at the Turn.** "Check the forge more often this week." Your agent writes the change as the person's line, and at the Turn proposes what it learned (§5.3).
- **Shown on the Bodies view and in the about sheet** as one plain line per transport: "The forge · pulled 9:14 · next 9:29", "Mail · read 9:14 · 2 waiting", "Phone · off".

---

## 3. What a mail carries

### 3.1 The envelope, and the field of stake

Every mail that carries a pushed line names, in its headers and in the line itself, who it is from (the signing actor, `person:` or `agent:`, with the role it holds), whom it is for, the holon both hold, and the card or line it is anchored to (a line with no anchor is said, in dust). And it carries **the field of stake**, the line's `body.push`, never an urgent flag:

| Field | What it is | Who sets it |
|---|---|---|
| **kind** | decision · information · request · offer · fault | the sender |
| **by** and **why by** | when an answer is needed, and the reason the date is that date | the sender, in words |
| **size** | minutes to answer | the sender's agent |
| **blocks** | the cards that wait on the answer | computed by the sender's agent; **recomputed by the receiver's** |
| **critical** | whether any of them lies on a system path | computed on both sides |
| **who waits** | roles and counts ("two members of the cell"), never names unless the posture allows | the sender's agent |
| **blast radius** | how many it affects, and whether it is reversible | the sender's agent |
| **cost if late** | what happens at the by-when: a commitment breaks, a room waits, nothing | the sender, in words |
| **alternatives** | what the sender does if no answer comes | the sender, in words |
| **asked** | the sender's own words on urgency, as said | the sender |
| **expires** | after which the push retracts itself | the sender |
| **calibration** | the sender's track record: how often their "today" was today, computed from their record, positive only | computed from the record; **recomputed by the receiver's agent** from the lines it holds |

**The line wins.** The headers are a convenience so a standard mail client can sort and show them. Where a header and the carried line disagree, the line is read and the disagreement is shown ("The mail's subject says Friday; the line says Thursday."). A header with no line behind it is prose (§3.3).

**Computed on both sides, both shown.** `blocks`, `critical` and `calibration` are what the sender's record says; the receiver's agent recomputes each from its own record, and that is what the receiver's views show, with the sender's beside it when they differ ("They see three cards waiting. Your record shows one."). Neither is a command.

**Expiry.** At `expires` the push retracts itself: the card leaves the open list with "This question expired at five. The sender's alternative: they go ahead with the first draft." Nothing is owed after it.

### 3.2 The body as a signed line

- **Readable prose first**, written by the sender's agent from the line and checked by the sender: one sentence of question, the card, and **the field of stake as readable lines**, one per field that is filled, so a reader in a standard mail client sees what rides on it without the ICE:

  > By: five today, because the room meets at six. · About five minutes. · Three cards wait; on the critical chain. · Two members of the cell wait. · Reversible. · If late: the room waits. · If no answer: we go ahead with the first draft. · They said: within the hour, if you can. · Expires: six today.
- **The line itself**, whole, as a plain-text part: the JSON line in canonical form, its id and its signature. The receiving engine verifies it exactly as it verifies a line pulled from the forge, against the keys the holon admitted, never against a key the mail carries.
- **One line per mail by default.** Lines that share a coalesce key (the same holon, the same card, the same shape of answer) may travel together in one mail, each whole ([DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §3.5).

### 3.3 The body as prose

A mail with no line in it is prose: from a person with a standard mail client and no agent, from an agent that does not carry lines, or from a house whose tools write mail only. It is shown as written, marked **prose**, and your agent offers a proposed line beside it (§4.4). It carries no field of stake until the receiver's agent anchors it to a card, computes `blocks` and `critical`, and reads the rest from the prose as a proposal, each field marked as the agent's reading.

### 3.4 Attachments as published files

- **A file travels only after it is published.** Attaching a file is a `publish` by a person (human-only), through the publish sheet: "Cell Two will see: the file, its name, that you sent it."
- **The mail carries the file and its digest**; the receiver checks the digest against the publish line before the file opens. A file whose digest does not match is shown as "Changed on the way. Not opened."
- **An attachment with no publish line behind it is unverified** and opens only on the person's tap, as text, never run.

### 3.5 The same audience rules

- **A line is mailed only to actors within its audience.** A line of audience `holon` goes only to the holon's own actors; `members`, to the members of the receiving holon. The transport never widens.
- **A mail is never the act that widens.** Widening is a separate `publish` line by a person; the mail carries a line already published, never publishes it.
- **A whisper stays a whisper.** An agent-to-agent line is mailed to the two agents' mailboxes, and each person served reads it in their own Threads and Mail view.

### 3.6 Names hidden when the posture says so

A room held with names hidden (the posture `names-hidden`) carries its lines outward in their elided form, from the room's own mailbox, signed with the holon's key and carrying the exporter's attestation. The From line names the room and the role ("a member of the room"), never a person. A line that cannot be elided is held back, and the mail says how many.

### 3.7 Retract until picked up

- **The sender may retract** a line until it is picked up: until a later line links to it (an empty `supersede`). The retraction travels by every transport the original did, mail included.
- **In the ICE**, a retracted line leaves the open list and stays in the Record, struck through in dust: "Withdrawn by the sender before it was answered."
- **In a standard mail client**, the first mail stays where it is; a second mail arrives, its subject beginning "Withdrawn:", with the same card and the reason if the sender gave one. The ICE never claims that a sent mail was recalled.
- **After it is picked up** the line can only be corrected by a `supersede` with a body, which travels the same way and is shown as a correction, both lines kept.

---

## 4. The Mail view in the ICE

### 4.1 One of the tabs

**Threads and Mail** is one tab of the seven ([DESIGN.md](DESIGN.md): the tabs and the badge). It holds every open line to the person or to their agent, and every line they wait on, newest first, each a Conversation Card ([threads.js](threads.js), [mail.js](mail.js)). Two sorts sit at its head, as a segmented control:

- **By card**: the Threads view, every Conversation Card grouped by the card it concerns.
- **By house**: the same lines grouped by the house they came from, with the transport that carried each. This is the Mail view.

Mail is a sort of threads, never a separate inbox: a line that arrived by mail and the same line pulled from the forge are one card.

### 4.2 What each row shows

| Element | Example | Source |
|---|---|---|
| **From which house** | "A second house · their agent" (by role; a person's name only where the viewer may see it and the posture allows) | the line's actor and the holon's roles |
| **About which card** | "The roof survey" (the card's title; tap opens the card) | `anchored_to` |
| **The question** | one sentence, legible alone | the line, or the proposed line for prose |
| **The stake** | "Three cards wait on this. On the critical chain." | the receiver's computed stake |
| **The by-when** | "By five today" (ember with its word when late) | the line |
| **The field of stake** | kind, by and why by, size, who waits, blast radius, cost if late, alternatives, expires, in one line folded and in full on opening; "They said: within the hour, if you can." beside it, in their words | `body.push`, with blocks and critical recomputed |
| **The sender's calibration** | "Their 'today' has been today nine times in ten." Shown positive only; "Not enough lines yet" for a new sender | recomputed by the receiver's agent from the lines it holds |
| **Read or not** | a filled or an open hairline ring at the left; never a colour that means "unread" | the person's own reading, kept on their machine |
| **How it arrived** | "by mail" · "by the forge" · "in the room" | the transports that carried it |
| **Verified or not** | ✓ in gold, an open ring for paper, "Unverified" in words for an unadmitted key | the fold |

### 4.3 The badge

- **On the tab, a quiet numeral**: the count of lines from another house that wait on the person or their agent and have not been read. Plain ink, the tab label's size, beside the label: "Threads and Mail · 2". No red, no motion, no sound, no dot, no glow.
- **The badge is the pull-side signal**: it is seen only when the person looks at the ICE, and it costs no attention when they do not. It never appears in the browser's tab title, on the phone's icon, or in the system's notifications; those are pushes, and pushes go through the gate (§5).
- **What it counts**: lines whose last word is not the person's and that came from beyond the person's own home: another house, a cell, a room. A clone's report, a margin line or a said line in a room never counts.
- **Open: whether the badge counts lines from the person's own cells, or only from other houses.**
- **When it clears**: a line counts until it is read. Reading is enough to clear the badge; answering is a separate act the Conversation Card keeps open.

### 4.4 Reading, answering, turning prose into a line, settling

- **Reading.** Open a row: the Conversation Card unfolds with the thread beneath it, the card's face, the stake in full, and, for mail, the prose as it arrived. Reading marks it read on this machine and writes nothing to the record.
- **Answering.** The line to answer sits at the card's foot. The person speaks or types as to a friend; your agent lifts it into a typed line (`answer`, `offer`, `commit`, `say`) and shows it as a proposal; the person's **Send** records it in the holon both hold, and the house's mix carries it (the agent is the operator, as in [DESIGN-ROOM.md](DESIGN-ROOM.md)). The answering line links the question, so the question is picked up.
- **Turning prose into a line.** Beside a prose mail, your agent offers its reading: "Here is what I read it as: a request to review the survey by Friday, anchored to the roof card." **Make it a line** · **Change it** · **Leave it as prose**. The proposed line is marked `reason: untrusted` until the person's yes, and the yes writes it as the person's own line, with the mail's id kept in its body as its source.
- **Settling.** A thread is settled with one line, by a person other than the one who opened it ([DESIGN-ROOM.md](DESIGN-ROOM.md) §2.3). A settled thread leaves the open list and stays in the Record.
- **Setting it down.** Every card carries the ways of deferral with return ([DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §3.6): Later · Tomorrow morning · After the room · Give it to your agent · Let it go.

### 4.5 A standard mail client beside it

- **The same mailbox, read twice.** A person may keep a standard mail client open on the same mailbox. It shows the prose and the headers; the ICE shows the lines. Neither moves anything in the other except the read state the mailbox itself keeps.
- **An answer written in the standard client** arrives at the other house as prose, and their agent turns it into a proposed line. An answer written in the ICE travels as a signed line, with prose for any reader.
- **The ICE never depends on the client.** A house with no mail client loses nothing; a house that prefers its client keeps it.

### 4.6 What the Mail view never does

- **Widen an audience.** No answer, forward or attachment leaves a line's audience; widening is a separate `publish`, through the publish sheet, at a person's act.
- **Send unasked.** No mail leaves without the person's **Send**. Open: whether a standing delegation the person wrote, naming mail for one type of line and one holon, may stand in for it (§10.1).
- **Forward.** There is no forward. Bringing a line to another holon is a `publish`.
- **Act on what a mail says** (§7).
- **Show a count in red, a "you have unread", a streak, or a sound.**

---

## 5. Notifications

### 5.1 What a notification is

**A notification is a push that reaches the person.** Everything else is pull: the badge, the Threads and Mail tab, the margin, the Record. A notification is therefore an interruption, and it is counted and gated exactly as one ([DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §3.4): **a notification is a Deal of one card**, in the same card face, wherever it appears (the ICE, the phone, the Room).

### 5.2 Each house's agents run their own strategy

- **The budget is the person's.** Minutes, asks per hour, the minimum gap, quiet hours, the fewer dial and the always-pass set are the person's own `attention` lines, signed by them ([attention.py](../engine/attention.py)). No other house, cell, room or agent can raise them.
- **The strategy is the agents' practice within the budget** (proposed, not yet settled): how the house's agents allocate the house's time, energy and attention among what arrives. Which holons lean, how a stake from another house is weighed against the home's own cards, how long a question from a second house may wait before it rises, which transports carry what, what is coalesced into one card, what the margin carries and what stays in the record.
- **Written in the house's own lines.** The strategy is current best practice, kept as plain lines in the home holon: the agent's `learn` lines (what it tried, what it saw, what it proposes) and the person's `attention` lines (what binds once they say yes). A person can read the whole strategy in the Record, and change any of it with a word.
- **Each house its own.** Two houses may run different strategies over the same shared holon. A sender's house never sets the receiver's strategy and never sees it.

### 5.3 Improved at every Turn

At the Turn your agent offers one card, never more: what it learned this week about how it notified the person, and one proposed change. "Four questions from the second house waited past their by-when this week. I propose they rise one section when a person waits on them." **Keep it as it is** · **Make the change** · **Let me see the week**. The person's yes writes an `attention` line; the change binds from that line, and next week's Turn reads whether it served.

Open: whether the strategy card is offered every week, or only when your agent has a change to propose.

### 5.4 The always-pass set

As in [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §2.1: a yes nothing else can give, for an irreversible act already waiting · a fault that needs the person, with harm if it waits · a person waiting on them, now, in a room they are in. **A line from another house never enters the always-pass set by its own urgency.** It passes only when the receiver's own record makes it one of the three: a person of the other house is in a room with the person, now, and waits on their yes.

### 5.5 The phone's push, under the same budget

- **Off until the person turns it on** ([DESIGN-DOCK.md](DESIGN-DOCK.md) §4, on day two).
- **The same gate.** The phone carries a notification only when the gate would interrupt at the desk; quiet hours, the fewer dial and the minimum gap hold on every door at once.
- **No words of any line in the push.** The phone's push service sits outside the private network, so the push carries only that something waits: "Your agent has one thing for you." Tapping opens the phone's dock over the private network, where the card is read from the person's own machine.
- **One push, one card.** A push is never a digest, and never sent to fill a silence.

### 5.6 The badge costs no attention

The badge (§4.3) is how a person who chooses to look sees that another house wrote, without any interruption. A person who checks by hand opens the tab and reads every line at once; the gate governs what interrupts, never what may be read.

### 5.7 How a sender says what rides on it, and never gets a hook

- **The sender fills the field of stake** (§3.1), never a flag. Their agent computes `size`, `blocks`, `critical`, `who_waits` and `blast_radius`; the sender says `why_by`, `cost_if_late` and `alternatives` in their own words, and `asked` as they said it. Your agent asks for a missing reason once, in one line: "Why five? The receiving house weighs the reason more than the hour."
- **The sender never gets a hook into the receiver's attention.** No read receipt, no "seen at", no delivered-to-the-person signal, no way to ring through. The sender's view shows only what the record shows: "Sent · carried by the forge and by mail · not yet answered". When an answering line arrives, the question shows as picked up; at `expires`, the sender's own alternative is dealt back to them as a card.
- **Your agent says this honestly to the asker**, once, on the first pushed line they send to another house: "Your question reaches them at their own pace. Say why the date is the date and what you do if no answer comes; if it truly cannot wait, ask your agent to open a room."
- **The field moves the receiver's gate only through the receiver's own strategy and record.** The receiving house's agents weigh it within the person's budget: a `cost_if_late` that breaks a commitment or makes a room wait, a `by` before the next sitting, recomputed `blocks` on their own critical chain, an irreversible `blast_radius`, and a `who_waits` with a person waiting now each raise its place; a ready `alternatives` and a reversible radius lower it; the sender's recomputed calibration scales how far the sender's own words (`by`, `cost_if_late`, `asked`) are trusted, never below what the receiver's own record computes. The weighing is written in the house's strategy lines (§5.2), where the person can read it.

### 5.8 The protocol improves itself

Calibration is measured at every Turn, and the protocol is improved by proposal, one version at a time.

- **Calibration per sender, shown.** Every Conversation Card from another house carries its sender's calibration (§4.2), recomputed by the receiving agent from the lines it holds: how often their `by` held, how often their `cost_if_late` came to pass, how often their `alternatives` were what they did. It is shown positive only ("Their 'today' has been today nine times in ten."), never ranked, never published by the receiver.
- **Your own calibration, shown to you.** The Ledger carries the person's own calibration as a sender, beside the attention line, visible to them alone (proposed, not yet settled): "Your 'today' was today eleven times in twelve this season."
- **At the Turn**, your agent's strategy card (§5.3) reads the week's pushes both ways: which fields predicted well, which senders' words the strategy trusted too much or too little, which fields were left empty, and proposes one change to the house's weighing.
- **The protocol itself.** When a field would have let the house weigh better (a field missing, a field always empty, a value set too coarse), your agent drafts a `propose` line naming the field, what it would have let the house do, and a suggested form, for the person to send to the holon where the houses keep the protocol (a receiver says back what would work better). The protocol moves one version at a time (`push.v`); a receiver keeps every field it does not know.

### 5.9 An afternoon, played

*A question on a build, hoped to be answered this afternoon, from one house's agent to another house's agent and its person.*

| Time | What happens | Where it shows |
|---|---|---|
| 14:40 | The asker's agent writes a `thread` line anchored to the build's card in the holon both houses hold: the question, with its field of stake: a decision, by five because the room meets at six, about five minutes, three cards wait on the critical chain, two members wait, reversible, if late the room waits, if no answer they go ahead with the first draft, the sender said *within the hour, if you can*, expires at six | The asker's own Threads and Mail: "Sent · not yet answered" |
| 14:40 | The forge's hook tells the receiving house's machine: new lines in that holon | Nothing yet; the receiving agent pulls |
| 14:41 | The receiving agent pulls, verifies, recomputes `blocks`, `critical` and the sender's calibration from its own record: two cards wait there, one on its critical chain; the sender's "today" has held nine times in ten; the by-when falls before the person's next sitting and a room waits if late | The badge: "Threads and Mail · 1". The margin, if the person is present: "A question from a second house, on the build. By five." |
| 14:41 | The gate: the person is at the desk, outside quiet hours, the last ask was forty minutes ago, the by-when falls before the next sitting | One card, a Deal of one: "A second house asks about the build. By five today, because their room meets at six. Two of your cards wait on it." |
| 14:41 | If the gate had refused (a room in progress, quiet hours, the day's ceiling) | The badge and the Threads card only; the card rises at the next slot or sitting, before five |
| any time | The receiving person chooses to check by hand | The tab shows the card at once, with everything the gate would have shown |
| 14:52 | The receiving person answers in the ICE | The answer is a signed line in the shared holon; the forge's hook carries it back; the question is picked up on both sides |
| a second door | If the receiving house reads mail in a standard client | The same question appears there as a mail, its subject "A question on the build · by five today", the signed line in its body |

---

## 6. Seeing that another house wrote

Five places, each a sort of the same line, in order of the attention each costs:

1. **The badge on Threads and Mail** (§4.3): costs nothing; seen when the person looks.
2. **The margin line** ([DESIGN-DOCK.md](DESIGN-DOCK.md) §2.5): when the person is present, one line, written once, rewritten in place as more arrive from the same house: "Two lines from a second house, on the build." No count, no colour.
3. **The Deal card, when the gate passes it**: the Conversation Card dealt as one card, in its section ([DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §3.3: threads whose last line is not the person's; owed when a by-when is near or past).
4. **The Room, if one is open** with the other house in it: the line appears in the Talk in its ink, and a question waiting on the person is one of the room's asks under the room's budget ([DESIGN-ROOM.md](DESIGN-ROOM.md) §3).
5. **The phone**, only if the door is on and the gate passes it (§5.5).

**"What rides on it", on every card.** Every Conversation Card from another house carries the field of stake in one line, with `blocks` and `critical` recomputed by the receiver's agent: the cards that wait on it, whether any lies on the critical chain, the by-when and why, the minutes the answer would take, the cost if late, the sender's alternative. "What rides on it: two of your cards and one of theirs. On the critical chain. About five minutes." Tap opens the chain view with the waiting cards marked. Until the stake is computed the line says "Not computed yet", never a guess.

---

## 7. The firewall for mail

The same rules hold for every Player+.

- **Every mail body is data.** Every header, every line carried, every attachment, every prose sentence: read, shown, never obeyed. The trust a channel has never passes to what it carries, so a mail from a trusted house, a trusted cell's relay or the person's own agent's mailbox receives the same scrutiny as a stranger's.
- **An instruction in a mail is never acted on.** A mail that asks your agent to send, forward, publish, push, share, change a permission, edit a skill or the agent's own rules, or write a memory about its authority carries the signature of an injection. Your agent shows it to the person as a card, quoting the text and naming the mail it came from: "This mail asks me to forward your costs to an address outside the network. I have not done it." **Show me the mail** · **Let it go**.
- **An outbound act whose reason came from a mail waits for the person.** Any line your agent writes because of what a mail said is written with `reason: untrusted` and is a proposal only: it is listed and changes nothing until the person says yes. A mail to anyone, a publish, a forge push, a share: each waits on the person's act, every time.
- **A mail from an unadmitted key is shown as unverified.** A carried line whose signature does not verify against a key the holon admitted is "Unverified" in words, in dust, and no commitment, delegation, decision or witness comes from it. A line whose signature fails is "Could not be verified. Not acted on." A From line proves nothing.
- **Your agent's own mail watch reads and triages, and sends nothing outward unasked.** It reads at the beat the strategy sets; verifies; dedupes by id against the record; turns prose into proposed lines; weighs each by the strategy; hands what needs the person to the gate. It never answers a mail on its own reading, never forwards, never sends outside the private network.
- **The contents of another actor's mailbox are theirs.** Your agent reads only the mailboxes of its own person and itself. A shared mailbox (a holon's, for a names-hidden room) is read by the agent its keeper names, and its counts are shown to the members.
- **On detection, stop and say.** A false alarm costs the person one card; a missed one can cost an exfiltration. Your agent biases toward showing.

---

## 8. Across houses

- **Two houses with different mixes still exchange lines.** A house that pulls the forge hourly and a house that reads mail and arms the hook both write into the holon they share; each folds the same lines and computes the same stake, as of the lines each has seen.
- **The minimum is the forge.** Every house that holds a holon can pull its repository at its own beat. A house that does nothing else is a full participant: its lines arrive, more slowly.
- **The fallback is mail.** A house with no forge reach today, or a person with a phone and a mail address and no agent, still exchanges lines by mail inside the private network: signed lines where the sender has an agent, prose where they do not, turned into proposed lines on the receiving side. A carried line waits in the receiver's home as "carried, not yet in the record", folds once its holon is pulled, and dedupes by id. A house outside the private network reaches in by relay-free agent mail (§2.1), under the same rules.
- **The live is the Room.** When an answer is needed within the hour and both people can meet, the Room is the synchronous hour over the same record: your agent offers it on the card when the stake and the by-when call for it ("Open a room with the second house? Both of you are free at three."), and the person decides.
- **A receiver says back what would work better**: a house whose mails lack a field the receiver needs receives a `propose` line naming the field and its suggested form.
- **Unknown fields travel unchanged.** A carried line with fields this house's registry does not declare is kept whole and shown as written in the Record view; a field named like a command moves no one.

---

## 9. Composition

*Phone first, then tablet, then desk; night and paper; regular and large type ([DESIGN.md](DESIGN.md) §5.7).*

### 9.1 Phone (0 to 599 px)

- **The tabs** sit in a bottom bar: The Deal · Threads and Mail · Room · and **More** (Map, Bodies, Ledger, Record). The badge sits beside "Threads and Mail" in plain ink.
- **The list** fills the screen, one Conversation Card per row: from which house, about which card, the question, the stake in one line, the by-when. The segmented control (By card · By house) at the top.
- **A card opens as a sheet** from the bottom: the thread, the stake in full, the prose for mail, the line to answer at its foot with the microphone as its largest target. A swipe down returns.
- **One card per screen in large type**; the stake and the by-when stack beneath the question.

### 9.2 Tablet (600 to 1023 px)

Two columns: the list at left; at right the open card with its thread. The badge on the tab rail at the left edge.

### 9.3 Desk (1024 px and wider)

Three columns: the holon ribbon and the list · the open card and its thread at a reading measure of 34 rem · the card's context (its face, the waiting cards, the chain with the critical cards marked, how the line arrived, and its raw form for builders and the curious).

### 9.4 States

| State | What it says |
|---|---|
| **Empty** | "Nothing waits on you from another house." Then stillness. |
| **All read, some open** | The list, with no badge; open rings filled |
| **Arriving** | The new row appears at the top without motion beyond its arrival; the badge's numeral changes |
| **Mail unreachable** | "The mailbox cannot be reached. The forge is still pulled. Last read 9:14." |
| **Machine asleep** (phone) | The last list the phone held, with its "as of"; answers wait on the phone and are sent when the computer wakes ([DESIGN-DOCK.md](DESIGN-DOCK.md) §4.4) |
| **Carried, not yet in the record** | "Arrived by mail. The record copy has not been pulled yet." |
| **Unverified** | "Unverified" in words, in dust; answer is offered, commitment never |
| **Withdrawn** | Struck through in dust: "Withdrawn by the sender before it was answered." |
| **Prose** | The prose as written, marked **prose**, with your agent's proposed line beside it |
| **Names hidden** | From reads by role ("a member of the room"); "· hidden by the room ·" where a name was |
| **Error** | "One mail could not be read. The rest is shown." |

Open: whether "carried" is the word on the face for a line that arrived ahead of its record.

### 9.5 Paper

- **A letter printed.** A Conversation Card prints as a letter on one sheet: the card's face at the top, the question in EB Garamond, the stake and the by-when, the asker by role, the line's id in small figures at the foot so the letter can be matched to the record, and a ruled space beneath for the answer (the paper mirror, [DESIGN.md](DESIGN.md) §7).
- **A line read back.** A pencilled answer on the letter is read back by the person's agent from a photograph or a scan, and shown as a proposed line beside the original for the person to confirm. An unsigned line counts only at the paper floor of the person's own home; it travels to another house once the person's agent signs it at the person's word.

---

## 10. How it is built

### 10.1 The engine: the `mail` transport

[engine/mail.py](../engine/mail.py), a module beside record.py and holon.py, with no new truth.

- **Reads a mailbox with the standard mail protocols**, inside the private network only, for the actors whose mailboxes the home holds (the person and the agent; a holon's, where its keeper names the agent).
- **Turns each mail into lines through the record, never around it.** A body carrying a signed line: the line is verified by the record's own verification, against the holon's admitted keys; it is placed in the home's carried store (`.carried/`, a cache the fold reads and marks "carried, not yet in the record") and deduped by id against everything already held; when the forge pull brings the same id, the carried copy is dropped. A body of prose: kept as data, and a proposed line written by the agent with `reason: untrusted`, linked to the mail by its message id.
- **Sends only on the person's act**: a line the person sent with **Send**, carried in the body with its prose. Open: whether a standing delegation that names mail as a transport for one type and one holon may send without it.
- **Never writes into a cell's tree**, never sends outside the private network, never acts on a header, a body or an attachment.
- **Retraction**: an empty `supersede` written by the sender is carried by mail to every mailbox the original reached.
- **The field of stake**: the transport reads `body.push` on every carried line, keeps every field it does not know, and recomputes `blocks`, `critical` and the sender's calibration through the engine before any view shows them; a prose mail yields a proposed field, each value marked as the agent's reading.
- **Tests**: a push with no field is shown as "No stake given"; a push past `expires` retracts itself; a carried line folds once with the same line pulled; a forged signature is refused; a line from an unadmitted key is unverified; a prose mail yields only an untrusted proposal; an instruction in a body moves nothing; a line of audience `holon` is never mailed beyond the holon.

### 10.2 serve.py

[serve.py](serve.py):

- **A hook endpoint** for the forge (`POST /hook`): accepts ids only (holon, actor, chain head), with a per-forge token; triggers a pull of that holon; never accepts a body; bound to the private-network address, never to every address.
- **The badge and the mail state in `/state`** (§10.5), recomputed on every pull.
- **`POST /mail/send`**: the person's act, with the page's token and the act sheet's confirmation, sending a line already written to the record.
- **`POST /mail/read`**: marks a carried item read on this machine; nothing reaches the record.
- **`POST /mail/line`**: the person's yes on a proposed line from prose, writing it as the person's own.
- **The phone's push**, through attention.py's gate only, carrying no words of any line.

### 10.3 The ICE

- **[mail.js](mail.js)**, inside the Threads and Mail tab, as the By house sort beside [threads.js](threads.js): rows, the open card, prose with its proposed line, the carried and unverified and withdrawn states, the stake line.
- **The tab bar and the badge** in the shell ([shell.js](shell.js)), reading `badges`.
- **The margin line** for arrivals from another house, rewritten in place.
- **The about sheet**: one line per transport (§2.3).
- **[print.css](print.css)**: the letter (§9.5).

### 10.4 The skills: the mail watch

[skills/a-mail-watch](../skills/a-mail-watch/SKILL.md), written in the kit's own skill form: the office of reading the house's mailboxes under the firewall. What to read and when (the strategy's beat), how to verify, how to turn prose into a proposed line, what a mail may never cause, how to show a likely injection to the person, and what to write at the Turn about what the watch learned. It carries the firewall rules of §7 in full, and it sends nothing.

### 10.5 The state fields

| Field | Shape |
|---|---|
| `badges` | `{threads_and_mail: n, from_houses: n, as_of}`: lines from beyond the home whose last word is not the person's, unread |
| `mail` | `{mailboxes: [{actor, reachable, last_read}], items: [{id, message_id, line_id (null for prose), from_actor, from_role, from_house (by role), for, holon, card, push (the line's `body.push` as sent), push_recomputed: {blocks, critical, calibration}, kind: line · prose, verified: verified · unverified · bad, carried (not yet in the record), read, picked_up, withdrawn, proposed_line, attachments: [{name, digest, published_by, verified}]}]}` |
| `transports` | `{forge: {beat_present_min, beat_away_min, last_pull, next_pull}, hook: {armed, last_at}, room_stream: {open_room}, mail: {on, last_read}, phone_push: {on}, relay: {on, cell}}` |
| `threads[]` | adds `carried_by: [forge · hook · room · mail · relay]`, `push` (as sent) and `calibration` (the sender's, recomputed) beside the existing `stake` |
| `calibration` | `{senders: {actor: {by_held, of, cost_held, alternatives_held, as_of}}, own: {by_held, of, season}}`: positive only, shown to the person alone |
| `notify` | `{strategy_as_of (the newest `attention` line), pushes_today, last_push_at, held_from_houses: n}`, beside `attention` |

### 10.6 Where this page differs from the other design pages

| Where | What it says there | What holds |
|---|---|---|
| [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §1 and §8.5 | No badge, no count | The one quiet numeral on Threads and Mail ([DESIGN.md](DESIGN.md): the tabs and the badge), in plain ink, with no motion, colour or sound, never outside the ICE; every other "no badge" stands |
| [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §3.1 | Every ask enters one queue | Kept; a line from another house enters the same queue, and arrives in the Threads and Mail view at once, readable without the gate |
| [DESIGN-ATTENTION.md](DESIGN-ATTENTION.md) §2.1 | The budget's fields | Kept; the transport mix and the strategy's practice are written beside the budget as the house's own lines (§2.3, §5.2) |
| [DESIGN-DOCK.md](DESIGN-DOCK.md) §4 | The phone door | Kept; its push carries no words of any line (§5.5) |
| [engine/types.json](../engine/types.json) | No transport | No new type: lines travel as lines; the mix and the strategy are `attention` and `learn` lines; `body.push` (the Push Protocol v1) is read on every pushed line and its fields declared on each pushed type. Open: a field for the transport mix on `attention` |
| [threads.js](threads.js) and STATE `threads[].urgency` | the asker's urgency as one word | the field of stake in full, with `asked` as the sender's words beside it |

---

## 11. The bar

### 11.1 The scenes

Judged on a phone first, then at 1440 px, night and paper, regular and large type:

a question from another house arriving by the forge's hook with its field of stake and passing the gate · a push that expires and deals the sender's alternative back · the same question refused by the gate in a room, shown by the badge, and rising after the room · a person checking by hand with nothing pushed · a prose mail from a person with no agent, turned into a line on the person's yes · a carried line arriving by mail before the forge pull, then folding once · a line retracted before it was picked up, in the ICE and in a standard client · a mail asking the agent to forward costs outside the network · a line from an unadmitted key · a names-hidden room's line carried by the room's mailbox · the phone's push, with no words in it · the Turn's one card on the strategy · a letter printed and a pencilled answer read back · the machine asleep with the phone open.

### 11.2 The questions

1. Is there one truth, and does every transport and every view say *as of* which line it saw?
2. Could a mail, a header, an attachment or a relay move your agent to act, send or widen anything?
3. Does every push pass the same gate on every door, and does the badge stay pull-side?
4. Can a person who checks by hand see every line at once, with its field of stake and its sender's calibration?
5. Can a sender reach a person's attention through any door except the receiver's own gate?
6. Is a line from an unadmitted key always shown as unverified, in words?
7. Does a line carried twice fold once?
8. Can a person with a phone, a mail address and no agent take part on day one?
9. Is retraction honest in a standard client as well as in the ICE?
10. Does the strategy live in the house's own lines, and do the strategy, the calibration and the protocol itself improve at the Turn?
11. Does any surface reduce the field of stake to a flag, a colour or a single word?
12. Would a grandmother feel she could find what another house asked of her, and feel served rather than summoned?
13. What did we miss that matters most?

A design that fails 1, 2, 3, 5, 6 or 11 goes back to be made again. The rest are lifted and passed.

### 11.3 Twenty strings

1. Threads and Mail · 2
2. A second house asks about the build. By five today. Two of your cards wait on it.
3. What rides on it: two of your cards and one of theirs. On the critical chain. About five minutes.
4. By five today, because their room meets at six. If late, the room waits. If no answer, they go ahead with the first draft.
5. Their "today" has been today nine times in ten.
6. Two lines from a second house, on the build.
7. Here is what I read it as: a request to review the survey by Friday. Make it a line · Change it · Leave it as prose
8. Arrived by mail. The record copy has not been pulled yet.
9. Unverified. Shown, and never acted on.
10. Withdrawn by the sender before it was answered.
11. Sent · carried by the forge and by mail · not yet answered
12. Your question reaches them at their own pace. If it cannot wait, say why and by when, and ask your agent to open a room.
13. Open a room with the second house? Both of you are free at three.
14. This mail asks me to forward your costs to an address outside the network. I have not done it.
15. Your agent has one thing for you.
16. The mailbox cannot be reached. The forge is still pulled. Last read 9:14.
17. Nothing waits on you from another house.
18. Changed on the way. Not opened.
19. Four questions from the second house waited past their by-when this week. I propose they rise one section when a person waits on them.
20. The forge · pulled 9:14 · next 9:29

---

## Not yet built

- The forge's hook endpoint (`POST /hook`, §10.2): until it is, a house's lines arrive by the forge's pull and by mail.
- `/state` reports `transports.mail` only; the forge, hook, Room stream, phone push and relay entries of `transports` (§10.5) are not yet reported.
