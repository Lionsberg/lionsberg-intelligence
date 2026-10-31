"""test_connections.py — the Connections view: Condition, the pulse in two directed columns, our ear, changes.

Each law of connections.py has a test that fails when it is broken. A home and one cell are made
fresh for each test in a temporary folder, signed with throwaway keys made once for the run: the
home's person (the player) and their agent, the cell's keeper (the steward), and an Agreement
between the home and the cell.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_connections.py -v
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import record          # noqa: E402
import holon           # noqa: E402
import connections     # noqa: E402

P, S, AIDE, SAIDE = 'person:player', 'person:steward', 'agent:player-aide', 'agent:steward-aide'
NOW = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KD = None


def setUpModule():
    global WORK, KD
    WORK = tempfile.mkdtemp(prefix='lionsberg-connections-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KD = os.path.join(WORK, 'keys')
    os.makedirs(KD)
    if HAVE_KEYGEN:
        for a in (P, S, AIDE, SAIDE):
            record.make_key(a, KD)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def pk(actor):
    return record.pubkey_of(record.find_key(None, actor, KD))


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the lines are signed')
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.n = 0
        self.home = os.path.join(self.tmp, 'home')
        holon.init(self.home, 'home', 'person', P, ts=self.ts(), key_dir=KD)
        self.H = record.holon_info(self.home)['id']
        holon.affirm(self.home, P, AIDE, pk(AIDE), ts=self.ts(), key_dir=KD)
        self.put(self.home, P, 'delegate', {'to': AIDE, 'scope': ['sight', 'receive', 'say'], 'holons': ['*'],
                                            'until': '2027-12-31'})
        self.cell = os.path.join(self.home, 'cells', 'first')
        holon.init(self.cell, 'first', 'cell', S, ts=self.ts(), key_dir=KD)
        self.C = record.holon_info(self.cell)['id']
        holon.admit(self.cell, S, P, pk(P), ts=self.ts(), key_dir=KD)
        holon.affirm(self.cell, P, AIDE, pk(AIDE), ts=self.ts(), key_dir=KD)
        holon.affirm(self.cell, S, SAIDE, pk(SAIDE), ts=self.ts(), key_dir=KD)
        self.put(self.cell, S, 'delegate', {'to': SAIDE, 'scope': ['sight', 'say'], 'holons': [self.C],
                                            'until': '2027-12-31'})
        self.agreement = self.agree()

    def ts(self):
        self.n += 1
        return '2026-10-20T10:%02d:%02d-07:00' % (self.n // 60, self.n % 60)

    def put(self, d, actor, typ, body=None, links=None, for_=None, reason=None, ts=None, audience='holon'):
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        for_ = for_ or (actor if actor.startswith('person:') else (P if actor == AIDE else S))
        r = record.append(d, actor, for_, typ, body, links, audience, reason, ts=ts or self.ts(), key_dir=KD)
        self.assertTrue(r['signed'], r)
        return r['line']

    def agree(self, cadence=None, bell=None, until='2027-03-20'):
        """The player proposes in the cell; the steward answers: live."""
        permits = {'write': False}
        if bell:
            permits['bell'] = list(bell)
        prop = self.put(self.cell, P, 'agree', {'with': self.C, 'crosses': ['request', 'commit', 'sight', 'receive',
                                                                            'correct', 'say', 'card'],
                                                'cadence': cadence or {'say': 604800, 'request': 3600},
                                                'permits': permits, 'until': until})
        self.put(self.cell, S, 'agree', {'with': self.H}, {'answers': [prop['id']]})
        return prop['id']

    def read(self, extra=()):
        r = record.read_all(self.home)
        lines = r['lines'] + list(extra)
        f = record.fold(lines, record.load_types(), r['keepers'], clock=NOW)
        return f, lines

    def pulse(self, now=NOW, **kw):
        f, lines = self.read()
        return connections.pulse(f, lines, self.H, self.C, now=now, **kw)

    def check(self, column, name):
        return next(c for c in column['checks'] if c['check'] == name)


class TestCondition(Base):
    """Law 1: Condition is only a person's own word for their holon; stale past until; grey when none."""

    def test_their_own_word(self):
        self.put(self.cell, S, 'condition', {'color': 'orange', 'why': 'half of us are away', 'until': '2026-12-01'})
        f, lines = self.read()
        c = connections.condition_of(f, lines, self.C, now=NOW)
        self.assertEqual((c['color'], c['basis'], c['stale']), ('orange', 'their own word', False))
        self.assertEqual(c['why'], 'half of us are away')

    def test_grey_when_none_and_never_inferred(self):
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C})       # the pulse goes red...
        f, lines = self.read()
        c = connections.condition_of(f, lines, self.C, now=NOW)
        self.assertEqual((c['color'], c['basis'], c['line']), ('grey', 'not said', None))   # ...the Condition does not

    def test_stale_past_until(self):
        self.put(self.cell, S, 'condition', {'color': 'green', 'why': 'all well', 'until': '2026-10-22'})
        f, lines = self.read()
        c = connections.condition_of(f, lines, self.C, now=NOW)
        self.assertEqual((c['color'], c['stale']), ('grey', True))
        self.assertTrue(c['basis'].startswith('stale'))

    def test_an_agents_line_never_counts(self):
        self.put(self.cell, SAIDE, 'condition', {'color': 'green', 'why': 'the agent thinks so'}, for_=S)
        f, lines = self.read()
        self.assertEqual(connections.condition_of(f, lines, self.C, now=NOW)['color'], 'grey')

    def test_a_delegated_agents_line_the_fold_trusts_still_never_counts(self):
        # a once-delegation for `condition`: the fold lets the agent sign this one act at the person's word
        self.put(self.cell, S, 'delegate', {'to': SAIDE, 'scope': ['condition'], 'holons': [self.C],
                                            'until': '2027-12-31', 'once': True})
        l = self.put(self.cell, SAIDE, 'condition', {'color': 'green', 'why': 'the agent thinks so'}, for_=S)
        f, lines = self.read()
        self.assertEqual(f['trust'].get(l['id']), 'signed')            # the fold trusts it...
        self.assertNotIn(l['id'], {x.get('id') for x in f.get('invalid') or []})
        self.assertIn(l['id'], {x.get('id') for x in f.get('signed_for') or []})
        c = connections.condition_of(f, lines, self.C, now=NOW)
        self.assertEqual((c['color'], c['line']), ('grey', None))       # ...the module's own guard keeps it grey

    def test_an_untrusted_line_never_counts(self):
        head = record._chain_head(self.cell, record.actor_file(S))
        unsigned = record.make_line(S, S, self.C, 'condition', {'color': 'green', 'why': 'unsigned'},
                                    prev=head['id'] if head else '', ts='2026-10-21T09:00:00-07:00')
        f, lines = self.read([unsigned])
        self.assertEqual(connections.condition_of(f, lines, self.C, now=NOW)['color'], 'grey')
        self.put(self.cell, S, 'condition', {'color': 'red', 'why': 'from untrusted text'}, reason='untrusted')
        f, lines = self.read()
        self.assertEqual(connections.condition_of(f, lines, self.C, now=NOW)['color'], 'grey')

    def test_a_member_who_does_not_speak_for_the_holon(self):
        self.put(self.cell, P, 'condition', {'color': 'red', 'why': 'a member, not the keeper'})
        f, lines = self.read()
        self.assertEqual(connections.condition_of(f, lines, self.C, now=NOW)['color'], 'grey')
        # the same person's word on their own holon, said in the cell both hold, does count for the home
        self.put(self.cell, P, 'condition', {'color': 'yellow', 'why': 'slow this week', 'of': self.H})
        f, lines = self.read()
        self.assertEqual(connections.condition_of(f, lines, self.H, now=NOW)['color'], 'yellow')


