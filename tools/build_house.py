#!/usr/bin/env python3
"""build_house.py — the scripted build of a Player+ 4.1 house.

A house is built by a Claude reading pkai-starter-kit/BUILD.md and player-plus-kit/BUILD.md with a
person. This script does the same file work with no conversation, so that the tests, and anyone who
wants to check a build made by hand, have a house to compare against. It installs nothing, runs no
git, makes no environment in the app, and touches only the two folders it is given.

    python3 -I tools/build_house.py --kit . --home /tmp/home --hq-name ada-hq \
        --person Ada --handle ada --agent River --house "the Ada house" --persona chief-of-staff

Standard library only.
"""
import argparse
import datetime
import os
import re
import shutil
import sys

PKAI = 'pkai-starter-kit'
PLUS = 'player-plus-kit'
BEGIN = '<!-- Player+ begins'
END = '<!-- Player+ ends -->'
ANCHOR = '## Things you always do'
# what pkai-starter-kit/BUILD.md step 5.5 installs in every house
PKAI_INSTALLED = ['pull-from-benchmark', 'save-a-memory', 'wrap-up-this-session', 'start-a-project', 'venue-card',
                  'widen-a-boundary', 'heads-up', 'foreground-background', 'find-it-again', 'review-and-prune',
                  'import-chatgpt-history', 'fair-copy-a-transcript', 'phone-path', 'send-for-review']


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def persona_as_charter(kit, persona, hq_path):
    """The starter kit's persona, personalized as its BUILD.md step 5.3 says: comment stripped, path filled."""
    text = read(os.path.join(kit, PKAI, 'personas', persona + '.md'))
    text = re.sub(r'\A<!-- persona:.*?-->\n*', '', text, count=1, flags=re.S)
    return text.replace('{{HQ_PATH}}', hq_path)


def block(kit, hq_path):
    text = read(os.path.join(kit, PLUS, 'PLAYER-PLUS-BLOCK.md')).strip('\n')
    if not (text.startswith(BEGIN) and text.endswith(END)):
        raise SystemExit('PLAYER-PLUS-BLOCK.md does not begin and end with its markers')
    return text.replace('{{HQ_PATH}}', hq_path)


def with_block(charter, block_text):
    """The charter with the Player+ block immediately above '## Things you always do'."""
    if BEGIN in charter:
        raise SystemExit('the charter already holds a Player+ block')
    at = charter.find('\n' + ANCHOR + '\n')
    if at < 0:
        raise SystemExit('the persona has no line "%s"' % ANCHOR)
    return charter[:at].rstrip('\n') + '\n\n' + block_text + '\n\n' + charter[at + 1:]


def memory(path, name, kind, description, body):
    write(path, '---\nname: %s\ntype: %s\ndescription: %s\n---\n\n%s\n' % (name, kind, description, body))


