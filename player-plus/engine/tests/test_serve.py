"""hud/serve.py against what a pull can bring in (the last security look, H1, H2, M2 and L2).

Each test plants, in a home's cells/, what a member with push could commit (a link, a said
store, a holon.json claiming the home's id, a carried proposal), runs serve.py on 127.0.0.1 at
a free port, and checks that nothing is written through a link, that a planted said line is not
the Talk, that a home act stays home, and that a mail becomes only a said line. No key or token
value is printed. Standard library only.
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
SERVE = ENGINE.parent / "hud" / "serve.py"
sys.path.insert(0, str(ENGINE))
import holon   # noqa: E402
import record  # noqa: E402

A, B = "person:alice", "person:bob"


class Served(unittest.TestCase):
    """A home for alice with a room she keeps (bob admitted and joined) and a cell carol keeps."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="serve-test-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        for x in (A, B, "person:carol"):
            record.make_key(x, cls.kd)
        pk = lambda x: record.pubkey_of(record.find_key(None, x, cls.kd))
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        cls.home_id = record.holon_info(cls.hq)["id"]
        cells = os.path.join(cls.hq, "cells")
        os.makedirs(cells)
        cls.room = os.path.join(cells, "room")
        holon.init(cls.room, "Room", "room", A, key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        holon.admit(cls.room, A, B, pk(B), ts="2026-10-24T09:01:00-07:00", key_dir=cls.kd)
        record.append(cls.room, B, B, "join", {"role": "member"}, ts="2026-10-24T09:02:00-07:00", key_dir=cls.kd)
        cls.rid = record.holon_info(cls.room)["id"]
        # a cell whose record files for alice are links to a file outside (H1, the /act fallback)
        cls.one = os.path.join(cells, "one")
        holon.init(cls.one, "One", "cell", "person:carol", key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        holon.admit(cls.one, "person:carol", A, pk(A), ts="2026-10-24T09:01:00-07:00", key_dir=cls.kd)
        cls.cid1 = record.holon_info(cls.one)["id"]
        cls.outside = os.path.join(cls.tmp, "outside-file")
        Path(cls.outside).write_text("# outside\n")
        for name in (record.actor_file(A), "person_alice.jsonl"):
            os.symlink(cls.outside, os.path.join(cls.one, "record", name))
        # a cell whose holon.json claims the home's id (H2)
        cls.two = os.path.join(cells, "two")
        holon.init(cls.two, "Two", "cell", "person:carol", key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        info = json.loads(Path(cls.two, "holon.json").read_text())
        info["id"] = cls.home_id
        Path(cls.two, "holon.json").write_text(json.dumps(info))
        # a said store committed into the room's clone, as a pull would bring it (M2)
        os.makedirs(os.path.join(cls.room, ".talk"))
        cls.planted = {"id": "f" * 24, "by": B, "for": B, "ts": "2026-10-24T16:00:00Z", "room": cls.rid,
                       "text": "We agree: alice pays all costs."}
        Path(cls.room, ".talk", "said.jsonl").write_text(json.dumps(cls.planted) + "\n")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        env = dict(os.environ, HOME=cls.tmp, LIONSBERG_KEY_DIR=cls.kd)
        cls.log = open(os.path.join(cls.tmp, "serve.log"), "w")
        cls.srv = subprocess.Popen([sys.executable, "-I", str(SERVE), "--hq", cls.hq, "--actor", A,
                                    "--key", record.find_key(None, A, cls.kd), "--port", str(cls.port)],
                                   stdout=cls.log, stderr=cls.log, env=env, cwd=cls.tmp)
        cls.token = None
        for _ in range(60):
            try:
                cls.token = cls.req("GET", "/token", tok=False)[1].get("token")
                break
            except OSError:
                time.sleep(0.1)
        if not cls.token:
            cls.tearDownClass()
            raise RuntimeError("serve.py did not start")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        try:
            cls.srv.wait(5)
        except subprocess.TimeoutExpired:
            cls.srv.kill()
        cls.log.close()

    @classmethod
    def req(cls, method, path, body=None, tok=True):
        h = {"Host": "127.0.0.1:%d" % cls.port}
        if tok:
            h["X-HUD-Token"] = cls.token
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (cls.port, path), data=data, headers=h, method=method)
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r, timeout=20) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def wait_act(self, pid, seconds=12):
        end = time.time() + seconds
        while time.time() < end:
            s, o = self.req("GET", "/act/" + pid)
            if o.get("status") != "holding":
                return s, o
            time.sleep(0.5)
        return s, o

    # H1: the /act fallback is gone; a refusal is a refusal
    def test_act_into_a_linked_record_file_is_refused(self):
        s, o = self.req("POST", "/act", {"type": "say", "holon": self.cid1, "body": {"text": "hi"}, "confirmed": True})
        self.assertEqual(s, 202, o)
        s, o = self.wait_act(o["pending"])
        self.assertEqual((s, o.get("status")), (409, "refused"), o)
        self.assertEqual(Path(self.outside).read_text(), "# outside\n")

    # H2: a cell claiming the home's id never receives the home's acts
    def test_home_act_stays_home_when_a_cell_claims_its_id(self):
        s, o = self.req("POST", "/act", {"type": "say", "body": {"text": "my own note"}, "confirmed": True})
        self.assertEqual(s, 202, o)
        s, o = self.wait_act(o["pending"])
        self.assertEqual(o.get("status"), "written", o)
        self.assertFalse(Path(self.two, "record", record.actor_file(A)).exists())
        self.assertIn(o["line_id"], Path(self.hq, "record", record.actor_file(A)).read_text())

    # H2 (record.holon_dirs): a home-only act aimed at a cell is refused; aimed at the claimed id, it goes home
    def test_home_only_act_never_goes_to_a_cell(self):
        s, o = self.req("POST", "/act", {"type": "attention", "holon": self.cid1,
                                         "body": {"fewer": 3, "note": "my private budget"}, "confirmed": True})
        self.assertEqual(s, 409, o)
        s, o = self.req("POST", "/act", {"type": "attention", "holon": self.home_id,
                                         "body": {"fewer": 3, "note": "my private budget"}, "confirmed": True})
        self.assertEqual(s, 202, o)
        s, o = self.wait_act(o["pending"])
        self.assertEqual(o.get("status"), "written", o)
        self.assertFalse(Path(self.two, "record", record.actor_file(A)).exists())
        self.assertIn(o["line_id"], Path(self.hq, "record", record.actor_file(A)).read_text())

    # M2: a said store in the room's clone is not the Talk, and Keep never signs it
    def test_planted_said_line_is_not_the_talk(self):
        s, o = self.req("GET", "/talk?room=" + self.rid)
        self.assertEqual(s, 200)
        self.assertNotIn(self.planted["id"], [x["id"] for x in o["said"]])
        s, o = self.req("POST", "/keep", {"room": self.rid, "id": self.planted["id"], "confirmed": True})
        self.assertEqual(s, 404, o)
        # a forged row in the home's own store, without the store's HMAC, is not read either
        d = Path(self.hq, ".talk", self.rid)
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "said.jsonl", "a") as f:
            f.write(json.dumps(dict(self.planted, id="e" * 24)) + "\n")
        s, o = self.req("POST", "/keep", {"room": self.rid, "id": "e" * 24, "confirmed": True})
        self.assertEqual(s, 404, o)

    # H1: the Talk never writes through a link
    def test_say_never_writes_through_a_link(self):
        s, o = self.req("POST", "/say", {"room": self.rid, "text": "first", "confirmed": True})
        self.assertEqual(s, 200, o)
        f = Path(self.hq, ".talk", self.rid, "said.jsonl")
        self.assertFalse(f.is_symlink())
        self.assertNotIn("first", Path(self.room, ".talk", "said.jsonl").read_text())
        moved = f.with_name("said.moved")
        f.rename(moved)
        os.symlink(self.outside, f)
        try:
            s, o = self.req("POST", "/say", {"room": self.rid, "text": "hello $(touch /tmp/never)", "confirmed": True})
            self.assertEqual(s, 409, o)
            self.assertEqual(Path(self.outside).read_text(), "# outside\n")
        finally:
            f.unlink()
            moved.rename(f)

    # L2: the person's tap names the type; a carried proposal never does
    def test_agent_figures_and_modes_relay(self):
        # the trust layer's Full depth and the harness's own modes: behind the page's token, an agent named,
        # and said plainly when the agent host is not running (DESIGN-TALK.md, the trust layer)
        for path in ("/agent/figures", "/agent/mode"):
            self.assertEqual(self.req("GET", path + "?agent=yours", tok=False)[0], 403)
            self.assertEqual(self.req("GET", path)[0], 400)
            s, o = self.req("GET", path + "?agent=yours")
            self.assertEqual((s, o), (409, {"refused": "your agent is resting"}))
        s, o = self.req("GET", "/agent/list")
        self.assertEqual(s, 200)
        self.assertTrue(all(a.get("figures") is None for a in o["agents"]))   # no host: nothing guessed

    def test_mail_line_is_only_a_said_line(self):
        d = Path(self.hq, ".carried", "prose")
        d.mkdir(parents=True, exist_ok=True)
        prop = {"v": 1, "type": "commit", "actor": "agent:x", "for": A, "holon": self.home_id,
                "body": {"text": "I will pay", "source_mail": "<m@x>", "consent": "yes", "consent_for": "z"}}
        eid = "a" * 32
        (d / (eid + ".json")).write_text(json.dumps({"v": 1, "kind": "prose", "id": eid, "message_id": "<m@x>",
                                                    "prose": "I will pay", "proposed_line": prop, "read": False}))
        s, o = self.req("POST", "/mail/line", {"id": eid, "type": "commit", "confirmed": True})
        self.assertEqual(s, 400, o)
        s, o = self.req("POST", "/mail/line", {"id": eid, "confirmed": True})
        self.assertEqual(s, 200, o)
        line = next(json.loads(x) for x in Path(self.hq, "record", record.actor_file(A)).read_text().splitlines()
                    if json.loads(x)["id"] == o["id"])
        self.assertEqual(line["type"], "say")
        self.assertEqual(sorted(k for k in line["body"] if k != "body_salt"), ["source_mail", "text"])


