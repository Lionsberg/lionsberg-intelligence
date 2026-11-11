#!/bin/sh
# make_release_zip.sh — the download a newcomer's kickoff sentence names: the two kit folders, and nothing else.
# Usage: sh tools/make_release_zip.sh [out.zip]     (run from the top of the repository, on a committed tree)
set -eu
OUT="${1:-player-plus-kit.zip}"
git diff --quiet HEAD -- pkai-starter-kit player-plus-kit || { echo "commit your changes to the two kit folders first" >&2; exit 1; }
git archive --format=zip -o "$OUT" HEAD pkai-starter-kit player-plus-kit
echo "wrote $OUT"
