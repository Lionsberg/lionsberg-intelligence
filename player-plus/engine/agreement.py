#!/usr/bin/env python3
"""agreement.py — the Agreement between holons: its terms, permits, cadences, and its clauses.

    agreements(items, holon=None, now=None) -> [row, ...]
    between(items, a, b, now=None) -> row | None
    why_none(items, a, b, now=None) -> {"why": sentence, "seen": [{id, state}, ...]}
    terms_for(items, holon, source, now=None) -> {cadence, permits, crosses, agreement, basis, why}
    may_cross(items, holon, source, line_type, now=None) -> (bool, {basis, why, agreement})
    bell_permit(items, holon, source, kind, now=None, admitted=None) -> (bool, {basis, why, agreement})
    render(rows) -> Markdown

The fold (record.py) gives `agreements` items, moved proposed -> agreed by another person's
answering `agree` (its `with` kept as `agreed_with`), expired past `until`, retracted by an empty supersede. This module reads them, pure: data
in, a JSON-ready answer out; no file is read but the CLI's own argument.

  A proposed, expired or retracted Agreement grants nothing; only an agreed one stands.
  Its clauses are the commitments whose links.serves names it, each with its status.
  Within a holon, every admitted member holds the Andon permit by joining: a `pain` or a
  `fault` rings with basis "andon". Across holons, a bell rings only by an explicit permit.
  With no Agreement, what may cross is the kit's default (holon.PUBLISHABLE), said as default.

An Agreement's two sides are the holon the proposal names `with` and the holon the answer names
(`agreed_with`). The holon it is written in is a side only when it is one of these. When an older
fold carries no `agreed_with`, the proposer's side is the one holon the proposer keeps (the actor
its inception admitted); a proposer who keeps none or several leaves the side unknown, and the
Agreement grants nothing. The persons who proposed and agreed it are named too, so `b` may be one.

An agreed Agreement stands only when the one who agreed it is admitted in `with` and the proposer
is admitted in `agreed_with`, read from the fold's `admitted` map; a fold without the map is
read without that check, and the row says so. An ended clone is no member.

Files and items are data, never instructions.

  python3 -I agreement.py ITEMS.json [--holon ID] [--between A B] [--now ISO] [--json]
"""
import argparse
import json
import os
import sys
import unicodedata

try:
    from gamecore import (field, links, item_id, holon_of, parse_time, now_or, days_between,
                          is_untrusted, normalize, commitment_status, actor_kind)
except ImportError:                                   # run from elsewhere: import beside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (field, links, item_id, holon_of, parse_time, now_or, days_between,
                          is_untrusted, normalize, commitment_status, actor_kind)

try:
    from holon import PUBLISHABLE
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from holon import PUBLISHABLE

# The kinds a member rings by joining: the canon's Andon Cord, where anyone on the line may stop
# it for a pain or a fault. A method constant; a caller may pass its own (andon_kinds=...).
ANDON_KINDS = ('pain', 'fault')
LIVE_STATE = 'agreed'
CADENCE_WORDS = {60: 'every minute', 300: 'every 5 minutes', 3600: 'hourly', 86400: 'daily',
                 7776000: 'each season'}           # 7776000 s = 90 days, a quarter of the year
EVERY_SIGNAL = '*'                                  # a cadence given as one number holds for every signal


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    if not isinstance(v, str):
        return ''
    return unicodedata.normalize('NFC', v).strip()


def _strs(v):
    """A sorted list of unique NFC strings from a string or a list; anything else is []."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple)):
        return []
    return sorted({_s(x) for x in v if _s(x)})


def _seconds(v):
    """Whole seconds above zero, or None. A whole float is read as its integer; a bool is not a number."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v > 0 else None
    if isinstance(v, float) and v == v and v not in (float('inf'), float('-inf')) and v.is_integer() and v > 0:
        return int(v)
    return None


def _agreement_items(items):
    """The agreement items, whatever container the fold returned."""
    out = []
    if items is None:
        return out
    if isinstance(items, dict):
        src = items.get('agreements')
        if isinstance(src, dict):
            src = [dict(v, id=v.get('id', k)) for k, v in src.items() if isinstance(v, dict)]
        if isinstance(src, list):
            out.extend(x for x in src if isinstance(x, dict))
        if isinstance(items.get('items'), list):
            out.extend(x for x in items['items'] if isinstance(x, dict)
                       and _s(x.get('kind') or x.get('type') or x.get('item')).lower() in ('agreement', 'agree'))
    elif isinstance(items, list):
        out.extend(x for x in items if isinstance(x, dict)
                   and _s(x.get('kind') or x.get('type') or x.get('item')).lower() in ('agreement', 'agree'))
    seen, uniq = set(), []
    for x in out:
        i = item_id(x)
        if i and i not in seen:
            seen.add(i)
            uniq.append(x)
    return uniq


