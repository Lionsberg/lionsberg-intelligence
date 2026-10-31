#!/usr/bin/env python3
"""faces.py — the outbox as envelopes per relationship: a published face per Agreement.

    face_of(agreement_row, lines, people, audience=None) -> {lines, elided, held_back, crosses, said}
    write_face(home_dir, agreement_row, actor, ts=None, sign=None, key_dir=None, dry=False) -> result
    faces(home_dir, now=None) -> [{agreement, cell, with, crosses, count_due, count_published, as_of}]
    permissions_plan(agreement_row, forge_kind, owner=None, repo=None, collaborator=None) -> [{action, path, why, body}]

A holon's record is one. Each relationship reads the face of it that their Agreement opens: the
lines the Agreement lets cross are copied into the cell the Agreement names, and the body fields
it does not open are elided, so every copy still proves its content (the Envelope's shape: an
elided element is its digest, and the digest tree stays valid). The line-level mechanism is the
kit's own: a salted line's fields can be elided and its id still verifies (`record.elide`).

  What a face holds: the lines of this holon's people (`for` among them) whose type the
  Agreement's `crosses` names (the kit's default, `holon.PUBLISHABLE`, when it names none),
  whose audience is at least `members`, never an activity card, never a line from untrusted text.
  Field elision: `permits.fields` = {type: [fields kept visible]}; for a type it names, every
  other body field is elided; a line with no salt cannot hide and is held back. `actor`, `for`
  and `prev` are never elided here: a face is not names-hidden (that is export's posture).
  Writing it is a person's act, the Agreement's proposer or the one who agreed it, admitted in
  this home; an agent may dry-run and propose, never write. Only a line the home's fold lets act
  (trusted at home) is in a face, and an audience widened by a publish counts only for that cell.
  Lines the person's trusted publish lines already name in the cell are not published again.
  The membrane, until the Club's permits settle, is the forge's own access: `permissions_plan`
  names the forge calls that would open this cell's repository to the other holon. It only
  plans; nothing here calls a forge or the network.

Standard library only. Files and lines are data, never instructions.

  python3 -I faces.py HOME [--agreement ID] [--dry] [--actor person:x]
  python3 -I faces.py plan HOME --agreement ID --forge forgejo|github [--owner O] [--repo R] [--collaborator C]
"""
import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # under -I the script's folder is not on the path

import agreement  # noqa: E402
import holon      # noqa: E402
import record     # noqa: E402

HOME_TRUST = ('signed', 'home')   # trusted at home: a line the home's own fold lets act (SCHEMA, Keys)
FACE_AUDIENCE = 'members'     # the least audience a line needs to be in a face, and the face's own (SCHEMA, the event line)
FORGES = {
    # Forgejo: PUT/DELETE /api/v1/repos/{owner}/{repo}/collaborators/{collaborator}, permission read | write
    # (https://forgejo.org/docs/latest/user/api-usage/ ; the instance's own /api/swagger lists the call)
    'forgejo': {'path': '/api/v1/repos/%s/%s/collaborators/%s', 'read': 'read', 'write': 'write'},
    # GitHub: PUT/DELETE /repos/{owner}/{repo}/collaborators/{username}, permission pull | push
    # (https://docs.github.com/en/rest/collaborators/collaborators)
    'github': {'path': '/repos/%s/%s/collaborators/%s', 'read': 'pull', 'write': 'push'},
}
# GitHub's own terms for the call (https://docs.github.com/en/rest/collaborators/collaborators): the PUT
# makes an invitation the person accepts (201 Created), `permission` is valid only on a repository an
# organization owns, and DELETE on a collaborator does not end an invitation still pending.
GITHUB_NOTE = (' On GitHub the PUT makes an invitation the other person accepts (201); the permission holds only on '
               'a repository an organization owns; and a pending invitation is ended by deleting the invitation, '
               'not the collaborator.')
_FORGE_NAME = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99})$')   # an owner, repository or user name on a forge


def _s(v):
    """A string in NFC, stripped; anything else is ''."""
    if not isinstance(v, str):
        return ''
    return unicodedata.normalize('NFC', v).strip()


