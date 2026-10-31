"""test_pull.py — the pull's laws, each checked: one question per tick, the token kept, only what is due
and changed fetched, a 304 fetches nothing, a missed tick loses nothing, as-of per source, null-guards.

Real temporary git repositories stand for the forge (a bare repository per cell under a folder that
`https://forge.test/` is rewritten to, in a git config made for the run); a fake opener stands for the
forge's API. Nothing here reaches a network.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_pull.py -v
"""
import ast
import datetime as dt
import http.client
import http.server
import io
import threading
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import holon   # noqa: E402
import pull    # noqa: E402
import record  # noqa: E402

GIT = shutil.which('git')
PERSON, OTHER, AIDE, STEWARD = 'person:player', 'person:other', 'agent:aide', 'person:steward'
T0 = '2026-10-31T09:00:00-07:00'
TOKEN = 'tok-SEKRET-7f3a'
WORK = None
SAVED_ENV = {}
ENV_KEYS = ('LIONSBERG_KEY_DIR', 'LIONSBERG_SIGCACHE_KEY', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM')


def at(seconds):
    return (dt.datetime.fromisoformat(T0) + dt.timedelta(seconds=seconds)).isoformat(timespec='seconds')


def setUpModule():
    global WORK
    if not GIT:
        raise unittest.SkipTest('git is needed: the cells are real repositories')
    WORK = tempfile.mkdtemp(prefix='lionsberg-pull-')
    for k in ENV_KEYS:
        SAVED_ENV[k] = os.environ.get(k)
    os.makedirs(os.path.join(WORK, 'keys'))
    os.makedirs(os.path.join(WORK, 'forge', 'owner'))
    cfg = os.path.join(WORK, 'gitconfig')
    with open(cfg, 'w', encoding='utf-8') as f:
        f.write('[user]\n\tname = test\n\temail = test@localhost\n[init]\n\tdefaultBranch = main\n'
                '[url "file://%s/forge/"]\n\tinsteadOf = https://forge.test/\n\tinsteadOf = https://other.test/\n'
                % WORK)
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


class Resp:
    def __init__(self, status, headers, body):
        self.status, self.headers, self._body = status, headers, body

    def read(self):
        return self._body


class Fake:
    """A forge's API: answers in order; counts and keeps every request."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, req, timeout=None):
        self.calls.append(req)
        a = self.answers.pop(0) if self.answers else (200, {}, [])
        if isinstance(a, BaseException):
            raise a
        status, headers, body = a
        raw = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
        if status >= 300:
            raise urllib.error.HTTPError(req.full_url, status, 'answer', headers, io.BytesIO(raw))
        return Resp(status, headers, raw)


def act(full, ts, eid=1, op='commit_repo'):
    """One entry of Forgejo's activity feed."""
    return {'id': eid, 'op_type': op, 'repo': {'full_name': full}, 'created': ts, 'ref_name': 'refs/heads/main'}


def event(full, ts, eid):
    """One of GitHub's received events."""
    return {'id': str(eid), 'type': 'PushEvent', 'repo': {'name': full}, 'created_at': ts}


class Base(unittest.TestCase):
    CELLS = ('cella', 'cellb')
    SIGNED = False

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.forge_dir = os.path.join(WORK, 'forge', 'owner')
        self.home = os.path.join(self.tmp, 'home')
        holon.init(self.home, 'home', 'person', PERSON, sign=False, ts=T0, salt='h')
        self.writers = {}
        for name in self.CELLS:
            tag = '%s-%s' % (os.path.basename(self.tmp), name)
            src = os.path.join(self.tmp, 'src-' + name)
            holon.init(src, name, 'cell', STEWARD, sign=None if self.SIGNED else False, ts=T0, salt=tag)
            git(src, 'init', '-q', '-b', 'main')
            git(src, 'add', '-A')
            git(src, 'commit', '-q', '-m', 'inception')
            bare = os.path.join(self.forge_dir, tag + '.git')
            subprocess.run([GIT, 'clone', '-q', '--bare', src, bare], check=True, capture_output=True)
            url = 'https://forge.test/owner/%s.git' % tag
            res = holon.join(self.home, url, name, ts=T0, salt='j' + name)
            self.assertTrue(res['ok'], res['said'])
            w = os.path.join(self.tmp, 'writer-' + name)
            subprocess.run([GIT, 'clone', '-q', url, w], check=True, capture_output=True)
            self.writers[name] = w
        self.full = {n: 'owner/%s-%s' % (os.path.basename(self.tmp), n) for n in self.CELLS}
        self.calls = []

    def upstream(self, name, n=1, typ='say', body=None, actor=OTHER, sign=False, base=0):
        w = self.writers[name]
        ids = []
        for i in range(n):
            r = record.append(w, actor, actor if actor.startswith('person:') else OTHER, typ,
                              body or {'text': 'line %d' % i}, sign=sign, ts=at(base + i), salt='u%d%s%d' % (i, typ, base))
            git(w, 'add', '-A')
            git(w, 'commit', '-q', '-m', 'line %d' % i)
            ids.append(r['line']['id'])
        git(w, 'push', '-q', 'origin', 'HEAD')
        return ids

    def sync(self, exe, d, hq):
        self.calls.append(os.path.basename(d))
        return holon._sync_one(exe, d, hq)

    def tick(self, seconds, **kw):
        kw.setdefault('sync', self.sync)
        return pull.tick(self.home, now=at(seconds), **kw)

    def forgejo(self):
        return {'kind': 'forgejo', 'url': 'https://forge.test', 'user': 'player-account', 'token': TOKEN}

    def github(self):
        return {'kind': 'github', 'url': 'https://api.forge.test', 'user': 'player-account', 'token': TOKEN}

    def subs_file(self, rows):
        with open(os.path.join(self.home, 'subscriptions.json'), 'w', encoding='utf-8') as f:
            json.dump(rows, f)

    def state(self):
        with open(os.path.join(self.home, '.pulled.json'), encoding='utf-8') as f:
            return json.load(f)


class TestOneQuestion(Base):
    def test_one_request_per_tick(self):
        fake = Fake((200, {}, [act(self.full['cella'], at(0))]))
        r = self.tick(0, forge=self.forgejo(), opener=fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(r['asked_forge'], 1)
        self.assertEqual(r['fetched'], ['cella', 'cellb'])        # the first tick is always due
        fake2 = Fake((200, {}, []))
        self.tick(400, forge=self.forgejo(), opener=fake2)
        self.assertEqual(len(fake2.calls), 1)
        self.assertIn('/api/v1/users/player-account/activities/feeds?', fake2.calls[0].full_url)

    def test_each_page_is_counted(self):
        f = dict(self.forgejo(), limit=2)
        seen = {'90': at(-100)}
        fake = Fake((200, {}, [act('owner/a', at(3), 3), act('owner/b', at(2), 2)]),
                    (200, {}, [act('owner/c', at(1), 1), act('owner/z', at(-100), 90)]))
        res = pull.forge_changes(f, seen, opener=fake)
        self.assertEqual(res['asked'], 2)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn('page=2', fake.calls[1].full_url)
        self.assertEqual(sorted(res['changed']), ['owner/a', 'owner/b', 'owner/c'])   # owner/z was seen
        self.assertTrue(res['complete'])

    def test_a_full_page_past_the_cap_is_incomplete(self):
        f = dict(self.forgejo(), limit=2, max_pages=1)
        fake = Fake((200, {}, [act('owner/a', at(3), 3), act('owner/b', at(2), 2)]))
        res = pull.forge_changes(f, {'90': at(-100)}, opener=fake)
        self.assertEqual(res['asked'], 1)
        self.assertFalse(res['complete'])
        self.assertTrue(res['said'])
        first = pull.forge_changes(self.forgejo(), None, opener=Fake((200, {}, [])))
        self.assertFalse(first['complete'])                       # a first question compares with nothing

    def test_only_pushes_name_a_change(self):
        res = pull.forge_changes(self.forgejo(), {}, opener=Fake((200, {}, [
            act('owner/a', at(1), 1, 'star_repo'), act('owner/b', at(2), 2, 'merge_pull_request')])))
        self.assertEqual(sorted(res['changed']), ['owner/b'])
        self.assertEqual(sorted(res['seen']), ['1', '2'])


class _Forge(http.server.BaseHTTPRequestHandler):
    seen, target = [], None

    def do_GET(self):
        type(self).seen.append((self.path, self.headers.get('Authorization')))
        if self.path.startswith('/api/'):
            self.send_response(302)
            self.send_header('Location', type(self).target(self))
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'[]')

    def log_message(self, *a):
        pass


class TestToken(Base):
    CELLS = ('cella',)

    def test_token_never_leaves_the_header(self):
        fake = Fake((200, {}, []), urllib.error.URLError('refused at %s' % TOKEN))
        r1 = self.tick(0, forge=self.forgejo(), opener=fake)
        r2 = self.tick(400, forge=self.forgejo(), opener=fake)
        for req in fake.calls:
            self.assertNotIn(TOKEN, req.full_url)
            self.assertEqual(req.get_header('Authorization'), 'token ' + TOKEN)
            self.assertNotIn('Authorization', req.headers)          # unredirected: never carried on a redirect
        for r in (r1, r2):
            self.assertNotIn(TOKEN, json.dumps(r))
        self.assertTrue(any('did not answer' in s for s in r2['said']))
        with open(os.path.join(self.home, pull.LOG_NAME), encoding='utf-8') as f:
            self.assertNotIn(TOKEN, f.read())
        self.assertNotIn(TOKEN, json.dumps(self.state()))
        res = pull.forge_changes(self.github(), None, opener=Fake(OSError('no route %s' % TOKEN)))
        self.assertNotIn(TOKEN, json.dumps(res))
        self.assertIsNone(res['status'])

    def test_a_redirect_never_carries_the_token_off_the_forge(self):
        class Evil(_Forge):
            seen = []
        evil = http.server.HTTPServer(('127.0.0.1', 0), Evil)

        class Forge(_Forge):
            seen = []
            target = staticmethod(lambda h: 'http://127.0.0.1:%d/steal' % evil.server_port)
        forge = http.server.HTTPServer(('127.0.0.1', 0), Forge)
        for srv in (evil, forge):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            f = {'kind': 'forgejo', 'url': 'http://127.0.0.1:%d' % forge.server_port, 'user': 'u', 'token': TOKEN}
            res = pull.forge_changes(f, {})
            self.assertEqual(Evil.seen, [])                           # the other host was never asked
            self.assertEqual(res['status'], 302)
            self.assertFalse(res['complete'])
            Forge.target = staticmethod(lambda h: '/elsewhere')       # a redirect on the forge's own host
            res = pull.forge_changes(f, {})
            self.assertEqual(res['status'], 200)
            self.assertEqual(Forge.seen[-1], ('/elsewhere', None))    # followed, without the token
        finally:
            for srv in (evil, forge):
                srv.shutdown()
                srv.server_close()

    def test_plain_http_with_a_token_is_refused(self):
        fake = Fake()
        res = pull.forge_changes(dict(self.forgejo(), url='http://forge.test'), {}, opener=fake)
        self.assertEqual((res['asked'], fake.calls), (0, []))
        self.assertIn('plain http', res['said'])

    def test_whatever_the_opener_raises_is_said(self):
        for boom in (http.client.IncompleteRead(b'par'), http.client.BadStatusLine('bad %s' % TOKEN),
                     RuntimeError('odd %s' % TOKEN)):
            self.tick(0)
            r = self.tick(400, forge=self.forgejo(), opener=Fake(boom))
            self.assertNotIn(TOKEN, json.dumps(r))
            self.assertTrue(r['said'])
        r = pull.tick(self.home, now=at(900), forge=self.forgejo(), sync=lambda *a: 1 / 0)
        self.assertNotIn(TOKEN, json.dumps(r))

    def test_no_token_falls_back_to_each_due_cell(self):
        f = dict(self.forgejo(), token='')
        fake = Fake()
        r = self.tick(0, forge=f, opener=fake)
        self.assertEqual(fake.calls, [])
        self.assertEqual(r['fetched'], ['cella'])
        self.assertEqual(r['asked_forge'], 1)
        self.assertTrue(any('no token' in s for s in r['said']))


class TestDue(Base):
    def test_a_cell_not_due_is_not_fetched(self):
        self.tick(0)
        self.assertEqual(sorted(self.calls), ['cella', 'cellb'])
        self.calls.clear()
        self.upstream('cella')
        r = self.tick(60)
        self.assertEqual(self.calls, [])
        self.assertEqual(r['skipped'], [{'cell': 'cella', 'why': 'not due'}, {'cell': 'cellb', 'why': 'not due'}])
        self.assertEqual(r['next_due'], {'cella': at(300), 'cellb': at(300)})
        r = self.tick(300)
        self.assertEqual(r['new_lines'], {'cella': 1, 'cellb': 0})

    def test_unchanged_is_skipped_and_changed_is_fetched(self):
        self.tick(0, forge=self.forgejo(), opener=Fake((200, {}, [])))
        self.calls.clear()
        self.upstream('cella')
        r = self.tick(400, forge=self.forgejo(), opener=Fake((200, {}, [act(self.full['cella'], at(350))])))
        self.assertEqual(self.calls, ['cella'])
        self.assertEqual(r['skipped'], [{'cell': 'cellb', 'why': 'unchanged'}])
        self.assertEqual(r['new_lines'], {'cella': 1})
        self.assertEqual(r['cost']['requests'], 2)                 # one question, one fetch

    def test_nothing_due_asks_nothing(self):
        self.tick(0)
        fake = Fake()
        r = self.tick(10, forge=self.forgejo(), opener=fake)
        self.assertEqual(fake.calls, [])
        self.assertEqual(r['asked_forge'], 0)

    def test_pending_keeps_only_joined_cells(self):
        self.tick(0, forge=self.forgejo(), opener=Fake((200, {}, [])))
        self.tick(400, forge=self.forgejo(), opener=Fake((200, {}, [act('owner/not-joined', at(390), 7),
                                                                     act(self.full['cella'], at(391), 8)])))
        self.assertEqual(self.state()[pull.STATE_KEY]['forge']['pending'], {})

    def test_a_time_that_is_not_a_time_is_refused(self):
        r = pull.tick(self.home, now='half past never')
        self.assertTrue(any('not a time' in s for s in r['said']))
        self.assertEqual(r['fetched'], [])
        self.assertTrue(any('not a time' in s for s in pull.due(self.home, 'nope')['said']))


class TestGitHub(Base):
    def test_304_fetches_nothing_and_keeps_the_etag(self):
        first = Fake((200, {'ETag': '"e1"', 'X-Poll-Interval': '60'}, []))
        r = self.tick(0, forge=self.github(), opener=first)
        self.assertEqual(r['fetched'], ['cella', 'cellb'])
        self.assertTrue(first.calls[0].full_url.startswith('https://api.forge.test/users/player-account/received_events'))
        self.calls.clear()
        fake = Fake((304, {'X-Poll-Interval': '60'}, b''))
        r = self.tick(400, forge=self.github(), opener=fake)
        self.assertEqual(fake.calls[0].get_header('If-none-match'), '"e1"')
        self.assertEqual(self.calls, [])
        self.assertEqual(r['fetched'], [])
        self.assertEqual(r['forge']['poll_interval'], 60)
        self.assertEqual(self.state()[pull.STATE_KEY]['forge']['etag'], '"e1"')
        soon = Fake()
        r = self.tick(430, forge=self.github(), opener=soon)
        self.assertEqual(soon.calls, [])
        self.assertEqual(r['asked_forge'], 0)
        self.assertTrue(any(s.startswith('too soon') for s in r['said']))
        self.assertEqual(r['forge']['next_question'], at(460))

    def test_new_events_name_the_changed_repository(self):
        self.tick(0, forge=self.github(), opener=Fake((200, {'ETag': '"e1"'}, [])))
        self.upstream('cellb')
        self.calls.clear()
        ev = [event(self.full['cellb'], '2026-10-31T16:05:00Z', 'g1')]
        self.tick(400, forge=self.github(), opener=Fake((200, {'ETag': '"e2"'}, ev)))
        self.assertEqual(self.calls, ['cellb'])
        self.assertEqual(self.state()[pull.STATE_KEY]['forge']['etag'], '"e2"')

    def test_a_late_event_is_not_dropped(self):
        self.tick(0, forge=self.github(), opener=Fake((200, {}, [event(self.full['cella'], at(0), 'g1')])))
        self.upstream('cellb')
        self.calls.clear()
        late = [event(self.full['cella'], at(0), 'g1'), event(self.full['cellb'], at(-3000), 'g0')]
        r = self.tick(400, forge=self.github(), opener=Fake((200, {}, late)))
        self.assertEqual(self.calls, ['cellb'])                    # older than the newest seen, and never seen
        self.assertEqual(r['new_lines'], {'cellb': 1})

    def test_too_soon_holds_back_only_what_the_forge_speaks_for(self):
        self.subs_file([{'source': 'cella', 'cadence': 10}, {'source': 'cellb', 'cadence': 10}])
        self.tick(0, forge=self.github(), opener=Fake((200, {'X-Poll-Interval': '600'}, [])))
        cb = os.path.join(self.home, 'cells', 'cellb')
        git(cb, 'remote', 'set-url', 'origin', 'https://other.test/' + self.full['cellb'] + '.git')
        self.calls.clear()
        r = self.tick(20, forge=self.github(), opener=Fake())
        self.assertTrue(any(s.startswith('too soon') for s in r['said']))
        self.assertEqual(r['skipped'], [{'cell': 'cella', 'why': 'too soon'}])
        self.assertEqual(self.calls, ['cellb'])                    # on another host: the forge cannot speak for it


class TestNothingLost(Base):
    def test_a_missed_tick_loses_nothing(self):
        self.tick(0)
        ids = self.upstream('cella', n=2)
        r = self.tick(1000)
        self.assertEqual(r['new_lines']['cella'], 2)
        held = {l['id'] for l in record.read(os.path.join(self.home, 'cells', 'cella'))['lines']}
        self.assertTrue(set(ids) <= held)

    def test_a_change_seen_while_not_due_is_kept_until_due(self):
        self.subs_file([{'source': 'cella', 'cadence': {'say': 3600}}])
        self.tick(0, forge=self.forgejo(), opener=Fake((200, {}, [])))
        self.upstream('cella')
        r = self.tick(400, forge=self.forgejo(), opener=Fake((200, {}, [act(self.full['cella'], at(390))])))
        self.assertIn({'cell': 'cella', 'why': 'not due'}, r['skipped'])
        self.calls.clear()
        r = self.tick(4000, forge=self.forgejo(), opener=Fake((200, {}, [act(self.full['cella'], at(390))])))
        self.assertIn('cella', self.calls)                         # the forge names it as seen now; pending holds it
        self.assertEqual(r['new_lines']['cella'], 1)

    def test_the_gate_still_refuses_a_rewritten_history(self):
        self.upstream('cella', n=2)
        self.tick(0)
        w = self.writers['cella']
        git(w, 'reset', '-q', '--hard', 'HEAD~1')
        record.append(w, OTHER, OTHER, 'say', {'text': 'rewritten'}, sign=False, ts=at(5), salt='rw')
        git(w, 'add', '-A')
        git(w, 'commit', '-q', '-m', 'rewrite')
        git(w, 'push', '-q', '--force', 'origin', 'HEAD')
        r = self.tick(400)
        self.assertFalse(r['sources']['cella']['ok'])
        self.assertIn('rewritten', r['sources']['cella']['said'])
        self.assertEqual(r['new_lines']['cella'], 0)
        self.assertEqual(r['next_due']['cella'], at(300))         # not counted as pulled: tried again next tick


class TestReport(Base):
    def test_as_of_per_source_and_deterministic(self):
        self.upstream('cella')
        twin = os.path.join(self.tmp, 'twin')
        shutil.copytree(self.home, twin, symlinks=True)
        a = pull.tick(self.home, now=at(0))
        b = pull.tick(twin, now=at(0))
        for r in (a, b):
            r['cost'].pop('seconds')
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a['as_of'], at(0))
        self.assertEqual(sorted(a['sources']), ['cella', 'cellb'])
        for s in a['sources'].values():
            self.assertIn('newest', s)
            self.assertEqual(s['pulled_at'], at(0))
        self.assertEqual(a['next_due'], {'cella': at(300), 'cellb': at(300)})
        r = pull.tick(self.home, now=at(60))
        self.assertEqual(r['sources']['cella']['newest'], a['sources']['cella']['newest'])

    def test_the_cost_line(self):
        self.tick(0, forge=self.forgejo(), opener=Fake((200, {}, [act('owner/x', at(0))])))
        with open(os.path.join(self.home, pull.LOG_NAME), encoding='utf-8') as f:
            rows = [json.loads(x) for x in f if x.strip()]
        self.assertEqual(len(rows), 1)
        c = rows[0]['cost']
        self.assertEqual(c['requests'], 3)                         # one question, two first fetches
        self.assertGreater(c['bytes'], 0)
        self.assertIsInstance(c['seconds'], float)

    def test_dry_fetches_and_keeps_nothing(self):
        r = self.tick(0, forge=self.forgejo(), opener=Fake((200, {}, [])), dry=True)
        self.assertEqual(self.calls, [])
        self.assertEqual(r['fetched'], ['cella', 'cellb'])
        self.assertNotIn(pull.STATE_KEY, self.state())
        self.assertFalse(os.path.exists(os.path.join(self.home, pull.LOG_NAME)))


