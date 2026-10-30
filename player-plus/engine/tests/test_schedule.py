"""Tests for schedule.py: one per feature, and agreement with cpm.py on a shared example.

The cpm.py figures below were taken from cpm.py itself on 2026-10-24 (the shared table is in
SHARED_TABLE). Run from the engine folder, by discovery (a dotted module name fails under -I):
    python3 -I -m unittest -v
and, to compare against cpm.py live as well:
    CPM_PY=/path/to/cpm.py python3 -I -m unittest -v -k test_schedule
"""
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import schedule as S  # noqa: E402

DD = '2026-11-02'   # a Monday

SHARED_TABLE = """| ID | Dur | Preds | Finish-by | Owner | Activity |
|---|---|---|---|---|---|
| A | 3 | — | | builder | frame |
| B | 2 | A | | builder | wire |
| C | 4 | A SS+1 | | reviewer | read |
| D | 1 | B, C FF+1 | | builder | fit |
| E | 0 | D | {fb} | | ready |
| F | 2 | C SF+3 | | reviewer | note |
| G | 1 | F FS+2, E | | builder | close |
"""


def shared_items(fb=None):
    rows = [('A', 3, '', 'builder'), ('B', 2, 'A', 'builder'), ('C', 4, 'A SS+1', 'reviewer'),
            ('D', 1, 'B, C FF+1', 'builder'), ('E', 0, 'D', None), ('F', 2, 'C SF+3', 'reviewer'),
            ('G', 1, 'F FS+2, E', 'builder')]
    out = []
    for i, d, p, h in rows:
        it = {'id': i, 'type': 'card', 'kind': 'milestone' if i == 'E' else 'activity',
              'dur_days': d, 'preds': p, 'holder': h}
        if i == 'E' and fb:
            it['by'] = fb
        out.append(it)
    return out


# (ES, EF, LS, LF, TF) as day offsets, read from cpm.py's output
GOLD_FB_1112 = {'A': (0, 3, 3, 6, 3), 'B': (3, 5, 6, 8, 3), 'C': (1, 5, 4, 8, 3), 'D': (5, 6, 8, 9, 3),
                'E': (6, 6, 9, 9, 3), 'F': (2, 4, 5, 7, 3), 'G': (6, 7, 9, 10, 3)}
GOLD_FB_1107 = {'A': (0, 3, -1, 2, -1), 'B': (3, 5, 2, 4, -1), 'C': (1, 5, 0, 4, -1),
                'D': (5, 6, 4, 5, -1), 'E': (6, 6, 5, 5, -1), 'F': (2, 4, 2, 4, 0), 'G': (6, 7, 6, 7, 0)}
GOLD_SERIAL_REVIEWER = {'A': (0, 3, 0, 3, 0), 'B': (3, 5, 6, 8, 3), 'C': (1, 5, 1, 5, 0),
                        'D': (5, 6, 8, 9, 3), 'E': (6, 6, 9, 9, 3), 'F': (5, 7, 5, 7, 0),
                        'G': (9, 10, 9, 10, 0)}
# working days (Mon-Fri), no finish-by: cpm.py --workdays dates (MM-DD) and TF
GOLD_WORKDAYS = {'A': ('11-02', '11-05', '11-02', '11-05', 0), 'B': ('11-05', '11-09', '11-05', '11-09', 0),
                 'C': ('11-03', '11-09', '11-03', '11-09', 0), 'D': ('11-09', '11-10', '11-09', '11-10', 0),
                 'E': ('11-10', '11-10', '11-10', '11-10', 0), 'F': ('11-04', '11-06', '11-04', '11-06', 0),
                 'G': ('11-10', '11-11', '11-10', '11-11', 0)}


def by_id(res):
    return {r['id']: r for r in res['items']}


def five_cards():
    """The module docstring's paper example."""
    return [{'id': 'A', 'dur_days': 3},
            {'id': 'B', 'dur_days': 2, 'links': {'predecessor': ['A']}},
            {'id': 'C', 'dur_days': 4, 'links': {'predecessor': ['A']}},
            {'id': 'D', 'dur_days': 1, 'links': {'predecessor': ['B', 'C']}},
            {'id': 'E', 'kind': 'milestone', 'by': '2026-11-09', 'links': {'predecessor': ['D']}}]


class PaperExample(unittest.TestCase):
    def test_docstring_numbers(self):
        r = by_id(S.run(five_cards(), data_date=DD))
        want = {'A': (0, 3, -1, 2, -1, 0), 'B': (3, 5, 4, 6, 1, 1), 'C': (3, 7, 2, 6, -1, 0),
                'D': (7, 8, 6, 7, -1, 0), 'E': (8, 8, 7, 7, -1, 0)}
        for i, w in want.items():
            x = r[i]
            self.assertEqual((x['ES'], x['EF'], x['LS'], x['LF'], x['TF'], x['FF']), w, i)
        res = S.run(five_cards(), data_date=DD)
        self.assertEqual(res['path']['critical'], ['A', 'C', 'D', 'E'])
        self.assertEqual(res['path']['driving'], ['A', 'C', 'D', 'E'])
        self.assertEqual(res['negative_float'], ['A', 'C', 'D', 'E'])

    def test_docstring_carries_the_example(self):
        self.assertIn('A LF = min(B.LS 4, C.LS 2) = 2, LS -1, TF -1', S.__doc__)


