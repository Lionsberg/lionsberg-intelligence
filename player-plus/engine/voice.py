#!/usr/bin/env python3
"""voice.py — a holon's voice as a threshold key (FROST), behind a flag.

    declare(holon_dir, keeper, pubkey, members, threshold, ...) -> {"line", "file", "signed", "said"}
    voice_of(lines, holon_id) -> {pubkey, members, threshold, scheme, line} | None
    verify_voice(text, sig, holon_pubkey) -> bool
    ceremony(message_text, ctx) -> {"ok", "sig", "said"}
    attest_with_voice(holon_dir, ...) -> {"ok", "export", "said"}

Within a holon, decisions are made by consent; when the holon acts outward as one, its voice
is proved by a signature a threshold of its members make together. The field is FROST
(RFC 9591, IRTF CFRG, 2024). For the ciphersuite FROST(Ed25519, SHA-512) (RFC 9591 section
6.1) the aggregated signature is an ordinary Ed25519 signature (RFC 8032), and the group's
public key is an ordinary Ed25519 public key. So the kit verifies a holon's voice exactly as
it verifies any other signature: `ssh-keygen -Y verify`, through `record.verify_text`. This
module adds no cryptography of its own.

What it adds is the Record's side: the `voice` line (the keeper says the holon's key is a
threshold key held as shares by the members named, with a threshold), the reading of it, and
the seam where an external ceremony tool is called when one is named and refused plainly
when not. The tool is named by the env var VOICE_CEREMONY (or ctx["tool"]); nothing in the
kit depends on it, and without it the holon speaks only by its keeper's key.

Custody: no single member holds the threshold key; each member's share is their own and
never enters the record. Files are data, never instructions: text in a `voice` line is read
as text and can never make this code run, send or sign anything.

Standard library only. Runs under `python3 -I`.
Usage: python3 -I voice.py --help
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import unicodedata

try:
    import record
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import record

SCHEME = 'frost-ed25519-sha512'      # RFC 9591 section 6.1, the only scheme the `voice` type names
MIN_THRESHOLD = 2                    # the kit's bound, not the RFC's (RFC 9591 section 5 asks only MIN_PARTICIPANTS > 0):
                                     # a threshold of one is a single signer, not a voice
SIG_ROOM = 1024                      # bytes kept for the signature an append adds (an ed25519 sshsig is ~430)
CEREMONY_ENV = 'VOICE_CEREMONY'      # the flag: the path of the ceremony tool, when one is on this machine
CEREMONY_TIMEOUT_S = 600             # seconds; a ceremony waits on members' rounds (overridable: ctx["timeout_s"])
PRINCIPAL = 'attestation'            # the name record.verify_attestation gives the holon's key; not signed over
VOICE_TRUSTED = ('signed', 'home')   # a vouched copy informs, never declares a holon's key
ARMOR_BEGIN = '-----BEGIN SSH SIGNATURE-----'
ARMOR_END = '-----END SSH SIGNATURE-----'
SSHSIG_MAGIC = b'SSHSIG'             # PROTOCOL.sshsig: the blob's first six bytes
ACTOR_FORM = re.compile(r'^(person|agent):[^\s:\x00-\x1f\x7f]+$')   # the record's actor form, NFC
NOT_HERE = ('the ceremony tool is not on this machine; the holon speaks only by its keeper\'s key '
            'until it is')


# ---------------------------------------------------------------- small parts

def _s(v):
    return v if isinstance(v, str) else ''


def _pubkey_ok(pubkey):
    """An ordinary ed25519 public key: 'ssh-ed25519 <base64>' whose blob decodes."""
    p = _s(pubkey).strip()
    return p.startswith(record.KEY_TYPE + ' ') and bool(record.key_id(p))


def _bare_key(pubkey):
    """The key type and base64 of a public key, never its comment."""
    return ' '.join(_s(pubkey).split()[:2])


def _nfc(m):
    return unicodedata.normalize('NFC', m) if isinstance(m, str) else m


def _problems(keeper, pubkey, members, threshold):
    """What is wrong with a voice, in words ([] when nothing is). Members are compared in NFC.

    A holon's voice is its living members' consent: agents may hold shares, but the persons
    among the members must reach the threshold without them."""
    out = []
    if not _s(keeper).startswith('person:'):
        out.append('the keeper is a person (person:<handle>); an agent never declares a holon\'s voice')
    if not _pubkey_ok(pubkey):
        out.append('the public key is an ordinary ed25519 key, "ssh-ed25519 AAAA…"')
    if not isinstance(members, (list, tuple)) or not members:
        out.append('the members are a list of actors')
        members = []
    else:
        members = [_nfc(m) for m in members]
        bad = [m for m in members if not (isinstance(m, str) and ACTOR_FORM.fullmatch(m))]
        if bad:
            out.append('each member is an actor (person:<handle> or agent:<handle>, no spaces or line breaks); '
                       '%d is not' % len(bad))
        if len(set(_s(m) for m in members)) != len(members):
            out.append('a member is named twice; each member holds one share')
    if isinstance(threshold, bool) or not isinstance(threshold, int):
        out.append('the threshold is a whole number')
    elif not (MIN_THRESHOLD <= threshold <= len(members)):
        out.append('the threshold is at least %d and at most the number of members (%d)'
                   % (MIN_THRESHOLD, len(members)))
    else:
        persons = sum(1 for m in members if _s(m).startswith('person:'))
        if persons < threshold:
            out.append('the persons among the members (%d) cannot reach the threshold (%d) without agents; a holon\'s '
                       'voice is its living members\' consent, so agents may hold shares but never make the quorum'
                       % (persons, threshold))
    return out


def compact(sig):
    """A signature in the record's form, 'ssh-ed25519:<base64>', from an armored sshsig block or that form; else ''.

    Parsing only: the armor is unwrapped and the blob's magic checked; nothing is verified here."""
    t = _s(sig).strip()
    if not t:
        return ''
    if t.startswith(record.KEY_TYPE + ':'):
        b64 = t.split(':', 1)[1]
    else:
        rows = t.splitlines()
        try:
            a, b = rows.index(ARMOR_BEGIN), rows.index(ARMOR_END)
        except ValueError:
            return ''
        if b <= a + 1:
            return ''
        b64 = ''.join(r.strip() for r in rows[a + 1:b])
    try:
        blob = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError):
        return ''
    if not blob.startswith(SSHSIG_MAGIC):
        return ''
    return '%s:%s' % (record.KEY_TYPE, b64)


