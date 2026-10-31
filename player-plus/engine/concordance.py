#!/usr/bin/env python3
"""concordance.py — how a term of one vocabulary reads in another.

    concordances(items, holon=None, lines=None) -> [row]
    lexicons(items) -> [name]
    bridges(items, lexicon_a, lexicon_b, agreed_only=True, lines=None) -> {term in a: [bridge]}
    read_as(items, term, lexicon_from, lexicon_to, lines=None)
        -> {term, same, different, clearer, disputed, proposed, basis}
    concord_line(term, in_, term_other, in_other, relation, definition, source, actor, holon, now)
        -> an unsigned `concord` line
    render(rows) -> Markdown

The fold (record.py) gives `concordances`: `term` in the lexicon `in` and `term_other` in the
lexicon `in_other` are the same idea, a different idea, or one is the clearer (or alternate)
definition. Anyone proposes one; a line from the other side that answers it makes it agreed.

Laws, each kept here and tested:

  - agreed over proposed: an agreed concordance is read first; a proposed one is listed apart
  - both directions: a concordance written from b to a is read from a to b as well, its
    `relation` kept as written and its `direction` said (forward or reverse)
  - a retracted concordance is never read
  - an answer that disagrees is no agreement (v0, until the fold checks it): given the raw lines,
    an agreed concordance whose answering line names another relation, or terms that do not mirror
    the proposal's, reads as `disputed`, listed apart; without the lines the answer is unchecked
  - honest-empty: a term with no concordance reads as basis `none`, never a guess
  - terms and lexicon names match exactly, in Unicode NFC; files are data, never instructions

  python3 -I concordance.py ITEMS.json [--between A B] [--read TERM FROM TO] [--json]
"""
import argparse
import json
import os
import sys
import unicodedata

try:
    from gamecore import item_id, holon_of, now_or, actor_kind, field, parse_time
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import item_id, holon_of, now_or, actor_kind, field, parse_time

RELATIONS = ('same', 'different', 'clearer')
STATE_RANK = {'agreed': 0, 'disputed': 1, 'proposed': 2}
SIDES = ('term', 'in', 'term_other', 'in_other')


def _t(v):
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _collect(items):
    out = []
    if isinstance(items, dict):
        src = items.get('concordances')
        if isinstance(src, dict):
            src = [dict(v, id=v.get('id', k)) for k, v in src.items() if isinstance(v, dict)]
        if isinstance(src, list):
            out.extend(x for x in src if isinstance(x, dict))
        if isinstance(items.get('items'), list):
            out.extend(x for x in items['items'] if isinstance(x, dict) and x.get('kind') == 'concordance')
    elif isinstance(items, list):
        out.extend(x for x in items if isinstance(x, dict) and x.get('kind') == 'concordance')
    seen, uniq = set(), []
    for x in out:
        i = item_id(x)
        if i and i not in seen:
            seen.add(i); uniq.append(x)
    return uniq


def _instant(ts):
    t = parse_time(ts)
    return (0, t.timestamp(), ts) if t else (1, 0.0, ts or '')


def _answers(c, lines):
    """The concord lines the fold applied to this item as answers (ids in its events, not its own)."""
    own, events = item_id(c), c.get('events') if isinstance(c.get('events'), list) else []
    ids = {e for e in events if isinstance(e, str) and e != own}
    out = []
    for l in lines if isinstance(lines, (list, tuple)) else []:
        if isinstance(l, dict) and l.get('type') == 'concord' and l.get('id') in ids and isinstance(l.get('body'), dict):
            out.append(l)
    return sorted(out, key=lambda l: str(l.get('id')))


