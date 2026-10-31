"""test_ask_fields.py — the sender's word rides with the ask: why, effort and voice.

The fold fills `voice` on a new item; the Deal shows the sender's why, effort (in words), by and
voice on every risen ask and every owed request or offer card, sized by the effort; owed counts
effort and sums `minutes_asked`; `waiting_on` is the sender's side; a live stop withholds the acts
of the cards it binds. The fold tests build the signed sample fixtures (fixtures/make_fixtures.py)
once per run, as test_record does. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_ask_fields.py -v
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import deal as deal_mod      # noqa: E402
import owed as owed_mod      # noqa: E402
import record                # noqa: E402

NOW = '2026-10-31T12:00:00-07:00'
A, B = 'holon-home', 'holon-cell'
P, K, X, AG, XA = 'person:player', 'person:keeper', 'person:stranger', 'agent:aide', 'agent:xaide'
HOLONS = [{'id': A, 'name': 'Home', 'kind': 'person', 'keeper': P},
          {'id': B, 'name': 'The Cell', 'kind': 'cell', 'keeper': K}]
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def card(i, holon=B, title=None, minutes=10, holder=P, state='ready', actor=K, **kw):
    c = {'id': i, 'kind': 'card', 'holon': holon, 'title': title or f'Card {i}', 'minutes': minutes,
         'holder': holder, 'state': state, 'body_kind': 'activity', 'actor': actor, 'for': actor,
         'ts': '2026-10-30T09:00:00-07:00'}
    c.update(kw)
    return c


def ask(i, to=P, actor=K, **kw):
    """A request card as the fold makes it: holder and `to` from the line's body.to."""
    kw.setdefault('state', 'open')
    return card(i, holder=to if isinstance(to, str) else None, actor=actor, asked='request', to=to, **kw)


def line(i, typ, body, actor=K, holon=B, ts='2026-10-30T11:00:00-07:00', links=None, reason='human', for_=None):
    return {'v': 1, 'id': i, 'ts': ts, 'actor': actor, 'for': for_ or actor, 'holon': holon, 'type': typ,
            'body': body, 'links': links or {}, 'audience': 'holon', 'reason': reason, 'prev': '', 'sig': ''}


def items(*cards):
    return {'cards': list(cards), 'commitments': [], 'threads': [], 'sightings': [],
            'delegations': [{'id': 'g1', 'kind': 'delegation', 'holon': A, 'state': 'live', 'to': AG, 'actor': P,
                             'for': P, 'scope': ['claim', 'say', 'request'], 'holons': ['*'], 'until': '2026-12-31'}]}


def D(its, actor=P, lines=None, **kw):
    return deal_mod.deal(its, None, actor, 1000, now=NOW, holons=HOLONS, lines=lines, **kw)


def by_id(d):
    return {c['id']: c for c in d['cards'] + d['beyond']['cards']}


# ---------------------------------------------------------------- the fold fills voice

def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        return
    import make_fixtures
    WORK = tempfile.mkdtemp(prefix='lionsberg-ask-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the fixtures are signed')
