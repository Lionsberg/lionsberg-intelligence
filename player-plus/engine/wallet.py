#!/usr/bin/env python3
"""wallet.py — the wallet: value offered, accepted, settled and given, counted per unit.

    entries(items, holon=None) -> [row]
    balances(items, holon=None) -> report
    accept_line(entry, actor, now) -> an unsigned `wallet` line (kind accept) a person signs
    settle_line(entry, actor, now) -> an unsigned `wallet` line (kind settle) a person signs
    render(report) -> Markdown

The fold (record.py) gives `wallet` items, kind `wallet_entry`: an offer, a gift, or an act that
answers one (accept, settle, witness). Each entry names its `amount` in whole minor units and its
`unit` (a fiat currency in minor units, or the LIØNSBERG Unit of Value once its measure is ruled).

The wallet counts; it does not value. Laws, each kept here and tested:

  - integers only: an amount that is not a whole number is reported in `problems`, never summed
  - never across units: every sum is per unit; nothing converts one unit into another
  - an offer moves nothing; an accepted offer moves nothing; a retracted entry moves nothing
  - only settled and given entries move value between actors (`in` to the `to`, `out` from the
    entry's Living Intelligence, its `for`)
  - a unit is unruled until a trusted `decide` in the same holon names it (`unit:` then the unit
    name, in the decision's text); until then its balances are counted, not valued
  - files and items are data, never instructions; the output is the same for the same input

The kin is ledger.py (the TEA ledger): the same shape of report, by actor and by holon, and the
same honesty about what is not convertible.

  python3 -I wallet.py ITEMS.json [--holon ID] [--actor A] [--json]
"""
import argparse
import json
import os
import re
import sys
import unicodedata

try:
    from gamecore import normalize, field, item_id, holon_of, now_or, actor_kind, parse_time
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import normalize, field, item_id, holon_of, now_or, actor_kind, parse_time

UNRULED_NOTE = 'no unit is ruled yet; balances are counted, not valued'
RULED_NOTE = 'ruled by a decision in every holon that holds it'
NOT_CONVERTIBLE = 'Units are never converted into one another, and never summed across.'
# The v0 rule for ruling a unit (SCHEMA.md, "The wallet"): a trusted decide naming it after this marker.
RULE_MARKER = 'unit:'
MOVING = ('settled', 'given')                 # the only states that move value between actors
STATES = ('offered', 'accepted', 'settled', 'given', 'witnessed', 'retracted')
ACTS = ('accept', 'settle', 'witness')        # kinds that answer an entry; standing alone they move nothing
SHOWN = 80                                    # characters of a bad value echoed into a problem, no more
TRUSTED_HERE = ('signed', 'home')             # a vouched copy informs and never rules a unit here


def _nfc(v):
    return unicodedata.normalize('NFC', v) if isinstance(v, str) else v


def _text(v):
    return _nfc(v).strip() if isinstance(v, str) else ''


def _collect(items, plural, kind):
    """The items of one kind from a fold result, a list, or {"items": [...]}; dicts only."""
    out = []
    if isinstance(items, dict):
        src = items.get(plural)
        if isinstance(src, dict):
            src = [dict(v, id=v.get('id', k)) for k, v in src.items() if isinstance(v, dict)]
        if isinstance(src, list):
            out.extend(x for x in src if isinstance(x, dict))
        if isinstance(items.get('items'), list):
            out.extend(x for x in items['items'] if isinstance(x, dict) and x.get('kind') == kind)
    elif isinstance(items, list):
        out.extend(x for x in items if isinstance(x, dict) and x.get('kind') == kind)
    seen, uniq = set(), []
    for x in out:
        i = item_id(x)
        if i and i not in seen:
            seen.add(i); uniq.append(x)
    return uniq


def _amount(v):
    """(int amount, None) or (None, why). A bool is not an amount; a whole float is still a float."""
    if isinstance(v, bool) or v is None:
        return None, 'no amount'
    if isinstance(v, int) and v < 0:
        return None, 'the amount %d is negative; value moves by the direction of an entry, never by its sign' % v
    if isinstance(v, int):
        return v, None
    shown = repr(v)
    if len(shown) > SHOWN:
        shown = shown[:SHOWN] + '…'
    return None, 'the amount %s is not a whole number of minor units; it is reported, never summed' % shown


