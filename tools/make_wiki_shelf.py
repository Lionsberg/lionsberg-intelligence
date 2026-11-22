#!/usr/bin/env python3
"""make_wiki_shelf.py — the LIØNSBERG Wiki as one archive, for the bookshelf's third shelf.

The wiki's page names carry Ø and other letters outside plain ASCII, and a name like that can stop an
unzip. So the wiki travels inside the kit as one archive with a plain name, and a build unpacks it with
`tar`, which every Mac and Windows 10 and 11 have. Every member sits under `wiki/`, so unpacking the
archive in `library/lionsberg/` makes `library/lionsberg/wiki/`.

    python3 -I tools/make_wiki_shelf.py <the wiki's folder>
    python3 -I tools/make_wiki_shelf.py <the wiki's folder> --out <somewhere>/wiki.tar.gz

The same folder always makes the same bytes: names sorted and in NFC, one fixed time, no owner names,
plain modes. Skips .git, .obsidian, .DS_Store and symbolic links. Standard library only.
"""
import argparse
import gzip
import io
import os
import sys
import tarfile
import unicodedata

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(TOP, 'player-plus-kit', 'library', 'lionsberg', 'wiki.tar.gz')
ROOT = 'wiki'
SKIP = {'.git', '.obsidian', '.DS_Store'}
MTIME = 1767225600          # 2026-01-01T00:00:00Z, the same for every member


def entries(src):
    """(path on disk, name in the archive, is a folder), sorted by name in the archive."""
    out, links = [], []
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in SKIP]
        for n in dn + fn:
            p = os.path.join(dp, n)
            if n in SKIP:
                continue
            if os.path.islink(p):
                links.append(p)
                continue
            rel = os.path.relpath(p, src).replace(os.sep, '/')
            out.append((p, unicodedata.normalize('NFC', ROOT + '/' + rel), os.path.isdir(p)))
    return sorted(out, key=lambda e: e[1]), links


def member(name, is_dir, size=0):
    t = tarfile.TarInfo(name)
    t.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    t.mode = 0o755 if is_dir else 0o644
    t.size = size
    t.mtime = MTIME
    t.uid = t.gid = 0
    t.uname = t.gname = ''
    return t


def make(src, out):
    if not os.path.isfile(os.path.join(src, 'README.md')):
        raise SystemExit('the wiki has no README.md at its top: %s' % src)
    items, links = entries(src)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.PAX_FORMAT, encoding='utf-8') as tar:
        tar.addfile(member(ROOT, True))
        for path, name, is_dir in items:
            if is_dir:
                tar.addfile(member(name, True))
            else:
                with open(path, 'rb') as f:
                    data = f.read()
                tar.addfile(member(name, False, len(data)), io.BytesIO(data))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'wb') as f:
        with gzip.GzipFile(filename='', mode='wb', fileobj=f, compresslevel=9, mtime=0) as gz:
            gz.write(raw.getvalue())
    files = [e for e in items if not e[2]]
    pages = sum(1 for e in files if e[1].endswith('.md'))
    return {'files': len(files), 'pages': pages, 'folders': len(items) - len(files) + 1, 'links_skipped': links,
            'bytes': os.path.getsize(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Write the LIØNSBERG Wiki as one archive for the bookshelf.')
    ap.add_argument('source', help="the wiki's folder (its README.md at the top)")
    ap.add_argument('--out', default=OUT, help='where to write the archive (default: %(default)s)')
    a = ap.parse_args(argv)
    r = make(a.source, a.out)
    print('wrote %s: %d files (%d pages), %d folders, %d bytes' % (a.out, r['files'], r['pages'], r['folders'], r['bytes']))
    for p in r['links_skipped']:
        print('skipped a symbolic link: %s' % p, file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
