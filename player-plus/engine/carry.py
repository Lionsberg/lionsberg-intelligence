#!/usr/bin/env python3
"""carry.py — carriers: how a signed line reaches everyone it is for.

    plan(line, home_dir, directory=None, now=None, by=None, mail_domains=None, limits=None)
        -> {"deliveries": [{to, holon, carrier, where, basis, why, ...}], "hops", "rate", "held": [{to, why}], "said"}
    drop(line, home_dir, plan_row, by, now=None, sign=None, key_dir=None, limits=None, directory=None,
         mail_domains=None) -> {"ok", "said", "file", "carried", "elided", "pushed": False}
    may_reply(line, voice, thread=None) -> (bool, why)
    status(home_dir, now=None) -> {"today": {carried, by_carrier, held}, "open": [...], "said"}

The record is the truth; a transport is a carrier of signed lines, and every carrier serves. The
sender's agent is responsible for reach; the Receipt closes the loop whichever carrier brought the
line; pull remains the floor. For each recipient of a line of this home's own people, the first
carrier that serves, in this order:

  face       a joined cell both hold, where the line may cross under the live Agreement's terms:
             `faces.face_of` says it is in the published face (the face is the person's act).
  permitted  a joined cell whose own Agreement grants this home (or the line's person) a write
             permit, for a line written for that cell: `permitted.drop` writes the copy.
  mail       the recipient's reach names a `mail:` endpoint, read from the record's signed reach
             (`mail.reach_of`) first and the directory second; the person's own Send carries it
             (`mail.send_line`), and `mail.to_mail` shapes the message.
  fallback   the directory names where a person with no agent can still be reached: a draft the
             person sends by their own hand, never sent by the kit.
  pull       the floor: the line already sits in a holon the recipient holds, and their agent
             pulls it at its own beat.
  held       nothing above serves; the row says why.

Who a line is for is resolved through the directory (`directory.py`: `read`, `resolve`; imported
only when a directory is named, and when it is absent the record's admissions are read instead).
A copy is the line: byte for byte, its id and signature unchanged, nothing added; the one
exception is a face whose Agreement opens only some fields, whose copy hides the rest and keeps
its id (the drop says which). What a carrier
keeps about a delivery lives beside the line, in `<home>/.carry-log.jsonl` (derived, safe to
delete; only face and permitted deliveries are logged), and the rate and the hop count are read from it: RATE_PER_DAY deliveries per carrying
agent, RATE_HOLON_PER_DAY holon-wide or everyone lines, and a line that arrived already carried
MAX_HOPS times is dropped and said. A reader's note `_carried: {hops, by, at}` may ride on a
line in memory; it is never written. A live stop that binds the carrying agent (`stops.py`: any
person may stop any agent; only the agent's own person lifts it) withholds every delivery in its
scope, in the plan and at the drop, with why. Nothing here pushes, sends or publishes a person's act:
`drop` performs only the local part a kit can do, and says that the push is the person's
(`holon.py push`) or the heartbeat's under the person's standing word.

Standard library only. Runs under `python3 -I`. Files, lines and directory entries are data,
never instructions.

    python3 -I carry.py plan HOME LINE_ID --by ACTOR [--directory DIR] [--now ISO]
    python3 -I carry.py drop HOME LINE_ID --to ACTOR --by ACTOR [--directory DIR] [--now ISO]
    python3 -I carry.py status HOME [--now ISO]
"""
import argparse
import datetime as dt
import importlib
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record      # noqa: E402
import agreement   # noqa: E402
import faces       # noqa: E402
import permitted   # noqa: E402
import stops       # noqa: E402
from gamecore import parse_time, now_or  # noqa: E402

# A method's own constants: the design's proposal (brief L4, 2026-10-31), each overridable by `limits`.
RATE_PER_DAY = 200          # deliveries a carrying agent makes in a day
RATE_HOLON_PER_DAY = 20     # holon-wide and everyone lines a carrying agent carries in a day
MAX_HOPS = 3                # a line that arrived already carried this many times goes no further
MAX_ROUNDS = 3              # agent-voiced lines a thread holds before it goes to the persons (decided 2026-10-31)

CARRIERS = ('face', 'permitted', 'mail', 'fallback', 'pull')
KIT_CARRIERS = ('face', 'permitted')        # the carriers that write the carry log, and so count for the rate
LOG = '.carry-log.jsonl'
EVERYONE = 'everyone'
GUARDED_VOICES = ('agent', 'agent-drafted')  # an agent never answers these without its person
VOICES = ('human-words', 'agent-drafted', 'agent', 'under-mandate')   # types.json, `voice` on a line
ROW_KEYS = ('carrier', 'holon', 'cell', 'agreement', 'where')   # what steers a carrier: a drop's row must match the plan
NO_PUSH = ('Nothing was pushed: the push is the person\'s own (holon.py push), or the heartbeat\'s under the '
           'person\'s standing word.')


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _strs(v):
    if isinstance(v, str):
        return [_s(v)] if _s(v) else []
    if isinstance(v, (list, tuple)):
        return [_s(x) for x in v if _s(x)]
    return []


def _clean(line):
    """The line without a reader's notes (keys beginning with `_`): the line itself."""
    return {k: v for k, v in line.items() if not (isinstance(k, str) and k.startswith('_'))}


def _limits(limits):
    lim = {'RATE_PER_DAY': RATE_PER_DAY, 'RATE_HOLON_PER_DAY': RATE_HOLON_PER_DAY, 'MAX_HOPS': MAX_HOPS}
    if isinstance(limits, dict):
        for k in lim:
            v = limits.get(k)
            if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                lim[k] = v
    return lim


