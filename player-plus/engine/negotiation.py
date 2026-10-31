#!/usr/bin/env python3
"""negotiation.py — the conversation for action: the moves between an ask and its resolution.

    report(items, lines, now=None, holon=None, trust=None) -> {asks, pending, not_counted, as_of, basis}
    asks(items, lines, now=None, holon=None, trust=None) -> [ask, ...]   (report(...)['asks'])
    move_line(ask, move, actor, for_, terms=None, text=None, answers=None, now=None) -> an unsigned `move` line
    mandate_covers(delegations, actor, move, terms, for_=None, holon=None, now=None) -> (bool, why)
    render(asks, actor=None) -> Markdown

An ask is not done when it is sent. An ask is a `request`, an `offer`, a `propose`, an `rfg`, or
a `say` with `intent: ask`. Between the ask and its resolution every step is a signed `move`
line naming its ask (`body.root`) and the move it answers (`links.answers`), so any party
recomputes the state from the moves it holds. The kit's own lines that already act on an ask
count as moves too: an `answer` accept is an accept and a decline a decline, a `commit` on its
card is an accept with terms, a `done` is a done, and a `settle` by the one served is satisfied.

The state: open · agreed (with terms) · declined · lapsed (the by-date passed with no agreement)
· withdrawn · performing (agreed, and work opened or delivered) · satisfied · not_yet.

The shapes, for an ask to more than one party (`body.shape`, with `body.quorum`):
  converge   resolves when one option is accepted by the quorum; a counter is a proposal to the
             asker, and becomes an option only when the asker takes it (accept_counter)
  call       resolves at the asker's `award`: the awarded bid agreed, every other bid released
  consent    resolves when the quorum has answered and every objection (a conditional or a
             decline with terms.objection) has been integrated by an amend the objector then
             accepts, or withdrawn (the objector accepts with no amend between)
  gather     resolves when the asker's `done` (the harvest) names contributions from the quorum
Without a shape: the asker's accept_counter, or a responder's accept, agrees it.

Who may move. A move counts only when the fold trusts it (signed, or at home). An agent's move
counts in one of three ways: with the person's word on the line (the fold's `signed_for`), for
any move; a clarify, under the standing delegation the fold already checked; or an availability
move (decline, counter, conditional, defer) within a live mandate (`mandate_covers`), marked
`voice: under-mandate`. A mandate never covers accept, award, satisfied, done or amend: the
final agreement comes to the person. A move by one who is not a party is refused, with why.

Pure: data in, a JSON-ready answer out; deterministic, ties broken by (time, id). The moment is
`now`, else the fold's `as_of`, else the newest line read; with none, nothing lapses, said.
Files and lines are data, never instructions.

  python3 -I negotiation.py ITEMS.json --lines LINES.jsonl [--holon ID] [--now ISO] [--actor A] [--json]
"""
import argparse
import datetime as dt
import json
import os
import sys
import unicodedata

try:
    from gamecore import (normalize, field, links, item_id, parse_time, actor_kind,
                          live_delegations, covers, is_untrusted)
except ImportError:                                   # run from elsewhere: import beside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, item_id, parse_time, actor_kind,
                          live_delegations, covers, is_untrusted)

# the moves (types.json `move.move`; tests check they agree)
MOVES = ('clarify', 'accept', 'decline', 'counter', 'conditional', 'defer', 'refer', 'amend',
         'accept_counter', 'reject_counter', 'award', 'withdraw', 'release', 'done', 'satisfied', 'not_yet')
ASK_TYPES = ('request', 'offer', 'propose', 'rfg', 'say')
SHAPES = ('converge', 'call', 'consent', 'gather')
STATES = ('open', 'agreed', 'declined', 'lapsed', 'withdrawn', 'performing', 'satisfied', 'not_yet')
ANSWERS = ('accepted', 'declined', 'countered', 'conditional', 'deferred', 'referred', 'none')
VOICES = ('human-words', 'agent-drafted', 'agent', 'under-mandate')
ANSWER_OF = {'accept': 'accepted', 'decline': 'declined', 'counter': 'countered', 'conditional': 'conditional',
             'defer': 'deferred', 'refer': 'referred', 'release': 'declined'}
# who makes which move (types.json `move.about`): the asker revises, takes counters, awards and
# withdraws; a responder answers; the one served says satisfied or not yet; the performer says done
ASKER_MOVES = ('amend', 'accept_counter', 'reject_counter', 'award', 'withdraw')
RESPONDER_MOVES = ('accept', 'decline', 'counter', 'conditional', 'defer', 'refer', 'release')
CUSTOMER_MOVES = ('satisfied', 'not_yet')
PERFORMER_MOVES = ('done',)
# an agent's availability moves within a mandate (types.json `delegate.about`: decline, counter,
# conditional, defer; never accept, so every yes comes to the person)
MANDATE_MOVES = ('decline', 'counter', 'conditional', 'defer')
NEVER_MANDATE = ('accept', 'award', 'satisfied', 'done', 'amend')
MANDATE_LIMITS = ('days', 'after', 'before', 'max_minutes', 'not')
MANDATE_WORDS = ('text', 'words', 'note', 'consent')      # the person's words beside the limits; never a limit
TERM_TIMES = ('time', 'times', 'start', 'at', 'date', 'when', 'by')
DAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
COUNTED_TRUST = ('signed', 'home')                        # a vouched copy informs and never acts (SCHEMA, Keys)
NOT_COUNTED = ('invalid', 'unverified', 'refused', 'forked', 'proposals')
ENDED_DELEGATION = ('revoked', 'expired')
QUORUM_DEFAULT = 'everyone'                               # the kit's default for a shape with no quorum said
EVERYONE = ('everyone', 'all', 'every one')
ANY_ONE = ('any one', 'anyone', 'any', 'one')
TITLE_CUT = 200


# ---------------------------------------------------------------- small helpers

def _s(v):
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _dict(v):
    return v if isinstance(v, dict) else {}


def _strs(v):
    if isinstance(v, str):
        v = [v]
    return [_s(x) for x in v if _s(x)] if isinstance(v, (list, tuple)) else []


def _body(l):
    return _dict(l.get('body')) if isinstance(l, dict) else {}


def _instant(ts):
    t = parse_time(ts)
    return t.astimezone(dt.timezone.utc).isoformat() if t else ''


def _key(x):
    return (_instant(x.get('ts')), _s(x.get('id')))


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _clean(v):
    """A JSON-ready copy of a body value: NFC text, no floats, no salts."""
    if isinstance(v, dict):
        return {_s(k): _clean(x) for k, x in v.items() if isinstance(k, str) and not k.startswith('body_salt')}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, str):
        return unicodedata.normalize('NFC', v)
    if isinstance(v, float):
        return int(v) if v == v and v not in (float('inf'), float('-inf')) and v == int(v) else None
    return v


# ---------------------------------------------------------------- what one call reads

def _standing(norm, agent, at):
    """The delegations that stood for this agent at a moment; a revoked one stands for what came before it."""
    out = list(live_delegations(norm, agent, at))
    for d in norm.get('delegation', []):
        ended = parse_time(field(d, 'revoked_ts'))
        until = parse_time(field(d, 'until'))
        if _s(field(d, 'to')) == agent and _s(field(d, 'state')).lower() == 'revoked' and ended and at \
                and at < ended and (until is None or until >= at) and d not in out:
            out.append(d)
    return out


