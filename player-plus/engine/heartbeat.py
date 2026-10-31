#!/usr/bin/env python3
"""heartbeat.py — the heartbeat: one always-on process per holon, plain code that spends no model tokens.

    beat(home_dir, now=None, forge=None, opener=None, wake=None, dry=False) -> report
    run(home_dir, every_s=None, beats=None, ...) -> {"beats", "errors", "every_s", "stopped"}
    every(home_dir, now=None, every_s=None) -> {"every_s", "basis", "said"}
    install(home_dir, kind="launchd" | "systemd" | "cron", out_dir=None, python=sys.executable) -> {"files", "said"}
    status(home_dir, now=None) -> {last_beat, last_wake, beats_today, wakes_today, cost_today, next_due, said}

Every holon is always awake. A process on some host that never sleeps pulls the holon's
subscriptions on their cadences, wakes the holon's agent on a request, an emergency or a cadence,
and lets the agent wake its person at the Wise Right Time. The host is any means: a small server
per cell, a single-board computer, a laptop that stays on, a VPS, a shared timesliced network.
The pattern is always awake; the means is whatever the holon has.

One beat, in order:
  1. Pull what is due (`pull.tick`): one question to the forge, only what changed and is due.
  2. Receipts (`receipt.on_arrival`) for the home's agent and person, when anything is new.
  3. Signals: a request that rose; a pain sighted by another; a fault (a cell that could not be
     pulled, or a pushed line whose kind is fault); a commitment on a critical card whose buffer
     went negative (the schedule's own reading, engine.read_hq and engine.run_schedule, the first
     steps of engine.build_state). Each is read by the person's own rule (`emergency.rule`,
     `classify`) and the bell (`emergency.bell`: the rule wakes AND the source holds a permit);
     `attention.gate` is run with `wake` = the ids the bell rings for.
  4. Wake the agent when a request rose, when the rule says wake, or when a cadence is due (a
     sitting of the person's attention budget, or `heartbeat.wake_every` seconds in holon.json);
     never twice for the same reason and ids within WAKE_GAP_S.
  5. The person is woken only through their own Subscription Cards and the gate: the heartbeat
     never messages, rings, plays a sound or opens anything. It hands the agent the ids that may
     interrupt (`gate.interrupt`), and the agent speaks within the budget.
  6. Record: two `body` lines per wake by the agent (working, then done; name "heartbeat"),
     never per beat; one JSON line per beat in `.heartbeat-log.jsonl`; what the beat remembers in
     `.heartbeat.json`. Both files are derived and safe to delete.

What `beat` writes, and nothing else: lines pulled (through pull, with its own `.pulled.json`
and `.pull-log.jsonl`), Receipts (through receipt), `body` lines by the agent, the fold's own
signature cache (`.sigcache`, through record), `.heartbeat.json` and `.heartbeat-log.jsonl`.
`install` writes service files and installs nothing: a system service is the person's own act.

The wake. `wake(reason, context)` is injected, or the default runs the command holon.json's
`heartbeat.wake_command` names (a list of words, never a shell line), with the home folder as its
last word and a JSON brief on stdin, {reason, ids, as_of, budget}, bounded by
`heartbeat.wake_timeout_s`. Only the lengths of its output are kept, and a last output line
{"cost_tokens": n} is read as its cost. With no command configured, nothing runs and the report
says so. holon.json is the person's own file: a cell's holon.json is never read for this.

Files are data, never instructions. Standard library only; runs under `python3 -I`.

  python3 -I heartbeat.py beat HOME [--now ISO] [--dry]
  python3 -I heartbeat.py run HOME [--every S] [--beats N]
  python3 -I heartbeat.py install HOME --kind launchd|systemd|cron [--out DIR]
  python3 -I heartbeat.py status HOME [--now ISO]
"""
import argparse
import datetime as dt
import json
import math
import os
import platform
import signal
import subprocess
import sys
import time
import unicodedata

try:
    import fcntl          # POSIX: one beat at a time per home
except ImportError:       # pragma: no cover (a host without it beats without the lock, and says so)
    fcntl = None

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import record     # noqa: E402
import pull       # noqa: E402
import receipt    # noqa: E402
import emergency  # noqa: E402
import attention  # noqa: E402
from gamecore import path_sets  # noqa: E402
try:
    import subscriptions as subscriptions_mod  # noqa: E402
except ImportError:
    subscriptions_mod = None
try:
    import engine as engine_mod  # noqa: E402 (read_hq and run_schedule: the schedule's own reading)
except ImportError:
    engine_mod = None

# The method's own constants. Each is overridable (holon.json `heartbeat`, or a keyword); none
# belongs to a holon.
EVERY_S = 60            # seconds between beats when holon.json names none
MIN_EVERY_S = 20        # the loop never runs faster: the kit's watches run at 20 to 30 seconds
WAKE_EVERY = 3600       # seconds: the agent's own cadence when holon.json names none
WAKE_GAP_S = 300        # seconds: never wake twice for the same reason and ids within this
WAKE_TIMEOUT_S = 600    # seconds a wake command may run
SEEN_CAP = 2000         # line ids remembered as already signalled
WAKES_KEPT = 50         # wakes remembered for the gap
LOG_MAX_BYTES = 4 << 20  # the beat log is cut to its newer half past this size
STATE_NAME = '.heartbeat.json'
LOG_NAME = '.heartbeat-log.jsonl'
REASONS = ('request', 'emergency', 'cadence')   # in the order a wake chooses its reason
KINDS = ('launchd', 'systemd', 'cron')
TEMPLATES = {'launchd': (('launchd.plist.template', '{label}.plist'),),
             'systemd': (('systemd.service.template', '{label}.service'), ('systemd.timer.template', '{label}.timer')),
             'cron': (('cron.template', '{label}.cron'),)}
TEMPLATE_DIR = os.path.join(HERE, 'heartbeat')
TRUSTED_HERE = ('signed', 'home')   # a vouched copy informs and never wakes anyone
RISE_KIND = {'request': 'request', 'rfg': 'request', 'escalate': 'request', 'say': 'say', 'commit': 'commitment'}
MAX_LOG_READ = 2 << 20  # status reads at most this much of the log's tail


