#!/usr/bin/env python3
"""proxy.py: the Proxy layer of the Player+ kit, simplest honest version (schema v1).

A local HTTP proxy between an agent and the models. It speaks the Anthropic
Messages API shape on POST /v1/messages, so a Claude Code body can be pointed
at it with

    ANTHROPIC_BASE_URL=http://127.0.0.1:8790
    ANTHROPIC_CUSTOM_HEADERS="X-Proxy-Token: <contents of <holon>/.proxy-token>"

and it forwards each request to a vendor chosen by rule: the Anthropic API, an
OpenAI-compatible endpoint (a router service), or a local OpenAI-compatible
server (Ollama-class). It records where each request went as a `route` line
and takes an agent's note on an answer as a `note` line (never a `discern`,
which is a person's own judgment), in the shape of SCHEMA.md (the event line).

TWO FILES, TWO OWNERS
  vendors.json   WHERE requests may go and WITH WHICH KEY. It lives outside
                 every holon, in the person's own config directory:
                 ~/.config/lionsberg/vendors.json, owned by the person and mode
                 0600, written by the person's hand (or by an install, with
                 their yes). The proxy refuses to start on a vendors file that
                 is a symlink, not theirs, or readable or writable by others.
                 Each vendor pins kind, scheme, host, optional port and path,
                 and key_env. Template: engine/vendors.sample.json
                 (install -m 600 vendors.sample.json ~/.config/lionsberg/vendors.json).
  routes.json    WHICH vendor, by NAME, for which request. It may live in the
                 holon (pulled from others), so it names vendors only. Any
                 host, scheme, base_url, port, path, url, headers or key_env
                 anywhere inside it is refused at load, as is any key it does
                 not know. A planted routes.json can choose among the person's
                 own vendors and nothing else.

VENDOR RULES (vendors.json)
  scheme https to a named host; or http only to an IP literal that is loopback
  or an address this machine actually has (checked by binding to it, never by
  trusting a name: "localhost", *.ts.net or a 100.64.0.0/10 address that is not
  this machine's own are refused). key_env is null, or a non-empty name that
  starts with LIONSBERG_ or ends with _API_KEY. A named key that is unset at
  request time is an error (500 and a route line), never a fall-back. Only a
  vendor of kind anthropic with key_env null passes the client's own x-api-key
  or Authorization header through. "allowed_origins" (web origins that may call
  the proxy) also lives here.

THE PRIVATE TAG
  A request tagged private (X-Route-Tag: private; tags are trimmed and
  case-folded, so "Private " is private too) may go only to a vendor whose
  host is loopback or one of this machine's own addresses, checked again on
  every request. Every http vendor is checked again on every request too: if
  its address has left this machine, nothing is sent (502 and a route line). A rule that sends private elsewhere refuses to load; a private
  request that would leave the machine is refused (403 and a route line).

WHAT IT RECORDS (one line per event, JSON, append-only)
  route    every request that passed the gate: route id, rule, vendor, model
           asked and model sent, request size in bytes, tokens in and out when
           the vendor reports them, latency, status, whether it streamed,
           translation notes (fixed labels and counts only), conversation, turn
           and body ids from headers, and keyed digests (HMAC-SHA256 under the
           holon's salt, <holon>/.proxy-salt) of the request body and of the
           completion (see completion_digest), unless routes.json sets
           "hash_bodies": "none". A malformed request, a refused request and an
           upstream failure each get a route line too.
  note     every POST /discern: exactly the note type's fields, route (the
           route id), verdict ("chosen", "corrected" or "rated:<n>") and text
           (the caller's note, cut to 2000 characters). Type `note`, never `discern`: always an
           UNTRUSTED, UNSIGNED agent note that no fold counts as discernment.

WHAT IT NEVER RECORDS
  Prompt bodies, system prompts, completions, tool inputs or outputs, images,
  keys, auth headers, the token. Text the agent controls is never written as
  sent: a model name that is not 1-128 of [A-Za-z0-9._:/@-] is written as
  "nonconforming:" plus a keyed digest; block types the translation drops are
  written under fixed labels; header ids outside that character set are
  dropped. The digests are keyed: only a holder of the holon's salt (kept out
  of git) can confirm a guessed prompt.

DISCERNMENT IS THE PERSON'S, SIGNED BY THE PERSON
  The proxy holds no person token and writes no person's line. A person's
  discernment is a `discern` line signed with the person's own key, made by
  the ICE's act path after the person's gesture (the HUD server signs with
  ~/.ssh/lionsberg-person-<handle>, unlocked by the person through ssh-agent;
  the agent process has no access to that key). POST /discern, from any
  caller, writes only an untrusted, unsigned `note` by the proxy's agent:
  actor the configured agent, for its person, reason untrusted, no consent. A
  body naming actor, for, reason or consent is refused. One note per (route
  id, verdict) is written; a repeat answers {"duplicate": true}. `report`
  counts only the proxy's own route lines (--actor), first per route id, so a
  planted line cannot move a verdict to another vendor; it counts a verdict
  once per (route id, verdict), and only from a person's discern line whose
  signature verifies (record.py's verify_text) under the key the holon's
  record admits for that person; unverified lines are counted apart, and
  agent notes are listed in their own column.

LINKS ARE NEVER WRITTEN THROUGH
  Every write into the holon (proxy-log.jsonl, .gitignore, the token and salt
  files) opens each folder and the file with O_NOFOLLOW relative to its
  parent, so a link planted in a pulled holon is refused, never followed;
  record.py's writer does the same for record/<actor>.jsonl. Reads skip links,
  as record.read does. A line that cannot be written without following a link
  is not written, and the proxy says so on stderr.

THE GATE (every request, before its body is read)
  Host must be 127.0.0.1:<port> or localhost:<port> (blocks DNS rebinding). A
  request with an Origin header is refused unless vendors.json lists it. Every
  endpoint needs X-Proxy-Token with the token in <holon>/.proxy-token (0600,
  fresh on every start, gitignored). Then: Content-Length is required and
  capped (32 MB by default, --max-body-mb: the Messages API's own request
  ceiling, so a real request with images is never refused here), JSON nesting
  is capped at 100, and a body may hold at most 1,000,000 structural tokens
  ([ { ,), counted on the raw bytes before parsing, so 30 MB of tiny values is
  refused (413) before it becomes millions of objects; the client socket
  times out after 30 s; at most 32 connections are served at once
  (--max-connections).

HOLDING THE DOOR (no slot for a caller without a token)
  A connection must pass the gate within 5 s of accept, however slowly it
  drips its headers, or it is closed. When every slot is taken, the oldest
  connection still before the gate is closed to make room. At most 24 may wait
  before the gate from one address (on loopback, every caller is 127.0.0.1, so
  this is a second ceiling, not fairness). A token holder's headers arrive in
  milliseconds, so it always gets in.

NOTES AND REFUSALS DO NOT FLOOD THE RECORD
  A note may be written only on a route that came back from a vendor (a
  malformed or refused request makes no notable route id). The proxy's agent
  may write 30 notes a minute and the holon takes 1000 a day; beyond, 429, with
  one route line (rule note-cap) per minute of refusals. Requests refused
  before any upstream call write at most 120 route lines a minute; the rest are
  counted on the next line written.

UPSTREAM
  One opener, built with no ambient proxy settings (HTTP(S)_PROXY and system
  proxies are ignored) and refusing every redirect: a 3xx is answered 502 with
  a route line, and no other host ever answers as the model. The User-Agent is
  fixed ("player-plus-proxy"). Encoding asked: identity; an answer in any other
  encoding is refused. Answers from the Anthropic API stream through as they
  arrive (capped at 64 MB, cut at the stream deadline); OpenAI-shape answers
  are read whole (capped), translated, and, when the client asked to stream,
  re-sent as a synthesized stream with an x-proxy-note saying so.

ROUTING (routes.json)
  "rules" are tried in order; the first enabled rule whose "when" holds wins;
  else "default". Conditions, all of which must hold: model (exact or glob),
  tag (X-Route-Tag), min_bytes / max_bytes, hours [start, end) wrapping past
  midnight. A rule names {"vendor", "model"?} or a council. A rule naming a
  vendor the person has not defined is skipped and said at start. Keys whose
  names start with "about" are comments.

FUSION (a council instead of an oracle), off by default
  A rule with "council": [{"vendor", "model"}...] and "enabled": true sends the
  same request to every member at once and returns, within the rule's
  "deadline_s" (default 60, at most 600), one Messages response whose content
  is the first member in listed order that answered, plus
     "council": [{"route_id","vendor","model","status","latency_ms",
                  "message" | "error"}, ...]
  A council has 1 to 7 members (so at most 7 upstream calls for one request),
  no member repeated, and its rule must carry a tag condition: a council never
  takes untagged requests. Each member's answer is capped at 8 MB.
  Members past the deadline are listed with status 504. Members never receive
  the client's credential; a member of kind anthropic without its own key_env
  refuses to load. Each member gets its own route line ("<council id>.<n>").
  When the client streams, the stream is synthesized and the council field
  rides on the message object of message_start.

ENDPOINTS
  POST /v1/messages              the proxy (query strings pass through)
  POST /v1/messages/count_tokens to the first vendor of kind anthropic; recorded
  POST /discern                  {"route_id","verdict","rating"?,"note"?}
  GET  /routes/recent?n=20       this proxy's own latest route lines
  GET  /health                   {"ok": true}
  Headers read: X-Route-Tag, X-Conversation, X-Turn, X-Body (ids, never from
  the body) and X-Proxy-Token. None of them is forwarded to a vendor.

WHERE LINES GO
  engine/record.py, when it is a regular file in the engine folder (not a
  symlink), owned by this user and not writable by group or others, writes
  every line through record.append into <holon>/record/<actor>.jsonl (route
  lines signed when the agent's key is at hand; notes always unsigned).
  Otherwise, or if it fails, lines go to <holon>/proxy-log.jsonl in the
  SCHEMA.md shape with sig empty. Only this proxy's own actor's route lines are
  indexed for /discern and /routes/recent; lines from other actors' files are
  never taken as its own.

API VERSION ASSUMED
  The client's anthropic-version header passes through unchanged; when absent,
  routes.json "anthropic_version" (the sample says 2026-10-21, the newest dated
  version in the reference consulted at build time; 2023-06-01 is the
  long-standing one). Shapes follow the Messages API: system, messages, content
  blocks, usage, and the SSE events message_start .. message_stop.

CLI
  proxy.py serve --holon HQ_DIR [--port 8790] [--routes routes.json]
                 [--vendors ~/.config/lionsberg/vendors.json]
                 [--actor agent:<handle>] [--for person:<handle>]
                 [--max-body-mb 32] [--max-connections 32]
  proxy.py routes [--routes ...] [--vendors ...]
  proxy.py report --holon HQ_DIR [--actor agent:<handle>] [--conversation ID | --by-body]

Python 3.11+, standard library only. Runs under `python3 -I`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import hmac
import http.client
import importlib.util
import ipaddress
import json
import os
import re
import secrets
import socket
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
DEFAULT_ROUTES = ENGINE_DIR / "routes.json"
DEFAULT_VENDORS = "~/.config/lionsberg/vendors.json"
DEFAULT_PORT = 8790
DEFAULT_VERSION = "2026-10-21"
TAG_HEADER = "x-route-tag"
CONVERSATION_HEADER = "x-conversation"
TURN_HEADER = "x-turn"
BODY_HEADER = "x-body"
TOKEN_HEADER = "x-proxy-token"
LOG_NAME = "proxy-log.jsonl"
TOKEN_FILE = ".proxy-token"
SALT_FILE = ".proxy-salt"
USER_AGENT = "player-plus-proxy"
MIB = 1024 * 1024
MAX_BODY = 32 * MIB
DISCERN_MAX_BODY = 64 * 1024
MAX_UPSTREAM = 64 * MIB
PARSE_CAP = 16 * MIB
ERROR_CAP = 1 * MIB
MAX_CONNECTIONS = 32
CLIENT_TIMEOUT = 30
UPSTREAM_TIMEOUT = 300
STREAM_DEADLINE = 1800
COUNCIL_DEADLINE = 60
COUNCIL_MAX_DEADLINE = 600
JSON_MAX_DEPTH = 100
NOTE_MAX = 2000
HEADER_DEADLINE = 5             # seconds from accept to a request whose token has passed the gate
PER_SOURCE_PREAUTH = 24         # connections from one address still before the gate
MAX_JSON_ELEMENTS = 1_000_000   # structural tokens ([ { ,) in one request body, counted before parsing
NOTES_PER_MINUTE = 30           # notes the proxy's agent may write in any minute
NOTES_PER_DAY = 1000            # notes in one holon in one day
REFUSAL_LINES_PER_MINUTE = 120  # route lines for requests refused before any upstream call; beyond, counted
MAX_COUNCIL = 7                  # members of one council, and so upstream calls for one request
COUNCIL_MEMBER_CAP = 8 * MIB     # one member's answer, read whole
VERDICTS = ("chosen", "corrected", "rated")
LINE_ORDER = ("v", "id", "ts", "actor", "for", "holon", "type", "body",
              "links", "audience", "reason", "prev", "sig")
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate",
              "proxy-authorization", "te", "trailers", "transfer-encoding",
              "upgrade", "content-length", "content-encoding", "host"}
SAFE_RE = re.compile(r"^[A-Za-z0-9._:/@-]{1,128}$")
KEY_ENV_RE = re.compile(r"^(LIONSBERG_[A-Z0-9_]+|[A-Z0-9_]+_API_KEY)$")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
PATH_RE = re.compile(r"^(/[A-Za-z0-9._~-]+)*$")
VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ORIGIN_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d{1,5})?$")
FORBIDDEN_IN_ROUTES = {"vendors", "base_url", "host", "hosts", "scheme", "port", "path",
                       "url", "headers", "key_env", "allowed_origins"}
ROUTES_KEYS = {"rules", "default", "anthropic_version", "hash_bodies"}
RULE_KEYS = {"id", "when", "vendor", "model", "council", "enabled", "deadline_s"}
WHEN_KEYS = {"model", "tag", "min_bytes", "max_bytes", "hours"}
VENDOR_KEYS = {"kind", "scheme", "host", "port", "path", "key_env"}
KNOWN_BLOCKS = {"thinking", "redacted_thinking", "server_tool_use", "web_search_tool_result",
                "web_fetch_tool_result", "document", "search_result", "container_upload",
                "code_execution_tool_result", "bash_code_execution_tool_result",
                "mcp_tool_use", "mcp_tool_result"}


# ---------------------------------------------------------------- small helpers

def now_iso() -> str:
    """The local time with its offset, read from the clock."""
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def canonical(obj: dict) -> bytes:
    """SCHEMA.md canonical form: sorted keys, separators , and :, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def keyed_digest(salt: bytes, data: bytes) -> str:
    """HMAC-SHA256 of data under the holon's salt."""
    return hmac.new(salt or b"", data or b"", hashlib.sha256).hexdigest()


