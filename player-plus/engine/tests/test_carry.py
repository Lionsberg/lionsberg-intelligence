"""test_carry.py — carriers: how a signed line reaches everyone it is for; and stops.

Each law of carry.py (and of stops.py, which it reads) has a test that fails when it is broken.
The holons are made fresh for each test in a temporary folder and signed with throwaway keys
made once for the run.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_carry.py -v
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import record      # noqa: E402
import holon       # noqa: E402
import carry       # noqa: E402
import stops       # noqa: E402

P, S, T3, F4, X = 'person:player', 'person:steward', 'person:third', 'person:fourth', 'person:stranger'
AIDE = 'agent:player-aide'
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KD = None


def setUpModule():
    global WORK, KD
    WORK = tempfile.mkdtemp(prefix='lionsberg-carry-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KD = os.path.join(WORK, 'keys')
    os.makedirs(KD)
    if HAVE_KEYGEN:
        for a in (P, S, T3, F4, X, AIDE):
            record.make_key(a, KD)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def pk(actor):
    return record.pubkey_of(record.find_key(None, actor, KD))


def fake_directory(people):
    """A stand-in for directory.py (L3's interface: read, resolve), for the tests only."""
    m = types.ModuleType('directory')

    def read(d):
        return {'people': people, 'agents': {}, 'holons': {}, 'memberships': {}, 'problems': []}

    def resolve(d, address):
        rec = (d.get('people') or {}).get(address)
        if rec is None:
            return {'kind': 'person', 'ids': [], 'agents': [], 'fallbacks': [], 'said': 'not in the directory'}
        fb = [{'person': address, 'fallback': rec['fallback']}] if rec.get('fallback') and not rec.get('agents') else []
        return {'kind': 'person', 'ids': [address], 'agents': list(rec.get('agents') or []), 'fallbacks': fb,
                'said': 'carried by an agent' if fb else ''}

    m.read, m.resolve = read, resolve
    return m


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the lines are signed')
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.n = 0
        self.home = os.path.join(self.tmp, 'home')
        holon.init(self.home, 'home', 'person', P, ts=self.ts(), key_dir=KD)
        self.H = record.holon_info(self.home)['id']
        holon.affirm(self.home, P, AIDE, pk(AIDE), ts=self.ts(), key_dir=KD)
        self.cell = os.path.join(self.home, 'cells', 'first')
        holon.init(self.cell, 'first', 'cell', S, ts=self.ts(), key_dir=KD)
        self.C = record.holon_info(self.cell)['id']
        holon.admit(self.cell, S, P, pk(P), ts=self.ts(), key_dir=KD)

    def ts(self):
        self.n += 1
        return '2026-10-20T10:%02d:%02d-07:00' % (self.n // 60, self.n % 60)

    def put(self, d, actor, typ, body=None, links=None, for_=None, audience='holon', reason=None, sub='record'):
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        return record.append(d, actor, for_ or actor, typ, body, links, audience, reason, ts=self.ts(), sub=sub,
                             key_dir=KD)['line']

    def agree(self, crosses=('request', 'sight'), write=False, fields=None):
        """A live Agreement written in the cell: the player proposes, the steward answers."""
        permits = {'write': write}
        if fields:
            permits['fields'] = fields
        prop = self.put(self.cell, P, 'agree', {'with': self.C, 'crosses': list(crosses),
                                                'permits': permits, 'until': '2027-03-20'})
        self.put(self.cell, S, 'agree', {'with': self.H}, {'answers': [prop['id']]})
        return prop['id']

    def third(self, write=True):
        """A second cell, kept by a third person, whose Agreement grants this home a write permit."""
        self.tcell = os.path.join(self.home, 'cells', 'third')
        holon.init(self.tcell, 'third', 'cell', T3, ts=self.ts(), key_dir=KD)
        self.T = record.holon_info(self.tcell)['id']
        holon.admit(self.tcell, T3, P, pk(P), ts=self.ts(), key_dir=KD)
        prop = self.put(self.tcell, T3, 'agree', {'with': self.H, 'permits': {'write': write},
                                                   'terms': 'what each may drop into the other'})
        self.put(self.tcell, P, 'agree', {'with': self.T}, {'answers': [prop['id']]})

    def signed_for(self, holon_dir, actor, typ, body, audience='members'):
        """A signed line written for another holon, held only in memory until it is carried."""
        head = record._chain_head(holon_dir, record.actor_file(actor))
        line = record.make_line(actor, P, record.holon_info(holon_dir)['id'], typ, body, audience=audience,
                                reason='human' if actor.startswith('person:') else 'delegated',
                                prev=head['id'] if head else '', ts=self.ts())
        line['sig'] = record.sign_id(line['id'], record.find_key(None, actor, KD))
        return line

    def request(self, to, audience='members', **extra):
        body = dict({'text': 'can the hall hold forty', 'to': to}, **extra)
        return self.put(self.home, P, 'request', body, audience=audience)

    def plan(self, line, **kw):
        kw.setdefault('now', CLOCK)
        return carry.plan(line, self.home, **kw)

    def row(self, out, to):
        got = [d for d in out['deliveries'] if d['to'] == to]
        return got[0] if got else None

    def held(self, out, to):
        got = [h for h in out['held'] if h['to'] == to]
        return got[0]['why'] if got else None

    def raw_lines(self, path):
        with open(path, encoding='utf-8') as fh:
            return [x.rstrip('\n') for x in fh if x.strip()]


class TestOrder(Base):
    """Law 1: the carrier order holds, one test per carrier; a line that may not cross is held with why."""

    def test_face(self):
        aid = self.agree()
        line = self.request(S)
        r = self.row(self.plan(line), S)
        self.assertEqual(r['carrier'], 'face', self.plan(line))
        self.assertEqual((r['cell'], r['agreement'], r['holon'], r['basis']), ('first', aid, self.C, 'agreement'))
        self.assertEqual(r['where'], 'cells/first/published/' + record.actor_file(P))

    def test_held_when_the_agreement_does_not_let_it_cross(self):
        self.agree(crosses=('sight',))
        line = self.request(S)
        out = self.plan(line)
        self.assertIsNone(self.row(out, S))
        self.assertIn("does not name 'request' among what crosses", self.held(out, S))

    def test_held_when_no_agreement_stands(self):
        out = self.plan(self.request(S))
        self.assertIn('no live Agreement opens a face', self.held(out, S))

    def test_permitted(self):
        self.third()
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we use the hall', 'to': T3})
        r = self.row(self.plan(line), T3)
        self.assertEqual((r['carrier'], r['cell'], r['basis']), ('permitted', 'third', 'permit'))
        self.assertEqual(r['where'], 'cells/third/permitted/' + record.actor_file(P))

    def test_permitted_needs_the_write_permit(self):
        self.third(write=False)
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we use the hall', 'to': T3})
        self.assertIn('no write permit', self.held(self.plan(line), T3))

    def test_mail_then_pull(self):
        self.put(self.home, P, 'join', {'who': F4, 'pubkey': pk(F4), 'reach': ['mail:fourth@lan.test']})
        line = self.request(F4)
        r = self.row(self.plan(line), F4)
        self.assertEqual((r['carrier'], r['where'], r['basis']), ('mail', 'fourth@lan.test', 'reach (record)'))
        r = self.row(self.plan(line, mail_domains=['elsewhere.test']), F4)
        self.assertEqual((r['carrier'], r['where']), ('pull', 'record/'))   # pull is the floor

    def test_face_comes_before_mail(self):
        self.put(self.home, P, 'join', {'who': S, 'pubkey': pk(S), 'reach': ['mail:steward@lan.test']})
        line = self.request(S)
        self.assertEqual(self.row(self.plan(line), S)['carrier'], 'mail')
        self.agree()
        self.assertEqual(self.row(self.plan(line), S)['carrier'], 'face')

    def test_fallback_from_the_directory(self):
        fake = fake_directory({'person:ghost': {'id': 'person:ghost', 'fallback': 'the front desk at the hall'}})
        line = self.request('person:ghost')
        with mock.patch.dict(sys.modules, {'directory': fake}):
            out = self.plan(line, directory={'people': {'person:ghost': {'fallback': 'the front desk at the hall'}}})
        r = self.row(out, 'person:ghost')
        self.assertEqual((r['carrier'], r['where'], r['basis']), ('fallback', 'the front desk at the hall', 'directory'))
        self.assertEqual(r['draft']['sends'], 'person')
        self.assertIn('Carried by an agent', r['draft']['note'])

    def test_without_directory_py_the_record_is_read(self):
        with mock.patch.dict(sys.modules, {'directory': None}):
            out = self.plan(self.request('person:ghost'), directory=self.tmp)
        self.assertIn('directory.py is not here', out['said'])
        self.assertIn('No carrier reaches them', self.held(out, 'person:ghost'))

    def test_a_holon_address_reaches_its_members(self):
        self.agree()
        out = self.plan(self.request(self.C))
        self.assertEqual([d['to'] for d in out['deliveries']], [S])   # the sender's own are not recipients
        self.assertTrue(out['rate']['wide'])

    def test_pull_for_a_line_in_the_cell(self):
        line = self.put(self.cell, P, 'say', {'text': 'the hall holds forty', 'to': S}, audience='members')
        r = self.row(self.plan(line), S)
        self.assertEqual((r['carrier'], r['where'], r['holon']), ('pull', 'cells/first/record/', self.C))

    def test_only_the_homes_own_people(self):
        line = self.put(self.cell, S, 'say', {'text': 'hello', 'to': P})
        out = self.plan(line)
        self.assertEqual(out['deliveries'], [])
        self.assertIn('only a line of this home\'s own people', out['said'])

    def test_deterministic(self):
        self.agree()
        line = self.request([S, X])
        a, b = self.plan(line), self.plan(line)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertIn('No carrier reaches them', self.held(a, X))


class TestCopy(Base):
    """Law 2: the copy is byte-identical to the line; nothing is added to the line."""

    def test_permitted_copy_is_the_line(self):
        self.third()
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we use the hall', 'to': T3})
        before = copy.deepcopy(line)
        mem = dict(line, _carried={'hops': 1, 'by': AIDE, 'at': CLOCK})
        out = self.plan(mem)
        res = carry.drop(mem, self.home, self.row(out, T3), by=P, now=CLOCK)
        self.assertTrue(res['ok'], res['said'])
        self.assertEqual(line, before)
        self.assertEqual(self.raw_lines(res['file']), [record.dumps(line)])
        got = json.loads(self.raw_lines(res['file'])[0])
        self.assertEqual((got['id'], got['sig']), (line['id'], line['sig']))
        self.assertNotIn('_carried', got)
        self.assertEqual((res['carried']['hops'], res['carried']['by']), (2, P))
        # the home holds both sides, so its fold lets the dropped line count under the permit
        self.assertEqual(record.fold_hq(self.home, clock=CLOCK)['trust'][line['id']], 'signed')

    def test_face_copy_is_the_line(self):
        self.agree()
        line = self.request(S)
        res = carry.drop(line, self.home, self.row(self.plan(line), S), by=P, now=CLOCK, key_dir=KD)
        self.assertTrue(res['ok'], res['said'])
        home_raw = [x for x in self.raw_lines(os.path.join(self.home, 'record', record.actor_file(P)))
                    if json.loads(x)['id'] == line['id']]
        cell_raw = [x for x in self.raw_lines(res['file']) if json.loads(x)['id'] == line['id']]
        self.assertEqual(cell_raw, home_raw)


class TestRateAndHops(Base):
    """Law 3: the rate limits and the hop count hold; a line past MAX_HOPS is dropped and said."""

    def log(self, **e):
        entry = dict({'at': CLOCK, 'ok': True, 'by': P, 'carrier': 'permitted', 'line': 'e' * 64, 'to': S,
                      'hops_in': 0, 'hops': 1, 'wide': False}, **e)
        with open(os.path.join(self.home, carry.LOG), 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(entry) + '\n')

    def test_rate_per_day(self):
        self.agree()
        line = self.request(S)
        self.log()
        self.assertEqual(self.row(self.plan(line, limits={'RATE_PER_DAY': 2}), S)['carrier'], 'face')
        out = self.plan(line, limits={'RATE_PER_DAY': 1})
        self.assertIn('rate', self.held(out, S))
        self.assertEqual((out['rate']['today'], out['rate']['limit'], out['rate']['left']), (1, 1, 0))
        self.log(at='2026-10-22T12:00:00-07:00')                  # another day does not count
        self.assertEqual(self.plan(line, limits={'RATE_PER_DAY': 1})['rate']['today'], 1)
        self.assertEqual(carry.RATE_PER_DAY, 200)

    def test_rate_for_holon_wide_lines(self):
        self.agree()
        line = self.request(self.C)
        self.log(wide=True)
        out = self.plan(line, limits={'RATE_HOLON_PER_DAY': 1})
        self.assertIn('holon-wide', self.held(out, S))
        self.assertEqual(carry.RATE_HOLON_PER_DAY, 20)

    def test_past_max_hops_is_dropped(self):
        self.agree()
        line = self.request(S)
        out = self.plan(dict(line, _carried={'hops': 3}))
        self.assertTrue(out.get('dropped'))
        self.assertEqual(out['deliveries'], [])
        self.assertIn('MAX_HOPS', out['said'])
        self.assertEqual(self.plan(dict(line, _carried={'hops': 2}))['hops'], 3)
        self.log(line=line['id'], hops_in=3, hops=4)
        self.assertTrue(self.plan(line).get('dropped'))
        res = carry.drop(line, self.home, {'carrier': 'face', 'cell': 'first', 'to': S}, by=P, now=CLOCK)
        self.assertFalse(res['ok'])
        self.assertIn('MAX_HOPS', res['said'])


class TestNeverPushes(Base):
    """Law 4: drop never pushes; a face drop by an agent is refused."""

    def test_face_by_an_agent_is_refused(self):
        self.agree()
        line = self.request(S)
        with mock.patch.object(holon, 'push', side_effect=AssertionError('pushed')):
            res = carry.drop(line, self.home, self.row(self.plan(line), S), by=AIDE, now=CLOCK)
        self.assertFalse(res['ok'])
        self.assertIn('an agent may only propose it', res['said'])
        self.assertFalse(os.path.exists(os.path.join(self.cell, 'published', record.actor_file(P))))

    def test_every_carrier_says_it_never_pushed(self):
        self.third()
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we use the hall', 'to': T3})
        with mock.patch.object(holon, 'push', side_effect=AssertionError('pushed')):
            for carrier in carry.CARRIERS:
                row = dict(self.row(self.plan(line), T3), carrier=carrier)
                res = carry.drop(line, self.home, row, by=P, now=CLOCK)
                self.assertFalse(res['pushed'])
                self.assertIn('Nothing was pushed', res['said'])
        self.assertFalse(carry.drop(line, self.home, {'carrier': 'mail', 'where': 'a@b.test'}, by=P, now=CLOCK)['ok'])


class TestMayReply(unittest.TestCase):
    """Law 5: no automatic reply to an agent-drafted line."""

    def test_guard(self):
        agent = {'actor': AIDE, 'reason': 'delegated', 'body': {'text': 'hi'}}
        drafted = {'actor': AIDE, 'reason': 'human', 'body': {'text': 'hi'}}
        voiced = {'actor': P, 'reason': 'human', 'body': {'text': 'hi', 'voice': 'agent-drafted'}}
        human = {'actor': P, 'reason': 'human', 'body': {'text': 'hi'}}
        for l in (agent, drafted, voiced):
            ok, why = carry.may_reply(l, 'agent')
            self.assertFalse(ok, l)
            self.assertIn('without its person', why)
            self.assertFalse(carry.may_reply(l, None)[0])
            self.assertTrue(carry.may_reply(l, 'person')[0])
        self.assertTrue(carry.may_reply(human, 'agent')[0])
        self.assertFalse(carry.may_reply(None, 'agent')[0])


class TestStops(Base):
    """Stops: a stop by any person binds; only the agent's own person lifts it; a lift frees the delivery."""

    def stop(self, by=S, **body):
        body = dict({'agents': [AIDE], 'scope': self.C, 'why': 'hold every post until the hall is confirmed'}, **body)
        return self.put(self.cell, by, 'stop', body)

    def lift(self, by, stop_id):
        return self.put(self.cell, by, 'stop', {'lift': True, 'stop': stop_id}, {'answers': [stop_id]})

    def test_a_stop_by_another_person_binds_the_aide(self):
        self.agree()
        line = self.request(S)
        st = self.stop()
        out = self.plan(line, by=AIDE)
        self.assertIsNone(self.row(out, S))
        self.assertIn('A live stop by person:steward binds agent:player-aide', self.held(out, S))
        res = carry.drop(line, self.home, {'carrier': 'face', 'cell': 'first', 'to': S, 'holon': self.C}, by=AIDE,
                         now=CLOCK)
        self.assertTrue(res.get('stopped'))
        self.assertEqual(self.row(self.plan(line, by=P), S)['carrier'], 'face')   # it binds agents, not the person
        self.assertEqual([s['id'] for s in stops.live(record.fold_hq(self.home, clock=CLOCK), actor=AIDE)], [st['id']])

    def test_a_lift_by_anyone_else_counts_for_nothing(self):
        self.agree()
        line = self.request(S)
        st = self.stop()
        bad = self.lift(S, st['id'])
        f = record.fold_hq(self.home, clock=CLOCK)
        item = [x for x in f['stops'] if x['id'] == st['id']][0]
        # the fold keeps the lift rule: a lift by anyone but the aide's own person is refused, and the stop stays live
        self.assertEqual((item['state'], item.get('persons')), ('live', [P]))
        self.assertIsNone(item.get('lifted_by'))
        self.assertEqual([r['event'] for r in item.get('refused') or [] if 'not the right actor' in r['why']], [bad['id']])
        self.assertEqual([s['id'] for s in stops.live(f, actor=AIDE, home=self.H)], [st['id']])
        self.assertIsNone(self.row(self.plan(line, by=AIDE), S))

    def test_a_lift_by_the_agents_own_person_frees_it(self):
        self.agree()
        line = self.request(S)
        st = self.stop()
        self.lift(S, st['id'])            # first a lift that counts for nothing
        self.lift(P, st['id'])            # then the aide's own person
        self.assertEqual(self.row(self.plan(line, by=AIDE), S)['carrier'], 'face')
        f = record.fold_hq(self.home, clock=CLOCK)
        self.assertEqual([(x['state'], x['lifted_by']) for x in f['stops'] if x['id'] == st['id']], [('lifted', P)])
        self.assertEqual(stops.live(f, actor=AIDE, home=self.H), [])

    def test_scope_and_every_agent(self):
        row = {'id': 's' * 64, 'agents': [], 'scope': 'all', 'by': S}
        self.assertTrue(stops.binds([row], AIDE)[0])
        self.assertFalse(stops.binds([row], P)[0])
        row = dict(row, scope='t' * 64)
        self.assertFalse(stops.binds([row], AIDE, holon=self.C)[0])
        self.assertTrue(stops.binds([row], AIDE, line={'id': 'l' * 64, 'links': {'anchored_to': ['t' * 64]}})[0])
        self.assertTrue(stops.binds([dict(row, scope=S)], AIDE, to=S)[0])

    def test_lines_a_person_signs(self):
        s = stops.stop_line(S, self.C, agents=[AIDE], scope=self.C, why='hold', ts=CLOCK)
        self.assertEqual((s['type'], s['actor'], s['sig'], s['body']['agents']), ('stop', S, '', [AIDE]))
        l = stops.lift_line(P, self.C, s['id'], ts=CLOCK)
        self.assertEqual((l['body']['lift'], l['links']['answers']), (True, [s['id']]))
        for bad in (lambda: stops.stop_line(AIDE, self.C), lambda: stops.lift_line(AIDE, self.C, s['id']),
                    lambda: stops.lift_line(P, self.C, '')):
            with self.assertRaises(ValueError):
                bad()


class TestStatusAndCli(Base):
    def test_status_open_until_a_receipt(self):
        self.third()
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we use the hall', 'to': T3})
        carry.drop(line, self.home, self.row(self.plan(line), T3), by=P, now=CLOCK)
        st = carry.status(self.home, now=CLOCK)
        self.assertEqual((st['today']['carried'], st['today']['by_carrier']), (1, {'permitted': 1}))
        self.assertEqual([(o['line'], o['to']) for o in st['open']], [(line['id'], T3)])
        self.put(self.tcell, T3, 'receive', {'of': line['id'], 'how': 'permitted', 'from': P}, {'answers': [line['id']]})
        self.assertEqual(carry.status(self.home, now=CLOCK)['open'], [])

    def test_cli(self):
        self.agree()
        line = self.request(S)
        env = dict(os.environ)
        cmd = [sys.executable, '-I', os.path.join(ENGINE, 'carry.py')]
        out = subprocess.run(cmd + ['plan', self.home, line['id'], '--now', CLOCK, '--by', P], capture_output=True, text=True,
                             env=env, cwd=ENGINE)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)['deliveries'][0]['carrier'], 'face')
        out = subprocess.run(cmd + ['status', self.home, '--now', CLOCK], capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(out.stdout)['today']['carried'], 0)


