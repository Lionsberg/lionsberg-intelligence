# This release

*What this kit is made of. Player+ is the latest personal-agent kit, as its keeper ships it, with layers added. Each layer is one capability, with its own version and its own source. A release is the list of them.*

| Layer | What it adds | Version | Comes from | Lives in a house at | How it stays current |
|---|---|---|---|---|---|
| **The agent** | a personal agent that works: a charter, memory, sessions, the desk and the clock, skills that travel alone | pkai-starter-kit 3.1.0 | the PKAI starter kit and benchmark | `My Agents/<name>/` | each release of its upstream is read against the ledger of differences, and offered by proposal |
| **Player+** | the Game in the agent's charter, the chief of staff's office, and the skills that play the Game | 4.0.0, in the making | this kit | added to the agent | by a proposal the person agrees to |
| **The Library** | the books, the LIØNSBERG information, and this kit whole, for reading and reference | follows the `release` branch | the canon and the library | `HQ/Library/` | the agent refreshes it each day or each week |
| **The Game Engine** | the record's engine: what is in play, what is owed, commitments kept, The Deal | game-engine 1.1.1 | this kit | `HQ/engine/` | by a proposal the person agrees to |
| **The board** | the page where The Deal and the conversation sit side by side | ships with the engine | this kit | `HQ/hud/` | by a proposal the person agrees to |

## Three rules the layers keep

1. **Each layer stands without the ones above it.** An agent with no Library, no engine and no board is a whole personal agent. No layer may weaken the one below it.
2. **What is read may refresh on its own; what runs, or tells an agent how to act, changes only when its person says yes.** The Library is reading and reference, so it follows each release. The charter, the hooks, the skills, the engine and the board change by proposal (`player-plus/.claude/skills/pull-a-release`).
3. **Every layer follows its own source, and none is bound by it.** Where a layer departs from the source it grew from, the departure is written down with its reason (`player-plus/LEDGER.md`), so that the next release of that source can be read against it and taken or declined, piece by piece.

## For an agent reading this

```yaml
release: player-plus on pkai-starter-kit 3.1.0
layers:
  agent:    pkai-starter-kit 3.1.0        # upstream: github.com/peterkaminski-ai/pkai-starter-kit
  player:   player-plus 4.0.0 (in the making)
  library:  the release branch of this repository, read whole
  engine:   game-engine 1.1.1
  board:    ships with the engine
places:
  agent:    ~/My Agents/<name>/
  library:  ~/HQ/Library/lionsberg-intelligence/
  engine:   ~/HQ/engine/
  board:    ~/HQ/hud/
skills_by_layer: player-plus/.claude/skills/LAYERS.md
```

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
