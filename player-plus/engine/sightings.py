#!/usr/bin/env python3
"""sightings.py — the living map: a holon's Sightings, their lifecycle, and its triage.

    lifecycle(items, lines=None, now=None) -> {sighting id: {state, weight, resighted_by, resightings,
                 accepted_by, picked_up_by, fixed_ts, fixed_by, closed, responded_by, became,
                 needs_response, triage, kind}}
    triage(items, holon=None, lines=None, now=None) -> [sighting row, ...]
    by_holon(triaged, holons) -> {holon id: {as_of, new, held, elevated, folded}}
    the_map(items, lines=None, holon=None, now=None) -> {by_place, by_kind, open, pains_open, retracted, as_of}
    scoreboard(items, lines=None, holon=None) -> {player: {defects_sighted, sightings, resightings, fixed_by_me}}
    paper(sighting) -> 'kind · where · what I saw'
    elevate_line · hold_line · claim_line · resight_line -> unsigned lines (a person signs)

Each `sight` line is one Sighting, placed in the holon where it was seen, of one of nine kinds
(defect · hazard · blocked · wonder · offer · request · question · witness · pain; the fold keeps
the sighting's own kind as body_kind). Sightings from every player, re-sighted by others as they
pass the same place, compose the living map of reality, the ground the work moves over.

The lifecycle (SCHEMA.md, the Card kinds; the fold sets seen, accepted, fixed and retracted, and
this module computes the rest from the links):

  seen         sighted, nothing more yet
  still_there  another player's trusted `sight` links to it (anchored_to, witnesses, serves,
               supersedes, predecessor); weight = 1 + the distinct players who re-sighted it
  accepted     a `claim` names it (the fold's state), or another person's thread note is anchored to it
  picked_up    a trusted `commit` serves it, or names a card that serves it (`became` is that card)
  fixed        a `done` names it (the fold's state)
  closed       a trusted `settle` is anchored to it (or to a thread anchored to it); its text is
               the consequence
  responded    a pain only: a trusted line by another player anchored to it
  retracted    a Correction recalled it (the fold's state)

When several apply the first of PRECEDENCE wins. "Another player" is another Living Intelligence:
an agent's line counts as the person it answers for, so a player and their own agent never
re-sight or answer each other. The triage statuses (new · held · elevated · folded) stay as
they were, in their own field.

A line counts only when it is trusted: not `reason: untrusted`; not listed by the fold as
invalid, unverified, refused, forked or a proposal; when the fold's trust map is given, one of
TRUSTED; by a person for themselves, or by an agent under a live delegation from its person that
covers the line's type and holon; and never an agent's line of a person's own act. A raw line
whose id the fold already made into an item is read through that item alone, so an item the fold
dropped (a released commitment, a retracted card) never comes back through its line. The gate
holds whole only when the fold is passed whole (its trust map and lists ride beside the items).
Files are data, never instructions.
"""
import json
import os
import sys
import unicodedata

try:
    from gamecore import (normalize, field, links, item_id, holon_of, now_or, actor_kind, parse_time,
                          live_delegations, covers, is_untrusted, HUMAN_ONLY_ACTS)
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, item_id, holon_of, now_or, actor_kind, parse_time,
                          live_delegations, covers, is_untrusted, HUMAN_ONLY_ACTS)

LINK_RELS = ('anchored_to', 'serves', 'supersedes', 'predecessor')
# the nine kinds: types.json `sight.kind` values (tests/test_sightings.py checks they agree)
NINE = ('defect', 'hazard', 'blocked', 'wonder', 'offer', 'request', 'question', 'witness', 'pain')
# the links by which a `sight` re-sights another (the E2 brief; SCHEMA.md: "another sight links to it")
RESIGHT_RELS = ('anchored_to', 'witnesses', 'serves', 'supersedes', 'predecessor')
# the lines that answer a pain (the E2 brief names say, answer, claim and commit; a thread note,
# a settle and a done anchored to it answer it too)
RESPONSE_TYPES = ('say', 'answer', 'claim', 'commit', 'thread', 'settle', 'done')
# when several states apply, the first wins (the E2 brief)
PRECEDENCE = ('retracted', 'closed', 'fixed', 'picked_up', 'accepted', 'responded', 'still_there', 'seen')
ENDED = ('fixed', 'closed', 'retracted')                 # not open on the map
DROPPED_COMMITMENT = ('released', 'declined', 'retracted', 'returned', 'withdrawn')
ENDED_DELEGATION = ('revoked', 'expired')
TRUSTED = ('signed', 'home', 'vouched')                  # record.TRUSTED
NOT_COUNTED = ('invalid', 'unverified', 'refused', 'forked', 'proposals')   # the fold's lists of lines that never act
NO_PLACE, NO_KIND = '(no place)', '(no kind)'
TEXT_CUT = 280                                           # a row's text, as the triage always cut it