# ---------------------------------------------------------------- small readers

def _s(v):
    """A string in NFC, else ''."""
    return unicodedata.normalize('NFC', v) if isinstance(v, str) else ''


def _iso(d):
    return d.isoformat(timespec='seconds') if isinstance(d, dt.datetime) else None


def _clock(now):
    """The beat's time: the given ISO time (or datetime), the machine's clock only when none is
    given, and None when what is given is not a time."""
    if now is None:
        return dt.datetime.now().astimezone().replace(microsecond=0)
    d = record._parse_ts(now) if isinstance(now, str) else (now if isinstance(now, dt.datetime) else None)
    if isinstance(d, dt.datetime) and d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.replace(microsecond=0) if isinstance(d, dt.datetime) else None


def _ts(v):
    d = record._parse_ts(v) if isinstance(v, str) else None
    return d if isinstance(d, dt.datetime) else None


def _seconds(v):
    """Whole seconds (at least 1), or None: a bool, a string, NaN, zero or less is no number of seconds."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    n = int(math.ceil(v))
    return n if n >= 1 else None


def _strs(v):
    """A list of non-empty strings, else []: what the beat remembers is data, and a wrong type is forgotten."""
    return [x for x in v if isinstance(x, str) and x] if isinstance(v, list) else []


def _home_ok(home_dir):
    """('' when the home can be beaten, else why not)."""
    if not isinstance(home_dir, str) or not home_dir:
        return 'no home folder was given, so nothing was done'
    if os.path.islink(home_dir.rstrip(os.sep) or home_dir):
        return 'the home is reached through a link; nothing is done through one'
    if not os.path.isdir(home_dir):
        return 'there is no home folder at %s, so nothing was done' % home_dir[:200]
    return ''


def _read_json_nofollow(path):
    """(value, why): JSON read without following a link; (None, why) when it cannot be."""
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
    except (OSError, ValueError, RecursionError):
        return None, 'is not readable JSON'


def _config(home_dir):
    """holon.json's `heartbeat` section of the home ({} when absent), and holon.json's keeper."""
    v, _ = _read_json_nofollow(os.path.join(home_dir, 'holon.json'))
    v = v if isinstance(v, dict) else {}
    hb = v.get('heartbeat') if isinstance(v.get('heartbeat'), dict) else {}
    return hb, _s(v.get('keeper'))


def _forge_from(cfg):
    """The forge holon.json names (`heartbeat.forge`: kind, url, user, host, token_env), with the token
    read from the environment variable it names; None when none is named."""
    f = cfg.get('forge') if isinstance(cfg.get('forge'), dict) else None
    if not f or _s(f.get('kind')) not in pull.KINDS or not _s(f.get('url')):
        return None
    env = _s(f.get('token_env'))
    return {'kind': _s(f['kind']), 'url': _s(f['url']), 'user': _s(f.get('user')), 'host': _s(f.get('host')),
            'token': os.environ.get(env, '') if env else ''}


def _wake_command(cfg):
    """(argv, why): the wake command as a list of words, or (None, why)."""
    c = cfg.get('wake_command')
    if c is None:
        return None, 'no wake command configured; the agent is not woken'
    if not isinstance(c, list) or not c or not all(isinstance(x, str) and x and '\x00' not in x for x in c):
        return None, 'the wake command in holon.json is not a list of words; it was not run, and the agent is not woken'
    return [_s(x) for x in c], ''


# ---------------------------------------------------------------- what the beat remembers

def _load_state(home_dir):
    v, _ = _read_json_nofollow(os.path.join(home_dir, STATE_NAME))
    return v if isinstance(v, dict) else {}


def _save_state(home_dir, st):
    path = os.path.join(home_dir, STATE_NAME)
    tmp = path + '.tmp'
    if os.path.islink(path) or os.path.islink(tmp):
        return 'the home\'s %s is a link, so what this beat learned was not kept' % STATE_NAME
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(st, f, indent=1, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError as e:
        return 'what this beat learned could not be kept (%s)' % e.__class__.__name__
    return ''


def _log(home_dir, entry):
    path = os.path.join(home_dir, LOG_NAME)
    if os.path.islink(path):
        return 'the beat log is a link, so the beat\'s line was not written'
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + '\n')
        if os.path.getsize(path) > LOG_MAX_BYTES:
            _trim(path)
    except OSError as e:
        return 'the beat\'s line could not be written (%s)' % e.__class__.__name__
    return ''


def _trim(path):
    """Keep the newer half of the log, whole lines only (a temporary file, then a rename)."""
    with open(path, 'rb') as f:
        f.seek(-(LOG_MAX_BYTES // 2), os.SEEK_END)
        tail = f.read()
    tail = tail[tail.find(b'\n') + 1:]
    tmp = path + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(tail)
    os.replace(tmp, path)


def _lock(home_dir):
    """(fd, why): an exclusive lock on the home folder itself, so two beats never overlap (a folder
    lock writes nothing). (None, '') where the host has no lock; (None, why) when another beat holds it."""
    if fcntl is None:
        return None, ''
    try:
        fd = os.open(home_dir, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    except OSError:
        return None, ''
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None, 'another beat of this home is running; this one did nothing'
    return fd, ''


def _unlock(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------- who the home is

def _people(home_lines, home_id, keeper, cfg):
    """(person, agent, said): the keeper, and the keeper's own affirmed agent: an `affirm` in the home's
    own record by the keeper for themselves, not from untrusted text. holon.json `heartbeat.agent`
    chooses among several; with several and none chosen, none is guessed."""
    if not keeper.startswith('person:'):
        return '', '', 'the home has no keeper who is a person, so no agent and no Receipt'
    agents = []
    for l in home_lines:
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if (l.get('type') == 'affirm' and l.get('actor') == keeper and l.get('for') == keeper
                and l.get('reason') != 'untrusted' and _s(l.get('_file')).startswith('record/')
                and (not home_id or _s(l.get('holon')) == home_id)
                and _s(b.get('agent')).startswith('agent:') and '.' not in _s(b.get('agent'))[6:]):
            if _s(b['agent']) not in agents:
                agents.append(_s(b['agent']))
    chosen = _s(cfg.get('agent'))
    if chosen and chosen in agents:
        return keeper, chosen, ''
    if chosen:
        return keeper, '', ('holon.json names %s as the heartbeat\'s agent, but the keeper has not affirmed it here; '
                            'no agent' % chosen[:60])
    if len(agents) == 1:
        return keeper, agents[0], ''
    if not agents:
        return keeper, '', 'the keeper has affirmed no agent here, so no Receipt and no body line is written'
    return keeper, '', ('the keeper has affirmed %d agents here; name one in holon.json heartbeat.agent, '
                        'and until then no Receipt and no body line is written' % len(agents))


def _key(home_read, pull_rep):
    """What the beat has seen: the newest line of the home and of each cell."""
    k = {'home': ((home_read.get('newest') or {}).get('id')) or ''}
    for name, src in sorted(((pull_rep or {}).get('sources') or {}).items()):
        k[name] = ((src or {}).get('newest') or {}).get('id') or '' if isinstance(src, dict) else ''
    return json.dumps(k, sort_keys=True)


# ---------------------------------------------------------------- the signals

def _members(folded, holon_id):
    adm = folded.get('admitted') if isinstance(folded, dict) and isinstance(folded.get('admitted'), dict) else {}
    m = adm.get(holon_id) if holon_id else None
    return sorted(a for a, e in m.items() if isinstance(a, str) and isinstance(e, dict)) if isinstance(m, dict) else []


def _cal(d):
    v, _ = _read_json_nofollow(os.path.join(d, 'calendar.json')) if isinstance(d, str) and d else (None, '')
    return v if isinstance(v, dict) else None


def _reading(home_dir, t):
    """Every holon held, folded at the beat's own time, and the schedule over it (engine.run_schedule,
    as engine.build_state runs it): (folded, lines, schedule report, why). The home's hand-written
    Cards are not read here: a paper Card is a view, and enters the record by card.py append."""
    try:
        r = record.read_all(home_dir)
        tp = os.path.join(home_dir, 'types.json')
        types = record.load_types(tp if os.path.isfile(tp) and not os.path.islink(tp) else None)
        with record.signature_cache(home_dir):
            folded = record.fold(r['lines'], types, r.get('keepers') or {}, clock=_iso(t))
    except Exception as e:  # noqa: BLE001 (a reading that cannot run is said, never raised)
        return None, [], None, 'the record could not be read (%s)' % e.__class__.__name__
    lines = r['lines']
    by_id = {l.get('id'): l for l in lines if isinstance(l, dict)}
    for val in folded.values():                 # each item the links of the line that made it, for the schedule
        for it in val if isinstance(val, list) else []:
            ln = by_id.get(it.get('id')) if isinstance(it, dict) and 'links' not in it else None
            if ln and isinstance(ln.get('links'), dict) and ln['links']:
                it['links'] = ln['links']
    if engine_mod is None:
        return folded, lines, None, 'engine.py is not beside heartbeat.py; no commitment\'s buffer is read'
    holons = []
    for h in r.get('holons') or []:
        if not h.get('id') or h.get('refused'):
            continue
        info = record.holon_info(h.get('dir')) if h.get('dir') else {}
        holons.append({'id': h['id'], 'name': h.get('name') or info.get('name'), 'kind': info.get('kind'),
                       'keeper': h.get('keeper'), 'dir': h.get('dir'), 'calendar': _cal(h.get('dir'))})
    try:
        rep, note = engine_mod.run_schedule(folded, _cal(home_dir), t, holons, lines)
    except Exception as e:  # noqa: BLE001
        rep, note = None, 'the schedule could not run (%s)' % e.__class__.__name__
    return folded, lines, rep, note or ''


def _signals(home_id, person, agents, folded, lines, rep, rose, pull_rep, seen, negatives, seed):
    """(signals, seen ids now, negative commitments now). A line already signalled is not signalled
    again; the first beat (seed) learns what already stands and signals only what arrived."""
    trust = folded.get('trust') if isinstance(folded, dict) and isinstance(folded.get('trust'), dict) else {}
    own = {person} | set(agents)
    by_id = {l.get('id'): l for l in lines if isinstance(l, dict) and isinstance(l.get('id'), str)}
    out, seen_now = [], list(seen)
    have = set(seen)

    def note(i):
        if i not in have:
            have.add(i)
            seen_now.append(i)

    for i in rose or []:                       # requests that rose at this pull (pull.rising: trusted, addressed)
        l = by_id.get(i) or {}
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        out.append({'id': i, 'kind': RISE_KIND.get(l.get('type'), 'request'), 'from': _s(l.get('for')) or None,
                    'holon': _s(l.get('holon')) or home_id, 'by': _s(b.get('by')) or None})
        note(i)
    for l in sorted(by_id.values(), key=lambda x: x['id']):
        if l['id'] in have or trust.get(l['id']) not in TRUSTED_HERE or l.get('reason') == 'untrusted':
            continue
        if l.get('actor') in own or l.get('for') in own:
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        push = b.get('push') if isinstance(b.get('push'), dict) else {}
        kind = None
        if l.get('type') == 'sight' and _s(b.get('kind')) == 'pain':
            kind = {'kind': 'sight', 'sight_kind': 'pain'}
        elif _s(push.get('kind')) == 'fault':
            kind = {'kind': 'fault'}
        if kind is None:
            continue
        note(l['id'])
        if not seed:
            out.append(dict(kind, id=l['id'], **{'from': _s(l.get('for')) or None,
                                                 'holon': _s(l.get('holon')) or home_id}))
    for name, src in sorted(((pull_rep or {}).get('sources') or {}).items()):
        if isinstance(src, dict) and src.get('ok') is False:
            out.append({'id': 'fault:pull:%s' % name, 'kind': 'fault', 'holon': home_id,
                        'said': _s(src.get('said'))[:200]})
    neg_now = []
    crit, _ = path_sets(rep)
    for r in (rep or {}).get('commitments') or [] if isinstance(rep, dict) else []:
        if not isinstance(r, dict) or not isinstance(r.get('commitment'), str):
            continue
        bd = r.get('buffer_days')
        if isinstance(bd, bool) or not isinstance(bd, (int, float)) or bd >= 0:
            continue
        if r.get('delivered_by') not in crit or not ({r.get('committor'), r.get('committee')} & own):
            continue
        neg_now.append(r['commitment'])
        if not seed and r['commitment'] not in negatives:
            out.append({'id': r['commitment'], 'kind': 'commitment', 'buffer_days': bd, 'critical': True,
                        'by': r.get('due_by'), 'holon': _s(r.get('holon')) or home_id})
    uniq = {}
    for s in out:
        uniq.setdefault(s['id'], s)
    return [uniq[k] for k in sorted(uniq)], seen_now[-SEEN_CAP:], sorted(set(neg_now))


def _weigh(signals, rule, folded, lines, person, home_id, t, nxt):
    """Each signal read by the person's rule (classify) and the bell (rule AND permit)."""
    subs = []
    if subscriptions_mod is not None and isinstance(folded, dict):
        try:
            subs = subscriptions_mod.subscriptions(lines, person, items=folded, now=_iso(t), home=home_id)
        except Exception:  # noqa: BLE001 (a reader that fails grants no permit)
            subs = []
    rows = []
    for s in signals:
        mem = _members(folded, s.get('holon')) if isinstance(folded, dict) else []
        ctx = {'members': mem, 'now': _iso(t), 'next_sitting': _iso(nxt)}
        c = emergency.classify(s, rule, ctx)
        b = emergency.bell(s, rule, subs, folded if isinstance(folded, dict) else {}, mem, _iso(t), ctx)
        rows.append({'id': s['id'], 'kind': s['kind'], 'wake': bool(c.get('wake')), 'ring': bool(b.get('ring')),
                     'permit': b.get('permit'), 'why': c.get('why'), 'bell': b.get('why')})
    return rows


