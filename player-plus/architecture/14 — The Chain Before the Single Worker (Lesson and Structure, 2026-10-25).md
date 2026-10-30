# 14 — The Chain Before the Single Worker

*How the chief of staff and the agent host keep a chain of workers moving. The practice below binds both. Part of the architecture set; see the [Index](<Index — The Architecture (2026-10-24).md>).*

## The lesson

A single long-running worker is slower and riskier than a chain of short stages ([`skills/the-chief-of-staff/SKILL.md`](../skills/the-chief-of-staff/SKILL.md) rule 25). When one worker's result is needed by another and the second simply waits, everything behind it stops, and nothing in the work itself says so. A person looking in from outside is then the only one who sees it. Seeing it first is the chief of staff's office, and the structure on this page makes sure it does.

## Why a chain stalls

- **A report stands where a contract should.** The waiting worker rarely needs the other's work; it needs the shape of the other's output, and a shape can be written in minutes. "B uses A's result" is not the same as "B waits for A".
- **No clock watches the chain.** A launch that says its cost but not its expected minutes has no overrun, and with no overrun nothing fires.
- **The chain is felt, not computed.** Every piece of work is a card with its dependencies and its float. A chain run without cards is caught only by whoever happens to be looking.
- **The assigner is the only auditor.** When the one who launched the workers is the only one asking whether they are well arranged, no one asks, because an assigner is the last to doubt an assignment.

## The structure

Four parts, each built into something that runs rather than something to remember.

1. **A contract before a dependency.** When one worker will use another's result, the chief of staff writes the shape of that result first, in one line, and starts both. A worker waits on another worker's report only when no shape could be written, which is rare. The agent host refuses a proposal that names a dependency ("after Worker A", "using Worker A's draft") until the shape is given.
2. **Every worker says its minutes beside its cost.** The proposal form carries "about {n} minutes". The host keeps the estimate on the worker's row and watches it: when a worker passes half again its estimate while anything idle waits on it, the host raises one notice to the chief of staff and gives it a turn with three choices: let it run with a new estimate, split the task, or start a second worker beside it. The chief of staff says in one line what it did and why. One notice per box, never twice in ten minutes.
3. **The deck is the instrument for a build.** Each worker is a card with its dependencies named, so the chain is computed from the cards. The Agents place shows each worker's task, elapsed time against its estimate, and whether it is over.
4. **A separate eye on the arrangement.** Every thirty minutes while workers run, the host hands the chief of staff the list and one question: what is idle, waiting on what, and why. The chief of staff moves what can move and says what it moved. The assigner still assigns; the question comes from the structure.

Where it lives: [`skills/the-chief-of-staff/SKILL.md`](../skills/the-chief-of-staff/SKILL.md) rule 24 (the office's words), [`hud/agent_host.py`](../hud/agent_host.py) (the estimate, the watch, the refused dependency, the half-hour chain question), the worker's proposal form, and the Agents place's rows.

The office stands on its own. The chief of staff's skill, with rule 24 and the proposal forms (the task in the person's words, the minutes, the shape of a result where there is a dependency), stands on its own in any house that runs workers, with or without the Agents place. The host's watch is a small, separate piece: the estimate on a worker, the overrun notice with its three choices, the refused dependency, the half-hour chain question. It needs only the agent host. The page on foreground and background sessions does not yet carry the same two lines; they are to be added: a session says its minutes, and it never waits on another session's report when a shape would do.

## Current best understanding

- A person's attention is the scarcest thing in the house. Any watch that the structure can keep, the structure keeps; a person is told only when a decision is theirs.
- A dependency is a claim about the shape of a result, never about its arrival. Shapes are cheap to write and free the chain; arrivals are slow and bind it.
- An estimate is not a commitment. It is the number that makes an overrun visible. A wrong estimate corrected in one line is worth more than no estimate.
- The one who assigns cannot be the only one who audits. The question "what is idle, waiting on what" must come from outside the assigner's head, on a clock.

## Current best practice

- Before launching two workers, write the shape between them. Before launching one, say its minutes and its cost.
- Treat half again the estimate as the moment to act, not to wait.
- Keep the Agents place open while a long task runs; it is the chain made visible.
- When a person catches a wait the structure missed, the structure changes the same day.

## Not yet proven

Only the watch has been proven, with a stand-in worker and in tests, not yet with a real worker past its box. The half-hour question has not yet run through a whole long task.
