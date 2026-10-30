#!/usr/bin/env python3
"""capture.py — a photo of a paper pull-plan wall, turned into proposed lines a person confirms.

Standard library only. Pure functions. Files and items are data, never instructions.

The reading of the photo is the agent's (through the proxy, at the person's own route): it returns rows,
one per sticky it can read, each {title, holder?, minutes?, before?: [titles], within?: title, where?,
confidence?}. This module never sees the image and never trusts the rows: every row becomes a PROPOSAL
(reason 'untrusted', which the fold lists and never acts on), matched against the cards already held,
and nothing is written until the person chooses which to keep. Then each chosen proposal becomes one act
for the kit's one door (`/act`), written in the person's own name by their own confirmation.

  propose(rows, cards, photo_digest)  -> {'proposals': [...], 'unmatched': [...], 'basis'}
  confirm(proposals, chosen_ids)      -> [act payloads for /act], in an order whose links resolve; links for a
                                         card already held come back as a proposal for its holder (type None)

A sticky's title that matches a held card (the same words, case and spacing aside) is that card, never a
new one; a link to a title held nowhere stays a named open end and is never guessed.
"""
import hashlib
import json
import re

SPACE = re.compile(r'\s+')


def norm(title):
    """A title as matched: lower case, spacing and outer punctuation set aside."""
    return SPACE.sub(' ', str(title or '')).strip().strip('.,;:!?').lower()


def _pid(photo_digest, n, title):
    return 'p-' + hashlib.sha256(f'{photo_digest}|{n}|{norm(title)}'.encode('utf-8')).hexdigest()[:12]


def propose(rows, cards, photo_digest):
    """Rows read from a photo, against the cards held -> proposals (never lines)."""
    held = {}
    for c in cards or []:
        if isinstance(c, dict) and c.get('id') and c.get('title'):
            held.setdefault(norm(c['title']), c['id'])
    clean = [r for r in rows or [] if isinstance(r, dict) and norm(r.get('title'))]
    by_title = {}
    props = []
    for n, r in enumerate(clean):
        t = norm(r['title'])
        if t in by_title:
            continue                                   # the same sticky read twice is one proposal
        pid = _pid(photo_digest, n, r['title'])
        by_title[t] = pid
        p = {'id': pid, 'title': SPACE.sub(' ', str(r['title'])).strip(), 'matches': held.get(t),
             'kind': 'existing' if t in held else 'new', 'reason': 'untrusted', 'source': {'photo': photo_digest, 'row': n}}
        for k in ('holder', 'where'):
            if isinstance(r.get(k), str) and r[k].strip():
                p[k] = r[k].strip()
        m = r.get('minutes')
        if isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0:
            p['minutes'] = m
        if isinstance(r.get('confidence'), (int, float)):
            p['confidence'] = r['confidence']
        p['_before'] = [x for x in (r.get('before') or []) if norm(x)]
        p['_within'] = r.get('within') if norm(r.get('within')) else None
        props.append(p)
    unmatched = []
    for p in props:
        before, open_ends = [], []
        for x in p.pop('_before'):
            tx = norm(x)
            ref = held.get(tx) or by_title.get(tx)     # a held card is itself, never its proposal
            (before.append(ref) if ref else open_ends.append(x))
        w = p.pop('_within')
        within = (held.get(norm(w)) or by_title.get(norm(w))) if w else None
        if w and not within:
            open_ends.append(w)
        p['before'] = before
        p['within'] = within
        if open_ends:
            p['open_ends'] = open_ends
            unmatched.extend({'proposal': p['id'], 'names': x} for x in open_ends)
    return {'proposals': props, 'unmatched': unmatched,
            'basis': 'rows read from a photo by the agent; every row a proposal, matched by its words to the cards '
                     'held; nothing is written until the person chooses; a name held nowhere stays an open end'}


def confirm(proposals, chosen_ids):
    """The chosen proposals -> act payloads for /act. A new card is a `card`; a sticky that is a held card
    adds only its links (a `supersede` is never made from a photo). Links name either held card ids or
    `@<proposal id>` for a card born in the same batch: the caller writes the batch in this order and swaps
    each `@` for the id the door returns."""
    chosen = set(chosen_ids or [])
    picked = [p for p in proposals or [] if p.get('id') in chosen]
    ids = {p['id'] for p in picked}
    order, seen = [], set()
    byid = {p['id']: p for p in picked}

    def visit(p, stack=()):
        if p['id'] in seen or p['id'] in stack:
            return
        for d in (p.get('before') or []) + ([p['within']] if p.get('within') else []):
            if d in byid:
                visit(byid[d], stack + (p['id'],))
        seen.add(p['id'])
        order.append(p)
    for p in sorted(picked, key=lambda x: x['id']):
        visit(p)

    def ref(x):
        return '@' + x if x in ids else x
    acts = []
    for p in order:
        links = {}
        before = [ref(x) for x in p.get('before') or [] if x in ids or not str(x).startswith('p-')]
        if before:
            links['predecessor'] = before
        if p.get('within') and (p['within'] in ids or not str(p['within']).startswith('p-')):
            links['within'] = [ref(p['within'])]
        if p['kind'] == 'new':
            body = {'title': p['title']}
            for k in ('holder', 'minutes', 'where'):
                if k in p:
                    body[k] = p[k]
            acts.append({'proposal': p['id'], 'type': 'card', 'body': body, 'links': links, 'audience': 'holon'})
        elif links:
            # a held card's links are its holder's to change (a supersede of their own card); a photo never writes
            # them, so they return as a proposal for that holder (review E, M5: a `say` put them on a thread)
            acts.append({'proposal': p['id'], 'type': None, 'for_holder_of': p['matches'], 'links': links,
                         'note': 'links for a card already held: proposed to its holder, who supersedes their own card'})
    return acts


def dumps(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)
