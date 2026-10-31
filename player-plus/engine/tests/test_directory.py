"""test_directory.py — the directory as plain files: people, agents, holons, memberships.

The sample fixtures (fixtures/make_fixtures.py) are built once per run in a temporary folder,
signed with throwaway keys kept for the run: two holons (a person's home and a cell it holds),
three actors (two persons and one agent). Each test generates or reads a directory from them.

Run from the engine folder: python3 -I -m unittest discover -t . -s tests -p test_directory.py -v
"""
import json
import os
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

import record          # noqa: E402
import holon           # noqa: E402
import directory       # noqa: E402
import make_fixtures   # noqa: E402

PLAYER, STEWARD, AIDE = make_fixtures.PLAYER, make_fixtures.STEWARD, make_fixtures.AIDE
CLOCK = '2026-10-24T12:00:00-07:00'
HAVE_KEYGEN = bool(shutil.which('ssh-keygen'))
WORK = KEYS = TEMPLATE = None
IDS = {}


def setUpModule():
    global WORK, KEYS, TEMPLATE, IDS
    if not HAVE_KEYGEN:
        raise unittest.SkipTest('ssh-keygen is needed: the fixtures are signed')
    WORK = tempfile.mkdtemp(prefix='lionsberg-directory-test-')
    os.environ['LIONSBERG_SIGCACHE_KEY'] = os.path.join(WORK, 'sigcache.key')
    KEYS = os.path.join(WORK, 'keys')
    TEMPLATE = os.path.join(WORK, 'template')
    os.makedirs(TEMPLATE)
    IDS = make_fixtures.build(TEMPLATE, KEYS)


def tearDownModule():
    if WORK:
        shutil.rmtree(WORK, ignore_errors=True)


def _tree(root):
    out = {}
    for d, _, files in os.walk(root):
        for n in files:
            p = os.path.join(d, n)
            with open(p, 'rb') as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.hq = os.path.join(TEMPLATE, 'hq')
        self.cell = os.path.join(self.hq, 'cells', make_fixtures.CELL)
        self.H, self.C = IDS['hq_holon'], IDS['cell_holon']
        self.tmp = tempfile.mkdtemp(prefix='dir-', dir=WORK)
        self.out = os.path.join(self.tmp, 'directory')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gen(self):
        return directory.generate(self.hq, self.out, now=CLOCK)

    def fold(self):
        return directory._fold_home(self.hq, CLOCK)[0]


