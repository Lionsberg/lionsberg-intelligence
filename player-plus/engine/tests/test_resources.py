"""Tests for resources.py: Actors, Pledges, capacity, Level of Commitment, TEA · Fiat · Tokens.

Every number is checkable by pencil. Run from the engine folder:
    python3 -m unittest tests.test_resources
"""
import copy
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import schedule as S  # noqa: E402
import resources as R  # noqa: E402

DD = '2026-11-02'   # a Monday

PERIODS = [{'id': 'P-1', 'name': 'this season', 'from': '2026-09-22', 'to': '2026-12-20'},
           {'id': 'P-2', 'name': 'next season', 'from': '2026-12-21', 'to': '2027-03-19'}]
ACTORS = [{'id': 'person:a', 'kind': 'living', 'class': 'player+', 'holon': 'H1', 'available_min_week': 2400},
          {'id': 'person:b', 'kind': 'living', 'class': 'player', 'holon': 'H2'},
          {'id': 'agent:x', 'kind': 'artificial', 'class': 'actor'}]
FIVE_DAYS = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}


def pledge(pid, actor, level, tea, to='H1', period='P-1', state='committed'):
    return {'id': pid, 'actor': actor, 'period': period, 'to': to, 'level': level,
            'tea_min_week': tea, 'state': state}


def run(items, registers, calendar=None):
    res = S.run(copy.deepcopy(items), calendar, DD)
    return R.resources(res, items, registers, calendar)


class Capacity(unittest.TestCase):

    def test_a_quest_week_never_hides_the_season_baseline(self):
        # review E, M1: a quest Pledge in a week inside the season kept the season's baseline out of capacity
        weeks = PERIODS + [{'id': 'W-45', 'name': 'a week', 'from': '2026-11-02', 'to': '2026-11-08', 'within': 'P-1'}]
        regs = {'actors': ACTORS, 'periods': weeks,
                'pledges': [pledge('PL-1', 'person:a', 'season', 1000), pledge('PL-2', 'person:a', 'quest', 300, to='c', period='W-45')]}
        out = run([{'id': 'c', 'holder': 'person:a', 'minutes': 60}], regs, FIVE_DAYS)
        self.assertEqual(out['capacity']['person:a']['min_per_day'], 200)      # max(1000, 300) over five days
        self.assertEqual(out['level_of_commitment']['person:a']['baseline_min_week'], 1000)

    def test_season_pledge_over_five_working_days(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [pledge('PL-1', 'person:a', 'season', 600)]}
        out = run([{'id': 'c', 'holder': 'person:a', 'minutes': 60}], regs, FIVE_DAYS)
        cap = out['capacity']['person:a']
        self.assertEqual((cap['min_per_day'], cap['source'], cap['pledges'], cap['period']),
                         (120, 'pledges', ['PL-1'], 'P-1'))               # 600 / 5
        self.assertEqual(R.capacity_map(out), {'person:a': 120})

    def test_seven_days_by_default_fraction_kept(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [pledge('PL-1', 'person:a', 'season', 600)]}
        cap = run([], regs)['capacity']['person:a']
        self.assertEqual(cap['min_per_day'], round(600 / 7, 6))           # 85.714286, never rounded up
        self.assertEqual(cap['working_days_per_week'], 7)

    def test_quest_pledges_exceeding_baseline_win(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [
            pledge('PL-1', 'person:a', 'season', 600),
            pledge('PL-2', 'person:a', 'quest', 400, to='Q1'),
            pledge('PL-3', 'person:a', 'quest', 350, to='Q2')]}
        out = run([], regs, FIVE_DAYS)
        self.assertEqual(out['capacity']['person:a']['min_per_day'], 150)  # max(600, 750) / 5
        loc = out['level_of_commitment']['person:a']
        self.assertEqual((loc['baseline_min_week'], loc['quests_min_week'], loc['quests_meet_baseline']),
                         (600, 750, True))

    def test_pledge_in_another_period_ignored(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [
            pledge('PL-1', 'person:a', 'season', 500),
            pledge('PL-9', 'person:a', 'season', 5000, period='P-2')]}
        cap = run([], regs, FIVE_DAYS)['capacity']['person:a']
        self.assertEqual((cap['min_per_day'], cap['pledges']), (100, ['PL-1']))

    def test_released_and_unreadable_pledges_reported_never_counted(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [
            pledge('PL-1', 'person:a', 'season', 500),
            pledge('PL-2', 'person:a', 'season', 500, state='released'),
            pledge('PL-3', 'person:a', 'season', -100),
            {'id': 'PL-4', 'actor': 'person:a', 'period': 'P-1', 'to': 'H1', 'tea_min_week': 50},
            pledge('PL-5', 'person:a', 'season', 50, period='P-404')]}
        out = run([], regs, FIVE_DAYS)
        self.assertEqual(out['capacity']['person:a']['min_per_day'], 100)
        self.assertEqual([u['id'] for u in out['pledges_unread']], ['PL-2', 'PL-3', 'PL-4', 'PL-5'])

    def test_assumed_fallback_said_else_none(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'capacity_assumed': {'person:b': 240}}
        out = run([{'id': 'c', 'holder': 'agent:x', 'minutes': 30}], regs)
        self.assertEqual(out['capacity']['person:b'], {'min_per_day': 240, 'source': 'assumed', 'pledges': [],
                                                       'period': None, 'working_days_per_week': 7})
        self.assertEqual((out['capacity']['agent:x']['min_per_day'], out['capacity']['agent:x']['source']),
                         (None, 'none'))
        self.assertNotIn('agent:x', R.capacity_map(out))

    def test_narrowest_period_holding_the_data_date(self):
        periods = PERIODS + [{'id': 'P-W', 'from': '2026-11-02', 'to': '2026-11-08', 'within': 'P-1'}]
        regs = {'actors': ACTORS, 'periods': periods, 'pledges': [
            pledge('PL-1', 'person:a', 'season', 500), pledge('PL-W', 'person:a', 'season', 250, period='P-W')]}
        cap = run([], regs, FIVE_DAYS)['capacity']['person:a']
        self.assertEqual((cap['min_per_day'], cap['period'], cap['other_periods']), (50, 'P-W', ['P-1']))