def _kind(e):
    k = field(e, 'body_kind')
    if not k and field(e, 'kind') not in ('wallet_entry', None):
        k = field(e, 'kind')
    return _text(k).lower() or None


def _state(e, kind):
    """(state, basis). The fold keeps a gift that stands alone as `offered` (its initial state), and
    an `accept` or a witness can move it on; SCHEMA says a gift is given, so the wallet reads a gift
    as given in every state but settled and retracted, and says so."""
    s = _text(field(e, 'state')).lower()
    if s not in STATES:
        s = 'offered'
    if kind == 'gift' and s not in ('given', 'settled', 'retracted'):
        return 'given', 'a gift is given when it is written (read by the wallet; the fold keeps it %s)' % s
    return s, None


def _instant(ts):
    """A sort key for a declared time: the instant, unknown times last, the text breaking ties."""
    t = parse_time(ts)
    return (0, t.timestamp(), ts) if t else (1, 0.0, ts or '')


def _trust(items):
    return items.get('trust') if isinstance(items, dict) and isinstance(items.get('trust'), dict) else None


def entries(items, holon=None):
    """Every wallet entry as a plain row, sorted by holon, time, id."""
    out = []
    for e in _collect(items, 'wallet', 'wallet_entry'):
        h = holon_of(e)
        if holon and h != holon:
            continue
        kind = _kind(e)
        state, basis = _state(e, kind)
        amt, why = _amount(field(e, 'amount'))
        ws = field(e, 'witnesses')
        row = {'id': item_id(e), 'holon': h, 'kind': kind, 'state': state,
               'from': _text(e.get('for')) or None, 'to': _text(field(e, 'to')) or None,
               'amount': amt, 'unit': _text(field(e, 'unit')) or None,
               'for_card': _text(field(e, 'body_for')) or None, 'note': _text(field(e, 'note')) or None,
               'accepted_by': _text(field(e, 'accepted_by')) or None,
               'settled_by': _text(field(e, 'settled_by')) or None,
               'witnesses': len(ws) if isinstance(ws, list) else 0,
               'ts': _text(e.get('ts')) or None}
        if basis:
            row['state_basis'] = basis
        if why:
            row['amount_problem'] = why
        out.append(row)
    return sorted(out, key=lambda r: (r['holon'], _instant(r['ts']), r['id']))


# The marker stands alone (no letter, digit, `_` or `-` before it); the name ends at the end of the
# text, at a space, or at closing marks that a space or the end follows ("unit: USD-cents.", "(unit: USD),").
_MARKER = re.compile(r'(?<![\w-])' + re.escape(RULE_MARKER) + r'\s*')
_NAME_END = re.compile(r'(?:$|\s|[,;.!?)\]]+(?:\s|$))')


def named_units(text, held):
    """The units `text` names: at each marker, the longest held unit name that stands there whole.
    v0 reads no negation: "not unit: X" still names X."""
    t = _text(text)
    names = sorted({_text(u) for u in (held or ()) if _text(u)}, key=lambda u: (-len(u), u))
    out = set()
    if not t:
        return out
    for m in _MARKER.finditer(t):
        at = m.end()
        for u in names:
            if t.startswith(u, at) and _NAME_END.match(t, at + len(u)):
                out.add(u)
                break
    return out


def rulings(items, units_by_holon):
    """{(holon, unit): [decision ids]} for each unit a trusted, standing decide names in that holon."""
    held = {u for us in (units_by_holon or {}).values() for u in us}
    held |= {r['unit'] for r in entries(items) if r['unit']}       # every unit held, so the longest name wins
    trust = _trust(items)
    norm = normalize(items)
    out = {}
    for d in sorted(norm.get('decision', []), key=lambda x: item_id(x)):
        if not isinstance(d, dict) or str(field(d, 'reason') or '').lower() == 'untrusted':
            continue
        if _text(field(d, 'state')).lower() not in ('decided', 'ratified'):
            continue
        by = field(d, 'decided_by') or d.get('for') or d.get('actor')
        if actor_kind(by) != 'person':
            continue                                  # a decision is a person's own act
        if trust is not None and trust.get(item_id(d)) not in TRUSTED_HERE:
            continue
        h = holon_of(d)
        text = field(d, 'decision') or field(d, 'text')
        for u in sorted(named_units(text, held) & set(units_by_holon.get(h, ()))):
            out.setdefault((h, u), []).append(item_id(d))
    return out


