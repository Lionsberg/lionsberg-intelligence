"""test_faces.py — the outbox as envelopes per relationship: a published face per Agreement, checked.

Each law of faces.py has a test that fails when it is broken. The pure function is proven on lines
made by hand; writing a face is proven on the signed sample fixtures (fixtures/make_fixtures.py),
built once per run in a temporary folder and copied fresh for each test.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_faces.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import faces           # noqa: E402
import holon           # noqa: E402
import record          # noqa: E402

P, S, A = 'person:player', 'person:steward', 'agent:player-aide'
HOME, CELL = 'a' * 64, 'c' * 64
TS = '2026-10-20T10:00:00-07:00'
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def mk(type_, body, for_=P, actor=None, audience='members', salt=None, reason='human', ts=TS):
    return record.make_line(actor or for_, for_, HOME, type_, body, audience=audience, reason=reason, ts=ts, salt=salt)


def row(**kw):
    r = {'id': '1' * 64, 'holon': CELL, 'state': 'agreed', 'live': True, 'with': CELL, 'agreed_with': HOME,
         'proposer': P, 'agreed_by': S, 'crosses': ['sight', 'commit', 'card'],
         'permits': {'write': False, 'bell': []}, 'face': None, 'sides': [CELL, HOME]}
    r.update(kw)
    return r


def fo(r, lines, people, audience=None, trust=None, invalid=None):
    """face_of with every line trusted at home unless a trust map is given."""
    if trust is None:
        trust = {l['id']: 'signed' for l in (lines or []) if isinstance(l, dict) and isinstance(l.get('id'), str)}
    return faces.face_of(r, lines, people, audience=audience, trust=trust, invalid=invalid)


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        return
    import make_fixtures
    WORK = tempfile.mkdtemp(prefix='lionsberg-faces-test-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


class TestWhatCrosses(unittest.TestCase):
    """Law 2: a face holds only `crosses` types; an activity card stays home; the rest is held back with why."""

    def test_only_crosses(self):
        sight = mk('sight', {'text': 'a hazard at the ford', 'kind': 'hazard'})
        say = mk('say', {'text': 'hello'})
        tea = mk('tea', {'minutes': 30, 'energy': 5, 'attention': 5})
        f = fo(row(), [sight, say, tea], [P])
        self.assertEqual([l['id'] for l in f['lines']], [sight['id']])
        why = {h['id']: h['why'] for h in f['held_back']}
        self.assertIn("does not name 'say'", why[say['id']])
        self.assertIn("does not name 'tea'", why[tea['id']])
        self.assertEqual(f['basis'], 'agreement')

    def test_activity_card_stays_home(self):
        act = mk('card', {'title': 'Gather the notes', 'kind': 'activity'})
        bare = mk('card', {'title': 'No kind named'})
        mile = mk('card', {'title': 'The plan', 'kind': 'milestone'})
        f = fo(row(), [act, bare, mile], [P])
        self.assertEqual([l['id'] for l in f['lines']], [mile['id']])
        self.assertTrue(all('activity card stays home' in h['why'] for h in f['held_back']))

    def test_default_is_the_kits(self):
        say = mk('say', {'text': 'hello'})
        commit = mk('commit', {'card': '2' * 64, 'by': '2026-11-01'})
        f = fo(row(crosses=[]), [say, commit], [P])
        self.assertEqual(f['basis'], 'default')
        self.assertEqual(f['crosses'], sorted(holon.PUBLISHABLE))
        self.assertEqual([l['id'] for l in f['lines']], [commit['id']])
        self.assertIn('inner work', f['held_back'][0]['why'])

    def test_not_publishable_though_named(self):
        tea = mk('tea', {'minutes': 30, 'energy': 5, 'attention': 5})
        f = fo(row(crosses=['tea']), [tea], [P])
        self.assertEqual(f['lines'], [])
        self.assertIn('never carries', f['held_back'][0]['why'])

    def test_people_audience_and_untrusted(self):
        other = mk('sight', {'text': 'seen by another'}, for_=S)
        quiet = mk('sight', {'text': 'kept in the holon'}, audience='holon')
        widened = mk('sight', {'text': 'widened by a publish'}, audience='holon')
        untrusted = mk('sight', {'text': 'from a page the agent read'}, actor=A, reason='untrusted')
        f = fo(row(), [other, quiet, widened, untrusted], [P], audience={widened['id']: 'members'})
        self.assertEqual([l['id'] for l in f['lines']], [widened['id']])
        why = {h['id']: h['why'] for h in f['held_back']}
        self.assertIn('not a line of this face', why[other['id']])
        self.assertIn('audience is holon', why[quiet['id']])
        self.assertIn('proposal', why[untrusted['id']])


class TestTrustAtHome(unittest.TestCase):
    """Only a line the home's fold lets act is in a face."""

    def test_trust_map_and_invalid_list(self):
        good = mk('sight', {'text': 'seen', 'kind': 'wonder'})
        unver = mk('sight', {'text': 'unverified', 'kind': 'wonder'})
        paper = mk('sight', {'text': 'paper', 'kind': 'wonder'})
        invalid = mk('commit', {'card': '2' * 64, 'by': '2026-11-01'}, actor=A)
        trust = {good['id']: 'signed', unver['id']: 'unverified', paper['id']: 'paper', invalid['id']: 'signed'}
        f = faces.face_of(row(), [good, unver, paper, invalid], [P], trust=trust, invalid=[{'id': invalid['id']}])
        self.assertEqual([l['id'] for l in f['lines']], [good['id']])
        why = {h['id']: h['why'] for h in f['held_back']}
        self.assertIn('unverified', why[unver['id']])
        self.assertIn('paper', why[paper['id']])
        self.assertIn('not valid', why[invalid['id']])

    def test_no_trust_map_holds_back(self):
        f = faces.face_of(row(), [mk('sight', {'text': 'seen'})], [P])
        self.assertEqual(f['lines'], [])
        self.assertIn('not known', f['held_back'][0]['why'])


