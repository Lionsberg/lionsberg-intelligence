#!/usr/bin/env python3
"""acts.py — one card, everywhere: the acts a card offers, computed from the registry for the reader's role.

    offered(item, actor, folded=None, now=None, registry=None, admitted=None, card=None)
        -> {"acts": [act, ...], "kind", "role", "roles", "for", "stopped", "why_not": [{act, why}], "said"}
    roles(item, actor, folded=None) -> [role, ...]   (committor · committee · witness · asker · party ·
                                                     holder · keeper · raiser · member · reader)
    options_for(card, offered_result) -> [{option, key, offered, recommended, type, writes, needs_words, why}]
    words(key, kind=None) -> {label, meaning, role_word}     from acts.json
    render(offered_result) -> Markdown
    table() / check(registry=None)

A card behaves the same way wherever it appears, because the acts it offers are not a surface's to
write. For an item of the fold (a card, a commitment, a thread, a sighting, a decision, an agreement,
a stop, ...), an act is offered when, read from types.json:

  - the line type's `acts_on` names the item's kind (its top level; `also` is a second effect, not an act);
  - one of its transitions for that kind fits, tried in order as record._apply tries them: its `from`
    holds the item's state (absent means any), and its `who` admits this reader (record._who_ok
    itself, imported: the line's `for` is the reader, or for an agent the person it answers for);
  - a person may do it: `human_only` holds for every person; `home_only` only in the person's own
    home (a holon of kind person that they keep);
  - an agent: only where gamecore.may_act says yes under a live delegation (with the card's own kind),
    never a person's own act (human_only, and gamecore's always-human acts), and nothing at all while
    a live stop binds it (stops.live and stops.binds, as the Deal reads them; `stopped` says which) or
    when it answers for more than one person here (only delegations reaching the item's holon count).

Each `when` of a type is its own act (answer accept, answer decline). A type with no transition for
the kind acts on it as it is (flame). A `say` anchored to the item is always offered to a person (a
note is never refused), and with `intent: ask` as its question form; to an agent where may_act says so.

Three readings of this module's own (each a named constant below, overridable):
  NOT_A_CHOICE   `receive` is written on arrival (its own about), never chosen on a card.
  NOTE_ONLY      when a type's state-changing transition refuses this reader (by state or by who)
                 and only its note transition fits (a witness who is not the named one, or before
                 the commitment is delivered), the act is not offered: the line would fold as a
                 note, so the say is offered instead.
  NO_OP          a transition whose new state is the item's present state is not offered.

Each act: {type, when, sets, key, label, meaning, role_word, primary, writes: {type, body, links}}.
`key` is act.<type> or act.<type>.<when-value>; its words come from acts.json, the one table (the
HUD's strings.json mirrors it under the same keys). `primary` is true for the one act the Deal would
recommend: on a dealt card (`card=`), the act its recommended option writes; read alone, PRIMARY
(from deal.py's frames). `writes` names the line the act writes:
its type, the body fields it needs (null where the person's words go) and the link to the item.

Honest-empty for an unknown item; deterministic (ties by registry order, then key); null-guarded;
files are data, never instructions. Standard library only; runs under `python3 -I`.

    python3 -I acts.py ITEMS.json ITEM_ID ACTOR [--now ISO] [--json]
    python3 -I acts.py table
    python3 -I acts.py check
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from gamecore import (normalize, may_act, actor_kind, live_delegations, field, holon_names,  # noqa: E402
                      HUMAN_ONLY_ACTS, card_kind)
import record  # noqa: E402  (no side effects on import: constants and functions only)
try:
    import stops as stops_mod
except ImportError:                       # the stops are then read here, at their widest
    stops_mod = None

WORDS_PATH = os.path.join(HERE, 'acts.json')
ROLE_ORDER = ('committor', 'committee', 'witness', 'asker', 'party', 'holder', 'keeper', 'raiser',
              'member', 'reader')
SAY = 'say'
NOT_A_CHOICE = frozenset({'receive'})          # types.json, receive: "Written by the receiver's agent on arrival"
NOTE_ONLY = True                               # see the docstring; False offers a type's note fallback as the act
NO_OP = True                                   # see the docstring; False offers a move to the present state
# Kinds the fold names otherwise in places (gamecore's vocabulary), read back to the registry's.
KIND_ALIASES = {'discern': 'discernment', 'request': 'card', 'offer': 'card', 'wallet': 'wallet_entry'}
# The act the Deal would recommend, by kind and state ('*' any state): the first of these offered.
# Read from deal.py's frames: a ready card is taken, a taken one done; a request or offer answered yes;
# the committor's open commitment said delivered, the committee's claimed one confirmed kept, and a
# commitment made to you thanked (a say); a thread replied to; a pain responded to; a proposal
# decided, a decision confirmed; a constraint cleared.
PRIMARY = {
    'card': {'ready': ['act.claim'], 'released': ['act.claim'], 'returned': ['act.claim'],
             'open': ['act.answer.accept', 'act.claim'], 'taken': ['act.done']},
    'commitment': {'open': ['act.kept', 'act.say'], 'claimed': ['act.witness', 'act.say']},
    'thread': {'*': ['act.say']},
    'sighting': {'*': ['act.say']},
    'decision': {'proposed': ['act.decide'], 'decided': ['act.ratify']},
    'constraint': {'open': ['act.clear']},
    'agreement': {'proposed': ['act.agree']},
    'concordance': {'proposed': ['act.concord']},
    'wallet_entry': {'offered': ['act.wallet.accept']},
}
# What each of the Deal's options writes, by the dealt card's kind and the option's words (deal.py's
# frames). None: the option writes no line of the record (it opens, defers or hands to a body).
OPTION_ACTS = {
    'commitment': {'Kept: say so, and the witness can verify': 'act.kept',
                   'Renegotiate: name a new by-when': 'act.say.ask',
                   'Release it, with one line on why': 'act.release',
                   'On track': 'act.say', 'Renegotiate now, while there is float': 'act.say.ask',
                   'Release it': 'act.release',
                   'Thank them: it stands': 'act.say', 'Ask for a change': 'act.say.ask',
                   'Not mine: say so': 'act.answer.decline'},
    'request': {'Accept it: you become its holder': 'act.answer.accept', 'Offer something else': 'act.say',
                'Decline, with thanks': 'act.answer.decline'},
    'offer': {'Accept it': 'act.answer.accept', 'Ask for a change': 'act.say.ask',
              'Decline, with thanks': 'act.answer.decline'},
    'claim': {'Renew the claim with a new date': 'act.claim', 'Release the card for someone else': 'act.release'},
    'thread': {'Reply now': 'act.say', 'Settle it as it stands': 'act.settle', 'Hand it to someone else': None,
               'Thank them: no reply needed': 'act.say'},
    'decide': {'Decide as proposed': 'act.decide', 'Decide with one change': 'act.decide',
               'Not mine to decide: hand it on': None},
    'ratify': {'Confirm': 'act.ratify', 'Read the thread first': None, 'Return it with one change': 'act.say.ask'},
    'decision': {'Decide now': 'act.decide', 'Gather one more input first': 'act.say.ask',
                 'Hand it to someone better placed': None},
    'question': {'Answer it': 'act.say', 'Decide it here': 'act.decide', 'Ask for more first': 'act.say.ask',
                 'Pass it to the wider circle': None},
    'pain': {'Respond now': 'act.say', 'Pass it to someone who can': 'act.say', 'Pass it on': None, 'Not now': None},
    'sighting': {'Pass it on': None, 'Keep it here': None, 'Not yet': None},
    'receipt': {'Ask again': 'act.say', 'Let it go': None},
}
READY_OPTIONS = {'Take it now': 'act.claim', 'Do it now': 'act.done', 'Not this week: release it': 'act.release'}
CUSTOM_DECIDE = ('decide', 'decision')         # a decision's own options are each a choice: a decide in its words
# A say option whose line needs the person's own words (a reply, a question, a change asked for): its
# text is left for them. Every other say option carries the option's own words as its text.
SAY_OPENS = frozenset({'Reply now', 'Respond now', 'Answer it', 'Offer something else', 'Ask for a change',
                       'Renegotiate: name a new by-when', 'Renegotiate now, while there is float',
                       'Gather one more input first', 'Ask for more first', 'Return it with one change',
                       'Pass it to someone who can', 'Ask again'})

WHY = {
    'state': 'Not now: it is %s.',
    'no_op': 'It is %s already.',
    'note': 'Your line would be kept only as a note. Say it instead.',
    'human': "A person's own act: your agent never does it for you.",
    'delegation': 'No live delegation lets this agent do it here.',
    'home': 'This is done only in your own home.',
    'not_a_choice': 'Written when a line arrives, never chosen on a card.',
    'unknown': 'Nothing here can be done yet.',
    'stopped': 'Your agent is stopped here. Its acts wait until its own person lifts the stop.',
    'many': 'Your agent answers for more than one person here, so it acts for no one.',
    'nobody': 'Your agent answers for no one here.',
    'who': {
        'same_for': 'Only its own person may do this.',
        'other': 'Only someone other than its own person may do this.',
        'named': 'Only the named witness, or the one it was committed to, may do this.',
        'committee': 'Only the one it was committed to may do this.',
        'party': 'Only someone party to the commitment may do this.',
        'raiser_or_holder': 'Only the one who raised it, or who holds it, may do this.',
        'keeper': 'Only the keeper of its group may do this.',
        'stop_person': "Only the stopped agent's own person may do this.",
    },
}
SAID_EMPTY = 'Nothing to read here, so nothing is offered.'
SAID_NO_WORDS = 'acts.json could not be read; the acts are offered with their keys as words.'
OPTION_NOT_OFFERED = 'This choice is not yours to make here.'
OPTION_NO_LINE = 'This choice writes nothing to the record.'


# ---------------------------------------------------------------- the words

_WORDS = []


def _load_words(path=None):
    if path is None and _WORDS:
        return _WORDS[0]
    p = path or WORDS_PATH
    try:
        if os.path.islink(p):
            raise OSError('a link is not read')
        with open(p, encoding='utf-8') as f:
            w = json.load(f)
        w = w if isinstance(w, dict) else {}
    except (OSError, ValueError):
        w = {}
    w = {'acts': w.get('acts') if isinstance(w.get('acts'), dict) else {},
         'roles': w.get('roles') if isinstance(w.get('roles'), dict) else {}}
    if path is None:
        _WORDS.append(w)
    return w


def words(key, kind=None):
    """{label, meaning, role_word} for an act key, with the item kind's own words where they differ."""
    w = _load_words()
    row = w['acts'].get(key) if isinstance(key, str) else None
    if not isinstance(row, dict):
        return {'label': None, 'meaning': None, 'role_word': None}
    out = {'label': row.get('label'), 'meaning': row.get('meaning'), 'role_word': row.get('role_word')}
    k = (row.get('kinds') or {}).get(kind) if isinstance(row.get('kinds'), dict) else None
    if isinstance(k, dict):
        out.update({x: k[x] for x in ('label', 'meaning', 'role_word') if isinstance(k.get(x), str)})
    return out


