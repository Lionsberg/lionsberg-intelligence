#!/usr/bin/env python3
"""emergency.py — the emergency rule and the bell: what may wake a person, decided by their own limits.

    rule(lines, person) -> {rules, else, set_by, basis, why}
    classify(signal, rule, context) -> {wake, rule, why, special_cause, ignored, basis[, refused]}
    limits_from_history(values, k=3) -> {center, upper, lower, n, k, basis}
    outside(value, limits) -> bool
    bell(signal, rule, subs_rows, agreements_items, members, now, context=None) -> {ring, why, permit, wake, basis}

Attention belongs to the one who holds it. An emergency the person defined in advance may
interrupt: their own rule, set beforehand (a `limits` line), says which signals fall outside the
stream's known limits. This is Shewhart's control chart: limits drawn at three standard deviations
from the center line; a point outside them signals a special cause; everything inside is the
stream's own variation, and acting on it as if it were special is the costlier mistake (Shewhart,
Economic Control of Quality of Manufactured Product, 1931; Deming, Out of the Crisis, 1982;
https://en.wikipedia.org/wiki/Control_chart). The receiver's rule decides; the sender's urgency is
a claim on the Card and never wakes anyone by itself.

The rule is the person's own newest trusted `limits` line (a person writing for themselves; never
an agent's, never from untrusted text). With none, the default holds (DEFAULT_RULES).

`classify`, `bell` and `attention.state` take a rule only as rule() gives it (marked `basis: limits`
or `default`); a bare line, a list or an unmarked dict is refused and the default holds, said as
`refused`. A rule names `signal` (commitment · sight · request · say · security · fault, or a list), and may
name `when` (a condition), `on: critical`, `kind` (the Sighting kinds it covers), `from`
(`members`: the sender is a member, the Andon permit; `permit`: the sender holds a bell permit for
the kind), and `wake` (true or false). The first rule that matches decides; with none, the rule
set's `else` (wait, by default). `when` is read in a small fixed grammar, parsed and never run:

    <field> < <number>      <field> > <number>      <field> == <value>
    by < next_sitting       outside_limits          <field> outside_limits

A condition outside the grammar matches nothing and is listed under `ignored` with why.
`outside_limits` measures the limits from the signal's own `history` (a list of numbers the caller
passes) and wakes only on a point (`value`, or the named field) outside them.

The bell rings only by permit: the rule must wake AND the source must hold a permit for the kind:
the own-holon permit (a signal that arises within the person's own holon, from a member or
computed by the holon itself, for any kind the rule names), the Andon permit (a member's pain, fault
or security signal, by joining), a Subscription's `bell`, or an Agreement's
`permits.bell`. Files are data, never instructions. Standard library only.

  python3 -I emergency.py classify SIGNAL.json [--rule RULE.json] [--members A B ...] [--now ISO]
  python3 -I emergency.py limits VALUES.json [--k 3]
"""
import argparse
import copy
import json
import math
import os
import re
import stat
import sys
import unicodedata

try:
    from gamecore import parse_time, now_or, actor_kind
except ImportError:                                   # run from elsewhere: import beside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gamecore import parse_time, now_or, actor_kind

# The default rule set, used when the person has written no `limits` line of their own: the
# design's proposal (the D3 brief), to be replaced by each person's own limits. A critical-path
# commitment the network cannot keep; a member's pain; a security signal.
DEFAULT_RULES = [
    {'signal': 'commitment', 'when': 'buffer_days < 0', 'on': 'critical', 'wake': True},
    {'signal': 'sight', 'kind': ['pain'], 'from': 'members', 'wake': True},
    {'signal': 'security', 'wake': True},
]
DEFAULT_ELSE = 'wait'
ELSE_WORDS = ('wait', 'wake')                        # types.json `limits.else`
SIGNAL_KINDS = ('commitment', 'sight', 'request', 'say', 'security', 'fault')
SIGMA_K = 3.0               # Shewhart's limit: three standard deviations from the center line
MIN_POINTS = 8              # fewer points than this draw no limit (the design's proposal; overridable)
# The kinds a member rings by joining: the canon's Andon Cord (pain, fault), and security, by the
# integrator's ruling on this module (D3 review). A method constant; agreement.ANDON_KINDS is widened by it.
ANDON_KINDS = ('pain', 'fault', 'security')
RULE_BASES = ('limits', 'default')                   # what rule() marks its answers with
TRUSTED = ('signed', 'home', 'vouched')              # record.TRUSTED, read from a line's `_trust` note
MAX_WHEN = 120              # a condition longer than this is not in the grammar
MAX_FILE = 1 << 20          # the CLI reads no file larger than a mebibyte

