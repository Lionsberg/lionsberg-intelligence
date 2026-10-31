#!/usr/bin/env python3
"""deal.py — The Deal: the few cards that need this player now, sized to the time they have.

    deal(items, schedule_report, actor, minutes_available, room=None, now=None, holons=None) -> dict
    render(deal) -> Markdown, opening "Here's the deal."
    render_paper(deal) -> a printable card with tick boxes

Across every holon the items come from, in this order:

  0. what rises first, before float, stake or groups (rising): a request addressed to this person
     or their agents and not yet answered (a `request` or `rfg` to them, a `say` with them in `to`,
     a `commit` with them as committee, an `escalate` or `rfg` to a holon they keep), newest first,
     each with why "asked of you" and rose true; then an open pain sighted in a holon they belong
     to that needs a response (sightings.lifecycle), why "a pain needs a response". A risen card is
     not an interruption: it is first at the next sitting; the gate and the emergency rule decide
     any wake. The why a risen card had before it rose is kept as `because`. When the fold's trust
     map can be reached, only what it marks trusted rises; a ladder question rises only when its
     line is trusted (among the lines given, or so marked by the map), never on the ladder's word.
  1. what is owed of this actor: commitments past or near their by-when, requests to answer,
     expired claims (owed.py)
  2. threads addressed to them, or that they spoke in, whose last line is not theirs
  3. decisions waiting on them: decision cards they hold, and decisions waiting for their ratify
  4. ready cards, ranked by leverage

and always, last, the standing question: "What did we miss that matters to you most?"

THE LEVERAGE RULE (named assumptions, tuned by evidence, never by feeling):

  leverage = (urgent work moved) ÷ (own minutes)
             × 1.5 if on the critical path × 1.5 if someone it touches is in the room

  urgent work moved = own minutes × urgency(own float) + Σ downstream minutes × urgency(their float)
  urgency(float)    = 1 / (1 + float/3) up to 14 days of float, 0 beyond; unknown float counts 0.25

  So leverage is urgent work moved per minute of the actor's own. Downstream is every card after
  this one, by successor links and by other cards' predecessor links. Ties go to the cheaper card.
  Two cases, both at float 0, each freeing 120 minutes downstream:
      a 5-minute card:  (5 + 120) ÷ 5   = 25.0
      a 60-minute card: (60 + 120) ÷ 60 = 3.0     the smaller card ranks higher, never lower
  With nothing downstream both score 1.0 (urgency alone), and the 5-minute card comes first.

Authority: a person may be dealt anything. An agent is dealt only what a live delegation covers
(the act's type and the card's holon), and never a person-only act (every type types.json marks
human_only, and always commit, ratify, decide, kept, witness, publish, and accepting a request),
nor a decision or review card. A request waiting on its person may be dealt to the agent as a
proposal to draft, when its delegation covers `propose`: the agent proposes acceptance, the person
accepts. Lines an agent wrote for a reason that came from untrusted text are never dealt as owed.
Released and declined cards are never dealt: they have left the board, as the schedule drops them.
A ratify is recommended only when what was decided is written (and by whom), any conditions it
names are marked met, and no open thread contests it; otherwise the recommendation is "Read the
thread first", with the reason.
A milestone is never dealt as work to take. A card is ready only when every held predecessor is
done, read from both directions of the links. A decision or review card handed to an agent is
dealt to the person that agent serves. A question (`rfg` or `escalate`) that climbed to a holon is
dealt to its keeper as "A question for you:" (owed once past its by-when). A sighting not yet
triaged is dealt to the keeper of its holon as "Pass this on to the circle?" (an agent never elevates).
A line that crossed to another holon and has had no Receipt (owed.py, receipts) is dealt to the
person who sent it as "No Receipt yet from <addressee> for <title>, <age>", asking nothing to
confirm: "Ask again" (a `say` to the addressee, drafted on the card as `draft`, sent only by a
person) or "Let it go". With `fewer` it is left to the agent.
The bodies' cards (DESIGN-BODIES §3), for the person the bodies answer for: review a handoff (and a
stale claim that left one), a clone past a day, a clone quiet three hours, close-out, two claims on
the desk, and "give this to a body" for long research or draft work. With `fewer`, handoffs that
ask for no yes are left to the agent, past-a-day waits for close-out, and nothing is offered to a body.

The dial (`fewer`, the person's word, four steps; True is one step): as set · fewer (at most two
cards; handoffs that ask for no yes left to the agent; past-a-day at close-out; nothing offered to
a body) · much fewer (one card) · only what always passes (a person waiting now, an irreversible
yes, a fault). Every card carries what attention.gate reads: by, who_waits, always_passes, heavy.

Sizing: first fit, in order: each card is taken if it fits the minutes left; the rest are counted
under "beyond" ({count, minutes}), and the first twenty of them are carried as `beyond.cards`, in the
order the dealer ranked them and framed as dealt cards are (numbered on after the dealt ones), so
the next hand can be dealt from them without dealing again. The cap and the budget decide what is
dealt; beyond is what was ranked and not dealt.
The minutes dealt never exceed the minutes available. The standing question costs no minutes.

  python3 -I deal.py ITEMS.json --actor person:x --minutes 20 [--room a,b] [--schedule S.json]
                    [--lines LINES.jsonl] [--home ID] [--now ISO] [--json | --paper]
"""
import argparse
import json
import os
import sys
import unicodedata

try:
    from gamecore import (normalize, field, links, sched_map, path_sets, now_or, days_between, item_id,
                          holon_of, holon_names, may_act, minutes_of, hm, DONE_STATES,
                          STANDING_QUESTION, is_untrusted, card_kind, actor_kind,
                          live_delegations, covers, HUMAN_ONLY_KINDS, parse_time)
    import owed as owed_mod
    import attention as attention_mod
    import subscriptions as subscriptions_mod
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, sched_map, path_sets, now_or, days_between, item_id,
                          holon_of, holon_names, may_act, minutes_of, hm, DONE_STATES,
                          STANDING_QUESTION, is_untrusted, card_kind, actor_kind,
                          live_delegations, covers, HUMAN_ONLY_KINDS, parse_time)
    import owed as owed_mod
    import attention as attention_mod
    import subscriptions as subscriptions_mod
try:
    import sightings as sightings_mod
except ImportError:                       # the pain fallback reads the links itself
    sightings_mod = None

HORIZON_D = 14.0       # a successor with more float than this frees nothing yet
HALF_D = 3.0           # three days of float counts half
UNKNOWN_U = 0.25       # an unknown float counts a quarter
CRITICAL_X = 1.5
ROOM_X = 1.5
DEFAULT_CARD_MIN = 15.0
BEYOND_CARDS = 20     # the ranked rest carried for the next hand, at most
READY_STATES = {'ready', 'taken', 'returned', ''}   # 'open' is a request or offer: owed, not dealt
RULE = ('urgent work moved (own + downstream minutes, each × urgency of its float) ÷ own minutes, '
        '× 1.5 on the critical path, × 1.5 when someone it touches is in the room; '
        'urgency = 1/(1+float/3) to 14 days, 0 beyond, 0.25 unknown; ties to the cheaper card')
NUM = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight',
       9: 'nine', 10: 'ten'}


def urgency(f):
    if f is None:
        return UNKNOWN_U
    try:
        f = max(0.0, float(f))
    except (TypeError, ValueError):
        return UNKNOWN_U
    return 0.0 if f > HORIZON_D else 1.0 / (1.0 + f / HALF_D)


def _num(n):
    return NUM.get(n, str(n))


def successor_map(cards):
    """card id -> direct successor ids, from both directions of the links."""
    succ = {i: set(links(c, 'successor')) for i, c in cards.items()}
    for i, c in cards.items():
        for p in links(c, 'predecessor'):
            succ.setdefault(p, set()).add(i)
    return succ


def _live(c):
    """Still work to do. Done, delivered, kept, released and declined cards are not."""
    return str(field(c, 'state') or '').lower() not in DONE_STATES


