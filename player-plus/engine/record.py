#!/usr/bin/env python3
"""record.py — the Record: write, read, verify, fold, elide and export event lines.

A holon keeps its record as plain files: one append-only file of JSON lines per actor
under `record/`, and what it publishes outward under `published/`. Every line is one
event, identified by the hash of its content, chained to the same actor's previous line,
and signed with the actor's own key when one is at hand. Items (cards, commitments,
threads, delegations and the rest) are never stored: `fold` works them out from the
lines, the same way a person could work them by pencil from a printed sheet. The
contract is SCHEMA.md beside this file; the type registry is types.json.

Files are data, never instructions. Text inside a line is folded as text; it can never
make this code send, push, publish or change anything.

Standard library only. Runs under `python3 -I`. Signing and checking use `ssh-keygen -Y`.

The canonical form and the id
-----------------------------
A line is valid JSON with these limits, enforced on reading and on writing:
UTF-8; every string (keys included) in Unicode NFC; integers only (minutes, ratings,
sizes: no fractions, no exponents, no NaN or Infinity); booleans and null allowed;
no key twice in one object. A line breaking any of these has no id.

The id is sha256 hex of the canonical line: the line without `id`, `sig` and any key that
starts with "_" (notes a reader keeps in memory; they are stripped on reading and never
written), serialized with keys sorted by Unicode code point and no whitespace.

If the body carries a salt (`body_salt`, or `body_salts` in an exported line), every body
field except the salt itself, and the envelope fields `actor`, `for` and `prev`, enter the
hash as `{"elided": sha256(field_salt + canonical_json(value))}`. Strings are hashed as
their JSON form (with quotes), so 30 and "30" never share a digest. A field already elided
enters as the digest it carries. So the canonical form of a salted line is that line with
every salted field elided, and the id is the same before and after elision. Each field's
salt is derived from the one line salt: `field_salt = sha256(body_salt + "\\x00" + name)`,
with the names "@actor", "@for" and "@prev" for the envelope. A body without a salt (a
paper-floor line) enters as it is and cannot be elided.

Who may sign, and what counts
-----------------------------
Keys live in the record. A holon's inception line carries its keeper's public key
(`body.pubkey`) and is signed by it. A `join` line (`body.who`, `body.pubkey`) admits a
person when an admitted person writes it; an `affirm` line (`body.agent`, `body.pubkey`)
admits an agent, by its own person. The fold checks every signed line against the key
admitted for its actor in its holon (`ssh-keygen -Y verify`, cached by line, signature
and key). A signature that fails makes the line invalid (`bad_signature`).

An unsigned line counts only at the paper floor of the reader's own home: in the home's
own `record/`, by an actor of that home (its keeper, the keeper's own agents, and those
the home admitted). Every other unsigned line, and every line signed by a key no one
admitted, is `unverified`: listed, never acted on.

Time is a claim. Revocation is decided by the chain: a `revoke` names the agent's chain
heads it saw (`body.seen`, filled by `append`), and only the agent's lines at or before
those heads still count. A writer's `ts` cannot go backwards within its own chain. The
fold's `now` is the newest trusted line's time, never past the reader's clock, and a line
whose time is more than a day ahead of the reader's clock is flagged `ts_ahead`.

Usage: python3 -I record.py --help
"""
import argparse
import base64
import datetime as dt
import fnmatch
import hmac
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
NAMESPACE = 'lionsberg-record'
FIELD_ORDER = ('v', 'id', 'ts', 'actor', 'for', 'holon', 'type', 'body', 'links',
               'audience', 'reason', 'prev', 'sig')
AUDIENCES = ('holon', 'members', 'commons', 'public')
REASONS = ('human', 'delegated', 'untrusted')
LINK_KEYS = ('predecessor', 'successor', 'serves', 'fulfils', 'answers', 'witnesses',
             'anchored_to', 'supersedes', 'within')
SALT_KEYS = ('body_salt', 'body_salts')
ENVELOPE_ELIDABLE = ('actor', 'for', 'prev')
POSTURES = ('names-hidden', 'open', 'sealed')
MAX_LINE = 65536          # bytes; a longer line is refused on reading
TRUSTED = ('signed', 'home', 'vouched')
INVALID_TRUST = ('bad_signature', 'bad_admission', 'bad_vouch', 'wrong_holon', 'hidden')
KEY_TYPE = 'ssh-ed25519'
CONTRACT = '3.6.0'         # the contract version a holon is born under (its inception's body.contract)
CONSENT_V = 2              # the consent digest a consent line names (body.consent_v)
CLONE_HOURS = 36           # a clone's claim lasts a day and a half
OUTWARD = ('publish', 'elevate', 'escalate', 'affirm', 'delegate', 'revoke', 'join', 'leave', 'posture')


class LineError(ValueError):
    """A line that breaks the canonical rules (duplicate key, fraction, non-NFC text)."""


# ---------------------------------------------------------------- small helpers

def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _cjson(obj):
    """Canonical JSON: keys sorted by code point, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def _is_elided(v):
    return isinstance(v, dict) and set(v.keys()) == {'elided'} and isinstance(v.get('elided'), str)


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [x for x in v if x is not None]
    return [v]


def _str(v):
    """A plain string for a value that should be one; elided or missing values become ''."""
    return v if isinstance(v, str) else ''


def _parse_ts(s):
    """An aware datetime from an ISO 8601 string (a naive one is read as UTC), or None."""
    s = _str(s)
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        try:
            d = dt.datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def _date(s):
    s = _str(s)
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def handle_of(actor):
    a = _str(actor)
    return a.split(':', 1)[1] if ':' in a else a


def actor_file(actor):
    """The file name for an actor's lines: the actor id percent-encoded, case kept (`person%3Aplayer.jsonl`)."""
    return quote(_str(actor) or 'unknown', safe='') + '.jsonl'


def _legacy_actor_file(actor):
    a = _str(actor) or 'unknown'
    return ''.join(c if (c.isalnum() or c in '-_.+@') else '_' for c in a) + '.jsonl'


def load_types(path=None):
    """Read the type registry (types.json beside this file unless a path is given)."""
    p = path or os.path.join(HERE, 'types.json')
    try:
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {'items': {}, 'types': {}}
        d.setdefault('items', {})
        d.setdefault('types', {})
        return d
    except (OSError, ValueError):
        return {'items': {}, 'types': {}}


# ---------------------------------------------------------------- strict JSON

def _no_dups(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise LineError('the key %r appears twice' % k)
        out[k] = v
    return out


def _no_fraction(s):
    raise LineError('numbers are whole: %s is not' % s)


def _no_constant(s):
    raise LineError('%s is not a number a line may hold' % s)


def loads(raw):
    """Parse one line strictly: duplicate keys, fractions, exponents and NaN are refused."""
    return json.loads(raw, object_pairs_hook=_no_dups, parse_float=_no_fraction,
                      parse_constant=_no_constant)


def check_value(v, where='line'):
    """Raise LineError unless v keeps the canonical rules (NFC strings, integers, no floats)."""
    if v is None or isinstance(v, bool):
        return
    if isinstance(v, int):
        return
    if isinstance(v, str):
        if not unicodedata.is_normalized('NFC', v):
            raise LineError('%s: text is not in Unicode NFC' % where)
        return
    if isinstance(v, list):
        for i, x in enumerate(v):
            check_value(x, '%s[%d]' % (where, i))
        return
    if isinstance(v, dict):
        for k, x in v.items():
            if not isinstance(k, str):
                raise LineError('%s: a key is not text' % where)
            check_value(k, where)
            check_value(x, '%s.%s' % (where, k))
        return
    raise LineError('%s: %s is not allowed in a line (whole numbers only)' % (where, type(v).__name__))


def normalize(v):
    """A value made fit to write: text to NFC, whole floats to integers. Raises LineError otherwise."""
    if v is None or isinstance(v, (bool, int)):
        return v
    if isinstance(v, float):
        if v != v or v in (float('inf'), float('-inf')) or v != int(v):
            raise LineError('numbers in a line are whole (minutes, ratings): %r is not' % v)
        return int(v)
    if isinstance(v, str):
        return unicodedata.normalize('NFC', v)
    if isinstance(v, (list, tuple)):
        return [normalize(x) for x in v]
    if isinstance(v, dict):
        return {unicodedata.normalize('NFC', str(k)): normalize(x) for k, x in v.items()}
    raise LineError('%s cannot be written in a line' % type(v).__name__)


# ---------------------------------------------------------------- canonical form and id

def field_salt(body_salt, name):
    """The salt for one field, derived from the line's one salt."""
    return _sha(_str(body_salt) + '\x00' + name)


def digest(fsalt, value):
    """The salted digest of one field value: sha256 of the salt and the value's canonical JSON."""
    return _sha(_str(fsalt) + _cjson(value))


def _salt_for(body, name):
    """The salt for field `name`, from body_salt or from an export's body_salts; None if not held."""
    if not isinstance(body, dict):
        return None
    bs = body.get('body_salt')
    if isinstance(bs, str) and bs:
        return field_salt(bs, name)
    salts = body.get('body_salts')
    if isinstance(salts, dict) and isinstance(salts.get(name), str):
        return salts[name]
    return None


def is_salted(line):
    body = line.get('body') if isinstance(line, dict) else None
    if not isinstance(body, dict):
        return False
    return bool(_str(body.get('body_salt'))) or isinstance(body.get('body_salts'), dict)


def canonical(line):
    """The canonical form of a line, as the dict that is hashed for its id.

    Raises ValueError when the line breaks the canonical rules or a salted field's salt is not held."""
    if not isinstance(line, dict):
        raise ValueError('a line must be a JSON object')
    out = {k: v for k, v in line.items()
           if k not in ('id', 'sig') and not (isinstance(k, str) and k.startswith('_'))}
    check_value(out)
    if not is_salted(line):
        return out
    body = line.get('body') or {}
    cbody = {}
    for k, v in body.items():
        if k in SALT_KEYS:
            continue
        if _is_elided(v):
            cbody[k] = v
            continue
        s = _salt_for(body, k)
        if s is None:
            raise ValueError('no salt held for body field %r' % k)
        cbody[k] = {'elided': digest(s, v)}
    out['body'] = cbody
    for k in ENVELOPE_ELIDABLE:
        if k not in out or _is_elided(out[k]):
            continue
        s = _salt_for(body, '@' + k)
        if s is None:
            raise ValueError('no salt held for %r' % k)
        out[k] = {'elided': digest(s, out[k])}
    return out


def compute_id(line):
    """sha256 hex of the canonical line."""
    return _sha(_cjson(canonical(line)))


def check_id(line):
    """True when the line keeps the canonical rules and its id matches its content."""
    try:
        return isinstance(line, dict) and line.get('id') == compute_id(line)
    except ValueError:
        return False


def ordered(line):
    """The line with its fields in the readable order of SCHEMA.md (unknown fields kept, after)."""
    out = {k: line[k] for k in FIELD_ORDER if k in line}
    for k, v in line.items():
        if k not in out and not (isinstance(k, str) and k.startswith('_')):
            out[k] = v
    return out


def dumps(line):
    return json.dumps(ordered(line), ensure_ascii=False, allow_nan=False)


# ---------------------------------------------------------------- keys and signing

def _ssh_keygen():
    return shutil.which('ssh-keygen')


def key_name(actor):
    """The file name of an actor's key: lionsberg-<kind>-<handle> (kind is person or agent), the handle percent-encoded.

    The kind is part of the name, so person:x and agent:x never share a key file."""
    a = _str(actor)
    kind = a.split(':', 1)[0] if ':' in a else ''
    if kind not in ('person', 'agent', 'holon'):
        kind = 'unknown'
    return 'lionsberg-%s-%s' % (kind, quote(handle_of(actor) or 'unknown', safe=''))


def key_id(pubkey):
    """The id of a public key, as ssh-keygen prints it: 'SHA256:<base64 of the key blob's sha256, unpadded>'."""
    parts = _str(pubkey).split()
    if len(parts) < 2:
        return ''
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (ValueError, TypeError):
        return ''
    return 'SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode('ascii').rstrip('=')


def body_digest(body):
    """The digest a once-delegation may name: sha256 of the body's canonical JSON, without its salt."""
    b = body if isinstance(body, dict) else {}
    return _sha(_cjson({k: v for k, v in b.items() if k not in SALT_KEYS}))


def find_key(key=None, actor=None, key_dir=None):
    """The signing key for an actor, or None (the paper floor).

    With an actor, only a key file named for that actor (`lionsberg-<kind>-<handle>`) is used, so a
    person and their agent never sign with one key. It is looked for as `key` itself, then in
    `key_dir` or env LIONSBERG_KEY_DIR, then env LIONSBERG_KEY (a file, or a folder of keys),
    then ~/.ssh. Without an actor (older callers): `key`, env LIONSBERG_KEY, ~/.ssh/lionsberg."""
    if not actor:
        for p in (key, os.environ.get('LIONSBERG_KEY'), os.path.expanduser('~/.ssh/lionsberg')):
            if p and os.path.isfile(p):
                return p
        return None
    name = key_name(actor)
    cands = [key]
    kd = key_dir or os.environ.get('LIONSBERG_KEY_DIR')
    if kd:
        cands.append(os.path.join(kd, name))
    env = os.environ.get('LIONSBERG_KEY')
    if env:
        cands.append(os.path.join(env, name) if os.path.isdir(env) else env)
    if not kd:   # a named key folder is the only place looked: a test or a second body never reaches ~/.ssh
        cands.append(os.path.join(os.path.expanduser('~/.ssh'), name))
    for p in cands:
        if p and os.path.isfile(p) and os.path.basename(p) == name:
            return p
    return None


def make_key(actor, key_dir=None):
    """Make an ed25519 key for an actor at <key_dir or ~/.ssh>/lionsberg-<kind>-<handle> if none is there.

    The folder is `key_dir`, else env LIONSBERG_KEY_DIR, else ~/.ssh. Returns the path, or
    None when ssh-keygen is absent. Never overwrites a key."""
    exe = _ssh_keygen()
    if not exe or not actor:
        return None
    d = key_dir or os.environ.get('LIONSBERG_KEY_DIR') or os.path.expanduser('~/.ssh')
    os.makedirs(d, mode=0o700, exist_ok=True)
    path = os.path.join(d, key_name(actor))
    if os.path.isfile(path):
        return path
    try:
        r = subprocess.run([exe, '-q', '-t', 'ed25519', '-N', '', '-C', _str(actor), '-f', path],
                           capture_output=True, timeout=60)
        return path if r.returncode == 0 and os.path.isfile(path) else None
    except (OSError, subprocess.SubprocessError):
        return None


def pubkey_of(key):
    """The public key of a private key file, as 'ssh-ed25519 AAAA…', or ''."""
    if not key:
        return ''
    try:
        pub = key + '.pub'
        if os.path.isfile(pub):
            with open(pub, encoding='utf-8') as f:
                t = f.read().split()
        else:
            r = subprocess.run([_ssh_keygen(), '-y', '-f', key], capture_output=True, text=True, timeout=30)
            t = r.stdout.split()
        return '%s %s' % (t[0], t[1]) if len(t) >= 2 else ''
    except (OSError, subprocess.SubprocessError, TypeError):
        return ''


def sign_text(text, key):
    """Sign text with `ssh-keygen -Y sign` (ed25519 keys only); returns 'ssh-ed25519:<base64>' or ''."""
    exe = _ssh_keygen()
    if not exe or not key or not text:
        return ''
    if not pubkey_of(key).startswith(KEY_TYPE + ' '):
        return ''
    try:
        r = subprocess.run([exe, '-Y', 'sign', '-f', key, '-n', NAMESPACE],
                           input=text.encode('utf-8'), capture_output=True, timeout=30)
        if r.returncode != 0:
            return ''
        armored = r.stdout.decode('ascii', 'replace').strip().splitlines()
        b64 = ''.join(x.strip() for x in armored if x and not x.startswith('-----'))
        return '%s:%s' % (KEY_TYPE, b64)
    except (OSError, subprocess.SubprocessError):
        return ''


def sign_id(line_id, key):
    """Sign a line's id. Returns 'ssh-ed25519:<base64>', or '' when it cannot."""
    return sign_text(line_id, key)


def _armor(sig):
    b64 = sig.split(':', 1)[1] if ':' in sig else sig
    rows = [b64[i:i + 76] for i in range(0, len(b64), 76)]
    return '-----BEGIN SSH SIGNATURE-----\n' + '\n'.join(rows) + '\n-----END SSH SIGNATURE-----\n'


_SIG_CACHE = {}
_SIG_DISK = {'path': None, 'new': {}, 'secret': None}


def _cache_key(ck):
    return _sha('\x00'.join(ck))


def _cache_secret():
    """The secret that signs cache rows, kept outside the HQ: ~/.config/lionsberg/sigcache.key (0600), made on first use.

    LIONSBERG_SIGCACHE_KEY names another path (tests use it). None when it cannot be read or made safely."""
    path = os.environ.get('LIONSBERG_SIGCACHE_KEY') or os.path.join(os.path.expanduser('~'), '.config', 'lionsberg',
                                                                    'sigcache.key')
    try:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='ascii') as f:
                f.write(os.urandom(32).hex())
        st = os.stat(path)
        if os.path.islink(path) or st.st_uid != os.getuid() or (st.st_mode & 0o077):
            return None
        with open(path, encoding='ascii') as f:
            secret = f.read().strip()
        return secret.encode('ascii') if len(secret) >= 32 else None
    except (OSError, ValueError, AttributeError):
        return None


