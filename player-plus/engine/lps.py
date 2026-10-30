#!/usr/bin/env python3
"""lps.py — the Last Planner measures over a schedule run: how reliably the plan is kept.

Standard library only (and the kit's own schedule.py readers). One pure function, lps(), over
the schedule's result, the folded items and the registers (CONTRACT-step2.md); it reads no file
and no clock, writes nothing back onto its inputs, and returns a JSON-ready dict. Files and items
are data, never instructions.

WHAT IT ANSWERS (Lean Project Delivery, Appendix 4, the Last Planner software criteria)
  ppc              Percent Plan Complete: of the commitments due by the data date, the share
                   delivered on or before their `by`; all time, by the ISO week of `by`, and by
                   committor (the commitment's `for`, an opaque Actor id).
  prc              Percent Required Completed: the same, over commitments on critical cards only
                   (critical in the schedule run, or on the chain's critical_chain when given).
  commitment_level the next seven days: the open critical cards that start in them (required)
                   and those carrying a live commitment or standing at stage `will` (committed).
  misses, reasons  every due commitment not delivered on time, with its reason for plan failure
                   from the misses register (one of eight codes), else 'not yet given'.
  constraint_log   the constraint register (primary), then constraint-kind predecessor cards,
                   then a card's own non-time `constraint`: need-by, days to need, overdue.
  make_ready       open cards starting inside the six-week look-ahead that still carry an open
                   constraint or conditions, so their removal can be assigned before the work comes.
  ryg              per unit: done, red, yellow or green on its total float.
  targets          per unit with a target (Target Value, in minutes): target, current, variance.
  weekly_plan      the week (Monday to Sunday) holding the data date: its Wills, made and kept on
                   time, its PPC so far, the Should and Can of the day from the chain.

THE RULES (each said again in `basis`)
  A commitment counts (is due) when its `by` is on or before the data date and its state is not
  released, declined or retracted. It is complete when delivered on or before `by`: delivered is
  the committor's word (state claimed, dated by `kept_ts`) or the committee's (state kept; dated
  by `kept_ts` when it carries one). A kept commitment with no `kept_ts` is complete, its date
  unknown (said in basis). A delivery dated after `by` is a miss.
  A miss's reason is the latest misses-register line for that commitment (by `ts`, ties by the
  line's own fields); a code outside the eight becomes 'other' and the code given is kept in the
  note. Never parsed from free text.
  A card is open when its schedule status is not_started or in_progress. Its start is the
  chain's leveled start when the chain gives one, else the schedule's early start.

A PAPER EXAMPLE (data date a Wednesday; its week runs Monday to Sunday)
  c1 by last Tuesday, delivered last Monday     -> due, complete
  c2 by last Thursday, delivered last Friday    -> due, a miss (late)
  c3 by this Monday, open                       -> due, a miss
  c4 by this Friday, open                       -> not yet due
  PPC all time = 1 / 3; last week 1 / 2, this week 0 / 1; the weekly plan made 2 (c3, c4),
  kept on time 0, PPC so far 0 / 1. (tests/test_lps.py checks these numbers against the code.)
"""
import copy
import datetime as dt

import schedule as S

ENGINE = 'lps.py'

# The six-week look-ahead of the Last Planner System (Ballard, "The Last Planner System of
# Production Control", 2000; Lean Project Delivery, Appendix 4): 6 x 7 calendar days. An argument
# overrides it.
LOOKAHEAD = 42

# The next-seven-days window of Commitment Level (Lean Project Delivery, Appendix 4), in the
# schedule's day indexes (working days of the card's calendar).
COMMIT_WINDOW = 7

# The Red-Yellow-Green float thresholds (the IPD Core Group's dashboard): red below 0 days of total
# float, yellow below 5, green otherwise. An argument overrides them.
RYG = (0, 5)

