"""test_wallet.py — the wallet folds wallet entries to balances per unit, and values nothing unruled.

Most tests read hand-built items (the shape record.py's fold gives); one class folds signed lines
with the same fixtures test_kinds.py builds, so the wallet is checked against the real fold.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_wallet.py -v
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import wallet  # noqa: E402

H, H2 = 'h' * 64, 'g' * 64
A, B, C = 'person:player', 'person:steward', 'person:third'


def entry(i, kind='offer', state='offered', amount=100, unit='USD-cents', to=B, for_=A, holon=H, ts=None, **kw):
    e = {'id': i, 'kind': 'wallet_entry', 'body_kind': kind, 'state': state, 'amount': amount, 'unit': unit,
         'to': to, 'for': for_, 'actor': for_, 'holon': holon, 'ts': ts or '2026-10-21T10:%02d:00-07:00' % (len(i) % 60)}
    e.update(kw)
    return e


def decision(i, text, holon=H, by=A, state='decided'):
    return {'id': i, 'kind': 'decision', 'state': state, 'text': text, 'decided_by': by, 'for': by,
            'actor': by, 'holon': holon, 'ts': '2026-10-21T11:00:00-07:00'}


class TestEntries(unittest.TestCase):
    def test_rows_are_sorted_and_carry_the_contract_fields(self):
        items = {'wallet': [entry('b2', ts='2026-10-21T10:02:00-07:00', body_for='card1', note='for the walk'),
                            entry('a1', ts='2026-10-21T10:01:00-07:00')]}
        rows = wallet.entries(items)
        self.assertEqual([r['id'] for r in rows], ['a1', 'b2'])
        self.assertEqual(set(rows[1]) >= {'id', 'holon', 'kind', 'state', 'from', 'to', 'amount', 'unit', 'for_card',
                                          'note', 'accepted_by', 'settled_by', 'witnesses', 'ts'}, True)
        self.assertEqual((rows[1]['from'], rows[1]['for_card']), (A, 'card1'))

    def test_null_guards(self):
        for bad in (None, {}, [], 3.5, 'text', {'wallet': None}, {'wallet': [None, 1, 'x']}):
            self.assertEqual(wallet.entries(bad), [])
            r = wallet.balances(bad)
            self.assertEqual((r['by_unit'], r['by_actor'], r['units'], r['convertible']), ({}, {}, [], False))
        self.assertIn('No wallet entries yet.', wallet.render(wallet.balances(None)))
        self.assertIn('No wallet entries yet.', wallet.render(None))


class TestBalances(unittest.TestCase):
    def test_an_offer_moves_nothing(self):
        r = wallet.balances({'wallet': [entry('o1'), entry('o2', state='accepted', accepted_by=B)]})
        self.assertEqual(r['by_unit']['USD-cents']['offered'], 100)
        self.assertEqual(r['by_unit']['USD-cents']['accepted'], 100)
        self.assertEqual(r['by_actor'], {})

    def test_settled_moves_from_the_for_to_the_to(self):
        r = wallet.balances({'wallet': [entry('s1', state='settled', amount=250)]})
        self.assertEqual(r['by_actor'][A]['USD-cents'], {'in': 0, 'out': 250, 'net': -250})
        self.assertEqual(r['by_actor'][B]['USD-cents'], {'in': 250, 'out': 0, 'net': 250})

    def test_a_gift_is_given(self):
        r = wallet.balances({'wallet': [entry('g1', kind='gift', amount=7)]})   # the fold keeps a lone gift offered
        self.assertEqual((r['by_unit']['USD-cents']['given'], r['by_unit']['USD-cents']['offered']), (7, 0))
        self.assertEqual(r['by_actor'][B]['USD-cents']['in'], 7)
        self.assertIn('state_basis', wallet.entries({'wallet': [entry('g1', kind='gift')]})[0])

    def test_a_retracted_entry_moves_nothing(self):
        r = wallet.balances({'wallet': [entry('r1', state='retracted', witnesses=[{'id': 'w'}])]})
        self.assertEqual(r['by_actor'], {})
        self.assertEqual(r['by_unit']['USD-cents'], {'offered': 0, 'accepted': 0, 'settled': 0, 'given': 0, 'witnessed_n': 0})

    def test_never_across_units(self):
        r = wallet.balances({'wallet': [entry('u1', state='settled', amount=100, unit='USD-cents'),
                                         entry('u2', state='settled', amount=3, unit='LIØNSBERG Unit of Value')]})
        self.assertEqual(sorted(r['by_unit']), ['LIØNSBERG Unit of Value', 'USD-cents'])
        self.assertEqual(r['by_unit']['USD-cents']['settled'], 100)
        self.assertEqual(r['by_unit']['LIØNSBERG Unit of Value']['settled'], 3)
        self.assertEqual(r['by_actor'][B], {'USD-cents': {'in': 100, 'out': 0, 'net': 100},
                                            'LIØNSBERG Unit of Value': {'in': 3, 'out': 0, 'net': 3}})
        self.assertFalse(r['convertible'])
        self.assertNotIn('total', json.dumps(r))

    def test_integers_only(self):
        r = wallet.balances({'wallet': [entry('f1', state='settled', amount=12.5), entry('f2', state='settled', amount=2.0),
                                         entry('f3', state='settled', amount=True), entry('i1', state='settled', amount=4)]})
        self.assertEqual(r['by_unit']['USD-cents']['settled'], 4)
        self.assertEqual(sorted(p['id'] for p in r['problems']), ['f1', 'f2', 'f3'])

    def test_witnessed_counts_entries(self):
        r = wallet.balances({'wallet': [entry('w1', witnesses=[{'id': 'x'}, {'id': 'y'}]), entry('w2')]})
        self.assertEqual(r['by_unit']['USD-cents']['witnessed_n'], 1)

    def test_a_lone_act_and_a_missing_party_are_said(self):
        r = wallet.balances({'wallet': [entry('l1', kind='accept'), entry('m1', state='settled', to=None)]})
        whys = {p['id']: p['why'] for p in r['problems']}
        self.assertIn('answers no entry', whys['l1'])
        self.assertIn('no to named', whys['m1'])
        self.assertEqual(r['by_unit']['USD-cents']['settled'], 100)
        self.assertEqual(r['by_actor'], {})

    def test_by_holon_and_the_holon_filter(self):
        items = {'wallet': [entry('x1', state='settled', holon=H), entry('x2', state='settled', amount=5, holon=H2)]}
        r = wallet.balances(items)
        self.assertEqual((r['by_holon'][H]['USD-cents']['settled'], r['by_holon'][H2]['USD-cents']['settled']), (100, 5))
        self.assertEqual(r['by_unit']['USD-cents']['settled'], 105)
        only = wallet.balances(items, holon=H2)
        self.assertEqual((sorted(only['by_holon']), only['by_unit']['USD-cents']['settled']), ([H2], 5))

    def test_deterministic(self):
        es = [entry('z%d' % i, state=('settled', 'offered', 'accepted')[i % 3], amount=i + 1, to=(B, C)[i % 2]) for i in range(9)]
        a = json.dumps(wallet.balances({'wallet': es}), sort_keys=True)
        b = json.dumps(wallet.balances({'wallet': list(reversed(es))}), sort_keys=True)
        self.assertEqual(a, b)

    def test_non_nfc_units_are_one_unit(self):
        r = wallet.balances({'wallet': [entry('n1', state='settled', unit='cafe\u0301'), entry('n2', state='settled', unit='caf\u00e9')]})
        self.assertEqual(list(r['by_unit']), ['caf\u00e9'])
        self.assertEqual(r['by_unit']['caf\u00e9']['settled'], 200)


class TestRepairs(unittest.TestCase):
    """The independent review's findings, each pinned."""

    def test_a_gift_gives_in_every_state_but_settled_or_retracted(self):
        for st in ('offered', 'accepted', 'witnessed', 'given'):
            r = wallet.balances({'wallet': [entry('g1', kind='gift', state=st, amount=9)]})
            self.assertEqual((r['by_unit']['USD-cents']['given'], r['by_actor'][B]['USD-cents']['in']), (9, 9), st)
        r = wallet.balances({'wallet': [entry('g1', kind='gift', state='retracted', amount=9)]})
        self.assertEqual((r['by_unit']['USD-cents']['given'], r['by_actor']), (0, {}))
        r = wallet.balances({'wallet': [entry('g1', kind='gift', state='settled', amount=9)]})
        self.assertEqual((r['by_unit']['USD-cents']['settled'], r['by_unit']['USD-cents']['given']), (9, 0))

    def test_accept_line_refuses_a_gift(self):
        with self.assertRaises(ValueError) as e:
            wallet.accept_line(entry('g' * 64, kind='gift'), B, '2026-10-31T09:00:00-07:00')
        self.assertIn('gift', str(e.exception))
        self.assertEqual(wallet.settle_line(entry('g' * 64, kind='gift'), A, '2026-10-31T09:00:00-07:00')['body']['kind'], 'settle')

    def test_a_negative_amount_is_reported_never_summed(self):
        r = wallet.balances({'wallet': [entry('n1', kind='gift', amount=-300), entry('n2', state='settled', amount=-5)]})
        self.assertEqual(r['by_unit'], {})
        self.assertEqual(r['by_actor'], {})
        self.assertEqual(sorted(p['id'] for p in r['problems']), ['n1', 'n2'])
        self.assertTrue(all('negative' in p['why'] for p in r['problems']))
        with self.assertRaises(ValueError):
            wallet.settle_line(entry('n' * 64, amount=-1), A)

    def test_a_long_amount_is_cut_in_its_problem(self):
        r = wallet.balances({'wallet': [entry('s1', amount='9' * 80000)]})
        self.assertLess(len(r['problems'][0]['why']), 300)

    def test_the_marker_takes_the_longest_held_name(self):
        long, short = 'LIØNSBERG Unit of Value', 'LIØNSBERG Unit'
        items = {'wallet': [entry('e1', unit=long), entry('e2', unit=short)],
                 'decisions': [decision('d1', 'Count it in unit: %s.' % long)]}
        ruled = {u['unit']: u['ruled'] for u in wallet.balances(items)['units']}
        self.assertEqual(ruled, {long: True, short: False})

    def test_the_marker_stands_alone_and_the_name_ends_whole(self):
        for text in ('unit: USD.cents', 'subunit: USD', 'sub-unit: USD', 'unit:USDx'):
            items = {'wallet': [entry('e1', unit='USD')], 'decisions': [decision('d1', text)]}
            self.assertFalse(wallet.balances(items)['units'][0]['ruled'], text)
        for text in ('unit: USD', 'unit:USD', 'We rule (unit: USD), today.', 'unit: USD; and unit: EUR'):
            items = {'wallet': [entry('e1', unit='USD')], 'decisions': [decision('d1', text)]}
            self.assertTrue(wallet.balances(items)['units'][0]['ruled'], text)

    def test_v0_reads_no_negation(self):
        self.assertEqual(wallet.named_units('This is not unit: USD', {'USD'}), {'USD'})

    def test_render_never_raises_and_escapes_cells(self):
        for bad in ({'units': [{'x': 1}, 3], 'by_unit': {'u': {}, 'v': None}, 'by_actor': {'a': {'u': None}, 'b': 2},
                     'problems': [{'why': None}, 3]}, {'units': 'x', 'by_unit': [1], 'by_actor': 'y', 'problems': 'z'},
                    {'by_unit': {'u': {'settled': 'many'}}}, 7, [], None):
            self.assertIsInstance(wallet.render(bad), str)
        r = wallet.balances({'wallet': [entry('s1', state='settled', unit='a|b\nc', to='person:x|y')]})
        md = wallet.render(r)
        self.assertIn('| a\\|b c | 0 | 0 | 100 | 0 | 0 |', md)
        self.assertIn('| person:x\\|y | a\\|b c | 100 | 0 | 100 |', md)

    def test_times_are_instants_not_text(self):
        late, early = '2026-10-21T09:00:00-07:00', '2026-10-21T12:00:00+00:00'    # 16:00Z after 12:00Z
        items = [entry('a1', ts=late), entry('b2', ts=early)]
        self.assertEqual([r['id'] for r in wallet.entries({'wallet': items})], ['b2', 'a1'])
        self.assertEqual(wallet.balances({'wallet': items})['as_of'], late)