def _row_mac(secret, ck):
    return hmac.new(secret, (ck + ' 1').encode('ascii'), hashlib.sha256).hexdigest()


def load_sigcache(path):
    """Use a signature cache on disk, so a run need not re-check every line with ssh-keygen.

    Each row is `<check digest> 1 <HMAC>`, the HMAC made under a secret kept outside the HQ
    (see _cache_secret). Only verified checks are written, and only checks made in this
    process; a row whose HMAC does not verify is ignored; a failed check is never cached, so
    a cache can never suppress a line, only spare a re-check. The cache lives in the reader's
    own home (never in a cell), is made 0600, and is ignored when it is not the reader's own
    file or is readable by others."""
    _SIG_DISK['path'], _SIG_DISK['new'], _SIG_DISK['secret'] = None, {}, None
    if not path:
        return
    secret = _cache_secret()
    if not secret:
        return
    try:
        if os.path.exists(path):
            st = os.stat(path)
            if os.path.islink(path) or st.st_uid != os.getuid() or (st.st_mode & 0o077):
                return
            with open(path, encoding='ascii') as f:
                for row in f:
                    parts = row.split()
                    if len(parts) == 3 and parts[1] == '1' and hmac.compare_digest(parts[2], _row_mac(secret, parts[0])):
                        _SIG_CACHE[parts[0]] = True
        _SIG_DISK['path'], _SIG_DISK['secret'] = path, secret
    except (OSError, ValueError, AttributeError):
        _SIG_DISK['path'] = None


class signature_cache:
    """Use the reader's signature cache for a block of folds: `with record.signature_cache(hq): ...`.

    Every reader path (the engine, the Deal, the HUD) wraps its folds in this, so a warm run
    does not re-check every signature with ssh-keygen. The cache is `<hq>/.sigcache` (see
    load_sigcache); new checks are saved when the block ends."""

    def __init__(self, hq_dir):
        self.path = os.path.join(hq_dir, '.sigcache') if hq_dir else None

    def __enter__(self):
        load_sigcache(self.path)
        return self

    def __exit__(self, *exc):
        save_sigcache()
        _SIG_DISK['path'] = None
        return False


def save_sigcache():
    """Append the verified checks made since load_sigcache to the cache file (created 0600)."""
    path, new, secret = _SIG_DISK['path'], _SIG_DISK['new'], _SIG_DISK.get('secret')
    if not path or not new or not secret:
        return
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'a', encoding='ascii') as f:
            for k, v in new.items():
                if v:
                    f.write('%s 1 %s\n' % (k, _row_mac(secret, k)))
        os.chmod(path, 0o600)
    except OSError:
        pass
    _SIG_DISK['new'] = {}


_PRINCIPAL_OK = re.compile(r'^[A-Za-z0-9:_.@+%~-]+$')


def verify_text(text, sig, principal, pubkey):
    """True when `sig` is a valid signature over `text` by `pubkey`, named for `principal`.

    Cached by (text, sig, principal, key). False when ssh-keygen is absent."""
    sig, principal, pubkey = _str(sig), _str(principal), _str(pubkey)
    if not (text and sig and principal and pubkey) or not sig.startswith(KEY_TYPE + ':') \
            or not pubkey.startswith(KEY_TYPE + ' ') or not _PRINCIPAL_OK.match(principal):
        return False
    ck = _cache_key((text, sig, principal, pubkey))
    if _SIG_CACHE.get(ck) is True:
        return True
    exe = _ssh_keygen()
    if not exe:
        return False
    tmp = tempfile.mkdtemp(prefix='lionsberg-verify-')
    ok = False
    try:
        sf = os.path.join(tmp, 's.sig')
        af = os.path.join(tmp, 'allowed')
        with open(sf, 'w', encoding='ascii') as f:
            f.write(_armor(sig))
        with open(af, 'w', encoding='utf-8') as f:
            f.write('%s namespaces="%s" %s\n' % (principal, NAMESPACE, pubkey))
        r = subprocess.run([exe, '-Y', 'verify', '-f', af, '-I', principal, '-n', NAMESPACE, '-s', sf],
                           input=text.encode('utf-8'), capture_output=True, timeout=30)
        ok = r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if ok:
        _SIG_CACHE[ck] = True
        if _SIG_DISK['path']:
            _SIG_DISK['new'][ck] = True
    return ok


def verify(line, allowed_signers=None):
    """Check one line by itself: its id against its content, then its signature.

    Returns {"id", "id_ok", "sig": "valid|invalid|unsigned|unchecked", "said"}. The signer
    must be listed under the line's actor in the allowed-signers file given. Without one the
    signature is left `unchecked`: a signature checked against the key it carries proves
    nothing about who signed. To check against the keys admitted in a holon's record, fold
    the holon (or run `record.py verify <holon folder>`)."""
    out = {'id': line.get('id') if isinstance(line, dict) else None, 'id_ok': check_id(line),
           'sig': 'unsigned', 'said': ''}
    if not isinstance(line, dict):
        out['said'] = 'not a JSON object'
        return out
    sig = _str(line.get('sig'))
    if not sig:
        out['said'] = 'unsigned: this line stands at the paper floor'
        return out
    exe = _ssh_keygen()
    if not exe:
        out['sig'] = 'unchecked'
        out['said'] = 'ssh-keygen is not installed, so the signature was not checked'
        return out
    if not out['id_ok']:
        out['sig'] = 'invalid'
        out['said'] = 'the id does not match the content'
        return out
    tmp = tempfile.mkdtemp(prefix='lionsberg-verify-')
    try:
        sf = os.path.join(tmp, 'line.sig')
        with open(sf, 'w', encoding='ascii') as f:
            f.write(_armor(sig))
        actor = line.get('actor')
        if not (allowed_signers and isinstance(actor, str) and actor):
            out['sig'] = 'unchecked'
            out['said'] = 'no allowed-signers file (or a hidden actor): name one, or fold the holon to check ' \
                          'against its admitted keys'
            return out
        cmd = [exe, '-Y', 'verify', '-f', allowed_signers, '-I', actor, '-n', NAMESPACE, '-s', sf]
        r = subprocess.run(cmd, input=line['id'].encode('utf-8'), capture_output=True, timeout=30)
        out['sig'] = 'valid' if r.returncode == 0 else 'invalid'
        out['said'] = (r.stdout + r.stderr).decode('utf-8', 'replace').strip()[:300]
    except (OSError, subprocess.SubprocessError) as e:
        out['sig'] = 'unchecked'
        out['said'] = 'could not run ssh-keygen: %s' % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---------------------------------------------------------------- reading files

def _read_jsonl(path):
    """Yield (line_no, obj or None, raw, why) for each non-empty line; never raises.

    Keys starting with "_" are stripped: they are a reader's in-memory notes, never data."""
    try:
        with open(path, 'rb') as f:
            for n, rawb in enumerate(f, 1):
                if len(rawb) > MAX_LINE:
                    yield n, None, '', 'longer than %d bytes' % MAX_LINE
                    continue
                raw = rawb.decode('utf-8', 'replace').strip()
                if not raw:
                    continue
                try:
                    obj = loads(raw)
                except (ValueError, RecursionError) as e:
                    yield n, None, raw, str(e)[:120]
                    continue
                if not isinstance(obj, dict):
                    yield n, None, raw, 'not a JSON object'
                    continue
                yield n, {k: v for k, v in obj.items() if not (isinstance(k, str) and k.startswith('_'))}, raw, ''
    except OSError:
        return