class LevelOfCommitment(unittest.TestCase):

    def test_across_two_holons_and_their_quests(self):
        items = [{'id': 'Q1', 'holon': 'H1'}, {'id': 'a', 'holon': 'H1', 'within': 'Q1', 'minutes': 60},
                 {'id': 'Q2', 'holon': 'H2'}, {'id': 'b', 'holon': 'H2', 'within': 'Q2', 'minutes': 60}]
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [
            pledge('PL-1', 'person:a', 'season', 600, to='H1'),
            pledge('PL-2', 'person:a', 'season', 300, to='H2'),
            pledge('PL-3', 'person:a', 'quest', 500, to='Q1'),
            pledge('PL-4', 'person:a', 'quest', 200, to='Q2')]}
        loc = run(items, regs)['level_of_commitment']['person:a']
        self.assertEqual(loc['baseline_min_week'], 900)                   # 600 + 300, both holons
        self.assertEqual(loc['quests_min_week'], 700)
        self.assertIs(loc['quests_meet_baseline'], False)                 # 700 < 900
        self.assertEqual(loc['level'], 0.375)                             # 900 / 2400
        self.assertEqual(loc['holons'], ['H1', 'H2'])
        self.assertEqual(loc['quests'], ['Q1', 'Q2'])

    def test_missing_available_said(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [pledge('PL-1', 'person:b', 'season', 300, to='H2')]}
        loc = run([], regs)['level_of_commitment']['person:b']
        self.assertIsNone(loc['level'])
        self.assertIn('available', loc['basis'])


class Tea(unittest.TestCase):

    def test_artificial_holder_counts_tokens_not_tea(self):
        items = [{'id': 'c', 'holder': 'agent:x', 'minutes': 120, 'tokens_m': 2.5, 'platform': 'some-model'},
                 {'id': 'd', 'holder': 'agent:y', 'minutes': 30}]           # artificial by id prefix
        out = run(items, {'actors': ACTORS})
        c = out['cards']['c']
        self.assertEqual((c['tea'], c['tokens_m'], c['platform']), ({}, 2.5, 'some-model'))
        self.assertIn('artificial', c['tea_basis'])
        self.assertEqual(out['actors']['agent:y']['kind'], 'artificial')
        self.assertEqual(out['totals']['whole']['tea'], {})
        self.assertEqual(out['totals']['whole']['tokens_m'], 2.5)
        self.assertEqual(out['totals']['whole']['artificial_cards_without_tokens'], 1)   # d: honest-empty

    def test_living_holder_default_tea_is_its_minutes(self):
        out = run([{'id': 'c', 'holder': 'person:a', 'minutes': 90}], {'actors': ACTORS})
        self.assertEqual((out['cards']['c']['tea'], out['cards']['c']['tea_basis']), ({'person:a': 90}, 'holder minutes'))

    def test_unknown_kind_reported_no_tea(self):
        out = run([{'id': 'c', 'holder': 'A-0001', 'minutes': 90}], {'actors': ACTORS})
        self.assertEqual(out['unknown_kind'], ['A-0001'])
        self.assertEqual(out['actors']['A-0001']['kind'], 'unknown')
        self.assertEqual(out['cards']['c']['tea'], {})
        self.assertTrue(out['warnings'])

    def test_explicit_tea_wins_artificial_and_negative_dropped_and_reported(self):
        items = [{'id': 'c', 'holder': 'person:a', 'minutes': 100,
                  'tea': {'person:a': 30, 'person:b': -20, 'agent:x': 70},
                  'fiat': {'USD': 250, 'EUR': -5}}]
        out = run(items, {'actors': ACTORS})
        c = out['cards']['c']
        self.assertEqual((c['tea'], c['tea_basis'], c['fiat']), ({'person:a': 30}, 'explicit', {'USD': 250}))
        self.assertEqual([(d['field'], d['key'], d['reason'].split(' ')[0]) for d in out['dropped']],
                         [('fiat', 'EUR', 'negative'), ('tea', 'agent:x', 'artificial'), ('tea', 'person:b', 'negative')])

    def test_no_negative_share_anywhere(self):
        items = [{'id': 'c', 'holder': 'person:a', 'minutes': -50}, {'id': 'd', 'holder': 'person:b', 'minutes': 40,
                                                                      'tea': {'person:b': -40}}]
        out = run(items, {'actors': ACTORS})
        vals = [v for c in out['cards'].values() for v in c['tea'].values()]
        vals += list(out['totals']['whole']['tea'].values())
        self.assertTrue(all(v >= 0 for v in vals))
        self.assertEqual(out['totals']['whole']['tea'], {})


