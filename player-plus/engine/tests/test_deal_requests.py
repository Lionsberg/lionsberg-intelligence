"""test_deal_requests.py — requests first: what is asked of a person rises to the top of their Deal.

Hand-built items in the shape record.py's fold returns (a dict of lists), across a person's home
and a cell, with trusted lines beside them where a test needs the line itself. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_deal_requests.py -v
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import deal as deal_mod      # noqa: E402
import ladder as ladder_mod  # noqa: E402

NOW = '2026-10-31T12:00:00-07:00'
A, B, F = 'holon-home', 'holon-cell', 'holon-far'
P, K, X, AG = 'person:player', 'person:keeper', 'person:stranger', 'agent:aide'
HOLONS = [{'id': A, 'name': 'Home', 'kind': 'person', 'keeper': P},
          {'id': B, 'name': 'The Cell', 'kind': 'cell', 'keeper': K},
          {'id': F, 'name': 'Far', 'kind': 'cell', 'keeper': X}]
SCHED = {'items': [{'id': 'a1', 'TF': 0, 'critical': True}, {'id': 'a2', 'TF': 0, 'critical': True}],
         'path': {'critical': ['a1', 'a2'], 'system': ['a2']}}


def card(i, holon, title, minutes, holder=P, state='ready', **kw):
    c = {'id': i, 'kind': 'card', 'holon': holon, 'title': title, 'minutes': minutes, 'holder': holder,
         'state': state, 'body_kind': 'activity', 'actor': holder or P, 'for': holder or P,
         'ts': '2026-10-20T09:00:00-07:00'}
    c.update(kw)
    return c


def ask(i, to=P, ts='2026-10-30T09:00:00-07:00', actor=K, holon=B, state='open', **kw):
    """A request card as the fold makes it: holder and `to` from the line's body.to."""
    return card(i, holon, f'Ask {i}', 10, holder=to, state=state, asked='request', to=to, actor=actor,
                ts=ts, **dict({'for': actor}, **kw))


def sight(i, kind='pain', actor=K, holon=B, ts='2026-10-30T10:00:00-07:00', **kw):
    s = {'id': i, 'kind': 'sighting', 'body_kind': kind, 'holon': holon, 'text': f'Seen {i}', 'actor': actor,
         'for': actor, 'ts': ts, 'state': 'seen', 'links': {}}
    s.update(kw)
    return s


def line(i, typ, body, actor=K, holon=B, ts='2026-10-30T11:00:00-07:00', links=None, reason='human', for_=None):
    return {'v': 1, 'id': i, 'ts': ts, 'actor': actor, 'for': for_ or actor, 'holon': holon, 'type': typ,
            'body': body, 'links': links or {}, 'audience': 'holon', 'reason': reason, 'prev': '', 'sig': ''}


def base(**extra):
    its = {
        'cards': [card('a1', A, 'Write the outline', 30, links={'successor': ['a2']}),
                  card('a2', A, 'Write the draft', 60, links={'predecessor': ['a1']}),
                  card('k1', B, 'Sweep the hall', 10, holder=K)],      # K writes in the cell; P holds nothing there
        'commitments': [{'id': 'c-late', 'kind': 'commitment', 'holon': A, 'card': 'a1', 'by': '2026-10-28',
                         'state': 'open', 'for': P, 'actor': P, 'ts': '2026-10-19T09:00:00-07:00'}],
        'threads': [], 'sightings': [],
        'delegations': [{'id': 'g1', 'kind': 'delegation', 'holon': A, 'state': 'live', 'to': AG, 'actor': P,
                         'for': P, 'scope': ['claim', 'say'], 'holons': [A], 'until': '2026-12-31'}],
    }
    for k, v in extra.items():
        its.setdefault(k, []).extend(v)
    return its


def D(its, actor=P, lines=None, **kw):
    return deal_mod.deal(its, SCHED, actor, 1000, now=NOW, holons=HOLONS, lines=lines, **kw)


def ids(d):
    return [c['id'] for c in d['cards']]


