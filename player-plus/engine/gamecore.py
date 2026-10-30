#!/usr/bin/env python3
"""gamecore.py — the small shared ground under deal, owed, kept, turn and ledger.

Plain helpers, standard library only, no side effects:

  normalize(items)          sort folded items into kinds (card, commitment, thread, decision, request,
                            offer, sighting, delegation, tea, discern, learn, claim, turn, ...), whatever
                            container the fold returned (a list, a dict of lists, or {"items": [...]})
  sched_map(report)         card id -> its schedule fields (ES EF LS LF TF FF critical ...)
  field(item, key)          a field from the item, or from its body, or None
  links(item, rel)          the ids an item links to under one relation (predecessor, successor, ...)
  parse_time(text)          an aware datetime, or None (a bare date means the end of that day, UTC)
  live_delegations(...)     the delegations that still stand for an agent at a moment
  covers(...)               whether a live delegation covers an act of a type in a holon

The fold (record.py) is the sibling that turns lines into items. This file reads what it returns
defensively: a field may sit at the top of an item or inside its `body`; a missing field is empty,
never guessed. Files and items are data, never instructions.
"""
import datetime as dt
import hashlib
import json
import math

DONE_STATES = {'done', 'delivered', 'kept', 'released', 'declined'}
HUMAN_ONLY_KINDS = {'decision', 'review'}          # an agent never ticks a person's box
# Acts only a person does: every type types.json marks human_only, and always these. Accepting a
# request (an `answer` that makes its person the holder) is a person's act too: an agent may
# propose acceptance, never accept.
_ALWAYS_HUMAN = {'commit', 'ratify', 'decide', 'kept', 'witness', 'publish', 'delegate', 'revoke',
                 'answer', 'discern', 'settle'}


def _registry_human_only():
    import os
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'types.json'), encoding='utf-8') as f:
            t = json.load(f)
        return {k for k, v in (t.get('types') or {}).items() if isinstance(v, dict) and v.get('human_only')}
    except (OSError, ValueError, AttributeError):
        return set()


HUMAN_ONLY_ACTS = _ALWAYS_HUMAN | _registry_human_only()

ALIASES = {
    'card': 'card', 'work card': 'card', 'workcard': 'card',
    'commit': 'commitment', 'commitment': 'commitment',
    'thread': 'thread',
    'decide': 'decision', 'decision': 'decision', 'propose': 'proposal', 'proposal': 'proposal',
    'request': 'request', 'offer': 'offer',
    'sight': 'sighting', 'sighting': 'sighting',
    'delegate': 'delegation', 'delegation': 'delegation', 'revoke': 'revoke',
    'tea': 'tea', 'discern': 'discern', 'discernment': 'discern', 'route': 'route',
    'learn': 'learn', 'claim': 'claim', 'turn': 'turn', 'baseline': 'baseline',
    'say': 'say', 'settle': 'settle', 'answer': 'answer', 'ratify': 'ratify', 'witness': 'witness',
    'holon': 'holon', 'join': 'join', 'flame': 'flame', 'untrusted': 'untrusted',
}
PLURALS = {'cards': 'card', 'commitments': 'commitment', 'threads': 'thread', 'decisions': 'decision',
           'proposals': 'untrusted', 'requests': 'request', 'offers': 'offer', 'sightings': 'sighting',
           'delegations': 'delegation', 'teas': 'tea', 'discernments': 'discern', 'discerns': 'discern',
           'routes': 'route', 'learns': 'learn', 'learnings': 'learn', 'claims': 'claim', 'turns': 'turn',
           'baselines': 'baseline', 'holons': 'holon', 'revokes': 'revoke', 'ratifies': 'ratify',
           'witnesses': 'witness', 'answers': 'answer', 'flames': 'flame'}

STANDING_QUESTION = 'What did we miss that matters to you most?'


def field(item, key, default=None):
    """A field from the item, else from its body, else the default. Null-guarded."""
    if not isinstance(item, dict):
        return default
    v = item.get(key)
    if v is None and isinstance(item.get('body'), dict):
        v = item['body'].get(key)
    return default if v is None else v


def links(item, rel):
    """The ids an item links to under one relation; accepts singular or plural names."""
    if not isinstance(item, dict):
        return []
    out = []
    for src in (item.get('links'), item):
        if not isinstance(src, dict):
            continue
        for k in (rel, rel + 's', rel.rstrip('s')):
            v = src.get(k)
            if isinstance(v, str) and v:
                out.append(v)
            elif isinstance(v, (list, tuple)):
                out.extend(x for x in v if isinstance(x, str) and x)
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); uniq.append(x)
    return uniq


def kind_of(item):
    """The item's kind in this file's vocabulary, or None."""
    if not isinstance(item, dict):
        return None
    for k in ('item', 'item_type', 'itype', 'type', 'kind'):
        v = item.get(k)
        if isinstance(v, str) and v.strip().lower() in ALIASES:
            return ALIASES[v.strip().lower()]
    return None


