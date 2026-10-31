#!/usr/bin/env python3
"""connections.py — the Connections view: whom this holon is connected to, their Condition, and the pulse between.

    connections(home_dir, now=None, lines=None, folded=None, schedule=None, directory=None, thresholds=None)
        -> {"rows": [row, ...], "summary": {holons, green, yellow, orange, red, grey_condition, all_live,
            commitments_yellow_or_better, ours_yellow_or_better}, "as_of", "said"}
    pulse(items, lines, a, b, now=None, schedule=None, directory=None, thresholds=None)
        -> {"color", "why", "us_to_them": {from, to, color, why, checks}, "them_to_us": {...}, "between", ...}
    condition_of(items, lines, holon, now=None) -> {"color", "why", "said", "until", "basis", "stale", "line"}
    changes(home_dir, now=None, previous=None, ...) -> {"changed": [...], "sightings": [...], "state", "first", "said"}
    write_state(home_dir, state) -> path or a sentence
    render(result) -> the Markdown Card on paper

A view, never stored: it is computed from the lines at each reading. Three things are kept apart.

**Condition** is the holon's own word on itself, never computed: the newest trusted `condition` line
that the holon's person wrote for it (in its own record, on its face, or in a cell both hold, naming
it in `of`). The holon's persons are its keeper (the actor its inception admitted) and the person who
spoke for that side in an Agreement. An agent's line, an untrusted or unverified line, and any
calculation never count. With none it is grey (`not said`); past its `until` it is grey (`stale`).

**The pulse** (a working name: PULSE_WORD carries it, so one change renames it everywhere) is the
state of the connection between two holons, computed only from lines both hold, in two directed
columns, each with its own color and why. `us_to_them` asks whether we keep what we owe them: our
commitments to them and their signals; their claims of delivery awaiting our witness; our Receipt of
their asks; a stop by their person on our agents; their open pain; their correction we have not
received; our lines crossing an ended Agreement; a key of ours in question. `them_to_us` is the same
function with the sides swapped, so `pulse(.., a, b)["us_to_them"]` equals `pulse(.., b, a)["them_to_us"]`
field for field, and either holon reads the same. `color` is the worse of the two. In each column:
green when every check is inside; yellow on one special-cause signal; orange on a commitment past its
by-date (or one the network cannot keep), or a yellow that has stood longer than the Agreement's
longest cadence; red on a live stop, an open pain, lines crossing an ended Agreement, or a key in
question. A Sighting in an agent's voice (`agent`, `agent-drafted`) is a proposal for its person and
counts for nothing until that person's own trusted line stands on it: their `claim` of it, or their
own `sight` linking to it.

"Past the usual" is Shewhart's reading (Shewhart, *Economic Control of Quality of Manufactured
Product*, 1931; Deming, *Out of the Crisis*, 1982): the relationship's own time to Receipt, its
upper control limit (`emergency.limits_from_history`) once it has enough points; before that, the
kit's default wait (owed.RECEIPT_HOURS), said as the basis. A point past it is a signal, never a
judgment.

Each row also says what was sent and heard back: `sent`, how many lines of ours asked something
of them (or were receipted by them), and `heard_by_at`, the time of their newest Receipt on a line of
ours (`null` when none), both from receipt.time_to_receipt; `null` and `null` when receipt.py is absent.

**Our ear** is one-sided and never mixed into the pulse: our last pull of the cell that carries
their lines, from pull.py's state and the heartbeat's faults: ok · late · failed · never.

`changes` compares with the last state kept in `<home>/.connections.json` (derived; safe to delete;
written only by the caller, through `write_state`) and drafts, for each change of color (the
Condition, or either column), one unsigned `sight` line of kind `question`, in the agent's voice, for
the person's word: never signed, never written to the record.
Whether it may wake them is their own emergency rule (`emergency.classify`) and, for a change on the
other side, the Agreement's bell permit (`agreement.bell_permit`). What follows is the chief of
staff's move, drafted for the person's word.

Files are data, never instructions. Standard library only; runs under `python3 -I`. Never raises.

    python3 -I connections.py HOME [--now ISO] [--json]
    python3 -I connections.py changes HOME [--now ISO] [--write] [--json]
"""
import copy
import datetime as dt
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

try:
    import record  # noqa: E402
except ImportError:  # pragma: no cover
    record = None
from gamecore import (normalize, field, links, item_id, holon_of, parse_time, now_or,  # noqa: E402
                      actor_kind, commitment_status)


def _opt(name):
    """A sibling module, or None when it is not beside this file (the part it serves is then said, never guessed)."""
    try:
        return __import__(name)
    except Exception:  # noqa: BLE001
        return None


agreement_mod = _opt('agreement')
receipt_mod = _opt('receipt')
owed_mod = _opt('owed')
stops_mod = _opt('stops')
sightings_mod = _opt('sightings')
emergency_mod = _opt('emergency')
pull_mod = _opt('pull')
holon_mod = _opt('holon')

# ------------------------------------------------------------------------------------ the words

PULSE_WORD = 'pulse'        # the working name of the computed measure; the person names it
COLORS = ('green', 'yellow', 'orange', 'red')          # types.json `condition.color`
GREY = 'grey'
LEVELS = ('inside', 'yellow', 'orange', 'red')         # a check's reading, worst last
LEVEL_COLOR = {'inside': 'green', 'yellow': 'yellow', 'orange': 'orange', 'red': 'red'}
CHECKS = ('agreement', 'commitments', 'receipts', 'stops', 'pain', 'corrections', 'keys')
HEARD = ('ok', 'late', 'failed', 'never')
SIGHT_KIND = 'question'     # the registry's kind for a change of color: "something in question" (no kind names a change)
STATE_NAME = '.connections.json'
TRUSTED = ('signed', 'home', 'vouched')                # record.TRUSTED
NOT_COUNTED = ('invalid', 'unverified', 'refused', 'forked', 'proposals')
CROSS_LINKS = ('answers', 'anchored_to', 'serves', 'supersedes', 'witnesses', 'fulfils')
KEY_PROBLEMS = ('key_differs', 'xid_differs', 'person_differs', 'keeper_differs')   # directory.check's kinds
KEY_FLAGS = ('xid_mismatch', 'xid_shared')                                          # the fold's own flags

# The method's own thresholds, each sourced and overridable (thresholds={...}); none belongs to a holon.
THRESHOLDS = {
    'receipt_hours': 24,        # owed.RECEIPT_HOURS: the wait for a Receipt before a relationship has its own history
    'sigma_k': 3.0,             # emergency.SIGMA_K: Shewhart's three standard deviations
    'min_points': 8,            # emergency.MIN_POINTS: fewer receipted lines draw no limit
    'commitment': {             # a commitment's signal -> the check's reading
        'safe': 'inside',
        'inside its buffer': 'yellow',     # special cause: the buffer is being eaten
        'cannot keep': 'orange',           # the schedule says the by-date will pass
        'past its by-date': 'orange',      # the by-date has passed with no keeping
        'unwitnessed claim': 'yellow',     # read only once the claim has waited past the usual
    },
    'ear_late_cadences': 2,     # our ear is late once the last pull is older than this many cadences
    'window_s': 86400,          # "lines crossed in the last cadence" with no Agreement cadence to read: one day
}


def _thr(thresholds):
    t = copy.deepcopy(THRESHOLDS)
    if isinstance(thresholds, dict):
        for k, v in thresholds.items():
            if k == 'commitment' and isinstance(v, dict):
                t['commitment'].update({_s(a): _s(b) for a, b in v.items() if _s(b) in LEVELS})
            elif k in t and k != 'commitment' and _num(v) is not None and _num(v) > 0:
                t[k] = _num(v)
    return t


# ------------------------------------------------------------------------------------ small helpers

def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float('inf'), float('-inf')):
        return None
    return v


def _at(ts):
    """Seconds since the epoch for a time as written, or None."""
    t = parse_time(ts) if isinstance(ts, (str, dt.datetime, dt.date)) else None
    return t.timestamp() if t is not None else None


def _iso(t):
    return t.isoformat(timespec='seconds') if isinstance(t, dt.datetime) else None


def _short(x):
    x = _s(x)
    return x[:12] if len(x) == 64 and all(c in '0123456789abcdef' for c in x) else x


def _ids(v):
    if isinstance(v, str):
        return [v] if v else []
    if isinstance(v, (list, tuple)):
        return [x for x in v if isinstance(x, str) and x]
    return []


def _body(l):
    return l.get('body') if isinstance(l, dict) and isinstance(l.get('body'), dict) else {}


def _hours(sec):
    return round(sec / 3600.0, 2)


