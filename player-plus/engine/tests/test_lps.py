"""Tests for lps.py: the Last Planner measures, every number checkable by pencil.

Run from the engine folder:
    python3 -m unittest tests.test_lps
The fixture's data date is a Wednesday; its week runs Monday 11-02 to Sunday 11-08, and the week
before from Monday 10-26. The schedule is on the default calendar (every day works), so a day
index is a calendar day.
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

import lps as L  # noqa: E402
import schedule as S  # noqa: E402

DD = '2026-11-04'   # a Wednesday


def cards():
    """A 3 -> B 2 -> D 4 -> F 1 (the critical path, ES 0, 3, 5, 9); C 1 alone (TF 9);
    X 1, a constraint card before D (TF 4)."""
    return [{'id': 'A', 'dur_days': 3, 'holder': 'person:a'},
            {'id': 'B', 'dur_days': 2, 'holder': 'person:a', 'links': {'predecessor': ['A']}},
            {'id': 'C', 'dur_days': 1, 'holder': 'person:b'},
            {'id': 'X', 'kind': 'constraint', 'title': 'permit in hand', 'holder': 'person:b', 'dur_days': 1},
            {'id': 'D', 'dur_days': 4, 'holder': 'person:a', 'links': {'predecessor': ['B', 'X']}},
            {'id': 'F', 'dur_days': 1, 'holder': 'person:a', 'links': {'predecessor': ['D']},
             'conditions': 'the room is booked'}]


def commitments():
    """The module docstring's paper example, plus one released."""
    return [{'id': 'c1', 'card': 'A', 'by': '2026-10-27', 'for': 'person:a', 'state': 'claimed',
             'kept_ts': '2026-10-26T15:00:00Z'},
            {'id': 'c2', 'card': 'C', 'by': '2026-10-29', 'for': 'person:a', 'state': 'claimed',
             'kept_ts': '2026-10-30T09:00:00Z'},
            {'id': 'c3', 'card': 'A', 'by': '2026-11-02', 'for': 'person:b', 'state': 'open'},
            {'id': 'c4', 'card': 'C', 'by': '2026-11-06', 'for': 'person:b', 'state': 'open'},
            {'id': 'c5', 'card': 'B', 'by': '2026-10-28', 'for': 'person:b', 'state': 'released'}]


def run(regs=None, chain=None, items=None, **kw):
    items = items if items is not None else cards()
    res = S.run(items, data_date=DD)
    regs = regs if regs is not None else {'commitments': commitments()}
    return L.lps(res, items, regs, chain=chain, **kw)


class PPC(unittest.TestCase):
    def test_all_time_and_by_week_by_pencil(self):
        p = run()['ppc']
        self.assertEqual(p['all_time'], {'due': 3, 'complete': 1, 'ppc': 0.333})   # c1 of c1, c2, c3
        self.assertEqual(p['by_week'], [{'week': '2026-10-26', 'due': 2, 'complete': 1, 'ppc': 0.5},
                                         {'week': '2026-11-02', 'due': 1, 'complete': 0, 'ppc': 0.0}])
        self.assertEqual(p['by_committor'], [{'committor': 'person:a', 'due': 2, 'complete': 1, 'ppc': 0.5},
                                             {'committor': 'person:b', 'due': 1, 'complete': 0, 'ppc': 0.0}])

    def test_released_declined_retracted_do_not_count(self):
        cs = commitments() + [{'id': 'c6', 'card': 'A', 'by': '2026-10-28', 'for': 'person:a', 'state': 'declined'},
                              {'id': 'c7', 'card': 'A', 'by': '2026-10-28', 'for': 'person:a', 'state': 'retracted'}]
        out = run({'commitments': cs})
        self.assertEqual(out['ppc']['all_time']['due'], 3)
        self.assertNotIn('c5', [m['id'] for m in out['misses']])

    def test_a_delivery_after_by_is_a_miss(self):
        m = {x['id']: x for x in run()['misses']}
        self.assertEqual(m['c2']['delivered_on'], '2026-10-30')     # by 10-29, delivered 10-30
        self.assertIsNone(m['c3']['delivered_on'])
        self.assertNotIn('c1', m)

    def test_kept_with_no_date_is_complete(self):
        cs = [{'id': 'k', 'card': 'A', 'by': '2026-10-28', 'for': 'person:a', 'state': 'kept'}]
        self.assertEqual(run({'commitments': cs})['ppc']['all_time']['complete'], 1)


