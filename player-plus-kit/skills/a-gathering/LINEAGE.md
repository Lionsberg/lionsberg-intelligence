# Lineage — `a-gathering`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: a-gathering
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "heads-up and play-by-play (the private page; the room's page only when the room asks; an idea may travel, its room may not)"
  - "the kit's architecture (The Deal at the start and the end of a meeting; speech is not recorded, only what is settled; export with names hidden and signatures valid) · LIØNSBERG"
  - "Chatham House Rule, as the Game's rooms hold it"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house, from its first room
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/a-gathering/; the kit's engine/ (holon.py pull; record.py append and export); the heads-up and play-by-play skills
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