class TestGenerated(Base):
    def test_two_holons_three_actors_and_the_memberships(self):
        r = self.gen()
        self.assertEqual((r['people'], r['agents'], r['holons'], r['memberships']), (2, 1, 2, 2))
        d = directory.read(self.out)
        self.assertEqual(d['problems'], [])
        self.assertEqual(sorted(d['people']), [PLAYER, STEWARD])
        self.assertEqual(sorted(d['agents']), [AIDE])
        self.assertEqual(sorted(d['holons']), sorted([self.H, self.C]))
        cell = {m['actor']: m for m in d['memberships'][self.C]['members']}
        self.assertEqual(sorted(cell), [PLAYER, STEWARD])
        lines = {l['id']: l for l in record.read_all(self.hq)['lines']}
        self.assertEqual(cell[PLAYER]['since'], lines[IDS['cell_join']]['ts'])
        self.assertEqual(cell[PLAYER]['by'], STEWARD)
        self.assertEqual(cell[STEWARD]['since'], lines[IDS['cell_inception']]['ts'])
        self.assertEqual(cell[STEWARD]['by'], STEWARD)
        # traffic comes from the person's own Subscription Card for that source, else it is not said
        self.assertEqual(cell[PLAYER]['traffic'], 'now')
        self.assertNotIn('traffic', cell[STEWARD])
        home = d['memberships'][self.H]['members']
        self.assertEqual([m['actor'] for m in home], [PLAYER])
        # the agent: its person, the key the record admitted, what its delegations let it do
        ag = d['agents'][AIDE]
        self.assertEqual(ag['person'], PLAYER)
        self.assertEqual(ag['pubkey'], self.fold()['admitted'][self.C][AIDE]['pubkey'])
        self.assertIn('card', ag['can'])
        self.assertIn('receive', ag['can'])
        self.assertEqual(d['people'][PLAYER]['agents'], [AIDE])
        self.assertEqual(d['people'][STEWARD]['agents'], [])
        self.assertEqual(d['people'][PLAYER]['xid'], self.fold()['admitted'][self.H][PLAYER]['xid'])
        # holons: kind, keeper, open by default, stewards
        self.assertEqual(d['holons'][self.C]['kind'], 'cell')
        self.assertEqual(d['holons'][self.C]['keeper'], STEWARD)
        self.assertIs(d['holons'][self.C]['open'], False)
        self.assertEqual(d['holons'][self.H]['open'], 'private')
        self.assertEqual(d['holons'][self.C]['stewards'], [STEWARD])
        # what the record does not say is named, never guessed
        self.assertIn('fallback', d['people'][PLAYER]['missing'])
        self.assertNotIn('fallback', d['people'][PLAYER])

    def test_idempotent(self):
        self.gen()
        before = _tree(self.out)
        r = self.gen()
        self.assertEqual(r['written'], [])
        self.assertEqual(_tree(self.out), before)
        a = directory.from_record(*directory._fold_home(self.hq, CLOCK)[:2])
        b = directory.from_record(*directory._fold_home(self.hq, CLOCK)[:2])
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_hand_kept_fields_survive_a_regeneration(self):
        self.gen()
        p = os.path.join(self.out, 'people', 'steward.md')
        with open(p, encoding='utf-8') as f:
            text = f.read()
        text = text.replace('name: steward\n', 'name: steward\nfallback: "mail:steward@commons.test"\n'
                                               'profile: "https://forge.test/steward"\n')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)
        h = os.path.join(self.out, 'holons', 'first-cell.md')
        with open(h, encoding='utf-8') as f:
            text = f.read()
        text = text.replace('open: false\n', 'open: true\nmeets: the first day of each week\n')
        with open(h, 'w', encoding='utf-8') as f:
            f.write(text)
        self.gen()
        d = directory.read(self.out)
        self.assertEqual(d['people'][STEWARD]['fallback'], 'mail:steward@commons.test')
        self.assertEqual(d['people'][STEWARD]['profile'], 'https://forge.test/steward')
        self.assertNotIn('fallback', d['people'][STEWARD].get('missing', []))
        self.assertIs(d['holons'][self.C]['open'], True)
        self.assertEqual(d['holons'][self.C]['meets'], 'the first day of each week')
        # and a hand-kept field the record also says is not taken from the file: the key stays the record's
        self.assertEqual(d['holons'][self.C]['keeper'], STEWARD)


class TestTheRecordWins(Base):
    def test_check_is_clean_on_a_generated_directory(self):
        self.gen()
        self.assertEqual(directory.check(directory.read(self.out), self.fold()), [])

    def test_check_names_a_member_not_admitted_and_a_key_that_differs(self):
        self.gen()
        d = directory.read(self.out)
        d['memberships'][self.C]['members'].append({'actor': 'person:stranger', 'since': CLOCK, 'by': STEWARD})
        other = record.pubkey_of(record.make_key('person:stranger', os.path.join(self.tmp, 'k')))
        d['agents'][AIDE]['pubkey'] = other
        probs = directory.check(d, self.fold())
        kinds = {(p['kind'], p['id']) for p in probs}
        self.assertIn(('not_admitted', 'person:stranger'), kinds)
        self.assertIn(('key_differs', AIDE), kinds)
        self.assertNotIn('PRIVATE', json.dumps(probs))
        # a member the record admits but the directory leaves out is said too
        d['memberships'][self.C]['members'] = [m for m in d['memberships'][self.C]['members'] if m['actor'] != PLAYER]
        self.assertIn(('not_listed', PLAYER), {(p['kind'], p['id']) for p in directory.check(d, self.fold())})

    def test_check_on_files_and_by_the_cli(self):
        self.gen()
        p = os.path.join(self.out, 'people', 'ghost.md')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('---\nid: "person:ghost"\nname: ghost\n---\n')
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'directory.py'), 'check', self.out, self.hq,
                            '--now', CLOCK], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn(('not_in_record', 'person:ghost'), {(x['kind'], x['id']) for x in out['problems']})


