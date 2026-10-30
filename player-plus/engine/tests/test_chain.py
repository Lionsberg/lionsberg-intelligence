"""Tests for chain.py: the leveled critical chain, its buffers, the fever chart, release and the day.

Every number is checkable by pencil: the data date is a Monday, the calendar all seven days (a
day is a calendar day), and every holder pours 480 minutes a day unless a test says otherwise.
Run from the engine folder:  python3 -m unittest tests.test_chain
"""
import ast
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
import chain as C  # noqa: E402

DD = '2026-11-02'   # a Monday
X, Y, W = 'person:x', 'person:y', 'agent:w'
CAP = {X: {'min_per_day': 480, 'source': 'pledges'}, Y: {'min_per_day': 480, 'source': 'assumed'}}


def _source():
    with open(os.path.join(ENGINE, 'chain.py'), encoding='utf-8') as f:
        return f.read()


def run(items, capacity=CAP, registers=None, **kw):
    res = S.run(items, None, DD)
    return C.chain(res, items, capacity, registers, **kw)


def card(i, holder=None, minutes=None, preds=(), **kw):
    it = {'id': i}
    if holder:
        it['holder'] = holder
    if minutes is not None:
        it['minutes'] = minutes
    if preds:
        it['links'] = {'predecessor': list(preds)}
    it.update(kw)
    return it


def ms(i, preds=(), **kw):
    return card(i, preds=preds, kind='milestone', **kw)


class Leveling(unittest.TestCase):
    def test_two_cards_one_holder_one_waits(self):
        # A and B, 480 min each, one holder at 480 a day, no logic between them: by id, A takes
        # day 0 and B waits for day 1 (logic gives both day 0).
        out = run([card('A', X, 480), card('B', X, 480)])
        A, B = out['leveled']['A'], out['leveled']['B']
        self.assertEqual((A['lev_ES'], A['lev_EF'], A['lev_start'], A['lev_finish']), (0, 1, '2026-11-02', '2026-11-03'))
        self.assertEqual((B['lev_ES'], B['lev_EF'], B['lev_start'], B['lev_finish']), (1, 2, '2026-11-03', '2026-11-04'))
        # logic LF is 1 (late end); lev_TF = LF - lev_EF
        self.assertEqual((A['lev_TF'], B['lev_TF']), (0, -1))
        self.assertEqual(B['driven_by'], {'id': 'A', 'tie': 'resource'})

    def test_least_late_finish_goes_first(self):
        # B feeds a milestone due on day 1; A has float to the late end. B goes first though A's id is less.
        items = [card('A', X, 480), card('B', X, 480), ms('M', ['B'], by='2026-11-03'),
                 card('Z', Y, 1440)]
        lv = run(items)['leveled']
        self.assertEqual((lv['B']['lev_ES'], lv['A']['lev_ES']), (0, 1))

    def test_fractional_pour_shares_a_day(self):
        # 240-minute cards at 480 a day: A fills the morning, B the afternoon, C the next morning.
        out = run([card('A', X, 240), card('B', X, 240), card('C', X, 240)])
        lv = out['leveled']
        self.assertEqual([(lv[i]['lev_ES'], lv[i]['lev_EF']) for i in 'ABC'], [(0, 0.5), (0.5, 1), (1, 1.5)])
        self.assertEqual((lv['B']['lev_start'], lv['C']['lev_start'], lv['C']['lev_finish']),
                         ('2026-11-02', '2026-11-03', '2026-11-03'))

    def test_a_card_spans_days_at_its_holders_pace(self):
        # 600 minutes at 240 a day is 2.5 days (never rounded up).
        cap = {X: {'min_per_day': 240, 'source': 'pledges'}}
        lv = run([card('A', X, 600)], cap)['leveled']['A']
        self.assertEqual((lv['lev_ES'], lv['lev_EF'], lv['lev_finish']), (0, 2.5, '2026-11-04'))

    def test_logic_holds_after_leveling(self):
        # A -> M due 2026-11-03 (LF 1, TF 0); B -> C (Y, 240): late end 1.5, B LF 1, TF 0. A goes
        # first by id; B waits a day for X; C must follow B's leveled finish (2), not its logic one (1).
        items = [card('A', X, 480), ms('M', ['A'], by='2026-11-03'), card('B', X, 480), card('C', Y, 240, ['B'])]
        lv = run(items)['leveled']
        self.assertEqual((lv['B']['lev_ES'], lv['C']['lev_ES'], lv['C']['lev_EF']), (1, 2, 2.5))
        self.assertEqual(lv['C']['driven_by'], {'id': 'B', 'tie': 'logic'})

    def test_no_capacity_entry_is_listed_unleveled(self):
        items = [card('A', X, 480), card('B', 'person:z', 480), card('C', None, 480)]
        out = run(items)
        un = {u['id']: u['reason'] for u in out['unleveled']}
        self.assertEqual(un, {'B': 'its holder has no capacity entry', 'C': 'no holder'})
        self.assertEqual((out['leveled']['B']['lev_ES'], out['leveled']['B']['lev_EF']), (0, 1))  # its logic dates
        cap = dict(CAP, **{'person:z': {'min_per_day': 0, 'source': 'none'}})
        un = {u['id']: u['reason'] for u in run(items, cap)['unleveled']}
        self.assertEqual(un['B'], "its holder's capacity is 0 minutes a day")


