"""test_xid.py — the XID: an identifier that outlives its keys, checked.

Run from the engine folder:
    python3 -I -m unittest discover -t . -s tests -p test_xid.py -v
"""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import holon   # noqa: E402
import record  # noqa: E402
import xid     # noqa: E402

HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
KEEPER, MEMBER, OTHER, AGENT = 'person:keeper', 'person:member', 'person:member-two', 'agent:keeper-aide'
SECOND = 'person:aaa'   # sorts first: a handle admitted with another actor's public key
CLOCK = '2026-10-24T12:00:00-07:00'

# The reference implementation's own test (bc-components-rust, src/id/xid.rs), Schnorr form.
VECTOR_KEY = 'e8251dc3a17e0f2c07865ed191139ecbcddcbdd070ec1ff65df5148c7ef4005a'
VECTOR_CBOR = 'd99c565820e8251dc3a17e0f2c07865ed191139ecbcddcbdd070ec1ff65df5148c7ef4005a'
VECTOR_XID = 'd40e0602674df1b732f5e025d04c45f2e74ed1652c5ae1740f6a5502dbbdcd47'


def ts(n):
    return '2026-10-21T09:%02d:00-07:00' % n


class Keys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix='lionsberg-xid-')
        os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(cls.work, 'sigcache.key')
        cls.kd = os.path.join(cls.work, 'keys')
        cls.pk = {}
        if HAVE_KEYGEN:
            for a in (KEEPER, MEMBER, OTHER, AGENT, SECOND):
                cls.pk[a] = record.pubkey_of(record.make_key(a, cls.kd))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def need_keys(self):
        if not HAVE_KEYGEN:
            self.skipTest('ssh-keygen is needed to make keys')


class TestDerivation(Keys):
    def test_law1_reference_vector_byte_for_byte(self):
        c = xid.cbor_signing_public_key('schnorr', bytes.fromhex(VECTOR_KEY))
        self.assertEqual(c.hex(), VECTOR_CBOR)
        self.assertEqual(hashlib.sha256(c).hexdigest(), VECTOR_XID)

    def test_ed25519_form_is_the_two_array(self):
        raw = bytes.fromhex(VECTOR_KEY)
        self.assertEqual(xid.cbor_signing_public_key('ed25519', raw), bytes.fromhex('d99c5682025820') + raw)
        for bad in (None, b'', b'\x00' * 31, b'\x00' * 33, 'x' * 32, 1.5):
            with self.assertRaises(ValueError):
                xid.cbor_signing_public_key('ed25519', bad)
        with self.assertRaises(ValueError):
            xid.cbor_signing_public_key('ecdsa', raw)

    def test_law2_ssh_ed25519_key(self):
        self.need_keys()
        a, b = self.pk[KEEPER], self.pk[MEMBER]
        x = xid.xid_of(a)
        self.assertRegex(x, r'^[0-9a-f]{64}$')
        self.assertEqual(x, xid.xid_of(a + ' a comment'))
        self.assertEqual(x, xid.xid_of(a))
        self.assertNotEqual(x, xid.xid_of(b))
        self.assertEqual(len(xid.ed25519_raw(a)), 32)
        self.assertEqual(xid.short(x), x[:8])
        self.assertTrue(xid.check(a, x))
        self.assertTrue(xid.check(a, x.upper()))
        self.assertFalse(xid.check(b, x))

    def test_law2_other_keys_refused_in_words(self):
        import base64
        import struct
        rsa_blob = base64.b64encode(struct.pack('>I', 7) + b'ssh-rsa' + struct.pack('>I', 3) + b'\x01\x00\x01').decode()
        lying = base64.b64encode(struct.pack('>I', 7) + b'ssh-rsa' + struct.pack('>I', 32) + b'\x00' * 32).decode()
        short_key = base64.b64encode(struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 31) + b'\x00' * 31).decode()
        for bad in ('ssh-rsa ' + rsa_blob, 'ssh-ed25519 ' + lying, 'ssh-ed25519 ' + short_key, 'ssh-ed25519 !!!',
                    'ssh-ed25519', ''):
            with self.assertRaises(ValueError) as cm:
                xid.xid_of(bad)
            self.assertTrue(str(cm.exception).strip())
            self.assertIsNone(xid.try_xid(bad))
        for bad in (None, {}, [], 1.5, 3):
            self.assertIsNone(xid.try_xid(bad))
            self.assertFalse(xid.check(bad, VECTOR_XID))
            self.assertEqual(xid.short(bad), '')
            self.assertIsNone(record.xid_for_key(bad))

    def test_cli(self):
        self.need_keys()
        f = os.path.join(self.work, 'k.pub')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(self.pk[KEEPER] + ' comment\n')
        exe = os.path.join(ENGINE, 'xid.py')
        r = subprocess.run([sys.executable, '-I', exe, 'of', f], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['xid'], xid.xid_of(self.pk[KEEPER]))
        r = subprocess.run([sys.executable, '-I', exe, 'check', f, '00' * 32], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, 1)
        link = os.path.join(self.work, 'link.pub')
        os.symlink(f, link)
        r = subprocess.run([sys.executable, '-I', exe, 'of', link], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)          # a linked file is not followed; its path is not a key