class TestResolve(Base):
    def setUp(self):
        super().setUp()
        self.gen()
        p = os.path.join(self.out, 'people', 'steward.md')
        with open(p, encoding='utf-8') as f:
            text = f.read()
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text.replace('name: steward\n', 'name: steward\nfallback: "mail:steward@commons.test"\n'))
        self.d = directory.read(self.out)

    def test_by_current_membership(self):
        r = directory.resolve(self.d, self.C)
        self.assertEqual(r['kind'], 'holon')
        self.assertEqual(r['ids'], [PLAYER, STEWARD])
        self.assertEqual(r['agents'], [AIDE])
        self.assertEqual(directory.resolve(self.d, 'first-cell'), r)           # by slug
        self.d['memberships'][self.C]['members'][0]['left'] = True              # player no longer a member
        r2 = directory.resolve(self.d, self.C)
        self.assertEqual(r2['ids'], [STEWARD])
        self.assertEqual(r2['agents'], [])

    def test_a_person_with_no_agent_resolves_to_their_fallback(self):
        r = directory.resolve(self.d, STEWARD)
        self.assertEqual((r['kind'], r['ids'], r['agents']), ('person', [STEWARD], []))
        self.assertEqual(r['fallbacks'], [{'person': STEWARD, 'fallback': 'mail:steward@commons.test'}])
        self.assertTrue(any('carried by an agent' in s for s in r['said']))
        r = directory.resolve(self.d, PLAYER)
        self.assertEqual((r['agents'], r['fallbacks']), ([AIDE], []))
        # no agent and no fallback: said, never guessed
        self.d['people'][STEWARD].pop('fallback')
        r = directory.resolve(self.d, STEWARD)
        self.assertEqual(r['fallbacks'], [])
        self.assertTrue(any('cannot reach them yet' in s for s in r['said']))

    def test_nesting_and_everyone_and_an_agent(self):
        child = 'c' * 64
        self.d['holons'][child] = {'id': child, 'slug': 'circle', 'name': 'circle', 'kind': 'cell', 'parent': self.C}
        self.d['memberships'][child] = {'holon': child, 'slug': 'circle',
                                        'members': [{'actor': 'person:circle-member'}]}
        self.assertNotIn('person:circle-member', directory.resolve(self.d, self.C)['ids'])
        r = directory.resolve(self.d, self.C, include_children=True)
        self.assertEqual(r['ids'], ['person:circle-member', PLAYER, STEWARD])
        # a cycle of parents ends
        self.d['holons'][self.C]['parent'] = child
        self.assertEqual(directory.resolve(self.d, child, include_children=True)['ids'],
                         ['person:circle-member', PLAYER, STEWARD])
        e = directory.resolve(self.d, 'everyone')
        self.assertEqual((e['kind'], e['ids']), ('everyone', [PLAYER, STEWARD]))
        a = directory.resolve(self.d, AIDE)
        self.assertEqual((a['kind'], a['agents']), ('agent', [AIDE]))
        u = directory.resolve(self.d, 'no-such-place')
        self.assertIsNone(u['kind'])
        self.assertEqual(u['ids'], [])

    def test_resolve_by_the_cli(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'directory.py'), 'resolve', self.out, 'first-cell'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['ids'], [PLAYER, STEWARD])


