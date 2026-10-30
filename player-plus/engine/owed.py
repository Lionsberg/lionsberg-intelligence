#!/usr/bin/env python3
"""owed.py — what is owed, computed from the record, never remembered.

    owed(items, actor=None, holon=None, now=None, horizon_days=2) -> {"entries": [...], "proposals": [...]}

Across every holon the items come from, it lists what waits on whom:

  commitment  an open commitment past its by-when, or due within the horizon (default two days)
  request     a request no one has answered yet
  thread      a thread whose last line is not the holder's (addressed to them, or one they spoke in)
  ratify      a decision made and waiting for a person to ratify it (the holon's keeper unless named)
  decide      a proposal put to a person by name, waiting for their decision
  claim       a claim whose time ran out while the card is still not done
  handoff     a body (bodies.fold) finished with a handoff no person has reviewed: owed by the
              person the body answers for, "review this handoff · N min" (N from review_min)
  question    an `rfg` or `escalate` past its by-when, unanswered: owed by the holon it climbed to,
              the ball in its keeper's court (from ladder.questions)

Each entry: kind · id · holon · title · holder · status (past | near | waiting) · due · age_days ·
minutes (an estimate of what answering takes). Lines an agent wrote for a reason that came from
untrusted text are never owed: they come back under "proposals" for a person to take up or let go.
A pushed thread or request past its push's `expires` folds as retracted and is not owed.

  python3 -I owed.py ITEMS.json [--actor person:x] [--holon ID] [--now ISO] [--json]
"""
import argparse
import json
import sys

try:
    from gamecore import (normalize, field, links, parse_time, now_or, days_between, is_untrusted,
                          item_id, holon_of, commitment_status, keeper_of, DONE_STATES, holon_names)
except ImportError:                                   # run from elsewhere: import beside this file
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, parse_time, now_or, days_between, is_untrusted,
                          item_id, holon_of, commitment_status, keeper_of, DONE_STATES, holon_names)

MINUTES = {'commitment': 5, 'request': 5, 'thread': 3, 'ratify': 5, 'decide': 5, 'claim': 2, 'question': 10}


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    return [x for x in v if isinstance(x, str) and x] if isinstance(v, (list, tuple)) else []


def _thread_lines(t):
    ls = field(t, 'lines')
    return [x for x in ls if isinstance(x, dict)] if isinstance(ls, list) else []


def _retracted(it, t):
    p = field(it, 'push')
    e = parse_time(p.get('expires')) if isinstance(p, dict) else None
    return e is not None and e < t


def thread_view(t):
    """last_actor, last_ts, settled, participants, to — from the thread item."""
    ls = _thread_lines(t)
    last = max(ls, key=lambda x: str(x.get('ts') or '')) if ls else {}
    last_actor = field(t, 'last_actor') or last.get('actor') or (None if ls else field(t, 'actor'))
    last_ts = field(t, 'last_ts') or last.get('ts') or (None if ls else field(t, 'ts'))
    settled = bool(field(t, 'settled')) or str(last.get('type') or '').lower() == 'settle' \
        or str(field(t, 'state') or '').lower() in ('settled', 'closed', 'done')
    parts = {x.get('actor') for x in ls if x.get('actor')}
    if field(t, 'actor'):
        parts.add(field(t, 'actor'))
    return {'last_actor': last_actor, 'last_ts': last_ts, 'settled': settled,
            'participants': sorted(parts), 'to': _as_list(field(t, 'to'))}


