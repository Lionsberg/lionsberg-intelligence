"""test_way_in.py — the way in: START-HERE, MOVING-IN, Your First Hour, and the Quest's Gate 5.

These pages are read cold by a person with no training, and they leave this home for anyone's.
This module checks what a script can: every path, command and skill the pages name exists in the
kit; each page stays under its line cap; no person's name and no contraction; the host is named at
most once on a page, and where it is, as the first host, with "your agent in its host" said on every
page; the kit's words (no older word for a home, no word the kit retired); no line that cages the
agent's own judgment, and no line that states its speech as fact; no timed undo promised in the
conversation (the read-back is the undo there; the board's held act is the one timed undo); the
commands the pages name run; every anchor and every Part of the seed text named is there; and the
doors other pages point to are still there. Whether an untrained
reader can follow the pages is the cold reader's test, not this one. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_way_in.py -v
"""
import os
import re
import subprocess
import sys
import unittest
import unicodedata
from urllib.parse import unquote

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
GETTING_STARTED = os.path.join(KIT, 'bookshelf', 'getting-started')
QUEST = os.path.join(GETTING_STARTED, 'Becoming a Player+ — the Quest.md')

# Each page and the line count it stays under (the brief's caps; the Quest page is checked only
# in the part this brief writes, its Gate 5 and first waking).
PAGES = {
    'START-HERE.md': (os.path.join(KIT, 'START-HERE.md'), 70),
    'MOVING-IN.md': (os.path.join(KIT, 'MOVING-IN.md'), 60),
    'Your First Hour.md': (os.path.join(GETTING_STARTED, 'Your First Hour.md'), 80),
}
QUEST_PART = ('## Gate 5', '> [!tip]')   # the Quest page's own part, from this heading to this line

# Paths a page names that live in the reader's own home once it is in use, not in the kit.
MADE_IN_USE = {'memory/agreements.md', '.claude/skills/'}
# Files of the starter kit a credit names; they live in that kit, not in this one.
UPSTREAM = {'MOVING-FROM-V2.md'}
# Bare names a page gives inside a sentence that already says where they live.
BARE = {'SOURCES.md': 'bookshelf/the-great-game/SOURCES.md'}
# The top folders of the kit; a code span starting with one of these names a path.
TOP = ('skills/', 'engine/', 'hud/', 'bookshelf/', 'memory/', '.claude/', 'scripts/', 'player-plus/')
EXT = ('.md', '.py', '.sh', '.json')

# The host's name, assembled so this file does not itself carry it.
HOST = 'Cla' + 'ude'
IN_ITS_HOST = 'your agent in its host'

# Names of persons that must not appear on these pages (lineage, the first holons, the old examples).
NAMES = ('Ada', 'Ana', 'Pete', 'Peter', 'Kaminski', 'Jordan', 'Sukut', 'Freya',
         'AURELLI' + 'ØN', 'S' + 'ir')
CONTRACTION = re.compile(
    r"\b\w+[’'](?:t|re|ve|ll|m|d)\b|\b(?:it|that|here|there|what|let|who|where|he|she)[’']s\b", re.I)
# The kit's words: no older word for a home or a holon, no retired word.
OLD_WORDS = re.compile(r'\b(?:HQ|house|houses|estate|prom' + r'ise|prom' + r'ises)\b', re.I)
# Lines that would cage the agent's own judgment or speech (the keeper's correction, 2026-10-31).
CAGES = ('asks only', 'speaks only', 'never recites', 'nothing is explained before',
         'only when asked', 'the agent never', 'your agent never', 'the agent always',
         'your agent always')

# A licence or credit line names its author by law (MPL-2.0 keeps the notice); such a line is
# exempt from the name check, and only such a line.
LICENCE_LINE = re.compile(r'MPL-2\.0|©|^licence:', re.M)
# Speech stated as fact, where the pages say how a first hour tends to go.
STATED_SPEECH = ('says at once', 'it asks one thing', 'it deals you', 'then it deals')
# The commands the pages name, each run from the kit as a reader's agent would run it.
COMMANDS = (
    ('engine/level.py', ['simplest'], 'The simplest Game'),
    ('engine/holon.py', ['init', '--help'], '--adopt'),
    ('engine/plain.py', ['--help'], 'actor'),
)
SEED = os.path.join(KIT, 'bookshelf', 'the-dna-of-heaven', 'THE DNA OF HEAVEN.md')

CODE = re.compile(r'`([^`]+)`')
LINK = re.compile(r'\]\((<[^>]+>|[^)\s]+)\)')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return unicodedata.normalize('NFC', f.read())


def _quest_part():
    text = _read(QUEST)
    start = text.find(QUEST_PART[0])
    end = text.find(QUEST_PART[1], start if start >= 0 else 0)
    return text[start:end] if start >= 0 and end > start else ''


