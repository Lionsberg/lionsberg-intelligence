# Constraints — Time, the Art and the Science

*A date imposed on a plan from outside its own logic. The science is how the date is written and computed; the art is how seldom you set one, and why.*

Most dates in a plan are found, not set. You name the work, how long each piece takes and what waits on what, and the two passes of [[The Game Engine]] tell you when each piece can start and must finish ([[The Game Engine — By Pencil]]). A time constraint is the other kind of date: one the logic did not produce, laid on a card because someone or something outside the plan requires it. Used well, it is how the word you gave and the world you live in reach the schedule. Used badly, it is how a plan learns to lie.

**One word, several kinds.** A [[Constraint]] is anything that binds what work can happen, and when. It comes in kinds. A **resource** constraint is a missing hand, tool or material. An **information** constraint is a missing answer, design or decision. An **agreement** constraint is a yes not yet given: a neighbor, a permit, a condition of satisfaction not yet settled. These three are what the look-ahead finds and the make-ready clears, so that work is ready before anyone commits to it ([[The look-ahead]], [[Make-Ready Process]]). A **time** constraint is a date the work must meet. This page is about that fourth kind. Temporal markers, the solstices, equinoxes and moons the seasons and weeks turn on, are a different concept again: beats of rhythm, never constraints and never milestones ([[Temporal markers apart from milestones]]).

## The technical language

The heavy scheduling engines that plan the largest programs on Earth share one vocabulary for time constraints. You can carry it into the Game unchanged.

**A time constraint** is a date fixed on an activity or a [[Milestone]] that the calculation must respect. Its kinds:

- **Start no earlier than.** The card may not begin before this date, whatever its predecessors say. A delivery that cannot arrive sooner, a hall that is not open until Friday.
- **Finish no later than.** The card must be done by this date. If the logic cannot get it there, the calculation says so.
- **Start on** and **finish on.** The card begins, or ends, on exactly this date. In their mandatory form they pin the date in both passes.
- **As late as possible.** The card is scheduled at the last moment that delays nothing after it, using up its free [[Float]]. Useful for work that should not be done early: perishable goods, a decision best taken with the most information.
- **A project's must-finish-by.** One date for the whole plan. The backward pass runs from it instead of from the latest early finish.

**Hard and soft.** A *hard constraint* pins a date and overrides the logic: the card starts or finishes there even if a predecessor is not done, and the network quietly stops being true. A *soft constraint* leaves the logic alone. A start-no-earlier holds a card back but never pulls it ahead of its predecessors. A finish-no-later or a finish-by acts on the backward pass only: the early dates stay where the work puts them, and the late dates are pulled back to the imposed date.

**Negative float** is what a soft constraint produces when its date cannot be met. If the logic says the work finishes on day 8 and the constraint says day 7, every card on the chain carries a total float of minus one: the plan is a day late before a day of work is done. It is the most honest number a schedule can show. A hard constraint would have hidden it, by moving a date and breaking a link instead.

**The data date** is the morning the plan is true as of ([[Data Date]]). Everything before it is record; everything after it is calculation from the logic that remains. A time constraint is always read against it: a finish-by that was comfortable a month ago may show negative float this morning, because the data date moved and the work did not.

**Retained logic** is the rule for work that was started out of order. Under retained logic, an unfinished predecessor still holds its successor, even if the successor began early. The other school, progress override, lets started work run on regardless. The choice changes the [[Critical Path]]. The Game holds retained logic, because a predecessor not done is news the plan should keep telling.

**Why the discipline rations them.** The best-known checks of schedule health hold hard constraints to a small share of unfinished activities, about one in twenty at most, and ask that every constraint carry a written reason. The cause is simple. Each hard constraint is a place where the plan stops computing and starts asserting. A few are reality. Many are a schedule that has been made to say what someone wanted to hear.

## The science in the Game

The Game keeps the discipline's vocabulary and narrows its use.

**Where a time constraint lives.** By default, on a milestone. A milestone is a threshold the body steers by; a date on it says *by then, this must be so*, and every activity that serves the milestone inherits its finish-by through the backward pass. A time constraint goes on an activity only with a reason that belongs to that activity alone: the timber yard does not open until the 4th; the seed must go in after the last frost.

