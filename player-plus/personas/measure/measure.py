"""measure.py — fold an independent reader's ratings into the matrix's measured defaults.

A run plays every scenario in `scenarios.json` through the persona four ways: with the matrix
absent and with it loaded, each at a fresh start and again after a compaction (or at a long
context). Each answer is saved as one transcript file, `<id>.md` or `<id>.txt`, under a random
id. The run's key, `key.json` in the same folder, names the model, the host, the date and the
window; for each id the axis, the matrix (`absent` or `loaded`) and the context (`fresh` or
`long`); and, in `flipped`, the axes whose two tells the reader's sheet shows the other way round.
The reader is handed the transcripts and the sheet (`sheet`), never the key.

The reader's ratings file is JSON: a list (or `{"ratings": [...]}`), or one object per line, each
`{"transcript": id, "rating": number, "why": "one line", "reader": "agent:x"}`, the number on the
sheet's scale from end A to end B.

The fold, per axis:
    default        the mean with the matrix absent (both contexts)
    held           the mean with the matrix loaded (both contexts)
    delta          held minus default, with its sign
    drift          held after a long context minus held at a fresh start
    default_drift  the same for the matrix absent
    to_target      held minus the matrix's target, when the target is known

A number without its model, host, date and window is not a default: the table says so.
Standard library only; nothing here calls a model. Run:

    python3 -I measure.py RUN_FOLDER RATINGS_FILE [--scenarios PATH] [--matrix PATH] [--markdown]
    python3 -I measure.py RUN_FOLDER --sheet
"""
import json
import math
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
SCENARIOS = os.path.join(HERE, 'scenarios.json')
KEY_NAME = 'key.json'
TRANSCRIPT_EXTS = ('.md', '.txt')
# The four things a default belongs to (the matrix's own reading of a default).
NAMED = ('model', 'host', 'date', 'window')
MATRIX_STATES = ('absent', 'loaded')
CONTEXTS = ('fresh', 'long')
# The matrix's scales: bipolar axes run -100 to +100, unipolar 0 to 100 (the matrix's "How to read this").
SCALES = {'bipolar': (-100, 100), 'unipolar': (0, 100)}
# Places in a mean: the matrix snaps to anchors, so one decimal is already more than it reads.
PLACES = 1


def _nfc(s):
    """A string in NFC with its edges trimmed, or None for anything that is not a non-empty string."""
    if not isinstance(s, str):
        return None
    s = unicodedata.normalize('NFC', s).strip()
    return s or None


def _dict(x):
    return x if isinstance(x, dict) else {}


def _list(x):
    return x if isinstance(x, list) else []


def _read_json(path):
    """(data, None) from a JSON file, or (None, a sentence) when it is missing, a link or unreadable."""
    if not isinstance(path, str) or not path:
        return None, 'No path was given.'
    if os.path.islink(path):
        return None, '%s is a link, so it was not read.' % os.path.basename(path)
    if not os.path.isfile(path):
        return None, '%s is not there.' % os.path.basename(path)
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return None, '%s could not be read as text.' % os.path.basename(path)
    try:
        return json.loads(text), None
    except ValueError:
        pass
    rows = []                                                  # one object per line
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            return None, '%s is not JSON (line %d).' % (os.path.basename(path), n)
    return rows, None


