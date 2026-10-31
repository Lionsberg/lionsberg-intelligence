"""test_acts.py — one card, everywhere: the acts a card offers are computed from the registry.

Laws: the committor is offered the committor's acts and the committee the committee's, never the other
side's state-changing acts, and a third person a say and nothing that changes state; an agent only what
a live delegation covers and never a person's own act; a person nothing home-only outside their home;
every key offered can produce has words in acts.json, and no label is a bare state; the Deal's `offers`
is acts.offered for the dealt actor, and the Deal is otherwise unchanged; plain.next_step reads the
act's label from acts.json; deterministic, honest-empty, null-guarded, the kit's words. Run from engine/:

    python3 -I -m unittest discover -t . -s tests -p test_acts.py -v
"""
import copy
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import acts            # noqa: E402
import deal as deal_mod  # noqa: E402
import plain           # noqa: E402
import record          # noqa: E402
from gamecore import normalize  # noqa: E402

NOW = '2026-10-31T12:00:00-07:00'
A, B = 'holon-home', 'holon-cell'
P, K, W, X, AG = 'person:player', 'person:keeper', 'person:witness', 'person:stranger', 'agent:aide'
HOLONS = [{'id': A, 'name': 'Home', 'kind': 'person', 'keeper': P},
          {'id': B, 'name': 'The Cell', 'kind': 'cell', 'keeper': K}]
REG = record.load_types()


def commitment(state='open', committee=P, witness=None, holon=B):
    c = {'id': 'cm1', 'kind': 'commitment', 'holon': holon, 'card': 'k1', 'by': '2026-11-06', 'state': state,
         'for': K, 'actor': K, 'ts': '2026-10-30T07:00:00-07:00'}
    if committee:
        c['committee'] = committee
    if witness:
        c['witness'] = witness
    return c


def card(i, holon=A, holder=P, state='ready', **kw):
    c = {'id': i, 'kind': 'card', 'holon': holon, 'title': 'Card ' + i, 'minutes': 10, 'holder': holder,
         'state': state, 'body_kind': 'activity', 'actor': holder or P, 'for': holder or P,
         'ts': '2026-10-20T09:00:00-07:00'}
    c.update(kw)
    return c


def folded(*items, delegations=()):
    return {'cards': [i for i in items if i['kind'] == 'card'],
            'commitments': [i for i in items if i['kind'] == 'commitment'],
            'threads': [i for i in items if i['kind'] == 'thread'],
            'decisions': [i for i in items if i['kind'] == 'decision'],
            'delegations': list(delegations), 'holons': HOLONS}


def keys(r):
    return {a['key'] for a in r['acts']}


def moves(r):
    return {a['key'] for a in r['acts'] if a['sets']}


def offered(item, actor, f=None, **kw):
    return acts.offered(item, actor, folded=f if f is not None else folded(item), now=NOW, **kw)