class Chain(unittest.TestCase):
    def test_traced_through_a_resource_tie(self):
        # A (X, 1 day) -> C (Y, 2 days) -> M; B (X, 3 days) -> M.  Logic: A 0-1, C 1-3, B 0-3, M 3.
        # Leveling: A first (LF 1); then B (LF 3, TF 0, id < C): X's day 0 is full, so B pours 1-4.
        # M follows B at 4. The chain is A -> B (resource) -> M, not the logic path through C.
        items = [card('A', X, 480), card('C', Y, 960, ['A']), card('B', X, 1440), ms('M', ['B', 'C'])]
        out = run(items)
        ch = out['critical_chain']
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]['cards'], ['A', 'B', 'M'])
        self.assertEqual([t['tie'] for t in ch[0]['ties']], ['resource', 'logic'])
        self.assertEqual((ch[0]['lev_EF'], ch[0]['lev_finish']), (4, '2026-11-06'))
        self.assertEqual(ch[0]['marker_date'], None)

    def test_a_marker_names_a_milestone_mid_network(self):
        items = [card('A', X, 480), ms('M1', ['A']), card('B', X, 480, ['M1']), ms('M2', ['B'])]
        reg = {'markers': [{'id': 'M1', 'name': 'first', 'date': '2026-11-05', 'state': 'open'},
                           {'id': 'Q', 'name': 'unheld', 'date': '2026-11-09', 'state': 'open'}]}
        out = run(items, registers=reg)
        ch = {c['milestone']: c for c in out['critical_chain']}
        self.assertEqual(sorted(ch), ['M1', 'M2'])
        self.assertEqual((ch['M1']['cards'], ch['M1']['marker_date'], ch['M1']['end']), (['A', 'M1'], '2026-11-05', False))
        self.assertEqual(ch['M2']['cards'], ['A', 'M1', 'B', 'M2'])
        self.assertEqual(out['markers_without_milestone'], ['Q'])


