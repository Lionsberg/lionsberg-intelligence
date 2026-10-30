#!/usr/bin/env python3
"""kept.py — commitments kept, per holon and per actor, over a window.

    kept(items, holon=None, actor=None, window_days=7, now=None) -> report

A commitment counts in the window when it was made in it or fell due in it. Each is one of:

  kept              the keeper said it was kept and a witness verified it
  kept-unwitnessed  the keeper said it was kept; no witness yet
  broken            its by-when passed and it was not kept (rendered as "not kept by the by-when")
  released          let go openly, before or after the by-when
  returned          handed back
  open              not yet due

The gap per commitment is the keeping time minus the by-when, in days; negative is early. The
share is kept (witnessed) ÷ (kept + kept-unwitnessed + broken): a commitment counts as kept once
its witness verifies it. `share_claimed` beside it counts the keeper's own claims too. Learning lines are the `learn` events the fold
attached to a commitment or its card. The words describe what happened to a commitment, never a person.

  python3 -I kept.py ITEMS.json [--holon ID] [--actor person:x] [--days 7] [--now ISO] [--json]
"""
import argparse
import datetime as dt
import json
import sys

try:
    from gamecore import (normalize, field, links, parse_time, now_or, item_id, holon_of,
                          commitment_status, keeper_of, holon_names)
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, parse_time, now_or, item_id, holon_of,
                          commitment_status, keeper_of, holon_names)

KEYS = ('made', 'kept', 'kept_unwitnessed', 'broken', 'released', 'returned', 'open')


def _tally():
    return {k: 0 for k in KEYS}


def _share(t):
    due = t['kept'] + t['kept_unwitnessed'] + t['broken']
    t['share'] = round(t['kept'] / due, 3) if due else None                     # witnessed, per the contract
    t['share_claimed'] = round((t['kept'] + t['kept_unwitnessed']) / due, 3) if due else None
    return t


def kept(items, holon=None, actor=None, window_days=7, now=None, start=None):
    """Commitments kept over the window ending now (or from `start` to now)."""
    norm = normalize(items)
    t = now_or(now)
    t0 = parse_time(start) if start else t - dt.timedelta(days=float(window_days or 7))
    if t0 is None:
        t0 = t - dt.timedelta(days=7)
    cards = {item_id(c): c for c in norm.get('card', [])}
    by_holon, by_actor, rows = {}, {}, []
    for c in norm.get('commitment', []):
        if holon and holon_of(c) != holon:
            continue
        k = keeper_of(c)
        if actor and k != actor:
            continue
        made = parse_time(field(c, 'ts'))
        due = parse_time(field(c, 'by'))
        in_window = (made is not None and t0 <= made <= t) or (due is not None and t0 <= due <= t)
        if not in_window:
            continue
        status, gap = commitment_status(c, t)
        cid = field(c, 'card')
        title = field(c, 'title') or (field(cards.get(cid), 'title') if isinstance(cid, str) else None) \
            or item_id(c)[:8]
        rows.append({'id': item_id(c), 'holon': holon_of(c), 'keeper': k, 'title': title,
                     'by': field(c, 'by'), 'witness': field(c, 'witness'), 'status': status,
                     'gap_days': gap})
        key = status.replace('-', '_')
        for bucket, name in ((by_holon, holon_of(c)), (by_actor, k or '?')):
            tl = bucket.setdefault(name, _tally())
            tl['made'] += 1 if made is not None and t0 <= made <= t else 0
            tl[key] += 1
    learning, seen_l = [], set()
    row_ids = {r['id'] for r in rows}
    for c in norm.get('commitment', []):         # the fold appends learn lines to what they came from
        if item_id(c) not in row_ids:
            continue
        cid = field(c, 'card')
        for src in (c, cards.get(cid) if isinstance(cid, str) else None):
            for ln in (field(src, 'learnings') or []) if isinstance(src, dict) else []:
                if isinstance(ln, dict) and ln.get('id') not in seen_l:
                    seen_l.add(ln.get('id'))
                    learning.append({'id': ln.get('id'), 'holon': holon_of(c), 'actor': ln.get('actor'),
                                     'text': str(ln.get('text') or '')[:280], 'about': item_id(c)})
    for ln in norm.get('learn', []):              # learn items, when a fold keeps them apart
        lt = parse_time(field(ln, 'ts'))
        if item_id(ln) in seen_l or lt is None or not (t0 <= lt <= t) or (holon and holon_of(ln) != holon):
            continue
        learning.append({'id': item_id(ln), 'holon': holon_of(ln), 'actor': field(ln, 'actor'),
                         'text': str(field(ln, 'text') or '')[:280], 'about': field(ln, 'commitment')})
    total = _tally()
    for tl in by_holon.values():
        for k2 in KEYS:
            total[k2] += tl[k2]
    return {'window': {'from': t0.isoformat(timespec='seconds'), 'to': t.isoformat(timespec='seconds')},
            'total': _share(total),
            'by_holon': {h: _share(v) for h, v in by_holon.items()},
            'by_actor': {a: _share(v) for a, v in by_actor.items()},
            'commitments': sorted(rows, key=lambda r: (r['holon'], str(r['by'] or ''))),
            'learning': learning}