def _span_words(sec):
    sec = abs(sec or 0)
    if sec < 3600:
        return '%d min' % round(sec / 60.0)
    if sec < 172800:
        return '%d h' % round(sec / 3600.0)
    return '%d days' % round(sec / 86400.0)


def _worst(levels):
    best = 'inside'
    for x in levels:
        if x in LEVELS and LEVELS.index(x) > LEVELS.index(best):
            best = x
    return best


# ------------------------------------------------------------------------------------ the ground

class _Ground:
    """What every check reads, computed once: the trusted lines, the holons' persons, the Agreements,
    the stops, the Sightings' lifecycle, time to Receipt and each person's asks."""

    def __init__(self, items, lines, now, schedule=None, directory=None, thresholds=None):
        self.f = items if isinstance(items, dict) else {}
        self.t = now_or(now)
        self.now = self.t.timestamp()
        self.thr = _thr(thresholds)
        self.said = []
        trust = self.f.get('trust')
        self.trust = trust if isinstance(trust, dict) else None
        if self.trust is None:
            self.said.append('the fold\'s trust map was not given: lines are read as given, and no Condition is read')
        bad = set()
        for k in NOT_COUNTED:
            for x in self.f.get(k) or []:
                if isinstance(x, dict) and isinstance(x.get('id'), str):
                    bad.add(x['id'])
        self.bad = bad
        raw = [l for l in (lines if isinstance(lines, (list, tuple)) else []) if isinstance(l, dict)
               and isinstance(l.get('id'), str) and l.get('id')]
        uniq = {}
        for l in raw:
            uniq.setdefault(l['id'], l)
        self.all = [uniq[k] for k in sorted(uniq)]
        self.lines = [l for l in self.all if self.ok(l)]
        self.by_id = {l['id']: l for l in self.lines}
        adm = self.f.get('admitted')
        self.adm = adm if isinstance(adm, dict) else {}
        self.norm = normalize(self.f)
        self.rows = self._agreements()
        self._persons = {}
        self._sched = self._schedule_rows(schedule)
        self.directory = directory
        self._cache = {}

    # trust
    def ok(self, l):
        if l.get('reason') == 'untrusted' or l.get('id') in self.bad:
            return False
        return self.trust is None or self.trust.get(l.get('id')) in TRUSTED

    def signed_trust(self, l):
        return self.trust is not None and self.trust.get(l.get('id')) in TRUSTED and self.ok(l)

    # who belongs where
    def _agreements(self):
        if agreement_mod is None:
            self.said.append('agreement.py is not present: no Agreement is read')
            return []
        try:
            return agreement_mod.agreements(self.f, now=_iso(self.t))
        except Exception as e:  # noqa: BLE001
            self.said.append('agreement.py could not read the Agreements (%s)' % type(e).__name__)
            return []

    def keeper(self, h):
        room = self.adm.get(h) if isinstance(self.adm.get(h), dict) else {}
        for a in sorted(room):
            e = room[a]
            if isinstance(e, dict) and e.get('via') == 'inception' and actor_kind(a) == 'person':
                return _s(a)
        return ''

    def persons(self, h):
        """The persons who speak for holon h: its keeper, and whoever spoke for its side in an Agreement."""
        h = _s(h)
        if h in self._persons:
            return self._persons[h]
        out = set()
        if h:
            k = self.keeper(h)
            if k:
                out.add(k)
            for r in self.rows:
                if r.get('state') == 'retracted':
                    continue
                if r.get('agreed_with') == h and actor_kind(r.get('proposer')) == 'person':
                    out.add(r['proposer'])
                if r.get('with') == h and actor_kind(r.get('agreed_by')) == 'person':
                    out.add(r['agreed_by'])
        self._persons[h] = out
        return out

    def person_of(self, actor, for_=None):
        a, f = _s(actor), _s(for_)
        if actor_kind(a) == 'person':
            return a
        if actor_kind(a) == 'agent':
            if actor_kind(f) == 'person':
                return f
            ps = sorted({_s(room[a].get('person')) for room in self.adm.values()
                         if isinstance(room, dict) and isinstance(room.get(a), dict) and _s(room[a].get('person'))})
            return ps[0] if len(ps) == 1 else ''
        return ''

    def side(self, actor, for_, x, y):
        """x or y when the actor (an agent: its person) speaks for exactly one of them; else None."""
        p = self.person_of(actor, for_)
        if not p:
            return None
        inx, iny = p in self.persons(x), p in self.persons(y)
        return x if inx and not iny else y if iny and not inx else None

    def side_of_to(self, to, x, y):
        to = _s(to)
        if to in (x, y):
            return to
        if actor_kind(to):
            return self.side(to, None, x, y)
        return None

    def admitted_in(self, h, persons):
        room = self.adm.get(h) if isinstance(self.adm.get(h), dict) else {}
        return any(p in room for p in persons)

    def both_hold(self, h, x, y):
        return (h == x or self.admitted_in(h, self.persons(x))) and (h == y or self.admitted_in(h, self.persons(y)))

    # what crossed
    def crossed(self, l, x, y):
        """(from, to) when the line crossed between x and y: written by one side and placed in the other's
        holon, addressed to the other's people or to the other holon, or linked to a line of the other's."""
        if record is not None and record.is_inception(l):
            return None
        s = self.side(l.get('actor'), l.get('for'), x, y)
        if s is None:
            return None
        o = y if s == x else x
        if _s(l.get('holon')) == o:
            return s, o
        b = _body(l)
        tos = []
        if receipt_mod is not None:
            try:
                tos = receipt_mod.addressees(l)
            except Exception:  # noqa: BLE001
                tos = []
        tos = tos + _ids(b.get('to'))
        if any(self.side_of_to(t, x, y) == o for t in tos) or _s(b.get('with')) == o:
            return s, o
        lk = l.get('links') if isinstance(l.get('links'), dict) else {}
        for rel in CROSS_LINKS:
            for t in _ids(lk.get(rel)):
                tl = self.by_id.get(t)
                if tl is not None and self.side(tl.get('actor'), tl.get('for'), x, y) == o:
                    return s, o
        return None

    def between(self, x, y):
        key = ('between', x, y)
        if key not in self._cache:
            out = []
            for l in self.lines:
                c = self.crossed(l, x, y)
                if c:
                    out.append((l, c[0], c[1]))
            self._cache[key] = out
        return self._cache[key]

    # cached readers
    def waiting(self, person):
        key = ('waiting', person)
        if key not in self._cache:
            w = {}
            if owed_mod is not None:
                try:
                    w = owed_mod.waiting_on(self.f, self.all, person, now=_iso(self.t))
                except Exception as e:  # noqa: BLE001
                    self.said.append('owed.py could not read what %s waits on (%s)' % (person, type(e).__name__))
            self._cache[key] = w if isinstance(w, dict) else {}
        return self._cache[key]

    def ttr(self):
        if 'ttr' not in self._cache:
            r = {}
            if receipt_mod is not None:
                try:
                    r = receipt_mod.time_to_receipt(self.f, self.all)
                except Exception as e:  # noqa: BLE001
                    self.said.append('receipt.py could not measure time to Receipt (%s)' % type(e).__name__)
            self._cache['ttr'] = r if isinstance(r, dict) else {}
        return self._cache['ttr']

    def stops(self):
        if 'stops' not in self._cache:
            rows = []
            if stops_mod is not None:
                try:
                    rows = stops_mod.live(self.f)
                except Exception as e:  # noqa: BLE001
                    self.said.append('stops.py could not read the stops (%s)' % type(e).__name__)
            self._cache['stops'] = rows if isinstance(rows, list) else []
        return self._cache['stops']

    def life(self):
        if 'life' not in self._cache:
            lc = {}
            if sightings_mod is not None:
                try:
                    lc = sightings_mod.lifecycle(self.f, lines=self.all, now=_iso(self.t))
                except Exception as e:  # noqa: BLE001
                    self.said.append('sightings.py could not read the Sightings (%s)' % type(e).__name__)
            self._cache['life'] = lc if isinstance(lc, dict) else {}
        return self._cache['life']

    def _schedule_rows(self, schedule):
        rows = schedule.get('commitments') if isinstance(schedule, dict) else schedule
        out = {}
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict) and isinstance(r.get('commitment'), str):
                out.setdefault(r['commitment'], r)
        self.sched_given = isinstance(rows, list)
        return out

    def sched_row(self, cid):
        return self._sched.get(cid)

    def live_agreement(self, x, y):
        if agreement_mod is None:
            return None
        try:
            return agreement_mod.between(self.f, x, y, now=_iso(self.t))
        except Exception:  # noqa: BLE001
            return None


