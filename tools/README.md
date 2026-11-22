# tools/

For whoever keeps this kit. Nothing here is part of a house.

- `build_house.py` builds a Player+ house into a throwaway home with no conversation, so that a build made by a Claude and a person can be compared against it, file for file. The tests use it.
- `compare_houses.py` builds the same house from the same answers and compares the two, file for file.
- `make_release_zip.sh` writes the download the kickoff sentence names: the two kit folders, and nothing else.
- `make_wiki_shelf.py <the wiki's folder>` writes `player-plus-kit/library/lionsberg/wiki.tar.gz`, the LIØNSBERG Wiki as one archive with a plain name, since the wiki's own file names are not plain ASCII; the same folder always makes the same bytes.
  A build unpacks it with `tar` into `<HQ>/library/lionsberg/wiki/` and removes the archive. Run it again, and the tests, when the wiki carried should change.

To carry a newer release of the starter kit: replace `pkai-starter-kit/` with that release's tree, unchanged; write its hashes to `tests/pkai-starter-kit.sha256` from the keeper's own repository (`git ls-files -z | xargs -0 shasum -a 256`, sorted by name); name the new version in `player-plus-kit/RELEASE.md`, `CHANGES.md` and `LINEAGE.md`; and run the tests. They say where the starter kit's steps or personas moved under this kit's additions.