def strip_about(obj):
    """Drop comment fields (keys starting with 'about') at every depth."""
    if isinstance(obj, dict):
        return {k: strip_about(v) for k, v in obj.items()
                if not (isinstance(k, str) and k.startswith("about"))}
    if isinstance(obj, list):
        return [strip_about(v) for v in obj]
    return obj


def as_dict(x) -> dict:
    return x if isinstance(x, dict) else {}


def as_list(x) -> list:
    return x if isinstance(x, list) else []


def safe_label(value):
    """An id or label fit for disk: 1-128 of [A-Za-z0-9._:/@-]; anything else is None."""
    return value if isinstance(value, str) and SAFE_RE.match(value) else None


def safe_model(value, salt: bytes = b""):
    """A model name as recorded: itself when it conforms, else 'nonconforming:' + a keyed digest."""
    if value is None or value == "":
        return None
    if safe_label(value):
        return value
    raw = value if isinstance(value, str) else json.dumps(value, default=str)
    return "nonconforming:" + keyed_digest(salt, raw.encode("utf-8", "replace"))[:16]


def json_depth(obj) -> int:
    """The nesting depth of a parsed JSON value, counted without recursion."""
    deepest, stack = 0, [(obj, 1)]
    while stack:
        o, d = stack.pop()
        if isinstance(o, dict):
            deepest = max(deepest, d)
            stack.extend((v, d + 1) for v in o.values())
        elif isinstance(o, list):
            deepest = max(deepest, d)
            stack.extend((v, d + 1) for v in o)
    return deepest


def parse_json(raw: bytes, max_depth: int = JSON_MAX_DEPTH, max_elements: int | None = None):
    """(value, None) or (None, reason). Never raises on malformed or hostile input.

    max_elements bounds the structural tokens ([ { ,) counted on the raw bytes before
    parsing (in C, no copy), so a body of millions of tiny values is refused before it
    becomes millions of objects. Commas inside strings count too: an overestimate.
    """
    if max_elements is not None and raw and \
            raw.count(b",") + raw.count(b"[") + raw.count(b"{") > max_elements:
        return None, "too many JSON elements"
    try:
        value = json.loads(raw or b"null")
    except (ValueError, RecursionError):
        return None, "malformed JSON"
    if json_depth(value) > max_depth:
        return None, "JSON nested too deep"
    return value, None


