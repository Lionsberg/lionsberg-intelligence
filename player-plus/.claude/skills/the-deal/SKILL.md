---
name: the-deal
description: The daily office — pull every holon, compute The Deal (a few Work Cards sized to the minutes they have), say it, deliver it by the door they chose, and take their answers back. Use each morning, around a meeting, and for "deal me in", "what needs me", "what is waiting on me".
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
8. **Take their answers as events.** Each answer becomes a line in the record, written as `the-record` says. Where the answer is their own act (a `commit`, a `decide`, a `ratify`, a `release`), prepare the line and show it. It reaches the record by their own hand, or at their word: you write it as your own line, signed with your own key, `for` them, `reason: human`, with their words in `body.consent` and their own signed `say` carrying the same words named in `links.answers`; or under a once-delegation they wrote for that one act, preferably naming its exact body with `body_digest` (`the-record`, rule 8). A bare consent, with no signed line of theirs, never counts. Where it is a fact they told you, write it as yours, `for` them. In the session, their word on a dealt card becomes the line the HUD makes for the same choice, written by this path (*The Hand in the session*, below).
9. **Never tick their box.** You do not answer a card for them, mark one done because it looks done, or carry yesterday's yes onto today's card. An unanswered card stays unanswered and comes back, honestly, next time.
10. **The answer to the standing question** is the most valuable line of the day. Write it down in their words, and bring it into the next Deal or the next Turn.
11. **Read each card's `offers` and `level`.** Every dealt card carries `offers`, the acts its reader's role may take, computed from the registry (`engine/acts.py`): each with its label and its one-line meaning from `engine/acts.json`, the primary act being the one the recommended option writes, and `offers.options`, what each option writes as a line. A choice is said by its act's label, with its meaning wherever the label alone could be misread, and `offers` holds the reader's own role's acts: the committor's to the committor, the committee's to the committee (`say-it-on-the-card`). A card dealt with `stopped` offers you nothing while that stop binds you, and one line says so. Every card also carries `level` (`{name, lifts, why}`), computed from what the card carries (`engine/level.py`). It is not a gate: a card plays at any level, and its acts stay the same at every level. `lifts` names the fields of the next rung, in words; one of them is worth offering when it would change their next play, as an offer and not a demand (`the-simplest-game`).

## The Hand in the session

In the session the Deal is dealt as words, and the person answers it with a word. What their word makes is the line the HUD makes when they tap the same choice: the same type, body and links. Who writes it follows the record's own rule 8 (`the-record`): a line of yours is yours, written as you, `for` them, at their word; their own acts reach the record by their own hand. The board itself opens beside the conversation when they ask to see it (`the-chief-of-staff`, rule 35). *Show me the board*, or the same ask in their words, opens it as a pane through your host's preview (the home's `.claude/launch.json`, `the-board`, serves `hud/serve.py` on its port); every act there is the same line as the word here, so there is nothing the session cannot do without it.

1. **What the engine dealt.** `python3 -I engine/engine.py deal <home> --actor person:<them> --minutes <n> --json`. Each card carries `offers`: the acts their role may take, each with its `label`, its `meaning` and the line it `writes`, the one marked `primary` first; and `offers.options`, what each of the card's options writes. Each card also carries `level`, which leaves what is offered unchanged. Together these say what every choice does.
2. **A card in one sentence.** Its question; then the primary act by its label, with its meaning; then the other acts of `offers` by their labels. *The cell asks you to bring the soup by Saturday. I would say yes: you become its holder, and they count on you. Or offer something else, or decline with thanks.* A card that offers them no act (its `offers.acts` empty, or `stopped`) is said by its title or question, with the reason in `offers.said` or `why_not`: *The budget decision is the keeper's to back, so there is nothing for you to do on it.*
3. **Their word picks one act.** A plain yes takes the primary act; the act's label, an option's words, or a clear answer in their own words picks that act. A word that could mean two acts is a question back, naming the two labels. An act outside `offers.acts` is not theirs here, and its `why_not` says why.
4. **The line, from the engine.** The fold first, and again after every line written or pulled: `python3 -I engine/record.py fold <home> > <scratch>/items.json`. Then, for the act they chose:

   ```
   python3 -I engine/acts.py line <scratch>/items.json <card id> person:<them> <act key> --agent agent:<you> --consent "<their yes>" [--text "<their words>"] [--why "<their words>"] [--option "<the option's words>"]
   ```

   It prints JSON, in one of four shapes.
   - **A line**: the act is one you may write at their word. `line` is your own line (`actor` you, `for` them), with their yes in `body.consent`; `label` and `meaning` say what it does; `append` is the rest of the command that writes it, starting with the holon's folder; `signed_for` holds their yes and `consent_for`, the digest their own signed `say` names when they want the line marked as signed at their word.
   - **Theirs**: the act is their own (an `answer`, yes or no to an ask, a `commit`, a `ratify`, a `decide`, a `kept`, a `witness`, a `settle`, every `human_only` type). `theirs` says so, and `draft` is the line for their own hand: their tap in the HUD, or their own `record.py append`. Say that in one line, with the draft.
   - **Needs**: `needs` names what is missing and `ask` says it plainly: their own words (a reply, a question, a change asked for, in `--text`; the reason for handing a commitment back, in `--why`), or their yes (`--consent`). Their words are theirs to give; ask in one line, then run it again with them.
   - **Refused**: `refused` says why the act is not theirs here. Nothing is written.

   `--option` carries the words of the option they chose. Where those words are the line itself (*On track*, *Thank them: it stands*), they become its text; where the option opens a reply (*Offer something else*), their own words are asked for. A settle keeps the conversation's own title, or the option's words when it has none.
5. **The read-back is the undo.** Before anything is written, read the line back in your own words, by the act's label, on the card's title, with their words as they gave them: *I will write, on bring the soup, in your words: Saturday works for me. Yes?* Their yes is `--consent`; anything else leaves the record as it was. On their yes, write it: `python3 -I engine/record.py append <append>`, each item of `append` one argument, as printed, signed with your own key. A line once written stays, and a change afterward is a correction (`the-record`). When the HUD is running, its own held act gives them a timed undo on their tap (five seconds, or up to fifteen as they set it there).
6. **Then the next card**, as `the-chief-of-staff` says (rule 5). An answered card has had its turn in the sitting.

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
