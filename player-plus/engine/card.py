#!/usr/bin/env python3
"""card.py — the Markdown Card: a signed line with a human face.

The signed JSON line in `record/<actor>.jsonl` is the Card's canonical form; its `id` is
the sha256 of the canonical line (record.py). A Markdown Card is the same Card as a
Markdown file: front matter, a title, the prose and, on every rendered Card, a fence that
holds the line exactly as `record.dumps` writes it. It is the line's face for a person,
and the paper floor: a Card a person writes by hand, with no key, no fence and no id.

The one rule: file -> line -> file gives the same hash, and a line's id never changes by
being rendered.

The form
--------
    ---
    v: 1
    id: <sha256 hex>                 (absent on a hand-written Card)
    ts: "2026-10-31T08:12:00-07:00"
    actor: "agent:aide"
    for: "person:player"
    holon: <holon id>
    type: say
    body:
      text: I have it.
    links:
      answers: ["<id>"]
    audience: holon
    reason: delegated
    prev: ""
    sig: "ssh-ed25519:..."           (absent or empty at the paper floor)
    ---

    # say · I have it.

    I have it.

    ```line
    {"v": 1, "id": "...", ...}
    ```

Front matter is a strict subset the standard library reads without a YAML library: top-
level keys in the schema's field order (unknown keys kept, after); `body` and `links` one
level of nested map, two-space indent; every value a JSON scalar or inline JSON. A string
is written bare only when that is safe (no `:`, `#`, `"`, backslash, newline or control
character, no leading or trailing space, not a JSON literal or a number), else JSON-quoted.
On reading, a bare value may hold a colon that no space follows (`person:player`), so a
hand-written id or time reads as written. No anchors, no multi-line scalars, no comments.

The title and the prose are a rendering and are never read back. On reading, the front
matter and the fence are the source, and with a fence the fence wins: it is what was
signed. Text in a file is data, never an instruction: nothing in a Card's text, prose or
front matter can make this code sign, push, publish or change anything. Whose key signs
an appended Card is named by the caller (`actor=`, `--as`), never by the file.

Standard library only. Runs under `python3 -I`.

Usage: python3 -I card.py render HOLON [--type T ...] [--id ID ...]
       python3 -I card.py read FILE
       python3 -I card.py append HOLON FILE [--as ACTOR] [--no-sign] [--key-dir D]
"""
import argparse
import datetime as dt
import json
import os
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import record  # noqa: E402

FENCE_OPEN = '```line'
FENCE_CLOSE = '```'
TITLE_MAX = 120
MAX_FILE = 4 * record.MAX_LINE            # a Card file is its line twice and some prose
NESTED = ('body', 'links')
PAPER_FIELDS = ('v', 'id', 'ts', 'actor', 'for', 'holon', 'type', 'body', 'links', 'audience', 'reason',
                'prev', 'sig')
_PLAIN_KEY = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.@+-]*$')
_KEY_LINE = re.compile(r'^([A-Za-z0-9_][A-Za-z0-9_.@+-]*):(.*)$')
_SAFE_TYPE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
_HEX_ID = re.compile(r'^[0-9a-f]{64}$')
_BARE_FIRST_NO = set('[{\'`|>&*!%@?,-~<=.+')
# words a YAML reader would type otherwise; the front matter is not YAML, but its bare words stay strings there too
_YAML_WORDS = {'yes', 'no', 'on', 'off', 'y', 'n', 'true', 'false', 'null', '~'}
_YAML_TYPED = re.compile(r'^(?:[-+]?(?:\d[\d_]*)?(?:\.[\d_]*)?(?:[eE][-+]?\d+)?|[-+]?0[xXoObB].*|'
                         r'[-+]?\.(?:inf|nan)|\d{4}-\d{1,2}-\d{1,2}.*)$', re.IGNORECASE)
_SEPARATORS = (' ', ' ', '\x85')


