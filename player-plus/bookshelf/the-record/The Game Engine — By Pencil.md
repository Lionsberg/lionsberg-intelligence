# The Game Engine — By Pencil

*Everything the engine computes, worked by hand on one sheet: the schedule, what is owed, commitments kept and the buffers. Same lines, same answers. A person with no computer can run the Game from this page.*

[[The Game Engine]] is a set of plain rules applied to a record. A machine applies them quickly; a person with a pencil applies them slowly; both get the same numbers. The rules come first and the programs are conveniences. If a program and a careful pencil disagree, check the pencil, then fix the program.

You need a sheet of paper, a pencil, and an afternoon the first time. After that, a Cell's week takes a few minutes.

## 1. One event is one line on a sheet

Rule a sheet into seven columns:

**time · who · for whom · kind · what · links · audience**

Every [[Event]] is one line. Number the lines down the page; the number is the line's name, and a link is written as the number of the line it points to. Sign each line with your initials (or have the person whose word it is sign it). A witnessed paper sheet outranks a typed copy of it.

Here is the start of a Cell's sheet for a small [[Quest]]: four raised garden beds, planted before the frost. The Cell has three people, called here by their roles: the host, the builder and the gardener.

| # | time | who | for whom | kind | what | links | audience |
|---|---|---|---|---|---|---|---|
| 1 | Mon 2 Nov 09:10 | host | host | card | **A** Agree the plot · 2 days | | members |
| 2 | Mon 09:12 | host's agent | host | card | **B** Write to the neighbors · 1 day | after 1 | members |
| 3 | Mon 09:14 | host | host | card | **C** Gather the neighbors' yes · 2 days | after 2 | members |
| 4 | Mon 09:15 | builder | builder | card | **D** Build the beds · 5 days | after 1 | members |
| 5 | Mon 09:16 | builder | builder | card | **E** Planting day · 1 day | after 3 and 4 | members |
| 6 | Mon 09:30 | host | host | commit | A by Tue 3 Nov · witness: gardener | serves 1 | members |

*Who* is whoever wrote the line. *For whom* is the person who answers for it: for a person, themselves; for an agent, the person it acts for. Line 2 was written by the host's agent, and the host answers for it.

**Reading a card's state.** A card is born on one line and changed only by later lines that point to it. To know where card D stands, read down the sheet for every line that links to line 4. The latest one says where it is. This is called *folding*, and it is all the engine does before it computes anything.

## 2. The two passes

Count time in days from the start. Day 0 is the morning of Monday 2 November. A card that "finishes at 2" finishes when two full days have passed, at the end of Tuesday 3 November. A card waits for every card it comes *after* ([[Predecessor - Successor]]).

**The forward pass: early dates.** Go down the cards in order.

- A card with nothing before it starts at 0.
- Otherwise, its **early start** is the *largest* early finish among the cards it comes after.
- Its **early finish** is its early start plus its days.

**The backward pass: late dates.** Go up the cards in reverse.

- The end of the plan is the largest early finish (here, 8), or a finish-by date if the Cell has one.
- A card with nothing after it has its **late finish** at the end.
- Otherwise, its late finish is the *smallest* late start among the cards that come after it.
- Its **late start** is its late finish minus its days.

**Float.** For each card:

- **Total float** = late start − early start. How far it can slip before the end moves.
- **Free float** = the smallest early start among the cards after it, minus its own early finish (for the last card, the end minus its early finish). How far it can slip before the next card is delayed.

Worked on the five cards:

| card | days | after | early start | early finish | late start | late finish | total float | free float |
|---|---|---|---|---|---|---|---|---|
| A | 2 | none | 0 | 2 | 0 | 2 | **0** | 0 |
| B | 1 | A | 2 | 3 | 4 | 5 | 2 | 0 |
| C | 2 | B | 3 | 5 | 5 | 7 | 2 | 2 |
| D | 5 | A | 2 | 7 | 2 | 7 | **0** | 0 |
| E | 1 | C, D | 7 | 8 | 7 | 8 | **0** | 0 |

The working, line by line:

- Forward. A: 0 + 2 = 2. B: after A, starts 2, finishes 3. C: after B, starts 3, finishes 5. D: after A, starts 2, finishes 7. E: after C (5) and D (7); the larger is 7, so E starts 7 and finishes 8.
- Backward from 8. E: finishes 8, starts 7. D: comes before E, so finishes 7, starts 2. C: comes before E, finishes 7, starts 5. B: comes before C, finishes 5, starts 4. A: comes before B (late start 4) and D (late start 2); the smaller is 2, so A finishes 2 and starts 0.
- Float. B can slip 2 days before the end moves, but not one day before C is delayed: its free float is 0, because C is waiting on it. C can slip 2 days on its own.

**The [[Critical Path]]** is the chain of cards with zero total float: **A → D → E**, eight days. Planting day is the morning of Monday 9 November. Any day lost on A, D or E moves planting day; days lost on B or C do not, up to two. That is where the Cell's attention belongs ([[Float]]).

**If the date is fixed.** Suppose the frost is forecast for the 9th and the beds must be planted by the end of Sunday 8 November, day 7. Run the backward pass from 7 instead of 8: E starts 6, D starts 1, C starts 4, B starts 3, and A must start at −1. Total float on A, D and E is now **−1**. The plan is a day late before a day of work is done. That number is the honest news, found early: re-pull, add hands to D, or move the date, and write down why ([[Honesty about time]]).