class TestSymmetry(Base):
    """Law 2: one side's us_to_them is the other's them_to_us, field for field; deterministic on shuffle."""

    def setUp(self):
        super().setUp()
        self.put(self.cell, P, 'say', {'text': 'is the hall free', 'to': [S], 'intent': 'ask'},
                 ts='2026-10-21T09:00:00-07:00')
        card = self.put(self.cell, S, 'card', {'title': 'Book the hall', 'minutes': 30})
        self.put(self.cell, S, 'commit', {'card': card['id'], 'by': '2026-10-22', 'committee': P})

    def test_directed_columns_mirror(self):
        f, lines = self.read()
        ab = connections.pulse(f, lines, self.H, self.C, now=NOW)
        ba = connections.pulse(f, lines, self.C, self.H, now=NOW)
        self.assertEqual(json.dumps(ab['us_to_them'], sort_keys=True), json.dumps(ba['them_to_us'], sort_keys=True))
        self.assertEqual(json.dumps(ab['them_to_us'], sort_keys=True), json.dumps(ba['us_to_them'], sort_keys=True))
        self.assertEqual(ab['color'], ba['color'])
        self.assertNotEqual(ab['us_to_them']['color'], ab['them_to_us']['color'])   # the columns are not one

    def test_shuffled_input_reads_the_same(self):
        for i in range(3):
            self.put(self.cell, P, 'say', {'text': 'q%d' % i, 'to': [S], 'intent': 'ask'},
                     ts='2026-10-21T09:0%d:00-07:00' % i)
            self.put(self.cell, S, 'say', {'text': 'r%d' % i, 'to': [P], 'intent': 'ask'},
                     ts='2026-10-21T09:1%d:00-07:00' % i)
        f, lines = self.read()
        one = json.dumps(connections.pulse(f, lines, self.H, self.C, now=NOW), sort_keys=True)
        shuffled = list(lines)
        random.Random(7).shuffle(shuffled)
        r = record.read_all(self.home)
        f2 = record.fold(shuffled, record.load_types(), r['keepers'], clock=NOW)
        for seed in range(4):
            shuffled = list(lines)
            random.Random(seed).shuffle(shuffled)
            f2 = record.fold(shuffled, record.load_types(), r['keepers'], clock=NOW)
            self.assertEqual(one, json.dumps(connections.pulse(f2, shuffled, self.H, self.C, now=NOW), sort_keys=True))


