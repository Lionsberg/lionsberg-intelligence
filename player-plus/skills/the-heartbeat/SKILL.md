---
name: the-heartbeat
description: The always-on hand — one plain process per holon, on any host, that pulls on the person's cadences, writes Receipts, reads the signals, and wakes the agent only on a request, an emergency or a cadence; the agent then wakes the person only through their own Subscription Cards and their emergency rule, within their budget, through the gate, and never with a sound; the emergency rule as the person's own `limits` Card, drafted with the default three rules; installed on any host by the person's own hand; its status, and its cost per wake and per day; and how it stops. Use when the person says "keep this running", "keep watching", "wake me when…", "why did you wake me", "do not wake me for…", "how much is the heartbeat costing", "stop the heartbeat".
license: MPL-2.0
---

# The heartbeat

Every holon is always awake. A process on some host that never sleeps pulls the holon's subscriptions on their cadences, wakes the holon's agent on a request, an emergency or a cadence, and lets the agent wake its person at the right time. The host is whatever the holon has: a laptop that stays on, a small server, a single-board computer, a shared host. The heartbeat is plain code: it calls no model and spends no model tokens; only a wake of the agent costs tokens. The module is `engine/heartbeat.py`; the contract is `engine/SCHEMA.md`, **The heartbeat**, with the rules it reads in **The pull**, **Subscriptions** and **The emergency rule and the bell**.

## What a beat does

1. **In order:** pull what is due (`pull`); write Receipts for the home's agent and person when anything is new (`receive`); read the signals (a request that rose, a pain sighted by another, a fault such as a cell that could not be pulled, a commitment on a critical card whose buffer went negative); classify each by the person's own rule, and ring the bell only by permit; wake the agent when it is owed; record.
2. **What it records.** Two `body` lines by the agent per wake that ran (working, then done, named `heartbeat`, `reason: delegated`, so under a live delegation from your person that covers `body`), never one per beat; a wake that could not start writes no `body` line and is logged `ok: false`; one JSON line per beat in `<home>/.heartbeat-log.jsonl`; what it remembers in `<home>/.heartbeat.json`. Both files are derived and safe to delete.
3. **One beat by hand:** `python3 -I engine/heartbeat.py beat <home>`. `--dry` asks and decides, and fetches, wakes and keeps nothing. Run a dry beat once before anything is installed, and read its `said` to your person in a line.

## When the agent is woken

4. **Three reasons, and no other:** a request that rose; a signal the person's rule says wakes them; or a cadence, a sitting in their attention budget or `heartbeat.wake_every` seconds in the home's `holon.json` (an hour, when it names none). Never twice for the same reason and the same ids within five minutes.
5. **How it wakes you.** `holon.json`'s `heartbeat.wake_command` names the command as a list of words, never a shell line. It runs with the home folder as its last word and a brief on stdin: the reason, the ids, as of when, and the budget (what may interrupt now, the next sitting, the dial, whether it is quiet hours). The command runs without the forge token's variable in its environment. With no command, nothing runs and the report says so. `holon.json` is the person's own file; a cell's is never read for this.

## How you then wake the person

6. **Only by their own word.** When you are woken, you speak to your person only about the ids the gate handed you (`interrupt`), only on the surfaces their Subscription Cards name, and only within their attention budget. Everything else waits for their next sitting, and you say nothing of it until then.
7. **The bell rings by permit.** A signal reaches them before their sitting only when their own rule wakes them AND the source holds a permit for the kind: the signal arose within their own holon; or a member rang a pain, a fault or a security signal (the Andon permit, held by joining); or their Subscription Card's `bell`, or a live Agreement's `permits.bell`, names it. A sender's urgency is a claim on the card and never rings by itself.
8. **The closed word outranks every rule.** While their `closed_until` holds, nothing passes. Quiet hours hold for everything but what their rule wakes and what they said always passes.
9. **Never a sound.** The heartbeat never messages, rings, plays a sound or opens anything, and neither do you on its account. A wake is a card in their Deal or a line on the surface they chose: never an alarm, never audio, never a window opened on their screen.
10. **"Why did you wake me."** Answer from the record: the reason, the signal, the rule that matched (or the default), the permit that let it ring. *"A member of the cell sighted a pain at 14:02; your rule wakes you for a member's pain; the Andon permit let it ring."* If it should not have woken them, offer to change their rule, never the sender's line.

## The emergency rule