## 3. What is owed

To find what is waiting on whom, take every card that is not done, every request not yet answered, and every commitment claimed but not yet witnessed:

- A card whose predecessors are all done **waits on its holder.**
- A card whose predecessors are not done **waits on the holders of those predecessors.**
- A request **waits on the one asked,** until an answer line points to it.
- A commitment claimed as kept **waits on its witness.**

Worked on the sheet as of Wednesday evening (end of day 3). By then the sheet also holds: A done and witnessed; B done and claimed as kept by the host, not yet witnessed; D started by the builder on day 2; and a request from the builder to a neighboring Cell to borrow a saw, with no answer.

| waits on | what | by when |
|---|---|---|
| host | C, Gather the neighbors' yes (ready: B is done) | start by day 5, or planting day moves |
| builder | D, Build the beds (in progress, critical) | finish by day 7 |
| gardener | witness that B was kept | at the next Turn |
| the neighboring Cell | answer the saw request | before D needs the saw |
| host and builder | E, Planting day (waits on C and D) | starts day 7 |

Nobody had to remember any of this. It is read off the sheet, and anyone holding the same sheet reads the same table. This table is what [[The Deal]] deals from.

## 4. Commitments kept

To count [[Commitments Kept]] for a stretch of time (here, the week of Monday 2 to Sunday 8 November):

1. List every commitment whose *by* date falls in the week. That count is **made**.
2. For each, find the line that says it was done, and the line that witnesses it.
3. **The gap** = the day it was done − the day it was due. Zero is on time; a minus number is early; a plus number is late.
4. A commitment counts as **kept** when it was done by its date and a witness has said so. A claim without a witness is waiting, not yet counted.
5. **Commitments kept** = kept ÷ made.

| commitment | by | done | witnessed | gap | counts as |
|---|---|---|---|---|---|
| host: A, Agree the plot | Tue 3 | Tue 3 | yes, gardener | 0 | kept |
| host: B, Write to the neighbors | Wed 4 | Wed 4 | not yet | 0 | waiting on its witness |
| builder: Buy the timber | Wed 4 | Thu 5 | yes, host | +1 | late |
| gardener: Soil test | Fri 6 | no line | | open (+2 on Sunday) | not kept |
| builder: Frame two beds | Sat 7 | Fri 6 | yes, gardener | −1 | kept |

**Made: 5. Kept: 2. Commitments kept: 2 of 5.** When the gardener witnesses B, it is 3 of 5.

Beside each gap the Cell writes what it learned, at [[The Turn]], without blame: *the timber yard closes at noon on Wednesdays; order the day before.* *The soil kit came late; ask for it two days earlier.* The learning is the reason for the count ([[The gap]], [[Zero Blame Environment]]).

## 5. Buffers at an interface milestone

A Cell does not publish its inner cards to the wider body. It publishes its milestones: here, **Beds planted, by day 8.** Its [[Supercell]] plans a harvest fair that several Cells' milestones feed into. Between this Cell's milestone and the day the fair needs the beds, the supercell holds a [[Buffer]] of 4 days, so the beds are needed by day 12. The Cell plans to day 8 with no slack of its own; the four days belong to the joint, held by the supercell, and are spent in the open.

At each Turn, two numbers are read:

- **Chain complete** = (days on the critical chain − days still to go on it) ÷ days on the chain.
- **Buffer consumed** = (projected finish − planned finish) ÷ buffer days, never below zero.

The signal is the two read together. When buffer consumed stays below chain complete, the chain is absorbing its variation. When buffer consumed runs ahead of chain complete, say so at the Turn and send the news up.

| reading | days still to go on A → D → E | chain complete | projected finish | buffer consumed | signal |
|---|---|---|---|---|---|
| end of day 5 | D 3 (a day behind), E 1 = 4 | (8 − 4) ÷ 8 = 50% | 5 + 4 = day 9 | (9 − 8) ÷ 4 = 25% | consumed behind complete: steady |
| end of day 8 | D 2 (two days lost to rain), E 1 = 3 | (8 − 3) ÷ 8 ≈ 62% | 8 + 3 = day 11 | (11 − 8) ÷ 4 = 75% | consumed ahead of complete: speak up |

At the second reading the Cell says, at its Turn, that the beds will be planted on day 11, one day inside the buffer. The supercell sees the fair's joint at risk a week before the fair rather than on the day, and can lend a hand to D, which is where a lent hand buys days.

## 6. The same numbers

Give these lines to any engine that meets the kit's rules and it returns these numbers: early starts 0, 2, 3, 2, 7; total float 0, 2, 2, 0, 0; the critical path A → D → E; the same table of what is owed; commitments kept 2 of 5; buffer consumed 25% and then 75%. If it returns anything else, one of you has made a mistake, and the sheet is where you look first.

A Cell with no computer runs the Game by doing this once a week at the Turn. A Cell with an agent has the agent do it every time a line is written, and checks it by hand now and then, because a check never uses only the instrument that made the number.

## With a notebook

Keep one sheet per season for the Cell's cards and one page per week for its commitments. Pencil the two passes in the margin beside the cards each week, circle the zero-float chain, and write the commitments-kept fraction at the bottom of the page.

---

*Read next: [[The Record — How Your Holon Remembers]] · [[Commitments Kept]] · [[The Deal]] · in the Field, [[The activity table]], [[Milestone]], [[Data Date]] and [[Notebook form]].*

*CC BY-SA 4.0 · LIØNSBERG*
