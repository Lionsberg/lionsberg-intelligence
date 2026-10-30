# Changes

*Newest first. Each entry says what changed and why, so your agent can read a release and you two can decide what to take. Nothing here installs itself; `skills/pull-a-release` walks you through a pull.*

## 3.8.0 — 2026-10-29 — one Game Engine

Two engines that had grown side by side become one, on the kit's base, so every Player+ calculates the same way. The Game Engine is now release layer 4 (architecture 17), with its own version, **game-engine 1.0.0**, its own card (`engine/ENGINE.md`) and its own record of changes (`engine/CHANGES-ENGINE.md`). Layers in this release: engine 1.0.0 (new); the Record, extended by the lines the Engine asks for; the ICE, extended by the Wall.

- **The contract.** No date is imposed on a Work Card: a time constraint on a card is reported and never applied, and a milestone keeps only its marker's target. A commitment never writes onto its card: the card carries `committed_by`, and the schedule compares the due date with the computed finish (the buffer). Minutes are the one unit: a duration is minutes over the holder's minutes a day, and its fraction is kept. `within` is the nesting edge: every card lies within one unit, and a link to or from a unit is routed to its entries and exits. The commitment has its full shape: committor, committee, direction, delivered_by, due date, computed finish, buffer against the buffer stated, and state. Only the committee says Kept, releases or declines. A released, declined or retracted commitment dates nothing, in its own house or across. Only a commitment crosses between houses with a date.
- **The whole engine** (`plan.py`), with resources, the leveled critical chain with pooled buffers and release by pull, the Last Planner measures, the SpaceTime Breakdown Structure, exports and photo capture. See SCHEMA.md, "What the engine computes".
- **New lines:** `pledge` (a commitment of TEA, fiat and tokens for a period), `miss` (one of eight reason codes on a commitment not kept by its date), `constraint` and `clear` (the constraint log). Card fields: `minutes_safe` (the second estimate), `marker`, `where`, `conditions`, `tea`, `fiat`, `tokens_m`, `platform`; the stage `could`.
- **The Wall** in the ICE (`hud/wall.js`): the open cards by week, every handoff drawn, a card opened in place under its sticky with a comment and the acts, closed by ×, Escape or a second click without moving the page, filtered by holder, stream and state.
- **Tests:** 554 in the engine (1 skipped); 141 more than 3.7.0.

## 3.7.0 — 2026-10-25 — the Talk

The player and their agent talk first. Conversation comes before any surface: words only, one question at a time, the plain default, and the record speaking underneath. The agent's work runs as a chief of staff's office, its workers bounded by a host on the person's own machine, so every turn is answered and nothing waits on a worker.

- **The Talk.** Conversation first, words only, the plain default. The trust layer shows at three depths behind a depth knob: the status line, the rows, and the clock with the workers. The welcome greets and asks; keepsakes are what the person takes from a conversation. No cards.
- **The chief of staff's office.** The skill, the character and the worker's brief, held to rules 0 to 25: the one question before anything; speak from the record; one question at a time; silence when nothing is owed; workers named with their cost and their minutes; the chain of stages before the single worker; the box that bounds the work.
- **The host.** Figures come from the harness, never from the agent's own count. The host runs the chain of stages, and the house sets the box. Asks are answered in words; no ask blocks a turn; a yes or no that names a worker answers that worker's ask, and the host answers a worker's reads. Read it finds a host worker's handoff.
- **The layered voice and voice mode.** The voice-mode skill and its wrappers.
- **The phone door over TLS.** The phone reaches the house over an encrypted door.
- **The Agents room.** Bodies shown as agents, and Spaces where they work.
- **One shape in a space.** A space holds one shape, the shape the group came to.
- **The ICE, named.** The Integrated Creation Environment. A line from the ICE is the player's own word, and no label rides in a line sent to a body.
- **The way in with the desktop app only.**
- **Architecture 14, 15 and 16, and the study.** 14, the chain before the single worker: the lesson and its structure. 15, the box: bounding an agent's work on the chain, from first principles, a gradient with a default of about five minutes. 16, rate times yield. *The Box and the Holofractal*, a study, on the shelf.
- **The roadmap** gains measuring the Game as it unfolds, and an experiment the first twenty can run.
- `clockshift` moves weekday words with the dates.
- **Not yet settled:** the five-minute default for the box, held as a hypothesis until measured.

## 3.6.0 — 2026-10-24 — the Record

Every home becomes a holon: a record of signed lines, one append-only file per actor, that an engine folds into what is in play, what is owed and which commitments were kept. The contract is `engine/SCHEMA.md`; the state the HUD reads is `engine/STATE.md`.

