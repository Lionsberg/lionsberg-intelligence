#!/usr/bin/env python3
"""mail.py — mail inside the private network, as a carrier of lines and never a second truth.

One record, many transports. A mail carries a signed line in its body, or it carries prose.
The record stays the truth whichever carried it (SCHEMA.md, Messaging; hud/DESIGN-MAIL.md).

    to_mail(line, to_addr, from_addr, posture, card=None, ...) -> an RFC 5322 message
    from_mail(message, hq_dir=None) -> (line | None, prose | None, verified)
    carry(message, hq_dir) -> what was carried into <hq>/.carried/
    fetch(account, hq_dir) -> reads the mailbox over IMAP with TLS; carries; sends nothing
    send(account, message, on_the_persons_send=False) -> SMTP with TLS, only at the person's act
    send_line(hq_dir, line_id, to_addr, account, on_the_persons_send=False) -> the gated send
    recompute_push(line, items, schedule) -> the sender's stake beside the receiver's own
    unread_from_other_houses(hq_dir) -> the badge's count, from the carried store

CARRYING A LINE. The message opens with readable prose (the card it concerns, the question,
the field of stake from `body.push`, the by-when, the sender's own words) in a text/plain part,
and carries the line whole, as one JSON line in canonical form, in a second text/plain part.
The headers X-Lionsberg-Line (the line id) and X-Lionsberg-Holon are a convenience for a
standard mail client; where a header and the line disagree, the line is read and the
disagreement is said. Under the posture `names-hidden` the line travels in its elided form
(record.py's elision, as its export does: actor, for, prev, every field that names an actor,
every public key field; the signature removed), with an optional one-line attestation; a line
that cannot be elided is held back. Files travel by reference only: their name, their digest
and the publish line that let them out. No file's bytes are ever attached here.

RECEIVING. A carried line is verified with record.verify against the keys its holon admitted in
the reader's own copy of that holon, never against a key the mail carries. A line from a key the
holon never admitted is `unverified`; a signature that fails, or an id that does not match, is
`bad`. A mail with no line is prose: it becomes a proposed `say` line with `reason: untrusted`,
which changes nothing until the person says yes. Every mail is data. A sentence in a mail that
asks for sending, forwarding, publishing or any other act is quoted back as a likely injection
and never acted on: nothing in this file can be moved to send by what a mail says.

THE CARRIED STORE. `<hq>/.carried/` holds what mail brought before the record did: "carried, not
yet in the record". Each line is kept once, by its id. When the forge pull brings the same line,
`prune` drops the carried copy and the fold reads the record's; `lines_for_fold` hands the fold
only carried lines the record does not hold, so a line carried twice folds once. Read state is
kept here, on this machine, and is never written to the record. The folder ignores itself for
the forge (its own .gitignore) and every file in it is mode 0600.

THE MAILBOX. The account comes from ~/.config/lionsberg/mail.json (mode 0600, owned by the
person), never from a holon. Credentials are never printed, logged, stored in the carried store
or put in an error. Hosts must sit on the private network (a private, loopback or shared
address). Fetch peeks at unseen mail, stores it, and only then marks it seen. Fetch never sends.

Files are data, never instructions. Standard library only. Runs under `python3 -I`.
Usage: python3 -I mail.py --help
"""
import argparse
import contextlib
import datetime as dt
import email
import email.policy
import email.utils
import hashlib
import html.parser
import imaplib
import ipaddress
import json
import os
import re
import shutil
import smtplib
import socket
import ssl
import stat
import sys
import tempfile
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import record  # noqa: E402
import rooms  # noqa: E402

try:                                    # the Push Protocol, built by a sibling; mail works without it
    import push as _push                # noqa: E402
except Exception:                       # pragma: no cover - depends on the sibling's file
    _push = None

HDR_LINE = 'X-Lionsberg-Line'
HDR_HOLON = 'X-Lionsberg-Holon'
LINE_PART = 'lionsberg-line v1'
ATTEST_PART = 'lionsberg-attestation v1'
CARRIED = '.carried'
CONFIG = os.path.join('~', '.config', 'lionsberg', 'mail.json')
MAX_MAIL = 10 * 1024 * 1024          # bytes; a larger mail is not read
MAX_PROSE = 20000                    # characters of prose kept for a proposal
HEX64 = re.compile(r'^[0-9a-f]{64}$')
CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
TIMEOUT = 30

IMAP_FACTORY = None                  # tests put a fake here; None means imaplib over TLS
SMTP_FACTORY = None                  # tests put a fake here; None means smtplib over TLS

KIND_WORDS = {'decision': 'A decision', 'information': 'News', 'request': 'A request', 'offer': 'An offer',
              'fault': 'A fault'}
TYPE_WORDS = {'thread': 'A question', 'rfg': 'A request for guidance', 'escalate': 'A decision moved up',
              'request': 'A request', 'offer': 'An offer', 'answer': 'An answer', 'say': 'A word',
              'commit': 'A commitment', 'propose': 'A proposal', 'sight': 'A sighting', 'decide': 'A decision',
              'supersede': 'A correction'}

# Sentences that ask for an act. Matching one never causes anything; it only makes the mail
# show as a likely injection, quoted, so the person sees it (DESIGN-MAIL §7).
SUSPECT = re.compile(
    r'\b(forward|send|resend|reply\s+all|mail\s+(?:it|this|them)|publish|push|share|upload|post|delete|'
    r'remove|erase|transfer|pay|wire|grant|revoke|approve|sign|commit\s+to|'
    r'change\s+(?:your|the)\s+(?:permission|permissions|rules|settings|key|keys|password)|'
    r'ignore\s+(?:all\s+|any\s+)?(?:previous|prior|earlier|your)\s+instructions|'
    r'reveal|disclose|password|credential|credentials|api\s+key|private\s+key)\b', re.I)


class Refused(Exception):
    """An act this module will not do, said in plain words. Never carries a credential."""


# ---------------------------------------------------------------- small parts

def _s(v):
    return v if isinstance(v, str) else ''


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def _sha(b):
    if isinstance(b, str):
        b = b.encode('utf-8', 'replace')
    return hashlib.sha256(b or b'').hexdigest()


def _body(line):
    b = line.get('body') if isinstance(line, dict) else None
    return b if isinstance(b, dict) else {}


def _links(line, key):
    lk = line.get('links') if isinstance(line, dict) else None
    v = (lk or {}).get(key) if isinstance(lk, dict) else None
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def _shown(v):
    """A value as a reader sees it: an elided value is said as hidden."""
    if isinstance(v, dict) and 'elided' in v:
        return '· hidden by the room ·'
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return '' if v is None else str(v)


def _write_private(path, text):
    """Write a file atomically, mode 0600."""
    d = os.path.dirname(path)
    os.makedirs(d, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=d)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- the home and its holons

def _holon_dirs(hq_dir):
    """{holon id: folder} for every holon the reader holds: the home first, then each cell."""
    out = {}
    for d in record.hold(hq_dir) if hq_dir else []:
        hid = _s(record.holon_info(d).get('id'))
        if hid and hid not in out:
            out[hid] = d
    return out


def _home_id(hq_dir):
    return _s(record.holon_info(hq_dir).get('id')) if hq_dir else ''


def _person(hq_dir):
    """The person the home serves: its keeper by the inception line, else holon.json's keeper."""
    if not hq_dir:
        return ''
    r = record.read(hq_dir)
    return _s(r.get('keeper')) or _s(record.holon_info(hq_dir).get('keeper'))