class Misses(unittest.TestCase):
    def test_reason_applied_latest_wins_and_unknown_is_other(self):
        regs = {'commitments': commitments(),
                'misses': [{'commitment': 'c2', 'reason': 'estimate', 'ts': '2026-10-30T10:00:00Z'},
                           {'commitment': 'c2', 'reason': 'capacity', 'ts': '2026-10-31T10:00:00Z', 'note': 'two at once'},
                           {'commitment': 'c3', 'reason': 'weather', 'ts': '2026-11-03T10:00:00Z'}]}
        out = run(regs)
        m = {x['id']: x for x in out['misses']}
        self.assertEqual((m['c2']['reason'], m['c2']['note']), ('capacity', 'two at once'))
        self.assertEqual(m['c3']['reason'], 'other')
        self.assertIn('weather', m['c3']['note'])
        self.assertEqual(out['reasons']['capacity'], 1)
        self.assertEqual(out['reasons']['other'], 1)
        self.assertEqual(out['reasons']['not yet given'], 0)
        self.assertEqual(sum(out['reasons'].values()), 2)

    def test_not_yet_given_counted(self):
        regs = {'commitments': commitments(), 'misses': [{'commitment': 'c2', 'reason': 'external', 'ts': '2026-10-30'}]}
        out = run(regs)
        self.assertEqual(out['reasons']['external'], 1)
        self.assertEqual(out['reasons']['not yet given'], 1)          # c3
        self.assertEqual([x['reason'] for x in out['misses']], ['external', 'not yet given'])


class PRC(unittest.TestCase):
    def test_critical_cards_only(self):
        out = run()
        self.assertEqual(out['prc'], {'due': 2, 'complete': 1, 'prc': 0.5})   # c1, c3 on A; c2 on C is not critical

    def test_the_chain_adds_its_cards(self):
        out = run(chain={'critical_chain': [{'marker': 'end', 'cards': ['C']}]})
        self.assertEqual(out['prc'], {'due': 3, 'complete': 1, 'prc': 0.333})


class CommitmentLevel(unittest.TestCase):
    def test_next_seven_days(self):
        cl = run()['commitment_level']
        self.assertEqual([c['id'] for c in cl['cards']], ['A', 'B', 'D'])      # F starts at 9
        self.assertEqual((cl['required'], cl['committed'], cl['level']), (3, 1, 0.333))   # A carries c1, c3; c5 is released

    def test_stage_will_and_leveled_start(self):
        items = cards()
        items[1]['stage'] = 'will'
        cl = run(items=items, chain={'leveled': {'F': {'lev_ES': 6}}})['commitment_level']
        self.assertEqual([c['id'] for c in cl['cards']], ['A', 'B', 'D', 'F'])
        self.assertEqual((cl['required'], cl['committed'], cl['level']), (4, 2, 0.5))


class ConstraintLog(unittest.TestCase):
    def regs(self):
        return {'commitments': commitments(),
                'constraints': [{'id': 'K1', 'card': 'B', 'sort': 'information', 'what': 'drawings', 'holder': 'person:b',
                                 'need_by': '2026-11-03', 'raised_on': '2026-10-20', 'state': 'open'},
                                {'id': 'K2', 'card': 'D', 'sort': 'resource', 'what': 'crane', 'holder': 'person:a',
                                 'need_by': '2026-11-10', 'raised_on': '2026-10-21', 'state': 'open'},
                                {'id': 'K3', 'card': 'F', 'sort': 'agreement', 'what': 'sign-off', 'holder': 'person:a',
                                 'need_by': '2026-11-01', 'raised_on': '2026-10-21', 'cleared_on': '2026-10-31',
                                 'state': 'cleared'}]}

    def test_overdue_and_days_to_need(self):
        log = {(e['id'], e['card']): e for e in run(self.regs())['constraint_log']}
        k1, k2, k3 = log[('K1', 'B')], log[('K2', 'D')], log[('K3', 'F')]
        self.assertEqual((k1['days_to_need'], k1['overdue'], k1['card_start']), (-1, True, '2026-11-07'))
        self.assertEqual((k2['days_to_need'], k2['overdue']), (6, False))
        self.assertEqual((k3['days_to_need'], k3['overdue'], k3['cleared_on']), (-3, False, '2026-10-31'))

    def test_a_constraint_card_before_is_a_second_source(self):
        log = {(e['id'], e['card']): e for e in run(self.regs())['constraint_log']}
        x = log[('X', 'D')]
        self.assertEqual((x['source'], x['state'], x['what'], x['holder']), ('predecessor card', 'open', 'permit in hand', 'person:b'))
        self.assertEqual((x['need_by'], x['need_by_source'], x['days_to_need']), ('2026-11-09', 'the start of the card it binds', 5))
        self.assertEqual(log[('K1', 'B')]['source'], 'register')


