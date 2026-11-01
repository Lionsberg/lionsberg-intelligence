"""test_measure.py — the matrix's defaults are measured, not asserted, checked law by law.

The instrument lives in `personas/measure/`: one fixed scenario per axis of the companion's matrix,
and `measure.py`, which folds an independent reader's ratings into a table. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_measure.py -v
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.dirname(ENGINE)
MEASURE = os.path.join(HOME, 'personas', 'measure')
if MEASURE not in sys.path:
    sys.path.insert(0, MEASURE)

import measure   # noqa: E402

COMPANION = os.path.join(HOME, 'personas', 'Character-Matrix-companion.md')
CARRIER = os.path.join(HOME, 'personas', 'Character-Matrix-carrier.md')
SCENARIOS = os.path.join(MEASURE, 'scenarios.json')
README = os.path.join(MEASURE, 'README.md')
# The kit's lint for words on these pages: no contraction, the older word, no honorific, no vendor name.
LINT = ("n't", "I'd", "I'll", "you'd", "it's", "we'll", "you'll", "I'm", "you're", "'re ", "'ve ",
        "prom" + "ise", "S" + "ir", "Cla" + "ude", " house", " HQ", " estate")
README_MAX = 60
# A tell shares no run of this many words with either matrix (a shared run steers the reader).
RUN = 4
# Words that carry one axis's fault; a tell of any other axis holds none of them (the tell is its own pole only).
FAULTS = {
    'Warmth': r'\b(care|caring|cold|coldly|kind|kindly|harsh|gentle)\b',
    'Stance': r'\b(decid\w*|in charge)\b',
    'Conflict approach': r'\b(lectur\w*|argu\w*|contest)\b',
    'Ask vs act': r'\b(without asking|refus\w*)\b',
    'Verbosity': r'\b(buried|thin|paragraphs)\b',
    'Judgment vs deference': r'\b(against the person|as told)\b',
}
NAMED = {'model': 'model:under-test', 'host': 'host:under-test', 'date': '2026-10-31', 'window': 'window:test'}


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace('’', "'"))


def runs(text, n=RUN):
    w = words(text)
    return {' '.join(w[i:i + n]) for i in range(len(w) - n + 1)}


def make_run(folder, axes, named=None, ids=None, files=True, flipped=None):
    """A run folder: one transcript per axis and condition, ids opaque, and its key."""
    os.makedirs(folder, exist_ok=True)
    transcripts, n = {}, 0
    for axis in axes:
        for m in measure.MATRIX_STATES:
            for c in measure.CONTEXTS:
                n += 1
                tid = (ids or {}).get((axis, m, c), 'q%03d' % n)
                transcripts[tid] = {'axis': axis, 'matrix': m, 'context': c}
                if files:
                    with open(os.path.join(folder, tid + '.md'), 'w', encoding='utf-8') as f:
                        f.write('person: a short exchange\npersona: an answer\n')
    key = dict(NAMED if named is None else named, transcripts=transcripts)
    if flipped is not None:
        key['flipped'] = flipped
    with open(os.path.join(folder, measure.KEY_NAME), 'w', encoding='utf-8') as f:
        json.dump(key, f)
    return transcripts


def rate(transcripts, values):
    """One rating per transcript, the value looked up by (axis, matrix, context)."""
    out = []
    for tid, e in sorted(transcripts.items()):
        v = values.get((e['axis'], e['matrix'], e['context']))
        if v is not None:
            out.append({'transcript': tid, 'rating': v, 'why': 'one line of why', 'reader': 'agent:reader'})
    return out


class OneScenarioPerAxis(unittest.TestCase):
    """Law 1: one scenario per axis of the companion's matrix, naming its axis and the two tells."""

    def setUp(self):
        self.axes = measure.matrix_axes(_read(COMPANION))
        self.loaded = measure.load_scenarios(SCENARIOS)

    def test_the_matrix_parses_to_its_axes(self):
        self.assertGreaterEqual(len(self.axes), 20)
        self.assertIn('kept', {a['scale'] for a in self.axes})
        self.assertEqual(measure.targets_of(_read(COMPANION))['Pacing'], -35)

    def test_every_numeric_axis_has_exactly_one_scenario_in_the_matrix_order(self):
        self.assertEqual(self.loaded['missing'], [])
        numeric = [a['axis'] for a in self.axes if a['scale'] != 'kept']
        self.assertEqual([s['axis'] for s in self.loaded['scenarios']], numeric)
        names = [s['axis'] for s in json.loads(_read(SCENARIOS))['scenarios']]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(self.loaded['matrix'], COMPANION)

    def test_a_kept_row_is_named_as_not_measured_and_has_no_scenario(self):
        data = json.loads(_read(SCENARIOS))
        kept = [a['axis'] for a in self.axes if a['scale'] == 'kept']
        self.assertTrue(kept)
        for axis in kept:
            self.assertIn(axis, data['not_measured'])
            self.assertNotIn(axis, [s['axis'] for s in data['scenarios']])

    def test_each_scenario_names_its_poles_scale_band_and_two_tells(self):
        by_axis = {a['axis']: a for a in self.axes}
        for s in self.loaded['scenarios']:
            a = by_axis[s['axis']]
            self.assertEqual(s['scale'], a['scale'], s['axis'])
            self.assertEqual(s['pole_minus'], a['pole_minus'], s['axis'])
            self.assertEqual(s['pole_plus'], a['pole_plus'], s['axis'])
            self.assertIn(s['band'], 'ABCDEF', s['axis'])
            for k in ('tell_minus', 'tell_plus'):
                self.assertIsInstance(s[k], str, (s['axis'], k))
                self.assertGreaterEqual(len(s[k].split()), 4, (s['axis'], k))
            self.assertNotEqual(s['tell_minus'], s['tell_plus'])
            self.assertIsInstance(s['exchange'], list)
            self.assertTrue(s['exchange'] and all(isinstance(x, str) and x.strip() for x in s['exchange']))
            self.assertLess(sum(len(x.split()) for x in s['exchange']), 70, s['axis'])  # a short exchange

    def test_no_tell_shares_a_run_of_words_with_either_matrix(self):
        matrix = runs(_read(COMPANION)) | runs(_read(CARRIER))
        for s in self.loaded['scenarios']:
            for k in ('tell_minus', 'tell_plus'):
                self.assertEqual(runs(s[k]) & matrix, set(), (s['axis'], k))

    def test_each_tell_is_its_own_pole_and_carries_no_other_axis_fault(self):
        for s in self.loaded['scenarios']:
            for owner, pattern in FAULTS.items():
                if owner == s['axis']:
                    continue
                for k in ('tell_minus', 'tell_plus'):
                    self.assertIsNone(re.search(pattern, s[k].lower()), (s['axis'], k, owner))

    def test_no_scenario_states_the_limit_its_axis_probes(self):
        by_axis = {s['axis']: s for s in self.loaded['scenarios']}
        pacing = ' '.join(by_axis['Pacing']['exchange']).lower()
        self.assertIsNone(re.search(r'\b(minutes?|hours?|short|brief|quick)\b', pacing))
        recency = ' '.join(by_axis['Recency weighting']['exchange']).lower()
        self.assertIsNone(re.search(r'\b(long|careful|after much)\b', recency))
        for axis in ('Pacing', 'Synthesis tempo', 'Recency weighting'):
            target = next(a['target'] for a in self.axes if a['axis'] == axis)
            lo, hi = measure.SCALES[by_axis[axis]['scale']]
            self.assertTrue(lo < target < hi, axis)                       # the ideal sits between the tells

    def test_the_scenarios_and_readme_keep_the_kit_lint_and_nfc(self):
        for path in (SCENARIOS, README):
            text = _read(path)
            self.assertEqual(unicodedata.normalize('NFC', text), text, path)
            for word in LINT:
                self.assertNotIn(word, text, (path, word))

    def test_the_carrier_matrix_parses_too(self):
        self.assertGreaterEqual(len(measure.matrix_axes(_read(CARRIER))), 20)


