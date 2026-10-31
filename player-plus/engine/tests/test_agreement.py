"""test_agreement.py — the Agreement between holons: terms, permits, cadences, and its clauses.

Each law of agreement.py has a test that fails when it is broken. Most build folded items by hand,
in the shape record.py's fold returns; one class folds the signed sample fixtures, so the module is
proven against the real fold.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_agreement.py -v
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
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import agreement       # noqa: E402
import holon           # noqa: E402

HOME = 'a' * 64        # the proposing person's own holon
CELL = 'c' * 64        # the shared holon the Agreement is written in
OTHER = 'e' * 64       # a holon with no Agreement
P, S, X = 'person:player', 'person:steward', 'person:stranger'
NOW = '2026-10-24T12:00:00-07:00'


def ag(id_, state='agreed', **kw):
    it = {'id': id_, 'kind': 'agreement', 'holon': CELL, 'state': state, 'actor': P, 'for': P,
          'ts': '2026-10-20T10:00:00-07:00', 'with': CELL, 'crosses': ['request', 'commit'],
          'cadence': {'request': 60, 'commit': 300}, 'permits': {'write': True, 'bell': ['hazard']},
          'until': '2027-03-20', 'links': {}}
    if state == 'agreed':
        it.update(agreed_by=S, agreed_ts='2026-10-20T11:00:00-07:00', agreed_with=HOME)
    it.update(kw)
    return it


def admitted():
    return {HOME: {P: {'via': 'inception'}},
            CELL: {S: {'via': 'inception'}, P: {'via': 'join'}, 'agent:player-aide': {'via': 'affirm'}}}


def fold(*agreements_, commitments=(), adm=None):
    return {'agreements': list(agreements_), 'commitments': list(commitments),
            'admitted': admitted() if adm is None else adm, 'as_of': '2026-10-21T10:00:00-07:00'}


class TestPure(unittest.TestCase):
    """Law 1: no file is read in the functions, only the CLI's own argument."""

    def test_no_file_read(self):
        f = fold(ag('1' * 64))
        boom = mock.Mock(side_effect=AssertionError('a file was opened'))
        with mock.patch.object(builtins, 'open', boom), mock.patch.object(io, 'open', boom), \
                mock.patch.object(os, 'listdir', boom), mock.patch.object(os, 'scandir', boom):
            rows = agreement.agreements(f, now=NOW)
            agreement.between(f, HOME, CELL, NOW)
            agreement.why_none(f, HOME, OTHER, NOW)
            agreement.terms_for(f, HOME, CELL, NOW)
            agreement.may_cross(f, HOME, CELL, 'request', NOW)
            agreement.bell_permit(f, CELL, S, 'pain', NOW)
            agreement.render(rows)
        boom.assert_not_called()


class TestGrants(unittest.TestCase):
    """Law 2: a proposed, expired or retracted Agreement grants nothing."""

    def test_agreed_grants(self):
        t = agreement.terms_for(fold(ag('1' * 64)), HOME, CELL, NOW)
        self.assertEqual((t['basis'], t['agreement']), ('agreement', '1' * 64))
        self.assertEqual(t['cadence'], {'commit': 300, 'request': 60})
        self.assertEqual(t['permits'], {'write': True, 'bell': ['hazard']})

    def test_proposed_grants_nothing(self):
        t = agreement.terms_for(fold(ag('1' * 64, state='proposed')), HOME, CELL, NOW)
        self.assertEqual(t, {'cadence': {}, 'permits': {}, 'crosses': [], 'agreement': None, 'basis': 'none',
                             'why': t['why']})
        self.assertIn('none is agreed', t['why'])

    def test_expired_and_retracted_grant_nothing(self):
        for a in (ag('1' * 64, state='expired'), ag('1' * 64, state='retracted'),
                  ag('1' * 64, until='2026-10-01'),                         # past until, though the fold said agreed
                  ag('1' * 64, retracted_by='9' * 64)):
            t = agreement.terms_for(fold(a), HOME, CELL, NOW)
            self.assertEqual((t['basis'], t['cadence'], t['permits']), ('none', {}, {}), a)
        row = agreement.agreements(fold(ag('1' * 64, until='2026-10-01')), now=NOW)[0]
        self.assertEqual(row['state'], 'expired')

    def test_untrusted_or_vouched_grant_nothing(self):
        for a in (ag('1' * 64, reason='untrusted'), ag('1' * 64, vouched_by='8' * 64)):
            self.assertIsNone(agreement.between(fold(a), HOME, CELL, NOW))