class BodiesLiveReader(unittest.TestCase):
    """The live reader over a house shaped like a swarm vault (DESIGN-BODIES §11.3, addendum
    2026-10-25): two RUNNING bodies (one whose process is in the table, one whose pid is dead),
    one DONE, a desk file, and a sessions folder with one helper. The process table is planted;
    nothing on this machine is probed for the bodies' liveness."""

    def setUp(self):
        import importlib.util
        import types
        spec = importlib.util.spec_from_file_location("serve_bodies_test", SERVE)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.tmp = Path(tempfile.mkdtemp(prefix="bodies-live-"))
        house = self.tmp / "vault"
        bg = house / "record" / "bg"
        here = os.uname().nodename.split(".")[0]
        now = time.time()
        iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
        for name, pid, marks in (("Vega", 4242, ["RUNNING"]), ("Deneb", 999999, ["RUNNING"]), ("Rigel", None, ["DONE"])):
            d = bg / f"bg-{name}"
            d.mkdir(parents=True)
            (d / "task.md").write_text(f"# Task — Polaris {name} (background body)\n\n**What I am doing:** reading the rooms for the week ahead. Then more.\n")
            (d / "status.md").write_text("- 07:00 woke\n- 07:20 read the rooms\n")
            if "RUNNING" in marks:
                (d / "RUNNING").write_text(f"pid: {pid}\nstart: {iso(now - 3600)}\nhost: {here}\ncard: —\n")
            if "DONE" in marks:
                (d / "DONE").write_text("")
                (d / "handoff.md").write_text("the words of a handoff, never read into the state\n")
        (bg / "briefs").mkdir()
        (bg / "proposals.md").write_text("not a body\n")
        desk = house / "estate" / "desk" / "on-deck.md"
        desk.parent.mkdir(parents=True)
        desk.write_text(f"holder: laptop\nsince: {iso(now - 7200)}\nhandoff: words never read\n")
        sessions = self.tmp / "projects"
        slug = sessions / re.sub(r"[^A-Za-z0-9]", "-", str(house.resolve()))
        sid = "11111111-2222-3333-4444-555555555555"
        slug.mkdir(parents=True)
        (slug / f"{sid}.jsonl").write_text(json.dumps({"type": "user", "timestamp": iso(now - 7200), "sessionId": sid}) + "\n")
        sub = slug / sid / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-abc123.meta.json").write_text(json.dumps({"description": "Build the next hand", "model": "opus"}))
        (sub / "agent-abc123.jsonl").write_text(json.dumps({"timestamp": iso(now - 600)}) + "\n")
        (sub / "agent-old999.meta.json").write_text(json.dumps({"description": "A finished reader", "model": "sonnet", "finished": True}))
        (sub / "agent-old999.jsonl").write_text(json.dumps({"timestamp": iso(now - 900)}) + "\n")
        args = types.SimpleNamespace(bg=str(bg), desk=str(desk), sessions=str(sessions), heartbeat=None,
                                     usage_file=str(self.tmp / "none.json"), harness_sessions=str(self.tmp / "no-registry"))
        hub = types.SimpleNamespace(args=args, hq=self.tmp / "hq")
        self.live = self.mod.BodiesLive(hub)
        cwd = str(house.resolve())
        planted = [
            {"pid": 7000, "ppid": 1, "start": now - 7200, "cmd": "/usr/local/bin/claude", "exe": "/usr/local/bin/claude", "cwd": cwd, "parent": "-zsh"},
            {"pid": 4242, "ppid": 1, "start": now - 3600, "cmd": "/usr/local/bin/claude --append-system-prompt BACKGROUND BODY. You are Polaris Vega — a body.",
             "exe": "/usr/local/bin/claude", "cwd": cwd, "parent": "-zsh"},
        ]
        self.live._procs = lambda: planted
        self.live._ps_ok = True

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prime_stale_and_helpers(self):
        out = self.live.read()
        m = out["machine"]
        prime = m[0]
        self.assertEqual(prime["kind"], "prime")
        self.assertTrue(prime["alive"])
        self.assertTrue(prime["holds_desk"])
        self.assertEqual(prime["pid"], 7000)
        self.assertEqual(prime["joined_by"], "start")
        self.assertEqual([(a["description"], a["model"], a["running"]) for a in prime["subagents"]],
                         [("Build the next hand", "opus", True)])
        by = {e["name"]: e for e in m if e["kind"] == "background"}
        self.assertEqual(sorted(by), ["Deneb", "Rigel", "Vega"])           # briefs/ and proposals.md are not bodies
        self.assertTrue(by["Vega"]["alive"])
        self.assertFalse(by["Vega"]["stale"])
        self.assertEqual(by["Vega"]["task"], "Reading the rooms for the week ahead.")
        self.assertEqual(by["Vega"]["status_last"], "07:20 read the rooms")
        self.assertTrue(by["Deneb"]["stale"])
        self.assertEqual(by["Deneb"]["state"], "stale")
        self.assertEqual(by["Rigel"]["state"], "archived")
        self.assertEqual(out["house_helpers"], [])
        blob = json.dumps(out)
        self.assertNotIn("never read", blob)                                 # no handoff or desk note words
        self.assertNotIn("the words of a handoff", blob)


def load_serve(tag):
    import importlib.util
    spec = importlib.util.spec_from_file_location(tag, SERVE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BodyTalkReader(unittest.TestCase):
    """The transcript reader over a planted session file: the kinds, `since`, the tool rows,
    thinking and tool results withheld, the harness's meta lines withheld, a peer's message
    said as the person's line with who sent it, and appends followed."""

    def setUp(self):
        self.mod = load_serve("serve_talk_reader")
        self.tmp = Path(tempfile.mkdtemp(prefix="body-talk-"))
        self.f = self.tmp / "s.jsonl"
        rows = [
            {"type": "queue-operation"},
            {"type": "user", "timestamp": "t1", "origin": {"kind": "human"}, "message": {"role": "user", "content": "Build the deal view."}},
            {"type": "assistant", "timestamp": "t2", "message": {"content": [{"type": "thinking", "thinking": "SECRET THOUGHT"}]}},
            {"type": "assistant", "timestamp": "t3", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x/hud/deal.js"}}]}},
            {"type": "user", "timestamp": "t4", "message": {"content": [{"type": "tool_result", "content": "TOOL OUTPUT WORDS"}]}},
            {"type": "assistant", "timestamp": "t5", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "rm -rf SECRET-CMD"}}]}},
            {"type": "user", "timestamp": "t6", "isMeta": True, "message": {"content": "<system-reminder>META WORDS</system-reminder>"}},
            {"type": "assistant", "timestamp": "t7", "message": {"content": [{"type": "text", "text": "Done: the deal view is built."}]}},
            {"type": "user", "timestamp": "t8", "isSidechain": True, "message": {"content": "HELPER WORDS"}},
            {"type": "user", "timestamp": "t9", "isMeta": True, "origin": {"kind": "peer", "from": "unknown", "name": "the ICE",
             "body": "[from the ICE, the person's own tap] hello"},
             "message": {"content": "Another Claude session sent a message:\n<cross-session-message from-name=\"the ICE\">\n[from the ICE, the person's own tap] hello\n</cross-session-message>"}},
        ]
        self.f.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_kinds_rows_and_withheld(self):
        r = self.mod.TranscriptReader(self.f)
        evs = r.read_new(0)
        self.assertEqual([(e["n"], e["kind"], e["text"]) for e in evs], [
            (1, "user", "Build the deal view."),
            (2, "state", "thinking"),
            (3, "tool", "Read deal.js"),
            (5, "tool", "Ran a command"),
            (7, "agent", "Done: the deal view is built."),
            (9, "user", "[from the ICE, the person's own tap] hello"),
        ])
        self.assertEqual(evs[-1]["from"], "the ICE")
        self.assertEqual(evs[4]["turn"], 1)                    # the agent's line belongs to the person's turn
        blob = json.dumps(evs)
        for hidden in ("SECRET THOUGHT", "TOOL OUTPUT WORDS", "SECRET-CMD", "META WORDS", "HELPER WORDS"):
            self.assertNotIn(hidden, blob)

    def test_since_and_follow(self):
        r = self.mod.TranscriptReader(self.f)
        self.assertEqual([e["n"] for e in r.read_new(5)], [5, 7, 9])
        self.assertEqual(r.read_new(0), [])
        with open(self.f, "a") as fh:
            fh.write(json.dumps({"type": "assistant", "timestamp": "t10", "message": {"content": [{"type": "text", "text": "And one more."}]}}))
        self.assertEqual(r.read_new(0), [])                    # a half-written line waits for its end
        with open(self.f, "a") as fh:
            fh.write("\n")
        self.assertEqual([(e["n"], e["text"], e["turn"]) for e in r.read_new(0)], [(10, "And one more.", 9)])

    def test_tool_rows(self):
        t = self.mod.tool_row
        self.assertEqual(t("Edit", {"file_path": "/a/b/serve.py"}), "Edited serve.py")
        self.assertEqual(t("Bash", {"command": "secret"}), "Ran a command")
        self.assertEqual(t("Agent", {}), "Started a helper")
        self.assertEqual(t("mcp__claude-in-chrome__navigate", {}), "Used navigate")

    def test_a_link_is_not_read(self):
        link = self.tmp / "link.jsonl"
        os.symlink(self.f, link)
        with self.assertRaises(OSError):
            self.mod.TranscriptReader(link).read_new(0)


