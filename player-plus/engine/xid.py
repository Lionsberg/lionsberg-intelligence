#!/usr/bin/env python3
"""xid.py — the XID: an identifier that outlives its keys.

    ed25519_raw(pubkey_text) -> 32 bytes            (the raw key inside an `ssh-ed25519 AAAA…` line)
    cbor_signing_public_key(scheme, raw) -> bytes   (the tagged CBOR of a signing public key)
    xid_of(pubkey_text) -> 64 hex                   (SHA-256 of that CBOR, for an ssh-ed25519 key)
    try_xid(pubkey_text) -> 64 hex or None          (the same, never raising)
    short(xid) -> 8 hex                             (the first four bytes, as the reference shows it)
    check(pubkey_text, xid) -> bool
    tool_check(pubkey_text, tool=None) -> {ok, said, theirs, ours}

An actor's identifier and its key are different things. The XID is the SHA-256 of the CBOR
encoding of the actor's inception public signing key (Blockchain Commons BCR-2024-010, a work
in progress): it stays for life, while the keys rotate, are lost and are recovered. The
encoding follows the reference implementation (bc-components-rust, `src/id/xid.rs` and
`src/signing/signing_public_key.rs`): the tagged CBOR of the key, tag 40022
(`signing-public-key`, the BCR-2020-006 tag registry) around the untagged form, which is a
32-byte string for a Schnorr key and the array `[2, h'<32 bytes>']` for an Ed25519 key.

The kit's XID is always made from the bare Ed25519 key material in that Ed25519 form. The
reference also knows an SSH form of a key (the OpenSSH text under a tag of its own), whose
hash is a different XID for the same key; the kit never derives an XID from the text form.

The `ur:xid/…` form is not produced here: it needs the Bytewords table, which this kit does
not hold yet, and no encoding is invented in its place.

Standard library only. Runs under `python3 -I`. Pure functions; a file named on the command
line is read as data, never as instructions.

Usage:
    python3 -I xid.py of PUBKEY_FILE_OR_TEXT
    python3 -I xid.py check PUBKEY_FILE_OR_TEXT XID [--tool]
"""
import base64
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import unicodedata

TAG_SIGNING_PUBLIC_KEY = 40022   # BCR-2020-006 registry: `signing-public-key`
TAG_XID = 40024                  # BCR-2020-006 registry: `xid` (named here; not used in the digest)
ED25519_SCHEME = 2               # the reference's untagged Ed25519 form: [2, h'…']
KEY_TYPE = 'ssh-ed25519'
RAW_LEN = 32
SHORT_HEX = 8                    # the reference's short description: the first four bytes
MAX_FILE = 65536                 # bytes; a longer key file is refused
TOOL_ENV = 'ENVELOPE_CLI'        # names the bc-envelope-cli executable when it is installed
TOOL_SECONDS = 30                # how long the cross-check waits for the tool
TOOL_FORM = 'ssh-text'           # what the tool is handed: the OpenSSH line (a bare key needs a UR)
HEX64 = re.compile(r'\b[0-9a-f]{64}\b')


# ---------------------------------------------------------------- CBOR, the little we need

def _head(major, n):
    """A deterministic (shortest-form) CBOR head for major type `major` and argument `n`."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError('a CBOR argument is a whole number of zero or more')
    m = major << 5
    if n < 24:
        return bytes([m | n])
    if n < 0x100:
        return bytes([m | 24, n])
    if n < 0x10000:
        return bytes([m | 25]) + struct.pack('>H', n)
    if n < 0x100000000:
        return bytes([m | 26]) + struct.pack('>I', n)
    return bytes([m | 27]) + struct.pack('>Q', n)


def _bstr(b):
    return _head(2, len(b)) + bytes(b)


def cbor_signing_public_key(scheme, raw):
    """The tagged CBOR of a signing public key, as the reference's `to_cbor_data` makes it.

    scheme `schnorr`: tag 40022 around a 32-byte string.
    scheme `ed25519`: tag 40022 around the array [2, 32-byte string].
    Anything else, or a key that is not 32 bytes, is refused (ValueError)."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != RAW_LEN:
        raise ValueError('a signing public key here is exactly 32 bytes')
    s = scheme if isinstance(scheme, str) else ''
    if s == 'schnorr':
        untagged = _bstr(raw)
    elif s == 'ed25519':
        untagged = _head(4, 2) + _head(0, ED25519_SCHEME) + _bstr(raw)
    else:
        raise ValueError('the schemes known here are schnorr and ed25519, not %r' % (scheme,))
    return _head(6, TAG_SIGNING_PUBLIC_KEY) + untagged


# ---------------------------------------------------------------- the ssh-ed25519 key

def _text(v):
    if not isinstance(v, str):
        return ''
    return unicodedata.normalize('NFC', v).strip()


