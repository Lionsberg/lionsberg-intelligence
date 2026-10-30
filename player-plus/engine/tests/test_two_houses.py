"""Two houses calculating together (the plan's step 7, run locally): only a live commitment crosses with a date."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E    # noqa: E402
import schedule as S  # noqa: E402

DD = '2026-11-02'
A, B = 'house-a', 'house-b'


def folded(state='open'):
    return {'cards': [{'id': 'a1', 'holon': A, 'title': 'the cohort walks through', 'minutes': 480,
                       'links': {'predecessor': ['b1']}},
                      {'id': 'b1', 'holon': B, 'title': 'the onboarding walk, written', 'minutes': 960, 'by': '2026-11-20'}],
            'commitments': [{'id': 'k1', 'holon': B, 'card': 'b1', 'by': '2026-11-06', 'for': 'person:b',
                             'committee': 'person:a', 'state': state}]}


class TwoHouses(unittest.TestCase):
    def run_a(self, f):
        items, ext = E.holon_graph(f, [], A, {A, B})
        return {r['id']: r for r in S.run(items, None, DD, external=ext or None)['items']}, ext

    def test_a_live_commitment_dates_the_waiting_work(self):
        r, ext = self.run_a(folded())
        self.assertEqual([e['body']['by'] for e in ext], ['2026-11-06'])   # the commitment's date, never the card's own
        self.assertEqual(r['a1']['start'], '2026-11-06')

    def test_a_released_commitment_dates_nothing(self):
        for st in ('released', 'declined', 'retracted'):
            r, ext = self.run_a(folded(st))
            self.assertEqual(ext, [])                                       # the card stays in its own house
            self.assertEqual(r['a1']['start'], DD)

    def test_a_card_never_crosses_with_its_own_date(self):
        f = folded('released')
        f['cards'][1]['holon'] = 'house-c'                                  # a house not held: its card crosses, dateless
        items, ext = E.holon_graph(f, [], A, {A, B})
        self.assertEqual([e['body'].get('by') for e in ext], [None])

    def test_no_date_crosses_in_the_line_body(self):
        # review E, H3: a card from a house not held carried `date`/`finish`/`at`/`ef` in its line body across
        f = folded('released')
        f['cards'][1]['holon'] = 'house-c'
        lines = [{'id': 'b1', 'holon': 'house-c', 'body': {'title': 'x', 'date': '2026-11-20', 'finish': '2026-11-20',
                                                            'at': '2026-11-20', 'ef': '2026-11-20'}, 'finish': '2026-11-20'}]
        items, ext = E.holon_graph(f, lines, A, {A, B})
        r = {x['id']: x for x in S.run(items, None, DD, external=ext or None)['items']}
        self.assertEqual(r['a1']['start'], DD)
        self.assertIsNone(S._ext_date(ext[0]))

    def test_the_earliest_live_commitment_dates_the_work(self):
        f = folded()
        f['commitments'].insert(0, dict(f['commitments'][0], id='k0', by='2026-11-12'))
        r, ext = self.run_a(f)
        self.assertEqual(r['a1']['start'], '2026-11-06')

    def test_the_committors_house_sees_the_buffer(self):
        items, _ = E.holon_graph(dict(folded(), cards=[dict(folded()['cards'][1], committed_by=[
            {'commitment': 'k1', 'due_by': '2026-11-06', 'for': 'person:b', 'committee': 'person:a', 'state': 'open',
             'buffer': 480}])]), [], B, {A, B})
        res = S.run(items, None, DD, me='person:b')
        row = res['commitments'][0]
        self.assertEqual((row['direction'], row['computed_finish'], row['buffer_days'], row['signal']),
                         ('given', '2026-11-03', 3, 'safe'))       # the last day of work, 11-03; due 11-06


if __name__ == '__main__':
    unittest.main()