class TestColors(Base):
    """Law 3: each color is reached through its named check, and the why names it."""

    def test_green_when_every_check_is_inside(self):
        p = self.pulse()
        self.assertEqual((p['color'], p['us_to_them']['color'], p['them_to_us']['color']), ('green',) * 3)
        self.assertTrue(p['us_to_them']['why'][0].startswith('every check is inside'))

    def test_yellow_a_receipt_past_the_usual(self):
        self.put(self.cell, P, 'say', {'text': 'is the hall free', 'to': [S], 'intent': 'ask'},
                 ts='2026-10-21T09:00:00-07:00')
        p = self.pulse()
        col = p['them_to_us']                        # the steward owes the player a Receipt
        self.assertEqual(col['color'], 'yellow')
        self.assertEqual(self.check(col, 'receipts')['level'], 'yellow')
        self.assertTrue(any(w.startswith('receipts:') for w in col['why']))
        self.assertEqual(p['us_to_them']['color'], 'green')
        # a Receipt from the steward's side clears it
        line = next(l for l in self.read()[1] if l['type'] == 'say' and l['actor'] == P)
        self.put(self.cell, S, 'receive', {'of': line['id'], 'from': P, 'how': 'pull'}, {'answers': [line['id']]})
        self.assertEqual(self.pulse()['them_to_us']['color'], 'green')

    def test_orange_a_yellow_that_stood_longer_than_the_cadence(self):
        self.put(self.cell, P, 'say', {'text': 'is the hall free', 'to': [S], 'intent': 'ask'},
                 ts='2026-10-21T09:00:00-07:00')
        col = self.pulse(now='2026-11-05T12:00:00-07:00')['them_to_us']
        self.assertEqual(col['color'], 'orange')
        self.assertIn('longer than the Agreement\'s cadence', self.check(col, 'receipts')['why'])

    def test_orange_a_commitment_past_its_by_date(self):
        card = self.put(self.cell, S, 'card', {'title': 'Book the hall', 'minutes': 30})
        self.put(self.cell, S, 'commit', {'card': card['id'], 'by': '2026-10-22', 'committee': P})
        p = self.pulse()
        col = p['them_to_us']
        self.assertEqual(col['color'], 'orange')
        self.assertEqual(self.check(col, 'commitments')['rows'][0]['signal'], 'past its by-date')
        self.assertTrue(any(w.startswith('commitments:') for w in col['why']))
        self.assertEqual((p['us_to_them']['color'], p['color']), ('green', 'orange'))

    def test_red_a_live_stop(self):
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C, 'why': 'hold'})
        col = self.pulse()['us_to_them']             # their person stops our agent
        self.assertEqual(col['color'], 'red')
        self.assertTrue(any(w.startswith('stops:') for w in col['why']))

    def test_no_actor_id_in_any_why(self):
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C, 'why': 'hold'})
        p = self.pulse()
        for col in (p['us_to_them'], p['them_to_us']):
            for w in col['why'] + [c['why'] or '' for c in col['checks']]:
                self.assertNotIn('person:', w)
                self.assertNotIn('agent:', w)
        self.assertIn('their person on our agent', ' '.join(p['us_to_them']['why']))

    def test_red_a_key_in_question(self):
        f, lines = self.read()
        d = {'holons': {self.C: {'keeper': 'person:someone-else'}}}
        p = connections.pulse(f, lines, self.H, self.C, now=NOW, directory=d)
        self.assertEqual(self.check(p['them_to_us'], 'keys')['level'], 'red')   # the cell's keeper is in question
        self.assertEqual(self.check(p['us_to_them'], 'keys')['level'], 'inside')
        self.assertEqual(self.check(p['them_to_us'], 'keys')['why'], 'keeper_differs for our holon')

    def test_yellow_a_correction_not_yet_received(self):
        card = self.put(self.cell, S, 'card', {'title': 'x', 'minutes': 30})
        c = self.put(self.cell, S, 'commit', {'card': card['id'], 'by': '2026-12-22', 'committee': P})
        corr = self.put(self.cell, S, 'correct', {'why': 'the by-date is wrong'}, {'supersedes': [c['id']]})
        col = self.pulse()['us_to_them']
        self.assertEqual((col['color'], self.check(col, 'corrections')['level']), ('yellow', 'yellow'))
        self.put(self.cell, AIDE, 'receive', {'of': corr['id'], 'from': S, 'how': 'pull'}, {'answers': [corr['id']]})
        self.assertEqual(self.check(self.pulse()['us_to_them'], 'corrections')['level'], 'inside')

    def test_yellow_inside_its_buffer_from_the_schedule(self):
        card = self.put(self.cell, P, 'card', {'title': 'x', 'minutes': 30})
        c = self.put(self.cell, P, 'commit', {'card': card['id'], 'by': '2026-12-22', 'committee': S})
        col = self.pulse(schedule=[{'commitment': c['id'], 'signal': 'inside its buffer'}])['us_to_them']
        self.assertEqual(self.check(col, 'commitments')['level'], 'yellow')
        self.assertEqual(self.pulse(schedule=[{'commitment': c['id'], 'signal': 'safe'}])['us_to_them']['color'],
                         'green')

    def test_yellow_their_claim_awaits_our_witness(self):
        card = self.put(self.cell, S, 'card', {'title': 'x', 'minutes': 30})
        c = self.put(self.cell, S, 'commit', {'card': card['id'], 'by': '2026-12-22', 'committee': P})
        self.put(self.cell, S, 'kept', {'commitment': c['id']}, ts='2026-10-21T09:00:00-07:00')
        p = self.pulse()
        self.assertEqual(self.check(p['us_to_them'], 'commitments')['rows'][0]['signal'], 'unwitnessed claim')
        self.assertEqual(p['us_to_them']['color'], 'yellow')

    def test_red_an_open_pain(self):
        self.put(self.cell, S, 'sight', {'text': 'we cannot reach a member', 'kind': 'pain'})
        p = self.pulse()
        self.assertEqual(p['us_to_them']['color'], 'red')  # their pain asks for our response
        self.assertTrue(any(w.startswith('pain:') for w in p['us_to_them']['why']))
        self.assertEqual(p['color'], 'red')

    def test_red_lines_crossing_an_expired_agreement(self):
        self.agree(until='2026-10-20T11:00:00-07:00')          # a newer Agreement, already ended
        # retire the first one so the ended one is the only one that names both
        self.put(self.cell, P, 'supersede', {}, {'supersedes': [self.agreement]})
        self.put(self.cell, P, 'request', {'to': S, 'title': 'the keys'}, ts='2026-10-22T09:00:00-07:00')
        col = self.pulse()['us_to_them']
        self.assertEqual(self.check(col, 'agreement')['level'], 'red', self.check(col, 'agreement'))