# ------------------------------------------------------------------------------------ the Condition

def _condition(g, holon):
    h = _s(holon)
    out = {'color': GREY, 'why': None, 'said': None, 'until': None, 'basis': 'not said', 'stale': False,
           'line': None, 'holon': h or None}
    if not h:
        out['basis'] = 'no holon named'
        return out
    if g.trust is None:
        out['basis'] = 'not said: the fold\'s trust map was not given, so no line can be read as the holon\'s own word'
        return out
    people = g.persons(h)
    if not people:
        out['basis'] = 'not said: no person who speaks for this holon is known here'
        return out
    mine = []
    for l in g.all:
        if l.get('type') != 'condition' or not g.signed_trust(l):
            continue
        a, f = _s(l.get('actor')), _s(l.get('for'))
        if actor_kind(a) != 'person' or a != f or a not in people:
            continue
        b = _body(l)
        of = _s(b.get('of'))
        if (of or _s(l.get('holon'))) != h:
            continue
        if _s(b.get('color')) not in COLORS:
            continue
        at = _at(l.get('ts'))
        mine.append((at if at is not None else float('-inf'), l['id'], l))
    if not mine:
        return out
    mine.sort(key=lambda x: (x[0], x[1]))
    l = mine[-1][2]
    b = _body(l)
    until = b.get('until') if isinstance(b.get('until'), str) else None
    out.update(color=_s(b['color']), why=_s(b.get('why')) or None, said=l.get('ts'), until=until, line=l['id'],
               basis='their own word')
    ut = parse_time(until) if until else None
    if until and ut is None:
        out['basis'] = 'their own word; its until is not a date, so it is read as having none'
    elif ut is not None and ut < g.t:
        out.update(color=GREY, stale=True,
                   basis='stale: their word was until %s, and it has passed; it reads grey until they say again' % until)
    return out


def condition_of(items, lines, holon, now=None):
    """The holon's own word on its Condition, or grey. Never computed, never inferred. Never raises."""
    try:
        return _condition(_Ground(items, lines, now), holon)
    except Exception as e:  # noqa: BLE001
        return {'color': GREY, 'why': None, 'said': None, 'until': None, 'stale': False, 'line': None,
                'holon': _s(holon) or None, 'basis': 'not read (%s)' % type(e).__name__}


# ------------------------------------------------------------------------------------ the pulse's checks
#
# Each check reads one direction: what holon `a` owes holon `b` (the column `a` -> `b`). The column
# a -> b holds: a's commitments to b and their signals; b's claims of delivery awaiting a's witness;
# b's asks of a and a's Receipt of them; a stop by b's person on a's agents; b's open pain; b's
# correction a has not received; a's lines crossing an ended Agreement; a key of a's in question.
# So the column b -> a is the same function with the sides swapped, and either holon reads the same.

def _check(name, level, reading, basis, why=None, since=None, rows=None):
    c = {'check': name, 'level': level, 'reading': reading, 'basis': basis, 'why': why}
    if since is not None:
        c['since'] = since
    if rows is not None:
        c['rows'] = rows
    return c


def _longest_cadence(row):
    cad = row.get('cadence') if isinstance(row, dict) else None
    vals = [v for v in (cad or {}).values() if _num(v) is not None and v > 0] if isinstance(cad, dict) else []
    return max(vals) if vals else None


def _pair_rows(g, x, y):
    return sorted((r for r in g.rows if set(r.get('sides') or []) == {x, y}), key=lambda r: r.get('id') or '')


def _agreement_of(g, x, y):
    """(row or None, reading, end instant or None): the live Agreement, else the newest that names both."""
    live = g.live_agreement(x, y)
    if live:
        return live, 'agreed', None
    rows = _pair_rows(g, x, y)
    if not rows:
        return None, 'none', None
    r = max(rows, key=lambda r: (_at(r.get('agreed_ts')) or float('-inf'), r.get('id') or ''))
    state = r.get('state') or 'proposed'
    end = None
    if state == 'expired':
        end = _at(r.get('until'))
    elif state == 'retracted':
        it = next((a for a in g.norm.get('agreement', []) if item_id(a) == r.get('id')), None)
        rl = g.by_id.get(_s(field(it, 'retracted_by')))
        end = _at(rl.get('ts')) if rl else None
    return r, state, end


def _check_agreement(g, x, y, a, b, ag):
    row, state, end = ag
    if state == 'agreed':
        return _check('agreement', 'inside', 'agreed', 'agreement %s stands' % _short(row['id']),
                      'agreed, until %s' % (row.get('until') or 'no end named'))
    if row is None:
        return _check('agreement', 'inside', 'none', 'no Agreement names both holons; the kit\'s default holds',
                      'no Agreement; the default holds')
    if end is None:
        why = 'Agreement %s is %s and grants nothing' % (_short(row['id']), state)
        return _check('agreement', 'inside', state, why, why)
    crosses = set(row.get('crosses') or []) or set(getattr(holon_mod, 'PUBLISHABLE', ()) or ())
    after = sorted((l for l, s, _o in g.between(x, y)
                    if s == a and l.get('type') in crosses and l.get('type') != 'agree'
                    and (_at(l.get('ts')) or float('-inf')) > end), key=lambda l: l['id'])
    basis = 'lines held by both, from %s, timed after the Agreement ended' % _short(a)
    if after:
        why = '%d line(s) from %s crossed after Agreement %s %s' % (
            len(after), _short(a), _short(row['id']), 'expired' if state == 'expired' else 'was retracted')
        return _check('agreement', 'red', state + ', lines still crossing', basis, why, rows=[l['id'] for l in after])
    why = 'Agreement %s %s, and nothing from %s has crossed since' % (_short(row['id']), state, _short(a))
    return _check('agreement', 'inside', state, basis, why)


def _usual(g, x, y):
    """The relationship's own usual time to Receipt in hours, both ways together, and its basis."""
    hist = []
    for row in (g.ttr().get('rows') or []):
        if not isinstance(row, dict) or row.get('hours') is None:
            continue
        l = g.by_id.get(row.get('line'))
        if l is None:
            continue
        s = g.side(l.get('actor'), l.get('for'), x, y)
        to = g.side_of_to(row.get('to'), x, y)
        if s and to and s != to and _num(row.get('hours')) is not None:
            hist.append(row['hours'])
    hist.sort()
    lim = None
    if emergency_mod is not None and hist:
        try:
            lim = emergency_mod.limits_from_history(hist, k=g.thr['sigma_k'], min_points=int(g.thr['min_points']))
        except Exception:  # noqa: BLE001
            lim = None
    if isinstance(lim, dict) and lim.get('basis') == 'measured' and _num(lim.get('upper')) is not None:
        return max(0.0, float(lim['upper'])), ('measured: the upper control limit of %d Receipts between them'
                                               % len(hist))
    return float(g.thr['receipt_hours']), ('the kit\'s default wait of %s h: %d Receipt(s) between them, too few '
                                           'for limits' % (g.thr['receipt_hours'], len(hist)))


def _check_receipts(g, x, y, a, b, usual_h, usual_basis):
    """b's asks of a, and whether a's side has given its Receipt within the usual."""
    rows, seen, since, whys = [], set(), None, []
    for p in sorted(g.persons(b)):
        if g.side(p, p, x, y) != b:
            continue
        for ask in g.waiting(p).get('asks') or []:
            if not isinstance(ask, dict):
                continue
            for rc in ask.get('recipients') or []:
                if not isinstance(rc, dict) or g.side_of_to(rc.get('to'), x, y) != a:
                    continue
                key = (str(ask.get('id')), _s(rc.get('to')))
                if key in seen or rc.get('state') != 'no_receipt':
                    continue
                seen.add(key)
                at = _at(ask.get('ts'))
                age = (g.now - at) if at is not None else None
                past = age is not None and age > usual_h * 3600
                rows.append({'ask': ask.get('id'), 'from': b, 'to': a, 'kind': ask.get('kind'),
                             'age_hours': _hours(age) if age is not None else None, 'past_usual': past})
                if past:
                    st_at = at + usual_h * 3600
                    since = st_at if since is None else min(since, st_at)
                    whys.append('no Receipt from %s for %s after %s, past the usual %s h'
                                % (_short(a), _short(ask.get('id')), _span_words(age), round(usual_h, 2)))
    rows.sort(key=lambda r: (str(r['ask']), r['to']))
    n_past = sum(1 for r in rows if r['past_usual'])
    reading = ('%d ask(s) from %s waiting on a Receipt, %d past the usual' % (len(rows), _short(b), n_past)
               if rows else 'every ask from %s has its Receipt' % _short(b))
    c = _check('receipts', 'yellow' if n_past else 'inside', reading, usual_basis, '; '.join(whys) or None,
               since=since, rows=rows)
    c['usual_hours'] = round(usual_h, 3)
    return c


