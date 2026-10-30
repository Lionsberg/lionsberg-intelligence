#!/usr/bin/env python3
"""turn.py — the turn of a holon, at the depth the day calls for.

    turn(items, schedule_report, holon, actor, now=None, depth='daily', for_=None) -> dict
    choose_depth(now, calendar=None) -> 'daily' | 'lunar' | 'seasonal'
    render(turn) -> Markdown

Looking back over the work is continual, at varying depths:

  daily     the day's commitments kept and the gap on each, and one line of learning
  lunar     at each new and full moon: the fortnight's commitments kept, the learnings, and a
            story skeleton
  seasonal  at each turning: the full retrospective, the baseline freeze, the Score
  weekly    for holons that keep a weekly turn: the week's commitments kept, learnings, story, and
            a baseline freeze

The depth defaults to what the date calls for, by schedule.py's rhythms() when it offers one,
else daily. The depth is said in the turn line's body.

A turn gathers, for one holon (what each depth includes is above):

  baseline     (weekly and seasonal) the plan as scheduled now with its number n: what
               plan/baseline-<n>.json would hold, and a drafted `baseline` line (unsigned) that
               records it. This file writes nothing; `engine.py turn --freeze` asks schedule.freeze
               to write the file, and says plainly when nothing was written
  kept         commitments kept over the week (or the season: 91 days), from kept.py
  score        earned value with the Score as the currency: the schedule's own when present,
               else minutes of done cards over minutes of all cards in the holon
  lines        the window's learnings, sightings and discernments
  story        four lines for the person to finish. Every composed line is marked draft; the
               person's own words replace it. Nothing here is said on their behalf.
  event        a `turn` line (body: depth, span), built but not signed and not appended: the
               person or their agent appends it with record.py when they affirm the turn
  frame        for a season, the retrospective frame: the questions the holon answers together
  study        at the daily depth, the person's own `study` lines of the last day (the surface
               studies itself; home-only): {view: {measure: value}}, and one draft sentence per view
               ("The Deal: first act in two seconds, two reversals; proposed: nothing")
  calibration  the push protocol's calibration of each actor who pushed in this holon (push.py),
               when the raw lines are given: how many of their by-whens were real, positive only

  python3 -I turn.py ITEMS.json --holon ID --actor person:x [--depth daily|lunar|seasonal]
                    [--schedule S.json] [--json]
"""
import argparse
import datetime as dt
import json
import sys

try:
    from gamecore import (normalize, field, sched_map, path_sets, now_or, parse_time, item_id, holon_of,
                          holon_names, minutes_of, canonical_id, DONE_STATES, card_kind)
    import kept as kept_mod
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import (normalize, field, sched_map, path_sets, now_or, parse_time, item_id, holon_of,
                          holon_names, minutes_of, canonical_id, DONE_STATES, card_kind)
    import kept as kept_mod

DEPTHS = ('daily', 'lunar', 'weekly', 'seasonal')
FREEZE_DEPTHS = ('weekly', 'seasonal')      # the weekly Turn freezes a baseline; so does the seasonal
DEPTH_DAYS = {'daily': 1, 'lunar': 15, 'weekly': 7, 'seasonal': 91}   # lunar: half a synodic month, rounded up
DEPTH_SPAN = {'daily': 'day', 'lunar': 'fortnight', 'weekly': 'week', 'seasonal': 'season'}
DEPTH_WORD = {'daily': 'today', 'lunar': 'this moon', 'weekly': 'this week', 'seasonal': 'this season'}
RHYTHM_DEPTH = {'day': 'daily', 'new_moon': 'lunar', 'full_moon': 'lunar', 'turning': 'seasonal'}
ALIASES = {'day': 'daily', 'moon': 'lunar', 'fortnight': 'lunar', 'week': 'weekly', 'season': 'seasonal'}
DRAFT = 'draft'
SEASON_FRAME = [
    'What did we say we would do this season?',
    'What did we do? (the commitments kept, and the gap on each)',
    'Where was the gap, and what did it teach us?',
    'What did we see that we did not expect? (the sightings)',
    'What do we carry into the next season, and what do we let go?',
    'To whom did we pass the flame, and who passed it to us?',
]