class TestWhoseSighting(Base):
    """Amendment 2: an agent-voiced pain counts for nothing until its person stands on it."""

    def test_an_agents_pain_alone_changes_nothing(self):
        before = self.pulse()
        self.put(self.cell, SAIDE, 'sight', {'text': 'a member may be in trouble', 'kind': 'pain'}, for_=S)
        after = self.pulse()
        self.assertEqual(after['us_to_them']['color'], before['us_to_them']['color'])
        self.assertEqual(after['us_to_them']['color'], 'green')
        self.assertIn('wait on their person', self.check(after['us_to_them'], 'pain')['basis'])

    def test_a_say_or_thread_on_it_is_not_their_weight(self):
        s = self.put(self.cell, SAIDE, 'sight', {'text': 'a member may be in trouble', 'kind': 'pain'}, for_=S)
        self.put(self.cell, S, 'say', {'text': 'not so'}, {'anchored_to': [s['id']]})
        self.put(self.cell, S, 'thread', {'text': 'looking'}, {'anchored_to': [s['id']]})
        self.assertEqual(self.pulse()['us_to_them']['color'], 'green')

    def test_the_persons_own_resighting_stands_on_it(self):
        s = self.put(self.cell, SAIDE, 'sight', {'text': 'a member may be in trouble', 'kind': 'pain'}, for_=S)
        self.put(self.cell, S, 'sight', {'text': 'still there', 'kind': 'pain'}, {'anchored_to': [s['id']]})
        rows = self.check(self.pulse()['us_to_them'], 'pain')['rows']
        self.assertIn(s['id'], [r['sighting'] for r in rows])

    def test_the_persons_accept_turns_the_column_red(self):
        s = self.put(self.cell, SAIDE, 'sight', {'text': 'a member may be in trouble', 'kind': 'pain'}, for_=S)
        self.put(self.cell, S, 'claim', {'card': s['id']})
        col = self.pulse()['us_to_them']
        self.assertEqual(col['color'], 'red')
        self.assertEqual(self.check(col, 'pain')['rows'][0]['voice'], 'agent')