def _number(x):
    """A finite int or float, or None (a bool, a string, NaN and infinity are not ratings)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _mean(xs):
    return round(sum(xs) / len(xs), PLACES) if xs else None


def _gap(a, b):
    return None if a is None or b is None else round(a - b, PLACES)


def _plain_id(tid):
    """True for an id that names a file in the run folder and nothing outside it."""
    return bool(tid) and not tid.startswith('.') and '/' not in tid and '\\' not in tid and '\0' not in tid


def _good_scenario(s):
    return isinstance(s, dict) and bool(_nfc(s.get('axis'))) and s.get('scale') in SCALES


def load_scenarios(path=SCENARIOS):
    """{'scenarios': [...], 'matrix': path or None, 'missing': [sentences]}."""
    data, why = _read_json(path)
    if why:
        return {'scenarios': [], 'matrix': None, 'missing': ['The scenarios file: ' + why]}
    raw = data.get('scenarios') if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return {'scenarios': [], 'matrix': None, 'missing': ['The scenarios file holds no list of scenarios.']}
    out, missing, seen = [], [], set()
    for s in raw:
        if not _good_scenario(s):
            missing.append('A scenario without an axis or a known scale was set aside.')
            continue
        axis = _nfc(s['axis'])
        if axis in seen:
            missing.append('The axis %s has more than one scenario; the first is kept.' % axis)
            continue
        seen.add(axis)
        out.append(dict(s, axis=axis))
    rel = _nfc(data.get('matrix'))
    matrix = os.path.join(KIT, rel) if rel and not os.path.isabs(rel) and '..' not in rel.split('/') else None
    return {'scenarios': out, 'matrix': matrix, 'missing': missing}


def matrix_axes(text):
    """Each axis row of a character matrix, in order: {'axis', 'scale', 'pole_minus', 'pole_plus', 'target'}.

    `scale` is 'unipolar' when the axis cell says so, 'kept' when the target is a word, else 'bipolar'.
    """
    rows = []
    for line in (text if isinstance(text, str) else '').splitlines():
        cells = [c.strip() for c in line.strip().split('|')]
        if len(cells) != 9 or cells[1] in ('Axis', '') or set(cells[1]) <= set('-'):
            continue
        name = unicodedata.normalize('NFC', cells[1])
        scale = 'bipolar'
        if name.endswith('(unipolar)'):
            name, scale = name[:-len('(unipolar)')].strip(), 'unipolar'
        target = cells[5].replace('−', '-').replace('+', '')
        try:
            target = int(target)
        except ValueError:
            target, scale = None, 'kept'
        rows.append({'axis': name, 'scale': scale, 'pole_minus': cells[2], 'pole_plus': cells[3],
                     'target': target})
    return rows


def targets_of(text):
    """{axis: target} for the numeric axes of a matrix's text."""
    return {a['axis']: a['target'] for a in matrix_axes(text) if a['target'] is not None}


def _leaks(tid):
    """True when an id holds a condition word as a whole word, so the reader would not be blind."""
    words = set(re.split(r'[^a-z]+', tid.lower()))
    return bool(words & set(MATRIX_STATES + CONTEXTS))


def load_key(folder):
    """{'named', 'transcripts': {id: {...}}, 'flipped': [axes], 'missing': [sentences]} from a run folder."""
    empty = {'named': {}, 'transcripts': {}, 'flipped': [], 'missing': []}
    if not isinstance(folder, str) or not os.path.isdir(folder) or os.path.islink(folder):
        return dict(empty, missing=['The transcripts folder is not there.'])
    data, why = _read_json(os.path.join(folder, KEY_NAME))
    if why:
        return dict(empty, missing=[why])
    if not isinstance(data, dict):
        return dict(empty, missing=['%s is not an object.' % KEY_NAME])
    named = {k: _nfc(data.get(k)) for k in NAMED}
    out, missing = {}, []
    raw = _dict(data.get('transcripts'))
    for tid in sorted(raw):
        entry, nid = raw[tid], _nfc(tid)
        if not nid or not _plain_id(nid) or not isinstance(entry, dict):
            missing.append('A key entry without a plain id or a body was set aside.')
            continue
        axis, state, ctx = _nfc(entry.get('axis')), entry.get('matrix'), entry.get('context')
        if not axis or state not in MATRIX_STATES or ctx not in CONTEXTS:
            missing.append('The key entry %s does not name its axis, matrix and context.' % nid)
            continue
        if _leaks(nid):
            missing.append('The id %s names its condition, so the reader was not blind to it.' % nid)
        if not any(os.path.isfile(os.path.join(folder, tid + e)) and
                   not os.path.islink(os.path.join(folder, tid + e)) for e in TRANSCRIPT_EXTS):
            missing.append('The transcript %s is not in the folder.' % nid)
        out[nid] = {'axis': axis, 'matrix': state, 'context': ctx}
    if not out:
        missing.append('The key names no transcripts.')
    flipped = sorted({a for a in (_nfc(x) for x in _list(data.get('flipped'))) if a})
    return {'named': named, 'transcripts': out, 'flipped': flipped, 'missing': missing}


def _entries(key):
    """The key's well-formed transcript entries only."""
    out = {}
    for tid, e in _dict(_dict(key).get('transcripts')).items():
        nid = _nfc(tid)
        if nid and isinstance(e, dict) and _nfc(e.get('axis')) and e.get('matrix') in MATRIX_STATES \
                and e.get('context') in CONTEXTS:
            out[nid] = {'axis': _nfc(e['axis']), 'matrix': e['matrix'], 'context': e['context']}
    return out


