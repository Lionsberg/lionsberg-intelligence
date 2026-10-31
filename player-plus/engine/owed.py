#!/usr/bin/env python3
"""owed.py — what is owed, computed from the record, never remembered.

    owed(items, actor=None, holon=None, now=None, horizon_days=2) -> {"entries": [...], "proposals": [...],
                                                                      "summary": {holder: {...}}}
    waiting_on(items, lines, actor, now=None) -> the sender's side: the open asks this person started,
                                                 per recipient, with each recipient's state

Across every holon the items come from, it lists what waits on whom:

  commitment  an open commitment past its by-when, or due within the horizon (default two days)
  request     a request no one has answered yet
  offer       an open offer that names whom it is for (`to`), waiting on their answer
  thread      a thread whose last line is not the holder's (addressed to them, or one they spoke in)
  ratify      a decision made and waiting for a person to ratify it (the holon's keeper unless named)
  decide      a proposal put to a person by name, waiting for their decision
  claim       a claim whose time ran out while the card is still not done
  handoff     a body (bodies.fold) finished with a handoff no person has reviewed: owed by the
              person the body answers for, "review this handoff · N min" (N from review_min)
  question    an `rfg` or `escalate` past its by-when, unanswered: owed by the holon it climbed to,
              the ball in its keeper's court (from ladder.questions)
  receipt     (with receipts=True) a trusted line by this holon's own people that crossed (its
              audience is members or wider, or it lives in a cell) and asks something of another
              holon's person, with no Receipt after RECEIPT_HOURS: the sender's concern, so its
              holder is the sender (the person the line was written for, else its actor), and the
              row names its `addressee`: waiting on a Receipt from them, one minute

Each entry: kind · id · holon · title · holder · status (past | near | waiting) · due · age_days ·
minutes (an estimate of what answering takes) · minutes_basis. For a request, an offer or a question
the minutes are the sender's `effort` when the line gave one (whole minutes, more than none), else
the kit's own estimate (MINUTES); `minutes_basis` says which (effort | default). The summary gives,
per holder, the entries, their minutes, and `minutes_asked`: the minutes of the requests, offers and
questions waiting on them, which is what others asked of their time. Lines an agent wrote for a
reason that came from untrusted text are never owed: they come back under "proposals" for a person
to take up or let go. A pushed thread or request past its push's `expires` folds as retracted and is
not owed.

Receipts are on when the caller asks (receipts=True); the engine's state asks, with the home's own
people. A Receipt is written by the addressee's agent; the row waits on it, and the Deal frames it
for the sender as "no Receipt yet from <addressee>". The receipt row reads the item the line made (a request or
offer card, a commitment, a message's thread, a wallet entry); a receipt on that item by anyone but
the sender's side counts, and silence never does.

WAITING ON (the sender's side, which the person's agent says beside what they owe): every open ask
this person or their agent started (a request or offer card, a request item, a message thread with
`to`, and, among the lines given, an `rfg` or `escalate`), each recipient with one state, the
furthest the record shows: no Receipt · received (a Receipt from their side) · surfaced (a Receipt
in their own hand: written by the person, or carried by room or hand) · acknowledged (a line of
theirs linked to the ask that does not answer it: a say on a request, a clarify move) · answered (an
answer, a move other than clarify, a claim, commit, decide, done, kept, settle, offer or agree
linked to it, or a reply in the message's thread). A Receipt is never an answer. Only trusted
lines count (trusted_lines, the one gate deal.py shares): when the fold's trust map rides with the
items, a line it does not mark trusted is left out, so is a line on the fold's invalid, unverified,
refused, forked or proposal lists, and a line from untrusted text never counts.

  python3 -I owed.py ITEMS.json [--actor person:x] [--holon ID] [--now ISO] [--json]
                     [--receipts] [--receipt-hours H] [--home ID] [--people person:x,...]
                     [--waiting-on --lines LINES.jsonl]
"""
import argparse
import json
import math
import os
import sys
import unicodedata

try:
    from gamecore import (normalize, field, links, parse_time, now_or, days_between, is_untrusted,
                          item_id, holon_of, commitment_status, keeper_of, DONE_STATES, holon_names,
                          actor_kind, live_delegations)