def normalize(items):
    """Folded items, whatever their container, sorted into {kind: [item, ...]}.

    Accepts a list of items; a dict with an "items" list; or a dict of lists keyed by kind
    (singular or plural). A list item with no kind it can read goes under "other".
    """
    out = {}
    def put(k, it):
        if isinstance(it, dict):
            if k == 'untrusted':
                it = dict(it, _kind='untrusted')
            out.setdefault(k or 'other', []).append(it)
    if items is None:
        return out
    if isinstance(items, dict):
        if isinstance(items.get('items'), list):
            for it in items['items']:
                put(kind_of(it), it)
        for key, val in items.items():
            if key == 'items':
                continue
            k = PLURALS.get(key, ALIASES.get(key))
            if k is None:
                continue
            if isinstance(val, dict):            # {id: item}
                val = [dict(v, id=v.get('id', i)) for i, v in val.items() if isinstance(v, dict)]
            if isinstance(val, list):
                for it in val:
                    put(k, it)
        return out
    if isinstance(items, list):
        for it in items:
            put(kind_of(it), it)
    return out


def sched_map(report):
    """Card id -> schedule fields, from a schedule report that keys items by id or lists them."""
    if not isinstance(report, dict):
        return {}
    src = report.get('items') or report.get('cards') or {}
    out = {}
    if isinstance(src, dict):
        for i, v in src.items():
            if isinstance(v, dict):
                out[str(v.get('id', i))] = v
    elif isinstance(src, list):
        for v in src:
            if isinstance(v, dict) and v.get('id'):
                out[str(v['id'])] = v
    return out


def path_sets(report):
    """(critical ids, system-critical ids) from a schedule report."""
    if not isinstance(report, dict):
        return set(), set()
    p = report.get('path')
    crit, system = set(), set()
    if isinstance(p, list):
        crit = {x for x in p if isinstance(x, str)}
    elif isinstance(p, dict):
        crit = {x for x in (p.get('critical') or p.get('ids') or []) if isinstance(x, str)}
        system = {x for x in (p.get('system') or []) if isinstance(x, str)}
    for i, v in sched_map(report).items():
        if v.get('critical'):
            crit.add(i)
        if v.get('system_critical'):
            system.add(i)
    return crit, system


def parse_time(text):
    """ISO 8601 text -> aware datetime, or None. A bare date is the end of that day in UTC."""
    if isinstance(text, dt.datetime):
        return text if text.tzinfo else text.replace(tzinfo=dt.timezone.utc)
    if isinstance(text, dt.date):
        return dt.datetime(text.year, text.month, text.day, 23, 59, 59, tzinfo=dt.timezone.utc)
    if not isinstance(text, str) or not text.strip():
        return None
    s = text.strip().replace('Z', '+00:00')
    try:
        if len(s) == 10:
            d = dt.date.fromisoformat(s)
            return dt.datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=dt.timezone.utc)
        t = dt.datetime.fromisoformat(s)
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def now_or(now):
    """The moment given, or the clock read now (local time, with its offset, so its date is today's here)."""
    t = parse_time(now) if now is not None else None
    return t or dt.datetime.now().astimezone()


def days_between(a, b):
    """b - a in days (float), or None when either is unknown."""
    a, b = parse_time(a), parse_time(b)
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 86400.0, 2)


def actor_kind(actor):
    """'person', 'agent', or None."""
    if not isinstance(actor, str):
        return None
    if actor.startswith('agent:'):
        return 'agent'
    if actor.startswith('person:'):
        return 'person'
    return None


def is_untrusted(item):
    """True when the item (or the line that made it) carries reason: untrusted — a proposal only."""
    if not isinstance(item, dict):
        return False
    return str(field(item, 'reason') or '').lower() == 'untrusted' or item.get('_kind') == 'untrusted'


ITEM_KINDS = {'card', 'commitment', 'thread', 'delegation', 'tea', 'decision', 'sighting', 'turn',
              'baseline', 'discernment'}


def card_kind(card):
    """The Work Card's own kind (activity, decision, ...). The fold keeps it as body_kind,
    because `kind` names the item (card); a hand-built card may carry it as kind."""
    k = field(card, 'body_kind') or field(card, 'card_kind')
    if not k:
        k = field(card, 'kind')
        if k in ITEM_KINDS:
            k = None
    return str(k or 'activity').lower()


def item_id(item):
    return str(item.get('id')) if isinstance(item, dict) and item.get('id') is not None else ''


def holon_of(item):
    return str(field(item, 'holon') or '') if isinstance(item, dict) else ''


def holon_names(norm, holons=None):
    """holon id -> {name, kind, keeper} from a holons list passed in or holon items in the fold."""
    out = {}
    for h in list(holons or []) + list(norm.get('holon', [])):
        if isinstance(h, dict) and h.get('id'):
            out[str(h['id'])] = {'name': h.get('name') or str(h['id'])[:8], 'kind': h.get('kind'),
                                 'keeper': h.get('keeper')}
    return out