class TestBetween(unittest.TestCase):
    """Law 3: between is symmetric and picks the newest agreed."""

    def test_symmetric(self):
        f = fold(ag('1' * 64))
        for a, b in ((HOME, CELL), (CELL, HOME), (HOME, S), (CELL, P)):
            r = agreement.between(f, a, b, NOW)
            self.assertIsNotNone(r, (a, b))
            self.assertEqual(r['id'], '1' * 64)
        self.assertIsNone(agreement.between(f, HOME, OTHER, NOW))
        self.assertIsNone(agreement.between(f, OTHER, HOME, NOW))
        self.assertIsNone(agreement.between(f, HOME, HOME, NOW))
        self.assertIsNone(agreement.between(f, S, HOME, NOW))            # the first side is a holon
        self.assertIsNone(agreement.between(f, P, S, NOW))               # two persons are not an Agreement's sides

    def test_newest_agreed(self):
        old = ag('2' * 64, agreed_ts='2026-10-19T09:00:00-07:00')
        new = ag('1' * 64, agreed_ts='2026-10-20T09:00:00-07:00')
        prop = ag('3' * 64, state='proposed')
        for order in ((old, new, prop), (prop, new, old), (new, prop, old)):
            self.assertEqual(agreement.between(fold(*order), CELL, HOME, NOW)['id'], '1' * 64)

    def test_why_none_says_a_sentence(self):
        self.assertIn('No Agreement', agreement.why_none(fold(ag('1' * 64)), HOME, OTHER, NOW)['why'])
        w = agreement.why_none(fold(ag('1' * 64, state='proposed')), HOME, CELL, NOW)
        self.assertEqual(w['seen'], [{'id': '1' * 64, 'state': 'proposed'}])
        self.assertTrue(w['why'].endswith('.'))
        self.assertIn('same', agreement.why_none(fold(), HOME, HOME, NOW)['why'])


class TestClauses(unittest.TestCase):
    """Law 4: a commitment serving the Agreement is its clause, with its status; another is not."""

    def test_clauses(self):
        serving = {'id': 'f' * 64, 'kind': 'commitment', 'holon': CELL, 'state': 'open', 'for': P,
                   'committee': S, 'card': 'd' * 64, 'by': '2026-10-01', 'links': {'serves': ['1' * 64]}}
        kept = dict(serving, id='b' * 64, state='kept', kept_ts='2026-09-30T10:00:00-07:00', witnessed_by=S)
        other = dict(serving, id='0' * 64, links={'serves': ['7' * 64]})
        row = agreement.agreements(fold(ag('1' * 64), commitments=[serving, kept, other]), now=NOW)[0]
        got = {c['id']: c['status'] for c in row['clauses']}
        self.assertEqual(got, {'f' * 64: 'broken', 'b' * 64: 'kept'})
        self.assertEqual(set(row['clauses'][0]), {'id', 'card', 'for', 'committee', 'by', 'state', 'status'})


