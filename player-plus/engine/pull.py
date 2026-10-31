#!/usr/bin/env python3
"""pull.py — the pull: one question to the forge per tick, fetch only what changed and is due.

A holon follows other holons' repositories (the cells joined under `cells/<name>/`) at the
cadences its person set, per source and per signal, in their own `subscribe` lines (the
Subscription Card, read through `subscriptions.py`; `subscriptions.json` in the home is read only
when no row comes from the record). On each tick the module asks the forge once what changed
across everything the holon follows (Forgejo's activity feed, GitHub's received events), fetches
only the cells that changed and whose cadence is due, and brings their lines in through
`holon.py`'s own gate (`holon._sync_one`): nothing but plain appends by others enters. The record
stays the truth; the forge is a relay. A missed tick loses nothing, because the next fetch brings
every commit since the last head this home saw.

What it keeps, in the home and never in a clone: the forge's etag, the ids of the forge's entries
already seen, the changes the forge reported and the home has not yet fetched, and each cell's
last pull, under the `.pull` key of `.pulled.json` (beside the per-cell heads `holon.py` keeps
there); and one JSON line per tick in `.pull-log.jsonl`, the cost of attention (requests, seconds,
bytes). Both are derived and safe to delete.

Plain code, run by a heartbeat: it calls no model and spends no model tokens. Standard library
only; runs under `python3 -I`. The token goes only in the Authorization header, which is never
carried on a redirect, and a redirect off the forge's host is refused: the token is never in a
URL, a log line, a report or an error.

Usage:
  python3 -I pull.py tick HOLON [--forge-url U --forge-kind forgejo|github --forge-user X
                                 --token-env NAME] [--now ISO] [--dry]
  python3 -I pull.py due HOLON [--now ISO]
  python3 -I pull.py subscriptions HOLON
"""
import argparse
import datetime as dt
import http.client
import json
import math
import os
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record  # noqa: E402
import holon   # noqa: E402
try:
    import subscriptions as subscriptions_mod  # noqa: E402 (the Subscription Card's own reader)
except ImportError:  # the kit without it: this module's own reading of the lines stands in
    subscriptions_mod = None

# The method's own constants. Each is overridable by the caller (a keyword argument, or a key
# of the forge dict); none belongs to a holon.
DEFAULT_CADENCE = 300   # seconds: a joined cell with no Subscription Card (the module brief's default)
BACKSTOP = 86400        # seconds: a cell the forge calls unchanged is fetched anyway once this long has passed
                        # since its last pull, so an entry the forge lost delays a line, never drops it
SINCE_OVERLAP = 600     # seconds: Forgejo's feed is read back this far before the newest entry already seen,
                        # for an entry its queue wrote late
GITHUB_LATENCY = 21600  # seconds: GitHub says an event may appear 30 s to 6 h after it happened
                        # (https://docs.github.com/en/rest/activity/events); its events are read back this far
SEEN_CAP = 1000         # the forge's entry ids kept as seen: ten pages of GitHub's largest, twenty of Forgejo's
FORGEJO_LIMIT = 50      # entries per page asked of Forgejo (`limit`)
GITHUB_PER_PAGE = 100   # events per page asked of GitHub (its largest page)
MAX_PAGES = 10          # pages read in one tick; a walk that needs more fetches every due cell instead
TIMEOUT = 30            # seconds a question to the forge may take
STATE_KEY = '.pull'     # this module's key in .pulled.json: a leading dot, so no cell's name can take it
LOG_NAME = '.pull-log.jsonl'
SUB_FIELDS = ('source', 'signals', 'cadence', 'surface', 'bell', 'agreement')
KINDS = ('forgejo', 'github')
# The Forgejo activity kinds that move a repository's refs (the swagger's Activity.op_type values);
# any other kind is read as seen and names no change.
FORGEJO_PUSH_OPS = ('commit_repo', 'merge_pull_request', 'auto_merge_pull_request', 'push_tag', 'delete_tag',
                    'delete_branch', 'mirror_sync_push', 'mirror_sync_create', 'mirror_sync_delete')
LOOPBACK = ('localhost', '127.0.0.1', '::1')   # the only hosts a token may be sent to over plain http


# ---------------------------------------------------------------- small guards

def _s(v):
    """A string in NFC, else ''."""
    return unicodedata.normalize('NFC', v) if isinstance(v, str) else ''


def _iso(d):
    return d.isoformat(timespec='seconds') if d else None


def _clock(now):
    """The tick's time: the given ISO time (or datetime), the machine's clock when none is given,
    and None when what is given is not a time."""
    if now is None:
        return dt.datetime.now().astimezone().replace(microsecond=0)
    d = record._parse_ts(now) if isinstance(now, str) else (now if isinstance(now, dt.datetime) else None)
    if isinstance(d, dt.datetime) and d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def _not_a_time(now):
    return 'the time given (%s) is not a time, so nothing was done; give an ISO 8601 time' % (
        repr(now)[:40] if not isinstance(now, str) else '"%s"' % now[:40])