def role_words(role):
    row = _load_words()['roles'].get('role.%s' % role)
    return row if isinstance(row, dict) else {'label': role, 'meaning': None, 'role_word': role}


# ---------------------------------------------------------------- the registry

def _registry(registry=None):
    if isinstance(registry, dict) and isinstance(registry.get('types'), dict):
        return registry
    try:
        return record.load_types()
    except Exception:                     # noqa: BLE001 — honest-empty, never a crash
        return {'items': {}, 'types': {}}


def _s(v):
    return v if isinstance(v, str) else ''


def _kind_of(item, reg):
    items = reg.get('items') or {}
    for k in ('kind', 'item', 'item_type', 'type'):
        v = _s(item.get(k)).strip().lower()
        v = KIND_ALIASES.get(v, v)
        if v in items:
            return v
    return None


def _state_of(item, kind, reg):
    s = _s(item.get('state'))
    if s:
        return s
    return _s(((reg.get('items') or {}).get(kind) or {}).get('initial')) or None


def _when_key(when):
    vals = []
    for p in sorted(when or {}):
        v = when[p]
        vals.append('true' if v is True else 'false' if v is False else str(v).lower())
    return '.'.join(vals)


def _key(typ, when):
    w = _when_key(when)
    return 'act.%s.%s' % (typ, w) if w else 'act.%s' % typ