class TestAndon(unittest.TestCase):
    """Law 5: a member's pain rings without a permit; a stranger's does not; an explicit permit across holons does."""

    def test_member_rings_by_joining(self):
        f = fold()                                   # no Agreement at all
        ok, why = agreement.bell_permit(f, CELL, P, 'pain', NOW, admitted=admitted())
        self.assertEqual((ok, why['basis']), (True, 'andon'))
        ok, why = agreement.bell_permit(f, CELL, 'agent:player-aide', 'fault', NOW, admitted=admitted()[CELL])
        self.assertEqual((ok, why['basis']), (True, 'andon'))
        ok, _ = agreement.bell_permit(f, CELL, P, 'hazard', NOW, admitted=admitted())
        self.assertFalse(ok)                         # only the Andon kinds ring by joining

    def test_stranger_does_not(self):
        ok, why = agreement.bell_permit(fold(ag('1' * 64)), CELL, X, 'pain', NOW, admitted=admitted())
        self.assertEqual((ok, why['basis']), (False, 'none'))

    def test_explicit_permit_across_holons(self):
        f = fold(ag('1' * 64, permits={'bell': ['pain', 'hazard']}))
        ok, why = agreement.bell_permit(f, HOME, CELL, 'pain', NOW, admitted=admitted())
        self.assertEqual((ok, why['basis'], why['agreement']), (True, 'agreement', '1' * 64))
        ok, why = agreement.bell_permit(fold(ag('1' * 64)), HOME, CELL, 'pain', NOW, admitted=admitted())
        self.assertEqual((ok, why['basis']), (False, 'agreement'))
        ok, _ = agreement.bell_permit(fold(ag('1' * 64, state='proposed', permits={'bell': ['pain']})),
                                      HOME, CELL, 'pain', NOW, admitted=admitted())
        self.assertFalse(ok)

    def test_the_folds_own_admitted_map_is_read_when_none_is_passed(self):
        ok, why = agreement.bell_permit(fold(), CELL, S, 'pain', NOW)
        self.assertEqual((ok, why['basis']), (True, 'andon'))


class TestMayCross(unittest.TestCase):
    """Law 6: with no Agreement, holon.PUBLISHABLE applies, said as default."""

    def test_default(self):
        ok, why = agreement.may_cross(fold(), HOME, OTHER, 'request', NOW)
        self.assertEqual((ok, why['basis']), ('request' in holon.PUBLISHABLE, 'default'))
        ok, why = agreement.may_cross(fold(), HOME, OTHER, 'subscribe', NOW)
        self.assertEqual((ok, why['basis']), (False, 'default'))
        ok, why = agreement.may_cross(fold(ag('1' * 64, crosses=[])), HOME, CELL, 'sight', NOW)
        self.assertEqual((ok, why['basis'], why['agreement']), (True, 'default', '1' * 64))

    def test_under_an_agreement(self):
        f = fold(ag('1' * 64, crosses=['request', 'subscribe']))
        self.assertEqual(agreement.may_cross(f, HOME, CELL, 'request', NOW)[0], True)
        ok, why = agreement.may_cross(f, HOME, CELL, 'sight', NOW)
        self.assertEqual((ok, why['basis']), (False, 'agreement'))
        ok, why = agreement.may_cross(f, HOME, CELL, 'subscribe', NOW)   # never across a membrane
        self.assertFalse(ok)
        self.assertIn('never', why['why'])


