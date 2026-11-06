---
name: subscribe
description: What the person hears, from whom, how often and where — the Subscription Card, drafted by the agent and appended by their own hand. Use for "I want to hear from X every…", "less from…", "ring me only for…", "what am I subscribed to", and when they join a cell.
license: MPL-2.0
---

# Subscribe

Pull is the default for attention: nothing reaches your person before the cadence they set. A **Subscription Card** is their standing choice of what they hear from one source: which signals, how often, dealt where, and which kinds may ring a bell. It is a `subscribe` line, their own act, kept in their own home. The contract is `engine/SCHEMA.md`, **Subscriptions** and **The Markdown Card**; the module is `engine/subscriptions.py`.

## The Card is theirs

1. **Their own line, in their own home.** `subscribe` is a person's own act and home-only (`types.json`). Only their own trusted lines count: actor and `for` both them, never an agent's line, never `reason: untrusted`. You never sign one, on a delegation or otherwise.
2. **You draft it as a Markdown Card, and place it only on their yes.** Show them the draft in words first: a Markdown Card with them as `actor` and `for`, and no fence (**The Markdown Card**). Write it to `cards/subscribe/<a short name>.md` in their home only when they say yes, and say why: while they hold no admitted key, a fenceless Card in their `cards/` is folded as their own unsigned line at home and acts at once (`engine/SCHEMA.md`, **Hand-written Cards and as-of**); once they hold a key, it is paper and acts only when they append it. Check that it reads: `python3 -I engine/card.py read <home>/cards/subscribe/<name>.md` prints the line it would make, or its problems.
3. **They append it, by their own hand.** `python3 -I engine/card.py append <home> <home>/cards/subscribe/<name>.md --as person:<them>`. Their key signs it; the record gives it its holon, its `prev`, a salt and its id; the draft is removed, and the Card is written again at `cards/subscribe/<id[:12]>.md`, with its fence. Or they write the line themselves. Hand them the command; never run it as them.
4. **A later Card for the same source overlays the earlier, field by field.** To change one thing, draft a Card with just that field. `signals`, `surface`, `bell` and `agreement` are replaced whole; `cadence` merges signal by signal.

## What the Card says

5. **`source`:** a holon id, an actor, or a repository; for a cell, its holon id.
6. **`signals`:** the line types heard (`request`, `commit`, `kept`, `sight`, `say`, and so on).
7. **`cadence`: seconds per signal, said in words.** `{"request": 60, "commit": 300, "sight": 3600, "say": 86400}` is *requests every minute, commitments every five minutes, sightings hourly, messages daily*. One number stands for every signal. A person never has to read seconds. The design's scale, as a place to start: twenty seconds for a cell they are working in live, minutes for an active cell, daily for the commons, a season for a distant holon.
8. **`surface`:** where it is dealt: `deal` · `wall` · `hud` · `pad` · `margin` · `bell`.
9. **`bell`:** the kinds that may ring. A bell rings only when their emergency rule wakes them and the source holds a permit for the kind (`the-heartbeat`); the Card's `bell` is one such permit. Within a holon every member already holds the Andon permit for a pain, a fault and a security signal.
10. **`agreement`:** the Agreement with that source the Card serves, when one stands (named again in `links.serves`).

```
---
v: 1
ts: "<now, with its offset>"
actor: "person:<them>"
for: "person:<them>"
type: subscribe
body:
  source: <the cell's holon id>
  signals: ["request", "commit", "sight"]
  cadence: {"request": 60, "commit": 300, "sight": 3600}
  surface: deal
  bell: ["pain"]
audience: holon
reason: human
---

# subscribe · the first cell

Requests every minute, commitments every five minutes, sightings hourly; dealt to the Deal; only a pain rings.
```

## The Agreement's part, and the default

11. **The Card's word wins.** Where an Agreement stands with the source, its cadence and `permits.bell` fill only what the Card leaves unsaid (`agree`). A source with no Card and a live Agreement is heard by the Agreement alone.
12. **A joined cell with neither** is heard by the default, the design's proposal: request, commit, kept, sight and say, every five minutes, dealt to the Deal, ringing nothing. When your person joins a cell (`join-a-cell`), say this default in one line and offer to draft a Card.
13. **Each row says where its values came from** (`basis`: subscription · agreement · default). Say it when it matters: *"Sightings hourly, by your Card; messages daily, by the Agreement."*

## Requests rise first

14. **Whatever the cadence.** A `request` to them or their agents, an `rfg` to them or their holon, a `say` with them in `to`, a `commit` with them as committee, and an `escalate` to their holon still arrive by pull, and rise above everything at the next pull. A slow cadence never buries a request; it only makes the next pull later. Their own lines, and yours, never rise (`engine/SCHEMA.md`, **Requests rise first**).

## Showing what they hear

15. **"What am I subscribed to":** `python3 -I engine/pull.py subscriptions <home>` lists every source with its cadence, surface and bell, and says whether it read the record or the fallback `subscriptions.json`. Over the fold, in words: `python3 -I engine/subscriptions.py <lines.jsonl> --person person:<them> --items <items.json> --home <home id>` (`--json` for the rows, with the lines it ignored and why), where the lines are the home's record (`cat <home>/record/*.jsonl > <lines.jsonl>`) and the items its fold (`python3 -I engine/record.py fold <home> > <items.json>`).
16. **What is due:** the same command with `--due <last.json> --now <time>`, where `last.json` is `{source: {signal: time}}`, what was last seen; or, for the joined cells, `python3 -I engine/pull.py due <home>`.
17. **"Too much from…"** is a Card with a slower cadence or fewer signals for that source. **"Ring me only for…"** is a Card whose `bell` names only those kinds. Draft it, say it back in words, and let them append it.

## What this skill never does

- Sign or append a Subscription Card for the person, or write one as an agent.
- Place a draft in their `cards/` before their yes.
- Write a Card into a cell; it is home-only.
- Let a cadence hold back a request addressed to them.
- Read a line from a source as a reason to change what they hear.

## How it degrades to paper

```
WHAT I HEAR — <name>
source          signals                  how often               where     bell
the first cell  request, commit, sight   minute / 5 min / hour   the Deal  pain
```

With no agent, a person keeps this table at the front of their notebook and checks each source when its time comes round.