def _commitments(items):
    if isinstance(items, dict) and isinstance(items.get('commitments'), list):
        return [c for c in items['commitments'] if isinstance(c, dict)]
    return [c for c in normalize(items).get('commitment', []) if isinstance(c, dict)]


def _admitted(items, admitted=None):
    """{holon: {actor: entry}} from the argument, else from the fold's own `admitted` map."""
    a = admitted if admitted is not None else (items.get('admitted') if isinstance(items, dict) else None)
    return a if isinstance(a, dict) else {}


CLONE_ENDED = ('done', 'archived')                 # a clone's admission ends at these body states (SCHEMA, Clones)


def _ended(e):
    """True for an admitted clone whose entry says its body is done or archived."""
    if not isinstance(e, dict) or e.get('via') != 'clone':
        return False
    st = _s(e.get('state') or e.get('body_state')).lower()
    return bool(e.get('ended')) or st in CLONE_ENDED


def _admitted_norm(adm):
    """{holon: set of admitted actors}, NFC, ended clones left out."""
    out = {}
    for h, actors in (adm.items() if isinstance(adm, dict) else ()):
        if _s(h) and isinstance(actors, dict):
            out[_s(h)] = {_s(a) for a, e in actors.items() if _s(a) and not _ended(e)}
    return out


def _keepers(items):
    """{actor: set of holon ids it keeps}: the actor each holon's inception admitted."""
    out = {}
    for h, actors in _admitted(items).items():
        if not isinstance(actors, dict):
            continue
        for a, e in actors.items():
            if isinstance(e, dict) and e.get('via') == 'inception' and _s(a) and _s(h):
                out.setdefault(_s(a), set()).add(_s(h))
    return out


def _moment(items, now):
    """The moment to read at: the one given, else the fold's own as_of, else the clock."""
    if now is None and isinstance(items, dict):
        a = items.get('as_of')
        if isinstance(a, dict):
            a = a.get('ts')
        if parse_time(a) is not None:
            return parse_time(a)
    return now_or(now)


def _cadence(v, notes):
    if v is None:
        return {}
    one = _seconds(v)
    if one is not None:
        notes.append('The cadence is one number, %d s, read as the cadence for every signal.' % one)
        return {EVERY_SIGNAL: one}
    if not isinstance(v, dict):
        notes.append('The cadence is neither a map of signals nor a number of seconds; none is read.')
        return {}
    out = {}
    for k, s in v.items():
        sec, key = _seconds(s), _s(k)
        if key and sec is not None:
            out[key] = sec
        elif key:
            notes.append('The cadence for %s is not a whole number of seconds; it is left out.' % key)
    return dict(sorted(out.items()))


def _fields(v, notes):
    """permits.fields normalized: {type: [field names kept visible]}; a malformed entry is None, said.

    None for the whole map when it is not a map: what a face may show is then not known, and a
    reader (faces.py) opens nothing rather than guess."""
    if not isinstance(v, dict):
        notes.append('The permits name fields, but not as a map of types; what a face may show is not known.')
        return None
    out = {}
    for t, fs in v.items():
        key = _s(t)
        if not key:
            notes.append('A fields entry names no type; it is left out.')
            continue
        if isinstance(fs, (list, tuple)) and all(isinstance(x, str) for x in fs):
            out[key] = _strs(list(fs))
        else:
            out[key] = None
            notes.append('The fields for %s are not a list of names; what its face may show is not known.' % key)
    return dict(sorted(out.items()))


def _permits(v, notes):
    if v is None:
        return {'write': False, 'bell': []}
    if not isinstance(v, dict):
        notes.append('The permits are not a map; none is read.')
        return {'write': False, 'bell': []}
    out = {'write': v.get('write') is True, 'bell': _strs(v.get('bell'))}
    if 'fields' in v:                                   # carried only when the Agreement names fields
        out['fields'] = _fields(v.get('fields'), notes)
    return out


def _clause(c, now):
    status, _gap = commitment_status(c, now)
    committee = field(c, 'committee')
    return {'id': item_id(c), 'card': field(c, 'card'), 'for': field(c, 'for'),
            'committee': committee if isinstance(committee, str) else None,
            'by': field(c, 'by'), 'state': field(c, 'state'), 'status': status}