class TestDeterministicAndGuarded(unittest.TestCase):
    """Law 7: deterministic output; null-guards."""

    def test_deterministic(self):
        a, b = ag('1' * 64), ag('2' * 64, holon=HOME, agreed_ts='2026-10-19T09:00:00-07:00')
        one = json.dumps(agreement.agreements(fold(a, b), now=NOW), sort_keys=True)
        two = json.dumps(agreement.agreements(fold(b, a), now=NOW), sort_keys=True)
        self.assertEqual(one, two)
        self.assertEqual(agreement.render(agreement.agreements(fold(a, b), now=NOW)),
                         agreement.render(list(reversed(agreement.agreements(fold(a, b), now=NOW)))))
        self.assertEqual([r['holon'] for r in agreement.agreements(fold(a, b), now=NOW)], [HOME, CELL])

    def test_null_guards(self):
        for items in (None, {}, [], {'agreements': None}, {'agreements': [None, 3, 'x']}, 7):
            self.assertEqual(agreement.agreements(items, now=NOW), [])
            self.assertIsNone(agreement.between(items, HOME, CELL, NOW))
            self.assertEqual(agreement.terms_for(items, HOME, CELL, NOW)['basis'], 'none')
            self.assertEqual(agreement.may_cross(items, HOME, CELL, 'request', NOW)[1]['basis'], 'default')
            self.assertFalse(agreement.bell_permit(items, HOME, CELL, 'pain', NOW)[0])
        self.assertIn('No Agreement', agreement.render([]))
        self.assertFalse(agreement.may_cross(fold(), None, None, None, NOW)[0])
        self.assertFalse(agreement.bell_permit(fold(), None, P, 'pain', NOW)[0])

    def test_no_with(self):
        a = ag('1' * 64)
        del a['with']
        row = agreement.agreements(fold(a), now=NOW)[0]
        self.assertIsNone(row['with'])
        self.assertTrue(any('names no holon' in n for n in row['notes']))
        self.assertFalse(row['live'])
        self.assertIsNone(agreement.between(fold(a), HOME, S, NOW))      # one side unknown: it grants nothing

    def test_cadence_as_an_int_is_every_signal_and_said(self):
        row = agreement.agreements(fold(ag('1' * 64, cadence=300)), now=NOW)[0]
        self.assertEqual(row['cadence'], {'*': 300})
        self.assertTrue(any('every signal' in n for n in row['notes']))
        self.assertIn('every signal every 5 minutes', agreement.render([row]))

    def test_floats_and_odd_values(self):
        row = agreement.agreements(fold(ag('1' * 64, cadence={'request': 60.0, 'sight': 1.5, 'say': True},
                                           permits='yes', crosses='request')), now=NOW)[0]
        self.assertEqual(row['cadence'], {'request': 60})
        self.assertEqual(row['permits'], {'write': False, 'bell': []})
        self.assertEqual(row['crosses'], ['request'])
        self.assertEqual(len(row['notes']), 3)

    def test_non_nfc(self):
        decomposed = unicodedata.normalize('NFD', 'café-cell')
        a = ag('1' * 64)
        a['with'] = decomposed
        adm = dict(admitted(), **{unicodedata.normalize('NFC', 'café-cell'): {S: {'via': 'inception'}}})
        r = agreement.between(fold(a, adm=adm), unicodedata.normalize('NFC', 'café-cell'), HOME, NOW)
        self.assertIsNotNone(r)

    def test_cadence_words(self):
        words = {60: 'every minute', 300: 'every 5 minutes', 3600: 'hourly', 86400: 'daily',
                 7776000: 'each season', 45: 'every 45 s'}
        for s, w in words.items():
            self.assertEqual(agreement.cadence_words(s), w)


H2, D, V = 'b' * 64, 'd' * 64, '9' * 64


