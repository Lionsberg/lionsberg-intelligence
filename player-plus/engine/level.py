#!/usr/bin/env python3
"""level.py — the level of a Card, computed from what it carries: the simplest Game that works.

    level_of(item_or_line, kind=None, registry=None) -> {kind, name, rung, of, has, lifts, why, claimed}
    minimum(kind, registry=None) -> {needs, gives}
    ladder(kind, registry=None)  -> [rung, ...]
    the_simplest_game()          -> [{say, line, ...}, ...]   the six lines, each with its plainest sentence
    levels(items, lines=None, holon=None, registry=None) -> {by_kind, below_minimum, claimed, as_of}
    render(levels_result)        -> Markdown, plain words

The Game plays very simply and very deep, and the simplest play works and can be worked out: by
voice with an agent, or on paper. Each Card kind has a minimum without which the Engine cannot
compute, and depths that give it more. The level of a Card is computed from what the Card carries,
never typed and never a gate: a lower level always plays, and nothing here changes what a Card may
do. The Engine says a Card's level and the field that would lift it, so an agent can draw out of its
person the minimum that makes the Game work, and offer the next depth only when it would change
the person's next play. The way deeper is the canon's Path; this kit carries pointers only.

THE LADDER (LADDER, one table; each rung {name, needs, gives}, in order from the minimum):

  card       named (title) · placed (links.within) · sized (minutes) ·
             chained (links.predecessor or links.successor) · resourced (tea, fiat or tokens_m)
  commit     works (card, by) · schedules (size, conditions) · auditable (buffer, witness) ·
             a clause (links.serves)
  request    asked (to; title or card) · dated (by) · accountable (why, effort) · shaped (shape, quorum)
  offer      asked (title or card) · accountable (why, effort) · shaped (shape, quorum)
  propose    asked (text) · accountable (why, effort) · shaped (shape, quorum)
  rfg        asked (to, question) · dated (by) · accountable (why, effort) · shaped (shape, quorum)
  say        (with intent: ask) asked (to, text) · accountable (why, effort) · shaped (shape, quorum)
  sight      seen (text) · placed (where) · kinded (kind) · carried (travel)
  agree      named (with) · termed (terms, crosses) · paced (cadence) · permitted (permits, face) ·
             bounded (until)
  condition  said (color, why) · dated (until)
  subscribe  chosen (source) · tuned (signals, cadence) · surfaced (surface, bell)

A need written `a|b` is met by either. `links.x` is one of the nine link kinds of the event line
(SCHEMA.md, **The event line**: LINKS below, the same as record.LINK_KEYS); every other need is a
body field of that type in types.json.

READ FROM THE REGISTRY. Every rung is read against types.json when it is used: a field the type does
not register is dropped from the rung, and a rung left with nothing is skipped, never invented.
Against the registry of 2026-10-31 (UNREGISTERED, which a test checks):
  - a Work Card's name is its `title`; its estimate is `minutes`; its three resource estimates are
    `tea`, `fiat` and `tokens_m`, and any one of them makes it resourced (an artificial Actor's work
    is counted in tokens, never TEA, so no Card carries all three by need).
  - `propose` registers no `to` (a proposal is put before the holon) and no `by`.
  - `offer` and `say` register no `by`: their dated rung is skipped.
  - `offer`: its `to` is optional in the registry and the fold makes the card from the title alone,
    so an offer put to the holon plays: its minimum is what is offered. (A departure from the
    first reading of the ladder, which named `to` for every ask.)
  - the ask's text is `title` (or the `card` it names) on a request and an offer, `text` on a
    propose and a say, `question` on an rfg.

THE PLACED RUNG counts only for a Work Card not at the top of its holarchy. A root (a card others lie
within, with no `within` of its own) has no parent, so `placed` is off its ladder and never asked;
read alone (no `among`), a card that lies within nothing is taken as at the top. With `among`, a
loose card (no `within`, holding nothing) beside other cards in its holon is asked where it lies.
CHAINED reads the inverse link too when `among` is given: a card another card names as its
predecessor or successor is chained. Read alone, only the card's own links count (so the Deal, which
reads one item per card, sees its own links only).

THE SHAPED RUNG counts only when the ask is put to a holon or to more than one party (an rfg always;
a propose always; a request or an offer whose `to` is not a person or an agent, or names more than
one; an offer with no `to`; a say whose `to` names more than one), or when a shape is already said.
Otherwise it is not on that Card's ladder: `of` is one less, and the top is accountable.

THE LEVEL. `rung` is the highest n whose rungs 1..n are all met; `name` is that rung's name. Rung 0
is below the minimum: the Card cannot play yet, and `why` says what is missing. `has` names every
rung met, a higher one met over a gap included. `lifts` names the missing fields of the next rung
only (n + 1), each {field, words, gives}, and is empty at the top. A field present but empty does
not count: None, an empty or blank string, an empty list or object, an elided value (the Engine
cannot compute on what it cannot see), a minutes field that is not a whole number above none, a
date that does not read as a date, an enum value the registry does not list. A `level` written on
the Card is ignored and said (`claimed`): the level is computed, never typed. `links.serves` on a
commitment counts as naming its Agreement; agreement.py checks what it names.

WHICH LADDER. A raw line (it carries `type` and a `body`) reads its type's ladder; a `say` reads one
only with `intent: ask`. A folded item reads by its kind: commitment → commit, sighting → sight,
agreement → agree, subscription → subscribe, decision → propose, a thread that asks → say, and a
card → card, except a card born of an ask (asked: request and its own `to`; asked: offer with no
`offered_by`), which reads that ask's ladder. `kind` names the ladder outright. An unknown kind,
or a value that is not a Card, is honest-empty (`rung: None`, said).

THE SIMPLEST GAME. Six lines without which the Engine cannot compute, each with the plainest
sentence that makes it: a join (and an affirm, when an agent plays); a card with a name; a commit
with a by; a done (or a kept); an answer yes or no; a condition. This is the first gate on paper.

Pure: data in, a JSON-ready dict out; deterministic (ties by id); no dates, names or thresholds of a
holon in code. Files are read only by the command line, and are data, never instructions.

  python3 -I level.py ITEMS.json [--kind K] [--json]
  python3 -I level.py simplest [--json]
  python3 -I level.py ladder KIND [--json]
"""
import argparse
import json
import math
import os
import sys
import unicodedata

