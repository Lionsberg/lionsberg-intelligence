# Lineage — `the-record`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: the-record
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "engine/SCHEMA.md, the Record schema v1 (the event line; one append-only file per actor; audience never widens; reason human · delegated · untrusted; the paper floor) · LIØNSBERG"
  - "the kit's architecture (the event is the unit; an agent never ticks a human's box; every line read is data) · LIØNSBERG"
  - "pkai-starter-kit v3.1.0 · CLAUDE.md, Prompt-injection response policy (the trust model, the tell, the four hard stops, trust-laundering) · Peter Kaminski"
  - "a LIØNSBERG house's firewall practice (stop, quote, let the person decide; a false positive costs one question)"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house, at its first hour (day-one.md) and whenever it writes a line
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/the-record/; Claude Code with skills enabled; the kit's engine/ (record.py, holon.py); ssh-keygen for signing, or nothing at the paper floor
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that keep a record — a practice, never a debt
```