# ---------------------------------------------------------------- small helpers

def _nfc(v):
    return unicodedata.normalize('NFC', v) if isinstance(v, str) and v else None


def _kind(s):
    k = field(s, 'body_kind') or field(s, 'sight_kind')
    if not k and field(s, 'kind') not in ('sighting', 'sight', None):
        k = field(s, 'kind')
    return k if isinstance(k, str) else None


def _lines(lines):
    return [l for l in lines if isinstance(l, dict)] if isinstance(lines, (list, tuple)) else []


def _list(v):
    return v if isinstance(v, (list, tuple)) else []


def _type(l):
    t = l.get('type') if isinstance(l.get('type'), str) else l.get('kind')
    return t if isinstance(t, str) else None


def _ts(x):
    v = field(x, 'ts')
    return v if isinstance(v, str) else ''


def _key(x):
    return (_ts(x), item_id(x))


def _state(x):
    return str(field(x, 'state') or '').lower()


def _sid_of(x):
    v = x.get('id') if isinstance(x, dict) else None
    return v if isinstance(v, str) and v else None


def _anchors(x):
    """Every id a line or item is anchored to, answers, fulfils or names as its card."""
    out = set(links(x, 'anchored_to')) | set(links(x, 'answers')) | set(links(x, 'fulfils'))
    for k in ('anchor', 'card'):
        v = field(x, k)
        if isinstance(v, str) and v:
            out.add(v)
        elif isinstance(v, list):
            out.update(i for i in v if isinstance(i, str) and i)
    return out


def _thread_anchors(th):
    a = field(th, 'anchor')
    s = set(links(th, 'anchored_to'))
    if isinstance(a, str) and a:
        s.add(a)
    elif isinstance(a, list):
        s.update(i for i in a if isinstance(i, str) and i)
    return s


def _excluded(items):
    """Ids the fold says never act, and its trust map, when the caller passed the fold whole."""
    ex, trust = set(), {}
    if isinstance(items, dict):
        for k in NOT_COUNTED:
            for e in _list(items.get(k)):
                if isinstance(e, str):
                    ex.add(e)
                elif isinstance(e, dict):
                    for f in ('id', 'line'):
                        if isinstance(e.get(f), str):
                            ex.add(e[f])
        if isinstance(items.get('trust'), dict):
            trust = {k: v for k, v in items['trust'].items() if isinstance(k, str)}
    return ex, trust


