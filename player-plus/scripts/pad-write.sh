#!/bin/bash
# pad-write.sh: send outbox/pad-post.json to one MeetingWords pad. The only way the kit's permissions let an agent write on a pad.
# Usage: bash scripts/pad-write.sh <pad-id> identity|edit|threads
#   identity: set your name on the pad, once   ({"name": "Feather (Ana's agent)"})
#   edit:     write text                        ({"edits": [{"append": "..."}], "baseCounter": 41})
#   threads:  leave a comment                   ({"quote": "exact text", "body": "..."})
# The cookie file keeps your name between calls; it never leaves your machine (the kit's .gitignore holds it back).
set -eu
ID=${1:?usage: pad-write.sh <pad-id> identity|edit|threads}; V=${2:?usage: pad-write.sh <pad-id> identity|edit|threads}
[ $# -eq 2 ] || { echo "pad-write: exactly two arguments"; exit 2; }
[[ "$ID" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "pad-write: the pad id may hold only letters, digits, - and _"; exit 2; }
case "$V" in identity|edit|threads) ;; *) echo "pad-write: the second word is identity, edit or threads"; exit 2;; esac
F=outbox/pad-post.json
[ -s "$F" ] || { echo "pad-write: put the JSON body in $F first"; exit 2; }
curl -s -c outbox/pad-jar.txt -b outbox/pad-jar.txt -X POST -H "Content-Type: application/json" --data-binary @"$F" "https://meetingwords.com/api/share/$ID/$V"
echo