except ImportError:                                   # run from elsewhere: import beside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, parse_time, now_or, days_between, is_untrusted,
                          item_id, holon_of, commitment_status, keeper_of, DONE_STATES, holon_names,
                          actor_kind, live_delegations)

MINUTES = {'commitment': 5, 'request': 5, 'offer': 5, 'thread': 3, 'ratify': 5, 'decide': 5, 'claim': 2,
           'question': 10, 'receipt': 1}
ASK_KINDS = ('request', 'offer', 'question')          # the kinds whose minutes follow the sender's effort
# A line that crossed waits this many hours for its Receipt before the addressee owes one. The
# method's own default (a day: one pull at the slowest daily beat); overridable by argument.
RECEIPT_HOURS = 24
_WIDE = ('members', 'commons', 'public')
_PICKED_UP = DONE_STATES | {'retracted', 'taken', 'answered', 'agreed', 'accepted', 'settled', 'given'}

# waiting on: the states a recipient moves through, nearest first (the kit's own ladder)
WAIT_STATES = ('no_receipt', 'received', 'surfaced', 'acknowledged', 'answered')
WAIT_WORDS = {'no_receipt': 'no Receipt yet', 'received': 'received', 'surfaced': 'in their own hand',
              'acknowledged': 'acknowledged', 'answered': 'answered'}
IN_HAND = ('room', 'hand')                            # a Receipt carried this way was taken in person
ANSWER_TYPES = ('answer', 'claim', 'commit', 'decide', 'done', 'kept', 'settle', 'offer', 'agree')
NOT_A_LINK = ('receive', 'subscribe', 'propose')      # a Receipt says "I have it", never the answer
LINK_RELS = ('answer', 'anchored_to', 'serves', 'supersede', 'witnesses', 'fulfils')
LINK_FIELDS = ('card', 'commitment', 'about', 'what', 'root')    # a move names its ask in `root`
TRUSTED_LINES = ('signed', 'home', 'vouched')         # record.TRUSTED
NOT_COUNTED = ('invalid', 'unverified', 'refused', 'forked', 'proposals')   # the fold's lists that never act


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    return [x for x in v if isinstance(x, str) and x] if isinstance(v, (list, tuple)) else []


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def effort_of(it):
    """The sender's effort in whole minutes, more than none, or None (a fraction, a flag, text: none)."""
    v = field(it, 'effort')
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def ask_minutes(it, kind):
    """(minutes, basis) for an entry of this kind: the sender's effort for an ask, else the kit's estimate."""
    e = effort_of(it) if kind in ASK_KINDS else None
    return (e, 'effort') if e is not None else (MINUTES.get(kind, MINUTES['request']), 'default')


def _thread_lines(t):
    ls = field(t, 'lines')
    return [x for x in ls if isinstance(x, dict)] if isinstance(ls, list) else []


def _retracted(it, t):
    p = field(it, 'push')
    e = parse_time(p.get('expires')) if isinstance(p, dict) else None
    return e is not None and e < t


def thread_view(t):
    """last_actor, last_ts, settled, participants, to — from the thread item."""
    ls = _thread_lines(t)
    last = max(ls, key=lambda x: str(x.get('ts') or '')) if ls else {}
    last_actor = field(t, 'last_actor') or last.get('actor') or (None if ls else field(t, 'actor'))
    last_ts = field(t, 'last_ts') or last.get('ts') or (None if ls else field(t, 'ts'))
    settled = bool(field(t, 'settled')) or str(last.get('type') or '').lower() == 'settle' \
        or str(field(t, 'state') or '').lower() in ('settled', 'closed', 'done')
    parts = {x.get('actor') for x in ls if x.get('actor')}
    if field(t, 'actor'):
        parts.add(field(t, 'actor'))
    return {'last_actor': last_actor, 'last_ts': last_ts, 'settled': settled,
            'participants': sorted(parts), 'to': _as_list(field(t, 'to'))}


def _addressed_to(line, people, holon_id):
    try:
        from receipt import addressed_to
    except ImportError:                               # receipt.py beside this file, when run from elsewhere
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from receipt import addressed_to
    return addressed_to(line, people, holon_id)