def holon_info(holon_dir):
    """holon.json as a dict ({} when absent or unreadable)."""
    try:
        with open(os.path.join(holon_dir, 'holon.json'), encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def last_line(path):
    """The last valid line of a JSONL file, or None."""
    last = None
    for _, obj, _, _ in _read_jsonl(path):
        if obj is not None:
            last = obj
    return last


def is_inception(line):
    b = line.get('body') if isinstance(line.get('body'), dict) else {}
    return line.get('type') == 'join' and line.get('holon') == '' and b.get('role') == 'inception'


def read(holon_dir):
    """Every line held in one holon, from record/ and published/, with what is wrong said plainly.

    Returns {"holon", "dir", "lines", "problems", "as_of": {actor: head id}, "heads": {actor:
    [ids]}, "counts": {actor: n}, "newest": {"id", "ts"}, "inception", "keeper"}. Each line
    carries in-memory notes `_held_in` and `_file`. A line that breaks the canonical rules or
    whose id does not match is reported and left out. In record/ each actor's file is a
    chain: a line's `prev` names an earlier line of the file ('' for the first); a missing
    one is a `broken_chain`, and two lines with the same `prev` are a `fork` (both kept,
    both flagged). The holon's id must be the id of an inception line in its record, and its
    keeper is that line's actor; holon.json alone proves neither."""
    out = {'holon': None, 'dir': holon_dir, 'lines': [], 'problems': [], 'as_of': {}, 'heads': {},
           'counts': {}, 'newest': None, 'inception': None, 'keeper': None}
    if not holon_dir or not os.path.isdir(holon_dir):
        out['problems'].append({'kind': 'no_holon', 'said': 'no folder at %r' % holon_dir})
        return out
    info = holon_info(holon_dir)
    hid = _str(info.get('id')) or None
    out['holon'] = hid
    tag = hid or os.path.abspath(holon_dir)
    newest_dt = None
    for sub in ('record', 'published'):
        d = os.path.join(holon_dir, sub)
        if not os.path.isdir(d) or os.path.islink(d):
            continue
        names = sorted(n for n in os.listdir(d) if n.endswith('.jsonl'))
        lowered = {}
        for name in names:
            if name.lower() in lowered and sub == 'record':
                out['problems'].append({'kind': 'case_collision', 'file': sub + '/' + name,
                                        'said': 'two actor files differ only by case: %s and %s'
                                                % (lowered[name.lower()], name)})
            lowered.setdefault(name.lower(), name)
        for name in names:
            path = os.path.join(d, name)
            if os.path.islink(path):
                out['problems'].append({'kind': 'symlink', 'file': sub + '/' + name, 'said': 'a link is not read'})
                continue
            rel = sub + '/' + name
            in_file, prev_used, file_lines = set(), {}, []
            for n, obj, raw, why in _read_jsonl(path):
                if obj is None:
                    out['problems'].append({'kind': 'bad_json', 'file': rel, 'line_no': n,
                                            'said': '%s: %s' % (why, raw[:80])})
                    continue
                if not check_id(obj):
                    out['problems'].append({'kind': 'bad_id', 'file': rel, 'line_no': n, 'id': obj.get('id'),
                                            'said': 'the id does not match the content, or the line breaks '
                                                    'the canonical rules; left out'})
                    continue
                line = dict(obj)
                if sub == 'record':
                    actor = obj.get('actor')
                    if isinstance(actor, str) and name not in (actor_file(actor), _legacy_actor_file(actor)):
                        out['problems'].append({'kind': 'actor_mismatch', 'file': rel, 'line_no': n, 'id': obj['id'],
                                                'said': 'a line by %r sits in another actor\'s file' % actor})
                    prev = _str(obj.get('prev'))
                    if prev and prev not in in_file:
                        out['problems'].append({'kind': 'broken_chain', 'file': rel, 'line_no': n, 'id': obj['id'],
                                                'found_prev': prev,
                                                'said': 'the chain is broken here: prev names no earlier line'})
                    elif prev in prev_used:
                        out['problems'].append({'kind': 'fork', 'file': rel, 'line_no': n, 'id': obj['id'],
                                                'also': prev_used.get(prev),
                                                'said': 'the chain forks here: two lines follow the same line; both kept'})
                        line['_fork'] = True
                    prev_used.setdefault(prev, obj['id'])
                    in_file.add(obj['id'])
                    file_lines.append(obj)
                    if hid and obj['id'] == hid and is_inception(obj):
                        out['inception'] = obj['id']
                        out['keeper'] = obj.get('actor')
                line['_held_in'] = tag
                line['_file'] = rel
                out['lines'].append(line)
                t = _parse_ts(obj.get('ts'))
                if t and (newest_dt is None or t > newest_dt):
                    newest_dt = t
                    out['newest'] = {'id': obj['id'], 'ts': obj.get('ts')}
            if sub == 'record' and file_lines:
                used = {_str(x.get('prev')) for x in file_lines}
                for x in file_lines:
                    a = x.get('actor')
                    if not isinstance(a, str):
                        continue
                    out['counts'][a] = out['counts'].get(a, 0) + 1
                    if x['id'] not in used:
                        out['heads'].setdefault(a, []).append(x['id'])
                        out['as_of'][a] = x['id']
    if hid and not out['inception']:
        out['problems'].append({'kind': 'holon_id_unproven',
                                'said': 'holon.json names an id that no inception line in record/ carries'})
    elif out['keeper'] and _str(info.get('keeper')) and info.get('keeper') != out['keeper']:
        out['problems'].append({'kind': 'keeper_mismatch',
                                'said': 'holon.json names a keeper other than the inception line\'s actor; '
                                        'the inception line holds'})
    return out


def hold(hq_dir):
    """Every holon a player holds: their own HQ, then each holon under cells/ (sorted; links are not followed)."""
    out = []
    if hq_dir and os.path.isdir(hq_dir):
        out.append(hq_dir)
        cells = os.path.join(hq_dir, 'cells')
        if os.path.isdir(cells) and not os.path.islink(cells):
            for name in sorted(os.listdir(cells)):
                d = os.path.join(cells, name)
                if os.path.islink(d) or not os.path.isdir(d):
                    continue
                if os.path.isfile(os.path.join(d, 'holon.json')) or os.path.isdir(os.path.join(d, 'record')):
                    out.append(d)
    return out


def holon_dirs(hq_dir):
    """{holon id: folder} for every holon held, the home first and bound to the HQ's own record.

    A cell never displaces the home, and a cell whose id is already held or is not proven by
    its own inception line is left out. Every writer that sends a line "to the home" or "to a
    holon id" (the HUD, the agent) looks it up here, never in holon.json alone."""
    out = {}
    for h in read_all(hq_dir)['holons']:
        if h.get('refused') or not h.get('id') or h['id'] in out:
            continue
        out[h['id']] = h['dir']
    return out


def read_all(hq_dir):
    """Lines from the HQ and every holon under cells/, each tagged with the holon that holds it.

    Returns {"holons", "lines", "keepers", "home"}. Lines in the HQ's own record/ are noted
    `_home_record` (the only place an unsigned line can count). A line held in two holons
    appears once, with `_also_in` naming the others. Keepers come from inception lines; only
    the HQ, the reader's own folder, may fall back to its holon.json. A cell claiming an id
    already held (the home's included), or whose id no inception line proves, is refused:
    reported, and none of its lines read."""
    holons, lines, seen, keepers = [], [], {}, {}
    home = None
    for i, d in enumerate(hold(hq_dir)):
        r = read(d)
        info = holon_info(d)
        hid = r['holon']
        problems = list(r['problems'])
        if i == 0:
            home = hid or os.path.abspath(d)
        if i > 0 and (not hid or hid in keepers or hid == home or not r['inception']):
            problems.append({'kind': 'duplicate_holon_id' if (hid and (hid in keepers or hid == home))
                             else 'holon_id_unproven',
                             'said': 'this cell claims an id already held, or one no inception line proves; '
                                     'it is refused and none of its lines are read'})
            holons.append({'dir': d, 'id': hid, 'name': info.get('name'), 'keeper': None, 'count': 0,
                           'as_of': {}, 'heads': {}, 'counts': {}, 'newest': None, 'problems': problems,
                           'refused': True})
            continue
        elif hid:
            k = r['keeper'] or (_str(info.get('keeper')) if i == 0 else '')
            if k:
                keepers[hid] = k
        holons.append({'dir': d, 'id': hid, 'name': info.get('name'), 'keeper': keepers.get(hid),
                       'count': len(r['lines']), 'as_of': r['as_of'], 'heads': r['heads'],
                       'counts': r['counts'], 'newest': r['newest'], 'problems': problems})
        for line in r['lines']:
            if i == 0 and line['_file'].startswith('record/'):
                line['_home_record'] = True
            if line['id'] in seen:
                seen[line['id']].setdefault('_also_in', []).append(line['_held_in'])
                continue
            seen[line['id']] = line
            lines.append(line)
    return {'holons': holons, 'lines': lines, 'keepers': keepers, 'home': home}


# ---------------------------------------------------------------- writing

def make_line(actor, for_, holon, type_, body=None, links=None, audience='holon', reason='human',
              prev='', ts=None, salt=None):
    """Build one line (without signing). `salt=None` makes a fresh salt; `salt=''` makes an unsalted line.

    Text is written in NFC and whole floats become integers; a fraction raises LineError."""
    body = {k: v for k, v in (body or {}).items() if v is not None and v != '' and v != [] and v != {}
            and k not in SALT_KEYS} if isinstance(body, dict) else {}
    body = normalize(body)
    links = {k: _as_list(v) for k, v in (links or {}).items() if _as_list(v)} if isinstance(links, dict) else {}
    links = normalize(links)
    if salt is None:
        salt = os.urandom(16).hex()
    if salt:
        body['body_salt'] = salt
    line = {'v': 1, 'ts': normalize(ts or _now()), 'actor': normalize(_str(actor)), 'for': normalize(_str(for_)),
            'holon': _str(holon), 'type': normalize(_str(type_)), 'body': body, 'links': links,
            'audience': audience if audience in AUDIENCES else 'holon',
            'reason': reason if reason in REASONS else 'human', 'prev': _str(prev)}
    line['id'] = compute_id(line)
    line['sig'] = ''
    return ordered(line)


def open_append_nofollow(root, rel_dir, fname, mode=0o644):
    """Open root/rel_dir/fname for appending without following a link at any step.

    The holon folder itself, each folder below it (made when missing) and the file are all
    opened with O_NOFOLLOW, so a link planted by a pull raises OSError instead of letting a
    write land outside the holon. Returns a writable text file object."""
    flags_dir = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | os.O_NOFOLLOW
    fd = os.open(root, flags_dir)
    try:
        for part in [p for p in _str(rel_dir).split('/') if p and p != '.']:
            if part == '..':
                raise OSError('a path may not climb out of the holon')
            try:
                nfd = os.open(part, flags_dir, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(part, 0o755, dir_fd=fd)
                nfd = os.open(part, flags_dir, dir_fd=fd)
            os.close(fd)
            fd = nfd
        ffd = os.open(fname, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, mode, dir_fd=fd)
    finally:
        os.close(fd)
    return os.fdopen(ffd, 'a', encoding='utf-8')


def holon_kind(holon_dir):
    """The holon's kind as its inception line states it (never holon.json alone), or ''."""
    r = read(holon_dir)
    for l in r['lines']:
        if l['id'] == r['inception']:
            return _str((l.get('body') or {}).get('kind'))
    return ''


def _agent_heads(holon_dir, delegation_id):
    """The chain heads, in this holon, of the agent a delegation names."""
    r = read(holon_dir)
    to = None
    for l in r['lines']:
        if l['id'] == delegation_id and l.get('type') == 'delegate':
            to = _str((l.get('body') or {}).get('to'))
    return list(r['heads'].get(to, [])) if to else []


def append(holon_dir, actor, for_, type, body=None, links=None, audience='holon', reason='human',
           ts=None, salt=None, sign=None, key=None, sub='record', key_dir=None):
    """Append one line to `<holon>/record/<actor>.jsonl`, chained to that actor's last line.

    Signs with the actor's own key (see find_key: a file named lionsberg-<kind>-<handle>) unless
    sign=False; with no such key the line is written unsigned, at the paper floor, and the
    result says so. A `revoke` that names a delegation gets `body.seen`: the agent's chain
    heads here, so the fold can tell which of its lines came before. Returns {"line",
    "file", "signed", "said"}. Raises ValueError on a missing actor, for or type, a missing
    holon folder, or an actor file that differs from another only by case."""
    if not holon_dir or not os.path.isdir(holon_dir):
        raise ValueError('no holon folder at %r' % holon_dir)
    if not _str(actor) or not _str(for_) or not _str(type):
        raise ValueError('actor, for and type are all required')
    if not (actor.startswith('person:') or actor.startswith('agent:')):
        raise ValueError('an actor is person:<handle> or agent:<handle>')
    if not for_.startswith('person:'):
        raise ValueError('for names a Living Intelligence: person:<handle>')
    if sub not in ('record', 'published'):
        raise ValueError('lines are written only to record/ or published/')
    spec = (load_types(os.path.join(holon_dir, 'types.json') if os.path.isfile(os.path.join(holon_dir, 'types.json'))
                       else None).get('types') or {}).get(type) or {}
    if spec.get('home_only') and holon_kind(holon_dir) != 'person':
        raise ValueError('a %r line is written only into the person\'s own home, never into a cell' % type)
    hid = _str(holon_info(holon_dir).get('id'))
    d = os.path.join(holon_dir, sub)
    fname = actor_file(actor)
    if os.path.islink(holon_dir) or os.path.islink(d):
        raise OSError('a link stands where the holon or its %s/ should be; nothing was written' % sub)
    for n in (os.listdir(d) if os.path.isdir(d) else []):
        if n.lower() == fname.lower() and n != fname:
            raise ValueError('another actor file differs from %s only by case (%s); refused' % (fname, n))
    path = os.path.join(d, fname)
    body = dict(body or {}) if isinstance(body, dict) else {}
    if type == 'revoke' and isinstance(body.get('delegation'), str) and 'seen' not in body:
        body['seen'] = _agent_heads(holon_dir, body['delegation']) or ['']
    last = last_line(path) if sub == 'record' else None
    prev = _str(last.get('id')) if last else ''
    line = make_line(actor, for_, hid, type, body, links, audience, reason, prev, ts, salt)
    said = ''
    signed = False
    k = find_key(key, actor, key_dir) if sign is not False else None
    if k:
        s = sign_id(line['id'], k)
        if s:
            line['sig'] = s
            signed = True
        else:
            said = 'a key was found but signing failed (ed25519 keys only); the line is unsigned, at the paper floor'
    elif sign is not False:
        said = 'no key named %s for %s; the line is unsigned, at the paper floor' % (key_name(actor), actor)
    else:
        said = 'unsigned by choice; the line stands at the paper floor'
    # never written through a link: the folder and the file are opened without following one,
    # so a link planted in a pulled holon raises OSError here instead of writing outside it
    with open_append_nofollow(holon_dir, sub, fname) as f:
        f.write(dumps(line) + '\n')
    return {'line': line, 'file': path, 'signed': signed, 'said': said}


# ---------------------------------------------------------------- elision and export

def elide(line, fields):
    """Hide the named fields of a line, keeping its id verifiable.

    `fields` names body fields, or "actor", "for", "prev". Each becomes {"elided": digest}.
    The line's `body_salt` is dropped and `body_salts` keeps only the salts of the fields
    left visible, so the hidden ones cannot be guessed. An unsalted line cannot be elided:
    it is returned unchanged with `_said` explaining why."""
    if not isinstance(line, dict):
        raise ValueError('a line must be a JSON object')
    out = json.loads(json.dumps(line))
    if not is_salted(out):
        out['_said'] = 'unsalted line: nothing can be elided without breaking its id'
        return out
    body = out.get('body') or {}
    names = set(_as_list(fields))
    salts = {}
    for k in list(body.keys()):
        if k in SALT_KEYS:
            continue
        v = body[k]
        s = _salt_for(body, k)
        if _is_elided(v):
            continue
        if k in names:
            if s is None:
                raise ValueError('no salt held for %r' % k)
            body[k] = {'elided': digest(s, v)}
        elif s is not None:
            salts[k] = s
    for k in ENVELOPE_ELIDABLE:
        if k not in out or _is_elided(out.get(k)):
            continue
        s = _salt_for(body, '@' + k)
        if k in names:
            if s is None:
                raise ValueError('no salt held for %r' % k)
            out[k] = {'elided': digest(s, out[k])}
        elif s is not None:
            salts['@' + k] = s
    body.pop('body_salt', None)
    body['body_salts'] = salts
    out['body'] = body
    return ordered(out)


def _names_in(v, handles=()):
    """True when a value names an actor: an actor id, or a known handle as a whole word."""
    if isinstance(v, str):
        if 'person:' in v or 'agent:' in v:
            return True
        low = v.lower()
        for h in handles:
            if len(h) >= 3 and re.search(r'(?<![A-Za-z0-9])' + re.escape(h.lower()) + r'(?![A-Za-z0-9])', low):
                return True
        return False
    if isinstance(v, (list, tuple)):
        return any(_names_in(x, handles) for x in v)
    if isinstance(v, dict):
        return any(_names_in(k, handles) or _names_in(x, handles) for k, x in v.items())
    return False


KEY_FIELDS = ('pubkey', 'holon_pubkey', 'keys')   # a public key names its holder as surely as a handle


def _attest_digest(att):
    return _sha(_cjson({k: v for k, v in att.items() if k != 'sig'}))


def holon_keys(holon_dir, home=False):
    """The public keys admitted in a holon's record: {actor: public key}. From the record, never from an export."""
    r = read(holon_dir)
    lines = r['lines']
    if home:
        for l in lines:
            if l['_file'].startswith('record/'):
                l['_home_record'] = True
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    f = fold(lines, None, keepers)
    return {a: e.get('pubkey') for a, e in (f.get('admitted') or {}).get(r['holon'], {}).items() if e.get('pubkey')}


def holon_pubkey(holon_dir):
    """The holon's own public key, from its inception line (`body.holon_pubkey`), or ''."""
    r = read(holon_dir)
    for l in r['lines']:
        if l['id'] == r['inception']:
            return _str((l.get('body') or {}).get('holon_pubkey'))
    return ''


def verify_attestation(att, lines, pubkey=None, holon_dir=None):
    """Check an export's attestation: its role, its signer, its key, its set, and its signature.

    With the holon's folder (`holon_dir`) the check is against the record:
    - "the keeper of <holon>" verifies only under the holon's own key (signer `holon:<id>`,
      the key from the inception) or the keeper's admitted key (signer the keeper, or "the
      keeper" under a hidden posture);
    - "a member of <holon>" verifies only under that member's admitted key (signer the member,
      or, under a hidden posture, "a member", the key id picking the member's admitted key);
    - any other role, signer or key is `bad_attestation`;
    - the set must be whole: every line of the holon's record at or before the heads the
      attestation names, which the export may carry, must be in it, so a trimmed subset fails.
    A caller may instead give `pubkey`, a key it trusts, which skips the record checks. The
    key is never taken from the attestation itself. Returns {"ids_ok", "sig":
    "valid|invalid|unsigned|unchecked|bad_attestation", "said"}."""
    ids = [l.get('id') for l in lines if isinstance(l, dict)]
    ok = isinstance(att, dict) and att.get('ids_sha256') == _sha('\n'.join(_str(i) for i in ids)) \
        and att.get('count') == len(ids)
    out = {'ids_ok': bool(ok), 'sig': 'unsigned', 'said': ''}
    sig = _str((att or {}).get('sig'))
    if not sig:
        return out
    pk = _str(pubkey)
    if not pk and holon_dir:
        r = read(holon_dir)
        hid, keeper, signer, role = r['holon'], r['keeper'], _str(att.get('signer')), _str(att.get('by'))
        keys = holon_keys(holon_dir)
        if att.get('holon') != hid:
            out.update(sig='bad_attestation', said='the attestation names another holon')
            return out
        if role == 'the keeper of %s' % hid:
            if signer == 'holon:%s' % hid:
                pk = holon_pubkey(holon_dir)
            elif signer and signer in (keeper, 'the keeper'):
                pk = _str(keys.get(keeper))
        elif role == 'a member of %s' % hid:
            if signer.startswith('person:') and signer != keeper:
                pk = _str(keys.get(signer))
            elif signer == 'a member':
                want = _str(att.get('key_id'))
                pk = next((v for a2, v in keys.items() if a2.startswith('person:') and a2 != keeper
                           and key_id(v) == want), '')
        if not pk or _str(att.get('key_id')) != key_id(pk):
            out.update(sig='bad_attestation', said='the role, the signer and the key do not agree with the record')
            return out
        missing = _missing_from_set(r, att, set(ids), posture=_str(att.get('posture')))
        if missing:
            out.update(ids_ok=False, said='the export is not the whole set: %d line(s) at or before its heads are '
                                          'missing' % len(missing))
    if not pk:
        out.update(sig='unchecked', said='no key to check against: give the holon folder, or a key you trust')
        return out
    if _str(att.get('key_id')) != key_id(pk):
        out.update(sig='invalid', said='the attestation names a key other than the one given')
        return out
    good = verify_text(_attest_digest(att), sig, 'attestation', pk)
    out['sig'] = 'valid' if good else 'invalid'
    return out


def _missing_from_set(r, att, have, posture='names-hidden'):
    """Ids of the record's exportable lines at or before the attestation's heads that the export lacks."""
    heads = [h for h in _as_list(att.get('heads')) if isinstance(h, str)]
    parent = {l['id']: _str(l.get('prev')) for l in r['lines'] if l['_file'].startswith('record/')}
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    trust = fold(r['lines'], None, keepers)['trust']
    covered = set()
    for h in heads:
        cur, n = h, 0
        while cur and n < 100000:
            covered.add(cur)
            cur = parent.get(cur)
            n += 1
    out = []
    for l in r['lines']:
        if l['id'] not in covered or trust.get(l['id']) not in TRUSTED:
            continue
        if posture != 'open' and not is_salted(l):
            continue
        if l['id'] not in have:
            out.append(l['id'])
    return out


def export(holon_dir, posture='names-hidden', types=None, exporter=None, key=None, key_dir=None, ts=None,
           home=False):
    """The holon's lines prepared to leave it, under a posture, with one signed attestation.

    names-hidden: who said it is hidden. `actor`, `for` and `prev` are elided, and so is
    every body field whose registry kind is actor/actors, every public key field, and every
    field whose value names an actor (an actor id, or a known handle as a whole word in
    free text, in values and in the keys of objects). What was said stays. Because
    an SSH signature names its signer by key, each line's `sig` is removed; the ids and the
    salted digests stay, so each line still proves its content. One attestation, signed by
    the exporter, names the set (the count and the sha256 of the ids in order), so a reader
    can check the export is the one the exporter vouched for. It names the exporter by role
    ("the keeper of <holon id>", or "a member of <holon id>"), and is signed with the
    holon's own key when the exporter holds it, else with the exporter's own key, said
    plainly. Unsalted lines cannot hide
    their names and are held back.
    sealed: every body field and the envelope names are elided, signatures removed.
    open: nothing hidden; signatures kept.
    A form that keeps each author's signature while hiding names waits on the envelope.
    Only lines the fold trusts in this holon leave (signed by an admitted key, or, with
    home=True, at the paper floor of the reader's own home); unverified, forged and
    wrongly placed lines are held back. The attestation names the exporter and the id of
    the exporter's key (`key_id`); a reader checks it against the key admitted for the
    exporter in the record, never against a key the export carries.
    Returns {"posture", "lines", "attestation", "said", "problems"}."""
    if posture not in POSTURES:
        raise ValueError('posture is one of %s' % ', '.join(POSTURES))
    types = types or load_types()
    r = read(holon_dir)
    info = holon_info(holon_dir)
    exporter = exporter or r['keeper'] or _str(info.get('keeper'))
    handles = set()
    for line in r['lines']:
        for k in ('actor', 'for'):
            if isinstance(line.get(k), str):
                handles.add(handle_of(line[k]))
        for v in (line.get('body') or {}).values():
            for x in _as_list(v):
                if isinstance(x, str) and x.startswith(('person:', 'agent:')):
                    handles.add(handle_of(x))
    if home:
        for line in r['lines']:
            if line['_file'].startswith('record/'):
                line['_home_record'] = True
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    folded = fold(r['lines'], types, keepers)
    trusted_ids = {i for i, t in folded['trust'].items() if t in TRUSTED}
    home_only = {k for k, v in (types.get('types') or {}).items() if isinstance(v, dict) and v.get('home_only')}
    lines, held_back, untrusted = [], 0, 0
    for line in r['lines']:
        if _str(line.get('type')) in home_only:
            continue                       # a home-only line (e.g. `study`) never leaves the holon, in any posture
        if line['id'] not in trusted_ids:
            untrusted += 1
            continue
        clean = {k: v for k, v in line.items() if not k.startswith('_')}
        if posture == 'open':
            lines.append(ordered(clean))
            continue
        if not is_salted(clean):
            held_back += 1
            continue
        body = clean.get('body') or {}
        spec = (types.get('types') or {}).get(_str(clean.get('type'))) or {}
        actor_fields = {f.get('name') for f in (spec.get('fields') or [])
                        if isinstance(f, dict) and f.get('kind') in ('actor', 'actors')}
        if posture == 'sealed':
            names = ['actor', 'for', 'prev'] + [k for k in body if k not in SALT_KEYS]
        else:
            names = ['actor', 'for', 'prev'] + [k for k, v in body.items()
                                                if k not in SALT_KEYS and (k in actor_fields or k in KEY_FIELDS
                                                                           or _names_in(v, handles))]
        out = elide(clean, names)
        out.pop('sig', None)
        lines.append(out)
    ids = [l['id'] for l in lines]
    keeper = r['keeper'] or _str(info.get('keeper'))
    role = ('the keeper of %s' if exporter and exporter == keeper else 'a member of %s') % r['holon']
    att = {'v': 1, 'attest': 'export', 'posture': posture, 'holon': r['holon'], 'count': len(ids),
           'ids_sha256': _sha('\n'.join(ids)), 'by': role, 'ts': ts or _now(),
           'heads': sorted(h for hs in r['heads'].values() for h in hs)}   # chain heads, without the actors' names
    said = []
    hk = find_key(None, 'holon:%s' % r['holon'], key_dir) if (r['holon'] and exporter == keeper) else None
    if hk and key_id(pubkey_of(hk)) != key_id(holon_pubkey(holon_dir)):
        hk = None
    k = hk or (find_key(key, exporter, key_dir) if exporter else None)
    if k:
        # under a hidden posture the signer is named by role, never by handle; the key id picks the key
        att['signer'] = ('holon:%s' % r['holon']) if hk else (
            exporter if posture == 'open' else ('the keeper' if exporter == keeper else 'a member'))
        att['key_id'] = key_id(pubkey_of(k))
        att['sig'] = sign_text(_attest_digest(att), k)
        if not hk:
            said.append('the holon has no key of its own here; the attestation is signed with the exporter\'s key')
    else:
        att['sig'] = ''
        said.append('no key for the holon or the exporter; the attestation is unsigned')
    if untrusted:
        said.append('%d line(s) the fold does not trust in this holon were held back' % untrusted)
    if held_back:
        said.append('%d unsalted line(s) were held back: their names cannot be hidden without breaking their ids'
                    % held_back)
    return {'posture': posture, 'lines': lines, 'attestation': att, 'said': '; '.join(said),
            'problems': r['problems']}


# ---------------------------------------------------------------- the fold: small parts

def _get(line, path):
    """Values at a dotted path into a line ('body.card', 'links.answers'), as a list."""
    if not isinstance(path, str) or '.' not in path:
        return []
    head, key = path.split('.', 1)
    src = line.get(head) if isinstance(line, dict) else None
    if not isinstance(src, dict):
        return []
    return [x for x in _as_list(src.get(key)) if isinstance(x, (str, int, bool))]


def _value(spec, line, body):
    """Resolve a value in a transition: '$actor', '$for', '$ts', 'body.x', 'links.x', or a literal."""
    if isinstance(spec, str):
        if spec == '$actor':
            return line.get('actor')
        if spec == '$for':
            return line.get('for')
        if spec == '$ts':
            return line.get('ts')
        if spec.startswith('body.'):
            v = body.get(spec[5:])
            return None if _is_elided(v) else v
        if spec.startswith('links.'):
            v = _as_list((line.get('links') or {}).get(spec[6:]))
            return v[0] if len(v) == 1 else (v or None)
    return spec


def _past(until, as_of):
    """True when `until` (a date, meaning that whole day, or a time) is before `as_of`."""
    u, a = _str(until), _str(as_of)
    if not u or not a:
        return False
    if len(u) <= 10:
        ud, ad = _date(u), _date(a)
        return bool(ud and ad and ad > ud)
    ut, at = _parse_ts(u), _parse_ts(a)
    return bool(ut and at and at > ut)


def _rank(aud):
    return AUDIENCES.index(aud) if aud in AUDIENCES else 0


def _order(lines):
    """Order lines causally: an actor's lines by their prev chain, a line after every held line it names
    (links and body references), and an actor's lines after the line that admits them in that holon;
    time, then arrival, only breaks ties."""
    ids = {l['id']: l for l in lines}
    pos = {l['id']: i for i, l in enumerate(lines)}
    deps = {}
    for l in lines:
        d = set()
        if _str(l.get('prev')) in ids:
            d.add(l['prev'])
        for v in (l.get('links') or {}).values():
            for x in _as_list(v):
                if isinstance(x, str) and x in ids and x != l['id']:
                    d.add(x)
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        for k in ('card', 'commitment', 'delegation', 'route', 'route_id', 'decision', 'tea', 'line'):
            x = body.get(k)
            if isinstance(x, str) and x in ids and x != l['id']:
                d.add(x)
        for k in ('lines', 'seen'):
            for x in _as_list(body.get(k)):
                if isinstance(x, str) and x in ids and x != l['id']:
                    d.add(x)
        deps[l['id']] = d
    # an actor's lines come after the first line that admits them in that holon (a join or affirm by another)
    admits = {}
    keepers = {l['id']: _str(l.get('actor')) for l in lines if is_inception(l)}
    for l in sorted(lines, key=lambda x: (_str(x.get('ts')), pos[x['id']])):
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        who = b.get('who') if l.get('type') == 'join' else (b.get('agent') if l.get('type') == 'affirm' else None)
        h = _str(l.get('holon'))
        if isinstance(who, str) and who != l.get('actor') and who != keepers.get(h):
            admits.setdefault((h, who), l['id'])
    for l in lines:
        a = admits.get((_str(l.get('holon')), _str(l.get('actor'))))
        if a and a != l['id']:
            if l['id'] in _ancestors(a, deps):
                # the admission comes first: it may answer the actor's own request, which then follows it
                deps[a] = {d for d in deps[a] if not (ids[d].get('actor') == l.get('actor')
                                                       and _str(ids[d].get('holon')) == _str(l.get('holon')))}
            if l['id'] not in _ancestors(a, deps):
                deps[l['id']].add(a)
    key = lambda i: (_str(ids[i].get('ts')), pos[i])
    done, out = set(), []
    remaining = sorted(ids, key=key)
    while remaining:
        ready = [i for i in remaining if deps[i] <= done]
        i = ready[0] if ready else remaining[0]   # a cycle: take the earliest
        out.append(ids[i])
        done.add(i)
        remaining.remove(i)
    return out


def _ancestors(x, deps, limit=100000):
    """Every line x depends on, directly or not (to keep the causal order free of cycles)."""
    seen, stack = set(), [x]
    while stack and len(seen) < limit:
        for d in deps.get(stack.pop(), ()):
            if d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


def _consent(line):
    """The person's words carried on the line (body.consent), or ''."""
    body = line.get('body') if isinstance(line.get('body'), dict) else {}
    c = body.get('consent')
    return c.strip() if isinstance(c, str) else ''


class _Ctx:
    """What the fold knows while it runs: chains, effective times, trust, admitted keys."""

    def __init__(self):
        self.parent = {}      # line id -> prev id
        self.eff = {}         # line id -> effective time (never earlier than its chain's previous line)
        self.trust = {}
        self.by_id = {}
        self.admitted = {}
        self.keepers = {}
        self.resolves = {}
        self.vouched = {}
        self.clone_affirms = set()
        self.clock = None

    def at_or_before(self, x, head, limit=100000):
        cur, n = head, 0
        while cur and n < limit:
            if cur == x:
                return True
            cur = self.parent.get(cur)
            n += 1
        return False


def _delegations(lines, ctx=None):
    """Every trusted delegate line by a person, with any trusted revoke by the same person."""
    trusted = (lambda l: ctx is None or ctx.trust.get(l['id']) in TRUSTED)
    table = {}
    for l in lines:
        if l.get('type') == 'delegate' and _str(l.get('actor')).startswith('person:') \
                and l.get('actor') == l.get('for') and l.get('reason') != 'untrusted' and trusted(l):
            b = l.get('body') or {}
            d = {'id': l['id'], 'by': l['for'], 'to': _str(b.get('to')),
                 'scope': [x for x in _as_list(b.get('scope')) if isinstance(x, str)],
                 'holons': [x for x in _as_list(b.get('holons')) if isinstance(x, str)],
                 'until': _date(b.get('until')), 'revoked': None, 'once': b.get('once') is True,
                 'body_digest': _str(b.get('body_digest')) or None}
            d['once_ok'] = d['once'] and len(d['scope']) == 1 and d['scope'][0] != '*' \
                and len(d['holons']) == 1 and d['holons'][0] != '*'
            table[l['id']] = d
    for l in lines:
        if l.get('type') == 'revoke' and _str(l.get('actor')).startswith('person:') \
                and l.get('reason') != 'untrusted' and trusted(l):
            b = l.get('body') or {}
            seen = b.get('seen')
            seen = [x for x in _as_list(seen) if isinstance(x, str)] if isinstance(seen, list) else None
            for t in _as_list(b.get('delegation')) + _as_list((l.get('links') or {}).get('anchored_to')):
                d = table.get(t)
                if d and d['by'] == l.get('for') and not d['revoked']:
                    d['revoked'] = {'line': l['id'], 'seen': seen}
    return table


def delegation_for(line, table, once=False, used=None, ctx=None):
    """The live delegation covering an agent's line, or (None, why).

    With once=False only standing delegations count; with once=True only unused
    once-delegations (a single type and holon). A revoked delegation still covers the
    agent's lines at or before the chain heads the revoke saw, and nothing after."""
    actor, for_, typ, holon = (_str(line.get(k)) for k in ('actor', 'for', 'type', 'holon'))
    best = (0, 'no delegation from %s to %s' % (for_ or '?', actor or '?'))

    def note(level, text):
        nonlocal best
        if level > best[0]:
            best = (level, text)

    eff = (ctx.eff.get(line['id']) if ctx else None) or _parse_ts(line.get('ts'))
    for d in table.values():
        if d['to'] != actor or d['by'] != for_:
            continue
        if bool(d.get('once')) != bool(once):
            continue
        if once and (not d.get('once_ok') or d['id'] in (used or ())):
            note(1, 'the once-delegation is used up or names more than one type or holon')
            continue
        if once and d.get('body_digest') and body_digest(line.get('body')) != d['body_digest']:
            note(3, 'the line does not match the body the once-delegation names (body_digest)')
            continue
        if '*' not in d['scope'] and typ not in d['scope']:
            note(1, 'the delegation does not cover the type %r' % typ)
            continue
        if '*' not in d['holons'] and holon not in d['holons']:
            note(2, 'the delegation does not cover this holon')
            continue
        if d['until'] and eff and eff.date() > d['until']:
            note(3, 'the delegation had ended')
            continue
        rv = d['revoked']
        if rv:
            seen = rv.get('seen')
            if seen is None:
                note(3, 'the delegation was revoked, and the revoke names no chain head, so no line is proven earlier')
                continue
            if not ctx or not any(h and ctx.at_or_before(line['id'], h) for h in seen):
                note(3, 'the delegation was revoked before this line')
                continue
        return d, ''
    return None, best[1]


def _validity(line, spec, table, used=None, by_id=None, ctx=None):
    """Whether a line counts: (why it does not, or '', signed_for source or None, once-delegation id or None).

    A person's line counts when they answer for themselves. An agent's line counts under a
    live standing delegation covering its type and holon, except for a Living Intelligence's
    own acts (human_only). Any agent line, human_only included, also counts at the person's
    word: under an unused once-delegation for that one type and holon (which the line then
    uses up), or with the person's consent written on the line (body.consent, with
    links.answers naming their say line when there is one)."""
    actor = line.get('actor')
    if _is_elided(actor) or not isinstance(actor, str):
        return 'the actor is hidden; an elided line informs but never acts', None, None
    if not actor.startswith(('person:', 'agent:')):
        return 'the actor is neither person: nor agent:', None, None
    if not _str(line.get('for')).startswith('person:'):
        return 'the line answers for no Living Intelligence', None, None
    if actor.startswith('person:'):
        if actor != line.get('for'):
            return 'a person answers for themselves', None, None
        return '', None, None
    if ctx is not None and line.get('type') == 'affirm' and line['id'] in getattr(ctx, 'clone_affirms', ()):
        return '', None, None
    clone = (getattr(ctx, 'admitted', {}) or {}).get(_str(line.get('holon')), {}).get(actor) if ctx else None
    if clone and clone.get('via') == 'clone':
        typ = _str(line.get('type'))
        if typ in OUTWARD or spec.get('human_only'):
            return 'a clone never performs an outward act or a person\'s own act (%r)' % typ, None, None
        as_prime = dict(line, actor=clone.get('prime'))
        d, why = delegation_for(as_prime, table, ctx=None)
        return ('' if d else 'the clone acts only within its prime\'s delegation: ' + why), None, None
    if not spec.get('human_only'):
        d, why = delegation_for(line, table, ctx=ctx)
        if d:
            return '', None, None
    else:
        why = ('an agent never ticks a human\'s box: %r is a Living Intelligence\'s own act, '
               'valid from an agent only at their word (a once-delegation or consent on the line)' % line.get('type'))
    if ctx is not None and not _affirmed_by_person(line, ctx):
        return (why + '; and signing at the person\'s word needs the agent let in by an affirm of the person '
                'it answers for'), None, None
    words = _consent(line)
    if words:
        src = _consent_source(line, words, by_id, ctx, used)
        if not src:
            return ('the consent names no unused signed line of the person\'s own, in this holon, that names this '
                    'very act (consent_for) in the same words; a bare consent never counts'), None, None
        return '', {'consent': words, 'line': src}, 'consent:' + src
    d, w = delegation_for(line, table, once=True, used=used, ctx=ctx)
    if d:
        return '', {'delegate': d['id'], 'once': True}, d['id']
    if 'body_digest' in w:
        return w, None, None
    return why, None, None


def _affirmed_by_person(line, ctx):
    """True when the agent was let into the line's holon by an affirm of the person it answers for."""
    e = (getattr(ctx, 'admitted', {}) or {}).get(_str(line.get('holon')), {}).get(_str(line.get('actor')))
    return bool(e) and e.get('via') in ('affirm', 'rotate') and e.get('person') == line.get('for')


def consent_digest(act, without=None):
    """What a person's consent line names in `consent_for`: the digest of the act itself.

    It hashes the act's type, holon, links and body (the body without its salt and its
    consent words), so a consent for ratifying one decision never serves another, and a
    consent for one type never serves another type. `act` is the act's line, or a dict with
    those four keys written before the act exists. The consent line's own id (`without`) is
    left out of the links, since the person writes the consent before the agent links it."""
    a = act if isinstance(act, dict) else {}
    body = a.get('body') if isinstance(a.get('body'), dict) else {}
    links = {}
    for k, v in (a.get('links') or {}).items() if isinstance(a.get('links'), dict) else []:
        ids = [x for x in _as_list(v) if x != without]
        if ids:
            links[k] = ids
    return _sha(_cjson({'type': _str(a.get('type')), 'holon': _str(a.get('holon')), 'links': links,
                        'body': {k: v for k, v in body.items() if k not in SALT_KEYS and k != 'consent'}}))


def _norm_words(t):
    return ' '.join(_str(t).lower().split())


def _consent_source(line, words, by_id, ctx, used=None):
    """The id of the person's consent line for this act, or ''.

    It is the person's own line, in the same holon, trusted as signed under their admitted
    key, not yet used by another act, that names its digest version (`body.consent_v`, which
    must be CONSENT_V) and whose `body.consent_for` names this act (its consent_digest, or its id), and whose text is the consent words exactly (two characters
    at least). A substring, a one-letter word, or a line that names another act never counts."""
    want = _norm_words(words)
    if len(want) < 2 or ctx is None:
        return ''
    cands = list(_as_list((line.get('links') or {}).get('answers')))
    cands += [i for i, l in (by_id or {}).items()
              if isinstance(l.get('body'), dict) and l['body'].get('consent_for') == line['id']]
    for x in cands:
        held = (by_id or {}).get(x)
        if held is None or held.get('actor') != line.get('for') or held.get('for') != line.get('for'):
            continue
        if held.get('holon') != line.get('holon') or ctx.trust.get(x) != 'signed':
            continue
        if ('consent:' + x) in (used or ()):
            continue
        b = held.get('body') or {}
        if b.get('consent_v') != CONSENT_V:      # a consent counts only under the digest its version names
            continue
        if b.get('consent_for') not in (consent_digest(line, without=x), line['id']):
            continue
        texts = [v for k, v in b.items() if isinstance(v, str) and k != 'consent_for']
        if any(_norm_words(t) == want for t in texts):
            return x
    return ''


def _invalid_reason(line, spec, table):
    """Why a line does not count, or '' (without using up any once-delegation)."""
    return _validity(line, spec, table)[0]


def _merge_links(item, line):
    """Merge a line's links into an item's `links` (each a list of ids, no repeats, order kept)."""
    links = item.setdefault('links', {k: [] for k in LINK_KEYS})
    src = line.get('links') if isinstance(line.get('links'), dict) else {}
    for k, v in src.items():
        if not isinstance(k, str):
            continue
        dest = links.setdefault(k, [])
        for x in _as_list(v):
            if isinstance(x, str) and x and x not in dest and x != item.get('id'):
                dest.append(x)


def _new_item(kind, line, body, holon):
    item = {'id': line['id'], 'kind': kind, 'holon': holon, 'state': None,
            'actor': line.get('actor'), 'for': line.get('for'), 'ts': line.get('ts'),
            'events': [line['id']], 'held_in': line.get('_held_in'),
            'links': {k: [] for k in LINK_KEYS}}
    _merge_links(item, line)
    for k, v in body.items():
        if k in SALT_KEYS or _is_elided(v):
            continue
        item[k if k not in item else 'body_' + k] = v
    return item


def _who_ok(who, line, item, keepers):
    if not who:
        return True
    lf = line.get('for')
    if who == 'same_for':
        return lf == item.get('for')
    if who == 'other':
        return lf != item.get('for')
    if who == 'named':
        # who verifies Kept: the named witness or the committee, never the committor; with neither named, anyone else
        allowed = {x for x in (item.get('witness'), item.get('committee')) if isinstance(x, str) and x}
        if allowed:
            return lf in allowed and lf != item.get('for')
        return lf != item.get('for')
    if who == 'committee':
        # who releases or declines a commitment: its committee; with none named, the holon's keeper speaks for the holon
        c = item.get('committee')
        if isinstance(c, str) and c:
            return lf == c
        k = (keepers or {}).get(item.get('holon'))
        return bool(k) and lf == k
    if who == 'party':
        # a party to the commitment: its committor, its committee or its named witness
        return lf in {x for x in (item.get('for'), item.get('committee'), item.get('witness')) if isinstance(x, str) and x}
    if who == 'raiser_or_holder':
        # a constraint: the one who raised it, or the one who holds its removal
        return lf in {x for x in (item.get('for'), item.get('holder')) if isinstance(x, str) and x}
    if who == 'keeper':
        k = (keepers or {}).get(item.get('holon'))
        if k:
            return lf == k and lf != item.get('for')
        return lf != item.get('for')
    return False


def _matches(when, line, body):
    for path, want in (when or {}).items():
        if _value(path, line, body) != want:
            return False
    return True


def _entry(line, body):
    e = {'id': line['id'], 'type': line.get('type'), 'actor': line.get('actor'), 'ts': line.get('ts')}
    for k in ('text', 'did', 'note', 'reason'):     # reason: a miss's coded reason
        if isinstance(body.get(k), str):
            e[k] = body[k]
    return e


def _apply(item, spec_list, line, body, keepers, kind_filter=True):
    """Apply the first transition that fits. Returns '' or why none did."""
    if not spec_list:
        return ''
    why = 'no transition fits'
    for t in spec_list:
        if not isinstance(t, dict):
            continue
        if kind_filter and t.get('kind') and t['kind'] != item['kind']:
            continue
        if not _matches(t.get('when'), line, body):
            continue
        frm = t.get('from')
        if frm and item.get('state') not in frm:
            why = 'cannot move from %r' % item.get('state')
            continue
        if not _who_ok(t.get('who'), line, item, keepers):
            why = 'not the right actor for this act (%s)' % t.get('who')
            continue
        for k, v in (t.get('set') or {}).items():
            item[k] = _value(v, line, body)
        if t.get('append_to'):
            item.setdefault(t['append_to'], []).append(_entry(line, body))
        return ''
    return why


# ---------------------------------------------------------------- the fold: trust

def _trust_pass(order, inceptions, keepers, ctx):
    """Decide each line's trust: signed · home · unverified · bad_signature · bad_admission · wrong_holon · hidden.

    Admission, in fold order: the inception admits the keeper and its key. A trusted `join`
    by an admitted person admits a person whose handle is not yet admitted. A key for an
    already-admitted handle changes only by a rotation: a `join` naming that handle, by that
    handle itself, signed with its current key; or a `join` by the holon's keeper naming a
    `witness`, which takes effect when that witness (an admitted person, not the keeper)
    writes a trusted `witness` line linking it. A trusted `affirm` by a person admits an
    agent not yet admitted, for that person; only that same person re-affirms it. Any other
    re-admission is `bad_admission` and changes nothing. At home, an unsigned line counts
    only from an admitted actor, so an agent there needs an affirm too.

    Returns (trust, why) dicts by line id, and the admitted keys {holon: {actor: {...}}}."""
    admitted = {}
    for hid, k in (keepers or {}).items():
        if hid not in inceptions and isinstance(k, str) and k:
            admitted.setdefault(hid, {})[k] = {'pubkey': None, 'person': None, 'by': 'holon.json', 'via': 'holon.json'}
    known = set(inceptions) | set((keepers or {}).keys())
    trust, why = {}, {}
    pending = {}   # keeper rotations waiting on their witness: join id -> (holon, who, pubkey, witness)
    standing = {}  # trusted standing delegations seen so far: id -> line (for a prime's affirm of a clone)
    revoked = set()
    clones = {}    # clone actor -> {"claim": time or None, "ended": bool}
    paper = {}     # keyed actors' unsigned lines at home, waiting on a signed witness
    by_id_t = ctx.by_id
    ctx.clone_affirms = set()
    for l in order:
        lid = l['id']
        a = l.get('actor')
        H = l.get('holon') or (lid if lid in inceptions else '')
        sig = _str(l.get('sig'))
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        if not isinstance(a, str):
            trust[lid], why[lid] = 'hidden', 'the actor is hidden'
            continue
        held = l.get('_held_in')
        if _str(l.get('_file')).startswith('record/') and held in known and held != H:
            trust[lid], why[lid] = 'wrong_holon', 'a line written for another holon sits in this record; it never acts here'
            continue
        if H in inceptions and (inceptions[H].get('body') or {}).get('contract') != CONTRACT:
            trust[lid], why[lid] = 'unverified', ('the holon was born under a contract this reader does not know; '
                                                  'none of its lines act (contract_unknown)')
            continue
        if lid in inceptions:
            pk = _str(body.get('pubkey'))
            if sig:
                if pk and verify_text(lid, sig, a, pk):
                    trust[lid] = 'signed'
                else:
                    trust[lid], why[lid] = 'bad_signature', 'the inception is not signed by the key it names'
            elif l.get('_home_record'):
                trust[lid] = 'home'
            else:
                trust[lid], why[lid] = 'unverified', 'an unsigned inception outside the home'
            if trust[lid] in TRUSTED:
                admitted.setdefault(H, {})[a] = {'pubkey': pk or None, 'person': None, 'by': lid, 'via': 'inception'}
            continue
        entry = admitted.get(H, {}).get(a)
        if entry is not None and a.startswith('agent:') and entry.get('person') \
                and entry['person'] != l.get('for'):
            trust[lid], why[lid] = 'unverified', 'the agent was let in by another person'
            continue
        adm = by_id_t.get(_str((entry or {}).get('by'))) if entry is not None and \
            entry.get('via') in ('join', 'affirm', 'clone') else None
        if adm is not None and adm['id'] != lid:
            named = [x for v in (adm.get('links') or {}).values() for x in _as_list(v) if isinstance(x, str)]
            if lid not in named:
                ae, le = ctx.eff.get(adm['id']), ctx.eff.get(lid)
                if any(ctx.at_or_before(lid, n) for n in named) or (ae and le and le < ae):
                    trust[lid], why[lid] = 'paper', ('written before %s was admitted here; only the line the admission '
                                                     'answers is kept' % a)
                    continue
        if entry is not None and entry.get('via') == 'clone':
            cs = clones.setdefault((H, a), {'claim': None, 'ended': False})
            eff = ctx.eff.get(lid)
            is_claim = l.get('type') == 'body' and body.get('state') == 'claimed'
            if cs['ended']:
                trust[lid], why[lid] = 'unverified', 'the clone\'s body is done or archived; its admission has ended'
                continue
            if cs['claim'] is None and not is_claim:
                trust[lid], why[lid] = 'unverified', 'a clone acts only after its body line claims its work'
                continue
            start = cs['claim'] if cs['claim'] is not None else eff
            limit = start + dt.timedelta(hours=CLONE_HOURS) if start else None
            if limit and ((eff and eff > limit) or (getattr(ctx, 'clock', None) and ctx.clock > limit)):
                trust[lid], why[lid] = 'unverified', ('the clone\'s claim is stale: more than a day and a half old by '
                                                      'its own time or by the reader\'s clock')
                continue
        if sig:
            if entry and entry.get('pubkey'):
                if verify_text(lid, sig, a, entry['pubkey']):
                    trust[lid] = 'signed'
                else:
                    trust[lid], why[lid] = 'bad_signature', 'the signature does not verify against %s\'s admitted key' % a
            else:
                trust[lid], why[lid] = 'unverified', 'signed by a key no one admitted in this holon'
        elif l.get('_home_record') and entry is not None:
            if entry.get('pubkey'):
                trust[lid], why[lid] = 'paper', ('%s holds an admitted key: an unsigned line of theirs is paper, and acts '
                                                 'only after their own (or the keeper\'s) signed witness of it' % a)
                paper[lid] = l
                continue
            trust[lid] = 'home'
        else:
            trust[lid], why[lid] = 'unverified', ('unsigned, and not in the home\'s own record' if entry is not None
                                                  else '%s was never admitted in this holon' % a)
        if entry is not None and entry.get('via') == 'clone' and trust[lid] in TRUSTED \
                and l.get('type') == 'body':
            cs = clones[(H, a)]
            if body.get('state') == 'claimed' and cs['claim'] is None:
                cs['claim'] = ctx.eff.get(lid)
            if body.get('state') in ('done', 'archived'):
                cs['ended'] = True
        if trust[lid] in TRUSTED and l.get('reason') != 'untrusted':
            if l.get('type') == 'delegate' and a.startswith('person:') and a == l.get('for'):
                standing[lid] = l
            elif l.get('type') == 'revoke' and a.startswith('person:'):
                for x in _as_list(body.get('delegation')):
                    if x in standing and standing[x].get('for') == l.get('for'):
                        revoked.add(x)
            elif l.get('type') == 'affirm' and a.startswith('agent:') and entry is not None \
                    and entry.get('via') in ('affirm', 'rotate'):
                ag, pk = body.get('agent'), _str(body.get('pubkey')) or None
                room = admitted.setdefault(H, {})
                d = _clone_delegation(l, ag, standing, revoked, H)
                elsewhere = any(ag in r2 and r2[ag].get('person') not in (None, l.get('for'))
                                for r2 in admitted.values())
                if not (isinstance(ag, str) and ag.startswith('agent:')) or ag in room or not d or elsewhere:
                    trust[lid], why[lid] = 'bad_admission', ('an agent lets in a clone only under its person\'s standing '
                                                             'delegation covering affirm and body and naming the clone\'s '
                                                             'handle, and only a handle not yet admitted')
                else:
                    room[ag] = {'pubkey': pk, 'person': l.get('for'), 'by': lid, 'via': 'clone', 'prime': a}
                    ctx.clone_affirms.add(lid)
                continue
        if trust[lid] not in TRUSTED or l.get('reason') == 'untrusted' or not a.startswith('person:') \
                or a != l.get('for'):
            continue
        room = admitted.setdefault(H, {})
        typ = l.get('type')
        if typ == 'join' and isinstance(body.get('who'), str) and body['who'].startswith('person:'):
            who, pk = body['who'], _str(body.get('pubkey')) or None
            if who not in room:
                room[who] = {'pubkey': pk, 'person': None, 'by': lid, 'via': 'join'}
            elif who == a and trust[lid] == 'signed' and pk:
                room[who] = dict(room[who], pubkey=pk, by=lid, via='rotate')
            elif a == (keepers or {}).get(H) and isinstance(body.get('witness'), str) \
                    and body['witness'].startswith('person:') and body['witness'] != a and pk:
                pending[lid] = (H, who, pk, body['witness'])
            else:
                trust[lid], why[lid] = 'bad_admission', ('%s is already admitted here; a key changes only by a rotation '
                                                         'signed with the current key, or by the keeper with a witness' % who)
        elif typ == 'affirm' and isinstance(body.get('agent'), str) and body['agent'].startswith('agent:'):
            ag, pk = body['agent'], _str(body.get('pubkey')) or None
            if ag not in room:
                room[ag] = {'pubkey': pk, 'person': a, 'by': lid, 'via': 'affirm'}
            elif room[ag].get('person') == a:
                room[ag] = dict(room[ag], pubkey=pk or room[ag].get('pubkey'), by=lid, via='affirm')
            else:
                trust[lid], why[lid] = 'bad_admission', '%s was let in by another person; only that person re-affirms it' % ag
        elif typ == 'witness':
            if trust[lid] == 'signed':
                for x in _as_list((l.get('links') or {}).get('witnesses')):
                    if x in paper and (paper[x].get('actor') == a or a == (keepers or {}).get(H)):
                        trust[x] = 'home'
                        why.pop(x, None)
                        paper.pop(x, None)
            for x in _as_list((l.get('links') or {}).get('witnesses')):
                pend = pending.get(x)
                if pend and pend[0] == H and pend[3] == a and pend[1] in room:
                    room[pend[1]] = dict(room[pend[1]], pubkey=pend[2], by=x, via='rotate')
                    pending.pop(x, None)
    _vouch(order, trust, why, admitted, known, ctx)
    return trust, why, admitted


def _clone_delegation(line, clone, standing, revoked, holon):
    """The standing delegation under which an agent (the prime) may let in this clone, or None.

    It is a trusted, unrevoked `delegate` from the person the prime answers for, to the prime,
    whose scope covers both `affirm` and `body` (or is "*"), whose holons cover this holon,
    and whose `clones` (a handle pattern) matches the clone's handle. A clone's handle always
    begins with its prime's handle and a dot (`agent:<prime>.<name>`), so no pattern, not
    even "*", reaches another person's agent."""
    for did, d in standing.items():
        b = d.get('body') or {}
        scope = [x for x in _as_list(b.get('scope')) if isinstance(x, str)]
        holons = [x for x in _as_list(b.get('holons')) if isinstance(x, str)]
        pats = [x for x in _as_list(b.get('clones')) if isinstance(x, str)]
        if did in revoked or b.get('once') is True or _str(b.get('to')) != line.get('actor') \
                or d.get('for') != line.get('for'):
            continue
        if not ('*' in scope or ('affirm' in scope and 'body' in scope)):
            continue
        if '*' not in holons and holon not in holons:
            continue
        prime_handle = handle_of(line.get('actor'))
        if not handle_of(clone).startswith(prime_handle + '.'):
            continue
        if any(fnmatch.fnmatchcase(handle_of(clone), pat) for pat in pats):
            return did
    return None


def _vouch(order, trust, why, admitted, known, ctx):
    """Copies published from a holon this reader does not hold, vouched for by a trusted publish line.

    A `publish` written by an admitted person of the receiving holon names the copied lines
    (`body.lines`) and their authors' public keys as admitted at home (`body.keys`:
    {actor: public key}). A named copy whose own holon is not held and whose `for` is the
    publisher's is checked against the key the publish line carries for its actor:
    - if that actor is already admitted here, the vouched key must equal the admitted key,
      else the copy is `bad_vouch`;
    - a signature that does not verify under the vouched key is `bad_signature`;
    - an agent's copy is vouched only when the agent is also affirmed in the receiving holon;
    - otherwise the copy is `vouched`, by that publish line.
    A vouched copy informs (its items appear, the schedule reads it as an external) but never
    acts on the receiving holon's own items. A copy no trusted publish line names stays unverified."""
    by_id = ctx.by_id
    ctx.vouched = {}
    for p in order:
        if p.get('type') != 'publish' or trust.get(p['id']) not in ('signed', 'home') \
                or not _str(p.get('actor')).startswith('person:') or p.get('reason') == 'untrusted':
            continue
        b = p.get('body') or {}
        keys = b.get('keys') if isinstance(b.get('keys'), dict) else {}
        room = admitted.get(_str(p.get('holon')), {})
        for x in _as_list(b.get('lines')):
            c = by_id.get(x)
            if c is None or trust.get(x) != 'unverified' or _str(c.get('holon')) in known:
                continue
            a = c.get('actor')
            if c.get('for') != p.get('for') or not isinstance(a, str):
                continue
            pk = _str(keys.get(a))
            if not pk or not _str(c.get('sig')):
                continue
            here = room.get(a)
            if here and here.get('pubkey') and here['pubkey'] != pk:
                trust[x], why[x] = 'bad_vouch', 'the vouched key for %s differs from the key admitted here' % a
                continue
            if not verify_text(x, c['sig'], a, pk):
                trust[x], why[x] = 'bad_signature', 'the copy does not verify under the key its publish line vouches'
                continue
            if a.startswith('agent:') and not (here and here.get('via') in ('affirm', 'rotate', 'clone')):
                why[x] = 'a vouched agent acts only when it is also affirmed in this holon'
                continue
            trust[x] = 'vouched'
            why[x] = 'vouched for by the publish line %s' % p['id']
            ctx.vouched[x] = p['id']


def _forks(clean, trust):
    """Lines that fork an actor's chain (two lines with one prev, in one holon), and which survive.

    A fork holds until a later trusted line by the same actor in the same holon names one
    branch in `links.supersedes`: that branch survives, the others never act. Until then
    neither acts. Returns (held ids, [{"lines", "survivor"}], resolution links {resolver id: survivor id})."""
    groups = {}
    for l in clean:
        a = l.get('actor')
        if isinstance(a, str) and isinstance(l.get('prev'), str):
            groups.setdefault((_str(l.get('holon')), a, l['prev']), []).append(l['id'])
    held, report, resolves = set(), [], {}
    by_actor = {}
    for l in clean:
        if isinstance(l.get('actor'), str):
            by_actor.setdefault((_str(l.get('holon')), l['actor']), []).append(l)
    for (h, a, _), ids in groups.items():
        if len(ids) < 2:
            continue
        survivor = None
        for r in by_actor.get((h, a), []):
            if r['id'] in ids or trust.get(r['id']) not in TRUSTED:
                continue
            named = [x for x in _as_list((r.get('links') or {}).get('supersedes')) if x in ids]
            if named:
                survivor = named[0]
                resolves[r['id']] = survivor
                break
        held |= {i for i in ids if i != survivor}
        report.append({'lines': ids, 'survivor': survivor})
    return held, report, resolves


def _ratified_by(decide_id, person, by_id, ctx):
    """True when a trusted ratify by `person` answers (or is anchored to) the decide line."""
    for l in by_id.values():
        if l.get('type') == 'ratify' and l.get('actor') == person and l.get('for') == person \
                and ctx.trust.get(l['id']) in TRUSTED and l.get('reason') != 'untrusted' \
                and decide_id in (_as_list((l.get('links') or {}).get('answers'))
                                  + _as_list((l.get('links') or {}).get('anchored_to'))):
            return l['id']
    return ''


def _witnessed_by(ids, person, by_id, ctx):
    """True when a trusted witness line by `person` links any of these ids."""
    for l in by_id.values():
        if l.get('type') == 'witness' and l.get('actor') == person and l.get('for') == person \
                and ctx.trust.get(l['id']) in TRUSTED \
                and set(ids) & set(_as_list((l.get('links') or {}).get('witnesses'))):
            return True
    return False


def _supersessions(order, ctx, tdefs, table):
    """Map each superseded line to the valid `supersede` lines that replace it (oldest first),
    and list refused supersessions with why.

    A supersede counts only when it is trusted, not untrusted, valid, and by the same actor
    as the line it replaces. Otherwise only a person may supersede, and only under a trusted
    `decide` in the same holon that the supersede links (answers or anchored_to): a decide by
    the holon's keeper, or one ratified by the replaced line's own Living Intelligence. Over
    another actor's commitment the decide must be ratified by the committor, or by the
    keeper with the commitment's named witness witnessing it; a person alone never rewrites
    another's commitment. An agent never supersedes another actor's line. A link from a
    fork's resolving line to a branch resolves the fork; it is not a correction."""
    replaced, refused = {}, []
    by_id = ctx.by_id
    sspec = tdefs.get('supersede') or {}
    for s in order:
        if s.get('type') != 'supersede':
            continue
        for t in [x for x in _as_list((s.get('links') or {}).get('supersedes')) if isinstance(x, str)]:
            old = by_id.get(t)
            if old is None or getattr(ctx, 'resolves', {}).get(s['id']) == t:
                continue
            root, hops = old, 0
            while root.get('type') == 'supersede' and hops < 50:
                nxt = [x for x in _as_list((root.get('links') or {}).get('supersedes')) if x in by_id]
                if not nxt:
                    break
                root = by_id[nxt[0]]
                hops += 1

            def refuse(text):
                refused.append({'id': s['id'], 'supersedes': t, 'invalid_reason': text})

            if ctx.trust.get(s['id']) not in TRUSTED:
                refuse('an unverified line never supersedes')
                continue
            if s.get('reason') == 'untrusted':
                refuse('an untrusted line never supersedes')
                continue
            why = _validity(s, sspec, table, by_id=by_id, ctx=ctx)[0]
            if why:
                refuse(why)
                continue
            sa, ra = _str(s.get('actor')), _str(root.get('actor'))
            if sa == ra and sa:
                replaced.setdefault(root['id'], []).append(s)
                continue
            if sa.startswith('agent:'):
                refuse('an agent never supersedes another actor\'s line')
                continue
            keeper = (getattr(ctx, 'keepers', {}) or {}).get(_str(root.get('holon')))
            owner = _str(root.get('for'))
            is_commit = root.get('type') == 'commit'
            witness = _str((root.get('body') or {}).get('witness'))
            backed = False
            for x in _as_list((s.get('links') or {}).get('answers')) + _as_list((s.get('links') or {}).get('anchored_to')):
                dl = by_id.get(x)
                if dl is None or dl.get('type') != 'decide' or ctx.trust.get(x) not in TRUSTED \
                        or not _str(dl.get('actor')).startswith('person:') or dl.get('actor') != dl.get('for') \
                        or not (dl.get('holon') == s.get('holon') == root.get('holon')):
                    continue
                if is_commit:
                    if _ratified_by(x, owner, by_id, ctx):
                        backed = True
                    elif keeper:
                        kr = _ratified_by(x, keeper, by_id, ctx)
                        if kr and witness and witness != keeper and _witnessed_by([x, kr], witness, by_id, ctx):
                            backed = True
                elif dl.get('actor') == keeper or _ratified_by(x, owner, by_id, ctx):
                    backed = True
            if backed:
                replaced.setdefault(root['id'], []).append(s)
            elif is_commit:
                refuse('a person alone never rewrites another\'s commitment: it needs a decide ratified by the '
                       'committor, or by the keeper with the named witness')
            else:
                refuse('only the same actor, or a person under a decide by the keeper or ratified by the line\'s '
                       'own person, may supersede a line')
    return replaced, refused


# ---------------------------------------------------------------- the fold

def fold(lines, types=None, keepers=None, now=None, clock=None):
    """Fold lines into items.

    Returns {cards, commitments, threads, delegations, tea, decisions, sightings, turns,
    baselines, discernments, unknown, invalid, unverified, forked, forks, proposals, pending,
    refused, signed_for, audience, trust, flags, admitted, problems, as_of}. Every item carries its
    `holon`, the `events` that made it, its `state`, and its `links` (all nine kinds,
    merged from the line that made it and every later line that acts on it).

    The rules, in order: a line that breaks the canonical rules or whose id does not match
    is left out. Each line's trust is decided (see the module docstring): a bad signature or
    a line written for another holon is `invalid`; an unverified line is listed in
    `unverified` and never acts. An agent's line counts only under a live delegation from
    the person it answers for, covering its type and holon, and never for a Living
    Intelligence's own acts, unless the person's word is on it (a once-delegation, used up
    by the line, or body.consent); such a line is listed in `signed_for` and its item marked
    `signed_for: true`. A line whose reason is `untrusted` is a proposal only. A `supersede`
    replaces the body of the line it supersedes (both remain; the latest shows; an empty one
    retracts it). An audience widens only by a person's `publish` of their own lines. A
    commitment never writes a date onto its card: the card carries `committed_by`, a reference
    to each commitment made on it (its due date, committor, committee, stated buffer and state),
    and the schedule compares. Unknown types are kept in `unknown`.
    A link to a line not held is `pending`, not yet replicated. A claim with `until` expires
    when `until` is past as of `now`.

    `now` overrides the fold's time; else it is the newest trusted line's time, never past
    `clock` (the reader's clock, default the machine's). `keepers` gives keepers for holons
    whose inception line is not held (the reader's own home only)."""
    types = types if isinstance(types, dict) else load_types()
    tdefs = types.get('types') or {}
    idefs = types.get('items') or {}
    out = {(idefs[k].get('plural') or k): [] for k in idefs}
    for k in ('cards', 'commitments', 'threads', 'delegations', 'tea', 'decisions', 'sightings',
              'turns', 'baselines', 'discernments'):
        out.setdefault(k, [])
    out.update({'unknown': [], 'invalid': [], 'unverified': [], 'forked': [], 'proposals': [], 'pending': [], 'refused': [],
                'signed_for': [], 'audience': {}, 'trust': {}, 'flags': [], 'problems': []})

    clean, seen = [], set()
    for l in lines or []:
        if not isinstance(l, dict):
            out['problems'].append({'kind': 'not_a_line'})
            continue
        if not check_id(l):
            out['problems'].append({'kind': 'bad_id', 'id': l.get('id'), 'said': 'left out of the fold'})
            continue
        if l['id'] in seen:
            continue
        seen.add(l['id'])
        clean.append(l)
    ctx = _Ctx()
    ctx.by_id = {l['id']: l for l in clean}
    by_id = ctx.by_id
    inceptions = {l['id']: l for l in clean if is_inception(l)}
    for hid, l in inceptions.items():
        c = (l.get('body') or {}).get('contract')
        if c != CONTRACT:
            out['problems'].append({'kind': 'contract_unknown', 'holon': hid, 'contract': c,
                                    'said': 'this holon was born under a contract this reader does not know (%r); '
                                            'it must be made again under %s' % (c, CONTRACT)})
    keepers = dict(keepers or {})
    for hid, l in inceptions.items():
        if isinstance(l.get('actor'), str):
            keepers[hid] = l['actor']
    order = _order(clean)

    # effective times: a chain's time never runs backwards; flag times ahead of the reader's clock
    clock_dt = _parse_ts(clock) or dt.datetime.now().astimezone()
    for l in order:
        t = _parse_ts(l.get('ts'))
        p = _str(l.get('prev'))
        ctx.parent[l['id']] = p
        if t is None:
            t = ctx.eff.get(p)
        elif p in ctx.eff and ctx.eff[p] and t < ctx.eff[p]:
            out['flags'].append({'id': l['id'], 'flag': 'ts_backward',
                                 'said': 'its time is earlier than its chain\'s previous line; read as that line\'s'})
            t = ctx.eff[p]
        ctx.eff[l['id']] = t
        if t and t > clock_dt + dt.timedelta(days=1):
            out['flags'].append({'id': l['id'], 'flag': 'ts_ahead',
                                 'said': 'its time is more than a day ahead of the reader\'s clock'})

    ctx.clock = clock_dt
    trust, why_t, admitted = _trust_pass(order, inceptions, keepers, ctx)
    ctx.trust = trust
    ctx.admitted = admitted
    ctx.keepers = keepers
    out['trust'] = trust
    held_forks, out['forks'], ctx.resolves = _forks(clean, trust)
    ahead = {f['id'] for f in out['flags'] if f['flag'] == 'ts_ahead'}
    if now:
        as_of = _str(now)
    else:
        cands = [ctx.eff[i] for i in trust if trust[i] in TRUSTED and i not in ahead and ctx.eff.get(i)]
        newest = max(cands) if cands else None
        if newest and newest > clock_dt:
            newest = clock_dt
        as_of = newest.isoformat(timespec='seconds') if newest else ''

    table = _delegations(clean, ctx)
    replaced, refused = _supersessions(order, ctx, tdefs, table)
    out['refused'].extend(refused)
    good_supersedes = {s['id'] for ss in replaced.values() for s in ss}

    used_once = set()
    items = {}         # item key -> item
    event_item = {}    # line id -> item key

    def plural(kind):
        return (idefs.get(kind) or {}).get('plural') or kind

    def resolve(line, paths, acts_on):
        missing = []
        for p in paths or []:
            for x in _get(line, p):
                key = event_item.get(x)
                if key and items[key]['kind'] in (acts_on or []):
                    return key, missing
                if x not in by_id:
                    missing.append(x)
        return None, missing

    for l in order:
        typ = _str(l.get('type'))
        out['audience'][l['id']] = l.get('audience') if l.get('audience') in AUDIENCES else 'holon'
        spec = tdefs.get(typ)
        t = trust.get(l['id'])
        if t in INVALID_TRUST:
            out['invalid'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'), 'holon': l.get('holon'),
                                   'invalid_reason': t if t != 'hidden' else why_t.get(l['id']),
                                   'said': why_t.get(l['id'], '')})
            continue
        if t not in TRUSTED:
            out['unverified'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'), 'for': l.get('for'),
                                      'holon': l.get('holon'), 'said': why_t.get(l['id'], 'unverified')})
            continue
        if l['id'] in held_forks:
            out['forked'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'), 'holon': l.get('holon'),
                                  'said': 'a fork in the actor\'s chain: held until the actor names the surviving branch'})
            continue
        if spec is None:
            out['unknown'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'),
                                   'holon': l.get('holon'), 'body': l.get('body')})
            continue
        why, signed_src, once_id = _validity(l, spec, table, used_once, by_id, ctx)
        if why:
            out['invalid'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'),
                                   'holon': l.get('holon'), 'invalid_reason': why})
            continue
        if l.get('reason') == 'untrusted':
            out['proposals'].append({'id': l['id'], 'type': typ, 'actor': l.get('actor'),
                                     'for': l.get('for'), 'holon': l.get('holon'),
                                     'would_fold_into': spec.get('item'),
                                     'body': {k: v for k, v in (l.get('body') or {}).items() if k not in SALT_KEYS},
                                     'said': 'its reason came from text an agent read; it waits for a person'})
            continue
        if once_id:
            used_once.add(once_id)   # a once-delegation, or a consent line ('consent:<id>'), is used up
        if signed_src:
            out['signed_for'].append({'id': l['id'], 'type': typ, 'agent': l.get('actor'),
                                      'for': l.get('for'), 'source': signed_src})

        body = dict(l.get('body') or {}) if isinstance(l.get('body'), dict) else {}
        if typ == 'supersede':
            if l['id'] in good_supersedes:
                for tgt in _as_list((l.get('links') or {}).get('supersedes')):
                    key = event_item.get(tgt)
                    if key and l['id'] not in items[key]['events']:
                        items[key]['events'].append(l['id'])
                        items[key].setdefault('superseded', []).append(tgt)
                        event_item[l['id']] = key
                        _merge_links(items[key], l)
            continue
        retracted_by = None
        if l['id'] in replaced:
            for s in replaced[l['id']]:
                sb = {k: v for k, v in (s.get('body') or {}).items() if k not in SALT_KEYS and not _is_elided(v)}
                if not sb:
                    retracted_by = s['id']
                for k, v in sb.items():
                    body[k] = v

        if typ == 'publish':
            if _str(l.get('actor')).startswith('person:') and t != 'vouched':
                want = body.get('audience')
                for x in _as_list(body.get('lines')):
                    tl = by_id.get(x)
                    if tl is None or x not in out['audience']:
                        continue
                    if tl.get('for') != l.get('for'):
                        out['refused'].append({'id': l['id'], 'line': x,
                                               'invalid_reason': 'a person publishes only their own lines'})
                        continue
                    if (tdefs.get(_str(tl.get('type'))) or {}).get('home_only'):
                        out['refused'].append({'id': l['id'], 'line': x,
                                               'invalid_reason': 'a home-only line never leaves its holon'})
                        continue
                    if want in AUDIENCES and _rank(want) > _rank(out['audience'][x]):
                        out['audience'][x] = want
            continue

        kind = spec.get('item') or 'none'
        acts_on = spec.get('acts_on') or ([kind] if kind != 'none' else [])
        creates = spec.get('creates') or 'never'
        target, missing = resolve(l, spec.get('target'), acts_on) if creates != 'always' else (None, [])
        holon = l.get('holon') or l.get('_held_in')

        if target is None and (creates == 'always' or (creates == 'if_no_target' and kind != 'none')):
            item = _new_item(kind, l, body, holon)
            item['state'] = (idefs.get(kind) or {}).get('initial')
            for k, v in (spec.get('create_set') or {}).items():
                val = _value(v, l, body)
                if k == 'state':
                    if val:
                        item['state'] = val
                elif item.get(k) in (None, '', []):
                    item[k] = val
            if retracted_by:
                item['state'] = 'retracted'
                item['retracted_by'] = retracted_by
            items[l['id']] = item
            event_item[l['id']] = l['id']
            out[plural(kind)].append(item)
        elif target is not None and t == 'vouched' and items[target].get('holon') != l.get('holon'):
            out['refused'].append({'id': l['id'], 'invalid_reason': 'a vouched copy informs but never acts on this '
                                                                    'holon\'s own items'})
        elif target is not None:
            item = items[target]
            item['events'].append(l['id'])
            event_item[l['id']] = target
            _merge_links(item, l)
            before = (item.get('state'), item.get('holder'))
            if retracted_by:
                item.setdefault('refused', []).append({'event': l['id'], 'why': 'retracted by %s' % retracted_by})
            else:
                why = _apply(item, spec.get('transitions'), l, body, keepers)
                if why:
                    item.setdefault('refused', []).append({'event': l['id'], 'why': why})
                elif typ == 'claim':
                    until = body.get('until') if isinstance(body.get('until'), str) else None
                    if until:
                        item['claim'] = {'event': l['id'], 'by': l.get('actor'), 'until': until,
                                         'previous_holder': before[1]}
                    else:
                        item.pop('claim', None)
        elif missing:
            out['pending'].append({'id': l['id'], 'type': typ, 'links_to': missing, 'said': 'not yet replicated'})
        elif kind != 'none' or spec.get('target'):
            out['pending'].append({'id': l['id'], 'type': typ, 'said': 'nothing held for it to act on'})

        also = spec.get('also')
        if isinstance(also, dict) and not retracted_by:
            key, _ = resolve(l, also.get('target'), also.get('acts_on'))
            if key and t == 'vouched' and items[key].get('holon') != l.get('holon'):
                key = None
            if key:
                it = items[key]
                if l['id'] not in it['events']:
                    it['events'].append(l['id'])
                _merge_links(it, l)
                for k, v in (also.get('set') or {}).items():
                    it[k] = _value(v, l, body)
        if typ == 'commit' and not retracted_by and isinstance(body.get('by'), str) and body.get('by'):
            key, _ = resolve(l, ['body.card'], ['card'])
            if key and t == 'vouched' and items[key].get('holon') != l.get('holon'):
                key = None
            if key:
                # A commitment never writes a date onto its Work Card. The card carries a reference to each commitment made on
                # it; the schedule compares the committed date with the card's computed finish (the buffer) and never obeys it.
                it = items[key]
                refs = [x for x in (it.get('committed_by') or []) if isinstance(x, dict) and x.get('commitment') != l['id']]
                refs.append({'commitment': l['id'], 'due_by': body['by'], 'for': l.get('for')})
                it['committed_by'] = refs

    # each commitment's reference on its Work Card carries its present shape: the committee, the stated buffer, and its state,
    # so the schedule compares only a live commitment (a released, declined or retracted one is shown and never compared)
    for item in items.values():
        for ref in item.get('committed_by') or []:
            c = items.get(ref.get('commitment'))
            if isinstance(c, dict):
                ref['state'] = c.get('state')
                ref['committee'] = c.get('committee') if isinstance(c.get('committee'), str) else None
                ref['buffer'] = c.get('buffer') if isinstance(c.get('buffer'), (int, float)) else None

    # computed, never remembered
    for c in out.get('commitments', []):
        end = c.get('kept_ts')
        card = items.get(c.get('card')) if isinstance(c.get('card'), str) else None
        if card and card.get('done_ts') and (not end or card['done_ts'] < end):
            end = card['done_ts']
        by, e = _date(c.get('by')), _date(end)
        c['gap_days'] = (e - by).days if (by and e) else None
    for d in out.get('delegations', []):
        if d.get('state') == 'live' and _past(d.get('until'), as_of):
            d['state'] = 'expired'
    for item in items.values():
        c = item.get('claim')
        if not isinstance(c, dict) or item.get('state') != 'taken' or item.get('holder') != c.get('by'):
            continue
        if _past(c.get('until'), as_of):
            item['state'] = 'ready'
            item['holder'] = c.get('previous_holder')
            item['claim_expired'] = c.get('event')
    for sf in out['signed_for']:
        key = event_item.get(sf['id'])
        if key:
            items[key]['signed_for'] = True
            items[key].setdefault('signed_for_by', []).append(
                {'event': sf['id'], 'agent': sf['agent'], 'source': sf['source']})
    for item in items.values():
        item['audience'] = out['audience'].get(item['id'], 'holon')
        if item['id'] in ctx.vouched:
            item['vouched_by'] = ctx.vouched[item['id']]
    out['vouched'] = dict(ctx.vouched)
    out['admitted'] = {h: {a: {'pubkey': e.get('pubkey'), 'key_id': key_id(e.get('pubkey')), 'by': e.get('by'),
                               'via': e.get('via'), 'person': e.get('person')} for a, e in m.items()}
                       for h, m in admitted.items()}
    out['as_of'] = as_of
    out['clock'] = clock_dt.isoformat(timespec='seconds')   # the reader's clock this fold was made by
    return out