def _commitments(g, x, y):
    """[(item, committor side, committee side)] for every commitment between the two, by id."""
    out = []
    for c in sorted(g.norm.get('commitment', []), key=item_id):
        if not isinstance(c, dict) or str(field(c, 'reason') or '') == 'untrusted':
            continue
        committor = _s(field(c, 'for')) or _s(field(c, 'actor'))
        committee = field(c, 'committee')
        committee = _s(committee) if isinstance(committee, str) else ''
        s = g.side(committor, committor, x, y)
        o = g.side(committee, None, x, y) if committee else None
        if s and o and s != o:
            out.append((c, s, o))
    return out


def _check_commitments(g, x, y, a, b, usual_h):
    rows, whys, level, since = [], [], 'inside', None
    cmap = g.thr['commitment']
    for c, s, o in _commitments(g, x, y):
        status, _gap = commitment_status(c, g.t)
        signal, sig_at = None, None
        if status == 'kept-unwitnessed':
            if s != b:                     # a claim of ours waits on their witness: their column, not ours
                continue
            k_at = _at(field(c, 'kept_ts') or field(c, 'kept_at') or field(c, 'done_ts'))
            if k_at is not None and g.now - k_at > usual_h * 3600:
                signal, sig_at = 'unwitnessed claim', k_at + usual_h * 3600
            else:
                signal = 'claimed, its witness not yet past the usual'
        elif s != a:
            continue
        elif status == 'broken':
            signal, sig_at = 'past its by-date', _at(field(c, 'by'))
        elif status == 'open':
            r = g.sched_row(item_id(c))
            signal = r.get('signal') if isinstance(r, dict) else None
            if signal is None:
                signal = 'not compared' + ('' if g.sched_given else ': no schedule was given')
        else:
            signal = status
        lv = cmap.get(signal, 'inside')
        rows.append({'commitment': item_id(c), 'from': s, 'to': o, 'by': field(c, 'by'), 'status': status,
                     'signal': signal, 'level': lv})
        if lv != 'inside':
            whys.append('commitment %s: %s' % (_short(item_id(c)), signal))
            level = _worst([level, lv])
            if lv == 'yellow' and sig_at is not None:
                since = sig_at if since is None else min(since, sig_at)
    reading = ('%d commitment(s) %s keeps toward %s' % (len(rows), _short(a), _short(b))) if rows \
        else 'no commitment from %s to %s' % (_short(a), _short(b))
    basis = ('each commitment\'s status from the fold and its signal from the schedule; a claim of delivery '
             'waits on the committee\'s witness')
    return _check('commitments', level, reading, basis, '; '.join(whys) or None, since=since, rows=rows)


def _check_stops(g, x, y, a, b):
    """A live stop by b's person on a's agents."""
    rows, whys = [], []
    for r in g.stops():
        if not isinstance(r, dict):
            continue
        by = _s(r.get('by'))
        if g.side(by, by, x, y) != b:
            continue
        agents = [ag for ag in (r.get('agents') or []) if isinstance(ag, str)]
        ours = [ag for ag in agents if g.side(ag, None, x, y) == a]
        if agents and not ours:
            continue
        rows.append({'stop': r.get('id'), 'by': by, 'on': ours or 'every agent', 'scope': r.get('scope')})
        whys.append('a live stop by their person on %s (stop %s)' % (
            ('our agent' if len(ours) == 1 else 'our %d agents' % len(ours)) if ours else 'every agent',
            _short(r.get('id'))))
    rows.sort(key=lambda r: str(r['stop']))
    basis = 'stops.live over the fold; only the stopped agent\'s own person lifts a stop'
    if rows:
        return _check('stops', 'red', '%d live stop(s) on %s\'s agents' % (len(rows), _short(a)), basis,
                      '; '.join(whys), rows=rows)
    return _check('stops', 'inside', 'no live stop from %s on %s\'s agents' % (_short(b), _short(a)), basis)


AGENT_VOICES = ('agent', 'agent-drafted')       # a Sighting in these voices is a proposal for its person
STAND_ON = ('claim', 'sight')                     # the person's own lines that put their weight on it: accept, re-sight
RESIGHT_RELS = ('answers', 'anchored_to', 'witnesses', 'serves', 'supersedes', 'predecessor')   # sightings.RESIGHT_RELS + answers


def _role(g, actor, a, x, y):
    """The role word for an actor, from column a's side: our person, their agent, ...; never the actor id."""
    kind = actor_kind(_s(actor)) or 'actor'
    side = g.side(actor, None, x, y)
    return ('our %s' if side == a else 'their %s' if side else 'a %s') % kind


def _stood_on(g, it, sid):
    """Whether the person an agent-voiced Sighting answers for has stood on it with their own trusted line:
    their `claim` of it (accept), or their own `sight` linking to it (a re-sighting). Nothing else counts:
    a say, a thread note, an answer or a settle on it is not their weight on it (a settle closes it anyway,
    and a retraction ends it)."""
    person = _s(field(it, 'for'))
    if actor_kind(person) != 'person':
        return False
    for l in g.lines:
        if _s(l.get('actor')) != person or l.get('id') == sid:
            continue
        typ = l.get('type')
        if typ not in STAND_ON:
            continue
        b = _body(l)
        lk = l.get('links') if isinstance(l.get('links'), dict) else {}
        if typ == 'claim':
            named = sid in _ids(b.get('card'))
            linked = sid in _ids(lk.get('answers'))
        else:
            named = sid in _ids(b.get('re'))
            linked = any(sid in _ids(lk.get(rel)) for rel in RESIGHT_RELS)
        if named or linked:
            return True
    return False


def _check_pain(g, x, y, a, b):
    """b's open pain, placed in a holon both hold or elevated to either: b asks for help."""
    lc = g.life()
    ended = getattr(sightings_mod, 'ENDED', ('fixed', 'closed', 'retracted'))
    elevated = set()
    for l in g.lines:
        if l.get('type') == 'elevate' and _s(_body(l).get('to')) in (x, y) and _s(_body(l).get('what')):
            elevated.add(_s(_body(l).get('what')))
    rows, whys, waiting = [], [], []
    for it in sorted(g.norm.get('sighting', []), key=item_id):
        sid = item_id(it)
        kind = _s(field(it, 'body_kind')) or _s((lc.get(sid) or {}).get('kind'))
        if kind != 'pain':
            continue
        state = (lc.get(sid) or {}).get('state') or _s(field(it, 'state')) or 'seen'
        if state in ended or g.side(field(it, 'actor'), field(it, 'for'), x, y) != b:
            continue
        if not (g.both_hold(holon_of(it), x, y) or sid in elevated):
            continue
        voice = _s(field(it, 'voice')) or ('agent' if actor_kind(_s(field(it, 'actor'))) == 'agent' else 'human-words')
        if voice in AGENT_VOICES and not _stood_on(g, it, sid):
            waiting.append(sid)
            continue
        rows.append({'sighting': sid, 'from': b, 'holon': holon_of(it), 'state': state, 'voice': voice})
        whys.append('an open pain from %s (%s, %s)' % (_short(b), _short(sid), state))
    basis = ('%s\'s pain Sightings in a holon both hold, or elevated to either, not fixed, closed or retracted; '
             'an agent\'s Sighting counts once its person stands on it' % _short(b))
    if waiting:
        basis += '; %d agent Sighting(s) wait on their person and count for nothing yet' % len(waiting)
    if rows:
        return _check('pain', 'red', '%d open pain(s) from %s' % (len(rows), _short(b)), basis, '; '.join(whys),
                      rows=rows)
    return _check('pain', 'inside', 'no open pain from %s' % _short(b), basis)


