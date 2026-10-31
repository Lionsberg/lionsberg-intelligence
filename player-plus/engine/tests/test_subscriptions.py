"""test_subscriptions.py — the Subscription Card: what a holon hears, from whom, how often, where.

Each law of subscriptions.py has a test that fails when it is broken. Lines and folded items are
built by hand, in the shapes record.py writes and folds.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_subscriptions.py -v
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest
from contextlib import redirect_stdout, redirect_stderr

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import subscriptions as sub   # noqa: E402

HOME = 'a' * 64        # the person's own holon
CELL = 'c' * 64        # a cell joined, where an Agreement is written
FAR = 'f' * 64         # a distant holon
OTHER = 'e' * 64       # a joined cell with no Card and no Agreement
P, S, X = 'person:player', 'person:steward', 'person:stranger'
AG = 'agent:player'
NOW = '2026-10-31T12:00:00-07:00'


def line(i, ts, body, actor=P, for_=None, reason='human', holon=HOME, links=None):
    return {'v': 1, 'id': ('%x' % i) * 64 if i < 16 else str(i), 'ts': ts, 'actor': actor,
            'for': for_ or actor, 'holon': holon, 'type': 'subscribe', 'body': body,
            'links': links or {}, 'audience': 'holon', 'reason': reason, 'prev': '', 'sig': ''}


def ag(id_='9' * 64, state='agreed', **kw):
    it = {'id': id_, 'kind': 'agreement', 'holon': CELL, 'state': state, 'actor': P, 'for': P,
          'ts': '2026-10-20T10:00:00-07:00', 'with': CELL, 'crosses': ['request', 'commit'],
          'cadence': {'request': 20, 'commit': 600}, 'permits': {'write': True, 'bell': ['hazard']},
          'until': '2027-03-20', 'links': {}}
    if state == 'agreed':
        it.update(agreed_by=S, agreed_ts='2026-10-20T11:00:00-07:00', agreed_with=HOME)
    it.update(kw)
    return it


def admitted():
    return {HOME: {P: {'via': 'inception'}, AG: {'via': 'affirm'}},
            CELL: {S: {'via': 'inception'}, P: {'via': 'join'}},
            OTHER: {X: {'via': 'inception'}, P: {'via': 'join'}}}


def fold(*agreements, trust=None, subs=None, adm=True, **lists):
    f = {'agreements': list(agreements), 'commitments': [], 'as_of': NOW}
    if subs is not None:
        f['subscriptions'] = subs
    for k, ids in lists.items():                     # invalid, unverified, forked, proposals
        f[k] = [{'id': i} for i in ids]
    if adm:
        f['admitted'] = admitted()
    if trust is not None:
        f['trust'] = trust
    return f


def row(rows, source):
    return next(r for r in rows if r['source'] == source)


class TestOwnLines(unittest.TestCase):
    """Law 1: only the person's own trusted lines count."""

    def test_own_line_counts(self):
        rows = sub.subscriptions([line(1, NOW, {'source': FAR, 'cadence': 86400})], P, now=NOW)
        r = row(rows, FAR)
        self.assertEqual(r['basis'], 'subscription')
        self.assertEqual(set(r['cadence'].values()), {86400})

    def test_agent_and_untrusted_change_nothing(self):
        base = [line(1, '2026-10-30T10:00:00-07:00', {'source': FAR, 'cadence': 86400})]
        bad = [line(2, '2026-10-30T11:00:00-07:00', {'source': FAR, 'cadence': 20}, actor=AG, for_=P,
                    reason='delegated'),
               line(3, '2026-10-30T12:00:00-07:00', {'source': FAR, 'cadence': 20}, reason='untrusted'),
               line(4, '2026-10-30T13:00:00-07:00', {'source': FAR, 'cadence': 20}, actor=S),
               line(5, '2026-10-30T14:00:00-07:00', {'source': FAR, 'cadence': 20}, actor=P, for_=S)]
        a = sub.subscriptions(base, P, now=NOW)
        b = sub.subscriptions(base + bad, P, now=NOW)
        self.assertEqual(a, b)
        why = {x['id'][:1]: x['why'] for x in sub.ignored(base + bad, P)}
        self.assertIn('agent', why['2'])
        self.assertIn('untrusted', why['3'])

    def test_fold_trust_retraction_and_home(self):
        l1 = line(1, '2026-10-30T10:00:00-07:00', {'source': FAR, 'cadence': 86400})
        l2 = line(2, '2026-10-30T11:00:00-07:00', {'source': FAR, 'cadence': 20})
        l3 = line(3, '2026-10-30T12:00:00-07:00', {'source': FAR, 'cadence': 60}, holon=CELL)
        trust = {l1['id']: 'home', l2['id']: 'unverified', l3['id']: 'signed'}
        rows = sub.subscriptions([l1, l2, l3], P, fold(trust=trust), NOW)
        self.assertEqual(set(row(rows, FAR)['cadence'].values()), {86400})   # l2 untrusted; l3 not home
        retracted = fold(trust={l1['id']: 'home'}, subs=[{'id': l1['id'], 'state': 'retracted'}])
        self.assertNotIn(FAR, [r['source'] for r in sub.subscriptions([l1], P, retracted, NOW)])

    def test_vouched_never_trusted(self):
        l1 = line(1, NOW, {'source': FAR, 'cadence': 86400})
        f = fold(trust={l1['id']: 'vouched'}, subs=[{'id': l1['id']}])
        self.assertNotIn(FAR, [r['source'] for r in sub.subscriptions([l1], P, f, NOW)])
        self.assertIn('does not trust', sub.ignored([l1], P, f)[0]['why'])

    def test_forked_invalid_proposals_never_count(self):
        l1 = line(1, '2026-10-30T10:00:00-07:00', {'source': FAR, 'surface': 'wall'})
        l2 = line(2, '2026-10-30T11:00:00-07:00', {'source': FAR, 'surface': 'pad'})
        held = [{'id': l1['id']}, {'id': l2['id']}]
        trust = {l1['id']: 'signed', l2['id']: 'signed'}
        for k in ('forked', 'invalid', 'proposals', 'unverified'):
            f = fold(trust=trust, subs=held, **{k: [l2['id']]})
            self.assertEqual(row(sub.subscriptions([l1, l2], P, f, NOW), FAR)['surface'], 'wall', k)
        f = fold(trust=trust, subs=held)
        self.assertEqual(row(sub.subscriptions([l1, l2], P, f, NOW), FAR)['surface'], 'pad')

    def test_a_line_the_fold_does_not_hold_never_counts(self):
        l1 = line(1, NOW, {'source': FAR})
        f = fold(trust={l1['id']: 'home'}, subs=[])
        self.assertNotIn(FAR, [r['source'] for r in sub.subscriptions([l1], P, f, NOW)])

    def test_an_agent_has_no_card(self):
        self.assertEqual(sub.subscriptions([line(1, NOW, {'source': FAR}, actor=AG)], AG), [])


