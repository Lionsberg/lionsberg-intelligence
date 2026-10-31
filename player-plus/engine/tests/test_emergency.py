"""test_emergency.py — the emergency rule and the bell: what may wake a person, decided by their own limits.

Each law of emergency.py has a test that fails when it is broken.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_emergency.py -v
"""
import builtins
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import attention       # noqa: E402
import emergency       # noqa: E402

HOME = 'a' * 64
CELL = 'c' * 64
P, AG, M, X = 'person:player', 'agent:player-aide', 'person:steward', 'person:stranger'
NOW = '2026-10-24T13:00:00-07:00'          # a Saturday afternoon
NIGHT = '2026-10-24T22:30:00-07:00'        # inside the default quiet hours


def _source():
    with open(os.path.join(ENGINE, 'emergency.py'), encoding='utf-8') as fh:
        return fh.read()


def lim(i, rules, actor=P, for_=P, reason='human', ts='2026-10-20T09:00:00-07:00', **kw):
    body = {'rules': rules}
    body.update(kw)
    return {'id': i, 'ts': ts, 'actor': actor, 'for': for_, 'holon': HOME, 'type': 'limits', 'body': body,
            'reason': reason}


def commitment(i='c1', buffer_days=-1.5, critical=True, **kw):
    s = {'kind': 'commitment', 'id': i, 'from': M, 'holon': HOME, 'buffer_days': buffer_days, 'critical': critical}
    s.update(kw)
    return s


def pain(i='s1', frm=M, **kw):
    s = {'kind': 'sight', 'id': i, 'from': frm, 'holon': HOME, 'sight_kind': 'pain'}
    s.update(kw)
    return s


def ctx(**kw):
    c = {'members': {P, M, AG}, 'now': NOW}
    c.update(kw)
    return c


def agreement_items(bell=('pain',)):
    """An agreed Agreement between HOME and CELL that lets `bell` kinds ring, in the fold's shape."""
    it = {'id': '1' * 64, 'kind': 'agreement', 'holon': CELL, 'state': 'agreed', 'actor': P, 'for': P,
          'ts': '2026-10-20T10:00:00-07:00', 'with': CELL, 'crosses': ['request', 'sight'],
          'cadence': {'request': 60}, 'permits': {'write': True, 'bell': list(bell)}, 'until': '2027-03-20',
          'links': {}, 'agreed_by': M, 'agreed_ts': '2026-10-20T11:00:00-07:00', 'agreed_with': HOME}
    return {'agreements': [it], 'commitments': [],
            'admitted': {HOME: {P: {'via': 'inception'}}, CELL: {M: {'via': 'inception'}, P: {'via': 'join'}}},
            'as_of': '2026-10-21T10:00:00-07:00'}


class TestOwnRule(unittest.TestCase):
    """Law 1: only the person's own `limits` line counts."""

    def test_the_default_when_none(self):
        r = emergency.rule([], P)
        self.assertEqual((r['basis'], r['set_by'], r['else']), ('default', None, 'wait'))
        self.assertEqual(r['rules'], emergency.DEFAULT_RULES)

    def test_the_newest_own_line(self):
        mine = [{'signal': 'say', 'wake': True}]
        ls = [lim('l1', [{'signal': 'request', 'wake': True}]),
              lim('l2', mine, ts='2026-10-21T09:00:00-07:00'),
              lim('l3', [{'signal': 'fault', 'wake': True}], actor=AG, ts='2026-10-22T09:00:00-07:00'),   # an agent's
              lim('l4', [{'signal': 'fault', 'wake': True}], reason='untrusted', ts='2026-10-23T09:00:00-07:00'),
              lim('l5', [{'signal': 'fault', 'wake': True}], actor=M, for_=M, ts='2026-10-23T10:00:00-07:00'),
              dict(lim('l6', [{'signal': 'fault', 'wake': True}], ts='2026-10-23T11:00:00-07:00'), _trust='unverified'),
              {'id': 'l7', 'type': 'attention', 'actor': P, 'for': P, 'ts': '2026-10-24T09:00:00-07:00',
               'body': {'rules': [{'signal': 'fault', 'wake': True}]}}]
        r = emergency.rule(ls, P)
        self.assertEqual((r['basis'], r['set_by'], r['rules']), ('limits', 'l2', mine))
        self.assertEqual(emergency.rule(ls, M)['set_by'], 'l5')             # a person's own, for themselves
        self.assertEqual(emergency.rule(ls, AG)['basis'], 'default')       # an agent sets no limits

    def test_else_is_the_persons(self):
        r = emergency.rule([lim('l1', [], **{'else': 'wake'})], P)
        self.assertEqual(r['else'], 'wake')
        self.assertTrue(emergency.classify(commitment(critical=False), r, ctx())['wake'])
        r = emergency.rule([lim('l1', [], **{'else': 'shout'})], P)
        self.assertEqual(r['else'], 'wait')