class BodyTalkRoutes(unittest.TestCase):
    """The registry's pid -> session mapping, the refusals without the person's tap, unreachable
    answers in plain words, and the window route with no match (osascript mocked, never run)."""

    def setUp(self):
        import types
        self.mod = load_serve("serve_talk_routes")
        self.tmp = Path(tempfile.mkdtemp(prefix="body-routes-"))
        self.reg = self.tmp / "sessions"
        self.reg.mkdir(mode=0o700)
        self.pid = os.getpid()                                  # a live process of this user
        self.sid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        (self.reg / f"{self.pid}.json").write_text(json.dumps({
            "pid": self.pid, "sessionId": self.sid, "cwd": "/Users/x/house", "peerProtocol": 1, "kind": "interactive",
            "entrypoint": "cli", "messagingSocketPath": f"/tmp/cc-socks/{self.pid}.sock", "status": "busy",
            "name": "x", "secretField": "NOT KEPT"}))
        (self.reg / "999999.json").write_text(json.dumps({"pid": 999999, "sessionId": self.sid}))   # its process is gone
        (self.reg / "12.json").write_text(json.dumps({"pid": 13}))                                  # names another pid
        args = types.SimpleNamespace(harness_sessions=str(self.reg), sessions=str(self.tmp / "projects"), bg=None, desk=None)
        machine = [
            {"name": "prime", "kind": "prime", "pid": self.pid, "alive": True, "window": True, "status": "busy",
             "session_id": self.sid},
            {"name": "Vega", "folder": "bg-Vega", "kind": "background", "pid": 4242, "alive": True, "window": False},
            {"name": "Deneb", "folder": "bg-Deneb", "kind": "background", "pid": 999999, "alive": False},
        ]
        hub = types.SimpleNamespace(args=args, hq=self.tmp)
        hub.bodies = types.SimpleNamespace(registry=self.mod.HarnessRegistry(str(self.reg)),
                                           read=lambda: {"machine": machine},
                                           _procs=lambda: [{"pid": self.pid, "tty": "ttys009"}, {"pid": 4242, "tty": None}])
        self.bt = self.mod.BodyTalk(hub)
        self.ran = []
        self.bt._osascript = lambda lines, args=(): self.ran.append(list(args)) or "none"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_registry_maps_pid_to_session(self):
        e = self.bt.registry.entries()
        self.assertEqual(sorted(e), [self.pid])                 # a dead pid and a mismatched record are not kept
        self.assertEqual(e[self.pid]["sessionId"], self.sid)
        self.assertEqual(e[self.pid]["status"], "busy")
        self.assertNotIn("secretField", e[self.pid])
        self.assertIsNone(self.bt.transcript_of(e[self.pid]))   # no such folder: nothing to read
        (self.tmp / "projects" / "-Users-x-house").mkdir(parents=True)
        self.assertEqual(self.bt.transcript_of(e[self.pid]),
                         self.tmp / "projects" / "-Users-x-house" / f"{self.sid}.jsonl")

    def test_sessions_join_by_registry_first(self):
        import types
        live = self.mod.BodiesLive(types.SimpleNamespace(args=types.SimpleNamespace(harness_sessions=str(self.reg)), hq=self.tmp))
        sdir = self.tmp / "projects" / "h"
        sdir.mkdir(parents=True)
        (sdir / f"{self.sid}.jsonl").write_text(json.dumps({"timestamp": "2020-01-01T00:00:00Z"}) + "\n")
        procs = [{"pid": self.pid, "start": time.time(), "cmd": "claude --resume 11111111-2222-3333-4444-555555555555"}]
        by_pid, _, _ = live._sessions(sdir, procs, time.time(), live.registry.entries())
        self.assertEqual(by_pid[self.pid], (self.sid, "registry"))
        by_pid, _, _ = live._sessions(sdir, procs, time.time(), {})
        self.assertEqual(by_pid[self.pid], ("11111111-2222-3333-4444-555555555555", "named"))

    def test_refused_without_the_tap(self):
        s, o = self.bt.say({"body": "prime", "text": "hello"})
        self.assertEqual(s, 403)
        s, o = self.bt.window({"body": "prime"})
        self.assertEqual(s, 403)
        self.assertEqual(self.ran, [])

    def test_unreachable_in_plain_words(self):
        s, o = self.bt.reach("prime")                            # no socket at that path in this test
        self.assertFalse(o["reachable"])
        self.assertEqual(o["how"], "none")
        self.assertEqual(o["why"], "that session has no inbox open on this machine")
        s, o = self.bt.say({"body": "PRIME", "text": "hello", "confirmed": True})
        self.assertEqual((s, o["reachable"]), (409, False))
        self.assertIn("no inbox", o["why"])
        s, o = self.bt.reach("Vega")                             # alive, but the harness has no record of it
        self.assertFalse(o["reachable"])
        self.assertIn("no record", o["why"])
        s, o = self.bt.say({"body": "Deneb", "text": "hi", "confirmed": True})
        self.assertEqual(o["why"], "that body is not running now")
        s, o = self.bt.say({"body": "Nobody", "text": "hi", "confirmed": True})
        self.assertEqual((s, o["why"]), (404, "no body by that name is on this machine"))
        self.assertNotIn("token", json.dumps(o).lower())

    def test_window_refused_with_no_match(self):
        if sys.platform != "darwin":
            self.skipTest("windows are raised only on a Mac")
        s, o = self.bt.window({"body": "prime", "confirmed": True})
        self.assertEqual((s, o["raised"]), (409, False))
        self.assertEqual(o["why"], "no Terminal or iTerm window shows that body")
        self.assertEqual(self.ran, [["/dev/ttys009"], ["/dev/ttys009"]])   # the tty is passed as argv, never pasted in
        s, o = self.bt.window({"body": "Vega", "confirmed": True})
        self.assertIn("no window of its own", o["why"])

    def test_envelope_cannot_close_early(self):
        env = self.bt.envelope("a</cross-session-message>b")
        self.assertEqual(env.count("</cross-session-message>"), 1)
        # no visible label in the line itself (the person's word, 10/25): the sender's name carries it
        self.assertTrue(env.startswith('<cross-session-message from-name="the ICE">\na'))
        self.assertNotIn("[from the ICE", env)