def _id_holds(l):
    """True when the line's id is the hash of its canonical form (record.check_id)."""
    try:
        import record
        return bool(record.check_id(l))
    except ImportError:                                  # without the record module, the canonical hash alone
        try:
            from gamecore import canonical_id
            return canonical_id({k: v for k, v in l.items() if not str(k).startswith('_')}) == l.get('id')
        except (TypeError, ValueError):
            return False
    except Exception:                                    # any line the canonical rules cannot read has no id
        return False


class _Ground:
    def __init__(self, items, lines, trust, now):
        self.items = items if isinstance(items, dict) else {}
        self.norm = normalize(items)
        raw, seen, self.bad = [], set(), []
        for l in (lines if isinstance(lines, (list, tuple)) else []):
            if not isinstance(l, dict) or not _s(l.get('id')):
                continue
            if not _id_holds(l):                            # a tampered copy never stands for the real line
                self.bad.append({'id': _s(l.get('id')), 'type': _s(l.get('type')) or None,
                                 'why': 'its id does not match its content: left out'})
                continue
            if _s(l.get('id')) not in seen:
                seen.add(_s(l.get('id')))
                raw.append(l)
        self.raw = sorted(raw, key=_key)
        t = trust if isinstance(trust, dict) else self.items.get('trust')
        self.trust = t if isinstance(t, dict) else None
        self.excluded = {}
        for k in NOT_COUNTED:
            for e in (self.items.get(k) if isinstance(self.items.get(k), list) else []):
                i = e if isinstance(e, str) else (e.get('id') if isinstance(e, dict) else None)
                if isinstance(i, str):
                    why = e.get('invalid_reason') or e.get('said') if isinstance(e, dict) else None
                    self.excluded.setdefault(i, '%s%s' % (k, (': ' + str(why)[:160]) if why else ''))
        self.signed_for = {}
        for e in (self.items.get('signed_for') if isinstance(self.items.get('signed_for'), list) else []):
            if isinstance(e, dict) and isinstance(e.get('id'), str):
                self.signed_for[e['id']] = e.get('source')
        adm = self.items.get('admitted')
        self.admitted = adm if isinstance(adm, dict) else None
        self.agent_for = {}
        for h, m in sorted((self.admitted or {}).items()):
            for a, e in sorted(_dict(m).items()):
                if actor_kind(a) == 'agent' and isinstance(e, dict) and actor_kind(e.get('person')) == 'person':
                    self.agent_for.setdefault(_s(a), _s(e['person']))
        for d in sorted(self.norm.get('delegation', []), key=_key):
            a, p = _s(field(d, 'to')), _s(field(d, 'actor') or field(d, 'for'))
            if actor_kind(a) == 'agent' and actor_kind(p) == 'person':
                self.agent_for.setdefault(a, p)
        self.event_item = {}
        for kind in sorted(self.norm):
            for it in self.norm[kind]:
                if not isinstance(it, dict) or not item_id(it):
                    continue
                for ev in [item_id(it)] + [e for e in (it.get('events') or []) if isinstance(e, str)]:
                    self.event_item.setdefault(ev, it)
        self.moment, self.moment_basis = self._moment(now)

    def _moment(self, now):
        t = parse_time(now) if now is not None else None
        if t:
            return t, 'now, as given'
        a = self.items.get('as_of')
        if isinstance(a, dict):
            a = a.get('ts')
        if parse_time(a):
            return parse_time(a), "the fold's as_of"
        ts = [parse_time(l.get('ts')) for l in self.raw if parse_time(l.get('ts'))]
        if ts:
            return max(ts), 'the newest line read'
        return None, 'no moment known: nothing lapses'

    def who(self, line_or_actor):
        """The Living Intelligence a line or an actor answers for."""
        if isinstance(line_or_actor, dict):
            f = _s(line_or_actor.get('for'))
            if actor_kind(f) == 'person':
                return f
            return self.who(_s(line_or_actor.get('actor')))
        a = _s(line_or_actor)
        return self.agent_for.get(a, a) if actor_kind(a) == 'agent' else a

    def why_not(self, l):
        """'' when the line counts here, else why it does not."""
        lid, typ = _s(l.get('id')), _s(l.get('type'))
        if not lid or not typ:
            return 'a line with no id or type'
        if lid in self.excluded:
            return 'the fold lists it as %s' % self.excluded[lid]
        if self.trust is not None:
            t = self.trust.get(lid)
            if t is None:
                return 'not in the fold: no trust is known for it'
            if t == 'vouched':
                return 'a vouched copy informs and never acts'
            if t not in COUNTED_TRUST:
                return 'the fold does not trust it (%s)' % t
        if '_trust' in l and l['_trust'] not in COUNTED_TRUST:
            return 'the fold does not trust it (%s)' % l['_trust']
        if _s(l.get('reason')).lower() == 'untrusted':
            return 'its reason came from text an agent read: a proposal only'
        a, f = _s(l.get('actor')), _s(l.get('for'))
        k = actor_kind(a)
        if k == 'person':
            return '' if f in ('', a) else 'a person answers for themselves'
        if k != 'agent':
            return 'the actor is neither a person nor an agent'
        if actor_kind(f) != 'person':
            return 'the line answers for no Living Intelligence'
        if self.trust is None and lid not in self.signed_for:
            at = parse_time(l.get('ts')) or self.moment
            dl = [d for d in _standing(self.norm, a, at) if _s(field(d, 'actor') or field(d, 'for')) == f]
            if not covers(dl, typ, _s(l.get('holon'))):
                return 'no live delegation from %s covers %r in this holon' % (f, typ)
        return ''

    def members(self, holon):
        """The persons admitted in a holon, or None when the fold's admitted map is not held."""
        if self.admitted is None:
            return None
        m = self.admitted.get(holon)
        if not isinstance(m, dict):
            return None
        return sorted(_s(a) for a, e in m.items()
                      if actor_kind(_s(a)) == 'person' and not (isinstance(e, dict) and e.get('ended')))

    def keepers(self, holon):
        m = _dict((self.admitted or {}).get(holon))
        return sorted(_s(a) for a, e in m.items() if isinstance(e, dict) and e.get('via') == 'inception')


# ---------------------------------------------------------------- the asks

def _voice(given, actor, reason):
    v = _s(given)
    if v in VOICES:
        return v, None
    if actor_kind(actor) == 'person':
        return 'human-words', 'no voice on the line: a person\'s line is read as their own words'
    return 'agent', 'no voice on the line: an agent\'s line is read as the agent\'s'


def _ask_from_line(l, g):
    b = _body(l)
    item = g.event_item.get(_s(l.get('id')))
    v, vsaid = _voice(b.get('voice'), _s(l.get('actor')), l.get('reason'))
    title = _s(b.get('title')) or _s(b.get('text')) or _s(b.get('question'))
    a = {'id': _s(l.get('id')), 'type': _s(l.get('type')), 'holon': _s(l.get('holon')),
         'actor': _s(l.get('actor')), 'asker': g.who(l), 'ts': _s(l.get('ts')), 'title': title[:TITLE_CUT],
         'why': _s(b.get('why')) or None, 'effort': _int(b.get('effort')), 'minutes': _int(b.get('minutes')),
         'by': _s(b.get('by')) or None, 'shape': _s(b.get('shape')) or None, 'quorum': b.get('quorum'),
         'voice': v, 'to': _strs(b.get('to')), 'options': _clean(b.get('options')) if isinstance(b.get('options'), list) else None,
         'card': item_id(item) if isinstance(item, dict) and item.get('kind') == 'card' else (_s(b.get('card')) or None),
         'receipts': [r for r in (item.get('receipts') or []) if isinstance(r, dict)] if isinstance(item, dict) else []}
    if vsaid:
        a['voice_said'] = vsaid
    return a