class TestRose(Base):
    CELLS = ('cella',)
    SIGNED = True

    def test_only_trusted_lines_of_others_rise(self):
        w = self.writers['cella']
        holon.admit(w, STEWARD, OTHER, record.pubkey_of(record.find_key(None, OTHER)), ts=at(1), salt='adm')
        git(w, 'add', '-A')
        git(w, 'commit', '-q', '-m', 'admit')
        git(w, 'push', '-q', 'origin', 'HEAD')
        self.tick(0)
        rq = self.upstream('cella', typ='request', body={'to': PERSON, 'title': 'a look at the draft'}, sign=None,
                           base=10)
        sy = self.upstream('cella', typ='say', body={'text': 'for you', 'to': [PERSON]}, sign=None, base=11)
        self.upstream('cella', typ='say', body={'text': 'for someone else', 'to': ['person:third']}, sign=None,
                      base=12)
        impostor = self.upstream('cella', typ='request', body={'to': PERSON, 'title': 'urgent'},
                                 actor='person:third', base=13)                 # unsigned, never admitted
        r = self.tick(400)
        self.assertEqual(r['new_lines'], {'cella': 4})
        self.assertEqual(r['rose'], sorted(rq + sy))
        self.assertNotIn(impostor[0], r['rose'])

    def test_rising_by_trust_and_never_the_homes_own(self):
        # a member who writes in the home is the home's own, though their line answers for themselves
        own = {'id': 'a' * 64, 'actor': 'person:member', 'for': 'person:member', 'type': 'say',
               'body': {'text': 'x', 'to': [PERSON]}}
        theirs = dict(own, id='b' * 64, actor=OTHER, **{'for': OTHER})
        unverified = dict(theirs, id='c' * 64)
        trust = {own['id']: 'signed', theirs['id']: 'signed', unverified['id']: 'unverified'}
        held = pull.subscriptions_mod
        try:
            for reader in (held, None):                             # through the Card reader, and without it
                pull.subscriptions_mod = reader
                got = pull.rising([own, theirs, unverified], trust, {PERSON, 'person:member'}, PERSON, {AIDE}, set())
                self.assertEqual(got, [theirs['id']])
        finally:
            pull.subscriptions_mod = held


