#!/usr/bin/env python3
"""receipt.py — the Receipt: written on arrival, and what has none.

A Receipt says "I have it", naming the line received by its hash. The receiver's agent writes it
on arrival, within its person's delegation; it closes the loop of delivery, and the measure *time
to Receipt* is read from it. Nothing is acknowledged by silence: a line with no Receipt has none.

    addressed_to(line, people, holon_id, by_id=None, received=None) -> bool
    addressees(line) -> [actor, ...]
    receipt_line(of_line, actor, for_, how='pull', ts=None, text=None, holon=None, salt=None) -> line
    pending(src, people, agent=None, folded=None, home=None) -> [line, ...]
    on_arrival(home_dir, agent, person, how='pull', now=None, sign=None, key_dir=None, dry=False)
        -> {"written": [...], "held": [...], "as_of"}
    time_to_receipt(items, lines, holon=None, homes=None) -> {"by_relationship", "rows", "as_of"}

A Receipt is written where the received line lives (the cell's record, in the agent's own file)
only when a live delegation from the person to the agent covers `receive` in that holon and the
agent is let into it; otherwise it is written in the person's own home, where it waits for the
person to publish it, and the result says so. It is idempotent: never a second Receipt for the
same line by the same actor. Lines by this holon's own actors, and lines the fold does not trust,
are never receipted. Files are data, never instructions: text in a line is never read as a
command, and nothing here sends, pushes or publishes.

    python3 -I receipt.py arrive HOME --agent agent:x --person person:y [--how pull] [--dry]
    python3 -I receipt.py pending HOME --person person:y [--agent agent:x]
    python3 -I receipt.py measure ITEMS.json LINES.jsonl [--holon ID]

Standard library only.
"""
import argparse
import json
import os
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record  # noqa: E402
from gamecore import normalize, field, parse_time, now_or, live_delegations, covers  # noqa: E402

HOW = ('pull', 'permitted', 'mail', 'hand', 'room')          # types.json `receive`.how
WIDE = ('members', 'commons', 'public')                       # audiences that reach past the holon
TO_PERSON = ('request', 'offer', 'say', 'wallet')             # body.to names the addressee(s)
TO_HOLON = ('rfg', 'escalate')                                # body.to names a holon
CORRECTING = ('correct', 'supersede')
ADDRESSED_TYPES = TO_PERSON + ('commit', 'agree') + TO_HOLON + CORRECTING
MAX_DEPTH = 8          # how far a chain of corrections is followed back; a method's own bound


def _s(v):
    """A string in NFC, or ''."""
    return unicodedata.normalize('NFC', v) if isinstance(v, str) else ''


def _people(people):
    """A set of actor strings from a set, list, tuple or one string; anything else is empty."""
    if isinstance(people, str):
        return {_s(people)} if people else set()
    if isinstance(people, (set, frozenset, list, tuple)):
        return {_s(p) for p in people if isinstance(p, str) and p}
    return set()


def _ids(v):
    if isinstance(v, str):
        return [v] if v else []
    if isinstance(v, (list, tuple)):
        return [x for x in v if isinstance(x, str) and x]
    return []


def _body(line):
    return line.get('body') if isinstance(line, dict) and isinstance(line.get('body'), dict) else {}


def _links(line, rel):
    l = line.get('links') if isinstance(line, dict) and isinstance(line.get('links'), dict) else {}
    return _ids(l.get(rel))


def addressees(line):
    """The actors a line asks something of by name: body.to of a request, offer, say or wallet
    entry, and the committee of a commitment. Holons (an agree's `with`, an rfg's `to`) are not
    actors and are not listed. Pure."""
    if not isinstance(line, dict):
        return []
    typ, b = _s(line.get('type')), _body(line)
    if typ in TO_PERSON:
        out = _ids(b.get('to'))
    elif typ == 'commit':
        out = _ids(b.get('committee'))
    else:
        out = []
    seen, uniq = set(), []
    for a in (_s(x) for x in out):
        if a.startswith(('person:', 'agent:')) and a not in seen:
            seen.add(a); uniq.append(a)
    return uniq


