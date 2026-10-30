#!/usr/bin/env python3
"""holon.py — make a holon, admit people and agents, join a cell, publish to it, pull from it.

A holon is a folder (usually a git repository) laid out as SCHEMA.md says: holon.json,
record/, published/, plan/, types.json, calendar.json, and a .gitignore that keeps the
derived state.json out. A person's home (their HQ) is a holon; each cell they join is a
clone under `cells/<name>/` inside it.

Keys live in the record. `init` makes the keeper's key (`~/.ssh/lionsberg-<kind>-<handle>`, or
under a key folder you name) when asked, puts its public key in the inception line and
signs it. `admit` writes a `join` that lets a person in with their public key; `affirm`
lets an agent in, by its own person. The fold counts a signed line only from a key
admitted this way.

Pulling brings others' lines in. `push` sends the home's own lines only when the person runs it;
nothing here pushes on its own, and nothing is ever forced. Sending your own lines out is a
person's act, done by their own hand (`holon.py push`).

Standard library only. Runs under `python3 -I`. Uses git and ssh-keygen when present and
says so plainly when they are not.

Usage: python3 -I holon.py --help
"""
import argparse
import json
import os
import re
from urllib.parse import unquote
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record  # noqa: E402

KINDS = ('person', 'pair', 'cell', 'room', 'body')
PUBLISHABLE = ('card', 'commit', 'request', 'offer', 'answer', 'done', 'kept', 'witness',
               'turn', 'flame', 'hand', 'claim', 'release', 'supersede', 'sight')
GITIGNORE = 'state.json\ncells/\n.sigcache\n.carried/\n.talk/\n.pulled.json\n'   # .carried/: mail the transport carries; .talk/: a room's said lines, kept only on the machine


def default_calendar():
    """The one starting calendar, in the shape schedule.py reads.

    Taken from schedule.py's own default when it offers one; otherwise the same shape here:
    every day a working day and schedule.py's default minutes per day (480)."""
    try:
        import schedule  # noqa: WPS433 (beside this file)
        fn = getattr(schedule, 'default_calendar', None)
        if callable(fn):
            cal = fn()
            if isinstance(cal, dict):
                return cal
        minutes = int(getattr(schedule, 'DEFAULT_MINUTES_PER_DAY', 480))
    except Exception:  # schedule.py absent or broken: the same shape, inline
        minutes = 480
    return {'v': 1, 'working_days': ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
            'holidays': [], 'minutes_per_day': minutes, 'actors': {}, 'gameclock': {}}


def _write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')