class TestGrammar(unittest.TestCase):
    """Law 2: the `when` grammar is parsed, never run."""

    def test_no_eval_or_exec(self):
        src = _source()
        self.assertIsNone(re.search(r'(?<![.\w])(eval|exec|compile)\s*\(', src))
        self.assertNotIn('__import__', src)

    def test_an_injection_is_ignored_with_why(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'commitment', 'when': "__import__('os')", 'wake': True}], 'else': 'wait'}
        with mock.patch.object(builtins, '__import__', wraps=builtins.__import__) as imp:
            c = emergency.classify(commitment(), r, ctx())
            self.assertNotIn('os', [a[0][0] for a in imp.call_args_list])
        self.assertFalse(c['wake'])
        self.assertEqual(len(c['ignored']), 1)
        self.assertIn('not in the rule grammar', c['ignored'][0]['why'])

    def test_the_grammar(self):
        ok = ['buffer_days < 0', 'buffer_days > -2.5', 'kind == commitment', 'critical == true', 'by < next_sitting',
              'outside_limits', 'value outside_limits', 'from == "person:steward"']
        for w in ok:
            self.assertIsNotNone(emergency.parse_when(w)[0], w)
        for w in ['buffer_days <= 0', 'a < b', '1 < 2', 'x == y or 1', 'buffer_days < 0; rm', '', None, 3,
                  'x < 1' + ' ' * 200 + '0']:
            self.assertIsNone(emergency.parse_when(w)[0], w)

    def test_conditions_read(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'request', 'when': 'by < next_sitting', 'wake': True}]}
        c = ctx(next_sitting='2026-10-25T08:00:00-07:00')
        self.assertTrue(emergency.classify({'kind': 'request', 'id': 'r', 'by': '2026-10-24T18:00:00-07:00'}, r, c)['wake'])
        self.assertFalse(emergency.classify({'kind': 'request', 'id': 'r', 'by': '2026-10-30'}, r, c)['wake'])
        self.assertFalse(emergency.classify({'kind': 'request', 'id': 'r', 'by': '2026-10-24T18:00:00-07:00'}, r, ctx())['wake'])
        r = {'basis': 'limits', 'rules': [{'signal': 'say', 'when': 'from == "person:steward"', 'wake': True}]}
        self.assertTrue(emergency.classify({'kind': 'say', 'from': M}, r, ctx())['wake'])
        self.assertFalse(emergency.classify({'kind': 'say', 'from': X}, r, ctx())['wake'])

    def test_a_rule_out_of_grammar_is_ignored(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'commitment', 'wake': 'yes'}, {'signal': 'commitment', 'on': 'loud', 'wake': True},
                       {'signal': 'commitment', 'from': 'anyone', 'wake': True}, {'wake': True},
                       {'signal': 'telegram', 'wake': True}]}
        c = emergency.classify(commitment(), r, ctx())
        self.assertFalse(c['wake'])
        self.assertEqual([x['index'] for x in c['ignored']], [0, 1, 2, 3, 4])