class TestEar(Base):
    """Law 4: our ear never changes the pulse; it shows only in `heard`."""

    def row(self):
        f, lines = self.read()
        res = connections.connections(self.home, now=NOW, lines=lines, folded=f)
        return next(r for r in res['rows'] if r['holon'] == self.C)

    def test_a_failed_pull_shows_only_in_heard(self):
        quiet = self.row()
        self.assertEqual(quiet['ear']['heard'], 'never')
        with open(os.path.join(self.home, '.pulled.json'), 'w', encoding='utf-8') as fh:
            json.dump({'.pull': {'cells': {'first': {'pulled_at': '2026-10-24T11:59:30-07:00'}}}}, fh)
        heard = self.row()
        self.assertEqual(heard['ear']['heard'], 'ok', heard['ear'])
        with open(os.path.join(self.home, '.heartbeat.json'), 'w', encoding='utf-8') as fh:
            json.dump({'faults': ['fault:pull:first']}, fh)
        failed = self.row()
        self.assertEqual(failed['ear']['heard'], 'failed')
        for r in (heard, failed):
            self.assertEqual(json.dumps(r['pulse'], sort_keys=True), json.dumps(quiet['pulse'], sort_keys=True))


class TestChanges(Base):
    """Law 5: one unsigned, agent-voiced sight line per change of color; nothing written to the record."""

    def record_bytes(self):
        out = {}
        for d in (self.home, self.cell):
            for sub in ('record', 'published', 'permitted'):
                p = os.path.join(d, sub)
                for name in sorted(os.listdir(p)) if os.path.isdir(p) else []:
                    with open(os.path.join(p, name), 'rb') as fh:
                        out[(d, sub, name)] = fh.read()
        return out

    def test_first_run_reports_nothing_and_writes_when_asked(self):
        res = connections.changes(self.home, now=NOW)
        self.assertTrue(res['first'])
        self.assertEqual((res['changed'], res['sightings']), ([], []))
        self.assertFalse(os.path.exists(os.path.join(self.home, connections.STATE_NAME)))
        path = connections.write_state(self.home, res['state'])
        self.assertTrue(os.path.isfile(path))

    def test_a_change_drafts_one_sighting_and_writes_nothing(self):
        connections.write_state(self.home, connections.changes(self.home, now=NOW)['state'])
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C})
        before = self.record_bytes()
        res = connections.changes(self.home, now=NOW)
        self.assertEqual(self.record_bytes(), before)
        ch = [c for c in res['changed'] if c['holon'] == self.C]
        self.assertEqual([(c['what'], c['from'], c['to']) for c in ch], [('us_to_them', 'green', 'red')])
        self.assertEqual(len(res['sightings']), 1)
        s = res['sightings'][0]
        self.assertEqual((s['type'], s['sig'], s['body']['kind'], s['body']['voice'], s['actor'], s['for']),
                         ('sight', '', connections.SIGHT_KIND, 'agent', AIDE, P))
        self.assertEqual(ch[0]['voice'], 'agent')
        self.assertFalse(ch[0]['wake']['wake'])                    # the default rule does not wake on a question

    def test_a_later_run_writes_no_state(self):
        path = connections.write_state(self.home, connections.changes(self.home, now=NOW)['state'])
        with open(path, 'rb') as fh:
            kept = fh.read()
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C})
        self.assertTrue(connections.changes(self.home, now=NOW)['changed'])
        with open(path, 'rb') as fh:
            self.assertEqual(fh.read(), kept)

    def test_only_colors_are_read_from_the_kept_state(self):
        with open(os.path.join(self.home, connections.STATE_NAME), 'w', encoding='utf-8') as fh:
            json.dump({'holons': {self.C: {'condition': [1], 'us_to_them': {'a': 1}, 'them_to_us': 'purple'}}}, fh)
        res = connections.changes(self.home, now=NOW)
        self.assertEqual((res['changed'], res['sightings']), ([], []))
        self.assertTrue(any('not a color' in x for x in res['said']))

    def test_wake_follows_the_rule_and_the_bell(self):
        self.put(self.home, P, 'limits', {'rules': [{'signal': 'sight', 'kind': ['question'], 'wake': True}],
                                          'else': 'wait'})
        connections.write_state(self.home, connections.changes(self.home, now=NOW)['state'])
        self.put(self.cell, S, 'stop', {'agents': [AIDE], 'scope': self.C})
        self.put(self.cell, S, 'condition', {'color': 'red', 'why': 'we are stopped'})
        res = connections.changes(self.home, now=NOW)
        by = {c['what']: c for c in res['changed']}
        self.assertTrue(by['us_to_them']['wake']['wake'])          # our own computed signal: own-holon
        self.assertFalse(by['condition']['wake']['wake'])          # their word: no bell permit for a question
        self.assertEqual(len(res['sightings']), len(res['changed']))