def near_critical(cards, sm):
    """card id -> (minutes of near-critical work downstream, downstream ids)."""
    succ = successor_map(cards)
    live = {i: c for i, c in cards.items() if _live(c)}
    out = {}
    for i in live:
        seen, stack = {i}, list(succ.get(i, ()))
        while stack:
            s = stack.pop()
            if s in live and s not in seen:
                seen.add(s); stack.extend(succ.get(s, ()))
        seen.discard(i)
        tot = sum(minutes_of(live[s], DEFAULT_CARD_MIN) * urgency(_tf(s, live[s], sm)) for s in seen)
        out[i] = (round(tot, 1), sorted(seen))
    return out


def _tf(cid, card, sm):
    s = sm.get(cid) or {}
    for k in ('TF', 'tf', 'total_float'):
        if s.get(k) is not None:
            return s[k]
    return field(card, 'TF')


def predecessor_map(cards):
    """card id -> direct predecessor ids, from both directions of the links."""
    pred = {i: set(links(c, 'predecessor')) for i, c in cards.items()}
    for i, c in cards.items():
        for s in links(c, 'successor'):
            pred.setdefault(s, set()).add(i)
    return pred


def _ready(cid, card, cards, preds=None):
    """True when every held predecessor is done, read from both directions of the links.
    Predecessors not held are not counted."""
    ps = (preds or predecessor_map(cards)).get(cid, set(links(card, 'predecessor')))
    for p in ps:
        if p in cards and _live(cards[p]):
            return False
    return True


def _touches_room(card, cards, succ, room):
    if not room:
        return []
    who = set()
    for s in succ.get(item_id(card), ()):
        h = field(cards.get(s), 'holder')
        if h in room:
            who.add(h)
    for k in ('requester', 'witness', 'actor'):
        v = field(card, k)
        if v in room:
            who.add(v)
    return sorted(who)


def _titles(ids, cards, n=2):
    ts = [str(field(cards[i], 'title') or i[:8]) for i in ids if i in cards][:n]
    return ', '.join(f'"{t}"' for t in ts)


def deal(items, schedule_report, actor, minutes_available, room=None, now=None, holons=None,
         questions=None, sightings=None, bodies=None, fewer=False, closeout=False, lines=None,
         home=None, people=None, receipts=True, fold=None):
    """The Deal for one actor, across every holon in the items. `questions` from ladder.questions,
    `sightings` from sightings.triage, when the caller has the raw lines. `lines` are the record's
    trusted lines (what rises first reads them; without them, the fold's items alone), and `fold`
    the fold whole when `items` were normalized from it (its trust map gates the lines again).
    `home` and `people` are owed.py's, for the receipt cards (people defaults to the actor)."""
    norm = normalize(items)
    t = now_or(now)
    room = [r for r in (room or []) if isinstance(r, str) and r and r != actor]
    try:
        budget = max(0.0, float(minutes_available or 0))
    except (TypeError, ValueError):
        budget = 0.0
    sm = sched_map(schedule_report)
    crit, system = path_sets(schedule_report)
    names = holon_names(norm, holons)
    cards = {item_id(c): c for c in norm.get('card', []) if item_id(c)}
    for i, c in cards.items():
        if field(c, 'critical'):
            crit.add(i)
        if field(c, 'system_critical'):
            system.add(i)
    succ = successor_map(cards)
    preds = predecessor_map(cards)
    nc = near_critical(cards, sm)
    threads = {item_id(x): x for x in norm.get('thread', [])}

    def hname(h):
        return names.get(h, {}).get('name') or (h[:8] if h else '?')

    def lev(cid, card, in_room):
        own = minutes_of(card, DEFAULT_CARD_MIN)
        v = own * urgency(_tf(cid, card, sm)) + nc.get(cid, (0.0, []))[0]
        v *= CRITICAL_X if cid in crit else 1.0
        v *= ROOM_X if in_room else 1.0
        return round(v / max(1.0, own), 2)

    def unlocks(cid):
        frees, down = nc.get(cid, (0.0, []))
        if not down:
            return 'nothing waits on it yet'
        names_ = _titles(down, cards)
        return f'frees {hm(frees)} of near-critical work' + (f', starting with {names_}' if names_ else '')

    cands = []

    # 1–3a: what is owed (commitments, requests, threads, ratifies, claims) — never untrusted lines
    step = attention_mod.fewer_step(fewer)        # the four-step dial: as set · fewer · much fewer · only what always passes
    fewer = step >= 1
    bl = (bodies or {}).get('bodies') if isinstance(bodies, dict) else (bodies or [])
    ow = owed_mod.owed(norm, actor=actor, now=t, holons=holons, questions=questions, bodies=bl)
    act_of = {'commitment': 'kept', 'request': 'answer', 'thread': 'say', 'ratify': 'ratify', 'decide': 'decide',
              'claim': 'claim', 'question': 'decide', 'handoff': 'witness', 'receipt': 'say'}
    for e in ow['entries']:
        if not may_act(norm, actor, act_of.get(e['kind'], e['kind']), e['holon'], t):
            continue
        if e['kind'] == 'handoff' and fewer and not e.get('asks_yes', True):
            continue                      # "fewer": the agent judges handoffs that ask for no yes
        c = _frame_owed(e, norm, cards, succ, nc, threads, room, hname, unlocks)
        c['by'] = e.get('due')
        cands.append(c)

    # the bodies' own cards, for the person they answer for
    if actor_kind(actor) == 'person':
        cands.extend(body_cards(bl, (bodies or {}).get('desk') if isinstance(bodies, dict) else None,
                                actor, fewer, closeout, cards, hname, nc, t, norm))

    # questions that climbed to this actor's holon and wait on them, not yet past (past ones are owed)
    for q in questions or []:
        if isinstance(q, dict) and q.get('state') == 'open' and not q.get('past') and q.get('holder') == actor \
                and may_act(norm, actor, 'decide', q.get('to') or '', t):
            cands.append(_frame_question(q, hname, 'decision'))
    # sightings not yet triaged, for the keeper of the holon they were seen in
    for sg in sightings or []:
        if isinstance(sg, dict) and sg.get('status') == 'new' and names.get(sg.get('holon'), {}).get('keeper') == actor \
                and may_act(norm, actor, 'elevate', sg.get('holon') or '', t):
            cands.append(_frame_sighting(sg, hname))

    # an agent may propose acceptance of a request waiting on its person, never accept it
    if actor_kind(actor) == 'agent':
        for dlg in live_delegations(norm, actor, t):
            person = field(dlg, 'for') or field(dlg, 'actor')
            for e in owed_mod.owed(norm, actor=person, now=t, holons=holons)['entries']:
                if e['kind'] == 'request' and covers([dlg], 'propose', e['holon']):
                    cands.append(_base('owed', e['id'], e['holon'], hname,
                                       f'"{e["title"]}" waits on {person}. Draft a proposal that they accept it?',
                                       ['Draft the proposal for them to decide', 'Leave it to them'], 0,
                                       'only they can accept; a drafted proposal saves them the time',
                                       'they can accept in one line', 3, rank=1, kind='propose'))

    # 3b: decision cards held by the actor; 4: ready cards
    for cid, c in cards.items():
        if not _live(c) or is_untrusted(c):
            continue
        st = str(field(c, 'state') or '').lower()
        holder = field(c, 'holder')
        kind = card_kind(c)
        if st not in READY_STATES or not _ready(cid, c, cards, preds):
            continue
        if kind == 'milestone':
            continue                      # a milestone is a marker reached, never work to take
        if kind in HUMAN_ONLY_KINDS and actor_kind(holder) == 'agent':
            # a decision or review handed to an agent still belongs to the person it serves
            served = {field(d, 'for') or field(d, 'actor') for d in live_delegations(norm, holder, t)}
            holder = actor if actor in served else holder
        if holder and holder != actor:
            continue
        if not holder and kind == 'decision':
            continue                      # a decision with no holder is not yet anyone's to make
        if not may_act(norm, actor, 'claim', holon_of(c), t, kind):
            continue
        who = _touches_room(c, cards, succ, room)
        L = lev(cid, c, bool(who))
        cands.append(_frame_card(cid, c, kind, L, who, cid in crit, cid in system, room, hname,
                                 unlocks(cid), nc.get(cid, (0.0, []))[0]))

    # a line that crossed and has no Receipt, for the person who sent it (never with "fewer")
    n_receipts = 0
    if receipts and not fewer and actor_kind(actor) == 'person':
        rc = receipt_cards(norm, actor, t, holons, home, people, hname)
        rc = [c for c in rc if may_act(norm, actor, act_of['receipt'], c['holon'], t)]
        n_receipts = len(rc)
        cands.extend(rc)

    # what rises first: asked of this person, then a pain that needs a response
    rs = rising(items, actor, lines, t, holons, questions, fold)
    by_id = {}
    for x in cands:
        by_id.setdefault(x['id'], x)
    ask_act = {'request': 'answer', 'request_item': 'answer', 'thread': 'say', 'say': 'say',
               'commitment': 'say', 'question': 'decide'}
    for r in rs['requests']:
        x = by_id.get(r['id'])
        if x is None:
            x = _frame_ask(r, norm, cards, succ, nc, threads, room, hname, unlocks, t, questions)
            if x is None or not may_act(norm, actor, ask_act.get(r['kind'], 'say'), x['holon'], t):
                continue
            cands.append(x)
            by_id[x['id']] = x
        x['_tier'], x['_epoch'] = 0, r['epoch']
    for p in rs['pains']:
        if not may_act(norm, actor, 'say', p.get('holon') or '', t):
            continue
        old = by_id.get(p['id'])
        if old is not None:
            cands.remove(old)             # its triage card gives way; the pain card keeps its "Pass it on"
        x = _frame_pain(p, hname, keeper=old is not None and old.get('kind') == 'sighting')
        x['_tier'], x['_epoch'] = 1, p['epoch']
        cands.append(x)
        by_id[x['id']] = x

    order = {'owed': 0, 'thread': 1, 'decision': 2, 'ready': 3}
    for x in cands:                       # what the attention gate reads on every card
        x.setdefault('by', field(cards.get(x['id']), 'by') if x['id'] in cards else None)
        x.setdefault('who_waits', 'now' if 'in the room' in x.get('why', '') else None)   # a person waiting now
        x['always_passes'] = bool(x.get('always_passes') or x.get('who_waits') == 'now')
        x['heavy'] = x['section'] == 'decision' and x.get('kind') in ('decision', 'ratify', 'decide', 'question')
        tier = x.get('_tier')
        x['rose'] = tier in (0, 1)
        if x['rose']:
            why = ASKED if tier == 0 else PAIN_WHY
            if x.get('why') and x['why'] != why:
                x['because'] = x['why']
            x['why'] = why

    def rank(x):
        tier = x.get('_tier', 2)
        if tier < 2:                      # risen: newest first, then id
            e = x.get('_epoch')
            return (tier, -e if e is not None else float('inf'), x['id'])
        return (2, order[x['section']], x.get('_rank', 0), -x['leverage'], x['minutes'], x['id'])
    cands.sort(key=rank)
    if step == 3:
        cands = [x for x in cands if x['always_passes']]
    cap = {1: 2, 2: 1, 3: 1}.get(step)

    dealt, rest, spent, beyond_m = [], [], 0.0, 0.0
    for x in cands:
        if (cap is None or len(dealt) < cap) and spent + x['minutes'] <= budget + 1e-9:
            spent += x['minutes']; dealt.append(x)
        else:
            rest.append(x); beyond_m += x['minutes']
    for n, x in enumerate(dealt + rest[:BEYOND_CARDS], 1):
        x['n'] = n                        # the next hand is numbered on from the dealt one
    for x in cands:
        for k in ('_rank', '_tier', '_epoch'):
            x.pop(k, None)

    owed_to_you = []                       # what others owe this actor: said, not dealt
    by_id = {item_id(i): i for k in ('commitment', 'request') for i in norm.get(k, [])}
    for e in owed_mod.owed(norm, now=t, holons=holons)['entries']:
        it = by_id.get(e['id'])
        if it is None or e['holder'] == actor:
            continue
        mine = actor in (field(it, 'witness'), field(it, 'to')) if e['kind'] == 'commitment' \
            else field(it, 'actor') == actor
        if mine:
            owed_to_you.append({'kind': e['kind'], 'id': e['id'], 'holon': e['holon'], 'title': e['title'],
                                'holder': e['holder'], 'status': e['status'], 'due': e['due']})

    as_of = {}
    if isinstance(schedule_report, dict) and isinstance(schedule_report.get('as_of'), dict):
        as_of = dict(schedule_report['as_of'])
    for h in holons or []:
        if isinstance(h, dict) and h.get('id') and isinstance(h.get('as_of'), dict):
            as_of.setdefault(h['id'], h['as_of'].get('event'))
    risen = [x for x in dealt + rest if x.get('rose')]
    return {'actor': actor, 'minutes_available': budget, 'minutes_dealt': round(spent, 1), 'room': room,
            'generated_at': t.isoformat(timespec='seconds'), 'opening': "Here's the deal.",
            'cards': dealt,
            'beyond': {'count': len(rest), 'minutes': round(beyond_m, 1), 'cards': rest[:BEYOND_CARDS]},
            'owed_to_you': owed_to_you, 'proposals': len(ow.get('proposals') or []),
            'fewer': attention_mod.FEWER_STEPS[step],
            'question': STANDING_QUESTION, 'rule': RULE, 'as_of': as_of,
            'newest_line': rs['newest_line'],             # the newest line this Deal saw: {id, ts}, or None
            'receipt_cards': n_receipts,
            'risen': {'requests': sum(1 for x in risen if x['why'] == ASKED),
                      'pains': sum(1 for x in risen if x['why'] == PAIN_WHY),
                      'pain_basis': rs['pain_basis'], 'lines_basis': rs['lines_basis']}}