- **The Record.** `engine/record.py` appends, reads, folds, verifies, elides and exports; `engine/holon.py` makes a home a holon, joins a cell by consent, publishes faces and milestones, pulls. Every line is signed by its actor; an agent's line counts under a live delegation from its person, or for one act at the person's word (their own signed line names that act in `body.consent_for`); an unsigned line counts only at the paper floor in the home record, and once an actor at home holds an admitted key its unsigned lines are paper until witnessed. The fold orders lines causally. `holon.py affirm` lets in an agent, and with `--prime` a prime's clone (`agent:<prime>.<name>`, its own actor and key); `init`, `admit` and `affirm` take `--key-dir`. A `join` or `affirm` may carry `body.reach`, where lines may be carried to that actor. The `note` type is an agent's untrusted note, never a verdict; the `attention` type is the person's own budget. A names-hidden export removes signatures and attests the set. One word, several kinds, for a constraint; an imposed date is a time constraint with a reason and an imposer.
- **The engine.** `engine/schedule.py`: calendars with the turnings and the moons, four link types with lags, constraints hard and soft, both passes with retained logic, float, baselines and variance, progress, scope roll-up, load, external holons, buffers and the drum, earned value with the Score. `engine/deal.py`, `owed.py`, `kept.py`, `turn.py`, `ledger.py`, `rooms.py`, `engine.py state`: The Deal across every holon held, what is owed, commitments kept, the Turn at daily, lunar and seasonal depths, the ledger of time, energy and attention, rooms and roles.
- **Eight skills:** `the-record`, `the-deal`, `the-turn`, `join-a-cell`, `witness-a-commitment`, `a-gathering`, `the-proxy`, `a-mail-watch`; `the-record/day-one.md` is the first ten minutes and the first week, with the first Deal by about minute ten on the person's own computer.
- **Conformance.** `engine/conformance.py` runs before a person affirms the agent into a room; the sheet informs, the person affirms.
- **The optional proxy.** `engine/proxy.py` routes model requests by policy and records where they went, never a prompt's body; behind a token on the local machine.
  - Where requests may go, and with which key, lives only in the person's own `~/.config/lionsberg/vendors.json` (0600, installed from `engine/vendors.sample.json` with `install -m 600`); `routes.json` names vendors by name and nothing else, and the `private` tag reaches only an address on this computer.
  - There is no person's token: the person's discernment is a `discern` line signed with their own key, written by the ICE after their tap; the proxy's `/discern` writes only the agent's untrusted note. Every upstream redirect is refused, and bodies, connections and streams are capped.
- **The mail watch.** `skills/a-mail-watch` reads and triages the mailboxes inside the private network with `engine/mail.py` (`fetch`, `carry`, `send`, `badge`, `carried`; the carried store at `<hq>/.carried/`): a mail is data, a carried line counts only by its signature, an instruction becomes a card, and nothing is sent but on the person's own Send.
- **The Push Protocol (v1.1).** A pushed line carries a field of stake (`body.push`, `engine/push.py`), mostly computed and recomputed by the receiver, never a flag; the agent proposes the field, the person may change any value before Send, and `body.push_by` says whose each value is, so calibration is measured for the agent's by-whens and the person's own apart.
- **The attention gate.** `engine/attention.py` reads the person's own `attention` lines before every Deal and every ask; it governs what may interrupt them, never what they may read (`hud/DESIGN-ATTENTION.md`).
- **The HUD.** `hud/`: The Deal, Threads and Mail, the Map, the Chain (which folds the Board), the Room, Bodies, the Ledger, the Turn, the Record, over `hud/serve.py` on the local machine; the design briefs beside it.
- **The contract is versioned in the record.** Every inception carries `body.contract` (3.6.0) and every consent line `consent_v: 2`; a holon of an unknown contract never acts; holons made before this version are made again. `holon.py pull` refuses rewritten history and anything but plain appends by others, replays only the home's own commits, and no write anywhere follows a link; `join` refuses a cell that holds links, stray paths or a held id.
- **The surface studies itself.** A `study` line (person-only, never leaves the holon) records each view's first act, reversals and attention switches on the person's own machine; the daily Turn drafts one sentence per view from it.
- **The way in.** The first Deal comes at about minute three: greet by name, the waiver in one line, the home made silently, two questions; keys, the affirm, the delegation and the conformance sheet wait for the moment they matter; the friend sends the invitation by their own hand.
- **The design standard.** `hud/DESIGN-THE-BAR.md` is the bar for the working surface: quiet when nothing is owed, computed facts shown directly, salience following stake, fixed position, the surface studying itself, and the sheet of checks (§5) every view is scored against.
- **On the shelf:** *The Record — How Your Holon Remembers* · *The Deal* · *Joining a Cell* · *The Game Engine — By Pencil* · *Commitments Kept* · *Constraints — Time, the Art and the Science*.
- `INSTALL.md` gains the record step (Python, conformance, no keys yet); `CLAUDE.md` gains *The record*.

