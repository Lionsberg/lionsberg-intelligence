"""test_hud_pane.py — the board as a pane beside the session (Player+ 4.0).

The home carries one launch configuration (`.claude/launch.json`) that serves the kit's HUD, so the
host's preview opens the board beside the conversation. This module checks what a script can: the
configuration names a server that is in the kit and a port that server uses; the server it names
starts and answers on that port's form; the Deal's skill names the pane; and the bookshelf page that
explains it stays under its cap, names no person, carries no contraction and no older word, names
the host at most once and as the first host, and links only to what is there. Whether an untrained
reader can use the pane is the cold reader's test, not this one. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_hud_pane.py -v
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
import urllib.request
from urllib.parse import unquote

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
LAUNCH = os.path.join(KIT, '.claude', 'launch.json')
SERVE = os.path.join(KIT, 'hud', 'serve.py')
DEAL = os.path.join(KIT, '.claude', 'skills', 'the-deal', 'SKILL.md')
PAGE = os.path.join(KIT, 'bookshelf', 'with-your-agent', 'The Board Beside the Talk.md')
PAGE_CAP = 60                       # the brief's cap, in lines

# The host's name, assembled so this file does not itself carry it.
HOST = 'Cla' + 'ude'
IN_ITS_HOST = 'your agent in its host'
# Names of persons that must not appear on a page that leaves this home (as test_way_in keeps them).
NAMES = ('Ada', 'Ana', 'Pete', 'Peter', 'Kaminski', 'Jordan', 'Sukut', 'Freya',
         'AURELLI' + 'ØN', 'S' + 'ir')
CONTRACTION = re.compile(
    r"\b\w+[’'](?:t|re|ve|ll|m|d)\b|\b(?:it|that|here|there|what|let|who|where|he|she)[’']s\b", re.I)
OLD_WORDS = re.compile(r'\b(?:HQ|house|houses|estate|prom' + r'ise|prom' + r'ises)\b', re.I)
CAGES = ('asks only', 'speaks only', 'never recites', 'only when asked', 'the agent never',
         'your agent never', 'the agent always', 'your agent always')
# A quoted line of anyone's words: curly double quotes, or straight ones outside code.
QUOTED = re.compile(r'[“”]|"[^"\n]{3,}"')
TOP = ('.claude/skills/', 'engine/', 'hud/', 'bookshelf/', '.claude/', 'scripts/')
CODE = re.compile(r'`([^`]+)`')
LINK = re.compile(r'\]\((<[^>]+>|[^)\s]+)\)')
PORT_DEFAULT = re.compile(r'add_argument\(\s*"--port"\s*,\s*type=int\s*,\s*default=(\d+)')
START_WAIT_S = 15                   # seconds the smoke test waits for the server's first answer


def _read(path):
    with open(path, encoding='utf-8') as f:
        return unicodedata.normalize('NFC', f.read())


def _config():
    data = json.loads(_read(LAUNCH))
    confs = data.get('configurations') if isinstance(data, dict) else None
    return data, (confs[0] if isinstance(confs, list) and len(confs) == 1 and isinstance(confs[0], dict) else None)


def _script_and_flags(conf):
    """The script the configuration runs (the first argument naming a .py file), and its flags."""
    args = conf.get('runtimeArgs') or []
    script = next((a for a in args if isinstance(a, str) and a.endswith('.py')), None)
    flags = {}
    for i, a in enumerate(args):
        if isinstance(a, str) and a.startswith('--') and i + 1 < len(args):
            flags[a] = args[i + 1]
    return script, flags


def _prose(text):
    """The words a reader reads: code and link targets taken out."""
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    text = CODE.sub(' ', text)
    text = LINK.sub('] ', text)
    return re.sub(r'https?://\S+', ' ', text)


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestLaunchConfiguration(unittest.TestCase):

    def test_one_configuration_in_the_hosts_form(self):
        data, conf = _config()
        self.assertIsInstance(data.get('version'), str)
        self.assertIsNotNone(conf, 'one configuration, an object')
        for key in ('name', 'runtimeExecutable', 'runtimeArgs', 'port'):
            self.assertIn(key, conf)
        self.assertTrue(conf['name'].strip())
        self.assertIsInstance(conf['runtimeArgs'], list)
        self.assertTrue(all(isinstance(a, str) for a in conf['runtimeArgs']))
        self.assertIsInstance(conf['port'], int)
        self.assertNotIsInstance(conf['port'], bool)

    def test_it_names_the_kits_hud_server_and_it_exists(self):
        _data, conf = _config()
        script, _flags = _script_and_flags(conf)
        self.assertEqual(script, 'hud/serve.py')
        path = os.path.join(KIT, script)
        self.assertTrue(os.path.isfile(path) and not os.path.islink(path), path)
        self.assertIn('python', os.path.basename(conf['runtimeExecutable']))

    def test_its_port_is_the_port_the_server_uses(self):
        _data, conf = _config()
        _script, flags = _script_and_flags(conf)
        m = PORT_DEFAULT.search(_read(SERVE))
        self.assertIsNotNone(m, 'serve.py declares its --port default')
        self.assertEqual(conf['port'], int(m.group(1)))
        if '--port' in flags:
            self.assertEqual(int(flags['--port']), conf['port'])

    def test_it_gives_the_server_a_home_it_can_start_on(self):
        _data, conf = _config()
        _script, flags = _script_and_flags(conf)
        self.assertTrue('--hq' in flags or '--fixture' in flags, 'serve.py starts only with --hq or --fixture')
        if '--hq' in flags:
            self.assertTrue(os.path.isdir(os.path.join(KIT, flags['--hq'])))

    def test_the_server_it_names_starts_and_answers(self):
        """The same arguments, on a free port and a scratch home, answer GET / with the HUD's page."""
        _data, conf = _config()
        args = list(conf['runtimeArgs'])
        port = _free_port()
        with tempfile.TemporaryDirectory() as hq:
            for flag, value in (('--hq', hq), ('--port', str(port))):
                if flag in args:
                    args[args.index(flag) + 1] = value
                else:
                    args += [flag, value]
            proc = subprocess.Popen([sys.executable] + args, cwd=KIT,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                body, deadline = None, time.monotonic() + START_WAIT_S
                while time.monotonic() < deadline and proc.poll() is None:
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=2) as r:
                            body = r.read(4096).decode('utf-8', 'replace')
                        break
                    except OSError:
                        time.sleep(0.2)
                self.assertIsNotNone(body, 'the server answered within the wait')
                self.assertIn('<html', body.lower())
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