def _base(section, id_, holon, hname, question, options, rec_i, why, unlocks, minutes, leverage=0.0,
          whole=False, rank=0, kind=''):
    options = options[:3]
    return {'section': section, 'kind': kind, 'id': id_, 'holon': holon, 'holon_name': hname(holon),
            'question': question, 'options': options, 'recommendation': options[rec_i], 'why': why,
            'unlocks': unlocks, 'minutes': float(minutes), 'leverage': leverage, 'whole_waits': whole,
            '_rank': rank}


HAZARD_KINDS = {'hazard', 'threat', 'danger', 'risk', 'harm'}


def _frame_question(q, hname, section, rank=0):
    frm = hname(q.get('from_holon') or '')
    text = str(q.get('question') or '').strip() or 'a decision beyond its remit'
    head = 'A question for you:' if q.get('type') == 'rfg' else 'A decision for you:'
    opts = (['Answer it', 'Decide it here', 'Pass it to the wider circle'] if q.get('type') == 'rfg'
            else ['Decide it here', 'Ask for more first', 'Pass it to the wider circle'])
    why = (f'{frm} sent it to you, the nearest circle able to take it'
           + (f'; it was due {q.get("by")}' if q.get('past') else f'; by {q.get("by")}' if q.get('by') else ''))
    return _base(section, q.get('id'), q.get('to') or '', hname, f'{head} "{text}"', opts, 0, why,
                 f'{frm} can move', 10, rank=rank, kind='question')


def _frame_sighting(sg, hname):
    kind = str(sg.get('kind') or 'sighting')
    hazard = kind.lower() in HAZARD_KINDS
    # plain words for a tired person; the acts stay by position (0 elevate, 1 hold, 2 the last, a say)
    opts = ['Pass it on', 'Keep it here', 'Not yet']
    why = ('a danger one person sees is a danger for everyone near it' if hazard
           else 'nothing in it reaches beyond here yet; keeping it here keeps it in view')
    seen = 'Someone saw a danger' if hazard else 'Someone saw this'
    return _base('decision', sg.get('id'), sg.get('holon') or '', hname,
                 f'Pass this on to the circle? {seen}: "{str(sg.get("text") or "")[:90]}"', opts, 0 if hazard else 1,
                 why, 'what the circle around you knows', 3, kind='sighting')


