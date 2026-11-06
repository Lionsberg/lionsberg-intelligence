# The skills, by layer

*Which skills belong to which layer of a house. A builder copies a layer's skills only when that layer is built; `RELEASE.md` at the top of the kit names the layers.*

## The agent

The skills of the personal-agent kit this one is built on. Every house has them.

`art-director` · `assign-an-id` · `before-your-first-room` · `check-my-setup` · `choose-a-name` · `choose-a-version-scheme` · `fair-copy-a-transcript` · `find-it-again` · `foreground-background` · `heads-up` · `import-chatgpt-history` · `make-a-skill` · `phone-path` · `pull-from-benchmark` · `review-and-prune` · `save-a-memory` · `send-for-review` · `start-a-project` · `test-a-charter-edit` · `venue-card` · `widen-a-boundary` · `wrap-up-this-session`

## Player+

The skills that play the Game with a notebook, and keep a house current. They work without the engine, at the paper floor, and use it where the house holds it.

`entering-the-field` · `pass-the-flame` · `play-by-play` · `pull-a-release` · `read-the-story-aloud` · `refresh-the-library` · `safe-sparring` · `the-chief-of-staff` · `the-offering` · `the-record` · `the-retrospective` · `the-roll` · `the-season-sheet-by-hand` · `the-simplest-game` · `witness-a-commitment`

## The Game Engine

The skills that read or write the record through the engine, or open the board. They are copied only into a house that has `HQ/engine`.

`a-gathering` · `a-mail-watch` · `agree` · `connections` · `join-a-cell` · `negotiate` · `pull` · `receive` · `say-it-on-the-card` · `sight` · `subscribe` · `the-deal` · `the-heartbeat` · `the-proxy` · `the-turn` · `voice-mode`

## The room a description has

The host hands the model each skill's name and description, within a limit: about 24,000 characters for a house's own skills, measured with Claude Code 2.1.317. Past the limit, the skills last in the alphabet are listed by name alone, and the model no longer knows when to reach for them. The skills of this kit take about 22,300.

So a description says what the skill does in one clause, and when to use it in a few of the person's own phrases, in under 300 characters. The rest belongs in the skill's page. A house that adds many skills of its own keeps theirs as short, and a test of the kit (`engine/tests/test_the_house.py`) holds the total.
