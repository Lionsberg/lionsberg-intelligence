#!/usr/bin/env python3
"""ledger.py — TEA balances (time, energy, attention) and discernment totals.

    ledger(items, holon=None, lines=None) -> report
    render(report) -> Markdown

Each `tea` event says what its author spent on a card: minutes, energy (1-10), attention (1-10).
The ledger sums minutes and averages energy and attention per actor, per holon, per card and per
stream, and says for each event how far it has been witnessed:

  unwitnessed   no one has verified it yet
  keeper        the holon's keeper verified it
  supercell     a witness from a wider holon verified it as well

TEA points are not convertible: not into money, not into one another, not into rank. The output
says so every time.

Each actor's chain of `prev` links: engine.py passes what record.py found while reading (every
break named); given raw lines alone, record.py's own check is used when it offers one; otherwise
the report says the chain was not checked.

Discernment, lightly: a person's `discern` judgments counted, by route and by verdict (chosen,
corrected, rated). Discernment is human-only: it arrives under the person's own key (through the
HUD's act path); an agent's notes about a route ride on the route line and are not counted here.

  python3 -I ledger.py ITEMS.json [--holon ID] [--json]
"""
import argparse
import json
import sys

try:
    from gamecore import normalize, field, links, item_id, holon_of, holon_names, minutes_of, actor_kind
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import normalize, field, links, item_id, holon_of, holon_names, minutes_of, actor_kind

NOT_CONVERTIBLE = 'TEA points are not convertible: not into money, not into one another, not into rank.'


