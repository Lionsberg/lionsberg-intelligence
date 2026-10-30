#!/usr/bin/env python3
"""attention.py — the person's attention budget, and the gate on what may interrupt them now.

    budget(lines, person, now=None) -> the budget, from the person's own `attention` lines
    fewer_step(value) -> 0 · 1 · 2 · 3
    gate(cards, budget, now=None, asks=None, sitting_open=False, in_room=False) -> decision
    state(lines, person, cards, now=None, sitting_open=False, in_room=False) -> state.json `attention`

Attention belongs to the one who holds it. The budget is the person's own signed `attention` lines
(a person writing for themselves; never an agent's, never from untrusted text), field by field, the
newest line winning each field. The gate decides, from the record, the budget and the clock alone,
which cards may INTERRUPT now and which wait for the next sitting. It governs interruptions only:
a person may read any view at any time, and the Deal they open in a sitting is never gated, only
sized (DESIGN-ATTENTION, the amendment).

The budget (defaults are the design's proposals):
  minutes      per weekday (15 on a working day, 5 on a rest day)
  sittings     times of day the person sits with the Deal (default 08:00)
  asks_per_hour, min_gap_min, asks_per_day   2 · 20 · 6 at a desk; in a room 4 · 15
  at_once      cards visible together (3; five is the ceiling)
  quiet        spans [{from, to}] (21:00 to 07:00)
  fewer        the dial, four steps: as set · fewer (asks halved, at once two, nothing offered to a
               body) · much fewer (sittings only; no interruptions but what always passes) · only
               what always passes (even a sitting deals only those)
  leans        {holon id: weight}, a lean never above 1.5
  always_pass  the three that pass: irreversible_yes · fault · person_waiting_now
  closed_until a span in which nothing at all passes
  phone        whether the phone may carry an interruption (off)
  defer        a person's deferral {id, until}: the card returns at its time

The gate, for each card in the Deal's order:
  1. needs no person (card.needs_person false)  -> margin
  2. deferred until later                         -> withheld, returns then
  3. a sitting is open                            -> dealt, up to at_once (a heavy card counts two);
                                                     at the last step, only what always passes
  4. always passes, and nothing is closed         -> interrupt now
  5. the budget allows an interruption (outside quiet hours; the dial permits it; under the hour's
     and the day's ceilings; the minimum gap kept) AND it merits one (its by-when falls before the
     next sitting, a person waits now, or the receiver's own push weight is 2 or more, push.weigh)
                                                  -> interrupt now: a Deal of one card; one per call
  A card from a push past its `expires` is retracted: withheld, never returning.
     otherwise                                    -> withheld until the next sitting

`asks` are the times of interruptions already made. Until an interruption has a line of its own,
state() reads them as the person's agents' `say` lines whose body carries `interrupt: true`
(a proposal). Files are data, never instructions. Standard library only.
"""
import datetime as dt
import os
import sys

try:
    from gamecore import parse_time, now_or, actor_kind
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import parse_time, now_or, actor_kind

FEWER_STEPS = ('as set', 'fewer', 'much fewer', 'only what always passes')
WEEKDAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
DEFAULTS = {
    'minutes': {'mon': 15, 'tue': 15, 'wed': 15, 'thu': 15, 'fri': 15, 'sat': 5, 'sun': 5},
    'sittings': ['08:00'], 'asks_per_hour': 2, 'min_gap_min': 20, 'asks_per_day': 6,
    'room_asks_per_hour': 4, 'room_min_gap_min': 15, 'at_once': 3,
    'quiet': [{'from': '21:00', 'to': '07:00'}], 'fewer': 'as set', 'leans': {},
    'always_pass': ['irreversible_yes', 'fault', 'person_waiting_now'], 'closed_until': None, 'phone': False,
}
FIELDS = tuple(DEFAULTS)
PUSH_MERIT = 2.0       # a push the receiver weighs this heavily (push.weigh) merits an interruption