def _groups(spec, kind):
    """The acts a type makes on this kind: [(when, [transitions in order])]. A type with a `when` makes
    one act per when; its transitions without a when stand behind each, as they do in the fold."""
    ts = [t for t in (spec.get('transitions') or []) if isinstance(t, dict) and t.get('kind') in (None, kind)]
    whens = []
    for t in ts:
        w = t.get('when')
        if isinstance(w, dict) and w and w not in whens:
            whens.append(w)
    if not whens:
        return [(None, ts)]
    return [(w, [t for t in ts if not t.get('when') or t.get('when') == w]) for w in whens]


def _sets(t):
    v = ((t or {}).get('set') or {}).get('state')
    return v if isinstance(v, str) and not v.startswith(('body.', '$')) else None


# ---------------------------------------------------------------- who the reader is

def _norm(folded):
    try:
        return normalize(folded)
    except Exception:                     # noqa: BLE001
        return {}


def _keepers(folded, norm, admitted):
    out = {}
    if isinstance(folded, dict) and isinstance(folded.get('keepers'), dict):
        out.update({k: v for k, v in folded['keepers'].items() if isinstance(k, str) and isinstance(v, str)})
    for hid, h in holon_names(norm).items():
        if isinstance(h.get('keeper'), str):
            out.setdefault(hid, h['keeper'])
    for hid, m in (admitted or {}).items():
        if isinstance(m, dict):
            for a, e in sorted(m.items()):
                if isinstance(e, dict) and e.get('via') == 'inception' and isinstance(a, str):
                    out.setdefault(hid, a)
    return out