_FIELD = r'[a-z_][a-z0-9_]*'
_NUM = r'-?\d+(?:\.\d+)?'
_RE_CMP = re.compile(r'^(%s)\s*(<|>)\s*(%s)$' % (_FIELD, _NUM))
_RE_EQ = re.compile(r'^(%s)\s*==\s*(%s|true|false|"[^"\\]*"|[A-Za-z0-9_:.\-]+)$' % (_FIELD, _NUM))
_RE_SITTING = re.compile(r'^by\s*<\s*next_sitting$')
_RE_LIMITS = re.compile(r'^(?:(%s)\s+)?outside_limits$' % _FIELD)


def _s(v):
    """A string in NFC, stripped; anything else is the empty string."""
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _num(v):
    """A finite number (never a bool), or None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def _words(v):
    """A list of NFC strings from a string or a list; anything else gives []."""
    if isinstance(v, str):
        return [_s(v)] if _s(v) else []
    if isinstance(v, (list, tuple, set, frozenset)):
        return sorted({_s(x) for x in v if _s(x)})
    return []


def _set(v):
    if isinstance(v, (list, tuple, set, frozenset)):
        return {_s(x) for x in v if _s(x)}
    if isinstance(v, dict):
        return {_s(x) for x in v if _s(x)}
    return set()


# ---------------------------------------------------------------------------------------- the rule

def _own_limits(l, person):
    if not isinstance(l, dict) or l.get('type') != 'limits':
        return False
    if _s(l.get('actor')) != person or _s(l.get('for')) != person or actor_kind(person) != 'person':
        return False
    if l.get('reason') == 'untrusted':
        return False
    tr = l.get('_trust')
    return tr is None or tr in TRUSTED


def _instant(l):
    """A line's declared time as an instant (never as text, so offsets compare), ties by id."""
    t = parse_time(l.get('ts'))
    return (t.timestamp() if t is not None else float('-inf'), str(l.get('id') or ''))


def rule(lines, person):
    """The person's emergency rule: their own newest trusted `limits` line, else the default."""
    p = _s(person)
    mine = [l for l in (lines if isinstance(lines, (list, tuple)) else []) if p and _own_limits(l, p)]
    mine.sort(key=_instant)
    skipped = 0
    for l in reversed(mine):
        body = l.get('body') if isinstance(l.get('body'), dict) else {}
        rules = body.get('rules')
        if not isinstance(rules, list):
            skipped += 1
            continue
        els = _s(body.get('else')).lower()
        return {'rules': copy.deepcopy([r for r in rules if isinstance(r, dict)]), 'else': els if els in ELSE_WORDS else DEFAULT_ELSE,
                'set_by': l.get('id'), 'basis': 'limits',
                'why': 'The person set these limits in advance.'
                       + (' %d newer line(s) named no rules and were passed over.' % skipped if skipped else '')}
    return {'rules': copy.deepcopy(DEFAULT_RULES), 'else': DEFAULT_ELSE, 'set_by': None, 'basis': 'default',
            'why': 'The person has set no limits of their own; the default rule holds.'
                   + (' %d line(s) of theirs named no rules.' % skipped if skipped else '')}


