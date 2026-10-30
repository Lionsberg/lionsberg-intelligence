#!/usr/bin/env python3
"""sightings.py — a holon's triage of what its players saw.

    triage(items, holon=None, lines=None) -> [sighting, ...]
    by_holon(triaged, holons) -> {holon id: {as_of, new, held, elevated, folded}}
    elevate_line(sighting, to, why, witness, actor, now) -> an unsigned `elevate` line (a person signs)
    hold_line(sighting, note, actor, now) -> an unsigned `thread` line anchored to the sighting

Each `sight` line is one sighting, placed in the holon where it was seen, of a kind (from a hazard
to a gift; the kind is the sighting's own `kind`, kept by the fold as body_kind). A cell triages
its members' sightings at its Turn and between:

  new       not yet triaged
  held      a `thread` note is anchored to it: the cell holds it, and says why
  elevated  a person's `elevate` line names it (body.what): published upward by consent, with a
            witness and why
  folded    a duplicate: it links to another sighting (any link: anchored_to, serves, supersedes,
            predecessor), and is folded into that one

Elevated wins over held; folded wins over new. An `elevate` written by an agent, or from untrusted
text, does not count (elevating is a person's act). Files are data, never instructions.
"""
import os
import sys

try:
    from gamecore import normalize, field, links, item_id, holon_of, now_or, actor_kind
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import normalize, field, links, item_id, holon_of, now_or, actor_kind

LINK_RELS = ('anchored_to', 'serves', 'supersedes', 'predecessor')


def _kind(s):
    k = field(s, 'body_kind') or field(s, 'sight_kind')
    if not k and field(s, 'kind') not in ('sighting', 'sight', None):
        k = field(s, 'kind')
    return k


def triage(items, holon=None, lines=None):
    norm = normalize(items)
    sights = {item_id(s): s for s in norm.get('sighting', []) if item_id(s)}
    elevated = {}
    for l in list(lines or []) + list(norm.get('elevate', [])):
        if not isinstance(l, dict) or 'elevate' not in (l.get('type'), l.get('kind')):
            continue
        a = l.get('actor')
        if actor_kind(a) != 'person' or l.get('for') not in (None, a) or l.get('reason') == 'untrusted':
            continue
        b = l.get('body') if isinstance(l.get('body'), dict) else l
        what = b.get('what')
        if what in sights and what not in elevated:
            elevated[what] = {'by': a, 'to': b.get('to'), 'why': b.get('why'), 'witness': b.get('witness'),
                              'line': l.get('id'), 'ts': l.get('ts')}
    held = {}
    for th in norm.get('thread', []):
        a = field(th, 'anchor')
        anchors = set(links(th, 'anchored_to')) | ({a} if isinstance(a, str) else set(a) if isinstance(a, list) else set())
        for sid in anchors & set(sights):
            held.setdefault(sid, {'thread': item_id(th), 'note': str(field(th, 'text') or '')[:200],
                                  'by': field(th, 'actor')})
    out = []
    for sid, s in sights.items():
        if holon and holon_of(s) != holon:
            continue
        into = next((x for r in LINK_RELS for x in links(s, r) if x in sights and x != sid), None)
        row = {'id': sid, 'holon': holon_of(s), 'kind': _kind(s), 'text': str(field(s, 'text') or '')[:280],
               'where': field(s, 'where'), 'actor': field(s, 'actor'), 'ts': field(s, 'ts')}
        if sid in elevated:
            row.update(status='elevated', elevated=elevated[sid])
        elif sid in held:
            row.update(status='held', held=held[sid])
        elif into:
            row.update(status='folded', folded_into=into)
        else:
            row.update(status='new')
        out.append(row)
    return sorted(out, key=lambda r: (r['holon'], str(r['ts'] or ''), r['id']))


def by_holon(triaged, holons=None):
    out = {}
    for h in holons or []:
        if isinstance(h, dict) and h.get('id'):
            out[h['id']] = {'as_of': (h.get('as_of') or {}).get('ts') if isinstance(h.get('as_of'), dict) else None,
                            'new': [], 'held': [], 'elevated': [], 'folded': []}
    for r in triaged or []:
        b = out.setdefault(r['holon'], {'as_of': None, 'new': [], 'held': [], 'elevated': [], 'folded': []})
        b[r['status']].append(r)
    return out


def _line(actor, holon, type_, body, links_, now):
    try:
        import record
        return record.make_line(actor, actor, holon, type_, body, links_, ts=now_or(now).isoformat(timespec='seconds'))
    except Exception:
        from gamecore import canonical_id
        l = {'v': 1, 'ts': now_or(now).isoformat(timespec='seconds'), 'actor': actor, 'for': actor, 'holon': holon,
             'type': type_, 'body': body, 'links': links_ or {}, 'audience': 'holon', 'reason': 'human', 'prev': ''}
        l['id'] = canonical_id(l)
        l['sig'] = ''
        return l


def elevate_line(sighting, to, why, witness, actor, now=None):
    """The `elevate` line a person signs: publish this sighting upward, with a witness and why."""
    return _line(actor, sighting.get('holon'), 'elevate',
                 {'what': sighting.get('id'), 'to': to, 'why': why, 'witness': witness}, None, now)


def hold_line(sighting, note, actor, now=None):
    """A hold is a thread note anchored to the sighting, saying why it is held."""
    return _line(actor, sighting.get('holon'), 'thread', {'text': note}, {'anchored_to': [sighting.get('id')]}, now)
