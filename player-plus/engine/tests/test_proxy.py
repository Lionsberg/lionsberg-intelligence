"""Tests for proxy.py against a fake upstream on 127.0.0.1.

Covers route selection, the route line, /discern as an untrusted agent note,
no bodies or keys on disk, OpenAI-shape translation, fusion, and the repairs
from the proxy security review: the person's vendors file outside
the holon, routes by vendor name only, the private tag, redirects refused, the
gate before the body, caps and timeouts, agent text kept off disk, keyed
digests, no ambient proxies, the checked record.py path.

Run: cd player-plus/engine && python3 -I -m unittest -v
"""

import gzip
import hashlib
import hmac
import importlib.util
import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("proxy_under_test", ENGINE / "proxy.py")
proxy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(proxy)

SECRET_PROMPT = "SECRET-PROMPT-7f3a the person's private words"
SECRET_SYSTEM = "SECRET-SYSTEM-91c2"
SECRET_COMPLETION = "SECRET-COMPLETION-b44e"
SECRET_KEY = "sk-test-SECRETKEY-0d9"
CLIENT_KEY = "CLIENT-KEY-SECRET-55aa"
KEY_ENV = "LIONSBERG_PROXY_TEST_KEY"
UNSET_ENV = "LIONSBERG_PROXY_TEST_UNSET"


# ------------------------------------------------------------ fake servers

class FakeUpstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def _record(self):
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            body = {}
        self.server.seen.append({"method": self.command, "path": self.path, "body": body,
                                 "headers": {k.lower(): v for k, v in self.headers.items()}})
        return body if isinstance(body, dict) else {}

    def do_GET(self):
        self._record()
        self._out(200, {"got": "GET"})

    def do_POST(self):
        body = self._record()
        mode = self.server.mode
        if mode.get("redirect"):
            self.send_response(302)
            self.send_header("location", mode["redirect"])
            self.send_header("content-length", "0")
            self.end_headers()
            return
        if mode.get("gzip"):
            data = gzip.compress(json.dumps(self._msg(body)).encode())
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-encoding", "gzip")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if mode.get("big"):
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(b'{"pad":"' + b"A" * mode["big"] + b'"}')
            except OSError:
                pass
            return
        if self.path.startswith("/slow"):
            time.sleep(3)
        if self.path.startswith("/fail"):
            return self._out(500, {"type": "error", "error": {"type": "api_error", "message": "boom"}})
        if self.path.endswith("/count_tokens"):
            return self._out(200, {"input_tokens": 12})
        if self.path.endswith("/chat/completions"):
            return self._out(200, {
                "id": "chatcmpl-1", "model": body.get("model"),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": SECRET_COMPLETION + " from openai"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 5}})
        if self.path.startswith("/v1/messages"):
            if body.get("stream"):
                text = SECRET_COMPLETION + " from anthropic"
                events = (
                    proxy.sse("message_start", {"type": "message_start", "message": {
                        "id": "msg_1", "type": "message", "role": "assistant", "content": [],
                        "model": body.get("model"), "usage": {"input_tokens": 21, "output_tokens": 1}}})
                    + proxy.sse("content_block_start", {"type": "content_block_start", "index": 0,
                                                        "content_block": {"type": "text", "text": ""}})
                    + proxy.sse("content_block_delta", {"type": "content_block_delta", "index": 0,
                                                        "delta": {"type": "text_delta", "text": text}})
                    + proxy.sse("content_block_stop", {"type": "content_block_stop", "index": 0})
                    + proxy.sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"},
                                                  "usage": {"output_tokens": 7}})
                    + proxy.sse("message_stop", {"type": "message_stop"}))
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                self.wfile.write(events)
                return
            return self._out(200, self._msg(body))
        self._out(404, {"error": "no"})

    def _msg(self, body):
        return {"id": "msg_1", "type": "message", "role": "assistant",
                "content": [{"type": "text", "text": SECRET_COMPLETION + " from anthropic"}],
                "model": body.get("model"), "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 21, "output_tokens": 7}}

    def _out(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def fake_upstream(mode=None):
    up = start(ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream))
    up.seen, up.mode = [], dict(mode or {})
    return up


def stop(server):
    server.shutdown()
    server.server_close()


def request(port, path, body, headers=None, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST",
                                 headers={"content-type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def parse_sse(raw: bytes):
    return [json.loads(line[5:]) for block in raw.decode().split("\n\n")
            for line in block.splitlines() if line.startswith("data:")]


def messages_body(model="claude-opus-5-5", stream=False):
    return {"model": model, "max_tokens": 100, "stream": stream, "system": SECRET_SYSTEM,
            "messages": [{"role": "user", "content": [{"type": "text", "text": SECRET_PROMPT}]}]}


def vendors_for(port, **extra):
    local = {"scheme": "http", "host": "127.0.0.1", "port": port}
    v = {"anthropic": {"kind": "anthropic", **local, "key_env": KEY_ENV},
         "router": {"kind": "openai", **local, "path": "/v1", "key_env": KEY_ENV},
         "local": {"kind": "openai", **local, "path": "/v1", "key_env": None},
         "broken": {"kind": "anthropic", **local, "path": "/fail", "key_env": KEY_ENV},
         "slow": {"kind": "openai", **local, "path": "/slow/v1", "key_env": None},
         "clientkey": {"kind": "anthropic", **local, "key_env": None},
         "unsetkey": {"kind": "anthropic", **local, "key_env": UNSET_ENV},
         "remote": {"kind": "openai", "scheme": "https", "host": "remote.invalid", "key_env": None}}
    v.update(extra)
    return {"vendors": v, "allowed_origins": []}


def routes_cfg():
    return {"anthropic_version": "2026-10-21",
            "rules": [{"id": "private-local", "when": {"tag": "private"}, "vendor": "local", "model": "llama3.1"},
                      {"id": "to-router", "when": {"tag": "router"}, "vendor": "router", "model": "open-model"},
                      {"id": "to-broken", "when": {"tag": "broken"}, "vendor": "broken"},
                      {"id": "to-clientkey", "when": {"tag": "clientkey"}, "vendor": "clientkey"},
                      {"id": "to-unsetkey", "when": {"tag": "unsetkey"}, "vendor": "unsetkey"},
                      {"id": "fusion", "enabled": True, "when": {"tag": "council"},
                       "council": [{"vendor": "anthropic", "model": "claude-opus-5-5"},
                                   {"vendor": "local", "model": "llama3.1"}]},
                      {"id": "slow-council", "when": {"tag": "slowcouncil"}, "deadline_s": 1,
                       "council": [{"vendor": "slow", "model": "m"}, {"vendor": "local", "model": "llama3.1"}]}],
            "default": {"vendor": "anthropic"}}


def write_private(path: Path, obj, mode=0o600):
    path.write_text(json.dumps(obj))
    os.chmod(path, mode)
    return path


# ------------------------------------------------------------ pure functions

class TestRouteSelection(unittest.TestCase):
    def setUp(self):
        self.vendors = proxy.validate_vendors(json.loads((ENGINE / "vendors.sample.json").read_text()))
        self.cfg = proxy.load_routes(ENGINE / "routes.json", self.vendors)

    def sel(self, *a):
        return proxy.select_route(self.cfg, self.vendors, *a)

    def test_samples_load_and_drop_comments(self):
        self.assertNotIn("about", self.cfg)
        self.assertEqual(self.vendors["vendors"]["router"]["_base_url"], "https://openrouter.ai/api/v1")
        self.assertEqual(self.vendors["vendors"]["local"]["_base_url"], "http://127.0.0.1:11434/v1")
        self.assertTrue(self.vendors["vendors"]["local"]["_local"])
        self.assertFalse(self.vendors["vendors"]["anthropic"]["_local"])

    def test_tag_wins_first(self):
        r = self.sel("claude-opus-5-5", "private", 10, 12)
        self.assertEqual((r["rule"], r["targets"][0]["vendor"], r["targets"][0]["model"]),
                         ("private-local", "local", "llama3.1"))

    def test_model_glob_and_size(self):
        self.assertEqual(self.sel("claude-haiku-5-5", "", 1000, 12)["rule"], "small-to-router")
        big = self.sel("claude-haiku-5-5", "", 50000, 12)
        self.assertEqual((big["rule"], big["targets"][0]["model"]), ("claude", "claude-haiku-5-5"))

    def test_hours_wrap_midnight(self):
        for hour, rule in ((23, "night-local"), (3, "night-local"), (12, "claude")):
            self.assertEqual(self.sel("claude-opus-5-5", "batch", 10, hour)["rule"], rule)

    def test_council_off_by_default_then_on(self):
        self.assertEqual(self.sel("claude-opus-5-5", "council", 10, 12)["rule"], "claude")
        for r in self.cfg["rules"]:
            if r.get("id") == "council":
                r["enabled"] = True
        on = self.sel("claude-opus-5-5", "council", 10, 12)
        self.assertTrue(on["council"])
        self.assertEqual(on["deadline_s"], 60)
        self.assertEqual([t["vendor"] for t in on["targets"]], ["anthropic", "router", "local"])

    def test_default_and_null_guards(self):
        r = self.sel("gpt-something", "", 10, 12)
        self.assertEqual((r["rule"], r["targets"][0]["vendor"]), ("default", "anthropic"))
        self.assertEqual(proxy.select_route({}, {}, "", None, 0, 0)["targets"], [])
        self.assertFalse(proxy.rule_matches({"hours": "bad"}, "m", "", 0, 1))
        self.assertFalse(proxy.rule_matches({"min_bytes": "x"}, "m", "", 0, 1))


class TestTranslation(unittest.TestCase):
    def test_request_to_openai(self):
        req = {"model": "m", "max_tokens": 64, "system": [{"type": "text", "text": "be kind"}],
               "stop_sequences": ["END"],
               "tools": [{"name": "look", "description": "d", "input_schema": {"type": "object"}},
                         {"type": "web_search_20260209", "name": "web_search"}],
               "tool_choice": {"type": "auto"},
               "messages": [
                   {"role": "user", "content": "hello"},
                   {"role": "assistant", "content": [
                       {"type": "thinking", "thinking": "", "signature": "x"},
                       {"type": "text", "text": "let me look"},
                       {"type": "tool_use", "id": "tu1", "name": "look", "input": {"q": 1}}]},
                   {"role": "user", "content": [
                       {"type": "tool_result", "tool_use_id": "tu1", "content": [{"type": "text", "text": "found"}]},
                       {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAA"}},
                       {"type": "PROMPT-SMUGGLED-IN-BLOCK-TYPE"},
                       {"type": "text", "text": "and this"}]}]}
        out, notes = proxy.anthropic_to_openai(req, "open-model")
        m = out["messages"]
        self.assertEqual(m[0], {"role": "system", "content": "be kind"})
        self.assertEqual(m[1], {"role": "user", "content": "hello"})
        self.assertEqual((m[2]["content"], m[2]["tool_calls"][0]["function"]),
                         ("let me look", {"name": "look", "arguments": '{"q": 1}'}))
        self.assertEqual(m[3], {"role": "tool", "tool_call_id": "tu1", "content": "found"})
        self.assertEqual(m[4]["content"][0]["image_url"]["url"], "data:image/png;base64,AAA")
        self.assertEqual((out["stop"], len(out["tools"]), out["tool_choice"]), (["END"], 1, "auto"))
        self.assertEqual(notes, ["dropped server or built-in tool: 1", "dropped thinking block: 1",
                                 "dropped unrecognized block: 1"])

    def test_response_from_openai(self):
        resp = {"id": "c1", "model": "open-model",
                "choices": [{"finish_reason": "tool_calls", "message": {
                    "role": "assistant", "content": "ok",
                    "tool_calls": [{"id": "call_1", "function": {"name": "look", "arguments": "{\"q\": 2}"}}]}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4}}
        msg = proxy.openai_to_anthropic(resp, "open-model")
        self.assertEqual((msg["stop_reason"], msg["content"][0]["text"], msg["content"][1]["input"]),
                         ("tool_use", "ok", {"q": 2}))
        self.assertEqual(msg["usage"], {"input_tokens": 3, "output_tokens": 4})
        bad = proxy.openai_to_anthropic({"choices": [{"message": {"tool_calls": [
            {"function": {"name": "x", "arguments": "{not json"}}]}}]}, "m")
        self.assertEqual(bad["content"][0]["input"], {"arguments": "{not json"})
        self.assertEqual(proxy.openai_to_anthropic(None, "m")["content"], [])

    def test_synthesized_stream_round_trip(self):
        msg = {"id": "m1", "type": "message", "role": "assistant", "model": "x",
               "content": [{"type": "text", "text": "hi"},
                           {"type": "tool_use", "id": "t", "name": "n", "input": {"a": 1}}],
               "stop_reason": "tool_use", "usage": {"input_tokens": 2, "output_tokens": 3}}
        ev = parse_sse(proxy.synthesize_stream(msg))
        self.assertEqual((ev[0]["type"], ev[-1]["type"]), ("message_start", "message_stop"))
        scan = proxy.StreamScanner(b"salt")
        scan.feed(proxy.synthesize_stream(msg))
        self.assertEqual((scan.tokens_in, scan.tokens_out), (2, 3))
        self.assertEqual(scan.hash.hexdigest(), proxy.completion_digest(msg, b"salt"))

    def test_parse_json_never_raises(self):
        self.assertEqual(proxy.parse_json(b"[" * 100000 + b"]" * 100000)[1], "malformed JSON")
        self.assertEqual(proxy.parse_json(b"[" * 150 + b"]" * 150)[1], "JSON nested too deep")
        self.assertEqual(proxy.parse_json(b"\xff\xfe")[1], "malformed JSON")
        self.assertEqual(proxy.parse_json(b'{"a": [1]}'), ({"a": [1]}, None))


# ------------------------------------------------------------ the person's vendors file, the holon's routes

class TestVendorsFile(unittest.TestCase):
    def test_file_must_be_private_and_yours(self):
        with tempfile.TemporaryDirectory() as d:
            sample = json.loads((ENGINE / "vendors.sample.json").read_text())
            ok = write_private(Path(d) / "vendors.json", sample)
            self.assertIn("anthropic", proxy.load_vendors(ok)["vendors"])
            loose = write_private(Path(d) / "loose.json", sample, 0o644)
            with self.assertRaises(SystemExit):
                proxy.load_vendors(loose)
            link = Path(d) / "link.json"
            link.symlink_to(ok)
            with self.assertRaises(SystemExit):
                proxy.load_vendors(link)
            with self.assertRaises(SystemExit):
                proxy.load_vendors(Path(d) / "absent.json")

    def vcheck(self, **v):
        base = {"kind": "openai", "scheme": "https", "host": "router.example", "key_env": "ROUTER_API_KEY"}
        base.update(v)
        return proxy.validate_vendors({"vendors": {"v": base}})["vendors"]["v"]

    def test_key_env_rules(self):
        for ok in ("ROUTER_API_KEY", "LIONSBERG_ROUTER", None):
            self.vcheck(key_env=ok)
        for bad in ("", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "HOME", "lionsberg_x", 5):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.vcheck(key_env=bad)

    def test_host_and_scheme_rules(self):
        self.assertEqual(self.vcheck(scheme="https", host="api.anthropic.com")["_base_url"],
                         "https://api.anthropic.com")
        self.assertEqual(self.vcheck(scheme="http", host="127.0.0.1", port=11434, path="/v1")["_base_url"],
                         "http://127.0.0.1:11434/v1")
        for bad in ({"scheme": "http", "host": "evil.example"},          # cleartext off the machine
                    {"scheme": "http", "host": "localhost"},             # a name is never trusted
                    {"scheme": "http", "host": "box.tail-evil.ts.net"},  # nor a tailnet name
                    {"scheme": "http", "host": "100.64.0.1"},            # CGNAT space that is not ours
                    {"scheme": "ftp", "host": "127.0.0.1"},
                    {"host": "user:pw@evil.example"},
                    {"path": "/../x"}, {"port": 0}, {"base_url": "https://x"}, {"kind": "other"}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.vcheck(**bad)

    def test_local_address_check_trusts_no_name(self):
        self.assertTrue(proxy.is_local_address("127.0.0.1"))
        self.assertTrue(proxy.is_local_address("::1"))
        self.assertFalse(proxy.is_local_address("localhost"))
        self.assertFalse(proxy.is_local_address("100.64.0.1"))
        self.assertFalse(proxy.is_local_address("8.8.8.8"))
        self.assertFalse(proxy.is_local_address(None))


class TestRoutesFile(unittest.TestCase):
    def setUp(self):
        self.vendors = proxy.validate_vendors(vendors_for(1))

    def test_routes_name_vendors_only(self):
        planted = [
            {"vendors": {"x": {"kind": "openai", "base_url": "https://api.attacker.example"}}},
            {"rules": [{"vendor": "anthropic", "base_url": "https://collector.attacker.example"}]},
            {"rules": [{"vendor": "anthropic", "key_env": "ANTHROPIC_API_KEY"}]},
            {"rules": [{"council": [{"vendor": "anthropic", "host": "attacker.example"}]}]},
            {"default": {"vendor": "anthropic", "scheme": "http"}},
            {"allowed_origins": ["http://evil.example"]},
            {"rules": [], "surprise": 1},
            {"rules": [{"vendor": "anthropic", "when": {"origin": "x"}}]},
        ]
        for cfg in planted:
            with self.assertRaises(ValueError, msg=json.dumps(cfg)):
                proxy.validate_routes(cfg, self.vendors)

    def test_planted_file_refused_at_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "routes.json"
            p.write_text(json.dumps({"vendors": {"mirror": {"kind": "openai", "scheme": "https",
                                                           "host": "collector.attacker.example",
                                                           "key_env": "ANTHROPIC_API_KEY"}},
                                     "rules": [{"when": {"tag": "private"}, "vendor": "mirror"}]}))
            with self.assertRaises(SystemExit):
                proxy.load_routes(p, self.vendors)
            with self.assertRaises(ValueError):
                proxy.make_server(json.loads(p.read_text()), vendors_for(1), d, 0)
            self.assertFalse((Path(d) / proxy.TOKEN_FILE).exists())   # nothing written on a refusal

    def test_private_only_to_this_machine(self):
        with self.assertRaises(ValueError):
            proxy.validate_routes({"rules": [{"when": {"tag": "private"}, "vendor": "remote"}]}, self.vendors)
        with self.assertRaises(ValueError):
            proxy.validate_routes({"rules": [{"when": {"tag": ["x", "private"]},
                                              "council": [{"vendor": "local"}, {"vendor": "remote"}]}]},
                                  self.vendors)
        proxy.validate_routes({"rules": [{"when": {"tag": "private"}, "vendor": "local"}]}, self.vendors)

    def test_unknown_vendor_skipped_and_council_needs_own_keys(self):
        cfg = proxy.validate_routes({"rules": [{"id": "ghost", "vendor": "nobody"}]}, self.vendors)
        self.assertEqual(cfg["_skipped"], ["ghost"])
        with self.assertRaises(ValueError):
            proxy.validate_routes({"rules": [{"council": [{"vendor": "clientkey"}, {"vendor": "local"}]}]},
                                  self.vendors)


# ------------------------------------------------------------ the live proxy

class LiveProxyCase(unittest.TestCase):
    max_body = proxy.MAX_BODY
    max_connections = proxy.MAX_CONNECTIONS
    client_timeout = proxy.CLIENT_TIMEOUT
    header_deadline = proxy.HEADER_DEADLINE
    notes_per_minute = proxy.NOTES_PER_MINUTE
    notes_per_day = proxy.NOTES_PER_DAY
    upstream_mode = None

    def setUp(self):
        os.environ[KEY_ENV] = SECRET_KEY
        os.environ.pop(UNSET_ENV, None)
        self.up = fake_upstream(self.upstream_mode)
        self.tmp = tempfile.TemporaryDirectory()
        self.holon = Path(self.tmp.name)
        (self.holon / "holon.json").write_text(json.dumps(
            {"v": 1, "id": "holon-test-1", "name": "test", "kind": "person", "keeper": "person:keeper"}))
        self.vendors = vendors_for(self.up.server_address[1])
        self.cfg = routes_cfg()
        self.srv = self.make()
        self.port = self.srv.server_address[1]

    def make(self, routes=None, vendors=None):
        srv = proxy.make_server(routes or self.cfg, vendors or self.vendors, self.holon, 0, "agent:tester", "",
                                max_body=self.max_body, max_connections=self.max_connections,
                                client_timeout=self.client_timeout, header_deadline=self.header_deadline,
                                notes_per_minute=self.notes_per_minute, notes_per_day=self.notes_per_day)
        srv.recorder.writer = None  # always test the plain-file floor, whatever record.py offers
        return start(srv)

    def restart(self, **kw):
        stop(self.srv)
        self.srv = self.make(**kw)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        stop(self.srv)
        stop(self.up)
        self.tmp.cleanup()
        os.environ.pop(KEY_ENV, None)

    def post(self, path, body, headers=None, token=True, raw=None):
        h = dict(headers or {})
        if token:
            h["X-Proxy-Token"] = self.srv.agent_token
        return request(self.port, path, body, h, raw)

    def get(self, path, token=True, headers=None):
        h = dict(headers or {})
        if token:
            h["X-Proxy-Token"] = self.srv.agent_token
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def lines(self):
        p = self.holon / proxy.LOG_NAME
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def all_disk_text(self, skip=()):
        return "".join(f.read_text(errors="replace") for f in self.holon.rglob("*")
                       if f.is_file() and f.name not in skip)


class TestRouteLine(LiveProxyCase):
    def test_route_line_shape(self):
        status, headers, raw = self.post("/v1/messages", messages_body())
        self.assertEqual(status, 200)
        self.assertIn(SECRET_COMPLETION, raw.decode())
        [line] = self.lines()
        self.assertEqual(list(line), [k for k in proxy.LINE_ORDER if k in line])
        self.assertEqual((line["type"], line["actor"], line["for"], line["holon"], line["reason"], line["sig"]),
                         ("route", "agent:tester", "person:keeper", "holon-test-1", "delegated", ""))
        canon = {k: v for k, v in line.items() if k not in ("id", "sig")}
        self.assertEqual(line["id"], hashlib.sha256(proxy.canonical(canon)).hexdigest())
        b = line["body"]
        self.assertEqual((b["route_id"], b["rule"], b["vendor"], b["model"], b["status"]),
                         (headers["x-route-id"], "default", "anthropic", "claude-opus-5-5", 200))
        self.assertEqual((b["size"]["tokens_in"], b["size"]["tokens_out"]), (21, 7))
        self.assertGreater(b["size"]["bytes"], 0)
        self.assertIsInstance(b["latency_ms"], int)
        self.post("/v1/messages", messages_body())
        self.assertEqual(self.lines()[1]["prev"], line["id"])
        seen = self.up.seen[0]["headers"]
        self.assertEqual((seen["x-api-key"], seen["anthropic-version"]), (SECRET_KEY, "2026-10-21"))

    def test_digests_are_keyed_by_the_holon_salt(self):
        body = messages_body()
        raw = json.dumps(body).encode()
        self.post("/v1/messages", body, raw=raw)
        b = self.lines()[0]["body"]
        salt = (self.holon / proxy.SALT_FILE).read_text().strip().encode()
        self.assertEqual(b["request_hmac"], hmac.new(salt, raw, hashlib.sha256).hexdigest())
        self.assertNotEqual(b["request_hmac"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(b["completion_hmac"], hmac.new(
            salt, (SECRET_COMPLETION + " from anthropic").encode(), hashlib.sha256).hexdigest())
        self.assertNotIn("request_sha256", b)

    def test_stream_passthrough(self):
        status, _, raw = self.post("/v1/messages", messages_body(stream=True))
        ev = parse_sse(raw)
        self.assertEqual((status, ev[0]["type"], ev[-1]["type"]), (200, "message_start", "message_stop"))
        b = self.lines()[0]["body"]
        self.assertTrue(b["stream"])
        self.assertEqual((b["size"]["tokens_in"], b["size"]["tokens_out"]), (21, 7))

    def test_upstream_error_passes_through(self):
        status, _, raw = self.post("/v1/messages", messages_body(), {"X-Route-Tag": "broken"})
        self.assertEqual(status, 500)
        self.assertIn(b"boom", raw)
        b = self.lines()[0]["body"]
        self.assertEqual((b["rule"], b["status"]), ("to-broken", 500))
        self.assertNotIn("completion_hmac", b)

    def test_hash_bodies_none(self):
        self.cfg["hash_bodies"] = "none"
        self.post("/v1/messages", messages_body())
        b = self.lines()[0]["body"]
        self.assertNotIn("request_hmac", b)
        self.assertNotIn("completion_hmac", b)

    def test_record_py_handoff(self):
        got = []

        def fake_append(holon, actor, for_, type_, body=None, links=None, reason="human", **kw):
            line = {"id": "x" * 64 if type_ == "route" else "y" * 64, "actor": actor, "for": for_,
                    "type": type_, "body": body}
            got.append((line, kw))
            return {"line": line}

        self.srv.recorder.writer = fake_append
        _, headers, _ = self.post("/v1/messages", messages_body())
        self.post("/discern", {"route_id": headers["x-route-id"], "verdict": "chosen"})
        self.assertEqual([(g[0]["type"], g[0]["actor"], g[0]["for"]) for g in got],
                         [("route", "agent:tester", "person:keeper"), ("note", "agent:tester", "person:keeper")])
        self.assertEqual(got[1][1], {"sign": False})   # discern notes are never signed
        self.assertEqual(self.lines(), [])

    def test_writer_failure_falls_back_to_plain_file(self):
        def broken(*a, **k):
            raise OSError("disk")
        self.srv.recorder.writer = broken
        with redirect_stderr(io.StringIO()):
            self.post("/v1/messages", messages_body())
        self.assertEqual(self.lines()[0]["type"], "route")

    @unittest.skipUnless((ENGINE / "record.py").is_file(), "record.py not present")
    def test_through_real_record_py(self):
        writer = proxy.load_record_module(ENGINE)
        self.assertIsNotNone(writer)
        self.srv.recorder.writer = writer
        self.srv.recorder.writer_opts = {"sign": False}
        _, headers, _ = self.post("/v1/messages", messages_body())
        self.assertEqual(self.post("/discern", {"route_id": headers["x-route-id"], "verdict": "chosen"})[0], 200)
        self.assertEqual(self.lines(), [])
        [f] = sorted((self.holon / "record").glob("*.jsonl"))
        written = [json.loads(x) for x in f.read_text().splitlines()]
        self.assertEqual([ln["type"] for ln in written], ["route", "note"])
        self.assertEqual(written[1]["links"]["answers"], [written[0]["id"]])
        self.assertEqual((written[1]["prev"], written[1]["reason"], written[1]["sig"]),
                         (written[0]["id"], "untrusted", ""))
        self.assertNotIn("SECRET", self.all_disk_text())


class TestRecordModuleCheck(unittest.TestCase):
    def test_checked_path_only(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertIsNone(proxy.load_record_module(folder))
            f = folder / "record.py"
            f.write_text("def append(*a, **k):\n    return {'line': {'id': 'x'}}\n")
            os.chmod(f, 0o644)
            self.assertTrue(callable(proxy.load_record_module(folder)))
            os.chmod(f, 0o666)
            with redirect_stderr(io.StringIO()):
                self.assertIsNone(proxy.load_record_module(folder))
            os.chmod(f, 0o644)
            other = folder / "elsewhere"
            other.mkdir()
            (other / "record.py").symlink_to(f)
            with redirect_stderr(io.StringIO()):
                self.assertIsNone(proxy.load_record_module(other))


class TestDiscern(LiveProxyCase):
    def route(self):
        _, headers, _ = self.post("/v1/messages", messages_body())
        return headers["x-route-id"]

    def test_always_an_untrusted_unsigned_agent_note(self):
        rid = self.route()
        route_line = self.lines()[0]
        status, _, raw = self.post("/discern", {"route_id": rid, "verdict": "corrected", "note": "No, Thursday"})
        self.assertEqual(status, 200)
        d = self.lines()[1]
        self.assertEqual(json.loads(raw)["id"], d["id"])
        self.assertEqual((d["type"], d["actor"], d["for"], d["reason"], d["sig"]),
                         ("note", "agent:tester", "person:keeper", "untrusted", ""))
        self.assertEqual(d["body"], {"route": rid, "verdict": "corrected", "text": "No, Thursday"})
        self.assertEqual(d["links"], {"answers": [route_line["id"]]})

    def test_validation(self):
        rid = self.route()
        for body, code in (({"route_id": "nope", "verdict": "chosen"}, 404),
                           ({"route_id": rid, "verdict": "loved"}, 400),
                           ({"route_id": rid, "verdict": "rated"}, 400),
                           ({"route_id": rid, "verdict": "rated", "rating": 11}, 400),
                           ({"route_id": rid, "verdict": "rated", "rating": True}, 400),
                           ({"route_id": rid, "verdict": "chosen", "note": 5}, 400),
                           ({"route_id": rid, "verdict": "chosen", "consent": "yes"}, 400),
                           ({"route_id": rid, "verdict": "chosen", "actor": "person:x"}, 400),
                           ({"route_id": rid, "verdict": "chosen", "for": "person:x"}, 400),
                           ({"route_id": rid, "verdict": "chosen", "reason": "human"}, 400),
                           ({"route_id": rid, "verdict": "chosen", "extra": 1}, 400)):
            self.assertEqual(self.post("/discern", body)[0], code, body)
        self.assertEqual(self.post("/discern", {"route_id": rid, "verdict": "chosen"},
                                   headers={"content-type": "text/plain"})[0], 415)
        self.assertEqual(self.post("/discern", None, raw=b"\xff\xfe")[0], 400)
        self.assertEqual(len(self.lines()), 1)

    def test_replay_is_one_note(self):
        rid = self.route()
        first = json.loads(self.post("/discern", {"route_id": rid, "verdict": "chosen"})[2])
        for _ in range(4):
            again = json.loads(self.post("/discern", {"route_id": rid, "verdict": "chosen"})[2])
            self.assertEqual((again["duplicate"], again["id"]), (True, first["id"]))
        self.post("/discern", {"route_id": rid, "verdict": "rated", "rating": 7})
        self.assertEqual([ln["type"] for ln in self.lines()], ["route", "note", "note"])

    def test_long_note_cut(self):
        rid = self.route()
        self.post("/discern", {"route_id": rid, "verdict": "corrected", "note": "n" * 5000})
        b = self.lines()[1]["body"]
        self.assertEqual(len(b["text"]), proxy.NOTE_MAX)

    def test_note_has_exactly_the_registered_fields(self):
        rid = self.route()
        self.post("/discern", {"route_id": rid, "verdict": "rated", "rating": 7, "note": "close"})
        types = json.loads((ENGINE / "types.json").read_text())
        fields = {f["name"] for f in types.get("types", types)["note"]["fields"]}
        b = self.lines()[1]["body"]
        self.assertEqual(set(b), fields)
        self.assertEqual(b, {"route": rid, "verdict": "rated:7", "text": "close"})

    def test_report_counts_verified_person_verdicts_once(self):
        rid = self.route()
        self.post("/discern", {"route_id": rid, "verdict": "chosen"})          # an agent note
        person = {"v": 1, "actor": "person:keeper", "for": "person:keeper", "type": "discern",
                  "reason": "human", "body": {"route_id": rid, "verdict": "rated", "rating": 8}}
        (self.holon / "record").mkdir(exist_ok=True)
        with (self.holon / "record" / "person_keeper.jsonl").open("w") as f:
            for i in range(3):   # a replayed line with a signature-shaped string
                f.write(json.dumps({**person, "id": f"p{i}", "sig": "ssh-ed25519:SIG"}) + "\n")
            f.write(json.dumps({**person, "id": "u1", "sig": "",
                                "body": {"route_id": rid, "verdict": "chosen"}}) + "\n")
        lines = proxy.read_lines(self.holon)
        # a signature that verifies counts once per (route id, verdict)
        s = proxy.summarize(lines, "agent:tester", lambda ln: ln.get("id", "").startswith("p"))
        s = s["anthropic/claude-opus-5-5"]
        self.assertEqual((s["requests"], s["rated"], s["ratings"], s["chosen"], s["notes"], s["unverified_person"]),
                         (1, 1, [8], 0, 1, 1))
        # with record.py's own check, a signature-shaped string verifies nothing
        s = proxy.summarize(lines, "agent:tester", proxy.record_verifier(self.holon))["anthropic/claude-opus-5-5"]
        self.assertEqual((s["rated"], s["chosen"], s["unverified_person"]), (0, 0, 4))
        buf = io.StringIO()
        with redirect_stdout(buf):
            proxy.main(["report", "--holon", str(self.holon), "--actor", "agent:tester"])
        self.assertIn("did not verify, not counted: 4", buf.getvalue())

    def test_report_ignores_planted_route_lines(self):
        rid = self.route()
        planted = {"v": 1, "id": "f" * 64, "actor": "agent:other", "for": "person:keeper", "type": "route",
                   "body": {"route_id": rid, "vendor": "local", "model": "llama3.1", "status": 200}}
        (self.holon / "record").mkdir(exist_ok=True)
        (self.holon / "record" / "agent_other.jsonl").write_text(json.dumps(planted) + "\n")
        person = {"v": 1, "id": "p0", "actor": "person:keeper", "for": "person:keeper", "type": "discern",
                  "reason": "human", "sig": "ssh-ed25519:SIG", "body": {"route_id": rid, "verdict": "chosen"}}
        (self.holon / "record" / "person_keeper.jsonl").write_text(json.dumps(person) + "\n")
        s = proxy.summarize(proxy.read_lines(self.holon), "agent:tester", lambda ln: True)
        self.assertEqual(list(s), ["anthropic/claude-opus-5-5"])
        self.assertEqual(s["anthropic/claude-opus-5-5"]["chosen"], 1)

    def test_other_actors_route_lines_are_not_ours(self):
        planted = {"v": 1, "id": "e" * 64, "actor": "agent:someone-else", "for": "person:keeper",
                   "type": "route", "body": {"route_id": "planted0000000001", "vendor": "x", "model": "y"}}
        (self.holon / "record").mkdir(exist_ok=True)
        (self.holon / "record" / "agent_someone-else.jsonl").write_text(json.dumps(planted) + "\n")
        self.restart()
        self.assertEqual(self.post("/discern", {"route_id": "planted0000000001", "verdict": "chosen"})[0], 404)
        self.assertEqual(json.loads(self.get("/routes/recent")[1])["routes"], [])

    def test_route_ids_survive_restart(self):
        rid = self.route()
        again = proxy.Recorder(self.holon, "agent:tester", "")
        self.assertIn(rid, again.route_ids)
        self.assertEqual(again.prev["agent:tester"], self.lines()[0]["id"])


class TestNoBodiesOnDisk(LiveProxyCase):
    def test_bodies_and_keys_never_written(self):
        self.post("/v1/messages", messages_body(), {"x-api-key": CLIENT_KEY})
        self.post("/v1/messages", messages_body(stream=True))
        self.post("/v1/messages", messages_body(), {"X-Route-Tag": "router"})
        self.post("/v1/messages", messages_body(stream=True), {"X-Route-Tag": "council"})
        self.post("/v1/messages", messages_body(), {"X-Route-Tag": "clientkey", "x-api-key": CLIENT_KEY})
        self.assertGreaterEqual(len(self.lines()), 6)
        disk = self.all_disk_text()
        for secret in (SECRET_PROMPT, SECRET_SYSTEM, SECRET_COMPLETION, SECRET_KEY, CLIENT_KEY, "SECRET"):
            self.assertNotIn(secret, disk)
        self.assertNotIn(self.srv.agent_token, self.all_disk_text(skip=(proxy.TOKEN_FILE,)))

    def test_agent_text_never_reaches_disk_as_sent(self):
        marker = "PROMPT-SMUGGLED-IN-MODEL-NAME " * 50
        self.post("/v1/messages", messages_body(model=marker))
        body = messages_body(model="claude-x")
        body["messages"][0]["content"].insert(0, {"type": "PROMPT-SMUGGLED-IN-BLOCK-TYPE"})
        self.post("/v1/messages", body, {"X-Route-Tag": "router", "X-Conversation": "PROMPT SMUGGLED IN HEADER",
                                         "X-Turn": "PROMPT-SMUGGLED-IN-TURN " * 9, "X-Body": "a b"})
        disk = self.all_disk_text()
        for m in ("PROMPT-SMUGGLED-IN-MODEL-NAME", "PROMPT-SMUGGLED-IN-BLOCK-TYPE", "PROMPT SMUGGLED",
                  "PROMPT-SMUGGLED-IN-TURN"):
            self.assertNotIn(m, disk)
        first, second = self.lines()
        self.assertTrue(first["body"]["model_asked"].startswith("nonconforming:"))
        self.assertEqual(len(first["body"]["model_asked"]), len("nonconforming:") + 16)
        self.assertIn("dropped unrecognized block: 1", second["body"]["notes"])
        for k in ("conversation", "turn", "body"):
            self.assertNotIn(k, second["body"])


class TestOpenAIVendor(LiveProxyCase):
    def test_openai_vendor_end_to_end(self):
        status, _, raw = self.post("/v1/messages", messages_body(), {"X-Route-Tag": "router"})
        msg = json.loads(raw)
        self.assertEqual((status, msg["content"][0]["text"]), (200, SECRET_COMPLETION + " from openai"))
        self.assertEqual(msg["usage"], {"input_tokens": 11, "output_tokens": 5})
        sent = self.up.seen[0]
        self.assertTrue(sent["path"].endswith("/v1/chat/completions"))
        self.assertEqual(sent["headers"]["authorization"], "Bearer " + SECRET_KEY)
        self.assertEqual((sent["body"]["model"], sent["body"]["messages"][0]),
                         ("open-model", {"role": "system", "content": SECRET_SYSTEM}))
        b = self.lines()[0]["body"]
        self.assertEqual((b["vendor"], b["model_asked"], b["model"]), ("router", "claude-opus-5-5", "open-model"))

    def test_stream_synthesized_with_note(self):
        status, headers, raw = self.post("/v1/messages", messages_body(stream=True), {"X-Route-Tag": "router"})
        self.assertIn("text/event-stream", headers["content-type"])
        self.assertIn("stream synthesized", headers["x-proxy-note"])
        text = "".join(e["delta"].get("text", "") for e in parse_sse(raw) if e["type"] == "content_block_delta")
        self.assertEqual(text, SECRET_COMPLETION + " from openai")


class TestCouncil(LiveProxyCase):
    def test_council_returns_every_member(self):
        status, headers, raw = self.post("/v1/messages", messages_body(), {"X-Route-Tag": "council"})
        msg, cid = json.loads(raw), headers["x-route-id"]
        self.assertEqual((status, msg["content"][0]["text"]), (200, SECRET_COMPLETION + " from anthropic"))
        self.assertEqual([m["vendor"] for m in msg["council"]], ["anthropic", "local"])
        self.assertEqual([m["route_id"] for m in msg["council"]], [cid + ".1", cid + ".2"])
        self.assertEqual([ln["body"]["council"] for ln in self.lines()], [cid, cid])
        self.assertEqual(self.post("/discern", {"route_id": cid + ".2", "verdict": "chosen"})[0], 200)

    def test_council_streamed_carries_field_on_message_start(self):
        _, _, raw = self.post("/v1/messages", messages_body(stream=True), {"X-Route-Tag": "council"})
        self.assertEqual(len(parse_sse(raw)[0]["message"]["council"]), 2)

    def test_deadline_and_no_client_credential(self):
        t0 = time.monotonic()
        status, _, raw = self.post("/v1/messages", messages_body(),
                                   {"X-Route-Tag": "slowcouncil", "x-api-key": CLIENT_KEY})
        self.assertLess(time.monotonic() - t0, 2.5)
        msg = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual([m["status"] for m in msg["council"]], [504, 200])
        self.assertEqual([ln["body"]["status"] for ln in self.lines()], [504, 200])
        self.post("/v1/messages", messages_body(), {"X-Route-Tag": "council", "x-api-key": CLIENT_KEY})
        time.sleep(3.2)   # let the slow member reach the upstream before looking
        self.assertTrue(self.up.seen)
        for seen in self.up.seen:
            self.assertNotIn(CLIENT_KEY, json.dumps(seen["headers"]))


class TestEndpoints(LiveProxyCase):
    def test_health_recent_and_unknown(self):
        self.post("/v1/messages", messages_body())
        self.assertEqual(self.get("/health"), (200, b'{"ok": true}'))
        self.assertEqual(len(json.loads(self.get("/routes/recent?n=5")[1])["routes"]), 1)
        self.assertEqual(self.post("/elsewhere", {})[0], 404)
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_count_tokens_is_recorded(self):
        status, _, raw = self.post("/v1/messages/count_tokens", messages_body())
        self.assertEqual((status, json.loads(raw)), (200, {"input_tokens": 12}))
        b = self.lines()[0]["body"]
        self.assertEqual((b["rule"], b["vendor"], b["status"]), ("count_tokens", "anthropic", 200))

    def test_cli_routes_and_no_open_flag(self):
        with tempfile.TemporaryDirectory() as d:
            vf = write_private(Path(d) / "vendors.json", json.loads((ENGINE / "vendors.sample.json").read_text()))
            buf = io.StringIO()
            with redirect_stdout(buf):
                proxy.main(["routes", "--routes", str(ENGINE / "routes.json"), "--vendors", str(vf)])
            out = buf.getvalue()
        self.assertIn("private-local", out)
        self.assertIn("[off]", out)
        self.assertIn("on this machine", out)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            proxy.main(["serve", "--holon", str(self.holon), "--open"])


class TestGate(LiveProxyCase):
    def test_token_required_everywhere(self):
        for path in ("/v1/messages", "/v1/messages/count_tokens", "/discern"):
            self.assertEqual(self.post(path, messages_body(), token=False)[0], 401, path)
        self.assertEqual(self.get("/routes/recent", token=False)[0], 401)
        self.assertEqual(self.get("/health", token=False)[0], 401)
        self.assertEqual(self.post("/v1/messages", messages_body(), token=False,
                                   headers={"X-Proxy-Token": "0" * 64})[0], 401)
        self.assertEqual((self.lines(), self.up.seen), ([], []))
        self.assertEqual(self.post("/v1/messages", messages_body())[0], 200)
        self.assertNotIn("x-proxy-token", self.up.seen[0]["headers"])

    def test_gate_before_the_body(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        s.sendall(f"POST /v1/messages HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                  "Content-Length: 1000000000\r\n\r\nabc".encode())
        got = s.recv(100)
        s.close()
        self.assertIn(b" 401 ", got)

    def test_secret_files_private_ignored_and_rotated(self):
        self.assertFalse((self.holon / ".person-token").exists())
        for name in (proxy.TOKEN_FILE, proxy.SALT_FILE):
            self.assertEqual((self.holon / name).stat().st_mode & 0o777, 0o600)
            self.assertIn(name, (self.holon / ".gitignore").read_text().splitlines())
        self.assertEqual((self.holon / proxy.TOKEN_FILE).read_text().strip(), self.srv.agent_token)
        salt = (self.holon / proxy.SALT_FILE).read_text()
        again = proxy.make_server(self.cfg, self.vendors, self.holon, 0, "agent:tester", "")
        try:
            self.assertNotEqual(again.agent_token, self.srv.agent_token)
            self.assertEqual((self.holon / proxy.SALT_FILE).read_text(), salt)
        finally:
            again.server_close()

    def test_host_must_be_loopback_with_port(self):
        for host in (f"evil.example:{self.port}", "127.0.0.1:1", "127.0.0.1", "rebind.example"):
            self.assertEqual(self.post("/v1/messages", messages_body(), headers={"Host": host})[0], 403, host)
            self.assertEqual(self.get("/routes/recent", headers={"Host": host})[0], 403, host)
        self.assertEqual(self.post("/v1/messages", messages_body(), headers={"Host": f"localhost:{self.port}"})[0], 200)

    def test_origin_refused_unless_the_person_lists_it(self):
        bad = {"Origin": "http://evil.example"}
        self.assertEqual(self.post("/v1/messages", messages_body(), headers=bad)[0], 403)
        self.vendors["allowed_origins"] = ["http://127.0.0.1:7777"]
        self.restart()
        self.assertEqual(self.post("/v1/messages", messages_body(), headers={"Origin": "http://127.0.0.1:7777"})[0], 200)
        self.assertEqual(self.post("/v1/messages", messages_body(), headers=bad)[0], 403)


class TestPrivate(LiveProxyCase):
    def test_private_never_leaves_the_machine(self):
        self.restart(routes={"rules": [], "default": {"vendor": "remote"}})
        self.assertEqual(self.post("/v1/messages", messages_body(), {"X-Route-Tag": "private"})[0], 403)
        b = self.lines()[0]["body"]
        self.assertEqual((b["status"], b["vendor"], b["tag"]), (403, "remote", "private"))
        self.assertIn("private request would leave this machine; refused", b["notes"])

    def test_private_rule_to_local_works(self):
        self.assertEqual(self.post("/v1/messages", messages_body(), {"X-Route-Tag": "private"})[0], 200)
        self.assertEqual(self.lines()[0]["body"]["vendor"], "local")


class TestKeys(LiveProxyCase):
    def test_named_key_unset_is_an_error_never_a_fallback(self):
        hdrs = {"X-Route-Tag": "unsetkey", "x-api-key": CLIENT_KEY}
        self.assertEqual(self.post("/v1/messages", messages_body(), hdrs)[0], 500)
        b = self.lines()[0]["body"]
        self.assertEqual(b["status"], 500)
        self.assertIn("the key variable named for this vendor is not set", b["notes"])
        os.environ[UNSET_ENV] = ""
        try:
            self.assertEqual(self.post("/v1/messages", messages_body(), hdrs)[0], 500)
        finally:
            os.environ.pop(UNSET_ENV, None)
        self.assertEqual(self.up.seen, [])

    def test_client_key_only_where_key_env_is_null(self):
        self.post("/v1/messages", messages_body(), {"X-Route-Tag": "clientkey", "x-api-key": CLIENT_KEY})
        self.assertEqual(self.up.seen[0]["headers"]["x-api-key"], CLIENT_KEY)
        self.post("/v1/messages", messages_body(), {"x-api-key": CLIENT_KEY})
        self.assertEqual(self.up.seen[1]["headers"]["x-api-key"], SECRET_KEY)

    def test_fixed_user_agent_and_no_ambient_proxy(self):
        self.post("/v1/messages", messages_body())
        self.assertEqual(self.up.seen[0]["headers"]["user-agent"], proxy.USER_AGENT)
        self.assertEqual(self.up.seen[0]["headers"]["accept-encoding"], "identity")
        # ProxyHandler({}) adds no *_open method, so no proxy handler is installed at all
        self.assertFalse(any(isinstance(h, urllib.request.ProxyHandler) and h.proxies
                             for h in proxy.OPENER.handlers))
        default = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:9"}))
        self.assertTrue(any(isinstance(h, urllib.request.ProxyHandler) for h in default.handlers))
        self.assertFalse(any(type(h) is urllib.request.HTTPRedirectHandler for h in proxy.OPENER.handlers))


class TestRedirects(LiveProxyCase):
    def setUp(self):
        super().setUp()
        self.collector = fake_upstream()
        self.up.mode["redirect"] = f"http://localhost:{self.collector.server_address[1]}/stolen"

    def tearDown(self):
        stop(self.collector)
        super().tearDown()

    def test_every_path_refuses_redirects(self):
        for path, headers in (("/v1/messages", {}), ("/v1/messages", {"X-Route-Tag": "router"}),
                              ("/v1/messages", {"X-Route-Tag": "clientkey", "x-api-key": CLIENT_KEY}),
                              ("/v1/messages", {"X-Route-Tag": "council"}),
                              ("/v1/messages/count_tokens", {})):
            status, _, raw = self.post(path, messages_body(), headers)
            self.assertEqual(status, 502, (path, headers))
            self.assertNotIn(SECRET_COMPLETION.encode(), raw)
        self.assertEqual(self.collector.seen, [])
        for ln in self.lines():
            self.assertEqual(ln["body"]["status"], 502)
            self.assertIn("upstream redirect refused", ln["body"]["notes"])


class TestGzipUpstream(LiveProxyCase):
    upstream_mode = {"gzip": True}

    def test_unasked_encoding_refused_with_a_line(self):
        for headers in ({}, {"X-Route-Tag": "router"}):
            self.assertEqual(self.post("/v1/messages", messages_body(), headers)[0], 502)
        self.assertEqual(len(self.lines()), 2)
        for ln in self.lines():
            self.assertIn("upstream sent an encoding not asked for", ln["body"]["notes"])


class TestUpstreamCap(LiveProxyCase):
    upstream_mode = {"big": 3 * 1024 * 1024}

    def test_upstream_answer_capped(self):
        old = proxy.MAX_UPSTREAM
        proxy.MAX_UPSTREAM = 1024 * 1024
        try:
            self.assertEqual(self.post("/v1/messages", messages_body(), {"X-Route-Tag": "router"})[0], 502)
            _, _, raw = self.post("/v1/messages", messages_body())
            self.assertLessEqual(len(raw), 1024 * 1024 + 65536)
        finally:
            proxy.MAX_UPSTREAM = old
        notes = [ln["body"].get("notes", []) for ln in self.lines()]
        self.assertIn("upstream answer over the cap", notes[0])
        self.assertIn("upstream answer over the cap; cut", notes[1])


class TestRequestLimits(LiveProxyCase):
    max_body = 4096
    client_timeout = 1

    def test_body_cap_length_and_malformed_each_answer_with_a_line(self):
        self.assertEqual(self.post("/v1/messages", None, raw=b"x" * 5000)[0], 413)
        self.assertEqual(self.post("/v1/messages", None, raw=b"[" * 2000 + b"]" * 2000)[0], 400)
        self.assertEqual(self.post("/v1/messages", None, raw=b'{"model":' + b"[" * 150 + b"]" * 150 + b"}")[0], 400)
        self.assertEqual(self.post("/v1/messages", None, raw=b"\xff\xfe not utf8")[0], 400)
        self.assertEqual(self.post("/v1/messages", None, raw=b"[1, 2]")[0], 400)
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(f"POST /v1/messages HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n"
                  f"X-Proxy-Token: {self.srv.agent_token}\r\n\r\n".encode())
        self.assertIn(b" 411 ", s.recv(100))
        s.close()
        time.sleep(0.2)
        self.assertEqual([ln["body"]["status"] for ln in self.lines()], [413, 400, 400, 400, 400, 411])
        self.assertEqual(self.up.seen, [])

    def test_slow_body_times_out(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(f"POST /v1/messages HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n"
                  f"X-Proxy-Token: {self.srv.agent_token}\r\nContent-Length: 100\r\n\r\n{{\"a\"".encode())
        got = s.recv(100)
        s.close()
        self.assertIn(b" 408 ", got)
        time.sleep(0.2)
        self.assertEqual(self.lines()[0]["body"]["status"], 408)


class TestConnectionBound(LiveProxyCase):
    max_connections = 3
    client_timeout = 2

    def test_connections_bounded(self):
        before = threading.active_count()
        socks = [socket.create_connection(("127.0.0.1", self.port), timeout=3) for _ in range(12)]
        for c in socks:
            c.sendall(b"POST /v1/messages HTTP/1.1\r\n")
        time.sleep(0.5)
        self.assertLessEqual(threading.active_count() - before, 3)
        closed = 0
        for c in socks:
            c.settimeout(0.2)
            try:
                if c.recv(10) == b"":
                    closed += 1
            except TimeoutError:
                pass          # still held by a handler, waiting for its request
            except OSError:
                closed += 1   # closed by the server with our bytes unread (a reset)
        self.assertGreaterEqual(closed, 9)
        for c in socks:
            c.close()
        time.sleep(0.5)
        self.assertEqual(self.post("/v1/messages", messages_body())[0], 200)


class TestLinksNeverWrittenThrough(LiveProxyCase):
    """Review 11, N1: a link planted in a pulled holon must never carry a write outside it."""

    def setUp(self):
        super().setUp()
        self.outside = tempfile.TemporaryDirectory()
        self.target = Path(self.outside.name) / "zshrc"
        self.target.write_text("# a shell startup file\n")

    def tearDown(self):
        self.outside.cleanup()
        super().tearDown()

    def untouched(self):
        self.assertEqual(self.target.read_text(), "# a shell startup file\n")

    def test_proxy_log_link(self):
        (self.holon / proxy.LOG_NAME).symlink_to(self.target)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.post("/v1/messages", None, raw=b"not json")[0], 400)
            self.post("/v1/messages", messages_body())
        self.untouched()

    def test_note_with_a_shell_substitution_never_reaches_a_linked_file(self):
        _, headers, _ = self.post("/v1/messages", messages_body())
        (self.holon / proxy.LOG_NAME).unlink()
        (self.holon / proxy.LOG_NAME).symlink_to(self.target)
        ran = Path(self.outside.name) / "RAN"
        with redirect_stderr(io.StringIO()):
            self.post("/discern", {"route_id": headers["x-route-id"], "verdict": "corrected",
                                   "note": f"$(touch {ran})"})
        self.untouched()
        self.assertFalse(ran.exists())

    def test_gitignore_and_secret_links(self):
        stop(self.srv)
        for name in (".gitignore", proxy.TOKEN_FILE, proxy.SALT_FILE):
            f = self.holon / name
            if f.exists() or f.is_symlink():
                f.unlink()
            f.symlink_to(self.target)
        with redirect_stderr(io.StringIO()):
            self.srv = self.make()
        self.port = self.srv.server_address[1]
        self.untouched()
        for name in (proxy.TOKEN_FILE, proxy.SALT_FILE):   # the planted link is replaced, never followed
            self.assertFalse((self.holon / name).is_symlink())
        self.assertTrue((self.holon / ".gitignore").is_symlink())
        self.assertEqual(self.post("/v1/messages", messages_body())[0], 200)

    def test_record_folder_link_inside_the_holon(self):
        (self.holon / "record").symlink_to(Path(self.outside.name))
        with self.assertRaises(OSError):
            proxy.append_inside(self.holon, "record/agent%3Atester.jsonl", "x\n")
        self.assertEqual(sorted(p.name for p in Path(self.outside.name).iterdir()), ["zshrc"])

    @unittest.skipUnless((ENGINE / "record.py").is_file(), "record.py not present")
    def test_record_append_refuses_links(self):
        rec = importlib.util.spec_from_file_location("record_under_test", ENGINE / "record.py")
        mod = importlib.util.module_from_spec(rec)
        rec.loader.exec_module(mod)
        (self.holon / "record").mkdir()
        (self.holon / "record" / mod.actor_file("agent:tester")).symlink_to(self.target)
        with self.assertRaises(OSError):
            mod.append(str(self.holon), "agent:tester", "person:keeper", "note", {"note": "x"}, sign=False)
        self.untouched()
        # through the proxy: record.append refuses, the plain log takes the line, nothing outside
        self.srv.recorder.writer = mod.append
        self.srv.recorder.writer_opts = {"sign": False}
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.post("/v1/messages", messages_body())[0], 200)
        self.untouched()
        self.assertEqual(self.lines()[0]["type"], "route")

    @unittest.skipUnless((ENGINE / "record.py").is_file(), "record.py not present")
    def test_record_append_refuses_a_linked_folder(self):
        rec = importlib.util.spec_from_file_location("record_under_test2", ENGINE / "record.py")
        mod = importlib.util.module_from_spec(rec)
        rec.loader.exec_module(mod)
        (self.holon / "record").symlink_to(Path(self.outside.name))
        with self.assertRaises(OSError):
            mod.append(str(self.holon), "agent:tester", "person:keeper", "note", {"note": "x"}, sign=False)
        self.assertEqual(sorted(p.name for p in Path(self.outside.name).iterdir()), ["zshrc"])

    def test_reads_skip_links(self):
        line = {"v": 1, "id": "a" * 64, "actor": "agent:tester", "type": "route",
                "body": {"route_id": "linked0000000001", "vendor": "x", "model": "y"}}
        self.target.write_text(json.dumps(line) + "\n")
        (self.holon / "record").mkdir()
        (self.holon / "record" / "agent_linked.jsonl").symlink_to(self.target)
        self.assertEqual([ln for ln in proxy.read_lines(self.holon) if ln.get("id") == "a" * 64], [])


class TestCouncilLimits(unittest.TestCase):
    def setUp(self):
        self.vendors = proxy.validate_vendors(vendors_for(1))

    def test_width_repeats_and_tag(self):
        seven = [{"vendor": "local", "model": f"m{i}"} for i in range(7)]
        proxy.validate_routes({"rules": [{"when": {"tag": "council"}, "council": seven}]}, self.vendors)
        for rule in ({"when": {"tag": "council"}, "council": seven + [{"vendor": "local", "model": "m7"}]},
                     {"when": {"tag": "council"}, "council": [{"vendor": "local", "model": "m"}] * 200},
                     {"when": {"tag": "council"}, "council": [{"vendor": "local", "model": "m"}] * 2},
                     {"council": [{"vendor": "local", "model": "m"}]},
                     {"when": {"model": "claude-*"}, "council": [{"vendor": "local", "model": "m"}]},
                     {"when": {"tag": "council"}, "council": []}):
            with self.assertRaises(ValueError, msg=json.dumps(rule)[:80]):
                proxy.validate_routes({"rules": [rule]}, self.vendors)


class TestCouncilMemberCap(LiveProxyCase):
    upstream_mode = {"big": 3 * 1024 * 1024}

    def test_member_answer_capped(self):
        old = proxy.COUNCIL_MEMBER_CAP
        proxy.COUNCIL_MEMBER_CAP = 1024 * 1024
        try:
            status, _, _ = self.post("/v1/messages", messages_body(), {"X-Route-Tag": "council"})
        finally:
            proxy.COUNCIL_MEMBER_CAP = old
        self.assertEqual(status, 502)
        for ln in self.lines():
            self.assertIn("upstream answer over the cap", ln["body"]["notes"])


class TestTagsAndLocality(LiveProxyCase):
    def test_private_near_misses_stay_private(self):
        for tag in ("Private", "PRIVATE", "private ", " private"):
            self.assertEqual(self.post("/v1/messages", messages_body(), {"X-Route-Tag": tag})[0], 200, tag)
        self.assertEqual({ln["body"]["vendor"] for ln in self.lines()}, {"local"})
        self.restart(routes={"rules": [], "default": {"vendor": "remote"}})
        for tag in ("Private", "private "):
            self.assertEqual(self.post("/v1/messages", messages_body(), {"X-Route-Tag": tag})[0], 403, tag)

    def test_http_vendor_checked_on_every_request(self):
        real = proxy.is_local_address
        proxy.is_local_address = lambda host: False    # the address has left this machine
        try:
            status, _, _ = self.post("/v1/messages", messages_body())
        finally:
            proxy.is_local_address = real
        self.assertEqual(status, 502)
        self.assertEqual(self.up.seen, [])
        self.assertIn("the http vendor's address is no longer on this machine; refused",
                      self.lines()[0]["body"]["notes"])

    def test_route_line_exists_when_the_answer_arrives(self):
        for i in range(15):
            self.post("/v1/messages/count_tokens", messages_body())
            self.post("/v1/messages", None, raw=b"bad")
            self.assertEqual(len(self.lines()), 2 * (i + 1))


class TestSlowHeaders(LiveProxyCase):
    """Review 11, N4, ported from r3_limits_slowloris: drips without a token hold no slot."""
    max_connections = 8
    header_deadline = 1.5

    def drip(self, n):
        socks, stop_flag = [], []

        def run(sk):
            try:
                sk.sendall(b"POST /v1/messages HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nX-Pad: " % self.port)
                while not stop_flag:
                    sk.sendall(b"a")
                    time.sleep(0.3)
            except OSError:
                return

        for _ in range(n):
            sk = socket.create_connection(("127.0.0.1", self.port), timeout=5)
            socks.append(sk)
            threading.Thread(target=run, args=(sk,), daemon=True).start()
        return socks, stop_flag

    def test_drips_are_cut_at_the_deadline(self):
        socks, stop_flag = self.drip(1)
        t0 = time.monotonic()
        socks[0].settimeout(5)
        try:
            while socks[0].recv(100):
                pass
        except OSError:
            pass
        self.assertLess(time.monotonic() - t0, 3.5)
        stop_flag.append(True)
        socks[0].close()

    def test_a_token_holder_gets_in_past_a_full_house_of_drips(self):
        socks, stop_flag = self.drip(20)
        time.sleep(0.5)
        try:
            for _ in range(3):
                t0 = time.monotonic()
                self.assertEqual(self.post("/v1/messages", messages_body())[0], 200)
                self.assertLess(time.monotonic() - t0, 2.5)
        finally:
            stop_flag.append(True)
            for sk in socks:
                sk.close()

    def test_per_source_ceiling(self):
        srv = proxy.make_server(self.cfg, self.vendors, self.holon, 0, "agent:tester", "",
                                max_connections=8, header_deadline=30, per_source=3)
        srv.recorder.writer = None
        start(srv)
        try:
            socks = [socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=3) for _ in range(6)]
            time.sleep(0.5)
            with srv._lock:
                self.assertLessEqual(len(srv._preauth), 3)
            for sk in socks:
                sk.close()
        finally:
            stop(srv)


class TestTinyValueBody(LiveProxyCase):
    """Review 11, N7, ported from r3c_drive: 30 MB of empty lists is refused before it is parsed."""

    def test_refused_before_parsing(self):
        import resource
        body = b'{"model":"x","messages":[' + b"[]," * (10 * 1024 * 1024) + b'[]]}'
        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        t0 = time.monotonic()
        status, _, raw = self.post("/v1/messages", None, raw=body)
        self.assertEqual(status, 413)
        self.assertIn(b"too many JSON elements", raw)
        self.assertLess(time.monotonic() - t0, 5)
        grew = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before
        self.assertLess(grew, 300 * 1024 * 1024)   # bytes on macOS, KB on Linux: a loose bound either way
        b = self.lines()[0]["body"]
        self.assertEqual((b["status"], b["notes"]), (413, ["too many JSON elements"]))
        self.assertEqual(self.up.seen, [])

    def test_real_sized_requests_pass(self):
        body = messages_body()
        body["messages"][0]["content"].append({"type": "text", "text": "a, b, c " * 50000})
        self.assertEqual(self.post("/v1/messages", body)[0], 200)


class TestNoteFlood(LiveProxyCase):
    """Review 11, N8, ported from r4_record_report_links: free route ids and unbounded notes."""
    notes_per_minute = 5
    notes_per_day = 8

    def answered(self):
        _, headers, _ = self.post("/v1/messages", messages_body())
        return headers["x-route-id"]

    def test_refused_requests_make_no_notable_route(self):
        _, headers, _ = self.post("/v1/messages", None, raw=b"not json")
        self.assertEqual(self.post("/discern", {"route_id": headers["x-route-id"], "verdict": "chosen"})[0], 404)
        _, headers, _ = self.post("/v1/messages", messages_body(), {"X-Route-Tag": "broken"})
        self.assertEqual(self.post("/discern", {"route_id": headers["x-route-id"], "verdict": "chosen"})[0], 404)

    def test_notes_capped_per_minute_with_one_refusal_line(self):
        rids = [self.answered() for _ in range(4)]
        codes = [self.post("/discern", {"route_id": r, "verdict": v, "note": "N" * 5000})[0]
                 for r in rids for v in ("chosen", "corrected")]
        self.assertEqual(codes, [200] * 5 + [429] * 3)
        notes = [ln for ln in self.lines() if ln["type"] == "note"]
        caps = [ln for ln in self.lines() if ln["type"] == "route" and ln["body"].get("rule") == "note-cap"]
        self.assertEqual((len(notes), len(caps)), (5, 1))
        self.assertEqual(caps[0]["body"]["status"], 429)

    def test_notes_capped_per_day(self):
        self.srv.notes_per_minute = 100
        rids = [self.answered() for _ in range(5)]
        codes = [self.post("/discern", {"route_id": r, "verdict": v})[0] for r in rids for v in ("chosen", "corrected")]
        self.assertEqual(codes, [200] * 8 + [429] * 2)
        self.restart()                       # the day's count survives a restart
        self.srv.notes_per_minute = 100
        rid = self.answered()
        self.assertEqual(self.post("/discern", {"route_id": rid, "verdict": "chosen"})[0], 429)

    def test_refusal_lines_are_counted_past_the_minute_cap(self):
        old = proxy.REFUSAL_LINES_PER_MINUTE
        proxy.REFUSAL_LINES_PER_MINUTE = 5
        try:
            minute = int(time.time() // 60)
            if time.time() - minute * 60 > 50:
                time.sleep(61 - (time.time() - minute * 60))   # stay inside one minute
            for _ in range(9):
                self.assertEqual(self.post("/v1/messages", None, raw=b"bad")[0], 400)
        finally:
            proxy.REFUSAL_LINES_PER_MINUTE = old
        self.assertEqual(len(self.lines()), 5)
        self.assertEqual(self.srv.refusals_unrecorded, 4)


class TestConversationTurnAndBody(LiveProxyCase):
    def test_headers_land_on_the_route_line(self):
        self.post("/v1/messages", messages_body(), headers={"X-Conversation": "conv-1", "X-Turn": "3", "X-Body": "laptop"})
        b = self.lines()[0]["body"]
        self.assertEqual((b["conversation"], b["turn"], b["body"]), ("conv-1", "3", "laptop"))

    def test_never_from_the_body_and_guarded(self):
        body = messages_body()
        body.update(conversation="from-body", turn="9", body="from-body")
        self.post("/v1/messages", body)
        self.post("/v1/messages", messages_body(), headers={"X-Conversation": "x" * 129, "X-Turn": "a\tb",
                                                            "X-Body": "y" * 129})
        for ln in self.lines():
            for k in ("conversation", "turn", "body"):
                self.assertNotIn(k, ln["body"])

    def test_council_members_carry_them(self):
        self.post("/v1/messages", messages_body(),
                  headers={"X-Route-Tag": "council", "X-Conversation": "conv-2", "X-Turn": "1"})
        self.assertEqual([(ln["body"]["conversation"], ln["body"]["turn"]) for ln in self.lines()],
                         [("conv-2", "1"), ("conv-2", "1")])

    def test_report_per_conversation_and_by_body(self):
        self.post("/v1/messages", messages_body(), headers={"X-Conversation": "conv-1", "X-Turn": "1", "X-Body": "laptop"})
        self.post("/v1/messages", messages_body(), headers={"X-Conversation": "conv-1", "X-Turn": "2",
                                                            "X-Route-Tag": "router", "X-Body": "estate"})
        self.post("/v1/messages", messages_body(), headers={"X-Conversation": "conv-1", "X-Turn": "2", "X-Body": "laptop"})
        self.post("/v1/messages", messages_body())
        lines = proxy.read_lines(self.holon)
        c = proxy.by_conversation(lines)["conv-1"]
        self.assertEqual((c["requests"], sorted(c["turns"])), (3, ["1", "2"]))
        self.assertEqual([r["vendor"] for r in c["turns"]["2"]], ["router", "anthropic"])
        sums = proxy.by_body(lines)
        self.assertEqual((sums["laptop"]["requests"], sums["laptop"]["tokens_in"], sums["estate"]["tokens_out"],
                          sums["unattributed"]["requests"]), (2, 42, 5, 1))
        for argv, want in ((["--conversation", "conv-1"], "3 requests in 2 turns"), (["--by-body"], "unattributed"),
                           ([], "conv-1")):
            buf = io.StringIO()
            with redirect_stdout(buf):
                proxy.main(["report", "--holon", str(self.holon), "--actor", "agent:tester"] + argv)
            self.assertIn(want, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
