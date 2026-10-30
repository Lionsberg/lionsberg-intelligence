"""test_record.py — what the Record owes its readers, checked.

The sample fixtures (fixtures/make_fixtures.py) are built once per run in a temporary
folder, signed with throwaway keys kept for the run, and copied fresh for each test, so
the shipped fixtures are never changed by a test.

Run from the engine folder: python3 -I -m unittest -v
"""
import datetime as dt
import json
import os
import shutil
import subprocess
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
NEAR = '2026-10-21T12:00:00-07:00'   # a reader's clock close to the clones' claims
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: the fixtures are signed')
    WORK = tempfile.mkdtemp(prefix='lionsberg-test-')
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
        self.tmp = tempfile.mkdtemp(prefix='lionsberg-case-', dir=WORK)
        shutil.copytree(os.path.join(TEMPLATE, 'hq'), os.path.join(self.tmp, 'hq'))
        self.ids = IDS
        self.hq = os.path.join(self.tmp, 'hq')
        self.cell = os.path.join(self.hq, 'cells', make_fixtures.CELL)
        self.types = record.load_types()
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.heads = {}
        for d in record.hold(self.hq):
            r = record.read(d)
            for a, hs in r['heads'].items():
                self.heads[(r['holon'], a)] = hs[-1]

    def lines(self):
        return record.read_all(self.hq)['lines']

    def fold(self, extra=(), now=None, clock='2026-10-24T12:00:00-07:00'):
        r = record.read_all(self.hq)
        return record.fold(r['lines'] + list(extra), self.types, r['keepers'], now=now, clock=clock)

    def mk(self, actor, holon_id, typ, body=None, links=None, ts='2026-10-21T09:00:00-07:00', salt='t',
           reason=None, for_=None, sign=True, prev=None, key=None):
        """A line made in memory, signed with the actor's test key, chained after the actor's head in that holon."""
        for_ = for_ or (actor if actor.startswith('person:') else PLAYER)
        if prev is None:
            prev = self.heads.get((holon_id, actor), '')
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        line = record.make_line(actor, for_, holon_id, typ, body, links, reason=reason, ts=ts, salt=salt, prev=prev)
        if sign:
            line['sig'] = record.sign_id(line['id'], key or record.find_key(None, actor, KEYS))
        self.heads[(holon_id, actor)] = line['id']
        return line

    def item(self, f, coll, key):
        want = self.ids.get(key, key)
        for i in f[coll]:
            if i['id'] == want:
                return i
        self.fail('no %s item for %s' % (coll, key))

    def invalid(self, f):
        return {i['id']: i for i in f['invalid']}


class TestCanonical(Base):
    def test_ids_stable(self):
        again_root = tempfile.mkdtemp(prefix='again-', dir=WORK)
        again = make_fixtures.build(again_root, KEYS)
        self.assertEqual(self.ids, again)
        for line in self.lines():
            clean = {k: v for k, v in line.items() if not k.startswith('_')}
            self.assertEqual(record.compute_id(dict(reversed(list(clean.items())))), line['id'])
            self.assertEqual(record.compute_id(json.loads(json.dumps(clean))), line['id'])

    def test_changed_content_changes_id(self):
        line = record.make_line(PLAYER, PLAYER, 'h', 'say', {'text': 'one'}, ts='2026-10-20T09:00:00-07:00', salt='s')
        self.assertTrue(record.check_id(line))
        line['body']['text'] = 'two'
        self.assertFalse(record.check_id(line))

    def test_types_never_share_a_digest(self):
        a = record.make_line(PLAYER, PLAYER, 'h', 'tea', {'minutes': 30}, ts='2026-10-20T09:00:00-07:00', salt='s')
        b = record.make_line(PLAYER, PLAYER, 'h', 'tea', {'minutes': '30'}, ts='2026-10-20T09:00:00-07:00', salt='s')
        self.assertNotEqual(a['id'], b['id'])
        b['id'] = a['id']
        self.assertFalse(record.check_id(b))

    def test_canonical_rules_enforced(self):
        with self.assertRaises(ValueError):
            record.loads('{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            record.loads('{"minutes":1.5}')
        with self.assertRaises(ValueError):
            record.loads('{"minutes":NaN}')
        with self.assertRaises(ValueError):
            record.make_line(PLAYER, PLAYER, 'h', 'tea', {'minutes': 1.5}, salt='s')
        whole = record.make_line(PLAYER, PLAYER, 'h', 'tea', {'minutes': 30.0}, salt='s')
        self.assertEqual(whole['body']['minutes'], 30)
        nfd = 'café'
        written = record.make_line(PLAYER, PLAYER, 'h', 'say', {'text': nfd}, salt='s')
        self.assertEqual(written['body']['text'], 'café')         # written in NFC
        forged = dict(written, body=dict(written['body'], text=nfd))
        forged['id'] = written['id']
        self.assertFalse(record.check_id(forged))                       # a non-NFC line has no id

    def test_holon_id_is_inception_line(self):
        self.assertEqual(record.holon_info(self.hq)['id'], self.ids['hq_inception'])
        self.assertEqual(record.read(self.cell)['keeper'], STEWARD)


class TestFiles(Base):
    def test_actor_files_percent_encoded(self):
        self.assertEqual(record.actor_file('person:a/b'), 'person%3Aa%2Fb.jsonl')
        self.assertNotEqual(record.actor_file('person:a/b'), record.actor_file('person:a_b'))
        self.assertTrue(os.path.isfile(os.path.join(self.hq, 'record', 'person%3Aplayer.jsonl')))

    def test_case_collision_refused(self):
        with self.assertRaises(ValueError):
            record.append(self.hq, 'person:Player', 'person:Player', 'say', {'text': 'hi'}, sign=False)

    def test_chains_verified(self):
        for d in record.hold(self.hq):
            self.assertEqual(record.read(d)['problems'], [], d)

    def test_broken_chain_reported_not_crashed(self):
        path = os.path.join(self.hq, 'record', record.actor_file(PLAYER))
        with open(path, encoding='utf-8') as f:
            rows = f.readlines()
        del rows[3]
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(rows)
        r = record.read(self.hq)
        self.assertIn('broken_chain', [p['kind'] for p in r['problems']])
        self.assertEqual(len([l for l in r['lines'] if l['actor'] == PLAYER]), len(rows))

    def test_fork_kept_and_flagged(self):
        path = os.path.join(self.hq, 'record', record.actor_file(PLAYER))
        with open(path, encoding='utf-8') as f:
            rows = f.readlines()
        second = json.loads(rows[1])
        twin = self.mk(PLAYER, self.H, 'say', {'text': 'from another body'}, prev=second['prev'], salt='fork')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(record.dumps(twin) + '\n')
        r = record.read(self.hq)
        self.assertIn('fork', [p['kind'] for p in r['problems']])
        self.assertIn(twin['id'], [l['id'] for l in r['lines']])

    def test_tampered_line_left_out(self):
        path = os.path.join(self.hq, 'record', record.actor_file(PLAYER))
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text.replace('Draft the season plan', 'Draft nothing'))
        r = record.read(self.hq)
        self.assertIn('bad_id', [p['kind'] for p in r['problems']])
        self.assertNotIn(self.ids['plan_card'], [l['id'] for l in r['lines']])

    def test_newest_seen_per_holon(self):
        r = record.read_all(self.hq)
        self.assertEqual(len(r['holons']), 2)
        for h in r['holons']:
            self.assertTrue(h['newest']['id'])
            self.assertIn(PLAYER, h['as_of'])
            self.assertTrue(h['counts'][PLAYER] >= 1)


class TestSignatures(Base):
    def test_every_fixture_line_verifies_in_the_fold(self):
        f = self.fold()
        self.assertEqual(set(f['trust'].values()), {'signed'})
        self.assertEqual(f['unverified'], [])

    def test_swapped_signature_is_bad_signature(self):
        path = os.path.join(self.hq, 'record', record.actor_file(PLAYER))
        with open(path, encoding='utf-8') as f:
            rows = [json.loads(x) for x in f if x.strip()]
        rows[3]['sig'], rows[4]['sig'] = rows[4]['sig'], rows[3]['sig']
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(record.dumps(r) + '\n' for r in rows)
        inv = self.invalid(self.fold())
        self.assertEqual(inv[rows[3]['id']]['invalid_reason'], 'bad_signature')

    def test_forged_person_line(self):
        # an unsigned line claiming the player, dropped into the cell by anyone with write access
        forged = self.mk(PLAYER, self.C, 'commit', {'card': self.ids['venue_card'], 'by': '2026-11-01'},
                         sign=False, salt='f1')
        # and one claiming the player, signed with another person's key
        stolen = self.mk(PLAYER, self.C, 'decide', {'text': 'The steward decides for the player'}, sign=False,
                         salt='f2')
        stolen['sig'] = record.sign_id(stolen['id'], record.find_key(None, STEWARD, KEYS))
        f = self.fold([dict(forged, _held_in=self.C, _file='record/x'), dict(stolen, _held_in=self.C, _file='record/x')])
        self.assertIn(forged['id'], [u['id'] for u in f['unverified']])
        self.assertEqual(self.invalid(f)[stolen['id']]['invalid_reason'], 'bad_signature')
        self.assertEqual(len(f['commitments']), 2)
        self.assertNotIn('The steward decides for the player', [d.get('text') for d in f['decisions']])

    def test_unadmitted_key_and_unaffirmed_agent(self):
        record.make_key('person:stranger', KEYS)
        record.make_key('agent:stray', KEYS)
        stranger = self.mk('person:stranger', self.C, 'card', {'title': 'A stranger\'s card'}, salt='u1')
        stray = self.mk('agent:stray', self.C, 'card', {'title': 'A stray agent\'s card'}, for_=STEWARD, salt='u2')
        f = self.fold([stranger, stray])
        unv = {u['id']: u for u in f['unverified']}
        self.assertIn(stranger['id'], unv)
        self.assertIn(stray['id'], unv)
        titles = [c.get('title') for c in f['cards']]
        self.assertNotIn('A stranger\'s card', titles)
        self.assertNotIn('A stray agent\'s card', titles)

    def test_unsigned_counts_only_at_home(self):
        home = lambda l: dict(l, _held_in=self.H, _file='record/x', _home_record=True)
        paper = self.mk(PLAYER, self.H, 'sight', {'text': 'seen at home'}, sign=False, salt='h1')
        f = self.fold([home(paper)])
        self.assertEqual(f['trust'][paper['id']], 'paper')        # the keeper holds a key: paper until witnessed
        self.assertNotIn('seen at home', [s.get('text') for s in f['sightings']])
        wit = self.mk(PLAYER, self.H, 'witness', {'note': 'mine'}, {'witnesses': [paper['id']]}, salt='h2')
        f = self.fold([home(paper), wit])
        self.assertEqual(f['trust'][paper['id']], 'home')
        self.assertIn('seen at home', [s.get('text') for s in f['sightings']])
        f2 = self.fold([dict(paper, _held_in=self.H, _file='published/x')])
        self.assertIn(paper['id'], [u['id'] for u in f2['unverified']])

    def test_paper_floor_kept_without_a_key(self):
        d = os.path.join(self.tmp, 'keyless')
        holon.init(d, 'keyless', 'person', 'person:host', sign=False)
        record.append(d, 'person:host', 'person:host', 'sight', {'text': 'on paper'}, sign=False)
        f = record.fold_hq(d)
        self.assertIn('on paper', [s.get('text') for s in f['sightings']])

    def test_wrong_holon_never_acts(self):
        line = self.mk(PLAYER, self.H, 'card', {'title': 'Written for the HQ', 'kind': 'milestone'}, salt='w1')
        f = self.fold([dict(line, _held_in=self.C, _file='record/person%3Aplayer.jsonl')])
        self.assertEqual(self.invalid(f)[line['id']]['invalid_reason'], 'wrong_holon')

    def test_sign_and_verify_one_line(self):
        r = record.append(self.hq, PLAYER, PLAYER, 'card', {'title': 'Signed card', 'holder': STEWARD},
                          ts='2026-10-21T10:00:00-07:00', key_dir=KEYS)
        self.assertTrue(r['signed'], r['said'])
        signers = os.path.join(self.tmp, 'allowed')
        with open(signers, 'w', encoding='utf-8') as f:
            f.write('%s namespaces="%s" %s\n' % (PLAYER, record.NAMESPACE, self.ids['pubkeys'][PLAYER]))
        self.assertEqual(record.verify(r['line'], signers)['sig'], 'valid')
        forged = dict(r['line'], ts='2026-10-22T10:00:00-07:00')
        self.assertEqual(record.verify(forged, signers)['sig'], 'invalid')


