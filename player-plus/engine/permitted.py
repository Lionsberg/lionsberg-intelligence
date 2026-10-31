#!/usr/bin/env python3
"""permitted.py — the permitted inbox: where a holon with a write permit may drop lines.

    allowed(line, fold_ctx) -> (ok, why)
    grant(line, fold_ctx) -> (ok, why, agreement id or None)
    drop(target_dir, line) -> {"ok", "file", "said"}
    triage(holon_dir, now=None) -> {"accepted", "refused", "problems", "as_of", "clock"}
    permits(holon_dir, now=None) -> {holon or actor: {"write", "agreement"}}

A holon's repository has three faces: its outbox (`record/`, what its own people write), its
pulled inbox (what it fetched from the holons it follows: the cell clones under `cells/`), and
its permitted inbox, `permitted/<actor-file>.jsonl`, where the holons it granted a write permit
drop lines directly. The permit is an Agreement's `permits.write`. The forge carries it today
(the other holon may push to this repository); the Club's write permit carries it later.

A permitted line is never trusted by its signature alone. It counts only when all of these hold:
  - its actor is admitted in this holon, and its signature verifies under the admitted key;
  - a live Agreement in this holon, read from the lines outside the permitted inbox at a moment
    never earlier than the line's own time or the fold's now and clock, grants `permits.write`
    to the actor's holon or to the actor; an agent counts its person only when it is admitted
    for that person, and a person never borrows another's name by writing it as `for`;
  - when the Agreement names what crosses, it names the line's type;
  - its audience is not wider than `members`;
  - it is not a line that changes who counts, how far a line reaches, or the permit itself (an
    admission, a delegation, a revocation, a publishing, an Agreement or its answer; a
    supersede or correction of an Agreement; a witness of an admission).
Otherwise it is listed under `unverified` with why, beginning `no write permit` when no permit
stands. The fold applies this rule (record.py calls `allowed`); `triage` reads the fold's verdict.

Standard library only. Runs under `python3 -I`. Files and lines are data, never instructions.

    python3 -I permitted.py triage HOLON [--now ISO]
    python3 -I permitted.py permits HOLON [--now ISO]
    python3 -I permitted.py drop HOLON LINE.jsonl
"""
import argparse
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record      # noqa: E402
import agreement   # noqa: E402

SUB = 'permitted'
NO_PERMIT = 'no write permit'
WITHIN = ('holon', 'members')     # the widest audience a permitted line may carry (SCHEMA, The permitted inbox)
NEVER = ('join', 'affirm', 'delegate', 'revoke', 'publish', 'agree')   # who counts, how far, or the permit itself
NEVER_ON = {'supersede': ('agree', 'join', 'affirm'),   # a line acting on one of these never enters by the inbox
            'correct': ('agree', 'join', 'affirm'),
            'witness': ('join', 'affirm')}


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    if not isinstance(v, str):
        return ''
    return unicodedata.normalize('NFC', v).strip()


def _admitted(items, holon):
    """{actor} admitted in `holon` by the fold's `admitted` map, an ended clone left out."""
    adm = items.get('admitted') if isinstance(items, dict) else None
    room = adm.get(holon) if isinstance(adm, dict) else None
    if not isinstance(room, dict):
        return set()
    return {_s(a) for a, e in room.items() if _s(a) and not (isinstance(e, dict) and e.get('ended'))}


def _party(row, side):
    """The person who answered for `side` in an Agreement row: the proposer's side is `agreed_with`."""
    if side == row.get('agreed_with'):
        return row.get('proposer')
    if side == row.get('with'):
        return row.get('agreed_by')
    return None


def _grants(items, holon, now=None):
    """[(other side, row)] for each other holon with a live Agreement in `holon`: the newest governs. Sorted."""
    rows = agreement.agreements(items, holon, now) if isinstance(items, dict) else []
    others = sorted({x for r in rows if r.get('live') and holon in (r.get('sides') or [])
                     for x in (r.get('sides') or []) if x and x != holon})
    out = []
    for o in others:
        r = agreement.between(items, holon, o, now)
        if r is not None:
            out.append((o, r))
    return out