def _problem(kind, said, **extra):
    p = {'kind': kind, 'said': said}
    p.update(extra)
    return p


def _clean(line):
    return {k: v for k, v in line.items() if not (isinstance(k, str) and k.startswith('_'))}


# ---------------------------------------------------------------- writing the face

def _bare_ok(s):
    """True when a string may be written bare in front matter and read back as itself."""
    if not s or s != s.strip() or s[0] in _BARE_FIRST_NO:
        return False
    if s.lower() in _YAML_WORDS or (_YAML_TYPED.match(s) and any(c.isdigit() for c in s)):
        return False
    if any(c in s for c in ':#"\\') or any(c in s for c in _SEPARATORS):
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in s):
        return False
    try:
        json.loads(s)
    except ValueError:
        return True
    return False


def _emit_key(k):
    return k if isinstance(k, str) and _PLAIN_KEY.match(k) else json.dumps(k, ensure_ascii=False)


def _emit_value(v):
    if isinstance(v, str) and _bare_ok(v):
        return v
    return json.dumps(v, ensure_ascii=False, allow_nan=False)


def _front_lines(line):
    out = []
    for k, v in record.ordered(line).items():
        key = _emit_key(k)
        if k in NESTED and isinstance(v, dict) and v:
            out.append(key + ':')
            for sk, sv in v.items():
                out.append('  %s: %s' % (_emit_key(sk), _emit_value(sv)))
        else:
            out.append('%s: %s' % (key, _emit_value(v)))
    return out


def _one_line(s):
    return ' '.join(s.split())


def _title(line):
    body = line.get('body') if isinstance(line.get('body'), dict) else {}
    typ = _one_line(record._str(line.get('type'))) or 'line'
    text = ''
    for k in ('title', 'text', 'note'):
        if isinstance(body.get(k), str) and body[k].strip():
            text = _one_line(body[k])
            break
    if len(text) > TITLE_MAX:
        text = text[:TITLE_MAX - 1] + '…'
    return '# ' + typ + (' · ' + text if text else '')


def _prose(line):
    body = line.get('body') if isinstance(line.get('body'), dict) else {}
    text = ''
    for k in ('text', 'title'):
        if isinstance(body.get(k), str) and body[k].strip():
            text = body[k]
            break
    if not text:
        return ''
    rows = []
    for row in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        # a prose row never opens a fence: the fence is the line's alone
        rows.append('\\' + row if row.lstrip().startswith(('```', '~~~')) else row.rstrip())
    return '\n'.join(rows).strip('\n')


def to_markdown(line):
    """The Markdown Card of a line: front matter, title, prose and the fence. Deterministic.

    Keys that begin with `_` are never written. Raises ValueError when the line cannot be
    written as JSON (a NaN, a value of no JSON kind)."""
    if not isinstance(line, dict):
        raise ValueError('a line must be a JSON object')
    clean = _clean(line)
    parts = ['---'] + _front_lines(clean) + ['---', '', _title(clean), '']
    prose = _prose(clean)
    if prose:
        parts += [prose, '']
    parts += [FENCE_OPEN, record.dumps(clean), FENCE_CLOSE]
    return '\n'.join(parts) + '\n'


# ---------------------------------------------------------------- reading the face

def _parse_key(raw):
    """(key, rest) from 'key: value' or '"key": value'; (None, why) when it is neither."""
    if raw.startswith('"'):
        try:
            k, end = json.JSONDecoder().raw_decode(raw)
        except ValueError:
            return None, 'a quoted key that is not JSON'
        if not isinstance(k, str) or raw[end:end + 1] != ':':
            return None, 'a quoted key with no colon after it'
        rest = raw[end + 1:]
    else:
        m = _KEY_LINE.match(raw)
        if not m:
            return None, 'not a key: value line'
        k, rest = m.group(1), m.group(2)
    if rest and not rest.startswith(' '):
        return None, 'a space follows the colon after a key'
    return k, rest