class TestKeys(Base):
    def test_each_actor_signs_with_its_own_key(self):
        p = record.find_key(None, PLAYER, KEYS)
        a = record.find_key(None, AIDE, KEYS)
        self.assertTrue(p.endswith('lionsberg-person-player'))
        self.assertTrue(a.endswith('lionsberg-agent-player-aide'))
        self.assertNotEqual(record.pubkey_of(p), record.pubkey_of(a))
        if not os.path.isfile(os.path.expanduser('~/.ssh/lionsberg-agent-player-aide')):
            self.assertIsNone(record.find_key(p, AIDE, None))     # a key named for another actor is refused

    def test_append_passes_the_actor(self):
        r = record.append(self.hq, AIDE, PLAYER, 'sight', {'text': 'the aide signs'}, reason='delegated',
                          ts='2026-10-21T10:00:00-07:00', key_dir=KEYS)
        self.assertTrue(r['signed'])
        self.assertTrue(record.verify_text(r['line']['id'], r['line']['sig'], AIDE, self.ids['pubkeys'][AIDE]))
        self.assertFalse(record.verify_text(r['line']['id'], r['line']['sig'], AIDE, self.ids['pubkeys'][PLAYER]))

    def test_unsigned_without_key_said_plainly(self):
        who = 'person:no-key-anywhere'
        r = record.append(self.hq, who, who, 'say', {'text': 'hi'}, key_dir=os.path.join(self.tmp, 'none'))
        self.assertFalse(r['signed'])
        self.assertIn('paper floor', r['said'])
        self.assertEqual(r['line']['sig'], '')


class TestFold(Base):
    def test_items_and_states_across_both_holons(self):
        f = self.fold()
        plan = self.item(f, 'cards', 'plan_card')
        self.assertEqual((plan['state'], plan['stage'], plan['holon']), ('done', 'did', self.H))
        self.assertEqual(self.item(f, 'cards', 'notes_card')['state'], 'released')
        self.assertEqual(self.item(f, 'cards', 'venue_card')['holon'], self.C)
        req = self.item(f, 'cards', 'request')
        self.assertEqual((req['state'], req['holder']), ('taken', PLAYER))
        self.assertEqual(self.item(f, 'cards', 'offer')['state'], 'declined')
        c = self.item(f, 'commitments', 'commitment')
        self.assertEqual((c['state'], c['witnessed_by'], c['gap_days']), ('kept', STEWARD, -10))
        self.assertIn(self.ids['learn'], c['events'])
        self.assertEqual(self.item(f, 'threads', 'thread')['state'], 'settled')
        self.assertEqual(self.item(f, 'decisions', 'proposal')['state'], 'decided')
        self.assertEqual(self.item(f, 'decisions', 'cell_decision')['state'], 'ratified')
        self.assertEqual(self.item(f, 'tea', 'tea')['state'], 'witnessed')
        disc = self.item(f, 'discernments', 'route')
        self.assertEqual((disc['state'], disc['discerned_by']), ('corrected', PLAYER))
        self.assertEqual(self.item(f, 'delegations', 'delegation2')['state'], 'revoked')
        self.assertEqual(self.item(f, 'delegations', 'delegation')['state'], 'live')
        for coll in ('sightings', 'turns', 'baselines'):
            self.assertEqual(len(f[coll]), 1)
        self.assertEqual(f['problems'], [])
        self.assertEqual(f['unknown'], [])
        for key in ('posture', 'affirm', 'layout', 'leave', 'hq_affirm', 'cell_join'):
            self.assertNotIn(self.ids[key], self.invalid(f))

    def test_every_type_appears_in_fixtures(self):
        first_set = {'say', 'settle', 'propose', 'card', 'commit', 'claim', 'release', 'hand', 'request',
                     'offer', 'answer', 'done', 'kept', 'witness', 'learn', 'decide', 'ratify', 'thread',
                     'sight', 'delegate', 'revoke', 'join', 'publish', 'elide', 'tea', 'turn', 'baseline',
                     'supersede', 'flame', 'discern', 'route', 'layout', 'leave', 'posture', 'affirm',
                     'elevate', 'escalate', 'rfg', 'body'}
        seen = {l['type'] for l in self.lines()}
        self.assertEqual(first_set - seen, set())
        self.assertEqual(set(self.types['types']) - seen, set(), 'a registered type has no fixture line')
        self.assertGreaterEqual(len(self.lines()), 50)

    def test_commitment_never_writes_onto_its_card(self):
        # a commitment never writes a date onto its Work Card; the card carries a reference only
        f = self.fold()
        plan = self.item(f, 'cards', 'plan_card')
        self.assertEqual(plan['by'], '2026-11-01')        # the card's own date, untouched by the commitment
        self.assertNotIn('constraint', plan)
        self.assertEqual(plan['committed_by'], [{'commitment': self.ids['commitment'], 'due_by': '2026-10-30', 'for': PLAYER,
                                                 'state': 'kept', 'committee': None, 'buffer': None}])
        second = self.mk(PLAYER, self.H, 'commit', {'card': self.ids['plan_card'], 'by': '2026-10-28'}, salt='c2')
        p2 = self.item(self.fold([second]), 'cards', 'plan_card')
        self.assertEqual([c['due_by'] for c in p2['committed_by']], ['2026-10-30', '2026-10-28'])
        self.assertEqual(p2['by'], '2026-11-01')

    def test_commitment_compared_by_the_schedule(self):
        import schedule as S
        card = self.mk(PLAYER, self.C, 'card', {'title': 'Due early', 'kind': 'milestone', 'by': '2026-11-01'}, salt='d1')
        com = self.mk(PLAYER, self.C, 'commit', {'card': card['id'], 'by': '2026-11-20'}, salt='d2')
        folded = [c for c in self.fold([card, com])['cards'] if c['id'] == card['id']][0]
        self.assertEqual(folded['by'], '2026-11-01')
        self.assertNotIn('constraint', folded)
        res = S.run([folded], data_date='2026-10-29')
        row = [x for x in res['items'] if x['id'] == card['id']][0]
        self.assertEqual(row['commitments'][0]['due_by'], '2026-11-20')
        self.assertEqual(row['commitments'][0]['buffer_days'], (S.to_date('2026-11-20') - S.to_date(row['finish'])).days)

    def test_the_commitments_full_shape(self):
        # committor (the line's for), committee, stated buffer; only the committee releases, declines or says Kept
        import schedule as S
        card = self.mk(PLAYER, self.C, 'card', {'title': 'The walk, written', 'minutes': 960}, ts='2026-10-21T09:11:00-07:00', salt='f1')
        com = self.mk(PLAYER, self.C, 'commit', {'card': card['id'], 'by': '2026-11-06', 'committee': STEWARD, 'buffer': 480},
                      ts='2026-10-21T09:12:00-07:00', salt='f2')
        f = self.fold([card, com])
        c = [x for x in f['commitments'] if x['id'] == com['id']][0]
        self.assertEqual((c['committee'], c['buffer'], c['state']), (STEWARD, 480, 'open'))
        folded = [x for x in f['cards'] if x['id'] == card['id']][0]
        res = S.run([folded], data_date='2026-11-02', me=STEWARD)
        row = res['commitments'][0]
        self.assertEqual((row['committor'], row['committee'], row['direction'], row['delivered_by']), (PLAYER, STEWARD, 'received', card['id']))
        self.assertEqual((row['computed_finish'], row['buffer_days'], row['stated_buffer_days'], row['signal']),
                         ('2026-11-03', 3, 1, 'safe'))       # 960 minutes is two days of work, the last 11-03; due 11-06 leaves three
        kept = self.mk(PLAYER, self.C, 'kept', {'commitment': com['id']}, ts='2026-10-21T09:13:00-07:00', salt='f3')
        self.assertEqual([x for x in self.fold([card, com, kept])['commitments'] if x['id'] == com['id']][0]['state'], 'claimed')
        wit = self.mk(STEWARD, self.C, 'witness', {'note': 'tested once'}, {'witnesses': [kept['id']]}, ts='2026-10-21T09:14:00-07:00', salt='f4')
        c = [x for x in self.fold([card, com, kept, wit])['commitments'] if x['id'] == com['id']][0]
        self.assertEqual((c['state'], c['witnessed_by']), ('kept', STEWARD))   # the committee says Kept
        rel = self.mk(STEWARD, self.C, 'release', {'commitment': com['id'], 'why': 'no longer needed'}, ts='2026-10-21T09:13:00-07:00', salt='f5')
        f = self.fold([card, com, rel])
        self.assertEqual([x for x in f['commitments'] if x['id'] == com['id']][0]['state'], 'released')
        folded = [x for x in f['cards'] if x['id'] == card['id']][0]
        row = S.run([folded], data_date='2026-11-02')['commitments'][0]
        self.assertEqual((row['state'], row['compared'], row['buffer_days']), ('released', False, None))   # shown, never compared
        mine = self.mk(PLAYER, self.C, 'release', {'commitment': com['id']}, ts='2026-10-21T09:13:00-07:00', salt='f6')
        self.assertEqual([x for x in self.fold([card, com, mine])['commitments'] if x['id'] == com['id']][0]['state'], 'open')
        dec = self.mk(STEWARD, self.C, 'answer', {'answer': 'decline', 'commitment': com['id']}, ts='2026-10-21T09:13:00-07:00', salt='f7')
        self.assertEqual([x for x in self.fold([card, com, dec])['commitments'] if x['id'] == com['id']][0]['state'], 'declined')

    def test_the_planning_lines(self):
        # pledge (an item of its own), miss (a coded reason on a commitment), constraint and clear (the constraint log)
        f = self.fold()
        pl = [x for x in f['pledges'] if x['id'] == self.ids['pledge']][0]
        self.assertEqual((pl['state'], pl['tea_min_week'], pl['level'], pl['for']), ('committed', 600, 'season', PLAYER))
        c = [x for x in f['commitments'] if x['id'] == self.ids['agent_commit']][0]
        self.assertEqual([(m['id'], m['reason']) for m in c['misses']], [(self.ids['miss'], 'capacity')])
        k = [x for x in f['constraints'] if x['id'] == self.ids['constraint']][0]
        self.assertEqual((k['state'], k['sort'], k['card']), ('cleared', 'information', self.ids['notes_card']))
        self.assertTrue(k['cleared_ts'])

    def test_only_the_right_party_acts_on_a_commitment(self):
        # review E, H1/H2/M3: release and decline by the committee (else the keeper); Kept by the committee or the named
        # witness, never the committor; a miss only by a party; a constraint cleared only by its raiser or holder
        t = lambda n: '2026-10-21T09:2%d:00-07:00' % n
        card = self.mk(STEWARD, self.C, 'card', {'title': 'The hall key', 'kind': 'activity'}, ts=t(0), salt='w0')
        com = self.mk(STEWARD, self.C, 'commit', {'card': card['id'], 'by': '2026-11-06'}, ts=t(1), salt='w1')
        rel = self.mk(PLAYER, self.C, 'release', {'commitment': com['id']}, ts=t(2), salt='w2')
        state = lambda f, i: [x for x in f['commitments'] if x['id'] == i][0]
        self.assertEqual(state(self.fold([card, com, rel]), com['id'])['state'], 'open')   # a member is not the committee
        miss = self.mk(PLAYER, self.C, 'miss', {'commitment': com['id'], 'reason': 'priority'}, ts=t(3), salt='w3')
        self.assertFalse(state(self.fold([card, com, miss]), com['id']).get('misses'))      # nor a party
        own = self.mk(PLAYER, self.C, 'commit', {'card': card['id'], 'by': '2026-11-06', 'committee': STEWARD,
                                                  'witness': 'person:auditor'}, ts=t(4), salt='w4')
        kept = self.mk(PLAYER, self.C, 'kept', {'commitment': own['id']}, ts=t(5), salt='w5')
        wit = self.mk(STEWARD, self.C, 'witness', {'note': 'it opens the hall'}, {'witnesses': [kept['id']]}, ts=t(6), salt='w6')
        self.assertEqual(state(self.fold([card, own, kept, wit]), own['id'])['state'], 'kept')   # the committee says Kept
        k = self.mk(STEWARD, self.C, 'constraint', {'card': card['id'], 'sort': 'resource', 'what': 'the key'}, ts=t(7), salt='w7')
        clr = self.mk(PLAYER, self.C, 'clear', {'constraint': k['id']}, ts=t(8), salt='w8')
        self.assertEqual([x for x in self.fold([card, k, clr])['constraints'] if x['id'] == k['id']][0]['state'], 'open')

    def test_unknown_type_kept(self):
        odd = self.mk(PLAYER, self.H, 'dance', {'text': 'a new type'}, salt='y')
        self.assertIn(odd['id'], [u['id'] for u in self.fold([odd])['unknown']])

    def test_link_not_yet_replicated(self):
        orphan = self.mk(PLAYER, self.H, 'claim', {'card': 'f' * 64}, salt='z')
        self.assertIn('not yet replicated', [p.get('said') for p in self.fold([orphan])['pending']])

    def test_fold_is_pure(self):
        self.assertEqual(json.dumps(self.fold(), sort_keys=True, default=str),
                         json.dumps(self.fold(), sort_keys=True, default=str))