class TestNever(Base):
    def test_never_a_private_key(self):
        self.gen()
        blob = b''.join(_tree(self.out).values())
        self.assertNotIn(b'PRIVATE KEY', blob)
        for name in os.listdir(KEYS):
            if not name.endswith('.pub'):
                with open(os.path.join(KEYS, name), 'rb') as f:
                    body = [x for x in f.read().splitlines() if x and not x.startswith(b'-----')]
                for row in body:
                    self.assertNotIn(row, blob)
        # a private key put into a file by hand is never read as data
        p = os.path.join(self.out, 'people', 'player.md')
        with open(p, encoding='utf-8') as f:
            text = f.read()
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text.replace('name: player\n', 'name: player\nprofile: "-----BEGIN OPENSSH PRIVATE KEY-----"\n'))
        d = directory.read(self.out)
        self.assertNotIn(PLAYER, d['people'])
        self.assertIn('private_key', {x['kind'] for x in d['problems']})
        self.gen()
        with open(p, encoding='utf-8') as f:
            self.assertNotIn('PRIVATE KEY', f.read())

    def test_never_a_link_followed(self):
        target = os.path.join(self.tmp, 'elsewhere')
        os.makedirs(target)
        os.symlink(target, self.out)
        r = self.gen()
        self.assertEqual(r['written'], [])
        self.assertTrue(any('link' in s for s in r['said']))
        self.assertEqual(os.listdir(target), [])
        os.remove(self.out)
        # a file that is a link is not written through, and reading names it
        self.gen()
        outside = os.path.join(self.tmp, 'outside.md')
        with open(outside, 'w', encoding='utf-8') as f:
            f.write('untouched\n')
        p = os.path.join(self.out, 'people', 'player.md')
        os.remove(p)
        os.symlink(outside, p)
        r = self.gen()
        with open(outside, encoding='utf-8') as f:
            self.assertEqual(f.read(), 'untouched\n')
        self.assertTrue(any('people/player.md is a link' in s for s in r['said']))
        d = directory.read(self.out)
        self.assertIn(('link', 'people/player.md'), {(x['kind'], x.get('file')) for x in d['problems']})
        # a folder that is a link is never followed
        shutil.rmtree(os.path.join(self.out, 'agents'))
        os.symlink(target, os.path.join(self.out, 'agents'))
        r = self.gen()
        self.assertEqual(os.listdir(target), [])
        self.assertIn(('link', 'agents'), {(x['kind'], x.get('file')) for x in directory.read(self.out)['problems']})

    def test_never_written_into_a_cell_or_a_record(self):
        before = _tree(self.cell)
        for where in (os.path.join(self.cell, 'directory'), os.path.join(self.cell, 'record', 'directory'),
                      os.path.join(self.hq, 'record', 'directory'), os.path.join(self.hq, 'cells', 'directory')):
            r = directory.generate(self.hq, where, now=CLOCK)
            self.assertEqual(r['written'], [], where)
            self.assertFalse(os.path.exists(where), where)
        self.assertEqual(_tree(self.cell), before)


class TestLdif(Base):
    def test_well_formed_and_deterministic(self):
        self.gen()
        d = directory.read(self.out)
        text = directory.ldap_view(d)
        self.assertEqual(text, directory.ldap_view(directory.read(self.out)))
        rows = text.split('\n')
        self.assertEqual(rows[0], 'version: 1')
        entries = [e for e in text.split('\n\n')[1:] if e.strip()]
        self.assertEqual(len(entries), len(d['people']) + len(d['holons']))
        attr = re.compile(r'^[A-Za-z][A-Za-z0-9-]*(;[A-Za-z0-9-]+)*(: [\x01-\x09\x0b\x0c\x0e-\x7f]*|:: [A-Za-z0-9+/=]*)$')
        for e in entries:
            lines = [x for x in e.split('\n') if x and not x.startswith('#')]
            self.assertTrue(lines[0].startswith('dn:'), lines[0])
            for x in lines:
                self.assertRegex(x, attr)
                self.assertNotIn('\r', x)
            names = [x.split(':', 1)[0] for x in lines]
            self.assertIn('objectClass', names)
            self.assertIn('cn', names)
        groups = [e for e in entries if 'objectClass: groupOfNames' in e]
        self.assertEqual(len(groups), 2)
        cell = next(g for g in groups if 'cn: first-cell' in g)
        self.assertIn('member: uid=player,ou=people,o=commons', cell)
        self.assertIn('member: uid=steward,ou=people,o=commons', cell)
        self.assertIn('owner: uid=steward,ou=people,o=commons', cell)
        self.assertIn('dn: cn=first-cell,ou=holons,o=commons', cell)

    def test_a_name_beyond_ascii_is_base64_and_a_dn_is_escaped(self):
        dd = {'people': {'person:lion': {'id': 'person:lion', 'name': 'LIØNSBERG player'},
                         'person:a,b': {'id': 'person:a,b', 'name': ' leading'}},
              'holons': {}, 'memberships': {}}
        text = directory.ldap_view(dd, base='dc=example,dc=test')
        self.assertIn('cn:: ' + __import__('base64').b64encode('LIØNSBERG player'.encode()).decode(), text)
        self.assertIn('dn: uid=a\\,b,ou=people,dc=example,dc=test', text)
        self.assertIn('cn:: ', text.split('uid=a\\,b')[1])

    def test_ldap_by_the_cli(self):
        self.gen()
        r = subprocess.run([sys.executable, '-I', os.path.join(ENGINE, 'directory.py'), 'ldap', self.out],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith('version: 1\n'))


