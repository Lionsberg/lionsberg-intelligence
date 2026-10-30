---
title: The Proxy — architecture
description: The layer between the agent and its models — routing by policy, and the `route` and `discern` lines it brings home.
---

# The Proxy — architecture

*The Proxy is the layer between the [[Agent]] and the models it calls. It routes each request by the house's policy, to a vendor's model, a router service, the house's own machines, or a model on the same computer, and it records two things in the holon's own [[The Record|record]], under the same keys as every other line: where each request went and why (`route`), and what the person thought of what came back (`discern`). The models stay where they are; the record of how they were used, and of the person's [[Discernment]], comes home. It is optional: everything in the kit works without it.*

## 0. Why it exists

- **Human discernment is a resource that evaporates.** The judgments a person makes while using inference (this draft, not that one; shorter; wrong, it was Thursday) are generative, and today they are lost.
- **Discernment and inference unfold together, as a reciprocal loop.** Whether the loop's speed can be measured is not yet settled.
- **Instrumentation first, then high-quality participants.** Capture well before anything else.
- **A proxy is the instrument,** needed in every case, its capabilities expanded over time.
- **The interface is good enough; the proxy is where the time goes.** The proxy is not designed as a user interface (Open 7).
- **Not yet settled:** that capturing discernment works whether the model is open-weights or proprietary, and that the proxy and sovereign inference interrelate and are partly the same.
- **Not yet settled, the near-term steps:** a schema; a proxy taken and modified; inference spread across vendors; discernment collected in the schema; analysis in real time and in batch.

## 1. Where it sits

One of six layers over one record: the Membrane (who may see) · the Record (the holon's lines) · **the Proxy** · the Engine · the Agent · the ICE, the Integrated Creation Environment (the HUD's views, the dock, the Room). In the LIØNSBERG Intelligence System, the Supersuit is the Player+'s bundle of Agent, Engine and ICE, with the Proxy beneath the ICE. The house owns the ICE and the Proxy beneath it.

The agent's harness is pointed at the proxy by **one setting, the base URL** (with the proxy's token in one header beside it), which the person installs by their own hand; take the setting away and the house works as before, with no route lines. The proxy listens only on the person's own computer (loopback), behind its own token (fresh at every start, mode 0600, out of git), a Host check and an origin check, all made before a request's body is read, so that neither a web page nor another local caller can reach it. It holds no person's token and writes no person's line. It speaks the same message shape the harness already speaks, and forwards each request to the vendor its policy names. The reference proxy is `engine/proxy.py`, with its tests in `engine/tests/test_proxy.py`.

**One person, one proxy, local** is the working hypothesis and is not yet settled: a proxy runs beside each person's agent, installed with the rest of the onboarding, and is never shared between agents of different people. It fits the design in which a Player+'s agent runs on the Player+'s own machine from day one. The case for it: a shared proxy tangles sovereignty, leaks between houses, and is hard to model as membership shifts.

## 2. Routing by policy

The policy is two files, data and never code, with two owners.