class TheTwoSidesOfACommitment(unittest.TestCase):
    """Law 1, over a commitment K made to P, read from the registry."""

    def expected_moves(self, state, who_ok):
        """The state-changing commitment acts the registry gives a reader whose `who` values are who_ok."""
        out = set()
        for typ, spec in REG['types'].items():
            if 'commitment' not in (spec.get('acts_on') or []) or typ in acts.NOT_A_CHOICE:
                continue
            for when, ts in acts._groups(spec, 'commitment'):
                for t in ts:
                    if t.get('from') and state not in t['from']:
                        continue
                    if t.get('who') not in who_ok:
                        continue
                    if acts._sets(t):
                        out.add(acts._key(typ, when))
                    break
        return out

    def test_the_committor_is_offered_the_committors_acts_only(self):
        for state in ('open', 'claimed'):
            r = offered(commitment(state), K)
            self.assertEqual(r['role'], 'committor')
            self.assertEqual(moves(r), self.expected_moves(state, {None, 'same_for', 'party'}), state)
            self.assertNotIn('act.witness', keys(r))                 # never Kept-as-witness
            self.assertNotIn('act.release', keys(r))
        self.assertIn('act.kept', keys(offered(commitment('open'), K)))
        kept = next(a for a in offered(commitment('open'), K)['acts'] if a['key'] == 'act.kept')
        self.assertEqual((kept['sets'], kept['primary']), ('claimed', True))

    def test_the_committee_is_offered_kept_release_and_decline_only(self):
        r_open, r_claimed = offered(commitment('open'), P), offered(commitment('claimed'), P)
        self.assertEqual(r_open['role'], 'committee')
        self.assertEqual(moves(r_open), self.expected_moves('open', {None, 'committee', 'named', 'party', 'other'}))
        self.assertEqual(moves(r_open), {'act.release', 'act.answer.decline'})
        self.assertEqual(moves(r_claimed), {'act.witness', 'act.release'})
        self.assertNotIn('act.kept', keys(r_open) | keys(r_claimed))
        w = next(a for a in r_claimed['acts'] if a['key'] == 'act.witness')
        self.assertEqual((w['sets'], w['label'], w['primary']), ('kept', 'Confirm it was kept', True))

    def test_the_two_sides_are_disjoint_on_what_changes_state(self):
        for state in ('open', 'claimed'):
            for c in (commitment(state), commitment(state, witness=W)):
                self.assertFalse(moves(offered(c, K)) & moves(offered(c, P)), state)

    def test_a_third_person_is_offered_a_say_and_nothing_that_changes_state(self):
        for state in ('open', 'claimed'):
            r = offered(commitment(state), X)
            self.assertEqual(r['role'], 'reader')
            self.assertEqual(moves(r), set(), state)
            self.assertIn('act.say', keys(r))
            self.assertIn('act.say.ask', keys(r))

    def test_a_named_witness_verifies_and_the_committee_still_may(self):
        r = offered(commitment('claimed', witness=W), W)
        self.assertEqual(r['role'], 'witness')
        self.assertEqual(moves(r), {'act.witness'})

    def test_the_fixture_commitment(self):
        src = os.path.join(ENGINE, 'fixtures', 'hq')
        if not os.path.isdir(src):
            self.skipTest('no fixtures/hq')
        r = record.read_all(src)
        f = record.fold(r['lines'], keepers=r['keepers'])
        f['holons'] = r['holons']
        cm = [c for c in f['commitments'] if c.get('state') == 'open']
        self.assertTrue(cm)
        mine = acts.offered(cm[0], cm[0]['for'], folded=f, now=NOW)
        self.assertIn('act.kept', keys(mine))
        self.assertNotIn('act.witness', keys(mine))
        other = acts.offered(cm[0], 'person:nobody-here', folded=f, now=NOW)
        self.assertEqual(moves(other), set())