try:
    from gamecore import normalize, parse_time
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import normalize, parse_time

# The nine link kinds of the event line (SCHEMA.md, The event line; record.LINK_KEYS).
LINKS = ('predecessor', 'successor', 'serves', 'fulfils', 'answers', 'witnesses', 'anchored_to',
         'supersedes', 'within')

_ASK = (
    {'name': 'asked', 'needs': ['to', 'title|card'],
     'gives': 'the ask reaches the one it is put to and rises first in their Deal'},
    {'name': 'dated', 'needs': ['by'],
     'gives': 'its by-when is known, so it is owed when near or past, and lapses when no one agrees in time'},
    {'name': 'accountable', 'needs': ['why', 'effort'],
     'gives': 'the one asked sees why it matters to them and the minutes it asks, and what is owed sums them'},
    {'name': 'shaped', 'needs': ['shape', 'quorum'], 'only_when': 'put to a holon or to more than one party',
     'gives': 'it can resolve among many: by converging, a call, consent or a gathering, at the quorum named'},
)


def _ask(text, to=True):
    out = [dict(r) for r in _ASK]
    out[0]['needs'] = (['to'] if to else []) + [text]
    return out


LADDER = {
    'card': [
        {'name': 'named', 'needs': ['title'],
         'gives': 'it can be dealt, held and done: the board and the Deal can show it'},
        {'name': 'placed', 'needs': ['links.within'], 'only_when': 'it is not at the top of its holarchy',
         'gives': 'it rolls up into the larger unit it lies within'},
        {'name': 'sized', 'needs': ['minutes'],
         'gives': "it schedules: its duration is its minutes over its holder's minutes a day"},
        {'name': 'chained', 'needs': ['links.predecessor|links.successor'],
         'gives': 'it has float: the two passes find what waits on it and what it waits on'},
        {'name': 'resourced', 'needs': ['tea|fiat|tokens_m'],
         'gives': 'what it consumes is counted (TEA, fiat or tokens) and summed up the holarchy'},
    ],
    'commit': [
        {'name': 'works', 'needs': ['card', 'by'],
         'gives': 'the commitment is compared with the computed finish of its card, and its gap is known when kept'},
        {'name': 'schedules', 'needs': ['size', 'conditions'],
         'gives': 'the schedule weighs it by its size and knows what it depends on'},
        {'name': 'auditable', 'needs': ['buffer', 'witness'],
         'gives': 'the buffer it states is compared, and a witness other than its committor can say Kept'},
        {'name': 'a clause', 'needs': ['links.serves'],
         'gives': 'it is a clause of the Agreement it serves, and counts in that relationship'},
    ],
    'request': _ask('title|card'),
    'offer': _ask('title|card', to=False),
    'propose': _ask('text'),
    'rfg': _ask('question'),
    'say': _ask('text'),
    'sight': [
        {'name': 'seen', 'needs': ['text'], 'gives': 'it is on the living map, and its lifecycle begins'},
        {'name': 'placed', 'needs': ['where'], 'gives': 'others passing the same place can sight it again, adding weight'},
        {'name': 'kinded', 'needs': ['kind'],
         'gives': 'it is read as what it is: a pain asks a response, a hazard warns, a defect is a gift'},
        {'name': 'carried', 'needs': ['travel'], 'gives': 'it may be elevated as far as its navigator allows, and no further'},
    ],
    'agree': [
        {'name': 'named', 'needs': ['with'],
         'gives': 'the relationship between the two holons is on the record, proposed until the other answers'},
        {'name': 'termed', 'needs': ['terms', 'crosses'], 'gives': 'what may cross between the two is known'},
        {'name': 'paced', 'needs': ['cadence'], 'gives': 'each hears the other at the cadence set, signal by signal'},
        {'name': 'permitted', 'needs': ['permits', 'face'],
         'gives': 'the permitted inbox and the bell follow its permits, and the face it reads is known'},
        {'name': 'bounded', 'needs': ['until'], 'gives': 'it expires when its until passes, and is said again'},
    ],
    'condition': [
        {'name': 'said', 'needs': ['color', 'why'], 'gives': "the holon's Condition travels on its face: its color and why"},
        {'name': 'dated', 'needs': ['until'], 'gives': 'it reads grey once its until passes, so it is said again in time'},
    ],
    'subscribe': [
        {'name': 'chosen', 'needs': ['source'], 'gives': 'the holon hears from that source, by pull'},
        {'name': 'tuned', 'needs': ['signals', 'cadence'], 'gives': 'it hears only the signals it chose, each at its cadence'},
        {'name': 'surfaced', 'needs': ['surface', 'bell'],
         'gives': 'it is dealt to the surface chosen, and only the kinds it permits may ring the bell'},
    ],
}