def completion_digest(message: dict, salt: bytes = b"") -> str:
    """Keyed digest (HMAC-SHA256 under the holon's salt) of a Messages response's completion.

    Over the concatenation, in block order, of each text block's text and each
    tool_use block's input as compact JSON. A streamed answer is digested over
    its text_delta texts and input_json_delta partial_json strings as they
    arrived, which equals this for text-only answers. The text is never kept.
    """
    h = hmac.new(salt or b"", digestmod=hashlib.sha256)
    for b in as_list(as_dict(message).get("content")):
        b = as_dict(b)
        if b.get("type") == "text" and isinstance(b.get("text"), str):
            h.update(b["text"].encode("utf-8"))
        elif b.get("type") == "tool_use":
            h.update(json.dumps(b.get("input", {}), separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def is_local_address(host) -> bool:
    """True only for an IP literal that is loopback or assigned to this machine now.

    A name is never trusted. An address counts as this machine's own when a
    socket can bind to it, which the system allows only for its own addresses.
    """
    try:
        ip = ipaddress.ip_address(str(host).strip("[]"))
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if ip.is_unspecified or ip.is_multicast:
        return False
    fam = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
    try:
        with socket.socket(fam, socket.SOCK_DGRAM) as s:
            s.bind((str(ip), 0))
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- vendors (the person's file)

def validate_vendors(cfg) -> dict:
    """Check a vendors config and pin each vendor. Raises ValueError.

    Returns {"vendors": {name: {kind, scheme, host, port?, path, key_env,
    "_base_url", "_local"}}, "allowed_origins": [...]}. Idempotent.
    """
    cfg = strip_about(cfg)
    if not isinstance(cfg, dict):
        raise ValueError("vendors must be a JSON object")
    unknown = [k for k in cfg if not k.startswith("_") and k not in ("vendors", "allowed_origins")]
    if unknown:
        raise ValueError(f"unknown key(s): {', '.join(sorted(map(str, unknown)))}")
    vendors = cfg.get("vendors")
    if not isinstance(vendors, dict) or not vendors:
        raise ValueError("'vendors' must be a non-empty object")
    origins = as_list(cfg.get("allowed_origins", []))
    if not isinstance(cfg.get("allowed_origins", []), list) or \
            not all(isinstance(o, str) and ORIGIN_RE.match(o) for o in origins):
        raise ValueError("'allowed_origins' must be a list of origins like http://127.0.0.1:7777")
    out = {}
    for name, v in vendors.items():
        if not safe_label(name):
            raise ValueError(f"vendor name {name!r} must be 1-128 of A-Za-z0-9._:/@-")
        if not isinstance(v, dict):
            raise ValueError(f"vendor {name}: must be an object")
        extra = [k for k in v if not k.startswith("_") and k not in VENDOR_KEYS]
        if extra:
            raise ValueError(f"vendor {name}: unknown key(s) {', '.join(sorted(extra))}")
        kind, scheme, host = v.get("kind"), v.get("scheme"), v.get("host")
        if kind not in ("anthropic", "openai"):
            raise ValueError(f"vendor {name}: kind must be anthropic or openai")
        if scheme not in ("https", "http"):
            raise ValueError(f"vendor {name}: scheme must be https or http")
        if not isinstance(host, str) or not HOST_RE.match(host.strip("[]")):
            raise ValueError(f"vendor {name}: host must be a plain host name or IP address")
        port = v.get("port")
        if port is not None and (not isinstance(port, int) or isinstance(port, bool)
                                 or not 1 <= port <= 65535):
            raise ValueError(f"vendor {name}: port must be 1-65535")
        path = v.get("path", "") or ""
        if not isinstance(path, str) or not PATH_RE.match(path) or \
                any(seg in (".", "..") for seg in path.split("/")):
            raise ValueError(f"vendor {name}: path must look like /api/v1")
        key_env = v.get("key_env")
        if key_env is not None and (not isinstance(key_env, str) or not KEY_ENV_RE.match(key_env)):
            raise ValueError(f"vendor {name}: key_env must be null or a non-empty name starting "
                             "LIONSBERG_ or ending _API_KEY")
        local = is_local_address(host)
        if scheme == "http" and not local:
            raise ValueError(f"vendor {name}: plain http only to loopback or this machine's own "
                             "address, written as an IP (no names); use https elsewhere")
        hostpart = f"[{host.strip('[]')}]" if ":" in host.strip("[]") else host
        base = f"{scheme}://{hostpart}" + (f":{port}" if port else "") + path
        out[name] = {"kind": kind, "scheme": scheme, "host": host, "port": port, "path": path,
                     "key_env": key_env, "_base_url": base, "_local": local}
    return {"vendors": out, "allowed_origins": origins}


def load_vendors(path=None) -> dict:
    """Read the person's vendors file, refusing one that others could have written or read."""
    p = Path(os.path.expanduser(str(path or DEFAULT_VENDORS)))
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        raise SystemExit(f"no vendors file at {p}. Write it by hand from engine/vendors.sample.json: "
                         f"install -m 600 vendors.sample.json {p}")
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise SystemExit(f"vendors file refused: {p} must be a regular file, not a link")
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        raise SystemExit(f"vendors file refused: {p} is not owned by you")
    if st.st_mode & 0o077:
        raise SystemExit(f"vendors file refused: {p} must be mode 0600 (chmod 600 {p})")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        cfg = validate_vendors(raw)
    except (ValueError, RecursionError) as e:
        raise SystemExit(f"vendors file refused: {p}: {e}")
    cfg["_path"] = str(p)
    return cfg


# ---------------------------------------------------------------- routes (the holon's file)

def _forbidden_keys(obj, found=None):
    found = set() if found is None else found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and not k.startswith("_") and k in FORBIDDEN_IN_ROUTES:
                found.add(k)
            _forbidden_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _forbidden_keys(v, found)
    return found


def norm_tag(value) -> str:
    """A route tag as compared: trimmed and case-folded, so 'Private ' is 'private'."""
    return value.strip().casefold() if isinstance(value, str) else ""


def _tags_of(when) -> list:
    t = as_dict(when).get("tag")
    return [norm_tag(x) for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)]


def validate_routes(cfg, vendors: dict) -> dict:
    """Check a routes config against the person's vendors. Raises ValueError. Idempotent.

    Refuses any host-, scheme- or key-shaped field, any unknown key, a private
    rule whose targets are not on this machine, and a council member of kind
    anthropic without its own key. A rule naming an undefined vendor is kept
    but skipped (cfg["_skipped"] says which).
    """
    if not isinstance(cfg, dict):
        raise ValueError("routes must be a JSON object")
    if json_depth(cfg) > 20:
        raise ValueError("routes nested too deep")
    clean = strip_about(cfg)
    bad = _forbidden_keys(clean)
    if bad:
        raise ValueError("routes.json names vendors by name only; refused: " + ", ".join(sorted(bad)))
    unknown = [k for k in clean if not k.startswith("_") and k not in ROUTES_KEYS]
    if unknown:
        raise ValueError("unknown key(s): " + ", ".join(sorted(map(str, unknown))))
    vmap = as_dict(as_dict(vendors).get("vendors"))
    rules = clean.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("'rules' must be a list")
    if clean.get("hash_bodies", "hmac") not in ("hmac", "none"):
        raise ValueError("'hash_bodies' must be hmac or none")
    av = clean.get("anthropic_version")
    if av is not None and (not isinstance(av, str) or not VERSION_RE.match(av)):
        raise ValueError("'anthropic_version' must look like 2026-10-21")
    skipped = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            raise ValueError(f"rule {i + 1}: must be an object")
        extra = [k for k in r if not k.startswith("_") and k not in RULE_KEYS]
        if extra:
            raise ValueError(f"rule {i + 1}: unknown key(s) {', '.join(sorted(extra))}")
        rid = r.get("id")
        if rid is not None and not safe_label(rid):
            raise ValueError(f"rule {i + 1}: id must be 1-128 of A-Za-z0-9._:/@-")
        wextra = [k for k in as_dict(r.get("when")) if k not in WHEN_KEYS]
        if wextra:
            raise ValueError(f"rule {i + 1}: unknown condition(s) {', '.join(sorted(wextra))}")
        if "deadline_s" in r and (not isinstance(r["deadline_s"], (int, float))
                                  or isinstance(r["deadline_s"], bool) or r["deadline_s"] <= 0):
            raise ValueError(f"rule {i + 1}: deadline_s must be a positive number")
        members = as_list(r.get("council"))
        if "council" in r:
            if not members or len(members) > MAX_COUNCIL:
                raise ValueError(f"rule {rid or i + 1}: a council has 1 to {MAX_COUNCIL} members")
            pairs = [(as_dict(m).get("vendor"), as_dict(m).get("model")) for m in members]
            if len(set(pairs)) != len(pairs):
                raise ValueError(f"rule {rid or i + 1}: a council member is repeated")
            if not _tags_of(r.get("when")):
                raise ValueError(f"rule {rid or i + 1}: a council needs a tag condition; it never "
                                 "takes untagged requests")
        names = [as_dict(m).get("vendor") for m in members] if members else [r.get("vendor")]
        missing = [n for n in names if n not in vmap]
        if missing:
            skipped.append(rid or f"rule-{i + 1}")
            continue
        if members:
            for n in names:
                if vmap[n]["kind"] == "anthropic" and not vmap[n]["key_env"]:
                    raise ValueError(f"rule {rid or i + 1}: council member {n} has no key_env of its "
                                     "own; the client's credential never fans out")
        if "private" in _tags_of(r.get("when")):
            for n in names:
                if not vmap[n]["_local"]:
                    raise ValueError(f"rule {rid or i + 1}: the private tag may route only to a vendor "
                                     f"on this machine; {n} is not")
    d = as_dict(clean.get("default"))
    if d and d.get("vendor") not in vmap:
        skipped.append("default")
    cfg.clear()
    cfg.update(clean)
    cfg["_skipped"] = skipped
    return cfg


def load_routes(path, vendors: dict) -> dict:
    """Read routes.json and check it against the person's vendors."""
    p = Path(path) if path else DEFAULT_ROUTES
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"routes file not found: {p}")
    except (ValueError, RecursionError) as e:
        raise SystemExit(f"routes file is not JSON: {p}: {e}")
    try:
        cfg = validate_routes(raw, vendors)
    except ValueError as e:
        raise SystemExit(f"routes file refused: {p}: {e}")
    cfg["_path"] = str(p)
    return cfg


def _hour_in(hour: int, span) -> bool:
    span = as_list(span)
    if len(span) != 2:
        return False
    try:
        start, end = int(span[0]), int(span[1])
    except (TypeError, ValueError):
        return False
    if start == end:
        return True
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def rule_matches(when, model: str, tag: str, size: int, hour: int) -> bool:
    when = as_dict(when)
    if "model" in when:
        pat = when.get("model")
        if not isinstance(pat, str) or not fnmatch.fnmatchcase(model or "", pat):
            return False
    if "tag" in when and norm_tag(tag) not in _tags_of(when):
        return False
    for key, ok in (("min_bytes", lambda lim: size >= lim), ("max_bytes", lambda lim: size <= lim)):
        if key in when:
            try:
                if not ok(int(when[key])):
                    return False
            except (TypeError, ValueError):
                return False
    if "hours" in when and not _hour_in(hour, when.get("hours")):
        return False
    return True


def select_route(cfg: dict, vendors: dict, model: str, tag: str = "", size: int = 0,
                 hour: int | None = None) -> dict:
    """Pick the route for one request: {"rule", "targets": [{"vendor","model"}], "council", "deadline_s"}."""
    if hour is None:
        hour = _dt.datetime.now().hour
    vmap = as_dict(as_dict(vendors).get("vendors"))
    for i, rule in enumerate(as_list(as_dict(cfg).get("rules"))):
        rule = as_dict(rule)
        if rule.get("enabled", True) is False:
            continue
        if not rule_matches(rule.get("when"), model, tag, size, hour):
            continue
        rid = safe_label(rule.get("id")) or f"rule-{i + 1}"
        members = as_list(rule.get("council"))
        if members:
            targets = [{"vendor": as_dict(m).get("vendor"), "model": as_dict(m).get("model") or model}
                       for m in members]
            if targets and all(t["vendor"] in vmap for t in targets):
                deadline = min(float(rule.get("deadline_s") or COUNCIL_DEADLINE), COUNCIL_MAX_DEADLINE)
                return {"rule": rid, "targets": targets, "council": True, "deadline_s": deadline}
            continue
        if rule.get("vendor") in vmap:
            return {"rule": rid, "council": False,
                    "targets": [{"vendor": rule["vendor"], "model": rule.get("model") or model}]}
    d = as_dict(as_dict(cfg).get("default"))
    vendor = d.get("vendor") if d.get("vendor") in vmap else next(iter(vmap), None)
    if vendor is None:
        return {"rule": "none", "targets": [], "council": False}
    return {"rule": "default", "council": False,
            "targets": [{"vendor": vendor, "model": d.get("model") or model}]}


# ---------------------------------------------------------------- translation

STOP_TO_ANTHROPIC = {"stop": "end_turn", "length": "max_tokens",
                     "tool_calls": "tool_use", "function_call": "tool_use",
                     "content_filter": "refusal"}


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "\n\n".join(as_dict(b).get("text", "") for b in as_list(content)
                       if as_dict(b).get("type") == "text" and isinstance(as_dict(b).get("text"), str))


def _note(notes: dict, label: str):
    notes[label] = notes.get(label, 0) + 1


def anthropic_to_openai(req: dict, model: str):
    """Translate a Messages request to a chat-completions request, minimally.

    Returns (openai_request, notes). Notes use fixed labels and counts only:
    known block types by name, anything else as "dropped unrecognized block".
    """
    req = as_dict(req)
    notes: dict[str, int] = {}
    msgs = []
    system = req.get("system")
    if system:
        text = _text_of(system)
        if text:
            msgs.append({"role": "system", "content": text})
    for m in as_list(req.get("messages")):
        m = as_dict(m)
        role = m.get("role") if m.get("role") in ("user", "assistant") else "user"
        content = m.get("content")
        if isinstance(content, str):
            msgs.append({"role": role, "content": content})
            continue
        parts, calls, results = [], [], []
        for b in as_list(content):
            b = as_dict(b)
            t = b.get("type")
            if t == "text":
                parts.append({"type": "text", "text": b.get("text", "") if isinstance(b.get("text"), str) else ""})
            elif t == "image":
                src = as_dict(b.get("source"))
                if src.get("type") == "base64":
                    url = f"data:{src.get('media_type', 'image/png')};base64,{src.get('data', '')}"
                else:
                    url = src.get("url", "")
                parts.append({"type": "image_url", "image_url": {"url": url}})
            elif t == "tool_use":
                calls.append({"id": str(b.get("id", "")), "type": "function",
                              "function": {"name": str(b.get("name", "")),
                                           "arguments": json.dumps(b.get("input", {}))}})
            elif t == "tool_result":
                results.append({"role": "tool", "tool_call_id": str(b.get("tool_use_id", "")),
                                "content": _text_of(b.get("content"))})
            else:
                _note(notes, f"dropped {t} block" if t in KNOWN_BLOCKS else "dropped unrecognized block")
        msgs.extend(results)
        if role == "assistant":
            out = {"role": "assistant",
                   "content": "".join(p.get("text", "") for p in parts if p["type"] == "text") or None}
            if calls:
                out["tool_calls"] = calls
            if out["content"] is not None or calls:
                msgs.append(out)
        elif parts:
            if all(p["type"] == "text" for p in parts):
                msgs.append({"role": role, "content": "\n\n".join(p["text"] for p in parts)})
            else:
                msgs.append({"role": role, "content": parts})
    out = {"model": model, "messages": msgs}
    if isinstance(req.get("max_tokens"), int):
        out["max_tokens"] = req["max_tokens"]
    for k in ("temperature", "top_p"):
        if isinstance(req.get(k), (int, float)) and not isinstance(req.get(k), bool):
            out[k] = req[k]
    if as_list(req.get("stop_sequences")):
        out["stop"] = req["stop_sequences"]
    tools = []
    for tl in as_list(req.get("tools")):
        tl = as_dict(tl)
        if "input_schema" not in tl:
            _note(notes, "dropped server or built-in tool")
            continue
        tools.append({"type": "function", "function": {
            "name": str(tl.get("name", "")), "description": str(tl.get("description", "")),
            "parameters": tl.get("input_schema") or {"type": "object"}}})
    if tools:
        out["tools"] = tools
        tc = as_dict(req.get("tool_choice"))
        if tc.get("type") == "any":
            out["tool_choice"] = "required"
        elif tc.get("type") == "none":
            out["tool_choice"] = "none"
        elif tc.get("type") == "tool" and tc.get("name"):
            out["tool_choice"] = {"type": "function", "function": {"name": str(tc["name"])}}
        elif tc:
            out["tool_choice"] = "auto"
    return out, [f"{k}: {v}" for k, v in sorted(notes.items())]


def openai_to_anthropic(resp: dict, model: str, msg_id: str = "") -> dict:
    """Translate a chat-completions response to a Messages response."""
    resp = as_dict(resp)
    choice = as_dict((as_list(resp.get("choices")) or [{}])[0])
    message = as_dict(choice.get("message"))
    content = []
    text = message.get("content")
    if isinstance(text, list):
        text = "".join(str(as_dict(p).get("text", "")) for p in text)
    if isinstance(text, str) and text:
        content.append({"type": "text", "text": text})
    for c in as_list(message.get("tool_calls")):
        c = as_dict(c)
        fn = as_dict(c.get("function"))
        args = fn.get("arguments")
        inp, err = parse_json(args.encode("utf-8")) if isinstance(args, str) and args else ({}, None)
        if err:
            inp = {"arguments": args}
        content.append({"type": "tool_use", "id": str(c.get("id") or f"toolu_{uuid.uuid4().hex[:12]}"),
                        "name": str(fn.get("name", "")),
                        "input": inp if isinstance(inp, dict) else {"value": inp}})
    usage = as_dict(resp.get("usage"))

    def num(v):
        return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0

    return {"id": msg_id or f"msg_{uuid.uuid4().hex}",
            "type": "message", "role": "assistant", "content": content,
            "model": resp.get("model") if isinstance(resp.get("model"), str) else model,
            "stop_reason": STOP_TO_ANTHROPIC.get(choice.get("finish_reason"), "end_turn"),
            "stop_sequence": None,
            "usage": {"input_tokens": num(usage.get("prompt_tokens")),
                      "output_tokens": num(usage.get("completion_tokens"))}}


def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def synthesize_stream(message: dict) -> bytes:
    """A full Messages response as the server-sent events a streaming client expects.

    Extension fields on the message (council) ride on message_start's message.
    """
    message = as_dict(message)
    usage = as_dict(message.get("usage"))
    start = {k: v for k, v in message.items() if k not in ("content", "usage")}
    start.update({"content": [], "stop_reason": None, "stop_sequence": None,
                  "usage": {"input_tokens": int(usage.get("input_tokens") or 0), "output_tokens": 0}})
    out = [sse("message_start", {"type": "message_start", "message": start})]
    for i, b in enumerate(as_list(message.get("content"))):
        b = as_dict(b)
        if b.get("type") == "tool_use":
            head = {"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": {}}
            delta = {"type": "input_json_delta",
                     "partial_json": json.dumps(b.get("input", {}), separators=(",", ":"), ensure_ascii=False)}
        else:
            head = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": b.get("text", "")}
        out.append(sse("content_block_start", {"type": "content_block_start", "index": i, "content_block": head}))
        out.append(sse("content_block_delta", {"type": "content_block_delta", "index": i, "delta": delta}))
        out.append(sse("content_block_stop", {"type": "content_block_stop", "index": i}))
    out.append(sse("message_delta", {"type": "message_delta",
                                     "delta": {"stop_reason": message.get("stop_reason") or "end_turn",
                                               "stop_sequence": message.get("stop_sequence")},
                                     "usage": {"output_tokens": int(usage.get("output_tokens") or 0)}}))
    out.append(sse("message_stop", {"type": "message_stop"}))
    return b"".join(out)


class StreamScanner:
    """Reads a passing Messages SSE stream for usage and the keyed completion digest. Keeps nothing."""

    def __init__(self, salt: bytes = b""):
        self.buf = b""
        self.hash = hmac.new(salt or b"", digestmod=hashlib.sha256)
        self.tokens_in = None
        self.tokens_out = None

    def feed(self, chunk: bytes):
        self.buf += chunk or b""
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            self._line(line.strip())
        if len(self.buf) > 4 * MIB:   # a runaway line; stop scanning it
            self.buf = b""

    def _line(self, line: bytes):
        if not line.startswith(b"data:"):
            return
        d, err = parse_json(line[5:].strip() or b"{}", 32)
        if err or not isinstance(d, dict):
            return
        t = d.get("type")
        if t == "message_start":
            u = as_dict(as_dict(d.get("message")).get("usage"))
            if isinstance(u.get("input_tokens"), int):
                self.tokens_in = u["input_tokens"]
        elif t == "content_block_delta":
            delta = as_dict(d.get("delta"))
            piece = delta.get("text") if delta.get("type") == "text_delta" else (
                delta.get("partial_json") if delta.get("type") == "input_json_delta" else None)
            if isinstance(piece, str):
                self.hash.update(piece.encode("utf-8"))
        elif t == "message_delta":
            u = as_dict(d.get("usage"))
            if isinstance(u.get("output_tokens"), int):
                self.tokens_out = u["output_tokens"]
            if isinstance(u.get("input_tokens"), int) and self.tokens_in is None:
                self.tokens_in = u["input_tokens"]


# ---------------------------------------------------------------- the record

def load_record_module(folder: Path = ENGINE_DIR):
    """record.append from <folder>/record.py, checked as load_record does; or None."""
    mod = load_record(folder)
    fn = getattr(mod, "append", None) if mod is not None else None
    return fn if callable(fn) else None


def load_record(folder: Path = ENGINE_DIR):
    """record.append from a checked path, or None.

    The file must be exactly <folder>/record.py (the engine folder unless a test
    says otherwise): a regular file (not a link), owned by this user, not
    writable by group or others. Nothing on sys.path is consulted.
    """
    path = Path(folder) / "record.py"
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        print("proxy: record.py is not a regular file; writing the plain log", file=sys.stderr)
        return None
    if (hasattr(os, "getuid") and st.st_uid != os.getuid()) or st.st_mode & 0o022:
        print("proxy: record.py is not owned by you or is writable by others; writing the plain log",
              file=sys.stderr)
        return None
    try:
        spec = importlib.util.spec_from_file_location("player_plus_record", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # a broken record.py must not stop the proxy
        print(f"proxy: record.py did not load ({type(e).__name__}); writing the plain log", file=sys.stderr)
        return None
    return mod


class Recorder:
    """Writes route and discern lines, through record.append when it passes the checks."""

    def __init__(self, holon_dir, actor: str, for_: str, record_folder: Path | None = None):
        self.holon = Path(holon_dir)
        self.holon.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        info = {}
        try:
            info = as_dict(json.loads((self.holon / "holon.json").read_text(encoding="utf-8")))
        except (OSError, ValueError, RecursionError):
            pass
        self.holon_id = info.get("id") if isinstance(info.get("id"), str) else ""
        keeper = info.get("keeper") if isinstance(info.get("keeper"), str) else ""
        self.actor = actor if safe_label(actor) and actor.startswith("agent:") else "agent:proxy"
        self.for_ = for_ if safe_label(for_) and for_.startswith("person:") else (
            keeper if safe_label(keeper) and keeper.startswith("person:") else "person:unknown")
        self.log = self.holon / LOG_NAME
        self.prev: dict[str, str] = {}
        self.route_ids: dict[str, str] = {}     # route_id -> event id, this actor's lines only
        self.discerned: dict[tuple, str] = {}   # (route_id, verdict) -> event id
        self.recent: list[dict] = []
        self.notes_by_day: dict[str, int] = {}  # this actor's notes per local day
        self.note_times: list[float] = []       # monotonic times of notes in the last minute
        self.writer = load_record_module(record_folder or ENGINE_DIR)
        self.writer_opts: dict = {}
        for line in read_lines(self.holon):
            self._index(line)

    def _index(self, line: dict):
        line = as_dict(line)
        if line.get("actor") != self.actor:
            return       # never take another actor's lines as this proxy's own
        if line.get("id"):
            self.prev[self.actor] = line["id"]
        b = as_dict(line.get("body"))
        if line.get("type") == "route" and isinstance(b.get("route_id"), str):
            # only an answer that came back from a vendor can be noted: a refused or malformed
            # request makes no route id worth a note (they cost nothing to make)
            st = b.get("status")
            if b.get("vendor") and isinstance(st, int) and st < 400:
                self.route_ids[b["route_id"]] = line.get("id", "")
            self.recent.append(line)
            del self.recent[:-200]
        elif line.get("type") in ("note", "discern"):
            rid, verdict = note_key(line)
            if rid:
                self.discerned.setdefault((rid, verdict), line.get("id", ""))
            if line.get("type") == "note" and isinstance(line.get("ts"), str):
                day = line["ts"][:10]
                self.notes_by_day[day] = self.notes_by_day.get(day, 0) + 1

    def make_line(self, type_: str, body: dict, links=None, reason="delegated") -> dict:
        obj = {"v": 1, "ts": now_iso(), "actor": self.actor, "for": self.for_}
        if self.holon_id:
            obj["holon"] = self.holon_id
        obj["type"] = type_
        obj["body"] = {k: v for k, v in body.items() if v is not None and v != "" and v != [] and v != {}}
        if links:
            obj["links"] = links
        obj["audience"] = "holon"
        obj["reason"] = reason
        if self.prev.get(self.actor):
            obj["prev"] = self.prev[self.actor]
        obj["id"] = sha256_hex(canonical(obj))
        obj["sig"] = ""
        return {k: obj[k] for k in LINE_ORDER if k in obj}

    def write(self, type_: str, body: dict, links=None, reason="delegated", sign=None) -> dict:
        with self.lock:
            line = self.make_line(type_, body, links=links, reason=reason)
            written = False
            if self.writer is not None:
                kw = dict(self.writer_opts)
                if sign is False:
                    kw["sign"] = False
                try:
                    res = self.writer(str(self.holon), self.actor, self.for_, type_, body=line["body"],
                                      links=links or None, reason=reason, **kw)
                    got = as_dict(as_dict(res).get("line"))
                    if got.get("id"):
                        line, written = got, True
                except Exception as e:
                    print(f"proxy: record.append failed ({type(e).__name__}); writing {LOG_NAME}",
                          file=sys.stderr)
            if not written:
                try:
                    append_inside(self.holon, LOG_NAME, json.dumps(line, ensure_ascii=False) + "\n")
                except OSError:
                    print(f"proxy: {LOG_NAME} is a link or unwritable; the line was not written "
                          "(nothing is written through a link)", file=sys.stderr)
                    return line
            self._index(line)
            return line


def read_lines(holon_dir):
    """Every route, discern and note line in a holon: proxy-log.jsonl and record/*.jsonl; links skipped."""
    holon = Path(holon_dir)
    rels = [LOG_NAME]
    try:
        if not os.path.islink(holon / "record"):
            rels += ["record/" + f.name for f in sorted((holon / "record").glob("*.jsonl"))]
    except OSError:
        pass
    out = []
    for rel in rels:
        try:
            text = read_inside(holon, rel)    # a link is not read, as in record.read
        except OSError:
            continue
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            line, err = parse_json(raw.encode("utf-8"), 40)
            if not err and isinstance(line, dict) and line.get("type") in ("route", "discern", "note"):
                out.append(line)
    return out


_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)


def _open_dir_inside(holon: Path, parts, create=False) -> int:
    """A descriptor for <holon>/<parts...>, refusing a link at every step inside the holon.

    The holon folder itself is the person's own argument and may be reached through a
    link; every component below it is opened with O_NOFOLLOW relative to its parent, so
    no link planted in the holon (a pulled repository) is ever followed.
    """
    fd = os.open(str(holon), _DIR_FLAGS)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, _DIR_FLAGS | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def append_inside(holon: Path, rel: str, text: str, mode: int = 0o600):
    """Append text to <holon>/<rel> with O_NOFOLLOW on the file and every folder inside the holon.

    Raises OSError (ELOOP, ENOTDIR) when any of them is a link: nothing is written.
    """
    parts = [x for x in rel.split("/") if x]
    if not parts or any(x in (".", "..") for x in parts):
        raise OSError("not a path inside the holon")
    dfd = _open_dir_inside(Path(holon), parts[:-1], create=True)
    try:
        fd = os.open(parts[-1], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, mode, dir_fd=dfd)
    finally:
        os.close(dfd)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(text)


def read_inside(holon: Path, rel: str) -> str:
    """Read <holon>/<rel> without following a link anywhere inside the holon; raises OSError on one."""
    parts = [x for x in rel.split("/") if x]
    dfd = _open_dir_inside(Path(holon), parts[:-1])
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
    finally:
        os.close(dfd)
    with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_secret(path: Path, value: str):
    """Write a secret file readable by its owner only (0600), replacing any old one; never through a link."""
    dfd = os.open(str(path.parent), _DIR_FLAGS)
    try:
        try:
            os.unlink(path.name, dir_fd=dfd)    # removes a planted link itself, never its target
        except FileNotFoundError:
            pass
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    finally:
        os.close(dfd)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value + "\n")