def _home_actors(hq_dir):
    """The person and the agents the person let into the home: lines by them are not from another house."""
    person = _person(hq_dir)
    out = {person} if person else set()
    if hq_dir:
        for l in record.read(hq_dir)['lines']:
            if l.get('type') == 'affirm' and l.get('actor') == person:
                a = _s(_body(l).get('agent'))
                if a:
                    out.add(a)
    return out


def _home_agent(hq_dir):
    person = _person(hq_dir)
    for a in sorted(_home_actors(hq_dir)):
        if a.startswith('agent:'):
            return a
    return person


def _admitted(holon_dir, home=False):
    try:
        return record.holon_keys(holon_dir, home=home)
    except Exception:
        return {}


def _posture(hq_dir, holon_id):
    """The posture of a holon: its newest trusted `posture` line, else open."""
    d = _holon_dirs(hq_dir).get(holon_id)
    if not d:
        return 'open'
    r = record.read(d)
    if d == hq_dir:
        for l in r['lines']:
            if l['_file'].startswith('record/'):
                l['_home_record'] = True
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    trust = record.fold(r['lines'], None, keepers).get('trust') or {}
    best = None
    for l in r['lines']:
        if l.get('type') == 'posture' and trust.get(l['id']) in record.TRUSTED:
            p = _s(_body(l).get('posture'))
            # a participation posture (Chatham House, fishbowl, …) reads as the export posture it
            # leaves under (rooms.export_posture); an unknown named posture reads as sealed
            if p not in record.POSTURES:
                p = rooms.export_posture(p)
            if p in record.POSTURES and (best is None or _s(l.get('ts')) >= _s(best.get('ts'))):
                best = l
    if not best:
        return 'open'
    p = _s(_body(best).get('posture'))
    return p if p in record.POSTURES else rooms.export_posture(p)


# ---------------------------------------------------------------- names hidden

def hide_names(line, posture='names-hidden', types=None, handles=()):
    """The line as it may leave under a posture, by record.py's elision.

    names-hidden: actor, for and prev, every field whose registry kind is an actor, every public
    key field, and every field that names an actor are elided, and the signature is removed.
    sealed: every body field as well. open: the line unchanged. Raises Refused for a line with
    no salt: its names cannot be hidden without breaking its id, so it is held back."""
    if not isinstance(line, dict):
        raise Refused('There is no line to carry.')
    clean = {k: v for k, v in line.items() if not (isinstance(k, str) and k.startswith('_'))}
    if posture == 'open':
        return record.ordered(clean)
    if posture not in record.POSTURES:
        raise Refused('The posture is one of %s.' % ', '.join(record.POSTURES))
    if not record.is_salted(clean):
        raise Refused('This line has no salt, so its names cannot be hidden. It is held back.')
    types = types or record.load_types()
    body = _body(clean)
    hs = set(h for h in handles if isinstance(h, str))
    for k in ('actor', 'for'):
        if isinstance(clean.get(k), str):
            hs.add(record.handle_of(clean[k]))
    spec = (types.get('types') or {}).get(_s(clean.get('type'))) or {}
    actor_fields = {f.get('name') for f in (spec.get('fields') or [])
                    if isinstance(f, dict) and f.get('kind') in ('actor', 'actors')}
    if posture == 'sealed':
        names = ['actor', 'for', 'prev'] + [k for k in body if k not in record.SALT_KEYS]
    else:
        names = ['actor', 'for', 'prev'] + [k for k, v in body.items() if k not in record.SALT_KEYS and (
            k in actor_fields or k in record.KEY_FIELDS or record._names_in(v, hs))]
    out = record.elide(clean, names)
    out.pop('sig', None)
    out.pop('_said', None)
    return out


def attest_one(holon_dir, line, exporter, key_dir=None, ts=None):
    """A one-line attestation for a names-hidden line, signed with the holon's own key.

    It names the exporter by role ("the keeper of <holon>"), the count (one), the sha256 of the id
    and no chain heads, so record.verify_attestation checks it against the holon key its inception
    carries. Unlike record.export, it never falls back to a person's key: a person's key names the
    person, and the room's mail must not. Returns the attestation, or None (the exporter is not
    the keeper, or the holon key is not held here); the line then travels unattested and is
    shown as unverified on arrival."""
    if not holon_dir or not isinstance(line, dict) or not exporter:
        return None
    r = record.read(holon_dir)
    keeper = r['keeper'] or _s(record.holon_info(holon_dir).get('keeper'))
    role = ('the keeper of %s' if exporter == keeper else 'a member of %s') % r['holon']
    att = {'v': 1, 'attest': 'export', 'posture': 'names-hidden', 'holon': r['holon'], 'count': 1,
           'ids_sha256': record._sha(_s(line.get('id'))), 'by': role, 'ts': ts or _now(), 'heads': []}
    if exporter != keeper:
        return None                       # only the holon's own key may vouch here: a person's key names them
    hk = record.find_key(None, 'holon:%s' % r['holon'], key_dir)
    if not hk or record.key_id(record.pubkey_of(hk)) != record.key_id(record.holon_pubkey(holon_dir)):
        return None
    att['signer'] = 'holon:%s' % r['holon']
    att['key_id'] = record.key_id(record.pubkey_of(hk))
    att['sig'] = record.sign_text(record._attest_digest(att), hk)
    return att if att['sig'] else None


# ---------------------------------------------------------------- carrying a line

def _question(line):
    b = _body(line)
    for k in ('text', 'question', 'title', 'what', 'ask'):
        if k in b:
            return _shown(b[k])
    return ''


def _subject(line, card_title):
    b = _body(line)
    p = b.get('push') if isinstance(b.get('push'), dict) else {}
    if line.get('type') == 'supersede' and not [k for k in b if k not in record.SALT_KEYS]:
        head = 'Withdrawn: ' + (TYPE_WORDS.get('thread'))
    else:
        head = KIND_WORDS.get(_s(p.get('kind'))) or TYPE_WORDS.get(_s(line.get('type'))) or 'A line'
    s = head + (' on ' + card_title if card_title else '')
    by = p.get('by')
    if by and not isinstance(by, dict):
        s += ' · by ' + str(by)
    return re.sub(r'[\r\n]+', ' ', s)[:200]


def stake_lines(push):
    """The field of stake as readable lines, one per field that is filled (DESIGN-MAIL §3.2)."""
    if not isinstance(push, dict) or not push:
        return ['No stake given.']
    out = []
    if push.get('kind'):
        out.append('Kind: %s.' % _shown(push['kind']))
    if push.get('by'):
        out.append('By: %s%s.' % (_shown(push['by']),
                                  (', because ' + _shown(push['why_by'])) if push.get('why_by') else ''))
    if isinstance(push.get('size'), int):
        out.append('About %d minutes.' % push['size'])
    if isinstance(push.get('blocks'), list):
        n = len(push['blocks'])
        out.append('%s wait%s.' % ('One card' if n == 1 else '%d cards' % n, 's' if n == 1 else '')
                   + (' On the critical chain.' if push.get('critical') else ''))
    elif push.get('critical'):
        out.append('On the critical chain.')
    w = push.get('who_waits')
    if isinstance(w, dict) and w:
        parts = ['%s %s' % (v, k) for k, v in w.items() if isinstance(v, int) and v]
        if parts:
            out.append('Who waits: %s.' % ', '.join(parts))
    elif isinstance(w, str) and w:
        out.append('Who waits: %s.' % w)
    br = push.get('blast_radius')
    if isinstance(br, dict):
        out.append('Reversible.' if br.get('reversible', True) is not False else 'Not reversible.')
    elif isinstance(br, str) and br:
        out.append('Blast radius: %s.' % br)
    for k, label in (('cost_if_late', 'If late'), ('alternatives', 'If no answer'), ('asked', 'They said'),
                     ('expires', 'Expires')):
        if push.get(k):
            out.append('%s: %s.' % (label, _shown(push[k]).rstrip('.')))
    c = push.get('calibration')
    if isinstance(c, dict) and c.get('said'):
        out.append('Their record, as they compute it: %s.' % _shown(c['said']))
    elif isinstance(c, str) and c:
        out.append('Their record, as they compute it: %s.' % c)
    return out or ['No stake given.']