**What a time constraint carries.** Five things, on the card, every time:

- **kind**: finish-by · start-no-earlier · finish-no-later · start-on · finish-on · as-late-as-possible
- **date**
- **reason**: in a sentence anyone can read
- **imposed by**: the one who holds the date, and the only one who can move it
- **source**, one of three:
  - **a commitment**: someone's word to someone. *We said we would bring the jars to the harvest supper.*
  - **the world**: a harvest, a frost, a launch window, a tide. A solstice can be the reason for a date; it is never itself the date of a piece of work.
  - **a law**: a filing date, a permit that expires, a notice period.

A time constraint without a reason and an imposer is a defect, and the record says so. It is not deleted; it is asked about at the next [[The Turn|Turn]].

**Negative float is shown, never hidden.** The engine computes it, prints it on the card and lists every card that carries it. It does not clamp it to zero and it never moves the logic to make it go away. You read it as one question: *the logic and the word disagree; which gives?* Either the work changes, or the date changes with the one who holds it, or the gap is accepted and said aloud. All three are honest. Silence is the only dishonest answer ([[Honesty about time]]).

**The constraints reading.** At each seasonal turning, and whenever a plan feels tight, read five numbers off the cards:

1. how many time constraints the plan holds
2. what share of the unfinished cards carry one
3. how many are hard and how many soft
4. how many sit on activities rather than milestones
5. how many lack a reason or an imposer

The fifth should be zero. The third and fourth should be small, and each one should be explainable in a sentence. A rising second number is a plan sliding from calculation toward assertion.

**Buffers answer most tempting dates.** Most of the urge to pin a date comes from fear that the work will slip. A [[Buffer]] is the better answer. Plan to finish ahead of the imposed date; hold the time between as pooled contingency, owned by the chain, spent in the open and read at each Turn. The milestone carries two dates for this reason: the plan date the schedule is computed to, and the imposed date, standing beyond it ([[Milestone]]). The time constraint sits on the later date. The buffer protects it. Nothing inside the chain needs pinning at all.

## The art in the Way

The science says how to write a time constraint. The art is in choosing whether to.

**Few, and each a conscious act.** A plan with no time constraints has no top and cannot be wrong. A plan with many has stopped listening to itself. Between them is a plan with a handful, each one chosen, each one readable by a stranger.

**Ask who the date serves.** Before a date goes on a card, the one keeping the plan asks: *whose date is this, and what happens to them if it is missed?* A date that serves a neighbor waiting on your work, a harvest that will not wait, or a law that will not bend, belongs on the plan. A date that serves only the comfort of looking decided does not.

**A commitment is the Game's own constraint.** When you say *I will do this, by then* to someone who depends on it, you have imposed a date on your own plan, and the by-when is that date ([[Commitment]], [[Commitments Kept]]). So the commitment is the natural source of most time constraints, and the person you gave your word to is the natural holder of the date. No body above a Cell pins its dates. A [[Supercell]] that needs a milestone by a date asks for it, and the date enters the Cell's plan only as a commitment the Cell makes. There is no center but ØNE.

**Reviewed at the Turn, like a commitment.** Each time constraint is read at the Turn beside the commitments: still true? still held by the same person? still the right kind? A constraint whose reason has gone is released.

**Released like a commitment.** Releasing a time constraint is a line in the record, with its reason and the holder's word, exactly as a commitment is released ([[Release]], [[Consciously Breaking Commitments]]). The old constraint stays on the sheet, marked released; the new one, if there is one, is a new line. Nothing is erased, so anyone can see when a date moved, who moved it and why.

### By pencil: one milestone that goes negative

A Cell of three grandmothers has said yes to bringing twelve jars of jam to a neighboring Cell's harvest supper on Monday evening. The supper's host asked for the jars by the end of Saturday, to set the hall on Sunday. Day 0 is the morning of Monday the week before.