class FoldFillsVoice(unittest.TestCase):
    CLOCK = '2026-10-24T12:00:00-07:00'

    def setUp(self):
        import make_fixtures
        self.mf = make_fixtures
        self.tmp = tempfile.mkdtemp(prefix='case-', dir=WORK)
        shutil.copytree(os.path.join(TEMPLATE, 'hq'), os.path.join(self.tmp, 'hq'))
        self.home = os.path.join(self.tmp, 'hq')
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.heads = {}
        for d in record.hold(self.home):
            r = record.read(d)
            for a, hs in r['heads'].items():
                self.heads[(r['holon'], a)] = hs[-1]

    def fold(self, extra=(), drop=()):
        r = record.read_all(self.home)
        ls = [l for l in r['lines'] if l['id'] not in drop] + list(extra)
        return record.fold(ls, record.load_types(), r['keepers'], clock=self.CLOCK)

    def mk(self, actor, typ, body, n, links=None):
        for_ = actor if actor.startswith('person:') else self.mf.PLAYER
        reason = 'human' if actor.startswith('person:') else 'delegated'
        ts = '2026-10-21T10:%02d:00-07:00' % n
        l = record.make_line(actor, for_, self.H, typ, body, links, reason=reason, ts=ts, salt='v%d' % n,
                             prev=self.heads.get((self.H, actor), ''))
        l['sig'] = record.sign_id(l['id'], record.find_key(None, actor, KEYS))
        self.heads[(self.H, actor)] = l['id']
        return l

    def item(self, f, coll, i):
        got = [x for x in f[coll] if x['id'] == i]
        self.assertTrue(got, f'no {coll} item for the line')
        return got[0]

    def test_a_persons_line_is_in_their_own_words(self):
        PLAYER, STEWARD = self.mf.PLAYER, self.mf.STEWARD
        r = self.mk(PLAYER, 'request', {'to': STEWARD, 'title': 'Bring the chairs', 'why': 'the hall opens at six',
                                         'effort': 20}, 1)
        c = self.item(self.fold([r]), 'cards', r['id'])
        self.assertEqual(c['voice'], 'human-words')
        self.assertEqual((c['why'], c['effort']), ('the hall opens at six', 20))
        self.assertNotIn('voice_claimed', c)

    def test_an_agents_line_is_the_agents_and_a_false_claim_is_overwritten_and_flagged(self):
        AIDE = self.mf.AIDE
        plain = self.mk(AIDE, 'say', {'text': 'The notes are up.'}, 2)
        claim = self.mk(AIDE, 'say', {'text': 'I will come.', 'voice': 'human-words'}, 3)
        f = self.fold([plain, claim])
        self.assertEqual(self.item(f, 'threads', plain['id'])['voice'], 'agent')
        t = self.item(f, 'threads', claim['id'])
        self.assertEqual((t['voice'], t['voice_claimed']), ('agent', 'human-words'))

    def test_an_agents_line_signed_at_the_persons_word_is_agent_drafted(self):
        PLAYER, AIDE, STEWARD = self.mf.PLAYER, self.mf.AIDE, self.mf.STEWARD
        od = self.mk(PLAYER, 'delegate', {'to': AIDE, 'scope': ['request'], 'holons': [self.H], 'once': True,
                                          'until': '2026-12-31'}, 4)
        r = self.mk(AIDE, 'request', {'to': STEWARD, 'title': 'Hold the room'}, 5)
        f = self.fold([od, r])
        c = self.item(f, 'cards', r['id'])
        self.assertTrue(c.get('signed_for'))
        self.assertEqual(c['voice'], 'agent-drafted')

    def test_a_stated_voice_is_kept(self):
        PLAYER = self.mf.PLAYER
        s = self.mk(PLAYER, 'say', {'text': 'My agent wrote this for me.', 'voice': 'agent-drafted'}, 6)
        self.assertEqual(self.item(self.fold([s]), 'threads', s['id'])['voice'], 'agent-drafted')

    def test_an_agents_false_claim_of_agent_drafted_or_under_mandate_is_overwritten_and_flagged(self):
        PLAYER, AIDE, STEWARD = self.mf.PLAYER, self.mf.AIDE, self.mf.STEWARD
        sd = self.mk(PLAYER, 'delegate', {'to': AIDE, 'scope': ['request'], 'holons': [self.H],
                                          'until': '2026-12-31'}, 9)        # standing: no person's word on the line
        drafted = self.mk(AIDE, 'request', {'to': STEWARD, 'title': 'Hold the hall', 'voice': 'agent-drafted'}, 10)
        mandate = self.mk(AIDE, 'say', {'text': 'Booked.', 'voice': 'under-mandate'}, 11)
        card_ = self.mk(AIDE, 'card', {'title': 'Set the hall', 'kind': 'activity', 'voice': 'agent-drafted'}, 12)
        f = self.fold([sd, drafted, mandate, card_])
        c = self.item(f, 'cards', drafted['id'])
        self.assertFalse(c.get('signed_for'))
        self.assertEqual((c['voice'], c['voice_claimed']), ('agent', 'agent-drafted'))
        c = self.item(f, 'cards', card_['id'])                     # a type that does not register voice
        self.assertEqual((c['voice'], c['voice_claimed']), ('agent', 'agent-drafted'))
        t = self.item(f, 'threads', mandate['id'])
        self.assertEqual((t['voice'], t['voice_claimed']), ('agent', 'under-mandate'))

    def test_an_agents_supported_claim_is_kept(self):
        PLAYER, AIDE, STEWARD = self.mf.PLAYER, self.mf.AIDE, self.mf.STEWARD
        od = self.mk(PLAYER, 'delegate', {'to': AIDE, 'scope': ['request'], 'holons': [self.H], 'once': True,
                                          'until': '2026-12-31'}, 13)
        r = self.mk(AIDE, 'request', {'to': STEWARD, 'title': 'Hold the room', 'voice': 'agent-drafted'}, 14)
        c = self.item(self.fold([od, r]), 'cards', r['id'])
        self.assertEqual(c['voice'], 'agent-drafted')
        self.assertNotIn('voice_claimed', c)
        mv = {'actor': AIDE, 'type': 'move', 'body': {'move': 'accept', 'voice': 'under-mandate'}}
        self.assertEqual(record.line_voice(mv, mandate=True), ('under-mandate', None))
        self.assertEqual(record.line_voice(mv, mandate=False), ('agent', 'under-mandate'))
        self.assertEqual(record.line_voice(dict(mv, body={'voice': 'agent-drafted'})), ('agent', 'agent-drafted'))
        self.assertEqual(record.line_voice(dict(mv, body={'voice': 'agent'}), signed_for=True), ('agent', None))

    def test_a_signed_line_the_fold_refused_is_not_counted(self):
        PLAYER, AIDE = self.mf.PLAYER, self.mf.AIDE
        r = self.mk(PLAYER, 'request', {'to': self.mf.STEWARD, 'title': 'Bring chairs'}, 15)
        bad = self.mk(AIDE, 'answer', {'answer': 'accept'}, 16, links={'answers': [r['id']]})
        f = self.fold([r, bad])
        self.assertEqual(f['trust'].get(bad['id']), 'signed')      # signed, and still refused by validity
        self.assertIn(bad['id'], {x['id'] for x in f['invalid']})
        self.assertNotIn(bad['id'], {l['id'] for l in owed_mod.trusted_lines(f, [r, bad])})
        self.assertEqual(deal_mod.trusted_lines(f, [r, bad]), owed_mod.trusted_lines(f, [r, bad]))

    def test_a_move_under_a_mandate(self):
        PLAYER, AIDE = self.mf.PLAYER, self.mf.AIDE
        dl = self.mk(PLAYER, 'delegate', {'to': AIDE, 'scope': ['move'], 'holons': [self.H], 'until': '2026-12-31',
                                          'mandate': {'days': ['tue', 'thu'], 'minutes': 60}}, 7)
        bare = self.mk(PLAYER, 'delegate', {'to': AIDE, 'scope': ['move'], 'holons': [self.H], 'until': '2026-12-31'}, 8)
        mv = self.mk(AIDE, 'move', {'move': 'accept', 'root': 'x' * 64}, 9)
        self.assertTrue(record._mandated(mv, record._delegations([dl]), {dl['id']: dl}))
        self.assertFalse(record._mandated(mv, record._delegations([bare]), {bare['id']: bare}))
        self.assertEqual(record.line_voice(mv, mandate=True), ('under-mandate', None))
        self.assertEqual(record.line_voice(mv, mandate=False), ('agent', None))
        self.assertEqual(record.line_voice(dict(mv, type='say'), mandate=True), ('agent', None))   # moves only
        self.assertEqual(record.line_voice(mv, signed_for=True, mandate=True), ('agent-drafted', None))

    def test_a_stop_withholds_the_agents_acts_and_its_lift_frees_them(self):
        PLAYER = self.mf.PLAYER

        def dealt(f):
            f['cards'].append(card('in-cell', holon=self.C, holder=PLAYER, actor=PLAYER, title='Set the hall'))
            f['cards'].append(card('at-home', holon=self.H, holder=PLAYER, actor=PLAYER, title='Rest'))
            return deal_mod.deal(f, None, PLAYER, 1000, now=self.CLOCK, fold=f)

        d = dealt(self.fold(drop={IDS['lift']}))
        cs = by_id(d)
        self.assertEqual(cs['in-cell']['acts'], [])
        self.assertEqual(cs['in-cell']['stopped']['stop'], IDS['stop'])
        self.assertEqual(cs['in-cell']['stopped']['by'], self.mf.STEWARD)
        self.assertTrue(cs['in-cell']['stopped']['why'])
        self.assertNotIn('stopped', cs['at-home'])                  # outside the stop's holon
        self.assertTrue(d['stopped']['line'].startswith('Your agent is stopped'))
        self.assertIn('stopped', deal_mod.render(d))
        lifted = dealt(self.fold())
        self.assertNotIn('stopped', by_id(lifted)['in-cell'])
        self.assertEqual((lifted['stopped']['count'], lifted['stopped']['line']), (0, ''))