GIVE_KINDS = {'research', 'draft'}
GIVE_MIN = 60.0


def body_cards(bl, desk, actor, fewer, closeout, cards, hname, nc, t, norm):
    """The bodies' cards (DESIGN-BODIES §3): a clone past a day · quiet three hours · close-out ·
    two claims on the desk · give this to a body. (The handoff card and the stale-claim card come
    from what is owed.) "Fewer" raises past-a-day only at close-out and offers no give-to-a-body."""
    mine = [b for b in bl or [] if isinstance(b, dict) and b.get('for') == actor]
    out = []
    for b in mine:
        name, fl = b.get('name') or 'A body', b.get('flags') or []
        if 'past_day' in fl and (closeout or not fewer):
            steady = 'quiet' not in fl and 'stale' not in fl
            out.append(_base('decision', f"body:{b.get('actor')}:past_day", b.get('holon') or '', hname,
                             f'{name} has run past a day. What now?',
                             ['Let it finish tonight', 'Hold it until Monday', 'Close it now'], 0 if steady else 2,
                             'it is writing steadily' if steady else 'it has gone quiet; closing keeps nothing open overnight',
                             'nothing is left running overnight without a line that says why', 1, kind='body'))
        if 'quiet' in fl and 'stale' not in fl:
            out.append(_base('decision', f"body:{b.get('actor')}:quiet", b.get('holon') or '', hname,
                             f'{name} has written nothing for three hours.', ['Ask it', 'Hold it', 'Close it'], 0,
                             'it gave no reason; asking costs one line', 'the body moves or rests with its why', 1,
                             kind='body'))
    working = [b for b in mine if b.get('state') in ('claimed', 'working')]
    if closeout and mine:
        held = sum(1 for b in mine if b.get('state') == 'hold')
        waiting = sum(1 for b in mine if b.get('handoff') and not b.get('reviewed'))
        out.append(_base('decision', 'body:closeout', mine[0].get('holon') or '', hname,
                         f'Close out the day? {len(working)} working, {held} resting, {waiting} finished and waiting for you.',
                         ['Close out now', 'Leave them working tonight', 'Close out at the usual hour'],
                         0 if working else 2,
                         'every body ends finished or resting, with its reason' if working else 'every body is at rest already',
                         'tomorrow starts clean, with each body\'s reason written down', 2, kind='body'))
    if desk and desk.get('collision'):
        first = (desk.get('claims') or [{}])[0].get('actor')
        out.append(_base('decision', 'body:desk', '', hname, 'Two bodies asked to lead the work. The first leads until you say.',
                         [f'Keep it with {first}', 'Give it to the second'], 0, 'the first claim stands until you say',
                         'one body leads at a time', 1, kind='body'))
    if not fewer:
        has_agent = any(field(d, 'for') == actor or field(d, 'actor') == actor for d in norm.get('delegation', [])
                        if str(field(d, 'state') or 'live') == 'live')
        best = None
        for cid, c in cards.items():
            if field(c, 'holder') == actor and _live(c) and card_kind(c) in GIVE_KINDS \
                    and minutes_of(c, 0) >= GIVE_MIN and str(field(c, 'state') or '').lower() in READY_STATES:
                if best is None or minutes_of(c, 0) > minutes_of(best[1], 0):
                    best = (cid, c)
        if best and has_agent:
            cid, c = best
            out.append(_base('ready', f'body:give:{cid}', holon_of(c), hname,
                             f'Give "{field(c, "title")}" to a body? ({hm(minutes_of(c, 0))})',
                             ['Give it to a body (the cost is said first)', 'Do it myself', 'Not now'], 0,
                             f'it is {card_kind(c)} work of {hm(minutes_of(c, 0))} that a body can carry while you play',
                             'your minutes go to what only you can do', 1, kind='body'))
    return out


def _frame_owed(e, norm, cards, succ, nc, threads, room, hname, unlocks):
    k, title, h = e['kind'], e['title'], e['holon']
    if k == 'handoff':
        name, task = e.get('body') or 'A body', e.get('task') or 'its task'
        mins = e['minutes']
        late = (e.get('age_days') or 0) >= 1
        if e.get('stale'):
            q = f'{name} stopped without closing. It left a handoff · {hm(mins)}. Read it?'
            opts = ['Read it now', 'Let your agent judge it', 'Put it in my Deal']
        else:
            q = f'{name} finished "{str(task)[:80]}". Read what it found? · {hm(mins)}'
            opts = ['Read it now', 'Put it in my Deal', 'Let your agent judge it']
        if e.get('asks_yes', True):
            opts = [o for o in opts if o != 'Let your agent judge it']
        c = _base('owed', e['id'], h, hname, q, opts, 0, 'it asks for your yes' if e.get('asks_yes', True)
                  else 'it asks for no yes; reading it keeps you in the work', 'the handoff dries to full ink', mins,
                  rank=1, kind='handoff')
        c['eyebrow'] = 'WAITING A DAY' if late else 'HANDOFF · YOUR AGENT · REVIEW'
        return c
    if k == 'question':
        return _frame_question(dict(e, id=e['id'], question=e['title'], to=e['holon'], past=True, by=e['due']),
                               hname, 'owed', rank=0)
    if k == 'receipt':
        return _frame_receipt(e, hname)
    age = e.get('age_days')
    agew = f'{age:g} days' if age is not None else 'a while'
    rank = 0 if e['status'] == 'past' else 1
    if k == 'commitment':
        it = next((c for c in norm.get('commitment', []) if item_id(c) == e['id']), {})
        cid = field(it, 'card')
        card = cards.get(cid) if isinstance(cid, str) else None
        done = card is not None and not _live(card)
        if e['status'] == 'past':
            q = f'Your commitment "{title}" was due {e["due"]}. Where does it stand?'
            opts = ['Kept: say so, and the witness can verify', 'Renegotiate: name a new by-when',
                    'Release it, with one line on why']
            ri, why = (0, 'the card is done; only the claim is missing') if done else \
                (1, 'a new date said now costs less than a quiet miss')
        else:
            q = f'"{title}" is due {e["due"]}. Still on track?'
            opts = ['On track', 'Renegotiate now, while there is float', 'Release it']
            ri, why = (0, 'nothing in the record says otherwise; one key confirms it')
        un = unlocks(cid) if cid in cards else 'the witness can verify and the chain holds'
        return _base('owed', e['id'], h, hname, q, opts, ri, why, un, e['minutes'], rank=rank, kind=k)
    if k == 'request':
        it = next((r for r in norm.get('request', []) if item_id(r) == e['id']), {})
        asker = field(it, 'actor') or 'someone'
        size = minutes_of(it, 0)
        q = f'{asker} asks: "{title}". Your answer?'
        opts = ['Accept it: you become its holder', 'Offer something else', 'Decline, with thanks']
        ri, why = (0, f'it asks {hm(size)}, which fits') if 0 < size <= 30 else \
            (1, 'an offer sized to your week keeps it honest' if size else 'its size is not said; an offer can name one')
        if asker in room:
            why += '; they are in the room'
        return _base('owed', e['id'], h, hname, q, opts, ri, why, 'the asker knows where they stand',
                     e['minutes'], rank=rank, kind=k)
    if k == 'claim':
        q = f'Your claim on "{title}" ran out on {e["due"]}. Keep it or let it go?'
        opts = ['Renew the claim with a new date', 'Release the card for someone else']
        return _base('owed', e['id'], h, hname, q, opts, 1, 'a released card can be dealt to someone free now',
                     'the card is free to be taken', e['minutes'], rank=rank, kind=k)
    if k == 'thread':
        th = threads.get(e['id'], {})
        v = owed_mod.thread_view(th)
        ls = [x for x in (field(th, 'lines') or []) if isinstance(x, dict)]
        last = (max(ls, key=lambda x: str(x.get('ts') or '')).get('text') if ls else '') or ''
        excerpt = (' Last: ' + str(v['last_actor']) + ': "' + str(last)[:90] + '"') if last else ''
        q = f'The thread on "{title}" waits for your line.{excerpt}'
        opts = ['Reply now', 'Settle it as it stands', 'Hand it to someone else']
        why = f'{agew} without your line'
        r = rank
        if v['last_actor'] in room:
            why, r = f'{v["last_actor"]} is in the room now', -1     # a person waiting now: it always passes
        return _base('thread', e['id'], h, hname, q, opts, 0, why, 'the thread can move', e['minutes'],
                     rank=r, kind=k)
    d = next((x for x in norm.get('decision', []) if item_id(x) == e['id']), {})
    if k == 'decide':
        opts = field(d, 'options')
        if not (isinstance(opts, list) and len(opts) >= 2 and all(isinstance(o, str) for o in opts)):
            opts = ['Decide as proposed', 'Decide with one change', 'Not mine to decide: hand it on']
        rec = field(d, 'recommend')
        ri = rec if isinstance(rec, int) and 0 <= rec < min(3, len(opts)) else 0
        why = str(field(d, 'why') or ('as the proposal recommends' if isinstance(rec, int)
                                      else 'it was put to you by name; nothing in the record contests it'))
        return _base('decision', e['id'], h, hname, f'Decide: "{title}"?', opts, ri, why,
                     'the proposal becomes a decision the holon can act on', e['minutes'], rank=-1, kind='decide')
    # ratify
    def anchors(th):
        a = field(th, 'anchor')
        return set(links(th, 'anchored_to')) | ({a} if isinstance(a, str) else set(a or []) if isinstance(a, list) else set())
    contesting = [th for th in threads.values()
                  if e['id'] in anchors(th) and not owed_mod.thread_view(th)['settled']]
    written = bool(field(d, 'decision') or field(d, 'text')) and bool(field(d, 'decided_by') or field(d, 'actor'))
    conds = field(d, 'conditions')
    conds_met = not conds or bool(field(d, 'conditions_met'))
    opts = ['Confirm', 'Read the thread first', 'Return it with one change']
    if contesting:
        ri, why = 1, f'{len(contesting)} open thread{"s" if len(contesting) != 1 else ""} on it {"are" if len(contesting) != 1 else "is"} not settled'
    elif not written:
        ri, why = 1, 'what was decided, or who decided it, is not written in full'
    elif not conds_met:
        ri, why = 1, 'its conditions are not yet marked met'
    else:
        ri, why = 0, 'what was decided is written, its conditions are met, and no open thread contests it'
    return _base('decision', e['id'], h, hname, f'Confirm "{title}"?', opts, ri, why,
                 'the decision binds and its cards can be dealt', e['minutes'], rank=-1, kind='ratify')