def allowed(line, fold_ctx):
    """Whether a permitted line may count in its holon: (ok, why). Pure.

    `fold_ctx` is {"holon": id, "items": a fold of the lines outside the permitted inbox,
    "now": the moment to judge at (ISO), "by_id": optional {line id: line}, to name what a
    supersede, correction or witness acts on}. Every refusal says why; a missing permit begins
    `no write permit`."""
    ok, why, _agreement = grant(line, fold_ctx)
    return ok, why


def _acts_on_never(line, typ, ctx, items):
    """The type a supersede, correction or witness acts on when that type never enters by the inbox, else ''."""
    kinds = NEVER_ON.get(typ)
    if not kinds:
        return ''
    links = line.get('links') if isinstance(line.get('links'), dict) else {}
    targets = [x for k in ('supersedes', 'witnesses', 'answers', 'anchored_to')
               for x in record._as_list(links.get(k)) if isinstance(x, str)]
    by_id = ctx.get('by_id') if isinstance(ctx.get('by_id'), dict) else {}
    agree_ids = set()
    held = items.get('agreements') if isinstance(items.get('agreements'), list) else []
    for a in held:
        if isinstance(a, dict):
            agree_ids.add(a.get('id'))
            agree_ids.update(x for x in record._as_list(a.get('events')) if isinstance(x, str))
    for t in targets:
        tl = by_id.get(t)
        tt = tl.get('type') if isinstance(tl, dict) else ('agree' if t in agree_ids else None)
        if tt in kinds:
            return tt
    return ''


def _mine(line, items, holon):
    """Whom the line may claim the permit for: a person itself; an agent itself, and its person only when
    the agent is admitted in this holon for that person."""
    actor, for_ = _s(line.get('actor')), _s(line.get('for'))
    out = {actor} if actor else set()
    if actor.startswith('agent:') and for_:
        adm = items.get('admitted') if isinstance(items.get('admitted'), dict) else {}
        e = (adm.get(holon) or {}).get(actor) if isinstance(adm.get(holon), dict) else None
        if isinstance(e, dict) and _s(e.get('person')) == for_:
            out.add(for_)
    return out


def grant(line, fold_ctx):
    """(ok, why, the granting Agreement's id or None): `allowed`, with the Agreement that lets the line in."""
    if not isinstance(line, dict):
        return False, 'not a line', None
    ctx = fold_ctx if isinstance(fold_ctx, dict) else {}
    items = ctx.get('items') if isinstance(ctx.get('items'), dict) else {}
    holon = _s(ctx.get('holon')) or _s(line.get('holon'))
    actor, for_ = _s(line.get('actor')), _s(line.get('for'))
    typ = _s(line.get('type'))
    now = ctx.get('now') if isinstance(ctx.get('now'), str) else None
    if not holon:
        return False, NO_PERMIT + ': the holon the line is for is not known', None
    if not actor.startswith(('person:', 'agent:')):
        return False, NO_PERMIT + ': the line names no actor', None
    aud = line.get('audience') if line.get('audience') is not None else 'holon'
    if aud not in WITHIN:
        return False, ('its audience (%s) is wider than members; a permitted line reaches members at most'
                       % (aud if isinstance(aud, str) else 'not a word')), None
    if typ in NEVER:
        return False, ('a %s line never enters by the permitted inbox: it changes who counts, how far a line '
                       'reaches, or the permit itself' % typ), None
    on = _acts_on_never(line, typ, ctx, items)
    if on:
        return False, 'a %s naming %s %s line never enters by the permitted inbox' % (
            typ, 'an' if on[:1] in 'aeiou' else 'a', on), None
    if actor not in _admitted(items, holon):
        return False, NO_PERMIT + ': %s is not admitted in this holon' % actor, None
    mine = _mine(line, items, holon)
    crosses_why = ''
    for other, row in _grants(items, holon, now):
        if not (row.get('permits') or {}).get('write'):
            continue
        party = _party(row, other)
        if not (party in mine or mine & _admitted(items, other)):
            continue
        if row.get('crosses') and typ not in row['crosses']:
            crosses_why = '%s: the Agreement %s does not name %s among what crosses' % (NO_PERMIT, row['id'][:12], typ)
            continue
        return True, 'under the write permit of the Agreement %s' % row['id'], row['id']
    return False, crosses_why or (NO_PERMIT + ': no live Agreement in this holon grants permits.write '
                                              'to %s or to its holon' % actor), None