def _ask_from_item(c, g):
    v, vsaid = _voice(field(c, 'voice'), _s(field(c, 'actor')), field(c, 'reason'))
    a = {'id': item_id(c), 'type': _s(field(c, 'asked')), 'holon': _s(field(c, 'holon')),
         'actor': _s(field(c, 'actor')), 'asker': g.who(c), 'ts': _s(field(c, 'ts')),
         'title': _s(field(c, 'title'))[:TITLE_CUT], 'why': _s(field(c, 'why')) or None,
         'effort': _int(field(c, 'effort')), 'minutes': _int(field(c, 'minutes')), 'by': _s(field(c, 'by')) or None,
         'shape': _s(field(c, 'shape')) or None, 'quorum': field(c, 'quorum'), 'voice': v,
         'to': _strs(field(c, 'to')) if field(c, 'asked') == 'request' else [], 'options': None, 'card': item_id(c),
         'receipts': [r for r in (c.get('receipts') or []) if isinstance(r, dict)], '_from_item': True}
    if vsaid:
        a['voice_said'] = vsaid
    return a


def _base_terms(a):
    return {k: a[k] for k in ('title', 'by', 'minutes', 'options') if a.get(k)}


def _quorum(a, parties, g):
    """{need, stewards, basis}: how many responders resolve a shape, or which stewards must."""
    q = a.get('quorum')
    said = ''
    if q is None or (isinstance(q, str) and not q.strip()):
        q, said = QUORUM_DEFAULT, ' (the kit\'s default: the ask says no quorum)'
    if isinstance(q, list):
        st = sorted(set(_strs(q)))
        return {'need': None, 'stewards': st, 'basis': 'the stewards named: %s' % ', '.join(st)}
    n = _int(q)
    if n is None and isinstance(q, str) and q.strip().isdigit():
        n = int(q.strip())
    if n is not None:
        if n < 1:
            return {'need': None, 'stewards': None, 'basis': 'a quorum of %d is not one the kit reads' % n}
        return {'need': n, 'stewards': None, 'basis': 'a number: %d' % n}
    s = _s(q).lower() if isinstance(q, str) else ''
    if s in EVERYONE:
        if parties is None:
            return {'need': None, 'stewards': None,
                    'basis': 'everyone, but the parties are not known (no `to` and no members held)' + said}
        return {'need': len(parties), 'stewards': None, 'everyone': True, 'basis': 'everyone: %d' % len(parties) + said}
    if s in ANY_ONE:
        return {'need': 1, 'stewards': None, 'basis': 'any one'}
    if s.startswith('stewards'):
        rest = _s(q)[len('stewards'):].replace(',', ' ').replace(':', ' ', 1).split()
        st = sorted({x for x in rest if actor_kind(x)})
        if st:
            return {'need': None, 'stewards': st, 'basis': 'the stewards named: %s' % ', '.join(st)}
        kp = [k for k in g.keepers(a['holon']) if k != a['asker']]
        if kp:
            return {'need': None, 'stewards': kp,
                    'basis': 'the stewards, read as the holon\'s keeper less the asker (none named)'}
        return {'need': None, 'stewards': None,
                'basis': 'no stewards are named, and the holon holds no keeper but the asker: '
                         'this ask cannot resolve until its quorum names the stewards'}
    return {'need': None, 'stewards': None, 'basis': 'the quorum %r is not one the kit reads' % (str(q)[:60],)}


def _parties(a, g):
    """(responders or None, basis): the parties other than the asker."""
    to = a.get('to') or []
    if a['type'] == 'rfg' and len(to) == 1 and not actor_kind(to[0]):
        m = g.members(to[0])
        if m is None:
            return None, 'the rfg is to holon %s, whose members are not held' % to[0][:12]
        return sorted(set(m) - {a['asker']}), 'the members of holon %s' % to[0][:12]
    actors = [g.who(x) for x in to if actor_kind(x)]
    holons = [x for x in to if not actor_kind(x)]
    out = set(actors)
    for h in holons:
        m = g.members(h)
        if m is None:
            return None, 'the ask is to holon %s, whose members are not held' % h[:12]
        out.update(m)
    if out:
        return sorted(out - {a['asker']}), 'the ask\'s `to`'
    m = g.members(a['holon'])
    if m is None:
        return None, 'no `to` and no members held: every trusted move is counted'
    return sorted(set(m) - {a['asker']}), 'the members of the holon it was asked in'


# ---------------------------------------------------------------- mandates

def _clock(v):
    if not isinstance(v, str) or len(v.strip()) != 5 or v.strip()[2] != ':':
        return None
    h, m = v.strip()[:2], v.strip()[3:]
    if not (h.isdigit() and m.isdigit()) or int(h) > 23 or int(m) > 59:
        return None
    return int(h) * 60 + int(m)


def _day(v):
    if _int(v) is not None and 1 <= v <= 7:
        return v - 1
    s = _s(v).lower()[:3] if isinstance(v, str) else ''
    return DAYS.index(s) if s in DAYS and len(_s(v)) >= 3 else None


def _when(v):
    """(datetime read as written, has a clock time) or None."""
    s = _s(v).replace('Z', '+00:00')
    if not s:
        return None
    try:
        if len(s) == 10:
            d = dt.date.fromisoformat(s)
            return dt.datetime(d.year, d.month, d.day), False
        return dt.datetime.fromisoformat(s), True
    except ValueError:
        return None


