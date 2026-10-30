---
status: current best understanding, loosely held · improved each week
licence: this page adapts MOVING-FROM-V3.0.md of pkai-starter-kit v3.1.0 (© 2026 Peter Kaminski, MPL-2.0); under MPL-2.0 it stays MPL-2.0
---

# Moving from 3.4

If your house was built from Player+ 3.0 to 3.4.1, **nothing is reinstalled and nothing you have stops working.** This page says what changed in 3.5.0 and how to take each piece, one at a time. It is written for your agent to read with you, and the `pull-a-release` skill uses it as its list.

3.5.0 is pull, not push, like every release: your agent proposes, you decide. Anything that touches the charter, the settings or the hooks is drafted for **you** to install by hand, and then you restart: type `/exit`, then double-click **My Agent** again (or start your agent the way you usually do). An agent never edits its own charter or hooks as part of a pull.

Your memory, your sessions, your agreements, your venue cards and your settings stay yours. Nothing on this page asks you to copy a release file over any of them.

## What changed, in words

- **The desk.** Your house now keeps one foreground at a time. If you start a second session while the first is working (another terminal, or the Claude app), the second becomes a *guest*: it says so in one sentence, works in its own folder under `bg/`, and does not change memory, the charter or the settings. A desk nobody has touched for 30 minutes is free.
- **Every house runs foreground and background.** The `foreground-background` skill now covers guests and the desk, and every house has a `bg/` folder for the work of its second sessions.
- **`grows_from`.** Every skill's lineage now says `grows_from` where it used to say `sits_on`: what a thing grew out of, not what it rests on. Player+'s own `LINEAGE.md` already used the new word.
- **`memory/` is the only memory.** The house's settings turn off Claude Code's own auto memory, and the charter says `memory/` wins if the two ever disagree.
- Smaller things, in `CHANGES.md` under 3.5.0: the clock stamps the time into every turn, a Windows machine without Git Bash has its own scripts and settings, several skills improved, and the shelf has a new chapter on output styles.

## What to take, item by item

Each item says what it touches. Take them in this order; each one stands alone, so stopping after any of them is fine.

### 1. The scripts — touches `scripts/`

Copy from the release's `scripts/` into the `scripts/` folder in your HQ:

- `desk` — new: the desk lease, guests, the write guard and the handoff notice.
- `now-hook` — new: it stamps the time into every turn, asks the desk to renew, and says when a handoff is waiting.
- `now` — **replace** your copy. It is now POSIX `sh`, so it runs on machines without `bash`. If you changed your copy, your agent shows you the difference first and keeps your changes.
- On Windows without Git Bash only: `desk.ps1`, `now-hook.ps1` and `now.ps1` as well.

On a Mac or Linux, `chmod +x` them. The hooks call every script with `sh`, so a lost executable bit (a zip download can lose it) does not break them. Nothing runs these scripts until step 3 wires the hooks.

### 2. `bg/` and the `.gitignore` line — touches the HQ and `.gitignore`

Create `bg/` in your HQ if it is not there. Add these two lines to your `.gitignore` (the desk's state is live session state, never history):

```
# The desk lease (scripts/desk): live session state, never history
.desk/
```

### 3. The hooks — touches `.claude/settings.json` (you install it)

This is the step that needs care. Your settings already hold the two Dojo permissions, perhaps permissions you added since, and perhaps hooks of your own, and **all of them must survive**. Never copy the release's `settings.json` over yours. Instead, your agent drafts the merged file into `outbox/settings.json` for you to read and install:

1. Start from your current `.claude/settings.json`, exactly as it is. Every permission stays.
2. Add the release's four hooks: `SessionStart` (`desk start`), `UserPromptSubmit` (`now-hook`), `PreToolUse` with the matcher `Write|Edit|MultiEdit|NotebookEdit` (`desk guard`), and `SessionEnd` (`desk end`). If an event already has entries of your own, **append** the release's entry to that event's list. If your house already wired a clock hook that calls `now-hook`, replace just that one entry with the release's. Never remove or reorder an entry you have.
3. Add `"autoMemoryEnabled": false` at the top level, but only after the look in the auto-memory folder that item 4 below describes.
4. Check that the result parses as JSON. Your agent says the difference in plain words: "four new hooks and auto memory off; your two permissions are unchanged."

Then you copy `outbox/settings.json` over `.claude/settings.json` by hand, and restart. On Windows without Git Bash, your agent merges from the release's `settings.powershell.json` instead.

**How to check it worked:** after the restart, ask your agent to run `sh scripts/desk status`; it names this session. Then start a second session in your HQ: it should say it is a guest. Close it.

### 4. Auto memory off, and two charter pieces — touches `.claude/settings.json` (in step 3), maybe `memory/`, and `CLAUDE.md` by your hand

Before Claude Code's auto memory is turned off, your agent looks in its folder (`~/.claude/projects/<this project>/memory/`, or under `$CLAUDE_CONFIG_DIR` if your machine uses one). If anything is there, it shows you, and with your yes it saves what is worth keeping into `memory/` with `save-a-memory`. Then the `autoMemoryEnabled` line goes in with step 3.

Two pieces of the charter come next, both drafted into `outbox/` for your own hand. Your agent copies the exact text from the release's `CLAUDE.md` and adapts nothing of its own charter unwatched:

- **The memory sentence**, for the Memory section: Claude Code has its own auto-memory folder too; the house turns it off, and `memory/` is the memory of record and wins.
- **The section "Foreground and background"**: what the desk is, what a guest may and may not do, and that the `foreground-background` skill carries the procedure. The hooks work without it, but with it your agent can explain what the hooks are doing. The section comes with one line in *Session structure*, so a guest says so before anything else, and with `bg/` and the new scripts in *Files and directories*. If your house runs on the carrier persona, its version of this section is called *More than one of me*.

Install them by hand, then restart.

### 5. Skills — touches the skill folders

Replace these folders whole, licence and lineage included, wherever your house keeps them: `skills/` as the Quest built it, and `.claude/skills/` for any your agent has taken on there.

- **`foreground-background`** — it now covers guests and the desk, and the guest message the hooks give points at its *If you are a guest* section.
- **`pull-a-release`** — it now reads a release's moving guide first, and merges settings instead of overwriting them.
- **`pull-from-benchmark`** — the same, for the starter kit.
- Improved, take if you like: `start-a-project`, `wrap-up-this-session`, `save-a-memory`, `check-my-setup`, `make-a-skill`.

Every other skill's `LINEAGE.md` changed one word, `sits_on` to `grows_from`. Copying the new ones in is tidy and optional.

### 6. `LINEAGE.md` — touches your house's own lineage

If your `LINEAGE.md` is still Player+'s own (`name: player-plus`), take the release's whole. If you made it your house's own, set `grows_from` to `player-plus 3.5.0` and add the 3.5.0 entry at the top of `lineage`. The skills' own lineage files came with their folders in step 5.

### 7. The shelf — touches `bookshelf/`

Copy in the changed chapters: *Two Ways In* in `your-house`, which replaces *Three Ways In* (delete the old one); *Foreground and Background*, which now has the desk; *Installing Claude Code* in `getting-started`, which now has the Windows `PATH` steps; and *Output Styles*, new in `getting-started`; *The Stairs* in `your-house` (one sentence) and *Troubleshooting* in `getting-started` (the new *Two Windows* section). Take the two books' `README.md` files too, so their lists match.

## Afterwards

Write the pull down in a session log: what you took, what you left, and anything your house does better than 3.5.0. That last part is what we most want to hear; `CONTRIBUTING.md` says how to send it.