class _Ground:
    """What one call reads: the sightings, the trusted lines, and who each agent answers for."""

    def __init__(self, items, lines, now):
        self.norm = normalize(items)
        self.now = now
        ex, trust = _excluded(items)
        raw = _lines(lines)
        self.by_id = {l['id']: l for l in raw if isinstance(l.get('id'), str)}
        # every id the fold made into an item, whatever its state: its line is read through the item
        self.folded = {item_id(x) for v in self.norm.values() for x in v if isinstance(x, dict) and item_id(x)}
        counted, seen = [], set()
        for l in sorted((l for l in raw if self._counts(l, ex, trust)), key=_key):
            if l['id'] not in seen:
                seen.add(l['id'])
                counted.append(l)
        self.counted = counted                            # every trusted line, once
        self.lines = [l for l in counted if l['id'] not in self.folded]   # those no folded item stands for
        # who each agent answers for: from trusted lines and standing delegations only, the earliest first
        cand = {}
        for l in counted:
            a, f = l.get('actor'), l.get('for')
            if actor_kind(a) == 'agent' and actor_kind(f) == 'person':
                cand.setdefault(_nfc(a), []).append((_ts(l), l['id'], _nfc(f)))
        for d in self.norm.get('delegation', []):
            a, f = field(d, 'to'), field(d, 'actor') or field(d, 'for')
            if actor_kind(a) == 'agent' and actor_kind(f) == 'person' and not is_untrusted(d) \
                    and _state(d) not in ENDED_DELEGATION and not field(d, 'revoked'):
                cand.setdefault(_nfc(a), []).append((_ts(d), item_id(d), _nfc(f)))
        self.agent_for = {a: min(v)[2] for a, v in cand.items()}
        self.sights = {item_id(s): s for s in self.norm.get('sighting', [])
                       if isinstance(s, dict) and item_id(s) and not is_untrusted(s)}

    def _counts(self, l, ex, trust):
        lid, typ = l.get('id'), _type(l)
        if not isinstance(lid, str) or not lid or not typ or lid in ex:
            return False
        if trust and lid in trust and trust[lid] not in TRUSTED:
            return False
        if '_trust' in l and l['_trust'] not in TRUSTED:
            return False
        if str(l.get('reason') or '').lower() == 'untrusted':
            return False
        a, f = l.get('actor'), l.get('for')
        k = actor_kind(a)
        if k == 'person':
            return f in (None, a)
        if k != 'agent' or actor_kind(f) != 'person' or typ in HUMAN_ONLY_ACTS:
            return False
        at = parse_time(l.get('ts')) or now_or(self.now)
        dl = [d for d in live_delegations(self.norm, a, at) if (field(d, 'actor') or field(d, 'for')) == f]
        return covers(dl, typ, l.get('holon') or holon_of(l))

    def who(self, x):
        """The Living Intelligence a line or an item answers for: its person, or the person its agent serves."""
        if isinstance(x, str):
            return self.agent_for.get(_nfc(x), _nfc(x)) if actor_kind(x) == 'agent' else _nfc(x)
        if not isinstance(x, dict):
            return None
        f = x.get('for')
        if actor_kind(f) == 'person':
            return _nfc(f)
        a = x.get('actor')
        return self.who(a) if actor_kind(a) else None


# ---------------------------------------------------------------- triage (its statuses unchanged)

def _triage_rows(items, holon=None, lines=None):
    norm = normalize(items)
    sights = {item_id(s): s for s in norm.get('sighting', []) if item_id(s)}
    elevated = {}
    for l in _lines(lines) + [x for x in norm.get('elevate', []) if isinstance(x, dict)]:
        if 'elevate' not in (l.get('type'), l.get('kind')):
            continue
        a = l.get('actor')
        if actor_kind(a) != 'person' or l.get('for') not in (None, a) or l.get('reason') == 'untrusted':
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else l
        what = b.get('what')
        if isinstance(what, str) and what in sights and what not in elevated:
            elevated[what] = {'by': a, 'to': b.get('to'), 'why': b.get('why'), 'witness': b.get('witness'),
                              'line': l.get('id'), 'ts': l.get('ts')}
    held = {}
    for th in sorted((t for t in norm.get('thread', []) if isinstance(t, dict)), key=_key):
        for sid in sorted(_thread_anchors(th) & set(sights)):
            held.setdefault(sid, {'thread': item_id(th), 'note': str(field(th, 'text') or '')[:200],
                                  'by': field(th, 'actor')})
    out = []
    for sid, s in sights.items():
        if holon and holon_of(s) != holon:
            continue
        into = next((x for r in LINK_RELS for x in links(s, r) if x in sights and x != sid), None)
        row = {'id': sid, 'holon': holon_of(s), 'kind': _kind(s), 'text': str(field(s, 'text') or '')[:TEXT_CUT],
               'where': field(s, 'where'), 'actor': field(s, 'actor'), 'ts': field(s, 'ts')}
        if sid in elevated:
            row.update(status='elevated', elevated=elevated[sid])
        elif sid in held:
            row.update(status='held', held=held[sid])
        elif into:
            row.update(status='folded', folded_into=into)
        else:
            row.update(status='new')
        out.append(row)
    return sorted(out, key=lambda r: (r['holon'], str(r['ts'] or ''), r['id']))