class TestElision(unittest.TestCase):
    """Law 3: permits.fields elides the rest, the id still verifies; an unsalted line is held back."""

    def test_fields_kept_and_hidden(self):
        sight = mk('sight', {'text': 'a hazard at the ford', 'kind': 'hazard', 'where': 'the ford'})
        commit = mk('commit', {'card': '2' * 64, 'by': '2026-11-01'})
        f = fo(row(permits={'write': False, 'fields': {'sight': ['kind']}}), [sight, commit], [P])
        self.assertEqual(f['elided'], {sight['id']: ['text', 'where']})
        copy = [l for l in f['lines'] if l['id'] == sight['id']][0]
        self.assertTrue(record.check_id(copy))
        self.assertEqual(copy['body']['kind'], 'hazard')
        self.assertTrue(record._is_elided(copy['body']['text']))
        self.assertNotIn('the ford', json.dumps(copy))
        self.assertNotIn('body_salt', copy['body'])
        self.assertEqual((copy['actor'], copy['for']), (P, P))          # a face is not names-hidden
        whole = [l for l in f['lines'] if l['id'] == commit['id']][0]
        self.assertEqual(whole['body']['by'], '2026-11-01')              # a type the fields do not name goes whole
        self.assertNotIn(commit['id'], f['elided'])

    def test_unsalted_held_back(self):
        paper = mk('sight', {'text': 'written on paper', 'kind': 'wonder'}, salt='')
        f = fo(row(permits={'fields': {'sight': ['kind']}}), [paper], [P])
        self.assertEqual(f['lines'], [])
        self.assertIn('no salt', f['held_back'][0]['why'])

    def test_bad_fields_held_back(self):
        sight = mk('sight', {'text': 'x', 'kind': 'wonder'})
        f = fo(row(permits={'fields': {'sight': None}}), [sight], [P])          # agreement.py's malformed entry
        self.assertEqual(f['lines'], [])
        self.assertIn('not a list of names', f['held_back'][0]['why'])
        f = fo(row(permits={'fields': None}), [sight], [P])                     # the whole map malformed
        self.assertEqual(f['lines'], [])
        self.assertIn('not a map of types', f['held_back'][0]['why'])

    def test_fields_only_from_permits(self):
        sight = mk('sight', {'text': 'x', 'kind': 'wonder'})
        f = fo(row(fields={'sight': ['kind']}), [sight], [P])                   # a top-level fields is not read
        self.assertEqual(f['elided'], {})


