"""test_permitted.py — the permitted inbox: where a holon with a write permit may drop lines.

Each law of permitted.py has a test that fails when it is broken. The holons are made fresh for
each test in a temporary folder and signed with throwaway keys made once for the run.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_permitted.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import record      # noqa: E402
import holon       # noqa: E402
import permitted   # noqa: E402
import agreement   # noqa: E402

ALICE, BOB, MALLORY = 'person:alice', 'person:bob', 'person:mallory'
AIDE = 'agent:bob-aide'
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
HAVE_GIT = bool(shutil.which('git'))
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@test.invalid', '-c', 'commit.gpgsign=false']
WORK = KD = None


def setUpModule():
    global WORK, KD
    WORK = tempfile.mkdtemp(prefix='lionsberg-permitted-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KD = os.path.join(WORK, 'keys')
    os.makedirs(KD)
    if HAVE_KEYGEN:
        for a in (ALICE, BOB, MALLORY, AIDE):
            record.make_key(a, KD)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.n = 0

    def ts(self):
        self.n += 1
        return '2026-10-20T10:%02d:%02d-07:00' % (self.n // 60, self.n % 60)

    def put(self, d, actor, typ, body=None, links=None, for_=None, sub='record', audience='holon', reason=None,
            ts=None):
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        r = record.append(d, actor, for_ or actor, typ, body, links, audience, reason, ts=ts or self.ts(), sub=sub,
                          key_dir=KD)
        return r['line']

    def world(self, permits=None, crosses=None, agreed=True, until=None):
        """Alice's holon (the one with the inbox) holds Bob's holon under cells/; Bob is admitted in Alice's."""
        self.a = os.path.join(self.tmp, 'alice')
        holon.init(self.a, 'alice', 'person', ALICE, ts=self.ts(), key_dir=KD)
        self.b = os.path.join(self.a, 'cells', 'bob')
        holon.init(self.b, 'bob', 'person', BOB, ts=self.ts(), key_dir=KD)
        self.A, self.B = record.holon_info(self.a)['id'], record.holon_info(self.b)['id']
        holon.admit(self.a, ALICE, BOB, record.pubkey_of(record.find_key(None, BOB, KD)), ts=self.ts(), key_dir=KD)
        self.agreement = None
        if permits is not None:
            body = {'with': self.B, 'permits': permits, 'terms': 'what each may drop into the other'}
            if crosses:
                body['crosses'] = crosses
            if until:
                body['until'] = until
            self.agreement = self.put(self.a, ALICE, 'agree', body)['id']
            if agreed:
                self.put(self.a, BOB, 'agree', {'with': self.A}, {'answers': [self.agreement]})

    def fold(self, clock=CLOCK):
        return record.fold_hq(self.a, clock=clock)

    def unverified(self, f):
        return {x['id']: x['said'] for x in f['unverified']}


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the lines are signed')
class TestTrust(Base):
    """Law 1: a permitted line counts only under a write permit; law 4: never wider than members."""

    def test_no_permit_is_unverified(self):
        self.world()                                         # admitted, signed, and no Agreement
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        f = self.fold()
        self.assertEqual(f['trust'][line['id']], 'unverified')
        self.assertIn('no write permit', self.unverified(f)[line['id']])

    def test_an_agreement_without_write_grants_nothing(self):
        self.world(permits={'write': False})
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        self.assertIn('no write permit', self.unverified(self.fold())[line['id']])

    def test_a_proposed_agreement_grants_nothing(self):
        self.world(permits={'write': True}, agreed=False)
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        self.assertIn('no write permit', self.unverified(self.fold())[line['id']])

    def test_with_the_permit_it_counts(self):
        self.world(permits={'write': True})
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        f = self.fold()
        self.assertEqual(f['trust'][line['id']], 'signed')
        self.assertNotIn(line['id'], self.unverified(f))
        self.assertTrue(any(line['id'] in t.get('events', []) for t in f['threads']))

    def test_read_marks_the_line(self):
        self.world(permits={'write': True})
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        got = [l for l in record.read(self.a)['lines'] if l['id'] == line['id']][0]
        self.assertTrue(got['_permitted'])
        self.assertEqual(got['_held_in'], self.A)
        self.assertEqual(got['_file'], 'permitted/' + record.actor_file(BOB))

    def test_the_permit_reaches_the_persons_agent(self):
        self.world(permits={'write': True})
        self.put(self.a, BOB, 'affirm', {'agent': AIDE, 'pubkey': record.pubkey_of(record.find_key(None, AIDE, KD))})
        line = self.put(self.a, AIDE, 'say', {'text': 'from the aide'}, for_=BOB, sub='permitted')
        self.assertEqual(self.fold()['trust'][line['id']], 'signed')

    def test_a_stranger_is_never_let_in(self):
        self.world(permits={'write': True})
        line = self.put(self.a, MALLORY, 'say', {'text': 'let me in'}, sub='permitted')
        self.assertEqual(self.fold()['trust'][line['id']], 'unverified')

    def test_an_unsigned_permitted_line_never_counts(self):
        self.world(permits={'write': True})
        r = record.append(self.a, BOB, BOB, 'say', {'text': 'unsigned'}, ts=self.ts(), sub='permitted', sign=False)
        self.assertEqual(self.fold()['trust'][r['line']['id']], 'unverified')

    def test_public_is_refused(self):
        self.world(permits={'write': True})
        line = self.put(self.a, BOB, 'say', {'text': 'to everyone'}, sub='permitted', audience='public')
        f = self.fold()
        self.assertEqual(f['trust'][line['id']], 'unverified')
        self.assertIn('wider than members', self.unverified(f)[line['id']])
        ok = self.put(self.a, BOB, 'say', {'text': 'to members'}, sub='permitted', audience='members')
        self.assertEqual(self.fold()['trust'][ok['id']], 'signed')

    def test_crosses_names_the_types(self):
        self.world(permits={'write': True}, crosses=['request'])
        line = self.put(self.a, BOB, 'say', {'text': 'not named'}, sub='permitted')
        said = self.unverified(self.fold())[line['id']]
        self.assertIn('no write permit', said)
        self.assertIn('crosses', said)

    def test_the_inbox_never_admits(self):
        self.world(permits={'write': True})
        line = self.put(self.a, BOB, 'join', {'who': MALLORY, 'role': 'member'}, sub='permitted')
        f = self.fold()
        self.assertEqual(f['trust'][line['id']], 'unverified')
        self.assertNotIn(MALLORY, f['admitted'].get(self.A, {}))

    def test_the_inbox_cannot_grant_itself_a_permit(self):
        self.world(permits={'write': True}, agreed=False)
        self.put(self.a, BOB, 'agree', {'with': self.A}, {'answers': [self.agreement]}, sub='permitted')
        line = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        self.assertIn('no write permit', self.unverified(self.fold())[line['id']])

    def test_a_line_for_another_holon_never_acts_here(self):
        self.world(permits={'write': True})
        other = record.make_line(BOB, BOB, self.B, 'say', {'text': 'for bob\'s own'}, ts=self.ts(), salt='x')
        other['sig'] = record.sign_id(other['id'], record.find_key(None, BOB, KD))
        with record.open_append_nofollow(self.a, 'permitted', record.actor_file(BOB)) as fh:
            fh.write(record.dumps(other) + '\n')
        self.assertEqual(self.fold()['trust'][other['id']], 'wrong_holon')

    def test_an_expired_agreement_grants_nothing(self):
        self.world(permits={'write': True}, until='2026-10-20T23:00:00-07:00')
        line = self.put(self.a, BOB, 'say', {'text': 'after the until'}, sub='permitted',
                        ts='2026-10-30T10:00:00-07:00')
        f = self.fold(clock='2026-10-31T12:00:00-07:00')
        self.assertEqual(f['trust'][line['id']], 'unverified')
        self.assertIn('no write permit', self.unverified(f)[line['id']])
        self.assertEqual([x['id'] for x in permitted.triage(self.a)['accepted']], [])

    def test_a_person_never_borrows_anothers_name(self):
        self.world(permits={'write': True})
        holon.admit(self.a, ALICE, MALLORY, record.pubkey_of(record.find_key(None, MALLORY, KD)), ts=self.ts(),
                    key_dir=KD)
        borrowed = self.put(self.a, MALLORY, 'say', {'text': 'as if for bob'}, for_=BOB, sub='permitted')
        f = self.fold()
        self.assertEqual(f['trust'][borrowed['id']], 'unverified')
        self.assertIn('no write permit', self.unverified(f)[borrowed['id']])

    def test_a_copy_in_an_inbox_never_turns_the_real_line_wrong_holon(self):
        self.world()
        z = os.path.join(self.a, 'cells', 'zeta')
        holon.init(z, 'zeta', 'cell', BOB, ts=self.ts(), key_dir=KD)
        real = self.put(z, BOB, 'say', {'text': 'bob in zeta'})
        self.assertEqual(self.fold()['trust'][real['id']], 'signed')
        for sub in ('permitted', 'record'):        # record/ had the same hole
            with record.open_append_nofollow(self.a, sub, record.actor_file(BOB)) as fh:
                fh.write(record.dumps(real) + '\n')
            f = self.fold()
            self.assertEqual(f['trust'][real['id']], 'signed', sub)
            kept = [l for l in record.read_all(self.a)['lines'] if l['id'] == real['id']]
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0]['_held_in'], record.holon_info(z)['id'])

    def test_a_narrowing_answer_never_enters_by_the_inbox(self):
        self.world(permits={'write': True})
        narrow = self.put(self.a, ALICE, 'agree', {'with': self.B, 'permits': {'write': False}, 'terms': 'narrowed'})
        answer = self.put(self.a, BOB, 'agree', {'with': self.A}, {'answers': [narrow['id']]}, sub='permitted')
        say = self.put(self.a, BOB, 'say', {'text': 'still here'}, sub='permitted')
        f = self.fold()
        self.assertEqual(f['trust'][answer['id']], 'unverified')
        self.assertIn('never enters', self.unverified(f)[answer['id']])
        self.assertEqual(agreement.between(f, self.A, self.B)['id'], self.agreement)   # the whole fold and the permit agree
        self.assertEqual(f['trust'][say['id']], 'signed')

    def test_supersede_of_an_agreement_and_witness_of_a_join_never_enter(self):
        self.world(permits={'write': True})
        f = self.fold()
        answer = [x for x in f['agreements'] if x['id'] == self.agreement][0]['events'][-1]
        join = f['admitted'][self.A][BOB]['by']
        sup = self.put(self.a, BOB, 'supersede', {}, {'supersedes': [answer]}, sub='permitted')
        wit = self.put(self.a, BOB, 'witness', {}, {'witnesses': [join]}, sub='permitted')
        u = self.unverified(self.fold())
        self.assertIn('supersede naming an agree', u[sup['id']])
        self.assertIn('witness naming a join', u[wit['id']])

    def test_record_and_permitted_are_one_chain(self):
        self.world(permits={'write': True})
        ids = [self.put(self.a, BOB, 'say', {'text': 't%d' % i}, sub=('record', 'permitted')[i % 2])['id']
               for i in range(4)]
        r = record.read(self.a)
        self.assertFalse([p for p in r['problems'] if p['kind'] in ('broken_chain', 'fork')], r['problems'])
        self.assertEqual(r['heads'][BOB], [ids[-1]])
        f = self.fold()
        self.assertEqual(f['forks'], [])
        self.assertTrue(all(f['trust'][i] == 'signed' for i in ids))

    def test_triage_folds_once_more_not_three_times(self):
        self.world(permits={'write': True})
        self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        with mock.patch.object(record, 'fold', wraps=record.fold) as spy:
            t = permitted.triage(self.a)
        self.assertEqual(spy.call_count, 2)          # the whole fold, and the one it makes for the permit
        self.assertEqual(t['accepted'][0]['agreement'], self.agreement)
        with mock.patch.object(record, 'fold', wraps=record.fold) as spy:
            permitted.permits(self.a)
        self.assertEqual(spy.call_count, 2)

    def test_triage_and_permits(self):
        self.world(permits={'write': True})
        good = self.put(self.a, BOB, 'say', {'text': 'hello'}, sub='permitted')
        wide = self.put(self.a, BOB, 'say', {'text': 'wide'}, sub='permitted', audience='public')
        t = permitted.triage(self.a)
        self.assertEqual([x['id'] for x in t['accepted']], [good['id']])
        self.assertEqual(t['accepted'][0]['agreement'], self.agreement)
        self.assertEqual([x['id'] for x in t['refused']], [wide['id']])
        self.assertIn('wider than members', t['refused'][0]['why'])
        self.assertIn('as_of', t)
        self.assertEqual(json.dumps(t, sort_keys=True), json.dumps(permitted.triage(self.a), sort_keys=True))
        p = permitted.permits(self.a)
        self.assertEqual(p[self.B], {'write': True, 'agreement': self.agreement})
        self.assertEqual(p[BOB], {'write': True, 'agreement': self.agreement})
        self.assertNotIn(ALICE, p)

    def test_permits_is_honest_empty(self):
        self.world()
        self.assertEqual(permitted.permits(self.a), {})
        t = permitted.triage(self.a)
        self.assertEqual(t['accepted'], [])
        self.assertIn('no line', t['said'])

    def test_append_chains_the_permitted_file(self):
        self.world(permits={'write': True})
        one = self.put(self.a, BOB, 'say', {'text': 'one'}, sub='permitted')
        two = self.put(self.a, BOB, 'say', {'text': 'two'}, sub='permitted')
        self.assertEqual(two['prev'], one['id'])
        self.assertEqual(self.fold()['forks'], [])

    def test_the_cli(self):
        self.world(permits={'write': True})
        line = record.make_line(BOB, BOB, self.A, 'say', {'text': 'by hand'}, ts=self.ts(), salt='c',
                                prev=record.last_line(os.path.join(self.a, 'record', record.actor_file(BOB)))['id'])
        line['sig'] = record.sign_id(line['id'], record.find_key(None, BOB, KD))
        path = os.path.join(self.tmp, 'line.jsonl')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(record.dumps(line) + '\n')
        run = lambda *a: subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'permitted.py')] + list(a),
                                        capture_output=True, text=True, timeout=120)
        r = run('drop', self.a, path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)[0]['ok'])
        r = run('triage', self.a)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x['id'] for x in json.loads(r.stdout)['accepted']], [line['id']])


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the lines are signed')
class TestDrop(Base):
    """Law 3: drop never follows a link, refuses unsigned and oversized lines, never the holon's own file."""

    def signed(self, actor=BOB, holon_id=None, body=None, audience='holon', typ='say'):
        l = record.make_line(actor, actor, holon_id or self.A, typ, body or {'text': 'dropped'}, audience=audience,
                             ts=self.ts(), salt='d%d' % self.n)
        l['sig'] = record.sign_id(l['id'], record.find_key(None, actor, KD))
        return l

    def test_drop_and_idempotent(self):
        self.world(permits={'write': True})
        l = self.signed()
        r = permitted.drop(self.a, l)
        self.assertTrue(r['ok'], r['said'])
        self.assertTrue(r['file'].endswith(os.path.join('permitted', record.actor_file(BOB))))
        again = permitted.drop(self.a, record.dumps(l))
        self.assertTrue(again['ok'])
        self.assertIn('already held', again['said'])
        with open(r['file'], encoding='utf-8') as fh:
            self.assertEqual(len([x for x in fh if x.strip()]), 1)

    def test_refusals(self):
        self.world(permits={'write': True})
        unsigned = dict(self.signed(), sig='')
        self.assertIn('unsigned', permitted.drop(self.a, unsigned)['said'])
        big = record.make_line(BOB, BOB, self.A, 'say', {'text': 'x' * (record.MAX_LINE + 10)}, salt='b')
        big['sig'] = 'ssh-ed25519:AAAA'
        self.assertIn('longer than', permitted.drop(self.a, big)['said'])
        self.assertIn('longer than', permitted.drop(self.a, record.dumps(big))['said'])
        self.assertIn('own', permitted.drop(self.a, self.signed(actor=ALICE))['said'])
        self.assertIn('another holon', permitted.drop(self.a, self.signed(holon_id=self.B))['said'])
        self.assertIn('wider than members', permitted.drop(self.a, self.signed(audience='public'))['said'])
        self.assertIn('never enters', permitted.drop(self.a, self.signed(typ='join', body={'who': MALLORY}))['said'])
        forged = dict(self.signed(), ts='2026-01-01T00:00:00-07:00')
        self.assertIn('id does not verify', permitted.drop(self.a, forged)['said'])
        self.assertFalse(os.path.exists(os.path.join(self.a, 'permitted', record.actor_file(ALICE))))

    def test_never_through_a_link(self):
        self.world(permits={'write': True})
        outside = os.path.join(self.tmp, 'outside')
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.a, 'permitted'))
        r = permitted.drop(self.a, self.signed())
        self.assertFalse(r['ok'])
        self.assertEqual(os.listdir(outside), [])
        os.remove(os.path.join(self.a, 'permitted'))
        os.makedirs(os.path.join(self.a, 'permitted'))
        target = os.path.join(outside, 'planted.jsonl')
        os.symlink(target, os.path.join(self.a, 'permitted', record.actor_file(BOB)))
        r = permitted.drop(self.a, self.signed())
        self.assertFalse(r['ok'])
        self.assertFalse(os.path.exists(target))
        link = os.path.join(self.tmp, 'alias')
        os.symlink(self.a, link)
        self.assertFalse(permitted.drop(link, self.signed())['ok'])
        self.assertTrue(any(p['kind'] == 'symlink' for p in record.read(self.a)['problems']))