# ---------------------------------------------------------------- the lifecycle

def lifecycle(items, lines=None, now=None):
    """Each sighting's place in its lifecycle, computed from the fold's state and the links."""
    g = _Ground(items, lines, now)
    sights = g.sights
    tri = {r['id']: r['status'] for r in _triage_rows(items, lines=lines)}

    threads = sorted((t for t in g.norm.get('thread', []) if isinstance(t, dict) and item_id(t)
                      and not is_untrusted(t) and _state(t) != 'retracted'), key=_key)
    reach = {sid: {sid} for sid in sights}                # a sighting and the threads anchored to it
    on = {}                                               # thread id -> the sightings it is anchored to
    for th in threads:
        for sid in _thread_anchors(th) & set(sights):
            reach[sid].add(item_id(th))
            on.setdefault(item_id(th), set()).add(sid)

    # re-sightings, from folded sightings and trusted sight lines
    resight = {sid: {} for sid in sights}
    srcs = [x for x in sights.values() if _state(x) != 'retracted']
    srcs += [l for l in g.lines if _type(l) == 'sight']
    for x in srcs:
        xid = item_id(x)
        for rel in RESIGHT_RELS:
            for t in links(x, rel):
                if t in sights and t != xid:
                    resight[t].setdefault(xid, (g.who(x), _ts(x)))

    # cards that serve a sighting (what it `became`)
    serving = {}                                          # card id -> (ts, {sighting ids})
    cards = [c for c in g.norm.get('card', []) if isinstance(c, dict) and not is_untrusted(c)
             and _state(c) != 'retracted']
    for c in cards + [l for l in g.lines if _type(l) == 'card']:
        hit = set(links(c, 'serves')) & set(sights)
        if hit and item_id(c):
            serving.setdefault(item_id(c), (_ts(c), set()))[1].update(hit)

    # commitments that serve it, or name a card that serves it
    picked = {}
    comms = [c for c in g.norm.get('commitment', []) if isinstance(c, dict) and not is_untrusted(c)
             and _state(c) not in DROPPED_COMMITMENT]
    for c in comms + [l for l in g.lines if _type(l) == 'commit']:
        cid = item_id(c)
        if not cid:
            continue
        names = set(links(c, 'serves')) | set(links(c, 'anchored_to'))
        card = field(c, 'card')
        if isinstance(card, str) and card:
            names.add(card)
        for t in sorted(names):
            if t in sights:
                via = card if isinstance(card, str) and card in serving and t in serving[card][1] else None
                picked.setdefault(t, []).append((_ts(c), cid, g.who(c), via))
            if t in serving:
                for sid in serving[t][1]:
                    picked.setdefault(sid, []).append((_ts(c), cid, g.who(c), t))

    # settles anchored to it (a settled thread anchored to it, or a settle line)
    closed = {}
    for th in threads:
        if _state(th) != 'settled':
            continue
        ents = [e for e in _list(field(th, 'lines')) if isinstance(e, dict) and e.get('type') == 'settle']
        last = sorted(ents, key=lambda e: (str(e.get('ts') or ''), str(e.get('id') or '')))[-1] if ents else None
        lid, txt, ts_ = ((last.get('id'), last.get('text'), str(last.get('ts') or '')) if last
                         else (item_id(th), field(th, 'text'), _ts(th)))
        for sid in on.get(item_id(th), ()):
            closed.setdefault(sid, []).append((ts_, str(lid or ''), txt))
    for l in g.lines:
        if _type(l) != 'settle':
            continue
        for sid in sights:
            if set(links(l, 'anchored_to')) & reach[sid]:
                closed.setdefault(sid, []).append((_ts(l), l['id'], field(l, 'text')))

    # who fixed it (a trusted done naming it)
    dones = {}
    for l in g.lines:
        if _type(l) == 'done':
            for t in _anchors(l) & set(sights):
                dones.setdefault(t, []).append((_ts(l), l['id'], g.who(l)))

    out = {}
    for sid, s in sights.items():
        st = _state(s) or 'seen'
        kind = _kind(s)
        me = g.who(s)
        rs = {xid: v for xid, v in resight[sid].items() if v[0] and v[0] != me}
        by = sorted({v[0] for v in rs.values()})
        weight = 1 + len(by)

        hold_by = None
        for th in threads:
            tid = item_id(th)
            made = g.by_id.get(tid)
            if sid in on.get(tid, ()) and _state(th) != 'settled' and actor_kind(field(th, 'actor')) == 'person' \
                    and g.who(th) != me and (made is None or _type(made) == 'thread'):
                hold_by = field(th, 'actor')
                break
        holder = field(s, 'holder')
        accepted_by = holder if isinstance(holder, str) and holder else hold_by

        pk = sorted(picked.get(sid, []), key=lambda p: (p[0], p[1]))
        cl = sorted(closed.get(sid, []), key=lambda c: (c[0], c[1]))
        responders = set()
        if kind == 'pain':
            for l in g.lines:
                if _type(l) in RESPONSE_TYPES and _anchors(l) & reach[sid]:
                    responders.add(g.who(l))
            for th in threads:
                if sid in on.get(item_id(th), ()):
                    responders.add(g.who(th))
                    for e in _list(field(th, 'lines')):
                        if isinstance(e, dict):
                            eid = e.get('id')
                            src = g.by_id.get(eid) if isinstance(eid, str) else None
                            responders.add(g.who(src or e.get('actor')))
            if accepted_by:
                responders.add(g.who(accepted_by))
            responders.update(p[2] for p in pk)
        responders = sorted(r for r in responders if isinstance(r, str) and r and r != me)

        flags = set()
        if st == 'retracted':
            flags.add('retracted')
        if st in ('closed', 'settled') or cl:
            flags.add('closed')
        if st == 'fixed':
            flags.add('fixed')
        if st == 'picked_up' or pk:
            flags.add('picked_up')
        if st == 'accepted' or accepted_by:
            flags.add('accepted')
        if kind == 'pain' and (st == 'responded' or responders):
            flags.add('responded')
        if st == 'still_there' or weight > 1:
            flags.add('still_there')
        state = next((p for p in PRECEDENCE if p in flags), 'seen')

        fx = sorted(dones.get(sid, []), key=lambda d: (d[0], d[1]))
        fixed_ts = field(s, 'fixed_ts')
        fixed_by = None
        if st == 'fixed':
            given = field(s, 'fixed_by')
            fixed_by = next((d[2] for d in fx if d[0] == fixed_ts), fx[0][2] if fx else (given if isinstance(given, str) else None))
        own = sorted(((v[0], c) for c, v in serving.items() if sid in v[1]))
        became = next((p[3] for p in pk if p[3]), None) or (own[0][1] if own else None)
        out[sid] = {
            'state': state, 'weight': weight, 'kind': kind, 'triage': tri.get(sid),
            'resighted_by': by, 'resightings': [x for x, _ in sorted(rs.items(), key=lambda kv: (kv[1][1], kv[0]))],
            'accepted_by': accepted_by,
            'picked_up_by': pk[0][2] if pk else None,
            'fixed_ts': fixed_ts if isinstance(fixed_ts, str) else None,
            'fixed_by': fixed_by,
            'closed': {'settle': cl[-1][1], 'consequence': str(cl[-1][2] or '')[:TEXT_CUT] or None} if cl else None,
            'responded_by': responders,
            'became': became,
            'needs_response': kind == 'pain' and not responders and state not in ENDED and st != 'responded',
        }
    return out