class AgentsAndHomes(unittest.TestCase):
    """Law 2."""
    dlg = {'id': 'g1', 'kind': 'delegation', 'holon': A, 'state': 'live', 'to': AG, 'actor': P, 'for': P,
           'scope': ['claim', 'say'], 'holons': [A], 'until': '2026-12-31'}

    def test_an_agent_is_offered_only_what_a_live_delegation_covers(self):
        c = card('a1', holder=None)
        r = offered(c, AG, folded(c, delegations=[self.dlg]))
        self.assertEqual(keys(r), {'act.claim', 'act.say', 'act.say.ask'})
        self.assertEqual(r['for'], P)
        none = offered(c, AG, folded(c))                              # no delegation: nothing at all
        self.assertEqual(none['acts'], [])
        self.assertTrue(any(w['act'] == 'act.say' for w in none['why_not']))
        far = card('b1', holon=B, holder=None)
        self.assertEqual(offered(far, AG, folded(far, delegations=[self.dlg]))['acts'], [])   # not this holon
        gone = dict(self.dlg, until='2026-10-01')
        self.assertEqual(offered(c, AG, folded(c, delegations=[gone]))['acts'], [])          # ended

    def test_an_agent_is_never_offered_a_persons_own_act(self):
        allof = dict(self.dlg, scope=['*'], holons=['*'])
        for item in (commitment('open', holon=A), commitment('claimed', holon=A), card('r1', state='open', asked='request', to=P)):
            r = offered(item, AG, folded(item, delegations=[allof]))
            for a in r['acts']:
                spec = REG['types'][a['type']]
                self.assertFalse(spec.get('human_only'), a['key'])
                self.assertNotIn(a['type'], ('kept', 'witness', 'answer', 'commit', 'ratify', 'decide', 'settle'))

    def test_a_person_is_offered_nothing_home_only_outside_their_home(self):
        reg = copy.deepcopy(REG)
        reg['types']['pin'] = {'item': 'none', 'creates': 'never', 'acts_on': ['card'], 'home_only': True,
                               'human_only': True, 'target': ['links.anchored_to'], 'fields': [], 'transitions': []}
        home, cell = card('h1', holon=A), card('c1', holon=B)
        self.assertIn('act.pin', keys(offered(home, P, folded(home), registry=reg)))
        r = offered(cell, P, folded(cell), registry=reg)
        self.assertNotIn('act.pin', keys(r))
        self.assertIn({'act': 'act.pin', 'why': acts.WHY['home']}, r['why_not'])
        self.assertNotIn('act.pin', keys(offered(home, K, folded(home), registry=reg)))   # not K's home


class TheTableOfWords(unittest.TestCase):
    """Law 3."""

    def test_every_key_the_registry_can_produce_has_words(self):
        r = acts.check()
        self.assertTrue(r['ok'], r['missing'])
        for key, kind in acts.producible():
            w = acts.words(key, kind)
            self.assertTrue(w['label'] and w['meaning'], key)
            self.assertTrue(w['meaning'].startswith('You '), key)      # second person, its consequence

    def test_no_label_is_a_bare_state(self):
        states = {s for d in REG['items'].values() for s in d.get('states') or []}
        for key, kind in acts.producible():
            label = acts.words(key, kind)['label']
            self.assertNotIn(label.strip().lower().replace(' ', '_'), states, key)
        self.assertNotEqual(acts.words('act.kept')['label'].lower(), 'kept')
        kept_words = {k for k, _ in acts.producible() if 'kept' in acts.words(k, 'commitment')['label'].lower()}
        self.assertEqual(kept_words, {'act.witness'})                # "kept" is only the committee's word

    def test_settle_and_say_are_distinct(self):
        self.assertNotEqual(acts.words('act.settle')['label'], acts.words('act.say')['label'])
        self.assertNotEqual(acts.words('act.settle')['meaning'], acts.words('act.say')['meaning'])

    def test_every_offered_act_carries_its_words(self):
        for item, who in ((commitment('open'), K), (commitment('claimed'), P), (card('a1'), P)):
            for a in offered(item, who)['acts']:
                self.assertEqual((a['label'], a['meaning']),
                                 (acts.words(a['key'], item['kind'])['label'], acts.words(a['key'], item['kind'])['meaning']))

    def test_the_kits_words(self):
        with open(os.path.join(ENGINE, 'acts.json'), encoding='utf-8') as f:
            text = f.read().lower()
        for bad in ('promise', 'house', ' hq', 'estate'):
            self.assertNotIn(bad, text)
        self.assertFalse(re.search(r'person:[a-z]', text))
        self.assertNotIn('"', ''.join(v['meaning'] for v in acts.table().values()))   # quotes no one
        self.assertNotIn('nothing else changes', text)