def readable(line, card_title=None, holon_name=None, posture='open', attachments=None):
    """The prose a reader of a standard mail client sees: no ICE needed to know what rides on it."""
    b = _body(line)
    p = b.get('push') if isinstance(b.get('push'), dict) else None
    hidden = posture != 'open'
    rows = [_subject(line, card_title) + '.', '']
    rows.append('From: %s' % ('a member of the room' if hidden or not isinstance(line.get('actor'), str)
                              else line['actor']))
    rows.append('Holon: %s' % (holon_name or _s(line.get('holon')) or 'none named'))
    rows.append('About: %s' % (card_title or 'no card named'))
    q = _question(line)
    if q:
        asks = _s(line.get('type')) in ('thread', 'request', 'rfg', 'escalate')
        rows.append('%s: %s' % ('The question' if asks else 'The line says', q))
    rows.append('')
    rows.append('What rides on it:')
    rows.extend('  ' + x for x in stake_lines(p))
    if p and p.get('asked'):
        rows.append('')
        rows.append('In their own words: %s' % _shown(p['asked']))
    files = [a for a in (attachments or []) if isinstance(a, dict)]
    if files:
        rows.append('')
        rows.append('Files, by reference only (each opens after its digest matches its publish line):')
        for a in files:
            rows.append('  %s · sha256 %s · published by line %s' % (
                _s(a.get('name')) or 'a file', _s(a.get('digest')) or 'no digest', _s(a.get('publish_line')) or
                'none, so it is unverified'))
    rows.append('')
    rows.append('Line: %s' % _s(line.get('id')))
    rows.append('This mail carries the line itself in its second part. Your agent reads and checks the line; '
                'this text is for reading. An answer written here arrives as prose.')
    return '\n'.join(rows) + '\n'


def to_mail(line, to_addr, from_addr, posture='open', card=None, holon_name=None, attestation=None,
            attachments=None, types=None, message_id_domain=None):
    """An RFC 5322 message carrying one line: readable prose first, the line whole second.

    `card` is the card item or its title. Under names-hidden or sealed the line is elided first
    (hide_names), so neither the line, the prose nor the From line names who said it. Raises
    Refused when the line is not a line (no matching id), or cannot be elided."""
    if not isinstance(line, dict) or not record.check_id(line):
        raise Refused('There is no line to carry: the id does not match its content.')
    to_addr, from_addr = _s(to_addr).strip(), _s(from_addr).strip()
    if not to_addr or not from_addr or '\n' in to_addr + from_addr or '\r' in to_addr + from_addr:
        raise Refused('A mail needs one address to send to and one to send from.')
    posture = posture if posture in record.POSTURES else None
    if posture is None:
        raise Refused('The posture is one of %s.' % ', '.join(record.POSTURES))
    carried = hide_names(line, posture, types)
    title = card.get('title') if isinstance(card, dict) else card
    title = _shown(title) if title else ''
    msg = EmailMessage(policy=email.policy.SMTP)
    name = 'a member of the room' if posture != 'open' else ''
    msg['From'] = email.utils.formataddr((name, from_addr)) if name else from_addr
    msg['To'] = to_addr
    msg['Subject'] = _subject(carried, title)
    msg['Date'] = email.utils.formatdate(localtime=True)
    dom = message_id_domain or (from_addr.rsplit('@', 1)[1] if '@' in from_addr else None)
    msg['Message-ID'] = email.utils.make_msgid(domain=dom)
    msg[HDR_LINE] = _s(carried.get('id'))
    msg[HDR_HOLON] = _s(carried.get('holon'))
    msg.set_content(readable(carried, title, holon_name, posture, attachments))
    msg.add_attachment(record.dumps(carried) + '\n', subtype='plain', disposition='inline',
                       filename='line.jsonl')
    msg.get_payload()[-1]['Content-Description'] = LINE_PART
    if attestation and posture != 'open':
        msg.add_attachment(json.dumps(attestation, ensure_ascii=False, sort_keys=True) + '\n', subtype='plain',
                           disposition='inline', filename='attestation.json')
        msg.get_payload()[-1]['Content-Description'] = ATTEST_PART
    return msg


# ---------------------------------------------------------------- receiving

class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []

    def handle_data(self, d):
        self.out.append(d)


def parse(message):
    """An EmailMessage from bytes, text or a message; None when it cannot be read."""
    if isinstance(message, email.message.Message):
        return message
    try:
        if isinstance(message, str):
            message = message.encode('utf-8', 'replace')
        if not isinstance(message, (bytes, bytearray)) or len(message) > MAX_MAIL:
            return None
        return email.message_from_bytes(bytes(message), policy=email.policy.default)
    except Exception:
        return None


def _part_text(part):
    try:
        t = part.get_content()
        return t if isinstance(t, str) else ''
    except Exception:
        try:
            raw = part.get_payload(decode=True) or b''
            return raw.decode('utf-8', 'replace')
        except Exception:
            return ''


def _scan(msg):
    """(lines, attestations, prose text) from a message's text parts. Nothing here is obeyed."""
    lines, atts, prose, html_prose = [], [], [], []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        if ctype not in ('text/plain', 'text/html'):
            continue
        text = _part_text(part)
        if ctype == 'text/html':
            p = _Text()
            with contextlib.suppress(Exception):
                p.feed(text)
            html_prose.append(''.join(p.out))
            continue
        found = False
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw.startswith('{') or len(raw.encode('utf-8', 'replace')) > record.MAX_LINE:
                continue
            try:
                obj = record.loads(raw)
            except (ValueError, RecursionError):
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get('attest') == 'export':
                atts.append(obj)
                found = True
            elif isinstance(obj.get('id'), str) and 'type' in obj and 'v' in obj:
                lines.append({k: v for k, v in obj.items() if not (isinstance(k, str) and k.startswith('_'))})
                found = True
        if not found:
            prose.append(text)
    text = '\n'.join(x for x in prose if x.strip()) or '\n'.join(x for x in html_prose if x.strip())
    text = CONTROL.sub('', text)           # control characters are never prose
    return lines, atts, text.strip()


def _allowed_signers(keys):
    """A temporary allowed-signers file from the holon's admitted keys. Returns (folder, path)."""
    tmp = tempfile.mkdtemp(prefix='lionsberg-mail-')
    path = os.path.join(tmp, 'allowed')
    with open(path, 'w', encoding='utf-8') as f:
        for actor, pk in sorted(keys.items()):
            if isinstance(actor, str) and record._PRINCIPAL_OK.match(actor) and _s(pk).startswith('ssh-ed25519 '):
                f.write('%s namespaces="%s" %s\n' % (actor, record.NAMESPACE, pk))
    return tmp, path