class TestRepair(Base):
    """The independent review's findings, each pinned by a test."""

    def stop(self, by=S, d=None, **body):
        body = dict({'agents': [AIDE], 'scope': self.C, 'why': 'hold'}, **body)
        return self.put(d or self.cell, by, 'stop', body)

    def test_h1_a_stranger_who_affirms_the_aide_cannot_lift_it(self):
        self.agree()
        line = self.request(S)
        holon.affirm(self.cell, S, AIDE, pk(AIDE), ts=self.ts(), key_dir=KD)   # a second person claims the aide
        st = self.stop()
        self.put(self.cell, S, 'stop', {'lift': True, 'stop': st['id']}, {'answers': [st['id']]})
        f = record.fold_hq(self.home, clock=CLOCK)
        self.assertEqual([s['id'] for s in stops.live(f, actor=AIDE, home=self.H)], [st['id']])
        self.assertIsNone(self.row(self.plan(line, by=AIDE), S))
        # with no `persons` on the item, a lift counts only by the home holon's person, and holons that disagree
        item = dict([x for x in f['stops'] if x['id'] == st['id']][0], state='lifted', lifted_by=S)
        item.pop('persons', None)
        self.assertEqual(len(stops.live([item], actor=AIDE, home=self.H, admitted=f['admitted'])), 1)

    def test_m2_by_is_required(self):
        self.third()
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we', 'to': T3})
        self.stop(d=self.tcell, by=T3, scope=self.T)
        row = self.row(self.plan(line, by=P), T3)
        res = carry.drop(line, self.home, row, now=CLOCK)
        self.assertFalse(res['ok'])
        self.assertIn('names its carrier', res['said'])
        self.assertTrue(self.plan(line)['held'][0].get('stopped'))   # no carrier named: every agent is checked
        cmd = [sys.executable, '-I', os.path.join(ENGINE, 'carry.py')]
        out = subprocess.run(cmd + ['drop', self.home, line['id'], '--to', T3, '--now', CLOCK], capture_output=True,
                             text=True)
        self.assertEqual(out.returncode, 2)

    def test_m3_drop_remakes_the_plan(self):
        self.third(write=False)
        line = self.signed_for(self.tcell, P, 'request', {'text': 'may we', 'to': T3})
        res = carry.drop(line, self.home, {'carrier': 'permitted', 'cell': 'third', 'to': T3, 'holon': self.T}, by=P,
                         now=CLOCK)
        self.assertFalse(res['ok'])
        self.assertIn('no write permit', res['said'])
        self.assertFalse(os.path.exists(os.path.join(self.tcell, 'permitted', record.actor_file(P))))
        self.agree()
        face = self.request(S)
        row = self.row(self.plan(face, by=P), S)
        res = carry.drop(face, self.home, dict(row, holon='f' * 64), by=P, now=CLOCK, key_dir=KD)
        self.assertFalse(res['ok'])
        self.assertIn('differs from the plan made now', res['said'])

    def test_m4_the_real_directory(self):
        import directory
        d = {'people': {'person:ghost': {'id': 'person:ghost', 'fallback': 'the front desk'},
                        'person:list': {'id': 'person:list', 'fallback': ['desk', 'phone']}},
             'agents': {'agent:other': {'id': 'agent:other', 'person': 'person:ghost2'}}, 'holons': {}, 'memberships': {}}
        self.assertTrue(isinstance(directory.resolve(d, 'person:ghost')['said'], list))
        out = self.plan(self.request(['person:ghost', 'person:list', 'agent:other']), directory=d)
        got = {x['to']: (x['carrier'], x['where'], x.get('fallbacks')) for x in out['deliveries']}
        self.assertEqual(got['person:ghost'], ('fallback', 'the front desk', ['the front desk']))
        self.assertEqual(got['person:list'], ('fallback', 'desk', ['desk', 'phone']))
        self.assertIn('agent:other', [h['to'] for h in out['held']])
        out = self.plan(self.request('agent:other'))
        self.assertEqual([h['to'] for h in out['held']], ['agent:other'])
        out = self.plan(self.request('f' * 64))
        self.assertEqual([h['to'] for h in out['held']], ['f' * 64])        # an address that reaches no one is said

    def test_m5_a_thread_stop_reaches_every_line_under_it(self):
        self.agree()
        line = self.request(S)
        two = self.put(self.home, P, 'request', {'text': 'second', 'to': S}, {'answers': [line['id']]},
                       audience='members')
        three = self.put(self.home, P, 'request', {'text': 'third', 'to': S}, {'answers': [two['id']]},
                         audience='members')
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': line['id']})
        self.assertIsNotNone(self.held(self.plan(two, by=AIDE), S))
        self.assertIsNotNone(self.held(self.plan(three, by=AIDE), S))
        by_id = {l['id']: l for l in record.read_all(self.home)['lines']}
        self.assertEqual(stops.ancestors(three, by_id), {line['id'], two['id']})

    def test_m6_rounds_and_the_claim_of_human_words(self):
        ok, why = carry.may_reply({'actor': AIDE, 'reason': 'delegated', 'body': {'voice': 'human-words'}}, 'agent')
        self.assertFalse(ok)
        mandate = {'id': 'm' * 64, 'actor': AIDE, 'body': {'voice': 'under-mandate'}}
        self.assertTrue(carry.may_reply(mandate, 'under-mandate')[0])
        thread = [{'id': str(i) * 64, 'actor': 'agent:x', 'body': {'voice': 'under-mandate'}} for i in range(1, 3)]
        ok, why = carry.may_reply(mandate, 'under-mandate', thread=thread)
        self.assertFalse(ok)
        self.assertIn('MAX_ROUNDS', why)
        self.assertEqual(carry.MAX_ROUNDS, 3)
        self.assertTrue(carry.may_reply(mandate, 'person', thread=thread)[0])
        person = {'id': 'p' * 64, 'actor': P, 'body': {'voice': 'human-words'}}
        self.assertTrue(carry.may_reply(person, 'agent', thread=thread[:1])[0])

    def test_low_pull_never_promises_an_agent(self):
        self.put(self.home, P, 'join', {'who': F4, 'pubkey': pk(F4)})
        r = self.row(self.plan(self.request(F4)), F4)
        self.assertEqual(r['carrier'], 'pull')
        self.assertIn('no agent of theirs', r['why'])

    def log(self, **e):
        entry = dict({'at': CLOCK, 'ok': True, 'by': P, 'carrier': 'permitted', 'line': 'e' * 64, 'to': S,
                      'hops_in': 0, 'hops': 1, 'wide': False}, **e)
        with open(os.path.join(self.home, carry.LOG), 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(entry) + '\n')

    def test_low_rate_across_recipients_and_which_carriers_count(self):
        self.agree()
        holon.admit(self.cell, S, F4, pk(F4), ts=self.ts(), key_dir=KD)
        line = self.request([S, F4])
        out = self.plan(line, by=P, limits={'RATE_PER_DAY': 1})
        self.assertEqual(([d['to'] for d in out['deliveries']], [h['to'] for h in out['held']]), ([F4], [S]))
        self.log(carrier='mail')
        self.log(carrier='pull')
        self.log(ok=False)
        self.assertEqual(self.plan(line, by=P)['rate']['today'], 0)

    def test_low_rate_is_read_again_at_the_drop(self):
        self.agree()
        line = self.request(S)
        row = self.row(self.plan(line, by=P, limits={'RATE_PER_DAY': 1}), S)
        self.log()
        res = carry.drop(line, self.home, row, by=P, now=CLOCK, key_dir=KD, limits={'RATE_PER_DAY': 1})
        self.assertFalse(res['ok'])
        self.assertIn('rate', res['said'])

    def test_low_the_elided_face_copy(self):
        self.agree(fields={'request': ['text']})
        line = self.request(S)
        row = self.row(self.plan(line, by=P), S)
        self.assertEqual(row['elided'], ['to'])
        res = carry.drop(line, self.home, row, by=P, now=CLOCK, key_dir=KD)
        self.assertTrue(res['ok'], res['said'])
        self.assertEqual(res['elided'], ['to'])
        copy_ = [json.loads(x) for x in self.raw_lines(res['file']) if json.loads(x)['id'] == line['id']][0]
        self.assertTrue(record.check_id(copy_))
        self.assertIn('elided', copy_['body']['to'])
        self.assertEqual(copy_['body']['text'], line['body']['text'])

    def test_low_no_private_helper(self):
        with open(os.path.join(ENGINE, 'carry.py'), encoding='utf-8') as fh:
            text = fh.read()
        self.assertNotRegex(text, r'(faces|permitted)\._[a-z]')

