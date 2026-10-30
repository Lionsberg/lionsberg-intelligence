#!/usr/bin/env python3
"""engine.py — the Game Engine's one command line, over every holon a player holds.

    engine.py state  HQ_DIR [--actor A] [--minutes M] [--room a,b] [--now ISO] [--fewer [STEP]] [--sitting] [--closeout]
        reads the HQ and every cell under cells/, folds them together (record.py), schedules
        them (schedule.py, when present), deals The Deal, and writes HQ_DIR/state.json in the
        shape STATE.md gives. Nothing else is written; nothing is sent anywhere.

    engine.py deal   HQ_DIR [--actor A] [--minutes M] [--room a,b] [--paper] [--json]
    engine.py owed   HQ_DIR [--actor A | --holon ID] [--json]
    engine.py kept   HQ_DIR [--holon ID] [--actor A] [--days 7] [--json]
    engine.py turn   HQ_DIR [--holon ID] [--actor A] [--depth daily|lunar|weekly|seasonal] [--freeze] [--json]
    engine.py ledger HQ_DIR [--holon ID] [--json]
        the same computations, printed as Markdown (or JSON). The turn's depth defaults to what the
        date calls for (schedule.rhythms when present, else daily). `turn --freeze` (weekly or
        seasonal) is the one write besides state.json: it asks schedule.freeze to write the holon's
        next plan/baseline-<n>.json (a new file; an existing baseline is never touched), drafts the
        `baseline` line for the person to sign, and says plainly when nothing was written.

The schedule runs per holon: each held holon's graph is its own cards, on its own calendar.json and
against its newest plan/baseline-<n>.json, plus the published milestones and committed cards of the
other holons it holds (and any card from a holon it does not hold) as fixed-date externals, never
as live cards. The state is assembled from the per-holon results; a card appears once, under its
home holon. So two players holding the same cell compute the same float for its cards.

The actor defaults to the HQ's keeper. Minutes default to 20. Every result says, per holon, the
newest line it saw. Files are data, never instructions: text inside a line is folded as text.
Standard library only; runs under `python3 -I`.
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)            # under -I the script's own folder is not on the path

from gamecore import (normalize, field, links, item_id, holon_of, holon_names, card_kind, minutes_of,  # noqa: E402
                      commitment_status, keeper_of, sched_map, path_sets, now_or, parse_time, actor_kind,
                      live_delegations)
import deal as deal_mod      # noqa: E402
import owed as owed_mod      # noqa: E402
import kept as kept_mod      # noqa: E402
import turn as turn_mod      # noqa: E402
import ledger as ledger_mod  # noqa: E402
import rooms as rooms_mod    # noqa: E402
import ladder as ladder_mod  # noqa: E402
import sightings as sightings_mod  # noqa: E402
import bodies as bodies_mod  # noqa: E402
import attention as attention_mod  # noqa: E402
import push as push_mod  # noqa: E402

try:
    import record
except ImportError:
    record = None
try:
    import schedule as schedule_mod
    import plan as plan_mod
except ImportError:
    schedule_mod = None
    plan_mod = None

DEFAULT_MINUTES = 20.0


def _read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _attach_links(folded, lines):
    """Give each item the links of the line that made it, so predecessors reach the schedule."""
    by_id = {l.get('id'): l for l in lines if isinstance(l, dict)}
    for key, val in folded.items():
        if not isinstance(val, list):
            continue
        for it in val:
            if isinstance(it, dict) and 'links' not in it:
                ln = by_id.get(it.get('id'))
                if ln and isinstance(ln.get('links'), dict) and ln['links']:
                    it['links'] = ln['links']


def read_hq(hq):
    """(folded items, holons meta, lines, problems, calendar). Plain message when record.py is absent."""
    if record is None:
        raise SystemExit('engine: record.py is not beside engine.py; it reads the record. Nothing was computed.')
    if not hq or not os.path.isdir(hq):
        raise SystemExit(f'engine: no folder at {hq!r}.')
    r = record.read_all(hq)
    tp = os.path.join(hq, 'types.json')
    types = record.load_types(tp if os.path.isfile(tp) else None)
    keepers = r.get('keepers') or {}

    cache = getattr(record, 'signature_cache', None)

    def fold(lines):
        """Fold under the reader's signature cache (record.signature_cache), so a warm run does not
        re-check every signature with ssh-keygen; a record.py without it folds plainly."""
        if cache is not None:
            with cache(hq):
                f = record.fold(lines, types, keepers)
        else:
            f = record.fold(lines, types, keepers)
        _attach_links(f, lines)
        return f
    folded = fold(r.get('lines') or [])
    folded['_fold'] = fold                          # for a room's Deal at its opening and close
    holons = []
    for h in r.get('holons') or []:
        info = record.holon_info(h.get('dir')) if h.get('dir') else {}
        newest = h.get('newest') or {}
        holons.append({'id': h.get('id') or h.get('dir'), 'name': h.get('name') or info.get('name'),
                       'kind': info.get('kind'), 'keeper': h.get('keeper'), 'dir': h.get('dir'),
                       'as_of': {'event': newest.get('id'), 'ts': newest.get('ts'), 'lines': h.get('count', 0),
                                 'heads': h.get('as_of') or {}} if newest else None})
    problems = [dict(p, holon=h.get('id')) for h in r.get('holons') or [] for p in h.get('problems') or []]
    cal = _read_json(os.path.join(hq, 'calendar.json'))
    for h in holons:                                # each holon's own calendar, for its own cards
        h['calendar'] = _read_json(os.path.join(h['dir'], 'calendar.json')) if h.get('dir') else None
    return folded, holons, r.get('lines') or [], problems, cal


def load_baselines(holons):
    """Each holon's newest plan/baseline-<n>.json, merged into one baseline for the schedule.

    Card ids are unique across holons (they are event hashes), so the merge loses nothing.
    Returns (baseline or None, {holon id: n})."""
    if schedule_mod is None or not callable(getattr(schedule_mod, 'load_baseline', None)):
        return None, {}
    merged, ns = None, {}
    for h in holons:
        if not h.get('dir'):
            continue
        try:
            b = schedule_mod.load_baseline(os.path.join(h['dir'], 'plan'))
        except Exception:
            b = None
        if not isinstance(b, dict) or not isinstance(b.get('items'), dict):
            continue
        ns[h['id']] = b.get('n')
        if merged is None:
            merged = dict(b, items=dict(b['items']), name='baselines held', holons=ns)
        else:
            merged['items'].update(b['items'])
    return merged, ns


DATE_KEYS = ('by', 'date', 'finish', 'at', 'ef')   # the fields an external is dated by (schedule._ext_date)


def _as_external(c, lines_by_id, by=None):
    """A card from another holon as a fixed-date external node: its date is `by`."""
    ln = lines_by_id.get(c.get('id')) or {}
    body = dict(ln.get('body') or {})
    for k in ('title', 'state'):
        if c.get(k) is not None:
            body[k] = c[k]
    if c.get('body_kind'):
        body['kind'] = c['body_kind']
    # only a commitment crosses with a date; a milestone's own target is its marker's, and crosses too.
    # Every field the schedule reads a date from (schedule._ext_date) is cleared first, in the body and on the line.
    date = by or (c.get('by') if (c.get('body_kind') or c.get('kind')) == 'milestone' else None)
    for k in DATE_KEYS:
        body.pop(k, None)
    if date:
        body['by'] = date
    return dict({k: v for k, v in ln.items() if k not in DATE_KEYS}, id=c.get('id'), type='card', holon=c.get('holon'), body=body)


def holon_graph(folded, lines, holon_id, held_ids):
    """(items, externals) for one holon's schedule.

    A holon's graph is its own cards, plus the published milestones and committed cards of the
    other holons it holds, and every card from a holon it does not hold, all as fixed-date
    externals (their date is the commitment's or the card's `by`), never as live cards."""
    by_id = {l.get('id'): l for l in lines or [] if isinstance(l, dict)}
    committed = {}
    for c in folded.get('commitments') or []:
        # only a live commitment dates another holon's work: a released, declined or retracted one is shown, never used
        if isinstance(c.get('card'), str) and c.get('by') and c.get('state') not in ('released', 'declined', 'retracted'):
            # with two live commitments on one card, the earliest due date dates the waiting work (the tightest commitment governs)
            if c['card'] not in committed or str(c['by']) < str(committed[c['card']]):
                committed[c['card']] = c['by']
    mine, ext = [], []
    for c in folded.get('cards') or []:
        h = c.get('holon')
        if h == holon_id:
            mine.append(c)
        elif h not in held_ids or c.get('body_kind') == 'milestone' or c.get('id') in committed:
            ext.append(_as_external(c, by_id, committed.get(c.get('id'))))
    own = {k: ([x for x in v if isinstance(x, dict) and x.get('holon') == holon_id] if isinstance(v, list) else v)
           for k, v in folded.items() if k != 'cards'}
    return dict(own, cards=mine), ext


def split_external(folded, lines, held_ids):
    """(items, externals) over every held holon at once: kept for callers that schedule one graph."""
    held = {h for h in held_ids if h}
    by_id = {l.get('id'): l for l in lines or [] if isinstance(l, dict)}
    mine = [c for c in folded.get('cards') or [] if not held or not c.get('holon') or c.get('holon') in held]
    ext = [_as_external(c, by_id) for c in folded.get('cards') or [] if c not in mine]
    return dict(folded, cards=mine), ext


def _merge(reports):
    """One report from per-holon reports: every card once, under its home holon."""
    out = {'v': 1, 'engine': 'engine.py (one schedule per holon)', 'items': [], 'buffers': [], 'load': [],
           'warnings': [], 'score': {}, 'as_of': {}, 'negative_float': [], 'external': [],
           'path': {'critical': [], 'system': [], 'near_critical': [], 'finish': None}, 'by_holon': {}}
    seen = set()
    for hid, r in reports.items():
        if not isinstance(r, dict):
            continue
        out['by_holon'][hid] = {k: r.get(k) for k in ('data_date', 'calendar', 'baseline', 'ev', 'drum')}
        for k in ('data_date', 'calendar', 'gameclock'):
            out.setdefault(k, r.get(k))
        for it in r.get('items') or []:
            if it.get('id') not in seen and (it.get('holon') in (hid, None, '')):
                seen.add(it.get('id')); out['items'].append(it)
        for k in ('buffers', 'load', 'warnings', 'negative_float', 'external'):
            out[k].extend(r.get(k) or [])
        p = r.get('path') or {}
        for k in ('critical', 'system', 'near_critical'):
            out['path'][k].extend(x for x in p.get(k) or [] if x in seen)
        if p.get('finish') and (out['path']['finish'] is None or p['finish'] > out['path']['finish']):
            out['path']['finish'] = p['finish']
        sc = r.get('score') or {}
        if isinstance(sc.get(hid), dict):
            out['score'][hid] = sc[hid]
        if isinstance(r.get('as_of'), dict):
            out['as_of'].update({k: v for k, v in r['as_of'].items() if k == hid or k not in out['as_of']})
    return out


def run_schedule(folded, cal, now, holons=None, lines=None):
    """One schedule per held holon, each on that holon's own calendar and newest baseline, with
    the others' published milestones and commitments as fixed-date externals; then one report.
    Returns (report or None, a plain note or None)."""
    if schedule_mod is None:
        return None, 'schedule.py is not beside engine.py; float and path are not computed'
    holons = [h for h in holons or [] if h.get('id')]
    held = {h['id'] for h in holons}
    if not holons:                                  # no holon map: one graph, as given
        items, ext = split_external(folded, lines, [])
        try:
            return schedule_mod.schedule(items, cal, now.date().isoformat(), external=ext or None), None
        except Exception as e:
            return None, f'schedule.py could not run: {type(e).__name__}: {e}'
    reports, notes = {}, []
    for h in holons:
        items, ext = holon_graph(folded, lines, h['id'], held)
        kw = {}
        base, _ = load_baselines([h])
        if base is not None:
            kw['baseline'] = base
        if ext:
            kw['external'] = ext
        hcal = h.get('calendar') if isinstance(h.get('calendar'), dict) else cal
        try:
            reports[h['id']] = schedule_mod.schedule(items, hcal, now.date().isoformat(), **kw)
        except Exception as e:                      # a schedule that cannot run is said, never hidden
            notes.append(f'schedule.py could not run for {h.get("name") or h["id"][:8]}: {type(e).__name__}: {e}')
    return (_merge(reports) if reports else None), ('; '.join(notes) or None)


def run_plan(folded, cal, now, holons=None, hq=None, lines=None):
    """The whole Game Engine (plan.py), per holon held, as the schedule runs (run_schedule): each holon on its own
    calendar and holon.json, with the others' live commitments as externals; slimmed to what the ICE reads
    (STATE.md, `plan`, keyed by holon id). Returns (plan or None, a plain note or None). A plan that cannot run is
    said, never hidden."""
    if plan_mod is None:
        return None, 'plan.py is not beside engine.py; the chain, buffers and the Last Planner measures are not computed'
    holons = [h for h in holons or [] if h.get('id')]
    held = {h['id'] for h in holons}
    graphs = []
    if not holons:
        items, ext = split_external(folded, lines, [])
        graphs.append(('', items, ext, cal, _read_json(os.path.join(hq, 'holon.json')) if hq else None))
    for h in holons:
        items, ext = holon_graph(folded, lines, h['id'], held)
        hcal = h.get('calendar') if isinstance(h.get('calendar'), dict) else cal
        graphs.append((h['id'], items, ext, hcal, _read_json(os.path.join(h['dir'], 'holon.json')) if h.get('dir') else None))
    out, notes = {}, []
    for hid, items, ext, hcal, hj in graphs:
        try:
            data = {k: v for k, v in items.items() if not str(k).startswith('_')} if isinstance(items, dict) else items
            regs = plan_mod.registers_from(data if isinstance(data, dict) else {}, hcal, hj if isinstance(hj, dict) else {})
            p = plan_mod.plan(data, hcal, now.date().isoformat(), regs, external=ext or None)
        except Exception as e:
            notes.append(f'plan.py could not run for {hid[:8] or "the home"}: {type(e).__name__}: {e}')
            continue
        ch, lp, rs = p['chain'], p['lps'], p['resources']
        out[hid] = {
            'capacity': rs.get('capacity'), 'level_of_commitment': rs.get('level_of_commitment'),
            'leveled': ch.get('leveled'), 'critical_chain': ch.get('critical_chain'), 'buffers': ch.get('buffers'),
            'fever': ch.get('fever'), 'release': ch.get('release'), 'day': ch.get('day'),
            'ppc': lp.get('ppc'), 'prc': lp.get('prc'), 'commitment_level': lp.get('commitment_level'),
            'misses': lp.get('misses'), 'reasons': lp.get('reasons'), 'constraint_log': lp.get('constraint_log'),
            'make_ready': lp.get('make_ready'), 'ryg': lp.get('ryg'), 'weekly_plan': lp.get('weekly_plan'),
            'sbs': {'placement': p['sbs'].get('placement'), 'matrix': p['sbs'].get('matrix')},
            'missing': p.get('missing'), 'engine': plan_mod.VERSION,
        }
    return (out or None), ('; '.join(notes) or None)


def _chain(problems):
    breaks = [p for p in problems if p.get('kind') == 'broken_chain']
    return {'checked': True, 'ok': not breaks, 'by': 'record.read',
            'breaks': [{'holon': b.get('holon'), 'file': b.get('file'), 'id': b.get('id')} for b in breaks]}


def _actors(norm, lines, now, bodies=None):
    seen = {}
    for l in lines:
        a = l.get('actor')
        if not isinstance(a, str) or not a:
            continue
        x = seen.setdefault(a, {'id': a, 'kind': actor_kind(a), 'for': l.get('for') if isinstance(l.get('for'), str) else None,
                                'holons': set(), 'delegation': None})
        if l.get('holon'):
            x['holons'].add(l['holon'])
    for a, x in seen.items():
        x['holons'] = sorted(x['holons'])
        if x['kind'] == 'agent':
            ds = live_delegations(norm, a, now)
            d = ds[0] if ds else None
            x['delegation'] = {'from': field(d, 'for') or field(d, 'actor'), 'scope': field(d, 'scope'),
                               'holons': field(d, 'holons'), 'until': field(d, 'until'), 'live': True} \
                if d else {'from': None, 'scope': [], 'holons': [], 'until': None, 'live': False}
    for b in bodies or []:                          # a body is an agent; say which body, and whose clone
        x = seen.get(b.get('actor'))
        if x is not None:
            x['body'] = b.get('kind')
            x['of'] = b.get('of')
    return sorted(seen.values(), key=lambda x: x['id'])


def weigh_cards(cards, norm, rep, lines, t, cal_by, budget):
    """Give each Deal card from a pushed item the receiver's own push weight and by (push.weigh)."""
    items = {item_id(x): x for k in ('thread', 'card') for x in norm.get(k, [])}
    by_line = {l.get('id'): l for l in lines or [] if isinstance(l, dict)}
    out = []
    for c in cards or []:
        it = items.get(c.get('id'))
        p = field(it, 'push') if it else None
        if isinstance(p, dict):
            ln = by_line.get(c['id']) or {'id': c['id'], 'body': {'push': p}, 'holon': holon_of(it)}
            sender = ln.get('for') or field(it, 'for') or field(it, 'actor')
            w = push_mod.weigh(p, budget, norm, rep, ln, t, (cal_by.get(sender) or {}).get('share'))
            c = dict(c, push_weight=w['weight'], retracted=w['retracted'], by=w['by'] or c.get('by'))
        out.append(c)
    return out