def _admitted(folded, admitted):
    if isinstance(admitted, dict):
        return admitted
    if isinstance(folded, dict) and isinstance(folded.get('admitted'), dict):
        return folded['admitted']
    return {}


def _persons_for(actor, holon, norm, admitted, now):
    """The persons an agent may answer for on this item: the person who let it into the item's holon,
    else the persons whose live delegations reach that holon (a delegation for another holon never
    counts: record.delegation_for asks that it cover the line's holon and come from its `for`)."""
    if actor_kind(actor) == 'person':
        return [actor]
    m = (admitted or {}).get(holon) if isinstance(admitted, dict) else None
    e = m.get(actor) if isinstance(m, dict) else None
    if isinstance(e, dict) and actor_kind(e.get('person')) == 'person':
        return [e['person']]
    ps = set()
    try:
        for d in live_delegations(norm, actor, now):
            hs = field(d, 'holons') or []
            hs = [hs] if isinstance(hs, str) else hs if isinstance(hs, list) else []
            if '*' in hs or (holon and holon in hs):
                ps.add(_s(field(d, 'for') or field(d, 'by') or field(d, 'actor')))
    except Exception:                     # noqa: BLE001
        ps = set()
    return sorted(p for p in ps if actor_kind(p) == 'person')


def _person_for(actor, holon, norm, admitted, now):
    """The one person the reader answers for here, or None (none, or more than one)."""
    ps = _persons_for(actor, holon, norm, admitted, now)
    return ps[0] if len(ps) == 1 else None


def _stop_items(folded):
    out = []
    if isinstance(folded, dict):
        for k in ('stops', 'stop'):
            v = folded.get(k)
            out += [x for x in (v.values() if isinstance(v, dict) else v if isinstance(v, list) else [])
                    if isinstance(x, dict)]
        if isinstance(folded.get('items'), list):
            out += [x for x in folded['items'] if isinstance(x, dict) and x.get('kind') == 'stop']
    elif isinstance(folded, list):
        out += [x for x in folded if isinstance(x, dict) and x.get('kind') == 'stop']
    seen, keep = set(), []
    for x in sorted(out, key=lambda x: _s(x.get('id'))):
        if _s(x.get('id')) and x['id'] not in seen:
            seen.add(x['id'])
            keep.append(x)
    return keep