def owed(items, actor=None, holon=None, now=None, horizon_days=2, holons=None, questions=None, bodies=None):
    """What is owed, per actor or holon (or everyone, when neither is given). `questions` are
    ladder.questions(): an open one past its by-when is owed by the holon it climbed to."""
    norm = normalize(items)
    t = now_or(now)
    cards = {item_id(c): c for c in norm.get('card', [])}
    entries, proposals = [], []

    def title_of(it):
        tt = field(it, 'title') or field(it, 'text') or field(it, 'what')
        if not tt:
            for cid in [field(it, 'card')] + links(it, 'anchored_to') + links(it, 'answer'):
                if isinstance(cid, str) and cid in cards:
                    return field(cards[cid], 'title') or cid[:8]
        return (str(tt) if tt else item_id(it)[:8])[:120]

    def add(kind, it, holder, status, due=None, since=None):
        entries.append({'kind': kind, 'id': item_id(it), 'holon': holon_of(it), 'title': title_of(it),
                        'holder': holder, 'status': status, 'due': due,
                        'age_days': days_between(since or field(it, 'ts'), t), 'minutes': MINUTES[kind]})

    def propose(kind, it):
        proposals.append({'kind': kind, 'id': item_id(it), 'holon': holon_of(it),
                          'title': title_of(it),
                          'proposer': field(it, 'actor'), 'for': field(it, 'for'),
                          'note': 'its reason came from text the agent read; a person decides'})

    for c in norm.get('commitment', []):
        if is_untrusted(c):
            propose('commitment', c); continue
        status, _ = commitment_status(c, t)
        if status not in ('open', 'broken'):
            continue
        due = field(c, 'by')
        d = days_between(t, due)
        if status == 'broken' or (d is not None and d <= horizon_days):
            add('commitment', c, keeper_of(c), 'past' if status == 'broken' else 'near', due)

    # requests are cards the fold opened with asked=request; open means not yet answered
    for c in norm.get('card', []):
        if is_untrusted(c):
            continue
        if str(field(c, 'asked') or '') == 'request' and str(field(c, 'state') or '').lower() == 'open' \
                and not _retracted(c, t):
            add('request', c, field(c, 'holder'), 'waiting', field(c, 'by'))
    for r in norm.get('request', []):                 # a request item, when a fold keeps them apart
        if is_untrusted(r):
            propose('request', r); continue
        st = str(field(r, 'state') or '').lower()
        if field(r, 'answered') or st in DONE_STATES | {'answered', 'taken'}:
            continue
        for h in _as_list(field(r, 'to')) or [None]:
            add('request', r, h, 'waiting', field(r, 'by'))

    for th in norm.get('thread', []):
        if is_untrusted(th):
            propose('thread', th); continue
        if _retracted(th, t):
            continue                                  # a push past its expires folds as retracted
        v = thread_view(th)
        if v['settled']:
            continue
        holders = v['to'] or [p for p in v['participants']]
        for h in holders:
            if h and h != v['last_actor']:
                add('thread', th, h, 'waiting', None, v['last_ts'])

    names = holon_names(norm, holons)
    for d in norm.get('decision', []):
        if is_untrusted(d):
            propose('decision', d); continue
        st = str(field(d, 'state') or '').lower()
        if st == 'decided' and not field(d, 'ratified_by'):
            ratifier = field(d, 'ratifier') or names.get(holon_of(d), {}).get('keeper')
            add('ratify', d, ratifier, 'waiting', field(d, 'by'))
        elif st == 'proposed':
            for h in _as_list(field(d, 'to')) + _as_list(field(d, 'holder')):
                add('decide', d, h, 'waiting', field(d, 'by'))

    for it in norm.get('untrusted', []):              # the fold's proposals: lines from untrusted text
        propose(str(it.get('would_fold_into') or it.get('type') or 'line'), it)

    expired = [(c, field(c, 'claim_until') or field(c, 'until'), True) for c in norm.get('card', [])
               if str(field(c, 'state') or '').lower() == 'taken']
    expired += [(cl, field(cl, 'until'), False) for cl in norm.get('claim', [])]
    for it, until_s, is_card in expired:
        until = parse_time(until_s)
        if until is None or until >= t or is_untrusted(it):
            continue
        cid = field(it, 'card') or (links(it, 'anchored_to') or [None])[0]
        card = it if is_card else (cards.get(cid) if isinstance(cid, str) else None)
        if card is not None and str(field(card, 'state') or '').lower() in DONE_STATES:
            continue
        add('claim', it, field(it, 'holder') or field(it, 'actor'), 'past', until_s)

    for q in questions or []:
        if not isinstance(q, dict) or not q.get('past'):
            continue
        entries.append({'kind': 'question', 'id': q.get('id'), 'holon': q.get('to') or '',
                        'title': str(q.get('question') or '')[:120], 'holder': q.get('holder'), 'status': 'past',
                        'due': q.get('by'), 'age_days': days_between(q.get('ts'), t), 'minutes': MINUTES['question'],
                        'type': q.get('type'), 'from_holon': q.get('from_holon'), 'rung': q.get('rung')})

    for bd in bodies or []:                         # bodies.fold: a finished body's handoff, not yet reviewed
        if not isinstance(bd, dict) or not bd.get('handoff') or bd.get('reviewed'):
            continue
        if bd.get('state') not in ('handoff', 'done', 'stale', 'archived'):
            continue
        mins = bd.get('review_min') if isinstance(bd.get('review_min'), (int, float)) else 5
        entries.append({'kind': 'handoff', 'id': bd['handoff'], 'holon': bd.get('holon') or '',
                        'title': f"review this handoff · {mins:g} min", 'holder': bd.get('for'),
                        'status': 'waiting', 'due': None, 'age_days': days_between(bd.get('newest_line'), t),
                        'minutes': float(mins), 'body': bd.get('name'), 'task': bd.get('task'),
                        'asks_yes': bd.get('asks_yes', True), 'stale': bd.get('state') == 'stale'})

    if actor:
        entries = [e for e in entries if e['holder'] == actor]
        proposals = [p for p in proposals if p['for'] == actor or p['proposer'] == actor]
    if holon:
        entries = [e for e in entries if e['holon'] == holon]
        proposals = [p for p in proposals if p['holon'] == holon]
    order = {'past': 0, 'waiting': 1, 'near': 2}
    entries.sort(key=lambda e: (order.get(e['status'], 3), -(e['age_days'] or 0), e['id']))
    return {'as_of': t.isoformat(timespec='seconds'), 'actor': actor, 'holon': holon,
            'entries': entries, 'proposals': proposals}