def init(dir, name, kind, keeper, ts=None, salt=None, sign=None, types_path=None, adopt=False,
         key_dir=None, make_key=False, holon_key=False):
    """Make a new holon in `dir` (empty or absent, or an existing home with adopt=True).

    The first line, the inception, is a `join` line by the keeper with an empty holon field
    (the holon has no id until it exists); the holon's id is that line's id. With make_key the
    keeper's key is made if missing (`<key_dir or ~/.ssh>/lionsberg-<kind>-<handle>`). When the
    keeper has a key, its public key goes in the inception and the line is signed; without
    one the holon stands at the paper floor, said plainly. sign=False writes unsigned.
    With holon_key (True, or the path of a key to use) a key for the holon itself is made too: its public key goes in the
    inception (`body.holon_pubkey`) and the private key is kept as
    `<key_dir or ~/.ssh>/lionsberg-holon-<id>`. The holon's key signs what the holon vouches
    for as a whole, such as an export's attestation.
    Returns {"dir", "holon", "inception", "key", "holon_key", "said"}."""
    if not dir or not record._str(name) or not record._str(keeper):
        raise ValueError('dir, name and keeper are required')
    if kind not in KINDS:
        raise ValueError('kind is one of %s' % ', '.join(KINDS))
    if not keeper.startswith('person:'):
        raise ValueError('a keeper is a Living Intelligence: person:<handle>')
    if os.path.exists(dir) and os.listdir(dir) and not adopt:
        raise ValueError('%s is not empty; a holon is made in an empty folder, or an existing home is adopted with adopt=True' % dir)
    if os.path.isfile(os.path.join(dir, 'holon.json')):
        raise ValueError('%s is already a holon' % dir)
    key = None
    if sign is not False:
        if make_key:
            record.make_key(keeper, key_dir)
        key = record.find_key(None, keeper, key_dir)
    for sub in ('record', 'published', 'plan'):
        os.makedirs(os.path.join(dir, sub), exist_ok=True)
    body = {'name': name, 'kind': kind, 'role': 'inception', 'contract': record.CONTRACT}
    if key:
        body['pubkey'] = record.pubkey_of(key)
    hk_tmp, hk_given = None, isinstance(holon_key, str) and os.path.isfile(holon_key)
    if holon_key and sign is not False:
        kd = key_dir or os.environ.get('LIONSBERG_KEY_DIR') or os.path.expanduser('~/.ssh')
        hk_tmp = holon_key if hk_given else record.make_key('holon:new-%s' % os.urandom(6).hex(), kd)
        if hk_tmp:
            body['holon_pubkey'] = record.pubkey_of(hk_tmp)
    line = record.make_line(keeper, keeper, '', 'join', body, ts=ts, salt=salt)
    said = ''
    if key:
        line['sig'] = record.sign_id(line['id'], key)
        if not line['sig']:
            said = 'the keeper\'s key could not sign (ed25519 keys only); the holon stands at the paper floor'
    else:
        said = 'no key for %s; the holon stands at the paper floor' % keeper
    with open(os.path.join(dir, 'record', record.actor_file(keeper)), 'a', encoding='utf-8') as f:
        f.write(record.dumps(line) + '\n')
    hk = None
    if hk_tmp:
        hk = os.path.join(key_dir or os.path.dirname(hk_tmp), record.key_name('holon:%s' % line['id']))
        move = shutil.copyfile if hk_given else os.replace
        move(hk_tmp, hk)
        os.chmod(hk, 0o600)
        if os.path.exists(hk_tmp + '.pub'):
            move(hk_tmp + '.pub', hk + '.pub')
    info = {'v': 1, 'id': line['id'], 'name': name, 'kind': kind, 'keeper': keeper,
            'created': line['ts']}
    _write_json(os.path.join(dir, 'holon.json'), info)
    src = types_path or os.path.join(HERE, 'types.json')
    if os.path.isfile(src) and not os.path.exists(os.path.join(dir, 'types.json')):
        shutil.copyfile(src, os.path.join(dir, 'types.json'))
    if not os.path.exists(os.path.join(dir, 'calendar.json')):
        _write_json(os.path.join(dir, 'calendar.json'), default_calendar())
    with open(os.path.join(dir, '.gitignore'), 'a', encoding='utf-8') as f:
        f.write(GITIGNORE)
    return {'dir': dir, 'holon': info, 'inception': line, 'key': key, 'holon_key': hk, 'said': said}


def admit(dir, admitter, who, pubkey=None, ts=None, salt=None, sign=None, key_dir=None):
    """Let a person into a holon: a `join` line by an admitted person naming them and their public key.

    The fold admits `who` only when this line is itself trusted (signed by the admitter's
    admitted key, or at the home's paper floor). Returns record.append's result."""
    if not record._str(who).startswith('person:'):
        raise ValueError('admit lets a person in; an agent is let in with affirm')
    body = {'who': who, 'role': 'member'}
    if pubkey:
        body['pubkey'] = pubkey
    return record.append(dir, admitter, admitter, 'join', body, ts=ts, salt=salt, sign=sign, key_dir=key_dir)