class RequestsRiseFirst(unittest.TestCase):
    def test_a_request_to_the_person_rises_above_a_critical_card_with_less_float(self):
        d = D(base(cards=[ask('r1')]))
        top = d['cards'][0]
        self.assertEqual(top['id'], 'r1')
        self.assertEqual((top['why'], top['rose']), ('asked of you', True))
        self.assertTrue(top.get('because'))                       # the reason it had before it rose is kept
        self.assertLess(ids(d).index('r1'), ids(d).index('c-late'))   # above a commitment past its by-when
        self.assertLess(ids(d).index('r1'), ids(d).index('a1'))       # and above the critical card at float 0
        self.assertFalse(d['cards'][ids(d).index('a1')]['rose'])
        self.assertEqual(d['risen']['requests'], 1)

    def test_a_request_line_rises_when_the_card_does_not_keep_its_to(self):
        c = ask('r2')
        c.pop('to')                                               # a request acting on a card already there
        self.assertNotIn('r2', [x['id'] for x in D(base(cards=[c]))['cards'] if x['rose']])
        ln = line('L-r2', 'request', {'to': P, 'card': 'r2'})
        d = D(base(cards=[c]), lines=[ln])
        self.assertEqual(d['cards'][0]['id'], 'r2')
        self.assertTrue(d['cards'][0]['rose'])

    def test_a_say_a_commit_an_escalate_and_an_rfg_rise(self):
        th = {'id': 't1', 'kind': 'thread', 'holon': B, 'state': 'open', 'actor': K, 'text': 'The hall',
              'ts': '2026-10-29T09:00:00-07:00',
              'lines': [{'id': 's1', 'type': 'say', 'actor': K, 'ts': '2026-10-30T08:00:00-07:00', 'text': 'Friday?'}]}
        cm = {'id': 'c2', 'kind': 'commitment', 'holon': B, 'card': 'k1', 'by': '2026-11-06', 'state': 'open',
              'for': K, 'actor': K, 'committee': P, 'ts': '2026-10-30T07:00:00-07:00'}
        lines = [line('s1', 'say', {'text': 'Friday?', 'to': [P]}, ts='2026-10-30T08:00:00-07:00',
                      links={'anchored_to': ['t1']}),
                 line('e1', 'escalate', {'about': 'k1', 'to': A, 'blast_radius': 'home'}, ts='2026-10-30T06:00:00-07:00'),
                 line('q1', 'rfg', {'question': 'Which room?', 'to': P}, ts='2026-10-30T05:00:00-07:00')]
        d = D(base(threads=[th], commitments=[cm]), lines=lines)
        risen = [c for c in d['cards'] if c['rose']]
        self.assertEqual([c['id'] for c in risen], ['t1', 'c2', 'e1', 'q1'])      # newest first
        self.assertTrue(all(c['why'] == 'asked of you' for c in risen))
        self.assertIn('commits to you', risen[1]['question'])
        self.assertTrue(risen[2]['question'].startswith('A decision for you:'))
        self.assertEqual(risen[2]['holon'], A)
        self.assertTrue(risen[3]['question'].startswith('A question for you:'))
        self.assertEqual(risen[3]['holon'], B)                                      # a question to a person stays where it was asked

    def test_a_request_to_their_agent_rises(self):
        d = D(base(), lines=[line('s9', 'say', {'text': 'Can your aide sort the hall?', 'to': [AG]})])
        self.assertEqual((d['cards'][0]['id'], d['cards'][0]['rose']), ('s9', True))