def _parse_value(text, where):
    """(value, problem or None). JSON first; a bare string only when it is safe to be one."""
    s = text.strip(' ')
    if s == '':
        return '', None
    try:
        json.loads(s)                     # JSON at all? (a hex id that starts like 1e5 is not)
        is_json = True
    except (ValueError, RecursionError):
        is_json = False
    if is_json:
        try:
            return record.loads(s), None  # then strictly: no fraction, exponent, NaN or twice-named key
        except (record.LineError, ValueError, RecursionError) as e:
            return None, _problem('not_whole' if 'whole' in str(e) or 'number' in str(e) else 'bad_value',
                                  '%s: %s' % (where, e), field=where)
    bad = (s[0] in '[{' or any(c in s for c in '#"') or ': ' in s or s.endswith(':')
           or any(ord(c) < 32 or ord(c) == 127 for c in s))
    if bad:
        return None, _problem('bad_value', '%s: %r is neither JSON nor a plain word '
                                           '(quote it as JSON)' % (where, s[:60]), field=where)
    return s, None


def _parse_front(rows, first_no):
    front, problems, opened, cur = {}, [], set(), None
    for n, raw in enumerate(rows, first_no):
        if raw.strip() == '':
            continue
        lead = raw[:len(raw) - len(raw.lstrip())]
        if '\t' in lead:
            problems.append(_problem('bad_indent', 'line %d: a tab in the indent; two spaces only' % n))
            continue
        if lead:
            if lead != '  ' or cur is None:
                problems.append(_problem('bad_indent', 'line %d: only body and links hold one level, '
                                                       'two spaces deep' % n))
                continue
            k, rest = _parse_key(raw[2:])
            if k is None:
                problems.append(_problem('bad_front_matter', 'line %d: %s' % (n, rest)))
                continue
            if k in front[cur]:
                problems.append(_problem('duplicate_key', 'line %d: %s.%s appears twice' % (n, cur, k)))
                continue
            v, p = _parse_value(rest, '%s.%s' % (cur, k))
            if p:
                problems.append(p)
                continue
            front[cur][k] = v
            opened.discard(cur)
            continue
        if raw.startswith('#'):
            problems.append(_problem('comment', 'line %d: front matter holds no comments' % n))
            cur = None
            continue
        k, rest = _parse_key(raw)
        if k is None:
            problems.append(_problem('bad_front_matter', 'line %d: %s' % (n, rest)))
            cur = None
            continue
        if k in front:
            problems.append(_problem('duplicate_key', 'line %d: %s appears twice' % (n, k)))
            cur = None
            continue
        if rest.strip(' ') == '':
            front[k] = {}
            opened.add(k)
            cur = k
            continue
        cur = None
        v, p = _parse_value(rest, k)
        if p:
            problems.append(p)
            continue
        front[k] = v
    for k in opened:                                # 'key:' with nothing under it
        front[k] = {} if k in NESTED else ''
    return front, problems


def _split(text):
    """(front rows, first row number, rows after the front matter, problems)."""
    rows = text.split('\n')
    if not rows or rows[0].rstrip(' ') != '---':
        return None, 0, rows, [_problem('no_front_matter', 'a Card begins with a line of three dashes')]
    for j in range(1, len(rows)):
        if rows[j].rstrip(' ') == '---':
            return rows[1:j], 2, rows[j + 1:], []
    return None, 0, rows[1:], [_problem('no_front_matter', 'the front matter is never closed by three dashes')]


def _find_fence(rows):
    """(raw line text or None, problems, present): the one fence, which closes the file."""
    opens = [i for i, r in enumerate(rows) if r.rstrip(' ') == FENCE_OPEN]
    if not opens:
        return None, [], False
    problems = []
    if len(opens) > 1:
        problems.append(_problem('two_fences', 'more than one line fence; the last is read'))
    i = opens[-1]
    if i + 2 >= len(rows) or rows[i + 2].rstrip(' ') != FENCE_CLOSE or any(r.strip() for r in rows[i + 3:]):
        return None, problems + [_problem('bad_fence', 'the line fence holds one line, is closed by ``` '
                                                       'and closes the file')], True
    return rows[i + 1], problems, True


