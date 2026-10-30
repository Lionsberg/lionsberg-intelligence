#!/usr/bin/env python3
"""chain.py — the leveled critical chain, its buffers, the fever chart, release by pull, and the day.

Standard library only. Pure functions: data comes in as arguments and a JSON-ready dict goes out;
nothing is read from files, nothing is written, no clock is read (the data date is an argument).
It keeps the module contract (CONTRACT-step2.md) and builds on schedule.py: the logic dates come
from `schedule.run()`'s result, and the logic itself (each card's predecessors, with type and lag,
routed through units) is read by schedule.py's own reader, so both see the same network.

THE TIME AXIS
  Every number is a fractional working-day index from the data date, on one calendar (the
  `calendar` argument; all seven days by default, so a day is then a calendar day), exactly as
  schedule.py counts. A whole index is that day's morning; a fraction is part-way through it. A
  date is the day the moment lies in (floor), as schedule.py's `_item_out` gives it. Minutes are
  the one unit of size: a card's days are its minutes over its holder's minutes a day, with the
  fraction kept.

LEVELING (serial, in the topological order of the logic)
  Among the open cards whose predecessors are all leveled, take the least late finish, then the
  least total float, then the id. Its start may be no earlier than its logic early start and the
  constraint each predecessor's leveled dates put on it (FS: P.lev_EF + lag; SS: P.lev_ES + lag;
  FF: P.lev_EF + lag - its remaining days; SF: P.lev_ES + lag - its remaining days). From there
  the holder's remaining focused minutes are poured into the holder's days with room, at
  capacity[holder]['min_per_day'] a day: each day fills from its morning, and a card begins where
  the day's work so far ends. lev_TF = the logic late finish - lev_EF.
  Not poured, and so kept at their logic duration from that start: a milestone (it marks
  completion), a card with no minutes left, a card whose duration the world sets (`dur_days`),
  and a card whose holder has no capacity entry (or none above 0), each listed in `unleveled`
  with its reason.

THE CRITICAL CHAIN (traced, never guessed)
  For each open milestone with no live successor (an end) and each milestone a marker names by
  id, walk back from it along the predecessor that set its leveled start: a logic predecessor, or
  a resource one (the card the leveling placed it after on the same holder). The chain is that
  walk, ordered from its first card to the milestone.

BUFFERS (root of the sum of squares)
  safety = max(0, minutes_safe - minutes): the safe estimate less the focused one, for a card
  with two estimates. A project buffer per traced chain is sqrt(sum of safety^2) in minutes, and
  in days as sqrt(sum of (safety / its holder's minutes a day)^2). A feeding buffer stands where a
  non-chain logic predecessor joins a chain card, sized the same way over the side chain (that
  predecessor and every non-chain card before it).

THE FEVER CHART (per project buffer)
  done_share = minutes done / minutes of the chain; consumed_share = the working days the
  milestone's leveled finish has moved past its baseline leveled finish, over the buffer's days.
  Zones (FEVER_ZONES): red above 0.30 + 0.70 x done, yellow above 0.15 + 0.55 x done, green
  below or on the line.

RELEASE BY PULL
  A card on a chain is released on its leveled start. Any other is released on max(ES, LS - its
  feeding buffer): a side chain starts late by design, by lean pull.

THE DAY (Should and Can; Will is never computed)
  Per actor with capacity: Should is the actor's cards whose leveled start lies on the data date,
  the chain first, then the least leveled float, then the id, up to the minutes the actor has for
  the day (always one, if there is any). Can is the part of it whose stage is `can` or whose
  predecessors are all complete. Will is the Player's own choice, and this module never makes it.
"""
import datetime as dt
import heapq
import math

import schedule as S

MODULE = 'chain.py'
EPS = 1e-9
# The fever chart's zone lines: consumed share above base + slope x done share. Source: the house
# engine's fever chart (build/cards.py, "zones as commonly drawn" in critical chain buffer
# management). A method's own constant; the `zones` argument overrides it.
FEVER_ZONES = {'red': (0.30, 0.70), 'yellow': (0.15, 0.55)}
NO_BUFFER = 'no buffer yet: no two estimates on its chain'
LOGIC_TYPES = ('activity', 'milestone')
OPEN_STATUS = ('not_started', 'in_progress')


