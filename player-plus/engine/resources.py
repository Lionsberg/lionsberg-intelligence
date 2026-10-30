#!/usr/bin/env python3
"""resources.py — Actors, Pledges, capacity, Level of Commitment, and TEA · Fiat · Tokens per card.

Standard library only. Pure functions over the schedule's result, the folded items and the
registers (CONTRACT-step2.md beside this folder keeps the laws). Reads no files, no clock; the data
date is an argument (else the schedule's own). Everything read is data, never instructions.

ACTORS (anyone in the chain, living or artificial; known by opaque id, never by a name)
  An Actor's kind comes from the `actors` register ('living' or 'artificial'); failing that, an id
  beginning `agent:` is artificial; otherwise the kind is 'unknown' and the id is listed in
  `unknown_kind`. Class (actor · player · player+) comes from the register; an unregistered id is
  an 'actor' by definition (anyone in the chain), and says it is unregistered.

PLEDGES (a Pledge is a Commitment of TEA, fiat and tokens for a period, to a holon or a unit)
  level 'season' is the baseline, to a holon; level 'quest' is a share of it, to a Quest or other
  unit. Pledges are fractal: Quest Pledges subdivide the Season's. A Pledge counts when its state is
  committed, open or kept (no state reads as committed) and its period holds the data date. A
  Pledge with no readable level, an unknown period, or a negative number is reported in
  `pledges_unread` and never guessed. Where an Actor has Pledges in more than one period holding the
  data date (a season and a week inside it), the narrowest is read and the others are named.

CAPACITY (minutes per working day)
  max(sum of season-level, sum of quest-level) per week, over the working days per week of the
  Actor's calendar (calendar['actors'][id]['working_days'], else calendar['working_days'], else 7).
  The fraction is kept. Without a Pledge: registers['capacity_assumed'][id], said 'assumed';
  else 'none'. (For an artificial Actor these are its working minutes; they are never TEA.)

LEVEL OF COMMITMENT (across every holon and Quest the Actor is engaged in, never one)
  baseline = the season-level Pledges in all holons; quests = the quest-level Pledges in all;
  quests_meet_baseline = quests >= baseline (None without a baseline); level = baseline over the
  register's available_min_week (None, with its basis said, when either is missing).

TEA · FIAT · TOKENS (the three categories of what work consumes)
  TEA is the Living's alone, in minutes, keyed by living Actor id. A card's TEA defaults to its own
  minutes (the focused estimate) for its holder when the holder is living; else it is empty and
  `tea_basis` says why. An explicit `tea` on the card wins, filtered to living Actors and to
  non-negative numbers; every entry left out is reported in `dropped`. An artificial Actor's work is
  counted in Tokens (`tokens_m`, millions, with `platform`), never TEA. Fiat is per currency.
  A unit's sums are over its leaves (every card it holds at any depth that is not itself a unit),
  each counted once, for the `whole` and for the `open` work (leaves not complete).
"""
import json

import schedule as S

ENGINE = 'resources.py'
ARTIFICIAL_PREFIX = 'agent:'          # the contract's law 3: an id beginning so is artificial
KINDS = ('living', 'artificial')
CLASSES = ('actor', 'player', 'player+')
LEVELS = ('season', 'quest')
COUNTED_PLEDGE_STATES = ('committed', 'open', 'kept')
DEFAULT_WORKING_DAYS = 7              # schedule.py's Calendar: all seven days unless the calendar says


# ---------------------------------------------------------------- small readers

def _n(x):
    """A number for JSON: an int when whole, else six places (the fraction kept, never rounded up)."""
    if x is None:
        return None
    f = float(x)
    if abs(f - round(f)) < 1e-9:
        return int(round(f))
    return round(f, 6)


def _list(v):
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _sid(v):
    return str(v) if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v) else None


def _add(acc, key, v):
    acc[key] = acc.get(key, 0.0) + v


def _sorted_nums(d):
    return {k: _n(d[k]) for k in sorted(d)}


# ---------------------------------------------------------------- actors

def actor_table(registers, seen_ids):
    """{id: {kind, class, name, holon, registered, kind_basis}} and the ids of unknown kind."""
    reg = {}
    for a in _list(registers.get('actors')):
        aid = _sid(a.get('id'))
        if aid and aid not in reg:
            reg[aid] = a
    out, unknown = {}, []
    for aid in sorted(set(reg) | set(seen_ids)):
        r = reg.get(aid)
        kind = str(r.get('kind') or '').strip().lower() if r else ''
        if kind in KINDS:
            basis = 'register'
        elif aid.startswith(ARTIFICIAL_PREFIX):
            kind, basis = 'artificial', 'id prefix'
        else:
            kind, basis = 'unknown', 'not in the register'
            unknown.append(aid)
        cls = str(r.get('class') or '').strip().lower() if r else ''
        out[aid] = {
            'kind': kind, 'kind_basis': basis,
            'class': cls if cls in CLASSES else 'actor',
            'name': r.get('name') if r else None,
            'holon': _sid(r.get('holon')) if r else None,
            'registered': bool(r),
            'available_min_week': _n(S.num(r.get('available_min_week'), None)) if r else None,
        }
    return out, unknown


