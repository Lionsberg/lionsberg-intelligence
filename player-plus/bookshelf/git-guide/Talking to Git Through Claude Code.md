# Talking to Git Through Claude Code

You do not need to learn Git commands. Claude Code handles the technical details -- you just tell it what you want in plain English. Here is a phrasebook of things you can say, organized by what you are trying to do.

None of this needs to be memorized. Claude Code understands natural language, so paraphrasing is fine. When in doubt, just describe what you want.

## Saving your work

When you have made changes and want to save them:

- **"Commit my changes"** -- saves a snapshot of your work locally.
- **"Commit everything and push"** -- saves all your changes and uploads them to GitHub.
- **"Commit but do not push"** -- saves a checkpoint locally without sharing it yet. Useful when you want to save your progress but are not ready for others to see it.
- **"Commit everything, including new files, then push"** -- picks up any brand-new files you created and sends everything to GitHub.

## Syncing with GitHub

Your computer and GitHub can get out of sync -- you have made changes locally, or someone else has pushed changes. These phrases keep things lined up:

- **"Pull the latest"** -- downloads recent changes from GitHub.
- **"Pull and push"** -- grabs the latest changes, then uploads yours. A good habit because it makes sure you have the newest version before sharing.
- **"Is everything synced?"** or **"Are we up to date with GitHub?"** -- asks Claude Code to check.
- **"Anything untracked?"** -- checks if you have created new files that have not been saved to Git yet.

## Checking what has changed

- **"What has changed?"** or **"What is the status?"** -- shows what files you have modified since the last commit. Completely safe -- it does not change anything.
- **"What do we have that is not pushed?"** -- shows what you have committed locally but have not sent to GitHub yet.
- **"Pull and tell me what is new"** -- downloads recent changes and summarizes what other people have been working on.

## Tagging milestones

You can label a specific version so you can find it later -- like a bookmark in the project's history:

- **"Tag this as v1-draft"** -- marks the current state with a name you choose.
- **"Bookmark this as pre-demo"** -- same idea, different words.

Useful before big changes or when you have reached a version worth remembering.

## Working with branches

Branches let you experiment without affecting the main version. You probably will not need them often, but when you do:

- **"Create a branch called experiment"** -- makes a separate workspace for trying things out.
- **"Switch back to the main branch"** -- returns to the main version.
- **"Merge my branch into main"** -- folds your experimental changes back into the main version.

See [Branches](Branches.md) for more about what branches are and when to use them.

## Recovering and investigating

Git keeps a history of every change, which means you can always go back:

- **"Show me the recent history"** -- lists recent commits (save points) so you can see what happened.
- **"What did this file look like yesterday?"** -- shows you a previous version of a specific file.
- **"Undo my last commit"** -- takes back the most recent save point. (Your changes are not lost -- they just become un-committed again.)

## Tips

- **You do not need exact wording.** Claude Code understands intent. "Save my work and send it to the cloud" works just as well as "commit and push."
- **When in doubt, say "commit and push."** It is the most common thing you will need.
- **"What has changed?" is always safe.** It just looks; it does not touch anything.
- **If something goes wrong, describe the problem.** Claude Code can usually fix it. Git rarely loses anything permanently.

## Next

[What Is a Commit](What%20Is%20a%20Commit.md) -- understanding the building block of Git history.
