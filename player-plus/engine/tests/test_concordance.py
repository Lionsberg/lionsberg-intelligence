"""test_concordance.py — how a term of one vocabulary reads in another.

Most tests read hand-built items (the shape record.py's fold gives); one class folds signed lines
with the same fixtures test_kinds.py builds, so the reading is checked against the real fold.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_concordance.py -v
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

import concordance as cc  # noqa: E402

H, H2 = 'h' * 64, 'g' * 64
LB, LP, PM = 'lionsberg', 'last-planner', 'project-management'


def conc(i, term, in_, other, in_other, relation='same', state='agreed', holon=H, ts=None, **kw):
    c = {'id': i, 'kind': 'concordance', 'term': term, 'in': in_, 'term_other': other, 'in_other': in_other,
         'relation': relation, 'state': state, 'holon': holon, 'actor': 'person:player', 'for': 'person:player',
         'ts': ts or '2026-10-21T10:00:00-07:00'}
    c.update(kw)
    return c


class TestRows(unittest.TestCase):
    def test_rows_sorted_with_their_fields(self):
        items = {'concordances': [conc('b', 'commitment', LB, 'promise', LP, ts='2026-10-21T10:02:00-07:00', definition='d'),
                                  conc('a', 'card', LB, 'activity', PM, ts='2026-10-21T10:01:00-07:00')]}
        rows = cc.concordances(items)
        self.assertEqual([r['id'] for r in rows], ['a', 'b'])
        self.assertEqual(rows[1]['definition'], 'd')
        self.assertEqual(cc.concordances(items, holon=H2), [])

    def test_null_guards(self):
        for bad in (None, {}, [], 2.5, 'x', {'concordances': None}, {'concordances': [None, 3]}):
            self.assertEqual(cc.concordances(bad), [])
            self.assertEqual(cc.lexicons(bad), [])
            self.assertEqual(cc.bridges(bad, LB, LP), {})
            self.assertEqual(cc.read_as(bad, 'commitment', LB, LP)['basis'], 'none')
        self.assertEqual(cc.bridges({'concordances': [conc('a', 'x', LB, 'y', LP)]}, None, LP), {})
        self.assertEqual(cc.read_as({}, None, None, None)['basis'], 'none')
        self.assertIn('No concordances yet.', cc.render(None))

    def test_a_malformed_row_is_said_and_never_read(self):
        items = {'concordances': [conc('a', '', LB, 'y', LP), conc('b', 'x', LB, 'y', LP, relation='kin')]}
        rows = cc.concordances(items)
        self.assertTrue(all(r.get('problem') for r in rows))
        self.assertEqual(cc.bridges(items, LB, LP, agreed_only=False), {})

    def test_lexicons(self):
        items = {'concordances': [conc('a', 'x', LB, 'y', LP), conc('b', 'x', PM, 'y', LB, state='proposed'),
                                  conc('c', 'x', 'gone', 'y', LB, state='retracted')]}
        self.assertEqual(cc.lexicons(items), sorted([LB, LP, PM]))


class TestBridges(unittest.TestCase):
    def test_both_directions(self):
        items = {'concordances': [conc('f', 'commitment', LB, 'promise', LP),
                                  conc('r', 'reliable promise', LP, 'commitment', LB, relation='clearer')]}
        b = cc.bridges(items, LB, LP)
        self.assertEqual([(x['term_other'], x['relation'], x['direction']) for x in b['commitment']],
                         [('promise', 'same', 'forward'), ('reliable promise', 'clearer', 'reverse')])
        back = cc.bridges(items, LP, LB)
        self.assertEqual(sorted(back), ['promise', 'reliable promise'])
        self.assertEqual(back['promise'][0]['direction'], 'reverse')
        self.assertEqual(back['reliable promise'][0]['direction'], 'forward')

    def test_agreed_only_by_default(self):
        items = {'concordances': [conc('p', 'commitment', LB, 'promise', LP, state='proposed')]}
        self.assertEqual(cc.bridges(items, LB, LP), {})
        self.assertEqual(cc.bridges(items, LB, LP, agreed_only=False)['commitment'][0]['state'], 'proposed')

    def test_agreed_sorts_before_proposed(self):
        items = {'concordances': [conc('z', 'commitment', LB, 'aa', LP, state='proposed'),
                                  conc('y', 'commitment', LB, 'zz', LP)]}
        b = cc.bridges(items, LB, LP, agreed_only=False)['commitment']
        self.assertEqual([x['state'] for x in b], ['agreed', 'proposed'])

    def test_retracted_is_never_read(self):
        items = {'concordances': [conc('x', 'commitment', LB, 'promise', LP, state='retracted')]}
        self.assertEqual(cc.bridges(items, LB, LP, agreed_only=False), {})

    def test_deterministic_and_nfc(self):
        cs = [conc('c%d' % i, 'café', LB, 'term%d' % (i % 3), LP, state=('agreed', 'proposed')[i % 2]) for i in range(8)]
        a = json.dumps(cc.bridges({'concordances': cs}, LB, LP, False), sort_keys=True)
        b = json.dumps(cc.bridges({'concordances': list(reversed(cs))}, LB, LP, False), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(cc.read_as({'concordances': cs}, 'café', LB, LP)['basis'], 'agreed')


class TestReadAs(unittest.TestCase):
    def test_agreed_first_proposed_apart(self):
        items = {'concordances': [conc('a', 'commitment', LB, 'promise', LP),
                                  conc('b', 'commitment', LB, 'pledge', LP, relation='different', state='proposed')]}
        r = cc.read_as(items, 'commitment', LB, LP)
        self.assertEqual(r['basis'], 'agreed')
        self.assertEqual([x['term_other'] for x in r['same']], ['promise'])
        self.assertEqual(r['different'], [])
        self.assertEqual([x['term_other'] for x in r['proposed']['different']], ['pledge'])

    def test_proposed_only(self):
        items = {'concordances': [conc('b', 'commitment', LB, 'pledge', LP, state='proposed')]}
        r = cc.read_as(items, 'commitment', LB, LP)
        self.assertEqual((r['basis'], r['same'], r['different'], r['clearer']), ('proposed', [], [], []))

    def test_none_is_honest_empty(self):
        r = cc.read_as({'concordances': [conc('a', 'commitment', LB, 'promise', LP)]}, 'card', LB, LP)
        self.assertEqual((r['basis'], r['same'], r['different'], r['clearer']), ('none', [], [], []))
        self.assertTrue(r['note'])


def answer(i, prop, relation=None, mirrored=True, **body):
    """The other side's concord line answering `prop`, as the raw line the fold applied."""
    b = {'term': prop['term_other'], 'in': prop['in_other'], 'term_other': prop['term'], 'in_other': prop['in']} if mirrored \
        else {k: prop[k] for k in ('term', 'in', 'term_other', 'in_other')}
    b['relation'] = relation or prop['relation']
    b.update(body)
    return {'id': i, 'type': 'concord', 'actor': 'person:steward', 'for': 'person:steward', 'holon': prop['holon'],
            'body': b, 'links': {'answers': [prop['id']]}}


