#!/usr/bin/env python3
"""directory.py — the directory as plain files: people, agents, holons, memberships.

    from_record(folded, lines=(), holons=(), home=None, now=None) -> directory      (pure)
    generate(home_dir, out_dir, now=None) -> {written, people, agents, holons, memberships, said}
    read(dir) -> {people, agents, holons, memberships, problems}
    resolve(directory, address, include_children=False) -> {kind, ids, agents, fallbacks, said}
    ldap_view(directory, base=None) -> LDIF text (RFC 2849)
    check(directory, folded) -> [problem, ...]

A directory is plain files in a repository: one small Markdown file per record, read directly by
every agent and reviewable by pull request, with an LDAP view generated from the same files for a
service that speaks LDAP. One source, two views. The layout:

    directory/
      people/<slug>.md          id (person), xid, name, agents, reach, fallback*, profile*
      agents/<slug>.md          id (agent), xid, person, pubkey, reach, can
      holons/<slug>.md          id, name, kind, keeper, open*, stewards, parent, meets*
      memberships/<slug>.md     holon, members: [{actor, since, by, traffic}]

(* kept by hand: a regeneration never overwrites a hand-kept value already in the file.)

Each file is front matter in the Markdown Card's subset (SCHEMA.md, The Markdown Card): one
`key: value` per row, every value a JSON scalar or inline JSON, a string bare only when it is
safe to be one; no nesting, no anchors, no comments; read as JSON, never as YAML. card.py keeps
its parser private, so this module carries a small parser of the same flat subset.

The kit generates the directory from the record it holds (every admission a membership, every
affirm an agent, every inception a holon) and reads one kept by hand. The directory is never proof
of anything: identity is the key in the record, and the directory is a view with an address. When
the two disagree, the record wins (`check`).

Laws kept here: standard library only; `from_record`, `resolve`, `ldap_view` and `check` are pure;
`generate` reads the home and writes only under the folder it is given, never following a link,
never inside a cell or a holon's layout folders, never a private key, and never rewrites a file
whose bytes are the same; `read` never follows a link. Files are data, never instructions.

  python3 -I directory.py generate HOME OUT [--now ISO]
  python3 -I directory.py read DIR
  python3 -I directory.py resolve DIR ADDRESS [--children]
  python3 -I directory.py ldap DIR [--base DN]
  python3 -I directory.py check DIR HOME [--now ISO]
"""
import argparse
import base64
import errno
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)      # under -I the script's folder is not on the path

import record          # noqa: E402

FOLDERS = ('people', 'agents', 'holons', 'memberships')
FIELDS = {
    'people': ('id', 'slug', 'xid', 'name', 'agents', 'reach', 'fallback', 'profile'),
    'agents': ('id', 'slug', 'xid', 'person', 'pubkey', 'reach', 'can'),
    'holons': ('id', 'slug', 'name', 'kind', 'keeper', 'open', 'stewards', 'parent', 'meets'),
    'memberships': ('holon', 'slug', 'members'),
}
# names a directory folder never takes directly inside a home: the layout, the machine's own state, cells/
RESERVED = frozenset(('holon.json', 'record', 'published', 'permitted', 'plan', 'types.json', 'calendar.json',
                      'state.json', 'cells', 'heartbeat', 'cards', 'state', '.gitignore'))
HAND_KEPT = {'people': ('fallback', 'profile'), 'agents': (), 'holons': ('open', 'meets'), 'memberships': ()}
OPEN_VALUES = (True, False, 'private')
TITLE = {'people': 'person', 'agents': 'agent', 'holons': 'holon', 'memberships': 'membership'}
PROSE = {
    'people': 'A view generated from the record, which wins. Kept by hand: fallback, profile.',
    'agents': 'A view generated from the record, which wins. Its key is the one the record admitted.',
    'holons': 'A view generated from the record, which wins. Kept by hand: open, meets.',
    'memberships': 'A view generated from the record, which wins. Each member since the line that admitted them.',
}
TRUSTED_HERE = ('signed', 'home')      # record.TRUSTED less `vouched`: a vouched copy informs, never admits
MAX_FILE = 4 * record.MAX_LINE         # bytes; a longer directory file is a problem, never read
SLUG_MAX = 100                         # characters in a file name before it is cut to a digest
# Traffic, read from the person's Subscription Card for the source (subscriptions.py): the fastest
# cadence the Card names decides it. These two bounds are this module's own proposal, overridable
# by argument: a minute or less is heard now (a room's pace), a week or more is quiet.
NOW_UP_TO_SECONDS = 60
QUIET_FROM_SECONDS = 604800
DEFAULT_BASE = 'o=commons'             # the LDIF's base DN when none is given; a holon names its own
LDIF_VERSION = 1                       # RFC 2849: the only version

KEY_MARKS = ('-----BEGIN', 'PRIVATE KEY', 'b3BlbnNzaC1rZXktdjE')   # armour, and "openssh-key-v1" in base64
KEY_RUN = 64                           # characters: a longer unbroken base64 run may be a key's row
_KEY_RUN = re.compile(r'[A-Za-z0-9+/=]{%d,}' % (KEY_RUN + 1))
_REACH = re.compile(r'^[a-z][a-z0-9+.-]*:\S+$')
_SLUG_OK = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
_KEY_LINE = re.compile(r'^([A-Za-z0-9_][A-Za-z0-9_.@+-]*):(.*)$')
_HEX_ID = re.compile(r'^[0-9a-f]{64}$')
_ACTOR = re.compile(r'^(person|agent):[^\s]+$')
_BARE_FIRST_NO = set('[{\'`|>&*!%@?,-~<=.+')
_YAML_WORDS = {'yes', 'no', 'on', 'off', 'y', 'n', 'true', 'false', 'null', '~'}
_YAML_TYPED = re.compile(r'^(?:[-+]?(?:\d[\d_]*)?(?:\.[\d_]*)?(?:[eE][-+]?\d+)?|[-+]?0[xXoObB].*|'
                         r'[-+]?\.(?:inf|nan)|\d{4}-\d{1,2}-\d{1,2}.*)$', re.IGNORECASE)


# ---------------------------------------------------------------- small guards

def _s(v):
    """A string made NFC, else ''."""
    return unicodedata.normalize('NFC', v) if isinstance(v, str) else ''


def _strs(v):
    """A sorted list of distinct non-empty NFC strings from a list (anything else: [])."""
    if not isinstance(v, (list, tuple)):
        return []
    return sorted({_s(x).strip() for x in v if _s(x).strip()})