def _sent_lines(norm, items):
    """(item, a line-shaped view of the line that made it) for each item a person-addressed line made."""
    out = []
    for c in norm.get('card', []):
        asked = str(field(c, 'asked') or '')
        if asked in ('request', 'offer'):             # a request's addressee is its holder when no `to` is kept
            out.append((c, asked, {'to': field(c, 'to') or (field(c, 'holder') if asked == 'request' else None)}))
    for c in norm.get('commitment', []):
        out.append((c, 'commit', {'committee': field(c, 'committee')}))
    for th in norm.get('thread', []):
        if field(th, 'to'):
            out.append((th, 'say', {'to': field(th, 'to')}))
    for w in norm.get('wallet_entry', []):            # the fold keeps them as `wallet`; normalize reads them
        out.append((w, 'wallet', {'to': field(w, 'to')}))
    return out


def _receipts(norm, items, t, names, people, home, hours):
    """(item, addressee) for each crossed line by this holon's people with no Receipt after `hours`."""
    ppl = {p for p in (people or ()) if isinstance(p, str)}
    try:
        limit = float(hours)
    except (TypeError, ValueError):
        limit = float(RECEIPT_HOURS)
    if not math.isfinite(limit) or limit < 0:
        limit = float(RECEIPT_HOURS)                  # a non-finite or negative wait reads as the default
    out = []
    for it, typ, body in _sent_lines(norm, items):
        if is_untrusted(it) or str(field(it, 'state') or '').lower() in _PICKED_UP:
            continue
        sender = {x for x in (it.get('actor'), it.get('for')) if isinstance(x, str) and x}
        if ppl and not (sender & ppl):
            continue                                  # only lines by this holon's own people
        h = holon_of(it)
        crossed = it.get('audience') in _WIDE or (bool(home) and h != home) or \
            (not home and names.get(h, {}).get('kind') not in (None, 'person'))
        if not crossed:
            continue
        sent = parse_time(field(it, 'ts'))
        if sent is None or (t - sent).total_seconds() / 3600.0 <= limit:
            continue
        got = {r.get('actor') for r in (it.get('receipts') or []) if isinstance(r, dict)}
        got -= sender | ppl
        if got:
            continue                                  # a receipt by the receiving side; silence never counts
        line = {'id': item_id(it), 'type': typ, 'body': body, 'holon': h}
        to = body.get('to')
        named = ([to] if isinstance(to, str) else list(to) if isinstance(to, (list, tuple)) else []) + [body.get('committee')]
        for a in sorted({x for x in named if isinstance(x, str) and x}):
            if a in sender or a in ppl or not _addressed_to(line, {a}, h):
                continue
            out.append((it, a))
    return out


def summarize(entries):
    """Per holder (a string; '' when no one holds it yet): entries, minutes, and minutes_asked, the
    minutes of the requests, offers and questions waiting on them, with how many were sized by effort."""
    out = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        h = e.get('holder') if isinstance(e.get('holder'), str) else ''
        s = out.setdefault(h, {'entries': 0, 'minutes': 0, 'asks': 0, 'minutes_asked': 0, 'sized_by_effort': 0})
        m = e.get('minutes')
        m = m if isinstance(m, (int, float)) and not isinstance(m, bool) and math.isfinite(m) and m >= 0 else 0
        s['entries'] += 1
        s['minutes'] += m
        if e.get('kind') in ASK_KINDS:
            s['asks'] += 1
            s['minutes_asked'] += m
            s['sized_by_effort'] += 1 if e.get('minutes_basis') == 'effort' else 0
    return out