def _stopped(actor, item, folded, admitted, now):
    """The live stop that binds this agent on this item, as {stop, by, why}, or None. stops.py decides
    (live, then binds), as the Deal's apply_stops does; without it, any stop not lifted or retracted
    that names this agent, or names none, binds (the widest reading)."""
    if actor_kind(actor) != 'agent':
        return None
    raw = _stop_items(folded)
    if not raw:
        return None
    hit = None
    if stops_mod is not None:
        try:
            rows = stops_mod.live({'stops': raw, 'admitted': admitted or None}, actor, None, now)
            for row in rows:
                got = stops_mod.binds([row], actor, _s(item.get('holon')) or None, item, admitted=admitted or None)
                if isinstance(got, tuple) and got and got[0]:
                    hit = row
                    break
        except Exception:                 # noqa: BLE001 — read at the widest below
            hit, rows = None, None
        else:
            return {'stop': hit['id'], 'by': hit.get('by') or None, 'why': hit.get('why') or None} if hit else None
    for x in raw:
        if _s(x.get('state')) in ('lifted', 'retracted'):
            continue
        ags = x.get('agents')
        if not ags or (isinstance(ags, list) and actor in ags):
            return {'stop': x['id'], 'by': _s(x.get('for') or x.get('actor')) or None, 'why': _s(x.get('why')) or None}
    return None


def _as_set(v):
    if isinstance(v, str) and v:
        return {v}
    if isinstance(v, (list, tuple)):
        return {x for x in v if isinstance(x, str) and x}
    return set()


def _roles(item, who, kind, keepers, admitted):
    if not isinstance(item, dict) or not isinstance(who, str) or not who:
        return []
    holon = _s(item.get('holon'))
    have = set()
    if kind == 'commitment':
        if item.get('for') == who:
            have.add('committor')
        if item.get('committee') == who:
            have.add('committee')
        if item.get('witness') == who:
            have.add('witness')
    if kind == 'card' and item.get('asked') == 'request' and item.get('for') == who:
        have.add('asker')
    if who in _as_set(item.get('to')) or who in _as_set(item.get('body_to')):
        have.add('party')
    if item.get('holder') == who:
        have.add('holder')
    if holon and keepers.get(holon) == who:
        have.add('keeper')
    if kind in ('sighting', 'constraint') and item.get('for') == who:
        have.add('raiser')
    m = admitted.get(holon) if isinstance(admitted.get(holon), dict) else {}
    e = m.get(who)
    if isinstance(e, dict) and not e.get('ended'):
        have.add('member')
    out = [r for r in ROLE_ORDER if r in have]
    return out or ['reader']


def roles(item, actor, folded=None):
    """The reader's roles on the item, in a fixed order (ROLE_ORDER); 'reader' when no other holds. An
    agent's roles are those of the person it answers for."""
    if not isinstance(item, dict) or not item.get('id'):
        return []
    reg = _registry()
    kind = _kind_of(item, reg)
    norm = _norm(folded)
    adm = _admitted(folded, None)
    who = _person_for(actor, _s(item.get('holon')), norm, adm, None) if actor_kind(actor) else None
    return _roles(item, who, kind, _keepers(folded, norm, adm), adm) if who else ['reader']


def _home_of(person, holon, norm):
    h = holon_names(norm).get(holon) or {}
    return bool(holon) and h.get('kind') == 'person' and h.get('keeper') == person


# ---------------------------------------------------------------- what a line would write

def _target(spec, kind, iid):
    body, links = {}, {}
    for p in spec.get('target') or []:
        if not isinstance(p, str):
            continue
        if p.startswith('body.'):
            f = p[5:]
            if f == kind or (f == 'entry' and kind == 'wallet_entry'):
                body[f] = iid
                return body, links
        elif p.startswith('links.'):
            links[p[6:]] = [iid]
            return body, links
    return body, {'anchored_to': [iid]}


def _writes(typ, spec, kind, item, when, extra=None):
    body, links = _target(spec, kind, _s(item.get('id')))
    for f in spec.get('fields') or []:
        if isinstance(f, dict) and f.get('required') and isinstance(f.get('name'), str):
            body.setdefault(f['name'], None)
    for p, v in (when or {}).items():
        if isinstance(p, str) and p.startswith('body.'):
            body[p[5:]] = v
    for t in spec.get('transitions') or []:
        if isinstance(t, dict) and t.get('when') in (None, when) and isinstance(t.get('when_item'), dict):
            for p, f in t['when_item'].items():
                if isinstance(p, str) and p.startswith('body.'):
                    body[p[5:]] = item.get(f)
    body.update(extra or {})
    return {'type': typ, 'body': body, 'links': links}


