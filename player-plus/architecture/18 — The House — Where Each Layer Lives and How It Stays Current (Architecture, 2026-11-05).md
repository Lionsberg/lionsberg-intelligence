---
title: "18 — The House: where each layer lives and how it stays current"
description: The layers of document 17, placed apart in a house; the rule for what may refresh on its own; and how a house follows each layer's source without being bound by it.
---

# 18 — The House: where each layer lives and how it stays current

*Document 17 says how the kit is made in layers. A kit placed whole in the agent's home fuses those layers in one folder. This page says where each layer lives in a house, why, and how each stays current. It settles 17 §8 for the installed house; the repository keeps its one folder.*

## 1. The principle

Player+ is the latest personal-agent kit, as its keeper ships it, with layers added. Each layer is one capability. Each stands without the ones above it, each has its own source and its own pace, and none may weaken the one below it. A person may hold some layers and not others.

## 2. Where each layer lives

| Layer (document 17) | In a house | What is there |
|---|---|---|
| The agent (the PKAI base) and Player+ | `~/My Agents/<name>/` | the charter and the matrix it imports, memory, sessions, inbox and outbox, the desk and the clock, the hooks and settings, the skills of the layers the house holds, the person's record |
| The Library (the LIØNSBERG layer of 17, and the kit as reference) | `~/HQ/Library/lionsberg-intelligence/` | the kit, whole and unchanged: every shelf, every skill, the pages, the architecture |
| The Game Engine | `~/HQ/engine/` | the running engine, copied out of the Library when the house takes it |
| The board (the ICE of 17) | `~/HQ/hud/` | the running board, beside the engine it reads |

`~/HQ/projects/` holds the person's work, as before. `HQ` holds no charter.

**Why the kit sits whole in the Library.** Every page of the kit names other pages by the kit's own paths. Kept whole, each of those paths stays true, the kit's tests describe the Library as it stands in every house, and a release can be compared with the last one file by file.

**Why the engine and the board sit in `HQ`.** They read every holon the person plays in, and a house may hold more than one agent. They belong to the house.

**Why the agent's home holds links.** The charter, the skills and the settings name `engine/`, `hud/` and `bookshelf/` beside them. A link of each name in the agent's home keeps those lines true wherever the host follows links (§5 says what is not yet walked), in a house built this way and in a home built before it. Where a link cannot be made, the builder leaves one copy of each thing: the shelf copied into the home, the engine and the board moved into it, and the receipt says so.

## 3. What may refresh on its own

One rule: **what is read may refresh on its own; what runs, or tells an agent how to act, changes only when its person says yes.**

- The Library is read, never run. It follows the kit's `release` branch, and the agent refreshes it at the first session of a day or a week (`scripts/refresh-library`).
- The charter, the hooks, the settings, the skills, the engine and the board run or instruct. A refresh never touches them. It names the engine, the board, the skills, the scripts and the hooks whose copy in the Library differs, once, when the difference is new; the charter and the settings are read at a pull (`pull-a-release`). A page on the shelf that the agent acts from (the seed, the Field of Agreements, the commands for a room) is still only read: the refresh names it when it changes, and the agent keeps to the lines it held until its person has read the change.

This holds the firewall: a page that arrives by a refresh is information.

## 4. Following a source without being bound by it

Each layer follows its own source (17 §6). The ledger of differences (`LEDGER.md`) records where the agent layer departs from the personal-agent kit it is built on, file by file, so that the next release of that kit is read against it and each change is taken or declined with a reason. `RELEASE.md`, at the top of the kit, is the manifest of 17 §5: the layers, their versions and their places.

## 5. Open

- The link on Windows (a junction) is written into the builder's page and has not been walked on a Windows computer.
- A host's search may not follow a link from the home's top; the charter tells the agent to search the shelf by its own path.
- A house with two agents shares one engine and one board. Whether it also shares one record, in `HQ`, is not settled; today each agent's home holds its person's record.
- Whether a layer's skills should move between layers as the paper floor is made fuller.

---

**Siblings:** [[17 — The Layers — How the Kit Is Built, Improved and Shipped (Architecture, 2026-10-29)]] · [[00 — The System — Six Layers, One Record (Architecture, 2026-10-24)]] · [[04 — The Player+ Agent (Architecture, 2026-10-24)]] · [[Index — The Architecture (2026-10-24)]]