# ---------------------------------------------------------------- the Deal shows the sender's word

class TheDealShowsTheSendersWord(unittest.TestCase):
    def test_a_risen_ask_carries_why_effort_by_and_voice_and_its_minutes_are_the_effort(self):
        d = D(items(ask('r1', why='the hall opens at six.', effort=20, voice='human-words', by='2026-11-02')))
        c = d['cards'][0]
        self.assertEqual((c['id'], c['rose']), ('r1', True))
        s = c['sender']
        self.assertEqual((s['why'], s['effort'], s['effort_words'], s['by'], s['voice_words'], s['from']),
                         ('the hall opens at six', 20, 'about twenty minutes', '2026-11-02', 'in their own words', K))
        self.assertEqual(s['missing'], [])
        self.assertEqual(c['minutes'], 20.0)
        self.assertIn('Why: the hall opens at six.', c['question'])
        self.assertTrue(c['question'].endswith('Your answer?'))
        self.assertEqual(c['why'], 'asked of you')                  # the dealer's reason stays its own
        self.assertIn('In their own words; about twenty minutes', deal_mod.render(d))

    def test_honest_empty_when_the_sender_said_nothing(self):
        c = D(items(ask('r2')))['cards'][0]
        self.assertEqual(c['sender']['missing'], ['why', 'effort', 'by', 'voice'])
        self.assertEqual(c['sender']['said'], '')
        self.assertEqual(c['minutes'], float(owed_mod.MINUTES['request']))
        self.assertNotIn('Why:', c['question'])

    def test_the_voices_in_words(self):
        for v, w in (('agent-drafted', 'drafted by their agent'), ('under-mandate', 'their agent, within a mandate'),
                     ('agent', "their agent's words"), ('loud', None)):
            self.assertEqual(deal_mod.sender_word({'voice': v})['voice_words'], w)

    def test_effort_in_words(self):
        for m, w in ((1, 'one minute'), (5, 'five minutes'), (10, 'ten minutes'), (20, 'about twenty minutes'),
                     (23, 'about twenty-five minutes'), (58, 'about an hour'), (90, 'about an hour and a half'),
                     (120, 'about two hours'), (150, 'about two and a half hours')):
            self.assertEqual(deal_mod.effort_words(m), w, m)
        for m in (0, -3, None, 2.5, True, '20', float('nan')):
            self.assertIsNone(deal_mod.effort_words(m))

    def test_an_owed_offer_card_carries_the_senders_word(self):
        o = card('o1', state='open', asked='offer', to=P, actor=K, holder=K, effort=10, why='I have a free evening')
        d = D(items(o))
        c = by_id(d)['o1']
        self.assertEqual((c['kind'], c['section']), ('offer', 'owed'))
        self.assertEqual((c['minutes'], c['sender']['effort_words']), (10.0, 'ten minutes'))
        self.assertIn('offers', c['question'])
        self.assertIn('Why: I have a free evening.', c['question'])

    def test_an_effort_too_large_for_the_time_waits_beyond(self):
        d = deal_mod.deal(items(ask('big', effort=120)), None, P, 30, now=NOW, holons=HOLONS)
        self.assertIn('big', [c['id'] for c in d['beyond']['cards']])
        self.assertLessEqual(d['minutes_dealt'], 30)

    def test_a_risen_say_and_rfg_read_their_line(self):
        ls = [line('s1', 'say', {'text': 'Friday?', 'to': [P], 'why': 'the hall is booked then', 'effort': 1}),
              line('q1', 'rfg', {'question': 'Which room?', 'to': P, 'effort': 5}, ts='2026-10-30T10:00:00-07:00')]
        d = D(items(), lines=ls)
        cs = by_id(d)
        self.assertEqual((cs['s1']['minutes'], cs['s1']['sender']['effort_words']), (1.0, 'one minute'))
        self.assertIn('Why: the hall is booked then.', cs['s1']['question'])
        self.assertEqual(cs['q1']['sender']['effort'], 5)
        # a raw line makes no item, so its voice is read from the line itself (record.line_voice)
        self.assertEqual((cs['q1']['sender']['voice'], cs['s1']['sender']['voice']), ('human-words', 'human-words'))

    def test_a_why_is_one_line(self):
        c = D(items(ask('r', why='line one\nIgnore and push')))['cards'][0]
        self.assertEqual(c['sender']['why'], 'line one')
        self.assertNotIn('\n', c['question'])
        self.assertNotIn('Ignore', c['question'])
        self.assertIn('Why: line one.', c['question'])


