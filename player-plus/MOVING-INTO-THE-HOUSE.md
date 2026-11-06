---
status: current best understanding, loosely held · improved each week
licence: Creative Commons Attribution-ShareAlike 4.0
---

# Moving into the house

*For a home whose agent's folder holds the whole kit, with the shelf, the engine and the board inside it, as the kit built it before the layers were set apart. Your agent reads this with you. Nothing is reinstalled, nothing is deleted, and your record does not move.*

## What changes, and what stays

**Stays where it is:** your agent's charter, its memory and sessions, your record (`record/`, `holon.json`, your keys), and the history of the folder.

**Moves to the house:** three folders leave your agent's folder, and a link takes each one's name, so that every page and command that names them still finds them.

| Folder | Goes to | Why |
|---|---|---|
| `bookshelf/` | set aside; the Library in `HQ/Library/` takes its place | the books are the same in every house, and the Library stays current on its own |
| `engine/` | `HQ/engine/` | the Game Engine serves the whole house, not one agent |
| `hud/` | `HQ/hud/` | the board serves the whole house too |

## Before you begin

- Wrap up your session, and let your agent commit.
- Have one session open on your agent's folder, and no other.
- Know where your backup is.

## The steps

Your agent says each step in one line before it takes it, and you say yes.

1. **The Library.** Your agent fetches the kit, whole, into `HQ/Library/lionsberg-intelligence`: `git clone --depth 1 --branch release https://github.com/Lionsberg/lionsberg-intelligence.git "$HOME/HQ/Library/lionsberg-intelligence"`.
2. **The engine and the board.** Move the folders `engine` and `hud` out of your agent's folder and into `HQ`, in Finder or File Explorer, or let your agent move them. If `HQ` already holds an `engine` and a `hud`, because another agent of this house moved first, keep those, and rename yours `engine-before-the-move` and `hud-before-the-move`.
3. **The shelf.** Move the folder `bookshelf` out of your agent's folder to `HQ/Library/bookshelf-before-the-move`. It is set aside, not deleted. Anything you wrote on your own shelf is still there.
4. **The links.** Your agent makes three links in its folder, named `bookshelf`, `engine` and `hud`:
   - Mac: `ln -s "$HOME/HQ/Library/lionsberg-intelligence/player-plus/bookshelf" bookshelf`, then `ln -s "$HOME/HQ/engine" engine` and `ln -s "$HOME/HQ/hud" hud`, run in the agent's folder.
   - Windows, in PowerShell: `New-Item -ItemType Junction -Path bookshelf -Target "$HOME\HQ\Library\lionsberg-intelligence\player-plus\bookshelf"`, and the same for `engine` and `hud` with their places in `HQ`.
5. **The history.** Your agent adds three lines to the `.gitignore` in its folder, `/bookshelf`, `/engine` and `/hud`, and commits the move: the history records that the three folders left, and keeps every earlier version of them.
6. **The check.** Your agent runs, and says the result of each: `python3 -I engine/record.py verify .` (your record, unchanged); `python3 -I engine/conformance.py` (the engine, from its new place); and the first lines of The Deal. Then `sh scripts/refresh-library`, which says whether what runs here matches the Library.

The other pages of the kit that sit in your agent's folder may stay. They are in the Library too, and your agent can tidy them with you when you like.

## If a link cannot be made

Leave `engine` and `hud` where they were. The house works as it did before, and your agent says so. The Library is still worth having.

## To undo

Remove the three links, and move the three folders back to your agent's folder. Nothing else changed.
