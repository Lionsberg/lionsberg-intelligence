"""test_keepsafe.py — recovery through the cell, checked: the field, the scheme, the header, the record's side.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_keepsafe.py -v
"""
import base64
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import holon      # noqa: E402
import keepsafe   # noqa: E402
import record     # noqa: E402

HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
PERSON = 'person:player'
MEMBERS = ['person:m1', 'person:m2', 'person:m3', 'person:m4', 'person:m5']
TS = '2026-10-31T09:00:00-07:00'


def det_rng(seed):
    """A deterministic rng for tests: sha256 of the seed and a counter, as a byte stream."""
    state = {'n': 0, 'buf': b''}

    def rng(k):
        while len(state['buf']) < k:
            state['buf'] += hashlib.sha256(seed + state['n'].to_bytes(8, 'big')).digest()
            state['n'] += 1
        out, state['buf'] = state['buf'][:k], state['buf'][k:]
        return out
    return rng


SECRET = bytes(range(32))


class TestField(unittest.TestCase):
    def test_rijndael_polynomial(self):
        self.assertEqual(keepsafe.POLY, 0x11b)

    def test_hand_values(self):
        self.assertEqual(keepsafe.gf_mul(0x53, 0xCA), 0x01)
        self.assertEqual(keepsafe.gf_mul(2, 128), 0x1b)
        self.assertEqual(keepsafe.gf_mul(0x57, 0x83), 0xC1)   # FIPS-197 section 4.2
        self.assertEqual(keepsafe.gf_mul(0, 0x77), 0)
        self.assertEqual(keepsafe.gf_div(1, 0x53), 0xCA)
        self.assertEqual(keepsafe.gf_inv(0xCA), 0x53)

    def test_every_inverse(self):
        for b in range(1, 256):
            self.assertEqual(keepsafe.gf_mul(b, keepsafe.gf_inv(b)), 1)
            self.assertEqual(keepsafe.gf_div(keepsafe.gf_mul(0x9d, b), b), 0x9d)

    def test_zero_and_range_refused(self):
        with self.assertRaises(ValueError):
            keepsafe.gf_div(5, 0)
        with self.assertRaises(ValueError):
            keepsafe.gf_mul(256, 1)
        with self.assertRaises(ValueError):
            keepsafe.gf_mul(1.0, 1)

    def test_interpolate_line(self):
        c, m = 0x11, 0x23   # f(x) = c + m x
        pts = [(0, bytes([c])), (1, bytes([c ^ m]))]
        self.assertEqual(keepsafe.interpolate(2, pts), bytes([c ^ keepsafe.gf_mul(m, 2)]))
        self.assertEqual(keepsafe.interpolate(1, pts), bytes([c ^ m]))
        with self.assertRaises(ValueError):
            keepsafe.interpolate(3, [(1, b'a'), (1, b'b')])
        with self.assertRaises(ValueError):
            keepsafe.interpolate(3, [])
        with self.assertRaisesRegex(ValueError, 'bytes'):
            keepsafe.interpolate(3, [(1, 4), (2, 5)])