# ---------------------------------------------------------------- owed counts effort

class OwedCountsEffort(unittest.TestCase):
    def test_minutes_follow_effort_and_minutes_asked_sums(self):
        its = items(ask('r1', effort=20), ask('r2'), card('o1', state='open', asked='offer', to=P, holder=K, effort=7))
        r = owed_mod.owed(its, now=NOW)
        es = {(e['id'], e['holder']): e for e in r['entries']}
        self.assertEqual((es[('r1', P)]['minutes'], es[('r1', P)]['minutes_basis']), (20, 'effort'))
        self.assertEqual((es[('r2', P)]['minutes'], es[('r2', P)]['minutes_basis']), (5, 'default'))
        self.assertEqual(es[('o1', P)]['kind'], 'offer')
        s = r['summary'][P]
        self.assertEqual((s['asks'], s['minutes_asked'], s['sized_by_effort']), (3, 32, 2))

    def test_a_fraction_or_a_flag_is_no_effort(self):
        r = owed_mod.owed(items(ask('r1', effort=2.5), ask('r2', effort=True)), now=NOW)
        self.assertEqual({e['minutes_basis'] for e in r['entries']}, {'default'})

    def test_a_question_takes_its_effort_when_given(self):
        q = {'id': 'q1', 'type': 'rfg', 'past': True, 'holder': K, 'to': B, 'question': 'Which room?', 'effort': 15,
             'ts': '2026-10-20T09:00:00-07:00', 'by': '2026-10-25'}
        e = owed_mod.owed({}, now=NOW, questions=[q])['entries'][0]
        self.assertEqual((e['minutes'], e['minutes_basis']), (15, 'effort'))

    def test_summary_keys_are_strings(self):
        r = owed_mod.owed({'requests': [{'id': 'rq', 'kind': 'request', 'state': 'open', 'holon': B,
                                         'ts': '2026-10-30T09:00:00-07:00'}]}, now=NOW)
        self.assertEqual(list(r['summary']), [''])
        json.dumps(r, sort_keys=True)


