#!/usr/bin/env python3
"""serve.py: the HUD's tiny local server. Python standard library only.

WHAT IT DOES
  Binds to 127.0.0.1 only and serves this folder's static files (the HUD), plus:

  GET  /state          the merged state: the home holon's state.json and every
                       cells/<name>/state.json under it, folded into one object in
                       engine/STATE.md's shape, with the server's own `hud` block
                       (sources and their readability, the folded layout events,
                       acts still inside their undo window, the undo window).
  GET  /stream         server-sent events: `event: state` whenever any holon's
                       state.json or record/ changes, or an act is written or undone.
  POST /act            {type, holon, body, links, audience, hold_ms?, confirmed?,
                       sheet_token?} -> {pending, writes_at, undo_ms}. The act is held
                       for the undo window (five seconds; up to fifteen if asked),
                       then written as one event line (engine/SCHEMA.md).
  DELETE /act/<id>     Undo, within the window -> {undone: true}.
  POST /publish-sheet  -> {token}: a one-time token the publish sheet asks for when
                       the person presses Publish; a `publish` act without it is refused.

WHERE LINES GO
  Every act is written by ../engine/record.py's append(holon_dir, actor, for, type,
  body, links, audience, reason, key=...): the record layer salts, chains, signs and
  names the file. Only when record.py is absent (the paper floor) does this server write
  the line itself, in the same salted shape, to <holon>/record/<actor>.jsonl (':' written
  as '_', as record.actor_file names it) with reason "human", prev chained to
  that actor's last line, id = sha256 of the canonical line, and sig made with
  `ssh-keygen -Y sign -n lionsberg-record` when --key is given (empty otherwise: the
  paper floor).

THE PAGE'S TOKEN (no other local process may act)
  On start it writes a random token to <HQ>/.hud-token (mode 0600). GET /token gives it
  only to a request whose Host is 127.0.0.1:<port> (or localhost:<port>) and which
  carries no Origin header, the page's own first read. The page sends it as X-HUD-Token
  on every POST /act, DELETE /act/<id> and POST /publish-sheet; an act without it is
  refused. Any request whose Host is not 127.0.0.1 or localhost with this port is
  refused, and so is any Origin other than the server's own.

SIGNING
  A person's yes is signed with that person's own key, ~/.ssh/lionsberg-<handle> for
  person:<handle> (or --key), never an agent's key, and only when the undo window has
  passed and the line is written. With no key the line is written unsigned, at the
  paper floor, and the server says so.

WHAT IT REFUSES
  Any audience but "holon" (an audience widens only by a `publish` act); a type not
  in engine/types.json (or `layout`); a human-only type not confirmed by the person
  in the HUD; a `publish` without the publish sheet's token; a holon it does not hold.

THE DOCK (DESIGN-DOCK.md)
  GET  /agent/list     the player's agents, their declared capabilities and states
  POST /agent/wake     {agent, confirmed: true}: starts the agent through agent_host.py,
                       only on the player's confirmed tap (never a page load)
  POST /agent/say      {agent, conversation?, text, about?, page?, confirmed: true}
                       page {line, question, options, local_answers, settled: {option, card}}
                       is passed to the host with the served Deal's cards; the answer carries
                       `local` {kinds, lines, text, reach?} when the host answered a first-contact
                       line itself (agent_host.py, POST /say)
  POST /agent/stop · /agent/mode · /agent/answer · /agent/offer · /agent/prefs
  GET  /agent/stream   ?conversation=&since=  server-sent events, relayed from the host
  GET  /agent/routes   ?conversation=&turn=   that turn's route lines, matched by its time
                       window; where each went (on this computer or not), never a body
  GET  /agent/figures  ?agent=  the trust layer's Full depth (DESIGN-TALK.md): the
                       agent's figures block and every raw field its harness gave (agent_host.py,
                       GET /figures). /agent/list carries each agent's `figures` (each the
                       harness's own or null), its `clock` mid-turn, and a worker's `worker` row
  GET  /agent/mode     ?agent=  the modes the harness declared, in its own names, with the
                       Talk's plain words beside; POST /agent/mode sets one (session/set_mode)
  POST /agent/pty/open {agent, confirmed: true} · /agent/pty/write · /agent/pty/close
  GET  /agent/pty/stream  the command line: a pseudo-terminal in the agent's home, a second
                       conversation with the agent (never the live one), on the computer only
  POST /discern        {route, verdict, rating?, note?, confirmed: true}: the person's own
                       `discern` line, by person:<handle> in the person's own file, written
                       with record.append and signed with ~/.ssh/lionsberg-person-<handle>
                       (through ssh-agent) after the person's tap; without the key it is
                       written unsigned, on paper, and the answer says why. The proxy's own
                       /discern is never used for this: it writes only an agent's untrusted note

MAIL (engine/mail.py; hud/DESIGN-MAIL.md §10.2, §10.5). GET /state carries `badges`, `mail` and
`transports.mail` from the carried store (<HQ>/.carried/), pruned on every read so a line the
pull brought folds once. Each needs the page's token and the person's own tap (confirmed: true):
  POST /mail/send      {line_id, to, confirmed: true}: mail.send_line(..., on_the_persons_send=True)
                       with the account in ~/.config/lionsberg/mail.json; refused otherwise
  POST /mail/read      {id}: marks a carried item read on this machine; nothing reaches the record
  POST /mail/line      {id, confirmed: true}: the person's yes to a proposed line from prose,
                       written as the person's own line by record.append, signed as /discern is;
                       the prose entry is then removed from the carried store

THE TALK (DESIGN-ROOM §8.2). Said lines live on this machine, in the home's own store
<HQ>/.talk/<room id>/said.jsonl (0600, gitignored, never in a cell's clone, never through a
link; each row carries an HMAC under <HQ>/.talk/.key, and a row without it is not read or kept),
never in the record until kept. Each needs
the page's token; a said line and a keep need the person's own tap (confirmed: true):
  POST /say            {room, text, part?, parent?, confirmed: true}: a present person's said line
  GET  /talk?room=     the room's said lines (the newest 500), each with `kept` once kept
  POST /keep           {room, id, confirmed: true}: the room's keeper agrees another's said line;
                       a `settle` is written in the room's record as the keeper's own line,
                       signed as /discern is
  GET  /presence?room= who is present, from rooms.py over the fold's trust, never a raw list
  Every said line and keep bumps /stream, which then sends `event: talk` with the new rows.
  Every one of them needs the page's token (X-HUD-Token), GETs included. The agent host
  is its own process (agent_host.py), started detached on the player's first word, so a
  restart of this server ends no conversation.

THE BODIES (DESIGN-BODIES.md §11.3)
  GET  /bodies/live    what only this machine can say about your agent's bodies, read
                       live and never written to the record, never sent anywhere:
                       for each folder under <HQ>/bg/ (not bg/archive/): whether the
                       process its claim names is alive (the pid in its RUNNING file,
                       checked on this machine), its newest write and its writes in the
                       last thirty minutes; the desk lease's holder process; the gaps in
                       the prime's heartbeat file (<HQ>/.heartbeat, one "<time> <monotonic
                       seconds>" line a minute), each read as slept (the machine's own
                       clock stood still) or stopped (the service ended while the machine
                       was awake); and the usage the vendor's harness last wrote on this
                       machine (--usage-file, default ~/.claude/statusline-last.json; only
                       its five-hour and seven-day used percentages and reset times are
                       read, nothing else in the file). The same block rides in GET /state
                       as hud.bodies_live. One machine per Player+.
                       With --desk (a house's desk file) the block also carries `machine`:
                       the prime (the interactive harness whose working folder is the house,
                       alive or not, and whether it holds the desk), each background body
                       (its folder joined by name to its process; a RUNNING claim whose
                       process is gone is stale), the dock and any other window, each with
                       the helpers its session has running (from the harness's sessions
                       folder: a helper's description, model and start, never its words).
                       The process table is read once in five seconds; no environment is
                       read; a handoff's presence and size only, never its contents (its
                       `review_min` line, for the Deal's card, is read by the fold below).
                       Each machine entry also carries session_id, status (idle|busy, from the
                       harness's registry) and window (it has a terminal, or is the Claude app).

THE BODIES' ACTS (DESIGN-BODIES §4, §3.3, §7; 2026-10-25)
  POST /agent/body     {task, from_card?, confirmed: true}: a second body of the player's agent,
                       started through agent_host.py's POST /body on the person's own tap, after the
                       cost was said. The host starts it over the Agent Client Protocol with no
                       terminal window, from the player's agents file, with the house's home folder
                       (the folder holding --bg and --desk) as its cwd and the kit's background-body
                       page (skills/foreground-background/SKILL.md) named in its brief. /state lists
                       it among hud.agents with `body: {name, task, started, session, spent_today}`.
  A handoff waiting    each body folder under bg/ with a handoff.md under two days old and no review
                       folds one card into deal.cards ("Read {name}'s handoff", its minutes from the
                       handoff's `review_min` line in its first 40 lines; nothing else of it is read
                       for the state), counted by the Deal like any other. A review is the person's
                       own `witness` (body: handoff_of, handoff_bytes, card), written through /act to
                       the person's home; after it the card is gone and the body's entry says so.
  GET  /bodies/handoff?body=   the text of that body's handoff.md, read-only (a megabyte at most),
                       only for a body that keeps its own folder under bg/, never through a link.
  What each spent      each machine entry carries `spent_today`: {usd} from the harness's cost ledger
                       (--cost-ledger, default ~/.claude/cost-ledger.jsonl: each line's day, session,
                       running cost and folder only), else {tokens} from its own transcript's usage
                       (assistant lines today), else null. bodies_live.spent_today is the house's day:
                       every session the ledger saw working in the house today.

THE BODIES' TALK (a terminal body as a room; class BodyTalk). Each needs the page's token; a
send and a window need the person's own tap (confirmed: true). A body is named as /bodies/live
names it (case folded; the prime is "prime").
  GET  /bodies/reach?body=     {reachable, how: socket|none, window, status, why?}
  GET  /bodies/talk?body=&since=  server-sent events (`event: line`) of that session's own
                       conversation, read from its transcript and followed as it grows:
                       {n, ts, kind: user|agent|tool|state, text, turn}. `n` is the transcript
                       line; `since` resumes. Tool uses are short rows ("Read deal.js", "Ran a
                       command"); thinking is only `state: thinking`; tool results never sent.
  POST /bodies/talk    {body, text, confirmed: true}: one message into that live session, through
                       its own inbox socket, as the harness's sessions message one another (an
                       `auth` line with the session's key, then one `user` line, newline-delimited
                       JSON); it lands labelled <cross-session-message from-name="the ICE"> with
                       the sender name "the ICE" (no label in the text; the person asked for none). Sent only after confirming that the
                       process listening is that body's own. Unreachable: {reachable: false, why}.
  POST /bodies/window  {body, confirmed: true}: brings that body's own window forward (the Terminal
                       or iTerm tab whose tty is its terminal; the Claude app for a desktop session).
                       No other window is moved, hidden or minimized. Never on the phone door.
  READ (only this user's own files, never through a link): ~/.claude/sessions/<pid>.json (the
  harness's registry, --harness-sessions) and the one transcript a chosen body's record names,
  ~/.claude/projects/<slug of its folder>/<sessionId>.jsonl (--sessions). A session's key
  (<pid>.<hash>.key) is read into memory for one send, then dropped: never kept, logged, printed
  or answered. NEVER READ: any other transcript, another user's files, the environment.

THE PHONE DOOR (off by default; --phone enables it)
  With --phone, the player may open, from this computer's own HUD, a second listener bound
  only to the machine's private-network address (--phone-address, else the first address in
  100.64.0.0/10, else a private LAN address; never 0.0.0.0, never a public address):
  POST /phone/listen {on, confirmed: true}   from the computer only
  POST /phone/pair                           from the computer only: a one-time code, five minutes
  POST /phone/claim {code, name?}            from the phone: returns its own device token,
                                             kept on the computer only as a hash in
                                             <HQ>/.hud-devices (mode 0600)
  DELETE /phone/<device>                     revokes that phone at once
  POST /voice                                a voice note, turned into words by --speech CMD
                                             on this computer; the audio is deleted after
  On the phone listener every route but the static files and /phone/claim needs the device
  token (X-HUD-Device); /token is never given there.
  THE DOOR SPEAKS TLS (a phone's browser gives the microphone and speech recognition only to a
  secure page). Opening the door opens two listeners on the same private-network address:
    https://<address>:<phone port>/        the door itself (TLS, Python's ssl), everything above
    http://<address>:<phone port + 1>/     the trust page only: GET / (how to trust this computer
                                           once, the fingerprint to compare) and GET /phone-door.crt
                                           (this computer's own authority, DER); every other
                                           request there is refused in one sentence
  The certificates are made here (hud/phone_cert.py, standard library only) under
  <HQ>/.phone-door/<address>/ (files 0600, folders 0700, ignored by git): an authority that lives a
  year and may vouch only for that one address, and the door's certificate (thirty days, renewed
  quietly). /phone/pair answers the trust page's address with the code (`address`), the door's
  own (`door`) and the fingerprint; GET /state's hud.phone carries `trust`, and says when the
  fingerprint changed. DESIGN-PHONE-DOOR.md is the design, with what trusting the authority means.

THE LAYERED VOICE (DESIGN-DOCK "The layered voice"; both off unless started with them)
  Every voice route needs the page's token (or, on the phone door, the device token). No audio is
  sent anywhere but this server on this computer, and no audio or rendering enters the record: a
  voice note's words become the person's own line only when the person sends them.
  GET  /voice/info     {hear: bool, say: bool}: whether --speech and --voice are set here
  POST /voice          a recording (any audio the browser makes) -> {text}: --speech CMD is run
                       with the audio file's path as its last argument and its stdout is the words.
                       The file is written under <HQ>/.voice/ (0600) and deleted after, unless
                       ?keep=true.
  POST /voice/say      {text} -> the WAV bytes (audio/wav): your agent's words read aloud by
                       --voice CMD, for a page that plays them.
  THE --voice CONTRACT: CMD is split like a shell line (quotes kept, no shell run) and the text is
  appended as its LAST argument (at most 4000 characters, leading dashes and spaces removed so it
  is never read as an option). The command writes a new WAV file and prints that file's path on
  the last line of its stdout, exit status 0, within 60 seconds. The server reads it only if it is
  a regular file (no link), under 20 MB, begins RIFF....WAVE, and was written after the request
  began; it then deletes that file and answers its bytes. Anything else: 422, nothing played.
  Without --voice: 501. Example, a two-line script on a Mac (nothing is played aloud by it):
      #!/bin/sh
      f=$(mktemp -t her-voice).wav; say -o "$f" --data-format=LEI16@22050 -- "$1" && echo "$f"

USAGE
  python3 serve.py --hq PATH [--actor person:handle] [--port 8765] [--key ~/.ssh/lionsberg-<handle>]
  python3 serve.py --fixture fresh [--hq PATH]     serve fixtures/fresh.json as the state;
                                                   acts are written to --hq, or to a
                                                   temporary folder it names on start.
  Nothing it does plays sound or reaches the network.
"""
import argparse
import atexit
import hashlib
import hmac
import importlib.util
import ipaddress
import json
import os
import re
import secrets
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
LINE_ORDER = ["v", "id", "ts", "actor", "for", "holon", "type", "body", "links",
              "audience", "reason", "prev", "sig"]
LINK_KINDS = ["predecessor", "successor", "serves", "fulfils", "answers", "witnesses",
              "anchored_to", "supersedes"]
UNDO_MS, UNDO_MAX_MS = 5000, 15000
# Quiet acts: the page's own study lines and its layout. Written like any act, but they never wake
# /stream: each wake costs every open page a /state read and a full redraw (the profiler, 2026-10-25:
# one study line cost the page three reads and three redraws), and no view reads them back live.
QUIET_TYPES = frozenset({"study", "layout"})
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_json(path: Path):
    """(value, None) or (None, a plain reason)."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "no saved state yet"
    except json.JSONDecodeError:
        return None, "its saved state could not be parsed"
    except OSError as e:
        return None, f"it could not be opened ({e.strerror or 'unknown'})"


def as_list(x):
    return x if isinstance(x, list) else []


def as_dict(x):
    return x if isinstance(x, dict) else {}


# ------------------------------------------------------------------ the holons held

def inception_id(d: Path):
    """The holon id its own inception line gives (record.read), or None when record.py cannot say."""
    try:
        if str(ENGINE) not in sys.path:
            sys.path.insert(0, str(ENGINE))
        import record as rec
        return rec.read(str(d)).get("holon") or ""
    except Exception:
        return None


def append_nofollow(base: Path, rel: list, text: str):
    """Append text to base/<rel...> creating folders 0700, never through a link: no component of
    the path may be a link, and the file is opened with O_NOFOLLOW. Raises OSError otherwise."""
    cur = base
    for part in rel[:-1]:
        cur = cur / part
        if cur.is_symlink():
            raise OSError(f"{cur.name} is a link; nothing is written through it")
        cur.mkdir(mode=0o700, exist_ok=True)
        if cur.is_symlink() or not cur.is_dir():
            raise OSError(f"{cur.name} is not a plain folder")
    fd = os.open(str(cur / rel[-1]), os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(text)


MAIL_LINE_TYPES = ("say",)   # what the Threads and Mail view offers on a proposal from prose


class Holons:
    """The home holon and every cells/<name>/ under it."""

    def __init__(self, hq: Path):
        self.hq = hq

    def dirs(self):
        out = [self.hq]
        cells = self.hq / "cells"
        if cells.is_dir():
            out += sorted(p for p in cells.iterdir() if p.is_dir() and not p.name.startswith("."))
        return out

    def info(self, d: Path) -> dict:
        info, _ = read_json(d / "holon.json")
        return as_dict(info)

    def by_id(self) -> dict:
        """{holon id: folder}, from record.holon_dirs (the home bound to the HQ, a cell claiming a held
        id refused). Only when record.py cannot answer: the HQ's own holon.json first, never displaced,
        and a cell only when its holon.json id is its inception line's id and is not already held."""
        try:
            if str(ENGINE) not in sys.path:
                sys.path.insert(0, str(ENGINE))
            import record as rec
            if callable(getattr(rec, "holon_dirs", None)):
                return {i: Path(d) for i, d in rec.holon_dirs(str(self.hq)).items()}
        except Exception:
            pass
        out = {}
        home = self.info(self.hq).get("id")
        if isinstance(home, str):
            out[home] = self.hq
        for d in self.dirs()[1:]:
            i = self.info(d).get("id")
            if isinstance(i, str) and i not in out and inception_id(d) in (i, None):
                out[i] = d
        return out

    def signature(self) -> tuple:
        """A cheap fingerprint of everything that can change the state."""
        sig = []
        for d in self.dirs():
            for f in [d / "state.json", d / "holon.json"]:
                try:
                    sig.append((str(f), f.stat().st_mtime_ns))
                except OSError:
                    sig.append((str(f), 0))
            rec = d / "record"
            if rec.is_dir():
                for f in sorted(rec.glob("*.jsonl")):
                    try:
                        st = f.stat()
                        sig.append((str(f), st.st_mtime_ns, st.st_size))
                    except OSError:
                        pass
        return tuple(sig)


def merge_states(parts):
    """Fold several STATE v1 objects into one. The home's top level wins; lists are
    joined and de-duplicated by (holon, id); per-holon maps are joined."""
    merged = None
    seen = {}
    for st in parts:
        if merged is None:
            merged = json.loads(json.dumps(st))
            for k, v in merged.items():
                if isinstance(v, list):
                    seen[k] = {(as_dict(i).get("holon"), as_dict(i).get("id")) for i in v}
            continue
        for k, v in st.items():
            if isinstance(v, list):
                tgt = merged.setdefault(k, [])
                keys = seen.setdefault(k, {(as_dict(i).get("holon"), as_dict(i).get("id")) for i in tgt})
                for item in v:
                    key = (as_dict(item).get("holon"), as_dict(item).get("id"))
                    if key in keys and key != (None, None):
                        continue
                    keys.add(key)
                    tgt.append(item)
            elif isinstance(v, dict) and k in ("kept", "score", "tea", "owed", "discernments"):
                tgt = merged.setdefault(k, {})
                for kk, vv in v.items():
                    if isinstance(vv, dict) and isinstance(tgt.get(kk), dict):
                        for a, b in vv.items():
                            tgt[kk].setdefault(a, b)
                    elif isinstance(vv, list) and isinstance(tgt.get(kk), list):
                        ids = {json.dumps(x, sort_keys=True) for x in tgt[kk]}
                        tgt[kk] += [x for x in vv if json.dumps(x, sort_keys=True) not in ids]
                    else:
                        tgt.setdefault(kk, vv)
            elif k not in merged:
                merged[k] = v
    return merged or {"v": 1}


OWN_LINKS = ("answers", "anchored_to", "settles")
OWN_TYPES = {"answer", "ratify", "decide", "say", "settle", "commit", "kept", "witness"}


def fold_own(st: dict, acts: list, actor: str) -> dict:
    """One truth after an act (the night test, 2026-10-24): fold the person's own acts, held or
    written, into the state served to every view, so the top line, the Deal, the Map and Threads
    change together, before the engine next runs and in fixture mode too. Only what the act
    settles is changed: the card it answers is marked answered in the deal (never removed, so
    "2 of 2" holds), its owed entry (and an owed entry about the same card, by title) is done,
    a thread it answers has the person's turn taken, a decision it answers is decided. The
    engine's briefing describes the deal before the answer, so it is dropped once anything in it
    is answered. Idempotent: a state the engine has already re-folded is left as it is."""
    targets = set()
    for a in acts or []:
        if not isinstance(a, dict) or a.get("type") not in OWN_TYPES:
            continue
        links = as_dict(a.get("links"))
        for k in OWN_LINKS:
            targets.update(i for i in as_list(links.get(k)) if isinstance(i, str))
        card = as_dict(a.get("body")).get("card")
        if isinstance(card, str):
            targets.add(card)
    if not targets:
        return st
    cards = {as_dict(c).get("id"): as_dict(c) for c in as_list(st.get("cards"))}
    titles = {str(cards[t].get("title") or "").strip().lower() for t in targets if t in cards} - {""}
    deal = as_dict(st.get("deal"))
    changed = False
    for dc in as_list(deal.get("cards")) + as_list(as_dict(deal.get("beyond")).get("cards")):   # the next hand too
        if isinstance(dc, dict) and dc.get("id") in targets and not dc.get("answered"):
            dc["answered"] = True
            changed = True
    if changed:
        deal["briefing"] = None
    for e in as_list(as_dict(st.get("owed")).get("entries")):
        if isinstance(e, dict) and e.get("holder") == actor and (
                e.get("id") in targets or str(e.get("title") or "").strip().lower() in titles):
            e["status"] = "done"
    for th in as_list(st.get("threads")):
        if isinstance(th, dict) and th.get("id") in targets:
            th["last_actor"] = actor
            th["to"] = [x for x in as_list(th.get("to")) if x != actor]
    for d in as_list(st.get("decisions")):
        if isinstance(d, dict) and (d.get("id") in targets or str(d.get("title") or "").strip().lower() in titles):
            d["state"] = "decided"
    for q in as_list(st.get("questions")):
        if isinstance(q, dict) and q.get("id") in targets:
            q["state"] = "answered"
    hud = st.setdefault("hud", {})
    hud["folded_own"] = sorted(targets)
    return st