class TestEngine(Base):
    """Law 6: engine.state carries connections, honest-empty on failure."""

    def test_state_carries_connections(self):
        import engine
        st = engine.build_state(self.home, now=NOW)
        self.assertIn('connections', st)
        self.assertIn('as_of', st['connections'])
        self.assertEqual([r['holon'] for r in st['connections']['rows']], [self.C])

    def test_honest_empty_on_failure(self):
        import engine
        with mock.patch.object(engine.connections_mod, 'connections', side_effect=RuntimeError('boom')):
            st = engine.build_state(self.home, now=NOW)
        self.assertEqual(st['connections']['rows'], [])
        self.assertEqual(set(st['connections']['summary']), set(connections._empty('x')['summary']))
        self.assertTrue(any('connections.py could not' in n for n in st['notes']))


class TestRow(Base):
    """Amendment 1's summary flags; with_us and since."""

    def res(self):
        f, lines = self.read()
        return connections.connections(self.home, now=NOW, lines=lines, folded=f), lines

    def test_summary_flags_read_each_column(self):
        card = self.put(self.cell, S, 'card', {'title': 'x', 'minutes': 30})
        self.put(self.cell, S, 'commit', {'card': card['id'], 'by': '2026-10-22', 'committee': P})
        s = self.res()[0]['summary']                       # their commitment to us is past its by-date
        self.assertEqual((s['commitments_yellow_or_better'], s['ours_yellow_or_better']), (False, True))
        self.setUp()
        card = self.put(self.cell, P, 'card', {'title': 'x', 'minutes': 30})
        self.put(self.cell, P, 'commit', {'card': card['id'], 'by': '2026-10-22', 'committee': S})
        s = self.res()[0]['summary']                       # ours to them is
        self.assertEqual((s['commitments_yellow_or_better'], s['ours_yellow_or_better']), (True, False))

    def test_with_us_and_since(self):
        c1 = self.put(self.cell, S, 'card', {'title': 'x', 'minutes': 30})
        self.put(self.cell, S, 'commit', {'card': c1['id'], 'by': '2026-12-22', 'committee': P})
        c2 = self.put(self.cell, P, 'card', {'title': 'y', 'minutes': 30})
        self.put(self.cell, P, 'commit', {'card': c2['id'], 'by': '2026-12-22', 'committee': S})
        self.put(self.cell, P, 'commit', {'card': c2['id'], 'by': '2026-12-23', 'committee': S})
        self.put(self.cell, P, 'say', {'text': 'is the hall free', 'to': [S], 'intent': 'ask'})
        self.put(self.cell, S, 'request', {'to': P, 'title': 'the keys'})
        res, lines = self.res()
        w = res['rows'][0]['with_us']
        self.assertEqual((w['commitments_given'], w['commitments_received']), (2, 1))
        self.assertEqual((w['asks_waiting_on_them'], w['asks_waiting_on_us']), (1, 1))
        self.assertGreater(w['lines_crossed'], 0)
        first = min((l for l in lines if l['actor'] == P and l['holon'] == self.C), key=lambda l: l['ts'])
        self.assertEqual(res['rows'][0]['since'], first['ts'])