class TheDealCarriesOffers(unittest.TestCase):
    """Law 4."""

    def items(self):
        return {'cards': [card('a1', links={'successor': ['a2']}), card('a2', links={'predecessor': ['a1']}),
                          card('r1', holon=B, holder=P, state='open', asked='request', to=P, actor=K, **{'for': K}),
                          card('free', holder=None, title='Sort the post', minutes=5)],     # in A, held by no one: the agent's
                'commitments': [dict(commitment('open', committee=K, holon=A), id='c-late', **{'for': P, 'actor': P},
                                     by='2026-10-28', card='a1'),
                                commitment('open')],
                'threads': [], 'sightings': [], 'delegations': [AgentsAndHomes.dlg]}

    def deal(self, items, actor=P):
        return deal_mod.deal(items, {}, actor, 1000, now=NOW, holons=HOLONS)

    def test_offers_is_acts_offered_for_the_dealt_actor(self):
        for actor in (P, AG):
            its = self.items()
            d = self.deal(its, actor)
            norm = normalize(its)
            ctx = deal_mod.acts_context(norm, HOLONS)
            by = {x['id']: x for xs in norm.values() for x in xs if isinstance(x, dict) and x.get('id')}
            self.assertTrue(d['cards'], actor)                        # the agent is dealt through its delegation
            if actor == AG:
                free = next(c for c in d['cards'] if c['id'] == 'free')
                self.assertEqual({a['key'] for a in free['offers']['acts']}, {'act.claim', 'act.say', 'act.say.ask'})
                self.assertEqual(free['offers']['for'], P)
            for c in d['cards'] + d['beyond']['cards']:
                want = acts.offered(by.get(c['id']), actor, folded=ctx, now=deal_mod.now_or(NOW), card=c)
                got = {k: v for k, v in c['offers'].items() if k != 'options'}
                self.assertEqual(got, want, c['id'])
                self.assertEqual([o['option'] for o in c['offers']['options']], c['options'])

    def test_the_deal_is_otherwise_unchanged(self):
        its = self.items()
        with_offers = self.deal(copy.deepcopy(its))
        saved = deal_mod.acts_mod
        try:
            deal_mod.acts_mod = None                                  # the snapshot: the Deal as it was before
            before = self.deal(copy.deepcopy(its))
        finally:
            deal_mod.acts_mod = saved
        strip = lambda d: json.dumps([{k: v for k, v in c.items() if k != 'offers'} for c in d['cards']], sort_keys=True)
        self.assertEqual(strip(with_offers), strip(before))
        for c in with_offers['cards']:
            self.assertEqual(c.get('acts'), next(x for x in before['cards'] if x['id'] == c['id']).get('acts'))
        self.assertTrue(all(c['offers']['said'] == deal_mod.OFFERS_NONE for c in before['cards']))

    def test_the_options_write_acts_not_words(self):
        d = self.deal(self.items())
        r1 = next(c for c in d['cards'] if c['id'] == 'r1')
        acc = r1['offers']['options'][0]
        self.assertEqual((acc['key'], acc['type'], acc['offered']), ('act.answer.accept', 'answer', True))
        self.assertEqual([o['recommended'] for o in r1['offers']['options']],
                         [o == r1['recommendation'] for o in r1['options']])
        self.assertEqual(acc['writes']['body']['answer'], 'accept')
        self.assertEqual(acc['writes']['links'], {'answers': ['r1']})          # the answer line, never a commit
        self.assertEqual([o['option'] for o in r1['offers']['options'] if o['needs_words']], ['Offer something else'])
        rec = next(o for o in r1['offers']['options'] if o['recommended'])
        self.assertEqual([a['key'] for a in r1['offers']['acts'] if a['primary']], [rec['key']])   # primary is the card's
        late = next(c for c in d['cards'] if c['id'] == 'c-late')
        rel = next(o for o in late['offers']['options'] if o['option'].startswith('Release'))
        self.assertEqual((rel['key'], rel['offered'], rel['writes']), ('act.release', False, None))  # the committee's, not P's
        self.assertTrue(rel['why'])

    def test_a_ratify_writes_ratify(self):
        dec = {'id': 'd1', 'kind': 'decision', 'holon': A, 'state': 'decided', 'for': P, 'actor': P,
               'decision': 'Meet weekly', 'decided_by': P, 'ts': '2026-10-30T07:00:00-07:00'}
        r = offered(dec, P, folded(dec))
        rat = next(a for a in r['acts'] if a['key'] == 'act.ratify')
        self.assertEqual(rat['writes']['type'], 'ratify')
        x = {'kind': 'ratify', 'section': 'decision', 'options': ['Confirm', 'Read the thread first', 'Return it with one change'],
             'recommendation': 'Confirm'}
        self.assertEqual(acts.options_for(x, r)[0]['writes']['type'], 'ratify')