class TestRepairs(unittest.TestCase):
    """The independent review's findings, each pinned."""

    def agreed(self, i='p1'):
        return conc(i, 'commitment', LB, 'pledge', LP, events=[i, 'y1'], agreed_by='person:steward')

    def test_an_answer_with_another_relation_is_disputed(self):
        c = self.agreed()
        lines = [answer('y1', c, relation='different')]
        r = cc.read_as({'concordances': [c]}, 'commitment', LB, LP, lines=lines)
        self.assertEqual((r['basis'], r['same'], r['different']), ('disputed', [], []))
        self.assertEqual([x['id'] for x in r['disputed']], ['p1'])
        self.assertIn('different', r['disputed'][0]['dispute'])
        self.assertEqual(cc.bridges({'concordances': [c]}, LB, LP, lines=lines), {})

    def test_an_answer_with_other_terms_is_disputed(self):
        c = self.agreed()
        lines = [answer('y1', c, term='promise')]
        self.assertEqual(cc.read_as({'concordances': [c]}, 'commitment', LB, LP, lines=lines)['basis'], 'disputed')

    def test_a_matching_answer_stays_agreed_and_is_checked(self):
        c = self.agreed()
        for ans in (answer('y1', c), answer('y1', c, mirrored=False)):
            r = cc.read_as({'concordances': [c]}, 'commitment', LB, LP, lines=[ans])
            self.assertEqual((r['basis'], r['answers_checked']), ('agreed', True))
            self.assertTrue(cc.concordances({'concordances': [c]}, lines=[ans])[0]['answer_checked'])
        r = cc.read_as({'concordances': [c]}, 'commitment', LB, LP)
        self.assertEqual((r['basis'], r['answers_checked']), ('agreed', False))
        self.assertIn('not checked', r['note'])
        r = cc.read_as({'concordances': [c]}, 'commitment', LB, LP, lines=[])     # lines given, the answer not among them
        self.assertEqual((r['basis'], r['answers_checked']), ('agreed', False))

    def test_agreed_sorts_before_proposed_against_id_and_time(self):
        items = {'concordances': [conc('a', 'commitment', LB, 'aa', LP, state='proposed', ts='2026-10-21T09:00:00-07:00'),
                                  conc('z', 'commitment', LB, 'zz', LP, ts='2026-10-21T11:00:00-07:00')]}
        self.assertEqual([r['id'] for r in cc.concordances(items)], ['a', 'z'])   # the rows run the other way
        b = cc.bridges(items, LB, LP, agreed_only=False)['commitment']
        self.assertEqual([x['id'] for x in b], ['z', 'a'])

    def test_times_are_instants_not_text(self):
        items = {'concordances': [conc('a1', 'x', LB, 'y', LP, ts='2026-10-21T09:00:00-07:00'),
                                  conc('b2', 'x', LB, 'z', LP, ts='2026-10-21T12:00:00+00:00')]}
        self.assertEqual([r['id'] for r in cc.concordances(items)], ['b2', 'a1'])

    def test_render_escapes_cells_and_never_raises(self):
        md = cc.render(cc.concordances({'concordances': [conc('a', 'a|b', LB, 'line\nbreak', LP)]}))
        self.assertIn('| a\\|b | lionsberg | same | line break | last-planner | agreed |', md)
        for bad in (None, 3, 'x', {'a': 1}, [None, 2, {}]):
            self.assertIsInstance(cc.render(bad), str)