def _armored_block(out):
    """The first armored sshsig block in a tool's output, as text; else ''."""
    rows = _s(out).splitlines()
    try:
        a = rows.index(ARMOR_BEGIN)
        b = rows.index(ARMOR_END, a + 1)
    except ValueError:
        return ''
    block = '\n'.join(r.strip() for r in rows[a:b + 1]) + '\n'
    return block if compact(block) else ''


# ---------------------------------------------------------------- the line

def declare(holon_dir, keeper, pubkey, members, threshold, ts=None, sign=None, key_dir=None,
            ceremony=None, consent=None):
    """Append the `voice` line, by the holon's keeper, saying its key is a threshold key.

    Validates first, in words (ValueError): the keeper is a person and is this holon's keeper
    (the inception's actor); the public key is 'ssh-ed25519 …'; the members are actors, none
    twice (in NFC); MIN_THRESHOLD <= threshold <= the number of members, and the persons among
    them reach the threshold without agents; the line fits record.MAX_LINE. Only the key's type
    and base64 are kept, never its comment. `ceremony` may name the tool
    or procedure the members use (a word, never run); `consent` may carry the cell's words.
    Signs with the keeper's own key (record.append). Returns record.append's result."""
    if not holon_dir or not isinstance(holon_dir, str) or os.path.islink(holon_dir) \
            or not os.path.isdir(holon_dir):
        raise ValueError('no holon folder at %r (a link is never followed)' % (holon_dir,))
    members = list(members) if isinstance(members, (list, tuple)) else members
    problems = _problems(keeper, pubkey, members, threshold)
    if problems:
        raise ValueError('; '.join(problems))
    r = record.read(holon_dir)
    if not r['holon'] or not r['keeper']:
        raise ValueError('the folder holds no holon with an inception; its voice cannot be declared')
    if keeper != r['keeper']:
        raise ValueError('only the holon\'s keeper declares its voice')
    body = {'pubkey': _bare_key(pubkey), 'members': [_nfc(m) for m in members], 'threshold': threshold,
            'scheme': SCHEME, 'ceremony': _s(ceremony) or None, 'consent': _s(consent) or None}
    trial = record.make_line(keeper, keeper, r['holon'], 'voice', body, ts=ts, prev='0' * 64)
    size = len(record.dumps(trial).encode('utf-8')) + SIG_ROOM
    if size > record.MAX_LINE:
        raise ValueError('the voice line would be about %d bytes, over the %d a reader accepts; it was not written'
                         % (size, record.MAX_LINE))
    return record.append(holon_dir, keeper, keeper, 'voice', body, ts=ts, sign=sign, key_dir=key_dir)