def _within(m, terms):
    """(bool, why): whether every term lies within the mandate's limits."""
    notes = []
    unknown = sorted(k for k in m if isinstance(k, str) and k not in MANDATE_LIMITS + MANDATE_WORDS)
    if unknown:
        notes.append('ignored, not a limit the kit reads: %s' % ', '.join(unknown))
    days = None
    if 'days' in m:
        raw = m['days'] if isinstance(m['days'], list) else None
        days = {_day(x) for x in raw} if raw is not None else {None}
        if None in days or not days:
            return False, 'the mandate\'s days are not read (%s), so nothing is covered' % str(m['days'])[:60]
    after = before = None
    for k in ('after', 'before'):
        if k in m:
            c = _clock(m[k])
            if c is None:
                return False, 'the mandate\'s %s is not a time of day (HH:MM), so nothing is covered' % k
            after, before = (c, before) if k == 'after' else (after, c)
    cap = None
    if 'max_minutes' in m:
        cap = _int(m['max_minutes'])
        if cap is None or cap < 0:
            return False, 'the mandate\'s max_minutes is not a whole number of minutes, so nothing is covered'
    nots = []
    if 'not' in m:
        if not isinstance(m['not'], list) or not all(isinstance(x, str) for x in m['not']):
            return False, 'the mandate\'s not is not a list of dates or days, so nothing is covered'
        nots = [_s(x) for x in m['not']]
    t = _dict(terms)
    beyond = sorted(k for k in t if k not in TERM_TIMES + ('minutes',))
    if beyond:
        return False, ('the terms name %s, beyond the times, days and lengths a mandate reads: that word goes '
                       'to the person' % ', '.join(str(k)[:40] for k in beyond))
    mins = _int(t.get('minutes'))
    if 'minutes' in t and mins is None:
        return False, 'the term minutes is not a whole number, so it cannot be checked'
    if cap is not None and mins is not None and mins > cap:
        return False, 'the term of %d minutes is longer than the mandate\'s %d' % (mins, cap)
    for k in TERM_TIMES:
        if k not in t:
            continue
        vals = t[k] if isinstance(t[k], list) else [t[k]]
        for v in vals:
            w = _when(v)
            if w is None:
                return False, 'the term %s %r is not a time the mandate can be checked against' % (k, str(v)[:40])
            when, has_clock = w
            wd = when.weekday()
            if days is not None and wd not in days:
                return False, '%s falls on %s, outside the mandate\'s days' % (_s(v), DAYS[wd])
            for n in nots:
                if n.lower()[:3] in DAYS and len(n) >= 3 and DAYS.index(n.lower()[:3]) == wd \
                        or n == when.date().isoformat() or (len(n) > 10 and _s(v).startswith(n)):
                    return False, '%s is one the mandate rules out (%s)' % (_s(v), n)
            if has_clock:
                start = when.hour * 60 + when.minute
                end = start + (mins or 0)
                if after is not None and start < after:
                    return False, '%s starts before the mandate\'s %s' % (_s(v), m['after'])
                if before is not None and (end > before if mins else start >= before):
                    return False, '%s ends after the mandate\'s %s' % (_s(v), m['before'])
    return True, '; '.join(['within the mandate'] + notes)


def mandate_covers(delegations, actor, move, terms, for_=None, holon=None, now=None):
    """(bool, why): whether a live mandate covers this availability move by this agent.

    `delegations` is a list of delegation items, or a fold. The mandate is read as data
    (days, after, before, max_minutes, not); a term outside it is not covered; unknown keys are
    ignored and said. A mandate never covers accept, award, satisfied, done or amend."""
    mv = _s(move)
    if mv in NEVER_MANDATE:
        return False, 'a mandate never covers %s: that word comes to the person' % mv
    if mv not in MANDATE_MOVES:
        return False, 'a mandate covers only the availability moves (%s), not %s' % (', '.join(MANDATE_MOVES), mv or '?')
    if actor_kind(_s(actor)) != 'agent':
        return False, 'a mandate is given to an agent; %s is not one' % (_s(actor) or '?')
    if isinstance(delegations, dict):
        ds = normalize(delegations).get('delegation', [])
    elif isinstance(delegations, (list, tuple)):
        ds = [d for d in delegations if isinstance(d, dict)]
    else:
        ds = []
    t = parse_time(now) if now is not None else None
    best = 'no live delegation from the person covers move with a mandate'
    for d in sorted(ds, key=_key):
        if _s(field(d, 'to')) != _s(actor):
            continue
        by = _s(field(d, 'actor') or field(d, 'for'))
        if actor_kind(by) != 'person' or (for_ and by != _s(for_)) or is_untrusted(d):
            continue
        if _s(field(d, 'state')).lower() in ENDED_DELEGATION or field(d, 'revoked'):
            # the fold keeps a revoked delegation's earlier lines: a move dated before the revoke still counts
            ended = parse_time(field(d, 'revoked_ts'))
            if _s(field(d, 'state')).lower() == 'expired' or ended is None or t is None or not t < ended:
                best = 'the delegation %s had ended by then' % item_id(d)[:12]
                continue
        until = parse_time(field(d, 'until'))
        if t is not None and until is not None and until < t:
            best = 'the delegation %s had ended by then' % item_id(d)[:12]
            continue
        if not covers([d] if holon is not None else [dict(d, holons=['*'])], 'move', _s(holon) or '*'):
            continue
        m = field(d, 'mandate')
        if not isinstance(m, dict):
            best = ('the delegation %s covers move but gives no mandate as data' % item_id(d)[:12])
            continue
        ok, why = _within(m, terms)
        if ok:
            return True, '%s (delegation %s)' % (why, item_id(d)[:12])
        best = why
    return False, best


# ---------------------------------------------------------------- the moves

def _move(l, g, move, via, terms=None):
    b = _body(l)
    t = _clean(terms if terms is not None else b.get('terms'))
    return {'id': _s(l.get('id')), 'move': move, 'actor': _s(l.get('actor')), 'for': g.who(l),
            'ts': _s(l.get('ts')), 'terms': t if isinstance(t, dict) and t else None,
            'text': _s(b.get('text') or b.get('note'))[:TITLE_CUT] or None,
            'answers': sorted(links(l, 'answers')), 'given_voice': _s(b.get('voice')) or None,
            'to': _strs(b.get('to')) or _strs(_dict(t).get('to')), 'by': _s(b.get('by')) or _s(_dict(t).get('by')) or None,
            'via': via, '_line': l}


def _refs(a):
    return {x for x in (a['id'], a.get('card')) if x}


def _kit_moves(l, a, g, shape):
    """The moves a kit line makes on this ask (an answer, a commit, a done, a settle, an offer as a bid)."""
    typ, b, refs = _s(l.get('type')), _body(l), _refs(a)
    named = set(links(l, 'answers')) | set(links(l, 'anchored_to')) | set(links(l, 'fulfils'))
    for k in ('card', 'commitment', 'of'):
        if _s(b.get(k)):
            named.add(_s(b.get(k)))
    if not named & refs:
        return None
    if typ == 'answer' and b.get('answer') in ('accept', 'decline'):
        return _move(l, g, b['answer'], 'answer', terms={'text': b['text']} if _s(b.get('text')) else {})
    if typ == 'commit':
        return _move(l, g, 'accept', 'commit',
                     terms={k: b[k] for k in ('by', 'conditions', 'size') if b.get(k) is not None})
    if typ == 'done':
        return _move(l, g, 'done', 'done', terms={})
    if typ == 'settle':
        return _move(l, g, 'satisfied', 'settle', terms={})
    if typ == 'offer' and shape == 'call':
        return _move(l, g, 'counter', 'offer',
                     terms={k: b[k] for k in ('title', 'minutes', 'by') if b.get(k) is not None})
    return None


def _touches(l, a, g, threads):
    named = set(links(l, 'answers')) | set(links(l, 'anchored_to'))
    b = _body(l)
    for k in ('card', 'of'):
        if _s(b.get(k)):
            named.add(_s(b.get(k)))
    return bool(named & (_refs(a) | threads))


# ---------------------------------------------------------------- one conversation

