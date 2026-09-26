#!/bin/bash
# room-post.sh: post outbox/room-post.txt to a So Many Rooms chat. The only way the kit's permissions let an agent post.
# Usage: bash scripts/room-post.sh <token>     (the token is the long part of your Link for your agent, between /feed/ and /)
# It posts one file to one room and nothing else; the go is still your person's word.
set -eu
T=${1:?usage: room-post.sh <token>}
[ $# -eq 1 ] || { echo "room-post: exactly one argument, the token"; exit 2; }
[[ "$T" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "room-post: the token may hold only letters, digits, - and _"; exit 2; }
F=outbox/room-post.txt
[ -s "$F" ] || { echo "room-post: write the message to $F first"; exit 2; }
curl -s -X POST -H "Content-Type: text/plain" --data-binary @"$F" "https://somanyrooms.com/feed/$T/chat"
echo