def _check_corrections(g, x, y, a, b):
    """b's correction of a line that crossed, and whether a's side holds a Receipt of it."""
    crossed = {l['id'] for l, _s1, _o in g.between(x, y)}
    rows, whys, since = [], [], None
    for l in g.lines:
        if l.get('type') != 'correct' or g.side(l.get('actor'), l.get('for'), x, y) != b:
            continue
        lk = l.get('links') if isinstance(l.get('links'), dict) else {}
        if not any(t in crossed for t in _ids(lk.get('supersedes')) + _ids(_body(l).get('line'))):
            continue
        seen = False
        for r in g.lines:
            if r.get('type') != 'receive' or g.side(r.get('actor'), r.get('for'), x, y) != a:
                continue
            rl = r.get('links') if isinstance(r.get('links'), dict) else {}
            if l['id'] in _ids(_body(r).get('of')) + _ids(rl.get('answers')):
                seen = True
                break
        rows.append({'correction': l['id'], 'from': b, 'to': a, 'seen': seen})
        if not seen:
            at = _at(l.get('ts'))
            if at is not None:
                since = at if since is None else min(since, at)
            whys.append('correction %s from %s not yet received by %s' % (_short(l['id']), _short(b), _short(a)))
    rows.sort(key=lambda r: r['correction'])
    basis = 'a correction of a line that crossed, and whether the receiving side holds a Receipt of it'
    reading = ('%d correction(s) from %s, %d not yet seen' % (len(rows), _short(b), len(whys))) if rows \
        else 'no correction from %s of a crossed line' % _short(b)
    return _check('corrections', 'yellow' if whys else 'inside', reading, basis, '; '.join(whys) or None,
                  since=since, rows=rows)


def _check_keys(g, x, y, a, b):
    """A key of a's side in question: the fold's XID flags, and the directory where one is given."""
    rows, whys = [], []
    people = g.persons(a)

    def ours(actor):
        actor = _s(actor)
        return bool(actor) and (actor in people or g.person_of(actor) in people)

    for fl in g.f.get('flags') or []:
        if not isinstance(fl, dict) or fl.get('flag') not in KEY_FLAGS:
            continue
        who = _s(fl.get('actor'))
        if not who:
            l = g.by_id.get(_s(fl.get('id'))) or {}
            bd = _body(l)
            who = _s(bd.get('who')) or _s(bd.get('agent')) or _s(l.get('actor'))
        if ours(who):
            rows.append({'flag': fl['flag'], 'actor': who, 'line': fl.get('id'), 'from': 'the fold'})
            whys.append('%s for %s' % (fl['flag'], _role(g, who, a, x, y)))
    basis = 'the fold\'s XID flags'
    if g.directory is not None:
        d = _opt('directory')
        if d is None:
            basis += '; directory.py is not present, so the directory is not checked'
            probs = []
        else:
            try:
                probs = d.check(g.directory, g.f)
                basis += '; directory.check against the record'
            except Exception as e:  # noqa: BLE001
                probs = []
                basis += '; the directory could not be checked (%s)' % type(e).__name__
        for p in probs if isinstance(probs, list) else []:
            if not isinstance(p, dict) or p.get('kind') not in KEY_PROBLEMS:
                continue
            pid, ph = _s(p.get('id')), _s(p.get('holon'))
            mine = ours(pid) if actor_kind(pid) else (
                ph == a or pid == a if p['kind'] == 'keeper_differs' else (pid == a and not ph))
            if mine:
                rows.append({'flag': p['kind'], 'actor': pid, 'line': None, 'from': 'the directory'})
                whys.append('%s for %s' % (p['kind'], _role(g, pid, a, x, y) if actor_kind(pid) else 'our holon'))
    else:
        basis += '; no directory was given, so none is checked'
    rows.sort(key=lambda r: (r['flag'], r['actor'], str(r.get('line') or '')))
    if rows:
        return _check('keys', 'red', '%d key disagreement(s) for %s' % (len(rows), _short(a)), basis,
                      '; '.join(sorted(set(whys))), rows=rows)
    return _check('keys', 'inside', 'no key disagreement for %s' % _short(a), basis)


def _direction(g, x, y, a, b, ag, cadence, usual_h, usual_basis):
    """The column a -> b: whether `a` keeps what it owes `b`, with its color, why and checks."""
    checks = [_check_agreement(g, x, y, a, b, ag), _check_commitments(g, x, y, a, b, usual_h),
              _check_receipts(g, x, y, a, b, usual_h, usual_basis), _check_stops(g, x, y, a, b),
              _check_pain(g, x, y, a, b), _check_corrections(g, x, y, a, b), _check_keys(g, x, y, a, b)]
    for c in checks:                              # a yellow that has stood longer than the Agreement's cadence
        s = c.pop('since', None)
        if c['level'] == 'yellow' and s is not None and cadence:
            stood = g.now - s
            if stood > cadence:
                c['level'] = 'orange'
                c['why'] = (c['why'] or '') + '; yellow for %s, longer than the Agreement\'s cadence of %s' % (
                    _span_words(stood), _span_words(cadence))
        if s is not None:
            c['yellow_since'] = _iso(dt.datetime.fromtimestamp(s, tz=g.t.tzinfo))
    worst = _worst(c['level'] for c in checks)
    why = ['%s: %s' % (c['check'], c['why']) for c in checks if c['level'] != 'inside' and c['why']] \
        or ['every check is inside: %s' % ', '.join(CHECKS)]
    return {'from': a, 'to': b, 'color': LEVEL_COLOR[worst], 'why': why, 'checks': checks}


def _pulse(g, a, b):
    a, b = _s(a), _s(b)
    out = {'color': None, 'why': [], 'us_to_them': None, 'them_to_us': None, 'between': sorted([a, b]),
           'word': PULSE_WORD, 'as_of': _iso(g.t)}
    if not a or not b or a == b:
        out['why'] = ['the %s is between two holons, and two were not named' % PULSE_WORD]
        return out
    x, y = sorted([a, b])
    ag = _agreement_of(g, x, y)
    cadence = _longest_cadence(ag[0]) if ag[0] else None
    usual_h, usual_basis = _usual(g, x, y)
    us = _direction(g, x, y, a, b, ag, cadence, usual_h, usual_basis)
    them = _direction(g, x, y, b, a, ag, cadence, usual_h, usual_basis)
    out['us_to_them'], out['them_to_us'] = us, them
    out['color'] = LEVEL_COLOR[_worst([k for k, v in LEVEL_COLOR.items() if v in (us['color'], them['color'])])]
    out['why'] = ['us to them: %s' % w for w in us['why'] if not w.startswith('every check')] + \
        ['them to us: %s' % w for w in them['why'] if not w.startswith('every check')] or \
        ['every check is inside, both ways']
    out['cadence_s'] = cadence
    out['usual_receipt_hours'] = round(usual_h, 3)
    out['agreement'] = {'id': ag[0].get('id') if ag[0] else None, 'state': ag[1]}
    return out


def pulse(items, lines, a, b, now=None, schedule=None, directory=None, thresholds=None):
    """The measure between holons `a` (us) and `b` (them), from the lines given: two directed columns,
    `us_to_them` and `them_to_us`, each its own color and why, and `color` the worse of the two.
    Law: pulse(.., a, b)['us_to_them'] equals pulse(.., b, a)['them_to_us'], field for field. Never raises."""
    try:
        g = _Ground(items, lines, now, schedule, directory, thresholds)
        return _pulse(g, a, b)
    except Exception as e:  # noqa: BLE001
        return {'color': None, 'why': ['not computed (%s)' % type(e).__name__], 'us_to_them': None,
                'them_to_us': None, 'between': sorted([_s(a), _s(b)]), 'word': PULSE_WORD, 'as_of': None}


# ------------------------------------------------------------------------------------ our ear

def _ear_state(home_dir, now_iso):
    """({cell id: pull row}, {cell names that failed}, said)."""
    said = []
    cells, failed = {}, set()
    if pull_mod is None:
        return cells, failed, ['pull.py is not present: our ear is not read']
    try:
        d = pull_mod.due(home_dir, now_iso)
    except Exception as e:  # noqa: BLE001
        return cells, failed, ['pull.py could not say what is due (%s)' % type(e).__name__]
    for c in d.get('cells') or []:
        cid = _s((c.get('_c') or {}).get('id')) if isinstance(c.get('_c'), dict) else ''
        if cid:
            cells[cid] = {'cell': c.get('cell'), 'cadence': c.get('cadence'), 'pulled_at': c.get('pulled_at'),
                          'basis': c.get('basis')}
    path = os.path.join(home_dir, '.heartbeat.json')
    if os.path.islink(path):
        said.append('the heartbeat\'s state is a link, so no failed pull is read')
    elif os.path.isfile(path):
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, encoding='utf-8') as fh:
                st = json.load(fh)
            for f in (st.get('faults') if isinstance(st, dict) and isinstance(st.get('faults'), list) else []):
                if isinstance(f, str) and f.startswith('fault:pull:'):
                    failed.add(f[len('fault:pull:'):])
        except (OSError, ValueError):
            said.append('the heartbeat\'s state could not be read, so no failed pull is read')
    return cells, failed, said