def owed(items, actor=None, holon=None, now=None, horizon_days=2, holons=None, questions=None, bodies=None,
         receipts=False, receipt_hours=RECEIPT_HOURS, home=None, people=None):
    """What is owed, per actor or holon (or everyone, when neither is given). `questions` are
    ladder.questions(): an open one past its by-when is owed by the holon it climbed to. With
    `receipts`, a line that crossed and has had no Receipt for `receipt_hours` (a non-finite or
    negative value reads as RECEIPT_HOURS) waits on its addressee: the row is the sender's (`holder`), naming
    the `addressee`. `home` is the home's holon id:
    a line in any other holon lives in a cell and so has crossed; without it, a holon crosses when
    `holons` names its kind as other than person, or the line's audience is members or wider.
    `people` is this holon's own people (a set of actor ids): only lines they sent are counted, and
    nothing is waited on from an addressee among them; without it, every sender counts and only the sender
    itself is excluded."""
    norm = normalize(items)
    t = now_or(now)
    cards = {item_id(c): c for c in norm.get('card', [])}
    entries, proposals = [], []

    def title_of(it):
        tt = field(it, 'title') or field(it, 'text') or field(it, 'what')
        if not tt:
            for cid in [field(it, 'card')] + links(it, 'anchored_to') + links(it, 'answer'):
                if isinstance(cid, str) and cid in cards:
                    return field(cards[cid], 'title') or cid[:8]
        return (str(tt) if tt else item_id(it)[:8])[:120]

    def add(kind, it, holder, status, due=None, since=None):
        mins, basis = ask_minutes(it, kind)
        entries.append({'kind': kind, 'id': item_id(it), 'holon': holon_of(it), 'title': title_of(it),
                        'holder': holder, 'status': status, 'due': due,
                        'age_days': days_between(since or field(it, 'ts'), t), 'minutes': mins,
                        'minutes_basis': basis})

    def propose(kind, it):
        proposals.append({'kind': kind, 'id': item_id(it), 'holon': holon_of(it),
                          'title': title_of(it),
                          'proposer': field(it, 'actor'), 'for': field(it, 'for'),
                          'note': 'its reason came from text the agent read; a person decides'})

    for c in norm.get('commitment', []):
        if is_untrusted(c):
            propose('commitment', c); continue
        status, _ = commitment_status(c, t)
        if status not in ('open', 'broken'):
            continue
        due = field(c, 'by')
        d = days_between(t, due)
        if status == 'broken' or (d is not None and d <= horizon_days):
            add('commitment', c, keeper_of(c), 'past' if status == 'broken' else 'near', due)

    # requests are cards the fold opened with asked=request; open means not yet answered
    for c in norm.get('card', []):
        if is_untrusted(c):
            continue
        asked, st = str(field(c, 'asked') or ''), str(field(c, 'state') or '').lower()
        if asked == 'request' and st == 'open' and not _retracted(c, t):
            add('request', c, field(c, 'holder'), 'waiting', field(c, 'by'))
        elif asked == 'offer' and st == 'open' and not _retracted(c, t):
            offerer = {x for x in (field(c, 'actor'), field(c, 'for'), field(c, 'offered_by')) if isinstance(x, str)}
            for h in sorted(set(_as_list(field(c, 'to'))) - offerer):     # an offer waits on whom it is for
                add('offer', c, h, 'waiting', field(c, 'by'))
    for r in norm.get('request', []):                 # a request item, when a fold keeps them apart
        if is_untrusted(r):
            propose('request', r); continue
        st = str(field(r, 'state') or '').lower()
        if field(r, 'answered') or st in DONE_STATES | {'answered', 'taken'}:
            continue
        for h in _as_list(field(r, 'to')) or [None]:
            add('request', r, h, 'waiting', field(r, 'by'))

    for th in norm.get('thread', []):
        if is_untrusted(th):
            propose('thread', th); continue
        if _retracted(th, t):
            continue                                  # a push past its expires folds as retracted
        v = thread_view(th)
        if v['settled']:
            continue
        holders = v['to'] or [p for p in v['participants']]
        for h in holders:
            if h and h != v['last_actor']:
                add('thread', th, h, 'waiting', None, v['last_ts'])

    names = holon_names(norm, holons)
    for d in norm.get('decision', []):
        if is_untrusted(d):
            propose('decision', d); continue
        st = str(field(d, 'state') or '').lower()
        if st == 'decided' and not field(d, 'ratified_by'):
            ratifier = field(d, 'ratifier') or names.get(holon_of(d), {}).get('keeper')
            add('ratify', d, ratifier, 'waiting', field(d, 'by'))
        elif st == 'proposed':
            for h in _as_list(field(d, 'to')) + _as_list(field(d, 'holder')):
                add('decide', d, h, 'waiting', field(d, 'by'))

    for it in norm.get('untrusted', []):              # the fold's proposals: lines from untrusted text
        propose(str(it.get('would_fold_into') or it.get('type') or 'line'), it)

    expired = [(c, field(c, 'claim_until') or field(c, 'until'), True) for c in norm.get('card', [])
               if str(field(c, 'state') or '').lower() == 'taken']
    expired += [(cl, field(cl, 'until'), False) for cl in norm.get('claim', [])]
    for it, until_s, is_card in expired:
        until = parse_time(until_s)
        if until is None or until >= t or is_untrusted(it):
            continue
        cid = field(it, 'card') or (links(it, 'anchored_to') or [None])[0]
        card = it if is_card else (cards.get(cid) if isinstance(cid, str) else None)
        if card is not None and str(field(card, 'state') or '').lower() in DONE_STATES:
            continue
        add('claim', it, field(it, 'holder') or field(it, 'actor'), 'past', until_s)

    for q in questions or []:
        if not isinstance(q, dict) or not q.get('past'):
            continue
        mins, basis = ask_minutes(q, 'question')      # ladder.questions carries effort only when the line gave it
        entries.append({'kind': 'question', 'id': q.get('id'), 'holon': q.get('to') or '',
                        'title': str(q.get('question') or '')[:120], 'holder': q.get('holder'), 'status': 'past',
                        'due': q.get('by'), 'age_days': days_between(q.get('ts'), t), 'minutes': mins,
                        'minutes_basis': basis,
                        'type': q.get('type'), 'from_holon': q.get('from_holon'), 'rung': q.get('rung')})

    for bd in bodies or []:                         # bodies.fold: a finished body's handoff, not yet reviewed
        if not isinstance(bd, dict) or not bd.get('handoff') or bd.get('reviewed'):
            continue
        if bd.get('state') not in ('handoff', 'done', 'stale', 'archived'):
            continue
        mins = bd.get('review_min') if isinstance(bd.get('review_min'), (int, float)) else 5
        entries.append({'kind': 'handoff', 'id': bd['handoff'], 'holon': bd.get('holon') or '',
                        'title': f"review this handoff · {mins:g} min", 'holder': bd.get('for'),
                        'status': 'waiting', 'due': None, 'age_days': days_between(bd.get('newest_line'), t),
                        'minutes': float(mins), 'minutes_basis': 'review_min' if 'review_min' in bd else 'default',
                        'body': bd.get('name'), 'task': bd.get('task'),
                        'asks_yes': bd.get('asks_yes', True), 'stale': bd.get('state') == 'stale'})

    if receipts:
        for it, addressee in _receipts(norm, items, t, names, people, home, receipt_hours):
            f = field(it, 'for')                      # the sender's concern: whose line it is
            add('receipt', it, f if isinstance(f, str) and f.startswith('person:') else field(it, 'actor'), 'waiting', None)
            entries[-1]['addressee'] = addressee

    if actor:
        entries = [e for e in entries if e['holder'] == actor]
        proposals = [p for p in proposals if p['for'] == actor or p['proposer'] == actor]
    if holon:
        entries = [e for e in entries if e['holon'] == holon]
        proposals = [p for p in proposals if p['holon'] == holon]
    order = {'past': 0, 'waiting': 1, 'near': 2}
    entries.sort(key=lambda e: (order.get(e['status'], 3), -(e['age_days'] or 0), str(e['id']),
                                str(e.get('holder') or '')))
    return {'as_of': t.isoformat(timespec='seconds'), 'actor': actor, 'holon': holon,
            'entries': entries, 'proposals': proposals, 'summary': summarize(entries)}


