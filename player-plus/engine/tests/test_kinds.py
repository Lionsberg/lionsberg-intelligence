"""test_kinds.py — the Card kinds of the collaboration surface, folded from lines and checked.

Receipt · Agreement · Subscription Card · Message · Concordance · Correction · Wallet entry ·
the Sighting's nine kinds and its lifecycle · the emergency rule · the key share · the voice.

The sample fixtures (fixtures/make_fixtures.py) are built once per run in a temporary folder,
signed with throwaway keys kept for the run; each test folds the fixture lines with lines it
makes in memory, chained after each actor's head and signed with the actor's test key.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_kinds.py -v
"""
import os
import shutil
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import record          # noqa: E402
import holon           # noqa: E402
import make_fixtures   # noqa: E402

PLAYER, STEWARD, AIDE = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: the fixtures are signed')
    WORK = tempfile.mkdtemp(prefix='lionsberg-kinds-test-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.hq = os.path.join(TEMPLATE, 'hq')
        self.cell = os.path.join(self.hq, 'cells', make_fixtures.CELL)
        self.types = record.load_types()
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.r = record.read_all(self.hq)
        self.heads = {}
        for d in record.hold(self.hq):
            rd = record.read(d)
            for a, hs in rd['heads'].items():
                self.heads[(rd['holon'], a)] = hs[-1]
        self.n = 0

    def fold(self, extra=(), now=None):
        return record.fold(self.r['lines'] + list(extra), self.types, self.r['keepers'], now=now, clock=CLOCK)

    def mk(self, actor, holon_id, typ, body=None, links=None, ts=None, reason=None, for_=None, sign=True):
        """A signed line in memory, chained after the actor's head in that holon (then it is the new head)."""
        self.n += 1
        ts = ts or '2026-10-21T%02d:%02d:00-07:00' % (10 + self.n // 60, self.n % 60)
        for_ = for_ or (actor if actor.startswith('person:') else PLAYER)
        prev = self.heads.get((holon_id, actor), '')
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        line = record.make_line(actor, for_, holon_id, typ, body, links, reason=reason, ts=ts, salt='k%d' % self.n, prev=prev)
        if sign:
            line['sig'] = record.sign_id(line['id'], record.find_key(None, actor, KEYS))
        self.heads[(holon_id, actor)] = line['id']
        return line

    def item(self, f, coll, key):
        for i in f[coll]:
            if i['id'] == key:
                return i
        self.fail('no %s item %s' % (coll, key[:8]))

    def delegate_receive(self):
        """The player lets the aide write receipts in the cell (the fixtures' delegation does not cover receive)."""
        return self.mk(PLAYER, self.C, 'delegate', {'to': AIDE, 'scope': ['receive'], 'holons': [self.C], 'until': '2026-12-31'})


class TestReceipt(Base):
    def test_a_receipt_lands_on_the_item_the_line_made(self):
        d = self.delegate_receive()
        r = self.mk(AIDE, self.C, 'receive', {'of': IDS['request'], 'from': STEWARD, 'how': 'pull', 'text': 'I have it.'},
                    {'answers': [IDS['request']]})
        f = self.fold([d, r])
        card = self.item(f, 'cards', IDS['request'])
        mine = [x for x in card['receipts'] if x['id'] == r['id']]          # the fixtures hold a receipt of their own
        self.assertEqual([(x['how'], x['actor']) for x in mine], [('pull', AIDE)])
        self.assertEqual(len(card['receipts']), 2)

    def test_a_receipt_needs_trust(self):
        # an agent no one let in: its receipt is unverified and lands on nothing
        other = 'agent:stranger'
        r = record.make_line(other, STEWARD, self.C, 'receive', {'of': IDS['request'], 'how': 'pull'},
                             {'answers': [IDS['request']]}, reason='delegated', ts='2026-10-21T11:00:00-07:00', salt='x')
        f = self.fold([r])
        self.assertIn(r['id'], {i['id'] for i in f['unverified']})
        self.assertNotIn(r['id'], {x['id'] for x in self.item(f, 'cards', IDS['request']).get('receipts', [])})
        # and an untrusted reason makes it a proposal, never a receipt
        u = self.mk(AIDE, self.C, 'receive', {'of': IDS['request'], 'how': 'pull'}, {'answers': [IDS['request']]}, reason='untrusted')
        f = self.fold([u])
        self.assertIn(u['id'], {i['id'] for i in f['proposals']})
        self.assertNotIn(u['id'], {x['id'] for x in self.item(f, 'cards', IDS['request']).get('receipts', [])})

    def test_a_receipt_is_publishable(self):
        for t in ('receive', 'agree', 'concord', 'correct', 'wallet'):
            self.assertIn(t, holon.PUBLISHABLE)


class TestAgreement(Base):
    def test_proposed_then_agreed_by_the_other_holon(self):
        a = self.mk(PLAYER, self.C, 'agree', {'with': self.C, 'terms': 'what crosses', 'crosses': ['request', 'commit'],
                                              'cadence': {'request': 60}, 'permits': {'write': True, 'bell': ['pain']},
                                              'until': '2027-03-20'})
        f = self.fold([a])
        self.assertEqual(self.item(f, 'agreements', a['id'])['state'], 'proposed')
        b = self.mk(STEWARD, self.C, 'agree', {'with': self.H}, {'answers': [a['id']]})
        f = self.fold([a, b])
        it = self.item(f, 'agreements', a['id'])
        self.assertEqual((it['state'], it['agreed_by']), ('agreed', STEWARD))
        self.assertEqual(it['cadence'], {'request': 60})

    def test_a_person_cannot_agree_with_themselves(self):
        a = self.mk(PLAYER, self.C, 'agree', {'with': self.C})
        b = self.mk(PLAYER, self.C, 'agree', {'with': self.C}, {'answers': [a['id']]})
        it = self.item(self.fold([a, b]), 'agreements', a['id'])
        self.assertEqual(it['state'], 'proposed')
        self.assertTrue(any('not the right actor' in x['why'] for x in it.get('refused', [])))

    def test_an_agreement_expires_past_until(self):
        a = self.mk(PLAYER, self.C, 'agree', {'with': self.C, 'until': '2026-10-19'})   # before the fold's as-of
        self.assertEqual(self.item(self.fold([a]), 'agreements', a['id'])['state'], 'expired')

    def test_an_agent_never_agrees_on_a_standing_delegation(self):
        a = self.mk(AIDE, self.C, 'agree', {'with': self.C})
        f = self.fold([a])
        self.assertIn(a['id'], {i['id'] for i in f['invalid']})


class TestSubscription(Base):
    def test_a_subscription_is_the_persons_own_in_their_home(self):
        s = self.mk(PLAYER, self.H, 'subscribe', {'source': self.C, 'signals': ['request'], 'cadence': {'request': 60},
                                                  'surface': 'deal', 'bell': ['pain']})
        it = self.item(self.fold([s]), 'subscriptions', s['id'])
        self.assertEqual((it['state'], it['source'], it['surface']), ('live', self.C, 'deal'))

    def test_a_subscription_is_written_only_into_a_home(self):
        tmp = tempfile.mkdtemp(prefix='sub-', dir=WORK)
        shutil.copytree(self.hq, os.path.join(tmp, 'hq'))
        cell = os.path.join(tmp, 'hq', 'cells', make_fixtures.CELL)
        with self.assertRaises(ValueError):
            record.append(cell, PLAYER, PLAYER, 'subscribe', {'source': self.C}, sign=False)
        for t in ('subscribe', 'limits', 'share'):
            spec = self.types['types'][t]
            self.assertTrue(spec.get('home_only') and spec.get('human_only'), t)


class TestMessage(Base):
    def test_a_say_with_its_intent_is_a_message_in_a_thread(self):
        m = self.mk(PLAYER, self.C, 'say', {'text': 'When will the walk be written?', 'to': [STEWARD], 'intent': 'ask',
                                            'outcome': 'a date, or the reason there cannot be one', 'urgency': 'this week'},
                    {'anchored_to': [IDS['request']]})
        f = self.fold([m])
        th = self.item(f, 'threads', m['id'])
        self.assertEqual((th['to'], th['intent']), ([STEWARD], 'ask'))
        names = {x['name'] for x in self.types['types']['say']['fields']}
        self.assertTrue({'to', 'intent', 'outcome', 'urgency'} <= names)


class TestConcordance(Base):
    def test_proposed_by_an_agent_agreed_by_the_other_side(self):
        d = self.mk(PLAYER, self.C, 'delegate', {'to': AIDE, 'scope': ['concord'], 'holons': [self.C], 'until': '2026-12-31'})
        c = self.mk(AIDE, self.C, 'concord', {'term': 'commitment', 'in': 'lionsberg', 'term_other': 'promise',
                                              'in_other': 'last-planner', 'relation': 'same'})
        f = self.fold([d, c])
        self.assertEqual(self.item(f, 'concordances', c['id'])['state'], 'proposed')
        # an answer agrees only when it restates the proposal as written; a mirrored or different answer does not
        m = self.mk(STEWARD, self.C, 'concord', {'term': 'promise', 'in': 'last-planner', 'term_other': 'commitment',
                                                 'in_other': 'lionsberg', 'relation': 'same'}, {'answers': [c['id']]})
        self.assertEqual(self.item(self.fold([d, c, m]), 'concordances', c['id'])['state'], 'proposed')
        y = self.mk(STEWARD, self.C, 'concord', {'term': 'commitment', 'in': 'lionsberg', 'term_other': 'promise',
                                                 'in_other': 'last-planner', 'relation': 'same'}, {'answers': [c['id']]})
        it = self.item(self.fold([d, c, y]), 'concordances', c['id'])
        self.assertEqual((it['state'], it['agreed_by']), ('agreed', STEWARD))


class TestCorrection(Base):
    def wrong(self):
        return self.mk(PLAYER, self.H, 'sight', {'text': 'the road at the north gate is blocked', 'kind': 'blocked',
                                                 'where': 'the north gate'})

    def test_the_same_actor_corrects_their_own_sighting(self):
        w = self.wrong()
        c = self.mk(PLAYER, self.H, 'correct', {'why': 'the road is not blocked; the sign was moved'},
                    {'supersedes': [w['id']]})
        f = self.fold([w, c])
        s = self.item(f, 'sightings', w['id'])
        self.assertEqual((s['state'], s['retracted_by'], s['corrected_why']),
                         ('retracted', c['id'], 'the road is not blocked; the sign was moved'))
        self.assertIn(c['id'], s['events'])
        self.assertEqual(self.item(self.fold([w]), 'sightings', w['id'])['state'], 'seen')   # both lines remain

    def test_an_agent_never_corrects_a_persons_line(self):
        w = self.wrong()
        d = self.mk(PLAYER, self.H, 'delegate', {'to': AIDE, 'scope': ['correct'], 'holons': [self.H], 'until': '2026-12-31'})
        c = self.mk(AIDE, self.H, 'correct', {'why': 'wrong'}, {'supersedes': [w['id']]})
        f = self.fold([w, d, c])
        self.assertNotEqual(self.item(f, 'sightings', w['id'])['state'], 'retracted')
        self.assertTrue(any(r.get('supersedes') == w['id'] for r in f['refused']))

    def test_an_agent_corrects_its_own_line(self):
        d = self.mk(PLAYER, self.H, 'delegate', {'to': AIDE, 'scope': ['correct'], 'holons': [self.H], 'until': '2026-12-31'})
        c = self.mk(AIDE, self.H, 'correct', {'why': 'seen wrongly'}, {'supersedes': [IDS['sighting']]})
        s = self.item(self.fold([d, c]), 'sightings', IDS['sighting'])    # the fixtures' sighting is the aide's own
        self.assertEqual((s['state'], s['corrected_why']), ('retracted', 'seen wrongly'))

    def test_a_correction_names_what_replaces_the_line(self):
        w = self.wrong()
        new = self.mk(PLAYER, self.H, 'sight', {'text': 'the sign was moved on the 2nd', 'kind': 'defect', 'where': 'the north gate'})
        c = self.mk(PLAYER, self.H, 'correct', {'why': 'moved', 'with': new['id']}, {'supersedes': [w['id']]})
        s = self.item(self.fold([w, new, c]), 'sightings', w['id'])
        self.assertEqual(s['corrected_with'], new['id'])


class TestWallet(Base):
    def test_offer_accept_settle(self):
        o = self.mk(PLAYER, self.C, 'wallet', {'kind': 'offer', 'amount': 12000, 'unit': 'USD-cents', 'to': STEWARD,
                                               'for': IDS['request'], 'note': 'for the walk, on its keeping'})
        f = self.fold([o])
        self.assertEqual(self.item(f, 'wallet', o['id'])['state'], 'offered')
        a = self.mk(STEWARD, self.C, 'wallet', {'kind': 'accept', 'amount': 12000, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        it = self.item(self.fold([o, a]), 'wallet', o['id'])
        self.assertEqual((it['state'], it['accepted_by']), ('accepted', STEWARD))
        s = self.mk(PLAYER, self.C, 'wallet', {'kind': 'settle', 'amount': 12000, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        self.assertEqual(self.item(self.fold([o, a, s]), 'wallet', o['id'])['state'], 'settled')

    def test_the_offerer_cannot_accept_their_own_offer(self):
        o = self.mk(PLAYER, self.C, 'wallet', {'kind': 'offer', 'amount': 1, 'unit': 'USD-cents'})
        a = self.mk(PLAYER, self.C, 'wallet', {'kind': 'accept', 'amount': 1, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        self.assertEqual(self.item(self.fold([o, a]), 'wallet', o['id'])['state'], 'offered')

    def test_a_witness_appends_and_an_agent_never_moves_value(self):
        o = self.mk(PLAYER, self.C, 'wallet', {'kind': 'offer', 'amount': 1, 'unit': 'USD-cents'})
        w = self.mk(STEWARD, self.C, 'wallet', {'kind': 'witness', 'amount': 1, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        self.assertEqual(len(self.item(self.fold([o, w]), 'wallet', o['id'])['witnesses']), 1)
        g = self.mk(AIDE, self.C, 'wallet', {'kind': 'gift', 'amount': 1, 'unit': 'USD-cents'})
        self.assertIn(g['id'], {i['id'] for i in self.fold([g])['invalid']})


class TestSighting(Base):
    def test_nine_kinds(self):
        kind = next(fd for fd in self.types['types']['sight']['fields'] if fd['name'] == 'kind')
        self.assertEqual(kind['values'], ['defect', 'hazard', 'blocked', 'wonder', 'offer', 'request', 'question', 'witness', 'pain'])
        p = self.mk(PLAYER, self.H, 'sight', {'text': 'a member cannot reach the cell and has been silent two days',
                                              'kind': 'pain', 'where': 'the north gate'})
        it = self.item(self.fold([p]), 'sightings', p['id'])
        self.assertEqual((it['state'], it['body_kind']), ('seen', 'pain'))

    def test_accepted_by_a_claim_and_fixed_by_a_done(self):
        p = self.mk(PLAYER, self.H, 'sight', {'text': 'the link opens the wrong section', 'kind': 'defect'})
        c = self.mk(AIDE, self.H, 'claim', {'card': p['id']})
        it = self.item(self.fold([p, c]), 'sightings', p['id'])
        self.assertEqual((it['state'], it['holder']), ('accepted', AIDE))
        d = self.mk(PLAYER, self.H, 'done', {'card': p['id'], 'note': 'the link is right'})
        it = self.item(self.fold([p, c, d]), 'sightings', p['id'])
        self.assertEqual(it['state'], 'fixed')
        self.assertTrue(it['fixed_ts'])
        states = self.types['items']['sighting']['states']
        for s in ('seen', 'still_there', 'accepted', 'picked_up', 'fixed', 'closed', 'responded', 'retracted'):
            self.assertIn(s, states)

    def test_a_card_is_still_taken_by_a_claim(self):
        f = self.fold([])
        self.assertEqual(self.item(f, 'cards', IDS['plan_card'])['state'], 'done')   # the fixtures' own claim and done still fold


class TestRule(Base):
    def test_the_emergency_rule_is_the_persons_own(self):
        rule = {'rules': [{'signal': 'commitment', 'when': 'buffer_days < 0', 'on': 'critical', 'wake': True}], 'else': 'wait'}
        ok = self.mk(PLAYER, self.H, 'limits', rule)
        f = self.fold([ok])
        self.assertNotIn(ok['id'], {i['id'] for i in f['invalid']})
        bad = self.mk(AIDE, self.H, 'limits', rule)
        self.assertIn(bad['id'], {i['id'] for i in self.fold([bad])['invalid']})

    def test_only_the_stopped_agents_own_person_lifts_a_stop(self):
        s = self.mk(STEWARD, self.C, 'stop', {'agents': [AIDE], 'scope': self.C, 'why': 'hold'})
        f = self.fold([s])
        it = self.item(f, 'stops', s['id'])
        self.assertEqual((it['state'], it['persons']), ('live', [PLAYER]))
        stranger = self.mk(STEWARD, self.C, 'stop', {'lift': True, 'stop': s['id']}, {'answers': [s['id']]})
        it = self.item(self.fold([s, stranger]), 'stops', s['id'])
        self.assertEqual(it['state'], 'live')
        self.assertTrue(any('not the right actor' in x['why'] for x in it.get('refused', [])))
        own = self.mk(PLAYER, self.C, 'stop', {'lift': True, 'stop': s['id']}, {'answers': [s['id']]})
        it = self.item(self.fold([s, stranger, own]), 'stops', s['id'])
        self.assertEqual((it['state'], it['lifted_by']), ('lifted', PLAYER))

    def test_share_and_voice_are_registered(self):
        for t in ('share', 'voice'):
            self.assertEqual(self.types['types'][t]['item'], 'none')
            self.assertTrue(self.types['types'][t]['human_only'])


if __name__ == '__main__':
    unittest.main()