class _Run:
    def __init__(self, a, g):
        self.a, self.g = a, g
        self.parties, self.parties_basis = _parties(a, g)
        self.shape = a['shape'] if a.get('shape') in SHAPES else None
        self.q = _quorum(a, self.parties, g) if self.shape else None
        if self.q and self.q['stewards'] and self.parties is not None:
            extra = sorted(set(self.q['stewards']) - set(self.parties) - {a['asker']})
            if extra:
                self.parties = sorted(set(self.parties) | set(extra))
                self.parties_basis += '; and the stewards the quorum names'
        self.customers = set(self.parties or []) if a['type'] == 'offer' else {a['asker']}
        self.version, self.round, self.by = 0, 0, a.get('by')
        self.terms = None
        self.answers, self.acc = {}, {}            # party -> answer; party -> (version, terms, move id, order)
        self.counters, self.bids, self.contrib = {}, {}, {}
        self.objections = {}                      # party -> {move, open, how}
        self.amends = []
        self.withdrawn = self.satisfied = self.done = self.not_yet = self.harvest = self.awarded = None
        self.agreed = None                        # {terms, basis, at}
        self.history, self.rows, self.refused, self.ignored, self.released = [], [], [], [], []

    # -- the checks
    def side(self, m):
        who, mv, a = m['for'], m['move'], self.a
        if mv == 'clarify':
            return ''
        asker = who == a['asker']
        if self.shape == 'gather' and mv == 'done':
            return '' if asker else 'in a gather, the done that harvests is the asker\'s'
        if mv in ASKER_MOVES and not asker:
            return 'a %s is the asker\'s move' % mv
        if mv in RESPONDER_MOVES and asker:
            return 'a %s is a responder\'s move; the asker does not answer their own ask' % mv
        if mv in CUSTOMER_MOVES and who not in self.customers:
            return 'a %s is the move of the one the work serves' % mv
        if mv in PERFORMER_MOVES and who in self.customers:
            return 'a done is the performer\'s move'
        return ''

    def agent_ok(self, m):
        """(why not or '', voice, voice_said)."""
        given = m['given_voice']
        if actor_kind(m['actor']) != 'agent':
            v = given if given in VOICES else 'human-words'
            return '', v, None if given in VOICES else 'no voice on the line: read as the person\'s own words'
        if m['id'] in self.g.signed_for:
            v = given if given in VOICES else 'agent-drafted'
            return '', v, None if given in VOICES else 'signed by the agent at the person\'s word: read as agent-drafted'
        if m['move'] == 'clarify':
            return '', given if given in VOICES else 'agent', None
        if m['move'] in MANDATE_MOVES:
            ok, why = mandate_covers(self.g.norm.get('delegation', []), m['actor'], m['move'], m['terms'],
                                     for_=m['for'], holon=self.a['holon'], now=m['ts'] or None)
            if not ok:
                return 'an agent\'s %s counts only within a mandate: %s' % (m['move'], why), None, None
            said = None if given == 'under-mandate' else \
                'voice set to under-mandate (the line carried %s)' % (given or 'none')
            return '', 'under-mandate', said
        return ('an agent\'s %s counts only with the person\'s word on the line, never on a standing '
                'delegation' % m['move']), None, None

    # -- the resolution
    def _accepted_now(self):
        """(party, terms, move id) of every accept that stands for the current version, in move order."""
        out = [(mid_order, p, t, mid) for p, (v, t, mid, mid_order) in self.acc.items()
               if v == self.version or self.shape == 'consent']
        return [(p, t, mid) for _, p, t, mid in sorted(out)]

    def _met(self, supporters):
        q = self.q or {}
        if q.get('stewards'):
            return set(q['stewards']) <= set(supporters)
        need = q.get('need')
        if q.get('everyone') and self.parties is not None:
            need = len(self.parties)             # everyone now, a referred party included
        return need is not None and len(set(supporters)) >= need

    def _need_words(self):
        return (self.q or {}).get('basis') or 'two-party'

    def resolve(self):
        cur = self.terms if self.terms is not None else _base_terms(self.a)
        if self.shape is None:
            acc = self._accepted_now()
            if acc:
                p, t, mid = acc[0]
                return {'terms': t or cur, 'basis': '%s accepted (%s)' % (p, mid[:12]), 'at': mid}
            return None
        if self.shape == 'converge':
            opts = {}
            for i, (p, t, mid) in enumerate(self._accepted_now()):
                k = _canon(t or cur)
                o = opts.setdefault(k, {'terms': t or cur, 'who': [], 'first': i, 'at': mid})
                o['who'].append(p)
                o['at'] = mid
            good = [o for o in opts.values() if self._met(o['who'])]
            if not good:
                return None
            o = sorted(good, key=lambda o: (-len(o['who']), o['first'], _canon(o['terms'])))[0]
            return {'terms': o['terms'], 'basis': 'converged: %s accepted it; the quorum is %s'
                    % (', '.join(sorted(o['who'])), self._need_words()), 'at': o['at']}
        if self.shape == 'consent':
            open_obj = sorted(p for p, o in self.objections.items() if o['open'])
            if open_obj:
                return None
            ok = sorted(p for p, ans in self.answers.items() if ans == 'accepted'
                        or (ans == 'declined' and not self.objections.get(p, {}).get('open')))
            if 'accepted' not in self.answers.values() or not self._met(ok):
                return None
            return {'terms': cur, 'basis': 'consent: no objection remains; %s answered; the quorum is %s'
                    % (', '.join(ok), self._need_words()), 'at': self.rows[-1]['id'] if self.rows else None}
        if self.shape == 'call':
            if not self.awarded:
                return None
            bid, award = self.awarded
            return {'terms': award['terms'] or bid['terms'] or cur,
                    'basis': 'awarded to %s (%s)' % (bid['for'], bid['id'][:12]), 'at': award['id']}
        if self.shape == 'gather':
            if not self.harvest:
                return None
            named = set(self.harvest['answers']) | set(_strs(_dict(self.harvest['terms']).get('harvest')))
            who = sorted({p for p, ms in self.contrib.items() for m in ms if m in named})
            if not self._met(who):
                return None
            return {'terms': dict(self.harvest['terms'] or {}, harvest=sorted(named)),
                    'basis': 'gathered: the harvest names contributions from %s; the quorum is %s'
                    % (', '.join(who), self._need_words()), 'at': self.harvest['id']}
        return None

    # -- one move
    def apply(self, m, order):
        a, who, mv = self.a, m['for'], m['move']
        row = {k: m[k] for k in ('id', 'move', 'actor', 'for', 'ts', 'terms', 'answers', 'via')}
        if who != a['asker'] and self.parties is not None and who not in self.parties:
            self.refused.append(dict(row, why='%s is not a party to this ask (%s)' % (who or '?', self.parties_basis)))
            return
        why = self.side(m)
        if not why:
            why, voice, said = self.agent_ok(m)
        if why:
            self.refused.append(dict(row, why=why))
            return
        row['voice'] = voice
        if said:
            row['voice_said'] = said
        if self.withdrawn or self.satisfied:
            self.ignored.append(dict(row, why='the conversation had closed (%s)'
                                     % ('withdrawn' if self.withdrawn else 'satisfied')))
            return
        if mv in ('done', 'satisfied', 'not_yet') and not self.agreed and not (self.shape == 'gather' and mv == 'done'):
            self.ignored.append(dict(row, why='a %s before any agreement changes nothing' % mv))
            return
        self.rows.append(row)
        if mv in ANSWER_OF:
            self.answers[who] = ANSWER_OF[mv]
            if mv != 'accept':
                self.acc.pop(who, None)
        if mv == 'accept':
            self.acc[who] = (self.version, m['terms'], m['id'], order)
            ob = self.objections.get(who)
            if ob and ob['open']:
                ob['open'] = False
                ob['how'] = 'integrated' if any(x > ob['order'] for x in self.amends) else 'withdrawn'
            self.bids[who] = m
            self.contrib.setdefault(who, []).append(m['id'])
        elif mv in ('counter', 'conditional', 'defer'):
            if mv == 'counter':
                self.round += 1
            self.counters[m['id']] = m
            if mv != 'defer':
                self.bids[who] = m
                if m['terms'] or m['text']:
                    self.contrib.setdefault(who, []).append(m['id'])
            if mv == 'conditional' and _dict(m['terms']).get('objection') is not None:
                self.objections[who] = {'move': m['id'], 'open': True, 'how': None, 'order': order}
        elif mv == 'decline':
            self.bids.pop(who, None)
            ob = self.objections.get(who)
            if _dict(m['terms']).get('objection') is not None:
                self.objections[who] = {'move': m['id'], 'open': True, 'how': None, 'order': order}
            elif ob and ob['open']:                      # a later plain decline: the objector stands aside
                ob['open'], ob['how'] = False, 'stood aside'
        elif mv == 'refer' and self.parties is not None:
            new = sorted({self.g.who(x) for x in m['to'] if actor_kind(x)} - set(self.parties) - {a['asker']})
            if new:
                self.parties = sorted(set(self.parties) | set(new))
                self.history.append({'at': m['id'], 'said': 'referred to %s, now a party' % ', '.join(new)})
        elif mv == 'release':
            self.bids.pop(who, None)
            self.history.append({'at': m['id'], 'said': '%s released their yes, with notice' % who})
        elif mv == 'amend':
            self.round += 1
            self.version += 1
            self.amends.append(order)
            self.terms = m['terms'] or self.terms
            self.by = m['by'] or self.by
        elif mv in ('accept_counter', 'reject_counter'):
            target = self._target(m, self.counters, fallback=True)
            if target is None:
                self.rows.pop()
                self.ignored.append(dict(row, why='it answers no counter, condition or deferral held'))
                return
            if mv == 'accept_counter':
                self.version += 1
                self.terms = m['terms'] or target['terms'] or self.terms
                if target['move'] == 'defer' and target['by']:
                    self.by = target['by']
                self.acc[target['for']] = (self.version, None, target['id'], order)
                self.answers[target['for']] = 'accepted'
                ob = self.objections.get(target['for'])
                if ob and ob['open']:
                    ob['open'], ob['how'] = False, 'integrated'
            elif self.answers.get(target['for']) == ANSWER_OF[target['move']]:
                self.answers[target['for']] = 'none'      # refused: the ask waits on the responder again
            self.counters.pop(target['id'], None)
        elif mv == 'award':
            if self.shape != 'call':
                self.rows.pop()
                self.ignored.append(dict(row, why='an award resolves only a call for takers'))
                return
            bids = {b['id']: b for b in self.bids.values()}
            pick = _strs(_dict(m['terms']).get('award'))
            target = self._target(m, bids, fallback=False) or next((bids[i] for i in pick if i in bids), None) \
                or next((b for b in self.bids.values() if b['for'] in pick), None)
            if target is None:
                self.rows.pop()
                self.ignored.append(dict(row, why='it names no bid held'))
                return
            self.awarded = (target, m)
            self.released = sorted(b['id'] for p, b in self.bids.items() if b['id'] != target['id'])
        elif mv == 'withdraw':
            self.withdrawn = m['id']
        elif mv == 'done':
            if self.shape == 'gather' and who == a['asker']:
                self.harvest = m
            else:
                self.done, self.not_yet = m['id'], None
        elif mv == 'satisfied':
            self.satisfied = m['id']
        elif mv == 'not_yet':
            self.not_yet = m['id'] if self.done else None
        self._settle(m)

    def _target(self, m, pool, fallback):
        """The held move this one answers; with fallback, the newest held when it names none."""
        hit = sorted((pool[i] for i in m['answers'] if i in pool), key=_key)
        if hit:
            return hit[-1]
        named = [i for i in m['answers'] if i != self.a['id'] and i != self.a.get('card')]
        return sorted(pool.values(), key=_key)[-1] if fallback and pool and not named else None

    def awaiting_asker(self):
        """True when a counter, condition or deferral waits on the asker's word."""
        return any(self.answers.get(c['for']) == ANSWER_OF[c['move']] for c in self.counters.values())

    def _settle(self, m):
        if self.withdrawn:
            return
        r = self.resolve()
        if r and not self.agreed:
            self.agreed = r
            self.history.append({'at': m['id'], 'said': 'agreed: %s' % r['basis']})
        elif r and self.agreed and _canon(r['terms']) != _canon(self.agreed['terms']):
            self.agreed = r
            self.history.append({'at': m['id'], 'said': 'agreed again, on other terms: %s' % r['basis']})
        elif not r and self.agreed:
            self.history.append({'at': m['id'], 'said': 'the agreement no longer stands; open again'})
            self.agreed, self.done, self.not_yet = None, None, None

    # -- the state
    def state(self, worked, moment):
        if self.withdrawn:
            return 'withdrawn'
        if self.agreed:
            if self.satisfied:
                return 'satisfied'
            if self.not_yet:
                return 'not_yet'
            if self.done or worked:
                return 'performing'
            return 'agreed'
        ps = self.parties if self.parties is not None else sorted(self.answers)
        if ps and all(self.answers.get(p) == 'declined' for p in ps):
            return 'declined'
        due = parse_time(self.by)
        if due is not None and moment is not None and due < moment:
            return 'lapsed'
        return 'open'