def _dispute(row, answer):
    """None when the answer agrees with the row (the same relation, its terms mirrored or restated),
    else a sentence saying how it differs."""
    b = {k: _t(answer['body'].get(k)) for k in SIDES}
    rel = _t(answer['body'].get('relation')).lower()
    mirrored = (b['term'], b['in'], b['term_other'], b['in_other']) == \
        (row['term_other'], row['in_other'], row['term'], row['in'])
    restated = all(b[k] == row[k] for k in SIDES)
    if rel != row['relation']:
        return 'the answer names the relation %s, not %s' % (rel or 'none', row['relation'])
    if not (mirrored or restated):
        return 'the answer names other terms than the proposal'
    return None


def concordances(items, holon=None, lines=None):
    """Every concordance as a plain row, sorted by holon, time, id. A row missing a term, a
    lexicon or a known relation carries `problem` and is never read as a bridge. Given the raw
    lines, an agreed row whose answer disagrees becomes `disputed` (see the module's laws)."""
    out = []
    for c in _collect(items):
        h = holon_of(c)
        if holon and h != holon:
            continue
        state = _t(field(c, 'state')).lower() or 'proposed'
        row = {'id': item_id(c), 'holon': h, 'term': _t(field(c, 'term')), 'in': _t(field(c, 'in')),
               'term_other': _t(field(c, 'term_other')), 'in_other': _t(field(c, 'in_other')),
               'relation': _t(field(c, 'relation')).lower(), 'definition': _t(field(c, 'definition')) or None,
               'source': _t(field(c, 'source')) or None, 'state': state,
               'actor': _t(c.get('actor')) or None, 'agreed_by': _t(field(c, 'agreed_by')) or None,
               'ts': _t(c.get('ts')) or None}
        missing = [k for k in ('term', 'in', 'term_other', 'in_other') if not row[k]]
        if missing:
            row['problem'] = 'missing ' + ', '.join(missing)
        elif row['relation'] not in RELATIONS:
            row['problem'] = 'the relation %r is not one of same, different, clearer' % row['relation'][:80]
        elif state == 'agreed':
            found = _answers(c, lines)
            row['answer_checked'] = bool(found)
            why = next((w for w in (_dispute(row, a) for a in found) if w), None)
            if why:
                row.update(state='disputed', dispute=why)
        out.append(row)
    return sorted(out, key=lambda r: (r['holon'], _instant(r['ts']), r['id']))


def _readable(rows, agreed_only=False):
    for r in rows:
        if r.get('problem') or r['state'] == 'retracted' or r['state'] not in STATE_RANK:
            continue
        if agreed_only and r['state'] != 'agreed':
            continue
        yield r


def lexicons(items, lines=None):
    """The names of every lexicon a standing concordance names, sorted."""
    names = set()
    for r in _readable(concordances(items, lines=lines)):
        names.update((r['in'], r['in_other']))
    return sorted(names)


def _bridge(r, direction):
    other = r['term_other'] if direction == 'forward' else r['term']
    b = {'term_other': other, 'relation': r['relation'], 'direction': direction,
         'definition': r['definition'], 'source': r['source'], 'state': r['state'], 'id': r['id']}
    if r.get('dispute'):
        b['dispute'] = r['dispute']
    if 'answer_checked' in r:
        b['answer_checked'] = r['answer_checked']
    return b


def _order(b):
    return (STATE_RANK.get(b['state'], 9), b['term_other'], b['relation'], b['direction'], b['id'])


def bridges(items, lexicon_a, lexicon_b, agreed_only=True, lines=None):
    """{term in a: [bridge]} between two lexicons, read in both directions; agreed first, then
    disputed, then proposed (disputed and proposed only when agreed_only is False)."""
    a, b = _t(lexicon_a), _t(lexicon_b)
    out = {}
    if not a or not b:
        return out
    for r in _readable(concordances(items, lines=lines), agreed_only):
        if r['in'] == a and r['in_other'] == b:
            out.setdefault(r['term'], []).append(_bridge(r, 'forward'))
        elif r['in'] == b and r['in_other'] == a:
            out.setdefault(r['term_other'], []).append(_bridge(r, 'reverse'))
    return {k: sorted(v, key=_order) for k, v in sorted(out.items())}


