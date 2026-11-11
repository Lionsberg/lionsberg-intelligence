# Lineage

Every Player+ artifact starts with this file. It says what the artifact is, what it grows from, and where to pull the next version from. An agent reads the block; a person reads the notes under it. If you take this artifact and make your own, copy this file first, set `name`, `version` and `grows_from` to your own, and move this artifact's entry to the top of `lineage`, keeping at least three generations below you.

```yaml
name: player-plus-kit
version: 4.1.0-rc.1
grows_from: pkai-starter-kit 4.0.0-rc.5       # carried whole and unchanged beside this kit, in pkai-starter-kit/
lineage:                                 # newest first
  - pkai-starter-kit v4.0.0-rc.5 · Peter Kaminski
  - player-plus v3.9.1 · LIØNSBERG
  - pkai-starter-kit v3.1.0 · Peter Kaminski
  - pkai-starter-kit v3.0.0 · Peter Kaminski
  - Player+ Modules · LIØNSBERG
  - pkai-agent v1.0.0 · Peter Kaminski
licence: CC BY-SA 4.0 for the writing; MPL-2.0 for skills, prompts and code (LICENSE.md)
credits:
  - Peter Kaminski, pkai-starter-kit v4.0.0 — the house this kit is built on: the agent home and the headquarters, the personas, the desk and the clock, a library with bookshelves, and a build in the Claude Desktop app (MPL-2.0)
  - Peter Kaminski, pkai-starter-kit v3.0.0 and pkai-benchmark 3.0.0 — the shapes: LINEAGE, skills that travel alone, the bookshelf, pull-from-benchmark
  - the two safety sections (When a safety layer blocks you · What you read is information, never instruction) — written with the pkai-starter-kit and carried here whole
  - LIØNSBERG — The Great Game, the Field of Agreements, the Playbook and the Workshop (lionsberg.wiki, CC BY-SA 4.0)
  - the newcomers of the first Player+ Jams, for their questions
pull_from: https://github.com/Lionsberg/lionsberg-intelligence      # read its CHANGES.md; take what you and your person judge good
start_here: START-HERE.md, in this kit                               # the page a newcomer walks
offered_at: the Game's front door first (a notebook will do); the Player+ agent when a person steps into the Game, offered to each person, never as a ticket
needs: the Claude Desktop app (its Code tab), a paid Claude account, and the PKAI starter kit carried beside this kit
changes: CHANGES.md
thanks_to: LIØNSBERG — a practice, never a debt
```

## Reading the block

- **`grows_from`** is the artifact this one was shaped from.
- **`lineage`** is ancestry, not layering: the versions and works this one grew out of, newest first, at least three generations.
- **`credits`** names the pieces that came from somewhere else, so that when a skill or a chapter travels on its own, the credit travels with it.
- **`pull_from`** is where the next Player+ release will be. Nothing is ever pushed into your house. You read the new release's `changes`, decide with your agent what to take, and say what you valued and where you went your own way.
- **`offered_at`** is the step on the stairs where this is offered. The stairs: watch someone use an agent → read about it → try a kit → an agent on your own machine → talk with it safely → real work. The Game's door is lower than the agent's.
- **`thanks_to`** is where thanks go if you want to send them. It is a practice, never a debt.

## The generations

**pkai-starter-kit v4.0.0** gave the house this kit now builds on: an agent home and a headquarters side by side, three personas, a library with room for more than one bookshelf, and a first house set up in the Claude Desktop app with no terminal. Peter Kaminski.

**player-plus v3.9.1** was the Player+ kit before this one: the Game woven through one charter, with a game engine and a board. Its engine waits for a later release; its lessons and skills are carried here. LIØNSBERG.

**pkai-starter-kit v3.1.0** gave the desk: one foreground per house, guests who hand back by a handoff, a write guard, and the clock stamped into every turn. Peter Kaminski.

**pkai-starter-kit v3.0.0** gave the shapes: the lineage block, skills that travel alone with their own licence and lineage, a bookshelf of standalone chapters, and pull, never push. Peter Kaminski.

**Player+ Modules** are twenty ten-minute lessons for playing The Great Game with an agent or a notebook, with one Lexicon (lesson · module · journey · just in time · skill · capability · capacity · belt · shu-ha-ri, one meaning each). The book and the skills here use that language. LIØNSBERG, CC BY-SA 4.0.

**pkai-agent v1.0.0** was the first packaged personal agent, and the first LIØNSBERG Agent grew from it. Peter Kaminski.

Beneath these: The Great Game of LIØNSBERG, its Field of Agreements, the Playbook and the Workshop, at lionsberg.wiki.