class AgreesWithCpm(unittest.TestCase):
    def check(self, res, gold):
        r = by_id(res)
        for i, g in gold.items():
            x = r[i]
            self.assertEqual((x['ES'], x['EF'], x['LS'], x['LF'], x['TF']), g, i)
            self.assertEqual(x['critical'], g[4] <= 0, i)

    def test_finish_by_with_float(self):
        self.check(S.run(shared_items('2026-11-12'), data_date=DD), GOLD_FB_1112)

    def test_negative_float(self):
        res = S.run(shared_items('2026-11-07'), data_date=DD)
        self.check(res, GOLD_FB_1107)
        self.assertEqual(by_id(res)['A']['late_start'], '2026-11-01')

    def test_serialize_equals_level(self):
        res = S.run(shared_items('2026-11-12'), data_date=DD, level_actors=['reviewer'])
        self.check(res, GOLD_SERIAL_REVIEWER)
        self.assertEqual(res['leveled']['ties'], [['C', 'F']])
        self.assertEqual(by_id(res)['G']['start'], '2026-11-11')

    def test_workdays_dates(self):
        cal = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}
        r = by_id(S.run(shared_items(), cal, DD))
        for i, g in GOLD_WORKDAYS.items():
            x = r[i]
            self.assertEqual((x['start'][5:], x['finish'][5:], x['late_start'][5:], x['late_finish'][5:],
                              x['TF']), g, i)

    @unittest.skipUnless(os.environ.get('CPM_PY'), 'set CPM_PY to compare against cpm.py live')
    def test_live(self):
        cases = [('2026-11-12', [], None), ('2026-11-07', [], None), ('', ['--workdays'], 'wd'),
                 ('2026-11-12', ['--serialize', 'reviewer'], 'reviewer')]
        for fb, flags, mode in cases:
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, 't.md')
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(SHARED_TABLE.format(fb=fb))
                out = subprocess.run([sys.executable, '-I', os.environ['CPM_PY'], p, '--start', DD] + flags,
                                     capture_output=True, text=True, check=True).stdout
            cal = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']} if mode == 'wd' else None
            lv = ['reviewer'] if mode == 'reviewer' else None
            r = by_id(S.run(shared_items(fb or None), cal, DD, level_actors=lv))
            for line in out.splitlines():
                m = re.match(r'^([A-G])\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(-?\d+)', line)
                if m:
                    x = r[m.group(1)]
                    self.assertEqual((x['start'][5:], x['finish'][5:], x['late_start'][5:],
                                      x['late_finish'][5:], x['TF']),
                                     (m.group(2), m.group(3), m.group(4), m.group(5), int(m.group(6))),
                                     (fb, flags, m.group(1)))


class Durations(unittest.TestCase):
    def test_minutes_to_days(self):
        cal = {'actors': {'person:slow': {'minutes_per_day': 240}}}
        items = [{'id': 'a', 'minutes': 600, 'holder': 'person:slow'},
                 {'id': 'b', 'minutes': 600, 'holder': 'person:other'},
                 {'id': 'c', 'minutes': 600, 'dur_days': 5},
                 {'id': 'd', 'kind': 'milestone', 'minutes': 30},
                 {'id': 'e', 'title': 'unsized'}]
        res = S.run(items, cal, DD)
        r = by_id(res)
        self.assertEqual(r['a']['dur_days'], 2.5)  # 600 / 240: minutes are the one unit, never rounded up
        self.assertEqual(r['b']['dur_days'], 1.25) # 600 / 480
        self.assertEqual(r['c']['dur_days'], 5)    # dur_days wins
        self.assertEqual(r['d']['dur_days'], 0)    # milestones are zero
        self.assertTrue(any('e: no minutes' in w for w in res['warnings']))

    def test_holiday_moves_dates(self):
        cal = {'holidays': ['2026-11-03']}
        r = by_id(S.run([{'id': 'a', 'dur_days': 2}], cal, DD))
        self.assertEqual(r['a']['finish'], '2026-11-05')
        self.assertEqual(r['a']['last_day'], '2026-11-04')


class MinutesTheOneUnit(unittest.TestCase):
    """Minutes are the one unit; a card keeps its fraction of a working day."""

    def test_short_cards_share_a_day(self):
        items = [{'id': 'a', 'minutes': 120}, {'id': 'b', 'minutes': 120, 'links': {'predecessor': ['a']}},
                 {'id': 'c', 'minutes': 240, 'links': {'predecessor': ['b']}}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual([(r[k]['ES'], r[k]['EF']) for k in 'abc'], [(0, 0.25), (0.25, 0.5), (0.5, 1)])
        self.assertEqual({r[k]['start'] for k in 'abc'}, {DD})
        self.assertEqual((r['c']['finish'], r['c']['last_day']), ('2026-11-03', DD))   # a whole EF is the next morning
        self.assertTrue(all(r[k]['critical'] for k in 'abc'))

    def test_a_fraction_carries_over_a_weekend(self):
        cal = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}
        r = by_id(S.run([{'id': 'a', 'dur_days': 4.5}, {'id': 'b', 'dur_days': 1, 'links': {'predecessor': ['a']}}],
                        cal, DD))
        self.assertEqual((r['b']['ES'], r['b']['EF']), (4.5, 5.5))
        self.assertEqual((r['b']['start'], r['b']['finish'], r['b']['last_day']),
                         ('2026-11-06', '2026-11-09', '2026-11-09'))   # Friday afternoon, Monday morning

    def test_a_fraction_crossing_calendars(self):
        cals = {'seven': {}, 'five': {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}}
        for dur, want in ((4.5, (4.5, 5.5)), (5.5, (5, 6))):
            items = [{'id': 'a', 'holon': 'seven', 'dur_days': dur},
                     {'id': 'b', 'holon': 'five', 'dur_days': 1, 'links': {'predecessor': ['a']}}]
            r = by_id(S.run(items, None, DD, calendars=cals))
            self.assertEqual((r['b']['ES'], r['b']['EF']), want)   # Friday mid-day stays; Saturday mid-day waits for Monday
            self.assertGreaterEqual(r['b']['start'], r['a']['start'])


