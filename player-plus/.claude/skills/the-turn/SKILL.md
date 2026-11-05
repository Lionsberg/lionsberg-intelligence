---
name: the-turn
description: The weekly and seasonal Turn from the record — pull every holon, freeze the plan's baseline, count commitments kept and the gap per commitment, gather the week's learnings, draft the four lines for the person to finish (we set out to · we kept so many of so many · we learned · next we), write the turn event on their word, and propose what to publish to each cell. Use once a week at the hour the person keeps, at a solstice or equinox, when the person says "the Turn", "let us do the week", "how did I do", "what did I commit to", or before a cell's weekly gathering.
license: MPL-2.0
---

# The Turn

Once a week your person looks at what they said they would do and what they did, says the difference plainly, and says what comes next. That difference, the gap, is the only genuinely new thing a week produces. The record already holds most of what the Turn needs; your job is to bring it, honestly and short, so the Turn takes minutes and not an evening of remembering.

The Turn is theirs. You prepare; they finish, sign and choose what crosses.

## Steps — the weekly Turn

1. **Pull every holon,** home and every cell, and fold (`the-record`, rule 17). Say as of when.
2. **Agree the week.** The exact days, said out loud: "This is the Turn for Monday the 19th to Sunday the 25th." Read the dates from the clock; never compute them from an earlier stamp.
3. **Draft the Turn from the engine.** Run `python3 -I engine/engine.py turn <home> --actor person:<them>`. The engine reads the date and turns at the depth it calls for; to choose, pass `--depth daily`, `--depth lunar` (at the new and the full moon) or `--depth seasonal` (at a solstice or an equinox). It drafts the four lines and the unsigned `turn` line used below. **To freeze the baseline,** add `--freeze`: the engine writes the next `plan/baseline-<n>.json`, and later variance is measured against it. If its answer says no baseline was written, tell your person so, in one line; never say a baseline was frozen when none was. The engine writes the plan; nothing else does.
4. **Count commitments kept.** Run the engine's kept command (`python3 -I engine/engine.py kept <home> --actor person:<them> --days 7`) for the week. Bring three things: kept as so many of so many; each commitment's gap (by when, against when it was done or claimed kept); and any commitment still waiting on a witness. The gap is computed, never remembered and never softened. A number off target is work to do, never a fault.
5. **Gather the learnings.** The week's `learn` lines, the answers to the standing question from each Deal, any `discern` lines where your person corrected you. Short; their words where they wrote them.
6. **Draft the four lines for them to finish.** Each line starts from the record, is marked *draft*, and ends in their words:
   - **This week we set out to…** drafted from the cards at *will* and *did*.
   - **We kept so many of so many commitments…** drafted from the kept count; the gap on each, and why, is theirs to say, or to leave unsaid.
   - **We learned…** drafted from step 5.
   - **Next we…** The engine may name a card waiting at *will* as material; you never choose for them. Only the person chooses *will*.
   Show each line beside what it was drawn from, and wait. With an offer and a request beside them, these make the Turn's five lines as the kit's weekly Turn teaches them.
7. **Their commitments become lines.** Each *will* they name becomes a `commit` line: the card, by when, its size in minutes, the conditions, and a witness if they name one. It is their act, and reaches the record by their own hand, or at their word: you write it as your own line, signed with your own key, `for` them, `reason: human`, with their words in `body.consent` and their own signed `say` carrying the same words named in `links.answers` (`the-record`, rule 8).
8. **Write the turn event, on their word.** One `turn` line in their home, linking the baseline, the kept count and the four lines. It is their act, and reaches the record by their own hand or at their word, with their words in `body.consent` and their own signed `say` carrying the same words named in `links.answers` (`the-record`, rule 8).
9. **Propose what to publish.** For each cell they are part of, draft what would cross: the kept count, so many of so many; their four lines, or the parts they choose; their new commitments' faces; their offers and requests. Show each cell's draft separately. Nothing crosses without their yes for that cell, this week (`join-a-cell`). A cell's minimum is one seasonal signal; the weekly Turn is offered, never required.

## The seasonal Turn

At a solstice or an equinox the same steps run over the season, and three things are added: the season's baseline is frozen (`--depth seasonal --freeze`) and kept beside the earlier ones; the Season Sheet's fourteen lines are filled by hand at the table first (`the-season-sheet-by-hand`), and you bring the counts as material, never as answers; and the cell's one seasonal signal is drafted for the cell's people to ratify together. The date of a turning is read, never computed.

## What this skill never does

- Choose what the person will do.
- Soften, round or explain away a gap.
- Write the `commit` or `turn` lines on a standing delegation, or without their words for that act.
- Publish anything to a cell without the person's yes for that cell, that week.
- Grade the person. The Turn looks at the work and the set-up, never at the worth of the worker; if a look-back on the week is wanted, a reader that did not do the work writes it (`the-retrospective`).
- Make the Turn long. Twenty minutes alone; less with the record's help.

## How it degrades to paper

```
TURN — week of <date>                     kept ___ of ___
We set out to   ________________________________________
We kept         ___ of ___   the gap: ______________________
We learned      ________________________________________
Next we         ________________ by ______  witness ______
Offer ______________________   Request ______________________
```

Carry last week's sheet to this week and read its commitments aloud before writing new ones. It works with no agent at all.