class TestCommitments(unittest.TestCase):
    """Law 3: a critical-path commitment the network cannot keep wakes under the default rule."""

    def test_the_default_rule(self):
        c = emergency.classify(commitment(buffer_days=-1.5), None, ctx())
        self.assertTrue(c['wake']); self.assertTrue(c['special_cause'])
        self.assertEqual(c['rule'], emergency.DEFAULT_RULES[0])
        self.assertFalse(emergency.classify(commitment(buffer_days=2.0), None, ctx())['wake'])
        self.assertFalse(emergency.classify(commitment(buffer_days=-1.5, critical=False), None, ctx())['wake'])
        self.assertFalse(emergency.classify(commitment(buffer_days=None), None, ctx())['wake'])
        self.assertFalse(emergency.classify(commitment(buffer_days=-1, critical='true'), None, ctx())['wake'])

    def test_urgency_never_wakes_by_itself(self):
        loud = {'kind': 'request', 'id': 'r', 'from': X, 'push_weight': 9.0, 'urgency': 'now'}
        self.assertFalse(emergency.classify(loud, None, ctx())['wake'])
        b = emergency.bell(loud, None, [], {}, {P}, NOW)
        self.assertFalse(b['ring'])

    def test_security_wakes_under_the_default(self):
        self.assertTrue(emergency.classify({'kind': 'security', 'id': 'x'}, None, ctx())['wake'])

    def test_a_rule_that_holds_inside(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'commitment', 'wake': False}] + emergency.DEFAULT_RULES}
        c = emergency.classify(commitment(), r, ctx())
        self.assertFalse(c['wake']); self.assertFalse(c['special_cause'])
        self.assertIn('inside their limits', c['why'])


class TestBell(unittest.TestCase):
    """Law 4: a member's pain wakes and rings by the Andon permit; a stranger's rings only by a permit."""

    def test_a_members_pain_rings(self):
        c = emergency.classify(pain(), None, ctx())
        self.assertTrue(c['wake'])
        b = emergency.bell(pain(), None, [], {}, {P, M}, NOW)
        self.assertEqual((b['ring'], b['permit']), (True, 'andon'))

    def test_a_strangers_pain(self):
        s = pain(frm=X, from_holon=CELL)
        self.assertFalse(emergency.classify(s, None, ctx())['wake'])             # the default: members only
        open_rule = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'wake': True}]}
        self.assertTrue(emergency.classify(s, open_rule, ctx())['wake'])          # it classifies
        b = emergency.bell(s, open_rule, [], {}, {P, M}, NOW)
        self.assertEqual((b['wake'], b['ring'], b['permit']), (True, False, None))   # and does not ring
        b = emergency.bell(s, open_rule, [], agreement_items(), {P, M}, NOW)
        self.assertEqual((b['ring'], b['permit'], b['agreement']), (True, 'agreement', '1' * 64))
        b = emergency.bell(s, open_rule, [], agreement_items(bell=('hazard',)), {P, M}, NOW)
        self.assertFalse(b['ring'])

    def test_from_permit(self):
        s = pain(frm=X, from_holon=CELL)
        r = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'from': 'permit', 'wake': True}]}
        self.assertFalse(emergency.classify(s, r, ctx())['wake'])
        self.assertTrue(emergency.classify(s, r, ctx(bell_permits={CELL: ['pain']}))['wake'])
        self.assertTrue(emergency.bell(s, r, [], agreement_items(), {P, M}, NOW)['ring'])

    def test_the_subscription_reader_absent_is_said(self):
        s = pain(frm=X, from_holon=CELL)
        open_rule = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'wake': True}]}
        with mock.patch.dict(sys.modules, {'subscriptions': None}):
            b = emergency.bell(s, open_rule, [{'source': CELL, 'bell': ['pain']}], {}, {P}, NOW)
        self.assertFalse(b['ring'])
        self.assertTrue(any('only the Agreement' in n for n in b['permit_basis']))

    def test_a_subscription_rings(self):
        fake = mock.Mock()
        fake.bell_for = lambda rows, source, kind: (source == CELL and kind == 'pain', {'basis': 'subscription'})
        s = pain(frm=X, from_holon=CELL)
        open_rule = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'wake': True}]}
        with mock.patch.dict(sys.modules, {'subscriptions': fake}):
            b = emergency.bell(s, open_rule, [], {}, {P}, NOW)
        self.assertEqual((b['ring'], b['permit']), (True, 'subscription'))

    def test_a_member_rings_no_bell_the_rule_holds(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'sight', 'wake': False}]}
        b = emergency.bell(pain(), r, [], {}, {P, M}, NOW)
        self.assertEqual((b['ring'], b['permit']), (False, None))