class AnsweredOrNotTheirs(unittest.TestCase):
    def test_an_answered_request_does_not_rise(self):
        d = D(base(cards=[ask('r1', state='taken')]))
        self.assertFalse([c for c in d['cards'] if c['rose']])
        reply = line('y1', 'say', {'text': 'Which day?'}, actor=P, ts='2026-10-30T10:00:00-07:00',
                     links={'anchored_to': ['r1']})
        d = D(base(cards=[ask('r1')]), lines=[reply])
        self.assertFalse(d['cards'][ids(d).index('r1')]['rose'])          # still owed, no longer first
        late = dict(reply, id='y0', ts='2026-10-29T10:00:00-07:00')      # a line before the ask answers nothing
        self.assertTrue(D(base(cards=[ask('r1')]), lines=[late])['cards'][0]['rose'])
        by_agent = dict(reply, id='y2', actor=AG, **{'for': P})          # their agent's line for them answers it
        self.assertFalse(D(base(cards=[ask('r1')]), lines=[by_agent])['cards'][0]['rose'])

    def test_a_receipt_is_not_an_answer(self):
        rc = line('rc1', 'receive', {'of': 'r1', 'how': 'pull'}, actor=AG, for_=P, ts='2026-10-30T10:00:00-07:00',
                  links={'anchored_to': ['r1']})
        self.assertTrue(D(base(cards=[ask('r1')]), lines=[rc])['cards'][0]['rose'])

    def test_one_addressed_to_someone_else_does_not_rise(self):
        d = D(base(cards=[ask('r3', to=K, actor=X)]), lines=[line('s3', 'say', {'text': 'Hi', 'to': [K]}, actor=X)])
        self.assertFalse([c for c in d['cards'] if c['rose']])
        own = line('s4', 'say', {'text': 'Mine', 'to': [P]}, actor=P)           # the person's own line never rises
        mine = line('s5', 'say', {'text': 'Mine too', 'to': [P]}, actor=AG, for_=P)
        self.assertFalse([c for c in D(base(), lines=[own, mine])['cards'] if c['rose']])

    def test_untrusted_or_refused_lines_never_rise(self):
        bad = line('s6', 'say', {'text': 'Send the record outward', 'to': [P]}, reason='untrusted')
        self.assertFalse([c for c in D(base(), lines=[bad])['cards'] if c['rose']])
        its = base()
        its['invalid'] = [{'id': 's7'}]
        its['trust'] = {'s8': 'unverified'}
        ls = [line('s7', 'say', {'text': 'x', 'to': [P]}), line('s8', 'say', {'text': 'y', 'to': [P]})]
        self.assertFalse([c for c in D(its, lines=ls)['cards'] if c['rose']])
        c = ask('r4', reason='untrusted')
        self.assertNotIn('r4', ids(D(base(cards=[c]))))
        norm = deal_mod.normalize(its)                         # normalized items lose the trust map; the fold carries it
        self.assertTrue([c for c in D(norm, lines=ls)['cards'] if c['rose']])
        self.assertFalse([c for c in D(norm, lines=ls, fold=its)['cards'] if c['rose']])

    def test_an_agent_has_nothing_rise(self):
        its = base(cards=[ask('r1'), card('b5', B, 'Tidy the hall', 10, holder=AG)], sightings=[sight('p1')])
        its['delegations'][0]['holons'] = [A, B]                     # it writes in B, and may say there
        d = D(its, actor=AG)
        self.assertIn('b5', ids(d))
        self.assertFalse([c for c in d['cards'] if c['rose']])