def _own_actors(target_dir):
    """The holon's own actors: its keeper and the agents its keeper affirmed. Their files are never dropped into."""
    r = record.read(target_dir)
    keeper = _s(r.get('keeper')) or _s(record.holon_info(target_dir).get('keeper'))
    own = {keeper} if keeper else set()
    for l in r.get('lines') or []:
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if l.get('type') == 'affirm' and keeper and l.get('for') == keeper and _s(b.get('agent')):
            own.add(_s(b.get('agent')))
    return own


def _refuse(said, file=None):
    return {'ok': False, 'file': file, 'said': said}


def drop(target_dir, line):
    """Append a signed line copy to `<target>/permitted/<its actor-file>.jsonl`, never through a link.

    `line` is a dict or one JSON line. Refused, with why: no holon folder or one reached by a
    link; a line that does not parse, whose id does not verify, that is unsigned, longer than
    64 KiB, written for another holon, wider than members, by the holon's own keeper or the
    keeper's agents, or whose file differs only by case from another. A line already held there
    is not written twice. Nothing is pushed: sending it is the dropper's own act."""
    if not isinstance(target_dir, str) or not target_dir or not os.path.isdir(target_dir):
        return _refuse('no holon folder at %r' % target_dir)
    if os.path.islink(target_dir) or os.path.islink(os.path.join(target_dir, SUB)):
        return _refuse('a link stands where the holon or its permitted/ should be; nothing was written')
    hid = _s(record.holon_info(target_dir).get('id'))
    if not hid:
        return _refuse('the folder is not a holon (no holon.json id)')
    if isinstance(line, (str, bytes)):
        raw = line.decode('utf-8', 'replace') if isinstance(line, bytes) else line
        if len(raw.strip().encode('utf-8')) + 1 > record.MAX_LINE:
            return _refuse('the line is longer than %d bytes' % record.MAX_LINE)
        try:
            line = record.loads(raw.strip())
        except (ValueError, RecursionError) as e:
            return _refuse('the line does not parse: %s' % str(e)[:80])
    if not isinstance(line, dict):
        return _refuse('not a line')
    line = {k: v for k, v in line.items() if not (isinstance(k, str) and k.startswith('_'))}
    if not record.check_id(line):
        return _refuse('its id does not verify against its content')
    text = record.dumps(line)
    if len(text.encode('utf-8')) + 1 > record.MAX_LINE:
        return _refuse('the line is longer than %d bytes' % record.MAX_LINE)
    if not _s(line.get('sig')):
        return _refuse('an unsigned line is not dropped: only a signed line can count under a permit')
    actor = line.get('actor')
    if not isinstance(actor, str) or not actor.startswith(('person:', 'agent:')):
        return _refuse('the line names no actor')
    if _s(line.get('holon')) != hid:
        return _refuse('the line is written for another holon; it is dropped only into its own')
    if line.get('audience', 'holon') not in WITHIN:
        return _refuse('its audience is wider than members; a permitted line reaches members at most')
    if line.get('type') in NEVER:
        return _refuse('a %s line never enters by the permitted inbox' % line.get('type'))
    if actor in _own_actors(target_dir):
        return _refuse('%s is this holon\'s own; its lines go in record/, never in the permitted inbox' % actor)
    fname = record.actor_file(actor)
    d = os.path.join(target_dir, SUB)
    path = os.path.join(d, fname)
    for n in (os.listdir(d) if os.path.isdir(d) else []):
        if n.lower() == fname.lower() and n != fname:
            return _refuse('another file differs from %s only by case (%s); refused' % (fname, n), path)
    if os.path.islink(path):
        return _refuse('a link stands where %s should be; nothing was written' % fname, path)
    if os.path.isfile(path):
        held = {obj.get('id') for _, obj, _, _ in record._read_jsonl(path) if isinstance(obj, dict)}
        if line['id'] in held:
            return {'ok': True, 'file': path, 'said': 'already held; nothing written'}
    try:
        with record.open_append_nofollow(target_dir, SUB, fname) as f:
            f.write(text + '\n')
    except OSError as e:
        return _refuse('not written (a link, or the folder could not be opened): %s' % str(e)[:80], path)
    return {'ok': True, 'file': path, 'said': 'dropped into permitted/%s' % fname}