def addressed_to(line, people, holon_id, by_id=None, received=None, _depth=0):
    """Whether a line asks something of this holon's people.

    A `request` or `offer` whose body.to is one of them; a `say` whose body.to names one; a `commit`
    whose committee is one; an `agree` whose `with` is this holon; a `wallet` entry whose `to` is one;
    an `rfg` or `escalate` whose `to` is this holon; a `correct` or `supersede` of a line one of them
    received (a line in `received`, or one in `by_id` that was itself addressed to them). Pure."""
    if not isinstance(line, dict):
        return False
    ppl, hid = _people(people), _s(holon_id)
    typ, b = _s(line.get('type')), _body(line)
    if typ in TO_PERSON or typ == 'commit':
        return bool(set(addressees(line)) & ppl)
    if typ == 'agree':
        return bool(hid) and _s(b.get('with')) == hid
    if typ in TO_HOLON:
        return bool(hid) and _s(b.get('to')) == hid
    if typ in CORRECTING:
        got = received if isinstance(received, (set, frozenset, list, tuple, dict)) else ()
        for x in _links(line, 'supersedes') + _ids(b.get('line')):
            if x in got:
                return True
            if isinstance(by_id, dict) and _depth < MAX_DEPTH and isinstance(by_id.get(x), dict) \
                    and addressed_to(by_id[x], ppl, hid, by_id, received, _depth + 1):
                return True
    return False


def receipt_line(of_line, actor, for_, how='pull', ts=None, text=None, holon=None, salt=None):
    """An unsigned `receive` line for one received line, or None when there is nothing to receipt.

    It lives in the holon the received line lives in (or `holon`, when given), answers it
    (`links.answers`), names it (`body.of`) and its author (`body.from`), says the transport
    (`body.how`, one of HOW; another word is left out, never guessed), keeps the received line's
    audience, and its reason is `delegated` for an agent (`human` for a person). Pure, except that
    with no `salt` the record gives it a fresh one and with no `ts` it is stamped now."""
    if not isinstance(of_line, dict) or not _s(of_line.get('id')):
        return None
    actor, for_ = _s(actor), _s(for_)
    if not actor.startswith(('person:', 'agent:')) or not for_.startswith('person:'):
        return None
    body = {'of': of_line['id'], 'from': _s(of_line.get('actor')) or None,
            'how': how if how in HOW else None, 'text': _s(text) or None}
    aud = of_line.get('audience') if of_line.get('audience') in record.AUDIENCES else 'holon'
    reason = 'delegated' if actor.startswith('agent:') else 'human'
    where = _s(holon) or _s(of_line.get('holon'))
    try:
        return record.make_line(actor, for_, where, 'receive', body, {'answers': [of_line['id']]},
                                audience=aud, reason=reason, ts=ts, salt=salt)
    except (ValueError, TypeError):
        return None


def _bad_ids(folded):
    out = set()
    for k in ('invalid', 'unverified', 'proposals', 'forked'):
        for x in (folded or {}).get(k) or []:
            if isinstance(x, dict) and isinstance(x.get('id'), str):
                out.add(x['id'])
    return out


def _trusted(line, trust, bad):
    return isinstance(line, dict) and trust.get(line.get('id')) in record.TRUSTED \
        and line.get('id') not in bad and line.get('reason') != 'untrusted'


def _of(line):
    """The ids a receive line names as received."""
    return _ids(_body(line).get('of')) + [x for x in _links(line, 'answers') if x not in _ids(_body(line).get('of'))]


def _pending(lines, folded, people, agent, home):
    ppl = _people(people)
    agent = _s(agent)
    if not ppl or not isinstance(lines, list):
        return []
    folded = folded if isinstance(folded, dict) else {}
    trust = folded.get('trust') if isinstance(folded.get('trust'), dict) else {}
    bad = _bad_ids(folded)
    lines = [l for l in lines if isinstance(l, dict) and isinstance(l.get('id'), str)]
    by_id = {l['id']: l for l in lines}

    def ours(a, f):
        a, f = _s(a), _s(f)
        return a in ppl or (agent and a == agent) or (a.startswith('agent:') and f in ppl)

    received = set()                          # what this holon's actors already hold a trusted Receipt of
    for l in lines:
        if _s(l.get('type')) == 'receive' and _trusted(l, trust, bad) and ours(l.get('actor'), l.get('for')):
            received.update(_of(l))
    # a receipt the fold placed on an item whose line is not among these lines still counts for the line that made it
    for coll in folded.values():
        if not isinstance(coll, list):
            continue
        for it in coll:
            if not isinstance(it, dict) or not isinstance(it.get('receipts'), list):
                continue
            for e in it['receipts']:
                if isinstance(e, dict) and e.get('id') not in by_id and _s(e.get('actor')) in ppl | {agent}:
                    received.add(it.get('id'))
    out = []
    for l in lines:
        if _s(l.get('type')) not in ADDRESSED_TYPES or not _trusted(l, trust, bad):
            continue
        if ours(l.get('actor'), l.get('for')) or l['id'] in received:
            continue
        if addressed_to(l, ppl, home, by_id, received):
            out.append(l)
    out.sort(key=lambda l: (str(l.get('ts') or ''), l['id']))
    return out