# What the registry of 2026-10-31 does not hold, per ladder kind: {kind: [field, ...]}. A test
# checks that ladder() drops exactly these, so a change in types.json is seen, never absorbed.
UNREGISTERED = {'propose': ['by', 'to'], 'offer': ['by'], 'say': ['by']}

# A field said in words, for the one asked (per kind where the plain word differs).
FIELD_WORDS = {
    'title': 'a name', 'links.within': 'the larger card it lies within', 'minutes': 'a size in minutes',
    'links.predecessor|links.successor': 'a card that comes before it or after it',
    'tea|fiat|tokens_m': 'what it consumes: TEA, money or tokens',
    'card': 'the card it delivers', 'by': 'a by-when', 'size': 'its size in minutes', 'conditions': 'its conditions',
    'buffer': 'a buffer in minutes', 'witness': 'a witness who can say it was kept',
    'links.serves': 'the Agreement it serves',
    'to': 'whom it is put to', 'title|card': 'what is asked', 'text': 'what is said', 'question': 'the question',
    'why': 'why it matters to the one asked', 'effort': 'the minutes it asks of them',
    'shape': 'how it resolves (converge, call, consent or gather)', 'quorum': 'who must answer for it to resolve',
    'where': 'where it was seen', 'kind': 'what kind of thing it is', 'travel': 'how far it may travel',
    'with': 'the other holon', 'terms': 'its terms', 'crosses': 'what may cross',
    'cadence': 'how often each hears the other', 'permits': 'what it permits', 'face': 'the face it reads',
    'until': 'when it ends', 'color': 'a color (green, yellow, orange or red)', 'source': 'what it hears from',
    'signals': 'which signals it hears', 'surface': 'where it is dealt', 'bell': 'which kinds may ring the bell',
}
FIELD_WORDS_BY_KIND = {
    ('offer', 'title|card'): 'what is offered', ('propose', 'text'): 'what is proposed',
    ('condition', 'why'): 'why, in one line', ('condition', 'until'): 'when to say it again',
    ('subscribe', 'cadence'): 'how often it is heard', ('agree', 'until'): 'until when it stands',
}
KIND_WORDS = {
    'card': ('Work Card', 'Work Cards'), 'commit': ('commitment', 'Commitments'), 'request': ('request', 'Requests'),
    'offer': ('offer', 'Offers'), 'propose': ('proposal', 'Proposals'), 'rfg': ('question', 'Questions that climb'),
    'say': ('ask in a thread', 'Asks in a thread'), 'sight': ('Sighting', 'Sightings'),
    'agree': ('Agreement', 'Agreements'), 'condition': ('Condition', 'Conditions'),
    'subscribe': ('Subscription Card', 'Subscription Cards'),
}
ITEM_LADDER = {'card': 'card', 'commitment': 'commit', 'sighting': 'sight', 'agreement': 'agree',
               'subscription': 'subscribe', 'decision': 'propose', 'thread': 'say'}