def _paper_line(front):
    """(line or None, problems): the line a hand-written Card makes (unsalted unless it says)."""
    problems = []
    for k in front:
        if k not in PAPER_FIELDS:
            problems.append(_problem('unknown_field', 'a hand-written Card carries only the line\'s own '
                                                      'fields; %r is not one' % k, field=k))
    try:
        f = record.normalize(front)
    except (record.LineError, ValueError) as e:
        return None, problems + [_problem('not_whole', str(e))]
    for k in ('actor', 'for', 'type'):
        if not record._str(f.get(k)):
            problems.append(_problem('missing_' + k, 'a Card names its %s' % k, field=k))
    for k in ('ts', 'holon', 'prev', 'sig', 'id'):
        if k in f and not isinstance(f[k], str):
            problems.append(_problem('bad_value', '%s is text' % k, field=k))
    actor, for_ = record._str(f.get('actor')), record._str(f.get('for'))
    if actor and not (actor.startswith('person:') or actor.startswith('agent:')):
        problems.append(_problem('bad_actor', 'an actor is person:<handle> or agent:<handle>', field='actor'))
    if for_ and not for_.startswith('person:'):
        problems.append(_problem('bad_for', 'for names a Living Intelligence: person:<handle>', field='for'))
    if 'v' in f and f['v'] != 1:
        problems.append(_problem('bad_value', 'this reader knows envelope version 1 only', field='v'))
    if record._str(f.get('sig')):
        problems.append(_problem('sig_without_fence', 'a signature is carried only with its line in the fence; '
                                                      'a hand-written Card is unsigned', field='sig'))
    body = f.get('body', {})
    body = {} if body == '' else body
    links = f.get('links', {})
    links = {} if links == '' else links
    if not isinstance(body, dict):
        problems.append(_problem('bad_value', 'body is a map', field='body'))
    if not isinstance(links, dict) or not all(isinstance(x, str) or (isinstance(x, list) and all(
            isinstance(y, str) for y in x)) for x in links.values()):
        problems.append(_problem('bad_value', 'links is a map of lists of ids', field='links'))
    audience = f.get('audience', 'holon')
    if audience not in record.AUDIENCES:
        problems.append(_problem('bad_value', 'audience is one of %s' % ', '.join(record.AUDIENCES),
                                 field='audience'))
    reason = f.get('reason')
    if reason is None or reason == '':
        reason = 'untrusted' if actor.startswith('agent:') else 'human'
    elif reason not in record.REASONS:
        problems.append(_problem('bad_value', 'reason is one of %s' % ', '.join(record.REASONS), field='reason'))
    if not record._str(f.get('ts')):
        problems.append(_problem('no_ts', 'a hand-written Card says when it was written (ts); without it its '
                                          'id would change at every reading', field='ts'))
    if problems:
        return None, problems
    salt = body.get('body_salt') if isinstance(body.get('body_salt'), str) else ''
    try:
        line = record.make_line(actor, for_, f.get('holon', ''), f['type'], body, links, audience, reason,
                                f.get('prev', ''), f['ts'], salt=salt)
    except (record.LineError, ValueError, TypeError) as e:
        return None, [_problem('bad_value', str(e))]
    if len(record.dumps(line).encode('utf-8')) > record.MAX_LINE:
        return None, [_problem('too_long', 'the line would be longer than %d bytes' % record.MAX_LINE)]
    if record._str(f.get('id')) and f['id'] != line['id']:
        problems.append(_problem('bad_id', 'the Card names an id its content does not make', field='id',
                                 found=f['id'], computed=line['id']))
    return line, problems