TS = '2026-10-22T10:%02d:00-07:00'


class Copied(Base):
    """A copy of the fixture home, so a test may write lines into it."""
    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.tmp, 'home')
        shutil.copytree(os.path.join(TEMPLATE, 'hq'), self.home, symlinks=True)
        self.hcell = os.path.join(self.home, 'cells', make_fixtures.CELL)
        self.k = os.path.join(self.tmp, 'k')
        self.n = 0

    def ts(self):
        self.n += 1
        return TS % self.n

    def newbie(self, **body):
        pub = record.pubkey_of(record.make_key('person:newbie', self.k))
        b = {'who': 'person:newbie', 'role': 'member', 'pubkey': pub}
        b.update(body)
        return b

    def generate(self):
        return directory.generate(self.home, self.out, now=CLOCK)


class TestRepairPlace(Copied):
    def test_a_path_whose_case_differs_is_refused_by_inode(self):
        before = _tree(self.hcell)
        for where in (os.path.join(self.home, 'CELLS', make_fixtures.CELL, 'directory'),
                      os.path.join(self.home, 'cells', make_fixtures.CELL.upper(), 'directory'),
                      os.path.join(self.home, 'Record', 'directory'),
                      os.path.join(self.home, 'RECORD')):
            r = directory.generate(self.home, where, now=CLOCK)
            self.assertEqual(r['written'], [], where)
        self.assertEqual(_tree(self.hcell), before)
        self.assertEqual(sorted(os.listdir(os.path.join(self.home, 'record'))),
                         sorted(os.listdir(os.path.join(TEMPLATE, 'hq', 'record'))))
        self.assertFalse(any(n in os.listdir(self.home) for n in ('CELLS', 'Record', 'RECORD')))

    def test_beside_a_home_only(self):
        for where in (self.home, os.path.join(self.home, '.carried', 'directory'), os.path.join(self.home, '.carried'),
                      os.path.join(self.home, '.talk', 'directory'), os.path.join(self.home, 'heartbeat'),
                      os.path.join(self.home, 'heartbeat', 'directory'), os.path.join(self.home, 'deep', 'directory')):
            before = sorted(os.listdir(self.home))
            r = directory.generate(self.home, where, now=CLOCK)
            self.assertEqual(r['written'], [], where)
            self.assertEqual(sorted(os.listdir(self.home)), before, where)
        r = directory.generate(self.home, os.path.join(self.home, 'directory'), now=CLOCK)   # a direct folder: allowed
        self.assertEqual(len(r['written']), 7)
        el = os.path.join(self.tmp, 'elsewhere')
        os.makedirs(el)
        os.symlink(el, os.path.join(self.tmp, 'lnk'))
        r = directory.generate(self.home, os.path.join(self.tmp, 'lnk', 'directory'), now=CLOCK)
        self.assertEqual(r['written'], [])
        self.assertEqual(os.listdir(el), [])


