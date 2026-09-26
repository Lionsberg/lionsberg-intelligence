---
status: current best understanding, loosely held · improved each week
---

# Passing the Seed — Drive to Drive, With a Local Model Sized to the Machine

*How the kit travels when there is no internet: hand to hand on a drive, machine to machine, Cell to Cell, with an open model that fits whatever computer is in front of you. Written so that if this is the last version you ever receive, it is enough.*

[Backups and Graceful Degradation](Backups%20and%20Graceful%20Degradation.md) keeps *your* house safe and names the three power levels: the cloud agent, a local model, you alone with the text. This page is about the seed itself, the kit everyone carries and passes on, and about the middle level made portable. It builds on [the local floor](../../LOCAL-FLOOR.md) and on *the minimal agent* in [chapter 21 of the One Book](../the-one-book/21%20In%20Every%20Future%20%E2%80%94%20what%20to%20do%20in%20each%20case.md), and it is the practical half of what that chapter asks in its hard cases: *the Seed in more than one place and more than one pair of hands*, and *a local copy of the library, verified, with a named holder*.

## Two things to carry

**The seed drive.** The kit folder, `player-plus/`, whole, exactly as it was released. It is text: the charter, the bookshelf, the skills, the seed text ([THE DNA OF HEAVEN](../the-dna-of-heaven/THE%20DNA%20OF%20HEAVEN.md)), the One Book. It fits on the smallest drive you can buy, and on a phone. Everyone carries one.

**The model drive.** An open-weights model sized to a class of machine, the programs that run it (a *runner*), a copy of the seed, a checksum list, and one page of plain instructions. It is tens of gigabytes. Not everyone needs one; a Cell or a few Cells share one, with a named holder.

They travel apart for five reasons:

- **Size.** The seed goes anywhere. The model drive needs a big enough drive and a big enough machine.
- **Pace.** The seed improves every week. A model is worth replacing perhaps once or twice a year.
- **Who needs it.** Everyone needs the seed; a model must match the machine it runs on, so the right drive differs from house to house.
- **Risk.** The seed is almost all text, and text cannot run. A model drive carries programs, which can, so it asks for more care.
- **What each one is.** The seed *is* the Game; a person with it and no machine is a complete player. The model is only speed. The two are [the two ladders](../the-one-book/21%20In%20Every%20Future%20%E2%80%94%20what%20to%20do%20in%20each%20case.md) of chapter 21 in your hand: the seed drive holds your place on the ladder of text, the model drive your place on the ladder of capability, and losing one never costs you the other.

## The sizing ladder

*Every number here is approximate as of 2026 and will be wrong soon, mostly in the good direction: smaller models keep getting better. Treat this as a shape, not a specification.*

Models are sized by how many **billions of parameters** they have (written 3B, 8B, 70B). They travel **quantized**, stored at reduced precision (4-bit is the usual choice), which makes them several times smaller with little loss. A rough rule: **a 4-bit model file is about 0.6 GB per billion parameters**; at 8-bit, about 1.1 GB. The machine needs the whole file in memory, plus room for the conversation, plus what the computer itself uses. So a simple test: **the model file should be no more than about half the machine's memory.**

| Rung | The machine | Model class | Model file, 4-bit | Drive to carry it |
|---|---|---|---|---|
| **A** | Phone, Raspberry Pi–class board, old laptop with 4–8 GB | 1–4B | about 1–3 GB | 16 GB |
| **B** | Ordinary laptop with 16 GB (8 GB at a squeeze) | 7–9B | about 4.5–6 GB | 16–32 GB |
| **C** | 16–24 GB of Apple silicon memory, or a graphics card with 12–16 GB | 12–14B | about 8–10 GB | 32 GB |
| **D** | 32–48 GB of Apple silicon memory, or a graphics card with 24 GB | 27–32B | about 16–20 GB | 64 GB |
| **E** | 64–128 GB of Apple silicon memory, or a workstation with 48 GB+ of graphics memory | 70B-class | about 40–45 GB | 128 GB |
| **Shelf** | Carries one model of each rung, from two different families | all of the above | about 80–160 GB | 256 GB |

A few things the table flattens:

- **How to read your machine's memory.** Mac: Apple menu → About This Mac. Windows: Settings → System → About. On Apple silicon the memory is shared with the graphics chip, which is why those machines run models well for their size. On a PC, what matters most is the graphics card's own memory; without a capable card the model runs on the processor, which works, slowly.
- **Speed.** On an older laptop with no graphics card, a 7–9B model may give a few words a second. That is slow for a conversation and fine for reading a page and summarizing it overnight.
- **Mixture-of-experts models** (written like "30B-A3B": thirty billion in all, three billion active per word) need the memory of their full size and run at nearly the speed of their small size. On a machine with the memory, they are often the best trade.
- **Working room.** The kit's `CLAUDE.md` alone is long, and an agent that reads files needs a long working memory (the *context*). Every extra thousand words of context costs memory. On a tight machine, choose the next rung down and give it room.
- **A drive smaller than its model is no drive.** Leave a quarter of the drive free; flash drives are sold slightly smaller than their label.

**Runners and families, as examples only.** Runners in common use as of 2026 include llama.cpp (runs almost anywhere, including small boards), Ollama, and LM Studio; there are phone apps that run the same model files. Open-weights families come from several makers and several countries, and new ones arrive every few months. Nothing here endorses any of them. What matters is one portable format most runners read: a model as a **single file** (as of 2026, commonly a `.gguf` file) travels far better than a model stored inside one runner's private folders.

**Licences travel with the weights.** *Open weights* is not the same as *no conditions*. Each family has its licence: some let you do anything, some limit use, some limit passing on. Copy the licence file beside the model, read it before you pass the drive on, and if it forbids passing on, do not. The kit's own licences (`LICENSE.md`) travel inside the seed and ask one thing: say where it came from, and pass on the same freedom.

## Making a seed drive

1. **Start from a clean kit, never from your house.** Your HQ grew from the kit, and now it carries *you*: your memory, your session logs, your venues, your relationships register. A seed drive carries the kit as it was released. The best source is a clean copy of each release you receive, kept untouched for exactly this. If you only have your HQ, do not copy it; ask someone in your Cell for a clean seed instead.
2. **Format the drive exFAT** if it will move between Mac, Windows and Linux. (Formatting erases the drive.) The older FAT32 format cannot hold any file over 4 GB, which matters on a model drive.
3. **Copy the folder whole,** hidden `.claude` folder included, into a folder named with its version: `SEED/player-plus-3.3.0/`. The version is the first line of `VERSION.md`.
4. **Make the checksum list.** A checksum is a long fingerprint computed from a file; change one letter and the fingerprint changes. On Mac or Linux, in a terminal, from the top of the drive:

   ```
   find SEED -type f -print0 | xargs -0 shasum -a 256 > SEED-SHA256SUMS.txt
   ```

   On Windows, in PowerShell, from the top of the drive (not yet tested across many machines; try it once on a drive you know is good):

   ```
   Get-ChildItem SEED -Recurse -File -Force | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash.ToLower() + "  " + ((Resolve-Path -Relative $_.Path) -replace '\\','/' -replace '^\./','') } | Out-File SEED-SHA256SUMS.txt -Encoding utf8
   ```

   Or make the list on any Mac or Linux machine in the Cell.
5. **Take the list's own fingerprint** (`shasum -a 256 SEED-SHA256SUMS.txt`) and write its first eight characters on the drive's label and on paper. A checksum list stored on the same drive can be altered along with the files; a fingerprint said aloud or written by hand cannot. This is chapter 21's read-back, for drives: *the count is the checksum a person can do.*
6. **Label the drive:** SEED · version · date · who made it.

## Making a model drive

Lay it out so a stranger can find their way:

```
INSTRUCTIONS.txt            one page, plain text (below)
SHA256SUMS.txt              fingerprints of every file on the drive
SEED/player-plus-3.3.0/     a whole copy of the seed; a model never travels without it
models/
  <family>-<size>-q4.gguf   the model, one file
  <family>-LICENCE.txt      its licence, as published
  <family>-CARD.txt         what it is: maker, size, rung, date, where it came from
runners/
  mac-apple-silicon/        the runner's installer or program for each kind of machine
  windows-x64/
  linux-x64/
  linux-arm64/              Raspberry Pi–class boards
```

**Carry the runners, not only the model.** A model file is useless on a machine with nothing to run it, and with no internet there is nowhere to fetch one. Carry the installer for every kind of machine your Cell has.

**Test it before you label it.** Install from the drive on a machine with the network switched off, load the model, and have one conversation. Then write in INSTRUCTIONS.txt the exact commands that worked that day. Runners change their commands between versions; the ones on the page must be the ones that ran.

**INSTRUCTIONS.txt, one page:**