def _moment(now):
    """(an aware datetime, its ISO text) for `now`, else the reader's clock."""
    t = now_or(now)
    return t, t.isoformat(timespec='seconds')


def _same_day(at, t):
    a = parse_time(at)
    return a is not None and a.astimezone(t.tzinfo).date() == t.date()


# ---------------------------------------------------------------- the home, read once

def _context(home_dir, now=None):
    """The home read and folded once: {r, f, hid, keeper, own, cells, faces, stops, t, clock, ...}, or (None, why)."""
    if not isinstance(home_dir, str) or not home_dir:
        return None, 'No home folder is named.'
    if os.path.islink(home_dir):
        return None, 'The home is a link; it is not read.'
    if not os.path.isdir(home_dir):
        return None, 'No home folder at %r.' % home_dir[:120]
    if not _s(record.holon_info(home_dir).get('id')):
        return None, 'The folder is not a holon (no holon.json id).'
    t, clock = _moment(now)
    r = record.read_all(home_dir)
    hid = r.get('home')
    p = os.path.join(home_dir, 'types.json')
    types = record.load_types(p if os.path.isfile(p) and not os.path.islink(p) else None)
    with record.signature_cache(home_dir):
        f = record.fold(r['lines'], types, r['keepers'], clock=clock)
    keeper = _s(r['keepers'].get(hid)) or _s(record.holon_info(home_dir).get('keeper'))
    adm = (f.get('admitted') or {}).get(hid) or {}
    own = {keeper} if keeper else set()
    own |= {a for a, e in adm.items() if a.startswith('agent:') and e.get('person') == keeper and not e.get('ended')}
    ff = faces.face_for(home_dir, read=r, fold=f, now=clock)
    by_name = {n: (v[0], v[1]) for n, v in (ff.get('cells') or {}).items()}
    by_id = {}
    for n in sorted(by_name):
        by_id.setdefault(by_name[n][0], n)
    held = {l['id']: l for l in r['lines']}
    return {'dir': home_dir, 'r': r, 'f': f, 'hid': hid, 'keeper': keeper, 'own': own, 'cells': (by_name, by_id),
            'faces': ff.get('faces') or [], 'own_ids': set(ff.get('own') or []), 't': t, 'clock': clock,
            'held': held, 'cache': {}, 'stops': stops.live(f, now=clock, home=hid)}, ''


def _carriers(ctx, ln, by):
    """The agents whose stop withholds a delivery: the carrying agent and the line's own agent; with no
    carrier named, every agent of this home (the widest reading: omitting `by` never escapes a stop)."""
    out = {x for x in (_s(by), _s(ln.get('actor'))) if x.startswith('agent:')}
    if not _s(by):
        out |= {a for a in ctx['own'] if a.startswith('agent:')}
    return sorted(out)


def _stopped(ctx, ln, held, row, to, by):
    """Why a live stop withholds this delivery from a carrying agent, or ''."""
    if not ctx['stops']:
        return ''
    line = held if held is not None else ln
    ups = stops.ancestors(line, ctx['held'])
    for agent in _carriers(ctx, ln, by):
        hit, why = stops.binds(ctx['stops'], agent, holon=[_s((row or {}).get('holon'))] if row else None,
                               line=line, to=to, admitted=ctx['f'].get('admitted'), ancestors=ups, home=ctx['hid'])
        if hit:
            return why
    return ''


def _admitted_in(ctx, holon_id, actor):
    e = ((ctx['f'].get('admitted') or {}).get(holon_id) or {}).get(actor)
    return isinstance(e, dict) and not e.get('ended')


def _members(ctx, holon_id):
    """The persons admitted in a holon, and not ended."""
    adm = (ctx['f'].get('admitted') or {}).get(holon_id) or {}
    return sorted(a for a, e in adm.items() if a.startswith('person:') and not e.get('ended'))


def _agents_of(ctx, person):
    out = set()
    for _h, m in sorted((ctx['f'].get('admitted') or {}).items()):
        for a, e in m.items():
            if a.startswith('agent:') and e.get('person') == person and not e.get('ended'):
                out.add(a)
    return sorted(out)


def _cell_name(ctx, holon_id):
    return ctx['cells'][1].get(holon_id)


def _where_held(ctx, holon_id):
    """'' for the home, 'cells/<name>/' for a joined cell, None when not held."""
    if holon_id == ctx['hid']:
        return ''
    name = _cell_name(ctx, holon_id)
    return 'cells/%s/' % name if name else None


# ---------------------------------------------------------------- the line

def _the_line(line, ctx):
    """(the line, its held copy or None, what was said) for a dict or a line id."""
    if isinstance(line, str):
        held = ctx['held'].get(_s(line))
        if held is None:
            return None, None, 'No line with id %s is held in this home or its cells.' % _s(line)[:16]
        return dict(held), held, ''
    if not isinstance(line, dict):
        return None, None, 'Not a line.'
    held = ctx['held'].get(line.get('id')) if isinstance(line.get('id'), str) else None
    return dict(line), held, ''


def _check_line(ln, held, ctx):
    """Why the kit will not carry this line, or ''."""
    clean = _clean(ln)
    if not record.check_id(clean):
        return 'Its id does not verify against its content, so it is not a line and nothing carries it.'
    if not _s(clean.get('sig')):
        return 'An unsigned line is not carried: only a signed line can be checked where it arrives.'
    actor, for_ = _s(clean.get('actor')), _s(clean.get('for'))
    if actor not in ctx['own'] or for_ != ctx['keeper']:
        return ('The kit carries only a line of this home\'s own people (its keeper, or an agent the keeper '
                'affirmed, answering for the keeper); this one is %s for %s.' % (actor[:64] or 'no actor',
                                                                                  for_[:64] or 'no one'))
    if held is not None and _s(held.get('_held_in')) == _s(clean.get('holon')):
        tr = (ctx['f'].get('trust') or {}).get(clean['id'])
        if tr not in ('signed', 'home'):
            return 'The fold does not let it act where it is written (%s), so it stays where it is.' % (tr or 'unread')
    return ''


