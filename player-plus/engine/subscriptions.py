#!/usr/bin/env python3
"""subscriptions.py — the Subscription Card: what a holon hears, from whom, how often, and where.

    subscriptions(lines, person, items=None, now=None, home=None, joined=None) -> [row, ...]
    ignored(lines, person, items=None, home=None) -> [{id, why}, ...]
    cadence_for(rows, source, signal) -> seconds | None
    due(rows, last_seen, now) -> [{source, signal, cadence, last, due_at, overdue_s}, ...]
    surface_for(rows, source, signal) -> "deal" | "wall" | "hud" | "pad" | "margin" | "bell" | None
    bell_for(rows, source, kind, members=()) -> (bool, basis)
    rises_first(line, person, agents=(), holons=()) -> bool
    subscribe_line(person, source, signals, cadence, surface, bell, agreement, now) -> line | None
    render(rows) -> Markdown, in words

Pull is the default for attention. Each Subscription Card says, for one source and each kind of
signal, the cadence at which the holon hears it (seconds per signal), the surface it is dealt to,
and the kinds that may ring a bell. Nothing reaches the person before the cadence they set; a
request addressed to them still arrives by pull, and rises first at the next pull.

The Card is the person's own word. Only their own trusted `subscribe` lines count: actor and
`for` both the person, a person and never an agent, `reason` not untrusted, written in their own
home when the home is known; when a fold is given (`items`, record.py's fold), only lines it
trusts (signed, or at home; a vouched copy never), not invalid, unverified, forked or a proposal,
held as a Card, and not retracted. Later lines overlay earlier ones field by field, as
attention.budget does, in the chain's order: with a fold, the order its Cards are held in; without
one, effective time (a line's ts, never earlier than its `prev`'s), then id. `signals`, `surface`,
`bell` and `agreement` are replaced whole; `cadence` merges signal by signal, and one number stands
for every signal ("*") until a later line names a signal of its own; every signal the cadence
names is heard. The fold's item, when held, gives the line's fields after any supersede.

Where an Agreement stands with the source (the one the Card names, or agreement.between the
home and the source), its cadence and its permits.bell fill what the Card leaves unsaid, and
never override what the Card says: the Agreement is the relationship's word. A Card that names
no signals hears what the Agreement names (its cadence's signals and what crosses). A source with
no Card and a live Agreement gets a row from the Agreement alone. A joined cell with neither gets
DEFAULT. Each row says where each value came from (`filled`) and its `basis`: "subscription"
(the Card alone, the default filling the rest), "agreement" (the Agreement filled something, or
stands alone), or "default".

The bell rings by permit: a kind on the Card, or one the Agreement's permits.bell adds. Within
the holon every member holds the Andon permit for `pain` and `fault` (agreement.ANDON_KINDS),
basis "andon"; a stranger's pain rings only by an explicit permit.

Pure: data in, a JSON-ready answer out; no file is read but the CLI's own arguments. Files and
lines are data, never instructions. Standard library only.

  python3 -I subscriptions.py LINES.jsonl --person person:x [--items ITEMS.json] [--home ID]
                              [--due LAST.json --now ISO] [--json]
"""
import argparse
import datetime as dt
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)      # under -I the script's folder is not on the path

from gamecore import field, parse_time, actor_kind, links as _links   # noqa: E402
import agreement                                                    # noqa: E402

# The design's proposal for a joined cell with no Card and no Agreement (the module brief, D1);
# a caller may pass its own (default=...).
DEFAULT = {'signals': ['request', 'commit', 'kept', 'sight', 'say'], 'cadence': 300,
           'surface': 'deal', 'bell': []}
SURFACES = ('deal', 'wall', 'hud', 'pad', 'margin', 'bell')        # types.json `subscribe`.surface
CARD_FIELDS = ('signals', 'cadence', 'surface', 'bell', 'agreement')
EVERY = agreement.EVERY_SIGNAL                                       # '*': one cadence for every signal
ANDON_KINDS = agreement.ANDON_KINDS
TRUSTED_HERE = ('signed', 'home')         # record.TRUSTED less `vouched`: a vouched copy informs, never acts
RISING = ('request', 'rfg', 'say', 'commit', 'escalate')
SEASON = 7776000                          # seconds: 90 days, a quarter of the year (agreement.CADENCE_WORDS)