class TestSides(unittest.TestCase):
    """The sides are `with` and `agreed_with`; the keeper map is a fallback for one kept holon only."""

    def test_proposer_keeping_two_holons(self):
        adm = dict(admitted(), **{H2: {P: {'via': 'inception'}}})
        f = fold(ag('1' * 64), adm=adm)                                  # agreed with HOME, by the answer
        self.assertEqual(agreement.between(f, HOME, CELL, NOW)['id'], '1' * 64)
        self.assertIsNone(agreement.between(f, H2, CELL, NOW))
        self.assertEqual(agreement.terms_for(f, H2, CELL, NOW)['basis'], 'none')
        self.assertFalse(agreement.bell_permit(f, H2, CELL, 'pain', NOW)[0])
        self.assertIsNone(agreement.between(f, HOME, H2, NOW))
        old = ag('1' * 64)
        del old['agreed_with']                                           # an older fold: no agreed_with
        row = agreement.agreements(fold(old, adm=adm), now=NOW)[0]
        self.assertFalse(row['live'])
        self.assertTrue(any('several' in n for n in row['notes']))
        row = agreement.agreements(fold(old), now=NOW)[0]                # one kept holon: the fallback holds
        self.assertEqual((row['live'], row['agreed_with']), (True, HOME))

    def test_agreeing_person_keeping_another_holon(self):
        adm = dict(admitted(), **{D: {S: {'via': 'inception'}}})
        f = fold(ag('1' * 64), adm=adm)
        self.assertIsNone(agreement.between(f, HOME, D, NOW))
        self.assertIsNone(agreement.between(f, D, HOME, NOW))
        self.assertEqual(agreement.between(f, HOME, CELL, NOW)['id'], '1' * 64)

    def test_a_key_rotation_keeps_the_agreement(self):
        adm = admitted()
        adm[HOME] = {P: {'via': 'rotate'}}
        adm[CELL][S] = {'via': 'rotate'}
        self.assertEqual(agreement.between(fold(ag('1' * 64), adm=adm), HOME, CELL, NOW)['id'], '1' * 64)

    def test_the_venue_is_no_side(self):
        adm = {HOME: {P: {'via': 'inception'}}, D: {S: {'via': 'inception'}},
               V: {P: {'via': 'join'}, S: {'via': 'join'}}}
        f = fold(ag('1' * 64, holon=V, **{'with': D}), adm=adm)
        self.assertIsNone(agreement.between(f, V, HOME, NOW))
        self.assertIsNone(agreement.between(f, V, D, NOW))
        self.assertEqual(agreement.between(f, D, HOME, NOW)['id'], '1' * 64)


class TestAdmission(unittest.TestCase):
    """An Agreement stands only when the answerer is admitted in `with` and the proposer in `agreed_with`."""

    def test_an_answerer_not_admitted_grants_nothing(self):
        adm = dict(admitted(), **{D: {'person:keeper-of-d': {'via': 'inception'}}})
        f = fold(ag('1' * 64, **{'with': D}), adm=adm)                   # agreed by S, who is not admitted in D
        self.assertIsNone(agreement.between(f, HOME, D, NOW))
        self.assertEqual(agreement.terms_for(f, HOME, D, NOW)['basis'], 'none')
        self.assertFalse(agreement.bell_permit(f, D, HOME, 'pain', NOW)[0])
        self.assertTrue(any('not admitted' in n for n in agreement.agreements(f, now=NOW)[0]['notes']))

    def test_a_proposer_not_admitted_in_agreed_with_grants_nothing(self):
        adm = admitted()
        adm[HOME] = {'person:other': {'via': 'inception'}}
        self.assertIsNone(agreement.between(fold(ag('1' * 64), adm=adm), HOME, CELL, NOW))

    def test_without_the_map_it_is_said(self):
        f = fold(ag('1' * 64))
        del f['admitted']
        row = agreement.agreements(f, now=NOW)[0]
        self.assertTrue(row['live'])
        self.assertTrue(any('No admitted map' in n for n in row['notes']))


class TestLow(unittest.TestCase):
    def test_render_tolerates_a_hand_built_row(self):
        out = agreement.render([{'id': '1' * 64, 'state': 'agreed', 'cadence': 300},
                                {'id': '2' * 64, 'cadence': 'x', 'clauses': None, 'crosses': 'request', 'notes': 'n'}])
        self.assertIn('every signal every 5 minutes', out)
        self.assertIn('no cadence', out)

    def test_andon_kinds_as_a_set(self):
        ok, why = agreement.bell_permit(fold(), CELL, P, 'stop', NOW, andon_kinds={'stop'})
        self.assertEqual((ok, why['basis']), (True, 'andon'))

    def test_an_ended_clone_does_not_ring(self):
        adm = admitted()
        adm[CELL]['agent:player-aide.one'] = {'via': 'clone', 'state': 'done'}
        adm[CELL]['agent:player-aide.two'] = {'via': 'clone'}
        f = fold(adm=adm)
        self.assertFalse(agreement.bell_permit(f, CELL, 'agent:player-aide.one', 'pain', NOW)[0])
        self.assertTrue(agreement.bell_permit(f, CELL, 'agent:player-aide.two', 'pain', NOW)[0])