def _norm(v):
    """A value made safe for a file: strings NFC, floats refused (None), nested lists and maps kept."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, str):
        return _s(v)
    if isinstance(v, int):
        return v
    if isinstance(v, (list, tuple)):
        return [x for x in (_norm(y) for y in v) if x is not None]
    if isinstance(v, dict):
        return {_s(k): _norm(x) for k, x in v.items() if isinstance(k, str) and _norm(x) is not None}
    return None                         # a float, a set, an object: never written


def _is_actor(v, kind=None):
    s = _s(v)
    if not _ACTOR.match(s):
        return False
    return kind is None or s.startswith(kind + ':')


def _handle(actor):
    s = _s(actor)
    return s.split(':', 1)[1] if ':' in s else s


def _private(v):
    """True when a value may hold key material: never written, never read as data.

    A PEM or OpenSSH armour line (`-----BEGIN`, `PRIVATE KEY`), the OpenSSH private key's magic in
    base64 (`openssh-key-v1`), or any unbroken base64 run longer than KEY_RUN characters (a row of a
    key file is 70). An XID or a line id (64 hex) stays within the bound; a public key is checked
    apart, by its shape (`_pubkey`), and never through this test."""
    if isinstance(v, str):
        return any(m in v for m in KEY_MARKS) or bool(_KEY_RUN.search(v))
    if isinstance(v, (list, tuple)):
        return any(_private(x) for x in v)
    if isinstance(v, dict):
        return any(_private(k) or _private(x) for k, x in v.items())
    return False


def _pubkey(v):
    """An OpenSSH ed25519 public key line (`ssh-ed25519 <base64 of its 51-byte wire blob>`), else None."""
    parts = _s(v).strip().split()
    if len(parts) not in (2, 3) or parts[0] != record.KEY_TYPE or any(m in _s(v) for m in KEY_MARKS):
        return None
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (ValueError, TypeError):
        return None
    head = b'\x00\x00\x00\x0b' + record.KEY_TYPE.encode() + b'\x00\x00\x00\x20'
    if len(blob) != len(head) + 32 or not blob.startswith(head):
        return None
    return '%s %s' % (parts[0], parts[1])


def _reach_ok(v):
    """A reach entry is a `scheme:address` (mail:, hook:, phone:), never key material."""
    return isinstance(v, str) and bool(_REACH.match(v)) and not _private(v)


def _clean_value(k, v):
    """The value as it may be written, or None: a public key by its shape, anything else free of key material."""
    if k == 'pubkey':
        return _pubkey(v)
    if k == 'reach' and isinstance(v, list):
        return [x for x in v if _reach_ok(x)]
    return None if _private(v) else v


def _ts_key(line):
    t = record._parse_ts(line.get('ts')) if isinstance(line, dict) else None
    return (t.isoformat() if t else '9999', _s(line.get('id')) if isinstance(line, dict) else '')


def slug_of(text, fallback=''):
    """A file name for a record: the text when it is safe, else percent-encoded, else a digest."""
    s = _s(text).strip()
    if not s:
        s = _s(fallback).strip()
    if not s:
        return ''
    if not _SLUG_OK.match(s):
        from urllib.parse import quote
        s = quote(s, safe='-._')
        if s.startswith(('.', '-', '_')):
            s = 'x' + s
    if len(s) > SLUG_MAX:
        s = s[:SLUG_MAX - 17] + '-' + record._sha(s)[:16]
    return s


# ---------------------------------------------------------------- the file form

def _bare_ok(s):
    """True when a string may stand bare and read back as itself (the Markdown Card's rule)."""
    if not s or s != s.strip() or s[0] in _BARE_FIRST_NO:
        return False
    if s.lower() in _YAML_WORDS or (_YAML_TYPED.match(s) and any(c.isdigit() for c in s)):
        return False
    if any(c in s for c in ':#"\\') or any(ord(c) < 32 or ord(c) == 127 or c in '  \x85' for c in s):
        return False
    try:
        json.loads(s)
    except ValueError:
        return True
    return False


def _emit(v):
    if isinstance(v, str) and _bare_ok(v):
        return v
    return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(', ', ': '))


def to_markdown(folder, rec):
    """The file's text for one record: front matter in FIELDS order (then any other field, sorted), a title, a sentence."""
    rec = rec if isinstance(rec, dict) else {}
    order = list(FIELDS.get(folder, ())) + sorted(k for k in rec if k not in FIELDS.get(folder, ()))
    rows = ['---']
    for k in order:
        if k in rec and rec[k] is not None and _KEY_LINE.match(k + ':'):
            rows.append('%s: %s' % (k, _emit(rec[k])))
    rows.append('---')
    label = _s(rec.get('name')) or _s(rec.get('slug')) or _s(rec.get('id')) or _s(rec.get('holon'))
    label = ' '.join(label.split())[:120]
    rows.append('# %s · %s' % (TITLE.get(folder, 'record'), label))
    rows.append('')
    rows.append(PROSE.get(folder, 'A view generated from the record, which wins.'))
    return '\n'.join(rows) + '\n'


def _parse_value(text, where):
    s = text.strip(' ')
    if s == '':
        return '', None
    try:
        json.loads(s)
        is_json = True
    except (ValueError, RecursionError):
        is_json = False
    if is_json:
        try:
            return _norm(record.loads(s)), None   # strictly: no fraction, exponent, NaN or twice-named key
        except (record.LineError, ValueError, RecursionError) as e:
            return None, {'kind': 'bad_value', 'field': where, 'said': '%s: %s' % (where, str(e)[:120])}
    if s[0] in '[{' or any(c in s for c in '#"') or ': ' in s or s.endswith(':') \
            or any(ord(c) < 32 or ord(c) == 127 for c in s):
        return None, {'kind': 'bad_value', 'field': where,
                      'said': '%s: neither JSON nor a plain word (quote it as JSON)' % where}
    return _s(s), None


def from_markdown(text):
    """(front matter dict, problems). Flat: one key per row; a value is JSON or a safe bare word."""
    if not isinstance(text, str):
        return {}, [{'kind': 'not_text', 'said': 'a directory file is UTF-8 text'}]
    rows = text.split('\n')
    if not rows or rows[0].rstrip(' \r') != '---':
        return {}, [{'kind': 'no_front_matter', 'said': 'a directory file begins with a line of three dashes'}]
    end = next((j for j in range(1, len(rows)) if rows[j].rstrip(' \r') == '---'), None)
    if end is None:
        return {}, [{'kind': 'no_front_matter', 'said': 'the front matter is never closed by three dashes'}]
    front, problems = {}, []
    for n, raw in enumerate(rows[1:end], 2):
        raw = raw.rstrip('\r')
        if raw.strip() == '':
            continue
        if raw.startswith('#'):
            problems.append({'kind': 'comment', 'said': 'line %d: front matter holds no comments' % n})
            continue
        m = _KEY_LINE.match(raw)
        if not m or (m.group(2) and not m.group(2).startswith(' ')):
            problems.append({'kind': 'bad_front_matter', 'said': 'line %d: not a flat key: value row' % n})
            continue
        k = m.group(1)
        if k in front:
            problems.append({'kind': 'duplicate_key', 'said': 'line %d: %s appears twice' % (n, k)})
            continue
        v, p = _parse_value(m.group(2), k)
        if p:
            problems.append(p)
            continue
        front[k] = v
    return front, problems


