---
status: current best understanding, loosely held · improved each week
licence: Creative Commons Attribution-ShareAlike 4.0
---

# The ledger of differences

*Where this kit departs from the personal-agent kit it is built on, file by file. It exists so that the next release of that kit can be read against it, and each change taken or declined with a reason (architecture 17 §6 and 18 §4). The table is made by comparing the two kits; the reasons are written by hand, and where no reason is recorded the row says so.*

**Compared:** pkai-starter-kit v3.1.0, at its tag, with this kit as it stands in this release.

**In sum:** of the starter kit's files, 27 are carried unchanged, 129 are carried and changed, and 9 are not carried.

## Not carried

| File of the starter kit | Why |
|---|---|
| `ARCHITECTURE.md` | its shape is this kit's shape, taught in `BUILD.md`, `RELEASE.md` and *Your First House*; architecture 18 says where each layer lives |
| `BUILD.md` | this kit's own `BUILD.md`, at the top of the kit, is its counterpart |
| `MOVING-FROM-V2.md`, `MOVING-FROM-V3.0.md` | for houses built from that kit; `MOVING-IN.md`, Path C, adapts them |
| `SHAPING.md`, `WISHLIST.md` | the upstream project's own planning |
| `bookshelf/README.md`, `personas/README.md` | this kit's shelves and personas are described in its own pages |
| `template/hq/projects/README.md` | the builder writes the two lines itself |

## Carried, by part

| Part | Unchanged | Changed | Why it differs |
|---|---|---|---|
| `bookshelf/getting-started` | 1 | 17 | rewritten around the Quest and the app as the way in |
| `template/` | 4 | 7 | the agent's home is this kit's own folder; the settings add the record's hooks and narrow permissions |
| `(top of the kit)` | 0 | 10 | this kit's own pages take their place |
| `bookshelf/git-guide` | 0 | 12 | carried whole, in this kit's voice |
| `bookshelf/keeping-yourself-safe` | 0 | 7 | in this kit's voice, with the Game's venues added |
| `bookshelf/project-management` | 0 | 15 | carried whole, in this kit's voice; five pages still teach the one-folder house and say so at the head of the shelf |
| `bookshelf/working-with-other-houses` | 0 | 6 | in this kit's voice, with the Dojo added |
| `bookshelf/your-house` | 0 | 7 | in this kit's voice; the house is taught in layers |
| `personas/` | 0 | 3 | the companion is the base of this kit's charter; the archivist and the chief of staff are carried, lightly edited |
| `skills/` (22 skills) | 22 | 45 | carried under each skill's own `LINEAGE.md` and `LICENSE.md`; they live at `.claude/skills/`, where the host loads them; the wording is in this kit's voice |

## The files changed most

How far each has moved: the starter kit's lines, this kit's lines, and how many lines the two still share.

| File | Its lines there | Its lines here | Lines shared |
|---|---|---|---|
| `CHANGES.md` | 73 | 202 | 8 |
| `LICENSE.md` | 188 | 14 | 7 |
| `skills/README.md` | 57 | 97 | 15 |
| `CONTRIBUTING.md` | 85 | 13 | 5 |
| `template/agent-home/dot-claude/settings.json` | 55 | 114 | 55 |
| `README.md` | 64 | 53 | 14 |
| `template/agent-home/README.md` | 8 | 53 | 4 |
| `personas/chief-of-staff.md` | 215 | 215 | 175 |
| `bookshelf/getting-started/Troubleshooting.md` | 73 | 97 | 58 |
| `START-HERE.md` | 56 | 61 | 23 |
| `.gitignore` | 38 | 42 | 5 |
| `personas/archivist.md` | 227 | 227 | 192 |
| `LINEAGE.md` | 50 | 52 | 18 |
| `bookshelf/getting-started/Installing Claude Code.md` | 78 | 87 | 54 |
| `bookshelf/getting-started/README.md` | 47 | 50 | 18 |
| `bookshelf/getting-started/Installing Git.md` | 99 | 107 | 76 |
| `personas/companion.md` | 225 | 225 | 195 |
| `template/agent-home/venues.md` | 32 | 8 | 4 |
| `bookshelf/getting-started/Choosing Your Terminal.md` | 93 | 105 | 78 |
| `template/agent-home/dot-claude/settings.powershell.json` | 86 | 112 | 86 |
| `bookshelf/getting-started/Getting a Claude Account.md` | 36 | 36 | 14 |
| `bookshelf/project-management/Anti-Patterns.md` | 105 | 105 | 84 |
| `bookshelf/project-management/Pair Programming with AI.md` | 101 | 101 | 80 |
| `bookshelf/getting-started/System Requirements.md` | 44 | 47 | 28 |
| `bookshelf/project-management/Starting a New Project.md` | 102 | 102 | 83 |

## How to use this page

When the starter kit ships a release, read its changes against this page. A file carried unchanged takes the new version as it is. A file carried and changed is compared with care: the upstream's change is taken where it does not undo a reason written here, and declined, with the reason added to this page, where it does. A new file is weighed as a new piece. What this kit learns that would serve every personal agent is offered to that kit's keeper, as an offer.