class PlainReadsTheLabel(unittest.TestCase):
    """Law 5."""

    def test_the_how_reads_the_acts_label(self):
        d = deal_mod.deal(TheDealCarriesOffers().items(), {}, P, 1000, now=NOW, holons=HOLONS)
        a1 = next(c for c in d['cards'] if c['id'] == 'a1')
        self.assertEqual(a1['recommendation'], 'Take it now')
        s = plain.next_step(a1, P)
        w = acts.words('act.claim', 'card')
        self.assertEqual(s['act'], {'key': 'act.claim', 'label': w['label'], 'meaning': w['meaning']})
        self.assertEqual(s['how_act'], plain.HOW_ACT_VOICE % w['label'])
        self.assertEqual(s['how'], plain.HOW_VOICE)                  # one way to answer, while HOW_READS_ACT is off
        saved = plain.HOW_READS_ACT
        try:
            plain.HOW_READS_ACT = True
            s2 = plain.next_step(a1, P)
            self.assertEqual(s2['how'], plain.HOW_ACT_VOICE % w['label'])
            self.assertIn(s2['how'], s2['sentence'])
            self.assertIn(plain.HOW_ACT_PAPER % w['label'], plain.next_step(a1, P, paper=True)['sentence'])
        finally:
            plain.HOW_READS_ACT = saved

    def test_a_step_that_is_no_act_keeps_its_how(self):
        s = plain.next_step({'kind': 'body', 'options': ['Read it now'], 'recommendation': 'Read it now'})
        self.assertIsNone(s['act'])
        self.assertIsNone(s['how_act'])
        self.assertEqual(s['how'], plain.HOW_VOICE)


class DeterministicAndHonest(unittest.TestCase):
    """Law 6."""

    def test_deterministic(self):
        c = commitment('claimed', witness=W)
        f = folded(c)
        a = json.dumps(offered(c, P, f), sort_keys=True)
        f2 = copy.deepcopy(f)
        random.Random(7).shuffle(f2['holons'])
        self.assertEqual(a, json.dumps(offered(copy.deepcopy(c), P, f2), sort_keys=True))
        self.assertEqual(a, json.dumps(offered(c, P, f), sort_keys=True))

    def test_honest_empty_and_null_guards(self):
        for item in (None, {}, [], 1.5, 'x', {'id': ''}, {'id': 7}, {'id': 'z', 'kind': 'nothing-known'}):
            r = acts.offered(item, P)
            self.assertEqual(r['acts'], [], item)
            self.assertTrue(r['said'])
        for actor in (None, 1.5, '', 'steward', [], {}):
            self.assertEqual(acts.offered(card('a1'), actor)['acts'], [])
        for f in (None, {}, [], 1.5, 'x', {'cards': 'no'}, {'holons': [None, 3]}, {'admitted': 4}):
            r = acts.offered(card('a1'), P, folded=f)
            self.assertIn('act.say', keys(r))                        # a note is never refused a person
        nfc = unicodedata.normalize('NFD', 'person:café')
        self.assertIn('act.say', keys(acts.offered(card('a1'), nfc)))
        self.assertEqual(acts.render(None), acts.SAID_EMPTY + '\n')
        self.assertEqual(acts.render({}), acts.SAID_EMPTY + '\n')
        self.assertEqual(acts.roles(None, P), [])
        self.assertEqual(acts.options_for(None, None), [])
        self.assertEqual(acts.words(None), {'label': None, 'meaning': None, 'role_word': None})

    def test_roles_in_their_fixed_order(self):
        c = commitment('open', committee=P, witness=P)
        self.assertEqual(acts.roles(c, P, folded(c)), ['committee', 'witness'])
        self.assertEqual(acts.roles(c, K, folded(c)), ['committor', 'keeper'])
        self.assertEqual(acts.roles(c, X, folded(c)), ['reader'])
        f = dict(folded(c), admitted={B: {X: {'via': 'join'}}})
        self.assertEqual(acts.roles(c, X, f), ['member'])
        self.assertEqual(acts.roles(c, AG, f), ['reader'])                 # an agent answering for no one here

    def test_render_lists_the_primary_first_and_what_these_mean(self):
        md = acts.render(offered(commitment('claimed'), P))
        lines = md.splitlines()
        self.assertTrue(lines[2].startswith('- **Confirm it was kept** (the one I would choose)'), md)
        self.assertIn('### What these mean', md)
        after = md.split('### What these mean')[1]
        self.assertIn('**Confirm it was kept** — You confirm', after)
        self.assertNotRegex(md, r'person:|agent:|[0-9a-f]{12}')

    def test_the_say_is_always_offered_to_a_person(self):
        for item in (commitment('kept'), card('d', state='done'), card('x', state='retracted'),
                     {'id': 'th', 'kind': 'thread', 'holon': B, 'state': 'settled', 'for': K}):
            r = offered(item, X)
            self.assertIn('act.say', keys(r))
            ask = next(a for a in r['acts'] if a['key'] == 'act.say.ask')
            self.assertEqual(ask['writes'], {'type': 'say', 'body': {'text': None, 'intent': 'ask'},
                                             'links': {'anchored_to': [item['id']]}})


