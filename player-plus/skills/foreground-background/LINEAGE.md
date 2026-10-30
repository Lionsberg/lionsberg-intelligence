# Lineage — `foreground-background`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.

```yaml
name: foreground-background
version: 3.1.0
grows_from: pkai-starter-kit 3.1.0          # shipped in the kit; also in pkai-benchmark 3.1.0
lineage:
  - "pkai-starter-kit v3.1.0 · Peter Kaminski"
  - "pkai-starter-kit v3.0.0 · Peter Kaminski"
  - "pkai-starter-kit v2.0.0 · Peter Kaminski"
  - "pkai-agent v1.0.0–v1.2.0 · Peter Kaminski"
  - "the PKAI Founders KB · Agentic AI with Pete, Founders Cohort 2026 · Peter Kaminski and the participants"
licence: MPL-2.0                          # LICENSE.md in this folder
credits:
  - "the foreground/background practice of pkai-agent (task → status → handoff → done; the foreground integrates by copying), and the pairs persistent/ephemeral, host/guest, definitive/provisional"
pull_from: "https://github.com/peterkaminski-ai/pkai-benchmark"   # skills/foreground-background/
offered_at: every house, from setup; used from stair 6
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/foreground-background/
changes: 3.1.0 — guests and the desk; in every house; the lineage field sits_on renamed grows_from; 3.0.0 — first release
thanks_to: "https://peterkaminski.ai"       # a practice, never a debt
```