def _seconds(v):
    """A cadence in whole seconds (at least 1), or None: a bool, a string, NaN, zero or less is no cadence."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    n = int(math.ceil(v))
    return n if n >= 1 else None


def _cadence(c):
    """The shortest cadence a Subscription Card names: an int, or the least of {signal: seconds}."""
    if isinstance(c, dict):
        vals = [x for x in (_seconds(v) for _, v in sorted(c.items(), key=lambda kv: str(kv[0]))) if x]
        return min(vals) if vals else None
    return _seconds(c)


def _scrub(text, token):
    text = text if isinstance(text, str) else str(text)
    return text.replace(token, '[token]') if token else text


def _read_json_nofollow(path):
    """(value, why): a JSON file read without following a link; (None, why) when it cannot be."""
    if os.path.islink(path):
        return None, 'is a link, so it is not read'
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return None, 'is absent'
    except OSError as e:
        return None, 'cannot be opened (%s)' % e.__class__.__name__
    try:
        with os.fdopen(fd, encoding='utf-8') as f:
            return json.load(f), ''
    except (OSError, ValueError):
        return None, 'is not readable JSON'


# ---------------------------------------------------------------- the home and its cells

def _home(holon_dir):
    """The home's own lines (record/ lines noted `_home_record`, as read_all does), id and keeper."""
    r = record.read(holon_dir)
    for l in r['lines']:
        if _s(l.get('_file')).startswith('record/'):
            l['_home_record'] = True
    keeper = r['keeper'] or _s(record.holon_info(holon_dir).get('keeper'))
    return {'id': r['holon'], 'keeper': keeper, 'lines': r['lines']}


def _origin_url(cell_dir):
    """The clone's `remote "origin"` url, read from .git/config (no subprocess); '' when absent."""
    path = os.path.join(cell_dir, '.git', 'config')
    if os.path.islink(path) or os.path.islink(os.path.join(cell_dir, '.git')) or not os.path.isfile(path):
        return ''
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read(65536)
    except (OSError, ValueError):
        return ''
    section = ''
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('['):
            section = line
            continue
        if re.match(r'^\[remote\s+"origin"\]$', section) and '=' in line:
            k, _, v = line.partition('=')
            if k.strip().lower() == 'url':
                return v.strip()
    return ''


def _where(url):
    """(host, owner/repo) of a repository url: https, ssh://, user@host:path, or a local path (host '')."""
    url = _s(url).strip()
    if not url:
        return '', ''
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*://', url):
        p = urllib.parse.urlsplit(url)
        host, path = (p.hostname or '').lower(), p.path
        if p.scheme == 'file':
            host = ''
    elif re.match(r'^[^/@:]+@[^:/]+:', url):
        host, _, path = url.split('@', 1)[1].partition(':')
        host = host.lower()
    else:
        host, path = '', url
    parts = [x for x in path.replace('\\', '/').split('/') if x]
    if parts and parts[-1].endswith('.git'):
        parts[-1] = parts[-1][:-4]
    return host, '/'.join(parts[-2:]) if len(parts) >= 2 else ''


def _cells(holon_dir):
    """Every cell joined under cells/: its name, folder, holon id, origin, host and owner/repo."""
    out = []
    for d in record.hold(holon_dir)[1:]:
        url = _origin_url(d)
        host, full = _where(url)
        out.append({'name': os.path.basename(d), 'dir': d, 'id': _s(record.holon_info(d).get('id')),
                    'url': url, 'host': host, 'full_name': full})
    return out


def _keys_of(cell):
    """The names a Subscription Card's source may use for a cell, case-folded."""
    keys = {cell['name'], cell['id'], cell['full_name'], cell['url']}
    if cell['url'].endswith('.git'):
        keys.add(cell['url'][:-4])
    if cell['host'] and cell['full_name']:
        keys.add(cell['host'] + '/' + cell['full_name'])
    return {k.casefold() for k in keys if k}


# ---------------------------------------------------------------- subscriptions

def _fold_home(holon_dir, lines, hid, keeper, clock):
    tp = os.path.join(holon_dir, 'types.json')
    types = record.load_types(tp if os.path.isfile(tp) and not os.path.islink(tp) else None)
    with record.signature_cache(holon_dir):
        return record.fold(lines, types, {hid: keeper} if hid and keeper else {}, clock=clock)


def _own_reading(lines, f, hid, keeper):
    """The fallback when subscriptions.py is absent: the person's own trusted, unretracted subscribe
    lines in their own home, later lines overlaying earlier field by field. Returns (rows, ignored)."""
    trust = f.get('trust') or {}
    bad = {i.get('id') for i in f.get('invalid') or [] if isinstance(i, dict)}
    items = {i.get('id'): i for i in f.get('subscriptions') or [] if isinstance(i, dict)}
    subs = [l for l in lines if l.get('type') == 'subscribe']
    good = [l for l in subs if trust.get(l.get('id')) in record.TRUSTED and l.get('id') not in bad
            and keeper and l.get('actor') == keeper and l.get('for') == keeper
            and hid and l.get('holon') == hid and l.get('reason') != 'untrusted']
    merged = {}
    for l in sorted(good, key=lambda l: (_iso(record._parse_ts(l.get('ts'))) or '', l['id'])):
        it = items.get(l['id']) or {}
        if it.get('state') == 'retracted':
            continue
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        vals = {k: it.get(k, body.get(k)) for k in SUB_FIELDS}
        src = _s(vals.get('source'))
        if not src:
            continue
        e = merged.setdefault(src.casefold(), {'set_by': {'source': l['id']}, 'basis': 'subscription'})
        for k in SUB_FIELDS:
            v = vals.get(k)
            if v in (None, '', [], {}) or (isinstance(v, dict) and 'elided' in v):
                continue
            if k == 'cadence' and isinstance(v, dict) and isinstance(e.get('cadence'), dict):
                v = dict(e['cadence'], **v)
            e[k] = _s(v) if isinstance(v, str) else v
            e['set_by'][k] = l['id']
    return [e for _, e in sorted(merged.items())], len(subs) - len(good)


