#!/usr/bin/env python3
"""bodies.py — an agent's bodies (the prime and its clones), the desk, and what each body cost.

    fold(lines, now=None, live=None) -> {"bodies": [...], "desk": {...}, "cost": {...}}

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

  handoff   the id of its `handoff` line (or of a `done` line that carries review_min)
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
Files are data, never instructions. Standard library only.
"""
import datetime as dt
import os
import sys

try:
    from gamecore import parse_time, now_or, actor_kind, links
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import parse_time, now_or, actor_kind, links

AT_REST = {'done', 'archived', 'hold'}
PAST_DAY_H = 24.0
QUIET_H = 3.0
NO_TASK_MIN = 10.0
STALE_H = 24.0


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
    ls = sorted((l for l in lines or [] if isinstance(l, dict) and l.get('id')), key=lambda l: str(l.get('ts') or ''))
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
        if st == 'handoff' or (st == 'done' and b.get('review_min') is not None and not known['handoff']):
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
    for v in bodies.values():
        v['cost_tokens'] = sum(by_body.get(k, 0) for k in {v['actor'], v['name']} if k)
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
    return {'bodies': out, 'desk': desk, 'cost': cost, 'closeout': closeout}


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