def _texts():
    """(label, folder its links resolve from, text) for every page this brief writes."""
    out = [(label, os.path.dirname(path), _read(path)) for label, (path, _cap) in PAGES.items()]
    out.append(('the Quest, Gate 5', GETTING_STARTED, _quest_part()))
    return out


def _prose(text):
    """The words a reader reads: code spans and link targets taken out."""
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    text = CODE.sub(' ', text)
    text = LINK.sub('] ', text)
    return re.sub(r'https?://\S+', ' ', text)


def _slug(heading):
    """A heading's anchor, as the forge and the library make it."""
    h = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return h.replace(' ', '-')


def _span_path(span):
    """The path a code span names, or None when it names none."""
    s = span.strip()
    if s.startswith('python3'):
        toks = [t for t in s.split() if not t.startswith('-') and t != 'python3']
        return toks[0] if toks else None
    if s in BARE:
        return BARE[s]
    if s.endswith(EXT) or s.endswith('/'):
        return s if (s.startswith(TOP) or '/' not in s or s.endswith(EXT)) else None
    first = s.split()[0]
    if first.endswith(EXT) and first.startswith(TOP):
        return first
    if s.startswith(TOP) and ' ' not in s:
        return s
    return None


class TestPagesExist(unittest.TestCase):
    def test_every_page_is_there(self):
        for label, (path, _cap) in PAGES.items():
            self.assertTrue(os.path.isfile(path), label)
        self.assertTrue(_quest_part(), "the Quest page has its Gate 5 and first waking")
        self.assertIn('## The first waking', _quest_part())


class TestPathsAndCommands(unittest.TestCase):
    def test_every_code_path_exists(self):
        for label, _folder, text in _texts():
            for span in CODE.findall(text):
                p = _span_path(span)
                if p is None or p in MADE_IN_USE or p in UPSTREAM or '<' in p:
                    continue
                if p.startswith('player-plus/'):
                    p = p[len('player-plus/'):]
                full = os.path.join(KIT, p)
                self.assertTrue(os.path.exists(full), f'{label}: `{span}` names {p}, which is not in the kit')

    def test_every_link_resolves(self):
        for label, folder, text in _texts():
            for target in LINK.findall(text):
                t = target[1:-1] if target.startswith('<') else unquote(target)
                if t.startswith(('http://', 'https://', 'mailto:')):
                    continue
                t = t.split('#', 1)[0]
                if not t:
                    continue
                full = os.path.normpath(os.path.join(folder, t))
                self.assertTrue(os.path.exists(full), f'{label}: the link to {t} leads nowhere')

    def test_every_anchor_is_there(self):
        for label, folder, text in _texts():
            for target in LINK.findall(text):
                t = target[1:-1] if target.startswith('<') else unquote(target)
                if t.startswith(('http://', 'https://')) or '#' not in t:
                    continue
                path, anchor = t.split('#', 1)
                full = os.path.normpath(os.path.join(folder, path)) if path else None
                self.assertTrue(full and os.path.isfile(full), f'{label}: {t} leads nowhere')
                slugs = {_slug(h) for h in re.findall(r'^#+\s+(.+?)\s*$', _read(full), re.M)}
                self.assertIn(anchor.lower(), slugs, f'{label}: no heading for #{anchor} in {path}')

    def test_every_seed_part_named_is_there(self):
        parts = set(re.findall(r'^# Part ([IVXLC]+) —', _read(SEED), re.M))
        for label, _folder, text in _texts():
            for roman in re.findall(r'\bPart ([IVXLC]+)\b', _prose(text)):
                self.assertIn(roman, parts, f'{label} names Part {roman}, which the seed text does not hold')

    def test_the_commands_named_run(self):
        for script, args, expect in COMMANDS:
            r = subprocess.run([sys.executable, '-I', os.path.join(KIT, script)] + args, cwd=KIT,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, f'{script} {" ".join(args)}: {r.stderr[-300:]}')
            self.assertIn(expect, r.stdout, f'{script} {" ".join(args)} did not print {expect!r}')

    def test_every_skill_named_exists(self):
        skills = set(os.listdir(os.path.join(KIT, 'skills')))
        for label, _folder, text in _texts():
            for span in CODE.findall(text):
                s = span.strip()
                if re.fullmatch(r'[a-z]+(?:-[a-z]+)+', s):
                    self.assertIn(s, skills, f'{label}: the skill `{s}` is not in skills/')
                m = re.fullmatch(r'skills/([a-z-]+)/?(?:SKILL\.md)?', s)
                if m:
                    self.assertIn(m.group(1), skills, f'{label}: the skill `{s}` is not in skills/')

    def test_the_commands_run_from_the_kit(self):
        # The one command a page shows a reader running, with the kit's own engine.
        self.assertTrue(os.path.isfile(os.path.join(ENGINE, 'level.py')))
        self.assertTrue(os.path.isfile(os.path.join(ENGINE, 'holon.py')))
        self.assertTrue(os.path.isfile(os.path.join(KIT, 'hud', 'serve.py')))
        self.assertTrue(os.path.isfile(os.path.join(KIT, '.claude', 'hooks', 'awaken.sh')))