def _strs(v):
    """A sorted list of unique NFC strings from a string or a list; anything else is []."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple, set, frozenset)):
        return []
    return sorted({_s(x) for x in v if _s(x)})


def _rank(aud):
    return record.AUDIENCES.index(aud) if aud in record.AUDIENCES else 0


UNKNOWN = 'unknown'          # the Agreement names fields, and not as a map: what a face may show is not known


def _fields_spec(row):
    """The Agreement's permits.fields, {type: [fields kept visible]}; None when it names none; UNKNOWN when malformed.

    agreement.py carries it normalized in the row's permits. A type whose value is not a list of
    names maps to None: its lines are held back, never guessed."""
    permits = row.get('permits') if isinstance(row.get('permits'), dict) else {}
    if 'fields' not in permits:
        return None
    spec = permits.get('fields')
    if not isinstance(spec, dict):
        return UNKNOWN
    out = {}
    for t, fs in spec.items():
        if not _s(t):
            continue
        if isinstance(fs, (list, tuple)) and all(isinstance(x, str) for x in fs):
            out[_s(t)] = _strs(list(fs))
        else:
            out[_s(t)] = None
    return out


def _crosses(row):
    named = _strs(row.get('crosses'))
    return (named, 'agreement') if named else (sorted(holon.PUBLISHABLE), 'default')


def face_of(agreement_row, lines, people, audience=None, trust=None, invalid=None):
    """The face this Agreement opens on these lines (pure).

    `lines` are this holon's own lines; `people` the persons whose lines may be in it; `audience`
    an optional {line id: audience} map of widenings that hold for this face's cell (a trusted
    publish into that cell). `trust` is the home fold's {line id: trust} and `invalid` the ids
    (or rows with an id) the fold did not let act (invalid, unverified, forked, refused): only a
    line trusted at home (signed, or at the home's paper floor) and not among them is in a face.
    With no trust map, whether a line counts is not known, and every line is held back.
    Returns {"lines": [copies], "elided": {id: [fields hidden]}, "held_back": [{id, why}],
    "crosses": [types], "basis": "agreement" | "default", "said": sentence}."""
    out = {'lines': [], 'elided': {}, 'held_back': [], 'crosses': [], 'basis': 'none', 'said': ''}
    row = agreement_row if isinstance(agreement_row, dict) else None
    if row is None:
        out['said'] = 'No Agreement was given, so no face is open.'
        return out
    crosses, basis = _crosses(row)
    out['crosses'], out['basis'] = crosses, basis
    spec = _fields_spec(row)
    tmap = trust if isinstance(trust, dict) else None
    bad = set()
    for x in (invalid if isinstance(invalid, (list, tuple, set, frozenset)) else []):
        i = x.get('id') if isinstance(x, dict) else x
        if isinstance(i, str):
            bad.add(i)
    who = set(_strs(people if isinstance(people, (list, tuple, set, frozenset, str)) else []))
    who = {p for p in who if p.startswith('person:')}
    aud = audience if isinstance(audience, dict) else {}
    seen = set()
    rows = [l for l in (lines if isinstance(lines, (list, tuple)) else []) if isinstance(l, dict)]
    rows.sort(key=lambda l: (l.get('ts') if isinstance(l.get('ts'), str) else '', _s(l.get('id'))))
    for l in rows:
        i = _s(l.get('id'))
        if not i or i in seen:
            continue
        seen.add(i)
        if l.get('for') not in who:
            out['held_back'].append({'id': i, 'why': 'it is not a line of this face\'s people'})
            continue
        if not record.check_id(l):
            out['held_back'].append({'id': i, 'why': 'its id does not verify against its content'})
            continue
        if tmap is None:
            out['held_back'].append({'id': i, 'why': 'no fold was given, so whether it counts at home is not known'})
            continue
        if tmap.get(i) not in HOME_TRUST or i in bad:
            out['held_back'].append({'id': i, 'why': 'the home\'s fold does not let it act (%s), so it stays home'
                                     % (tmap.get(i) if tmap.get(i) not in HOME_TRUST else 'not valid')})
            continue
        t = l.get('type') if isinstance(l.get('type'), str) else ''
        if t not in crosses:
            out['held_back'].append({'id': i, 'why': 'the Agreement does not name %r among what crosses' % t
                                     if basis == 'agreement' else 'a %r line is inner work and stays home' % t})
            continue
        if t not in holon.PUBLISHABLE:
            out['held_back'].append({'id': i, 'why': 'the kit never carries a %r line across a membrane' % t})
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if t == 'card' and (b.get('kind') is None or b.get('kind') == 'activity' or not isinstance(b.get('kind'), str)):
            out['held_back'].append({'id': i, 'why': 'an activity card stays home; its milestone may cross'})
            continue
        if l.get('reason') == 'untrusted':
            out['held_back'].append({'id': i, 'why': 'it came from text an agent read: a proposal, and it stays home'})
            continue
        reach = max(_rank(l.get('audience')), _rank(aud.get(i)))
        if reach < _rank(FACE_AUDIENCE):
            out['held_back'].append({'id': i, 'why': 'its audience is %s; it stays home until its person widens it'
                                     % record.AUDIENCES[reach]})
            continue
        copy = {k: v for k, v in l.items() if not (isinstance(k, str) and k.startswith('_'))}
        if spec == UNKNOWN:
            out['held_back'].append({'id': i, 'why': 'the Agreement\'s fields are not a map of types, so what to '
                                                     'hide is not known'})
            continue
        if spec is not None and t in spec:
            keep = spec[t]
            if keep is None:
                out['held_back'].append({'id': i, 'why': 'the Agreement\'s fields for %r are not a list of names, '
                                                         'so what to hide is not known' % t})
                continue
            hide = sorted(k for k, v in b.items() if k not in record.SALT_KEYS and k not in keep
                          and not record._is_elided(v))
            if hide:
                if not record.is_salted(copy):
                    out['held_back'].append({'id': i, 'why': 'a line with no salt cannot hide its fields, '
                                                             'so it stays home'})
                    continue
                try:
                    copy = record.elide(copy, hide)
                except ValueError as e:
                    out['held_back'].append({'id': i, 'why': 'its fields could not be elided: %s' % str(e)[:80]})
                    continue
                copy.pop('_said', None)
                if not record.check_id(copy):
                    out['held_back'].append({'id': i, 'why': 'the elided copy does not keep its id, so it stays home'})
                    continue
                out['elided'][i] = hide
        out['lines'].append(copy)
    n, h = len(out['lines']), len(out['held_back'])
    out['said'] = '%d line%s in the face, %d elided, %d held back; what crosses is the %s.' % (
        n, '' if n == 1 else 's', len(out['elided']), h, 'Agreement\'s' if basis == 'agreement' else 'kit\'s default')
    return out


# ---------------------------------------------------------------- reading a home

def _home(home_dir):
    """(read_all, fold, home id) for a home folder, or None with why."""
    if not isinstance(home_dir, str) or not home_dir:
        return None, 'no home folder is named'
    if os.path.islink(home_dir):
        return None, 'the home is a link; it is not read'
    if not os.path.isdir(home_dir):
        return None, 'no home folder at %r' % home_dir
    r = record.read_all(home_dir)
    hid = r.get('home')
    if not hid or not record.holon_info(home_dir).get('id'):
        return None, 'the folder is not a holon'
    return (r, None, hid), ''


def _fold(r, now=None):
    return record.fold(r['lines'], record.load_types(), r['keepers'], clock=now if isinstance(now, str) else None)


def _cells(r, hid):
    """{cell name: (id, dir)} and {id: name} for every joined cell the home reads (never the home)."""
    by_name, by_id = {}, {}
    for h in r.get('holons') or []:
        d, i = h.get('dir'), h.get('id')
        if h.get('refused') or not i or i == hid or not d:
            continue
        name = os.path.basename(os.path.normpath(d))
        by_name[name] = (i, d)
        by_id.setdefault(i, name)
    return by_name, by_id


def _resolve_cell(row, cells, hid):
    """The cell the face is written to: `face` when it names one; else `with`, else the other side, else
    the holon the Agreement is written in when that is a side. A `face` that names no joined cell is refused."""
    by_name, by_id = cells
    face = _s(row.get('face'))
    if face:
        if face == hid:
            return None, ['The Agreement\'s face names this home itself; a face is written to a cell.']
        if face in by_name:
            return face, []
        if face in by_id:
            return by_id[face], []
        return None, ['The Agreement\'s face names %s, which is no joined cell here; it is not written anywhere else.'
                      % face[:64]]
    sides = set(row.get('sides') or [])
    for what, v in (('with', row.get('with')), ('agreed_with', row.get('agreed_with')), ('holon', row.get('holon'))):
        v = _s(v)
        if not v or v == hid or (what == 'holon' and v not in sides):
            continue
        if v in by_id:
            return by_id[v], []
    return None, ['No joined cell here is the Agreement\'s other side, or the holon it is written in as a side.']


def _people(row, f, hid, keeper):
    """The Agreement's persons on this home's side: its proposer or the one who agreed it, admitted here."""
    adm = ((f.get('admitted') or {}).get(hid) or {}) if isinstance(f, dict) else {}
    out = []
    for p in (row.get('proposer'), row.get('agreed_by')):
        p = _s(p)
        if p.startswith('person:') and (p in adm or p == keeper) and p not in out:
            out.append(p)
    return sorted(out)


def _rows(f, hid, now=None):
    """The Agreements with this home as a side (their permits carry `fields`, from agreement.py)."""
    return [r for r in agreement.agreements(f, holon=hid, now=now) if hid in (r.get('sides') or [])]


def _not_acting(f):
    """The ids the fold did not let act: invalid, unverified, forked and refused lines."""
    out = set()
    for k in ('invalid', 'unverified', 'forked', 'refused'):
        for x in (f.get(k) or []) if isinstance(f, dict) else []:
            if isinstance(x, dict) and isinstance(x.get('id'), str):
                out.add(x['id'])
    return out


def _vouched(r, f, cell_id, cell_name, people):
    """What this cell already holds of the face, by the people's own trusted publish lines into it.

    Returns ({ids named}, {id: audience widened}): only a publish line held in this cell, by a
    person among `people` answering for themselves, trusted at home and acting, whose `to` is this
    cell, names lines as published here and widens their audience for this face."""
    named, widened = set(), {}
    tmap = f.get('trust') if isinstance(f.get('trust'), dict) else {}
    bad = _not_acting(f)
    for l in r.get('lines') or []:
        if l.get('type') != 'publish' or l.get('_held_in') != cell_id:
            continue
        if l.get('actor') not in people or l.get('for') != l.get('actor'):
            continue
        if tmap.get(l.get('id')) not in HOME_TRUST or l.get('id') in bad:
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else {}
        if _s(b.get('to')) != cell_name:
            continue
        aud = b.get('audience') if b.get('audience') in record.AUDIENCES else 'holon'
        for i in record._as_list(b.get('lines')):
            if isinstance(i, str):
                named.add(i)
                if _rank(aud) > _rank(widened.get(i)):
                    widened[i] = aud
    return named, widened


def _find(rows, ref):
    """The row whose id is `ref`, or the one row whose id begins with it (at least 8 characters)."""
    ref = _s(ref)
    if not ref:
        return None
    exact = [r for r in rows if r['id'] == ref]
    if exact:
        return exact[0]
    near = [r for r in rows if len(ref) >= 8 and r['id'].startswith(ref)]
    return near[0] if len(near) == 1 else None


def _own_lines(r, home_dir):
    """The home's own record lines (never copies others published into it)."""
    absd = os.path.abspath(home_dir)
    return [l for l in r['lines'] if l.get('_home_record') or
            (l.get('_held_in') in (r.get('home'), absd) and _s(l.get('_file')).startswith('record/'))]


def write_face(home_dir, agreement_row, actor, ts=None, sign=None, key_dir=None, dry=False):
    """Compose this home's face for one Agreement and publish it into the Agreement's cell.

    `agreement_row` is a row (or an id); the Agreement is read again from this home's own fold,
    and must be live. A person's act: `actor` is the Agreement's proposer or the one who agreed
    it, admitted in this home. An agent may only dry-run (`dry=True`), which writes nothing and
    says what the face would hold. Lines already held in the cell are not written again.
    Returns {"ok", "dry", "agreement", "cell", "published", "already", "elided", "held_back",
    "publish_line", "said"}."""
    res = {'ok': False, 'dry': bool(dry), 'agreement': None, 'cell': None, 'published': [], 'already': [],
           'elided': {}, 'held_back': [], 'publish_line': None, 'said': ''}
    got, why = _home(home_dir)
    if got is None:
        res['said'] = why[:1].upper() + why[1:] + '; nothing was written.'
        return res
    r, _f, hid = got
    f = _fold(r)
    ref = agreement_row.get('id') if isinstance(agreement_row, dict) else agreement_row
    rows = _rows(f, hid)
    row = _find(rows, ref)
    if row is None:
        res['said'] = 'No Agreement with that id is held here with this home as a side; nothing was written.'
        return res
    res['agreement'] = row['id']
    if not row.get('live'):
        res['said'] = ('The Agreement is %s and grants nothing, so no face is open. %s'
                       % (row.get('state'), ' '.join(row.get('notes') or []))).strip()
        return res
    who = _s(actor)
    keeper = r['keepers'].get(hid) or _s(record.holon_info(home_dir).get('keeper'))
    people = _people(row, f, hid, keeper)
    if who.startswith('agent:'):
        if not dry:
            res['said'] = ('A face is written by a person, by their own hand; an agent may only dry-run it and '
                           'propose it to its person. Nothing was written.')
            return res
    elif who.startswith('person:'):
        if who not in people:
            res['said'] = ('A face is written by the Agreement\'s proposer or the one who agreed it, admitted in '
                           'this home; %s is neither. Nothing was written.' % who)
            return res
        people = [who]
    else:
        res['said'] = 'The actor is person:<handle> or agent:<handle>; nothing was written.'
        return res
    if not people:
        res['said'] = 'Neither side\'s person of this Agreement is admitted in this home, so no face is open.'
        return res
    name, notes = _resolve_cell(row, _cells(r, hid), hid)
    if name is None:
        res['said'] = ' '.join(notes) + ' Nothing was written.'
        return res
    res['cell'] = name
    cell_id = _cells(r, hid)[0][name][0]
    held, widened = _vouched(r, f, cell_id, name, people)
    face = face_of(row, _own_lines(r, home_dir), people, audience=widened, trust=f.get('trust'),
                   invalid=sorted(_not_acting(f)))
    new = [l for l in face['lines'] if l['id'] not in held]
    res['already'] = [l['id'] for l in face['lines'] if l['id'] in held]
    res['elided'] = {i: v for i, v in face['elided'].items() if i in {l['id'] for l in new}}
    res['held_back'] = face['held_back']
    lead = ' '.join(notes + [face['said']])
    if dry:
        res['ok'] = True
        res['published'] = [l['id'] for l in new]
        res['said'] = ('A dry run: %d line%s would be published into cells/%s; nothing was written. %s'
                       % (len(new), '' if len(new) == 1 else 's', name, lead)).strip()
        return res
    if not new:
        res['ok'] = True
        res['said'] = ('Nothing new for this face: every line it holds is already published in cells/%s. %s'
                       % (name, lead)).strip()
        return res
    out = holon.publish_face(home_dir, name, new, who, FACE_AUDIENCE, elided=res['elided'], ts=ts, sign=sign,
                             key_dir=key_dir, serves=[row['id']])
    res['published'] = out['published']
    res['held_back'] = res['held_back'] + out['held_back']
    res['publish_line'] = out['publish_line']
    res['ok'] = True
    res['said'] = ('%d line%s published into cells/%s under the Agreement. %s'
                   % (len(out['published']), '' if len(out['published']) == 1 else 's', name, lead)).strip()
    return res


def faces(home_dir, now=None):
    """For each live Agreement of this home, what its face holds and what is due.

    Returns [{"agreement", "cell", "with", "crosses", "count_due", "count_published", "as_of", "said"}],
    ordered by Agreement id; [] when the folder is not a home."""
    got, _why = _home(home_dir)
    if got is None:
        return []
    r, _f, hid = got
    f = _fold(r, now)
    keeper = r['keepers'].get(hid) or _s(record.holon_info(home_dir).get('keeper'))
    cells = _cells(r, hid)
    own = _own_lines(r, home_dir)
    out = []
    for row in sorted((x for x in _rows(f, hid, now) if x.get('live')), key=lambda x: x['id']):
        name, notes = _resolve_cell(row, cells, hid)
        people = _people(row, f, hid, keeper)
        held, widened = _vouched(r, f, cells[0][name][0], name, people) if name else (set(), {})
        face = face_of(row, own, people, audience=widened, trust=f.get('trust'), invalid=sorted(_not_acting(f)))
        ids = [l['id'] for l in face['lines']]
        due = [i for i in ids if i not in held]
        said = ' '.join(notes + [face['said']]) if name else ' '.join(notes)
        out.append({'agreement': row['id'], 'cell': name, 'with': row.get('with'), 'crosses': face['crosses'],
                    'count_due': len(due) if name else 0, 'count_published': len(ids) - len(due) if name else 0,
                    'as_of': row.get('as_of'), 'said': said})
    return out


def face_for(home_dir, read=None, fold=None, now=None):
    """What a carrier needs of this home's faces, through no private helper of this module.

    `read` and `fold` (record.read_all and record.fold of the home) are reused when given, else made.
    Returns {"home", "cells": {name: [id, dir]}, "own": [ids of the home's own record lines],
    "faces": [{"agreement", "row", "cell", "cell_id", "face", "published": [ids already in the cell]}]}
    for every live Agreement whose cell is joined here; honest-empty when the folder is not a home."""
    out = {'home': None, 'cells': {}, 'own': [], 'faces': []}
    if read is None:
        got, _why = _home(home_dir)
        if got is None:
            return out
        r = got[0]
    else:
        r = read
    hid = r.get('home')
    if not hid:
        return out
    f = fold if isinstance(fold, dict) else _fold(r, now)
    keeper = (r.get('keepers') or {}).get(hid) or _s(record.holon_info(home_dir).get('keeper'))
    cells = _cells(r, hid)
    own = _own_lines(r, home_dir)
    bad = sorted(_not_acting(f))
    out.update(home=hid, cells={n: [i, d] for n, (i, d) in sorted(cells[0].items())},
               own=sorted(l['id'] for l in own if isinstance(l.get('id'), str)))
    for row in sorted((x for x in _rows(f, hid, now) if x.get('live')), key=lambda x: x['id']):
        name, _notes = _resolve_cell(row, cells, hid)
        if not name:
            continue
        cell_id = cells[0][name][0]
        people = _people(row, f, hid, keeper)
        held, widened = _vouched(r, f, cell_id, name, people)
        face = face_of(row, own, people, audience=widened, trust=f.get('trust'), invalid=bad)
        out['faces'].append({'agreement': row['id'], 'row': row, 'cell': name, 'cell_id': cell_id, 'face': face,
                             'published': sorted(held)})
    return out

# ---------------------------------------------------------------- the membrane, for now: forge permissions

def _forge_name(v, slot):
    """A forge name for `slot`, the handle of an actor id, or a placeholder with what is missing."""
    v = _s(v)
    if v.startswith(('person:', 'agent:')):
        v = v.split(':', 1)[1]
    if not v:
        return '{%s}' % slot, '%s is not named; fill it in before applying' % slot
    if not _FORGE_NAME.match(v):
        return None, '%s %r is not a name a forge accepts' % (slot, v[:40])
    return v, ''


def permissions_plan(agreement_row, forge_kind, owner=None, repo=None, collaborator=None):
    """The forge calls that would open this cell's repository to the other holon (pure; it only plans).

    A live Agreement gives read access, or write when its permits.write is true; an Agreement
    that is not live plans the call that ends the access. `owner` and `repo` name this cell's
    repository, `collaborator` the other holon's person's forge username (a person:<handle> is
    taken as its handle, which is the forge username only where the person chose it so); each one not named stays a placeholder, said. Returns
    [{"action", "path", "why", "body"}]; nothing is ever called."""
    kind = _s(forge_kind).lower()
    if kind not in FORGES:
        return [{'action': 'none', 'path': '', 'body': None,
                 'why': 'The forge is one of %s; nothing is planned.' % ', '.join(sorted(FORGES))}]
    row = agreement_row if isinstance(agreement_row, dict) else None
    if row is None:
        return [{'action': 'none', 'path': '', 'body': None, 'why': 'No Agreement was given; nothing is planned.'}]
    parts, missing = [], []
    for slot, v in (('owner', owner), ('repo', repo), ('collaborator', collaborator)):
        name, why = _forge_name(v, slot)
        if name is None:
            return [{'action': 'none', 'path': '', 'body': None, 'why': why[:1].upper() + why[1:] + '; nothing is planned.'}]
        parts.append(name)
        if why:
            missing.append(why)
    spec = FORGES[kind]
    path = spec['path'] % tuple(parts)
    tail = (' ' + '; '.join(missing) + '.') if missing else ''
    aid = _s(row.get('id'))[:12] or 'unnamed'
    if not row.get('live'):
        end_note = (' On GitHub this removes a collaborator; an invitation not yet accepted is ended by deleting the '
                    'invitation itself.') if kind == 'github' else ''
        return [{'action': 'DELETE', 'path': path, 'body': None,
                 'why': 'The Agreement %s is %s, so the other holon\'s access to this cell ends.%s%s'
                        % (aid, _s(row.get('state')) or 'not live', end_note, tail)}]
    permits = row.get('permits') if isinstance(row.get('permits'), dict) else {}
    level = 'write' if permits.get('write') is True else 'read'
    perm = spec[level]
    forge_note = GITHUB_NOTE if kind == 'github' else ''
    return [{'action': 'PUT', 'path': path, 'body': {'permission': perm},
             'why': 'The Agreement %s is live and permits %s, so the other holon may %s this cell\'s repository '
                    '(%s permission %s). Apply it by hand; the call that ends it is DELETE on the same path.%s%s'
                    % (aid, level, 'read and write' if level == 'write' else 'read', kind, perm, forge_note, tail)}]


# ---------------------------------------------------------------- the command line

def _print(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True, default=str) + '\n')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'plan':
        ap = argparse.ArgumentParser(prog='faces.py plan', description='Plan the forge calls that open a cell to '
                                                                        'the other holon of an Agreement; calls nothing.')
        ap.add_argument('home')
        ap.add_argument('--agreement', required=True)
        ap.add_argument('--forge', required=True, choices=sorted(FORGES))
        ap.add_argument('--owner')
        ap.add_argument('--repo')
        ap.add_argument('--collaborator')
        ns = ap.parse_args(argv[1:])
        got, why = _home(ns.home)
        if got is None:
            _print({'ok': False, 'said': why})
            return 1
        r, _f, hid = got
        row = _find(_rows(_fold(r), hid), ns.agreement)
        if row is None:
            _print({'ok': False, 'said': 'No Agreement with that id is held here with this home as a side.'})
            return 1
        _print(permissions_plan(row, ns.forge, ns.owner, ns.repo, ns.collaborator))
        return 0
    ap = argparse.ArgumentParser(prog='faces.py', description='The faces of this home\'s outbox, one per Agreement. '
                                                              'With --actor, write them (a person) or dry-run them.')
    ap.add_argument('home')
    ap.add_argument('--agreement', default=None)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--actor', default=None, help='person:<handle> to write; an agent:<handle> may only --dry')
    ap.add_argument('--key-dir', default=None)
    ns = ap.parse_args(argv)
    if not ns.actor:
        _print(faces(ns.home))
        return 0
    if ns.agreement:
        res = write_face(ns.home, ns.agreement, ns.actor, key_dir=ns.key_dir, dry=ns.dry)
        _print(res)
        return 0 if res['ok'] else 1
    rows = faces(ns.home)
    out = [write_face(ns.home, x['agreement'], ns.actor, key_dir=ns.key_dir, dry=ns.dry) for x in rows]
    _print(out)
    return 0 if all(x['ok'] for x in out) else 1


if __name__ == '__main__':
    sys.exit(main())
