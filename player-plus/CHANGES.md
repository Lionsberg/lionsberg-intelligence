# Changes

*Newest first. Each entry says what changed and why, so your agent can read a release and you two can decide what to take. Nothing here installs itself; `skills/pull-a-release` walks you through a pull.*

## 3.4.1 — 2026-09-30 — the installer says its plan, verifies, and leaves a receipt

From Freya's installer study for Pete's kit (9/30), the parts that need no code:

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