def _act(typ, spec, kind, item, when, t, primary_keys, extra=None):
    key = _key(typ, when)
    w = words(key, kind)
    return {'type': typ, 'when': dict(when) if when else None, 'sets': _sets(t), 'key': key,
            'label': w['label'] or key, 'meaning': w['meaning'], 'role_word': w['role_word'], 'primary': False,
            'writes': _writes(typ, spec, kind, item, when, extra)}


# ---------------------------------------------------------------- the acts

def _empty(said=SAID_EMPTY):
    return {'acts': [], 'kind': None, 'role': None, 'roles': [], 'for': None, 'stopped': None, 'why_not': [],
            'said': said}


def offered(item, actor, folded=None, now=None, registry=None, admitted=None, card=None):
    """The acts this item offers this reader, computed from the registry. See the module docstring.
    With `card` (the dealt card about this item), the primary act is the one its recommended option
    writes, when this reader is offered it; else none is primary. Without a card, PRIMARY decides."""
    if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
        return _empty()
    if actor_kind(actor) is None:
        return _empty('No reader is named, so nothing is offered.')
    reg = _registry(registry)
    kind = _kind_of(item, reg)
    if kind is None:
        return _empty('This is not a kind of item the record knows, so nothing is offered.')
    tdefs = reg.get('types') or {}
    state = _state_of(item, kind, reg)
    holon = _s(item.get('holon'))
    norm = _norm(folded)
    adm = _admitted(folded, admitted)
    keepers = _keepers(folded, norm, adm)
    is_agent = actor_kind(actor) == 'agent'
    persons = _persons_for(actor, holon, norm, adm, now)
    person = persons[0] if len(persons) == 1 else None
    stopped = _stopped(actor, item, folded, adm, now) if is_agent else None
    blocked = WHY['stopped'] if stopped else (WHY['many'] if len(persons) > 1 else WHY['nobody']) \
        if is_agent and (stopped or person is None) else None
    ckind = card_kind(item) if kind == 'card' else None
    line = {'actor': actor, 'for': person}
    rs = _roles(item, person, kind, keepers, adm) if person else ['reader']
    acts, why_not = [], []

    def refuse(key, why):
        why_not.append({'act': key, 'why': why})

    def agent_may(typ):
        try:
            return may_act(norm, actor, typ, holon, now, ckind)
        except Exception:                 # noqa: BLE001
            return False

    for typ in tdefs:
        spec = tdefs[typ]
        if not isinstance(spec, dict) or typ == SAY or kind not in (spec.get('acts_on') or []):
            continue
        for when, ts in _groups(spec, kind):
            key = _key(typ, when)
            if blocked:
                refuse(key, blocked)
                continue
            if typ in NOT_A_CHOICE:
                refuse(key, WHY['not_a_choice'])
                continue
            if is_agent and (spec.get('human_only') or typ in HUMAN_ONLY_ACTS):
                refuse(key, WHY['human'])
                continue
            if is_agent and not agent_may(typ):
                refuse(key, WHY['delegation'])
                continue
            if spec.get('home_only') and not _home_of(person, holon, norm):
                refuse(key, WHY['home'])
                continue
            if person is None:
                refuse(key, WHY['delegation'])
                continue
            fit, why, refused_move = None, WHY['unknown'], None
            for t in (ts or [{}]):
                frm = t.get('from')
                if frm and state not in frm:
                    why = WHY['state'] % (state or 'new')
                    refused_move = refused_move or (why if _sets(t) else None)
                    continue
                try:
                    ok = record._who_ok(t.get('who'), line, item, keepers)
                except Exception:         # noqa: BLE001
                    ok = False
                if not ok:
                    why = WHY['who'].get(t.get('who'), WHY['unknown'])
                    refused_move = refused_move or (why if _sets(t) else None)
                    continue
                fit = t
                break
            if fit is None:
                refuse(key, why)
                continue
            if NOTE_ONLY and refused_move and not (fit.get('set') or {}):
                refuse(key, refused_move + ' ' + WHY['note'])      # its move is refused; only its note fits
                continue
            if NO_OP and _sets(fit) and _sets(fit) == state:
                refuse(key, WHY['no_op'] % state)
                continue
            acts.append(_act(typ, spec, kind, item, when, fit, None))

    # the say: always to a person (a note is never refused), and its question form
    say_spec = tdefs.get(SAY) if isinstance(tdefs.get(SAY), dict) else {'target': ['links.anchored_to']}
    say_spec = dict(say_spec, target=['links.anchored_to'])
    if blocked:
        refuse('act.say', blocked)
        refuse('act.say.ask', blocked)
    elif not is_agent or agent_may(SAY):
        acts.append(_act(SAY, say_spec, kind, item, None, None, None, {'text': None}))
        ask = _act(SAY, say_spec, kind, item, None, None, None, {'text': None, 'intent': 'ask'})
        ask.update(key='act.say.ask', when={'body.intent': 'ask'})
        w = words('act.say.ask', kind)
        ask.update(label=w['label'] or 'act.say.ask', meaning=w['meaning'], role_word=w['role_word'])
        acts.append(ask)
    else:
        refuse('act.say', WHY['delegation'])
        refuse('act.say.ask', WHY['delegation'])

    have = {a['key']: a for a in acts}
    if isinstance(card, dict):
        rk = _option_key(card, _s(card.get('recommendation')))
        first = rk if rk in have else None
    else:
        prefs = (PRIMARY.get(kind) or {}).get(state) or (PRIMARY.get(kind) or {}).get('*') or []
        first = next((k for k in prefs if k in have), None)
    if first:
        have[first]['primary'] = True
    acts.sort(key=lambda a: (not a['primary'],))     # stable: the primary first, then registry order
    role = rs[0] if rs else 'reader'
    rw = role_words(role).get('label') or role
    if acts:
        n = len(acts)
        said = 'As %s, you have %s here.' % (rw, 'one act' if n == 1 else '%d acts' % n)
        if first:
            said += ' "%s" is the one I would choose.' % have[first]['label']
    else:
        said = 'As %s, nothing here is yours to do.' % rw
    if blocked:
        said = blocked
    elif is_agent:
        said = 'For the person it answers for: ' + said
    return {'acts': acts, 'kind': kind, 'role': role, 'roles': rs, 'for': person, 'stopped': stopped,
            'why_not': why_not, 'said': said}