def _clean(line):
    return {k: v for k, v in line.items() if not k.startswith('_')} if isinstance(line, dict) else line


def pending(src, people, agent=None, folded=None, home=None):
    """Trusted lines addressed to this holon's people with no Receipt yet from this holon.

    `src` is a home folder (every holon it holds is read and folded), or a list of lines with
    their `folded` result (folded here when not given; `home` then names the home's id). A line
    by this holon's own actors (its people, its agent, any agent answering for one of them) is
    never pending. Never raises: an unreadable source has nothing pending."""
    try:
        if isinstance(src, str):
            if not src or not os.path.isdir(src) or os.path.islink(src.rstrip(os.sep) or src):
                return []                          # a linked home is not read
            r = record.read_all(src)
            f = folded if isinstance(folded, dict) else record.fold_hq(src)
            return _pending(r['lines'], f, people, agent, home or r.get('home'))
        if isinstance(src, list):
            f = folded if isinstance(folded, dict) else record.fold(src)
            return _pending(src, f, people, agent, home)
    except (OSError, ValueError, TypeError, KeyError):
        return []
    return []


SAID_PROBLEMS = ('bad_json', 'symlink', 'case_collision', 'holon_id_unproven', 'duplicate_holon_id', 'no_holon')


def _signs_as_admitted(agent, admitted_entry, sign, key_dir):
    """True when the line the record writes will carry the agent's signature by the key admitted for it there."""
    if sign is False or not isinstance(admitted_entry, dict):
        return False
    want = _s(admitted_entry.get('key_id')) or record.key_id(admitted_entry.get('pubkey'))
    key = record.find_key(None, agent, key_dir)
    return bool(want) and bool(key) and record.key_id(record.pubkey_of(key)) == want


def _said(home_dir, r):
    """A sentence for each thing the read could not take in: a long or broken line, a linked file or
    cell, a cell folder that holds no holon, a refused cell."""
    out = []
    for h in r.get('holons') or []:
        name = h.get('name') or _s(h.get('id'))[:12] or os.path.basename(_s(h.get('dir')))
        for p in h.get('problems') or []:
            if isinstance(p, dict) and p.get('kind') in SAID_PROBLEMS:
                where = (' (%s, line %s)' % (p.get('file'), p.get('line_no'))) if p.get('file') else ''
                out.append({'of': None, 'why': 'holon %s%s: %s; it was not read' % (name, where, p.get('said') or p['kind'])})
    cells = os.path.join(home_dir, 'cells')
    if os.path.isdir(cells) and not os.path.islink(cells):
        for n in sorted(os.listdir(cells)):
            d = os.path.join(cells, n)
            if os.path.islink(d):
                out.append({'of': None, 'why': 'cells/%s is a link; a linked cell is not read or written' % n})
            elif os.path.isdir(d) and not (os.path.isfile(os.path.join(d, 'holon.json'))
                                           or os.path.isdir(os.path.join(d, 'record'))):
                out.append({'of': None, 'why': 'cells/%s holds no holon; nothing there was read' % n})
            elif os.path.isdir(d) and not os.path.isfile(os.path.join(d, 'holon.json')):
                out.append({'of': None, 'why': 'cells/%s has no holon.json; its lines cannot be placed' % n})
    elif os.path.islink(cells):
        out.append({'of': None, 'why': 'cells/ is a link; no cell is read or written through it'})
    return out