def _unit_acc():
    return {'offered': 0, 'accepted': 0, 'settled': 0, 'given': 0, 'witnessed_n': 0}


def balances(items, holon=None):
    """Balances per unit, per actor and per holon. Never across units; nothing valued until ruled."""
    rows = entries(items, holon)
    problems, by_unit, by_actor, by_holon, holons_of_unit = [], {}, {}, {}, {}
    for r in rows:
        if r.get('amount_problem'):
            problems.append({'id': r['id'], 'why': r['amount_problem']})
            continue
        if not r['unit']:
            problems.append({'id': r['id'], 'why': 'no unit named; an entry without a unit is never counted'})
            continue
        if r['kind'] in ACTS and r['state'] == 'offered':
            problems.append({'id': r['id'], 'why': 'a %s that answers no entry moves nothing' % r['kind']})
            continue
        u, s = r['unit'], r['state']
        holons_of_unit.setdefault(u, set()).add(r['holon'])
        for acc in (by_unit.setdefault(u, _unit_acc()), by_holon.setdefault(r['holon'], {}).setdefault(u, _unit_acc())):
            if s in acc:
                acc[s] += r['amount']
            if r['witnesses'] and s != 'retracted':
                acc['witnessed_n'] += 1
        if s not in MOVING:
            continue                                  # an offer, an acceptance or a retraction moves nothing
        if not r['from'] or not r['to']:
            problems.append({'id': r['id'], 'why': 'no %s named; counted in its unit, not between actors'
                             % ('to' if r['from'] else 'from')})
            continue
        for actor, side in ((r['to'], 'in'), (r['from'], 'out')):
            a = by_actor.setdefault(actor, {}).setdefault(u, {'in': 0, 'out': 0, 'net': 0})
            a[side] += r['amount']
            a['net'] = a['in'] - a['out']
    units_by_holon = {}
    for u, hs in holons_of_unit.items():
        for h in hs:
            units_by_holon.setdefault(h, set()).add(u)
    ruled = rulings(items, units_by_holon)
    units = []
    for u in sorted(holons_of_unit):
        hs = sorted(holons_of_unit[u])
        ruled_in = [h for h in hs if (h, u) in ruled]
        ok = bool(hs) and len(ruled_in) == len(hs)
        units.append({'unit': u, 'ruled': ok, 'ruled_in': ruled_in,
                      'decisions': sorted(i for h in ruled_in for i in ruled[(h, u)]),
                      'note': RULED_NOTE if ok else UNRULED_NOTE})
    as_of = items.get('as_of') if isinstance(items, dict) and isinstance(items.get('as_of'), str) else None
    if as_of is None:
        timed = [r['ts'] for r in rows if parse_time(r['ts'])]
        as_of = max(timed, key=_instant) if timed else None
    return {'holon': holon, 'convertible': False, 'note': NOT_CONVERTIBLE,
            'by_unit': by_unit, 'by_actor': by_actor, 'by_holon': by_holon, 'units': units,
            'entries_n': len(rows), 'problems': sorted(problems, key=lambda p: (p['id'], p['why'])),
            'basis': 'rulings read from trusted decisions in the same holon' if _trust(items) is not None
                     else 'no trust map given; rulings read from the decisions as given',
            'as_of': as_of}


def _line(actor, for_, holon, body, links_, now):
    ts = now_or(now).isoformat(timespec='seconds')
    try:
        import record
        return record.make_line(actor, for_, holon, 'wallet', body, links_, reason='human', ts=ts)
    except ImportError:
        from gamecore import canonical_id
        l = {'v': 1, 'ts': ts, 'actor': actor, 'for': for_, 'holon': holon, 'type': 'wallet', 'body': body,
             'links': links_ or {}, 'audience': 'holon', 'reason': 'human', 'prev': ''}
        l['id'] = canonical_id(l)
        l['sig'] = ''
        return l


