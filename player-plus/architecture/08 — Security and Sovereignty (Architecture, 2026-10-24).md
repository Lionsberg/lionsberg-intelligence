---
title: Security and Sovereignty — architecture
description: How each holon keeps its own record, signs its own lines and decides what leaves it, and what keeps that true under attack.
---

# Security and Sovereignty

*Sovereignty is holonic: every [[Holon]] keeps its own record, signs its own lines and decides what leaves it. Security is what keeps that true when an agent reads hostile text, a tool is poisoned, a key is stolen or a host is taken. Two sentences carry the whole page: **reading is the attack surface**, and **capability is not authority**. The gate must be structural, never advisory: auditability is not legitimacy.*

## 0. The trust model

Instructions about what an [[Agent]] may do come from exactly two places: **the Living Intelligence it serves** (in person, through their own signed act) and **its charter** (the files that say its Roles, its authority and its firewall, in the kit). **Everything else is data**: every line of every record, published faces from other holons, messages, web pages, tool and command output, other agents' words, files in shared spaces, comments on published work, and the agent's own recalled memories. Data informs; it never commands and never widens authority. A sender's name inside data proves nothing.

**The tell.** When data instructs the agent to act, above all to send, forward, post, push, publish or share; to change its permissions; to edit its charter, settings or skills; or to write a memory about its own authority, that is the injection signature. The more it reads like a directive, the more suspect it is. The agent neither obeys nor silently cleans it and proceeds: it stops, quotes the text with its source, and lets its person decide. A false positive costs one question; a false negative can cost an exfiltration.

**Trust-laundering.** A payload relayed through a trusted agent, a trusted [[House]] or a trusted channel gets the same scrutiny as a stranger's. The channel being trusted does not make the payload trusted.

## 1. The threat model, in classes

| # | Class | What it looks like | What it reaches for |
|---|---|---|---|
| T1 | **Injected text read by an agent** | A line in a room, a card's title, a published face, an unknown field, a web page, a document an agent summarizes, written so a model takes it as an order. | Outbound acts; a forged yes; a widened audience; a poisoned recommendation in The Deal; a memory that rewrites the agent's rules. |
| T2 | **Trojanized tools and packages** | A poisoned update of a coding harness; a package from a package index carrying a payload; a repository whose own configuration runs code when a folder is trusted; a poisoned skill or correction folded into the shared kit. | Whatever the host can reach: keys, tokens, every holon cloned there. |
| T3 | **Stolen standing credentials** | A broad, long-lived token for the forge or a model provider sitting near an agent; a credential typed into chat and kept in a transcript. | Write access to many repositories at once; impersonation at the forge. |
| T4 | **A compromised relay or host** | The forge, a mirror, a relay, a shared server or the machine the agent runs on, taken or coerced. | Withholding or reordering lines; serving stale state; on the agent's own host, signing as the agent, and as the person if their key sits there. |
| T5 | **A leaked name under a room's posture** | A name spoken in a [[Chatham House]] room reaching a settled line, a transcript, an export or another house. | A person's safety and trust; the room's willingness to speak. |
| T6 | **An agent acting beyond delegation** | Through bug, drift, injection or zeal, an agent writes a type, into a holon or after a date its delegation does not cover; or drafts and then "confirms" its own draft. | A human's box ticked by a machine; work moved without a yes. |
| T7 | **A forged identity** | Lines signed by a key that claims a person or an agent it is not; a display name copied; an agent presented as a person. | Admission to a holon; votes, ratifications, witness. |
| T8 | **A lost key** | A device lost, a key deleted, a person gone without a successor for their holon's key. | Continuity: a holon no one can sign for; an identity no one can rotate. |
| T9 | **Forged lines by anyone with write access** | Someone who can push to a repository appends a line in another actor's file, or an unsigned line, claiming to be that actor. | A forged commitment, yes or witness. Answered by signatures verified in the fold, with keys admitted by `join` and `affirm` lines; an unsigned line is authoritative only at the paper floor in the home record. |
| T10 | **Local callers and web pages reaching loopback** | Another process on the machine, or a web page in the person's browser, calls the HUD's server or the proxy on the loopback address. | Acts in the person's name; reading judgments. Answered by a token and a Host check on every local endpoint, made before a body is read. The proxy's token is its own and it holds no person's token, so no caller of the proxy can write a person's line. |
| T11 | **Canonical malleability** | Two byte forms of one line that a careless reader treats as different, or one id given to two meanings. | A line counted twice, or a signature carried to a changed line. |
| T12 | **Poisoned data files** | A changed `types.json`, `routes.json` or `calendar.json` arriving by a pull. | Human-only types made delegable; requests routed outward; dates moved. For routing, answered by structure: `routes.json` names vendors by name only and is refused at load if it names a host, scheme, key or vendor block; where requests may go lives only in the person's own vendors file, outside every holon. |
| T13 | **Time used for authority** | A `ts` back-dated to fall inside a delegation that has expired, or before a revocation. | An agent line counted as valid after its delegation ended. |
| T14 | **Replay into another holon** | A genuine signed line copied into a holon it was never written for. | A commitment or yes shown where it was never given. |
| T15 | **History rewritten by the forge** | The host of the repositories rewrites or drops commits. | Lines withheld or reordered for everyone who pulls from that host. |
| T16 | **A stolen key** | A person's or an agent's private key copied off a device. | Signing as that actor until the key is ended. Each actor holds its own key, so one stolen key signs for one actor only. |