def affirm(dir, person, agent, pubkey=None, ts=None, salt=None, sign=None, key_dir=None, prime=None):
    """Let an agent into a holon: an `affirm` line naming the agent and its public key.

    Written by the agent's own person; or, for a clone (`agent:<prime>.<name>`), by the prime
    (`prime`), answering for the person, under the person's standing delegation that covers
    affirm and body and names the clone's handle pattern."""
    if not record._str(agent).startswith('agent:'):
        raise ValueError('affirm lets an agent in')
    body = {'agent': agent}
    if pubkey:
        body['pubkey'] = pubkey
    hid = record._str(record.holon_info(dir).get('id'))
    if hid:
        body['room'] = hid
    if prime:
        if not record._str(prime).startswith('agent:') or not agent.startswith(prime + '.'):
            raise ValueError('a clone is agent:<prime>.<name>, affirmed by its prime')
        return record.append(dir, prime, person, 'affirm', body, reason='delegated', ts=ts, salt=salt, sign=sign,
                             key_dir=key_dir)
    return record.append(dir, person, person, 'affirm', body, ts=ts, salt=salt, sign=sign, key_dir=key_dir)


def _git():
    return shutil.which('git')


def join(dir, cell_url, name, actor=None, for_=None, ts=None, salt=None, key_dir=None):
    """Join a cell: clone it under `<dir>/cells/<name>/` and note the joining in the HQ record.

    The note is a `join` line by the joining actor (default: the HQ's keeper) answering for
    themselves, or, for an agent, for its person (`for_`, default the keeper). Being let into
    the cell's record is the cell's own act (`admit` there, by an admitted person).
    Returns {"ok", "said", "path"}. Says plainly when git is absent; never pushes."""
    if not dir or not os.path.isdir(dir):
        return {'ok': False, 'said': 'no HQ folder at %r' % dir, 'path': None}
    safe = ''.join(c for c in record._str(name) if c.isalnum() or c in '-_.')
    if not safe or safe.startswith('.') or safe != record._str(name):
        return {'ok': False, 'said': 'a cell name is letters, digits, - _ or .', 'path': None}
    if not record._str(cell_url):
        return {'ok': False, 'said': 'a cell url is required', 'path': None}
    exe = _git()
    if not exe:
        return {'ok': False, 'said': 'git is not installed, so the cell cannot be joined from here; '
                                     'install git, or copy the cell folder by hand into cells/%s/' % safe,
                'path': None}
    dest = os.path.join(dir, 'cells', safe)
    if os.path.exists(dest):
        return {'ok': False, 'said': 'cells/%s already exists' % safe, 'path': dest}
    os.makedirs(os.path.join(dir, 'cells'), exist_ok=True)
    try:
        r = subprocess.run([exe, 'clone', '--quiet', '--', cell_url, dest],
                           capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return {'ok': False, 'said': 'git clone could not run: %s' % e, 'path': None}
    if r.returncode != 0:
        return {'ok': False, 'said': 'git clone failed: %s' % (r.stderr or r.stdout).strip()[:300], 'path': None}
    bad = _tree_problems(exe, dest, dir)
    if bad:
        shutil.rmtree(dest, ignore_errors=True)
        return {'ok': False, 'said': 'the cell was refused and removed: ' + '; '.join(bad[:5]), 'path': None}
    _remember(dir, safe, head=_run(exe, dest, ['rev-parse', 'HEAD']).stdout.strip())
    keeper = record._str(record.holon_info(dir).get('keeper'))
    who = actor or keeper
    if who:
        answers_for = who if who.startswith('person:') else (for_ or keeper)
        if answers_for:
            record.append(dir, who, answers_for, 'join', {'cell': safe, 'url': cell_url},
                          ts=ts, salt=salt, sign=None, key_dir=key_dir)
    return {'ok': True, 'said': 'joined; the cell is at cells/%s' % safe, 'path': dest}


def publish(dir, cell_name, line_ids, actor=None, audience='members', ts=None, salt=None, sign=None,
            key_dir=None):
    """Publish chosen lines from the HQ into a joined cell. A person's act only.

    Each chosen line is copied whole (its id and signature travel with it) into the cell's
    `published/<actor>.jsonl`, and one `publish` line by the person is appended to the cell's
    `record/<actor>.jsonl`, raising those lines' audience. Only the person's own lines cross
    (their `for` is the publisher), and only faces, milestones, commitments, requests, offers
    and signals: a card of kind activity stays home. An agent never writes into a cell's
    tree. The publish line carries the authors' public keys as admitted at home
    (`body.keys`), so a reader holding only the cell can check each copy. Nothing is pushed.
    Returns {"published": [ids], "held_back": [{id, why}], "publish_line": id or None}."""
    cell = os.path.join(dir or '', 'cells', record._str(cell_name))
    if not os.path.isdir(cell):
        raise ValueError('no joined cell at cells/%s' % cell_name)
    if audience not in record.AUDIENCES:
        raise ValueError('audience is one of %s' % ', '.join(record.AUDIENCES))
    who = record._str(actor)
    if not who.startswith('person:'):
        raise ValueError('publish is a person\'s act: give the actor as person:<handle>')
    held = {l['id']: l for l in record.read(dir)['lines']}
    already = {l['id'] for l in record.read(cell)['lines']}
    out = {'published': [], 'held_back': [], 'publish_line': None}
    chosen = []
    for i in record._as_list(line_ids):
        l = held.get(i)
        if l is None:
            out['held_back'].append({'id': i, 'why': 'not held in this HQ'})
            continue
        if l.get('for') != who:
            out['held_back'].append({'id': i, 'why': 'a person publishes only their own lines'})
            continue
        if l.get('type') not in PUBLISHABLE:
            out['held_back'].append({'id': i, 'why': 'a %r line is inner work and stays home' % l.get('type')})
            continue
        b = l.get('body') or {}
        if l.get('type') == 'card' and b.get('kind') in (None, 'activity'):
            out['held_back'].append({'id': i, 'why': 'an activity card stays home; publish its milestone'})
            continue
        chosen.append(l)
    if chosen:
        # every folder from the home down and the file itself are opened without following a link
        with record.open_append_nofollow(dir, 'cells/%s/published' % record._str(cell_name),
                                         record.actor_file(who)) as f:
            for l in chosen:
                if l['id'] not in already:
                    f.write(record.dumps({k: v for k, v in l.items() if not k.startswith('_')}) + '\n')
                out['published'].append(l['id'])
        home_keys = record.holon_keys(dir, home=True)
        keys = {a: home_keys[a] for a in sorted({l.get('actor') for l in chosen}) if a in home_keys}
        res = record.append(cell, who, who, 'publish',
                            {'lines': out['published'], 'audience': audience, 'to': record._str(cell_name),
                             'keys': keys},
                            ts=ts, salt=salt, sign=sign, key_dir=key_dir)
        out['publish_line'] = res['line']['id']
    return out


def _run(exe, d, args, env=None):
    return subprocess.run([exe, '-C', d] + args, capture_output=True, text=True, timeout=600, env=env)


ALLOWED_APPEND = re.compile(r'^(record|published)/[^/]+\.jsonl$')
ALLOWED_AT_CLONE = re.compile(r'^(holon\.json|types\.json|calendar\.json|\.gitignore|'
                              r'(record|published)/[^/]+\.jsonl|plan/[^/]+\.json)$')


def _state_path(hq):
    return os.path.join(hq, '.pulled.json')


def _remembered(hq, cell):
    try:
        with open(_state_path(hq), encoding='utf-8') as f:
            d = json.load(f)
        return d.get(cell) if isinstance(d, dict) and isinstance(d.get(cell), dict) else {}
    except (OSError, ValueError):
        return {}


def _remember(hq, cell, head=None, own=None):
    """Keep, in the home (never in a clone), the last upstream head seen and the commits the home made."""
    path = _state_path(hq)
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        d = d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        d = {}
    e = d.get(cell) if isinstance(d.get(cell), dict) else {}
    if head:
        e['head'] = head
    if own:
        e['own'] = sorted(set(e.get('own') or []) | set(own))
    d[cell] = e
    tmp = path + '.tmp'
    if os.path.islink(path) or os.path.islink(tmp):
        return
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, path)