def _sched_fields(v):
    return {k: v.get(k) for k in ('ES', 'EF', 'LS', 'LF', 'TF', 'FF', 'critical') if v.get(k) is not None}


def freeze(items, schedule_report, holon, now=None):
    """The baseline to freeze: {n, file, cards: {id: dates}, as_of, by}. Pure: writes nothing."""
    norm = normalize(items)
    n = 1 + sum(1 for b in norm.get('baseline', []) if holon_of(b) == holon)
    cards = {item_id(c): c for c in norm.get('card', []) if holon_of(c) == holon}
    frozen, by = None, 'schedule report'          # pure: schedule.freeze writes, so the engine calls it, not this
    if frozen is None:
        sm = sched_map(schedule_report)
        frozen = {'cards': {i: dict(_sched_fields(sm.get(i, {})), minutes=minutes_of(c, 0),
                                    by=field(c, 'by'), title=field(c, 'title'))
                            for i, c in cards.items()}}
    frozen = dict(frozen)
    frozen.update({'n': n, 'file': f'plan/baseline-{n}.json', 'holon': holon, 'by': by,
                   'as_of': (schedule_report or {}).get('as_of') if isinstance(schedule_report, dict) else None,
                   'frozen_at': now_or(now).isoformat(timespec='seconds')})
    return frozen


def score(items, schedule_report, holon):
    """Earned value with the Score as the currency, for one holon."""
    rep = schedule_report if isinstance(schedule_report, dict) else {}
    sc = rep.get('score')
    if isinstance(sc, dict) and isinstance(sc.get(holon), dict):
        return dict(sc[holon], by='schedule.py earned value')
    norm = normalize(items)
    cs = [c for c in norm.get('card', []) if holon_of(c) == holon]
    total = sum(minutes_of(c, 0) for c in cs)
    done = sum(minutes_of(c, 0) for c in cs if str(field(c, 'state') or '').lower() in DONE_STATES - {'released', 'declined'})
    return {'earned': round(done, 1), 'planned': round(total, 1), 'minutes_done': round(done, 1),
            'minutes_total': round(total, 1), 'spi': None, 'share': round(done / total, 3) if total else None,
            'by': 'cards done ÷ cards held (no schedule earned value given)'}


REWORK_TYPES = ('supersede', 'undo', 'return')