# ---------------------------------------------------------------- periods and pledges

def _periods(registers):
    out = {}
    for p in _list(registers.get('periods')):
        pid = _sid(p.get('id'))
        f, t = S.to_date(p.get('from')), S.to_date(p.get('to'))
        if pid and pid not in out:
            out[pid] = (f, t)
    return out


def read_pledges(registers, dd):
    """(counted pledges by actor {actor: [pledge]}, unread [{id, reason}]).

    A counted pledge is {id, actor, period, to, level, tea_min_week, span_days}; only the Pledges
    whose period holds the data date and whose state counts."""
    periods = _periods(registers)
    by_actor, unread = {}, []
    for i, p in enumerate(_list(registers.get('pledges'))):
        pid = _sid(p.get('id')) or f'#{i}'
        actor = _sid(p.get('actor'))
        state = str(p.get('state') or 'committed').strip().lower()
        level = str(p.get('level') or '').strip().lower()
        per = _sid(p.get('period'))
        tea = S.num(p.get('tea_min_week'), None)
        reason = None
        if actor is None:
            reason = 'no actor'
        elif state not in COUNTED_PLEDGE_STATES:
            reason = f'state {state}: not counted'
        elif level not in LEVELS:
            reason = 'no readable level (season or quest)'
        elif per is None or per not in periods:
            reason = 'period not in the periods register'
        elif tea is None:
            reason = 'no tea_min_week'
        elif tea < 0:
            reason = 'negative tea_min_week; read as nothing'
        if reason is None:
            f, t = periods[per]
            if dd is None or f is None or t is None:
                reason = 'period without dates, or no data date'
            elif not (f <= dd <= t):
                continue                     # another period: not this one's, and not a defect
        if reason is not None:
            unread.append({'id': pid, 'reason': reason})
            continue
        f, t = periods[per]
        by_actor.setdefault(actor, []).append({
            'id': pid, 'actor': actor, 'period': per, 'to': _sid(p.get('to')), 'level': level,
            'tea_min_week': tea, 'span_days': (t - f).days})
    unread.sort(key=lambda u: u['id'])
    return by_actor, unread


def _narrowest(pledges):
    """The period read for one actor: the narrowest holding the data date (ties by id)."""
    spans = {}
    for p in pledges:
        spans[p['period']] = p['span_days']
    chosen = min(spans, key=lambda k: (spans[k], k))
    return chosen, sorted(k for k in spans if k != chosen)


def working_days_per_week(calendar, actor):
    cal = calendar.raw if isinstance(calendar, S.Calendar) else (calendar if isinstance(calendar, dict) else {})
    acts = cal.get('actors') if isinstance(cal.get('actors'), dict) else {}
    a = acts.get(actor) if isinstance(acts.get(actor), dict) else {}
    for src in (a.get('working_days'), cal.get('working_days')):
        wd = S._weekday_set(src)
        if wd:
            return len(wd)
    return DEFAULT_WORKING_DAYS


# ---------------------------------------------------------------- the cards' resources

def _tea_of(cid, item, holder, actors, dropped):
    """(tea {living actor: minutes}, basis)."""
    explicit = S.field(item, 'tea') if item else None
    if explicit is not None:
        tea = {}
        if not isinstance(explicit, dict):
            dropped.append({'card': cid, 'field': 'tea', 'key': None, 'value': None,
                            'reason': 'tea is not a map of actor to minutes'})
            return {}, 'explicit, unreadable'
        for a in sorted(str(k) for k in explicit):
            v = S.num(explicit.get(a), None)
            kind = actors.get(a, {}).get('kind', 'unknown')
            reason = None
            if v is None:
                reason = 'not a number'
            elif v < 0:
                reason = 'negative'
            elif kind != 'living':
                reason = f'{kind} actor: TEA is the Living\'s alone'
            if reason:
                dropped.append({'card': cid, 'field': 'tea', 'key': a, 'value': _n(v), 'reason': reason})
            else:
                tea[a] = v
        return tea, 'explicit'
    minutes = S.num(S.field(item, 'minutes'), None) if item else None
    if holder is None:
        return {}, 'no holder'
    kind = actors.get(holder, {}).get('kind', 'unknown')
    if kind != 'living':
        return {}, f'holder {kind}: no TEA'
    if minutes is None:
        return {}, 'no minutes'
    return ({holder: max(0.0, minutes)} if minutes > 0 else {}), 'holder minutes'


