#!/usr/bin/env python3
"""bodies.py — an agent's bodies (the prime and its clones), the desk, and what each body cost.

    fold(lines, now=None, live=None) -> {"bodies": [...], "desk": {...}, "cost": {...}, "closeout"}
    wakes(lines, now=None) -> [{name, actor, holon, reason, host, opened, closed, seconds, seconds_basis,
                                cost_tokens, tokens_whole, working, done}]
    cost_of_attention(lines, bodies=None, pull_log=None, now=None, days=1) -> {per_day, today, basis,
                                                                               as_of, days, bodies, said}
    beat_log(home_dir) -> {rows, from, said} from the heartbeat's beat log, or None (the engine's read)

Pure: lines in, state out; no clock but `now`, no process probe. `live` is optional: what the
HUD's server saw on this machine ({actor: {"process": "alive" | "gone" | "elsewhere"}}); it is
never in the record and only sharpens `stale`.

A body is told by its `body` lines (types.json): name, state (claimed · working · hold · handoff
· done · archived), task, brief, review_min, cost_tokens, host, desk. The prime archives a clone
by its own `body` line naming the clone. A body is a clone when an agent `affirm`s it, `of` that
agent; otherwise it is a prime. Per body:

  {name, actor, for, holon, kind (prime · clone), of, state (… · stale), task, first_word, brief,
   host, claimed_at, newest_line, review_min, handoff, reviewed, asks_yes, cost_tokens, readers,
   affirmed_by, age_hours, flags}

  handoff   the id of its `handoff` line (or of a `done` line that carries a review_min above zero;
            review_min 0 says there is nothing to review, as the heartbeat's wake lines say)
  reviewed  a person's `witness` (or `discern`) line that names the handoff, else null
  flags     past_day (claimed more than 24 hours ago and not at rest) · quiet (no line for 3 hours
            while claimed or working) · no_task (no task 10 minutes after the claim) · stale
  stale     a body not at rest whose process `live` says is gone, or with no line for 24 hours
            (named assumptions; the desk's own lease is 30 minutes without a turn, read live)

The desk: `body` lines with `desk: true` claim it and `desk: false` release it; `claim` and
`release` lines whose body says `desk: true` (or names the card "desk") count the same.
  {holder, since, claims: [{actor, at, live}], collision}
The earliest live claim holds it; two live claims are a collision, and the first keeps it.

Cost, from the proxy's `route` lines: tokens (`tokens`, else tokens_in + tokens_out) per body (the
route line's `body` field) AND per session (its `conversation`; rows {session, body, tokens, first,
last}), and per model, for the day and for the week; `unattributed` for lines with no body, never
spread by guess; `route_lines`; `money` {by_body, unit} only when route lines carry a price.
`ceiling` is {day_tokens, seven_day_pct, five_hour_pct, set_by} from the person's newest live
delegation that names one, else null. `closeout` is {at, at_rest, by} from the prime's last `body`
line with `closeout: true`, else null. Per body also: reviewed_at, delegation_live, lines_30m and
lines_1h (its own lines in the last half hour and hour). `limits()` (called by the engine, not the
fold) reads the machine's usage status file, when present, for the five-hour and seven-day
used percentages and their reset times.

Wakes. A wake body is a body named `heartbeat` (heartbeat.py writes two `body` lines per wake, working
then done, task = the wake's reason) or one whose task begins `wake:` (an agent recording its own wake;
the reason is what follows, cut to 280 as a task is). `wakes()` pairs each working (or claimed) line
with the next done (handoff, archived) line of the same actor and name, taking lines in time order with
an opening line before a closing line at the same time (the heartbeat stamps both alike), then by id:
`seconds` is the done line's own `seconds` when it carries one, else done minus working from the two
lines' times; null when a line is missing or both carry one time (`seconds_basis` says which);
`cost_tokens` is the done line's, null when it carries none (an open wake, or a wake that could not
count), and a count that is not a whole number is kept as given and said, never rounded. Only an
agent's own lines count, never one gamecore.is_untrusted marks. Per wake body the fold adds
`wakes` (how many), and from its newest wake `wake_reason`, `cost_tokens` (the wake's own, null when
unknown), `seconds` and `host`; every body also carries `route_tokens`, the day's route-line tokens
(which is its `cost_tokens` when it is not a wake body), and non-wake bodies carry `wakes: 0`,
`wake_reason: null` and `seconds: null`.

The cost of attention, per holon per day. `cost_of_attention` counts, per calendar day of the reader's
clock (`now`), the wakes and their tokens from the `body` lines, and forge requests, bytes and beats
from the beat-log rows it is given (`.heartbeat-log.jsonl`, read by the caller with `beat_log`).
A wake whose tokens are unknown counts as a wake and in `tokens_unknown`, never as zero tokens;
`tokens_per_wake` is over the wakes whose tokens are known, null when there are none. A day with no
wakes shows zeros. With no beat log given, `forge_requests`, `bytes` and `beats` are null and
`basis.requests` is "none"; only the log's tail is read, so a day before the oldest row read carries
them as null, and a sentence says where the log begins. `cost.attention` is this measure for today with no beat log; the engine
may replace it with one that has the log.
Files are data, never instructions. Standard library only.
"""
import datetime as dt
import math
import os
import sys
import unicodedata