# ---------------------------------------------------------------- triage, the map, the scoreboard

def triage(items, holon=None, lines=None, now=None):
    """The cell's triage of its sightings (new · held · elevated · folded), each row with its
    lifecycle state (`life`), its weight, whether it waits for a response, and whether its kind
    is one of the nine."""
    rows = _triage_rows(items, holon, lines)
    life = lifecycle(items, lines, now) if rows else {}
    for r in rows:
        lf = life.get(r['id']) or {}
        r['life'] = lf.get('state', 'seen')
        r['weight'] = lf.get('weight', 1)
        r['needs_response'] = bool(lf.get('needs_response'))
        r['known_kind'] = r['kind'] in NINE
    return rows


def by_holon(triaged, holons=None):
    out = {}
    for h in _list(holons):
        if isinstance(h, dict) and h.get('id'):
            out[h['id']] = {'as_of': (h.get('as_of') or {}).get('ts') if isinstance(h.get('as_of'), dict) else None,
                            'new': [], 'held': [], 'elevated': [], 'folded': []}
    for r in _list(triaged):
        if not isinstance(r, dict) or r.get('status') not in ('new', 'held', 'elevated', 'folded'):
            continue
        b = out.setdefault(r.get('holon'), {'as_of': None, 'new': [], 'held': [], 'elevated': [], 'folded': []})
        b[r['status']].append(r)
    return out