def _prev_sitting(budget, t):
    best = None
    for x in budget.get('sittings') or []:
        try:
            h, m = (int(p) for p in str(x).split(':')[:2])
            c = t.replace(hour=h, minute=m, second=0, microsecond=0)
        except (ValueError, TypeError):
            continue
        if c > t:
            c -= dt.timedelta(days=1)
        best = c if best is None or c > best else best
    return best


# ---------------------------------------------------------------- the wake

def _wake_env(cfg, token):
    """The environment the wake runs in: the beat's own, less the forge token's variable and any
    variable that holds the token. The token is for the forge, never for the agent's command."""
    f = cfg.get('forge') if isinstance(cfg.get('forge'), dict) else {}
    drop = {_s(f.get('token_env'))} - {''}
    return {k: v for k, v in os.environ.items() if k not in drop and not (token and v == token)}


def _wake_default(home_dir, argv, brief, timeout, env=None):
    """Run the person's wake command: argv plus the home folder, the brief as JSON on stdin. Keeps only
    the lengths of its output, and a last output line {"cost_tokens": n}. `started` is False when the
    command could not be started at all."""
    t0 = time.monotonic()
    try:
        r = subprocess.run(argv + [home_dir], input=json.dumps(brief, sort_keys=True).encode('utf-8'),
                           capture_output=True, timeout=timeout, cwd=home_dir, shell=False, env=env)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'started': True, 'seconds': round(time.monotonic() - t0, 3),
                'said': 'the wake command ran past %d seconds and was stopped' % timeout}
    except (OSError, ValueError) as e:
        return {'ok': False, 'started': False, 'seconds': 0,
                'said': 'the wake command could not be started (%s); the agent was not woken' % e.__class__.__name__}
    out = {'ok': r.returncode == 0, 'exit': r.returncode, 'seconds': round(time.monotonic() - t0, 3),
           'stdout_bytes': len(r.stdout or b''), 'stderr_bytes': len(r.stderr or b'')}
    last = [x for x in (r.stdout or b'').splitlines() if x.strip()][-1:] or [b'']
    try:
        v = json.loads(last[0].decode('utf-8', 'replace')) if last[0] else None
    except ValueError:
        v = None
    n = v.get('cost_tokens') if isinstance(v, dict) else None
    if isinstance(n, int) and not isinstance(n, bool) and n >= 0:
        out['cost_tokens'] = n
    out['said'] = 'the agent was woken' if out['ok'] else 'the wake command ended with exit %d' % r.returncode
    return out


