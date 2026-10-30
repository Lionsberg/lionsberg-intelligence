"""Tests for exports.py: MS Project XML, the HTML wall and CSV, on a fixture checkable by pencil.

Run from the engine folder:
    python3 -m unittest tests.test_exports

THE FIXTURE (data date 2026-11-02, a Monday; calendar days; 480 minutes a day)
  U, a unit, holds A (480 min) and B (90 min, after A). C (960 min, holder agent:reader) after A
  by SS+1. M, a milestone after B. D, done. X, 480 min, after M, its title a script tag.
  Forward: A 0-1 · B 1-1.1875 · C 1-3 · M 1.1875 · X 1.1875-2.1875. All in ISO week 2026-W45.
  Open cards on the wall (units and done left out): A, B, C, M, X = 5.
  Links: A->B FS, A->C SS+1, B->M FS, M->X FS = 4, every one between two notes.
"""
import copy
import csv
import io
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import schedule as S  # noqa: E402
import exports as E  # noqa: E402

DD = '2026-11-02'
NS = '{http://schemas.microsoft.com/project}'
EVIL = '<script>alert(1)</script> & "quotes"'


def items():
    return [
        {'id': 'U', 'title': 'the unit'},
        {'id': 'A', 'title': 'frame', 'minutes': 480, 'holder': 'person:maker', 'stage': 'will', 'links': {'within': 'U'}},
        {'id': 'B', 'title': 'wire', 'minutes': 90, 'holder': 'person:maker', 'links': {'within': 'U', 'predecessor': ['A']}},
        {'id': 'C', 'title': 'read, then note', 'minutes': 960, 'holder': 'agent:reader', 'preds': 'A SS+1', 'stream': 'review'},
        {'id': 'M', 'title': 'ready', 'kind': 'milestone', 'links': {'predecessor': ['B']}},
        {'id': 'D', 'title': 'begun', 'minutes': 60, 'state': 'done', 'actual_finish': '2026-10-28'},
        {'id': 'X', 'title': EVIL, 'minutes': 480, 'links': {'predecessor': ['M']}},
    ]


def res_of(its=None):
    return S.run(items() if its is None else its, data_date=DD)


def tasks(xml):
    root = ET.fromstring(xml.encode('utf-8'))
    out = {}
    for t in root.iter(NS + 'Task'):
        name = t.find(NS + 'Name').text
        out[name.split(' — ')[0]] = t
    return root, out


class Mspdi(unittest.TestCase):
    def setUp(self):
        self.its = items()
        self.res = res_of(self.its)
        self.xml = E.mspdi(self.res, self.its, 'The test plan')
        self.root, self.t = tasks(self.xml)

    def test_parses_with_every_row_a_task(self):
        self.assertEqual(self.root.tag, NS + 'Project')
        self.assertEqual(self.root.find(NS + 'Name').text, 'The test plan')
        self.assertEqual(len(self.t), len(self.res['items']))
        self.assertEqual(sorted(self.t), ['A', 'B', 'C', 'D', 'M', 'U', 'X'])

    def test_flags_and_outline(self):
        g = lambda i, k: self.t[i].find(NS + k).text  # noqa: E731
        self.assertEqual(g('M', 'Milestone'), '1')
        self.assertEqual(g('A', 'Milestone'), '0')
        self.assertEqual(g('U', 'Summary'), '1')
        self.assertEqual(g('A', 'Summary'), '0')
        self.assertEqual((g('U', 'OutlineLevel'), g('A', 'OutlineLevel'), g('B', 'OutlineLevel')), ('1', '2', '2'))
        self.assertEqual(g('D', 'PercentComplete'), '100')
        uids = [int(x.find(NS + 'UID').text) for x in self.root.iter(NS + 'Task')]
        self.assertEqual(uids, list(range(1, len(uids) + 1)))
        order = [x.find(NS + 'Name').text.split(' — ')[0] for x in self.root.iter(NS + 'Task')]
        self.assertEqual(order.index('U') + 1, order.index('A'))   # a unit's cards follow it

    def test_predecessor_links(self):
        uid = {i: t.find(NS + 'UID').text for i, t in self.t.items()}

        def links(i):
            return [(pl.find(NS + 'PredecessorUID').text, pl.find(NS + 'Type').text, pl.find(NS + 'LinkLag').text)
                    for pl in self.t[i].findall(NS + 'PredecessorLink')]
        self.assertEqual(links('B'), [(uid['A'], '1', '0')])
        self.assertEqual(links('C'), [(uid['A'], '3', '4800')])   # SS, one day of 480 min in tenths
        self.assertEqual(links('M'), [(uid['B'], '1', '0')])
        self.assertEqual(links('A'), [])

    def test_duration_from_minutes(self):
        self.assertEqual(E._duration(90), 'PT1H30M0S')
        self.assertEqual(self.t['B'].find(NS + 'Duration').text, 'PT1H30M0S')
        self.assertEqual(self.t['M'].find(NS + 'Duration').text, 'PT0H0M0S')

    def test_dates_by_pencil(self):
        g = lambda i, k: self.t[i].find(NS + k).text  # noqa: E731
        self.assertEqual((g('A', 'Start'), g('A', 'Finish')), ('2026-11-02T08:00:00', '2026-11-02T16:00:00'))
        # B: ES 1 (11-03 08:00), EF 1.1875 -> 0.1875 x 480 = 90 min -> 09:30
        self.assertEqual((g('B', 'Start'), g('B', 'Finish')), ('2026-11-03T08:00:00', '2026-11-03T09:30:00'))

    def test_escaped(self):
        self.assertIn('&lt;script&gt;', self.xml)
        self.assertEqual(self.t['X'].find(NS + 'Name').text, 'X — ' + EVIL)


