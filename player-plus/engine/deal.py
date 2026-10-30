#!/usr/bin/env python3
"""deal.py — The Deal: the few cards that need this player now, sized to the time they have.

    deal(items, schedule_report, actor, minutes_available, room=None, now=None, holons=None) -> dict
    render(deal) -> Markdown, opening "Here's the deal."
    render_paper(deal) -> a printable card with tick boxes

Across every holon the items come from, in this order:

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
                    [--now ISO] [--json | --paper]
"""
import argparse
import json
import sys

try:
    from gamecore import (normalize, field, links, sched_map, path_sets, now_or, days_between, item_id,
                          holon_of, holon_names, may_act, minutes_of, hm, DONE_STATES,
                          STANDING_QUESTION, is_untrusted, card_kind, actor_kind,
                          live_delegations, covers, HUMAN_ONLY_KINDS)
    import owed as owed_mod
    import attention as attention_mod
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, links, sched_map, path_sets, now_or, days_between, item_id,
                          holon_of, holon_names, may_act, minutes_of, hm, DONE_STATES,
                          STANDING_QUESTION, is_untrusted, card_kind, actor_kind,
                          live_delegations, covers, HUMAN_ONLY_KINDS)
    import owed as owed_mod
    import attention as attention_mod

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
         questions=None, sightings=None, bodies=None, fewer=False, closeout=False):
    """The Deal for one actor, across every holon in the items. `questions` from ladder.questions,
    `sightings` from sightings.triage, when the caller has the raw lines."""
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
              'claim': 'claim', 'question': 'decide', 'handoff': 'witness'}
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

    order = {'owed': 0, 'thread': 1, 'decision': 2, 'ready': 3}
    for x in cands:                       # what the attention gate reads on every card
        x.setdefault('by', field(cards.get(x['id']), 'by') if x['id'] in cards else None)
        x.setdefault('who_waits', 'now' if 'in the room' in x.get('why', '') else None)   # a person waiting now
        x['always_passes'] = bool(x.get('always_passes') or x.get('who_waits') == 'now')
        x['heavy'] = x['section'] == 'decision' and x.get('kind') in ('decision', 'ratify', 'decide', 'question')
    cands.sort(key=lambda x: (order[x['section']], x.get('_rank', 0), -x['leverage'], x['minutes'], x['id']))
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
        x.pop('_rank', None)

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
    return {'actor': actor, 'minutes_available': budget, 'minutes_dealt': round(spent, 1), 'room': room,
            'generated_at': t.isoformat(timespec='seconds'), 'opening': "Here's the deal.",
            'cards': dealt,
            'beyond': {'count': len(rest), 'minutes': round(beyond_m, 1), 'cards': rest[:BEYOND_CARDS]},
            'owed_to_you': owed_to_you, 'proposals': len(ow.get('proposals') or []),
            'fewer': attention_mod.FEWER_STEPS[step],
            'question': STANDING_QUESTION, 'rule': RULE, 'as_of': as_of}


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


HEADS = {
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
    for sec in ('owed', 'thread', 'decision', 'ready'):
        cs = [c for c in cards if c['section'] == sec]
        if not cs:
            continue
        out += [HEADS[sec](len(cs)), '']
        for c in cs:
            if c.get('eyebrow'):
                out.append(f"   {c['eyebrow']}")
            out.append(f"{c['n']}. {c['question']}  [{c['holon_name']} · {hm(c['minutes'])}]")
            out.append('   ' + '   '.join(f'{letters[i]}) {o}' for i, o in enumerate(c['options'])))
            ri = c['options'].index(c['recommendation'])
            out.append(f"   I would choose {letters[ri]}: {c['why']}.")
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


def _load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def _main(argv=None):
    ap = argparse.ArgumentParser(description="The Deal from folded items (JSON). Opens: Here's the deal.")
    ap.add_argument('items'); ap.add_argument('--actor', required=True)
    ap.add_argument('--minutes', type=float, default=20.0)
    ap.add_argument('--room', default='', help='comma-separated actor ids present')
    ap.add_argument('--schedule', help='a JSON schedule report (schedule.py)')
    ap.add_argument('--now'); g = ap.add_mutually_exclusive_group()
    g.add_argument('--json', action='store_true'); g.add_argument('--paper', action='store_true')
    a = ap.parse_args(argv)
    try:
        items = _load(a.items)
        rep = _load(a.schedule) if a.schedule else None
    except (OSError, ValueError) as e:
        print(f'deal: cannot read input: {e}', file=sys.stderr); return 2
    room = [x.strip() for x in a.room.split(',') if x.strip()]
    d = deal(items, rep, a.actor, a.minutes, room, a.now)
    print(json.dumps(d, indent=1, ensure_ascii=False) if a.json else render_paper(d) if a.paper else render(d))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
