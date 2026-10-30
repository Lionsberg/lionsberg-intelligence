---
title: The Record — architecture
description: The ground layer: holons as folders, the signed event line, its id and elision, keys and delegation, audience, replication, and the fold to items. `engine/SCHEMA.md` is the binding contract; this page explains it.
---

# The Record

*The ground layer of the LIØNSBERG Intelligence System. Every other layer reads it, and every number in the system can be rebuilt from it. A [[Holon]] remembers by keeping its own lines; nothing else it holds is history. The binding contract is the kit's `engine/SCHEMA.md` (schema v1); this page explains it.*

## 1. Holons as folders, and usually repositories

A holon is a folder laid out the same way at every scale, and usually a git repository:

```
<holon>/
  holon.json        who this holon is: v, id, name, kind (person · pair · cell · room · body), keeper, created
  record/<actor>.jsonl     one append-only file per Actor who writes here
  published/<actor>.jsonl  copies of lines this holon's people published into it from elsewhere, same line format
  plan/baseline-<n>.json   frozen plan versions (only the Engine writes them)
  types.json        the type registry (data, not code)
  calendar.json     the holon's calendar: seasons, spans, working days, each Actor's minutes per day
  state.json        the Engine's latest fold (derived; ignored by git; safe to delete)
  .gitignore        state.json, and cells/ in a home (and the local files in §12)
```

**The actor file** is the actor id percent-encoded with its case kept (`person:handle` writes to `person%3Ahandle.jsonl`); two actor files that differ only by case are refused on writing and reported on reading. A reader does not read a line longer than 64 KiB, a linked file or a linked cell.

**A holon's identity is the hash of its inception.** A holon is born by one line, the first in the keeper's file: a `join` with `body.role: inception`, written before the holon has an id (its `holon` field is empty). The holon's id is that line's id, and the keeper is that line's actor. `holon.json` alone proves neither: a reader reports an id that no inception line carries, a keeper that differs from the inception's actor, and a cell that claims an id already held. Only the reader's own home may fall back to its `holon.json` when its inception line is missing. The repository's address is where the holon lives, never what it is: a holon that moves to another host keeps its id and its whole history, because nothing in a line names a host.

A person's [[Player+]] home (their HQ) is a holon. A [[Cell]] is a holon on the forge. Joining a cell is being given access to its repository and cloning it under `cells/<name>/` inside the home; being let into the cell's record is the cell's own act, a `join` line by one of its admitted people (§4). A room is a holon; a room's record and a holon's record are one idea. A body of bodies is a holon whose record is mostly what its members publish into it.

**One file per actor, so there is never a merge conflict.** Each Actor appends only to its own file in each holon, and no one edits another's file. Two writers can never touch the same bytes, so git merges by union. Each file is a chain: every line's `prev` names an earlier line of the same file, or is empty for the first; a `prev` that names no earlier line is a broken chain, reported.

## 2. The event line

One JSON object per line, fields in a fixed order so a line reads by eye:

`v` · `id` · `ts` · `actor` · `for` · `holon` · `type` · `body` · `links` · `audience` · `reason` · `prev` · `sig`

- **`v`**: the envelope version (1). Readers keep fields they do not know.
- **`id`**: the event's identity, the hash of its canonical form (§3). The same in every record that holds it.
- **`ts`**: the author's declared time, with offset. A claim, never an order.
- **`actor`**: who signed: `person:<handle>` or `agent:<handle>`; the handle is the forge username where one exists.
- **`for`**: the [[Actor|Living Intelligence]] the actor answers for. For a person, themselves. Every line traces to a Living Intelligence.
- **`holon`**: the id of the holon this line is published in. Empty only on an inception line.
- **`type`** and **`body`**: one of the registry's types and its typed fields. Honest-empty fields are omitted, never guessed. A line meant to be elidable carries `body_salt`, one salt per line. Two types bear on attention and on judgment: `attention` is the person's attention budget as their own signed lines (what may interrupt them, when and how often; human-only; it governs interruptions, never what may be read), and `note` is an agent's untrusted note on a route or a line, written by the proxy with `reason: untrusted`, unsigned, never counted as discernment (a person's judgment is only a `discern` line signed with their own key).
- **`links`**: typed edges to other lines by id: `predecessor` · `successor` · `serves` · `fulfils` · `answers` · `witnesses` · `anchored_to` · `supersedes`.
- **`audience`**: the widest audience the line may reach: `holon` (default) · `members` · `commons` · `public`. It never widens except by a separate `publish` line by a person, and a person publishes only their own lines.
- **`reason`**: `human` (a Living Intelligence asked) · `delegated` (within a standing delegation) · `untrusted` (the reason came from text the agent read; the line is a proposal only).
- **`prev`**: the id of this actor's previous line in this holon, chaining the actor's file into a tamper-evident log.
- **`sig`**: the actor's signature over `id` by its own ed25519 key (`ssh-ed25519:<base64>`, made with `ssh-keygen -Y sign` in the namespace `lionsberg-record`), or empty at the paper floor.