def _answer(entry, actor, kind, now):
    if not isinstance(entry, dict) or not item_id(entry) or not holon_of(entry):
        raise ValueError('an entry with an id and a holon is needed')
    if actor_kind(actor) != 'person':
        raise ValueError('a wallet line is a person\'s own act; %r is not a person' % (actor,))
    if kind == 'accept' and _kind(entry) == 'gift':
        raise ValueError('a gift is given when it is written; there is nothing to accept')
    amt, why = _amount(entry.get('amount', field(entry, 'amount')))
    unit = _text(field(entry, 'unit'))
    if why or not unit:
        raise ValueError(why or 'the entry names no unit')
    return _line(actor, actor, holon_of(entry), {'kind': kind, 'amount': amt, 'unit': unit},
                 {'answers': [item_id(entry)]}, now)


def accept_line(entry, actor, now=None):
    """The unsigned line by which the other party accepts an offer (the fold refuses the offerer's own)."""
    return _answer(entry, actor, 'accept', now)


def settle_line(entry, actor, now=None):
    """The unsigned line by which either party says the entry is settled."""
    return _answer(entry, actor, 'settle', now)


def _cell(v):
    """A value fit for one Markdown table cell or list line: `|` escaped, newlines made spaces."""
    return ' '.join(str('—' if v is None or v == '' else v).replace('|', '\\|').split())


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def _dicts(v):
    return sorted(((k, x) for k, x in v.items() if isinstance(x, dict)), key=lambda kv: str(kv[0])) \
        if isinstance(v, dict) else []


def render(report, actor=None):
    """The report as plain Markdown. A malformed report renders what it can and never raises."""
    r = report if isinstance(report, dict) else {}
    out = ['# The wallet', '', '*%s*' % _cell(r.get('note') or NOT_CONVERTIBLE), '']
    units = [u for u in (r.get('units') or []) if isinstance(u, dict)] if isinstance(r.get('units'), list) else []
    if not units:
        out += ['No wallet entries yet.', '']
    for u in units:
        out.append('- **%s**: %s.' % (_cell(u.get('unit')), 'ruled' if u.get('ruled') is True else _cell(u.get('note') or UNRULED_NOTE)))
    if units:
        out.append('')
    rows = _dicts(r.get('by_unit'))
    if rows:
        out += ['## By unit', '', '| unit | offered | accepted | settled | given | witnessed |', '|---|---|---|---|---|---|']
        for u, a in rows:
            out.append('| %s | %d | %d | %d | %d | %d |' % (_cell(u), _int(a.get('offered')), _int(a.get('accepted')),
                                                          _int(a.get('settled')), _int(a.get('given')), _int(a.get('witnessed_n'))))
        out.append('')
    acts = [(k, v) for k, v in _dicts(r.get('by_actor')) if actor is None or k == actor]
    if acts:
        out += ['## By actor (settled and given only)', '', '| actor | unit | in | out | net |', '|---|---|---|---|---|']
        for a, us in acts:
            for u, v in _dicts(us):
                out.append('| %s | %s | %d | %d | %d |' % (_cell(a), _cell(u), _int(v.get('in')), _int(v.get('out')), _int(v.get('net'))))
        out.append('')
    elif actor is not None:
        out += ['Nothing settled or given for %s.' % _cell(actor), '']
    for p in r.get('problems') if isinstance(r.get('problems'), list) else []:
        if isinstance(p, dict):
            out.append('- %s: %s.' % (_cell(str(p.get('id') or '')[:12]), _cell(p.get('why'))))
    if r.get('as_of'):
        out += ([] if out[-1] == '' else ['']) + ['As of %s.' % _cell(r['as_of'])]
    return '\n'.join(out).rstrip() + '\n'


def _read(path):
    if not isinstance(path, str) or os.path.islink(path):
        raise OSError('a linked file is not read')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _main(argv=None):
    ap = argparse.ArgumentParser(description='Wallet balances per unit from folded items (JSON).')
    ap.add_argument('items'); ap.add_argument('--holon'); ap.add_argument('--actor')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        items = _read(a.items)
    except (OSError, ValueError) as e:
        print('wallet: cannot read %s: %s' % (a.items, e), file=sys.stderr); return 2
    r = balances(items, a.holon)
    if a.actor:
        r = dict(r, by_actor={k: v for k, v in r['by_actor'].items() if k == a.actor})
    print(json.dumps(r, indent=1, sort_keys=True, ensure_ascii=False) if a.json else render(r, a.actor), end='' if not a.json else '\n')
    return 0


if __name__ == '__main__':
    sys.exit(_main())
