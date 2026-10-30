#!/usr/bin/env python3
"""rooms.py — who is in each room, its posture, what was offered and agreed, and the Roles held.

    rooms(lines, holons, actor=None, minutes=20, fold=None, now=None) -> {room holon id: room}
    roles(lines, holons) -> {holon id: {actor: role}}

`join`, `affirm`, `posture` and `leave` fold into no item (they are acts about a holon, not
things in it), so this file reads them straight from the lines, the same way a person would
from the sheet. A room is a holon whose kind is `room`, or any holon with a posture line.

Per room:

  present       [{actor, kind, for, role}]: persons who joined this room and have not left, and the
                agents a present person affirmed (an agent is in a room only after a person's
                `affirm`). The keeper is present from the holon's inception line. A join that
                records joining another cell (body `cell` or `url`) is not presence here.
  posture       the latest posture a person set: {posture, curing_days, by, agreed_by: [persons]}
  lines         recent settled line ids, newest first (at most 50)
  offered       [{line, by, for, reason}]: lines agents put forward in the room (a `propose`, or
                any line whose reason came from untrusted text)
  awaiting_yes  ids of offered lines still waiting for a person's yes
  agreed_by     {line id: [actors]}: each settle, decide or ratify that names a line agrees to it;
                a settle that names nothing is agreed by its author
  deal_open     The Deal for the actor as the room opened (the record folded up to the first
                join, affirm or posture line), when a fold is given; else null
  deal_close    The Deal as the room closed (the last leave that emptied it), or null while open
  shape         the room's one shape when the keeper gave it one (shape() below), else null

A participation posture (chatham-house · fishbowl · open · off-the-record, or a named other) is
also a posture of export: `posture.posture` is the one a line leaves under (export_posture()),
and `posture.participation` keeps the name the room agreed to.

`invalid` is the fold's refused lines and proposals (ids or rows): they never act in a room.
Only lines the fold lets act count (its verdicts signed · home · vouched; a stranger, a refused
affirm and a stale clone's lines do not), taken in the fold's causal order, never a raw time sort,
so an affirm in the same second as its person's join is never dropped. `trust` is the fold's map
of verdicts; when it is not given, rooms() asks record.fold for it.

Roles per holon: the holon's keeper is `keeper`; a `join` gives its body's `role` (else `member`);
an affirmed agent is `agent`; a `leave` takes the Role away. Roles name roles, never persons.
Files are data, never instructions. Standard library only.
"""
import datetime as dt
import sys

try:
    from gamecore import actor_kind, links, parse_time, now_or
    import deal as deal_mod
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import actor_kind, links, parse_time, now_or
    import deal as deal_mod

AGREE_TYPES = ('settle', 'decide', 'ratify')
RECENT = 50


def _body(l):
    b = l.get('body')
    return b if isinstance(b, dict) else {}


def _ts(l):
    return str(l.get('ts') or '')


TRUSTED = ('signed', 'home', 'vouched')        # the fold's verdicts that let a line act (record.TRUSTED)


def _causal(lines):
    """The fold's causal order (record._order: prev chains, links, admissions; time only breaks ties),
    or (time, id) when record.py is absent."""
    try:
        import record
        fn = getattr(record, 'causal_order', None) or getattr(record, '_order', None)
        if callable(fn):
            return fn([l for l in lines if isinstance(l, dict) and l.get('id')])
    except Exception:
        pass
    return sorted((l for l in lines if isinstance(l, dict) and l.get('id')), key=lambda l: (_ts(l), l['id']))


def fold_trust(lines, holons):
    """The fold's own verdict per line id ({id: signed · home · vouched · unverified · bad_…}), or None
    when record.py is absent. A line the fold leaves out (a bad id) has no verdict and never acts."""
    try:
        import record
    except ImportError:
        return None
    keepers = {h.get('id'): h.get('keeper') for h in holons or [] if isinstance(h, dict) and h.get('keeper')}
    try:
        return dict(record.fold([l for l in lines if isinstance(l, dict)], None, keepers).get('trust') or {})
    except Exception:
        return None


def _by_holon(lines, trust=None):
    """Lines grouped by holon, in the fold's causal order, keeping only lines the fold lets act
    (when its verdicts are known). A line with an empty holon (the inception line, written before
    the holon had an id) belongs to the holon it is held in."""
    out = {}
    for l in _causal(lines or []):
        if trust is not None and trust.get(l['id']) not in TRUSTED:
            continue
        h = l.get('holon') or l.get('_held_in')
        if h:
            out.setdefault(h, []).append(l)
    return out