def _ear(g, holon, x_side_lines, ear_cells, failed):
    """Our one-sided hearing of a holon: the cell that carries its lines, and our last pull of it."""
    carriers = []
    if holon in ear_cells:
        carriers = [holon]
    else:
        carriers = sorted({_s(l.get('_held_in')) for l in x_side_lines if _s(l.get('_held_in')) in ear_cells})
    if not carriers:
        return {'heard': 'never', 'via': None, 'pulled_at': None, 'cadence_s': None, 'age_s': None,
                'basis': 'no joined cell here carries its lines, so we have not pulled it'}
    best = None
    for cid in carriers:
        c = ear_cells[cid]
        cad = _num(c.get('cadence'))
        at = _at(c.get('pulled_at'))
        age = (g.now - at) if at is not None else None
        if c.get('cell') in failed:
            heard, basis = 'failed', 'the heartbeat\'s last pull of this cell failed'
        elif at is None:
            heard, basis = 'never', 'this cell has not been pulled yet'
        elif cad and age > g.thr['ear_late_cadences'] * cad:
            heard, basis = 'late', 'the last pull is older than %s cadences of %s' % (g.thr['ear_late_cadences'],
                                                                                    _span_words(cad))
        else:
            heard, basis = 'ok', 'pulled within its cadence'
        row = {'heard': heard, 'via': c.get('cell'), 'pulled_at': c.get('pulled_at'), 'cadence_s': cad,
               'age_s': int(age) if age is not None else None, 'basis': basis}
        if best is None or (HEARD.index(heard), str(row['via'])) < (HEARD.index(best['heard']), str(best['via'])):
            best = row
    return best


# ------------------------------------------------------------------------------------ the view

def _empty(said, t=None):
    return {'rows': [], 'summary': {'holons': 0, 'green': 0, 'yellow': 0, 'orange': 0, 'red': 0,
                                    'grey_condition': 0, 'all_live': True, 'commitments_yellow_or_better': True,
                                    'ours_yellow_or_better': True, 'not_live': [], 'not_yellow_or_better': [],
                                    'ours_not_yellow_or_better': []},
            'as_of': _iso(t) if t else None, 'said': [said] if isinstance(said, str) else list(said or [])}


def _read_home(home_dir):
    r = record.read_all(home_dir)
    tp = os.path.join(home_dir, 'types.json')
    types = record.load_types(tp if os.path.isfile(tp) and not os.path.islink(tp) else None)
    cache = getattr(record, 'signature_cache', None)
    if cache is not None:
        with cache(home_dir):
            f = record.fold(r['lines'], types, r.get('keepers') or {})
    else:
        f = record.fold(r['lines'], types, r.get('keepers') or {})
    return r['lines'], f


def _counterpart(g, home, actor, line_holon):
    """The holon an actor speaks for, other than the home: the one it is known to speak for, else the
    holon the line lives in."""
    p = g.person_of(actor)
    if not p:
        return None
    known = sorted(h for h in _known_holons(g) if h != home and p in g.persons(h))
    if len(known) == 1:
        return known[0]
    if not known and line_holon and line_holon != home and p not in g.persons(home):
        return line_holon
    return None


def _known_holons(g):
    hs = set(h for h in g.adm if isinstance(h, str) and h)
    for r in g.rows:
        hs.update(x for x in (r.get('sides') or []) if isinstance(x, str) and x)
    return hs


def _connected(g, home):
    out, why = set(), {}
    people = g.persons(home)
    for r in g.rows:
        sides = [x for x in r.get('sides') or [] if isinstance(x, str)]
        if home in sides:
            for o in sides:
                if o != home:
                    out.add(o)
                    why.setdefault(o, 'an Agreement')
    for h in sorted(g.adm):
        if h != home and isinstance(h, str) and g.admitted_in(h, people):
            out.add(h)
            why.setdefault(h, 'a cell both hold')
    for c in g.norm.get('commitment', []):
        a, b = _s(field(c, 'for')) or _s(field(c, 'actor')), field(c, 'committee')
        b = _s(b) if isinstance(b, str) else ''
        if not b:
            continue
        for mine, other in ((a, b), (b, a)):
            if g.person_of(mine) in people:
                o = _counterpart(g, home, other, holon_of(c))
                if o:
                    out.add(o)
                    why.setdefault(o, 'a commitment')
    for p in sorted(people):
        for ask in g.waiting(p).get('asks') or []:
            for rc in (ask.get('recipients') or []) if isinstance(ask, dict) else []:
                to = _s(rc.get('to')) if isinstance(rc, dict) else ''
                o = to if (to and not actor_kind(to) and to != home) else _counterpart(g, home, to, _s(ask.get('holon')))
                if o:
                    out.add(o)
                    why.setdefault(o, 'an ask')
    if receipt_mod is not None:
        for l in g.lines:
            try:
                tos = receipt_mod.addressees(l)
            except Exception:  # noqa: BLE001
                tos = []
            if any(g.person_of(t) in people for t in tos) and g.person_of(l.get('actor'), l.get('for')) not in people:
                o = _counterpart(g, home, l.get('actor') if actor_kind(_s(l.get('actor'))) == 'person'
                                 else l.get('for'), _s(l.get('holon')))
                if o:
                    out.add(o)
                    why.setdefault(o, 'an ask')
    return sorted(out), why


def _cadence_words(row):
    cad = row.get('cadence') if isinstance(row, dict) else None
    if not isinstance(cad, dict) or not cad:
        return 'no cadence named'
    words = getattr(agreement_mod, 'cadence_words', None)
    parts = []
    for k in sorted(cad):
        w = words(cad[k]) if callable(words) else 'every %s s' % cad[k]
        parts.append(('%s %s' % ('every signal' if k == '*' else k, w)))
    return '; '.join(parts)


def _sent_heard_by(g, home, X):
    """(sent, heard_by_at): how many lines of ours asked something of them or were receipted by them, and the
    time of their newest Receipt on a line of ours, both read from time to Receipt (receipt.time_to_receipt).
    (None, None) when receipt.py is not beside this file: then nothing is known, and nothing is claimed."""
    if receipt_mod is None:
        return None, None
    x, y = sorted([home, X])
    sent, newest = set(), None
    for r in (g.ttr().get('rows') or []):
        if not isinstance(r, dict):
            continue
        l = g.by_id.get(r.get('line'))
        if l is None or g.side(l.get('actor'), l.get('for'), x, y) != home or g.side_of_to(r.get('to'), x, y) != X:
            continue
        sent.add(l['id'])
        at = _at(r.get('receipt_ts'))
        if r.get('receipt') is not None and at is not None and (newest is None or (at, str(r.get('receipt'))) > newest[:2]):
            newest = (at, str(r.get('receipt')), r.get('receipt_ts'))
    return len(sent), (newest[2] if newest else None)


def _row(g, home, X, names, ear_cells, failed, why_connected):
    p = _pulse(g, home, X)
    cond = _condition(g, X)
    x, y = sorted([home, X])
    btw = g.between(x, y)
    window = p.get('cadence_s') or g.thr['window_s']
    lo = g.now - window
    crossed = sum(1 for l, _a, _b in btw if (_at(l.get('ts')) or float('-inf')) >= lo)
    given = sum(1 for _c, s1, _o in _commitments(g, x, y) if s1 == home)
    received = sum(1 for _c, s1, _o in _commitments(g, x, y) if s1 == X)
    # asks waiting each way, counted from what each side's persons started
    out_wait = in_wait = 0
    for person in sorted(g.persons(x) | g.persons(y)):
        s = g.side(person, person, x, y)
        if s is None:
            continue
        o = y if s == x else x
        for ask in g.waiting(person).get('asks') or []:
            for r in (ask.get('recipients') or []) if isinstance(ask, dict) else []:
                if isinstance(r, dict) and r.get('state') != 'answered' and g.side_of_to(r.get('to'), x, y) == o:
                    if s == home:
                        out_wait += 1
                    else:
                        in_wait += 1
    first = min(btw, key=lambda t: ((_at(t[0].get('ts')) if _at(t[0].get('ts')) is not None else float('inf')),
                                    t[0]['id']), default=None)
    ag_row = g.live_agreement(home, X) or (max(_pair_rows(g, x, y), key=lambda r: (
        _at(r.get('agreed_ts')) or float('-inf'), r.get('id') or '')) if _pair_rows(g, x, y) else None)
    x_lines = [l for l in g.lines if g.side(l.get('actor'), l.get('for'), x, y) == X]
    sent, heard_by_at = _sent_heard_by(g, home, X)
    return {
        'holon': X, 'name': names.get(X), 'connected_by': why_connected.get(X),
        'condition': cond,
        PULSE_WORD: p,
        'ear': _ear(g, X, x_lines, ear_cells, failed),
        'with_us': {'commitments_given': given, 'commitments_received': received,
                    'asks_waiting_on_them': out_wait, 'asks_waiting_on_us': in_wait,
                    'lines_crossed': crossed, 'window_s': int(window),
                    'usual_receipt_hours': p.get('usual_receipt_hours')},
        'agreement': ({'id': ag_row.get('id'), 'state': ag_row.get('state'), 'live': bool(ag_row.get('live')),
                       'until': ag_row.get('until'), 'cadence': _cadence_words(ag_row)} if ag_row else
                      {'id': None, 'state': 'none', 'live': False, 'until': None, 'cadence': 'no Agreement'}),
        'since': first[0].get('ts') if first else None,
        'sent': sent, 'heard_by_at': heard_by_at,
    }