class TestSupersede(Base):
    def test_latest_shows_both_remain(self):
        plan = self.item(self.fold(), 'cards', 'plan_card')
        self.assertEqual((plan['title'], plan['minutes']), ('Draft the first season plan', 300))
        self.assertIn(self.ids['supersede'], plan['events'])
        held = {l['id'] for l in self.lines()}
        self.assertTrue({self.ids['plan_card'], self.ids['supersede']} <= held)

    def test_other_person_refused(self):
        bad = self.mk(STEWARD, self.C, 'supersede', {'title': 'Taken over'}, {'supersedes': [self.ids['venue_card']]},
                      salt='s1', for_=STEWARD)
        # the steward over the player's request answer, in the cell, without a decision
        over = self.mk(STEWARD, self.C, 'supersede', {'answer': 'decline'}, {'supersedes': [self.ids['accept']]},
                       salt='s2')
        f = self.fold([bad, over])
        self.assertEqual(self.item(f, 'cards', 'venue_card')['title'], 'Taken over')   # its own line: allowed
        self.assertIn(over['id'], [r['id'] for r in f['refused']])
        self.assertEqual(self.item(f, 'cards', 'request')['state'], 'taken')

    def test_agent_never_supersedes_a_person(self):
        sup = self.mk(AIDE, self.H, 'supersede', {'by': '2027-06-01', 'size': 1},
                      {'supersedes': [self.ids['commitment']]}, salt='s3')
        f = self.fold([sup])
        self.assertIn(sup['id'], [r['id'] for r in f['refused']])
        self.assertEqual(self.item(f, 'commitments', 'commitment')['by'], '2026-10-30')

    def test_untrusted_or_other_type_never_supersedes(self):
        say = self.mk(PLAYER, self.H, 'say', {'text': 'x'}, {'supersedes': [self.ids['venue_card']]}, salt='s4')
        unt = self.mk(PLAYER, self.H, 'supersede', {'title': 'gone'}, {'supersedes': [self.ids['plan_card']]},
                      reason='untrusted', salt='s5')
        f = self.fold([say, unt])
        self.assertIn(self.ids['venue_card'], [c['id'] for c in f['cards']])
        self.assertEqual(self.item(f, 'cards', 'plan_card')['title'], 'Draft the first season plan')

    def test_person_under_a_decision_may_supersede(self):
        dec = self.mk(STEWARD, self.C, 'decide', {'text': 'The offer is reopened'}, salt='s6')
        sup = self.mk(STEWARD, self.C, 'supersede', {'title': 'Host the second gathering'},
                      {'supersedes': [self.ids['offer']], 'answers': [dec['id']]}, ts='2026-10-21T09:01:00-07:00',
                      salt='s7')
        f = self.fold([dec, sup])
        self.assertEqual(self.item(f, 'cards', 'offer')['title'], 'Host the second gathering')

    def test_empty_supersede_retracts(self):
        sup = self.mk(PLAYER, self.H, 'supersede', {}, {'supersedes': [self.ids['sighting']]}, salt='s8')
        f = self.fold([sup])
        self.assertIn(sup['id'], [r['id'] for r in f['refused']])        # the sighting is the aide's, not the player's
        own = self.mk(PLAYER, self.H, 'supersede', {}, {'supersedes': [self.ids['proposal']]}, salt='s9')
        d = self.item(self.fold([own]), 'decisions', 'proposal')
        self.assertEqual((d['state'], d['retracted_by']), ('retracted', own['id']))


class TestLinksAndClaims(Base):
    def test_items_carry_merged_links(self):
        a = self.mk(PLAYER, self.H, 'card', {'title': 'First'}, ts='2026-10-21T09:00:00-07:00', salt='l1')
        b = self.mk(PLAYER, self.H, 'card', {'title': 'Second'}, {'predecessor': [a['id']]},
                    ts='2026-10-21T09:01:00-07:00', salt='l2')
        hand = self.mk(PLAYER, self.H, 'hand', {'card': b['id'], 'to': STEWARD},
                       {'serves': [self.ids['plan_card']]}, ts='2026-10-21T09:02:00-07:00', salt='l3')
        f = self.fold([a, b, hand])
        second = [c for c in f['cards'] if c['id'] == b['id']][0]
        self.assertEqual(second['links']['predecessor'], [a['id']])
        self.assertEqual(second['links']['serves'], [self.ids['plan_card']])
        for key in record.LINK_KEYS:
            self.assertIsInstance(second['links'][key], list)
        self.assertEqual(self.item(f, 'threads', 'thread')['links']['anchored_to'], [self.ids['plan_card']])

    def test_claim_until_expires(self):
        card = self.mk(STEWARD, self.C, 'card', {'title': 'Held a while'}, ts='2026-10-21T09:00:00-07:00', salt='c1')
        claim = self.mk(PLAYER, self.C, 'claim', {'card': card['id'], 'until': '2026-10-22'},
                        ts='2026-10-21T09:05:00-07:00', salt='c2')
        live = [c for c in self.fold([card, claim], now='2026-10-22T18:00:00-07:00')['cards'] if c['id'] == card['id']][0]
        self.assertEqual((live['state'], live['holder']), ('taken', PLAYER))
        gone = [c for c in self.fold([card, claim], now='2026-10-23T08:00:00-07:00')['cards'] if c['id'] == card['id']][0]
        self.assertEqual((gone['state'], gone['holder'], gone['claim_expired']), ('ready', STEWARD, claim['id']))
        handed = self.mk(PLAYER, self.C, 'hand', {'card': card['id'], 'to': STEWARD},
                         ts='2026-10-21T10:00:00-07:00', salt='c3')
        moved = [c for c in self.fold([card, claim, handed], now='2026-10-23T08:00:00-07:00')['cards']
                 if c['id'] == card['id']][0]
        self.assertEqual((moved['state'], moved['holder']), ('taken', STEWARD))   # handed on: the claim no longer decides


class TestTime(Base):
    def test_backdated_revoke_and_backdated_agent_line(self):
        a = record.append(self.hq, AIDE, PLAYER, 'sight', {'text': 'before the revoke'}, reason='delegated',
                          ts='2026-10-21T10:00:00-07:00', key_dir=KEYS)['line']
        rv = record.append(self.hq, PLAYER, PLAYER, 'revoke', {'delegation': self.ids['delegation']},
                           ts='2026-10-19T08:00:00-07:00', key_dir=KEYS)['line']      # dated before everything
        self.assertIn(a['id'], rv['body']['seen'])
        b = record.append(self.hq, AIDE, PLAYER, 'sight', {'text': 'after the revoke'}, reason='delegated',
                          ts='2026-10-20T08:00:00-07:00', key_dir=KEYS)['line']       # dated before the revoke
        f = self.fold()
        texts = [s.get('text') for s in f['sightings']]
        self.assertIn('before the revoke', texts)                 # the revoke saw it: the backdate changes nothing
        self.assertIn('A neighbouring cell needs a venue', texts)
        self.assertEqual(self.invalid(f)[b['id']]['invalid_reason'], 'the delegation was revoked before this line')
        self.assertIn(b['id'], [x['id'] for x in f['flags'] if x['flag'] == 'ts_backward'])

    def test_time_ahead_is_flagged_and_moves_nothing(self):
        far = self.mk(PLAYER, self.H, 'sight', {'text': 'from the far future'}, ts='9999-12-31T00:00:00+00:00', salt='t1')
        f = self.fold([far])
        self.assertIn(far['id'], [x['id'] for x in f['flags'] if x['flag'] == 'ts_ahead'])
        self.assertTrue(f['as_of'].startswith('2026-10'))
        self.assertEqual(self.item(f, 'delegations', 'delegation')['state'], 'live')


class TestDelegation(Base):
    def test_agent_line_outside_delegation_invalid_and_kept(self):
        f = self.fold()
        self.assertEqual(self.invalid(f)[self.ids['invalid_agent']]['invalid_reason'],
                         'the delegation does not cover this holon')
        self.assertNotIn('Book the hall', [c.get('title') for c in f['cards']])
        self.assertIn(self.ids['invalid_agent'], {l['id'] for l in record.read(self.cell)['lines']})

    def test_agent_line_inside_delegation_valid(self):
        self.assertEqual(self.item(self.fold(), 'cards', 'notes_card')['actor'], AIDE)

    def test_agent_with_neither_consent_nor_once_stays_invalid(self):
        commit = self.mk(AIDE, self.H, 'commit', {'card': self.ids['notes_card'], 'by': '2026-11-01'}, salt='a1')
        ratify = self.mk(AIDE, self.H, 'ratify', {}, {'answers': [self.ids['decision']]}, salt='a2')
        inv = self.invalid(self.fold([commit, ratify]))
        self.assertIn('never ticks', inv[commit['id']]['invalid_reason'])   # the once-delegation is used up
        self.assertIn('never ticks', inv[ratify['id']]['invalid_reason'])

    def test_once_delegated_commit_signed_for_and_used_up(self):
        f = self.fold()
        c = self.item(f, 'commitments', 'agent_commit')
        self.assertTrue(c['signed_for'])
        self.assertEqual(c['signed_for_by'][0]['source'], {'delegate': self.ids['once_delegation'], 'once': True})
        again = self.mk(AIDE, self.H, 'commit', {'card': self.ids['notes_card'], 'by': '2026-11-09'},
                        ts='2026-10-21T09:00:00-07:00', salt='o2')
        self.assertIn(again['id'], self.invalid(self.fold([again])))

    def test_consent_ratify_signed_for(self):
        f = self.fold()
        d = self.item(f, 'decisions', 'consent_decision')
        self.assertEqual(d['state'], 'ratified')
        self.assertTrue(d['signed_for'])
        src = d['signed_for_by'][0]['source']
        self.assertEqual((src['consent'], src['line']), (make_fixtures.CONSENT, self.ids['consent_say']))
        forged = self.mk(AIDE, self.H, 'ratify', {'consent': 'yes'}, {'answers': [self.ids['decision'],
                                                                                   self.ids['injection']]}, salt='o3')
        self.assertIn('bare consent never counts', self.invalid(self.fold([forged]))[forged['id']]['invalid_reason'])

    def test_revoked_delegation_no_longer_covers(self):
        offer = self.mk(AIDE, self.H, 'offer', {'title': 'After the revoke'}, salt='b')
        self.assertIn('revoked', self.invalid(self.fold([offer]))[offer['id']]['invalid_reason'])


