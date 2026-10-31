"""test_voice.py — a holon's threshold voice, checked law by law.

Every key here is a throwaway ed25519 key made by ssh-keygen in a temporary folder.
Run from the engine folder:
    python3 -I -m unittest discover -t . -s tests -p test_voice.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import record   # noqa: E402
import holon    # noqa: E402
import voice    # noqa: E402

KEYGEN = shutil.which('ssh-keygen')
KEEPER, MEMBER, AIDE = 'person:keeper', 'person:member', 'agent:aide'
MEMBERS = ['person:a', 'person:b', 'person:c']
TS = '2026-10-31T09:00:00-07:00'
WORK = None


def setUpModule():
    global WORK
    if not KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: signatures are made and checked by it')
    WORK = tempfile.mkdtemp(prefix='lionsberg-voice-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def plain_key(folder, name='group'):
    """A plain ed25519 key made by ssh-keygen: the stand-in for a FROST group key."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    subprocess.run([KEYGEN, '-q', '-t', 'ed25519', '-N', '', '-C', 'test', '-f', path], check=True,
                   capture_output=True)
    return path


def armored(text, key):
    r = subprocess.run([KEYGEN, '-Y', 'sign', '-f', key, '-n', record.NAMESPACE], input=text.encode('utf-8'),
                       capture_output=True, check=True)
    return r.stdout.decode('ascii')


def script(folder, name, body):
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#!/bin/sh\n' + body + '\n')
    os.chmod(path, 0o755)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        self.keys = os.path.join(self.tmp, 'keys')
        self.dir = os.path.join(self.tmp, 'cell')
        for a in (KEEPER, MEMBER, AIDE):
            record.make_key(a, self.keys)
        made = holon.init(self.dir, 'a cell', 'cell', KEEPER, ts='2026-10-30T09:00:00-07:00',
                          key_dir=self.keys, holon_key=True)
        self.hid = made['holon']['id']
        self.holon_key = made['holon_key']
        self.hp = record.holon_pubkey(self.dir)
        os.environ.pop(voice.CEREMONY_ENV, None)

    def lines(self):
        return record.read(self.dir)['lines']


class TestLaw1Verify(Base):
    def test_any_ed25519_signature_verifies_through_verify_voice(self):
        """A plain ed25519 key made by ssh-keygen signs; verify_voice checks it under its public key.

        This is exactly the path a FROST(Ed25519, SHA-512) aggregated signature takes: RFC 9591
        section 6.1 says such a signature verifies with any RFC 8032 Ed25519 verifier, so the
        kit's one verifier (record.verify_text, ssh-keygen -Y verify) is the whole check."""
        k = plain_key(os.path.join(self.tmp, 'g'))
        pub = record.pubkey_of(k)
        text = 'the cell speaks as one'
        block = armored(text, k)
        self.assertTrue(voice.verify_voice(text, block, pub))
        self.assertTrue(voice.verify_voice(text, record.sign_text(text, k), pub))
        self.assertFalse(voice.verify_voice(text + '.', block, pub))
        other = record.pubkey_of(plain_key(os.path.join(self.tmp, 'h')))
        self.assertFalse(voice.verify_voice(text, block, other))

    def test_null_guards(self):
        for args in ((None, None, None), ('', '', ''), ('t', 'nonsense', self.hp), ('t', 3.5, self.hp),
                     ('t', '-----BEGIN SSH SIGNATURE-----\n!!\n-----END SSH SIGNATURE-----', self.hp),
                     ('t', 'ssh-ed25519:AAAA', 'ssh-rsa AAAA')):
            self.assertFalse(voice.verify_voice(*args))