class TestGate(unittest.TestCase):
    """Law 5: the closed word outranks the rule in the gate; quiet hours do not; Law 7 is test_game."""

    def cards(self):
        return [{'id': 'c1', 'by': '2026-10-30'}, {'id': 'k2', 'by': '2026-10-30'}]

    def test_wake_passes_quiet_hours(self):
        b = attention.budget([], P)
        g = attention.gate(self.cards(), b, NIGHT)
        self.assertEqual(g['interrupt'], [])
        g = attention.gate(self.cards(), b, NIGHT, wake={'c1'})
        self.assertEqual((g['interrupt'], g['woken']), (['c1'], ['c1']))
        self.assertEqual({x['id']: x['why'] for x in g['withheld']}['k2'], 'quiet hours')

    def test_closed_outranks_the_rule(self):
        b = dict(attention.budget([], P), closed_until='2026-10-25T07:00:00-07:00')
        g = attention.gate(self.cards(), b, NIGHT, wake={'c1'})
        self.assertEqual(g['interrupt'], [])
        self.assertTrue({x['id']: x['why'] for x in g['withheld']}['c1'].startswith('closed by the person'))

    def test_the_last_step_of_the_dial(self):
        b = dict(attention.budget([], P), fewer='only what always passes')
        g = attention.gate(self.cards(), b, NOW, sitting_open=True, wake=['c1'])
        self.assertEqual(g['deal'], ['c1'])

    def test_state_wakes_by_the_bell(self):
        cards = [{'id': 's1'}, {'id': 's2'}, {'id': 'c2', 'by': '2026-10-30'}]
        c = {'members': {P, M}}
        sig = [pain('s1'), pain('s2', frm=X, from_holon=CELL), commitment('c2', **{'from': X, 'from_holon': CELL})]
        st = attention.state([], P, cards, NIGHT, signals=sig, context=c)
        self.assertEqual(st['interrupt_now'], ['s1'])                            # a member's pain: Andon
        self.assertEqual(st['emergency']['basis'], 'default')
        self.assertEqual(st['emergency']['woken'], ['s1'])
        rows = {r['id']: r for r in st['emergency']['signals']}
        self.assertEqual((rows['c2']['wake'], rows['c2']['ring']), (True, False))   # wakes; no permit, no bell
        fake = mock.Mock()
        fake.bell_for = lambda rows, source, kind: (source == CELL and kind == 'commitment', 'subscription')
        with mock.patch.dict(sys.modules, {'subscriptions': fake}):
            st = attention.state([], P, cards, NIGHT, signals=sig, context=c)
        self.assertEqual(st['interrupt_now'], ['s1', 'c2'])                      # the person's Subscription
        st = attention.state([lim('l1', [{'signal': 'sight', 'wake': False}])], P, cards, NIGHT,
                             signals=[pain('s1')], context=c)
        self.assertEqual(st['interrupt_now'], [])                                # the person's own limits hold
        self.assertEqual(st['emergency']['set_by'], 'l1')
        self.assertNotIn('emergency', attention.state([], P, cards, NIGHT))      # no signals: nothing moves

    def test_no_permit_no_bell_at_night(self):
        """Repair 2: a stranger's pain under an any-pain rule is a special cause and still waits."""
        any_pain = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'wake': True}]}
        s = pain('s2', frm=X, from_holon=CELL)
        self.assertTrue(emergency.classify(s, any_pain, ctx())['special_cause'])
        st = attention.state([], P, [{'id': 's2'}], NIGHT, signals=[s], rule=any_pain, context={'members': {P, M}})
        self.assertEqual(st['interrupt_now'], [])
        self.assertEqual({x['id']: x['why'] for x in st['withheld']}['s2'], 'quiet hours')
        st = attention.state([], P, [{'id': 's2'}], NIGHT, signals=[s], rule=any_pain,
                             context={'members': {P, M}, 'agreements': agreement_items()})
        self.assertEqual(st['interrupt_now'], ['s2'])                            # with an Agreement's permit

    def test_gate_unchanged_without_wake(self):
        b = attention.budget([], P)
        a = attention.gate(self.cards(), b, NOW)
        self.assertNotIn('woken', a)
        self.assertEqual(attention.gate(self.cards(), b, NOW, wake=None), a)