def _body_line(home_dir, agent, person, state, reason, t, host, cost=None, seconds=None):
    body = {'name': 'heartbeat', 'state': state, 'task': reason, 'host': host, 'review_min': 0}
    if cost is not None:
        body['cost_tokens'] = cost
    if seconds is not None:
        body['seconds'] = seconds
    try:
        res = record.append(home_dir, agent, person, 'body', body, reason='delegated', ts=_iso(t))
    except (OSError, ValueError) as e:
        return None, 'the %s body line could not be written (%s)' % (state, e)
    return res['line']['id'], ''


# ---------------------------------------------------------------- one beat

def _empty(as_of, dry):
    return {'as_of': as_of, 'dry': bool(dry), 'person': None, 'agent': None, 'pull': None,
            'receipts': {'written': 0, 'held': 0, 'ran': False}, 'signals': [], 'emergency': [],
            'gate': None, 'handed': [], 'woke': False, 'reason': None, 'ids': [], 'wake': None,
            'recorded': [], 'next_wake': None, 'cost': {'requests': 0, 'seconds': 0.0, 'bytes': 0}, 'said': []}


def beat(home_dir, now=None, forge=None, opener=None, wake=None, dry=False):
    """One beat: pull, Receipts, signals, the gate, a wake when one is owed, the record of it.
    Deterministic given `now` and the injected `forge`, `opener` and `wake`; never sleeps; never raises."""
    t = _clock(now)
    rep = _empty(_iso(t), dry)
    if t is None:
        rep['said'].append('the time given (%s) is not a time, so nothing was done' % repr(now)[:40])
        return rep
    why = _home_ok(home_dir)
    if why:
        rep['said'].append(why)
        return rep
    fd, why = _lock(home_dir)
    if why:
        rep['said'].append(why)
        return rep
    token = [_s(forge.get('token')) if isinstance(forge, dict) else '']
    try:
        _beat(home_dir, t, forge, opener, wake, bool(dry), rep, token)
    except Exception as e:  # noqa: BLE001 (a beat reports in words, never an exception)
        rep['said'].append('the beat stopped (%s: %s); nothing more was done this beat'
                           % (e.__class__.__name__, str(e)[:200]))
    finally:
        _unlock(fd)
    if token[0]:
        rep['said'] = [x.replace(token[0], '[token]') for x in rep['said']]
    return rep