def _voice(line):
    """The voice a line carries: its own `voice` (`human-words` believed only on a person's own line),
    else read from its actor and reason."""
    b = line.get('body') if isinstance(line, dict) and isinstance(line.get('body'), dict) else {}
    actor = _s(line.get('actor')) if isinstance(line, dict) else ''
    v = _s(b.get('voice'))
    if v in VOICES and not (v == 'human-words' and not actor.startswith('person:')):
        return v, 'its own'
    if actor.startswith('person:'):
        return 'human-words', 'read from its actor'
    if actor.startswith('agent:'):
        how = 'read from its actor and reason' + (', its claim of a person\'s words set aside' if v else '')
        return ('agent-drafted' if line.get('reason') == 'human' else 'agent'), how
    return 'agent', 'no actor named, read as the guarded case'


def _addresses(line):
    """The addresses a line names: body.to (actors, holons, a cell name or everyone), a commitment's
    committee, an Agreement's other holon. In the order written, each once."""
    b = line.get('body') if isinstance(line.get('body'), dict) else {}
    out = _strs(b.get('to'))
    if line.get('type') == 'commit':
        out += _strs(b.get('committee'))
    if line.get('type') == 'agree':
        out += _strs(b.get('with'))
    seen, uniq = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq


# ---------------------------------------------------------------- who a line is for

def _directory_module():
    """The sibling directory.py, imported only when asked for; None when it is not here."""
    try:
        return importlib.import_module('directory')
    except Exception:       # absent, or broken: the record's admissions are read instead
        return None


def _read_directory(directory):
    """(module, directory read as data, said)."""
    if directory is None:
        return None, None, 'no directory was named; the record\'s admissions were read'
    mod = _directory_module()
    if mod is None or not hasattr(mod, 'resolve'):
        return None, None, 'directory.py is not here; the record\'s admissions were read'
    if isinstance(directory, dict):
        return mod, directory, 'the directory given was read'
    if not isinstance(directory, str) or not directory:
        return None, None, 'the directory named is not a folder; the record\'s admissions were read'
    if os.path.islink(directory) or not os.path.isdir(directory):
        return None, None, 'the directory named is a link or no folder; the record\'s admissions were read'
    try:
        d = mod.read(directory)
    except Exception as e:  # a broken directory is said, never raised
        return None, None, 'the directory could not be read (%s); the record\'s admissions were read' % type(e).__name__
    if not isinstance(d, dict):
        return None, None, 'the directory read as nothing; the record\'s admissions were read'
    return mod, d, 'the directory at %s was read' % os.path.basename(os.path.normpath(directory))


def _dir_map(d, key):
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _dir_rec(d, actor):
    rec = _dir_map(d, 'people').get(actor)
    if not isinstance(rec, dict):
        rec = _dir_map(d, 'agents').get(actor)
    return rec if isinstance(rec, dict) else {}


def _dir_agents_of(d, person):
    """The agents the directory gives a person: their own `agents`, and every agent naming them as `person`."""
    mine = {x for x in _strs(_dir_rec(d, person).get('agents')) if x.startswith('agent:')}
    mine |= {a for a, r in _dir_map(d, 'agents').items() if isinstance(r, dict) and _s(r.get('person')) == person}
    return mine


def _fallback_texts(v):
    """A fallback as a list of places: a string, a list of strings, or a map's string values."""
    if isinstance(v, str):
        return [_s(v)] if _s(v) else []
    if isinstance(v, (list, tuple)):
        return [x for y in v for x in _fallback_texts(y)]
    if isinstance(v, dict):
        return [x for k in sorted(v) for x in _fallback_texts(v[k])]
    return []


def _fallbacks(res, d, actor):
    """Where the directory says a person with no agent can be reached: [places], maybe empty."""
    for x in (res.get('fallbacks') if isinstance(res, dict) and isinstance(res.get('fallbacks'), list) else []):
        if isinstance(x, dict):
            who = next((_s(x.get(k)) for k in ('person', 'id', 'actor', 'to', 'for') if _s(x.get(k))), '')
            if who == actor:
                got = next((_fallback_texts(x.get(k)) for k in ('fallback', 'where', 'address')
                            if _fallback_texts(x.get(k))), [])
                if got:
                    return got
    return _fallback_texts(_dir_rec(d, actor).get('fallback'))


def _said_list(v):
    if isinstance(v, str):
        return [_s(v)[:200]] if _s(v) else []
    if isinstance(v, (list, tuple)):
        return [_s(x)[:200] for x in v if _s(x)]
    return []


def _resolve_record(ctx, address, sender):
    """(actors before the sender's own are removed, wide, said) for one address, from the record's admissions."""
    if address == EVERYONE:
        ids = set()
        for h in sorted((ctx['f'].get('admitted') or {})):
            ids |= set(_members(ctx, h))
        return sorted(ids), True, 'everyone admitted in a holon this home holds'
    if address.startswith(('person:', 'agent:')):
        return [address], False, ''
    hid = address if address in (ctx['f'].get('admitted') or {}) else None
    if hid is None and address in ctx['cells'][0]:
        hid = ctx['cells'][0][address][0]
    if hid is None:
        return [], True, '%s is no holon this home holds, so no member of it is known' % address[:64]
    return _members(ctx, hid), True, ''