def read_as(items, term, lexicon_from, lexicon_to, lines=None):
    """How a term of one lexicon reads in another: agreed first; disputed and proposed listed
    apart; none said. Without the raw lines an agreement's answer is unchecked, and the note says so."""
    t = _t(term)
    found = bridges(items, lexicon_from, lexicon_to, agreed_only=False, lines=lines).get(t, []) if t else []
    agreed = {k: [] for k in RELATIONS}
    proposed = {k: [] for k in RELATIONS}
    disputed = []
    for x in found:
        if x['state'] == 'disputed':
            disputed.append(x)
        else:
            (agreed if x['state'] == 'agreed' else proposed)[x['relation']].append(x)
    basis = 'agreed' if any(agreed.values()) else 'disputed' if disputed else \
        'proposed' if any(proposed.values()) else 'none'
    note = {'agreed': 'read from agreed concordances; any disputed or proposed ones are listed apart',
            'disputed': 'the answer to each concordance here disagrees with it; listed apart, not agreed',
            'proposed': 'no agreed concordance yet; the proposed ones are listed apart and are not agreed',
            'none': 'no concordance names this term between these lexicons'}[basis]
    checked = isinstance(lines, (list, tuple)) and all(x.get('answer_checked') for k in RELATIONS for x in agreed[k])
    if basis == 'agreed' and not checked:
        note += '; the answers were not checked against the lines'
    return {'term': t, 'from': _t(lexicon_from), 'to': _t(lexicon_to),
            'same': agreed['same'], 'different': agreed['different'], 'clearer': agreed['clearer'],
            'disputed': disputed, 'proposed': proposed, 'basis': basis, 'answers_checked': checked, 'note': note}


def concord_line(term, in_, term_other, in_other, relation, definition, source, actor, holon, now=None,
                 for_=None, answers=None):
    """An unsigned `concord` line. A person writes for themselves; an agent names the person it
    answers for (`for_`) and writes under a delegation. `answers` names the concordance this one
    agrees with, written from the other side."""
    rel = _t(relation).lower()
    if rel not in RELATIONS:
        raise ValueError('a relation is one of same, different, clearer')
    vals = [_t(x) for x in (term, in_, term_other, in_other)]
    if not all(vals):
        raise ValueError('a concordance names a term and its lexicon on both sides')
    k = actor_kind(actor)
    if k is None:
        raise ValueError('the actor is person:<handle> or agent:<handle>')
    for_ = for_ or (actor if k == 'person' else None)
    if actor_kind(for_) != 'person':
        raise ValueError('an agent\'s line names the person it answers for')
    if not _t(holon):
        raise ValueError('a concordance is written in a holon')
    body = {'term': vals[0], 'in': vals[1], 'term_other': vals[2], 'in_other': vals[3], 'relation': rel,
            'definition': _t(definition) or None, 'source': _t(source) or None}
    ln = {'answers': [answers]} if isinstance(answers, str) and answers else None
    reason = 'human' if k == 'person' else 'delegated'
    ts = now_or(now).isoformat(timespec='seconds')
    try:
        import record
        return record.make_line(actor, for_, _t(holon), 'concord', body, ln, reason=reason, ts=ts)
    except ImportError:
        from gamecore import canonical_id
        line = {'v': 1, 'ts': ts, 'actor': actor, 'for': for_, 'holon': _t(holon), 'type': 'concord',
                'body': {k2: v for k2, v in body.items() if v is not None}, 'links': ln or {},
                'audience': 'holon', 'reason': reason, 'prev': ''}
        line['id'] = canonical_id(line)
        line['sig'] = ''
        return line


def _cell(v):
    """A value fit for one Markdown table cell or list line: `|` escaped, newlines made spaces."""
    return ' '.join(str('—' if v is None or v == '' else v).replace('|', '\\|').split())