class TestScheme(unittest.TestCase):
    def test_round_trip_thresholds(self):
        for t in (1, 2, 3, 5):
            shares = keepsafe.split(SECRET, t, 5, rng=det_rng(b't%d' % t))
            self.assertEqual(len(shares), 5)
            self.assertEqual(keepsafe.recover(shares[:t]), SECRET)
            self.assertEqual(keepsafe.recover(shares[-t:]), SECRET)

    def test_every_subset_three_of_five(self):
        shares = keepsafe.split(SECRET, 3, 5, rng=det_rng(b'sub'))
        for sub in itertools.combinations(shares, 3):
            self.assertEqual(keepsafe.recover(list(sub)), SECRET)
        self.assertEqual(keepsafe.recover(shares), SECRET)

    def test_threshold_one_extra_shares_checked(self):
        shares = keepsafe.split(SECRET, 1, 3, rng=det_rng(b'one'))
        bad = bytearray(shares[2])
        bad[8] ^= 1
        with self.assertRaisesRegex(ValueError, 'index 2'):
            keepsafe.recover([shares[0], shares[1], bytes(bad)])
        self.assertEqual(keepsafe.recover(shares), SECRET)

    def test_threshold_one_is_the_secret(self):
        for s in keepsafe.split(SECRET, 1, 3, rng=det_rng(b'one')):
            self.assertEqual(s[5:], SECRET)

    def test_fewer_than_threshold_refused(self):
        shares = keepsafe.split(SECRET, 3, 5, rng=det_rng(b'few'))
        with self.assertRaisesRegex(ValueError, 'needs 3'):
            keepsafe.recover(shares[:2])
        with self.assertRaisesRegex(ValueError, 'needs 3'):
            keepsafe.recover([shares[0], shares[0], shares[1]])
        with self.assertRaisesRegex(ValueError, 'no shares'):
            keepsafe.recover([])

    def test_tampered_share_refused_by_digest(self):
        shares = keepsafe.split(SECRET, 3, 5, rng=det_rng(b'tamper'))
        bad = bytearray(shares[1])
        bad[9] ^= 0x01
        with self.assertRaisesRegex(ValueError, 'digest'):
            keepsafe.recover([shares[0], bytes(bad), shares[2]])
        with self.assertRaisesRegex(ValueError, 'index 3'):   # a fourth share off the polynomial is named
            bad4 = bytearray(shares[3])
            bad4[7] ^= 0x40
            keepsafe.recover([shares[0], shares[1], shares[2], bytes(bad4)])

    def test_disagreeing_shares_refused(self):
        a = keepsafe.split(SECRET, 2, 3, identifier=1, rng=det_rng(b'a'))
        b = keepsafe.split(SECRET, 2, 3, identifier=2, rng=det_rng(b'b'))
        with self.assertRaisesRegex(ValueError, 'identifiers differ'):
            keepsafe.recover([a[0], b[1]])
        c = keepsafe.split(SECRET + SECRET, 2, 3, identifier=1, rng=det_rng(b'c'))
        with self.assertRaisesRegex(ValueError, 'length'):
            keepsafe.recover([a[0], c[1]])
        d = keepsafe.split(SECRET, 3, 3, identifier=1, rng=det_rng(b'd'))
        with self.assertRaisesRegex(ValueError, 'threshold'):
            keepsafe.recover([a[0], d[1]])

    def test_validation_in_words(self):
        for args in ((SECRET, 0, 3), (SECRET, 4, 3), (SECRET, 2, 17), (SECRET[:15], 2, 3), (SECRET[:17], 2, 3),
                     (SECRET, True, 3), ('text', 2, 3), (SECRET, 2.0, 3)):
            with self.assertRaises(ValueError):
                keepsafe.split(*args, rng=det_rng(b'v'))
        with self.assertRaises(ValueError):
            keepsafe.split(SECRET, 2, 3, identifier=70000)

    def test_deterministic(self):
        a = keepsafe.split(SECRET, 3, 5, rng=det_rng(b'same'))
        b = keepsafe.split(SECRET, 3, 5, rng=det_rng(b'same'))
        self.assertEqual(a, b)
        self.assertEqual(json.dumps([keepsafe.b64(x) for x in a], sort_keys=True),
                         json.dumps([keepsafe.b64(x) for x in b], sort_keys=True))
        self.assertNotEqual(a, keepsafe.split(SECRET, 3, 5, rng=det_rng(b'other')))


# an independent GF(256) by log and antilog tables (generator 0x03, polynomial 0x11b), for the known answer
_EXP, _LOG = [0] * 510, [0] * 256
_v = 1
for _i in range(255):
    _EXP[_i] = _EXP[_i + 255] = _v
    _LOG[_v] = _i
    _v ^= (_v << 1) ^ (0x11b if _v & 0x80 else 0)
    _v &= 0xff


def _ref_mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _ref_div(a, b):
    return 0 if a == 0 else _EXP[(_LOG[a] - _LOG[b]) % 255]


def _ref_interp(x, pts):
    out = bytearray(len(pts[0][1]))
    for i, (xi, vi) in enumerate(pts):
        num = den = 1
        for j, (xj, _) in enumerate(pts):
            if j != i:
                num, den = _ref_mul(num, x ^ xj), _ref_mul(den, xi ^ xj)
        w = _ref_div(num, den)
        for k in range(len(out)):
            out[k] ^= _ref_mul(w, vi[k])
    return bytes(out)