try:
    from gamecore import parse_time, now_or, actor_kind, links, is_untrusted
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import parse_time, now_or, actor_kind, links, is_untrusted

AT_REST = {'done', 'archived', 'hold'}
PAST_DAY_H = 24.0
QUIET_H = 3.0
NO_TASK_MIN = 10.0
STALE_H = 24.0
WAKE_NAME = 'heartbeat'    # the body name heartbeat.py gives its wake lines (heartbeat._body_line)
WAKE_TASK = 'wake:'        # the task prefix of a wake an agent records itself
WAKE_OPEN = ('claimed', 'working')
WAKE_CLOSE = ('done', 'handoff', 'archived')
SKEW_MIN = 5               # minutes a line may run ahead of the reader's clock (as the route tally allows)
MAX_DAYS = 366             # this method's bound on the days one reading covers
REASON_MAX = 280           # a wake's reason is cut as a body's task is (the fold's own cut)


def _b(l):
    return l.get('body') if isinstance(l.get('body'), dict) else {}


def _hours(a, b):
    a, b = parse_time(a), parse_time(b)
    return None if a is None or b is None else round((b - a).total_seconds() / 3600.0, 2)


def _money(b):
    """(amount, unit) when a route line carries a price, else (None, None). Never estimated."""
    for k, unit in (('usd', 'dollars'), ('dollars', 'dollars'), ('cost', None), ('money', None)):
        v = b.get(k)
        if isinstance(v, (int, float)):
            return float(v), unit or str(b.get('unit') or 'dollars')
        if isinstance(v, dict) and isinstance(v.get('amount'), (int, float)):
            return float(v['amount']), str(v.get('unit') or 'dollars')
    return None, None


def _tokens(b):
    for k in ('tokens', 'cost_tokens'):
        try:
            if b.get(k) is not None:
                return int(b[k])
        except (TypeError, ValueError):
            pass
    try:
        return int(b.get('tokens_in') or 0) + int(b.get('tokens_out') or 0)
    except (TypeError, ValueError):
        return 0


