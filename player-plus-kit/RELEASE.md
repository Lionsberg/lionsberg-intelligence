# This release

*What Player+ 4.1 is made of. It is the PKAI starter kit, as its keeper ships it, with one layer added. Each part has its own source and stays current in its own way.*

| Part | What it adds | Version | Comes from | Lives in a house at | How it stays current |
|---|---|---|---|---|---|
| **The agent** | a personal agent that works: a persona, memory, sessions, the desk and the clock, skills that travel alone, a bookshelf | pkai-starter-kit 4.0.0-rc.5 | the PKAI starter kit, carried whole and unchanged in `pkai-starter-kit/` | `~/<AgentName> (agent)/` and the HQ | `pull-from-benchmark`: each release is read, and taken by proposal |
| **The Player+ block** | The Great Game of LIØNSBERG in the agent's charter: the Goal, the words, the Cards, and where to find the rest | 4.1.0-rc.1 | `PLAYER-PLUS-BLOCK.md` | the agent's `CLAUDE.md`, between two markers | `pull-a-release`: a change is drafted, and the person installs it |
| **The longer guide** | how to play: the Cards in full, the six sentences, the Turn, joining a Cell, the belts, Pass the Flame | 4.1.0-rc.1 | `PLAYER-PLUS.md` | beside the charter | `pull-a-release`, on the person's yes |
| **The Player+ skills** | sixteen procedures for the Game that need no engine | each its own, in its `LINEAGE.md` | `skills/` | `<agent home>/.claude/skills/` | `pull-a-release`, on the person's yes |
| **The LIØNSBERG bookshelf** | `reviewed/`, the words reviewed line by line; `playing/`, the practical books, each marked as not yet reviewed that way | follows each release | `library/lionsberg/` | `<HQ>/library/lionsberg/`, beside `<HQ>/library/pkai/` | `refresh-the-library`: reading refreshes, and what changed is said |
| **The Cards** | a place for play written as plain files, and one example of each kind | 4.1.0-rc.1 | `template/hq/cards/`, `card-examples/` | `<HQ>/cards/`; a Cell's in its own repository under `<HQ>/cells/` | they are the person's own |

## The sixteen skills

`a-gathering` · `entering-the-field` · `join-a-cell` · `pass-the-flame` · `play-by-play` · `pull-a-release` · `read-the-story-aloud` · `refresh-the-library` · `safe-sparring` · `the-offering` · `the-retrospective` · `the-roll` · `the-season-sheet-by-hand` · `the-simplest-game` · `the-turn` · `witness-a-commitment`

The host hands the model each skill's name and description within a limit of about 24,000 characters for a whole house. A house is built with fourteen of the starter kit's twenty-two skills and these sixteen. All thirty-eight together take about 18,200, so a house that takes every one still fits, and a test of this kit holds the total. A house that adds skills of its own keeps their descriptions as short.

## Three rules the parts keep

1. **The starter kit is carried, not changed.** No line of `pkai-starter-kit/` differs from what its keeper ships, and a test holds that. A build moves that kit's library into the house, as its own page says, and changes nothing else in it. In a house, the only lines Player+ adds to the charter sit between its two markers.
2. **What is read may refresh by itself; what tells an agent how to act changes only when its person says yes.** The bookshelf is reading. The block, the guide and the skills change by proposal.
3. **Each part follows its own source.** The agent follows the PKAI benchmark; the Player+ layer follows this kit. Where a house does a thing its own way and better, that is a finding to send back, not a fault.

## Not in this release

The game engine, the board, the daily Deal and the scripts for rooms and pads are being proven before they are offered. A 4.1 house holds none of them. The Cards are written in the form the engine reads, so a house that plays now loses nothing when the engine arrives.

## For an agent reading this

```yaml
release: player-plus-kit 4.1.0-rc.1 on pkai-starter-kit 4.0.0-rc.5
parts:
  agent:      pkai-starter-kit 4.0.0-rc.5     # carried unchanged; upstream github.com/peterkaminski-ai/pkai-starter-kit
  block:      PLAYER-PLUS-BLOCK.md 4.1.0-rc.1
  guide:      PLAYER-PLUS.md 4.1.0-rc.1
  skills:     16, in skills/
  bookshelf:  library/lionsberg/ (reviewed/, playing/)
  cards:      template/hq/cards/, card-examples/
places:
  agent_home: ~/<AgentName> (agent)/
  hq:         ~/Documents/<yourname>-hq/      # the top of the home folder when Documents is synced
  bookshelf:  <HQ>/library/lionsberg/
  cards:      <HQ>/cards/
  cells:      <HQ>/cells/<cell-name>/
not_in_this_release: [game engine, board, Deal, room and pad scripts]
```

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