class TestWitness(Base):
    def test_witness_other_than_named_is_a_note(self):
        card = self.mk(PLAYER, self.C, 'card', {'title': 'Audited work', 'kind': 'milestone'}, salt='n1')
        com = self.mk(PLAYER, self.C, 'commit', {'card': card['id'], 'by': '2026-10-30', 'witness': 'person:auditor'},
                      ts='2026-10-21T09:01:00-07:00', salt='n2')
        kept = self.mk(PLAYER, self.C, 'kept', {'commitment': com['id']}, ts='2026-10-21T09:02:00-07:00', salt='n3')
        wit = self.mk(STEWARD, self.C, 'witness', {'note': 'looks done to me'}, {'witnesses': [kept['id']]},
                      ts='2026-10-21T09:03:00-07:00', salt='n4')
        c = [x for x in self.fold([card, com, kept, wit])['commitments'] if x['id'] == com['id']][0]
        self.assertEqual(c['state'], 'claimed')            # kept, unwitnessed
        self.assertEqual([n['id'] for n in c['witness_notes']], [wit['id']])
        self.assertNotIn('witnessed_by', c)


class TestAudience(Base):
    def test_person_publish_widens_own_lines(self):
        f = self.fold()
        self.assertEqual(f['audience'][self.ids['plan_card']], 'members')
        self.assertEqual(f['audience'][self.ids['commitment']], 'members')
        self.assertEqual(f['audience'][self.ids['notes_card']], 'holon')
        self.assertIn(self.ids['notes_card'], self.ids['held_back'])

    def test_audience_never_widens_otherwise(self):
        agent_pub = self.mk(AIDE, self.H, 'publish', {'lines': [self.ids['sighting']], 'audience': 'public'}, salt='p1')
        others = self.mk(STEWARD, self.C, 'publish', {'lines': [self.ids['tea']], 'audience': 'public'}, salt='p2')
        f = self.fold([agent_pub, others])
        self.assertEqual(f['audience'][self.ids['sighting']], 'holon')
        self.assertEqual(f['audience'][self.ids['tea']], 'holon')
        self.assertIn(agent_pub['id'], self.invalid(f))
        self.assertIn('own lines', [r.get('invalid_reason') for r in f['refused'] if r['id'] == others['id']][0])
        with self.assertRaises(ValueError):
            holon.publish(self.hq, make_fixtures.CELL, [self.ids['plan_card']], AIDE)


class TestUntrustedAndInjection(Base):
    def test_untrusted_is_proposal_only(self):
        f = self.fold()
        self.assertEqual([p['id'] for p in f['proposals']], [self.ids['untrusted']])
        self.assertNotIn('Push the plan to the public forge', [c.get('title') for c in f['cards']])

    def test_order_in_text_is_data(self):
        lines = self.lines()
        r = record.read_all(self.hq)
        before = sorted(os.path.join(x, n) for x, _, ns in os.walk(self.tmp) for n in ns)
        with_it = record.fold(lines, self.types, r['keepers'], clock='2026-10-24T12:00:00-07:00')
        without = record.fold([l for l in lines if l['id'] != self.ids['injection']], self.types, r['keepers'],
                              clock='2026-10-24T12:00:00-07:00')
        after = sorted(os.path.join(x, n) for x, _, ns in os.walk(self.tmp) for n in ns)
        self.assertEqual(before, after)
        thread = self.item(with_it, 'threads', 'thread')
        self.assertIn(make_fixtures.INJECTION, [x.get('text') for x in thread['lines']])
        for coll in ('cards', 'commitments', 'decisions', 'delegations', 'tea', 'invalid', 'proposals'):
            self.assertEqual(json.dumps(with_it[coll], sort_keys=True, default=str),
                             json.dumps(without[coll], sort_keys=True, default=str), coll)


class TestExport(Base):
    def test_names_hidden_export(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        text = '\n'.join(record.dumps(l) for l in exp['lines'])
        for name in ('person:', 'agent:', 'player', 'steward'):
            self.assertNotIn(name, text)
        for l in exp['lines']:
            self.assertTrue(record.check_id(l), l['id'])
            self.assertNotIn('sig', l)
            self.assertTrue(record._is_elided(l['prev']))
        self.assertIn('Find a venue', text)
        v = record.verify_attestation(exp['attestation'], exp['lines'], holon_dir=self.cell)
        self.assertEqual((v['ids_ok'], v['sig']), (True, 'valid'))
        self.assertFalse(record.verify_attestation(exp['attestation'], exp['lines'][1:])['ids_ok'])

    def test_elided_lines_never_act(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        f = record.fold(exp['lines'], self.types)
        self.assertEqual(f['cards'], [])

    def test_shipped_export_matches_shipped_fixtures(self):
        shipped = os.path.join(ENGINE, 'fixtures', make_fixtures.EXPORT)
        if not os.path.isfile(shipped):
            self.skipTest('no shipped export')
        with open(shipped, encoding='utf-8') as f:
            rows = [json.loads(x) for x in f if x.strip()]
        att, lines = rows[0], rows[1:]
        cell = os.path.join(ENGINE, 'fixtures', 'hq', 'cells', make_fixtures.CELL)
        v = record.verify_attestation(att, lines, holon_dir=cell)
        self.assertEqual((v['ids_ok'], v['sig']), (True, 'valid'), v)
        self.assertEqual(record.verify_attestation(att, lines)['sig'], 'unchecked')   # never the export's own word
        self.assertTrue(all(record.check_id(l) for l in lines))

    def test_cli_posture_names(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'export', self.cell,
                            '--posture', 'names-hidden'], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.splitlines()[0])['posture'], 'names-hidden')
        bad = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'export', self.cell,
                              '--posture', 'chatham'], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(bad.returncode, 0)


class TestHolon(Base):
    def test_init_layout_and_key(self):
        d = os.path.join(self.tmp, 'new')
        kd = os.path.join(self.tmp, 'newkeys')
        res = holon.init(d, 'a-room', 'room', 'person:host', ts='2026-10-21T09:00:00-07:00', salt='e',
                         key_dir=kd, make_key=True)
        for name in ('holon.json', 'types.json', 'calendar.json', '.gitignore', 'record', 'published', 'plan'):
            self.assertTrue(os.path.exists(os.path.join(d, name)), name)
        self.assertTrue(os.path.isfile(os.path.join(kd, 'lionsberg-person-host')))
        self.assertEqual(res['holon']['id'], res['inception']['id'])
        self.assertTrue(res['inception']['body']['pubkey'].startswith('ssh-ed25519 '))
        f = record.fold_hq(d)
        self.assertEqual(f['trust'][res['inception']['id']], 'signed')

    def test_calendar_is_schedule_shaped(self):
        d = os.path.join(self.tmp, 'cal')
        holon.init(d, 'a-cell', 'cell', 'person:host', sign=False)
        with open(os.path.join(d, 'calendar.json'), encoding='utf-8') as f:
            cal = json.load(f)
        try:
            import schedule
        except Exception as e:   # schedule.py is another part of the kit
            self.skipTest('schedule.py not importable: %s' % e)
        c = schedule.Calendar(cal)
        self.assertEqual(c.actor_minutes('person:host'), 480)
        day = dt.date(2026, 10, 26)
        self.assertEqual(480 / c.capacity('person:host', day), 1)     # a 480-minute card is one day

    def test_hold(self):
        self.assertEqual(holon.hold(self.hq), [self.hq, self.cell])

    @unittest.skipUnless(shutil.which('git'), 'git is not installed')
    def test_join_writes_the_joiner_as_for(self):
        src = os.path.join(self.tmp, 'cell-src')
        holon.init(src, 'second-cell', 'cell', STEWARD, ts='2026-10-21T09:00:00-07:00', salt='f', key_dir=KEYS)
        g = ['git', '-C', src, '-c', 'user.name=test', '-c', 'user.email=test@example.invalid']
        subprocess.run(['git', 'init', '-q', src], check=True)
        subprocess.run(g + ['add', '.'], check=True)
        subprocess.run(g + ['commit', '-q', '-m', 'inception'], check=True)
        res = holon.join(self.hq, src, 'second-cell', actor='person:guest', ts='2026-10-21T09:05:00-07:00',
                         salt='g', key_dir=KEYS)
        self.assertTrue(res['ok'], res['said'])
        last = record.last_line(os.path.join(self.hq, 'record', record.actor_file('person:guest')))
        self.assertEqual((last['actor'], last['for']), ('person:guest', 'person:guest'))
        self.assertIn(os.path.join(self.hq, 'cells', 'second-cell'), holon.hold(self.hq))
        self.assertTrue(all(p['ok'] for p in holon.pull(self.hq) if p['cell'] == 'second-cell'))

    def test_bad_cell_name_refused(self):
        self.assertFalse(holon.join(self.hq, 'x', '../escape')['ok'])


def pk(actor):
    return record.pubkey_of(record.make_key(actor, KEYS))