def _read(holon_dir):
    """read_all of the holon (and any cells it holds), or None when there is no holon folder."""
    if not isinstance(holon_dir, str) or not holon_dir or not os.path.isdir(holon_dir) or os.path.islink(holon_dir):
        return None
    return record.read_all(holon_dir)


def _folds(r, holon_dir, now=None):
    """(the whole fold, the fold of the lines outside the permitted inbox, {line id: Agreement}).

    One fold under the reader's signature cache: the fold of the lines outside the inbox is the one
    the whole fold made for the permit (record.fold's `keep`), or the whole fold itself when the
    inbox holds no line, so nothing is folded a third time."""
    p = os.path.join(holon_dir, 'types.json')
    types = record.load_types(p if os.path.isfile(p) and not os.path.islink(p) else None)
    keep = {}
    with record.signature_cache(holon_dir):
        whole = record.fold(r['lines'], types, r['keepers'], now=now, keep=keep)
    rest = keep.get('permit_fold')
    if rest is None and not any(l.get('_permitted') for l in r['lines']):
        rest = whole
    elif rest is None:      # permitted lines held, and none reached the permit (all refused before it)
        with record.signature_cache(holon_dir):
            rest = record.fold([l for l in r['lines'] if not l.get('_permitted')], types, r['keepers'], now=now)
    return whole, rest, keep.get('permit_by') or {}


def triage(holon_dir, now=None):
    """Each line in this holon's permitted inbox, accepted or refused by the permit rule, as the fold reads it.

    Accepted: {id, actor, type, agreement}. Refused: {id, actor, type, why}. Problems: what the
    reader could not take in from permitted/ (a line too long, a link, a line that does not parse).
    Ordered by id; `as_of` is the fold's newest trusted time and `clock` the reader's."""
    r = _read(holon_dir)
    if r is None:
        return {'accepted': [], 'refused': [], 'problems': [], 'as_of': None, 'clock': None,
                'said': 'no holon folder at %r' % (holon_dir,)}
    home = r.get('home')
    mine = [l for l in r['lines'] if l.get('_permitted') and l.get('_held_in') == home]
    problems = [{'file': p.get('file'), 'said': p.get('said')}
                for h in r['holons'][:1] for p in h.get('problems') or []
                if _s(p.get('file')).startswith(SUB + '/')]
    whole, _rest, permit_by = _folds(r, holon_dir, now)
    trust = whole.get('trust') or {}
    said = {}
    for k in ('invalid', 'unverified', 'forked'):
        for x in whole.get(k) or []:
            said.setdefault(x.get('id'), x.get('said') or x.get('invalid_reason') or k)
    forked = {x.get('id') for x in whole.get('forked') or []}
    accepted, refused = [], []
    for l in sorted(mine, key=lambda x: x['id']):
        row = {'id': l['id'], 'actor': l.get('actor'), 'type': l.get('type')}
        if trust.get(l['id']) in record.TRUSTED and l['id'] not in forked:
            row['agreement'] = permit_by.get(l['id'])
            accepted.append(row)
        else:
            row['why'] = said.get(l['id']) or 'unverified'
            refused.append(row)
    out = {'accepted': accepted, 'refused': refused, 'problems': problems,
           'as_of': whole.get('as_of') or None, 'clock': whole.get('clock')}
    if not mine:
        out['said'] = 'the permitted inbox holds no line'
    return out