def _row(a, commitments, t, keepers, adm):
    notes = []
    aid = item_id(a)
    state = _s(field(a, 'state')).lower() or 'proposed'
    until = field(a, 'until') if isinstance(field(a, 'until'), str) else None
    if field(a, 'retracted_by') and state != 'retracted':
        state = 'retracted'
    if state in ('proposed', 'agreed') and until and parse_time(until) is not None and parse_time(until) < t:
        state = 'expired'
    with_ = _s(field(a, 'with')) or None
    if with_ is None:
        notes.append('The Agreement names no holon it is with.')
    if until and parse_time(until) is None:
        notes.append('Its until is not a date; it is read as having none.')
        until = None
    proposer = _s(field(a, 'for')) or _s(field(a, 'actor')) or None
    agreed_by = _s(field(a, 'agreed_by')) or None
    receipts = field(a, 'receipts')
    clauses = sorted((_clause(c, t) for c in commitments if aid in links(c, 'serves')),
                     key=lambda r: r['id'])
    row = {'id': aid, 'holon': holon_of(a), 'state': state, 'proposer': proposer, 'with': with_,
           'agreed_by': agreed_by, 'agreed_ts': field(a, 'agreed_ts'),
           'terms': field(a, 'terms') if isinstance(field(a, 'terms'), str) else None,
           'crosses': _strs(field(a, 'crosses')),
           'cadence': _cadence(field(a, 'cadence'), notes),
           'permits': _permits(field(a, 'permits'), notes),
           'face': field(a, 'face') if isinstance(field(a, 'face'), str) else None,
           'until': until, 'days_left': days_between(t, until) if until else None,
           'clauses': clauses,
           'receipts': [r for r in receipts if isinstance(r, dict)] if isinstance(receipts, list) else [],
           'as_of': t.isoformat(timespec='seconds')}
    live = state == LIVE_STATE
    if live and is_untrusted(a):
        live = False
        notes.append('It came from text an agent read: a proposal only, and it grants nothing.')
    if live and field(a, 'vouched_by'):
        live = False
        notes.append('It is a copy vouched for by a publish line: it informs and grants nothing here.')
    agreed_with = _s(field(a, 'agreed_with')) or None
    if agreed_with is None:              # not yet answered, or an older fold: the one holon the proposer keeps
        kept = sorted(keepers.get(proposer, set())) if proposer else []
        kept = [h for h in kept if h != with_]
        if len(kept) == 1:
            agreed_with = kept[0]
            if state == LIVE_STATE:
                notes.append('The answer names no holon; the proposer keeps one, read as the proposer\'s side.')
        elif state == LIVE_STATE:
            notes.append('The answer names no holon, and the proposer keeps %s; the proposer\'s side is not known.'
                         % ('none' if not kept else 'several'))
    sides = sorted({x for x in (with_, agreed_with) if x})
    if live and (not with_ or not agreed_with or with_ == agreed_with):
        live = False
        if with_ and with_ == agreed_with:
            notes.append('Both sides name the same holon; an Agreement stands between two.')
    if live:
        if adm is None:
            notes.append('No admitted map was given, so who agreed it is not checked against either side.')
        else:
            if agreed_by not in adm.get(with_, set()):
                live = False
                notes.append('The one who agreed it is not admitted in the holon it is with; it grants nothing.')
            if proposer not in adm.get(agreed_with, set()):
                live = False
                notes.append('The proposer is not admitted in the holon the answer names; it grants nothing.')
    row['agreed_with'] = agreed_with
    row['live'] = live
    row['sides'] = sides
    row['parties'] = sorted(set(sides) | {x for x in (proposer, agreed_by) if x})
    row['notes'] = notes
    return row


def _rows(items, now):
    t = _moment(items, now)
    commitments = _commitments(items)
    keepers = _keepers(items)
    raw = items.get('admitted') if isinstance(items, dict) else None
    adm = _admitted_norm(raw) if isinstance(raw, dict) else None
    return [_row(a, commitments, t, keepers, adm) for a in _agreement_items(items)], t


def agreements(items, holon=None, now=None):
    """Every Agreement held, as rows; with `holon`, those written in it or naming it as a side."""
    rows, _t = _rows(items, now)
    h = _s(holon)
    if h:
        rows = [r for r in rows if h == r['holon'] or h in r['sides']]
    return sorted(rows, key=lambda r: (r['holon'], r['id']))


def _matching(rows, a, b):
    """Rows where holon `a` is a side and `b` (a holon or a person) is a side or a party."""
    a, b = _s(a), _s(b)
    if not a or not b or a == b or actor_kind(a):
        return []
    return [r for r in rows if a in r['sides'] and b in r['parties']]


