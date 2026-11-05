# Lineage — `a-mail-watch`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.


```yaml
name: a-mail-watch
version: 0.1.0
grows_from: player-plus 3.6.0
lineage:
  - "hud/DESIGN-MAIL.md, sections 1, 5, 7 and 10 (one record, many transports; notifications as a Deal of one card; the firewall for mail; the mail transport and the mail-watch office) · LIØNSBERG"
  - "engine/SCHEMA.md (the event line; reason untrusted is a proposal only; the Push Protocol's field of stake) · LIØNSBERG"
  - "pkai-starter-kit v3.1.0 · CLAUDE.md, Prompt-injection response policy (the trust model, the tell, the four hard stops, trust-laundering) · Peter Kaminski"
licence: MPL-2.0                          # LICENSE.md in this folder
pull_from: (the Player+ release)
offered_at: any house that reads mail through its agent; never required
needs: Claude Code with skills enabled; installed at <agent home>/.claude/skills/a-mail-watch/; the kit's engine/mail.py; a mailbox reachable inside the private network
changes: 0.1.0 — first release, with the Record (Player+ 3.6)
thanks_to: the houses that read their mail as data — a practice, never a debt
```