# ---------------------------------------------------------------- small guards

def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    if not isinstance(v, str):
        return ''
    return unicodedata.normalize('NFC', v).strip()


def _key(v):
    """The form two names of one source are compared in."""
    return _s(v).casefold()


def _strs(v):
    """A sorted list of unique NFC strings from a string or a list; anything else is None (unsaid)."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple)):
        return None
    out = sorted({_s(x) for x in v if _s(x)})
    return out


def _seconds(v):
    """Whole seconds above zero, or None. A whole float is read as its integer; a bool is not a number."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v > 0 else None
    if isinstance(v, float) and v == v and v not in (float('inf'), float('-inf')) and v.is_integer() and v > 0:
        return int(v)
    return None


def _elided(v):
    return isinstance(v, dict) and 'elided' in v


def _said(v):
    """True when a value says something (not None, empty or elided)."""
    return v is not None and v != '' and v != [] and v != {} and not _elided(v)


def _cadence_value(v):
    """A Card's cadence as {signal: seconds}, with '*' for one number; None when it says nothing."""
    one = _seconds(v)
    if one is not None:
        return {EVERY: one}
    if not isinstance(v, dict):
        return None
    out = {}
    for k, s in v.items():
        sec, name = _seconds(s), _s(k)
        if name and sec is not None:
            out[name] = sec
    return out or None


def _ts_key(line):
    t = parse_time(line.get('ts'))
    return (t.timestamp() if t else float('-inf'), _s(line.get('id')))


def _chain_order(lines, items):
    """The lines in the order the person's word was given.

    With a fold that holds subscription items, their order there (the fold's causal order).
    Without one, by effective time: a line's own ts, never earlier than the line its `prev`
    names (time never runs backwards within a chain); ties by id."""
    subs = items.get('subscriptions') if isinstance(items, dict) else None
    if isinstance(subs, list):
        pos = {}
        for i, it in enumerate(subs):
            if isinstance(it, dict) and isinstance(it.get('id'), str):
                pos.setdefault(it['id'], i)
        return sorted((l for l in lines if _s(l.get('id')) in pos),
                      key=lambda l: (pos[_s(l.get('id'))], _s(l.get('id'))))
    by_id = {}
    for l in lines:
        if _s(l.get('id')):
            by_id.setdefault(_s(l.get('id')), l)
    eff = {}

    def effective(l):
        stack, seen = [l], set()
        while stack:                              # walk back to a known time, then come forward
            top = stack[-1]
            tid = _s(top.get('id'))
            prev = by_id.get(_s(top.get('prev')))
            if prev is not None and _s(prev.get('id')) not in eff and _s(prev.get('id')) not in seen:
                seen.add(tid)
                stack.append(prev)
                continue
            stack.pop()
            own = _ts_key(top)[0]
            before = eff.get(_s(prev.get('id'))) if prev is not None else None
            eff[tid] = own if before is None else max(own, before)
        return eff.get(_s(l.get('id')), _ts_key(l)[0])

    return sorted(lines, key=lambda l: (effective(l), _s(l.get('id'))))


def _moment(now):
    t = parse_time(now) if now is not None else None
    return t


def _iso(t):
    return t.isoformat(timespec='seconds') if t is not None else None


# ---------------------------------------------------------------- what the fold says