def fold(lines, now=None, live=None):
    t = now_or(now)
    ls = sorted((l for l in _list(lines) if isinstance(l, dict) and l.get('id')), key=lambda l: str(l.get('ts') or ''))
    affirmed = {}
    for l in ls:
        if l.get('type') == 'affirm' and actor_kind(l.get('actor')) == 'agent':
            ag = _b(l).get('agent')
            if isinstance(ag, str):
                affirmed.setdefault(ag, l.get('actor'))
    names_by_actor = {}
    bodies = {}
    for l in ls:
        if l.get('type') != 'body':
            continue
        b = _b(l)
        name = str(b.get('name') or l.get('actor') or '')
        if not name:
            continue
        a = l.get('actor')
        known = bodies.get(name)
        if known is not None and known['actor'] != a:
            # another actor's line naming this body: only the prime's archive of its own clone counts
            if b.get('state') == 'archived' and affirmed.get(known['actor']) == a:
                known['state'] = 'archived'; known['newest_line'] = l.get('ts'); known['archived_by'] = a
            continue
        if known is None:
            names_by_actor[a] = name
            known = bodies[name] = {
                'name': name, 'actor': a, 'for': l.get('for'), 'holon': l.get('holon') or l.get('_held_in'),
                'kind': 'clone' if a in affirmed else 'prime', 'of': affirmed.get(a), 'state': None,
                'task': None, 'first_word': None, 'brief': None, 'host': None, 'claimed_at': l.get('ts'),
                'newest_line': None, 'review_min': None, 'handoff': None, 'reviewed': None, 'reviewed_at': None,
                'asks_yes': True, 'delegation_live': False, 'lines_30m': 0, 'lines_1h': 0,
                'cost_tokens': 0, 'declared_tokens': None, 'readers': 0, 'affirmed_by': affirmed.get(a),
                'age_hours': None, 'flags': []}
        st = b.get('state')
        if st:
            known['state'] = st
        if b.get('task'):
            known['task'] = str(b['task'])[:280]
            known['first_word'] = known['first_word'] or str(b['task']).split('.')[0][:80]
        for k in ('brief', 'host'):
            if b.get(k):
                known[k] = b[k]
        if b.get('review_min') is not None:
            known['review_min'] = b.get('review_min')
        if b.get('asks_yes') is not None:
            known['asks_yes'] = bool(b.get('asks_yes'))
        if b.get('cost_tokens') is not None:
            known['declared_tokens'] = _tokens(b)
        if st == 'handoff' or (st == 'done' and _positive(b.get('review_min')) and not known['handoff']):
            known['handoff'] = l['id']
        known['newest_line'] = l.get('ts')
    handoffs = {v['handoff']: v for v in bodies.values() if v['handoff']}
    for l in ls:
        if l.get('type') in ('witness', 'discern') and actor_kind(l.get('actor')) == 'person' \
                and l.get('actor') == l.get('for') and l.get('reason') != 'untrusted':
            named = set(links(l, 'witnesses')) | set(links(l, 'answers')) | set(links(l, 'anchored_to'))
            named |= {_b(l).get('handoff')} if _b(l).get('handoff') else set()
            for h in named & set(handoffs):
                if not handoffs[h]['reviewed']:
                    handoffs[h]['reviewed'], handoffs[h]['reviewed_at'] = l['id'], l.get('ts')

    # cost, from route lines: per body AND per session (the route's `conversation`), and per model
    day = t.date().isoformat()
    week0 = t - dt.timedelta(days=7)

    def tally():
        return {'tokens': 0, 'by_body': {}, 'by_session': {}, 'by_model': {}, 'unattributed': 0, 'lines': 0,
                'as_of': None, '_money': {}, '_unit': None}
    day_t, week_t, readers = tally(), tally(), {}
    for l in ls:
        if l.get('type') != 'route':
            continue
        lt = parse_time(l.get('ts'))
        if lt is None or lt < week0 or lt > t + dt.timedelta(minutes=5):
            continue
        b = _b(l)
        tok = _tokens(b)
        who = b.get('body') if isinstance(b.get('body'), str) and b.get('body') else None
        sess = b.get('conversation') if isinstance(b.get('conversation'), str) and b.get('conversation') else None
        m = str(b.get('model') or '(no model)')
        buckets = [week_t] + ([day_t] if lt.astimezone(t.tzinfo).date().isoformat() == day else [])
        for tl in buckets:
            tl['tokens'] += tok; tl['lines'] += 1; tl['as_of'] = l.get('ts')
            tl['by_model'][m] = tl['by_model'].get(m, 0) + tok
            if who:
                tl['by_body'][who] = tl['by_body'].get(who, 0) + tok
            else:
                tl['unattributed'] += tok
            key = sess or '(no session)'
            row = tl['by_session'].setdefault(key, {'session': key, 'body': who, 'tokens': 0,
                                                    'first': l.get('ts'), 'last': l.get('ts')})
            row['tokens'] += tok
            row['body'] = row['body'] or who
            row['last'] = l.get('ts')
            money, unit = _money(b)
            if money is not None and who:
                tl['_money'][who] = round(tl['_money'].get(who, 0.0) + money, 4)
                tl['_unit'] = tl['_unit'] or unit
        if who and b.get('turn'):
            readers.setdefault(who, set()).add(b['turn'])
    by_body = day_t['by_body']
    seen_wakes = wakes(ls, t)
    for v in bodies.values():
        v['cost_tokens'] = v['route_tokens'] = sum(by_body.get(k, 0) for k in {v['actor'], v['name']} if k)
        mine_w = [w for w in seen_wakes if w['actor'] == v['actor'] and w['name'] == v['name']]
        v['wakes'], v['wake_reason'], v['seconds'], v['seconds_basis'] = len(mine_w), None, None, None
        if mine_w:
            last = mine_w[-1]
            v['wake_reason'], v['cost_tokens'], v['seconds'] = last['reason'], last['cost_tokens'], last['seconds']
            v['seconds_basis'] = last['seconds_basis']
            v['host'] = last['host'] or v['host']
        v['readers'] = len(readers.get(v['actor'], set()) | readers.get(v['name'], set()))
        v['age_hours'] = _hours(v['claimed_at'], t)
        mine = [parse_time(l.get('ts')) for l in ls if l.get('actor') == v['actor']]
        v['lines_30m'] = sum(1 for x in mine if x is not None and t - dt.timedelta(minutes=30) < x <= t)
        v['lines_1h'] = sum(1 for x in mine if x is not None and t - dt.timedelta(hours=1) < x <= t)
        v['delegation_live'] = any(l.get('type') == 'delegate' and _b(l).get('to') in (v['actor'], v['of'])
                                   and actor_kind(l.get('actor')) == 'person'
                                   and (parse_time(_b(l).get('until')) is None or parse_time(_b(l).get('until')) >= t)
                                   and not any(r.get('type') == 'revoke' and (_b(r).get('delegation') == l.get('id')
                                                                              or l.get('id') in links(r, 'anchored_to'))
                                               for r in ls)
                                   for l in ls)
        quiet = _hours(v['newest_line'], t)
        flags = []
        if v['state'] not in AT_REST:
            if v['age_hours'] is not None and v['age_hours'] > PAST_DAY_H:
                flags.append('past_day')
            if v['state'] in ('claimed', 'working') and quiet is not None and quiet > QUIET_H:
                flags.append('quiet')
            if not v['task'] and v['age_hours'] is not None and v['age_hours'] * 60 > NO_TASK_MIN:
                flags.append('no_task')
            gone = ((live or {}).get(v['actor']) or {}).get('process') == 'gone'
            if gone or (quiet is not None and quiet > STALE_H):
                flags.append('stale')
                v['state_line'] = v['state']
                v['state'] = 'stale'
        v['flags'] = flags

    # the desk
    claims, holding = [], {}
    for l in ls:
        b = _b(l)
        typ = l.get('type')
        is_desk = (typ == 'body' and b.get('desk') is not None) or \
            (typ in ('claim', 'release') and (b.get('desk') is True or b.get('card') == 'desk'))
        if not is_desk:
            continue
        a = l.get('actor')
        on = (b.get('desk') is True) if typ == 'body' else (typ == 'claim')
        if on and a not in holding:
            holding[a] = l.get('ts')
        elif not on:
            holding.pop(a, None)
        claims.append({'actor': a, 'at': l.get('ts'), 'on': on})
    live_claims = sorted(holding.items(), key=lambda kv: str(kv[1] or ''))
    desk = {'holder': live_claims[0][0] if live_claims else None,
            'since': live_claims[0][1] if live_claims else None,
            'claims': [{'actor': a, 'at': at, 'live': True} for a, at in live_claims] +
                      [{'actor': c['actor'], 'at': c['at'], 'live': False} for c in claims
                       if c['on'] and (c['actor'], c['at']) not in set(live_claims)],
            'collision': len(live_claims) > 1}

    ceiling = None
    for l in ls:
        b = _b(l)
        if l.get('type') == 'delegate' and actor_kind(l.get('actor')) == 'person' and l.get('actor') == l.get('for'):
            until = parse_time(b.get('until'))
            if (until is None or until >= t) and any(b.get(k) is not None for k in
                                                     ('ceiling', 'ceiling_pct', 'seven_day_pct', 'five_hour_pct')):
                c = b.get('ceiling')
                ceiling = {'day_tokens': c if isinstance(c, (int, float)) else (c or {}).get('day_tokens') if isinstance(c, dict) else None,
                           'seven_day_pct': b.get('seven_day_pct', b.get('ceiling_pct')),
                           'five_hour_pct': b.get('five_hour_pct'), 'set_by': l.get('actor')}

    def shape(tl, **extra):
        out = {k: v for k, v in tl.items() if not k.startswith('_')}
        out['by_session'] = sorted(tl['by_session'].values(), key=lambda r: (str(r['first'] or ''), r['session']))
        out['route_lines'] = tl['lines']
        out['money'] = {'by_body': tl['_money'], 'unit': tl['_unit'] or 'dollars'} if tl['_money'] else None
        out.update(extra)
        return out
    day_s = shape(day_t, date=day)
    cost = {'by_body': day_s['by_body'], 'by_session': day_s['by_session'], 'by_model': day_s['by_model'],
            'day': day_s, 'week': shape(week_t, **{'from': week0.date().isoformat()}),
            'ceiling': ceiling, 'limits': None}
    closeout = None
    for l in ls:
        if l.get('type') == 'body' and _b(l).get('closeout') is True and actor_kind(l.get('actor')) == 'agent':
            at = l.get('ts')
            rest = all(v['state'] in AT_REST for v in bodies.values() if v['actor'] != l.get('actor'))
            closeout = {'at': at, 'at_rest': rest, 'by': l.get('actor')}
    out = sorted(bodies.values(), key=lambda v: (v['kind'] != 'prime', str(v['claimed_at'] or ''), v['name']))
    cost['attention'] = cost_of_attention(ls, out, None, t)
    return {'bodies': out, 'desk': desk, 'cost': cost, 'closeout': closeout}


