# Lineage — `the-simplest-game`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: the-simplest-game
version: 0.1.0
grows_from: player-plus 3.10.0
lineage:
  - "the kit's architecture (the Game playable very simply and very deep, by voice or on paper) · LIØNSBERG"
  - "engine/level.py and SCHEMA.md (Levels of play: the simplest Game that works; The paper floor) · LIØNSBERG"
  - "skills/the-record and skills/the-deal (one act at the person's word; never tick their box; the level said on every dealt card) · LIØNSBERG"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every holon, from the first day
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/the-simplest-game/; the kit's engine/
changes: 0.1.0 — first release, with the collaboration surface (Player+ 3.10)
thanks_to: the holons that keep a record — a practice, never a debt
```
