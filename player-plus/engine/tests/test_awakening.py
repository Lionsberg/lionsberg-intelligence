"""test_awakening.py — the character matrices load with the charter.

The charter (`CLAUDE.md`) imports its persona's character matrix by an `@path` line. The host
resolves such a line relative to the file that holds it, stops the path at the first space, skips
code spans and fenced blocks, and follows imports a few hops deep. This module resolves the chain
the same way and checks that each matrix's load canary is on it, that every imported path exists
and has no spaces, and that each matrix keeps its own form. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_awakening.py -v
"""
import os
import re
import shutil
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.dirname(ENGINE)
CHARTER = os.path.join(HOME, 'CLAUDE.md')
PERSONAS = os.path.join(HOME, 'personas')
README = os.path.join(PERSONAS, 'README-from-the-kit.md')

# The host follows imports this many hops from the charter (its documented recursion limit).
MAX_HOPS = 5
# The persona matrices, the import line that loads each, and the canary each carries.
MATRICES = {
    'companion': ('personas/Character-Matrix-companion.md', 'MATRIX-COMPANION-LOADED'),
    'carrier': ('personas/Character-Matrix-carrier.md', 'MATRIX-CARRIER-LOADED'),
}
# The kit's lint for words on these pages: no contraction, the older word, no honorific, no vendor name.
LINT = ("n't", "I'd", "I'll", "you'd", "it's", "we'll", "you'll", "I'm", "you're",
        "prom" + "ise", "S" + "ir", "Cla" + "ude")
# A matrix stays one page an agent reads at every start.
MAX_LINES = 110
# The matrix's own threshold for a large correction, named in its closing section.
LARGE_DELTA = 75

IMPORT_RE = re.compile(r'(?:^|(?<=\s))@(\S+)')


def _read(path):
    """The text of a file, or None when it is missing, a folder, or unreadable."""
    try:
        if not path or not os.path.isfile(path):
            return None
        with open(path, encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def imports_in(text):
    """The raw `@` import tokens in a text, as the host reads them: outside fenced blocks and code spans."""
    if not isinstance(text, str):
        return []
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        bare = re.sub(r'`[^`]*`', '', line)
        out.extend(IMPORT_RE.findall(bare))
    return out


def resolve_chain(path, text=None, hops=MAX_HOPS):
    """Follow the imports from one file. Returns {'loaded': [abs paths in load order], 'missing': [tokens]}.

    `text` stands in for the file's own text (to resolve a charter with one line changed); every
    imported path resolves relative to the folder of the file that holds it, `~` to the home folder.
    A cycle loads each file once; beyond `hops` nothing more loads.
    """
    loaded, missing = [], []

    def walk(p, body, depth):
        loaded.append(os.path.realpath(p))
        if depth >= hops:
            return
        for tok in imports_in(body):
            target = os.path.expanduser(tok) if tok.startswith('~') else os.path.join(os.path.dirname(p), tok)
            real = os.path.realpath(target)
            if real in loaded:
                continue
            nxt = _read(target)
            if nxt is None:
                missing.append(tok)
                continue
            walk(target, nxt, depth + 1)

    body = _read(path) if text is None else text
    if body is None:
        return {'loaded': [], 'missing': [path]}
    walk(path, body, 0)
    return {'loaded': loaded, 'missing': missing}


def chain_text(chain):
    return '\n'.join(_read(p) or '' for p in chain['loaded'])


def _num(cell):
    s = cell.replace('*', '').replace('−', '-').replace('+', '').strip()
    try:
        return int(s)
    except ValueError:
        return None


def matrix_rows(text):
    """Each axis row of a matrix as (axis, default, target, delta), numbers or None."""
    rows = []
    for line in (text or '').splitlines():
        cells = [c.strip() for c in line.strip().split('|')]
        if len(cells) != 9 or cells[1] in ('Axis', '') or set(cells[1]) <= set('-'):
            continue
        rows.append((cells[1], _num(cells[4]), _num(cells[5]), _num(cells[6])))
    return rows


class TheCharterLoadsItsMatrix(unittest.TestCase):

    def test_the_charter_imports_the_companion_matrix_and_its_canary_loads(self):
        rel, canary = MATRICES['companion']
        self.assertIn(rel, imports_in(_read(CHARTER)))
        chain = resolve_chain(CHARTER)
        self.assertEqual(chain['missing'], [])
        self.assertIn(os.path.realpath(os.path.join(HOME, rel)), chain['loaded'])
        self.assertIn(canary, chain_text(chain))
        self.assertNotIn(MATRICES['carrier'][1], chain_text(chain))     # one persona's matrix, never both

    def test_the_carrier_loads_by_the_one_line_the_readme_names(self):
        readme = _read(README)
        self.assertIsNotNone(readme)
        comp, carr = '@' + MATRICES['companion'][0], '@' + MATRICES['carrier'][0]
        self.assertIn(comp, readme)
        self.assertIn(carr, readme)
        charter = _read(CHARTER)
        self.assertEqual(charter.count(comp), 1)
        chain = resolve_chain(CHARTER, text=charter.replace(comp, carr))
        self.assertEqual(chain['missing'], [])
        self.assertIn(MATRICES['carrier'][1], chain_text(chain))
        self.assertNotIn(MATRICES['companion'][1], chain_text(chain))

    def test_every_import_on_the_chain_exists_and_has_no_spaces(self):
        for path in resolve_chain(CHARTER)['loaded']:
            for line in (_read(path) or '').splitlines():
                if imports_in(line) and line.strip().startswith('@'):
                    self.assertNotIn(' ', line.strip(), line)            # the host stops a path at a space
            for tok in imports_in(_read(path)):
                self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(path), tok)), tok)
        for rel, _ in MATRICES.values():
            self.assertNotIn(' ', rel)
            self.assertTrue(os.path.isfile(os.path.join(HOME, rel)), rel)

    def test_each_canary_lives_in_its_own_matrix_once(self):
        for name, (rel, canary) in MATRICES.items():
            own = _read(os.path.join(HOME, rel))
            self.assertEqual(own.count(canary), 1, name)
            for other, (orel, ocanary) in MATRICES.items():
                if other != name:
                    self.assertNotIn(ocanary, own)


