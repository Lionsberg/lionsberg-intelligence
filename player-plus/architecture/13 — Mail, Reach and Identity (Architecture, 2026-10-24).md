---
title: Mail, Reach and Identity
description: How lines travel between houses by push and by mail, how an actor is reached, who an author is, and the Push Protocol's field of stake.
---

# Mail, Reach and Identity

*How lines travel between houses by mail, how an actor is reached, and who an author is. Each part says what the kit does in 3.8.0, and what is not yet settled.*

The contract lives in `engine/SCHEMA.md` (Messaging · Reach, not identity · The Push Protocol v1.1) and `engine/types.json` (`join`, `affirm`, `body.reach`). The mail transport is `engine/mail.py`, the field of stake is `engine/push.py`, and the Mail view is `hud/mail.js` and `hud/push.js`, served by `hud/serve.py` and described in `hud/DESIGN-MAIL.md`.

## 1. The ground

**There is no messaging layer.** A message between any two actors is a typed, anchored line in a [[Holon|holon]] both hold. Delivery is a pull; mail, hooks and streams only carry the line (`engine/SCHEMA.md`, Messaging; `hud/DESIGN-MAIL.md`, the ground and §1).

**Push and pull, both.** A line reaches another Player's house by pull (the forge, at the receiving agent's beat) and by push (the forge's hook, the Room's live stream, mail inside the private network, the phone door). The record stays the truth whichever carried it (`hud/DESIGN-MAIL.md` §2.1; `hud/serve.py`, the hook and `/mail/send`). The measure of a channel is lines per commitment kept, read per transport at the Turn.

**Mail is one of a few main views of the ICE.** It is a tab beside a standard mail client, with a badge on the Threads and Mail views when another house writes (`hud/DESIGN-MAIL.md` §4; `hud/mail.js`; `hud/DESIGN.md`, tabs and the badge). The badge is meant to draw attention only within the person's attention budget; as built, it counts what is unread from other houses.

## 2. Mail inside and outside the network

**Mail is a carrier, never a second truth.** This is the one bridge from mail into the record:

- a carried line is verified by its signature against the keys the holon admitted;
- it is kept once, by id, until the forge brings it;
- prose in a mail becomes one proposed line, marked untrusted.

The aim: a line never folds twice, and no view shows a mail's copy where it differs from the record's (`hud/DESIGN-MAIL.md` §1, §10.1; `engine/mail.py`, RECEIVING and THE CARRIED STORE).

**Inside the private network, mail is plain mail:** the standard mail protocols, on a host inside the network, read by any standard client on the desk and the phone. The client side is built. `engine/mail.py` (THE MAILBOX) accepts a host only on a private, loopback or shared address, and refuses public hosts (`hud/DESIGN-MAIL.md` §2.2).

Not yet settled:

- **The mail host.** No host is chosen. As designed, a mail host is a shared square inside the network, like the forge, kept by named keepers and required by no one: under no center but [[ØNE]], no house is the mail center. A house must always be able to exchange lines without that host; the forge's pull stays the floor.
- **Sign-in for mail clients.** Mail programs do not do passkeys. If the network's sign-in cannot serve standard clients, app passwords are the proposed bridge.
- **Mail across the public internet.** A relay-free agent-to-agent mail, of the same kind as the other transports and read by the agent's own fetch, may serve the public internet and a house outside the network. Nothing in the code carries it, and `hud/DESIGN-MAIL.md` §2.1 has no row for it yet.
- **How long mail carries the houses.** Mail is a bootstrap, expected to serve for about six months before the forge's hook and the Room's stream carry the houses' lines. The Turn will show what actually carried them.

## 3. Reach and identity

**The author is a key; an address is reach.** A mail address is a transport endpoint, never an author. An agent's key is distinct from its person's, and a line is signed with the actor's own key (`engine/SCHEMA.md`, Reach, not identity; `engine/types.json`, `join` and `affirm`; `engine/mail.py`, RECEIVING).

**`body.reach`.** An actor's own `join` or `affirm` line may carry `body.reach`: the actor's signed list of where lines may be carried to them (`mail:<address>` inside the private network, `hook:<url>`, `phone:<pairing>`). A sender's agent reads reach from the holon to choose a transport. A person with an address and no key is reached on day one; her lines count on their own when she makes a key and her join carries it. The field is in the contract (`engine/types.json`, field `reach`).

**The address book, for now.** The mail transport does not yet read `body.reach`. Until it does, the audience check maps a mail address to an actor through the person's own address book (`account.addresses` in `~/.config/lionsberg/mail.json`). The address book decides only who may receive, never who wrote.

Not yet settled:

