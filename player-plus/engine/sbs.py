#!/usr/bin/env python3
"""sbs.py — the SpaceTime Breakdown Structure: where and when each card lands.

Standard library only. A pure function over the schedule's result, the folded items and the
registers; it reads no file, no clock and no global, and returns a new JSON-ready dict.

The Work Breakdown says what the work is; the SpaceTime Breakdown says where and when it lands.
It has two holarchies. SPACE is places within places (`registers['places']`: {id, name, within}).
TIME is periods within periods (`registers['periods']`: {id, name, from, to, within}, ISO dates,
both ends held). Each is checked, never repaired: exactly one root, no loop, every `within` held,
and for time every span readable, ordered and inside the span of its `within`. A defect is
listed; nothing is fixed by guess.

PLACEMENT (per scheduled card and unit)
  where: the card's own `where`; else the `where` of its nearest enclosing unit (up the
    `within` chain); else `registers['home_place']`; else None, said as 'unplaced'.
    A place is location, never identity: it says where the work lands, never who carries it.
  when: the smallest period (fewest days; ties by `from`, then id) whose [from, to] holds the
    card's finish date. The finish date is the last day of work (`last_day`: the schedule's
    `finish` is the MORNING after the last day, see schedule.py, THE TIME AXIS), else `finish`;
    for a done card, its actual finish. A card's period is never typed: it is computed, so it
    moves with the plan.
  week: the ISO Monday of that date.

THE DEFAULT TIME (no `periods` register)
  Derived from the data alone: the ISO years and the ISO weeks that hold the data date or any
  card's finish date, and, when more than one ISO year is held, one root spanning them all. No
  season or marker date lives in this code; those belong in the register.

THE MATRIX (where x when)
  Every open card (not complete; units and summaries left out, since they hold cards already
  counted): per (where, when), the cards, how many are open, their minutes, the least total
  float and how many are critical.

PAPER EXAMPLE (tests/test_sbs.py checks it)
  Places: Earth > Valley > Site. Unit U (where Valley) holds A (where Site) and B (no where);
  C stands alone; home is Earth. Then A is at Site (own), B at Valley (its unit's), C at Earth
  (home). With periods Y (the year) > W1, W2 (weeks), a card whose last day falls in W1 is
  placed in W1, never Y: the smallest period that holds it.
"""
import datetime as dt

ENGINE = 'sbs.py'
NONE_WORDS = ('', '—', '-', '–')
OPEN_EXCLUDED_TYPES = ('unit', 'summary')   # they hold cards counted already
COMPLETE = 'complete'                       # schedule.py's status for done work


# ---------------------------------------------------------------- small readers (null-guarded)

def _field(item, key):
    if not isinstance(item, dict):
        return None
    v = item.get(key)
    if v is None and isinstance(item.get('body'), dict):
        v = item['body'].get(key)
    return v


def _id(x):
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        return None
    s = str(x).strip()
    return None if s in NONE_WORDS else s


def _date(x):
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    if not isinstance(x, str) or not x.strip():
        return None
    try:
        return dt.date.fromisoformat(x.strip()[:10])
    except ValueError:
        return None