def verify_line(line, hq_dir, attestation=None):
    """(verified, said) for a carried line: verified · unverified · bad.

    Checked against the keys the line's holon admitted in the reader's own copy, never a key the
    mail carries. A key the holon never admitted is unverified; a failing signature is bad."""
    if not isinstance(line, dict) or not record.check_id(line):
        return 'bad', 'Could not be verified. Not acted on.'
    d = _holon_dirs(hq_dir).get(_s(line.get('holon')))
    if not d:
        return 'unverified', 'This house does not hold the holon the line names, so its key cannot be checked.'
    keys = _admitted(d, home=(d == hq_dir))
    actor = line.get('actor')
    if _s(line.get('sig')):
        if not isinstance(actor, str) or actor not in keys:
            return 'unverified', 'Unverified. Signed by a key the holon never admitted. Shown, and never acted on.'
        tmp, allowed = _allowed_signers({actor: keys[actor]})
        try:
            v = record.verify(line, allowed)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if v.get('sig') == 'valid':
            return 'verified', 'Verified against the key the holon admitted.'
        if v.get('sig') == 'unchecked':
            return 'unverified', 'The signature could not be checked on this machine.'
        return 'bad', 'Could not be verified. Not acted on.'
    if isinstance(attestation, dict):
        a = record.verify_attestation(attestation, [line], holon_dir=d)
        if a.get('sig') == 'valid' and a.get('ids_ok'):
            return 'verified', 'Names hidden; vouched for by %s.' % _s(attestation.get('by'))
        return 'unverified', 'Names hidden; the attestation did not check against the holon\'s record.'
    return 'unverified', 'Unsigned. Shown, and never acted on.'


def suspects(text):
    """Sentences in a mail that ask for an act, quoted, each with what the agent says back."""
    out = []
    for sent in re.split(r'(?<=[.!?])\s+|\n+', _s(text)):
        s = sent.strip()
        if s and SUSPECT.search(s):
            q = s[:300]
            out.append({'quote': q, 'said': 'This mail asks for an act: "%s". I have not done it.' % q})
    return out[:20]


def _line_texts(line):
    b = _body(line)
    out = []
    for v in b.values():
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            out.extend(x for x in v.values() if isinstance(x, str))
    return '\n'.join(out)


def propose_from_prose(prose, hq_dir=None, message_id='', ts=None):
    """A proposed `say` line from prose: reason untrusted, unsigned, held as a proposal only.

    The person's agent turns it into a real line at the person's yes; until then it changes
    nothing. The mail's Message-ID is kept as its source; the From line is not (it proves nothing)."""
    text = _s(prose).strip()[:MAX_PROSE]
    if not text:
        return None
    person = _person(hq_dir) if hq_dir else ''
    actor = _home_agent(hq_dir) if hq_dir else ''
    body = {'text': text, 'source_mail': _s(message_id)[:500]}
    line = record.make_line(actor or 'agent:unknown', person or 'person:unknown', _home_id(hq_dir), 'say', body,
                            reason='untrusted', ts=ts)
    return line


def read_mail(message, hq_dir=None, now=None):
    """Everything a mail carries, as data: {lines: [{line, verified, said}], prose, proposal,
    suspect, header_disagreements, message_id, subject, from_header, kind: line · prose · bad}."""
    msg = parse(message)
    out = {'lines': [], 'prose': None, 'proposal': None, 'suspect': [], 'header_disagreements': [],
           'message_id': '', 'subject': '', 'from_header': '', 'kind': 'bad',
           'said': 'One mail could not be read. The rest is shown.'}
    if msg is None:
        return out
    with contextlib.suppress(Exception):
        out['message_id'] = _s(str(msg.get('Message-ID') or '')).strip()[:500]
        out['subject'] = _s(str(msg.get('Subject') or '')).strip()[:300]
        out['from_header'] = _s(str(msg.get('From') or '')).strip()[:300]
    lines, atts, prose = _scan(msg)
    out['prose'] = prose or None
    att = atts[0] if atts else None
    for l in lines:
        v, said = verify_line(l, hq_dir, att)
        out['lines'].append({'line': l if v != 'bad' else None, 'id': _s(l.get('id')), 'verified': v,
                             'said': said})
    hl = _s(str(msg.get(HDR_LINE) or '')).strip()
    hh = _s(str(msg.get(HDR_HOLON) or '')).strip()
    if lines:
        first = lines[0]
        if hl and hl != _s(first.get('id')):
            out['header_disagreements'].append('The mail\'s header names line %s; the line it carries is %s. '
                                               'The line is read.' % (hl[:16], _s(first.get('id'))[:16]))
        if hh and hh != _s(first.get('holon')):
            out['header_disagreements'].append('The mail\'s header names another holon than the line does. '
                                               'The line is read.')
        out['kind'] = 'line' if any(x['verified'] != 'bad' for x in out['lines']) else 'bad'
        out['said'] = out['lines'][0]['said']
        texts = '\n'.join(_line_texts(x['line']) for x in out['lines'] if x['line'])
        out['suspect'] = suspects(texts + '\n' + (prose or ''))
    elif prose:
        out['kind'] = 'prose'
        out['proposal'] = propose_from_prose(prose, hq_dir, out['message_id'], ts=now)
        out['suspect'] = suspects(prose)
        out['said'] = 'Prose. Your agent offers a proposed line beside it; it changes nothing until you say yes.'
    if hl and not lines:
        out['header_disagreements'].append('The mail\'s header names a line, and no line is carried. It is prose.')
    return out


def from_mail(message, hq_dir=None, now=None):
    """(line | None, prose | None, verified) for one mail.

    A carried line comes back with its verification: verified · unverified · bad (a bad line comes
    back as None). Prose with no line comes back as a proposed `say` line with reason untrusted,
    and verified 'unverified'. An instruction in a mail is never acted on: this returns data."""
    r = read_mail(message, hq_dir, now)
    if r['lines']:
        x = r['lines'][0]
        return x['line'], r['prose'], x['verified']
    if r['proposal'] is not None:
        return r['proposal'], r['prose'], 'unverified'
    return None, r['prose'], 'bad'


# ---------------------------------------------------------------- the carried store

def _store(hq_dir):
    d = os.path.join(hq_dir, CARRIED)
    if not os.path.isdir(d):
        os.makedirs(d, mode=0o700, exist_ok=True)
    gi = os.path.join(d, '.gitignore')
    if not os.path.exists(gi):
        _write_private(gi, '*\n')
    return d


def _record_ids(hq_dir):
    return {l['id'] for l in record.read_all(hq_dir)['lines']}


def _arrival(store, line_id, message_id, via):
    path = os.path.join(store, 'arrivals.jsonl')
    row = {'id': line_id, 'via': via, 'message_id': message_id, 'at': _now()}
    have = set()
    try:
        with open(path, encoding='utf-8') as f:
            for raw in f:
                with contextlib.suppress(ValueError):
                    o = json.loads(raw)
                    have.add((o.get('id'), o.get('message_id')))
    except OSError:
        pass
    if (line_id, message_id) in have:
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def home_fold(hq_dir, now=None):
    """(items, schedule report, lines) for the receiving home: its own fold, so a carried push is weighed
    against the home's own cards by default. Read through engine.py (read_hq under the reader's
    signature cache, then run_schedule); when engine.py is not at hand, a plain fold under
    record.signature_cache, with no schedule. Never raises: on any fault, ({}, None, [])."""
    try:
        import engine as _engine
        folded, holons, lines, _, cal = _engine.read_hq(hq_dir)
        try:
            t = record._parse_ts(now) if isinstance(now, str) else now
            rep, _ = _engine.run_schedule(folded, cal, t or dt.datetime.now().astimezone(), holons, lines)
        except Exception:
            rep = None
        folded = {k: v for k, v in folded.items() if not k.startswith('_')}
        return folded, rep, lines
    except (Exception, SystemExit):
        pass
    try:
        r = record.read_all(hq_dir)
        cache = getattr(record, 'signature_cache', None)
        if cache is not None:
            with cache(hq_dir):
                f = record.fold(r['lines'], None, r['keepers'])
        else:
            f = record.fold(r['lines'], None, r['keepers'])
        return f, None, r['lines']
    except Exception:
        return {}, None, []