class TestRepairKeys(Copied):
    def test_a_planted_key_body_never_reaches_a_file(self):
        kfile = os.path.join(KEYS, record.key_name(STEWARD))
        with open(kfile, encoding='ascii') as f:
            rows = [x for x in f.read().splitlines() if x and not x.startswith('-----')]
        r = record.append(self.hcell, STEWARD, STEWARD, 'join',
                          self.newbie(name=rows[0], reach=['mail:n@commons.test', rows[1], 'not an address']),
                          ts=self.ts(), key_dir=KEYS)
        self.assertTrue(r['signed'])
        self.generate()
        blob = b''.join(_tree(self.out).values())
        for row in rows:
            if len(row) > directory.KEY_RUN:
                self.assertNotIn(row.encode(), blob)
        self.assertNotIn(b'b3BlbnNzaC1rZXktdjE', blob)
        self.assertNotIn(b'BEGIN', blob)
        d = directory.read(self.out)
        self.assertEqual(d['people']['person:newbie']['name'], 'newbie')
        self.assertEqual(d['people']['person:newbie']['reach'], ['mail:n@commons.test'])

    def test_the_guard_and_the_public_key_shape(self):
        pub = self.newbie()['pubkey']
        self.assertEqual(directory._pubkey(pub + ' newbie@commons.test'), pub)
        self.assertIsNone(directory._pubkey('ssh-ed25519 ' + 'A' * 68))
        self.assertIsNone(directory._pubkey('ssh-rsa ' + pub.split()[1]))
        self.assertFalse(directory._private('d' * 64))                       # an XID or an id stays
        self.assertTrue(directory._private('A' * 65))
        self.assertTrue(directory._private('x -----BEGIN y'))
        self.assertTrue(directory._private({'k': 'b3BlbnNzaC1rZXktdjE'}))


class TestRepairHandKept(Copied):
    def _steward(self):
        return os.path.join(self.out, 'people', 'steward.md')

    def test_a_file_the_reader_cannot_read_is_left_as_it_is(self):
        self.generate()
        p = self._steward()
        with open(p, encoding='utf-8') as f:
            text = f.read()
        cases = [text.replace('name: steward\n', 'name: steward\nprofile: https://forge.test/steward#me\n'
                                                 'fallback: mail: steward@commons.test\n'),
                 '﻿' + text.replace('name: steward\n', 'name: steward\nprofile: "https://forge.test/steward"\n'),
                 text + 'x' * (directory.MAX_FILE + 10)]
        for t in cases:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(t)
            with open(p, 'rb') as f:
                before = f.read()
            r = self.generate()
            with open(p, 'rb') as f:
                self.assertEqual(f.read(), before)
            self.assertTrue(any('people/steward.md' in s and 'never overwritten' in s for s in r['said']), r['said'])
            self.assertNotIn(p, r['written'])