def _home_files(hq):
    """The actor files the home's own actors write (its keeper and its agents)."""
    actors = {l.get('actor') for l in record.read(hq)['lines'] if isinstance(l.get('actor'), str)}
    keeper = record._str(record.holon_info(hq).get('keeper'))
    if keeper:
        actors.add(keeper)
    return {record.actor_file(a) for a in actors}


def _tree_problems(exe, d, hq):
    """What is wrong with a freshly cloned cell's tree: links, paths outside the layout, an unproven id."""
    out = []
    r = _run(exe, d, ['ls-tree', '-r', '-z', 'HEAD'])
    for row in [x for x in r.stdout.split('\0') if x]:
        meta, _, path = row.partition('\t')
        mode = meta.split(' ')[0]
        if mode == '120000':
            out.append('a link at %s' % path)
        elif not ALLOWED_AT_CLONE.match(path):
            out.append('a path outside the layout: %s' % path)
    if not out:
        rd = record.read(d)
        hq_id = record.read(hq)['holon']
        if not rd['inception']:
            out.append('its holon.json names an id no inception line proves')
        elif rd['holon'] == hq_id:
            out.append('it claims the home\'s own id')
    return out


def _incoming_problems(exe, d, old, new, home_files):
    """Refuse anything in old..new but plain appends to record/*.jsonl and published/*.jsonl by others.

    Paths are compared case-folded (a case-insensitive disk, as on macOS, would let `Person%3A…`
    replace `person%3A…`): two paths in the new tree that fold to one name are refused, and a
    path whose folded name is the home's own file is refused. A published file is appended
    to only by its own actor: every new line in published/<actor>.jsonl must answer for that
    actor, and the home's own published files take nothing from others."""
    out = []
    folded = {}
    for row in [x for x in _run(exe, d, ['ls-tree', '-r', '-z', '--name-only', new]).stdout.split('\0') if x]:
        k = row.casefold()
        if k in folded and folded[k] != row:
            out.append('two paths differ only by case: %s and %s' % (folded[k], row))
        folded.setdefault(k, row)
    home_folded = {h.casefold() for h in home_files}
    old_paths = {x.casefold(): x for x in _run(exe, d, ['ls-tree', '-r', '-z', '--name-only', old]).stdout.split('\0') if x}
    r = _run(exe, d, ['diff', '--raw', '-z', '--no-renames', old, new])
    parts = [x for x in r.stdout.split('\0') if x != '']
    i = 0
    while i + 1 < len(parts):
        meta, path = parts[i], parts[i + 1]
        i += 2
        f = meta.lstrip(':').split(' ')
        if len(f) < 5:
            continue
        omode, nmode, osha, nsha, status = f[0], f[1], f[2], f[3], f[4]
        if not ALLOWED_APPEND.match(path):
            out.append('a change outside record/ and published/: %s' % path)
            continue
        if nmode != '100644' or status not in ('A', 'M'):
            out.append('not a plain file appended to (%s, mode %s): %s' % (status, nmode, path))
            continue
        if os.path.basename(path).casefold() in home_folded:
            out.append('a change to the home\'s own file, which only the home writes: %s' % path)
            continue
        if status == 'A' and path.casefold() in old_paths and old_paths[path.casefold()] != path:
            out.append('a new path differs only by case from %s: %s' % (old_paths[path.casefold()], path))
            continue
        if path.startswith('published/'):
            owner = unquote(os.path.basename(path)[:-len('.jsonl')])
            a = _run(exe, d, ['cat-file', '-p', osha]).stdout if status == 'M' else ''
            b = _run(exe, d, ['cat-file', '-p', nsha]).stdout
            added = b[len(a):] if b.startswith(a) else b
            for raw in [x for x in added.splitlines() if x.strip()]:
                try:
                    ln = json.loads(raw)
                except ValueError:
                    ln = {}
                if not isinstance(ln, dict) or ln.get('for') != owner:
                    out.append('a line in %s that does not answer for its own actor' % path)
                    break
        if status == 'M':
            a = _run(exe, d, ['cat-file', '-p', osha]).stdout
            b = _run(exe, d, ['cat-file', '-p', nsha]).stdout
            if not b.startswith(a):
                out.append('an existing line was changed or removed: %s' % path)
    return out


