"""test_receipt.py — the Receipt: written on arrival, where the line lives, once; and what has none.

The sample fixtures (fixtures/make_fixtures.py) are built once per run in a temporary folder,
signed with throwaway keys kept for the run; each test that writes copies the sample home first.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_receipt.py -v
"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import record          # noqa: E402
import receipt         # noqa: E402
import owed as owed_mod  # noqa: E402
import make_fixtures   # noqa: E402

PLAYER, STEWARD, AIDE = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
NOW = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: the fixtures are signed')
    WORK = tempfile.mkdtemp(prefix='lionsberg-receipt-test-')
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
        self.tmp = tempfile.mkdtemp(prefix='home-', dir=WORK)
        self.hq = os.path.join(self.tmp, 'hq')
        shutil.copytree(os.path.join(TEMPLATE, 'hq'), self.hq, symlinks=True)
        self.cell = os.path.join(self.hq, 'cells', make_fixtures.CELL)
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def arrive(self, **kw):
        kw.setdefault('now', NOW)
        kw.setdefault('key_dir', KEYS)
        return receipt.on_arrival(self.hq, AIDE, PLAYER, **kw)

    def put(self, d, actor, typ, body, links=None, reason=None, sign=None, ts='2026-10-22T09:00:00-07:00'):
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        return record.append(d, actor, actor if actor.startswith('person:') else PLAYER, typ, body, links,
                             reason=reason, ts=ts, sign=sign, key_dir=KEYS)['line']

    def receipt_lines(self, d):
        return [l for l in record.read(d)['lines'] if l.get('type') == 'receive' and l.get('actor') == AIDE]


class TestArrival(Base):
    def test_law1_a_second_arrival_writes_nothing(self):
        first = self.arrive()
        self.assertTrue(first['written'], first)
        self.assertEqual(first['held'], [])
        again = self.arrive()
        self.assertEqual(again['written'], [])
        self.assertEqual(receipt.pending(self.hq, {PLAYER}, AIDE), [])
        ofs = [x['of'] for x in first['written']]
        self.assertEqual(len(ofs), len(set(ofs)))                  # one Receipt per received line

    def test_law3_the_receipt_lands_where_the_line_lives(self):
        res = self.arrive()
        self.assertEqual({w['holon'] for w in res['written']}, {self.C})
        want = os.path.join(self.cell, 'record', record.actor_file(AIDE))
        for w in res['written']:
            self.assertEqual(os.path.realpath(w['file']), os.path.realpath(want))
            self.assertTrue(w['signed'])
            self.assertIsNone(w['waits'])
        # and the fold trusts it and places it on the item the line acted on
        f = record.fold_hq(self.hq)
        ag = next(i for i in f['agreements'] if i['id'] == IDS['agreement'])
        self.assertIn(AIDE, {r['actor'] for r in ag.get('receipts', [])})
        mine = {w['id'] for w in res['written']}
        self.assertFalse(mine & {x['id'] for x in f['invalid'] + f['unverified'] + f['proposals']})

    def test_the_receipt_line_is_well_formed(self):
        res = self.arrive()
        lines = {l['id']: l for l in self.receipt_lines(self.cell)}
        for w in res['written']:
            l = lines[w['id']]
            self.assertEqual(l['body']['of'], w['of'])
            self.assertEqual(l['links']['answers'], [w['of']])
            self.assertEqual((l['body']['how'], l['reason'], l['for']), ('pull', 'delegated', PLAYER))
            self.assertEqual(l['body']['from'], STEWARD)

    def test_law2_no_delegation_anywhere_writes_nothing_and_says_so(self):
        self.put(self.hq, PLAYER, 'revoke', {'delegation': IDS['surface_delegation']})
        want = {l['id'] for l in receipt.pending(self.hq, {PLAYER}, AIDE)}
        self.assertTrue(want)
        res = self.arrive()
        self.assertEqual(res['written'], [])
        self.assertEqual({h['of'] for h in res['held']}, want)
        for h in res['held']:
            self.assertIn('covers receive', h['why'])
            self.assertIn('no Receipt was written', h['why'])
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)    # only the fixtures' own receipt
        self.assertEqual(self.receipt_lines(self.hq), [])          # never an invalid line in the record

    def test_law2_a_delegation_at_home_only_writes_it_at_home(self):
        self.put(self.hq, PLAYER, 'revoke', {'delegation': IDS['surface_delegation']})
        self.put(self.hq, PLAYER, 'delegate', {'to': AIDE, 'scope': ['receive'], 'holons': [self.H], 'until': '2026-12-31'},
                 ts='2026-10-22T09:01:00-07:00')
        res = self.arrive()
        self.assertTrue(res['written'])
        self.assertEqual({w['holon'] for w in res['written']}, {self.H})
        self.assertEqual({w['waits'] for w in res['written']}, {'publish'})
        self.assertEqual({h['of'] for h in res['held']}, {w['of'] for w in res['written']})
        for h in res['held']:
            self.assertIn('covers receive in holon', h['why'])
            self.assertIn('publish', h['why'])
        f = record.fold_hq(self.hq)
        mine = {w['id'] for w in res['written']}
        self.assertFalse(mine & {x['id'] for x in f['invalid'] + f['unverified']})   # it folds valid at home
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)
        self.assertEqual(self.arrive()['written'], [])            # and still idempotent

    def assert_home_unsigned(self, res):
        self.assertTrue(res['written'])
        self.assertEqual({w['holon'] for w in res['written']}, {self.H})
        self.assertEqual({w['signed'] for w in res['written']}, {False})
        self.assertTrue(all('would not be signed by the key admitted' in h['why'] for h in res['held']))
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)    # nothing unsigned lands in the cell

    def test_high1_no_key_never_writes_an_unsigned_line_into_the_cell(self):
        empty = os.path.join(self.tmp, 'no-keys')
        os.makedirs(empty)
        self.assert_home_unsigned(self.arrive(key_dir=empty))

    def test_high1_sign_false_never_writes_into_the_cell(self):
        self.assert_home_unsigned(self.arrive(sign=False))

    def test_high1_an_unverified_receipt_never_blocks_a_good_one(self):
        agreed = IDS['agreed']
        self.put(self.cell, AIDE, 'receive', {'of': agreed, 'how': 'pull'}, {'answers': [agreed]}, sign=False)
        f = record.fold_hq(self.hq)
        bad = [l for l in self.receipt_lines(self.cell) if l['body'].get('of') == agreed]
        self.assertEqual(f['trust'].get(bad[0]['id']), 'unverified')
        res = self.arrive()
        self.assertIn(agreed, {w['of'] for w in res['written'] if w['holon'] == self.C and w['signed']})

    def test_medium3_an_agent_not_let_into_the_cell_writes_at_home(self):
        orig = record.fold_hq

        def without_admission(d, **kw):
            f = orig(d, **kw)
            f['admitted'] = {h: ({a: v for a, v in m.items() if a != AIDE} if h == self.C else m)
                             for h, m in f['admitted'].items()}
            return f
        record.fold_hq = without_admission
        try:
            res = self.arrive()
        finally:
            record.fold_hq = orig
        self.assertTrue(res['written'])
        self.assertEqual({w['holon'] for w in res['written']}, {self.H})
        self.assertTrue(all('is not let into holon' in h['why'] for h in res['held']))
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)

    def test_law8_long_line_linked_cell_and_empty_cell_are_said(self):
        with open(os.path.join(self.cell, 'record', record.actor_file(STEWARD)), 'a', encoding='utf-8') as fh:
            fh.write('{"x":"' + 'a' * 70000 + '"}\n')
        os.symlink(self.cell, os.path.join(self.hq, 'cells', 'linked'))
        os.makedirs(os.path.join(self.hq, 'cells', 'empty'))
        res = self.arrive()
        whys = ' | '.join(h['why'] for h in res['held'])
        self.assertIn('longer than', whys)
        self.assertIn('cells/linked is a link', whys)
        self.assertIn('cells/empty holds no holon', whys)
        self.assertTrue(res['written'])                           # the good lines still get their Receipts
        self.assertFalse(any('arrival stopped' in h['why'] for h in res['held']))

    def test_dry_writes_nothing(self):
        res = self.arrive(dry=True)
        self.assertTrue(res['written'])
        self.assertTrue(all(w['dry'] and w['id'] is None for w in res['written']))
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)

    def test_law4_own_lines_and_untrusted_lines_are_never_receipted(self):
        good = self.put(self.cell, STEWARD, 'request', {'to': PLAYER, 'title': 'Bring the chairs'})
        unsigned = self.put(self.cell, STEWARD, 'request', {'to': PLAYER, 'title': 'Bring a key'}, sign=False)
        untrusted = self.put(self.cell, STEWARD, 'request', {'to': PLAYER, 'title': make_fixtures.INJECTION},
                             reason='untrusted')
        own = self.put(self.cell, PLAYER, 'say', {'text': 'To myself', 'to': [PLAYER]})
        ids = {l['id'] for l in receipt.pending(self.hq, {PLAYER}, AIDE)}
        self.assertIn(good['id'], ids)
        self.assertNotIn(unsigned['id'], ids)
        self.assertNotIn(untrusted['id'], ids)
        self.assertNotIn(own['id'], ids)
        self.assertNotIn(IDS['message'], ids)                      # the person's own message to the steward
        got = {w['of'] for w in self.arrive()['written']}
        self.assertIn(good['id'], got)
        self.assertFalse(got & {unsigned['id'], untrusted['id'], own['id']})

    def test_files_are_data(self):
        line = self.put(self.cell, STEWARD, 'say', {'text': make_fixtures.INJECTION, 'to': [PLAYER]},
                        {'anchored_to': [IDS['venue_card']]})
        before = sorted(os.listdir(os.path.join(self.cell, 'record')))
        res = self.arrive()
        self.assertIn(line['id'], {w['of'] for w in res['written']})
        self.assertEqual(sorted(os.listdir(os.path.join(self.cell, 'record'))), before)   # no new file, no new actor
        for l in self.receipt_lines(self.cell):
            self.assertNotIn(make_fixtures.INJECTION, json.dumps(l))


class TestAddressedTo(unittest.TestCase):
    P, Q, H = 'person:p', 'person:q', 'holon-h'

    def L(self, typ, body=None, links=None, actor='person:q'):
        return {'id': typ + '-1', 'type': typ, 'actor': actor, 'for': actor, 'body': body or {}, 'links': links or {}}

    def test_request(self):
        self.assertTrue(receipt.addressed_to(self.L('request', {'to': self.P}), {self.P}, self.H))

    def test_offer(self):
        self.assertTrue(receipt.addressed_to(self.L('offer', {'to': self.P}), {self.P}, self.H))

    def test_say(self):
        self.assertTrue(receipt.addressed_to(self.L('say', {'text': 'x', 'to': [self.Q, self.P]}), {self.P}, self.H))

    def test_commit(self):
        self.assertTrue(receipt.addressed_to(self.L('commit', {'card': 'c', 'committee': self.P}), {self.P}, self.H))

    def test_agree(self):
        self.assertTrue(receipt.addressed_to(self.L('agree', {'with': self.H}), {self.P}, self.H))

    def test_wallet(self):
        self.assertTrue(receipt.addressed_to(self.L('wallet', {'kind': 'offer', 'to': self.P}), {self.P}, self.H))

    def test_rfg(self):
        self.assertTrue(receipt.addressed_to(self.L('rfg', {'question': 'q', 'to': self.H}), {self.P}, self.H))

    def test_escalate(self):
        self.assertTrue(receipt.addressed_to(self.L('escalate', {'about': 'd', 'to': self.H}), {self.P}, self.H))

    def test_correct(self):
        req = self.L('request', {'to': self.P})
        c = self.L('correct', {'why': 'wrong'}, {'supersedes': [req['id']]})
        self.assertTrue(receipt.addressed_to(c, {self.P}, self.H, by_id={req['id']: req}))

    def test_supersede(self):
        s = self.L('supersede', {}, {'supersedes': ['held-line']})
        self.assertTrue(receipt.addressed_to(s, {self.P}, self.H, received={'held-line'}))

    def test_not_addressed(self):
        self.assertFalse(receipt.addressed_to(self.L('request', {'to': self.Q}), {self.P}, self.H))
        self.assertFalse(receipt.addressed_to(self.L('agree', {'with': 'other'}), {self.P}, self.H))
        self.assertFalse(receipt.addressed_to(self.L('rfg', {'to': self.H}), {self.P}, None))
        self.assertFalse(receipt.addressed_to(self.L('card', {'title': 't', 'to': self.P}), {self.P}, self.H))
        self.assertFalse(receipt.addressed_to(self.L('supersede', {}, {'supersedes': ['x']}), {self.P}, self.H))


def _line(i, typ, actor, holon, ts, body=None, links=None, for_=None):
    return {'id': i, 'type': typ, 'actor': actor, 'for': for_ or actor, 'holon': holon, 'ts': ts,
            'body': body or {}, 'links': links or {}, 'reason': 'human' if actor.startswith('person:') else 'delegated'}


class TestTimeToReceipt(unittest.TestCase):
    def lines(self):
        return [
            {'id': 'home-p', 'type': 'join', 'actor': 'person:p', 'for': 'person:p', 'holon': '', 'ts': '2026-10-01T00:00:00Z',
             'body': {'role': 'inception', 'kind': 'person'}, 'links': {}},
            _line('r1', 'request', 'person:q', 'cell', '2026-10-20T09:00:00Z', {'to': 'person:p'}),
            _line('r2', 'request', 'person:q', 'cell', '2026-10-20T10:00:00Z', {'to': 'person:p'}),
            _line('r3', 'request', 'person:q', 'cell', '2026-10-21T10:00:00Z', {'to': 'person:p'}),
            _line('k1', 'receive', 'agent:p-aide', 'cell', '2026-10-20T11:30:00Z', {'of': 'r1'}, {'answers': ['r1']},
                  for_='person:p'),
            _line('k2', 'receive', 'agent:p-aide', 'cell', '2026-10-20T14:00:00Z', {'of': 'r2'}, {'answers': ['r2']},
                  for_='person:p'),
        ]

    def test_law6_pure_deterministic_and_none_yet(self):
        ls = self.lines()
        a = receipt.time_to_receipt(None, ls)
        b = receipt.time_to_receipt(None, list(reversed(json.loads(json.dumps(ls)))))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(ls, self.lines())                         # its input is untouched
        g = a['by_relationship']['cell -> home-p']
        self.assertEqual((g['from'], g['to'], g['n'], g['none_yet']), ('cell', 'home-p', 2, 1))
        self.assertEqual((g['median_hours'], g['max_hours']), (3.25, 4.0))
        rows = {x['line']: x for x in a['rows']}
        self.assertEqual(rows['r1']['hours'], 2.5)
        self.assertIsNone(rows['r3']['receipt'])
        self.assertEqual(a['as_of'], '2026-10-21T10:00:00+00:00')

    def test_medium4_the_first_receipt_is_the_earliest_moment_not_the_earliest_text(self):
        ls = [_line('r1', 'request', 'person:q', 'cell', '2026-10-20T09:00:00Z', {'to': 'person:p'}),
              _line('k1', 'receive', 'agent:a', 'cell', '2026-10-20T12:00:00-07:00', {'of': 'r1'}, {'answers': ['r1']},
                    for_='person:p'),
              _line('k2', 'receive', 'agent:a', 'cell', '2026-10-20T15:00:00Z', {'of': 'r1'}, {'answers': ['r1']},
                    for_='person:p')]
        row = receipt.time_to_receipt(None, ls)['rows'][0]
        self.assertEqual((row['receipt'], row['receipt_ts'], row['hours']), ('k2', '2026-10-20T15:00:00Z', 6.0))
        tie = ls[:2] + [_line('k0', 'receive', 'agent:a', 'cell', '2026-10-20T19:00:00Z', {'of': 'r1'},
                              {'answers': ['r1']}, for_='person:p')]
        self.assertEqual(receipt.time_to_receipt(None, tie)['rows'][0]['receipt'], 'k0')   # the same moment: by id

    def test_untrusted_receipts_do_not_count(self):
        ls = self.lines()
        ls[4] = dict(ls[4], reason='untrusted')
        g = receipt.time_to_receipt(None, ls)['by_relationship']['cell -> home-p']
        self.assertEqual((g['n'], g['none_yet']), (1, 2))
        f = {'trust': {l['id']: 'signed' for l in ls if l['id'] != 'k2'}}
        g = receipt.time_to_receipt(f, self.lines())['by_relationship']['cell -> home-p']
        self.assertEqual((g['n'], g['none_yet']), (1, 2))


class TestOwedReceipt(unittest.TestCase):
    SENT = '2026-10-20T09:00:00-07:00'
    HOLONS = [{'id': 'home', 'name': 'Home', 'kind': 'person', 'keeper': 'person:p'},
              {'id': 'cell', 'name': 'Cell', 'kind': 'cell', 'keeper': 'person:k'}]

    def items(self, **kw):
        c = {'id': 'q1', 'kind': 'card', 'holon': 'cell', 'title': 'Bring the plan', 'asked': 'request', 'to': 'person:p',
             'holder': 'person:p', 'state': 'open', 'actor': 'person:k', 'for': 'person:k', 'ts': self.SENT,
             'audience': 'holon'}
        c.update(kw)
        return {'cards': [c]}

    def at(self, hours):
        return (dt.datetime.fromisoformat(self.SENT) + dt.timedelta(hours=hours)).isoformat()

    def rows(self, items, hours, **kw):
        r = owed_mod.owed(items, now=self.at(hours), holons=self.HOLONS, receipts=True, **kw)
        return [e for e in r['entries'] if e['kind'] == 'receipt']

    def test_law7_after_a_day_and_not_before(self):
        self.assertEqual(self.rows(self.items(), 23), [])
        got = self.rows(self.items(), 25)
        self.assertEqual(len(got), 1)
        e = got[0]
        self.assertEqual((e['id'], e['holder'], e['addressee'], e['status'], e['due'], e['minutes'], e['holon']),
                         ('q1', 'person:k', 'person:p', 'waiting', None, 1, 'cell'))   # the sender waits on the addressee's Receipt
        self.assertEqual(owed_mod.RECEIPT_HOURS, 24)
        self.assertEqual(owed_mod.MINUTES['receipt'], 1)

    def test_the_constant_is_overridable(self):
        self.assertEqual(self.rows(self.items(), 25, receipt_hours=48), [])
        self.assertEqual(len(self.rows(self.items(), 3, receipt_hours=2)), 1)

    def test_low6_a_non_finite_or_negative_wait_reads_as_the_default(self):
        for h in (float('nan'), float('inf'), -5, None, 'soon'):
            self.assertEqual(self.rows(self.items(), 1, receipt_hours=h), [], h)
            self.assertEqual(len(self.rows(self.items(), 25, receipt_hours=h)), 1, h)

    def test_low5_the_cli_takes_people(self):
        import contextlib
        import io
        path = os.path.join(tempfile.mkdtemp(prefix='owed-cli-', dir=WORK), 'items.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(self.items(), fh)

        def run(*extra):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                owed_mod._main([path, '--json', '--receipts', '--home', 'home', '--now', self.at(30)] + list(extra))
            return [e for e in json.loads(buf.getvalue())['entries'] if e['kind'] == 'receipt']
        self.assertEqual(len(run()), 1)
        self.assertEqual(len(run('--people', 'person:k')), 1)
        self.assertEqual(run('--people', 'person:x,person:p'), [])

    def test_a_receipt_by_the_receiving_side_clears_it(self):
        it = self.items(receipts=[{'id': 'k', 'type': 'receive', 'actor': 'agent:p-aide', 'ts': self.at(1)}])
        self.assertEqual(self.rows(it, 30), [])
        own = self.items(receipts=[{'id': 'k', 'type': 'receive', 'actor': 'person:k', 'ts': self.at(1)}])
        self.assertEqual(len(self.rows(own, 30)), 1)              # the sender's own line is no receipt

    def test_only_what_crossed(self):
        home = self.items(holon='home', actor='person:p', **{'for': 'person:p'}, to='person:x', holder='person:x')
        self.assertEqual(self.rows(home, 30), [])
        wide = self.items(holon='home', actor='person:p', **{'for': 'person:p'}, to='person:x', holder='person:x',
                          audience='members')
        self.assertEqual([e['addressee'] for e in self.rows(wide, 30)], ['person:x'])
        self.assertEqual(len(self.rows(self.items(), 30, home='home')), 1)
        self.assertEqual(self.rows(self.items(), 30, people={'person:p'}), [])   # not sent by this holon's people

    def test_off_unless_asked_and_untrusted_never(self):
        r = owed_mod.owed(self.items(), now=self.at(30), holons=self.HOLONS)
        self.assertNotIn('receipt', [e['kind'] for e in r['entries']])
        self.assertEqual(self.rows(self.items(reason='untrusted'), 30), [])
        self.assertEqual(self.rows(self.items(state='taken'), 30), [])


class TestNullGuards(unittest.TestCase):
    def test_pure_functions_take_nothing(self):
        for bad in (None, {}, [], 3.5, 'x'):
            self.assertFalse(receipt.addressed_to(bad, {'person:p'}, 'h'))
            self.assertEqual(receipt.addressees(bad), [])
            self.assertIsNone(receipt.receipt_line(bad, AIDE, PLAYER))
            r = receipt.time_to_receipt(bad, bad)
            self.assertEqual((r['rows'], r['by_relationship'], r['as_of']), ([], {}, None))
            self.assertEqual(receipt.pending(bad, {PLAYER}), [])
        self.assertFalse(receipt.addressed_to({'type': 'request', 'body': {'to': 'person:p'}}, None, None))
        self.assertIsNone(receipt.receipt_line({'id': 'x'}, 'nobody', PLAYER))
        self.assertIsNone(receipt.receipt_line({'id': 'x'}, AIDE, AIDE))

    def test_non_nfc_names_meet(self):
        nfd = unicodedata.normalize('NFD', 'person:café')
        line = {'type': 'request', 'body': {'to': unicodedata.normalize('NFC', 'person:café')}}
        self.assertTrue(receipt.addressed_to(line, {nfd}, None))

    def test_receipt_line_is_pure_when_salted(self):
        of = {'id': 'abc', 'actor': STEWARD, 'holon': 'h', 'audience': 'members'}
        a = receipt.receipt_line(of, AIDE, PLAYER, 'mail', '2026-10-24T12:00:00-07:00', salt='s')
        b = receipt.receipt_line(dict(of), AIDE, PLAYER, 'mail', '2026-10-24T12:00:00-07:00', salt='s')
        self.assertEqual(a, b)
        self.assertEqual((a['holon'], a['audience'], a['type'], a['body']['how']), ('h', 'members', 'receive', 'mail'))
        self.assertNotIn('how', receipt.receipt_line(of, AIDE, PLAYER, 'carrier-pigeon', salt='s')['body'])


class TestArrivalGuards(Base):
    def test_a_missing_or_wrong_home_is_said_never_raised(self):
        for home in (None, '', os.path.join(self.tmp, 'nowhere'), 3.5):
            r = receipt.on_arrival(home, AIDE, PLAYER, now=NOW)
            self.assertEqual(r['written'], [])
            self.assertTrue(r['held'] and isinstance(r['held'][0]['why'], str))
        r = receipt.on_arrival(self.hq, PLAYER, PLAYER, now=NOW)
        self.assertEqual(r['written'], [])
        self.assertTrue(r['held'])

    def test_a_home_reached_through_a_link_is_never_written(self):
        link = os.path.join(self.tmp, 'link')
        os.symlink(self.hq, link)
        r = receipt.on_arrival(link, AIDE, PLAYER, now=NOW, key_dir=KEYS)
        self.assertEqual(r['written'], [])
        self.assertTrue(r['held'])
        self.assertEqual(len(self.receipt_lines(self.cell)), 1)

    def test_a_float_clock_is_honest_empty(self):
        r = receipt.on_arrival(self.hq, AIDE, PLAYER, now=3.5, key_dir=KEYS)
        self.assertTrue(r['written'])                              # read as no clock given: the machine's


class TestWords(unittest.TestCase):
    def test_the_kits_words(self):
        with open(os.path.join(ENGINE, 'receipt.py'), encoding='utf-8') as f:
            src = f.read().lower()
        for w in ('promise', ' house', 'estate', ' hq '):
            self.assertNotIn(w, src)


if __name__ == '__main__':
    unittest.main()