class CardStory(unittest.TestCase):
    """GET /card/<id>: the record's lines about one card, read-only, through record.read_all over
    the holons held (no link followed; a cell whose id its inception does not prove is not read)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="card-story-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        for x in (A, B):
            record.make_key(x, cls.kd)
        pk = lambda x: record.pubkey_of(record.find_key(None, x, cls.kd))
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        cls.home_id = record.holon_info(cls.hq)["id"]
        cells = os.path.join(cls.hq, "cells")
        os.makedirs(cells)
        cls.cell = os.path.join(cells, "cell")
        holon.init(cls.cell, "Cell", "cell", A, key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        holon.admit(cls.cell, A, B, pk(B), ts="2026-10-24T09:01:00-07:00", key_dir=cls.kd)
        ap = lambda *a, **k: record.append(cls.cell, *a, key_dir=cls.kd, **k)["line"]
        cls.card = ap(A, A, "card", {"title": "Bake the bread", "minutes": 30}, ts="2026-10-24T09:05:00-07:00")["id"]
        cls.said = ap(B, B, "say", {"text": "I can help knead."}, {"anchored_to": [cls.card]}, ts="2026-10-24T09:06:00-07:00")["id"]
        cls.commit = ap(A, A, "commit", {"card": cls.card, "by": "2026-10-31", "witness": B}, ts="2026-10-24T09:07:00-07:00")["id"]
        cls.kept = ap(A, A, "kept", {"note": "baked"}, {"fulfils": [cls.commit]}, ts="2026-10-24T09:08:00-07:00")["id"]
        cls.next = ap(A, A, "card", {"title": "Slice the bread"}, {"predecessor": [cls.card]}, ts="2026-10-24T09:09:00-07:00")["id"]
        cls.other = ap(A, A, "card", {"title": "Sweep the hall"}, ts="2026-10-24T09:10:00-07:00")["id"]
        cls.unsigned = record.append(cls.cell, B, B, "say", {"text": "on paper"}, {"anchored_to": [cls.card]},
                                     ts="2026-10-24T09:11:00-07:00", sign=False, key_dir=cls.kd)["line"]["id"]
        # a cell whose holon.json claims the home's id: refused, so its line naming the card is not read
        cls.two = os.path.join(cells, "two")
        holon.init(cls.two, "Two", "cell", A, key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        cls.planted = record.append(cls.two, A, A, "say", {"text": "planted"}, {"anchored_to": [cls.card]},
                                    ts="2026-10-24T09:12:00-07:00", key_dir=cls.kd)["line"]["id"]
        info = json.loads(Path(cls.two, "holon.json").read_text())
        info["id"] = cls.home_id
        Path(cls.two, "holon.json").write_text(json.dumps(info))
        # a record file that is a link to a file outside: never read
        cls.outside = os.path.join(cls.tmp, "outside.jsonl")
        line = record.make_line(B, B, record.holon_info(cls.cell)["id"], "say", {"text": "from outside"}, {"anchored_to": [cls.card]})
        Path(cls.outside).write_text(record.dumps(line) + "\n")
        cls.linked = line.get("id")
        os.symlink(cls.outside, os.path.join(cls.cell, "record", "person_linked.jsonl"))
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        env = dict(os.environ, HOME=cls.tmp, LIONSBERG_KEY_DIR=cls.kd)
        cls.log = open(os.path.join(cls.tmp, "serve.log"), "w")
        cls.srv = subprocess.Popen([sys.executable, "-I", str(SERVE), "--hq", cls.hq, "--actor", A,
                                    "--key", record.find_key(None, A, cls.kd), "--port", str(cls.port)],
                                   stdout=cls.log, stderr=cls.log, env=env, cwd=cls.tmp)
        for _ in range(60):
            try:
                cls.get("/state")
                break
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        try:
            cls.srv.wait(5)
        except subprocess.TimeoutExpired:
            cls.srv.kill()
        cls.log.close()

    @classmethod
    def get(cls, path, host=None):
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (cls.port, path), headers={"Host": host or "127.0.0.1:%d" % cls.port})
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r, timeout=20) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_the_story_oldest_first(self):
        s, o = self.get("/card/" + self.card)
        self.assertEqual(s, 200, o)
        ids = [l["id"] for l in o["lines"]]
        # the card, a say naming it, the commitment on it, the kept answering the commitment, the
        # card that waits on it, the unsigned say; never the unrelated card
        self.assertEqual(ids, [self.card, self.said, self.commit, self.kept, self.next, self.unsigned])
        self.assertNotIn(self.other, ids)
        signed = {l["id"]: l["signed"] for l in o["lines"]}
        self.assertTrue(signed[self.card])
        self.assertFalse(signed[self.unsigned])
        self.assertTrue(all("sig" not in l for l in o["lines"]))   # only whether it is signed, never the signature

    def test_never_outside_the_holons_served(self):
        s, o = self.get("/card/" + self.card)
        ids = [l["id"] for l in o["lines"]]
        self.assertNotIn(self.planted, ids)     # the cell claiming the home's id is refused
        self.assertNotIn(self.linked, ids)      # a linked record file is not read

    def test_an_unknown_id_is_an_empty_story(self):
        s, o = self.get("/card/" + "0" * 64)
        self.assertEqual((s, o["lines"]), (200, []))

    def test_only_on_its_own_host(self):
        s, o = self.get("/card/" + self.card, host="evil.example:%d" % self.port)
        self.assertEqual(s, 421)


if __name__ == "__main__":
    unittest.main()


class HandoffFold(unittest.TestCase):
    """A handoff waiting is one Deal card (DESIGN-BODIES §3.3, the acts build 2026-10-25): folded
    from a planted bg folder; its minutes from `review_min`; nothing else of the handoff in the
    state; answered (kept in the deal) after the person's witness today, gone after one before."""

    def setUp(self):
        self.mod = load_serve("serve_handoff_fold")
        self.tmp = Path(tempfile.mkdtemp(prefix="handoff-fold-"))
        self.bg = self.tmp / "bg"
        d = self.bg / "bg-Rigel"
        d.mkdir(parents=True)
        self.text = "# Handoff — Rigel\n\nSECRET WORDS OF THE HANDOFF\n\nreview_min: 7\n\nmore secret words\n"
        (d / "handoff.md").write_text(self.text)
        (d / "DONE").write_text("")
        self.size = len(self.text.encode())
        self.live = {"machine": [
            {"name": "prime", "kind": "prime"},
            {"name": "Rigel", "folder": "bg-Rigel", "kind": "background", "state": "archived",
             "handoff": {"present": True, "bytes": self.size}},
            {"name": "Vega", "folder": "bg-Vega", "kind": "background", "state": "running", "handoff": None},
        ]}
        self.words = lambda k, **kw: {"bodies.deal.handoff_q": "Read {name}'s handoff"}.get(k, k).replace("{name}", kw.get("name", ""))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fold(self, lines=()):
        st = {"deal": {"cards": [{"id": "a" * 64, "question": "Another card"}]}}
        live = json.loads(json.dumps(self.live))
        added = self.mod.fold_handoffs(st, live, self.bg, list(lines), A, "home-id", self.words)
        return st, live, added

    def test_card_folded_with_its_minutes_and_nothing_else(self):
        st, live, added = self.fold()
        cards = [c for c in st["deal"]["cards"] if c.get("section") == "handoff"]
        self.assertEqual(len(cards), 1)
        c = cards[0]
        self.assertEqual(c["question"], "Read Rigel's handoff")
        self.assertEqual(c["minutes"], 7)
        self.assertEqual(c["holon"], "home-id")
        self.assertEqual(len(c["options"]), 3)
        self.assertEqual(c["acts"][0]["type"], "witness")
        self.assertEqual(c["acts"][0]["body"]["handoff_bytes"], self.size)
        self.assertEqual(c["id"], self.mod.handoff_card_id("bg-Rigel", self.size))
        self.assertEqual(live["machine"][1]["handoff"]["review_min"], 7)
        self.assertIsNone(live["machine"][1]["handoff"]["reviewed"])
        blob = json.dumps(st) + json.dumps(live)
        self.assertNotIn("SECRET", blob)
        self.assertNotIn("secret words", blob)

    def test_witness_today_answers_it_and_an_older_one_removes_it(self):
        cid = self.mod.handoff_card_id("bg-Rigel", self.size)
        today = {"type": "witness", "actor": A, "ts": self.mod.now_iso(),
                 "body": {"handoff_of": "bg-Rigel", "handoff_bytes": self.size, "card": cid, "note": "Read"}}
        st, live, _ = self.fold([today])
        c = next(c for c in st["deal"]["cards"] if c.get("section") == "handoff")
        self.assertTrue(c.get("answered"))                 # the Deal's one truth: an answered card stays, answered
        self.assertEqual(live["machine"][1]["handoff"]["reviewed"], "read")
        old = dict(today, ts="2020-01-01T09:00:00-07:00")
        st, live, _ = self.fold([old])
        self.assertFalse([c for c in st["deal"]["cards"] if c.get("section") == "handoff"])
        archived = dict(today, body=dict(today["body"], archived=True))
        _, live, _ = self.fold([archived])
        self.assertEqual(live["machine"][1]["handoff"]["reviewed"], "archived")

    def test_another_persons_witness_or_another_size_is_no_review(self):
        cid = self.mod.handoff_card_id("bg-Rigel", self.size)
        theirs = {"type": "witness", "actor": B, "ts": self.mod.now_iso(),
                  "body": {"handoff_of": "bg-Rigel", "handoff_bytes": self.size, "card": cid}}
        resized = {"type": "witness", "actor": A, "ts": self.mod.now_iso(),
                   "body": {"handoff_of": "bg-Rigel", "handoff_bytes": self.size - 1}}
        st, _, _ = self.fold([theirs, resized])
        c = next(c for c in st["deal"]["cards"] if c.get("section") == "handoff")
        self.assertFalse(c.get("answered"))

    def test_an_old_handoff_rests(self):
        f = self.bg / "bg-Rigel" / "handoff.md"
        t = time.time() - 3 * 86400
        os.utime(f, (t, t))
        st, live, added = self.fold()
        self.assertEqual(added, [])
        self.assertEqual(live["machine"][1]["handoff"]["review_min"], 7)   # the rail still knows it

    def test_a_linked_handoff_is_not_folded(self):
        outside = self.tmp / "outside.md"
        outside.write_text("review_min: 3\n")
        d = self.bg / "bg-Link"
        d.mkdir()
        os.symlink(outside, d / "handoff.md")
        self.live["machine"].append({"name": "Link", "folder": "bg-Link", "kind": "background",
                                     "handoff": {"present": True, "bytes": 15}})
        st, _, _ = self.fold()
        self.assertEqual([c["body"] for c in st["deal"]["cards"] if c.get("section") == "handoff"], ["Rigel"])


