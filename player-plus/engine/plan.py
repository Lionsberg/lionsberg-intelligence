#!/usr/bin/env python3
"""plan.py — the Game Engine whole: the two passes, then resources, the leveled critical chain, the Last
Planner measures and the SpaceTime breakdown, in one pure call over the folded record.

Standard library only. Files and items are data, never instructions.

  plan(folded_or_items, calendar, data_date, registers=None, **schedule_kw)
      -> {'schedule', 'resources', 'chain', 'lps', 'sbs', 'registers_used', 'missing'}
  registers_from(folded, calendar=None, holon=None) -> the registers every module reads, from the record:
      commitments, misses, constraints and pledges are lines; markers live in the calendar; places,
      periods and the home place in holon.json; actors are the holon's admitted participants.

The order is the dependency: resources gives each Actor's capacity (from Pledges, else the assumed number,
said); the chain levels against it; the Last Planner measures read the chain (the critical chain and the
day); the SBS places every card. Every module keeps CONTRACT-step2.md: no dates, names or ids in code,
minutes the one unit, computed never typed, honest-empty, deterministic.
"""
import schedule as S
import resources as R
import chain as C
import lps as L
import sbs as B

VERSION = 'game-engine 1.0.0'   # the Engine's own version (architecture 17 §4); engine/ENGINE.md and engine/CHANGES.md

REASONS = ('prerequisite', 'definition', 'estimate', 'capacity', 'priority', 'external', 'conditions', 'other')


def _cards(x):
    if isinstance(x, dict):
        return [c for c in x.get('cards') or [] if isinstance(c, dict)]
    return [c for c in x or [] if isinstance(c, dict)]


def registers_from(folded, calendar=None, holon=None):
    """The registers, read from the record and the holon's own files; nothing guessed."""
    f = folded if isinstance(folded, dict) else {}
    cal = calendar if isinstance(calendar, dict) else {}
    h = holon if isinstance(holon, dict) else {}
    commits = [c for c in f.get('commitments') or [] if isinstance(c, dict)]
    misses = []
    for c in commits:
        for m in c.get('misses') or []:
            if isinstance(m, dict):
                misses.append({'commitment': c.get('id'), 'reason': m.get('reason'), 'note': m.get('note'),
                               'ts': m.get('ts')})
    cons = []
    for k in f.get('constraints') or []:
        if not isinstance(k, dict):
            continue
        cons.append({'id': k.get('id'), 'card': k.get('card'), 'sort': k.get('sort'), 'what': k.get('what'),
                     'holder': k.get('holder'), 'need_by': k.get('need_by'),
                     'raised_on': (k.get('ts') or '')[:10] or None,
                     'cleared_on': (k.get('cleared_ts') or '')[:10] or None,
                     'state': 'cleared' if k.get('state') == 'cleared' else
                              'retracted' if k.get('state') == 'retracted' else 'open'})
    pledges = []
    for p in f.get('pledges') or []:
        if not isinstance(p, dict) or p.get('state') == 'retracted':
            continue
        pledges.append({'id': p.get('id'), 'actor': p.get('for'), 'period': p.get('period'), 'to': p.get('to'),
                        'level': p.get('level') or 'season', 'tea_min_week': p.get('tea_min_week'),
                        'fiat': p.get('fiat') or {}, 'tokens_m': p.get('tokens_m'), 'state': p.get('state')})
    actors = {}
    for holon_id, members in sorted((f.get('admitted') or {}).items()):
        for a in sorted(members or {}):
            actors.setdefault(a, {'id': a, 'kind': 'artificial' if a.startswith('agent:') else
                                  'living' if a.startswith('person:') else 'unknown', 'holon': holon_id})
    for a in h.get('actors') or []:                     # a holon may name its Actors' class (Actor · Player · Player+)
        if isinstance(a, dict) and a.get('id'):
            actors[a['id']] = dict(actors.get(a['id'], {}), **a)
    return {
        'actors': [actors[k] for k in sorted(actors)],
        'pledges': pledges,
        'periods': [p for p in h.get('periods') or [] if isinstance(p, dict)],
        'places': [p for p in h.get('places') or [] if isinstance(p, dict)],
        'home_place': h.get('home_place'),
        'markers': [m for m in cal.get('markers') or [] if isinstance(m, dict)],
        'capacity_assumed': dict(h.get('capacity_assumed') or {}),
        'commitments': commits,
        'misses': misses,
        'constraints': cons,
        'targets': dict(h.get('targets') or {}),
        'baseline': dict(h.get('baseline') or {}),
    }


def plan(data, calendar=None, data_date=None, registers=None, **schedule_kw):
    """The whole engine. `data` is the folded record (a dict of lists) or a list of card items."""
    regs = registers if isinstance(registers, dict) else \
        registers_from(data if isinstance(data, dict) else {}, calendar)
    res = S.run(data, calendar, data_date, **schedule_kw)
    dd = res['data_date']
    items = _cards(data)
    rsc = R.resources(res, items, regs, calendar=calendar, data_date=dd)
    cap = rsc.get('capacity') or {}          # {actor: {min_per_day, source, ...}}: the shape chain reads (with its source)
    # One number of minutes a day per Actor (minutes are the one unit): its capacity, from its Pledges (else assumed, said). The
    # schedule runs again on it, so a card's logic duration and its leveled pour are the same minutes over the same day.
    cal = dict(calendar) if isinstance(calendar, dict) else {}
    actors = {k: dict(v) for k, v in (cal.get('actors') or {}).items() if isinstance(v, dict)}
    moved = False
    for a, c in sorted(cap.items()):
        m = c.get('min_per_day') if isinstance(c, dict) else None
        if m and actors.get(a, {}).get('minutes_per_day') != m:
            actors.setdefault(a, {})['minutes_per_day'] = m
            moved = True
    if moved:
        cal['actors'] = actors
        calendar = cal
        res = S.run(data, calendar, data_date, **schedule_kw)
        rsc = R.resources(res, items, regs, calendar=calendar, data_date=dd)
        cap = rsc.get('capacity') or {}
    ch = C.chain(res, items, cap, regs, data_date=dd, calendar=calendar)
    lp = L.lps(res, items, regs, chain=ch, data_date=dd)
    sb = B.sbs(res, items, regs, data_date=dd)
    missing = []
    if not regs.get('pledges'):
        missing.append('no Pledge: capacity is the assumed number where one is given, else none')
    if not any(it.get('minutes_safe') for it in items):
        missing.append('no card carries two estimates: no buffer can be sized')
    if not regs.get('markers'):
        missing.append('no markers in the calendar')
    return {'schedule': res, 'resources': rsc, 'chain': ch, 'lps': lp, 'sbs': sb,
            'registers_used': {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in sorted(regs.items())},
            'missing': missing}