def _beat(home_dir, t, forge, opener, wake, dry, rep, token):  # noqa: C901 (the beat's order is its contract)
    cfg, holon_keeper = _config(home_dir)
    if forge is None:
        forge = _forge_from(cfg)
        token[0] = forge['token'] if forge else ''
    st = _load_state(home_dir)
    seed = 'seen' not in st

    # 1. pull
    p = pull.tick(home_dir, now=_iso(t), forge=forge, opener=opener, dry=dry)
    rep['pull'] = p
    for k in ('requests', 'bytes'):
        rep['cost'][k] += int(((p.get('cost') or {}).get(k)) or 0)
    rep['cost']['seconds'] += float(((p.get('cost') or {}).get('seconds')) or 0.0)

    # who
    h = record.read(home_dir)
    keeper = _s(h.get('keeper')) or holon_keeper
    person, agent, said = _people(h['lines'], _s(h.get('holon')), keeper, cfg)
    rep['person'], rep['agent'] = person or None, agent or None
    if said:
        rep['said'].append(said)
    key = _key(h, p)
    arrived = sum(int(v or 0) for v in (p.get('new_lines') or {}).values())
    changed = seed or arrived > 0 or bool(p.get('rose')) or st.get('key') != key
    day = t.date().isoformat()

    # 2. receipts
    if person and agent and changed:
        r = receipt.on_arrival(home_dir, agent, person, how='pull', now=_iso(t), dry=dry)
        rep['receipts'] = {'written': len(r.get('written') or []), 'held': len(r.get('held') or []), 'ran': True,
                           'said': [x.get('why') for x in (r.get('held') or [])[:5] if isinstance(x, dict)]}
    elif person and agent:
        rep['receipts']['said'] = ['nothing is new since the last beat, so no Receipt is owed']

    # 3. signals
    folded, lines, sched = None, h['lines'], None
    seen, negatives = _strs(st.get('seen')), _strs(st.get('negatives'))
    if person and (changed or st.get('schedule_on') != day):
        folded, lines, sched, why = _reading(home_dir, t)
        lines = lines or h['lines']
        if why:
            rep['said'].append(why)
    agents = [agent] if agent else []
    if folded is not None:
        sigs, seen, negatives = _signals(_s(h.get('holon')), person, agents, folded, lines, sched, p.get('rose'), p,
                                         seen, set(negatives), seed)
    else:
        sigs, _, _ = _signals(_s(h.get('holon')), person, agents, {}, h['lines'], None, p.get('rose'), p,
                              seen, set(negatives), True)
    failing = sorted(x['id'] for x in sigs if x['id'].startswith('fault:pull:'))
    was = set(_strs(st.get('faults')))
    sigs = [x for x in sigs if x['id'] not in was]          # a cell that still cannot be pulled is said once
    rep['signals'] = sigs
    home_lines = h['lines']
    budget = attention.budget(home_lines, person, t) if person else dict(attention.DEFAULTS)
    nxt = attention.next_sitting(budget, t)
    ring = []
    if person:
        if sigs:
            rule = emergency.rule(home_lines, person)
            rows = _weigh(sigs, rule, folded, lines, person, _s(h.get('holon')), t, nxt)
            rep['emergency'] = rows
            ring = sorted(r['id'] for r in rows if r['ring'])
        cards = [{'id': s['id'], 'needs_person': True, 'by': s.get('by')} for s in sigs]
        g = attention.gate(cards, budget, _iso(t), attention.asks_from(home_lines, person, agents or None),
                           wake=ring)
        rep['gate'] = {k: g.get(k) for k in ('interrupt', 'withheld', 'next_sitting', 'next_slot', 'quiet_now',
                                             'woken')}
        rep['handed'] = list(g.get('interrupt') or [])

    # 4. wake
    rose = sorted(set(p.get('rose') or []))
    emerg = sorted(r['id'] for r in rep['emergency'] if r['wake'])
    every = _seconds(cfg.get('wake_every')) or WAKE_EVERY
    mark = _ts(st.get('cadence_mark'))
    cadence_due, cadence_why = False, ''
    if mark is None:
        mark = t
        cadence_why = 'the cadence starts at this beat'
    else:
        sat = _prev_sitting(budget, t)
        if (t - mark).total_seconds() >= every:
            cadence_due, cadence_why = True, 'the agent\'s own cadence (%d seconds) came round' % every
        elif sat is not None and sat > mark:
            cadence_due, cadence_why = True, 'the person\'s sitting at %s came round' % sat.strftime('%H:%M')
    reason = 'request' if rose else 'emergency' if emerg else 'cadence' if cadence_due else None
    ids = sorted(set(rose) | set(emerg)) if reason in ('request', 'emergency') else []
    wakes = [dict(w, ids=_strs(w.get('ids'))) for w in (st.get('wakes') if isinstance(st.get('wakes'), list) else [])
             if isinstance(w, dict) and _ts(w.get('at')) and isinstance(w.get('reason'), str)]
    if reason:
        recent = [w for w in wakes if w.get('reason') == reason and w.get('ids') == ids
                  and (t - _ts(w['at'])).total_seconds() < WAKE_GAP_S]
        if recent:
            rep['said'].append('the agent was woken for the same %s within %d seconds; not again' % (reason, WAKE_GAP_S))
            reason = None
    if (reason == 'cadence' or mark == t) and cadence_why:
        rep['said'].append(cadence_why)
    rep['reason'], rep['ids'] = reason, ids
    if reason:
        brief = {'reason': reason, 'ids': ids, 'as_of': _iso(t),
                 'budget': {'interrupt': rep['handed'], 'next_sitting': (rep['gate'] or {}).get('next_sitting')
                            or _iso(nxt), 'next_slot': (rep['gate'] or {}).get('next_slot'),
                            'fewer': budget.get('fewer'), 'quiet_now': attention.quiet_now(budget, t)[0]}}
        argv, why = (None, '') if callable(wake) else _wake_command(cfg)
        if dry:
            rep['said'].append('dry: the agent would be woken (%s); nothing ran and nothing was written' % reason)
        elif not callable(wake) and argv is None:
            rep['said'].append(why)
            rep['wake'] = {'ran': False, 'said': why}
        else:
            host = _s(cfg.get('host')) or platform.node() or None
            try:
                if callable(wake):
                    res = wake(reason, brief)
                else:
                    tmo = _seconds(cfg.get('wake_timeout_s')) or WAKE_TIMEOUT_S
                    res = _wake_default(home_dir, argv, brief, tmo, env=_wake_env(cfg, token[0]))
            except Exception as e:  # noqa: BLE001 (a wake that fails is said; the next beat still runs)
                res = {'ok': False, 'said': 'the wake failed (%s: %s)' % (e.__class__.__name__, str(e)[:120])}
            res = res if isinstance(res, dict) else {}
            started = res.get('started') is not False
            cost = res.get('cost_tokens')
            cost = cost if isinstance(cost, int) and not isinstance(cost, bool) and cost >= 0 else None
            sec = res.get('seconds')
            sec = float(sec) if isinstance(sec, (int, float)) and not isinstance(sec, bool) and math.isfinite(sec) \
                and sec >= 0 else None
            if sec is not None:
                rep['cost']['seconds'] += sec
            rep['wake'] = {'ran': started, 'ok': started and res.get('ok') is not False, 'cost_tokens': cost,
                           'seconds': sec, 'said': _s(res.get('said')) or None}
            if res.get('ok') is False and res.get('said'):
                rep['said'].append(_s(res['said'])[:240])
            if started:
                # both body lines are written once the wake has run, so a wake that never started leaves none;
                # the done line is dated by the whole seconds the wake ran (at least one), so it reads after
                # its working line in every order by time
                if agent:
                    whole = int(round(sec)) if sec is not None else None
                    ends = t + dt.timedelta(seconds=max(1, int(math.ceil(sec)) if sec is not None else 1))
                    for state, at_ in (('working', t), ('done', ends)):
                        lid, w = _body_line(home_dir, agent, person, state, reason, at_, host,
                                            cost if state == 'done' else None, whole if state == 'done' else None)
                        if lid:
                            rep['recorded'].append(lid)
                        else:
                            rep['said'].append(w)
                else:
                    rep['said'].append('no agent is affirmed, so no body line was written for this wake')
                rep['woke'] = True
                wakes.append({'at': _iso(t), 'reason': reason, 'ids': ids})
                mark = t
    nm = mark + dt.timedelta(seconds=every)
    sat_next = nxt if nxt is not None and nxt > mark else None
    rep['next_wake'] = _iso(min(x for x in (nm, sat_next) if x is not None))
    rep['cost']['seconds'] = round(rep['cost']['seconds'], 3)
    if rep['emergency'] and not rep['handed']:
        rep['said'].append('nothing may interrupt the person now; what came waits for their next sitting')

    # 6. record
    if dry:
        rep['said'].append('dry: nothing was kept')
        return
    h2 = record.read(home_dir)
    st.update({'key': _key(h2, p), 'cadence_mark': _iso(mark), 'last_beat': _iso(t), 'faults': failing,
               'wakes': [w for w in wakes if (t - _ts(w['at'])).total_seconds() < 86400][-WAKES_KEPT:]})
    if folded is not None:              # what stands is learned only from a reading of it
        st.update({'seen': seen, 'negatives': negatives, 'schedule_on': day})
    else:                               # what was kept is kept as lists of strings, else forgotten
        st.update({k: v for k, v in (('seen', seen), ('negatives', negatives)) if k in st})
    w = _save_state(home_dir, st)
    if w:
        rep['said'].append(w)
    w = _log(home_dir, {'as_of': _iso(t), 'pulled': arrived, 'receipts': rep['receipts']['written'],
                        'signals': len(sigs), 'woke': rep['woke'], 'reason': rep['reason'],
                        'ok': (rep['wake'] or {}).get('ok') if rep['wake'] else None,
                        'cost': dict(rep['cost'])})
    if w:
        rep['said'].append(w)