def _parse(text):
    """{'front', 'fence_raw', 'problems'}; never raises."""
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            return {'front': None, 'fence_raw': None, 'fenced': False,
                    'problems': [_problem('not_text', 'a Card is UTF-8 text')]}
    if not isinstance(text, str):
        return {'front': None, 'fence_raw': None, 'fenced': False, 'problems': [_problem('not_text', 'a Card is text')]}
    text = text.lstrip('﻿').replace('\r\n', '\n')
    rows, first, rest, problems = _split(text)
    front = None
    if rows is not None:
        front, p = _parse_front(rows, first)
        problems += p
    fence_raw, p, fenced = _find_fence(rest)
    problems += p
    return {'front': front, 'fence_raw': fence_raw, 'fenced': fenced, 'problems': problems}


def _from_fence(raw, front, problems):
    if len(raw.encode('utf-8')) > record.MAX_LINE:
        return None, problems + [_problem('too_long', 'the fenced line is longer than %d bytes' % record.MAX_LINE)]
    try:
        obj = record.loads(raw)
    except (ValueError, RecursionError) as e:
        return None, problems + [_problem('bad_fence', 'the fenced line is not a strict JSON line: %s'
                                          % str(e)[:120])]
    if not isinstance(obj, dict):
        return None, problems + [_problem('bad_fence', 'the fenced line is not a JSON object')]
    line = _clean(obj)
    if not record.check_id(line):
        problems.append(_problem('bad_id', 'the fenced line\'s id does not match its content, or the line '
                                           'breaks the canonical rules', id=line.get('id')))
    if front is not None:
        for k in list(dict.fromkeys(list(front) + list(line))):
            if isinstance(k, str) and k.startswith('_'):
                continue
            try:
                same = k in front and k in line and \
                    record._cjson(record.normalize(front[k])) == record._cjson(line[k])
            except (record.LineError, ValueError, TypeError):
                same = False
            if not same:                  # canonical JSON, so true never passes for 1
                problems.append(_problem('front_matter_differs', 'the front matter and the fenced line differ '
                                                                 'at %s; the fenced line holds' % k, field=k))
    return line, problems


def from_markdown(text):
    """Read a Markdown Card. Returns {"line": dict or None, "paper": bool, "problems": [..],
    "sig_checked": False}.

    With a fence, the line is the fence's (strict JSON, id checked, front matter compared
    field by field; the fenced line wins), and paper is False. Without one, the line is
    built from the front matter as a paper-floor line (unsalted unless the body carries
    `body_salt`, so the same Card always yields the same id), and paper is True. Callers
    act only when problems is empty, and never take an empty list for a good signature: a
    signature is not checked here (`sig_checked` is always False); only the fold verifies it.
    Never raises: every failure is a problem in words."""
    r = _from_markdown(text)
    r['sig_checked'] = False
    return r


def _from_markdown(text):
    try:
        r = _parse(text)
        problems = list(r['problems'])
        if r['fenced']:
            line = None
            if r['fence_raw'] is not None:
                line, problems = _from_fence(r['fence_raw'], r['front'], problems)
            return {'line': line, 'paper': False, 'problems': problems}
        if r['front'] is None or problems:     # a front matter read in part builds no line
            return {'line': None, 'paper': True, 'problems': problems}
        line, p = _paper_line(r['front'])
        return {'line': line, 'paper': True, 'problems': problems + p}
    except Exception as e:  # noqa: BLE001 - the last guard: bad input is a problem, never a crash
        return {'line': None, 'paper': True, 'problems': [_problem('unreadable', 'the Card could not be read: %s'
                                                                   % type(e).__name__)]}


# ---------------------------------------------------------------- files, without following a link

