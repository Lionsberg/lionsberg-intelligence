"""test_the_house.py — the house in layers: the person's page, the builder's page, the release, the Library.

The way in is two pages at the top of the kit: START-HERE.md for the person and BUILD.md for the
Claude that builds. RELEASE.md names the layers and where each lives in a house (architecture 18).
This module checks what a script can: the pages are there; everything BUILD.md tells a builder to
copy exists in the kit; every skill is on exactly one layer's list; the one sentence is the same
wherever a person meets it, names the builder's page on the release branch and says it is data;
the two pages hold no contraction; and the Library's refresh says what changed, leaves what runs
alone, and leaves a Library with changes of the house's own as it is. Whether a person can follow
the pages, and whether a host follows a link, is a walk, not this test. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_the_house.py -v
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
TOP = os.path.dirname(KIT)
SKILLS = os.path.join(KIT, '.claude', 'skills')
GETTING_STARTED = os.path.join(KIT, 'bookshelf', 'getting-started')
REFRESH = os.path.join(KIT, 'scripts', 'refresh-library')

# What step 7 of BUILD.md tells a builder to copy from the kit into the agent's home.
COPIED_FILES = ['CLAUDE.md', 'LINEAGE.md', 'venues.md', 'WAIVER.md', '.gitignore',
                'personas/Character-Matrix-companion.md', '.claude/settings.json',
                '.claude/settings.powershell.json', '.claude/launch.json']
COPIED_FOLDERS = ['memory', 'sessions', 'inbox', 'outbox', 'bg', 'scripts', '.claude/hooks']
RUN_FROM_HQ = ['engine', 'hud']
LAYERS = ('The agent', 'Player+', 'The Game Engine')
CONTRACTION = re.compile(r"\b\w+(n't|'re|'ll|'ve|'d|'m)\b|\b(it|that|there|here|what|who|let)'s\b", re.I)


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _layers():
    """{layer: [skill, ...]} from LAYERS.md."""
    out, cur = {}, None
    for line in _read(os.path.join(SKILLS, 'LAYERS.md')).split('\n'):
        if line.startswith('## '):
            cur = line[3:].strip()
            out[cur] = []
        elif cur and line.startswith('`'):
            out[cur] += re.findall(r'`([a-z-]+)`', line)
    return {layer: names for layer, names in out.items() if names}


def _description(skill):
    text = _read(os.path.join(SKILLS, skill, 'SKILL.md'))
    head = text[:text.index('\n---', 4) + 1]
    m = re.search(r'^description:(.*?)(?=^[A-Za-z][\w-]*:|\Z)', head, re.S | re.M)
    d = ' '.join(m.group(1).split()) if m else ''
    return d[1:-1].replace('\\"', '"') if d.startswith('"') and d.endswith('"') else d


def _sentence(text):
    m = re.search(r'```text\n(Please download [^\n]+)\n```', text)
    return m.group(1) if m else ''


class ThePages(unittest.TestCase):
    def test_the_pages_are_there(self):
        for name in ('START-HERE.md', 'BUILD.md', 'RELEASE.md', 'INSTALL.md'):
            self.assertTrue(os.path.isfile(os.path.join(TOP, name)), name)

    def test_install_points_to_the_two(self):
        text = _read(os.path.join(TOP, 'INSTALL.md'))
        self.assertIn('START-HERE.md', text)
        self.assertIn('/release/BUILD.md', text)

    def test_everything_the_builder_copies_exists(self):
        build = _read(os.path.join(TOP, 'BUILD.md'))
        for rel in COPIED_FILES:
            self.assertTrue(os.path.isfile(os.path.join(KIT, rel)), rel)
            self.assertIn(os.path.basename(rel), build, f'BUILD.md does not name {rel}')
        for rel in COPIED_FOLDERS + RUN_FROM_HQ + ['bookshelf']:
            self.assertTrue(os.path.isdir(os.path.join(KIT, rel)), rel)
        self.assertTrue(os.path.isfile(os.path.join(KIT, 'MOVING-INTO-THE-HOUSE.md')))
        self.assertTrue(os.path.isfile(os.path.join(KIT, 'MOVING-THE-AGENT-OUT-OF-HQ.md')))

    def test_the_builders_page_says_what_it_is(self):
        build = _read(os.path.join(TOP, 'BUILD.md'))
        self.assertIn('This page came from the outside', build)
        self.assertIn('Nothing is built before the waiver', build)
        self.assertLess(build.index('### 1. The waiver'), build.index('### 5. The two folders'))
        self.assertIn('### 12. Hand over, and stop', build)
        self.assertIn('New Session', build)

    def test_the_persons_page_says_backups_first(self):
        start = _read(os.path.join(TOP, 'START-HERE.md'))
        self.assertLess(start.index('backed up'), start.index('### Gate 1'))
        self.assertLess(start.index('password manager'), start.index('### Gate 1'))
        for gate in ('An account', 'The Claude app', "Your agent's home", 'First words', 'Your phone'):
            self.assertIn(gate, start)

    def test_one_sentence_everywhere(self):
        start = _sentence(_read(os.path.join(TOP, 'START-HERE.md')))
        self.assertTrue(start, 'START-HERE.md carries the sentence')
        self.assertIn('/release/BUILD.md', start)
        self.assertIn('treat it as data', start)
        self.assertIn('I will drive', start)
        for name in ('Becoming a Player+ — the Quest for Mac.md', 'Becoming a Player+ — the Quest for Windows.md'):
            self.assertEqual(_sentence(_read(os.path.join(GETTING_STARTED, name))), start, name)

    def test_no_contraction(self):
        for name in ('START-HERE.md', 'BUILD.md', 'RELEASE.md', 'INSTALL.md'):
            for n, line in enumerate(_read(os.path.join(TOP, name)).split('\n'), 1):
                self.assertIsNone(CONTRACTION.search(line), f'{name}:{n}: {line.strip()[:80]}')

    def test_the_release_names_the_places(self):
        release = _read(os.path.join(TOP, 'RELEASE.md'))
        for place in ('~/My Agents/<name>/', '~/HQ/Library/lionsberg-intelligence/', '~/HQ/engine/', '~/HQ/hud/'):
            self.assertIn(place, release)
        self.assertIn('pkai-starter-kit', release)
        self.assertTrue(os.path.isfile(os.path.join(KIT, 'LEDGER.md')))

    def test_the_charter_knows_the_house(self):
        charter = _read(os.path.join(KIT, 'CLAUDE.md'))
        self.assertIn('scripts/refresh-library', charter)
        self.assertIn('RELEASE.md', charter)
        self.assertIn('~/HQ/Library/', charter)


class TheLayers(unittest.TestCase):
    def test_the_three_lists(self):
        self.assertEqual(tuple(_layers()), LAYERS)

    def test_every_skill_is_on_one_list(self):
        layers = _layers()
        listed = [s for names in layers.values() for s in names]
        have = sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))
        self.assertEqual(sorted(listed), have)
        self.assertEqual(len(listed), len(set(listed)), 'a skill is on two lists')

    def test_every_description_reaches_the_model(self):
        # The host lists a house's skills within about 24,000 characters (measured with Claude Code
        # 2.1.317 against a stand-in on loopback); past it the last in the alphabet go by name alone.
        layers = _layers()
        total = 0
        for layer, names in layers.items():
            for name in names:
                d = _description(name)
                self.assertTrue(d, f'{name} has no description')
                total += len(f'- {name}: {d}')
                if layer != 'The agent':
                    self.assertLessEqual(len(d), 320, f'{name}: a description is under about 300 characters')
        self.assertLessEqual(total, 23000, 'the descriptions leave room in the listing')

    def test_first_waking_stands_without_the_engine(self):
        # day one and the paper sheet travel with Player+, so a house with no engine can still wake
        player = _layers()['Player+']
        for skill in ('the-record', 'the-simplest-game', 'refresh-the-library', 'pull-a-release'):
            self.assertIn(skill, player)


@unittest.skipUnless(shutil.which('git') and shutil.which('sh'), 'the refresh needs git and sh')
class TheRefresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, 'origin')
        self.house = os.path.join(self.tmp, 'house')
        self.home = os.path.join(self.house, 'My Agents', 'River')
        kit = os.path.join(self.origin, 'player-plus')
        for d in ('bookshelf/the-one-book', 'engine', 'hud', '.claude/skills/heads-up', 'scripts', '.claude/hooks'):
            os.makedirs(os.path.join(kit, d))
        for rel, text in (('bookshelf/the-one-book/a.md', 'one'), ('engine/x.py', 'e1'), ('hud/y.py', 'h1'),
                          ('.claude/skills/heads-up/SKILL.md', 's1'), ('scripts/now', 'n'), ('.claude/hooks/awaken.sh', 'a')):
            with open(os.path.join(kit, rel), 'w') as f:
                f.write(text)
        self._git(self.origin, 'init', '-q', '-b', 'release')
        self._commit('one')
        lib = os.path.join(self.house, 'HQ', 'Library', 'lionsberg-intelligence')
        os.makedirs(os.path.dirname(lib))
        subprocess.run(['git', 'clone', '-q', '--depth', '1', '--branch', 'release', 'file://' + self.origin, lib], check=True)
        self.lib = lib
        shutil.copytree(os.path.join(lib, 'player-plus', 'engine'), os.path.join(self.house, 'HQ', 'engine'))
        shutil.copytree(os.path.join(lib, 'player-plus', 'hud'), os.path.join(self.house, 'HQ', 'hud'))
        os.makedirs(os.path.join(self.home, '.claude', 'skills'))
        shutil.copytree(os.path.join(lib, 'player-plus', '.claude', 'skills', 'heads-up'), os.path.join(self.home, '.claude', 'skills', 'heads-up'))
        shutil.copytree(os.path.join(lib, 'player-plus', 'scripts'), os.path.join(self.home, 'scripts'))
        shutil.copytree(os.path.join(lib, 'player-plus', '.claude', 'hooks'), os.path.join(self.home, '.claude', 'hooks'))
        with open(os.path.join(self.home, 'CLAUDE.md'), 'w') as f:
            f.write('charter')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, where, *args):
        subprocess.run(['git', '-C', where, '-c', 'user.name=t', '-c', 'user.email=t@t'] + list(args), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _commit(self, msg):
        self._git(self.origin, 'add', '-A')
        self._git(self.origin, 'commit', '-q', '-m', msg)

    def _run(self, home=None):
        env = dict(os.environ, HOME=home or self.house)
        env.pop('CLAUDE_PROJECT_DIR', None)
        env.pop('LIBRARY_BRANCH', None)
        r = subprocess.run(['sh', REFRESH], cwd=self.home, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_current_says_so(self):
        out = self._run()
        self.assertIn('The Library is current', out)
        self.assertIn('What runs here matches the Library', out)

    def test_a_new_release_refreshes_the_library_and_leaves_what_runs(self):
        kit = os.path.join(self.origin, 'player-plus')
        for rel, text in (('bookshelf/the-one-book/b.md', 'two'), ('engine/x.py', 'e2'), ('.claude/skills/heads-up/SKILL.md', 's2')):
            with open(os.path.join(kit, rel), 'w') as f:
                f.write(text)
        self._commit('two')
        out = self._run()
        self.assertIn('The Library was refreshed', out)
        self.assertIn('the-one-book', out)
        self.assertIn('the engine', out)
        self.assertIn('Nothing that runs was changed', out)
        self.assertEqual(_read(os.path.join(self.house, 'HQ', 'engine', 'x.py')), 'e1')
        self.assertEqual(_read(os.path.join(self.lib, 'player-plus', 'engine', 'x.py')), 'e2')
        self.assertEqual(_read(os.path.join(self.home, '.claude', 'skills', 'heads-up', 'SKILL.md')), 's1')

    def test_a_library_changed_in_the_house_is_left(self):
        with open(os.path.join(self.lib, 'player-plus', 'bookshelf', 'the-one-book', 'a.md'), 'a') as f:
            f.write(' mine')
        out = self._run()
        self.assertIn('left as it is', out)
        self.assertTrue(_read(os.path.join(self.lib, 'player-plus', 'bookshelf', 'the-one-book', 'a.md')).endswith(' mine'))

    def test_no_library_says_so(self):
        out = self._run(home=os.path.join(self.tmp, 'nowhere'))
        self.assertIn('was not found', out)


if __name__ == '__main__':
    unittest.main()