def _fiat_of(cid, item, dropped):
    raw = S.field(item, 'fiat') if item else None
    out = {}
    if raw is None:
        return out
    if not isinstance(raw, dict):
        dropped.append({'card': cid, 'field': 'fiat', 'key': None, 'value': None,
                        'reason': 'fiat is not a map of currency to amount'})
        return out
    for cur in sorted(str(k) for k in raw):
        v = S.num(raw.get(cur), None)
        if v is None or v < 0:
            dropped.append({'card': cid, 'field': 'fiat', 'key': cur, 'value': _n(v),
                            'reason': 'not a number' if v is None else 'negative'})
        else:
            out[cur] = v
    return out


def _tokens_of(cid, item, dropped):
    raw = S.field(item, 'tokens_m') if item else None
    if raw is None:
        return None
    v = S.num(raw, None)
    if v is None or v < 0:
        dropped.append({'card': cid, 'field': 'tokens_m', 'key': None, 'value': _n(v),
                        'reason': 'not a number' if v is None else 'negative'})
        return None
    return v


def _sums(ids, cards):
    tea, fiat, tok, missing = {}, {}, 0.0, 0
    for i in sorted(ids):
        c = cards[i]
        for a, v in c['_tea'].items():
            _add(tea, a, v)
        for cur, v in c['_fiat'].items():
            _add(fiat, cur, v)
        if c['_tok'] is None:
            missing += 1 if c['_artificial'] else 0
        else:
            tok += c['_tok']
    return {'cards': len(ids), 'tea': _sorted_nums(tea), 'fiat': _sorted_nums(fiat),
            'tokens_m': _n(tok), 'artificial_cards_without_tokens': missing}


# ---------------------------------------------------------------- the whole