def _num(v, lo=None, hi=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if lo is not None and x < lo or hi is not None and x > hi:
        return None
    return x


def _acc():
    return {'events': 0, 'minutes': 0.0, '_e': [], '_a': [],
            'witness': {'unwitnessed': 0.0, 'keeper': 0.0, 'supercell': 0.0}}


def _close(a):
    e, at = a.pop('_e'), a.pop('_a')
    a['energy_avg'] = round(sum(e) / len(e), 2) if e else None
    a['attention_avg'] = round(sum(at) / len(at), 2) if at else None
    a['minutes'] = round(a['minutes'], 1)
    return a


def _witnesses(tea, norm):
    """[(actor, holon)] that witnessed this tea event."""
    out = []
    for k in ('witnessed_by', 'witnesses'):
        v = field(tea, k)
        for w in (v if isinstance(v, list) else [v] if v else []):
            if isinstance(w, str):
                out.append((w, holon_of(tea)))
            elif isinstance(w, dict):
                out.append((w.get('actor'), w.get('holon') or holon_of(tea)))
    tid = item_id(tea)
    for w in norm.get('witness', []):
        if tid and tid in links(w, 'witnesses'):
            out.append((field(w, 'actor'), holon_of(w)))
    return out


def witness_status(tea, norm, names):
    h = holon_of(tea)
    keeper = (names.get(h) or {}).get('keeper')
    spender = field(tea, 'actor')
    ws = [(a, wh) for a, wh in _witnesses(tea, norm) if a and a != spender]
    if any(wh and wh != h for _, wh in ws) or field(tea, 'supercell_by') or field(tea, 'witnessed_by_supercell'):
        return 'supercell'
    if str(field(tea, 'state') or '').lower() == 'witnessed':    # the fold moves to witnessed only on the keeper
        return 'keeper'
    if any(a == keeper for a, _ in ws) or (keeper is None and ws):
        return 'keeper'
    return 'unwitnessed'


def _chain(lines):
    if not lines:
        return {'checked': False, 'ok': None, 'note': 'no raw lines given; chain not checked'}
    try:
        import record
    except ImportError:
        return {'checked': False, 'ok': None, 'note': 'record.py not found beside this file; chain not checked'}
    for name in ('verify_chain', 'check_chain', 'chain_check'):   # never record.verify: that checks one signature
        fn = getattr(record, name, None)
        if callable(fn):
            try:
                r = fn(lines)
            except Exception as e:                   # a check that fails to run is said, never hidden
                return {'checked': False, 'ok': None, 'note': f'record.{name} could not run: {e}'}
            ok = r.get('ok') if isinstance(r, dict) else bool(r) if isinstance(r, bool) else not r
            return {'checked': True, 'ok': ok, 'by': f'record.{name}', 'detail': r if isinstance(r, (dict, list)) else None}
    return {'checked': False, 'ok': None, 'note': 'record.py offers no chain check; chain not checked'}


def ledger(items, holon=None, lines=None, holons=None, chain=None):
    """TEA balances and discernment totals. `chain` is a chain check already made (engine.py
    passes the read's broken_chain findings); else record.py's own check when lines are given."""
    norm = normalize(items)
    names = holon_names(norm, holons)
    cards = {item_id(c): c for c in norm.get('card', [])}
    by_actor, by_holon, by_card, by_stream, events = {}, {}, {}, {}, []
    for t in norm.get('tea', []):
        h = holon_of(t)
        if holon and h != holon:
            continue
        mins = minutes_of(t, 0)
        en, at = _num(field(t, 'energy'), 1, 10), _num(field(t, 'attention'), 1, 10)
        ws = witness_status(t, norm, names)
        cid = field(t, 'card') if isinstance(field(t, 'card'), str) else ''
        stream = field(cards.get(cid), 'stream') or '' if cid else ''
        for bucket, key in ((by_actor, field(t, 'actor') or '?'), (by_holon, h or '?'),
                            (by_card, cid or '(no card)'), (by_stream, stream or '(no stream)')):
            a = bucket.setdefault(key, _acc())
            a['events'] += 1; a['minutes'] += mins
            if en is not None: a['_e'].append(en)
            if at is not None: a['_a'].append(at)
            a['witness'][ws] += mins
        events.append({'id': item_id(t), 'holon': h, 'actor': field(t, 'actor'), 'card': cid or None,
                       'minutes': mins, 'energy': en, 'attention': at, 'witness': ws})
    disc = {'count': 0, 'by_route': {}, 'by_verdict': {}}
    for d in norm.get('discern', []):
        if holon and holon_of(d) != holon:
            continue
        v = str(field(d, 'state') or field(d, 'choice') or field(d, 'verdict') or 'routed').lower()
        if v == 'routed':
            continue                              # a route no Living Intelligence has judged yet
        by = field(d, 'discerned_by')
        if by and actor_kind(by) != 'person':
            continue                              # discernment is a person's own act; an agent's note rides the route line
        disc['count'] += 1
        r = field(d, 'model') or field(d, 'policy') or field(d, 'route') or '(no route)'
        disc['by_route'][str(r)] = disc['by_route'].get(str(r), 0) + 1
        disc['by_verdict'][v] = disc['by_verdict'].get(v, 0) + 1
    witness = {'unwitnessed': 0, 'keeper': 0, 'supercell': 0}
    for e in events:
        witness[e['witness']] += 1
    return {'holon': holon, 'convertible': False, 'note': NOT_CONVERTIBLE,
            'by_actor': {k: _close(v) for k, v in by_actor.items()},
            'by_holon': {k: _close(v) for k, v in by_holon.items()},
            'by_card': {k: _close(v) for k, v in by_card.items()},
            'by_stream': {k: _close(v) for k, v in by_stream.items()},
            'witness': witness, 'events': events,
            'chain': chain if isinstance(chain, dict) else _chain(lines), 'discernments': disc}


def render(r, names=None):
    names = names or {}
    out = ['# The TEA ledger', '', f"*{r.get('note', NOT_CONVERTIBLE)}*", '']
    for title, key, label in (('By actor', 'by_actor', lambda k: k),
                              ('By holon', 'by_holon', lambda k: names.get(k, {}).get('name', k[:8])),
                              ('By stream', 'by_stream', lambda k: k)):
        rows = r.get(key) or {}
        if not rows:
            continue
        out += [f'## {title}', '', '| | minutes | energy | attention | unwitnessed | keeper | supercell |',
                '|---|---|---|---|---|---|---|']
        for k, a in sorted(rows.items(), key=lambda kv: -kv[1]['minutes']):
            w = a['witness']
            out.append(f"| {label(k)} | {a['minutes']:g} | {a['energy_avg'] if a['energy_avg'] is not None else '—'} | "
                       f"{a['attention_avg'] if a['attention_avg'] is not None else '—'} | "
                       f"{w['unwitnessed']:g} | {w['keeper']:g} | {w['supercell']:g} |")
        out.append('')
    if not r.get('events'):
        out += ['No TEA recorded yet.', '']
    c = r.get('chain') or {}
    out.append('Chain: ' + ('verified' if c.get('ok') else 'a break was found' if c.get('checked') else c.get('note', 'not checked')) + '.')
    d = r.get('discernments') or {}
    if d.get('count'):
        out += ['', f"Discernment: {d['count']} judgments — " +
                ', '.join(f'{k} {v}' for k, v in sorted(d['by_verdict'].items())) + '.']
    return '\n'.join(out) + '\n'


def _main(argv=None):
    ap = argparse.ArgumentParser(description='TEA balances and discernment totals from folded items (JSON).')
    ap.add_argument('items'); ap.add_argument('--holon'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        print(f'ledger: cannot read {a.items}: {e}', file=sys.stderr); return 2
    r = ledger(items, a.holon)
    print(json.dumps(r, indent=1, ensure_ascii=False) if a.json else render(r, holon_names(normalize(items))))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
