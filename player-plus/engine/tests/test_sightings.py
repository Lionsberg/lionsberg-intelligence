"""test_sightings.py — the living map: the Sighting's nine kinds, its lifecycle, the map, the scoreboard.

Hand-built items in the shape record.py's fold returns (a dict of lists; a sighting's own kind as
`body_kind`), with raw lines beside them, and one pass over the real fold of signed lines.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_sightings.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import sightings as S  # noqa: E402

H, H2 = 'holon-cell', 'holon-other'
P, K, T, AG = 'person:player', 'person:keeper', 'person:third', 'agent:aide'
NOW = '2026-10-24T13:00:00-07:00'


def sg(i, kind, text, actor=P, where='the north gate', ts='2026-10-22T09:00:00-07:00', state='seen', for_=None, **kw):
    d = {'id': i, 'kind': 'sighting', 'body_kind': kind, 'holon': H, 'text': text, 'where': where, 'actor': actor,
         'for': for_ or actor, 'ts': ts, 'state': state, 'links': {}}
    d.update(kw)
    return d


def L(i, typ, actor, body=None, links=None, ts='2026-10-22T10:00:00-07:00', reason=None, for_=None, holon=H):
    return {'id': i, 'type': typ, 'actor': actor, 'for': for_ or (actor if actor.startswith('person:') else P),
            'holon': holon, 'ts': ts, 'body': body or {}, 'links': links or {},
            'reason': reason or ('human' if actor.startswith('person:') else 'delegated')}


def base():
    return {'sightings': [], 'cards': [], 'commitments': [], 'threads': [],
            'delegations': [{'id': 'g1', 'kind': 'delegation', 'holon': H, 'state': 'live', 'to': AG, 'actor': P,
                             'for': P, 'scope': ['say', 'sight', 'claim'], 'holons': [H], 'until': '2026-12-31'}]}


class ResightingAddsWeight(unittest.TestCase):
    def test_another_player_makes_it_still_there(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The bridge rail is loose'),
                            sg('s2', 'defect', 'Still loose', actor=K, links={'anchored_to': ['s1']},
                               ts='2026-10-22T11:00:00-07:00')]
        lf = S.lifecycle(its)
        self.assertEqual((lf['s1']['state'], lf['s1']['weight'], lf['s1']['resighted_by'], lf['s1']['resightings']),
                         ('still_there', 2, [K], ['s2']))

    def test_the_same_player_adds_no_weight(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The bridge rail is loose'),
                            sg('s2', 'defect', 'Again', links={'witnesses': ['s1']})]
        lines = [L('r1', 'sight', P, {'text': 'and again'}, {'anchored_to': ['s1']}),
                 L('r2', 'sight', AG, {'text': 'my agent saw it too'}, {'anchored_to': ['s1']})]   # P's own agent
        lf = S.lifecycle(its, lines, NOW)
        self.assertEqual((lf['s1']['state'], lf['s1']['weight'], lf['s1']['resighted_by']), ('seen', 1, []))

    def test_each_distinct_player_adds_one(self):
        its = base()
        its['sightings'] = [sg('s1', 'hazard', 'Ice on the steps'),
                            sg('s2', 'hazard', 'Still icy', actor=K, links={'serves': ['s1']})]
        lines = [L('r1', 'sight', K, {'text': 'again'}, {'supersedes': ['s1']}),
                 L('r2', 'sight', T, {'text': 'yes'}, {'predecessor': ['s1']})]
        lf = S.lifecycle(its, lines)
        self.assertEqual((lf['s1']['weight'], lf['s1']['resighted_by']), (3, [K, T]))


class PickedUpAndClosed(unittest.TestCase):
    def test_a_commit_serving_it_picks_it_up(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The form drops the last line')]
        its['commitments'] = [{'id': 'c1', 'kind': 'commitment', 'holon': H, 'card': 'x', 'by': '2026-11-01',
                               'state': 'open', 'actor': K, 'for': K, 'links': {'serves': ['s1']}}]
        lf = S.lifecycle(its)['s1']
        self.assertEqual((lf['state'], lf['picked_up_by'], lf['became']), ('picked_up', K, None))

    def test_a_commit_on_a_card_that_serves_it_and_what_it_became(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The form drops the last line')]
        its['cards'] = [{'id': 'k1', 'kind': 'card', 'holon': H, 'title': 'Mend the form', 'state': 'ready',
                         'actor': K, 'for': K, 'links': {'serves': ['s1']}}]
        lines = [L('c1', 'commit', T, {'card': 'k1', 'by': '2026-11-01'})]
        lf = S.lifecycle(its, lines)['s1']
        self.assertEqual((lf['state'], lf['picked_up_by'], lf['became']), ('picked_up', T, 'k1'))

    def test_a_released_commitment_picks_up_nothing(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The form drops the last line')]
        its['commitments'] = [{'id': 'c1', 'kind': 'commitment', 'holon': H, 'card': 's1', 'state': 'released',
                               'actor': K, 'for': K}]
        self.assertEqual(S.lifecycle(its)['s1']['state'], 'seen')

    def test_a_settle_closes_it_with_its_consequence_and_precedence_holds(self):
        its = base()
        its['sightings'] = [sg('s1', 'blocked', 'The east road is shut'),
                            sg('s2', 'blocked', 'Still shut', actor=K, links={'anchored_to': ['s1']})]
        lines = [L('c1', 'commit', T, {'card': 's1', 'by': '2026-11-01'}),
                 L('st', 'settle', K, {'text': 'We walk the river path until spring'}, {'anchored_to': ['s1']},
                   ts='2026-10-23T09:00:00-07:00')]
        lf = S.lifecycle(its, lines)['s1']
        self.assertEqual(lf['state'], 'closed')
        self.assertEqual(lf['closed'], {'settle': 'st', 'consequence': 'We walk the river path until spring'})
        self.assertEqual(lf['weight'], 2)                       # still weighed, though closed

    def test_a_settled_thread_anchored_to_it_closes_it(self):
        its = base()
        its['sightings'] = [sg('s1', 'question', 'Who keeps the hall key?')]
        its['threads'] = [{'id': 't1', 'kind': 'thread', 'holon': H, 'state': 'settled', 'actor': K, 'for': K,
                           'anchor': 's1', 'text': 'The steward keeps it', 'ts': '2026-10-23T09:00:00-07:00'}]
        lf = S.lifecycle(its)['s1']
        self.assertEqual((lf['state'], lf['closed']['consequence']), ('closed', 'The steward keeps it'))

    def test_the_folds_own_states_and_precedence(self):
        its = base()
        its['sightings'] = [sg('a', 'defect', 'x', state='accepted', holder=K),
                            sg('f', 'defect', 'y', state='fixed', fixed_ts='2026-10-23T09:00:00-07:00'),
                            sg('r', 'defect', 'z', state='retracted'),
                            sg('rs', 'defect', 'z again', actor=K, links={'anchored_to': ['r', 'f']})]
        lines = [L('d1', 'done', T, {'card': 'f'}, ts='2026-10-23T09:00:00-07:00')]
        lf = S.lifecycle(its, lines)
        self.assertEqual((lf['a']['state'], lf['a']['accepted_by']), ('accepted', K))
        self.assertEqual((lf['f']['state'], lf['f']['fixed_by'], lf['f']['weight']), ('fixed', T, 2))
        self.assertEqual(lf['r']['state'], 'retracted')         # retracted outranks a re-sighting

    def test_a_persons_thread_note_accepts_it(self):
        its = base()
        its['sightings'] = [sg('s1', 'wonder', 'A hall is free on Fridays')]
        its['threads'] = [{'id': 'h1', 'kind': 'thread', 'holon': H, 'state': 'open', 'actor': K, 'for': K,
                           'anchor': ['s1'], 'text': 'Held until the hall answers'}]
        lf = S.lifecycle(its)['s1']
        self.assertEqual((lf['state'], lf['accepted_by'], lf['triage']), ('accepted', K, 'held'))


class APainNeedsAResponse(unittest.TestCase):
    def pain(self):
        its = base()
        its['sightings'] = [sg('p1', 'pain', 'A member has been silent two days and cannot reach the cell')]
        return its

    def test_a_pain_with_no_response_needs_one(self):
        lf = S.lifecycle(self.pain())['p1']
        self.assertEqual((lf['state'], lf['needs_response'], lf['responded_by']), ('seen', True, []))

    def test_the_sighters_own_line_does_not_answer_it(self):
        lines = [L('y1', 'say', P, {'text': 'still no word'}, {'anchored_to': ['p1']}),
                 L('y2', 'say', AG, {'text': 'I am watching for word'}, {'anchored_to': ['p1']})]
        self.assertTrue(S.lifecycle(self.pain(), lines, NOW)['p1']['needs_response'])

    def test_one_say_by_another_clears_it(self):
        lines = [L('y1', 'say', K, {'text': 'I will call tonight'}, {'anchored_to': ['p1']})]
        lf = S.lifecycle(self.pain(), lines)['p1']
        self.assertEqual((lf['state'], lf['needs_response'], lf['responded_by']), ('responded', False, [K]))

    def test_responded_is_for_a_pain_only(self):
        its = base()
        its['sightings'] = [sg('q1', 'question', 'Is the well safe?')]
        lines = [L('y1', 'say', K, {'text': 'I think so'}, {'anchored_to': ['q1']})]
        lf = S.lifecycle(its, lines)['q1']
        self.assertEqual((lf['state'], lf['needs_response'], lf['responded_by']), ('seen', False, []))


class TheMap(unittest.TestCase):
    def its(self):
        its = base()
        its['sightings'] = [sg('s1', 'hazard', 'Ice on the steps', where='the hall'),
                            sg('s2', 'hazard', 'Ice again', actor=K, where='the hall', links={'anchored_to': ['s1']},
                               ts='2026-10-22T08:00:00-07:00'),
                            sg('s3', 'wonder', 'Swallows nesting', where='the hall'),
                            sg('s4', 'pain', 'Someone is alone and unwell', where=None),
                            sg('s5', 'defect', 'The tap drips', where='the hall', state='fixed'),
                            sg('s6', 'defect', 'Wrongly seen', where='the hall', state='retracted'),
                            sg('s7', 'defect', 'A loose board', where='café')]       # not NFC
        its['sightings'].append(sg('s8', 'defect', 'Another board', where='café', actor=T))
        return its

    def test_grouped_by_place_and_kind_and_counted(self):
        m = S.the_map(self.its())
        self.assertEqual(sorted(m['by_place']), ['(no place)', 'café', 'the hall'])
        self.assertEqual([r['id'] for r in m['by_place']['the hall']['hazard']], ['s1', 's2'])   # weight first
        self.assertEqual([r['id'] for r in m['by_place']['café']['defect']], ['s7', 's8'])
        self.assertEqual(m['by_kind'], {'hazard': 2, 'wonder': 1, 'pain': 1, 'defect': 3})
        self.assertEqual((m['open'], m['pains_open'], m['retracted']), (6, 1, 1))
        self.assertEqual(m['as_of'], '2026-10-22T09:00:00-07:00')
        self.assertTrue(m['by_place']['(no place)']['pain'][0]['needs_response'])

    def test_deterministic(self):
        a = self.its()
        b = self.its()
        b['sightings'].reverse()
        x = json.dumps(S.the_map(a, now=NOW), sort_keys=True)
        self.assertEqual(x, json.dumps(S.the_map(b, now=NOW), sort_keys=True))
        self.assertEqual(x, json.dumps(S.the_map(a, now=NOW), sort_keys=True))
        self.assertEqual(S.the_map(a, now=NOW)['as_of'], NOW)

    def test_one_holon(self):
        its = self.its()
        its['sightings'].append(dict(sg('o1', 'wonder', 'Elsewhere'), holon=H2))
        self.assertEqual(S.the_map(its, holon=H2)['by_kind'], {'wonder': 1})


class Scoreboard(unittest.TestCase):
    def test_defects_per_sighter(self):
        its = base()
        its['sightings'] = [sg('d1', 'defect', 'a'), sg('d2', 'defect', 'b'), sg('w1', 'wonder', 'c'),
                            sg('d3', 'defect', 'd', actor=K),
                            sg('d4', 'defect', 'e', state='retracted'),
                            sg('r1', 'defect', 'a again', actor=K, links={'anchored_to': ['d1']}),
                            sg('f1', 'defect', 'f', actor=K, state='fixed', fixed_ts='2026-10-23T09:00:00-07:00')]
        lines = [L('dn', 'done', P, {'card': 'f1'}, ts='2026-10-23T09:00:00-07:00'),
                 L('x1', 'sight', T, {'text': 'seen'}, {'anchored_to': ['d2']})]
        b = S.scoreboard(its, lines)
        self.assertEqual(b[P], {'defects_sighted': 2, 'sightings': 3, 'resightings': 0, 'fixed_by_me': 1})
        self.assertEqual(b[K], {'defects_sighted': 2, 'sightings': 2, 'resightings': 1, 'fixed_by_me': 0})
        self.assertEqual(b[T], {'defects_sighted': 0, 'sightings': 0, 'resightings': 1, 'fixed_by_me': 0})


class OnlyTrustedLinesCount(unittest.TestCase):
    def its(self):
        its = base()
        its['sightings'] = [sg('s1', 'pain', 'Someone needs a ride to the clinic')]
        return its

    def test_untrusted_invalid_and_undelegated_count_for_nothing(self):
        its = self.its()
        its['invalid'] = [{'id': 'bad', 'said': 'bad signature'}]
        its['trust'] = {'unv': 'unverified'}
        lines = [L('u1', 'sight', K, {'text': 'still there'}, {'anchored_to': ['s1']}, reason='untrusted'),
                 L('u2', 'say', K, {'text': 'I can drive'}, {'anchored_to': ['s1']}, reason='untrusted'),
                 L('bad', 'sight', T, {'text': 'still'}, {'anchored_to': ['s1']}),
                 L('unv', 'say', T, {'text': 'me too'}, {'anchored_to': ['s1']}),
                 L('a1', 'say', 'agent:stranger', {'text': 'hello'}, {'anchored_to': ['s1']}, for_=K),
                 L('a2', 'commit', AG, {'card': 's1', 'by': '2026-11-01'}, for_=K),
                 L('a3', 'sight', 'agent:k-aide', {'text': 'on behalf'}, {'anchored_to': ['s1']}, for_=K),
                 L('w1', 'say', K, {'text': 'not mine to say'}, {'anchored_to': ['s1']}, for_=T),
                 'not a line', 3.5, None]
        lf = S.lifecycle(its, lines, NOW)['s1']
        self.assertEqual((lf['state'], lf['weight'], lf['needs_response'], lf['picked_up_by']), ('seen', 1, True, None))

    def test_a_delegated_agent_counts_as_its_person(self):
        its = self.its()
        its['delegations'].append({'id': 'g2', 'kind': 'delegation', 'holon': H, 'state': 'live', 'to': 'agent:k-aide',
                                   'actor': K, 'for': K, 'scope': ['sight'], 'holons': [H], 'until': '2026-12-31'})
        lines = [L('a3', 'sight', 'agent:k-aide', {'text': 'on behalf'}, {'anchored_to': ['s1']}, for_=K)]
        lf = S.lifecycle(its, lines, NOW)['s1']
        self.assertEqual((lf['weight'], lf['resighted_by']), (2, [K]))

    def test_an_untrusted_folded_item_counts_for_nothing(self):
        its = self.its()
        its['sightings'].append(sg('s2', 'pain', 'again', actor=K, reason='untrusted', links={'anchored_to': ['s1']}))
        self.assertEqual(S.lifecycle(its)['s1']['weight'], 1)


class TriageKeepsItsStatuses(unittest.TestCase):
    def test_rows_carry_life_weight_and_kind(self):
        its = base()
        its['sightings'] = [sg('s1', 'hazard', 'The bridge is cracked'),
                            sg('s2', 'hazard', 'Cracked still', actor=K, links={'anchored_to': ['s1']}),
                            sg('s3', 'gift', 'Not one of the nine')]
        rows = {r['id']: r for r in S.triage(its)}
        self.assertEqual((rows['s1']['status'], rows['s1']['life'], rows['s1']['weight']), ('new', 'still_there', 2))
        self.assertEqual(rows['s2']['status'], 'folded')
        self.assertEqual((rows['s1']['known_kind'], rows['s3']['known_kind'], rows['s3']['kind']), (True, False, 'gift'))


class NullGuardsAndWords(unittest.TestCase):
    def test_empty_and_odd_inputs(self):
        for its in (None, {}, [], 3.5, 'text', {'sightings': None}, {'sightings': [None, 3.5, 'x', {}]}):
            for lines in (None, [], 3.5, {}, [None, 1.5, 'x', {}]):
                self.assertEqual(S.lifecycle(its, lines), {})
                self.assertEqual(S.triage(its, lines=lines), [])
                m = S.the_map(its, lines)
                self.assertEqual((m['by_place'], m['open'], m['pains_open'], m['as_of']), ({}, 0, 0, None))
                self.assertEqual(S.scoreboard(its, lines), {})
        self.assertEqual(S.by_holon(None, 3.5), {})
        self.assertEqual(S.paper(None), '')
        self.assertEqual(S.paper({}), '(no kind) · (no place) · ')

    def test_odd_fields_on_a_sighting(self):
        its = base()
        its['sightings'] = [{'id': 's1', 'kind': 'sighting', 'holon': H, 'body_kind': 7, 'where': 2.5, 'ts': 1.5,
                             'text': None, 'actor': None, 'links': {'anchored_to': 3}, 'state': None}]
        lf = S.lifecycle(its)['s1']
        self.assertEqual((lf['state'], lf['kind'], lf['weight']), ('seen', None, 1))
        self.assertEqual(S.the_map(its)['by_place'], {'(no place)': {'(no kind)': S.triage(its)}})

    def test_paper_and_the_acts(self):
        s = sg('s1', 'blocked', 'The east  road\nis shut')
        self.assertEqual(S.paper(s), 'blocked · the north gate · The east road is shut')
        c = S.claim_line(s, K, NOW)
        self.assertEqual((c['type'], c['body']['card'], c['actor'], c['for'], c['sig']), ('claim', 's1', K, K, ''))
        r = S.resight_line(s, AG, 'still shut', NOW, for_=P)
        self.assertEqual((r['type'], r['links']['anchored_to'], r['body']['kind'], r['body']['where'], r['for']),
                         ('sight', ['s1'], 'blocked', 'the north gate', P))
        self.assertEqual(S.resight_line(None, K, 'x', NOW)['type'], 'sight')

    def test_the_nine_agree_with_the_registry(self):
        with open(os.path.join(ENGINE, 'types.json'), encoding='utf-8') as f:
            t = json.load(f)
        kind = next(fd for fd in t['types']['sight']['fields'] if fd['name'] == 'kind')
        self.assertEqual(tuple(kind['values']), S.NINE)
        states = t['items']['sighting']['states']
        for st in S.PRECEDENCE:
            self.assertIn(st, states)

    def test_the_kits_words(self):
        with open(os.path.join(ENGINE, 'sightings.py'), encoding='utf-8') as f:
            src = f.read().lower()
        import re
        for w in ('promise', 'house', 'hq', 'estate'):
            self.assertIsNone(re.search(r'\b%s' % w, src), w)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='sightings-cli-')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'sightings.py')] + list(args),
                              capture_output=True, text=True, cwd=self.d)

    def test_map_scoreboard_and_paper(self):
        its = base()
        its['sightings'] = [sg('s1', 'pain', 'Someone needs a ride')]
        p = os.path.join(self.d, 'items.json')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(its, f)
        lp = os.path.join(self.d, 'lines.jsonl')
        with open(lp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(L('y1', 'say', K, {'text': 'I can drive'}, {'anchored_to': ['s1']})) + '\nnot json\n')
        r = self.run_cli(p, '--map')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['pains_open'], 1)
        r = self.run_cli(p, '--lines', lp, '--json')
        self.assertEqual(json.loads(r.stdout)[0]['life'], 'responded')
        r = self.run_cli(p, '--scoreboard')
        self.assertEqual(json.loads(r.stdout)[P]['sightings'], 1)
        r = self.run_cli(p)
        self.assertEqual(r.stdout.strip(), 'seen · weight 1 · pain · the north gate · Someone needs a ride')

    def test_missing_and_linked_files_are_refused(self):
        r = self.run_cli(os.path.join(self.d, 'none.json'))
        self.assertNotEqual(r.returncode, 0)
        real = os.path.join(self.d, 'real.json')
        with open(real, 'w', encoding='utf-8') as f:
            f.write('{}')
        link = os.path.join(self.d, 'link.json')
        os.symlink(real, link)
        r = self.run_cli(link)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('not a plain file', r.stderr)


class Repairs(unittest.TestCase):
    """The independent review's findings, each held by a test."""

    def test_a_retracted_card_never_returns_through_its_line(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The form drops the last line')]
        its['cards'] = [{'id': 'k1', 'kind': 'card', 'holon': H, 'title': 'Mend the form', 'state': 'retracted',
                         'actor': K, 'for': K, 'links': {'serves': ['s1']}}]
        lines = [L('k1', 'card', K, {'title': 'Mend the form'}, {'serves': ['s1']}),
                 L('c1', 'commit', T, {'card': 'k1', 'by': '2026-11-01'})]
        lf = S.lifecycle(its, lines)['s1']
        self.assertEqual((lf['state'], lf['became'], lf['picked_up_by']), ('seen', None, None))

    def test_a_released_commitment_never_returns_through_its_line(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'The gate sticks')]
        its['commitments'] = [{'id': 'c1', 'kind': 'commitment', 'holon': H, 'card': 's1', 'state': 'released',
                               'actor': K, 'for': K}]
        lines = [L('c1', 'commit', K, {'card': 's1', 'by': '2026-11-01'})]
        self.assertEqual(S.lifecycle(its, lines)['s1']['state'], 'seen')

    def test_who_an_agent_serves_comes_only_from_trusted_lines_and_delegations(self):
        its = base()
        its['sightings'] = [sg('p1', 'pain', 'help', state='accepted', holder=AG)]   # P's own agent holds it
        x = L('zz', 'say', AG, {'text': 'x'}, for_=K, reason='untrusted', ts='2026-10-01T00:00:00-07:00')
        y = L('zy', 'say', AG, {'text': 'y'}, for_=T, reason='untrusted', ts='2026-10-01T00:00:00-07:00')
        a = S.lifecycle(its, [x, y])['p1']
        b = S.lifecycle(its, [y, x])['p1']
        self.assertEqual(a, b)
        self.assertEqual((a['needs_response'], a['responded_by']), (True, []))

    def test_a_list_id_in_a_threads_lines_is_guarded(self):
        its = base()
        its['sightings'] = [sg('p1', 'pain', 'help')]
        its['threads'] = [{'id': 't1', 'kind': 'thread', 'holon': H, 'state': 'open', 'actor': K, 'for': K,
                           'anchor': 'p1', 'lines': [{'id': ['a'], 'actor': K}, {'id': {'x': 1}}]}]
        self.assertEqual(S.lifecycle(its, [])['p1']['responded_by'], [K])

    def test_the_map_is_free_of_thread_order(self):
        its = base()
        its['sightings'] = [sg('s1', 'wonder', 'Swallows nesting')]
        its['threads'] = [{'id': 't1', 'kind': 'thread', 'holon': H, 'state': 'open', 'actor': K, 'for': K,
                           'anchor': 's1', 'text': 'one', 'ts': '2026-10-22T10:00:00-07:00'},
                          {'id': 't2', 'kind': 'thread', 'holon': H, 'state': 'open', 'actor': T, 'for': T,
                           'anchor': 's1', 'text': 'two', 'ts': '2026-10-22T09:30:00-07:00'}]
        a = json.dumps(S.the_map(its, now=NOW), sort_keys=True)
        its['threads'].reverse()
        self.assertEqual(a, json.dumps(S.the_map(its, now=NOW), sort_keys=True))
        self.assertEqual(S.the_map(its)['by_place']['the north gate']['wonder'][0]['held']['thread'], 't2')

    def test_the_scoreboard_counts_a_line_once(self):
        its = base()
        its['sightings'] = [sg('d1', 'defect', 'a')]
        l = L('x1', 'sight', T, {'text': 'seen'}, {'anchored_to': ['d1']})
        self.assertEqual(S.scoreboard(its, [l, dict(l), dict(l)])[T]['resightings'], 1)

    def test_a_sighters_own_note_never_accepts_their_own_pain(self):
        its = base()
        its['sightings'] = [sg('p1', 'pain', 'help')]
        its['threads'] = [{'id': 'h1', 'kind': 'thread', 'holon': H, 'state': 'open', 'actor': P, 'for': P,
                           'anchor': ['p1'], 'text': 'still waiting'}]
        lf = S.lifecycle(its)['p1']
        self.assertEqual((lf['state'], lf['accepted_by'], lf['needs_response']), ('seen', None, True))

    def test_as_of_never_comes_from_a_retracted_row(self):
        its = base()
        its['sightings'] = [sg('s1', 'defect', 'a', ts='2026-10-22T09:00:00-07:00'),
                            sg('s2', 'defect', 'b', ts='2026-10-23T09:00:00-07:00', state='retracted')]
        self.assertEqual(S.the_map(its)['as_of'], '2026-10-22T09:00:00-07:00')

    def test_an_ended_pain_needs_no_response(self):
        its = base()
        its['sightings'] = [sg('pf', 'pain', 'a', state='fixed'), sg('pr', 'pain', 'b', state='retracted'),
                            sg('pc', 'pain', 'c')]
        lines = [L('st', 'settle', P, {'text': 'it passed'}, {'anchored_to': ['pc']})]   # the sighter's own settle
        lf = S.lifecycle(its, lines)
        self.assertEqual([(lf[i]['state'], lf[i]['needs_response']) for i in ('pf', 'pr', 'pc')],
                         [('fixed', False), ('retracted', False), ('closed', False)])

    def test_an_agents_settle_or_commit_counts_for_nothing_even_delegated(self):
        its = base()
        its['sightings'] = [sg('p1', 'pain', 'help')]
        its['delegations'].append({'id': 'g3', 'kind': 'delegation', 'holon': H, 'state': 'live', 'to': 'agent:k-aide',
                                   'actor': K, 'for': K, 'scope': ['settle', 'commit', '*'], 'holons': [H],
                                   'until': '2026-12-31'})
        lines = [L('a1', 'settle', 'agent:k-aide', {'text': 'done'}, {'anchored_to': ['p1']}, for_=K),
                 L('a2', 'commit', 'agent:k-aide', {'card': 'p1', 'by': '2026-11-01'}, for_=K)]
        lf = S.lifecycle(its, lines, NOW)['p1']
        self.assertEqual((lf['state'], lf['closed'], lf['picked_up_by'], lf['needs_response']), ('seen', None, None, True))


HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the fixtures are signed')
class OverTheRealFold(unittest.TestCase):
    """Signed lines in the sample cell, folded by record.py, read by the lifecycle."""

    @classmethod
    def setUpClass(cls):
        import record
        import make_fixtures
        cls.record, cls.mf = record, make_fixtures
        cls.work = tempfile.mkdtemp(prefix='lionsberg-sightings-test-')
        os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(cls.work, 'sigcache.key')
        cls.keys = os.path.join(cls.work, 'keys')
        cls.ids = make_fixtures.build(cls.work, cls.keys)
        cls.hq = os.path.join(cls.work, 'hq')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_resighted_answered_and_closed(self):
        rec, mf = self.record, self.mf
        r = rec.read_all(self.hq)
        heads = {}
        for d in rec.hold(self.hq):
            rr = rec.read(d)
            for a, hs in rr['heads'].items():
                heads[(rr['holon'], a)] = hs[-1]
        C = self.ids['cell_holon']

        def mk(actor, typ, body, links=None, ts='2026-10-21T09:00:00-07:00'):
            line = rec.make_line(actor, actor, C, typ, body, links, ts=ts, salt='t', prev=heads.get((C, actor), ''))
            line['sig'] = rec.sign_id(line['id'], rec.find_key(None, actor, self.keys))
            heads[(C, actor)] = line['id']
            return line

        p = mk(mf.PLAYER, 'sight', {'text': 'a member cannot reach the cell', 'kind': 'pain', 'where': 'the north gate'})
        rs = mk(mf.STEWARD, 'sight', {'text': 'still no word', 'kind': 'pain'}, {'anchored_to': [p['id']]},
                ts='2026-10-21T09:01:00-07:00')
        new = r['lines'] + [p, rs]
        f = rec.fold(new, rec.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')
        lf = S.lifecycle(f, new)[p['id']]
        self.assertEqual((lf['state'], lf['weight'], lf['needs_response']), ('still_there', 2, True))
        y = mk(mf.STEWARD, 'say', {'text': 'I will walk over tonight'}, {'anchored_to': [p['id']]},
               ts='2026-10-21T09:02:00-07:00')
        st = mk(mf.PLAYER, 'settle', {'text': 'they are well; the line was down'}, {'anchored_to': [p['id']]},
                ts='2026-10-21T09:03:00-07:00')
        new = new + [y]
        f = rec.fold(new, rec.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')
        lf = S.lifecycle(f, new)[p['id']]
        self.assertEqual((lf['state'], lf['needs_response'], lf['responded_by']), ('responded', False, [mf.STEWARD]))
        new = new + [st]
        f = rec.fold(new, rec.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')
        lf = S.lifecycle(f, new)[p['id']]
        self.assertEqual((lf['state'], lf['closed']['consequence']), ('closed', 'they are well; the line was down'))


    def test_a_commit_then_its_release_leaves_it_seen(self):
        rec, mf = self.record, self.mf
        r = rec.read_all(self.hq)
        heads = {}
        for d in rec.hold(self.hq):
            rr = rec.read(d)
            for a, hs in rr['heads'].items():
                heads[(rr['holon'], a)] = hs[-1]
        C = self.ids['cell_holon']

        def mk(actor, typ, body, links=None, ts='2026-10-21T09:00:00-07:00'):
            line = rec.make_line(actor, actor, C, typ, body, links, ts=ts, salt='t', prev=heads.get((C, actor), ''))
            line['sig'] = rec.sign_id(line['id'], rec.find_key(None, actor, self.keys))
            heads[(C, actor)] = line['id']
            return line

        d = mk(mf.PLAYER, 'sight', {'text': 'the gate sticks', 'kind': 'defect'}, ts='2026-10-21T09:10:00-07:00')
        c = mk(mf.STEWARD, 'commit', {'card': d['id'], 'by': '2026-11-01'}, ts='2026-10-21T09:11:00-07:00')
        rl = mk(mf.STEWARD, 'release', {'commitment': c['id'], 'why': 'not mine'}, ts='2026-10-21T09:12:00-07:00')
        new = r['lines'] + [d, c]
        f = rec.fold(new, rec.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')
        self.assertEqual(S.lifecycle(f, new)[d['id']]['state'], 'picked_up')
        new = new + [rl]
        f = rec.fold(new, rec.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')
        self.assertIn('released', [x.get('state') for x in f['commitments'] if x['id'] == c['id']])
        self.assertEqual(S.lifecycle(f, new)[d['id']]['state'], 'seen')

if __name__ == '__main__':
    unittest.main()
