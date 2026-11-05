# Lineage — `the-turn`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: the-turn
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "Player+ Modules · 15 The Weekly Turn (the five lines; kept so many of so many; only a person posts the Turn) · LIØNSBERG"
  - "the kit's architecture (the gap is computed, never remembered; only the person chooses will; the minimum interoperability floor) · LIØNSBERG"
  - "the-retrospective and the-season-sheet-by-hand (review is not self-evaluation; the fourteen lines by hand first)"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house, weekly and at each turning
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/the-turn/; the kit's engine/ (engine.py turn and kept); or a notebook
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