def on_arrival(home_dir, agent, person, how='pull', now=None, sign=None, key_dir=None, dry=False):
    """Write a Receipt for every pending line addressed to the person, one per line, where it lives.

    For each holon held, folded together. A line in a cell gets its Receipt in that cell's record,
    in the agent's own file, only when a live delegation from the person to the agent covers
    `receive` there, the agent is let in there, and the line will be signed by the key admitted for
    the agent there (so the cell trusts it). Otherwise the Receipt is written in the home, where it
    waits for the person to publish it, when a live delegation covers `receive` in the home; and
    when none does, nothing is written. `held` says each of these, and names what the read could
    not take in (a long line, a linked or empty cell). Idempotent: a line already holding a Receipt
    by this agent that is trusted, or that sits in the home's own record, gets none; an unverified
    Receipt in a cell never blocks a good one. `dry` writes nothing and says what it would.
    Returns {"written": [{id, of, holon, file, signed, waits}], "held": [{of, why}], "as_of"}.
    Never raises: every failure is a sentence in `held`."""
    out = {'written': [], 'held': [], 'as_of': None}
    try:
        agent, person = _s(agent), _s(person)
        if not isinstance(home_dir, str) or not home_dir or not os.path.isdir(home_dir):
            out['held'].append({'of': None, 'why': 'there is no home folder at %r; nothing was written' % (home_dir,)})
            return out
        if os.path.islink(home_dir.rstrip(os.sep) or home_dir):
            out['held'].append({'of': None, 'why': 'the home is reached through a link; nothing is written through one'})
            return out
        if not agent.startswith('agent:') or not person.startswith('person:'):
            out['held'].append({'of': None, 'why': 'a Receipt is written by an agent:<handle> for a person:<handle>; '
                                                   'nothing was written'})
            return out
        how = how if how in HOW else 'pull'
        t = now_or(now) if now is not None and parse_time(now) is not None else None
        ts = t.isoformat(timespec='seconds') if t else None
        r = record.read_all(home_dir)
        out['held'].extend(_said(home_dir, r))
        f = record.fold_hq(home_dir, clock=ts)
        out['as_of'] = f.get('as_of') or ts
        home = r.get('home')
        dirs = {h['id']: h['dir'] for h in r.get('holons') or [] if h.get('id') and not h.get('refused')}
        home_dir_ = dirs.get(home) or home_dir
        norm = normalize(f)
        live = [d for d in live_delegations(norm, agent, t) if (field(d, 'for') or field(d, 'actor')) == person]
        admitted = f.get('admitted') if isinstance(f.get('admitted'), dict) else {}
        trust = f.get('trust') if isinstance(f.get('trust'), dict) else {}
        bad = {x.get('id') for x in f.get('invalid') or [] if isinstance(x, dict)}
        done = set()        # lines this agent holds a good Receipt of: trusted anywhere, or in the home's own record
        for l in r['lines']:
            if l.get('type') == 'receive' and l.get('actor') == agent and l.get('id') not in bad \
                    and (trust.get(l.get('id')) in record.TRUSTED or l.get('_home_record')):
                done.update(_of(l))
        home_ok = bool(home) and covers(live, 'receive', home)
        for l in _pending(r['lines'], f, {person}, agent, home):
            if l['id'] in done:
                continue
            where = _s(l.get('_held_in'))
            waits, why = None, ''
            if where == home and where in dirs:
                cell_ok = home_ok
                why = '' if home_ok else 'no live delegation from %s to %s covers receive in the home' % (person, agent)
            elif where not in dirs:
                cell_ok, why = False, 'the line lives in no holon held here'
            elif not covers(live, 'receive', where):
                cell_ok, why = False, 'no live delegation from %s to %s covers receive in holon %s' % (person, agent, where[:12])
            elif agent not in (admitted.get(where) or {}):
                cell_ok, why = False, '%s is not let into holon %s' % (agent, where[:12])
            elif not _signs_as_admitted(agent, admitted[where][agent], sign, key_dir):
                cell_ok, why = False, ('the Receipt would not be signed by the key admitted for %s in holon %s, '
                                       'so that holon would not trust it' % (agent, where[:12]))
            else:
                cell_ok = True
            if cell_ok:
                target, holon_id = dirs[where], where
            elif where != home and home_ok:
                target, holon_id, waits = home_dir_, home, 'publish'
                out['held'].append({'of': l['id'], 'why': why + '; the Receipt is written in the home, where it waits '
                                                                 'for the person to publish it'})
            else:
                more = '' if where == home else '; and none covers receive in the home'
                out['held'].append({'of': l['id'], 'why': why + more + '; no Receipt was written'})
                continue
            pre = receipt_line(l, agent, person, how, ts, holon=None, salt='')
            if pre is None:
                out['held'].append({'of': l['id'], 'why': 'no Receipt could be made of this line'})
                continue
            path = os.path.join(target, 'record', record.actor_file(agent))
            if dry:
                out['written'].append({'id': None, 'of': l['id'], 'holon': holon_id, 'file': path, 'signed': None,
                                       'waits': waits, 'dry': True})
                done.add(l['id'])
                continue
            try:
                res = record.append(target, agent, person, 'receive', pre['body'], pre['links'],
                                    audience=pre['audience'], reason=pre['reason'], ts=ts, sign=sign, key_dir=key_dir)
            except (OSError, ValueError) as e:
                out['held'].append({'of': l['id'], 'why': 'the Receipt could not be written: %s' % e})
                continue
            done.add(l['id'])
            if target != home_dir_ and not res['signed']:
                out['held'].append({'of': l['id'], 'why': 'the Receipt was written but its signing failed (%s); the '
                                                          'holon will not trust it, and the next arrival writes another'
                                                          % (res.get('said') or 'no signature')})
            out['written'].append({'id': res['line']['id'], 'of': l['id'], 'holon': res['line']['holon'],
                                   'file': res['file'], 'signed': res['signed'], 'waits': waits})
    except Exception as e:  # noqa: BLE001 — never raises; the failure is said
        out['held'].append({'of': None, 'why': 'the arrival stopped: %s: %s' % (type(e).__name__, e)})
    return out