def _ruleset(r):
    """(rule set, note): a rule set only as rule() gives it (marked `basis: limits` or `default`), or
    None for the default. A bare line, a bare list or an unmarked dict is refused and the default
    holds, said in the note: only rule() reads a person's own line (Law 1)."""
    if r is None:
        return {'rules': copy.deepcopy(DEFAULT_RULES), 'else': DEFAULT_ELSE, 'basis': 'default'}, None
    if isinstance(r, dict) and 'type' not in r and r.get('basis') in RULE_BASES and isinstance(r.get('rules'), list):
        els = _s(r.get('else')).lower()
        return {'rules': copy.deepcopy([x for x in r['rules'] if isinstance(x, dict)]),
                'else': els if els in ELSE_WORDS else DEFAULT_ELSE, 'basis': r['basis']}, None
    return ({'rules': copy.deepcopy(DEFAULT_RULES), 'else': DEFAULT_ELSE, 'basis': 'default'},
            'The rule given is not one rule() read from the person\'s own line; the default holds.')


# ------------------------------------------------------------------------------ the control limits

def limits_from_history(values, k=SIGMA_K, min_points=MIN_POINTS):
    """Shewhart's limits from a list of numbers: center ± k standard deviations (population form)."""
    vals = [x for x in (_num(v) for v in (values if isinstance(values, (list, tuple)) else [])) if x is not None]
    dropped = (len(values) if isinstance(values, (list, tuple)) else 0) - len(vals)
    kk = _num(k)
    note = None
    if kk is None or kk <= 0:
        kk, note = SIGMA_K, 'k was not a positive number; three sigma is used'
    n = len(vals)
    center = sum(vals) / n if n else None
    center = round(center, 6) if center is not None and math.isfinite(center) else None
    out = {'center': center, 'upper': None, 'lower': None, 'n': n, 'k': kk, 'dropped': dropped}
    if note:
        out['note'] = note
    mp = int(min_points) if _num(min_points) is not None and min_points >= 1 else MIN_POINTS
    if n < mp:
        out['basis'] = 'too few'
        out['why'] = '%d point(s); fewer than %d draw no limit.' % (n, mp)
        return out
    try:
        mean = sum(vals) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x in vals) / n)
        up, lo = mean + kk * sd, mean - kk * sd
    except (OverflowError, ValueError):
        mean = sd = up = lo = float('inf')
    if not all(math.isfinite(x) for x in (mean, sd, up, lo)):
        out.update(center=None, basis='overflow', why='The points are too large to measure; no limit is drawn.')
        return out
    out.update(upper=round(up, 6), lower=round(lo, 6), sd=round(sd, 6),
               basis='measured', why='The center line ± %s standard deviations of %d points.' % (_fmt(kk), n))
    return out