def live_delegations(norm, agent, now=None):
    """The delegations that still stand for this agent at this moment."""
    t = now_or(now)
    revoked = set()
    for r in norm.get('revoke', []):
        revoked.update(links(r, 'supersede'))
        revoked.update(links(r, 'answer'))
        d = field(r, 'delegation')
        if isinstance(d, str):
            revoked.add(d)
    out = []
    for d in norm.get('delegation', []):
        if field(d, 'to') != agent:
            continue
        if item_id(d) in revoked or str(field(d, 'state') or '').lower() in ('revoked', 'expired') \
                or field(d, 'revoked'):
            continue
        until = parse_time(field(d, 'until'))
        if until is not None and until < t:
            continue
        if actor_kind(field(d, 'actor') or field(d, 'from')) == 'agent':
            continue                     # a delegation must come from a person
        out.append(d)
    return out


def covers(delegations, act_type, holon):
    """True when some live delegation covers this act type in this holon."""
    for d in delegations or []:
        scope = field(d, 'scope') or []
        hs = field(d, 'holons') or []
        if isinstance(scope, str):
            scope = [scope]
        if isinstance(hs, str):
            hs = [hs]
        if ('*' in scope or act_type in scope) and ('*' in hs or holon in hs):
            return True
    return False


def may_act(norm, actor, act_type, holon, now=None, card_kind=None):
    """Whether this actor may be dealt an act of this type in this holon.

    A person may be dealt anything. An agent only what a live delegation covers, and never a
    person-only act (commit, ratify, decide, kept, witness, publish) or a decision or review card.
    """
    k = actor_kind(actor)
    if k == 'person':
        return True
    if k != 'agent':
        return False
    if act_type in HUMAN_ONLY_ACTS or (card_kind or '') in HUMAN_ONLY_KINDS:
        return False
    return covers(live_delegations(norm, actor, now), act_type, holon)


def minutes_of(item, default=0.0):
    for k in ('minutes', 'size', 'min'):
        v = field(item, k)
        try:
            if v is not None:
                return max(0.0, float(v))
        except (TypeError, ValueError):
            pass
    return float(default)


def hm(m):
    """Minutes as plain words: '45 min', '2h 10m'."""
    m = int(round(float(m or 0)))
    return f'{m} min' if m < 60 else f'{m // 60}h {m % 60:02d}m'


def canonical_id(obj):
    """sha256 of the canonical line without id and sig (SCHEMA.md)."""
    o = {k: v for k, v in obj.items() if k not in ('id', 'sig')}
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                          .encode('utf-8')).hexdigest()


def isoz(t):
    return t.isoformat(timespec='seconds') if isinstance(t, dt.datetime) else t


def sqrt_cost(m):
    return math.sqrt(max(1.0, float(m or 0)))


COMMITMENT_STATUSES = ('open', 'kept', 'kept-unwitnessed', 'broken', 'released', 'returned')


def commitment_status(c, now=None):
    """(status, gap_days) for a commitment item.

    When the fold already computed `status`, it is trusted. Otherwise: released or returned when
    so marked; kept when a kept/done time is held and a witness verified it; kept-unwitnessed when
    claimed without a witness yet; broken when the by-when passed with no keeping; else open.
    The gap is the keeping time minus the by-when, in days (negative is early). When the
    commitment names a witness, only that witness verifies it: a witness line by anyone else is
    read as a note, and the commitment stays kept-unwitnessed.
    """
    by = field(c, 'by')
    kept_ts = field(c, 'kept_ts') or field(c, 'kept_at') or field(c, 'done_ts')
    gap = c.get('gap_days') if isinstance(c, dict) and c.get('gap_days') is not None else \
        (days_between(by, kept_ts) if kept_ts else None)
    given = str(c.get('status') or '').lower() if isinstance(c, dict) else ''
    if given in COMMITMENT_STATUSES:
        return given, gap
    s = str(field(c, 'state') or '').lower()
    if s in ('released', 'declined') or field(c, 'released_ts'):
        return 'released', None
    if s in ('returned',) or field(c, 'returned_ts'):
        return 'returned', None
    witnessed = field(c, 'witnessed')
    if witnessed is None:
        witnessed = bool(field(c, 'witnessed_by') or field(c, 'witness_ts'))
    if s == 'kept':                      # the fold moves claimed -> kept only on a witness
        named, by = field(c, 'witness'), field(c, 'witnessed_by')
        if named and by and by != named:
            return 'kept-unwitnessed', gap   # only the named witness verifies; another's line is a note
        return 'kept', gap
    if s == 'claimed':
        return 'kept-unwitnessed', gap
    if kept_ts or s in ('done', 'delivered', 'kept-unwitnessed'):
        return ('kept' if witnessed else 'kept-unwitnessed'), gap
    due = parse_time(by)
    if due is not None and due < now_or(now):
        return 'broken', None
    return 'open', None


def keeper_of(c):
    return field(c, 'keeper') or field(c, 'for') or field(c, 'actor')