def _fold_maps(items):
    """(trust map or None, invalid ids, {line id: subscription item}) from a fold, null-guarded."""
    if not isinstance(items, dict):
        return None, set(), {}
    trust = items.get('trust') if isinstance(items.get('trust'), dict) else None
    bad = set()
    for k in ('invalid', 'unverified', 'proposals', 'forked'):
        for x in items.get(k) or []:
            if isinstance(x, dict) and isinstance(x.get('id'), str):
                bad.add(x['id'])
    subs = items.get('subscriptions')
    if isinstance(subs, dict):
        subs = [dict(v, id=v.get('id', k)) for k, v in subs.items() if isinstance(v, dict)]
    held = {}
    for it in subs if isinstance(subs, list) else []:
        if isinstance(it, dict) and isinstance(it.get('id'), str):
            held[it['id']] = it
    return trust, bad, held


def _admitted(items):
    a = items.get('admitted') if isinstance(items, dict) else None
    return a if isinstance(a, dict) else {}


def _member_of(entry):
    return not (isinstance(entry, dict) and (entry.get('ended') or
                (entry.get('via') == 'clone' and _s(entry.get('state')).lower() in ('done', 'archived'))))


def _homes_of(items, person):
    """The holons whose inception admitted `person`: the homes they keep."""
    out = set()
    for h, actors in _admitted(items).items():
        if isinstance(actors, dict):
            e = actors.get(person)
            if isinstance(e, dict) and e.get('via') == 'inception' and _s(h):
                out.add(_s(h))
    return out


def _joined_of(items, person, home):
    """The holons the fold admits `person` in, other than the home."""
    out = set()
    for h, actors in _admitted(items).items():
        if isinstance(actors, dict) and person in actors and _member_of(actors.get(person)) and _s(h) != home:
            out.add(_s(h))
    return out


# ---------------------------------------------------------------- the person's own lines

def _sorted_lines(lines):
    if isinstance(lines, dict):
        lines = [lines]
    if not isinstance(lines, (list, tuple)):
        return []
    return [l for l in lines if isinstance(l, dict)]


def _judge(l, person, trust, bad, held, home, items_subs_marker=None):
    """None when the line counts as the person's own Card; else why it does not."""
    if l.get('type') != 'subscribe':
        return 'not a subscribe line'
    if actor_kind(person) != 'person':
        return 'a Subscription Card is a person\'s own act'
    if _s(l.get('actor')) != person or _s(l.get('for')) != person:
        return 'written by %s, not by the person for themselves' % (
            'an agent' if actor_kind(_s(l.get('actor'))) == 'agent' else 'another actor')
    if _s(l.get('reason')).lower() == 'untrusted':
        return 'its reason is untrusted: a proposal only'
    lid = _s(l.get('id'))
    if trust is not None and trust.get(lid) not in TRUSTED_HERE:
        return 'the fold does not trust it'
    if lid in bad:
        return 'the fold lists it as invalid, unverified, forked or a proposal'
    if isinstance(items_subs_marker, dict) and lid not in held:
        return 'the fold holds no Card for it'
    it = held.get(lid)
    if isinstance(it, dict) and (_s(it.get('state')).lower() == 'retracted' or it.get('retracted_by')):
        return 'it is retracted'
    if home and _s(l.get('holon')) and _s(l.get('holon')) != home:
        return 'it is written outside the person\'s own home, and a Card is home-only'
    return None


def _home(lines, person, items, home):
    if _s(home):
        return _s(home)
    homes = _homes_of(items, person)
    if len(homes) == 1:
        return next(iter(homes))
    own = {_s(l.get('holon')) for l in lines if l.get('type') == 'subscribe'
           and _s(l.get('actor')) == person and _s(l.get('for')) == person and _s(l.get('holon'))}
    return next(iter(own)) if len(own) == 1 else ''


def ignored(lines, person, items=None, home=None):
    """Every subscribe line that does not count as the person's own Card, and why."""
    person = _s(person)
    ls = _sorted_lines(lines)
    trust, bad, held = _fold_maps(items)
    h = _home(ls, person, items, home)
    out = []
    marker = held if isinstance(items, dict) and isinstance(items.get('subscriptions'), list) else None
    for l in sorted((l for l in ls if l.get('type') == 'subscribe'), key=_ts_key):
        why = _judge(l, person, trust, bad, held, h, marker)
        if why:
            out.append({'id': _s(l.get('id')) or None, 'why': why})
    return out