def subscriptions(holon_dir, lines=None, clock=None):
    """What this holon follows: {"from": "record" | "subscriptions.json" | "none", "subscriptions": [...], "said"}.

    Each subscription is {source, signals, cadence, surface, bell, agreement, set_by, basis}. The rows
    come from the person's own trusted `subscribe` lines (and the Agreements their holon holds), read
    by `subscriptions.subscriptions` over the home's fold; an agent's `subscribe` line and an untrusted
    one are ignored, and a later line for the same source supersedes the earlier field by field. Only
    when the record gives no row is `<home>/subscriptions.json` read (a list of the same shape).
    `lines`, when given, are the home's lines already read (noted `_home_record` as `record.read_all`
    notes them). Never raises on its inputs."""
    out = {'from': 'none', 'subscriptions': [], 'said': ''}
    if not isinstance(holon_dir, str) or not holon_dir or not os.path.isdir(holon_dir):
        out['said'] = 'there is no home folder here, so nothing is followed'
        return out
    h = _home(holon_dir)
    hid, keeper = h['id'], h['keeper']
    lines = [l for l in lines if isinstance(l, dict)] if isinstance(lines, list) else h['lines']
    said, rows = [], []
    t = _clock(clock)
    if keeper and any(l.get('type') in ('subscribe', 'agree') for l in lines):
        f = _fold_home(holon_dir, lines, hid, keeper, _iso(t))
        reader = subscriptions_mod if callable(getattr(subscriptions_mod, 'subscriptions', None)) else None
        n_ignored = 0
        if reader is not None:
            try:
                rows = reader.subscriptions(lines, keeper, items=f, now=_iso(t), home=hid, joined=())
                n_ignored = len(reader.ignored(lines, keeper, items=f, home=hid) or [])
            except Exception as e:  # noqa: BLE001 (a reader that stops is said; the file still serves)
                rows = []
                said.append('the Subscription Card reader stopped (%s), so the record gave no row'
                            % e.__class__.__name__)
        else:
            rows, n_ignored = _own_reading(lines, f, hid, keeper)
        if n_ignored:
            said.append('%d subscribe line(s) were ignored: only the person\'s own trusted lines in their own home '
                        'set what this holon follows' % n_ignored)
        rows = [r for r in (rows or []) if isinstance(r, dict) and _s(r.get('source'))]
    if rows:
        out['from'] = 'record'
        out['subscriptions'] = sorted((_shape(r) for r in rows), key=lambda r: (r['source'].casefold(), r['source']))
        out['said'] = ' '.join(said + ['%d subscription(s), from the person\'s own lines' % len(rows)])
        return out
    v, why = _read_json_nofollow(os.path.join(holon_dir, 'subscriptions.json'))
    if v is None:
        said.append('no Subscription Card is held and subscriptions.json %s; every joined cell is pulled at the '
                    'default cadence' % why)
    elif not isinstance(v, list):
        said.append('subscriptions.json is not a list, so it is not read; every joined cell is pulled at the '
                    'default cadence')
    else:
        out['from'] = 'subscriptions.json'
        merged = {}
        for e in v:
            if not isinstance(e, dict) or not _s(e.get('source')):
                continue
            m = merged.setdefault(_s(e['source']).casefold(), {'set_by': {'file': 'subscriptions.json'},
                                                               'basis': 'subscription'})
            for k in SUB_FIELDS:
                x = e.get(k)
                if x not in (None, '', [], {}):
                    m[k] = _s(x) if isinstance(x, str) else x
        out['subscriptions'] = [_shape(e) for _, e in sorted(merged.items())]
        said.append('%d subscription(s), from subscriptions.json (the record gives none)'
                    % len(out['subscriptions']))
    out['said'] = ' '.join(said)
    return out


def _shape(e):
    sig = e.get('signals')
    sig = sorted({_s(x) for x in sig if _s(x)}) if isinstance(sig, list) else []
    bell = e.get('bell')
    bell = sorted({_s(x) for x in bell if _s(x)}) if isinstance(bell, list) else []
    cad = e.get('cadence')
    if isinstance(cad, dict):
        cad = {_s(k): v for k, v in sorted(cad.items(), key=lambda kv: str(kv[0])) if _s(k) and _seconds(v)}
    elif _seconds(cad) is None:
        cad = None
    set_by = e.get('set_by') if isinstance(e.get('set_by'), dict) else {}
    return {'source': _s(e.get('source')), 'signals': sig, 'cadence': cad or None,
            'surface': _s(e.get('surface')) or None, 'bell': bell, 'agreement': _s(e.get('agreement')) or None,
            'set_by': dict(sorted(set_by.items())), 'basis': _s(e.get('basis')) or 'subscription'}


# ---------------------------------------------------------------- state kept in the home

def _load_state(holon_dir):
    """This module's part of .pulled.json ({} when absent, unreadable, or a link)."""
    v, _ = _read_json_nofollow(holon._state_path(holon_dir))
    mine = v.get(STATE_KEY) if isinstance(v, dict) else None
    mine = mine if isinstance(mine, dict) else {}
    forge = mine.get('forge') if isinstance(mine.get('forge'), dict) else {}
    cells = mine.get('cells') if isinstance(mine.get('cells'), dict) else {}
    pend = forge.get('pending') if isinstance(forge.get('pending'), dict) else {}
    forge = dict(forge, pending={k: v for k, v in pend.items() if isinstance(k, str) and isinstance(v, str)})
    return {'forge': forge, 'cells': {k: v for k, v in cells.items() if isinstance(v, dict)}}


