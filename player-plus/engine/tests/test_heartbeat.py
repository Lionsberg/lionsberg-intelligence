"""test_heartbeat.py — the heartbeat's laws, each checked: a beat is deterministic and never sleeps; the
agent wakes on a risen request, an emergency or a cadence and not otherwise, never twice within the
gap; with no wake command nothing runs; a beat writes only what it may; install installs nothing;
the loop survives a failing beat, stops when told, and never runs faster than twenty seconds.

Real temporary git repositories stand for the forge where a cell is needed (a bare repository per
cell under a folder that `https://forge.test/` is rewritten to); a fake wake stands for the agent.
Nothing here reaches a network, starts a service or calls a model.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_heartbeat.py -v
"""
import ast
import datetime as dt
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import types
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import bodies     # noqa: E402
import heartbeat  # noqa: E402
import holon      # noqa: E402
import pull       # noqa: E402
import record     # noqa: E402

GIT = shutil.which('git')
PERSON, OTHER, AIDE, STEWARD = 'person:player', 'person:other', 'agent:aide', 'person:steward'
T0 = '2026-10-31T09:00:00-07:00'
WORK = None
SAVED_ENV = {}
ENV_KEYS = ('LIONSBERG_KEY_DIR', 'LIONSBERG_SIGCACHE_KEY', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM')
DERIVED = {'.heartbeat.json', '.heartbeat-log.jsonl', '.pulled.json', '.pull-log.jsonl', '.sigcache'}


def at(seconds):
    return (dt.datetime.fromisoformat(T0) + dt.timedelta(seconds=seconds)).isoformat(timespec='seconds')


def setUpModule():
    global WORK
    WORK = tempfile.mkdtemp(prefix='lionsberg-heartbeat-')
    for k in ENV_KEYS:
        SAVED_ENV[k] = os.environ.get(k)
    os.makedirs(os.path.join(WORK, 'keys'))
    os.makedirs(os.path.join(WORK, 'forge', 'owner'))
    cfg = os.path.join(WORK, 'gitconfig')
    with open(cfg, 'w', encoding='utf-8') as f:
        f.write('[user]\n\tname = test\n\temail = test@localhost\n[init]\n\tdefaultBranch = main\n'
                '[url "file://%s/forge/"]\n\tinsteadOf = https://forge.test/\n' % WORK)
    os.environ.update({'LIONSBERG_KEY_DIR': os.path.join(WORK, 'keys'),
                       'LIONSBERG_SIGCACHE_KEY': os.path.join(WORK, 'sigcache.key'),
                       'GIT_CONFIG_GLOBAL': cfg, 'GIT_CONFIG_NOSYSTEM': '1'})
    for who in (STEWARD, OTHER):
        record.make_key(who, os.path.join(WORK, 'keys'))


def tearDownModule():
    for k, v in SAVED_ENV.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def git(d, *args):
    r = subprocess.run([GIT, '-C', d] + list(args), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError('git %s: %s' % (' '.join(args), r.stderr))
    return r.stdout.strip()


def make_home(d, agent=True, cfg=None):
    """A person's home, its keeper's affirmed agent, and a delegation covering receive and body."""
    holon.init(d, 'home', 'person', PERSON, sign=False, ts=T0, salt='h')
    if agent:
        record.append(d, PERSON, PERSON, 'affirm', {'agent': AIDE}, sign=False, ts=T0, salt='a')
        record.append(d, PERSON, PERSON, 'delegate', {'to': AIDE, 'scope': ['receive', 'body'], 'holons': ['*']},
                      sign=False, ts=T0, salt='d')
    if cfg is not None:
        p = os.path.join(d, 'holon.json')
        with open(p, encoding='utf-8') as f:
            hj = json.load(f)
        hj['heartbeat'] = cfg
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(hj, f)
    return d


class FakeWake:
    def __init__(self, result=None, raises=None):
        self.calls, self.result, self.raises = [], result, raises

    def __call__(self, reason, context):
        self.calls.append((reason, context))
        if self.raises:
            raise self.raises
        return self.result if self.result is not None else {'ok': True, 'cost_tokens': 42}


def snapshot(d):
    out = {}
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x != '.git']
        for n in files:
            p = os.path.join(root, n)
            with open(p, 'rb') as f:
                out[os.path.relpath(p, d)] = hashlib.sha256(f.read()).hexdigest()
    return out


def comparable(rep):
    """A report without what is measured or salted: seconds, and the ids of the body lines (fresh salts)."""
    r = json.loads(json.dumps(rep, sort_keys=True))
    r['cost'].pop('seconds', None)
    r['pull']['cost'].pop('seconds', None)
    r['recorded'] = len(r['recorded'])
    return json.dumps(r, sort_keys=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.home = make_home(os.path.join(self.tmp, 'home'))

    def body_lines(self, home=None):
        path = os.path.join(home or self.home, 'record', record.actor_file(AIDE))
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            return [json.loads(x) for x in f if x.strip() and json.loads(x).get('type') == 'body']

    def log(self, home=None):
        path = os.path.join(home or self.home, heartbeat.LOG_NAME)
        with open(path, encoding='utf-8') as f:
            return [json.loads(x) for x in f if x.strip()]


# ---------------------------------------------------------------- law 1: deterministic, no sleep

class TestDeterministic(Base):
    def test_same_now_same_report_and_no_sleep(self):
        other = make_home(os.path.join(self.tmp, 'other'))
        held = (heartbeat.time.sleep, pull.time.sleep)

        def no_sleep(*a):
            raise AssertionError('a beat never sleeps')
        heartbeat.time.sleep = pull.time.sleep = no_sleep
        try:
            reps = []
            for h in (self.home, other):
                w = FakeWake()
                heartbeat.beat(h, now=at(0), wake=w)
                reps.append(heartbeat.beat(h, now=at(3600), wake=w))
        finally:
            heartbeat.time.sleep, pull.time.sleep = held
        self.assertEqual(comparable(reps[0]), comparable(reps[1]))
        self.assertEqual(reps[0]['as_of'], at(3600))
        self.assertTrue(reps[0]['woke'])
        json.dumps(reps[0], sort_keys=True)                     # JSON-ready

    def test_the_clock_is_read_only_when_no_time_is_given(self):
        self.assertEqual(heartbeat._clock(at(5)).isoformat(), at(5))
        self.assertIsNone(heartbeat._clock('not a time'))
        r = heartbeat.beat(self.home, now='not a time')
        self.assertFalse(r['woke'])
        self.assertTrue(any('not a time' in s for s in r['said']))


# ---------------------------------------------------------------- law 2: when the agent wakes

class TestCadence(Base):
    def test_cadence_wakes_and_not_otherwise(self):
        w = FakeWake()
        r0 = heartbeat.beat(self.home, now=at(0), wake=w)
        self.assertFalse(r0['woke'])                            # the cadence starts; nothing is owed yet
        self.assertTrue(any('starts' in s for s in r0['said']))
        self.assertFalse(heartbeat.beat(self.home, now=at(1800), wake=w)['woke'])
        r = heartbeat.beat(self.home, now=at(3600), wake=w)
        self.assertTrue(r['woke'])
        self.assertEqual(r['reason'], 'cadence')
        self.assertFalse(heartbeat.beat(self.home, now=at(3700), wake=w)['woke'])   # the cadence starts again
        self.assertEqual(len(w.calls), 1)

    def test_the_wake_every_of_holon_json(self):
        h = make_home(os.path.join(self.tmp, 'h2'), cfg={'wake_every': 600})
        w = FakeWake()
        heartbeat.beat(h, now=at(0), wake=w)
        self.assertTrue(heartbeat.beat(h, now=at(600), wake=w)['woke'])

    def test_a_sitting_of_the_person_wakes_the_agent(self):
        # T0 is 09:00; the default sitting is 08:00 the next day; the agent's own cadence is two days here
        h = make_home(os.path.join(self.tmp, 'sits'), cfg={'wake_every': 172800})
        w = FakeWake()
        heartbeat.beat(h, now=at(0), wake=w)
        self.assertFalse(heartbeat.beat(h, now=at(3600), wake=w)['woke'])
        self.assertFalse(heartbeat.beat(h, now=at(23 * 3600 - 10), wake=w)['woke'])   # 07:59:50
        r = heartbeat.beat(h, now=at(23 * 3600 + 10), wake=w)      # past 08:00, the sitting came round
        self.assertTrue(r['woke'])
        self.assertTrue(any('sitting' in s for s in r['said']))

    def test_never_twice_within_the_gap(self):
        w = FakeWake()
        heartbeat.beat(self.home, now=at(0), wake=w)
        st = heartbeat._load_state(self.home)
        st['cadence_mark'] = at(-7200)
        st['wakes'] = [{'at': at(-100), 'reason': 'cadence', 'ids': []}]
        heartbeat._save_state(self.home, st)
        r = heartbeat.beat(self.home, now=at(60), wake=w)
        self.assertFalse(r['woke'])
        self.assertTrue(any('within %d seconds' % heartbeat.WAKE_GAP_S in s for s in r['said']))
        self.assertTrue(heartbeat.beat(self.home, now=at(60 + heartbeat.WAKE_GAP_S), wake=w)['woke'])

    def test_a_failing_wake_is_said_and_still_recorded(self):
        w = FakeWake(raises=RuntimeError('the agent fell over'))
        heartbeat.beat(self.home, now=at(0), wake=w)
        r = heartbeat.beat(self.home, now=at(3600), wake=w)
        self.assertTrue(any('the wake failed' in s for s in r['said']))
        self.assertEqual([b['body']['state'] for b in self.body_lines()], ['working', 'done'])
        r2 = heartbeat.beat(self.home, now=at(3660), wake=FakeWake())
        self.assertFalse(r2['woke'])                            # a failed wake still counts against the cadence


@unittest.skipUnless(GIT, 'git is needed: the cell is a real repository')
class TestSignals(Base):
    def setUp(self):
        super().setUp()
        tag = os.path.basename(self.tmp)
        src = os.path.join(self.tmp, 'src')
        holon.init(src, 'cella', 'cell', STEWARD, sign=None, ts=T0, salt=tag)
        holon.admit(src, STEWARD, OTHER, record.pubkey_of(record.find_key(None, OTHER)), ts=at(1), salt='adm')
        git(src, 'init', '-q', '-b', 'main')
        git(src, 'add', '-A')
        git(src, 'commit', '-q', '-m', 'inception')
        bare = os.path.join(WORK, 'forge', 'owner', tag + '.git')
        subprocess.run([GIT, 'clone', '-q', '--bare', src, bare], check=True, capture_output=True)
        url = 'https://forge.test/owner/%s.git' % tag
        res = holon.join(self.home, url, 'cella', ts=T0, salt='jc')
        self.assertTrue(res['ok'], res['said'])
        self.writer = os.path.join(self.tmp, 'writer')
        subprocess.run([GIT, 'clone', '-q', url, self.writer], check=True, capture_output=True)

    def upstream(self, typ, body, base):
        r = record.append(self.writer, OTHER, OTHER, typ, body, sign=None, ts=at(base), salt='u%s%d' % (typ, base))
        git(self.writer, 'add', '-A')
        git(self.writer, 'commit', '-q', '-m', typ)
        git(self.writer, 'push', '-q', 'origin', 'HEAD')
        return r['line']['id']

    def test_a_risen_request_and_a_pain_wake_the_agent(self):
        w = FakeWake()
        r0 = heartbeat.beat(self.home, now=at(10), wake=w)
        self.assertFalse(r0['woke'])
        rq = self.upstream('request', {'to': PERSON, 'title': 'a look at the draft'}, 20)
        pain = self.upstream('sight', {'kind': 'pain', 'where': 'the north gate', 'text': 'help wanted'}, 21)
        r = heartbeat.beat(self.home, now=at(400), wake=w)
        self.assertEqual(r['pull']['rose'], [rq])
        self.assertTrue(r['woke'])
        self.assertEqual(r['reason'], 'request')
        self.assertEqual(r['ids'], sorted([rq, pain]))
        kinds = {s['id']: s['kind'] for s in r['signals']}
        self.assertEqual(kinds[pain], 'sight')
        row = {x['id']: x for x in r['emergency']}
        self.assertTrue(row[pain]['wake'] and row[pain]['ring'])  # a member's pain: the rule wakes, Andon rings
        self.assertFalse(row[rq]['wake'])                         # the default rule lets a request wait
        self.assertIn(pain, r['handed'])
        self.assertGreaterEqual(r['receipts']['written'], 1)      # the request has its Receipt, waiting at home
        reason, ctx = w.calls[-1]
        self.assertEqual(sorted(ctx), ['as_of', 'budget', 'ids', 'reason'])
        self.assertIn(pain, ctx['budget']['interrupt'])
        r2 = heartbeat.beat(self.home, now=at(460), wake=w)
        self.assertFalse(r2['woke'])                              # nothing new: no second wake
        self.assertEqual(r2['signals'], [])

    def test_a_cell_that_cannot_be_pulled_is_a_fault_said_once(self):
        heartbeat.beat(self.home, now=at(0), wake=FakeWake())
        shutil.rmtree(os.path.join(self.home, 'cells', 'cella', '.git'))
        r = heartbeat.beat(self.home, now=at(400), wake=FakeWake())
        self.assertEqual([x['id'] for x in r['signals']], ['fault:pull:cella'])
        self.assertFalse(r['emergency'][0]['wake'])               # the default rule lets a fault wait
        self.assertFalse(r['woke'])
        self.assertEqual(heartbeat.beat(self.home, now=at(800), wake=FakeWake())['signals'], [])

    def test_the_first_beat_learns_what_stands(self):
        self.upstream('sight', {'kind': 'pain', 'where': 'the north gate', 'text': 'old'}, 5)
        w = FakeWake()
        heartbeat.beat(self.home, now=at(0), wake=w)          # the first pull brings the old pain in
        st = heartbeat._load_state(self.home)
        self.assertTrue(st.get('seen'))
        self.assertFalse(w.calls)


# ---------------------------------------------------------------- law 3: the wake command

class TestWakeCommand(Base):
    def test_no_command_runs_nothing_and_says_so(self):
        heartbeat.beat(self.home, now=at(0))
        r = heartbeat.beat(self.home, now=at(3600))
        self.assertFalse(r['woke'])
        self.assertTrue(any('no wake command configured' in s for s in r['said']))
        self.assertEqual(self.body_lines(), [])

    def test_a_command_list_gets_the_brief_and_its_cost_is_read(self):
        out = os.path.join(self.tmp, 'brief.json')
        code = ('import sys, json; d = sys.stdin.read(); open(%r, "w").write(json.dumps({"home": sys.argv[1], '
                '"brief": json.loads(d)})); print("working"); print(json.dumps({"cost_tokens": 7}))' % out)
        h = make_home(os.path.join(self.tmp, 'h3'), cfg={'wake_command': [sys.executable, '-I', '-c', code],
                                                          'wake_timeout_s': 30})
        heartbeat.beat(h, now=at(0))
        r = heartbeat.beat(h, now=at(3600))
        self.assertTrue(r['woke'], r['said'])
        with open(out, encoding='utf-8') as f:
            got = json.load(f)
        self.assertEqual(got['home'], h)
        self.assertEqual(sorted(got['brief']), ['as_of', 'budget', 'ids', 'reason'])
        self.assertEqual(r['wake']['cost_tokens'], 7)
        done = [b for b in self.body_lines(h) if b['body']['state'] == 'done']
        self.assertEqual(done[0]['body']['cost_tokens'], 7)
        self.assertEqual(done[0]['body']['name'], 'heartbeat')
        self.assertEqual(done[0]['reason'], 'delegated')

    def test_the_wake_never_sees_the_forge_token(self):
        out = os.path.join(self.tmp, 'env.json')
        code = ('import os, json; json.dump({"named": os.environ.get("HB_TEST_TOKEN"), "copy": os.environ.get('
                '"HB_TEST_COPY"), "path": bool(os.environ.get("PATH"))}, open(%r, "w"))' % out)
        h = make_home(os.path.join(self.tmp, 'tok'), cfg={
            'wake_command': [sys.executable, '-I', '-c', code],
            'forge': {'kind': 'forgejo', 'url': 'https://forge.test', 'user': 'acct', 'token_env': 'HB_TEST_TOKEN'}})
        os.environ.update({'HB_TEST_TOKEN': 'tok-SEKRET-91', 'HB_TEST_COPY': 'tok-SEKRET-91'})
        try:
            heartbeat.beat(h, now=at(0))
            r = heartbeat.beat(h, now=at(3600))
        finally:
            os.environ.pop('HB_TEST_TOKEN', None)
            os.environ.pop('HB_TEST_COPY', None)
        self.assertTrue(r['woke'], r['said'])
        with open(out, encoding='utf-8') as f:
            got = json.load(f)
        self.assertEqual(got, {'named': None, 'copy': None, 'path': True})
        self.assertNotIn('tok-SEKRET-91', json.dumps(r))

    def test_a_wake_that_never_started_is_not_a_wake(self):
        h = make_home(os.path.join(self.tmp, 'nostart'), cfg={'wake_command': [os.path.join(self.tmp, 'no-such-agent')]})
        heartbeat.beat(h, now=at(0))
        r = heartbeat.beat(h, now=at(3600))
        self.assertFalse(r['woke'])
        self.assertFalse(r['wake']['ran'])
        self.assertTrue(any('could not be started' in s for s in r['said']))
        self.assertEqual(self.body_lines(h), [])
        line = self.log(h)[-1]
        self.assertEqual((line['woke'], line['ok']), (False, False))
        r2 = heartbeat.beat(h, now=at(3660))                     # not counted against the gap: it is tried again
        self.assertFalse(any('within' in s for s in r2['said']))
        self.assertTrue(any('could not be started' in s for s in r2['said']))
        self.assertEqual(heartbeat.status(h, now=at(3700))['wakes_today'], 0)

    def test_the_done_line_carries_the_seconds_the_wake_ran(self):
        heartbeat.beat(self.home, now=at(0))
        r = heartbeat.beat(self.home, now=at(3600), wake=FakeWake({'ok': True, 'seconds': 2.4, 'cost_tokens': 9}))
        done = [b for b in self.body_lines() if b['body']['state'] == 'done'][0]
        self.assertEqual(done['body']['seconds'], 2)
        self.assertEqual(r['wake']['seconds'], 2.4)
        got = bodies.wakes(record.read(self.home)['lines'], at(3700))
        self.assertEqual((got[-1]['seconds'], got[-1]['cost_tokens']), (2, 9))

    def test_a_command_that_is_not_a_list_is_not_run(self):
        h = make_home(os.path.join(self.tmp, 'h4'), cfg={'wake_command': 'rm -rf /'})
        heartbeat.beat(h, now=at(0))
        r = heartbeat.beat(h, now=at(3600))
        self.assertFalse(r['woke'])
        self.assertTrue(any('not a list of words' in s for s in r['said']))


# ---------------------------------------------------------------- law 4: what a beat writes

class TestWrites(Base):
    def test_only_what_it_may(self):
        w = FakeWake()
        before = snapshot(self.home)                        # before the first beat, so nothing it writes hides
        heartbeat.beat(self.home, now=at(0), wake=w)
        r = heartbeat.beat(self.home, now=at(3600), wake=w)
        self.assertTrue(r['woke'])
        after = snapshot(self.home)
        allowed = DERIVED | {os.path.join('record', record.actor_file(AIDE))}
        self.assertTrue(set(after) - set(before) <= allowed, set(after) - set(before) - allowed)   # new paths
        self.assertEqual(set(before) - set(after), set())                                         # none gone
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        self.assertTrue(changed <= allowed, changed - allowed)
        self.assertEqual(len(self.body_lines()), 2)
        self.assertEqual(len(self.log()), 2)
        line = self.log()[-1]
        self.assertEqual(sorted(line), ['as_of', 'cost', 'ok', 'pulled', 'reason', 'receipts', 'signals', 'woke'])
        self.assertEqual(sorted(line['cost']), ['bytes', 'requests', 'seconds'])

    def test_dry_writes_nothing(self):
        before = snapshot(self.home)
        r = heartbeat.beat(self.home, now=at(0), dry=True, wake=FakeWake())
        self.assertTrue(r['dry'])
        self.assertEqual(snapshot(self.home), before)

    def test_a_body_line_per_wake_not_per_beat(self):
        w = FakeWake()
        for s in (0, 60, 120, 180):
            heartbeat.beat(self.home, now=at(s), wake=w)
        self.assertEqual(self.body_lines(), [])
        self.assertEqual(len(self.log()), 4)


# ---------------------------------------------------------------- law 5: install installs nothing

class TestInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.home = make_home(os.path.join(self.tmp, 'a home & 100% <here>'))

    def test_install_writes_files_and_installs_nothing(self):
        for kind in heartbeat.KINDS:
            out = os.path.join(self.tmp, 'out-' + kind)
            r = heartbeat.install(self.home, kind, out_dir=out, python='/usr/bin/python3')
            self.assertTrue(r['files'])
            self.assertEqual(sorted(os.listdir(out)), sorted(os.path.basename(f) for f in r['files']))
            text = ' '.join(r['said'])
            self.assertIn({'launchd': 'launchctl', 'systemd': 'systemctl', 'cron': 'crontab'}[kind], text)
            self.assertIn('nothing is installed', text)
        with open(heartbeat.install(self.home, 'launchd', out_dir=os.path.join(self.tmp, 'pl'))['files'][0], 'rb') as f:
            pl = plistlib.load(f)
        self.assertEqual(pl['ProgramArguments'][-2:], ['beat', os.path.abspath(self.home)])
        self.assertEqual(pl['StartInterval'], heartbeat.EVERY_S)
        svc = [f for f in heartbeat.install(self.home, 'systemd', out_dir=os.path.join(self.tmp, 'sd'))['files']
               if f.endswith('.service')][0]
        with open(svc, encoding='utf-8') as f:
            self.assertIn('100%% <here>', f.read())             # systemd's % is doubled, the path quoted

    def test_the_module_calls_no_service_manager(self):
        with open(heartbeat.__file__, encoding='utf-8') as f:
            tree = ast.parse(f.read())
        calls = []
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                            and isinstance(n.func.value, ast.Name) and n.func.value.id in ('subprocess', 'os') \
                            and n.func.attr in ('run', 'Popen', 'call', 'check_call', 'check_output', 'system',
                                                'popen', 'execv', 'execvp', 'spawnv', 'spawnvp', 'startfile'):
                        calls.append((fn.name, n))
        self.assertEqual([c[0] for c in calls], ['_wake_default'])
        for _, n in calls:
            for s in ast.walk(n):
                if isinstance(s, ast.Constant) and isinstance(s.value, str):
                    for word in ('launchctl', 'systemctl', 'crontab'):
                        self.assertNotIn(word, s.value)

    def test_cron_keeps_to_its_own_steps(self):
        self.assertEqual(heartbeat._cron(20)[0], '* * * * *')
        self.assertEqual(heartbeat._cron(120)[0], '*/2 * * * *')
        self.assertEqual(heartbeat._cron(3540)[0], '*/59 * * * *')
        self.assertEqual(heartbeat._cron(3600)[0], '0 * * * *')
        self.assertEqual(heartbeat._cron(4000)[0], '0 */2 * * *')
        self.assertEqual(heartbeat._cron(90000)[0], '0 0 * * *')
        self.assertIn('once a day', heartbeat._cron(90000)[1])
        h = make_home(os.path.join(self.tmp, 'slow'), cfg={'every_s': 7200})
        r = heartbeat.install(h, 'cron', out_dir=os.path.join(self.tmp, 'cr'))
        with open(r['files'][0], encoding='utf-8') as f:
            self.assertIn('\n0 */2 * * * ', f.read())
        self.assertTrue(any('every 2 hour' in s for s in r['said']))

    def test_an_out_dir_that_is_a_file_is_said(self):
        f = os.path.join(self.tmp, 'a-file')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write('x')
        r = heartbeat.install(self.home, 'launchd', out_dir=f)
        self.assertEqual(r['files'], [])
        self.assertTrue(any('cannot be made' in s for s in r['said']))

    def test_null_guards(self):
        self.assertTrue(heartbeat.install(None, 'cron')['said'])
        self.assertEqual(heartbeat.install(self.home, 'windows')['files'], [])
        self.assertEqual(heartbeat.install(self.home, 'cron', python=None)['files'], [])


# ---------------------------------------------------------------- laws 6 and 7: the loop

class TestRun(Base):
    def clock(self, step=60):
        n = {'i': 0}

        def c():
            n['i'] += 1
            return at(n['i'] * step)
        return c

    def test_two_beats_and_stop(self):
        slept = []
        r = heartbeat.run(self.home, beats=2, clock=self.clock(), sleep=slept.append, wake=FakeWake())
        self.assertEqual(r['beats'], 2)
        self.assertEqual(r['stopped'], 'beats')
        self.assertEqual(len(self.log()), 2)
        self.assertAlmostEqual(sum(slept), heartbeat.EVERY_S)   # one gap between two beats

    def test_a_failing_beat_is_logged_and_the_next_runs(self):
        n = {'i': 0}

        def flaky(home, **kw):
            n['i'] += 1
            if n['i'] == 1:
                raise RuntimeError('the disk hiccuped')
            return heartbeat.beat(home, **kw)
        r = heartbeat.run(self.home, beats=3, clock=self.clock(), sleep=lambda s: None, beat_fn=flaky)
        self.assertEqual(r['beats'], 3)
        self.assertEqual(r['errors'], 1)
        log = self.log()
        self.assertIn('the disk hiccuped', log[0]['error'])
        self.assertEqual(len(log), 3)

    def test_a_wake_that_raises_does_not_stop_the_loop(self):
        st_clock = self.clock(step=3600)
        r = heartbeat.run(self.home, beats=3, clock=st_clock, sleep=lambda s: None,
                          wake=FakeWake(raises=ValueError('no')))
        self.assertEqual((r['beats'], r['errors']), (3, 0))
        self.assertTrue(any(b['body']['state'] == 'done' for b in self.body_lines()))

    def test_never_faster_than_twenty_seconds(self):
        slept = []
        r = heartbeat.run(self.home, every_s=1, beats=3, clock=self.clock(), sleep=slept.append)
        self.assertEqual(r['every_s'], heartbeat.MIN_EVERY_S)
        self.assertAlmostEqual(sum(slept), 2 * heartbeat.MIN_EVERY_S)
        self.assertEqual(heartbeat.every(self.home, every_s=5)['every_s'], 20)
        h = make_home(os.path.join(self.tmp, 'fast'), cfg={'every_s': 3})
        self.assertEqual(heartbeat.every(h)['every_s'], 20)
        self.assertEqual(heartbeat.every(self.home)['every_s'], heartbeat.EVERY_S)

    def test_a_count_of_none_or_less_beats_nothing(self):
        for n in (0, -3, True, 2.5, 'two'):
            r = heartbeat.run(self.home, beats=n, clock=self.clock(), sleep=lambda s: None)
            self.assertEqual(r['beats'], 0, n)
            self.assertTrue(r['said'], n)
        self.assertFalse(os.path.exists(os.path.join(self.home, heartbeat.LOG_NAME)))
        import contextlib
        buf = __import__('io').StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(heartbeat.main(['run', self.home, '--beats', '0']), 0)
        self.assertIn('beats nothing', buf.getvalue())

    def test_a_signal_stops_it_between_beats(self):
        import signal as sig

        def sleep(s):
            os.kill(os.getpid(), sig.SIGTERM)
        r = heartbeat.run(self.home, beats=None, clock=self.clock(), sleep=sleep)
        self.assertEqual(r['stopped'], 'signal')
        self.assertEqual(r['beats'], 1)


# ---------------------------------------------------------------- status and law 8

class TestStatusAndGuards(Base):
    def test_status(self):
        w = FakeWake()
        heartbeat.beat(self.home, now=at(0), wake=w)
        heartbeat.beat(self.home, now=at(3600), wake=w)
        s = heartbeat.status(self.home, now=at(4000))
        self.assertEqual((s['beats_today'], s['wakes_today']), (2, 1))
        self.assertEqual(s['last_wake'], at(3600))
        self.assertEqual(s['next_due']['wake'], at(7200))
        self.assertEqual(sorted(s['cost_today']), ['bytes', 'requests', 'seconds'])
        empty = heartbeat.status(make_home(os.path.join(self.tmp, 'new')), now=at(0))
        self.assertIsNone(empty['last_beat'])
        self.assertTrue(empty['said'])

    def test_null_guards(self):
        for h in (None, '', 3.5, {}, [], os.path.join(self.tmp, 'absent')):
            r = heartbeat.beat(h, now=at(0))
            self.assertFalse(r['woke'])
            self.assertTrue(r['said'])
            self.assertTrue(heartbeat.status(h, now=at(0))['said'])
        link = os.path.join(self.tmp, 'link')
        os.symlink(self.home, link)
        self.assertTrue(any('link' in s for s in heartbeat.beat(link, now=at(0))['said']))
        for bad in ({'wake_command': None}, {'wake_every': 'often'}, {'wake_every': float('nan')},
                    {'every_s': True}, {'agent': 7}, {'forge': 'x'}):
            h = make_home(os.path.join(self.tmp, 'g%d' % len(os.listdir(self.tmp))), cfg=bad)
            heartbeat.beat(h, now=at(0))
            self.assertFalse(heartbeat.beat(h, now=at(1))['woke'])
        nfc = make_home(os.path.join(self.tmp, 'nfc'), agent=False,
                        cfg={'agent': unicodedata.normalize('NFD', 'agent:caf\u00e9')})
        record.append(nfc, PERSON, PERSON, 'affirm', {'agent': 'agent:caf\u00e9'}, sign=False, ts=T0, salt='a')
        record.append(nfc, PERSON, PERSON, 'affirm', {'agent': AIDE}, sign=False, ts=T0, salt='b')
        heartbeat.beat(nfc, now=at(0))
        r = heartbeat.beat(nfc, now=at(3600), wake=FakeWake())
        self.assertEqual(r['agent'], 'agent:caf\u00e9')          # the NFD name in holon.json chooses the NFC agent
        self.assertTrue(r['woke'])
        self.assertEqual(len(r['recorded']), 2)

    def test_one_beat_at_a_time(self):
        fd, why = heartbeat._lock(self.home)
        try:
            r = heartbeat.beat(self.home, now=at(0), wake=FakeWake())
        finally:
            heartbeat._unlock(fd)
        if heartbeat.fcntl is not None:
            self.assertTrue(any('another beat' in s for s in r['said']))
            self.assertFalse(os.path.exists(os.path.join(self.home, heartbeat.LOG_NAME)))

    def test_a_type_wrong_memory_never_wedges_a_beat(self):
        for i, bad in enumerate(({'seen': 5}, {'negatives': 5}, {'faults': 7}, {'seen': [[1]]},
                                 {'wakes': 5}, {'wakes': [{'at': at(0), 'reason': 'cadence', 'ids': 3}]},
                                 {'seen': 'abc', 'negatives': {'a': 1}, 'faults': [None, 2], 'cadence_mark': 9})):
            h = make_home(os.path.join(self.tmp, 'mem%d' % i))
            heartbeat.beat(h, now=at(0), wake=FakeWake())
            st = heartbeat._load_state(h)
            st.update(bad)
            heartbeat._save_state(h, st)
            for s_ in (60, 3700):
                r = heartbeat.beat(h, now=at(s_), wake=FakeWake())
                self.assertFalse(any('stopped' in x for x in r['said']), (bad, r['said']))
            self.assertTrue(r['woke'], bad)
            st = heartbeat._load_state(h)
            for k in ('seen', 'negatives', 'faults'):
                self.assertTrue(all(isinstance(x, str) for x in st.get(k, [])), (bad, k, st.get(k)))

    def test_no_clock_is_read_when_the_time_is_given(self):
        reads = []

        class Clockless(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                reads.append('datetime.now')
                return dt.datetime.now(tz)

            @classmethod
            def today(cls):
                reads.append('datetime.today')
                return dt.datetime.today()

        class Dayless(dt.date):
            @classmethod
            def today(cls):
                reads.append('date.today')
                return dt.date.today()
        shim = types.SimpleNamespace(**{k: getattr(dt, k) for k in dir(dt) if not k.startswith('__')})
        shim.datetime, shim.date = Clockless, Dayless
        held = {}
        for name, mod in list(sys.modules.items()):
            f = getattr(mod, '__file__', None) or ''
            if f.startswith(ENGINE + os.sep) and getattr(mod, 'dt', None) is dt:
                held[name] = mod
                mod.dt = shim
        try:
            heartbeat.beat(self.home, now=at(0), wake=FakeWake())
            r = heartbeat.beat(self.home, now=at(3600), wake=FakeWake())
        finally:
            for mod in held.values():
                mod.dt = dt
        self.assertIn('heartbeat', held)
        self.assertTrue(r['woke'], r['said'])
        self.assertEqual(reads, [])

    def test_no_agent_no_body_line(self):
        h = make_home(os.path.join(self.tmp, 'alone'), agent=False)
        heartbeat.beat(h, now=at(0))
        r = heartbeat.beat(h, now=at(3600), wake=FakeWake())
        self.assertIsNone(r['agent'])
        self.assertTrue(r['woke'])
        self.assertEqual(self.body_lines(h), [])
        self.assertTrue(any('no agent' in s for s in r['said']))

    def test_words(self):
        with open(heartbeat.__file__, encoding='utf-8') as f:
            src = f.read()
        with open(os.path.join(ENGINE, 'heartbeat', 'README.md'), encoding='utf-8') as f:
            readme = f.read()
        for text in (src, readme):
            for word in ('promise', ' HQ', 'estate', 'house'):
                self.assertNotIn(word, text)
        self.assertLess(len(readme.splitlines()), 60)


if __name__ == '__main__':
    unittest.main()