def fold_layouts(lines):
    """The latest `layout` event per name, after supersessions."""
    superseded = set()
    for ln in lines:
        for i in as_list(as_dict(ln.get("links")).get("supersedes")):
            superseded.add(i)
    latest = {}
    for ln in sorted((l for l in lines if l.get("type") == "layout"), key=lambda l: str(l.get("ts", ""))):
        if ln.get("id") in superseded:
            continue
        b = as_dict(ln.get("body"))
        name = b.get("name") or "player"
        latest[name] = {"id": ln.get("id"), "actor": ln.get("actor"), "ts": ln.get("ts"), "name": name,
                        "views": as_list(b.get("views")), "hidden": as_list(b.get("hidden")),
                        "holons": as_list(b.get("holons")), "type": b.get("type", "regular"),
                        "theme": b.get("theme", "system"), "density": b.get("density", "calm"),
                        "default": bool(b.get("default")), "undo_ms": b.get("undo_ms"),
                        "dock": b.get("dock") if b.get("dock") in ("open", "collapsed") else None,
                        "phone": b.get("phone") if b.get("phone") in ("on", "off") else None}
    return list(latest.values())


def read_record(d: Path):
    out = []
    rec = d / "record"
    if not rec.is_dir():
        return out
    for f in sorted(rec.glob("*.jsonl")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                ln = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(ln, dict):
                out.append(ln)
    return out


# ------------------------------------------------------------------ the server's state

class Hub:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.version = 0
        self.pending = {}            # id -> {req, writes_at, timer}
        self.written = {}            # id -> {line_id, type, signed}: what each held act became (GET /act/<id>)
        self.own = []                # the person's acts written while this server runs, folded into /state (fold_own)
        self.tokens = set()
        self.quiet_pairs = []        # (fingerprint before, after) of each quiet write: the watch lets them pass silently
        self.wlock = threading.Lock()  # one write at a time, so each line chains to the last
        self.types = self._types()
        t, _ = read_json(ENGINE / "types.json")   # home-only types: written only in the person's own home
        self.home_only = {k for k, v in as_dict(as_dict(t).get("types")).items() if as_dict(v).get("home_only")}
        self.fixture = None
        if args.fixture:
            p = HERE / "fixtures" / f"{args.fixture}.json"
            self.fixture, why = read_json(p)
            if self.fixture is None:
                sys.exit(f"serve.py: fixture {p.name}: {why}")
            if getattr(args, "shift_clock", False):    # the sample's clock moved to now, every interval kept (clockshift.py)
                import importlib.util as _ilu
                _spec = _ilu.spec_from_file_location("clockshift", HERE / "clockshift.py")
                _cs = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_cs)
                self.fixture = _cs.shift(self.fixture)
        if args.hq:
            self.hq = Path(args.hq).expanduser().resolve()
        else:
            self.hq = Path(tempfile.mkdtemp(prefix="hud-acts-"))
            print(f"serve.py: no --hq given; acts are written under {self.hq}", file=sys.stderr)
        self.holons = Holons(self.hq)
        self.writer = self._record_module()
        self.mail = self._mail_module()
        self.actor = args.actor or self._keeper() or as_dict(self.fixture).get("actor") or "person:player"
        self.key = self._person_key()
        self.token = secrets.token_hex(24)
        tok = self.hq / ".hud-token"
        try:
            self.hq.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(tok), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(self.token + "\n")
            os.chmod(str(tok), 0o600)
        except OSError as e:
            sys.exit(f"serve.py: could not write {tok} ({e.strerror})")
        self.bridge = AgentBridge(self)
        self.phone = PhoneDoor(self)
        self.bodies = BodiesLive(self)
        self.bodytalk = BodyTalk(self)
        self.talk = Talk(self)

    def _person_key(self):
        """The person's own key: --key, else ~/.ssh/lionsberg-person-<handle>. Never an agent's."""
        if not self.actor.startswith("person:"):
            sys.exit("serve.py: the wearer is a person (person:<handle>); an agent's key never signs a person's yes")
        if self.args.key:
            return str(Path(self.args.key).expanduser())
        k = Path.home() / ".ssh" / f"lionsberg-person-{self.actor.split(':', 1)[1]}"
        return str(k) if k.is_file() else None

    # -- setup
    def _types(self):
        t, _ = read_json(ENGINE / "types.json")
        types = as_dict(as_dict(t).get("types"))
        # a home-only type (a `study`) is written to the person's own home whatever view is open
        self.home_only = {k for k, v in types.items() if as_dict(v).get("home_only")}
        return {k: bool(as_dict(v).get("human_only")) for k, v in types.items()}

    def _keeper(self):
        k = self.holons.info(self.hq).get("keeper")
        return k if isinstance(k, str) and k.startswith("person:") else None

    def _record_module(self):
        """engine/record.py when present: its append(holon_dir, actor, for_, type, body, links,
        audience, reason, key=...) salts, chains, signs and writes every act. Returns
        ("append", fn), or None when record.py is absent (the paper floor)."""
        path = ENGINE / "record.py"
        if not path.is_file():
            return None
        try:
            spec = importlib.util.spec_from_file_location("player_plus_record", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:   # a broken record.py must not stop the HUD
            print(f"serve.py: record.py did not load ({type(e).__name__}); writing record/<actor>.jsonl itself",
                  file=sys.stderr)
            return None
        if callable(getattr(mod, "append", None)):
            return ("append", mod.append)
        print("serve.py: engine/record.py has no append(); writing at the paper floor", file=sys.stderr)
        return None

    def _mail_module(self):
        """engine/mail.py when present and loadable (the carried store, the gated send), else None."""
        path = ENGINE / "mail.py"
        if not path.is_file():
            return None
        try:
            spec = importlib.util.spec_from_file_location("player_plus_mail", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception as e:   # a broken mail.py must not stop the HUD
            print(f"serve.py: mail.py did not load ({type(e).__name__}); no mail state", file=sys.stderr)
            return None

    def mail_state(self) -> dict:
        """`badges`, `mail` and `transports.mail` for /state, from the carried store (DESIGN-MAIL §10.5).
        The store is pruned first, so a line the forge pull brought is read from the record, once.
        `mail.items` is null while nothing was ever carried, so the page falls back to its own reading."""
        m, hq = self.mail, str(self.hq)
        try:
            m.prune(hq)
            entries = m.carried(hq)
            trust = {}
            if any(e.get("kind") == "line" and not e.get("in_record") for e in entries):
                trust = as_dict(m.fold_with_carried(hq).get("trust"))
            badge = m.badge(hq)
        except Exception as e:
            print(f"serve.py: the carried store could not be read ({type(e).__name__})", file=sys.stderr)
            return {}
        items = []
        for e in entries:
            ln = as_dict(e.get("line"))
            body = as_dict(ln.get("body"))
            items.append({"id": e.get("id"), "message_id": e.get("message_id"), "kind": e.get("kind"),
                          "line_id": ln.get("id") if e.get("kind") == "line" else None,
                          "from_actor": ln.get("actor"), "for": ln.get("for"), "holon": ln.get("holon") or e.get("holon"),
                          "card": body.get("card"), "subject": e.get("subject"),
                          "ts": ln.get("ts") or e.get("received_at"), "received_at": e.get("received_at"),
                          "push": body.get("push"), "push_recomputed": e.get("push_recomputed"),
                          "verified": "bad" if e.get("kind") == "bad" else (e.get("verified") or "unverified"),
                          "trust": trust.get(ln.get("id")) if ln else None, "said": e.get("said"),
                          "carried": e.get("kind") == "prose" or (e.get("kind") == "line" and not e.get("in_record")),
                          "read": bool(e.get("read")), "withdrawn": bool(e.get("withdrawn")),
                          "suspect": e.get("suspect") or [], "prose": e.get("prose"),
                          "proposed_line": e.get("proposed_line"), "carried_by": e.get("carried_by") or []})
        last = max((str(e.get("received_at")) for e in entries if e.get("received_at")), default=None)
        cfg = Path(os.environ.get("LIONSBERG_MAIL_CONFIG") or Path.home() / ".config" / "lionsberg" / "mail.json")
        return {"badges": badge,
                "mail": {"mailboxes": [], "items": items if (self.hq / ".carried").is_dir() else None},
                "transports": {"mail": {"on": cfg.is_file(), "last_read": last}}}

    def write_own(self, typ, body, links=None, holon_dir=None):
        """A line by the person, for the person, in the person's own file in the home holon, written by
        record.append after the person's tap and signed with the person's key (~/.ssh/lionsberg-person-
        <handle>, through ssh-agent). Without the key it is written unsigned, on paper, and the answer
        says why in one sentence. Returns (status, answer)."""
        key, handle = self.key, self.actor.split(":", 1)[1]
        d = Path(holon_dir) if holon_dir else self.hq
        with self.wlock:
            signed, line = False, None
            if self.writer is not None:
                try:
                    out = self.writer[1](str(d), self.actor, self.actor, typ, body, links or {},
                                         "holon", "human", key=key, sign=bool(key))
                    line, signed = out.get("line"), bool(out.get("signed"))
                except Exception as e:
                    print(f"serve.py: record.append refused {typ} ({type(e).__name__}: {e})", file=sys.stderr)
                    return 409, {"refused": f"the record refused the line: {e}"}
            else:
                line = self.make_line(d, {"type": typ, "holon": None, "body": body, "links": links or {}})
                line["sig"] = self._sign(line["id"])
                signed = bool(line["sig"])
                try:
                    append_nofollow(d, ["record", self.actor_file(self.actor)], json.dumps(line, ensure_ascii=False) + "\n")
                except OSError as e:
                    return 409, {"refused": f"the line could not be written: {e}"}
        self.bump()
        out = {"written": True, "id": (line or {}).get("id"), "signed": signed,
               "verified": "signed" if signed else "unsigned"}
        if not signed:
            out["said"] = (f"Your key (~/.ssh/lionsberg-person-{handle}) is not on this computer, so this line "
                           f"is written unsigned, on paper." if not key else
                           f"Your key could not sign (it may need unlocking in ssh-agent), so this line "
                           f"is written unsigned, on paper.")
        return 200, out

    def mail_post(self, path, req):
        """POST /mail/send · /mail/read · /mail/line. Returns (status, answer)."""
        m, hq = self.mail, str(self.hq)
        if m is None:
            return 503, {"refused": "mail is not set up on this computer"}
        if path == "/mail/read":
            ok = m.mark_read(hq, req.get("id"))
            if ok:
                self.bump()
            return (200, {"read": True, "id": req.get("id")}) if ok else (404, {"refused": "that item is not held here"})
        if req.get("confirmed") is not True:
            return 403, {"refused": "this is your own act and needs your own tap"}
        if path == "/mail/send":
            if not req.get("line_id") and isinstance(req.get("pending"), str):   # the act just written
                with self.lock:
                    req = dict(req, line_id=as_dict(self.written.get(req["pending"])).get("line_id"))
            try:
                acct = m.load_account(holon_dir=hq)
                out = m.send_line(hq, req.get("line_id"), req.get("to"), acct, on_the_persons_send=True)
            except m.Refused as e:
                return 403, {"refused": str(e)}
            except Exception as e:
                print(f"serve.py: mail send failed ({type(e).__name__})", file=sys.stderr)
                return 502, {"refused": "The mailbox cannot be reached. Nothing was sent."}
            return 200, {"sent": True, "to": out.get("to"), "line_id": out.get("line"), "said": out.get("said")}
        if path == "/mail/line":
            eid = req.get("id")
            entry = next((e for e in m.carried(hq) if e.get("kind") == "prose" and e.get("id") == eid), None)
            prop = as_dict(as_dict(entry).get("proposed_line"))
            if not entry or not prop:
                return 404, {"refused": "that proposal is not held here"}
            typ = req.get("type") or "say"   # the person's tap names the type; a carried mail never does
            if typ not in MAIL_LINE_TYPES:
                return 400, {"refused": "a mail becomes only a said line here"}
            pb = as_dict(prop.get("body"))
            body = {k: pb[k] for k in ("text", "source_mail") if isinstance(pb.get(k), str) and pb[k]}
            if not body.get("text"):
                return 404, {"refused": "that proposal has no words to keep"}
            s, out = self.write_own(typ, body)
            if s == 200:
                try:
                    os.unlink(entry["_path"])
                except OSError:
                    pass
                self.bump()
            return s, out
        return 404, {"refused": "not here"}

    def agents_signature(self):
        """Each agent's state and open asks, so the HUD's top line follows the agent host."""
        if not (self.hq / ".agent-host").exists():
            return ()
        s, st = self.bridge.call("GET", "/status", timeout=0.5)
        if s != 200:
            return ("down",)
        return tuple((a.get("id"), a.get("state"), a.get("asks_open")) for a in as_list(as_dict(st).get("agents")))

    def bump(self):
        with self.cond:
            self.version += 1
            self.cond.notify_all()

    # -- GET /state
    def state(self) -> dict:
        home_lines = read_record(self.hq)
        if self.fixture is not None:
            # a fixture's acts land under cells/<holon id> (see _holon_dir), so its layout
            # events (the dock's open or collapsed among them) are read from there too
            for d in self.holons.dirs()[1:]:
                home_lines += read_record(d)
        if self.fixture is not None:
            st = json.loads(json.dumps(self.fixture))
            hud = st.setdefault("hud", {})
            hud["mode"] = "fixture"
            hud["layouts"] = as_list(hud.get("layouts")) + fold_layouts(home_lines)
        else:
            parts, sources = [], []
            for d in self.holons.dirs():
                info = self.holons.info(d)
                st, why = read_json(d / "state.json")
                heard = None
                try:
                    heard = datetime.fromtimestamp((d / "state.json").stat().st_mtime).astimezone().isoformat(timespec="seconds")
                except OSError:
                    pass
                rel = "." if d == self.hq else str(d.relative_to(self.hq))
                sources.append({"holon": info.get("id"), "name": info.get("name") or d.name, "path": rel,
                                "readable": True if isinstance(st, dict) else why, "heard": heard,
                                "missing": why == "no saved state yet"})
                if isinstance(st, dict):
                    parts.append(st)
            # a cell with no state.json of its own is still read when the home's fold covers it
            folded = {as_dict(x).get("id") for p in parts for x in as_list(p.get("holons"))}
            for src in sources:
                if src.pop("missing") and src["holon"] in folded:
                    src["readable"] = True
                    src["heard"] = sources[0]["heard"] if sources else None
            st = merge_states(parts)
            # a home just adopted has no saved state until the engine first runs: its holons are
            # still held here, so the page can write to its own record (the layout among them)
            # and The Deal can say the record is new rather than that the agent failed
            held = {as_dict(x).get("id") for x in as_list(st.get("holons"))}
            for d in self.holons.dirs():
                info = self.holons.info(d)
                if isinstance(info.get("id"), str) and info["id"] not in held:
                    st.setdefault("holons", []).append({k: info.get(k) for k in ("id", "name", "kind", "keeper")})
            hud = st.setdefault("hud", {})
            hud.update(mode="live", sources=sources, layouts=fold_layouts(home_lines))
            hud["now"] = None
            hud["fresh"] = not parts
            hud["record_newer"] = self.record_newer()
        if self.mail is not None and "mail" not in st:   # the carried store (engine/mail.py)
            ms = self.mail_state()
            st.setdefault("transports", {}).update(ms.pop("transports", {}))
            st.update(ms)
        hud["talk"] = self.talk.all()   # the open rooms' said lines (DESIGN-ROOM §8.2), never the record
        hud["presence"] = self.talk.presence_all()   # {room: the /presence answer}, so views need no extra call
        hud.update(v=1, served_at=now_iso(), undo_ms=UNDO_MS, actor=self.actor,
                   writes_to=str(self.hq), signer="the person's own key" if self.key else "none (the paper floor)",
                   record_layer=("engine/record.py " + self.writer[0]) if self.writer else "record/<actor>.jsonl")
        # a fixture carries its own (or none: the offline state), unless --bg names a real folder of
        # bodies: then this machine's own reading rides beside the sample, and the sample's folded
        # bodies and desk step aside so the view shows the machine, never a mix of the two
        if self.fixture is None or self.args.bg:
            if self.fixture is not None:
                st.pop("bodies", None)
                st.pop("desk", None)
            try:                        # read live, never written to the record
                hud["bodies_live"] = self.bodies.read()
            except Exception as e:      # the bodies' live fields never stop The Deal
                print(f"serve.py: the bodies could not be read ({type(e).__name__})", file=sys.stderr)
            try:                        # a handoff waiting is one Deal card (DESIGN-BODIES §3.3), folded
                fold_handoffs(st, hud.get("bodies_live"), self.bg_dir(), home_lines, self.actor,
                              self.home_holon(), self.words)   # before the person's own acts are
            except Exception as e:
                print(f"serve.py: the handoffs could not be folded ({type(e).__name__}: {e})", file=sys.stderr)
        with self.lock:
            hud["pending"] = [{"pending": pid, "type": p["req"]["type"], "holon": p["req"]["holon"],
                               "writes_at": p["writes_at"]} for pid, p in self.pending.items()]
            own = list(self.own) + [p["req"] for p in self.pending.values()]
        # one truth: the person's own acts, held and written, folded in at once (and, in fixture
        # mode, the acts already in the scratch home's record from an earlier run)
        if self.fixture is not None:
            own = [{"type": l.get("type"), "links": l.get("links"), "body": l.get("body")}
                   for l in home_lines if isinstance(l, dict) and l.get("actor") == self.actor] + own
        fold_own(st, own, self.actor)
        st.setdefault("actor", self.actor)
        # the person's keepsakes (proposal, DESIGN-TALK.md): their own home-only `keepsake`
        # lines, oldest first, so the Talk's marks live in their record and follow them to every device
        hud["keepsakes"] = [dict({k: as_dict(l.get("body")).get(k) for k in ("card", "title", "name", "mark")
                                  if isinstance(as_dict(l.get("body")).get(k), str)}, at=l.get("ts"))
                            for l in home_lines if isinstance(l, dict) and l.get("type") == "keepsake"
                            and l.get("actor") == self.actor][-60:]
        try:                            # the person's name and who brought them, for the welcome
            hud.setdefault("person", self.person(st))
        except Exception as e:          # never stops The Deal; the Talk then says "Good morning." alone
            print(f"serve.py: the person's name could not be read ({type(e).__name__})", file=sys.stderr)
        try:
            hud.update(self.bridge.hud_block(home_lines))
        except Exception as e:   # the dock's fields never stop The Deal
            print(f"serve.py: the dock's state could not be read ({type(e).__name__})", file=sys.stderr)
        hud["phone"] = self.phone.block()
        try:                            # what each body started from the ICE spent today
            for a in as_list(hud.get("agents")):
                b = as_dict(as_dict(a).get("body"))
                if b:
                    b["spent_today"] = self.bodies.spent(b.get("session"), b.get("cwd"))
        except Exception as e:
            print(f"serve.py: what the hosted bodies spent could not be read ({type(e).__name__})", file=sys.stderr)
        return st

    # -- the person: name, handle, and who brought them (the Talk's welcome, the dock's About sheet)
    def person(self, st) -> dict:
        """{name, handle, brought_by}. `name`: the person's own entry among the actors when it names
        them, else a `join` line that names them (never the inception line, whose name is the
        house's), else the home's holon.json `keeper_name` when the person keeps it; else null.
        `brought_by` {name, house, reach}: the one who admitted the person (the actor of a join whose
        body.who is the person), else the witness of the person's own join; `house` the name of the
        holon the join was written in; `reach` a mailto: or https: address from that actor's
        join/affirm line, else null. Fixture mode reads the same from the fixture's actors and
        holons: the person's entry may carry `joined: {witness, holon}`, the witness's its `reach`."""
        me = self.actor
        handle = me.split(":", 1)[1] if ":" in me else me
        actors = {a["id"]: a for a in as_list(st.get("actors")) if isinstance(a, dict) and isinstance(a.get("id"), str)}
        houses = {h["id"]: h.get("name") for h in as_list(st.get("holons")) if isinstance(h, dict) and isinstance(h.get("id"), str)}
        clean = lambda v: v.strip()[:80] if isinstance(v, str) and v.strip() else None
        reachable = lambda v: next((x.strip()[:200] for x in (v if isinstance(v, list) else [v])
                                    if isinstance(x, str) and x.strip().lower().startswith(("mailto:", "https://"))), None)
        name = clean(as_dict(actors.get(me)).get("name"))
        sender, house, names, reach = None, None, {}, {}
        if self.fixture is not None:
            j = as_dict(as_dict(actors.get(me)).get("joined"))
            if isinstance(j.get("witness"), str):
                sender, house = j["witness"], clean(houses.get(j.get("holon")))
        else:
            admitted = witnessed = None
            for ln, hname in self._joins():
                b, actor, typ = as_dict(ln.get("body")), ln.get("actor"), ln.get("type")
                who = b.get("who") if isinstance(b.get("who"), str) else actor
                if typ == "join" and b.get("role") != "inception" and clean(b.get("name")):
                    names.setdefault(who, clean(b["name"]))
                r = reachable(b.get("reach"))
                if r:
                    reach.setdefault(who, r)
                if typ != "join":
                    continue
                if who == me and isinstance(actor, str) and actor != me and admitted is None:
                    admitted = (actor, hname)
                elif actor == me and isinstance(b.get("witness"), str) and witnessed is None:
                    witnessed = (b["witness"], hname)
            sender, house = admitted or witnessed or (None, None)
            info = self.holons.info(self.hq)
            name = name or names.get(me) or (clean(info.get("keeper_name")) if info.get("keeper") == me else None)
        bb = None
        if sender:
            e = as_dict(actors.get(sender))
            bb = {"name": clean(e.get("name")) or names.get(sender), "house": house,
                  "reach": reachable(e.get("reach")) or reach.get(sender)}
            bb = bb if (bb["name"] or bb["house"] or bb["reach"]) else None
        return {"name": name, "handle": handle, "brought_by": bb}

    def _joins(self):
        """[(join or affirm line, the name of the house it was written in)] across the home and its
        cells; re-read only when a record file changed."""
        files = []
        for d in self.holons.dirs():
            rec = d / "record"
            for f in sorted(rec.glob("*.jsonl")) if rec.is_dir() else []:
                try:
                    stt = f.stat()
                except OSError:
                    continue
                files.append((d, f, stt.st_mtime_ns, stt.st_size))
        key = tuple((str(f), m, z) for _, f, m, z in files)
        cached = getattr(self, "_joins_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        out = []
        for d in dict.fromkeys(d for d, *_ in files):
            hname = self.holons.info(d).get("name")
            out += [(ln, hname if isinstance(hname, str) else None) for ln in read_record(d)
                    if ln.get("type") in ("join", "affirm")]
        self._joins_cache = (key, out)
        return out

    # -- the bodies' handoffs (DESIGN-BODIES §3.3)
    def bg_dir(self) -> Path:
        return Path(self.args.bg).expanduser() if self.args.bg else self.hq / "bg"

    def home_holon(self):
        """The person's own home: the holon this server writes a home act to (fixture: the fixture's
        person holon kept by the wearer, written to the scratch home)."""
        if self.fixture is not None:
            fx = next((as_dict(x) for x in as_list(self.fixture.get("holons"))
                       if as_dict(x).get("kind") == "person" and as_dict(x).get("keeper") == self.actor), {})
            return fx.get("id")
        return self.holons.info(self.hq).get("id")

    def words(self, key, **kw):
        """A line from strings.json (the kit's words), its {slots} filled."""
        if not hasattr(self, "_strings"):
            d, _ = read_json(HERE / "strings.json")
            self._strings = as_dict(d)
        text = str(self._strings.get(key) or key)
        for k, v in kw.items():
            text = text.replace("{" + k + "}", str(v))
        return text

    def handoff_text(self, name):
        """GET /bodies/handoff?body=: the text of a machine body's handoff.md, read-only. Only a body
        that keeps its own folder under bg/, or a worker the host started (its folder under its own
        cwd's bg/, found through the host's /status); never the prime or a window; never through a link (the folder or the file); at most a megabyte."""
        key = str(name or "").strip().casefold()
        if not key:
            return 400, {"refused": "which body? (none was named)"}
        live = self.bodies.read() if (self.fixture is None or self.args.bg) else {}
        hits = [e for e in as_list(as_dict(live).get("machine")) if isinstance(e, dict)
                and key in (str(e.get("name") or "").casefold(), str(e.get("folder") or "").casefold())]
        if not hits:
            w = host_worker_folder(getattr(self, "bridge", None), key)
            if w is None:
                return 404, {"refused": "no body by that name keeps a folder on this machine"}
            return read_handoff(w[0], w[1], w[2])
        e = hits[0]
        if e.get("kind") != "background" or not e.get("folder"):
            return 409, {"refused": "only a body that keeps its own folder leaves a handoff here"}
        return read_handoff(self.bg_dir(), str(e["folder"]), e.get("name"))

    # -- POST /act
    def act(self, req: dict):
        typ = req.get("type")
        if not isinstance(typ, str) or (typ not in self.types and typ != "layout"):
            return 400, {"refused": "that kind of act is not known"}
        audience = req.get("audience") or "holon"
        if audience != "holon":
            return 403, {"refused": "an act stays in its own record; only a publish widens who sees it"}
        if self.types.get(typ) and req.get("confirmed") is not True:
            return 403, {"refused": "this is a person's own act and needs the person's confirmation"}
        if typ == "publish":
            tok = req.get("sheet_token")
            with self.lock:
                ok = tok in self.tokens
                self.tokens.discard(tok)
            if not ok:
                return 403, {"refused": "publishing goes through the publish sheet"}
        holon = req.get("holon")
        dirs = self.holons.by_id()
        if self.fixture is None and not holon:   # the person's own record: the home held here
            holon = self.holons.info(self.hq).get("id")
        if self.fixture is None and holon not in dirs:
            return 404, {"refused": "that record is not held here"}
        if (typ in self.home_only or typ == "layout") and holon and dirs.get(holon) not in (None, self.hq):
            return 409, {"refused": "this act is written only in your own home, never in a cell"}
        body = as_dict(req.get("body"))
        links = {k: [i for i in as_list(v) if isinstance(i, str)]
                 for k, v in as_dict(req.get("links")).items() if k in LINK_KINDS}
        links = {k: v for k, v in links.items() if v}
        hold = req.get("hold_ms")
        hold = UNDO_MS if not isinstance(hold, (int, float)) else max(UNDO_MS, min(UNDO_MAX_MS, int(hold)))
        pid = secrets.token_hex(8)
        writes_at = time.time() + hold / 1000
        clean = {"type": typ, "holon": holon, "body": body, "links": links, "audience": "holon"}
        timer = threading.Timer(hold / 1000, self._write, args=(pid,))
        timer.daemon = True
        with self.lock:
            self.pending[pid] = {"req": clean, "writes_at": datetime.fromtimestamp(writes_at).astimezone().isoformat(timespec="seconds"),
                                 "timer": timer}
        timer.start()
        if typ not in QUIET_TYPES:
            self.bump()
        return 202, {"pending": pid, "writes_at": self.pending[pid]["writes_at"], "undo_ms": hold,
                     "line_id": None, "status_url": f"/act/{pid}"}   # the id exists once the hold has passed

    def act_status(self, pid: str):
        """GET /act/<id>: holding · written (with the line's id) · unknown (undone, or never held here)."""
        with self.lock:
            if pid in self.pending:
                return 200, {"pending": pid, "status": "holding", "line_id": None}
            w = self.written.get(pid)
        if w and w.get("refused"):
            return 409, dict(w, pending=pid, status="refused")
        if w:
            return 200, dict(w, pending=pid, status="written")
        return 404, {"pending": pid, "status": "unknown", "line_id": None}

    def undo(self, pid: str):
        with self.lock:
            p = self.pending.get(pid)
            p = None if (not p or p.get("writing")) else self.pending.pop(pid, None)
        if not p:
            return 410, {"undone": False, "why": "the window has passed; a correction is a new line"}
        p["timer"].cancel()
        self.bump()
        return 200, {"undone": True}

    def publish_token(self):
        tok = secrets.token_hex(12)
        with self.lock:
            self.tokens.add(tok)
        return tok

    # -- writing
    def _holon_dir(self, holon):
        dirs = self.holons.by_id()
        if holon in dirs:
            return dirs[holon]
        # fixture mode: a folder per holon id under the write dir, so acts land somewhere real; the
        # fixture's own home (a person's holon kept by the wearer) is the write dir itself, with its
        # kind kept, so a home-only line (a `study`) is written where record.py allows it
        fx = next((as_dict(x) for x in as_list(as_dict(self.fixture).get("holons")) if as_dict(x).get("id") == holon), {})
        if not holon or (fx.get("kind") == "person" and fx.get("keeper") == self.actor):
            return self._home_dir()
        d = self.hq / "cells" / str(holon)[:16]
        if not (d / "holon.json").exists():
            d.mkdir(parents=True, exist_ok=True)
            (d / "holon.json").write_text(json.dumps({"v": 1, "id": holon, "name": fx.get("name") or "fixture holon",
                                                       "kind": fx.get("kind") or "cell", "keeper": fx.get("keeper") or self.actor}) + "\n", encoding="utf-8")
        return d

    def _home_dir(self):
        """The person's own home: the HQ. In fixture mode the write folder is made a home at the
        paper floor (an unsigned inception line, kind person) the first time a line is written to
        it, so a home-only line lands where record.py allows it (otherwise every
        `study` would be refused, the scratch folder having no inception)."""
        if self.fixture is None:
            return self.hq
        try:
            if str(ENGINE) not in sys.path:
                sys.path.insert(0, str(ENGINE))
            import record as rec
            if rec.holon_kind(str(self.hq)) == "person":
                return self.hq
            import holon as hol
            if not (self.hq / "holon.json").exists():
                hol.init(str(self.hq), "Home", "person", self.actor, sign=False, adopt=True)
        except Exception as e:
            print(f"serve.py: the fixture's write folder could not be made a home ({type(e).__name__}: {e})", file=sys.stderr)
        return self.hq

    @staticmethod
    def actor_file(actor: str) -> str:
        """The record file for an actor, as engine/record.py names it: ':' written as '_'."""
        return "".join(c if (c.isalnum() or c in "-_.+@") else "_" for c in (actor or "unknown")) + ".jsonl"

    def _prev(self, d: Path, actor: str):
        f = d / "record" / self.actor_file(actor)
        try:
            lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
            return json.loads(lines[-1]).get("id") if lines else None
        except (OSError, json.JSONDecodeError, IndexError):
            return None

    def _sign(self, ident: str) -> str:
        if not self.key:
            return ""
        try:
            r = subprocess.run(["ssh-keygen", "-Y", "sign", "-n", "lionsberg-record", "-f",
                                self.key],
                               input=ident.encode(), capture_output=True, timeout=10)
            if r.returncode != 0:
                print("serve.py: signing failed; the line is written unsigned", file=sys.stderr)
                return ""
            armored = r.stdout.decode().strip().splitlines()
            b64 = "".join(l for l in armored if not l.startswith("-----"))
            return "ssh-ed25519:" + b64
        except (OSError, subprocess.SubprocessError):
            print("serve.py: ssh-keygen unavailable; the line is written unsigned", file=sys.stderr)
            return ""

    def make_line(self, d: Path, req: dict) -> dict:
        """The paper floor, used only when engine/record.py is absent: the same salted
        shape record.py writes (one body_salt; each body field, actor and for hashed
        through its own derived salt), so the line can still be elided in an export."""
        sha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
        cj = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        salt = secrets.token_hex(16)
        body = {k: v for k, v in req["body"].items() if v is not None and v != "" and v != [] and v != {}}
        body["body_salt"] = salt
        obj = {"v": 1, "ts": now_iso(), "actor": self.actor, "for": self.actor,
               "holon": str(self.holons.info(d).get("id") or req.get("holon") or ""),
               "type": req["type"], "body": body, "links": req["links"], "audience": "holon",
               "reason": "human", "prev": self._prev(d, self.actor) or ""}

        def dig(name, value):
            fs = sha(salt + "\x00" + name)
            return {"elided": sha(fs + (value if isinstance(value, str) else cj(value)))}
        canon = dict(obj)
        canon["body"] = {k: dig(k, v) for k, v in body.items() if k != "body_salt"}
        for k in ("actor", "for"):
            canon[k] = dig("@" + k, obj[k])
        obj["id"] = sha(cj(canon))
        obj["sig"] = ""   # signed in _write_locked, once the undo window has passed
        return {k: obj[k] for k in LINE_ORDER if k in obj}

    def _write(self, pid: str):
        # the act stays pending (its status "holding") until its line is written and recorded, so a
        # status read in the instant between the hold's end and the write never answers "unknown"
        with self.lock:
            p = self.pending.get(pid)
            if p:
                p["writing"] = True
        if not p:
            return
        with self.wlock:
            try:
                line = self._write_locked(p["req"])
            except OSError as e:
                line = {"refused": f"the line could not be written: {e}"}
            except Exception as e:   # never left pending for ever
                line = {"refused": f"the line could not be written ({type(e).__name__})"}
        if line.get("refused"):
            with self.lock:
                self.written[pid] = {"line_id": None, "refused": line["refused"]}
                self.pending.pop(pid, None)
            if p["req"].get("type") not in QUIET_TYPES:
                self.bump()
            return
        with self.lock:
            self.written[pid] = {"line_id": line.get("id"), "type": line.get("type"), "signed": bool(line.get("sig"))}
            self.pending.pop(pid, None)
            self.own.append(p["req"])
            del self.own[:-500]
            while len(self.written) > 500:
                self.written.pop(next(iter(self.written)))

    def _sig(self):
        """The watch's fingerprint: the holons' files, the agents' states, the said lines."""
        return self.holons.signature() + (self.agents_signature(), self.talk.signature())

    def _write_locked(self, req: dict):
        if req.get("type") in QUIET_TYPES:
            # the watch is told of this one change, so it neither wakes /stream nor redraws a page
            pre = self._sig()
            line = self._write_line(req)
            if not line.get("refused"):
                self.quiet_pairs.append((pre, self._sig()))
                del self.quiet_pairs[:-20]
            return line
        return self._write_line(req)

    def _write_line(self, req: dict):
        d = self._home_dir() if req.get("type") in getattr(self, "home_only", set()) else self._holon_dir(req.get("holon"))
        line = self.make_line(d, req)
        written = False
        if self.writer is not None:
            kind, fn = self.writer
            try:
                if kind == "append":
                    out = fn(str(d), self.actor, self.actor, req["type"], req["body"], req["links"],
                             "holon", "human", key=self.key, sign=bool(self.key))
                    line = out.get("line", line) if isinstance(out, dict) else line
                    if not self.key:
                        print("serve.py: no key of the person's own (~/.ssh/lionsberg-person-<handle> or --key); "
                              "the line is written unsigned, at the paper floor", file=sys.stderr)
                    elif isinstance(out, dict) and out.get("said"):
                        print(f"serve.py: {out['said']}", file=sys.stderr)
                written = True
            except Exception as e:   # a refusal is a refusal: nothing is written another way
                print(f"serve.py: record.{kind} refused the line ({type(e).__name__}: {e})", file=sys.stderr)
                return {"refused": f"the record refused the line: {e}"}
        if not written:   # only when record.py is absent: the paper floor, never through a link
            line["sig"] = self._sign(line["id"])
            append_nofollow(d, ["record", self.actor_file(self.actor)], json.dumps(line, ensure_ascii=False) + "\n")
        print(f"serve.py: wrote {line['type']} {line['id'][:8]} to {d}", file=sys.stderr)
        if req.get("type") not in QUIET_TYPES:
            self.bump()
        return line

    def record_newer(self):
        """The newest record line written after the home's state.json was folded: {ts, by_agent},
        or None. While it stands, the state is being refolded and the Deal says so, never
        "nothing is dealt" beside a margin that says a line is in the record."""
        try:
            folded = (self.hq / "state.json").stat().st_mtime
        except OSError:
            folded = 0
        newest, by = 0, None
        for d in self.holons.dirs():
            rec = d / "record"
            if not rec.is_dir():
                continue
            for f in rec.glob("*.jsonl"):
                try:
                    m = f.stat().st_mtime
                except OSError:
                    continue
                if m > newest:
                    newest, by = m, f.name
        if newest <= folded:
            return None
        return {"ts": datetime.fromtimestamp(newest).astimezone().isoformat(timespec="seconds"),
                "by_agent": bool(by and by.startswith("agent"))}

    def refold(self, quiet=False):
        """Run the engine's fold (engine.py state) once the record has moved past state.json, one at
        a time: it writes state.json, the watch sees it and streams the new state to every view."""
        if self.fixture is not None or getattr(self, "_refolding", False):
            return
        eng = HERE.parent / "engine" / "engine.py"
        if not eng.exists():
            return
        self._refolding = True
        def run():
            pre = self._sig() if quiet else None
            try:
                subprocess.run([sys.executable, "-I", str(eng), "state", str(self.hq), "--actor", self.actor],
                               capture_output=True, text=True, timeout=120, cwd=str(self.hq))
            except (OSError, subprocess.SubprocessError) as e:
                print(f"serve.py: the refold did not run ({type(e).__name__})", file=sys.stderr)
            finally:
                self._refolding = False
                if quiet:            # a fold made only for a quiet line: the watch lets its state.json pass
                    self.quiet_pairs.append((pre, self._sig()))
                    del self.quiet_pairs[:-20]
                else:
                    self.bump()
        threading.Thread(target=run, daemon=True).start()

    def watch(self):
        last = self._sig()
        while True:
            time.sleep(1)
            sig = self._sig()
            if sig != last:
                quiet = (last, sig) in self.quiet_pairs
                if quiet:
                    self.quiet_pairs.remove((last, sig))
                last = sig
                if not quiet:
                    self.bump()
                if self.fixture is None and self.record_newer():
                    self.refold(quiet)   # a line was written (by the person, the agent, or another body): fold it in


# ------------------------------------------------------------------ the dock's bridge to agent_host.py

NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class AgentBridge:
    """Speaks to agent_host.py on loopback with the page's token. Starts the host, detached, only
    when the player's confirmed word asks for an agent; reads its state for hud.agents."""

    def __init__(self, hub):
        self.hub = hub
        self.lock = threading.Lock()
        self.agents_path = Path(hub.args.agents).expanduser().resolve() if hub.args.agents else hub.hq / "agents.json"
        self._proxy_seen = (0.0, False)
        self.owned = None          # the host's pid, once this server started or adopted it
        why = self.claim()
        if why:
            sys.exit(f"serve.py: {why}")
        atexit.register(self.release)
        if threading.current_thread() is threading.main_thread():
            try:
                prev = signal.getsignal(signal.SIGTERM)
                def on_term(signum, frame):
                    self.release()
                    if callable(prev) and prev not in (signal.SIG_DFL, signal.SIG_IGN):
                        prev(signum, frame)
                    sys.exit(0)
                signal.signal(signal.SIGTERM, on_term)
            except (ValueError, OSError):
                pass

    # -- one host per home, owned by one server (the host outlives no server that started it)
    @staticmethod
    def _alive(pid):
        if not isinstance(pid, int) or pid <= 1:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _entry(self):
        info, _ = read_json(self.hub.hq / ".agent-host")
        return as_dict(info)

    def _write_entry(self, info):
        path = self.hub.hq / ".agent-host"
        try:
            fd = os.open(str(path) + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(json.dumps(info) + "\n")
            os.replace(str(path) + ".tmp", str(path))
        except OSError as e:
            print(f"serve.py: could not write {path} ({e.strerror})", file=sys.stderr)

    def claim(self):
        """At start: a dead entry is cleaned; a live host of another live server is a refusal, in one
        line; a live host whose server is gone (or never named) is adopted, so its conversations go on."""
        path = self.hub.hq / ".agent-host"
        info = self._entry()
        if not info:
            return None
        host = info.get("pid")
        if not self._alive(host):
            try:
                path.unlink()
            except OSError:
                pass
            return None
        srv = as_dict(info.get("server"))
        other = srv.get("pid")
        if other != os.getpid() and self._alive(other):
            return (f"another server (pid {other}, port {srv.get('port')}) holds the agent host for {self.hub.hq}; "
                    "stop it first, or give this one another --hq")
        self.adopt(info)
        return None

    def adopt(self, info=None):
        """Write this server's pid and port beside the host's own, so the host is stopped with it."""
        info = info or self._entry()
        if not self._alive(info.get("pid")):
            return
        info["server"] = {"pid": os.getpid(), "port": getattr(self.hub.args, "port", None)}
        self._write_entry(info)
        self.owned = info.get("pid")

    def release(self):
        """On this server's exit: stop the host it started or adopted (its agents with it), and clear
        the entry. A host another server holds is never touched."""
        pid, self.owned = self.owned, None
        if not pid:
            return
        info = self._entry()
        if info.get("pid") != pid or as_dict(info.get("server")).get("pid") != os.getpid():
            return
        try:
            os.killpg(pid, signal.SIGTERM)      # started in its own session: the host and its agents
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        try:
            (self.hub.hq / ".agent-host").unlink()
        except OSError:
            pass

    def _port(self):
        info, _ = read_json(self.hub.hq / ".agent-host")
        info = as_dict(info)
        pid, port = info.get("pid"), info.get("port")
        if not isinstance(port, int) or not isinstance(pid, int):
            return None
        try:
            os.kill(pid, 0)
        except OSError:
            return None
        return port

    def call(self, method, path, body=None, timeout=3.0):
        port = self._port()
        if not port:
            return None, None
        data = json.dumps(body or {}).encode() if method == "POST" else None
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                     headers={"X-HUD-Token": self.hub.token, "Content-Type": "application/json"})
        try:
            with NO_PROXY.open(req, timeout=timeout) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except (ValueError, OSError):
                return e.code, {"refused": "the host refused"}
        except (OSError, ValueError):
            return None, None

    def ensure(self):
        """The host, started on the player's word if it is not running. True when it answers."""
        with self.lock:
            s, _ = self.call("GET", "/status", timeout=1.0)
            if s == 200:
                return True
            log = self.hub.hq / ".agent-host.log"
            try:
                fh = open(log, "a", encoding="utf-8")
                a = self.hub.args
                subprocess.Popen([sys.executable, str(HERE / "agent_host.py"), "--hq", str(self.hub.hq),
                                  "--agents", str(self.agents_path), "--person", self.hub.actor]
                                 + (["--ask-wait", str(a.ask_wait)] if a.ask_wait else [])
                                 # the trust layer reads the same harness files the Bodies place reads
                                 + [x for k, flag in (("usage_file", "--usage-file"), ("cost_ledger", "--cost-ledger"),
                                                      ("routes", "--routes"), ("vendors", "--vendors"))
                                    if getattr(a, k, None) for x in (flag, str(getattr(a, k)))],
                                 stdin=subprocess.DEVNULL, stdout=fh, stderr=fh, start_new_session=True, cwd=str(self.hub.hq))
            except OSError as e:
                print(f"serve.py: the agent host could not start ({e.strerror})", file=sys.stderr)
                return False
            for _ in range(40):
                time.sleep(0.1)
                s, _ = self.call("GET", "/status", timeout=0.5)
                if s == 200:
                    self.adopt()        # started by this server: stopped with it
                    return True
            return False

    def registry(self):
        info, _ = read_json(self.agents_path)
        return [a for a in as_list(as_dict(info).get("agents")) if isinstance(a, dict) and isinstance(a.get("id"), str)]

    def proxy_up(self):
        """Whether the proxy answers its /health with its own token (<hq>/.proxy-token); asked at most every ten seconds."""
        at, up = self._proxy_seen
        if time.time() - at < 10:
            return up
        up = False
        tok = None
        try:
            tok = (self.hub.hq / ".proxy-token").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        if tok:
            req = urllib.request.Request(self.hub.args.proxy.rstrip("/") + "/health", headers={"X-Proxy-Token": tok})
            try:
                with NO_PROXY.open(req, timeout=0.4) as r:
                    up = r.status == 200
            except (OSError, ValueError):
                up = False
        self._proxy_seen = (time.time(), up)
        return up

    def hud_block(self, home_lines):
        s, st = self.call("GET", "/status", timeout=0.6)
        host = s == 200
        routes = [l for l in home_lines if l.get("type") == "route"]
        last_heard = max((str(l.get("ts")) for l in routes), default=None)
        if host:
            agents = as_list(as_dict(st).get("agents"))
            convs = as_list(as_dict(st).get("conversations"))
        else:
            agents = [{"id": a["id"], "name": a.get("name") or None, "of": a.get("of") or self.hub.actor,
                       "kind": a.get("kind") or "harness", "state": "asleep", "declared": {}, "modes": [],
                       "mode": None, "asks_open": 0, "asks_last_15m": 0, "proxy_declared": bool(a.get("proxy")),
                       "discern_offered": False, "conversation": None, "installed": True,
                       "figures": None, "clock": None} for a in self.registry()]
            convs = []
        up = None
        for a in agents:
            if a.get("proxy_declared"):
                up = self.proxy_up() if up is None else up
            a["proxy"] = {"on": bool(a.get("proxy_declared") and up), "last_heard": last_heard}
        return {"agents": agents, "dock": {"host": host, "conversations": convs,
                                           "rung": 1 if agents else None,
                                           "epoch": as_dict(st).get("epoch") if host else None}}

    # -- the routes of one turn: where each request went, never a body
    def routes_of(self, conversation, turn):
        s, w = self.call("GET", f"/turn?conversation={quote(str(conversation))}&turn={quote(str(turn))}", timeout=1.0)
        if s != 200:
            return s or 409, {"refused": "that turn is not held here"}
        start, end = w.get("start"), w.get("end")
        try:
            t0 = datetime.fromisoformat(start).timestamp() - 1
            t1 = datetime.fromisoformat(end).timestamp() + 2
        except (TypeError, ValueError):
            return 400, {"refused": "that turn has no time"}
        lines = read_record(self.hub.hq)
        log = self.hub.hq / "proxy-log.jsonl"
        try:
            for raw in log.read_text(encoding="utf-8").splitlines():
                try:
                    lines.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
        places = self.places()
        out = []
        for ln in lines:
            if not isinstance(ln, dict) or ln.get("type") != "route":
                continue
            try:
                ts = datetime.fromisoformat(str(ln.get("ts"))).timestamp()
            except ValueError:
                continue
            if not (t0 <= ts <= t1):
                continue
            b = as_dict(ln.get("body"))
            tag, rule = str(b.get("tag") or ""), str(b.get("rule") or "")
            out.append({"route": b.get("route_id"), "place": places.get(b.get("vendor"), "elsewhere"),
                        "private": "private" in (tag + " " + rule).lower(), "rule": rule or None,
                        "latency_ms": b.get("latency_ms") if isinstance(b.get("latency_ms"), int) else None,
                        "ok": isinstance(b.get("status"), int) and b["status"] < 400, "at": ln.get("ts")})
        out.sort(key=lambda r: str(r["at"]))
        return 200, {"matched": "time", "routes": out, "turn": turn, "conversation": conversation}

    def places(self):
        """vendor name -> here (a model on this computer) · frontier · elsewhere. The vendors are
        read from the person's own vendors file (--vendors, else ~/.config/lionsberg/vendors.json,
        as the proxy reads them); an older routes.json that still names vendors is read too. A
        vendor not found reads as elsewhere, never as here."""
        vendors = {}
        for path in [Path(self.hub.args.routes).expanduser() if self.hub.args.routes else ENGINE / "routes.json",
                     Path(self.hub.args.vendors).expanduser() if self.hub.args.vendors
                     else Path.home() / ".config" / "lionsberg" / "vendors.json"]:
            cfg, _ = read_json(path)
            vendors.update(as_dict(as_dict(cfg).get("vendors")))
        out = {}
        for name, v in vendors.items():
            host = str(as_dict(v).get("host") or urlparse(str(as_dict(v).get("base_url") or "")).hostname or "")
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == "localhost"
            if local:
                out[name] = "here"
            elif as_dict(v).get("kind") == "anthropic":
                out[name] = "frontier"
            else:
                out[name] = "elsewhere"
        return out

    def discern(self, req):
        """The person's discernment: a `discern` line by the person, for the person, in the person's
        own file in the home holon, written by record.append after the person's tap and signed with
        the person's key (~/.ssh/lionsberg-person-<handle>, through ssh-agent). Without the key the
        line is written unsigned, on paper, and the answer says why in one sentence. The proxy's own
        POST /discern is not used: it writes only an untrusted note by the agent."""
        route = req.get("route")
        if not isinstance(route, str) or not route.strip() or len(route) > 128:
            return 400, {"refused": "a judgment needs the answer it is about"}
        body = {"route_id": route, "verdict": req.get("verdict")}
        if isinstance(req.get("rating"), int) and not isinstance(req.get("rating"), bool):
            body["rating"] = req["rating"]
        if isinstance(req.get("note"), str) and req["note"].strip():
            body["note"] = req["note"][:2000]
        return self.hub.write_own("discern", body)


# ------------------------------------------------------------------ the phone door

def private_address():
    """The machine's private-network address: the first in 100.64.0.0/10, else a private LAN
    address. Never loopback, link-local, unspecified or public."""
    text = ""
    for cmd in (["ifconfig"], ["ip", "-4", "addr"]):
        try:
            text = subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
            if text:
                break
        except (OSError, subprocess.SubprocessError):
            continue
    cands = []
    for a in re.findall(r"inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)", text):
        try:
            cands.append(ipaddress.ip_address(a))
        except ValueError:
            pass
    cgnat = ipaddress.ip_network("100.64.0.0/10")
    for a in cands:
        if a in cgnat:
            return str(a)
    for a in cands:
        if a.is_private and not a.is_loopback and not a.is_link_local and not a.is_unspecified:
            return str(a)
    return None


def address_allowed(addr):
    try:
        a = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if a.is_unspecified or a.is_loopback or a.is_link_local or a.is_multicast:
        return False
    return a.is_private or a in ipaddress.ip_network("100.64.0.0/10")


class PhoneDoor:
    """The second listener, bound only to the private-network address, on the player's word."""

    def __init__(self, hub):
        self.hub = hub
        self.lock = threading.Lock()
        self.server = None
        self.addr = None
        self.port = hub.args.phone_port or (hub.args.port + 1)      # the door, over TLS
        self.trust_port = self.port + 1                              # the trust page, plain http
        self.plain = None         # the trust page's listener
        self.trust = None         # phone_cert.ensure()'s meta for the bound address
        self.changed = None       # {was, now, at}: the fingerprint changed while this server ran
        self.renewer = None
        self.code = None          # {hash, expires, tries}
        self.path = hub.hq / ".hud-devices"

    def devices(self):
        d, _ = read_json(self.path)
        return as_dict(as_dict(d).get("devices"))

    def _save(self, devs):
        fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"devices": devs}, ensure_ascii=False, indent=1) + "\n")
        os.chmod(str(self.path), 0o600)

    def block(self):
        t = self.trust if self.server else None
        return {"enabled": bool(self.hub.args.phone),
                "listening": f"{self.addr}:{self.port}" if self.server else False,
                "door": f"https://{self.addr}:{self.port}/" if self.server else None,
                "trust_page": f"http://{self.addr}:{self.trust_port}/" if self.server else None,
                "trust": ({"fingerprint": t["fingerprint"], "ca_expires": t["ca_expires"],
                           "leaf_expires": t["leaf_expires"], "changed": self.changed} if t else None),
                "devices": [{"id": k, "name": v.get("name"), "added": v.get("added"), "last_seen": v.get("last_seen")}
                            for k, v in self.devices().items()]}

    def _certs(self, addr):
        """Make or renew this address's certificates (phone_cert.py); a new TLS context on change."""
        import importlib.util as _ilu
        import ssl
        spec = _ilu.spec_from_file_location("phone_cert", HERE / "phone_cert.py")
        pc = _ilu.module_from_spec(spec)
        spec.loader.exec_module(pc)
        meta = pc.ensure(self.hub.hq, addr)
        if "ca" in meta["renewed"] and meta.get("prior_fingerprint"):
            self.changed = {"was": meta["prior_fingerprint"], "now": meta["fingerprint"], "at": now_iso()}
            print("serve.py: the phone door's authority was renewed; its fingerprint changed, and each phone "
                  "must trust this computer again", file=sys.stderr)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(meta["cert"], meta["key"])
        self.trust = meta
        return ctx

    def _renew_beat(self, srv):
        while self.server is srv:
            time.sleep(6 * 3600)
            if self.server is not srv:
                return
            try:
                ctx = self._certs(self.addr)
            except (OSError, ValueError) as e:
                print(f"serve.py: the phone door's certificate could not be renewed ({e})", file=sys.stderr)
                continue
            if self.trust["renewed"]:
                srv.ctx = ctx
                self.hub.bump()

    def ca_der(self):
        try:
            return Path(self.trust["ca_der"]).read_bytes() if self.trust else None
        except OSError:
            return None

    def listen(self, on):
        if not self.hub.args.phone:
            return 403, {"refused": "the phone door is off on this computer; serve.py was started without --phone"}
        with self.lock:
            if not on:
                for srv in (self.server, self.plain):
                    if srv:
                        srv.shutdown()
                        srv.server_close()
                self.server = self.plain = None
                self.code = None
                return 200, {"listening": False}
            if self.server:
                return 200, {"listening": f"{self.addr}:{self.port}"}
            addr = self.hub.args.phone_address or private_address()
            if not addr or not address_allowed(addr):
                return 409, {"refused": "no private-network address was found on this computer"}
            try:
                ctx = self._certs(addr)
            except (OSError, ValueError) as e:
                return 409, {"refused": f"the phone door's certificate could not be made ({e})"}
            try:
                srv = PhoneTLSServer((addr, self.port), PhoneHandler)
            except OSError as e:
                return 409, {"refused": f"the phone door could not open ({e.strerror})"}
            try:
                plain = QuietServer((addr, self.trust_port), PhoneTrustHandler)
            except OSError as e:
                srv.server_close()
                return 409, {"refused": f"the phone door's trust page could not open ({e.strerror})"}
            srv.ctx = ctx
            for x in (srv, plain):
                x.daemon_threads = True
                x.door = self
            self.server, self.plain, self.addr = srv, plain, addr
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            threading.Thread(target=plain.serve_forever, daemon=True).start()
            self.renewer = threading.Thread(target=self._renew_beat, args=(srv,), daemon=True)
            self.renewer.start()
            print(f"serve.py: the phone door is open at https://{addr}:{self.port}/ ; a phone trusts this computer "
                  f"once at http://{addr}:{self.trust_port}/ (fingerprint {self.trust['fingerprint']})", file=sys.stderr)
        self.hub.bump()
        return 200, {"listening": f"{addr}:{self.port}"}

    def pair(self):
        if not self.server:
            return 409, {"refused": "the phone door is not open"}
        code = f"{secrets.randbelow(10 ** 6):06d}"
        with self.lock:
            self.code = {"hash": hashlib.sha256(code.encode()).hexdigest(), "expires": time.time() + 300, "tries": 0}
        return 200, {"code": code, "address": f"http://{self.addr}:{self.trust_port}/?pair={code}",
                     "door": f"https://{self.addr}:{self.port}/?pair={code}",
                     "fingerprint": (self.trust or {}).get("fingerprint"), "expires_in": 300}

    def claim(self, code, name):
        with self.lock:
            c = self.code
            if not c or time.time() > c["expires"]:
                self.code = None
                return 403, {"refused": "that code has expired; ask the computer for a new one"}
            c["tries"] += 1
            ok = isinstance(code, str) and secrets.compare_digest(hashlib.sha256(code.encode()).hexdigest(), c["hash"])
            if not ok:
                if c["tries"] >= 5:
                    self.code = None
                return 403, {"refused": "that code is not the one on the computer"}
            self.code = None          # one time only
            token = secrets.token_urlsafe(32)
            dev = "d-" + secrets.token_hex(4)
            devs = self.devices()
            devs[dev] = {"hash": hashlib.sha256(token.encode()).hexdigest(),
                         "name": (str(name)[:40] if name else "your phone"), "added": now_iso(), "last_seen": now_iso()}
            self._save(devs)
        self.hub.bump()
        return 200, {"token": token, "device": dev}

    def check(self, token):
        if not token or len(token) > 200:
            return None
        h = hashlib.sha256(token.encode()).hexdigest()
        devs = self.devices()
        for k, v in devs.items():
            if secrets.compare_digest(str(v.get("hash") or ""), h):
                seen = str(v.get("last_seen") or "")
                if seen[:16] != now_iso()[:16]:
                    with self.lock:
                        v["last_seen"] = now_iso()
                        self._save(devs)
                return k
        return None

    def revoke(self, dev):
        with self.lock:
            devs = self.devices()
            if dev not in devs:
                return 404, {"refused": "no such phone"}
            devs.pop(dev)
            self._save(devs)
        self.hub.bump()
        return 200, {"revoked": dev}

    def voice(self, handler, n):
        cmd = self.hub.args.speech
        if not cmd:
            if 0 < n <= 20 * 1024 * 1024:
                handler.rfile.read(n)     # read what was sent, so the refusal arrives whole (over TLS above all)
            return 501, {"refused": "no speech model is set up on this computer"}
        try:
            argv = shlex.split(cmd)
        except ValueError:
            return 501, {"refused": "the speech command could not be read"}
        if n <= 0 or n > 20 * 1024 * 1024:
            return 413, {"refused": "that recording is too long"}
        keep = (parse_qs(urlparse(handler.path).query).get("keep") or [""])[0] == "true"
        d = self.hub.hq / ".voice"
        d.mkdir(exist_ok=True, mode=0o700)
        f = d / (secrets.token_hex(6) + ".audio")
        fd = os.open(str(f), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(handler.rfile.read(n))
        try:
            r = subprocess.run(argv + [str(f)], capture_output=True, text=True, timeout=180)
            words = r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            words = ""
        finally:
            if not keep:
                try:
                    f.unlink()
                except OSError:
                    pass
        if not words:
            return 422, {"refused": "the recording could not be turned into words"}
        return 200, {"text": words[:20000], "kept": keep}


# ------------------------------------------------------------------ the layered voice: her words read aloud

VOICE_TEXT_MAX, VOICE_WAV_MAX, VOICE_WAIT_S = 4000, 20 * 1024 * 1024, 60


def voice_info(args) -> dict:
    """GET /voice/info: whether this server can hear a recording (--speech) and read aloud (--voice)."""
    return {"hear": bool(getattr(args, "speech", None)), "say": bool(getattr(args, "voice", None))}


def render_voice(cmd, text):
    """POST /voice/say under the --voice contract (the header): (200, wav bytes) or (status, {refused}).
    The command is run without a shell, the text its last argument; the WAV it names is read only if
    it is a plain file written after the request began, under 20 MB, RIFF....WAVE, and is deleted."""
    if not cmd:
        return 501, {"refused": "no voice is set up on this computer"}
    words = re.sub(r"\s+", " ", str(text or "")).strip().lstrip("-").strip()[:VOICE_TEXT_MAX]
    if not words:
        return 400, {"refused": "there are no words to read"}
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return 501, {"refused": "the voice command could not be read"}
    began = time.time() - 1
    try:
        r = subprocess.run(argv + [words], capture_output=True, text=True, timeout=VOICE_WAIT_S)
    except (OSError, subprocess.SubprocessError):
        return 422, {"refused": "the words could not be read aloud on this computer"}
    lines = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    if r.returncode != 0 or not lines:
        return 422, {"refused": "the words could not be read aloud on this computer"}
    f = Path(lines[-1])
    try:
        st = os.lstat(f)
        if not stat.S_ISREG(st.st_mode) or st.st_size > VOICE_WAV_MAX or st.st_size < 12 or st.st_mtime < began:
            return 422, {"refused": "the voice did not write a new sound file"}
        with open(f, "rb") as fh:
            data = fh.read(VOICE_WAV_MAX + 1)
    except OSError:
        return 422, {"refused": "the voice did not write a new sound file"}
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return 422, {"refused": "the voice did not write a new sound file"}
    try:
        f.unlink()
    except OSError:
        pass
    return 200, data


# ------------------------------------------------------------------ HTTP

# ------------------------------------------------------------------ the Room's Talk, a live store

class Talk:
    """Said lines for each room held here (DESIGN-ROOM §8.2), kept only on this machine, in the home's
    own store <HQ>/.talk/<room id>/said.jsonl (0600, gitignored, never inside a cell's clone), and
    never in the record until the keeper keeps one as a `settle`. Each row carries an HMAC under
    <HQ>/.talk/.key, so only rows a server of this home received over /say are read or kept; a
    file brought in any other way is not the Talk. Nothing here is written or read through a link.
    Two servers of one home share the store; each one's watch sees the other's writes."""
    KEEP = 500

    def __init__(self, hub):
        self.hub = hub
        self.lock = threading.Lock()
        self._key = None

    def _engine(self):
        if str(ENGINE) not in sys.path:
            sys.path.insert(0, str(ENGINE))
        import record as rec   # noqa: the engine's own reader and fold
        import rooms as rms
        return rec, rms

    def rooms(self) -> dict:
        """{room holon id: folder} for the holons held here whose kind is room (ids as by_id proves them)."""
        return {i: d for i, d in self.hub.holons.by_id().items() if self.hub.holons.info(d).get("kind") == "room"}

    def _store(self) -> Path:
        return self.hub.hq / ".talk"

    def _file(self, room) -> Path:
        return self._store() / str(room) / "said.jsonl"

    def _read_nofollow(self, path: Path) -> str:
        cur = self.hub.hq
        for part in path.relative_to(self.hub.hq).parts[:-1]:
            cur = cur / part
            if cur.is_symlink():
                raise OSError(f"{part} is a link")
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            return fh.read()

    def key(self) -> bytes:
        if self._key is None:
            path = self._store() / ".key"
            try:
                k = self._read_nofollow(path).strip()
            except FileNotFoundError:
                k = secrets.token_hex(32)
                append_nofollow(self.hub.hq, [".talk", ".key"], k + "\n")
                k = self._read_nofollow(path).strip()
            if len(k) < 32:
                raise OSError("the Talk's key is not usable")
            self._key = k.encode()
        return self._key

    def _mac(self, row: dict) -> str:
        body = json.dumps({k: v for k, v in row.items() if k != "mac"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hmac.new(self.key(), body.encode("utf-8"), hashlib.sha256).hexdigest()

    def signature(self) -> tuple:
        sig = []
        for room in self.rooms():
            try:
                st = self._file(room).lstat()
                sig.append((room, st.st_mtime_ns, st.st_size))
            except OSError:
                sig.append((room, 0, 0))
        return tuple(sig)

    def _rows(self, room) -> list:
        """The rows of this home's own store whose HMAC holds; anything else is not the Talk."""
        try:
            raw = self._read_nofollow(self._file(room)).splitlines()
        except OSError:
            return []
        out = []
        for r in raw:
            try:
                o = json.loads(r)
            except json.JSONDecodeError:
                continue
            if isinstance(o, dict) and isinstance(o.get("mac"), str) and hmac.compare_digest(o["mac"], self._mac(o)):
                out.append({k: v for k, v in o.items() if k != "mac"})
        return out

    def said(self, room) -> list:
        if room not in self.rooms():
            return []
        rows = self._rows(room)
        kept = {r["kept"]: {"line": r.get("line"), "by": r.get("by"), "ts": r.get("ts")}
                for r in rows if isinstance(r.get("kept"), str)}
        out = []
        for r in rows:
            if isinstance(r.get("id"), str) and isinstance(r.get("text"), str):
                x = {k: r.get(k) for k in ("id", "by", "for", "ts", "room", "part", "parent", "text") if r.get(k) is not None}
                if r["id"] in kept:
                    x["kept"] = kept[r["id"]]
                out.append(x)
        return out[-self.KEEP:]

    def all(self) -> dict:
        return {room: self.said(room) for room in self.rooms()}

    def counts(self) -> dict:
        return {room: len(self._rows(room)) for room in self.rooms()}

    def since(self, seen: dict):
        """The rows written after `seen` ({room: rows already sent}); returns (new seen, [(room, rows)])."""
        now, out = {}, []
        for room in self.rooms():
            rows = self._rows(room)
            now[room] = len(rows)
            if len(rows) > seen.get(room, 0):
                out.append((room, rows[seen.get(room, 0):]))
        return now, out

    def _append(self, room, row: dict):
        """One row into the home's own store, with its HMAC, never through a link."""
        if not re.fullmatch(r"[0-9a-f]{64}", str(room)):
            raise OSError("not a room id")
        gi = self._store() / ".gitignore"
        if not gi.is_symlink() and not gi.exists():
            append_nofollow(self.hub.hq, [".talk", ".gitignore"], "*\n")
        row = dict(row, mac=self._mac(row))
        append_nofollow(self.hub.hq, [".talk", str(room), "said.jsonl"], json.dumps(row, ensure_ascii=False) + "\n")

    def _room_folds(self):
        """{room id: rooms.py's room} over the fold's trust, or None when the record cannot be read."""
        try:
            rec, rms = self._engine()
            r = rec.read_all(str(self.hub.hq))
            trust = rec.fold(r["lines"], None, r["keepers"]).get("trust") or {}
            holons = [dict(h, kind=self.hub.holons.info(Path(h["dir"])).get("kind")) for h in r["holons"]]
            return rms.rooms(r["lines"], holons, trust=trust)
        except Exception as e:
            print(f"serve.py: presence could not be read ({type(e).__name__}: {e})", file=sys.stderr)
            return None

    @staticmethod
    def _presence_of(room, info):
        info = info or {}
        return {"room": room, "present": info.get("present") or [], "keeper": info.get("keeper"), "as_of": now_iso()}

    def presence(self, room):
        """(status, {room, present: [{actor, kind, for, role}], keeper, as_of}) from rooms.py over the fold's trust."""
        if room not in self.rooms():
            return 404, {"refused": "that room is not held here"}
        folds = self._room_folds()
        if folds is None:
            return 503, {"refused": "who is present could not be read from the record"}
        return 200, self._presence_of(room, folds.get(room))

    def presence_all(self) -> dict:
        """{room: the /presence answer} for every room held here; {} when none is held."""
        held = self.rooms()
        if not held:
            return {}
        folds = self._room_folds() or {}
        return {room: self._presence_of(room, folds.get(room)) for room in held}

    def say(self, req):
        room, text = req.get("room"), req.get("text")
        d = self.rooms().get(room)
        if d is None:
            return 404, {"refused": "that room is not held here"}
        if req.get("confirmed") is not True:
            return 403, {"refused": "a said line is yours and goes only on your own tap"}
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            return 400, {"refused": "nothing to say, or too long for one line"}
        s, pr = self.presence(room)
        if s != 200:
            return s, pr
        if self.hub.actor not in {p.get("actor") for p in pr["present"]}:
            return 403, {"refused": "you are not present in this room, so nothing is said there"}
        row = {"id": secrets.token_hex(12), "by": self.hub.actor, "for": self.hub.actor, "ts": now_iso(),
               "room": room, "text": text}
        for k in ("part", "parent"):
            if isinstance(req.get(k), str) and 0 < len(req[k]) <= 128:
                row[k] = req[k]
        if isinstance(req.get("part"), int) and not isinstance(req.get("part"), bool) and 0 <= req["part"] < 10000:
            row["part"] = req["part"]   # a part may be named by its number
        with self.lock:
            # the same line twice within thirty seconds is one line (DESIGN-ROOM §4.4): a double
            # tap or a retry returns the line already said, and nothing is written twice
            now = datetime.now(timezone.utc)
            for r in reversed(self._rows(room)[-50:]):
                try:
                    age = (now - datetime.fromisoformat(str(r.get("ts")).replace("Z", "+00:00"))).total_seconds()
                except (TypeError, ValueError):
                    continue
                if age < 30 and r.get("by") == row["by"] and r.get("text") == text and r.get("parent") == row.get("parent"):
                    return 200, {"said": r, "repeat": True}
            try:
                self._append(room, row)
            except OSError as e:
                return 409, {"refused": f"the said line could not be kept on this machine: {e}"}
        self.hub.bump()
        return 200, {"said": row}

    def keep(self, req):
        room, sid = req.get("room"), req.get("id")
        d = self.rooms().get(room)
        if d is None:
            return 404, {"refused": "that room is not held here"}
        if req.get("confirmed") is not True:
            return 403, {"refused": "keeping a line is the keeper's own act and needs the keeper's tap"}
        s, pr = self.presence(room)
        if s != 200:
            return s, pr
        if pr.get("keeper") != self.hub.actor:
            return 403, {"refused": "only the room's keeper keeps a said line"}
        with self.lock:
            x = next((r for r in self.said(room) if r.get("id") == sid), None)
            if x is None:
                return 404, {"refused": "that said line is not held here"}
            if x.get("kept"):
                return 409, {"refused": "that line is already kept", "kept": x["kept"]}
            if x.get("by") == self.hub.actor:
                return 403, {"refused": "a line is agreed by someone other than the one who said it"}
            st, out = self.hub.write_own("settle", {"text": x["text"]}, holon_dir=d)
            if st != 200:
                return st, out
            try:
                self._append(room, {"kept": sid, "line": out.get("id"), "by": self.hub.actor, "ts": now_iso()})
            except OSError as e:
                print(f"serve.py: the keep mark was not stored ({e}); the settle is written", file=sys.stderr)
        self.hub.bump()
        return 200, {"kept": sid, "line": out}


# ------------------------------------------------------------------ the bodies, read live

class HarnessRegistry:
    """The vendor harness's own registry of live sessions on this machine (read only):
    <root>/<pid>.json, one per live session (default root ~/.claude/sessions), and beside it
    <pid>.<sha256 of its socket path>.key, the key that session's inbox asks of a sender.
    Only this user's own files are read: the folder and each file must be this user's, not a
    link, and small. Of a record only the fields below are kept. A key is read only by
    `token_for`, for one send, and never kept, logged, printed or answered."""
    FIELDS = ("pid", "sessionId", "cwd", "startedAt", "procStart", "version", "peerProtocol", "peerFeatures",
              "kind", "entrypoint", "messagingSocketPath", "name", "status")
    SOCK_RE = re.compile(r"^(?:/private)?/tmp/cc-socks(?:-\d+)?/\d+(?:-[0-9a-f]{8})?\.sock$")
    TTL = 2.0
    CAP = 65536

    def __init__(self, root=None):
        self.root = Path(root).expanduser() if root else Path.home() / ".claude" / "sessions"
        self._lock = threading.Lock()
        self._cache = (0.0, None)

    @staticmethod
    def _mine(st) -> bool:
        import stat as _st
        return _st.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and st.st_size <= HarnessRegistry.CAP

    def _root_ok(self) -> bool:
        import stat as _st
        try:
            st = os.lstat(self.root)
        except OSError:
            return False
        return _st.S_ISDIR(st.st_mode) and st.st_uid == os.getuid()

    def _read_small(self, path: Path):
        """A file's text, refused when it is a link, another user's, or large."""
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return None
        try:
            if not self._mine(os.fstat(fd)):
                return None
            return os.read(fd, self.CAP + 1).decode("utf-8", errors="replace")
        except OSError:
            return None
        finally:
            os.close(fd)

    def entries(self) -> dict:
        """{pid: record} for every registry record whose pid is this machine's live process."""
        now = time.time()
        with self._lock:
            at, cached = self._cache
            if cached is not None and now - at < self.TTL:
                return cached
        out = {}
        if self._root_ok():
            try:
                names = os.listdir(self.root)
            except OSError:
                names = []
            for nm in names:
                m = re.match(r"^(\d+)\.json$", nm)
                if not m:
                    continue
                text = self._read_small(self.root / nm)
                try:
                    d = json.loads(text) if text else None
                except ValueError:
                    d = None
                if not isinstance(d, dict) or d.get("pid") != int(m.group(1)):
                    continue
                pid = int(m.group(1))
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    continue                # a record its process left behind
                except PermissionError:
                    continue                # another user's process: never ours
                out[pid] = {k: d.get(k) for k in self.FIELDS if k in d}
        with self._lock:
            self._cache = (now, out)
        return out

    def socket_of(self, rec: dict):
        """The record's socket path when it has the harness's own shape and is this user's socket."""
        import stat as _st
        sp = str(as_dict(rec).get("messagingSocketPath") or "")
        if not self.SOCK_RE.match(sp):
            return None
        try:
            st = os.lstat(sp)
        except OSError:
            return None
        return sp if _st.S_ISSOCK(st.st_mode) and st.st_uid == os.getuid() else None

    def key_file(self, rec: dict):
        sp = self.socket_of(rec)
        if not sp:
            return None
        h = hashlib.sha256(os.path.abspath(sp).encode("utf-8")).hexdigest()
        f = self.root / f"{int(rec['pid'])}.{h}.key"
        try:
            return f if self._mine(os.lstat(f)) else None
        except OSError:
            return None

    def token_for(self, rec: dict):
        """The peer token from the session's key file: for one send, never kept."""
        f = self.key_file(rec)
        text = self._read_small(f) if f else None
        try:
            tok = as_dict(json.loads(text)).get("peerToken") if text else None
        except ValueError:
            tok = None
        return tok if isinstance(tok, str) and re.match(r"^[0-9a-f]{32}$", tok) else None


TOOL_VERBS = {"Read": "Read", "Edit": "Edited", "Write": "Wrote", "NotebookEdit": "Edited", "MultiEdit": "Edited"}


def tool_row(name, inp) -> str:
    """A tool use, said in a few words: the file's name for a file tool, never a command's words."""
    name = str(name or "a tool")
    inp = as_dict(inp)
    if name in TOOL_VERBS:
        f = str(inp.get("file_path") or inp.get("notebook_path") or "")
        return f"{TOOL_VERBS[name]} {os.path.basename(f)}" if f else TOOL_VERBS[name] + " a file"
    if name in ("Bash", "PowerShell"):
        return "Ran a command"
    if name in ("Grep", "Glob", "ToolSearch"):
        return "Searched"
    if name in ("Agent", "Task"):
        return "Started a helper"
    if name in ("WebFetch", "WebSearch"):
        return "Read the web"
    if name == "SendMessage":
        return "Sent a message to another body"
    if name.startswith("mcp__"):
        return "Used " + name.split("__")[-1].replace("_", " ")
    return "Used " + name


class TranscriptReader:
    """One session transcript (the harness's <sessionId>.jsonl), read forward from its start and
    followed as it grows. Each line is one record; `n` is its index. Said: the person's lines
    (`user`, and a peer's message as `user` with `from`), the body's text (`agent`), each tool
    use as a short row (`tool`), and thinking only as `state: thinking`. Never sent: thinking's
    words, tool results, the harness's own meta lines, a helper's side lines. Nothing is written."""
    MAX_TEXT = 4000

    def __init__(self, path: Path):
        self.path = Path(path)
        self.pos = 0
        self.n = 0
        self.turn = None
        self._part = b""

    def _open(self):
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        st = os.fstat(fd)
        import stat as _st
        if not _st.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            os.close(fd)
            raise PermissionError("not this user's own transcript")
        return os.fdopen(fd, "rb")

    def read_new(self, since=0, cap=1 << 22) -> list:
        """The events of the lines appended since the last read (the first read starts at the top)."""
        out = []
        with self._open() as fh:
            size = os.fstat(fh.fileno()).st_size
            if size < self.pos:                         # the file was replaced: start again
                self.pos, self.n, self._part, self.turn = 0, 0, b"", None
            fh.seek(self.pos)
            while True:
                chunk = fh.read(cap)
                if not chunk:
                    break
                self.pos += len(chunk)
                buf = self._part + chunk
                lines = buf.split(b"\n")
                self._part = lines.pop()
                for raw in lines:
                    n = self.n
                    self.n += 1
                    evs = self.events(raw, n)
                    if n >= since:
                        out.extend(evs)
        return out

    def events(self, raw: bytes, n: int) -> list:
        if b'"user"' not in raw and b'"assistant"' not in raw:
            return []
        try:
            d = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(d, dict) or d.get("isSidechain"):
            return []
        typ, ts = d.get("type"), d.get("timestamp")
        msg = as_dict(d.get("message"))
        content = msg.get("content")
        short = lambda s: s if len(s) <= self.MAX_TEXT else s[:self.MAX_TEXT] + "…"
        ev = lambda kind, text, **kw: dict({"n": n, "ts": ts, "kind": kind, "text": text, "turn": self.turn}, **kw)
        if typ == "user":
            origin = as_dict(d.get("origin"))
            if d.get("isMeta"):
                if origin.get("kind") != "peer":
                    return []                           # the harness's own lines (reminders, images, resumes)
                body = origin.get("body")
                if not isinstance(body, str):
                    body = content if isinstance(content, str) else ""
                    m = re.search(r"<cross-session-message[^>]*>\n([\s\S]*?)\n</cross-session-message>", body)
                    body = m.group(1) if m else body
                self.turn = n
                who = origin.get("name") or origin.get("from") or "another session"
                return [ev("user", short(body.strip()), **{"from": str(who)[:80]})]
            if origin.get("kind") == "task-notification":
                return [ev("state", "a helper reported back")]
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    return []                           # tool results are never sent
                text = "\n".join(str(b.get("text") or "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            else:
                return []
            text = text.strip()
            if not text or text.startswith("<system-reminder>") or text.startswith("<local-command-"):
                return []
            self.turn = n
            return [ev("user", short(text))]
        if typ == "assistant" and isinstance(content, list):
            out = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and str(b.get("text") or "").strip():
                    out.append(ev("agent", short(str(b["text"]).strip())))
                elif bt == "tool_use":
                    out.append(ev("tool", tool_row(b.get("name"), b.get("input"))))
                elif bt in ("thinking", "redacted_thinking"):
                    out.append(ev("state", "thinking"))
            return out
        return []


class BodyTalk:
    """GET /bodies/talk, POST /bodies/talk, POST /bodies/window, GET /bodies/reach (DESIGN-BODIES,
    the room). A terminal body is a live harness session the person started; this talks with the
    session itself, never a copy.

    READ, only this user's own files: the harness's sessions registry (HarnessRegistry), and the
    one transcript the chosen body's registry record names (<sessions>/<slug of its cwd>/
    <sessionId>.jsonl). Never read: any other transcript, another user's files, a helper's
    words, thinking's words, tool results, the environment.
    WRITTEN: nothing on disk. The one act that leaves this server is the person's own tap:
    POST /bodies/talk sends one message to that session's own inbox socket, as the harness's
    sessions send to one another (newline-delimited JSON on the socket the record names: an
    `auth` line with the session's key, then one `user` line), after confirming that the process
    listening is the body's own. The key is read into memory for that one send and never kept,
    logged, printed or answered. POST /bodies/window raises that body's own window, and no other."""
    MAX_TEXT = 8000
    GAP_S = 1.0          # at most one message a second to a body (its inbox drops a burst)
    LABEL = "the ICE"
    PREFIX = ""    # the person asked for no visible label; the harness's sender name "the ICE" tells a body where the line came from

    def __init__(self, hub):
        self.hub = hub
        self._last = {}
        self._lock = threading.Lock()

    @property
    def registry(self) -> HarnessRegistry:
        return self.hub.bodies.registry

    def find(self, name):
        """(machine entry, registry record) for a body name, or (None, why in plain words)."""
        key = str(name or "").strip().casefold()
        if not key:
            return None, "which body? (none was named)"
        machine = as_list(self.hub.bodies.read().get("machine"))
        hits = [e for e in machine if isinstance(e, dict) and key in (str(e.get("name") or "").casefold(),
                                                                       str(e.get("folder") or "").casefold())]
        if not hits:
            return None, "no body by that name is on this machine"
        live = [e for e in hits if e.get("alive") and e.get("pid")]
        if not live:
            return None, "that body is not running now"
        if len(live) > 1:
            return None, "more than one body answers to that name"
        e = live[0]
        rec = self.registry.entries().get(e["pid"])
        if not rec:
            return e, None
        return e, rec

    def transcript_of(self, rec: dict):
        sid = str(as_dict(rec).get("sessionId") or "")
        cwd = str(as_dict(rec).get("cwd") or "")
        if not UUID_RE.match(sid) or not cwd.startswith("/"):
            return None
        root = getattr(self.hub.args, "sessions", None)
        root = Path(root).expanduser() if root else Path.home() / ".claude" / "projects"
        d = root / re.sub(r"[^A-Za-z0-9]", "-", cwd)
        try:
            if os.path.islink(d) or not d.is_dir():
                return None
        except OSError:
            return None
        return d / f"{sid}.jsonl"

    def reach(self, name):
        e, rec = self.find(name)
        if e is None:
            return 404, {"reachable": False, "how": "none", "window": False, "status": None, "why": rec}
        out = {"body": e.get("name"), "window": bool(e.get("window")), "status": e.get("status"),
               "session_id": e.get("session_id")}
        if rec is None:
            return 200, dict(out, reachable=False, how="none",
                             why="the harness has no record of that session, so it cannot be reached from here")
        why = None
        if rec.get("peerProtocol") != 1:
            why = "that session speaks a messaging version this page does not know"
        elif not self.registry.socket_of(rec):
            why = "that session has no inbox open on this machine"
        elif not self.registry.key_file(rec):
            why = "that session's inbox key is not here"
        if why:
            return 200, dict(out, reachable=False, how="none", why=why)
        return 200, dict(out, reachable=True, how="socket")

    @staticmethod
    def _peer_pid(s):
        """The pid of the process listening on a connected unix socket, or None."""
        try:
            if sys.platform == "darwin":
                return s.getsockopt(0, 0x002)                 # SOL_LOCAL, LOCAL_PEERPID
            import socket as _so
            import struct
            cred = s.getsockopt(_so.SOL_SOCKET, _so.SO_PEERCRED, struct.calcsize("3i"))
            return struct.unpack("3i", cred)[0]
        except (OSError, AttributeError, ValueError):
            return None

    def envelope(self, text: str) -> str:
        """The person's words as the harness labels a message between sessions."""
        clean = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text).replace("</cross-session-message", "<\\/cross-session-message")
        return (f'<cross-session-message from-name="{self.LABEL}">\n{(self.PREFIX + " ") if self.PREFIX else ""}{clean}\n'
                f"</cross-session-message>")

    def _deliver(self, rec: dict, text: str):
        """One send to the session's inbox. Returns (True, None) or (False, why)."""
        import socket as _so
        sp = self.registry.socket_of(rec)
        if not sp:
            return False, "that session has no inbox open on this machine"
        s = _so.socket(_so.AF_UNIX, _so.SOCK_STREAM)
        s.settimeout(5)
        try:
            try:
                s.connect(sp)
            except OSError:
                return False, "that session's inbox did not answer"
            if self._peer_pid(s) != int(rec["pid"]):
                return False, "the process listening there is not that body, so nothing was sent"
            tok = self.registry.token_for(rec)
            if not tok:
                return False, "that session's inbox key could not be read"
            frame = {"msgV": 1, "msg_id": str(__import__("uuid").uuid4()), "type": "user",
                     "message": {"role": "user", "content": self.envelope(text)}, "priority": "next",
                     "session_id": rec.get("sessionId")}
            data = (json.dumps({"type": "auth", "token": tok}) + "\n" + json.dumps(frame, ensure_ascii=False) + "\n").encode()
            tok = None
            try:
                s.sendall(data)
                time.sleep(0.15)
                s.shutdown(_so.SHUT_WR)
            except OSError:
                return False, "the message could not be handed to that session"
            finally:
                data = None
            return True, frame["msg_id"]
        finally:
            s.close()

    def say(self, req: dict):
        if req.get("confirmed") is not True:
            return 403, {"refused": "a message to a body is sent only on your own tap"}
        text = str(req.get("text") or "").strip()
        if not text:
            return 400, {"refused": "nothing to say"}
        if len(text) > self.MAX_TEXT:
            return 413, {"refused": f"that is longer than {self.MAX_TEXT} characters"}
        e, rec = self.find(req.get("body"))
        if e is None:
            return 404, {"reachable": False, "why": rec}
        if rec is None:
            return 409, {"reachable": False, "why": "the harness has no record of that session, so it cannot be reached from here"}
        if rec.get("peerProtocol") != 1:
            return 409, {"reachable": False, "why": "that session speaks a messaging version this page does not know"}
        with self._lock:
            now = time.time()
            if now - self._last.get(rec["pid"], 0) < self.GAP_S:
                return 429, {"refused": "one message a second to a body"}
            self._last[rec["pid"]] = now
        ok, why = self._deliver(rec, text)
        if not ok:
            return 409, {"reachable": False, "why": why}
        return 200, {"sent": True, "body": e.get("name"), "msg_id": why, "at": now_iso(),
                     "note": "it lands in that session's conversation as a message from the ICE"}

    TERMINAL_AS = [
        "on run argv",
        "set want to item 1 of argv",
        'if application "Terminal" is not running then return "none"',
        'tell application "Terminal"',
        "repeat with w in windows",
        "repeat with t in tabs of w",
        "if tty of t is want then",
        "set selected tab of w to t",
        "set index of w to 1",
        "activate",
        'return "terminal"',
        "end if",
        "end repeat",
        "end repeat",
        "end tell",
        'return "none"',
        "end run",
    ]
    ITERM_AS = [
        "on run argv",
        "set want to item 1 of argv",
        'if application "iTerm2" is not running then return "none"',
        'tell application "iTerm2"',
        "repeat with w in windows",
        "repeat with t in tabs of w",
        "repeat with s in sessions of t",
        "if tty of s is want then",
        "select w",
        "tell t to select",
        "tell s to select",
        "activate",
        'return "iterm"',
        "end if",
        "end repeat",
        "end repeat",
        "end repeat",
        "end tell",
        'return "none"',
        "end run",
    ]
    DESKTOP_AS = ["on run argv", 'if application "Claude" is not running then return "none"',
                   'tell application "Claude" to activate', 'return "desktop"', "end run"]

    def _osascript(self, lines, args=()):
        """Runs an AppleScript with its arguments passed as argv (never pasted into the script)."""
        cmd = ["osascript"]
        for ln in lines:
            cmd += ["-e", ln]
        try:
            r = subprocess.run(cmd + list(args), capture_output=True, text=True, timeout=8)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def window(self, req: dict):
        if req.get("confirmed") is not True:
            return 403, {"refused": "a window is brought forward only on your own tap"}
        e, rec = self.find(req.get("body"))
        if e is None:
            return 404, {"raised": False, "why": rec}
        if sys.platform != "darwin":
            return 409, {"raised": False, "why": "windows are brought forward only on a Mac"}
        if as_dict(rec).get("entrypoint") == "claude-desktop":
            got = self._osascript(self.DESKTOP_AS)
            if got == "desktop":
                return 200, {"raised": True, "how": "the Claude app"}
            return 409, {"raised": False, "why": "the Claude app is not open"}
        p = next((x for x in self.hub.bodies._procs() if x.get("pid") == e["pid"]), None)
        tty = (p or {}).get("tty")
        if not tty:
            return 409, {"raised": False, "why": "that body has no window of its own (it runs without a terminal)"}
        dev = "/dev/" + tty
        got = self._osascript(self.TERMINAL_AS, [dev])
        if got != "terminal":
            got = self._osascript(self.ITERM_AS, [dev])
        if got in ("terminal", "iterm"):
            return 200, {"raised": True, "how": "Terminal" if got == "terminal" else "iTerm"}
        return 409, {"raised": False, "why": "no Terminal or iTerm window shows that body"}


# ------------------------------------------------------------------ a body's handoff, read
def host_worker_folder(bridge, key):
    """A worker the host started (agent_host.py POST /body) keeps its handoff in bg/<folder>/ under its
    own cwd, not under this server's bg dir. Asked of the host's /status: the agent whose
    `body.name` (or its folder) is `key`. Returns (its bg dir, its folder, its name), or None."""
    if bridge is None:
        return None
    try:
        s, st = bridge.call("GET", "/status", timeout=1.0)
    except Exception:
        return None
    if s != 200:
        return None
    for a in as_list(as_dict(st).get("agents")):
        b = as_dict(as_dict(a).get("body"))
        name = str(b.get("name") or "")
        if not name:
            continue
        folder = re.sub(r"[^a-z0-9-]", "-", name.lower())
        if key not in (name.casefold(), folder):
            continue
        cwd = b.get("cwd") or as_dict(a).get("cwd")
        if not cwd:
            return None
        return Path(os.path.expanduser(str(cwd))) / "bg", folder, name
    return None


def read_handoff(bg, folder, name):
    """A body's handoff.md in bg/<folder>/, read-only: never through a link (the bg dir, the folder or
    the file), the folder directly under bg, at most a megabyte."""
    bg = Path(bg)
    d = bg / folder
    f = d / "handoff.md"
    try:
        if os.path.islink(bg) or os.path.islink(d) or os.path.islink(f):
            return 403, {"refused": "a handoff is read only from the body's own folder, never through a link"}
        if d.resolve().parent != bg.resolve():
            return 403, {"refused": "a handoff is read only from the body's own folder"}
        fd = os.open(str(f), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return 404, {"refused": "that body left no handoff"}
    except OSError:
        return 403, {"refused": "that handoff could not be opened"}
    with os.fdopen(fd, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        raw = fh.read(1 << 20)
        more = bool(fh.read(1))
    text = raw.decode("utf-8", errors="replace")
    out = {"body": name, "folder": folder, "text": text, "bytes": size, "cut": more,
           "card": handoff_card_id(folder, size), "review_min": handoff_review_min(f)}
    # "Read it" opens what the worker made, not its report to the house.
    made = handoff_made_file(bg, d, text)
    if made is not None:
        got = read_inside(bg, made)
        if got is not None:
            body, msize, mmore = got
            state = handoff_state_line(text)
            out.update({"text": (state + "\n\n" + body) if state else body, "bytes": msize, "cut": mmore,
                        "made": os.path.relpath(str(made), str(bg.resolve())), "state": state})
    return 200, out


HANDOFF_SKIP = {"handoff.md", "status.md", "done", "done.md"}
MADE_FIELD_RE = re.compile(r"^\W*(?:made|wrote|file|written)\W{0,4}?[:=]\s*(.+)$", re.I)
PATH_RE = re.compile(r"[\w./~-]*[\w-]\.(?:md|txt|markdown)\b", re.I)
STATE_RE = re.compile(r"^\W*(?:status|state)\W{0,4}?[:=]\s*(.+)$", re.I)


def _inside(root: Path, p: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def handoff_made_file(bg, d, text):
    """The file the worker made, named by its handoff (a `made:`/`wrote:`/`file:` field, else a path in
    its first lines), else the one file it wrote in its folder besides its handoff and status. Only a
    regular file, not a link, inside the house's bg dir; None when there is nothing else to read."""
    bg, d = Path(bg), Path(d)
    head = text.splitlines()[:40]

    def place(raw):
        raw = raw.strip().strip("`*_'\"<>()[] ").rstrip(".,;:")
        if not raw or Path(raw).name.casefold() in HANDOFF_SKIP:
            return None
        for base in (d, bg, bg.parent):
            c = Path(os.path.expanduser(raw)) if raw.startswith(("/", "~")) else base / raw
            if _inside(bg, c) and not os.path.islink(c) and c.is_file():
                return c.resolve()
        return None

    for line in head:
        m = MADE_FIELD_RE.match(line)
        if m:
            for tok in [m.group(1)] + PATH_RE.findall(m.group(1)):
                c = place(tok)
                if c is not None:
                    return c
    for line in head[:20]:
        for tok in PATH_RE.findall(line):
            c = place(tok)
            if c is not None:
                return c
    try:
        others = [p for p in d.iterdir() if p.name.casefold() not in HANDOFF_SKIP and not p.name.startswith(".")
                  and not os.path.islink(p) and p.is_file()]
    except OSError:
        return None
    return others[0].resolve() if len(others) == 1 and _inside(bg, others[0]) else None


def read_inside(bg, path):
    """A file's text, at most a megabyte, never through a link and never outside bg. (text, bytes, cut) or None."""
    if not _inside(Path(bg), Path(path)):
        return None
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    with os.fdopen(fd, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        raw = fh.read(1 << 20)
        more = bool(fh.read(1))
    return raw.decode("utf-8", errors="replace"), size, more


def handoff_state_line(text):
    """The handoff's own state ('Status: blocked on the count'), one line, from its first 40 lines;
    empty when it names none or the state is done."""
    for line in text.splitlines()[:40]:
        m = STATE_RE.match(line)
        if m:
            v = re.sub(r"[*_`]", "", m.group(1)).strip()
            v = re.split(r"(?<=[.!?])\s", v, maxsplit=1)[0].rstrip(".")
            if not v or re.match(r"(done|complete|finished|ready)\b", v, re.I):
                return ""
            return "Status: " + v
    return ""


# ------------------------------------------------------------------ a handoff waiting: one Deal card

HANDOFF_DEAL_S = 2 * 86400     # dealt today and, waiting a day, once more; then it rests (DESIGN-BODIES §3.3)
REVIEW_MIN_RE = re.compile(r"review_min\W{0,4}?[:=]+\s*\**\s*(\d{1,4})", re.I)


def handoff_card_id(folder: str, size) -> str:
    """The folded card's id: one handoff of one body at one size, so a rewritten handoff is new."""
    return hashlib.sha256(f"handoff\x00{folder}\x00{size}".encode("utf-8")).hexdigest()


def handoff_review_min(path: Path):
    """The handoff's `review_min` line, from its first 40 lines only; None when it names none.
    Nothing else of the handoff is read for the state."""
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as fh:
            head = fh.read(16384).decode("utf-8", errors="replace").splitlines()[:40]
    except OSError:
        return None
    for line in head:
        m = REVIEW_MIN_RE.search(line)
        if m:
            n = int(m.group(1))
            return n if 0 < n <= 600 else None
    return None


def handoffs_reviewed(lines, actor) -> dict:
    """{card id: ("read" | "archived", ts)} from the person's own `witness` lines naming a body's
    handoff (body.handoff_of, body.handoff_bytes, body.card), written through /act to the home."""
    out = {}
    for ln in lines or []:
        if not isinstance(ln, dict) or ln.get("type") != "witness" or ln.get("actor") != actor:
            continue
        b = as_dict(ln.get("body"))
        of, size = b.get("handoff_of"), b.get("handoff_bytes")
        cid = b.get("card") if isinstance(b.get("card"), str) else None
        if isinstance(of, str) and isinstance(size, int):
            cid = handoff_card_id(of, size)
        if cid:
            out[cid] = ("archived" if b.get("archived") else "read", str(ln.get("ts") or ""))
    return out


def fold_handoffs(st: dict, live: dict, bg, lines, actor, home, words, now=None) -> list:
    """One Deal card per machine body (a folder under bg/) that left a handoff.md and has no review
    yet, folded into deal.cards so the Deal counts it like any other (deal.js dealt(): ranked by the
    one order, five at most, fitted to her minutes; the rest wait for the next hand). Dealt while the
    handoff is under two days old (§3.3: today, and once more waiting a day). Reviewed today, the card
    stays in the deal marked answered (the Deal's one truth: an answered card is never removed, so
    "2 of 5" holds); reviewed before today, it is gone. Each machine entry's `handoff` gains {card,
    review_min, reviewed} for the rail. Returns the cards added."""
    machine = as_list(as_dict(live).get("machine"))
    if not machine or not bg:
        return []
    now = now or time.time()
    reviewed = handoffs_reviewed(lines, actor)
    added = []
    for e in machine:
        if not isinstance(e, dict) or e.get("kind") != "background" or not e.get("folder"):
            continue
        ho = as_dict(e.get("handoff"))
        if not ho.get("present") or not isinstance(ho.get("bytes"), int):
            continue
        f = Path(bg) / str(e["folder"]) / "handoff.md"
        cid = handoff_card_id(str(e["folder"]), ho["bytes"])
        try:
            if os.path.islink(f.parent) or os.path.islink(f):
                continue
            age = now - f.stat().st_mtime
        except OSError:
            continue
        rm = handoff_review_min(f)
        rv = reviewed.get(cid)
        ho.update(card=cid, review_min=rm, reviewed=rv[0] if rv else None)
        e["handoff"] = ho
        today = datetime.fromtimestamp(now).astimezone().strftime("%Y-%m-%d")
        rv_today = bool(rv) and TranscriptSpend._local_day(rv[1]) == today
        if (rv and not rv_today) or age > HANDOFF_DEAL_S:
            continue
        name = str(e.get("name") or e["folder"])
        card = {"id": cid, "section": "handoff", "holon": home, "body": name,
                "question": words("bodies.deal.handoff_q", name=name),
                "options": [words("bodies.deal.read_now"), words("bodies.deal.later"), words("bodies.deal.archive")],
                "minutes": rm, "whole_waits": False,
                "go": f"#/bodies?body={quote(name)}&handoff=1",
                "acts": [
                    {"type": "witness", "body": {"note": words("bodies.deal.read_now"), "handoff_of": str(e["folder"]),
                                                 "handoff_bytes": ho["bytes"], "card": cid}, "links": {}},
                    {"type": "say", "body": {"text": words("bodies.deal.later"), "card": cid}, "links": {"anchored_to": [cid]}},
                    {"type": "witness", "body": {"note": words("bodies.deal.archive"), "handoff_of": str(e["folder"]),
                                                 "handoff_bytes": ho["bytes"], "card": cid, "archived": True}, "links": {}},
                ]}
        if age > 86400:
            card["waited_day"] = True
        if rv:
            card["answered"] = True
        added.append(card)
    if added:
        if st.get("deal") is None:
            st["deal"] = {"cards": []}
        deal = st.get("deal")
        if isinstance(deal, dict):
            have = {as_dict(c).get("id") for c in as_list(deal.get("cards"))}
            deal["cards"] = as_list(deal.get("cards")) + [c for c in added if c["id"] not in have]
    return added


# ------------------------------------------------------------------ what each body spent today

class CostLedger:
    """What each harness session spent today, in dollars, from the harness's own cost ledger
    (~/.claude/cost-ledger.jsonl, --cost-ledger): one line per status refresh, {ts (local time),
    session, cost_usd (the session's running total), model, cwd}. A session's day is the sum of
    its rises since its last line before today's midnight; a fall (a new process for the same
    session) counts from nothing. A session with no line before today, anywhere in the ledger,
    began today and counts from nothing. Read once in full (only session, cost and the day, by pattern), then only what was
    appended. Nothing is written; no figure is guessed."""
    LINE = re.compile(rb'"ts":\s*"(\d{4}-\d{2}-\d{2})T[^"]*".*?"session":\s*"([0-9a-f-]{36})".*?"cost_usd":\s*([0-9.]+)'
                      rb'(?:.*?"cwd":\s*"((?:[^"\\]|\\.)*)")?')

    def __init__(self, path):
        self.path = Path(path).expanduser() if path else Path.home() / ".claude" / "cost-ledger.jsonl"
        self.lock = threading.Lock()
        self.day = None
        self.off = 0
        self.last = {}       # session -> its running total at its newest line
        self.today = {}      # session -> dollars today
        self.cwd = {}        # session -> its working folder (as the ledger names it)
        self.ino = None

    def _take(self, day, sid, v, cwd):
        prev = self.last.get(sid)
        if day == self.day:
            if prev is None:
                d = v            # no line before, in the whole ledger: the session began today
            else:
                d = v - prev if v >= prev else v
            self.today[sid] = self.today.get(sid, 0.0) + max(0.0, d)
            if cwd:
                self.cwd[sid] = cwd
        self.last[sid] = v

    def read(self, now=None):
        """{session: dollars today}, {session: cwd}, or (None, None) when there is no ledger."""
        day = datetime.fromtimestamp(now or time.time()).strftime("%Y-%m-%d")
        with self.lock:
            try:
                st = os.stat(self.path)
            except OSError:
                return None, None
            if day != self.day or st.st_ino != self.ino or st.st_size < self.off:
                self.day, self.off, self.ino = day, 0, st.st_ino
                self.last, self.today, self.cwd = {}, {}, {}
            if st.st_size > self.off:
                try:
                    fd = os.open(str(self.path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    with os.fdopen(fd, "rb") as fh:
                        fh.seek(self.off)
                        raw = fh.read(st.st_size - self.off)
                except OSError:
                    return None, None
                end = raw.rfind(b"\n") + 1     # a half-written last line waits for the next read
                for line in raw[:end].splitlines():
                    m = self.LINE.search(line)
                    if not m:
                        continue
                    d = m.group(1).decode()
                    if d > day:
                        continue
                    try:
                        v = float(m.group(3))
                    except ValueError:
                        continue
                    cwd = None
                    if m.group(4) is not None:
                        try:
                            cwd = json.loads(b'"' + m.group(4) + b'"')
                        except ValueError:
                            cwd = None
                    self._take(d, m.group(2).decode(), v, cwd)
                self.off += end
            return dict(self.today), dict(self.cwd)


class TranscriptSpend:
    """The fallback when a session is not in the cost ledger (a body run through the agent host):
    the session transcript's own `usage` on its assistant lines written today, summed once per
    message (input, cache writes and output; cache reads are left out, as they repeat what was
    already counted). A count of tokens, never dollars. Read incrementally; nothing written."""

    def __init__(self):
        self.lock = threading.Lock()
        self.files = {}      # path -> {day, off, ino, sum, seen}

    def tokens_today(self, path: Path, now=None):
        day = datetime.fromtimestamp(now or time.time()).strftime("%Y-%m-%d")
        key = str(path)
        with self.lock:
            try:
                if os.path.islink(path):
                    return None
                st = os.stat(path)
            except OSError:
                return None
            c = self.files.get(key)
            if not c or c["day"] != day or c["ino"] != st.st_ino or st.st_size < c["off"]:
                c = self.files[key] = {"day": day, "off": 0, "ino": st.st_ino, "sum": 0, "seen": set()}
            if st.st_size > c["off"]:
                try:
                    fd = os.open(key, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    with os.fdopen(fd, "rb") as fh:
                        fh.seek(c["off"])
                        raw = fh.read(min(st.st_size - c["off"], 1 << 26))
                except OSError:
                    return None
                end = raw.rfind(b"\n") + 1
                for line in raw[:end].splitlines():
                    if b'"assistant"' not in line or b'"usage"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(o, dict) or o.get("type") != "assistant":
                        continue
                    ts = self._local_day(o.get("timestamp"))
                    if ts != day:
                        continue
                    msg = as_dict(o.get("message"))
                    mid = msg.get("id") or o.get("requestId") or o.get("uuid")
                    if mid in c["seen"]:
                        continue
                    c["seen"].add(mid)
                    u = as_dict(msg.get("usage"))
                    c["sum"] += sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "output_tokens")
                                    if isinstance(u.get(k), (int, float)))
                c["off"] += end
            return c["sum"]

    @staticmethod
    def _local_day(ts):
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return None


class BodiesLive:
    """GET /bodies/live and hud.bodies_live (DESIGN-BODIES §11.3). Read only, on this machine:
    nothing here is written to the record, kept, or sent. A heartbeat cannot report its own
    absence, so the gaps between its ticks are read here."""
    GAP_S = 180          # no tick for three minutes is a sleep or a stop
    SLEEP_S = 120        # the machine's monotonic clock fell behind the wall clock by this much
    MAX_FILES = 4000     # a body folder is scanned no deeper than this many files
    PROC_TTL = 5.0       # the process table and the whole reading are read at most once in five seconds
    JOIN_S = 120         # a session whose first line came within two minutes of a process's start is its own
    RUN_S = 900          # a helper that has written nothing for fifteen minutes is not said to be running
    KEEP_S = 7200        # helpers quiet for two hours are not read at all

    def __init__(self, hub):
        self.hub = hub
        self.registry = HarnessRegistry(getattr(hub.args, "harness_sessions", None))
        self._lock = threading.Lock()
        self._ps = (0.0, None)
        self._ps_ok = False
        self._cache = (0.0, None)
        self.ledger = CostLedger(getattr(hub.args, "cost_ledger", None))
        self.spend = TranscriptSpend()

    @staticmethod
    def _iso(ts):
        try:
            return datetime.fromtimestamp(float(ts)).astimezone().isoformat(timespec="seconds")
        except (OverflowError, OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _fields(path: Path) -> dict:
        """key=value or key: value lines (the kit's lease, the house's RUNNING marker)."""
        out = {}
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
                m = re.match(r"^\s*([A-Za-z_]+)\s*[:=]\s*(.*?)\s*$", line)
                if m and m.group(1).lower() not in out:
                    out[m.group(1).lower()] = m.group(2)
        except OSError:
            pass
        return out

    @staticmethod
    def _alive(pid) -> str:
        try:
            n = int(str(pid).strip())
        except (TypeError, ValueError):
            return "gone"
        if n <= 1:
            return "gone"
        try:
            os.kill(n, 0)
        except ProcessLookupError:
            return "gone"
        except PermissionError:
            return "alive"           # it exists; it is only not ours to signal
        except OSError:
            return "gone"
        return "alive"

    def _folder(self, d: Path, now: float) -> dict:
        newest, recent, n = None, 0, 0
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            for f in files:
                n += 1
                if n > self.MAX_FILES:
                    break
                try:
                    m = os.stat(os.path.join(root, f)).st_mtime
                except OSError:
                    continue
                newest = m if newest is None or m > newest else newest
                if now - m <= 1800:
                    recent += 1
        marks = [m for m in ("RUNNING", "HOLD", "DONE") if (d / m).is_file()]
        claim = self._fields(d / "RUNNING") if "RUNNING" in marks else {}
        host = self._short_host(claim.get("host"))
        here = self._short_host(os.uname().nodename if hasattr(os, "uname") else "")
        if not claim:
            process = None
        elif host and here and host != here:
            process = "elsewhere"
        else:
            process = self._alive(claim.get("pid"))
        return {"name": d.name, "actor": claim.get("actor"), "process": process, "markers": marks,
                "newest_write": self._iso(newest) if newest else None, "writes_30m": recent,
                "claimed_at": claim.get("started") or claim.get("start")}

    def _heartbeat(self, path: Path, now: float):
        """Ticks are "<ISO time> <monotonic seconds>". A gap longer than three minutes is a sleep
        when the monotonic clock (which stands still while the machine sleeps) advanced much less
        than the wall clock, and a stop otherwise (a restart resets the monotonic clock: a stop)."""
        try:
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 200_000))
                raw = fh.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            return None
        ticks = []
        for line in raw:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                wall = datetime.fromisoformat(parts[0].replace("Z", "+00:00")).timestamp()
                mono = float(parts[1])
            except ValueError:
                continue
            ticks.append((wall, mono))
        if not ticks:
            return None
        ticks.sort()
        slept, stopped = [], []
        for (w0, m0), (w1, m1) in zip(ticks, ticks[1:]):
            if w1 - w0 <= self.GAP_S:
                continue
            gap = {"from": self._iso(w0), "to": self._iso(w1)}
            if m1 >= m0 and (w1 - w0) - (m1 - m0) > self.SLEEP_S:
                slept.append(gap)
            else:
                stopped.append(gap)
        last = ticks[-1][0]
        out = {"last": self._iso(last), "slept": slept[-20:], "stopped": stopped[-20:]}
        if now - last > self.GAP_S:
            # this server is awake to answer, so the machine is awake: the service stopped
            out["open"] = {"from": self._iso(last), "kind": "stopped"}
        return out

    def _usage(self):
        f = self.hub.args.usage_file
        path = Path(f).expanduser() if f else Path.home() / ".claude" / "statusline-last.json"
        d, _ = read_json(path)
        rl = as_dict(as_dict(d).get("rate_limits"))
        if not rl:
            return None
        out = {}
        for k in ("five_hour", "seven_day"):
            w = as_dict(rl.get(k))
            pct = w.get("used_percentage")
            if isinstance(pct, (int, float)):
                out[k] = {"used_pct": pct, "resets_at": self._iso(w.get("resets_at")) if w.get("resets_at") else None}
        if not out:
            return None
        try:
            out["as_of"] = self._iso(path.stat().st_mtime)
        except OSError:
            out["as_of"] = None
        return out

    # ---- the house's own bodies, from the process table and the files they leave (2026-10-25)

    @staticmethod
    def _short_host(h) -> str:
        return str(h or "").strip().split(".")[0].lower()

    @staticmethod
    def _etime(s: str) -> int:
        """ps's elapsed time, [[dd-]hh:]mm:ss, in seconds."""
        days = 0
        if "-" in s:
            d, s = s.split("-", 1)
            days = int(d)
        parts = [int(x) for x in s.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]

    @staticmethod
    def _parse_ts(x):
        try:
            return datetime.fromisoformat(str(x).strip().replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return None

    def _procs(self) -> list:
        """The agent harness's processes on this machine, read once per PROC_TTL seconds: pid,
        parent, start, command line and working folder. Only the executable named `claude` is
        kept; the environment is never read (it carries credentials)."""
        now = time.time()
        with self._lock:
            at, rows = self._ps
            if rows is not None and now - at < self.PROC_TTL:
                return rows
        rows, parents, ok = [], {}, False
        try:
            out = subprocess.run(["ps", "-axww", "-o", "pid=,ppid=,etime=,tty=,command="], capture_output=True,
                                 text=True, timeout=4).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for line in out.splitlines():
            m = re.match(r"\s*(\d+)\s+(\d+)\s+([\d:-]+)\s+(\S+)\s+(.*)$", line)
            if not m:
                continue
            ok = True
            pid, ppid, cmd = int(m.group(1)), int(m.group(2)), m.group(5)
            tty = m.group(4) if re.match(r"^ttys?\d+$|^pts/\d+$", m.group(4)) else None
            parents[pid] = cmd[:300]
            exe = cmd.split(" --", 1)[0].strip()
            if not (exe == "claude" or exe.endswith("/claude")):
                continue
            try:
                start = now - self._etime(m.group(3))
            except ValueError:
                continue
            rows.append({"pid": pid, "ppid": ppid, "start": start, "cmd": cmd, "exe": exe, "cwd": None, "tty": tty})
        for r in rows:
            r["parent"] = parents.get(r["ppid"], "")
        if rows:
            try:
                lo = subprocess.run(["lsof", "-a", "-d", "cwd", "-p", ",".join(str(r["pid"]) for r in rows), "-Fpn"],
                                    capture_output=True, text=True, timeout=4).stdout
            except (OSError, subprocess.SubprocessError):
                lo = ""
            cur, cwd = None, {}
            for line in lo.splitlines():
                if line.startswith("p"):
                    cur = int(line[1:]) if line[1:].isdigit() else None
                elif line.startswith("n") and cur is not None:
                    cwd[cur] = line[1:]
            for r in rows:
                r["cwd"] = cwd.get(r["pid"])
        with self._lock:
            self._ps = (now, rows)
            self._ps_ok = ok
        return rows

    @staticmethod
    def _kind(p) -> str:
        """prime-candidate · background · dock · window, from the command line alone."""
        cmd, exe = p["cmd"], p["exe"]
        if re.search(r"--append-system-prompt[ =]+BACKGROUND BODY", cmd, re.I):
            return "background"
        if "claude-agent-sdk" in exe or "claude-agent-acp" in p.get("parent", ""):
            return "dock"
        if "--output-format stream-json" in cmd or "--output-format=stream-json" in cmd:
            return "window"
        return "interactive"

    @staticmethod
    def _proc_name(cmd: str):
        m = re.search(r"BACKGROUND BODY\.?\s+You are ([^\n—,.;]+?)\s*(?:[—–,.;]|$)", cmd)
        return m.group(1).split()[-1] if m else None

    @staticmethod
    def _prompt_tail(cmd: str):
        """For a body with no folder: the words after its name, a sentence at most."""
        m = re.search(r"BACKGROUND BODY\.?\s+You are [^—\n]*—\s*([^\n]+)", cmd)
        if not m:
            return None
        s = re.split(r"(?<=[.!?])\s", m.group(1).strip(), maxsplit=1)[0]
        return s[:110] or None

    def _session_dir(self, house: Path) -> Path:
        root = getattr(self.hub.args, "sessions", None)
        root = Path(root).expanduser() if root else Path.home() / ".claude" / "projects"
        return root / re.sub(r"[^A-Za-z0-9]", "-", str(house))

    def _first_ts(self, path: Path):
        try:
            with open(path, "rb") as fh:
                head = fh.read(65536).decode("utf-8", errors="replace")
        except OSError:
            return None
        m = re.search(r'"timestamp"\s*:\s*"([^"]+)"', head)
        return self._parse_ts(m.group(1)) if m else None

    def _sessions(self, sdir: Path, procs: list, now: float, reg=None):
        """Which session each process is writing, and the helpers each session has running.
        A process names its session when its command carries --resume or --session-id; else the
        session whose first line was written within two minutes of the process's start is its
        own (a harness writes its first line as it starts). A session begun later in the same
        process (a cleared conversation) cannot be joined; its helpers are said to be running in
        this house, under no body. The harness's own registry (~/.claude/sessions/<pid>.json) names
        each live process's session outright; where it does, it is used first and these readings
        are only the fallback."""
        by_pid, files = {}, {}
        reg = reg or {}
        if sdir.is_dir():
            oldest = min((p["start"] for p in procs), default=now) - 300
            for f in sdir.glob("*.jsonl"):
                try:
                    if f.stat().st_mtime >= oldest:
                        files[f.stem] = f
                except OSError:
                    continue
        taken = set()
        for p in procs:
            sid = str(as_dict(reg.get(p["pid"])).get("sessionId") or "")
            if UUID_RE.match(sid):
                by_pid[p["pid"]] = (sid, "registry")
                taken.add(sid)
                f = sdir / f"{sid}.jsonl"
                if sid not in files and f.is_file():
                    files[sid] = f
        for p in sorted(procs, key=lambda x: x["start"]):
            if p["pid"] in by_pid:
                continue
            m = re.search(r"--(?:resume|session-id)[ =]+([0-9a-f-]{36})", p["cmd"])
            if m:
                by_pid[p["pid"]] = (m.group(1), "named")
                taken.add(m.group(1))
        starts = {sid: self._first_ts(f) for sid, f in files.items() if sid not in taken}
        for p in procs:
            if p["pid"] in by_pid:
                continue
            best = None
            for sid, t0 in starts.items():
                if t0 is None or sid in taken:
                    continue
                d = abs(t0 - p["start"])
                if d <= self.JOIN_S and (best is None or d < best[0]):
                    best = (d, sid)
            if best:
                by_pid[p["pid"]] = (best[1], "start")
                taken.add(best[1])
        helpers, last = {}, {}
        for sid, f in files.items():
            try:
                last[sid] = f.stat().st_mtime
            except OSError:
                pass
        if sdir.is_dir():
            for meta in sdir.glob("*/subagents/agent-*.meta.json"):
                sid = meta.parent.parent.name
                log = meta.with_name(meta.name[:-len(".meta.json")] + ".jsonl")
                try:
                    mt = log.stat().st_mtime
                except OSError:
                    continue
                if now - mt > self.KEEP_S:
                    continue
                d, _ = read_json(meta)
                d = as_dict(d)
                started = self._first_ts(log)
                running = not d.get("finished") and now - mt <= self.RUN_S
                desc = str(d.get("description") or "")[:90] or None
                helpers.setdefault(sid, []).append({
                    "id": meta.name[len("agent-"):-len(".meta.json")][:40], "description": desc,
                    "model": str(d.get("model"))[:24] if d.get("model") else None,
                    "started": self._iso(started) if started else None, "newest_write": self._iso(mt),
                    "running": bool(running)})
        for v in helpers.values():
            v.sort(key=lambda x: x.get("started") or "")
        return by_pid, helpers, last

    @staticmethod
    def _task(d: Path):
        """The first meaningful line of a body's task file, in a few words."""
        try:
            text = (d / "task.md").read_text(encoding="utf-8", errors="replace")[:20000]
        except OSError:
            return None
        lines = text.splitlines()
        short = lambda s: (s if len(s) <= 110 else s[:108].rsplit(" ", 1)[0] + "…") if s else None
        cap = lambda s: s[:1].upper() + s[1:] if s else s
        name = re.escape(d.name[3:] if d.name.lower().startswith("bg-") else d.name)
        for ln in lines:                                   # 1. the heading, less its labels
            if ln.startswith("#"):
                s = ln.lstrip("#").strip()
                s = re.sub(r"\([^)]*background body[^)]*\)", "", s, flags=re.I)
                s = re.sub(r"\b(bg-)?(sophia\s+)?" + name + r"\b", "", s, flags=re.I)
                s = re.sub(r"^\W*task\b", "", s, flags=re.I)
                s = re.sub(r"\btask\W*$", "", s, flags=re.I)
                s = s.strip(" ,;:—–-*")
                if len(s.split()) >= 3:
                    return short(s)
                break
        paras, cur = [], []
        for ln in lines + [""]:
            if not ln.strip() or ln.startswith("#"):
                if cur:
                    paras.append(" ".join(cur))
                cur = []
                continue
            cur.append(ln.strip())
        for p in paras:                                    # 2. a line that says what it does
            m = re.match(r"^\**\s*(?:what i am doing|the one task[^:]*|task)\s*:\**\s*(.+)$", p, re.I)
            if m:
                first = re.split(r"(?<=[.!?])\s", m.group(1).strip(" *"), maxsplit=1)[0]
                return short(cap(first))
        for m in re.finditer(r"^brief:\s*\S*?([^/\s]+)\.md\b", text, re.I | re.M):   # 3. the brief's own name
            if m:
                s = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", m.group(1)).replace("-", " ").strip()
                if s:
                    return short(cap(s))
        for p in paras:                                    # 4. the first plain paragraph
            if p.startswith("*") or re.match(r"^[A-Za-z _-]{2,24}:\s", p) or re.match(r"^\d+\.", p):
                continue
            s = re.split(r"(?<=[.!?])\s", p, maxsplit=1)[0]
            if ": " in s[:140] and len(s.split(": ", 1)[1].split()) >= 4:
                s = s.split(": ", 1)[1]
            return short(cap(s.strip()))
        return None

    @staticmethod
    def _last_line(path: Path):
        try:
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 8000))
                raw = fh.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            return None
        for ln in reversed(raw):
            s = ln.strip().lstrip("-*# ").strip()
            if s:
                return s[:160]
        return None

    def _house(self, bg: Path, desk):
        if desk:
            try:
                return Path(os.path.commonpath([str(bg.resolve()), str(Path(desk).resolve())]))
            except ValueError:
                pass
        hq = self.hub.hq
        try:
            bg.resolve().relative_to(hq)
            return hq
        except ValueError:
            return bg.resolve().parent

    def _machine(self, bg: Path, now: float, bodies: list):
        """The house's bodies on this machine: the prime (the interactive harness in the house),
        each background body (its process, its folder, or both), the dock and any other window,
        each with the helpers its session has running."""
        desk_f = getattr(self.hub.args, "desk", None)
        house = self._house(bg, desk_f)
        hs = str(house)
        everyone = self._procs()
        allp = {x["pid"]: x for x in everyone}
        procs = [p for p in everyone if p.get("cwd") and (p["cwd"] == hs or p["cwd"].startswith(hs + os.sep))]
        for p in procs:
            p["k"] = self._kind(p)
        reg = self.registry.entries()
        by_pid, helpers, last = self._sessions(self._session_dir(house), procs, now, reg)
        joined = set()

        def subs(pid):
            j = by_pid.get(pid)
            if not j:
                return [], None, None
            joined.add(j[0])
            return [x for x in helpers.get(j[0], []) if x["running"]], j[1], last.get(j[0])

        newer = lambda a, b: a if b is None else b if a is None else max(a, b)
        desk = self._fields(Path(desk_f).expanduser()) if desk_f else {}
        entries = []
        # the prime: the interactive harness in the house; of several, the one begun nearest the desk's since
        inter = [p for p in procs if p["k"] == "interactive"]
        since = self._parse_ts(desk.get("since")) if desk else None
        prime = None
        if inter:
            prime = min(inter, key=lambda p: abs(p["start"] - since) if since else p["start"])
        if desk_f or prime:
            holder = (desk.get("holder") or "").strip()
            here = self._short_host(os.uname().nodename if hasattr(os, "uname") else "")
            holds = bool(holder) and holder.lower() in ("laptop", "prime", "this machine", here)
            s, how, sw = subs(prime["pid"]) if prime else ([], None, None)
            entries.append({"name": "prime", "kind": "prime", "pid": prime["pid"] if prime else None,
                            "alive": bool(prime), "started": self._iso(prime["start"]) if prime else None,
                            "holds_desk": holds, "desk_holder": holder or None, "since": desk.get("since") or None,
                            "newest_write": self._iso(sw) if sw else None,
                            "newest_age_s": int(now - sw) if sw else None,
                            "joined_by": how, "subagents": s})
        # background bodies: by folder, joined to their process by name
        procs_bg = {}
        for p in procs:
            if p["k"] == "background":
                n = self._proc_name(p["cmd"])
                if n:
                    procs_bg.setdefault(n.casefold(), p)
        seen = set()
        for b in bodies:
            nm = b["name"][3:] if b["name"].lower().startswith("bg-") else b["name"]
            key = nm.casefold()
            p = procs_bg.get(key)
            d = bg / b["name"]
            marks = b.get("markers") or []
            claim = self._fields(d / "RUNNING") if "RUNNING" in marks else {}
            claimed_pid = None
            try:
                claimed_pid = int(str(claim.get("pid", "")).strip())
            except ValueError:
                pass
            host = claim.get("host") or None
            here_h = self._short_host(os.uname().nodename if hasattr(os, "uname") else "")
            elsewhere = bool(host) and self._short_host(host) != here_h
            # alive: its harness is in the table now, by its name or by the claim's pid. A living pid
            # that is not the harness is a reused number, never this body. Without a table (ps
            # could not be run), the claim's pid is asked of the machine, as before.
            proc = p or (allp.get(claimed_pid) if claimed_pid else None)
            alive = proc is not None or (not self._ps_ok and bool(claimed_pid) and not elsewhere
                                         and self._alive(claimed_pid) == "alive")
            done = "DONE" in marks
            stale = "RUNNING" in marks and not done and not alive and not elsewhere
            state = ("archived" if done else "elsewhere" if elsewhere else "running" if alive
                     else "stale" if "RUNNING" in marks else "archived")
            if alive:
                seen.add(proc["pid"])
            s, how, sw = subs(proc["pid"]) if proc else ([], None, None)
            fw = self._parse_ts(b.get("newest_write")) if b.get("newest_write") else None
            nw = newer(fw, sw)
            hf = d / "handoff.md"
            try:
                hsize = hf.stat().st_size if hf.is_file() else None
            except OSError:
                hsize = None
            heavy = state != "archived"
            entries.append({"name": nm, "folder": b["name"], "kind": "background", "pid": proc["pid"] if proc else claimed_pid,
                            "alive": alive, "started": claim.get("start") or claim.get("started") or (self._iso(proc["start"]) if proc else None),
                            "task": (self._task(d) if heavy else None) or (self._prompt_tail(proc["cmd"]) if proc else None),
                            "newest_write": self._iso(nw) if nw else None,
                            "newest_age_s": int(now - nw) if nw else None,
                            "status_last": self._last_line(d / "status.md") if heavy else None,
                            "stale": stale, "state": state, "host": host, "here": not elsewhere,
                            "handoff": {"present": hsize is not None, "bytes": hsize} if hsize is not None else None,
                            "joined_by": how, "subagents": s})
        for p in procs:
            if p["pid"] in seen or (prime and p["pid"] == prime["pid"]):
                continue
            k = p["k"]
            if k == "interactive":
                k = "window"
            s, how, sw = subs(p["pid"])
            e = {"name": self._proc_name(p["cmd"]) if k == "background" else k, "kind": k, "pid": p["pid"], "alive": True,
                 "started": self._iso(p["start"]), "task": self._prompt_tail(p["cmd"]) if k == "background" else None,
                 "newest_write": self._iso(sw) if sw else None, "newest_age_s": int(now - sw) if sw else None,
                 "stale": False, "state": "running", "here": True, "joined_by": how, "subagents": s}
            entries.append(e)
        for e in entries:                       # what the harness's registry says of each live process
            p = allp.get(e.get("pid")) if e.get("alive") else None
            r = as_dict(reg.get(e.get("pid"))) if p else {}
            j = by_pid.get(e.get("pid")) if p else None
            e["session_id"] = (j[0] if j else None)
            e["status"] = r.get("status") if r.get("status") in ("idle", "busy", "shell", "waiting") else None
            e["window"] = bool(p) and (bool(p.get("tty")) or r.get("entrypoint") == "claude-desktop")
        loose = [x for sid, v in helpers.items() if sid not in joined for x in v if x["running"]]
        return entries, loose

    def spent(self, sid, cwd, today=None, now=None):
        """One session's spend today: {usd} from the cost ledger, else {tokens} from its transcript's
        own usage (DESIGN-BODIES §7, the fallback), else None: never a guess."""
        if not isinstance(sid, str) or not UUID_RE.match(sid):
            return None
        if today is None:
            today, _ = self.ledger.read(now)
        if today and sid in today:
            return {"usd": round(today[sid], 2)}
        if isinstance(cwd, str) and cwd.startswith("/"):
            n = self.spend.tokens_today(self._session_dir(Path(cwd)) / f"{sid}.jsonl", now)
            if n:
                return {"tokens": n}
        return None

    def _spent_all(self, out, house, now):
        """Each machine entry's `spent_today`, and the house's day in `spent_today` (every session the
        ledger saw working in the house today, whether on the rail or not)."""
        today, cwds = self.ledger.read(now)
        hs = str(house) if house else None
        for e in as_list(out.get("machine")):
            if isinstance(e, dict):
                e["spent_today"] = self.spent(e.get("session_id"), hs, today, now) if e.get("session_id") else None
        if today is None:
            toks = sum(as_dict(e.get("spent_today")).get("tokens") or 0 for e in as_list(out.get("machine")) if isinstance(e, dict))
            out["spent_today"] = {"tokens": toks, "as_of": self._iso(now), "from": "transcripts"} if toks else None
            return
        mine = [sid for sid, c in (cwds or {}).items() if hs and (c == hs or str(c).startswith(hs + os.sep))]
        total = sum(today.get(sid, 0.0) for sid in mine)
        out["spent_today"] = {"usd": round(total, 2), "sessions": len(mine), "as_of": self._iso(now), "from": "ledger"}

    def read(self) -> dict:
        now = time.time()
        with self._lock:
            at, cached = self._cache
            if cached is not None and now - at < self.PROC_TTL:
                return cached
        out = self._read(now)
        with self._lock:
            self._cache = (now, out)
        return out

    def _read(self, now: float) -> dict:
        hq = self.hub.hq
        bg = Path(self.hub.args.bg).expanduser() if self.hub.args.bg else hq / "bg"
        bodies = []
        if bg.is_dir():
            for d in sorted(bg.iterdir()):
                if not d.is_dir() or d.name == "archive" or d.name.startswith("."):
                    continue
                if getattr(self.hub.args, "desk", None) and not (d.name.lower().startswith("bg-") or
                                               any((d / m).is_file() for m in ("RUNNING", "DONE", "task.md"))):
                    continue          # a house's other folders (briefs, a jam's files) are not bodies
                if (d / "DONE").is_file() and not (d / "RUNNING").is_file():
                    bodies.append(self._archived(d))
                else:
                    bodies.append(self._folder(d, now))
        lease = self._fields(hq / ".desk" / "lease" / "holder")
        desk = None
        if lease:
            here = self._short_host(os.uname().nodename if hasattr(os, "uname") else "")
            lh = self._short_host(lease.get("host"))
            proc = "elsewhere" if lh and here and lh != here else self._alive(lease.get("pid"))
            desk = {"process": proc, "since": lease.get("started")}
        out = {"as_of": self._iso(now), "host": "this machine", "bodies": bodies, "desk": desk,
               "heartbeat": None, "usage": self._usage()}
        hb = self.hub.args.heartbeat
        out["heartbeat"] = self._heartbeat(Path(hb).expanduser() if hb else hq / ".heartbeat", now)
        try:
            out["machine"], out["house_helpers"] = self._machine(bg, now, bodies)
        except Exception as e:      # the machine's reading never stops the rest
            print(f"serve.py: this machine's bodies could not be read ({type(e).__name__})", file=sys.stderr)
            out["machine"], out["house_helpers"] = None, []
        try:
            self._spent_all(out, self._house(bg, getattr(self.hub.args, "desk", None)), now)
        except Exception as e:      # what was spent never stops the rest
            print(f"serve.py: what the bodies spent could not be read ({type(e).__name__})", file=sys.stderr)
            out["spent_today"] = None
        return out

    def _archived(self, d: Path) -> dict:
        """A finished body, cheaply: its name and when it finished, no walk of its folder."""
        try:
            m = (d / "DONE").stat().st_mtime
        except OSError:
            m = None
        return {"name": d.name, "actor": None, "process": None, "markers": ["DONE"],
                "newest_write": self._iso(m) if m else None, "writes_30m": 0, "claimed_at": None}


# ------------------------------------------------------------------ the full card's story (GET /card/<id>)

CARD_STORY_MAX = 400
CARD_STORY_CARRIES = {"commit", "thread", "request", "rfg", "escalate", "kept", "decide", "offer"}


def card_story(hub, cid) -> dict:
    """GET /card/<id>: every line the record holds about one card (or a thread, a commitment, a
    question), read-only, oldest first: the line itself; every line naming it in its links or in its
    body (card, about, answers); and the lines answering a commitment, thread, request or question
    that names it. The same rule as hud/card-full.js (linesAbout). Read through engine/record.py's
    read_all over the holons held here, so no link is followed and a cell whose id its own inception
    does not prove is refused and not read; in fixture mode the fixture's own cards[].lines too.
    A line's signature is not sent, only whether it carries one."""
    out = {"id": cid, "lines": [], "as_of": now_iso()}
    if not isinstance(cid, str) or not cid or len(cid) > 200:
        return out
    pool = []
    if hub.fixture is not None:
        for c in as_list(as_dict(hub.fixture).get("cards")):
            pool += [ln for ln in as_list(as_dict(c).get("lines")) if isinstance(ln, dict)]
    try:
        if str(ENGINE) not in sys.path:
            sys.path.insert(0, str(ENGINE))
        import record as rec
        pool += [ln for ln in as_list(rec.read_all(str(hub.hq)).get("lines")) if isinstance(ln, dict)]
    except Exception as e:   # the story is a reading; a record that cannot be read leaves it short, said in the log
        print(f"serve.py: the card's story could not be read ({type(e).__name__})", file=sys.stderr)
    ids, found = {cid}, {}

    def named(v):
        return {i for i in as_list(v) if isinstance(i, str)} & ids

    def relation(ln):
        if ln.get("id") in ids:
            return True
        body, links = as_dict(ln.get("body")), as_dict(ln.get("links"))
        if any(isinstance(body.get(k), str) and body.get(k) in ids for k in ("card", "about", "answers", "thread")):
            return True
        if any(named(links.get(k)) for k in ("answers", "anchored_to", "fulfils", "witnesses", "supersedes")):
            return True
        if any(named(links.get(k)) for k in ("predecessor", "successor", "serves")):
            return False   # near: shown in the story, its own story not followed
        return None

    for _ in range(4):
        grew = False
        for ln in pool:
            i = ln.get("id")
            if not isinstance(i, str) or i in found:
                continue
            r = relation(ln)
            if r is None:
                continue
            found[i] = ln
            if r and ln.get("type") in CARD_STORY_CARRIES and i not in ids:
                ids.add(i)
                grew = True
        if not grew:
            break
    rows = sorted(found.values(), key=lambda ln: (str(ln.get("ts") or ""), str(ln.get("id"))))[:CARD_STORY_MAX]
    out["lines"] = [dict({k: ln.get(k) for k in ("v", "id", "ts", "actor", "for", "holon", "type", "links", "audience", "reason")},
                         body={k: v for k, v in as_dict(ln.get("body")).items() if k not in ("body_salt", "body_salts")},
                         signed=bool(ln.get("sig"))) for ln in rows]
    return out


class Handler(SimpleHTTPRequestHandler):
    hub: Hub = None
    phone = False      # True on the phone listener (PhoneHandler)

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def log_message(self, fmt, *args):
        if self.hub.args.verbose:
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self) -> bool:
        port = self.hub.args.port
        return (self.headers.get("Host") or "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        port = self.hub.args.port
        return origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

    def _token_ok(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-HUD-Token") or "", self.hub.token)

    def _guard(self, need_token: bool) -> bool:
        """True when the request may proceed; otherwise the refusal is already sent."""
        if not self._host_ok():
            self._json(421, {"refused": "this server answers only on 127.0.0.1 or localhost at its own port"})
            return False
        if not self._origin_ok():
            self._json(403, {"refused": "only this server's own pages may act"})
            return False
        if need_token and not self._token_ok():
            self._json(403, {"refused": "the page's token is missing"})
            return False
        return True

    def _read_body(self, cap=1 << 20):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            v = json.loads(self.rfile.read(min(n, cap)) or b"{}")
            return v if isinstance(v, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        need = (path.startswith("/agent/") or path.startswith("/act/") or path in ("/talk", "/presence", "/bodies/talk", "/bodies/reach", "/bodies/handoff", "/voice/info")
                or (self.phone and path in ("/state", "/stream", "/bodies/live")))
        if not self._guard(need):
            return
        if path.startswith("/agent/"):
            return self._agent_get(path, {k: v[0] for k, v in parse_qs(u.query).items()})
        if path == "/token":
            if self.phone:
                return self._json(403, {"refused": "the page's token is never given on the phone door"})
            if self.headers.get("Origin") is not None:
                return self._json(403, {"refused": "the token is read only by the page's own first request"})
            return self._json(200, {"token": self.hub.token})
        if path == "/state":
            return self._json(200, self.hub.state())
        if path.startswith("/card/"):   # the full card's story: the record's lines about one id, read-only
            if self.phone and not self._token_ok():
                return self._json(403, {"refused": "the page's token is missing"})
            from urllib.parse import unquote
            return self._json(200, card_story(self.hub, unquote(path[len("/card/"):])))
        if path.startswith("/act/"):
            s, o = self.hub.act_status(path[len("/act/"):])
            return self._json(s, o)
        if path in ("/talk", "/presence"):
            room = (parse_qs(u.query).get("room") or [None])[0]
            if path == "/presence":
                s, o = self.hub.talk.presence(room)
                return self._json(s, o)
            if room not in self.hub.talk.rooms():
                return self._json(404, {"refused": "that room is not held here"})
            return self._json(200, {"room": room, "said": self.hub.talk.said(room), "as_of": now_iso()})
        if path == "/stream":
            return self._stream()
        if path in ("/bodies/talk", "/bodies/reach"):
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if path == "/bodies/reach":
                s, o = self.hub.bodytalk.reach(q.get("body"))
                return self._json(s, o)
            return self._body_stream(q)
        if path == "/bodies/handoff":
            s, o = self.hub.handoff_text((parse_qs(u.query).get("body") or [None])[0])
            return self._json(s, o)
        if path == "/voice/info":
            return self._json(200, voice_info(self.hub.args))
        if path == "/bodies/live":
            if self.hub.fixture is not None and not self.hub.args.bg:
                return self._json(200, as_dict(as_dict(self.hub.fixture.get("hud")).get("bodies_live")))
            return self._json(200, self.hub.bodies.read())
        if path.endswith(".py") or "/." in path or path.endswith(".hud-token"):
            return self._json(404, {"refused": "not served"})
        return super().do_GET()

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        hub = self.hub
        with hub.cond:
            seen = hub.version
        talk_seen = hub.talk.counts()
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            while True:
                with hub.cond:
                    hub.cond.wait_for(lambda: hub.version != seen, timeout=15)
                    v = hub.version
                if v != seen:
                    seen = v
                    msg = json.dumps({"version": v, "at": now_iso()})
                    self.wfile.write(f"event: state\ndata: {msg}\n\n".encode())
                    talk_seen, fresh = hub.talk.since(talk_seen)
                    for room, rows in fresh:
                        msg = json.dumps({"room": room, "rows": rows}, ensure_ascii=False)
                        self.wfile.write(f"event: talk\ndata: {msg}\n\n".encode())
                else:
                    self.wfile.write(b": still here\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _body_stream(self, q):
        """GET /bodies/talk: a terminal body's conversation, from its own transcript, as server-sent
        events; followed as it grows. A new conversation in that session ends the stream with a
        `state` line (the page opens it again)."""
        bt = self.hub.bodytalk
        e, rec = bt.find(q.get("body"))
        if e is None:
            return self._json(404, {"refused": rec})
        if rec is None:
            return self._json(409, {"refused": "the harness has no record of that session, so its conversation cannot be read"})
        path = bt.transcript_of(rec)
        if path is None:
            return self._json(409, {"refused": "that session's conversation is not on this machine"})
        try:
            since = max(0, int(q.get("since") or 0))
        except ValueError:
            since = 0
        reader = TranscriptReader(path)
        try:
            first = reader.read_new(since)
        except OSError:
            return self._json(409, {"refused": "that session's conversation could not be read"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        sid, pid = rec.get("sessionId"), rec.get("pid")
        send = lambda ev: self.wfile.write(f"event: line\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
        try:
            self.wfile.write(b"retry: 3000\n\n")
            for ev in first:
                send(ev)
            self.wfile.write(f"event: caught_up\ndata: {json.dumps({'next': reader.n})}\n\n".encode())
            self.wfile.flush()
            quiet, checked = time.time(), time.time()
            while True:
                time.sleep(0.5)
                try:
                    evs = reader.read_new(0)
                except OSError:
                    evs = []
                for ev in evs:
                    send(ev)
                if evs:
                    self.wfile.write(f"event: caught_up\ndata: {json.dumps({'next': reader.n})}\n\n".encode())
                    self.wfile.flush()
                    quiet = time.time()
                if time.time() - checked > 5:
                    checked = time.time()
                    now_rec = bt.registry.entries().get(pid)
                    if not now_rec or now_rec.get("sessionId") != sid:
                        send({"n": reader.n, "ts": now_iso(), "kind": "state", "turn": reader.turn,
                              "text": "this body began a new conversation" if now_rec else "this body has ended"})
                        self.wfile.flush()
                        return
                if time.time() - quiet > 15:
                    self.wfile.write(b": still here\n\n")
                    self.wfile.flush()
                    quiet = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _agent_get(self, path, q):
        b = self.hub.bridge
        if path == "/agent/list":
            st = self.hub.state()
            # the service the agent thinks with, by the name the person's vendors file gives it (or null):
            # the About sheet and the host's first-contact answer say one sentence from it (dock.first.words)
            return self._json(200, {"agents": st["hud"].get("agents", []),
                                    "dock": dict(as_dict(st["hud"].get("dock")), vendor=self._agent_vendor())})
        if path == "/agent/routes":
            s, o = b.routes_of(q.get("conversation", ""), q.get("turn", ""))
            return self._json(s, o)
        if path in ("/agent/figures", "/agent/mode"):
            # the trust layer's Full depth (every raw field the harness gave), and the harness's own modes
            if not q.get("agent"):
                return self._json(400, {"refused": "which agent?"})
            s, o = b.call("GET", f"{path[len('/agent'):]}?agent={quote(q['agent'])}", timeout=2.0)
            if s is None:
                return self._json(409, {"refused": "your agent is resting"})
            return self._json(s, o)
        if path == "/agent/stream":
            return self._agent_stream(f"/stream?conversation={quote(q.get('conversation', ''))}&since={quote(q.get('since', '0'))}")
        if path == "/agent/pty/stream":
            if self.phone:
                return self._json(403, {"refused": "the command line is opened only on the computer itself"})
            return self._agent_stream(f"/pty/stream?pty={quote(q.get('pty', ''))}&since={quote(q.get('since', '0'))}")
        return self._json(404, {"refused": "not here"})

    def _agent_stream(self, hostpath):
        b = self.hub.bridge
        port = b._port()
        if not port:
            return self._json(409, {"refused": "your agent is resting"})
        req = urllib.request.Request(f"http://127.0.0.1:{port}{hostpath}", headers={"X-HUD-Token": self.hub.token})
        try:
            up = NO_PROXY.open(req, timeout=40)
        except urllib.error.HTTPError as e:
            return self._json(e.code, {"refused": "no such conversation"})
        except OSError:
            return self._json(409, {"refused": "your agent is resting"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            while True:
                line = up.readline()
                if not line:
                    break
                self.wfile.write(line)
                if line in (b"\n", b"\r\n"):
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            up.close()

    def _agent_house(self, st):
        """What the house holds now, as the agent needs it with every line (without it the
        agent could say "no one waiting on you" beside a card that said the steward waited, and could not see
        what she had just answered): the served Deal's cards in the dealer's order, the open owed entries
        (each holder by name, each by-when as a date), and the served clock's day. The host says each
        by-when against that day in words, so the agent never computes it."""
        st = as_dict(st)
        names = {as_dict(a).get("id"): as_dict(a).get("name") for a in as_list(st.get("actors"))}
        holons = {as_dict(x).get("id"): as_dict(x).get("name") for x in as_list(st.get("holons"))}
        owed = [as_dict(e) for e in as_list(as_dict(st.get("owed")).get("entries"))]
        due = {e.get("id"): e.get("due") for e in owed if isinstance(e.get("id"), str)}
        cards = [as_dict(c) for c in as_list(as_dict(st.get("deal")).get("cards"))]
        out = {"deal": [dict({k: c.get(k) for k in ("id", "question", "title", "options", "holon", "holon_name", "kind",
                                                    "section", "why", "recommendation", "answered")},
                             due=due.get(c.get("id"))) for c in cards[:40]],
               "owed": [{"id": e.get("id"), "title": e.get("title"), "kind": e.get("kind"), "due": e.get("due"),
                         "holder": e.get("holder"), "holder_name": names.get(e.get("holder")),
                         "holon_name": holons.get(e.get("holon")), "status": e.get("status")}
                        for e in owed if e.get("status") in (None, "open")][:40],
               "person": st.get("actor") or getattr(self.hub, "actor", None),
               # her name as the house knows it (hud.person), never the computer's account name
               "person_name": as_dict(as_dict(st.get("hud")).get("person")).get("name")}
        now = as_dict(st.get("hud")).get("now")
        out["today"] = (str(now)[:10] if isinstance(now, str) and re.match(r"\d{4}-\d{2}-\d{2}", now)
                        else datetime.now().astimezone().date().isoformat())
        return out

    def _agent_vendor(self):
        """The name of the one service beyond this computer that the person's vendors file names (its
        `name`, else "Anthropic" for a vendor of that kind; one marked `default` wins), or None when the
        file names none, or several alike. Only names and hosts are read, never a key."""
        args = self.hub.args
        vendors = {}
        for path in [Path(args.routes).expanduser() if getattr(args, "routes", None) else ENGINE / "routes.json",
                     Path(args.vendors).expanduser() if getattr(args, "vendors", None)
                     else Path.home() / ".config" / "lionsberg" / "vendors.json"]:
            cfg, _ = read_json(path)
            vendors.update(as_dict(as_dict(cfg).get("vendors")))
        far = []
        for v in vendors.values():
            v = as_dict(v)
            host = str(v.get("host") or urlparse(str(v.get("base_url") or "")).hostname or "")
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == "localhost"
            if host and not local:
                far.append(v)
        pick = [v for v in far if v.get("default") is True] or far
        if len(pick) != 1:
            return None
        v = pick[0]
        name = v.get("name") if isinstance(v.get("name"), str) and v["name"].strip() else (
            "Anthropic" if v.get("kind") == "anthropic" else None)
        return name.strip()[:60] if name else None

    def _agent_post(self, path, req):
        hub, b = self.hub, self.hub.bridge
        if path in ("/agent/wake", "/agent/say"):
            if req.get("confirmed") is not True:
                return self._json(403, {"refused": "your agent is woken only by your own tap"})
            if path == "/agent/say" and not str(req.get("text") or "").strip():
                return self._json(400, {"refused": "nothing to say"})
            if not b.ensure():
                return self._json(503, {"refused": "your agent could not be woken on this computer"})
            body = {k: req.get(k) for k in ("agent", "conversation", "text", "about") if req.get(k) is not None}
            if path == "/agent/say":
                # what the page shows now rides with the line, so the agent never contradicts the screen;
                # the served Deal's cards ride too, so an act the agent proposes by a card's title resolves
                if isinstance(req.get("page"), dict):
                    body["page"] = req["page"]
                # and what the house holds now (the Deal's open cards, what is owed, the served day), so
                # the agent answers "what waits" and "is anything late" from it, with no tool
                try:
                    body.update(self._agent_house(hub.state()))
                except Exception:
                    pass
                body["vendor"] = self._agent_vendor()
            s, o = b.call("POST", path[len("/agent"):], body, timeout=5)
            hub.bump()
            return self._json(s or 503, o or {"refused": "your agent did not answer"})
        if path == "/agent/body":
            # a second body, started on the person's own tap after the cost was said (DESIGN-BODIES §4)
            if req.get("confirmed") is not True:
                return self._json(403, {"refused": "a body is started only by your own tap"})
            task = str(req.get("task") or "").strip()
            if not task:
                return self._json(400, {"refused": "a body needs its task, in your words"})
            if not b.ensure():
                return self._json(503, {"refused": "your agent could not be woken on this computer"})
            live = {}
            try:
                live = hub.bodies.read()
            except Exception:
                pass
            bg = hub.bg_dir()
            house = hub.bodies._house(bg, getattr(hub.args, "desk", None))
            kit = HERE.parent
            page = next((p for p in (kit / "skills" / "foreground-background" / "SKILL.md",
                                     kit / "bookshelf" / "your-house" / "Foreground and Background.md") if p.is_file()), None)
            taken = [str(as_dict(e).get("name") or "") for e in as_list(as_dict(live).get("machine"))]
            body = {"task": task[:4000], "cwd": str(house), "brief_page": str(page) if page else None, "taken": taken,
                    "from_card": req.get("from_card") if isinstance(req.get("from_card"), str) else None}
            s, o = b.call("POST", "/body", body, timeout=8)
            hub.bump()
            return self._json(s or 503, o or {"refused": "your agent did not answer"})
        if path == "/discern":
            if req.get("confirmed") is not True:
                return self._json(403, {"refused": "a judgment is a person's own act and needs the person's tap"})
            if req.get("verdict") not in ("chosen", "corrected", "rated"):
                return self._json(400, {"refused": "chosen, corrected or rated"})
            s, o = b.discern(req)
            return self._json(s, o)
        if path.startswith("/agent/pty/"):
            # the command line: a shell in the same home. Only on the computer itself, never the
            # phone door; opened only by the player's own tap; then only what the player types.
            if self.phone:
                return self._json(403, {"refused": "the command line is opened only on the computer itself"})
            if path == "/agent/pty/open" and req.get("confirmed") is not True:
                return self._json(403, {"refused": "the command line opens only on your own tap"})
            if path == "/agent/pty/open" and not b.ensure():
                return self._json(503, {"refused": "the command line could not start on this computer"})
            s, o = b.call("POST", path[len("/agent"):], req, timeout=5)
            return self._json(s or 409, o or {"refused": "your agent is resting"})
        if path in ("/agent/stop", "/agent/mode", "/agent/answer", "/agent/offer", "/agent/prefs"):
            if path == "/agent/answer" and req.get("answer") == "yes_kind":
                pass   # the host refuses it for an act that leaves the computer
            s, o = b.call("POST", path[len("/agent"):], req, timeout=5)
            if s is None:
                return self._json(409, {"refused": "your agent is resting"})
            hub.bump()
            return self._json(s, o)
        return self._json(404, {"refused": "not here"})

    def do_POST(self):
        path = urlparse(self.path).path
        if self.phone and path == "/phone/claim":
            if not self._guard(False):
                return
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "the code could not be read"})
            s, o = self.hub.phone.claim(req.get("code"), req.get("name"))
            return self._json(s, o)
        if not self._guard(True):
            return
        if path == "/voice":
            n = int(self.headers.get("Content-Length") or 0)
            s, o = self.hub.phone.voice(self, n)
            return self._json(s, o)
        if path == "/voice/say":
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "that could not be read"})
            s, o = render_voice(getattr(self.hub.args, "voice", None), req.get("text"))
            if s != 200:
                return self._json(s, o)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(o)))
            self.end_headers()
            self.wfile.write(o)
            return
        if path in ("/phone/listen", "/phone/pair", "/phone/claim"):
            if self.phone:
                return self._json(403, {"refused": "the phone door is opened only from the computer"})
            if path == "/phone/claim":
                return self._json(404, {"refused": "a phone claims its token on the phone door"})
            req = self._read_body() or {}
            if path == "/phone/listen":
                if req.get("confirmed") is not True:
                    return self._json(403, {"refused": "the phone door opens only on your own tap"})
                s, o = self.hub.phone.listen(bool(req.get("on")))
            else:
                s, o = self.hub.phone.pair()
            return self._json(s, o)
        if path in ("/say", "/keep"):
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "that could not be read"})
            s, o = self.hub.talk.say(req) if path == "/say" else self.hub.talk.keep(req)
            return self._json(s, o)
        if path in ("/mail/send", "/mail/read", "/mail/line"):
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "that could not be read"})
            s, o = self.hub.mail_post(path, req)
            return self._json(s, o)
        if path in ("/bodies/talk", "/bodies/window"):
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "that could not be read"})
            if path == "/bodies/window":
                if self.phone:
                    return self._json(403, {"refused": "a window is brought forward only from the computer itself"})
                s, o = self.hub.bodytalk.window(req)
            else:
                s, o = self.hub.bodytalk.say(req)
            return self._json(s, o)
        if path.startswith("/agent/") or path == "/discern":
            req = self._read_body()
            if req is None:
                return self._json(400, {"refused": "that could not be read"})
            return self._agent_post(path, req)
        if path == "/publish-sheet":
            return self._json(200, {"token": self.hub.publish_token()})
        if path != "/act":
            return self._json(404, {"refused": "not here"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(min(n, 1 << 20)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"refused": "the act could not be read"})
        status, out = self.hub.act(as_dict(req))
        return self._json(status, out)

    def do_DELETE(self):
        if not self._guard(True):
            return
        path = urlparse(self.path).path
        if path.startswith("/phone/"):
            dev = path[len("/phone/"):]
            if self.phone and dev != self.device:
                return self._json(403, {"refused": "a phone lets only itself go; the computer lets any go"})
            s, o = self.hub.phone.revoke(dev)
            return self._json(s, o)
        if not path.startswith("/act/"):
            return self._json(404, {"refused": "not here"})
        status, out = self.hub.undo(path[len("/act/"):])
        return self._json(status, out)


class PhoneHandler(Handler):
    """The phone door: the same HUD, reached over the private network. Its own Host and Origin;
    the device token on every route but the static files and /phone/claim."""
    phone = True
    device = None

    def _host_ok(self) -> bool:
        door = self.hub.phone
        return (self.headers.get("Host") or "") == f"{door.addr}:{door.port}"

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        door = self.hub.phone
        return origin is None or origin == f"https://{door.addr}:{door.port}"

    def _token_ok(self) -> bool:
        self.device = self.hub.phone.check(self.headers.get("X-HUD-Device") or "")
        return self.device is not None


class PhoneTrustHandler(SimpleHTTPRequestHandler):
    """The phone door's plain-http address: the trust page and this computer's authority, nothing
    else. Every other request is refused in one sentence (the door itself speaks only TLS)."""

    def log_message(self, fmt, *args):
        if Handler.hub and Handler.hub.args.verbose:
            super().log_message(fmt, *args)

    def _send(self, status, ctype, data, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _refuse(self):
        door = self.server.door
        self._send(403, "text/plain; charset=utf-8",
                   (f"This address only introduces the phone door; everything else is at "
                    f"https://{door.addr}:{door.port}/ once this phone trusts this computer.\n").encode())

    def do_GET(self):
        door = self.server.door
        u = urlparse(self.path)
        if (self.headers.get("Host") or "") != f"{door.addr}:{door.trust_port}":
            return self._refuse()
        if u.path == "/phone-door.crt":
            der = door.ca_der()
            if not der:
                return self._refuse()
            return self._send(200, "application/x-x509-ca-cert", der,
                              {"Content-Disposition": f'attachment; filename="phone-door-{door.addr}.crt"'})
        if u.path != "/":
            return self._refuse()
        code = (parse_qs(u.query).get("pair") or [""])[0]
        code = code if re.fullmatch(r"\d{6}", code) else ""
        t = door.trust or {}
        try:
            page = (HERE / "phone-trust.html").read_text(encoding="utf-8")
        except OSError:
            return self._refuse()
        import html as _html
        fp = t.get("fingerprint") or ""
        vals = {"fingerprint": fp, "fingerprint_short": fp[:23],
                "door": f"https://{door.addr}:{door.port}/" + (f"?pair={code}" if code else ""),
                "address": str(door.addr), "ca_expires": (t.get("ca_expires") or "")[:10],
                "code": code or "the six figures on your computer"}
        for k, v in vals.items():
            page = page.replace("{{" + k + "}}", _html.escape(v))
        self._send(200, "text/html; charset=utf-8", page.encode("utf-8"),
                   {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'"})

    def do_HEAD(self):
        return self._refuse()

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return   # a page closed mid-stream: nothing to say
        super().handle_error(request, client_address)


class PhoneTLSServer(QuietServer):
    """The phone door over TLS. The handshake is made in each request's own thread (a slow phone
    never holds the door's accept), with the context of the moment (renewed certificates take
    effect on the next connection)."""
    ctx = None

    def finish_request(self, request, client_address):
        import ssl
        request.settimeout(20)
        try:
            tls = self.ctx.wrap_socket(request, server_side=True)
        except (ssl.SSLError, OSError):
            return    # a phone that does not yet trust this computer ends here, quietly
        try:
            tls.settimeout(None)
            self.RequestHandlerClass(tls, client_address, self)
        except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                tls.close()
            except OSError:
                pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Example: python3 serve.py --fixture fresh   then open http://127.0.0.1:8765/")
    ap.add_argument("--hq", help="the home holon folder (its cells are read from cells/<name>/)")
    ap.add_argument("--shift-clock", action="store_true", help="with --fixture: move the sample's clock to now, keeping every interval (clockshift.py)")
    ap.add_argument("--fixture", help="serve fixtures/<name>.json as the state (fresh, empty, stale, unreadable, names-hidden, large, deal-chain, deal-rich)")
    ap.add_argument("--actor", help="the wearer, person:<handle> (default: the home holon's keeper)")
    ap.add_argument("--key", help="the person's own ssh ed25519 key (default ~/.ssh/lionsberg-person-<handle>); never an agent's")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--verbose", action="store_true", help="log every request")
    ap.add_argument("--agents", help="the player's agents file for the dock (default <HQ>/agents.json)")
    ap.add_argument("--proxy", default="http://127.0.0.1:8790", help="the proxy, on loopback, asked only for its health (with <HQ>/.proxy-token)")
    ap.add_argument("--routes", help="the proxy's routes.json (default engine/routes.json)")
    ap.add_argument("--vendors", help="the person's vendors file, read to say where each request went "
                                      "(default ~/.config/lionsberg/vendors.json); only names and hosts are read, never a key")
    ap.add_argument("--ask-wait", type=float, default=None, help="seconds before an unanswered ask goes into The Deal (default 900)")
    ap.add_argument("--phone", action="store_true",
                    help="allow the phone door: off by default; even with it, the door opens only on the player's tap in "
                         "this computer's HUD, bound only to the private-network address, with a one-time pairing code "
                         "and a revocable token per phone")
    ap.add_argument("--phone-address", help="the private-network address to bind the phone door to (default: found)")
    ap.add_argument("--phone-port", type=int, help="the phone door's https port (default --port + 1); its plain-http "
                    "trust page is the next port up")
    ap.add_argument("--bg", help="the folder of your agent's body folders (default <HQ>/bg)")
    ap.add_argument("--desk", help="the house's desk file (holder:, since: lines), naming which body holds the desk; "
                    "with it the prime is always shown, alive or not")
    ap.add_argument("--sessions", help="the harness's sessions folder (default ~/.claude/projects), read only for "
                    "which helpers each body has running: their description, model and start, never their words")
    ap.add_argument("--harness-sessions", help="the harness's registry of live sessions (default ~/.claude/sessions): "
                    "which session each process is, its status and its inbox; a key there is read only for a send "
                    "on the person's own tap, never kept or shown")
    ap.add_argument("--heartbeat", help="the prime's heartbeat file on this machine (default <HQ>/.heartbeat)")
    ap.add_argument("--usage-file", help="the harness's status file with its five-hour and seven-day usage "
                    "(default ~/.claude/statusline-last.json; only those figures are read)")
    ap.add_argument("--cost-ledger", help="the harness's cost ledger (default ~/.claude/cost-ledger.jsonl): only each "
                    "line's day, session, running cost and folder are read, to say what each body spent today")
    ap.add_argument("--speech", help="a local speech-to-words command for voice notes; the audio file path is its last argument")
    ap.add_argument("--voice", help="a local text-to-speech command that reads your agent's words aloud on a page that asks: "
                    "the text is its last argument and it prints the path of a new WAV file (the header's --voice contract)")
    args = ap.parse_args(argv)
    if not args.hq and not args.fixture:
        ap.error("give --hq PATH, or --fixture NAME to serve a sample state")
    hub = Hub(args)
    Handler.hub = hub
    threading.Thread(target=hub.watch, daemon=True).start()
    if args.phone and any(l.get("phone") == "on" for l in fold_layouts(read_record(hub.hq))):
        hub.phone.listen(True)    # the player's own layout says the door stays open across restarts
    srv = QuietServer(("127.0.0.1", args.port), Handler)
    srv.daemon_threads = True
    print(f"serve.py: the HUD is at http://127.0.0.1:{args.port}/  (wearer {hub.actor})", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
