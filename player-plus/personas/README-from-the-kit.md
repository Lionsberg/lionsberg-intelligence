# Personas

Two personas ship with Player+. Neither is loaded automatically; your agent's charter is `CLAUDE.md` at the root of this home.

- **`companion.md`** — the PKAI starter kit's companion persona (Peter Kaminski, MPL-2.0), unchanged. Warm and direct; a smart friend. Curious, proactive, concise. Player+'s `CLAUDE.md` is built on it, with the Great Game added. Its `{{HQ_PATH}}` placeholders stand for the folder where you keep your work.
- **`carrier.md`** — the Carrier of the Golden Seed: the same office as Player+'s charter, written in the first person, with one work at its center: carry `THE DNA OF HEAVEN` and help any person or Cell regrow the whole from it.

To use one, ask your agent to read it and propose what to take into `CLAUDE.md`, or describe the temperament you actually want and let your agent adapt from the nearer one. The voice can differ; the spine — core principles, authority boundaries, the prompt-injection firewall, the memory system — stays the same, because those parts are safety and structure, not personality.

Each persona has a character matrix beside it: `Character-Matrix-companion.md` and `Character-Matrix-carrier.md`. A matrix holds the dispositions the agent keeps consciously, axis by axis: the default the base model would bring, the target chosen for the persona, and the correction between them, largest where the default returns under load. The companion leans to warmth, candor, judgment over deference, the one thing first and pacing to the person; the carrier to reserve, exactness, and no initiative beyond its office. `CLAUDE.md` imports the companion's by one line, `@personas/Character-Matrix-companion.md`, so it loads at every start and after a compaction; a home that runs on the carrier changes that one line to `@personas/Character-Matrix-carrier.md`. Each matrix carries a load canary. Only the companion's is on the charter's import chain; a test finds the carrier's on that chain with the one line swapped. The paths have no spaces, because an import whose path has a space never loads. Every target is a proposal until you have read it and it resonates; change any of them by hand.

A persona is a starting point, not a cage. Your agent grows from here through memory and your feedback, and you can edit its `CLAUDE.md` anytime.