class TestWords(unittest.TestCase):
    """Law 8: the kit's words; quote no one."""

    def test_words(self):
        with open(os.path.join(ENGINE, 'agreement.py'), encoding='utf-8') as f:
            src = f.read()
        for bad in ('promise', 'house', 'HQ', 'estate'):
            self.assertIsNone(re.search(r'\b%s' % bad, src, re.I if bad != 'HQ' else 0), bad)
        for good in ('holon', 'person', 'agent', 'commitment'):
            self.assertIn(good, src)

    def test_render_quotes_no_one(self):
        out = agreement.render(agreement.agreements(fold(ag('1' * 64, terms='We hear each other daily.')), now=NOW))
        self.assertNotIn('We hear each other daily', out)
        self.assertNotIn('"', out)
        self.assertNotIn(P, out)


HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the fixtures are signed')
class TestOverTheFold(unittest.TestCase):
    """The module over the real fold of the signed sample fixtures."""

    @classmethod
    def setUpClass(cls):
        import record
        import make_fixtures
        cls.work = tempfile.mkdtemp(prefix='lionsberg-agreement-test-')
        cls.env = mock.patch.dict(os.environ, {'LIONSBERG_SIGCACHE_KEY': os.path.join(cls.work, 'sigcache.key')})
        cls.env.start()
        tpl = os.path.join(cls.work, 'template')
        os.makedirs(tpl)
        cls.ids = make_fixtures.build(tpl, os.path.join(cls.work, 'keys'))
        r = record.read_all(os.path.join(tpl, 'hq'))
        cls.f = record.fold(r['lines'], record.load_types(), r['keepers'], clock='2026-10-24T12:00:00-07:00')

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_the_fixture_agreement(self):
        H, C = self.ids['hq_holon'], self.ids['cell_holon']
        r = agreement.between(self.f, H, C)
        self.assertIsNotNone(r)
        self.assertEqual((r['id'], r['state'], r['agreed_by'], r['agreed_with']),
                         (self.ids['agreement'], 'agreed', 'person:steward', H))
        self.assertNotIn('No admitted map', ' '.join(r['notes']))
        self.assertEqual(agreement.between(self.f, C, H)['id'], r['id'])
        t = agreement.terms_for(self.f, H, C)
        self.assertEqual(t['cadence']['request'], 60)
        self.assertEqual(agreement.may_cross(self.f, H, C, 'say')[1]['basis'], 'agreement')
        self.assertFalse(agreement.may_cross(self.f, H, C, 'say')[0])         # the Agreement does not name say
        self.assertTrue(agreement.bell_permit(self.f, H, C, 'fault')[0])
        self.assertTrue(agreement.render(agreement.agreements(self.f)).startswith('# Agreements'))
        self.assertEqual(r['receipts'], [])



class TestFields(unittest.TestCase):
    """permits.fields travels in the terms, normalized, so terms_for, may_cross and faces read one set."""

    def test_fields_normalized_in_the_terms(self):
        f = fold(ag('1' * 64, permits={'write': True, 'bell': ['hazard'],
                                       'fields': {'sight': ['where', 'kind', 'kind'], 'commit': 'by', '': ['x']}}))
        t = agreement.terms_for(f, HOME, CELL, NOW)
        self.assertEqual(t['permits']['fields'], {'commit': None, 'sight': ['kind', 'where']})
        notes = ' '.join(agreement.agreements(f, now=NOW)[0]['notes'])
        self.assertIn('fields for commit are not a list of names', notes)
        self.assertIn('names no type', notes)

    def test_fields_not_a_map_and_absent(self):
        row = agreement.agreements(fold(ag('1' * 64, permits={'fields': 'kind'})), now=NOW)[0]
        self.assertIsNone(row['permits']['fields'])
        self.assertIn('not as a map of types', ' '.join(row['notes']))
        row = agreement.agreements(fold(ag('1' * 64)), now=NOW)[0]
        self.assertNotIn('fields', row['permits'])                     # carried only when named

if __name__ == '__main__':
    unittest.main()