def _presence_step(present, l, keeper):
    """Apply one line to {actor: {actor, kind, for, role}}: a person's join, an affirm, a leave."""
    a, typ, b = l.get('actor'), l.get('type'), _body(l)
    if not isinstance(a, str) or actor_kind(a) is None:
        return
    if typ == 'join' and actor_kind(a) == 'person' and l.get('for') == a \
            and not b.get('cell') and not b.get('url'):     # a join that records joining another cell is not presence here
        present[a] = {'actor': a, 'kind': 'person', 'for': a,
                      'role': 'keeper' if a == keeper else str(b.get('role') or 'member')}
    elif typ == 'affirm' and a in present and isinstance(b.get('agent'), str) \
            and actor_kind(b['agent']) == 'agent':
        present[b['agent']] = {'actor': b['agent'], 'kind': 'agent', 'for': a, 'role': 'agent'}
    elif typ == 'leave':
        present.pop(a, None)
        for k in [k for k, v in present.items() if v['kind'] == 'agent' and v['for'] == a]:
            present.pop(k)           # an agent leaves with its person


def _presence(ls, keeper, upto=None):
    """{actor: {actor, kind, for, role}} present after the first `upto` lines (all when None),
    taken in the order given (the fold's causal order)."""
    present = {}
    for n, l in enumerate(ls):
        if upto is not None and n >= upto:
            break
        _presence_step(present, l, keeper)
    return present


def roles(lines, holons, trust=None):
    out = {}
    keepers = {h.get('id'): h.get('keeper') for h in holons or [] if isinstance(h, dict)}
    by_h = _by_holon(lines, trust if trust is not None else fold_trust(lines, holons))
    for hid in set(keepers) | set(by_h):
        r = {}
        if keepers.get(hid):
            r[keepers[hid]] = 'keeper'
        for a, v in _presence(by_h.get(hid, []), keepers.get(hid)).items():
            r[a] = v['role']
        for l in by_h.get(hid, []):      # a leave from a non-room holon ends the role too
            if l.get('type') == 'leave' and l.get('actor') in r and l.get('actor') != keepers.get(hid):
                r.pop(l['actor'], None)
        out[hid] = r
    return out


def _gone_by_verdict(lines, trust, holon):
    """Agents whose standing here has ended: their newest line the fold reads as `unverified` (a
    clone's stale claim, an ended body, an admission that no longer stands). A refused line (a bad
    signature, a refused admission, a bad vouch, a line for another holon) or a paper line changes
    nothing about who is present: it is skipped, and the line before it decides."""
    if trust is None:
        return set()
    last = {}
    for l in _causal(lines or []):
        if (l.get('holon') or l.get('_held_in')) == holon and actor_kind(l.get('actor')) == 'agent':
            v = trust.get(l['id'])
            if v in TRUSTED or v == 'unverified':
                last[l['actor']] = v
    return {a for a, v in last.items() if v == 'unverified'}