class TestKnownAnswer(unittest.TestCase):
    S = bytes(range(16))
    PINNED = ['12340002009949ea85f914097078c8c1052c4ac214',
              '123400020114d46acbdf20afa1a8a20c3a835580b1',
              '12340002023a9b16c3dc216c45cf6e310e48d1c84d',
              '1234000203b706968dfa15ca941f04fc31e7ce8ae8']

    def test_pinned_vector(self):
        shares = keepsafe.split(self.S, 3, 4, identifier=0x1234, rng=det_rng(b'kat'))
        self.assertEqual([s.hex() for s in shares], self.PINNED)

    def test_slip39_construction_independently(self):
        rng = det_rng(b'kat')
        r = rng(len(self.S) - 4)                 # R: n - 4 random bytes, drawn first
        first = rng(len(self.S))                 # the T - 2 = 1 random share, at x = 0
        import hmac as _hmac
        digest_share = _hmac.new(r, self.S, hashlib.sha256).digest()[:4] + r   # HMAC-SHA256(key=R, msg=S)[:4] ‖ R
        base = [(0, first), (254, digest_share), (255, self.S)]
        want = [first] + [_ref_interp(x, base) for x in (1, 2, 3)]
        shares = [bytes.fromhex(h) for h in self.PINNED]
        self.assertEqual([s[5:] for s in shares], want)
        pts = [(i, s[5:]) for i, s in enumerate(shares[:3])]
        self.assertEqual(_ref_interp(255, pts), self.S)
        self.assertEqual(_ref_interp(254, pts), digest_share)
        self.assertEqual(keepsafe.recover(shares[1:]), self.S)

    def test_reference_field_agrees(self):
        for a in range(0, 256, 7):
            for b in range(256):
                self.assertEqual(keepsafe.gf_mul(a, b), _ref_mul(a, b))