def _run(a, moves, acks, worked, received, g, offered=None):
    r = _Run(a, g)
    for p, ids in sorted((offered or {}).items()):
        if p != a['asker'] and (r.parties is None or p in r.parties):
            r.contrib.setdefault(p, []).extend(sorted(ids))     # a say or an offer to a gather is a contribution
    for i, m in enumerate(sorted(moves, key=_key)):
        r.apply(m, i)
    st = r.state(worked, g.moment)
    parties = r.parties if r.parties is not None else sorted({m['for'] for m in r.rows if m['for'] != a['asker']})
    answers = {p: r.answers.get(p, 'none') for p in parties}
    # an agent's clarify is never a person's acknowledgment (types.json `delegate.mandate`)
    movers = {m['for'] for m in r.rows if not (actor_kind(m['actor']) == 'agent' and m['move'] == 'clarify')}
    performers = [a['asker']] if a['type'] == 'offer' else [p for p in parties if answers[p] == 'accepted']
    if r.awarded:
        performers = [r.awarded[0]['for']]
    owed = []                                          # who owes the next move, and whether an answer or the work
    if st == 'open':                                   # who has not answered, and the asker when a counter waits
        owed = [{'by': p, 'to': 'answer'} for p in parties if answers[p] == 'none']
        if r.awaiting_asker():
            owed.append({'by': a['asker'], 'to': 'answer'})
    elif r.shape == 'gather' or st not in ('agreed', 'performing', 'not_yet'):
        owed = []
    elif st == 'performing' and r.done:                # delivered: the one served says satisfied or not yet
        owed = [{'by': p, 'to': 'close'} for p in sorted(r.customers)]
    else:                                              # agreed, or not yet: the performer owes the work
        owed = [{'by': p, 'to': 'do'} for p in sorted(set(performers))]
    owed = sorted({(o['by'], o['to']): o for o in owed}.values(), key=lambda o: (o['by'], o['to']))
    waiting = sorted({o['by'] for o in owed})
    tally = {'n': len(parties), 'received': len(set(received) & set(parties)),
             'acknowledged': len((movers | set(acks)) & set(parties)),
             'answered': sum(1 for p in parties if answers[p] != 'none'),
             'agreed': sum(1 for p in parties if answers[p] == 'accepted'),
             'declined': sum(1 for p in parties if answers[p] == 'declined')}
    tally['open'] = tally['n'] - tally['answered']
    out = {k: a[k] for k in ('id', 'type', 'holon', 'actor', 'asker', 'ts', 'title', 'why', 'effort', 'minutes',
                             'shape', 'voice', 'to', 'card')}
    out.update({'by': r.by, 'by_asked': a.get('by'), 'quorum': a.get('quorum') if isinstance(a.get('quorum'), (str, int, list)) else None,
                'state': st, 'terms': r.agreed['terms'] if r.agreed and st != 'withdrawn' else None,
                'resolution': r.agreed['basis'] if r.agreed and st != 'withdrawn' else None,
                'round': r.round, 'moves': r.rows, 'answers': answers, 'released': r.released if r.agreed else [],
                'waiting_on': waiting, 'owed': owed, 'tally': tally, 'refused': r.refused, 'ignored': r.ignored,
                'history': r.history, 'parties': parties, 'parties_basis': r.parties_basis,
                'objections': {p: {'move': o['move'], 'open': o['open'], 'how': o['how']}
                               for p, o in sorted(r.objections.items())},
                'done': r.done, 'as_of': g.moment.isoformat(timespec='seconds') if g.moment else None})
    if r.q:
        out['quorum_basis'] = r.q['basis']
        if not r.q.get('stewards') and r.q.get('need') is None and not (r.q.get('everyone') and r.parties is not None):
            out['cannot_resolve'] = r.q['basis']         # said, never an ask open forever in silence
    if a.get('voice_said'):
        out['voice_said'] = a['voice_said']
    if a.get('_from_item'):
        out['basis'] = 'read from the folded item: its line was not among the lines given'
    return out