# ---------------------------------------------------------------- the record to the directory (pure)

def _trusted(line, trust):
    return isinstance(line, dict) and trust.get(line.get('id')) in TRUSTED_HERE and line.get('reason') != 'untrusted'


def _holon_of(line):
    return line['id'] if record.is_inception(line) else _s(line.get('holon'))


def _admitting(lines, trust):
    """{(holon, actor): the earliest trusted line that admitted the actor there}: inception, join, affirm."""
    out = {}
    for l in sorted((x for x in lines if _trusted(x, trust)), key=_ts_key):
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        h, who = _holon_of(l), None
        if record.is_inception(l):
            who = _s(l.get('actor'))
        elif l.get('type') == 'join' and _is_actor(b.get('who'), 'person'):
            who = _s(b['who'])
        elif l.get('type') == 'affirm' and _is_actor(b.get('agent'), 'agent'):
            who = _s(b['agent'])
        if h and who and (h, who) not in out:
            out[(h, who)] = l
    return out


def _reach_of(lines, trust):
    """{actor: reach list}, from the latest trusted join or affirm that carries the actor's body.reach."""
    out = {}
    for l in sorted((x for x in lines if _trusted(x, trust)), key=_ts_key):
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if not isinstance(b.get('reach'), list):
            continue
        who = None
        if l.get('type') == 'affirm' and _is_actor(b.get('agent'), 'agent'):
            who = _s(b['agent'])
        elif l.get('type') == 'join':
            who = _s(b['who']) if _is_actor(b.get('who'), 'person') else (
                _s(l.get('actor')) if _is_actor(l.get('actor'), 'person') and not b.get('who') else None)
        reach = [x for x in _strs(b['reach']) if _reach_ok(x)]
        if who:
            out[who] = reach
    return out


def _names_of(lines, trust):
    """{person: name}, from the latest trusted admission join that carries body.name for them."""
    out = {}
    for l in sorted((x for x in lines if _trusted(x, trust)), key=_ts_key):
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if l.get('type') == 'join' and not record.is_inception(l) and _is_actor(b.get('who'), 'person') \
                and _s(b.get('name')).strip() and not _private(b.get('name')):
            out[_s(b['who'])] = ' '.join(_s(b['name']).split())
    return out