class TestOverlay(unittest.TestCase):
    """Law 2: later overlays earlier field by field; an int cadence applies to every signal."""

    def test_field_by_field(self):
        ls = [line(1, '2026-10-30T10:00:00-07:00', {'source': FAR, 'signals': ['sight', 'say'],
                                                     'cadence': {'sight': 3600}, 'surface': 'wall'}),
              line(2, '2026-10-30T11:00:00-07:00', {'source': FAR, 'cadence': {'say': 60}, 'bell': ['hazard']})]
        r = row(sub.subscriptions(ls, P, now=NOW), FAR)
        self.assertEqual(r['signals'], ['say', 'sight'])
        self.assertEqual(r['cadence'], {'say': 60, 'sight': 3600})
        self.assertEqual(r['surface'], 'wall')
        self.assertEqual(r['bell'], ['hazard'])
        self.assertEqual(r['set_by']['surface'], ls[0]['id'])
        self.assertEqual(r['set_by']['cadence'], ls[1]['id'])

    def test_order_is_by_time_not_by_position(self):
        a = line(1, '2026-10-30T11:00:00-07:00', {'source': FAR, 'surface': 'pad'})
        b = line(2, '2026-10-30T10:00:00-07:00', {'source': FAR, 'surface': 'hud'})
        self.assertEqual(row(sub.subscriptions([a, b], P, now=NOW), FAR)['surface'], 'pad')

    def test_overlay_follows_the_chain_not_the_stamp(self):
        a = line(1, '2026-10-30T11:00:00-07:00', {'source': FAR, 'surface': 'pad'})
        b = line(2, '2026-10-30T10:00:00-07:00', {'source': FAR, 'surface': 'hud'})
        b['prev'] = a['id']                                   # B names A, but is stamped an hour earlier
        self.assertEqual(row(sub.subscriptions([b, a], P, now=NOW), FAR)['surface'], 'hud')
        trust = {a['id']: 'home', b['id']: 'home'}
        f = fold(trust=trust, subs=[{'id': a['id']}, {'id': b['id']}])
        self.assertEqual(row(sub.subscriptions([b, a], P, f, NOW), FAR)['surface'], 'hud')
        f = fold(trust=trust, subs=[{'id': b['id']}, {'id': a['id']}])    # the fold's order decides
        self.assertEqual(row(sub.subscriptions([a, b], P, f, NOW), FAR)['surface'], 'pad')

    def test_every_signal_the_cadence_names_is_heard(self):
        r = row(sub.subscriptions([line(1, NOW, {'source': FAR, 'cadence': {'wonder': 60}})], P, now=NOW), FAR)
        self.assertIn('wonder', r['signals'])
        self.assertEqual(r['cadence']['wonder'], 60)
        r = row(sub.subscriptions([line(1, NOW, {'source': FAR, 'signals': ['say'], 'cadence': {'sight': 60}})],
                                  P, now=NOW), FAR)
        self.assertEqual(r['signals'], ['say', 'sight'])

    def test_int_cadence_every_signal(self):
        ls = [line(1, '2026-10-30T10:00:00-07:00', {'source': FAR, 'signals': ['request', 'say', 'sight'],
                                                     'cadence': {'say': 60}}),
              line(2, '2026-10-30T11:00:00-07:00', {'source': FAR, 'cadence': 7776000})]
        r = row(sub.subscriptions(ls, P, now=NOW), FAR)
        self.assertEqual(r['cadence'], {'request': 7776000, 'say': 7776000, 'sight': 7776000})
        ls.append(line(3, '2026-10-30T12:00:00-07:00', {'source': FAR, 'cadence': {'request': 20}}))
        r = row(sub.subscriptions(ls, P, now=NOW), FAR)
        self.assertEqual(r['cadence'], {'request': 20, 'say': 7776000, 'sight': 7776000})

    def test_supersede_read_from_the_fold_item(self):
        l1 = line(1, NOW, {'source': FAR, 'cadence': 86400})
        f = fold(trust={l1['id']: 'home'}, subs=[{'id': l1['id'], 'source': FAR, 'cadence': 3600}])
        self.assertEqual(set(row(sub.subscriptions([l1], P, f, NOW), FAR)['cadence'].values()), {3600})