class TestRecheck(Base):
    """The re-check's attacks (poc2) and the rules that close them."""

    def ts(self, n):
        return '2026-10-21T%02d:%02d:00-07:00' % (10 + n // 60, n % 60)

    def test_n1_member_cannot_take_over_a_key(self):
        m2 = 'person:member-two'
        admit = self.mk(PLAYER, self.C, 'join', {'who': m2, 'pubkey': pk(m2)}, ts=self.ts(1), salt='k1')
        take = self.mk(m2, self.C, 'join', {'who': PLAYER, 'pubkey': pk(m2)}, ts=self.ts(2), salt='k2')
        keeper = self.mk(m2, self.C, 'join', {'who': STEWARD, 'pubkey': pk(m2)}, ts=self.ts(3), salt='k3')
        forged = self.mk(PLAYER, self.C, 'decide', {'text': 'as the player'}, ts=self.ts(4), salt='k4',
                         key=record.find_key(None, m2, KEYS))
        f = self.fold([admit, take, keeper, forged])
        inv = self.invalid(f)
        self.assertEqual(f['trust'][admit['id']], 'signed')
        self.assertEqual(inv[take['id']]['invalid_reason'], 'bad_admission')
        self.assertEqual(inv[keeper['id']]['invalid_reason'], 'bad_admission')
        self.assertEqual(inv[forged['id']]['invalid_reason'], 'bad_signature')

    def test_n1_rotation_by_own_key_and_by_keeper_with_witness(self):
        rot_dir = os.path.join(self.tmp, 'rot')
        new = record.make_key(PLAYER, rot_dir)
        rot = self.mk(PLAYER, self.C, 'join', {'who': PLAYER, 'pubkey': record.pubkey_of(new)}, ts=self.ts(1), salt='r1')
        after = self.mk(PLAYER, self.C, 'sight', {'text': 'with the new key'}, ts=self.ts(2), salt='r2', key=new)
        f = self.fold([rot, after])
        self.assertEqual(f['trust'][after['id']], 'signed')
        m2 = 'person:member-three'
        admit = self.mk(STEWARD, self.C, 'join', {'who': m2, 'pubkey': pk(m2)}, ts=self.ts(1), salt='r3')
        third = record.make_key(PLAYER, os.path.join(self.tmp, 'rot3'))
        kr = self.mk(STEWARD, self.C, 'join', {'who': PLAYER, 'pubkey': record.pubkey_of(third), 'witness': m2},
                     ts=self.ts(2), salt='r4')
        early = self.mk(PLAYER, self.C, 'sight', {'text': 'before the witness'}, ts=self.ts(3), salt='r5', key=third)
        self.assertEqual(self.invalid(self.fold([admit, kr, early]))[early['id']]['invalid_reason'], 'bad_signature')
        self.heads[(self.C, PLAYER)] = early['prev']
        wit = self.mk(m2, self.C, 'witness', {'note': 'the new key is theirs'}, {'witnesses': [kr['id']]},
                      ts=self.ts(3), salt='r6')
        late = self.mk(PLAYER, self.C, 'sight', {'text': 'after the witness'}, ts=self.ts(4), salt='r7', key=third)
        self.assertEqual(self.fold([admit, kr, wit, late])['trust'][late['id']], 'signed')

    def test_n1_only_its_person_reaffirms_an_agent(self):
        hijack = self.mk(STEWARD, self.C, 'affirm', {'agent': AIDE, 'pubkey': pk('person:member-two')}, salt='h1')
        line = self.mk(AIDE, self.C, 'sight', {'text': 'still the aide'}, salt='h2')
        f = self.fold([hijack, line])
        self.assertEqual(self.invalid(f)[hijack['id']]['invalid_reason'], 'bad_admission')
        self.assertEqual(f['trust'][line['id']], 'signed')

    def test_n2_consent_needs_the_persons_signed_line(self):
        bare = self.mk(AIDE, self.H, 'commit', {'card': self.ids['notes_card'], 'by': '2026-11-01', 'consent': 'yes'},
                       ts=self.ts(1), salt='c1')
        said = self.mk(PLAYER, self.H, 'say', {'text': 'something else entirely'}, ts=self.ts(2), salt='c2')
        wrong_words = self.mk(AIDE, self.H, 'ratify', {'consent': 'yes, ratify it'},
                              {'answers': [self.ids['decision'], said['id']]}, ts=self.ts(3), salt='c3')
        unsigned_say = self.mk(PLAYER, self.H, 'say', {'text': 'yes, ratify it'}, ts=self.ts(4), salt='c4', sign=False)
        on_unverified = self.mk(AIDE, self.H, 'ratify', {'consent': 'yes, ratify it'},
                                {'answers': [self.ids['decision'], unsigned_say['id']]}, ts=self.ts(5), salt='c5')
        f = self.fold([bare, said, wrong_words, unsigned_say, on_unverified])
        inv = self.invalid(f)
        for x in (bare, wrong_words, on_unverified):
            self.assertIn('bare consent never counts', inv[x['id']]['invalid_reason'])
        self.assertNotIn(bare['id'], [s['id'] for s in f['signed_for']])

    def test_n2_n4_unaffirmed_agent_at_home(self):
        home = lambda l: dict(l, _held_in=self.H, _file='record/x', _home_record=True)
        dlg = self.mk(PLAYER, self.H, 'delegate', {'to': 'agent:helper', 'scope': ['card'], 'holons': [self.H],
                                                    'until': '2026-12-31'}, ts=self.ts(1), salt='u1')
        card = self.mk('agent:helper', self.H, 'card', {'title': 'helper card'}, ts=self.ts(2), salt='u2', sign=False)
        consent = self.mk('agent:helper', self.H, 'commit', {'card': card['id'], 'by': '2026-12-01', 'consent': 'yes'},
                          ts=self.ts(3), salt='u3', sign=False)
        f = self.fold([home(dlg), home(card), home(consent)])
        unv = {u['id'] for u in f['unverified']}
        self.assertIn(card['id'], unv)
        self.assertIn(consent['id'], unv)
        aff = self.mk(PLAYER, self.H, 'affirm', {'agent': 'agent:helper'}, ts=self.ts(1), salt='u4')
        f2 = self.fold([home(dlg), home(aff), home(card)])
        self.assertIn('helper card', [c.get('title') for c in f2['cards']])

    def test_n3_no_person_alone_rewrites_anothers_commitment(self):
        com = self.mk(STEWARD, self.C, 'commit', {'card': self.ids['venue_card'], 'by': '2026-11-10', 'witness': PLAYER},
                      ts=self.ts(1), salt='s1')
        dec = self.mk(PLAYER, self.C, 'decide', {'text': 'the player decides'}, ts=self.ts(2), salt='s2')
        sup = self.mk(PLAYER, self.C, 'supersede', {'by': '2030-01-01', 'size': 1},
                      {'supersedes': [com['id']], 'answers': [dec['id']]}, ts=self.ts(3), salt='s3')
        f = self.fold([com, dec, sup])
        c = [x for x in f['commitments'] if x['id'] == com['id']][0]
        self.assertEqual(c['by'], '2026-11-10')
        self.assertIn('never rewrites', [r['invalid_reason'] for r in f['refused'] if r['id'] == sup['id']][0])
        rat = self.mk(STEWARD, self.C, 'ratify', {}, {'answers': [dec['id']]}, ts=self.ts(4), salt='s4')
        c2 = [x for x in self.fold([com, dec, sup, rat])['commitments'] if x['id'] == com['id']][0]
        self.assertEqual(c2['by'], '2030-01-01')          # the committor ratified the decision

    def test_n5_attestation_checked_against_the_record(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        att, lines = exp['attestation'], exp['lines']
        self.assertEqual(record.verify_attestation(att, lines, holon_dir=self.cell)['sig'], 'valid')
        fake = {k: v for k, v in att.items() if k != 'sig'}
        evil = record.make_key('person:outsider', KEYS)
        fake['key_id'] = record.key_id(record.pubkey_of(evil))
        fake['sig'] = record.sign_text(record._attest_digest(fake), evil)
        self.assertEqual(record.verify_attestation(fake, lines, holon_dir=self.cell)['sig'], 'bad_attestation')
        self.assertEqual(record.verify_attestation(fake, lines)['sig'], 'unchecked')

    def test_n5_export_holds_back_untrusted_lines(self):
        forged = record.make_line(PLAYER, PLAYER, self.C, 'decide', {'text': 'forged'}, ts=self.ts(1), salt='e1')
        with open(os.path.join(self.cell, 'record', record.actor_file(STEWARD)), 'a', encoding='utf-8') as f:
            f.write(record.dumps(forged) + '\n')
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        self.assertNotIn(forged['id'], [l['id'] for l in exp['lines']])
        self.assertIn('held back', exp['said'])

    def test_n6_key_names_carry_the_kind(self):
        self.assertEqual(record.key_name('person:x'), 'lionsberg-person-x')
        self.assertEqual(record.key_name('agent:x'), 'lionsberg-agent-x')
        self.assertNotEqual(record.make_key('person:same', KEYS), record.make_key('agent:same', KEYS))

    def test_n7_fork_holds_until_the_survivor_is_named(self):
        base = self.heads[(self.C, PLAYER)]
        a = self.mk(PLAYER, self.C, 'card', {'title': 'branch a', 'kind': 'milestone'}, prev=base, ts=self.ts(1), salt='f1')
        b = self.mk(PLAYER, self.C, 'card', {'title': 'branch b', 'kind': 'milestone'}, prev=base, ts=self.ts(1), salt='f2')
        f = self.fold([a, b])
        self.assertEqual({x['id'] for x in f['forked']}, {a['id'], b['id']})
        titles = [c.get('title') for c in f['cards']]
        self.assertNotIn('branch a', titles)
        self.assertNotIn('branch b', titles)
        pick = self.mk(PLAYER, self.C, 'say', {'text': 'branch a holds'}, {'supersedes': [a['id']]}, prev=a['id'],
                       ts=self.ts(2), salt='f3')
        f2 = self.fold([a, b, pick])
        titles = [c.get('title') for c in f2['cards']]
        self.assertIn('branch a', titles)
        self.assertNotIn('branch b', titles)

    def test_n8_once_delegation_binds_the_body(self):
        want = {'commitment': self.ids['commitment'], 'note': 'exactly this'}
        od = self.mk(PLAYER, self.H, 'delegate', {'to': AIDE, 'scope': ['kept'], 'holons': [self.H], 'once': True,
                                                   'until': '2026-12-31', 'body_digest': record.body_digest(want)},
                     ts=self.ts(1), salt='o1')
        other = self.mk(AIDE, self.H, 'kept', {'commitment': self.ids['commitment'], 'note': 'something else'},
                        ts=self.ts(2), salt='o2')
        same = self.mk(AIDE, self.H, 'kept', want, ts=self.ts(3), salt='o3')
        f = self.fold([od, other, same])
        self.assertIn('body_digest', self.invalid(f)[other['id']]['invalid_reason'])
        self.assertNotIn(same['id'], self.invalid(f))
        self.assertIn(same['id'], [s['id'] for s in f['signed_for']])

    def test_verify_cli_needs_keys(self):
        path = os.path.join(self.cell, 'record', record.actor_file(STEWARD))
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'verify', path],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'verify', self.cell],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout)['signed'], 10)
        self.assertEqual(record.verify(record.last_line(path))['sig'], 'unchecked')