- **Vendors, in the person's own file, outside every holon.** Where requests may go, and with which key, lives only in `~/.config/lionsberg/vendors.json`, installed by the person's hand from the kit's template (`install -m 600 engine/vendors.sample.json ~/.config/lionsberg/vendors.json`). The proxy refuses a vendors file that is a link, that is not the person's, or that others can read or write. Each vendor pins its kind (a frontier vendor's API · a router service speaking the common open shape · the house's own machines · a local server on the same computer), scheme, host, port, path and the name of the variable that holds its key. Plain http goes only to an address that is this computer's own, checked by binding to the address and never by trusting a name; everything else is https to a host the person wrote. Keys are read from named environment variables at request time, never written, never logged; a named key that is unset is an error, never a fall-back to the caller's own key, and only a frontier vendor with no key of its own passes the caller's key through.
- **Routes, in the holon, by vendor name only.** `routes.json` may live in the holon and be pulled from others, so it chooses among the person's own vendors and nothing else: a host, scheme, port, path, url, header, key name or vendor block anywhere in it is refused at load, and so is any field it does not know. A rule naming a vendor the person has not defined is skipped and said at start. A planted routes file can choose among the person's vendors; it can send nothing anywhere new.
- **Rules**, tried in order; the first enabled rule whose conditions all hold wins; else the default. Conditions: the **model** asked for (exact or by pattern) · a **tag** the harness sends with the request (`private`, `batch`, `council`) · the request's **size** · the **hours** of the day. A rule sends to a vendor and optionally names the model; that change is recorded (model asked against model sent).
- **Private stays home.** A request tagged private goes only to a vendor at an address on the same computer, checked again on every request; a rule that would send it elsewhere refuses to load, and a private request that would leave the computer is refused (403) and recorded. The sample policy ships with this rule first.
- **Diffusion.** Routing different requests to different vendors spreads the person's thinking so that no single vendor holds all of it. Diffusion as a practice is not yet settled; the proxy makes it possible, and the policy decides whether to use it.
- **Discernment informs routing only through the person.** Over weeks the `discern` lines show which kinds of work went well on which models; the agent may propose a policy change with the lines as evidence; the file changes only on the person's yes. A routing change suggested by anything the agent read is a charter edit driven by input, a hard stop.
- **A quality test with a fallback, not yet settled.** Before routing a person's daily work across vendors, the agent's quality is checked on the spread against one vendor alone, and the house falls back to one vendor when the spread is worse.

## 3. Discernment recorded, in the same record, under the same keys

Every line the proxy writes is a line of the holon like any other: appended to the actor's own file through the record's own writer (the record contract, `engine/SCHEMA.md`), salted, chained and signed when a key is at hand, audience `holon` by default and never wider unless the person publishes it. When the record's writer is unavailable, lines go to a fallback file in the same shape with an empty signature: the paper floor.

