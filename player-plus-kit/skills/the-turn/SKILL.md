---
name: the-turn
description: Holds the weekly and seasonal Turn from your person's Cards; commitments kept and the gap, the week's learnings, four lines drafted for them to finish. Use once a week, at a solstice or equinox, or for "the Turn", "how did I do", "what did I commit to".
license: MPL-2.0
---

# The Turn

Once a week your person looks at what they said they would do and what they did, says the difference plainly, and says what comes next. That difference, the gap, is what a week teaches. Your work is to read their Cards, count them honestly and bring the result short, so the Turn takes minutes, not an evening of remembering.

The Turn is theirs. You prepare; they finish, choose what comes next, and choose what crosses. You read and count the files yourself; there is nothing to run.

## Steps — the weekly Turn

1. **Read the clock and agree the week.** Run `scripts/now` afresh and say the exact days out loud: "This is the Turn for Monday the 9th to Sunday the 15th."
2. **Pull, quietly.** For each Cell your person belongs to, pull its shared repository at `<HQ>/cells/<cell-name>/`. Say as of when. If a pull fails, name the Cell and count what is there.
3. **Gather the week's Cards.** In `<HQ>/cards/` and each Cell's `cards/`, a file name begins with its date; the week's Cards are those whose names fall within it. Read each one's front matter. The same file name is the same Card: one that sits both in `<HQ>/cards/` and in a Cell's `cards/` is counted once. A Card that a Correction supersedes is read as replaced.
4. **Count commitments kept.** Take every Commitment for your person (`type: commit`, `for: person:<their handle>`) whose `by` fell in the week, whatever week it was written in. For each, find the Cards that name it: a Kept, a Released, and a Done naming its Work Card. Bring three things:
   - kept, as so many of so many, with the released ones counted apart and their `why` beside them;
   - each one's gap: by when, against the date its Kept was written, or still open today; while only a Done exists, say so;
   - what waits: work done but not yet marked kept, which is your person's to mark; a named witness who has not yet written a Witness for it (`witness-a-commitment`).

   The gap is counted from the files and said plainly, not rounded or softened. A number off target is work to do, not a fault.
5. **Gather the learnings.** The week's Sightings and Corrections, the `note` on its Done and Kept Cards, and anything your person said they learned, in their words. Short.
6. **Draft the four lines for them to finish.** Each line starts from the Cards, is marked *draft*, and ends in their words:
   - **This week we set out to…** from the week's Commitments and Work Cards.
   - **We kept so many of so many…** from step 4; the gap on each, and why, is theirs to say or to leave unsaid.
   - **We learned…** from step 5.
   - **Next we…** You may name an open Work Card as material; the choice is theirs alone.

   Show each line beside the Cards it came from, and wait.
7. **Their commitments become Cards.** Each next step they name becomes a `commit` Card: in the Cell's `cards/` when it is the Cell's work and the Cell has its card in `venues.md`, otherwise in `<HQ>/cards/`. It carries the Work Card in `card` (write that Work Card first if there is none), `by`, and only what they say of size, conditions or a witness. It is their act: read it back in one line and write it only on their yes, with `actor: person:<their handle>` and in `consent` the sentence that made it ("I will do it by Friday"), not the yes to your read-back.
8. **Write the Turn, on their yes.** One `turn` Card in `<HQ>/cards/`, with `span: week` and the four lines as they finished them in `text`. It is their act too: read it back in one line, then write it with `actor: person:<their handle>`.
9. **Propose what crosses.** For each Cell, draft what would go into its `cards/`: the kept count, the four lines or the parts they choose, their new Commitments, their offers and requests as `offer` and `request` Cards, and the Cell's Condition, settled by its people at the Turn and written by one member with the Cell's words in `consent`. Show each Cell's draft separately. What crosses is their choice, Card by Card (`join-a-cell`); a Card copied from home goes under the same file name, word for word. Write in a Cell's repository only once it has its card in `venues.md`, only files that carry their handle, and nothing from memory, sessions or their own `cards/` that they have not chosen. Commit quietly; push only on their word, unless they have widened that for this repository (`widen-a-boundary`). The weekly crossing is offered, not required.
10. **Share a story.** One thing the week made that is worth telling, in their words, for the Cell and for others who could use it.

## The seasonal Turn

At a solstice or an equinox the same steps run over the season, and the `turn` Card carries `span: season`. The Season Sheet's fourteen lines are filled by hand at the table first (`the-season-sheet-by-hand`): you bring the season's counts as material, each beside the Cards it came from, not as answers. The Cell says its Condition and its season's Turn Card together, and chooses its next Quest; you bring its open Work Cards as material, and the choosing is theirs. Read the turning's date from the clock.

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