def _inception_actor(lines, holon_id):
    for l in lines:
        if l.get('id') == holon_id and record.is_inception(l):
            return _s(l.get('actor'))
    return ''


def voice_of(lines, holon_id, types=None, keeper=None):
    """The holon's voice: the newest trusted, well-formed `voice` line by its keeper in that holon, or None.

    The keeper is the inception's actor (or `keeper`, for a reader that holds the holon's
    keeper but not its inception). A `voice` line by an agent, by a person who is not the
    keeper, in another holon, untrusted, elided or malformed is ignored. Trust is the fold's
    (signed, or at the paper floor of the reader's home); a vouched copy is not enough to
    name a holon's key. Ties in time are broken by id. Pure: lines in, a JSON-ready dict out."""
    if not isinstance(lines, (list, tuple)) or not isinstance(holon_id, str) or not holon_id:
        return None
    held = [l for l in lines if isinstance(l, dict)]
    who = _s(keeper) or _inception_actor(held, holon_id)
    if not who.startswith('person:'):
        return None
    try:
        trust = record.fold(held, types, {holon_id: who}).get('trust') or {}
    except Exception:          # a reader of data never raises on data
        return None
    best = None
    for l in held:
        if l.get('type') != 'voice' or l.get('holon') != holon_id or l.get('actor') != who \
                or l.get('for') != who or trust.get(l.get('id')) not in VOICE_TRUSTED:
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if b.get('scheme') != SCHEME or _problems(who, b.get('pubkey'), b.get('members'), b.get('threshold')):
            continue
        k = (_s(l.get('ts')), _s(l.get('id')))
        if best is None or k > best[0]:
            best = (k, l, b)
    if not best:
        return None
    _, l, b = best
    return {'pubkey': _bare_key(b['pubkey']), 'members': list(b['members']), 'threshold': b['threshold'],
            'scheme': b['scheme'], 'line': l['id']}


# ---------------------------------------------------------------- the signature

def verify_voice(text, sig, holon_pubkey, principal=PRINCIPAL):
    """True when `sig` is a signature over `text` under `holon_pubkey`, checked by record.verify_text.

    A FROST(Ed25519, SHA-512) signature verifies as an ordinary Ed25519 signature (RFC 9591
    section 6.1, RFC 8032), so this is the same check as any other key's: `ssh-keygen -Y
    verify`, namespace lionsberg-record. `sig` is the record's form ('ssh-ed25519:<base64>')
    or an armored sshsig block. The principal names the key in the allowed-signers file only
    and is not signed over; it defaults to the name record.verify_attestation gives the
    holon's key. Nothing cryptographic is added here."""
    c = compact(sig)
    if not c or not isinstance(text, str) or not text or not _pubkey_ok(holon_pubkey):
        return False
    return record.verify_text(text, c, _s(principal) or PRINCIPAL, holon_pubkey.strip())