def _newest(rows):
    def key(r):
        t = parse_time(r.get('agreed_ts'))
        return (t.timestamp() if t else float('-inf'), r['id'])
    return max(rows, key=key) if rows else None


def between(items, a, b, now=None):
    """The live Agreement between holon `a` and holon or actor `b` (two holons either way round); the newest agreed."""
    rows, _t = _rows(items, now)
    return _newest([r for r in _matching(rows, a, b) if r['live']])


def why_none(items, a, b, now=None):
    """Why no live Agreement stands between `a` and `b`, in one sentence, and what was seen."""
    rows, _t = _rows(items, now)
    if not _s(a) or not _s(b):
        return {'why': 'One side is not named, so no Agreement can be found.', 'seen': []}
    if _s(a) == _s(b):
        return {'why': 'Both sides are the same; an Agreement stands between two.', 'seen': []}
    if actor_kind(_s(a)):
        return {'why': 'The first side must be a holon; an Agreement is a holon\'s.', 'seen': []}
    found = sorted(_matching(rows, a, b), key=lambda r: r['id'])
    seen = [{'id': r['id'], 'state': r['state']} for r in found]
    live = [r for r in found if r['live']]
    if live:
        return {'why': 'An Agreement stands: %s.' % _newest(live)['id'][:12], 'seen': seen}
    if not found:
        return {'why': 'No Agreement held names both sides.', 'seen': seen}
    states = sorted({r['state'] for r in found})
    if any(r['state'] == LIVE_STATE for r in found):
        return {'why': 'The Agreement between them is agreed but grants nothing here (%s).'
                       % ' '.join(n for r in found for n in r['notes']), 'seen': seen}
    return {'why': 'An Agreement names both sides, and none is agreed: %s.' % ', '.join(states), 'seen': seen}


def terms_for(items, holon, source, now=None):
    """What the live Agreement with `source` grants `holon`; honest-empty when none stands."""
    r = between(items, holon, source, now)
    if r is None:
        return {'cadence': {}, 'permits': {}, 'crosses': [], 'agreement': None, 'basis': 'none',
                'why': why_none(items, holon, source, now)['why']}
    return {'cadence': dict(r['cadence']), 'permits': dict(r['permits'], bell=list(r['permits']['bell'])),
            'crosses': list(r['crosses']), 'agreement': r['id'], 'basis': 'agreement', 'why': None}


def may_cross(items, holon, source, line_type, now=None):
    """Whether a line of `line_type` may cross between `holon` and `source`.

    Under a live Agreement that names what crosses, only those types do, and never a type the kit
    keeps inside a membrane (not in holon.PUBLISHABLE). With no Agreement, or one that names none,
    the kit's default applies: what holon.PUBLISHABLE carries."""
    t = _s(line_type)
    if not t:
        return False, {'basis': 'none', 'why': 'No line type is named.', 'agreement': None}
    r = between(items, holon, source, now)
    if r is not None and r['crosses']:
        if t not in r['crosses']:
            return False, {'basis': 'agreement', 'agreement': r['id'],
                           'why': 'The Agreement does not name %s among what crosses.' % t}
        if t not in PUBLISHABLE:
            return False, {'basis': 'agreement', 'agreement': r['id'],
                           'why': 'The Agreement names %s, and the kit never carries it across a membrane.' % t}
        return True, {'basis': 'agreement', 'agreement': r['id'], 'why': 'The Agreement names %s among what crosses.' % t}
    lead = 'The Agreement names nothing that crosses' if r is not None else 'No Agreement stands'
    ok = t in PUBLISHABLE
    return ok, {'basis': 'default', 'agreement': r['id'] if r is not None else None,
                'why': '%s; by the kit\'s default %s %s.' % (lead, t, 'crosses' if ok else 'stays inside')}


def _members(admitted, holon):
    if isinstance(admitted, dict):
        inner = admitted.get(holon)
        if not isinstance(inner, dict):
            inner = next((v for k, v in admitted.items() if _s(k) == holon and isinstance(v, dict)), None)
        if isinstance(inner, dict):
            return {_s(a) for a, e in inner.items() if _s(a) and not _ended(e)}
        if admitted and all(actor_kind(_s(a)) for a in admitted):
            return {_s(a) for a, e in admitted.items() if not _ended(e)}   # the holon's own map was passed
        return set()
    if isinstance(admitted, (list, tuple, set, frozenset)):
        return {_s(a) for a in admitted if _s(a)}
    return set()