def render(result, names=None):
    """Markdown, plain voice."""
    names = names or {}
    es = (result or {}).get('entries') or []
    who = result.get('actor') or result.get('holon') or 'everyone'
    out = [f'# What is owed — {who}', '', f'*As of {result.get("as_of")}. Computed from the record.*', '']
    if not es:
        out.append('Nothing is owed.')
    words = {'past': 'past its by-when', 'near': 'due soon', 'waiting': 'waiting'}
    for e in es:
        hn = names.get(e['holon'], {}).get('name', e['holon'][:8] if e['holon'] else '?')
        age = f", {e['age_days']:g} days" if e.get('age_days') is not None else ''
        due = f", by {e['due']}" if e.get('due') else ''
        out.append(f"- **{e['kind']}** · {e['title']} · {e['holder'] or 'no holder yet'} · "
                   f"{words.get(e['status'], e['status'])}{due}{age} · [{hn}]")
    ps = result.get('proposals') or []
    if ps:
        out += ['', '## Proposals, not owed', '',
                '*An agent wrote these for a reason that came from text it read. A person decides.*', '']
        out += [f"- {p['kind']} · {p['title']} · from {p['proposer']}" for p in ps]
    return '\n'.join(out) + '\n'


def _main(argv=None):
    ap = argparse.ArgumentParser(description='What is owed, computed from folded items (JSON).')
    ap.add_argument('items', help='a JSON file of folded items (the output of record.py fold)')
    ap.add_argument('--actor'); ap.add_argument('--holon'); ap.add_argument('--now')
    ap.add_argument('--horizon', type=float, default=2.0, help='days ahead a by-when counts as near')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        print(f'owed: cannot read {a.items}: {e}', file=sys.stderr); return 2
    r = owed(items, a.actor, a.holon, a.now, a.horizon)
    print(json.dumps(r, indent=1, ensure_ascii=False) if a.json else render(r, holon_names(normalize(items))))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
