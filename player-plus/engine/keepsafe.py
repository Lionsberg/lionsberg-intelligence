"""keepsafe.py — recovery through the cell: a person's signing key split into shares held by the members of their cell.

A threshold of members can restore the key; fewer learn nothing of it. The split is made in the
same hour the key is made, so the first time a key is lost is not the first time recovery is tried.

The pattern is Blockchain Commons' SSKR (BCR-2020-011) for the share's layout, with the Shamir
scheme of SLIP-39 beneath it: GF(256) under the Rijndael polynomial, each byte shared on its own,
the secret at x = 255 and a digest share at x = 254. One group for now.

The record keeps who holds which share and the sha256 of it (a `share` line per member, in the
person's own home); the share bytes themselves never enter the record. They go to each member by a
transport the person chooses.

Standard library only. The field and the scheme are pure functions, deterministic given an rng.

    python3 -I keepsafe.py split KEYFILE --threshold 3 --count 5
    python3 -I keepsafe.py recover SHARE... [--from FILE] [--out PATH]
    python3 -I keepsafe.py plan HOLON --person person:x --members a b c d e --threshold 3
    python3 -I keepsafe.py restore HOLON --person person:x --share actor=base64 ... [--out PATH]
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import record  # noqa: E402

# ---------------------------------------------------------------- the method's own constants (each sourced)

POLY = 0x11b             # x^8 + x^4 + x^3 + x + 1, the Rijndael polynomial (SLIP-39, "Shamir's secret-sharing")
SECRET_X = 255           # the shared secret is f(255) (SLIP-39)
DIGEST_X = 254           # the digest share is f(254) (SLIP-39)
DIGEST_LEN = 4           # the digest is the first 4 bytes of HMAC-SHA256(key=R, msg=S) (SLIP-39)
MIN_SECRET = 16          # at least 128 bits, a multiple of 16 bits (SLIP-39)
MAX_MEMBERS = 16         # member-index and member-threshold are 4-bit fields (BCR-2020-011)
HEADER_LEN = 5           # identifier 16 · GT-1 4 · GC-1 4 · group-index 4 · MT-1 4 · reserved 4 · member-index 4
PAD = b'\n'              # an odd-length key file is padded with one trailing newline, and says so

# ---------------------------------------------------------------- GF(256)


def _byte(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255:
        raise ValueError('%s must be a whole number from 0 to 255' % what)
    return v


def gf_mul(a, b):
    """a times b in GF(256) under the Rijndael polynomial (0x11b)."""
    a, b = _byte(a, 'a'), _byte(b, 'b')
    p = 0
    while b:
        if b & 1:
            p ^= a
        a <<= 1
        if a & 0x100:
            a ^= POLY
        b >>= 1
    return p


def gf_inv(a):
    """The inverse of a nonzero a in GF(256): a^254, since a^255 = 1."""
    if _byte(a, 'a') == 0:
        raise ValueError('zero has no inverse in GF(256)')
    r, base, e = 1, a, 254
    while e:
        if e & 1:
            r = gf_mul(r, base)
        base = gf_mul(base, base)
        e >>= 1
    return r


def gf_div(a, b):
    """a divided by b in GF(256); b must not be zero."""
    if _byte(b, 'b') == 0:
        raise ValueError('division by zero in GF(256)')
    return gf_mul(_byte(a, 'a'), gf_inv(b))


def interpolate(x, points):
    """The value at x of the polynomial through `points`, a list of (xi, bytes), each byte on its own.

    Lagrange's form in GF(256), where subtraction is XOR. The xi must be distinct and the values
    of one length. Returns bytes."""
    x = _byte(x, 'x')
    pts = list(points or [])
    if not pts:
        raise ValueError('interpolation needs at least one point')
    xs = [_byte(p[0], 'a point\'s x') for p in pts]
    if len(set(xs)) != len(xs):
        raise ValueError('two points share an x; each share must be a different member')
    if any(not isinstance(p[1], (bytes, bytearray)) for p in pts):
        raise ValueError('each point\'s value must be bytes')
    vals = [bytes(p[1]) for p in pts]
    n = len(vals[0])
    if any(len(v) != n for v in vals):
        raise ValueError('the points\' values differ in length')
    out = bytearray(n)
    for i, xi in enumerate(xs):
        num, den = 1, 1
        for j, xj in enumerate(xs):
            if j != i:
                num = gf_mul(num, x ^ xj)
                den = gf_mul(den, xi ^ xj)
        basis = gf_div(num, den)
        if basis:
            vi = vals[i]
            for k in range(n):
                out[k] ^= gf_mul(basis, vi[k])
    return bytes(out)


# ---------------------------------------------------------------- the scheme (SLIP-39's Shamir, one group)


def _digest(r, secret):
    return hmac.new(r, secret, hashlib.sha256).digest()[:DIGEST_LEN]


def _rand(rng, n):
    b = rng(n)
    if not isinstance(b, (bytes, bytearray)) or len(b) != n:
        raise ValueError('the rng must return exactly %d bytes' % n)
    return bytes(b)


def _count(v, what):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError('%s must be a whole number' % what)
    return v


def _check_secret(secret):
    if not isinstance(secret, (bytes, bytearray)):
        raise ValueError('the secret must be bytes')
    if len(secret) < MIN_SECRET:
        raise ValueError('the secret must be at least %d bytes (128 bits)' % MIN_SECRET)
    if len(secret) % 2:
        raise ValueError('the secret must be an even number of bytes (a multiple of 16 bits)')
    return bytes(secret)


def header(identifier, threshold, count, index, group_threshold=1, group_count=1, group_index=0):
    """The 5-byte SSKR header, laid out bit-exactly as BCR-2020-011."""
    return bytes([(identifier >> 8) & 0xff, identifier & 0xff,
                  ((group_threshold - 1) & 0xf) << 4 | ((group_count - 1) & 0xf),
                  (group_index & 0xf) << 4 | ((threshold - 1) & 0xf),
                  index & 0xf])


def parse(share):
    """A share's header and value: {"identifier", "group_threshold", "group_count", "group_index",
    "threshold", "reserved", "index", "value"}. Raises ValueError in words on a malformed share."""
    if not isinstance(share, (bytes, bytearray)):
        raise ValueError('a share must be bytes')
    s = bytes(share)
    if len(s) < HEADER_LEN + MIN_SECRET:
        raise ValueError('a share is a 5-byte header and a value of at least %d bytes; this one is %d bytes'
                         % (MIN_SECRET, len(s)))
    h = {'identifier': s[0] << 8 | s[1],
         'group_threshold': (s[2] >> 4) + 1, 'group_count': (s[2] & 0xf) + 1,
         'group_index': s[3] >> 4, 'threshold': (s[3] & 0xf) + 1,
         'reserved': s[4] >> 4, 'index': s[4] & 0xf, 'value': s[HEADER_LEN:]}
    if h['reserved']:
        raise ValueError('the share\'s reserved bits are not zero; it is not an SSKR share')
    if h['group_threshold'] != 1 or h['group_count'] != 1 or h['group_index'] != 0:
        raise ValueError('the share belongs to a split of several groups; this kit reads one group only')
    if h['threshold'] > MAX_MEMBERS:
        raise ValueError('the share names a threshold beyond %d' % MAX_MEMBERS)
    return h


def split(secret, threshold, count, identifier=None, rng=os.urandom):
    """SSKR shares of `secret` for one group (group-threshold 1, group-count 1, group-index 0).

    `threshold` of the `count` shares restore the secret. The identifier (16 bits, the same on every
    share) is drawn from rng when not given. Each share is header ‖ value as BCR-2020-011 lays it
    out; the value is SLIP-39's Shamir split of the secret, with the digest share at x = 254.
    Raises ValueError in words."""
    secret = _check_secret(secret)
    threshold, count = _count(threshold, 'the threshold'), _count(count, 'the count')
    if not 1 <= threshold <= count <= MAX_MEMBERS:
        raise ValueError('the threshold and count must satisfy 1 <= threshold <= count <= %d' % MAX_MEMBERS)
    if identifier is None:
        idb = _rand(rng, 2)
        identifier = idb[0] << 8 | idb[1]
    identifier = _count(identifier, 'the identifier')
    if not 0 <= identifier <= 0xffff:
        raise ValueError('the identifier is 16 bits: 0 to 65535')
    n = len(secret)
    if threshold == 1:
        values = [secret] * count
    else:
        r = _rand(rng, n - DIGEST_LEN)
        base = [(i, _rand(rng, n)) for i in range(threshold - 2)]
        base += [(DIGEST_X, _digest(r, secret) + r), (SECRET_X, secret)]
        values = [v for _, v in base[:threshold - 2]]
        values += [interpolate(i, base) for i in range(threshold - 2, count)]
    return [header(identifier, threshold, count, i) + values[i] for i in range(count)]


def recover(shares):
    """The secret from at least a threshold of shares of one split. Raises ValueError in words when
    the shares disagree (identifier, threshold, length), repeat a member, are fewer than the
    threshold, or fail SLIP-39's digest check."""
    items = list(shares or [])
    if not items:
        raise ValueError('no shares were given')
    hs = [parse(s) for s in items]
    first = hs[0]
    for h in hs[1:]:
        if h['identifier'] != first['identifier']:
            raise ValueError('the shares come from different splits (their identifiers differ)')
        if h['threshold'] != first['threshold']:
            raise ValueError('the shares disagree on the threshold')
        if len(h['value']) != len(first['value']):
            raise ValueError('the shares differ in length')
    seen = {}
    for h in hs:
        if h['index'] in seen and seen[h['index']] != h['value']:
            raise ValueError('two different shares claim member index %d' % h['index'])
        seen[h['index']] = h['value']
    t = first['threshold']
    if len(seen) < t:
        raise ValueError('%d share%s given; this split needs %d to restore the secret'
                         % (len(seen), '' if len(seen) == 1 else 's', t))
    pts = sorted(seen.items())[:t]
    if t == 1:   # every share is the secret itself, so every further share must equal the first
        for x, v in sorted(seen.items())[1:]:
            if v != pts[0][1]:
                raise ValueError('member index %d\'s share does not agree with the others; it has been changed' % x)
        return pts[0][1]
    secret = interpolate(SECRET_X, pts)
    d = interpolate(DIGEST_X, pts)
    if not hmac.compare_digest(d[:DIGEST_LEN], _digest(d[DIGEST_LEN:], secret)):
        raise ValueError('the digest check failed: a share has been changed, or the shares do not belong together')
    if len(seen) > t:   # every further share must lie on the same polynomial
        for x, v in sorted(seen.items())[t:]:
            if interpolate(x, pts) != v:
                raise ValueError('member index %d\'s share does not agree with the others; it has been changed' % x)
    return secret