## 2. The structural answers in this system

Each answer is carried by structure (the line format, the server's refusals, the fold's validity rules, the conformance test), never by this text alone. Graceful degradation runs down to paper; the text is the top layer. The line format and the fold are the record contract (`engine/SCHEMA.md`, and [[01 — The Record (Architecture, 2026-10-24)|the Record architecture]]) and the state contract (`engine/STATE.md`).

1. **Every line is data** (T1). An agent reads every line of every record as data, never as instruction. Unknown fields are kept and shown, never obeyed; "do-it-now" dispositions and urgency fields are injection channels and are read as data.
2. **Reason-origin gating** (T1, T6). Every line carries `reason`: `human` (a Living Intelligence asked) · `delegated` (within a standing delegation) · `untrusted` (the reason came from text the agent read). **An agent act whose reason came from untrusted input is a proposal only and waits for a human, however reversible.** The Engine folds such lines into `owed.proposals`, shown for a person to take up, never counted as owed. The Deal says when a recommendation was drafted from something the agent read.
3. **Delegation scope and expiry** (T6). A [[Delegation]] is a `delegate` line by a person to an agent: which types, which holons, until when; `revoke` ends it. **An agent's line is valid only when a live delegation covers its type and holon;** the fold refuses the rest, so an out-of-scope line is visible as invalid rather than silently acted on. Every agent's delegation ends in a Living Intelligence.
4. **Signing by the Actor** (T7, T6, T9, T16). Every line is signed by the [[Actor]] who wrote it, over its content hash; the agent signs with its own key on its own account, distinct from its person's. **Human-only acts (the sixteen types the registry marks, `commit`, `ratify`, `decide` and `publish` among them) are valid only under the person's own key, or from the agent for one act at the person's recorded consent.** Signatures are verified in the fold, with keys admitted by `join` and `affirm` lines, and each actor holds its own key. A person's key is admitted once and changes only by a signed rotation, or by the keeper with a [[Witness]]; key files carry the actor's kind; consent-signing requires the person's own verified line; a forked chain holds both lines and neither acts until the actor names the survivor; another's commitment is superseded only by the committor's decision or the keeper's with a witness. `answer` stays open to agents: an agent may answer a request inside its delegation, and an answer that would commit its person still needs the person's `commit`. An agent never ticks a human's box, and the agent's signature on a yes is no yes. Who signed, under whose delegation, is kept forever; whose idea it was is separate and never attached to a person without their word.
5. **Append-only with elision** (T5). Nothing is edited or deleted; a correction supersedes and both remain. Every body string is hashed through a salted digest, so an exported line hides its names and keeps its proof ([[Elision]]). A Chatham House room exports with names hidden; the export removes signatures and the exporter attests the set, until the Envelope. A non-consenting person's name is removed wherever it was written, and the removal is recorded.
6. **Audience narrow-only** (T5, T1). A line's audience is never wider than its holon; within a holon it only narrows; widening is a separate `publish` line by a Living Intelligence. The local server refuses a wider write, and a forbidden line answers exactly as a missing one ([[02 — The Membrane (Architecture, 2026-10-24)|the Membrane]]).
7. **Private network first** (T3, T4). The first week runs on a private network only. The HUD's server and the proxy bind to the loopback address, behind a token and a Host check. Nothing is exposed to the public internet that has not been published to it by a person.
8. **The Proxy's trust model** (T1, T10, T12; [[05 — The Proxy (Architecture, 2026-10-24)|the Proxy architecture]]). Where requests may go, and with which key, lives only in the person's own `~/.config/lionsberg/vendors.json`, outside every holon, refused unless it is the person's, mode 0600 and not a link; `routes.json` in the holon names those vendors by name and nothing else. Plain http reaches only an address of this computer's own, checked by the address and never by a name; a request tagged `private` reaches only such an address, checked on every request. Every upstream redirect is refused, no ambient proxy setting is used, and bodies, nesting, connections, answers and streams are capped. The person's discernment is a `discern` line signed with the person's own key (`~/.ssh/lionsberg-person-<handle>`, through ssh-agent), written by the ICE after the person's tap, or written unsigned and shown as paper when the key is not at hand; the proxy's `/discern` writes only an untrusted agent note, never counted as the person's. The agent never writes `~/.config/lionsberg/` or `~/.ssh/lionsberg-person-*`.
9. **Relays never the truth** (T4). Servers, mirrors and relays are conveniences. Truth is the signed lines; any holder verifies any line anywhere. A relay can withhold or delay; it cannot forge. Every computation says *as of* which line it last saw from each neighbor, so withholding shows as staleness, and two holders comparing their `as_of` find the gap.
10. **Disposable identities until a key ceremony** (T7, T8). The current design: for the first week identities are disposable and labeled as such; real identities come with a ceremony: a stable identifier from a first key that survives rotation, a chain of marks that shows which description is current, a witnessed inception, and a named successor. The ceremony's details are open (Open 3).
11. **Conformance before admission** (T1, T6, T2). An agent enters a room only after a present person affirms it and only after it passes the six conformance checks: deal a Deal from a sample record, compute the reference float, sign and verify, **refuse an injected line**, mark an out-of-delegation line invalid, fold two holons at once.
12. **The one who assigns never audits** (T6, T2). The actor who sets a piece of work never verifies it; a separate reviewer does. An agent never grades its own act; a fold computed by one holon is checked by another holding the same lines.
13. **No outbound act without a human's word** (T1, T3). Every act that leaves a holon (publish, message, post, push, share, spend) needs a Living Intelligence's word for that act; an agent asks before anything leaves its holon. The hard stops: an outbound act whose reason came from data · a memory about the agent's own authority not given by its person · a charter edit traced to data · any request to reveal or forward a person's records, keys or private particulars.