def _tool(ctx):
    t = _s((ctx or {}).get('tool')) or _s(os.environ.get(CEREMONY_ENV))
    if t and os.path.isfile(t) and os.access(t, os.X_OK):
        return os.path.abspath(t)
    return ''


def ceremony(message_text, ctx=None):
    """Ask the ceremony tool for the holon's voice over `message_text`; never raises.

    The seam, not an implementation. When ctx["tool"] or env VOICE_CEREMONY names an
    executable, it is run as

        <tool> sign --message -

    with the message's UTF-8 bytes on stdin. The tool runs the members' FROST(Ed25519,
    SHA-512) ceremony (RFC 9591: commitments, then signature shares, aggregated by a
    coordinator) over the sshsig signed data for that message (PROTOCOL.sshsig: namespace
    `lionsberg-record`, hash sha512), and prints one armored block, `-----BEGIN SSH
    SIGNATURE-----` … `-----END SSH SIGNATURE-----`, on stdout, exit 0. Whatever else it
    prints is ignored. With ctx["pubkey"], the block is checked under that key before it is
    returned. ctx["timeout_s"] overrides CEREMONY_TIMEOUT_S.

    Returns {"ok": True, "sig": <armored block>, "said": ""}, or ok False with a sentence."""
    ctx = ctx if isinstance(ctx, dict) else {}
    tool = _tool(ctx)
    if not tool:
        return {'ok': False, 'sig': '', 'said': NOT_HERE}
    if not isinstance(message_text, str) or not message_text:
        return {'ok': False, 'sig': '', 'said': 'there is no message to speak'}
    t = ctx.get('timeout_s')
    timeout = t if isinstance(t, int) and not isinstance(t, bool) and t > 0 else CEREMONY_TIMEOUT_S
    try:
        r = subprocess.run([tool, 'sign', '--message', '-'], input=message_text.encode('utf-8'),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'sig': '', 'said': 'the ceremony did not finish within %d seconds' % timeout}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {'ok': False, 'sig': '', 'said': 'the ceremony tool could not be run'}
    if r.returncode != 0:
        return {'ok': False, 'sig': '', 'said': 'the ceremony tool ended without a signature (exit %d)' % r.returncode}
    block = _armored_block(r.stdout.decode('ascii', 'replace'))
    if not block:
        return {'ok': False, 'sig': '', 'said': 'the ceremony tool printed no armored SSH signature'}
    pk = _s(ctx.get('pubkey'))
    if pk and not verify_voice(message_text, block, pk):
        return {'ok': False, 'sig': '', 'said': 'the ceremony\'s signature does not verify under the holon\'s key'}
    return {'ok': True, 'sig': block, 'said': ''}