def _homes(lines):
    """person -> their home holon id, from the inception lines of person holons among the lines."""
    out = {}
    for l in lines:
        if isinstance(l, dict) and record.is_inception(l) and _body(l).get('kind') == 'person' \
                and isinstance(l.get('actor'), str) and isinstance(l.get('id'), str):
            out.setdefault(l['actor'], l['id'])
    return out


def _moment(ts):
    """A sortable moment for a time as written: seconds since the epoch, or +inf when unknown (last)."""
    t = parse_time(ts)
    return t.timestamp() if t is not None else float('inf')


def _hours(a, b):
    ta, tb = parse_time(a), parse_time(b)
    if ta is None or tb is None:
        return None
    return round((tb - ta).total_seconds() / 3600.0, 3)


def time_to_receipt(items, lines, holon=None, homes=None):
    """Time to Receipt, by relationship: for each line that asked something of someone, or that
    someone receipted, the hours from its sending to the first Receipt on each receiving side.

    `from` is the line's holon; `to` is the receiving side: the home of the receipt's person when
    the lines hold its inception (or `homes` names it), else the receipt's actor; for an addressee
    with no Receipt yet, their home or their id, and the row counts under `none_yet`. When `items`
    is a fold result, only lines it trusts count. Relationships are keyed "from -> to" (JSON keys
    are strings), each value naming its `from` and `to`. Pure and deterministic."""
    lines = [l for l in (lines if isinstance(lines, list) else []) if isinstance(l, dict) and isinstance(l.get('id'), str)]
    f = items if isinstance(items, dict) else {}
    trust = f.get('trust') if isinstance(f.get('trust'), dict) else None
    bad = _bad_ids(f)

    def ok(l):
        if l.get('reason') == 'untrusted' or l['id'] in bad:
            return False
        return trust is None or trust.get(l['id']) in record.TRUSTED

    lines = [l for l in lines if ok(l)]
    hm = dict(_homes(lines))
    if isinstance(homes, dict):
        hm.update({_s(k): _s(v) for k, v in homes.items() if isinstance(k, str) and isinstance(v, str) and v})

    def side(actor, for_):
        a, p = _s(actor), _s(for_)
        who = a if a.startswith('person:') else p
        return hm.get(who) or a or None

    by_id = {l['id']: l for l in lines}
    first = {}                                     # (line id, to) -> (moment, receipt id, receipt ts as written)
    for l in lines:
        if _s(l.get('type')) != 'receive':
            continue
        to = side(l.get('actor'), l.get('for'))
        for x in _of(l):
            if x not in by_id or not to:
                continue
            k = (x, to)
            cand = (_moment(l.get('ts')), l['id'], l.get('ts'))
            if k not in first or cand[:2] < first[k][:2]:
                first[k] = cand
    # receipts the fold placed on items whose receive line is not among these lines
    for coll in f.values():
        if not isinstance(coll, list):
            continue
        for it in coll:
            if not isinstance(it, dict) or it.get('id') not in by_id or not isinstance(it.get('receipts'), list):
                continue
            for e in it['receipts']:
                if isinstance(e, dict) and e.get('id') not in by_id and _s(e.get('actor')):
                    k = (it['id'], side(e.get('actor'), None))
                    cand = (_moment(e.get('ts')), str(e.get('id') or ''), e.get('ts'))
                    if k[1] and (k not in first or cand[:2] < first[k][:2]):
                        first[k] = cand
    rows = []
    for l in lines:
        typ = _s(l.get('type'))
        if typ == 'receive' or record.is_inception(l):
            continue
        frm = _s(l.get('holon')) or None
        own = side(l.get('actor'), l.get('for'))
        tos = set()
        for a in addressees(l):
            tos.add(side(a, a if a.startswith('person:') else None))
        if typ == 'agree' and _s(_body(l).get('with')):
            tos.add(_s(_body(l)['with']))
        if typ in TO_HOLON and _s(_body(l).get('to')):
            tos.add(_s(_body(l)['to']))
        tos |= {to for (x, to) in first if x == l['id']}
        tos -= {None, own, frm}                    # a holon never waits on its own Receipt
        for to in sorted(tos):
            got = first.get((l['id'], to))
            rows.append({'line': l['id'], 'type': typ, 'from': frm, 'to': to, 'sent_ts': l.get('ts'),
                         'receipt': got[1] if got else None, 'receipt_ts': got[2] if got else None,
                         'hours': _hours(l.get('ts'), got[2]) if got else None})
    if holon:
        rows = [x for x in rows if holon in (x['from'], x['to'])]
    rows.sort(key=lambda x: (_moment(x['sent_ts']), x['line'], str(x['to'])))
    rel = {}
    for x in rows:
        key = '%s -> %s' % (x['from'], x['to'])
        g = rel.setdefault(key, {'from': x['from'], 'to': x['to'], 'n': 0, 'none_yet': 0, '_h': []})
        if x['receipt'] is None:
            g['none_yet'] += 1
        else:
            g['n'] += 1
            if x['hours'] is not None:
                g['_h'].append(x['hours'])
    for g in rel.values():
        hs = g.pop('_h')
        g['median_hours'] = round(statistics.median(hs), 3) if hs else None
        g['max_hours'] = round(max(hs), 3) if hs else None
    stamps = [parse_time(l.get('ts')) for l in lines]
    stamps = [s for s in stamps if s is not None]
    as_of = max(stamps).isoformat(timespec='seconds') if stamps else None
    return {'by_relationship': {k: rel[k] for k in sorted(rel)}, 'rows': rows, 'as_of': as_of,
            'basis': 'from the lines given; a line with no Receipt is counted as none yet, never as received'}