class TestRepairRecord(Copied):
    def test_stewards_a_name_and_a_parent_from_the_record(self):
        url = 'ssh://forge.test/first-cell.git'
        record.append(self.home, PLAYER, PLAYER, 'join', {'cell': make_fixtures.CELL, 'url': url},
                      ts=self.ts(), key_dir=KEYS)
        record.append(self.hcell, PLAYER, PLAYER, 'join', self.newbie(name='New  Member'), ts=self.ts(), key_dir=KEYS)
        kids = {}
        for name, body in (('circle', {'cell': 'known-here-by-another-name', 'url': url}),
                           ('namesake', {'cell': make_fixtures.CELL, 'url': 'ssh://forge.test/another/first-cell.git'})):
            d = os.path.join(self.home, 'cells', name)
            kids[name] = holon.init(d, name, 'cell', STEWARD, ts=self.ts(), key_dir=KEYS)['holon']['id']
            record.append(d, STEWARD, STEWARD, 'join', body, ts=self.ts(), key_dir=KEYS)
        self.generate()
        d = directory.read(self.out)
        self.assertEqual(d['problems'], [])
        self.assertEqual(d['holons'][self.C]['stewards'], [PLAYER, STEWARD])     # the keeper, and who let a person in
        self.assertEqual(d['people']['person:newbie']['name'], 'New Member')
        self.assertEqual(d['holons'][kids['circle']]['parent'], self.C)          # by the url it was cloned from
        self.assertNotIn('parent', d['holons'][kids['namesake']])                # a name alone never nests
        self.assertIn('person:circle-x', directory.resolve(
            dict(d, memberships=dict(d['memberships'], **{kids['circle']: {
                'holon': kids['circle'], 'members': [{'actor': 'person:circle-x'}]}})), self.C, True)['ids'])

    def test_a_vouched_line_never_sets_since_or_by(self):
        h = 'e' * 64
        early = {'id': '1' * 64, 'ts': '2026-10-01T09:00:00-07:00', 'actor': 'person:other', 'holon': h,
                 'type': 'join', 'body': {'who': 'person:x'}, 'reason': 'human'}
        real = {'id': '2' * 64, 'ts': '2026-10-02T09:00:00-07:00', 'actor': 'person:k', 'holon': h,
                'type': 'join', 'body': {'who': 'person:x'}, 'reason': 'human'}
        folded = {'admitted': {h: {'person:k': {'via': 'inception', 'by': h},
                                   'person:x': {'via': 'join', 'by': early['id']}}},
                  'trust': {early['id']: 'vouched', real['id']: 'signed'}}
        m = {x['actor']: x for x in directory.from_record(folded, [early, real])['memberships'][h]['members']}
        self.assertEqual((m['person:x']['since'], m['person:x']['by']), (real['ts'], 'person:k'))
        folded['trust'] = {early['id']: 'vouched'}
        m = {x['actor']: x for x in directory.from_record(folded, [early])['memberships'][h]['members']}
        self.assertNotIn('since', m['person:x'])
        self.assertNotIn('by', m['person:x'])


class TestRepairLdifAndKeys(unittest.TestCase):
    def test_duplicate_dns_and_an_empty_group_are_not_emitted(self):
        a, b, c = 'a' * 64, 'b' * 64, 'c' * 64
        dd = {'people': {'person:Ann': {'name': 'Ann'}, 'person:ann': {'name': 'ann'}, 'person:bo': {'name': 'Bo'}},
              'holons': {a: {'slug': 'Circle'}, b: {'slug': 'circle'}, c: {'slug': 'empty'}},
              'memberships': {a: {'members': [{'actor': 'person:Ann'}]}, b: {'members': [{'actor': 'person:bo'}]},
                              c: {'members': [{'actor': 'person:gone', 'left': False}, {'actor': 'person:bo', 'left': True}]}}}
        text = directory.ldap_view(dd)
        dns = [x.split(': ', 1)[1].casefold() for x in text.split('\n') if x.startswith('dn: ')]
        self.assertEqual(len(dns), len(set(dns)))
        self.assertEqual(len(dns), 3)                                          # Ann, bo, one Circle
        self.assertNotIn('cn=empty', text.replace('# ', '#'))
        self.assertIn('# not emitted', text)
        self.assertNotIn('uid=ann,', text)

    def test_keys_that_are_not_strings_never_raise(self):
        mixed = {'people': {1: {}, 'person:a': 'str'}, 'holons': {1: {}, 'a' * 64: {}},
                 'memberships': {2: {}, 'b' * 64: {'members': 'xx'}}}
        directory.resolve(mixed, 'x')
        directory.resolve(mixed, 'b' * 64)
        self.assertTrue(directory.ldap_view(mixed).startswith('version: 1\n'))
        directory.check(mixed, {'admitted': {'b' * 64: {}, 3: {}}})