# ---------------------------------------------------------------- waiting on: the sender's side

def _epoch(ts):
    t = parse_time(ts) if isinstance(ts, str) else None
    return t.timestamp() if t is not None else None


def _refs(x):
    """Every id a line or item names: its links of answer and anchor, and the id fields that name an ask."""
    out = set()
    for r in LINK_RELS:
        out.update(links(x, r))
    for k in LINK_FIELDS:
        v = field(x, k)
        if isinstance(v, str) and v:
            out.add(v)
    return out


def trusted_lines(items, lines):
    """The one gate on lines, shared with deal.py (deal.trusted_lines calls this): each line once, by
    id; when the fold's trust map can be reached, only a line it marks trusted (an id missing from it
    never passes); never one on the fold's invalid, unverified, refused, forked or proposal lists (a
    line can be signed and still be refused by the fold's validity check), nor one from untrusted
    text. Ordered by ts, then id."""
    if not isinstance(lines, (list, tuple)):
        return []
    trust = items.get('trust') if isinstance(items, dict) and isinstance(items.get('trust'), dict) else None
    out_ids = set()
    if isinstance(items, dict):
        for k in NOT_COUNTED:
            for x in items.get(k) if isinstance(items.get(k), list) else []:
                if not isinstance(x, dict):
                    continue
                if isinstance(x.get('id'), str):
                    out_ids.add(x['id'])
                if isinstance(x.get('lines'), list):                    # a fork: every line but its survivor
                    out_ids.update(i for i in x['lines'] if isinstance(i, str) and i != x.get('survivor'))
    seen, out = set(), []
    for l in lines:
        if not isinstance(l, dict):
            continue
        lid = l.get('id')
        if not isinstance(lid, str) or not lid or lid in seen or lid in out_ids:
            continue
        if (trust is not None and trust.get(lid) not in TRUSTED_LINES) or \
                ('_trust' in l and l['_trust'] not in TRUSTED_LINES):
            continue
        if _s(l.get('reason')).lower() == 'untrusted':
            continue
        seen.add(lid)
        out.append(l)
    return sorted(out, key=lambda l: (str(l.get('ts') or ''), l['id']))