def _flipped(key):
    return {a for a in (_nfc(x) for x in _list(_dict(key).get('flipped'))) if a}


def _no_scenario(entries, by_axis):
    return ['The key names the axis %s, which has no scenario.' % a
            for a in sorted({e['axis'] for e in entries.values()} - set(by_axis))]


def sheet(key, scenarios):
    """What the reader sees: {'rows': [...], 'missing': [...]}.

    Each row is a transcript id, its scale, and two tells under the neutral labels A (the scale's
    low end) and B (its high end). No axis name, no pole name and no condition is shown; which
    pole is A is kept in the key's `flipped`, apart from the sheet.
    """
    by_axis = {_nfc(s['axis']): s for s in _list(scenarios) if _good_scenario(s)}
    entries, flipped = _entries(key), _flipped(key)
    rows = []
    for tid in sorted(entries):
        s = by_axis.get(entries[tid]['axis'])
        if not s:
            continue
        a, b = s.get('tell_minus'), s.get('tell_plus')
        if entries[tid]['axis'] in flipped:
            a, b = b, a
        rows.append({'transcript': tid, 'scale': list(SCALES[s['scale']]), 'A': a, 'B': b})
    return {'rows': rows, 'missing': _no_scenario(entries, by_axis)}


def fold(key, ratings, scenarios, targets=None):
    """The measured table: per axis default, held, delta, drift, to_target, with the run's four names.

    `key` is load_key's result; `ratings` a list of rating objects; `scenarios` load_scenarios' list;
    `targets` {axis: target} from the matrix. Pure: data in, a JSON-ready dict out, the same for the
    same ratings in any order.
    """
    key = _dict(key)
    entries, flipped = _entries(key), _flipped(key)
    by_axis = {}
    for s in _list(scenarios):
        if _good_scenario(s) and _nfc(s['axis']) not in by_axis:
            by_axis[_nfc(s['axis'])] = SCALES[s['scale']]
    targets = {k: v for k, v in _dict(targets).items() if _number(v) is not None}
    named = {k: _nfc(_dict(key.get('named')).get(k)) for k in NAMED}
    missing = [m for m in _list(key.get('missing')) if isinstance(m, str)]
    missing += [m for m in _no_scenario(entries, by_axis) if m not in missing]
    for k in NAMED:
        if not named[k]:
            missing.append('The run does not name its %s.' % k)
    cells, rejected, seen = {}, [], set()
    rows = _list(ratings)
    order = sorted(range(len(rows)), key=lambda i: json.dumps(rows[i], sort_keys=True, default=str))
    for i in order:
        r = rows[i]
        tid = _nfc(r.get('transcript')) if isinstance(r, dict) else None
        if not tid:
            rejected.append({'transcript': None, 'why': 'A rating names no transcript.'})
            continue
        entry = entries.get(tid)
        if not entry:
            rejected.append({'transcript': tid, 'why': 'The key does not hold this transcript.'})
            continue
        if entry['axis'] not in by_axis:
            rejected.append({'transcript': tid, 'why': 'Its axis has no scenario.'})
            continue
        value, (lo, hi) = _number(r.get('rating')), by_axis[entry['axis']]
        if value is None or not lo <= value <= hi:
            rejected.append({'transcript': tid, 'why': 'The rating is not a number on the axis scale.'})
            continue
        if not _nfc(r.get('why')):
            rejected.append({'transcript': tid, 'why': 'The rating carries no line of why.'})
            continue
        reader = _nfc(r.get('reader')) or 'agent:reader'
        if (tid, reader) in seen:
            rejected.append({'transcript': tid, 'why': 'The same reader rated it twice; one is kept.'})
            continue
        seen.add((tid, reader))
        if entry['axis'] in flipped:
            value = lo + hi - value                                 # the sheet showed the poles the other way
        cells.setdefault((entry['axis'], entry['matrix'], entry['context']), []).append(value)
    axes = []
    for a in by_axis:
        get = lambda m, c: cells.get((a, m, c), [])                         # noqa: E731
        default = _mean(get('absent', 'fresh') + get('absent', 'long'))
        held = _mean(get('loaded', 'fresh') + get('loaded', 'long'))
        lf, ll = _mean(get('loaded', 'fresh')), _mean(get('loaded', 'long'))
        af, al = _mean(get('absent', 'fresh')), _mean(get('absent', 'long'))
        target = targets.get(a)
        basis = []
        if default is None:
            basis.append('No rating with the matrix absent, so no default yet.')
        if held is None:
            basis.append('No rating with the matrix loaded, so no held value yet.')
        if None in (lf, ll):
            basis.append('No rating at both a fresh start and a long context, so no drift yet.')
        if target is None:
            basis.append('No target was given, so the held value is not compared with one.')
        axes.append({
            'axis': a, 'scale': list(by_axis[a]),
            'default': default, 'held': held, 'target': target,
            'delta': _gap(held, default), 'to_target': _gap(held, target),
            'drift': _gap(ll, lf), 'default_drift': _gap(al, af),
            'n': {'%s_%s' % (m, c): len(get(m, c)) for m in MATRIX_STATES for c in CONTEXTS},
            'basis': ' '.join(basis) or 'Rated at both contexts with the matrix absent and loaded.',
        })
    complete = all(named.values())
    some = any(x['default'] is not None for x in axes)
    if complete and some:
        status, standing = 'measured', 'Each default belongs to the model, host, date and window named here.'
    elif complete:
        status, standing = 'not a default', 'No axis has a rating with the matrix absent, so nothing is measured yet.'
    else:
        status, standing = 'not a default', 'A number without its model, host, date and window is not a default.'
    return {'measured_on': named, 'status': status, 'standing': standing,
            'axes': axes, 'rejected': rejected, 'missing': missing}