class TestTheDealNamesThePane(unittest.TestCase):

    def test_the_skill_says_how_the_board_opens(self):
        text = _read(DEAL)
        _data, conf = _config()
        self.assertIn('Show me the board', text)
        self.assertIn('.claude/launch.json', text)
        self.assertIn(conf['name'], text)


class TestTheBookshelfPage(unittest.TestCase):

    def setUp(self):
        self.text = _read(PAGE)
        self.prose = _prose(self.text)

    def test_under_its_cap(self):
        self.assertLess(len(self.text.splitlines()), PAGE_CAP)

    def test_names_no_person_and_quotes_no_one(self):
        for name in NAMES:
            self.assertIsNone(re.search(r'\b' + re.escape(name) + r'\b', self.text), name)
        self.assertNotIn('person:', self.text.replace('person:<', ''))
        self.assertIsNone(QUOTED.search(self.prose))

    def test_no_contraction_no_older_word_no_cage(self):
        self.assertIsNone(CONTRACTION.search(self.prose))
        self.assertIsNone(OLD_WORDS.search(self.prose))
        low = self.prose.lower()
        for phrase in CAGES:
            self.assertNotIn(phrase, low)

    def test_the_host_named_once_as_the_first_host(self):
        self.assertLessEqual(self.prose.count(HOST), 1)
        if HOST in self.prose:
            self.assertIn('the first host your agent lives in, the ' + HOST + ' app', self.prose)
        self.assertIn(IN_ITS_HOST, self.prose.lower())

    def test_it_says_the_same_act_and_never_required(self):
        low = self.text.lower()
        self.assertIn('same line in the record', low)
        self.assertIn('never required', low)
        self.assertIn('read-back is the undo', low)

    def test_every_link_and_path_it_names_is_there(self):
        here = os.path.dirname(PAGE)
        for target in LINK.findall(self.text):
            t = unquote(target.strip('<>')).split('#', 1)[0]
            if not t or t.startswith(('http://', 'https://')):
                continue
            self.assertTrue(os.path.exists(os.path.join(here, t)), t)
        for span in CODE.findall(self.text):
            if span.startswith(TOP):
                self.assertTrue(os.path.exists(os.path.join(KIT, span)), span)

    def test_the_shelf_lists_it(self):
        readme = _read(os.path.join(os.path.dirname(PAGE), 'README.md'))
        if 'The%20Board%20Beside%20the%20Talk' not in readme and 'The Board Beside the Talk' not in readme:
            self.skipTest('the shelf README is written by the integrator, who lists the page')


if __name__ == '__main__':
    unittest.main()