def _save_state(holon_dir, mine):
    """Write this module's key into .pulled.json, keeping every other key (holon.py's per-cell heads)."""
    path = holon._state_path(holon_dir)
    tmp = path + '.pull-tmp'
    if os.path.islink(path) or os.path.islink(tmp):
        return 'the home\'s .pulled.json is a link, so nothing was kept'
    v, _ = _read_json_nofollow(path)
    d = v if isinstance(v, dict) else {}
    d[STATE_KEY] = mine
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except OSError as e:
        return 'what this tick learned could not be kept (%s)' % e.__class__.__name__
    return ''


def _log(holon_dir, entry):
    path = os.path.join(holon_dir, LOG_NAME)
    if os.path.islink(path):
        return 'the pull log is a link, so the cost line was not written'
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + '\n')
    except OSError as e:
        return 'the cost line could not be written (%s)' % e.__class__.__name__
    return ''


# ---------------------------------------------------------------- what is due

def due(holon_dir, now=None, default_cadence=DEFAULT_CADENCE, subs=None, state=None):
    """What is due and when: {"as_of", "cells": [{cell, cadence, basis, pulled_at, due, next_due, sources}],
    "unjoined": [sources], "subscriptions_from", "said"}. Reads files only; fetches nothing."""
    t = _clock(now)
    out = {'as_of': _iso(t), 'cells': [], 'unjoined': [], 'subscriptions_from': 'none', 'said': []}
    if t is None:
        out['said'].append(_not_a_time(now))
        return out
    if not isinstance(holon_dir, str) or not holon_dir or not os.path.isdir(holon_dir):
        out['said'].append('there is no home folder here, so nothing is due')
        return out
    default_cadence = _seconds(default_cadence) or DEFAULT_CADENCE
    subs = subs if isinstance(subs, dict) else subscriptions(holon_dir, clock=_iso(t))
    state = state if isinstance(state, dict) else _load_state(holon_dir)
    out['subscriptions_from'] = subs.get('from')
    if subs.get('said'):
        out['said'].append(subs['said'])
    cells = _cells(holon_dir)
    matched = set()
    for c in cells:
        keys = _keys_of(c)
        mine = [s for s in subs.get('subscriptions') or [] if s['source'].casefold() in keys]
        matched.update(s['source'] for s in mine)
        cads = sorted((x, s.get('basis') or 'subscription') for x, s in ((_cadence(s.get('cadence')), s) for s in mine)
                      if x)
        cadence, basis = cads[0] if cads else (default_cadence, 'default')
        pulled = record._parse_ts((state['cells'].get(c['name']) or {}).get('pulled_at'))
        is_due = pulled is None or (t - pulled).total_seconds() >= cadence
        nxt = t if pulled is None else pulled + dt.timedelta(seconds=cadence)
        out['cells'].append({'cell': c['name'], 'cadence': cadence, 'basis': basis, 'pulled_at': _iso(pulled),
                             'due': is_due, 'next_due': _iso(nxt), 'sources': sorted(s['source'] for s in mine),
                             '_c': c, '_pulled': pulled})
    out['unjoined'] = sorted(s['source'] for s in subs.get('subscriptions') or [] if s['source'] not in matched)
    for src in out['unjoined']:
        out['said'].append('a Subscription Card follows %s, which is not joined here; there is nothing to fetch '
                           'until it is' % src)
    if not cells:
        out['said'].append('no cell is joined here, so there is nothing to pull')
    return out


def _public(d):
    return {k: v for k, v in d.items() if not k.startswith('_')}


# ---------------------------------------------------------------- the one question to the forge

def _hget(headers, name):
    if headers is None:
        return None
    try:
        v = headers.get(name)
        if v is not None:
            return v
    except (AttributeError, TypeError):
        pass
    try:
        for k, v in headers.items():
            if isinstance(k, str) and k.lower() == name.lower():
                return v
    except (AttributeError, TypeError):
        pass
    return None


def _origin(url):
    p = urllib.parse.urlsplit(url)
    return (p.scheme.lower(), (p.netloc or '').lower())