def _main(argv=None):
    ap = argparse.ArgumentParser(prog='receipt.py', description='Receipts: written on arrival, and what has none.')
    sp = ap.add_subparsers(dest='cmd')
    a = sp.add_parser('arrive', help='write a Receipt for every pending line addressed to the person')
    a.add_argument('home')
    a.add_argument('--agent', required=True)
    a.add_argument('--person', required=True)
    a.add_argument('--how', default='pull', choices=HOW)
    a.add_argument('--now', default=None)
    a.add_argument('--key-dir', default=None)
    a.add_argument('--no-sign', action='store_true')
    a.add_argument('--dry', action='store_true')
    p = sp.add_parser('pending', help='lines addressed to the person with no Receipt from this holon yet')
    p.add_argument('home')
    p.add_argument('--person', required=True)
    p.add_argument('--agent', default=None)
    m = sp.add_parser('measure', help='time to Receipt, by relationship')
    m.add_argument('items')
    m.add_argument('lines')
    m.add_argument('--holon', default=None)
    args = ap.parse_args(argv)
    if args.cmd == 'arrive':
        res = on_arrival(args.home, args.agent, args.person, args.how, args.now,
                         sign=False if args.no_sign else None, key_dir=args.key_dir, dry=args.dry)
    elif args.cmd == 'pending':
        res = {'pending': [_clean(l) for l in pending(args.home, {args.person}, args.agent)]}
    elif args.cmd == 'measure':
        try:
            with open(args.items, encoding='utf-8') as fh:
                items = json.load(fh)
            lines = [obj for _, obj, _, _ in record._read_jsonl(args.lines) if obj is not None]
        except (OSError, ValueError) as e:
            print('receipt: cannot read the input: %s' % e, file=sys.stderr)
            return 2
        res = time_to_receipt(items, lines, args.holon)
    else:
        ap.print_help()
        return 2
    print(json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(_main())