class MakeReady(unittest.TestCase):
    def test_open_constraint_or_conditions(self):
        regs = ConstraintLog().regs()
        mr = run(regs)['make_ready']
        self.assertEqual([m['id'] for m in mr], ['B', 'D', 'F'])     # by start: 11-07, 11-09, 11-13
        self.assertEqual(mr[1]['constraints'], ['K2', 'X'])
        self.assertEqual(mr[2]['conditions'], 'the room is booked')   # K3 on F is cleared; its conditions remain

    def test_the_look_ahead_boundary(self):
        items = [{'id': 'long41', 'dur_days': 41}, {'id': 'long42', 'dur_days': 42},
                 {'id': 'in', 'dur_days': 1, 'conditions': 'ready', 'links': {'predecessor': ['long41']}},
                 {'id': 'out', 'dur_days': 1, 'conditions': 'ready', 'links': {'predecessor': ['long42']}}]
        res = S.run(items, data_date=DD)
        self.assertEqual([m['id'] for m in L.lps(res, items, {})['make_ready']], ['in'])     # day 41 in, day 42 out
        self.assertEqual([m['id'] for m in L.lps(res, items, {}, lookahead_days=43)['make_ready']], ['in', 'out'])
        self.assertEqual(L.LOOKAHEAD, 42)


class RYG(unittest.TestCase):
    def res(self):
        return {'data_date': DD, 'items': [
            {'id': 'U1', 'type': 'unit', 'TF': -1, 'status': 'in_progress'},
            {'id': 'U2', 'type': 'unit', 'TF': 0, 'status': 'not_started'},
            {'id': 'U3', 'type': 'unit', 'TF': 4.5, 'status': 'not_started'},
            {'id': 'U4', 'type': 'unit', 'TF': 5, 'status': 'not_started'},
            {'id': 'U5', 'type': 'unit', 'TF': -3, 'status': 'complete'},
            {'id': 'U6', 'type': 'unit', 'TF': None, 'status': 'not_started'},
            {'id': 'a', 'type': 'activity', 'TF': -9, 'status': 'not_started'}]}

    def test_thresholds(self):
        out = {r['id']: r['ryg'] for r in L.lps(self.res(), [], {})['ryg']}
        self.assertEqual(out, {'U1': 'red', 'U2': 'yellow', 'U3': 'yellow', 'U4': 'green', 'U5': 'done',
                               'U6': 'unscheduled'})

    def test_thresholds_as_arguments(self):
        out = {r['id']: r['ryg'] for r in L.lps(self.res(), [], {}, ryg=(1, 3))['ryg']}
        self.assertEqual((out['U2'], out['U3'], out['U4']), ('red', 'green', 'green'))


class Targets(unittest.TestCase):
    def test_variance(self):
        items = [{'id': 'U'}, {'id': 'a', 'within': 'U', 'minutes': 120, 'state': 'done'},
                 {'id': 'b', 'within': 'U', 'minutes': 360, 'links': {'predecessor': ['a']}}]
        res = S.run(items, data_date=DD)
        t = {r['id']: r for r in L.lps(res, items, {'targets': {'U': 400, 'ghost': 100}})['targets']}
        self.assertEqual((t['U']['target_min'], t['U']['current_min'], t['U']['variance_min']), (400, 480, 80))
        self.assertIsNone(t['ghost']['variance_min'])
        self.assertTrue(t['ghost']['missing'])