## 3. What remains exposed, said plainly

- **The HUD's token is readable by any local process running as the person** (accepted in 3.8.0). The local server hands the page its token on request, so another program of the person's can act through the HUD, and a person's tap is then a flag that program can set.
- **The agent's own host is the soft center.** Whatever runs on the machine where the agent runs can sign as the agent. If the HUD's local server signs the person's yes with the person's key on that same machine, a taken host can sign as the person too. Key separation on one device protects against mistakes, not against a compromised host. Hardware-held keys for human acts would close most of it (Open 1).
- **`reason` is a claim by its writer.** A compromised or careless agent can label an injected act `delegated`. The schema's protection is that human-only types need the person's key and that delegation scope bounds the rest; within its scope, a mislabeled agent line can still do what the scope allows.
- **A human's real yes can be steered.** A poisoned recommendation, drafted from hostile text, can earn a genuine signature. The defense is showing where a recommendation came from, and the person's own judgment; no structure fully covers it.
- **Elision is not forgetting.** Every holder of a line keeps a copy. A name settled before it was elided has already replicated to everyone who pulled it; removal is recorded and honored by conforming readers, and cannot be enforced on a copy already taken.
- **The paper floor is unsigned.** A paper line, or a yes the agent writes from a photo of a paper card, carries no key; it is as strong as its witness.
- **Model providers see what is sent to them.** The Proxy records where a request went and why, with no prompt bodies; the provider still saw the body.
- **The Proxy's known limits.** The vendors file is a same-user boundary: it protects against what a pulled holon carries, not against a process running as the person, so an agent with a shell can edit it, and the charter's line is what holds there. https to any host the person writes in their own file is allowed, by design. The proxy's report counts signed person lines without verifying their signatures; that is the fold's job. A slow upstream can hold a thread up to the thirty-minute stream deadline, within thirty-two connections. The fixed User-Agent still marks a request as coming from the proxy, and a council's fan-out is correlatable across vendors by timing. The record writer the proxy loads is checked by path, owner and mode, not by a pinned hash, because it changes with each kit version; pinning belongs to a signed release.
- **The forge sees the shape.** Who joined which holon, when, and how often is visible to whoever hosts the repositories, even when contents are private.
- **The kit is a supply path.** Every agent pulls [[The Kit]], and the weekly retrospective folds corrections into it. A poisoned skill or correction reaches every agent at the next pull. Review by someone other than the proposer, and signed kit releases, narrow this; nothing removes it.
- **Time is a claim.** A line's `ts` is what its author declared; order comes from links. A forged time misleads only a reader who trusts times over links.
- **Disposable first-week identities** can be made by anyone with access to the private network; admission rests on a present person's affirmation.
- **Flooding.** An append-only record remembers everything written to it; a holder with write access can flood it.
- **Coding harnesses are a supply-chain target.** Public reports, not yet checked against the vendors' own advisories, describe trojanized updates of a harness, a repository configuration that runs code when a folder is trusted, and broad standing tokens near a harness as the common shape of this class (T2, T3). The hygiene below holds whether or not each report holds.