def _frame_card(cid, c, kind, L, who, critical, whole, room, hname, unlocks, frees):
    title = str(field(c, 'title') or cid[:8])
    mins = max(1.0, minutes_of(c, DEFAULT_CARD_MIN))
    h = holon_of(c)
    if critical and frees:
        why = f'on the critical path; it {unlocks}'
    elif critical:
        why = 'on the critical path'
    elif frees:
        why = f'it {unlocks}'
    else:
        why = 'nothing near-critical waits on it; it is cheap to clear' if mins <= 15 else \
            'nothing near-critical waits on it yet'
    if who:
        why += f'; {", ".join(who)} {"is" if len(who) == 1 else "are"} in the room'
    if kind == 'decision':
        q = field(c, 'question') or (title if title.endswith('?') else f'Decide: {title}.')
        opts = field(c, 'options')
        if isinstance(opts, list) and len(opts) >= 2 and all(isinstance(o, str) for o in opts):
            opts = opts[:3]
        else:
            opts = ['Decide now', 'Gather one more input first', 'Hand it to someone better placed']
        rec = field(c, 'recommend')
        ri = rec if isinstance(rec, int) and 0 <= rec < len(opts) else 0
        if isinstance(rec, int) and field(c, 'why'):
            why = str(field(c, 'why'))
        return _base('decision', cid, h, hname, str(q), opts, ri, why, unlocks, mins, L, whole, kind=kind)
    other = f'Hand it to {room[0]}' if room else 'Hand it to someone else'
    if str(field(c, 'state') or '').lower() == 'taken':
        q = f'"{title}" is yours. Do it now? ({hm(mins)})'
        opts = ['Do it now', other, 'Not this week: release it']
    else:
        q = f'Take "{title}" now? ({hm(mins)})'
        opts = ['Take it now', other, 'Not this week: release it']
    return _base('ready', cid, h, hname, q, opts, 0, why, unlocks, mins, L, whole, kind=kind)


def _frame_receipt(e, hname):
    """A line that crossed with no Receipt: it asks nothing to confirm; one line asks again."""
    # owed.py names the addressee on the row (its holder is the sender); an older row held it as holder
    holder = e.get('addressee') or e.get('holder') or 'the addressee'
    title = e.get('title') or (e.get('id') or '')[:8]
    age = e.get('age_days')
    agew = f'{age:g} days' if isinstance(age, (int, float)) else 'a while'
    c = _base('owed', f"receipt:{e.get('id')}:{holder}", e.get('holon') or '', hname,
              f'No Receipt yet from {holder} for "{title}", {agew}.', ['Ask again', 'Let it go'], 0,
              f'it crossed {agew} ago and {holder} has not said they have it; one line asks again',
              f'you know whether it reached {holder}', e.get('minutes') or 1, rank=1, kind='receipt')
    c['of'], c['to'] = e.get('id'), holder
    c['draft'] = {'type': 'say', 'holon': e.get('holon') or '', 'body': {'to': [holder],
                  'text': f'Checking that "{title}" reached you.'}, 'links': {'anchored_to': [e.get('id')]},
                  'sends': 'person'}                       # drafted here; only a person signs and sends it
    return c


def receipt_cards(norm, actor, now, holons=None, home=None, people=None, hname=None):
    """The receipt cards for the person who sent what crossed (owed.py, receipts=True)."""
    hname = hname or (lambda h: h[:8] if h else '?')
    person = _s(actor)
    if actor_kind(person) != 'person':
        return []
    ppl = {_s(p) for p in people if _s(p)} if isinstance(people, (set, frozenset, list, tuple)) else set()
    them = {person} | agents_of(norm, person, now)
    r = owed_mod.owed(norm, now=now, holons=holons, receipts=True, home=home, people=ppl or {person})
    by_id = {item_id(x): x for xs in norm.values() for x in xs if isinstance(x, dict) and item_id(x)}
    out = []
    for e in r.get('entries') or []:
        if e.get('kind') != 'receipt':
            continue
        it = by_id.get(e.get('id')) or {}
        if _s(it.get('for')) == person or _s(it.get('actor')) in them:
            out.append(_frame_receipt(e, hname))
    return out


def _frame_pain(p, hname, keeper=False):
    """A pain that needs a response. Its keeper keeps the triage card's "Pass it on" (an elevate)."""
    text = str(p.get('text') or '')[:90]
    opts = ['Respond now', 'Pass it on' if keeper else 'Pass it to someone who can', 'Not now']
    c = _base('owed', p['id'], p.get('holon') or '', hname,
              f'Someone asks for help: "{text}". Will you respond?', opts, 0, PAIN_WHY,
              'the one who asked knows someone has it', 3, kind='pain')
    c['acts'] = ['say', 'elevate' if keeper else 'say', None]     # the line each option writes; the last writes none
    return c