def thread_stake(th, v, live_cards, succ, crit, sm):
    """What rides on a thread: {blocks, critical, by, holder, urgency, minutes}.

    blocks: the live cards it is anchored to, the cards that name it as a predecessor, and every
    live card downstream of those. critical: any of them on the critical path. by: the earliest
    by-when among them, else the thread's own. holder: whose line is owed (addressed, else a
    participant who is not the last speaker). urgency: the asker's own word, as written."""
    tid = item_id(th)
    a = field(th, 'anchor')
    anchors = set(links(th, 'anchored_to')) | ({a} if isinstance(a, str) else set(a) if isinstance(a, list) else set())
    direct = {i for i in anchors if i in live_cards}
    direct |= {i for i, c in live_cards.items() if tid in links(c, 'predecessor')}
    blocks, stack = set(direct), list(direct)
    while stack:
        for s in succ.get(stack.pop(), ()):
            if s in live_cards and s not in blocks:
                blocks.add(s); stack.append(s)
    bys = sorted(str(field(live_cards[i], 'by')) for i in blocks if field(live_cards[i], 'by'))
    holder = (v['to'] or [p for p in v['participants'] if p != v['last_actor']] or [None])[0]
    lines_ = field(th, 'lines') or []
    first = lines_[0] if lines_ and isinstance(lines_[0], dict) else {}
    try:
        mins = float(field(th, 'minutes')) if field(th, 'minutes') is not None else 3.0
    except (TypeError, ValueError):
        mins = 3.0
    return {'blocks': sorted(blocks), 'critical': any(i in crit for i in blocks),
            'by': bys[0] if bys else field(th, 'by'), 'holder': None if v['settled'] else holder,
            'urgency': field(th, 'urgency') or first.get('urgency'), 'minutes': mins}