class TestOnTheActor(Keys):
    def setUp(self):
        self.need_keys()
        self.dir = tempfile.mkdtemp(prefix='holon-', dir=self.work)
        self.made = holon.init(self.dir, 'xid-cell', 'cell', KEEPER, ts=ts(0), salt='s0', key_dir=self.kd)
        self.hid = self.made['holon']['id']

    def fold(self):
        r = record.read(self.dir)
        return record.fold(r['lines'], None, {r['holon']: r['keeper']}, clock=CLOCK)

    def test_law3_inception_and_admission_carry_the_xid(self):
        inc = self.made['inception']
        self.assertEqual(inc['body']['xid'], xid.xid_of(inc['body']['pubkey']))
        self.assertEqual(record.holon_info(self.dir)['xid'], inc['body']['xid'])
        adm = holon.admit(self.dir, KEEPER, MEMBER, pubkey=self.pk[MEMBER], ts=ts(1), salt='s1', key_dir=self.kd)
        aff = holon.affirm(self.dir, KEEPER, AGENT, pubkey=self.pk[AGENT], ts=ts(2), salt='s2', key_dir=self.kd)
        self.assertEqual(adm['line']['body']['xid'], xid.xid_of(self.pk[MEMBER]))
        self.assertEqual(aff['line']['body']['xid'], xid.xid_of(self.pk[AGENT]))
        f = self.fold()
        for line in (inc, adm['line'], aff['line']):
            self.assertEqual(f['trust'][line['id']], 'signed')
        room = f['admitted'][self.hid]
        self.assertEqual(room[KEEPER]['xid'], inc['body']['xid'])
        self.assertEqual(room[MEMBER]['xid'], xid.xid_of(self.pk[MEMBER]))
        self.assertEqual(room[AGENT]['xid'], xid.xid_of(self.pk[AGENT]))
        self.assertEqual(room[MEMBER]['xid_now'], room[MEMBER]['xid'])
        self.assertNotIn('xid_mismatch', [x['flag'] for x in f['flags']])
        self.assertEqual(json.dumps(f['admitted'], sort_keys=True), json.dumps(self.fold()['admitted'], sort_keys=True))

    def test_admission_without_body_xid_still_gets_one(self):
        old = record.append(self.dir, KEEPER, KEEPER, 'join', {'who': MEMBER, 'pubkey': self.pk[MEMBER]},
                            ts=ts(1), salt='o1', key_dir=self.kd)
        self.assertNotIn('xid', old['line']['body'])
        self.assertEqual(self.fold()['admitted'][self.hid][MEMBER]['xid'], xid.xid_of(self.pk[MEMBER]))

    def test_law4_tampered_xid_is_flagged_and_the_computed_one_kept(self):
        bad = record.append(self.dir, KEEPER, KEEPER, 'join',
                            {'who': OTHER, 'pubkey': self.pk[OTHER], 'xid': 'ab' * 32},
                            ts=ts(1), salt='t1', key_dir=self.kd)
        f = self.fold()
        flags = [x for x in f['flags'] if x['flag'] == 'xid_mismatch']
        self.assertEqual([x['id'] for x in flags], [bad['line']['id']])
        self.assertEqual(f['admitted'][self.hid][OTHER]['xid'], xid.xid_of(self.pk[OTHER]))
        self.assertEqual(record.actor_by_xid(f, 'ab' * 32), None)

    def test_law4_tampered_affirm_is_flagged(self):
        bad = record.append(self.dir, KEEPER, KEEPER, 'affirm',
                            {'agent': AGENT, 'pubkey': self.pk[AGENT], 'xid': 'cd' * 32},
                            ts=ts(1), salt='ta', key_dir=self.kd)
        f = self.fold()
        self.assertEqual(f['trust'][bad['line']['id']], 'signed')
        self.assertIn((bad['line']['id'], 'xid_mismatch'), [(x['id'], x['flag']) for x in f['flags']])
        self.assertEqual(f['admitted'][self.hid][AGENT]['xid'], xid.xid_of(self.pk[AGENT]))

    def test_law4_tampered_inception_is_flagged(self):
        inc = self.made['inception']
        bad = record.make_line(KEEPER, KEEPER, '', 'join', dict(inc['body'], xid='ef' * 32), ts=ts(0), salt='ti',
                               prev='')
        bad['sig'] = record.sign_id(bad['id'], record.find_key(None, KEEPER, self.kd))
        f = record.fold([bad], None, {}, clock=CLOCK)
        self.assertEqual(f['trust'][bad['id']], 'signed')
        self.assertIn((bad['id'], 'xid_mismatch'), [(x['id'], x['flag']) for x in f['flags']])
        self.assertEqual(f['admitted'][bad['id']][KEEPER]['xid'], xid.xid_of(self.pk[KEEPER]))

    def test_one_xid_two_actors_names_no_one(self):
        holon.admit(self.dir, KEEPER, MEMBER, pubkey=self.pk[MEMBER], ts=ts(1), salt='m1', key_dir=self.kd)
        same = record.append(self.dir, KEEPER, KEEPER, 'join', {'who': SECOND, 'pubkey': self.pk[MEMBER]},
                             ts=ts(2), salt='m2', key_dir=self.kd)   # any admitter can admit anyone's public key
        f = self.fold()
        self.assertEqual(f['trust'][same['line']['id']], 'signed')
        x = xid.xid_of(self.pk[MEMBER])
        self.assertEqual(f['admitted'][self.hid][SECOND]['xid'], x)
        self.assertIsNone(record.actor_by_xid(f, x))
        self.assertIsNone(record.actor_by_xid(f, x, self.hid))
        shared = sorted(s['actor'] for s in f['flags'] if s['flag'] == 'xid_shared')
        self.assertEqual(shared, sorted([MEMBER, SECOND]))
        self.assertEqual(record.actor_by_xid(f, xid.xid_of(self.pk[KEEPER])), KEEPER)

    def test_body_xid_is_a_claim_checked_against_the_home(self):
        home = tempfile.mkdtemp(prefix='home-', dir=self.work)
        holon.init(home, 'member-home', 'person', MEMBER, ts=ts(0), salt='h0', key_dir=self.kd)
        life = xid.xid_of(self.pk[MEMBER])
        other = record.pubkey_of(record.make_key(MEMBER, os.path.join(self.work, 'other-%s' % self.hid[:8])))
        right = holon.admit(self.dir, KEEPER, MEMBER, pubkey=self.pk[MEMBER], xid=life, ts=ts(1), salt='c1',
                            key_dir=self.kd)
        self.assertEqual(right['line']['body']['xid'], life)
        cell2 = tempfile.mkdtemp(prefix='cell2-', dir=self.work)
        holon.init(cell2, 'second-cell', 'cell', KEEPER, ts=ts(0), salt='c2', key_dir=self.kd)
        here = holon.admit(cell2, KEEPER, MEMBER, pubkey=other, ts=ts(1), salt='c3', key_dir=self.kd)
        claimed = holon.admit(cell2, KEEPER, OTHER, pubkey=self.pk[OTHER], xid=life, ts=ts(2), salt='c4',
                              key_dir=self.kd)
        lines, keepers = [], {}
        for d in (home, self.dir, cell2):
            r = record.read(d)
            lines += r['lines']
            keepers[r['holon']] = r['keeper']
        f = record.fold(lines, None, keepers, clock=CLOCK)
        flagged = {x['id'] for x in f['flags'] if x['flag'] == 'xid_mismatch'}
        self.assertNotIn(right['line']['id'], flagged)      # the life XID, and the first key admitted here
        self.assertIn(here['line']['id'], flagged)          # its key's XID, not the home's inception key's
        self.assertIn(claimed['line']['id'], flagged)       # a life XID that is not the key admitted here
        self.assertEqual(f['admitted'][record.holon_info(cell2)['id']][OTHER]['xid'], xid.xid_of(self.pk[OTHER]))

    def test_another_xid_module_on_the_path_never_breaks_the_fold(self):
        import types
        saved = sys.modules.get('xid')
        sys.modules['xid'] = types.ModuleType('xid')       # a stranger's `xid`, without try_xid
        cache = getattr(record, '_XID_MODULE', None)
        if isinstance(cache, list):
            del cache[:]
        try:
            f = self.fold()
            self.assertEqual(f['admitted'][self.hid][KEEPER]['xid'], xid.xid_of(self.pk[KEEPER]))
        finally:
            sys.modules['xid'] = saved

    def test_law5_rotation_keeps_the_xid(self):
        holon.admit(self.dir, KEEPER, MEMBER, pubkey=self.pk[MEMBER], ts=ts(1), salt='r1', key_dir=self.kd)
        new = record.pubkey_of(record.make_key(MEMBER, os.path.join(self.work, 'rotated-%s' % self.hid[:8])))
        rot = record.append(self.dir, MEMBER, MEMBER, 'join', {'who': MEMBER, 'pubkey': new}, ts=ts(2), salt='r2',
                            key_dir=self.kd)   # signed with the current key: a rotation
        f = self.fold()
        e = f['admitted'][self.hid][MEMBER]
        self.assertEqual(f['trust'][rot['line']['id']], 'signed')
        self.assertEqual((e['via'], e['pubkey']), ('rotate', new))
        first = xid.xid_of(self.pk[MEMBER])
        self.assertEqual(record.xid_of_actor(f, self.hid, MEMBER), first)
        self.assertEqual(e['xid_now'], xid.xid_of(new))
        self.assertEqual(record.actor_by_xid(f, first), MEMBER)
        self.assertEqual(record.actor_by_xid(f, first.upper(), self.hid), MEMBER)
        self.assertIsNone(record.actor_by_xid(f, first, 'another-holon'))
        self.assertIsNone(record.actor_by_xid(f, xid.xid_of(new)))   # the current key's hash is not the XID
        self.assertEqual(record.actor_by_xid(f, xid.xid_of(self.pk[KEEPER])), KEEPER)

    def test_readers_null_guards(self):
        for bad in (None, {}, [], 1.5, {'admitted': None}, {'admitted': {'h': None}}):
            self.assertIsNone(record.actor_by_xid(bad, VECTOR_XID))
            self.assertIsNone(record.xid_of_actor(bad, 'h', KEEPER))
        f = self.fold()
        self.assertIsNone(record.actor_by_xid(f, None))
        self.assertIsNone(record.actor_by_xid(f, ''))
        self.assertIsNone(record.xid_of_actor(f, self.hid, 'person:nobody'))
        self.assertIsNone(record.xid_of_actor(f, None, KEEPER))