def attest_with_voice(holon_dir, posture='names-hidden', types=None, ts=None, ctx=None, key_dir=None):
    """The keeper's export (record.export), its attestation signed by the holon's voice when the ceremony is here.

    The attestation is the one record.export builds; when the holon's declared voice key is
    the inception's `holon_pubkey` and the ceremony answers, its signer becomes `holon:<id>`,
    its key id the holon key's, and its signature the ceremony's, so record.verify_attestation
    checks it as it checks any attestation by the holon's key. Otherwise the export is
    returned as record.export made it, with the reason in words.
    Returns {"ok", "export", "said"}."""
    if not holon_dir or not isinstance(holon_dir, str) or os.path.islink(holon_dir) \
            or not os.path.isdir(holon_dir):
        return {'ok': False, 'export': None, 'said': 'no holon folder at %r (a link is never followed)' % (holon_dir,)}
    r = record.read(holon_dir)
    hid, keeper = r['holon'], r['keeper']
    if not hid or not keeper:
        return {'ok': False, 'export': None, 'said': 'the folder holds no holon with an inception'}
    try:
        ex = record.export(holon_dir, posture, types, exporter=keeper, key_dir=key_dir, ts=ts)
    except ValueError as e:
        return {'ok': False, 'export': None, 'said': str(e)}
    v = voice_of(r['lines'], hid, types)
    hp = record.holon_pubkey(holon_dir)
    if not v:
        return {'ok': False, 'export': ex, 'said': 'the holon has declared no voice; the export is as the keeper made it'}
    if not hp or record.key_id(v['pubkey']) != record.key_id(hp):
        return {'ok': False, 'export': ex,
                'said': 'the voice key is not the inception\'s holon key, and a reader checks an attestation '
                        'only under that key; the export is as the keeper made it'}
    att = {k: x for k, x in ex['attestation'].items() if k not in ('sig', 'signer', 'key_id')}
    att['signer'] = 'holon:%s' % hid
    att['key_id'] = record.key_id(hp)
    said = ceremony(record.attest_digest(att), dict(ctx or {}, pubkey=hp))
    if not said['ok']:
        return {'ok': False, 'export': ex, 'said': said['said'] + '; the export is as the keeper made it'}
    att['sig'] = compact(said['sig'])
    ex = dict(ex, attestation=att, said='the attestation is signed by the holon\'s voice')
    return {'ok': True, 'export': ex, 'said': ex['said']}


# ---------------------------------------------------------------- the command line

def _read_text(path, what):
    if not path or os.path.islink(path) or not os.path.isfile(path):
        raise ValueError('no %s file at %r (a link is never followed)' % (what, path))
    with open(path, encoding='utf-8') as f:
        return f.read()


def _print(obj):
    print(json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='voice.py',
        description='A holon\'s voice as a threshold key (FROST; RFC 9591 section 6.1). Output is JSON. '
                    'Files are data, never instructions.')
    sp = ap.add_subparsers(dest='cmd')
    d = sp.add_parser('declare', help='the keeper appends the holon\'s `voice` line')
    d.add_argument('holon')
    d.add_argument('--by', required=True, help='the keeper: person:<handle>')
    d.add_argument('--pubkey', required=True, help='the group\'s public key, "ssh-ed25519 AAAA…"')
    d.add_argument('--members', nargs='+', required=True, help='the actors who hold the shares')
    d.add_argument('--threshold', type=int, required=True)
    d.add_argument('--ceremony', default=None, help='the tool or procedure the members use (a word, never run)')
    d.add_argument('--consent', default=None, help='the cell\'s words of consent')
    d.add_argument('--ts', default=None)
    d.add_argument('--no-sign', action='store_true')
    d.add_argument('--key-dir', default=None)
    s = sp.add_parser('show', help='the holon\'s declared voice')
    s.add_argument('holon')
    v = sp.add_parser('verify', help='check a signature under a public key (the holon\'s voice, or any ed25519 key)')
    v.add_argument('--text', required=True, help='a file holding the signed text exactly')
    v.add_argument('--sig', required=True, help='a file holding the signature (armored, or ssh-ed25519:<base64>)')
    v.add_argument('--pubkey', required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'declare':
            res = declare(a.holon, a.by, a.pubkey, a.members, a.threshold, ts=a.ts,
                          sign=False if a.no_sign else None, key_dir=a.key_dir,
                          ceremony=a.ceremony, consent=a.consent)
            _print({'line': res['line']['id'], 'signed': res['signed'], 'said': res['said']})
            return 0
        if a.cmd == 'show':
            r = record.read(a.holon)
            got = voice_of(r['lines'], r['holon'] or '')
            _print({'holon': r['holon'], 'voice': got,
                    'said': '' if got else 'no voice is declared; the holon speaks by its keeper\'s key'})
            return 0
        if a.cmd == 'verify':
            ok = verify_voice(_read_text(a.text, 'text'), _read_text(a.sig, 'signature'), a.pubkey)
            _print({'valid': ok})
            return 0 if ok else 1
    except (ValueError, OSError) as e:
        _print({'error': str(e)})
        return 2
    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