class TestLimits(unittest.TestCase):
    """Law 6: Shewhart's limits, measured; fewer than eight points give no limit."""

    def test_three_sigma_by_pencil(self):
        # 2, 4, 4, 4, 5, 5, 7, 9: mean 5, population sd 2, so 5 ± 6 is -1 to 11.
        l = emergency.limits_from_history([2, 4, 4, 4, 5, 5, 7, 9])
        self.assertEqual((l['center'], l['upper'], l['lower'], l['n'], l['basis']), (5.0, 11.0, -1.0, 8, 'measured'))
        self.assertTrue(emergency.outside(11.5, l)); self.assertTrue(emergency.outside(-2, l))
        self.assertFalse(emergency.outside(10, l)); self.assertFalse(emergency.outside(None, l))
        l2 = emergency.limits_from_history([2, 4, 4, 4, 5, 5, 7, 9], k=1)
        self.assertEqual((l2['upper'], l2['lower']), (7.0, 3.0))

    def test_too_few(self):
        l = emergency.limits_from_history([1, 2, 3, 4, 5, 6, 7])
        self.assertEqual((l['basis'], l['upper'], l['lower'], l['n']), ('too few', None, None, 7))
        self.assertFalse(emergency.outside(1000, l))
        l = emergency.limits_from_history([1, 2, True, 'x', float('nan'), None, 3])
        self.assertEqual((l['n'], l['dropped'], l['basis']), (3, 4, 'too few'))
        self.assertEqual(emergency.limits_from_history(None)['n'], 0)

    def test_outside_limits_rule(self):
        r = {'basis': 'limits', 'rules': [{'signal': 'say', 'when': 'gap outside_limits', 'wake': True}]}
        hist = [2, 4, 4, 4, 5, 5, 7, 9]
        self.assertTrue(emergency.classify({'kind': 'say', 'gap': 12, 'history': hist}, r, ctx())['wake'])
        self.assertFalse(emergency.classify({'kind': 'say', 'gap': 8, 'history': hist}, r, ctx())['wake'])
        self.assertFalse(emergency.classify({'kind': 'say', 'gap': 99, 'history': hist[:5]}, r, ctx())['wake'])
        r = {'basis': 'limits', 'rules': [{'signal': 'say', 'when': 'outside_limits', 'wake': True}]}
        self.assertTrue(emergency.classify({'kind': 'say', 'value': -3, 'history': hist}, r, ctx())['wake'])