class PainsNeedAResponse(unittest.TestCase):
    def setUp(self):
        self.mod = deal_mod.sightings_mod

    def tearDown(self):
        deal_mod.sightings_mod = self.mod

    def both(self):
        """The same answer from sightings.lifecycle and from the fallback."""
        yield 'lifecycle'
        deal_mod.sightings_mod = None
        yield 'fallback'

    def test_a_pain_rises_below_requests_and_above_the_rest(self):
        for how in self.both():
            its = base(cards=[ask('r1', ts='2026-10-29T09:00:00-07:00')], sightings=[sight('p1')])
            d = D(its)
            self.assertEqual(ids(d)[:3], ['r1', 'p1', 'c-late'], how)  # the pain is newer, and still below the request
            p = d['cards'][1]
            self.assertEqual((p['why'], p['rose'], p['kind']), ('a pain needs a response', True, 'pain'), how)
            self.assertEqual(d['risen']['pains'], 1, how)
            self.assertTrue(d['risen']['pain_basis'].startswith('fallback') == (how == 'fallback'), how)

    def test_a_responded_pain_does_not_rise(self):
        for how in self.both():
            th = {'id': 't-p', 'kind': 'thread', 'holon': B, 'state': 'open', 'actor': X, 'for': X,
                  'text': 'I can help', 'anchor': ['p1'], 'links': {'anchored_to': ['p1']},
                  'ts': '2026-10-30T11:00:00-07:00'}
            mine = [card('b1', B, 'Book the hall', 10)]                 # the person belongs to B, so a pain there could rise
            self.assertIn('p1', ids(D(base(cards=mine, sightings=[sight('p1')]))), how)
            self.assertNotIn('p1', ids(D(base(cards=mine, sightings=[sight('p1')], threads=[th]))), how)
            fixed = sight('p2', state='fixed')
            self.assertIn('p2', ids(D(base(cards=mine, sightings=[sight('p2')]))), how)
            self.assertNotIn('p2', ids(D(base(cards=mine, sightings=[fixed]))), how)

    def test_the_keeper_keeps_pass_it_on(self):
        tri = [{'id': 'p1', 'holon': B, 'kind': 'pain', 'text': 'Seen p1', 'status': 'new'}]
        d = D(base(sightings=[sight('p1', actor=X)]), actor=K, sightings=tri)
        p = [c for c in d['cards'] if c['id'] == 'p1']
        self.assertEqual(len(p), 1)                                   # the triage card gave way to one pain card
        self.assertEqual((p[0]['kind'], p[0]['rose']), ('pain', True))
        self.assertIn('Pass it on', p[0]['options'])
        self.assertEqual(p[0]['acts'][p[0]['options'].index('Pass it on')], 'elevate')

    def test_a_risen_card_passes_the_same_act_check(self):
        real = deal_mod.may_act
        deal_mod.may_act = lambda norm, actor, act, holon, now=None, card_kind=None: act != 'say' and real(
            norm, actor, act, holon, now, card_kind)
        try:
            d = D(base(cards=[card('b1', B, 'Book the hall', 10)], sightings=[sight('p1')]),
                  lines=[line('s9', 'say', {'text': 'Hi', 'to': [P]})])
            self.assertNotIn('p1', ids(d))
            self.assertNotIn('s9', ids(d))
        finally:
            deal_mod.may_act = real

    def test_only_a_pain_in_a_holon_they_belong_to_and_never_their_own(self):
        for how in self.both():
            d = D(base(sightings=[sight('p3', holon=F, actor=X), sight('p4', actor=P)]))
            self.assertFalse([c for c in d['cards'] if c['rose']], how)

    def test_other_kinds_of_sighting_do_not_rise(self):
        self.assertFalse([c for c in D(base(sightings=[sight('h1', kind='hazard')]))['cards'] if c['rose']])


class NewestFirst(unittest.TestCase):
    def test_order_among_risen_requests_is_newest_first_and_deterministic(self):
        rs = [ask('r1', ts='2026-10-28T09:00:00-07:00'), ask('r2', ts='2026-10-30T09:00:00-07:00'),
              ask('r3', ts='2026-10-29T09:00:00-07:00'), ask('r0', ts='2026-10-29T09:00:00-07:00'),
              ask('r9', ts='not a time')]
        d = D(base(cards=rs))
        self.assertEqual([c['id'] for c in d['cards'] if c['rose']], ['r2', 'r0', 'r3', 'r1', 'r9'])
        rev = base(cards=list(reversed(copy.deepcopy(rs))))
        self.assertEqual(json.dumps(d, sort_keys=True), json.dumps(D(rev), sort_keys=True))

    def test_a_risen_card_is_not_an_interruption(self):
        d = D(base(cards=[ask('r1')]))
        self.assertFalse(d['cards'][0]['always_passes'])
        th = {'id': 't1', 'kind': 'thread', 'holon': B, 'state': 'open', 'actor': K, 'to': [P], 'text': 'Now?',
              'ts': '2026-10-30T09:00:00-07:00'}
        top = D(base(threads=[th]), room=[K])['cards'][0]
        self.assertEqual((top['id'], top['rose']), ('t1', True))
        self.assertTrue(top['always_passes'])                     # the asker is in the room: they wait now
        only = D(base(cards=[ask('r1')]), fewer=3)
        self.assertNotIn('r1', ids(only))                         # the gate decides what passes, not the rise