# ---------------------------------------------------------------- waiting on: the sender's side

def sent():
    w1 = ask('w1', to=[K, X], actor=P, receipts=[{'id': 'rc1', 'type': 'receive', 'actor': XA, 'ts': '2026-10-30T10:00:00-07:00', 'how': 'pull'},
                                               {'id': 'rc2', 'type': 'receive', 'actor': K, 'ts': '2026-10-30T10:05:00-07:00', 'how': 'pull'}],
             why='the hall needs both of you', effort=15)
    w2 = ask('w2', to=K, actor=P)
    w3 = ask('w3', to=X, actor=AG, **{'for': P})
    done = ask('w4', to=K, actor=P, state='taken')                      # moved on: not open, not listed
    other = ask('w5', to=P, actor=K)                                     # asked of P, not by P
    its = items(w1, w2, w3, done, other)
    ls = [line('rc1', 'receive', {'of': 'w1', 'how': 'pull'}, actor=XA, for_=X, links={'answers': ['w1']},
               ts='2026-10-30T10:00:00-07:00'),
          line('m1', 'move', {'move': 'clarify', 'root': 'w1', 'text': 'Which door?'}, actor=X,
               links={'answers': ['w1']}, ts='2026-10-30T10:30:00-07:00'),
          line('a2', 'answer', {'answer': 'accept'}, actor=K, links={'answers': ['w2']}, ts='2026-10-30T11:00:00-07:00'),
          line('u1', 'move', {'move': 'accept', 'root': 'w3'}, actor=X, reason='untrusted', ts='2026-10-30T11:30:00-07:00')]
    return its, ls