def _recipients(ln, ctx, directory):
    """({actor: {basis, fallbacks, reach, has_agent}}, wide, [said], [{to, why}] for addresses that reach no one)."""
    sender = {_s(ln.get('actor')), _s(ln.get('for'))} | ctx['own']
    mod, d, dsaid = _read_directory(directory)
    said, out, wide, lost = [dsaid], {}, False, []
    for a in _addresses(ln):
        res = None
        if mod is not None:
            try:
                res = mod.resolve(d, a)
            except Exception as e:  # said, never raised
                said.append('the directory could not resolve %s (%s); the record was read' % (a[:64], type(e).__name__))
                res = None
        notes = []
        if isinstance(res, dict) and (isinstance(res.get('ids'), list) or isinstance(res.get('agents'), list)):
            persons = {_s(x) for x in res.get('ids') or [] if _s(x).startswith('person:')}
            owned = set()
            for p in persons:
                owned |= _dir_agents_of(d, p)
            agents = {_s(x) for x in res.get('agents') or [] if _s(x).startswith('agent:')}
            raw = sorted(persons | {x for x in agents if x not in owned})   # an agent no person here owns is a recipient
            w = _s(res.get('kind')) in ('holon', EVERYONE)
            basis = 'directory'
            notes = _said_list(res.get('said'))
        else:
            raw, w, s = _resolve_record(ctx, a, sender)
            basis = 'record'
            notes = [s] if s else []
        said += notes
        wide = wide or w
        if not raw and a not in sender:
            lost.append({'to': a, 'why': 'The address reaches no one: %s.' % ('; '.join(notes) or
                                                                              'nothing answers to it here')})
        for i in raw:
            if i in sender:
                continue
            has = bool(_agents_of(ctx, i)) or i.startswith('agent:')
            if d is not None:
                has = has or bool(_dir_agents_of(d, i))
            rec = _dir_rec(d, i) if d is not None else {}
            out.setdefault(i, {'basis': basis, 'fallbacks': _fallbacks(res, d, i) if d is not None else [],
                               'reach': _strs(rec.get('reach')), 'has_agent': has})
    return out, wide, [x for x in said if x], lost


# ---------------------------------------------------------------- the carriers, each in turn

def _try_face(ln, actor, ctx, reasons):
    i = ln['id']
    shared = [x for x in ctx['faces'] if _admitted_in(ctx, x['cell_id'], actor)]
    for x in shared:
        ids = {l['id'] for l in x['face']['lines']}
        if i in ids:
            row = {'carrier': 'face', 'holon': x['cell_id'], 'cell': x['cell'], 'agreement': x['agreement'],
                   'where': 'cells/%s/published/%s' % (x['cell'], record.actor_file(ln['actor'])),
                   'basis': 'agreement',
                   'why': ('In the face the Agreement opens on cells/%s, which both hold; writing the face is the '
                           'person\'s own act.' % x['cell'])}
            if i in x['published']:
                row['why'] = 'Already published in cells/%s under the Agreement; the push carries it.' % x['cell']
                row['already'] = True
            if x['face']['elided'].get(i):
                row['elided'] = sorted(x['face']['elided'][i])
                row['why'] += (' The Agreement opens only some fields: the copy hides %s, and keeps its id.'
                               % ', '.join(row['elided']))
            return row
        why = next((h['why'] for h in x['face']['held_back'] if h.get('id') == i), '')
        if why:
            reasons.append('cells/%s: %s' % (x['cell'], why))
    agreed = {x['cell_id'] for x in shared}
    for cid in sorted(ctx['cells'][1]):
        if _admitted_in(ctx, cid, actor) and cid not in agreed:
            reasons.append('cells/%s: no live Agreement opens a face there' % ctx['cells'][1][cid])
    return None


def _try_permitted(ln, held, actor, ctx, reasons):
    cid = _s(ln.get('holon'))
    if cid == ctx['hid'] or cid not in ctx['cells'][1] or not _admitted_in(ctx, cid, actor):
        return None
    name = _cell_name(ctx, cid)
    if held is not None and (held.get('_held_in') == cid or cid in (held.get('_also_in') or [])):
        return None     # already in that holon: pull carries it
    key = ('permits', cid)
    if key not in ctx['cache']:
        ctx['cache'][key] = permitted.grant_for(ctx['f'], cid, ctx['clock'])
    p = ctx['cache'][key]
    grant = p.get(ctx['hid']) if isinstance(p.get(ctx['hid']), dict) else p.get(_s(ln.get('for')))
    if not isinstance(grant, dict) or not grant.get('write'):
        reasons.append('cells/%s: no write permit stands for this home there' % name)
        return None
    if ln.get('audience', 'holon') not in permitted.WITHIN:
        reasons.append('cells/%s: a permitted line reaches members at most, and this one is wider' % name)
        return None
    if ln.get('type') in permitted.NEVER:
        reasons.append('cells/%s: a %s line never enters by the permitted inbox' % (name, ln.get('type')))
        return None
    rows = [x for x in agreement.agreements(ctx['f'], holon=cid, now=ctx['clock']) if x['id'] == grant.get('agreement')]
    crosses = rows[0].get('crosses') if rows else []
    if crosses and ln.get('type') not in crosses:
        reasons.append('cells/%s: the Agreement does not name %r among what crosses' % (name, ln.get('type')))
        return None
    return {'carrier': 'permitted', 'holon': cid, 'cell': name, 'agreement': grant.get('agreement'),
            'where': 'cells/%s/permitted/%s' % (name, record.actor_file(ln['actor'])), 'basis': 'permit',
            'why': 'The Agreement in cells/%s grants a write permit, and the line is written for it.' % name}