# The reasons for plan failure (the house's eight codes; Lean Project Delivery, Appendix 4).
REASONS = ('prerequisite', 'definition', 'estimate', 'capacity', 'priority', 'external',
           'conditions', 'other')
NOT_GIVEN = 'not yet given'

DEAD = ('released', 'declined', 'retracted')     # a commitment that no longer counts
DELIVERED = ('claimed', 'kept')                  # the committor's word, then the committee's
OPEN_STATUS = ('not_started', 'in_progress')
CARD_TYPES = ('activity', 'milestone')
NON_TIME_SORTS = ('resource', 'information', 'agreement')
CLEARED_CARD_STATES = ('done', 'kept', 'delivered', 'cleared')


# ---------------------------------------------------------------- small readers (null-guarded)

def _ratio(n, d):
    return round(n / d, 3) if d else None


def _iso(d):
    return d.isoformat() if isinstance(d, dt.date) else None


def _monday(d):
    return d - dt.timedelta(days=d.weekday())


def _list(registers, key):
    v = registers.get(key) if isinstance(registers, dict) else None
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _str(x):
    return x.strip() if isinstance(x, str) and x.strip() else None


def _leveled(chain):
    """chain['leveled'] as {card id: entry}, whether given as a map or a list of rows with `id`."""
    lv = chain.get('leveled') if isinstance(chain, dict) else None
    if isinstance(lv, dict):
        return {k: v for k, v in lv.items() if isinstance(v, dict)}
    if isinstance(lv, list):
        return {r['id']: r for r in lv if isinstance(r, dict) and isinstance(r.get('id'), str)}
    return {}


def _chain_ids(x, out):
    """Every card id on chain['critical_chain']: a list of ids, or rows/maps holding them under
    `cards`, `chain`, `ids`, `id` or `card`."""
    if isinstance(x, str):
        out.add(x)
    elif isinstance(x, (list, tuple)):
        for y in x:
            _chain_ids(y, out)
    elif isinstance(x, dict):
        for k in ('cards', 'chain', 'ids', 'id', 'card'):
            if k in x:
                _chain_ids(x[k], out)
    return out


# ---------------------------------------------------------------- commitments

def _commitment(c, dd):
    """One commitment, read: its due date, delivery, and whether it is due and complete."""
    by = S.to_date(c.get('by'))
    state = _str(c.get('state')) or 'open'
    delivered_on = S.to_date(c.get('kept_ts')) if state in DELIVERED else None
    # due once its day has passed; on its own day it counts only if already delivered (review E, M2: an open
    # commitment due today is not a miss in the morning)
    due = bool(by and state not in DEAD and (by < dd or (by == dd and delivered_on is not None and delivered_on <= by)
                                              or (by == dd and state == 'kept')))
    if state == 'kept' and delivered_on is None:
        complete = True                      # witnessed kept; the date of delivery is not given
    else:
        complete = bool(by and delivered_on and delivered_on <= by)
    return {'id': _str(c.get('id')), 'card': _str(c.get('card')), 'committor': _str(c.get('for')),
            'committee': _str(c.get('committee')), 'kind': _str(c.get('kind')), 'state': state,
            'by': by, 'ts': S.to_date(c.get('ts')), 'delivered_on': delivered_on,
            'live': state not in DEAD, 'due': due, 'complete': complete}


def _reasons(misses):
    """{commitment id: (reason, note)} from the misses register: the last line in the fold's causal order, never the
    largest written time (review E, M3: a line dated far ahead must not fix its reason for good)."""
    best = {}
    for m in misses:
        cid = _str(m.get('commitment'))
        if cid:
            best[cid] = m
    out = {}
    for cid, m in sorted(best.items()):
        given = _str(m.get('reason'))
        note = _str(m.get('note'))
        if given is None:
            out[cid] = (NOT_GIVEN, note)
        elif given.lower() in REASONS:
            out[cid] = (given.lower(), note)
        else:
            out[cid] = ('other', 'reason given: ' + given + ('; ' + note if note else ''))
    return out