def _asker_words(line):
    """The asker's own words on a carried line: `body.text`, never a subject line; None when hidden or absent."""
    t = _body(line).get('text')
    return t if isinstance(t, str) and t.strip() else None


def carry(message, hq_dir, via='mail', now=None, items=None, schedule=None, lines=None):
    """Carry one mail into <hq>/.carried/: "carried, not yet in the record".

    Returns {kind: line · prose · bad, stored: [paths], duplicates, in_record, verified, suspect,
    said}. A line already in the record, or already carried, is not stored again; its arrival by
    this carrier is noted. Raises ValueError when the home folder is missing."""
    if not hq_dir or not os.path.isdir(hq_dir):
        raise ValueError('There is no home folder at %r.' % hq_dir)
    store = _store(hq_dir)
    r = read_mail(message, hq_dir, now)
    out = {'kind': r['kind'], 'stored': [], 'duplicates': 0, 'in_record': 0, 'verified': [],
           'suspect': r['suspect'], 'said': r['said'], 'header_disagreements': r['header_disagreements']}
    held = _record_ids(hq_dir)
    received = now or _now()
    for x in r['lines']:
        lid = x['id']
        out['verified'].append(x['verified'])
        if x['line'] is None or not HEX64.match(lid):
            path = os.path.join(store, 'bad', _sha(r['message_id'] + lid)[:32] + '.json')
            if not os.path.exists(path):
                _write_private(path, json.dumps({'v': 1, 'kind': 'bad', 'message_id': r['message_id'],
                                                 'subject': r['subject'], 'said': x['said'],
                                                 'received_at': received, 'read': False},
                                                ensure_ascii=False, indent=1))
                out['stored'].append(path)
            continue
        _arrival(store, lid, r['message_id'], via)
        if lid in held:
            out['in_record'] += 1
            continue
        path = os.path.join(store, 'lines', lid + '.json')
        if os.path.exists(path):
            out['duplicates'] += 1
            continue
        entry = {'v': 1, 'kind': 'line', 'id': lid, 'holon': _s(x['line'].get('holon')), 'line': x['line'],
                 'verified': x['verified'], 'said': x['said'], 'carried_by': [via], 'message_id': r['message_id'],
                 'subject': r['subject'], 'from_header': r['from_header'], 'received_at': received,
                 'question': _asker_words(x['line']),
                 'read': False, 'suspect': r['suspect'], 'header_disagreements': r['header_disagreements'],
                 'state': 'carried, not yet in the record'}
        if _body(x['line']).get('push') is not None:
            if items is None:
                items, schedule, lines = home_fold(hq_dir, now)
            entry['push_recomputed'] = recompute_push(x['line'], items, schedule, lines=lines, now=now)
        _write_private(path, json.dumps(entry, ensure_ascii=False, indent=1))
        out['stored'].append(path)
    if r['kind'] == 'prose':
        key = _sha(r['message_id'] or (r['prose'] or ''))[:32]
        path = os.path.join(store, 'prose', key + '.json')
        if os.path.exists(path):
            out['duplicates'] += 1
        else:
            _write_private(path, json.dumps({'v': 1, 'kind': 'prose', 'id': key, 'message_id': r['message_id'],
                                             'subject': r['subject'], 'from_header': r['from_header'],
                                             'prose': (r['prose'] or '')[:MAX_PROSE],
                                             'proposed_line': r['proposal'], 'suspect': r['suspect'],
                                             'question': _asker_words(r['proposal']),
                                             'received_at': received, 'read': False,
                                             'state': 'prose; a proposed line waits on your yes'},
                                            ensure_ascii=False, indent=1))
            out['stored'].append(path)
    elif r['kind'] == 'bad' and not r['lines']:
        path = os.path.join(store, 'bad', _sha(r['message_id'] or received)[:32] + '.json')
        _write_private(path, json.dumps({'v': 1, 'kind': 'bad', 'message_id': r['message_id'],
                                         'said': r['said'], 'received_at': received, 'read': False},
                                        ensure_ascii=False, indent=1))
        out['stored'].append(path)
    return out


def carried(hq_dir):
    """Every entry in the carried store, each with `in_record` and `withdrawn` worked out."""
    if not hq_dir:
        return []
    d = os.path.join(hq_dir, CARRIED)
    if not os.path.isdir(d):
        return []
    held = _record_ids(hq_dir)
    out = []
    for sub in ('lines', 'prose', 'bad'):
        sd = os.path.join(d, sub)
        if not os.path.isdir(sd) or os.path.islink(sd):
            continue
        for name in sorted(os.listdir(sd)):
            p = os.path.join(sd, name)
            if not name.endswith('.json') or os.path.islink(p):
                continue
            e = _read_json(p)
            if e is None:
                continue
            e['_path'] = p
            if e.get('kind') == 'line':
                e['in_record'] = e.get('id') in held
            out.append(e)
    lines = [e['line'] for e in out if e.get('kind') == 'line' and isinstance(e.get('line'), dict)]
    lines += record.read_all(hq_dir)['lines']
    withdrawn = set()
    actor_of = {l.get('id'): l.get('actor') for l in lines}
    for l in lines:
        if l.get('type') == 'supersede' and not [k for k in _body(l) if k not in record.SALT_KEYS]:
            for t in _links(l, 'supersedes'):
                if actor_of.get(t) == l.get('actor'):
                    withdrawn.add(t)
    for e in out:
        if e.get('kind') == 'line':
            e['withdrawn'] = e.get('id') in withdrawn
    return out


def prune(hq_dir):
    """Drop carried copies the record now holds (the forge pull brought them). Returns how many."""
    n = 0
    for e in carried(hq_dir):
        if e.get('kind') == 'line' and e.get('in_record'):
            with contextlib.suppress(OSError):
                os.unlink(e['_path'])
                n += 1
    return n


def lines_for_fold(hq_dir):
    """Carried lines the record does not hold, tagged as carried, for the fold to read beside the record.

    The fold decides their trust as it does any line's; a line the record holds is never added twice."""
    out = []
    for e in carried(hq_dir):
        if e.get('kind') != 'line' or e.get('in_record') or not isinstance(e.get('line'), dict):
            continue
        l = dict(e['line'])
        l['_held_in'] = _s(l.get('holon'))
        l['_file'] = 'carried/' + _s(l.get('id'))
        l['_carried'] = True
        out.append(l)
    return out


def fold_with_carried(hq_dir, types=None, now=None, clock=None):
    """The fold of the record and the carried lines it does not yet hold; each line folds once."""
    r = record.read_all(hq_dir)
    extra = lines_for_fold(hq_dir)
    f = record.fold(r['lines'] + extra, types, r['keepers'], now=now, clock=clock)
    f['carried_ids'] = [l['id'] for l in extra]
    return f


def arrived_by(hq_dir):
    """{line id: [carriers]} from the arrival notes: the second carrier only adds that it also came that way."""
    out = {}
    path = os.path.join(hq_dir or '', CARRIED, 'arrivals.jsonl')
    try:
        with open(path, encoding='utf-8') as f:
            for raw in f:
                with contextlib.suppress(ValueError):
                    o = json.loads(raw)
                    if isinstance(o, dict) and isinstance(o.get('id'), str):
                        v = out.setdefault(o['id'], [])
                        if o.get('via') not in v:
                            v.append(o.get('via'))
    except OSError:
        pass
    return out