# ---------------------------------------------------------------- the whole

def report(items, lines, now=None, holon=None, trust=None):
    """Every ask with its state, and the moves that could not be placed."""
    g = _Ground(items, lines, trust, now)
    asks_, not_counted, pending = {}, [], []
    for l in g.raw:
        typ = _s(l.get('type'))
        if typ not in ASK_TYPES or (typ == 'say' and _body(l).get('intent') != 'ask'):
            continue
        why = g.why_not(l)
        if why:
            not_counted.append({'id': _s(l.get('id')), 'type': typ, 'why': why})
            continue
        asks_[_s(l.get('id'))] = _ask_from_line(l, g)
    for c in sorted(g.norm.get('card', []), key=_key):
        if isinstance(c, dict) and field(c, 'asked') in ('request', 'offer') and item_id(c) \
                and not is_untrusted(c) and not any(x.get('card') == item_id(c) for x in asks_.values()) \
                and item_id(c) not in asks_ and not set(c.get('events') or []) & set(asks_):
            asks_[item_id(c)] = _ask_from_item(c, g)
    by_card = {}
    for a in sorted(asks_.values(), key=_key):
        if a.get('card'):
            by_card[a['card']] = a['id']                     # the newest ask on a card holds it
    moves = {i: [] for i in asks_}
    acks = {i: set() for i in asks_}
    worked = {i: False for i in asks_}
    offered = {i: {} for i in asks_}
    received = {i: {g.who(_s(r.get('actor'))) for r in a['receipts']} for i, a in asks_.items()}
    threads = {i: {item_id(t) for t in g.norm.get('thread', []) if isinstance(t, dict)
                   and set(links(t, 'anchored_to') + _strs(field(t, 'anchor'))) & _refs(a)} for i, a in asks_.items()}
    index = {}                                           # an ask's id, its card and its threads -> the asks
    for i, a in asks_.items():
        for x in _refs(a) | threads[i]:
            index.setdefault(x, set()).add(i)
    for l in g.raw:
        typ, lid = _s(l.get('type')), _s(l.get('id'))
        if typ == 'move':
            root = _s(_body(l).get('root'))
            why = g.why_not(l)
            if why:
                not_counted.append({'id': lid, 'type': 'move', 'root': root or None, 'why': why})
                continue
            mv = _s(_body(l).get('move'))
            target = root if root in asks_ else by_card.get(root)
            if mv not in MOVES:
                not_counted.append({'id': lid, 'type': 'move', 'root': root or None,
                                    'why': 'the move %r is not one of the grammar' % mv[:40]})
            elif not target:
                pending.append({'id': lid, 'move': mv, 'root': root or None, 'actor': _s(l.get('actor')),
                                'why': 'its root is not a held ask: not yet replicated, or not an ask'})
            else:
                moves[target].append(_move(l, g, mv, 'move'))
            continue
        if lid in asks_ or typ not in ('answer', 'commit', 'done', 'settle', 'offer', 'say', 'claim', 'tea', 'receive'):
            continue
        if g.why_not(l):
            continue
        named = set(links(l, 'answers')) | set(links(l, 'anchored_to')) | set(links(l, 'fulfils')) | \
            {_s(_body(l).get(k)) for k in ('card', 'commitment', 'of') if _s(_body(l).get(k))}
        for i in sorted({i for x in named for i in index.get(x, ())}):
            a = asks_[i]
            if typ == 'receive':
                if _s(_body(l).get('of')) in _refs(a) or set(links(l, 'answers')) & _refs(a):
                    received[i].add(g.who(l))
                continue
            m = _kit_moves(l, a, g, a.get('shape'))
            if m is None and typ == 'settle' and _touches(l, a, g, threads[i]):
                m = _move(l, g, 'satisfied', 'settle', terms={})
            if m is not None:
                moves[i].append(m)
            elif typ in ('say', 'offer') and _touches(l, a, g, threads[i]):
                if actor_kind(_s(l.get('actor'))) == 'person':     # an agent's say is no acknowledgment
                    acks[i].add(g.who(l))
                if a.get('shape') == 'gather':
                    offered[i].setdefault(g.who(l), set()).add(lid)
            elif typ in ('claim', 'tea') and _touches(l, a, g, set()):
                worked[i] = True
    out = []
    for i, a in sorted(asks_.items(), key=lambda kv: _key(kv[1])):
        if holon and a['holon'] != holon and holon not in a.get('to', []):
            continue
        out.append(_run(a, moves[i], acks[i], worked[i], received[i], g, offered[i]))
    return {'asks': out, 'pending': sorted(pending, key=lambda p: p['id']),
            'not_counted': sorted(not_counted + g.bad, key=lambda p: (p['id'], p['why'])),
            'as_of': g.moment.isoformat(timespec='seconds') if g.moment else None, 'basis': g.moment_basis,
            'trust_basis': 'the fold\'s trust map' if g.trust is not None else
            'no trust map given: lines are read by the person-or-delegation rule alone'}


def asks(items, lines, now=None, holon=None, trust=None):
    """Every ask (request, offer, propose, rfg, a say with intent ask) with its state from its moves."""
    return report(items, lines, now=now, holon=holon, trust=trust)['asks']


# ---------------------------------------------------------------- lines a person (or agent) signs