# ---------------------------------------------------------------- the key file


def sha256_hex(b):
    return hashlib.sha256(bytes(b)).hexdigest()


def b64(b):
    return base64.b64encode(bytes(b)).decode('ascii')


def unb64(text):
    """Bytes from base64 text, or ValueError in words."""
    if isinstance(text, (bytes, bytearray)):
        return bytes(text)
    if not isinstance(text, str):
        raise ValueError('a share is bytes or base64 text')
    try:
        return base64.b64decode(unicodedata.normalize('NFC', text).strip(), validate=True)
    except (ValueError, TypeError):
        raise ValueError('a share is not valid base64 text')


def _read_regular(path):
    """A regular file's bytes, never through a link; ValueError in words otherwise."""
    if not isinstance(path, str) or not path:
        raise ValueError('no key file was named')
    if os.path.islink(path):
        raise ValueError('the key file is a link; a link is not read')
    if not os.path.isfile(path):
        raise ValueError('no key file at %r' % path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        return f.read()


def split_key_file(key_path, threshold, count, key_dir=None, identifier=None, rng=os.urandom):
    """Split a private key file into SSKR shares.

    `key_path` is the file, or an actor id whose key `record.find_key` finds (in `key_dir` when
    named). The secret is the file's bytes; an odd length is padded with one trailing newline and
    `padded` says so, so the padding is undone at restore. Returns {"shares": [{"index", "share",
    "digest"}], "threshold", "count", "identifier", "pubkey", "fingerprint", "padded", "said"}:
    each share as base64 text with the sha256 hex of its bytes."""
    path = key_path
    if isinstance(key_path, str) and (key_path.startswith('person:') or key_path.startswith('agent:')):
        path = record.find_key(None, key_path, key_dir)
        if not path:
            raise ValueError('no key named %s was found' % record.key_name(key_path))
    data = _read_regular(path)
    padded = len(data) % 2 == 1
    secret = data + PAD if padded else data
    shares = split(secret, threshold, count, identifier=identifier, rng=rng)
    pub = record.pubkey_of(path)
    out = {'shares': [{'index': i, 'share': b64(s), 'digest': sha256_hex(s)} for i, s in enumerate(shares)],
           'threshold': threshold, 'count': count, 'identifier': parse(shares[0])['identifier'],
           'pubkey': pub, 'fingerprint': record.key_id(pub), 'padded': padded,
           'said': '%d of %d members restore the key%s' % (threshold, count,
                                                           '; one trailing newline was added to make its length even'
                                                           if padded else '')}
    if not pub:
        out['said'] += '; its public key could not be read (ssh-keygen is needed), so a restore cannot be checked'
    return out


def unpad(secret, padded):
    """The key file's bytes from a recovered secret: one trailing newline removed when `padded`."""
    if padded and secret.endswith(PAD):
        return secret[:-len(PAD)]
    return secret


# ---------------------------------------------------------------- the record's side


def _actor(a):
    return isinstance(a, str) and (a.startswith('person:') or a.startswith('agent:')) and len(a.split(':', 1)[1]) > 0


def share_lines(holon_dir, person, members, shares, threshold, ts=None, sign=None, key_dir=None, pubkey=None,
                consent=None, padded=None, count=None):
    """One `share` line per member, written by the person into their own home.

    Each line carries `to` (the member), `threshold`, `count`, `index`, `identifier`, `digest`
    (sha256 hex of that member's share bytes), `pubkey` (the key the shares restore; given, else
    the person's own found by `record.find_key`) and, when given, `padded` (the split's flag). `count`
    is the split's count (the header does not carry it), else the number of shares given. The share
    value never enters the record.
    Returns {"lines": [record.append results], "shares": {member: base64}, "said"}: the shares are
    for the caller to hand to each member by a transport the person chooses."""
    if not isinstance(person, str) or not person.startswith('person:'):
        raise ValueError('the person is person:<handle>')
    ms = list(members or [])
    sh = [unb64(s) for s in (shares or [])]
    if not ms or len(ms) != len(sh):
        raise ValueError('one member for each share: %d members, %d shares' % (len(ms), len(sh)))
    for m in ms:
        if not _actor(m):
            raise ValueError('a member is person:<handle> or agent:<handle>; %r is not' % (m,))
    if len(set(ms)) != len(ms):
        raise ValueError('a member is named twice; each holds one share')
    hs = [parse(s) for s in sh]
    if len({h['identifier'] for h in hs}) != 1 or len({len(h['value']) for h in hs}) != 1:
        raise ValueError('the shares do not come from one split')
    if any(h['threshold'] != _count(threshold, 'the threshold') for h in hs):
        raise ValueError('the threshold given differs from the shares\' own (%d)' % hs[0]['threshold'])
    if len({h['index'] for h in hs}) != len(hs):
        raise ValueError('two shares carry the same member index')
    if count is None:
        count = len(sh)
    if _count(count, 'the count') < len(sh) or count > MAX_MEMBERS:
        raise ValueError('the split\'s count must be at least the number of shares given, and at most %d' % MAX_MEMBERS)
    if padded is not None and not isinstance(padded, bool):
        raise ValueError('padded is true or false')
    if not pubkey:
        k = record.find_key(None, person, key_dir)
        pubkey = record.pubkey_of(k) if k else ''
    if not pubkey:
        raise ValueError('no public key for %s: the shares must name the key they restore' % person)
    out, hand = [], {}
    for m, s, h in sorted(zip(ms, sh, hs), key=lambda z: z[2]['index']):
        body = {'to': m, 'threshold': h['threshold'], 'count': count, 'index': h['index'],
                'identifier': h['identifier'], 'digest': sha256_hex(s), 'pubkey': pubkey}
        if padded is not None:
            body['padded'] = padded
        if consent:
            body['consent'] = consent
        out.append(record.append(holon_dir, person, person, 'share', body, ts=ts, sign=sign, key_dir=key_dir))
        hand[m] = b64(s)
    return {'lines': out, 'shares': hand,
            'said': '%d share lines written; hand each member their share by a transport the person chooses'
                    % len(out)}


TRUSTED_HERE = ('signed', 'home')   # what the fold trusts in the person's own record (record.TRUSTED, less 'vouched')


def _folded(holon_dir):
    """The holon read and folded as the reader's own home: (read, fold)."""
    r = record.read(holon_dir)
    for l in r['lines']:
        if str(l.get('_file', '')).startswith('record/'):
            l['_home_record'] = True
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    tp = os.path.join(holon_dir, 'types.json') if isinstance(holon_dir, str) else None
    types = record.load_types(tp if tp and os.path.isfile(tp) and not os.path.islink(tp) else None)
    return r, record.fold(r['lines'], types, keepers)


def admitted_key(holon_dir, person, folded=None):
    """The person's admitted public key in this holon, from the fold, or ''."""
    r, f = folded or _folded(holon_dir)
    e = ((f.get('admitted') or {}).get(r['holon']) or {}).get(person) if r['holon'] else None
    return str(e.get('pubkey') or '') if isinstance(e, dict) else ''


def share_records(holon_dir, person, folded=None):
    """The person's `share` lines in this holon that the fold trusts (signed, or at the paper floor of
    the home), from their own actor file in record/ only."""
    if not isinstance(person, str) or not person.startswith('person:'):
        return []
    want = 'record/' + record.actor_file(person)
    r, f = folded or _folded(holon_dir)
    trust = f.get('trust') or {}
    return [l for l in r['lines'] if l.get('type') == 'share' and l.get('_file') == want
            and l.get('actor') == person and l.get('for') == person and isinstance(l.get('body'), dict)
            and trust.get(l['id']) in TRUSTED_HERE]


def _pubkey_of_text(key_bytes):
    """The public half of a private key given as bytes, through a temporary file removed at once."""
    d = tempfile.mkdtemp(prefix='keepsafe-')
    try:
        os.chmod(d, 0o700)
        p = os.path.join(d, 'key')
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key_bytes)
        return record.pubkey_of(p) if shutil.which('ssh-keygen') else ''
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)