def the_map(items, lines=None, holon=None, now=None):
    """The living map: every sighting not retracted, by place and kind, heaviest first."""
    rows = triage(items, holon, lines, now)
    by_place, by_kind = {}, {}
    open_n = pains = gone = 0
    shown = []
    for r in rows:
        if r['life'] == 'retracted':
            gone += 1
            continue
        shown.append(r)
        where = _nfc(r.get('where')) or NO_PLACE
        kind = _nfc(r.get('kind')) or NO_KIND
        by_place.setdefault(where, {}).setdefault(kind, []).append(r)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if r['life'] not in ENDED:
            open_n += 1
            pains += int(kind == 'pain')
    for kinds in by_place.values():
        for k in kinds:
            kinds[k].sort(key=lambda r: (-r['weight'], str(r.get('ts') or ''), r['id']))
    newest = max((r['ts'] for r in shown if isinstance(r.get('ts'), str)), default=None)
    as_of = now_or(now).isoformat(timespec='seconds') if now is not None else newest
    return {'by_place': by_place, 'by_kind': by_kind, 'open': open_n, 'pains_open': pains,
            'retracted': gone, 'as_of': as_of}


def scoreboard(items, lines=None, holon=None):
    """Per player: the defects they sighted, their sightings, their re-sightings of others', and
    the sightings they fixed. Every defect is a gift. A retracted sighting counts for nothing."""
    g = _Ground(items, lines, None)
    life = lifecycle(items, lines)
    board = {}

    def row(who):
        return board.setdefault(who, {'defects_sighted': 0, 'sightings': 0, 'resightings': 0, 'fixed_by_me': 0})

    def resights_another(x, who):
        return any(t in g.sights and t != item_id(x) and g.who(g.sights[t]) != who
                   for r in RESIGHT_RELS for t in links(x, r))

    for sid, s in sorted(g.sights.items()):
        if holon and holon_of(s) != holon:
            continue
        lf = life.get(sid) or {}
        who = g.who(s)
        if lf.get('fixed_by'):
            row(lf['fixed_by'])['fixed_by_me'] += 1
        if not who or lf.get('state') == 'retracted':
            continue
        if resights_another(s, who):
            row(who)['resightings'] += 1
            continue
        row(who)['sightings'] += 1
        row(who)['defects_sighted'] += int(_kind(s) == 'defect')
    for l in g.lines:                                     # trusted, once each, and no folded item stands for it
        if _type(l) != 'sight':
            continue
        if holon and (l.get('holon') or '') != holon:
            continue
        who = g.who(l)
        if who and resights_another(l, who):
            row(who)['resightings'] += 1
    return {k: board[k] for k in sorted(board)}


def paper(sighting):
    """A Sighting on paper, one line: kind · where · what I saw."""
    if not isinstance(sighting, dict):
        return ''
    kind = _nfc(_kind(sighting)) or NO_KIND
    where = _nfc(field(sighting, 'where')) or NO_PLACE
    text = ' '.join(str(field(sighting, 'text') or '').split())
    return ' · '.join((kind, where, _nfc(text) or ''))