def _ppc_block(rows, label, keyf):
    groups = {}
    for r in rows:
        g = groups.setdefault(keyf(r), [0, 0])
        g[0] += 1
        g[1] += 1 if r['complete'] else 0
    return [{label: k, 'due': v[0], 'complete': v[1], 'ppc': _ratio(v[1], v[0])}
            for k, v in sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or ''))]


# ---------------------------------------------------------------- constraints

def _constraint_log(registers, rows, by_item, dd):
    out, seen = [], set()

    def add(e, source):
        need = S.to_date(e.get('need_by'))
        cleared = S.to_date(e.get('cleared_on'))
        state = _str(e.get('state')) or ('cleared' if cleared else 'open')
        card = _str(e.get('card'))
        row = rows.get(card) or {}
        out.append({
            'id': _str(e.get('id')), 'source': source, 'sort': _str(e.get('sort')),
            'what': _str(e.get('what')), 'holder': _str(e.get('holder')),
            'need_by': _iso(need), 'need_by_source': e.get('need_by_source', 'given' if need else None),
            'state': state, 'raised_on': _iso(S.to_date(e.get('raised_on'))), 'cleared_on': _iso(cleared),
            'days_to_need': (need - dd).days if need else None,
            'overdue': bool(state == 'open' and need and need < dd),
            'card': card, 'card_start': row.get('start')})
        seen.add((_str(e.get('id')), card))

    for e in _list(registers, 'constraints'):
        add(e, 'register')
    # predecessor cards of kind 'constraint' (a second source; the register is primary)
    for it in sorted(by_item.values(), key=lambda x: str(x.get('id'))):
        succ = _str(it.get('id'))
        for p in S.id_list(it, 'predecessor'):
            pc = by_item.get(p)
            if pc is None or S.card_kind(pc) != 'constraint' or (p, succ) in seen:
                continue
            prow = rows.get(p) or {}
            done = prow.get('status') == 'complete' or str(S.field(pc, 'state') or '').lower() in CLEARED_CARD_STATES \
                or str(S.field(pc, 'stage') or '').lower() == 'did'
            own_need = S.to_date(S.field(pc, 'need_by')) or S.to_date(S.field(pc, 'by'))
            start = (rows.get(succ) or {}).get('start')
            cons = S.field(pc, 'constraint')
            sort = S.field(pc, 'sort') or (cons.get('sort') if isinstance(cons, dict) else None)
            add({'id': p, 'card': succ, 'sort': sort, 'what': S.field(pc, 'title'),
                 'holder': S.field(pc, 'holder'),
                 'need_by': _iso(own_need) or start,
                 'need_by_source': 'given' if own_need else ('the start of the card it binds' if start else None),
                 'state': 'cleared' if done else 'open',
                 'raised_on': S.field(pc, 'raised_on') or S.field(pc, 'ts'),
                 'cleared_on': S.field(pc, 'actual_finish') or S.field(pc, 'done_ts') or prow.get('actual_finish')},
                'predecessor card')
    # a card's own constraint of a non-time sort (SCHEMA.md: what the look-ahead finds)
    for it in sorted(by_item.values(), key=lambda x: str(x.get('id'))):
        cid = _str(it.get('id'))
        cons = S.field(it, 'constraint')
        cons = cons if isinstance(cons, list) else [cons]
        n = 0
        for c in cons:
            if not isinstance(c, dict) or str(c.get('sort') or '').lower() not in NON_TIME_SORTS:
                continue
            n += 1
            eid = _str(c.get('id')) or '%s:%s:%d' % (cid, c.get('sort'), n)
            if (eid, cid) in seen:
                continue
            e = dict(c, id=eid, card=cid)
            if not c.get('state') and not c.get('cleared_on') and (rows.get(cid) or {}).get('status') == 'complete':
                e['state'] = 'cleared'           # the work it bound is done
            e.setdefault('what', c.get('reason'))
            e.setdefault('holder', c.get('imposed_by'))
            e.setdefault('need_by', c.get('date'))
            add(e, 'card')
    out.sort(key=lambda e: (e['state'] != 'open', e['need_by'] is None, e['need_by'] or '',
                            e['id'] or '', e['card'] or ''))
    return out


