"""test_level.py — the level of a Card, computed from what it carries; the simplest Game that works.

Laws: a Card at the minimum plays (and the Deal deals it, its acts unchanged by the level); the level
is computed, never typed; the ladder follows types.json; `lifts` names only the next rung's fields;
the six lines of the simplest Game fold and compute; deterministic, honest-empty, null-guarded; the
kit's words. Run from the engine folder:

    python3 -I -m unittest discover -t . -s tests -p test_level.py -v
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
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ENGINE, os.path.join(ENGINE, 'fixtures')):
    if p not in sys.path:
        sys.path.insert(0, p)

import level as level_mod    # noqa: E402
import deal as deal_mod      # noqa: E402
import owed as owed_mod      # noqa: E402
import record                # noqa: E402

NOW = '2026-10-31T12:00:00-07:00'
A = 'holon-home'
P, K = 'person:player', 'person:keeper'
HOLONS = [{'id': A, 'name': 'Home', 'kind': 'person', 'keeper': P}]
SCHED = {'items': [{'id': 'a1', 'TF': 0, 'critical': True}], 'path': {'critical': ['a1'], 'system': []}}
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
# The six lines' fields, exactly: the minimum, and nothing beyond it (law 5).
SIX = {'join': {'who', 'pubkey'}, 'affirm': {'agent'}, 'card': {'title'}, 'commit': {'card', 'by'},
       'done': {'card'}, 'kept': {'commitment'}, 'answer': {'answer'}, 'condition': {'color', 'why'}}


def line(typ, body, i='l1', links=None, holon=A, actor=P, ts='2026-10-30T09:00:00-07:00'):
    return {'v': 1, 'id': i, 'ts': ts, 'actor': actor, 'for': actor, 'holon': holon, 'type': typ,
            'body': body, 'links': links or {}, 'audience': 'holon', 'reason': 'human', 'prev': '', 'sig': ''}


def card(i, title='Write the outline', minutes=30, **kw):
    c = {'id': i, 'kind': 'card', 'holon': A, 'title': title, 'minutes': minutes, 'holder': P, 'state': 'ready',
         'body_kind': 'activity', 'actor': P, 'for': P, 'ts': '2026-10-20T09:00:00-07:00', 'links': {}}
    c.update(kw)
    return c


def items():
    return {'cards': [card('a1'), card('a2', 'Draft', 60, links={'within': ['a1'], 'predecessor': ['a1']})],
            'commitments': [{'id': 'c-min', 'kind': 'commitment', 'holon': A, 'card': 'a1', 'by': '2026-10-28',
                             'state': 'open', 'for': P, 'actor': P, 'ts': '2026-10-19T09:00:00-07:00', 'links': {}}],
            'threads': [], 'sightings': []}


class TestMinimumPlays(unittest.TestCase):
    def test_a_commit_with_card_and_by_is_rung_one(self):
        lv = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07'}))
        self.assertEqual((lv['kind'], lv['name'], lv['rung'], lv['of']), ('commit', 'works', 1, 4))
        it = items()['commitments'][0]
        self.assertEqual(level_mod.level_of(it)['rung'], 1)

    def test_the_deal_deals_it_and_its_acts_are_unchanged(self):
        d = deal_mod.deal(items(), SCHED, P, 1000, now=NOW, holons=HOLONS)
        c = [x for x in d['cards'] if x['id'] == 'c-min']
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]['level']['name'], 'works')
        self.assertEqual(c[0]['level']['lifts'], ['its size in minutes', 'its conditions'])
        saved = deal_mod.level_mod
        try:
            deal_mod.level_mod = None                     # the level cannot be read: honest-empty
            e = deal_mod.deal(items(), SCHED, P, 1000, now=NOW, holons=HOLONS)
        finally:
            deal_mod.level_mod = saved
        for x in e['cards']:
            self.assertEqual(x['level'], {'name': None, 'lifts': [], 'why': deal_mod.LEVEL_NONE})

        def strip(dl):
            dl = copy.deepcopy(dl)
            for x in dl['cards'] + dl['beyond']['cards']:
                x.pop('level', None)
            dl.pop('generated_at', None)
            return dl
        self.assertEqual(json.dumps(strip(d), sort_keys=True), json.dumps(strip(e), sort_keys=True))

    def test_every_dealt_card_carries_a_level(self):
        d = deal_mod.deal(items(), SCHED, P, 1000, now=NOW, holons=HOLONS)
        self.assertTrue(d['cards'])
        for x in d['cards']:
            self.assertEqual(set(x['level']), {'name', 'lifts', 'why'})
            self.assertIsInstance(x['level']['lifts'], list)


class TestComputedNeverTyped(unittest.TestCase):
    def test_a_written_level_is_ignored_and_said(self):
        plain = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07'}))
        typed = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07', 'level': 'a clause'}))
        self.assertEqual((typed['rung'], typed['name']), (plain['rung'], plain['name']))
        self.assertEqual(typed['claimed'], 'a clause')
        self.assertIn('ignored', typed['why'])
        self.assertIsNone(plain['claimed'])
        it = dict(items()['commitments'][0], level=4)
        lv = level_mod.level_of(it)
        self.assertEqual((lv['claimed'], lv['rung'], lv['name']), (4, 1, 'works'))     # typed 4, computed 1
        lv = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07', 'level': 3}))
        self.assertEqual((lv['claimed'], lv['rung']), (3, 1))
        self.assertEqual(level_mod.levels({'commitments': [it]})['claimed'], ['c-min'])


class TestLadderFollowsRegistry(unittest.TestCase):
    def test_every_need_is_registered(self):
        types = record.load_types()['types']
        for k in level_mod.LADDER:
            fields = {f['name'] for f in types[k]['fields']}
            for r in level_mod.ladder(k):
                for need in r['needs']:
                    for a in need.split('|'):
                        if a.startswith('links.'):
                            self.assertIn(a[6:], record.LINK_KEYS, (k, a))
                        else:
                            self.assertIn(a, fields, (k, a))

    def test_what_is_dropped_is_exactly_what_is_said(self):
        for k in level_mod.LADDER:
            self.assertEqual(level_mod.unregistered(k), sorted(level_mod.UNREGISTERED.get(k, [])), k)
        self.assertEqual(tuple(level_mod.LINKS), tuple(record.LINK_KEYS))

    def test_a_rung_left_empty_is_skipped(self):
        names = [r['name'] for r in level_mod.ladder('offer')]
        self.assertEqual(names, ['asked', 'accountable', 'shaped'])
        reg = {'types': {'condition': {'fields': [{'name': 'color', 'kind': 'enum', 'values': ['green']},
                                                  {'name': 'why', 'kind': 'text'}]}}}
        self.assertEqual([r['name'] for r in level_mod.ladder('condition', reg)], ['said'])

    def test_minimum_and_ladder_are_data(self):
        self.assertEqual(level_mod.minimum('commit')['needs'], ['card', 'by'])
        self.assertEqual(level_mod.minimum('nothing'), {'needs': [], 'gives': None})
        self.assertEqual(level_mod.ladder('nothing'), [])
        json.dumps([level_mod.ladder(k) for k in level_mod.LADDER])


class TestLifts(unittest.TestCase):
    def test_only_the_next_rung(self):
        lv = level_mod.level_of(card('x', links={'within': ['u']}))
        self.assertEqual((lv['name'], lv['rung']), ('sized', 3))
        self.assertEqual([l['field'] for l in lv['lifts']], ['links.predecessor|links.successor'])
        self.assertEqual(lv['has'], ['named', 'placed', 'sized'])

    def test_a_present_field_of_the_next_rung_is_not_asked(self):
        lv = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07', 'size': 30}))
        self.assertEqual([l['field'] for l in lv['lifts']], ['conditions'])

    def test_empty_at_the_top(self):
        lv = level_mod.level_of(line('condition', {'color': 'green', 'why': 'well', 'until': '2026-11-07'}))
        self.assertEqual((lv['name'], lv['rung'], lv['of'], lv['lifts']), ('dated', 2, 2, []))

    def test_rung_zero_says_what_is_missing(self):
        lv = level_mod.level_of(line('commit', {'card': 'a1'}))
        self.assertEqual((lv['rung'], lv['name']), (0, 'below the minimum'))
        self.assertEqual([l['field'] for l in lv['lifts']], ['by'])
        self.assertIn('a by-when', lv['why'])

    def test_a_gap_keeps_the_level_at_the_last_unbroken_rung(self):
        lv = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07', 'buffer': 60, 'witness': K}))
        self.assertEqual((lv['rung'], lv['has']), (1, ['works', 'auditable']))

    def test_present_but_empty_does_not_count(self):
        for body in ({'card': 'a1', 'by': ''}, {'card': 'a1', 'by': '  '}, {'card': 'a1', 'by': 'soon'},
                     {'card': '', 'by': '2026-11-07'}, {'card': {'elided': 'abc'}, 'by': '2026-11-07'}):
            self.assertEqual(level_mod.level_of(line('commit', body))['rung'], 0, body)
        for size in (0, -5, 2.5, '30', True):
            lv = level_mod.level_of(line('commit', {'card': 'a1', 'by': '2026-11-07', 'size': size, 'conditions': 'x'}))
            self.assertEqual(lv['rung'], 1, size)
        lv = level_mod.level_of(line('sight', {'text': 'a hole', 'where': 'the lane', 'kind': 'not-a-kind'}))
        self.assertEqual(lv['rung'], 2)

    def test_the_shaped_rung_counts_only_for_many(self):
        to_one = level_mod.level_of(line('request', {'to': K, 'title': 'x', 'by': '2026-11-07', 'why': 'w', 'effort': 5}))
        self.assertEqual((to_one['rung'], to_one['of'], to_one['lifts']), (3, 3, []))
        to_holon = level_mod.level_of(line('request', {'to': 'holon-cell', 'title': 'x', 'by': '2026-11-07',
                                                       'why': 'w', 'effort': 5}))
        self.assertEqual((to_holon['rung'], to_holon['of']), (3, 4))
        self.assertEqual([l['field'] for l in to_holon['lifts']], ['shape', 'quorum'])
        say_many = level_mod.level_of(line('say', {'intent': 'ask', 'text': 'who can?', 'to': [P, K]}))
        self.assertEqual((say_many['rung'], say_many['of']), (1, 3))

    def test_an_offer_to_the_holon_plays(self):
        lv = level_mod.level_of(line('offer', {'title': 'Host the gathering'}))
        self.assertEqual((lv['rung'], lv['name']), (1, 'asked'))


class TestRootsAndChains(unittest.TestCase):
    def test_a_root_card_is_never_held_at_named(self):
        root = card('u', minutes=60, links={'successor': ['x']}, tea={'person:player': 60})
        lv = level_mod.level_of(root)                          # read alone: it lies within nothing
        self.assertEqual((lv['name'], lv['rung'], lv['of'], lv['lifts']), ('resourced', 4, 4, []))
        self.assertNotIn('links.within', [l['field'] for l in level_mod.level_of(card('v'))['lifts']])
        its = {'cards': [root, card('x', links={'within': ['u'], 'predecessor': ['u']})]}
        lv = level_mod.level_of(root, among=its)               # others lie within it: a root
        self.assertEqual((lv['name'], lv['rung'], lv['of']), ('resourced', 4, 4))
        child = level_mod.level_of(its['cards'][1], among=its)
        self.assertEqual((child['name'], child['rung'], child['of']), ('chained', 4, 5))

    def test_a_loose_card_beside_others_is_asked_where_it_lies(self):
        its = {'cards': [card('u'), card('x', links={'within': ['u']}), card('loose')]}
        lv = level_mod.level_of(its['cards'][2], among=its)
        self.assertEqual((lv['name'], lv['rung']), ('named', 1))
        self.assertEqual([l['field'] for l in lv['lifts']], ['links.within'])
        alone = {'cards': [card('only')]}
        self.assertEqual(level_mod.level_of(alone['cards'][0], among=alone)['name'], 'sized')

    def test_chained_reads_the_inverse_link(self):
        its = {'cards': [card('a', links={'within': ['u']}), card('b', links={'within': ['u'], 'predecessor': ['a']}),
                         card('u')]}
        self.assertEqual(level_mod.level_of(its['cards'][0])['name'], 'sized')        # alone: own links only
        self.assertEqual(level_mod.level_of(its['cards'][0], among=its)['name'], 'chained')
        idx = level_mod.index_of(its)
        self.assertEqual(level_mod.level_of(its['cards'][0], among=idx)['name'], 'chained')
        self.assertEqual(level_mod.levels(its)['by_kind']['card'], {'chained': 2, 'sized': 1})


class TestWhichLadder(unittest.TestCase):
    def test_items_read_by_their_kind(self):
        self.assertEqual(level_mod.level_of(card('x'))['kind'], 'card')
        ask = card('r', asked='request', to=P)
        self.assertEqual(level_mod.level_of(ask)['kind'], 'request')
        asked_later = card('r2', asked='request')            # a card asked of someone after it was born
        self.assertEqual(level_mod.level_of(asked_later)['kind'], 'card')
        s = {'id': 's', 'kind': 'sighting', 'text': 'a hole', 'body_kind': 'hazard', 'where': 'the lane'}
        self.assertEqual(level_mod.level_of(s)['name'], 'kinded')
        self.assertEqual(level_mod.level_of({'id': 'd', 'kind': 'decision', 'text': 'Meet weekly'})['kind'], 'propose')

    def test_kind_names_the_ladder(self):
        q = {'id': 'q', 'type': 'rfg', 'question': 'May we?', 'to': 'holon-cell', 'by': '2026-11-02'}
        self.assertEqual(level_mod.level_of(q, kind='rfg')['name'], 'dated')
        self.assertEqual(level_mod.level_of(q, kind='question')['kind'], 'rfg')


class TestHonestAndDeterministic(unittest.TestCase):
    def test_null_guards(self):
        for v in (None, {}, [], 1.5, 'a string', 3, True, {'kind': 7}, {'type': 'card', 'body': None}):
            lv = level_mod.level_of(v)
            self.assertIsNone(lv['rung'], v)
            self.assertTrue(lv['why'])
        for v in (None, {}, [], 1.5, 'a string'):
            r = level_mod.levels(v)
            self.assertEqual((r['by_kind'], r['below_minimum'], r['count']), ({}, [], 0))
            self.assertIn('No Cards', level_mod.render(r))
        for junk in (1.5, 5, 'ab', {'a': 1}):
            self.assertEqual(level_mod.levels({'cards': []}, lines=junk)['count'], 0)
        self.assertIn('No Cards', level_mod.render(None))
        md = level_mod.render({'by_kind': {'card': {'named': '2', 'sized': True, 'placed': 1.5, 'chained': 3},
                                           'sight': ['x'], 'nonsense': {'a': 1}}, 'below_minimum': ['a']})
        self.assertIn('- chained: 3', md)
        self.assertNotIn('named', md)
        self.assertEqual(level_mod.ladder(None), [])
        self.assertEqual(level_mod.ladder(3.5), [])

    def test_unknown_kind_is_said(self):
        lv = level_mod.level_of(line('tea', {'minutes': 5}))
        self.assertIsNone(lv['rung'])
        self.assertIn('no ladder', lv['why'])
        self.assertIsNone(level_mod.level_of(card('x'), kind='nonsense')['rung'])
        self.assertIsNone(level_mod.level_of(line('say', {'text': 'hello'}))['rung'])

    def test_non_nfc_kind(self):
        self.assertEqual(level_mod.level_of(card('x'), kind='CARD')['kind'], 'card')
        self.assertEqual(level_mod.level_of(line('sight', {'text': 'Café'}))['rung'], 1)

    def test_deterministic(self):
        its = items()
        its['sightings'] = [{'id': 's2', 'kind': 'sighting', 'holon': A, 'text': 'x', 'ts': '2026-10-29T09:00:00-07:00'},
                            {'id': 's1', 'kind': 'sighting', 'holon': A, 'text': '', 'ts': '2026-10-30T09:00:00-07:00'}]
        lines = [line('condition', {'color': 'red', 'why': 'short of hands'}, i='cond'),
                 line('rfg', {'question': 'q'}, i='rfg1')]
        a = level_mod.levels(its, lines)
        shuffled = copy.deepcopy(its)
        for v in shuffled.values():
            random.Random(7).shuffle(v)
        b = level_mod.levels(shuffled, list(reversed(lines)))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a['by_kind']['sight'], {'below the minimum': 1, 'seen': 1})
        self.assertEqual(a['by_kind']['card'], {'chained': 2})          # a1, a root, chained by a2's link
        self.assertEqual(a['by_kind']['condition'], {'said': 1})
        self.assertEqual(a['below_minimum'], ['rfg1', 's1'])
        self.assertEqual(a['as_of'], '2026-10-30T09:00:00-07:00')
        self.assertEqual(level_mod.levels(its, holon='elsewhere')['count'], 0)
        self.assertEqual(level_mod.levels(its, kind='sight')['by_kind'].keys(), {'sight'})
        md = level_mod.render(a)
        self.assertIn('## Sightings', md)
        self.assertIn('Cannot play yet', md)
        self.assertEqual(md, level_mod.render(b))


class TestTheSimplestGame(unittest.TestCase):
    def test_six_lines_in_plain_words(self):
        g = level_mod.the_simplest_game()
        self.assertEqual(len(g), 6)
        self.assertEqual([r['line']['type'] for r in g], ['join', 'card', 'commit', 'done', 'answer', 'condition'])
        self.assertEqual((g[0]['also']['type'], g[3]['or']['type']), ('affirm', 'kept'))
        for r in g:
            self.assertTrue(r['say'].endswith('.'))
            self.assertNotIn('person:', r['say'])
        types = record.load_types()['types']
        for r in g:
            for ln in [r['line']] + [r[k] for k in ('also', 'or') if k in r]:
                regs = {f['name'] for f in types[ln['type']]['fields']}
                self.assertTrue(set(ln['fields']) <= regs, ln)
                self.assertEqual(set(ln['fields']), SIX[ln['type']], ln['type'])   # the minimum, nothing beyond

    @unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed: the lines are signed')
    def test_the_six_fold_and_compute(self):
        import holon
        import make_fixtures
        import schedule
        work = tempfile.mkdtemp(prefix='lionsberg-level-test-')
        old = os.environ.get('LIONSBERG_SIGCACHE_KEY')
        os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(work, 'sigcache.key')
        try:
            kd = os.path.join(work, 'keys')
            pub = make_fixtures.make_keys(kd)
            PL, ST, AI = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
            cell = os.path.join(work, 'cell')
            holon.init(cell, 'simplest', 'cell', ST, ts='2026-10-31T09:00:00-07:00', salt='s0', key_dir=kd)
            g = {r['line']['type']: r for r in level_mod.the_simplest_game()}
            n, made = [0], {}

            def put(actor, spec, values, links=None):
                self.assertEqual(set(spec['fields']), SIX[spec['type']], 'the minimum and nothing beyond')
                self.assertEqual(set(values), SIX[spec['type']])
                n[0] += 1
                r = record.append(cell, actor, actor, spec['type'], values, links,
                                  ts='2026-10-31T09:%02d:00-07:00' % n[0], salt='s%d' % n[0], key_dir=kd)
                self.assertTrue(r['signed'])
                made[spec['type']] = r['line']['id']
                return r['line']

            put(ST, g['join']['line'], {'who': PL, 'pubkey': pub[PL]})
            put(PL, g['join']['also'], {'agent': AI})
            put(ST, g['card']['line'], {'title': 'Mend the gate'})
            put(PL, g['commit']['line'], {'card': made['card'], 'by': '2026-11-07'})
            clock = '2026-10-31T10:00:00-07:00'
            types = record.load_types()

            def fold():
                return record.fold(record.read(cell)['lines'], types, now=clock, clock=clock)
            f = fold()
            d = deal_mod.deal(f, schedule.run(f), ST, 60, now=clock)
            self.assertIn(made['card'], [x['id'] for x in d['cards']])      # the card is dealt to its holder
            self.assertEqual([x['level']['name'] for x in d['cards'] if x['id'] == made['card']], ['named'])
            late = '2026-11-08T10:00:00-07:00'           # past the by-when: owed computes the commitment
            f8 = record.fold(record.read(cell)['lines'], types, now=late, clock=late)
            o = owed_mod.owed(f8, actor=PL, now=late)
            self.assertEqual([(e['kind'], e['id'], e['status']) for e in o['entries']],
                             [('commitment', made['commit'], 'past')])
            put(PL, g['done']['line'], {'card': made['card']})
            put(ST, g['answer']['line'], {'answer': 'accept'}, {'answers': [made['commit']]})
            put(ST, g['condition']['line'], {'color': 'green', 'why': 'All is on track'})
            f = fold()
            for k in ('invalid', 'unverified', 'refused', 'paper', 'proposals', 'forked'):
                self.assertEqual(f.get(k) or [], [], k)
            cards = {c['id']: c for c in f['cards']}
            self.assertEqual(cards[made['card']]['state'], 'done')
            s = schedule.run(f)
            self.assertIn(made['commit'], json.dumps(s.get('commitments')))
            self.assertEqual(owed_mod.owed(f, actor=PL, now=clock)['entries'], [])   # not yet near its by-when
            for who in (PL, ST):
                d = deal_mod.deal(f, s, who, 60, now=clock)
                self.assertTrue(d['question'])
            commit = [c for c in f['commitments'] if c['id'] == made['commit']][0]
            self.assertEqual(level_mod.level_of(commit)['name'], 'works')
            self.assertEqual(level_mod.level_of(cards[made['card']])['name'], 'named')
            cond = [x for x in record.read(cell)['lines'] if x['type'] == 'condition'][0]
            self.assertEqual(level_mod.level_of(cond)['name'], 'said')
        finally:
            if old is None:
                os.environ.pop('LIONSBERG_SIGCACHE_KEY', None)
            else:
                os.environ['LIONSBERG_SIGCACHE_KEY'] = old
            shutil.rmtree(work, ignore_errors=True)


class TestWordsAndCommandLine(unittest.TestCase):
    def test_the_kits_words(self):
        with open(os.path.join(ENGINE, 'level.py'), encoding='utf-8') as fh:
            src = fh.read().lower()
        for w in ('promise', ' house', 'estate', ' hq'):
            self.assertNotIn(w, src, w)
        said = json.dumps(level_mod.the_simplest_game()) + json.dumps(level_mod.LADDER)
        self.assertNotIn('person:', said)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'level.py')] + list(args),
                              capture_output=True, text=True, timeout=60)

    def test_cli(self):
        r = self.run_cli('simplest', '--json')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(json.loads(r.stdout)), 6)
        r = self.run_cli('ladder', 'card')
        self.assertIn('**named**', r.stdout)
        self.assertNotEqual(self.run_cli('ladder', 'nothing').returncode, 0)
        work = tempfile.mkdtemp(prefix='lionsberg-level-cli-')
        try:
            p = os.path.join(work, 'items.json')
            with open(p, 'w', encoding='utf-8') as fh:
                json.dump(items(), fh)
            r = self.run_cli(p, '--json')
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)['by_kind']['commit'], {'works': 1})
            self.assertIn('# Levels of play', self.run_cli(p).stdout)
            ln = os.path.join(work, 'link.json')
            os.symlink(p, ln)
            self.assertNotEqual(self.run_cli(ln).returncode, 0)
            self.assertNotEqual(self.run_cli(os.path.join(work, 'absent.json')).returncode, 0)
        finally:
            shutil.rmtree(work, ignore_errors=True)


class TestNoPointerClaimed(unittest.TestCase):
    """The kit holds no pointer to the Path or its Gates yet; no surface may claim one."""
    CLAIM = re.compile(r'pointer|\bPath\b|\bGates?\b|first gate', re.IGNORECASE)

    def test_the_simplest_game_claims_no_pointer(self):
        said = json.dumps(level_mod.the_simplest_game(), sort_keys=True)
        self.assertIsNone(self.CLAIM.search(said.replace('mend the gate', '')))

    def test_no_ladder_claims_a_pointer(self):
        for k in sorted(level_mod.LADDER):
            said = json.dumps(level_mod.ladder(k), sort_keys=True)
            self.assertIsNone(self.CLAIM.search(said), k)

    def test_the_module_says_it_holds_none(self):
        self.assertIn('holds no pointer', level_mod.__doc__)
        self.assertNotIn('carries pointers', level_mod.__doc__)


if __name__ == '__main__':
    unittest.main()