def build_state(hq, actor=None, minutes=None, room=None, now=None, window_days=7, fewer=False, closeout=False,
                live=None, sitting_open=False):
    """The whole state.json as a dict (STATE.md)."""
    t = now_or(now)
    folded, holons, lines, problems, cal = read_hq(hq)
    fold = folded.pop('_fold', None)
    norm = normalize(folded)
    names = holon_names(norm, holons)
    actor = actor or (holons[0].get('keeper') if holons else None) or ''
    rep, sched_note = run_schedule(folded, cal, t, holons, lines)
    plan_state, plan_note = run_plan(folded, cal, t, holons, hq, lines)
    sm = sched_map(rep)
    crit, system = path_sets(rep)
    cards_by = {item_id(c): c for c in norm.get('card', [])}

    cards = []
    for i, c in cards_by.items():
        s = sm.get(i, {})
        cards.append({'id': i, 'holon': holon_of(c), 'title': field(c, 'title'), 'kind': card_kind(c),
                      'stream': field(c, 'stream'), 'holder': field(c, 'holder'), 'minutes': field(c, 'minutes'),
                      'by': field(c, 'by'), 'stage': field(c, 'stage'), 'state': field(c, 'state'),
                      'asked': field(c, 'asked'),
                      'agent_minutes': field(c, 'agent_minutes'), 'tokens_estimate': field(c, 'tokens_estimate'),
                      'predecessors': links(c, 'predecessor'), 'successors': links(c, 'successor'),
                      'serves': links(c, 'serves'), 'audience': c.get('audience', 'holon'),
                      **{k: s.get(k) for k in ('ES', 'EF', 'LS', 'LF', 'TF', 'FF')},
                      'start': s.get('start'), 'finish': s.get('finish'), 'type': s.get('type'),
                      'within': links(c, 'within'),
                      'critical': i in crit, 'system_critical': i in system,
                      'variance_days': s.get('variance_days')})
    commitments = []
    for c in norm.get('commitment', []):
        st, gap = commitment_status(c, t)
        cid = field(c, 'card')
        commitments.append({'id': item_id(c), 'holon': holon_of(c), 'card': cid,
                            'title': field(cards_by.get(cid), 'title') if isinstance(cid, str) else None,
                            'keeper': keeper_of(c), 'by': field(c, 'by'), 'size': field(c, 'size'),
                            'witness': field(c, 'witness'), 'conditions': field(c, 'conditions'),
                            'status': st, 'gap_days': gap})
    threads = []
    live_cards = {i: c for i, c in cards_by.items() if deal_mod._live(c)}
    succ = deal_mod.successor_map(cards_by)
    for th in norm.get('thread', []):
        v = owed_mod.thread_view(th)
        threads.append({'id': item_id(th), 'holon': holon_of(th), 'anchored_to': field(th, 'anchor') or links(th, 'anchored_to'),
                        'title': str(field(th, 'title') or field(th, 'text') or '')[:120],
                        'lines': 1 + len(field(th, 'lines') or []), 'last_actor': v['last_actor'],
                        'last_ts': v['last_ts'], 'settled': v['settled'], 'to': v['to'],
                        'stake': thread_stake(th, v, live_cards, succ, crit, sm),
                        'push': None})
    decisions = [{'id': item_id(d), 'holon': holon_of(d),
                  'title': str(field(d, 'title') or field(d, 'decision') or field(d, 'text') or '')[:120],
                  'holder': field(d, 'holder') or field(d, 'to'), 'state': field(d, 'state'),
                  'ratifier': field(d, 'ratifier') or names.get(holon_of(d), {}).get('keeper')}
                 for d in norm.get('decision', [])]
    triaged = sightings_mod.triage(norm, lines=lines)
    ladders = {h['id']: ladder_mod.load_ladder(h.get('dir')) for h in holons if h.get('id')}
    qs = ladder_mod.questions(lines, holons, t, ladders)

    try:
        mins = DEFAULT_MINUTES if minutes is None else float(minutes)
    except (TypeError, ValueError):
        mins = DEFAULT_MINUTES
    bd = bodies_mod.fold(lines, t, live)
    cal_by = push_mod.calibration(lines, norm, t)
    by_line = {l.get('id'): l for l in lines if isinstance(l, dict)}
    abud = attention_mod.budget(lines, actor, t)
    for th_row, th in zip(threads, norm.get('thread', [])):
        p = field(th, 'push')
        if isinstance(p, dict):
            ln = by_line.get(item_id(th)) or {'id': item_id(th), 'body': {'push': p}, 'holon': holon_of(th)}
            sender = (ln.get('for') if isinstance(ln, dict) else None) or field(th, 'for') or field(th, 'actor')
            w = push_mod.weigh(p, abud, norm, rep, ln, t, (cal_by.get(sender) or {}).get('share'))
            th_row['push'] = {'sent': p, 'push_by': field(th, 'push_by') or {},
                              'state': 'retracted' if w['retracted'] else 'active', 'weight': w['weight'],
                              'by': w['by'], 'why_by': w.get('why_by'), 'blocks': w['blocks'], 'critical': w['critical'],
                              'cost_if_late': w['cost_if_late'], 'own': w['own'],
                              'calibration': cal_by.get(sender)}
    bd['cost']['limits'] = bodies_mod.limits(cal, (bd['cost'].get('ceiling') or {}).get('seven_day_pct'))
    the_deal = deal_mod.deal(norm, rep, actor, mins, room or [], t, holons, questions=qs, sightings=triaged,
                             bodies=bd, fewer=fewer, closeout=closeout)
    ow = owed_mod.owed(norm, actor=actor, now=t, holons=holons, questions=qs, bodies=bd['bodies'])
    kp = kept_mod.kept(norm, window_days=window_days, now=t)
    led = ledger_mod.ledger(norm, holons=holons, chain=_chain(problems))
    score = {h['id']: turn_mod.score(norm, rep, h['id']) for h in holons}
    for hid in score:
        score[hid].update(turn_mod.throughput(lines, hid, t))
    turns = norm.get('turn', [])

    def last(depth):
        span = turn_mod.DEPTH_SPAN[depth]
        ts = [field(x, 'ts') for x in turns if field(x, 'ts') and
              (field(x, 'depth') == depth or (not field(x, 'depth') and field(x, 'span') == span))]
        return max(ts) if ts else None
    lw = last('weekly')
    nxt = parse_time(lw)
    return {
        'v': 1, 'generated_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'actor': actor,
        'calendar': (rep or {}).get('calendar') and ('working-days' if 'work' in str(rep.get('calendar')) else 'calendar-days')
                    or 'calendar-days',
        'holons': [dict({k: h[k] for k in ('id', 'name', 'kind', 'keeper', 'as_of')},
                        baseline=load_baselines([h])[1].get(h['id'])) for h in holons],
        'actors': _actors(norm, lines, t, bd['bodies']),
        'cards': cards, 'commitments': commitments, 'threads': threads, 'decisions': decisions,
        'sightings': sightings_mod.by_holon(triaged, holons),
        'questions': qs,
        'bodies': bd['bodies'], 'desk': bd['desk'], 'cost': bd['cost'], 'bodies_closeout': bd.get('closeout'),
        'attention': attention_mod.state(lines, actor, weigh_cards(the_deal['cards'], norm, rep, lines, t, cal_by,
                                                                   attention_mod.budget(lines, actor, t)),
                                         t, sitting_open, in_room=bool(room), fewer=fewer),
        'calibration': cal_by,
        'study': turn_mod.study(lines, actor, t),
        'ladders': ladders,
        'tea': {k: led[k] for k in ('by_actor', 'by_holon', 'by_card', 'by_stream', 'witness', 'convertible', 'note', 'chain')},
        'discernments': led['discernments'],
        'deal': the_deal,
        'owed': {'entries': ow['entries'], 'proposals': ow['proposals']},
        'kept': {k: kp[k] for k in ('window', 'total', 'by_holon', 'by_actor', 'commitments', 'learning')},
        'score': score,
        'buffers': (rep or {}).get('buffers') or [],
        'load': (rep or {}).get('load') or [],
        'path': {'critical': sorted(crit), 'system': sorted(system), 'finish': ((rep or {}).get('path') or {}).get('finish')},
        'rooms': rooms_mod.rooms(lines, holons, actor, mins, fold, t, trust=folded.get('trust') or {},
                                 invalid=(folded.get('invalid') or []) + (folded.get('proposals') or [])),
        'roles': rooms_mod.roles(lines, holons, trust=folded.get('trust') or {}),
        'turn': {'depth_due': turn_mod.choose_depth(t, cal), 'last_daily': last('daily'),
                 'last_lunar': last('lunar'), 'last_weekly': lw, 'last_seasonal': last('seasonal'),
                 'next_weekly_due': (nxt + dt.timedelta(days=7)).date().isoformat() if nxt else None},
        'invalid': folded.get('invalid') or [], 'pending': folded.get('pending') or [],
        'problems': problems + (folded.get('problems') or []),
        'plan': plan_state,
        'notes': [n for n in (sched_note, plan_note) if n],
    }