def _sync_one(exe, d, hq=None):
    """Bring one clone up to its upstream, through the gate.

    Fetch; refuse an upstream that is not a descendant of the last head this home saw (a
    rewritten history); refuse anything incoming but plain appends to record/*.jsonl and
    published/*.jsonl by others (a link, a changed or deleted line, a change to the home's
    own files, any other path); then fast-forward, or replay the home's own commits on top.
    Only commits that touch the home's own actor files are replayed; a commit of anyone else
    sitting in the clone stops the replay. A conflict is aborted and said plainly; nothing
    is ever forced. Returns (ok, said)."""
    hq = hq or os.path.dirname(os.path.dirname(d))
    cell = os.path.basename(d)
    f = _run(exe, d, ['fetch', '--quiet'])
    if f.returncode != 0:
        return False, 'git fetch failed: %s' % (f.stderr or f.stdout).strip()[:200]
    up = _run(exe, d, ['rev-parse', '@{u}'])
    if up.returncode != 0:
        return False, 'this clone has no upstream branch to follow'
    upstream = up.stdout.strip()
    last = record._str(_remembered(hq, cell).get('head')) or \
        _run(exe, d, ['merge-base', 'HEAD', upstream]).stdout.strip()
    if last and _run(exe, d, ['merge-base', '--is-ancestor', last, upstream]).returncode != 0:
        return False, ('the cell\'s history was rewritten (the head this home last saw is gone); nothing was '
                       'brought in or replayed. Ask the cell\'s keeper, and protect the cell against force-push')
    home_files = _home_files(hq)
    if last:
        bad = _incoming_problems(exe, d, last, upstream, home_files)
        if bad:
            return False, 'refused what the cell sent: ' + '; '.join(bad[:5])
    counts = _run(exe, d, ['rev-list', '--left-right', '--count', 'HEAD...' + upstream]).stdout.split()
    ahead, behind = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
    if behind == 0:
        _remember(hq, cell, head=upstream)
        return True, 'up to date' if ahead == 0 else 'up to date; %d commit(s) of yours not yet pushed' % ahead
    if ahead == 0:
        r = _run(exe, d, ['merge', '--ff-only', '--quiet', upstream])
        if r.returncode == 0:
            _remember(hq, cell, head=upstream)
        return r.returncode == 0, (r.stderr or r.stdout).strip()[:200] or 'brought in %d commit(s)' % behind
    mine = _run(exe, d, ['rev-list', upstream + '..HEAD']).stdout.split()
    for c in mine:
        files = _run(exe, d, ['diff-tree', '--no-commit-id', '--name-only', '-r', '--root', c]).stdout.split()
        if any(not (ALLOWED_APPEND.match(x) and os.path.basename(x) in home_files) for x in files):
            return False, ('a commit in this clone that is not the home\'s own (%s) would be replayed; nothing was '
                           'replayed or forced' % c[:12])
    env = dict(os.environ)
    if not _run(exe, d, ['config', 'user.email']).stdout.strip():
        env.setdefault('GIT_COMMITTER_NAME', 'lionsberg')       # only the committer of the replayed commits
        env.setdefault('GIT_COMMITTER_EMAIL', 'lionsberg@localhost')
    r = _run(exe, d, ['rebase', '--quiet', upstream], env=env)
    if r.returncode != 0:
        _run(exe, d, ['rebase', '--abort'])
        return False, ('your own commits meet a file others changed, so they were not replayed; nothing was forced. '
                       'Look at the clone by hand: %s' % (r.stderr or r.stdout).strip()[:160])
    _remember(hq, cell, head=upstream)
    return True, 'brought in %d commit(s) and replayed your %d on top' % (behind, ahead)