def _mail_module():
    try:
        return importlib.import_module('mail')
    except Exception:
        return None


def _domain(addr):
    return addr.rsplit('@', 1)[1].lower() if '@' in addr else ''


def _try_mail(ln, actor, info, ctx, mail_domains, reasons):
    hid = _s(ln.get('holon'))
    key = ('reach', hid)
    if key not in ctx['cache']:
        m = _mail_module()
        try:
            ctx['cache'][key] = m.reach_of(ctx['dir'], hid) if m is not None else {}
        except Exception:   # an unreadable holon gives no reach; said below
            ctx['cache'][key] = {}
    addrs, basis = list(ctx['cache'][key].get(actor) or []), 'reach (record)'
    if not addrs:
        addrs = [x[5:].strip() for x in info.get('reach') or [] if x.startswith('mail:') and '@' in x]
        basis = 'reach (directory)'
    if not addrs:
        return None
    if not _admitted_in(ctx, hid, actor):
        reasons.append('mail: a line is mailed only to an actor its holon admitted, and %s is not admitted there'
                       % actor[:64])
        return None
    doms = [d.lower() for d in _strs(mail_domains)] if mail_domains is not None else None
    if doms is not None:
        addrs = [a for a in addrs if _domain(a) in doms]
        if not addrs:
            reasons.append('mail: no address in their reach sits inside the private network')
            return None
    note = ('' if doms is not None else ' Whether the address sits inside the private network is checked at the '
                                         'Send (mail.py refuses one beyond it).')
    return {'carrier': 'mail', 'holon': hid, 'where': sorted(addrs)[0], 'basis': basis,
            'why': ('Their reach names a mail endpoint; the person\'s own Send carries the line in the mail\'s body '
                    '(mail.py send_line), shaped by mail.to_mail.' + note)}


def _draft(ln, fallback):
    m = _mail_module()
    try:
        text = m.readable(_clean(ln)) if m is not None else ''
    except Exception:
        text = ''
    if not text:
        b = ln.get('body') if isinstance(ln.get('body'), dict) else {}
        text = (_s(b.get('text')) or _s(b.get('title')) or 'A line') + '\n\nLine: %s\n' % ln.get('id')
    return {'to': fallback, 'text': text, 'sends': 'person',
            'note': 'Carried by an agent for its person; the signed line is the truth, and this text is for reading.'}


def _try_pull(ln, held, actor, info, ctx):
    hid = _s(ln.get('holon'))
    if held is None or _s(held.get('_held_in')) != hid or not _admitted_in(ctx, hid, actor):
        return None
    w = _where_held(ctx, hid)
    if w is None:
        return None
    why = ('The line sits in a holon they hold; their agent pulls it at its own beat.' if info.get('has_agent') else
           'The line sits in a holon they hold, where they read it themselves: no agent of theirs is known to pull it.')
    return {'carrier': 'pull', 'holon': hid, 'where': w + 'record/', 'basis': 'membership', 'why': why}


def _choose(ln, held, actor, info, ctx, mail_domains):
    reasons = []
    if ln['id'] not in ctx['own_ids']:
        reasons.append('face: the line is not in this home\'s own record, so no face carries it')
    row = (_try_face(ln, actor, ctx, reasons) or _try_permitted(ln, held, actor, ctx, reasons)
           or _try_mail(ln, actor, info, ctx, mail_domains, reasons))
    if row is None and info.get('fallbacks'):
        fb = info['fallbacks']
        row = {'carrier': 'fallback', 'holon': '', 'where': fb[0], 'fallbacks': list(fb), 'basis': 'directory',
               'why': 'The directory names where they can be reached without an agent; the person sends the draft '
                      'by their own hand.', 'draft': _draft(ln, fb[0])}
    if row is None:
        row = _try_pull(ln, held, actor, info, ctx)
    return row, reasons


# ---------------------------------------------------------------- the carrier's own log

def _read_log(home_dir):
    """Every entry of the carry log, never through a link; a line that does not parse is skipped."""
    p = os.path.join(home_dir, LOG) if isinstance(home_dir, str) else ''
    if not p or not os.path.isfile(p) or os.path.islink(p):
        return []
    out = []
    with open(p, 'rb') as fh:
        for raw in fh:
            if len(raw) > record.MAX_LINE:
                continue
            try:
                e = json.loads(raw.decode('utf-8', 'replace'))
            except ValueError:
                continue
            if isinstance(e, dict):
                out.append(e)
    return out


def _write_log(home_dir, entry):
    try:
        with record.open_append_nofollow(home_dir, '', LOG) as fh:
            fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + '\n')
        return ''
    except OSError as e:
        return 'the carry log was not written (%s)' % str(e)[:80]


def _hops(ln, log):
    """The hops the line arrived with: its reader's note, or the carry log's."""
    note = ln.get('_carried') if isinstance(ln.get('_carried'), dict) else {}
    h = note.get('hops') if isinstance(note.get('hops'), int) and not isinstance(note.get('hops'), bool) else 0
    for e in log:
        if e.get('line') == ln.get('id') and isinstance(e.get('hops_in'), int) and not isinstance(e['hops_in'], bool):
            h = max(h, e['hops_in'])
    return max(h, 0)