class TestGuards(unittest.TestCase):
    """Law 8: null-guards, determinism, pure functions, the CLI's files; the kit's words."""

    def test_nulls(self):
        for s in (None, {}, [], 3.5, 'pain'):
            c = emergency.classify(s, None, None)
            self.assertFalse(c['wake'])
            self.assertFalse(emergency.bell(s, None, None, None, None, NOW)['ring'])
        for r in (None, {}, [], 3.5, 'x', {'rules': 'x'}):
            self.assertIn('wake', emergency.classify(commitment(), r, ctx()))
        for ls in (None, {}, [], [None, 3, 'x', {}]):
            self.assertEqual(emergency.rule(ls, P)['basis'], 'default')
        self.assertEqual(emergency.rule([lim('l1', [])], None)['basis'], 'default')

    def test_nfc(self):
        nfd = unicodedata.normalize('NFD', 'person:zoë')
        nfc = unicodedata.normalize('NFC', 'person:zoë')
        r = emergency.rule([lim('l1', [{'signal': 'say', 'wake': True}], actor=nfd, for_=nfd)], nfc)
        self.assertEqual(r['set_by'], 'l1')
        self.assertTrue(emergency.classify(pain(frm=nfd), None, ctx(members={nfc}))['wake'])

    def test_deterministic_and_pure(self):
        boom = mock.Mock(side_effect=AssertionError('a file was opened'))
        with mock.patch.object(builtins, 'open', boom), mock.patch.object(io, 'open', boom):
            a = [emergency.classify(commitment(), None, ctx()), emergency.bell(pain(), None, [], {}, {M}, NOW),
                 emergency.limits_from_history([1, 2, 3, 4, 5, 6, 7, 8]), emergency.rule([], P)]
        b = [emergency.classify(commitment(), None, ctx()), emergency.bell(pain(), None, [], {}, {M}, NOW),
             emergency.limits_from_history([1, 2, 3, 4, 5, 6, 7, 8]), emergency.rule([], P)]
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        boom.assert_not_called()

    def test_the_cli(self):
        d = tempfile.mkdtemp()
        try:
            sp, vp, rp = (os.path.join(d, n) for n in ('s.json', 'v.json', 'r.json'))
            for path, value in ((sp, commitment()), (vp, [2, 4, 4, 4, 5, 5, 7, 9]),
                                (rp, {'basis': 'limits', 'rules': [{'signal': 'commitment', 'wake': False}]})):
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump(value, fh)
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                self.assertEqual(emergency._main(['classify', sp, '--members', M]), 0)
            self.assertTrue(json.loads(out.getvalue())['wake'])
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                self.assertEqual(emergency._main(['classify', sp, '--rule', rp]), 0)
            self.assertFalse(json.loads(out.getvalue())['wake'])
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                self.assertEqual(emergency._main(['limits', vp]), 0)
            self.assertEqual(json.loads(out.getvalue())['upper'], 11.0)
            link = os.path.join(d, 'link.json')
            os.symlink(sp, link)
            for bad in (link, os.path.join(d, 'missing.json')):
                out = io.StringIO()
                with mock.patch('sys.stdout', out):
                    self.assertEqual(emergency._main(['classify', bad]), 2)
                self.assertIn('problem', json.loads(out.getvalue()))
        finally:
            shutil.rmtree(d)

    def test_the_kits_words(self):
        src = _source().lower()
        for w in ('promise', ' house', 'estate', ' hq'):
            self.assertNotIn(w, src)