class TheFoldIsDeterministicAndHonest(unittest.TestCase):
    """Law 2: ratings fold to a table deterministically; honest-empty; null-guards."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='lionsberg-measure-')
        self.run = os.path.join(self.tmp, 'run')
        self.scen = measure.load_scenarios(SCENARIOS)['scenarios']
        self.axes = [s['axis'] for s in self.scen]
        self.tr = make_run(self.run, self.axes)
        self.key = measure.load_key(self.run)
        self.targets = measure.targets_of(_read(COMPANION))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def values(self):
        return {('Warmth', 'absent', 'fresh'): -20, ('Warmth', 'absent', 'long'): -10,
                ('Warmth', 'loaded', 'fresh'): 40, ('Warmth', 'loaded', 'long'): 20,
                ('Pacing', 'absent', 'fresh'): 60, ('Pacing', 'loaded', 'fresh'): -30}

    def row(self, table, axis):
        return next(a for a in table['axes'] if a['axis'] == axis)

    def test_default_held_signed_delta_drift_and_target(self):
        t = measure.fold(self.key, rate(self.tr, self.values()), self.scen, self.targets)
        self.assertEqual(t['status'], 'measured')
        self.assertEqual(t['measured_on'], NAMED)
        w = self.row(t, 'Warmth')
        self.assertEqual((w['default'], w['held'], w['delta'], w['drift'], w['default_drift']),
                         (-15.0, 30.0, 45.0, -20.0, 10.0))
        self.assertEqual((w['target'], w['to_target']), (30, 0.0))
        self.assertEqual(w['n'], {'absent_fresh': 1, 'absent_long': 1, 'loaded_fresh': 1, 'loaded_long': 1})
        p = self.row(t, 'Pacing')
        self.assertEqual((p['delta'], p['target'], p['to_target']), (-90.0, -35, 5.0))
        self.assertEqual(t['rejected'], [])

    def test_an_axis_with_no_ratings_is_honest_empty(self):
        t = measure.fold(self.key, rate(self.tr, self.values()), self.scen)
        e = self.row(t, 'Honesty floor')
        self.assertEqual([e[k] for k in ('default', 'held', 'delta', 'drift', 'to_target')], [None] * 5)
        self.assertIn('no default yet', e['basis'])
        self.assertIn('No target was given', e['basis'])
        p = self.row(t, 'Pacing')
        self.assertEqual((p['default'], p['held'], p['drift']), (60.0, -30.0, None))
        self.assertIn('no drift yet', p['basis'])

    def test_measured_needs_the_four_names_and_at_least_one_default(self):
        self.assertEqual(measure.fold(self.key, [], self.scen)['status'], 'not a default')
        held_only = rate(self.tr, {('Warmth', 'loaded', 'fresh'): 10})
        t = measure.fold(self.key, held_only, self.scen)
        self.assertEqual(t['status'], 'not a default')
        self.assertIn('nothing is measured yet', t['standing'])
        self.assertEqual(measure.fold(self.key, rate(self.tr, self.values()), [])['status'], 'not a default')

    def test_the_same_ratings_in_any_order_give_the_same_table(self):
        ratings = rate(self.tr, self.values())
        ratings.append(dict(ratings[0], rating=99))                    # a duplicate by one reader
        a = json.dumps(measure.fold(self.key, ratings, self.scen, self.targets), sort_keys=True)
        for seed in range(5):
            shuffled = list(ratings)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(json.dumps(measure.fold(self.key, shuffled, self.scen, self.targets),
                                        sort_keys=True), a)

    def test_two_readers_are_both_counted(self):
        ratings = rate(self.tr, {('Warmth', 'absent', 'fresh'): -20})
        ratings.append(dict(ratings[0], rating=0, reader='agent:second'))
        w = self.row(measure.fold(self.key, ratings, self.scen), 'Warmth')
        self.assertEqual((w['default'], w['n']['absent_fresh']), (-10.0, 2))

    def test_bad_ratings_are_set_aside_with_why(self):
        tid = sorted(self.tr)[0]                                       # Warmth, bipolar
        uni = next(t for t, e in sorted(self.tr.items()) if e['axis'] == 'Calibration')
        bad = [None, {}, [], 'x', 1.5, {'transcript': None}, {'transcript': 1.5, 'rating': 1, 'why': 'w'},
               {'transcript': 'nowhere', 'rating': 0, 'why': 'w'},
               {'transcript': tid, 'rating': float('nan'), 'why': 'w'},
               {'transcript': tid, 'rating': float('inf'), 'why': 'w'},
               {'transcript': tid, 'rating': True, 'why': 'w'},
               {'transcript': tid, 'rating': '10', 'why': 'w'},
               {'transcript': tid, 'rating': 100.5, 'why': 'w'},
               {'transcript': uni, 'rating': -0.5, 'why': 'w'},             # below a unipolar scale
               {'transcript': tid, 'rating': 10},
               {'transcript': tid, 'rating': 10, 'why': 1.5},
               {'transcript': tid, 'rating': 10, 'why': '   '}]
        t = measure.fold(self.key, bad, self.scen)
        self.assertEqual(len(t['rejected']), len(bad))
        self.assertTrue(all(r['why'] for r in t['rejected']))
        self.assertTrue(all(a['default'] is None for a in t['axes']))
        ok = measure.fold(self.key, [{'transcript': tid, 'rating': 12.5, 'why': 'w'}], self.scen)
        self.assertEqual(self.row(ok, 'Warmth')['default'], 12.5)

    def test_a_flipped_axis_is_folded_back_to_its_poles(self):
        run = os.path.join(self.tmp, 'flip')
        tr = make_run(run, ['Warmth', 'Calibration'], flipped=['Warmth', 'Calibration', 1.5])
        key = measure.load_key(run)
        self.assertEqual(key['flipped'], ['Calibration', 'Warmth'])
        rows = {r['transcript']: r for r in measure.sheet(key, self.scen)['rows']}
        by_axis = {s['axis']: s for s in self.scen}
        w = next(t for t, e in tr.items() if e['axis'] == 'Warmth' and e['matrix'] == 'absent')
        self.assertEqual(rows[w]['A'], by_axis['Warmth']['tell_plus'])
        t = measure.fold(key, rate(tr, {('Warmth', 'absent', 'fresh'): 60,
                                        ('Calibration', 'absent', 'fresh'): 20}), self.scen)
        self.assertEqual(self.row(t, 'Warmth')['default'], -60)
        self.assertEqual(self.row(t, 'Calibration')['default'], 80)

    def test_a_non_nfc_id_finds_its_transcript(self):
        run = os.path.join(self.tmp, 'nfc')
        nfc = unicodedata.normalize('NFC', 'té')
        tr = make_run(run, ['Warmth'], ids={('Warmth', 'absent', 'fresh'): nfc})
        nfd = unicodedata.normalize('NFD', nfc)
        t = measure.fold(measure.load_key(run), [{'transcript': nfd, 'rating': 5, 'why': 'w'}], self.scen)
        self.assertIn(nfc, tr)
        self.assertEqual(self.row(t, 'Warmth')['default'], 5.0)

    def test_null_inputs_never_raise(self):
        odd = (None, {}, [], 'x', 1.5, float('nan'), [None], [1.5], {'transcripts': None},
               {'transcripts': []}, {'transcripts': {'a': 'x'}}, {'transcripts': {'a': 1.5}},
               {'named': 1.5}, {'named': {'model': 1.5}}, {'missing': 1.5}, {'flipped': 1.5})
        scens = (None, [], {}, 1.5, [None], [1.5], [{'axis': 'X', 'scale': 'odd'}], [{'axis': 1.5}], self.scen)
        for key in odd:
            for ratings in (None, {}, [], 'x', 1.5, [None], [1.5], [{'transcript': 'a', 'rating': 1, 'why': 'w'}]):
                for scen in scens:
                    for targets in (None, 1.5, {'Warmth': 1.5}, {'Warmth': 'x'}):
                        t = measure.fold(key, ratings, scen, targets)
                        self.assertEqual(t['status'], 'not a default')
                        json.dumps(t, sort_keys=True)
            for scen in scens:
                s = measure.sheet(key, scen)
                self.assertEqual(s['rows'], [])
        for folder in (None, '', os.path.join(self.tmp, 'absent'), 3.5):
            k = measure.load_key(folder)
            self.assertEqual(k['transcripts'], {})
            self.assertTrue(k['missing'])
        for path in (os.path.join(self.tmp, 'none.json'), None, 1.5):
            self.assertEqual(measure.load_scenarios(path)['scenarios'], [])
        for text in (None, 1.5, [], ''):
            self.assertEqual(measure.matrix_axes(text), [])
            self.assertEqual(measure.targets_of(text), {})
        for table in (None, 1.5, {'axes': [{}]}, {'axes': [None, 1.5]}, {'axes': 1.5},
                      {'axes': [{'n': 1.5, 'default': float('nan')}]}, {'measured_on': 1.5}):
            self.assertTrue(measure.render(table))

    def test_a_linked_key_is_not_read(self):
        run = os.path.join(self.tmp, 'linked')
        os.makedirs(run)
        os.symlink(os.path.join(self.run, measure.KEY_NAME), os.path.join(run, measure.KEY_NAME))
        k = measure.load_key(run)
        self.assertEqual(k['transcripts'], {})
        self.assertIn('is a link', k['missing'][0])

    def test_a_missing_transcript_and_a_leaking_id_are_named_by_whole_word(self):
        run = os.path.join(self.tmp, 'gaps')
        make_run(run, ['Warmth'], files=False, ids={('Warmth', 'loaded', 'long'): 'loaded_long1',
                                                    ('Warmth', 'absent', 'long'): 'belong7',
                                                    ('Warmth', 'absent', 'fresh'): 'refreshed2'})
        missing = measure.load_key(run)['missing']
        self.assertIn('The transcript belong7 is not in the folder.', missing)
        leaks = [m for m in missing if 'was not blind' in m]
        self.assertEqual(leaks, ['The id loaded_long1 names its condition, so the reader was not blind to it.'])

    def test_an_id_that_climbs_out_of_the_folder_is_set_aside(self):
        run = os.path.join(self.tmp, 'climb')
        make_run(run, ['Warmth'], files=False, ids={('Warmth', 'absent', 'fresh'): '../../x',
                                                    ('Warmth', 'absent', 'long'): '.hidden'})
        k = measure.load_key(run)
        self.assertNotIn('../../x', k['transcripts'])
        self.assertNotIn('.hidden', k['transcripts'])
        self.assertIn('A key entry without a plain id or a body was set aside.', k['missing'])

    def test_an_axis_with_no_scenario_is_named(self):
        run = os.path.join(self.tmp, 'odd')
        tr = make_run(run, ['Nonsense'])
        key = measure.load_key(run)
        line = 'The key names the axis Nonsense, which has no scenario.'
        self.assertIn(line, measure.sheet(key, self.scen)['missing'])
        t = measure.fold(key, rate(tr, {('Nonsense', 'absent', 'fresh'): 5}), self.scen)
        self.assertIn(line, t['missing'])
        self.assertEqual(t['status'], 'not a default')

    def test_the_sheet_shows_no_axis_no_pole_and_no_condition(self):
        sheet = measure.sheet(self.key, self.scen)
        self.assertEqual(len(sheet['rows']), len(self.tr))
        self.assertEqual(sheet['missing'], [])
        poles = {s[k] for s in self.scen for k in ('pole_minus', 'pole_plus') if s[k] != '—'}
        for row in sheet['rows']:
            self.assertEqual(sorted(row), ['A', 'B', 'scale', 'transcript'])
            text = json.dumps(row, ensure_ascii=False)
            for name in self.axes:
                self.assertNotIn(name, text)
            for pole in poles:
                self.assertNotIn(pole, text)
            for word in ('absent', 'loaded', 'fresh', 'compaction'):
                self.assertNotIn(word, text)
        self.assertEqual(measure.sheet(None, None), {'rows': [], 'missing': []})

    def test_the_cli_folds_to_json_and_markdown(self):
        rp = os.path.join(self.tmp, 'ratings.jsonl')
        with open(rp, 'w', encoding='utf-8') as f:
            for r in rate(self.tr, self.values()):
                f.write(json.dumps(r) + '\n')
        cmd = [sys.executable, '-I', os.path.join(MEASURE, 'measure.py'), self.run, rp]
        t = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
        self.assertEqual(t['status'], 'measured')
        self.assertEqual(self.row(t, 'Warmth')['to_target'], 0.0)
        md = subprocess.run(cmd + ['--markdown'], capture_output=True, text=True, check=True).stdout
        self.assertIn('| Warmth | -15 | +30 | +45 | +30 | +0 | -20 | 4 |', md)
        sh = subprocess.run(cmd[:3] + [self.run, '--sheet'], capture_output=True, text=True, check=True).stdout
        self.assertEqual(len(json.loads(sh)['rows']), len(self.tr))
        none = subprocess.run(cmd + ['--scenarios'], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(none)['status'], 'not a default')
        empty = os.path.join(self.tmp, 'empty.json')
        with open(empty, 'w', encoding='utf-8') as f:
            f.write('[]')
        zero = subprocess.run(cmd[:4] + [empty], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(zero)['status'], 'not a default')
        self.assertEqual(subprocess.run(cmd[:3], capture_output=True, text=True).returncode, 2)


class ANumberWithoutItsRunIsNotADefault(unittest.TestCase):
    """Law 3: the README says what is measured, by whom, and the four things a default belongs to."""

    def test_an_unnamed_run_is_not_a_default(self):
        tmp = tempfile.mkdtemp(prefix='lionsberg-measure-')
        try:
            scen = measure.load_scenarios(SCENARIOS)['scenarios']
            for drop in measure.NAMED:
                named = {k: v for k, v in NAMED.items() if k != drop}
                run = os.path.join(tmp, drop)
                tr = make_run(run, ['Warmth'], named=named)
                t = measure.fold(measure.load_key(run), rate(tr, {('Warmth', 'absent', 'fresh'): 5}), scen)
                self.assertEqual(t['status'], 'not a default', drop)
                self.assertIn('The run does not name its %s.' % drop, t['missing'])
                self.assertIn('is not a default', t['standing'])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_readme_says_the_method_the_reader_and_the_four(self):
        text = _read(README)
        self.assertLess(len(text.splitlines()), README_MAX)
        self.assertIn('**A number without its model, host, date and window is not a default.**', text)
        self.assertIn('**An independent reader**', text)
        self.assertIn('sees only the transcripts', text)
        for part in ('matrix absent', 'matrix loaded', 'fresh start', 'compaction', 'scenarios.json',
                     'one line of why', 'never the key', 'random id',
                     'holds only the scenario\'s exchange and the persona\'s answer',
                     'neutral labels A and B', 'no axis name, no pole name', 'with its sign'):
            self.assertIn(part, text, part)

    def test_each_matrix_status_line_adds_one_sentence_on_how_defaults_are_measured(self):
        base = 'tune it by hand.'
        musts = {COMPANION: 'still estimates until the first run lands',
                 CARRIER: 'has no scenarios for this matrix yet'}
        for path, must in musts.items():
            status = next(l for l in _read(path).splitlines() if l.startswith('**Status: proposal.**'))
            added = status.split(base, 1)[1].strip()
            self.assertTrue(added.endswith('.'), path)
            self.assertIsNone(re.search(r'[.!?]\s', added), path)               # one sentence
            for part in ('`measure/`', 'independent reader', 'model, host, date and window', must):
                self.assertIn(part, added, (path, part))
            self.assertIsNone(re.search(r"n't|it's", status), path)


if __name__ == '__main__':
    unittest.main()