@unittest.skipUnless(HAVE_GIT, 'git is needed for the pull gate')
class TestGate(Base):
    """Law 2: the pull gate takes an append to permitted/<other> by its own actor, and nothing else."""

    def g(self, d, *a):
        return subprocess.run(GIT + ['-C', d] + list(a), capture_output=True, text=True)

    def gate_world(self, seed_permitted=False):
        bare = os.path.join(self.tmp, 'cell.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare], check=True)
        seed = os.path.join(self.tmp, 'seed')
        holon.init(seed, 'cell', 'cell', 'person:carol', sign=False)
        if seed_permitted:
            self.raw(seed, BOB, BOB)
        subprocess.run(['git', 'init', '-q', '-b', 'main', seed], check=True)
        self.g(seed, 'add', '-A'); self.g(seed, 'commit', '-qm', 'inception')
        self.g(seed, 'push', '-q', bare, 'HEAD:main')
        hq = os.path.join(self.tmp, 'alice')
        holon.init(hq, 'alice', 'person', ALICE, sign=False)
        res = holon.join(hq, bare, 'cell', actor=ALICE)
        self.assertTrue(res['ok'], res['said'])
        other = os.path.join(self.tmp, 'other')
        subprocess.run(['git', 'clone', '-q', bare, other], check=True)
        return hq, res['path'], other

    def raw(self, d, file_actor, actor, name=None, for_=None):
        """An unsigned line by `actor` appended to permitted/<file_actor's file> (the gate reads paths, not keys)."""
        self.n += 1
        l = record.make_line(actor, for_ or actor, record.holon_info(d).get('id', ''), 'say',
                             {'text': 'n%d' % self.n}, salt='g%d' % self.n)
        os.makedirs(os.path.join(d, 'permitted'), exist_ok=True)
        with open(os.path.join(d, 'permitted', name or record.actor_file(file_actor)), 'a', encoding='utf-8') as fh:
            fh.write(record.dumps(l) + '\n')
        return l

    def send(self, d, msg):
        self.g(d, 'add', '-A'); self.g(d, 'commit', '-qm', msg)
        return self.g(d, 'push', '-q')

    def test_join_takes_a_permitted_file(self):
        hq, mine, _other = self.gate_world(seed_permitted=True)
        self.assertTrue(os.path.isfile(os.path.join(mine, 'permitted', record.actor_file(BOB))))

    def test_an_append_by_its_own_actor_is_taken(self):
        hq, mine, other = self.gate_world()
        l = self.raw(other, BOB, BOB)
        self.send(other, 'bob drops')
        res = holon.pull(hq)
        self.assertTrue(res[0]['ok'], res)
        self.assertIn(l['id'], {x['id'] for x in record.read(mine)['lines']})
        self.raw(other, BOB, BOB)
        self.send(other, 'bob again')
        self.assertTrue(holon.pull(hq)[0]['ok'])

    def test_an_agents_line_for_its_person_is_taken(self):
        hq, mine, other = self.gate_world()
        l = self.raw(other, AIDE, AIDE, for_=BOB)
        self.send(other, 'the aide drops for bob')
        res = holon.pull(hq)
        self.assertTrue(res[0]['ok'], res)
        self.assertIn(l['id'], {x['id'] for x in record.read(mine)['lines']})

    def test_the_homes_own_file_is_refused(self):
        hq, mine, other = self.gate_world()
        self.raw(other, ALICE, ALICE)
        self.send(other, 'as alice')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn("home's own file", res[0]['said'])

    def test_another_actor_in_the_file_is_refused(self):
        hq, mine, other = self.gate_world()
        self.raw(other, BOB, MALLORY)
        self.send(other, 'mallory in bob')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('its own actor', res[0]['said'])

    def test_a_deleted_line_is_refused(self):
        hq, mine, other = self.gate_world()
        self.raw(other, BOB, BOB)
        self.raw(other, BOB, BOB)
        self.send(other, 'two')
        self.assertTrue(holon.pull(hq)[0]['ok'])
        path = os.path.join(other, 'permitted', record.actor_file(BOB))
        with open(path, encoding='utf-8') as fh:
            first = fh.readline()
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(first)
        self.send(other, 'drop one')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('changed or removed', res[0]['said'])

    def test_a_path_outside_the_layout_is_refused(self):
        hq, mine, other = self.gate_world()
        os.makedirs(os.path.join(other, 'permitted', 'deeper'))
        with open(os.path.join(other, 'permitted', 'deeper', 'x.jsonl'), 'w', encoding='utf-8') as fh:
            fh.write('{}\n')
        self.send(other, 'deeper')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('outside', res[0]['said'])
        self.assertFalse(os.path.exists(os.path.join(mine, 'permitted', 'deeper')))


class TestGitignore(unittest.TestCase):
    """A new home keeps the heartbeat's state and logs on the machine."""

    def test_a_new_home_ignores_the_heartbeat(self):
        h = os.path.join(tempfile.mkdtemp(dir=WORK), 'home')
        holon.init(h, 'home', 'person', 'person:carol', sign=False)
        with open(os.path.join(h, '.gitignore'), encoding='utf-8') as fh:
            names = set(fh.read().split())
        for n in ('.heartbeat.json', '.heartbeat-log.jsonl', '.pull-log.jsonl', 'heartbeat/', '.pulled.json',
                  'state.json', '.sigcache'):
            self.assertIn(n, names)


class TestGuards(unittest.TestCase):
    """Law 6: null-guards, the kit's words, no one quoted."""

    def test_allowed_guards(self):
        for line, ctx in ((None, None), ({}, None), ({}, {}), ({'actor': 3.5}, {'holon': 'h'}),
                          ({'actor': 'person:x', 'holon': 'h'}, {'items': []}),
                          ({'actor': 'person:x', 'holon': 'h', 'audience': 1.5}, {'items': {'admitted': None}})):
            ok, why = permitted.allowed(line, ctx)
            self.assertFalse(ok)
            self.assertTrue(isinstance(why, str) and why)
        nfd = {'actor': 'person:josé', 'holon': 'h', 'type': 'say'}
        ok, why = permitted.allowed(nfd, {'holon': 'h', 'items': {'admitted': {'h': {'person:josé': {}}}}})
        self.assertFalse(ok)
        self.assertIn('no write permit', why)

    def test_drop_guards(self):
        tmp = tempfile.mkdtemp(dir=WORK)
        for target, line in ((None, None), ('', {}), (tmp, {}), (os.path.join(tmp, 'absent'), {}), (3.5, [])):
            self.assertFalse(permitted.drop(target, line)['ok'])
        h = os.path.join(tmp, 'h')
        holon.init(h, 'h', 'cell', 'person:carol', sign=False)
        for line in (None, 3.5, [], {}, 'not json', b'{"a": 1.5}', '{"a": 1}'):
            r = permitted.drop(h, line)
            self.assertFalse(r['ok'])
            self.assertTrue(r['said'])

    def test_triage_and_permits_guards(self):
        for d in (None, '', 3.5, '/no/such/holon'):
            t = permitted.triage(d)
            self.assertEqual((t['accepted'], t['refused']), ([], []))
            self.assertEqual(permitted.permits(d), {})
        tmp = tempfile.mkdtemp(dir=WORK)
        link = os.path.join(tmp, 'link')
        os.symlink(tmp, link)
        self.assertEqual(permitted.permits(link), {})

    def test_words(self):
        with open(os.path.join(ENGINE, 'permitted.py'), encoding='utf-8') as fh:
            text = fh.read()
        for w in ('house', 'estate', 'promise'):
            self.assertIsNone(re.search(r'\b%s' % w, text, re.I), w)
        self.assertNotIn('HQ', text)
        self.assertNotIn('“', text)    # no one is quoted


if __name__ == '__main__':
    unittest.main()