class TestRuling(unittest.TestCase):
    def test_every_unit_is_unruled_until_a_decide_names_it(self):
        r = wallet.balances({'wallet': [entry('e1')]})
        self.assertEqual(r['units'], [{'unit': 'USD-cents', 'ruled': False, 'ruled_in': [], 'decisions': [],
                                       'note': wallet.UNRULED_NOTE}])

    def test_a_decide_naming_the_unit_rules_it(self):
        items = {'wallet': [entry('e1')], 'decisions': [decision('d1', 'We count in unit: USD-cents from the solstice.')]}
        u = wallet.balances(items)['units'][0]
        self.assertEqual((u['ruled'], u['decisions']), (True, ['d1']))

    def test_what_does_not_rule(self):
        cases = [
            decision('d1', 'USD-cents is fine'),                          # no marker
            decision('d2', 'unit: USD-centsX'),                           # another name
            decision('d3', 'unit: USD-cents', holon=H2),                  # another holon
            decision('d4', 'unit: USD-cents', by='agent:aide'),           # not a person
            decision('d5', 'unit: USD-cents', state='proposed'),          # not decided
            decision('d6', 'unit: USD-cents', state='retracted'),
            dict(decision('d7', 'unit: USD-cents'), reason='untrusted'),
        ]
        for d in cases:
            u = wallet.balances({'wallet': [entry('e1')], 'decisions': [d]})['units'][0]
            self.assertFalse(u['ruled'], d['id'])

    def test_a_trust_map_admits_only_signed_or_home(self):
        items = {'wallet': [entry('e1')], 'decisions': [decision('d1', 'unit: USD-cents')], 'trust': {'d1': 'vouched'}}
        self.assertFalse(wallet.balances(items)['units'][0]['ruled'])
        items['trust'] = {'d1': 'signed'}
        self.assertTrue(wallet.balances(items)['units'][0]['ruled'])

    def test_ruled_only_where_every_holon_rules_it(self):
        items = {'wallet': [entry('e1', holon=H), entry('e2', holon=H2)], 'decisions': [decision('d1', 'unit: USD-cents', holon=H)]}
        u = wallet.balances(items)['units'][0]
        self.assertEqual((u['ruled'], u['ruled_in']), (False, [H]))
        self.assertTrue(wallet.balances(items, holon=H)['units'][0]['ruled'])

    def test_a_decided_proposal_rules_by_its_decision_text(self):
        p = dict(decision('p1', 'unit: USD-cents, please'), decision='not yet')    # the proposal's text is not the decision
        self.assertFalse(wallet.balances({'wallet': [entry('e1')], 'decisions': [p]})['units'][0]['ruled'])


