# Lineage — `the-deal`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: the-deal
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "the kit's architecture (The Deal: a few Work Cards sized to the player's time; the opening line of the briefing; one card is always the same question) · LIØNSBERG"
  - "engine/SCHEMA.md and engine/STATE.md (deal(items, actor, minutes, room) → The Deal) · LIØNSBERG"
  - "pkai-starter-kit v3.1.0 · skills/heads-up (each item carries a draft answer, never a blank question) · Peter Kaminski"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house, daily, once the home is a holon
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/the-deal/; the kit's engine/ (holon.py pull; engine.py deal); a door the person chose: their viewer, a message channel they set up, or paper
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