class CostReader(unittest.TestCase):
    """What each body spent today, from a planted cost ledger (running totals per session, a reset,
    yesterday's lines as the baseline) and, for a session the ledger lacks, its transcript's usage."""

    def setUp(self):
        self.mod = load_serve("serve_cost_reader")
        self.tmp = Path(tempfile.mkdtemp(prefix="cost-reader-"))
        self.ledger = self.tmp / "cost-ledger.jsonl"
        self.today = time.strftime("%Y-%m-%d")
        self.yday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        self.s1, self.s2, self.s3 = ("11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222",
                                     "33333333-3333-3333-3333-333333333333")
        L = lambda d, t, s, c, cwd="/house": json.dumps({"ts": f"{d}T{t}", "session": s, "cost_usd": c, "model": "m", "cwd": cwd})
        self.ledger.write_text("\n".join([
            L(self.yday, "22:00:00", self.s1, 10.0),          # s1's total before today: 10
            L(self.today, "08:00:00", self.s1, 10.5),
            L(self.today, "09:00:00", self.s1, 12.0),          # s1 today: 2.00
            L(self.today, "08:10:00", self.s2, 0.4),           # s2 began today: 0.40 ...
            L(self.today, "08:20:00", self.s2, 0.1),           # ... a new process: counts from nothing, +0.10
            L(self.today, "08:30:00", self.s3, 5.0, "/elsewhere"),
        ]) + "\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ledger_day_per_session_and_appended_lines(self):
        cl = self.mod.CostLedger(str(self.ledger))
        today, cwds = cl.read()
        self.assertAlmostEqual(today[self.s1], 2.0)
        self.assertAlmostEqual(today[self.s2], 0.5)
        self.assertEqual(cwds[self.s3], "/elsewhere")
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps({"ts": f"{self.today}T10:00:00", "session": self.s1, "cost_usd": 12.75, "cwd": "/house"}) + "\n")
            fh.write('{"ts": "' + self.today + 'T10:01:00", "session": "' + self.s1)   # half written: waits
        today, _ = cl.read()
        self.assertAlmostEqual(today[self.s1], 2.75)

    def test_no_ledger_is_none_never_a_guess(self):
        cl = self.mod.CostLedger(str(self.tmp / "absent.jsonl"))
        self.assertEqual(cl.read(), (None, None))

    def test_bodies_live_house_total_and_transcript_fallback(self):
        import types
        house = self.tmp / "house"
        house.mkdir()
        sessions = self.tmp / "projects"
        slug = sessions / re.sub(r"[^A-Za-z0-9]", "-", str(house))
        slug.mkdir(parents=True)
        s4 = "44444444-4444-4444-4444-444444444444"
        now_iso = self.mod.now_iso()
        rows = [{"type": "assistant", "timestamp": now_iso, "message": {"id": "m1", "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 99999, "output_tokens": 40}}},
                {"type": "assistant", "timestamp": now_iso, "message": {"id": "m1", "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "output_tokens": 40}}},
                {"type": "assistant", "timestamp": "2020-01-01T00:00:00Z", "message": {"id": "m0", "usage": {"output_tokens": 5000}}},
                {"type": "user", "timestamp": now_iso, "message": {"content": "the words"}}]
        (slug / f"{s4}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        led = self.ledger.read_text().replace("/house", str(house))
        self.ledger.write_text(led)
        args = types.SimpleNamespace(bg=None, desk=None, sessions=str(sessions), heartbeat=None, usage_file=None,
                                     harness_sessions=str(self.tmp / "none"), cost_ledger=str(self.ledger))
        live = self.mod.BodiesLive(types.SimpleNamespace(args=args, hq=house))
        self.assertEqual(live.spent(self.s1, str(house)), {"usd": 2.0})
        self.assertEqual(live.spent(s4, str(house)), {"tokens": 150})     # once per message; cache reads left out
        self.assertIsNone(live.spent("55555555-5555-5555-5555-555555555555", str(house)))
        out = {"machine": [{"name": "prime", "kind": "prime", "session_id": self.s1}, {"name": "x", "kind": "window", "session_id": None}]}
        live._spent_all(out, house, time.time())
        self.assertEqual(out["machine"][0]["spent_today"], {"usd": 2.0})
        self.assertIsNone(out["machine"][1]["spent_today"])
        self.assertAlmostEqual(out["spent_today"]["usd"], 2.5)              # s1 and s2 in the house; s3 elsewhere


class HandoffRoute(unittest.TestCase):
    """GET /bodies/handoff: a machine body's handoff text, read-only; refused for a body with no
    folder of its own (the prime), and through a link (the folder or the file)."""

    def setUp(self):
        import types
        self.mod = load_serve("serve_handoff_route")
        self.tmp = Path(tempfile.mkdtemp(prefix="handoff-route-"))
        self.bg = self.tmp / "bg"
        (self.bg / "bg-Rigel").mkdir(parents=True)
        (self.bg / "bg-Rigel" / "handoff.md").write_text("What was done.\nreview_min: 4\n")
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "handoff.md").write_text("OUTSIDE WORDS\n")
        os.symlink(outside, self.bg / "bg-Linked")
        (self.bg / "bg-FileLink").mkdir()
        os.symlink(outside / "handoff.md", self.bg / "bg-FileLink" / "handoff.md")
        machine = [{"name": "prime", "kind": "prime"},
                   {"name": "Rigel", "folder": "bg-Rigel", "kind": "background"},
                   {"name": "Linked", "folder": "bg-Linked", "kind": "background"},
                   {"name": "FileLink", "folder": "bg-FileLink", "kind": "background"},
                   {"name": "window", "kind": "window"}]
        bg = self.bg
        self.hub = types.SimpleNamespace(fixture=None, args=types.SimpleNamespace(bg=str(bg)),
                                         bodies=types.SimpleNamespace(read=lambda: {"machine": machine}),
                                         bg_dir=lambda: bg)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ask(self, name):
        return self.mod.Hub.handoff_text(self.hub, name)

    def test_reads_a_machine_bodys_handoff(self):
        s, o = self.ask("rigel")
        self.assertEqual(s, 200)
        self.assertEqual(o["text"], "What was done.\nreview_min: 4\n")
        self.assertEqual(o["review_min"], 4)
        self.assertEqual(o["card"], self.mod.handoff_card_id("bg-Rigel", o["bytes"]))

    def test_refuses_links_and_bodies_without_a_folder(self):
        for name in ("Linked", "FileLink"):
            s, o = self.ask(name)
            self.assertEqual(s, 403, name)
            self.assertNotIn("OUTSIDE", json.dumps(o))
        self.assertEqual(self.ask("prime")[0], 409)
        self.assertEqual(self.ask("window")[0], 409)
        self.assertEqual(self.ask("nobody")[0], 404)
        self.assertEqual(self.ask("")[0], 400)

    def test_finds_a_host_workers_folder_when_bg_has_none(self):
        house = self.tmp / "house"
        (house / "bg" / "vega").mkdir(parents=True)
        (house / "bg" / "vega" / "handoff.md").write_text("Host worker done.\n")
        status = {"agents": [{"id": "mine", "name": None},
                             {"id": "w1", "body": {"name": "Vega", "task": "t", "cwd": str(house)}}]}
        import types
        self.hub.bridge = types.SimpleNamespace(call=lambda m, p, timeout=0: (200, status))
        self.assertFalse((self.bg / "vega").exists())
        s, o = self.ask("Vega")
        self.assertEqual(s, 200)
        self.assertEqual(o["text"], "Host worker done.\n")
        self.assertEqual(o["folder"], "vega")
        self.assertEqual(self.ask("nobody")[0], 404)


class QuietActs(unittest.TestCase):
    """A quiet act (`study`, `layout`) never wakes /stream: no bump when it is held or written, and
    the watch is handed its change so it lets it pass (each wake cost every page three /state
    reads and three redraws). Any other act still wakes it."""

    def setUp(self):
        import types
        self.mod = load_serve("serve_quiet_acts")
        self.tmp = Path(tempfile.mkdtemp(prefix="quiet-acts-"))
        names = ("hq shift_clock fixture actor key port verbose agents proxy routes vendors ask_wait phone phone_address "
                 "phone_port bg desk sessions harness_sessions heartbeat usage_file cost_ledger speech").split()
        args = types.SimpleNamespace(**{n: None for n in names})
        args.hq, args.fixture, args.port, args.proxy, args.phone = str(self.tmp / "hq"), "deal-rich", 0, "http://127.0.0.1:1", False
        args.verbose, args.shift_clock = False, False
        self.hub = self.mod.Hub(args)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, typ, body):
        holon = self.hub.home_holon()
        v0 = self.hub.version
        s, o = self.hub.act({"type": typ, "holon": holon, "body": body, "links": {}, "audience": "holon", "confirmed": True})
        self.assertEqual(s, 202, o)
        self.hub.pending[o["pending"]]["timer"].cancel()
        self.hub._write(o["pending"])
        return v0

    def test_quiet_acts_do_not_wake_the_stream(self):
        v0 = self.write("layout", {"name": "player", "views": ["deal"]})
        self.assertEqual(self.hub.version, v0)
        self.assertTrue(self.hub.quiet_pairs)
        pre, post = self.hub.quiet_pairs[-1]
        self.assertNotEqual(pre, post)
        self.assertEqual(post, self.hub._sig())          # the watch will see exactly this change, and let it pass
        v1 = self.write("study", {"view": "bodies", "measure": "first_act_ms", "value": 120})
        self.assertEqual(self.hub.version, v1)

    def test_other_acts_still_wake_it(self):
        v0 = self.write("say", {"text": "a line"})
        self.assertGreater(self.hub.version, v0)


class ChiefOfStaffCharacter(unittest.TestCase):
    """The Talk's agent is the chief of staff (skills/the-chief-of-staff/SKILL.md): the character sent on
    session/new names the skill and carries its four rules; a worker's brief carries its three lines and
    not the office; a row with its own character keeps it. Proved through the stand-in agent, which says
    back the character it was given."""

    RULES = ("Speak from the record", "One question at a time", "No figures unasked", "The cost before a worker")
    WORKER = ("report in one handoff line", "ask the chief of staff, never the person", "Never speak to the person unasked")

    def _host(self, rows):
        import importlib.util
        import types
        spec = importlib.util.spec_from_file_location("agent_host_cos", ENGINE.parent / "hud" / "agent_host.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.RecordWatch.__init__ = lambda self, host, start=True: None   # no watching in a test
        (self.tmp / "agents.json").write_text(json.dumps({"agents": rows}))
        host = mod.Host(types.SimpleNamespace(hq=str(self.tmp / "hq"), agents=str(self.tmp / "agents.json"),
                                              ask_wait=900, person=A))
        return mod, host

    def _said_back(self, host, conv, needles):
        """The agent's words in this conversation, once every needle is in them (the stand-in speaks a
        word at a time) or the turn ended, at most forty seconds."""
        said = ""
        for _ in range(400):
            evs = list(host.convs[conv].events)
            said = "".join(e.get("text", "") for e in evs if e.get("kind") == "agent")
            if all(n in said for n in needles) or any(e.get("kind") == "turn_end" for e in evs):
                return said
            time.sleep(0.1)
        return said

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="host-cos-"))
        self.fake = ENGINE.parent / "hud" / "fixtures" / "fake_agent.py"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_talk_agent_is_the_chief_of_staff(self):
        mod, host = self._host([{"id": "yours", "of": A, "kind": "harness",
                                 "command": [sys.executable, str(self.fake)], "cwd": str(self.tmp)}])
        ch = mod.DEFAULT_CHARACTER
        self.assertIn("skills/the-chief-of-staff/SKILL.md", ch)
        self.assertTrue((ENGINE.parent / "skills" / "the-chief-of-staff" / "SKILL.md").is_file())
        for rule in self.RULES:
            self.assertIn(rule, ch)
        for word in ("S" + "ir", "prom" + "ise", "n't", "Claude"):   # the kit lint: no honorific, the older word, no contraction
            self.assertNotIn(word, ch)
        s, o = host.wake({"agent": "yours"})
        self.assertEqual(s, 200, o)
        s, o = host.say({"agent": "yours", "conversation": o["conversation"], "text": "What were you given?"})
        self.assertEqual(s, 200, o)
        said = self._said_back(host, o["conversation"], ("skills/the-chief-of-staff/SKILL.md",) + self.RULES)
        self.assertIn("skills/the-chief-of-staff/SKILL.md", said)        # what session/new carried
        for rule in self.RULES:
            self.assertIn(rule, said)
        host.agents["yours"]._end()

    def test_a_worker_brief_and_not_the_office(self):
        mod, host = self._host([{"id": "yours", "of": A, "kind": "harness",
                                 "command": [sys.executable, str(self.fake)], "cwd": str(self.tmp)}])
        for line in self.WORKER:
            self.assertIn(line, mod.BODY_BRIEF)
        s, o = host.body({"task": "Who are you? Then draft the harvest notes.", "cwd": str(self.tmp)})
        self.assertEqual(s, 200, o)
        a = host.agents[o["agent"]]
        for line in self.WORKER:
            self.assertIn(line, a.row["character"])
        self.assertNotIn("chief of staff: you hold", a.row["character"])  # a worker is not the office
        self.assertTrue(a.row["character"].startswith(mod.WORKER_CHARACTER))
        said = self._said_back(host, o["conversation"], self.WORKER)
        self.assertIn("ask the chief of staff, never the person", said)  # what its session/new carried
        a._end()

    def test_a_row_with_its_own_character_keeps_it(self):
        mod, host = self._host([{"id": "yours", "of": A, "kind": "harness", "character": "Be brief.",
                                 "command": [sys.executable, str(self.fake)], "cwd": str(self.tmp)}])
        self.assertEqual(host.agents["yours"].character(), "Be brief.")
        s, o = host.body({"task": "Read the rooms.", "cwd": str(self.tmp)})
        self.assertEqual(s, 200, o)
        a = host.agents[o["agent"]]
        self.assertTrue(a.row["character"].startswith("Be brief."))
        self.assertIn("report in one handoff line", a.row["character"])
        a._end()


class AgentHostBody(unittest.TestCase):
    """agent_host.py's POST /body: a second body of the player's agent, from the agents file, with
    a name of its own, its brief as its character, the house as its cwd; an empty task refused."""

    def test_body_started_and_kept(self):
        import importlib.util
        import types
        spec = importlib.util.spec_from_file_location("agent_host_body", ENGINE.parent / "hud" / "agent_host.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = Path(tempfile.mkdtemp(prefix="host-body-"))
        try:
            fake = ENGINE.parent / "hud" / "fixtures" / "fake_agent.py"
            (tmp / "agents.json").write_text(json.dumps({"agents": [{"id": "yours", "of": A, "kind": "harness",
                                                                     "command": [sys.executable, str(fake)], "cwd": str(tmp)}]}))
            page = tmp / "SKILL.md"
            page.write_text("how a background body works\n")
            mod.RecordWatch.__init__ = lambda self, host, start=True: None   # no watching in a test
            host = mod.Host(types.SimpleNamespace(hq=str(tmp / "hq"), agents=str(tmp / "agents.json"), ask_wait=900, person=A))
            self.assertEqual(host.body({"task": "  "})[0], 400)
            s, o = host.body({"task": "Read the rooms.", "cwd": str(tmp), "brief_page": str(page), "taken": ["Vega"]})
            self.assertEqual(s, 200, o)
            self.assertEqual(o["name"], "Rigel")                          # Vega is taken on this machine
            a = host.agents[o["agent"]]
            self.assertEqual(a.cwd, str(tmp))
            self.assertIn(str(page), a.row["character"])
            self.assertIn("bg/rigel/", a.row["character"])
            f = a.facts()
            self.assertEqual(f["body"]["task"], "Read the rooms.")
            self.assertEqual(f["name"], "Rigel")
            kept = json.loads((tmp / "hq" / ".agent-host-bodies.json").read_text())
            self.assertEqual([r["id"] for r in kept["bodies"]], [o["agent"]])
            for _ in range(50):
                if any(e.get("kind") == "user" for e in host.convs[o["conversation"]].events):
                    break
                time.sleep(0.1)
            self.assertEqual(next(e for e in host.convs[o["conversation"]].events if e.get("kind") == "user")["text"], "Read the rooms.")
            a._end()
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


FAKE_VOICE = r'''import sys, os, time, wave, tempfile
words = sys.argv[-1]
side = os.environ.get("FAKE_VOICE_SAID")
if side:
    open(side, "w").write(words)
how = os.environ.get("FAKE_VOICE_HOW", "wav")
if how == "fail":
    sys.exit(3)
fd, path = tempfile.mkstemp(suffix=".wav", dir=os.environ.get("FAKE_VOICE_DIR"))
os.close(fd)
if how == "text":
    open(path, "w").write("not a sound at all")
else:
    w = wave.open(path, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b"\x00\x00" * 80); w.close()
if how == "old":
    os.utime(path, (time.time() - 3600, time.time() - 3600))
if how == "link":
    os.symlink(path, path + ".link.wav"); path = path + ".link.wav"
print("rendered")
print(path)
'''


class VoiceSay(unittest.TestCase):
    """The --voice contract (serve.py's header): a fake text-to-speech command that writes a tiny WAV
    is run without a shell with the words as its last argument; its new WAV is answered and deleted;
    a non-WAV, an old file, a link, a failure and no command are refused, and nothing else is
    deleted. Then over HTTP: /voice/say answers audio/wav with the page's token and only with it,
    and /voice/info says what this server can do. Nothing is played; no sound."""

    def setUp(self):
        self.mod = load_serve("serve_voice_say")
        self.tmp = Path(tempfile.mkdtemp(prefix="voice-say-"))
        self.script = self.tmp / "fake voice.py"          # a space in the path: the command is split like a shell line
        self.script.write_text(FAKE_VOICE)
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.said = self.tmp / "said.txt"
        self.cmd = f'{sys.executable} -I "{self.script}"'
        self.env0 = dict(os.environ)
        os.environ.update(FAKE_VOICE_DIR=str(self.out), FAKE_VOICE_SAID=str(self.said), FAKE_VOICE_HOW="wav")

    def tearDown(self):
        import shutil
        os.environ.clear()
        os.environ.update(self.env0)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_renders_and_deletes_its_own_wav(self):
        s, data = self.mod.render_voice(self.cmd, "  --Good morning.\n Two things need you.  ")
        self.assertEqual(s, 200)
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WAVE")
        self.assertEqual(self.said.read_text(), "Good morning. Two things need you.")   # last argument, never an option
        self.assertEqual(list(self.out.iterdir()), [])                                 # its file is deleted

    def test_refuses_what_is_not_a_new_wav_and_deletes_nothing(self):
        for how in ("text", "old", "link"):
            os.environ["FAKE_VOICE_HOW"] = how
            s, o = self.mod.render_voice(self.cmd, "Hello.")
            self.assertEqual(s, 422, how)
            self.assertIn("refused", o)
            self.assertTrue(list(self.out.iterdir()), how)                             # nothing of theirs was removed
            for f in self.out.iterdir():
                f.unlink()
        os.environ["FAKE_VOICE_HOW"] = "fail"
        self.assertEqual(self.mod.render_voice(self.cmd, "Hello.")[0], 422)
        self.assertEqual(self.mod.render_voice(None, "Hello.")[0], 501)
        self.assertEqual(self.mod.render_voice(self.cmd, "  -- ")[0], 400)
        self.assertEqual(self.mod.render_voice(self.cmd, "x" * 9000)[0], 422)            # failing command still refused
        self.assertLessEqual(len(self.said.read_text()), self.mod.VOICE_TEXT_MAX)

    def test_over_http_with_the_token_only(self):
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        log = open(self.tmp / "serve.log", "w")
        srv = subprocess.Popen([sys.executable, "-I", str(SERVE), "--fixture", "fresh", "--hq", str(self.tmp / "hq"),
                                "--port", str(port), "--voice", self.cmd], stdout=log, stderr=log, cwd=str(self.tmp))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            token = None
            for _ in range(100):
                try:
                    with opener.open(f"http://127.0.0.1:{port}/token", timeout=2) as r:
                        token = json.loads(r.read())["token"]
                        break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.1)
            self.assertTrue(token)

            def call(path, body=None, tk=token):
                req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if body is not None else "GET",
                                             data=json.dumps(body).encode() if body is not None else None,
                                             headers={"Content-Type": "application/json", **({"X-HUD-Token": tk} if tk else {})})
                try:
                    with opener.open(req, timeout=20) as r:
                        return r.status, r.headers.get("Content-Type"), r.read()
                except urllib.error.HTTPError as e:
                    return e.code, e.headers.get("Content-Type"), e.read()

            s, ct, body = call("/voice/info")
            self.assertEqual((s, json.loads(body)), (200, {"hear": False, "say": True}))
            self.assertEqual(call("/voice/info", tk=None)[0], 403)
            s, ct, body = call("/voice/say", {"text": "That is all I need from you today."})
            self.assertEqual(s, 200)
            self.assertEqual(ct, "audio/wav")
            self.assertEqual(body[:4], b"RIFF")
            self.assertEqual(call("/voice/say", {"text": "Hello."}, tk=None)[0], 403)
            self.assertEqual(call("/voice", {})[0], 501)                       # no speech command: the note path says so
        finally:
            srv.terminate()
            srv.wait(5)
            log.close()


class PhoneDoorTLS(unittest.TestCase):
    """The phone door speaks TLS (a phone's browser gives the microphone only to a secure page):
    its certificates are made once with the standard library, kept 0600 and ignored by git; the
    door's certificate names the bound address; the plain-http address serves only the trust page
    and this computer's authority and refuses everything else, the microphone's routes first."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import types
        spec = importlib.util.spec_from_file_location("phone_cert_test", ENGINE.parent / "hud" / "phone_cert.py")
        cls.pc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pc)
        cls.mod = load_serve("serve_phone_tls")
        cls.mod.address_allowed = lambda a: True          # loopback stands in for the private address here
        cls.tmp = Path(tempfile.mkdtemp(prefix="phone-tls-"))
        ports = []
        for _ in range(8):
            with socket.socket() as sk:
                sk.bind(("127.0.0.1", 0))
                ports.append(sk.getsockname()[1])
        door = next(p for p in ports if p + 1 not in ports and cls._free(p + 1))
        names = ("hq shift_clock fixture actor key port verbose agents proxy routes vendors ask_wait phone phone_address "
                 "phone_port bg desk sessions harness_sessions heartbeat usage_file cost_ledger speech voice").split()
        args = types.SimpleNamespace(**{n: None for n in names})
        args.hq, args.fixture, args.port, args.proxy = str(cls.tmp / "hq"), "deal-rich", 0, "http://127.0.0.1:1"
        args.verbose, args.shift_clock, args.phone = False, False, True
        args.phone_address, args.phone_port = "127.0.0.1", door
        cls.hub = cls.mod.Hub(args)
        cls.mod.Handler.hub = cls.hub
        s, o = cls.hub.phone.listen(True)
        assert s == 200, o
        cls.door, cls.plain = door, door + 1
        cls.ca_pem = Path(cls.hub.phone.trust["ca_der"]).with_name("ca.pem")

    @staticmethod
    def _free(port):
        with socket.socket() as sk:
            try:
                sk.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    @classmethod
    def tearDownClass(cls):
        import shutil
        cls.hub.phone.listen(False)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def plain_call(self, method, path):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.plain, timeout=10)
        try:
            c.request(method, path, body=b"x" if method == "POST" else None)
            r = c.getresponse()
            return r.status, r.getheader("Content-Type"), r.read()
        finally:
            c.close()

    def tls_call(self, method, path, body=None, device=None, ca=True):
        import http.client
        import ssl
        ctx = ssl.create_default_context(cafile=str(self.ca_pem)) if ca else ssl.create_default_context()
        c = http.client.HTTPSConnection("127.0.0.1", self.door, timeout=10, context=ctx)
        try:
            hdr = {"Content-Type": "application/json", **({"X-HUD-Device": device} if device else {})}
            c.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=hdr)
            cert = c.sock.getpeercert()
            r = c.getresponse()
            return r.status, r.read(), cert
        finally:
            c.close()

    def test_plain_door_serves_only_the_trust_page_and_the_authority(self):
        import hashlib
        s, ct, page = self.plain_call("GET", "/?pair=123456")
        self.assertEqual((s, ct), (200, "text/html; charset=utf-8"))
        fp = self.hub.phone.trust["fingerprint"]
        self.assertIn(fp, page.decode())
        self.assertIn(f"https://127.0.0.1:{self.door}/?pair=123456", page.decode())
        s, ct, der = self.plain_call("GET", "/phone-door.crt")
        self.assertEqual((s, ct), (200, "application/x-x509-ca-cert"))
        self.assertEqual(":".join(f"{b:02X}" for b in hashlib.sha256(der).digest()), fp)
        for method, path in (("POST", "/voice"), ("POST", "/voice/say"), ("GET", "/voice/info"), ("GET", "/state"),
                             ("GET", "/stream"), ("POST", "/phone/claim"), ("GET", "/index.html"), ("GET", "/token"),
                             ("GET", "/dock.js"), ("DELETE", "/phone/d-1")):
            s, ct, body = self.plain_call(method, path)
            self.assertEqual(s, 403, (method, path))
            self.assertTrue(ct.startswith("text/plain"))
            self.assertEqual(body.decode().count("\n"), 1, "one sentence")
            self.assertIn(f"https://127.0.0.1:{self.door}/", body.decode())

    def test_tls_door_serves_and_names_the_bound_address(self):
        import ssl
        s, body, cert = self.tls_call("GET", "/state")
        self.assertEqual(s, 403)                                         # no device token, no state
        self.assertEqual(cert["subjectAltName"], (("IP Address", "127.0.0.1"),))
        s, o = self.hub.phone.pair()
        self.assertTrue(o["address"].startswith(f"http://127.0.0.1:{self.plain}/?pair="))
        self.assertEqual(o["door"], f"https://127.0.0.1:{self.door}/?pair={o['code']}")
        self.assertEqual(o["fingerprint"], self.hub.phone.trust["fingerprint"])
        s, body, _ = self.tls_call("POST", "/phone/claim", {"code": o["code"], "name": "a test phone"})
        self.assertEqual(s, 200)
        token = json.loads(body)["token"]
        s, body, _ = self.tls_call("GET", "/state", device=token)
        self.assertEqual(s, 200)
        state = json.loads(body)
        self.assertEqual(state["hud"]["phone"]["trust"]["fingerprint"], self.hub.phone.trust["fingerprint"])
        self.assertEqual(state["hud"]["phone"]["door"], f"https://127.0.0.1:{self.door}/")
        self.assertEqual(self.tls_call("POST", "/voice", {}, device=token)[0], 501)     # reached; no --speech here
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.tls_call("GET", "/state", ca=False)                    # untrusted until the phone trusts it

    def test_files_are_private_and_ignored_by_git(self):
        d = Path(self.hub.phone.trust["cert"]).parent
        self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(d.parent).st_mode & 0o777, 0o700)
        for f in d.iterdir():
            self.assertEqual(os.stat(f).st_mode & 0o777, 0o600, f.name)
        kit = ENGINE.parent
        for rel in (".phone-door/127.0.0.1/ca.key", "cells/a/.phone-door/10.0.0.2/door.key", ".hud-devices"):
            r = subprocess.run(["git", "-C", str(kit), "check-ignore", "-q", "--no-index", rel], capture_output=True)
            if r.returncode == 128:
                self.skipTest("git is not here to ask")
            self.assertEqual(r.returncode, 0, rel)

    def test_rotation_quiet_for_the_leaf_and_said_for_the_authority(self):
        from datetime import datetime, timedelta, timezone
        pc = self.pc
        pc.KEY_BITS = 1024           # speed only; the door itself always makes 2048-bit keys
        try:
            hq = self.tmp / "rotate"
            hq.mkdir()
            now = datetime.now(timezone.utc)
            m0 = pc.ensure(hq, "10.1.2.3", now)
            self.assertEqual(m0["renewed"], ["ca", "leaf"])
            self.assertEqual(pc.ensure(hq, "10.1.2.3", now)["renewed"], [])
            m1 = pc.ensure(hq, "10.1.2.3", now + timedelta(days=25))          # the leaf near its thirty days
            self.assertEqual(m1["renewed"], ["leaf"])
            self.assertEqual(m1["fingerprint"], m0["fingerprint"])
            m2 = pc.ensure(hq, "10.1.2.3", now + timedelta(days=360))         # the authority near its year
            self.assertEqual(m2["renewed"], ["ca", "leaf"])
            self.assertNotEqual(m2["fingerprint"], m0["fingerprint"])
            self.assertEqual(m2["prior_fingerprint"], m0["fingerprint"])
            der = (hq / ".phone-door" / "10.1.2.3" / "ca.crt").read_bytes()
            self.assertEqual(pc.not_after(der).date(), (now + timedelta(days=360 + pc.CA_DAYS)).date())
        finally:
            pc.KEY_BITS = 2048


class WorkerProposalAsk(unittest.TestCase):
    """agent_host.py: the chief of staff only proposes a worker (skills/the-chief-of-staff §4, 9); a
    turn that ends with the proposal in its form ("The task, in your words: ...", then "Start it?")
    becomes an ask of kind `worker` carrying the task; Not now answers it and tells the agent; nothing
    is started by the host."""

    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("agent_host_worker", ENGINE.parent / "hud" / "agent_host.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_form_is_read_and_nothing_is_guessed(self):
        wp = self.load().worker_proposal
        self.assertEqual(wp("About an hour. The task, in your words: draw the map of the commons. It writes in its own folder. Start it?"),
                         "draw the map of the commons")
        self.assertEqual(wp("The task, in your words: “draft the harvest notes”.\nStart it?"), "draft the harvest notes")
        self.assertIsNone(wp("The task, in your words: draw it. Shall I?"))          # no "Start it?" at the end
        self.assertIsNone(wp("I could have a worker draw it. Start it?"))            # no task in the form
        self.assertIsNone(wp(""))

    def test_a_proposal_becomes_a_worker_ask(self):
        import types
        mod = self.load()
        tmp = Path(tempfile.mkdtemp(prefix="host-worker-"))
        try:
            fake = ENGINE.parent / "hud" / "fixtures" / "fake_agent.py"
            (tmp / "agents.json").write_text(json.dumps({"agents": [{"id": "yours", "of": A, "kind": "harness",
                                                                     "command": [sys.executable, str(fake)], "cwd": str(tmp)}]}))
            mod.RecordWatch.__init__ = lambda self, host, start=True: None
            host = mod.Host(types.SimpleNamespace(hq=str(tmp / "hq"), agents=str(tmp / "agents.json"), ask_wait=900, person=A))
            s, o = host.say({"agent": "yours", "text": "have a worker draw the map of the commons"})
            self.assertEqual(s, 200, o)
            conv = host.convs[o["conversation"]]
            ask = None
            for _ in range(100):
                ask = next((e["ask"] for e in conv.events if e.get("kind") == "ask"), None)
                if ask:
                    break
                time.sleep(0.1)
            self.assertIsNotNone(ask, [e.get("kind") for e in conv.events])
            self.assertEqual(ask["kind"], "worker")
            self.assertEqual(ask["task"], "draw the map of the commons")
            self.assertFalse(ask["leaves"])
            self.assertEqual([x["name"] for x in ask["options"]], ["Start the worker", "Not now"])
            a = host.agents["yours"]
            self.assertEqual(a.answer(ask["id"], "not_this")[0], 200)
            self.assertTrue(any(e.get("kind") == "answered" and e.get("ask") == ask["id"] for e in conv.events))
            a._end()
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class AgentHostOwner(unittest.TestCase):
    """serve.py's host bridge: the server writes its pid and port beside the host's in <HQ>/.agent-host,
    stops the host it holds on its own exit (SIGTERM here), refuses to start beside another live
    server's live host with a one-line reason, and cleans a dead entry."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="host-owner-"))
        self.hq = self.tmp / "hq"
        self.hq.mkdir()
        self.procs = []

    def tearDown(self):
        import shutil
        for p in self.procs:
            try:
                p.kill()
                p.wait(5)
            except (OSError, subprocess.SubprocessError):
                pass
            for f in (p.stdout, p.stderr):
                if f:
                    f.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def free(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def serve(self):
        port = self.free()
        p = subprocess.Popen([sys.executable, "-I", str(SERVE), "--fixture", "empty", "--port", str(port), "--hq", str(self.hq)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        for _ in range(100):
            if p.poll() is not None:
                return p, port
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/token", timeout=0.5):
                    return p, port
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        return p, port

    def host(self):
        """A stand-in host: a sleeping process in its own session, named in .agent-host with no server."""
        h = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)
        self.procs.append(h)
        (self.hq / ".agent-host").write_text(json.dumps({"port": 1, "pid": h.pid, "started": "now", "epoch": "e"}) + "\n")
        return h

    def entry(self):
        try:
            return json.loads((self.hq / ".agent-host").read_text())
        except (OSError, ValueError):
            return None

    def test_held_refused_and_stopped(self):
        h = self.host()
        a, _ = self.serve()
        self.assertIsNone(a.poll())
        self.assertEqual(self.entry()["server"]["pid"], a.pid)         # adopted: its pid beside the host's
        b, _ = self.serve()                                             # a second server, the same home
        b.wait(10)
        self.assertNotEqual(b.returncode, 0)
        err = b.stderr.read().strip().splitlines()
        self.assertTrue(err and "another server" in err[-1], err)
        self.assertIsNone(h.poll())                                     # the refusal touched nothing
        a.terminate()
        a.wait(10)
        for _ in range(50):
            if h.poll() is not None:
                break
            time.sleep(0.1)
        self.assertIsNotNone(h.poll(), "the host outlived the server that held it")
        self.assertIsNone(self.entry())

    def test_a_dead_entry_is_cleaned(self):
        h = subprocess.Popen([sys.executable, "-c", "pass"])
        h.wait(5)
        (self.hq / ".agent-host").write_text(json.dumps({"port": 1, "pid": h.pid, "server": {"pid": h.pid, "port": 1}}) + "\n")
        a, _ = self.serve()
        self.assertIsNone(a.poll())
        self.assertIsNone(self.entry())


class AgentHouse(unittest.TestCase):
    """/agent/say carries what the house holds now (so the agent never says "no one
    waiting on you" beside a card that says the steward waits, and can see what she has just
    answered): the Deal's cards with their by-when, the open owed entries with each holder by name, the
    served clock's day; and the one service the vendors file names, for the first-contact sentence."""

    def setUp(self):
        self.mod = load_serve("serve_agent_house")
        self.tmp = Path(tempfile.mkdtemp(prefix="agent-house-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def handler(self, vendors=None):
        import types
        args = types.SimpleNamespace(**{n: None for n in PersonServed.NAMES})
        args.hq, args.fixture, args.port, args.proxy = str(self.tmp / "hq"), "deal-rich", 0, "http://127.0.0.1:1"
        args.verbose, args.shift_clock, args.phone = False, True, False
        if vendors is not None:
            (self.tmp / "vendors.json").write_text(json.dumps({"vendors": vendors}))
            args.vendors = str(self.tmp / "vendors.json")
        else:
            args.vendors = str(self.tmp / "none.json")
        h = self.mod.Handler.__new__(self.mod.Handler)
        h.hub = self.mod.Hub(args)
        return h

    def test_the_house_rides_with_the_line(self):
        h = self.handler()
        st = h.hub.state()
        house = h._agent_house(st)
        self.assertEqual(house["today"], st["hud"]["now"][:10])
        self.assertEqual(house["person"], "person:player")
        self.assertEqual(house["person_name"], "Player")                      # the house's name for her
        first = house["deal"][0]
        self.assertTrue(first["question"].startswith("Cell Two asked for the harvest count"))
        self.assertIn("steward is waiting on it", first["why"])
        self.assertEqual(first["recommendation"], "Yes, send it today")
        self.assertRegex(first["due"], r"^\d{4}-\d{2}-\d{2}$")             # joined from the owed entry
        held = {e["title"]: e for e in house["owed"]}
        self.assertEqual(held["Carry the long tables from the Commons"]["holder"], "person:weaver")
        self.assertEqual(held["Send the harvest count to Cell Two"]["holon_name"], "Cell Two")
        self.assertTrue(all(e["status"] in (None, "open") for e in house["owed"]))

    def test_the_service_named(self):
        self.assertIsNone(self.handler()._agent_vendor())                     # no vendors file: unnamed
        local = {"local": {"kind": "openai", "scheme": "http", "host": "127.0.0.1"}}
        self.assertEqual(self.handler(dict(local, anthropic={"kind": "anthropic", "host": "api.anthropic.com"}))._agent_vendor(),
                         "Anthropic")
        self.assertEqual(self.handler({"r": {"kind": "openai", "host": "openrouter.ai", "name": "OpenRouter"}})._agent_vendor(),
                         "OpenRouter")
        two = {"a": {"kind": "anthropic", "host": "api.anthropic.com"}, "r": {"kind": "openai", "host": "openrouter.ai"}}
        self.assertIsNone(self.handler(two)._agent_vendor())                  # two alike: unnamed
        two["r"]["default"], two["r"]["name"] = True, "OpenRouter"
        self.assertEqual(self.handler(two)._agent_vendor(), "OpenRouter")     # the default one wins
        self.assertIsNone(self.handler(local)._agent_vendor())                # only this computer's


class PersonServed(unittest.TestCase):
    """hud.person (the Talk's welcome by name, the dock's "who brought you"): the person's name and
    handle, and who brought them with their house and reach; from the fixture's actors and holons,
    or from a home's join lines (never the inception line's name, which is the house's)."""

    NAMES = ("hq shift_clock fixture actor key port verbose agents proxy routes vendors ask_wait phone phone_address "
             "phone_port bg desk sessions harness_sessions heartbeat usage_file cost_ledger speech voice").split()

    def setUp(self):
        self.mod = load_serve("serve_person")
        self.tmp = Path(tempfile.mkdtemp(prefix="person-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def hub(self, hq, fixture=None):
        import types
        args = types.SimpleNamespace(**{n: None for n in self.NAMES})
        args.hq, args.fixture, args.port, args.proxy = str(hq), fixture, 0, "http://127.0.0.1:1"
        args.verbose, args.shift_clock, args.phone = False, False, False
        return self.mod.Hub(args)

    def test_fixture_names_the_person_and_the_witness(self):
        p = self.hub(self.tmp / "hq", "deal-rich").state()["hud"]["person"]
        self.assertEqual(p, {"name": "Player", "handle": "player",
                             "brought_by": {"name": "Cell Two's steward", "house": "Cell Two",
                                            "reach": "mailto:steward@cell-two.example"}})

    def test_live_reads_the_join_lines(self):
        hq, cell, C = self.tmp / "hq", self.tmp / "hq" / "cells" / "one", "person:carol"
        holon.init(str(hq), "Alice's home", "person", A, sign=False, ts="2026-10-24T08:00:00-07:00")
        cell.parent.mkdir()
        holon.init(str(cell), "One", "cell", C, sign=False, ts="2026-10-24T09:00:00-07:00")
        record.append(str(cell), C, C, "join", {"who": C, "role": "member", "name": "Carol",
                                                 "reach": ["ftp://no", "mailto:carol@example.org"]},
                      sign=False, ts="2026-10-24T09:00:30-07:00")
        record.append(str(cell), C, C, "join", {"who": A, "role": "member", "name": "Alice"},
                      sign=False, ts="2026-10-24T09:01:00-07:00")
        p = self.hub(hq).state()["hud"]["person"]
        self.assertEqual(p, {"name": "Alice", "handle": "alice",
                             "brought_by": {"name": "Carol", "house": "One", "reach": "mailto:carol@example.org"}})

    def test_live_with_nothing_said_is_null(self):
        hq = self.tmp / "hq"
        holon.init(str(hq), "Alice's home", "person", A, sign=False, ts="2026-10-24T08:00:00-07:00")
        p = self.hub(hq).state()["hud"]["person"]
        self.assertEqual(p, {"name": None, "handle": "alice", "brought_by": None})   # the house's name is not hers
