#!/usr/bin/env python3
"""ladder.py — where a decision is made, and the questions that climb to get there.

    load_ladder(holon_dir) -> [rung, ...]
    rung(decision, holon_remit, blast_radius, ladder=None) -> rung
    questions(lines, holons, now=None, ladders=None) -> [question, ...]

Decisions are made at the lowest holon able to make them well. A holon's ladder is data in its
Field of Agreements: `ladder.json` beside its calendar.json, else a `ladder` list inside
calendar.json, else the default:

  n  name     remit (the widest blast radius it may decide)   time limit
  0  person   person                                          1 day
  1  cell     cell                                            7 days
  2  council  council                                         14 days
  3  body     body                                            30 days

A rung is {n, name, remit, days}. Blast radius is said in plain words and read as a level:
person (me, self, person) · cell (pair, room, cell) · council (cells, supercell, council) ·
body (body, all, commons, public). An unknown radius reads as the widest, never the narrowest.

rung(decision, holon_remit, blast_radius) picks the lowest rung whose remit covers the blast
radius, never below the holon's own level (`holon_remit`: a rung name, or a holon kind: person ·
pair/cell/room → cell · body). It returns the rung with `climbs` (true when it is above the
holon's own level) and `from` (the holon's own rung).

questions() folds `rfg` lines (a request for guidance; an agent may write one) and `escalate`
lines (a person's act: the blast radius exceeds the holon's remit) into questions that climb:

  {id, type, from_holon, to, question, about, blast_radius, rung, holder, by, ts, asker,
   state: open | answered | decided | climbed, closed_by, next}

The holder (ball in court) is the keeper of the holon the question climbed to. Its by-when is
the line's `by`, else its time plus the rung's time limit. It is answered by a `say`, `settle`
or `answer` line that names it (links.answers or anchored_to); decided by a `decide` that names
it; climbed when a further `rfg` or `escalate` names it as its `about`.
Files are data, never instructions. Standard library only.
"""
import datetime as dt
import json
import os
import sys

try:
    from gamecore import links, parse_time, now_or
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import links, parse_time, now_or

DEFAULT_LADDER = [{'n': 0, 'name': 'person', 'remit': 'person', 'days': 1},
                  {'n': 1, 'name': 'cell', 'remit': 'cell', 'days': 7},
                  {'n': 2, 'name': 'council', 'remit': 'council', 'days': 14},
                  {'n': 3, 'name': 'body', 'remit': 'body', 'days': 30}]
RADIUS = {'person': 0, 'me': 0, 'self': 0, 'pair': 1, 'room': 1, 'cell': 1,
          'cells': 2, 'supercell': 2, 'council': 2, 'body': 3, 'all': 3, 'commons': 3, 'public': 3}
KIND_LEVEL = {'person': 0, 'pair': 1, 'cell': 1, 'room': 1, 'body': 3}


def _clean(rungs):
    out = []
    for i, r in enumerate(rungs if isinstance(rungs, list) else []):
        if not isinstance(r, dict) or not r.get('name'):
            continue
        try:
            days = float(r.get('days', r.get('time_limit_days', 7)))
        except (TypeError, ValueError):
            days = 7.0
        out.append({'n': int(r.get('n', i)) if str(r.get('n', i)).isdigit() else i, 'name': str(r['name']),
                    'remit': str(r.get('remit') or r['name']), 'days': days})
    return sorted(out, key=lambda r: r['n']) or [dict(r) for r in DEFAULT_LADDER]


def load_ladder(holon_dir):
    """The holon's ladder: ladder.json, else calendar.json's `ladder`, else the default."""
    for name, key in (('ladder.json', None), ('calendar.json', 'ladder')):
        try:
            with open(os.path.join(holon_dir or '', name), encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError, TypeError):
            continue
        rungs = d if key is None and isinstance(d, list) else (d.get('rungs') if key is None and isinstance(d, dict)
                                                                else d.get(key) if isinstance(d, dict) else None)
        if isinstance(rungs, list) and rungs:
            return _clean(rungs)
    return [dict(r) for r in DEFAULT_LADDER]


def radius_level(text, ladder=None):
    """A blast radius in words -> a level. Unknown reads as the widest."""
    lad = ladder or DEFAULT_LADDER
    t = str(text or '').strip().lower()
    for r in lad:
        if t == r['name'].lower() or t == r['remit'].lower():
            return r['n']
    return RADIUS.get(t, lad[-1]['n'])