def throughput(lines, holon, now=None, days=7, person=None):
    """Useful throughput as rate times yield, for one holon and the week ending at `now`.

    yield: made (commit lines in the week) · kept_as_said (of those, a kept or witness line at or
    before the by-when) · rework (supersede, undo and returned-card lines in the week) · share
    (kept_as_said / made, null when made is 0). rate: acts (people's own lines in the week) ·
    person_hours (distinct clock hours with a line, per person, summed) · per_hour (null when 0).
    Status: proposal. Read from the lines, never from a remembered count."""
    t = now_or(now)
    t0 = t - dt.timedelta(days=days)
    ls = [l for l in lines or [] if isinstance(l, dict) and l.get('holon') == holon]
    by_id = {l.get('id'): l for l in ls if l.get('id')}

    def body(l):
        return l.get('body') if isinstance(l.get('body'), dict) else {}

    def links(l):
        return l.get('links') if isinstance(l.get('links'), dict) else {}

    def week(l):
        return _in(l.get('ts'), t0, t)

    def one(v):
        return (v[0] if v else None) if isinstance(v, list) else v

    made = [l for l in ls if l.get('type') == 'commit' and week(l)]
    first_kept = {}
    for l in ls:
        if l.get('type') not in ('kept', 'witness'):
            continue
        x = parse_time(l.get('ts'))
        if x is None:
            continue
        b, k = body(l), links(l)
        ref = one(b.get('commitment')) or one(k.get('fulfils')) or one(k.get('witnesses'))
        tgt = by_id.get(ref)
        if tgt is not None and tgt.get('type') == 'kept':   # a witness of the kept line
            ref = one(body(tgt).get('commitment')) or one(links(tgt).get('fulfils'))
        if ref and (ref not in first_kept or x < first_kept[ref]):
            first_kept[ref] = x
    kept_as_said = 0
    for c in made:
        end, k = parse_time(body(c).get('by')), first_kept.get(c.get('id'))   # a bare date runs to its day's end
        if end is not None and k is not None and k <= end:
            kept_as_said += 1
    rework = sum(1 for l in ls if week(l) and (l.get('type') in REWORK_TYPES or body(l).get('undo')
                                               or str(body(l).get('state') or '') == 'returned'))
    acts, hours = 0, set()
    for l in ls:
        a = str(l.get('actor') or '')
        if not a.startswith('person:') or l.get('for', a) != a or (person and a != person) or not week(l):
            continue
        acts += 1
        x = parse_time(l.get('ts'))
        hours.add((a, x.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H')))
    n = len(made)
    return {'yield': {'made': n, 'kept_as_said': kept_as_said, 'rework': rework,
                      'share': round(kept_as_said / n, 3) if n else None},
            'rate': {'acts': acts, 'person_hours': len(hours),
                     'per_hour': round(acts / len(hours), 3) if hours else None}}


def _in(ts, t0, t1):
    x = parse_time(ts)
    return x is not None and t0 <= x <= t1


def make_line(actor, for_, holon, type_, body, now):
    """A line, unsigned and not appended. record.make_line when present, else built here."""
    try:
        import record
        return record.make_line(actor, for_, holon, type_, body, ts=now.isoformat(timespec='seconds'))
    except Exception:
        line = {'v': 1, 'ts': now.isoformat(timespec='seconds'), 'actor': actor or '', 'for': for_ or actor or '',
                'holon': holon or '', 'type': type_, 'body': body, 'links': {}, 'audience': 'holon',
                'reason': 'human', 'prev': ''}
        line['id'] = canonical_id(line)
        line['sig'] = ''
        return line


def make_event(actor, for_, holon, body, now):
    """The `turn` line, unsigned and not appended."""
    return make_line(actor, for_, holon, 'turn', body, now)


STUDY_MEASURES = ('first_act_ms', 'reversals', 'attention_switches', 'one_breath', 'workload_words')
VIEW_NAMES = {'deal': 'The Deal', 'map': 'The Map', 'room': 'The Room', 'bodies': 'The Bodies view',
              'threads': 'The Threads view', 'ledger': 'The Ledger', 'turn': 'The Turn', 'dock': 'The dock'}
_NUM = {0: 'no', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
        10: 'ten'}


def study(lines, person=None, now=None, days=1):
    """{view: {measure: value}} from the person's own `study` lines of the last day (newest wins).

    A study line counts only when a person wrote it for themselves (never an agent's, never from
    untrusted text); it is home-only and never leaves the holon (SCHEMA, The surface studies itself)."""
    t = now_or(now)
    t0 = t - dt.timedelta(days=days)
    out, seen = {}, {}
    for l in lines or []:
        if not isinstance(l, dict) or l.get('type') != 'study' or l.get('reason') == 'untrusted':
            continue
        a = l.get('actor')
        if not str(a or '').startswith('person:') or l.get('for') != a or (person and a != person):
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        when = parse_time(b.get('as_of') or l.get('ts'))
        view, m = b.get('view'), b.get('measure')
        if when is None or not (t0 <= when <= t) or not isinstance(view, str) or m not in STUDY_MEASURES:
            continue
        key = (view, m)
        if key not in seen or when >= seen[key]:
            seen[key] = when
            out.setdefault(view, {})[m] = b.get('value')
    return out


def _n(v):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        return str(v)
    return _NUM.get(v, str(v))


def study_sentence(view, measures):
    """One draft sentence for a view: what the measures say, and what is proposed (often nothing)."""
    bits, proposals = [], []
    m = measures or {}
    if m.get('first_act_ms') is not None:
        try:
            sec = float(m['first_act_ms']) / 1000.0
        except (TypeError, ValueError):
            sec = None
        if sec is not None:
            bits.append('first act in under a second' if sec < 1 else
                        f'first act in {_n(sec)} second{"s" if round(sec) != 1 else ""}')
            if sec > 10:
                proposals.append('look at what the eye meets first')
    if m.get('reversals') is not None:
        r = m['reversals']
        bits.append(f'{_n(r)} reversal{"s" if _n(r) != "one" else ""}')
        if isinstance(r, (int, float)) and r >= 3:
            proposals.append('ask why the first choice was undone')
    if m.get('attention_switches') is not None:
        a = m['attention_switches']
        bits.append(f'{_n(a)} attention switch{"es" if _n(a) != "one" else ""}')
        if isinstance(a, (int, float)) and a > 5:
            proposals.append('gather what it sends the eye to')
    if m.get('one_breath') is not None:
        ok = bool(m['one_breath'])
        bits.append('said in one breath' if ok else 'not yet said in one breath')
        if not ok:
            proposals.append('shorten its first line')
    if m.get('workload_words') is not None:
        w = m['workload_words']
        bits.append(f'{_n(w)} words of workload')
        if isinstance(w, (int, float)) and w > 60:
            proposals.append('cut the words it asks the person to read')
    name = VIEW_NAMES.get(view, view)
    return f'{name}: {", ".join(bits) or "measured"}; proposed: {"; ".join(proposals) or "nothing"}'


def norm_depth(depth):
    d = str(depth or '').strip().lower()
    d = ALIASES.get(d, d)
    return d if d in DEPTHS else 'daily'


def choose_depth(now=None, calendar=None):
    """What the date calls for: the deepest rhythm schedule.rhythms() finds on the day (turning ->
    seasonal; new or full moon -> lunar; day -> daily), else daily when it is absent."""
    t = now_or(now)
    try:
        import schedule as sched_mod
        fn = getattr(sched_mod, 'rhythms', None)
    except Exception:
        fn = None
    if not callable(fn):
        return 'daily'
    got = None
    for args in ((t.date().isoformat(), calendar), (t.date().isoformat(),), ()):
        try:
            got = fn(*args)
            break
        except TypeError:
            continue
        except Exception:
            return 'daily'
    due = []
    if isinstance(got, str):
        due = [got]
    elif isinstance(got, dict):
        if isinstance(got.get('depth'), str):
            due = [got['depth']]
        else:
            due = [k for k, v in got.items() if v is True or (isinstance(v, dict) and v.get('due'))]
            due += [x for x in (got.get('due') or []) if isinstance(x, str)]
    elif isinstance(got, list):                  # schedule.rhythms: [{kind, date}] for the day
        day = t.date().isoformat()
        for x in got:
            if isinstance(x, str):
                due.append(x)
            elif isinstance(x, dict) and str(x.get('date') or day)[:10] == day:
                due.append(RHYTHM_DEPTH.get(str(x.get('kind') or ''), x.get('depth') or x.get('name') or ''))
    known = {ALIASES.get(x.strip().lower(), x.strip().lower()) for x in due if isinstance(x, str)}
    due = known & set(DEPTHS)                     # names it does not know are ignored, never guessed
    for d in ('seasonal', 'lunar', 'weekly', 'daily'):
        if d in due:
            return d
    return 'daily'


def _window_days(depth, t, calendar=None):
    if depth == 'seasonal':
        try:
            import schedule as sched_mod
            gc = sched_mod.gameclock(t.date(), calendar)
            if isinstance(gc, dict) and isinstance(gc.get('season_length'), (int, float)):
                return float(gc['season_length'])
        except Exception:
            pass
    return float(DEPTH_DAYS[depth])


def turn(items, schedule_report, holon, actor, now=None, depth='daily', for_=None, calendar=None, lines_in=None):
    norm = normalize(items)
    t = now_or(now)
    depth = norm_depth(depth)
    days = _window_days(depth, t, calendar)
    t0 = t - dt.timedelta(days=days)
    k = kept_mod.kept(norm, holon=holon, window_days=days, now=t)
    deep = depth == 'seasonal'
    sc = score(norm, schedule_report, holon) if deep else None
    base = freeze(norm, schedule_report, holon, t) if depth in FREEZE_DEPTHS else None
    if base is not None:
        base['line'] = make_line(actor, for_ or actor, holon, 'baseline',
                                 {'n': base['n'], 'file': base['file'], 'cards': sorted(base.get('cards') or {})}, t)
    learn = k.get('learning') or []
    lines = {
        'learn': learn[:1] if depth == 'daily' else learn,
        'sight': [] if depth == 'daily' else
        [{'id': item_id(s), 'actor': field(s, 'actor'), 'text': str(field(s, 'text') or '')[:280]}
         for s in norm.get('sighting', []) if holon_of(s) == holon and _in(field(s, 'ts'), t0, t)],
        'discern': [] if depth == 'daily' else
        [{'id': item_id(d), 'state': field(d, 'state'), 'model': field(d, 'model')}
         for d in norm.get('discern', []) if holon_of(d) == holon and _in(field(d, 'ts'), t0, t)
         and str(field(d, 'state') or '') != 'routed'],
    }
    tot = k.get('total') or {}
    due = tot.get('kept', 0) + tot.get('kept_unwitnessed', 0) + tot.get('broken', 0)
    kept_line = (f"We kept {tot.get('kept', 0)} of {due} commitments, witnessed"
                 + (f", {tot['kept_unwitnessed']} awaiting a witness" if tot.get('kept_unwitnessed') else '') + '.')
    learned = 'We learned: ' + (learn[0]['text'].rstrip('.') + '.' if learn else '…')
    if depth == 'daily':
        story = [{'line': kept_line, 'status': DRAFT}, {'line': learned, 'status': DRAFT}]
    else:
        cards = [c for c in norm.get('card', []) if holon_of(c) == holon]
        willed = [str(field(c, 'title')) for c in cards if field(c, 'stage') in ('will', 'did') and field(c, 'title')][:3]
        crit, _ = path_sets(schedule_report)
        nxt = [str(field(c, 'title')) for c in cards if item_id(c) in crit and field(c, 'title')
               and str(field(c, 'state') or '').lower() not in DONE_STATES][:1]
        story = [
            {'line': f'{DEPTH_WORD[depth].capitalize()} we set out to: ' + ('; '.join(willed) + '.' if willed else '…'),
             'status': DRAFT},
            {'line': kept_line, 'status': DRAFT},
            {'line': learned, 'status': DRAFT},
            {'line': 'Next we ' + (f'take up "{nxt[0]}".' if nxt else '…'), 'status': DRAFT},
        ]
    gaps = [{'id': c['id'], 'title': c['title'], 'status': c['status'], 'gap_days': c['gap_days']}
            for c in k.get('commitments') or []]
    body = {'depth': depth, 'span': DEPTH_SPAN[depth], 'from': t0.isoformat(timespec='seconds'),
            'to': t.isoformat(timespec='seconds'),
            'kept': {x: tot.get(x) for x in ('made', 'kept', 'kept_unwitnessed', 'broken', 'released', 'share')}}
    if deep:
        body['score'] = {x: sc.get(x) for x in ('earned', 'planned', 'spi', 'share') if sc.get(x) is not None}
    if base is not None:
        body['baseline'] = base['n']
    studied = study(lines_in, actor, t) if depth == 'daily' and lines_in else {}
    study_lines = [{'line': study_sentence(v, m), 'status': DRAFT} for v, m in sorted(studied.items())]
    try:                                         # the push protocol's calibration, measured at the Turn
        import push as push_mod
        mine = [l for l in lines_in or [] if isinstance(l, dict) and (l.get('holon') or l.get('_held_in')) == holon]
        cal = push_mod.calibration(mine, norm, t) if mine else {}
    except ImportError:
        cal = {}
    return {'holon': holon, 'depth': depth, 'span': DEPTH_SPAN[depth], 'calibration': cal,
            'study': studied, 'study_lines': study_lines,
            'window': {'from': body['from'], 'to': body['to']},
            'baseline': base, 'kept': k, 'gaps': gaps, 'score': sc, 'lines': lines, 'story': story,
            'event': make_event(actor, for_ or actor, holon, body, t),
            'frame': SEASON_FRAME if deep else None,
            'note': 'Story lines are drafts for the person to finish. The turn line is unsigned until they affirm it.'}


def render(r, names=None):
    names = names or {}
    hn = names.get(r.get('holon'), {}).get('name') or str(r.get('holon') or '')[:8]
    w = r.get('window') or {}
    depth = r.get('depth') or 'daily'
    out = [f"# The {depth} turn — {hn}", f"*{w.get('from', '')[:10]} to {w.get('to', '')[:10]}*", '']
    out += ['## In your words (drafts to finish)', '']
    out += [f"{i}. {s['line']}  *({s['status']})*" for i, s in enumerate(r.get('story') or [], 1)]
    if r.get('study_lines'):
        out += ['', '## How the views served you today (drafts)', '']
        out += [f"- {x['line']}  *({x['status']})*" for x in r['study_lines']]
    gaps = r.get('gaps') or []
    if gaps:
        out += ['', '## Each commitment, and the gap', '']
        for g in gaps:
            gw = kept_mod.gap_words(g.get('gap_days'))
            out.append(f"- {g['title']} · {kept_mod.WORDS.get(g['status'], g['status'])}" + (f' · {gw}' if gw else ''))
    elif depth == 'daily':
        out += ['', 'No commitment fell due today.']
    sc = r.get('score')
    if sc:
        out += ['', '## The Score', '',
                f"Earned {sc.get('earned') or 0:g} minutes of work"
                + (f" of {sc['planned']:g} planned" if isinstance(sc.get('planned'), (int, float)) else '')
                + f" ({sc.get('by', '')})."]
    b = r.get('baseline')
    if b:
        w = b.get('written')
        said = (f"Baseline {b.get('n')} written: `{w}`." if w and not str(w).startswith('not written')
                else f"Baseline {b.get('n')} is ready to freeze at `{b.get('file')}`"
                     + (f" ({w})." if w else " (run with --freeze to write it)."))
        out += ['', said, f"A `baseline` line is drafted for you to sign: {str((b.get('line') or {}).get('id', ''))[:12]}."]
    ln = r.get('lines') or {}
    if depth != 'daily':
        for key, title in (('learn', 'Learned'), ('sight', 'Seen')):
            if ln.get(key):
                out += ['', f'## {title}', ''] + [f"- {x.get('text')}" for x in ln[key]]
        if ln.get('discern'):
            out += ['', f"Discernment {DEPTH_WORD.get(depth, '')}: {len(ln['discern'])} judgments."]
    if r.get('frame'):
        out += ['', '## The seasonal retrospective', ''] + [f'- {q}' for q in r['frame']]
    out += ['', f"*{r.get('note', '')}*"]
    return '\n'.join(out) + '\n'


def _main(argv=None):
    ap = argparse.ArgumentParser(description='The weekly or seasonal turn of one holon, from folded items (JSON).')
    ap.add_argument('items'); ap.add_argument('--holon', required=True); ap.add_argument('--actor', required=True)
    ap.add_argument('--depth', choices=DEPTHS, help='default: what the date calls for (schedule.rhythms), else daily')
    ap.add_argument('--schedule'); ap.add_argument('--now')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        with open(a.items, encoding='utf-8') as f:
            items = json.load(f)
        rep = None
        if a.schedule:
            with open(a.schedule, encoding='utf-8') as f:
                rep = json.load(f)
    except (OSError, ValueError) as e:
        print(f'turn: cannot read input: {e}', file=sys.stderr); return 2
    r = turn(items, rep, a.holon, a.actor, a.now, a.depth or choose_depth(a.now))
    print(json.dumps(r, indent=1, ensure_ascii=False) if a.json else render(r, holon_names(normalize(items))))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