class TestSubscriptions(Base):
    def write_cards(self):
        self.subs_file([{'source': 'cellb', 'cadence': 5}])        # the file is only the fallback
        record.append(self.home, PERSON, PERSON, 'subscribe', {'source': 'cella', 'cadence': {'say': 3600,
                      'request': 600}, 'signals': ['say', 'request']}, sign=False, ts=at(1), salt='s1')
        record.append(self.home, PERSON, PERSON, 'subscribe', {'source': 'cella', 'surface': 'deal'},
                      sign=False, ts=at(2), salt='s2')
        aide = record.make_line(AIDE, PERSON, record.holon_info(self.home)['id'], 'subscribe',
                                {'source': 'cellb', 'cadence': 10}, reason='delegated', ts=at(3), salt='s3')
        with open(os.path.join(self.home, 'record', record.actor_file(AIDE)), 'a', encoding='utf-8') as f:
            f.write(record.dumps(aide) + '\n')

    def check(self):
        s = pull.subscriptions(self.home, clock=at(10))
        self.assertEqual(s['from'], 'record')
        self.assertEqual(len(s['subscriptions']), 1)
        one = s['subscriptions'][0]
        self.assertEqual((one['source'], one['surface'], one['cadence']), ('cella', 'deal', {'request': 600, 'say': 3600}))
        self.assertNotEqual(one['set_by']['cadence'], one['set_by']['surface'])   # two lines, field by field
        self.assertIn('ignored', s['said'])
        d = {c['cell']: c for c in pull.due(self.home, at(10))['cells']}
        self.assertEqual((d['cella']['cadence'], d['cella']['basis']), (600, 'subscription'))
        self.assertEqual((d['cellb']['cadence'], d['cellb']['basis']), (pull.DEFAULT_CADENCE, 'default'))

    def test_the_persons_own_lines_through_the_card_reader(self):
        self.assertIsNotNone(pull.subscriptions_mod)
        self.write_cards()
        self.check()

    def test_the_own_reading_when_the_reader_is_absent(self):
        self.write_cards()
        held, pull.subscriptions_mod = pull.subscriptions_mod, None
        try:
            self.check()
        finally:
            pull.subscriptions_mod = held

    def test_the_file_until_a_line_is_held(self):
        self.subs_file([{'source': self.full['cella'], 'cadence': 299.5}, {'source': 'nowhere', 'cadence': True}, 7])
        s = pull.subscriptions(self.home)
        self.assertEqual(s['from'], 'subscriptions.json')
        d = pull.due(self.home, at(0))
        cad = {c['cell']: c['cadence'] for c in d['cells']}
        self.assertEqual(cad, {'cella': 300, 'cellb': pull.DEFAULT_CADENCE})
        self.assertEqual(d['unjoined'], ['nowhere'])