def card_path(holon_dir, line):
    """`<holon>/cards/<type>/<id[:12]>.md`. Raises ValueError on a type or id unfit for a path."""
    if not isinstance(holon_dir, str) or not holon_dir:
        raise ValueError('a Card path needs the holon folder, named as text')
    if not isinstance(line, dict):
        raise ValueError('a Card path needs a line, a JSON object')
    typ, lid = record._str(line.get('type')), record._str(line.get('id'))
    if not _SAFE_TYPE.match(typ):
        raise ValueError('the type %r cannot name a folder' % typ)
    if not _HEX_ID.match(lid):
        raise ValueError('the id is not a sha256 hex digest')
    return os.path.join(holon_dir, 'cards', typ, lid[:12] + '.md')


def _dir_fd(root, parts, make=True):
    """A folder descriptor for root/parts..., each step opened without following a link (made when missing)."""
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | os.O_NOFOLLOW
    fd = os.open(root, flags)
    try:
        for part in parts:
            if part in ('', '.', '..'):
                raise OSError('a path may not climb out of the holon')
            try:
                nfd = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not make:
                    raise
                os.mkdir(part, 0o755, dir_fd=fd)
                nfd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nfd
    except BaseException:
        os.close(fd)
        raise
    return fd


def _read_at(fd, name):
    """The bytes of name in folder fd, None when absent; OSError on a link or a folder."""
    try:
        f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    except FileNotFoundError:
        return None
    with os.fdopen(f, 'rb') as fh:
        return fh.read(MAX_FILE + 1)


def _write_card(holon_dir, line, text):
    """('written' | 'overwrote' | 'unchanged', path). OSError when a link stands in the way."""
    path = card_path(holon_dir, line)
    data = text.encode('utf-8')
    fd = _dir_fd(holon_dir, ['cards', record._str(line.get('type'))])
    try:
        name = os.path.basename(path)
        old = _read_at(fd, name)
        if old == data:
            return 'unchanged', path
        f = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644, dir_fd=fd)
        with os.fdopen(f, 'wb') as fh:
            fh.write(data)
        return ('written' if old is None else 'overwrote'), path
    finally:
        os.close(fd)


def _read_file(path):
    """(bytes or None, why). The file itself is opened without following a link; never raises."""
    if not isinstance(path, (str, bytes, os.PathLike)) or not path:
        return None, 'no file was named'
    try:
        f = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(f, 'rb') as fh:
            if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                return None, '%s is not a plain file' % (path,)
            data = fh.read(MAX_FILE + 1)
    except (OSError, ValueError) as e:
        return None, 'cannot read %s: %s' % (path, getattr(e, 'strerror', None) or e)
    if len(data) > MAX_FILE:
        return None, 'longer than %d bytes' % MAX_FILE
    return data, ''


def _home_refusal(holon_dir):
    """Words when holon_dir is no person's own home with no link where the Cards go, else ''."""
    if not holon_dir or not os.path.isdir(holon_dir):
        return 'no holon folder at %r' % holon_dir
    if os.path.islink(holon_dir) or os.path.islink(os.path.join(holon_dir, 'cards')):
        return 'a link stands where the holon or its cards/ should be; nothing was written'
    if record.holon_kind(holon_dir) != 'person':
        return ('Card files live in the person\'s own home; a cell\'s tree holds only the layout the gate '
                'allows, and the line travels, not the file')
    return ''


