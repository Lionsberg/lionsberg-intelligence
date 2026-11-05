# A Brief for a Body

*Player+ 4.0, 2026-10-31. The opening every brief carries when your agent hands work to another body of itself: a background instance, a guest, a body in a room. A proposal until it soaks; change it when a better opening serves.*

Your agent can run as more than one body at a time: the foreground, which holds the desk, and others it starts for a long job or a meeting ([Foreground and background](../../.claude/skills/foreground-background/SKILL.md)). Each new body starts with nothing but its charter and what the hooks print. The awakening hook (`.claude/hooks/awaken.sh`) prints, at every start and again after a compaction, five things: the desk, which is what awaits you, who holds the desk and what another body left; the last session's RESUME HERE; the live bodies and the rule of one desk, one watcher; the matrix's corrections, the dispositions your agent holds against its defaults ([the character matrix](../../personas/README-from-the-kit.md)); and, after a compaction, the reminder that a compaction is not an awakening.

A body that skips that print works from its defaults and from a stale picture of the work. So every brief opens by asking the body to read it, and to say which parts it read. The saying is the proof: **a body that cannot say what it read has not awakened.**

## The template

Copy the block below as the first lines of the brief, and put the task after "Then:".

```text
Awaken first: read the desk the hook printed, the matrix's corrections, the last resume block, and say in your first reply which you read. Then:

<the task: the outcome wanted, the completion condition, the boundaries (what it may read, what it may write), and how it reports>
```

## How it is used

- **The first line never changes.** The task follows it. A brief that opens with the task, and puts the awakening later or leaves it out, is sent back and opened again.
- **The first reply names what was read.** For example: "I read the desk, the matrix's corrections and the last resume block." If the hook printed that a part could not be read (the matrix did not load, no session yet), the body says that too.
- **Silence is a signal.** If the first reply does not say what it read, the foreground asks once. A second silence means the body did not awaken; the foreground closes it and starts it again.
- **The task is an outcome, not a list of steps**, as the foreground-background skill asks: what is wanted, when it is done, what the body may read and write, and how it hands back.

*CC BY-SA 4.0 · LIØNSBERG*
