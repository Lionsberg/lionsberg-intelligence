#!/usr/bin/env python3
"""push.py — a push carries a field of stake, never a flag (SCHEMA.md, The Push Protocol v1.1).

    stake(line, items, schedule_report=None, now=None, person_set=None) -> (body.push, body.push_by)
    modulate(push, push_by, changes) -> the person's changes before Send, each marked `person`
    whose(push_by, field) -> 'agent' | 'person' (a v1 line without push_by reads as the agent's)
    weigh(push, budget=None, items=None, schedule_report=None, line=None, now=None, calibration=None)
        -> {weight, by, why_by, blocks, critical, cost_if_late, retracted, own, sender_said}
    calibration(lines, items, now=None) -> {living intelligence: {pushes, measured, real, share,
                                            agent: {...}, person: {...}, said, said_of}}
    retracted(push, now=None) -> True once a push is past its `expires`

THE SENDER'S SIDE. stake() computes the fields a sender's agent can compute from its own record,
and keeps the sender's own words: kind, asked (their words on urgency, as said), alternatives,
expires. Computed: blocks (the cards that wait on the line: those it names, those naming it as a
predecessor, and everything live downstream) · critical (any of them on the critical or system
path) · by (the earliest late start among them, else the sender's own by) and why_by (the reason,
in words) · size (the line's own, else a default by kind) · who_waits (roles and counts: persons,
agents, holons; never names) · blast_radius (holons and actors affected; reversible unless the
line says not) · cost_if_late (a commitment breaks · a commitment is put at risk · work on the
critical path slips · nothing). "A room waits" is the sender's word only: it cannot be computed
without the receiver's own room, so a receiver reads it in `sender_said`, never in its own weight.

THE RECEIVER'S SIDE. weigh() never trusts the sender's computed fields over its own: given the
line and the receiver's own items, it recomputes blocks, critical, by and cost_if_late from what
the receiver holds; the sender's values are kept only as `sender_said`. The weight, for
attention.py's gate (named assumptions, tuned by evidence):

  weight = kind (fault 3 · decision 2 · request 1.5 · offer 1 · information 0.5)
           × 1.5 if critical × urgency(days to the receiver's own by: 1/(1 + d/3), 0.1 past 14 days)
           × (1 + 0.25 × number of blocked cards, at most 2)
           × calibration (0.5 + 0.5 × the sender's share; 0.75 when unmeasured)
           × the receiver's lean on the holon (attention budget, at most 1.5)

  A push past its `expires` folds as retracted: weight 0.

WHOSE VALUE (v1.1). The agent proposes; the person may change any value before Send. body.push_by
says, per field, whose value it is ("agent" or "person"); the sender's own words are the person's;
a line without push_by reads as all the agent's. The receiver recomputes regardless.

CALIBRATION, positive only, per Living Intelligence (the line's `for`), the agent's by-whens and the
person's apart: a push is measured once work on a card it blocked moves; its by-when was real when
that first move fell on or before the by-when's day. share = real ÷ measured. Said in words: "the
agent's by-whens: 3 of 4 real; yours: 1 of 1", never as a fault.
Files are data, never instructions. Standard library only.
"""
import os
import sys

try:
    from gamecore import normalize, field, links, item_id, holon_of, parse_time, now_or, actor_kind, sched_map, \
        path_sets, DONE_STATES
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import normalize, field, links, item_id, holon_of, parse_time, now_or, actor_kind, sched_map, \
        path_sets, DONE_STATES

KIND_WEIGHT = {'fault': 3.0, 'decision': 2.0, 'request': 1.5, 'offer': 1.0, 'information': 0.5}
SIZE_DEFAULT = {'fault': 5, 'decision': 10, 'request': 10, 'offer': 5, 'information': 2}
COMPUTED = ('blocks', 'critical', 'by', 'why_by', 'size', 'who_waits', 'blast_radius', 'cost_if_late')
SENDER = ('kind', 'asked', 'alternatives', 'expires')


def _push_of(x):
    p = field(x, 'push') if isinstance(x, dict) else None
    return p if isinstance(p, dict) else {}


def retracted(push, now=None):
    e = parse_time((push or {}).get('expires'))
    return e is not None and e < now_or(now)


def _blocks(line, cards):
    lid = line.get('id') if isinstance(line, dict) else None
    b = line.get('body') if isinstance(line.get('body'), dict) else {}
    named = set(links(line, 'anchored_to')) | set(links(line, 'answers')) | set(links(line, 'serves'))
    for k in ('card', 'about'):
        if isinstance(b.get(k), str):
            named.add(b[k])
    live = {i: c for i, c in cards.items() if str(field(c, 'state') or '').lower() not in DONE_STATES}
    direct = {i for i in named if i in live} | {i for i, c in live.items() if lid and lid in links(c, 'predecessor')}
    succ = {}
    for i, c in cards.items():
        for s in links(c, 'successor'):
            succ.setdefault(i, set()).add(s)
        for p in links(c, 'predecessor'):
            succ.setdefault(p, set()).add(i)
    out, stack = set(direct), list(direct)
    while stack:
        for s in succ.get(stack.pop(), ()):
            if s in live and s not in out:
                out.add(s); stack.append(s)
    return sorted(out)