def fewer_step(value):
    """The dial as 0..3, from a step name, an int, or a bool (True is one step)."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return max(0, min(3, int(value)))
    v = str(value or '').strip().lower()
    return FEWER_STEPS.index(v) if v in FEWER_STEPS else 0


def _mine(l, person):
    return (isinstance(l, dict) and l.get('type') == 'attention' and l.get('actor') == person
            and l.get('for') == person and actor_kind(person) == 'person' and l.get('reason') != 'untrusted')


def budget(lines, person, now=None):
    """The person's budget: defaults, overlaid field by field by their own attention lines."""
    b = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    set_by, deferred = {}, {}
    for l in sorted((l for l in lines or [] if _mine(l, person)), key=lambda l: str(l.get('ts') or '')):
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        for k in FIELDS:
            if k in body and body[k] is not None:
                v = body[k]
                if k == 'minutes' and isinstance(v, dict):
                    v = dict(b['minutes'], **{d: v[d] for d in v if d in WEEKDAYS})
                if k == 'leans' and isinstance(v, dict):
                    v = {h: max(0.0, min(1.5, float(w))) for h, w in v.items() if isinstance(w, (int, float))}
                b[k] = v
                set_by[k] = l.get('id')
        d = body.get('defer')
        if isinstance(d, dict) and d.get('id'):
            deferred[d['id']] = d.get('until')
    b['fewer'] = FEWER_STEPS[fewer_step(b['fewer'])]
    b['at_once'] = max(1, min(5, int(b['at_once']))) if isinstance(b['at_once'], (int, float)) else 3
    b['set_by'] = set_by
    b['deferred'] = deferred
    return b