def _traffic(row, now_up_to=NOW_UP_TO_SECONDS, quiet_from=QUIET_FROM_SECONDS):
    """now · digest · quiet from a Subscription row the person's own Card set, else None (honest-empty)."""
    if not isinstance(row, dict) or not row.get('set_by'):
        return None
    if row.get('surface') == 'bell':
        return 'now'
    cad = [v for v in (row.get('cadence') or {}).values() if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
    if not row.get('signals') or not cad:
        return 'quiet'
    fastest = min(cad)
    if fastest <= now_up_to:
        return 'now'
    if fastest >= quiet_from:
        return 'quiet'
    return 'digest'


def _subscription_rows(lines, folded, persons, home, now):
    """{(person, source): row}, from subscriptions.py when it is beside this file; else {} and a sentence."""
    try:
        import subscriptions
    except Exception:   # noqa: BLE001 (the module absent or broken: traffic stays honest-empty)
        return {}, 'subscriptions.py could not be read here, so no traffic is said'
    out = {}
    for p in persons:
        try:
            rows = subscriptions.subscriptions(lines, p, items=folded, now=now, home=home or None)
        except Exception:   # noqa: BLE001
            continue
        for r in rows or []:
            if isinstance(r, dict) and r.get('set_by'):
                out[(p, _s(r.get('source')))] = r
    return out, ''


def _unique_slugs(pairs):
    """[(id, wanted slug)] sorted by id -> {id: slug}; a slug taken (case aside) gets the id's digest."""
    out, taken, said = {}, set(), []
    for rid, want in sorted(pairs):
        s = want or record._sha(rid)[:12]
        if s.lower() in taken:
            s2 = slug_of('%s-%s' % (s, record._sha(rid)[:8]))
            said.append('%s and another record want the file name %s; this one is %s' % (rid, s, s2))
            s = s2
        taken.add(s.lower())
        out[rid] = s
    return out, said


def from_record(folded, lines=(), holons=(), home=None, now=None,
                now_up_to=NOW_UP_TO_SECONDS, quiet_from=QUIET_FROM_SECONDS):
    """The directory the record says, as data. Pure.

    `folded` is record.fold's output (its `admitted`, `trust`, `delegations`); `lines` the lines it
    folded (for since, by, reach and names); `holons` record.read_all's holons (dir, id, name);
    `home` the reader's own holon id. Returns {people, agents, holons, memberships, said}, each
    a map by id (memberships by holon id), every value JSON-ready."""
    out = {'people': {}, 'agents': {}, 'holons': {}, 'memberships': {}, 'said': []}
    f = folded if isinstance(folded, dict) else {}
    adm = f.get('admitted') if isinstance(f.get('admitted'), dict) else {}
    trust = f.get('trust') if isinstance(f.get('trust'), dict) else {}
    lines = [l for l in (lines if isinstance(lines, (list, tuple)) else []) if isinstance(l, dict) and l.get('id')]
    by_id = {l['id']: l for l in lines}
    held = {}
    for h in holons if isinstance(holons, (list, tuple)) else []:
        if isinstance(h, dict) and isinstance(h.get('id'), str) and h['id'] and not h.get('refused'):
            held.setdefault(h['id'], h)
    if not adm:
        out['said'].append('the record admits no one here, so the directory is empty')
        return out
    admits = _admitting(lines, trust)
    reach = _reach_of(lines, trust)
    names = _names_of(lines, trust)

    rooms = {}
    for h in sorted(k for k in adm if isinstance(k, str) and _HEX_ID.match(k)):
        room = adm[h] if isinstance(adm[h], dict) else {}
        rooms[h] = {a: e for a, e in room.items()
                    if _is_actor(a) and isinstance(e, dict) and not e.get('ended')}
    persons = sorted({a for r in rooms.values() for a in r if a.startswith('person:')})
    agents = sorted({a for r in rooms.values() for a in r if a.startswith('agent:')})
    keepers = {h: next((a for a, e in r.items() if e.get('via') == 'inception'), None) for h, r in rooms.items()}
    kinds = {}
    for h in rooms:
        inc = by_id.get(h)
        b = inc.get('body') if isinstance(inc, dict) and isinstance(inc.get('body'), dict) else {}
        kinds[h] = b
    homes = {keepers[h]: h for h in sorted(rooms) if keepers.get(h) and _s(kinds[h].get('kind')) == 'person'}

    pslug, s1 = _unique_slugs([(p, slug_of(_handle(p))) for p in persons])
    aslug, s2 = _unique_slugs([(a, slug_of(_handle(a))) for a in agents])
    hslug, s3 = _unique_slugs([(h, slug_of(_s((held.get(h) or {}).get('name')) or _s(kinds[h].get('name')), h[:12]))
                               for h in rooms])
    out['said'] += s1 + s2 + s3

    def xid_for(actor):
        if actor in homes and rooms[homes[actor]].get(actor, {}).get('xid'):
            return _s(rooms[homes[actor]][actor]['xid'])
        xs = sorted({_s(r[actor].get('xid')) for r in rooms.values() if actor in r and r[actor].get('xid')})
        if len(xs) > 1:
            out['said'].append('%s holds %d XIDs across holons; the first by order is shown, and check says the rest'
                               % (actor, len(xs)))
        return xs[0] if xs else None

    # agents
    can = {}
    for d in f.get('delegations') or []:
        if isinstance(d, dict) and d.get('state') == 'live' and _is_actor(d.get('to'), 'agent'):
            can.setdefault(_s(d['to']), set()).update(_strs(d.get('scope')))
    for a in agents:
        entries = [(h, rooms[h][a]) for h in sorted(rooms) if a in rooms[h]]
        person = next((_s(e.get('person')) for _, e in entries if _is_actor(e.get('person'), 'person')), None)
        keys = sorted({k for k in (_pubkey(e.get('pubkey')) for _, e in entries) if k})
        if len(keys) > 1:
            out['said'].append('%s holds %d keys across holons; the first by order is shown' % (a, len(keys)))
        rec = {'id': a, 'slug': aslug[a], 'xid': xid_for(a), 'person': person,
               'pubkey': keys[0] if keys else None, 'reach': reach.get(a), 'can': sorted(can.get(a, ()))}
        out['agents'][a] = rec

    # people
    for p in persons:
        mine = sorted(a for a, r in out['agents'].items() if r.get('person') == p)
        rec = {'id': p, 'slug': pslug[p], 'xid': xid_for(p), 'name': names.get(p) or _handle(p),
               'agents': mine, 'reach': reach.get(p), 'fallback': None, 'profile': None}
        out['people'][p] = rec

    # holons and memberships
    # a cell is named by the url it was cloned from (the joining holon's own `join` of it, whose clone
    # lies at cells/<cell> there) or by its inception id; never by its name, which two cells may share
    dirs = {}
    for h, info in held.items():
        i = _ino(_s(info.get('dir'))) if _s(info.get('dir')) else None
        if i is not None:
            dirs[i] = h
    by_url = {}
    for l in sorted((x for x in lines if _trusted(x, trust) and x.get('type') == 'join'
                     and not record.is_inception(x)), key=_ts_key):
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        c, u, w = _s(b.get('cell')), _s(b.get('url')), held.get(_s(l.get('holon')))
        if c and u and w and _s(w.get('dir')) and _SLUG_OK.match(c):
            got = dirs.get(_ino(os.path.join(_s(w['dir']), 'cells', c)))
            if got:
                by_url.setdefault(u, got)
    for h in rooms:
        kind = _s(kinds[h].get('kind')) or None
        admitters = set()
        for (hh, who), l in admits.items():
            if hh == h and l.get('type') == 'join' and not record.is_inception(l) \
                    and _is_actor(l.get('actor'), 'person') and _is_actor(who, 'person'):
                admitters.add(_s(l['actor']))
        stewards = sorted(({keepers[h]} if keepers.get(h) else set()) | (admitters & set(rooms[h])))
        parent = None
        if kind != 'person':
            for l in sorted((x for x in lines if _trusted(x, trust) and _s(x.get('holon')) == h
                             and x.get('type') == 'join' and not record.is_inception(x)), key=_ts_key):
                b = l.get('body') if isinstance(l.get('body'), dict) else {}
                c, u = _s(b.get('cell')), _s(b.get('url'))
                if not (c or u):
                    continue
                got = by_url.get(u) if u else None
                if not got:
                    got = next((x for x in (c, u) if x in rooms), None)
                if got:
                    parent = got
                else:
                    out['said'].append('%s joined a cell this home does not hold by its url or its id; its parent '
                                       'is not said' % hslug[h])
            if parent == h:
                parent = None
        rec = {'id': h, 'slug': hslug[h],
               'name': _s((held.get(h) or {}).get('name')) or _s(kinds[h].get('name')) or None,
               'kind': kind, 'keeper': keepers.get(h), 'open': 'private' if kind == 'person' else False,
               'stewards': stewards, 'parent': parent, 'meets': None}
        out['holons'][h] = rec

    subs, why = _subscription_rows(lines, f, persons, home, now)
    if why:
        out['said'].append(why)
    for h in rooms:
        members = []
        for a in sorted(x for x in rooms[h] if x.startswith('person:')):
            l = admits.get((h, a))
            if l is None:
                l = by_id.get(_s(rooms[h][a].get('by')))
                l = l if _trusted(l, trust) else None
            m = {'actor': a}
            if isinstance(l, dict):
                if _s(l.get('ts')):
                    m['since'] = _s(l['ts'])
                if _is_actor(l.get('actor')):
                    m['by'] = _s(l['actor'])
            t = _traffic(subs.get((a, h)), now_up_to, quiet_from)
            if t:
                m['traffic'] = t
            members.append(m)
        out['memberships'][h] = {'holon': h, 'slug': hslug[h], 'members': members}
    return out


# ---------------------------------------------------------------- files, never through a link

def _open_dir(path_or_name, dir_fd=None, make=False):
    """A directory's fd, opened without following a link; None when it is a link or cannot be opened."""
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    if make:
        try:
            os.mkdir(path_or_name, 0o755, dir_fd=dir_fd) if dir_fd is not None else os.mkdir(path_or_name, 0o755)
        except FileExistsError:
            pass
        except OSError:
            return None
    try:
        return os.open(path_or_name, flags, dir_fd=dir_fd) if dir_fd is not None else os.open(path_or_name, flags)
    except OSError:
        return None


def _read_at(dfd, name):
    """(text or None, why). Never through a link; never more than MAX_FILE bytes."""
    try:
        fd = os.open(name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0), dir_fd=dfd)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return None, 'absent'
        return None, 'link' if e.errno in (errno.ELOOP, errno.EMLINK) or os.path.islink(name) else 'unreadable'
    try:
        st = os.fstat(fd)
        if not (st.st_mode & 0o170000 == 0o100000):
            return None, 'not a file'
        if st.st_size > MAX_FILE:
            return None, 'longer than %d bytes' % MAX_FILE
        with os.fdopen(fd, 'rb') as fh:
            fd = None
            data = fh.read(MAX_FILE + 1)
        return data.decode('utf-8', 'replace'), ''
    except OSError:
        return None, 'unreadable'
    finally:
        if fd is not None:
            os.close(fd)