# ---------------------------------------------------------------- the acts, as unsigned lines

def _line(actor, holon, type_, body, links_, now, for_=None):
    for_ = for_ or actor
    try:
        import record
        return record.make_line(actor, for_, holon, type_, body, links_, ts=now_or(now).isoformat(timespec='seconds'))
    except Exception:
        from gamecore import canonical_id
        l = {'v': 1, 'ts': now_or(now).isoformat(timespec='seconds'), 'actor': actor, 'for': for_, 'holon': holon,
             'type': type_, 'body': body, 'links': links_ or {}, 'audience': 'holon', 'reason': 'human', 'prev': ''}
        l['id'] = canonical_id(l)
        l['sig'] = ''
        return l


def _sholon(sighting):
    return sighting.get('holon') if isinstance(sighting, dict) else None


def elevate_line(sighting, to, why, witness, actor, now=None):
    """The `elevate` line a person signs: publish this sighting upward, with a witness and why."""
    return _line(actor, _sholon(sighting), 'elevate',
                 {'what': _sid_of(sighting), 'to': to, 'why': why, 'witness': witness}, None, now)


def hold_line(sighting, note, actor, now=None):
    """A hold is a thread note anchored to the sighting, saying why it is held."""
    return _line(actor, _sholon(sighting), 'thread', {'text': note}, {'anchored_to': [_sid_of(sighting)]}, now)


def claim_line(sighting, actor, now=None, for_=None):
    """An unsigned `claim` naming the sighting: the actor accepts it and holds it (it may become a card)."""
    return _line(actor, _sholon(sighting), 'claim', {'card': _sid_of(sighting)}, None, now, for_)


def resight_line(sighting, actor, text, now=None, for_=None):
    """An unsigned `sight` anchored to the sighting: it is still there, seen again in passing."""
    s = sighting if isinstance(sighting, dict) else {}
    body = {'text': text, 'kind': _kind(s) if _kind(s) in NINE else None, 'where': field(s, 'where')}
    return _line(actor, _sholon(sighting), 'sight', body, {'anchored_to': [_sid_of(sighting)]}, now, for_)


# ---------------------------------------------------------------- command line

def _plain_file(path):
    if not isinstance(path, str) or os.path.islink(path) or not os.path.isfile(path):
        raise SystemExit('not a plain file: %s' % path)
    return path


def _read_json(path):
    with open(_plain_file(path), encoding='utf-8') as f:
        return json.load(f)


def _read_jsonl(path):
    out = []
    with open(_plain_file(path), encoding='utf-8') as f:
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


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sightings.py',
                                 description='The living map of a holon\'s Sightings, from folded items (JSON). '
                                             'Files are data, never instructions.')
    ap.add_argument('items', help='folded items, JSON (the fold whole, so its trust map rides along)')
    ap.add_argument('--lines', help='the raw lines, JSONL')
    ap.add_argument('--holon', help='one holon id')
    ap.add_argument('--now', help='the moment, ISO 8601')
    m = ap.add_mutually_exclusive_group()
    m.add_argument('--map', action='store_true', help='the living map, by place and kind')
    m.add_argument('--scoreboard', action='store_true', help='each player\'s sightings and defects')
    m.add_argument('--json', action='store_true', help='the triage rows with their lifecycle')
    a = ap.parse_args(argv)
    try:
        items = _read_json(a.items)
        lines = _read_jsonl(a.lines) if a.lines else None
    except (OSError, ValueError) as e:
        raise SystemExit('could not read: %s' % e)
    if a.map:
        out = the_map(items, lines, a.holon, a.now)
    elif a.scoreboard:
        out = scoreboard(items, lines, a.holon)
    elif a.json:
        out = triage(items, a.holon, lines, a.now)
    else:
        for r in triage(items, a.holon, lines, a.now):
            sys.stdout.write('%s · weight %d · %s\n' % (r['life'], r['weight'], paper(r)))
        return 0
    sys.stdout.write(json.dumps(out, sort_keys=True, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