def rooms(lines, holons, actor=None, minutes=20, fold=None, now=None, trust=None, invalid=None):
    t = now_or(now)
    skip = _skip_ids(invalid)
    trust = trust if trust is not None else fold_trust(lines, holons)
    by_h = _by_holon(lines, trust)
    meta = {h.get('id'): h for h in holons or [] if isinstance(h, dict) and h.get('id')}
    room_ids = {i for i, h in meta.items() if h.get('kind') == 'room'}
    room_ids |= {i for i, ls in by_h.items() if any(l.get('type') == 'posture' for l in ls)}
    out = {}
    for hid in sorted(room_ids):
        ls = by_h.get(hid, [])
        keeper = (meta.get(hid) or {}).get('keeper')
        present = _presence(ls, keeper)
        for gone in _gone_by_verdict(lines, trust, hid):
            present.pop(gone, None)
        posture, said_as = None, None
        for l in ls:
            if l.get('type') == 'posture' and actor_kind(l.get('actor')) == 'person' and l['id'] not in skip:
                b = _body(l)
                if b.get('withdraw') or b.get('at') == 'close':
                    continue             # a confirmation or a change of mind is the shape's to read, never a new setting
                if posture is None or b.get('posture') != said_as:
                    said_as = b.get('posture')
                    posture = {'posture': export_posture(said_as), 'curing_days': b.get('curing_days'),
                               'by': l.get('actor'), 'agreed_by': []}
                    if said_as not in EXPORT_POSTURE or said_as != posture['posture']:
                        posture['participation'] = said_as
                if l.get('actor') not in posture['agreed_by']:
                    posture['agreed_by'].append(l['actor'])
        agreed = {}
        for l in ls:
            if l.get('type') in AGREE_TYPES and actor_kind(l.get('actor')) == 'person':
                named = links(l, 'anchored_to') + links(l, 'answers')
                for x in (named or [l['id']]):
                    agreed.setdefault(x, [])
                    if l['actor'] not in agreed[x]:
                        agreed[x].append(l['actor'])
        settled = [l['id'] for l in reversed(ls) if l.get('type') == 'settle'][:RECENT]
        offered = []
        for l in ls:
            if actor_kind(l.get('actor')) == 'agent' and (l.get('type') == 'propose' or l.get('reason') == 'untrusted'):
                offered.append({'line': l['id'], 'by': l.get('actor'), 'for': l.get('for'),
                                'reason': l.get('reason') or 'human'})
        awaiting = [o['line'] for o in offered if o['line'] not in agreed]
        opened = next((_ts(l) for l in ls if l.get('type') in ('join', 'affirm', 'posture')), None)
        closed = None
        if opened:
            for n, l in enumerate(ls):
                if l.get('type') == 'leave' and not _presence(ls, keeper, n + 1):
                    closed = _ts(l)
            if closed and present:
                closed = None            # someone came back: the room is open again
        out[hid] = {'id': hid, 'name': (meta.get(hid) or {}).get('name'), 'keeper': keeper,
                    'present': sorted(present.values(), key=lambda v: (v['kind'] != 'person', v['actor'])),
                    'posture': posture, 'lines': settled, 'offered': offered, 'awaiting_yes': awaiting,
                    'agreed_by': agreed, 'opened': opened, 'closed': closed,
                    'shape': shape(ls, keeper, t, skip, actor),
                    'deal_open': _deal_at(lines, fold, opened, actor, minutes, present, holons),
                    'deal_close': _deal_at(lines, fold, closed, actor, minutes, present, holons)}
    return out


def _deal_at(lines, fold, ts, actor, minutes, present, holons):
    """The Deal as the record stood at `ts`, or None when there is no fold, no moment or no actor."""
    if not callable(fold) or not ts or not actor or parse_time(ts) is None:
        return None
    try:
        items = fold([l for l in lines if isinstance(l, dict) and _ts(l) <= ts])
    except Exception:
        return None
    room = [a for a in present if a != actor]
    return deal_mod.deal(items, None, actor, minutes, room, ts, holons)


# ---------------------------------------------------------------------------- the one shape
#
# A room may meet in one shape (a proposal): the lobby,
# the great room where anyone present may propose, the vote, the writing, and reflection, with a
# participation posture agreed at the door, confirmed again at the close, and a curing window of
# a few days afterwards in which anyone may change their mind. The shape is read from the lines
# like the rest of the room: a `shape` line by the keeper (or `body.shape` on the room's inception
# line), `part` lines by the facilitator (the switch), `propose`, `vote`, `card`, `claim`, `hand`,
# `say`/`learn` in reflection, and `posture` lines with `body.at` (open · close) or
# `body.withdraw`. The engine tallies by the rule and never breaks a tie.

SHAPE_PARTS = ('lobby', 'great room', 'the vote', 'the writing', 'reflection')
DOES = ('gather', 'propose', 'vote', 'write', 'reflect')        # what each of the five parts is for, by position
CLOSE = 'close'                  # the part name the facilitator moves to when the meeting ends
PARTICIPATION = ('chatham-house', 'fishbowl', 'open', 'off-the-record')
EXPORT_POSTURE = {'open': 'open', 'fishbowl': 'open', 'chatham-house': 'names-hidden', 'off-the-record': 'sealed',
                  'names-hidden': 'names-hidden', 'sealed': 'sealed'}
CURE_DAYS = 3
VOTE_RULE = {'choose': 3, 'advance': 2, 'minutes': 20}


def export_posture(p):
    """The posture a line leaves the room under (open · names-hidden · sealed) for a participation
    posture. A named other posture the reader does not know leaves sealed: the narrowest reading."""
    if not p:
        return 'open'
    return EXPORT_POSTURE.get(p, 'sealed')