class TestHeader(unittest.TestCase):
    def test_bit_exact_layout(self):
        shares = keepsafe.split(SECRET, 3, 5, identifier=0xABCD, rng=det_rng(b'h'))
        for i, s in enumerate(shares):
            self.assertEqual(s[:5], bytes([0xAB, 0xCD, 0x00, 0x02, i]))
            self.assertEqual(len(s), 5 + len(SECRET))   # the value is the secret's length, unpadded
            h = keepsafe.parse(s)
            self.assertEqual((h['identifier'], h['group_threshold'], h['group_count'], h['group_index'],
                              h['threshold'], h['reserved'], h['index']), (0xABCD, 1, 1, 0, 3, 0, i))

    def test_stored_minus_one_encodings(self):
        self.assertEqual(keepsafe.header(0, 16, 16, 15)[3] & 0xf, 0xf)
        self.assertEqual(keepsafe.header(0, 1, 1, 0)[3] & 0xf, 0x0)
        self.assertEqual(keepsafe.header(0x0102, 2, 2, 1, group_threshold=2, group_count=16, group_index=3),
                         bytes([0x01, 0x02, 0x1f, 0x31, 0x01]))
        top = keepsafe.split(SECRET, 16, 16, identifier=7, rng=det_rng(b'top'))
        self.assertEqual(keepsafe.parse(top[15])['threshold'], 16)
        self.assertEqual(keepsafe.parse(top[15])['index'], 15)
        self.assertEqual(keepsafe.recover(top), SECRET)

    def test_reserved_and_groups_refused(self):
        s = bytearray(keepsafe.split(SECRET, 2, 2, identifier=7, rng=det_rng(b'r'))[0])
        s[4] |= 0x10
        with self.assertRaisesRegex(ValueError, 'reserved'):
            keepsafe.parse(bytes(s))
        g = keepsafe.header(7, 2, 2, 0, group_count=2) + SECRET
        with self.assertRaisesRegex(ValueError, 'one group'):
            keepsafe.parse(g)
        with self.assertRaises(ValueError):
            keepsafe.parse(b'short')


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed to make and check keys')
class TestKeyAndRecord(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='keepsafe-test-')
        self.keys = os.path.join(self.tmp, 'keys')
        os.makedirs(self.keys)
        self.home = os.path.join(self.tmp, 'home')
        holon.init(self.home, 'home', 'person', PERSON, ts=TS, salt='h', key_dir=self.keys, make_key=True)
        self.key = record.find_key(None, PERSON, self.keys)
        with open(self.key, 'rb') as f:
            self.key_bytes = f.read()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self, t=3, key=None, padded=True, pubkey=None, sign=None):
        sp = keepsafe.split_key_file(key or self.key, t, len(MEMBERS), rng=det_rng(b'plan'))
        res = keepsafe.share_lines(self.home, PERSON, MEMBERS, [x['share'] for x in sp['shares']], t,
                                   ts=TS, key_dir=self.keys, padded=sp['padded'] if padded else None,
                                   count=sp['count'], pubkey=pubkey, sign=sign)
        return sp, res

    def other_key(self, name='other'):
        p = os.path.join(self.tmp, name)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', p], check=True, timeout=60)
        return p

    def test_forged_unsigned_lines_refused(self):
        # the review's scenario: unsigned share lines under the person's actor, naming another key
        ak = self.other_key()
        sp = keepsafe.split_key_file(ak, 2, 3)
        r = keepsafe.share_lines(self.home, PERSON, MEMBERS[:3], [x['share'] for x in sp['shares']], 2,
                                 pubkey=sp['pubkey'], sign=False)
        self.assertEqual([x['signed'] for x in r['lines']], [False] * 3)
        self.assertEqual(keepsafe.share_records(self.home, PERSON), [])
        out = keepsafe.restore_walk(self.home, PERSON, {m: r['shares'][m] for m in MEMBERS[:2]})
        self.assertFalse(out['ok'])
        self.assertIsNone(out['key_text'])
        self.assertIn('trusts', out['said'])

    def test_signed_lines_naming_another_key_refused(self):
        ak = self.other_key()
        sp, res = self.plan(t=2, key=ak, pubkey=record.pubkey_of(ak))
        self.assertTrue(all(x['signed'] for x in res['lines']))
        out = keepsafe.restore_walk(self.home, PERSON, {m: res['shares'][m] for m in MEMBERS[:2]})
        self.assertFalse(out['ok'])
        self.assertIsNone(out['key_text'])
        self.assertIn('name a key that is not %s\'s admitted key' % PERSON, out['said'])

    def test_recovered_key_not_the_named_key_refused(self):
        # signed lines name the admitted key, but the shares restore another key
        ak = self.other_key()
        sp, res = self.plan(t=2, key=ak, pubkey=keepsafe.admitted_key(self.home, PERSON))
        out = keepsafe.restore_walk(self.home, PERSON, {m: res['shares'][m] for m in MEMBERS[:2]})
        self.assertFalse(out['ok'])
        self.assertIsNone(out['key_text'])
        self.assertIn('is not %s\'s admitted key' % PERSON, out['said'])

    def test_admitted_key_is_the_persons(self):
        self.assertEqual(keepsafe.admitted_key(self.home, PERSON), record.pubkey_of(self.key))
        self.assertEqual(keepsafe.admitted_key(self.home, 'person:nobody'), '')

    def test_padded_recorded_byte_exact_with_two_newlines(self):
        data = self.key_bytes + b'\n'
        if len(data) % 2:
            data += b'\n'
        self.assertTrue(data.endswith(b'\n\n'))
        # the person's own key, written with a doubled trailing newline: still the admitted key
        with open(self.key, 'wb') as f:
            f.write(data)
        sp, res = self.plan(t=2)
        self.assertIs(sp['padded'], False)
        for r in res['lines']:
            self.assertIs(r['line']['body']['padded'], False)
        out = keepsafe.restore_walk(self.home, PERSON, {m: res['shares'][m] for m in MEMBERS[:2]})
        self.assertTrue(out['ok'], out['said'])
        self.assertEqual(out['key_text'].encode('utf-8'), data)
        self.assertEqual(out['basis'], 'padding as the share lines record it')

    def test_count_recorded_from_the_split(self):
        sp = keepsafe.split_key_file(self.key, 2, 5)
        res = keepsafe.share_lines(self.home, PERSON, MEMBERS[:3], [x['share'] for x in sp['shares'][:3]], 2,
                                   key_dir=self.keys, count=5)
        self.assertEqual({r['line']['body']['count'] for r in res['lines']}, {5})
        with self.assertRaises(ValueError):
            keepsafe.share_lines(self.home, PERSON, MEMBERS[:3], [x['share'] for x in sp['shares'][:3]], 2,
                                 key_dir=self.keys, count=2)

    def test_split_key_file(self):
        sp = keepsafe.split_key_file(self.key, 3, 5)
        self.assertEqual(sp['pubkey'], record.pubkey_of(self.key))
        self.assertEqual(sp['fingerprint'], record.key_id(sp['pubkey']))
        self.assertEqual(sp['padded'], len(self.key_bytes) % 2 == 1)
        for x in sp['shares']:
            self.assertEqual(x['digest'], hashlib.sha256(base64.b64decode(x['share'])).hexdigest())
        got = keepsafe.recover([base64.b64decode(x['share']) for x in sp['shares'][1:4]])
        self.assertEqual(keepsafe.unpad(got, sp['padded']), self.key_bytes)
        by_actor = keepsafe.split_key_file(PERSON, 2, 2, key_dir=self.keys)
        self.assertEqual(by_actor['pubkey'], sp['pubkey'])

    def test_odd_length_padding_recorded_and_reversed(self):
        for data in (b'x' * 33, b'y' * 34):
            p = os.path.join(self.tmp, 'secret-%d' % len(data))
            with open(p, 'wb') as f:
                f.write(data)
            sp = keepsafe.split_key_file(p, 2, 3)
            self.assertEqual(sp['padded'], len(data) % 2 == 1)
            got = keepsafe.recover([base64.b64decode(x['share']) for x in sp['shares'][:2]])
            self.assertEqual(len(got) % 2, 0)
            self.assertEqual(keepsafe.unpad(got, sp['padded']), data)

    def test_link_not_read(self):
        ln = os.path.join(self.tmp, 'link')
        os.symlink(self.key, ln)
        with self.assertRaisesRegex(ValueError, 'link'):
            keepsafe.split_key_file(ln, 2, 3)
        with self.assertRaises(ValueError):
            keepsafe.split_key_file(os.path.join(self.tmp, 'missing'), 2, 3)
        with self.assertRaises(ValueError):
            keepsafe.split_key_file(None, 2, 3)

    def test_share_lines_fields_and_signed(self):
        sp, res = self.plan()
        self.assertEqual(len(res['lines']), 5)
        self.assertEqual(sorted(res['shares']), sorted(MEMBERS))
        for i, r in enumerate(res['lines']):
            line = r['line']
            self.assertTrue(r['signed'])
            self.assertEqual((line['type'], line['actor'], line['for']), ('share', PERSON, PERSON))
            b = line['body']
            self.assertEqual((b['to'], b['threshold'], b['count'], b['index'], b['identifier']),
                             (MEMBERS[i], 3, 5, i, sp['identifier']))
            self.assertEqual(b['digest'], sp['shares'][i]['digest'])
            self.assertEqual(b['pubkey'], sp['pubkey'])
        self.assertEqual(len(keepsafe.share_records(self.home, PERSON)), 5)

    def test_share_value_never_enters_the_record(self):
        sp, res = self.plan()
        text = ''
        for root, _, files in os.walk(os.path.join(self.home, 'record')):
            for n in files:
                with open(os.path.join(root, n), encoding='utf-8') as f:
                    text += f.read()
        for x in sp['shares']:
            raw = base64.b64decode(x['share'])
            self.assertNotIn(x['share'], text)
            self.assertNotIn(raw[5:].hex(), text)
            self.assertNotIn(base64.b64encode(raw[5:]).decode(), text)
            self.assertNotIn(raw.hex(), text)
        for r in res['lines']:
            body = json.dumps(r['line']['body'])
            for x in sp['shares']:
                self.assertNotIn(x['share'], body)
                self.assertNotIn(x['share'][8:40], body)

    def test_share_lines_refusals(self):
        sp = keepsafe.split_key_file(self.key, 2, 3)
        sh = [x['share'] for x in sp['shares']]
        with self.assertRaises(ValueError):
            keepsafe.share_lines(self.home, PERSON, MEMBERS[:2], sh, 2, key_dir=self.keys)
        with self.assertRaises(ValueError):
            keepsafe.share_lines(self.home, PERSON, ['person:m1', 'person:m1', 'person:m2'], sh, 2, key_dir=self.keys)
        with self.assertRaises(ValueError):
            keepsafe.share_lines(self.home, PERSON, ['m1', 'person:m2', 'person:m3'], sh, 2, key_dir=self.keys)
        with self.assertRaisesRegex(ValueError, 'threshold'):
            keepsafe.share_lines(self.home, PERSON, MEMBERS[:3], sh, 3, key_dir=self.keys)
        with self.assertRaises(ValueError):
            keepsafe.share_lines(self.home, 'agent:aide', MEMBERS[:3], sh, 2, key_dir=self.keys)
        cell = os.path.join(self.tmp, 'cell')
        holon.init(cell, 'a-cell', 'cell', PERSON, ts=TS, salt='c', sign=False)
        with self.assertRaisesRegex(ValueError, 'own home'):
            keepsafe.share_lines(cell, PERSON, MEMBERS[:3], sh, 2, key_dir=self.keys)

    def test_restore_walk(self):
        sp, res = self.plan()
        before = sorted(os.listdir(self.tmp))
        given = {m: res['shares'][m] for m in MEMBERS[1:4]}
        out = keepsafe.restore_walk(self.home, PERSON, given, padded=sp['padded'])
        self.assertTrue(out['ok'], out['said'])
        self.assertEqual(out['key_text'].encode('utf-8'), self.key_bytes)
        self.assertEqual(out['pubkey'], sp['pubkey'])
        self.assertEqual([c['member'] for c in out['checked']], sorted(given))
        self.assertEqual(sorted(os.listdir(self.tmp)), before)   # nothing written without out_path
        recorded = keepsafe.restore_walk(self.home, PERSON, given)
        self.assertTrue(recorded['ok'])
        self.assertEqual(recorded['key_text'].encode('utf-8'), self.key_bytes)
        self.assertEqual(recorded['basis'], 'padding as the share lines record it')
        dest = os.path.join(self.tmp, 'restored')
        wrote = keepsafe.restore_walk(self.home, PERSON, given, out_path=dest, padded=sp['padded'])
        self.assertTrue(wrote['ok'])
        self.assertEqual(os.stat(dest).st_mode & 0o777, 0o600)
        with open(dest, 'rb') as f:
            self.assertEqual(f.read(), self.key_bytes)
        again = keepsafe.restore_walk(self.home, PERSON, given, out_path=dest)
        self.assertFalse(again['ok'])   # an existing file is never overwritten

    def test_restore_guesses_only_without_the_flag(self):
        sp, res = self.plan(padded=False)
        self.assertNotIn('padded', res['lines'][0]['line']['body'])
        out = keepsafe.restore_walk(self.home, PERSON, {m: res['shares'][m] for m in MEMBERS[:3]})
        self.assertTrue(out['ok'], out['said'])
        self.assertEqual(out['key_text'].encode('utf-8'), self.key_bytes)
        self.assertIn('was not given', out['basis'])

    def test_restore_refuses_and_names(self):
        sp, res = self.plan()
        bad = bytearray(base64.b64decode(res['shares'][MEMBERS[2]]))
        bad[20] ^= 1
        given = {MEMBERS[0]: res['shares'][MEMBERS[0]], MEMBERS[1]: res['shares'][MEMBERS[1]],
                 MEMBERS[2]: base64.b64encode(bytes(bad)).decode()}
        out = keepsafe.restore_walk(self.home, PERSON, given)
        self.assertFalse(out['ok'])
        self.assertIsNone(out['key_text'])
        named = {c['member']: c for c in out['checked']}
        self.assertFalse(named[MEMBERS[2]]['ok'])
        self.assertIn(MEMBERS[2], named[MEMBERS[2]]['said'])
        self.assertIn('digest', named[MEMBERS[2]]['said'])
        self.assertIn('needs 3', out['said'])
        swapped = {'person:stranger': res['shares'][MEMBERS[0]], MEMBERS[1]: res['shares'][MEMBERS[1]],
                   MEMBERS[2]: res['shares'][MEMBERS[2]]}
        out2 = keepsafe.restore_walk(self.home, PERSON, swapped)
        self.assertFalse(out2['ok'])
        self.assertIn('person:stranger', [c['member'] for c in out2['checked'] if not c['ok']])
        for empty in (None, {}, [], 3.5):
            self.assertFalse(keepsafe.restore_walk(self.home, PERSON, empty)['ok'])
        self.assertFalse(keepsafe.restore_walk(self.home, 'person:nobody', given)['ok'])
        self.assertFalse(keepsafe.restore_walk(os.path.join(self.tmp, 'missing'), PERSON, given)['ok'])
        self.assertFalse(keepsafe.restore_walk(self.home, PERSON, {MEMBERS[0]: 'not base64!'})['ok'])

    def test_cli(self):
        exe = [sys.executable, '-I', os.path.join(ENGINE, 'keepsafe.py')]
        r = subprocess.run(exe + ['split', self.key, '--threshold', '2', '--count', '3'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        sp = json.loads(r.stdout)
        r2 = subprocess.run(exe + ['recover'] + [x['share'] for x in sp['shares'][:2]],
                            capture_output=True, timeout=60)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(keepsafe.unpad(r2.stdout, sp['padded']), self.key_bytes)
        env = dict(os.environ, LIONSBERG_KEY_DIR=self.keys)
        r3 = subprocess.run(exe + ['plan', self.home, '--person', PERSON, '--members'] + MEMBERS[:3] +
                            ['--threshold', '2', '--key-dir', self.keys], capture_output=True, text=True,
                            timeout=60, env=env)
        self.assertEqual(r3.returncode, 0, r3.stderr)
        planned = json.loads(r3.stdout)
        args = ['--share', '%s=%s' % (MEMBERS[0], planned['shares'][MEMBERS[0]]),
                '--share', '%s=%s' % (MEMBERS[2], planned['shares'][MEMBERS[2]])]
        r4 = subprocess.run(exe + ['restore', self.home, '--person', PERSON] + args,
                            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r4.returncode, 0, r4.stderr)
        self.assertEqual(json.loads(r4.stdout)['key_text'].encode('utf-8'), self.key_bytes)
        r5 = subprocess.run(exe + ['recover', planned['shares'][MEMBERS[0]]], capture_output=True, text=True,
                            timeout=60)
        self.assertEqual(r5.returncode, 2)
        self.assertIn('needs 2', r5.stderr)
        self.assertIn('process list', r4.stderr)   # shares on the command line are warned of
        f = os.path.join(self.tmp, 'handed-back')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write('%s=%s\n%s=%s\n' % (MEMBERS[1], planned['shares'][MEMBERS[1]],
                                         MEMBERS[2], planned['shares'][MEMBERS[2]]))
        r6 = subprocess.run(exe + ['restore', self.home, '--person', PERSON, '--from', f],
                            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r6.returncode, 0, r6.stderr)
        self.assertNotIn('process list', r6.stderr)
        self.assertEqual(json.loads(r6.stdout)['key_text'].encode('utf-8'), self.key_bytes)


class TestKitWords(unittest.TestCase):
    def test_kit_words_and_no_names(self):
        with open(os.path.join(ENGINE, 'keepsafe.py'), encoding='utf-8') as f:
            src = f.read()
        for word in ('promise', 'house', 'estate', 'HQ'):
            self.assertIsNone(re.search(r'\b%s\b' % word, src, re.IGNORECASE if word != 'HQ' else 0), word)
        for word in ('person', 'member', 'cell', 'holon'):
            self.assertIn(word, src)
        self.assertNotIn('import requests', src)
        stdlib = {'argparse', 'base64', 'hashlib', 'hmac', 'json', 'os', 'shutil', 'sys', 'tempfile',
                  'unicodedata', 'record'}
        for m in re.findall(r'^import (\w+)', src, re.M):
            self.assertIn(m, stdlib)


if __name__ == '__main__':
    unittest.main()
