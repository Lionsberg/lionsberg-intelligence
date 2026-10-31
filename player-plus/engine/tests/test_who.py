"""test_who.py — who may make an act: the registry says it for the acts anyone could make.

  1. answer on a card: one its ask names, or, put to the holon, any admitted member (`addressee`)
  2. release on a card: the one who asked for it or the one who holds it (`raiser_or_holder`)
  3. done and hand on a card: the one who holds it (`holder`)
  4. ratify and decide: an admitted member of the decision's holon (`member`)
  5. claim renewed from taken, by its holder
  6. the committor hands a commitment back, with why: returned, or withdrawn when not begun

The sample fixtures (fixtures/make_fixtures.py) are built once per run in a temporary folder and signed
with throwaway keys; each test folds them with signed lines it makes in memory. A third person, let into
the cell by its keeper, is the stranger who is still trusted there.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_who.py -v
"""
import json
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
import acts            # noqa: E402
import make_fixtures   # noqa: E402

PLAYER, STEWARD, AIDE = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
NEIGHBOUR = 'person:neighbour'          # let into the cell: a member, and a stranger to every ask below
CLOCK = '2026-10-24T12:00:00-07:00'
NOW = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: the fixtures are signed')
    WORK = tempfile.mkdtemp(prefix='lionsberg-who-test-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)
    record.make_key(NEIGHBOUR, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def not_right(who):
    return 'not the right actor for this act (%s)' % who


class Base(unittest.TestCase):
    def setUp(self):
        self.hq = os.path.join(TEMPLATE, 'hq')
        self.types = record.load_types()
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.r = record.read_all(self.hq)
        self.heads = {}
        for d in record.hold(self.hq):
            rd = record.read(d)
            for a, hs in rd['heads'].items():
                self.heads[(rd['holon'], a)] = hs[-1]
        self.n = 0
        pub = record.pubkey_of(record.find_key(None, NEIGHBOUR, KEYS))
        self.base = [self.mk(STEWARD, self.C, 'join', {'who': NEIGHBOUR, 'pubkey': pub, 'role': 'member'})]

    def fold(self, extra=(), now=None):
        return record.fold(self.r['lines'] + self.base + list(extra), self.types, self.r['keepers'], now=now,
                           clock=CLOCK)

    def mk(self, actor, holon_id, typ, body=None, links=None, reason=None, for_=None):
        """A signed line in memory, chained after the actor's head in that holon (then it is the new head)."""
        self.n += 1
        ts = '2026-10-21T%02d:%02d:00-07:00' % (10 + self.n // 60, self.n % 60)
        for_ = for_ or (actor if actor.startswith('person:') else PLAYER)
        prev = self.heads.get((holon_id, actor), '')
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        line = record.make_line(actor, for_, holon_id, typ, body, links, reason=reason, ts=ts, salt='w%d' % self.n,
                                prev=prev)
        line['sig'] = record.sign_id(line['id'], record.find_key(None, actor, KEYS))
        self.heads[(holon_id, actor)] = line['id']
        return line

    def item(self, f, coll, key):
        for i in f[coll]:
            if i['id'] == key:
                return i
        self.fail('no %s item %s' % (coll, key[:8]))

    def refusals(self, it, line):
        return [x['why'] for x in it.get('refused', []) if x['event'] == line['id']]

    def assertClean(self, f, lines):
        ids = {l['id'] for l in lines}
        for k in ('invalid', 'unverified', 'pending', 'forked'):
            self.assertFalse([x for x in f.get(k) or [] if x.get('id') in ids], k)

    def offered(self, f, it, actor):
        f = dict(f, holons=self.r['holons'])
        return acts.offered(it, actor, folded=f, now=NOW)


def moves(r):
    return {a['key'] for a in r['acts'] if a['sets']}


def keys(r):
    return {a['key'] for a in r['acts']}


class TheRegistrySaysIt(unittest.TestCase):
    def test_each_rule_is_a_line_of_the_registry(self):
        T = record.load_types()['types']

        def card_who(typ):
            return [t.get('who') for t in T[typ]['transitions'] if t.get('kind', 'card') == 'card']
        self.assertEqual(card_who('answer'), ['addressee', 'addressee'])
        self.assertEqual(card_who('release'), ['raiser_or_holder'])
        self.assertEqual(card_who('done'), ['holder'])
        self.assertEqual(card_who('hand'), ['holder'])
        self.assertEqual([t.get('who') for t in T['ratify']['transitions']], ['member'])
        self.assertEqual([t.get('who') for t in T['decide']['transitions']], ['member'])
        renew = [t for t in T['claim']['transitions'] if t.get('kind') == 'card' and 'taken' in (t.get('from') or [])]
        self.assertEqual([(t['who'], t['from']) for t in renew], [('holder', ['taken'])])
        back = [(t['who'], t['set']['state']) for t in T['release']['transitions'] if t.get('kind') == 'commitment']
        self.assertEqual(back, [('committee', 'released'), ('committor_unbegun', 'withdrawn'), ('committor', 'returned')])
        self.assertTrue({'returned', 'withdrawn'} <= set(record.load_types()['items']['commitment']['states']))
        for typ in ('request', 'offer'):                       # a new ask about a card needs no `who`
            self.assertEqual([t.get('who') for t in T[typ]['transitions']], [None])

    def test_the_fixture_copies_are_the_registry(self):
        with open(os.path.join(ENGINE, 'types.json'), 'rb') as f:
            want = f.read()
        for rel in (('fixtures', 'hq', 'types.json'), ('fixtures', 'hq', 'cells', 'first-cell', 'types.json')):
            with open(os.path.join(ENGINE, *rel), 'rb') as f:
                self.assertEqual(f.read(), want, '/'.join(rel))


class Rule1Answer(Base):
    def test_only_the_one_the_request_names_answers_it(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': PLAYER, 'title': 'Bring the chairs'})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        y = self.mk(PLAYER, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        f = self.fold([ask, x, y])
        self.assertClean(f, [ask, x, y])
        it = self.item(f, 'cards', ask['id'])
        self.assertEqual(self.refusals(it, x), [not_right('addressee')])
        self.assertEqual((it['state'], it['holder']), ('taken', PLAYER))

    def test_a_decline_too(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': PLAYER, 'title': 'Sweep the hall'})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'decline'}, {'answers': [ask['id']]})
        it = self.item(self.fold([ask, x]), 'cards', ask['id'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('open', [not_right('addressee')]))

    def test_an_ask_put_to_the_holon_is_answered_by_any_member(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': self.C, 'title': 'Who can lock up?'})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        it = self.item(self.fold([ask, x]), 'cards', ask['id'])
        self.assertEqual((it['state'], it['holder'], self.refusals(it, x)), ('taken', NEIGHBOUR, []))

    def test_an_offer_to_no_one_is_answered_by_members_only(self):
        # an offer in the player's home, put to no one: the steward, no member there, is refused from the cell
        off = self.mk(PLAYER, self.H, 'offer', {'title': 'Lend the projector'})
        x = self.mk(STEWARD, self.C, 'answer', {'answer': 'accept'}, {'answers': [off['id']]})
        it = self.item(self.fold([off, x]), 'cards', off['id'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('open', [not_right('addressee')]))

    def test_an_offer_to_one_is_answered_by_that_one(self):
        off = self.mk(PLAYER, self.C, 'offer', {'title': 'Print the flyers', 'to': STEWARD})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'accept'}, {'answers': [off['id']]})
        y = self.mk(STEWARD, self.C, 'answer', {'answer': 'accept'}, {'answers': [off['id']]})
        it = self.item(self.fold([off, x, y]), 'cards', off['id'])
        self.assertEqual(self.refusals(it, x), [not_right('addressee')])
        self.assertEqual((it['state'], it['holder']), ('taken', STEWARD))

    def test_the_asker_takes_a_counter_made_on_their_own_card(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': PLAYER, 'title': 'Paint the door'})
        counter = self.mk(PLAYER, self.C, 'offer', {'card': ask['id'], 'title': 'Paint it next week'})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        y = self.mk(STEWARD, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        it = self.item(self.fold([ask, counter, x, y]), 'cards', ask['id'])
        self.assertEqual(self.refusals(it, x), [not_right('addressee')])
        self.assertEqual(it['state'], 'taken')


class Rule2Release(Base):
    def test_the_one_who_asked_or_holds_lets_it_go(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Count the chairs', 'kind': 'activity'})
        claim = self.mk(PLAYER, self.C, 'claim', {'card': card['id']})
        x = self.mk(NEIGHBOUR, self.C, 'release', {'card': card['id'], 'why': 'not needed'})
        f = self.fold([card, claim, x])
        it = self.item(f, 'cards', card['id'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('taken', [not_right('raiser_or_holder')]))
        for who in (STEWARD, PLAYER):                       # the one who asked; the one who holds it
            y = self.mk(who, self.C, 'release', {'card': card['id'], 'why': 'not needed'})
            it = self.item(self.fold([card, claim, x, y]), 'cards', card['id'])
            self.assertEqual((it['state'], it['holder']), ('released', None), who)


class Rule3DoneAndHand(Base):
    def setUp(self):
        super().setUp()
        self.card = self.mk(STEWARD, self.C, 'card', {'title': 'Find the key', 'kind': 'activity'})   # its maker holds it

    def test_only_the_holder_marks_it_done(self):
        x = self.mk(NEIGHBOUR, self.C, 'done', {'card': self.card['id']})
        it = self.item(self.fold([self.card, x]), 'cards', self.card['id'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('ready', [not_right('holder')]))
        y = self.mk(STEWARD, self.C, 'done', {'card': self.card['id']})
        self.assertEqual(self.item(self.fold([self.card, x, y]), 'cards', self.card['id'])['state'], 'done')

    def test_only_the_holder_hands_it_on(self):
        x = self.mk(NEIGHBOUR, self.C, 'hand', {'card': self.card['id'], 'to': NEIGHBOUR})
        y = self.mk(STEWARD, self.C, 'hand', {'card': self.card['id'], 'to': PLAYER})
        it = self.item(self.fold([self.card, x, y]), 'cards', self.card['id'])
        self.assertEqual(self.refusals(it, x), [not_right('holder')])
        self.assertEqual(it['holder'], PLAYER)

    def test_one_who_committed_to_deliver_it_marks_it_done(self):
        c = self.mk(PLAYER, self.C, 'commit', {'card': self.card['id'], 'by': '2026-11-07'})
        y = self.mk(PLAYER, self.C, 'done', {'card': self.card['id']})
        f = self.fold([self.card, c, y])
        self.assertClean(f, [self.card, c, y])
        self.assertEqual(self.item(f, 'cards', self.card['id'])['state'], 'done')

    def test_a_person_acts_as_holder_when_their_agent_holds_it(self):
        card = self.mk(PLAYER, self.H, 'card', {'title': 'Sort the notes', 'kind': 'activity'})
        claim = self.mk(AIDE, self.H, 'claim', {'card': card['id']})                  # the aide holds it
        x = self.mk(STEWARD, self.C, 'done', {'card': card['id']})
        y = self.mk(PLAYER, self.H, 'done', {'card': card['id']})                      # its person finishes it
        f = self.fold([card, claim, x, y])
        self.assertClean(f, [card, claim, x, y])
        it = self.item(f, 'cards', card['id'])
        self.assertEqual(self.refusals(it, x), [not_right('holder')])
        self.assertEqual((it['state'], self.refusals(it, y)), ('done', []))
        # and the fixture's own line of this shape still folds: the aide claimed the notes card, its person handed it
        notes = self.item(f, 'cards', IDS['notes_card'])
        self.assertEqual((notes['state'], notes.get('refused', [])), ('released', []))


class ACommittorHoldsOnlyWhileTheCommitmentLives(Base):
    """A committor counts as holder while the commitment is live in the fold itself, and only when it was
    made to the card's holder (or, while no one holds the card, to anyone)."""
    def setUp(self):
        super().setUp()
        self.card = self.mk(STEWARD, self.C, 'card', {'title': 'Mend the gate', 'kind': 'activity'})
        self.take = self.mk(STEWARD, self.C, 'claim', {'card': self.card['id']})          # taken, the steward holds it
        self.c = self.mk(PLAYER, self.C, 'commit', {'card': self.card['id'], 'by': '2026-11-07', 'committee': STEWARD})
        self.start = [self.card, self.take, self.c]

    def acts_after(self, end):
        d = self.mk(PLAYER, self.C, 'done', {'card': self.card['id']})
        h = self.mk(PLAYER, self.C, 'hand', {'card': self.card['id'], 'to': PLAYER})
        r = self.mk(PLAYER, self.C, 'claim', {'card': self.card['id']})
        f = self.fold(self.start + end + [d, h, r])
        self.assertClean(f, self.start + end + [d, h, r])
        return f, [d, h, r]

    def test_while_live_the_committor_finishes_it(self):
        d = self.mk(PLAYER, self.C, 'done', {'card': self.card['id']})
        it = self.item(self.fold(self.start + [d]), 'cards', self.card['id'])
        self.assertEqual((it['state'], self.refusals(it, d)), ('done', []))

    def test_once_ended_the_committor_holds_nothing(self):
        ends = {'returned': lambda: self.mk(PLAYER, self.C, 'release', {'commitment': self.c['id'], 'why': 'the gate is gone'}),
                'released': lambda: self.mk(STEWARD, self.C, 'release', {'commitment': self.c['id']}),
                'declined': lambda: self.mk(STEWARD, self.C, 'answer', {'answer': 'decline', 'commitment': self.c['id']},
                                            {'answers': [self.c['id']]})}
        start = dict(self.heads)
        for state, make in ends.items():
            self.heads = dict(start)                       # each case chains after the same start
            end = make()
            f, (d, h, r) = self.acts_after([end])
            self.assertEqual(self.item(f, 'commitments', self.c['id'])['state'], state)
            it = self.item(f, 'cards', self.card['id'])
            self.assertEqual((it['state'], it['holder']), ('taken', STEWARD), state)
            for x in (d, h, r):
                self.assertEqual(self.refusals(it, x), [not_right('holder')], (state, x['type']))

    def test_a_stranger_who_commits_to_a_taken_card_takes_nothing(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Hold the hall', 'kind': 'activity'})
        claim = self.mk(PLAYER, self.C, 'claim', {'card': card['id']})                   # the player holds it
        for committee in (None, STEWARD):                                                 # to no one (the keeper); to its own person
            body = {'card': card['id'], 'by': '2026-11-07'}
            if committee:
                body['committee'] = committee
            c = self.mk(NEIGHBOUR, self.C, 'commit', body)
            grab = self.mk(NEIGHBOUR, self.C, 'claim', {'card': card['id']})
            h = self.mk(NEIGHBOUR, self.C, 'hand', {'card': card['id'], 'to': NEIGHBOUR})
            it = self.item(self.fold([card, claim, c, grab, h]), 'cards', card['id'])
            self.assertEqual(it['holder'], PLAYER, committee)
            self.assertEqual(self.refusals(it, grab) + self.refusals(it, h), [not_right('holder')] * 2, committee)

    def test_a_commitment_made_to_the_holder_lets_the_committor_hand_it(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Hold the hall', 'kind': 'activity'})
        claim = self.mk(PLAYER, self.C, 'claim', {'card': card['id']})
        c = self.mk(NEIGHBOUR, self.C, 'commit', {'card': card['id'], 'by': '2026-11-07', 'committee': PLAYER})
        h = self.mk(NEIGHBOUR, self.C, 'hand', {'card': card['id'], 'to': NEIGHBOUR})
        it = self.item(self.fold([card, claim, c, h]), 'cards', card['id'])
        self.assertEqual((it['holder'], self.refusals(it, h)), (NEIGHBOUR, []))


class TheFoldOwnsItsFields(Base):
    def test_a_commit_line_never_marks_itself_unbegun(self):
        card = self.mk(PLAYER, self.H, 'card', {'title': 'Write the welcome', 'kind': 'activity'})
        c = self.mk(PLAYER, self.H, 'commit', {'card': card['id'], 'by': '2026-11-07', 'committee': STEWARD,
                                               'started': False})
        back = self.mk(PLAYER, self.H, 'release', {'commitment': c['id'], 'why': 'not begun'})
        it = self.item(self.fold([card, c, back]), 'commitments', c['id'])
        self.assertNotIn('started', it)
        self.assertEqual((it['body_started'], it['state']), (False, 'returned'))

    def test_a_body_never_sets_who_holds_or_who_committed(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': PLAYER, 'title': 'Bring the chairs', 'holder': NEIGHBOUR})
        x = self.mk(NEIGHBOUR, self.C, 'answer', {'answer': 'accept'}, {'answers': [ask['id']]})
        it = self.item(self.fold([ask, x]), 'cards', ask['id'])
        self.assertEqual((it['state'], it['holder'], self.refusals(it, x)), ('open', PLAYER, [not_right('addressee')]))
        forged = [{'commitment': 'x', 'for': NEIGHBOUR, 'due_by': '2026-11-07'}]
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Find the key', 'kind': 'activity', 'committed_by': forged})
        d = self.mk(NEIGHBOUR, self.C, 'done', {'card': card['id']})
        it = self.item(self.fold([card, d]), 'cards', card['id'])
        self.assertNotIn('committed_by', it)
        self.assertEqual((it['state'], self.refusals(it, d)), ('ready', [not_right('holder')]))
        # a card's own declared holder still names who holds it when it is born
        held = self.mk(STEWARD, self.C, 'card', {'title': 'Lock up', 'kind': 'activity', 'holder': PLAYER})
        self.assertEqual(self.item(self.fold([held]), 'cards', held['id'])['holder'], PLAYER)


class Rule4RatifyAndDecide(Base):
    def test_only_a_member_ratifies(self):
        x = self.mk(STEWARD, self.C, 'ratify', {}, {'answers': [IDS['proposal']]})     # the steward is no member of the home
        f = self.fold([x])
        it = self.item(f, 'decisions', IDS['proposal'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('decided', [not_right('member')]))
        y = self.mk(PLAYER, self.H, 'ratify', {}, {'answers': [IDS['proposal']]})
        it = self.item(self.fold([x, y]), 'decisions', IDS['proposal'])
        self.assertEqual((it['state'], it['ratified_by']), ('ratified', PLAYER))

    def test_only_a_member_decides_a_proposal(self):
        prop = self.mk(PLAYER, self.H, 'propose', {'text': 'Move the gathering to the second day'})
        x = self.mk(STEWARD, self.C, 'decide', {'text': 'The second day'}, {'answers': [prop['id']]})
        y = self.mk(PLAYER, self.H, 'decide', {'text': 'The second day'}, {'answers': [prop['id']]})
        it = self.item(self.fold([prop, x, y]), 'decisions', prop['id'])
        self.assertEqual(self.refusals(it, x), [not_right('member')])
        self.assertEqual((it['state'], it['decided_by']), ('decided', PLAYER))

    def test_the_cell_member_ratifies_in_the_cell(self):
        it = self.item(self.fold(), 'decisions', IDS['cell_decision'])
        self.assertEqual((it['state'], it.get('refused', [])), ('ratified', []))


class Rule5ClaimRenewed(Base):
    def setUp(self):
        super().setUp()
        self.card = self.mk(STEWARD, self.C, 'card', {'title': 'Hold the hall', 'kind': 'activity'})
        self.claim = self.mk(PLAYER, self.C, 'claim', {'card': self.card['id'], 'until': '2026-10-22'})

    def test_the_holder_renews_and_no_one_else(self):
        x = self.mk(NEIGHBOUR, self.C, 'claim', {'card': self.card['id']})
        y = self.mk(PLAYER, self.C, 'claim', {'card': self.card['id'], 'until': '2026-10-30'})
        f = self.fold([self.card, self.claim, x, y], now='2026-10-24T12:00:00-07:00')
        it = self.item(f, 'cards', self.card['id'])
        self.assertEqual(self.refusals(it, x), [not_right('holder')])
        self.assertEqual((it['state'], it['holder'], it['claim']['until']), ('taken', PLAYER, '2026-10-30'))

    def test_without_the_renewal_the_claim_lapses(self):
        it = self.item(self.fold([self.card, self.claim], now='2026-10-24T12:00:00-07:00'), 'cards', self.card['id'])
        self.assertEqual(it['state'], 'ready')


class Rule6TheCommittorHandsItBack(Base):
    def setUp(self):
        super().setUp()
        self.card = self.mk(PLAYER, self.H, 'card', {'title': 'Write the welcome', 'kind': 'activity'})
        self.c = self.mk(PLAYER, self.H, 'commit', {'card': self.card['id'], 'by': '2026-11-07', 'committee': STEWARD})

    def test_returned_with_why(self):
        bare = self.mk(PLAYER, self.H, 'release', {'commitment': self.c['id']})
        back = self.mk(PLAYER, self.H, 'release', {'commitment': self.c['id'], 'why': 'the date moved under me'})
        f = self.fold([self.card, self.c, bare, back])
        self.assertClean(f, [self.card, self.c, bare, back])
        it = self.item(f, 'commitments', self.c['id'])
        self.assertEqual(self.refusals(it, bare), [not_right('committor')])      # no why: refused
        self.assertEqual((it['state'], it['returned_why']), ('returned', 'the date moved under me'))

    def test_returned_once_claimed_kept(self):
        kept = self.mk(PLAYER, self.H, 'kept', {'commitment': self.c['id']})
        back = self.mk(PLAYER, self.H, 'release', {'commitment': self.c['id'], 'why': 'it is not what was asked'})
        it = self.item(self.fold([self.card, self.c, kept, back]), 'commitments', self.c['id'])
        self.assertEqual(it['state'], 'returned')

    def test_the_committees_release_stays(self):
        rel = self.mk(STEWARD, self.C, 'release', {'commitment': self.c['id']})
        it = self.item(self.fold([self.card, self.c, rel]), 'commitments', self.c['id'])
        self.assertEqual(it['state'], 'released')

    def test_a_stranger_is_refused(self):
        x = self.mk(NEIGHBOUR, self.C, 'release', {'commitment': self.c['id'], 'why': 'no reason of mine'})
        it = self.item(self.fold([self.card, self.c, x]), 'commitments', self.c['id'])
        self.assertEqual((it['state'], self.refusals(it, x)), ('open', [not_right('committor')]))

    def test_withdrawn_when_the_commitment_says_it_was_not_begun(self):
        spec = record.load_types()['types']['release']['transitions']
        line = {'id': 'l1', 'type': 'release', 'actor': PLAYER, 'for': PLAYER, 'ts': '2026-10-21T10:00:00-07:00',
                'body': {'commitment': 'cm', 'why': 'I cannot begin it'}}
        base = {'id': 'cm', 'kind': 'commitment', 'holon': 'h', 'for': PLAYER, 'committee': STEWARD, 'state': 'open'}
        for mark, want in ((False, 'withdrawn'), (True, 'returned'), (None, 'returned')):
            it = dict(base)
            if mark is not None:
                it['started'] = mark
            self.assertEqual(record._apply(it, spec, line, line['body'], {}), '')
            self.assertEqual(it['state'], want, mark)


class Law2Agents(Base):
    def test_an_agent_renews_its_persons_claim(self):
        card = self.mk(PLAYER, self.H, 'card', {'title': 'Tidy the notes', 'kind': 'activity'})
        claim = self.mk(PLAYER, self.H, 'claim', {'card': card['id']})
        renew = self.mk(AIDE, self.H, 'claim', {'card': card['id']})
        f = self.fold([card, claim, renew])
        self.assertClean(f, [card, claim, renew])
        it = self.item(f, 'cards', card['id'])
        self.assertEqual((it['state'], it['holder'], it.get('refused', [])), ('taken', AIDE, []))

    def test_an_agent_never_ratifies_on_its_own(self):
        x = self.mk(AIDE, self.H, 'ratify', {}, {'answers': [IDS['proposal']]})
        f = self.fold([x])
        self.assertIn(x['id'], {i['id'] for i in f['invalid']})
        self.assertEqual(self.item(f, 'decisions', IDS['proposal'])['state'], 'decided')

    def test_an_agent_counts_only_through_its_person(self):
        here = {PLAYER: PLAYER, AIDE: PLAYER}
        dec = {'id': 'd', 'kind': 'decision', 'holon': 'h', 'for': PLAYER, 'admitted_here': here}
        mine = {'actor': AIDE, 'for': PLAYER}
        other = {'actor': 'agent:elsewhere', 'for': 'person:elsewhere'}
        self.assertTrue(record._who_ok('member', mine, dec, {}))
        self.assertFalse(record._who_ok('member', other, dec, {}))
        card = {'id': 'k', 'kind': 'card', 'holon': 'h', 'for': STEWARD, 'holder': AIDE, 'admitted_here': here}
        self.assertTrue(record._who_ok('holder', {'actor': PLAYER, 'for': PLAYER}, card, {}))
        self.assertFalse(record._who_ok('holder', {'actor': STEWARD, 'for': STEWARD}, card, {}))
        ask = {'id': 'a', 'kind': 'card', 'holon': 'h', 'for': STEWARD, 'asked': 'request', 'holder': PLAYER,
               'admitted_here': here}
        self.assertTrue(record._who_ok('addressee', mine, ask, {}))
        self.assertFalse(record._who_ok('addressee', other, ask, {}))

    def test_the_fold_says_who_is_admitted_over_any_body(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'A forged room', 'kind': 'activity',
                                                 'admitted_here': {NEIGHBOUR: NEIGHBOUR, 'person:x': 'person:x'}})
        it = self.item(self.fold([card]), 'cards', card['id'])
        self.assertEqual(it['admitted_here'].get(AIDE), PLAYER)
        self.assertIn(NEIGHBOUR, it['admitted_here'])
        self.assertNotIn('person:x', it['admitted_here'])


class Law3ActsOffered(Base):
    def test_a_commitment_offers_release_to_its_two_sides_only(self):
        card = self.mk(PLAYER, self.H, 'card', {'title': 'Write the welcome', 'kind': 'activity'})
        c = self.mk(PLAYER, self.H, 'commit', {'card': card['id'], 'by': '2026-11-07', 'committee': STEWARD})
        f = self.fold([card, c])
        it = self.item(f, 'commitments', c['id'])
        self.assertIn('act.release', moves(self.offered(f, it, PLAYER)))        # the committor hands it back
        self.assertIn('act.release', moves(self.offered(f, it, STEWARD)))       # the committee releases it
        self.assertEqual(moves(self.offered(f, it, NEIGHBOUR)), set())

    def test_a_card_offers_done_and_hand_to_its_holder_only(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Find the key', 'kind': 'activity'})
        f = self.fold([card])
        it = self.item(f, 'cards', card['id'])
        self.assertTrue({'act.done', 'act.hand'} <= keys(self.offered(f, it, STEWARD)))
        theirs = keys(self.offered(f, it, NEIGHBOUR))
        self.assertFalse({'act.done', 'act.hand', 'act.release'} & theirs)

    def test_an_ask_offers_its_answer_to_the_one_it_names(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': PLAYER, 'title': 'Bring the chairs'})
        f = self.fold([ask])
        it = self.item(f, 'cards', ask['id'])
        self.assertTrue({'act.answer.accept', 'act.answer.decline'} <= moves(self.offered(f, it, PLAYER)))
        for who in (NEIGHBOUR, STEWARD):
            self.assertFalse({'act.answer.accept', 'act.answer.decline'} & moves(self.offered(f, it, who)), who)

    def test_a_decision_offers_ratify_to_members_only(self):
        f = self.fold()
        it = self.item(f, 'decisions', IDS['proposal'])
        self.assertIn('act.ratify', moves(self.offered(f, it, PLAYER)))
        self.assertNotIn('act.ratify', moves(self.offered(f, it, STEWARD)))


class Law5Guards(unittest.TestCase):
    def test_null_guards(self):
        for who in ('addressee', 'holder', 'member', 'committor', 'committor_unbegun'):
            for line in (None, {}, {'for': None}, {'for': 1.5}):
                for item in (None, {}, [], {'admitted_here': 'x', 'to': [None, 3], 'committed_by': [None, 'x']}):
                    self.assertIs(record._who_ok(who, line, item, None), False, (who, line, item))
        for adm, h in ((None, None), ({}, 'h'), ({'h': []}, 'h'), ({'h': {'person:a': None, 3: {}}}, 'h')):
            self.assertEqual(record.admitted_here(adm, h), {})
        self.assertEqual(record.admitted_here({'h': {'person:a': {'ended': True}, 'agent:b': {'person': 'person:a'},
                                                     'agent:c': {}}}, 'h'), {'agent:b': 'person:a'})

    def test_an_item_built_by_hand_reads_its_own_person_and_the_keeper(self):
        dec = {'id': 'd', 'kind': 'decision', 'holon': 'h', 'for': 'person:a'}
        self.assertTrue(record._who_ok('member', {'for': 'person:a'}, dec, {}))
        self.assertTrue(record._who_ok('member', {'for': 'person:k'}, dec, {'h': 'person:k'}))
        self.assertFalse(record._who_ok('member', {'for': 'person:z'}, dec, {'h': 'person:k'}))


class ReadersStopCountingAHandedBackCommitment(unittest.TestCase):
    """A returned or withdrawn commitment no longer counts, wherever its states are listed."""
    DD = __import__('datetime').date(2026, 10, 24)

    def c(self, state):
        return {'id': 'c1', 'kind': 'commitment', 'holon': 'A', 'card': 'k1', 'by': '2026-10-01', 'state': state,
                'for': 'person:k', 'actor': 'person:k'}

    def test_reliability(self):
        import reliability
        self.assertTrue(reliability._commitment(self.c('open'), self.DD)['live'])
        for st in ('returned', 'withdrawn'):
            r = reliability._commitment(self.c(st), self.DD)
            self.assertEqual((r['live'], r['due']), (False, False), st)

    def test_sightings(self):
        import sightings
        from tests import test_sightings as TS
        for st, want in (('open', 'picked_up'), ('returned', 'seen'), ('withdrawn', 'seen')):
            its = TS.base()
            its['sightings'] = [TS.sg('s1', 'defect', 'The gate sticks')]
            its['commitments'] = [dict(self.c(st), holon=TS.H, card='s1', **{'for': TS.K, 'actor': TS.K})]
            lines = [TS.L('c1', 'commit', TS.K, {'card': 's1', 'by': '2026-11-01'})]
            self.assertEqual(sightings.lifecycle(its, lines)['s1']['state'], want, st)

    def test_engine(self):
        import engine
        card = {'id': 'k1', 'kind': 'card', 'holon': 'B', 'title': 'Mend the gate'}
        for st, n in (('open', 1), ('returned', 0), ('withdrawn', 0)):
            ext = engine.holon_graph({'cards': [card], 'commitments': [self.c(st)]}, [], 'A', {'A', 'B'})[1]
            self.assertEqual(len(ext), n, st)        # only a live commitment dates another holon's card

    def test_schedule(self):
        import schedule
        for st, n in (('open', 1), ('returned', 0), ('withdrawn', 0)):
            self.assertEqual(schedule.score_lines([self.c(st)], [], [], self.DD)[0]['commitments_made'], n, st)

    def test_kept_and_owed(self):
        import gamecore
        import kept
        import owed
        now = '2026-10-24T12:00:00-07:00'
        for st in ('withdrawn', 'returned'):
            c = dict(self.c(st), ts='2026-10-20T10:00:00-07:00', by='2026-10-22', **{st + '_ts': '2026-10-21T10:00:00-07:00'})
            self.assertEqual(gamecore.commitment_status(c, now), (st, None))      # past due, and not broken
            self.assertEqual(owed.owed({'commitments': [c]}, actor='person:k', now=now)['entries'], [])
            t = kept.kept({'commitments': [c]}, now=now)['total']
            self.assertEqual((t.get(st), t.get('broken')), (1, 0), st)

    def test_the_card_lists_keep_a_returned_card_live(self):
        # a card handed back is ready to be claimed again: the card-only lists do not drop it
        import conformance
        import schedule
        self.assertNotIn('returned', schedule.DROP_STATES)
        self.assertNotIn('returned', conformance.DROPPED)


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed')
class Deterministic(Base):
    def test_the_same_lines_fold_the_same(self):
        ask = self.mk(STEWARD, self.C, 'request', {'to': self.C, 'title': 'Who can lock up?'})
        a = json.dumps(self.fold([ask]), sort_keys=True, default=str)
        b = json.dumps(self.fold([ask]), sort_keys=True, default=str)
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
