# Lineage — `a-gathering`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: a-gathering
version: 0.2.0
grows_from: player-plus-kit 4.1.0
lineage:
  - "a-gathering 0.1.0, in player-plus 3.6.0 · LIØNSBERG"
  - "heads-up and play-by-play (the private page; the room's page only when the room asks; an idea may travel, its room may not)"
  - "the kit's architecture (The Deal at the start and the end of a meeting; speech is not recorded, only what is settled; export with names hidden and signatures valid) · LIØNSBERG"
  - "Chatham House Rule, as the Game's rooms hold it"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release; its address is in the house LINEAGE.md, under player_plus)
offered_at: every house, from its first room
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/a-gathering/; or a notebook
changes: 0.2.0 — Player+ 4.1: written new for Cards as files, in a house with no game engine
thanks_to: the houses that keep a record — a practice, never a debt
```