def _values(l, held):
    """The line's Card fields, the fold's item (after any supersede) over the line's body."""
    body = l.get('body') if isinstance(l.get('body'), dict) else {}
    it = held.get(_s(l.get('id')))
    out = {}
    for k in ('source',) + CARD_FIELDS:
        v = field(it, k) if isinstance(it, dict) else None
        out[k] = v if v is not None else body.get(k)
    if not _said(out.get('agreement')):
        serves = _links(l, 'serves')
        out['agreement'] = serves[0] if len(serves) == 1 else out.get('agreement')
    return out


def _cards(lines, person, items, home):
    """{source key: card} from the person's own lines, later overlaying earlier field by field."""
    trust, bad, held = _fold_maps(items)
    cards = {}
    marker = held if isinstance(items, dict) and isinstance(items.get('subscriptions'), list) else None
    ls = _sorted_lines(lines)
    for l in _chain_order(ls, items):
        if _judge(l, person, trust, bad, held, home, marker):
            continue
        v = _values(l, held)
        src = _s(v.get('source'))
        if not src:
            continue
        lid = _s(l.get('id')) or None
        c = cards.setdefault(_key(src), {'source': src, 'set_by': {'source': lid}})
        sig = _strs(v.get('signals')) if _said(v.get('signals')) else None
        if sig:
            c['signals'] = sig
            c['set_by']['signals'] = lid
        cad = _cadence_value(v.get('cadence')) if _said(v.get('cadence')) else None
        if cad:
            if EVERY in cad:
                c['cadence'] = dict(cad)          # one number stands for every signal, replacing what was
            else:
                c['cadence'] = dict(c.get('cadence') or {}, **cad)
            c['set_by']['cadence'] = lid
        surf = _s(v.get('surface')).lower()
        if surf in SURFACES:
            c['surface'] = surf
            c['set_by']['surface'] = lid
        bell = _strs(v.get('bell')) if _said(v.get('bell')) else None
        if bell:
            c['bell'] = bell
            c['set_by']['bell'] = lid
        ag = _s(v.get('agreement'))
        if ag:
            c['agreement'] = ag
            c['set_by']['agreement'] = lid
    return cards, trust is not None


# ---------------------------------------------------------------- the Agreement's part

def _agreement_for(items, home, source, named, now, notes):
    """The live Agreement row that fills this source's Card, or None, with a sentence when it matters."""
    if items is None:
        if named:
            notes.append('The Card names an Agreement, and no fold was given to read it.')
        return None
    if named:
        rows = [r for r in agreement.agreements(items, now=now) if r.get('id') == named]
        if not rows:
            notes.append('The Agreement the Card names is not held; nothing is filled from it.')
            return None
        r = rows[0]
        if not r.get('live'):
            notes.append('The Agreement the Card names is %s and grants nothing here; nothing is filled from it.'
                         % (r.get('state') or 'not agreed'))
            return None
        if _key(source) not in {_key(x) for x in r.get('parties') or []}:
            notes.append('The Agreement the Card names is not with this source; nothing is filled from it.')
            return None
        if home and home not in (r.get('sides') or []):
            notes.append('The Agreement the Card names is not this home\'s; nothing is filled from it.')
            return None
        return r
    if not home:
        return None
    return agreement.between(items, home, source, now)


def _ag_signals(r):
    if r is None:
        return []
    cad = r.get('cadence') if isinstance(r.get('cadence'), dict) else {}
    return sorted({k for k in cad if k != EVERY} | set(r.get('crosses') or []))