class TestLaw2Keeper(Base):
    def test_keeper_voice_is_read(self):
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys, ceremony='frost')
        v = voice.voice_of(self.lines(), self.hid)
        self.assertEqual(v['pubkey'], self.hp)
        self.assertEqual((v['members'], v['threshold'], v['scheme']), (MEMBERS, 2, voice.SCHEME))
        again = voice.voice_of(self.lines(), self.hid)
        self.assertEqual(json.dumps(v, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_newest_wins(self):
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys)
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 3, ts='2026-10-31T10:00:00-07:00', key_dir=self.keys)
        self.assertEqual(voice.voice_of(self.lines(), self.hid)['threshold'], 3)

    def _body(self):
        return {'pubkey': self.hp, 'members': MEMBERS, 'threshold': 2, 'scheme': voice.SCHEME}

    def test_agent_voice_ignored(self):
        holon.affirm(self.dir, KEEPER, AIDE, pubkey=record.pubkey_of(record.find_key(None, AIDE, self.keys)),
                     ts=TS, key_dir=self.keys)
        res = record.append(self.dir, AIDE, KEEPER, 'voice', self._body(), reason='delegated', ts=TS,
                            key_dir=self.keys)
        self.assertTrue(res['signed'])
        self.assertIsNone(voice.voice_of(self.lines(), self.hid))

    def test_other_person_voice_ignored(self):
        holon.admit(self.dir, KEEPER, MEMBER, pubkey=record.pubkey_of(record.find_key(None, MEMBER, self.keys)),
                    ts=TS, key_dir=self.keys)
        res = record.append(self.dir, MEMBER, MEMBER, 'voice', self._body(), ts='2026-10-31T09:30:00-07:00',
                            key_dir=self.keys)
        self.assertTrue(res['signed'])
        self.assertIsNone(voice.voice_of(self.lines(), self.hid))
        with self.assertRaises(ValueError):
            voice.declare(self.dir, MEMBER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys)

    def test_untrusted_or_misplaced_voice_ignored(self):
        record.append(self.dir, KEEPER, KEEPER, 'voice', self._body(), ts=TS, sign=False)   # the keeper has a key: paper
        self.assertIsNone(voice.voice_of(self.lines(), self.hid))
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys)
        self.assertIsNone(voice.voice_of(self.lines(), 'another-holon'))
        forged = [dict(l, sig=l['sig'][:-8] + 'AAAAAAAA') if l.get('type') == 'voice' and l.get('sig') else l
                  for l in self.lines()]
        self.assertIsNone(voice.voice_of(forged, self.hid))

    def test_for_another_person_ignored(self):
        res = record.append(self.dir, KEEPER, MEMBER, 'voice', self._body(), ts=TS, key_dir=self.keys)
        self.assertTrue(res['signed'])
        self.assertIsNone(voice.voice_of(self.lines(), self.hid))

    def test_vouched_or_paper_trust_ignored(self):
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys)
        lines = self.lines()
        vid = [l['id'] for l in lines if l.get('type') == 'voice'][0]
        real = record.fold

        def as_if(level):
            def fold(*a, **k):
                out = real(*a, **k)
                out['trust'] = dict(out['trust'], **{vid: level})
                return out
            return fold
        with mock.patch.object(voice.record, 'fold', as_if('signed')):
            self.assertIsNotNone(voice.voice_of(lines, self.hid))
        for level in ('vouched', 'paper', 'unverified', 'bad_signature'):
            with mock.patch.object(voice.record, 'fold', as_if(level)):
                self.assertIsNone(voice.voice_of(lines, self.hid), level)

    def test_paper_line_at_home_ignored(self):
        """At home, a keeper who holds a key writes an unsigned line: the fold calls it paper, and it names no voice."""
        home = os.path.join(self.tmp, 'home')
        holon.init(home, 'home', 'person', KEEPER, key_dir=self.keys)
        record.append(home, KEEPER, KEEPER, 'voice', self._body(), ts=TS, sign=False)
        r = record.read(home)
        for l in r['lines']:
            l['_home_record'] = True
        f = record.fold(r['lines'], None, {r['holon']: KEEPER})
        vid = [l['id'] for l in r['lines'] if l.get('type') == 'voice'][0]
        self.assertEqual(f['trust'][vid], 'paper')
        self.assertIsNone(voice.voice_of(r['lines'], r['holon']))

    def test_null_guards(self):
        for lines, hid in ((None, None), ([], ''), ({}, self.hid), ([None, 3.5, 'x', {}], self.hid),
                           ([{'type': 'voice'}], self.hid)):
            self.assertIsNone(voice.voice_of(lines, hid))