def render(holon_dir, ids=None, types=None):
    """Write a Card file for each line the holon holds (record.read), or only the ids or types asked.

    Never follows a link (refused when the holon or cards/ is one; a file or type folder that
    is one is skipped), never rewrites a file that already holds the same bytes, and
    overwrites one whose content differs, saying so. Returns {"written", "skipped",
    "overwrote", "said"}."""
    out = {'written': [], 'skipped': [], 'overwrote': [], 'said': ''}
    why = _home_refusal(holon_dir)
    if why:
        out['said'] = why
        return out
    for name, given in (('ids', ids), ('types', types)):
        if given is not None and not isinstance(given, (list, tuple, set)):
            out['said'] = '%s is a list; nothing was written' % name
            return out
    # a filter that was given matches only its valid entries, so one holding none matches nothing
    want_ids = [x for x in (ids or []) if isinstance(x, str) and x]
    want_types = set(t for t in (types or []) if isinstance(t, str) and t)
    by_id, by_type = ids is not None, types is not None
    seen, matched = set(), set()
    for line in record.read(holon_dir)['lines']:
        lid = record._str(line.get('id'))
        if lid in seen:
            continue
        seen.add(lid)
        if by_type and line.get('type') not in want_types:
            continue
        if by_id:
            hit = [w for w in want_ids if lid == w or (len(w) >= 8 and lid.startswith(w))]
            if not hit:
                continue
            matched.update(hit)
        try:
            state, path = _write_card(holon_dir, line, to_markdown(line))
        except (OSError, ValueError) as e:
            out['skipped'].append({'id': lid, 'why': 'not written: %s' % (getattr(e, 'strerror', None) or e)})
            continue
        if state == 'unchanged':
            out['skipped'].append({'id': lid, 'why': 'already rendered, the same bytes'})
            continue
        out['written'].append(path)
        if state == 'overwrote':
            out['overwrote'].append(path)
    for w in want_ids:
        if w not in matched:
            out['skipped'].append({'id': w, 'why': 'no line with this id is held here'})
    said = '%d Card file(s) written' % len(out['written'])
    if out['overwrote']:
        said += ', %d of them over a file whose content differed' % len(out['overwrote'])
    out['said'] = said + '; %d skipped' % len(out['skipped'])
    return out