class TestLine(unittest.TestCase):
    NOW = '2026-10-31T09:00:00-07:00'

    def test_a_person_writes_a_concord_line(self):
        line = cc.concord_line('commitment', LB, 'promise', LP, 'same', 'what one says one will do',
                               'the kit lexicon', 'person:player', H, self.NOW)
        self.assertEqual((line['type'], line['actor'], line['for'], line['holon'], line['reason'], line['sig']),
                         ('concord', 'person:player', 'person:player', H, 'human', ''))
        self.assertEqual(line['body']['relation'], 'same')
        self.assertEqual(line['ts'], self.NOW)

    def test_an_agent_names_its_person_and_an_answer_links(self):
        line = cc.concord_line('promise', LP, 'commitment', LB, 'same', None, None, 'agent:aide', H, self.NOW,
                               for_='person:player', answers='a' * 64)
        self.assertEqual((line['for'], line['reason'], line['links']['answers']), ('person:player', 'delegated', ['a' * 64]))
        with self.assertRaises(ValueError):
            cc.concord_line('promise', LP, 'commitment', LB, 'same', None, None, 'agent:aide', H, self.NOW)

    def test_refusals(self):
        for args in (('x', LB, 'y', LP, 'kin'), ('', LB, 'y', LP, 'same'), ('x', None, 'y', LP, 'same')):
            with self.assertRaises(ValueError):
                cc.concord_line(*args, None, None, 'person:player', H, self.NOW)
        with self.assertRaises(ValueError):
            cc.concord_line('x', LB, 'y', LP, 'same', None, None, 'someone', H, self.NOW)
        with self.assertRaises(ValueError):
            cc.concord_line('x', LB, 'y', LP, 'same', None, None, 'person:player', '', self.NOW)