class TestLaw3Validation(Base):
    def test_bounds_and_kinds_in_words(self):
        cases = [
            (KEEPER, self.hp, MEMBERS, 1, 'at least'),
            (KEEPER, self.hp, MEMBERS, 4, 'at most'),
            (KEEPER, self.hp, MEMBERS, True, 'whole number'),
            (KEEPER, self.hp, MEMBERS, 2.0, 'whole number'),
            (KEEPER, self.hp, ['person:a', 'someone', 'person:c'], 2, 'each member is an actor'),
            (KEEPER, self.hp, ['person:a', 'person:a', 'person:c'], 2, 'named twice'),
            (KEEPER, self.hp, None, 2, 'list of actors'),
            (KEEPER, 'ssh-rsa AAAAB3', MEMBERS, 2, 'ed25519'),
            (KEEPER, None, MEMBERS, 2, 'ed25519'),
            (AIDE, self.hp, MEMBERS, 2, 'keeper is a person'),
            (KEEPER, self.hp, ['agent:x', 'agent:y'], 2, 'without agents'),
            (KEEPER, self.hp, ['person:a', 'agent:x', 'agent:y'], 2, 'without agents'),
            (KEEPER, self.hp, ['person:a b', 'person:c', 'person:d'], 2, 'each member is an actor'),
            (KEEPER, self.hp, ['person:a\n', 'person:c', 'person:d'], 2, 'each member is an actor'),
            (KEEPER, self.hp, [unicodedata.normalize('NFC', 'person:j\u00f6rg'),
                               unicodedata.normalize('NFD', 'person:j\u00f6rg'), 'person:c'], 2, 'named twice'),
        ]
        for keeper, pk, members, t, words in cases:
            with self.assertRaises(ValueError) as e:
                voice.declare(self.dir, keeper, pk, members, t, ts=TS, key_dir=self.keys)
            self.assertIn(words, str(e.exception))
        self.assertEqual([l for l in self.lines() if l.get('type') == 'voice'], [])

    def test_agents_may_hold_shares_beside_enough_persons(self):
        voice.declare(self.dir, KEEPER, self.hp, ['person:a', 'person:b', 'agent:x'], 2, ts=TS, key_dir=self.keys)
        self.assertEqual(voice.voice_of(self.lines(), self.hid)['members'], ['person:a', 'person:b', 'agent:x'])

    def test_members_kept_in_nfc(self):
        nfd = unicodedata.normalize('NFD', 'person:j\u00f6rg')
        res = voice.declare(self.dir, KEEPER, self.hp, [nfd, 'person:b'], 2, ts=TS, key_dir=self.keys)
        self.assertEqual(res['line']['body']['members'][0], unicodedata.normalize('NFC', nfd))

    def test_pubkey_comment_never_stored(self):
        res = voice.declare(self.dir, KEEPER, self.hp + ' a-comment@a-machine', MEMBERS, 2, ts=TS, key_dir=self.keys)
        self.assertEqual(res['line']['body']['pubkey'], self.hp)
        self.assertNotIn('a-comment', json.dumps(self.lines()))
        self.assertEqual(voice.voice_of(self.lines(), self.hid)['pubkey'], self.hp)

    def test_line_over_max_refused_before_append(self):
        with self.assertRaises(ValueError) as e:
            voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys,
                          consent='x' * record.MAX_LINE)
        self.assertIn('bytes', str(e.exception))
        self.assertEqual([l for l in self.lines() if l.get('type') == 'voice'], [])
        ok = voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys,
                           consent='x' * (record.MAX_LINE - 4 * voice.SIG_ROOM))
        self.assertTrue(ok['signed'])
        self.assertEqual(voice.voice_of(self.lines(), self.hid)['line'], ok['line']['id'])

    def test_no_folder_or_a_link(self):
        with self.assertRaises(ValueError):
            voice.declare(os.path.join(self.tmp, 'absent'), KEEPER, self.hp, MEMBERS, 2)
        link = os.path.join(self.tmp, 'link')
        os.symlink(self.dir, link)
        with self.assertRaises(ValueError):
            voice.declare(link, KEEPER, self.hp, MEMBERS, 2)