# ---------------------------------------------------------------- the loop

def every(home_dir, now=None, every_s=None):
    """The loop's cadence: `every_s` given, else holon.json `heartbeat.every_s`, else EVERY_S; a
    Subscription with a shorter cadence sets it to that cadence; never below MIN_EVERY_S."""
    said = []
    given = _seconds(every_s)
    if given:
        n, basis = given, 'given'
    else:
        cfg = _config(home_dir)[0] if not _home_ok(home_dir) else {}
        n, basis = (_seconds(cfg.get('every_s')), 'holon.json') if _seconds(cfg.get('every_s')) else (EVERY_S, 'default')
        if not _home_ok(home_dir):
            try:
                cads = [c['cadence'] for c in pull.due(home_dir, now)['cells'] if _seconds(c.get('cadence'))]
            except Exception:  # noqa: BLE001
                cads = []
            if cads and min(cads) < n:
                n, basis = min(cads), 'subscription'
    if n < MIN_EVERY_S:
        said.append('%d seconds is faster than the loop runs; it beats every %d seconds' % (n, MIN_EVERY_S))
        n = MIN_EVERY_S
    return {'every_s': n, 'basis': basis, 'said': said}


def run(home_dir, every_s=None, beats=None, forge=None, opener=None, wake=None, dry=False, clock=None,
        sleep=time.sleep, beat_fn=None):
    """The loop: beat, then sleep the loop's cadence; `beats=None` runs until SIGTERM or SIGINT.
    Every exception of a beat is logged in words and the next beat runs. `clock` (a callable giving
    an ISO time) and `sleep` are for tests; `beat_fn` stands in for beat."""
    beat_fn = beat_fn or beat
    stop = {'now': False}

    def _stop(signum, frame):  # noqa: ARG001
        stop['now'] = True
    old = {}
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            old[sig] = signal.signal(sig, _stop)
        except (ValueError, OSError):  # not the main thread: the caller stops it by `beats`
            pass
    out = {'beats': 0, 'errors': 0, 'every_s': None, 'stopped': None, 'said': []}
    n = None
    if beats is not None:
        n = beats if isinstance(beats, int) and not isinstance(beats, bool) else None
        if n is None or n <= 0:
            out['stopped'] = 'beats'
            out['said'].append('a count of %s beats nothing; give a whole number of beats, or none to run until '
                               'stopped' % repr(beats)[:40])
            for sig, h in old.items():
                try:
                    signal.signal(sig, h)
                except (ValueError, OSError):
                    pass
            return out
    try:
        while not stop['now'] and (n is None or out['beats'] < n):
            now = clock() if callable(clock) else None
            gap = every(home_dir, now, every_s)['every_s']
            out['every_s'] = gap
            try:
                beat_fn(home_dir, now=now, forge=forge, opener=opener, wake=wake, dry=dry)
            except Exception as e:  # noqa: BLE001 (logged in words; the loop goes on)
                out['errors'] += 1
                words = 'the beat raised %s: %s; the next beat runs' % (e.__class__.__name__, str(e)[:200])
                sys.stderr.write('heartbeat: %s\n' % words)
                if not dry and not _home_ok(home_dir):
                    _log(home_dir, {'as_of': _iso(_clock(now)), 'error': words})
            out['beats'] += 1
            if n is not None and out['beats'] >= n:
                break
            left = float(gap)
            while left > 0 and not stop['now']:
                step = min(1.0, left)
                sleep(step)
                left -= step
        out['stopped'] = 'signal' if stop['now'] else 'beats'
    finally:
        for sig, h in old.items():
            try:
                signal.signal(sig, h)
            except (ValueError, OSError):
                pass
    return out