class TestLines(unittest.TestCase):
    NOW = '2026-10-31T09:00:00-07:00'

    def test_accept_and_settle_lines_answer_the_entry(self):
        e = entry('e' * 64)
        a = wallet.accept_line(e, B, self.NOW)
        s = wallet.settle_line(e, A, self.NOW)
        for line, kind, who in ((a, 'accept', B), (s, 'settle', A)):
            self.assertEqual((line['type'], line['body']['kind'], line['body']['amount'], line['body']['unit']),
                             ('wallet', kind, 100, 'USD-cents'))
            self.assertEqual((line['actor'], line['for'], line['holon'], line['sig']), (who, who, H, ''))
            self.assertEqual(line['links']['answers'], ['e' * 64])
            self.assertEqual(line['ts'], self.NOW)

    def test_a_line_is_a_persons_and_needs_an_entry(self):
        for bad in (None, {}, {'id': 'x'}):
            with self.assertRaises(ValueError):
                wallet.settle_line(bad, A, self.NOW)
        with self.assertRaises(ValueError):
            wallet.accept_line(entry('e1'), 'agent:aide', self.NOW)
        with self.assertRaises(ValueError):
            wallet.settle_line(entry('e1', amount=1.5), A, self.NOW)


class TestRenderAndCli(unittest.TestCase):
    def test_render_is_plain(self):
        r = wallet.balances({'wallet': [entry('s1', state='settled')]})
        md = wallet.render(r)
        self.assertIn('| USD-cents | 0 | 0 | 100 | 0 | 0 |', md)
        self.assertIn(wallet.UNRULED_NOTE, md)
        self.assertIn('| person:steward | USD-cents | 100 | 0 | 100 |', md)

    def test_cli_reads_json_and_refuses_a_link(self):
        import contextlib, io
        tmp = tempfile.mkdtemp(prefix='wallet-test-')
        try:
            p = os.path.join(tmp, 'items.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump({'wallet': [entry('s1', state='settled')]}, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(wallet._main([p, '--json', '--actor', B]), 0)
            self.assertEqual(list(json.loads(out.getvalue())['by_actor']), [B])
            ln = os.path.join(tmp, 'link.json')
            os.symlink(p, ln)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(wallet._main([ln]), 2)
                self.assertEqual(wallet._main([os.path.join(tmp, 'missing.json')]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(shutil.which('ssh-keygen'), 'ssh-keygen is needed: the fixtures are signed')
class TestAgainstTheFold(unittest.TestCase):
    """Signed lines through record.py's fold, then the wallet."""

    @classmethod
    def setUpClass(cls):
        from tests import test_kinds as tk
        cls.tk = tk
        tk.setUpModule()

    @classmethod
    def tearDownClass(cls):
        cls.tk.tearDownModule()

    def test_offer_accept_settle_and_a_ruling(self):
        tk = self.tk
        b = tk.Base(); b.setUp()
        o = b.mk(tk.PLAYER, b.C, 'wallet', {'kind': 'offer', 'amount': 12000, 'unit': 'USD-cents', 'to': tk.STEWARD,
                                            'for': tk.IDS['request']})
        f = b.fold([o])
        r = wallet.balances(f, holon=b.C)
        self.assertEqual((r['by_unit']['USD-cents']['offered'], r['by_actor']), (12000, {}))
        a = b.mk(tk.STEWARD, b.C, 'wallet', {'kind': 'accept', 'amount': 12000, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        s = b.mk(tk.PLAYER, b.C, 'wallet', {'kind': 'settle', 'amount': 12000, 'unit': 'USD-cents'}, {'answers': [o['id']]})
        d = b.mk(tk.PLAYER, b.C, 'decide', {'text': 'Count it in unit: USD-cents.'})
        r = wallet.balances(b.fold([o, a, s, d]), holon=b.C)
        self.assertEqual(r['by_unit']['USD-cents']['settled'], 12000)
        self.assertEqual(r['by_actor'][tk.STEWARD]['USD-cents']['net'], 12000)
        self.assertEqual(r['by_actor'][tk.PLAYER]['USD-cents']['net'], -12000)
        self.assertEqual(wallet.entries(b.fold([o]), b.C)[0]['for_card'], tk.IDS['request'])
        self.assertTrue(r['units'][0]['ruled'])
        self.assertFalse(wallet.balances(b.fold([o, a, s]), holon=b.C)['units'][0]['ruled'])

    def test_a_gift_then_an_accept_still_gives(self):
        tk = self.tk
        b = tk.Base(); b.setUp()
        g = b.mk(tk.PLAYER, b.C, 'wallet', {'kind': 'gift', 'amount': 500, 'unit': 'USD-cents', 'to': tk.STEWARD})
        a = b.mk(tk.STEWARD, b.C, 'wallet', {'kind': 'accept', 'amount': 500, 'unit': 'USD-cents'}, {'answers': [g['id']]})
        f = b.fold([g, a])
        self.assertEqual(next(i for i in f['wallet'] if i['id'] == g['id'])['state'], 'accepted')   # the fold's reading
        r = wallet.balances(f, holon=b.C)
        self.assertEqual(r['by_actor'][tk.STEWARD]['USD-cents']['in'], 500)
        self.assertEqual(r['by_actor'][tk.PLAYER]['USD-cents']['out'], 500)

    def test_a_correction_retracts_and_nothing_moves(self):
        tk = self.tk
        b = tk.Base(); b.setUp()
        o = b.mk(tk.PLAYER, b.C, 'wallet', {'kind': 'offer', 'amount': 900, 'unit': 'EUR-cents', 'to': tk.STEWARD})
        s = b.mk(tk.PLAYER, b.C, 'wallet', {'kind': 'settle', 'amount': 900, 'unit': 'EUR-cents'}, {'answers': [o['id']]})
        c = b.mk(tk.PLAYER, b.C, 'correct', {'why': 'entered twice'}, {'supersedes': [o['id']]})
        r = wallet.balances(b.fold([o, s, c]), holon=b.C)
        self.assertNotIn('EUR-cents', json.dumps(r['by_actor']))


if __name__ == '__main__':
    unittest.main()