**The event is the unit.** In live text the unit is a settled line; that is a hypothesis, and it is stated as one so that it can be changed. Speech is not recorded. What is said stays in the conversation; only what a Living Intelligence settles enters the record.

## 3. Canonicalization

The id is computed the same way on every machine and, with patience, by hand:

0. The line must keep the canonical limits, on reading and on writing: every string, keys included, in Unicode NFC; integers only (no fractions, exponents, NaN or Infinity); booleans and null allowed; no key twice in one object. A line that breaks any of these has no id.
1. Take the line without `id`, `sig`, and any key beginning with `_` (a reader's local notes, never written).
2. If the line is **salted** (its body carries `body_salt`, or `body_salts` after an export), every body field except the salt enters the hash as its salted digest, `{"elided": sha256(field_salt + canonical_json(value))}`, and so do the three envelope fields `actor`, `for` and `prev` (under the names `@actor`, `@for` and `@prev`). Each field's salt is `sha256(body_salt + "\x00" + name)`. A string is hashed in its JSON form, with its quotes, so `30` and `"30"` never share a digest. A field already elided enters as the digest it carries.
3. Serialize with keys sorted by Unicode code point and the separators `,` and `:`, UTF-8; take the sha256 hex.

The consequence is the property the whole system leans on: **a salted line has the same id before and after any of its fields are hidden**, so its signature keeps verifying. A line with no salt (a paper-floor line) hashes as it stands and cannot be elided without changing its id.

The id excludes the signature, so the signature is made over a stable identity and a line can be countersigned later without becoming a different line.

## 4. Identity, keys and delegation

**An Actor is known by a key.** A line is signed with an SSH ed25519 key, `ssh-keygen -Y sign` in the namespace `lionsberg-record`, and verified in the fold with `ssh-keygen -Y verify` against the key admitted for its actor in its holon by a `join` or an `affirm` line, never against the key the signature carries. On a machine the key file is `lionsberg-person-<handle>` or `lionsberg-agent-<handle>`, in the folder `LIONSBERG_KEY_DIR` names (the kit's `--key-dir`), else `~/.ssh`; when a folder is named, no key is made or looked for anywhere else, and a key named for another actor is refused. Every key file carries the kind of its actor, so an agent's key can never be read as a person's. A holon may hold a key of its own, `lionsberg-holon-<holon id>`, whose public key its inception carries (`body.holon_pubkey`); it is made with the inception on the keeper's own machine, held by the keeper's body alone, never pushed to the forge, and used only for the holon's own acts (an export's attestation). The checks are cached in the reader's own home (`.sigcache`, mode 0600, each row under an HMAC whose secret lives outside the home); only a signature that verified is written, so the cache can spare a check but never pass a forged line.

**Admission.** A person's key is admitted once, by a `join` naming `body.who` and `body.pubkey`, written by the keeper or a person already admitted; it changes only by a rotation signed with the current key, or by a `join` from the keeper naming a witness, which takes effect when that witness writes a trusted `witness` line linking it. Any other re-admission is `bad_admission`. Admission does not reach backwards: an actor's lines written before the line that admits them are `paper`, except the one line the admission answers. An `affirm` by the agent's own person, carrying `body.agent` and `body.pubkey`, admits an agent; only that person re-affirms it. A `join` or an `affirm` may carry `body.reach`, the actor's own signed list of where lines may be carried to them (`mail:<address>` inside the private network, `hook:<url>`, `phone:<pairing>`): an endpoint says where to carry a line, never who wrote one ([[13 — Mail, Reach and Identity (Architecture, 2026-10-24)|document 13]]).

**The paper rule, for every keyed actor.** An unsigned line counts only at the paper floor of the reader's own home: in the home's own `record/`, by the keeper or actors the home admitted (an agent only after the keeper's `affirm`). Once an actor at home holds an admitted key (the keeper, or an affirmed agent with a key), that actor's unsigned lines at home are `paper`: shown, and acting only after their own, or the keeper's, signed `witness` of them. Every other unsigned line, including any that arrived from a cell or in `published/`, is `unverified`: shown, never acted on. A line written for another holon never acts where it sits (`wrong_holon`).

**Clones.** A prime agent may let in a clone of itself by an `affirm`, valid under a standing `delegate` from its person to the prime whose scope covers `affirm` and `body` and whose `clones` names a handle pattern the clone's handle matches (the kit's `holon.py affirm --prime`). A clone's handle always begins with its prime's handle and a dot (`agent:<prime>.<name>`), so no pattern reaches another person's agent. A clone acts only within the prime's delegation, never an outward act (`publish`, `elevate`, `escalate`, `affirm`, `delegate`, `revoke`, `join`, `leave`, `posture`) and never a person's own act; its first line is its `body` line claiming its work, and its admission ends at `done` or `archived`, or a day and a half after its claim, by its own chain time and by the reader's clock alike.

**Persons and agents have separate identities, linked.** An agent has its own account and its own key, distinct from its person's. Human-only acts go through the human's own key: in the registry, nineteen types are a Living Intelligence's own act, `settle` · `commit` · `kept` · `witness` · `decide` · `ratify` · `delegate` · `revoke` · `join` · `leave` · `publish` · `turn` · `discern` · `posture` · `affirm` · `layout` · `elevate` · `escalate` · `attention` (the prime's `affirm` of its own clone is the one agent `affirm` the registry allows, under the delegation above). `answer` stays open to agents, so an agent may answer a request inside its delegation. An agent's line of one of those types is kept in the record and folds as invalid, with one exception: an agent may sign a single act at its person's word, once the person has let that agent into the holon with their own `affirm`. Either by a `delegate` with `once: true`, a single type and a single holon, used up by the first line it covers, and, when it names `body_digest`, only for a line whose body matches it. Or by the person's consent for that one act: the person's own signed line in the same holon names the act in `body.consent_for` (the sha256 of the act's type, holon, links and body, the body without its salt and its consent words and the links without the consent line itself; or the act's id), and its text is the very words the agent's line carries in `body.consent` (two characters at least); the agent's line names that consent line in `links.answers`. A consent line counts once; a bare consent, a substring, a one-letter word, or a consent that names another act never counts. The fold marks the item `signed_for`, and every view shows it as signed by the agent at the person's word. An agent never ticks a human's box.

**Delegation is a line.** A person writes `delegate` to an agent: which types, which holons, until when. `revoke` ends it by chain order, not by time: it names the agent's chain heads it saw (`body.seen`), and after it only the agent's lines at or before those heads still count, so backdating either side changes nothing. An agent's line is valid when a live delegation covers its type and its holon, except for the human-only types, which no standing delegation covers. Delegation is explicit, scoped, time-bounded, revocable and recorded, so *every agent answers to a Living Intelligence* is structure, not policy. Roles and Offices belong to Living Intelligence, a being or a group of beings, who may delegate to agents.

**Identity that survives key rotation is not yet built.** At first, identities are disposable and labeled; real identities come with a ceremony. The expected path is XIDs: a stable identifier derived from a first ("inception") key, resolving to a controller document whose provenance marks show which edition is current. Provenance marks give order, not time. One way it could land: under an XID, the actor field names the XID and the allowed-signers list becomes the controller document's current keys, so no line written before the change stops verifying.

**Keys per body.** One key per Actor is the starting rule; where one Actor runs in several bodies (a laptop, an always-on server, a background body), each body signing with its own key is the target, so a line can be sorted by which body made it. Keys matter most for permanent acts; a human's authority for those is best held in a hardware-backed key that needs a touch.

## 5. Append-only, supersede, elide

**Nothing is edited or deleted.** A correction is a new line that `supersedes` the old; both remain, and the fold shows the newer. A retraction is a `supersede` with nothing in its place. A line is superseded only by its own actor or by a person's `decide`; another's commitment is superseded only by the committor's decision, or by the keeper's with a witness. A forked chain (two lines naming the same `prev`) holds both lines, and neither acts until the actor names the survivor. Conflicting claims both stand; the Living Intelligence holding the holon's keeper Role writes a `witness` that settles which holds for that holon.

**Elision hides a field and keeps the proof.** Any body field of a salted line, and its `actor`, `for` and `prev`, can be replaced by its salted digest. The exported line drops the line salt and keeps only the derived salts of the fields left visible, so a hidden value cannot be guessed from its digest while every visible one still checks. A low-entropy value (a yes, a birth year) is safe to hide because it was salted. A names-hidden export also hides every public key field and every body field that names an actor, removes the signatures, and attests the exported set as a whole by role ("the keeper of" or "a member of" the holon), with the count, the hash of the ids in order, the chain heads it reaches and the signing key's id; a reader checks the attestation against the record's admitted keys, and a trimmed subset fails. That holds until lines travel inside an Envelope.

**The one exception to append-only** is a non-consenting person's name, which is removed wherever it was written, and the removal is itself recorded. On a salted line, removal is an elision in place in the current file: the id and signature still verify, but the repository's git history keeps the earlier form until that history is rewritten. On an unsalted line the name cannot be hidden without changing the id; the line is rewritten, its old id superseded, and the rewrite recorded. This is why every line the kit writes is salted by default.

## 6. Audience and publication

Every line names the widest audience it may reach. **Audience belongs to the holon** (the holon's container is sometimes a repository): a line's audience is never wider than its holon, and within a holon it only narrows. The four audiences are `holon` · `members` · `commons` · `public`: `holon` is the holon's own Actors; `members` reaches the holons related to this one (its members, its subcells and its supercell); `commons` is the shared room of the private network; `public` is anyone. These four readings are not yet defined in SCHEMA; they are not yet settled.

**Publication is the one act that widens.** The line's own `audience` field is signed and never changes. To widen, a Living Intelligence writes a separate `publish` line naming the lines and the audience they may now reach; the published lines are copied whole, id and signature intact, into the receiving holon's `published/`. The Engine reads a line's reach as the wider of its own audience and any valid `publish` that names it. An agent may copy lines toward a cell, but its `publish` line folds invalid, so the audience widens only by a person's hand.

**What crosses by default** is a card's face and the holon's signals, never its inner activities: in 3.8.0, `card` (a milestone, decision or quest, never a bare activity) · `commit` · `request` · `offer` · `answer` · `done` · `kept` · `witness` · `turn` · `flame` · `hand` · `claim` · `release` · `supersede` · `sight`. [[02 — The Membrane (Architecture, 2026-10-24)|Document 02]] holds the membrane these cross.

## 7. Replication by relation, through git

A holon replicates the records it is related to: a person, the cells they belong to; a cell, its members, its subcells and its supercell. There is no global directory; the relation is the address book.

In 3.8.0 the transport is git. **Pulling brings others' lines in; pushing one's own lines out is a person's act**, done by their own hand. The kit's code pulls (fast-forward only) and never pushes. Signed commits by each Actor's forge key are the chain beneath the lines (a signed git history can be the log's chain), so the record is provable twice: line by line, and commit by commit.

Any transport delivers the same lines, verified by hash and signature on arrival: a git pull, two phones exchanging, a drive carried by hand, a sheet typed in later. A link to a line not yet held shows as *not yet replicated*, never as a broken reference. Relays and shared hosts are conveniences; one that vanishes loses nothing any holon held.

## 8. The fold to items

**Items are folded, never stored.** A [[Work Card]] is born by a `card` line and changed only by later lines that link to it. A [[Commitment]] is a `commit` by a Living Intelligence naming the card, the by-date, the conditions, the size and the witness. A commit that names a card adds a finish-by time constraint to it (`source: commitment`), which never loosens the card: the tightest constraint governs, and a commitment later than the card's own finish-by shows the gap (`commitment_gaps`). The keeper claims `kept`, the named Fair Witness verifies with `witness`, and another's witness line is kept as a note (`witness_notes`), never a verification; the witness is never the commitment's own Living Intelligence. The gap is computed from the by-date against the `done` or `kept` line's time. A `claim` may carry `until`; once it is past and the claimer still holds the card, the card returns to `ready`. A Thread is a `thread` line anchored to a line or a card, its lines `say` and `settle` anchored to it. A Delegation, a TEA entry, a Decision, a Sighting, a Turn, a Baseline and a Discernment fold the same way.

`fold(lines) → items` is a pure function. **The fold order is causal:** an actor's lines by their `prev` chain, a line after every held line it links to or names, and an actor's lines after the line that admits them in that holon; time, then arrival, only breaks ties, so two lines in the same second still fold in the order their causes give. Within one chain time never runs backwards: a line dated before its chain's previous line is read at that line's time and flagged. The fold's `now` is the newest trusted line's time, never later than the reader's own clock; a line more than a day ahead of the reader's clock is flagged `ts_ahead` and moves nothing. A delegation's `until` and a claim's `until` are still compared with time. The same lines give the same items, the same path and the same commitments kept on every machine and on paper; two holons holding the same lines agree, and two holding different lines differ only by replication lag.

**The type registry is data.** `types.json` declares each type's fields and their kinds, the item it folds into, whether it creates that item, where it finds the item it changes, which item kinds it may act on, its state transitions (from which states, by whom: the item's own Living Intelligence, anyone else, or the holon's keeper), and whether it is human-only. A new type is a new entry, not new code. Readers keep every line whose type they do not know; it folds into *unknown* and waits for a registry that knows it.

## 9. "As of"

Every computation says what it saw. The Engine's state lists each holon folded with its `as_of`: the newest line seen there, its time, how many lines were read, and the clock the fold used. Every number in the state is as of those lines. A HUD shows it; an agent says it; a sheet carries it at the top. Lag is visible rather than hidden behind a server.

**Known limits of this release.** A fold is as of the reader's clock: two players whose clocks disagree by more than a day can fold the same lines differently (a line flagged `ts_ahead`, a clone's window). The signature cache's HMAC secret lives on the reader's own machine, so a process running as the same user, the agent included, can read it and write a row that passes; the agent's own host is the soft center, and the cache moves to the OS keychain, or goes, in a later release.

## 10. The paper floor

One event is one line on a sheet: time · who · for whom · type · what · links · audience. Page and line numbers stand in for `prev` and `id` until the sheet meets a computer, where the hashes are computed and the lines typed in unsigned (`sig` empty) and unsalted. The two passes, what is owed and commitments kept are worked on the same sheet by pencil. **A witnessed paper sheet beats the typed copy.** Unsalted paper lines cannot be elided, so a names-hidden export holds them back and says how many.

## 11. What cannot change, and what migrates

Once lines are written, four things are fixed for those lines forever: **identity** (how the id is computed), **signature** (what is signed and how it verifies), **supersession** (that a line is replaced only by a later line pointing to it) and **audience** (that it never widens except by a `publish`). A change to any of them is a new envelope version, and old lines keep verifying under the rules they were written under.

Everything else migrates: the type registry, the link vocabulary, the body fields of a type, the items and their states, the holon layout around `record/`, the transports, the identity scheme above the key (XIDs over plain keys). Readers keep fields they do not know, so an older reader passes newer lines through unharmed.

## 12. What the home keeps beside the record

- **Local files, never committed.** A home's `.gitignore` holds `state.json` and `cells/`, and also the files that live only on the machine: `.sigcache` (the signature cache, §4), `.carried/` (what mail carried before the record did), `.talk/` (a room's said lines, kept on the machine) and `.pulled.json` (the last head the home saw of each cell).
- **The `attention` type.** `types.json` carries `attention` as a human-only type, the person's own attention budget (§2), read before any interruption.
- **Reach and push.** `body.reach` on `join` and `affirm` (§4), and the Push Protocol v1.1 with `push_by`, are held in full in [[13 — Mail, Reach and Identity (Architecture, 2026-10-24)|document 13]].