class TestGuards(unittest.TestCase):
    def test_null_inputs(self):
        tmp = tempfile.mkdtemp(dir=WORK)
        try:
            for home, out in ((None, None), ('', ''), (os.path.join(tmp, 'absent'), os.path.join(tmp, 'o')), ({}, [])):
                r = directory.generate(home, out)
                self.assertEqual(r['written'], [])
                self.assertTrue(r['said'])
            for x in (None, '', os.path.join(tmp, 'absent'), 3):
                r = directory.read(x)
                self.assertEqual((r['people'], r['agents'], r['holons'], r['memberships']), ({}, {}, {}, {}))
                self.assertTrue(r['problems'])
            for d in (None, {}, [], {'people': None, 'memberships': []}):
                for a in (None, '', 'everyone', 1.5, PLAYER):
                    r = directory.resolve(d, a)
                    self.assertEqual(r['ids'], [PLAYER] if a == PLAYER else [])
                self.assertEqual(directory.ldap_view(d), 'version: 1\n')
                self.assertEqual(directory.check(d, None), [])
                self.assertEqual(directory.check(d, {'admitted': None}), [])
            self.assertEqual(directory.from_record(None)['people'], {})
            self.assertEqual(directory.from_record({'admitted': {'x': None}}, lines=None, holons=None)['people'], {})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_float_a_bad_id_and_a_non_nfc_name(self):
        tmp = tempfile.mkdtemp(dir=WORK)
        try:
            os.makedirs(os.path.join(tmp, 'people'))
            os.makedirs(os.path.join(tmp, 'holons'))
            os.makedirs(os.path.join(tmp, 'memberships'))
            with open(os.path.join(tmp, 'people', 'a.md'), 'w', encoding='utf-8') as f:
                f.write('---\nid: "person:a"\nname: "Zoé"\nweight: 1.5\n---\n')
            with open(os.path.join(tmp, 'people', 'b.md'), 'w', encoding='utf-8') as f:
                f.write('---\nid: "holon-b"\n---\n')
            with open(os.path.join(tmp, 'holons', 'c.md'), 'w', encoding='utf-8') as f:
                f.write('---\nid: "person:c"\n---\n')
            with open(os.path.join(tmp, 'memberships', 'd.md'), 'w', encoding='utf-8') as f:
                f.write('---\nholon: %s\nmembers: [{"actor": "person:a"}, {"who": "x"}, 3]\n---\n' % ('d' * 64))
            with open(os.path.join(tmp, 'people', 'e.md'), 'w', encoding='utf-8') as f:
                f.write('no front matter\n')
            r = directory.read(tmp)
            self.assertEqual(r['people']['person:a']['name'], 'Zoé')        # made NFC
            self.assertNotIn('weight', r['people']['person:a'])                  # a fraction is a problem, never a guess
            kinds = {(x['kind'], x.get('file')) for x in r['problems']}
            self.assertIn(('bad_value', 'people/a.md'), kinds)
            self.assertIn(('bad_id', 'people/b.md'), kinds)
            self.assertIn(('bad_id', 'holons/c.md'), kinds)
            self.assertIn(('bad_member', 'memberships/d.md'), kinds)
            self.assertIn(('no_front_matter', 'people/e.md'), kinds)
            self.assertEqual([m['actor'] for m in r['memberships']['d' * 64]['members']], ['person:a'])
            self.assertEqual(json.dumps(r, sort_keys=True), json.dumps(directory.read(tmp), sort_keys=True))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_round_trip_of_a_record(self):
        rec = {'id': 'person:x', 'slug': 'x', 'name': 'yes', 'agents': [], 'reach': ['mail:x@commons.test'],
               'fallback': '2026-10-25', 'profile': ' padded'}
        front, probs = directory.from_markdown(directory.to_markdown('people', rec))
        self.assertEqual(probs, [])
        self.assertEqual(front, rec)

    def test_words_and_no_one_quoted(self):
        with open(os.path.join(ENGINE, 'directory.py'), encoding='utf-8') as f:
            src = f.read()
        for w in (r'\bhouses?\b', r'\bHQ\b', r'\bestates?\b', r'\bpromis'):
            self.assertIsNone(re.search(w, src, re.IGNORECASE if w != r'\bHQ\b' else 0), w)
        self.assertNotIn('Sir', src)


if __name__ == '__main__':
    unittest.main()