def pull(dir):
    """Bring every joined cell up to date (fetch, then fast-forward or replay the home's own commits).

    A home whose push was refused recovers here by itself: its own commits are replayed on
    top of what others pushed. A conflict stops and is said plainly; nothing is forced.
    Returns [{"cell", "ok", "said"}]."""
    exe = _git()
    out = []
    for d in record.hold(dir)[1:]:
        name = os.path.basename(d)
        if not exe:
            out.append({'cell': name, 'ok': False, 'said': 'git is not installed; nothing was pulled'})
            continue
        if not os.path.isdir(os.path.join(d, '.git')):
            out.append({'cell': name, 'ok': False, 'said': 'not a git clone; nothing to pull'})
            continue
        try:
            ok, said = _sync_one(exe, d, dir)
            out.append({'cell': name, 'ok': ok, 'said': said})
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            out.append({'cell': name, 'ok': False, 'said': 'git could not run: %s' % e})
    return out


def push(dir, cell=None):
    """Send the home's own commits to each joined cell (or one named cell). A person's act, run by them.

    When a push is refused because others pushed first, the clone is brought up to date
    (see pull: the home's own commits are replayed on top) and the push is tried once more.
    Nothing is ever forced. Returns [{"cell", "ok", "said"}]."""
    exe = _git()
    out = []
    for d in record.hold(dir)[1:]:
        name = os.path.basename(d)
        if cell and name != cell:
            continue
        if not exe or not os.path.isdir(os.path.join(d, '.git')):
            out.append({'cell': name, 'ok': False, 'said': 'git is not installed or this is not a clone; nothing sent'})
            continue
        try:
            r = _run(exe, d, ['push', '--quiet', 'origin', 'HEAD'])
            if r.returncode == 0:
                _remember(dir, name, head=_run(exe, d, ['rev-parse', 'HEAD']).stdout.strip())
                out.append({'cell': name, 'ok': True, 'said': 'sent'})
                continue
            ok, said = _sync_one(exe, d, dir)
            if not ok:
                out.append({'cell': name, 'ok': False, 'said': 'the push was refused and could not recover: ' + said})
                continue
            r = _run(exe, d, ['push', '--quiet', 'origin', 'HEAD'])
            if r.returncode == 0:
                _remember(dir, name, head=_run(exe, d, ['rev-parse', 'HEAD']).stdout.strip())
            out.append({'cell': name, 'ok': r.returncode == 0,
                        'said': ('sent after bringing in others\' lines' if r.returncode == 0 else
                                 'refused twice; nothing was forced: %s' % (r.stderr or r.stdout).strip()[:160])})
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            out.append({'cell': name, 'ok': False, 'said': 'git could not run: %s' % e})
    return out