def ensure_secrets(holon: Path):
    """A fresh agent token on every start; the holon's salt kept once made. Both 0600 and gitignored.

    Returns (token, salt_bytes).
    """
    token = secrets.token_hex(32)
    write_secret(holon / TOKEN_FILE, token)
    salt = ""
    try:
        st = os.lstat(holon / SALT_FILE)
        if stat.S_ISREG(st.st_mode) and st.st_mode & 0o077 == 0:
            salt = read_inside(holon, SALT_FILE).strip()
    except OSError:
        pass
    if len(salt) < 32:
        salt = secrets.token_hex(32)
        write_secret(holon / SALT_FILE, salt)
    try:
        have = read_inside(holon, ".gitignore").splitlines()
    except FileNotFoundError:
        have = []
    except OSError:
        have = None      # a link or worse: never written through
        print("proxy: .gitignore is a link; not touched. Add .proxy-token and .proxy-salt to it yourself.",
              file=sys.stderr)
    missing = [n for n in (TOKEN_FILE, SALT_FILE) if have is not None and n not in have]
    if missing:
        lead = "\n" if have and have[-1] != "" else ""
        try:
            append_inside(holon, ".gitignore", lead + "\n".join(missing) + "\n", 0o644)
        except OSError:
            print("proxy: .gitignore not written (a link?)", file=sys.stderr)
    return token, salt.encode("utf-8")