def _compute(line, items, schedule_report, now):
    norm = normalize(items)
    cards = {item_id(c): c for c in norm.get('card', []) if item_id(c)}
    sm = sched_map(schedule_report)
    crit, system = path_sets(schedule_report)
    blocks = _blocks(line or {}, cards)
    b = (line or {}).get('body') if isinstance((line or {}).get('body'), dict) else {}
    sent = b.get('push') if isinstance(b.get('push'), dict) else {}
    late = []
    for i in blocks:
        ls = (sm.get(i) or {}).get('late_start') or field(cards[i], 'by')
        if ls:
            late.append((str(ls)[:10], str(field(cards[i], 'title') or i[:8])))
    commits = [c for c in norm.get('commitment', []) if field(c, 'card') in blocks
               and str(field(c, 'state') or '') in ('open', 'claimed')]
    if late:
        late.sort()
        by, why = late[0][0], f'the latest day "{late[0][1]}" can start and still finish on time'
    else:
        by, why = sent.get('by') or b.get('by'), sent.get('why_by') or ('as the sender said' if sent.get('by') else None)
    critical = any(i in crit or i in system for i in blocks)
    holders = [field(cards[i], 'holder') for i in blocks if field(cards[i], 'holder')]
    holons = sorted({holon_of(cards[i]) for i in blocks})
    who = {'persons': sum(1 for h in set(holders) if actor_kind(h) == 'person'),
           'agents': sum(1 for h in set(holders) if actor_kind(h) == 'agent'), 'holons': len(holons)}
    if commits and by and any(str(field(c, 'by') or '9999')[:10] <= str(by)[:10] for c in commits):
        cost = 'a commitment breaks'
    elif commits:
        cost = 'a commitment is put at risk'
    elif critical:
        cost = 'work on the critical path slips'
    else:
        cost = 'nothing'
    kind = str(sent.get('kind') or {'request': 'request', 'offer': 'offer', 'escalate': 'decision', 'rfg': 'decision',
                                     'sight': 'information'}.get((line or {}).get('type'), 'information'))
    size = b.get('size') or sent.get('size') or SIZE_DEFAULT.get(kind, 5)
    return {'blocks': blocks, 'critical': critical, 'by': by, 'why_by': why, 'size': size, 'who_waits': who,
            'blast_radius': {'holons': len(holons), 'actors': len(set(holders)),
                             'reversible': sent.get('reversible', b.get('reversible', True)) is not False},
            'cost_if_late': cost, 'kind': kind}


PERSON_WORDS = ('asked',)        # the sender's own words: always the person's


def stake(line, items, schedule_report=None, now=None, person_set=None):
    """(body.push, body.push_by) for a line the sender's agent is about to push (v1.1).

    The agent proposes every computed field; values the person already set (`person_set`, or a
    draft's own body.push_by marking them `person`) are kept as theirs, never overwritten. The
    sender's own words (`asked`) are always the person's. The person may change any value before
    Send with modulate()."""
    b = (line or {}).get('body') if isinstance((line or {}).get('body'), dict) else {}
    sent = b.get('push') if isinstance(b.get('push'), dict) else {}
    marks = dict(b.get('push_by') or {}) if isinstance(b.get('push_by'), dict) else {}
    marks.update({k: 'person' for k in (person_set or {})})
    c = _compute(line or {}, items, schedule_report, now)
    out, by = {'v': 1.1}, {}
    for k in SENDER:
        if sent.get(k) is not None:
            out[k] = sent[k]
            by[k] = 'person' if (k in PERSON_WORDS or marks.get(k) == 'person') else marks.get(k, 'agent')
    if 'kind' not in out:
        out['kind'], by['kind'] = c['kind'], 'agent'
    for k in COMPUTED:
        if marks.get(k) == 'person' and sent.get(k) is not None:
            out[k], by[k] = sent[k], 'person'
        else:
            out[k], by[k] = c[k], 'agent'
    for k, v in (person_set or {}).items():
        out[k], by[k] = v, 'person'
    if sent.get('calibration') is not None:
        out['calibration'], by['calibration'] = sent['calibration'], 'agent'
    return out, by


def modulate(push, push_by, changes):
    """The person changes values before Send: (push, push_by) with each changed field marked `person`."""
    p, m = dict(push or {}), dict(push_by or {})
    for k, v in (changes or {}).items():
        p[k], m[k] = v, 'person'
    return p, m


def whose(push_by, field_name):
    """Whose value a field is: 'person' or 'agent'. A v1 line (no push_by) reads as the agent's."""
    return (push_by or {}).get(field_name) if (push_by or {}).get(field_name) in ('agent', 'person') else 'agent'