def write_state(hq, state):
    """Write state.json whole or not at all (a temporary file, then a rename)."""
    path = os.path.join(hq, 'state.json')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1, default=str)
        f.write('\n')
    os.replace(tmp, path)
    return path


def _dial(v):
    return attention_mod.fewer_step(int(v) if str(v).isdigit() else v)


def _room(s):
    return [x.strip() for x in (s or '').split(',') if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description='The Game Engine over every holon a player holds.',
                                 epilog='Writes only HQ_DIR/state.json (state) and, on turn --freeze, '
                                        'a new plan/baseline-<n>.json. Sends nothing.')
    ap.add_argument('cmd', choices=('state', 'deal', 'owed', 'kept', 'turn', 'ledger'))
    ap.add_argument('hq', help="the player's HQ folder (a holon; cells under cells/)")
    ap.add_argument('--actor'); ap.add_argument('--minutes', type=float)
    ap.add_argument('--room', default=''); ap.add_argument('--holon'); ap.add_argument('--now')
    ap.add_argument('--days', type=float, default=7.0)
    ap.add_argument('--depth', choices=turn_mod.DEPTHS, help='turn: daily · lunar (new and full moon) · '
                    'seasonal (at the turning); default: what the date calls for, else daily')
    ap.add_argument('--freeze', action='store_true', help='turn: write the next plan/baseline-<n>.json')
    ap.add_argument('--paper', action='store_true'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--fewer', nargs='?', const='fewer', default='as set',
                    help='the dial, four steps: "as set", "fewer" (the default when the flag is bare), '
                         '"much fewer", "only what always passes" (or 0 to 3)')
    ap.add_argument('--sitting', action='store_true', help='a sitting is open: the gate deals up to at once')
    ap.add_argument('--closeout', action='store_true', help="deal the day's close-out card and past-a-day flags")
    a = ap.parse_args(argv)
    t = now_or(a.now)
    if a.cmd == 'state':
        st = build_state(a.hq, a.actor, a.minutes, _room(a.room), t, a.days, _dial(a.fewer), a.closeout,
                         sitting_open=a.sitting)
        p = write_state(a.hq, st)
        print(f"state.json written: {p} · {len(st['holons'])} holons · {len(st['cards'])} cards · "
              f"the Deal {len(st['deal']['cards'])} cards, {st['deal']['minutes_dealt']:g} of "
              f"{st['deal']['minutes_available']:g} min" + (f" · {'; '.join(st['notes'])}" if st['notes'] else ''))
        return 0
    folded, holons, lines, problems, cal = read_hq(a.hq)
    folded.pop('_fold', None)
    norm = normalize(folded)
    names = holon_names(norm, holons)
    actor = a.actor or (holons[0].get('keeper') if holons else None) or ''
    holon = a.holon or (holons[0]['id'] if holons else None)
    out = None
    if a.cmd == 'deal':
        rep, _ = run_schedule(folded, cal, t, holons, lines)
        qs = ladder_mod.questions(lines, holons, t, {h['id']: ladder_mod.load_ladder(h.get('dir')) for h in holons})
        r = deal_mod.deal(norm, rep, actor, DEFAULT_MINUTES if a.minutes is None else a.minutes, _room(a.room), t, holons,
                          questions=qs, sightings=sightings_mod.triage(norm, lines=lines),
                          bodies=bodies_mod.fold(lines, t), fewer=_dial(a.fewer), closeout=a.closeout)
        out = json.dumps(r, indent=1, ensure_ascii=False) if a.json else \
            deal_mod.render_paper(r) if a.paper else deal_mod.render(r)
    elif a.cmd == 'owed':
        qs = ladder_mod.questions(lines, holons, t, {h['id']: ladder_mod.load_ladder(h.get('dir')) for h in holons})
        r = owed_mod.owed(norm, actor=None if a.holon else actor, holon=a.holon, now=t, holons=holons, questions=qs)
        out = json.dumps(r, indent=1, ensure_ascii=False) if a.json else owed_mod.render(r, names)
    elif a.cmd == 'kept':
        r = kept_mod.kept(norm, a.holon, a.actor, a.days, t)
        out = json.dumps(r, indent=1, ensure_ascii=False) if a.json else kept_mod.render(r, names)
    elif a.cmd == 'turn':
        rep, _ = run_schedule(folded, cal, t, holons, lines)
        depth = a.depth or turn_mod.choose_depth(t, cal)
        hcal = next((h.get('calendar') for h in holons if h['id'] == holon), None) or cal
        r = turn_mod.turn(norm, rep, holon, actor, t, depth, calendar=hcal, lines_in=lines)
        if a.freeze:
            if r.get('baseline'):
                r['baseline']['written'] = _freeze(folded, holons, holon, hcal, t)
            else:
                r['freeze'] = (f'not written: a {depth} turn does not freeze; '
                               'the weekly and seasonal turns do (--depth weekly or seasonal)')
        out = json.dumps(r, indent=1, ensure_ascii=False, default=str) if a.json else \
            turn_mod.render(r, names) + (f"\n{r['freeze']}\n" if r.get('freeze') else '')
    elif a.cmd == 'ledger':
        r = ledger_mod.ledger(norm, a.holon, holons=holons, chain=_chain(problems))
        out = json.dumps(r, indent=1, ensure_ascii=False) if a.json else ledger_mod.render(r, names)
    print(out)
    return 0


def _freeze(folded, holons, holon, cal, t):
    if schedule_mod is None or not callable(getattr(schedule_mod, 'freeze', None)):
        return 'not written: schedule.py offers no freeze'
    h = next((x for x in holons if x['id'] == holon), None)
    if not h or not h.get('dir'):
        return 'not written: the holon folder is unknown'
    mine = dict(folded, cards=[c for c in folded.get('cards') or [] if c.get('holon') == holon])
    try:
        return schedule_mod.freeze(mine, None, cal, t.date().isoformat(), os.path.join(h['dir'], 'plan'))
    except Exception as e:
        return f'not written: {type(e).__name__}: {e}'


if __name__ == '__main__':
    sys.exit(main())
