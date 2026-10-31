"""test_plain.py — the simplest form first: three answers in sentences, the tables on a pull.

Over a temporary copy of fixtures/hq, as the person `person:player` (and `person:steward`) sees it, and
over hand-built inputs whose full renders were snapshotted from the committed functions (SNAPSHOT, taken
2026-10-31 from the engine as it stood at 11:41, before plain.py). Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_plain.py -v
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import plain          # noqa: E402
import deal as deal_mod          # noqa: E402
import owed as owed_mod          # noqa: E402
import negotiation as neg_mod    # noqa: E402

NOW = '2026-10-31T12:17:18-07:00'
PLAYER, STEWARD = 'person:player', 'person:steward'
HEX12 = re.compile(r'[0-9a-f]{12}')
TOKEN = re.compile(r'\b(person|agent):')
COLOR = re.compile(r'\b(green|yellow|orange|red|grey)\b')
KIT = ('receipt', 'holon', 'round', 'converge', 'effort', 'pain', 'performing', 'ratify', 'sighting',
       'pulse', 'promise', 'house', ' hq', 'estate')
CONTRACTIONS = ("I'd", "I'll", "you'd", "don't", "can't", "won't", "isn't", "it's", "we'll", "you'll")
QUOTED = re.compile(r'"[^"]*"')

# Inputs and the full renders the committed functions gave for them (deal.render, deal.render_paper,
# owed.render_waiting, negotiation.render), taken before plain.py by loading the 11:41 copy of each module.
NEG_EMPTY = ('# The conversations for action\n\n## Waiting on\n\nNothing waits on another.\n\n## Owed by you: to answer'
             '\n\nNothing is yours to answer.\n\n## Owed by you: to do\n\nNothing agreed is yours to do.\n')
NEG_SIT = ('# The conversations for action\n\n## Waiting on\n\n- **Sit** (declined; round 0; asks effort not said): '
           'waiting on no one.\n\n## Owed by you: to answer\n\nNothing is yours to answer.\n\n## Owed by you: to do'
           '\n\nNothing agreed is yours to do.\n')
SNAPSHOT = json.loads('{"ASKS": [{"asker": "person:player", "by": "2026-11-06", "effort": 1, "id": "w1", "moves": [{"move": "accept"}], "owed": [{"by": "person:steward", "to": "do"}], "parties": ["person:steward"], "round": 1, "shape": "converge", "state": "agreed", "terms": {"time": "2026-11-05T18:00"}, "title": "Meet this week"}, {"asker": "person:player", "id": "w2", "moves": [], "owed": [{"by": "person:steward", "to": "answer"}], "parties": ["person:steward"], "round": 0, "state": "open", "title": "When is it"}, {"asker": "person:steward", "by": "2026-11-02", "id": "w3", "moves": [{"move": "accept"}], "owed": [{"by": "person:player", "to": "do"}], "parties": ["person:player"], "round": 0, "state": "performing", "terms": {"by": "2026-11-02", "minutes": 30}, "title": "Bring the plan"}, {"asker": "person:steward", "cannot_resolve": "no stewards", "id": "w4", "moves": [], "owed": [{"by": "person:player", "to": "answer"}], "parties": ["person:player"], "round": 0, "state": "open", "title": "Hold the door", "why": "the wind"}], "DEAL": {"actor": "person:player", "beyond": {"count": 2, "minutes": 45}, "cards": [{"because": "the river circle sent it to you", "holon": "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd", "holon_name": "the river circle", "id": "q1", "kind": "question", "minutes": 10.0, "n": 1, "options": ["Decide it here", "Ask for more first", "Pass it to the wider circle"], "question": "A decision for you: \\"the hall is shared\\"", "recommendation": "Decide it here", "rose": true, "section": "decision", "sender": {"from": "person:steward", "said": "In their own words."}, "unlocks": "the river circle can move", "why": "asked of you"}, {"holon": "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd", "holon_name": "the river circle", "id": "receipt:x", "kind": "receipt", "minutes": 1.0, "n": 2, "of": "x", "options": ["Ask again", "Let it go"], "question": "No Receipt yet from person:steward for \\"When is it\\", 3 days.", "recommendation": "Ask again", "section": "owed", "stopped": {"by": "person:steward"}, "to": "person:steward", "unlocks": "you know whether it reached person:steward", "why": "it crossed 3 days ago"}, {"by": "2026-11-02", "eyebrow": "On the critical path", "holon": "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd", "holon_name": "the river circle", "id": "r1", "kind": "activity", "minutes": 23.0, "n": 3, "options": ["Do it now", "Hand it to someone else", "Not this week: release it"], "question": "\\"Sweep the hall\\" is yours. Do it now? (23 min)", "recommendation": "Do it now", "section": "ready", "unlocks": "nothing waits on it yet", "whole_waits": true, "why": "nothing near-critical waits on it yet"}], "generated_at": "2026-10-31T12:00:00-07:00", "minutes_available": 60, "minutes_dealt": 34, "owed_to_you": [{"holder": "person:steward", "title": "Bring chairs"}], "proposals": 1, "question": "What did we miss that matters to you most?", "stopped": {"line": "Your agent is stopped in one place."}}, "WAIT": {"actor": "person:player", "as_of": "2026-10-31T12:00:00-07:00", "asks": [{"by": "2026-11-06", "id": "w1", "kind": "request", "recipients": [{"since": "2026-10-20T10:18:00-07:00", "state": "answered", "to": "person:steward", "words": "answered"}], "title": "Meet this week", "ts": "2026-10-20T10:00:00-07:00"}, {"id": "w2", "kind": "message", "recipients": [{"since": null, "state": "no_receipt", "to": "person:steward", "words": "no Receipt yet"}], "title": "When is it", "ts": "2026-10-28T10:00:00-07:00"}], "basis": "2 open asks this person started"}, "asks_none": "# The conversations for action\\n\\n## Waiting on\\n\\n- **Meet this week** (agreed; round 1; converge; by 2026-11-06; asks 1 minute): waiting on person:steward to do.\\n  - agreed: {\\"time\\":\\"2026-11-05T18:00\\"}\\n- **When is it** (open; round 0; asks effort not said): waiting on person:steward to answer.\\n- **Bring the plan** (performing; round 0; by 2026-11-02; asks effort not said): waiting on person:player to do.\\n  - agreed: {\\"by\\":\\"2026-11-02\\",\\"minutes\\":30}\\n- **Hold the door** (open; round 0; asks effort not said): waiting on person:player to answer.\\n  - cannot resolve: no stewards\\n", "asks_player": "# The conversations for action\\n\\n## Waiting on\\n\\n- **Meet this week** (agreed; round 1; converge; by 2026-11-06; asks 1 minute): waiting on person:steward to do.\\n  - agreed: {\\"time\\":\\"2026-11-05T18:00\\"}\\n- **When is it** (open; round 0; asks effort not said): waiting on person:steward to answer.\\n\\n## Owed by you: to answer\\n\\n- **Hold the door** (open; round 0; asks effort not said), from person:steward. Why: the wind.\\n\\n## Owed by you: to do\\n\\n- **Bring the plan** (performing; round 0; by 2026-11-02; asks effort not said), for person:steward.\\n  - agreed: {\\"by\\":\\"2026-11-02\\",\\"minutes\\":30}\\n", "asks_steward": "# The conversations for action\\n\\n## Waiting on\\n\\n- **Bring the plan** (performing; round 0; by 2026-11-02; asks effort not said): waiting on person:player to do.\\n  - agreed: {\\"by\\":\\"2026-11-02\\",\\"minutes\\":30}\\n- **Hold the door** (open; round 0; asks effort not said): waiting on person:player to answer.\\n  - cannot resolve: no stewards\\n\\n## Owed by you: to answer\\n\\n- **When is it** (open; round 0; asks effort not said), from person:player.\\n\\n## Owed by you: to do\\n\\n- **Meet this week** (agreed; round 1; converge; by 2026-11-06; asks 1 minute), for person:player.\\n  - agreed: {\\"time\\":\\"2026-11-05T18:00\\"}\\n", "deal": "Here\'s the deal.\\n\\nThis one rose to the top.\\n\\n1. A decision for you: \\"the hall is shared\\"  [the river circle · 10 min]\\n   a) Decide it here   b) Ask for more first   c) Pass it to the wider circle\\n   I would choose a: asked of you; the river circle sent it to you.\\n   Answering: the river circle can move.\\n   In their own words.\\n\\nThis one is waiting on you.\\n\\n2. No Receipt yet from person:steward for \\"When is it\\", 3 days.  [the river circle · 1 min]\\n   a) Ask again   b) Let it go\\n   I would choose a: it crossed 3 days ago.\\n   Answering: you know whether it reached person:steward.\\n   Your agent is stopped here; its acts wait for the lift.\\n\\nThis fits the time you have.\\n\\n   On the critical path\\n3. \\"Sweep the hall\\" is yours. Do it now? (23 min)  [the river circle · 23 min]\\n   a) Do it now   b) Hand it to someone else   c) Not this week: release it\\n   I would choose a: nothing near-critical waits on it yet.\\n   Answering: nothing waits on it yet.\\n   The whole is waiting on this.\\n\\nTwo more can wait (45 min); they stay in the list.\\nYour agent is stopped in one place.\\nOwed to you: 1, the oldest \\"Bring chairs\\" from person:steward.\\nOne agent proposal from text it read waits for a person; not dealt.\\n\\nLast: What did we miss that matters to you most?\\n\\n*34 min of 1h 00m dealt.*\\n", "empty_deal": "Here\'s the deal.\\n\\nNothing needs you right now.\\n\\nLast: What did we miss that matters to you most?\\n\\n*0 min of 0 min dealt.*\\n", "empty_paper": "THE DEAL ·  ·  · 0 min\\n================================================================\\n\\n[ ] What did we miss that matters to you most?\\n    ________________________________________________________\\n    ________________________________________________________\\n\\nSigned: ________________   Witness: ________________   Date: ________\\n", "paper": "THE DEAL · 2026-10-31 · person:player · 1h 00m\\n================================================================\\n\\n1. A decision for you: \\"the hall is shared\\"\\n   (the river circle · 10 min)\\n   [ ] Decide it here  <- recommended\\n   [ ] Ask for more first\\n   [ ] Pass it to the wider circle\\n   Why: asked of you.\\n   Note: ______________________________________________\\n\\n2. No Receipt yet from person:steward for \\"When is it\\", 3 days.\\n   (the river circle · 1 min)\\n   [ ] Ask again  <- recommended\\n   [ ] Let it go\\n   Why: it crossed 3 days ago.\\n   Note: ______________________________________________\\n\\n3. \\"Sweep the hall\\" is yours. Do it now? (23 min)\\n   (the river circle · 23 min)\\n   [ ] Do it now  <- recommended\\n   [ ] Hand it to someone else\\n   [ ] Not this week: release it\\n   Why: nothing near-critical waits on it yet.\\n   Note: ______________________________________________\\n\\n[ ] What did we miss that matters to you most?\\n    ________________________________________________________\\n    ________________________________________________________\\n\\nSigned: ________________   Witness: ________________   Date: ________\\n", "waiting": "# Waiting on — person:player\\n\\n*As of 2026-10-31T12:00:00-07:00. 2 open asks this person started.*\\n\\n- **request** · Meet this week · by 2026-11-06\\n  - person:steward: answered since 2026-10-20T10:18:00-07:00\\n- **message** · When is it\\n  - person:steward: no Receipt yet\\n"}')


def unquoted(s):
    """A sentence without its quoted titles: titles are the record's data, not the kit's words."""
    return QUOTED.sub('""', s)


def without_plain(fn, *a, **kw):
    """Call a render with plain.py unimportable: what it gives then is the render with no plain lines."""
    saved = sys.modules.get('plain')
    sys.modules['plain'] = None
    try:
        return fn(*a, **kw)
    finally:
        if saved is not None:
            sys.modules['plain'] = saved
        else:
            sys.modules.pop('plain', None)


def subsequence(small, big):
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def no_ids(test, text, label=''):
    test.assertIsNone(HEX12.search(text), (label, text))
    test.assertIsNone(TOKEN.search(text), (label, text))


class Snapshot(unittest.TestCase):
    """Law 4: depth="full" leaves each render as the committed functions gave it (SNAPSHOT, taken from them)."""

    def test_deal_full_is_the_snapshot_below_the_plain_lines(self):
        d = copy.deepcopy(SNAPSHOT['DEAL'])
        for fn, head, key in ((deal_mod.render, 2, 'deal'), (deal_mod.render_paper, 3, 'paper')):
            full = fn(d).split('\n')
            hand = plain.hand_lines(d, paper=fn is deal_mod.render_paper)
            self.assertEqual(full[:head], SNAPSHOT[key].split('\n')[:head])
            self.assertEqual(full[head:head + len(hand)], hand)
            self.assertEqual(full[head + len(hand):head + len(hand) + 3], ['', plain.MORE, ''])
            self.assertEqual('\n'.join(full[:head] + full[head + len(hand) + 3:]), SNAPSHOT[key])
            self.assertEqual(fn(d, depth='full'), fn(d))
            self.assertEqual(without_plain(fn, d), SNAPSHOT[key])
        self.assertEqual(deal_mod.render({}), SNAPSHOT['empty_deal'])            # one empty wording, once
        self.assertEqual(deal_mod.render_paper({}), SNAPSHOT['empty_paper'])

    def test_waiting_and_the_asks_full_are_the_snapshot(self):
        self.assertEqual(owed_mod.render_waiting(copy.deepcopy(SNAPSHOT['WAIT'])), SNAPSHOT['waiting'])
        self.assertEqual(owed_mod.render_waiting(copy.deepcopy(SNAPSHOT['WAIT']), depth='full'), SNAPSHOT['waiting'])
        for who, key in ((None, 'asks_none'), (PLAYER, 'asks_player'), (STEWARD, 'asks_steward')):
            self.assertEqual(neg_mod.render(copy.deepcopy(SNAPSHOT['ASKS']), who), SNAPSHOT[key])
            self.assertEqual(neg_mod.render(copy.deepcopy(SNAPSHOT['ASKS']), who, depth='full'), SNAPSHOT[key])

    def test_empty_asks_full_is_the_snapshot(self):
        self.assertEqual(neg_mod.render([], PLAYER), NEG_EMPTY)
        sit = [{'id': 'z1', 'title': 'Sit', 'state': 'declined', 'round': 0, 'asker': PLAYER,
                'parties': [STEWARD], 'moves': [1], 'owed': []}]
        self.assertEqual(neg_mod.render(sit, PLAYER), NEG_SIT)

    def test_a_card_on_an_ask_already_agreed_is_left_out_and_said(self):
        d = {'actor': PLAYER, 'cards': [
            {'n': 1, 'section': 'owed', 'kind': 'request', 'id': 'k1', 'holon': 'h', 'holon_name': 'the hall',
             'question': 'someone asks: "Lend the ladder". Your answer?', 'options': ['Accept it', 'Decline'],
             'recommendation': 'Accept it', 'why': 'w', 'unlocks': 'u', 'minutes': 5}]}
        asks = [{'id': 'k1', 'title': 'Lend the ladder', 'state': 'agreed', 'moves': [1], 'asker': STEWARD,
                 'owed': [{'by': 'person:other', 'to': 'do'}]}]
        said = []
        self.assertEqual(plain.deal_steps(d, {'reader': PLAYER, 'asks': asks}, said=said), [])
        self.assertTrue([x for x in said if 'Lend the ladder' in x and 'already agreed' in x], said)
        self.assertEqual(plain.hand_lines(d, {'reader': PLAYER, 'asks': asks}), [plain.EMPTY_NEXT])
        self.assertEqual(len(plain.deal_steps(d, {'reader': PLAYER})), 1)            # no asks given: dealt as it is

    def test_the_snapshot_inputs_in_plain(self):
        a, w, d = SNAPSHOT['ASKS'], SNAPSHOT['WAIT'], SNAPSHOT['DEAL']
        names = {'reader': PLAYER, 'holons': {'cd' * 32: 'the river circle'}, 'asks': a}
        mine = neg_mod.render(a, PLAYER, 'plain', names, w)
        self.assertIn('"Meet this week" eleven days ago; agreed; they still have to do it.', mine)
        self.assertIn('Yours to answer: "Hold the door" from the steward; %s.' % plain.HOW_VOICE, mine)
        self.assertIn('Yours to do: "Bring the plan" for the steward, by 2 November, about thirty minutes; %s.'
                      % plain.HOW_DONE, mine)
        self.assertNotIn(plain.NOTHING_TO_ANSWER, mine)
        stew = neg_mod.render(a, STEWARD, 'plain', dict(names, reader=STEWARD), w)     # the player's waiting is not the steward's
        self.assertIn('Yours to do: "Meet this week" for the player', stew)
        self.assertNotIn('You asked you', stew)
        self.assertIn('You asked the player "Bring the plan"; agreed; they are doing it.', stew)
        self.assertIn('agreed; they still have to do it', owed_mod.render_waiting(w, 'plain', names, a))
        self.assertIn('"Meet this week" eleven days ago; they have answered.', owed_mod.render_waiting(w, 'plain', names))
        p = deal_mod.render(d, 'plain', names)
        for text in (p, deal_mod.render_paper(d, 'plain', names), mine):
            no_ids(self, text)
        self.assertIn('Your agent is stopped here', p)
        self.assertNotIn('Signed', deal_mod.render_paper(d, 'plain', names))
        self.assertEqual(plain.hand_lines({'cards': [], 'beyond': {'count': 2}}), [plain.EMPTY_NOTHING_FITS])


class OnTheFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = os.path.join(ENGINE, 'fixtures', 'hq')
        if not os.path.isdir(src):
            raise unittest.SkipTest('no fixtures/hq beside the engine')
        try:
            import engine  # noqa: F401
        except SystemExit as e:
            raise unittest.SkipTest(str(e))
        cls.tmp = tempfile.mkdtemp()
        cls.hq = os.path.join(cls.tmp, 'hq')
        shutil.copytree(src, cls.hq)
        cls.r = plain.three(cls.hq, PLAYER, NOW, minutes=60)
        cls.s = plain.three(cls.hq, STEWARD, NOW, minutes=60)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'tmp', ''), ignore_errors=True)

    def sentences(self, r=None):
        r = r or self.r
        return [x['sentence'] for k in ('connected', 'next', 'waiting') for x in r[k]]

    def surfaces(self, r=None, who=PLAYER):
        r = r or self.r
        src, n = r['source'], r['names']
        return {'three': plain.render(r), 'deal': deal_mod.render(src['deal'], 'plain', n),
                'paper': deal_mod.render_paper(src['deal'], 'plain', n),
                'waiting': owed_mod.render_waiting(src['waiting'], 'plain', n, src['asks']),
                'asks': neg_mod.render(src['asks'], who, 'plain', n, src['waiting'])}

    # the shape, and the amendment: the second answer is the wise right next steps
    def test_the_three_answers_are_there(self):
        r = self.r
        self.assertEqual(set(r['summary']), {'connected', 'next', 'owed', 'waiting'})
        self.assertNotIn('do', r)
        self.assertTrue(r['connected'] and r['next'] and r['waiting'])
        self.assertEqual(r['summary']['next'], len(r['next']))
        self.assertIsInstance(r['summary']['owed'], int)
        for x in r['next']:
            self.assertTrue(x['sentence'].startswith('Next: I would '), x['sentence'])
            self.assertIn(', because ', x['sentence'])
            self.assertIn('; %s.' % x['how'], x['sentence'])

    def test_next_steps_keep_the_deal_order_and_the_deal_lists_the_same(self):
        for r in (self.r, self.s):
            ids = [c['id'] for c in r['source']['deal']['cards']]
            got = [x['id'] for x in r['next']]
            self.assertEqual([i for i in ids if i in got], got)
            lines = [l for l in deal_mod.render(r['source']['deal'], 'plain', r['names']).splitlines()
                     if re.match(r'^\d+\. Next: ', l)]
            self.assertEqual([re.sub(r'^\d+\. ', '', re.sub(r' \([^()]*\)$', '', l)) for l in lines],
                             [x['sentence'] for x in r['next']])

    def test_the_why_reads_what_it_unlocks(self):
        q = [x for x in self.r['next'] if x['kind'] == 'question'][0]
        self.assertIn('because then first-cell can move', q['sentence'])

    # law 1: a name, never an id
    def test_no_id_and_no_actor_token_in_any_plain_surface(self):
        for r, who in ((self.r, PLAYER), (self.s, STEWARD)):
            for s in self.sentences(r):
                no_ids(self, s)
            for name, text in self.surfaces(r, who).items():
                no_ids(self, text, name)

    def test_a_planted_id_never_reaches_a_plain_line(self):
        planted = ' person:steward ' + 'e' * 64 + ' agent:steward-aide ' + 'AB' * 6
        st = copy.deepcopy(self.r['source'])
        for a in st['asks']:
            a['title'] = (a.get('title') or '') + planted
        for a in st['waiting']['asks']:
            a['title'] = (a.get('title') or '') + planted
        for row in st['connections']['rows']:
            row['name'] = 'circle' + planted
        for c in st['deal']['cards']:
            c['question'] = c['question'].replace('"', '') + ' "x' + planted + '"'
            c['why'] = 'because' + planted
            c['unlocks'] = 'it moves' + planted
            c['holon_name'] = 'e' * 12
        r = plain.three(None, PLAYER, NOW, state=st)
        self.assertTrue(r['next'] and r['waiting'] and r['connected'])
        for text in [plain.render(r), plain.render(r, 'full').split(plain.MORE)[0]] + list(self.surfaces(r).values()):
            no_ids(self, text)
            self.assertNotIn('ABABABABABAB', text)

    def test_names_and_roles(self):
        text = plain.render(self.r)
        self.assertIn('first-cell', text)
        self.assertIn('the steward', text)
        self.assertIn('the player', plain.render(self.s))

    def test_the_home_is_named_when_the_reader_does_not_keep_it(self):
        for x in self.s['connected']:
            self.assertTrue(x['sentence'].startswith('player-hq is connected to '), x['sentence'])
        for x in self.r['connected']:
            self.assertTrue(x['sentence'].startswith('You are connected to '), x['sentence'])
        self.assertNotIn('your home', plain.render(self.s))

    def test_a_holon_with_no_name_is_a_group_and_said(self):
        said = []
        rows = plain.connected_entries({'rows': [{'holon': 'ab' * 32, 'name': None,
                                                  'pulse': {'color': 'green'}, 'condition': {}}]}, PLAYER, {}, said)
        self.assertEqual(rows[0]['name'], 'a group')
        self.assertIn('a group', rows[0]['sentence'])
        self.assertIn(plain.SAID_GROUP, said)
        self.assertEqual(plain.who('person:river-keeper'), 'the river keeper')
        self.assertEqual(plain.who(PLAYER, PLAYER), 'you')
        self.assertEqual(plain.who('agent:player-aide', PLAYER), 'your agent')
        self.assertEqual(plain.who('agent:other', PLAYER), 'their agent')
        self.assertEqual(plain.who('agent:x', 'steward'), 'their agent')                  # a reader with no colon
        self.assertEqual(plain.who('agent:player-aide', PLAYER, {'agents': {'agent:player-aide': STEWARD}}),
                         'their agent')                                                    # the directory wins

    # law 2: a color with its word; every next step with its how
    def test_every_color_carries_its_word(self):
        for s in self.sentences() + self.sentences(self.s):
            for m in COLOR.finditer(unquoted(s)):
                c = m.group(1)
                self.assertIn('%s: %s' % (c, plain.COLOR_WORDS[c]), s, s)
        for c in plain.COLOR_WORDS:
            self.assertEqual(plain.color_word(c), '%s: %s' % (c, plain.COLOR_WORDS[c]))
        self.assertEqual(plain.color_word(None), 'grey: they have not said')
        x = plain.next_step({'kind': 'body', 'question': 'x', 'why': 'the red line is near; more',
                             'options': ['Hold it until Monday', 'Close it now'], 'recommendation': 'Hold it until Monday'})
        self.assertFalse(plain._bare_color(unquoted(x['sentence'])), x['sentence'])

    def test_every_next_step_says_how_and_one_way_to_answer(self):
        for x in self.r['next'] + self.s['next']:
            self.assertEqual(x['how'], plain.HOW_VOICE)
            self.assertIn(x['how'], x['sentence'])
        for name, text in self.surfaces().items():
            if name != 'paper':
                self.assertNotIn(plain.HOW_PAPER, text)
        for line in deal_mod.render_paper(self.r['source']['deal'], 'plain', self.r['names']).splitlines():
            if 'Next:' in line:
                self.assertIn(plain.HOW_PAPER, line)
                self.assertNotIn(plain.HOW_VOICE, line)
        rel = plain.next_step({'kind': 'activity', 'section': 'ready', 'question': '"Sweep the hall" is yours.',
                               'options': ['Not this week: release it', 'Do it now'],
                               'recommendation': 'Not this week: release it', 'minutes': 5})
        self.assertEqual(rel['how'], plain.HOW_VOICE)

    def test_a_connection_not_well_says_how(self):
        text = plain.render(self.r)
        self.assertIn('To look closer, ask your agent what is wrong with first-cell.', text)
        self.assertEqual(plain.connection_do({'do': 'nothing to do'}), '')

    def test_yours_to_do_says_how(self):
        for r, who in ((self.r, PLAYER), (self.s, STEWARD)):
            for line in self.surfaces(r, who)['asks'].splitlines():
                if line.startswith('Yours to do:'):
                    self.assertTrue(line.endswith('; %s.' % plain.HOW_DONE), line)

    # law 3: one wording per ask across surfaces
    def test_the_same_ask_reads_the_same_words_everywhere(self):
        r = self.r
        sf = self.surfaces()
        self.assertTrue(r['waiting'])
        for x in r['waiting']:
            self.assertIn(x['sentence'], sf['waiting'])
            self.assertIn(x['sentence'], sf['asks'])
        meet = [x for x in r['waiting'] if 'Meet this week' in x['sentence']]
        self.assertEqual(len(meet), 1)
        self.assertEqual(meet[0]['words'], 'agreed; they still have to do it')
        line = [l for l in sf['waiting'].splitlines() if 'Meet this week' in l][0]
        self.assertNotIn(plain.WAIT_WORDS['answered'], line)

    def test_a_card_on_a_moved_ask_is_worded_from_its_state(self):
        self.assertFalse([x for x in self.r['next'] if x['kind'] == 'receipt' and 'Meet this week' in x['sentence']])
        self.assertTrue([s for s in self.r['said'] if 'already answered' in s])
        meet = [x for x in self.s['next'] if 'Meet this week' in x['sentence']]
        self.assertEqual(len(meet), 1)
        self.assertTrue(meet[0]['sentence'].startswith('Next: I would do "Meet this week to settle the venue" now'),
                        meet[0]['sentence'])
        self.assertIn('you agreed', meet[0]['sentence'])
        mine = [x for x in self.r['next'] if 'Bring the season plan' in x['sentence']][0]
        self.assertIn('you agreed, due 2 November', mine['sentence'])

    def test_ask_state_words(self):
        moved = {'state': 'agreed', 'moves': [{'move': 'accept'}], 'round': 1, 'owed': [{'by': STEWARD, 'to': 'do'}]}
        self.assertEqual(plain.ask_state_words(moved, 'answered'), 'agreed; they still have to do it')
        self.assertEqual(plain.ask_state_words(moved, 'answered', STEWARD), 'agreed; you still have to do it')
        self.assertEqual(plain.ask_state_words({'state': 'agreed', 'moves': [1]}), 'agreed')
        self.assertEqual(plain.ask_state_words({'state': 'open', 'moves': []}, 'no_receipt'),
                         plain.WAIT_WORDS['no_receipt'])
        self.assertEqual(plain.ask_state_words(None, {'recipients': [{'state': 'received'}, {'state': 'answered'}]}),
                         plain.WAIT_WORDS['received'])
        self.assertEqual(plain.ask_state_words({'state': 'open', 'moves': [1], 'answers': {'x': 'countered'}}),
                         plain.ANSWER_WORDS['countered'])
        for v in (None, {}, [], 3.5, 'nonsense', {'recipients': 'zz'}):
            self.assertIsInstance(plain.ask_state_words(v, v), str)

    def test_nothing_to_answer_only_when_nothing_waits_on_the_reader(self):
        mine = self.surfaces()['asks']
        self.assertIn('Yours to do: "Bring the season plan to the cell"', mine)
        self.assertNotIn(plain.NOTHING_TO_ANSWER, mine)
        self.assertNotIn('round', mine)
        self.assertNotIn('effort', mine)
        stew = self.surfaces(self.s, STEWARD)['asks']
        self.assertIn('Yours to answer:', stew)
        self.assertNotIn(plain.NOTHING_TO_ANSWER, stew)
        self.assertIn(plain.NOTHING_TO_ANSWER, neg_mod.render([], PLAYER, 'plain'))

    # law 4, on the fixtures: full is the render as it stood, below the plain lines
    def test_full_keeps_the_deal_and_the_paper_as_they_stood(self):
        d = self.r['source']['deal']
        for fn, head in ((deal_mod.render, 2), (deal_mod.render_paper, 3)):
            old = without_plain(fn, d).split('\n')
            full = fn(d).split('\n')
            hand = plain.hand_lines(d, paper=fn is deal_mod.render_paper)
            self.assertTrue(subsequence(old, full))
            self.assertEqual(full[:head] + full[head + len(hand) + 3:], old)
        self.assertTrue(deal_mod.render(d).startswith("Here's the deal."))
        self.assertNotIn('Answering:', deal_mod.render(d, 'plain'))
        self.assertIn('Answering:', deal_mod.render(d).split(plain.MORE)[1])

    def test_a_failing_plain_line_falls_back_to_the_full_render(self):
        d = self.r['source']['deal']
        saved = plain.hand_lines

        def boom(*a, **kw):
            raise IndexError('planted')
        plain.hand_lines = boom
        try:
            got, paper = deal_mod.render(d, 'plain'), deal_mod.render_paper(d, 'plain')
        finally:
            plain.hand_lines = saved
        self.assertEqual(got, without_plain(deal_mod.render, d))
        self.assertEqual(paper, without_plain(deal_mod.render_paper, d))
        self.assertNotIn(plain.EMPTY_NEXT, got)

    def test_render_plain_and_full(self):
        p = plain.render(self.r)
        self.assertNotIn(plain.MORE, p)
        self.assertNotIn('|', p)
        f = plain.render(self.r, 'full')
        self.assertTrue(f.startswith(p))
        for part in (plain.MORE, '# Connections', "Here's the deal.", '# Waiting on', '# The conversations for action'):
            self.assertIn(part, f)
        self.assertEqual(f.count(plain.MORE), 1)
        self.assertNotIn('Signed', deal_mod.render_paper(self.r['source']['deal'], 'plain', self.r['names']))

    # law 5: honest-empty and null-guards
    def test_the_empty_words(self):
        self.assertEqual(plain.EMPTY_CONNECTED, 'You are not connected to anyone yet.')
        self.assertEqual(plain.EMPTY_NEXT, 'Nothing to do.')
        self.assertEqual(plain.EMPTY_WAITING, 'Waiting on no one.')
        self.assertEqual(plain.NOTHING_TO_ANSWER, 'Nothing is yours to answer.')
        self.assertEqual(plain.render(plain.three(None, PLAYER)),
                         'You are not connected to anyone yet.\n\nNothing to do.\n\nWaiting on no one.\n')

    def test_honest_empty(self):
        for home in (None, {}, [], 3.5, '', os.path.join(self.tmp, 'nowhere')):
            r = plain.three(home, PLAYER, NOW)
            self.assertEqual(r['summary'], {'connected': 0, 'next': 0, 'owed': 0, 'waiting': 0})
            self.assertTrue(r['said'])
        for actor in (None, '', 'agent:player-aide', 3.5, {}):
            self.assertIn('no person named', ' '.join(plain.three(self.hq, actor, NOW)['said']))
        link = os.path.join(self.tmp, 'link')
        if not os.path.lexists(link):
            os.symlink(self.hq, link)
        self.assertIn('no home folder', ' '.join(plain.three(link, PLAYER, NOW)['said']))
        self.assertTrue(plain.three(self.hq, PLAYER, 1.5)['as_of'])          # a float moment reads the clock
        self.assertEqual(plain.three(None, PLAYER, 1.5, state=3.5)['summary']['next'], 0)
        empty = plain.EMPTY_CONNECTED + '\n\n' + plain.EMPTY_NEXT + '\n\n' + plain.EMPTY_WAITING + '\n'
        for v in (None, {}, [], 3.5, 5, {'connected': [{}]}, {'connected': 5}, {'next': [{'sentence': None}]},
                  {'waiting': [3, None]}):
            self.assertEqual(plain.render(v), empty, v)
            self.assertIsInstance(plain.render(v, 'full'), str)
        for v in (None, {}, [], 3.5):
            self.assertEqual(plain.hand_lines(v), [plain.EMPTY_NEXT])
            self.assertEqual(plain.waiting_entries(v, v), [])
            self.assertEqual(plain.connected_entries(v), [])
            self.assertIn(plain.EMPTY_WAITING, plain.negotiation_lines(v, PLAYER))
            self.assertEqual(owed_mod.render_waiting(v, 'plain'), plain.EMPTY_WAITING + '\n')
            self.assertIn(plain.EMPTY_NEXT, deal_mod.render(v, 'plain'))
            self.assertIn(plain.EMPTY_NEXT, deal_mod.render_paper(v, 'plain'))
            self.assertIsInstance(neg_mod.render(v, v, 'plain'), str)
        self.assertEqual(owed_mod.render_waiting({'asks': [{'id': 'x', 'recipients': 'zz'}]}, 'plain', None, 'bad'),
                         plain.EMPTY_WAITING + '\n')

    def test_a_state_given_is_read_and_nothing_else(self):
        src = self.r['source']
        r = plain.three(None, PLAYER, NOW, state=src)
        self.assertEqual([x['sentence'] for x in r['next']], [x['sentence'] for x in self.r['next']])
        self.assertEqual([x['sentence'] for x in r['waiting']], [x['sentence'] for x in self.r['waiting']])

    # law 6: short, second person, the kit's words only as plain words
    def test_short_second_person_plain_words(self):
        for r in (self.r, self.s):
            for k, start in (('connected', ' connected to '), ('next', 'Next: I would '), ('waiting', 'You asked ')):
                for x in r[k]:
                    s = x['sentence']
                    self.assertLess(len(s.split()), 25, s)
                    self.assertTrue(s.startswith(start) or start in s, s)
                    low = unquoted(s).lower()
                    for w in KIT:
                        self.assertNotIn(w, low, s)
                    for c in CONTRACTIONS:
                        self.assertNotIn(c, s)
        for text in self.surfaces().values():
            body = text.replace("Here's the deal.", '')
            for c in CONTRACTIONS:
                self.assertNotIn(c, body)

    def test_deterministic(self):
        a = json.dumps(plain._public(plain.three(self.hq, PLAYER, NOW, minutes=60)), sort_keys=True)
        b = json.dumps(plain._public(plain.three(self.hq, PLAYER, NOW, minutes=60)), sort_keys=True)
        self.assertEqual(a, b)

    def test_the_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(plain._main([self.hq, PLAYER, '--now', NOW, '--json']), 0)
        got = json.loads(buf.getvalue())
        self.assertNotIn('source', got)
        self.assertTrue(got['next'])
        p = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'plain.py'), self.hq, PLAYER, '--now', NOW,
                            '--full'], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('Next: I would', p.stdout)
        self.assertIn(plain.MORE, p.stdout)


class Words(unittest.TestCase):
    def test_dates_and_spans(self):
        self.assertEqual(plain.date_words('2026-11-02'), '2 November')
        self.assertEqual(plain.date_words('2026-11-05T18:00'), '5 November')
        self.assertEqual(plain.date_words(3.5), '')
        t = plain.parse_time(NOW)
        self.assertEqual(plain.since_words('2026-10-20T10:00:00-07:00', t), 'eleven days ago')
        self.assertEqual(plain.since_words(NOW, t), 'today')
        self.assertEqual(plain.since_words(None, t), '')
        self.assertEqual(plain.minutes_words(30), 'about thirty minutes')
        for v in (None, 0, -3, float('nan'), float('inf'), 'x'):
            self.assertEqual(plain.minutes_words(v), '')

    def test_scrub(self):
        names = {'holons': {'cd' * 32: 'the river circle'}}
        s = plain.scrub('No word from person:steward for %s or %s or %s' % ('cd' * 32, 'ef' * 6 + '12', 'AB' * 6),
                        PLAYER, names)
        self.assertEqual(s, 'No word from the steward for the river circle or a group or a group')

    def test_long_titles_and_names_stay_under_25_words_and_keep_the_how(self):
        x = plain.next_step({'kind': 'ratify', 'section': 'decision', 'question': 'Confirm "%s"?' % ' '.join(['word'] * 40),
                             'options': ['Confirm'], 'recommendation': 'Confirm'})
        self.assertLess(len(x['sentence'].split()), 25)
        self.assertIn('…', x['sentence'])
        t0 = time.time()
        big = plain.next_step({'kind': 'ratify', 'question': 'Confirm "%s"?' % ('w ' * 40000), 'options': ['C'],
                               'recommendation': 'C'})
        self.assertLess(time.time() - t0, 2.0)
        self.assertLess(len(big['sentence'].split()), 25)
        self.assertLessEqual(len(big['step'].split()), plain.MAX_WORDS + 6)          # the title is cut first
        pain = plain.next_step({'kind': 'pain', 'holon': 'h1', 'holon_name': 'The ' + 'great ' * 20 + 'circle',
                                'question': '"Help"', 'options': ['Respond now'], 'recommendation': 'Respond now'})
        self.assertLess(len(pain['sentence'].split()), 25)
        self.assertTrue(pain['sentence'].endswith('; %s.' % plain.HOW_VOICE), pain['sentence'])
        c = plain.connected_entries({'rows': [{'holon': 'ab' * 32, 'name': 'The ' + 'very ' * 20 + 'long circle',
                                               'pulse': {'color': 'red'}, 'condition': {'color': 'yellow'}}]})[0]
        self.assertLess(len(c['sentence'].split()), 25)
        self.assertIn('red: stop and look', c['sentence'])
        w = plain.waiting_entries({'actor': 'person:p', 'asks': [{'id': 'x1', 'title': 'Short', 'recipients': [
            {'to': 'person:r%d' % i, 'state': 'no_receipt'} for i in range(12)]}]}, [])[0]
        self.assertLess(len(w['sentence'].split()), 25)
        self.assertIn('others', w['sentence'])