def _num(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    f = float(x)
    return None if f != f or f in (float('inf'), float('-inf')) else f


def _out(x):
    if x is None:
        return None
    return int(round(x)) if abs(x - round(x)) < 1e-9 else round(x, 3)


def _within_of(item):
    """The unit an item lies within: `links.within`, else the top-level `within` (first id)."""
    if not isinstance(item, dict):
        return None
    for src in (item.get('links'), item):
        if not isinstance(src, dict):
            continue
        v = src.get('within')
        if isinstance(v, (list, tuple)):
            v = next((x for x in v if _id(x)), None)
        if _id(v):
            return _id(v)
    return None


def _monday(d):
    return (d - dt.timedelta(days=d.weekday())).isoformat() if d else None


# ---------------------------------------------------------------- the holarchy check

def check_holarchy(nodes, kind, dated=False):
    """Check a holarchy (a list of {id, name, within[, from, to]}) and return it with its defects.
    Nothing is repaired: a node held twice keeps its first form, and every defect is listed."""
    defects, held, order = [], {}, []
    for n in nodes if isinstance(nodes, list) else []:
        nid = _id(n.get('id')) if isinstance(n, dict) else None
        if nid is None:
            defects.append({'id': None, 'defect': f'a {kind} without an id'})
            continue
        if nid in held:
            defects.append({'id': nid, 'defect': 'held twice; the first is read'})
            continue
        held[nid] = n
        order.append(nid)
    within = {i: _id(held[i].get('within')) for i in order}
    for i in order:
        w = within[i]
        if w is not None and w not in held:
            defects.append({'id': i, 'defect': 'within not held', 'within': w})
    # loops: walk each chain; a revisit inside the walk is a loop
    in_loop, loops = set(), []
    for i in sorted(order):
        path, cur = [], i
        while cur is not None and cur in held and cur not in path:
            if cur in in_loop:
                break
            path.append(cur)
            cur = within[cur]
        if cur is not None and cur in path:
            members = sorted(path[path.index(cur):])
            if not in_loop.intersection(members):
                loops.append(members)
            in_loop.update(members)
    for members in loops:
        defects.append({'id': members[0], 'defect': 'loop', 'loop': members})
    roots = sorted(i for i in order if within[i] is None)
    if len(roots) != 1:
        defects.append({'id': None, 'defect': 'no root' if not roots else 'more than one root', 'roots': roots})

    def depth(i):
        d, cur, seen = 0, i, set()
        while cur is not None:
            if cur not in held or cur in seen or cur in in_loop:
                return None
            seen.add(cur)
            cur = within[cur]
            d += 1
        return d

    out = []
    span = {}
    for i in order:
        n = held[i]
        row = {'id': i, 'name': n.get('name') if isinstance(n.get('name'), str) else None,
               'within': within[i], 'depth': depth(i)}
        if dated:
            a, b = _date(n.get('from')), _date(n.get('to'))
            row['from'] = a.isoformat() if a else None
            row['to'] = b.isoformat() if b else None
            if a is None or b is None:
                defects.append({'id': i, 'defect': 'from or to is not an ISO date'})
            elif a > b:
                defects.append({'id': i, 'defect': 'from after to'})
            else:
                span[i] = (a, b)
        out.append(row)
    if dated:
        for i in order:
            w = within[i]
            if i in span and w in span and not (span[w][0] <= span[i][0] and span[i][1] <= span[w][1]):
                defects.append({'id': i, 'defect': 'outside the span of its within', 'within': w})
        out.sort(key=lambda r: (r['from'] or '', r['to'] or '', r['id']))
    else:
        out.sort(key=lambda r: r['id'])
    defects.sort(key=lambda d: (d['id'] is None, d['id'] or '', d['defect']))
    return {'nodes': out, 'roots': roots, 'defects': defects, 'ok': not defects}, span


def default_periods(dates):
    """The ISO years and ISO weeks that hold the given dates; one root over them when more than
    one year is held. Built from the dates alone."""
    dates = sorted({d for d in dates if d})
    years = sorted({d.isocalendar()[0] for d in dates})
    weeks = sorted({d.isocalendar()[:2] for d in dates})
    out = []
    root = None
    if len(years) > 1:
        root = f'{years[0]}/{years[-1]}'
        out.append({'id': root, 'name': f'the ISO years {years[0]} to {years[-1]}',
                    'from': dt.date.fromisocalendar(years[0], 1, 1).isoformat(),
                    'to': (dt.date.fromisocalendar(years[-1] + 1, 1, 1) - dt.timedelta(days=1)).isoformat(),
                    'within': None})
    for y in years:
        out.append({'id': str(y), 'name': f'the ISO year {y}',
                    'from': dt.date.fromisocalendar(y, 1, 1).isoformat(),
                    'to': (dt.date.fromisocalendar(y + 1, 1, 1) - dt.timedelta(days=1)).isoformat(),
                    'within': root})
    for y, w in weeks:
        mon = dt.date.fromisocalendar(y, w, 1)
        out.append({'id': f'{y}-W{w:02d}', 'name': f'the ISO week {y}-W{w:02d}',
                    'from': mon.isoformat(), 'to': (mon + dt.timedelta(days=6)).isoformat(),
                    'within': str(y)})
    return out


# ---------------------------------------------------------------- placement

def _finish_date(row, item):
    """(date, basis) a card is placed in time by."""
    if row.get('status') == COMPLETE:
        d = _date(row.get('actual_finish')) or _date(_field(item, 'actual_finish'))
        return (d, 'actual finish') if d else (None, 'missing: done with no actual finish')
    d = _date(row.get('last_day'))
    if d:
        return d, 'last day of work'
    d = _date(row.get('finish'))
    if d:
        return d, 'finish'
    return None, 'missing: no computed finish'


def _smallest(spans, d):
    best = None
    for pid, (a, b) in spans.items():
        if a <= d <= b:
            k = ((b - a).days, a, pid)
            if best is None or k < best[0]:
                best = (k, pid)
    return best[1] if best else None


def sbs(res, items, registers=None, data_date=None):
    """The SpaceTime Breakdown: {space, time, placement, matrix, basis}. See the module docstring."""
    res = res if isinstance(res, dict) else {}
    reg = registers if isinstance(registers, dict) else {}
    rows = [r for r in (res.get('items') or []) if isinstance(r, dict) and _id(r.get('id'))]
    by_row = {str(r['id']): r for r in rows}
    by_item = {}
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and _id(it.get('id')) is not None:
            by_item.setdefault(_id(it.get('id')), it)

    # space
    places = reg.get('places') if isinstance(reg.get('places'), list) else []
    space, _ = check_holarchy(places, 'place')
    space['basis'] = 'register' if places else 'missing: no places register'
    held_places = {n['id'] for n in space['nodes']}
    home = _id(reg.get('home_place'))
    space['home_place'] = home
    if home is not None and places and home not in held_places:
        space['defects'].append({'id': home, 'defect': 'home place not held'})
        space['ok'] = False

    # where, and the date each card is placed in time by
    placement, unheld = {}, []
    dates = {}
    for cid in sorted(by_row):
        row, item = by_row[cid], by_item.get(cid)
        where, basis, frm = _id(_field(item, 'where')), 'own', None
        if where is None:
            cur, seen = _id(row.get('within')) or _within_of(item), {cid}
            while cur is not None and cur not in seen:
                seen.add(cur)
                w = _id(_field(by_item.get(cur), 'where'))
                if w is not None:
                    where, basis, frm = w, 'unit', cur
                    break
                cur = _id(by_row[cur].get('within')) if cur in by_row else _within_of(by_item.get(cur))
        if where is None and home is not None:
            where, basis = home, 'home'
        if where is None:
            basis = 'unplaced'
        if where is not None and places and where not in held_places:
            unheld.append({'card': cid, 'where': where})
        d, when_basis = _finish_date(row, item)
        dates[cid] = d
        placement[cid] = {'where': where, 'where_basis': basis, 'where_from': frm,
                          'when_date': d.isoformat() if d else None, 'when_basis': when_basis,
                          'week': _monday(d)}
    space['unheld_places'] = unheld

    # time
    dd = _date(data_date) or _date(res.get('data_date'))
    periods = reg.get('periods') if isinstance(reg.get('periods'), list) else []
    if periods:
        time_basis = 'register'
    else:
        periods = default_periods([dd] + list(dates.values()))
        time_basis = ('default: the ISO years and ISO weeks holding the data date and the cards\' '
                      'finish dates' if dd else
                      'default: the ISO years and ISO weeks holding the cards\' finish dates (no data date)')
    time, spans = check_holarchy(periods, 'period', dated=True)
    time['basis'] = time_basis
    for cid, p in placement.items():
        d = dates[cid]
        when = _smallest(spans, d) if d else None
        p['when'] = when
        if d and when is None:
            p['when_basis'] = f'no period holds {d.isoformat()}'

    # the matrix
    cells = {}
    for cid in sorted(by_row):
        row = by_row[cid]
        if row.get('status') == COMPLETE or row.get('type') in OPEN_EXCLUDED_TYPES:
            continue
        p = placement[cid]
        c = cells.setdefault((p['where'], p['when']), {'cards': [], 'minutes': 0.0, 'tf': None, 'critical': 0})
        c['cards'].append(cid)
        c['minutes'] += _num(row.get('minutes')) or 0.0
        tf = _num(row.get('TF'))
        if tf is not None:
            c['tf'] = tf if c['tf'] is None else min(c['tf'], tf)
        c['critical'] += 1 if row.get('critical') else 0
    matrix = [{'where': w, 'when': n, 'cards': c['cards'], 'open': len(c['cards']),
               'minutes': _out(c['minutes']), 'least_float': _out(c['tf']), 'critical': c['critical']}
              for (w, n), c in sorted(cells.items(), key=lambda kv: (kv[0][0] is None, kv[0][0] or '',
                                                                      kv[0][1] is None, kv[0][1] or ''))]
    return {
        'v': 1, 'engine': ENGINE,
        'data_date': dd.isoformat() if dd else None,
        'space': space,
        'time': time,
        'placement': placement,
        'matrix': matrix,
        'basis': {
            'space': space['basis'], 'time': time_basis,
            'home_place': home if home is not None else 'missing: no home_place in the registers',
            'where': "the card's own where, else its nearest unit's, else the home place, else unplaced",
            'when': ('the smallest period holding the last day of work (the schedule\'s last_day, else '
                     'its finish); a done card\'s actual finish'),
            'matrix': 'open cards only; units and summaries left out (their cards are counted)',
            'rule': 'a place is location, never identity; a period is computed, never typed; '
                    'defects are listed, never fixed by guess',
        },
    }