def _frame_ask(r, norm, cards, succ, nc, threads, room, hname, unlocks, t, questions):
    """A card for an ask that rose and is not already among the cards."""
    kind, iid, b = r['kind'], r['id'], r.get('body') or {}
    who = r.get('from') or 'someone'
    if kind in ('request', 'request_item'):
        it = cards.get(iid) or next((x for x in norm.get('request', []) if item_id(x) == iid), {})
        e = {'kind': 'request', 'id': iid, 'holon': holon_of(it) or r.get('holon') or '',
             'title': str(field(it, 'title') or field(it, 'text') or iid[:8])[:120], 'holder': None,
             'status': 'waiting', 'due': field(it, 'by'), 'age_days': days_between(r.get('ts'), t),
             'minutes': owed_mod.MINUTES['request']}
        c = _frame_owed(e, norm, cards, succ, nc, threads, room, hname, unlocks)
        c['by'] = e['due']
        return c
    if kind == 'thread' and iid in threads:
        th = threads[iid]
        e = {'kind': 'thread', 'id': iid, 'holon': holon_of(th),
             'title': str(field(th, 'title') or field(th, 'text') or iid[:8])[:120], 'status': 'waiting',
             'due': None, 'age_days': days_between(r.get('ts'), t), 'minutes': owed_mod.MINUTES['thread']}
        return _frame_owed(e, norm, cards, succ, nc, threads, room, hname, unlocks)
    if kind == 'commitment':
        c = next((x for x in norm.get('commitment', []) if item_id(x) == iid), {})
        cid = field(c, 'card')
        title = (field(cards.get(cid), 'title') if isinstance(cid, str) else None) or field(c, 'title') \
            or field(c, 'what') or iid[:8]
        by = field(c, 'by')
        committor = field(c, 'for') or field(c, 'actor') or who
        x = _base('owed', iid, holon_of(c), hname,
                  f'{committor} commits to you: "{str(title)[:90]}"' + (f', by {by}' if by else '') + '. Your word?',
                  ['Thank them: it stands', 'Ask for a change', 'Not mine: say so'], 0,
                  'one line says it landed with you', 'they know it landed with you', 2, kind='commitment')
        x['by'] = by
        return x
    if kind == 'question':
        q = next((x for x in questions or [] if isinstance(x, dict) and x.get('id') == iid), None)
        if q is None:
            q = {'id': iid, 'type': r.get('type'), 'from_holon': r.get('holon'), 'by': b.get('by'),
                 'question': b.get('question') or '', 'state': 'open', 'to': b.get('to')}
        to = q.get('to')
        if not isinstance(to, str) or not to or actor_kind(to):   # a person, a list or nothing: where it was asked
            to = r.get('holon') or ''
        q = dict(q, to=to)
        x = _frame_question(q, hname, 'owed' if q.get('past') else 'decision')
        x['by'] = q.get('by')
        return x
    if kind == 'say':
        text = str(b.get('text') or '')[:90]
        return _base('thread', iid, r.get('holon') or '', hname, f'{who} says to you: "{text}". Your line?',
                     ['Reply now', 'Thank them: no reply needed', 'Hand it to someone else'], 0,
                     'it was said to you', 'they know it reached you', owed_mod.MINUTES['thread'], kind='thread')
    return None


HEADS = {
    'rose': lambda n: 'This one rose to the top.' if n == 1 else f'These {_num(n)} rose to the top.',
    'owed': lambda n: 'This one is waiting on you.' if n == 1 else f'These {_num(n)} are waiting on you.',
    'thread': lambda n: 'A thread waits for your line.' if n == 1 else f'{_num(n).capitalize()} threads wait for your line.',
    'decision': lambda n: 'We need a decision on this one.' if n == 1 else f'We need decisions on these {_num(n)}.',
    'ready': lambda n: 'This fits the time you have.' if n == 1 else f'These {_num(n)} fit the time you have.',
}


def render(d):
    """The Deal in a plain briefing voice."""
    d = d or {}
    cards = d.get('cards') or []
    out = ["Here's the deal.", '']
    if not cards:
        out.append('Nothing needs you right now.' if not (d.get('beyond') or {}).get('count')
                   else 'Nothing fits the minutes you have.')
    letters = 'abc'
    groups = [('rose', [c for c in cards if c.get('rose')])]
    groups += [(sec, [c for c in cards if c['section'] == sec and not c.get('rose')])
               for sec in ('owed', 'thread', 'decision', 'ready')]
    for sec, cs in groups:
        if not cs:
            continue
        out += [HEADS[sec](len(cs)), '']
        for c in cs:
            if c.get('eyebrow'):
                out.append(f"   {c['eyebrow']}")
            out.append(f"{c['n']}. {c['question']}  [{c['holon_name']} · {hm(c['minutes'])}]")
            out.append('   ' + '   '.join(f'{letters[i]}) {o}' for i, o in enumerate(c['options'])))
            ri = c['options'].index(c['recommendation'])
            because = f"; {c['because']}" if c.get('because') else ''
            out.append(f"   I would choose {letters[ri]}: {c['why']}{because}.")
            out.append(f"   Answering: {c['unlocks']}.")
            if c.get('whole_waits'):
                out.append('   The whole is waiting on this.')
            out.append('')
    b = d.get('beyond') or {}
    if b.get('count'):
        out.append(f"{_num(b['count']).capitalize()} more can wait ({hm(b['minutes'])}); "
                   f"{'it stays' if b['count'] == 1 else 'they stay'} in the list.")
    elif cards:
        out.append('Nothing else needs you.')
    oty = d.get('owed_to_you') or []
    if oty:
        out.append(f"Owed to you: {len(oty)}, the oldest \"{oty[0]['title']}\" from {oty[0]['holder']}.")
    if d.get('proposals'):
        n = d['proposals']
        out.append(f"{_num(n).capitalize()} agent proposal{'s' if n != 1 else ''} from text it read "
                   f"{'wait' if n != 1 else 'waits'} for a person; not dealt.")
    out += ['', f"Last: {d.get('question') or STANDING_QUESTION}", '',
            f"*{hm(d.get('minutes_dealt', 0))} of {hm(d.get('minutes_available', 0))} dealt.*"]
    return '\n'.join(out) + '\n'


def render_paper(d):
    """A printable card: one question per block, a tick box per option, a line to write on."""
    d = d or {}
    out = [f"THE DEAL · {str(d.get('generated_at', ''))[:10]} · {d.get('actor', '')} · "
           f"{hm(d.get('minutes_available', 0))}", '=' * 64, '']
    for c in d.get('cards') or []:
        out.append(f"{c['n']}. {c['question']}")
        out.append(f"   ({c['holon_name']} · {hm(c['minutes'])})")
        for o in c['options']:
            mark = '  <- recommended' if o == c['recommendation'] else ''
            out.append(f'   [ ] {o}{mark}')
        out.append(f"   Why: {c['why']}.")
        out += ['   Note: ______________________________________________', '']
    out += [f"[ ] {d.get('question') or STANDING_QUESTION}",
            '    ________________________________________________________',
            '    ________________________________________________________', '',
            'Signed: ________________   Witness: ________________   Date: ________']
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- what rises first

ASKED = 'asked of you'
PAIN_WHY = 'a pain needs a response'
TRUSTED_LINES = ('signed', 'home', 'vouched')        # record.TRUSTED: a line the fold counts
NOT_COUNTED = ('invalid', 'unverified', 'refused', 'forked', 'proposals')   # the fold's lists that never act
ASK_TYPES = ('request', 'rfg', 'say', 'commit', 'escalate')                 # subscriptions.RISING
ANSWER_RELS = ('answer', 'anchored_to', 'serves', 'supersede', 'witnesses')
ANSWER_FIELDS = ('card', 'commitment', 'about', 'what')
NOT_AN_ANSWER = ('receive', 'propose', 'subscribe')  # a Receipt says "I have it", never the answer
RESPONSE_TYPES = ('say', 'answer', 'claim', 'commit', 'thread', 'settle', 'done')   # sightings.RESPONSE_TYPES
ENDED_SIGHT = ('fixed', 'closed', 'retracted', 'responded')


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _epoch(ts):
    t = parse_time(ts) if isinstance(ts, str) else None
    return t.timestamp() if t is not None else None


def _body(x):
    return x.get('body') if isinstance(x, dict) and isinstance(x.get('body'), dict) else {}


def _trust_map(src):
    """The fold's trust map ({line id: trust}) when one can be reached, else None."""
    return src['trust'] if isinstance(src, dict) and isinstance(src.get('trust'), dict) else None