class WaitingOn(unittest.TestCase):
    def test_each_recipient_has_its_state(self):
        its, ls = sent()
        w = owed_mod.waiting_on(its, ls, P, NOW)
        asks = {a['id']: a for a in w['asks']}
        self.assertEqual(sorted(asks), ['w1', 'w2', 'w3'])
        st = {(a, r['to']): r['state'] for a, x in asks.items() for r in x['recipients']}
        self.assertEqual(st, {('w1', K): 'surfaced', ('w1', X): 'acknowledged', ('w2', K): 'answered',
                              ('w3', X): 'no_receipt'})               # the untrusted move counts for nothing
        self.assertEqual(w['waiting'], {K: 1, X: 2})
        self.assertEqual((asks['w1']['why'], asks['w1']['effort']), ('the hall needs both of you', 15))
        self.assertEqual(asks['w1']['recipients'][1]['line'], 'm1')

    def test_a_receipt_by_their_agent_is_received(self):
        its, ls = sent()
        w = owed_mod.waiting_on(its, [l for l in ls if l['id'] != 'm1'], P, NOW)
        x = {r['to']: r for r in w['asks'][0]['recipients']}
        self.assertEqual((x[X]['state'], x[X]['words'], x[X]['line']), ('received', 'received', 'rc1'))

    def test_an_answer_the_fold_refused_never_answers(self):
        its = items(ask('w2', to=K, actor=P))
        ls = [line('rc', 'receive', {'of': 'w2', 'how': 'pull'}, actor='agent:kaide', for_=K,
                   links={'answers': ['w2']}, reason='delegated', ts='2026-10-30T10:00:00-07:00'),
              line('a2', 'answer', {'answer': 'accept'}, actor='agent:kaide', for_=K, links={'answers': ['w2']},
                   reason='delegated', ts='2026-10-30T10:30:00-07:00')]
        its['trust'] = {'rc': 'signed', 'a2': 'signed'}
        open_ = owed_mod.waiting_on(its, ls, P, NOW)['asks'][0]['recipients'][0]['state']
        self.assertEqual(open_, 'answered')                          # the control: a counted answer answers
        its['invalid'] = [{'id': 'a2', 'invalid_reason': "the delegation does not cover the type 'answer'"}]
        r = owed_mod.waiting_on(its, ls, P, NOW)['asks'][0]['recipients'][0]
        self.assertEqual((r['state'], r['line']), ('received', 'rc'))
        self.assertEqual([l['id'] for l in deal_mod.trusted_lines(its, ls)], ['rc'])
        for k in ('unverified', 'refused', 'proposals'):
            its2 = dict(its, invalid=[], **{k: [{'id': 'a2'}]})
            self.assertNotEqual(owed_mod.waiting_on(its2, ls, P, NOW)['asks'][0]['recipients'][0]['state'], 'answered', k)
        its2 = dict(its, invalid=[], forked=[{'lines': ['a2', 'zz'], 'survivor': 'zz'}])
        self.assertNotEqual(owed_mod.waiting_on(its2, ls, P, NOW)['asks'][0]['recipients'][0]['state'], 'answered')

    def test_deterministic(self):
        its, ls = sent()
        a = json.dumps(owed_mod.waiting_on(its, ls, P, NOW), sort_keys=True)
        rnd = random.Random(7)
        for _ in range(5):
            l2 = list(ls); rnd.shuffle(l2)
            its2 = dict(its, cards=list(its['cards'])); rnd.shuffle(its2['cards'])
            self.assertEqual(json.dumps(owed_mod.waiting_on(its2, l2, P, NOW), sort_keys=True), a)

    def test_honest_empty(self):
        self.assertEqual(owed_mod.waiting_on(items(), [], P, NOW)['basis'], 'nothing this person asked is open')
        w = owed_mod.waiting_on(items(), None, AG, NOW)
        self.assertEqual((w['asks'], w['basis'][:14]), ([], 'no person name'))