class Within(unittest.TestCase):
    """The nesting edge (the Total Nested Holarchy of Work): every card lies within one unit; a link
    to or from a unit is routed to its entries and exits; a unit's dates are its children's."""

    def items(self):
        return [{'id': 'Q', 'title': 'a quest'},
                {'id': 'U1', 'within': 'Q'}, {'id': 'U2', 'within': 'Q', 'links': {'predecessor': ['U1']}},
                {'id': 'a', 'within': 'U1', 'dur_days': 2},
                {'id': 'b', 'within': 'U1', 'dur_days': 3},
                {'id': 'c', 'within': 'U1', 'dur_days': 1, 'links': {'predecessor': ['a', 'b']}},
                {'id': 'd', 'within': 'U2', 'dur_days': 2},
                {'id': 'e', 'within': 'U2', 'dur_days': 1, 'links': {'predecessor': ['d']}},
                {'id': 'z', 'dur_days': 1, 'links': {'predecessor': ['Q']}}]

    def test_units_route_to_entries_and_exits(self):
        res = S.run(self.items(), data_date=DD)
        r = by_id(res)
        self.assertEqual({r[k]['type'] for k in ('Q', 'U1', 'U2')}, {'unit'})
        self.assertEqual(r['d']['ES'], 4)                       # U1's exit c finishes at 4; U2's entry d starts then
        self.assertEqual(r['e']['EF'], 7)
        self.assertEqual(r['z']['ES'], 7)                       # after the quest's last exit
        self.assertEqual((r['U1']['ES'], r['U1']['EF'], r['U2']['ES'], r['U2']['EF']), (0, 4, 4, 7))
        self.assertEqual((r['Q']['ES'], r['Q']['EF']), (0, 7))
        self.assertEqual(r['Q']['holds'], ['U1', 'U2'])
        self.assertEqual(r['a']['within'], 'U1')
        self.assertEqual(r['a']['TF'], 1)                       # b is the longer branch
        self.assertTrue(r['Q']['critical'])

    def test_unit_minutes_roll_up_once(self):
        items = [{'id': 'U'}, {'id': 'a', 'within': 'U', 'minutes': 120, 'state': 'done'},
                 {'id': 'b', 'within': 'U', 'minutes': 360, 'links': {'predecessor': ['a']}}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual((r['U']['minutes'], r['U']['percent_complete'], r['U']['status']), (480, 25, 'in_progress'))
        self.assertEqual((r['U']['ES'], r['U']['EF']), (0, 0.75))

    def test_the_report_and_its_defects(self):
        items = [{'id': 'U', 'within': 'V'}, {'id': 'V', 'within': 'U'},          # a loop
                 {'id': 'x', 'within': 'nowhere', 'dur_days': 1},
                 {'id': 'y', 'within': ['U', 'V'], 'dur_days': 1, 'links': {'predecessor': ['U']}}]
        res = S.run(items, data_date=DD)
        h = res['holarchy']
        self.assertEqual(h['within_not_held'], ['x'])
        self.assertIn('x', h['open_ends']['nothing_before'])
        self.assertTrue(any('closes a loop' in w for w in res['warnings']))
        self.assertTrue(any('within 2 units' in w for w in res['warnings']))
        self.assertTrue(any('a card and a unit that holds it' in w for w in res['warnings']))


class DeadCommitmentsDateNothing(unittest.TestCase):
    def test_only_a_live_commitment_crosses(self):
        import engine as E
        folded = {'cards': [{'id': 'k', 'holon': 'other', 'title': 'theirs'}],
                  'commitments': [{'id': 'c1', 'card': 'k', 'by': '2026-11-20', 'state': 'retracted'},
                                  {'id': 'c2', 'card': 'k', 'by': '2026-11-21', 'state': 'released'}]}
        _, ext = E.holon_graph(folded, [], 'home', {'home', 'other'})
        self.assertEqual(ext, [])                                # nothing live: the card stays in its own holon
        folded['commitments'].append({'id': 'c3', 'card': 'k', 'by': '2026-11-22', 'state': 'open'})
        _, ext = E.holon_graph(folded, [], 'home', {'home', 'other'})
        self.assertEqual(len(ext), 1)


class Markers(unittest.TestCase):
    def test_a_milestone_names_its_marker(self):
        cal = {'markers': [{'id': 'M1', 'date': '2026-11-01', 'state': 'passed'}, {'id': 'M3', 'date': '2026-11-12'}]}
        items = [{'id': 'a', 'dur_days': 5}, {'id': 'm', 'kind': 'milestone', 'marker': 'M3', 'links': {'predecessor': ['a']}},
                 {'id': 'old', 'kind': 'milestone', 'marker': 'M1'}, {'id': 'x', 'kind': 'milestone', 'marker': 'M9'}]
        res = S.run(items, cal, DD)
        r = by_id(res)
        self.assertEqual((r['m']['LF'], r['m']['TF'], r['a']['TF']), (10, 5, 5))   # the marker's date is its target
        self.assertTrue(any('M1 has passed' in w for w in res['warnings']))
        self.assertTrue(any('M9 is not in the calendar' in w for w in res['warnings']))
        self.assertNotIn('2026', pathlib.Path(S.__file__).read_text().split('def marker')[1].split('def kind')[0])


class CommitmentBuffer(unittest.TestCase):
    def test_a_card_done_on_its_due_date_keeps_it(self):
        # review E, H4: the buffer runs to the last day of work, so a one-day card due that day is kept (0), not late
        for mins, want in ((480, (DD, 0, 'safe')), (360, (DD, 0, 'safe')), (960, ('2026-11-03', -1, 'cannot keep'))):
            it = {'id': 'a', 'minutes': mins, 'committed_by': [{'commitment': 'k', 'due_by': DD, 'state': 'open'}]}
            row = S.run([it], None, DD)['commitments'][0]
            self.assertEqual((row['computed_finish'], row['buffer_days'], row['signal']), want)


class Progress(unittest.TestCase):
    def test_done_work_drops_out(self):
        items = five_cards()
        items[0]['state'] = 'done'
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual(r['A']['status'], 'complete')
        self.assertIsNone(r['A']['ES'])
        self.assertEqual(r['C']['ES'], 0)

    def test_remaining_work_only(self):
        items = [{'id': 'a', 'dur_days': 4, 'percent_complete': 50, 'actual_start': '2026-10-30'},
                 {'id': 'b', 'dur_days': 4, 'remaining_minutes': 500},
                 {'id': 'c', 'dur_days': 4, 'remaining_days': 1, 'links': {'predecessor': ['a']}}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual((r['a']['status'], r['a']['ES'], r['a']['EF']), ('in_progress', 0, 2))
        self.assertAlmostEqual(r['b']['remaining_days'], 500 / 480, places=3)   # the fraction kept
        self.assertEqual((r['c']['ES'], r['c']['EF']), (2, 3))   # retained logic

    def test_dropped_cards_leave(self):
        items = five_cards()
        items[1]['state'] = 'released'
        r = by_id(S.run(items, data_date=DD))
        self.assertNotIn('B', r)


class ActivityTypes(unittest.TestCase):
    def test_level_of_effort_stretches(self):
        items = five_cards() + [{'id': 'L', 'kind': 'level-of-effort', 'minutes': 60,
                                 'links': {'predecessor': ['A'], 'successor': ['D']}}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual((r['L']['ES'], r['L']['EF']), (0, 8))
        self.assertFalse(r['L']['critical'])
        self.assertEqual(r['D']['ES'], 7)    # never drives

    def test_summary_rolls_up(self):
        items = [{'id': 'a', 'dur_days': 2, 'codes': ['P1/S1/K1']},
                 {'id': 'b', 'dur_days': 3, 'codes': ['P1/S1/K2'], 'links': {'predecessor': ['a']}},
                 {'id': 'c', 'dur_days': 9, 'codes': ['P2']},
                 {'id': 'sum', 'kind': 'summary', 'summarizes': 'P1/S1'}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual((r['sum']['ES'], r['sum']['EF']), (0, 5))


class Relationships(unittest.TestCase):
    def test_rel_maps(self):
        items = {'items': [{'id': 'a', 'dur_days': 4},
                           {'id': 'b', 'dur_days': 2, 'links': {'predecessor': ['a']}, 'rel': {'a': 'SS+1'}},
                           {'id': 'c', 'dur_days': 2, 'links': {'predecessor': ['a']}}],
                 'rel': {'c': {'a': 'FF-1'}}}
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual(r['b']['ES'], 1)
        self.assertEqual(r['c']['EF'], 3)

    def test_cycle_is_named(self):
        items = [{'id': 'a', 'dur_days': 1, 'links': {'predecessor': ['b']}},
                 {'id': 'b', 'dur_days': 1, 'links': {'predecessor': ['a']}}]
        with self.assertRaises(S.ScheduleError):
            S.run(items, data_date=DD)

    def test_unknown_link_is_not_yet_replicated(self):
        res = S.run([{'id': 'a', 'dur_days': 1, 'links': {'predecessor': ['zzz']}}], data_date=DD)
        self.assertTrue(any('not yet replicated' in w for w in res['warnings']))


class Constraints(unittest.TestCase):
    def test_imposed_dates_on_cards_are_reported_never_applied(self):
        # no imposed date on a Work Card; start-no-earlier, must-start-on and must-finish-on move nothing
        items = [{'id': 'a', 'dur_days': 5},
                 {'id': 'b', 'dur_days': 1, 'start_no_earlier': '2026-11-04'},
                 {'id': 'c', 'dur_days': 1, 'alap': True, 'links': {'successor': ['z']}},
                 {'id': 'z', 'kind': 'milestone', 'links': {'predecessor': ['a']}},
                 {'id': 'm', 'dur_days': 2, 'must_start_on': '2026-11-03', 'links': {'predecessor': ['a']}},
                 {'id': 'f', 'dur_days': 2, 'constraint': {'type': 'mfo', 'date': '2026-11-06'}}]
        res = S.run(items, data_date=DD)
        r = by_id(res)
        self.assertEqual(r['b']['ES'], 0)                          # not held by its date
        self.assertEqual((r['c']['ES'], r['c']['FF']), (4, 0))     # as-late-as-possible is a release rule, kept
        self.assertEqual(r['m']['ES'], 5)                          # logic, never a pin
        self.assertEqual(r['a']['TF'], 0)                          # no lateness invented upstream
        self.assertEqual((r['f']['ES'], r['f']['EF']), (0, 2))
        self.assertEqual(res['negative_float'], [])
        self.assertEqual(res['constraints']['not_applied'], 3)

    def test_milestone_targets_only(self):
        # a milestone keeps its finish-by as its marker's target (backward pass alone); finish-on reads as finish-by; start-on is reported only
        def plan(kind):
            return [{'id': 'A', 'dur_days': 5},
                    {'id': 'M', 'kind': 'milestone', 'links': {'predecessor': ['A']},
                     'constraint': {'kind': kind, 'date': '2026-11-05', 'reason': 'the hall is booked',
                                    'imposed_by': 'person:steward', 'source': 'world'}}]
        for kind in ('finish-by', 'finish-on'):
            res = S.run(plan(kind), data_date=DD)
            r = by_id(res)
            self.assertEqual((r['M']['ES'], r['M']['EF'], r['M']['TF'], r['A']['TF']), (5, 5, -2, -2))   # logic never moved
            item = res['constraints']['items'][0]
            self.assertEqual((item['negative_float_days'], item['defects'], item['applied']), (2, [], True))
        res = S.run(plan('start-on'), data_date='2026-10-30')
        r = by_id(res)
        self.assertEqual((r['M']['ES'], r['A']['TF']), (5, 0))
        self.assertFalse(res['constraints']['items'][0]['applied'])

    def test_constraints_report(self):
        items = [{'id': 'A', 'dur_days': 2, 'by': '2026-11-03'},
                 {'id': 'B', 'dur_days': 1, 'constraint': {'kind': 'start-no-earlier', 'date': '2026-11-05',
                                                           'reason': 'materials arrive', 'imposed_by': 'person:x',
                                                           'source': 'whim'}},
                 {'id': 'M', 'kind': 'milestone', 'by': '2026-11-10', 'links': {'predecessor': ['A', 'B']},
                  'constraint': [{'kind': 'finish-by', 'date': '2026-11-10', 'reason': 'the commitment',
                                  'imposed_by': 'person:y', 'source': 'commitment'},
                                 {'kind': 'as-late-as-possible'}]},
                 {'id': 'C', 'dur_days': 1},
                 {'id': 'X', 'constraint': {'kind': 'someday'}}]
        res = S.run(items, data_date=DD)
        c = res['constraints']
        self.assertEqual((c['count'], c['cards_constrained'], c['cards'], c['share_constrained']), (4, 3, 5, 0.6))
        self.assertEqual((c['hard'], c['soft'], c['on_activities'], c['not_applied']), (0, 4, 2, 2))
        self.assertEqual((c['no_reason'], c['no_imposer']), (2, 2))
        rows = {(r['card'], r['kind']): r for r in c['items']}
        self.assertEqual(rows[('A', 'finish-by')]['defects'],
                         ['no reason', 'no imposer', 'an imposed date on a card: reported, never applied'])
        self.assertEqual(rows[('A', 'finish-by')]['negative_float_days'], 1)       # the gap is still said, as a variance
        self.assertEqual(rows[('B', 'start-no-earlier')]['delay_days'], 0)          # it holds nothing
        self.assertIn('source not commitment, world or law', rows[('B', 'start-no-earlier')]['defects'])
        self.assertTrue(rows[('M', 'finish-by')]['applied'])
        self.assertEqual(c['by_source'], {'commitment': 1, 'unstated': 2, 'whim': 1})
        self.assertTrue(any("constraint kind 'someday' unknown" in w for w in res['warnings']))
        self.assertIn('Constraints: 4 on 3 of 5 cards', S.markdown(res))

    def test_free_float_and_near_critical(self):
        res = S.run(five_cards(), data_date=DD, near=1)
        self.assertEqual(by_id(res)['B']['FF'], 1)     # 2 to D, held to its total float
        self.assertEqual(res['path']['near_critical'], ['B'])


class Baselines(unittest.TestCase):
    def test_freeze_load_variance(self):
        with tempfile.TemporaryDirectory() as td:
            pd = os.path.join(td, 'plan')
            p1 = S.freeze(five_cards(), 'first', None, DD, pd)
            p2 = S.freeze(five_cards(), 'second', None, DD, pd)
            self.assertTrue(p1.endswith('baseline-1.json') and p2.endswith('baseline-2.json'))
            self.assertEqual(S.load_baseline(pd)['name'], 'second')
            b = S.load_baseline(pd, 'first')
            self.assertEqual(b['n'], 1)
            self.assertEqual(S.load_baseline(pd, '2')['name'], 'second')
            res = S.run(five_cards(), data_date='2026-11-04', baseline=b)
            self.assertEqual(res['baseline']['name'], 'first')
            self.assertEqual(res['variance']['milestones']['E']['finish_days'], 2)
            self.assertEqual(by_id(res)['E']['variance_days'], 2)


class Codes(unittest.TestCase):
    def test_rollup_many_codes(self):
        items = [{'id': 'a', 'dur_days': 2, 'minutes': 100, 'state': 'done', 'codes': ['P1/S1', 'risk/high']},
                 {'id': 'b', 'dur_days': 3, 'minutes': 300, 'codes': {'pillar': 'P1/S2'}}]
        ru = S.run(items, data_date=DD)['rollup']
        self.assertEqual(ru['P1']['cards'], ['a'])
        self.assertEqual(ru['risk/high']['percent_complete'], 100)
        self.assertEqual(ru['pillar:P1/S2']['minutes'], 300)
        self.assertEqual(ru['pillar:P1']['finish'], '2026-11-05')


class Resources(unittest.TestCase):
    def test_load_against_capacity(self):
        cal = {'actors': {'person:x': {'minutes_per_day': 120}}}
        items = [{'id': 'a', 'dur_days': 2, 'minutes': 300, 'holder': 'person:x'},
                 {'id': 'b', 'dur_days': 1, 'minutes': 60, 'holder': 'person:x'}]
        res = S.run(items, cal, DD)
        day0 = [r for r in res['load'] if r['date'] == DD][0]
        self.assertEqual((day0['minutes'], day0['capacity']), (210, 120))
        self.assertEqual(res['load_by_actor']['person:x']['over_days'], ['2026-11-02', '2026-11-03'])


class AcrossHolons(unittest.TestCase):
    def test_external_and_as_of(self):
        ext = [{'v': 1, 'id': 'ext1', 'ts': '2026-10-30T10:00:00-07:00', 'holon': 'h-cell',
                'type': 'publish', 'body': {'kind': 'milestone', 'title': 'room ready', 'by': '2026-11-05'}},
               {'v': 1, 'id': 'ext2', 'ts': '2026-10-31T09:00:00-07:00', 'holon': 'h-cell',
                'type': 'publish', 'body': {'by': '2026-11-04'}, 'links': {'predecessor': ['m']}},
               {'v': 1, 'id': 'ext0', 'ts': '2026-10-01T09:00:00-07:00', 'holon': 'h-other', 'type': 'say'}]
        items = {'items': [{'id': 'a', 'holon': 'h-home', 'dur_days': 1, 'links': {'predecessor': ['ext1']},
                            'ts': '2026-10-24T13:00:00-07:00'},
                           {'id': 'm', 'holon': 'h-home', 'kind': 'milestone', 'links': {'predecessor': ['a']}},
                           {'id': 'k', 'holon': 'h-cell', 'dur_days': 1}],
                 'as_of': {'h-home': {'ts': '2026-10-24T13:05:00-07:00'}}}
        res = S.run(items, None, DD, external=ext)
        r = by_id(res)
        self.assertEqual(r['a']['ES'], 3)                      # waits for the published milestone
        self.assertEqual(r['m']['constraints']['need_by'], '2026-11-04')
        self.assertEqual(r['m']['TF'], -2)
        self.assertEqual(res['as_of'], {'h-cell': '2026-10-31T09:00:00-07:00',
                                        'h-home': '2026-10-24T13:05:00-07:00',
                                        'h-other': '2026-10-01T09:00:00-07:00'})
        self.assertEqual([b['type'] for b in res['buffers'] if b['milestone'] == 'm'], ['feeding'])


class CriticalChain(unittest.TestCase):
    def test_project_buffer(self):
        b = S.run(five_cards(), data_date=DD)['buffers'][0]
        self.assertEqual((b['type'], b['chain_days'], b['size_days'], b['consumed_days'], b['signal']),
                         ('project', 8, 4, 5, 'red'))
        self.assertEqual(b['chain'], ['A', 'C', 'D', 'E'])
        items = five_cards()
        items[4]['by'] = '2026-11-14'
        b = S.run(items, data_date=DD)['buffers'][0]
        self.assertEqual((b['consumed_days'], b['signal']), (0, 'green'))

    def test_drum(self):
        cal = {'actors': {'person:x': {'minutes_per_day': 480}, 'person:y': {'minutes_per_day': 60}}}
        items = five_cards()
        items[0].update(holder='person:x', minutes=900)
        items[2].update(holder='person:y', minutes=900)
        res = S.run(items, cal, DD)
        self.assertEqual(res['drum']['actor'], 'person:y')


class EarnedValue(unittest.TestCase):
    def test_ev_in_minutes(self):
        items = [{'id': 'A', 'dur_days': 3, 'minutes': 300, 'holon': 'h'},
                 {'id': 'B', 'dur_days': 2, 'minutes': 200, 'holon': 'h', 'links': {'predecessor': ['A']}}]
        with tempfile.TemporaryDirectory() as td:
            S.freeze(items, 'plan', None, DD, td)
            base = S.load_baseline(td)
        items[0]['state'] = 'done'
        tea = [{'type': 'tea', 'card': 'A', 'minutes': 360, 'holon': 'h'}]
        res = S.run({'items': items + tea}, None, '2026-11-05', baseline=base)
        ev = res['ev']
        self.assertEqual((ev['PV'], ev['EV'], ev['AC'], ev['SPI'], ev['CPI']), (300, 300, 360, 1, 0.833))
        res = S.run({'items': items + tea}, None, '2026-11-06', baseline=base)
        self.assertEqual((res['ev']['PV'], res['ev']['SPI']), (400, 0.75))
        self.assertEqual(res['score']['h']['earned'], 300)

    def test_score_lines(self):
        items = [{'type': 'commit', 'holon': 'h', 'by': '2026-11-01', 'status': 'kept', 'kept_ts': '2026-10-31T10:00:00Z'},
                 {'type': 'commit', 'holon': 'h', 'by': '2026-10-30'},
                 {'type': 'commit', 'holon': 'h', 'by': '2026-12-30'},
                 {'type': 'commit', 'holon': 'h', 'status': 'released'},
                 {'type': 'tea', 'holon': 'h', 'minutes': 45},
                 {'type': 'sight', 'holon': 'h', 'text': 'a garden', 'value': 3}]
        s = S.run(items, None, DD)['score_lines']
        self.assertEqual((s['commitments_made'], s['commitments_kept'], s['kept_on_time'], s['open_past_due']),
                         (3, 1, 1, 1))
        self.assertEqual((s['tea_minutes'], s['value_sighted'], s['value_sighted_sum']), (45, 1, 3))


class Gameclock(unittest.TestCase):
    def test_turnings_2026(self):
        self.assertEqual([d.isoformat() for d, _ in S.turnings(2026)],
                         ['2026-03-20', '2026-06-21', '2026-09-23', '2026-12-21'])
        cal = S.Calendar({'gameclock': {'utc_offset_hours': -7}})
        self.assertEqual(S.turnings(2026, cal)[2][0].isoformat(), '2026-09-22')

    def test_spans(self):
        g = S.gameclock('2026-11-02')
        self.assertEqual((g['season'], g['span'], g['day_of_season']), ('Autumn', 1, 41))
        g = S.gameclock('2026-12-18')
        self.assertIsNone(g['span'])     # day 87 of 89: past the second span
        self.assertNotIn('omnispection', g)   # continual, never a point in the season
        self.assertEqual(S.gameclock('2026-11-10')['span'], 2)
        g = S.gameclock('2026-07-01', S.Calendar({'gameclock': {'hemisphere': 'south'}}))
        self.assertEqual(g['season'], 'Winter')

    def test_known_moons_2026(self):
        m = S.moons('2026-01-01', '2026-03-31')
        self.assertIn({'kind': 'full_moon', 'date': '2026-01-03'}, m)
        self.assertIn({'kind': 'new_moon', 'date': '2026-01-18'}, m)
        self.assertIn({'kind': 'new_moon', 'date': '2026-02-17'}, m)    # the annular eclipse
        self.assertIn({'kind': 'full_moon', 'date': '2026-03-03'}, m)   # the total lunar eclipse
        self.assertEqual(len(m), 6)
        t = S.moon_moment(S.math.floor((2026 + 17 / 365.25 - 2000) * 12.3685))
        self.assertLess(abs((t - dt.datetime(2026, 1, 18, 19, 52, tzinfo=dt.timezone.utc)).total_seconds()), 3600)

    def test_moons_from_the_calendar(self):
        cal = S.Calendar({'gameclock': {'new_moons': ['2026-01-19'], 'full_moons': ['2026-01-03']}})
        m = S.moons('2026-01-01', '2026-01-31', cal)
        self.assertEqual(m, [{'kind': 'full_moon', 'date': '2026-01-03'}, {'kind': 'new_moon', 'date': '2026-01-19'}])

    def test_rhythms(self):
        r = S.rhythms('2026-09-17', '2026-09-23')
        self.assertEqual([x['kind'] for x in r if x['kind'] == 'day'], ['day'] * 7)
        self.assertEqual([(x['kind'], x['date']) for x in r if x['kind'] != 'day'],
                         [('turning', '2026-09-23')])
        r = S.rhythms('2026-01-17', '2026-01-19')
        self.assertEqual([(x['kind'], x['date']) for x in r],
                         [('day', '2026-01-17'), ('day', '2026-01-18'), ('new_moon', '2026-01-18'),
                          ('day', '2026-01-19')])
        self.assertEqual([x['kind'] for x in S.rhythms('2026-09-23')], ['day', 'turning'])
        self.assertEqual([x['date'] for x in S.rhythms('2026-09-22', {'gameclock': {'utc_offset_hours': -7}})
                          if x['kind'] == 'turning'], ['2026-09-22'])   # one date and a raw calendar
        self.assertEqual(S.gameclock('2026-09-22', {'gameclock': {'utc_offset_hours': -7}})['day_of_season'], 1)
        self.assertEqual(S.rhythms('not a date'), [])
        self.assertEqual(S.rhythms('2026-02-02', '2026-02-01'), [])

    def test_explicit_turnings(self):
        cal = S.Calendar({'gameclock': {'turnings': ['2026-09-20', '2026-12-20']}})
        self.assertEqual(S.gameclock('2026-09-21', cal)['day_of_season'], 2)


class ReviewRepairs(unittest.TestCase):
    """Hand cases from an independent engine review (B1-B6, E31, A11)."""

    def test_b1_card_kind_from_the_fold(self):
        items = [{'id': 'v', 'kind': 'card', 'body_kind': 'milestone', 'minutes': 120, 'by': '2026-11-15',
                  'holder': 'person:steward', 'holon': 'cell'},
                 {'id': 'l', 'kind': 'card', 'body': {'kind': 'level-of-effort'}, 'minutes': 60,
                  'links': {'predecessor': ['v']}}]
        res = S.run(items, {'minutes_per_actor_per_day': 240}, '2026-10-24')
        r = by_id(res)
        self.assertEqual((r['v']['type'], r['v']['ES'], r['v']['EF'], r['v']['LS'], r['v']['TF']),
                         ('milestone', 0, 0, 22, 22))
        self.assertEqual(r['l']['type'], 'loe')
        self.assertEqual([b['milestone'] for b in res['buffers']], ['v'])
        self.assertEqual(res['load'], [])            # a milestone carries no days of work

    @unittest.skipUnless(os.path.isdir(os.path.join(ENGINE, 'fixtures', 'hq')), 'no fixture holon')
    def test_b1_the_fixture_through_the_fold(self):
        try:
            import engine
        except Exception as e:                       # the fold is a sibling; say why if it is absent
            self.skipTest(f'engine.py not importable: {e}')
        folded, holons, lines, problems, cal = engine.read_hq(os.path.join(ENGINE, 'fixtures', 'hq'))
        folded.pop('_fold', None)
        res = S.run(folded, cal, '2026-10-24')
        venue = [x for x in res['items'] if x['title'] == 'Find a venue'][0]
        self.assertEqual((venue['type'], venue['ES'], venue['EF'], venue['LS'], venue['LF'], venue['TF']),
                         ('milestone', 0, 0, 22, 22, 22))
        self.assertIn(venue['id'], [b['milestone'] for b in res['buffers']])
        for x in res['items']:
            if x['FF'] is not None and x['TF'] is not None:
                self.assertLessEqual(x['FF'], max(x['TF'], 0), x['title'])

    def test_b2_alap_never_past_its_own_finish_by(self):
        # on a milestone, where a finish-by is a target: as-late-as-possible never pushes it past that target
        items = [{'id': 'X', 'kind': 'milestone', 'by': '2026-11-07', 'alap': True, 'links': {'predecessor': ['P']}},
                 {'id': 'P', 'dur_days': 3}, {'id': 'Y', 'dur_days': 10}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual((r['X']['ES'], r['X']['TF']), (5, 0))
        # on an activity, the finish-by is reported and never applied: the card floats with the network's late end
        r = by_id(S.run([{'id': 'X', 'dur_days': 3, 'by': '2026-11-07', 'alap': True}, {'id': 'Y', 'dur_days': 10}], data_date=DD))
        self.assertEqual((r['X']['ES'], r['X']['EF'], r['X']['TF']), (7, 10, 0))

    def test_b3_free_float_never_above_total_float(self):
        r = by_id(S.run([{'id': 'X', 'dur_days': 3, 'by': '2026-11-07'}, {'id': 'Y', 'dur_days': 10}], data_date=DD))
        self.assertEqual((r['X']['TF'], r['X']['FF']), (7, 7))
        self.assertLessEqual(r['X']['FF'], r['X']['TF'])

    def test_b5_one_day_card_spans_a_day(self):
        items = [{'id': 'A', 'dur_days': 2, 'percent_complete': 25},
                 {'id': 'B', 'dur_days': 1, 'links': {'predecessor': ['A']}}]
        r = by_id(S.run(items, data_date='2026-11-03'))
        self.assertEqual(r['A']['remaining_days'], 1.5)         # the fraction kept, never rounded up
        self.assertEqual((r['B']['ES'], r['B']['EF']), (1.5, 2.5))
        self.assertEqual((r['B']['start'], r['B']['finish'], r['B']['last_day']),
                         ('2026-11-04', '2026-11-05', '2026-11-05'))   # starts mid-day, works into the next
        r = by_id(S.run([{'id': 'h', 'dur_days': 0.5}], data_date=DD))
        self.assertEqual((r['h']['EF'], r['h']['start'], r['h']['finish'], r['h']['last_day']),
                         (0.5, DD, DD, DD))                     # a half-day card starts and ends the same day

    def test_b6_start_to_start_from_actual_start(self):
        items = [{'id': 'P', 'dur_days': 4, 'actual_start': '2026-10-28', 'remaining_days': 1},
                 {'id': 'Q', 'dur_days': 2, 'preds': 'P SS+3'}]
        r = by_id(S.run(items, data_date=DD))
        self.assertEqual(r['Q']['ES'], 0)
        items[1]['preds'] = 'P SS+7'                            # 10-28 + 7 = 11-04
        self.assertEqual(by_id(S.run(items, data_date=DD))['Q']['start'], '2026-11-04')

    def test_e31_each_holon_on_its_own_calendar(self):
        cell = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri'], 'minutes_per_day': 240}
        lines = [{'id': 'c1', 'holon': 'cell', 'minutes': 1200, 'holder': 'person:steward'},
                 {'id': 'c2', 'holon': 'cell', 'kind': 'milestone', 'by': '2026-11-13',
                  'links': {'predecessor': ['c1']}}]
        home_a = {'minutes_per_day': 480}                                    # all seven days
        home_b = {'working_days': ['mon', 'wed', 'fri'], 'minutes_per_day': 120}
        ra = by_id(S.run([dict(x) for x in lines] + [{'id': 'a', 'holon': 'ha', 'dur_days': 1}],
                         home_a, '2026-10-30', calendars={'cell': cell}))
        rb = by_id(S.run([dict(x) for x in lines] + [{'id': 'b', 'holon': 'hb', 'dur_days': 1}],
                         home_b, '2026-10-30', calendars={'cell': cell}))
        for cid in ('c1', 'c2'):
            self.assertEqual({k: ra[cid][k] for k in ('ES', 'EF', 'LS', 'LF', 'TF', 'FF', 'start', 'finish')},
                             {k: rb[cid][k] for k in ('ES', 'EF', 'LS', 'LF', 'TF', 'FF', 'start', 'finish')})
        self.assertEqual((ra['c1']['dur_days'], ra['c1']['start'], ra['c1']['finish']),
                         (5, '2026-10-30', '2026-11-06'))     # Fri 10-30 is day 0; Fri, Mon-Thu
        self.assertEqual(ra['c2']['TF'], 5)                                   # by Fri 11-13: index 10 - 5
        # without the cell's calendar each house would compute its own answer: the defect repaired
        na = by_id(S.run([dict(x) for x in lines], home_a, '2026-10-30'))
        nb = by_id(S.run([dict(x) for x in lines], home_b, '2026-10-30'))
        self.assertNotEqual(na['c1']['finish'], nb['c1']['finish'])

    def test_a11_weekly_freeze_like_seasonal(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = S.freeze(five_cards(), None, None, DD, td, depth='weekly')
            p2 = S.freeze(five_cards(), None, None, DD, td, depth='seasonal')
            with open(p1, encoding='utf-8') as f:
                w = json.load(f)
            with open(p2, encoding='utf-8') as f:
                s = json.load(f)
            self.assertEqual((w['n'], w['depth'], w['name']), (1, 'weekly', 'weekly-2026-11-02'))
            self.assertEqual(w['items'], s['items'])
            self.assertEqual(S.load_baseline(td, 'weekly-2026-11-02')['n'], 1)

    def test_other_sorts_of_constraint_are_not_read(self):
        items = [{'id': 'M', 'kind': 'milestone', 'constraint': [
            {'sort': 'agreement', 'kind': 'finish-by', 'date': '2026-11-01', 'reason': 'awaiting a yes'},
            {'kind': 'finish-by', 'date': '2026-11-09', 'reason': 'the hall', 'imposed_by': 'person:x',
             'source': 'world'}]}]
        res = S.run(items, data_date=DD)
        self.assertEqual(res['constraints']['count'], 1)
        self.assertEqual(by_id(res)['M']['constraints']['finish_no_later'], '2026-11-09')


class NullGuards(unittest.TestCase):
    def test_garbage_in(self):
        items = [None, 'text', 3, {'id': None}, {'id': 'a', 'dur_days': 'two', 'links': {'predecessor': [None, 5]},
                                                 'codes': 7, 'by': 'soon', 'percent_complete': 'half'},
                 {'id': 'b', 'minutes': -5, 'links': 'x'}]
        res = S.run(items, {'working_days': 'weekdays', 'actors': []}, 'not a date')
        self.assertEqual(res['v'], 1)
        self.assertIn('a', by_id(res))
        self.assertEqual(S.run(None, None, DD)['items'], [])
        self.assertEqual(S.run({}, None, DD)['items'], [])


class Cli(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'schedule.py')] + list(args),
                              capture_output=True, text=True)

    def test_run_freeze_clock(self):
        with tempfile.TemporaryDirectory() as td:
            items = os.path.join(td, 'items.json')
            with open(items, 'w', encoding='utf-8') as f:
                json.dump(five_cards(), f)
            ext = os.path.join(td, 'pub.jsonl')
            with open(ext, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'id': 'e1', 'holon': 'h2', 'ts': '2026-10-20T00:00:00Z'}) + '\nnot json\n')
            p = self.cli('freeze', items, '--name', 'first', '--data-date', DD)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(os.path.isfile(os.path.join(td, 'plan', 'baseline-1.json')))
            p = self.cli('run', items, '--data-date', DD, '--baseline', 'first', '--external', ext)
            self.assertEqual(p.returncode, 0, p.stderr)
            res = json.loads(p.stdout)
            self.assertEqual(res['baseline']['name'], 'first')
            self.assertEqual(res['as_of'], {'h2': '2026-10-20T00:00:00Z'})
            p = self.cli('run', items, '--data-date', DD, '--markdown')
            self.assertIn('| A |', p.stdout)
            self.assertEqual(self.cli('run', items, '--baseline', 'nope').returncode, 2)
        p = self.cli('clock', '2026-11-02')
        out = json.loads(p.stdout)
        self.assertEqual(out['gameclock']['season'], 'Autumn')
        self.assertEqual((out['from'], out['to']), ('2026-09-23', '2026-12-21'))
        self.assertEqual([x['date'] for x in out['turnings']], ['2026-09-23', '2026-12-21'])
        self.assertEqual(len([m for m in out['moons'] if m['kind'] == 'full_moon']), 3)
        p = self.cli('clock', '2026-02-01', '--to', '2026-03-31')
        self.assertIn({'kind': 'new_moon', 'date': '2026-02-17'}, json.loads(p.stdout)['moons'])


if __name__ == '__main__':
    unittest.main()