def trusted_lines(items, lines):
    """The lines that may raise or answer an ask: each once, by id; when the fold's trust map can be
    reached, only a line it marks trusted (an id missing from it never passes); never one on its
    invalid, unverified, refused, forked or proposal lists, nor one from untrusted text. Callers pass
    trusted lines; this holds the gate again when the fold rides beside them."""
    if not isinstance(lines, (list, tuple)):
        return []
    trust, out_ids = _trust_map(items), set()
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


def agents_of(norm, person, now=None):
    """The agents a live delegation from this person stands for."""
    t = now_or(now)
    out = set()
    for d in norm.get('delegation', []):
        a = field(d, 'to')
        if actor_kind(a) != 'agent' or is_untrusted(d):
            continue
        if any(_s(field(x, 'for') or field(x, 'actor')) == person for x in live_delegations(norm, a, t)):
            out.add(_s(a))
    return out


def holons_of(items, norm, holons, person, them, lines):
    """(kept, belongs): the holons this person keeps, and every holon they belong to: kept, admitted in
    the fold, named among a holon's members or people, or where they or their agents wrote, hold a
    card, or joined."""
    names = holon_names(norm, holons)
    kept = {h for h, m in names.items() if _s(m.get('keeper')) == person}
    belong = set(kept)
    adm = items.get('admitted') if isinstance(items, dict) and isinstance(items.get('admitted'), dict) else {}
    for h, who in adm.items():
        if isinstance(who, dict) and person in {_s(k) for k in who}:
            belong.add(str(h))
    for h in holons or []:
        if isinstance(h, dict) and h.get('id'):
            for k in ('members', 'people'):
                v = h.get(k)
                if isinstance(v, (list, tuple)) and person in {_s(x) for x in v}:
                    belong.add(str(h['id']))
    for kind, xs in norm.items():
        if kind == 'untrusted':
            continue
        for x in xs:
            if not isinstance(x, dict) or is_untrusted(x):
                continue
            if _s(x.get('actor')) in them or _s(x.get('for')) == person \
                    or (kind == 'card' and _s(field(x, 'holder')) == person) \
                    or (kind == 'join' and _s(field(x, 'who')) == person):
                belong.add(holon_of(x))
    for l in lines:
        if _s(l.get('actor')) in them or _s(l.get('for')) == person \
                or (l.get('type') == 'join' and _s(_body(l).get('who')) == person):
            belong.add(_s(l.get('holon')))
    belong.discard('')
    return kept, belong


def _view(it, typ, body):
    return {'id': item_id(it), 'type': typ, 'actor': it.get('actor'), 'for': it.get('for'),
            'reason': field(it, 'reason'), 'ts': it.get('ts'), 'body': body}


def _asks(norm, lines, questions, admit_q=lambda qid: False):
    """(line or line-shaped view, target id or None, target kind) for every ask in the record:
    from the fold's items where they keep the addressee (a request card's or item's `to`, a
    commitment's committee, a thread's `to`, a question's `to`), and from the lines given. A ladder
    question is taken only when `admit_q` admits its id (ladder.questions reads lines raw)."""
    out = []
    by_q = {q['id']: q for q in questions or [] if isinstance(q, dict) and isinstance(q.get('id'), str)
            and q['id'] and admit_q(q['id'])}
    lines_by = {l['id']: l for l in lines}
    cards = {item_id(c): c for c in norm.get('card', []) if item_id(c)}
    reqs = {item_id(r): r for r in norm.get('request', []) if item_id(r)}
    comms = {item_id(c): c for c in norm.get('commitment', []) if item_id(c)}
    threads = {item_id(t): t for t in norm.get('thread', []) if item_id(t)}
    for cid, c in cards.items():
        if str(field(c, 'asked') or '') == 'request' and field(c, 'to'):
            out.append((_view(c, 'request', {'to': field(c, 'to')}), cid, 'request'))
    for rid, r in reqs.items():
        if field(r, 'to'):
            out.append((_view(r, 'request', {'to': field(r, 'to')}), rid, 'request_item'))
    for cid, c in comms.items():
        if field(c, 'committee'):
            out.append((_view(c, 'commit', {'committee': field(c, 'committee')}), cid, 'commitment'))
    for tid, th in threads.items():
        if field(th, 'to'):
            out.append((_view(th, 'say', {'to': field(th, 'to')}), tid, 'thread'))
    for qid, q in by_q.items():
        if q.get('type') in ('rfg', 'escalate'):
            src = lines_by.get(qid) or {}
            out.append(({'id': qid, 'type': q['type'], 'actor': q.get('asker') or src.get('actor'),
                         'for': src.get('for'), 'reason': src.get('reason'), 'ts': q.get('ts') or src.get('ts'),
                         'body': {'to': q.get('to')}}, qid, 'question'))
    entry_of = {}
    for tid, th in threads.items():
        for e in field(th, 'lines') or []:
            if isinstance(e, dict) and isinstance(e.get('id'), str):
                entry_of.setdefault(e['id'], tid)
    for l in lines:
        typ, lid = l.get('type'), l['id']
        if typ not in ASK_TYPES:
            continue
        if typ in ('rfg', 'escalate'):
            out.append((l, lid, 'question'))
        elif typ == 'say':
            tid = lid if lid in threads else entry_of.get(lid) or next(
                (x for x in links(l, 'anchored_to') if x in threads), None)
            out.append((l, tid, 'thread' if tid else 'say'))
        elif typ == 'commit':
            if lid in comms:
                out.append((l, lid, 'commitment'))
        else:                                             # a request: the card it made or acted on
            cid = lid if lid in cards else next((x for x in [field(l, 'card')] + links(l, 'anchored_to')
                                                 if isinstance(x, str) and x in cards), None)
            if cid:
                out.append((l, cid, 'request'))
            elif lid in reqs:
                out.append((l, lid, 'request_item'))
    return out, by_q, cards, reqs, comms, threads


def _refs(x):
    out = set()
    for r in ANSWER_RELS:
        out.update(links(x, r))
    for k in ANSWER_FIELDS:
        v = field(x, k)
        if isinstance(v, str) and v:
            out.add(v)
    a = field(x, 'anchor')
    out.update([a] if isinstance(a, str) else [y for y in a if isinstance(y, str)] if isinstance(a, list) else [])
    return out


def _answered(kind, item, ask, them, person, lines, by_q):
    """True when the ask no longer waits on the person: its item has moved on, or a line of their
    own side (theirs, or their agent's for them) answers it or links to it since it was asked."""
    st = str(field(item, 'state') or '').lower() if isinstance(item, dict) else ''
    if kind == 'request' and st != 'open':
        return True
    if kind == 'request_item' and (field(item, 'answered') or st in DONE_STATES | {'answered', 'taken'}):
        return True
    if kind == 'commitment' and st not in ('', 'open'):
        return True
    if kind == 'question':
        q = by_q.get(ask['id'])
        if q is not None and q.get('state') != 'open':
            return True
    since = _epoch(ask.get('ts'))
    if kind == 'thread' and isinstance(item, dict):
        if owed_mod.thread_view(item)['settled']:
            return True
        for e in field(item, 'lines') or []:
            if isinstance(e, dict) and e.get('id') != ask['id'] and _s(e.get('actor')) in them:
                e_t = _epoch(e.get('ts'))
                if since is None or e_t is None or e_t >= since:
                    return True
    targets = {ask['id']} | ({item_id(item)} if isinstance(item, dict) and item_id(item) else set())
    for l in lines:
        if l['id'] in targets or l.get('type') in NOT_AN_ANSWER:
            continue
        if not (_s(l.get('actor')) in them or _s(l.get('for')) == person):
            continue
        l_t = _epoch(l.get('ts'))
        if since is not None and l_t is not None and l_t < since:
            continue
        if _refs(l) & targets:
            return True
    return False


def _sight_kind(s):
    k = field(s, 'body_kind') or field(s, 'sight_kind')
    if not k and field(s, 'kind') not in ('sighting', 'sight', None):
        k = field(s, 'kind')
    return str(k).lower() if isinstance(k, str) else None