# ---------------------------------------------------------------- the stop fallback reads as stops.py does

def stop(i, holon=B, actor=X, **kw):
    s = {'id': i, 'kind': 'stop', 'holon': holon, 'actor': actor, 'for': actor, 'state': 'live', 'why': 'hold',
         'ts': '2026-10-30T09:00:00-07:00'}
    s.update(kw)
    return s


class StopFallback(unittest.TestCase):
    def agree(self, st, c, want):
        got = deal_mod._fallback_binds([st], AG, c['holon'], c['id'], c)
        self.assertEqual(got is not None, want, (st, c['id']))
        try:
            import stops
        except ImportError:
            return
        rows = stops.live([st], AG)
        self.assertEqual(bool(stops.binds(rows, AG, c['holon'], c)[0]), want, ('stops.py', st, c['id']))

    def test_a_stop_with_no_scope_and_no_agents_binds_the_home_card(self):
        self.agree(stop('s1'), card('home', holon=A, holder=P, actor=P), True)

    def test_a_stop_scoped_to_an_actor_binds_only_that_actors_cards(self):
        st = stop('s2', scope=K)
        self.agree(st, card('theirs', holon=A, actor=K), True)
        self.agree(st, card('mine', holon=A, holder=P, actor=P), False)
        self.agree(stop('s3', scope=AG), card('mine', holon=A, holder=P, actor=P), True)   # the agent itself

    def test_the_deal_withholds_the_home_card_under_an_unscoped_stop(self):
        its = items(card('home', holon=A, holder=P, actor=P))
        its['stops'] = [stop('s1')]
        d = D(its, fold=its)
        self.assertEqual(by_id(d)['home']['stopped']['stop'], 's1')
        self.assertEqual(by_id(d)['home']['acts'], [])


# ---------------------------------------------------------------- null-guards

class NullGuards(unittest.TestCase):
    def test_nothing_breaks_on_empty_or_strange_input(self):
        for its in (None, {}, [], {'cards': None}, {'cards': [None, 5, 'x']}):
            json.dumps(D(its), sort_keys=True)
            json.dumps(owed_mod.owed(its, now=NOW), sort_keys=True)
            for ls in (None, [], [None, 5, 'x', {}], {'not': 'a list'}):
                json.dumps(owed_mod.waiting_on(its, ls, P, NOW), sort_keys=True)
        for src in (None, {}, [], 'x', 5, {'why': 5, 'effort': '20', 'voice': ['agent'], 'by': 7}):
            w = deal_mod.sender_word(src)
            self.assertEqual(w['missing'], ['why', 'effort', 'by', 'voice'])
        self.assertEqual(record.line_voice({}), ('agent', None))
        self.assertEqual(record.line_voice({'actor': 'person:x', 'body': 'not a dict'}), ('human-words', None))
        for v in (None, 5, 'x', [], 2.5):
            self.assertEqual(record.line_voice(v), (None, None))

    def test_a_persons_line_with_no_reason_is_their_own_words(self):
        # the kit's reading: a person's own signed line is their words unless a reason says otherwise
        self.assertEqual(record.line_voice({'actor': 'person:a'}), ('human-words', None))
        self.assertEqual(record.line_voice({'actor': 'person:a', 'reason': 'human'}), ('human-words', None))
        self.assertEqual(record.line_voice({'actor': 'person:a', 'reason': 'delegated'}), ('agent', None))

    def test_a_non_nfc_why_is_read_in_nfc(self):
        c = D(items(ask('r1', why='Café at six')))['cards'][0]
        self.assertEqual(c['sender']['why'], 'Café at six')

    def test_the_deal_is_deterministic(self):
        its = items(ask('r1', effort=20, why='x'), ask('r2'), card('o1', state='open', asked='offer', to=P, holder=K))
        a = json.dumps(D(its), sort_keys=True)
        its['cards'].reverse()
        self.assertEqual(json.dumps(D(its), sort_keys=True), a)


if __name__ == '__main__':
    unittest.main()