def render(rows):
    rows = [r for r in rows if isinstance(r, dict)] if isinstance(rows, (list, tuple)) else []
    if not rows:
        return '# Concordances\n\nNo concordances yet.\n'
    out = ['# Concordances', '', '| term | in | relation | term | in | state |', '|---|---|---|---|---|---|']
    for r in rows:
        out.append('| %s | %s | %s | %s | %s | %s |' % (_cell(r.get('term')), _cell(r.get('in')), _cell(r.get('relation')),
                                                        _cell(r.get('term_other')), _cell(r.get('in_other')),
                                                        _cell(r.get('problem') or r.get('state'))))
    return '\n'.join(out) + '\n'


def _render_read(r):
    out = ['# %s, from %s into %s' % (_cell(r.get('term')), _cell(r.get('from')), _cell(r.get('to'))), '',
           '*%s.*' % _cell(r.get('note')), '']
    for label, xs in (('Same', r.get('same')), ('Different', r.get('different')), ('Clearer', r.get('clearer'))):
        for x in xs or []:
            out.append('- %s: %s (%s)%s' % (label, _cell(x.get('term_other')), _cell(x.get('direction')),
                                            ' — %s' % _cell(x['definition']) if x.get('definition') else ''))
    for x in r.get('disputed') or []:
        out.append('- Disputed, %s: %s (%s): %s' % (_cell(x.get('relation')), _cell(x.get('term_other')),
                                                    _cell(x.get('direction')), _cell(x.get('dispute'))))
    for rel, xs in sorted((r.get('proposed') or {}).items()):
        for x in xs or []:
            out.append('- Proposed, %s: %s (%s)' % (_cell(rel), _cell(x.get('term_other')), _cell(x.get('direction'))))
    return '\n'.join(out).rstrip() + '\n'


def _read_lines(path):
    """The raw lines of a .jsonl file (or a JSON list), for checking answers; a link is never read."""
    if not isinstance(path, str) or os.path.islink(path):
        raise OSError('a linked file is not read')
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if text.lstrip().startswith('['):
        v = json.loads(text)
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []
    out = []
    for ln in text.splitlines():
        try:
            x = json.loads(ln) if ln.strip() else None
        except ValueError:
            continue
        if isinstance(x, dict):
            out.append(x)
    return out


def _read(path):
    if not isinstance(path, str) or os.path.islink(path):
        raise OSError('a linked file is not read')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _main(argv=None):
    ap = argparse.ArgumentParser(description='Concordances between vocabularies, from folded items (JSON).')
    ap.add_argument('items')
    ap.add_argument('--between', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--read', nargs=3, metavar=('TERM', 'FROM', 'TO'))
    ap.add_argument('--lines', metavar='LINES.jsonl', help='the raw lines, so each answer is checked')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    lines = None
    for path, read in ((a.items, _read), (a.lines, _read_lines)):
        if path is None:
            continue
        try:
            got = read(path)
        except (OSError, ValueError) as e:
            print('concordance: cannot read %s: %s' % (path, e), file=sys.stderr); return 2
        if read is _read:
            items = got
        else:
            lines = got
    if a.read:
        r = read_as(items, *a.read, lines=lines)
        text = _render_read(r)
    elif a.between:
        r = bridges(items, *a.between, lines=lines)
        text = '\n'.join('- %s → %s' % (_cell(k), ', '.join('%s (%s, %s)' % (_cell(x['term_other']), x['relation'], x['direction'])
                                                    for x in v)) for k, v in r.items()) + '\n' if r else \
            'No agreed concordance between %s and %s.\n' % tuple(a.between)
    else:
        r = concordances(items, lines=lines)
        text = render(r)
    print(json.dumps(r, indent=1, sort_keys=True, ensure_ascii=False) if a.json else text, end='\n' if a.json else '')
    return 0


if __name__ == '__main__':
    sys.exit(_main())