class ReceiptsAndAsOf(unittest.TestCase):
    def sent(self, **kw):
        return card('o1', B, 'Bring the chairs', 10, holder=X, state='open', asked='request', to=X, actor=P,
                    ts='2026-10-28T09:00:00-07:00', **dict({'for': P}, **kw))

    def test_a_line_with_no_receipt_is_dealt_to_its_sender(self):
        d = D(base(cards=[self.sent()]))
        rc = [c for c in d['cards'] if c['kind'] == 'receipt']
        self.assertEqual(len(rc), 1)
        c = rc[0]
        self.assertTrue(c['question'].startswith(f'No Receipt yet from {X} for "Bring the chairs"'))
        self.assertEqual(c['options'], ['Ask again', 'Let it go'])
        self.assertEqual((c['draft']['type'], c['draft']['body']['to'], c['draft']['sends']), ('say', [X], 'person'))
        self.assertEqual(c['draft']['links']['anchored_to'], ['o1'])
        self.assertEqual(d['receipt_cards'], 1)
        self.assertNotIn('receipts', d['risen'])

    def test_a_receipt_from_them_or_fewer_or_off_deals_none(self):
        got = self.sent(receipts=[{'id': 'rc', 'type': 'receive', 'actor': 'agent:far', 'ts': '2026-10-28T10:00:00-07:00'}])
        for d in (D(base(cards=[got])), D(base(cards=[self.sent()]), fewer=True),
                  D(base(cards=[self.sent()]), receipts=False), D(base(cards=[self.sent()]), actor=AG)):
            self.assertFalse([c for c in d['cards'] if c['kind'] == 'receipt'])

    def test_as_of_names_the_newest_line_seen(self):
        d = D(base(cards=[ask('r1')]), lines=[line('n1', 'say', {'text': 'later'}, ts='2026-10-31T09:00:00-07:00')])
        self.assertEqual(d['newest_line'], {'id': 'n1', 'ts': '2026-10-31T09:00:00-07:00'})
        self.assertNotIn('newest_line', d['as_of'])                  # as_of stays keyed by holon id
        self.assertEqual(D(base(cards=[ask('r1')]))['newest_line']['id'], 'r1')
        self.assertIsNone(D({})['newest_line'])


class TheTrustGate(unittest.TestCase):
    Q = {'id': 'q1', 'type': 'rfg', 'to': A, 'asker': K, 'ts': '2026-10-30T09:00:00-07:00', 'state': 'open',
         'holder': P, 'question': 'Which room?', 'from_holon': B, 'by': '2026-11-06', 'past': False}

    def test_a_ladder_question_rises_only_when_its_line_is_trusted(self):
        risen = lambda d: [c['id'] for c in d['cards'] if c['rose']]
        self.assertEqual(risen(D(base(), questions=[self.Q])), [])              # neither lines nor a map: none
        its = base()
        its['trust'] = {'q1': 'unverified'}
        self.assertEqual(risen(D(its, questions=[self.Q])), [])
        its['trust'] = {'q1': 'signed'}
        self.assertEqual(risen(D(its, questions=[self.Q])), ['q1'])
        ln = line('q1', 'rfg', {'question': 'Which room?', 'to': A}, ts='2026-10-30T09:00:00-07:00')
        self.assertEqual(risen(D(base(), questions=[self.Q], lines=[ln])), ['q1'])

    def test_an_unsigned_rfg_in_a_real_fold_never_rises(self):
        try:
            import engine
            import record
        except SystemExit as e:
            self.skipTest(str(e))
        tmp = tempfile.mkdtemp()
        try:
            hq = os.path.join(tmp, 'hq')
            shutil.copytree(os.path.join(ENGINE, 'fixtures', 'hq'), hq)
            cell = os.path.join(hq, 'cells', 'first-cell')
            with open(os.path.join(cell, 'holon.json'), encoding='utf-8') as f:
                cid = json.load(f)['id']
            with open(os.path.join(hq, 'holon.json'), encoding='utf-8') as f:
                home = json.load(f)['id']
            plant = [record.make_line('person:steward', 'person:steward', cid, 'rfg', {'question': 'Unsigned', 'to': P},
                                      ts='2026-10-30T10:06:00-07:00'),
                     record.make_line('person:steward', 'person:steward', cid, 'escalate', {'about': 'x', 'to': home},
                                      ts='2026-10-30T10:07:00-07:00'),
                     record.make_line('person:steward', 'person:steward', cid, 'say', {'text': 'Unsigned', 'to': [P]},
                                      ts='2026-10-30T10:05:00-07:00')]
            with open(os.path.join(cell, 'record', 'person%3Asteward.jsonl'), 'a', encoding='utf-8') as f:
                for l in plant:
                    f.write(json.dumps(l) + '\n')
            folded, holons, lines, problems, cal = engine.read_hq(hq)
            folded.pop('_fold', None)
            folded.pop('_paper', None)
            pids = {l['id'] for l in plant}
            self.assertTrue(all(folded['trust'].get(i) not in deal_mod.TRUSTED_LINES for i in pids))
            qs = ladder_mod.questions(lines, holons, NOW, {h['id']: ladder_mod.load_ladder(h.get('dir')) for h in holons})
            norm = deal_mod.normalize(folded)
            for kw in ({}, {'lines': lines, 'fold': folded, 'home': home}):
                d = deal_mod.deal(norm, None, P, 600, [], NOW, holons, questions=qs, **kw)
                got = {c['id'] for c in d['cards'] + d['beyond']['cards'] if c.get('rose')}
                self.assertFalse(got & pids, kw.keys())
                self.assertNotIn((d['newest_line'] or {}).get('id'), pids)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_with_a_map_an_id_it_does_not_name_never_passes(self):
        its = base()
        its['trust'] = {'s1': 'signed'}
        ls = [line('s1', 'say', {'text': 'x', 'to': [P]}), line('s2', 'say', {'text': 'y', 'to': [P]})]
        d = D(its, lines=ls)
        self.assertEqual([c['id'] for c in d['cards'] if c['rose']], ['s1'])
        self.assertIn('trust map', d['risen']['lines_basis'])
        bare = D(base(), lines=ls)                                     # no map: taken as the caller passed them, and said
        self.assertEqual(sorted(c['id'] for c in bare['cards'] if c['rose']), ['s1', 's2'])
        self.assertIn('no trust map', bare['risen']['lines_basis'])
        self.assertIn('no lines', D(base())['risen']['lines_basis'])

    def test_an_rfg_to_a_list_never_crashes_the_deal(self):
        for to in ([P], [P, A], {'x': 1}, 7):
            d = D(base(), lines=[line('q9', 'rfg', {'question': 'Which room?', 'to': to})])
            for c in d['cards']:
                self.assertIsInstance(c['holon'], str)
        d = D(base(), lines=[line('q9', 'rfg', {'question': 'Which room?', 'to': [P]})])
        self.assertEqual((d['cards'][0]['id'], d['cards'][0]['holon']), ('q9', B))