def _option_key(card, o):
    """The act key one of a dealt card's options writes (OPTION_ACTS), or None."""
    card = card if isinstance(card, dict) else {}
    kind, sec = _s(card.get('kind')), _s(card.get('section'))
    table = OPTION_ACTS.get(kind) or {}
    if sec == 'ready' and kind not in OPTION_ACTS:
        table = READY_OPTIONS
    if not isinstance(o, str) or not o:
        return None
    if o in table:
        return table[o]
    if sec == 'ready' and o.startswith('Hand it to '):
        return 'act.hand'
    if kind in CUSTOM_DECIDE:
        return 'act.decide'
    return None


def options_for(card, offered_result):
    """What each of a dealt card's options writes, as an act of `offered_result` (OPTION_ACTS): aligned
    with the card's options, each {option, key, offered, recommended, type, writes, why}. An option whose
    act this reader is not offered says so (offered false, writes none); one that writes no line has key none."""
    card = card if isinstance(card, dict) else {}
    res = offered_result if isinstance(offered_result, dict) else {}
    opts = [o for o in (card.get('options') if isinstance(card.get('options'), list) else []) if isinstance(o, str)]
    kind = _s(card.get('kind'))
    have = {a.get('key'): a for a in res.get('acts') or [] if isinstance(a, dict)}
    rec = _s(card.get('recommendation'))
    custom = kind in CUSTOM_DECIDE and not any(o in (OPTION_ACTS.get(kind) or {}) for o in opts)
    out = []
    for o in opts:
        key = _option_key(card, o)
        a = have.get(key) if key else None
        row = {'option': o, 'key': key, 'offered': a is not None, 'recommended': o == rec,
               'type': a['type'] if a else None, 'writes': None, 'needs_words': False, 'why': None}
        if a:
            wr = json.loads(json.dumps(a.get('writes') or {}))
            body = wr.get('body') if isinstance(wr.get('body'), dict) else None
            if body is not None and a['type'] == 'decide' and custom:
                body['text'] = o                          # the decision's own option is the decision
            elif body is not None and a['type'] == 'say':
                if o in SAY_OPENS:
                    row['needs_words'] = True             # their reply, question or change goes here
                else:
                    body['text'] = o                      # the option's own words are the line
            row['needs_words'] = row['needs_words'] or (body is not None and 'text' in body and body['text'] is None)
            row['writes'] = wr
        else:
            row['why'] = res.get('said') if res.get('stopped') else (OPTION_NOT_OFFERED if key else OPTION_NO_LINE)
        out.append(row)
    return out


