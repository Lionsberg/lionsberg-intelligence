# The heartbeat

Every holon is always awake. A process that never sleeps pulls what the holon follows on the cadences its person set, wakes the holon's agent when something is owed, and lets the agent wake its person at the Wise Right Time.

## The pattern and the means

The pattern is always awake. The means is whatever the holon has: a small server per cell, a single-board computer, a laptop that stays on, a VPS, a share of a timesliced network. The heartbeat is plain code under `python3 -I`, with the standard library alone.

One beat, in order:

1. **Pull** what is due: one question to the forge, and only the cells that changed and whose cadence came round are fetched.
2. **Receipts** for what arrived, written by the agent under its delegation.
3. **Signals**: a request that rose, a pain sighted by another, a fault, a commitment on a critical card whose buffer went negative. Each is read by the person's own emergency rule and the bell.
4. **Wake** the agent on a request, on an emergency, or on a cadence: a sitting in the person's attention budget, or `heartbeat.wake_every` seconds. Never twice for the same reason and ids within five minutes.

The person is woken only through their own Subscription Cards and the gate. The heartbeat never messages, rings, plays a sound or opens anything. It hands the agent the ids that may interrupt, and the agent speaks within the person's budget.

## Configure it

In the home's `holon.json`, under `heartbeat` (every key may be left out):

- `every_s`: seconds between beats (60; a Subscription with a shorter cadence sets the loop to it; never below 20).
- `wake_every`: the agent's own cadence in seconds (3600).
- `wake_command`: the command that wakes the agent, as a list of words. It receives the home folder as its last word and a JSON brief on stdin: `{reason, ids, as_of, budget}`. If it prints `{"cost_tokens": n}` as its last line, the cost is recorded.
- `wake_timeout_s`: how long a wake may run (600).
- `agent`: which affirmed agent the heartbeat serves, when the keeper has affirmed several.
- `forge`: `{kind, url, user, host, token_env}`. The token is read from the environment variable `token_env` names, never written in a file, and is taken out of the wake command's environment. A service starts with a bare environment, so its file must carry that variable by your own hand (launchd's `EnvironmentVariables`, systemd's `EnvironmentFile=`, a line at the top of the crontab). Without a forge, each due cell is fetched by git.

## The three files

`heartbeat.py install HOME --kind launchd|systemd|cron` writes the service files into `HOME/heartbeat/` and installs nothing:

- **launchd** (a Mac): one `.plist`, a beat every `every_s` seconds.
- **systemd** (Linux): a `.service` that runs one beat and a `.timer` that runs it every `every_s` seconds.
- **cron** (any Unix host): one line, on cron's own steps: at most once a minute, and in whole hours past 59 minutes.

It then says the commands to run by your own hand, for example `launchctl bootstrap gui/$(id -u) …` or `systemctl --user enable --now ….timer`. A system service is the person's own act. A host with none of these runs `heartbeat.py run HOME` in a terminal that stays open.

## What it costs

One question to the forge per beat, and one fetch per cell that changed. No model tokens: only a wake spends them, and only on a request, an emergency or a cadence. Each beat writes one line to `HOME/.heartbeat-log.jsonl`: what was pulled, the Receipts, the signals, whether the agent woke and why, and the cost (requests, seconds, bytes). Each wake that ran writes two `body` lines by the agent, working then done, with the seconds it ran and the tokens it reported. `heartbeat.py status HOME` sums the day.

## What it writes

A beat writes these and nothing else:

- lines pulled into `cells/`, with the pull's own `.pulled.json` and `.pull-log.jsonl`;
- the fold's signature cache, `.sigcache`;
- Receipts and the agent's `body` lines, in the agent's own file under `record/` (the home's, or a cell's);
- `.heartbeat.json` (what it remembers) and `.heartbeat-log.jsonl`.

All but the record are derived and safe to delete. Add them to the home's `.gitignore`.

## How to stop it

- launchd: `launchctl bootout gui/$(id -u)/<label>`
- systemd: `systemctl --user disable --now <label>.timer`
- cron: `crontab -e`, and remove the line that names the label.
- `heartbeat.py run`: Ctrl-C, or SIGTERM; it stops cleanly between beats.