class TestSentAndHeardBy(Base):
    """Each row says how many lines of ours asked something of them, and when they last said one arrived."""

    def row(self):
        f, lines = self.read()
        return connections.connections(self.home, now=NOW, lines=lines, folded=f)['rows'][0]

    def test_sent_counts_ours_and_heard_by_is_their_newest_receipt(self):
        r0 = self.row()
        self.assertIsInstance(r0['sent'], int)
        self.assertIsNone(r0['heard_by_at'])
        a = self.put(self.cell, P, 'say', {'text': 'is the hall free', 'to': [S], 'intent': 'ask'}, ts='2026-10-21T09:00:00-07:00')
        b = self.put(self.cell, P, 'request', {'to': S, 'title': 'the chairs'}, ts='2026-10-21T10:00:00-07:00')
        self.put(self.cell, S, 'request', {'to': P, 'title': 'the keys'}, ts='2026-10-21T11:00:00-07:00')   # theirs: not ours
        r1 = self.row()
        self.assertEqual(r1['sent'], r0['sent'] + 2)
        self.assertIsNone(r1['heard_by_at'])                       # sent, and no word back yet
        self.put(self.cell, S, 'receive', {'of': a['id'], 'from': P, 'how': 'pull'}, {'answers': [a['id']]},
                 ts='2026-10-22T09:00:00-07:00')
        last = self.put(self.cell, S, 'receive', {'of': b['id'], 'from': P, 'how': 'pull'}, {'answers': [b['id']]},
                        ts='2026-10-23T09:00:00-07:00')
        r2 = self.row()
        self.assertEqual(r2['sent'], r1['sent'])
        self.assertEqual(r2['heard_by_at'], last['ts'])           # the newest of their Receipts on ours

    def test_our_own_receipt_is_not_theirs(self):
        x = self.put(self.cell, S, 'request', {'to': P, 'title': 'the keys'}, ts='2026-10-21T11:00:00-07:00')
        self.put(self.cell, P, 'receive', {'of': x['id'], 'from': S, 'how': 'pull'}, {'answers': [x['id']]},
                 ts='2026-10-22T09:00:00-07:00')
        self.assertIsNone(self.row()['heard_by_at'])

    def test_without_receipt_py_nothing_is_claimed(self):
        f, lines = self.read()
        with mock.patch.object(connections, 'receipt_mod', None):
            r = connections.connections(self.home, now=NOW, lines=lines, folded=f)['rows'][0]
        self.assertEqual((r['sent'], r['heard_by_at']), (None, None))

