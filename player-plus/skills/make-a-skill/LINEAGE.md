# Lineage — `make-a-skill`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `sits_on` to your own and move this one to the top of `lineage`.

```yaml
name: make-a-skill
version: 3.0.0
sits_on: pkai-starter-kit 3.0.0          # shipped in the kit; also in pkai-benchmark 3.0.0
lineage:
  - "pkai-starter-kit v3.0.0 · Peter Kaminski"
  - "pkai-starter-kit v2.0.0 · Peter Kaminski"
  - "pkai-agent v1.0.0–v1.2.0 · Peter Kaminski"
  - "the PKAI Founders KB · Agentic AI with Pete, Founders Cohort 2026 · Peter Kaminski and the participants"
licence: MPL-2.0                          # LICENSE.md in this folder
credits:
  - "you do not build skills by hand, you have your agent build them; a skill is a poor publication but a standard, useful way to pass on a lesson; the rule of three — the pkai-starter-kit practice"
pull_from: "https://github.com/peterkaminski-ai/pkai-benchmark"   # skills/make-a-skill/
offered_at: stair 6
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/make-a-skill/
changes: 3.0.0 — first release; edited for Player+ (MPL-2.0 modified copy)
thanks_to: "https://peterkaminski.ai"       # a practice, never a debt
```