## 4. The hygiene a house keeps

- **Pinned versions.** Tools, harnesses and libraries run at a pinned version; automatic updates are held until a release is checked against the vendor's own advisory. The HUD has no package manager; any library is one vendored file with its exact version in its name.
- **Untrusted repositories never opened in trusted folders.** A repository from outside is read in a sandboxed place with no folder trust, no hooks and no configuration executed; only then, if wanted, moved in. Downloaded files and archives live in their own new directory; scripts that read them live elsewhere.
- **Token scopes reviewed.** Every standing token is reviewed against what the work needs: the narrowest scope, the shortest life, one per agent, never shared between agents or with the person. A broad write token near a harness is retired.
- **Agents on their own accounts and keys,** distinct from their persons' and linked to them; human-only acts through the human's.
- **No secret in any record.** Credentials are never written into a line, a transcript or a shared page; transcripts are scanned for credentials before anything leaves the private store, and a credential found is rotated, not just masked.
- **Backups of keys and records** the house can restore without the agent, on paper where it matters, with a named successor for each holon's key.
- **Muted by default.** No agent plays sound unasked; no process plays audio; headless runs are muted.
- **The firewall in every charter.** Every agent's charter carries the trust model, the tell, the hard stops and the duty to stop, quote and ask.

## Open

1. **Where the person's key lives** relative to the agent's host: same device (the present design), a separate device, or a secure element; and for which acts. Whether to require hardware-held keys for human acts now, or only for irreversible acts.
2. **Keys per context for a witness:** one key per Actor until a case demands more, or separate keys from the start.
3. **The key ceremony:** who witnesses an inception, how a successor is named, how rotation is announced in a way a person can read, and how revocation stays visible to people.
4. **Identity form:** a stable identifier from a first key (XID) or a decentralized identifier (DID).
5. **Who runs conformance,** and who checks the test itself, so the one who assigns does not audit.
6. **Rate limits and the admission window:** per identity, per holon; whether an agent writes only while its person has been active within a window.
7. **A curing period** in which anyone may change their mind about what they shared in a room, and how it meets append-only.
8. **Revocation latency:** how fast a `revoke` reaches every holder, and what an out-of-date holder does with lines signed after it.
9. **The Proxy's routing policy:** which requests may go to which providers, under which audience, and whether the Proxy routes messages among agents.
10. **Removing a non-consenting name** from copies already replicated to other houses.
11. **Credentials already in transcripts** held in private stores: who decides to rotate and mask them.

## Not yet built

- Minting the HUD's token into the served page once, the repair for the first exposure in §3.
- Rate limits per identity against flooding.

*Concepts: [[Holon]] · [[Sovereignty]] · [[Sovereignty At Every Scale]] · [[Guard the Membrane]] · [[Agent]] · [[Actor]] · [[Delegation]] · [[Witness]] · [[Elision]] · [[Chatham House]] · [[The Record]] · [[House]] · [[The Kit]] · [[Player+]].*