def mark_read(hq_dir, entry_id):
    """Mark one carried entry read, on this machine only. Nothing is written to the record."""
    if not isinstance(entry_id, str) or not re.match(r'^[0-9a-f]{32,64}$', entry_id):
        return False
    for e in carried(hq_dir):
        if e.get('id') == entry_id:
            p = e.pop('_path')
            e.pop('in_record', None)
            e.pop('withdrawn', None)
            e['read'] = True
            _write_private(p, json.dumps(e, ensure_ascii=False, indent=1))
            return True
    return False


def unread_from_other_houses(hq_dir):
    """The badge's count, from the carried store: unread lines and prose from beyond the home.

    A line by the person or the person's own agents never counts; a withdrawn line never counts."""
    home = _home_actors(hq_dir)
    n = 0
    for e in carried(hq_dir):
        if e.get('read') or e.get('kind') == 'bad':
            continue
        if e.get('kind') == 'line':
            if e.get('withdrawn'):
                continue
            a = (e.get('line') or {}).get('actor')
            if isinstance(a, str) and a in home:
                continue
        n += 1
    return n


def badge(hq_dir):
    """The `badges` state field for serve.py: {threads_and_mail, from_houses, as_of}."""
    n = unread_from_other_houses(hq_dir)
    return {'threads_and_mail': n, 'from_houses': n, 'as_of': _now(), 'source': 'the carried store'}


# ---------------------------------------------------------------- the Push Protocol on a carried line

def recompute_push(line, items, schedule, lines=None, budget=None, now=None):
    """The receiver's own blocks, critical and the sender's calibration, kept beside the sender's values.

    Returns {sent, receiver, differs, said, retracted, computed}. When push.py is not at hand,
    `receiver` is None and the stake is said as not computed yet, never guessed."""
    b = _body(line)
    sent = b.get('push') if isinstance(b.get('push'), dict) else None
    out = {'sent': sent, 'receiver': None, 'differs': [], 'said': [], 'retracted': False, 'computed': False}
    if sent is None:
        out['said'].append('No stake given.')
        return out
    if _push is None:
        out['said'].append('Not computed yet.')
        return out
    try:
        w = _push.weigh(sent, budget=budget, items=items or {}, schedule_report=schedule, line=line, now=now)
        cal = None
        if lines:
            row = (_push.calibration(lines, items or {}, now=now) or {}).get(line.get('actor'))
            cal = row
        out['receiver'] = {'blocks': w.get('blocks'), 'critical': w.get('critical'), 'by': w.get('by'),
                           'why_by': w.get('why_by'), 'cost_if_late': w.get('cost_if_late'),
                           'weight': w.get('weight'), 'calibration': cal}
        out['retracted'] = bool(w.get('retracted'))
        out['computed'] = True
    except Exception:
        out['said'].append('Not computed yet.')
        return out
    rec = out['receiver']
    sb = sent.get('blocks') if isinstance(sent.get('blocks'), list) else None
    if sb is not None and rec['blocks'] is not None and len(sb) != len(rec['blocks']):
        out['differs'].append('blocks')
        out['said'].append('They see %d card%s waiting. Your record shows %d.' % (
            len(sb), '' if len(sb) == 1 else 's', len(rec['blocks'])))
    if 'critical' in sent and bool(sent.get('critical')) != bool(rec['critical']):
        out['differs'].append('critical')
        out['said'].append('They see it on the critical chain. Your record does not.' if sent.get('critical')
                           else 'Your record puts it on the critical chain. They do not.')
    if out['retracted']:
        alt = sent.get('alternatives')
        out['said'].append('This question expired. The sender\'s alternative: %s.' % _shown(alt).rstrip('.')
                           if alt else 'This question expired.')
    return out


# ---------------------------------------------------------------- the account

class Account(dict):
    """A mail account. Its repr and str never show the user or the password."""

    def __repr__(self):
        return 'Account(%s)' % _s(self.get('name')) if self.get('name') else 'Account()'

    __str__ = __repr__

    def secret(self):
        if self.get('password_file'):
            p = os.path.expanduser(_s(self['password_file']))
            _check_private(p)
            with open(p, encoding='utf-8') as f:
                return f.read().strip()
        return _s(self.get('password'))


def _check_private(path):
    st = os.stat(path)
    if st.st_mode & 0o077:
        raise Refused('The mail settings must be readable by you alone (mode 0600). Nothing was read.')
    if hasattr(os, 'getuid') and st.st_uid != os.getuid():
        raise Refused('The mail settings belong to another user. Nothing was read.')
    if not stat.S_ISREG(st.st_mode):
        raise Refused('The mail settings are not a plain file. Nothing was read.')


def load_account(name=None, path=None, holon_dir=None):
    """The account from ~/.config/lionsberg/mail.json (or LIONSBERG_MAIL_CONFIG), mode 0600.

    Never from a holon: a settings file inside the holon folder is refused. Shape:
    {"default": NAME, "accounts": {NAME: {"imap_host", "imap_port", "imap_tls": "ssl|starttls",
    "smtp_host", "smtp_port", "smtp_tls": "ssl|starttls", "user", "password" or "password_file",
    "address", "mailbox", "domains": [...], "addresses": {address: actor}, "holon": id}}}"""
    p = os.path.expanduser(path or os.environ.get('LIONSBERG_MAIL_CONFIG') or CONFIG)
    if holon_dir:
        rp, rh = os.path.realpath(p), os.path.realpath(holon_dir)
        if rp == rh or rp.startswith(rh + os.sep):
            raise Refused('Mail settings are never read from a holon. Keep them in %s.' % CONFIG)
    if not os.path.isfile(p):
        raise Refused('There are no mail settings at %s.' % CONFIG)
    _check_private(p)
    d = _read_json(p)
    if d is None:
        raise Refused('The mail settings could not be read as JSON.')
    accts = d.get('accounts') if isinstance(d.get('accounts'), dict) else {}
    nm = name or _s(d.get('default')) or (sorted(accts)[0] if len(accts) == 1 else '')
    a = accts.get(nm) if nm else None
    if not isinstance(a, dict):
        raise Refused('There is no mail account by that name.')
    acc = Account(a)
    acc['name'] = nm
    return acc


def _private_host(host):
    """True when every address the host resolves to sits on the private network."""
    host = _s(host).strip()
    if not host:
        return False
    try:
        addrs = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addrs = [ipaddress.ip_address(i[4][0].split('%', 1)[0])
                     for i in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)]
        except (OSError, ValueError):
            return False
    shared = ipaddress.ip_network('100.64.0.0/10')
    return bool(addrs) and all(a.is_private or a.is_loopback or (a.version == 4 and a in shared) for a in addrs)


def _scrub(text, account):
    """Text with the account's user and password taken out."""
    t = _s(text)
    if isinstance(account, Account):
        for s in (account.get('password'), account.get('user')):
            if isinstance(s, str) and s:
                t = t.replace(s, '[hidden]')
        with contextlib.suppress(Exception):
            sec = account.secret()
            if sec:
                t = t.replace(sec, '[hidden]')
    return t


# ---------------------------------------------------------------- the mailbox

def _imap(account):
    host, ctx = _s(account.get('imap_host')), ssl.create_default_context()
    tls = _s(account.get('imap_tls')) or 'ssl'
    port = account.get('imap_port') if isinstance(account.get('imap_port'), int) else (993 if tls == 'ssl' else 143)
    if IMAP_FACTORY is not None:
        return IMAP_FACTORY(host, port, ssl_context=ctx, tls=tls)
    if tls == 'ssl':
        return imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=TIMEOUT)
    if tls == 'starttls':
        c = imaplib.IMAP4(host, port, timeout=TIMEOUT)
        c.starttls(ssl_context=ctx)
        return c
    raise Refused('Mail is read only over TLS.')


