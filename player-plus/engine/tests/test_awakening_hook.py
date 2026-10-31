"""test_awakening_hook.py — the awakening hook's laws, each checked: on the fixtures' home it returns in
under two seconds and under forty lines; it prints the five parts in order (the fifth on a compaction
only); the matrix's corrections are the axes whose delta is at or above the line, read from the matrix
the charter imports and checked here by a second reading in Python; every part is honest-empty; it
never writes; a bad payload, a missing matrix, a symlinked session and a passed deadline do not break
it. And a brief made from the template opens with the awakening.

Temporary agent homes stand for a person's home; the fixtures' holon stands for their record. Nothing
here reaches a network, starts a service or calls a model.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_awakening_hook.py -v
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
HOOK = os.path.join(KIT, '.claude', 'hooks', 'awaken.sh')
FIXTURES = os.path.join(ENGINE, 'fixtures', 'hq')
TEMPLATE = os.path.join(KIT, 'bookshelf', 'with-your-agent', 'A Brief for a Body.md')
OPENING = ('Awaken first: read the desk the hook printed, the matrix\'s corrections, the last resume block, '
           'and say in your first reply which you read. Then:')
COMPACT_LINE = 'a compaction is not an awakening: re-read claude.md and the matrix'
HOLD_AT = 75
SH = shutil.which('sh')

MATRIX = """# A test matrix

*Load canary: MATRIX-TEST-LOADED 2026-10-31.*

## Band A

| Axis | − pole | + pole | Default | Target | Δ | Note |
|---|---|---|---|---|---|---|
| Warmth | cool | warm | −15 | **+25** | 40 | below the line |
| Judgment vs deference | defer | judge | −40 | **+60** | **100** | the largest |
| Pacing | paced to the person | own capacity | +60 | −30 | 90 | toward the minus pole |
| Edge low | low | high | 0 | +74 | 74 | one under the line |
| Edge at | low | high | 0 | +75 | 75 | at the line |

Prose between tables resets the header.

| Axis | − pole | + pole | Default | Target | Δ | Note |
|---|---|---|---|---|---|---|
| Recency weighting *(unipolar)* | — | newest glows brightest | 95 | 15 | 80 | unipolar, held lower |
| Calibration (unipolar) | — | perfectly calibrated | 5 | 90 | 85 | unipolar, held higher |
"""

EXPECTED_HOLDS = [
    'hold: Judgment vs deference toward judge',
    'hold: Pacing toward paced to the person',
    'hold: Calibration toward perfectly calibrated',
    'hold: Recency weighting toward less newest glows brightest',
    'hold: Edge at toward high',
]

CONTRACTION = re.compile(r"\b\w+n['’]t\b|\b(?:I|you|we|they|it|that|there|here|what|let|who)['’]"
                         r"(?:s|re|ll|ve|d|m)\b", re.IGNORECASE)


def run(home, hq=None, payload='{"session_id": "t1", "source": "startup"}', env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith('AWAKEN_')}
    e['CLAUDE_PROJECT_DIR'] = home
    e.update(env or {})
    argv = [SH, HOOK] + ([hq] if hq else [])
    t0 = time.monotonic()
    r = subprocess.run(argv, input=payload.encode('utf-8'), capture_output=True, env=e, timeout=20, cwd=home)
    return r.returncode, r.stdout.decode('utf-8'), time.monotonic() - t0


def snapshot(root):
    out = {}
    for d, dirs, files in os.walk(root):
        for n in dirs + files:
            p = os.path.join(d, n)
            st = os.lstat(p)
            out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns)
    return out


def imported_matrices(home):
    """A second reading of the charter's import chain: each @path that names a matrix, resolved."""
    path = os.path.join(home, 'CLAUDE.md')
    if not os.path.isfile(path):
        return []
    with open(path, encoding='utf-8') as f:
        text = f.read()
    seen = []
    for tok in re.findall(r'@([^\s`()<>"]+)', text):
        if 'atrix' in tok:
            p = os.path.join(home, tok[2:] if tok.startswith('./') else tok)
            if p not in seen:
                seen.append(p)
    return seen


