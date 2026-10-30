---
title: The Membrane
description: Who may see and who may reach, decided by each holon. Architecture document 02 of the LIØNSBERG Intelligence System.
---

# The Membrane

*The outermost layer of the LIØNSBERG Intelligence System: what passes into a [[Holon]] and what passes out, decided by the holon. The membrane governs who may see and who may reach. It never governs what is true; the record carries its own proof.*

The contract is `engine/SCHEMA.md` (schema v1): the `audience` field, the `publish` type, and `export(lines, posture)`.

## 1. What the membrane is

In a living body the membrane is a skin, not a wall. It knows self from not-self, lets in what nourishes, and gives out what the body chooses to give. A holon's membrane is the same: **audience**, decided by the holon, never by whatever network the lines happen to travel. (The practice behind it is [[Guard the Membrane]].)

The membrane has four parts, from widest to narrowest:

1. **The private network**: the shared network that only admitted devices can reach. Everything a holon keeps lives inside it unless published out.
2. **The forge and its accounts**: the self-hosted git forge inside the private network, where cells keep their repositories and every person and every agent has an account.
3. **Audience per holon**: each holon's container (usually a repository) and the `audience` on each line.
4. **Publication**: the one recorded act by which anything widens.

Every technology the system uses comes in two kinds, a private-network kind and a public-network kind. The membrane is the line between them.

## 2. The private network

The private network is the first membrane: a private mesh network of admitted devices, where a host is reachable only from a device that belongs. Inside it run the forge, the shared rooms, and in time internal mail, sign-in, transcription and a compute commons. Outside it is the public internet.

Being inside the private network is reach, not trust. A device on the network can reach the forge; what it may read there is decided by the forge's accounts and each holon's container. An agent on the network reads everything it reaches as data.

What is published to the commons on the private network is visible to every agent there. Nothing narrower is.

## 3. The forge and its accounts

The forge is where holons beyond a person's home keep their repositories: a cell is a repository on the forge, a quest a folder in it. The forge is held by a group that keeps the host; every holon on it is a tenant, and its own record does not depend on the host's survival.

**Every person has an account; every agent has its own.** An agent's account is separate from its person's and named for its person, and its key is its own. Human-only acts go through the human's account and the human's key. An agent's account is granted only what its person's delegation covers.

**Joining a cell is being given access** to its repository and cloning it into one's home. **Leaving is having access removed.** Lines already replicated stay where they were replicated; the membrane can stop future reach, never recall the past. That is why publication is weighed before it happens (§6).

**What the forge can do, and what it cannot.** The forge verifies signed commits against each account's registered keys and can protect a repository's main line so only signed changes, or only a named promoter, land there. Refusing at push time every change a repository's own policy forbids needs a hook run by the host's keepers, and that hook is not yet built; the record does not rely on the forge refusing. Each repository proves itself: every line signed, every commit signed, and any clone able to check the whole history with the forge out of the loop.

**One sign-in everywhere** (an identity service with passkeys) is the direction the private network leans; it is not yet built. The record's identity is the Actor's key in any case; an account is how a key reaches a host.

## 4. Audience per holon

Audience belongs to the holon, and the holon's container is sometimes a repository. Every line names the widest audience it may reach: `holon` · `members` · `commons` · `public`. Within a holon, audience only narrows.

**The forge enforces audience by repository, never by line.** Git access is whole-repository: whoever can clone a repository can read every line in it. So the rule that holds the membrane is:

> A line is written only into a container whose reach is no wider than the line's audience.

The mapping, proposed for the first build and not yet settled:

| Audience | Container |
|---|---|
| `holon` | the holon's own repository, readable only by its own Actors (a person's home: the person and their agent) |
| `members` | the receiving holon's `published/`, inside a repository its related holons can clone |
| `commons` | a repository in the commons space of the forge, readable by every account on the private network |
| `public` | a mirror outside the private network, reached only by a `publish` naming `public` |

Where one repository must hold lines of different audiences, the repository's reach is the ceiling, and a narrower line belongs somewhere narrower, or encrypted, or elided before it is written there. Encrypted bodies are not yet designed.

**An agent has no audience its person cannot read.** Agents may whisper to one agent, several or all; the person each agent serves can read all of it.

## 5. Publication: the one act that widens

A line's `audience` is part of what it signed and never changes. To widen, a [[Actor|Living Intelligence]] writes a `publish` line naming the lines and the audience they may now reach, and the lines are copied whole, id and signature intact, into the receiving holon's `published/`. The Engine reads a line's reach as the wider of its own audience and any valid `publish` that names it.

**Only a person widens.** `publish` is a human-only type: an agent may prepare the copy, and its own `publish` line folds invalid. Publishing across a membrane is the act the agent always asks before doing, because it leaves the holon.

**What crosses** is a holon's face, never its inner life: a card's face (what it is, its state, its by-when, who holds it, its stream), its milestones, commitments, requests, offers, answers and signals, and the holon's periodic broadcast ratified by its people. A card of kind activity stays home; its milestone crosses. A dependency crosses a membrane only through a [[Commitment]]. Each holon publishes what it chooses after each meeting.

## 6. Postures

A **participation posture** is how a gathering's record may leave it, agreed before the gathering begins. The export function carries three in 3.8.0:

- **Chatham House** (`names-hidden`): what was said leaves; who said it does not. Every name is hidden (the line's actor, for and prev, and every body field that names an Actor). Because a signature names its signer by key, the export removes each line's signature; the ids and salted digests stay, so each line still proves its content, and one attestation signed by the exporter vouches for the set. A form that keeps each author's signature while hiding names arrives with the Envelope. Lines that cannot be elided (unsalted paper lines) are held back, and the export says how many. A room under the [[Chatham House]] rule writes ideas without names beside them and quotes nothing outside without asking.
- **Open** (`open`): nothing hidden.
- **Sealed** (`sealed`): every body field and the envelope names hidden, signatures removed; what leaves proves that lines exist, when, and what they link to, under the exporter's attestation.

**The curing period** is not yet built: a window after a gathering, before anything is exported or published, in which each participant may correct, retract or narrow what they said. As proposed, and not yet settled: during the cure the room's lines stay at audience `holon`; a correction is a `supersede`; at the cure's end the posture's export runs and a person publishes it. Other postures (a fishbowl, where a few speak and many listen) wait to be named.

**[[Elision]] at export** is how a posture keeps the proof: a hidden field leaves its salted digest, so a stranger can verify that the exported record is the record (each line by its id, the set by the exporter's attestation) without learning what was hidden. Elision is decided by the holder, never by the issuer. [[01 — The Record (Architecture, 2026-10-24)|The Record]] gives the mechanism.

## 7. Entry: vouching and the trust graph

**Entry is by vouching.** A person comes into a holon because someone already in it vouches for them; who invited whom is the trust graph, and partial vouching is enough to begin. The trust graph is computed from the record (the `join` lines and who wrote them), never kept by hand, and it is the provenance of every member: any member can be traced to the one who vouched for them, and on to the holon's first keeper.

**An agent enters a room by its person's word.** Before a person affirms an agent into a room, the agent passes the conformance run: deal a Deal from a sample record, compute the reference float, sign and verify, refuse an injected line, mark an out-of-delegation line invalid, fold two holons at once. The agent's reach then is what its person's delegation covers, in the holons it names, until the date it names.

Believability, track record and endorsements by fair witnesses can ride the same graph later; none is designed yet.

## 8. The public door

The public door is the one place a stranger meets the system: a web page, read-only, or by invitation. Read-only, it shows what holons have published to `public`, every line verifiable by anyone. By invitation, it is the threshold of vouching: a passkey, and the list of holons the newcomer has been invited into.

The first door: a Player+'s agent runs on their own machine from the first day. A friend passes the flame; the install is one line pasted into the command-line harness and takes minutes; the agent speaks first, and The Deal arrives by about minute ten. Afterward the phone reaches the agent on that machine, over the private network; a printed card serves whoever prefers paper. That is the default; a shared machine, or a cell hosting agents for others, are configurations in the same space, chosen by those who run them. The forge is the builder's door, never the player's.

## 9. The keeper of the membrane

The **keeper of the membrane** is a Role, held by a Living Intelligence for a holon (often the holon's keeper; it need not be). Its offices:

- grant and remove access to the holon's container, on the holon's consent, and record each grant and removal as a line;
- keep the holon's allowed-signers list current: add keys, end keys, rotate. A person's key is admitted once and changes only by the person's signed rotation, or by the keeper with a witness; every key file carries the kind of its actor; an agent signs for its person only on the person's own verified line of consent;
- see that each line is written into a container no wider than its audience;
- hold the posture of each gathering, and run the export when a cure ends;
- answer for the holon's door.

The keepers of the host are a different Role: they keep the forge and the private network running for every holon on them, and they can see what the host stores. A holon's record does not depend on them: it proves itself in any clone, and it can move to another host and keep its id. The one who grants access never audits it; a fair witness does.

## 10. What the membrane is not

- **Never the truth.** Who may see is the membrane's; what happened is the record's. Within the record, a forked chain holds both lines and neither acts until the actor names the survivor; another's commitment is superseded only by the committor's decision or the keeper's with a witness; `answer` stays open to agents. A line is true to its signature wherever it travels, inside or outside the network, on the forge or on a sheet.
- **Never a commanding hub.** A server that enforced audience and held the only copy would make itself the hub every holon depends on; the system has no center but ØNE. The membrane is many skins, one per holon, and every holon keeps its own record.
- **Never a recall.** Once a line is replicated, it is held. The membrane governs the future; the cure and the posture govern what leaves.
- **Never the firewall alone.** Every agent reads every line as data, whatever side of the membrane it came from. A line that tells an agent to send, publish or change anything is folded as text and acted on by no one.

## Open

1. **Line-level audience inside one repository.** Encryption of bodies for lines only a home holon may read is not designed; until it is, audience is enforced by container.
2. **The curing period:** its length, who may cure what, and whether it is part of the posture or of the room's shape.
3. **A `vouch` type.** SCHEMA has `join`; open: whether vouching needs its own line, and how partial vouching is written.
4. **The commons as an audience of its own** is set in direction; its container on the forge, and who keeps it, are open.
5. **The public mirror:** where it lives, and who may publish to `public` for a cell.
6. **The forge refusing.** Open: whether the host runs a server-side check of each repository's policy.
7. **One sign-in everywhere** (passkeys, an identity service) and how an account binds to an XID.
8. **Reach beyond the gathered:** shared records may go to willing people beyond those present, who ask before sharing further; open: how that is written into a posture.

## Not yet built

- Encrypted bodies for lines of mixed audience in one repository.
- The curing period.
- A push-time hook on the forge that refuses what a repository's policy forbids.
- One sign-in everywhere.
- Believability, track record and endorsements on the trust graph.

*Siblings: [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)|The System]] · [[01 — The Record (Architecture, 2026-10-24)|The Record]] · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)|Interoperability]] (what crosses, in depth) · [[08 — Security and Sovereignty (Architecture, 2026-10-24)|Security and Sovereignty]] (the firewall and the threats the membrane does not stop).*