def _gate(items, lines):
    """The lines waiting_on may count: the shared gate (trusted_lines)."""
    return trusted_lines(items, lines)


def _agents_for(norm, lines, t):
    """person -> the agents a live delegation from them stands for, and agents whose lines answer for them."""
    out = {}
    for d in norm.get('delegation', []):
        a = _s(field(d, 'to'))
        if actor_kind(a) != 'agent' or is_untrusted(d):
            continue
        for x in live_delegations(norm, a, t):
            p = _s(field(x, 'for') or field(x, 'actor'))
            if p:
                out.setdefault(p, set()).add(a)
    for l in lines:
        a, p = _s(l.get('actor')), _s(l.get('for'))
        if actor_kind(a) == 'agent' and actor_kind(p) == 'person':
            out.setdefault(p, set()).add(a)
    return out


def _sent_asks(norm, lines, them, person):
    """(item or line, kind, recipients, opening line id) for each open ask this person's side started."""
    def mine(x):
        return _s(x.get('actor')) in them or _s(x.get('for')) == person
    out = []
    for c in norm.get('card', []):
        asked = str(field(c, 'asked') or '')
        if asked in ('request', 'offer') and mine(c) and not is_untrusted(c) \
                and str(field(c, 'state') or '').lower() == 'open':
            to = _as_list(field(c, 'to')) or (_as_list(field(c, 'holder')) if asked == 'request' else [])
            out.append((c, asked, to, item_id(c)))
    for r in norm.get('request', []):
        st = str(field(r, 'state') or '').lower()
        if mine(r) and not is_untrusted(r) and not field(r, 'answered') \
                and st not in DONE_STATES | {'answered', 'taken', 'retracted'}:
            out.append((r, 'request', _as_list(field(r, 'to')), item_id(r)))
    for th in norm.get('thread', []):
        if mine(th) and field(th, 'to') and not is_untrusted(th) and not thread_view(th)['settled'] \
                and str(field(th, 'state') or '').lower() != 'retracted':
            out.append((th, 'message', _as_list(field(th, 'to')), item_id(th)))
    held = {item_id(x) for xs in norm.values() for x in xs if isinstance(x, dict)}
    for l in lines:
        if l.get('type') in ('rfg', 'escalate') and mine(l) and l['id'] not in held:
            b = l.get('body') if isinstance(l.get('body'), dict) else {}
            closed = any(x.get('type') in ('answer', 'decide') and l['id'] in _refs(x) for x in lines)
            if not closed:
                out.append((l, 'question', _as_list(b.get('to')), l['id']))
    return [(x, k, sorted({_s(r) for r in to if _s(r)} - them), o) for x, k, to, o in out]