class TestRender(Base):
    def test_both_columns_and_the_summary(self):
        f, lines = self.read()
        text = connections.render(connections.connections(self.home, now=NOW, lines=lines, folded=f))
        self.assertIn('pulse: us to them', text)
        self.assertIn('pulse: them to us', text)
        self.assertIn('Not every connection is live: first', text)   # never pulled, so not live


class TestNullGuards(unittest.TestCase):
    """Law 7: null-guards and the kit's words."""

    def test_nothing_in_nothing_out(self):
        for bad in (None, '', '/no/such/home', 3.5, {}, []):
            r = connections.connections(bad, now=NOW)
            self.assertEqual(r['rows'], [])
            self.assertTrue(r['said'])
        self.assertIsNone(connections.pulse(None, None, None, None)['color'])
        self.assertIsNone(connections.pulse({}, [], 'a', 'a')['color'])
        self.assertEqual(connections.condition_of(None, None, None)['color'], 'grey')
        self.assertEqual(connections.condition_of({}, [{'id': 1.5}], 'Café')['color'], 'grey')
        self.assertIn('No connection yet', connections.render(None))
        self.assertEqual(connections.changes(None)['changed'], [])
        self.assertIn('nothing was written', connections.write_state(None, {}))

    def test_a_linked_home_is_not_read(self):
        tmp = tempfile.mkdtemp(dir=WORK)
        link = os.path.join(tmp, 'link')
        os.symlink(tmp, link)
        self.assertIn('link', connections.connections(link, now=NOW)['said'][0])

    def test_the_kits_words(self):
        with open(connections.__file__, encoding='utf-8') as fh:
            text = fh.read().lower()
        for word in ('promise', 'house'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