def holds_of(path, at=HOLD_AT):
    """A second reading of a matrix, in Python: the holds the hook should print, largest delta first."""
    def num(s):
        m = re.search(r'[-+]?\d+(?:\.\d+)?', s.replace('−', '-').replace('*', ''))
        return float(m.group(0)) if m else None

    def clean(s):
        s = re.sub(r'\*\([^)]*\)\*', '', s).replace('*', '').strip()
        return s

    rows, header, order = [], None, 0
    with open(path, encoding='utf-8') as f:
        for line in f:
            if not line.lstrip().startswith('|'):
                header = None
                continue
            cells = line.rstrip('\n').split('|')
            if header is None:
                if 'Target' in line and ('Δ' in line or 'elta' in line):
                    header = {}
                    for i, c in enumerate(cells[1:-1], 1):
                        h = clean(c)
                        if re.search(r'\+ *pole', h):
                            header['plus'] = i
                        elif 'pole' in h:
                            header['minus'] = i
                        elif h.startswith('Default'):
                            header['default'] = i
                        elif h.startswith('Target'):
                            header['target'] = i
                        elif 'Δ' in h or h.lower().startswith('delta'):
                            header['delta'] = i
                continue
            if re.match(r'^\s*\|[\s:|-]*$', line):
                continue
            axis = re.sub(r'\s*\([^)]*\)$', '', clean(cells[1]))
            d, t = num(cells[header['default']]), num(cells[header['target']])
            g = num(cells[header['delta']]) if 'delta' in header else None
            if g is None and d is not None and t is not None:
                g = t - d
            if not axis or g is None or d is None or t is None or abs(g) < at or t == d:
                continue
            plus = clean(cells[header['plus']]) if 'plus' in header else ''
            minus = clean(cells[header['minus']]) if 'minus' in header else ''
            if t > d:
                pole = plus or 'more'
            else:
                pole = ('less ' + plus) if minus in ('', '—', '-') else minus
            order += 1
            rows.append((-abs(g), order, 'hold: %s toward %s' % (axis, pole)))
    return [r[2] for r in sorted(rows)]


def make_home(matrix=MATRIX, sessions=None, charter='@personas/Character-Matrix-test.md\n'):
    home = tempfile.mkdtemp(prefix='awaken-home-')
    os.makedirs(os.path.join(home, 'personas'))
    os.makedirs(os.path.join(home, 'sessions'))
    if charter is not None:
        with open(os.path.join(home, 'CLAUDE.md'), 'w', encoding='utf-8') as f:
            f.write('# A charter\n\nThe dispositions held:\n\n' + charter)
    if matrix is not None:
        with open(os.path.join(home, 'personas', 'Character-Matrix-test.md'), 'w', encoding='utf-8') as f:
            f.write(matrix)
    for name, text in (sessions or {}).items():
        with open(os.path.join(home, 'sessions', name), 'w', encoding='utf-8') as f:
            f.write(text)
    return home


