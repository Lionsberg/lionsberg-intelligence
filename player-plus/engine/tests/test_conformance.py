"""The conformance sheet on the kit's own fixtures: every check that a script can make passes,
and signing reads at the paper floor when no key exists. The sheet is what a new Player's
install runs first; a FAIL there tells them their agent is not ready."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)


class TestConformanceSheet(unittest.TestCase):
    def test_the_fixtures_pass(self):
        with tempfile.TemporaryDirectory() as keys:
            env = dict(os.environ, LIONSBERG_KEY_DIR=keys, HOME=keys)
            env.pop('LIONSBERG_KEY', None)
            out = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'conformance.py')],
                                 capture_output=True, text=True, env=env, timeout=600).stdout
        rows = [l for l in out.splitlines() if l[:3] in ('(a)', '(b)', '(d)', '(e)', '(f)')]
        self.assertEqual(len(rows), 5, out)
        for row in rows:
            self.assertTrue(row.rstrip().endswith('PASS'), row + '\n' + out)
        self.assertIn('5 of 6 pass; signing at the paper floor', out)


    def test_the_known_answer_does_not_age(self):
        """The fixtures are dealt at their own moment, before any date they carry, so the known
        answer holds on every day the sheet is run, not only in the weeks the fixtures were written."""
        import datetime as dt
        import glob
        import json
        with tempfile.TemporaryDirectory() as keys:
            env = dict(os.environ, LIONSBERG_KEY_DIR=keys, HOME=keys)
            env.pop('LIONSBERG_KEY', None)
            out = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'conformance.py'), '--json'],
                                 capture_output=True, text=True, env=env, timeout=600).stdout
        sheet = json.loads(out)
        self.assertTrue(sheet.get('as_of'), 'the sheet names the moment the fixtures were dealt at')
        as_of = dt.datetime.fromisoformat(sheet['as_of'])
        dates = []
        for p in glob.glob(os.path.join(ENGINE, 'fixtures', '**', '*.jsonl'), recursive=True):
            with open(p, encoding='utf-8') as f:
                for line in f:
                    try:
                        by = (json.loads(line).get('body') or {}).get('by')
                    except (ValueError, AttributeError):
                        continue
                    if isinstance(by, str) and len(by) >= 10:
                        dates.append(by[:10])
        self.assertTrue(dates, 'the fixtures carry dates')
        self.assertLess(as_of.date().isoformat(), min(dates), 'dealt before the first date the fixtures carry')
        (a,) = [r for r in sheet['results'] if r['check'] == 'a']
        self.assertEqual(a['status'], 'PASS', a['detail'])


if __name__ == '__main__':
    unittest.main()
