# Lineage — `witness-a-commitment`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: witness-a-commitment
version: 0.2.0
grows_from: player-plus-kit 4.1.0
lineage:
  - "witness-a-commitment 0.1.0, in player-plus 3.6.0 · LIØNSBERG"
  - "the Game engine's record contract (kept is claimed by the keeper; witness verifies it; the gap is computed) · LIØNSBERG"
  - "the kit's architecture (kept is claimed, then verified by a fair witness; the one who assigns never audits) · LIØNSBERG"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release; its address is in the house LINEAGE.md, under player_plus)
offered_at: every house whose person is named as a witness
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/witness-a-commitment/; or a notebook
changes: 0.2.0 — Player+ 4.1: written new for Cards as files, in a house with no game engine
thanks_to: the houses that keep a record — a practice, never a debt
```
