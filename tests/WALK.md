# The walk: what only a person can prove

*The suites prove what a script can. This page is the other half: one person, with no training, walks `player-plus-kit/START-HERE.md` on a clean computer, and someone beside them writes down what happened. One walk on a Mac and one on Windows. A release is a candidate until both are walked.*

## Before the walk

- A computer account that has never held an agent: no `<Name> (agent)` folder, no `My Agents`, no `HQ`. A fresh user account or a virtual machine is fine.
- A paid Claude account the walker can sign in to, and their email at hand.
- The download the kickoff sentence names is live at its address, and its `player-plus-kit/VERSION.md` is the candidate being walked.
- The one who sits beside them watches and writes, and answers only when asked. The walker reads the page; the page does the teaching.

## Write down, at each Gate

| Gate | Started | Passed | Minutes | Where they stopped, and their own words | What the screen showed that the page did not say |
|---|---|---|---|---|---|
| 1 · An account | | | | | |
| 2 · The Claude app | | | | | |
| 3 · Your house | | | | | |
| 4 · First words | | | | | |
| 5 · Your phone | | | | | |

Read the clock for each time. Count the permission prompts at Gate 3.

## Look at, when the house is built

1. Two folders side by side: `<AgentName> (agent)` at the top of the home folder, and the HQ where the walker made it.
2. In the agent's `CLAUDE.md`: one line that begins `<!-- Player+ begins`, one line `<!-- Player+ ends -->`, above `## Things you always do`.
3. In the HQ: `library/pkai/`, `library/lionsberg/` with `reviewed/` and `playing/`, and `cards/`.
4. Then, from the top of this repository, with the walker's own answers:

   `python3 -I tools/compare_houses.py --kit . --home <their home folder> --hq-name <their HQ's name> --person <name> --handle <handle> --agent <agent> --persona <persona>`

   It says MATCH, or it names each file that is missing, extra or different.

## Look at, on the phone

1. On the computer, under Settings, Code, Remote Control: the Folders list holds the agent's own folder, pinned, and nothing the walker does not need.
2. On the phone, New session, then the computer: the agent's folder is offered, and a session started there wakes the agent, which answers by name. Note whether the walker was drawn to a cloud environment first.
3. Note whether the walker read what the Remote Control page says it sends before turning it on, and what they decided.

## The first hour, by voice

The walker says, in their own words, the six sentences: *here is a piece of work · I will do it by Friday · it is done · we are green*, and, if they have a Cell, *I join this Cell* and *yes, that works for me*. For each: did the agent read it back in one line before writing? Is there a Card file in `cards/`, named by its date, their handle and its kind? Does it open in their reading app and say what they said?

Then they ask the agent to read The Story aloud from the reviewed shelf, and ask one question about the Game. Did the agent say which shelf its answer came from?

## On Windows, also

- Whether git had to be installed, how long it took, and whether the app had to be restarted before the agent's first hello.
- Whether the unzip worked where the walker made the HQ.
- Whether the agent's clock showed the right local time in its first reply.

## The walk is passed when

The walker reached their agent's greeting without the one beside them touching the keyboard; the comparison says MATCH; the six sentences made the right Cards; and the walker can say, in a sentence of their own, what they now have.

Everything written down goes to the keepers as proposals: what we saw, what would have helped, the exact words the page should have said.

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