def waiting_on(items, lines, actor, now=None):
    """The sender's side of what is owed: the open asks this person (or their agent) started, per
    recipient, each with its state (no_receipt · received · surfaced · acknowledged · answered), read
    from the item's `receipts` and from the trusted lines linked to it. Deterministic; honest-empty."""
    norm = normalize(items)
    t = now_or(now)
    person = _s(actor)
    out = {'actor': person or None, 'as_of': t.isoformat(timespec='seconds'), 'asks': [], 'waiting': {},
           'basis': ''}
    if actor_kind(person) != 'person':
        out['basis'] = 'no person named: waiting on is a person\'s, said by their agent'
        return out
    tl = _gate(items, lines)
    agents = _agents_for(norm, tl, t)
    them = {person} | agents.get(person, set())
    by_line = {l['id']: l for l in tl}

    def side(r):
        """Whether an actor (and the person its line answers for) is on recipient r's side."""
        rs = {r} | agents.get(r, set())
        if actor_kind(r) in ('person', 'agent'):
            return lambda a, f: a in rs or f == r
        return lambda a, f: bool(a) and a not in them and f != person     # a holon: anyone not the sender's side

    def body_of(l):
        return l.get('body') if isinstance(l.get('body'), dict) else {}

    for src, kind, recips, opening in _sent_asks(norm, tl, them, person):
        targets = {opening} | ({item_id(src)} if item_id(src) else set())
        since = _epoch(src.get('ts'))
        got = [dict(r, _for=_s((by_line.get(r.get('id')) or {}).get('for'))) for r in (src.get('receipts') or [])
               if isinstance(r, dict)]
        known = {r.get('id') for r in got}
        got += [{'id': l['id'], 'actor': l.get('actor'), 'ts': l.get('ts'), 'how': body_of(l).get('how'),
                 '_for': _s(l.get('for'))}
                for l in tl if l.get('type') == 'receive' and l['id'] not in known
                and targets & (_refs(l) | {body_of(l).get('of')})]
        got.sort(key=lambda x: (str(x.get('ts') or ''), str(x.get('id') or '')))
        replies = [e for e in _thread_lines(src) if e.get('id') not in targets] if kind == 'message' else []
        linked = [l for l in tl if l['id'] not in targets and l.get('type') not in NOT_A_LINK and targets & _refs(l)]
        rows = []
        for r in recips:
            on = side(r)
            state, at, by_ = 'no_receipt', None, None
            for rc in got:
                a = _s(rc.get('actor'))
                if not on(a, rc.get('_for')):
                    continue
                s = 'surfaced' if (a == r and actor_kind(r) == 'person') or rc.get('how') in IN_HAND else 'received'
                if WAIT_STATES.index(s) > WAIT_STATES.index(state):
                    state, at, by_ = s, rc.get('ts'), rc.get('id')
            for l in replies + linked:
                if not on(_s(l.get('actor')), _s(l.get('for'))):
                    continue
                l_t = _epoch(l.get('ts'))
                if since is not None and l_t is not None and l_t < since:
                    continue
                typ = l.get('type')
                answers = typ in ANSWER_TYPES or (typ == 'move' and body_of(l).get('move') != 'clarify') or \
                    (kind == 'message' and typ in ('say', None))
                s = 'answered' if answers else 'acknowledged'
                if WAIT_STATES.index(s) > WAIT_STATES.index(state):
                    state, at, by_ = s, l.get('ts'), l.get('id')
            rows.append({'to': r, 'state': state, 'words': WAIT_WORDS[state], 'since': at, 'line': by_})
        title = field(src, 'title') or field(src, 'text') or field(src, 'question') or (opening or '')[:8]
        voice = field(src, 'voice')
        out['asks'].append({'id': opening, 'kind': kind, 'holon': holon_of(src) or _s(src.get('holon')),
                            'title': str(title)[:120], 'ts': src.get('ts'), 'by': field(src, 'by'),
                            'why': _s(field(src, 'why'))[:200] or None, 'effort': effort_of(src),
                            'voice': voice if isinstance(voice, str) else None,
                            'recipients': rows, 'waiting': sum(1 for x in rows if x['state'] != 'answered'),
                            'missing': [] if rows else ['recipient']})
        for x in rows:
            if x['state'] != 'answered':
                out['waiting'][x['to']] = out['waiting'].get(x['to'], 0) + 1
    inf = float('inf')
    out['asks'].sort(key=lambda a: (_epoch(a['ts']) if _epoch(a['ts']) is not None else inf, str(a['id'])))
    n = len(out['asks'])
    out['basis'] = ('nothing this person asked is open' if not n else
                    f'{n} open ask{"s" if n != 1 else ""} this person started') + \
        ('; no lines given, so receipts and answers are read from the items alone'
         if not isinstance(lines, (list, tuple)) else '')
    return out