class _StayOnHost(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only on the forge's own scheme and host; any other is refused (the 3xx is
    then the answer). The Authorization header is never carried in any case (it is unredirected)."""

    def __init__(self, base):
        super().__init__()
        self.base = _origin(base)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _origin(urllib.parse.urljoin(req.full_url, newurl)) != self.base:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_opener(base):
    return urllib.request.build_opener(_StayOnHost(base)).open


def _ask(opener, req, token):
    """(status, headers, body bytes, said). An HTTP error or a refused redirect is a status; a timeout,
    a refused connection or a broken answer is status None and a sentence. Never raises; the token
    is scrubbed from any text."""
    try:
        resp = opener(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        try:
            body = e.read() or b''
        except Exception:  # noqa: BLE001 (an error page that cannot be read is an empty one)
            body = b''
        return e.code, e.headers, body if isinstance(body, bytes) else b'', ''
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError,
            http.client.HTTPException) as e:
        why = getattr(e, 'reason', None) or e
        return None, None, b'', _scrub('the forge did not answer (%s: %s)' % (e.__class__.__name__, why), token)
    except Exception as e:  # noqa: BLE001 (whatever an opener raises is said, never raised)
        return None, None, b'', _scrub('the question to the forge stopped (%s: %s)' % (e.__class__.__name__, e),
                                       token)
    try:
        status = getattr(resp, 'status', None) or resp.getcode()
        headers = getattr(resp, 'headers', None)
        body = resp.read() or b''
    except Exception as e:  # noqa: BLE001 (a broken answer, IncompleteRead included, is said, never raised)
        return None, None, b'', _scrub('the forge\'s answer could not be read (%s)' % e.__class__.__name__, token)
    finally:
        close = getattr(resp, 'close', None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001
                pass
    return status, headers, body if isinstance(body, bytes) else b'', ''


def _newer(a, b):
    """The later of two ISO times (by parsed time; a string that does not parse loses)."""
    pa, pb = record._parse_ts(a), record._parse_ts(b)
    if pa is None:
        return b
    if pb is None:
        return a
    return a if pa >= pb else b


def _entries(kind, data):
    """[(id, owner/repo, ts, names_a_change)] from one page of the forge's answer."""
    out = []
    for e in data:
        if not isinstance(e, dict):
            continue
        eid = e.get('id')
        eid = str(eid) if isinstance(eid, (int, str)) and not isinstance(eid, bool) and str(eid) else ''
        repo = e.get('repo') if isinstance(e.get('repo'), dict) else {}
        if kind == 'forgejo':
            full, ts, change = _s(repo.get('full_name')), _s(e.get('created')), e.get('op_type') in FORGEJO_PUSH_OPS
        else:
            full, ts, change = _s(repo.get('name')), _s(e.get('created_at')), True
        if eid:
            out.append((eid, full, ts, change))
    return out


def forge_changes(forge, seen=None, opener=None, etag=None):
    """Ask the forge once what changed across every repository the holon's account follows.

    `seen` is {entry id: ts} from earlier answers (None when the forge was never asked). Returns
    {"changed": {owner/repo: newest_ts}, "seen": {id: ts}, "poll_interval", "asked": requests,
    "status", "said", "etag", "bytes", "complete"}. Forgejo: GET /api/v1/users/{user}/activities/feeds
    (its activity feed, where a push is `commit_repo`; notifications never carry a push). GitHub:
    GET /users/{user}/received_events with If-None-Match, where a 304 means nothing changed. A change
    is an entry whose id was not seen before, so an entry that arrives late is still read. Pages are
    read while a full page holds nothing already seen and nothing older than the read-back window;
    each page is counted in `asked`. `complete` is False when the answer cannot be trusted to name
    every change: a first question, an error, a full page past the page cap. Never raises."""
    out = {'changed': {}, 'seen': dict(seen) if isinstance(seen, dict) else {}, 'poll_interval': None, 'asked': 0,
           'status': None, 'said': '', 'etag': etag or None, 'bytes': 0, 'complete': False}
    forge = forge if isinstance(forge, dict) else {}
    kind, base = _s(forge.get('kind')), _s(forge.get('url')).rstrip('/')
    token, user = _s(forge.get('token')), _s(forge.get('user'))
    if kind not in KINDS or not re.match(r'^https?://[^/]', base):
        out['said'] = 'no forge is named (a kind, forgejo or github, and an http(s) url), so it was not asked'
        return out
    if token and base.lower().startswith('http://') and \
            (urllib.parse.urlsplit(base).hostname or '').lower() not in LOOPBACK:
        out['said'] = ('the forge\'s url is plain http, and a token is never sent in the clear, so it was not '
                       'asked; each due cell is fetched instead (name the forge by https)')
        return out
    if kind == 'forgejo' and not token:
        out['said'] = ('there is no token for the forge, so the question across every repository cannot be '
                       'asked; each due cell is fetched instead')
        return out
    if not user:
        out['said'] = 'no forge user is named, so the feed of what the account follows cannot be asked for'
        return out
    opener = opener or _default_opener(base)
    limit = _seconds(forge.get('limit')) or (FORGEJO_LIMIT if kind == 'forgejo' else GITHUB_PER_PAGE)
    cap = _seconds(forge.get('max_pages')) or MAX_PAGES
    window = _seconds(forge.get('overlap')) or (SINCE_OVERLAP if kind == 'forgejo' else GITHUB_LATENCY)
    first = not isinstance(seen, dict)
    newest_seen = None
    for ts in (seen or {}).values():
        newest_seen = _newer(ts, newest_seen) if newest_seen else ts
    nt = record._parse_ts(newest_seen)
    cutoff = nt - dt.timedelta(seconds=window) if nt else None
    who = urllib.parse.quote(user, safe='')
    complete, page = True, 1
    while True:
        if kind == 'forgejo':
            url = '%s/api/v1/users/%s/activities/feeds?%s' % (base, who, urllib.parse.urlencode(
                [('limit', str(limit)), ('only-performed-by', 'false'), ('page', str(page))]))
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            if token:
                req.add_unredirected_header('Authorization', 'token ' + token)
        else:
            url = '%s/users/%s/received_events?%s' % (base, who, urllib.parse.urlencode(
                [('page', str(page)), ('per_page', str(limit))]))
            req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json'})
            if token:
                req.add_unredirected_header('Authorization', 'Bearer ' + token)
            if etag and page == 1:
                req.add_header('If-None-Match', etag)
        status, h, body, said = _ask(opener, req, token)
        out['asked'] += 1
        out['bytes'] += len(body)
        out['status'] = status
        if page == 1:
            pi = _hget(h, 'X-Poll-Interval')
            out['poll_interval'] = int(pi) if isinstance(pi, str) and pi.strip().isdigit() else None
        if status == 304 and page == 1:
            out['complete'] = not first
            out['said'] = 'nothing changed since the last question'
            return out
        if status != 200:
            out['said'] = said or 'the forge answered %s, so every due cell is fetched' % status
            out['complete'] = False
            return out
        if page == 1 and kind == 'github':
            out['etag'] = _s(_hget(h, 'ETag')) or None
        try:
            data = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            data = None
        if not isinstance(data, list):
            out['said'] = 'the forge\'s answer was not a list of entries, so every due cell is fetched'
            out['complete'] = False
            return out
        rows = _entries(kind, data)
        reached = False
        for eid, full, ts, change in rows:
            t = record._parse_ts(ts)
            if eid in out['seen'] or (cutoff is not None and t is not None and t < cutoff):
                reached = True
            if eid not in out['seen'] and change and full:
                out['changed'][full] = _newer(ts, out['changed'][full]) if full in out['changed'] else ts
            out['seen'][eid] = ts
        if first or reached or len(data) < limit:
            break
        if page >= cap:
            complete = False
            out['said'] = ('a full page of new entries and no further page this tick may read: older changes may '
                           'lie past it, so every due cell is fetched')
            break
        page += 1
    if first:
        complete = False
        out['said'] = 'the first question: there is no earlier answer to compare, so every due cell is fetched'
    keep = sorted(out['seen'].items(), key=lambda kv: (_iso(record._parse_ts(kv[1])) or '', kv[0]), reverse=True)
    out['seen'] = dict(sorted(keep[:SEEN_CAP]))
    out['complete'] = complete
    return out