WORDS = {'kept': 'kept, witnessed', 'kept-unwitnessed': 'kept, awaiting a witness',
         'broken': 'not kept by the by-when', 'released': 'released', 'returned': 'returned',
         'open': 'open'}


def gap_words(g):
    if g is None:
        return ''
    if abs(g) < 0.5:
        return 'on the day'
    return f'{abs(g):g} days {"after" if g > 0 else "before"} the by-when'


def render(r, names=None):
    names = names or {}
    w = r.get('window') or {}
    tot = r.get('total') or {}
    out = [f"# Commitments kept — {w.get('from', '')[:10]} to {w.get('to', '')[:10]}", '']
    share = tot.get('share')
    due = tot.get('kept', 0) + tot.get('kept_unwitnessed', 0) + tot.get('broken', 0)
    out.append(f"{tot.get('kept', 0)} of {due} commitments due were kept and witnessed"
               + (f" ({share:.0%})." if share is not None else '.')
               + (f" {tot.get('kept_unwitnessed', 0)} await a witness." if tot.get('kept_unwitnessed') else '')
               + (f" {tot.get('released', 0)} released." if tot.get('released') else ''))
    for h, tl in (r.get('by_holon') or {}).items():
        hn = names.get(h, {}).get('name', h[:8] if h else '?')
        s = f"{tl['share']:.0%}" if tl.get('share') is not None else 'nothing due yet'
        out.append(f"- {hn}: {s} · made {tl['made']} · open {tl['open']}")
    out += ['', '## Each commitment', '']
    for c in r.get('commitments') or []:
        g = gap_words(c.get('gap_days'))
        out.append(f"- {c['title']} · {c['keeper']} · by {c['by']} · {WORDS.get(c['status'], c['status'])}"
                   + (f' · {g}' if g else ''))
    if r.get('learning'):
        out += ['', '## What we learned', ''] + [f"- {l['text']}" for l in r['learning']]
    return '\n'.join(out) + '\n'


def _main(argv=None):
    ap = argparse.ArgumentParser(description='Commitments kept over a window, from folded items (JSON).')
    ap.add_argument('items'); ap.add_argument('--holon'); ap.add_argument('--actor')
    ap.add_argument('--days', type=float, default=7.0); ap.add_argument('--now')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        print(f'kept: cannot read {a.items}: {e}', file=sys.stderr); return 2
    r = kept(items, a.holon, a.actor, a.days, a.now)
    print(json.dumps(r, indent=1, ensure_ascii=False) if a.json else render(r, holon_names(normalize(items))))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