class TestRound2(Base):
    """The Test Holon's second round (D12 to D14), the signature cache, and clones."""

    def test_d12_copies_vouched_for_a_cell_only_reader(self):
        r = record.read(self.cell)
        f = record.fold(r['lines'], self.types, {self.C: STEWARD}, clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(f['trust'][self.ids['plan_card']], 'vouched')
        card = [c for c in f['cards'] if c['id'] == self.ids['plan_card']][0]
        self.assertEqual(card['vouched_by'], self.ids['publish'])
        stray = [l for l in record.read(self.hq)['lines'] if l['id'] == self.ids['turn']][0]
        with open(os.path.join(self.cell, 'published', 'stray.jsonl'), 'w', encoding='utf-8') as fh:
            fh.write(record.dumps({k: v for k, v in stray.items() if not k.startswith('_')}) + '\n')
        r = record.read(self.cell)
        f = record.fold(r['lines'], self.types, {self.C: STEWARD}, clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(f['trust'][self.ids['turn']], 'unverified')   # no publish line vouches for it

    def test_d14_attestation_by_role_with_the_holon_key(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        att = exp['attestation']
        self.assertEqual(att['by'], 'the keeper of %s' % self.C)
        self.assertEqual(att['signer'], 'holon:%s' % self.C)
        self.assertNotIn('steward', json.dumps(att))
        self.assertEqual(record.verify_attestation(att, exp['lines'], holon_dir=self.cell)['sig'], 'valid')
        d = os.path.join(self.tmp, 'with-key')
        res = holon.init(d, 'keyed', 'cell', 'person:host', key_dir=os.path.join(self.tmp, 'hk'), make_key=True,
                         holon_key=True)
        self.assertTrue(res['inception']['body']['holon_pubkey'].startswith('ssh-ed25519 '))
        self.assertTrue(os.path.basename(res['holon_key']).startswith('lionsberg-holon-'))

    def test_sigcache_on_disk(self):
        record._SIG_CACHE.clear()
        record.fold_hq(self.hq, clock='2026-10-24T12:00:00-07:00')
        path = os.path.join(self.hq, '.sigcache')
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        with open(path, encoding='ascii') as fh:
            n = len(fh.readlines())
        self.assertGreater(n, 40)
        record._SIG_CACHE.clear()
        record.load_sigcache(path)
        self.assertGreaterEqual(len(record._SIG_CACHE), n)
        record._SIG_DISK['path'] = None
        # a cache others can write is ignored: a poisoned entry never makes a forged line valid
        forged = self.mk(PLAYER, self.H, 'decide', {'text': 'forged'}, salt='p1', sign=False)
        forged['sig'] = record.sign_id(forged['id'], record.find_key(None, STEWARD, KEYS))
        ck = record._cache_key((forged['id'], forged['sig'], PLAYER, self.ids['pubkeys'][PLAYER]))
        record._SIG_CACHE.clear()
        os.chmod(path, 0o644)
        with open(path, 'a', encoding='ascii') as fh:
            fh.write('%s 1\n' % ck)
        record.load_sigcache(path)
        self.assertNotIn(ck, record._SIG_CACHE)
        record._SIG_DISK['path'] = None

    def clone_setup(self, scope=('affirm', 'body', 'card')):
        clone = 'agent:player-aide.c1'
        dlg = self.mk(PLAYER, self.H, 'delegate', {'to': AIDE, 'scope': list(scope), 'holons': [self.H],
                                                    'until': '2026-12-31', 'clones': ['*']},
                      ts='2026-10-21T10:00:00-07:00', salt='b1')
        aff = self.mk(AIDE, self.H, 'affirm', {'agent': clone, 'pubkey': pk(clone)}, ts='2026-10-21T10:01:00-07:00',
                      salt='b2')
        claim = self.mk(clone, self.H, 'body', {'name': 'c1', 'state': 'claimed', 'task': 'notes'},
                        ts='2026-10-21T10:02:00-07:00', salt='b3')
        card = self.mk(clone, self.H, 'card', {'title': 'the clone\'s card'}, ts='2026-10-21T10:03:00-07:00', salt='b4')
        return clone, [dlg, aff, claim, card]

    def test_clone_under_delegation_counts(self):
        clone, lines = self.clone_setup()
        f = self.fold(lines, clock=NEAR)
        self.assertIn('the clone\'s card', [c.get('title') for c in f['cards']])
        self.assertNotIn(lines[1]['id'], self.invalid(f))

    def test_clone_without_delegation_is_invalid(self):
        clone, lines = self.clone_setup(scope=('card',))
        f = self.fold(lines, clock=NEAR)
        self.assertEqual(self.invalid(f)[lines[1]['id']]['invalid_reason'], 'bad_admission')
        self.assertIn(lines[3]['id'], [u['id'] for u in f['unverified']])

    def test_clone_after_done_and_when_stale(self):
        clone, lines = self.clone_setup()
        done = self.mk(clone, self.H, 'body', {'name': 'c1', 'state': 'done'}, ts='2026-10-21T10:04:00-07:00', salt='b5')
        after = self.mk(clone, self.H, 'card', {'title': 'after done'}, ts='2026-10-21T10:05:00-07:00', salt='b6')
        f = self.fold(lines + [done, after], clock=NEAR)
        self.assertIn(after['id'], [u['id'] for u in f['unverified']])
        clone2, lines2 = self.clone_setup()
        self.heads[(self.H, clone)] = lines[3]['id']
        stale = self.mk(clone, self.H, 'card', {'title': 'three days on'}, ts='2026-10-24T11:00:00-07:00', salt='b7')
        self.assertIn(stale['id'], [u['id'] for u in self.fold(lines + [stale], clock=NEAR)['unverified']])
        # a clone that freezes its clock is still stale by the reader's clock
        self.heads[(self.H, clone)] = lines[3]['id']
        frozen = self.mk(clone, self.H, 'card', {'title': 'frozen'}, ts='2026-10-21T10:02:00-07:00', salt='b8')
        f = self.fold(lines + [frozen], clock='2026-10-23T12:00:00-07:00')
        self.assertIn(frozen['id'], [u['id'] for u in f['unverified']])
        self.assertIn(lines[3]['id'], [u['id'] for u in f['unverified']])


class TestPass4(Base):
    """The third re-check (T1 to T7), the paper rule, and the Test Holon's third round (D16 to D19)."""

    def ts(self, n):
        return '2026-10-21T%02d:%02d:00-07:00' % (10 + n // 60, n % 60)

    def consent_pair(self, words, act, for_digest=None, n=1):
        say = self.mk(PLAYER, self.H, 'say', {'text': words, 'consent_v': record.CONSENT_V,
                                              'consent_for': for_digest or record.consent_digest(act)},
                      ts=self.ts(n), salt='cs%d' % n)
        return say

    def test_t1_consent_names_the_act_and_is_used_once(self):
        body = {'card': self.ids['notes_card'], 'by': '2026-12-01', 'size': 30}
        say = self.consent_pair('yes, commit me to the notes', {'type': 'commit', 'holon': self.H, 'body': body})
        act = self.mk(AIDE, self.H, 'commit', dict(body, consent='yes, commit me to the notes'), {'answers': [say['id']]},
                      ts=self.ts(2), salt='a1')
        again = self.mk(AIDE, self.H, 'commit', dict(body, consent='yes, commit me to the notes'),
                        {'answers': [say['id']]}, ts=self.ts(3), salt='a2')
        bigger = self.mk(AIDE, self.H, 'commit', dict(body, size=999, consent='yes, commit me to the notes'),
                         {'answers': [say['id']]}, ts=self.ts(4), salt='a3')
        f = self.fold([say, act, again, bigger])
        inv = self.invalid(f)
        self.assertNotIn(act['id'], inv)
        self.assertIn(act['id'], [x['id'] for x in f['signed_for']])
        self.assertIn('bare consent never counts', inv[again['id']]['invalid_reason'])     # used once
        self.assertIn('bare consent never counts', inv[bigger['id']]['invalid_reason'])    # another act

    def test_t1_substring_and_one_letter_never_count(self):
        body = {'note': 'r'}
        say = self.consent_pair('yes, ratify the weekly meeting',
                                {'type': 'ratify', 'holon': self.H, 'links': {'answers': [self.ids['decision']]}, 'body': body})
        sub = self.mk(AIDE, self.H, 'ratify', dict(body, consent='yes'), {'answers': [self.ids['decision'], say['id']]},
                      ts=self.ts(2), salt='b1')
        say2 = self.consent_pair('y', {'type': 'ratify', 'holon': self.H, 'links': {'answers': [self.ids['decision']]},
                                       'body': {'note': 's'}}, n=3)
        one = self.mk(AIDE, self.H, 'ratify', {'note': 's', 'consent': 'y'}, {'answers': [self.ids['decision'], say2['id']]},
                      ts=self.ts(4), salt='b2')
        inv = self.invalid(self.fold([say, sub, say2, one]))
        self.assertIn(sub['id'], inv)
        self.assertIn(one['id'], inv)

    def test_f1_consent_binds_type_holon_and_links(self):
        d1, d2 = self.ids['decision'], self.ids['consent_decision']
        act = {'type': 'ratify', 'holon': self.H, 'links': {'answers': [d1]}, 'body': {'note': 'ok'}}
        say = self.consent_pair('I ratify the first decision', act, n=1)
        other = self.mk(AIDE, self.H, 'ratify', {'note': 'ok', 'consent': 'I ratify the first decision'},
                        {'answers': [say['id'], d2]}, ts=self.ts(2), salt='f1')
        say2 = self.consent_pair('a fine note', {'type': 'witness', 'holon': self.H, 'body': {'note': 'fine'}}, n=3)
        typed = self.mk(AIDE, self.H, 'decide', {'note': 'fine', 'text': 'x', 'consent': 'a fine note'},
                        {'answers': [say2['id']]}, ts=self.ts(4), salt='f2')
        f = self.fold([say, other, say2, typed])
        inv = self.invalid(f)
        self.assertIn(other['id'], inv)                 # written for the first decision, never the second
        self.assertIn(typed['id'], inv)                 # written for a witness, never a decide
        self.assertNotEqual([e for e in self.item(f, 'decisions', 'consent_decision')['events'] if e == other['id']],
                            [other['id']])
        right = self.mk(AIDE, self.H, 'ratify', {'note': 'ok', 'consent': 'I ratify the first decision'},
                        {'answers': [say['id'], d1]}, ts=self.ts(5), salt='f3')
        self.assertNotIn(right['id'], self.invalid(self.fold([say, right])))

    def test_f3_keyed_agent_unsigned_at_home_is_paper(self):
        home = lambda l: dict(l, _held_in=self.H, _file='record/x', _home_record=True)
        line = self.mk(AIDE, self.H, 'card', {'title': 'unsigned, by a keyed agent'}, ts=self.ts(1), salt='g1', sign=False)
        f = self.fold([home(line)])
        self.assertEqual(f['trust'][line['id']], 'paper')
        wit = self.mk(PLAYER, self.H, 'witness', {'note': 'seen'}, {'witnesses': [line['id']]}, ts=self.ts(2), salt='g2')
        self.assertEqual(self.fold([home(line), wit])['trust'][line['id']], 'home')

    def test_f5_admission_answers_a_request_and_earlier_lines_stay_paper(self):
        dave = 'person:dave'
        dk = record.make_key(dave, KEYS)
        req = self.mk(dave, self.C, 'request', {'title': 'let me in', 'to': STEWARD}, ts=self.ts(1), salt='d1')
        adm = self.mk(STEWARD, self.C, 'join', {'who': dave, 'pubkey': record.pubkey_of(dk), 'role': 'member'},
                      {'answers': [req['id']]}, ts=self.ts(2), salt='d2')
        old = self.mk(dave, self.C, 'decide', {'text': 'dated before he was let in'}, ts='2026-10-01T00:00:00-07:00',
                      salt='d3')
        after = self.mk(dave, self.C, 'sight', {'text': 'after admission'}, ts=self.ts(5), salt='d4')
        f = self.fold([req, adm, old, after])
        self.assertEqual(f['trust'][req['id']], 'signed')      # the request the admission answers is kept
        self.assertEqual(f['trust'][old['id']], 'paper')       # written before the admission
        self.assertEqual(f['trust'][after['id']], 'signed')

    def test_d22_holon_affirm_writes_a_clone(self):
        record.append(self.hq, PLAYER, PLAYER, 'delegate',
                      {'to': AIDE, 'scope': ['affirm', 'body', 'card'], 'holons': [self.H], 'until': '2026-12-31',
                       'clones': ['player-aide.*']}, ts='2026-10-21T10:00:00-07:00', key_dir=KEYS)
        clone = 'agent:player-aide.d22'
        r = holon.affirm(self.hq, PLAYER, clone, pk(clone), prime=AIDE, ts='2026-10-21T10:01:00-07:00', key_dir=KEYS)
        self.assertEqual((r['line']['actor'], r['line']['for']), (AIDE, PLAYER))
        f = record.fold_hq(self.hq, clock=NEAR)
        self.assertNotIn(r['line']['id'], self.invalid(f))
        self.assertEqual(f['admitted'][self.H][clone]['via'], 'clone')
        with self.assertRaises(ValueError):
            holon.affirm(self.hq, PLAYER, 'agent:someone', None, prime=AIDE)

    def test_d14_hidden_attestation_names_no_signer(self):
        d = os.path.join(self.tmp, 'nokey')
        res = holon.init(d, 'nokey', 'cell', PLAYER, key_dir=KEYS)
        record.append(d, PLAYER, PLAYER, 'sight', {'text': 'seen'}, key_dir=KEYS)
        exp = record.export(d, 'names-hidden', key_dir=KEYS)
        self.assertEqual(exp['attestation']['signer'], 'the keeper')
        self.assertNotIn('player', json.dumps(exp['attestation']))
        self.assertEqual(record.verify_attestation(exp['attestation'], exp['lines'], holon_dir=d)['sig'], 'valid')
        self.assertTrue(res['key'])

    def cell_only(self, extra=()):
        r = record.read(self.cell)
        return record.fold(r['lines'] + list(extra), self.types, {self.C: STEWARD}, clock='2026-10-24T12:00:00-07:00')

    def publish_copies(self, copies, keys):
        path = os.path.join(self.cell, 'published', record.actor_file(PLAYER))
        with open(path, 'a', encoding='utf-8') as fh:
            for c in copies:
                fh.write(record.dumps(c) + '\n')
        return self.mk(PLAYER, self.C, 'publish', {'lines': [c['id'] for c in copies], 'audience': 'members',
                                                    'keys': keys}, ts=self.ts(9), salt='pv')

    def test_t2_vouching_rules(self):
        fake = 'e' * 64
        steward_key = record.find_key(None, STEWARD, KEYS)
        ghost = 'agent:ghost'
        gk = record.make_key(ghost, KEYS)

        def copy(actor, typ, body, key, salt):
            l = record.make_line(actor, PLAYER, fake, typ, body, ts=self.ts(5), salt=salt)
            l['sig'] = record.sign_id(l['id'], key)
            return l
        forged = copy(PLAYER, 'decide', {'text': 'signed with the steward key'}, steward_key, 'v1')
        unaff = copy(ghost, 'claim', {'card': self.ids['venue_card']}, gk, 'v2')
        badsig = copy(AIDE, 'claim', {'card': self.ids['venue_card']}, gk, 'v3')
        honest = copy(PLAYER, 'claim', {'card': self.ids['venue_card']}, record.find_key(None, PLAYER, KEYS), 'v4')
        pub = self.publish_copies([forged, unaff, badsig, honest],
                                  {PLAYER: record.pubkey_of(steward_key), ghost: record.pubkey_of(gk),
                                   AIDE: self.ids['pubkeys'][AIDE]})
        f = self.cell_only([pub])
        inv = self.invalid(f)
        self.assertEqual(inv[forged['id']]['invalid_reason'], 'bad_vouch')     # differs from the key admitted here
        self.assertIn(unaff['id'], [u['id'] for u in f['unverified']])         # an agent nobody affirmed here
        self.assertEqual(inv[badsig['id']]['invalid_reason'], 'bad_signature')
        venue = [c for c in f['cards'] if c['id'] == self.ids['venue_card']][0]
        self.assertEqual(venue['state'], 'ready')                              # no copy acts on the cell's own card
        self.assertEqual(f['trust'][honest['id']], 'bad_vouch')                # the publish line vouched the wrong key

    def test_t3_attestation_role_bound_and_whole(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        lines = exp['lines']
        mem = record.export(self.cell, 'names-hidden', exporter=PLAYER, key_dir=KEYS)
        self.assertEqual(mem['attestation']['by'], 'a member of %s' % self.C)
        self.assertEqual(record.verify_attestation(mem['attestation'], mem['lines'], holon_dir=self.cell)['sig'], 'valid')
        claim = {k: v for k, v in mem['attestation'].items() if k != 'sig'}
        claim['by'] = 'the keeper of %s' % self.C
        claim['sig'] = record.sign_text(record._attest_digest(claim), record.find_key(None, PLAYER, KEYS))
        self.assertEqual(record.verify_attestation(claim, mem['lines'], holon_dir=self.cell)['sig'], 'bad_attestation')
        hk = record.find_key(None, 'holon:%s' % self.C, KEYS)
        sub = lines[:3]
        trim = {k: v for k, v in exp['attestation'].items() if k != 'sig'}
        trim.update(count=len(sub), ids_sha256=record._sha('\n'.join(l['id'] for l in sub)))
        trim['sig'] = record.sign_text(record._attest_digest(trim), hk)
        v = record.verify_attestation(trim, sub, holon_dir=self.cell)
        self.assertFalse(v['ids_ok'])
        self.assertIn('whole set', v['said'])

    def test_t3_holon_key_only_for_the_keeper(self):
        mem = record.export(self.cell, 'names-hidden', exporter=PLAYER, key_dir=KEYS)
        self.assertEqual(mem['attestation']['signer'], 'a member')      # named by role, never by handle
        self.assertEqual(mem['attestation']['key_id'], record.key_id(self.ids['pubkeys'][PLAYER]))

    def test_t4_cache_rows_need_the_hmac(self):
        forged = self.mk(STEWARD, self.C, 'decide', {'text': 'never said'}, salt='p1', sign=False)
        forged['sig'] = record.sign_id(forged['id'], record.find_key(None, PLAYER, KEYS))
        ck = record._cache_key((forged['id'], forged['sig'], STEWARD, record.read(self.cell)['lines'] and
                                record.holon_keys(self.cell)[STEWARD]))
        path = os.path.join(self.hq, '.sigcache')
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        os.write(fd, ('%s 1 %s\n' % (ck, '0' * 64)).encode())
        os.close(fd)
        record._SIG_CACHE.clear()
        with open(os.path.join(self.cell, 'record', record.actor_file(PLAYER)), 'a', encoding='utf-8') as fh:
            fh.write(record.dumps(forged) + '\n')
        f = record.fold_hq(self.hq, clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(self.invalid(f)[forged['id']]['invalid_reason'], 'bad_signature')
        real = record.append(self.cell, STEWARD, STEWARD, 'decide', {'text': 'really said'}, key_dir=KEYS)['line']
        ck2 = record._cache_key((real['id'], real['sig'], STEWARD, record.holon_keys(self.cell)[STEWARD]))
        fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        os.write(fd, ('%s 0 %s\n' % (ck2, '0' * 64)).encode())
        os.close(fd)
        record._SIG_CACHE.clear()
        f = record.fold_hq(self.hq, clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(f['trust'][real['id']], 'signed')                 # a 0 row never suppresses a line
        with open(path, encoding='ascii') as fh:
            rows = [r.split() for r in fh if r.strip()]
        self.assertTrue(all(len(r) == 3 for r in rows if r[0] not in (ck, ck2)))

    def test_t5_t6_clone_handles(self):
        dlg = self.mk(PLAYER, self.H, 'delegate', {'to': AIDE, 'scope': ['affirm', 'body', 'card'], 'holons': [self.H],
                                                    'until': '2026-12-31', 'clones': ['*']}, ts=self.ts(1), salt='q1')
        stray = self.mk(AIDE, self.H, 'affirm', {'agent': 'agent:someone-else', 'pubkey': pk('agent:someone-else')},
                        ts=self.ts(2), salt='q2')
        f = self.fold([dlg, stray], clock=NEAR)
        self.assertEqual(self.invalid(f)[stray['id']]['invalid_reason'], 'bad_admission')
        squat_name = 'agent:player-aide.taken'
        theirs = self.mk(STEWARD, self.C, 'affirm', {'agent': squat_name, 'pubkey': pk(squat_name)}, ts=self.ts(1), salt='q3')
        squat = self.mk(AIDE, self.H, 'affirm', {'agent': squat_name, 'pubkey': pk(squat_name)}, ts=self.ts(3), salt='q4')
        f = self.fold([dlg, theirs, squat], clock=NEAR)
        self.assertEqual(self.invalid(f)[squat['id']]['invalid_reason'], 'bad_admission')

    def test_d16_key_dir_honored(self):
        kd = os.path.join(self.tmp, 'envkeys')
        old = os.environ.get('LIONSBERG_KEY_DIR')
        os.environ['LIONSBERG_KEY_DIR'] = kd
        try:
            p = record.make_key('person:env-made')
            self.assertEqual(os.path.dirname(p), kd)
            self.assertEqual(record.find_key(None, 'person:env-made'), p)
            res = holon.init(os.path.join(self.tmp, 'envh'), 'envh', 'cell', 'person:env-host', make_key=True,
                             holon_key=True)
            self.assertEqual(os.path.dirname(res['key']), kd)
            self.assertEqual(os.path.dirname(res['holon_key']), kd)
        finally:
            if old is None:
                os.environ.pop('LIONSBERG_KEY_DIR', None)
            else:
                os.environ['LIONSBERG_KEY_DIR'] = old

    def test_d17_signature_cache_for_any_reader(self):
        record._SIG_CACHE.clear()
        with record.signature_cache(self.hq):
            r = record.read_all(self.hq)
            record.fold(r['lines'], self.types, r['keepers'], clock='2026-10-24T12:00:00-07:00')
        with open(os.path.join(self.hq, '.sigcache'), encoding='ascii') as fh:
            self.assertGreater(len(fh.readlines()), 40)

    def test_d18_same_second_admission_order(self):
        newagent = 'agent:helper-two'
        same = '2026-10-21T11:00:00-07:00'
        dlg = self.mk(PLAYER, self.H, 'delegate', {'to': newagent, 'scope': ['card'], 'holons': [self.H],
                                                    'until': '2026-12-31'}, ts='2026-10-21T10:59:00-07:00', salt='o1')
        aff = self.mk(PLAYER, self.H, 'affirm', {'agent': newagent, 'pubkey': pk(newagent)}, ts=same, salt='o2')
        card = self.mk(newagent, self.H, 'card', {'title': 'same second'}, ts=same, salt='o3')
        f = self.fold([card, aff, dlg])          # the agent's line first, in the same second
        self.assertIn('same second', [c.get('title') for c in f['cards']])

    def test_d19_attestation_heads_name_no_one(self):
        exp = record.export(self.cell, 'names-hidden', key_dir=KEYS)
        text = json.dumps(exp['attestation'])
        for name in ('person:', 'agent:', 'player', 'steward'):
            self.assertNotIn(name, text)


class TestPass6(Base):
    """The Test Holon's checks: the contract version (D24) and recovery after a refused push (D25)."""

    def test_d24_contract_and_consent_version(self):
        inc = [l for l in record.read(self.hq)['lines'] if l['id'] == self.ids['hq_inception']][0]
        self.assertEqual(inc['body']['contract'], record.CONTRACT)
        self.assertEqual(self.fold()['problems'], [])
        act = {'type': 'ratify', 'holon': self.H, 'links': {'answers': [self.ids['decision']]}, 'body': {'note': 'v'}}
        unversioned = self.mk(PLAYER, self.H, 'say', {'text': 'yes, ratify it', 'consent_for': record.consent_digest(act)},
                              ts='2026-10-21T10:01:00-07:00', salt='cv1')
        use = self.mk(AIDE, self.H, 'ratify', {'note': 'v', 'consent': 'yes, ratify it'},
                      {'answers': [unversioned['id'], self.ids['decision']]}, ts='2026-10-21T10:02:00-07:00', salt='cv2')
        self.assertIn(use['id'], self.invalid(self.fold([unversioned, use])))
        old = os.path.join(self.tmp, 'old')
        holon.init(old, 'old', 'person', 'person:host', sign=False)
        path = os.path.join(old, 'record', record.actor_file('person:host'))
        with open(path, encoding='utf-8') as fh:
            line = json.loads(fh.readline())
        line['body'].pop('contract')
        line['id'] = record.compute_id(line)
        f = record.fold([dict(line, _home_record=True, _file='record/x', _held_in=line['id'])], None,
                        clock='2026-10-24T12:00:00-07:00')
        self.assertIn('contract_unknown', [p['kind'] for p in f['problems']])

    @unittest.skipUnless(shutil.which('git'), 'git is not installed')
    def test_d25_two_homes_push_in_the_same_minute(self):
        env_g = ['git', '-c', 'user.name=t', '-c', 'user.email=t@test.invalid', '-c', 'commit.gpgsign=false']
        bare = os.path.join(self.tmp, 'cell.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare], check=True)
        seed = os.path.join(self.tmp, 'seed')
        holon.init(seed, 'cell', 'cell', STEWARD, key_dir=KEYS)
        subprocess.run(['git', 'init', '-q', '-b', 'main', seed], check=True)
        subprocess.run(env_g + ['-C', seed, 'add', '-A'], check=True)
        subprocess.run(env_g + ['-C', seed, 'commit', '-qm', 'inception'], check=True)
        subprocess.run(['git', '-C', seed, 'push', '-q', bare, 'HEAD:main'], check=True)
        homes = {}
        for who in ('person:home-one', 'person:home-two'):
            hq = os.path.join(self.tmp, who.split(':')[1])
            holon.init(hq, who, 'person', who, sign=False)
            homes[who] = (hq, holon.join(hq, bare, 'cell', actor=who)['path'])
        for who, (hq, c) in homes.items():
            record.append(c, who, who, 'say', {'text': 'from ' + who}, ts='2026-10-21T10:00:00-07:00', sign=False)
            subprocess.run(env_g + ['-C', c, 'add', '-A'], check=True)
            subprocess.run(env_g + ['-C', c, 'commit', '-qm', who], check=True)
        first = holon.push(homes['person:home-one'][0])
        second = holon.push(homes['person:home-two'][0])
        self.assertTrue(first[0]['ok'], first)
        self.assertTrue(second[0]['ok'], second)
        self.assertIn('after bringing in', second[0]['said'])
        back = holon.pull(homes['person:home-one'][0])
        self.assertTrue(back[0]['ok'], back)
        c1 = homes['person:home-one'][1]
        self.assertTrue(os.path.isfile(os.path.join(c1, 'record', record.actor_file('person:home-two'))))

    @unittest.skipUnless(shutil.which('git'), 'git is not installed')
    def test_d25_a_real_conflict_stops_and_says_so(self):
        env_g = ['git', '-c', 'user.name=t', '-c', 'user.email=t@test.invalid', '-c', 'commit.gpgsign=false']
        bare = os.path.join(self.tmp, 'c2.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare], check=True)
        seed = os.path.join(self.tmp, 'seed2')
        holon.init(seed, 'cell', 'cell', STEWARD, sign=False)
        subprocess.run(['git', 'init', '-q', '-b', 'main', seed], check=True)
        subprocess.run(env_g + ['-C', seed, 'add', '-A'], check=True)
        subprocess.run(env_g + ['-C', seed, 'commit', '-qm', 'inception'], check=True)
        subprocess.run(['git', '-C', seed, 'push', '-q', bare, 'HEAD:main'], check=True)
        clones = []
        for n in ('a', 'b'):
            hq = os.path.join(self.tmp, 'h' + n)
            holon.init(hq, n, 'person', 'person:h' + n, sign=False)
            c = holon.join(hq, bare, 'cell', actor='person:h' + n)['path']
            record.append(c, STEWARD, STEWARD, 'say', {'text': n}, sign=False)    # both write one file: a real conflict
            subprocess.run(env_g + ['-C', c, 'add', '-A'], check=True)
            subprocess.run(env_g + ['-C', c, 'commit', '-qm', n], check=True)
            clones.append(hq)
        self.assertTrue(holon.push(clones[0])[0]['ok'])
        res = holon.push(clones[1])
        self.assertFalse(res[0]['ok'])
        self.assertIn('forced', res[0]['said'])


GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@test.invalid', '-c', 'commit.gpgsign=false']


@unittest.skipUnless(shutil.which('git'), 'git is not installed')
class TestPass7(Base):
    """The last security look: the pull and join gate (M1), the home's id (H2), publish without links (H1),
    and unknown contracts (L3)."""

    def g(self, d, *a):
        return subprocess.run(GIT + ['-C', d] + list(a), capture_output=True, text=True)

    def world(self):
        bare = os.path.join(self.tmp, 'cell.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare], check=True)
        seed = os.path.join(self.tmp, 'seed')
        holon.init(seed, 'cell', 'cell', 'person:carol', sign=False)
        subprocess.run(['git', 'init', '-q', '-b', 'main', seed], check=True)
        self.g(seed, 'add', '-A'); self.g(seed, 'commit', '-qm', 'inception')
        self.g(seed, 'push', '-q', bare, 'HEAD:main')
        hq = os.path.join(self.tmp, 'alice')
        holon.init(hq, 'alice', 'person', 'person:alice', sign=False)
        res = holon.join(hq, bare, 'cell', actor='person:alice')
        self.assertTrue(res['ok'], res['said'])
        other = os.path.join(self.tmp, 'other')
        subprocess.run(['git', 'clone', '-q', bare, other], check=True)
        return bare, hq, res['path'], other

    def line(self, d, actor, text):
        record.append(d, actor, actor, 'say', {'text': text}, sign=False)
        self.g(d, 'add', '-A'); self.g(d, 'commit', '-qm', text)

    def test_m1_rewound_history_is_refused(self):
        bare, hq, mine, other = self.world()
        self.line(other, 'person:carol', 'carol-2'); self.g(other, 'push', '-q')
        self.assertTrue(holon.pull(hq)[0]['ok'])
        self.line(mine, 'person:alice', 'alice-2')
        self.g(other, 'reset', '-q', '--hard', 'HEAD~1')
        self.line(other, 'person:mallory', 'mallory-1'); self.g(other, 'push', '-q', '-f')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('history was rewritten', res[0]['said'])
        self.assertFalse(holon.push(hq)[0]['ok'])                       # never sends a replay of another's commit

    def test_m1_changed_lines_links_and_the_homes_own_file_are_refused(self):
        bare, hq, mine, other = self.world()
        self.line(mine, 'person:alice', 'alice-1'); self.assertTrue(holon.push(hq)[0]['ok'])
        self.g(other, 'pull', '-q')
        path = os.path.join(other, 'record', record.actor_file('person:carol'))
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('{"edited": true}\n')
        self.g(other, 'commit', '-qam', 'rewrite carol'); self.g(other, 'push', '-q')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('changed or removed', res[0]['said'])
        bare, hq, mine, other = self.world_fresh()
        apath = os.path.join(other, 'record', record.actor_file('person:alice'))
        with open(apath, 'a', encoding='utf-8') as fh:
            fh.write('{"forged": "as alice"}\n')
        self.g(other, 'add', '-A'); self.g(other, 'commit', '-qm', 'as alice'); self.g(other, 'push', '-q')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn("home's own file", res[0]['said'])
        bare, hq, mine, other = self.world_fresh()
        os.symlink(os.path.join(self.tmp, 'outside.txt'), os.path.join(other, 'record', 'person%3Abob.jsonl'))
        self.g(other, 'add', '-A'); self.g(other, 'commit', '-qm', 'link'); self.g(other, 'push', '-q')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('120000', res[0]['said'])
        self.assertFalse(os.path.islink(os.path.join(mine, 'record', 'person%3Abob.jsonl')))

    def test_m1_case_folded_paths_and_published_owners(self):
        bare, hq, mine, other = self.world()
        self.line(mine, 'person:alice', 'alice-1'); self.assertTrue(holon.push(hq)[0]['ok'])
        self.g(other, 'pull', '-q')
        twin = os.path.join(other, 'record', record.actor_file('person:alice').replace('alice', 'Alice'))
        with open(twin, 'w', encoding='utf-8') as fh:
            fh.write('{"as": "Alice"}\n')
        self.g(other, 'add', '-A'); self.g(other, 'commit', '-qm', 'case twin'); self.g(other, 'push', '-q')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertTrue('case' in res[0]['said'] or "home's own file" in res[0]['said'], res)
        bare, hq, mine, other = self.world_fresh()
        pub = os.path.join(other, 'published', record.actor_file('person:carol'))
        os.makedirs(os.path.dirname(pub), exist_ok=True)
        forged = record.make_line('person:mallory', 'person:mallory', 'x', 'say', {'text': 'in carol\'s file'}, salt='pp')
        with open(pub, 'a', encoding='utf-8') as fh:
            fh.write(record.dumps(forged) + '\n')
        self.g(other, 'add', '-A'); self.g(other, 'commit', '-qm', 'into carol'); self.g(other, 'push', '-q')
        res = holon.pull(hq)
        self.assertFalse(res[0]['ok'])
        self.assertIn('its own actor', res[0]['said'])

    def world_fresh(self):
        self.tmp = tempfile.mkdtemp(prefix='w-', dir=WORK)
        return self.world()

    def test_m1_join_refuses_a_bad_tree(self):
        bare = os.path.join(self.tmp, 'bad.git')
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare], check=True)
        seed = os.path.join(self.tmp, 'badseed')
        holon.init(seed, 'cell', 'cell', 'person:carol', sign=False)
        os.makedirs(os.path.join(seed, '.talk'))
        with open(os.path.join(seed, '.talk', 'said.jsonl'), 'w', encoding='utf-8') as fh:
            fh.write('{"by": "person:bob", "text": "alice pays"}\n')
        subprocess.run(['git', 'init', '-q', '-b', 'main', seed], check=True)
        self.g(seed, 'add', '-A', '-f'); self.g(seed, 'commit', '-qm', 'x'); self.g(seed, 'push', '-q', bare, 'HEAD:main')
        hq = os.path.join(self.tmp, 'joiner')
        holon.init(hq, 'j', 'person', 'person:alice', sign=False)
        res = holon.join(hq, bare, 'cell', actor='person:alice')
        self.assertFalse(res['ok'])
        self.assertIn('.talk/said.jsonl', res['said'])
        self.assertFalse(os.path.exists(os.path.join(hq, 'cells', 'cell')))

    def test_h1_publish_never_follows_a_link(self):
        outside = os.path.join(self.tmp, 'outside.jsonl')
        with open(outside, 'w', encoding='utf-8') as fh:
            fh.write('')
        target = os.path.join(self.cell, 'published', record.actor_file(PLAYER))
        os.remove(target)
        os.symlink(outside, target)
        with self.assertRaises(OSError):
            holon.publish(self.hq, make_fixtures.CELL, [self.ids['plan_card']], PLAYER, key_dir=KEYS)
        with open(outside, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), '')

    def test_h2_a_cell_never_takes_the_homes_id(self):
        hj = os.path.join(self.cell, 'holon.json')
        with open(hj, encoding='utf-8') as fh:
            info = json.load(fh)
        info['id'] = self.H
        with open(hj, 'w', encoding='utf-8') as fh:
            json.dump(info, fh)
        r = record.read_all(self.hq)
        self.assertTrue(r['holons'][1].get('refused'))
        self.assertEqual(record.holon_dirs(self.hq), {self.H: self.hq})
        with self.assertRaises(ValueError):
            record.append(self.cell, PLAYER, PLAYER, 'attention', {'asks_per_hour': 1}, sign=False)
        ok = record.append(self.hq, PLAYER, PLAYER, 'attention', {'asks_per_hour': 1}, key_dir=KEYS)
        self.assertTrue(ok['signed'])

    def test_l3_unknown_contract_never_acts(self):
        d = os.path.join(self.tmp, 'oldc')
        holon.init(d, 'old', 'person', 'person:host', sign=False)
        path = os.path.join(d, 'record', record.actor_file('person:host'))
        with open(path, encoding='utf-8') as fh:
            inc = json.loads(fh.readline())
        inc['body']['contract'] = '3.5.0'
        inc['id'] = record.compute_id(inc)
        dec = record.make_line('person:host', 'person:host', inc['id'], 'decide', {'text': 'acts?'}, prev=inc['id'],
                               salt='l3')
        home = lambda l: dict(l, _home_record=True, _file='record/x', _held_in=inc['id'])
        f = record.fold([home(inc), home(dec)], None, clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(f['decisions'], [])
        self.assertIn(dec['id'], [u['id'] for u in f['unverified']])
        self.assertIn('contract_unknown', [p['kind'] for p in f['problems']])


class TestCli(Base):
    def test_fold_cli_runs(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'fold', self.hq, '--only', 'cards'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)), 5)

    def test_help(self):
        for script in ('record.py', 'holon.py'):
            r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, script), '--help'],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'record.py'), 'export', '--help'],
                           capture_output=True, text=True, timeout=60)
        self.assertIn('signature', r.stdout)


if __name__ == '__main__':
    unittest.main()
