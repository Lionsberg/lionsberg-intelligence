---
name: check-my-setup
description: Checks the person's computer for agent work and reports what is ready and what is not — the terminal is readable, git is present and knows who they are, a review surface for markdown exists, cloud-sync is not fighting git, the launch command works, backups and a password manager are in place — with the smallest fix for each gap, for the person to apply. Use when the person says "check my setup", "is everything set up right", "something's off with my terminal", "why cannot I read this", after a new machine or an OS upgrade, or when the agent notices a symptom (dimmed text invisible, git refusing a commit, a folder inside OneDrive).
license: MPL-2.0
---

# Check my setup

A house runs on a few boring things being right: a terminal you can read, git that works, a place to read markdown, folders that are not being synced out from under you, a backup. When one is wrong the symptoms show up somewhere else and look like something else. This skill checks them in order and reports plainly — a sentence or two each, not a systems report — with the smallest fix for each.

## The checks

1. **Readability.** Print a small sample: a plain numbered list where one line is dimmed the way your interface renders secondary text — no blockquote, heading or code fence, which the interface restyles — and say beforehand which line should look fainter. Ask if every line is clearly readable. If not, fix it before anything else — on Windows the usual cure is Windows Terminal's *Campbell PowerShell* colour scheme and a dark theme; on Mac, a higher-contrast profile. Nothing else matters until they can see you.
2. **Git.** `git --version`; then `git config --global user.name` and `user.email`. Missing git: optional, but strongly recommended; point at *Installing Git* in the kit's `bookshelf/getting-started/`. Missing identity: git will refuse the first commit with "please tell me who you are" — ask for the name they would like on their history and an email they use, and set both.
3. **Cloud sync.** Resolve the agent home's and the HQ's real paths. If either is inside OneDrive, Dropbox, Google Drive, or iCloud (on Mac, `Library/Mobile Documents` or `com~apple~CloudDocs` in the path; on Windows, `OneDrive`), say so: git and sync engines contend and both lose. The fix is to move the folder to the top of the home folder — the person moves it, with you coaching.
4. **A review surface.** Ask what they use to read and edit markdown. None: point at the review surfaces in the kit's `REQUIREMENTS.md` (Typora, MarkText, MeetingWords; Obsidian or VS Code are fine if already in use). The terminal is not meant to be their reading room.
5. **The launch icon.** Does double-clicking **My Agent** on the Desktop open a terminal in HQ with the agent running? If not, look at the icon itself: on a Mac, the `My Agent.command` file on the Desktop; on Windows, the shortcut's target and, if Windows Terminal is installed, the `my-agent.json` profile fragment under `%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\LIONSBERG\`. Then check that `claude` is found: if `where claude` / `which claude` finds nothing, its folder is not on `PATH` (*Installing Claude Code* has the steps). On Windows, test in a new *window* after closing every Windows Terminal window; a new tab keeps the old environment. A PowerShell profile that does nothing is most often the execution policy blocking the profile (`Get-ExecutionPolicy` says `Restricted`). Re-add the icon with their yes (it touches a file outside the house).
6. **The desk.** `sh scripts/desk status` (or `scripts\desk.ps1 status` in PowerShell) runs and names this session or none. If the hooks are not firing, check `.claude/settings.json` has the four desk hooks; on a Windows machine without Git Bash, the PowerShell variant, `.claude/settings.powershell.json`, has to be the one installed — copied over `.claude/settings.json`.
7. **Remote Control.** Mention `/rc` once if they have not used it: the same session, continued from a phone or the web.
8. **Backups.** Ask, do not assume: is the computer backed up, automatically, and have they ever restored a file from it? An untested backup is a hope. Local plus off-machine is the standard.
9. **Secrets.** Ask: do passwords and keys live in a password manager, and none in the folders you work in? If any are in the house, help move them out now; do not read them aloud.
10. **Tool versions.** Claude Code and git reasonably current? Say how to update; do not run an update without a yes.

## The report

One short block: ✓ for each thing that is right, and for each gap the one-line fix and who does it (you, or them by hand). Then stop. Apply fixes one at a time, with a yes each, and re-check the one you fixed. Record anything durable — the review surface they chose, the launch word, git deferred — with `save-a-memory`.

## What this skill never does

- Change settings files, install software, or move folders without a yes.
- Read or display a secret it finds.
- Turn off a safety layer, or suggest it, to make a check pass.