def restore_walk(holon_dir, person, shares_given, out_path=None, padded=None):
    """Restore a person's key from the shares their members hand back.

    Reads the person's `share` lines; checks each given share's sha256 against its member's line
    (a share whose digest does not match is refused and named); recovers; checks the recovered
    key's public half against the line's `pubkey` and against the person's key admitted in the
    holon (a key that is not the admitted one is refused). Only share lines the fold trusts are read.
    Returns {"ok", "said", "key_text", "checked":
    [{"member", "ok", "said"}], "pubkey", "basis"}. Writes nothing to disk unless `out_path` is
    given (a new file, mode 0600); the check uses a temporary file removed at once. `padded` is
    the split's flag, else the lines' own `padded`; only for lines without it does a recovered key
    ending in two newlines lose one, on the basis that OpenSSH key text ends with one, said in `basis`."""
    out = {'ok': False, 'said': '', 'key_text': None, 'checked': [], 'pubkey': None, 'basis': None}
    folded = _folded(holon_dir)
    lines = share_records(holon_dir, person, folded)
    if not lines:
        out['said'] = 'no share lines by %s that this holon trusts' % person
        return out
    admitted = admitted_key(holon_dir, person, folded)
    if not admitted:
        out['said'] = '%s has no key admitted in this holon; there is no key to restore' % person
        return out
    given = shares_given if isinstance(shares_given, dict) else {}
    parsed = {}
    for m in sorted(given, key=str):
        try:
            b = unb64(given[m])
            parsed[m] = (b, parse(b))
        except ValueError as e:
            out['checked'].append({'member': m, 'ok': False, 'said': str(e)})
    if not parsed:
        out['said'] = 'no readable share was given'
        return out
    ids = sorted({h['identifier'] for _, h in parsed.values()})
    # the split to restore: the one the given shares name, its newest lines winning a tie
    by_member = {}
    for l in lines:
        b = l['body']
        if b.get('identifier') in ids:
            by_member[(b.get('identifier'), b.get('to'))] = l
    accepted, pubkeys, flags = [], set(), set()
    for m in sorted(parsed):
        b, h = parsed[m]
        l = by_member.get((h['identifier'], m))
        if not l:
            out['checked'].append({'member': m, 'ok': False,
                                   'said': 'no share line names %s for this split; refused' % m})
            continue
        if not hmac.compare_digest(sha256_hex(b), str(l['body'].get('digest'))):
            out['checked'].append({'member': m, 'ok': False,
                                   'said': '%s\'s share does not match its digest in the record; refused' % m})
            continue
        if h['index'] != l['body'].get('index'):
            out['checked'].append({'member': m, 'ok': False,
                                   'said': '%s\'s share carries another member index than the record names; refused' % m})
            continue
        out['checked'].append({'member': m, 'ok': True, 'said': 'matches its digest in the record'})
        accepted.append(b)
        pubkeys.add(str(l['body'].get('pubkey')))
        flags.add(l['body'].get('padded') if isinstance(l['body'].get('padded'), bool) else None)
    out['checked'].sort(key=lambda c: str(c['member']))
    if len(pubkeys) > 1:
        out['said'] = 'the accepted shares name different keys; nothing restored'
        return out
    if not accepted:
        out['said'] = 'no given share matched the record'
        return out
    if pubkeys != {admitted}:
        out['said'] = 'the share lines name a key that is not %s\'s admitted key; nothing restored' % person
        return out
    if padded is None and len(flags) > 1:
        out['said'] = 'the share lines disagree on padding; nothing restored'
        return out
    try:
        secret = recover(accepted)
    except ValueError as e:
        out['said'] = str(e)
        return out
    if padded is None and flags != {None}:
        padded = flags.pop()
        out['basis'] = 'padding as the share lines record it'
    if padded is None:
        padded = secret.endswith(PAD + PAD)
        out['basis'] = ('the padding flag was not given; one trailing newline was %s, since OpenSSH key text ends '
                        'with one' % ('removed' if padded else 'kept'))
    key = unpad(secret, padded)
    want = pubkeys.pop()
    out['pubkey'] = want
    got = _pubkey_of_text(key)
    if not got:
        out['said'] = 'the key was recovered but its public half could not be read (ssh-keygen is needed); not returned'
        return out
    if got != want:   # want is the admitted key, checked above
        out['said'] = 'the recovered key is not %s\'s admitted key; nothing returned' % person
        return out
    try:
        text = key.decode('utf-8')
    except UnicodeDecodeError:
        out['said'] = 'the recovered key is not text; nothing returned'
        return out
    if out_path:
        try:
            _write_new(out_path, key)
        except OSError as e:
            out['said'] = 'the key was restored but could not be written to %s (%s); nothing written' % (out_path, e)
            return out
    out.update(ok=True, key_text=text,
               said='the key is restored and its public half matches the record' +
                    ('; written to %s' % out_path if out_path else ''))
    return out