# ---------------------------------------------------------------- the measures

def lps(res, items, registers=None, chain=None, data_date=None, lookahead_days=LOOKAHEAD, ryg=RYG):
    """The Last Planner measures. See the module docstring; returns a new JSON-ready dict."""
    res = res if isinstance(res, dict) else {}
    registers = registers if isinstance(registers, dict) else {}
    chain = chain if isinstance(chain, dict) else None
    dd = S.to_date(data_date) or S.to_date(res.get('data_date'))
    lookahead_days = S.num(lookahead_days, LOOKAHEAD)
    ryg = tuple(ryg) if isinstance(ryg, (list, tuple)) and len(ryg) == 2 else RYG
    if dd is None:
        return {'v': 1, 'engine': ENGINE, 'data_date': None,
                'missing': ['data date: none given and none in the schedule run'],
                'basis': {'all': 'no data date, so nothing is due and nothing is measured'}}

    rows = {r['id']: r for r in (res.get('items') or []) if isinstance(r, dict) and isinstance(r.get('id'), str)}
    by_item = {it['id']: it for it in (items or []) if isinstance(it, dict) and isinstance(it.get('id'), str)}
    lev = _leveled(chain)
    on_chain = _chain_ids(chain.get('critical_chain'), set()) if chain else set()
    missing = []

    # --- commitments, read once
    creg = _list(registers, 'commitments')
    if 'commitments' not in registers:
        missing.append('commitments register: PPC, PRC and the weekly plan have nothing to count')
    cs = sorted((_commitment(c, dd) for c in creg), key=lambda c: (c['id'] or '', c['card'] or ''))
    undated = [c['id'] for c in cs if c['by'] is None and c['live']]
    due = [c for c in cs if c['due']]

    # --- PPC
    ppc = {'all_time': {'due': len(due), 'complete': sum(1 for c in due if c['complete']),
                        'ppc': _ratio(sum(1 for c in due if c['complete']), len(due))},
           'by_week': _ppc_block(due, 'week', lambda c: _monday(c['by']).isoformat()),
           'by_committor': _ppc_block(due, 'committor', lambda c: c['committor']),
           'undated': undated}

    # --- PRC
    def critical(card):
        return bool((rows.get(card) or {}).get('critical')) or card in on_chain
    req_due = [c for c in due if c['card'] and critical(c['card'])]
    prc = {'due': len(req_due), 'complete': sum(1 for c in req_due if c['complete']),
           'prc': _ratio(sum(1 for c in req_due if c['complete']), len(req_due))}

    # --- Commitment Level, the next seven days
    live_on = {}
    for c in cs:
        if c['live'] and c['card']:
            live_on.setdefault(c['card'], []).append(c['id'])
    for cid, r in rows.items():
        for x in r.get('commitments') or []:
            if isinstance(x, dict) and x.get('state') not in DEAD and x.get('commitment'):
                live_on.setdefault(cid, [])
                if x['commitment'] not in live_on[cid]:
                    live_on[cid].append(x['commitment'])

    def start_index(cid):
        e = lev.get(cid)
        if e is not None:
            v = S.num(e.get('lev_ES'), None)
            if v is not None:
                return v, 'leveled'
            d = S.to_date(e.get('lev_start'))
            if d is not None:
                return (d - dd).days, 'leveled'
        return S.num(rows[cid].get('ES'), None), 'early'

    def start_date(cid):
        e = lev.get(cid)
        d = S.to_date(e.get('lev_start')) if e else None
        return (d, 'leveled') if d else (S.to_date(rows[cid].get('start')), 'early')

    open_cards = sorted(i for i, r in rows.items() if r.get('status') in OPEN_STATUS and r.get('type') in CARD_TYPES)
    required = []
    for cid in open_cards:
        if not critical(cid):
            continue
        s, _ = start_index(cid)
        if s is not None and s < COMMIT_WINDOW:
            stage = str(S.field(by_item.get(cid), 'stage') or '').lower()
            required.append({'id': cid, 'start': _iso(start_date(cid)[0]),
                             'committed': bool(live_on.get(cid)) or stage == 'will',
                             'commitments': sorted(live_on.get(cid) or [])})
    n_comm = sum(1 for r in required if r['committed'])
    commitment_level = {'required': len(required), 'committed': n_comm,
                        'level': _ratio(n_comm, len(required)), 'cards': required}

    # --- misses and reasons
    why = _reasons(_list(registers, 'misses'))
    misses = []
    for c in sorted((c for c in due if not c['complete']), key=lambda c: (c['by'], c['id'] or '')):
        reason, note = why.get(c['id'], (NOT_GIVEN, None))
        misses.append({'id': c['id'], 'committor': c['committor'], 'card': c['card'], 'by': _iso(c['by']),
                       'delivered_on': _iso(c['delivered_on']), 'reason': reason, 'note': note})
    reasons = {k: 0 for k in REASONS + (NOT_GIVEN,)}
    for m in misses:
        reasons[m['reason']] += 1

    # --- the constraint log, then make-ready over the look-ahead
    clog = _constraint_log(registers, rows, by_item, dd)
    open_cons = {}
    for e in clog:
        if e['state'] == 'open' and e['card']:
            open_cons.setdefault(e['card'], []).append(e['id'])
    make_ready = []
    for cid in open_cards:
        it = by_item.get(cid)
        if it is not None and S.card_kind(it) == 'constraint':
            continue
        d, basis = start_date(cid)
        if d is None or (d - dd).days >= lookahead_days:
            continue
        cond = _str(S.field(it, 'conditions')) if it else None
        if not (open_cons.get(cid) or cond):
            continue
        make_ready.append({'id': cid, 'title': rows[cid].get('title'), 'holder': rows[cid].get('holder'),
                           'start': d.isoformat(), 'start_basis': basis, 'float': rows[cid].get('TF'),
                           'conditions': cond, 'constraints': sorted(x for x in open_cons.get(cid, []) if x)})
    make_ready.sort(key=lambda m: (m['start'], m['float'] is None, m['float'] if m['float'] is not None else 0, m['id']))

    # --- RYG and targets per unit
    units = sorted(i for i, r in rows.items() if r.get('type') == 'unit')
    ryg_rows = []
    for u in units:
        r = rows[u]
        tf = S.num(r.get('TF'), None)
        sig = ('done' if r.get('status') == 'complete' else 'unscheduled' if tf is None else
               'red' if tf < ryg[0] else 'yellow' if tf < ryg[1] else 'green')
        ryg_rows.append({'id': u, 'title': r.get('title'), 'TF': r.get('TF'), 'ryg': sig})
    treg = registers.get('targets') if isinstance(registers.get('targets'), dict) else {}
    targets = []
    for u in sorted(treg):
        t = S.num(treg[u], None)
        cur = S.num((rows.get(u) or {}).get('minutes'), None) if u in rows else None
        targets.append({'id': u, 'target_min': S.out_num(t), 'current_min': S.out_num(cur),
                        'variance_min': S.out_num(cur - t) if (cur is not None and t is not None) else None,
                        'missing': (None if u in rows else 'no such unit in the schedule run')})

    # --- the weekly work plan: the week holding the data date
    mon = _monday(dd)
    sun = mon + dt.timedelta(days=6)

    def in_week(d):
        return d is not None and mon <= d <= sun
    wills = [c for c in cs if c['live'] and (in_week(c['by']) or (c['kind'] == 'will' and c['by'] is None and in_week(c['ts'])))]
    w_due = [c for c in wills if c['due']]
    w_kept = [c for c in wills if c['complete']]
    day = chain.get('day') if chain else None
    weekly_plan = {
        'week': mon.isoformat(), 'from': mon.isoformat(), 'to': sun.isoformat(),
        'wills': [{'id': c['id'], 'card': c['card'], 'committor': c['committor'], 'kind': c['kind'],
                   'by': _iso(c['by']), 'state': c['state'], 'delivered_on': _iso(c['delivered_on'])}
                  for c in sorted(wills, key=lambda c: (c['by'] is None, _iso(c['by']) or '', c['id'] or ''))],
        'made': len(wills), 'due': len(w_due), 'kept_on_time': len(w_kept),
        'ppc': _ratio(sum(1 for c in w_due if c['complete']), len(w_due)),
        'should': copy.deepcopy({a: v.get('should') for a, v in day.items() if isinstance(v, dict)}) if isinstance(day, dict) else None,
        'can': copy.deepcopy({a: v.get('can') for a, v in day.items() if isinstance(v, dict)}) if isinstance(day, dict) else None,
        'misses_without_reason': sorted(m['id'] for m in misses if m['reason'] == NOT_GIVEN
                                        and any(c['id'] == m['id'] for c in wills)),
    }
    if chain is None:
        missing.append('chain: no leveled starts, no critical chain, no Should and Can of the day')

    basis = {
        'ppc': 'commitments whose by is on or before the data date and whose state is not released, declined or '
               'retracted; complete when delivered (claimed, dated by kept_ts) or kept on or before by; a kept '
               'commitment with no kept_ts is complete, its date unknown; weeks are the ISO Monday of by',
        'prc': 'the PPC rule over commitments on critical cards (critical in the run%s)'
               % (', or on the critical chain' if chain else '; no chain given'),
        'commitment_level': 'open critical cards whose start index is below %d (leveled start when the chain '
                            'gives one, else the early start, in working days); committed when a live commitment '
                            'is on the card or its stage is will' % COMMIT_WINDOW,
        'misses': 'each due commitment not complete; its reason is the latest misses-register line for it '
                  '(one of %d codes, any other given as other with the code kept in the note), else %s'
                  % (len(REASONS), NOT_GIVEN),
        'constraint_log': 'the constraints register first, then predecessor cards of kind constraint, then a '
                          "card's own resource, information or agreement constraint; overdue when open and "
                          'need_by is before the data date',
        'make_ready': 'open cards starting fewer than %s calendar days after the data date with an open '
                      'constraint or conditions; sorted by start, float, id' % S.out_num(lookahead_days),
        'ryg': 'per unit: done when complete; red when total float < %s, yellow when < %s, else green'
               % (S.out_num(ryg[0]), S.out_num(ryg[1])),
        'targets': 'per unit in the targets register: its minutes in the run less its target minutes'
                   if treg else 'no targets register',
        'weekly_plan': 'the Monday-to-Sunday week holding the data date; its Wills are live commitments whose by '
                       'falls in it (a Will with no by, by its ts); PPC over those due by the data date'
                       + ('' if isinstance(day, dict) else '; no chain day given, so no Should and Can'),
    }
    return {'v': 1, 'engine': ENGINE, 'data_date': dd.isoformat(),
            'lookahead_days': S.out_num(lookahead_days), 'ryg_thresholds': [S.out_num(ryg[0]), S.out_num(ryg[1])],
            'ppc': ppc, 'prc': prc, 'commitment_level': commitment_level,
            'misses': misses, 'reasons': reasons, 'constraint_log': clog, 'make_ready': make_ready,
            'ryg': ryg_rows, 'targets': targets, 'weekly_plan': weekly_plan,
            'missing': missing, 'basis': basis}
