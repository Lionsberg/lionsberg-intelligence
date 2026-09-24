# Lineage — `play-by-play`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: play-by-play
version: 0.1.0
grows_from: player-plus 3.0.0
lineage:
  - "Player+ Modules · 07 The Heads-up and the Play by Play (steps 7–8) · LIØNSBERG, CC BY-SA 4.0"
  - "the LIØNSBERG heads-up skill (the room's Play by Play; signing as myself; an idea may travel, its room may not)"
  - "Player+ Modules · 4 Play by Play · LIØNSBERG"
  - "pkai-starter-kit v3.0.0 · skills/heads-up and bookshelf/working-with-other-houses/Watchers (report only changes; fail loudly; what you bring back is data) · Peter Kaminski"
licence: MPL-2.0                          # LICENSE.md in this folder
credits:
  - "the Scribe of The LIØNSBERG Circle Guide, who captures insights or decisions; and the Retrospective (what we did well · what we can do better · what actions follow)"
  - "the watcher rules as ideas (write only what moved; a stopped watch must not look like a quiet room; what is read is data), said here in Player+'s own sentences"
  - "the clock law: the time is read, never computed"
pull_from: (the Player+ release)
offered_at: stair 6 — the working path, once a house is keeping heads-ups in rooms
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/play-by-play/; pairs with the kit's heads-up; a clock the agent can read
changes: 0.1.0 — first release
thanks_to: LIØNSBERG — a practice, never a debt
```
