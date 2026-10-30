# state.json — the HUD's contract (state v1)

*The shape of the one file the HUD reads. `engine.py state HQ_DIR` writes it to `HQ_DIR/state.json`, folded over every holon the player holds: their own HQ and each cell under `cells/`. It is derived, safe to delete, rebuilt from `record/` (see `SCHEMA.md`). Fields are added, never renamed, within `v: 1`. A reader keeps fields it does not know and treats a missing field as empty.*

## Rules every field keeps

- **Times** are ISO 8601 strings with an offset. A date alone (`2026-10-30`) means that whole day.
- **Minutes** are numbers (float allowed). **Days** in float fields (`TF`, `FF`, `gap_days`, `age_days`) are working days when a calendar was read, calendar days otherwise; `calendar` at the top says which.
- **Ids** are event ids (sha256 hex) from the record. A link to an id not held reads `"not yet replicated"`, never an error.
- **Every list item carries `holon`**, the id of the holon it lives in, so a view across holons can always say where a card comes from.
- **Honest-empty:** a value the engine does not know is `null` or omitted, never guessed.
- **Roles, never names:** actors are `person:<handle>` or `agent:<handle>` exactly as the record has them.

## Top level

| field | type | meaning |
|---|---|---|
| `v` | int | `1`. |
| `generated_at` | time | when the engine wrote this file (the clock read, not computed). |
| `actor` | string | whom this state was dealt for (the Deal, owed and kept are seen from here). |
| `calendar` | string | `working-days` or `calendar-days`. |
| `holons` | list | every holon folded: `{id, name, kind, keeper, as_of, baseline}`. `baseline` is the n of the holon's newest `plan/baseline-<n>.json`, which the schedule measures variance and planned value against (`null` when none is frozen). `as_of` is the newest line seen in that holon: `{event, ts, lines}` (`lines` is the count read). Every number below is as of these lines. |
| `actors` | list | `{id, kind, for, holons, delegation, body, of}`; `body` is `prime` or `clone` for an agent's body (else absent) and `of` the prime's actor id for a clone. `kind` is `person` or `agent`. `delegation` is `null` for a person, else `{from, scope, holons, until, live}`. |
| `cards` | list | Work Cards with their schedule (below). |
| `commitments` | list | `{id, holon, card, title, keeper, by, size, witness, conditions, status, gap_days}`. `status`: `open` · `kept` (claimed and witnessed) · `kept-unwitnessed` · `broken` (past its by-when, not kept) · `released` · `returned`. `gap_days` is kept-time minus by-when; negative is early; `null` while open. |
| `threads` | list | `{id, holon, anchored_to, title, lines, last_actor, last_ts, settled, to, stake, push}`. `stake` is what rides on the thread: `{blocks: [card ids that wait on it: the live cards it is anchored to, those naming it as a predecessor, and everything downstream], critical (any of them on the critical path), by (the earliest by-when among them, else the thread's own), holder (whose line is owed; null when settled), urgency (the asker's own word, as written), minutes}`. `push` is `null`, or for a pushed thread (SCHEMA, The Push Protocol) `{sent (body.push as the sender sent it), push_by (whose each value is, `agent` or `person`, Push Protocol v1.1; empty for a v1 line, which reads as the agent's), state (active · retracted, once past its expires), weight (the receiver's own, push.weigh), by, why_by, blocks, critical, cost_if_late (each recomputed from the receiver's own record), own (which fields were recomputed), calibration (the sender's, below)}`. |
| `attention` | object | the person's budget and the gate (attention.py): `{budget: {minutes, sittings, asks_per_hour, min_gap_min, asks_per_day, room_asks_per_hour, room_min_gap_min, at_once, quiet, fewer, leans, always_pass, closed_until, phone}, set_by, fewer, minutes_today, sitting_open, asks_today, asks_last_hour, last_ask_at, next_slot, next_sitting, quiet_now, interrupt_now: [card ids], margin: [card ids], withheld: [{id, returns_at, why}], withheld_count, deferred: [{id, returns_at}], limits, agent_commitments}`. The budget is the person's own `attention` lines over the defaults; the gate governs interruptions only, never what may be read. |
| `decisions` | list | `{id, holon, title, holder, state, ratifier}`. `state`: `open` · `decided` (awaits ratify) · `ratified`. |
| `sightings` | object | per holon id: `{as_of, new, held, elevated, folded}`, each a list of `{id, holon, kind, text, where, actor, ts, status}`; `held` rows carry `held: {thread, note, by}`, `elevated` rows `elevated: {by, to, why, witness, line, ts}`, `folded` rows `folded_into`. A sighting is held when a thread note is anchored to it, elevated when a person's `elevate` names it, folded when it links to another sighting (sightings.py). |
| `questions` | list | `rfg` and `escalate` lines folded as questions that climb: `{id, type, from_holon, to, question, about, blast_radius, rung: {n, name}, holder, by, ts, asker, state, closed_by, next, past}`. `state`: `open` · `answered` · `decided` · `climbed`. `holder` is the keeper of the holon it climbed to (ball in court); `by` is the line's own, else its time plus the rung's time limit (ladder.py). |
| `ladders` | object | per holon id: its rungs `[{n, name, remit, days}]`, from `ladder.json`, else `calendar.json`'s `ladder`, else person · cell · council · body (1 · 7 · 14 · 30 days). |
| `tea` | object | the ledger (`ledger.py`): `{by_actor, by_holon, by_card, by_stream, witness, convertible: false, chain}`. |
| `discernments` | object | `{count, by_route, by_verdict}`. |
| `deal` | object | The Deal for `actor` (shape below). |
| `owed` | object | `{entries, proposals}`. Each entry `{kind, id, holon, title, holder, status, due, age_days, minutes}`; `kind` is `commitment` · `request` · `thread` · `ratify` · `decide` · `claim` · `handoff` (a body's handoff no person has reviewed, owed by the person it answers for; `minutes` from `review_min`) · `question` (an `rfg` or `escalate` past its by-when, owed by the holon it climbed to; carries `type`, `from_holon`, `rung`). `proposals` are agent lines whose reason came from untrusted text: shown for a person to take up, never counted as owed. |
| `kept` | object | `{window, by_holon, by_actor, commitments, learning}`; each tally `{made, kept, kept_unwitnessed, broken, released, returned, open, share}`. `share` is kept (witnessed) ÷ (kept + kept_unwitnessed + broken), `null` when nothing was due; `share_claimed` counts the keepers' own claims too. Only the named witness verifies: a witness line by anyone else leaves the commitment `kept-unwitnessed`. |
| `score` | object | per holon id: `{earned, planned, minutes_done, minutes_total, spi, as_of}` (from the schedule's earned value when present). *Not yet settled:* each holon's score also carries `yield: {made, kept_as_said, rework, share}` for the week ending at `now`: commitments made, those kept (a `kept` or `witness` line) at or before their by-when, rework (supersede, undo and returned-card lines), and share = kept_as_said ÷ made (`null` when made is 0).<br>*Not yet settled:* and `rate: {acts, person_hours, per_hour}`: a person's own lines in the week, the distinct clock hours in which each person wrote a line (summed over people; a whole hour counts once), and per_hour = acts ÷ person_hours (`null` when zero). Useful throughput is rate times yield (turn.throughput). |
| `buffers` | list | from the schedule: `{milestone, holon, size_days, consumed_days, chain_complete, signal}`. |
| `load` | list | from the schedule: `{actor, date, minutes, capacity}`. |
| `plan` | object | the whole Game Engine (`plan.py`, engine/ENGINE.md), per holon held, keyed by holon id, each on its own calendar and holon.json with the others' live commitments as externals (as the schedule runs), or `null` with a note. Each: `{capacity: {actor: {min_per_day, source: pledges · assumed · none}}, level_of_commitment, leveled: {card: {lev_ES, lev_EF, lev_TF, lev_start, lev_finish}}, critical_chain: [{milestone, cards, ties, marker, lev_finish}], buffers: {project, feeding}, fever, release: {card: {release_on, on_chain}}, day: {actor: {should, can, unsized, should_min, capacity_min}}, ppc, prc, commitment_level, misses, reasons, constraint_log, make_ready, ryg, weekly_plan, sbs: {placement, matrix}, missing: [sentences], engine}`. Will is never computed. |
| `path` | object | from the schedule: `{critical: [card ids], system: [card ids], finish}`. |
| `invalid` | list | lines the fold refused (`{id, type, actor, holon, invalid_reason}`), e.g. an agent's line outside its delegation. Shown, never counted. |
| `pending` | list | lines that link to what is not yet replicated, or were superseded. |
| `problems` | list | what reading found wrong (bad id, broken chain, fork, `duplicate_holon_id` or `holon_id_unproven` for a refused cell, `contract_unknown` for a holon born under a contract this reader does not know, whose lines are then all unverified), each with its `holon`. |
| `notes` | list | plain sentences when a part could not run, or ran with less than it should (e.g. no schedule.py; no calendar per holon). |
| `rooms` | object | per room holon id (a holon of kind `room`, or any with a posture line): `{id, name, keeper, present, posture, lines, offered, awaiting_yes, agreed_by, opened, closed, deal_open, deal_close, shape}` (shape below). |
| `roles` | object | per holon id: `{actor: role}`. The keeper is `keeper`; a `join` gives its `role` (else `member`, or `guest` when so joined); an affirmed agent is `agent`; a `leave` ends the Role. |
| `bodies` | list | an agent's bodies (bodies.py): `{name, actor, for, holon, kind (prime · clone), of, state (claimed · working · hold · handoff · done · archived · stale), task, first_word, brief, host, claimed_at, newest_line, review_min, handoff, reviewed, reviewed_at, asks_yes, cost_tokens, readers, affirmed_by, delegation_live, age_hours, lines_30m, lines_1h, flags}`. `lines_30m`/`lines_1h` count the body's own lines in the last half hour and hour; `delegation_live` is true when a person's live delegation names the body or its prime. `flags`: `past_day` · `quiet` · `no_task` · `stale`. `handoff` is the handoff line's id; `reviewed` the person's `witness` (or `discern`) naming it. `stale` is a body not at rest whose process the server saw gone, or with no line for 24 hours. |
| `desk` | object | `{holder, since, claims: [{actor, at, live}], collision}`, from `body` lines with `desk: true/false` and desk `claim`/`release` lines. The earliest live claim holds it; two live claims are a collision. |
| `bodies_closeout` | object | `{at, at_rest, by}` from the prime's last `body` line with `closeout: true` (`at_rest`: every other body was at rest then), else `null`. |
| `cost` | object | from `route` lines, per body AND per session: `{by_body, by_session, by_model, day, week, ceiling, limits}`. `day` and `week` each say `{tokens, by_body: {actor: tokens}, by_session: [{session, body, tokens, first, last}], by_model: {model: tokens}, unattributed, route_lines, lines, as_of, money}` (plus `date` or `from`); the top-level `by_body`, `by_session` and `by_model` are the day's. A session is the route line's `conversation` (`(no session)` when absent). A route line with no `body` counts as `unattributed`, never spread by guess. `money` is `{by_body: {actor: amount}, unit}` only when route lines carry a price, else `null`. `ceiling` is `{day_tokens, seven_day_pct, five_hour_pct, set_by}` from the person's newest live delegation that names one, else `null`. `limits` is `null`, or, when the machine's usage status file is present (calendar.json `usage_status`, else the harness's usual place), `{seven_day_used_pct, five_hour_used_pct, resets_at: {seven_day, five_hour}, ceiling_pct, source}`. These are the shapes `hud/bodies.js` and `hud/fixtures/bodies-*.json` read. |
| `calibration` | object | per Living Intelligence pushes were sent for (the line's `for`): `{pushes, measured, real, share, agent: {pushes, measured, real, share}, person: {…}, said, said_of}`, the agent's by-whens and the person's own apart (v1.1 `push_by.by`; a v1 line's by-when is the agent's). A push is measured once work on a card it blocked has moved; its by-when was real when that first move fell on or before the by-when's day. `share` = real ÷ measured; `said` puts it in words to the person ("the agent's by-whens: 3 of 4 real; yours: 1 of 1"), `said_of` to anyone else ("…; the person's: 1 of 1"), positive only. |
| `study` | object | `{view: {measure: value}}` from the person's own `study` lines of the last day (newest value per measure; measures: first_act_ms · reversals · attention_switches · one_breath · workload_words). Home-only: these lines never leave the holon. The daily Turn drafts one sentence per view from them. |
| `turn` | object | `{depth_due, last_daily, last_lunar, last_weekly, last_seasonal, next_weekly_due}`. `depth_due` is what the date calls for: `daily` · `lunar` (new and full moon) · `seasonal` (the turning), by the schedule's rhythms when present, else `daily`. The rest are times or `null`; a turn line's body says its `depth`. |

## How a commitment's status is read from the fold

record.py folds a commitment through the states of `types.json`: `open` · `claimed` · `kept` · `released` · `declined`. The status here maps them, and nothing else: `claimed` (the keeper said kept, no witness yet) is `kept-unwitnessed`; `kept` (a witness verified it) is `kept` when the witness is the one the commitment named (else `kept-unwitnessed`); `released` is `released`, and `declined` is shown as `released`; `open` whose by-when has passed with no claim is `broken`; `open` otherwise stays `open`. `returned` is reserved for a returned commitment when the registry gains that state. `gap_days` is the fold's own when it gives one.

## A card

```
{"id": "…", "holon": "…", "title": "…", "kind": "activity|milestone|decision|review|draft|research|birth|quest",
 "stream": "…", "holder": "person:…", "minutes": 30, "agent_minutes": null, "tokens_estimate": null, "by": "2026-10-30", "stage": "should|can|will|did",
 "state": "ready|taken|open|delivered|kept|returned|released|declined|done",
 "predecessors": ["…"], "successors": ["…"], "serves": ["…"], "audience": "holon",
 "ES": 0, "EF": 1, "LS": 2, "LF": 3, "TF": 2, "FF": 0, "start": "2026-10-30", "finish": "2026-10-31",
 "type": "activity|milestone|loe|summary|unit", "within": ["…"],
 "critical": false, "system_critical": false, "variance_days": null}
```

`type` is the schedule's: a card that holds others is a `unit`, its dates its cards'. `within` is the unit the card lies within. `ES`…`FF` keep their fraction of a working day (minutes are the one unit).

`agent_minutes` and `tokens_estimate` are the card's own estimates for giving it to a body, when it carries them (else `null`; never guessed). `ES`/`EF`/`LS`/`LF` are day offsets from the schedule's `as_of`; `system_critical` is true when a wider holon's pass published this card's milestone as on the system path ("the whole is waiting on this").

## A room

`join`, `affirm`, `posture` and `leave` fold into no item, so `rooms.py` reads them from the lines.

```
{"id": "…", "name": "…", "keeper": "person:…",
 "present": [{"actor": "person:…", "kind": "person", "for": "person:…", "role": "keeper|member|guest|…"},
             {"actor": "agent:…", "kind": "agent", "for": "person:… (who affirmed it)", "role": "agent"}],
 "posture": {"posture": "open|names-hidden|sealed", "participation": "chatham-house|fishbowl|off-the-record|<a named other>" (only when it differs),
             "curing_days": 2, "by": "person:…", "agreed_by": ["person:…"]} | null,
 "lines": ["<settled line id>", "…"],                      // newest first, at most 50
 "offered": [{"line": "…", "by": "agent:…", "for": "person:…", "reason": "human|delegated|untrusted"}],
 "awaiting_yes": ["<offered line id not yet agreed>"],
 "agreed_by": {"<line id>": ["person:…"]},                 // settle/decide/ratify naming the line; a bare settle by its author
 "opened": "<ts of the first join, affirm or posture>", "closed": "<ts of the leave that emptied it>" | null,
 "deal_open": <a Deal, as the record stood when the room opened> | null,
 "deal_close": <a Deal, as it stood when the room closed> | null,
 "shape": <the room's one shape, below> | null}
```

An agent is present only after a present person's `affirm`, and leaves with its person. Only a person's lines agree to anything. `posture.posture` is always a posture of export; a participation posture keeps its own name in `participation`.

### A room's shape

*Not yet settled:* folded by `rooms.shape` from the room's lines (engine/SCHEMA.md, **A room's shape**); `null` when the keeper gave the room no shape.

```
{"name": "the one shape",
 "parts": [{"name": "lobby", "does": "gather"}, {"name": "great room", "does": "propose"}, {"name": "the vote", "does": "vote"},
           {"name": "the writing", "does": "write"}, {"name": "reflection", "does": "reflect"}],
 "facilitator": "person:…", "part": "<the current part's name, or close>", "part_does": "gather|propose|vote|write|reflect|close",
 "since": "<ts of the line that moved the room here>",
 "moves": [{"part": "…", "at": "…", "by": "person:…", "line": "…"}],
 "posture": {"name": "chatham-house", "leaves_as": "names-hidden", "agreed_open": ["person:…"], "confirmed": ["person:…"],
             "not_confirmed": ["person:…"], "not_agreed": ["person:… present"], "withdrawn": ["person:…"],
             "cure_days": 3, "cure_until": "<ISO time>" | null, "curing": true,
             "changes": [{"by": "person:…", "at": "…", "line": "…", "narrowed_to": "off-the-record"} | {…, "revoked": true}]},
 "proposals": [{"id": "<the propose line>", "text": "…", "by": "person:…|agent:…", "for": "person:…", "at": "…", "card": "…" | null,
                "votes": 4 | null}],                                  // null while the vote has not closed
 "vote": {"rule": {"choose": 3, "advance": 2, "minutes": 20}, "opens": "…", "closes": "…", "open": false, "closed": true, "closed_at": "…",
          "cast": 6, "of": 7, "voters": ["person:…"], "chosen": ["<proposal id>"],
          "tie": {"votes": 4, "proposals": ["…"], "places": 1, "said": "…"} | null},
 "writeups": [{"card": "…", "proposal": "…", "title": "…", "holder": "person:…" | null, "by": "2026-10-30", "at": "…"}],
 "reflections": [{"by": "person:…", "text": "…", "at": "…", "line": "…"}],
 "closed": "<ts of the facilitator's close>" | null,
 "owes": [{"kind": "agree|vote|holder|confirm", "who": "person:…" | null, "about": "<posture or proposal id>" | null, "by": "…" | null}],
 "mine": {"agreed": true, "confirmed": false, "withdrawn": false, "vote": ["<proposal id>"] | null, "facilitator": false} | null,
 "refused": [{"line": "…", "why": "…"}]}
```

## The Deal

```
{"actor": "person:…", "minutes_available": 20, "minutes_dealt": 18, "room": ["person:…"],
 "opening": "Here's the deal.",
 "cards": [ {"n": 1, "section": "owed|thread|decision|ready", "id": "…", "holon": "…", "holon_name": "…",
             "question": "…", "options": ["…", "…"], "recommendation": "…", "why": "…",
             "unlocks": "…", "minutes": 5, "leverage": 12.4, "whole_waits": false} ],
 "beyond": {"count": 3, "minutes": 75, "cards": [ {"n": 4, "section": "…", "id": "…", "…": "…"} ]},
 "question": "What did we miss that matters to you most?",
 "rule": "urgent work moved ÷ own minutes; …", "as_of": {"<holon id>": "<ts of the newest line seen>"}}
```

`minutes_dealt` never exceeds `minutes_available` (first fit, in order). `beyond` counts what was ranked and not dealt, and carries the first twenty of it as `cards`, in the dealer's order, framed as dealt cards are and numbered on after them, so the next hand can be dealt from them without dealing again (an older Deal may carry only `count` and `minutes`). `fewer` names the dial's step (as set · fewer · much fewer · only what always passes); each card also carries `by`, `who_waits`, `always_passes` and `heavy` for the attention gate. The standing question is always present and costs no dealt minutes. Released and declined cards and milestones are never dealt; a decision handed to an agent is dealt to the person it serves. `section` is `owed` · `thread` · `decision` · `ready`; `kind` names the act (`commitment`, `request`, `propose` for an agent drafting a proposal of acceptance, `ratify`, `decide`, or the card's kind).

## Example (trimmed)

```json
{"v": 1, "generated_at": "2026-10-24T13:40:00-07:00", "actor": "person:player", "calendar": "calendar-days",
 "holons": [{"id": "h-home", "name": "Home", "kind": "person", "keeper": "person:player",
             "as_of": {"event": "9f2c…", "ts": "2026-10-24T13:31:00-07:00", "lines": 212}},
            {"id": "h-cell", "name": "The Cell", "kind": "cell", "keeper": "person:steward",
             "as_of": {"event": "41ab…", "ts": "2026-10-24T12:02:00-07:00", "lines": 88}}],
 "actors": [{"id": "person:player", "kind": "person", "for": "person:player", "holons": ["h-home", "h-cell"], "delegation": null}],
 "cards": [{"id": "c1", "holon": "h-cell", "title": "Choose the meeting day", "kind": "decision", "holder": "person:player",
            "minutes": 5, "state": "open", "TF": 0, "critical": true, "system_critical": true}],
 "commitments": [], "threads": [], "decisions": [], "sightings": {"h-home": {"as_of": null, "new": [], "held": [], "elevated": [], "folded": []}}, "questions": [],
 "tea": {"by_actor": {}, "by_holon": {}, "convertible": false},
 "discernments": {"count": 0, "by_route": {}, "by_verdict": {}},
 "deal": {"opening": "Here's the deal.", "minutes_available": 20, "minutes_dealt": 5, "cards": [], "question": "What did we miss that matters to you most?"},
 "owed": {"entries": [], "proposals": []},
 "kept": {"window": {"from": "2026-10-17", "to": "2026-10-24"}, "by_holon": {}, "by_actor": {}},
 "score": {}, "buffers": [], "load": [], "path": {"critical": ["c1"], "system": ["c1"], "finish": null},
 "turn": {"depth_due": "daily", "last_daily": null, "last_lunar": null, "last_weekly": null, "last_seasonal": null, "next_weekly_due": null}}
```