- **Accounts and keys.** The account that opens the network's shared squares (single sign-on, groups) and the key that authors lines are two things; the join line is where they meet. How the two are reconciled, and whether signed identities (XIDs) carry it, is open. The design of reach and of authorship leans on that answer.
- **Membership as approval.** One possibility is that membership in the private network is the approval and a mail address falls out of it: one sign-in, with groups giving the address, outside the kit. A holon's own mailbox already needs its keeper's act of approval (`hud/DESIGN-MAIL.md` §2.2), so this may not hold for every address. See [[02 — The Membrane (Architecture, 2026-10-24)|The Membrane]], Open 7.
- **Reach under a names-hidden posture.** An address can name a person. Whether reach is elided with the names, and how a sender then finds a transport, is not designed.

## 4. The Push Protocol

**A push carries a field of stake, never an urgent flag.** The field holds: kind, by and why, size, what it blocks, who waits, blast radius, cost if late, alternatives, the sender's own words, expiry and calibration (`engine/SCHEMA.md`, The Push Protocol v1.1; `engine/push.py`; `hud/DESIGN-MAIL.md` §5.7). It is a key protocol, improved continuously; the test is whether receivers' weights track what turned out to matter, measured at the Turn.

**The agent proposes; the person decides.** The agent suggests every value, and the person may change any value before Send (`engine/push.py`, `stake` and `modulate`; `hud/push.js`). The Send sheet shows each value and whose it is.

**Every value says whose it is.** `push_by` is `agent` or `person`. The sender's own words are always the person's. A v1 line reads as all the agent's. A person's change is never shown as the agent's, nor the reverse (`engine/push.py`, `whose`).

**The receiver recomputes.** What blocks, what is critical, the by-when and the cost if late are recomputed from the receiver's own record; the sender's values are kept beside, as what the sender said (`engine/push.py`, `weigh` and `sender_said`; `engine/mail.py`, `recompute_push`). A receiver that lacks the sender's cards may compute that nothing waits where much does; the cross-holon schedule is what closes that gap.

**Calibration is measured for both,** per Living Intelligence: how often the agent's by-whens were real, and how often the person's own were. It is positive only and shown to the person alone (`engine/push.py`, `calibration`; `hud/DESIGN-MAIL.md` §10.5). That it never acts as a score or a rank between people is a design aim the Turn checks; whether it makes the field truer is read from the record at each Turn.

**Each house holds its own notification strategy:** the allocation of the house's time, energy and attention, written as practice in the house's own lines and improved at every Turn (`engine/SCHEMA.md`, Messaging; `hud/DESIGN-MAIL.md` §5.2–§5.3, the `learn` and `attention` lines). `engine/attention.py` holds the budget. The strategy itself, readable whole in the Record and changed by a word, is not yet built, and `attention` has no field yet for the transport mix.

## 5. The carried store and the mail functions

- **Where carried lines wait.** The carried store sits at `<hq>/.carried/`, with `lines/`, `prose/` and `bad/` (`engine/mail.py`, THE CARRIED STORE; `hud/serve.py`).
- **Names-hidden mail from a member.** A names-hidden line from a member who is not the keeper travels unattested and is shown as unverified, because only the holon key may vouch without naming anyone (`engine/mail.py`, CARRYING A LINE; `hud/DESIGN-MAIL.md` §3.6). Open: whether a room's mailbox agent may hold the holon key under a standing delegation.
- **Coalesced mail.** `from_mail` returns the first line only. `read_mail` and `carry` handle every line a coalesced mail carries; a caller that reads coalesced mail uses those.

## 6. The firewall for mail

**The fetch never sends.** A send happens only on the person's own Send: `send` and `send_line` refuse without `on_the_persons_send`, and `POST /mail/send` in `hud/serve.py` asks for confirmation (`hud/DESIGN-MAIL.md` §7, §10.1). An outbound act whose reason came from data waits for the person. The gate is a parameter a caller sets, so it holds only as long as no caller sets it without the person's act. Open: whether a standing delegation for mail is ever granted.

**The From line proves nothing.** Sender identity inside data is unauthenticated. A carried line counts only by its signature against keys the holon admitted; the From line is not kept as a source (`engine/mail.py`; `engine/SCHEMA.md`, Reach, not identity; `engine/types.json`, `join`). No path turns a From line into an author. The address book of §3 maps addresses to actors for receiving only.

When reading the code, start with the one bridge (§2) and the firewall (§6): a defect there costs the most.

## Not yet built

- The mail transport reading `body.reach` in place of the address book.
- A mail host inside the network, and who keeps it; what happens to a house's mail when that host is down.
- Relay-free mail across the public internet.
- A house's notification strategy as a readable, changeable whole, and a transport-mix field on `attention`.

*Related: [[01 — The Record (Architecture, 2026-10-24)|The Record]] (identity and keys) · [[02 — The Membrane (Architecture, 2026-10-24)|The Membrane]] (the private network, accounts) · [[05 — The Proxy (Architecture, 2026-10-24)|The Proxy]] (agent messaging) · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]] · [[08 — Security and Sovereignty (Architecture, 2026-10-24)|Security and Sovereignty]] (the firewall) · [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)|Decisions and Their Reasons]]. Concepts: [[Holon]] · Living Intelligence · [[Selectively Permeable Membrane]] · [[ØNE]].*