## Open

1. **The unit's one word:** event, change or commit. This page uses *event*, with a settled line as one event and a signed commit as its chain.
2. **Keys per context for a witness:** whether a witness needs more than one key. One key per Actor until a case demands more.
3. **What an XID adds:** whether an XID adds one secret (the provenance mark) beside the key, or none.
4. **A late `done`:** the keeper claims kept and the named witness verifies (§8); whether a late `done` counts as kept is unspecified.
5. **The TEA ledger.** TEA is kept on an immutable ledger; whether the signed, witnessed lines of the record are that ledger, or are checkpointed into another, is open.
6. **Canonical form across systems.** JSON with sorted keys here; deterministic CBOR in Gordian Envelope. Whether lines become envelopes, or are carried inside them, is open.
7. **An address scheme.** There is none; holons are known by their inception ids and named by `holon.json`.
8. **The proxy's digests** of request and completion bodies are keyed by the holon's own salt, so only a holder of that salt can confirm a guessed prompt; they can be switched off ([[05 — The Proxy (Architecture, 2026-10-24)|document 05]]).

## Not yet built

- Identity that survives key rotation (XIDs, §4).
- A key for each body of one Actor (§4).
- The bank's full design, beyond the TEA ledger.
- Encrypted bodies for lines only a home holon may read.

*Concepts: [[Holon]] · [[Actor|Living Intelligence]] · [[Player+]] · [[Cell]] · [[Work Card]] · [[Commitment]] · Fair Witness · Thread · XIDs · Gordian Envelope. Siblings: [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] · [[02 — The Membrane (Architecture, 2026-10-24)]] · [[03 — The Game Engine (Architecture, 2026-10-24)]] (the fold and every function over it) · [[07 — Interoperability — Across Holons and Houses (Architecture, 2026-10-24)]] (replication and publication across holons).*