# ---------------------------------------------------------------- CLI


def _dump(obj):
    print(json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='keepsafe.py', description='Recovery through the cell: SSKR shares of a signing key.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('split', help='split a key file into shares')
    s.add_argument('keyfile')
    s.add_argument('--threshold', type=int, required=True)
    s.add_argument('--count', type=int, required=True)
    r = sub.add_parser('recover', help='recover a secret from shares')
    r.add_argument('shares', nargs='*')
    r.add_argument('--from', dest='from_file')
    r.add_argument('--out')
    p = sub.add_parser('plan', help='split the person\'s own key, write the share lines, print the shares to hand out')
    p.add_argument('holon')
    p.add_argument('--person', required=True)
    p.add_argument('--members', nargs='+', required=True)
    p.add_argument('--threshold', type=int, required=True)
    p.add_argument('--key-dir')
    p.add_argument('--no-sign', action='store_true')
    t = sub.add_parser('restore', help='restore the person\'s key from the shares handed back')
    t.add_argument('holon')
    t.add_argument('--person', required=True)
    t.add_argument('--share', action='append', default=[], help='member=base64 (visible to the process list)')
    t.add_argument('--from', dest='from_file', help='a file of member=base64 lines, one per member')
    t.add_argument('--padded', choices=('yes', 'no'))
    t.add_argument('--out')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'split':
            _dump(split_key_file(a.keyfile, a.threshold, a.count))
            return 0
        if a.cmd == 'recover':
            items = list(a.shares)
            if a.from_file:
                items += [x for x in _read_regular(a.from_file).decode('utf-8').split() if x]
            secret = recover([unb64(x) for x in items])
            if a.out:
                _write_new(a.out, secret)
                _dump({'ok': True, 'said': 'written to %s' % a.out})
            else:
                sys.stdout.write(secret.decode('utf-8', errors='replace'))
            return 0
        if a.cmd == 'plan':
            k = record.find_key(None, a.person, a.key_dir)
            if not k:
                raise ValueError('no key named %s was found' % record.key_name(a.person))
            sp = split_key_file(k, a.threshold, len(a.members))
            res = share_lines(a.holon, a.person, a.members, [x['share'] for x in sp['shares']], a.threshold,
                              sign=False if a.no_sign else None, key_dir=a.key_dir, pubkey=sp['pubkey'] or None,
                              padded=sp['padded'], count=sp['count'])
            _dump({'lines': [x['line']['id'] for x in res['lines']], 'signed': [x['signed'] for x in res['lines']],
                   'shares': res['shares'], 'padded': sp['padded'], 'fingerprint': sp['fingerprint'],
                   'said': res['said']})
            return 0
        if a.cmd == 'restore':
            given = {}
            items = list(a.share)
            if items:
                print('keepsafe: shares given on the command line are visible to the process list; '
                      '--from FILE keeps them out of it', file=sys.stderr)
            if a.from_file:
                items += [x for x in _read_regular(a.from_file).decode('utf-8').split() if x]
            for x in items:
                if '=' not in x:
                    raise ValueError('a share is given as member=base64')
                m, v = x.split('=', 1)
                given[m] = v
            padded = None if a.padded is None else a.padded == 'yes'
            res = restore_walk(a.holon, a.person, given, out_path=a.out, padded=padded)
            if a.out:
                res['key_text'] = None if not res['ok'] else '(written to %s)' % a.out
            _dump(res)
            return 0 if res['ok'] else 1
    except (ValueError, OSError) as e:
        print('keepsafe: %s' % e, file=sys.stderr)
        return 2
    return 2


if __name__ == '__main__':
    sys.exit(main())
