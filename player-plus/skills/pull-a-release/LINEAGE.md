# Lineage — `pull-a-release`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: pull-a-release
version: 0.1.0
grows_from: player-plus 3.0.0
lineage:
  - "pkai-starter-kit v3.0.0 · skills/pull-from-benchmark (the procedure: one row per change; take · adapt · decline · already better; apply by copying; charter changes by the person's hand; the report back) · Peter Kaminski, MPL-2.0"
  - "pkai-benchmark 3.0.0 · PULL-PROTOCOL.md (benchmark-and-pull, never push-and-replace; the reason is sovereignty, not breakage) · Peter Kaminski"
  - "the LIØNSBERG pull-to-resync beat (each upstream release diffed against our lineage, adopted or declined with reasons; the resync verifies the location, not only the version) · LIØNSBERG"
  - "Player+ Modules · 14 The Agent Improvement Process · LIØNSBERG, CC BY-SA 4.0"
licence: MPL-2.0                          # LICENSE.md in this folder: a modified copy of the kit's pull-from-benchmark; MPL's file-level share-alike keeps it MPL-2.0
credits:
  - "benchmark-and-pull, never push-and-replace, for sovereignty rather than breakage; the house reports what it valued and where it diverged — pkai-benchmark PULL-PROTOCOL"
pull_from: (the Player+ release)
offered_at: stair 4 and up — any house that will take a later release of any line
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/pull-a-release/; a LINEAGE.md in the house with a pull_from
changes: 0.1.0 — first release
thanks_to: LIØNSBERG — a practice, never a debt
```