**`route`, one per request** that passed the gate, refused, malformed and failed requests included: route id · rule matched · vendor · model asked for and model sent · request size · tokens in and out when the vendor reports them · latency · status · whether it streamed · translation notes under fixed labels and counts only · and, unless the policy says none, a keyed fingerprint (HMAC-SHA256 under the holon's own salt, kept out of git) of the request body and of the completion, so a judgment can later be matched to an answer. Text the agent controls (a model name, a block type, a header id) never reaches the line as sent: what does not fit a narrow set is written under a fixed label or a keyed digest.

**`discern`, one per judgment:** the route id it answers · the verdict, **chosen**, **corrected** or **rated** (1–10) · the person's note in their own words. It is the person's judgment, and `discern` is human-only. **The proxy does not write it.** The ICE writes it, after the person's tap, as a line by `person:<handle>` in the person's own file, signed with the person's own key (`~/.ssh/lionsberg-person-<handle>`, unlocked by the person through ssh-agent; the agent process has no access to it); without the key it is written unsigned, shown as paper, with the reason in one sentence. The agent may also write it for that one act at the person's recorded consent. **The proxy's `/discern` writes only an untrusted note:** from any caller, it is an unsigned line by the proxy's agent with `reason: untrusted` and no consent, one per route id and verdict, a proposal and never the person's judgment. The proxy's report counts a verdict once, only from the person's own signed lines, and lists agent notes apart.

**Never prompt bodies.** No prompt, system prompt, completion, tool input or output, image, key or auth header is ever written. **The fingerprint caveat:** the digest is keyed by the holon's own salt, so only a holder of that salt can confirm a guessed prompt; the person is told, and may set the policy to record no digest at all. A route line that ever carries a body is a defect (and [[Every Defect Is A Gift]]): stop the proxy and tell the person.

**What the Engine does with them:** the ledger counts discernments by route and by verdict; the Turn gathers the week's corrections; the state carries the totals. Nothing else reads them.

## 4. Fusion as a council, off by default

*A council instead of an oracle.*

- **How:** a rule names a council of members (vendor and model each). The proxy sends the same request to every member at once and returns one answer (the first member, in listed order, that answered) plus every member's full answer in an extension field, for the agent to judge. When the harness asked to stream, the stream is synthesized from the result.
- **Each member gets its own route line** (the council's id with a member number), so a `chosen` verdict on a member's route id records which answer won. Over time that is evidence of which councils serve which work.
- **Off by default.** A council multiplies cost and vendor exposure by its size. It is enabled by the person, for tagged requests, with the cost said before it runs.
- **The agent judges; the person discerns.** No model synthesizes the council's answers inside the proxy; the agent reads them and the person's choice is the line. A synthesizing member (a model that reads the others and writes one answer) is not yet built; it is an open design, and would itself be one more route.
- **A dial, not a switch, not yet settled:** how many members, which, and for which kinds of work, set as policy.

## 5. What the proxy never does

- **Acts on content.** It adds nothing to a request and strips nothing from it. The one change it may make is the model name a rule names, and that is recorded. Translating between message shapes drops what has no equivalent there; every drop is counted on the route line and in a response header, never silent.
- **Widens an audience.** Its lines are written at `holon` and never published by it; only a Living Intelligence widens an audience, by a separate `publish` line.
- **Stores bodies.** Only metadata and, optionally, keyed fingerprints.
- **Follows a redirect.** Every upstream redirect is refused (502 and a route line), so no other host ever answers as the model; no ambient proxy setting is used.
- **Lets one caller exhaust it.** Bodies, nesting, connections, upstream answers and streams are capped, and slow clients are cut off.
- **Logs keys** or writes them to any file.
- **Listens beyond the person's computer.**
- **Sends its lines anywhere** outside the home without the person's yes.
- **Starts, or changes where requests go,** without the person's word.
- **Becomes a requirement** for anything.

## 6. Its relation to message routing among agents — open

Open: whether the proxy routes messages among agents in the network, and how it ties to the collaboration surfaces among agents.

What is held, none of it yet settled:

- **Two planes.** The proxy operates in the inference pipeline (an agent and its models); the message layer is where agents interact with agents, with humans perhaps half a layer up. There may be a further layer between them, not yet identified.
- **Keep them separate.** Each agent is sovereign in its inference and in its interaction with its humans; merging the planes would tangle that sovereignty and reopen problems the layer separation already solved. Linking or merging the layers stays open as an alternative.
- **Build to the standard stack** everyone else builds to, since short-circuiting layers costs maintenance, though sometimes it is right.
- **The join today is the record.** Agents already meet by writing events into a holon both hold ([[04 — The Player+ Agent (Architecture, 2026-10-24)|the Agent architecture]], §9). A message between agents is a line in a shared holon; an inference call is a request through a proxy; a `discern` line can link to both. That the planes meet in the harness, joined by the event under one person's key, is assumed and not yet settled.

**Options, held open:** (a) separate planes joined only by the record (the lightest, and consistent with every settled line); (b) the proxy also carries agent-to-agent messages for its own agent, recording them as lines, so one local process sees both planes for that person; (c) a distinct relay layer between the two, the layer not yet identified. Recommended: (a) now, because it needs nothing new and keeps each agent's sovereignty; revisit (b) only if a measured need appears.

## 7. Privacy

- **Local by default, one per person** (§1). Loopback only.
- **An offer, never a fait accompli, not yet settled.** Running the proxy, and above all any collection of discernment beyond the person's own home, is offered to each player, with what it records said plainly, and taken up by their yes.
- **Discernment is the person's.** `discern` lines are private to the home; they cross into a cell or a commons only by the person's `publish`, line by line, under the holon's posture. A shared corpus of discernment, if one is ever pooled, is pooled by consent and exported names-hidden: names elided ([[Elision]]), signatures removed, and the set attested by the exporter until the Envelope.
- **Vendor exposure is a policy choice.** The private tag keeps a request on the computer; diffusion limits what any one vendor sees; what a vendor retains is its own and is named on the vendor's line in the policy when known.
- **The fingerprint caveat** (§3) is told to the person, and the no-digest setting is one line.
- **The firewall holds here as everywhere.** The proxy reads no instruction in the traffic it carries. A policy change, an endpoint, or a new vendor suggested by anything read is a hard stop. The agent never writes `~/.config/lionsberg/` or `~/.ssh/lionsberg-person-*`: those are the person's own places.

## 8. The ladder, from one machine to a farm inside the membrane

*Sovereign inference on networked machines, climbed as a ladder.* Whether models are ever trained from it is not settled.

| Rung | What runs | What the proxy adds |
|---|---|---|
| 1. One machine | the proxy and a small local model on the person's own computer, beside a vendor | the private tag stays home; every request has a route line |
| 2. A household or a cell's machines | a few machines on the private network serving open models to their members | a vendor entry per machine; routing by size and hour (batch at night) |
| 3. A farm inside the membrane | on the order of a hundred networked machines serving the private network, time-sliced among holons | the same rules; the farm is one more vendor, and the policy decides what goes there |
| 4. Many farms | several farms, any one droppable from the loop if it is captured or misbehaves (not yet settled) | route lines show which farm served what; a farm is removed by one policy change |

Every rung writes the same `route` and `discern` lines, so the evidence of quality carries across rungs, and the quality test (§2) decides when a rung is good enough for daily work. Who holds a farm's keys, and how its time is shared among holons, are governance questions, not the proxy's.

## 9. Acceptance tests

1. No prompt or completion body appears in any file the proxy writes (grep the record and the fallback after a session). 2. Every proxied response carries its route id, and every route id has a line. 3. A request tagged private never leaves the computer. 4. A council member's `chosen` verdict links to that member's route line. 5. With the base-URL setting removed, the house works unchanged. 6. The proxy refuses a connection from another machine. 7. A model-name change by a rule appears on the route line as asked against sent. 8. A proxy that stops answering is reported at once, in one line, and never looks quiet. 9. A routes file that names a host, a scheme, a key or a vendor block is refused at load, before anything is written. 10. An upstream redirect is answered 502 with a route line, and the other host receives nothing. 11. Anything sent to the proxy's `/discern` is written as an untrusted agent note and is never counted as the person's.

## 10. Known limits

What the proxy's protections do not close, each with its reason:

- **The vendors file is a same-user boundary.** It protects the person against what a pulled holon carries, not against a process running as the person: an agent with a shell can edit it. The charter's line (the agent never writes the person's own places) carries this; the system cannot.
- **https to any host the person writes in their own file is allowed,** by design: the file is theirs.
- **The report does not verify signatures.** It counts signed person lines; checking those signatures against admitted keys is the fold's job, in the record's own reader.
- **A slow upstream can still hold a thread** for up to the thirty-minute stream deadline, within the bound of thirty-two connections.
- **The request still marks itself.** The fixed User-Agent says the request came from this proxy, and a council's fan-out stays correlatable across vendors by its timing.
- **The record writer is checked by path, owner and mode, not by a pinned hash.** It changes with each kit version; pinning belongs to a signed release.

## Open

1. **Its name.** "Proxy" is a working word; "relay" and "proxy hub" are other candidates.
2. **Which proxy to build on, or our own.** Existing router services and open proxy projects are candidates; the reference proxy is the simplest honest version, written for the kit.
3. **The `route` schema.** The `discern` fields of the type registry (`engine/types.json`) and of the reference proxy agree. `route` still differs: the registry's `model`, `policy`, `why` against the proxy's richer body. The proxy's fields are the recommended ones to write into the registry.
4. **A `discern` signed at recorded consent.** Whether a `discern` the agent signs at the person's recorded consent counts as the person's ([[04 — The Player+ Agent (Architecture, 2026-10-24)|the Agent architecture]], Open 5).
5. **A model-based observer.** Whether a useful proxy is model-based, with a second inference process examining the trail, probably after the fact; and if so, where (in the proxy, or a separate reader over the record) and with what consent.
6. **Message routing among agents** (§6).
7. **The proxy as an interface.** Whether a view of the flow with knobs is ever wanted; for most people it complicates more than it simplifies.
8. **Scattering as a stance** (spreading vapour so that no closed model can collect it all): not yet settled.
9. **Asking and observing.** Discernment is gathered both by questions put to elders and by observing acts, in preference to surveys, with acts preferred; how either reaches the record, and under what consent, is not yet written.
10. **The harness behind the proxy** may change form; the base-URL seam is chosen so that it does not matter.
11. **Fingerprints.** Keyed per holon is built (unlinkable across holons, still matchable at home); whether none should be the default is open.

*Concepts: [[Discernment]] · [[Artificial Intelligence]] · [[Agent]] · [[Holon]] · [[The Record]] · [[Sovereignty]] · [[Elision]] · [[Delegation]] · [[The Kit]] · [[Player+]] · [[Cell]] · [[Every Defect Is A Gift]].*