def _skip_ids(invalid):
    """Ids the fold refused or holds as proposals only: a set from a list of ids or of {id: …} rows."""
    out = set()
    for x in invalid or ():
        if isinstance(x, str):
            out.add(x)
        elif isinstance(x, dict) and isinstance(x.get('id'), str):
            out.add(x['id'])
    return out


def _iso(d):
    return d.isoformat(timespec='seconds') if d else None


def _int(v, default):
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else default


def _parts(raw):
    """[{name, does}] from the shape's parts: names (the five by position) or {name, does} objects."""
    items = raw if isinstance(raw, list) and raw else list(SHAPE_PARTS)
    out = []
    for i, p in enumerate(items):
        if isinstance(p, dict) and isinstance(p.get('name'), str):
            out.append({'name': p['name'], 'does': p.get('does') if p.get('does') in DOES else
                        (DOES[i] if i < len(DOES) else 'gather')})
        elif isinstance(p, str) and p:
            known = SHAPE_PARTS.index(p) if p in SHAPE_PARTS else i
            out.append({'name': p, 'does': DOES[known] if known < len(DOES) else 'gather'})
    return out


def _rule(raw, default=None):
    r = dict(default or VOTE_RULE)
    if isinstance(raw, dict):
        r['choose'] = _int(raw.get('choose'), r['choose'])
        r['advance'] = _int(raw.get('advance'), r['advance'])
        r['minutes'] = _int(raw.get('minutes'), r['minutes'])
    return r


def _the_shape(ls, keeper):
    """The keeper's newest shape: a `shape` line, else the inception line's body.shape. (line, shape dict)."""
    found = None
    for l in ls:
        b = _body(l)
        if l.get('actor') != keeper or actor_kind(keeper) != 'person':
            continue
        if l.get('type') == 'shape' and isinstance(b.get('shape'), dict):
            found = (l, b)
        elif l.get('type') == 'join' and not l.get('holon') and isinstance(b.get('shape'), dict) and found is None:
            found = (l, b)
    return found


def _tally(proposals, votes, rule):
    """Count each proposal's votes and choose the top `advance`; a tie across the line is said, never broken."""
    count = {p['id']: 0 for p in proposals}
    for v in votes.values():
        for c in v['choices']:
            count[c] = count.get(c, 0) + 1
    ranked = sorted(proposals, key=lambda p: -count[p['id']])          # stable: the earlier proposal first among equals
    adv = rule['advance']
    chosen, tie = [], None
    if ranked:
        cut = count[ranked[min(adv, len(ranked)) - 1]['id']]
        above = [p['id'] for p in ranked if count[p['id']] > cut]
        level = [p['id'] for p in ranked if count[p['id']] == cut]
        if cut == 0:
            chosen = above[:adv]
        elif len(above) + len(level) <= adv:
            chosen = above + level
        else:
            chosen = above
            tie = {'votes': cut, 'proposals': level, 'places': adv - len(above),
                   'said': 'the engine never breaks a tie; the circle chooses'}
    return count, chosen, tie