class Units(unittest.TestCase):

    def items(self):
        return [{'id': 'Q'},
                {'id': 'U1', 'within': 'Q'}, {'id': 'U2', 'within': 'U1'},
                {'id': 'a', 'within': 'U1', 'holder': 'person:a', 'minutes': 60, 'state': 'done'},
                {'id': 'b', 'within': 'U2', 'holder': 'person:a', 'minutes': 120,
                 'links': {'predecessor': ['a']}, 'fiat': {'USD': 10}},
                {'id': 'c', 'within': 'U2', 'holder': 'person:b', 'minutes': 30, 'links': {'predecessor': ['b']}},
                {'id': 'd', 'within': 'Q', 'holder': 'agent:x', 'minutes': 45, 'tokens_m': 1.5,
                 'links': {'predecessor': ['U1']}}]

    def test_open_vs_whole_from_nested_units_counted_once(self):
        out = run(self.items(), {'actors': ACTORS})
        q = out['units']['Q']
        self.assertEqual(q['leaves'], ['a', 'b', 'c', 'd'])
        self.assertEqual(q['whole']['tea'], {'person:a': 180, 'person:b': 30})   # 60 + 120, once each
        self.assertEqual(q['open']['tea'], {'person:a': 120, 'person:b': 30})    # a is done
        self.assertEqual((q['whole']['fiat'], q['whole']['tokens_m'], q['whole']['cards'], q['open']['cards']),
                         ({'USD': 10}, 1.5, 4, 3))
        self.assertEqual(out['units']['U2']['whole']['tea'], {'person:a': 120, 'person:b': 30})
        self.assertEqual(out['units']['U1']['whole']['tea'], {'person:a': 180, 'person:b': 30})
        self.assertNotIn('Q', out['cards'])
        self.assertEqual(out['totals']['whole']['tea'], q['whole']['tea'])


class Laws(unittest.TestCase):

    def test_deterministic_and_inputs_untouched(self):
        items = Units().items()
        regs = {'actors': list(reversed(ACTORS)), 'periods': PERIODS,
                'pledges': [pledge('PL-2', 'person:a', 'quest', 100, to='Q'), pledge('PL-1', 'person:a', 'season', 600)]}
        before = json.dumps([items, regs], sort_keys=True)
        res = S.run(copy.deepcopy(items), FIVE_DAYS, DD)
        one = json.dumps(R.resources(res, items, regs, FIVE_DAYS), sort_keys=True)
        two = json.dumps(R.resources(res, list(reversed(items)), regs, FIVE_DAYS), sort_keys=True)
        self.assertEqual(one, two)
        self.assertEqual(json.dumps([items, regs], sort_keys=True), before)

    def test_data_date_is_an_argument(self):
        regs = {'actors': ACTORS, 'periods': PERIODS, 'pledges': [pledge('PL-9', 'person:a', 'season', 700, period='P-2')]}
        res = S.run([], None, DD)
        self.assertEqual(R.resources(res, [], regs)['capacity']['person:a']['source'], 'none')
        later = R.resources(res, [], regs, None, '2027-01-04')
        self.assertEqual((later['capacity']['person:a']['min_per_day'], later['data_date']), (100, '2027-01-04'))

    def test_no_names_dates_or_actor_ids_in_code(self):
        with open(os.path.join(ENGINE, 'resources.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIsNone(re.search(r'\d{4}-\d{2}-\d{2}', src), 'a date in code')
        self.assertIsNone(re.search(r'person:\w|A-\d{4}|PL-\d|W-\d{4}', src), 'an actor or card id in code')
        for word in ('Sir', 'Sophia', 'sir_min', 'Spring', 'Summer', 'Autumn', 'Winter'):
            self.assertNotIn(word, src)
        self.assertNotIn('open(', src.replace('_open', ''))                   # reads no files
        self.assertNotIn('today(', src)                                       # reads no clock


if __name__ == '__main__':
    unittest.main()
