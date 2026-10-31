"""test_negotiation.py — the conversation for action: asks, moves, shapes, mandates.

The fixtures (fixtures/make_fixtures.py) are built once per run, signed with throwaway keys; the
fixture ask (meet_ask), its counter and the asker's accept_counter are folded on the real fold.
The shapes are checked on small records made in memory (unsigned lines read with a trust map,
as the fold would hand them over), so each test names only the lines it needs.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_negotiation.py -v
"""
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import record          # noqa: E402
import make_fixtures   # noqa: E402
import negotiation as N  # noqa: E402

PLAYER, STEWARD, AIDE = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        return
    WORK = tempfile.mkdtemp(prefix='lionsberg-negotiation-test-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def one(asks, ask_id):
    for a in asks:
        if a['id'] == ask_id:
            return a
    raise AssertionError('no ask %s' % ask_id[:12])


# ---------------------------------------------------------------- on the real fold

@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the fixtures are signed')
class Real(unittest.TestCase):
    def setUp(self):
        self.hq = os.path.join(TEMPLATE, 'hq')
        self.types = record.load_types()
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.r = record.read_all(self.hq)
        self.heads = {}
        for d in record.hold(self.hq):
            rd = record.read(d)
            for a, hs in rd['heads'].items():
                self.heads[(rd['holon'], a)] = hs[-1]
        self.n = 0

    def fold(self, lines):
        return record.fold(lines, self.types, self.r['keepers'], clock=CLOCK)

    def mk(self, actor, holon_id, typ, body=None, links=None, ts=None, reason=None, for_=None, sign=True):
        self.n += 1
        ts = ts or '2026-10-21T%02d:%02d:00-07:00' % (10 + self.n // 60, self.n % 60)
        for_ = for_ or (actor if actor.startswith('person:') else PLAYER)
        prev = self.heads.get((holon_id, actor), '')
        reason = reason or ('human' if actor.startswith('person:') else 'delegated')
        line = record.make_line(actor, for_, holon_id, typ, body, links, reason=reason, ts=ts, salt='n%d' % self.n, prev=prev)
        if sign:
            line['sig'] = record.sign_id(line['id'], record.find_key(None, actor, KEYS))
        self.heads[(holon_id, actor)] = line['id']
        return line

    def run_with(self, extra=(), drop=()):
        lines = [l for l in self.r['lines'] if l['id'] not in drop] + list(extra)
        f = self.fold(lines)
        return N.report(f, lines), f

    # law 2
    def test_the_fixture_ask_agrees_on_the_counters_time(self):
        rep, _ = self.run_with()
        a = one(rep['asks'], IDS['meet_ask'])
        self.assertEqual(a['state'], 'agreed')
        self.assertEqual(a['terms'], {'time': '2026-11-05T18:00'})
        self.assertEqual(a['round'], 1)
        self.assertEqual(a['answers'], {STEWARD: 'accepted'})
        self.assertEqual([m['move'] for m in a['moves']], ['counter', 'accept_counter'])
        self.assertEqual((a['why'], a['effort'], a['shape'], a['quorum'], a['voice'], a['to'], a['by']),
                         ('the hall is held only until Friday', 1, 'converge', 'everyone', 'human-words', [STEWARD], '2026-11-06'))
        self.assertEqual(a['waiting_on'], [STEWARD])           # agreed: the steward owes the meeting

    def test_before_the_accept_it_is_open_with_one_round_and_countered(self):
        rep, _ = self.run_with(drop={IDS['meet_accept']})
        a = one(rep['asks'], IDS['meet_ask'])
        self.assertEqual((a['state'], a['round'], a['answers']), ('open', 1, {STEWARD: 'countered'}))
        self.assertIsNone(a['terms'])
        self.assertEqual(a['waiting_on'], [PLAYER])            # the counter waits on the asker

    def test_the_kits_own_answers_are_moves(self):
        rep, _ = self.run_with()
        req, off = one(rep['asks'], IDS['request']), one(rep['asks'], IDS['offer'])
        self.assertIn(req['state'], ('agreed', 'performing'))
        self.assertEqual([(m['move'], m['via']) for m in req['moves']], [('accept', 'answer')])
        self.assertEqual(off['state'], 'declined')

    # law 6, on the real fold: the fixtures hold a receipt on the request
    def test_the_tally_reads_receipts_on_the_item(self):
        rep, _ = self.run_with()
        t = one(rep['asks'], IDS['request'])['tally']
        self.assertEqual((t['n'], t['received'], t['answered'], t['agreed']), (1, 1, 1, 1))

    # law 3
    def test_untrusted_and_unverified_moves_count_for_nothing(self):
        u = self.mk(STEWARD, self.C, 'move', {'move': 'accept', 'root': IDS['meet_ask']},
                    {'answers': [IDS['meet_ask']]}, reason='untrusted')
        x = record.make_line('person:stranger', 'person:stranger', self.C, 'move', {'move': 'accept', 'root': IDS['meet_ask']},
                             {'answers': [IDS['meet_ask']]}, ts='2026-10-21T11:00:00-07:00', salt='x')
        rep, _ = self.run_with([u, x], drop={IDS['meet_accept']})
        nc = {e['id'] for e in rep['not_counted']}
        self.assertTrue({u['id'], x['id']} <= nc)
        a = one(rep['asks'], IDS['meet_ask'])
        self.assertEqual(a['state'], 'open')
        self.assertNotIn(u['id'], [m['id'] for m in a['moves']])

    def test_a_move_on_no_held_ask_is_pending(self):
        m = self.mk(STEWARD, self.C, 'move', {'move': 'accept', 'root': 'f' * 64})
        rep, _ = self.run_with([m])
        self.assertEqual([p['id'] for p in rep['pending']], [m['id']])
        self.assertIn('not a held ask', rep['pending'][0]['why'])

    # law 4
    def test_an_agents_accept_on_a_standing_delegation_does_not_count(self):
        d = self.mk(PLAYER, self.C, 'delegate', {'to': AIDE, 'scope': ['move'], 'holons': [self.C], 'until': '2026-12-31'})
        m = self.mk(AIDE, self.C, 'move', {'move': 'accept', 'root': IDS['request']}, {'answers': [IDS['request']]})
        rep, f = self.run_with([d, m])
        self.assertEqual(f['trust'].get(m['id']), 'signed')     # the fold lets it in; the grammar does not
        a = one(rep['asks'], IDS['request'])
        self.assertIn(m['id'], [x['id'] for x in a['refused']])
        self.assertIn("person's word", [x for x in a['refused'] if x['id'] == m['id']][0]['why'])

    def test_under_a_mandate_an_availability_move_counts_and_says_so(self):
        mandate = {'days': ['mon', 'tue', 'wed', 'thu', 'fri'], 'after': '09:00', 'before': '17:00', 'max_minutes': 60,
                   'colour': 'blue'}
        d = self.mk(PLAYER, self.C, 'delegate', {'to': AIDE, 'scope': ['move'], 'holons': [self.C], 'until': '2026-12-31',
                                                  'mandate': mandate})
        ok = self.mk(AIDE, self.C, 'move', {'move': 'counter', 'root': IDS['request'],
                                            'terms': {'time': '2026-11-03T10:00', 'minutes': 30}}, {'answers': [IDS['request']]})
        sat = self.mk(AIDE, self.C, 'move', {'move': 'counter', 'root': IDS['request'],
                                             'terms': {'time': '2026-11-07T10:00'}}, {'answers': [IDS['request']]})
        acc = self.mk(AIDE, self.C, 'move', {'move': 'accept', 'root': IDS['request']}, {'answers': [IDS['request']]})
        rep, f = self.run_with([d, ok, sat, acc])
        dl = [x for x in f['delegations'] if x['id'] == d['id']][0]
        self.assertEqual(dl.get('mandate'), mandate)
        a = one(rep['asks'], IDS['request'])
        row = [m for m in a['moves'] if m['id'] == ok['id']][0]
        self.assertEqual(row['voice'], 'under-mandate')
        self.assertIn('voice set to under-mandate', row['voice_said'])
        refused = {x['id']: x['why'] for x in a['refused']}
        self.assertIn('sat', refused[sat['id']])
        self.assertIn(acc['id'], refused)
        self.assertEqual(a['answers'][PLAYER], 'countered')

    def test_an_agents_accept_counts_with_the_persons_word(self):
        d = self.mk(PLAYER, self.C, 'delegate', {'to': AIDE, 'scope': ['move'], 'holons': [self.C], 'until': '2026-12-31',
                                                  'once': True})
        m = self.mk(AIDE, self.C, 'move', {'move': 'accept', 'root': IDS['request']}, {'answers': [IDS['request']]})
        rep, f = self.run_with([d, m])
        self.assertIn(m['id'], [x['id'] for x in f['signed_for']])
        a = one(rep['asks'], IDS['request'])
        row = [x for x in a['moves'] if x['id'] == m['id']][0]
        self.assertEqual(row['voice'], 'agent-drafted')

    def test_a_move_from_the_wrong_side_is_refused(self):
        # the player asked: a counter is a responder's move, so the player's own counter is refused;
        # the steward, the one asked, may still accept
        m = self.mk(STEWARD, self.C, 'move', {'move': 'accept', 'root': IDS['meet_ask']}, {'answers': [IDS['meet_ask']]})
        n = self.mk(PLAYER, self.C, 'move', {'move': 'counter', 'root': IDS['meet_ask']}, {'answers': [IDS['meet_ask']]})
        rep, _ = self.run_with([m, n])
        a = one(rep['asks'], IDS['meet_ask'])
        why = {x['id']: x['why'] for x in a['refused']}
        self.assertIn('responder', why[n['id']])                # the asker does not counter their own ask
        self.assertNotIn(m['id'], why)

    # review High 1: a tampered copy keeps the real line's id; it is left out and never wins
    def test_a_tampered_copy_never_stands_for_the_real_line(self):
        real = [l for l in self.r['lines'] if l['id'] == IDS['meet_accept']][0]
        bad = json.loads(json.dumps(real))
        bad['body']['terms'] = {'time': '2026-12-25T03:00'}
        lines = [bad] + self.r['lines']
        rep = N.report(self.fold(self.r['lines']), lines)
        a = one(rep['asks'], IDS['meet_ask'])
        self.assertEqual(a['terms'], {'time': '2026-11-05T18:00'})
        self.assertIn('id does not match', [e['why'] for e in rep['not_counted'] if e['id'] == real['id']][0])

    # review Medium 4, N1, N6: an answer owed and work owed are apart, and an ask is in one place for a reader
    def test_render_separates_to_answer_from_to_do(self):
        rep, _ = self.run_with()
        md = N.render(rep['asks'], STEWARD)
        do = md.split('## Owed by you: to do')[1]
        ans = md.split('## Owed by you: to answer')[1].split('## Owed by you: to do')[0]
        self.assertIn('Meet this week', do)
        self.assertIn('2026-11-05T18:00', do)
        self.assertNotIn('Meet this week', ans)
        rep, _ = self.run_with(drop={IDS['meet_accept']})
        for who, here, not_here in ((PLAYER, '## Owed by you: to answer', '## Waiting on'),
                                    (STEWARD, '## Waiting on', '## Owed by you: to answer')):
            md = N.render(rep['asks'], who)
            sec = {h: md.split(h)[1].split('##')[0] for h in (here, not_here)}
            self.assertIn('Meet this week', sec[here], who)
            self.assertNotIn('Meet this week', sec[not_here], who)

    def test_the_cli_reads_a_fold_and_lines(self):
        rep, f = self.run_with()
        items = os.path.join(WORK, 'items.json')
        lines = os.path.join(WORK, 'lines.jsonl')
        with open(items, 'w', encoding='utf-8') as fh:
            json.dump(f, fh)
        with open(lines, 'w', encoding='utf-8') as fh:
            for l in self.r['lines']:
                fh.write(json.dumps(l) + '\n')
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(N._main([items, '--lines', lines, '--json']), 0)
        self.assertEqual(one(json.loads(buf.getvalue())['asks'], IDS['meet_ask'])['state'], 'agreed')
        link = os.path.join(WORK, 'items-link.json')
        if not os.path.exists(link):
            os.symlink(items, link)
        self.assertEqual(N._main([link, '--lines', lines]), 2)


# ---------------------------------------------------------------- small records in memory

H = 'h' * 64
A, B, C, D = 'person:a', 'person:b', 'person:c', 'person:d'
AG = 'agent:b-aide'


class Mem(unittest.TestCase):
    def setUp(self):
        self.lines, self.n = [], 0

    def L(self, actor, typ, body, links=None, for_=None, reason=None, ts=None):
        self.n += 1
        ts = ts or '2026-10-10T10:%02d:00+00:00' % self.n
        for_ = for_ or (actor if actor.startswith('person:') else B)
        l = record.make_line(actor, for_, H, typ, body, links, reason=reason or ('human' if actor.startswith('person:') else 'delegated'),
                             ts=ts, salt='')
        self.lines.append(l)
        return l

    def mv(self, actor, move, ask, terms=None, answers=None, **kw):
        body = {'move': move, 'root': ask['id']}
        if terms:
            body['terms'] = terms
        return self.L(actor, 'move', body, {'answers': answers or [ask['id']]}, **kw)

    def items(self, members=(A, B, C, D), extra=None, now='2026-10-20T00:00:00+00:00'):
        adm = {H: {m: {'via': 'inception' if m == A else 'join'} for m in members}}
        it = {'trust': {l['id']: 'signed' for l in self.lines}, 'admitted': adm, 'as_of': now,
              'delegations': [], 'signed_for': []}
        it.update(extra or {})
        return it

    def ask(self, shape=None, quorum=None, to=(B, C, D), by='2026-11-30', typ='request', **more):
        body = {'to': list(to) if typ == 'say' else (to[0] if len(to) == 1 else None), 'title': 'Choose the day',
                'by': by, 'why': 'the hall needs an answer', 'effort': 5}
        if typ == 'say':
            body = dict(body, text='Choose the day', intent='ask')
        if typ == 'propose':
            body = {'text': 'Adopt the plan', 'by': by}
        if shape:
            body['shape'] = shape
        if quorum is not None:
            body['quorum'] = quorum
        body.update(more)
        return self.L(A, typ, body)

    def get(self, ask, **kw):
        return one(N.asks(self.items(**{k: v for k, v in kw.items() if k in ('members', 'extra', 'now')}), self.lines), ask['id'])

    # law 1
    def test_pure_and_deterministic_ties_by_time_then_id(self):
        a = self.ask(typ='say', shape='converge', quorum='2')
        ts = '2026-10-10T11:00:00+00:00'
        self.mv(B, 'accept', a, ts=ts)
        self.mv(C, 'accept', a, ts=ts)
        it = self.items()
        before = json.dumps(it, sort_keys=True)
        r1 = json.dumps(N.report(it, self.lines), sort_keys=True)
        r2 = json.dumps(N.report(it, list(reversed(self.lines))), sort_keys=True)
        self.assertEqual(r1, r2)
        self.assertEqual(json.dumps(it, sort_keys=True), before)       # the input is never changed
        ids = [m['id'] for m in one(json.loads(r1)['asks'], a['id'])['moves']]
        self.assertEqual(ids, sorted(ids))

    # law 5: the four shapes, and no shape
    def test_converge_resolves_when_one_option_meets_the_quorum(self):
        a = self.ask(typ='say', shape='converge', quorum='2', options=['tue', 'wed'])
        self.mv(B, 'accept', a, {'option': 'tue'})
        self.mv(C, 'accept', a, {'option': 'wed'})
        self.assertEqual(self.get(a)['state'], 'open')
        self.mv(D, 'accept', a, {'option': 'wed'})
        g = self.get(a)
        self.assertEqual((g['state'], g['terms']), ('agreed', {'option': 'wed'}))
        self.assertEqual(g['tally']['agreed'], 3)

    def test_call_resolves_at_an_award_and_releases_the_rest(self):
        a = self.ask(typ='say', shape='call', quorum='any one')
        b1 = self.mv(B, 'counter', a, {'minutes': 60})
        b2 = self.mv(C, 'counter', a, {'minutes': 45})
        b3 = self.mv(D, 'accept', a)
        self.assertEqual(self.get(a)['state'], 'open')                # a call waits for its award
        self.mv(A, 'award', a, answers=[b2['id']])
        g = self.get(a)
        self.assertEqual((g['state'], g['terms']), ('agreed', {'minutes': 45}))
        self.assertEqual(g['released'], sorted([b1['id'], b3['id']]))
        self.assertEqual(g['waiting_on'], [C])

    def test_consent_resolves_when_every_objection_is_integrated(self):
        a = self.ask(typ='propose', shape='consent')
        self.mv(B, 'accept', a)
        ob = self.mv(C, 'conditional', a, {'objection': 'the cost is not said'})
        self.mv(D, 'accept', a)
        g = self.get(a)
        self.assertEqual((g['state'], g['objections'][C]['open']), ('open', True))
        self.mv(A, 'amend', a, {'cost': 'none'}, answers=[ob['id']])
        self.assertEqual(self.get(a)['state'], 'open')               # integrated only when the objector accepts
        self.mv(C, 'accept', a)
        g = self.get(a)
        self.assertEqual((g['state'], g['terms'], g['round']), ('agreed', {'cost': 'none'}, 1))
        self.assertEqual(g['objections'][C], {'move': ob['id'], 'open': False, 'how': 'integrated'})

    def test_gather_resolves_at_a_harvest_naming_the_quorums_contributions(self):
        a = self.ask(typ='say', shape='gather', quorum='2')
        c1 = self.mv(B, 'accept', a, {'idea': 'a garden'})
        s = self.L(C, 'say', {'text': 'a library'}, {'anchored_to': [a['id']]})
        self.mv(A, 'done', a, answers=[c1['id']])
        self.assertEqual(self.get(a)['state'], 'open')               # one contribution named; the quorum is two
        self.mv(A, 'done', a, answers=[c1['id'], s['id']])
        g = self.get(a)
        self.assertEqual(g['state'], 'agreed')
        self.assertEqual(g['terms']['harvest'], sorted([c1['id'], s['id']]))

    def test_two_party_accept_and_the_walk_to_satisfied(self):
        a = self.ask(to=(B,))
        self.mv(B, 'accept', a)
        self.assertEqual(self.get(a)['state'], 'agreed')
        self.mv(B, 'done', a)
        g = self.get(a)
        self.assertEqual((g['state'], g['waiting_on']), ('performing', [A]))
        self.mv(A, 'not_yet', a)
        self.assertEqual(self.get(a)['state'], 'not_yet')
        self.mv(B, 'done', a)
        self.mv(A, 'satisfied', a)
        g = self.get(a)
        self.assertEqual(g['state'], 'satisfied')
        late = self.mv(B, 'counter', a, {'minutes': 5})
        self.assertIn(late['id'], [x['id'] for x in self.get(a)['ignored']])

    def test_a_lapsed_by_date_lapses_it_and_withdraw_and_decline_close_it(self):
        a = self.ask(to=(B,), by='2026-10-15')
        self.assertEqual(self.get(a)['state'], 'lapsed')
        self.assertEqual(one(N.asks(self.items(now='2026-10-12T00:00:00+00:00'), self.lines), a['id'])['state'], 'open')
        b = self.ask(to=(B,))
        self.mv(B, 'decline', b)
        self.assertEqual(self.get(b)['state'], 'declined')
        c = self.ask(to=(B,))
        self.mv(A, 'withdraw', c)
        self.assertEqual(self.get(c)['state'], 'withdrawn')

    def test_a_defer_moves_the_by_date_once_the_asker_takes_it(self):
        a = self.ask(to=(B,), by='2026-10-15')
        d = self.L(B, 'move', {'move': 'defer', 'root': a['id'], 'by': '2026-10-30'}, {'answers': [a['id']]})
        self.assertEqual(self.get(a)['state'], 'lapsed')
        self.mv(A, 'accept_counter', a, answers=[d['id']])
        g = self.get(a)
        self.assertEqual((g['state'], g['by'], g['by_asked']), ('agreed', '2026-10-30', '2026-10-15'))

    # law 6
    def test_the_tally_for_a_holon_ask(self):
        a = self.ask(typ='say', shape='converge')
        self.mv(B, 'accept', a)
        self.mv(C, 'decline', a)
        self.L(D, 'say', {'text': 'reading it'}, {'anchored_to': [a['id']]})
        card = {'id': a['id'], 'kind': 'thread', 'events': [a['id']],
                'receipts': [{'id': 'r1', 'actor': AG}, {'id': 'r2', 'actor': C}]}
        dl = {'id': 'dd', 'kind': 'delegation', 'actor': B, 'for': B, 'to': AG, 'scope': ['receive'], 'holons': ['*'],
              'until': '2026-12-31', 'state': 'live'}
        g = self.get(a, extra={'threads': [card], 'delegations': [dl]})
        self.assertEqual(g['tally'], {'n': 3, 'received': 2, 'acknowledged': 3, 'answered': 2, 'agreed': 1,
                                      'declined': 1, 'open': 1})
        self.assertEqual(g['quorum_basis'], "everyone: 3 (the kit's default: the ask says no quorum)")

    def test_a_move_by_a_stranger_is_refused_and_a_clarify_changes_nothing(self):
        a = self.ask(to=(B,))
        x = self.mv(C, 'accept', a)
        self.mv(B, 'clarify', a)
        g = self.get(a)
        self.assertEqual(g['state'], 'open')
        self.assertIn('not a party', [r for r in g['refused'] if r['id'] == x['id']][0]['why'])
        self.assertEqual(g['answers'], {B: 'none'})

    # law 3 on the trust-map path
    def test_vouched_refused_and_untrusted_count_for_nothing(self):
        a = self.ask(to=(B,))
        v = self.mv(B, 'accept', a)
        r = self.mv(B, 'accept', a, ts='2026-10-10T11:30:00+00:00')
        u = self.mv(B, 'accept', a, reason='untrusted', ts='2026-10-10T11:40:00+00:00')
        x = self.mv(B, 'accept', a, ts='2026-10-10T11:50:00+00:00')
        it = self.items()
        it['trust'][v['id']] = 'vouched'
        it['trust'][r['id']] = 'refused'
        it['refused'] = [{'id': x['id'], 'said': 'refused by the fold'}]
        rep = N.report(it, self.lines)
        self.assertEqual(one(rep['asks'], a['id'])['state'], 'open')
        why = {e['id']: e['why'] for e in rep['not_counted']}
        self.assertIn('vouched', why[v['id']])
        self.assertIn('refused', why[r['id']])
        self.assertIn('proposal', why[u['id']])
        self.assertIn('the fold lists it', why[x['id']])

    # law 5, consent with a quorum of two
    def test_consent_with_a_quorum_of_two(self):
        a = self.ask(typ='propose', shape='consent', quorum='2')
        self.mv(B, 'accept', a)
        ob = self.mv(C, 'decline', a, {'objection': 'it costs too much'})
        self.mv(D, 'decline', a)                                       # stands aside
        g = self.get(a)
        self.assertEqual(g['objections'][C], {'move': ob['id'], 'open': True, 'how': None})
        self.assertEqual(g['state'], 'open')                           # two answered, but an objection is open
        self.mv(C, 'decline', a)                                       # the objector stands aside
        g = self.get(a)
        self.assertEqual((g['objections'][C]['open'], g['objections'][C]['how']), (False, 'stood aside'))
        self.assertEqual(g['state'], 'agreed')

    def test_consent_needs_one_accept(self):
        a = self.ask(typ='propose', shape='consent', quorum='2')
        self.mv(B, 'decline', a)
        self.mv(C, 'decline', a)
        self.assertEqual(self.get(a)['state'], 'open')                 # two stood aside, a quorum of two, yet no one consented
        self.mv(D, 'accept', a)
        self.assertEqual(self.get(a)['state'], 'agreed')

    # review Medium 2: an unnamed stewards quorum reads as the keeper less the asker, and says so
    def test_an_unnamed_stewards_quorum(self):
        a = self.ask(typ='say', shape='converge', quorum='stewards')            # the asker A is the keeper
        self.mv(B, 'accept', a)
        g = self.get(a)
        self.assertEqual(g['state'], 'open')
        self.assertIn('no stewards are named', g['cannot_resolve'])
        self.assertIn('cannot resolve', N.render([g]))
        b = self.L(B, 'say', {'text': 'Choose', 'intent': 'ask', 'to': [A, C], 'shape': 'converge', 'quorum': 'stewards'})
        self.mv(C, 'accept', b)
        self.assertEqual(self.get(b)['state'], 'open')                         # the keeper A has not accepted
        self.mv(A, 'accept', b)
        g = self.get(b)
        self.assertEqual(g['state'], 'agreed')
        self.assertNotIn('cannot_resolve', g)

    # review Medium 3: a revoke un-counts only what came after it
    def test_a_revoke_keeps_the_mandated_moves_before_it(self):
        a = self.ask(to=(B,))
        before = self.mv(AG, 'counter', a, {'time': '2026-11-03T10:00'}, ts='2026-10-10T12:00:00+00:00')
        after = self.mv(AG, 'counter', a, {'time': '2026-11-04T10:00'}, ts='2026-10-10T14:00:00+00:00')
        dl = {'id': 'd1', 'kind': 'delegation', 'actor': B, 'for': B, 'to': AG, 'scope': ['move'], 'holons': [H],
              'until': '2026-12-31', 'state': 'revoked', 'revoked_ts': '2026-10-10T13:00:00+00:00',
              'ts': '2026-10-01T00:00:00+00:00', 'mandate': {'days': ['mon', 'tue', 'wed', 'thu', 'fri']}}
        g = self.get(a, extra={'delegations': [dl]})
        self.assertIn(before['id'], [m['id'] for m in g['moves']])
        self.assertIn(after['id'], [r['id'] for r in g['refused']])

    # review N3: an agent's clarify is no person's acknowledgment
    def test_an_agents_clarify_acknowledges_no_one(self):
        a = self.ask(to=(B,))
        self.mv(AG, 'clarify', a)
        self.L(AG, 'say', {'text': 'my person will look'}, {'anchored_to': [a['id']]})
        g = self.get(a)
        self.assertEqual((g['tally']['acknowledged'], g['tally']['answered']), (0, 0))
        self.mv(B, 'clarify', a)
        self.assertEqual(self.get(a)['tally']['acknowledged'], 1)

    # review N4: after a reject_counter the ask waits on the responder again
    def test_a_rejected_counter_waits_on_the_responder(self):
        a = self.ask(to=(B,))
        c = self.mv(B, 'counter', a, {'minutes': 90})
        self.assertEqual(self.get(a)['waiting_on'], [A])
        self.mv(A, 'reject_counter', a, answers=[c['id']])
        g = self.get(a)
        self.assertEqual((g['state'], g['waiting_on'], g['answers'][B]), ('open', [B], 'none'))

    def test_without_a_trust_map_an_agent_needs_a_delegation(self):
        a = self.ask(to=(B,))
        m = self.mv(AG, 'counter', a, {'minutes': 5})
        it = self.items()
        del it['trust']
        rep = N.report(it, self.lines)
        self.assertIn(m['id'], [e['id'] for e in rep['not_counted']])
        self.assertIn('no trust map', rep['trust_basis'])


# ---------------------------------------------------------------- mandates, lines, words, guards

class Mandate(unittest.TestCase):
    D = {'id': 'd1', 'kind': 'delegation', 'actor': B, 'for': B, 'to': AG, 'scope': ['move'], 'holons': [H],
         'until': '2026-12-31', 'state': 'live',
         'mandate': {'days': ['mon', 'tue', 'wed', 'thu', 'fri'], 'after': '09:00', 'before': '17:00',
                     'max_minutes': 60, 'not': ['2026-11-04'], 'tone': 'x'}}

    def test_within_and_outside(self):
        ok, why = N.mandate_covers([self.D], AG, 'counter', {'time': '2026-11-03T10:00', 'minutes': 30}, holon=H)
        self.assertTrue(ok)
        self.assertIn('ignored', why)
        self.assertIn('tone', why)
        for terms in ({'time': '2026-11-07T10:00'}, {'time': '2026-11-03T08:00'}, {'time': '2026-11-03T16:30', 'minutes': 60},
                      {'minutes': 90}, {'time': '2026-11-04T10:00'}, {'time': 'Thursday'}):
            self.assertFalse(N.mandate_covers([self.D], AG, 'counter', terms, holon=H)[0], terms)
        self.assertTrue(N.mandate_covers([self.D], AG, 'decline', None, holon=H)[0])

    # review N2: a term beyond times, days and lengths goes to the person
    def test_terms_beyond_times_and_lengths_are_not_covered(self):
        for terms in ({'venue': 'the far hall'}, {'cost': 500}, {'time': '2026-11-03T10:00', 'title': 'more'}):
            ok, why = N.mandate_covers([self.D], AG, 'counter', terms, holon=H)
            self.assertFalse(ok, terms)
            self.assertIn('goes to the person', why)

    def test_a_mandate_never_covers_the_persons_word(self):
        for mv in ('accept', 'award', 'satisfied', 'done', 'amend'):
            ok, why = N.mandate_covers([self.D], AG, mv, {}, holon=H)
            self.assertFalse(ok)
            self.assertIn('never', why)

    def test_an_ended_or_absent_mandate_covers_nothing(self):
        self.assertFalse(N.mandate_covers([dict(self.D, state='revoked')], AG, 'counter', {}, holon=H)[0])
        self.assertFalse(N.mandate_covers([dict(self.D, mandate='within reason')], AG, 'counter', {}, holon=H)[0])
        self.assertFalse(N.mandate_covers([self.D], AG, 'counter', {}, holon='other')[0])
        self.assertFalse(N.mandate_covers([self.D], AG, 'counter', {}, now='2027-01-05T00:00:00+00:00', holon=H)[0])
        self.assertFalse(N.mandate_covers(None, AG, 'counter', {})[0])
        self.assertFalse(N.mandate_covers([dict(self.D, mandate={'days': 'weekdays'})], AG, 'counter', {}, holon=H)[0])


class Lines(unittest.TestCase):
    def test_move_line(self):
        ask = {'id': 'a' * 64, 'holon': H}
        l = N.move_line(ask, 'counter', AG, B, terms={'time': '2026-11-03T10:00'}, now='2026-10-21T10:00:00+00:00')
        self.assertEqual((l['type'], l['body']['move'], l['body']['root'], l['body']['voice'], l['links']['answers']),
                         ('move', 'counter', 'a' * 64, 'under-mandate', ['a' * 64]))
        self.assertEqual(l['sig'], '')
        self.assertEqual(l['id'], record.compute_id(l))
        p = N.move_line(ask, 'accept', B, B, now='2026-10-21T10:00:00+00:00')
        self.assertEqual((p['body']['voice'], p['reason']), ('human-words', 'human'))
        for bad in ((None, 'accept', B, B), (ask, 'promise', B, B), (ask, 'accept', 'x', B), (ask, 'accept', B, C),
                    (ask, 'accept', AG, AG)):
            with self.assertRaises(ValueError):
                N.move_line(*bad)

    def test_the_moves_agree_with_the_registry(self):
        t = record.load_types()['types']['move']
        values = [f for f in t['fields'] if f['name'] == 'move'][0]['values']
        self.assertEqual(tuple(values), N.MOVES)


class Guards(unittest.TestCase):
    def test_null_guards(self):
        for items, lines in ((None, None), ({}, []), ([], {}), ({'trust': 3}, [None, 1, 'x', {}, {'id': 5}]),
                             ({'items': []}, [{'id': 'x', 'type': 'move', 'body': 'no'}])):
            r = N.report(items, lines)
            self.assertEqual(r['asks'], [])
            json.dumps(r, sort_keys=True)
        self.assertEqual(N.asks(None, None), [])
        self.assertIn('Nothing asked yet', N.render(None))
        self.assertIn('Nothing', N.render([None, 3, {}], actor=B))
        self.assertEqual(N.effort_words(None), 'effort not said')
        self.assertEqual(N.effort_words(130), '2 hours 10 minutes')
        self.assertEqual(N.effort_words(1.5), 'effort not said')

    def test_floats_and_non_nfc_text(self):
        m = Mem('setUp')
        m.setUp()
        decomposed = unicodedata.normalize('NFD', 'Café')
        a = m.L(A, 'request', {'to': B, 'title': decomposed, 'by': '2026-11-30', 'effort': 2})
        l = m.mv(B, 'counter', a, {'minutes': 30})
        l['body']['terms']['weight'] = 2.5                    # a float in memory: the line no longer hashes
        rep = N.report(m.items(), m.lines)
        g = one(rep['asks'], a['id'])
        self.assertEqual(g['title'], unicodedata.normalize('NFC', 'Café'))
        json.dumps(rep, sort_keys=True)

    def test_render_both_sides(self):
        m = Mem('setUp')
        m.setUp()
        a = m.ask(to=(B,))
        md_asker = N.render(N.asks(m.items(), m.lines), actor=A)
        md_b = N.render(N.asks(m.items(), m.lines), actor=B)
        self.assertIn('waiting on person:b to answer', md_asker)
        self.assertIn('## Owed by you: to answer', md_b)
        self.assertIn('asks 5 minutes', md_b)
        self.assertIn('by 2026-11-30', md_b)
        self.assertNotIn(a['id'], md_b)

    def test_the_words(self):
        with open(os.path.join(ENGINE, 'negotiation.py'), encoding='utf-8') as f:
            src = f.read().lower()
        for w in ('promise', ' house', 'estate', ' hq'):
            self.assertNotIn(w, src)


if __name__ == '__main__':
    unittest.main()
