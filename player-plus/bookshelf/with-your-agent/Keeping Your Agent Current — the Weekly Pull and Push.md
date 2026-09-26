# Keeping Your Agent Current — the Weekly Pull and Push

*Proposed at Player+ Jam 4, 2026-09-26. How your agent learns from each new Player+ kit without losing anything that is yours, and how what you two learn goes back to help everyone. A proposal until it soaks; the people keep what helps.*

Your agent's home holds your memory, your notes, and the changes you two have made. Keeping current is never copying the new kit over it. It is reading what changed and taking what serves your house.

## 1. Knowing there is a new kit

- **Where releases appear.** The kit lives at https://github.com/Lionsberg/lionsberg-intelligence, in the folder `player-plus/`. Its [VERSION](../../VERSION.md) names the current release; its [CHANGES](../../CHANGES.md) say what changed and why, newest first. New releases are also announced in the shared space: Discord for now, then Buzz, then Sovereign Comms, in the order [Channels](../working-with-other-houses/Channels.md) describes.
- **Which one you have.** Your agent's `LINEAGE.md` names the version your house grew from, and its `pull_from` line says where the next one will be.
- **One question a week.** At closeout, or in the weekly look-back, your agent asks: *"Is there a newer kit than ours?"* It compares the VERSION online with its own LINEAGE. If the address does not answer, it tells you so rather than reporting "no news": a kit that moved looks just like a kit that stopped.

## 2. The pull: read, propose, then you decide

The kit's [pull-a-release](../../skills/pull-a-release/SKILL.md) skill is the whole of it. In plain words:

1. Your agent opens the new release read-only, never into its home, and reads CHANGES from the newest entry back to your version.
2. It compares each change with your house and proposes, one row per change, a one-line reason each: **adopt** it as is (the skill says *take*), **adapt** it to your house's shape, **decline** it, or **already better**, when your house does that thing another way that works better for you.
3. You decide, row by row. It answers your questions and does not argue past one round.
4. It applies only what you said yes to, by copying. Your memory, your notes and your own changes are never replaced. A change to its own charter it drafts for you to read and install by hand; an agent never edits its own charter unwatched.
5. It records in `LINEAGE.md` the version it now matches, with what it adopted, adapted and declined, so a declined change is not raised again unless you reopen it.

## 3. The push: offering back what you learned

Once a week the look-back ([the-retrospective](../../skills/the-retrospective/SKILL.md)) looks at the week's work and at your agent's working relationships, with you and with other agents. What it proposes for your own house is **Level 1**: you say yes or no to each. What would help every Player's agent is **Level 2**: it goes back to the kit.

This push is not a git push. Your copy never pushes to the repo it came from ([Moving In](../../MOVING-IN.md), *Before your first commit*). Instead:

1. Your agent drafts a proposal: what it changes, why it serves better, and what it rests on.
2. You choose whether to send it, and how: an issue or pull request on the kit, or a word to any Cell's Player+, to carry it there ([How Player+ and the seed change](../../HOW-TO-IMPROVE-IT.md), [Contributing](../../CONTRIBUTING.md)).
3. It soaks for a week while other Players and their agents read it; then the kit's keeper accepts or refuses it.

Your pull's report back — what you valued in a release, and where your house already does better — is sent the same way. The craft travels; nothing learned about you does.

## 4. The rhythm

Once a week, before your Turn:

- **Look back**, written by you or a reader with no part in the week.
- **Pull** the newest kit, if there is one.
- **Push** your Level 2 proposals, if you choose.

Each week's release gathers what the Players and their agents learned the week before, your house among them.

## The prompt

Give your agent these words, as they are:

> *Check for a newer Player+ kit. Show me what changed, and propose what to adopt, adapt or decline for our house, with a reason for each. Change nothing until I say.*

If your house does not carry `pull-a-release` yet, adopt it first ([Moving In](../../MOVING-IN.md), Path C).

---

*CC BY-SA 4.0 · LIØNSBERG*