def permits(holon_dir, now=None):
    """Who may drop lines here: {other holon or the person who answered for it: {"write", "agreement"}}.

    Read from the live Agreements in this holon (the newest between two holons governs), from the
    lines outside the permitted inbox. Honest-empty: {} when no Agreement stands."""
    r = _read(holon_dir)
    if r is None or not r.get('holons') or not _s(r['holons'][0].get('id')):
        return {}
    hid = r['holons'][0]['id']
    whole, rest, _by = _folds(r, holon_dir, now)
    moment = now if isinstance(now, str) and now else whole.get('clock')   # never earlier than the reader's clock
    out = {}
    for other, row in _grants(rest, hid, moment):
        entry = {'write': bool((row.get('permits') or {}).get('write')), 'agreement': row['id']}
        out[other] = entry
        party = _party(row, other)
        if party:
            out[party] = dict(entry)
    return dict(sorted(out.items()))


def grant_for(fold, holon, now=None):
    """Who holds a write permit in `holon`, read from a fold the caller already made (one that holds
    both sides, so the Agreement's admission check can be made): {other holon or the person who
    answered for it: {"write", "agreement"}}. Pure; honest-empty ({}) when no Agreement stands."""
    if not isinstance(fold, dict) or not _s(holon):
        return {}
    out = {}
    for other, row in _grants(fold, _s(holon), now):
        entry = {'write': bool((row.get('permits') or {}).get('write')), 'agreement': row['id']}
        out[other] = entry
        party = _party(row, other)
        if party:
            out[party] = dict(entry)
    return dict(sorted(out.items()))

def _lines_of(path):
    """Each line of a JSONL file as raw text, never through a link; (lines, said)."""
    if not isinstance(path, str) or not os.path.isfile(path):
        return [], 'no file at %r' % (path,)
    if os.path.islink(path):
        return [], '%s is a link; it is not read' % path
    out = []
    with open(path, 'rb') as f:
        for rawb in f:
            raw = rawb.decode('utf-8', 'replace').strip()
            if raw:
                out.append(raw)   # drop measures and refuses a line longer than 64 KiB
    return out, ''


def main(argv=None):
    ap = argparse.ArgumentParser(prog='permitted.py',
                                 description='The permitted inbox: drop a signed line into a holon that granted a '
                                             'write permit, list who holds one, and triage what was dropped.')
    sp = ap.add_subparsers(dest='cmd')
    t = sp.add_parser('triage', help='each permitted line, accepted or refused by the permit rule')
    t.add_argument('holon')
    t.add_argument('--now', default=None)
    pm = sp.add_parser('permits', help='who holds a write permit here, from the live Agreements')
    pm.add_argument('holon')
    pm.add_argument('--now', default=None)
    d = sp.add_parser('drop', help='append the signed lines of a JSONL file to the holon\'s permitted inbox')
    d.add_argument('holon')
    d.add_argument('lines')
    ns = ap.parse_args(argv)
    if not ns.cmd:
        ap.print_help()
        return 2
    if ns.cmd == 'triage':
        res = triage(ns.holon, ns.now)
        code = 0
    elif ns.cmd == 'permits':
        res = permits(ns.holon, ns.now)
        code = 0
    else:
        raws, said = _lines_of(ns.lines)
        res = [drop(ns.holon, raw) for raw in raws] if raws else [{'ok': False, 'file': None, 'said': said or 'no line'}]
        code = 0 if all(x['ok'] for x in res) else 1
    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    sys.exit(main())