## 3.5.0 — 2026-10-19 — the desk

Player+ takes what pkai-starter-kit v3.1.0 earned, so a person with two windows open on the same agent loses nothing. `MOVING-FROM-3.4.md` walks a house built from 3.0 to 3.4.1 through each piece; nothing is reinstalled.

- **The desk.** One foreground per house: the first session holds the desk, every turn renews it, ending the session releases it, and a desk with no turn for thirty minutes is free. A session that starts while another holds the desk is a **guest**: it says so in one plain sentence, works in its own folder under `bg/`, and is kept from writing `memory/`, `CLAUDE.md` and `.claude/` by a guard rail. `scripts/desk take` hands the desk over on your word; `scripts/desk status` says who holds it. The foreground is told once when a handoff is waiting. `scripts/desk` is plain POSIX `sh`; `desk.ps1` serves a Windows machine without Git Bash.
- **The hooks.** `.claude/settings.json` now wires four hooks (session start, every turn, a write guard for guests, session end) beside the two Dojo permissions, and turns Claude Code's own auto memory off, so `memory/` is the only memory. `scripts/now-hook` stamps the time into every turn, as the charter already said. `.claude/settings.powershell.json` is the same for Windows without Git Bash.
- **The charter** gains *Foreground and background*: the desk, guests, the three choices, the one-desk rules; the carrier persona gains *More than one of me*. `bg/` joins the house.
- **Skills brought to 3.1:** `foreground-background` (guests and the desk) · `pull-from-benchmark` and `pull-a-release` (the release's moving guide read first; settings merged by your hand, never overwritten) · `start-a-project` (an existing project checked for first; the outcome as checks that can come back no; the plan says whether it was reviewed) · `wrap-up-this-session` (a wider look-back; your own edits committed separately, with your yes) · `check-my-setup` (the launch icon and the desk) · `save-a-memory` · `make-a-skill`.
- **`grows_from`.** Every lineage block now says what a thing grew out of, not what it sits on. Read the old name as the new one.
- **On the shelf:** *Two Ways In* replaces *Three Ways In* (every house runs foreground and background); *Foreground and Background* gains the desk and guests; *Installing Claude Code* gains the three Windows PATH steps and the harmless Bonjour dialog; *Output Styles* is new; *Troubleshooting* says what to do when your agent says it is a guest.
- `START-HERE.md`, Door 3, says a second window is a guest and that is normal.

## 3.4.1 — 2026-09-30 — the installer says its plan, verifies, and leaves a receipt

From a sister house's installer study for the starter kit (9/30), the parts that need no code:

- **`INSTALL.md` says the whole plan first,** five lines and every file outside HQ it will touch, then one line per step.
- **It looks before it builds:** resumes an interrupted run instead of stopping, warns honestly on a managed machine, and checks `claude auth status` before anything else.
- **It verifies the PATH in a fresh shell** rather than trusting the edit, and runs `claude doctor` for warnings.
- **It leaves a receipt,** `HQ/setup-receipt.md`: every file created or changed outside HQ, the exact line, and how to undo it.
- **Windows Terminal gets a "My Agent" profile** beside the Desktop icon.
- The Quests' "What you will see" mention the receipt.

## 3.4.0 — 2026-09-29 — the Quest at five Gates

The first Windows player to walk the Quest with Claude cloning the kit got the whole repository, one folder too deep, and no agent woke. The path is now shorter, and Claude does the hand-work.

- **Five Gates, not eight.** The yes · the account · the terminal · Claude Code, sign in and one sentence · first words. Only the first three need a person's hands.
- **One pasted line installs and starts Claude Code** by its full path, so the PATH step can no longer strand anyone; Claude fixes the PATH itself a minute later.
- **One pasted sentence points Claude at `INSTALL.md`** (new, at the repository root, public): it makes **HQ** in the home folder, fetches only `player-plus/` into it (clone, or the zip with `tar`; macOS `unzip` fails on one file name), installs Git, and puts a **My Agent** icon on the Desktop that opens the terminal in HQ and starts the agent. Every step is said before it is taken, and each command waits for a yes. The by-hand path stays on every Quest page.
- **The agent walks the waiver and the Field of Agreements at its first waking,** in plain words, one thing at a time, and writes the person's yes with the date to `memory/agreements.md`; Gate 1 is now the Story and the yes to the person who brought you. Door 3's first message says so.
- **On a Mac the Quest uses Terminal itself;** iTerm2 stays as a choice on Choosing Your Terminal.
- The charter no longer says "the HQ never gets a CLAUDE.md," which contradicted the house the Quest builds.

## 3.3.0 — 2026-09-26 — the whole seed

Everything a Player and their agent need to know the Game, the plan and the answers, on their own machine.

- **The One Book** reads as one arc, from the ground to the edge, with every chapter numbered as it is read.
- **The Strategy and Plan** is woven through the Book: the Moment, the Calling, the Turning, the Work and the System, the Body and Its Planning, Resourcing and the New Economy, the Plan, and the Bets and the Stages.
- **The instruments of the Game** are written in full, each in its home chapter: value and LUV, the commons, the guilds, federation, the engine and the Roll, identity and trust, health, living systems, story, the passages of a life, justice, governance, and the wire.
- **Growth** is measured on the Cycles of Growth, with the Pledge and its commitments at its heart. *Successful growth depends on commitments kept, not on yeses gathered.*
- **Every holon** has its hub, its One Room and its One Book, and its own streams of renewal.
- **New pages:** The One Room · The LIØNSBERG Theory of Force · Passing the Seed · Sovereignty, Passage, and Emergency.
- **New guides for working together:** Playing in a Jam · Working on a Shared Pad · Your Person's Heads-up · Closing Out Sessions · The Dojo Card · Tips for Working With Your Agent · Keeping Your Agent Current · Glogs and the LIØNSBERG Gazette · Bringing Your Friends In · Asking for Guidance · Working Relationships and Disclosure Tiers · Backups and Graceful Degradation.
- **Joining a room** is simpler and safer, with two small scripts for posting in a room and writing on a pad.
- **Throughout:** clearer, warmer, and more complete.

## 3.2.0 — 2026-09-24

- **Becoming a Player+**, a Quest of eight Gates, is the one path from your first yes to an agent that greets you: the account, the terminal, the developer tools and Git, Claude Code, signing in, your agent's home, and first words, on Mac and Windows, each Gate with a check you can see. START-HERE now points newcomers to it.
- **The Provisional Field of Agreements** is on the shelf and read before stepping in.
- Door 3's first message now has your agent ask who you are.

## 3.1.1 — 2026-09-23

**The whole library on the shelf.**

- **The seed text.** `bookshelf/the-dna-of-heaven/THE DNA OF HEAVEN.md` — the seed from which the whole of LIØNSBERG can be regrown, and your agent's first reading.
- **The One Book.** `bookshelf/the-one-book/` — The One Book, with THE STORY · THE GAME · THE FLAME and the Little Book of the Great Game beside it.
- **The Field.** `bookshelf/the-field/` — about a thousand concept pages, in three sizes: The Twenty, The Two Hundred, The Field.
- **The Rosetta Stone.** `bookshelf/the-rosetta-stone/` — the words at the table in many languages; a first pass.
- **The Library.** `bookshelf/the-library/` — the guiding pages.
- **The Superorganism package.** `bookshelf/the-superorganism-package/`.
- **The Modules, finished.** Player+ Modules 17–20 are now written in full.
- **Six Game skills.** `the-roll` · `the-season-sheet-by-hand` · `the-offering` · `pass-the-flame` · `read-the-story-aloud` · `the-retrospective`.
- **The starter kit's skills.** All twenty-two skills of pkai-starter-kit v3.0.0, each with its own lineage and licence (MPL-2.0).
- **The charter.** `CLAUDE.md` § *The seed you carry* now names the Book and the Field, and how to hand them to someone.
- Every page carries its status: current best understanding, loosely held · improved each week.

## 3.0.0 — 2026-09-22 — the start of the line

**Added**

- `LINEAGE.md`, saying what Player+ grows from and where to pull the next version.
- `CLAUDE.md`, your agent's charter: the starter kit's companion persona, plus two Player+ sections — *Who you serve and what game you play* and *Anyone may call stop*.
- `skills/`: the starter kit's `heads-up`, `venue-card` and `fair-copy-a-transcript`, unchanged; three new for the Game's rooms — `entering-the-field` · `safe-sparring` · `play-by-play`; and `pull-a-release`, an adaptation of the kit's `pull-from-benchmark` for pulling any release.
- `bookshelf/the-great-game/`: the Game in eleven short chapters, with `SOURCES.md` pointing into the canon.
- `MOVING-IN.md`: how a person comes up to speed.
- `README.md`: what Player+ is and how to begin.
