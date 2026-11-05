# Lineage — `negotiate`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: negotiate
version: 0.1.0
grows_from: player-plus 3.10.0
lineage:
  - "the kit's architecture (the Game Engine as the collaboration surface: carrying an ask from its sending to its resolution) · LIØNSBERG"
  - "engine/negotiation.py and SCHEMA.md (The conversation for action; The sender's word: why, effort, voice; both with Player+ 3.10.0) · LIØNSBERG"
  - "the grammar of moves, from a draft shared between holons on 2026-10-25 · LIØNSBERG"
  - "the conversation for action: Winograd and Flores, Understanding Computers and Cognition (1986)"
  - "the call, the bid, the award and the release: Smith, The Contract Net Protocol (IEEE Transactions on Computers, 1980)"
  - "conditional commitments: Singh, An ontology for commitments in multiagent systems (1999); each move naming what it depends on: Singh, BSPL (AAMAS 2011)"
  - "consent decision-making: objections integrated until none remain"
  - ".claude/skills/receive and .claude/skills/the-record (a Receipt never answers an ask; one act at the person's word) · LIØNSBERG"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every holon, once the home is a holon
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/negotiate/; the kit's engine/
changes: 0.1.0 — first release, with the collaboration surface (Player+ 3.10)
thanks_to: the holons that keep a record — a practice, never a debt
```