def _is_link_at(dfd, name):
    try:
        st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
        return (st.st_mode & 0o170000) == 0o120000
    except OSError:
        return False


def _write_at(dfd, name, text):
    """'written' · 'same' · 'link' · 'failed'. The file is never reached through a link."""
    if _is_link_at(dfd, name):
        return 'link'
    old, why = _read_at(dfd, name)
    data = text.encode('utf-8')
    if old is not None and old.encode('utf-8') == data:
        return 'same'
    if why == 'link':
        return 'link'
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o644, dir_fd=dfd)
    except OSError:
        return 'link' if _is_link_at(dfd, name) else 'failed'
    with os.fdopen(fd, 'wb') as fh:
        fh.write(data)
    return 'written'


def _ino(path):
    """(st_dev, st_ino) of a path that exists (a link is not followed), else None."""
    try:
        st = os.stat(path, follow_symlinks=False)
    except (OSError, ValueError, TypeError):
        return None
    return (st.st_dev, st.st_ino)


def _chain(path):
    """The (st_dev, st_ino) of the nearest existing folder at or above `path`, and of every folder above it.

    Compared by inode, never by the typed name, so a path whose case differs on a volume that
    ignores case still names the same folder."""
    out, p = [], os.path.abspath(path)
    while True:
        i = _ino(p)
        if i is not None:
            out.append(i)
        up = os.path.dirname(p)
        if up == p:
            return out
        p = up


def _linked_component(path):
    """The first existing component of `path` that is a link, else ''.

    A link the system owns (uid 0, such as /tmp or /var on macOS) is the machine's own layout,
    not a path a holon's files can plant, and is passed."""
    p = os.path.abspath(path)
    parts = []
    while True:
        parts.append(p)
        up = os.path.dirname(p)
        if up == p:
            break
        p = up
    for q in reversed(parts):
        try:
            st = os.lstat(q)
        except OSError:
            continue
        if (st.st_mode & 0o170000) == 0o120000 and st.st_uid != 0:
            return q
    return ''


def _forbidden(home_dir, out_dir):
    """A sentence when the folder may not hold the directory, else ''.

    The directory stands beside a home: its folder's parent is the home's own folder (under a name
    that is none of the holon's layout or the machine's own state, and not hidden), or a folder
    outside every holon held. Never the home itself, never inside a cell, a layout folder,
    `.carried/`, `.talk/` or `heartbeat/`, and never through a link."""
    link = _linked_component(out_dir)
    if link:
        return 'a component of that path is a link (%s); it is never followed' % os.path.basename(link)
    held = {_ino(d) for d in record.hold(home_dir)} - {None}
    home = _ino(home_dir)
    out = os.path.abspath(out_dir)
    parent = os.path.dirname(out)
    if home is not None and _ino(parent) == home:
        name = os.path.basename(out).casefold()
        if name.startswith('.') or name in RESERVED:
            return 'the directory is never written into the home\'s own %s' % os.path.basename(out)
        return ''
    if any(i in held for i in _chain(out)):
        return ('the directory is never written inside a holon (the home itself, a cell, or a folder within '
                'them); give a folder beside the home, or a direct folder of the home')
    return ''


def _fold_home(home_dir, now=None):
    """(fold, lines, holons, home id) for a home and every cell it holds; the signature cache is used."""
    r = record.read_all(home_dir)
    p = os.path.join(home_dir, 'types.json')
    types = record.load_types(p if os.path.isfile(p) and not os.path.islink(p) else None)
    with record.signature_cache(home_dir):
        f = record.fold(r['lines'], types, r['keepers'], clock=now)
    return f, r['lines'], r['holons'], _s(r.get('home'))


def generate(home_dir, out_dir, now=None, now_up_to=NOW_UP_TO_SECONDS, quiet_from=QUIET_FROM_SECONDS):
    """Write the directory the record says under `out_dir`, from the fold of every holon the home holds.

    Idempotent: a file whose bytes are the same is not rewritten, and `written` lists only what
    changed. A hand-kept value (people: fallback, profile; holons: open, meets) already in the file
    is kept. Never follows a link, never writes inside a cell or a holon's layout folders, never a
    private key. A file left from an earlier run whose record is gone is kept and said."""
    res = {'written': [], 'people': 0, 'agents': 0, 'holons': 0, 'memberships': 0, 'said': []}
    if not isinstance(home_dir, str) or not home_dir or not os.path.isdir(home_dir) or os.path.islink(home_dir):
        res['said'].append('no home folder to read (a link is never followed)')
        return res
    if not isinstance(out_dir, str) or not out_dir:
        res['said'].append('no folder to write the directory into')
        return res
    if os.path.islink(out_dir):
        res['said'].append('the directory folder is a link; it is never followed, and nothing was written')
        return res
    why = _forbidden(home_dir, out_dir)
    if why:
        res['said'].append(why + '; nothing was written')
        return res
    now = _s(now) or None
    f, lines, holons, home = _fold_home(home_dir, now)
    d = from_record(f, lines, holons, home, now, now_up_to, quiet_from)
    res['said'] += d['said']
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_dir)), exist_ok=True)
    except OSError:
        pass
    root = _open_dir(out_dir, make=True)
    if root is None:
        res['said'].append('the directory folder could not be opened without following a link; nothing was written')
        return res
    try:
        for folder in FOLDERS:
            recs = d[folder]
            sub = None if _is_link_at(root, folder) else _open_dir(folder, root, make=True)
            if sub is None:
                res['said'].append('%s/ is a link or cannot be opened; it is never followed, and none of its files '
                                   'were written' % folder)
                continue
            try:
                made = set()
                for rid in sorted(recs):
                    rec = dict(recs[rid])
                    name = rec['slug'] + '.md'
                    made.add(name)
                    old, why_old = _read_at(sub, name)
                    if why_old == 'link' or _is_link_at(sub, name):
                        res['said'].append('%s/%s is a link; it is never followed, and it was not written'
                                           % (folder, name))
                        continue
                    if old is None and why_old != 'absent':
                        res['said'].append('%s/%s could not be read (%s); it is left as it is, never overwritten'
                                           % (folder, name, why_old))
                        res[folder] += 1
                        continue
                    if old is not None:
                        front, probs = from_markdown(old)
                        if probs:
                            res['said'].append('%s/%s holds what this reader cannot read (%s); it is left as it is, '
                                               'never overwritten, so nothing kept by hand there is lost'
                                               % (folder, name, '; '.join(_s(x.get('said')) for x in probs[:3])))
                            res[folder] += 1
                            continue
                        for k in HAND_KEPT[folder]:
                            v = front.get(k)
                            if v in (None, ''):
                                continue
                            if _private(v):
                                res['said'].append('%s/%s: the hand-kept %s holds what may be key material; it '
                                                   'was not kept' % (folder, name, k))
                                continue
                            if k == 'open' and v not in OPEN_VALUES:
                                res['said'].append('%s/%s: open is true, false or private; %r was not kept'
                                                   % (folder, name, v))
                                continue
                            rec[k] = v
                    for k in list(rec):
                        v = _clean_value(k, rec[k])
                        if v is None and rec[k] is not None:
                            res['said'].append('%s/%s: the %s held what may be key material, or a key of the '
                                               'wrong shape; it was never written' % (folder, name, k))
                        rec[k] = v
                    if rec.get('holon' if folder == 'memberships' else 'id') is None:
                        res['said'].append('%s/%s: its id could not be written safely; the record was left out'
                                           % (folder, name))
                        continue
                    missing = sorted(k for k in FIELDS[folder] if rec.get(k) is None)
                    for k in missing:
                        rec.pop(k, None)
                    if missing:
                        rec['missing'] = missing
                    st = _write_at(sub, name, to_markdown(folder, rec))
                    if st == 'written':
                        res['written'].append(os.path.join(out_dir, folder, name))
                    elif st in ('link', 'failed'):
                        res['said'].append('%s/%s could not be written (%s)' % (folder, name, st))
                    res[folder] += 1
                try:
                    left = sorted(n for n in os.listdir(sub) if n.endswith('.md') and n not in made)
                except OSError:
                    left = []
                if left:
                    res['said'].append('%s/ keeps %d file(s) the record no longer says: %s'
                                       % (folder, len(left), ', '.join(left[:5])))
            finally:
                os.close(sub)
    finally:
        os.close(root)
    return res