class TestResolveCell(unittest.TestCase):
    """The cell: a named face, else with, else the other side, else the holon written in when it is a side."""

    CELLS = ({'first': ('f' * 64, '/x/first'), 'second': ('5' * 64, '/x/second')},
             {'f' * 64: 'first', '5' * 64: 'second'})

    def test_face_beats_with(self):
        self.assertEqual(faces._resolve_cell(row(face='second', **{'with': 'f' * 64}), self.CELLS, HOME)[0], 'second')
        self.assertEqual(faces._resolve_cell(row(face='f' * 64, **{'with': '5' * 64}), self.CELLS, HOME)[0], 'first')
        self.assertEqual(faces._resolve_cell(row(**{'with': '5' * 64}), self.CELLS, HOME)[0], 'second')

    def test_unjoined_face_refused(self):
        name, notes = faces._resolve_cell(row(face='elsewhere', **{'with': 'f' * 64}), self.CELLS, HOME)
        self.assertIsNone(name)
        self.assertIn('no joined cell', notes[0])
        self.assertIsNone(faces._resolve_cell(row(face=HOME), self.CELLS, HOME)[0])

    def test_holon_only_as_a_side(self):
        r = row(**{'with': 'e' * 64, 'holon': '5' * 64, 'sides': ['e' * 64, HOME]})
        self.assertIsNone(faces._resolve_cell(r, self.CELLS, HOME)[0])
        r['sides'] = ['5' * 64, HOME]
        self.assertEqual(faces._resolve_cell(r, self.CELLS, HOME)[0], 'second')


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the fixtures are signed')
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='lionsberg-faces-case-', dir=WORK)
        self.hq = os.path.join(self.tmp, 'hq')
        shutil.copytree(os.path.join(TEMPLATE, 'hq'), self.hq)
        self.cell = os.path.join(self.hq, 'cells', 'first-cell')
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.sight = record.append(self.hq, P, P, 'sight',
                                   {'text': 'a hazard at the ford', 'kind': 'hazard', 'where': 'the ford'},
                                   audience='members', ts='2026-10-21T09:00:00-07:00', key_dir=KEYS)['line']
        self.n = 0

    def agree(self, face=None, crosses=('sight', 'commit', 'kept', 'request', 'offer'), permits=None):
        """A live Agreement written in the cell: the player proposes, the steward answers."""
        self.n += 1
        body = {'with': self.C, 'crosses': list(crosses), 'permits': permits or {'write': True}, 'until': '2027-03-20'}
        if face:
            body['face'] = face
        prop = record.append(self.cell, P, P, 'agree', body, ts='2026-10-21T09:%02d:00-07:00' % (10 + 2 * self.n),
                             key_dir=KEYS)['line']
        record.append(self.cell, S, S, 'agree', {'with': self.H}, {'answers': [prop['id']]},
                      ts='2026-10-21T09:%02d:00-07:00' % (11 + 2 * self.n), key_dir=KEYS)
        return prop['id']

    def second_cell(self):
        d = os.path.join(self.hq, 'cells', 'second')
        holon.init(d, 'second', 'cell', S, ts='2026-10-21T08:00:00-07:00', key_dir=KEYS)
        return d

    def publish_lines(self, cell=None):
        return [l for l in record.read(cell or self.cell)['lines'] if l.get('type') == 'publish']

    def fold_cell(self, cell=None):
        r = record.read(cell or self.cell)
        return record.fold(r['lines'], record.load_types(), {self.C: S}, clock=CLOCK)


