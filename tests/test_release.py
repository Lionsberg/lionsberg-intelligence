"""test_release.py — what holds Player+ 4.1 together.

Run from the top of the repository:

    python3 -I -m unittest discover -s tests -v

It checks what a script can: the starter kit is carried unchanged; the Player+ block is whole between
its markers and sits where the build puts it, with every other line of the charter the starter kit's
own; the skills fit the room a host gives their descriptions; nothing in the kit names the game engine
by a path, or a house an earlier kit built; the Cards read; the reviewed shelf holds the reviewed
words; the one sentence is the same wherever a person meets it; and a house built by the scripted
build is whole. Whether a person can follow the pages is a walk, not this test.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import zipfile

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKAI = os.path.join(TOP, 'pkai-starter-kit')
PLUS = os.path.join(TOP, 'player-plus-kit')
sys.path.insert(0, os.path.join(TOP, 'tools'))
import build_house  # noqa: E402

BEGIN, END, ANCHOR = build_house.BEGIN, build_house.END, build_house.ANCHOR
SKILLS16 = ['a-gathering', 'entering-the-field', 'join-a-cell', 'pass-the-flame', 'play-by-play', 'pull-a-release',
            'read-the-story-aloud', 'refresh-the-library', 'safe-sparring', 'the-offering', 'the-retrospective', 'the-roll',
            'the-season-sheet-by-hand', 'the-simplest-game', 'the-turn', 'witness-a-commitment']
REVIEWED = {'01 The Hour.md': '9dd86140d043ddeb', '02 The Call.md': '9f7b1f602b2e3aae', '03 The Doorway.md': 'a5d2b5feb10179a4',
            '04 The Story.md': '6c9a9ade50e2036c', '05 The Game.md': '4418ede0613f25e8', '06 The Flame.md': '406ac0f55ddf7765',
            '07 The Inheritance.md': '6984abd4e3e283be'}
CONTRACTION = re.compile(r"\b\w+(n't|'re|'ll|'ve|'d|'m)\b|\b(it|that|there|here|what|who|let)'s\b", re.I)
# The room a host gives a house's skill descriptions: about 24,000 characters (measured with Claude Code 2.1.317).
BUDGET = 23000


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def files(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != '.git']
        out += [os.path.relpath(os.path.join(dp, f), root) for f in fn if f != '.DS_Store']
    return sorted(out)


def description(skill_md):
    text = read(skill_md)
    head = text[:text.index('\n---', 4) + 1]
    m = re.search(r'^description:(.*?)(?=^[A-Za-z][\w-]*:|\Z)', head, re.S | re.M)
    d = ' '.join(m.group(1).split()) if m else ''
    return d[1:-1].replace('\\"', '"') if d.startswith('"') and d.endswith('"') else d


def sentence(text):
    m = re.search(r'```text\n(Please download [^\n]+)\n```', text)
    return m.group(1) if m else ''


class TheStarterKitIsCarriedUnchanged(unittest.TestCase):
    def test_every_file_is_the_keepers(self):
        want = {}
        for line in read(os.path.join(TOP, 'tests', 'pkai-starter-kit.sha256')).splitlines():
            digest, name = line.split(None, 1)
            want[name.strip()] = digest
        have = {f: sha(os.path.join(PKAI, f)) for f in files(PKAI)}
        self.assertEqual(sorted(have), sorted(want), 'a file was added to or taken from pkai-starter-kit/')
        changed = [f for f in want if have[f] != want[f]]
        self.assertEqual(changed, [], 'a line of the starter kit was changed')

    def test_its_version_is_the_one_named(self):
        version = read(os.path.join(PKAI, 'VERSION.md')).split()[-1].lstrip('v')
        for page in ('RELEASE.md', 'CHANGES.md', 'LINEAGE.md'):
            self.assertIn(version, read(os.path.join(PLUS, page)), page)


class ThePlayerPlusBlock(unittest.TestCase):
    def setUp(self):
        self.block = read(os.path.join(PLUS, 'PLAYER-PLUS-BLOCK.md'))

    def test_it_is_whole_between_its_markers(self):
        text = self.block.strip('\n')
        self.assertTrue(text.startswith(BEGIN))
        self.assertTrue(text.endswith(END))
        self.assertEqual(self.block.count(BEGIN), 1)
        self.assertEqual(self.block.count(END), 1)
        self.assertIn(read(os.path.join(PLUS, 'VERSION.md')).split()[-1].lstrip('v').split('-')[0], text.split('\n')[0])

    def test_its_size(self):
        words = len(self.block.split())
        self.assertTrue(900 <= words <= 1500, 'the block is about 1,200 words; it holds %d' % words)

    def test_it_holds_what_an_agent_must_hold(self):
        for must in ('## The Game you play', 'The Goal and the compass', 'Who you serve', 'The Field of Agreements', 'The words',
                     'The Cards', 'Whose act each Card is', 'Where to find more', 'The guard', 'PLAYER-PLUS.md',
                     '{{HQ_PATH}}/cards/', '{{HQ_PATH}}/library/lionsberg/'):
            self.assertIn(must, self.block, must)
        self.assertEqual(set(re.findall(r'\{\{(\w+)\}\}', self.block)), {'HQ_PATH'})

    def test_in_every_persona_it_sits_above_the_anchor_and_changes_nothing_else(self):
        for persona in ('chief-of-staff', 'companion', 'archivist'):
            hq = '/Users/ada/Documents/ada-hq'
            plain = build_house.persona_as_charter(TOP, persona, hq)
            block = build_house.block(TOP, hq)
            charter = build_house.with_block(plain, block)
            a, b = charter.index(BEGIN), charter.index(END) + len(END)
            self.assertEqual(charter[a:b], block, persona)
            self.assertTrue(charter[b:].startswith('\n\n' + ANCHOR + '\n'), persona)
            without = charter[:a].rstrip('\n') + '\n\n' + charter[b:].lstrip('\n')
            self.assertEqual(without, plain, 'outside the block, the charter is the starter kit\'s persona: ' + persona)
            self.assertNotIn('{{', charter)

    def test_it_is_not_added_twice(self):
        hq = '/h'
        once = build_house.with_block(build_house.persona_as_charter(TOP, 'chief-of-staff', hq), build_house.block(TOP, hq))
        with self.assertRaises(SystemExit):
            build_house.with_block(once, build_house.block(TOP, hq))


class TheSkills(unittest.TestCase):
    def test_the_sixteen(self):
        have = sorted(d for d in os.listdir(os.path.join(PLUS, 'skills')) if os.path.isdir(os.path.join(PLUS, 'skills', d)))
        self.assertEqual(have, SKILLS16)
        listed = re.search(r'## The sixteen skills\n\n(.*?)\n\n', read(os.path.join(PLUS, 'RELEASE.md')), re.S).group(1)
        self.assertEqual(sorted(re.findall(r'`([a-z-]+)`', listed)), SKILLS16)

    def test_each_travels_whole(self):
        for s in SKILLS16:
            for f in ('SKILL.md', 'LINEAGE.md', 'LICENSE.md'):
                self.assertTrue(os.path.isfile(os.path.join(PLUS, 'skills', s, f)), '%s/%s' % (s, f))
            head = read(os.path.join(PLUS, 'skills', s, 'SKILL.md')).split('\n---', 1)[0]
            self.assertIn('name: %s' % s, head)
            self.assertIn('license: MPL-2.0', head, s)
            self.assertIn('grows_from: player-plus-kit 4.1', read(os.path.join(PLUS, 'skills', s, 'LINEAGE.md')), s)

    def test_every_description_reaches_the_model(self):
        total = 0
        for s in sorted(os.listdir(os.path.join(PKAI, 'skills'))):
            p = os.path.join(PKAI, 'skills', s, 'SKILL.md')
            if os.path.isfile(p):
                total += len('- %s: %s' % (s, description(p)))
        for s in SKILLS16:
            d = description(os.path.join(PLUS, 'skills', s, 'SKILL.md'))
            self.assertTrue(d, '%s has no description' % s)
            self.assertLessEqual(len(d), 300, '%s: a description is under 300 characters' % s)
            self.assertNotIn(': ', d, '%s: a description holds no colon followed by a space' % s)
            total += len('- %s: %s' % (s, d))
        self.assertLessEqual(total, BUDGET, 'every skill of both kits, installed at once, fits the listing')

    def test_a_skill_names_only_skills_a_house_has(self):
        known = set(SKILLS16) | {d for d in os.listdir(os.path.join(PKAI, 'skills')) if os.path.isdir(os.path.join(PKAI, 'skills', d))}
        gone = {'the-deal', 'the-record', 'the-chief-of-staff', 'the-heartbeat', 'the-proxy', 'a-mail-watch', 'voice-mode',
                'say-it-on-the-card', 'receive', 'sight', 'subscribe', 'agree', 'connections', 'negotiate', 'pull'}
        for s in SKILLS16:
            text = read(os.path.join(PLUS, 'skills', s, 'SKILL.md'))
            for name in re.findall(r'`([a-z]+(?:-[a-z]+)+)`', text):
                self.assertNotIn(name, gone - known, '%s names `%s`, which this house does not have' % (s, name))


# What a 4.1 house does not hold. A page of the kit names none of these.
NOT_HERE = [
    (r'\bengine/', 'an engine path'), (r'\bhud/', 'a board path'), (r'\b[a-z_]+\.py\b', 'a Python file'),
    (r'\bpython3?\b', 'python'), (r'holon\.json|types\.json|launch\.json', 'an engine file'),
    (r'room-post|pad-write|refresh-library|awaken\.sh|what-waits', 'a script this release holds out'),
    (r'\.claude/hooks', 'hooks of an earlier kit'), (r'~/HQ\b|HQ/Library|HQ/engine|HQ/hud', 'the house of an earlier kit'),
    (r'Character-Matrix|character matrix', 'the character matrix'), (r'LAYERS\.md|INSTALL\.md|MOVING-(IN|THE)', 'a page of an earlier kit'),
    (r'\bbookshelf/', 'a bookshelf path of an earlier kit'), (r'read\.lionsberg|play\.lionsberg', 'a site that is closed'),
]
# The few places that name one on purpose.
ALLOWED = {
    ('BUILD.md', r'~/HQ\b|HQ/Library|HQ/engine|HQ/hud'),          # how the builder knows an earlier house
    ('CHANGES.md', r'Character-Matrix|character matrix'),          # said once, as held for a later release
}


class NothingNamesWhatTheHouseDoesNotHold(unittest.TestCase):
    def test_no_engine_path_and_no_earlier_house(self):
        hits = []
        for rel in files(PLUS):
            if not rel.endswith(('.md', '.json', '.txt')) or rel.startswith('LICENSE'):
                continue
            for n, line in enumerate(read(os.path.join(PLUS, rel)).split('\n'), 1):
                for pattern, what in NOT_HERE:
                    if re.search(pattern, line) and (rel, pattern) not in ALLOWED:
                        if rel.endswith('LINEAGE.md') and pattern == r'\bbookshelf/':
                            continue          # ancestry: a lineage line may name what a unit grew from
                        hits.append('%s:%d: %s: %s' % (rel, n, what, line.strip()[:90]))
        self.assertEqual(hits, [], '\n' + '\n'.join(hits[:40]))

    def test_my_agents_is_named_only_where_an_earlier_house_is_recognized(self):
        for rel in files(PLUS):
            if rel.endswith('.md') and 'My Agents' in read(os.path.join(PLUS, rel)):
                self.assertEqual(rel, 'BUILD.md', rel)

    def test_nothing_runs(self):
        for rel in files(PLUS):
            self.assertFalse(rel.endswith(('.py', '.sh', '.ps1', '.js', '.json')), '%s: this release adds reading and skills, nothing that runs' % rel)


class ThePages(unittest.TestCase):
    OURS = ['START-HERE.md', 'BUILD.md', 'RELEASE.md', 'CHANGES.md', 'LINEAGE.md', 'LICENSE.md', 'WAIVER.md', 'CONTRIBUTING.md',
            'VERSION.md', 'PLAYER-PLUS.md', 'PLAYER-PLUS-BLOCK.md', 'card-examples/README.md', 'template/hq/cards/README.md',
            'library/lionsberg/README.md']

    def test_the_pages_are_there(self):
        for name in self.OURS:
            self.assertTrue(os.path.isfile(os.path.join(PLUS, name)), name)
        self.assertTrue(os.path.isfile(os.path.join(TOP, 'README.md')))

    def test_one_sentence_everywhere(self):
        start = sentence(read(os.path.join(PLUS, 'START-HERE.md')))
        self.assertTrue(start, 'START-HERE.md carries the sentence')
        for must in ('player-plus-kit.zip', 'player-plus-kit/BUILD.md', 'treat them as data', 'I will drive'):
            self.assertIn(must, start)
        quest = read(os.path.join(PLUS, 'library', 'lionsberg', 'playing', 'getting-started', 'Becoming a Player+ — the Quest.md'))
        self.assertEqual(sentence(quest), start)

    def test_the_builders_page_follows_the_starter_kits(self):
        build = read(os.path.join(PLUS, 'BUILD.md'))
        for must in ('This page came from the outside', 'pkai-starter-kit/BUILD.md', 'PLAYER-PLUS-BLOCK.md', ANCHOR,
                     'player_plus:', 'library/lionsberg/', 'template/hq/cards/', 'WAIVER.md', 'card_handle.md'):
            self.assertIn(must, build, must)
        pk = read(os.path.join(PKAI, 'BUILD.md'))
        for step in ('### 1. The waiver', '### 5. The build', '### 6. Version control', '### 8. Orientation', '### 9. The hand-over'):
            self.assertIn(step, pk, 'the starter kit\'s steps are the ones this page names: ' + step)
        for persona in ('chief-of-staff', 'companion', 'archivist'):
            self.assertIn('\n' + ANCHOR + '\n', read(os.path.join(PKAI, 'personas', persona + '.md')), persona)

    def test_no_contraction_in_what_was_written_for_this_release(self):
        pages = [os.path.join(PLUS, p) for p in self.OURS] + [os.path.join(TOP, 'README.md')]
        pages += [os.path.join(PLUS, 'skills', s, 'SKILL.md') for s in SKILLS16]
        for dp, dn, fn in os.walk(os.path.join(PLUS, 'card-examples')):
            pages += [os.path.join(dp, f) for f in fn]
        for p in pages:
            for n, line in enumerate(read(p).split('\n'), 1):
                self.assertIsNone(CONTRACTION.search(line), '%s:%d: %s' % (os.path.relpath(p, TOP), n, line.strip()[:80]))

    def test_commitments_not_promises(self):
        for p in [os.path.join(PLUS, x) for x in self.OURS] + [os.path.join(PLUS, 'skills', s, 'SKILL.md') for s in SKILLS16]:
            self.assertIsNone(re.search(r'\bpromis', read(p), re.I), os.path.relpath(p, TOP))


CARD_NEEDS = {
    'card': ['title'], 'commit': ['card', 'by'], 'done': ['card'], 'kept': ['commitment'], 'release': [], 'request': ['to', 'title'],
    'offer': ['title'], 'answer': ['answer'], 'sight': ['text'], 'condition': ['color', 'why'], 'agree': ['with'], 'say': ['text'],
    'witness': [], 'correct': ['why'], 'join': ['who', 'cell'], 'turn': ['span'],
}
CARD_LINKS = {'answer': 'answers', 'witness': 'witnesses', 'correct': 'supersedes'}
TOP_FIELDS = ['type', 'actor', 'for', 'ts', 'body', 'links']
NAME = re.compile(r'^(\d{4}-\d{2}-\d{2})-([a-z0-9]+)-([a-z]+)-([a-z0-9-]+)\.md$')


def read_card(path):
    """A Card as the guide gives its form: {'type', 'actor', 'for', 'ts', 'body': {}, 'links': {}} and the rest of the page."""
    text = read(path)
    if not text.startswith('---\n'):
        raise ValueError('no front matter')
    end = text.index('\n---', 4)
    card, where = {'body': {}, 'links': {}}, None
    for line in text[4:end].split('\n'):
        if not line.strip():
            continue
        if line.startswith('  '):
            key, value = line.strip().split(':', 1)
            card[where][key.strip()] = value.strip()
        else:
            key, value = line.split(':', 1)
            key = key.strip()
            if key not in TOP_FIELDS:
                raise ValueError('a Card carries only its six fields at the top; %r is not one' % key)
            if key in ('body', 'links'):
                where = key
            else:
                card[key], where = value.strip(), None
    return card, text[end + 4:]


class TheCards(unittest.TestCase):
    def setUp(self):
        self.dir = os.path.join(PLUS, 'card-examples')
        self.cards = sorted(f for f in os.listdir(self.dir) if f != 'README.md')

    def test_one_example_of_each_kind(self):
        kinds = {NAME.match(f).group(3) for f in self.cards}
        self.assertEqual(kinds, set(CARD_NEEDS))

    def test_each_reads_and_carries_what_its_kind_needs(self):
        for f in self.cards:
            m = NAME.match(f)
            self.assertTrue(m, '%s: a Card is named YYYY-MM-DD-<handle>-<type>-<a-few-words>.md' % f)
            card, rest = read_card(os.path.join(self.dir, f))
            self.assertEqual(card['type'], m.group(3), f)
            self.assertRegex(card['actor'], r'^(person|agent):[a-z0-9]+$', f)
            self.assertRegex(card['for'], r'^person:[a-z0-9]+$', f)
            self.assertEqual(card['actor'].split(':')[1], m.group(2), '%s: the name carries the handle of the one whose Card it is' % f)
            self.assertRegex(card['ts'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', f)
            self.assertTrue(card['ts'].startswith(m.group(1)), f)
            for field in CARD_NEEDS[card['type']]:
                self.assertTrue(card['body'].get(field), '%s: a %s needs %s' % (f, card['type'], field))
            if card['type'] in CARD_LINKS:
                self.assertIn(CARD_LINKS[card['type']], card['links'], f)
            if card['type'] == 'release':
                self.assertTrue(card['body'].get('commitment') or card['body'].get('card'), f)
            self.assertTrue(rest.lstrip('\n').startswith('# %s · ' % card['type']), '%s: the title line' % f)

    def test_the_guide_and_the_examples_name_the_same_kinds(self):
        guide = read(os.path.join(PLUS, 'PLAYER-PLUS.md'))
        for kind in CARD_NEEDS:
            self.assertIn('| `%s` |' % kind, guide, kind)
        listed = re.findall(r'^\| `([^`]+\.md)` \|', read(os.path.join(self.dir, 'README.md')), re.M)
        self.assertEqual(sorted(listed), self.cards)

    def test_an_agents_card_answers_for_its_person(self):
        agents = [f for f in self.cards if read_card(os.path.join(self.dir, f))[0]['actor'].startswith('agent:')]
        self.assertTrue(agents, 'one example is written by an agent in its own name')


class TheBookshelf(unittest.TestCase):
    SHELF = os.path.join(PLUS, 'library', 'lionsberg')

    def test_the_reviewed_shelf_holds_the_reviewed_words(self):
        have = sorted(os.listdir(os.path.join(self.SHELF, 'reviewed')))
        self.assertEqual(have, sorted(REVIEWED))
        for name, digest in REVIEWED.items():
            text = read(os.path.join(self.SHELF, 'reviewed', name))
            title, body = text.split('\n\n', 1)
            self.assertEqual(title, '# ' + name[3:-3])
            self.assertEqual(hashlib.sha256(body.rstrip('\n').encode('utf-8')).hexdigest()[:16], digest, '%s was changed' % name)

    def test_every_playing_page_says_how_to_weigh_it(self):
        n = 0
        for rel in files(os.path.join(self.SHELF, 'playing')):
            if rel.endswith('.md'):
                head = read(os.path.join(self.SHELF, 'playing', rel)).split('\n---', 1)[0]
                self.assertIn('library-status: current best understanding, not yet reviewed line by line', head, rel)
                n += 1
        self.assertGreaterEqual(n, 30)


class AHouseBuiltByTheScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.home = os.path.join(cls.tmp, 'home')
        os.makedirs(cls.home)
        out = build_house.build(TOP, cls.home, 'ada-hq', 'Ada', 'ada', 'River', 'the Ada house', 'chief-of-staff', date='2026-11-10')
        cls.agent, cls.hq = out['agent_home'], out['hq']

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_two_folders_side_by_side(self):
        self.assertEqual(os.path.basename(self.agent), 'River (agent)')
        self.assertEqual(os.path.dirname(self.agent), self.home)
        self.assertFalse(os.path.exists(os.path.join(self.hq, 'CLAUDE.md')), 'the HQ holds no CLAUDE.md')

    def test_the_charter(self):
        charter = read(os.path.join(self.agent, 'CLAUDE.md'))
        self.assertEqual(charter.count(BEGIN), 1)
        self.assertEqual(charter.count(END), 1)
        self.assertLess(charter.index(BEGIN), charter.index(END))
        self.assertLess(charter.index(END), charter.index('\n' + ANCHOR))
        self.assertLess(charter.index('\n## Who you are'), charter.index(BEGIN))
        self.assertIn(self.hq + '/cards/', charter)

    def test_no_placeholder_is_left(self):
        for rel in files(self.agent):
            if rel.endswith('.md'):
                self.assertNotIn('{{', read(os.path.join(self.agent, rel)), rel)

    def test_what_the_agent_home_holds(self):
        for rel in ('CLAUDE.md', 'PLAYER-PLUS.md', 'LINEAGE.md', 'README.md', 'venues.md', '.gitignore', '.claude/settings.json',
                    'memory/MEMORY.md', 'memory/agent_name.md', 'memory/user_name.md', 'memory/waiver_agreed.md', 'memory/origin.md',
                    'memory/card_handle.md', 'scripts/now', 'scripts/desk'):
            self.assertTrue(os.path.isfile(os.path.join(self.agent, rel)), rel)
        self.assertEqual(read(os.path.join(self.agent, '.claude', 'settings.json')),
                         read(os.path.join(PKAI, 'template', 'agent-home', 'dot-claude', 'settings.json')), 'the settings are the starter kit\'s own')
        self.assertEqual(sorted(os.listdir(os.path.join(self.agent, 'scripts'))),
                         sorted(os.listdir(os.path.join(PKAI, 'template', 'agent-home', 'scripts'))), 'no script is added')
        skills = sorted(os.listdir(os.path.join(self.agent, '.claude', 'skills')))
        self.assertEqual(skills, sorted(build_house.PKAI_INSTALLED + SKILLS16))
        lineage = read(os.path.join(self.agent, 'LINEAGE.md'))
        self.assertIn('player_plus:', lineage)
        self.assertLess(lineage.index('player-plus-kit v'), lineage.index('pkai-starter-kit v4'))

    def test_what_the_hq_holds(self):
        for rel in ('projects/README.md', 'cards/README.md', 'library/README.md', 'library/pkai/README.md', 'library/lionsberg/README.md',
                    'pkai-starter-kit/BUILD.md', 'player-plus-kit/BUILD.md', 'player-plus-kit/card-examples/README.md'):
            self.assertTrue(os.path.isfile(os.path.join(self.hq, rel)), rel)
        self.assertEqual(len(os.listdir(os.path.join(self.hq, 'library', 'lionsberg', 'reviewed'))), 7)
        self.assertFalse(os.path.exists(os.path.join(self.hq, 'player-plus-kit', 'library')), 'one library, in one place')
        self.assertFalse(os.path.exists(os.path.join(self.hq, 'pkai-starter-kit', 'library')))

    def test_every_link_on_the_bookshelf_leads_somewhere(self):
        dead = []
        for root in (os.path.join(self.hq, 'library', 'lionsberg'), os.path.join(self.hq, 'cards')):
            for rel in files(root):
                if not rel.endswith('.md'):
                    continue
                here = os.path.dirname(os.path.join(root, rel))
                for m in re.finditer(r'\]\(([^)]+)\)', read(os.path.join(root, rel))):
                    u = m.group(1).split('#')[0].strip('<>')
                    if not u or re.match(r'https?:|mailto:', u):
                        continue
                    if not os.path.exists(os.path.normpath(os.path.join(here, urllib.parse.unquote(u)))):
                        dead.append('%s -> %s' % (rel, u))
        self.assertEqual(dead, [], '\n' + '\n'.join(dead[:30]))

    def test_the_guide_names_paths_that_exist(self):
        for name in ('PLAYER-PLUS.md', 'CLAUDE.md'):
            text = read(os.path.join(self.agent, name))
            for path in set(re.findall(r'`(%s/[^`<>*]+)`' % re.escape(self.hq), text)):
                if path.rstrip('/').endswith(('cells', 'pkai-starter-kit/.gitignore')) or '/cells/' in path:
                    continue          # a Cell's clone arrives when a Cell is joined
                self.assertTrue(os.path.exists(path.rstrip('/')), '%s names %s' % (name, path))


class TheDownload(unittest.TestCase):
    """The two folders as one zip: it unzips with the tools a new computer has, and no path is long enough to break Windows."""

    def test_paths_are_short(self):
        longest = max((len(os.path.join(k, f)), os.path.join(k, f)) for k in ('pkai-starter-kit', 'player-plus-kit') for f in files(os.path.join(TOP, k)))
        # C:\Users\<twenty characters>\Documents\<twenty>-hq\ is about 55; the limit is 260.
        self.assertLessEqual(longest[0], 160, longest[1])

    @unittest.skipUnless(shutil.which('unzip') and shutil.which('tar'), 'needs unzip and tar')
    def test_it_unzips(self):
        tmp = tempfile.mkdtemp()
        try:
            z = os.path.join(tmp, 'player-plus-kit.zip')
            names = []
            with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
                for k in ('pkai-starter-kit', 'player-plus-kit'):
                    for f in files(os.path.join(TOP, k)):
                        zf.write(os.path.join(TOP, k, f), os.path.join(k, f))
                        names.append(os.path.join(k, f))
            for tool, cmd in (('unzip', ['unzip', '-q', z]), ('tar', ['tar', '-xf', z])):
                out = os.path.join(tmp, tool)
                os.makedirs(out)
                r = subprocess.run(cmd, cwd=out, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, '%s: %s' % (tool, r.stderr[:300]))
                import unicodedata
                got = sorted(unicodedata.normalize('NFC', f) for f in files(out))
                self.assertEqual(got, sorted(unicodedata.normalize('NFC', n) for n in names), tool)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