def move_line(ask, move, actor, for_, terms=None, text=None, answers=None, now=None):
    """An unsigned `move` line on an ask. The signer signs it; the fold decides whether it counts."""
    a = ask if isinstance(ask, dict) else {}
    root, holon = _s(a.get('id')), _s(a.get('holon'))
    if not root or not holon:
        raise ValueError('an ask with an id and a holon is needed')
    mv = _s(move)
    if mv not in MOVES:
        raise ValueError('%r is not a move of the grammar (%s)' % (mv, ' · '.join(MOVES)))
    k = actor_kind(_s(actor))
    if k not in ('person', 'agent'):
        raise ValueError('the actor must be a person: or an agent:, not %r' % (actor,))
    f = _s(for_) or (_s(actor) if k == 'person' else '')
    if actor_kind(f) != 'person' or (k == 'person' and f != _s(actor)):
        raise ValueError('a move answers for a person: a person for themselves, an agent for its person')
    if terms is not None and not isinstance(terms, dict):
        raise ValueError('terms are a map of named terms')
    voice = 'human-words' if k == 'person' else ('under-mandate' if mv in MANDATE_MOVES else 'agent-drafted')
    body = {'move': mv, 'root': root, 'terms': _clean(terms) if terms else None,
            'text': _s(text) or None, 'voice': voice}
    if mv == 'defer' and _s(_dict(terms).get('by')):
        body['by'] = _s(terms['by'])
    ans = _strs(answers) or [root]
    t = parse_time(now) if now is not None else None
    ts = (t or dt.datetime.now().astimezone()).isoformat(timespec='seconds')
    reason = 'human' if k == 'person' else 'delegated'
    try:
        import record
        return record.make_line(_s(actor), f, holon, 'move', body, {'answers': ans}, reason=reason, ts=ts)
    except ImportError:
        from gamecore import canonical_id
        body = {k2: v for k2, v in body.items() if v is not None}
        l = {'v': 1, 'ts': ts, 'actor': _s(actor), 'for': f, 'holon': holon, 'type': 'move', 'body': body,
             'links': {'answers': ans}, 'audience': 'holon', 'reason': reason, 'prev': ''}
        l['id'] = canonical_id(l)
        l['sig'] = ''
        return l


# ---------------------------------------------------------------- the face

def effort_words(minutes):
    """Minutes in plain words: '1 minute', '45 minutes', '2 hours 10 minutes'."""
    m = _int(minutes)
    if m is None or m < 0:
        return 'effort not said'
    if m < 60:
        return '%d minute%s' % (m, '' if m == 1 else 's')
    h, r = divmod(m, 60)
    out = '%d hour%s' % (h, '' if h == 1 else 's')
    return out + (' %d minute%s' % (r, '' if r == 1 else 's') if r else '')


def _cell(v):
    return ' '.join(str('—' if v is None or v == '' else v).replace('|', '\\|').split())


def _line_of(a):
    title = _cell(a.get('title') or a.get('id', '')[:12])
    bits = ['%s' % _cell(a.get('state')), 'round %d' % (_int(a.get('round')) or 0)]
    if a.get('shape'):
        bits.append(_cell(a['shape']))
    if a.get('by'):
        bits.append('by %s' % _cell(a['by']))
    bits.append('asks %s' % effort_words(a.get('effort')))
    return '**%s** (%s)' % (title, '; '.join(bits))


OWED_WORDS = {'answer': 'to answer', 'close': 'to answer', 'do': 'to do'}


def _owed(a):
    return [o for o in (a.get('owed') or []) if isinstance(o, dict) and o.get('to') in OWED_WORDS]


def _who_owes(a):
    o = _owed(a)
    if not o:
        return 'no one'
    return ', '.join('%s %s' % (_cell(x.get('by')), OWED_WORDS[x['to']]) for x in o)


def _terms_line(a):
    return ['  - agreed: %s' % _cell(_canon(a['terms']))] if a.get('terms') else []


def render(asks_, actor=None):
    """Markdown: what each ask waits on, and, for one actor, what is owed by them (to answer, to do).

    An ask lands in one place for a reader: under "Owed by you" when they owe its next move, else
    under "Waiting on" when they are its asker or a party and another owes it."""
    rows = [a for a in (asks_ if isinstance(asks_, list) else []) if isinstance(a, dict)]
    me = _s(actor) or None
    out = ['# The conversations for action', '']
    if me is None:
        out += ['## Waiting on', '']
        if not rows:
            out.append('Nothing asked yet.')
        for a in rows:
            out.append('- %s: waiting on %s.' % (_line_of(a), _who_owes(a)))
            out += _terms_line(a)
            if a.get('cannot_resolve'):
                out.append('  - cannot resolve: %s' % _cell(a['cannot_resolve']))
        out.append('')
        return '\n'.join(out)
    answer, do, waiting = [], [], []
    for a in rows:
        mine = [o['to'] for o in _owed(a) if o.get('by') == me]
        involved = a.get('asker') == me or me in (a.get('parties') or [])
        if 'do' in mine:
            do.append(a)
        elif mine:
            answer.append(a)
        elif involved:
            waiting.append(a)
    out += ['## Waiting on', '']
    if not waiting:
        out.append('Nothing waits on another.')
    for a in waiting:
        out.append('- %s: waiting on %s.' % (_line_of(a), _who_owes(a)))
        out += _terms_line(a)
        if a.get('cannot_resolve'):
            out.append('  - cannot resolve: %s' % _cell(a['cannot_resolve']))
    out += ['', '## Owed by you: to answer', '']
    if not answer:
        out.append('Nothing is yours to answer.')
    for a in answer:
        why = (' Why: %s.' % _cell(a['why'])) if a.get('why') else ''
        frm = '' if a.get('asker') == me else ', from %s' % _cell(a.get('asker'))
        out.append('- %s%s.%s' % (_line_of(a), frm, why))
    out += ['', '## Owed by you: to do', '']
    if not do:
        out.append('Nothing agreed is yours to do.')
    for a in do:
        frm = '' if a.get('asker') == me else ', for %s' % _cell(a.get('asker'))
        out.append('- %s%s.' % (_line_of(a), frm))
        out += _terms_line(a)
    out.append('')
    return '\n'.join(out)


# ---------------------------------------------------------------- the CLI

def _read_json(path, what):
    if os.path.islink(path):
        raise ValueError('%s is a link; it is not read' % path)
    with open(path, encoding='utf-8') as f:
        if what == 'lines':
            out = []
            for n, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    v = json.loads(raw)
                except ValueError:
                    print('negotiation: line %d of %s is not JSON; left out' % (n, path), file=sys.stderr)
                    continue
                if isinstance(v, dict):
                    out.append(v)
            return out
        return json.load(f)


def _main(argv=None):
    ap = argparse.ArgumentParser(description='The conversations for action: asks and their moves, folded.')
    ap.add_argument('items', help='a JSON file of folded items (the output of record.py fold)')
    ap.add_argument('--lines', required=True, help='a JSONL file of the raw lines')
    ap.add_argument('--holon')
    ap.add_argument('--now')
    ap.add_argument('--actor', help='whose side to render: what waits on them and what they owe')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        items = _read_json(a.items, 'items')
        lines = _read_json(a.lines, 'lines')
    except (OSError, ValueError) as e:
        print('negotiation: cannot read: %s' % e, file=sys.stderr)
        return 2
    r = report(items, lines, now=a.now, holon=a.holon)
    if a.json:
        print(json.dumps(r, indent=1, sort_keys=True, ensure_ascii=False))
    else:
        print(render(r['asks'], a.actor), end='')
    return 0


if __name__ == '__main__':
    sys.exit(_main())