# ---------------------------------------------------------------- requests rise

def _targets(h):
    """(the home's person, its agents (the actors whose lines answer for that person), the home's id)."""
    agents = set()
    for l in h['lines']:
        a = l.get('actor')
        if isinstance(a, str) and a.startswith('agent:') and l.get('for') == h['keeper']:
            agents.add(a)
    return h['keeper'], agents, {h['id']} if h['id'] else set()


def _addressed(line, person, agents, holons):
    """A request, rfg or escalate to the person, an agent of theirs or their holon; a say whose `to`
    names them; a commit whose committee is them (subscriptions.rises_first when it is held)."""
    rf = getattr(subscriptions_mod, 'rises_first', None)
    if callable(rf):
        try:
            return bool(rf(line, person, agents=sorted(agents), holons=sorted(holons)))
        except Exception:  # noqa: BLE001 (the reader failing falls back to the reading below)
            pass
    them = {person} | set(agents)
    b = line.get('body') if isinstance(line.get('body'), dict) else {}
    t = line.get('type')
    if t in ('request', 'rfg', 'escalate'):
        return isinstance(b.get('to'), str) and b['to'] in (them | set(holons))
    if t == 'say':
        to = b.get('to')
        to = [to] if isinstance(to, str) else (to if isinstance(to, list) else [])
        return any(isinstance(x, str) and x in them for x in to)
    if t == 'commit':
        return isinstance(b.get('committee'), str) and b['committee'] in them
    return False


def rising(new_lines, trust, own, person, agents=(), holons=()):
    """The ids, sorted, of the newly pulled lines that rise first: trusted by the fold (record.TRUSTED),
    not the home's own (`own`, the actors who write in the home), not from untrusted text, and
    addressed to the person, an agent of theirs or their holon."""
    trust = trust if isinstance(trust, dict) else {}
    own = set(own or ())
    out = set()
    for l in new_lines or []:
        if not isinstance(l, dict) or not isinstance(l.get('id'), str):
            continue
        if trust.get(l['id']) not in record.TRUSTED or l.get('actor') in own or l.get('reason') == 'untrusted':
            continue
        if _addressed(l, person, set(agents or ()), set(holons or ())):
            out.add(l['id'])
    return sorted(out)


def _rose(holon_dir, new_lines, clock):
    """Fold every holon held (the home and its cells) once, for the trust of the newly pulled lines."""
    h = _home(holon_dir)
    person, agents, holons = _targets(h)
    if not person:
        return []
    r = record.read_all(holon_dir)
    tp = os.path.join(holon_dir, 'types.json')
    types = record.load_types(tp if os.path.isfile(tp) and not os.path.islink(tp) else None)
    with record.signature_cache(holon_dir):
        f = record.fold(r['lines'], types, r['keepers'], clock=clock)
    own = {l.get('actor') for l in h['lines']} | {person}
    return rising(new_lines, f.get('trust'), own, person, agents, holons)


# ---------------------------------------------------------------- the tick

def _empty_report(as_of, dry):
    return {'as_of': as_of, 'asked_forge': 0, 'fetched': [], 'skipped': [], 'new_lines': {}, 'next_due': {},
            'sources': {}, 'rose': [], 'said': [], 'cost': {'requests': 0, 'seconds': 0.0, 'bytes': 0},
            'forge': None, 'subscriptions_from': 'none', 'dry': bool(dry)}