def fetch(account, hq_dir, now=None, items=None, schedule=None):
    """Read new mail over IMAP with TLS, carry each into <hq>/.carried/, mark it seen once stored.

    Fetch never sends: it holds no way to send, and nothing it reads can make it. Returns
    {read, carried, prose, duplicates, in_record, bad, suspect, not_stored, said, badge}. On a
    mailbox that cannot be reached it says so, without any credential."""
    if not isinstance(account, Account):
        raise Refused('There is no mail account.')
    if not hq_dir or not os.path.isdir(hq_dir):
        raise Refused('There is no home folder there.')
    if not _private_host(account.get('imap_host')):
        raise Refused('The mailbox is not on the private network, so it is not read.')
    out = {'read': 0, 'carried': 0, 'prose': 0, 'duplicates': 0, 'in_record': 0, 'bad': 0, 'suspect': [],
           'not_stored': 0, 'said': '', 'badge': None}
    lines = None
    if items is None:                    # the home's own fold, once per fetch, so every push is recomputed
        items, schedule, lines = home_fold(hq_dir, now)
    conn = None
    try:
        conn = _imap(account)
        conn.login(_s(account.get('user')), account.secret())
        typ, _ = conn.select(_s(account.get('mailbox')) or 'INBOX')
        if typ != 'OK':
            raise Refused('The mailbox could not be opened.')
        typ, data = conn.uid('SEARCH', None, 'UNSEEN')
        uids = (data[0] or b'').split() if typ == 'OK' and data else []
        for uid in uids:
            typ, msg_data = conn.uid('FETCH', uid, '(BODY.PEEK[])')
            raw = None
            for part in msg_data or []:
                if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], (bytes, bytearray)):
                    raw = bytes(part[1])
            if typ != 'OK' or raw is None:
                out['not_stored'] += 1
                continue
            out['read'] += 1
            try:
                c = carry(raw, hq_dir, 'mail', now, items, schedule, lines)
            except Exception:
                out['not_stored'] += 1            # not stored, so not marked seen: read again next beat
                continue
            out['duplicates'] += c['duplicates']
            out['in_record'] += c['in_record']
            out['suspect'].extend(c['suspect'])
            if c['kind'] == 'prose':
                out['prose'] += 1
            elif c['kind'] == 'bad':
                out['bad'] += 1
            else:
                out['carried'] += len([p for p in c['stored'] if os.sep + 'lines' + os.sep in p])
            conn.uid('STORE', uid, '+FLAGS', '(\\Seen)')
        out['said'] = 'Mail · read %s · %d waiting' % (now or _now(), unread_from_other_houses(hq_dir))
    except Refused:
        raise
    except Exception as e:
        raise Refused('The mailbox cannot be reached (%s). The forge is still pulled.' % type(e).__name__)
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.logout()
    out['badge'] = badge(hq_dir)
    return out


def _smtp(account):
    host, ctx = _s(account.get('smtp_host')), ssl.create_default_context()
    tls = _s(account.get('smtp_tls')) or 'ssl'
    port = account.get('smtp_port') if isinstance(account.get('smtp_port'), int) else (465 if tls == 'ssl' else 587)
    if SMTP_FACTORY is not None:
        return SMTP_FACTORY(host, port, context=ctx, tls=tls)
    if tls == 'ssl':
        return smtplib.SMTP_SSL(host, port, context=ctx, timeout=TIMEOUT)
    if tls == 'starttls':
        c = smtplib.SMTP(host, port, timeout=TIMEOUT)
        c.ehlo()
        c.starttls(context=ctx)          # raises when the host offers no TLS: nothing is sent in the clear
        c.ehlo()
        return c
    raise Refused('Mail is sent only over TLS.')


def _domain_ok(addr, account):
    _, a = email.utils.parseaddr(_s(addr))
    if '@' not in a:
        return False
    dom = a.rsplit('@', 1)[1].lower()
    doms = [d.lower() for d in account.get('domains') or [] if isinstance(d, str)]
    if not doms and '@' in _s(account.get('address')):
        doms = [_s(account['address']).rsplit('@', 1)[1].lower()]
    return dom in doms


def send(account, message, on_the_persons_send=False):
    """Send one message over SMTP with TLS, only at the person's own act.

    `on_the_persons_send` must be True: the caller is the person's Send. Every recipient must sit in
    the private network's mail domains (the account's `domains`); a mail beyond them is an outward
    act that goes through the publish sheet, never through here."""
    if on_the_persons_send is not True:
        raise Refused('Nothing is sent without your own Send.')
    if not isinstance(account, Account):
        raise Refused('There is no mail account.')
    if not isinstance(message, email.message.Message):
        raise Refused('There is no message to send.')
    rcpts = [a for _, a in email.utils.getaddresses([str(message.get('To') or ''), str(message.get('Cc') or '')])
             if a]
    if not rcpts or not all(_domain_ok(a, account) for a in rcpts):
        raise Refused('A recipient is outside the private network. A mail beyond it goes through the publish sheet.')
    if not _private_host(account.get('smtp_host')):
        raise Refused('The mail host is not on the private network, so nothing was sent.')
    conn = None
    try:
        conn = _smtp(account)
        conn.login(_s(account.get('user')), account.secret())
        conn.send_message(message)
    except Refused:
        raise
    except Exception as e:
        raise Refused('The mail could not be sent (%s). Nothing else was tried.' % type(e).__name__)
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.quit()
    return {'sent': True, 'to': rcpts, 'line': str(message.get(HDR_LINE) or ''),
            'said': 'Sent · carried by mail · not yet answered'}


def _card_title(f, line):
    ids = set(_links(line, 'anchored_to'))
    b = _body(line)
    if isinstance(b.get('card'), str):
        ids.add(b['card'])
    for c in f.get('cards') or []:
        if isinstance(c, dict) and c.get('id') in ids:
            return _s(c.get('title')) or None
    return None


BOOK_SAID = 'address from your own book, not from the holon'


def reach_of(hq_dir, holon_id, account=None):
    """{actor: [mail addresses]} from the holon's own record: `body.reach` (SCHEMA, Reach, not identity).

    For each actor, the newest join or affirm line about them (a join's `who`, an affirm's `agent`,
    or the inception's keeper) that the fold trusts, that is signed, and that carries `reach` with a
    `mail:` entry; only addresses inside the private network's domains are kept when an account is
    given. A reach on an unsigned, unverified or refused line is never used."""
    d = _holon_dirs(hq_dir).get(_s(holon_id))
    if not d:
        return {}
    r = record.read(d)
    if d == hq_dir:
        for l in r['lines']:
            if l['_file'].startswith('record/'):
                l['_home_record'] = True
    keepers = {r['holon']: r['keeper']} if r['holon'] and r['keeper'] else {}
    trust = record.fold(r['lines'], None, keepers).get('trust') or {}
    best = {}
    for l in r['lines']:
        if l.get('type') not in ('join', 'affirm') or not _s(l.get('sig')):
            continue
        if trust.get(l['id']) not in ('signed', 'vouched'):
            continue
        b = _body(l)
        reach = b.get('reach') if isinstance(b.get('reach'), list) else []
        addrs = [x[5:].strip() for x in reach if isinstance(x, str) and x.startswith('mail:') and '@' in x]
        if account is not None:
            addrs = [a for a in addrs if _domain_ok(a, account)]
        if not addrs:
            continue
        who = _s(b.get('agent')) if l.get('type') == 'affirm' else (_s(b.get('who')) or _s(l.get('actor')))
        if not who:
            continue
        if who not in best or _s(l.get('ts')) >= _s(best[who][0]):
            best[who] = (_s(l.get('ts')), addrs)
    return {a: v[1] for a, v in best.items()}


