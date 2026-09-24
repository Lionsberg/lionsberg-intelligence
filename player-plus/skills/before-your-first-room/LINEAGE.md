# Lineage — `before-your-first-room`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `sits_on` to your own and move this one to the top of `lineage`.

```yaml
name: before-your-first-room
version: 3.0.0
sits_on: pkai-starter-kit 3.0.0          # shipped in the kit; also in pkai-benchmark 3.0.0
lineage:
  - "pkai-starter-kit v3.0.0 · Peter Kaminski"
  - "pkai-starter-kit v2.0.0 · Peter Kaminski"
  - "pkai-agent v1.0.0–v1.2.0 · Peter Kaminski"
  - "the PKAI Founders KB · Agentic AI with Pete, Founders Cohort 2026 · Peter Kaminski and the participants"
licence: MPL-2.0                          # LICENSE.md in this folder
credits:
  - "the Player+ module Before Your First Room, and the pre-flight a person runs before accepting an invitation to a shared pad"
pull_from: "https://github.com/peterkaminski-ai/pkai-benchmark"   # skills/before-your-first-room/
offered_at: stair 6 — before the first room
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/before-your-first-room/
changes: 3.0.0 — first release
thanks_to: "https://peterkaminski.ai"       # a practice, never a debt
```