class TestToolCheck(Keys):
    def setUp(self):
        self.need_keys()
        self.saved = os.environ.pop(xid.TOOL_ENV, None)

    def tearDown(self):
        if self.saved is not None:
            os.environ[xid.TOOL_ENV] = self.saved

    def fake(self, said):
        p = os.path.join(tempfile.mkdtemp(prefix='tool-', dir=self.work), 'envelope')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\necho "%s"\n' % said)
        os.chmod(p, 0o755)
        return p

    def test_law6_without_the_tool(self):
        r = xid.tool_check(self.pk[KEEPER])
        self.assertFalse(r['ok'])
        self.assertTrue(r['said'].strip())
        self.assertEqual(r['ours'], xid.xid_of(self.pk[KEEPER]))
        self.assertFalse(xid.tool_check(self.pk[KEEPER], tool=os.path.join(self.work, 'absent'))['ok'])
        self.assertFalse(xid.tool_check(None)['ok'])
        self.assertEqual(json.dumps(r, sort_keys=True), json.dumps(xid.tool_check(self.pk[KEEPER]), sort_keys=True))

    def test_law6_with_a_fake_tool(self):
        ours = xid.xid_of(self.pk[KEEPER])
        r = xid.tool_check(self.pk[KEEPER], tool=self.fake(ours))
        self.assertTrue(r['ok'])
        self.assertEqual(r['theirs'], ours)
        os.environ[xid.TOOL_ENV] = self.fake('ff' * 32)
        r = xid.tool_check(self.pk[KEEPER])
        self.assertFalse(r['ok'])
        self.assertEqual(r['theirs'], 'ff' * 32)
        self.assertEqual(r['form'], 'ssh-text')
        self.assertIn('expected', r['said'])                 # the reference's SSH form hashes differently
        self.assertFalse(xid.tool_check(self.pk[KEEPER], tool=self.fake('ur:xid/not-decoded'))['ok'])


class TestKit(unittest.TestCase):
    def test_law7_standard_library_and_the_kits_words(self):
        path = os.path.join(ENGINE, 'xid.py')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        tree = ast.parse(text)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or '').split('.')[0])
        stdlib = getattr(sys, 'stdlib_module_names', None)
        if stdlib:
            self.assertTrue(mods <= set(stdlib), mods - set(stdlib))
        added = []
        for name in ('record.py', 'holon.py'):
            with open(os.path.join(ENGINE, name), encoding='utf-8') as f:
                added += [ln for ln in f if 'xid' in ln.lower()]
        self.assertGreater(len(added), 20)
        low = (text + ''.join(added)).lower()
        for word in ('promise', ' house', 'estate', ' hq'):
            self.assertNotIn(word, low)


if __name__ == '__main__':
    unittest.main()