def resolve_recipient(hq_dir, holon_id, to, account):
    """(actor, address, source) for a recipient named by actor id or by address.

    The holon's own reach is read first (source 'holon'); the person's own address book in the
    account file (`addresses`: address -> actor) is the fallback (source 'book'). The actor must
    be one the line's holon admitted. Raises Refused otherwise."""
    to = _s(to).strip()
    d = _holon_dirs(hq_dir).get(_s(holon_id))
    keys = _admitted(d, home=(d == hq_dir)) if d else {}
    reach = reach_of(hq_dir, holon_id, account)
    book = account.get('addresses') if isinstance(account.get('addresses'), dict) else {}
    actor = addr = source = None
    if to.startswith(('person:', 'agent:')):
        if reach.get(to):
            actor, addr, source = to, reach[to][0], 'holon'
        else:
            mine = sorted(a for a, who in book.items() if who == to and isinstance(a, str))
            if mine:
                actor, addr, source = to, mine[0], 'book'
    else:
        _, a = email.utils.parseaddr(to)
        held = [who for who, addrs in reach.items() if a in addrs]
        if a and held:
            actor, addr, source = held[0], a, 'holon'
        elif a and isinstance(book.get(a), str):
            actor, addr, source = book[a], a, 'book'
    if not actor or actor not in keys:
        raise Refused('That recipient is not in the line\'s audience: a line is mailed only to actors its holon '
                      'admitted, at an address their own reach gives or your own book holds.')
    return actor, addr, source


def send_line(hq_dir, line_id, to_addr, account, on_the_persons_send=False, key_dir=None, dry_run=False):
    """The person's Send of a line already in the record, by mail.

    Refused unless: the person's act is named; the line is in the record (record/, never a carried
    or published copy); the fold trusts it and it is signed; it is the person's own line, or their
    agent's written at their word (reason human); it is not a proposal; the recipient resolves
    (resolve_recipient) to an actor the line's holon admitted. Under names-hidden the
    account must be the holon's own mailbox. Returns send()'s result, or the message on dry_run."""
    if on_the_persons_send is not True:
        raise Refused('Nothing is sent without your own Send.')
    if not isinstance(line_id, str) or not HEX64.match(line_id):
        raise Refused('That is not a line id.')
    if not hq_dir or not os.path.isdir(hq_dir):
        raise Refused('There is no home folder there.')
    r = record.read_all(hq_dir)
    line = next((l for l in r['lines'] if l['id'] == line_id), None)
    if line is None or not _s(line.get('_file')).startswith('record/'):
        raise Refused('That line is not in the record. Only a line already recorded is sent.')
    person = _person(hq_dir)
    f = record.fold(r['lines'], None, r['keepers'])
    if f['trust'].get(line_id) not in ('signed', 'vouched') or not _s(line.get('sig')):
        raise Refused('That line is not signed and trusted, so it does not travel.')
    if line.get('reason') == 'untrusted' or line_id in {p.get('id') for p in f.get('proposals') or []
                                                       if isinstance(p, dict)}:
        raise Refused('That line is a proposal. It travels once you say yes to it.')
    actor = _s(line.get('actor'))
    if not (actor == person or (actor.startswith('agent:') and line.get('for') == person
                                and line.get('reason') == 'human')):
        raise Refused('That line is not yours, nor written at your word.')
    if not isinstance(account, Account):
        raise Refused('There is no mail account.')
    hid = _s(line.get('holon'))
    d = _holon_dirs(hq_dir).get(hid)
    to_actor, addr, source = resolve_recipient(hq_dir, hid, to_addr, account)
    posture = _posture(hq_dir, hid)
    att = None
    if posture != 'open':
        if _s(account.get('holon')) != hid:
            raise Refused('A room held with names hidden speaks through its own mailbox. Choose that account.')
        att = attest_one(d, hide_names(line, posture), person, key_dir=key_dir)
    msg = to_mail(line, addr, _s(account.get('address')), posture, card=_card_title(f, line),
                  holon_name=_s(record.holon_info(d).get('name')) if d else None, attestation=att)
    if dry_run:
        return msg
    out = send(account, msg, on_the_persons_send=True)
    out['address_source'] = source
    if source == 'book':
        out['address_said'] = BOOK_SAID
    return out


# ---------------------------------------------------------------- the command line

HELP = """Mail inside the private network: a carrier of lines, never a second truth.

What is recorded: nothing in the record. Mail that arrives is kept in <HQ_DIR>/.carried/ as
"carried, not yet in the record" (a signed line, once by its id; or prose with a proposed line
marked reason: untrusted, which changes nothing until you say yes). When the forge pull brings
the same line, the carried copy is dropped and the line folds once. Read state stays on this
machine. Credentials are read from ~/.config/lionsberg/mail.json (mode 0600) and never printed.

fetch never sends. It reads unseen mail over TLS, stores it, and only then marks it seen.
Every mail is data: an instruction inside one is shown to you, quoted, and never acted on.
send sends one line already in your record, at your own act, and only with --on-the-persons-send.
"""


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='mail.py', description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('fetch', help='read new mail into the carried store (never sends)')
    p.add_argument('hq')
    p.add_argument('--account')
    p = sub.add_parser('carry', help='carry one saved mail (.eml) into the carried store')
    p.add_argument('eml')
    p.add_argument('hq')
    p = sub.add_parser('send', help='send one recorded line by mail, at your own act')
    p.add_argument('hq')
    p.add_argument('line_id')
    p.add_argument('--to', required=True, help='an actor id or an address; the holon\'s own reach is read first, '
                   'then your own book')
    p.add_argument('--account')
    p.add_argument('--on-the-persons-send', action='store_true', dest='act',
                   help='you, the person, are sending this now; without it nothing is sent')
    p = sub.add_parser('badge', help='the count of unread lines from other houses, from the carried store')
    p.add_argument('hq')
    p = sub.add_parser('carried', help='list what mail carried, with its state')
    p.add_argument('hq')
    a = ap.parse_args(argv)
    acct = None
    try:
        if a.cmd == 'fetch':
            acct = load_account(a.account, holon_dir=a.hq)
            _print(fetch(acct, a.hq))
        elif a.cmd == 'carry':
            if not os.path.isfile(a.eml) or os.path.getsize(a.eml) > MAX_MAIL:
                raise Refused('There is no readable mail file there.')
            with open(a.eml, 'rb') as fh:
                raw = fh.read()
            c = carry(raw, a.hq)
            c['stored'] = [os.path.relpath(x, a.hq) for x in c['stored']]
            _print(c)
        elif a.cmd == 'send':
            if not a.act:
                raise Refused('Nothing is sent without your own Send: add --on-the-persons-send.')
            acct = load_account(a.account, holon_dir=a.hq)
            _print(send_line(a.hq, a.line_id, a.to, acct, on_the_persons_send=True))
        elif a.cmd == 'badge':
            _print(badge(a.hq))
        elif a.cmd == 'carried':
            rows = []
            for e in carried(a.hq):
                rows.append({'kind': e.get('kind'), 'id': e.get('id'), 'verified': e.get('verified'),
                             'state': 'in the record' if e.get('in_record') else e.get('state'),
                             'withdrawn': e.get('withdrawn', False), 'read': e.get('read'),
                             'question': e.get('question'), 'subject': e.get('subject'),
                             'suspect': len(e.get('suspect') or [])})
            _print(rows)
        else:
            ap.print_help()
            return 2
    except (Refused, ValueError, OSError) as e:
        msg = e.args[0] if isinstance(e, (Refused, ValueError)) and e.args else type(e).__name__
        print(_scrub(str(msg), acct), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
