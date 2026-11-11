# Lineage — `join-a-cell`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: join-a-cell
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "engine/SCHEMA.md (a cell is a holon on the forge; joining is access plus a remote under cells/<name>/; published/) · LIØNSBERG"
  - "the kit's architecture (what crosses a membrane is published; one append-only file per actor; the seasonal signal is the floor) · LIØNSBERG"
  - "entering-the-field and venue-card (a room's terms read at the door; no card, read-only)"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house whose person plays in a cell
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/join-a-cell/; the kit's engine/ (holon.py join, pull, publish); git and access the keeper gives
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