# ---------------------------------------------------------------- reading a directory

def read(dir):
    """A directory as data, hand-kept or generated. Never follows a link.

    Returns {people, agents, holons, memberships, problems}: the first three by id, memberships by
    holon id; each record its front matter, with `slug` the file name when the file names none.
    A file that is a link, a record whose `id` is not an actor or holon id of its folder's kind,
    and an id said twice are problems; the record is left out."""
    out = {'people': {}, 'agents': {}, 'holons': {}, 'memberships': {}, 'problems': []}
    if not isinstance(dir, str) or not dir:
        out['problems'].append({'kind': 'no_directory', 'said': 'no directory folder was given'})
        return out
    if os.path.islink(dir):
        out['problems'].append({'kind': 'link', 'file': dir, 'said': 'the directory folder is a link; never followed'})
        return out
    root = _open_dir(dir)
    if root is None:
        out['problems'].append({'kind': 'no_directory', 'said': 'no directory folder at that path'})
        return out
    try:
        for folder in FOLDERS:
            if _is_link_at(root, folder):
                out['problems'].append({'kind': 'link', 'file': folder,
                                        'said': '%s/ is a link; it is never followed' % folder})
                continue
            sub = _open_dir(folder, root)
            if sub is None:
                continue
            try:
                try:
                    names = sorted(n for n in os.listdir(sub) if n.endswith('.md') and not n.startswith('.'))
                except OSError:
                    names = []
                for n in names:
                    rel = '%s/%s' % (folder, n)
                    if _is_link_at(sub, n):
                        out['problems'].append({'kind': 'link', 'file': rel, 'said': '%s is a link; never followed' % rel})
                        continue
                    text, why = _read_at(sub, n)
                    if text is None:
                        out['problems'].append({'kind': 'link' if why == 'link' else 'unreadable', 'file': rel,
                                                'said': '%s: %s' % (rel, why)})
                        continue
                    front, probs = from_markdown(text)
                    for p in probs:
                        out['problems'].append(dict(p, file=rel))
                    _take(out, folder, front, rel, n[:-3])
            finally:
                os.close(sub)
    finally:
        os.close(root)
    out['problems'].sort(key=lambda p: (_s(p.get('file')), _s(p.get('kind')), _s(p.get('said'))))
    return out


def _take(out, folder, front, rel, stem):
    key = 'holon' if folder == 'memberships' else 'id'
    rid = _s(front.get(key)).strip()
    ok = _is_actor(rid, 'person') if folder == 'people' else _is_actor(rid, 'agent') if folder == 'agents' \
        else bool(_HEX_ID.match(rid))
    if not ok:
        out['problems'].append({'kind': 'bad_id', 'file': rel,
                                'said': '%s: its %s is not %s' % (rel, key, {'people': 'a person id',
                                                                          'agents': 'an agent id'}.get(folder, 'a holon id'))})
        return
    if rid in out[folder]:
        out['problems'].append({'kind': 'duplicate_id', 'file': rel, 'said': '%s: %s is said by another file too' % (rel, rid)})
        return
    if any(_private(v) if k != 'pubkey' else (_pubkey(v) is None and _private(v)) for k, v in front.items()):
        out['problems'].append({'kind': 'private_key', 'file': rel,
                                'said': '%s holds what may be key material; it is never read' % rel})
        return
    rec = dict(front)
    if 'pubkey' in rec and rec['pubkey'] not in (None, '') and _pubkey(rec['pubkey']) is None:
        out['problems'].append({'kind': 'bad_value', 'field': 'pubkey', 'file': rel,
                                'said': '%s: pubkey is not an ssh-ed25519 public key; it is left out' % rel})
        rec.pop('pubkey')
    rec['slug'] = _s(rec.get('slug')).strip() or stem
    if folder == 'memberships':
        members = []
        for m in rec.get('members') if isinstance(rec.get('members'), list) else []:
            if isinstance(m, dict) and _is_actor(m.get('actor')):
                members.append(m)
            else:
                out['problems'].append({'kind': 'bad_member', 'file': rel,
                                        'said': '%s: a member that names no actor is left out' % rel})
        rec['members'] = sorted(members, key=lambda m: _s(m.get('actor')))
    out[folder][rid] = rec


# ---------------------------------------------------------------- resolving an address (pure)

def _as_directory(directory):
    if isinstance(directory, str):
        return read(directory)
    d = directory if isinstance(directory, dict) else {}
    return {k: ({i: r for i, r in d[k].items() if isinstance(i, str) and isinstance(r, dict)}
                if isinstance(d.get(k), dict) else {}) for k in FOLDERS}