ALIASES = {'commitment': 'commit', 'sighting': 'sight', 'agreement': 'agree', 'subscription': 'subscribe',
           'proposal': 'propose', 'decision': 'propose', 'question': 'rfg', 'work card': 'card', 'thread': 'say'}
# A folded item's own envelope keys: a body field of the same name sits at body_<name> (record._new_item).
ITEM_KEYS = ('id', 'kind', 'holon', 'state', 'actor', 'for', 'ts', 'events', 'held_in', 'links')
BELOW = 'below the minimum'
ACTOR_PREFIXES = ('person:', 'agent:')

_REGISTRY = None


def _nfc(s):
    return unicodedata.normalize('NFC', s) if isinstance(s, str) else s


def _load_registry():
    global _REGISTRY
    if _REGISTRY is None:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'types.json'), encoding='utf-8') as f:
                t = json.load(f)
            _REGISTRY = t.get('types') if isinstance(t, dict) and isinstance(t.get('types'), dict) else {}
        except (OSError, ValueError):
            _REGISTRY = {}
    return _REGISTRY


def _types(registry):
    """The registry's types, from the whole types.json, its `types` part, or the file beside this module."""
    if isinstance(registry, dict):
        if isinstance(registry.get('types'), dict):
            return registry['types']
        return registry
    return _load_registry()


def _fields(kind, registry):
    """{field name: (kind, values)} for a type, or None when the registry does not hold the type."""
    t = _types(registry).get(kind)
    if not isinstance(t, dict) or not isinstance(t.get('fields'), list):
        return None
    out = {}
    for f in t['fields']:
        if isinstance(f, dict) and isinstance(f.get('name'), str):
            out[f['name']] = (f.get('kind'), f.get('values') if isinstance(f.get('values'), list) else None)
    return out


def _known(a, fields):
    """Whether one need is registered: a link kind of the event line, or a body field of the type."""
    return a[6:] in LINKS if a.startswith('links.') else a in fields


def _registered(need, fields):
    return [a for a in need.split('|') if _known(a, fields)]


def _kind_name(kind):
    if not isinstance(kind, str):
        return None
    k = _nfc(kind).strip().lower()
    k = ALIASES.get(k, k)
    return k if k in LADDER else None


def ladder(kind, registry=None):
    """The ladder of a kind as the registry holds it: [{n, name, needs, gives, words, only_when?}, ...].
    A field the type does not register is dropped; a rung left with nothing is skipped. [] when unknown."""
    k = _kind_name(kind)
    fields = _fields(k, registry) if k else None
    if fields is None:
        return []
    out = []
    for r in LADDER[k]:
        needs = []
        for need in r['needs']:
            alts = _registered(need, fields)
            if alts:
                needs.append('|'.join(alts))
        if not needs:
            continue
        rung = {'n': len(out) + 1, 'name': r['name'], 'needs': needs, 'gives': r['gives'],
                'words': [_words(k, x) for x in needs]}
        if r.get('only_when'):
            rung['only_when'] = r['only_when']
        out.append(rung)
    return out


