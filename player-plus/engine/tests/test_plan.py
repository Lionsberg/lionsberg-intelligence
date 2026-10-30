"""plan.py: the whole engine in one call; the modules joined as the contract says (CONTRACT-step2.md)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plan as P  # noqa: E402

DD = '2026-11-02'   # a Monday
ME, AI = 'person:player', 'agent:aide'
CAL = {'minutes_per_day': 480, 'markers': [{'id': 'M1', 'date': '2026-11-13'}]}
ITEMS = [
    {'id': 'Q', 'title': 'the quest'},
    {'id': 'a', 'title': 'draft', 'holder': ME, 'minutes': 240, 'minutes_safe': 480, 'links': {'within': ['Q']}},
    {'id': 'b', 'title': 'review', 'holder': ME, 'minutes': 240, 'minutes_safe': 360, 'links': {'within': ['Q']}},
    {'id': 'c', 'title': 'build', 'holder': AI, 'minutes': 960, 'links': {'within': ['Q'], 'predecessor': ['a']}},
    {'id': 'm', 'title': 'the marker', 'kind': 'milestone', 'marker': 'M1', 'links': {'predecessor': ['b', 'c']}},
]
REGS = {'actors': [{'id': ME, 'kind': 'living', 'class': 'player+'}, {'id': AI, 'kind': 'artificial'}],
        'pledges': [{'id': 'PL1', 'actor': ME, 'period': 'S1', 'to': 'cell', 'level': 'season', 'tea_min_week': 1680,
                     'state': 'committed'}],
        'periods': [{'id': 'S1', 'name': 'the season', 'from': '2026-09-22', 'to': '2026-12-20'}],
        'capacity_assumed': {AI: 960},
        'markers': CAL['markers']}


class Plan(unittest.TestCase):
    def setUp(self):
        self.out = P.plan(ITEMS, CAL, DD, REGS)

    def test_every_part_is_there(self):
        self.assertEqual(sorted(self.out), ['chain', 'lps', 'missing', 'registers_used', 'resources', 'sbs', 'schedule'])

    def test_capacity_reaches_the_chain(self):
        # the join that once failed: resources gives {actor: {min_per_day, source}}, the chain levels against it
        cap = self.out['resources']['capacity']
        self.assertEqual((cap[ME]['min_per_day'], cap[ME]['source']), (240, 'pledges'))   # 1680 a week over 7 days
        self.assertEqual(cap[AI]['source'], 'assumed')
        day = self.out['chain']['day']
        self.assertEqual(day[ME]['capacity_min'], 240)
        self.assertNotIn(ME, [u.get('id') if isinstance(u, dict) else u for u in self.out['chain'].get('unleveled') or []])

    def test_one_holder_is_leveled(self):
        lev = self.out['chain']['leveled']
        firsts = sorted([lev['a']['lev_ES'], lev['b']['lev_ES']])
        self.assertEqual(firsts, [0, 1])                     # 240 minutes a day: one of the two waits a day

    def test_two_estimates_size_a_buffer(self):
        bufs = self.out['chain']['buffers']['project']
        self.assertTrue(bufs)
        self.assertGreater(bufs[0].get('buffer_min') or bufs[0].get('size_min') or 0, 0)

    def test_tea_is_the_livings_alone(self):
        cards = self.out['resources']['cards']
        self.assertEqual(cards['c']['tea'], {})
        self.assertEqual(cards['a']['tea'], {ME: 240})

    def test_nothing_missing_said_wrongly(self):
        self.assertEqual(self.out['missing'], [])
        bare = P.plan([{'id': 'x', 'minutes': 60}], {}, DD)
        self.assertEqual(len(bare['missing']), 3)

    def test_an_unsized_card_is_not_in_the_day(self):
        out = P.plan(ITEMS + [{'id': 'u', 'title': 'unsized', 'holder': ME}], CAL, DD, REGS)
        day = out['chain']['day'][ME]
        self.assertIn('u', day['unsized'])
        self.assertNotIn('u', day['should'])

    def test_deterministic(self):
        again = P.plan(ITEMS, CAL, DD, REGS)
        self.assertEqual(json.dumps(again, sort_keys=True, default=str), json.dumps(self.out, sort_keys=True, default=str))

    def test_the_state_carries_one_plan_per_holon(self):
        # review E, M4: the plan runs per holon held, as the schedule does, never once over all on the home calendar
        import engine as E
        hq = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fixtures', 'hq')
        st = E.build_state(hq, now='2026-10-21T12:00:00-07:00')
        self.assertEqual(set(st['plan']), {h['id'] for h in st['holons']})
        self.assertTrue(all(v['engine'] == P.VERSION for v in st['plan'].values()))

    def test_registers_from_the_record(self):
        folded = {'cards': ITEMS, 'commitments': [{'id': 'k', 'card': 'a', 'by': '2026-11-03', 'for': ME, 'state': 'open',
                                                     'misses': [{'id': 'x', 'reason': 'capacity', 'ts': '2026-11-04'}]}],
                  'constraints': [{'id': 'q', 'card': 'c', 'sort': 'information', 'what': 'notes', 'state': 'cleared',
                                   'ts': '2026-11-01T09:00:00-07:00', 'cleared_ts': '2026-11-02T10:00:00-07:00'}],
                  'pledges': [{'id': 'PL1', 'for': ME, 'period': 'S1', 'to': 'cell', 'level': 'season', 'tea_min_week': 1680,
                               'state': 'committed'}],
                  'admitted': {'cell': {ME: {}, AI: {}}}}
        r = P.registers_from(folded, CAL, {'home_place': 'Sol.3'})
        self.assertEqual(r['misses'], [{'commitment': 'k', 'reason': 'capacity', 'note': None, 'ts': '2026-11-04'}])
        self.assertEqual((r['constraints'][0]['state'], r['constraints'][0]['cleared_on']), ('cleared', '2026-11-02'))
        self.assertEqual(r['pledges'][0]['actor'], ME)
        self.assertEqual({a['id']: a['kind'] for a in r['actors']}, {ME: 'living', AI: 'artificial'})
        self.assertEqual(r['home_place'], 'Sol.3')


if __name__ == '__main__':
    unittest.main()