def _current(members):
    if not isinstance(members, (list, tuple)):
        return []
    return [m for m in members if isinstance(m, dict) and _is_actor(m.get('actor')) and not m.get('left')]


def resolve(directory, address, include_children=False):
    """The actors a line to `address` would reach, by current membership. Pure on a directory dict.

    `address` is a person id, an agent id, a holon id or slug, or `everyone`. With
    include_children a holon's nested holons (those whose `parent` is it) are reached too. A person
    with no agent resolves to their `fallback`, carried by an agent of the sender; with neither,
    it is said that the line cannot reach them yet."""
    d = _as_directory(directory)
    out = {'kind': None, 'ids': [], 'agents': [], 'fallbacks': [], 'said': []}
    a = _s(address).strip()
    if not a:
        out['said'].append('no address was given')
        return out
    people, agents, holons, ms = d['people'], d['agents'], d['holons'], d['memberships']
    persons, reached_agents = set(), set()
    if a == 'everyone':
        out['kind'] = 'everyone'
        persons = set(k for k in people if _is_actor(k, 'person'))
    elif _is_actor(a, 'person'):
        out['kind'] = 'person'
        persons = {a}
        if a not in people:
            out['said'].append('%s is not in the directory' % a)
    elif _is_actor(a, 'agent'):
        out['kind'] = 'agent'
        reached_agents = {a}
        if a not in agents:
            out['said'].append('%s is not in the directory' % a)
    else:
        hid = a if a in holons or a in ms else next(
            (h for h in sorted(set(holons) | set(ms))
             if _s((holons.get(h) or ms.get(h) or {}).get('slug')) == a), None)
        if not hid:
            out['said'].append('no person, agent or holon in the directory answers to that address')
            return out
        out['kind'] = 'holon'
        seen, todo = set(), [hid]
        while todo:
            h = todo.pop(0)
            if h in seen:
                continue
            seen.add(h)
            m = ms.get(h)
            if m is None:
                out['said'].append('%s has no membership file, so none of its members are reached' % h[:12])
            for x in _current((m or {}).get('members') or []):
                (persons if x['actor'].startswith('person:') else reached_agents).add(_s(x['actor']))
            if include_children:
                todo += sorted(k for k, r in holons.items()
                               if isinstance(r, dict) and r.get('parent') in (h, (holons.get(h) or {}).get('slug'))
                               and k not in seen)
        if include_children and len(seen) > 1:
            out['said'].append('%d nested holon(s) reached as well' % (len(seen) - 1))
    for p in sorted(persons):
        rec = people.get(p) if isinstance(people.get(p), dict) else {}
        mine = set(_strs(rec.get('agents'))) | {k for k, r in agents.items()
                                               if isinstance(r, dict) and _s(r.get('person')) == p}
        mine = {x for x in mine if _is_actor(x, 'agent')}
        if mine:
            reached_agents |= mine
            continue
        fb = rec.get('fallback')
        if fb not in (None, '', []):
            out['fallbacks'].append({'person': p, 'fallback': _norm(fb)})
            out['said'].append('%s has no agent: the line reaches them by their fallback, carried by an agent of '
                               'the sender' % p)
        else:
            out['said'].append('%s has no agent and no fallback: the line cannot reach them yet' % p)
    out['ids'] = sorted(persons)
    out['agents'] = sorted(reached_agents)
    return out


# ---------------------------------------------------------------- the LDAP view (RFC 2849)

def _safe_string(v):
    """RFC 2849 SAFE-STRING: ASCII, no NUL, LF or CR, not beginning with a space, a colon or '<'."""
    if v == '':
        return True
    if any(ord(c) > 127 or c in '\x00\n\r' for c in v):
        return False
    return v[0] not in ' :<' and not v.endswith(' ')


def _attr(name, value):
    v = _s(value)
    if _safe_string(v):
        return '%s: %s' % (name, v)
    return '%s:: %s' % (name, base64.b64encode(v.encode('utf-8')).decode('ascii'))


def _rdn_value(v):
    """An attribute value escaped for a DN (RFC 4514, section 2.4)."""
    v = _s(v)
    out = []
    for i, c in enumerate(v):
        if c in ',+"\\<>;=' or (i == 0 and c in ' #') or (i == len(v) - 1 and c == ' '):
            out.append('\\' + c)
        elif ord(c) < 32:
            out.append('\\%02x' % ord(c))
        else:
            out.append(c)
    return ''.join(out)


def _person_dn(p, base):
    return 'uid=%s,ou=people,%s' % (_rdn_value(_handle(p)), base)


def _holon_dn(slug, base):
    return 'cn=%s,ou=holons,%s' % (_rdn_value(slug), base)


def ldap_view(directory, base=None):
    """LDIF text (RFC 2849) of the people and the holons as groups. Pure; deterministic.

    One entry per person (inetOrgPerson: uid, cn, sn, description, labeledURI when a profile is
    given) and per holon (groupOfNames: cn, description, owner, one member per current person
    member), sorted by id. The kit never runs an LDAP server; the parent entries (ou=people,
    ou=holons) are the importing service's. An entry whose DN another entry already holds (the
    uid or cn compared case-folded, as an LDAP server compares them) and a holon with no current
    person member are not emitted, and a comment line after the version says why."""
    d = _as_directory(directory)
    base = _s(base).strip() or DEFAULT_BASE
    head, body = ['version: %d' % LDIF_VERSION], []
    people, holons, ms = d['people'], d['holons'], d['memberships']
    dns, emitted = set(), set()
    for p in sorted(k for k in people if _is_actor(k, 'person')):
        rec = people[p]
        dn = _person_dn(p, base)
        if dn.casefold() in dns:
            head.append('# not emitted: %s, whose DN another person already holds' % _attr_text(p))
            continue
        dns.add(dn.casefold())
        emitted.add(p)
        name = ' '.join(_s(rec.get('name')).split()) or _handle(p)
        body.append('')
        body.append(_attr('dn', dn))
        for oc in ('top', 'person', 'organizationalPerson', 'inetOrgPerson'):
            body.append('objectClass: %s' % oc)
        body.append(_attr('uid', _handle(p)))
        body.append(_attr('cn', name))
        body.append(_attr('sn', name))
        body.append(_attr('description', p))
        if isinstance(rec.get('profile'), str) and rec['profile'].strip():
            body.append(_attr('labeledURI', rec['profile'].strip()))
    hids = sorted(k for k in set(holons) | set(ms) if _HEX_ID.match(k))
    for h in hids:
        rec = holons.get(h) or {}
        slug = _s(rec.get('slug')) or _s((ms.get(h) or {}).get('slug')) or h[:12]
        dn = _holon_dn(slug, base)
        members = sorted({_s(m['actor']) for m in _current((ms.get(h) or {}).get('members'))
                          if _s(m['actor']) in emitted})
        if not members:
            head.append('# not emitted: the holon %s, which holds no current person member' % h[:12])
            continue
        if dn.casefold() in dns:
            head.append('# not emitted: the holon %s, whose DN another holon already holds' % h[:12])
            continue
        dns.add(dn.casefold())
        body.append('')
        body.append(_attr('dn', dn))
        body.append('objectClass: top')
        body.append('objectClass: groupOfNames')
        body.append(_attr('cn', slug))
        body.append(_attr('description', h))
        if _is_actor(rec.get('keeper'), 'person') and rec['keeper'] in emitted:
            body.append(_attr('owner', _person_dn(rec['keeper'], base)))
        for m in members:
            body.append(_attr('member', _person_dn(m, base)))
    return '\n'.join(head + body) + '\n'