class TestPublishUnchanged(Base):
    """Law 1: holon.publish behaves as before (the publish tests of test_record stay green too)."""

    def test_publish_whole_copy_and_line(self):
        out = holon.publish(self.hq, 'first-cell', [self.sight['id'], 'f' * 64], P, key_dir=KEYS)
        self.assertEqual(out['published'], [self.sight['id']])
        self.assertEqual(out['held_back'], [{'id': 'f' * 64, 'why': 'not held in this HQ'}])
        pub = [l for l in self.publish_lines() if l['id'] == out['publish_line']][0]
        self.assertEqual(sorted(pub['body']), ['audience', 'body_salt', 'keys', 'lines', 'to'])
        self.assertEqual(pub['links'], {})
        copy = [l for l in record.read(self.cell)['lines'] if l['id'] == self.sight['id']][0]
        self.assertEqual(copy['body']['where'], 'the ford')
        with self.assertRaises(ValueError):
            holon.publish(self.hq, 'first-cell', [self.sight['id']], A)

    def test_republish_writes_the_copy_once_and_a_second_line(self):
        one = holon.publish(self.hq, 'first-cell', [self.sight['id']], P, key_dir=KEYS)
        two = holon.publish(self.hq, 'first-cell', [self.sight['id']], P, key_dir=KEYS)
        self.assertEqual(two['published'], [self.sight['id']])
        self.assertTrue(two['publish_line'] and two['publish_line'] != one['publish_line'])
        with open(os.path.join(self.cell, 'published', record.actor_file(P)), encoding='utf-8') as fh:
            self.assertEqual(sum(1 for x in fh if json.loads(x)['id'] == self.sight['id']), 1)

    def test_non_default_audience(self):
        out = holon.publish(self.hq, 'first-cell', [self.sight['id']], P, audience='public', key_dir=KEYS)
        pub = [l for l in self.publish_lines() if l['id'] == out['publish_line']][0]
        self.assertEqual(pub['body']['audience'], 'public')
        self.assertEqual(self.fold_cell()['audience'][self.sight['id']], 'public')
        with self.assertRaises(ValueError):
            holon.publish(self.hq, 'first-cell', [self.sight['id']], P, audience='everyone')

    def test_publish_face_refuses_a_broken_copy(self):
        bad = dict({k: v for k, v in self.sight.items()}, type='commit')
        out = holon.publish_face(self.hq, 'first-cell', [bad, 'x'], P, key_dir=KEYS)
        self.assertEqual(out['published'], [])
        self.assertIsNone(out['publish_line'])
        self.assertEqual([h['why'] for h in out['held_back']],
                         ['its id does not verify against its content', 'not a line'])