# ---------------------------------------------------------------- small helpers

def _r(x):
    return None if x is None else round(float(x), 6)


def _num(x):
    return S.num(x, None)


def rss(xs):
    """Root of the sum of squares (0 for none)."""
    return math.sqrt(sum(float(x) * float(x) for x in xs))


def fever_zone(consumed, done, zones=None):
    """The fever chart's zone for a consumed share against a done share; None when consumed is None."""
    if consumed is None:
        return None
    z = zones or FEVER_ZONES
    rb, rs = z['red']
    yb, ys = z['yellow']
    d = done or 0.0
    if consumed > rb + rs * d + EPS:
        return 'red'
    if consumed > yb + ys * d + EPS:
        return 'yellow'
    return 'green'


def _cap(capacity, actor):
    """(minutes a day, source) from the capacity map; (None, reason) when it has none to give."""
    if not actor:
        return None, 'no holder'
    c = (capacity or {}).get(actor) if isinstance(capacity, dict) else None
    if not isinstance(c, dict):
        return None, 'its holder has no capacity entry'
    m = _num(c.get('min_per_day'))
    if m is None or m <= 0:
        return None, "its holder's capacity is 0 minutes a day"
    return m, c.get('source')


# ---------------------------------------------------------------- the whole

def chain(res, items, capacity, registers=None, data_date=None, calendar=None, zones=None):
    """The leveled critical chain over a schedule result. Returns a JSON-ready dict:
    leveled, unleveled, critical_chain, buffers, fever, release, day, basis.

    `res` is schedule.run(items, calendar, data_date)'s result; `items` the cards given to it;
    `capacity` {actor: {min_per_day, source, ...}} (resources.py's); `registers` the plain-data
    registers (markers, baseline); `data_date` defaults to the result's; `calendar` is the
    calendar the indexes count on (all seven days by default); `zones` overrides FEVER_ZONES.
    """
    registers = registers if isinstance(registers, dict) else {}
    capacity = capacity if isinstance(capacity, dict) else {}
    res = res if isinstance(res, dict) else {}
    dd = S.to_date(data_date) or S.to_date(res.get('data_date'))
    if dd is None:
        raise ValueError('chain: a data date is needed (as an argument or in the result)')
    cal = calendar if isinstance(calendar, S.Calendar) else S.Calendar(calendar)
    ax = S.Axis(dd, cal)

    def date(k):
        return ax.date_of(k).isoformat() if k is not None else None

    # the logic, by schedule.py's own reader (predecessors with type and lag, routed through units)
    warnings = []
    _, _, _, acts, _, _, _ = S._prepare(items, cal, dd.isoformat(), None, warnings)

    rows = {r['id']: r for r in (res.get('items') or []) if isinstance(r, dict) and r.get('id') is not None}
    opn = {i: r for i, r in rows.items()
           if r.get('status') in OPEN_STATUS and r.get('type') in LOGIC_TYPES and r.get('ES') is not None}
    raw = {}
    for it in S.split_items(items)[0]:
        if it.get('id') is not None:
            raw[str(it['id'])] = it

    def preds(i):
        a = acts.get(i)
        return [(p, t, float(lag)) for p, t, lag in (a.preds if a else []) if p in opn]

    def succs(i):
        a = acts.get(i)
        return [s for s, _, _ in (a.succs if a else []) if s in opn]

    def rem_minutes(i):
        r = opn[i]
        rm = _num(S.field(raw.get(i), 'remaining_minutes'))
        if rm is not None and rm >= 0:
            return rm
        m = _num(r.get('minutes')) or 0.0
        pct = _num(r.get('percent_complete')) or 0.0
        return max(0.0, m * (1 - pct / 100.0))

    def mpd_of(i):
        """The holder's minutes a day for card i: its capacity, else the schedule's own ratio."""
        r = rows.get(i) or {}
        m, _ = _cap(capacity, r.get('holder'))
        if m:
            return m
        mins, days = _num(r.get('minutes')), _num(r.get('dur_days'))
        if mins and days:
            return mins / days
        return None

    # ------------------------------------------------------------ leveling
    lev = {}            # id -> {'es', 'ef', 'driver', 'by'}
    unleveled = {}
    fills, booker = {}, {}
    indeg = {i: len({p for p, _, _ in preds(i)}) for i in opn}
    inf = float('inf')

    def prio(i):
        r = opn[i]
        lf, tf = _num(r.get('LF')), _num(r.get('TF'))
        return (lf if lf is not None else inf, tf if tf is not None else inf, i)

    heap = [prio(i) for i in opn if indeg[i] == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        _, _, i = heapq.heappop(heap)
        order.append(i)
        r = opn[i]
        rem_d = _num(r.get('remaining_days')) or 0.0
        s0 = _num(r.get('ES')) or 0.0
        logic_driver = None
        best = None
        for p, t, lag in sorted(preds(i), key=lambda x: x[0]):
            P = lev[p]
            c = {'FS': P['ef'] + lag, 'SS': P['es'] + lag,
                 'FF': P['ef'] + lag - rem_d, 'SF': P['es'] + lag - rem_d}.get(t, P['ef'] + lag)
            if best is None or c > best + EPS:
                best, logic_driver = c, p
        if best is not None and best > s0 + EPS:
            s0 = best
        elif best is None or best < s0 - EPS:
            logic_driver = None            # the start is set by something else (the data date, an external)
        s0 = _r(s0)
        holder = r.get('holder')
        m_left = rem_minutes(i)
        cap, why = _cap(capacity, holder)
        world = S.field(raw.get(i), 'dur_days') is not None
        reason = None
        if r.get('type') == 'milestone' or m_left <= EPS:
            reason = None
        elif world:
            reason = 'its duration is set by the world (dur_days); kept, not poured'
        elif cap is None:
            reason = why
        if r.get('type') == 'milestone' or m_left <= EPS or reason:
            if reason:
                unleveled[i] = reason
            lev[i] = {'es': s0, 'ef': _r(s0 + rem_d), 'driver': logic_driver,
                      'by': 'logic' if logic_driver else None}
        else:
            f_h = fills.setdefault(holder, {})
            b_h = booker.setdefault(holder, {})
            k0 = int(math.floor(s0 + EPS))
            k, f = k0, s0 - k0
            left, first, end, rdrv = m_left, None, s0, None
            for _ in range(S.Axis.LIMIT):
                if left <= EPS:
                    break
                works = cal.actor_works(holder, ax.date_of(k))
                fill = f_h.get(k, 0.0)
                begin = max(f, fill)
                room = (1.0 - begin) * cap if works else 0.0
                if room > EPS:
                    take = min(room, left)
                    if first is None:
                        first = k + begin
                        if first > s0 + EPS:
                            if begin > EPS and fill >= begin - EPS and k in b_h:
                                rdrv = b_h[k]
                            else:
                                for j in range(k - 1, k0 - 1, -1):
                                    if j in b_h:
                                        rdrv = b_h[j]
                                        break
                    f_h[k] = begin + take / cap
                    b_h[k] = i
                    left -= take
                    end = k + begin + take / cap
                k, f = k + 1, 0.0
            else:
                raise S.ScheduleError(f'{i}: no day with room for its holder')
            first = s0 if first is None else first
            if rdrv is not None:
                lev[i] = {'es': _r(first), 'ef': _r(end), 'driver': rdrv, 'by': 'resource'}
            else:
                lev[i] = {'es': _r(first), 'ef': _r(end), 'driver': logic_driver,
                          'by': 'logic' if logic_driver else None}
        for s in sorted(set(succs(i))):
            indeg[s] -= 1
            if indeg[s] == 0:
                heapq.heappush(heap, prio(s))
    if len(order) < len(opn):
        raise S.ScheduleError('cycle through ' + ', '.join(sorted(i for i in opn if i not in lev)))

    leveled = {}
    for i in sorted(lev):
        L, r = lev[i], opn[i]
        lf = _num(r.get('LF'))
        L['tf'] = _r(lf - L['ef']) if lf is not None else None
        leveled[i] = {'lev_ES': S.out_num(L['es']), 'lev_EF': S.out_num(L['ef']), 'lev_TF': S.out_num(L['tf']),
                      'lev_start': date(L['es']), 'lev_finish': date(L['ef']),
                      'driven_by': {'id': L['driver'], 'tie': L['by']} if L['driver'] else None}

    # ------------------------------------------------------------ the critical chain, traced
    markers = {}
    for m in registers.get('markers') or []:
        if isinstance(m, dict) and m.get('id') is not None:
            markers[str(m['id'])] = m
    # a milestone names its marker (`marker`, a calendar marker id); a marker may also be named by the milestone's own id
    marker_of = {}
    for i, r in opn.items():
        mk = S.field(raw.get(i), 'marker')
        if r.get('type') == 'milestone':
            if isinstance(mk, str) and mk.strip() in markers:
                marker_of[i] = mk.strip()
            elif i in markers:
                marker_of[i] = i
    targets = set()
    for i, r in opn.items():
        if r.get('type') == 'milestone' and (not succs(i) or i in marker_of):
            targets.add(i)
    markers_without = sorted(k for k in markers if k not in set(marker_of.values()))
    chains = []
    for m in sorted(targets):
        path, cur, seen = [m], m, {m}
        while lev[cur]['driver'] is not None and lev[cur]['driver'] in lev and lev[cur]['driver'] not in seen:
            cur = lev[cur]['driver']
            seen.add(cur)
            path.append(cur)
        path.reverse()
        mk = markers.get(marker_of.get(m)) if m in marker_of else None
        chains.append({'milestone': m, 'cards': path,
                       'ties': [{'from': path[k - 1], 'to': path[k], 'tie': lev[path[k]]['by']}
                                for k in range(1, len(path))],
                       'end': not succs(m), 'marker': marker_of.get(m) if mk else None,
                       'marker_date': (mk.get('date') if mk else None),
                       'lev_EF': S.out_num(lev[m]['ef']), 'lev_finish': date(lev[m]['ef'])})
    on_chain = set()
    for c in chains:
        on_chain.update(c['cards'])

    # ------------------------------------------------------------ buffers
    def safety(i):
        """(minutes, days, has two estimates) for an open activity."""
        it = raw.get(i)
        safe, foc = _num(S.field(it, 'minutes_safe')), _num(S.field(it, 'minutes'))
        if safe is None or foc is None:
            return 0.0, 0.0, False
        s = max(0.0, safe - foc)
        mpd = mpd_of(i)
        return s, (s / mpd if mpd else None), True

    def size(ids):
        work = [i for i in sorted(ids) if opn[i].get('type') != 'milestone']
        sm, sd, two, without, no_days = [], [], [], [], []
        for i in work:
            s, d, has = safety(i)
            if has:
                two.append(i)
                sm.append(s)
                if d is None:
                    no_days.append(i)
                else:
                    sd.append(d)
            else:
                without.append(i)
        out = {'size_min': S.out_num(rss(sm)), 'size_days': S.out_num(rss(sd)),
               'cards_with_two_estimates': two, 'cards_without': without}
        if no_days:
            out['missing'] = 'no minutes a day for ' + ', '.join(no_days) + '; left out of the days'
        if not two:
            out['note'] = NO_BUFFER
        return out, rss(sd)

    project = []
    for c in chains:
        b, days = size(c['cards'])
        ef = lev[c['milestone']]['ef']
        b.update({'milestone': c['milestone'], 'marker': c['marker'], 'marker_date': c['marker_date'],
                  'chain': c['cards'], 'chain_finish': date(ef),
                  'due_with_buffer': date(ef + days)})
        if c['marker_date'] and S.to_date(c['marker_date']):
            b['fits_marker'] = S.to_date(b['due_with_buffer']) <= S.to_date(c['marker_date'])
        b['_days'] = days
        project.append(b)
    feeding, fb = [], {}
    for j in sorted(on_chain):
        for p in sorted({p for p, _, _ in preds(j)}):
            if p in on_chain:
                continue
            side, stack = set(), [p]
            while stack:
                q = stack.pop()
                if q in side or q in on_chain or q not in opn:
                    continue
                side.add(q)
                stack.extend(x for x, _, _ in preds(q))
            b, days = size(side)
            b.update({'joins': j, 'from': p, 'side_chain': sorted(side)})
            feeding.append(b)
            for q in side:
                fb[q] = max(fb.get(q, 0.0), days)

    # ------------------------------------------------------------ the fever chart
    base = registers.get('baseline') if isinstance(registers.get('baseline'), dict) else {}
    fever = []
    for b in project:
        cards_ = [i for i in b['chain'] if opn[i].get('type') != 'milestone']
        tot = sum(_num(opn[i].get('minutes')) or 0.0 for i in cards_)
        done = sum((_num(opn[i].get('minutes')) or 0.0) * (_num(opn[i].get('percent_complete')) or 0.0) / 100.0
                   for i in cards_)
        tail, stack = set(), [b['chain'][0]] if b['chain'] else []
        while stack:                       # the done cards just before the chain, through done cards only
            q = stack.pop()
            for p, _, _ in (acts[q].preds if q in acts else []):
                if p in acts and acts[p].status == 'complete' and p not in tail:
                    tail.add(p)
                    stack.append(p)
        for p in tail:
            m = acts[p].minutes or 0.0
            tot += m
            done += m
        done_share = done / tot if tot > 0 else None
        m_id = b['milestone']
        bl = S.to_date((base.get(m_id) or {}).get('lev_finish')) if isinstance(base.get(m_id), dict) else None
        missing = []
        consumed, slip = None, None
        if not b['cards_with_two_estimates'] or not b['_days']:
            missing.append(b.get('note') or 'the buffer is 0 days')
        if bl is None:
            missing.append('no baseline lev_finish for ' + m_id)
        if bl is not None:
            slip = max(0, ax.idx_of(S.to_date(b['chain_finish'])) - ax.idx_of(bl))
        if bl is not None and b['_days']:
            consumed = slip / b['_days']
        row = {'milestone': m_id, 'marker': b['marker'], 'done_share': S.out_num(done_share),
               'done_cards_before_chain': sorted(tail),
               'slip_days': slip, 'buffer_days': b['size_days'],
               'consumed_share': S.out_num(consumed), 'zone': fever_zone(consumed, done_share, zones)}
        if missing:
            row['missing'] = '; '.join(missing)
        fever.append(row)
    for b in project:
        del b['_days']

    # ------------------------------------------------------------ release by pull
    release = {}
    for i in sorted(opn):
        r = opn[i]
        if i in on_chain:
            release[i] = {'release_on': leveled[i]['lev_start'], 'on_chain': True,
                          'feeding_buffer_days': 0, 'rule': 'its leveled start (on the critical chain)'}
            continue
        es, ls = _num(r.get('ES')) or 0.0, _num(r.get('LS'))
        f = fb.get(i, 0.0)
        k = es if ls is None else max(es, ls - f)
        release[i] = {'release_on': date(k), 'on_chain': False, 'feeding_buffer_days': S.out_num(f),
                      'rule': ('its early start (no late start)' if ls is None else
                               'its late start less its feeding buffer' if ls - f > es + EPS else
                               'its early start (its late start less its buffer falls before it)')}

    # ------------------------------------------------------------ the day
    day = {}
    for actor in sorted(capacity):
        cap, why = _cap(capacity, actor)
        capd = cap or 0.0
        if cap and not cal.actor_works(actor, dd):
            capd = 0.0
        mine = [i for i in opn if opn[i].get('holder') == actor and opn[i].get('type') != 'milestone'
                and lev[i]['es'] < 1 - EPS]
        mine.sort(key=lambda i: (i not in on_chain, lev[i]['tf'] if lev[i]['tf'] is not None else inf, i))
        should, used, unsized = [], 0.0, []
        for i in mine:
            if rem_minutes(i) <= EPS:
                unsized.append(i)          # no minutes: not yet work a day can hold; sized first, then pulled
                continue
            need = _today(i, lev[i], rem_minutes(i), cap)
            if should and used + need > capd + EPS:
                break
            should.append(i)
            used += need
        can = []
        for i in should:
            stage = str(S.field(raw.get(i), 'stage') or '').lower()
            a = acts.get(i)
            clear = a is not None and not a.ext_preds and all(
                p in acts and acts[p].status == 'complete' for p, _, _ in a.preds)
            if stage == 'can' or clear:
                can.append(i)
        cap_entry = capacity.get(actor) if isinstance(capacity.get(actor), dict) else {}
        day[actor] = {'should': should, 'can': can, 'should_min': S.out_num(used), 'unsized': unsized,
                      'capacity_min': S.out_num(capd), 'capacity_source': cap_entry.get('source'),
                      'missing': why if cap is None else None}

    basis = {
        'axis': f'working-day indexes from {dd.isoformat()} on '
                + (cal.kind() if isinstance(calendar, (dict, S.Calendar)) else 'all seven days (no calendar given)')
                + '; a date is the day the moment lies in'
                + ('; the result names holon calendars, which this module reads as one' if res.get('calendars') else ''),
        'leveled': 'serial in the logic\'s order (least late finish, then float, then id); each holder\'s remaining '
                   'minutes poured into its days with room at capacity min_per_day, each day filled from its morning; '
                   'logic dates and predecessor ties from the schedule (indexes as the result gives them, 6 places); '
                   'lev_TF = the logic late finish - lev_EF',
        'critical_chain': 'traced back from each open end milestone and each marker\'s milestone along the predecessor '
                          '(logic, or the resource tie on the same holder) that set its leveled start'
                          + ('' if chains else '; no open milestone, so no chain is traced'),
        'buffers': 'root of the sum of squares of safety = max(0, minutes_safe - minutes) over the chain\'s cards '
                   '(project) or the side chain\'s (feeding); days per card over its holder\'s minutes a day '
                   '(capacity, else the schedule\'s own minutes over days)',
        'fever': 'done share = minutes done (percent complete, and the done cards just before the chain) over the '
                 'chain\'s minutes; consumed share = whole working days the milestone\'s leveled finish has moved past '
                 'its baseline lev_finish, over the buffer days; zone lines red %s + %s x done, yellow %s + %s x done'
                 % ((zones or FEVER_ZONES)['red'] + (zones or FEVER_ZONES)['yellow']),
        'release': 'on the chain: its leveled start; else max(ES, LS - its feeding buffer), by lean pull',
        'day': 'Should: cards whose leveled start lies on the data date, chain first, then least leveled float, '
               'then id, up to the day\'s minutes (the minutes the leveling booked on the data date); Can: of those, '
               'stage can or every predecessor complete; Will is the Player\'s own and never computed',
    }
    return {
        'v': 1, 'module': MODULE, 'data_date': dd.isoformat(),
        'leveled': leveled,
        'unleveled': [{'id': i, 'reason': unleveled[i]} for i in sorted(unleveled)],
        'critical_chain': chains,
        'markers_without_milestone': markers_without,
        'buffers': {'project': project, 'feeding': feeding},
        'fever': fever,
        'release': release,
        'day': day,
        'warnings': sorted(set(warnings)),
        'basis': basis,
    }


def _today(i, L, minutes, cap):
    """The minutes of card i that fall on the data date (index 0) by its leveled pour."""
    if not cap:
        return minutes
    es, ef = L['es'], L['ef']
    if es >= 1 - EPS:
        return 0.0
    if ef <= 1 + EPS:
        return minutes
    return min(minutes, (1.0 - (es - math.floor(es + EPS))) * cap)