class StopsPersonsAndKinds(unittest.TestCase):
    """Repair: a stopped agent, an agent answering for two persons, a decision card, NO_OP, NOT_A_CHOICE."""
    dlg = dict(AgentsAndHomes.dlg, scope=['claim', 'say', 'done', 'hand', 'release'])

    def stop(self, **kw):
        s = {'id': 'st1', 'kind': 'stop', 'holon': A, 'state': 'live', 'actor': P, 'for': P, 'agents': [AG],
             'why': 'wait for me', 'ts': '2026-10-30T07:00:00-07:00'}
        s.update(kw)
        return s

    def test_a_stopped_agent_is_offered_nothing_that_acts(self):
        c = card('a1', holder=None)
        f = dict(folded(c, delegations=[self.dlg]), stops=[self.stop()])
        r = offered(c, AG, f)
        self.assertEqual(r['acts'], [])
        self.assertEqual(r['stopped']['stop'], 'st1')
        self.assertTrue(r['why_not'] and all(w['why'] == acts.WHY['stopped'] for w in r['why_not']))
        self.assertIn('act.say', [w['act'] for w in r['why_not']])
        x = {'kind': 'activity', 'section': 'ready', 'options': ['Take it now', 'Not this week: release it'],
             'recommendation': 'Take it now'}
        self.assertFalse(any(o['offered'] for o in acts.options_for(x, r)))
        lifted = dict(f, stops=[self.stop(state='retracted')])
        self.assertIn('act.claim', keys(offered(c, AG, lifted)))
        self.assertIn('act.claim', keys(offered(c, P, f)))             # a stop binds agents, never the person

    def test_the_deal_offers_a_stopped_agent_nothing(self):
        its = TheDealCarriesOffers().items()
        its['stops'] = [self.stop()]
        d = deal_mod.deal(its, {}, AG, 1000, now=NOW, holons=HOLONS)
        self.assertTrue(d['cards'])
        for c in d['cards']:
            self.assertEqual(c['offers']['acts'], [])
            self.assertTrue(c['offers']['stopped'])
            self.assertFalse(any(o['offered'] for o in c['offers']['options']))

    def test_an_agent_answers_only_for_the_person_whose_delegation_reaches_the_holon(self):
        zed = dict(self.dlg, id='g2', actor='person:zed', **{'for': 'person:zed'}, holons=[B])
        c = card('b1', holon=B, holder=None)
        r = offered(c, AG, folded(c, delegations=[self.dlg, zed]))
        self.assertEqual(r['for'], 'person:zed')                     # never the player, whose delegation is for A
        both = dict(zed, holons=[A])
        a = card('a1', holder=None)
        r2 = offered(a, AG, folded(a, delegations=[self.dlg, both]))
        self.assertEqual((r2['acts'], r2['for']), ([], None))      # two persons: nothing that acts
        self.assertTrue(all(w['why'] == acts.WHY['many'] for w in r2['why_not']))

    def test_an_agent_is_offered_nothing_on_a_decision_card(self):
        c = card('dc', holder=None, body_kind='decision')
        allof = dict(self.dlg, scope=['*'], holons=['*'])
        self.assertEqual(moves(offered(c, AG, folded(c, delegations=[allof]))), set())

    def test_no_move_to_the_state_it_holds(self):
        c = card('d1', state='done')
        r = offered(c, P)
        self.assertNotIn('act.done', keys(r))
        self.assertIn({'act': 'act.done', 'why': acts.WHY['no_op'] % 'done'}, r['why_not'])

    def test_receive_is_never_a_choice(self):
        for item in (card('a1'), commitment('open')):
            r = offered(item, P)
            self.assertNotIn('act.receive', keys(r))
            self.assertIn({'act': 'act.receive', 'why': acts.WHY['not_a_choice']}, r['why_not'])

    def test_settle_says_and_hand_on_a_decision(self):
        th = {'id': 'th', 'kind': 'thread', 'holon': A, 'state': 'open', 'for': K, 'actor': K}
        r = offered(th, P, folded(th))
        x = {'kind': 'thread', 'section': 'thread', 'recommendation': 'Reply now',
             'options': ['Reply now', 'Settle it as it stands', 'Hand it to someone else']}
        rows = acts.options_for(x, r)
        self.assertEqual([o['key'] for o in rows], ['act.say', 'act.settle', None])
        self.assertTrue(rows[0]['needs_words'])
        thank = acts.options_for({'kind': 'thread', 'options': ['Thank them: no reply needed']}, r)[0]
        self.assertEqual(thank['writes']['body']['text'], 'Thank them: no reply needed')   # its own words
        dec = {'kind': 'decision', 'section': 'decision', 'recommendation': 'Decide now',
               'options': ['Decide now', 'Gather one more input first', 'Hand it to someone better placed']}
        self.assertIsNone(acts.options_for(dec, offered(card('dc', body_kind='decision'), P))[2]['key'])

    def test_role_words(self):
        self.assertEqual(acts.words('act.release', 'commitment')['role_word'], 'committee')
        self.assertNotEqual(acts.words('act.revoke')['role_word'], 'committor')
        self.assertIn('own person', acts.words('act.stop.true')['role_word'])
        self.assertNotIn('tea', acts.words('act.witness', 'tea')['label'].lower().split())


class TheCommandLine(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'acts.py')] + list(args),
                              capture_output=True, text=True, timeout=60)

    def test_table_check_and_an_item(self):
        t = self.run_cli('table')
        self.assertEqual(t.returncode, 0, t.stderr)
        self.assertIn('act.kept', json.loads(t.stdout))
        c = self.run_cli('check')
        self.assertEqual(c.returncode, 0, c.stdout)
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, 'items.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(folded(commitment('claimed')), f)
            r = self.run_cli(p, 'cm1', P, '--json')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('act.witness', {a['key'] for a in json.loads(r.stdout)['acts']})
            md = self.run_cli(p, 'cm1', P)
            self.assertIn('### What these mean', md.stdout)
            link = os.path.join(tmp, 'link.json')
            os.symlink(p, link)
            self.assertEqual(self.run_cli(link, 'cm1', P).returncode, 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