class TestNullGuards(Base):
    CELLS = ('cella',)

    def test_no_home(self):
        for h in (None, '', os.path.join(self.tmp, 'absent'), 3.5):
            r = pull.tick(h, now=at(0))
            self.assertTrue(r['said'])
            self.assertEqual(r['fetched'], [])
            self.assertTrue(pull.subscriptions(h)['said'])
            self.assertTrue(pull.due(h)['said'])

    def test_a_home_with_no_cells_and_no_state(self):
        bare = os.path.join(self.tmp, 'lonely')
        holon.init(bare, 'lonely', 'person', PERSON, sign=False, ts=T0, salt='l')
        r = pull.tick(bare, now=at(0), forge=self.forgejo(), opener=Fake())
        self.assertTrue(any('no cell is joined' in s for s in r['said']))
        self.assertEqual(r['asked_forge'], 0)

    def test_empty_and_linked_subscription_files(self):
        self.subs_file([])
        self.assertEqual(pull.subscriptions(self.home)['subscriptions'], [])
        os.remove(os.path.join(self.home, 'subscriptions.json'))
        target = os.path.join(self.tmp, 'elsewhere.json')
        with open(target, 'w', encoding='utf-8') as f:
            json.dump([{'source': 'cella', 'cadence': 1}], f)
        os.symlink(target, os.path.join(self.home, 'subscriptions.json'))
        s = pull.subscriptions(self.home)
        self.assertEqual(s['from'], 'none')
        self.assertIn('link', s['said'])

    def test_a_forge_that_errors(self):
        for answer in ((500, {}, b'oops'), socket.timeout('timed out'), (200, {}, b'not json'),
                       http.client.RemoteDisconnected('gone')):
            if os.path.exists(os.path.join(self.home, '.pulled.json')):
                os.remove(os.path.join(self.home, '.pulled.json'))
            self.tick(0)
            self.calls.clear()
            r = self.tick(400, forge=self.forgejo(), opener=Fake(answer))
            self.assertTrue(r['said'])
            self.assertEqual(self.calls, ['cella'])                # the forge could not say, so the due cell is fetched

    def test_a_broken_state_file(self):
        with open(os.path.join(self.home, '.pulled.json'), 'w', encoding='utf-8') as f:
            f.write('{not json')
        r = self.tick(0)
        self.assertEqual(r['fetched'], ['cella'])


class TestModuleLaws(unittest.TestCase):
    def test_standard_library_only_no_model_no_names(self):
        path = os.path.join(ENGINE, 'pull.py')
        with open(path, encoding='utf-8') as f:
            src = f.read()
        mods = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                mods.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split('.')[0])
        self.assertEqual(mods - set(sys.stdlib_module_names), {'record', 'holon', 'subscriptions'})
        for word in (r'\bhouse\b', r'\bHQ\b', r'\bestate\b', r'promise', r'anthropic', r'openai', r'/v1/messages'):
            self.assertIsNone(re.search(word, src, re.I), word)


if __name__ == '__main__':
    unittest.main()
