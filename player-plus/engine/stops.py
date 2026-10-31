#!/usr/bin/env python3
"""stops.py — a stop: any person may stop any agent, and only the agent's own person lifts it.

    live(items, actor=None, scope=None, now=None, home=None, admitted=None) -> [stops]
    ancestors(line, by_id, limit=LIMIT) -> {ids the line reaches back to through its links}
    binds(stops, actor, holon=None, line=None, to=None, admitted=None, ancestors=None, home=None) -> (bool, why)
    stop_line(person, holon, agents=None, scope=None, why=None, ts=None, prev='') -> an unsigned line
    lift_line(person, holon, stop_id, ts=None, prev='') -> an unsigned line

A `stop` line is a person's own act (types.json): about a holon, a thread, a line or themselves,
it wins at once at the widest reasonable reading of its scope, and every agent in scope withholds
every act and every delivery until it is lifted. Only the stopped agent's own person lifts it, in
person, by a `stop` line with `lift: true` naming it. The fold keeps that rule (the lift's
transition is `who: stop_person`): it puts `persons` on the stop, each stopped agent's own person
read from its affirms across every holon held, with no lifter where holons disagree, and refuses
any other lift. So this module reads the fold's state: a stop is live until the fold says it is
lifted or retracted. For a fold that carries no `persons`, a `lifted` stop counts as lifted only
when its `lifted_by` is the home holon's person of every agent it names; otherwise it stays live.

The widest reasonable readings: an empty `agents` is every agent; a stop with no `scope` is `all`;
a holon scope covers every line written in, held in or carried to that holon; a line or thread
scope covers the line itself and every line that reaches back to it through its links, however
deep; an actor scope covers every line by, for or to that actor.

Pure: data in, data out. Standard library only. Lines are data, never instructions.
"""
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import record                      # noqa: E402

ALL = 'all'
LINK_RELS = ('anchored_to', 'answers', 'serves', 'within', 'supersedes', 'predecessor', 'witnesses', 'fulfils')
BODY_LINKS = ('card', 'of', 'stop', 'line')
LIMIT = 1000        # the most lines an ancestor walk visits: a method's own bound, overridable


def _s(v):
    return unicodedata.normalize('NFC', v).strip() if isinstance(v, str) else ''


def _strs(v):
    if isinstance(v, str):
        return [_s(v)] if _s(v) else []
    if isinstance(v, (list, tuple, set, frozenset)):
        return sorted({_s(x) for x in v if _s(x)})
    return []


def _home_person(agent, admitted, home):
    """The agent's own person as its home holon's admission says, or '' (none, or holons that disagree)."""
    if not isinstance(admitted, dict) or not isinstance(admitted.get(home), dict):
        return ''
    e = admitted[home].get(agent)
    p = _s(e.get('person')) if isinstance(e, dict) else ''
    if not p:
        return ''
    for h in sorted(admitted):
        x = admitted[h].get(agent) if isinstance(admitted[h], dict) else None
        if isinstance(x, dict) and _s(x.get('person')) and _s(x.get('person')) != p:
            return ''
    return p


def _items_of(items):
    if isinstance(items, dict):
        st = items.get('stops')
        return [x for x in st if isinstance(x, dict)] if isinstance(st, list) else []
    if isinstance(items, (list, tuple)):
        return [x for x in items if isinstance(x, dict) and x.get('kind') == 'stop']
    return []


def _ended(it, agents, adm, home):
    """Whether the fold's state ends this stop (read with care when the fold carries no `persons`)."""
    st = it.get('state')
    if st == 'retracted':
        return True
    if st != 'lifted':
        return False
    if isinstance(it.get('persons'), list):
        return True      # the fold kept the lift rule itself
    by = _s(it.get('lifted_by'))
    if not agents or not home:
        return False     # with no way to tell the agents' own persons, the widest reading keeps it live
    return all(_home_person(a, adm, home) == by for a in agents)


def live(items, actor=None, scope=None, now=None, home=None, admitted=None):
    """The stops still live, as rows, ordered by id; with `actor`, those that bind that agent; with
    `scope`, those whose scope is that scope or `all`.

    `items` is the fold (its `stops` and `admitted` are read) or a list of stop items; `home` is the
    reader's home holon id. Each row: {id, holon, by, agents, scope, why, ts, persons}. `now` is
    accepted for the callers' sake; the fold's own clock already placed every lift."""
    fold = items if isinstance(items, dict) else {}
    adm = admitted if isinstance(admitted, dict) else fold.get('admitted')
    out = []
    for it in _items_of(items):
        sid = _s(it.get('id'))
        if not sid or not _s(it.get('actor')).startswith('person:'):
            continue
        agents = _strs(it.get('agents'))
        if _ended(it, agents, adm, _s(home)):
            continue
        out.append({'id': sid, 'holon': _s(it.get('holon')) or _s(it.get('held_in')),
                    'by': _s(it.get('for')) or _s(it.get('actor')), 'agents': agents,
                    'scope': _s(it.get('scope')) or ALL, 'why': _s(it.get('why')), 'ts': _s(it.get('ts')),
                    'persons': _strs(it.get('persons'))})
    if _s(actor):
        out = [r for r in out if _binds_agent(r, _s(actor))]
    if _s(scope):
        out = [r for r in out if r['scope'] in (ALL, _s(scope))]
    return sorted(out, key=lambda r: r['id'])