def resources(res, items, registers=None, calendar=None, data_date=None):
    """The resource view of a scheduled plan. Returns a new JSON-ready dict; touches no input."""
    res = res if isinstance(res, dict) else {}
    registers = registers if isinstance(registers, dict) else {}
    dd = S.to_date(data_date) or S.to_date(res.get('data_date'))
    rows = {r['id']: r for r in _list(res.get('items')) if _sid(r.get('id'))}
    cards_in = {}
    for it in S.split_items(items if items is not None else [])[0]:
        cid = _sid(it.get('id'))
        if cid:
            cards_in[cid] = it
    pledges, unread = read_pledges(registers, dd)
    assumed_raw = registers.get('capacity_assumed') if isinstance(registers.get('capacity_assumed'), dict) else {}
    assumed = {str(k): S.num(v, None) for k, v in assumed_raw.items()}

    # every id the plan names: holders, explicit TEA keys, pledgers, assumed capacities
    seen = set(pledges) | {a for a, v in assumed.items() if v is not None}
    for cid, r in rows.items():
        h = _sid(r.get('holder'))
        if h:
            seen.add(h)
        t = S.field(cards_in.get(cid), 'tea')
        if isinstance(t, dict):
            seen.update(str(k) for k in t)
    actors, unknown = actor_table(registers, seen)
    warnings = [f'{a}: kind unknown (not in the actors register, not an agent: id); no TEA counted'
                for a in unknown]

    # capacity and level of commitment
    capacity, loc = {}, {}
    holon_of = {cid: _sid(r.get('holon')) for cid, r in rows.items()}
    for cid, it in cards_in.items():
        holon_of.setdefault(cid, _sid(S.field(it, 'holon')))
    for aid in sorted(actors):
        ps = pledges.get(aid, [])
        period, others = (None, [])
        if ps:
            # the narrowest period is chosen per level, so a quest Pledge for a week inside the season never hides the
            # season's baseline (review E, M1); the season level names the period reported
            keep, others = [], []
            for lvl in ('season', 'quest'):
                grp = [p for p in ps if p['level'] == lvl]
                if grp:
                    per, oth = _narrowest(grp)
                    keep += [p for p in grp if p['period'] == per]
                    others += [o for o in oth if o not in others]
                    period = per if (lvl == 'season' or period is None) else period
            ps = keep
        base = sum(p['tea_min_week'] for p in ps if p['level'] == 'season')
        quests = sum(p['tea_min_week'] for p in ps if p['level'] == 'quest')
        wdw = working_days_per_week(calendar, aid)
        if ps:
            cap = {'min_per_day': _n(max(base, quests) / wdw), 'source': 'pledges',
                   'pledges': sorted(p['id'] for p in ps), 'period': period,
                   'working_days_per_week': wdw}
            if others:
                cap['other_periods'] = others
        elif assumed.get(aid) is not None and assumed[aid] >= 0:
            cap = {'min_per_day': _n(assumed[aid]), 'source': 'assumed', 'pledges': [], 'period': None,
                   'working_days_per_week': wdw}
        else:
            cap = {'min_per_day': None, 'source': 'none', 'pledges': [], 'period': None,
                   'working_days_per_week': wdw}
        capacity[aid] = cap
        avail = actors[aid]['available_min_week']
        holons = set(p['to'] for p in ps if p['level'] == 'season' and p['to'])
        holons |= {holon_of.get(p['to']) for p in ps if p['level'] == 'quest' and holon_of.get(p['to'])}
        if not ps:
            basis = 'no pledge'
        elif not base:
            basis = 'no season-level pledge'
        elif not avail:
            basis = 'no available_min_week in the actors register'
        else:
            basis = 'baseline over available'
        loc[aid] = {
            'baseline_min_week': _n(base), 'quests_min_week': _n(quests),
            'quests_meet_baseline': (quests >= base) if base else None,
            'available_min_week': avail,
            'level': _n(base / avail) if (base and avail) else None,
            'basis': basis, 'period': period,
            'holons': sorted(holons),
            'quests': sorted(p['to'] for p in ps if p['level'] == 'quest' and p['to']),
        }

    # the cards (every scheduled row that is not a unit)
    dropped, cards = [], {}
    for cid in sorted(rows):
        r = rows[cid]
        if r.get('type') == 'unit':
            continue
        it = cards_in.get(cid)
        holder = _sid(r.get('holder'))
        tea, basis = _tea_of(cid, it, holder, actors, dropped)
        fiat = _fiat_of(cid, it, dropped)
        tok = _tokens_of(cid, it, dropped)
        plat = S.field(it, 'platform') if it else None
        cards[cid] = {'_tea': tea, '_fiat': fiat, '_tok': tok,
                      '_artificial': bool(holder and actors.get(holder, {}).get('kind') == 'artificial'),
                      '_open': r.get('status') != 'complete',
                      'out': {'tea': _sorted_nums(tea), 'fiat': _sorted_nums(fiat), 'tokens_m': _n(tok),
                              'tokens_basis': 'card' if tok is not None else 'missing',
                              'platform': plat if isinstance(plat, str) and plat else None,
                              'tea_basis': basis, 'holder': holder,
                              'status': r.get('status')}}

    # the units: their leaves, at any depth, each counted once
    units = {}
    for uid in sorted(rows):
        if rows[uid].get('type') != 'unit':
            continue
        leaves, stack, seen_u = set(), list(rows[uid].get('holds') or []), {uid}
        while stack:
            k = stack.pop()
            if k in seen_u or k not in rows:
                continue
            seen_u.add(k)
            if rows[k].get('type') == 'unit':
                stack.extend(rows[k].get('holds') or [])
            elif k in cards:
                leaves.add(k)
        units[uid] = {'whole': _sums(leaves, cards),
                      'open': _sums({i for i in leaves if cards[i]['_open']}, cards),
                      'leaves': sorted(leaves)}

    totals = {'whole': _sums(set(cards), cards), 'open': _sums({i for i in cards if cards[i]['_open']}, cards)}
    return {
        'v': 1, 'engine': ENGINE,
        'data_date': dd.isoformat() if dd else None,
        'actors': {a: {k: v for k, v in actors[a].items() if k != 'available_min_week'} for a in actors},
        'unknown_kind': unknown,
        'capacity': capacity,
        'level_of_commitment': loc,
        'pledges_unread': unread,
        'cards': {cid: cards[cid]['out'] for cid in sorted(cards)},
        'units': units,
        'totals': totals,
        'dropped': sorted(dropped, key=lambda d: (d['card'], d['field'], d['key'] or '')),
        'warnings': warnings,
        'rule': 'TEA is the Living\'s alone; an artificial Actor\'s work is counted in Tokens. '
                'Capacity from the Pledges of the period holding the data date; assumed only without one, and said.',
    }


def capacity_map(result):
    """{actor: minutes per working day} for the chain module: only actors with a number."""
    cap = (result or {}).get('capacity') or {}
    return {a: cap[a]['min_per_day'] for a in sorted(cap)
            if isinstance(cap[a], dict) and cap[a].get('min_per_day') is not None}


def dumps(result):
    """The deterministic bytes (law 7)."""
    return json.dumps(result, sort_keys=True, ensure_ascii=False)