class TestWriteFace(Base):
    """Laws 3, 4 and 5 over the real fold: a person writes, an agent dry-runs, twice writes once."""

    def test_person_writes_and_the_cell_vouches(self):
        aid = self.agree()
        res = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertTrue(res['ok'], res['said'])
        self.assertEqual(res['cell'], 'first-cell')
        self.assertIn(self.sight['id'], res['published'])
        pub = [l for l in self.publish_lines() if l['id'] == res['publish_line']][0]
        self.assertEqual(pub['links']['serves'], [aid])
        self.assertEqual(self.fold_cell()['trust'][self.sight['id']], 'vouched')

    def test_an_invalid_line_stays_home(self):
        aid = self.agree()
        bad = record.append(self.hq, A, P, 'commit', {'card': '2' * 64, 'by': '2026-11-01'}, audience='members',
                            reason='delegated', ts='2026-10-21T09:01:00-07:00', key_dir=KEYS)['line']
        res = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertNotIn(bad['id'], res['published'])
        self.assertIn('does not let it act', {h['id']: h['why'] for h in res['held_back']}[bad['id']])
        self.assertNotIn(bad['id'], {l['id'] for l in record.read(self.cell)['lines']})

    def test_field_elision_in_the_cell(self):
        aid = self.agree(crosses=['sight'], permits={'write': False, 'fields': {'sight': ['kind']}})
        res = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertTrue(res['ok'], res['said'])
        self.assertEqual(res['elided'], {self.sight['id']: ['text', 'where']})
        copy = [l for l in record.read(self.cell)['lines'] if l['id'] == self.sight['id']][0]
        self.assertTrue(record.check_id(copy))
        self.assertNotIn('the ford', json.dumps(copy))
        pub = [l for l in self.publish_lines() if l['id'] == res['publish_line']][0]
        self.assertEqual(pub['body']['elided'], {self.sight['id']: ['text', 'where']})
        self.assertEqual(self.fold_cell()['trust'][self.sight['id']], 'vouched')

    def test_a_named_face_not_joined_is_refused(self):
        before = len(self.publish_lines())
        res = faces.write_face(self.hq, IDS['agreement'], P, key_dir=KEYS)   # the fixture's face names "cell"
        self.assertFalse(res['ok'])
        self.assertIn('no joined cell', res['said'])
        self.assertEqual(len(self.publish_lines()), before)
        self.assertNotIn(self.sight['id'], {l['id'] for l in record.read(self.cell)['lines']})

    def test_the_named_face_wins_over_with(self):
        second = self.second_cell()
        aid = self.agree(face='second')
        res = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertTrue(res['ok'], res['said'])
        self.assertEqual(res['cell'], 'second')
        self.assertIn(self.sight['id'], {l['id'] for l in record.read(second)['lines']})
        self.assertNotIn(self.sight['id'], {l['id'] for l in record.read(self.cell)['lines']})

    def test_a_widening_counts_only_for_its_cell(self):
        self.second_cell()
        quiet = record.append(self.hq, P, P, 'sight', {'text': 'kept quiet', 'kind': 'wonder'},
                              ts='2026-10-21T09:02:00-07:00', key_dir=KEYS)['line']           # audience holon
        holon.publish(self.hq, 'first-cell', [quiet['id']], P, key_dir=KEYS)                  # widened for first-cell
        to_second = self.agree(face='second')
        to_first = self.agree(face='first-cell')
        res = faces.write_face(self.hq, to_second, P, dry=True)
        self.assertNotIn(quiet['id'], res['published'])
        self.assertIn('audience is holon', {h['id']: h['why'] for h in res['held_back']}[quiet['id']])
        res = faces.write_face(self.hq, to_first, P, dry=True)
        self.assertIn(quiet['id'], res['already'])

    def test_agent_refused_in_words_dry_allowed(self):
        aid = self.agree()
        before = sorted(os.listdir(os.path.join(self.cell, 'published')))
        n = len(self.publish_lines())
        res = faces.write_face(self.hq, aid, A, key_dir=KEYS)
        self.assertFalse(res['ok'])
        self.assertIn('written by a person', res['said'])
        dry = faces.write_face(self.hq, aid, A, dry=True)
        self.assertTrue(dry['ok'])
        self.assertIn(self.sight['id'], dry['published'])
        self.assertIn('nothing was written', dry['said'])
        self.assertEqual(len(self.publish_lines()), n)
        self.assertEqual(sorted(os.listdir(os.path.join(self.cell, 'published'))), before)
        self.assertNotIn(self.sight['id'], {l['id'] for l in record.read(self.cell)['lines']})

    def test_only_a_party_admitted_here(self):
        aid = self.agree()
        res = faces.write_face(self.hq, aid, 'person:stranger', key_dir=KEYS)
        self.assertFalse(res['ok'])
        self.assertIn('neither', res['said'])
        res = faces.write_face(self.hq, aid, S, key_dir=KEYS)   # agreed it, but not admitted in this home
        self.assertFalse(res['ok'])

    def test_idempotent(self):
        aid = self.agree()
        one = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        n = len(self.publish_lines())
        path = os.path.join(self.cell, 'published', record.actor_file(P))
        with open(path, encoding='utf-8') as fh:
            size = fh.read()
        two = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertTrue(two['ok'])
        self.assertEqual(two['published'], [])
        self.assertIsNone(two['publish_line'])
        self.assertIn(self.sight['id'], two['already'])
        self.assertIn('Nothing new', two['said'])
        self.assertEqual(len(self.publish_lines()), n)
        with open(path, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), size)
        self.assertTrue(one['published'])

    def test_a_copy_without_its_publish_line_is_vouched_on_the_next_write(self):
        aid = self.agree()
        path = os.path.join(self.cell, 'published', record.actor_file(P))
        with open(path, 'a', encoding='utf-8') as fh:                  # a write that stopped before its publish line
            fh.write(record.dumps(self.sight) + '\n')
        res = faces.write_face(self.hq, aid, P, key_dir=KEYS)
        self.assertIn(self.sight['id'], res['published'])
        with open(path, encoding='utf-8') as fh:
            self.assertEqual(sum(1 for x in fh if json.loads(x)['id'] == self.sight['id']), 1)
        self.assertEqual(self.fold_cell()['trust'][self.sight['id']], 'vouched')

    def test_faces_counts(self):
        aid = self.agree()
        r = [x for x in faces.faces(self.hq) if x['agreement'] == aid][0]
        self.assertEqual((r['cell'], r['with']), ('first-cell', self.C))
        due = r['count_due']
        self.assertGreaterEqual(due, 1)
        faces.write_face(self.hq, aid, P, key_dir=KEYS)
        r2 = [x for x in faces.faces(self.hq) if x['agreement'] == aid][0]
        self.assertEqual(r2['count_due'], 0)
        self.assertEqual(r2['count_published'], r['count_published'] + due)
        fx = [x for x in faces.faces(self.hq) if x['agreement'] == IDS['agreement']][0]
        self.assertIsNone(fx['cell'])
        self.assertIn('no joined cell', fx['said'])

    def test_not_live_opens_nothing(self):
        record.append(self.cell, P, P, 'supersede', {}, {'supersedes': [IDS['agreement']]},
                      ts='2026-10-21T09:20:00-07:00', key_dir=KEYS)
        res = faces.write_face(self.hq, IDS['agreement'], P, key_dir=KEYS)
        self.assertFalse(res['ok'])
        self.assertIn('retracted', res['said'])
        self.assertEqual(faces.faces(self.hq), [])

    def test_deterministic(self):
        aid = self.agree()
        a = json.dumps(faces.write_face(self.hq, aid, A, dry=True), sort_keys=True)
        b = json.dumps(faces.write_face(self.hq, aid, A, dry=True), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(json.dumps(faces.faces(self.hq), sort_keys=True), json.dumps(faces.faces(self.hq), sort_keys=True))

    def test_cli(self):
        aid = self.agree()
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'faces.py'), self.hq, '--agreement',
                            aid[:12], '--dry', '--actor', A], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)['dry'])
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'faces.py'), 'plan', self.hq, '--agreement',
                            IDS['agreement'], '--forge', 'forgejo', '--owner', 'lionsberg', '--repo', 'first-cell',
                            '--collaborator', S], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        plan = json.loads(r.stdout)
        self.assertEqual(plan[0]['path'], '/api/v1/repos/lionsberg/first-cell/collaborators/steward')
        self.assertEqual(plan[0]['body'], {'permission': 'write'})      # the fixture Agreement permits write


