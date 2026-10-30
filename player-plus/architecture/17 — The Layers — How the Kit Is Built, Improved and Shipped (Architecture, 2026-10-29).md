---
title: "17 — The Layers: how the kit is built, improved and shipped"
description: The layers the Player+ Kit is built in, what each carries, and how a kit release ships the best of every layer at once.
---

# 17 — The Layers: how the kit is built, improved and shipped

*What a [[Player+]] receives is built in layers, each an upgrade on the one below. This page says what the layers are, how each improves on its own, and how a kit release brings the best of every layer to every Player+ at once. Document 00 says how the parts run; this page says how they are made and shipped. A "release" here is always a kit release, a set of versions shipped together, never the [[Release]] of a commitment.*

## 1. The first principle: we run what we ship

A house that keeps a layer runs the layer it ships. It plays the Game on the kit's own release, never on a private product beside it. No improvement to a part the kit ships lives only in the house that keeps it: the improvement is made in a layer of the kit, proven in play, and shipped from there. Every house still keeps its own record and improves its own agent (00, the first invariant; 04 §10); the principle governs the parts the kit ships, never a house's own ways.

**The checks that make it true.** *Not yet settled.* A principle that cannot fail is only a sentence, so each is meant to be a check at the gate (§7):

- **We run what we ship.** A house that keeps a layer runs from a pinned kit release. Every local difference stands in that house's own ledger of differences, with its why. If the house runs code that belongs to no layer of the kit, the gate fails.
- **Each layer is the best of its kind.** The manifest (§5) records, beside each layer's pinned version, the newest version of its upstream and the reason for any lag. At each gate, every layer's accepted changes and every upstream release since the last kit release are read; a kit release is due when any layer has one.

## 2. Two stacks, kept apart

There are two ways to layer the same kit.

- **The release stack** is how the kit is made: each layer an upgrade on the one below it, with its own source and its own [[Keeper]]. It answers: *where did this come from, and who improves it?*
- **The runtime stack** is how the kit runs: the six layers of document 00 (the Membrane, the Record, the Proxy, the Engine, the Agent, the ICE), in the order of trust. It answers: *what depends on what while it runs?*

A part belongs to one layer of each. The Game Engine is a release layer and a runtime layer of its own. One folder can hold parts of several runtime layers: `engine/` holds the Engine and also the Record (`record.py`, `holon.py`) and the Proxy (`proxy.py`, with its tests), so it ships parts of three runtime layers as one release layer. [`engine/ENGINE.md`](../engine/ENGINE.md) draws the boundary file by file.

## 3. The release stack

The shape of the stack is settled. Its names are not yet settled (§9).

| Layer | What it adds | Keeper | Upstream | Where it lives in the kit |
|---|---|---|---|---|
| **1. The PKAI base** | a personal agent that works: the desk (one foreground per house, guests who hand back), the hooks, the clock in every turn, skills that travel alone, the bookshelf's shape, the lineage block, pull never push | Peter Kaminski (pkai-starter-kit) | the pkai-starter-kit and pkai-benchmark | `scripts/desk`, `scripts/now*`; 22 of the kit's 42 skills, by their own lineage files (among them `heads-up`, `venue-card`, `foreground-background`, `save-a-memory`, `pull-from-benchmark`); the shapes of `LINEAGE.md` and `bookshelf/` |
| **2. Player+** | the Player+ Agent: its charter, the chief of staff's office, the Talk, the twenty Player+ Modules, the shelves that help a person and their agent begin | the kit's keeper | this kit | `CLAUDE.md`, `START-HERE.md`, `bookshelf/player-plus-modules`, `getting-started`, `with-your-agent`, `your-house`, `keeping-yourself-safe`, `working-with-other-houses`, `the-record`; most of the other 20 skills |
| **3. The LIØNSBERG layer** | what the agent knows of the LIØNSBERG System, the Story and the Game, and the skills that play the Game's own moves | the kit's keeper, from the canon | the canon and the library, by [[The edition\|edition]] | `bookshelf/the-great-game`, `the-field`, `the-library`, `the-one-book`, `the-dna-of-heaven`, `the-rosetta-stone`, `the-superorganism-package`; skills such as `entering-the-field`, `pass-the-flame`, `read-the-story-aloud` |
| **4. The Game Engine** | pure functions over the record: the fold, the schedule, what is owed, commitments kept, The Deal, the Turn, the ledger | the kit's keeper | this kit | `engine/`, at game-engine 1.0.0 in 3.8.0; its contract with the HUD is `engine/STATE.md`, and it reads the Record's contract, `engine/SCHEMA.md`, like every part |
| **5. What comes next** | the ICE (the HUD, the dock, the Room), and parts not yet named; each becomes a release layer of its own when it has a contract and tests | the kit's keeper unless another is named | this kit | `hud/` |

Each layer is an upgrade, never a fork: a layer adds to the one below it and does not rewrite it. Where a higher layer must depart from a lower one, the departure is named (§6).

**The stack is kept by hand in 3.8.0.** A skill's `LINEAGE.md` says where it grew from (the pkai-starter-kit, or a Player+ release), which is ancestry rather than layering: the LIØNSBERG skills say "player-plus" like the rest, and the shelves carry no layer at all. *Not yet settled:* a `layer:` field in every lineage block, so the stack can be read from the files.

## 4. What every layer carries

Every layer, on its own:

- **a version**, which changes when the layer changes and only then;
- **a [[Lineage]]**: what it grows from, its keeper, and where to pull its next version;
- **a record of changes**, newest first, each with its why (for the Engine, [`engine/CHANGES-ENGINE.md`](../engine/CHANGES-ENGINE.md));
- **a contract**: what the layers above may rely on (for the Engine, `STATE.md`, over the Record's `SCHEMA.md`; for the Agent, its charter and skills; for the LIØNSBERG layer, the edition it carries);
- **tests**, or for writing, a review: nothing ships in a layer that its own check has not passed;
- **a keeper**, who accepts or refuses each proposed change to it. Where 04 §10 speaks of the kit's stewards, the keeper of a layer is the steward of that layer.

*Not yet settled:* two rules that keep the layers clean. A layer depends only on the contracts of the layers it needs, never on their insides. And no layer edits another layer's files: a change needed below is offered to that layer's keeper, and the higher layer waits or names its departure.

## 5. A kit release is a manifest

A Player+ kit release is the set of layer versions shipped together, written in one place. An example, with its dates left as placeholders:

```yaml
# EXAMPLE — the shape of a manifest; dates are placeholders
release: player-plus kit 3.8.0
date: YYYY-MM-DD                                               # example
layers:
  pkai-base:  pkai-starter-kit 3.1.0 · pkai-benchmark 3.1.0   # upstream newest: 3.1.0
  player-plus: 3.8.0
  lionsberg:  edition YYYY-MM-DD                               # canon newest: YYYY-MM-DD
  engine:     game-engine 1.0.0 · reads record schema v1 · state contract 3.6.0
  ice:        3.7.0
gate: passed YYYY-MM-DD (see §7)                               # example
```

The release's number and each layer's number are kept apart: a layer that did not change keeps its number from the last kit release (above, the ICE). The Engine carries its own number, game-engine 1.0.0, its first, beside the record schema v1 it reads and the state contract it serves. The fields of the manifest are not yet settled.

*Not yet settled:* `RELEASE.md`, at the top of `player-plus/`, holds the manifest. `VERSION.md` and the version line of `LINEAGE.md` are written from it, so they cannot disagree. `CHANGES.md` stays written by hand, because each change carries its why.

*Not yet settled:* `skills/pull-a-release` reads the manifest, so that a house decides layer by layer what to take and may hold one layer at a known version while it takes another. In 3.8.0 the skill reads a release item by item from `pull_from`.

## 6. Upstream: pull, never push, with a ledger of differences

Every layer with an upstream keeps a **ledger of differences**: each place this kit departs from the upstream, with its why. When the upstream ships, the keeper reads the new release against the ledger and adopts or declines each change, with a reason, in the record of changes. Because every departure is named, taking the next version is mechanical rather than a rewrite.

- **The PKAI base.** When the pkai-starter-kit or pkai-benchmark ships, the kit's keeper reads it against the ledger, adopts or declines each change, and says so. What this kit learns that would help every personal agent is offered to the PKAI keeper, as an offer, never as a push.
- **The LIØNSBERG layer.** The canon is the source, and the library is its readable form; the kit carries one edition of them. A new edition is pulled the same way. What the kit's players learn about the Game folds up to the canon by pull request (HOW-TO-IMPROVE-IT §6). An edition changes only at a turning, so this layer moves at the canon's pace rather than at every weekly gate.

## 7. The gate

Each kit release passes one gate, held at the weekly turn of the seed (HOW-TO-IMPROVE-IT §9). Its steps are not yet settled:

1. **Each layer's own check passes**: the Engine's own gate (its tests, the shadow run, the switch and the two-house test, in [`engine/ENGINE.md`](../engine/ENGINE.md)), the Agent's charter checks, the review of any new writing.
2. **The checks of §1 pass**: a house that keeps a layer runs only what the layers ship, and each lag behind an upstream has its reason.
3. **The shadow run.** A house that keeps a layer runs the candidate beside its current release on its own record until every difference is explained.
4. **The switch.** That house moves to the candidate, and plays on it.
5. **The two-house test**, once a second house holds the release: one commons repository, one thread settled, and one commitment kept across the two houses, each house's engine computing the same dates for it from its own copy of the record.
6. **The release is written**: the manifest, the record of changes, the lineage.

What improves a layer comes from play: each house's weekly retrospective, the rooms, the reviewers' guild (document 10). Each improvement lands as a proposed change on the layer it belongs to, soaks, and is accepted or refused by that layer's keeper.

## 8. How the folders follow

*Not yet settled.*

- **One repository for now.** The layers live as folders of `player-plus/`, each with its own version, lineage and changes, so that shipping stays one pull. A layer moves to a repository of its own only when its keeper is someone other than the kit's keeper.
- **The PKAI base held as a pinned copy.** The kit carries the pkai-starter-kit's parts it uses, unchanged, at a named version, with the ledger of differences beside them, so the upstream's next version can be compared file by file.
- **Moving there is gradual.** The Engine goes first; the PKAI base second, before the upstream's next major version is pulled; the rest as each is touched.

## 9. Open

- The names of the layers (the PKAI base, Player+, the LIØNSBERG layer, the Game Engine).
- Whether the ICE is a release layer of its own or ships with the Engine.
- How a house that has changed a layer locally says so in its own manifest, so that a pull does not overwrite its choices.
- Who keeps the LIØNSBERG layer when more than one house carries it.

---

**Siblings:** [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] · [[03 — The Game Engine (Architecture, 2026-10-24)]] · [[04 — The Player+ Agent (Architecture, 2026-10-24)]] · [[09 — Decisions and Their Reasons (Architecture, 2026-10-24)]] · [[10 — The Reviewer's Guide (Architecture, 2026-10-24)]] · [[Index — The Architecture (2026-10-24)]] · **Concepts:** [[The Kit]] · [[Lineage]] · [[Keeper]] · [[The edition]] · [[Release]] · [[Player+]]
