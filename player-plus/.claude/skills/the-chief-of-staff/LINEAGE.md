# Lineage — `the-chief-of-staff`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: the-chief-of-staff
version: 0.1.0
grows_from: player-plus 3.7.0
lineage:
  - "hud/DESIGN-THE-BAR.md §1–3 (the quiet surface that has already done the arithmetic; salience follows stake; the agent reaches the person more often than the person reaches a prompt) · LIØNSBERG"
  - "hud/DESIGN-DOCK.md (one breath; answer first; one offer at most; asks as cards with their what and why) · LIØNSBERG"
  - "hud/DESIGN-BODIES.md §3–4 and §14 (the cycles of hygiene; the cost said first, then the yes; a handoff is one card; a body asks the prime, never the person) · LIØNSBERG"
  - "engine/deal.py (the dealer's order and its framing: question, options, recommendation, why) · LIØNSBERG"
  - "skills/the-deal and skills/the-record (never tick their box; speak from every holon; the four hard stops) · LIØNSBERG"
  - "skills/foreground-background (the background instance's folder, status, handoff and DONE) · pkai-starter-kit v3.1.0"
  - "The practice of Player+s: dashboards do not serve; a few things to discern, asked in conversation, do; watch for interface difficulty and offer a ten-minute try of another way"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every house whose person speaks with their agent in the Talk, on a phone or a computer
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/the-chief-of-staff/; the kit's engine/ (engine.py state); the Talk for starting a worker by the person's tap, or the foreground-background skill in a terminal house
changes: 0.1.0 — first release (Player+ 3.7, the Talk)
thanks_to: the Player+s whose practice shaped it — a practice, never a debt
```