# ---------------------------------------------------------------- install (writes files; installs nothing)

def _xml(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _systemd(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')


def _sh(s):
    return "'%s'" % s.replace("'", "'\\''")


def _cron(gap):
    """(schedule, said): cron's own steps nearest the gap, never shorter. cron counts minutes within the
    hour and hours within the day (crontab(5)), so a step that does not divide them restarts at each."""
    if gap <= 60:
        return '* * * * *', 'cron beats at most once a minute.'
    if gap <= 3540:
        m = int(math.ceil(gap / 60.0))
        return '*/%d * * * *' % m, 'cron beats every %d minutes, counted within each hour.' % m
    h = int(math.ceil(gap / 3600.0))
    if h < 24:
        return '0 %s * * *' % ('*' if h == 1 else '*/%d' % h), \
            'cron beats every %d hour(s), counted within each day.' % h
    return '0 0 * * *', 'cron beats at most once a day here; %d seconds is longer than its steps.' % gap


def install(home_dir, kind='launchd', out_dir=None, python=sys.executable):
    """Render the service files for one host's scheduler into `out_dir` (default <home>/heartbeat/), and
    say the commands the person runs by their own hand. Installs nothing."""
    out = {'files': [], 'said': []}
    why = _home_ok(home_dir)
    if why:
        out['said'].append(why)
        return out
    if kind not in KINDS:
        out['said'].append('the kind is one of %s; nothing was written' % ', '.join(KINDS))
        return out
    if not isinstance(python, str) or not python or '\n' in python:
        out['said'].append('no python to run the heartbeat with was given; nothing was written')
        return out
    home = os.path.abspath(home_dir)
    hid = _s(record.holon_info(home).get('id'))[:12] or 'home'
    label = 'lionsberg.heartbeat.%s' % ''.join(c for c in hid if c.isalnum())
    gap = every(home)['every_s']
    od = os.path.abspath(out_dir) if isinstance(out_dir, str) and out_dir else os.path.join(home, 'heartbeat')
    if os.path.islink(od):
        out['said'].append('the folder for the service files is a link; nothing was written through it')
        return out
    script = os.path.join(HERE, 'heartbeat.py')
    cron, cron_said = _cron(gap)
    vals = {'LABEL': label, 'EVERY_S': str(gap), 'CRON_SCHEDULE': cron,
            'PYTHON_XML': _xml(python), 'SCRIPT_XML': _xml(script), 'HOME_XML': _xml(home),
            'PYTHON_SD': _systemd(python), 'SCRIPT_SD': _systemd(script), 'HOME_SD': _systemd(home),
            'PYTHON_SH': _sh(python), 'SCRIPT_SH': _sh(script), 'HOME_SH': _sh(home)}
    try:
        os.makedirs(od, exist_ok=True)
    except OSError as e:
        out['said'].append('the folder for the service files cannot be made at %s (%s); nothing was written'
                           % (od[:200], e.__class__.__name__))
        return out
    for tpl, name in TEMPLATES[kind]:
        try:
            with open(os.path.join(TEMPLATE_DIR, tpl), encoding='utf-8') as f:
                text = f.read()
        except OSError:
            out['said'].append('the template %s is missing beside heartbeat.py; nothing was written' % tpl)
            return out
        for k, v in vals.items():
            text = text.replace('{{%s}}' % k, v)
        path = os.path.join(od, name.format(label=label))
        if os.path.islink(path):
            out['said'].append('%s is a link; it was not written' % path)
            continue
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o644)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(text)
        except OSError as e:
            out['said'].append('%s could not be written (%s)' % (path[:200], e.__class__.__name__))
            continue
        out['files'].append(path)
    f0 = out['files'][0] if out['files'] else ''
    if kind == 'launchd':
        out['said'] += ['The files are written; nothing is installed. To put the heartbeat on this Mac, run by your own hand:',
                        'cp %s ~/Library/LaunchAgents/' % _sh(f0),
                        'launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/%s.plist' % label,
                        'To stop it: launchctl bootout gui/$(id -u)/%s' % label]
    elif kind == 'systemd':
        out['said'] += ['The files are written; nothing is installed. To put the heartbeat on this host, run by your own hand:',
                        'mkdir -p ~/.config/systemd/user && cp %s ~/.config/systemd/user/' % ' '.join(_sh(x) for x in out['files']),
                        'systemctl --user daemon-reload && systemctl --user enable --now %s.timer' % label,
                        'To stop it: systemctl --user disable --now %s.timer' % label]
    else:
        out['said'] += ['The file is written; nothing is installed. %s Run by your own hand:' % cron_said,
                        '(crontab -l 2>/dev/null; cat %s) | crontab -' % _sh(f0),
                        'To stop it: crontab -e, and remove the line that names %s' % label]
    out['said'].append('The heartbeat beats every %d seconds; it spends no model tokens; a wake runs only on a request, '
                       'an emergency or a cadence.' % gap)
    return out


# ---------------------------------------------------------------- status

def _log_tail(home_dir):
    path = os.path.join(home_dir, LOG_NAME)
    if os.path.islink(path):
        return [], 'the beat log is a link, so it is not read'
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return [], 'the heartbeat has not beaten here yet'
    except OSError as e:
        return [], 'the beat log cannot be opened (%s)' % e.__class__.__name__
    with os.fdopen(fd, 'rb') as f:
        size = os.fstat(f.fileno()).st_size
        f.seek(max(0, size - MAX_LOG_READ))
        raw = f.read()
    if size > MAX_LOG_READ:
        raw = raw[raw.find(b'\n') + 1:]
    rows = []
    for x in raw.splitlines():
        try:
            v = json.loads(x.decode('utf-8', 'replace'))
        except ValueError:
            continue
        if isinstance(v, dict) and _ts(v.get('as_of')):
            rows.append(v)
    return rows, ''


def status(home_dir, now=None):
    """What the heartbeat has done, from its log and `.heartbeat.json`: reads files only."""
    t = _clock(now)
    out = {'last_beat': None, 'last_wake': None, 'beats_today': 0, 'wakes_today': 0,
           'cost_today': {'requests': 0, 'seconds': 0.0, 'bytes': 0}, 'next_due': {'wake': None, 'pull': None},
           'errors_today': 0, 'said': []}
    why = _home_ok(home_dir)
    if why or t is None:
        out['said'].append(why or 'the time given is not a time')
        return out
    rows, why = _log_tail(home_dir)
    if why:
        out['said'].append(why)
    day = t.date()
    for r in rows:
        at = _ts(r['as_of'])
        today = at.astimezone(t.tzinfo).date() == day
        if 'error' in r:
            out['errors_today'] += 1 if today else 0
            continue
        out['last_beat'] = r['as_of'] if not out['last_beat'] or at > _ts(out['last_beat']) else out['last_beat']
        if r.get('woke') is True and (not out['last_wake'] or at > _ts(out['last_wake'])):
            out['last_wake'] = r['as_of']
        if today:
            out['beats_today'] += 1
            out['wakes_today'] += 1 if r.get('woke') is True else 0
            c = r.get('cost') if isinstance(r.get('cost'), dict) else {}
            for k in ('requests', 'bytes'):
                v = c.get(k)
                out['cost_today'][k] += v if isinstance(v, int) and not isinstance(v, bool) else 0
            v = c.get('seconds')
            out['cost_today']['seconds'] += float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
    out['cost_today']['seconds'] = round(out['cost_today']['seconds'], 3)
    st = _load_state(home_dir)
    cfg, _ = _config(home_dir)
    mark = _ts(st.get('cadence_mark'))
    if mark:
        out['next_due']['wake'] = _iso(mark + dt.timedelta(seconds=_seconds(cfg.get('wake_every')) or WAKE_EVERY))
    try:
        d = [_ts(c.get('next_due')) for c in pull.due(home_dir, _iso(t))['cells']]
        d = [x for x in d if x]
        out['next_due']['pull'] = _iso(min(d)) if d else None
    except Exception:  # noqa: BLE001
        pass
    if out['last_beat']:
        out['said'].append('the last beat was at %s; %d beat(s) and %d wake(s) today'
                           % (out['last_beat'], out['beats_today'], out['wakes_today']))
    return out


# ---------------------------------------------------------------- command line

def main(argv=None):
    ap = argparse.ArgumentParser(prog='heartbeat.py', description='The heartbeat: one always-on process per holon. '
                                 'Pulls, receipts, reads the signals and wakes the agent only when owed. Calls no model.')
    sp = ap.add_subparsers(dest='cmd')
    b = sp.add_parser('beat', help='one beat')
    b.add_argument('home')
    b.add_argument('--now', default=None)
    b.add_argument('--dry', action='store_true', help='ask and decide; fetch, wake and keep nothing')
    r = sp.add_parser('run', help='beat, and sleep the loop\'s cadence, until stopped')
    r.add_argument('home')
    r.add_argument('--every', type=float, default=None)
    r.add_argument('--beats', type=int, default=None)
    i = sp.add_parser('install', help='write the service files; install nothing')
    i.add_argument('home')
    i.add_argument('--kind', required=True, choices=KINDS)
    i.add_argument('--out', default=None)
    s = sp.add_parser('status', help='what the heartbeat has done')
    s.add_argument('home')
    s.add_argument('--now', default=None)
    ns = ap.parse_args(argv)
    if not ns.cmd:
        ap.print_help()
        return 2
    if ns.cmd == 'beat':
        res = beat(ns.home, now=ns.now, dry=ns.dry)
    elif ns.cmd == 'run':
        res = run(ns.home, every_s=ns.every, beats=ns.beats)
    elif ns.cmd == 'install':
        res = install(ns.home, ns.kind, ns.out)
    else:
        res = status(ns.home, ns.now)
    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=str) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