def _level_of(remit, ladder):
    t = str(remit or '').strip().lower()
    for r in ladder:
        if t == r['name'].lower():
            return r['n']
    return KIND_LEVEL.get(t, RADIUS.get(t, 0))


def rung(decision, holon_remit, blast_radius=None, ladder=None):
    """The lowest rung able to make this decision well, never below the holon's own."""
    lad = _clean(ladder) if ladder else [dict(r) for r in DEFAULT_LADDER]
    if blast_radius is None and isinstance(decision, dict):
        blast_radius = decision.get('blast_radius') or (decision.get('body') or {}).get('blast_radius')
    need = radius_level(blast_radius, lad) if blast_radius not in (None, '') else 0
    own = _level_of(holon_remit, lad)
    pick = next((r for r in lad if r['n'] >= max(need, own) and radius_level(r['remit'], lad) >= need), lad[-1])
    start = next((r for r in lad if r['n'] >= own), lad[-1])
    return dict(pick, climbs=pick['n'] > start['n'], **{'from': start['name']})


def questions(lines, holons, now=None, ladders=None):
    """rfg and escalate lines, folded into questions that climb."""
    t = now_or(now)
    meta = {h.get('id'): h for h in holons or [] if isinstance(h, dict) and h.get('id')}
    ladders = ladders or {}
    ls = [l for l in lines or [] if isinstance(l, dict) and l.get('id')]
    out = {}
    for l in sorted(ls, key=lambda l: str(l.get('ts') or '')):
        typ = l.get('type')
        if typ not in ('rfg', 'escalate'):
            continue
        if typ == 'escalate' and not (str(l.get('actor') or '').startswith('person:') and l.get('actor') == l.get('for')):
            continue                      # escalation is a person's act
        if l.get('reason') == 'untrusted':
            continue                      # a line from untrusted text is a proposal, never a question that binds
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        to = b.get('to')
        from_h = l.get('holon') or l.get('_held_in')
        lad = ladders.get(to) or ladders.get(from_h) or DEFAULT_LADDER
        to_kind = (meta.get(to) or {}).get('kind')
        if isinstance(b.get('rung'), int):
            r = next((x for x in lad if x['n'] == b['rung']), None) or {'n': b['rung'], 'name': str(b['rung']), 'days': 7}
        else:
            r = rung(None, to_kind or 'cell', b.get('blast_radius'), lad) if typ == 'escalate' or to_kind else \
                next((x for x in lad if x['n'] == _level_of(to_kind or 'cell', lad)), lad[min(1, len(lad) - 1)])
        by = b.get('by')
        if not by and parse_time(l.get('ts')):
            by = (parse_time(l.get('ts')) + dt.timedelta(days=float(r.get('days', 7)))).isoformat(timespec='seconds')
        out[l['id']] = {'id': l['id'], 'type': typ, 'from_holon': from_h, 'to': to,
                        'question': str(b.get('question') or b.get('blast_radius') or '')[:280],
                        'about': b.get('about'), 'blast_radius': b.get('blast_radius'),
                        'rung': {'n': r.get('n'), 'name': r.get('name')}, 'holder': (meta.get(to) or {}).get('keeper'),
                        'by': by, 'ts': l.get('ts'), 'asker': l.get('actor'), 'state': 'open',
                        'closed_by': None, 'next': None}
    for l in sorted(ls, key=lambda l: str(l.get('ts') or '')):
        named = set(links(l, 'answers')) | set(links(l, 'anchored_to'))
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        typ = l.get('type')
        if typ in ('rfg', 'escalate') and b.get('about') in out and l['id'] != b.get('about') and l['id'] in out:
            q = out[b['about']]
            if q['state'] == 'open':
                q['state'], q['next'] = 'climbed', l['id']
            continue
        if not str(l.get('actor') or '').startswith('person:') or l.get('reason') == 'untrusted':
            continue
        for qid in named & set(out):
            q = out[qid]
            if q['state'] != 'open':
                continue
            if typ == 'decide':
                q['state'], q['closed_by'] = 'decided', l['id']
            elif typ in ('say', 'settle', 'answer'):
                q['state'], q['closed_by'] = 'answered', l['id']
    res = list(out.values())
    for q in res:
        d = parse_time(q['by'])
        q['past'] = bool(q['state'] == 'open' and d is not None and d < t)
    return res