# ---------------------------------------------------------------- wakes and the cost of attention

def _list(v):
    return v if isinstance(v, (list, tuple)) else []


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def _count(v):
    """A count of requests or bytes: a non-negative whole number, else None. Never guessed."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v >= 0 else None
    if isinstance(v, float) and math.isfinite(v) and v >= 0 and v.is_integer():
        return int(v)
    return None


def _token_count(v):
    """A wake's token count as its done line says it: a whole number, or a non-negative float kept as
    given (never rounded) and flagged; else None, unknown."""
    if isinstance(v, bool):
        return None, False
    if isinstance(v, int):
        return (v, False) if v >= 0 else (None, False)
    if isinstance(v, float) and math.isfinite(v) and v >= 0:
        return (int(v), False) if v.is_integer() else (v, True)
    return None, False


def _secs(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0:
        return round(float(v), 3)
    return None


def _nfc(v):
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _wake_of(name, b):
    """(is a wake line, its reason, cut to REASON_MAX as a task is). The heartbeat's lines carry the
    reason as their task."""
    task = _nfc(b.get('task'))
    if task.lower().startswith(WAKE_TASK):
        return True, task[len(WAKE_TASK):].strip()[:REASON_MAX] or None
    if _nfc(name) == WAKE_NAME:
        return True, task[:REASON_MAX] or None
    return False, None


def _new_wake(l, name, reason, host):
    return {'name': name, 'actor': l.get('actor'), 'holon': l.get('holon') or l.get('_held_in'),
            'reason': reason, 'host': host, 'opened': None, 'closed': None, 'seconds': None,
            'seconds_basis': None, 'cost_tokens': None, 'tokens_whole': True, 'working': None, 'done': None}


def wakes(lines, now=None):
    """Every wake the `body` lines record, oldest first: a working line paired with the next done line
    of the same actor and name. Lines are taken in time order, an opening line before a closing line
    at the same time, then by id; so two lines stamped alike still pair. Pure; lines after `now`
    (beyond SKEW_MIN) are not yet read.

    seconds_basis says where `seconds` came from: "the done line" · "the two lines' times" ·
    "unknown: both lines carry one time" (no seconds of its own, so not measured) · "unknown: a line
    is missing"."""
    t = now_or(now)
    edge = t + dt.timedelta(minutes=SKEW_MIN)
    rows = []
    for l in _list(lines):
        if not isinstance(l, dict) or l.get('type') != 'body':
            continue
        if actor_kind(l.get('actor')) != 'agent' or is_untrusted(l):
            continue
        b = _b(l)
        name = str(b.get('name') or l.get('actor') or '')
        is_wake, reason = _wake_of(name, b)
        lt = parse_time(l.get('ts'))
        if not is_wake or lt is None or lt > edge:
            continue
        rows.append((lt, 0 if b.get('state') in WAKE_OPEN else 1, str(l.get('id') or ''), l, b, name, reason))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    open_, out = {}, []
    for lt, _o, _i, l, b, name, reason in rows:
        key = (l.get('actor'), name)
        host = _nfc(b.get('host')) or None
        st = b.get('state')
        if st in WAKE_OPEN:
            if key in open_:
                prev = open_.pop(key)               # opened again with no done line: its end is unknown
                prev['seconds_basis'] = 'unknown: a line is missing'
                out.append(prev)
            w = open_[key] = _new_wake(l, name, reason, host)
            w['opened'], w['working'], w['_at'] = l.get('ts'), l.get('id'), lt
        elif st in WAKE_CLOSE:
            w = open_.pop(key, None) or _new_wake(l, name, reason, host)
            w['closed'], w['done'] = l.get('ts'), l.get('id')
            w['reason'], w['host'] = reason or w['reason'], host or w['host']
            w['cost_tokens'], frac = _token_count(b.get('cost_tokens'))
            w['tokens_whole'] = not frac
            declared = _secs(b.get('seconds'))
            if declared is not None:
                w['seconds'], w['seconds_basis'] = declared, 'the done line'
            elif w.get('_at') is None:
                w['seconds_basis'] = 'unknown: a line is missing'
            else:
                s = (lt - w['_at']).total_seconds()
                if s > 0:
                    w['seconds'], w['seconds_basis'] = round(s, 3), "the two lines' times"
                else:
                    w['seconds_basis'] = 'unknown: both lines carry one time'
            out.append(w)
    for w in open_.values():
        w['seconds_basis'] = 'unknown: a line is missing'
        out.append(w)
    for w in out:
        w.pop('_at', None)
    return sorted(out, key=lambda w: (parse_time(w['opened'] or w['closed']), str(w['actor'] or ''), w['name'],
                                      str(w['working'] or w['done'] or '')))