class TestRepairs(unittest.TestCase):
    """The independent review's repairs, each with a test that fails without it."""

    def test_a_members_security_rings_by_andon(self):
        sec = {'kind': 'security', 'id': 'x', 'from': AG, 'holon': HOME}
        b = emergency.bell(sec, None, [], {}, {P, AG}, NOW)
        self.assertEqual((b['wake'], b['ring'], b['permit']), (True, True, 'andon'))
        b = emergency.bell(dict(sec, **{'from': X, 'from_holon': CELL}), None, [], {}, {P, AG}, NOW)
        self.assertFalse(b['ring'])                                              # a stranger's needs a permit
        b = emergency.bell(dict(sec, **{'from': X, 'from_holon': CELL}), None, [],
                           agreement_items(bell=('security',)), {P, AG}, NOW)
        self.assertEqual(b['permit'], 'agreement')
        self.assertIn('security', emergency.ANDON_KINDS)

    def test_the_newest_line_by_the_instant(self):
        ls = [lim('old', [{'signal': 'say', 'wake': True}], ts='2026-10-21T12:00:00+05:00'),   # 07:00Z
              lim('new', [{'signal': 'say', 'wake': False}], ts='2026-10-21T10:00:00-07:00')]  # 17:00Z
        self.assertEqual(emergency.rule(ls, P)['set_by'], 'new')
        ls = [lim('b', [], ts='2026-10-21T10:00:00Z'), lim('a', [], ts='2026-10-21T03:00:00-07:00')]  # one instant
        self.assertEqual(emergency.rule(ls, P)['set_by'], 'b')                   # ties broken by id

    def test_the_subscription_answer_read_strictly(self):
        s = pain(frm=X, from_holon=CELL)
        any_pain = {'basis': 'limits', 'rules': [{'signal': 'sight', 'kind': ['pain'], 'wake': True}]}
        for ans in ('none', 'subscription', {'permit': 'none'}, {'ring': 'yes'}, ['pain'], (False, 'subscription'), 1):
            fake = mock.Mock()
            fake.bell_for = lambda rows, source, kind, a=ans: a
            with mock.patch.dict(sys.modules, {'subscriptions': fake}):
                self.assertFalse(emergency.bell(s, any_pain, [], {}, {P}, NOW)['ring'], ans)
        for ans in (True, (True, 'subscription'), {'ring': True}):
            fake = mock.Mock()
            fake.bell_for = lambda rows, source, kind, a=ans: a
            with mock.patch.dict(sys.modules, {'subscriptions': fake}):
                self.assertTrue(emergency.bell(s, any_pain, [], {}, {P}, NOW)['ring'], ans)

    def test_the_default_is_never_changed_through_an_answer(self):
        before = json.dumps(emergency.DEFAULT_RULES, sort_keys=True)
        emergency.rule([], P)['rules'][1]['kind'].append('hazard')
        c = emergency.classify(pain(), None, ctx())
        c['rule']['kind'].append('wonder')
        self.assertEqual(json.dumps(emergency.DEFAULT_RULES, sort_keys=True), before)

    def test_limits_never_infinite(self):
        l = emergency.limits_from_history([1e308] * 8)
        self.assertEqual((l['basis'], l['upper'], l['lower'], l['center']), ('overflow', None, None, None))
        json.dumps(l, allow_nan=False)
        l = emergency.limits_from_history([1e308, -1e308] * 4)
        self.assertEqual(l['basis'], 'overflow')
        json.dumps(l, allow_nan=False)

    def test_a_bare_line_is_no_rule(self):
        agents_line = lim('l9', [{'signal': 'say', 'wake': True}], actor=AG, reason='untrusted')
        for r in (agents_line, agents_line['body'], [{'signal': 'say', 'wake': True}],
                  {'rules': [{'signal': 'say', 'wake': True}]}):
            c = emergency.classify({'kind': 'say', 'id': 'm', 'from': M}, r, ctx())
            self.assertFalse(c['wake'])
            self.assertEqual(c['basis'], 'default')
            self.assertIn('refused', c)
        st = attention.state([], P, [{'id': 'm'}], NOW, signals=[{'kind': 'say', 'id': 'm', 'from': M}],
                             rule=agents_line, context={'members': {P, M}})
        self.assertEqual(st['interrupt_now'], [])
        own = emergency.rule([lim('l1', [{'signal': 'say', 'wake': True}])], P)
        self.assertTrue(emergency.classify({'kind': 'say', 'id': 'm'}, own, ctx())['wake'])

    def test_the_holons_own_signal_rings(self):
        own = {'kind': 'commitment', 'id': 'c1', 'holon': HOME, 'buffer_days': -2, 'critical': True}
        b = emergency.bell(own, None, [], {}, {P, M}, NOW)
        self.assertEqual((b['wake'], b['ring'], b['permit']), (True, True, 'own-holon'))
        self.assertEqual(emergency.bell(dict(own, **{'from': M}), None, [], {}, {P, M}, NOW)['permit'], 'own-holon')
        outside = dict(own, **{'from': X, 'from_holon': CELL})
        b = emergency.bell(outside, None, [], {}, {P, M}, NOW)
        self.assertEqual((b['wake'], b['ring'], b['permit']), (True, False, None))
        self.assertFalse(emergency.bell(dict(own, **{'from': X}), None, [], {}, {P, M}, NOW)['ring'])   # a non-member
        st = attention.state([], P, [{'id': 'c1'}], NIGHT, signals=[own], context={'members': {P, M}})
        self.assertEqual(st['interrupt_now'], ['c1'])

    def test_bell_reads_members_from_the_context_too(self):
        b = emergency.bell(pain(), None, [], {}, None, NOW, context={'members': [M]})
        self.assertEqual((b['wake'], b['ring'], b['permit']), (True, True, 'andon'))


if __name__ == '__main__':
    unittest.main()