def shape(ls, keeper, now=None, skip=(), actor=None):
    """The room's shape folded from its lines (trusted, in causal order), or None when it has none.

    {name, parts: [{name, does}], facilitator, part, part_does, since, moves: [{part, at, by, line}],
     posture: {name, leaves_as, agreed_open: [persons], confirmed: [persons], not_confirmed: [persons],
               not_agreed: [persons present], withdrawn: [persons], cure_until, changes: [{by, at, line,
               narrowed_to | revoked}]},
     proposals: [{id, text, by, for, at, card, votes (when the vote has closed, else null)}],
     vote: {rule: {choose, advance}, opens, closes, open, closed, closed_at, cast, of, voters: [persons],
            chosen: [ids], tie: {votes, proposals, places, said} | null},
     writeups: [{card, proposal, title, holder, by, at}],
     reflections: [{by, text, at, line}],
     closed, owes: [{kind: agree | vote | holder | confirm, who, about, by}],
     mine: {agreed, confirmed, withdrawn, vote: [ids] | null, facilitator},
     refused: [{line, why}]}"""
    found = _the_shape(ls, keeper)
    if not found:
        return None
    sline, sb = found
    sh = sb['shape']
    t = now_or(now)
    parts = _parts(sh.get('parts'))
    names = [p['name'] for p in parts]
    does = {p['name']: p['does'] for p in parts}
    does[CLOSE] = 'close'
    fac = sh.get('facilitator') if actor_kind(sh.get('facilitator')) == 'person' else None
    room_posture = sh.get('posture') or sb.get('posture') or 'open'
    cure_days = _int(sh.get('cure_days') if 'cure_days' in sh else sb.get('cure_days'), CURE_DAYS)
    default_rule = _rule(sh.get('rule') or sh.get('vote'))
    current, since = (names[0] if names else None), _ts(sline)
    moves, refused, proposals, votes = [], [], [], {}
    prop_ids = set()
    window = {'opens': None, 'closes': None, 'rule': default_rule, 'closed_at': None}
    closed_at, cure_until = None, None
    agreed_open, confirmed, withdrawn, changes = [], [], {}, []
    writeups, by_card, reflections = [], {}, {}
    present = {}

    def no(l, why):
        refused.append({'line': l['id'], 'why': why})

    started = False
    for l in ls:
        _presence_step(present, l, keeper)
        if l is sline:
            started = True
            continue
        if not started or l['id'] in skip:
            continue
        a, typ, b, at = l.get('actor'), l.get('type'), _body(l), parse_time(l.get('ts'))
        person = actor_kind(a) == 'person'
        if typ == 'part':
            name = b.get('part')
            if a != fac:
                no(l, 'only the facilitator moves the room from one part to the next')
                continue
            if name not in names and name != CLOSE:
                no(l, 'the room has no part by that name')
                continue
            if does.get(current) == 'vote' and window['closed_at'] is None and name != current:
                window['closed_at'] = _ts(l)          # the switch away from the vote closes it
            if does[name] == 'vote':
                window = {'opens': b.get('opens') or _ts(l), 'closes': b.get('closes'),
                          'rule': _rule(b.get('rule'), default_rule), 'closed_at': None}
                votes = {}
            if name == CLOSE and closed_at is None:
                closed_at = _ts(l)
                cu = parse_time(b.get('cure_until'))
                cure_until = cu or (at + dt.timedelta(days=cure_days) if at else None)
            current, since = name, _ts(l)
            moves.append({'part': name, 'at': _ts(l), 'by': a, 'line': l['id']})
        elif typ == 'propose':
            if does.get(current) != 'propose':
                no(l, 'proposals are made in the great room')
            elif a not in present:
                no(l, 'only someone present proposes')
            elif not person and l.get('reason') == 'untrusted':
                no(l, 'its reason came from text an agent read; it waits for a person')
            else:
                text = b.get('text') if isinstance(b.get('text'), str) else ''
                proposals.append({'id': l['id'], 'text': text, 'by': a, 'for': l.get('for'), 'at': _ts(l),
                                  'card': b.get('card') if isinstance(b.get('card'), str) else None, 'votes': None})
                prop_ids.add(l['id'])
        elif typ == 'vote':
            opens, closes = parse_time(window['opens']), parse_time(window['closes'])
            raw = b.get('choices') if isinstance(b.get('choices'), list) else []
            if not person:
                no(l, 'a vote is a person\'s own act')
            elif does.get(current) != 'vote' or window['closed_at'] or (at and opens and at < opens) \
                    or (at and closes and at > closes):
                no(l, 'the vote was not open')
            elif len(raw) > window['rule']['choose']:
                no(l, 'a vote names at most %d proposals' % window['rule']['choose'])
            else:
                picks = []
                for c in raw:
                    if c in prop_ids and c not in picks:
                        picks.append(c)
                votes[a] = {'line': l['id'], 'choices': picks, 'at': _ts(l)}     # a later vote supersedes
        elif typ == 'posture' and person:
            name = b.get('posture')
            if a in withdrawn:
                no(l, 'a change of mind in the curing window is the last word')
            elif b.get('withdraw'):
                if cure_until and at and at > cure_until:
                    no(l, 'the curing window had closed')
                else:
                    ch = {'by': a, 'at': _ts(l), 'line': l['id']}
                    if name and name != room_posture:
                        ch['narrowed_to'] = name
                    else:
                        ch['revoked'] = True
                    changes.append(ch)
                    withdrawn[a] = ch
            elif (b.get('at') or 'open') == 'close':
                if closed_at is None:
                    no(l, 'the room has not closed yet')
                elif name != room_posture:
                    no(l, 'it confirms a posture other than the room\'s')
                elif a not in confirmed:
                    confirmed.append(a)
            elif name == room_posture:
                if a not in agreed_open:
                    agreed_open.append(a)
            else:
                no(l, 'it agrees to a posture other than the room\'s')
        elif typ == 'card':
            served = [x for x in links(l, 'serves') + links(l, 'anchored_to') if x in prop_ids]
            if served:
                w = {'card': l['id'], 'proposal': served[0], 'title': b.get('title'),
                     'holder': b.get('holder') if actor_kind(b.get('holder')) else None, 'by': b.get('by'), 'at': _ts(l)}
                writeups.append(w)
                by_card[l['id']] = w
        elif typ in ('claim', 'hand'):
            for c in ([b.get('card')] if isinstance(b.get('card'), str) else []) + links(l, 'anchored_to'):
                if c in by_card:
                    by_card[c]['holder'] = a if typ == 'claim' else (b.get('to') if actor_kind(b.get('to')) else by_card[c]['holder'])
        elif typ in ('say', 'learn') and person and does.get(current) == 'reflect' and isinstance(b.get('text'), str):
            reflections[a] = {'by': a, 'text': b['text'], 'at': _ts(l), 'line': l['id']}    # one line each; the newest stands

    # the vote, closed by the switch or by its clock
    closes = parse_time(window['closes'])
    vote_seen = any(does.get(m['part']) == 'vote' for m in moves)
    vclosed = bool(window['closed_at']) or bool(vote_seen and closes and t >= closes)
    vopen = does.get(current) == 'vote' and not vclosed
    rule = window['rule']
    chosen, tie = [], None
    if vote_seen and vclosed:
        count, chosen, tie = _tally(proposals, votes, rule)
        for p in proposals:
            p['votes'] = count.get(p['id'], 0)
    persons_here = [x for x, v in present.items() if v['kind'] == 'person']
    eligible = [x for x in agreed_open if x not in withdrawn] or persons_here

    owes = []
    closed = closed_at is not None
    if not closed:
        for x in persons_here:
            if x not in agreed_open and x not in withdrawn:
                owes.append({'kind': 'agree', 'who': x, 'about': room_posture, 'by': None})
    if vopen:
        for x in eligible:
            if x not in votes:
                owes.append({'kind': 'vote', 'who': x, 'about': None, 'by': window['closes']})
    if vote_seen and vclosed:
        for pid in chosen:
            ws = [w for w in writeups if w['proposal'] == pid]
            if not ws or not any(w['holder'] for w in ws):
                owes.append({'kind': 'holder', 'who': None, 'about': pid, 'by': None})
    not_confirmed = [x for x in agreed_open if x not in confirmed and x not in withdrawn] if closed else []
    if closed and cure_until and t <= cure_until:
        for x in not_confirmed:
            owes.append({'kind': 'confirm', 'who': x, 'about': room_posture, 'by': _iso(cure_until)})

    mine = None
    if actor:
        mine = {'agreed': actor in agreed_open, 'confirmed': actor in confirmed, 'withdrawn': actor in withdrawn,
                'vote': votes[actor]['choices'] if actor in votes else None, 'facilitator': actor == fac}
    return {
        'name': sh.get('name') if isinstance(sh.get('name'), str) else None,
        'parts': parts, 'facilitator': fac, 'part': current, 'part_does': does.get(current), 'since': since,
        'moves': moves,
        'posture': {'name': room_posture, 'leaves_as': export_posture(room_posture),
                    'agreed_open': agreed_open, 'confirmed': confirmed, 'not_confirmed': not_confirmed,
                    'not_agreed': [x for x in persons_here if x not in agreed_open and x not in withdrawn],
                    'withdrawn': sorted(withdrawn), 'cure_days': cure_days, 'cure_until': _iso(cure_until),
                    'curing': bool(closed and cure_until and t <= cure_until), 'changes': changes},
        'proposals': proposals,
        'vote': {'rule': rule, 'opens': window['opens'], 'closes': window['closes'], 'open': vopen,
                 'closed': bool(vote_seen and vclosed), 'closed_at': window['closed_at'] or (window['closes'] if vote_seen and vclosed else None),
                 'cast': len(votes), 'of': len(eligible), 'voters': sorted(votes), 'chosen': chosen, 'tie': tie},
        'writeups': writeups,
        'reflections': sorted(reflections.values(), key=lambda r: r['at']),
        'closed': closed_at, 'owes': owes, 'mine': mine, 'refused': refused,
    }