def _day_row(date, with_log):
    z = 0 if with_log else None
    return {'date': date, 'wakes': 0, 'tokens': 0, 'tokens_unknown': 0, 'tokens_per_wake': None,
            'by_reason': {}, 'by_holon': {}, 'forge_requests': z, 'bytes': z, 'beats': z}


def _log_rows(pull_log):
    """(rows, oldest as_of read, or None, given): a beat log as a list of rows, or as beat_log returns it."""
    if isinstance(pull_log, dict):
        rows = _list(pull_log.get('rows'))
        return rows, parse_time(pull_log.get('from')), True
    if isinstance(pull_log, (list, tuple)):
        return pull_log, None, True
    return [], None, False


def cost_of_attention(lines, bodies=None, pull_log=None, now=None, days=1):
    """The cost of attention per holon per day: wakes and tokens from the `body` lines, forge requests,
    bytes and beats from the beat-log rows given (never read here). Pure and deterministic given `now`.

    `pull_log` is a list of beat-log rows, or what beat_log returns ({rows, from}). A day before the
    oldest row read carries null requests, bytes and beats, and a sentence says the log begins there."""
    t = now_or(now)
    tz = t.tzinfo
    edge = t + dt.timedelta(minutes=SKEW_MIN)
    n = int(days) if isinstance(days, (int, float)) and not isinstance(days, bool) and math.isfinite(days) else 1
    n = max(1, min(MAX_DAYS, n))
    today = t.date()
    log, log_from, with_log = _log_rows(pull_log)
    rows = {}
    for i in range(n - 1, -1, -1):
        d = (today - dt.timedelta(days=i)).isoformat()
        rows[d] = _day_row(d, with_log)
    unknown = fractional = one_time = 0
    for w in wakes(lines, t):
        at = parse_time(w['opened'] or w['closed'])
        r = rows.get(at.astimezone(tz).date().isoformat()) if at is not None else None
        if r is None:
            continue
        tok = w['cost_tokens']
        h = r['by_holon'].setdefault(w['holon'] or '(no holon)', {'wakes': 0, 'tokens': 0, 'tokens_unknown': 0})
        why = w['reason'] or '(no reason)'
        r['by_reason'][why] = r['by_reason'].get(why, 0) + 1
        for x in (r, h):
            x['wakes'] += 1
            if tok is None:
                x['tokens_unknown'] += 1
            else:
                x['tokens'] += tok
        unknown += 1 if tok is None else 0
        fractional += 0 if w['tokens_whole'] else 1
        one_time += 1 if w['seconds_basis'] == 'unknown: both lines carry one time' else 0
    oldest = log_from
    if with_log:
        for e in log:
            if not isinstance(e, dict):
                continue
            at = parse_time(e.get('as_of'))
            if at is None or at > edge:
                continue
            if log_from is None and (oldest is None or at < oldest):
                oldest = at
            if 'error' in e:
                continue
            r = rows.get(at.astimezone(tz).date().isoformat())
            if r is None:
                continue
            c = e.get('cost') if isinstance(e.get('cost'), dict) else {}
            r['beats'] += 1
            r['forge_requests'] += _count(c.get('requests')) or 0
            r['bytes'] += _count(c.get('bytes')) or 0
    before = 0
    if with_log and oldest is not None:
        first = oldest.astimezone(tz).date().isoformat()
        for d, r in rows.items():
            if d < first:
                r['forge_requests'] = r['bytes'] = r['beats'] = None
                before += 1
    for r in rows.values():
        known = r['wakes'] - r['tokens_unknown']
        r['tokens_per_wake'] = round(r['tokens'] / known, 1) if known else None
    per_day = [rows[d] for d in sorted(rows)]
    said = []
    if not any(r['wakes'] for r in per_day):
        said.append('no wake was recorded on %s' % ('this day' if n == 1 else 'these %d days' % n))
    if unknown:
        said.append('%d wake(s) carried no token count; each is counted as a wake and its tokens are unknown, '
                    'not zero' % unknown)
    if fractional:
        said.append('%d wake(s) carried a token count that is not a whole number; it is kept as given' % fractional)
    if one_time:
        said.append('%d wake(s) carry one time on both lines and no seconds of their own, so their seconds are '
                    'unknown' % one_time)
    if not with_log:
        said.append('no beat log was given, so forge requests, bytes and beats are not counted')
    elif before:
        said.append('the beat log read begins at %s, so requests, bytes and beats are not counted for the %d '
                    'day(s) before it' % (oldest.isoformat(timespec='seconds'), before))
    wake_bodies = [{k: b.get(k) for k in ('name', 'actor', 'holon', 'wakes', 'wake_reason', 'cost_tokens',
                                          'seconds', 'seconds_basis', 'host')}
                   for b in _list(bodies) if isinstance(b, dict) and _count(b.get('wakes'))]
    return {'per_day': per_day, 'today': dict(per_day[-1]), 'days': n,
            'basis': {'tokens': 'body lines', 'requests': 'the pull log' if with_log else 'none'},
            'as_of': t.isoformat(timespec='seconds'),
            'bodies': sorted(wake_bodies, key=lambda b: (str(b.get('actor') or ''), str(b.get('name') or ''))),
            'said': said}


