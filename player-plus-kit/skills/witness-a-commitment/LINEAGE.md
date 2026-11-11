# Lineage — `witness-a-commitment`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: witness-a-commitment
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "engine/SCHEMA.md (kept is claimed by the keeper; witness verifies it; the gap is computed) · LIØNSBERG"
  - "the kit's architecture (kept is claimed, then verified by a fair witness; the one who assigns never audits) · LIØNSBERG"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house whose person is named as a witness
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/witness-a-commitment/; the kit's engine/ (holon.py pull; record.py append); or the cell's sheet
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