def _attr_text(v):
    """A comment's text: ASCII only, one line."""
    return ''.join(c if 32 <= ord(c) < 127 else '?' for c in _s(v))[:120]


# ---------------------------------------------------------------- the record wins (pure)

def check(directory, folded):
    """Where the directory disagrees with the record, said; the record wins. Pure on a fold.

    `folded` is record.fold's output (its `admitted`). Said: a member listed who is not admitted
    (`not_admitted`), an admitted person a held holon's membership leaves out (`not_listed`), a
    holon the record does not hold (`not_held`), a key or XID that differs (`key_differs`,
    `xid_differs`), an agent's person that differs (`person_differs`), a keeper that differs
    (`keeper_differs`), and a person or agent the record admits nowhere (`not_in_record`)."""
    d = _as_directory(directory)
    f = folded if isinstance(folded, dict) else {}
    adm = f.get('admitted') if isinstance(f.get('admitted'), dict) else {}
    rooms = {h: {a: e for a, e in (r if isinstance(r, dict) else {}).items()
                 if _is_actor(a) and isinstance(e, dict) and not e.get('ended')}
             for h, r in adm.items() if isinstance(h, str)}
    probs = []

    def say(kind, rid, said, holon=None):
        p = {'kind': kind, 'id': rid, 'said': said}
        if holon:
            p['holon'] = holon
        probs.append(p)

    for h in sorted(d['memberships']):
        m = d['memberships'][h] if isinstance(d['memberships'][h], dict) else {}
        if h not in rooms:
            say('not_held', h, 'the record held here does not hold this holon, so its members cannot be checked', h)
            continue
        listed = set()
        for x in _current(m.get('members') or []):
            a = _s(x['actor'])
            listed.add(a)
            if a not in rooms[h]:
                say('not_admitted', a, '%s is listed as a member but the record does not admit them here' % a, h)
        for a in sorted(x for x in rooms[h] if x.startswith('person:') and x not in listed):
            say('not_listed', a, '%s is admitted by the record but the directory leaves them out' % a, h)
    for h in sorted(d['holons']):
        rec = d['holons'][h] if isinstance(d['holons'][h], dict) else {}
        if h not in rooms:
            say('not_held', h, 'the record held here does not hold this holon', h)
            continue
        keeper = next((a for a, e in rooms[h].items() if e.get('via') == 'inception'), None)
        if keeper and rec.get('keeper') not in (None, '') and _s(rec.get('keeper')) != keeper:
            say('keeper_differs', h, 'the directory names another keeper than the inception does', h)
    for folder in ('people', 'agents'):
        for rid in sorted(d[folder]):
            rec = d[folder][rid] if isinstance(d[folder][rid], dict) else {}
            entries = [(h, rooms[h][rid]) for h in sorted(rooms) if rid in rooms[h]]
            if not entries:
                say('not_in_record', rid, '%s is in the directory but the record admits them nowhere held' % rid)
                continue
            x = _s(rec.get('xid')).strip().lower()
            xs = {_s(e.get('xid')).lower() for _, e in entries if e.get('xid')}
            if x and xs and x not in xs:
                say('xid_differs', rid, 'the XID the directory gives is not one the record admitted %s under' % rid)
            elif x and len(xs) > 1:
                say('xid_differs', rid, 'the record admitted %s under more than one XID' % rid)
            if folder == 'agents':
                k = _pubkey(rec.get('pubkey'))
                keys = {_pubkey(e.get('pubkey')) for _, e in entries if _pubkey(e.get('pubkey'))}
                if rec.get('pubkey') not in (None, '') and keys and k not in keys:
                    say('key_differs', rid, 'the key the directory gives for %s differs from the key the record '
                                            'admitted' % rid)
                persons = {_s(e.get('person')) for _, e in entries if e.get('person')}
                if rec.get('person') not in (None, '') and persons and _s(rec['person']) not in persons:
                    say('person_differs', rid, 'the directory names another person for %s than the record does' % rid)
    probs.sort(key=lambda p: (p['kind'], p['id'], p.get('holon', '')))
    return probs


# ---------------------------------------------------------------- command line

def _print(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='directory.py', description='The directory as plain files: a view with an address.')
    sp = ap.add_subparsers(dest='cmd')
    g = sp.add_parser('generate', help='write the directory the record says')
    g.add_argument('home')
    g.add_argument('out')
    g.add_argument('--now', default=None, help='the reader\'s clock, ISO 8601 (default: this machine\'s)')
    r = sp.add_parser('read', help='read a directory as data')
    r.add_argument('dir')
    s = sp.add_parser('resolve', help='the actors a line to an address would reach')
    s.add_argument('dir')
    s.add_argument('address')
    s.add_argument('--children', action='store_true', help='reach nested holons too')
    ld = sp.add_parser('ldap', help='the LDIF view (RFC 2849)')
    ld.add_argument('dir')
    ld.add_argument('--base', default=None, help='the base DN (default %s)' % DEFAULT_BASE)
    c = sp.add_parser('check', help='where the directory disagrees with the record')
    c.add_argument('dir')
    c.add_argument('home')
    c.add_argument('--now', default=None)
    a = ap.parse_args(argv)
    if a.cmd == 'generate':
        _print(generate(a.home, a.out, now=a.now))
    elif a.cmd == 'read':
        _print(read(a.dir))
    elif a.cmd == 'resolve':
        _print(resolve(read(a.dir), a.address, include_children=a.children))
    elif a.cmd == 'ldap':
        sys.stdout.write(ldap_view(read(a.dir), base=a.base))
    elif a.cmd == 'check':
        if not os.path.isdir(a.home) or os.path.islink(a.home):
            _print({'problems': [], 'said': 'no home folder to fold (a link is never followed)'})
            return 1
        f, _, _, _ = _fold_home(a.home, a.now)
        _print({'problems': check(read(a.dir), f)})
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
