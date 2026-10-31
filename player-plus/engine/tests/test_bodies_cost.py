"""test_bodies_cost.py — the cost per wake, measured and shown (bodies.wakes, bodies.cost_of_attention).

Laws, each checked: seconds and tokens per wake are read from the two body lines, and a missing done
line gives null, honest; cost_of_attention is pure and deterministic, a day with no wakes shows zeros,
and unknown tokens are counted as wakes and said; null-guards on every input; the beat log is read by
the caller (beat_log), never by the measure.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_bodies_cost.py -v
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import bodies     # noqa: E402
import heartbeat  # noqa: E402

PERSON, AIDE, OTHER = 'person:player', 'agent:aide', 'agent:other'
CELL = 'holon:cell-a'
NOW = '2026-10-31T13:00:00-07:00'


def L(i, ts, body, actor=AIDE, typ='body', reason='delegated', holon=CELL):
    return {'id': i, 'ts': ts, 'actor': actor, 'for': PERSON, 'holon': holon, 'type': typ, 'body': body,
            'reason': reason}


def hb(i, ts, state, task='cadence', cost=None, host='cell-host', **extra):
    b = {'name': 'heartbeat', 'state': state, 'task': task, 'host': host, 'review_min': 0}
    if cost is not None:
        b['cost_tokens'] = cost
    b.update(extra)
    return L(i, ts, b)


def lines():
    d = '2026-10-31T'
    return [
        L('p1', d + '08:00:00-07:00', {'name': 'prime', 'state': 'working', 'task': 'Hold the desk', 'desk': True}),
        hb('w1', d + '09:00:00-07:00', 'working'),
        hb('w2', d + '09:02:30-07:00', 'done', cost=1200),
        hb('w3', d + '10:00:00-07:00', 'working', task='request'),
        hb('w4', d + '10:00:40-07:00', 'done', task='request', cost=None),           # the wake could not count
        hb('w5', d + '11:00:00-07:00', 'working', task='emergency', host='cell-host-2'),
        hb('w6', d + '11:00:05-07:00', 'done', task='emergency', cost=300, seconds=12.5, host=None),  # own measure
        L('s1', d + '12:00:00-07:00', {'name': 'aide-self', 'state': 'working', 'task': 'wake:request'}),
        L('s2', d + '12:01:00-07:00', {'name': 'aide-self', 'state': 'done', 'task': 'wake:request',
                                       'cost_tokens': 500}),
        L('r1', d + '12:10:00-07:00', {'model': 'm', 'body': AIDE, 'tokens': 77}, typ='route'),
    ]


class Wakes(unittest.TestCase):

    def test_seconds_and_tokens_from_the_two_body_lines(self):
        ws = bodies.wakes(lines(), NOW)
        by = {w['working']: w for w in ws}
        self.assertEqual((by['w1']['seconds'], by['w1']['cost_tokens'], by['w1']['done']), (150.0, 1200, 'w2'))
        self.assertEqual((by['w1']['reason'], by['w1']['host']), ('cadence', 'cell-host'))
        self.assertEqual((by['w3']['seconds'], by['w3']['cost_tokens']), (40.0, None))   # unknown, never zero
        self.assertEqual(by['w5']['seconds'], 12.5)                                        # the done line's own
        self.assertEqual(by['s1']['reason'], 'request')                                    # task 'wake:request'

    def test_a_missing_done_line_gives_null(self):
        ws = bodies.wakes(lines()[:2], NOW)
        self.assertEqual(len(ws), 1)
        self.assertEqual((ws[0]['seconds'], ws[0]['cost_tokens'], ws[0]['done'], ws[0]['closed']),
                         (None, None, None, None))
        # opened twice with no done line between: two wakes, the first with no end
        ws = bodies.wakes(lines()[:2] + [hb('w9', '2026-10-31T09:30:00-07:00', 'working')], NOW)
        self.assertEqual([w['seconds'] for w in ws], [None, None])
        # a done line with no working line: tokens read, seconds unknown
        ws = bodies.wakes([hb('d1', '2026-10-31T09:00:00-07:00', 'done', cost=9)], NOW)
        self.assertEqual((ws[0]['cost_tokens'], ws[0]['seconds'], ws[0]['opened']), (9, None, None))

    def test_only_an_agents_own_trusted_lines_count(self):
        ls = [hb('a', '2026-10-31T09:00:00-07:00', 'working'), hb('b', '2026-10-31T09:01:00-07:00', 'done', cost=5)]
        ls[0]['actor'] = ls[1]['actor'] = PERSON
        self.assertEqual(bodies.wakes(ls, NOW), [])
        ls = [hb('a', '2026-10-31T09:00:00-07:00', 'working')]
        ls[0]['reason'] = 'untrusted'
        self.assertEqual(bodies.wakes(ls, NOW), [])
        self.assertEqual(bodies.wakes([hb('f', '2026-11-01T09:00:00-07:00', 'working')], NOW), [])  # not yet

    def test_the_fold_adds_the_wake_fields_per_body(self):
        f = bodies.fold(lines(), NOW)
        b = {x['name']: x for x in f['bodies']}
        h = b['heartbeat']
        self.assertEqual((h['wakes'], h['wake_reason'], h['cost_tokens'], h['seconds'], h['host']),
                         (3, 'emergency', 300, 12.5, 'cell-host-2'))
        self.assertEqual(b['aide-self']['wake_reason'], 'request')
        self.assertEqual(b['aide-self']['cost_tokens'], 500)
        self.assertEqual(b['aide-self']['seconds'], 60.0)
        p = b['prime']                                   # not a wake body: route tokens, as before
        self.assertEqual((p['wakes'], p['wake_reason'], p['seconds'], p['cost_tokens'], p['route_tokens']),
                         (0, None, None, 77, 77))
        self.assertEqual(h['route_tokens'], 77)          # the same agent's route lines, kept apart
        self.assertIsNone(h['handoff'])                  # review_min 0: nothing to review
        self.assertEqual(f['cost']['attention']['basis'], {'tokens': 'body lines', 'requests': 'none'})
        self.assertEqual(f['cost']['attention']['today']['wakes'], 4)

    def test_a_done_line_with_a_review_still_hands_off(self):
        ls = [L('c', '2026-10-31T09:00:00-07:00', {'name': 'Draft', 'state': 'claimed', 'task': 'Draft it'}),
              L('d', '2026-10-31T10:00:00-07:00', {'name': 'Draft', 'state': 'done', 'review_min': 4})]
        self.assertEqual(bodies.fold(ls, NOW)['bodies'][0]['handoff'], 'd')


class CostOfAttention(unittest.TestCase):

    def log(self):
        return [{'as_of': '2026-10-31T09:00:00-07:00', 'woke': True, 'cost': {'requests': 2, 'bytes': 900, 'seconds': 0.4}},
                {'as_of': '2026-10-31T09:00:20-07:00', 'woke': False, 'cost': {'requests': 1, 'bytes': 100}},
                {'as_of': '2026-10-31T09:00:40-07:00', 'error': 'the beat stopped'},          # not a beat
                {'as_of': '2026-10-29T09:00:00-07:00', 'cost': {'requests': 4, 'bytes': 40}},
                {'as_of': 'not a time', 'cost': {'requests': 99}}, 'a string', None,
                {'as_of': '2026-10-31T09:01:00-07:00', 'cost': {'requests': True, 'bytes': -5}}]

    def test_per_day_with_the_pull_log(self):
        ls = lines() + [hb('y1', '2026-10-31T06:30:00+00:00', 'working'),         # 10/30 23:30 on the reader's clock
                        hb('y2', '2026-10-31T06:31:00+00:00', 'done', cost=100)]
        c = bodies.cost_of_attention(ls, None, self.log(), NOW, days=3)
        self.assertEqual([r['date'] for r in c['per_day']], ['2026-10-29', '2026-10-30', '2026-10-31'])
        d29, d30, d31 = c['per_day']
        self.assertEqual((d29['wakes'], d29['tokens'], d29['tokens_per_wake'], d29['forge_requests'], d29['bytes'],
                          d29['beats']), (0, 0, None, 4, 40, 1))
        self.assertEqual((d30['wakes'], d30['tokens'], d30['tokens_per_wake']), (1, 100, 100.0))
        self.assertEqual((d31['wakes'], d31['tokens'], d31['tokens_unknown']), (4, 2000, 1))
        self.assertEqual(d31['tokens_per_wake'], round(2000 / 3, 1))            # over the wakes whose tokens are known
        self.assertEqual((d31['forge_requests'], d31['bytes'], d31['beats']), (3, 1000, 3))
        self.assertEqual(d31['by_reason'], {'cadence': 1, 'request': 2, 'emergency': 1})
        self.assertEqual(d31['by_holon'], {CELL: {'wakes': 4, 'tokens': 2000, 'tokens_unknown': 1}})
        self.assertEqual(c['today'], d31)
        self.assertEqual(c['basis'], {'tokens': 'body lines', 'requests': 'the pull log'})
        self.assertTrue(any('tokens are unknown, not zero' in s for s in c['said']))
        self.assertEqual(c['as_of'], '2026-10-31T13:00:00-07:00')

    def test_a_day_with_no_wakes_shows_zeros(self):
        c = bodies.cost_of_attention([], None, [], NOW)
        t = c['today']
        self.assertEqual((t['wakes'], t['tokens'], t['tokens_unknown'], t['forge_requests'], t['bytes'], t['beats']),
                         (0, 0, 0, 0, 0, 0))
        self.assertIsNone(t['tokens_per_wake'])          # no wake to divide by: said as null, never invented
        self.assertTrue(c['said'][0].startswith('no wake was recorded'))

    def test_no_pull_log_is_said(self):
        c = bodies.cost_of_attention(lines(), None, None, NOW)
        self.assertEqual(c['basis']['requests'], 'none')
        self.assertEqual((c['today']['forge_requests'], c['today']['bytes'], c['today']['beats']), (None, None, None))
        self.assertTrue(any('no beat log was given' in s for s in c['said']))

    def test_pure_and_deterministic(self):
        ls = lines()
        a = json.dumps(bodies.cost_of_attention(ls, bodies.fold(ls, NOW)['bodies'], self.log(), NOW, 7), sort_keys=True)
        sh = list(ls)
        random.Random(7).shuffle(sh)
        b = json.dumps(bodies.cost_of_attention(sh, bodies.fold(sh, NOW)['bodies'], self.log(), NOW, 7), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(ls, lines())                    # the input is not changed
        self.assertEqual(json.dumps(bodies.fold(ls, NOW), sort_keys=True), json.dumps(bodies.fold(sh, NOW), sort_keys=True))

    def test_the_wake_bodies_from_the_fold(self):
        f = bodies.fold(lines(), NOW)
        c = bodies.cost_of_attention(lines(), f['bodies'], None, NOW)
        self.assertEqual([b['name'] for b in c['bodies']], ['aide-self', 'heartbeat'])
        self.assertEqual(c['bodies'][1]['wakes'], 3)

    def test_null_guards(self):
        for bad in (None, {}, [], 3.5, 'text', [None, 1, 'x', {}, {'type': 'body'}]):
            c = bodies.cost_of_attention(bad, bad, bad if not isinstance(bad, list) else None, NOW, bad)
            self.assertEqual(c['today']['wakes'], 0)
            self.assertEqual(c['days'], 3 if bad == 3.5 else 1)               # a float of days is read whole
            self.assertEqual(bodies.wakes(bad, NOW), [])
        self.assertIn('bodies', bodies.fold(3.5, NOW))
        for d, n in ((0, 1), (-4, 1), (True, 1), (7.0, 7), (float('nan'), 1), (10 ** 6, bodies.MAX_DAYS)):
            self.assertEqual(bodies.cost_of_attention([], None, None, NOW, d)['days'], n)
        odd = [hb('a', '2026-10-31T09:00:00-07:00', 'working', task=None, host=7),
               hb('b', '2026-10-31T09:00:10-07:00', 'done', task=None, cost=12.6),
               hb('c', '2026-10-31T09:10:00-07:00', 'working', task='wake:cadence'),
               hb('d', '2026-10-31T09:10:10-07:00', 'done', cost=True),
               hb('e', 'not a time', 'done', cost=5),
               L('f', '2026-10-31T09:20:00-07:00', {'name': 'aide-x', 'state': 'working', 'task': 'WAKE: réquest'}),
               L('g', '2026-10-31T09:20:00-07:00', 'not a body'),
               hb('h', '2026-10-31T09:30:00-07:00', 'done', cost=-3, seconds=float('inf'))]
        ws = bodies.wakes(odd, NOW)
        self.assertEqual([(w['working'], w['cost_tokens']) for w in ws],
                         [('a', 12.6), ('c', None), ('f', None), (None, None)])
        self.assertEqual(ws[0]['host'], 'cell-host'); self.assertIsNone(ws[0]['reason'])
        self.assertEqual(ws[2]['reason'], 'réquest')                      # read as NFC
        self.assertIsNone(ws[3]['seconds'])

    def test_beat_log_is_the_callers_read(self):
        d = tempfile.mkdtemp(prefix='lionsberg-bodies-cost-')
        try:
            self.assertIsNone(bodies.beat_log(d))                              # not beaten here yet
            self.assertIsNone(bodies.beat_log(None)); self.assertIsNone(bodies.beat_log(3.5))
            for e in self.log()[:2]:
                self.assertEqual(heartbeat._log(d, e), '')
            got = bodies.beat_log(d)
            self.assertEqual((len(got['rows']), got['from']), (2, '2026-10-31T09:00:00-07:00'))
            c = bodies.cost_of_attention(lines(), None, got, NOW)
            self.assertEqual((c['today']['forge_requests'], c['today']['beats']), (3, 2))
            e = tempfile.mkdtemp(prefix='lionsberg-bodies-link-')
            os.symlink(os.path.join(d, heartbeat.LOG_NAME), os.path.join(e, heartbeat.LOG_NAME))
            self.assertIsNone(bodies.beat_log(e))                              # a link is not read
            shutil.rmtree(e, ignore_errors=True)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Repairs(unittest.TestCase):
    """The review's repairs: equal stamps pair, unmeasured seconds are null, a cut log is said."""

    def test_equal_stamps_pair_open_before_done(self):
        ts = '2026-10-31T09:00:00-07:00'
        # the done line's id sorts first; the pair must still hold
        ls = [hb('zz-working', ts, 'working'), hb('aa-done', ts, 'done', cost=42)]
        ws = bodies.wakes(ls, NOW)
        self.assertEqual(len(ws), 1)
        self.assertEqual((ws[0]['working'], ws[0]['done'], ws[0]['cost_tokens']), ('zz-working', 'aa-done', 42))
        h = {b['name']: b for b in bodies.fold(ls, NOW)['bodies']}['heartbeat']
        self.assertEqual((h['wakes'], h['cost_tokens']), (1, 42))

    def test_equal_stamps_and_no_seconds_give_null_and_say_so(self):
        ts = '2026-10-31T09:00:00-07:00'
        ws = bodies.wakes([hb('w', ts, 'working'), hb('d', ts, 'done', cost=1)], NOW)
        self.assertEqual((ws[0]['seconds'], ws[0]['seconds_basis']), (None, 'unknown: both lines carry one time'))
        c = bodies.cost_of_attention([hb('w', ts, 'working'), hb('d', ts, 'done', cost=1)], None, None, NOW)
        self.assertTrue(any('no seconds of their own' in x for x in c['said']))
        ws = bodies.wakes([hb('w', ts, 'working'), hb('d', ts, 'done', cost=1, seconds=37)], NOW)
        self.assertEqual((ws[0]['seconds'], ws[0]['seconds_basis']), (37.0, 'the done line'))

    def test_days_before_the_log_read_are_null_and_said(self):
        got = {'rows': [{'as_of': '2026-10-30T10:00:00-07:00', 'cost': {'requests': 2, 'bytes': 20}}],
               'from': '2026-10-30T10:00:00-07:00'}
        c = bodies.cost_of_attention([], None, got, NOW, days=4)
        self.assertEqual([r['beats'] for r in c['per_day']], [None, None, 1, 0])
        self.assertEqual(c['per_day'][0]['forge_requests'], None)
        self.assertTrue(any('the beat log read begins at 2026-10-30T10:00:00-07:00' in x and '2 day(s)' in x
                            for x in c['said']))
        # a plain list: its oldest row marks the start the same way
        c = bodies.cost_of_attention([], None, got['rows'], NOW, days=2)
        self.assertEqual([r['beats'] for r in c['per_day']], [1, 0])

    def test_trust_through_gamecore(self):
        for mark in ({'reason': 'UNTRUSTED'}, {'reason': 'Untrusted'}, {'_kind': 'untrusted'}):
            ls = [hb('a', '2026-10-31T09:00:00-07:00', 'working'), hb('b', '2026-10-31T09:01:00-07:00', 'done', cost=5)]
            for l in ls:
                l.update(mark)
            self.assertEqual(bodies.wakes(ls, NOW), [], mark)

    def test_a_line_over_64_kib(self):
        long_task = 'wake:' + 'x' * 70000
        ls = [L('a', '2026-10-31T09:00:00-07:00', {'name': 'aide-long', 'state': 'working', 'task': long_task}),
              L('b', '2026-10-31T09:01:00-07:00', {'name': 'aide-long', 'state': 'done', 'task': long_task,
                                                   'cost_tokens': 3})]
        self.assertGreater(len(json.dumps(ls[0])), 64 * 1024)
        ws = bodies.wakes(ls, NOW)
        self.assertEqual(len(ws[0]['reason']), bodies.REASON_MAX)
        c = bodies.cost_of_attention(ls, bodies.fold(ls, NOW)['bodies'], None, NOW)
        self.assertEqual([len(k) for k in c['today']['by_reason']], [bodies.REASON_MAX])
        self.assertEqual(len(c['bodies'][0]['wake_reason']), bodies.REASON_MAX)
        d = tempfile.mkdtemp(prefix='lionsberg-bodies-long-')
        try:
            heartbeat._log(d, {'as_of': '2026-10-31T09:00:00-07:00', 'pad': 'y' * 70000, 'cost': {'requests': 1}})
            got = bodies.beat_log(d)
            self.assertEqual(bodies.cost_of_attention([], None, got, NOW)['today']['forge_requests'], 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_float_token_count_is_said_not_rounded(self):
        ls = [hb('a', '2026-10-31T09:00:00-07:00', 'working'), hb('b', '2026-10-31T09:01:00-07:00', 'done', cost=12.6)]
        c = bodies.cost_of_attention(ls, None, None, NOW)
        self.assertEqual(c['today']['tokens'], 12.6)
        self.assertTrue(any('not a whole number' in x for x in c['said']))
        self.assertEqual(bodies.wakes([hb('b', '2026-10-31T09:01:00-07:00', 'done', cost=40.0)], NOW)[0]['cost_tokens'], 40)


class RealWake(unittest.TestCase):
    """A real wake through heartbeat.beat, read back by bodies: one wake, with its tokens."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ENGINE, 'tests'))
        import test_heartbeat as th
        cls.th = th
        th.setUpModule()

    @classmethod
    def tearDownClass(cls):
        cls.th.tearDownModule()

    def test_a_real_wake_is_one_wake_with_its_tokens(self):
        th = self.th
        import record
        for i in range(8):                       # line ids are hashes: eight homes reach both id orders
            h = th.make_home(os.path.join(tempfile.mkdtemp(dir=th.WORK), 'home'))
            w = th.FakeWake()
            heartbeat.beat(h, now=th.at(0), wake=w)
            r = heartbeat.beat(h, now=th.at(3600), wake=w)
            self.assertTrue(r['woke'], r['said'])
            path = os.path.join(h, 'record', record.actor_file(th.AIDE))
            with open(path, encoding='utf-8') as f:
                ls = [json.loads(x) for x in f if x.strip()]
            ws = bodies.wakes(ls, th.at(3700))
            self.assertEqual(len(ws), 1, ws)
            self.assertEqual(ws[0]['cost_tokens'], 42)
            done = [l for l in ls if l.get('id') == ws[0]['done']][0]
            work = [l for l in ls if l.get('id') == ws[0]['working']][0]
            want = done['body'].get('seconds')
            if want is None:                     # else from the two lines' times, null when they are one time
                gap = (bodies.parse_time(done['ts']) - bodies.parse_time(work['ts'])).total_seconds()
                want = gap if gap > 0 else None
            self.assertEqual(ws[0]['seconds'], None if want is None else float(want))
            hb_ = {b['name']: b for b in bodies.fold(ls, th.at(3700))['bodies']}['heartbeat']
            self.assertEqual((hb_['wakes'], hb_['cost_tokens']), (1, 42))


if __name__ == '__main__':
    unittest.main()