def unregistered(kind, registry=None):
    """The fields LADDER names for a kind that the registry does not hold, sorted."""
    k = _kind_name(kind)
    fields = _fields(k, registry) if k else None
    if fields is None:
        return []
    miss = set()
    for r in LADDER[k]:
        for need in r['needs']:
            for a in need.split('|'):
                if not _known(a, fields):
                    miss.add(a)
    return sorted(miss)


def minimum(kind, registry=None):
    """The minimum of a kind: {needs, gives} (the first rung), or {needs: [], gives: None} when unknown."""
    lad = ladder(kind, registry)
    if not lad:
        return {'needs': [], 'gives': None}
    return {'needs': list(lad[0]['needs']), 'gives': lad[0]['gives']}


def _words(kind, need):
    return FIELD_WORDS_BY_KIND.get((kind, need)) or FIELD_WORDS.get(need) or need.replace('|', ' or ')


def _is_line(x):
    return isinstance(x, dict) and isinstance(x.get('type'), str) and isinstance(x.get('body'), dict)


def _raw(x, name, line):
    if name.startswith('links.'):
        L = x.get('links')
        return L.get(name[6:]) if isinstance(L, dict) else None
    if line:
        return x['body'].get(name)
    v = x.get('body_' + name) if name in ITEM_KEYS else x.get(name)
    if v is None and isinstance(x.get('body'), dict):
        v = x['body'].get(name)
    return v


def _present(v, fkind=None, values=None):
    """Whether a value counts: present, not empty, not elided, and of the shape its registry kind says."""
    if v is None:
        return False
    if isinstance(v, bool):
        return fkind in ('bool', None)
    if isinstance(v, dict):
        return bool(v) and 'elided' not in v and fkind in ('object', None)
    if isinstance(v, (list, tuple)):
        return fkind in ('list', 'actors', 'ids', None) and any(_present(e) for e in v)
    if fkind == 'minutes':
        return isinstance(v, int) and v > 0
    if isinstance(v, int):
        return fkind in ('number', 'int', None)
    if isinstance(v, float):
        return math.isfinite(v) and fkind in ('number', None)
    if isinstance(v, str):
        s = v.strip()
        if not s or fkind in ('object', 'list', 'number', 'int'):
            return False
        if fkind in ('date', 'datetime'):
            return parse_time(s) is not None
        if fkind == 'enum' and values:
            return _nfc(s) in values
        return True
    return False


def _has(x, need, line, fields):
    for a in need.split('|'):
        if a.startswith('links.'):
            if _present(_raw(x, a, line)):
                return True
            continue
        fk, vals = fields.get(a, (None, None))
        if _present(_raw(x, a, line), fk, vals):
            return True
    return False


def _resolve(x, kind):
    """(ladder kind, a sentence when there is none)."""
    if kind is not None:
        k = _kind_name(kind)
        return (k, None) if k else (None, 'there is no ladder for the kind %r' % (_nfc(kind) if isinstance(kind, str) else kind))
    if _is_line(x):
        t = _nfc(x['type'])
        if t == 'say':
            return ('say', None) if x['body'].get('intent') == 'ask' else (None, 'a say that asks nothing has no ladder')
        return (t, None) if t in LADDER else (None, 'a %s line has no ladder' % t)
    ik = x.get('kind') if isinstance(x.get('kind'), str) else None
    ik = _nfc(ik.strip().lower()) if ik else None
    k = ITEM_LADDER.get(ik)
    if k is None:
        return None, ('an item of kind %r has no ladder' % ik if ik else 'an item with no kind has no ladder')
    if k == 'say' and _raw(x, 'intent', False) != 'ask':
        return None, 'a thread that asks nothing has no ladder'
    if k == 'card':
        asked = x.get('asked')
        if asked == 'request' and _present(x.get('to')):
            k = 'request'
        elif asked == 'offer' and x.get('offered_by') is None:
            k = 'offer'
    return k, None


