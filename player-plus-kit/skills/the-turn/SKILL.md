---
name: the-turn
description: Holds the weekly and seasonal Turn from your person's Cards; commitments kept and the gap, the week's learnings, four lines drafted for them to finish. Use once a week, at a solstice or equinox, or for "the Turn", "how did I do", "what did I commit to".
license: MPL-2.0
---

# The Turn

Once a week your person looks at what they said they would do and what they did, says the difference plainly, and says what comes next. That difference, the gap, is the one genuinely new thing a week produces. Their Cards already hold most of what the Turn needs. Your work is to read them, count them honestly and bring the result short, so the Turn takes minutes, not an evening of remembering.

The Turn is theirs. You prepare; they finish, choose what comes next, and choose what crosses.

You read and count the files yourself; there is nothing to run. A later release adds a game engine that will do the counting; this house does not hold it.

## Steps — the weekly Turn

1. **Read the clock and agree the week.** Run `scripts/now` in your agent's home and say the exact days out loud: "This is the Turn for Monday the 9th to Sunday the 15th." Read the dates from the clock, not from an earlier stamp.
2. **Pull, quietly.** For each Cell your person belongs to, pull its shared repository at `<HQ>/cells/<cell-name>/`. Say as of when. If a pull fails, name the Cell and count what is there.
3. **Gather the week's Cards.** In `<HQ>/cards/` and each Cell's `cards/`, a file name begins with its date; the week's Cards are those whose names fall within it. Read each one's front matter. A Card that a Correction supersedes is read as replaced.
4. **Count commitments kept.** Take every Commitment for your person (`type: commit`, `for: person:<their handle>`) whose `by` fell in the week, whatever week it was written in. For each, find the Cards that name it: a Kept whose `commitment` is its file name, a Released, and a Done naming the Work Card in its `card`. Bring three things:
   - kept, as so many of so many, with the released ones counted apart and their `why` beside them;
   - each one's gap: by when, against the date of its Done or Kept, or still open today;
   - what waits: work done but not yet marked kept, which is your person's to mark; a named witness who has not yet written a Witness for it (`witness-a-commitment`).

   The gap is counted from the files and said plainly, not rounded or softened. A number off target is work to do, not a fault.
5. **Gather the learnings.** The `note` on the week's Done and Kept Cards, the week's Sightings, and anything your person corrected in you this week. Short; their words where they wrote them.
6. **Draft the four lines for them to finish.** Each line starts from the Cards, is marked *draft*, and ends in their words:
   - **This week we set out to…** from the week's Commitments and Work Cards.
   - **We kept so many of so many…** from step 4; the gap on each, and why, is theirs to say or to leave unsaid.
   - **We learned…** from step 5.
   - **Next we…** You may name an open Work Card as material; the choice is theirs alone.

   Show each line beside the Cards it came from, and wait. With one offer and one request, these are the five lines of the weekly Turn.
7. **Their commitments become Cards.** Each next step they name becomes a `commit` Card in `<HQ>/cards/`: the Work Card it carries in `card` (write that Work Card first if there is none), `by`, its `size`, any `conditions`, and a `witness` if they name one. It is their act: read it back in one line and write it only on their yes, with `actor: person:<their handle>` and their exact words in `consent`.
8. **Write the Turn, on their yes.** One `turn` Card in `<HQ>/cards/`, with `span: week` and the four lines as they finished them in `text`. It is their act too: read it back in one line, then write it with `actor: person:<their handle>`.
9. **Propose what crosses.** For each Cell, draft what would go into its `cards/`: the Turn or the parts of it they choose, their new Commitments, their offers and requests as `offer` and `request` Cards. Show each Cell's draft separately. What crosses is their choice, Card by Card (`join-a-cell`). Write in a Cell's repository only once it has its card in `venues.md`, only files that carry their handle, and nothing from memory, sessions or their own `cards/` that they have not chosen. Commit quietly; push only on their word, unless they have widened that for this repository (`widen-a-boundary`). The weekly crossing is offered, not required.

## The seasonal Turn

At a solstice or an equinox the same steps run over the season, and the `turn` Card carries `span: season`. Two things are added. The Season Sheet's fourteen lines are filled by hand at the table first (`the-season-sheet-by-hand`): you bring the season's counts as material, each beside the Cards it came from, never as answers. And the Cell's one seasonal signal is drafted for the Cell's people to settle together. Read the turning's date from the clock.

## What this skill never does

- Choose what the person will do.
- Soften, round or explain away a gap.
- Write a `commit` or `turn` Card on a standing delegation, or without their words for that act.
- Edit or delete a written Card; a change is a new Card that names it.
- Put anything into a Cell's repository without the person's yes for that Card, or push without their word.
- Grade the person. The Turn looks at the work and the set-up, not at the worth of the worker; if a look-back on the week is wanted, a reader that did not do the work writes it (`the-retrospective`).
- Make the Turn long. Twenty minutes alone; less with the Cards' help.

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