def _summary(rows):
    """Counts by overall color; whether every connection is live; and, for the holons we exchanged
    commitments with, whether their column toward us (`commitments_yellow_or_better`) and ours toward
    them (`ours_yellow_or_better`) read yellow or better."""
    s = {'holons': len(rows), 'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey_condition': 0}
    not_live, theirs, ours = [], [], []
    ok = ('green', 'yellow')
    for r in rows:
        p = r[PULSE_WORD]
        if p.get('color') in s:
            s[p['color']] += 1
        if r['condition'].get('color') == GREY:
            s['grey_condition'] += 1
        if p.get('color') not in ok or r['ear'].get('heard') != 'ok':
            not_live.append(r['holon'])
        w = r['with_us']
        if w['commitments_given'] or w['commitments_received']:
            if (p.get('them_to_us') or {}).get('color') not in ok:
                theirs.append(r['holon'])
            if (p.get('us_to_them') or {}).get('color') not in ok:
                ours.append(r['holon'])
    s.update(all_live=not not_live, commitments_yellow_or_better=not theirs, ours_yellow_or_better=not ours,
             not_live=not_live, not_yellow_or_better=theirs, ours_not_yellow_or_better=ours)
    return s


def connections(home_dir, now=None, lines=None, folded=None, schedule=None, directory=None, thresholds=None):
    """Every holon this home is connected to, its Condition, the pulse between, our ear and what is with us.
    Pure apart from reading the home. Honest-empty; never raises."""
    t = now_or(now)
    try:
        if record is None:
            return _empty('record.py is not beside this file; nothing is read', t)
        if not isinstance(home_dir, str) or not home_dir or not os.path.isdir(home_dir):
            return _empty('there is no home folder here, so no connection is read', t)
        if os.path.islink(home_dir.rstrip(os.sep) or home_dir):
            return _empty('the home folder is a link, so it is not read', t)
        info = record.holon_info(home_dir)
        home = _s(info.get('id'))
        if lines is None or not isinstance(folded, dict):
            lines, folded = _read_home(home_dir)
        home = home or _s((folded.get('holons') or [{}])[0].get('id') if isinstance(folded.get('holons'), list)
                          and folded.get('holons') and isinstance(folded['holons'][0], dict) else '')
        if not home:
            return _empty('the home has no id its record proves, so no connection is read', t)
        g = _Ground(folded, lines, t, schedule, directory, thresholds)
        names = {}
        for d in record.hold(home_dir):
            i = record.holon_info(d)
            if _s(i.get('id')):
                names[_s(i['id'])] = _s(i.get('name')) or None
        ear_cells, failed, ear_said = _ear_state(home_dir, _iso(t))
        ids, why = _connected(g, home)
        rows = [_row(g, home, X, names, ear_cells, failed, why) for X in ids]
        said = list(g.said) + ear_said
        if not rows:
            said.append('this home is connected to no other holon yet')
        return {'rows': rows, 'summary': _summary(rows), 'as_of': _iso(t), 'home': home,
                'said': sorted(set(said))}
    except Exception as e:  # noqa: BLE001
        return _empty('the connections could not be read (%s)' % type(e).__name__, t)


# ------------------------------------------------------------------------------------ changes

def _read_state(home_dir):
    path = os.path.join(home_dir, STATE_NAME)
    if os.path.islink(path):
        return None, 'the kept state is a link, so it is not read'
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return None, 'no state is kept yet'
    except OSError as e:
        return None, 'the kept state cannot be opened (%s)' % type(e).__name__
    try:
        with os.fdopen(fd, encoding='utf-8') as fh:
            v = json.load(fh)
        return (v, '') if isinstance(v, dict) else (None, 'the kept state is not a map, so it is not read')
    except (OSError, ValueError):
        return None, 'the kept state is not readable JSON, so it is not read'


def write_state(home_dir, state):
    """Write <home>/.connections.json whole or not at all, never through a link. Returns the path, or a sentence."""
    if not isinstance(home_dir, str) or not os.path.isdir(home_dir) or not isinstance(state, dict):
        return 'nothing was written: no home folder, or no state to keep'
    path = os.path.join(home_dir, STATE_NAME)
    tmp = path + '.tmp'
    if os.path.islink(path) or os.path.islink(tmp):
        return 'nothing was written: the state file is a link'
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
        os.replace(tmp, path)
    except OSError as e:
        return 'nothing was written (%s)' % type(e).__name__
    return path


DIRECTIONS = ('us_to_them', 'them_to_us')
KEPT_COLORS = COLORS + (GREY,)               # what a kept state may hold; anything else is not read
WHATS = ('condition',) + DIRECTIONS          # what a change names: the Condition, or one column of the pulse


def _state_of(res):
    hs = {}
    for r in res.get('rows') or []:
        p = r.get(PULSE_WORD) or {}
        hs[r['holon']] = {'condition': r['condition'].get('color'), 'condition_line': r['condition'].get('line'),
                          PULSE_WORD: p.get('color'),
                          'us_to_them': (p.get('us_to_them') or {}).get('color'),
                          'them_to_us': (p.get('them_to_us') or {}).get('color')}
    return {'v': 1, 'as_of': res.get('as_of'), 'home': res.get('home'), 'holons': hs}


def _person_rule(lines, folded, person):
    if emergency_mod is None:
        return None
    trust = folded.get('trust') if isinstance(folded, dict) and isinstance(folded.get('trust'), dict) else {}
    mine = [l for l in (lines or []) if isinstance(l, dict) and l.get('type') == 'limits' and trust.get(l.get('id')) in TRUSTED]
    try:
        return emergency_mod.rule(mine, person)
    except Exception:  # noqa: BLE001
        return None


def _home_agent(g, home, person):
    """The agent the home's person let into the home, when exactly one is; else ''."""
    room = g.adm.get(home) if isinstance(g.adm.get(home), dict) else {}
    agents = sorted(a for a, e in room.items() if actor_kind(a) == 'agent' and isinstance(e, dict)
                    and _s(e.get('person')) == person and not e.get('ended') and e.get('via') == 'affirm')
    return agents[0] if len(agents) == 1 else ''


def _draft(agent, person, home, X, name, what, frm, to, why, at, anchor):
    """An unsigned, agent-voiced `sight` line for the person's word: a proposal, never signed here."""
    label = name or _short(X)
    whose = {'condition': 'its Condition', 'us_to_them': 'our side of the %s' % PULSE_WORD,
             'them_to_us': 'their side of the %s' % PULSE_WORD}[what]
    text = 'The connection with %s: %s moved from %s to %s. %s' % (
        label, whose, frm or 'nothing said', to or 'nothing said', why)
    body = {'text': ' '.join(text.split())[:280], 'kind': SIGHT_KIND, 'where': 'the connection with %s' % label,
            'voice': 'agent'}
    lk = {'anchored_to': [anchor]} if anchor else None
    actor = agent or person
    try:
        return record.make_line(actor, person, home, 'sight', body, lk, audience='holon',
                                reason='delegated' if agent else 'human', ts=at, salt='')
    except Exception:  # noqa: BLE001
        return None