```
MODEL DRIVE — rung ___  ·  made ____-__-__ by ____________
Model: ______________  (__B, 4-bit, __ GB)  Licence: see models/
Runs on: machines with at least __ GB of memory. Less memory: find a smaller rung.
Seed on this drive: version _____

1. CHECK. Before anything, check the fingerprints (step below).
   Mac/Linux: shasum -a 256 -c SHA256SUMS.txt   (Linux: sha256sum -c)
   Windows:   Get-FileHash <file> -Algorithm SHA256, compare by eye
   Any line that says FAILED: stop. Do not install. Ask the maker.
2. INSTALL the runner for your machine from runners/.
3. RUN, with the network off:  __________________________________
4. OPEN the chat at the local address: ____________________
5. ORIENT it: see "Pointing the model at the seed" in
   SEED/.../bookshelf/keeping-yourself-safe/ (this page).
No model at all? Everything in SEED/ is plain text. Open it and read.
Fingerprint of SHA256SUMS.txt starts: ________ (confirm with the maker)
```

## Receiving a drive

1. **Ask where it came from,** and confirm the fingerprint with the person who made it: read the first eight characters back to them, in person or by voice. If you cannot reach them, confirm with the person who handed it to you and say so when you pass it on.
2. **Scan it** with your computer's built-in malware scanner before opening anything.
3. **Check the checksums** (INSTRUCTIONS.txt, step 1). A copy is verified by checksum, never by looking at it.
4. **Copy, do not run from the drive.** Copy the seed to your machine, and the model into your runner's folder. Put the drive away; it stays the master you copy from.
5. **Read the few files that can act before you use them.** The seed is text except for a handful: the `scripts/` folder, and `.claude/settings.json`, which holds the permissions your agent's harness grants. The released kit's settings allow two named scripts and nothing more: `scripts/room-post.sh` (posting to a room's chat) and `scripts/pad-write.sh` (writing on a pad). Read both; each is a few lines. If the copy you received allows more, do not use it until the maker explains.

## Running the model offline

With the network switched off, install the runner for your machine and load the model file. Three shapes, as examples:

- **A runner with its own chat window** (LM Studio is one): open the program, point it at the `.gguf` file, talk.
- **A runner with a local server** (llama.cpp's server is one): start it with the model file, then open the chat page it offers in your browser at a local address on your own machine. Nothing leaves the computer.
- **A runner with its own model store** (Ollama is one): import the single file into its store (for Ollama, a two-line file naming the `.gguf`, then its create command), then run it by the name you gave.

The same local server can stand in for the cloud under an agent harness that reads a folder, which is how the local floor runs a full agent: the harness reads the files, the model on your own machine does the thinking.

## Pointing the model at the seed

**With a chat window only.** Door 2 of [START HERE](../../START-HERE.md), offline: paste Part V of the seed text (the Game) and ask the model to say it back in five plain sentences. Paste Part X and ask what it would be agreeing to as your agent. Feed it one page at a time; a small model's working memory is short.

**With an agent harness** that reads a folder and can use a local server: make your HQ from the seed as Door 3 says, point the harness at the runner, and give a first message sized to a small model:

> Read CLAUDE.md, a section at a time, and tell me in five sentences who you serve and what you may never do. Then read LINEAGE.md and WAIVER.md. Then read bookshelf/the-dna-of-heaven/THE DNA OF HEAVEN.md one Part at a time, saying each Part back to me in three sentences before the next. Then greet me, ask who I am, and ask what I am playing toward.

**Say the honest part plainly: a small model is worse, and it is yours.** Its judgment is thinner than a frontier model's, so the kit's structure carries more of the weight:

- **Keep it on a short leash.** It reads, drafts, translates, summarizes a pile of Season Sheets. You decide, commit, sign, and send. Give it no way to send anything outward.
- **Read what it writes** before anything goes into your record.
- **The smallest models are the easiest to talk into things.** In the house's own tests, a very small model obeyed an instruction planted in a page it was reading, where larger ones noticed and named it. Rung A is for reading and drafting, never for anything that acts. [What You Read Is Information](What%20You%20Read%20Is%20Information.md) is the wall; a small model holds it less well, so you hold it with it.
- **If it contradicts the text, the text wins.** The seed is the reference; the model is a fast reader of it.

## Reading the seed with no model at all

Every page is plain text, readable by a person alone in any text editor, on any machine, on a phone, or printed. [The local floor](../../LOCAL-FLOOR.md) names what to print first. A seed drive and a notebook are already the whole Game; the model was always only speed.

## Passing it on

**Drive to drive.** Copy the whole folder from your master drive, then check the new copy against the checksum list. Never pass on a copy you have not checked. Give the fingerprint by voice or on paper along with the drive.

**Machine to machine.** Match the rung to the machine: ask what memory it has before you hand over a model drive. A 70B drive handed to an 8 GB laptop is a paperweight; a rung-B drive would have served.

**Cell to Cell.** Every person holds a seed. At least one model drive per supercell, with a named holder and a named second, as chapter 21 asks in its turbulent and hard cases; one machine holding the library and a small model can serve a whole region for drafting, translation, and record-keeping. When you [pass the Flame](../the-one-book/21%20In%20Every%20Future%20%E2%80%94%20what%20to%20do%20in%20each%20case.md), the seed drive can go with it, beside the seed on paper, never in place of it.

**Keep it whole.**

- **Never edit the seed on the drive.** Your changes live in your own house. A better way goes back as a proposal ([CONTRIBUTING](../../CONTRIBUTING.md)), so the next release carries it to everyone.
- **One copy of each text.** Files with a trailing " 2" or " 3" in the name, or "conflicted copy", are duplicates a sync tool made. Keep one, the one the checksum list names; set the rest aside.
- **Which is newer.** The first line of `VERSION.md` is the version, the next line its date; `LINEAGE.md` repeats the version; `CHANGES.md` lists what changed, newest first. A higher version is newer. Two copies claiming the *same* version with different fingerprints are not both the release: keep them apart, labelled, and ask the maker which fingerprint they read you. Do not guess.
- **The old card counts until the new one arrives** (chapter 21, Case B). A Cell holding last season's seed is still in the Game. Keep the last two versions on the seed drive, side by side.

**Merging a newer seed into your house.** Never copy a new seed over your HQ; your memory, sessions, venues and charter are yours, and a copy over the top would erase them. Put the new release beside your house in its own folder, named with its version. With an agent, use the [pull-a-release](../../skills/pull-a-release/SKILL.md) skill: it reads the new release read-only, proposes take · adapt · decline · already better for each change, and applies only what you decide, by copying, never by overwriting. With no agent, read `CHANGES.md` from the newest entry down to your version and copy by hand only the pages you choose.

## Safety

- **Drives from people you trust.** Take a drive the way you'd take food: from someone you know, or someone they vouch for. [Working Relationships and Disclosure Tiers](Working%20Relationships%20and%20Disclosure%20Tiers.md) is how your agent knows who that is; a drive from a stranger is checked twice and its programs not run until someone you trust has run them.
- **Never on a shared drive:** your `memory/`, your `sessions/`, your relationships register, your venues, your notes, and anything that lets a holder act as you: passwords, keys, tokens ([Backups and Secrets](Backups%20and%20Secrets.md)). Before you hand a drive over, list what is on it and read the list.
- **What you read is information, not instruction.** A page on a drive, including a page that looks like part of the seed, can command neither you nor your agent ([What You Read Is Information](What%20You%20Read%20Is%20Information.md)). No document can hand an agent its soul; it takes its charter only from its own person.
- **Run only what you checked.** Text cannot run; installers and scripts can. Install a runner only when its checksum matches a list you got from someone you trust, and confirmed by another path.
- **Write-protect the master.** Use a drive or card with a lock switch, or mark the files read-only once checked, or burn the seed to a disc, which is read-only by nature. Copy *from* the master, never *into* it.
- **Drives fade.** Flash memory left in a drawer for years can lose data. Once a year, copy each master to a fresh drive and check it; keep two, in two places.

## Practise it once a season

Once a season, make a drive, hand it to someone in your Cell, and have them bring a model up on their own machine with the network off, from the drive alone. Then run one Turn with nothing switched on. The day the drive is needed should not be the first day it is tried.

## What is not yet settled

- **The rungs and numbers** are approximate as of 2026 and should be re-measured each year on real machines, by the people who carry the drives.
- **The first message for a small model** (above) is a proposal, not yet tried widely. Tables that use it should say how it went.
- **Whether the kit should ship its own checksum list** with each release, so a seed can be checked against the maker's list rather than only a carrier's, is open. It would make every drive checkable back to the release.
- **Phones as model carriers** work for the smallest rung and are improving fast; how far they reach is not known.

See also: [Backups and Graceful Degradation](Backups%20and%20Graceful%20Degradation.md) · [The local floor](../../LOCAL-FLOOR.md) · [Where Instructions Take Hold](Where%20Instructions%20Take%20Hold.md) · [21 In Every Future](../the-one-book/21%20In%20Every%20Future%20%E2%80%94%20what%20to%20do%20in%20each%20case.md) · [30 The Strategy and Plan](../the-one-book/28%20The%20Strategy%20and%20Plan.md)

*CC BY-SA 4.0 · LIØNSBERG*