def beat_log(home_dir):
    """The heartbeat's beat log (`.heartbeat-log.jsonl`) for cost_of_attention: {rows, from (the oldest
    as_of read, since only the log's tail is read), said}, or None when the heartbeat has not beaten in
    this home. The engine's read, never the fold's; heartbeat.py reads the file."""
    if not isinstance(home_dir, str) or not home_dir:
        return None
    try:
        import heartbeat
    except ImportError:
        return None
    try:
        rows, why = heartbeat._log_tail(home_dir)
    except (OSError, ValueError):
        return None
    if why and not rows:
        return None
    times = [(parse_time(r.get('as_of')), r.get('as_of')) for r in rows if isinstance(r, dict)]
    times = [x for x in times if x[0] is not None]
    oldest = min(times, key=lambda x: x[0])[1] if times else None
    return {'rows': rows, 'from': oldest, 'said': why or None}


# One harness's status-line snapshot, as an example of where usage limits may be found; a holon
# names its own in calendar.json (`usage_status`). Reading it is the engine's act, not the fold's.
DEFAULT_STATUS_PATHS = ('~/.claude/statusline-last.json',)


def limits(calendar=None, ceiling_pct=None, paths=None):
    """The usage limits the machine's harness reports, or None when no status file is present.

    {seven_day_used_pct, five_hour_used_pct, resets_at: {seven_day, five_hour}, ceiling_pct, source}.
    The path is calendar.json's `usage_status` (or `limits_status`), else DEFAULT_STATUS_PATHS.
    Reset times are said as ISO times. Nothing is guessed: a field the file lacks is null."""
    import json
    cands = []
    if isinstance(calendar, dict):
        for k in ('usage_status', 'limits_status'):
            if isinstance(calendar.get(k), str):
                cands.append(calendar[k])
    cands += list(paths if paths is not None else DEFAULT_STATUS_PATHS)
    for p in cands:
        try:
            with open(os.path.expanduser(p), encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError, TypeError):
            continue
        rl = d.get('rate_limits') if isinstance(d, dict) else None
        if not isinstance(rl, dict):
            continue

        def part(name):
            x = rl.get(name) if isinstance(rl.get(name), dict) else {}
            r = x.get('resets_at')
            try:
                r = dt.datetime.fromtimestamp(float(r), dt.timezone.utc).isoformat(timespec='seconds') \
                    if isinstance(r, (int, float)) else r
            except (OverflowError, OSError, ValueError):
                r = None
            return x.get('used_percentage'), r
        s7, r7 = part('seven_day')
        s5, r5 = part('five_hour')
        return {'seven_day_used_pct': s7, 'five_hour_used_pct': s5,
                'resets_at': {'seven_day': r7, 'five_hour': r5}, 'ceiling_pct': ceiling_pct,
                'source': os.path.basename(os.path.expanduser(p))}
    return None