def changes(home_dir, now=None, previous=None, lines=None, folded=None, schedule=None, directory=None,
            thresholds=None):
    """Each change of a holon's Condition, or of either column of the pulse, since the kept state, with
    one drafted (unsigned, agent-voiced) Sighting per change and whether the person's own rule and the
    bell let it wake them. Writes nothing; `write_state` keeps the state when the caller asks."""
    t = now_or(now)
    out = {'changed': [], 'sightings': [], 'state': None, 'first': False, 'said': []}
    try:
        if not isinstance(home_dir, str) or not os.path.isdir(home_dir):
            out['said'].append('there is no home folder here, so nothing has changed')
            return out
        if lines is None or not isinstance(folded, dict):
            lines, folded = _read_home(home_dir)
        res = connections(home_dir, now=t, lines=lines, folded=folded, schedule=schedule, directory=directory,
                          thresholds=thresholds)
        state = _state_of(res)
        out['state'] = state
        out['said'].extend(res.get('said') or [])
        prev, why = (previous, '') if isinstance(previous, dict) else _read_state(home_dir)
        if not isinstance(prev, dict) or not isinstance(prev.get('holons'), dict):
            out['first'] = True
            out['said'].append('%s; this is the first reading, so no change is reported' % (why or 'no state was given'))
            return out
        home = res.get('home') or ''
        g = _Ground(folded, lines, t)
        person = g.keeper(home) or (sorted(g.persons(home))[0] if g.persons(home) else '')
        agent = _home_agent(g, home, person)
        if not agent:
            out['said'].append('no one agent of the person is let into the home, so each draft names the person as '
                               'its actor and still carries the agent\'s voice')
        rule = _person_rule(lines, folded, person)
        rows = {r['holon']: r for r in res.get('rows') or []}
        for X in sorted(state['holons']):
            now_s, was = state['holons'][X], prev['holons'].get(X)
            if not isinstance(was, dict):
                out['said'].append('%s is newly connected; its colors are kept from now on' % _short(X))
                continue
            r = rows.get(X) or {}
            for what in WHATS:
                frm, to = was.get(what), now_s.get(what)
                if frm not in KEPT_COLORS:          # only the four colors or grey are read from the kept state
                    out['said'].append('the kept %s for %s is not a color, so it is not compared'
                                       % (what, _short(X)))
                    continue
                if frm == to:
                    continue
                if what == 'condition':
                    why = (r.get('condition') or {}).get('basis')
                else:
                    why = '; '.join(((r.get(PULSE_WORD) or {}).get(what) or {}).get('why') or [])
                draft = _draft(agent, person, home, X, r.get('name'), what, frm, to, why or '', _iso(t),
                               now_s.get('condition_line') if what == 'condition' else None)
                other_side = what == 'condition'          # their own word; a column of the pulse is ours, computed
                signal = {'kind': 'sight', 'sight_kind': SIGHT_KIND, 'id': draft['id'] if draft else None,
                          'holon': home, 'from_holon': X if other_side else home,
                          'from': (sorted(g.persons(X))[0] if g.persons(X) else X) if other_side else person}
                wake = {'wake': False, 'rule': None, 'permit': None}
                rule_wakes = False
                if emergency_mod is not None:
                    try:
                        cl = emergency_mod.classify(signal, rule, {'members': sorted(g.persons(home))})
                        wake['rule'], rule_wakes = cl.get('why'), cl.get('wake') is True
                    except Exception as e:  # noqa: BLE001
                        wake['rule'] = 'the rule could not be read (%s)' % type(e).__name__
                else:
                    wake['rule'] = 'emergency.py is not present; nothing wakes'
                if other_side:
                    ok, why_p = False, {'why': 'agreement.py is not present; no bell rings across holons'}
                    if agreement_mod is not None:
                        try:
                            ok, why_p = agreement_mod.bell_permit(folded, home, X, SIGHT_KIND, now=_iso(t))
                        except Exception as e:  # noqa: BLE001
                            ok, why_p = False, {'why': 'the bell permit could not be read (%s)' % type(e).__name__}
                    wake['permit'] = why_p.get('why') if isinstance(why_p, dict) else None
                else:
                    ok = True
                    wake['permit'] = 'own-holon: the %s is this home\'s own computed signal' % PULSE_WORD
                wake['wake'] = bool(rule_wakes and ok)
                out['changed'].append({'holon': X, 'what': what, 'from': frm, 'to': to, 'why': why or None,
                                       'wake': wake, 'draft': draft['id'] if draft else None, 'voice': 'agent',
                                       'voice_words': 'drafted by the agent: a proposal for the person\'s word, '
                                                      'counting for nothing until they stand on it'})
                if draft:
                    out['sightings'].append(draft)
        out['said'] = sorted(set(out['said']))
        return out
    except Exception as e:  # noqa: BLE001
        out['said'].append('the changes could not be read (%s)' % type(e).__name__)
        return out


# ------------------------------------------------------------------------------------ the Markdown Card

def _cell(text):
    return ' '.join(str(text if text is not None else '').replace('|', '\\|').split())


def render(result):
    """The Markdown Card on paper: one table (Condition · the pulse us to them · them to us · our ear · with us),
    and the summary line under it."""
    res = result if isinstance(result, dict) else {}
    rows = [r for r in res.get('rows') or [] if isinstance(r, dict)]
    out = ['# Connections', '', '*As of %s.*' % (res.get('as_of') or 'no time'), '']
    out.append('| Holon | Condition | %s: us to them | %s: them to us | our ear | with us |' % (PULSE_WORD, PULSE_WORD))
    out.append('|---|---|---|---|---|---|')
    for r in rows:
        c = r.get('condition') or {}
        p = r.get(PULSE_WORD) or {}
        e = r.get('ear') or {}
        w = r.get('with_us') or {}
        cond = '%s: %s' % (c.get('color') or GREY, c.get('why') or c.get('basis') or '')
        if c.get('until') and not c.get('stale'):
            cond += ' (until %s)' % c['until']
        cols = []
        for d in ('us_to_them', 'them_to_us'):
            col = p.get(d) if isinstance(p.get(d), dict) else {}
            cols.append('%s: %s' % (col.get('color') or 'not computed', '; '.join(col.get('why') or [])))
        ear = '%s: %s%s' % (e.get('heard') or 'never', e.get('basis') or '',
                            (', last pulled %s' % e['pulled_at']) if e.get('pulled_at') else '')
        wu = ('%d given, %d received; asks waiting %d on them, %d on us; %d line(s) crossed in the last %s'
              % (w.get('commitments_given', 0), w.get('commitments_received', 0), w.get('asks_waiting_on_them', 0),
                 w.get('asks_waiting_on_us', 0), w.get('lines_crossed', 0), _span_words(w.get('window_s') or 0)))
        out.append('| %s | %s | %s | %s | %s | %s |' % (_cell(r.get('name') or _short(r.get('holon'))), _cell(cond),
                                                        _cell(cols[0]), _cell(cols[1]), _cell(ear), _cell(wu)))
    if not rows:
        out.append('| (none) | | | | | |')
    s = res.get('summary') or {}
    label = {r.get('holon'): (r.get('name') or _short(r.get('holon'))) for r in rows}

    def names(ids):
        return ', '.join(label.get(x) or _short(x) for x in ids or [])
    out.append('')
    if not rows:
        out.append('No connection yet.')
    else:
        parts = []
        if s.get('all_live'):
            parts.append('Every connection is live')
        else:
            parts.append('Not every connection is live: %s' % names(s.get('not_live')))
        if s.get('commitments_yellow_or_better'):
            parts.append('each holon you have exchanged Commitments with reads yellow or better toward you')
        else:
            parts.append('these holons you have exchanged Commitments with read less than yellow toward you: %s'
                         % names(s.get('not_yellow_or_better')))
        if s.get('ours_yellow_or_better'):
            parts.append('and your side toward each of them reads yellow or better.')
        else:
            parts.append('and your side reads less than yellow toward: %s.'
                         % names(s.get('ours_not_yellow_or_better')))
        out.append('; '.join(parts))
    for line in res.get('said') or []:
        out.append('')
        out.append('*%s.*' % _cell(line))
    return '\n'.join(out) + '\n'


# ------------------------------------------------------------------------------------ command line

def _main(argv=None):
    import argparse
    argv = list(sys.argv[1:] if argv is None else argv)
    sub = argv[0] if argv and argv[0] == 'changes' else None
    if sub:
        argv = argv[1:]
    ap = argparse.ArgumentParser(prog='connections.py', description='The Connections view: Condition, %s, our ear.'
                                 % PULSE_WORD)
    ap.add_argument('home')
    ap.add_argument('--now', default=None)
    ap.add_argument('--json', action='store_true')
    if sub:
        ap.add_argument('--write', action='store_true', help='keep this reading as the state to compare with next')
    a = ap.parse_args(argv)
    if sub:
        res = changes(a.home, now=a.now)
        if a.write and isinstance(res.get('state'), dict):
            res['written'] = write_state(a.home, res['state'])
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=str) + '\n')
        return 0
    res = connections(a.home, now=a.now)
    if a.json:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=str) + '\n')
    else:
        sys.stdout.write(render(res))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