def append_card(holon_dir, path, sign=None, key_dir=None, actor=None):
    """Bring a hand-written Card onto the record, then write it back with its fence.

    The Card must be paper (no fence: a Card with one is "already on the record") and read
    with no problem but a missing `ts` (then it is stamped now). It is appended through
    record.append, so prev, id and sig are the record's, and it is salted afresh unless
    the Card carries its own `body_salt` (so it can be elided and exported): the paper id
    was the draft's, never the record's. The file never chooses whose key
    signs: the line is signed only when the caller names the signer (`actor`, which must be
    the Card's actor) and sign is not False; otherwise it stands unsigned, at the paper
    floor. A missing `reason` is `human` for a person and `untrusted` for an agent. The
    Card file is rewritten at card_path, and the hand-written file is removed when it lay
    elsewhere under cards/. Returns record.append's result + {"path", "removed",
    "problems"}; nothing is written when problems is not empty."""
    out = {'line': None, 'file': None, 'signed': False, 'said': '', 'path': None, 'removed': None, 'problems': []}

    def refuse(kind, said):
        out['problems'].append(_problem(kind, said))
        out['said'] = said
        return out

    why = _home_refusal(holon_dir)
    if why:
        return refuse('not_home', why)
    data, why = _read_file(path)
    if data is None:
        return refuse('unreadable', why)
    r = _parse(data)
    if r['fenced']:
        return refuse('on_record', 'already on the record: this Card carries its line in a fence')
    if r['front'] is None or r['problems']:
        out['problems'] = r['problems'] or [_problem('no_front_matter', 'a Card begins with front matter')]
        out['said'] = 'the Card could not be read; nothing was written'
        return out
    front = dict(r['front'])
    if front.get('ts') in (None, ''):
        front['ts'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    line, problems = _paper_line(front)
    if problems or line is None:
        out['problems'] = problems
        out['said'] = 'the Card has problems; nothing was written'
        return out
    if actor is not None and line['actor'] != actor:
        return refuse('not_the_signer', 'the Card\'s actor is %s, not %s; nothing was written' % (line['actor'], actor))
    if sign is True and actor is None:
        return refuse('no_signer', 'to sign, name the signer (actor=, --as); the file never chooses a key')
    hid = record._str(record.holon_info(holon_dir).get('id'))
    if line['holon'] and line['holon'] != hid:
        return refuse('wrong_holon', 'the Card names another holon; nothing was written')
    body = dict(line['body'])
    salt = body.pop('body_salt', None)        # None: a fresh salt, so the line can be elided and exported
    signing = sign is not False and actor is not None
    try:
        res = record.append(holon_dir, line['actor'], line['for'], line['type'], body, line['links'],
                            line['audience'], line['reason'], ts=line['ts'], salt=salt,
                            sign=None if signing else False, key_dir=key_dir)
    except (ValueError, OSError) as e:
        return refuse('not_appended', 'not appended: %s' % e)
    out.update(res)
    if not signing and sign is not False:
        out['said'] = 'unsigned: no signer was named; the line stands at the paper floor'
    try:
        _, new_path = _write_card(holon_dir, res['line'], to_markdown(res['line']))
    except (OSError, ValueError) as e:
        out['said'] = (out['said'] + '; ' if out['said'] else '') + \
            'the line is on the record; its Card file was not written: %s' % (getattr(e, 'strerror', None) or e)
        return out
    out['path'] = new_path
    kept = _remove_draft(holon_dir, path, new_path)
    if kept is None:
        out['removed'] = path
    elif kept:
        out['said'] = (out['said'] + '; ' if out['said'] else '') + kept
    return out


def _remove_draft(holon_dir, path, new_path):
    """Remove a hand-written draft that lay under cards/, by folder descriptor through the holon.

    Returns None when removed, '' when the draft lay outside cards/ (kept, nothing to say),
    and words when it was kept because a step was a link or it was not a plain file."""
    try:
        old, home = os.path.abspath(path), os.path.abspath(holon_dir)
        if old == os.path.abspath(new_path):
            return ''
        rel = os.path.relpath(old, home).split(os.sep)
        if len(rel) < 2 or rel[0] != 'cards' or '..' in rel:
            return ''
        if os.path.realpath(os.path.dirname(old)) != os.path.join(os.path.realpath(home), *rel[:-1]):
            return 'the draft was kept: a link stands on its way'
        fd = _dir_fd(holon_dir, rel[:-1], make=False)
        try:
            st = os.stat(rel[-1], dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                return 'the draft was kept: it is not a plain file'
            os.unlink(rel[-1], dir_fd=fd)
        finally:
            os.close(fd)
        return None
    except OSError:
        return 'the draft was kept: a link stands on its way, or it could not be removed'


# ---------------------------------------------------------------- command line

def _print(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='card.py', description='The Markdown Card: a line\'s human face.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('render', help='write Card files for a holon\'s lines')
    p.add_argument('holon')
    p.add_argument('--type', action='append', default=[])
    p.add_argument('--id', action='append', default=[])
    p = sub.add_parser('read', help='read a Card file and print its line, or its problems')
    p.add_argument('file')
    p = sub.add_parser('append', help='bring a hand-written Card onto the record')
    p.add_argument('holon')
    p.add_argument('file')
    p.add_argument('--as', dest='actor', default=None, help='the signer; must be the Card\'s actor')
    p.add_argument('--no-sign', action='store_true')
    p.add_argument('--key-dir', default=None)
    a = ap.parse_args(argv)
    if a.cmd == 'render':
        _print(render(a.holon, a.id or None, a.type or None))
        return 0
    if a.cmd == 'read':
        data, why = _read_file(a.file)
        if data is None:
            _print({'line': None, 'paper': True, 'problems': [_problem('unreadable', why)], 'said': why})
            return 1
        r = from_markdown(data)
        r['said'] = ('; '.join(p['said'] for p in r['problems']) if r['problems']
                     else ('a hand-written Card, not yet on the record' if r['paper'] else 'a Card on the record'))
        _print(r)
        return 1 if r['problems'] else 0
    r = append_card(a.holon, a.file, sign=False if a.no_sign else None, key_dir=a.key_dir, actor=a.actor)
    _print(r)
    return 1 if r['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