class EachMatrixKeepsItsForm(unittest.TestCase):

    def test_each_matrix_is_one_short_page_and_says_its_targets_are_proposals(self):
        for name, (rel, _) in MATRICES.items():
            text = _read(os.path.join(HOME, rel))
            self.assertLess(len(text.splitlines()), MAX_LINES, name)
            self.assertIn('**Status: proposal.**', text)
            for part in ('## The root', '## The precedence layer', '## What the matrix already tells'):
                self.assertIn(part, text, name)
            self.assertGreaterEqual(text.count('## Band '), 6, name)

    def test_every_delta_is_the_gap_and_the_large_ones_are_named(self):
        for name, (rel, _) in MATRICES.items():
            text = _read(os.path.join(HOME, rel))
            rows = matrix_rows(text)
            self.assertGreaterEqual(len(rows), 20, name)
            large = set()
            for axis, default, target, delta in rows:
                if target is None:
                    continue                                              # a kept row (its target is a word)
                self.assertIsNotNone(default, (name, axis))
                self.assertIsNotNone(delta, (name, axis))                 # a numeric target always shows its gap
                self.assertEqual(delta, abs(target - default), (name, axis))
                if delta >= LARGE_DELTA:
                    large.add(axis)
            closing = text.split('## What the matrix already tells', 1)[1]
            named = set(re.findall(r'^- (.+?) \(Δ \d+\)$', closing, re.M))
            self.assertEqual(named, large, name)

    def test_the_kit_lint_holds_on_every_matrix(self):
        for name, (rel, _) in MATRICES.items():
            text = _read(os.path.join(HOME, rel))
            for word in LINT:
                self.assertNotIn(word, text, (name, word))
            for holon_word in (' house', ' HQ', ' estate'):
                self.assertNotIn(holon_word, text, (name, holon_word))


class TheResolverIsHonest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='awakening-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _w(self, rel, body):
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(body)
        return p

    def test_nothing_in_nothing_out(self):
        for bad in (None, '', {}, [], 3.5):
            self.assertEqual(imports_in(bad), [])
        self.assertEqual(resolve_chain(os.path.join(self.tmp, 'absent.md')),
                         {'loaded': [], 'missing': [os.path.join(self.tmp, 'absent.md')]})
        self.assertEqual(matrix_rows(None), [])

    def test_a_spaced_path_a_code_span_a_fence_and_a_mail_address_load_nothing(self):
        self._w('a b.md', 'SPACED')
        self._w('x.md', 'X')
        top = self._w('top.md', '@a b.md\n`@x.md`\n```\n@x.md\n```\nwrite to me@x.md\n')
        chain = resolve_chain(top)
        self.assertEqual(chain['loaded'], [os.path.realpath(top)])
        self.assertEqual(chain['missing'], ['a'])

    def test_relative_to_the_holder_a_cycle_once_and_a_depth_limit(self):
        self._w('sub/b.md', '@c.md\n@../top.md\n')
        self._w('sub/c.md', 'CANARY-C')
        top = self._w('top.md', '@sub/b.md\n')
        chain = resolve_chain(top)
        self.assertEqual(len(chain['loaded']), 3)
        self.assertIn('CANARY-C', chain_text(chain))
        self.assertNotIn('CANARY-C', chain_text(resolve_chain(top, hops=1)))

    def test_a_symlinked_matrix_still_loads_once(self):
        real = self._w('real.md', 'CANARY-R')
        try:
            os.symlink(real, os.path.join(self.tmp, 'link.md'))
        except (OSError, NotImplementedError):
            self.skipTest('no symlinks here')
        top = self._w('top.md', '@link.md\n@real.md\n')
        chain = resolve_chain(top)
        self.assertEqual(chain_text(chain).count('CANARY-R'), 1)


if __name__ == '__main__':
    unittest.main()