class TestPermissionsPlan(unittest.TestCase):
    """Law 6: the right endpoint and permission for read and write, both forges; nothing is called."""

    def test_forgejo(self):
        p = faces.permissions_plan(row(), 'forgejo', 'lionsberg', 'cell-one', 'person:steward')
        self.assertEqual((p[0]['action'], p[0]['path'], p[0]['body']),
                         ('PUT', '/api/v1/repos/lionsberg/cell-one/collaborators/steward', {'permission': 'read'}))
        p = faces.permissions_plan(row(permits={'write': True}), 'Forgejo', 'lionsberg', 'cell-one', 'steward')
        self.assertEqual(p[0]['body'], {'permission': 'write'})
        self.assertNotIn('invitation', p[0]['why'])

    def test_github(self):
        p = faces.permissions_plan(row(), 'github', 'lionsberg', 'cell-one', 'steward')
        self.assertEqual((p[0]['action'], p[0]['path'], p[0]['body']),
                         ('PUT', '/repos/lionsberg/cell-one/collaborators/steward', {'permission': 'pull'}))
        p = faces.permissions_plan(row(permits={'write': True}), 'github', 'lionsberg', 'cell-one', 'steward')
        self.assertEqual(p[0]['body'], {'permission': 'push'})
        for words in ('invitation', '201', 'organization owns', 'pending invitation'):
            self.assertIn(words, p[0]['why'])

    def test_ending_and_placeholders(self):
        p = faces.permissions_plan(row(live=False, state='expired'), 'github', 'lionsberg', 'cell-one', 'steward')
        self.assertEqual((p[0]['action'], p[0]['body']), ('DELETE', None))
        self.assertIn('expired', p[0]['why'])
        self.assertIn('invitation not yet accepted', p[0]['why'])
        p = faces.permissions_plan(row(), 'forgejo')
        self.assertEqual(p[0]['path'], '/api/v1/repos/{owner}/{repo}/collaborators/{collaborator}')
        self.assertIn('owner is not named', p[0]['why'])
        for bad in (('gitlab', 'o', 'r', 'c'), ('github', '../o', 'r', 'c'), ('github', 'o', 'r', 'c d')):
            self.assertEqual(faces.permissions_plan(row(), *bad)[0]['action'], 'none', bad)

    def test_calls_nothing(self):
        with open(os.path.join(ENGINE, 'faces.py'), encoding='utf-8') as fh:
            src = fh.read()
        imports = re.findall(r'^\s*(?:import|from)\s+([\w.]+)', src, re.M)
        for banned in ('urllib', 'http', 'socket', 'subprocess', 'requests', 'ssl'):
            self.assertFalse([m for m in imports if m.split('.')[0] == banned], banned)
        self.assertNotIn('urllib', src)