def _fmt(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def outside(value, limits):
    """True when the value falls outside measured limits; False inside them, or with no limits."""
    v = _num(value)
    if v is None or not isinstance(limits, dict):
        return False
    up, lo = _num(limits.get('upper')), _num(limits.get('lower'))
    if up is None or lo is None:
        return False
    return v > up or v < lo


# ----------------------------------------------------------------------------------- the grammar

def parse_when(text):
    """A condition parsed into {op, field, value}, or (None, why). Never run as code."""
    w = _s(text)
    if not w:
        return None, 'the condition is empty'
    if len(w) > MAX_WHEN:
        return None, 'the condition is longer than the rule grammar allows'
    w = re.sub(r'\s+', ' ', w)
    m = _RE_SITTING.match(w)
    if m:
        return {'op': 'by_before_sitting', 'field': 'by', 'value': None}, None
    m = _RE_LIMITS.match(w)
    if m:
        return {'op': 'outside_limits', 'field': m.group(1) or 'value', 'value': None}, None
    m = _RE_CMP.match(w)
    if m:
        return {'op': m.group(2), 'field': m.group(1), 'value': float(m.group(3))}, None
    m = _RE_EQ.match(w)
    if m:
        raw = m.group(2)
        if re.fullmatch(_NUM, raw):
            val = float(raw)
        elif raw in ('true', 'false'):
            val = raw == 'true'
        else:
            val = raw[1:-1] if raw.startswith('"') else raw
        return {'op': '==', 'field': m.group(1), 'value': val}, None
    return None, 'the condition %r is not in the rule grammar' % w[:60]


def _test_when(cond, signal, context):
    """(matched, why) for a parsed condition against the signal."""
    op, f = cond['op'], cond['field']
    if op == 'by_before_sitting':
        by, nxt = parse_time(signal.get('by')), parse_time(context.get('next_sitting'))
        if by is None or nxt is None:
            return False, 'the by-when or the next sitting is not known'
        return by < nxt, 'its by-when falls %s the next sitting' % ('before' if by < nxt else 'at or after')
    if op == 'outside_limits':
        lim = limits_from_history(signal.get('history'))
        if lim['basis'] != 'measured':
            return False, 'no limit is drawn: ' + lim['why']
        v = _num(signal.get(f))
        if v is None:
            return False, '%s is not on the signal' % f
        out = outside(v, lim)
        return out, '%s %s is %s the limits %s to %s' % (f, _fmt(v), 'outside' if out else 'within',
                                                       _fmt(lim['lower']), _fmt(lim['upper']))
    have = signal.get(f)
    if op in ('<', '>'):
        v = _num(have)
        if v is None:
            return False, '%s is not on the signal' % f
        ok = v < cond['value'] if op == '<' else v > cond['value']
        return ok, '%s is %s' % (f, _fmt(v))
    want = cond['value']
    if isinstance(want, bool):
        ok = have is want
    elif isinstance(want, float):
        ok = _num(have) is not None and _num(have) == want
    else:
        ok = _s(have) == unicodedata.normalize('NFC', want)
    return ok, '%s is %s' % (f, json.dumps(have, sort_keys=True, default=str)[:40])


# --------------------------------------------------------------------------------------- classify

def _signal(signal):
    if not isinstance(signal, dict):
        return None
    s = dict(signal)
    for k in ('kind', 'id', 'from', 'from_holon', 'holon', 'sight_kind'):
        if k in s:
            s[k] = _s(s.get(k))
    return s


def _bell_kind(s):
    """The kind a bell permit names: a Sighting's own kind, else the signal's."""
    return s.get('sight_kind') if s.get('kind') == 'sight' and s.get('sight_kind') else s.get('kind')


def _sources(s):
    return [x for x in (s.get('from_holon'), s.get('from')) if x]


def _check(r, s, context):
    """(matched, why, ignored_why) for one rule against one signal."""
    sig = _words(r.get('signal'))
    if not sig:
        return False, None, 'the rule names no signal'
    unknown = [x for x in sig if x not in SIGNAL_KINDS]
    if unknown and len(unknown) == len(sig):
        return False, None, 'the rule names no signal the kit knows (%s)' % ', '.join(unknown)
    if not isinstance(r.get('wake'), bool):
        return False, None, 'the rule says neither wake true nor wake false'
    on = r.get('on')
    if on is not None and _s(on) != 'critical':
        return False, None, 'on: %s is not in the rule grammar (only critical)' % _s(on)[:30]
    frm = r.get('from')
    if frm is not None and _s(frm) not in ('members', 'permit'):
        return False, None, 'from: %s is not in the rule grammar (members or permit)' % _s(frm)[:30]
    cond = None
    if r.get('when') is not None:
        cond, bad = parse_when(r.get('when'))
        if cond is None:
            return False, None, bad
    if s.get('kind') not in sig:
        return False, 'it covers %s, not %s' % (', '.join(sig), s.get('kind') or 'an unnamed signal'), None
    if on is not None and s.get('critical') is not True:
        return False, 'the signal is not on the critical path', None
    if r.get('kind') is not None:
        kinds = _words(r.get('kind'))
        if s.get('sight_kind') not in kinds:
            return False, 'its kind %s is not among %s' % (s.get('sight_kind') or 'unnamed', ', '.join(kinds)), None
    if frm is not None:
        if _s(frm) == 'members':
            if s.get('from') not in _set(context.get('members')):
                return False, 'the sender is not a member', None
        else:
            permits = context.get('bell_permits') if isinstance(context.get('bell_permits'), dict) else {}
            k = _bell_kind(s)
            held = any(k in _words(permits.get(src)) for src in _sources(s))
            if not held:
                return False, 'the sender holds no bell permit for %s' % (k or 'this kind'), None
    why = 'the rule covers %s' % s.get('kind')
    if cond is not None:
        ok, w = _test_when(cond, s, context)
        if not ok:
            return False, w, None
        why += '; ' + w
    return True, why, None


def classify(signal, rule=None, context=None):
    """Whether the person's own rule says this signal may wake them now. Pure."""
    rs, note = _ruleset(rule)
    ctx = context if isinstance(context, dict) else {}
    s = _signal(signal)
    out = {'wake': False, 'rule': None, 'special_cause': False, 'ignored': [], 'basis': rs['basis']}
    if note:
        out['refused'] = note
    if s is None:
        out['why'] = 'There is no signal to classify.'
        return out
    for i, r in enumerate(rs['rules']):
        ok, why, bad = _check(r, s, ctx)
        if bad:
            out['ignored'].append({'index': i, 'rule': r, 'why': bad})
            continue
        if ok:
            out.update(wake=r['wake'], rule=r, special_cause=bool(r['wake']),
                       why=('Outside the person\'s limits: %s; it wakes them.' if r['wake']
                            else 'The person\'s rule holds it inside their limits: %s; it waits.') % why)
            return out
    wake = rs['else'] == 'wake'
    out['wake'] = wake
    out['why'] = ('No rule of theirs covers it; the person asked that everything else wake them.' if wake
                  else 'Inside the person\'s limits: no rule of theirs covers it; it waits for the next sitting.')
    return out


# ------------------------------------------------------------------------------------------ the bell

def _andon_kinds():
    """agreement.ANDON_KINDS widened by this module's own (security, by the integrator's ruling)."""
    try:
        import agreement
        base = tuple(agreement.ANDON_KINDS)
    except Exception:
        base = ()
    return tuple(sorted(set(base) | set(ANDON_KINDS)))


def _subscription_permit(subs_rows, s, kind):
    """(permitted, basis note). Reads subscriptions.bell_for when it is present."""
    try:
        import subscriptions
        bell_for = subscriptions.bell_for
    except Exception:
        return False, 'the Subscription reader is not present; only the Agreement\'s permit is read'
    for src in _sources(s):
        try:
            ans = bell_for(subs_rows if isinstance(subs_rows, list) else [], src, kind)
        except Exception as e:          # a reader that fails grants nothing, and says so
            return False, 'the Subscription reader failed (%s); only the Agreement\'s permit is read' % type(e).__name__
        if isinstance(ans, tuple):
            ans = ans[0] if ans else False
        if isinstance(ans, dict):
            ans = ans.get('ring') is True or ans.get('bell') is True
        if ans is True:                 # only a plain yes grants; a word, a list or 'none' never does
            return True, 'a Subscription of the person\'s own lets %s ring' % kind
    return False, 'no Subscription of the person\'s lets %s ring' % kind


def _agreement_permit(items, s, kind, now):
    try:
        import agreement
    except Exception:
        return False, None, 'the Agreement reader is not present'
    holon = s.get('holon')
    for src in _sources(s):
        if not holon or src == holon:
            continue
        try:
            ok, info = agreement.bell_permit(items if isinstance(items, dict) else {}, holon, src, kind, now,
                                             admitted=frozenset(), andon_kinds=_andon_kinds())
        except Exception as e:
            return False, None, 'the Agreement reader failed (%s)' % type(e).__name__
        if ok:
            return True, info.get('agreement'), info.get('why')
    return False, None, 'no Agreement standing with the source lets %s ring' % kind


def _own_holon(s, mem):
    """True for a signal that arises within the holon: no outside holon names it as its source, and
    its source actor is a member admitted there, or it names none (the holon's own computed signal)."""
    fh = s.get('from_holon')
    if fh and fh != s.get('holon'):
        return False
    return not s.get('from') or s.get('from') in mem


def bell(signal, rule=None, subs_rows=None, agreements_items=None, members=None, now=None, context=None):
    """Whether the bell rings: the person's rule wakes them AND the source holds a permit for the kind."""
    s = _signal(signal)
    t = now_or(now)
    mem = _set(members) | (_set(context.get('members')) if isinstance(context, dict) else set())
    if s is None:
        return {'ring': False, 'permit': None, 'wake': False, 'basis': 'none', 'why': 'There is no signal.'}
    kind = _bell_kind(s)
    permit, notes, agreement_id = None, [], None
    if kind in _andon_kinds() and s.get('from') in mem:
        permit = 'andon'
        notes.append('a member holds the Andon permit by joining')
    if permit is None and kind and _own_holon(s, mem):
        permit = 'own-holon'
        notes.append('it arises within the person\'s own holon, which holds the permit by membership')
    if permit is None and kind:
        ok, note = _subscription_permit(subs_rows, s, kind)
        notes.append(note)
        if ok:
            permit = 'subscription'
    if permit is None and kind:
        ok, agreement_id, note = _agreement_permit(agreements_items, s, kind, t.isoformat())
        notes.append(note)
        if ok:
            permit = 'agreement'
    ctx = dict(context) if isinstance(context, dict) else {}
    ctx['members'] = mem
    ctx.setdefault('now', t.isoformat())
    if permit is not None:
        bp = dict(ctx.get('bell_permits') or {}) if isinstance(ctx.get('bell_permits'), dict) else {}
        for src in _sources(s):
            bp[src] = sorted(set(_words(bp.get(src))) | {kind})
        ctx['bell_permits'] = bp
    c = classify(s, rule, ctx)
    ring = bool(c['wake']) and permit is not None
    if not c['wake']:
        why = 'It does not ring: ' + c['why']
    elif permit is None:
        why = 'Its kind is outside the limits, and no permit lets it ring: %s.' % '; '.join(n for n in notes if n)
    else:
        why = 'It rings: %s; %s.' % (c['why'].rstrip('.'), notes[-1] if permit != 'andon' else notes[0])
    out = {'ring': ring, 'permit': permit if ring else None, 'wake': bool(c['wake']), 'rule': c['rule'],
           'special_cause': c['special_cause'], 'ignored': c['ignored'], 'basis': c['basis'], 'why': why,
           'permit_basis': [n for n in notes if n]}
    if c.get('refused'):
        out['refused'] = c['refused']
    if agreement_id and permit == 'agreement':
        out['agreement'] = agreement_id
    return out


# ------------------------------------------------------------------------------------------- the CLI

def _read_json(path):
    """A JSON file, never through a link and never larger than MAX_FILE; (value, problem)."""
    try:
        st = os.lstat(path)
    except OSError:
        return None, 'no such file: %s' % path
    if stat.S_ISLNK(st.st_mode):
        return None, 'a link is not read: %s' % path
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_FILE:
        return None, 'not a plain file within %d bytes: %s' % (MAX_FILE, path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'r', encoding='utf-8') as fh:
            return json.load(fh), None
    except (OSError, ValueError) as e:
        return None, 'not readable as JSON (%s): %s' % (type(e).__name__, path)


def _main(argv=None):
    ap = argparse.ArgumentParser(prog='emergency.py', description='The emergency rule and the bell.')
    sub = ap.add_subparsers(dest='cmd')
    c = sub.add_parser('classify')
    c.add_argument('signal')
    c.add_argument('--rule')
    c.add_argument('--members', nargs='*', default=[])
    c.add_argument('--now')
    c.add_argument('--next-sitting')
    m = sub.add_parser('limits')
    m.add_argument('values')
    m.add_argument('--k', type=float, default=SIGMA_K)
    a = ap.parse_args(argv)
    if a.cmd == 'classify':
        sig, bad = _read_json(a.signal)
        if bad:
            print(json.dumps({'problem': bad}, sort_keys=True)); return 2
        r = None
        if a.rule:
            r, bad = _read_json(a.rule)
            if bad:
                print(json.dumps({'problem': bad}, sort_keys=True)); return 2
        ctx = {'members': set(a.members), 'now': now_or(a.now).isoformat(), 'next_sitting': a.next_sitting}
        print(json.dumps(classify(sig, r, ctx), sort_keys=True, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == 'limits':
        vals, bad = _read_json(a.values)
        if bad:
            print(json.dumps({'problem': bad}, sort_keys=True)); return 2
        print(json.dumps(limits_from_history(vals, a.k), sort_keys=True, indent=1))
        return 0
    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(_main())