# ---------------------------------------------------------------- upstream calls

class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Follow no redirect: urllib then raises HTTPError with the 3xx code, which the proxy refuses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# no ambient proxies (env or system), no redirects
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirects())


class Refused(Exception):
    """A request the proxy will not send; status is what the client gets."""
    status = 502


class KeyMissing(Refused):
    status = 500


class NotLocal(Refused):
    status = 502


def credentials(vendor: dict, client_headers: dict, allow_client: bool = True) -> dict:
    """The auth header for one vendor. Raises KeyMissing when a named key is unset or empty."""
    env = vendor.get("key_env")
    if env:
        val = os.environ.get(env, "")
        if not val:
            raise KeyMissing("the key variable named for this vendor is not set")
        return {"x-api-key": val} if vendor.get("kind") == "anthropic" else {"authorization": f"Bearer {val}"}
    if vendor.get("kind") == "anthropic" and allow_client:
        return {h: client_headers[h] for h in ("x-api-key", "authorization") if client_headers.get(h)}
    return {}


def vendor_request(vendor: dict, client_headers: dict, body: dict | None, raw: bytes, query: str,
                   cfg: dict, path_suffix: str = "/v1/messages", allow_client: bool = True):
    """Build the urllib Request for one vendor. Returns (request, notes). Raises Refused.

    An http vendor is checked again here, on every request, to be on this machine: if its
    address has left (a network change), the request and its key are not sent.
    """
    if vendor.get("scheme") == "http" and not is_local_address(vendor.get("host")):
        raise NotLocal("the http vendor's address is no longer on this machine; refused")
    headers = {"content-type": "application/json", "accept-encoding": "identity",
               "user-agent": USER_AGENT}
    headers.update(credentials(vendor, client_headers, allow_client))
    notes = []
    if vendor.get("kind") == "anthropic":
        url = vendor["_base_url"] + path_suffix + (("?" + query) if query else "")
        headers["anthropic-version"] = client_headers.get("anthropic-version") or \
            cfg.get("anthropic_version") or DEFAULT_VERSION
        if client_headers.get("anthropic-beta"):
            headers["anthropic-beta"] = client_headers["anthropic-beta"]
        if client_headers.get("accept"):
            headers["accept"] = client_headers["accept"]
        data = raw if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    else:
        url = vendor["_base_url"] + "/chat/completions"
        oreq, notes = anthropic_to_openai(as_dict(body), as_dict(body).get("model", ""))
        oreq["stream"] = False
        data = json.dumps(oreq, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(url, data=data, headers=headers, method="POST"), notes


def read_capped(f, cap: int):
    """(bytes, over) reading at most cap bytes."""
    data = f.read(cap + 1)
    return (data[:cap], True) if len(data) > cap else (data, False)


def open_upstream(request, timeout):
    """(response, None) or (None, {"status", "note", "payload"?, "ctype"?}). Refuses redirects and encodings."""
    try:
        resp = OPENER.open(request, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            if 300 <= e.code < 400:
                return None, {"status": 502, "note": "upstream redirect refused"}
            enc = ((e.headers.get("content-encoding") if e.headers else None) or "identity").lower()
            payload = b""
            if enc == "identity":
                try:
                    payload, _ = read_capped(e, ERROR_CAP)
                except OSError:
                    payload = b""
            ctype = (e.headers.get("content-type") if e.headers else None) or "application/json"
            return None, {"status": e.code, "note": f"upstream HTTP {e.code}", "payload": payload,
                          "ctype": ctype}
        finally:
            e.close()
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        if isinstance(e, TimeoutError) or isinstance(getattr(e, "reason", None), TimeoutError):
            return None, {"status": 504, "note": "upstream timed out"}
        return None, {"status": 502, "note": f"upstream unreachable: {type(e).__name__}"}
    enc = (resp.headers.get("content-encoding") or "identity").lower()
    if enc != "identity":
        resp.close()
        return None, {"status": 502, "note": "upstream sent an encoding not asked for"}
    return resp, None


def call_once(vendor: dict, client_headers: dict, req_body: dict, model: str, cfg: dict,
              timeout: float = UPSTREAM_TIMEOUT, allow_client: bool = True, cap: int | None = None):
    """Non-streaming call to one vendor. Returns a result dict with a Messages-shaped message or an error."""
    body = dict(req_body)
    body["model"] = model
    body.pop("stream", None)
    t0 = time.monotonic()
    result = {"model": model, "notes": []}
    try:
        request, notes = vendor_request(vendor, client_headers, body, b"", "", cfg, allow_client=allow_client)
    except Refused as e:
        result.update(status=e.status, error=str(e), latency_ms=0)
        return result
    result["notes"] = notes
    resp, err = open_upstream(request, timeout)
    if err:
        result.update(status=err["status"], error=err["note"])
    else:
        with resp:
            try:
                data, over = read_capped(resp, cap or MAX_UPSTREAM)
            except OSError as e:
                data, over = b"", False
                result["error"] = "upstream timed out" if isinstance(e, TimeoutError) else \
                    f"upstream read failed: {type(e).__name__}"
            result["status"] = resp.status
        if over:
            result.update(status=502, error="upstream answer over the cap")
        elif "error" not in result:
            payload, perr = parse_json(data)
            if perr or not isinstance(payload, dict):
                result.update(status=502, error="upstream answer not JSON")
            else:
                msg = payload if vendor.get("kind") == "anthropic" else openai_to_anthropic(payload, model)
                result["message"] = as_dict(msg)
        if "error" in result and result.get("status", 200) < 400:
            result["status"] = 502
    result["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return result


def anthropic_error(kind: str, message: str) -> bytes:
    return json.dumps({"type": "error", "error": {"type": kind, "message": message}}).encode()


# ---------------------------------------------------------------- the server

class BoundedServer(ThreadingHTTPServer):
    """A threading server with a fixed number of slots that a caller without a token cannot hold.

    - At most max_connections are served at once.
    - A connection whose token has not passed the gate within header_deadline seconds of
      accept is closed (a reaper checks twice a second), however slowly it drips headers.
    - When every slot is taken, the oldest connection still before the gate is closed to
      make room, so a token holder, whose headers arrive in milliseconds, always gets in.
    - No more than per_source connections from one address may wait before the gate. On
      loopback every caller is 127.0.0.1, so there this is a second ceiling on waiting
      connections rather than a fairness rule; the deadline and the eviction carry the load.
    """

    daemon_threads = True

    def __init__(self, addr, handler, max_connections=MAX_CONNECTIONS, header_deadline=HEADER_DEADLINE,
                 per_source=PER_SOURCE_PREAUTH):
        self._slots = threading.BoundedSemaphore(max(1, int(max_connections)))
        self._lock = threading.Lock()
        self._preauth = {}            # socket -> (address, accepted at)
        self._cut = set()             # sockets closed by the deadline or an eviction
        self.header_deadline = float(header_deadline)
        self.per_source = max(1, int(per_source))
        self._closing = False
        super().__init__(addr, handler)
        threading.Thread(target=self._reap, daemon=True).start()

    def _close_sock(self, sock):
        with self._lock:
            self._cut.add(sock)
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def was_cut(self, sock) -> bool:
        """True for a connection the deadline or an eviction closed: it gets no answer."""
        with self._lock:
            return sock in self._cut

    def _evict_oldest(self, source=None) -> bool:
        with self._lock:
            waiting = [(t, sk) for sk, (a, t) in self._preauth.items() if source is None or a == source]
            if not waiting:
                return False
            _, sk = min(waiting, key=lambda x: x[0])
            self._preauth.pop(sk, None)
        self._close_sock(sk)
        return True

    def _reap(self):
        while not self._closing:
            time.sleep(0.5)
            now = time.monotonic()
            with self._lock:
                late = [sk for sk, (a, t) in self._preauth.items() if now - t > self.header_deadline]
                for sk in late:
                    self._preauth.pop(sk, None)
            for sk in late:
                self._close_sock(sk)

    def authed(self, sock):
        """The gate passed: this connection is no longer subject to the header deadline or eviction."""
        with self._lock:
            self._preauth.pop(sock, None)

    def process_request(self, request, client_address):
        source = client_address[0] if client_address else None
        with self._lock:
            from_source = sum(1 for a, _ in self._preauth.values() if a == source)
        if from_source >= self.per_source:
            self._evict_oldest(source)
        if not self._slots.acquire(blocking=False):
            if not (self._evict_oldest() and self._slots.acquire(timeout=1.0)):
                self.shutdown_request(request)
                return
        with self._lock:
            self._preauth[request] = (source, time.monotonic())
        try:
            super().process_request(request, client_address)
        except Exception:
            self.authed(request)
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.authed(request)
            with self._lock:
                self._cut.discard(request)
            self._slots.release()

    def server_close(self):
        self._closing = True
        super().server_close()


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "player-plus-proxy/1"
    sys_version = ""
    protocol_version = "HTTP/1.0"   # one request per connection; streams end with the connection

    def setup(self):
        self.timeout = getattr(self.server, "client_timeout", CLIENT_TIMEOUT)
        self._sent = False
        self._pending = None     # the route line of the request in hand, written before its answer
        super().setup()

    def log_message(self, fmt, *args):
        """Quiet by default; --verbose prints request lines (method and path, never bodies)."""
        if getattr(self.server, "verbose", False):
            sys.stderr.write("proxy: " + (fmt % args) + "\n")

    # -- plumbing
    @property
    def cfg(self):
        return self.server.routes

    @property
    def rec(self) -> Recorder:
        return self.server.recorder

    def _headers_lower(self):
        return {k.lower(): v for k, v in self.headers.items()}

    def _send(self, status: int, payload: bytes, ctype="application/json", extra=None):
        # A length-delimited answer lets the client go before this handler ends, so the
        # request's route line is written first: whoever reads the record after the answer
        # finds it. (Streams end with the connection, after the line, so they need no hook.)
        if self._pending is not None:
            self._finish(self._pending)
        try:
            self.send_response(status)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(payload)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self._sent = True
            self.wfile.write(payload)
        except OSError:
            self._sent = True       # the client is gone; nothing more to say
            self.close_connection = True

    def _json(self, status: int, obj, extra=None):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), extra=extra)

    def _err(self, status: int, kind: str, message: str, extra=None):
        self._send(status, anthropic_error(kind, message), extra=extra)

    # -- the gate: Host, Origin, token; before any body is read
    def _gate(self) -> bool:
        if hasattr(self.server, "was_cut") and self.server.was_cut(self.request):
            self.close_connection = True
            return False
        port = self.server.server_address[1]
        host = (self.headers.get("host") or "").strip().lower()
        if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            self._err(403, "permission_error", "Host must be 127.0.0.1 or localhost with the port")
            return False
        origin = self.headers.get("origin")
        if origin is not None and origin not in self.server.allowed_origins:
            self._err(403, "permission_error", "requests from a web page are refused")
            return False
        given = (self.headers.get(TOKEN_HEADER) or "").strip()
        if not (given and hmac.compare_digest(given.encode(), self.server.agent_token.encode())):
            self._err(401, "authentication_error", f"X-Proxy-Token required (see {TOKEN_FILE})")
            return False
        if hasattr(self.server, "authed"):
            self.server.authed(self.request)
        return True

    def _read_body(self, cap: int):
        """(raw, None) or (None, (status, note)). Content-Length required and capped."""
        try:
            n = int(self.headers.get("content-length") or "")
        except ValueError:
            return None, (411, "Content-Length required")
        if n < 0:
            return None, (400, "bad Content-Length")
        if n > cap:
            return None, (413, "request body over the cap")
        try:
            raw = self.rfile.read(n) if n else b""
        except OSError:
            return None, (408, "request body not received in time")
        if len(raw) < n:
            return None, (400, "request body shorter than declared")
        return raw, None

    # -- routes
    def do_GET(self):
        if not self._gate():
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/health":
            return self._json(200, {"ok": True})
        if parsed.path == "/routes/recent":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                n = max(1, min(200, int((q.get("n") or ["20"])[0])))
            except ValueError:
                n = 20
            return self._json(200, {"routes": self.rec.recent[-n:]})
        self._err(404, "not_found_error", "no such path")

    def do_POST(self):
        if not self._gate():
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/discern":
            return self._discern()
        if parsed.path in ("/v1/messages", "/v1/messages/count_tokens"):
            return self._proxy(parsed.path, parsed.query)
        self._err(404, "not_found_error", "no such path")

    # -- discern: always an untrusted, unsigned agent note
    def _discern(self):
        raw, err = self._read_body(DISCERN_MAX_BODY)
        if err:
            return self._json(err[0], {"error": err[1]})
        if "application/json" not in (self.headers.get("content-type") or ""):
            return self._json(415, {"error": "content-type must be application/json"})
        d, perr = parse_json(raw, 4)
        if perr or not isinstance(d, dict):
            return self._json(400, {"error": perr or "body must be a JSON object"})
        refused = [k for k in ("actor", "for", "reason", "consent") if k in d]
        if refused:
            return self._json(400, {"error": "not taken from the caller: " + ", ".join(refused)})
        unknown = [k for k in d if k not in ("route_id", "verdict", "rating", "note")]
        if unknown:
            return self._json(400, {"error": "unknown field(s)"})
        rid = safe_label(d.get("route_id"))
        if rid is None or rid not in self.rec.route_ids:
            return self._json(404, {"error": "unknown route_id"})
        verdict = d.get("verdict")
        if verdict not in VERDICTS:
            return self._json(400, {"error": "verdict must be chosen, corrected or rated"})
        rating = d.get("rating")
        if rating is not None and (not isinstance(rating, int) or isinstance(rating, bool)
                                   or not 1 <= rating <= 10):
            return self._json(400, {"error": "rating must be an integer 1-10"})
        if verdict == "rated" and rating is None:
            return self._json(400, {"error": "a rated verdict needs a rating"})
        note = d.get("note")
        if note is not None and not isinstance(note, str):
            return self._json(400, {"error": "note must be a string"})
        if isinstance(note, str) and len(note) > NOTE_MAX:
            note = note[:NOTE_MAX]
        first = self.rec.discerned.get((rid, verdict))
        if first:
            return self._json(200, {"ok": True, "duplicate": True, "id": first})
        refused = self._note_cap()
        if refused:
            return self._json(429, {"error": refused})
        # exactly the note type's fields (types.json): route, verdict, text; a rating rides in
        # the verdict as "rated:<n>"
        line = self.rec.write("note", {"route": rid,
                                       "verdict": f"rated:{rating}" if verdict == "rated" else verdict,
                                       "text": note},
                              reason="untrusted", sign=False,
                              links={"answers": [self.rec.route_ids[rid]]})
        self._json(200, {"ok": True, "id": line.get("id")})

    def _note_cap(self):
        """None, or why a note is refused: per minute for the proxy's agent, per day for the holon.

        The first refusal in each minute writes one route line (rule note-cap, status 429);
        further refusals that minute are counted on it, not written one by one.
        """
        srv, rec = self.server, self.rec
        now = time.monotonic()
        with rec.lock:
            rec.note_times[:] = [t for t in rec.note_times if now - t < 60]
            today = _dt.datetime.now().astimezone().date().isoformat()
            why = None
            if len(rec.note_times) >= srv.notes_per_minute:
                why = f"notes over the cap of {srv.notes_per_minute} a minute; refused"
            elif rec.notes_by_day.get(today, 0) >= srv.notes_per_day:
                why = f"notes over the cap of {srv.notes_per_day} a day in this holon; refused"
            if why is None:
                rec.note_times.append(now)
                return None
            minute = int(time.time() // 60)
            first = srv.note_refusal_minute != minute
            srv.note_refusal_minute = minute
        if first:
            self.rec.write("route", {"route_id": uuid.uuid4().hex[:16], "rule": "note-cap", "status": 429,
                                     "notes": [why, "further refusals this minute are not written one by one"]})
        return why

    # -- the proxy
    def _new_rec(self, rid, rule="refused", target=None, model_asked=None, size=0, stream=False,
                 council=None):
        target = target or {}
        return {"route_id": rid, "rule": rule, "vendor": target.get("vendor"),
                "model_asked": model_asked, "model": safe_model(target.get("model"), self.server.salt),
                "bytes": size, "stream": stream, "req": None, "council": council, "status": None,
                "notes": [], "tin": None, "tout": None, "comp": None, "t0": time.monotonic(),
                "latency": None, "done": False}

    def _finish(self, rec):
        if rec["done"]:
            return
        rec["done"] = True
        if not isinstance(rec["status"], int):
            rec["status"] = 502
            rec["notes"].append("proxy error before an answer")
        latency = rec["latency"] if rec["latency"] is not None else int((time.monotonic() - rec["t0"]) * 1000)
        if not rec["vendor"]:    # refused before any upstream call: at most N lines a minute
            minute = int(time.time() // 60)
            with self.rec.lock:
                if self.server.refusal_minute != minute:
                    self.server.refusal_minute, self.server.refusal_count = minute, 0
                self.server.refusal_count += 1
                if self.server.refusal_count > REFUSAL_LINES_PER_MINUTE:
                    self.server.refusals_unrecorded += 1
                    return
                carried, self.server.refusals_unrecorded = self.server.refusals_unrecorded, 0
            if carried:
                rec["notes"].append(f"{carried} earlier refusals were counted, not written one by one")
        hashing = self.cfg.get("hash_bodies", "hmac") != "none"
        body = {"route_id": rec["route_id"], "rule": rec["rule"], "vendor": rec["vendor"],
                "model_asked": rec["model_asked"], "model": rec["model"],
                "size": {k: v for k, v in (("bytes", rec["bytes"]), ("tokens_in", rec["tin"]),
                                           ("tokens_out", rec["tout"])) if isinstance(v, int)},
                "latency_ms": latency, "status": rec["status"], "stream": bool(rec["stream"]),
                "tag": self._tag_label, "council": rec["council"], "notes": rec["notes"] or None,
                "conversation": self._conversation, "turn": self._turn, "body": self._body,
                "request_hmac": rec["req"] if hashing else None,
                "completion_hmac": rec["comp"] if hashing else None}
        try:
            self.rec.write("route", body)
        except OSError as e:
            print(f"proxy: route line not written ({type(e).__name__})", file=sys.stderr)

    def _proxy(self, path: str, query: str):
        hdrs = self._headers_lower()
        self._tag_raw = norm_tag(hdrs.get(TAG_HEADER, ""))
        self._tag_label = safe_label(self._tag_raw)
        # ids from headers only, never the body, and only in the safe character set
        self._conversation = safe_label(hdrs.get(CONVERSATION_HEADER))
        self._turn = safe_label(hdrs.get(TURN_HEADER))
        self._body = safe_label(hdrs.get(BODY_HEADER))
        rid = uuid.uuid4().hex[:16]
        try:
            declared = int(self.headers.get("content-length") or 0)
        except ValueError:
            declared = 0
        rec = self._new_rec(rid, size=max(0, declared))
        self._pending = rec
        try:
            raw, err = self._read_body(self.server.max_body)
            if err:
                rec["status"] = err[0]
                rec["notes"].append(err[1])
                return self._err(err[0], "invalid_request_error", err[1], {"x-route-id": rid})
            rec["bytes"] = len(raw)
            body, perr = parse_json(raw, max_elements=self.server.max_json_elements)
            if perr or not isinstance(body, dict):
                code = 413 if perr == "too many JSON elements" else 400
                rec["status"] = code
                rec["notes"].append(perr or "body must be a JSON object")
                return self._err(code, "invalid_request_error", perr or "body must be a JSON object",
                                 {"x-route-id": rid})
            model_asked = body.get("model") if isinstance(body.get("model"), str) else ""
            rec["model_asked"] = safe_model(model_asked, self.server.salt)
            rec["stream"] = body.get("stream") is True
            if self.cfg.get("hash_bodies", "hmac") != "none":
                rec["req"] = keyed_digest(self.server.salt, raw)
            if path == "/v1/messages/count_tokens":
                return self._count_tokens(rec, raw, query, hdrs)
            route = select_route(self.cfg, self.server.vendors, model_asked, self._tag_raw, len(raw))
            rec["rule"] = route["rule"]
            if not route["targets"]:
                rec["status"] = 503
                rec["notes"].append("no vendor defined")
                return self._err(503, "api_error", "no vendor defined in vendors.json", {"x-route-id": rid})
            vmap = self.server.vendors["vendors"]
            if self._tag_raw == "private":
                off = [t["vendor"] for t in route["targets"]
                       if not is_local_address(vmap[t["vendor"]]["host"])]
                if off:
                    t = route["targets"][0]
                    rec.update(vendor=t["vendor"], model=safe_model(t["model"], self.server.salt), status=403)
                    rec["notes"].append("private request would leave this machine; refused")
                    return self._err(403, "permission_error",
                                     "a private request may go only to a vendor on this machine",
                                     {"x-route-id": rid})
            if route["council"]:
                rec["done"] = True    # each member writes its own line
                return self._council(route, rid, body, hdrs, rec)
            target = route["targets"][0]
            rec["vendor"] = target["vendor"]
            rec["model"] = safe_model(target["model"], self.server.salt)
            vendor = vmap[target["vendor"]]
            if vendor["kind"] == "anthropic":
                return self._anthropic(rec, target, vendor, body, raw, query, hdrs, model_asked)
            return self._openai(rec, target, vendor, body, hdrs)
        except Exception as e:   # never leave a spent request without an answer and a line
            rec["notes"].append(f"proxy error: {type(e).__name__}")
            if not isinstance(rec["status"], int):
                rec["status"] = 500
            print(f"proxy: request failed ({type(e).__name__})", file=sys.stderr)
            if not self._sent:
                try:
                    self._err(500, "api_error", "the proxy failed on this request", {"x-route-id": rid})
                except OSError:
                    pass
        finally:
            self._finish(rec)

    def _openai(self, rec, target, vendor, body, hdrs):
        res = call_once(vendor, hdrs, body, target["model"], self.cfg)
        rec["notes"].extend(res.get("notes") or [])
        if rec["stream"]:
            rec["notes"].append("upstream non-streaming; stream synthesized")
        rec["latency"] = res.get("latency_ms")
        extra = {"x-route-id": rec["route_id"]}
        if rec["notes"]:
            extra["x-proxy-note"] = "; ".join(rec["notes"])
        if "message" in res:
            msg = res["message"]
            u = as_dict(msg.get("usage"))
            rec.update(status=res.get("status", 200), tin=u.get("input_tokens"), tout=u.get("output_tokens"),
                       comp=completion_digest(msg, self.server.salt))
            if rec["stream"]:
                return self._send(200, synthesize_stream(msg), "text/event-stream", extra)
            return self._json(200, msg, extra)
        rec["status"] = res.get("status", 502)
        rec["notes"].append(res.get("error", "upstream failed"))
        return self._err(rec["status"], "api_error", res.get("error", "upstream failed"), extra)

    def _anthropic(self, rec, target, vendor, body, raw, query, hdrs, model_asked):
        new_body = None
        if target["model"] and target["model"] != model_asked:
            new_body = dict(body)
            new_body["model"] = target["model"]
        extra = {"x-route-id": rec["route_id"]}
        try:
            request, _ = vendor_request(vendor, hdrs, new_body, raw, query, self.cfg)
        except Refused as e:
            rec["status"] = e.status
            rec["notes"].append(str(e))
            return self._err(e.status, "api_error", str(e), extra)
        resp, err = open_upstream(request, UPSTREAM_TIMEOUT)
        if err:
            rec["latency"] = int((time.monotonic() - rec["t0"]) * 1000)
            rec["status"] = err["status"]
            rec["notes"].append(err["note"])
            if err.get("payload"):
                return self._send(err["status"], err["payload"], err.get("ctype", "application/json"), extra)
            return self._err(err["status"], "api_error", err["note"], extra)
        with resp:
            ctype = resp.headers.get("content-type", "application/json")
            is_sse = "text/event-stream" in ctype
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.send_header("x-route-id", rec["route_id"])
            self.end_headers()
            self._sent = True
            rec["status"] = resp.status
            scan = StreamScanner(self.server.salt) if is_sse else None
            buf, total, parse_over = bytearray(), 0, False
            deadline = rec["t0"] + STREAM_DEADLINE
            while True:
                if time.monotonic() > deadline:
                    rec["notes"].append("stream deadline reached; cut")
                    break
                try:
                    chunk = resp.read1(65536)
                except OSError:
                    rec["notes"].append("upstream read failed")
                    break
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPSTREAM:
                    rec["notes"].append("upstream answer over the cap; cut")
                    break
                if scan is not None:
                    scan.feed(chunk)
                elif len(buf) + len(chunk) <= PARSE_CAP:
                    buf.extend(chunk)
                else:
                    parse_over = True
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except OSError:
                    rec["status"] = 499   # the client went away
                    break
            rec["latency"] = int((time.monotonic() - rec["t0"]) * 1000)
            if scan is not None:
                rec.update(tin=scan.tokens_in, tout=scan.tokens_out, comp=scan.hash.hexdigest())
            elif not parse_over:
                msg, perr = parse_json(bytes(buf))
                if not perr and isinstance(msg, dict):
                    u = as_dict(msg.get("usage"))
                    rec.update(tin=u.get("input_tokens"), tout=u.get("output_tokens"),
                               comp=completion_digest(msg, self.server.salt))
            else:
                rec["notes"].append("answer too large to digest")

    def _council(self, route, cid, body, hdrs, parent):
        targets = route["targets"]
        vmap = self.server.vendors["vendors"]
        results = [None] * len(targets)
        deadline = float(route.get("deadline_s") or COUNCIL_DEADLINE)
        member_headers = {k: v for k, v in hdrs.items() if k not in ("x-api-key", "authorization")}

        def run(i, t):
            try:
                results[i] = call_once(vmap[t["vendor"]], member_headers, body, t["model"], self.cfg,
                                       timeout=deadline, allow_client=False, cap=COUNCIL_MEMBER_CAP)
            except Exception as e:
                results[i] = {"status": 502, "error": f"proxy error: {type(e).__name__}", "latency_ms": 0}

        threads = [threading.Thread(target=run, args=(i, t), daemon=True) for i, t in enumerate(targets)]
        t0 = time.monotonic()
        for th in threads:
            th.start()
        for th in threads:
            th.join(max(0.0, deadline - (time.monotonic() - t0)))
        members, primary = [], None
        for i, t in enumerate(targets):
            res = results[i] if not threads[i].is_alive() and results[i] else \
                {"status": 504, "error": "council deadline", "latency_ms": int(deadline * 1000)}
            mid = f"{cid}.{i + 1}"
            mrec = self._new_rec(mid, route["rule"], t, parent["model_asked"], parent["bytes"],
                                 parent["stream"], council=cid)
            mrec["req"] = parent["req"]
            msg = res.get("message")
            u = as_dict(as_dict(msg).get("usage"))
            mrec.update(status=res.get("status", 502), latency=res.get("latency_ms", 0),
                        tin=u.get("input_tokens"), tout=u.get("output_tokens"),
                        comp=completion_digest(msg, self.server.salt) if msg else None)
            mrec["notes"].extend(res.get("notes") or [])
            if not msg:
                mrec["notes"].append(res.get("error", "failed"))
            self._finish(mrec)
            entry = {"route_id": mid, "vendor": t["vendor"], "model": t["model"],
                     "status": res.get("status", 502), "latency_ms": res.get("latency_ms", 0)}
            if msg:
                entry["message"] = msg
                primary = primary or msg
            else:
                entry["error"] = res.get("error", "failed")
            members.append(entry)
        extra = {"x-route-id": cid, "x-proxy-note": "council: one answer per member in the 'council' field"}
        if primary is None:
            return self._json(502, {"type": "error", "error": {"type": "api_error",
                                                               "message": "no council member answered"},
                                    "council": members}, extra)
        out = dict(primary)
        out["council"] = members
        if parent["stream"]:
            return self._send(200, synthesize_stream(out), "text/event-stream", extra)
        return self._json(200, out, extra)

    def _count_tokens(self, rec, raw, query, hdrs):
        rec["rule"] = "count_tokens"
        rec["stream"] = False
        vmap = self.server.vendors["vendors"]
        name = next((n for n, v in vmap.items() if v["kind"] == "anthropic"), None)
        extra = {"x-route-id": rec["route_id"]}
        if name is None:
            rec["status"] = 404
            rec["notes"].append("no vendor of kind anthropic")
            return self._err(404, "not_found_error", "count_tokens needs a vendor of kind anthropic", extra)
        rec["vendor"] = name
        if self._tag_raw == "private" and not is_local_address(vmap[name]["host"]):
            rec["status"] = 403
            rec["notes"].append("private request would leave this machine; refused")
            return self._err(403, "permission_error",
                             "a private request may go only to a vendor on this machine", extra)
        try:
            request, _ = vendor_request(vmap[name], hdrs, None, raw, query, self.cfg,
                                        path_suffix="/v1/messages/count_tokens")
        except Refused as e:
            rec["status"] = e.status
            rec["notes"].append(str(e))
            return self._err(e.status, "api_error", str(e), extra)
        resp, err = open_upstream(request, 60)
        rec["latency"] = int((time.monotonic() - rec["t0"]) * 1000)
        if err:
            rec["status"] = err["status"]
            rec["notes"].append(err["note"])
            return self._send(err["status"], err.get("payload") or anthropic_error("api_error", err["note"]),
                              extra=extra)
        with resp:
            data, over = read_capped(resp, ERROR_CAP)
            rec["status"] = 502 if over else resp.status
            if over:
                rec["notes"].append("upstream answer over the cap")
                return self._err(502, "api_error", "upstream answer over the cap", extra)
            return self._send(resp.status, data, extra=extra)


def make_server(routes: dict, vendors: dict, holon_dir, port: int = DEFAULT_PORT, actor="", for_="",
                verbose=False, max_body=MAX_BODY, max_connections=MAX_CONNECTIONS,
                client_timeout=CLIENT_TIMEOUT, record_folder=None, header_deadline=HEADER_DEADLINE,
                per_source=PER_SOURCE_PREAUTH, notes_per_minute=NOTES_PER_MINUTE,
                notes_per_day=NOTES_PER_DAY) -> BoundedServer:
    """Build the proxy bound to 127.0.0.1 (never another interface).

    Validates vendors and routes first (nothing is written on a refusal), then
    writes a fresh <holon>/.proxy-token and keeps or makes <holon>/.proxy-salt.
    """
    vendors = validate_vendors(vendors)
    routes = validate_routes(routes, vendors)
    srv = BoundedServer(("127.0.0.1", port), ProxyHandler, max_connections, header_deadline, per_source)
    srv.routes = routes
    srv.vendors = vendors
    srv.allowed_origins = list(vendors.get("allowed_origins") or [])
    srv.recorder = Recorder(holon_dir, actor, for_, record_folder)
    srv.agent_token, srv.salt = ensure_secrets(srv.recorder.holon)
    srv.verbose = verbose
    srv.max_body = int(max_body)
    srv.client_timeout = client_timeout
    srv.max_json_elements = MAX_JSON_ELEMENTS
    srv.notes_per_minute = int(notes_per_minute)
    srv.notes_per_day = int(notes_per_day)
    srv.note_refusal_minute = None
    srv.refusal_minute, srv.refusal_count, srv.refusals_unrecorded = None, 0, 0
    return srv


# ---------------------------------------------------------------- CLI and report

def resolve_routes(arg, holon=None) -> Path:
    if arg:
        return Path(arg)
    if holon and (Path(holon) / "routes.json").is_file():
        return Path(holon) / "routes.json"
    return DEFAULT_ROUTES


def cmd_routes(args) -> int:
    vendors = load_vendors(args.vendors)
    cfg = load_routes(resolve_routes(args.routes), vendors)
    print(f"vendors: {vendors['_path']}")
    for name, v in vendors["vendors"].items():
        env = v.get("key_env")
        state = "client's own key" if not env and v["kind"] == "anthropic" else (
            "no key" if not env else (f"{env} set" if os.environ.get(env) else f"{env} NOT set"))
        where = "on this machine" if v["_local"] else "off this machine"
        print(f"  {name:<16} {v['kind']:<9} {v['_base_url']}  ({where}; {state})")
    print(f"routes: {cfg['_path']}")
    print("rules (first match wins):")
    for i, r in enumerate(cfg.get("rules", [])):
        r = as_dict(r)
        rid = r.get("id", f"rule-{i + 1}")
        flags = ("  [off]" if r.get("enabled", True) is False else "") + \
            ("  [no such vendor; skipped]" if rid in cfg.get("_skipped", []) else "")
        if as_list(r.get("council")):
            target = "council: " + ", ".join(f"{as_dict(m).get('vendor')}/{as_dict(m).get('model') or '(asked)'}"
                                             for m in r["council"])
        else:
            target = f"{r.get('vendor')}/{r.get('model') or '(asked)'}"
        print(f"  {i + 1}. {rid:<18} when {json.dumps(r.get('when', {}))} -> {target}{flags}")
    d = as_dict(cfg.get("default"))
    print(f"  default -> {d.get('vendor')}/{d.get('model') or '(asked)'}")
    print(f"hash_bodies: {cfg.get('hash_bodies', 'hmac')}")
    return 0


def note_key(line) -> tuple:
    """(route id, base verdict) of a note line (route, verdict "chosen" | "corrected" | "rated:<n>")
    or of a discern line (route_id, verdict)."""
    b = as_dict(as_dict(line).get("body"))
    rid = b.get("route") if line.get("type") == "note" else b.get("route_id")
    verdict = b.get("verdict")
    base = verdict.split(":", 1)[0] if isinstance(verdict, str) else None
    return (rid if isinstance(rid, str) else None), base


def own_routes(lines, actor=None) -> list:
    """Route lines written by the proxy's own actor (all actors when actor is None), first line per route id.

    A route line another actor planted, even one reusing a real route id, never moves a verdict.
    """
    out, seen = [], set()
    for ln in lines:
        if ln.get("type") != "route" or (actor is not None and ln.get("actor") != actor):
            continue
        rid = as_dict(ln.get("body")).get("route_id")
        if isinstance(rid, str):
            if rid in seen:
                continue
            seen.add(rid)
        out.append(ln)
    return out


def record_verifier(holon_dir, folder: Path = ENGINE_DIR):
    """A function line -> bool: the line's id matches its content and its signature verifies
    under the key the holon's record admits for its actor (record.py's own check). Without
    record.py nothing verifies, and nothing is counted."""
    mod = load_record(folder)
    if mod is None or not all(hasattr(mod, n) for n in ("holon_keys", "verify_text", "check_id")):
        return lambda line: False
    try:
        keys = mod.holon_keys(str(holon_dir)) or {}
    except Exception:
        keys = {}

    def check(line):
        actor = line.get("actor")
        pub = keys.get(actor) if isinstance(actor, str) else None
        try:
            return bool(pub and line.get("sig") and mod.check_id(line)
                        and mod.verify_text(line.get("id"), line.get("sig"), actor, pub))
        except Exception:
            return False
    return check


def summarize(lines, actor=None, verify=None) -> dict:
    """Per vendor/model: requests, errors, latency, tokens, and the discernment on them.

    Only the proxy's own route lines (actor), first per route id, are counted, so a
    verdict lands on the vendor its own route line names. A verdict counts once per
    (route id, verdict), and only from a person's own discern line (actor person:,
    reason human) whose signature `verify` accepts (record_verifier: the key the
    holon admits for that person). Unverified person lines are counted apart and
    never as discernment. Agent notes (type note, or an old agent discern) are
    counted once per pair in their own column.
    """
    verify = verify or (lambda line: False)
    routes, by_rid = {}, {}
    for ln in own_routes(lines, actor):
        b = as_dict(ln.get("body"))
        key = f"{b.get('vendor')}/{b.get('model')}"
        s = routes.setdefault(key, {"requests": 0, "errors": 0, "latency_ms": 0, "tokens_in": 0,
                                    "tokens_out": 0, "bytes": 0, "rules": {}, "chosen": 0,
                                    "corrected": 0, "rated": 0, "ratings": [], "notes": 0,
                                    "unverified_person": 0})
        s["requests"] += 1
        st = b.get("status")
        if not isinstance(st, int) or st >= 400:
            s["errors"] += 1
        s["latency_ms"] += int(b.get("latency_ms") or 0)
        size = as_dict(b.get("size"))
        for k in ("tokens_in", "tokens_out", "bytes"):
            s[k] += int(size.get(k) or 0)
        rule = str(b.get("rule"))
        s["rules"][rule] = s["rules"].get(rule, 0) + 1
        if isinstance(b.get("route_id"), str):
            by_rid[b["route_id"]] = key
    seen_person, seen_note = set(), set()
    for ln in lines:
        if ln.get("type") not in ("discern", "note"):
            continue
        b = as_dict(ln.get("body"))
        rid, v = note_key(ln)
        key = by_rid.get(rid)
        if key is None or v not in VERDICTS:
            continue
        pair = (rid, v)
        who = ln.get("actor") if isinstance(ln.get("actor"), str) else ""
        if ln.get("type") == "discern" and who.startswith("person:") and ln.get("for") == who \
                and ln.get("reason") == "human":
            if not verify(ln):
                routes[key]["unverified_person"] += 1
                continue
            if pair in seen_person:
                continue
            seen_person.add(pair)
            routes[key][v] += 1
            if isinstance(b.get("rating"), int) and not isinstance(b.get("rating"), bool):
                routes[key]["ratings"].append(b["rating"])
        elif (actor is None or who == actor) and pair not in seen_note:
            seen_note.add(pair)
            routes[key]["notes"] += 1
    return routes


def by_conversation(lines, actor=None) -> dict:
    """Per conversation (X-Conversation): its turns and where each turn went. Lines without one are left out."""
    out = {}
    for ln in own_routes(lines, actor):
        b = as_dict(ln.get("body"))
        conv = b.get("conversation")
        if not isinstance(conv, str) or not conv:
            continue
        c = out.setdefault(conv, {"requests": 0, "turns": {}, "vendors": {}})
        c["requests"] += 1
        key = f"{b.get('vendor')}/{b.get('model')}"
        c["vendors"][key] = c["vendors"].get(key, 0) + 1
        turn = b.get("turn") if isinstance(b.get("turn"), str) else ""
        c["turns"].setdefault(turn, []).append(
            {"route_id": b.get("route_id"), "vendor": b.get("vendor"), "model": b.get("model"),
             "rule": b.get("rule"), "status": b.get("status"), "latency_ms": b.get("latency_ms"),
             "ts": ln.get("ts")})
    return out


def by_body(lines, actor=None) -> dict:
    """Per body (X-Body): requests, errors, tokens in and out, total latency; 'unattributed' without one."""
    out = {}
    for ln in own_routes(lines, actor):
        b = as_dict(ln.get("body"))
        who = b.get("body") if isinstance(b.get("body"), str) and b.get("body") else "unattributed"
        s = out.setdefault(who, {"requests": 0, "errors": 0, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0})
        s["requests"] += 1
        st = b.get("status")
        if not isinstance(st, int) or st >= 400:
            s["errors"] += 1
        size = as_dict(b.get("size"))
        s["tokens_in"] += int(size.get("tokens_in") or 0)
        s["tokens_out"] += int(size.get("tokens_out") or 0)
        s["latency_ms"] += int(b.get("latency_ms") or 0)
    return out


def cmd_report(args) -> int:
    lines = read_lines(args.holon)
    actor = args.actor
    if not lines:
        print(f"no route or discern lines in {args.holon}")
        return 0
    if getattr(args, "by_body", False):
        print(f"{'body':<40} {'req':>5} {'err':>4} {'tok in':>9} {'tok out':>8} {'total ms':>9}")
        for who, s in sorted(by_body(lines, actor).items()):
            print(f"{who[:40]:<40} {s['requests']:>5} {s['errors']:>4} {s['tokens_in']:>9}"
                  f" {s['tokens_out']:>8} {s['latency_ms']:>9}")
        return 0
    if getattr(args, "conversation", None):
        conv = by_conversation(lines, actor).get(args.conversation)
        if not conv:
            print(f"no route lines for conversation {args.conversation}")
            return 0
        print(f"conversation {args.conversation}: {conv['requests']} requests in {len(conv['turns'])} turns")
        for turn, routes in conv["turns"].items():
            print(f"  turn {turn or '(none)'}")
            for r in routes:
                print(f"    {r['vendor']}/{r['model']}  rule {r['rule']}  status {r['status']}"
                      f"  {r['latency_ms']} ms  route {r['route_id']}")
        return 0
    data = summarize(lines, actor, record_verifier(args.holon))
    print(f"route lines by {actor}; verdicts from person lines whose signature verifies under the holon's admitted keys")
    print(f"{'vendor/model':<40} {'req':>5} {'err':>4} {'avg ms':>7} {'tok in':>9} {'tok out':>8}"
          f" {'chosen':>6} {'corr':>5} {'rated':>5} {'avg':>5} {'notes':>5}")
    for key, s in sorted(data.items()):
        avg = s["latency_ms"] // s["requests"] if s["requests"] else 0
        rating = f"{sum(s['ratings']) / len(s['ratings']):.1f}" if s["ratings"] else "-"
        print(f"{key[:40]:<40} {s['requests']:>5} {s['errors']:>4} {avg:>7} {s['tokens_in']:>9}"
              f" {s['tokens_out']:>8} {s['chosen']:>6} {s['corrected']:>5} {s['rated']:>5} {rating:>5}"
              f" {s['notes']:>5}")
    unverified = sum(s["unverified_person"] for s in data.values())
    if unverified:
        print(f"person lines whose signature did not verify, not counted: {unverified}")
    rules = {}
    for s in data.values():
        for r, n in s["rules"].items():
            rules[r] = rules.get(r, 0) + n
    print("rules matched: " + ", ".join(f"{r} {n}" for r, n in sorted(rules.items())))
    convs = by_conversation(lines, actor)
    if convs:
        print(f"{'conversation':<40} {'turns':>5} {'req':>5}  where the words went")
        for cid, c in sorted(convs.items()):
            where = ", ".join(f"{k} {n}" for k, n in sorted(c["vendors"].items()))
            print(f"{cid[:40]:<40} {len(c['turns']):>5} {c['requests']:>5}  {where}")
    return 0


def cmd_serve(args) -> int:
    vendors = load_vendors(args.vendors)
    routes = load_routes(resolve_routes(args.routes, args.holon), vendors)
    srv = make_server(routes, vendors, args.holon, args.port, args.actor, args.for_, args.verbose,
                      max_body=int(args.max_body_mb * MIB), max_connections=args.max_connections)
    for r in routes.get("_skipped", []):
        print(f"rule {r}: names a vendor not in {vendors['_path']}; skipped")
    where = "record/<actor>.jsonl via record.py" if srv.recorder.writer else str(srv.recorder.log)
    print(f"proxy on http://127.0.0.1:{srv.server_address[1]}  routes {routes['_path']}  lines -> {where}")
    print(f"point an agent here: ANTHROPIC_BASE_URL=http://127.0.0.1:{srv.server_address[1]}")
    print(f'and ANTHROPIC_CUSTOM_HEADERS="X-Proxy-Token: <contents of {srv.recorder.holon / TOKEN_FILE}>"')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="proxy.py",
        description="Local Messages-API proxy: routes requests to the person's own vendors by rule and "
                    "records route lines and agent notes, never prompt or completion bodies.",
        epilog="Vendors, hosts and keys come only from ~/.config/lionsberg/vendors.json (0600, the person's "
               "own); routes.json names vendors by name and nothing else. Records per request: route id, "
               "rule, vendor, model (conforming names only), size, tokens, latency, status, fixed-label "
               "notes, conversation/turn/body ids from headers, and keyed HMAC digests under the holon's "
               "salt (unless hash_bodies is 'none'). Never records prompts, completions, tool data, images, "
               "keys, auth headers or the token. Binds 127.0.0.1 only; refuses a foreign Host or Origin; "
               "every endpoint needs X-Proxy-Token from <holon>/.proxy-token (0600) before any body is "
               "read. Refuses every upstream redirect. POST /discern writes only an untrusted, unsigned "
               "note by the proxy's agent; a person's discernment is signed by the person's own key "
               "through the ICE, never by the proxy.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the proxy on 127.0.0.1")
    s.add_argument("--holon", required=True, help="the holon (HQ) folder lines are written in")
    s.add_argument("--port", type=int, default=DEFAULT_PORT)
    s.add_argument("--routes", help="routes.json (default: <holon>/routes.json, else the kit sample)")
    s.add_argument("--vendors", default=DEFAULT_VENDORS, help="the person's vendors file (0600)")
    s.add_argument("--actor", default="", help="the agent the lines are written as, e.g. agent:<handle>")
    s.add_argument("--for", dest="for_", default="",
                   help="the person the agent answers for (default: the holon keeper if a person)")
    s.add_argument("--max-body-mb", type=float, default=MAX_BODY / MIB, help="request body cap in MB")
    s.add_argument("--max-connections", type=int, default=MAX_CONNECTIONS,
                   help="connections served at once; more are closed unanswered")
    s.add_argument("--verbose", action="store_true", help="print request lines (method and path) to stderr")
    r = sub.add_parser("routes", help="print the person's vendors and the active rules")
    r.add_argument("--routes")
    r.add_argument("--vendors", default=DEFAULT_VENDORS)
    p = sub.add_parser("report", help="summarize routes and discernment per vendor/model")
    p.add_argument("--holon", required=True)
    p.add_argument("--actor", default="agent:proxy",
                   help="the proxy's own actor; only its route lines are counted (default agent:proxy)")
    p.add_argument("--by-body", action="store_true",
                   help="sum requests, tokens and latency per body (X-Body); lines without one are 'unattributed'")
    p.add_argument("--conversation", help="show one conversation turn by turn: where each turn's requests went")
    args = ap.parse_args(argv)
    return {"serve": cmd_serve, "routes": cmd_routes, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