class TestLineCaps(unittest.TestCase):
    def test_each_page_under_its_cap(self):
        for label, (path, cap) in PAGES.items():
            n = len(_read(path).splitlines())
            self.assertLess(n, cap, f'{label} has {n} lines; its cap is under {cap}')


class TestWords(unittest.TestCase):
    def test_no_person_name(self):
        for label, _folder, text in _texts():
            for line in text.splitlines():
                if LICENCE_LINE.search(line):
                    continue
                for name in NAMES:
                    self.assertIsNone(re.search(r'\b' + re.escape(name) + r'\b', line),
                                      f'{label} names a person: {name}')

    def test_the_licence_notice_is_kept(self):
        moving = _read(PAGES['MOVING-IN.md'][0])
        self.assertIn('MOVING-FROM-V2.md', moving)
        self.assertIn('stays MPL-2.0', moving)
        self.assertIn('MOVING-IN.md, Path C', _read(os.path.join(KIT, 'LINEAGE.md')))

    def test_speech_is_how_it_tends_to_go(self):
        for label, _folder, text in _texts():
            low = _prose(text).lower()
            for phrase in STATED_SPEECH:
                self.assertNotIn(phrase, low, f'{label} states the agent\'s speech as fact: "{phrase}"')

    def test_no_timed_undo_in_the_conversation(self):
        for label, _folder, text in _texts():
            for line in _prose(text).splitlines():
                if re.search(r'\bundo\b', line, re.I):
                    self.assertIn('board', line.lower(), f'{label} promises an undo in the conversation: {line.strip()[:80]}')

    def test_the_first_sentence_is_a_form_to_fill(self):
        for label in ('START-HERE.md', 'Your First Hour.md'):
            self.assertIn('Hello, I am [your name].', _read(PAGES[label][0]), label)
        self.assertIn('Hello, I am [your name].', _quest_part())

    def test_no_contraction(self):
        for label, _folder, text in _texts():
            for line in _prose(text).splitlines():
                m = CONTRACTION.search(line)
                self.assertIsNone(m, f'{label}: a contraction, {m.group(0) if m else ""}, in: {line.strip()[:80]}')

    def test_the_kit_words(self):
        for label, _folder, text in _texts():
            for line in _prose(text).splitlines():
                m = OLD_WORDS.search(line)
                self.assertIsNone(m, f'{label}: the word {m.group(0) if m else ""} in: {line.strip()[:80]}')

    def test_no_line_cages_the_agent(self):
        for label, _folder, text in _texts():
            low = _prose(text).lower()
            for phrase in CAGES:
                self.assertNotIn(phrase, low, f'{label} prescribes the agent: "{phrase}"')


class TestTheHost(unittest.TestCase):
    def test_named_at_most_once_and_as_the_first_host(self):
        for label, _folder, text in _texts():
            lines = [ln for ln in _prose(text).splitlines() if re.search(r'\b' + HOST + r'\b', ln)]
            hits = sum(len(re.findall(r'\b' + HOST + r'\b', ln)) for ln in lines)
            self.assertLessEqual(hits, 1, f'{label} names the host {hits} times')
            for ln in lines:
                self.assertIn('first host', ln.lower(), f'{label} names the host outside "the first host"')

    def test_your_agent_in_its_host_elsewhere(self):
        for label, _folder, text in _texts():
            self.assertIn(IN_ITS_HOST, text.lower(), f'{label} does not say "{IN_ITS_HOST}"')

    def test_the_host_is_named_where_a_reader_starts(self):
        text = _prose(_read(PAGES['START-HERE.md'][0]))
        self.assertRegex(text, r'first host[^.]*\b' + HOST + r'\b')


class TestTheDoors(unittest.TestCase):
    def test_the_doors_other_pages_point_to(self):
        # The Quest pages for Mac and Windows, and MOVING-IN, send readers to these doors.
        text = _read(PAGES['START-HERE.md'][0])
        for door in ('## Door 1', '## Door 2', '## Door 3', '## Door 4', '## Door 5'):
            self.assertIn(door, text, door)
        self.assertIn("## Door 3 — your agent", text)
        moving = _read(PAGES['MOVING-IN.md'][0])
        for path in ('## Path A', '## Path B', '## Path C', '## Path D', '## Path E', '## Path F'):
            self.assertIn(path, moving, path)

    def test_the_board_is_offered_never_required(self):
        for label in ('START-HERE.md', 'Your First Hour.md'):
            low = _read(PAGES[label][0]).lower()
            self.assertIn('show me the board', low, label)
            self.assertIn('beside your conversation', low, label)
            self.assertIn('without', low, label)


if __name__ == '__main__':
    unittest.main()