class TestAgreement(unittest.TestCase):
    """Law 3: an Agreement fills what the Card leaves unsaid and never overrides what it says."""

    def test_fills_unsaid(self):
        ls = [line(1, NOW, {'source': CELL, 'signals': ['request', 'commit', 'say'], 'cadence': {'say': 300}})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(r['cadence'], {'commit': 600, 'request': 20, 'say': 300})
        self.assertEqual(r['filled']['cadence'], {'commit': 'agreement', 'request': 'agreement', 'say': 'subscription'})
        self.assertEqual(r['basis'], 'agreement')
        self.assertEqual(r['agreement'], '9' * 64)
        self.assertEqual(r['bell'], ['hazard'])

    def test_never_overrides(self):
        ls = [line(1, NOW, {'source': CELL, 'cadence': 86400, 'bell': ['wonder']})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(set(r['cadence'].values()), {86400})
        self.assertEqual(r['bell'], ['hazard', 'wonder'])           # the Agreement's bell adds
        self.assertEqual(r['filled']['bell'], {'hazard': 'agreement', 'wonder': 'subscription'})

    def test_per_signal_card_wins(self):
        ls = [line(1, NOW, {'source': CELL, 'cadence': {'request': 600}})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(r['cadence']['request'], 600)
        self.assertEqual(r['cadence']['commit'], 600)                  # the Agreement's, filling
        self.assertEqual(r['filled']['cadence'], {'commit': 'agreement', 'request': 'subscription'})

    def test_card_cadence_kept_beside_the_agreement(self):
        ls = [line(1, NOW, {'source': CELL, 'cadence': {'say': 60}})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(r['signals'], ['commit', 'request', 'say'])
        self.assertEqual(r['cadence'], {'commit': 600, 'request': 20, 'say': 60})

    def test_named_but_proposed_fills_nothing(self):
        ls = [line(1, NOW, {'source': CELL, 'agreement': '9' * 64})]
        r = row(sub.subscriptions(ls, P, fold(ag(state='proposed')), NOW), CELL)
        self.assertEqual(r['basis'], 'subscription')
        self.assertEqual(r['bell'], [])
        self.assertEqual(set(r['cadence'].values()), {300})
        self.assertTrue(any('proposed' in n for n in r['why']))

    def test_agreement_alone_gives_a_row(self):
        rows = sub.subscriptions([], P, fold(ag()), NOW)
        r = row(rows, CELL)
        self.assertEqual(r['basis'], 'agreement')
        self.assertEqual(r['signals'], ['commit', 'request'])
        self.assertEqual(r['cadence'], {'commit': 600, 'request': 20})
        self.assertEqual(r['set_by'], {})

    def test_proposed_or_named_but_not_standing_fills_nothing(self):
        rows = sub.subscriptions([], P, fold(ag(state='proposed')), NOW)
        self.assertEqual(row(rows, CELL)['basis'], 'default')
        ls = [line(1, NOW, {'source': CELL, 'agreement': '8' * 64})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(r['basis'], 'subscription')
        self.assertTrue(any('not held' in n for n in r['why']))

    def test_named_by_links_serves(self):
        ls = [line(1, NOW, {'source': CELL}, links={'serves': ['9' * 64]})]
        r = row(sub.subscriptions(ls, P, fold(ag()), NOW), CELL)
        self.assertEqual(r['agreement'], '9' * 64)
        self.assertEqual(r['basis'], 'agreement')


class TestDefault(unittest.TestCase):
    def test_joined_cell_with_neither(self):
        rows = sub.subscriptions([], P, fold(), NOW)
        self.assertEqual([r['source'] for r in rows], [CELL, OTHER])
        r = row(rows, OTHER)
        self.assertEqual(r['basis'], 'default')
        self.assertEqual(r['signals'], sorted(sub.DEFAULT['signals']))
        self.assertEqual(set(r['cadence'].values()), {300})
        self.assertEqual(r['surface'], 'deal')

    def test_default_overridable(self):
        rows = sub.subscriptions([], P, joined=[OTHER], default={'cadence': 60, 'signals': ['say']})
        self.assertEqual(rows[0]['cadence'], {'say': 60})

    def test_card_unsaid_falls_to_default(self):
        r = sub.subscriptions([line(1, NOW, {'source': FAR, 'signals': ['sight']})], P, now=NOW)[0]
        self.assertEqual(r['cadence'], {'sight': 300})
        self.assertEqual(r['filled']['cadence'], {'sight': 'default'})
        self.assertEqual(r['basis'], 'subscription')


class TestDue(unittest.TestCase):
    """Law 4: due is deterministic, says overdue seconds; a source never seen is due now."""

    def rows(self):
        return sub.subscriptions([line(1, NOW, {'source': FAR, 'signals': ['say', 'sight'],
                                                 'cadence': {'say': 20, 'sight': 86400}})], P, now=NOW)

    def test_due_and_overdue(self):
        last = {FAR: {'say': '2026-10-31T11:59:00-07:00', 'sight': '2026-10-31T00:00:00-07:00'}}
        d = sub.due(self.rows(), last, NOW)
        self.assertEqual([(x['signal'], x['overdue_s']) for x in d], [('say', 40)])
        self.assertEqual(d[0]['due_at'], '2026-10-31T11:59:20-07:00')

    def test_never_seen_is_due_now(self):
        d = sub.due(self.rows(), {}, NOW)
        self.assertEqual({x['signal'] for x in d}, {'say', 'sight'})
        self.assertTrue(all(x['overdue_s'] == 0 and x['last'] is None and x['due_at'] == NOW for x in d))

    def test_one_time_for_every_signal_and_determinism(self):
        last = {FAR.upper(): '2026-10-29T12:00:00-07:00'}
        a = sub.due(self.rows(), last, NOW)
        self.assertEqual([x['signal'] for x in a], ['say', 'sight'])     # most overdue first (say came due first)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(sub.due(self.rows(), last, NOW), sort_keys=True))

    def test_due_is_sorted(self):
        ls = [line(1, NOW, {'source': OTHER, 'signals': ['say'], 'cadence': 60}),
              line(2, NOW, {'source': FAR, 'signals': ['say', 'sight'], 'cadence': 60})]
        last = {FAR: {'say': '2026-10-31T11:58:00-07:00', 'sight': '2026-10-31T11:00:00-07:00'},
                OTHER: {'say': '2026-10-31T11:30:00-07:00'}}
        d = sub.due(sub.subscriptions(ls, P, now=NOW), last, NOW)
        self.assertEqual([(x['source'], x['signal'], x['overdue_s']) for x in d],
                         [(FAR, 'sight', 3540), (OTHER, 'say', 1740), (FAR, 'say', 60)])

    def test_cadence_and_surface_for(self):
        rows = self.rows()
        self.assertEqual(sub.cadence_for(rows, FAR, 'say'), 20)
        self.assertIsNone(sub.cadence_for(rows, FAR, 'commit'))
        self.assertIsNone(sub.cadence_for(rows, OTHER, 'say'))
        self.assertEqual(sub.surface_for(rows, FAR, 'sight'), 'deal')
        self.assertIsNone(sub.surface_for(rows, FAR, 'commit'))


class TestAndon(unittest.TestCase):
    """Law 5: a member's pain rings; a stranger's does not; an explicit bell permit does."""

    def test_member_stranger_permit(self):
        rows = sub.subscriptions([line(1, NOW, {'source': X, 'bell': ['pain']})], P, now=NOW)
        members = [P, S]
        self.assertEqual(sub.bell_for([], S, 'pain', members), (True, 'andon'))
        self.assertEqual(sub.bell_for([], S, 'fault', members), (True, 'andon'))
        self.assertEqual(sub.bell_for([], S, 'hazard', members), (False, 'none'))
        self.assertEqual(sub.bell_for([], X, 'pain', members), (False, 'none'))
        self.assertEqual(sub.bell_for(rows, X, 'pain', members), (True, 'subscription'))

    def test_agreement_permit_and_members_map(self):
        rows = sub.subscriptions([], P, fold(ag()), NOW)
        self.assertEqual(sub.bell_for(rows, CELL, 'hazard'), (True, 'agreement'))
        self.assertEqual(sub.bell_for(rows, CELL, 'pain'), (False, 'none'))
        self.assertEqual(sub.bell_for([], S, 'pain', {S: {'via': 'join'}}), (True, 'andon'))
        self.assertEqual(sub.bell_for([], S, 'pain', {S: {'via': 'clone', 'ended': True}}), (False, 'none'))


class TestRisesFirst(unittest.TestCase):
    """Law 6: rises_first covers each listed type."""

    def ln(self, typ, body, actor=S, reason='human'):
        return {'type': typ, 'actor': actor, 'for': actor, 'body': body, 'reason': reason}

    def test_each_type(self):
        self.assertTrue(sub.rises_first(self.ln('request', {'to': P}), P))
        self.assertTrue(sub.rises_first(self.ln('request', {'to': AG}), P, agents=[AG]))
        self.assertTrue(sub.rises_first(self.ln('rfg', {'to': HOME, 'question': 'q'}), P, holons=[HOME]))
        self.assertTrue(sub.rises_first(self.ln('say', {'to': [X, P], 'text': 't'}), P))
        self.assertTrue(sub.rises_first(self.ln('commit', {'committee': P, 'card': '1', 'by': '2026-11-01'}), P))
        self.assertTrue(sub.rises_first(self.ln('escalate', {'to': HOME, 'about': '1', 'blast_radius': 'b'}), P,
                                        holons=[HOME]))

    def test_what_does_not_rise(self):
        self.assertFalse(sub.rises_first(self.ln('request', {'to': X}), P))
        self.assertFalse(sub.rises_first(self.ln('say', {'text': 't'}), P))
        self.assertFalse(sub.rises_first(self.ln('escalate', {'to': FAR}), P, holons=[HOME]))
        self.assertFalse(sub.rises_first(self.ln('sight', {'to': P}), P))
        self.assertFalse(sub.rises_first(self.ln('request', {'to': P}, reason='untrusted'), P))
        self.assertFalse(sub.rises_first(self.ln('request', {'to': P}, actor=P), P))
        own_agent = dict(self.ln('request', {'to': P}, actor=AG), **{'for': P})
        self.assertFalse(sub.rises_first(own_agent, P, agents=[AG]))
        self.assertFalse(sub.rises_first(None, P))
        self.assertFalse(sub.rises_first(self.ln('request', {'to': P}), AG))


class TestGuardsAndWords(unittest.TestCase):
    """Law 7: null-guards; words; quote no one."""

    def test_null_guards(self):
        for bad in (None, {}, [], 'x', 3.5, [None, 'x', 1]):
            self.assertEqual(sub.subscriptions(bad, P), [])
            self.assertEqual(sub.due(bad, bad, NOW), [])
            self.assertEqual(sub.bell_for(bad, S, 'pain', bad), (False, 'none'))
            self.assertIsNone(sub.cadence_for(bad, FAR, 'say'))
        self.assertEqual(sub.subscriptions([], None), [])
        self.assertEqual(sub.due([], {}, None), [])
        odd = [line(1, None, {'source': FAR, 'cadence': {'say': 20.0, 'sight': 1.5, 'x': True}, 'signals': 'say',
                              'surface': 'nowhere', 'bell': {'elided': 'd'}}),
               line(2, NOW, {'source': '', 'cadence': 20}), line(3, NOW, 'not a body')]
        r = sub.subscriptions(odd, P, now=NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['cadence'], {'say': 20})
        self.assertEqual(r[0]['surface'], 'deal')
        self.assertEqual(r[0]['bell'], [])

    def test_nfc_sources_meet(self):
        nfd = 'cell:caf' + 'e\u0301'                             # decomposed: e and a combining acute
        nfc = unicodedata.normalize('NFC', nfd)
        self.assertNotEqual(nfd, nfc)
        ls = [line(1, '2026-10-30T10:00:00-07:00', {'source': nfd, 'surface': 'pad'}),
              line(2, '2026-10-30T11:00:00-07:00', {'source': nfc, 'cadence': 60})]
        rows = sub.subscriptions(ls, P, now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['surface'], 'pad')

    def test_deterministic(self):
        ls = [line(i, '2026-10-30T1%d:00:00-07:00' % i, {'source': s, 'cadence': 60 * i})
              for i, s in ((1, FAR), (2, OTHER), (3, FAR))]
        a = json.dumps(sub.subscriptions(ls, P, fold(ag()), NOW), sort_keys=True)
        b = json.dumps(sub.subscriptions(list(reversed(ls)), P, fold(ag()), NOW), sort_keys=True)
        self.assertEqual(a, b)

    def test_words(self):
        self.assertEqual(sub.words(20), 'every 20 seconds')
        self.assertEqual(sub.words(300), 'every 5 minutes')
        self.assertEqual(sub.words(3600), 'hourly')
        self.assertEqual(sub.words(86400), 'daily')
        self.assertEqual(sub.words(7776000), 'each season')
        self.assertEqual(sub.words(None), 'at no set cadence')

    def test_render(self):
        ls = [line(1, NOW, {'source': FAR, 'signals': ['say', 'sight'], 'cadence': {'say': 20, 'sight': 86400}})]
        md = sub.render(sub.subscriptions(ls, P, now=NOW))
        self.assertIn('say every 20 seconds', md)
        self.assertIn('sight daily', md)
        self.assertIn('rises first', md)
        self.assertNotIn('"', md)                                     # quotes no one
        self.assertIn('Nothing is followed', sub.render(None))

    def test_subscribe_line(self):
        l = sub.subscribe_line(P, CELL, ['say'], 20, 'pad', ['pain'], '9' * 64, NOW, holon=HOME, salt='')
        self.assertEqual(l['type'], 'subscribe')
        self.assertEqual(l['actor'], P)
        self.assertEqual(l['for'], P)
        self.assertEqual(l['body']['cadence'], 20)
        self.assertEqual(l['links']['serves'], ['9' * 64])
        self.assertEqual(l['sig'], '')
        self.assertEqual(sub.subscribe_line(P, CELL, ['say'], 20, 'pad', ['pain'], '9' * 64, NOW, HOME, '')['id'],
                         l['id'])
        r = sub.subscriptions([l], P, now=NOW)[0]
        self.assertEqual((r['source'], r['cadence'], r['surface']), (CELL, {'say': 20}, 'pad'))
        self.assertIsNone(sub.subscribe_line(AG, CELL))
        self.assertIsNone(sub.subscribe_line(P, ''))
        self.assertNotIn('surface', sub.subscribe_line(P, CELL, surface='nowhere', salt='')['body'])


@unittest.skipUnless(shutil.which('ssh-keygen'), 'ssh-keygen is needed: the fixtures are signed')
class TestOverTheFold(unittest.TestCase):
    """The module over the real fold of the sample home: its signed Card counts, as written."""

    def test_fixture_card(self):
        import record
        home_dir = os.path.join(ENGINE, 'fixtures', 'hq')
        r = record.read_all(home_dir)
        f = record.fold(r['lines'], record.load_types(os.path.join(home_dir, 'types.json')), r['keepers'])
        keeper = r['holons'][0]['keeper']
        rows = sub.subscriptions(r['lines'], keeper, f)
        mine = [l for l in r['lines'] if l.get('type') == 'subscribe' and l.get('actor') == keeper]
        self.assertTrue(mine)
        got = row(rows, mine[0]['body']['source'])
        self.assertEqual(got['cadence'], dict(sorted(mine[0]['body']['cadence'].items())))
        self.assertEqual(sub.ignored(r['lines'], keeper, f), [])


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='lionsberg-subs-test-')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sub._main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli(self):
        p = os.path.join(self.d, 'lines.jsonl')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(json.dumps(line(1, NOW, {'source': FAR, 'cadence': 20})) + '\nnot json\n')
        code, out, _ = self.run_cli(p, '--person', P, '--json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]['source'], FAR)
        lp = os.path.join(self.d, 'last.json')
        with open(lp, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        code, out, _ = self.run_cli(p, '--person', P, '--due', lp, '--now', NOW, '--json')
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out))
        code, _, err = self.run_cli(p, '--person', P, '--due', lp)
        self.assertEqual(code, 2)

    def test_link_not_read(self):
        p = os.path.join(self.d, 'lines.jsonl')
        open(p, 'w').close()
        q = os.path.join(self.d, 'link.jsonl')
        os.symlink(p, q)
        code, _, err = self.run_cli(q, '--person', P)
        self.assertEqual(code, 2)
        self.assertIn('link', err)


if __name__ == '__main__':
    unittest.main()
