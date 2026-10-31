# Lineage — `say-it-on-the-card`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: say-it-on-the-card
version: 0.1.0
grows_from: player-plus 3.10.0
lineage:
  - "the kit's architecture (one card, everywhere: a note on a card is a line in its Thread; every act says what it does) · LIØNSBERG"
  - "engine/acts.py, engine/acts.json and SCHEMA.md (Messaging: lines, not messages; One card, everywhere: the acts a card offers) · LIØNSBERG"
  - "skills/the-record, skills/negotiate and skills/the-deal (one act at the person's word; an ask with its why and effort; the card's offers) · LIØNSBERG"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: every holon, from the first day
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/say-it-on-the-card/; the kit's engine/
changes: 0.1.0 — first release, with the collaboration surface (Player+ 3.10)
thanks_to: the holons that keep a record — a practice, never a debt
```