def build(kit, home, hq_name, person, handle, agent, house, persona, date=None, waiver_words='Yes, I agree.'):
    kit = os.path.abspath(kit)
    date = date or datetime.date.today().isoformat()
    hq = os.path.join(home, 'Documents', hq_name)
    agent_home = os.path.join(home, '%s (agent)' % agent)
    for must_not in (agent_home, os.path.join(home, 'My Agents')):
        if os.path.exists(must_not):
            raise SystemExit('a house is already here: %s' % must_not)
    os.makedirs(hq, exist_ok=True)
    # the two kits, as the unzip leaves them in the HQ
    for k in (PKAI, PLUS):
        shutil.copytree(os.path.join(kit, k), os.path.join(hq, k), symlinks=False)
    pk, pl = os.path.join(hq, PKAI), os.path.join(hq, PLUS)
    pkai_version = read(os.path.join(pk, 'VERSION.md')).split()[-1].lstrip('v')
    plus_version = read(os.path.join(pl, 'VERSION.md')).split()[-1].lstrip('v')

    # --- the starter kit's step 5 ---
    shutil.copytree(os.path.join(pk, 'template', 'agent-home'), agent_home)
    os.rename(os.path.join(agent_home, 'dot-claude'), os.path.join(agent_home, '.claude'))
    os.remove(os.path.join(agent_home, '.claude', 'settings.powershell.json'))
    for s in ('now', 'now-hook', 'desk'):
        os.chmod(os.path.join(agent_home, 'scripts', s), 0o755)
    charter = persona_as_charter(kit, persona, hq)
    lineage = read(os.path.join(pk, 'LINEAGE.md'))
    lineage = re.sub(r'^name: .*$', 'name: %s' % agent, lineage, count=1, flags=re.M)
    lineage = re.sub(r'^version: .*$', 'version: 1.0.0', lineage, count=1, flags=re.M)
    lineage = re.sub(r'^grows_from: .*$', 'grows_from: pkai-starter-kit %s' % pkai_version, lineage, count=1, flags=re.M)
    kit_entry = '  - pkai-starter-kit v%s · %s · Peter Kaminski, with Saga · read' % (pkai_version, date)
    lineage = re.sub(r'^(lineage:.*)$', lambda m: m.group(1) + '\n' + kit_entry, lineage, count=1, flags=re.M)
    skills = os.path.join(agent_home, '.claude', 'skills')
    for s in PKAI_INSTALLED:
        shutil.copytree(os.path.join(pk, 'skills', s), os.path.join(skills, s))
    mem = os.path.join(agent_home, 'memory')
    memory(os.path.join(mem, 'agent_name.md'), 'agent-name', 'fact', "My name, chosen by my person.",
           'My name is %s. %s chose it on %s.\n\n**How I know:** heard, at setup, %s.' % (agent, person, date, date))
    memory(os.path.join(mem, 'user_name.md'), 'user-name', 'user', "My person's name.",
           'My person is %s.\n\n**How I know:** heard, at setup, %s.' % (person, date))
    memory(os.path.join(mem, 'waiver_agreed.md'), 'waiver-agreed', 'fact', 'My person agreed to both waivers at setup.',
           '%s agreed to the starter kit\'s `WAIVER.md` and to the Player+ kit\'s `WAIVER.md` on %s, in these words: "%s"\n\n'
           '**How I know:** heard, at setup, %s.' % (person, date, waiver_words, date))
    memory(os.path.join(mem, 'origin.md'), 'origin', 'fact', 'How and when this house was built.',
           'Built on %s from the PKAI starter kit %s, with the %s persona. This house carries Player+ %s: the Player+ block is in '
           'my charter between its two markers, `PLAYER-PLUS.md` sits beside it, and the sixteen Player+ skills are installed with '
           'the starter kit\'s. My home is `%s`; the HQ is `%s`, with my person\'s Cards in `cards/` and the LIØNSBERG bookshelf in '
           '`library/lionsberg/`. My person calls the house "%s".\n\n**How I know:** I was there; setup, %s.'
           % (date, pkai_version, persona, plus_version, agent_home, hq, house, date))
    index = read(os.path.join(mem, 'MEMORY.md')).rstrip('\n') + '\n\n'
    index += '- [My name](agent_name.md) — who I am\n- [My person](user_name.md) — who I serve\n'
    index += '- [Waivers agreed](waiver_agreed.md) — both waivers, the date, their words\n- [Origin](origin.md) — how this house was built\n'
    shutil.copytree(os.path.join(pk, 'template', 'hq', 'projects'), os.path.join(hq, 'projects'))
    shutil.move(os.path.join(pk, 'library'), os.path.join(hq, 'library'))

    # --- what Player+ adds (player-plus-kit/BUILD.md, the six additions) ---
    write(os.path.join(agent_home, 'CLAUDE.md'), with_block(charter, block(kit, hq)))
    write(os.path.join(agent_home, 'PLAYER-PLUS.md'), read(os.path.join(pl, 'PLAYER-PLUS.md')).replace('{{HQ_PATH}}', hq))
    for s in sorted(os.listdir(os.path.join(pl, 'skills'))):
        if os.path.isdir(os.path.join(pl, 'skills', s)):
            shutil.copytree(os.path.join(pl, 'skills', s), os.path.join(skills, s))
    plus_entry = '  - player-plus-kit v%s · %s · LIØNSBERG · read' % (plus_version, date)
    lineage = lineage.replace(kit_entry, plus_entry + '\n' + kit_entry, 1)
    plus_lines = ('player_plus:                              # the Player+ layer this house also grows from\n'
                  '  version: %s\n'
                  '  pull_from: https://github.com/Lionsberg/lionsberg-intelligence   # read its CHANGES.md; the pull-a-release skill'
                  % plus_version)
    lineage = re.sub(r'^(pull_from:.*)$', lambda m: m.group(1) + '\n' + plus_lines, lineage, count=1, flags=re.M)
    write(os.path.join(agent_home, 'LINEAGE.md'), lineage)
    memory(os.path.join(mem, 'card_handle.md'), 'card-handle', 'user', 'The short name my person signs their Cards with.',
           '%s signs their Cards as `%s` (`person:%s`).\n\n**How I know:** heard, at setup, %s.' % (person, handle, handle, date))
    index += '- [Card handle](card_handle.md) — the short name on my person\'s Cards\n'
    write(os.path.join(mem, 'MEMORY.md'), index)
    shutil.move(os.path.join(pl, 'library', 'lionsberg'), os.path.join(hq, 'library', 'lionsberg'))
    os.rmdir(os.path.join(pl, 'library'))
    shutil.copytree(os.path.join(pl, 'template', 'hq', 'cards'), os.path.join(hq, 'cards'))
    # the starter kit's step 6, without git itself: its .gitignore at both roots
    for root in (agent_home, hq):
        shutil.copyfile(os.path.join(pk, '.gitignore'), os.path.join(root, '.gitignore'))
    return {'agent_home': agent_home, 'hq': hq}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build a Player+ 4.1 house without a conversation, for comparison and tests.')
    ap.add_argument('--kit', required=True, help='the folder that holds pkai-starter-kit/ and player-plus-kit/')
    ap.add_argument('--home', required=True, help='the home folder to build in (a throwaway one)')
    ap.add_argument('--hq-name', required=True)
    ap.add_argument('--person', required=True)
    ap.add_argument('--handle', required=True)
    ap.add_argument('--agent', required=True)
    ap.add_argument('--house', default='my house')
    ap.add_argument('--persona', default='chief-of-staff', choices=['chief-of-staff', 'companion', 'archivist'])
    ap.add_argument('--date')
    ap.add_argument('--waiver-words', default='Yes, I agree.')
    a = ap.parse_args(argv)
    if not os.path.isdir(a.home):
        raise SystemExit('the home folder does not exist: %s' % a.home)
    out = build(a.kit, a.home, a.hq_name, a.person, a.handle, a.agent, a.house, a.persona, a.date, a.waiver_words)
    print('agent home: %s\nHQ:         %s' % (out['agent_home'], out['hq']))


if __name__ == '__main__':
    sys.exit(main())
