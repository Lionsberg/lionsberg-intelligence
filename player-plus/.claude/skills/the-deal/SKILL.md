---
name: the-deal
description: The daily office, from the first day — pull every holon the person is part of, compute The Deal (a few Work Cards sized to the minutes they have, asked or read from their calendar), say it in the briefing voice ("Here's the deal."), deliver it by the door they chose (a page in their viewer, their phone by the phone path, a printed card), from the agent on their own computer, take their answers back as events, and never tick their box. One card is always the standing question. The first Deal comes within about five minutes of the agent's first word, and the setup (the key's lock, the agent's affirm, the delegation, conformance) waits for the cell moment. Use each morning or at the hour the person set, at the start and the end of a meeting, when the person says "deal me in", "what is the deal", "what needs me", "what do I do", "what is waiting on me", or when they say how much time they have.
license: MPL-2.0
---

# The Deal

A person should never have to open a project tool to find out what needs them. You do that for them. **The Deal** is a few Work Cards, dealt from everything their holons hold, sized to the time they actually have, each one a question they can answer in a line. It is the daily office: the thing you do every day, whether or not anything else happens.

The test it must pass: your person can answer the whole Deal in the minutes it asked for, and nothing that needed them today is missing from it.

## Steps

1. **Pull every holon.** Their home and every cell they joined: `python3 -I engine/holon.py pull <home>`. If a pull fails, carry on with the rest and say which holon is stale (`the-record`, rules 17 and 18).
2. **Know the minutes.** Ask, in one line, "How much time do you have today?", unless they already said, or unless the holon's `calendar.json` names their minutes for today and they have told you to read it from there. Never assume more than they gave. Five minutes is a real Deal.
3. **Compute it.** Run the engine's deal command: `python3 -I engine/engine.py deal <home> --actor person:<them> --minutes <n>`, adding `--room` with the actors present if this is a meeting (`--paper` prints the card form). The engine folds every holon, finds what waits on them, weighs float and what the whole is waiting on, and returns the cards that fit. You may reorder for sense; you may not add a card the engine did not deal without saying why, or drop one silently. When they say "fewer", pass the dial (`--fewer`, or `--fewer "much fewer"`); when they sat down to it, `--sitting`. Their own `attention` lines (their budget: minutes, asks per hour and per day, the gap between asks, quiet hours, what always passes) decide what may interrupt them outside a sitting; the state's `attention` says what may interrupt now, what waits for the margin, and what was withheld with when it returns. The budget governs interruptions only, never what they may read: every view, and every open thread to them or to you, stays open to them at any time.
4. **Shape each card as a question legible alone.** What it is, in one line. Why it is theirs now (it waits on them; its float is gone; the whole is waiting on it; someone asked). The options, and your recommendation with its reason in a sentence. How to answer: one word, one key, or one line. A card that needs them to open three files first is not finished.
5. **Add the standing question.** One card is always the same: *What did we miss that matters to you most?* It is never dropped to make room.
6. **Say it in the briefing voice.** Short, warm, plain. Lead with the count and what kind they are:

   > Here's the deal. Three today, about twelve minutes.
   > 1. **The workshop date** waits on you. Thursday or Saturday? I would say Saturday: two of the cell cannot do weekdays. *(Thu / Sat)*
   > 2. **Your commitment to send the draft** is due tomorrow. Still on? *(yes / move it / release it)*
   > 3. **What did we miss that matters to you most?**

   No preamble, no recital of the record, no card they cannot act on.
7. **Deliver it by their door.** You run on your person's own computer, and so does their record; the door only decides where they read The Deal. It is theirs to choose and is written in memory: a page opened in their viewer on that computer (`open`, as *Open things for your person* says), their phone reaching you on that computer by the kit's `phone-path` skill, or a printed card. On paper, one card per line, a box to tick, room to write. A new door is set only by their word.
8. **Take their answers as events.** Each answer becomes a line in the record, written as `the-record` says. Where the answer is their own act (a `commit`, a `decide`, a `ratify`, a `release`), prepare the line and show it. It reaches the record by their own hand, or at their word: you write it as your own line, signed with your own key, `for` them, `reason: human`, with their words in `body.consent` and their own signed `say` carrying the same words named in `links.answers`; or under a once-delegation they wrote for that one act, preferably naming its exact body with `body_digest` (`the-record`, rule 8). A bare consent, with no signed line of theirs, never counts. Where it is a fact they told you, write it as yours, `for` them.
9. **Never tick their box.** You do not answer a card for them, mark one done because it looks done, or carry yesterday's yes onto today's card. An unanswered card stays unanswered and comes back, honestly, next time.
10. **The answer to the standing question** is the most valuable line of the day. Write it down in their words, and bring it into the next Deal or the next Turn.

## When

- **Daily,** at the hour they set, or when they ask. One Deal a day unless they ask for more.
- **At the start and the end of a meeting,** sized to the room (`a-gathering`).
- **Between,** at their pace. If they go quiet, the Deal waits; it does not chase.

## The first Deal, and the first week

- **The first Deal comes early,** within about five minutes of your first word, right after the greeting and the waiver's one word (`the-record/day-one.md`). It is dealt from what you can see: in a new home the engine deals the standing question, and you add two cards and say why: *What are you playing toward this week?* and *Whom would you pass the flame to, when you are ready?* Their answers are their own `say` lines, their exact words. It is never put off until the house is set up.
- **The setup waits for its moment.** Showing the record, the phone's door and the whole are cards on days two and three; the key's lock, your affirm, the delegation and your conformance check come due at the cell moment, when they first join a cell or sign something that counts beyond home. Each is a question legible alone, with its time written on it, and *Later* always allowed. The table is in `day-one.md`.
- **The waiver is the first word asked of all.** Nothing is recorded before their yes to it, said in one line; the whole waiver and the Field of Agreements are offered, never required.

## What this skill never does

- Deal from one holon when the person is part of several.
- Deal more than the minutes they gave.
- Tick, answer or sign a card in their name.
- Hide a card that is uncomfortable: a broken commitment is dealt as plainly as a new one, as work to do, never a fault.
- Send The Deal by a door they did not choose, or to anyone but them.
- Drop the standing question.

## How it degrades to paper

```
THE DEAL — <date>   minutes: ___
[ ] 1. <card as a question>     options: ___   I would say: ___
[ ] 2.
[ ] 3.
[ ] What did we miss that matters to you most?  ______________________
```

With no agent, a person can deal their own: list what waits on them in every group they play in, keep what fits today's time, and ask themselves the last question.