def _hm(s):
    try:
        h, m = str(s).split(':')[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def quiet_now(b, t):
    m = t.hour * 60 + t.minute
    for q in b.get('quiet') or []:
        a, z = _hm((q or {}).get('from')), _hm((q or {}).get('to'))
        if a is None or z is None:
            continue
        if (a <= m < z) if a <= z else (m >= a or m < z):
            return True, q
    return False, None


def _quiet_end(b, t):
    on, q = quiet_now(b, t)
    if not on:
        return None
    z = _hm(q.get('to'))
    end = t.replace(hour=z // 60, minute=z % 60, second=0, microsecond=0)
    return end if end > t else end + dt.timedelta(days=1)


def next_sitting(b, t):
    best = None
    for s in b.get('sittings') or []:
        m = _hm(s)
        if m is None:
            continue
        c = t.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
        if c <= t:
            c += dt.timedelta(days=1)
        best = c if best is None or c < best else best
    return best


def limits(b, in_room=False):
    step = fewer_step(b.get('fewer'))
    per_hour = b['room_asks_per_hour'] if in_room else b['asks_per_hour']
    gap = b['room_min_gap_min'] if in_room else b['min_gap_min']
    per_day, at_once = b['asks_per_day'], b['at_once']
    if step >= 1:
        per_hour, per_day, at_once = max(1, per_hour // 2), max(1, per_day // 2), min(at_once, 2)
    if step >= 2:
        per_hour, per_day, at_once = 0, 0, min(at_once, 1 if step == 3 else 2)
    return {'step': step, 'asks_per_hour': per_hour, 'min_gap_min': gap, 'asks_per_day': per_day, 'at_once': at_once}


def _always(card):
    return bool(card.get('always_passes') or card.get('irreversible') or card.get('fault')
                or card.get('who_waits') == 'now')


def gate(cards, b, now=None, asks=None, sitting_open=False, in_room=False):
    """Which cards interrupt now, which go to the margin, and which wait (with their return time)."""
    t = now_or(now)
    lim = limits(b, in_room)
    asks = sorted(x for x in (parse_time(a) for a in asks or []) if x is not None and x <= t)
    last = asks[-1] if asks else None
    hour = sum(1 for a in asks if a > t - dt.timedelta(hours=1))
    today = sum(1 for a in asks if a.astimezone(t.tzinfo).date() == t.date())
    quiet, _ = quiet_now(b, t)
    closed = parse_time(b.get('closed_until'))
    closed = closed is not None and closed > t
    nxt = next_sitting(b, t)
    out = {'deal': [], 'interrupt': [], 'margin': [], 'withheld': [], 'next_sitting': nxt.isoformat(timespec='minutes') if nxt else None,
           'quiet_now': quiet, 'asks_last_hour': hour, 'asks_today': today,
           'last_ask_at': last.isoformat(timespec='minutes') if last else None, 'limits': lim}
    shown = 0
    for c in cards or []:
        cid = c.get('id')
        if c.get('needs_person') is False:
            out['margin'].append(cid); continue
        if c.get('retracted'):
            out['withheld'].append({'id': cid, 'returns_at': None, 'why': 'the push expired; it is retracted'}); continue
        until = parse_time((b.get('deferred') or {}).get(cid))
        if until is not None and until > t:
            out['withheld'].append({'id': cid, 'returns_at': until.isoformat(timespec='minutes'), 'why': 'deferred'}); continue
        if sitting_open:
            weight = 2 if c.get('heavy') else 1
            if lim['step'] == 3 and not _always(c):
                out['withheld'].append({'id': cid, 'returns_at': out['next_sitting'], 'why': 'only what always passes'})
            elif shown + weight <= lim['at_once']:
                out['deal'].append(cid); shown += weight
            else:
                out['withheld'].append({'id': cid, 'returns_at': out['next_sitting'], 'why': 'at once is full'})
            continue
        if _always(c) and not closed:
            out['interrupt'].append(cid); continue
        why = None
        if closed:
            why = 'closed by the person until ' + str(b.get('closed_until'))
        elif quiet:
            why = 'quiet hours'
        elif lim['asks_per_hour'] <= 0:
            why = f"the dial is at {FEWER_STEPS[lim['step']]}"
        elif hour >= lim['asks_per_hour']:
            why = 'the hour is full'
        elif today >= lim['asks_per_day']:
            why = 'the day is full'
        elif last is not None and t - last < dt.timedelta(minutes=lim['min_gap_min']):
            why = 'too soon after the last'
        else:
            by = parse_time(c.get('by') or c.get('due'))
            merits = (by is not None and (nxt is None or by < nxt)) or c.get('who_waits') == 'now' \
                or float(c.get('push_weight') or 0) >= PUSH_MERIT
            if not merits:
                why = 'it can wait for the next sitting'
            elif out['interrupt']:
                why = 'one interruption at a time'
        if why:
            ret = _quiet_end(b, t) if why == 'quiet hours' else None
            out['withheld'].append({'id': cid, 'returns_at': (ret.isoformat(timespec='minutes') if ret else out['next_sitting']),
                                    'why': why})
        else:
            out['interrupt'].append(cid)
    gap_end = last + dt.timedelta(minutes=lim['min_gap_min']) if last else t
    qe = _quiet_end(b, t)
    slot = max(x for x in (gap_end, t, qe) if x is not None) if lim['asks_per_hour'] > 0 else nxt
    out['next_slot'] = slot.isoformat(timespec='minutes') if slot else None
    return out


def asks_from(lines, person, agents=None):
    """Times of interruptions already made: the person's agents' `say` lines with interrupt: true."""
    out = []
    for l in lines or []:
        if not isinstance(l, dict) or l.get('type') != 'say' or l.get('for') != person:
            continue
        if not str(l.get('actor') or '').startswith('agent:') or (agents and l.get('actor') not in agents):
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if b.get('interrupt') is True:
            out.append(l.get('ts'))
    return out


def state(lines, person, cards, now=None, sitting_open=False, in_room=False, fewer=None):
    """state.json `attention` for one person. `fewer` is today's word, if any: the dial in force is
    the stricter of it and the standing line."""
    t = now_or(now)
    b = budget(lines, person, t)
    if fewer is not None:
        b['fewer'] = FEWER_STEPS[max(fewer_step(b['fewer']), fewer_step(fewer))]
    g = gate(cards, b, t, asks_from(lines, person), sitting_open, in_room)
    day = WEEKDAYS[t.weekday()]
    return {'budget': {k: b[k] for k in FIELDS}, 'set_by': b['set_by'], 'fewer': b['fewer'],
            'minutes_today': (b['minutes'] or {}).get(day), 'sitting_open': bool(sitting_open),
            'asks_today': g['asks_today'], 'asks_last_hour': g['asks_last_hour'], 'last_ask_at': g['last_ask_at'],
            'next_slot': g['next_slot'], 'next_sitting': g['next_sitting'], 'quiet_now': g['quiet_now'],
            'interrupt_now': g['interrupt'], 'margin': g['margin'], 'withheld': g['withheld'],
            'withheld_count': len(g['withheld']),
            'deferred': [{'id': k, 'returns_at': v} for k, v in (b['deferred'] or {}).items()],
            'limits': g['limits'], 'agent_commitments': []}