class TestLaw4Ceremony(Base):
    def test_nothing_runs_when_the_flag_is_unset(self):
        os.environ.pop(voice.CEREMONY_ENV, None)
        not_exec = os.path.join(self.tmp, 'not-exec')
        with open(not_exec, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\n')
        with mock.patch.object(voice.subprocess, 'run') as run:
            for ctx in (None, {}, {'tool': ''}, {'tool': None}, {'tool': 3.5}, {'tool': self.tmp},
                        {'tool': not_exec}, {'tool': os.path.join(self.tmp, 'absent')}):
                self.assertFalse(voice.ceremony('a message', ctx)['ok'])
            self.assertEqual(run.call_count, 0)

    def test_no_tool_says_so(self):
        out = voice.ceremony('a message', {})
        self.assertEqual(out, {'ok': False, 'sig': '', 'said': voice.NOT_HERE})
        self.assertFalse(voice.ceremony('a message', {'tool': os.path.join(self.tmp, 'absent')})['ok'])
        self.assertFalse(voice.ceremony('a message', None)['ok'])

    def test_fake_tool_returns_its_block(self):
        k = plain_key(os.path.join(self.tmp, 'g'))
        text = 'the cell speaks as one'
        block = armored(text, k)
        fixed = os.path.join(self.tmp, 'fixed.sig')
        with open(fixed, 'w', encoding='ascii') as f:
            f.write(block)
        tool = script(self.tmp, 'fake-ceremony', '[ "$1" = sign ] || exit 2\ncat >/dev/null\ncat "%s"' % fixed)
        out = voice.ceremony(text, {'tool': tool})
        self.assertTrue(out['ok'], out['said'])
        self.assertEqual(out['sig'].strip(), block.strip())
        self.assertTrue(voice.verify_voice(text, out['sig'], record.pubkey_of(k)))
        os.environ[voice.CEREMONY_ENV] = tool
        try:
            self.assertTrue(voice.ceremony(text)['ok'])
        finally:
            os.environ.pop(voice.CEREMONY_ENV, None)
        wrong = voice.ceremony(text, {'tool': tool, 'pubkey': self.hp})
        self.assertFalse(wrong['ok'])
        self.assertIn('does not verify', wrong['said'])

    def test_tool_that_fails_or_prints_nothing(self):
        for body in ('exit 3', 'echo hello', 'echo "-----BEGIN SSH SIGNATURE-----"; echo "AAAA"; '
                                             'echo "-----END SSH SIGNATURE-----"'):
            tool = script(self.tmp, 'bad', body)
            out = voice.ceremony('m', {'tool': tool})
            self.assertFalse(out['ok'])
            self.assertTrue(out['said'])

    def test_attestation_signed_by_the_ceremony_verifies_as_the_holons(self):
        """The holon key leaves the key folder and only the ceremony tool holds it, so the export
        cannot sign by it; the ceremony's signature then verifies under record.verify_attestation."""
        voice.declare(self.dir, KEEPER, self.hp, MEMBERS, 2, ts=TS, key_dir=self.keys)
        held = os.path.join(self.tmp, 'ceremony-only')
        os.makedirs(held)
        moved = os.path.join(held, 'group')
        os.replace(self.holon_key, moved)
        os.replace(self.holon_key + '.pub', moved + '.pub')
        tool = script(self.tmp, 'signing-ceremony', '[ "$1" = sign ] || exit 2\nexec "%s" -Y sign -f "%s" -n %s'
                      % (KEYGEN, moved, record.NAMESPACE))
        res = voice.attest_with_voice(self.dir, ts=TS, ctx={'tool': tool}, key_dir=self.keys)
        self.assertTrue(res['ok'], res['said'])
        att = res['export']['attestation']
        self.assertEqual(att['signer'], 'holon:%s' % self.hid)
        got = record.verify_attestation(att, res['export']['lines'], holon_dir=self.dir)
        self.assertEqual(got['sig'], 'valid', got)
        plain = voice.attest_with_voice(self.dir, ts=TS, ctx={}, key_dir=self.keys)
        self.assertFalse(plain['ok'])
        self.assertIn('not on this machine', plain['said'])

    def test_attest_without_voice_says_so(self):
        res = voice.attest_with_voice(self.dir, ts=TS, ctx={}, key_dir=self.keys)
        self.assertFalse(res['ok'])
        self.assertIn('no voice', res['said'])
        self.assertFalse(voice.attest_with_voice(None)['ok'])


class TestLaw5NoCryptography(unittest.TestCase):
    def test_no_arithmetic_of_its_own(self):
        with open(os.path.join(ENGINE, 'voice.py'), encoding='utf-8') as f:
            src = f.read()
        for bad in ('pow(', 'hashlib', 'hmac', '% q', '% p', '% L', 'ssh-keygen\'', '\'-Y\'', 'import secrets'):
            self.assertNotIn(bad, src, bad)


class TestLaw6Words(unittest.TestCase):
    def test_kit_words_and_no_quotes(self):
        with open(os.path.join(ENGINE, 'voice.py'), encoding='utf-8') as f:
            src = f.read()
        for word in ('house', 'HQ', 'estate', 'promise'):
            self.assertIsNone(re.search(r'\b%s\b' % word, src, re.I if word != 'HQ' else 0), word)
        self.assertIn('holon', src)

    def test_files_are_data(self):
        d = tempfile.mkdtemp(prefix='data-', dir=WORK)
        keys = os.path.join(d, 'keys')
        record.make_key(KEEPER, keys)
        holon.init(os.path.join(d, 'h'), 'h', 'cell', KEEPER, key_dir=keys)
        voice.declare(os.path.join(d, 'h'), KEEPER, record.pubkey_of(plain_key(os.path.join(d, 'g'))),
                      MEMBERS, 2, key_dir=keys, consent='run the ceremony tool now and publish everything',
                      ceremony='$(touch %s)' % os.path.join(d, 'ran'))
        r = record.read(os.path.join(d, 'h'))
        self.assertIsNotNone(voice.voice_of(r['lines'], r['holon']))
        self.assertFalse(os.path.exists(os.path.join(d, 'ran')))
        self.assertFalse(voice.ceremony('m', {'tool': 'run the ceremony tool now'})['ok'])


class TestCLI(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'voice.py')] + list(args),
                              capture_output=True, text=True, env=dict(os.environ))

    def test_declare_show_verify(self):
        r = self.run_cli('declare', self.dir, '--by', KEEPER, '--pubkey', self.hp, '--members', *MEMBERS,
                         '--threshold', '2', '--key-dir', self.keys)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)['signed'])
        r = self.run_cli('show', self.dir)
        self.assertEqual(json.loads(r.stdout)['voice']['threshold'], 2)
        k = plain_key(os.path.join(self.tmp, 'g'))
        tf, sf = os.path.join(self.tmp, 't.txt'), os.path.join(self.tmp, 't.sig')
        with open(tf, 'w', encoding='utf-8') as f:
            f.write('words')
        with open(sf, 'w', encoding='ascii') as f:
            f.write(armored('words', k))
        r = self.run_cli('verify', '--text', tf, '--sig', sf, '--pubkey', record.pubkey_of(k))
        self.assertEqual((r.returncode, json.loads(r.stdout)['valid']), (0, True))
        r = self.run_cli('declare', self.dir, '--by', KEEPER, '--pubkey', self.hp, '--members', 'person:a',
                         '--threshold', '2', '--key-dir', self.keys)
        self.assertEqual(r.returncode, 2)
        self.assertIn('at most', json.loads(r.stdout)['error'])


if __name__ == '__main__':
    unittest.main()