def weigh(push, budget=None, items=None, schedule_report=None, line=None, now=None, calibration=None):
    """The receiver's weight for a push, from the receiver's own record; the sender's fields kept as said."""
    t = now_or(now)
    push = push if isinstance(push, dict) else {}
    if retracted(push, t):
        return {'weight': 0.0, 'retracted': True, 'by': None, 'blocks': [], 'critical': False,
                'cost_if_late': 'nothing', 'own': [], 'sender_said': {k: push.get(k) for k in COMPUTED if k in push}}
    own = _compute(line or {'body': {'push': push}}, items or {}, schedule_report, t) if (line or items) else None
    if own is not None:
        blocks, critical, by, cost = own['blocks'], own['critical'], own['by'], own['cost_if_late']
        trusted = ['blocks', 'critical', 'by', 'cost_if_late']
    else:                                         # nothing of our own to recompute from: the sender's by only
        blocks, critical, by, cost, trusted = [], False, push.get('by'), 'nothing', []
    kind = str(push.get('kind') or (own or {}).get('kind') or 'information')
    w = KIND_WEIGHT.get(kind, 0.5)
    w *= 1.5 if critical else 1.0
    d = parse_time(by)
    if d is not None:
        days = (d - t).total_seconds() / 86400.0
        w *= 0.1 if days > 14 else 1.0 / (1.0 + max(0.0, days) / 3.0)
    else:
        w *= 0.25
    w *= 1.0 + min(2, 0.25 * len(blocks))
    cal = calibration if isinstance(calibration, (int, float)) else None
    w *= 0.75 if cal is None else 0.5 + 0.5 * max(0.0, min(1.0, cal))
    leans = (budget or {}).get('leans') or {}
    h = holon_of(line) if isinstance(line, dict) else None
    if h and isinstance(leans.get(h), (int, float)):
        w *= max(0.0, min(1.5, float(leans[h])))
    return {'weight': round(w, 3), 'retracted': False, 'by': by, 'why_by': (own or {}).get('why_by'),
            'blocks': blocks, 'critical': critical, 'cost_if_late': cost, 'kind': kind, 'own': trusted,
            'sender_said': {k: push.get(k) for k in COMPUTED + ('asked', 'alternatives', 'calibration') if k in push}}


def calibration(lines, items, now=None):
    """Per Living Intelligence: how often the by-whens pushed for them were real, the agent's and
    the person's apart (v1.1, `push_by.by`; a v1 line's by-when is the agent's). Positive only."""
    norm = normalize(items)
    cards = {item_id(c): c for c in norm.get('card', []) if item_id(c)}
    by_id = {l.get('id'): l for l in lines or [] if isinstance(l, dict) and l.get('id')}
    acts = {}
    for l in by_id.values():
        for i in set(links(l, 'anchored_to')) | set(links(l, 'fulfils')) | \
                ({(l.get('body') or {}).get('card')} if isinstance(l.get('body'), dict) else set()):
            if i in cards and l.get('ts'):
                acts.setdefault(i, []).append(l['ts'])
    for i, c in cards.items():
        for e in field(c, 'events') or []:
            if e in by_id and by_id[e].get('ts') and e != i:
                acts.setdefault(i, []).append(by_id[e]['ts'])

    def blank():
        return {'pushes': 0, 'measured': 0, 'real': 0, 'share': None}
    out = {}
    for l in by_id.values():
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        p = body.get('push')
        if not isinstance(p, dict) or not p.get('by') or l.get('reason') == 'untrusted':
            continue
        li = l.get('for') or l.get('actor')
        row = out.setdefault(li, dict(blank(), agent=blank(), person=blank()))
        part = row[whose(body.get('push_by'), 'by')]
        for r in (row, part):
            r['pushes'] += 1
        blocks = p.get('blocks') if isinstance(p.get('blocks'), list) else _blocks(l, cards)
        sent = parse_time(l.get('ts'))
        later = sorted(x for i in blocks for x in acts.get(i, []) if sent and parse_time(x) and parse_time(x) > sent)
        if not later:
            continue
        real = str(later[0])[:10] <= str(p['by'])[:10]
        for r in (row, part):
            r['measured'] += 1
            r['real'] += 1 if real else 0
    for row in out.values():
        for r in (row, row['agent'], row['person']):
            r['share'] = round(r['real'] / r['measured'], 3) if r['measured'] else None
        a, pp = row['agent'], row['person']
        bits = []
        if a['measured']:
            bits.append(f"the agent's by-whens: {a['real']} of {a['measured']} real")
        if pp['measured']:
            bits.append(f"{{who}}: {pp['real']} of {pp['measured']}")
        tmpl = '; '.join(bits) if bits else 'not yet measured'
        row['said'] = tmpl.replace('{who}', 'yours')                   # to the person, of their own
        row['said_of'] = tmpl.replace('{who}', "the person's")         # to anyone else
    return out