def hold(dir):
    """Every holon held: the HQ itself, then each holon under cells/."""
    return record.hold(dir)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='holon.py',
                                 description='Make a holon, admit people and agents, join a cell, publish to it, '
                                             'pull from it, list what is held. Never pushes: sending lines out '
                                             'is a person\'s act.')
    sp = ap.add_subparsers(dest='cmd')
    i = sp.add_parser('init', help='make a new holon in an empty folder, or adopt an existing home with --adopt')
    i.add_argument('dir')
    i.add_argument('--name', required=True)
    i.add_argument('--kind', required=True, choices=KINDS)
    i.add_argument('--keeper', required=True, help='person:<handle>')
    i.add_argument('--adopt', action='store_true', help='adopt an existing home folder (a Player+ HQ) as this holon')
    i.add_argument('--no-key', action='store_true', help='do not make a key; the holon stands at the paper floor')
    i.add_argument('--key-dir', default=None, help='where keys live (default: env LIONSBERG_KEY_DIR, else ~/.ssh)')
    ad = sp.add_parser('admit', help='let a person into a holon (a join line with their public key)')
    ad.add_argument('dir')
    ad.add_argument('--by', required=True, help='the admitting person, person:<handle>')
    ad.add_argument('--who', required=True, help='the person let in, person:<handle>')
    ad.add_argument('--pubkey', default=None, help='their public key, "ssh-ed25519 AAAA…"')
    ad.add_argument('--key-dir', default=None, help='where keys live (default: env LIONSBERG_KEY_DIR, else ~/.ssh)')
    af = sp.add_parser('affirm', help='let an agent into a holon, by its own person')
    af.add_argument('dir')
    af.add_argument('--by', required=True, help='the agent\'s person, person:<handle>')
    af.add_argument('--agent', required=True, help='agent:<handle>')
    af.add_argument('--pubkey', default=None, help='the agent\'s public key')
    af.add_argument('--key-dir', default=None, help='where keys live (default: env LIONSBERG_KEY_DIR, else ~/.ssh)')
    af.add_argument('--prime', default=None, help='for a clone (agent:<prime>.<name>): the prime agent that affirms it')
    j = sp.add_parser('join', help='clone a cell under <dir>/cells/<name>/')
    j.add_argument('dir')
    j.add_argument('url')
    j.add_argument('--name', required=True)
    j.add_argument('--actor', default=None, help='who joins (default: the keeper)')
    p = sp.add_parser('publish', help='copy your chosen lines into a joined cell and record the publishing')
    p.add_argument('dir')
    p.add_argument('cell')
    p.add_argument('ids', nargs='+')
    p.add_argument('--actor', required=True, help='the publishing person, person:<handle>')
    p.add_argument('--audience', default='members', choices=record.AUDIENCES)
    sp.add_parser('pull', help='bring every joined cell up to date (replays your own commits on top)').add_argument('dir')
    pu = sp.add_parser('push', help='send your own commits to each joined cell; on a refusal, pull and try once more')
    pu.add_argument('dir')
    pu.add_argument('--cell', default=None)
    sp.add_parser('hold', help='list every holon held').add_argument('dir')
    ns = ap.parse_args(argv)
    if not ns.cmd:
        ap.print_help()
        return 2
    if ns.cmd == 'init':
        res = init(ns.dir, ns.name, ns.kind, ns.keeper, sign=False if ns.no_key else None, adopt=ns.adopt,
                   key_dir=ns.key_dir, make_key=not ns.no_key)
        res = {'dir': res['dir'], 'holon': res['holon'], 'key': res['key'], 'said': res['said']}
    elif ns.cmd == 'admit':
        r = admit(ns.dir, ns.by, ns.who, ns.pubkey, key_dir=ns.key_dir)
        res = {'id': r['line']['id'], 'signed': r['signed'], 'said': r['said']}
    elif ns.cmd == 'affirm':
        r = affirm(ns.dir, ns.by, ns.agent, ns.pubkey, key_dir=ns.key_dir, prime=ns.prime)
        res = {'id': r['line']['id'], 'signed': r['signed'], 'said': r['said']}
    elif ns.cmd == 'join':
        res = join(ns.dir, ns.url, ns.name, actor=ns.actor)
    elif ns.cmd == 'publish':
        res = publish(ns.dir, ns.cell, ns.ids, ns.actor, ns.audience)
    elif ns.cmd == 'pull':
        res = pull(ns.dir)
    elif ns.cmd == 'push':
        res = push(ns.dir, ns.cell)
    else:
        res = [{'dir': d, 'id': record.holon_info(d).get('id'), 'name': record.holon_info(d).get('name')}
               for d in hold(ns.dir)]
    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, default=str) + '\n')
    return 0 if not (isinstance(res, dict) and res.get('ok') is False) else 1


if __name__ == '__main__':
    sys.exit(main())