class Buffers(unittest.TestCase):
    def test_project_buffer_root_sum_of_squares(self):
        # safety 300 and 400 -> sqrt(90000 + 160000) = 500 minutes; at 480 a day, 500/480 = 1.042 days.
        items = [card('A', X, 480, minutes_safe=780), card('B', X, 480, ['A'], minutes_safe=880), ms('M', ['B'])]
        out = run(items)
        pb = [b for b in out['buffers']['project'] if b['milestone'] == 'M'][0]
        self.assertEqual(pb['size_min'], 500)
        self.assertEqual(pb['size_days'], 1.042)
        self.assertEqual((pb['cards_with_two_estimates'], pb['cards_without']), (['A', 'B'], []))
        self.assertEqual((pb['chain_finish'], pb['due_with_buffer']), ('2026-11-04', '2026-11-05'))

    def test_no_two_estimates_says_so(self):
        out = run([card('A', X, 480), ms('M', ['A'])])
        pb = out['buffers']['project'][0]
        self.assertEqual((pb['size_min'], pb['note'], pb['cards_without']), (0, C.NO_BUFFER, ['A']))
        fv = out['fever'][0]
        self.assertIsNone(fv['zone'])
        self.assertIn(C.NO_BUFFER, fv['missing'])
        self.assertIn('no baseline', fv['missing'])

    def test_feeding_buffer_and_release_by_pull(self):
        # Chain A (X, 3 days) -> B (X, 1 day) -> M.  Side S (Y, 240 min, safe 720) -> B.
        # S: ES 0, LS = 3 - 0.5 = 2.5; feeding buffer = 480 min = 1 day at Y's 480;
        # release_on = max(0, 2.5 - 1) = 1.5 -> day 1 (2026-11-03). Chain cards: their leveled start.
        items = [card('A', X, 1440), card('B', X, 480, ['A', 'S']), ms('M', ['B']),
                 card('S', Y, 240, minutes_safe=720)]
        out = run(items)
        self.assertEqual(out['critical_chain'][0]['cards'], ['A', 'B', 'M'])
        fd = out['buffers']['feeding']
        self.assertEqual(len(fd), 1)
        self.assertEqual((fd[0]['joins'], fd[0]['from'], fd[0]['side_chain'], fd[0]['size_min'], fd[0]['size_days']),
                         ('B', 'S', ['S'], 480, 1))
        rel = out['release']
        self.assertEqual((rel['S']['release_on'], rel['S']['feeding_buffer_days'], rel['S']['on_chain']),
                         ('2026-11-03', 1, False))
        self.assertEqual((rel['A']['release_on'], rel['B']['release_on']), ('2026-11-02', '2026-11-05'))

    def test_release_never_before_early_start(self):
        # S (0.5 day) has no float and a 1-day feeding buffer: LS - buffer < ES, so it releases at ES.
        items = [card('A', X, 240), card('B', X, 480, ['A', 'S']), ms('M', ['B']),
                 card('S', Y, 240, minutes_safe=720)]
        rel = run(items)['release']['S']
        self.assertEqual(rel['release_on'], '2026-11-02')
        self.assertIn('early start', rel['rule'])


class Fever(unittest.TestCase):
    def test_zone_lines_at_the_boundaries(self):
        z = C.fever_zone
        self.assertEqual([z(0.15, 0), z(0.16, 0), z(0.30, 0), z(0.31, 0)], ['green', 'yellow', 'yellow', 'red'])
        # at done 0.5: yellow line 0.425, red line 0.65
        self.assertEqual([z(0.425, 0.5), z(0.43, 0.5), z(0.65, 0.5), z(0.66, 0.5)],
                         ['green', 'yellow', 'yellow', 'red'])
        self.assertIsNone(z(None, 0.5))

    def test_zone_lines_are_overridable(self):
        zones = {'red': (0.5, 0.0), 'yellow': (0.2, 0.0)}
        self.assertEqual([C.fever_zone(0.3, 0, zones), C.fever_zone(0.6, 0, zones)], ['yellow', 'red'])

    def test_consumed_against_a_baseline(self):
        # A: 480 min, safe 10080 -> safety 9600 = 20 days. M's leveled finish is day 1 (2026-11-03).
        # Baseline 2026-10-31 (index -2): slip 3, consumed 3/20 = 0.15, on the yellow line: green.
        # Baseline 2026-10-30 (index -3): slip 4, consumed 0.2: yellow.  2026-10-27: slip 7, 0.35: red.
        # The done card D just before A counts: done share 480 / (480 + 480) = 0.5 -> lines 0.425, 0.65.
        items = [card('A', X, 480, minutes_safe=10080), ms('M', ['A'])]
        got = []
        for bl in ('2026-10-31', '2026-10-30', '2026-10-27'):
            fv = run(items, registers={'baseline': {'M': {'lev_finish': bl}}})['fever'][0]
            got.append((fv['slip_days'], fv['consumed_share'], fv['zone']))
        self.assertEqual(got, [(3, 0.15, 'green'), (4, 0.2, 'yellow'), (7, 0.35, 'red')])
        items2 = [card('D', X, 480, state='done'), card('A', X, 480, ['D'], minutes_safe=10080), ms('M', ['A'])]
        fv = run(items2, registers={'baseline': {'M': {'lev_finish': '2026-10-27'}}})['fever'][0]
        self.assertEqual((fv['done_share'], fv['done_cards_before_chain'], fv['zone']), (0.5, ['D'], 'green'))


