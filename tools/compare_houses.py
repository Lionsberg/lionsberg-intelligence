#!/usr/bin/env python3
"""compare_houses.py — is a house built by a Claude and a person the house the pages describe?

Builds the same house with build_house.py into a temporary home, from the same answers, and compares
the two, file for file. What a builder writes in its own words (the first memories, the prose under
the lineage block) is compared by presence, not by wording.

    python3 -I tools/compare_houses.py --kit . --home <the home that was built in> --hq-name mara-hq \
        --person Mara --handle mara --agent Tavi --house "the Okafor house" --persona chief-of-staff --date 2026-11-10

Exit 0 when the houses match. Standard library only.
"""
import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_house  # noqa: E402

IGNORE_DIRS = {'.git', '.desk', '__MACOSX'}
IGNORE_FILES = {'.DS_Store', 'player-plus-kit.zip'}
# written by the builder in its own words: present in both, wording free
OWN_WORDS = ('memory/',)
OWN_WORDS_FILES = {'LINEAGE.md'}


def tree(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in IGNORE_DIRS]
        for f in fn:
            if f in IGNORE_FILES:
                continue
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = p
    return out


def same(a, b, a_root, b_root):
    with open(a, 'rb') as f:
        x = f.read()
    with open(b, 'rb') as f:
        y = f.read()
    if x == y:
        return True
    # the two houses live at different paths, and each fills its own HQ path into its pages
    try:
        xs, ys = x.decode('utf-8'), y.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return xs.replace(a_root, '<HOME>').strip() == ys.replace(b_root, '<HOME>').strip()


def compare(built_home, ref_home, agent, hq_name):
    report, ok = [], True
    for label, rel in (('agent home', '%s (agent)' % agent), ('HQ', os.path.join('Documents', hq_name))):
        a_root, b_root = os.path.join(built_home, rel), os.path.join(ref_home, rel)
        if not os.path.isdir(a_root):
            report.append('%s: not found at %s' % (label, a_root))
            ok = False
            continue
        a, b = tree(a_root), tree(b_root)
        missing = sorted(set(b) - set(a))
        more = sorted(f for f in set(a) - set(b) if f.startswith(OWN_WORDS))     # a memory the builder chose to add
        extra = sorted(f for f in set(a) - set(b) if not f.startswith(OWN_WORDS))
        differs, own = [], []
        for f in sorted(set(a) & set(b)):
            if f.startswith(OWN_WORDS) or (label == 'agent home' and f in OWN_WORDS_FILES):
                own.append(f)
            elif not same(a[f], b[f], built_home, ref_home):
                differs.append(f)
        report.append('%s: %d files; %d the same; %d in the builder\'s own words; %d missing; %d extra; %d differ'
                      % (label, len(a), len(set(a) & set(b)) - len(differs) - len(own), len(own), len(missing), len(extra), len(differs)))
        for f in more:
            report.append('  a memory of the builder\'s own: %s' % f)
        for name, items in (('missing', missing), ('extra', extra), ('differs', differs)):
            for f in items[:40]:
                report.append('  %s: %s' % (name, f))
        if missing or extra or differs:
            ok = False
    return ok, report


def main(argv=None):
    ap = argparse.ArgumentParser(description='Compare a built house with the scripted build of the same answers.')
    for name in ('--kit', '--home', '--hq-name', '--person', '--handle', '--agent'):
        ap.add_argument(name, required=True)
    ap.add_argument('--house', default='my house')
    ap.add_argument('--persona', default='chief-of-staff')
    ap.add_argument('--date')
    a = ap.parse_args(argv)
    tmp = tempfile.mkdtemp()
    try:
        ref = os.path.join(tmp, 'home')
        os.makedirs(ref)
        build_house.build(a.kit, ref, a.hq_name, a.person, a.handle, a.agent, a.house, a.persona, a.date)
        ok, report = compare(os.path.abspath(a.home), ref, a.agent, a.hq_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\n'.join(report))
    print('MATCH' if ok else 'DIFFERENT')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