def _row(source, card, ag, default, set_by_trust):
    card = card or {}
    notes = list(card.get('_notes') or [])
    filled = {'signals': None, 'cadence': {}, 'surface': None, 'bell': {}}
    ccad = card.get('cadence') or {}
    named = {k for k in ccad if k != EVERY}       # every signal the Card's cadence names is heard
    if card.get('signals'):
        signals, filled['signals'] = sorted(set(card['signals']) | named), 'subscription'
    elif _ag_signals(ag):
        signals, filled['signals'] = sorted(set(_ag_signals(ag)) | named), 'agreement'
    else:
        signals, filled['signals'] = sorted(set(default['signals']) | named), 'default'
    acad = ag.get('cadence') if ag is not None and isinstance(ag.get('cadence'), dict) else {}
    dcad = default['cadence']
    cadence = {}
    for s in signals:
        if s in ccad:
            cadence[s], filled['cadence'][s] = ccad[s], 'subscription'
        elif EVERY in ccad:
            cadence[s], filled['cadence'][s] = ccad[EVERY], 'subscription'
        elif s in acad:
            cadence[s], filled['cadence'][s] = acad[s], 'agreement'
        elif EVERY in acad:
            cadence[s], filled['cadence'][s] = acad[EVERY], 'agreement'
        else:
            per = dcad.get(s, dcad.get(EVERY)) if isinstance(dcad, dict) else dcad
            cadence[s], filled['cadence'][s] = _seconds(per) or DEFAULT['cadence'], 'default'
    if card.get('surface'):
        surface, filled['surface'] = card['surface'], 'subscription'
    else:
        surface, filled['surface'] = default['surface'], 'default'
    bell = {}
    for k in card.get('bell') or []:
        bell[k] = 'subscription'
    if ag is not None:
        for k in (ag.get('permits') or {}).get('bell') or []:
            bell.setdefault(_s(k), 'agreement')
    if not card.get('bell') and ag is None:
        for k in default.get('bell') or []:
            bell.setdefault(_s(k), 'default')
    filled['bell'] = dict(sorted(bell.items()))
    used_ag = ag is not None and (filled['signals'] == 'agreement' or 'agreement' in filled['cadence'].values()
                                  or 'agreement' in filled['bell'].values())
    if not card.get('set_by'):
        basis = 'agreement' if ag is not None else 'default'
    else:
        basis = 'agreement' if used_ag else 'subscription'
    if card.get('set_by') and not set_by_trust:
        notes.append('No fold\'s trust was given, so the Card\'s lines were read by their envelope alone.')
    if basis == 'default':
        notes.append('No Subscription Card and no Agreement: the default for a joined cell holds.')
    elif basis == 'agreement' and not card.get('set_by'):
        notes.append('No Subscription Card: the Agreement alone says what is heard.')
    elif used_ag:
        notes.append('The Agreement fills what the Card leaves unsaid.')
    return {'source': source, 'signals': signals, 'cadence': dict(sorted(cadence.items())), 'surface': surface,
            'bell': sorted(bell), 'agreement': card.get('agreement') or (ag.get('id') if ag is not None else None),
            'set_by': dict(sorted((card.get('set_by') or {}).items())), 'basis': basis,
            'filled': filled, 'why': notes}


def _default(d):
    if not isinstance(d, dict):
        return DEFAULT
    out = dict(DEFAULT)
    for k in DEFAULT:
        if k in d and d[k] is not None:
            out[k] = d[k]
    out['signals'] = _strs(out['signals']) or DEFAULT['signals']
    out['surface'] = out['surface'] if out['surface'] in SURFACES else DEFAULT['surface']
    out['bell'] = _strs(out['bell']) or []
    if not (isinstance(out['cadence'], dict) or _seconds(out['cadence'])):
        out['cadence'] = DEFAULT['cadence']
    return out