# ---------------------------------------------------------------- render

def render(offered_result):
    """Markdown: the acts, the primary first, then "What these mean" under its own heading."""
    r = offered_result if isinstance(offered_result, dict) else {}
    acts = [a for a in r.get('acts') or [] if isinstance(a, dict)]
    said = _s(r.get('said')) or SAID_EMPTY
    if not acts:
        return said + '\n'
    acts = sorted(acts, key=lambda a: not a.get('primary'))
    out = [said, '']
    for a in acts:
        out.append('- **%s**%s' % (a.get('label') or a.get('key'), ' (the one I would choose)' if a.get('primary') else ''))
    out += ['', '### What these mean', '']
    for a in acts:
        out.append('- **%s** — %s' % (a.get('label') or a.get('key'), a.get('meaning') or 'no words yet'))
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- the table and its check

def producible(registry=None):
    """Every (key, kind) offered() can produce from this registry: [(key, kind)], sorted."""
    reg = _registry(registry)
    out = set()
    kinds = set((reg.get('items') or {}).keys())
    for typ, spec in (reg.get('types') or {}).items():
        if not isinstance(spec, dict) or typ == SAY or typ in NOT_A_CHOICE:
            continue
        for kind in spec.get('acts_on') or []:
            if kind not in kinds:
                continue
            for when, _ts in _groups(spec, kind):
                out.add((_key(typ, when), kind))
    for kind in kinds:
        out.add(('act.say', kind))
        out.add(('act.say.ask', kind))
    return sorted(out)


def check(registry=None):
    """{ok, missing: [key], extra: [key]}: every key the registry can produce has a label and a meaning."""
    keys = sorted({k for k, _ in producible(registry)})
    w = _load_words()['acts']
    missing = [k for k in keys if not (isinstance(w.get(k), dict) and _s(w[k].get('label')) and _s(w[k].get('meaning')))]
    extra = sorted(k for k in w if k not in keys and k[len('act.'):].split('.')[0] not in NOT_A_CHOICE)
    return {'ok': not missing, 'missing': missing, 'extra': extra}


def table():
    w = _load_words()
    return {k: {x: w['acts'][k].get(x) for x in ('label', 'meaning', 'role_word')} for k in sorted(w['acts'])}


# ---------------------------------------------------------------- CLI

def _load(p):
    if os.path.islink(p):
        raise OSError('%s is a link; a file is read only where it stands' % p)
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def _find(folded, iid):
    for xs in _norm(folded).values():
        for x in xs:
            if isinstance(x, dict) and x.get('id') == iid:
                return x
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['table']:
        print(json.dumps(table(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    if argv[:1] == ['check']:
        r = check()
        print(json.dumps(r, indent=2, sort_keys=True))
        return 0 if r['ok'] else 1
    ap = argparse.ArgumentParser(description='The acts a card offers this reader, from the registry.')
    ap.add_argument('items')
    ap.add_argument('item_id')
    ap.add_argument('actor')
    ap.add_argument('--now')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        folded = _load(a.items)
    except (OSError, ValueError) as e:
        print('acts: %s' % e, file=sys.stderr)
        return 2
    item = _find(folded, a.item_id)
    r = offered(item, a.actor, folded=folded, now=a.now)
    print(json.dumps(r, indent=2, sort_keys=True, ensure_ascii=False) if a.json else render(r), end='' if not a.json else '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
