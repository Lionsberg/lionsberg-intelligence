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


if __name__ == '__main__':
    unittest.main()