def subscriptions(lines, person, items=None, now=None, home=None, joined=None, default=None):
    """The person's Subscription Cards, one row per source, the Agreement and the default filling in.

    `items` is record.py's fold (its `trust`, `invalid`, `subscriptions`, `agreements`, `admitted`);
    `home` the person's own holon (else the one the fold says they keep, else the one their
    subscribe lines are written in); `joined` the holons a default row is owed to (else every holon
    the fold admits the person in, the home aside)."""
    person = _s(person)
    if actor_kind(person) != 'person':
        return []
    ls = _sorted_lines(lines)
    h = _home(ls, person, items, home)
    d = _default(default)
    cards, have_trust = _cards(ls, person, items, h)
    rows = {}
    for k, c in cards.items():
        notes = []
        ag = _agreement_for(items, h, c['source'], c.get('agreement'), now, notes)
        c['_notes'] = notes
        rows[k] = _row(c['source'], c, ag, d, have_trust)
    if items is not None and h:
        for r in agreement.agreements(items, holon=h, now=now):
            if not r.get('live') or h not in (r.get('sides') or []):
                continue
            for other in (x for x in r['sides'] if x != h):
                if _key(other) in rows:
                    continue
                ag = agreement.between(items, h, other, now)
                if ag is not None:
                    rows[_key(other)] = _row(other, None, ag, d, have_trust)
    js = joined if isinstance(joined, (list, tuple, set, frozenset)) else _joined_of(items, person, h)
    for j in sorted({_s(x) for x in js if _s(x)}):
        if _key(j) not in rows and j != h:
            rows[_key(j)] = _row(j, None, None, d, have_trust)
    return [rows[k] for k in sorted(rows, key=lambda k: (k, rows[k]['source']))]


# ---------------------------------------------------------------- reading the rows

def _find(rows, source):
    k = _key(source)
    if not k:
        return None
    for r in rows if isinstance(rows, (list, tuple)) else []:
        if isinstance(r, dict) and _key(r.get('source')) == k:
            return r
    return None


def cadence_for(rows, source, signal):
    """Seconds per `signal` from `source`, or None when the source or the signal is not heard."""
    r = _find(rows, source)
    cad = r.get('cadence') if isinstance(r, dict) and isinstance(r.get('cadence'), dict) else {}
    return _seconds(cad.get(_s(signal)))


def surface_for(rows, source, signal):
    """The surface a signal from `source` is dealt to, or None when it is not heard."""
    r = _find(rows, source)
    if r is None or cadence_for(rows, source, signal) is None:
        return None
    return r.get('surface') if r.get('surface') in SURFACES else None


def _last(last_seen, source, signal):
    if not isinstance(last_seen, dict):
        return None
    v = None
    for k, x in last_seen.items():
        if _key(k) == _key(source):
            v = x
            break
    if isinstance(v, dict):
        v = v.get(signal)
    return parse_time(v) if isinstance(v, str) else None


def due(rows, last_seen, now):
    """Each (source, signal) whose cadence has come round as of `now`; a pair never seen is due now.

    `last_seen` is {source: {signal: iso}} (or {source: iso}, one time for every signal). The
    most overdue first; ties by source, then signal."""
    t = _moment(now)
    if t is None:
        return []
    out = []
    for r in rows if isinstance(rows, (list, tuple)) else []:
        if not isinstance(r, dict) or not _s(r.get('source')):
            continue
        cad = r.get('cadence') if isinstance(r.get('cadence'), dict) else {}
        for sig in sorted(cad):
            sec = _seconds(cad[sig])
            if sec is None:
                continue
            last = _last(last_seen, r['source'], sig)
            at = t if last is None else last + dt.timedelta(seconds=sec)
            if at > t:
                continue
            out.append({'source': r['source'], 'signal': sig, 'cadence': sec,
                        'last': _iso(last.astimezone(t.tzinfo)) if last else None,
                        'due_at': _iso(at.astimezone(t.tzinfo)), 'overdue_s': int((t - at).total_seconds())})
    return sorted(out, key=lambda x: (-x['overdue_s'], _key(x['source']), x['source'], x['signal']))