11. **Their own `limits` Card.** What may wake them is decided by them, in advance, as a `limits` line: their own act, in their own home, never yours. With none, the default holds, said as `basis: default`.
12. **Draft one with the default three, in words first.** *"Three things may wake you: a commitment on the critical path that can no longer be kept in time; a pain from a member of your holon; a security signal. Everything else waits for your next sitting."* Then, only on their yes, the Card at `cards/limits/<a short name>.md` in their home, and say why: while they hold no admitted key, a fenceless Card there already acts as their own unsigned line at home. They append it by their own hand: `python3 -I engine/card.py append <home> <home>/cards/limits/<name>.md --as person:<them>` (`subscribe`, rules 2 and 3, the same way). The `rules` value is one line of inline JSON, as the Card's form requires:

```
---
v: 1
ts: "<now, with its offset>"
actor: "person:<them>"
for: "person:<them>"
type: limits
body:
  rules: [{"signal": "commitment", "when": "buffer_days < 0", "on": "critical", "wake": true}, {"signal": "sight", "kind": ["pain"], "from": "members", "wake": true}, {"signal": "security", "wake": true}]
  else: wait
audience: holon
reason: human
---

# limits · what may wake me
```

13. **Each rule** names its `signal` (commitment · sight · request · say · security · fault) and `wake`, and may name `on: critical`, `kind` (the Sighting kinds it covers), `from` (`members`, or `permit`) and `when`, read in a small fixed grammar and never run as code: `<field> < <number>`, `<field> > <number>`, `<field> == <value>`, `by < next_sitting`, `outside_limits`, `<field> outside_limits`. The first rule that matches decides; with none, `else`. A rule outside the grammar matches nothing and is said under `ignored`. To see how one signal would fall: `python3 -I engine/emergency.py classify <signal.json> --rule <rule.json> --members <person:x …>`, where the rule file is a rule set marked as theirs, `{"rules": [ … ], "else": "wait", "basis": "limits"}`; a bare rule or list is refused and the default answers. Leave out `--rule` to see how the default would fall.
14. **Inside the limits is the stream's own variation.** Waking a person for it is the costlier mistake. When they ask to be woken for more, say that once, kindly, and then draft what they asked for.

## Install, by their own hand

15. **The files, not the service.** `python3 -I engine/heartbeat.py install <home> --kind launchd` (`systemd` for a Linux host, `cron` where neither runs; `--out <folder>`, else `<home>/heartbeat/`) writes the service files for the host's scheduler and installs nothing. It prints the commands that put it on the host and the one that stops it. Show them those commands; they run them by their own hand, because a system service is their act. cron beats at most once a minute.
16. **The forge.** For the pull, `holon.json`'s `heartbeat.forge` names `kind`, `url`, `user`, `host` and `token_env`: the *name* of the environment variable that holds the token, which they set in the service's environment (`pull`, rule 7).
17. **The loop's cadence** is `heartbeat.every_s` in `holon.json` (a minute when it names none), shortened to the shortest Subscription cadence, and never faster than twenty seconds. `python3 -I engine/heartbeat.py run <home>` (`--every <seconds>`, `--beats <n>`) runs the loop in the foreground, for a test or a host with no scheduler.

## Status, and the cost

18. **What it has done:** `python3 -I engine/heartbeat.py status <home>` gives the last beat, the last wake, the beats, wakes and errors today, `cost_today` (forge requests, seconds, bytes) and `next_due` for the next wake and the next pull.
19. **The cost per wake** is the wake command's `cost_tokens`, when its last output line reports one: it is kept on the beat's `wake` and on the agent's `done` body line. **The cost per day** is `cost_today` for the forge, plus the `cost_tokens` on the day's `done` lines for the model. Say both in one line when asked: the beats, the forge requests, the wakes and the tokens they spent. A wake whose command reports no cost is said as not measured, never guessed.

## Stopping it

20. **By the command `install` printed,** run by their own hand: `launchctl bootout …` on a Mac, `systemctl --user disable --now …` on Linux, or removing the cron line. A loop run in the foreground stops on its signal. Stopping it loses nothing: the next pull brings every commit since the last head this home saw, and the record holds everything that happened.

## What this skill never does

- Install, start or stop a system service; the person does, by their own hand.
- Wake the person outside their own Subscription Cards, their emergency rule and their budget.
- Make a sound, send a message, or open anything on their screen.
- Write their `limits` Card for them, or change it because a sender asked.
- Place a draft in their `cards/` before their yes.
- Put the forge token anywhere but the environment.
- Spend model tokens on a beat. Only a wake costs tokens, and it says what it cost.

## How it degrades to paper

```
MY SOURCES AND TIMES — <name>
source            check at               wake me between only for
the first cell    9:00, 13:00, 17:00     a member's pain
the commons       Monday 9:00            —
```

A person with a notebook checks their sources at the times they wrote down, and keeps a short list of what may wake them between. The heartbeat is that, running.