class WeeklyPlan(unittest.TestCase):
    def test_mid_week(self):
        chain = {'day': {'person:a': {'should': ['B'], 'can': ['B', 'D'], 'should_min': 960, 'capacity_min': 480}}}
        w = run(chain=chain)['weekly_plan']
        self.assertEqual((w['from'], w['to']), ('2026-11-02', '2026-11-08'))
        self.assertEqual([x['id'] for x in w['wills']], ['c3', 'c4'])
        self.assertEqual((w['made'], w['due'], w['kept_on_time'], w['ppc']), (2, 1, 0, 0.0))   # c3 due Monday, open
        self.assertEqual(w['misses_without_reason'], ['c3'])
        self.assertEqual((w['should'], w['can']), ({'person:a': ['B']}, {'person:a': ['B', 'D']}))

    def test_a_will_with_no_by_and_an_early_delivery(self):
        cs = commitments()
        cs[3].update(state='claimed', kept_ts='2026-11-03T12:00:00Z')        # c4 delivered before its Friday
        cs.append({'id': 'c8', 'card': 'B', 'kind': 'will', 'for': 'person:a', 'state': 'open', 'ts': '2026-11-03T08:00:00Z'})
        w = run({'commitments': cs})['weekly_plan']
        self.assertEqual([x['id'] for x in w['wills']], ['c3', 'c4', 'c8'])
        self.assertEqual((w['made'], w['due'], w['kept_on_time'], w['ppc']), (3, 1, 1, 0.0))
        self.assertIsNone(w['should'])


class Laws(unittest.TestCase):
    def test_deterministic_and_never_writes_back(self):
        items, regs = cards(), {'commitments': commitments(), 'misses': [{'commitment': 'c3', 'reason': 'priority'}]}
        res = S.run(items, data_date=DD)
        before = json.dumps([res, items, regs], sort_keys=True)
        a = json.dumps(L.lps(res, items, regs), sort_keys=True)
        b = json.dumps(L.lps(res, copy.deepcopy(items), copy.deepcopy(regs)), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(json.dumps([res, items, regs], sort_keys=True), before)

    def test_honest_empty(self):
        out = run({})
        self.assertIsNone(out['ppc']['all_time']['ppc'])
        self.assertTrue(any('commitments' in m for m in out['missing']))
        self.assertTrue(any('chain' in m for m in out['missing']))
        none = L.lps({}, [], {})
        self.assertIsNone(none['data_date'])
        self.assertTrue(none['missing'])

    def test_the_data_date_is_an_argument(self):
        out = run(data_date='2026-11-10')       # a week on: c4 is now due too
        self.assertEqual(out['ppc']['all_time']['due'], 4)

    def test_no_names_dates_or_actors_in_code(self):
        with open(os.path.join(ENGINE, 'lps.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIsNone(re.search(r'\d{4}-\d{2}-\d{2}', src))
        for bad in ('person:', 'agent:', 'A-0', 'datetime.now', 'date.today', 'time.time', 'open('):
            self.assertNotIn(bad, src)



class ReviewE(unittest.TestCase):
    def test_due_today_is_not_a_miss_in_the_morning(self):
        regs = {'commitments': [{'id': 'k', 'card': 'a', 'by': DD, 'for': 'person:p', 'state': 'open'}]}
        out = L.lps(S.run([{'id': 'a', 'minutes': 60}], None, DD), [{'id': 'a', 'minutes': 60}], regs, data_date=DD)
        self.assertEqual((out['ppc']['all_time']['due'], out['misses']), (0, []))

    def test_the_last_miss_in_order_wins_never_the_latest_time(self):
        regs = {'commitments': [{'id': 'k', 'card': 'a', 'by': '2026-11-02', 'for': 'person:p', 'state': 'open'}],
                'misses': [{'commitment': 'k', 'reason': 'external', 'ts': '2099-01-01'},
                           {'commitment': 'k', 'reason': 'capacity', 'ts': '2026-11-03'}]}
        out = L.lps(S.run([{'id': 'a', 'minutes': 60}], None, DD), [{'id': 'a', 'minutes': 60}], regs, data_date=DD)
        self.assertEqual(out['misses'][0]['reason'], 'capacity')

if __name__ == '__main__':
    unittest.main()