def _rate(log, whos, ln_id, wide, t, lim):
    """The day's rate for the carrying actors `whos` (with no carrier named, every carrier of this home)."""
    whos = set(whos)
    today = [e for e in log if e.get('ok') and e.get('by') in whos and e.get('carrier') in KIT_CARRIERS
             and _same_day(e.get('at'), t)]
    wide_lines = sorted({e.get('line') for e in today if e.get('wide') and isinstance(e.get('line'), str)})
    return {'by': sorted(whos), 'day': t.date().isoformat(), 'today': len(today), 'limit': lim['RATE_PER_DAY'],
            'left': max(lim['RATE_PER_DAY'] - len(today), 0), 'wide': bool(wide), 'wide_today': len(wide_lines),
            'wide_limit': lim['RATE_HOLON_PER_DAY'],
            'wide_spent': bool(wide) and ln_id not in wide_lines and len(wide_lines) >= lim['RATE_HOLON_PER_DAY']}


def _whos(ctx, ln, by):
    """Who the rate is counted for: the carrier named, else every carrier of this home and the line's actor."""
    return {_s(by)} if _s(by) else (set(ctx['own']) | {_s(ln.get('actor'))})


# ---------------------------------------------------------------- plan

def plan(line, home_dir, directory=None, now=None, by=None, mail_domains=None, limits=None):
    """For a signed line of this home's own people, the carrier that reaches each recipient.

    `line` is a line or a line id held here; `directory` a directory folder (or one already read)
    for `directory.resolve`, else the record's admissions; `by` the carrying actor (with none, every
    agent of this home is checked against the stops and the rate is counted for all of them);
    `mail_domains` the private network's mail domains, when known. Reads the home and its carry
    log; writes nothing. Deterministic for the same home and `now`."""
    ctx, why = _context(home_dir, now)
    if ctx is None:
        return {'deliveries': [], 'hops': 0, 'rate': {}, 'held': [], 'said': why}
    ln, held, why = _the_line(line, ctx)
    if ln is None:
        return {'deliveries': [], 'hops': 0, 'rate': {}, 'held': [], 'said': why}
    return _plan(ctx, ln, held, directory, by, mail_domains, limits)


def _plan(ctx, ln, held, directory, by, mail_domains, limits):
    out = {'deliveries': [], 'hops': 0, 'rate': {}, 'held': [], 'said': ''}
    why = _check_line(ln, held, ctx)
    if why:
        out['said'] = why
        return out
    lim = _limits(limits)
    log = _read_log(ctx['dir'])
    arrived = _hops(ln, log)
    out['hops'] = arrived + 1
    if arrived >= lim['MAX_HOPS']:
        out['hops'] = arrived
        out['dropped'] = True
        out['said'] = ('The line arrived already carried %d times, the most a line is carried (MAX_HOPS %d); it is '
                       'dropped here and goes no further. Pull still reaches whoever holds its holon.'
                       % (arrived, lim['MAX_HOPS']))
        return out
    recips, wide, notes, lost = _recipients(ln, ctx, directory)
    who = _s(by) or 'the carriers of this home'
    out['rate'] = _rate(log, _whos(ctx, ln, by), ln['id'], wide, ctx['t'], lim)
    if not _addresses(ln):
        out['said'] = ('The line names no one in `to`, so it reaches no one by name; pull carries it to whoever '
                       'holds its holon.')
        return out
    out['held'].extend(lost)
    left = out['rate']['left']
    for actor in sorted(recips):
        row, reasons = _choose(ln, held, actor, recips[actor], ctx, mail_domains)
        stop = _stopped(ctx, ln, held, row, actor, by)
        if stop:
            out['held'].append({'to': actor, 'why': stop, 'stopped': True})
            continue
        if row is not None and row['carrier'] in KIT_CARRIERS and not row.get('already'):
            if out['rate']['wide_spent']:
                reasons = ['the day\'s rate of holon-wide lines for %s is spent (%d of %d); it waits for tomorrow or '
                           'the person\'s own hand' % (who, out['rate']['wide_today'], out['rate']['wide_limit'])]
                row = None
            elif left <= 0:
                reasons = ['the day\'s rate for %s is spent (%d of %d); it waits for tomorrow or the person\'s own '
                           'hand' % (who, out['rate']['today'], out['rate']['limit'])]
                row = None
            else:
                left -= 1
        if row is None:
            out['held'].append({'to': actor, 'why': ('No carrier reaches them: ' + '; '.join(reasons) + '.') if reasons
                                else 'No carrier reaches them: they hold no holon this home holds, the record gives no '
                                     'reach and the directory no fallback.'})
            continue
        out['deliveries'].append(dict(row, to=actor, wide=bool(wide)))
    out['held'].sort(key=lambda h: h['to'])
    n, h = len(out['deliveries']), len(out['held'])
    by_c = {}
    for d in out['deliveries']:
        by_c[d['carrier']] = by_c.get(d['carrier'], 0) + 1
    words = ', '.join('%d by %s' % (by_c[c], c) for c in CARRIERS if c in by_c)
    out['said'] = ('%d deliver%s planned%s, %d held; %s. The sender\'s agent is responsible for reach; the Receipt '
                   'closes the loop whichever carrier brings it; pull remains the floor.'
                   % (n, 'y' if n == 1 else 'ies', ' (%s)' % words if words else '', h, '; '.join(notes) or
                      'the record was read'))
    return out


# ---------------------------------------------------------------- drop

def _cell_dir(home_dir, name):
    name = _s(name)
    if not name or '/' in name or '\\' in name or name in ('.', '..'):
        return None
    cells = os.path.join(home_dir, 'cells')
    d = os.path.join(cells, name)
    if os.path.islink(cells) or os.path.islink(d) or not os.path.isdir(d):
        return None
    return d