class TestGuardsAndWords(unittest.TestCase):
    """Law 7: null-guards on every input; the kit's words; no one quoted."""

    def test_face_of_guards(self):
        for args in ((None, None, None), ({}, [], []), (row(), None, None), (row(), [None, 1, 'x', {}], [P]),
                     (row(crosses='sight', permits='x'), [mk('sight', {'text': 'x'})], P), (row(), [], 3.0)):
            out = fo(*args)
            self.assertEqual(sorted(out), ['basis', 'crosses', 'elided', 'held_back', 'lines', 'said'])
            json.dumps(out, sort_keys=True)
            out = faces.face_of(*args, trust=3.0, invalid='x')
            json.dumps(out, sort_keys=True)
        out = fo(row(crosses='sight'), [mk('sight', {'text': 'x'})], P)
        self.assertEqual(len(out['lines']), 1)                             # one name read as a list of one
        nfd = unicodedata.normalize('NFD', 'person:zoë')
        line = mk('sight', {'text': 'x'}, for_=unicodedata.normalize('NFC', nfd))
        self.assertEqual(len(fo(row(), [line], [nfd])['lines']), 1)

    def test_folders_guarded(self):
        tmp = tempfile.mkdtemp(prefix='lionsberg-faces-guard-')
        try:
            self.assertEqual(faces.faces(None), [])
            self.assertEqual(faces.faces(os.path.join(tmp, 'absent')), [])
            self.assertEqual(faces.faces(tmp), [])
            os.symlink(tmp, os.path.join(tmp, 'link'))
            self.assertEqual(faces.faces(os.path.join(tmp, 'link')), [])
            for d in (None, os.path.join(tmp, 'absent'), os.path.join(tmp, 'link'), tmp):
                res = faces.write_face(d, {'id': '1' * 64}, P)
                self.assertFalse(res['ok'])
                self.assertTrue(res['said'].endswith('.'))
            self.assertEqual(faces.permissions_plan(None, 'github')[0]['action'], 'none')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_words(self):
        with open(os.path.join(ENGINE, 'faces.py'), encoding='utf-8') as fh:
            src = fh.read()
        for word in ('promise', 'house', ' HQ', 'estate'):
            self.assertNotIn(word, src, word)
        self.assertNotIn('“', src)


if __name__ == '__main__':
    unittest.main()