def bell_for(rows, source, kind, members=()):
    """(rings, basis): basis "andon" (a member's pain or fault), "subscription" (the Card permits it),
    "agreement" (the Agreement's permits.bell adds it), or "none"."""
    k = _s(kind)
    src = _s(source)
    if not k or not src:
        return False, 'none'
    if isinstance(members, dict):
        mem = {_s(a) for a, e in members.items() if _member_of(e)}
    elif isinstance(members, (list, tuple, set, frozenset)):
        mem = {_s(a) for a in members if _s(a)}
    else:
        mem = set()
    if k in ANDON_KINDS and src in mem:
        return True, 'andon'
    r = _find(rows, src)
    if r is None:
        return False, 'none'
    filled = r.get('filled') if isinstance(r.get('filled'), dict) else {}
    fb = filled.get('bell') if isinstance(filled.get('bell'), dict) else {}
    if k in (r.get('bell') or []):
        b = fb.get(k)
        return True, b if b in ('subscription', 'agreement', 'default') else 'subscription'
    return False, 'none'


def _ids(v):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple)):
        return set()
    return {_s(x) for x in v if _s(x)}


def rises_first(line, person, agents=(), holons=()):
    """True for a line addressed to the person or their agents (a `request` or `rfg` to them, a
    `say` with them in `to`, a `commit` with them as committee) or an `escalate` to their holon:
    it rises above everything at the next pull, whatever the cadence. A line of the person's own
    (its actor or its `for` the person, so their own agent's too), or one from untrusted text,
    does not. The caller passes lines the fold trusts; this reads no signature."""
    if not isinstance(line, dict):
        return False
    person = _s(person)
    if actor_kind(person) != 'person':
        return False
    if (_s(line.get('reason')).lower() == 'untrusted' or _s(line.get('actor')) == person
            or _s(line.get('for')) == person):
        return False
    typ = _s(line.get('type'))
    if typ not in RISING:
        return False
    body = line.get('body') if isinstance(line.get('body'), dict) else {}
    them = {person} | _ids(list(agents) if isinstance(agents, (list, tuple, set, frozenset)) else agents)
    hs = _ids(list(holons) if isinstance(holons, (list, tuple, set, frozenset)) else holons)
    if typ in ('request', 'say'):
        return bool(_ids(body.get('to')) & them)
    if typ == 'rfg':
        return bool(_ids(body.get('to')) & (them | hs))
    if typ == 'commit':
        return bool(_ids(body.get('committee')) & them)
    return bool(_ids(body.get('to')) & (hs | them))         # escalate