def drop(line, home_dir, plan_row, by=None, now=None, sign=None, key_dir=None, limits=None, directory=None,
         mail_domains=None):
    """Perform the local part of one planned delivery the kit can do, and never push.

    `by`, the carrying actor, is required. The plan is made again here from the line, and a row
    that differs from it in any field that steers the carrier is refused, so no row can forge a
    permit, a cell or a holon; a stop, the rate and the hop count are read again with it.
    `permitted`: the line's copy goes into the cell's `permitted/<actor-file>.jsonl` through
    `permitted.drop`, byte for byte. `face`: the face is written through `faces.write_face`, a
    person's act, so `by` must be the person; an agent is refused; a face that hides fields says
    which (`elided`). `pull` needs nothing done here; `mail` goes at the person's own Send;
    `fallback` is the person's own act with the draft in the plan row. Each face or permitted
    delivery tried is logged."""
    res = {'ok': False, 'said': '', 'file': None, 'carried': None, 'pushed': False}
    row = plan_row if isinstance(plan_row, dict) else {}
    carrier = _s(row.get('carrier'))
    if carrier not in CARRIERS:
        res['said'] = 'The plan row names no carrier the kit knows; nothing was done. ' + NO_PUSH
        return res
    who = _s(by)
    if not who.startswith(('person:', 'agent:')):
        res['said'] = ('A drop names its carrier (`by`, person:<handle> or agent:<handle>); without it nothing is '
                       'done, so leaving it out never escapes a stop or the rate. ') + NO_PUSH
        return res
    ctx, why = _context(home_dir, now)
    if ctx is None:
        res['said'] = why + ' ' + NO_PUSH
        return res
    ln, held, why = _the_line(line, ctx)
    if ln is None:
        res['said'] = why + ' Nothing was done. ' + NO_PUSH
        return res
    p = _plan(ctx, ln, held, directory, who, mail_domains, limits)
    to = _s(row.get('to'))
    mine = next((d for d in p['deliveries'] if d.get('to') == to), None)
    if mine is None:
        h = next((x for x in p['held'] if x.get('to') == to), None)
        res['said'] = ((h['why'] if h else (p['said'] or 'No delivery to %s is planned.' % (to or 'no one')))
                       + ' Nothing was done. ' + NO_PUSH)
        if h and h.get('stopped'):
            res['stopped'] = True
        return res
    diff = [k for k in ROW_KEYS if (row.get(k) or None) != (mine.get(k) or None)]
    if diff:
        res['said'] = ('The plan row differs from the plan made now from the line (%s); nothing was done. '
                       % ', '.join(diff)) + NO_PUSH
        return res
    if carrier == 'pull':
        res.update(ok=True, said='The line already sits where they read it; nothing is copied. ' + NO_PUSH)
        return res
    if carrier == 'mail':
        res['said'] = ('Mail goes at the person\'s own Send (mail.py send_line, to %s); nothing was sent here. '
                       % (_s(mine.get('where'))[:80] or 'their address')) + NO_PUSH
        return res
    if carrier == 'fallback':
        res['said'] = ('The fallback is the person\'s own act: the draft rides on the plan row, and the kit sends '
                       'nothing. ') + NO_PUSH
        return res
    if carrier == 'face' and not who.startswith('person:'):
        res['said'] = ('A face is written by a person, by their own hand; an agent may only propose it to its '
                       'person. Nothing was written. ') + NO_PUSH
        return res
    d = _cell_dir(ctx['dir'], mine.get('cell'))
    if d is None:
        res['said'] = 'The plan names no joined cell here (or one reached by a link); nothing was written. ' + NO_PUSH
        return res
    arrived = p['hops'] - 1
    entry = {'at': ctx['clock'], 'line': ln['id'], 'to': to, 'holon': _s(mine.get('holon')),
             'cell': _s(mine.get('cell')), 'carrier': carrier, 'by': who, 'hops_in': arrived, 'hops': arrived + 1,
             'wide': bool(mine.get('wide')), 'from': _s((held or {}).get('_held_in')) or _s(ln.get('holon'))}
    if carrier == 'permitted':
        got = permitted.drop(d, _clean(ln))
        res['file'] = got.get('file')
        res['ok'] = bool(got.get('ok'))
        res['said'] = (_s(got.get('said'))[:1].upper() + _s(got.get('said'))[1:] + '. ') + NO_PUSH
    else:   # face
        got = faces.write_face(ctx['dir'], mine.get('agreement'), who, sign=sign, key_dir=key_dir)
        done = ln['id'] in (got.get('published') or []) or ln['id'] in (got.get('already') or [])
        res['ok'] = bool(got.get('ok')) and done
        res['file'] = os.path.join(d, 'published', record.actor_file(ln['actor'])) if res['ok'] else None
        res['elided'] = sorted((got.get('elided') or {}).get(ln['id']) or mine.get('elided') or [])
        res['said'] = ((_s(got.get('said')) if got.get('ok') and done else
                        (_s(got.get('said')) or 'The face does not hold this line.') + ' This line was not carried.')
                       + ' The face carries every line due in it, this one among them.'
                       + (' Its copy hides %s and keeps its id.' % ', '.join(res['elided']) if res['elided'] else '')
                       + ' ' + NO_PUSH)
    if res['ok']:
        res['carried'] = {'hops': arrived + 1, 'by': who, 'at': ctx['clock']}
    entry.update(ok=res['ok'], said=res['said'][:160])
    w = _write_log(ctx['dir'], entry)
    if w:
        res['said'] += ' (%s)' % w
    return res


# ---------------------------------------------------------------- the loop guard