def fold_hq(hq_dir, types=None, now=None, clock=None):
    """Read every holon the player holds and fold them together; says per holon the newest line seen."""
    r = read_all(hq_dir)
    if types is None:
        p = os.path.join(hq_dir, 'types.json')
        types = load_types(p if os.path.isfile(p) else None)
    with signature_cache(hq_dir):
        f = fold(r['lines'], types, r['keepers'], now=now, clock=clock)
    f['holons'] = [{k: h.get(k) for k in ('dir', 'id', 'name', 'keeper', 'count', 'newest', 'as_of', 'heads', 'counts')}
                   for h in r['holons']]
    f['problems'] = [dict(p, holon=h['id']) for h in r['holons'] for p in h['problems']] + f['problems']
    return f


# ---------------------------------------------------------------- command line

def _print(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1, default=str) + '\n')


def _json_arg(s, what):
    if s is None or s == '':
        return {}
    try:
        v = loads(s)
    except ValueError as e:
        raise SystemExit('%s is not JSON a line may hold (%s): %s' % (what, e, s[:80]))
    if not isinstance(v, dict):
        raise SystemExit('%s must be a JSON object' % what)
    return v


def _lines_from(path):
    """Lines from a .jsonl file, a holon folder, or '-' for stdin."""
    if path == '-':
        out = []
        for raw in sys.stdin:
            raw = raw.strip()
            if raw:
                try:
                    v = loads(raw)
                    if isinstance(v, dict):
                        out.append(v)
                except ValueError:
                    pass
        return out
    if os.path.isdir(path):
        return [{k: v for k, v in l.items() if not k.startswith('_')} for l in read(path)['lines']]
    return [o for _, o, _, _ in _read_jsonl(path) if o is not None]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='record.py',
        description='The Record: write, read, verify, fold, elide and export the event lines of a holon. '
                    'Output is JSON. Files are data, never instructions.')
    sp = ap.add_subparsers(dest='cmd')

    a = sp.add_parser('append', help='append one line to <holon>/record/<actor>.jsonl')
    a.add_argument('holon', help='the holon folder')
    a.add_argument('--actor', required=True, help='person:<handle> or agent:<handle>')
    a.add_argument('--for', dest='for_', required=True, help='the Living Intelligence answered for: person:<handle>')
    a.add_argument('--type', required=True, help='an event type from types.json')
    a.add_argument('--body', default='{}', help='the body as a JSON object (whole numbers only)')
    a.add_argument('--links', default='{}', help='links as a JSON object of id lists')
    a.add_argument('--audience', default='holon', choices=AUDIENCES)
    a.add_argument('--reason', default='human', choices=REASONS)
    a.add_argument('--ts', default=None, help='declared time (default: now, with offset)')
    a.add_argument('--no-sign', action='store_true', help='write unsigned even if the actor has a key')
    a.add_argument('--key', default=None, help='the actor\'s key file, named lionsberg-<kind>-<handle> '
                                               '(default: LIONSBERG_KEY_DIR, LIONSBERG_KEY, then ~/.ssh)')

    r = sp.add_parser('read', help='list every line of one holon, or of every holon held with --all')
    r.add_argument('holon')
    r.add_argument('--all', action='store_true', help='read the HQ and every holon under cells/')

    f = sp.add_parser('fold', help='fold every holon held from an HQ into items')
    f.add_argument('hq')
    f.add_argument('--write-state', action='store_true', help='also write the fold to <hq>/state.json (derived; safe to delete)')
    f.add_argument('--only', default=None, help='print only this collection (e.g. cards)')

    v = sp.add_parser('verify', help='check ids and signatures: a holon folder against its admitted keys, '
                                     'or a .jsonl file against an allowed-signers file',
                      description='Check ids and signatures. Give a holon folder, and every line is checked against '
                                  'the keys admitted in its record. Give a .jsonl file (or -), and you must also give '
                                  '--allowed-signers; a signature checked against the key it carries proves nothing, '
                                  'so this never does that.')
    v.add_argument('path', help='a holon folder, a .jsonl file, or - for stdin')
    v.add_argument('--allowed-signers', default=None, help='an ssh allowed-signers file naming each actor\'s key')

    e = sp.add_parser('elide', help='hide named fields of lines (reads a .jsonl file or -), keeping ids verifiable')
    e.add_argument('path')
    e.add_argument('--fields', required=True, help='comma-separated: body field names, actor, for, prev')

    x = sp.add_parser('export', help='print a holon\'s lines prepared to leave it, as JSON lines',
                      description='Print the holon\'s lines prepared to leave it. The first line printed is the '
                                  'attestation: the posture, the count and sha256 of the ids, signed by the exporter. '
                                  'The attestation names the exporter by role (the keeper of the holon, or a member) and '
                                  'is signed with the holon\'s own key when it is held here, else with the exporter\'s '
                                  'own key. '
                                  'Under names-hidden, actor, for, prev and every field naming an actor are elided, '
                                  'and each line\'s signature is removed, because an SSH signature names its signer by '
                                  'key; the ids and salted digests still prove each line\'s content, and the '
                                  'attestation vouches for the set. Under sealed, every body field is elided too. '
                                  'Under open, nothing is hidden and signatures stay. A form that keeps each '
                                  'author\'s signature while hiding names waits on the envelope.')
    x.add_argument('holon')
    x.add_argument('--posture', default='names-hidden', choices=POSTURES)
    x.add_argument('--exporter', default=None, help='who vouches for the export (default: the keeper)')
    x.add_argument('--key', default=None, help='the exporter\'s key file')

    ns = ap.parse_args(argv)
    if not ns.cmd:
        ap.print_help()
        return 2
    if ns.cmd == 'append':
        res = append(ns.holon, ns.actor, ns.for_, ns.type, _json_arg(ns.body, '--body'),
                     _json_arg(ns.links, '--links'), ns.audience, ns.reason, ts=ns.ts,
                     sign=False if ns.no_sign else None, key=ns.key)
        _print({'id': res['line']['id'], 'file': res['file'], 'signed': res['signed'], 'said': res['said']})
    elif ns.cmd == 'read':
        _print(read_all(ns.holon) if ns.all else read(ns.holon))
    elif ns.cmd == 'fold':
        res = fold_hq(ns.hq)
        if ns.write_state:
            with open(os.path.join(ns.hq, 'state.json'), 'w', encoding='utf-8') as fh:
                json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
        _print(res.get(ns.only) if ns.only else res)
    elif ns.cmd == 'verify':
        if os.path.isdir(ns.path) and not ns.allowed_signers:
            r = read(ns.path)
            keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
            f = fold(r['lines'], None, keepers)
            res = [{'id': l['id'], 'trust': f['trust'].get(l['id']), 'file': l['_file']} for l in r['lines']]
            _print({'lines': len(res), 'signed': sum(1 for x in res if x['trust'] == 'signed'),
                    'problems': r['problems'], 'results': res})
        elif not ns.allowed_signers:
            sys.stderr.write('verify: give a holon folder (its admitted keys are used) or --allowed-signers; '
                             'never neither\n')
            return 2
        else:
            res = [verify(l, ns.allowed_signers) for l in _lines_from(ns.path)]
            _print({'lines': len(res), 'id_ok': sum(1 for x in res if x['id_ok']),
                    'signed_valid': sum(1 for x in res if x['sig'] == 'valid'), 'results': res})
    elif ns.cmd == 'elide':
        names = [s.strip() for s in ns.fields.split(',') if s.strip()]
        for l in _lines_from(ns.path):
            sys.stdout.write(dumps(elide(l, names)) + '\n')
    elif ns.cmd == 'export':
        res = export(ns.holon, ns.posture, exporter=ns.exporter, key=ns.key)
        sys.stdout.write(json.dumps(res['attestation'], ensure_ascii=False) + '\n')
        for l in res['lines']:
            sys.stdout.write(dumps(l) + '\n')
        if res['said']:
            sys.stderr.write(res['said'] + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