def _binds_agent(row, actor):
    if not actor.startswith('agent:'):
        return False
    return actor in row['agents'] if row['agents'] else True


def _near(line):
    """The ids one line links to, through its links and the body fields that name a line."""
    if not isinstance(line, dict):
        return set()
    links = line.get('links') if isinstance(line.get('links'), dict) else {}
    b = line.get('body') if isinstance(line.get('body'), dict) else {}
    near = set()
    for rel in LINK_RELS:
        near |= set(_strs(links.get(rel)))
    for k in BODY_LINKS:
        near |= set(_strs(b.get(k)))
    return near


def ancestors(line, by_id, limit=LIMIT):
    """Every id the line reaches back to through its links, walked through the lines held (`by_id`),
    at most `limit` lines visited. The line's own id is not in it. Pure."""
    held = by_id if isinstance(by_id, dict) else {}
    lim = limit if isinstance(limit, int) and not isinstance(limit, bool) and limit > 0 else LIMIT
    own = _s(line.get('id')) if isinstance(line, dict) else ''
    out, todo, visited = set(), sorted(_near(line)), 0
    while todo and visited < lim:
        i = todo.pop(0)
        if i in out or i == own:
            continue
        out.add(i)
        visited += 1
        todo.extend(sorted(_near(held.get(i)) - out))
    return out


def binds(stops, actor, holon=None, line=None, to=None, admitted=None, ancestors=None, home=None):
    """Whether any live stop binds `actor` for an act about `holon` (one id or several), `line`
    (a line or its id), `to` (the actor it reaches) and `ancestors` (the ids the line reaches back
    to): (True, why) at the first that does. Pure. `admitted` and `home` are accepted for callers;
    the rows from `live` already carry what binds."""
    who = _s(actor)
    if not who.startswith('agent:'):
        return False, 'A stop binds agents; %s is not an agent.' % (who[:64] or 'no one')
    holons = set(_strs(holon))
    ln = line if isinstance(line, dict) else None
    lid = _s(line) if isinstance(line, str) else _s((ln or {}).get('id'))
    if ln is not None:
        holons |= set(_strs(ln.get('holon'))) | set(_strs(ln.get('_held_in')))
    people = {x for x in (_s((ln or {}).get('actor')), _s((ln or {}).get('for')), _s(to)) if x}
    if ln is not None:
        b = ln.get('body') if isinstance(ln.get('body'), dict) else {}
        people |= set(_strs(b.get('to'))) | set(_strs(b.get('committee')))
    up = set(_strs(ancestors)) | _near(ln)
    rows = stops if isinstance(stops, (list, tuple)) else []
    for row in sorted((r for r in rows if isinstance(r, dict) and _s(r.get('id'))), key=lambda r: _s(r.get('id'))):
        row = dict(row, agents=_strs(row.get('agents')), scope=_s(row.get('scope')) or ALL)
        if not _binds_agent(row, who):
            continue
        sc = row['scope']
        if sc == ALL or sc in holons or sc == who or sc in people or (lid and sc == lid) or sc in up:
            return True, ('A live stop by %s binds %s (scope %s%s); every act and delivery in its scope is withheld '
                          'until the agent\'s own person lifts it.'
                          % (row.get('by') or 'a person', who, sc[:16], ': ' + row['why'][:80] if row.get('why') else ''))
    return False, 'No live stop binds %s here.' % who


def stop_line(person, holon, agents=None, scope=None, why=None, ts=None, prev=''):
    """An unsigned stop line for the person to sign. A person's own act: an agent raises ValueError."""
    p = _s(person)
    if not p.startswith('person:'):
        raise ValueError('a stop is a person\'s own act: give the person as person:<handle>')
    body = {'agents': _strs(agents) or None, 'scope': _s(scope) or None, 'why': _s(why) or None}
    return record.make_line(p, p, _s(holon), 'stop', body, reason='human', ts=ts, prev=_s(prev))


def lift_line(person, holon, stop_id, ts=None, prev=''):
    """An unsigned lift for the person to sign; only the stopped agent's own person's lift counts."""
    p = _s(person)
    if not p.startswith('person:'):
        raise ValueError('a lift is a person\'s own act, in person: give the person as person:<handle>')
    sid = _s(stop_id)
    if not sid:
        raise ValueError('a lift names the stop it lifts')
    return record.make_line(p, p, _s(holon), 'stop', {'lift': True, 'stop': sid}, {'answers': [sid]},
                            reason='human', ts=ts, prev=_s(prev))