@unittest.skipUnless(SH and os.path.isfile(HOOK), 'needs sh and the hook')
class TestAwakeningHook(unittest.TestCase):

    def setUp(self):
        self.homes = []

    def tearDown(self):
        for h in self.homes:
            shutil.rmtree(h, ignore_errors=True)

    def home(self, **kw):
        h = make_home(**kw)
        self.homes.append(h)
        return h

    def test_fixtures_home_fast_short_and_in_order(self):
        rc, out, secs = run(KIT, FIXTURES)
        self.assertEqual(rc, 0)
        self.assertLess(secs, 2.0, out)
        lines = out.splitlines()
        self.assertLess(len(lines), 40, out)
        heads = [lines.index(x) for x in lines if re.match(r'^[1-5]\. ', x)]
        self.assertEqual([lines[i][:2] for i in heads], ['1.', '2.', '3.', '4.'], out)
        self.assertNotIn(COMPACT_LINE, out.lower())
        self.assertIn('first-cell', out)                     # the three answers over the fixtures' holon
        self.assertIn('One desk, one watcher', out)
        self.assertRegex(out, r'(?m)^  (The desk is free,|Desk held by|This home keeps no desk lease)')

    def test_compaction_adds_the_fifth_line_only_then(self):
        rc, out, secs = run(KIT, FIXTURES, payload='{"session_id": "t1", "source": "compact"}')
        self.assertEqual(rc, 0)
        self.assertLess(secs, 2.0)
        last = out.splitlines()[-1]
        self.assertTrue(last.startswith('5. '), out)
        self.assertIn(COMPACT_LINE, last.lower())
        self.assertIn('AWAKENING (compact)', out)
        for src in ('resume', 'clear'):
            _rc, o, _s = run(KIT, FIXTURES, payload='{"source": "%s"}' % src)
            self.assertNotIn(COMPACT_LINE, o.lower())

    def test_kit_matrix_corrections_match_a_second_reading(self):
        rc, out, _ = run(KIT, FIXTURES)
        self.assertEqual(rc, 0)
        part = out.split('4. ', 1)[1]
        got = [x.strip() for x in part.splitlines() if x.strip().startswith('hold: ')]
        mats = [m for m in imported_matrices(KIT) if os.path.isfile(m)]
        if not mats:
            self.assertIn('the matrix did not load', part.lower())
            self.assertEqual(got, [])
            return
        want = []
        for m in mats:
            want += holds_of(m)[:7]
        self.assertEqual(got, want, out)
        self.assertTrue(got, 'the kit matrix holds at least one axis at or above the line')

    def test_synthetic_home_resume_handoff_and_holds(self):
        sessions = {
            '2026-10-30-001-older.md': '# Older\n\n## RESUME HERE\n\nthe older step, never shown\n',
            '2026-10-31-002-newer.md': ('# Newer\n\nWhat happened.\n\n## RESUME HERE\n\n- the exact next step\n'
                                        '- and its second line\n\n## After\n\nnot part of the block\n'),
        }
        h = self.home(sessions=sessions)
        os.makedirs(os.path.join(h, 'bg', 'long-job'))
        with open(os.path.join(h, 'bg', 'long-job', 'handoff.md'), 'w', encoding='utf-8') as f:
            f.write('# The long job is done\n\nDetail.\n')
        open(os.path.join(h, 'bg', 'long-job', 'DONE'), 'w').close()
        os.makedirs(os.path.join(h, 'bg', 'still-going'))
        with open(os.path.join(h, 'bg', 'still-going', 'task.md'), 'w', encoding='utf-8') as f:
            f.write('a task\n')
        rc, out, secs = run(h, FIXTURES)
        self.assertEqual(rc, 0)
        self.assertLess(secs, 2.0)
        self.assertIn('From sessions/2026-10-31-002-newer.md:', out)
        self.assertIn('- the exact next step', out)
        self.assertIn('- and its second line', out)
        self.assertNotIn('not part of the block', out)
        self.assertNotIn('the older step', out)
        self.assertIn('bg/long-job/: The long job is done', out)
        self.assertIn('at least this body is live, with 0 guest folder(s) and 1 background job(s) still open', out)
        got = [x.strip() for x in out.split('4. ', 1)[1].splitlines() if x.strip().startswith('hold: ')]
        self.assertEqual(got, EXPECTED_HOLDS)
        self.assertEqual(holds_of(os.path.join(h, 'personas', 'Character-Matrix-test.md')), EXPECTED_HOLDS)
        self.assertNotIn('carries no load canary', out)

    def test_inline_resume_line(self):
        h = self.home(sessions={'2026-10-31-001-x.md': 'Notes.\n\n**RESUME HERE:** open the pad and read it.\n'})
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('**RESUME HERE:** open the pad and read it.', out)

    def test_hold_line_is_overridable(self):
        h = self.home()
        _rc, out, _ = run(h, FIXTURES, env={'AWAKEN_HOLD_AT': '95'})
        got = [x.strip() for x in out.split('4. ', 1)[1].splitlines() if x.strip().startswith('hold: ')]
        self.assertEqual(got, ['hold: Judgment vs deference toward judge'])
        _rc, out, _ = run(h, FIXTURES, env={'AWAKEN_HOLD_AT': '101'})
        self.assertIn('no axis holds a delta of 101 or more', out)

    def test_honest_empty_everywhere(self):
        h = tempfile.mkdtemp(prefix='awaken-empty-')
        self.homes.append(h)
        rc, out, secs = run(h)
        self.assertEqual(rc, 0)
        self.assertLess(secs, 2.0)
        self.assertIn('not a holon yet', out)
        self.assertIn('This home keeps no desk lease', out)
        self.assertIn('Another body left: nothing left.', out)
        self.assertIn('No session yet.', out)
        self.assertIn('the matrix did not load', out.lower())
        self.assertIn('the bodies cannot be counted; at least this body is live', out)
        self.assertNotRegex(out, r'\b0 (Claude|bod)')

    def test_matrix_missing_unimported_or_without_canary(self):
        h = self.home(matrix=None)
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('The matrix did not load: personas/Character-Matrix-test.md is not there.', out)
        h = self.home(charter='No import here.\n')
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('The matrix did not load: CLAUDE.md imports no character matrix.', out)
        h = self.home(matrix=MATRIX.replace('MATRIX-TEST-LOADED', 'no canary'))
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('carries no load canary', out)
        h = self.home(matrix='# A matrix with no table\n\nMATRIX-LOADED 2026-10-31\n')
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('no axis holds a delta of 75 or more', out)

    def test_bad_payloads_and_symlinks(self):
        h = self.home(sessions={'2026-10-30-001-real.md': '## RESUME HERE\n\nthe real step\n'})
        other = tempfile.mkdtemp(prefix='awaken-other-')
        self.homes.append(other)
        with open(os.path.join(other, 'x.md'), 'w', encoding='utf-8') as f:
            f.write('## RESUME HERE\n\na linked step\n')
        os.symlink(os.path.join(other, 'x.md'), os.path.join(h, 'sessions', '2026-10-31-009-link.md'))
        for p in ('', 'not json at all', '{"source": "compact"', '{"source": 7}', '\x00\x01'):
            rc, out, _ = run(h, FIXTURES, payload=p)
            self.assertEqual(rc, 0, p)
            self.assertIn('2. ', out)
            self.assertIn('the real step', out)
            self.assertNotIn('a linked step', out)
        lh = tempfile.mkdtemp(prefix='awaken-linkhq-')
        self.homes.append(lh)
        os.symlink(os.path.join(FIXTURES, 'holon.json'), os.path.join(lh, 'holon.json'))
        _rc, out, _ = run(h, lh)
        self.assertIn('holon.json is a link, so it was not read', out)

    def test_a_broken_holon_and_a_linked_matrix_are_said_as_such(self):
        h = self.home()
        with open(os.path.join(h, 'holon.json'), 'w', encoding='utf-8') as f:
            f.write('{"keeper": "person:player", ')
        _rc, out, _ = run(h)
        self.assertIn("holon.json is broken", out)
        self.assertNotIn('not a holon yet', out)
        m = os.path.join(h, 'personas', 'Character-Matrix-test.md')
        real = os.path.join(h, 'personas', 'elsewhere.md')
        os.rename(m, real)
        os.symlink(real, m)
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('personas/Character-Matrix-test.md is a link, so it was not read', out)
        self.assertNotIn('hold: ', out)

    def test_the_headquarters_path_comes_from_the_charter(self):
        h = self.home(charter='The *work* lives in the user\'s **headquarters** at `%s`: their projects.\n' % FIXTURES)
        _rc, out, _ = run(h)
        self.assertIn('first-cell', out)
        h = self.home(charter='The *work* lives in the user\'s **headquarters** at `{{HQ_PATH}}`: their projects.\n')
        _rc, out, _ = run(h)
        self.assertIn('not a holon yet', out)

    def test_the_body_count_is_the_skill_count_and_never_zero(self):
        h = self.home()
        os.makedirs(os.path.join(h, 'scripts'))
        shutil.copy(os.path.join(KIT, 'scripts', 'desk'), os.path.join(h, 'scripts', 'desk'))
        os.makedirs(os.path.join(h, 'bg', 'guest-20261031T090000Z'))
        os.makedirs(os.path.join(h, 'bg', 'guest-20261031T080000Z'))
        with open(os.path.join(h, 'bg', 'guest-20261031T080000Z', 'handoff.md'), 'w', encoding='utf-8') as f:
            f.write('handed back\n')
        _rc, out, _ = run(h, FIXTURES)
        self.assertIn('Bodies live in this home: 2 (the desk holder or this body, 1 guest(s)', out)
        self.assertNotIn('Claude Code session', out)

    def test_the_cap_keeps_the_last_line_for_the_compaction(self):
        many = ''.join('@personas/Character-Matrix-m%d.md\n' % i for i in range(6))
        h = self.home(charter=many, sessions={'2026-10-31-001-x.md': '## RESUME HERE\n\n' +
                                               ''.join('- step %d\n' % i for i in range(20))})
        for i in range(6):
            with open(os.path.join(h, 'personas', 'Character-Matrix-m%d.md' % i), 'w', encoding='utf-8') as f:
                f.write(MATRIX)
        os.makedirs(os.path.join(h, 'bg'))
        for i in range(5):
            os.makedirs(os.path.join(h, 'bg', 'job-%d' % i))
            open(os.path.join(h, 'bg', 'job-%d' % i, 'DONE'), 'w').close()
        _rc, out, _ = run(h, FIXTURES, payload='{"source": "compact"}')
        lines = out.splitlines()
        self.assertLessEqual(len(lines), 39, out)
        self.assertTrue(lines[-1].startswith('5. '), lines[-1])
        self.assertIn(COMPACT_LINE, lines[-1].lower())
        _rc, out, _ = run(h, FIXTURES)
        self.assertLessEqual(len(out.splitlines()), 38)

    def test_a_passed_deadline_is_said(self):
        rc, out, _ = run(KIT, FIXTURES, env={'AWAKEN_DEADLINE': '0.001'})
        self.assertEqual(rc, 0)
        self.assertIn('could not be read in time', out)
        self.assertIn('4. ', out)

    def test_never_writes(self):
        h = self.home(sessions={'2026-10-31-001-x.md': '## RESUME HERE\n\nstep\n'})
        before_home, before_hq = snapshot(h), snapshot(FIXTURES)
        for src in ('startup', 'compact'):
            run(h, FIXTURES, payload='{"source": "%s"}' % src)
        self.assertEqual(snapshot(h), before_home)
        self.assertEqual(snapshot(FIXTURES), before_hq)

    @unittest.skipUnless(shutil.which('ssh-keygen'), 'needs ssh-keygen to check signatures')
    def test_a_cold_signature_cache_is_never_saved(self):
        hq = tempfile.mkdtemp(prefix='awaken-cold-')
        self.homes.append(hq)
        shutil.copytree(FIXTURES, os.path.join(hq, 'hq'))
        hq = os.path.join(hq, 'hq')
        if os.path.exists(os.path.join(hq, '.sigcache')):
            os.remove(os.path.join(hq, '.sigcache'))
        key = os.path.join(os.path.dirname(hq), 'sigcache.key')
        fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='ascii') as f:
            f.write(os.urandom(32).hex())
        env = {'LIONSBERG_SIGCACHE_KEY': key, 'AWAKEN_DEADLINE': '15'}
        _rc, out, _ = run(KIT, hq, env=env)
        self.assertIn('first-cell', out)                       # the reading finished, so a save would have run
        self.assertFalse(os.path.exists(os.path.join(hq, '.sigcache')), 'the hook saved the signature cache')

    def test_a_missing_cache_secret_is_never_made(self):
        d = tempfile.mkdtemp(prefix='awaken-secret-')
        self.homes.append(d)
        key = os.path.join(d, 'no', 'sigcache.key')
        _rc, out, _ = run(KIT, FIXTURES, env={'LIONSBERG_SIGCACHE_KEY': key, 'AWAKEN_DEADLINE': '15'})
        self.assertIn('first-cell', out)
        self.assertFalse(os.path.exists(os.path.dirname(key)), 'the hook made the cache secret')

    def test_no_contractions_and_no_quoted_words_in_the_hook(self):
        with open(HOOK, encoding='utf-8') as f:
            text = f.read()
        self.assertIsNone(CONTRACTION.search(text), CONTRACTION.search(text) and CONTRACTION.search(text).group(0))
        _rc, out, _ = run(KIT, FIXTURES, payload='{"source": "compact"}')
        own = [x for x in out.splitlines() if not x.startswith('  ') or x.startswith('  One desk')]
        for line in own:
            self.assertIsNone(CONTRACTION.search(line), line)


class TestTheBriefTemplate(unittest.TestCase):

    def template_block(self):
        with open(TEMPLATE, encoding='utf-8') as f:
            text = f.read()
        m = re.search(r'```text\n(.*?)```', text, re.S)
        self.assertIsNotNone(m, 'the template block is fenced as text')
        return text, m.group(1)

    def test_a_brief_made_from_the_template_opens_with_the_awakening(self):
        _text, block = self.template_block()
        task = 'Draft the venue list for the cell; done when the steward has it; write only bg/venues/.'
        brief = re.sub(r'<the task:[^>]*>', task, block)
        self.assertTrue(brief.startswith(OPENING), brief[:200])
        self.assertEqual(brief.splitlines()[0], OPENING)
        self.assertIn(task, brief)
        self.assertLess(brief.index(OPENING), brief.index(task))

    def test_the_page_says_the_proof_and_keeps_the_laws(self):
        text, _block = self.template_block()
        self.assertIn('a body that cannot say what it read has not awakened', text.lower())
        self.assertIsNone(CONTRACTION.search(text), CONTRACTION.search(text) and CONTRACTION.search(text).group(0))
        self.assertNotRegex(text, r'\b(?:house|HQ|estate|promise)\b')


if __name__ == '__main__':
    unittest.main()