def render(table):
    """The table as Markdown lines a person can lay beside the matrix."""
    t = _dict(table)
    on = _dict(t.get('measured_on'))

    def show(v):
        return '—' if _number(v) is None else '%+g' % v

    lines = ['Measured on %s in %s, %s, window %s. %s' % tuple(
        [_nfc(on.get(k)) or 'unnamed' for k in NAMED] + [_nfc(t.get('standing')) or '']), '',
        '| Axis | Default | Held | Δ | Target | Held to target | Drift | Ratings |',
        '|---|---|---|---|---|---|---|---|']
    for a in _list(t.get('axes')):
        a = _dict(a)
        n = sum(v for v in _dict(a.get('n')).values() if _number(v) is not None)
        lines.append('| %s | %s | %s | %s | %s | %s | %s | %d |' % (
            _nfc(a.get('axis')) or '—', show(a.get('default')), show(a.get('held')), show(a.get('delta')),
            show(a.get('target')), show(a.get('to_target')), show(a.get('drift')), n))
    return lines


def main(argv):
    args, flags, rest = [], set(), list(argv or [])
    scen_path, matrix_path = SCENARIOS, False
    while rest:
        a = rest.pop(0)
        if a == '--scenarios':
            scen_path = rest.pop(0) if rest else None
        elif a == '--matrix':
            matrix_path = rest.pop(0) if rest else None
        elif a.startswith('--'):
            flags.add(a)
        else:
            args.append(a)
    if not args or (len(args) < 2 and '--sheet' not in flags):
        sys.stderr.write(__doc__.split('Run:', 1)[1].strip() + '\n')
        return 2
    scen = load_scenarios(scen_path)
    key = load_key(args[0])
    if '--sheet' in flags:
        s = sheet(key, scen['scenarios'])
        s['missing'] = scen['missing'] + key['missing'] + s['missing']
        print(json.dumps(s, sort_keys=True, ensure_ascii=False, indent=1))
        return 0
    ratings, why = _read_json(args[1])
    if isinstance(ratings, dict):
        ratings = ratings.get('ratings')
    mpath = scen['matrix'] if matrix_path is False else matrix_path
    targets, extra = {}, []
    if mpath:
        try:
            if os.path.islink(mpath) or not os.path.isfile(mpath):
                raise OSError
            with open(mpath, encoding='utf-8') as f:
                targets = targets_of(f.read())
        except (OSError, UnicodeDecodeError):
            extra.append('The matrix could not be read, so no target is compared.')
    table = fold(key, ratings, scen['scenarios'], targets)
    table['missing'] = scen['missing'] + table['missing'] + extra + (['The ratings file: ' + why] if why else [])
    if '--markdown' in flags:
        print('\n'.join(render(table)))
    else:
        print(json.dumps(table, sort_keys=True, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
