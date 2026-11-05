---
status: current best understanding, loosely held · improved each week
licence: Creative Commons Attribution-ShareAlike 4.0
---

# Moving your agent out of HQ

*For a home built by an earlier kit, where your agent lives in the folder called HQ. Nothing is reinstalled and nothing is lost. Move when it suits you; it takes about twenty minutes.*

## Why move

Earlier kits put everything in one folder: your agent and your work. Now the kit builds two, side by side in your home folder:

```
your home folder/
  My Agents/
    River/        your agent's home: who it is, what it remembers, your record
  HQ/
    projects/     your work, and never a CLAUDE.md
```

Your agent lives in its own folder and walks over to HQ to work. A place is not a person, so HQ holds no instructions for an agent. A second agent, one day, gets its own folder beside the first and shares the same HQ.

## Before you start, with your agent

Start a session with your agent, as you do now, and say:

> We are moving you out of HQ. Please fetch https://raw.githubusercontent.com/Lionsberg/lionsberg-intelligence/main/player-plus/MOVING-THE-AGENT-OUT-OF-HQ.md and https://raw.githubusercontent.com/Lionsberg/lionsberg-intelligence/main/player-plus/CLAUDE.md into your `outbox/`, read the first, and get ready.

Your agent then:

1. Saves both files in `outbox/`, so that it can read this page again after the move.
2. Stops the board, if it is open in your browser.
3. Gives you the command that stops the heartbeat, if you set it up (the `the-heartbeat` skill), because it names the old folder. You run it.
4. Lists which folders in HQ are your own work, and which are its own.

Then close every session with your agent in the Claude app, and the **My Agent** window if you use the terminal. Check that your backup is recent: moving a folder is safe, and a fresh copy makes it safer.

## The move, by your own hand

Use your agent's name where this page says River. Your agent's own folders stay with it: `CLAUDE.md`, `memory/`, `sessions/`, `record/`, `cells/`, `outbox/`, `inbox/`, `bg/`, `.claude/`, the hidden `.git` folder with its history, and the kit's folders (`engine`, `hud`, `skills`, `scripts`, `personas`, `bookshelf`, `architecture`, whichever your home has). Your work moves to the new HQ: `projects/`, and any folder your agent listed as yours. Your keys are not in either folder, so they do not move.

**On a Mac, in Finder:**

1. Press **Cmd+Shift+H** to open your home folder. Choose **File › New Folder** and name it **My Agents**.
2. Drag **HQ** into **My Agents**. Click it once, press Return, and rename it **River**.
3. Back in your home folder, choose **File › New Folder** and name it **HQ**.
4. Open **My Agents › River**. Drag **projects**, and each folder your agent listed as your work, into the new **HQ**.

**On Windows, in File Explorer:**

1. Type `%USERPROFILE%` in the address bar and press Enter. Click **New folder** and name it **My Agents**.
2. Drag **HQ** into **My Agents**. Click it once, press F2, and rename it **River**.
3. Back in your home folder, click **New folder** and name it **HQ**.
4. Open **My Agents › River**. Drag **projects**, and each folder your agent listed as your work, into the new **HQ**.

## Then, with your agent again

Open the Claude app and start a new session: click the folder control, then **Open folder…**, then **My Agents** and **River**. (By the terminal way, open a terminal, type `cd ~/"My Agents"/River` on a Mac or `cd "$HOME\My Agents\River"` in PowerShell, then `claude`.) Say:

> We moved: you now live in My Agents, and HQ is beside it. Please read outbox/MOVING-THE-AGENT-OUT-OF-HQ.md and finish the move with me.

Your agent then does these, saying each before it does it:

1. **Checks that nothing was lost.** Its memory, its last session log, its git history (the old commits are all there) and your record (`python3 -I engine/record.py verify .`, and the conformance sheet). Each should read as it did before.
2. **Drafts two changes for you to install by hand,** because your agent never changes its own charter or settings:
   - **The settings:** `.claude/settings.json` with one line added under `permissions`, `"additionalDirectories": ["~/HQ"]`, so that it can reach HQ without asking each time. Drafted into `outbox/settings.json`. You copy it over `.claude/settings.json`: the `.claude` folder is hidden, so press **Cmd+Shift+.** in Finder, or choose **View › Show › Hidden items** in File Explorer, to see it. Then start a new session.
   - **The charter:** the paragraph *Your home and the headquarters* near the top of `CLAUDE.md`, from the copy in `outbox/`, saying that the work lives in `~/HQ` and that HQ never holds a CLAUDE.md; and every path in `CLAUDE.md` that names `skills/…`, changed to `.claude/skills/…`, to match step 5. Drafted as a whole `CLAUDE.md` into `outbox/`, with the differences shown to you in plain words; you copy it over the old one.
3. **Makes HQ ready:** a short `README.md` in HQ that says what it is, and, if you use git, a history of its own for HQ. Your agent's own history records once that your projects left its folder; from then on, HQ's history keeps them.
4. **Fixes the doors.** By the terminal way, the **My Agent** icon on your Desktop, and on Windows the **My Agent** profile in Windows Terminal, still open the old place, where no agent lives now. With your yes, it writes both again for the new folder, and adds the change to `setup-receipt.md`.
5. **Takes its skills to where they load.** Earlier kits kept the skills in a folder called `skills`, where the Claude app does not load them. With your yes, your agent moves that folder's contents into `.claude/skills/`, keeping any skill of its own, and says which it now has.
6. **Starts the heartbeat again,** if you stopped it.

## What to know afterwards

- **Your old conversations** stay in the Claude app's list, under the name HQ. They now open on the new HQ, where no agent lives: read them there, and start new work in a new session on your agent's folder. Your agent's own record of every session is in `sessions/`, and moved with it.
- **The first session on the new folder** may ask whether you trust it, and may ask again for permissions you once allowed. That is expected: to the app it is a new folder.
- **To undo:** close every session. Move `projects/` and your other work folders from the new HQ back into River, then delete what is left of the new HQ (its `README.md`, and its hidden `.git` if your agent made one), never moving it into River. Drag River out of My Agents into your home folder and rename it **HQ**. Then ask your agent to move its skills back from `.claude/skills/` to `skills/`, and to restore `.claude/settings.json` and `CLAUDE.md` from its own git history, as they were before the move.

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
