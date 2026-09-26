---
status: proposed · current best understanding, loosely held · improved each week
---
# Backups and Graceful Degradation

*Proposed at Player+ Jam 4, 2026-09-26; drawn from practice with local models and plain-text houses, and from the git guide [Your First Commit](../getting-started/Your%20First%20Commit.md), carried here from the [PKAI starter kit](https://peterkaminski.ai/starter-kit)).*

## Why

Your HQ is your agent's memory and your record: who it is, what it knows about you, every session log, every note. It lives on one computer, and a computer can be lost, stolen, or die. [Backups and Secrets](Backups%20and%20Secrets.md) gives the two strong recommendations from setup; this page adds the layers, the restore, and what still works when the AI itself is out of reach.

## Three layers

**1. Git, pushed to a private remote.** This is the main one. Your agent already keeps a git history of HQ quietly as you work ([Why This Stack](../getting-started/Why%20This%20Stack.md)). On its own that history sits on the same disk, which is why Backups and Secrets says git alone is not a backup. Pushed to a **private** GitHub repository, it is: every copy of a git repository is a whole copy, history and all. Ask your agent once: *"Create a private GitHub repo for my HQ and push to it"* ([Your First House](../getting-started/Your%20First%20House.md) shows the words; [GitHub Account Setup](../getting-started/GitHub%20Account%20Setup.md) comes first). After that, commit and push at every wrap-up. GitHub is never required; if you choose not to use it, the next two layers carry the whole weight.

**2. A whole-machine backup.** Mac: **Time Machine** to an external drive. Windows: **File History** to an external drive. Turn it on and let it run. It catches what git does not: other folders, the things you forgot were there.

**3. A copy offline, now and then.** Once a month or so, copy HQ onto a drive that then goes in a drawer, or to a trusted person's house. A drive that is not plugged in cannot be reached by a virus, a bad sync or an agent's mistake.

An untested backup is a hope. Restore one file from each layer once, and open it.

## What to back up, and what never to put there

**Back up:** HQ whole: `memory/`, `sessions/`, your notes and projects, `CLAUDE.md`, `venues.md`, and `.claude/` (your agent's skills and settings). If your agent's home is a separate folder from HQ, back up both.

**Never in any repository, public or private:** keys, passwords, tokens, a pad's cookie file, a room's agent link, anything that lets a holder act as you. A private repo is private, not secret: it still lives on someone else's server. Ask your agent to list these in `.gitignore` so git never picks them up, and keep them in a password manager, which is backed up on its own ([Backups and Secrets](Backups%20and%20Secrets.md) says why). Never push your HQ to the repo you downloaded the kit from ([MOVING-IN](../../MOVING-IN.md)).

## Restoring on a new computer

1. Walk [the Quest](../getting-started/Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md) again ([Mac](../getting-started/Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest%20for%20Mac.md) · [Windows](../getting-started/Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest%20for%20Windows.md)) through Gate 5: the account, the terminal, Git, Claude Code.
2. At Gate 6, do not make a new HQ from the kit. In your terminal, go to your home folder (`cd ~`), type `claude`, sign in as at Gate 7, and say: *"Clone my private GitHub repo for HQ into a folder called HQ here."* It will walk you through signing in to GitHub.
3. Close Claude Code, go into the restored folder (`cd ~/HQ`), and type `claude`.

Your agent wakes remembering its name, you, and where you left off, because all of that was written down in HQ. No GitHub? Restore HQ from the machine backup or the drawer copy into your home folder, then do step 3. Secrets come back from the password manager.

## When the AI is out of reach

Everything in your HQ is plain text. If the AI service is down, too expensive, or gone, you lose speed, not knowledge. You can open every memory, session log and note and keep playing by hand; a notebook and two or three people are already a complete Player. Call these the three power levels: the cloud agent, then a local model, then you alone with the text.

**The middle level (advanced).** A smaller model can run on your own computer, with no internet, and read the same HQ. It is slower and less wise, but it remembers everything, because the memory is the text. If you want it, set it up with your agent's help while everything works, not during the outage.

**When the room goes down.** The chat server, the pad, or the video room can fail too. Keep the phone numbers and emails of your [Cell](../the-great-game/04%20Cells.md), exchanged with their yes, somewhere that is not the room: your phone's contacts, and on paper.

## The weekly check

Once a week, at wrap-up ([wrap-up-this-session](../../skills/wrap-up-this-session/SKILL.md)), your agent can ask two questions:

- *"Is everything committed and pushed?"*
- *"When was the last machine backup, and the last drawer copy?"*

Pushing is ask-first in this kit, so it asks, and you say yes. If you'd rather it push to your private HQ repo at every wrap-up without asking, tell it so in your own words; it saves that as a memory of what you said. The [check-my-setup](../../skills/check-my-setup/SKILL.md) skill asks the backup question too, and more.

*CC BY-SA 4.0 · LIØNSBERG*
