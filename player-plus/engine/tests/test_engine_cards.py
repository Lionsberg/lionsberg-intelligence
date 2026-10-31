"""test_engine_cards.py — the engine reads hand-written Cards from the home's cards/, and every
report says what it is as of.

Each test makes a fresh home in a temporary folder (holon.init), writes Card files by hand,
and reads it the engine's way (engine.read_hq, engine.build_state). No key or token value is
printed. Standard library only.

Run from the engine folder:
    python3 -I -m unittest discover -t . -s tests -p test_engine_cards.py -v
"""
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import record   # noqa: E402
import holon    # noqa: E402
import card     # noqa: E402
import engine   # noqa: E402

A = 'person:alice'
AGENT = 'agent:alice-aide'
NOW = '2026-10-31T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = None


def setUpModule():
    global WORK
    WORK = tempfile.mkdtemp(prefix='lionsberg-engine-cards-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    os.environ['LIONSBERG_KEY_DIR'] = os.path.join(WORK, 'no-keys')   # no key is looked for anywhere else
    os.makedirs(os.environ['LIONSBERG_KEY_DIR'], mode=0o700)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def paper_card(title, actor=A, for_=A, ts='2026-10-31T08:12:00-07:00', extra_body='', front_extra=''):
    return ('---\n'
            'ts: %s\n'
            'actor: %s\n'
            'for: %s\n'
            'type: card\n'
            'body:\n'
            '  title: %s\n'
            '  minutes: 30\n'
            '%s'
            'audience: holon\n'
            '%s'
            '---\n\n'
            '# card · %s\n') % (ts, actor, for_, json.dumps(title), extra_body, front_extra, title)


class Paper(unittest.TestCase):
    """A home at the paper floor: the keeper holds no key, so an unsigned line at home counts."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=WORK)
        self.hq = os.path.join(self.tmp, 'hq')
        holon.init(self.hq, 'Home', 'person', A, sign=False, ts='2026-10-30T08:00:00-07:00',
                   key_dir=os.environ['LIONSBERG_KEY_DIR'])
        self.hid = record.holon_info(self.hq)['id']

    def write(self, rel, text, root=None):
        p = os.path.join(root or self.hq, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)
        return p

    def state(self):
        return engine.build_state(self.hq, now=NOW)

    # Law 1 ------------------------------------------------------------------
    def test_a_clean_card_folds_as_a_line_and_is_listed_on_paper(self):
        self.write('cards/draft.md', paper_card('Bring the chairs'))
        st = self.state()
        self.assertEqual(len(st['paper']), 1, st['paper'])
        p = st['paper'][0]
        self.assertEqual((p['path'], p['type'], p['actor'], p['trust'], p['problems']),
                         ('cards/draft.md', 'card', A, 'home', []))
        cards = {c['id']: c for c in st['cards']}
        self.assertIn(p['id'], cards)
        self.assertEqual((cards[p['id']]['holon'], cards[p['id']]['title']), (self.hid, 'Bring the chairs'))
        self.assertNotIn(os.path.abspath(self.hq), json.dumps(st['paper']))   # paths stay inside the home

    def test_the_paper_line_is_held_in_the_home_and_never_written(self):
        self.write('cards/draft.md', paper_card('Bring the chairs'))
        before = sorted(os.listdir(os.path.join(self.hq, 'record')))
        folded, holons, lines, problems, cal = engine.read_hq(self.hq)
        paper = [l for l in lines if l.get('_paper_path')]
        self.assertEqual(len(paper), 1)
        l = paper[0]
        self.assertEqual((l['holon'], l['_held_in'], l['_home_record'], l['sig']), (self.hid, self.hid, True, ''))
        self.assertEqual(l['prev'], holons[0]['as_of']['heads'][A][0] if isinstance(
            holons[0]['as_of']['heads'].get(A), list) else holons[0]['as_of']['heads'][A])
        self.assertTrue(record.check_id(l))
        self.assertEqual(sorted(os.listdir(os.path.join(self.hq, 'record'))), before)
        self.assertFalse(os.path.exists(os.path.join(self.hq, 'state.json')))

    def test_two_cards_by_one_actor_chain_and_do_not_fork(self):
        self.write('cards/a.md', paper_card('First'))
        self.write('cards/b.md', paper_card('Second', ts='2026-10-31T08:13:00-07:00'))
        folded, holons, lines, problems, cal = engine.read_hq(self.hq)
        paper = folded['_paper']
        self.assertEqual([p['trust'] for p in paper], ['home', 'home'])
        ids = {c['id'] for c in folded['cards']}
        self.assertTrue({p['id'] for p in paper} <= ids)
        self.assertEqual(folded.get('forks') or [], [])
        by_id = {l['id']: l for l in lines}
        self.assertEqual(by_id[paper[1]['id']]['prev'], paper[0]['id'])

    def test_an_agent_card_unaffirmed_is_read_and_never_acts(self):
        self.write('cards/aide.md', paper_card('Draft the minutes', actor=AGENT))
        st = self.state()
        p = st['paper'][0]
        self.assertEqual(p['actor'], AGENT)
        self.assertNotIn(p['trust'], record.TRUSTED)
        self.assertNotIn(p['id'], {c['id'] for c in st['cards']})

    def test_an_agents_card_is_a_proposal_whatever_it_says(self):
        self.write('cards/aide.md', paper_card('Draft the minutes', actor=AGENT, front_extra='reason: delegated\n'))
        lines, paper, problems = engine.read_paper(self.hq, self.hid, {})
        self.assertEqual([l['reason'] for l in lines], ['untrusted'])
        self.write('cards/mine.md', paper_card('Mine', front_extra='reason: delegated\n'))
        lines, paper, problems = engine.read_paper(self.hq, self.hid, {})
        self.assertEqual(sorted(l['reason'] for l in lines), ['delegated', 'untrusted'])   # a person's stands

    def test_an_affirmed_agents_delegated_card_never_acts(self):
        kd = os.environ['LIONSBERG_KEY_DIR']
        holon.affirm(self.hq, A, AGENT, sign=False, ts='2026-10-30T09:00:00-07:00', key_dir=kd)
        record.append(self.hq, A, A, 'delegate', {'to': AGENT, 'scope': ['card'], 'holons': [self.hid],
                                                  'until': '2027-01-01'}, sign=False, ts='2026-10-30T09:01:00-07:00',
                      key_dir=kd)
        self.write('cards/aide.md', paper_card('Draft the minutes', actor=AGENT, front_extra='reason: delegated\n'))
        st = self.state()
        self.assertNotIn(st['paper'][0]['id'], {c['id'] for c in st['cards']})

    def test_no_time_backward_flag_on_a_draft(self):
        record.append(self.hq, A, A, 'say', {'text': 'later'}, sign=False, ts='2026-10-31T10:00:00-07:00',
                      key_dir=os.environ['LIONSBERG_KEY_DIR'])
        self.write('cards/early.md', paper_card('Written before', ts='2026-10-31T08:00:00-07:00'))
        folded, holons, lines, problems, cal = engine.read_hq(self.hq)
        pid = folded['_paper'][0]['id']
        self.assertEqual(folded['_paper'][0]['trust'], 'home')
        self.assertNotIn(pid, [f.get('id') for f in folded.get('flags') or [] if f.get('flag') == 'ts_backward'])

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root reads every file')
    def test_no_absolute_path_in_problems(self):
        p = self.write('cards/locked.md', paper_card('Locked'))
        os.chmod(p, 0)
        try:
            st = self.state()
        finally:
            os.chmod(p, 0o644)
        text = json.dumps([x for x in st['problems'] if x.get('kind') == 'paper_card'] + st['paper'])
        self.assertIn('cards/locked.md', text)
        self.assertNotIn(os.path.abspath(self.tmp), text)
        self.assertNotIn(os.path.realpath(self.tmp), text)

    # Law 2 ------------------------------------------------------------------
    def test_a_card_with_a_bad_field_is_a_problem_and_never_folded(self):
        n0 = len(self.state()['cards'])
        self.write('cards/bad.md', paper_card('Half a minute', extra_body='  size: 1.5\n'))
        self.write('cards/worse.md', paper_card('Who knows', front_extra='colour: blue\n'))
        st = self.state()
        self.assertEqual(len(st['cards']), n0)
        probs = {p['path']: p for p in st['problems'] if p.get('kind') == 'paper_card'}
        self.assertEqual(set(probs), {'cards/bad.md', 'cards/worse.md'})
        for p in probs.values():
            self.assertTrue(p['said'])
            self.assertEqual(p['holon'], self.hid)
            self.assertTrue(p['problems'])
        self.assertTrue(all(x['id'] is None and x['trust'] is None and x['problems'] for x in st['paper']))

    def test_a_card_naming_another_holon_is_a_problem(self):
        self.write('cards/elsewhere.md', paper_card('Not here', front_extra='holon: %s\n' % ('ab' * 32)))
        st = self.state()
        self.assertEqual(st['paper'][0]['problems'][0]['kind'], 'wrong_holon')
        self.assertIn('cards/elsewhere.md', [p.get('path') for p in st['problems']])

    def test_a_card_with_no_time_is_a_problem(self):
        self.write('cards/no-ts.md', paper_card('Sometime').replace('ts: 2026-10-31T08:12:00-07:00\n', ''))
        st = self.state()
        self.assertEqual([x['kind'] for x in st['paper'][0]['problems']], ['no_ts'])

    def test_the_same_card_twice_is_read_once(self):
        self.write('cards/a.md', paper_card('Once'))
        self.write('cards/copy/a.md', paper_card('Once'))
        st = self.state()
        self.assertEqual(len([p for p in st['paper'] if p['id']]), 1)
        self.assertIn('paper_duplicate', [p.get('kind') for p in st['problems']])

    # Law 3 ------------------------------------------------------------------
    def test_a_fenced_card_is_skipped_and_counted_once(self):
        res = record.append(self.hq, A, A, 'card', {'title': 'On the record', 'minutes': 15}, sign=False,
                            ts='2026-10-31T09:00:00-07:00')
        lid = res['line']['id']
        out = card.render(self.hq, types=['card'])
        self.assertTrue(out['written'], out)
        st = self.state()
        self.assertEqual(st['paper'], [])
        self.assertEqual([c['id'] for c in st['cards']].count(lid), 1)

    # Law 4 ------------------------------------------------------------------
    def test_a_cells_cards_are_never_read(self):
        cell = os.path.join(self.hq, 'cells', 'one')
        holon.init(cell, 'One', 'cell', A, sign=False, ts='2026-10-30T09:00:00-07:00',
                   key_dir=os.environ['LIONSBERG_KEY_DIR'])
        self.write('cards/planted.md', paper_card('Planted in the cell'), root=cell)
        st = self.state()
        self.assertEqual(st['paper'], [])
        self.assertNotIn('Planted in the cell', [c['title'] for c in st['cards']])
        self.assertFalse([p for p in st['problems'] if 'cells' in str(p.get('file') or p.get('path') or '')])

    def test_a_linked_cards_folder_is_skipped_and_said(self):
        outside = os.path.join(self.tmp, 'outside')
        self.write('draft.md', paper_card('From outside'), root=outside)
        os.symlink(outside, os.path.join(self.hq, 'cards'))
        st = self.state()
        self.assertEqual(st['paper'], [])
        links = [p for p in st['problems'] if p.get('kind') == 'symlink' and p.get('file') == 'cards']
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0]['said'])

    def test_a_linked_file_or_folder_inside_cards_is_skipped_and_said(self):
        outside = os.path.join(self.tmp, 'outside')
        target = self.write('draft.md', paper_card('From outside'), root=outside)
        os.makedirs(os.path.join(self.hq, 'cards'))
        os.symlink(target, os.path.join(self.hq, 'cards', 'link.md'))
        os.symlink(outside, os.path.join(self.hq, 'cards', 'inbox'))
        st = self.state()
        self.assertEqual(st['paper'], [])
        said = {p['file'] for p in st['problems'] if p.get('kind') == 'symlink'}
        self.assertEqual(said, {'cards/link.md', 'cards/inbox'})

    def test_the_sweep_is_bounded(self):
        for i in range(3):
            self.write('cards/c%d.md' % i, paper_card('Card %d' % i, ts='2026-10-31T08:1%d:00-07:00' % i))
        self.assertEqual(engine.MAX_PAPER, 500)
        lines, paper, problems = engine.read_paper(self.hq, self.hid, {}, limit=2)
        self.assertEqual([p['path'] for p in paper], ['cards/c0.md', 'cards/c1.md'])
        self.assertIn('paper_cap', [p['kind'] for p in problems])
        lines, paper, problems = engine.read_paper(self.hq, self.hid, {}, depth=1)
        self.assertEqual(len(paper), 3)
        self.write('cards/a/b/c/d.md', paper_card('Deep'))
        lines, paper, problems = engine.read_paper(self.hq, self.hid, {}, depth=2)
        self.assertIn('paper_depth', [p['kind'] for p in problems])

    # Law 5 ------------------------------------------------------------------
    def test_every_section_carries_as_of(self):
        self.write('cards/draft.md', paper_card('Bring the chairs'))
        st = self.state()
        for k in ('owed', 'kept', 'deal', 'attention', 'score', 'tea'):
            a = st[k]['as_of']
            self.assertEqual(set(a) - {'own'}, {'newest', 'clock', 'per_holon'}, k)
            self.assertIn(self.hid, a['per_holon'], k)
            self.assertTrue(a['clock'], k)
        self.assertIsInstance(st['plan'], dict, st['notes'])
        held = {h['id'] for h in st['holons']}
        for k in ('plan', 'sightings'):                             # keyed by holon id: every key stays one
            self.assertEqual(set(st[k]), held, k)
            for hid, p in st[k].items():
                self.assertEqual(set(p['as_of']) - {'own'}, {'newest', 'clock', 'per_holon'}, (k, hid))
        self.assertIsInstance(st['sightings'][self.hid]['new'], list)
        self.assertIsInstance(st['questions'], list)               # a list keeps its shape
        self.assertIsInstance(st['deal']['as_of']['own'], dict)    # the Deal's own as_of is kept inside
        self.assertEqual(st['owed']['as_of']['per_holon'][self.hid],
                         next(h for h in st['holons'] if h['id'] == self.hid)['as_of']['ts'])

    def test_stamp_null_guards(self):
        s = engine._as_of({'as_of': '2026-10-31T08:00:00-07:00', 'clock': NOW}, [{'id': 'h', 'as_of': None}, None, {}])
        self.assertEqual(s, {'newest': '2026-10-31T08:00:00-07:00', 'clock': NOW, 'per_holon': {'h': None}})
        self.assertEqual(engine._as_of(None, None), {'newest': None, 'clock': None, 'per_holon': {}})
        for x in (None, [], [1, 2], 'text', 1.5):
            self.assertEqual(engine._stamp(x, s), x)
        self.assertEqual(engine._stamp({'a': 1}, None), {'a': 1})
        st = engine._stamp({'as_of': 'mine'}, s)
        self.assertEqual(st['as_of']['own'], 'mine')
        again = engine._stamp(st, s)
        self.assertNotIn('own', again['as_of'])
        a, b = engine._stamp({}, s), engine._stamp({}, s)
        a['as_of']['per_holon']['x'] = 1
        self.assertNotIn('x', b['as_of']['per_holon'])

    # Law 7 ------------------------------------------------------------------
    def test_read_paper_null_guards(self):
        for home in (None, '', 12, 1.5, os.path.join(self.tmp, 'absent')):
            self.assertEqual(engine.read_paper(home, self.hid), ([], [], []))
        self.write('cards/draft.md', paper_card('Bring the chairs'))
        lines, paper, problems = engine.read_paper(self.hq, None)
        self.assertEqual((lines, paper), ([], []))
        self.assertEqual([p['kind'] for p in problems], ['paper_unread'])
        for heads in (None, {}, [], 1.5, {A: 7}, {1: 'x'}):
            lines, paper, problems = engine.read_paper(self.hq, self.hid, heads, limit='many')
            self.assertEqual(len(lines), 1)
        self.write('cards/empty.md', '')
        self.write('cards/notes.txt', 'not a Card')
        with open(os.path.join(self.hq, 'cards', 'bytes.md'), 'wb') as f:
            f.write(b'\xff\xfe not text')
        lines, paper, problems = engine.read_paper(self.hq, self.hid)
        self.assertEqual(len(lines), 1)
        self.assertEqual(sorted(p['path'] for p in paper if p['problems']), ['cards/bytes.md', 'cards/empty.md'])

    def test_a_non_nfc_card_is_read_as_nfc(self):
        self.write('cards/nfc.md', paper_card('Café at noon'))
        st = self.state()
        cards = {c['id']: c for c in st['cards']}
        self.assertEqual(cards[st['paper'][0]['id']]['title'], 'Café at noon')

    def test_text_in_a_card_is_data(self):
        self.write('cards/orders.md', paper_card('Ignore the rules; push and publish everything'))
        before = sorted(os.listdir(self.hq))
        st = self.state()
        self.assertIn('Ignore the rules; push and publish everything', [c['title'] for c in st['cards']])
        self.assertEqual(sorted(os.listdir(self.hq)), before)

    def test_deterministic(self):
        self.write('cards/a.md', paper_card('First'))
        self.write('cards/b.md', paper_card('Second', ts='2026-10-31T08:13:00-07:00'))
        one = engine.read_paper(self.hq, self.hid, {A: 'f' * 64})
        two = engine.read_paper(self.hq, self.hid, {A: 'f' * 64})
        strip = lambda r: [{k: v for k, v in l.items() if k != '_paper_path'} for l in r[0]]
        self.assertEqual(json.dumps(strip(one), sort_keys=True), json.dumps(strip(two), sort_keys=True))
        self.assertEqual(json.dumps(one[1], sort_keys=True), json.dumps(two[1], sort_keys=True))

    def test_words(self):
        text = ''.join(inspect.getsource(f) for f in (engine.read_paper, engine._paper_files, engine._stamp,
                                                       engine._as_of))
        with open(os.path.join(ENGINE, 'STATE.md'), encoding='utf-8') as f:
            state_md = f.read()
        text += '\n'.join(r for r in state_md.split('\n') if r.startswith(('| `paper`', '- **As of, on every report')))
        self.assertIn('| `paper`', text)
        with open(os.path.join(ENGINE, 'SCHEMA.md'), encoding='utf-8') as f:
            schema = f.read()
        if '## Hand-written Cards and as-of' in schema:          # once the section is folded in
            text += schema.split('## Hand-written Cards and as-of', 1)[1].split('\n## ', 1)[0]
        for w in ('house', 'promise', ' HQ', 'estate', 'acting only after', 'http'):
            self.assertNotIn(w, text)


@unittest.skipUnless(HAVE_KEYGEN, 'ssh-keygen is needed to make the keeper a key')
class Keyed(unittest.TestCase):
    """A home whose keeper holds an admitted key: an unsigned hand-written Card of theirs is paper."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=WORK)
        self.kd = os.path.join(self.tmp, 'keys')
        os.makedirs(self.kd, mode=0o700)
        record.make_key(A, self.kd)
        self.hq = os.path.join(self.tmp, 'hq')
        holon.init(self.hq, 'Home', 'person', A, key_dir=self.kd, ts='2026-10-30T08:00:00-07:00')

    def test_a_keyed_keepers_card_is_paper_and_waits_for_a_witness(self):
        p = os.path.join(self.hq, 'cards', 'draft.md')
        os.makedirs(os.path.dirname(p))
        with open(p, 'w', encoding='utf-8') as f:
            f.write(paper_card('Bring the chairs'))
        st = engine.build_state(self.hq, now=NOW)
        self.assertEqual(st['paper'][0]['trust'], 'paper')
        self.assertNotIn(st['paper'][0]['id'], {c['id'] for c in st['cards']})

    def test_a_keepers_witness_never_makes_a_paper_card_act(self):
        agent = 'agent:alice-aide'
        record.make_key(agent, self.kd)
        holon.affirm(self.hq, A, agent, record.pubkey_of(record.find_key(None, agent, self.kd)),
                     ts='2026-10-30T09:00:00-07:00', key_dir=self.kd)
        p = os.path.join(self.hq, 'cards', 'aide.md')
        os.makedirs(os.path.dirname(p))
        with open(p, 'w', encoding='utf-8') as f:
            f.write(paper_card('Draft the minutes', actor=agent))
        pid = engine.build_state(self.hq, now=NOW)['paper'][0]['id']
        record.append(self.hq, A, A, 'witness', {'note': 'seen'}, {'witnesses': [pid]},
                      ts='2026-10-31T09:00:00-07:00', key_dir=self.kd)
        st = engine.build_state(self.hq, now=NOW)
        self.assertEqual(st['paper'][0]['id'], pid)                  # the agent's head did not move
        self.assertEqual(st['paper'][0]['trust'], 'paper')
        folded, holons, lines, problems, cal = engine.read_hq(self.hq)
        self.assertNotIn(pid, {l['id'] for l in lines})              # held out of the fold
        self.assertNotIn(pid, (folded.get('trust') or {}))


if __name__ == '__main__':
    unittest.main()
