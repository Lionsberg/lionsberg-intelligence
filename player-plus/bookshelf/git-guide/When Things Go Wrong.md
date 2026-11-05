# When Things Go Wrong

Things will go wrong sometimes. That is normal. The most important thing to know is: **Git almost never loses your work.** It keeps a history of everything, and there is almost always a way back.

Here are the most common problems and how to handle them, using Claude Code to do the heavy lifting.

## Merge conflicts

**What happened:** You and a teammate both edited the same part of the same file. Git can merge most changes automatically, but when two people change the same lines, Git does not know which version to keep. It asks you to decide.

**What it looks like:** Claude Code will tell you there is a conflict and show you the two versions. You might see something like:

```
<<<<<<< HEAD
Your version of the text
=======
Their version of the text
>>>>>>> main
```

**What to do:** Tell Claude Code which version you want to keep, or how to combine them:

- "Keep my version"
- "Keep their version"
- "Combine both -- put my paragraph first, then theirs"
- "Here is what the final version should look like: [describe it]"

Claude Code will resolve the conflict, and you can commit and push as usual.

**How to prevent them:** Pull before you start working. The more frequently everyone pulls and pushes, the less likely conflicts become. When two people are editing the same document, coordinate so you are working on different sections.

## Diverged histories

**What happened:** You made commits locally, and someone else pushed commits to GitHub. Now your version and GitHub's version have gone in different directions.

**What it looks like:** When you try to push, Claude Code will tell you that your branch has diverged from the remote, or that the push was rejected because the remote has work you do not have locally.

**What to do:** Tell Claude Code:

- "Pull and then push" -- Claude Code will download the other person's changes, merge them with yours, and then push everything together.
- If there are conflicts during the merge, handle them as described above.

This is a normal part of collaborative work. It just means two people were working at the same time, and Git needs to combine the results.

## "I committed something I should not have"

**What happened:** You accidentally committed a file you did not mean to -- maybe a personal file, a very large file, or something that should not be shared.

**What to do, if you have not pushed yet:**

- "Undo my last commit but keep the changes" -- this un-commits but does not delete your work. Then you can commit again without the unwanted file.

**What to do, if you have already pushed:**

- Tell Claude Code: "I accidentally pushed [filename]. Help me remove it from the repository."
- Claude Code can remove the file from the project and commit that removal. Note that the file will still exist in Git's history (which is by design -- Git remembers everything). For most cases, that is fine. If the file contained something sensitive like a password, let Claude Code know and it can help you with more thorough cleanup.

## "I think I lost my changes"

**What happened:** You edited files but cannot find your changes, or something seems to have reverted to an older version.

**What to do:**

- "What is the status?" -- asks Claude Code to check what has changed and what is committed.
- "Show me the recent history" -- lists recent commits so you can see if your changes were saved.
- "Did I lose anything?" -- Claude Code can compare your current state to the last known good version.

If your changes were committed at any point, they are almost certainly recoverable. Git's history is durable -- even deleted files can be recovered from past commits.

## "I do not understand what this error means"

**What to do:** Copy-paste the error message to Claude Code and ask "What does this mean and what should I do?"

Git error messages are notoriously confusing, even for experienced developers. Claude Code can translate them into plain English and suggest the right fix. You do not need to interpret them yourself.

## The golden rule

**When in doubt, do not panic, and ask for help.** Whether that is Claude Code, a teammate, or Pete -- Git problems are almost always fixable, and having a second set of eyes makes them easier.

The worst thing you can do is start clicking or typing randomly to try to fix it. Describe what happened and let Claude Code (or a person) guide you to the solution.

## Next

[Working With Others](Working%20With%20Others.md) -- pull requests, reviews, and collaborative workflow.
