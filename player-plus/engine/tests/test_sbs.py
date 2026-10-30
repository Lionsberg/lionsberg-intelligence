"""Tests for sbs.py: the SpaceTime Breakdown, every number checkable by pencil.

Run from the engine folder:
    python3 -m unittest tests.test_sbs

THE FIXTURE (data date 2026-11-02, a Monday; calendar days; 480 minutes a day)
  U, a unit at 'valley', holds A (480 min, at 'site') and B (240 min, after A).
  C, 960 min, alone. M, a milestone after B. D, done, actual finish 2026-10-28.
  Forward: A 0-1 (last day 11-02) · B 1-1.5 (11-03) · C 0-2 (11-03) · M 1.5 (11-03).
  Late end 2: M TF 0.5 · B TF 0.5 · A TF 0.5 · C TF 0 (critical).
  Places: earth > valley > site; home earth.
  Periods: Y (2026-10-01..2026-12-31) > W44 (10-26..11-01), W45 (11-02..11-08).
  So A: site (own), W45 · B: valley (unit U), W45 · C: earth (home), W45 · M: earth (home), W45 ·
     D: earth (home), W44 by its actual finish.
  Matrix: earth/W45 = C, M: 2 open, 960 min, least float 0, 1 critical ·
          site/W45 = A: 1, 480, 0.5, 0 · valley/W45 = B: 1, 240, 0.5, 0.
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
import sbs as B  # noqa: E402

DD = '2026-11-02'


def items():
    return [
        {'id': 'U', 'title': 'the unit', 'where': 'valley'},
        {'id': 'A', 'title': 'frame', 'minutes': 480, 'where': 'site', 'links': {'within': 'U'}},
        {'id': 'B', 'title': 'wire', 'minutes': 240, 'links': {'within': 'U', 'predecessor': ['A']}},
        {'id': 'C', 'title': 'read', 'minutes': 960},
        {'id': 'M', 'title': 'ready', 'kind': 'milestone', 'links': {'predecessor': ['B']}},
        {'id': 'D', 'title': 'begun', 'minutes': 60, 'state': 'done', 'actual_finish': '2026-10-28'},
    ]


def registers(**over):
    r = {'places': [{'id': 'earth', 'name': 'Earth', 'within': None},
                    {'id': 'valley', 'name': 'the valley', 'within': 'earth'},
                    {'id': 'site', 'name': 'the site', 'within': 'valley'}],
         'home_place': 'earth',
         'periods': [{'id': 'Y', 'name': 'the year', 'from': '2026-10-01', 'to': '2026-12-31', 'within': None},
                     {'id': 'W44', 'name': 'week 44', 'from': '2026-10-26', 'to': '2026-11-01', 'within': 'Y'},
                     {'id': 'W45', 'name': 'week 45', 'from': '2026-11-02', 'to': '2026-11-08', 'within': 'Y'}]}
    r.update(over)
    return r


def run(its=None, reg=None):
    its = items() if its is None else its
    res = S.run(its, data_date=DD)
    return B.sbs(res, its, registers() if reg is None else reg)


class Placement(unittest.TestCase):
    def test_where_precedence_own_unit_home(self):
        p = run()['placement']
        self.assertEqual((p['A']['where'], p['A']['where_basis']), ('site', 'own'))
        self.assertEqual((p['B']['where'], p['B']['where_basis'], p['B']['where_from']), ('valley', 'unit', 'U'))
        self.assertEqual((p['C']['where'], p['C']['where_basis']), ('earth', 'home'))

    def test_nearest_unit_wins(self):
        its = items() + [{'id': 'U2', 'title': 'inner', 'links': {'within': 'U'}},
                         {'id': 'E', 'minutes': 60, 'links': {'within': 'U2'}}]
        p = run(its)['placement']
        self.assertEqual((p['E']['where'], p['E']['where_from']), ('valley', 'U'))   # U2 has none; U does
        its[-2]['where'] = 'site'
        p = run(its)['placement']
        self.assertEqual((p['E']['where'], p['E']['where_from']), ('site', 'U2'))

    def test_unplaced_without_home(self):
        reg = registers()
        del reg['home_place']
        out = run(reg=reg)
        self.assertEqual((out['placement']['C']['where'], out['placement']['C']['where_basis']), (None, 'unplaced'))
        self.assertTrue(out['basis']['home_place'].startswith('missing'))

    def test_when_is_the_smallest_holding_period(self):
        p = run()['placement']
        self.assertEqual((p['A']['when'], p['A']['when_date'], p['A']['week']), ('W45', '2026-11-02', '2026-11-02'))
        self.assertEqual(p['C']['when_date'], '2026-11-03')   # the last day of work, not the morning after
        self.assertEqual(p['U']['when'], 'W45')

    def test_done_uses_actual_finish(self):
        p = run()['placement']['D']
        self.assertEqual((p['when'], p['when_date'], p['when_basis'], p['week']),
                         ('W44', '2026-10-28', 'actual finish', '2026-10-26'))

    def test_done_without_actual_finish_is_said(self):
        its = items()
        its[-1] = {'id': 'D', 'minutes': 60, 'state': 'done'}
        p = run(its)['placement']['D']
        self.assertEqual((p['when'], p['when_basis']), (None, 'missing: done with no actual finish'))

    def test_no_period_holds_the_date(self):
        reg = registers(periods=[{'id': 'W44', 'name': 'w', 'from': '2026-10-26', 'to': '2026-11-01', 'within': None}])
        p = run(reg=reg)['placement']['A']
        self.assertIsNone(p['when'])
        self.assertEqual(p['when_basis'], 'no period holds 2026-11-02')

    def test_unheld_place_is_listed_not_fixed(self):
        its = items()
        its[3]['where'] = 'moon'
        out = run(its)
        self.assertEqual(out['placement']['C']['where'], 'moon')
        self.assertEqual(out['space']['unheld_places'], [{'card': 'C', 'where': 'moon'}])


class Holarchies(unittest.TestCase):
    def test_registers_check_clean(self):
        out = run()
        self.assertTrue(out['space']['ok'])
        self.assertTrue(out['time']['ok'])
        self.assertEqual(out['space']['roots'], ['earth'])
        depth = {n['id']: n['depth'] for n in out['space']['nodes']}
        self.assertEqual(depth, {'earth': 1, 'valley': 2, 'site': 3})

    def test_loop_and_unheld_within_reported(self):
        places = [{'id': 'a', 'within': 'b'}, {'id': 'b', 'within': 'a'}, {'id': 'c', 'within': 'zz'}]
        sp, _ = B.check_holarchy(places, 'place')
        kinds = {(d['id'], d['defect']) for d in sp['defects']}
        self.assertIn(('a', 'loop'), kinds)
        self.assertIn(('c', 'within not held'), kinds)
        self.assertIn((None, 'no root'), kinds)
        self.assertFalse(sp['ok'])
        loop = next(d for d in sp['defects'] if d['defect'] == 'loop')
        self.assertEqual(loop['loop'], ['a', 'b'])
        self.assertEqual({n['id']: n['within'] for n in sp['nodes']}, {'a': 'b', 'b': 'a', 'c': 'zz'})  # never fixed

    def test_two_roots_and_bad_spans(self):
        periods = [{'id': 'P', 'from': '2026-01-01', 'to': '2026-01-31'},
                   {'id': 'Q', 'from': '2026-03-01', 'to': '2026-02-01'},
                   {'id': 'R', 'from': '2026-02-01', 'to': '2026-02-10', 'within': 'P'},
                   {'id': 'S', 'from': 'soon', 'to': '2026-02-10', 'within': 'P'}]
        tm, _ = B.check_holarchy(periods, 'period', dated=True)
        kinds = {(d['id'], d['defect']) for d in tm['defects']}
        self.assertEqual(kinds, {(None, 'more than one root'), ('Q', 'from after to'),
                                 ('R', 'outside the span of its within'), ('S', 'from or to is not an ISO date')})

    def test_periods_loop_reported_in_result(self):
        reg = registers(periods=[{'id': 'X', 'from': '2026-11-01', 'to': '2026-11-30', 'within': 'Z'},
                                 {'id': 'Z', 'from': '2026-11-01', 'to': '2026-11-30', 'within': 'X'}])
        tm = run(reg=reg)['time']
        self.assertFalse(tm['ok'])
        self.assertIn('loop', [d['defect'] for d in tm['defects']])


class DefaultPeriods(unittest.TestCase):
    def test_iso_years_and_weeks_from_the_data(self):
        reg = registers()
        del reg['periods']
        out = run(reg=reg)
        ids = [n['id'] for n in out['time']['nodes']]
        self.assertEqual(sorted(ids), ['2026', '2026-W44', '2026-W45'])
        self.assertTrue(out['time']['ok'])
        self.assertTrue(out['time']['basis'].startswith('default'))
        self.assertEqual(out['placement']['A']['when'], '2026-W45')
        self.assertEqual(out['placement']['D']['when'], '2026-W44')

    def test_two_iso_years_get_one_root(self):
        import datetime as dt
        ps = B.default_periods([dt.date(2026, 12, 30), dt.date(2027, 1, 5)])
        tm, _ = B.check_holarchy(ps, 'period', dated=True)
        self.assertTrue(tm['ok'], tm['defects'])
        self.assertEqual(tm['roots'], ['2026/2027'])
        self.assertIn('2026-W53', [p['id'] for p in ps])   # 2026 has 53 ISO weeks


class Matrix(unittest.TestCase):
    def test_numbers(self):
        m = {(c['where'], c['when']): c for c in run()['matrix']}
        self.assertEqual(sorted(m), [('earth', 'W45'), ('site', 'W45'), ('valley', 'W45')])
        e = m[('earth', 'W45')]
        self.assertEqual((e['cards'], e['open'], e['minutes'], e['least_float'], e['critical']), (['C', 'M'], 2, 960, 0, 1))
        s = m[('site', 'W45')]
        self.assertEqual((s['open'], s['minutes'], s['least_float'], s['critical']), (1, 480, 0.5, 0))
        v = m[('valley', 'W45')]
        self.assertEqual((v['open'], v['minutes'], v['least_float'], v['critical']), (1, 240, 0.5, 0))

    def test_done_and_units_not_counted(self):
        cards = [c for cell in run()['matrix'] for c in cell['cards']]
        self.assertNotIn('D', cards)
        self.assertNotIn('U', cards)


class Laws(unittest.TestCase):
    def test_deterministic(self):
        a = json.dumps(run(), sort_keys=True)
        b = json.dumps(run(), sort_keys=True)
        self.assertEqual(a, b)
        its = items()
        res = S.run(its, data_date=DD)
        c = json.dumps(B.sbs(res, list(reversed(its)), registers()), sort_keys=True)
        self.assertEqual(a, c)

    def test_inputs_never_written(self):
        its, reg = items(), registers()
        res = S.run(its, data_date=DD)
        before = copy.deepcopy((res, its, reg))
        B.sbs(res, its, reg)
        self.assertEqual((res, its, reg), before)

    def test_honest_empty(self):
        out = B.sbs({}, [], None)
        self.assertEqual(out['placement'], {})
        self.assertEqual(out['matrix'], [])
        self.assertTrue(out['space']['basis'].startswith('missing'))
        self.assertEqual(out['data_date'], None)

    def test_data_date_argument_overrides(self):
        reg = registers()
        del reg['periods']
        its = items()
        res = S.run(its, data_date=DD)
        out = B.sbs(res, its, reg, data_date='2026-12-01')
        self.assertEqual(out['data_date'], '2026-12-01')
        self.assertIn('2026-W49', [n['id'] for n in out['time']['nodes']])

    def test_no_dates_names_or_clock_in_code(self):
        with open(os.path.join(ENGINE, 'sbs.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIsNone(re.search(r'\d{4}-\d{2}-\d{2}', src))
        for word in ('person:', 'agent:', 'today(', 'now(', 'open(', 'solstice', 'equinox'):
            self.assertNotIn(word, src)


if __name__ == '__main__':
    unittest.main()