def tick(holon_dir, now=None, forge=None, opener=None, sync=None, dry=False, default_cadence=DEFAULT_CADENCE,
         backstop=BACKSTOP):
    """One beat of attention. Returns {as_of, asked_forge, fetched, skipped: [{cell, why}], new_lines,
    next_due, sources: {cell: {newest, pulled_at, ok, said}}, rose, said, cost: {requests, seconds,
    bytes}, forge, subscriptions_from, dry}.

    A cell is fetched when its cadence is due (the shortest among its Subscription Cards' signals;
    the first tick is always due) and the forge says it changed, or the forge cannot say (no forge,
    no token, an error, a cell on another host, a first pull, the backstop passed). `sync(exe,
    cell_dir, home)` brings one cell in (default `holon._sync_one`, the gate). With `dry` the forge
    is asked and the choice made, and nothing is fetched or kept. Never raises: whatever stops the
    tick is said, with the token scrubbed."""
    t0 = time.monotonic()
    token = _s(forge.get('token')) if isinstance(forge, dict) else ''
    try:
        rep = _tick(holon_dir, now, forge, opener, sync, dry, default_cadence, backstop, token, t0)
    except Exception as e:  # noqa: BLE001 (law 8: a report in words, never an exception)
        t = None
        try:
            t = _clock(now)
        except Exception:  # noqa: BLE001
            pass
        rep = _empty_report(_iso(t), dry)
        rep['said'].append('the tick stopped (%s: %s); nothing more was done this tick'
                           % (e.__class__.__name__, str(e)[:200]))
    rep['cost']['seconds'] = round(time.monotonic() - t0, 3)
    rep['said'] = [_scrub(x, token) for x in rep['said'] if x]
    return rep


def _tick(holon_dir, now, forge, opener, sync, dry, default_cadence, backstop, token, t0):
    sync = sync or holon._sync_one
    t = _clock(now)
    rep = _empty_report(_iso(t), dry)
    if t is None:
        rep['said'].append(_not_a_time(now))
        return rep
    if not isinstance(holon_dir, str) or not holon_dir or not os.path.isdir(holon_dir):
        rep['said'].append('there is no home folder here, so nothing was pulled')
        return rep
    state = _load_state(holon_dir)
    plan = due(holon_dir, t, default_cadence, state=state)
    rep['subscriptions_from'] = plan['subscriptions_from']
    rep['said'].extend(plan['said'])
    due_cells = [c for c in plan['cells'] if c['due']]
    backstop = _seconds(backstop) or BACKSTOP
    joined = {c['_c']['full_name'].casefold() for c in plan['cells'] if c['_c']['full_name']}

    # the one question
    mode, changed, complete, too_soon, pages = 'none', {}, False, False, 0
    kind = _s(forge.get('kind')) if isinstance(forge, dict) else ''
    fst = dict(state['forge'])
    if isinstance(forge, dict) and kind:
        which = '%s %s' % (kind, _s(forge.get('url')).rstrip('/'))
        if fst.get('for') != which:
            fst = {'for': which, 'pending': dict(fst.get('pending') or {})}   # another forge: its ids mean nothing here
        web = _s(forge.get('host')).lower() or (urllib.parse.urlsplit(_s(forge.get('url'))).hostname or '').lower()
        if kind == 'github' and web.startswith('api.'):
            web = web[4:]
        rep['forge'] = {'kind': kind, 'host': web or None, 'status': None, 'poll_interval': None,
                        'next_question': None, 'said': ''}
        last_ask = record._parse_ts(fst.get('asked_at'))
        poll = _seconds(fst.get('poll_interval'))
        if poll and last_ask and (t - last_ask).total_seconds() < poll:
            too_soon, mode, complete = True, 'forge', True
            nq = last_ask + dt.timedelta(seconds=poll)
            rep['forge'].update(poll_interval=poll, next_question=_iso(nq))
            rep['said'].append('too soon: the forge asks for %d seconds between questions; the next is at %s. Only '
                               'what it cannot speak for, or already named, is fetched before it' % (poll, _iso(nq)))
        elif not due_cells:
            rep['said'].append('nothing is due, so the forge was not asked')
        else:
            seen = fst.get('seen') if isinstance(fst.get('seen'), dict) else None
            res = forge_changes(forge, seen, opener=opener, etag=_s(fst.get('etag')) or None)
            rep['cost']['bytes'] += res['bytes']
            rep['forge'].update(status=res['status'], poll_interval=res['poll_interval'], said=res['said'])
            pages = res['asked']
            rep['cost']['requests'] += pages
            if res['asked'] and res['status'] in (200, 304):
                mode, changed, complete = 'forge', res['changed'], res['complete']
                if res['said'] and not complete:
                    rep['said'].append(res['said'])
                fst['etag'] = res['etag'] or fst.get('etag')
                fst['asked_at'] = _iso(t)
                fst['poll_interval'] = res['poll_interval']
                fst['seen'] = res['seen']
            else:
                mode = 'fallback'
                rep['said'].append(res['said'])
            if res['poll_interval']:
                rep['forge']['next_question'] = _iso(t + dt.timedelta(seconds=res['poll_interval']))
    pending = {k: v for k, v in (fst.get('pending') or {}).items() if k in joined}
    for full, ts in changed.items():
        k = full.casefold()
        if k in joined:
            pending[k] = _newer(ts, pending[k]) if k in pending else (ts or _iso(t))

    # decide, then fetch
    decided = []
    for c in plan['cells']:
        name, cell = c['cell'], c['_c']
        if not c['due']:
            rep['skipped'].append({'cell': name, 'why': 'not due'})
            continue
        pulled = c['_pulled']
        known = bool(rep['forge'] and cell['full_name'] and cell['host'] and cell['host'] == rep['forge']['host'])
        if mode != 'forge' or pulled is None or not known or not complete \
                or (t - pulled).total_seconds() >= backstop or cell['full_name'].casefold() in pending:
            decided.append(c)
        else:
            rep['skipped'].append({'cell': name, 'why': 'too soon' if too_soon else 'unchanged'})
    rep['asked_forge'] = pages + (len(decided) if mode == 'fallback' else 0)   # a fallback fetch is its own question
    exe = holon._git() if decided and not dry else None
    arrived = []
    for c in decided:
        name, d = c['cell'], c['_c']['dir']
        if dry:
            rep['fetched'].append(name)
            continue
        if not exe:
            rep['sources'][name] = {'ok': False, 'said': 'git is not installed; nothing was pulled'}
            continue
        if not os.path.isdir(os.path.join(d, '.git')) or os.path.islink(os.path.join(d, '.git')):
            rep['sources'][name] = {'ok': False, 'said': 'not a git clone; nothing to pull'}
            continue
        before = {l['id'] for l in record.read(d)['lines']}
        rep['cost']['requests'] += 1
        try:
            ok, said = sync(exe, d, holon_dir)
        except Exception as e:  # noqa: BLE001 (git that cannot run is said, never raised)
            ok, said = False, 'git could not run: %s' % e.__class__.__name__
        r = record.read(d)
        new = [l for l in r['lines'] if l['id'] not in before]
        rep['fetched'].append(name)
        rep['new_lines'][name] = len(new)
        cs = state['cells'].setdefault(name, {})
        if ok:
            cs['pulled_at'] = _iso(t)
            cs['newest'] = r['newest']
            pending.pop(c['_c']['full_name'].casefold(), None)
        rep['sources'][name] = {'ok': bool(ok), 'said': _scrub(said, token), 'newest': r['newest']}
        arrived.extend(new)
    if arrived:
        rep['rose'] = _rose(holon_dir, arrived, _iso(t))
    for c in plan['cells']:
        name = c['cell']
        cs = state['cells'].get(name) or {}
        src = rep['sources'].setdefault(name, {})
        if 'newest' not in src:
            src['newest'] = cs['newest'] if 'newest' in cs else record.read(c['_c']['dir'])['newest']
        src['pulled_at'] = cs.get('pulled_at')
        p = record._parse_ts(cs.get('pulled_at'))
        rep['next_due'][name] = _iso(p + dt.timedelta(seconds=c['cadence'])) if p else _iso(t)
    rep['fetched'].sort()
    rep['skipped'].sort(key=lambda x: x['cell'])
    rep['sources'] = {k: dict(sorted(v.items())) for k, v in sorted(rep['sources'].items())}
    if dry:
        rep['said'].append('dry: the forge was asked and the choice made; nothing was fetched or kept')
        return rep
    fst['pending'] = dict(sorted(pending.items()))
    state['forge'] = fst
    w = _save_state(holon_dir, state)
    if w:
        rep['said'].append(w)
    w = _log(holon_dir, {'as_of': rep['as_of'], 'asked_forge': rep['asked_forge'], 'fetched': rep['fetched'],
                         'skipped': len(rep['skipped']), 'new_lines': rep['new_lines'],
                         'cost': dict(rep['cost'], seconds=round(time.monotonic() - t0, 3))})
    if w:
        rep['said'].append(w)
    return rep