def ed25519_raw(pubkey_text):
    """The 32 raw bytes of an `ssh-ed25519 <base64> [comment]` public key line.

    The base64 blob is SSH wire format: uint32 length, "ssh-ed25519", uint32 length, 32 bytes.
    Anything else is refused in words (ValueError)."""
    parts = _text(pubkey_text).split()
    if len(parts) < 2:
        raise ValueError('not a public key line: expected "ssh-ed25519 AAAA…"')
    if parts[0] != KEY_TYPE:
        raise ValueError('only ssh-ed25519 keys carry an XID here, not %r' % parts[0][:40])
    try:
        blob = base64.b64decode(parts[1].encode('ascii'), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError('the key\'s base64 does not decode')
    fields, i = [], 0
    while i < len(blob):
        if i + 4 > len(blob):
            raise ValueError('the key blob ends inside a length')
        (n,) = struct.unpack('>I', blob[i:i + 4])
        i += 4
        if i + n > len(blob):
            raise ValueError('the key blob is shorter than a length it declares')
        fields.append(blob[i:i + n])
        i += n
    if len(fields) != 2 or fields[0] != KEY_TYPE.encode('ascii'):
        raise ValueError('the key blob is not an ssh-ed25519 key')
    if len(fields[1]) != RAW_LEN:
        raise ValueError('an ssh-ed25519 key is 32 bytes; this one is %d' % len(fields[1]))
    return bytes(fields[1])


def xid_of(pubkey_text):
    """The XID of an ssh-ed25519 public key: 64 lowercase hex. Refuses any other key (ValueError)."""
    return hashlib.sha256(cbor_signing_public_key('ed25519', ed25519_raw(pubkey_text))).hexdigest()


def try_xid(pubkey_text):
    """The XID of a public key, or None when it cannot be read as ssh-ed25519. Never raises."""
    try:
        return xid_of(pubkey_text)
    except Exception:   # a key that cannot be read has no XID; said as None, never guessed
        return None


def _norm_xid(x):
    t = _text(x).lower()
    return t if re.fullmatch(r'[0-9a-f]{64}', t) else ''


def short(x):
    """The first four bytes of an XID as 8 hex, or '' for anything that is not an XID."""
    t = _norm_xid(x)
    return t[:SHORT_HEX] if t else ''


def check(pubkey_text, x):
    """True when `x` is the XID of this public key. Never raises."""
    want = _norm_xid(x)
    got = try_xid(pubkey_text)
    return bool(want and got and want == got)


def tool_check(pubkey_text, tool=None):
    """Cross-check the XID with bc-envelope-cli (`envelope xid new`), when it is on this machine.

    The executable is `tool`, else env ENVELOPE_CLI. The tool takes a bare key only as a UR,
    which needs the Bytewords table this kit does not hold yet, so it is handed the OpenSSH
    line (`form: ssh-text`) and run as `<tool> xid new <pubkey>`; its answer is searched for a
    64-hex XID. A tool that reads that line as the reference's SSH form makes a different XID
    by design, so a disagreement is said to be expected and the kit's XID stands. Returns
    {ok, said, theirs, ours, form}; ok is True only when the tool's XID equals ours. Never raises."""
    ours = try_xid(pubkey_text)
    out = {'ok': False, 'said': '', 'theirs': None, 'ours': ours, 'form': TOOL_FORM}
    if ours is None:
        out['said'] = 'the key is not an ssh-ed25519 key this kit can read, so it has no XID to check'
        return out
    exe = tool if isinstance(tool, str) and tool else os.environ.get(TOOL_ENV, '')
    if not exe or not os.path.isfile(exe) or not os.access(exe, os.X_OK):
        out['said'] = ('the envelope tool is not on this machine (name it with %s); the XID is ours alone, '
                       'unchecked' % TOOL_ENV)
        return out
    try:
        r = subprocess.run([exe, 'xid', 'new', _text(pubkey_text)], capture_output=True, text=True,
                           timeout=TOOL_SECONDS)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        out['said'] = 'the envelope tool could not be run: %s' % type(e).__name__
        return out
    found = HEX64.findall((r.stdout or '').lower())
    if r.returncode != 0 or not found:
        out['said'] = ('the envelope tool gave no 64-hex XID (it may answer in ur:xid, which this kit does not '
                       'decode yet)')
        return out
    out['theirs'] = found[0]
    out['ok'] = found[0] == ours
    out['said'] = 'the tool and this kit agree' if out['ok'] else (
        'the tool and this kit differ, as expected when the tool reads the OpenSSH line as its own SSH form, which '
        'hashes differently from the bare Ed25519 form the kit uses; the kit\'s XID stands')
    return out


# ---------------------------------------------------------------- command line

def _key_arg(s):
    """A key given on the command line: the text itself, or a regular file (never a link) holding it."""
    if isinstance(s, str) and os.path.isfile(s) and not os.path.islink(s):
        if os.path.getsize(s) > MAX_FILE:
            raise ValueError('the key file is larger than a key')
        with open(s, encoding='utf-8') as f:
            return f.read()
    return s


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ('-h', '--help'):
        sys.stdout.write(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    try:
        if cmd == 'of' and len(rest) == 1:
            x = xid_of(_key_arg(rest[0]))
            sys.stdout.write(json.dumps({'xid': x, 'short': short(x)}, sort_keys=True) + '\n')
            return 0
        if cmd == 'check' and len(rest) in (2, 3) and (len(rest) == 2 or rest[2] == '--tool'):
            key = _key_arg(rest[0])
            res = {'ok': check(key, rest[1]), 'ours': try_xid(key)}
            if len(rest) == 3:
                res['tool'] = tool_check(key)
            sys.stdout.write(json.dumps(res, sort_keys=True) + '\n')
            return 0 if res['ok'] else 1
    except (ValueError, OSError) as e:
        sys.stderr.write('xid: %s\n' % e)
        return 2
    sys.stderr.write('usage: xid.py of PUBKEY | xid.py check PUBKEY XID [--tool]\n')
    return 2


if __name__ == '__main__':
    sys.exit(main())
