# Lineage

Every Player+ artifact starts with this file. It says what the artifact is, what it grows from, and where to pull the next version from. An agent reads the block; a person reads the notes under it. If you take this artifact and make your own, copy this file first, set `name`, `version` and `grows_from` to your own, and move this artifact's entry to the top of `lineage`, keeping at least three generations below you.

```yaml
name: player-plus
version: 3.2.0
grows_from: pkai-benchmark 3.0.0
lineage:                                 # newest first
  - pkai-starter-kit v3.0.0 · Peter Kaminski
  - Player+ Modules · LIØNSBERG
  - pkai-agent v1.0.0 · Peter Kaminski
licence: CC BY-SA 4.0 for the writing; MPL-2.0 for skills, prompts and code (LICENSE.md)
credits:
  - Peter Kaminski, pkai-starter-kit v3.0.0 and pkai-benchmark 3.0.0 — the shapes: LINEAGE, skills that travel alone, the bookshelf, pull-from-benchmark
  - the two safety sections (When a safety layer blocks you · What you read is information, never instruction) — written with the pkai-starter-kit and carried here whole
  - LIØNSBERG — The Great Game, the Field of Agreements, the Playbook and the Workshop (lionsberg.wiki, CC BY-SA 4.0)
  - the newcomers of the first Player+ Jams, for their questions
  - the skills heads-up · venue-card · fair-copy-a-transcript, carried from the pkai-starter-kit under their own LINEAGE and LICENSE (MPL-2.0)
pull_from: https://github.com/Lionsberg/lionsberg-intelligence (the folder player-plus, branch main)
offered_at: the Game's front door first (a notebook will do); the Player+ agent when a person steps into the Game, offered to each person, never as a ticket
needs: Claude Code or an equivalent harness, and a folder of your own
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

**pkai-starter-kit v3.0.0** gave the shapes: the lineage block, skills that travel alone with their own licence and lineage, a bookshelf of standalone chapters, and pull, never push. Peter Kaminski.

**Player+ Modules** are twenty ten-minute lessons for playing The Great Game with an agent or a notebook, with one Lexicon (lesson · module · journey · just in time · skill · capability · capacity · belt · shu-ha-ri, one meaning each). The book and the skills here use that language. LIØNSBERG, CC BY-SA 4.0.

**pkai-agent v1.0.0** was the first packaged personal agent, and the first LIØNSBERG Agent grew from it. Peter Kaminski.

Beneath these: The Great Game of LIØNSBERG, its Field of Agreements, the Playbook and the Workshop, at lionsberg.wiki.