def _responded(sid, s, norm, lines):
    """The fallback when sightings.lifecycle is absent: a trusted line or item by another actor anchored to it."""
    side = {_s(s.get('for')), _s(s.get('actor'))} - {''}

    def who(x):
        f = _s(x.get('for'))
        return f if actor_kind(f) == 'person' else _s(x.get('actor'))
    for kind, xs in norm.items():
        if kind in ('sighting', 'untrusted'):
            continue
        for x in xs:
            if isinstance(x, dict) and item_id(x) != sid and not is_untrusted(x) and who(x) not in side \
                    and sid in _refs(x):
                return True
    return any(l.get('type') in RESPONSE_TYPES and who(l) not in side and sid in _refs(l) for l in lines)


def rising(items, actor, lines=None, now=None, holons=None, questions=None, fold=None):
    """What rises first in this person's Deal, before float, stake or groups.

    requests  each ask addressed to the person or their agents (subscriptions.rises_first: a
              `request` or `rfg` to them, a `say` with them in `to`, a `commit` with them as committee,
              an `escalate` or `rfg` to a holon they keep) not yet answered, newest first (ts, then id)
    pains     each open pain sighted in a holon they belong to that needs a response
              (sightings.lifecycle; without it, a pain with no line by another actor anchored to it),
              newest first; never a pain of their own side
    An agent's Deal has nothing rise: what is asked of a person is the person's. `fold` is record.py's
    fold whole, when the items were normalized from it: its trust map, its lists of lines that never
    act and its admitted members then gate the lines here as they gate the fold."""
    src = fold if isinstance(fold, dict) else items
    norm = normalize(items)
    t = now_or(now)
    person = _s(actor)
    trust = _trust_map(src)

    def ok(i):                                            # with a trust map, only what it marks trusted
        return trust is None or trust.get(i) in TRUSTED_LINES
    tl = trusted_lines(src, lines)
    tl_ids = {l['id'] for l in tl}
    out = {'requests': [], 'pains': [], 'pain_basis': 'none', 'newest_line': None,
           'lines_basis': ('no lines: the fold\'s items alone' if not isinstance(lines, (list, tuple))
                           else 'lines gated by the fold\'s trust map' if trust is not None
                           else 'lines given with no trust map: taken as the caller passed them')}
    seen = [(_epoch(x.get('ts')), x['id'], x.get('ts')) for x in tl]
    seen += [(_epoch(x.get('ts')), item_id(x), x.get('ts')) for xs in norm.values() for x in xs
             if isinstance(x, dict) and item_id(x) and x.get('_kind') != 'untrusted' and ok(item_id(x))]
    seen = [x for x in seen if x[0] is not None]
    if seen:
        e, i, ts = max(seen)
        out['newest_line'] = {'id': i, 'ts': ts}
    if actor_kind(person) != 'person':
        return out
    agents = agents_of(norm, person, t)
    them = {person} | agents
    kept, belong = holons_of(src, norm, holons, person, them, tl)
    asks, by_q, cards, reqs, comms, threads = _asks(
        norm, tl, questions, lambda qid: qid in tl_ids or (trust is not None and trust.get(qid) in TRUSTED_LINES))
    pool = {'request': cards, 'request_item': reqs, 'commitment': comms, 'thread': threads}
    found = {}
    for ask, target, kind in asks:
        if not ok(ask['id']) or _s(ask.get('actor')) in them or \
                not subscriptions_mod.rises_first(ask, person, sorted(agents), sorted(kept)):
            continue
        item = pool.get(kind, {}).get(target) if target else None
        if isinstance(item, dict) and is_untrusted(item):
            continue
        if _answered(kind, item, ask, them, person, tl, by_q):
            continue
        key = target or ask['id']
        e = _epoch(ask.get('ts'))
        prev = found.get(key)
        if prev is None or (e is not None and (prev['epoch'] is None or e > prev['epoch'])):
            found[key] = {'id': key, 'kind': kind, 'line': ask['id'], 'ts': ask.get('ts'), 'epoch': e,
                          'type': ask.get('type'), 'from': ask.get('actor'), 'holon': _s(ask.get('holon')) or
                          (holon_of(item) if isinstance(item, dict) else ''), 'body': _body(ask)}
    inf = float('inf')
    out['requests'] = sorted(found.values(), key=lambda r: (-r['epoch'] if r['epoch'] is not None else inf, r['id']))

    pains = [s for s in norm.get('sighting', []) if isinstance(s, dict) and item_id(s) and not is_untrusted(s)
             and _sight_kind(s) == 'pain' and holon_of(s) in belong and ok(item_id(s))
             and not (_s(s.get('for')) == person or _s(s.get('actor')) in them)]
    if pains:
        lf, basis = None, 'sightings.lifecycle'
        fn = getattr(sightings_mod, 'lifecycle', None) if sightings_mod is not None else None
        if callable(fn):
            try:
                lf = fn(src, lines=tl, now=t)
            except Exception as ex:                       # a module mid-repair never stops the Deal; it is said
                lf, basis = None, f'fallback: sightings.lifecycle raised {type(ex).__name__}'
        else:
            basis = 'fallback: sightings.lifecycle is absent'
        if not isinstance(lf, dict):
            lf = None
        out['pain_basis'] = basis
        keep = []
        for s in pains:
            sid = item_id(s)
            row = lf.get(sid) if lf is not None else None
            if isinstance(row, dict):
                if not row.get('needs_response'):
                    continue
            elif str(field(s, 'state') or '').lower() in ENDED_SIGHT or _responded(sid, s, norm, tl):
                continue
            keep.append({'id': sid, 'holon': holon_of(s), 'text': str(field(s, 'text') or ''),
                         'ts': s.get('ts'), 'epoch': _epoch(s.get('ts'))})
        out['pains'] = sorted(keep, key=lambda r: (-r['epoch'] if r['epoch'] is not None else inf, r['id']))
    return out


def _load(p):
    if os.path.islink(p):
        raise OSError(f'{p} is a symlink; a file is read only where it stands')
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def _load_lines(p):
    """A JSONL file of lines (or one JSON list); a line that does not parse is left out."""
    if os.path.islink(p):
        raise OSError(f'{p} is a symlink; a file is read only where it stands')
    with open(p, encoding='utf-8') as f:
        raw = f.read()
    try:
        v = json.loads(raw)
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else [v] if isinstance(v, dict) else []
    except ValueError:
        out = []
        for row in raw.splitlines():
            try:
                x = json.loads(row)
            except ValueError:
                continue
            if isinstance(x, dict):
                out.append(x)
        return out


def _main(argv=None):
    ap = argparse.ArgumentParser(description="The Deal from folded items (JSON). Opens: Here's the deal.")
    ap.add_argument('items'); ap.add_argument('--actor', required=True)
    ap.add_argument('--minutes', type=float, default=20.0)
    ap.add_argument('--room', default='', help='comma-separated actor ids present')
    ap.add_argument('--schedule', help='a JSON schedule report (schedule.py)')
    ap.add_argument('--lines', help='the trusted lines (JSONL): what is asked of the actor rises first')
    ap.add_argument('--home', help="the home's holon id, for the receipt cards")
    ap.add_argument('--now'); g = ap.add_mutually_exclusive_group()
    g.add_argument('--json', action='store_true'); g.add_argument('--paper', action='store_true')
    a = ap.parse_args(argv)
    try:
        items = _load(a.items)
        rep = _load(a.schedule) if a.schedule else None
        lines = _load_lines(a.lines) if a.lines else None
    except (OSError, ValueError) as e:
        print(f'deal: cannot read input: {e}', file=sys.stderr); return 2
    room = [x.strip() for x in a.room.split(',') if x.strip()]
    d = deal(items, rep, a.actor, a.minutes, room, a.now, lines=lines, home=a.home)
    print(json.dumps(d, indent=1, ensure_ascii=False) if a.json else render_paper(d) if a.paper else render(d))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
