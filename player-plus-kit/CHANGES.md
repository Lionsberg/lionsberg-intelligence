# Changes

Written for an agent to read when it pulls a new release. Newest first. Each entry says what changed and why, so that a house can decide what to take; nothing here installs itself. Releases before 4.1 are in this repository's history.

## 4.1.0-rc.1 — 2026-11-19

*Revised 2026-11-22, before its first public release: the LIØNSBERG Wiki travels in the kit as a shelf of the library; the charter block carries a map of the wiki, the Story and the moves; the seven pages to read first live in the wiki, beside The Invitation; at the third Gate the builder makes the headquarters itself; Your First Hour is written afresh.*

**Player+ on the PKAI starter kit 4.1, as its keeper ships it, with the same number.** The first release candidate. It builds a first house in the Claude Desktop app, with no terminal. A house built from Player+ 3.x is not changed by this release and can keep playing as it is; a page for moving such a house will follow once 4.1 is proven. This candidate has passed its suites and two fresh builds by agents; it has not yet been walked by a person on a clean Mac and a clean Windows computer.

**The shape**

- **The starter kit is carried whole and unchanged** in `pkai-starter-kit/` (4.1.0-rc.1). A house is built by that kit's own `BUILD.md`; this kit's `BUILD.md` says only what Player+ adds and at which step.
- **The Game lives in the charter as one marked block,** about 3,200 words, between `<!-- Player+ begins` and `<!-- Player+ ends -->`: the Goal and the compass, the Story and the moves in the Game's own words, the pages to read first, whom the agent serves, the Field of Agreements, the words, the Cards, hearing a Card, where to find more, and the map of the LIØNSBERG Wiki. Every other line of the charter is the starter kit's persona, or the person's own.
- **`PLAYER-PLUS.md`,** beside the charter, is the longer guide, read when a question needs it.
- **Play is written as Cards:** plain Markdown files, one per act, in `cards/` in the HQ and in a Cell's shared repository. The form is the one the Game's engine reads as a hand-written Card.
- **The library has two bookshelves side by side:** the starter kit's at `library/pkai/`, and LIØNSBERG's at `library/lionsberg/`, with `wiki/` (the LIØNSBERG Wiki, carried as one archive, `wiki.tar.gz`, and unpacked at the build; the seven pages to read first are in it, beside The Invitation) and `playing/` (the practical books, each marked as not yet reviewed line by line).
- **Sixteen Player+ skills** that need no engine. Eight are written new for Cards as files: `the-simplest-game`, `the-turn`, `a-gathering`, `join-a-cell`, `witness-a-commitment`, `pass-the-flame`, `refresh-the-library` and `pull-a-release`. Eight are carried with small changes.

**Held for a later release**

- The game engine, the board, the heartbeat and the daily Deal, until they are proven in real play. They will arrive as a skill from the Game's catalog.
- The scripts for posting in a room and writing on a pad, and the pages that taught them.
- The wider shelves of the LIØNSBERG Commons. A person may add a shelf of their own beside the two.
- The character matrix of Player+ 3.x. The three personas are the starter kit's, and Chief of Staff is recommended, as that kit recommends.

**For a house that pulls this**

- A 3.x house: nothing to take yet. Wait for the moving page.