class Day(unittest.TestCase):
    def test_should_is_capped_by_the_days_capacity(self):
        # Three 240-min cards at 480 a day: A and B fill the data date; C pours onto day 1.
        out = run([card('A', X, 240), card('B', X, 240), card('C', X, 240)])
        d = out['day'][X]
        self.assertEqual(sorted(d['should']), ['A', 'B'])
        self.assertEqual((d['should_min'], d['capacity_min'], d['capacity_source']), (480, 480, 'pledges'))
        self.assertNotIn('Will', json.dumps(d))

    def test_should_is_at_least_one(self):
        # A 960-min card starting today is Should though it runs past the day; its day's share is 480.
        d = run([card('A', X, 960)])['day'][X]
        self.assertEqual((d['should'], d['should_min']), (['A'], 480))

    def test_chain_first_then_float(self):
        # N (Y, 120 min) -> P (X, 120) -> M due 2026-11-03; K (X, 60) -> L (Y, 2400), no milestone.
        # Late end 5.125; K: LF 0.125, leveled 0-0.125, lev_TF 0. P: logic start 0.25 (after N,
        # past K's end, so not pushed), leveled 0.25-0.5, LF 1, lev_TF 0.5. P is on the chain
        # and K is not: P comes first though K has less float.
        items = [card('N', Y, 120), card('P', X, 120, ['N']), ms('M', ['P'], by='2026-11-03'),
                 card('K', X, 60), card('L', Y, 2400, ['K'])]
        out = run(items)
        self.assertEqual(out['critical_chain'][0]['cards'], ['N', 'P', 'M'])
        self.assertEqual((out['leveled']['K']['lev_TF'], out['leveled']['P']['lev_TF']), (0, 0.5))
        self.assertEqual(out['day'][X]['should'], ['P', 'K'])

    def test_can_is_stage_can_or_predecessors_complete(self):
        # P (Y, 60 min) is open; A (X) follows it and starts at 0.125, so A is Should but not Can,
        # unless its stage says can. B's predecessor is done: Can.
        items = [card('P', Y, 60), card('A', X, 240, ['P']), card('D', Y, 60, state='done'),
                 card('B', X, 120, ['D']), card('E', X, 60, ['P'], stage='can')]
        d = run(items)['day'][X]
        self.assertEqual(sorted(d['should']), ['A', 'B', 'E'])
        self.assertEqual(sorted(d['can']), ['B', 'E'])


class Laws(unittest.TestCase):
    def items(self):
        return [card('A', X, 480, minutes_safe=780), card('C', Y, 960, ['A'], minutes_safe=1200),
                card('B', X, 1440, minutes_safe=1500), ms('M', ['B', 'C']),
                card('S', Y, 240, minutes_safe=720), card('T', X, 120, ['S'])]

    def test_deterministic(self):
        a = json.dumps(run(self.items()), sort_keys=True)
        b = json.dumps(run(list(reversed(self.items()))), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(a, json.dumps(run(self.items()), sort_keys=True))

    def test_inputs_are_never_written(self):
        items = self.items()
        res = S.run(items, None, DD)
        before_i, before_r, before_c = copy.deepcopy(items), copy.deepcopy(res), copy.deepcopy(CAP)
        C.chain(res, items, CAP, {'baseline': {'M': {'lev_finish': '2026-11-01'}}})
        self.assertEqual((items, res, CAP), (before_i, before_r, before_c))

    def test_no_names_dates_or_ids_in_code(self):
        src = _source()
        for bad in ("'Sir'", "'Sophia'", '"Sir"', '"Sophia"', 'the Army', "'person:", "'agent:", '1440'):
            self.assertNotIn(bad, src)
        self.assertIsNone(re.search(r"""['"](19|20)\d\d-\d\d""", src))

    def test_standard_library_only(self):
        tree = ast.parse(_source())
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                names.add(n.module.split('.')[0])
        self.assertEqual(names - {'schedule'}, names & set(sys.stdlib_module_names))

    def test_json_ready(self):
        out = run(self.items(), registers={'baseline': {'M': {'lev_finish': '2026-11-01'}}})
        self.assertEqual(json.loads(json.dumps(out)), out)
        self.assertTrue(all(isinstance(v, str) and v for v in out['basis'].values()))

    def test_working_day_calendar(self):
        # Mon-Fri from a Monday: A (2400 min = 5 days) fills indexes 0-4; B waits for index 5, the
        # next Monday, past the weekend.
        cal = {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}
        items = [card('A', X, 2400), card('B', X, 480)]
        res = S.run(items, cal, DD)
        lv = C.chain(res, items, CAP, calendar=cal)['leveled']
        self.assertEqual((lv['B']['lev_ES'], lv['B']['lev_start'], lv['A']['lev_finish']), (5, '2026-11-09', '2026-11-09'))


if __name__ == '__main__':
    unittest.main()
