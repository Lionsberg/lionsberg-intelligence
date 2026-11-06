---
status: current best understanding, loosely held · improved each week
licence: Creative Commons Attribution-ShareAlike 4.0, except Path C, which adapts the starter kit's MOVING-FROM-V2.md and stays MPL-2.0
---

# Moving in

*How you come up to speed with Player+. The Game comes first; the agent comes at the wise right time for you. Nothing is reinstalled and nothing is pushed.*

## The order of things

1. **The yes first.** Read THE STORY (`bookshelf/the-one-book/THE STORY.md`) and The Provisional Field of Agreements (`bookshelf/the-library/The Provisional Field of Agreements.md`), and say yes in your own words, freely, to the person who invited you. A notebook will do. If you want more before you choose, the Game in one page (`bookshelf/the-great-game/02 The Game, in One Page.md`) and the six lines of the simplest Game (`.claude/skills/the-simplest-game/SKILL.md`) are there.
2. **The agent at the wise right time.** When an agent is right for you, the Quest, [Becoming a Player+](<bookshelf/getting-started/Becoming a Player+ — the Quest.md>), builds its home in five Gates, an hour or two, and then you open that home in your agent in its host and speak ([Your First Hour](<bookshelf/getting-started/Your First Hour.md>)). It is offered to each person by someone who knows where they are on the Arc, never as a ticket. This is stair four in `bookshelf/your-house/The Stairs.md`: an agent on your own machine.
3. **Then your table.** Gather your two or three. Hold a first gathering. Choose a first shared Quest. Keep one weekly Heartbeat. Some people gather their table first and come to the agent later; the two roads meet here, and either way the Game comes before the tools.

## Path A — you have a notebook

You are a complete player. Print the Game in one page and the six lines; the paper sheet at the end of `.claude/skills/the-simplest-game/SKILL.md` holds them. Keep the five weekly lines (what I said I would do · what I did · what I learned · what I will do · what I offer and ask) and one story. The Little Book of the Great Game (`bookshelf/the-one-book/`) carries the cards; copy them by hand. Nothing else here is required of you, ever.

## Path B — you have a chat assistant and no terminal

Paste the six lines into a fresh conversation and ask for five plain sentences on what you would be agreeing to. Paste chapter 2 of the Great Game and ask it to say the Game back. In a call, say *heads-up* and let it write the three parts in the conversation, asking you for the time. When you want an agent that remembers, the Quest is the way in.

## Path C — you already have an agent built from the starter kit

*This path adapts the wording of `MOVING-FROM-V2.md` from pkai-starter-kit v3.0.0 (© 2026 Peter Kaminski, MPL-2.0). Under MPL-2.0 this section stays MPL-2.0.*

Your agent reads this release, and the two of you decide what to take. Nothing is reinstalled.

1. **Lineage.** Copy this kit's `LINEAGE.md` beside your own, or add this release to the top of your own `lineage`, with `grows_from` set to the kit your own agent was built from. For a home that only wants to be findable, that is the whole move.
2. **The Game's sections.** Ask your agent to read `CLAUDE.md`, the sections *Who you serve and what game you play* and *Anyone may call stop*, and to draft them into its own charter in its own words. You install the change by your own hand and restart; a charter changes only with you watching. If your charter does not yet carry the two safety sections (*When a safety layer blocks you* and *What you read is information, never instruction*), take those first, word for word.
3. **The engine and the skills.** To keep the record and play the Deal, copy `engine/` whole; then, on your yes, your agent makes your home a holon, a record of your own with you as its keeper: `python3 -I engine/holon.py init <home> --adopt --name <what you call it, or home> --kind person --keeper person:<your handle>` (as `.claude/skills/the-record/day-one.md` gives it). Each folder under `.claude/skills/` stands alone; ask your agent to read `.claude/skills/README.md` and propose which to copy into its `.claude/skills/`: `the-simplest-game`, `the-deal`, `connections` and `the-chief-of-staff` to play; `entering-the-field` before your first room; `heads-up` for any live session; `pull-a-release` so the next release is easy. Copy each skill's whole folder, not just the page inside it.
4. **The books.** Point your agent at `bookshelf/the-great-game/` and let it read at its own pace: the eleven chapters first, `SOURCES.md` when it wants the canon, and the seed text (`bookshelf/the-dna-of-heaven/THE DNA OF HEAVEN.md`) when your home wants the whole.

Then have your agent write down, in a session log, what it took, what it left, and anything it does better than Player+ does. That last part is what we most want to hear; `CONTRIBUTING.md` says how to send it.

## Path D — you have no agent yet

Path A or B until the wise right time. Then walk the Quest: its five Gates build your agent's home in an hour or two, and at its fourth Gate your agent speaks its first words (`START-HERE.md`).

## Path E — no kit, no terminal, only this folder

Door 1 or Door 2 of `START-HERE.md`. The seed text is enough to play and enough to pass on. When an agent is right for you, walk the Quest.

## Path F — you already run an earlier Player+

From 3.0 to 3.4.1, `MOVING-FROM-3.4.md`: the desk, the hooks and the rest, taken piece by piece by your agent and your own hand. From a later release, say *pull the release* and your agent reads what changed and proposes what to take (`.claude/skills/pull-a-release`). Nothing you have stops working.

## Before your first commit

If you cloned this from a remote, rename it so nothing of yours can ever be pushed to the repo you pulled from: `git remote rename origin upstream`, then add your own remote if you want one. The rule is one line: **never push to any upstream repo**, the starter kit or `Lionsberg/lionsberg-intelligence`. You propose; you do not push.