class GuardsAndWords(unittest.TestCase):
    def test_null_guards(self):
        weird = [None, 1, 1.5, 'x', [], {}, {'id': 3}, {'id': ''}, {'id': 'z', 'type': 'say', 'body': 'not a dict'}]
        for its in (None, {}, [], base()):
            for ls in (None, {}, [], weird, 'lines'):
                for actor in (P, None, 1.5, '', 'agent:x'):
                    d = deal_mod.deal(its, None, actor, 30, now=NOW, holons=HOLONS, lines=ls,
                                      questions=[None, {'id': 9}], people='not a set')
                    self.assertEqual(d['opening'], "Here's the deal.")
                    json.dumps(d, sort_keys=True)
        self.assertEqual(deal_mod.rising(None, None)['requests'], [])

    def test_a_non_nfc_name_still_finds_its_person(self):
        nfd = 'person:' + unicodedata.normalize('NFD', 'zoë')
        nfc = 'person:' + unicodedata.normalize('NFC', 'zoë')
        r = deal_mod.rising(base(), nfc, lines=[line('s1', 'say', {'text': 'hi', 'to': [nfd]})], now=NOW)
        self.assertEqual([x['id'] for x in r['requests']], ['s1'])

    def test_words(self):
        d = D(base(cards=[ask('r1'), self.sent()], sightings=[sight('p1')]))
        md = deal_mod.render(d)
        self.assertTrue(md.startswith("Here's the deal."))
        self.assertIn('rose to the top', md)
        self.assertIn(': asked of you; its size is not said', md)     # the reason it had before it rose follows
        low = md.lower() + json.dumps(d).lower()
        for w in ('promise', 'house', ' hq', 'estate'):
            self.assertNotIn(w, low)
        self.assertIn('[ ]', deal_mod.render_paper(d))

    def sent(self):
        return card('o1', B, 'Bring the chairs', 10, holder=X, state='open', asked='request', to=X, actor=P,
                    ts='2026-10-28T09:00:00-07:00', **{'for': P})


if __name__ == '__main__':
    unittest.main()