| # | kind | what | links |
|---|---|---|---|
| 1 | card | **A** Gather the fruit · 3 days | |
| 2 | card | **B** Make the jam · 4 days | after 1 |
| 3 | card | **C** Write the labels · 2 days | |
| 4 | card | **D** Jars at the hall · milestone | after 2 and 3 |
| 5 | commit | D by the end of Saturday · to the supper's host | serves 4 |
| 6 | constraint | time · D finish-by 6 (end of Saturday) · soft · reason: the host sets the hall on Sunday · imposed by: the supper's host · source: commitment, line 5 | on 4 |

The two passes, worked as on the pencil page:

| card | days | early start | early finish | late finish | late start | total float |
|---|---|---|---|---|---|---|
| A | 3 | 0 | 3 | 2 | −1 | **−1** |
| B | 4 | 3 | 7 | 6 | 2 | **−1** |
| C | 2 | 0 | 2 | 6 | 4 | 4 |
| D | 0 | 7 | 7 | 6 | 6 | **−1** |

The logic says the jars reach the hall at the end of Sunday, day 7. The constraint says Saturday, day 6. A, B and D carry minus one. The plan is a day late on Monday morning, with a whole week left to do something about it. The Cell reads the number at its gathering and asks the one question: which gives?

- **Move work.** The labels have four days of float. The grandmother writing them finishes on Tuesday and joins the jam on Thursday, so B takes three days instead of four. B now finishes at 6, D at 6, total float 0. Nothing on the sheet changes but B's days, written as a new line with its reason.
- **Move the date, with the one who holds it.** One of the Cell calls the host: *we can bring the jars Sunday evening; does that work?* The host says Sunday is fine; the tables can be set Monday morning. The Cell writes line 7, releasing the constraint on line 6 at the host's word, and line 8, a new soft constraint, finish-by 7 (end of Sunday), held by the host, its reason restated. The commitment on line 5 is released and remade the same way. Float returns to 0.
- **Accept the gap and say why.** The Cell keeps the date, knows it will miss it by a day, and tells the host now, not on Saturday night. The gap is written on the sheet before it happens, counted when it does, and learned from at the Turn: *jam takes four days in this kitchen; next year, start the week before.*

What the Cell does not do is put a hard constraint on B, *finish on Saturday*, so the sheet shows zero float and everyone feels on time. The jam would still take four days.

At the next seasonal turning the Cell adds one line of learning: plan the jars to be ready two days before the host's date, and hold those two days as a buffer. Next year the constraint stands beyond the plan date, the plan finishes ahead of it, and nobody needs to look at a negative number unless the fruit comes late.

## What never to do

- **Pin a date to hide a gap.** A hard constraint that turns negative float into zero has not saved a day. It has hidden the news from everyone who depends on it, including you.
- **Constrain an activity to force a sort.** A start-on set to make a card appear first in the week, or to push something else down, turns a scheduling tool into a priority shout. Order comes from the logic and the look-ahead ([[SHOULD-CAN-WILL-DID]]).
- **Let a constraint stand without an imposer.** A date nobody holds is a date nobody can move, release or be asked about. It outlives its reason and quietly governs a plan that no longer needs it.

## For a Player+

Your agent shows you every card with negative float and the time constraint it runs against, reads the constraints numbers at each turning, and asks for the reason and the holder whenever a date is imposed without them. It drafts the line when you move work, the release when the holder agrees to a new date, and the note when you accept a gap. It never imposes a date on your plan, never turns a soft constraint hard, and never moves the logic to make a view look calm ([[The Deal]]).

## With a notebook

Draw a small box in the corner of any card that carries an imposed date. In it write five things: the kind, the date, the reason, who holds it, and where it comes from: *word*, *world* or *law*. When you pencil the backward pass, run it from the boxed date and write any negative float in red beside the card. At the Turn, read each box aloud. Cross out a released one, write its reason underneath, and initial it with the holder.

---

*Read next: [[The Game Engine — By Pencil]] · [[Commitments Kept]] · [[The Record — How Your Holon Remembers]] · [[The Deal]] · in the Field, [[Constraint]], [[Milestone]], [[Float]], [[Buffer]], [[Data Date]], [[Honesty about time]] and [[Networks of Commitments]].*

*CC BY-SA 4.0 · LIØNSBERG*