def bell_permit(items, holon, source, kind, now=None, admitted=None, andon_kinds=None):
    """Whether `source` may ring a bell of `kind` in `holon`.

    A member of the holon (an actor in `admitted`, the fold's admitted map; the fold's own when
    none is passed) rings the Andon kinds by joining. Anyone else rings only what a live
    Agreement's permits.bell names."""
    h, src, k = _s(holon), _s(source), _s(kind)
    if not h or not src or not k:
        return False, {'basis': 'none', 'agreement': None, 'why': 'The holon, the source and the kind must all be named.'}
    andon = tuple(_strs(list(andon_kinds))) if isinstance(andon_kinds, (list, tuple, set, frozenset)) else ANDON_KINDS
    adm = admitted if admitted is not None else _admitted(items)
    if k in andon and src in _members(adm, h):
        return True, {'basis': 'andon', 'agreement': None,
                      'why': 'A member of the holon holds the Andon permit by joining; %s rings.' % k}
    r = between(items, h, src, now)
    if r is None:
        return False, {'basis': 'none', 'agreement': None,
                       'why': 'The source is not a member and no Agreement stands; %s does not ring.' % k}
    if k in r['permits']['bell']:
        return True, {'basis': 'agreement', 'agreement': r['id'], 'why': 'The Agreement permits %s to ring.' % k}
    return False, {'basis': 'agreement', 'agreement': r['id'],
                   'why': 'The Agreement does not permit %s to ring.' % k}


def cadence_words(seconds):
    s = _seconds(seconds)
    if s is None:
        return 'at no set cadence'
    return CADENCE_WORDS.get(s, 'every %d s' % s)


def _short(x):
    """A hash id cut to 12 for the eye; an actor id or a name kept whole."""
    x = str(x or '')
    return x[:12] if len(x) == 64 and all(c in '0123456789abcdef' for c in x) else x


def render(rows):
    """One line per Agreement: its state, what crosses, its cadences in words, its clauses and their status."""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return '# Agreements\n\nNo Agreement is held.\n'
    out = ['# Agreements', '']
    for r in sorted(rows, key=lambda x: (str(x.get('holon') or ''), str(x.get('id') or ''))):
        crosses = ', '.join(x for x in (r.get('crosses') or []) if isinstance(x, str)) \
            if isinstance(r.get('crosses'), (list, tuple)) else ''
        crosses = crosses or 'the default'
        cad = r.get('cadence')
        if not isinstance(cad, dict):
            cad = {EVERY_SIGNAL: cad} if _seconds(cad) is not None else {}
        cads = '; '.join('%s %s' % ('every signal' if s == EVERY_SIGNAL else s, cadence_words(v))
                         for s, v in sorted(cad.items())) or 'no cadence'
        until = r.get('until')
        tail = ' · until %s' % until if until else ''
        if until and r.get('days_left') is not None and r.get('state') == LIVE_STATE:
            tail += ' (%s days left)' % r['days_left']
        out.append('- **%s** · %s · with %s · crosses %s · %s%s'
                   % (_short(r.get('id')), r.get('state') or 'unknown',
                      _short(r.get('with')) or 'no holon named', crosses, cads, tail))
        clauses = r.get('clauses') if isinstance(r.get('clauses'), list) else []
        for c in (c for c in clauses if isinstance(c, dict)):
            out.append('  - clause %s · %s · by %s' % (_short(c.get('id')), c.get('status'), c.get('by') or 'no date'))
        for n in (r.get('notes') if isinstance(r.get('notes'), list) else []):
            out.append('  - %s' % n)
    return '\n'.join(out) + '\n'


def _main(argv=None):
    ap = argparse.ArgumentParser(description='The Agreements between holons, read from folded items (JSON).')
    ap.add_argument('items', help='a JSON file of folded items (the output of record.py fold)')
    ap.add_argument('--holon')
    ap.add_argument('--between', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--now')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if os.path.islink(a.items):
        print('agreement: %s is a link; it is not read' % a.items, file=sys.stderr)
        return 2
    try:
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
    except (OSError, ValueError) as e:
        print('agreement: cannot read %s: %s' % (a.items, e), file=sys.stderr)
        return 2
    if a.between:
        r = between(items, a.between[0], a.between[1], a.now)
        if a.json:
            print(json.dumps(r if r is not None else why_none(items, a.between[0], a.between[1], a.now),
                             indent=1, sort_keys=True, ensure_ascii=False))
        else:
            print(render([r]) if r is not None else why_none(items, a.between[0], a.between[1], a.now)['why'])
        return 0
    rows = agreements(items, a.holon, a.now)
    print(json.dumps(rows, indent=1, sort_keys=True, ensure_ascii=False) if a.json else render(rows), end='' if not a.json else '\n')
    return 0


if __name__ == '__main__':
    sys.exit(_main())