def render(result, names=None):
    """Markdown, plain voice."""
    names = names or {}
    es = (result or {}).get('entries') or []
    who = result.get('actor') or result.get('holon') or 'everyone'
    out = [f'# What is owed — {who}', '', f'*As of {result.get("as_of")}. Computed from the record.*', '']
    if not es:
        out.append('Nothing is owed.')
    words = {'past': 'past its by-when', 'near': 'due soon', 'waiting': 'waiting'}
    for e in es:
        hn = names.get(e['holon'], {}).get('name', e['holon'][:8] if e['holon'] else '?')
        age = f", {e['age_days']:g} days" if e.get('age_days') is not None else ''
        due = f", by {e['due']}" if e.get('due') else ''
        out.append(f"- **{e['kind']}** · {e['title']} · {e['holder'] or 'no holder yet'} · "
                   f"{words.get(e['status'], e['status'])}{due}{age} · [{hn}]")
    ps = result.get('proposals') or []
    if ps:
        out += ['', '## Proposals, not owed', '',
                '*An agent wrote these for a reason that came from text it read. A person decides.*', '']
        out += [f"- {p['kind']} · {p['title']} · from {p['proposer']}" for p in ps]
    return '\n'.join(out) + '\n'


def render_waiting(w):
    """Waiting on, in a plain voice: each open ask and where each recipient stands."""
    w = w or {}
    out = [f"# Waiting on — {w.get('actor') or 'no one named'}", '', f"*As of {w.get('as_of')}. {w.get('basis')}.*", '']
    for a in w.get('asks') or []:
        out.append(f"- **{a['kind']}** · {a['title']}" + (f" · by {a['by']}" if a.get('by') else ''))
        for r in a.get('recipients') or []:
            out.append(f"  - {r['to']}: {r['words']}" + (f" since {r['since']}" if r.get('since') else ''))
    return '\n'.join(out) + '\n'


def _load_lines(p):
    if os.path.islink(p):
        raise OSError(f'{p} is a symlink; a file is read only where it stands')
    out = []
    with open(p, encoding='utf-8') as f:
        for row in f:
            try:
                x = json.loads(row)
            except ValueError:
                continue
            if isinstance(x, dict):
                out.append(x)
    return out


def _main(argv=None):
    ap = argparse.ArgumentParser(description='What is owed, computed from folded items (JSON).')
    ap.add_argument('items', help='a JSON file of folded items (the output of record.py fold)')
    ap.add_argument('--actor'); ap.add_argument('--holon'); ap.add_argument('--now')
    ap.add_argument('--horizon', type=float, default=2.0, help='days ahead a by-when counts as near')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--receipts', action='store_true', help='also list lines that crossed and have no Receipt')
    ap.add_argument('--receipt-hours', type=float, default=RECEIPT_HOURS,
                    help='hours a line waits for its Receipt before it is owed (default %(default)s)')
    ap.add_argument('--home', default=None, help='the home\'s holon id: every other holon is a cell')
    ap.add_argument('--people', action='append', default=None,
                    help='one of this holon\'s own people (person:x); repeat, or separate with commas')
    ap.add_argument('--waiting-on', action='store_true',
                    help='the sender\'s side: what the actor asked, and where each recipient stands')
    ap.add_argument('--lines', help='the trusted lines (JSONL), for --waiting-on')
    a = ap.parse_args(argv)
    try:
        if os.path.islink(a.items):
            raise OSError(f'{a.items} is a symlink; a file is read only where it stands')
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
        lines = _load_lines(a.lines) if a.lines else None
    except (OSError, ValueError) as e:
        print(f'owed: cannot read input: {e}', file=sys.stderr); return 2
    if a.waiting_on:
        w = waiting_on(items, lines, a.actor, a.now)
        print(json.dumps(w, indent=1, ensure_ascii=False, sort_keys=True) if a.json else render_waiting(w))
        return 0
    people = {p.strip() for x in (a.people or []) for p in x.split(',') if p.strip()} or None
    r = owed(items, a.actor, a.holon, a.now, a.horizon, receipts=a.receipts, receipt_hours=a.receipt_hours,
             home=a.home, people=people)
    print(json.dumps(r, indent=1, ensure_ascii=False) if a.json else render(r, holon_names(normalize(items))))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