def may_reply(line, voice, thread=None):
    """Whether an answer in `voice` may go to `line` without its person (a loop guard).

    `voice` is the voice of the answer: a person's (`person`, `human-words`) may always answer;
    any other (`agent`, `agent-drafted`, `under-mandate`, or nothing said) is an agent's. An agent
    never answers a line whose own voice is `agent` or `agent-drafted` without its person; it may
    answer a person's words or a line under a mandate only while the thread (`thread`, its lines)
    holds fewer than MAX_ROUNDS agent-voiced lines, this one counted; then it goes to the persons.
    `human-words` is believed only on a person's own line. Pure."""
    if not isinstance(line, dict):
        return False, 'There is no line to answer.'
    if _s(voice) in ('person', 'human-words'):
        return True, 'A person answers in their own words; the guard holds only an agent.'
    theirs, how = _voice(line)
    if theirs in GUARDED_VOICES:
        return False, ('The line\'s voice is %s (%s): an agent never answers an agent\'s words without its person, '
                       'so no automatic reply loops between agents. Bring it to the person.' % (theirs, how))
    seen, rounds = set(), 0
    for l in [x for x in (thread if isinstance(thread, (list, tuple)) else []) if isinstance(x, dict)] + [line]:
        i = l.get('id') if isinstance(l.get('id'), str) else None
        if i is not None and i in seen:
            continue
        if i is not None:
            seen.add(i)
        if _voice(l)[0] != 'human-words':
            rounds += 1
    if rounds >= MAX_ROUNDS:
        return False, ('The thread already holds %d agent-voiced lines (MAX_ROUNDS %d); it goes to the persons now.'
                       % (rounds, MAX_ROUNDS))
    return True, ('The line\'s voice is %s (%s); an agent may answer within its delegation (%d of %d agent-voiced '
                  'lines in the thread).' % (theirs, how, rounds, MAX_ROUNDS))


# ---------------------------------------------------------------- status

def status(home_dir, now=None):
    """The day's carrying, and what was carried with no Receipt yet, from the carry log and the record."""
    out = {'today': {'carried': 0, 'by_carrier': {}, 'held': 0}, 'open': [], 'said': ''}
    if not isinstance(home_dir, str) or not home_dir or os.path.islink(home_dir) or not os.path.isdir(home_dir):
        out['said'] = 'No home folder at %r.' % (home_dir,)
        return out
    t, _clock = _moment(now)
    log = _read_log(home_dir)
    for e in log:
        if not _same_day(e.get('at'), t):
            continue
        if e.get('ok'):
            out['today']['carried'] += 1
            c = _s(e.get('carrier'))
            out['today']['by_carrier'][c] = out['today']['by_carrier'].get(c, 0) + 1
        else:
            out['today']['held'] += 1
    got = set()
    lines = record.read_all(home_dir)['lines'] if record.holon_info(home_dir).get('id') else []
    for l in lines:
        if l.get('type') != 'receive':
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        links = l.get('links') if isinstance(l.get('links'), dict) else {}
        for of in _strs(b.get('of')) + _strs(links.get('answers')):
            got.add((of, _s(l.get('actor'))))
            got.add((of, _s(l.get('for'))))
    seen = set()
    for e in log:
        k = (_s(e.get('line')), _s(e.get('to')))
        if not e.get('ok') or not all(k) or k in seen or k in got:
            continue
        seen.add(k)
        out['open'].append({'line': k[0], 'to': k[1], 'carrier': _s(e.get('carrier')), 'at': _s(e.get('at'))})
    out['open'].sort(key=lambda x: (x['at'], x['line'], x['to']))
    tday = out['today']
    out['said'] = ('Today: %d carried, %d held; %d carried with no Receipt yet. Silence is never a Receipt.'
                   % (tday['carried'], tday['held'], len(out['open'])))
    return out


# ---------------------------------------------------------------- command line

def _print(obj):
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='carry.py', description='Carriers: how a signed line reaches everyone it is for.')
    sp = ap.add_subparsers(dest='cmd')
    p = sp.add_parser('plan', help='the carrier for each recipient of a line')
    p.add_argument('home')
    p.add_argument('line_id')
    p.add_argument('--directory')
    p.add_argument('--now')
    p.add_argument('--by', required=True)
    d = sp.add_parser('drop', help='perform the local part of one delivery (never pushes)')
    d.add_argument('home')
    d.add_argument('line_id')
    d.add_argument('--to', required=True)
    d.add_argument('--by', required=True)
    d.add_argument('--directory')
    d.add_argument('--now')
    s = sp.add_parser('status', help='the day\'s carrying, and what has no Receipt yet')
    s.add_argument('home')
    s.add_argument('--now')
    a = ap.parse_args(argv)
    if a.cmd == 'plan':
        _print(plan(a.line_id, a.home, directory=a.directory, now=a.now, by=a.by))
        return 0
    if a.cmd == 'drop':
        pl = plan(a.line_id, a.home, directory=a.directory, now=a.now, by=a.by)
        rows = [r for r in pl['deliveries'] if r.get('to') == _s(a.to)]
        if not rows:
            held = [h['why'] for h in pl['held'] if h.get('to') == _s(a.to)]
            _print({'ok': False, 'pushed': False, 'said': (held[0] if held else
                                                           'No delivery to %s is planned. %s' % (a.to, pl['said']))})
            return 1
        out = drop(a.line_id, a.home, rows[0], by=a.by, now=a.now, directory=a.directory)
        _print(out)
        return 0 if out['ok'] else 1
    if a.cmd == 'status':
        _print(status(a.home, now=a.now))
        return 0
    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