def _claimed(x, line):
    """A level written on the Card, kept only to say it was ignored."""
    if line:
        v = x['body'].get('level')
    else:
        v = x.get('level')
        if v is None and isinstance(x.get('body'), dict):
            v = x['body'].get('level')
    if v is None:
        return None
    if isinstance(v, str):
        return _nfc(v)
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    try:
        return json.dumps(v, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return str(v)


def _applies(rung, x, line, k, index=None):
    """Whether a conditional rung (a card's placed, an ask's shaped) is on this Card's ladder."""
    if not rung.get('only_when'):
        return True
    if k == 'card' and rung['name'] == 'placed':
        if _present(_raw(x, 'links.within', line)):
            return True
        if index is None:
            return False                  # read alone, a card that lies within nothing is at the top
        cid = x.get('id')
        if cid in index['units']:
            return False                  # a root: others lie within it, and it has no parent
        return index['cards_in'].get(x.get('holon'), 0) > 1   # a loose card beside others is asked where it lies
    if _present(_raw(x, 'shape', line)) or _present(_raw(x, 'quorum', line)):
        return True
    if k in ('rfg', 'propose'):
        return True
    to = _raw(x, 'to', line)
    if isinstance(to, (list, tuple)):
        named = [t for t in to if isinstance(t, str) and t.strip()]
        return len(named) > 1 or (len(named) == 1 and not named[0].startswith(ACTOR_PREFIXES))
    if isinstance(to, str) and to.strip():
        return k != 'say' and not to.strip().startswith(ACTOR_PREFIXES)
    return k == 'offer'


def _empty(kind, why, claimed=None):
    return {'kind': kind, 'name': None, 'rung': None, 'of': None, 'has': [], 'lifts': [], 'why': why,
            'claimed': claimed}


def index_of(items):
    """What one Card cannot show of itself, read across the fold's items: {units: ids some card lies
    within, linked: ids another card names as its predecessor or successor, cards_in: {holon: n}}."""
    norm = normalize(items) if items else {}
    units, linked, cards_in = set(), set(), {}
    for c in norm.get('card', []) or []:
        if not isinstance(c, dict) or str(c.get('state') or '') == 'retracted':
            continue
        h = c.get('holon') if isinstance(c.get('holon'), str) else None
        cards_in[h] = cards_in.get(h, 0) + 1
        L = c.get('links') if isinstance(c.get('links'), dict) else {}
        for rel, dest in (('within', units), ('predecessor', linked), ('successor', linked)):
            v = L.get(rel)
            for i in ([v] if isinstance(v, str) else v if isinstance(v, (list, tuple)) else []):
                if isinstance(i, str) and i and i != c.get('id'):
                    dest.add(i)
    return {'_level_index': True, 'units': units, 'linked': linked, 'cards_in': cards_in}


def _as_index(among):
    if among is None:
        return None
    if isinstance(among, dict) and among.get('_level_index') is True:
        return among
    return index_of(among)


def level_of(item_or_line, kind=None, registry=None, among=None):
    """The level of one Card: {kind, name, rung, of, has, lifts: [{field, words, gives}], why, claimed}.
    Pure. Reads a folded item, or a raw line by its body. `among` (the fold's items, or index_of them)
    lets a Work Card be read with what it cannot show alone: whether it is a root, and the links other
    cards make to it. Honest-empty for what has no ladder."""
    x = item_or_line
    if not isinstance(x, dict) or not x:
        return _empty(None, 'there is no Card here to read')
    line = _is_line(x)
    k, why = _resolve(x, kind)
    if k is None:
        return _empty(None, why)
    claimed = _claimed(x, line)
    fields = _fields(k, registry)
    lad = ladder(k, registry)
    if fields is None or not lad:
        return _empty(k, 'the type registry does not hold %s, so its level cannot be read' % k, claimed)
    index = _as_index(among) if k == 'card' else None
    lad = [r for r in lad if _applies(r, x, line, k, index)]
    given = set()
    if index is not None and x.get('id') in index['linked']:
        given.add('links.predecessor|links.successor')     # chained by another card's link to it

    def has(n):
        return n in given or _has(x, n, line, fields)
    met = [r['name'] for r in lad if all(has(n) for n in r['needs'])]
    rung = 0
    for r in lad:
        if r['name'] in met:
            rung += 1
        else:
            break
    lifts = []
    if rung < len(lad):
        nxt = lad[rung]
        for n in nxt['needs']:
            if not has(n):
                lifts.append({'field': n, 'words': _words(k, n), 'gives': nxt['gives']})
    one, _ = KIND_WORDS[k]
    if rung == 0:
        miss = ' and '.join(l['words'] for l in lifts) or 'its minimum'
        why = 'Below the minimum: this %s does not yet carry %s, so the Engine cannot compute it.' % (one, miss)
    else:
        top = lad[rung - 1]
        why = 'This %s stands at %s, rung %d of %d: %s.' % (one, top['name'], rung, len(lad), top['gives'])
        if lifts:
            why += ' With %s, %s.' % (' and '.join(l['words'] for l in lifts), lad[rung]['gives'])
        else:
            why += ' It is at the top of its ladder.'
    if claimed is not None:
        why += ' A level written on the Card (%s) is ignored: the level is computed from what it carries.' % claimed
    return {'kind': k, 'name': lad[rung - 1]['name'] if rung else BELOW, 'rung': rung, 'of': len(lad),
            'has': met, 'lifts': lifts, 'why': why, 'claimed': claimed}


def the_simplest_game():
    """The six lines without which the Engine cannot compute, each with the plainest sentence that
    makes it, as a role would say it. `line` is {type, fields: {name: what to put, in words}, links?};
    `also` and `or` are the second line one sentence may make. The first gate on paper."""
    return [
        {'say': 'I join this holon, and my agent may act here with me.',
         'line': {'type': 'join', 'fields': {'who': 'the one who joins',
                                             'pubkey': 'their public key, when lines are signed'}},
         'also': {'type': 'affirm', 'fields': {'agent': 'the agent let in, when an agent plays'}},
         'note': 'On paper the one who joins writes it; with keys, someone already in the holon writes it '
                 'naming the newcomer. A holon begins with its own join.'},
        {'say': 'Here is a piece of work: mend the gate.',
         'line': {'type': 'card', 'fields': {'title': 'its name'}}},
        {'say': 'I will do it by Friday.',
         'line': {'type': 'commit', 'fields': {'card': 'the card', 'by': 'the date it will be done by'}}},
        {'say': 'It is done.',
         'line': {'type': 'done', 'fields': {'card': 'the card'}},
         'or': {'type': 'kept', 'fields': {'commitment': 'the commitment kept'}}},
        {'say': 'Yes, that works for me.',
         'line': {'type': 'answer', 'fields': {'answer': 'accept, or decline for no'},
                  'links': {'answers': 'the commitment or the ask it answers'}}},
        {'say': 'We are green: all is on track.',
         'line': {'type': 'condition', 'fields': {'color': 'green, yellow, orange or red', 'why': 'why, in one line'}}},
    ]


def _ts(x):
    v = x.get('ts') if isinstance(x, dict) else None
    return v if isinstance(v, str) and parse_time(v) else None


def levels(items, lines=None, holon=None, registry=None, kind=None):
    """A holon's Cards by level, for the Board: {by_kind: {kind: {rung name: n}}, below_minimum: [ids],
    claimed: [ids], count, as_of}. Items are the fold's; `lines` add the Cards that make no item (a
    condition, an rfg, a say that asks with no thread). Retracted items are left out. Deterministic."""
    norm = normalize(items) if items else {}
    want = _kind_name(kind) if kind is not None else None
    seen, entries = set(), []
    for ik in sorted(ITEM_LADDER):
        for it in norm.get(ik, []) or []:
            if not isinstance(it, dict) or str(it.get('state') or '') == 'retracted':
                continue
            if holon is not None and it.get('holon') != holon:
                continue
            iid = it.get('id') if isinstance(it.get('id'), str) else None
            if iid:
                seen.add(iid)
            entries.append((iid or '', it))
    for ln in lines if isinstance(lines, list) else []:
        if not _is_line(ln) or ln['type'] not in ('condition', 'rfg', 'say'):
            continue
        if ln['type'] == 'say' and ln['body'].get('intent') != 'ask':
            continue
        lid = ln.get('id') if isinstance(ln.get('id'), str) else ''
        if lid in seen or (holon is not None and ln.get('holon') != holon):
            continue
        seen.add(lid)
        entries.append((lid, ln))
    index = index_of(norm)
    by_kind, below, claimed, newest, n = {}, [], [], None, 0
    for iid, x in sorted(entries, key=lambda e: e[0]):
        lv = level_of(x, registry=registry, among=index)
        if lv['rung'] is None or (want and lv['kind'] != want):
            continue
        n += 1
        row = by_kind.setdefault(lv['kind'], {})
        row[lv['name']] = row.get(lv['name'], 0) + 1
        if lv['rung'] == 0:
            below.append(iid)
        if lv['claimed'] is not None:
            claimed.append(iid)
        t = _ts(x)
        if t and (newest is None or parse_time(t) > parse_time(newest)):
            newest = t
    return {'by_kind': {k: dict(sorted(v.items())) for k, v in sorted(by_kind.items())},
            'below_minimum': sorted(below), 'claimed': sorted(claimed), 'count': n, 'holon': holon,
            'as_of': newest}


def render(levels_result):
    """Markdown in plain words: how many Cards stand at each level, kind by kind."""
    r = levels_result if isinstance(levels_result, dict) else {}
    out = ['# Levels of play', '']
    if r.get('as_of'):
        out += ['As of the newest Card read: %s.' % r['as_of'], '']
    bk = r.get('by_kind') if isinstance(r.get('by_kind'), dict) else {}
    if not bk:
        out.append('No Cards to read yet.')
        return '\n'.join(out) + '\n'
    for k in sorted(bk):
        if k not in LADDER:
            continue
        out.append('## ' + KIND_WORDS[k][1])
        names = [BELOW] + [x['name'] for x in LADDER[k]]
        row = bk[k] if isinstance(bk[k], dict) else {}
        for nm in names + sorted(set(row) - set(names)):
            c = row.get(nm)
            if isinstance(c, int) and not isinstance(c, bool) and c > 0:
                out.append('- %s: %d' % (nm, c))
        out.append('')
    below = r.get('below_minimum') or []
    if below:
        out.append('Cannot play yet, each missing its minimum: %s.' %
                   ', '.join(str(i)[:8] or '(no id)' for i in below))
    else:
        out.append('Every Card read carries its minimum, so every one plays.')
    if r.get('claimed'):
        out.append('A level written on %d Card%s was ignored: the level is computed from what a Card carries.'
                   % (len(r['claimed']), '' if len(r['claimed']) == 1 else 's'))
    return '\n'.join(out) + '\n'


def _render_simplest(rows):
    out = ['# The simplest Game that works', '', 'Six lines, each said in one sentence:', '']
    for i, r in enumerate(rows, 1):
        ln = r['line']
        extra = ''
        if r.get('also'):
            extra = ' (and `%s`)' % r['also']['type']
        if r.get('or'):
            extra = ' (or `%s`)' % r['or']['type']
        out.append('%d. "%s" makes `%s`%s with %s.' % (i, r['say'], ln['type'], extra, ', '.join(ln['fields'])))
    return '\n'.join(out) + '\n'


def _render_ladder(kind, rows):
    if not rows:
        return 'There is no ladder for %s.\n' % kind
    out = ['# The ladder of a %s' % KIND_WORDS[_kind_name(kind)][0], '']
    for r in rows:
        out.append('%d. **%s**: needs %s. Then %s.%s' % (r['n'], r['name'], ' and '.join(r['words']), r['gives'],
                                                       (' Counts only when %s.' % r['only_when']) if r.get('only_when') else ''))
    return '\n'.join(out) + '\n'


def _read_json(path):
    if not isinstance(path, str) or not path or os.path.islink(path):
        return None, 'not read: %s is missing or a link' % path
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f), None
    except (OSError, ValueError) as e:
        return None, 'not read: %s (%s)' % (path, e.__class__.__name__)


def _main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = '--json' in argv
    argv = [a for a in argv if a != '--json']
    if argv and argv[0] == 'simplest':
        rows = the_simplest_game()
        sys.stdout.write(json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False) + '\n' if as_json
                         else _render_simplest(rows))
        return 0
    if argv and argv[0] == 'ladder':
        k = argv[1] if len(argv) > 1 else ''
        rows = ladder(k)
        sys.stdout.write(json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False) + '\n' if as_json
                         else _render_ladder(k, rows))
        return 0 if rows else 1
    ap = argparse.ArgumentParser(description='The level of each Card, computed from what it carries.')
    ap.add_argument('items')
    ap.add_argument('--kind')
    a = ap.parse_args(argv)
    data, err = _read_json(a.items)
    if err:
        sys.stderr.write(err + '\n')
        return 1
    res = levels(data, kind=a.kind)
    sys.stdout.write(json.dumps(res, indent=2, sort_keys=True, ensure_ascii=False) + '\n' if as_json else render(res))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