class TestRenderAndCli(unittest.TestCase):
    def test_render(self):
        md = cc.render(cc.concordances({'concordances': [conc('a', 'commitment', LB, 'promise', LP)]}))
        self.assertIn('| commitment | lionsberg | same | promise | last-planner | agreed |', md)

    def test_cli(self):
        import contextlib, io
        tmp = tempfile.mkdtemp(prefix='concordance-test-')
        try:
            p = os.path.join(tmp, 'items.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump({'concordances': [conc('a', 'commitment', LB, 'promise', LP)]}, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cc._main([p, '--read', 'promise', LP, LB, '--json']), 0)
            self.assertEqual(json.loads(out.getvalue())['same'][0]['term_other'], 'commitment')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cc._main([p, '--between', LB, LP]), 0)
            self.assertIn('commitment → promise (same, forward)', out.getvalue())
            ln = os.path.join(tmp, 'link.json')
            os.symlink(p, ln)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cc._main([ln]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(shutil.which('ssh-keygen'), 'ssh-keygen is needed: the fixtures are signed')
class TestAgainstTheFold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests import test_kinds as tk
        cls.tk = tk
        tk.setUpModule()

    @classmethod
    def tearDownClass(cls):
        cls.tk.tearDownModule()

    def test_proposed_then_agreed_reads_both_ways(self):
        tk = self.tk
        b = tk.Base(); b.setUp()
        c = b.mk(tk.PLAYER, b.C, 'concord', {'term': 'commitment', 'in': LB, 'term_other': 'promise', 'in_other': LP,
                                             'relation': 'same'})
        r = cc.read_as(b.fold([c]), 'commitment', LB, LP)
        self.assertEqual(r['basis'], 'proposed')
        y = b.mk(tk.STEWARD, b.C, 'concord', {'term': 'commitment', 'in': LB, 'term_other': 'promise', 'in_other': LP,
                                              'relation': 'same'}, {'answers': [c['id']]})   # restated as written
        f = b.fold([c, y])
        self.assertEqual(cc.read_as(f, 'commitment', LB, LP)['basis'], 'agreed')
        back = cc.read_as(f, 'promise', LP, LB)
        self.assertEqual((back['basis'], back['same'][0]['direction'], back['same'][0]['id']), ('agreed', 'reverse', c['id']))
        self.assertTrue({LB, LP} <= set(cc.lexicons(f)))   # the fixtures hold a concordance of their own

    def test_an_answer_that_disagrees_is_disputed_given_the_lines(self):
        tk = self.tk
        b = tk.Base(); b.setUp()
        k = b.mk(tk.PLAYER, b.C, 'concord', {'term': 'commitment', 'in': 'A', 'term_other': 'pledge', 'in_other': 'B',
                                             'relation': 'same'})
        y = b.mk(tk.STEWARD, b.C, 'concord', {'term': 'pledge', 'in': 'B', 'term_other': 'commitment', 'in_other': 'A',
                                              'relation': 'different'}, {'answers': [k['id']]})
        f = b.fold([k, y])
        self.assertEqual(next(i for i in f['concordances'] if i['id'] == k['id'])['state'], 'proposed')   # the fold refuses an answer that does not restate
        r = cc.read_as(f, 'commitment', 'A', 'B', lines=b.r['lines'] + [k, y])
        self.assertEqual((r['basis'], [x['id'] for x in r['disputed']]), ('disputed', [k['id']]))


if __name__ == '__main__':
    unittest.main()