class TestNullGuards(unittest.TestCase):
    """Law 6: null-guards; the kit's words."""

    def test_nothing_raises(self):
        tmp = tempfile.mkdtemp(dir=WORK)
        f = os.path.join(tmp, 'file')
        open(f, 'w').close()
        os.symlink(tmp, os.path.join(tmp, 'link'))
        for home in (None, '', 3, 1.5, f, os.path.join(tmp, 'link'), tmp, {}, []):
            for line in (None, {}, [], 'x', 1.5, 'café'):
                out = carry.plan(line, home, now=CLOCK)
                self.assertEqual(out['deliveries'], [])
                self.assertTrue(out['said'])
                self.assertFalse(carry.drop(line, home, None)['ok'])
                self.assertFalse(carry.drop(line, home, {'carrier': 'face'})['pushed'])
            self.assertEqual(carry.status(home)['open'], [])
        self.assertEqual(stops.live(None), [])
        self.assertEqual(stops.live({'stops': [None, 1, {}]}), [])
        self.assertFalse(stops.binds(None, None)[0])
        self.assertFalse(stops.binds([None, {}], AIDE, holon=1.5, line=[])[0])

    def test_words(self):
        for name in ('carry.py', 'stops.py'):
            with open(os.path.join(ENGINE, name), encoding='utf-8') as fh:
                text = fh.read().lower()
            for w in (' house', 'promise', ' hq', 'estate'):
                self.assertNotIn(w, text, (name, w))


if __name__ == '__main__':
    unittest.main()
