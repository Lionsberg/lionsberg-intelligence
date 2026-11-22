---
library-status: current best understanding, not yet reviewed line by line
---

# Backups and Graceful Degradation

*What still works when something you lean on fails, so that the Game keeps playing one step down.*

[Backups and Secrets](../../../pkai/keeping-yourself-safe/Backups%20and%20Secrets.md) says how to keep your house safe: two backups, a restore you have tested, and no secrets in the folders your agent works in. This page adds what playing the Game asks of it. Each thing you lean on can fail: the computer, the AI service, the room, the power. When one does, you lose speed, not the Game. It plays on one step down.

The failures below run from the most likely to the least.

## What to back up

Both folders, whole: your agent's home, and your HQ, which holds your `cards/`, your projects and the library. Back them up as [Backups and Secrets](../../../pkai/keeping-yourself-safe/Backups%20and%20Secrets.md) describes. A Cell's repository, cloned in `<HQ>/cells/`, is also held by every other member of the Cell, so what you wrote together outlives any one computer: with the access you were given, it can be cloned again.

## A new or repaired computer

Your house comes back from the backup. Put both folders back where they were: your agent's home at the top of your home folder, and your HQ beside it, in Documents or at the top of your home folder. Keep both out of cloud-synced folders.

If the whole computer came back from a machine backup, the Desktop app and your agent's environment may already be there. Start a session in the environment and type hi.

If only the two folders survived, two things are set up again, as the starter kit's build describes: the Claude Desktop app, signed in to your account, and your agent's environment in its Code tab, made on your agent's home and nothing else. If the new computer lacks git, the build installs it as well. Open a session on your HQ, where the starter kit is kept, and ask Claude to repair the house by the kit's build: the build looks first for a house already on the computer, and picks it up as it is. Nothing is rebuilt over an existing house. Then start a session in your agent's environment and type hi.

Your agent wakes remembering its name, you, and where you left off, because all of that was written in its folder. Your Cards are where you left them. Secrets come back from your password manager.

## When the AI service is down, or the account is gone

Everything your agent knows is plain text you can read: its memory, its session logs, your projects. Your Cards are Markdown files in `<HQ>/cards/`, and any editor opens them. You can read every one, and write new ones by hand.

The Game plays on paper:

- **The six sentences on a sheet:** *I join this Cell · here is a piece of work · I will do it by Friday · it is done · yes, that works for me · we are green.*
- **The Turn on one page:** what you set out to do, what you kept, what you learned and what comes next, with the week's offers and requests beside them; these are the five lines [The Weekly Turn](../player-plus-modules/15%20The%20Weekly%20Turn.md) teaches.

When the agent is back, it can copy the paper into Cards, reading each one back to you; the ones that are your own act are written on your yes. Where a Card copied from paper disagrees with the paper, the paper wins; a Correction Card sets it right.

If the account is gone for good, the house still stands. An agent on a new account reads the same folders and picks up where the text leaves off.

## When a room, a pad or a shared repository is down

The Cell still meets: around a table, on a call, by phone. Write your Cards at home, in `<HQ>/cards/` or on paper, and put the ones you choose into the Cell's repository when it is back, pulling first.

Keep the phone numbers and addresses of the people in your [Cell](../player-plus-modules/Lexicon.md), exchanged with their yes, somewhere that is not the room: your phone's contacts, and on paper.

## When the power or the network is out

Print, while everything works, three pages from the wiki, whole: The Story, The Game and The Flame (`<HQ>/library/lionsberg/wiki/LIØNSBERG Core Documents/LIØNSBERG Invitation/`). Print the six-sentence sheet and the Turn page beside them, and keep a pencil with them. With those and the people of your Cell, the Game plays with no screen at all, and the Flame can still be passed by hand.

## Now and then

At each turning of the season, ask your agent three things:

- *When was the last backup, and when did we last restore a file from it?*
- *Are the printed pages current?*
- *Are the numbers and addresses of my Cell still right?*

With these in place, a failure costs you speed, and the Game goes on.

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