# ---------------------------------------------------------------- command line

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pull.py', description='The pull: one question to the forge per tick; '
                                 'only what changed and is due is fetched, through the gate. Calls no model.')
    sp = ap.add_subparsers(dest='cmd')
    t = sp.add_parser('tick', help='ask the forge once, fetch what is due and changed')
    t.add_argument('holon')
    t.add_argument('--forge-url', default=None)
    t.add_argument('--forge-kind', default=None, choices=KINDS)
    t.add_argument('--forge-user', default=None)
    t.add_argument('--forge-host', default=None, help='the host the cells\' repositories live on, when it is not '
                                                      'the API url\'s')
    t.add_argument('--token-env', default=None, help='the name of the environment variable holding the token '
                                                     '(the token itself is never an argument)')
    t.add_argument('--now', default=None)
    t.add_argument('--dry', action='store_true', help='ask and decide; fetch and keep nothing')
    d = sp.add_parser('due', help='what is due and when')
    d.add_argument('holon')
    d.add_argument('--now', default=None)
    sp.add_parser('subscriptions', help='what this holon follows, and where that was read').add_argument('holon')
    ns = ap.parse_args(argv)
    if not ns.cmd:
        ap.print_help()
        return 2
    if ns.cmd == 'tick':
        forge = None
        if ns.forge_url and ns.forge_kind:
            forge = {'kind': ns.forge_kind, 'url': ns.forge_url, 'user': ns.forge_user or '',
                     'host': ns.forge_host or '', 'token': os.environ.get(ns.token_env, '') if ns.token_env else ''}
        res = tick(ns.holon, now=ns.now, forge=forge, dry=ns.dry)
    elif ns.cmd == 'due':
        r = due(ns.holon, ns.now)
        res = dict(r, cells=[_public(c) for c in r['cells']])
    else:
        res = subscriptions(ns.holon)
    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=str) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