def subscribe_line(person, source, signals=None, cadence=None, surface=None, bell=None, agreement=None,
                   now=None, holon=None, salt=None):
    """An unsigned `subscribe` line for the person to sign, or None when it would say nothing true.

    It names the Agreement it serves both in body.agreement and links.serves. With no `holon` the
    record gives it one at the append; with no `salt` the record gives it a fresh one."""
    person, src = _s(person), _s(source)
    if actor_kind(person) != 'person' or not src:
        return None
    cad = _cadence_value(cadence)
    if cad is not None and EVERY in cad:
        cad = cad[EVERY]
    body = {'source': src, 'signals': _strs(signals) or None, 'cadence': cad,
            'surface': _s(surface).lower() if _s(surface).lower() in SURFACES else None,
            'bell': _strs(bell) or None, 'agreement': _s(agreement) or None}
    lk = {'serves': [_s(agreement)]} if _s(agreement) else None
    try:
        import record
        return record.make_line(person, person, _s(holon), 'subscribe', body, lk, audience='holon',
                                reason='human', ts=_iso(_moment(now)) if _moment(now) else None, salt=salt)
    except (ImportError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------- in words

def words(seconds):
    """Seconds as a person says a cadence."""
    s = _seconds(seconds)
    if s is None:
        return 'at no set cadence'
    if s == SEASON:
        return 'each season'
    if s % 86400 == 0:
        return 'daily' if s == 86400 else 'every %d days' % (s // 86400)
    if s % 3600 == 0:
        return 'hourly' if s == 3600 else 'every %d hours' % (s // 3600)
    if s % 60 == 0:
        return 'every minute' if s == 60 else 'every %d minutes' % (s // 60)
    return 'every second' if s == 1 else 'every %d seconds' % s


def _short(x):
    x = str(x or '')
    return x[:12] if len(x) == 64 and all(c in '0123456789abcdef' for c in x) else x


def _join(xs):
    xs = list(xs)
    if len(xs) <= 1:
        return ''.join(xs)
    return ', '.join(xs[:-1]) + ' and ' + xs[-1]


BASIS_WORDS = {'subscription': 'by the Card', 'agreement': 'by the Agreement', 'default': 'by the default'}


def render(rows):
    """One paragraph per source: what is heard, how often, where it is dealt, what may ring."""
    rows = [r for r in (rows if isinstance(rows, (list, tuple)) else []) if isinstance(r, dict)]
    if not rows:
        return '# Subscriptions\n\nNothing is followed: no Card, no Agreement, no joined cell.\n'
    out = ['# Subscriptions', '']
    for r in sorted(rows, key=lambda x: (_key(x.get('source')), str(x.get('source')))):
        cad = r.get('cadence') if isinstance(r.get('cadence'), dict) else {}
        by = {}
        for sig, sec in sorted(cad.items()):
            by.setdefault(words(sec), []).append(sig)
        heard = '; '.join('%s %s' % (_join(sigs), w) for w, sigs in
                          sorted(by.items(), key=lambda kv: (min(_seconds(cad[s]) or 0 for s in kv[1]), kv[0])))
        bell = r.get('bell') if isinstance(r.get('bell'), list) else []
        ring = 'may ring: %s' % _join(bell) if bell else 'rings nothing but the Andon kinds of a member'
        tail = ' · under Agreement %s' % _short(r.get('agreement')) if r.get('agreement') else ''
        out.append('- **%s** · %s · dealt to the %s · %s · %s%s'
                   % (_short(r.get('source')), heard or 'nothing heard', r.get('surface') or 'deal', ring,
                      BASIS_WORDS.get(r.get('basis'), 'basis unknown'), tail))
        for n in r.get('why') if isinstance(r.get('why'), list) else []:
            out.append('  - %s' % n)
    out.append('')
    out.append('A request addressed to the person or their agents rises first at the next pull, whatever the cadence.')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- command line

def _read_json(path, what):
    if os.path.islink(path):
        raise ValueError('%s %s is a link; it is not read' % (what, path))
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _read_lines(path):
    if os.path.islink(path):
        raise ValueError('%s is a link; it is not read' % path)
    out = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                v = json.loads(raw)
            except ValueError:
                continue
            if isinstance(v, dict):
                out.append(v)
    return out


def _main(argv=None):
    ap = argparse.ArgumentParser(description='What a holon hears, from whom, how often, and where.')
    ap.add_argument('lines', help='a JSONL file of record lines')
    ap.add_argument('--person', required=True)
    ap.add_argument('--items', help='a JSON file of folded items (record.py fold)')
    ap.add_argument('--home')
    ap.add_argument('--due', metavar='LAST.json', help='{source: {signal: iso}}: what was last seen')
    ap.add_argument('--now')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        lines = _read_lines(a.lines)
        items = _read_json(a.items, 'items') if a.items else None
        last = _read_json(a.due, 'last seen') if a.due else None
    except (OSError, ValueError) as e:
        print('subscriptions: %s' % e, file=sys.stderr)
        return 2
    rows = subscriptions(lines, a.person, items, a.now, home=a.home)
    if a.due is not None:
        if _moment(a.now) is None:
            print('subscriptions: --due needs --now, an ISO time', file=sys.stderr)
            return 2
        d = due(rows, last, a.now)
        if a.json:
            print(json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False))
        else:
            print('\n'.join('- %s · %s · due %s · %d s overdue' % (_short(x['source']), x['signal'], x['due_at'],
                                                                     x['overdue_s']) for x in d) or 'Nothing is due.')
        return 0
    if a.json:
        print(json.dumps(rows, indent=1, sort_keys=True, ensure_ascii=False))
    else:
        print(render(rows), end='')
    return 0


if __name__ == '__main__':
    sys.exit(_main())