class Wall(unittest.TestCase):
    def setUp(self):
        self.its = items()
        self.res = res_of(self.its)
        self.html = E.wall_html(self.res, self.its)

    def test_one_note_per_open_card(self):
        ids = re.findall(r'<div class="note [a-z]+"[^>]* data-id="([^"]+)"', self.html)
        self.assertEqual(sorted(ids), ['A', 'B', 'C', 'M', 'X'])

    def test_self_contained(self):
        self.assertNotIn('http', self.html.lower())
        self.assertNotIn('src=', self.html)
        self.assertNotIn('<link', self.html)
        self.assertEqual(self.html.count('<style>'), 1)

    def test_title_escaped(self):
        self.assertNotIn('<script>alert', self.html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', self.html)
        self.assertEqual(self.html.count('</script>'), 2)   # the data block and the code, nothing more

    def test_close_control_and_filters(self):
        self.assertIn("x.className = 'close'", self.html)
        self.assertIn("'aria-label', 'Close'", self.html)
        self.assertIn("e.key === 'Escape'", self.html)
        self.assertIn('insertBefore(p, n.nextSibling)', self.html)   # in place, directly under the note
        for k in ('holder', 'unit', 'stream', 'state'):
            self.assertIn(f'<select data-key="{k}"', self.html)
        self.assertIn('<option value="agent:reader">agent:reader</option>', self.html)

    def test_every_link_drawn(self):
        lines = re.findall(r'<line[^>]*data-from="([^"]+)" data-to="([^"]+)"', self.html)
        self.assertEqual(sorted(lines), [('A', 'B'), ('A', 'C'), ('B', 'M'), ('M', 'X')])

    def test_states_and_theme(self):
        state = dict(re.findall(r'data-id="([^"]+)"[^>]*data-state="([a-z]+)"', self.html))
        rows = {r['id']: r for r in self.res['items']}
        for i, s in state.items():
            want = 'critical' if rows[i]['critical'] else 'near' if rows[i]['near_critical'] else 'free'
            self.assertEqual(s, want, i)
        for s in ('critical', 'near', 'free'):   # every state the notes carry has its style
            self.assertIn(f'.note.{s} {{', self.html)
        self.assertIn('prefers-color-scheme: dark', self.html)
        self.assertIn('--bg:', self.html)

    def test_columns_by_week_and_leveled(self):
        self.assertEqual(re.findall(r'data-week="([^"]+)"', self.html), ['2026-W45'])
        plan = {'chain': {'leveled': {'C': {'lev_start': '2026-11-16', 'lev_finish': '2026-11-18', 'lev_TF': 9}}}}
        lev = E.wall_html(self.res, self.its, plan, leveled=True)
        self.assertEqual(re.findall(r'data-week="([^"]+)"', lev), ['2026-W45', '2026-W46', '2026-W47'])
        self.assertRegex(lev, r'data-id="C"[^>]*data-state="free"')
        self.assertIn('4 cards have no leveled start', lev)
        self.assertEqual(E.wall_html(self.res, self.its, plan), self.html)   # leveled off: the plan is not read


class Csv(unittest.TestCase):
    def test_header_and_rows(self):
        res = res_of()
        rows = list(csv.reader(io.StringIO(E.csv_rows(res))))
        self.assertEqual(rows[0], ['id', 'title', 'type', 'holder', 'within', 'start', 'finish', 'TF', 'critical'])
        self.assertEqual(len(rows), len(res['items']) + 1)
        by = {r[0]: r for r in rows[1:]}
        self.assertEqual(by['C'][1], 'read, then note')
        self.assertEqual(by['A'][4], 'U')
        self.assertIn(by['C'][8], ('true', 'false'))


class Laws(unittest.TestCase):
    def test_deterministic(self):
        its = items()
        res = res_of(its)
        for f in (lambda r, i: E.mspdi(r, i, 'p'), lambda r, i: E.wall_html(r, i), lambda r, i: E.csv_rows(r)):
            self.assertEqual(f(res, its), f(res, its))
            self.assertEqual(f(res, its), f(res, list(reversed(its))))

    def test_inputs_never_written(self):
        its = items()
        res = res_of(its)
        before = copy.deepcopy((res, its))
        E.mspdi(res, its)
        E.wall_html(res, its, {'chain': {'leveled': {}}}, leveled=True)
        E.csv_rows(res)
        self.assertEqual((res, its), before)

    def test_honest_empty(self):
        ET.fromstring(E.mspdi({}, []).encode('utf-8'))
        self.assertIn('0 of 0 open cards shown', E.wall_html({}, []))
        self.assertEqual(E.csv_rows({}).count('\n'), 1)

    def test_no_dates_or_names_in_code(self):
        with open(os.path.join(ENGINE, 'exports.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIsNone(re.search(r'\d{4}-\d{2}-\d{2}', src))
        for word in ('person:', 'agent:', 'today(', 'now(', 'open('):
            self.assertNotIn(word, src)


if __name__ == '__main__':
    unittest.main()
