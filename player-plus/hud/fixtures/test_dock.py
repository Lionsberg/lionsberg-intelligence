#!/usr/bin/env python3
"""test_dock.py: the dock's host, proven against the stand-in agent. Standard library only.

    python3 -I hud/fixtures/test_dock.py

A throwaway home under the system's temporary folder; the host on 127.0.0.1 at a port of its
own; the stand-in agent (fake_agent.py). Proves, after the real-agent test of 2026-10-24:
  - a picked-up conversation (session/load) does not repeat its history: nothing replayed is
    shown, kept in .said/, or taken as the first word of the new turn;
  - a line the agent wrote to the record with the kit's own scripts appears as a margin line;
  - the agent's line just before an ask reaches the ask's card;
  - the agents file's character reaches the agent as its first system-style context;
  - first contact never waits on a tool: the five kinds of first-contact line are answered by the
    host at once (`local` in /say's answer, a `local` event), and the agent adds without repeating;
  - the page's context reaches the agent as a note before the person's words;
  - an act the agent proposes ("Shall I mark: ..., for ...? Yes?") becomes an ask of kind `act`
    resolved against the served Deal, and is answered; an unresolved one raises nothing;
  - at most one ask is in front of the person at a time; a second waits behind it;
  - a read the house allows asks nothing (quiet_read);
  - the ask card's face is in words, its exact step behind one fold (test_dock_card.mjs, with node);
  - the command line's stripper keeps spaces and drops control strings whole (with node);
  - the layered voice and voice mode (test_dock_voice.mjs, with node and muted Chrome);
  - the agent knows its own page (the microphone, Voice mode, the places
    behind More); a change to any page is asked in words, its step a sentence and the raw step in `raw`;
    one Start card per worker task, and the start told by the worker's name; what it decides at her word
    becomes `decided` for a suggested choice only; no Mark card for what the page settled at her words;
    two streamed messages never glued; the voice receives a feeling; one name; the one first;
  - the trust layer (DESIGN-TALK.md): the harness's figures per agent in /status and every
    `state` event, each real or null and the stand-in marked; each turn's accounting (`turn_end`); the
    thinking clock and the thinking summaries; worker rows; the harness's own modes and its own options
    under every ask; notices said plainly; GET /figures with every raw field, behind the token;
  - the chain's watch: every worker carries a box of minutes from its
    proposal; a worker past half again its box gives the chief of staff a turn, and its three answers are
    parsed (a new box, a task note, a second proposal), once per box and never twice in ten minutes; a
    proposal that would wait on another worker is refused until the result's shape is written; the
    half-hour look shows the chain and says nothing to the person unless something moved (a short minute
    stands in for the clock).
Nothing leaves this machine; no sound.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import importlib.util
from datetime import datetime
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HUD = HERE.parent
ENGINE = HUD.parent / "engine"
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


record = load("dock_test_record", ENGINE / "record.py")
host_mod = load("dock_test_host", HUD / "agent_host.py")


class Host:
    def __init__(self, hq, extra=()):
        self.hq = hq
        log = open(hq / ".agent-host.log", "a")
        try:
            (hq / ".agent-host").unlink()
        except FileNotFoundError:
            pass
        self.proc = subprocess.Popen([sys.executable, "-I", str(HUD / "agent_host.py"), "--hq", str(hq)] + list(extra),
                                     stdout=log, stderr=log, start_new_session=True)
        log.close()
        for _ in range(100):
            try:
                self.port = json.loads((hq / ".agent-host").read_text())["port"]
                break
            except (OSError, ValueError, KeyError):
                time.sleep(0.05)
        self.token = (hq / ".hud-token").read_text().strip()

    def call(self, method, path, body=None):
        data = json.dumps(body or {}).encode() if method == "POST" else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method,
                                     headers={"X-HUD-Token": self.token, "Content-Type": "application/json"})
        with NO_PROXY.open(req, timeout=10) as r:
            return json.loads(r.read())

    def events_until(self, conv, since, pred, timeout=20):
        """Read the stream from `since` until pred(events) holds; returns the events read."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/stream?conversation={conv}&since={since}",
                                     headers={"X-HUD-Token": self.token})
        out, end = [], time.time() + timeout
        with NO_PROXY.open(req, timeout=timeout) as r:
            for raw in r:
                line = raw.decode().strip()
                if line.startswith("data: "):
                    out.append(json.loads(line[6:]))
                    if pred(out):
                        return out
                if time.time() > end:
                    break
        raise AssertionError("the stream did not show what was awaited: %r" % [e.get("kind") for e in out])

    def get(self, path, token=True):
        """A GET that returns (status, body), refusals included."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     headers={"X-HUD-Token": self.token} if token else {})
        try:
            with NO_PROXY.open(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def bodies(self):
        return self.hq / ".agent-host-bodies.json"

    def agent(self, aid):
        return next(a for a in self.call("GET", "/status")["agents"] if a["id"] == aid)

    def stop(self):
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except OSError:
            pass
        self.proc.wait(timeout=5)


def turn_ended(n):
    return lambda evs: any(e.get("kind") == "turn_end" and e.get("turn") == n for e in evs)


class DockHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-test-"))
        cls.hq = cls.tmp / "home"
        cls.hq.mkdir()
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / "record").mkdir()
        (cls.hq / ".hud-token").write_text("t0ken\n")
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(cls.tmp)}]}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_dock(self):
        h = Host(self.hq)
        try:
            r = h.call("POST", "/say", {"agent": "yours", "text": "Good morning"})
            conv = r["conversation"]
            evs = h.events_until(conv, 0, turn_ended(1))
            n = len(evs)

            # the agent's line just before an ask reaches the card
            h.call("POST", "/say", {"agent": "yours", "conversation": conv, "text": "the costs"})
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            self.assertIn("I will show you the words", ask["said"])
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(2))
            n += len(evs)

            # a line the agent wrote to the record itself appears in the margin
            record.append(str(self.hq), "agent:player-agent", "person:player", "card",
                          {"title": "Water the beans by Friday"}, None, "holon", "delegated", sign=False)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "offer" for x in e), timeout=8)
            off = next(x for x in evs if x.get("kind") == "offer")["offer"]
            self.assertEqual((off["text"], off["kind"], off["source"], off["ink"]),
                             ("Water the beans by Friday", "card", "record", "said"))
            n += len(evs)

            # the character reaches the agent
            h.call("POST", "/say", {"agent": "yours", "conversation": conv, "text": "What were you given?"})
            evs = h.events_until(conv, n, turn_ended(3), timeout=90)
            said = "".join(e.get("text", "") for e in evs if e.get("kind") == "agent")
            self.assertTrue(said.startswith("One question before every move"), said)   # the Goal first (rule 0)
            self.assertIn("You are this Player+'s own agent", said)
            self.assertNotIn("Claude", host_mod.DEFAULT_CHARACTER)
        finally:
            h.stop()

        # a picked-up conversation does not repeat its history
        h = Host(self.hq)
        try:
            st = h.call("GET", "/status")
            self.assertIn(conv, [c["id"] for c in st["conversations"]])
            r = h.call("POST", "/say", {"agent": "yours", "text": "Again"})
            self.assertEqual(r["conversation"], conv)
            evs = h.events_until(conv, 0, turn_ended(r["turn"]))
            fresh = [e for e in evs if e.get("turn") == r["turn"]]
            words = [e.get("text", "") for e in fresh if e.get("kind") == "agent"]
            self.assertTrue(words, "the new turn has words")
            self.assertTrue(words[0].startswith("Good"), words[0])
            self.assertFalse(any("REPLAYED" in (e.get("text") or "") for e in evs))
            self.assertFalse(any((e.get("tool") or {}).get("title") == "An old tool" for e in evs))
        finally:
            h.stop()
        said_files = list((self.hq / ".said").glob("*.jsonl"))
        self.assertTrue(said_files)
        self.assertFalse(any("REPLAYED" in f.read_text() for f in said_files), "the replay was kept as new lines")


DEAL = [{"id": "card-harvest", "kind": "request", "section": "owed", "holon": "cell-two",
         "question": "Cell Two asked for the harvest count by Friday. Send it now?",
         "options": ["Yes, send it today", "Not this week", "Hand it on"]},
        {"id": "card-meet", "kind": "decide", "section": "decision", "holon": "cell-two",
         "question": "Which day should Cell Two meet this month?",
         "options": ["Thursday evening", "Saturday morning", "Ask the cell"]}]
PAGE = {"line": "Cell Two would like to know which day to meet.", "question": "Which day should Cell Two meet this month?",
        "options": ["Thursday evening", "Saturday morning", "Ask the cell"]}


def words_of(evs, turn):
    return "".join(e.get("text", "") for e in evs if e.get("kind") == "agent" and e.get("turn") == turn)


class FirstContactAndAsks(unittest.TestCase):
    """The panel's repairs (2026-10-25), against the stand-in through the host's own HTTP."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-first-"))
        cls.hq = cls.tmp / "home"
        (cls.hq / "record").mkdir(parents=True)
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / ".hud-token").write_text("t0ken\n")
        # who brought the person: a keeper with a name and a reach, who admitted them
        (cls.hq / "record" / "person_wren.jsonl").write_text(
            json.dumps({"id": "j1", "type": "join", "actor": "person:wren", "body": {"name": "Wren", "reach": ["mail:wren@home.invalid"]}}) + "\n" +
            json.dumps({"id": "j2", "type": "join", "actor": "person:wren", "body": {"who": "person:player"}}) + "\n")
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(cls.tmp)}]}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def say(self, h, text, conv=None, **kw):
        t0 = time.time()
        r = h.call("POST", "/say", dict({"agent": "yours", "text": text}, **({"conversation": conv} if conv else {}), **kw))
        return r, time.time() - t0

    def test_greeting(self):
        """A line that is only a greeting is greeted by the house at once, by the hour and the name it knows; the
        agent adds nothing; the house tells it the time and the name once per sitting."""
        hq = self.tmp / "home-greet"
        shutil.copytree(self.hq, hq, ignore=shutil.ignore_patterns(".agent-host*", ".said", ".kept"))
        h = Host(hq)
        try:
            hour = datetime.now().hour
            part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
            r, _ = self.say(h, "what were you told", person_name="Ash")                     # a sitting's first line
            conv = r["conversation"]
            evs = h.events_until(conv, 0, turn_ended(r["turn"]))
            told = words_of(evs, r["turn"])
            self.assertIn("At the start of this sitting it is", told)
            self.assertIn("knows your person as Ash", told)
            self.assertIn("brought here by Wren", told)
            self.assertIsNone(host_mod.real_name("Player"))                               # a placeholder is no name
            r, took = self.say(h, "Good afternoon!", conv, person_name="Ash")
            turn = r["turn"]
            self.assertLess(took, 2.0, "the greeting waited")
            self.assertEqual((r["local"]["kinds"], r["local"]["text"]), (["greet"], "Good " + part + ", Ash."))
            evs = h.events_until(conv, 0, turn_ended(turn))
            self.assertEqual(words_of(evs, turn).strip(), "", "the agent added to a greeting that asked nothing")
            r, _ = self.say(h, "what were you told", conv, person_name="Ash")
            evs = h.events_until(conv, 0, turn_ended(r["turn"]))
            self.assertNotIn("At the start of this sitting", words_of(evs, r["turn"]))     # told once per sitting
            r, _ = self.say(h, "Hello", r["conversation"])
            self.assertEqual(r["local"]["text"], "Good " + part + ".")                    # no name given, none used
            self.assertNotIn("greet", host_mod.first_contact("Hi, I am new. Who are you?"))
            self.assertEqual(host_mod.first_contact("hey there!"), ["greet"])
        finally:
            h.stop()

    def test_first_contact_page_acts_and_one_ask(self):
        h = Host(self.hq)
        try:
            # who are you: answered at once by the host, in her voice, and the agent adds one line, no ask
            r, took = self.say(h, "Hi, I am new and a little nervous. Who are you?", page=PAGE, deal=DEAL)
            conv, turn = r["conversation"], r["turn"]
            self.assertLess(took, 2.0, "the local answer waited")
            self.assertEqual(r["local"]["kinds"], ["who"])
            self.assertEqual(r["local"]["text"], "I am Polaris. This is where we talk; "
                                                 "what needs you comes here one thing at a time.")
            evs = h.events_until(conv, 0, turn_ended(turn))
            self.assertTrue(any(e.get("kind") == "local" and e.get("text") == r["local"]["text"] for e in evs))
            said = words_of(evs, turn)
            self.assertIn("glad you came", said)
            self.assertNotIn("This is where we talk", said)               # added to, never repeated
            self.assertFalse(any(e.get("kind") == "ask" for e in evs))
            n = len(evs)

            # who sent me, and a person: the keeper who admitted them, by name, with their reach
            r, _ = self.say(h, "Who sent me? Can I talk to a real person?", conv)
            self.assertEqual(r["local"]["kinds"], ["sent", "person"])
            self.assertEqual(r["local"]["text"], "Wren brought you here. You can talk with them whenever you like. "
                                                 "Write to them whenever you like.")
            self.assertEqual(r["local"]["reach"], {"label": "Write to them", "who": "Wren", "to": ["mail:wren@home.invalid"]})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            r, _ = self.say(h, "If I want to stop, how do I stop?", conv)
            self.assertEqual(r["local"]["text"], "Say stop, or tap Stop. Nothing happens without your yes.")
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            r, _ = self.say(h, "I have a story about my mother's garden. If I tell it to you, where does it go?", conv)
            self.assertEqual(r["local"]["kinds"], ["words"])
            self.assertNotIn("record", r["local"]["text"])
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            r, _ = self.say(h, "Thank you.", conv)
            self.assertNotIn("local", r)                                   # any other line is the agent's
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            # the surface's own answer from the state returns in `local` too, and is kept in the conversation
            r, _ = self.say(h, "who is working on what?", conv,
                            page=dict(PAGE, local_answers=["No worker is at work."]))
            self.assertEqual((r["local"]["kinds"], r["local"]["text"]), (["page"], "No worker is at work."))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)

            # the page's context reaches the agent, before the person's words
            r, _ = self.say(h, "What does the page show?", conv, page=PAGE)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            said = words_of(evs, r["turn"])
            self.assertTrue(said.startswith("What the page shows now:"), said)
            self.assertIn('its line: "Cell Two would like to know which day to meet."', said)
            self.assertIn("Thursday evening · Saturday morning · Ask the cell", said)
            self.assertIn("do not repeat it, do not contradict it, build on it", said)
            n += len(evs)

            # an act at her word: proposed in the form, resolved against the served Deal, answered
            r, _ = self.say(h, "mark Saturday", conv, page=PAGE, deal=DEAL)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            self.assertEqual((ask["kind"], ask["card_id"], ask["option_index"], ask["option"]),
                             ("act", "card-meet", 1, "Saturday morning"))
            self.assertEqual([o["name"] for o in ask["options"]], ["Yes", "Not that"])
            self.assertFalse(ask["leaves"])
            self.assertEqual(h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "yes"}), {"ok": True})
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "answered" and x.get("ask") == ask["id"] for x in e))
            # the yes is told to the agent once, in the next turn's note, never as a turn of its own
            time.sleep(0.5)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "answered" and x.get("ask") == ask["id"] for x in e))
            self.assertEqual(sum(1 for x in evs if x.get("kind") == "turn_end"), 1)
            self.assertTrue(words_of(evs, r["turn"]).strip().endswith("Yes?"), words_of(evs, r["turn"]))
            n += len(evs)

            # an act the Deal cannot resolve raises nothing: the words stand
            r, _ = self.say(h, "mark Saturday", conv, deal=DEAL[:1])
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertFalse(any(e.get("kind") == "ask" for e in evs))
            self.assertIn("Shall I mark: Saturday morning", words_of(evs, r["turn"]))
            n += len(evs)

            # the surface settled an answer itself: the agent is told once; its bare "Marked." is dropped
            r, _ = self.say(h, "Thursday evening", conv,
                            page=dict(PAGE, settled={"option": "Thursday evening", "card": PAGE["question"]}))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertEqual(words_of(evs, r["turn"]).strip(), "")
            n += len(evs)

            # two asks at once: only one is in front of the person; the second waits behind it
            r, _ = self.say(h, "two changes", conv)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            time.sleep(1.0)
            st = next(a for a in h.call("GET", "/status")["agents"] if a["id"] == "yours")
            self.assertEqual((st["asks_open"], st["asks_waiting"], len(st["asks"])), (1, 1, 1))
            self.assertEqual(st["asks_15m"], 2)                            # the act, and the one in front
            self.assertTrue(st["asks_15m_since"])
            first = next(x for x in evs if x.get("kind") == "ask")["ask"]
            h.call("POST", "/answer", {"conversation": conv, "ask": first["id"], "answer": "yes"})
            evs = h.events_until(conv, n, lambda e: sum(1 for x in e if x.get("kind") == "ask") >= 2)
            asks = [x["ask"] for x in evs if x.get("kind") == "ask"]
            self.assertNotEqual(asks[0]["id"], asks[1]["id"])
            answered_at = next(i for i, x in enumerate(evs) if x.get("kind") == "answered" and x.get("ask") == first["id"])
            second_at = next(i for i, x in enumerate(evs) if x.get("kind") == "ask" and x["ask"]["id"] == asks[1]["id"])
            self.assertLess(answered_at, second_at, "the second ask was shown before the first was answered")
            h.call("POST", "/answer", {"conversation": conv, "ask": asks[1]["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertIn("Both are settled.", words_of(evs, r["turn"]))
        finally:
            h.stop()


TODAY = "2026-10-25"
HOUSE_DEAL = [dict(DEAL[0], question="Cell Two asked for the harvest count by Saturday. Send it now?", due="2026-10-24",
                   why="It was asked for by Saturday, and the steward is waiting on it to plan the gathering's table.",
                   recommendation="Yes, send it today", holon_name="Cell Two"),
              dict(DEAL[1], due="2026-10-27", recommendation="Saturday morning", holon_name="Cell Two")]
HOUSE_OWED = [{"id": "card-harvest", "title": "Send the harvest count to Cell Two", "holder": "person:player",
               "due": "2026-10-24", "status": "open"},
              {"id": "o-notes", "title": "Write up the cell's harvest notes", "holder": "person:player",
               "due": "2026-10-28", "status": "open", "holon_name": "Cell Two"},
              {"id": "o-tables", "title": "Carry the long tables from the Commons", "holder": "person:weaver",
               "holder_name": "Weaver", "due": "2026-10-24", "status": "open"}]


class RoundTwo(unittest.TestCase):
    """No file on her screen, the agent knows the page's cards,
    no late "Marked.", one name, the service named."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-two-"))
        cls.hq = cls.tmp / "home"
        (cls.hq / "record").mkdir(parents=True)
        (cls.tmp / "memory").mkdir()
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / ".hud-token").write_text("t0ken\n")
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(cls.tmp)}]}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_round_two(self):
        h = Host(self.hq)
        house = {"deal": HOUSE_DEAL, "owed": HOUSE_OWED, "today": TODAY, "person": "person:player"}
        try:
            # 4. one name: in /say's answer and in every state the stream carries
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Can we go slowly?"}, **house))
            conv, n = r["conversation"], 0
            self.assertEqual(r["name"], "Polaris")
            # 1. a note kept in memory/ is one plain ask: no file's name, no YAML, Keep it · No
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            self.assertEqual(ask["kind"], "keep")
            self.assertEqual(ask["question"], "May I remember that we go slowly?")
            self.assertEqual(ask["title"], ask["question"])
            self.assertEqual([o["name"] for o in ask["options"]], ["Keep it", "No"])
            face = json.dumps({k: v for k, v in ask.items() if k != "raw"})
            for leak in (".md", "MEMORY", "go-slowly", "---", "description:", "name:"):
                self.assertNotIn(leak, face, "a file reached her screen: " + leak)
            self.assertIn("go-slowly.md", json.dumps(ask["raw"]))            # the raw step, never on the face
            self.assertEqual(ask["step"], "Keep a note that we go slowly. Nothing leaves this computer.")
            self.assertTrue(all(e.get("name") == "Polaris" for e in evs if e.get("kind") == "state"))
            self.assertEqual(h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "yes"}), {"ok": True})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertIn("I will keep to it.", words_of(evs, r["turn"]))     # the index answered by her same yes
            self.assertEqual(sum(1 for e in evs if e.get("kind") == "ask"), 1, "asked twice for one note")
            self.assertFalse(any(e.get("kind") in ("tool", "tool_update") for e in evs), "a kept note was drawn as a changed file")
            self.assertTrue(any(e.get("kind") == "quiet_tool" and e["tool"].get("quiet") for e in evs))
            n += len(evs)
            # and her No keeps nothing, the index answered no without a second ask
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Please, go slowly with me.", "conversation": conv}, **house))
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertIn("Then slowly it is.", words_of(evs, r["turn"]))
            self.assertEqual(sum(1 for e in evs if e.get("kind") == "ask"), 1)
            n += len(evs)
            # after her No, a note in the next turn is denied quietly, never asked
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Really, go slowly.", "conversation": conv}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertFalse(any(e.get("kind") == "ask" for e in evs), "a note asked again after her No")
            n += len(evs)
            # an open keep never blocks the turn: her new line sets it aside, both turns end, and it
            # is not asked again in the sitting
            hq2 = self.hq.parent / "home-keep"
            shutil.copytree(self.hq, hq2, ignore=shutil.ignore_patterns(".agent-host*", ".said", ".kept", "memory"))
            h2 = Host(hq2)
            try:
                r = h2.call("POST", "/say", dict({"agent": "yours", "text": "Can we go slowly?"}, **house))
                c2 = r["conversation"]
                h2.events_until(c2, 0, lambda e: any(x.get("kind") == "ask" for x in e))
                r2 = h2.call("POST", "/say", dict({"agent": "yours", "text": "Anything late?", "conversation": c2}, **house))
                ends = lambda e: [x for x in e if x.get("kind") == "turn_end"]
                evs = h2.events_until(c2, 0, lambda e: len(ends(e)) >= 2, timeout=15)
                self.assertIn("a day past", "".join(x.get("text", "") for x in evs if x.get("kind") == "agent"))
                self.assertEqual(sum(1 for e in evs if e.get("kind") == "ask"), 1)
                r3 = h2.call("POST", "/say", dict({"agent": "yours", "text": "Can we go slowly?", "conversation": c2}, **house))
                evs = h2.events_until(c2, 0, lambda e: len(ends(e)) >= 3, timeout=15)
                self.assertEqual(sum(1 for e in evs if e.get("kind") == "ask"), 1, "a set-aside note asked again")
            finally:
                h2.stop()

            # 1. a command in the Talk is the harness's ask (no permission layer of the Talk's
            # own): it is put to her in words, the exact command as the step; her no is the harness's no;
            # 2. the answer comes from the note
            t0 = time.time()
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "What's blocked, and what do I need to do right now?",
                                             "conversation": conv}, **house))
            asks_of = lambda evs: [x["ask"] for x in evs if x.get("kind") == "ask"]
            evs = h.events_until(conv, n, lambda e: any(x["kind"] == "execute" for x in asks_of(e)), timeout=15)
            cmd = [x for x in asks_of(evs) if x["kind"] == "execute"][-1]
            self.assertEqual(cmd["step"], "find bg -name status.md")
            self.assertTrue(cmd["question"].startswith("May I "))
            h.call("POST", "/answer", {"conversation": conv, "ask": cmd["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertLess(time.time() - t0, 10)
            self.assertIn("First: Cell Two asked for the harvest count by Saturday. Send it now? (by Saturday, a day past)",
                          words_of(evs, r["turn"]))
            n += len(evs)
            # the next note tells it once why, and carries the Deal, what is owed, others' holdings, today
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "What were you told?", "conversation": conv}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            told = words_of(evs, r["turn"])
            for want in ("Today is Sunday 25 October.", "call them by none, never one taken from this computer", "The Deal's open cards",
                         "(the first: the one the page shows now)", "the steward is waiting on it",
                         "by Saturday, a day past", "Write up the cell's harvest notes (Cell Two), by Wednesday, in three days.",
                         "Carry the long tables from the Commons, held by Weaver", "Never say nothing waits"):
                self.assertIn(want, told)
            self.assertNotIn("Send the harvest count to Cell Two", told)      # dealt already: said once, as its card
            n += len(evs)
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "What were you told?", "conversation": conv}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertNotIn(host_mod.NO_COMMAND, words_of(evs, r["turn"]))   # told once
            n += len(evs)
            # "is anything late?" from the note, with no tool
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Is anything late?", "conversation": conv}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertIn("a day past", words_of(evs, r["turn"]))
            self.assertFalse(any(e.get("kind") in ("tool", "ask") for e in evs))
            n += len(evs)

            # 2. what she settled in this sitting rides in every note; 3. a settlement is told once
            page = dict(PAGE, settled={"option": "Take it now", "card": "Sort the seed packets now?"},
                        recent=[{"option": "Yes, send it today", "card": HOUSE_DEAL[0]["question"]}])
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "What were you told?", "conversation": conv, "page": page}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            told = words_of(evs, r["turn"])
            self.assertIn('- "Take it now" for "Sort the seed packets now?"', told)
            self.assertIn('- "Yes, send it today"', told)
            n += len(evs)
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "What does the page show?", "conversation": conv, "page": page}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertNotIn("it has just marked", words_of(evs, r["turn"]))  # the same settlement, not told again
            n += len(evs)
            # 3. a stray "Marked." at the head of another answer is cut
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "stray", "conversation": conv}, **house))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertEqual(words_of(evs, r["turn"]), "Your words stay with you here.")
            n += len(evs)

            # 5. the service named when the vendors file names it, else the plain sentence
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Where do my words go?", "conversation": conv,
                                             "vendor": "Anthropic"}, **house))
            self.assertIn("To answer you, I send them to Anthropic to think.", r["local"]["text"])
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            r = h.call("POST", "/say", dict({"agent": "yours", "text": "Where do my words go?", "conversation": conv,
                                             "vendor": None}, **house))
            self.assertIn("I send them to the service I think with.", r["local"]["text"])
            h.events_until(conv, n, turn_ended(r["turn"]))
        finally:
            h.stop()

    def test_forms(self):
        self.assertEqual(host_mod.by_when("2026-10-24", TODAY), "by Saturday, a day past")
        self.assertEqual(host_mod.by_when("2026-10-25", TODAY), "by today")
        self.assertEqual(host_mod.by_when("2026-10-26", TODAY), "by tomorrow, Monday")
        self.assertEqual(host_mod.by_when("2026-10-31", TODAY), "by Saturday, in six days")
        self.assertEqual(host_mod.by_when("2026-10-20", TODAY), "by Tuesday, five days past")
        self.assertEqual(host_mod.by_when(None, TODAY), "")
        mem = lambda p, kind="edit": host_mod.memory_write({"kind": kind, "input": json.dumps({"file_path": p})}, "/h/home")
        self.assertTrue(mem("memory/go-slowly.md"))
        self.assertTrue(mem("/h/home/memory/MEMORY.md"))
        self.assertFalse(mem("notes/go-slowly.md"))
        self.assertFalse(mem("/h/home/memory-not/x.md"))
        self.assertFalse(mem("memory/x.md", "execute"))
        said = "Gladly. I would like to remember that you call this card The Gathering Day."
        self.assertEqual(host_mod.keep_that({"input": "{}"}, said), "you call this card The Gathering Day")
        yaml = json.dumps({"file_path": "memory/x.md", "content": "---\nname: x\ndescription: My person calls the card...\n---\n"})
        self.assertIsNone(host_mod.keep_that({"input": yaml}, "Gladly."))          # not said to her: the plain ask
        self.assertTrue(host_mod.bare_mark(" Marked. ") and not host_mod.bare_mark("Marked yes."))
        note = host_mod.house_note([], [], "person:player", TODAY)
        self.assertIn("The Deal holds no open card.", note)
        self.assertEqual(host_mod.house_note(None, [], "person:player", None), "")


class AskClock(unittest.TestCase):
    """An ask older than the wait goes into the Deal, even one still waiting behind another."""
    def test_lapse_in_order(self):
        tmp = Path(tempfile.mkdtemp(prefix="dock-clock-"))
        try:
            hq = tmp / "home"
            (hq / "record").mkdir(parents=True)
            (hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
            (hq / ".hud-token").write_text("t0ken\n")
            (hq / "agents.json").write_text(json.dumps({"agents": [
                {"id": "yours", "of": "person:player", "kind": "harness", "actor": "agent:player-agent", "ask_wait_min": 0.05,
                 "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(tmp)}]}))
            h = Host(hq)
            try:
                r = h.call("POST", "/say", {"agent": "yours", "text": "two changes"})
                evs = h.events_until(r["conversation"], 0, turn_ended(r["turn"]), timeout=30)
                self.assertIn("Both are settled.", words_of(evs, r["turn"]))
                shown = [e for e in evs if e.get("kind") == "ask"]
                self.assertTrue(shown, "no ask was shown")
                titles = []
                for f in (hq / "record").glob("*.jsonl"):
                    titles += [json.loads(x)["body"].get("title", "") for x in f.read_text().splitlines()
                               if json.loads(x).get("type") == "request"]
                self.assertEqual(len(titles), 2, titles)
            finally:
                h.stop()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class KeepFrees(unittest.TestCase):
    """A keep ask left unanswered frees the turn within about
    twenty seconds; her words land, and the ask stays open in the Talk for her later yes."""
    def test_keep_frees_turn(self):
        tmp = Path(tempfile.mkdtemp(prefix="dock-keepfree-"))
        try:
            hq = tmp / "home"
            (hq / "record").mkdir(parents=True)
            (tmp / "memory").mkdir()
            (hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
            (hq / ".hud-token").write_text("t0ken\n")
            (hq / "agents.json").write_text(json.dumps({"agents": [
                {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
                 "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(tmp)}]}))
            h = Host(hq)
            house = {"deal": HOUSE_DEAL, "owed": HOUSE_OWED, "today": TODAY, "person": "person:player"}
            try:
                t0 = time.time()
                r = h.call("POST", "/say", dict({"agent": "yours", "text": "I am slow with these things. Can we go slowly?"}, **house))
                conv = r["conversation"]
                evs = h.events_until(conv, 0, turn_ended(r["turn"]), timeout=25)
                self.assertLess(time.time() - t0, 21, "the keep ask held the turn")
                self.assertIn("We go at your pace.", words_of(evs, r["turn"]))
                asks = [e["ask"] for e in evs if e.get("kind") == "ask"]
                self.assertEqual([a["kind"] for a in asks], ["keep"], "asked twice, or not at all")
                self.assertFalse(any(e.get("kind") == "answered" for e in evs), "the ask was closed, not left open")
                self.assertFalse((tmp / "memory" / "go-slowly.md").exists())
                # her later yes is still an answer
                self.assertEqual(h.call("POST", "/answer", {"conversation": conv, "ask": asks[0]["id"], "answer": "yes"}),
                                 {"ok": True})
            finally:
                h.stop()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_handback_state(self):
        self.assertEqual(host_mod.handoff_state("# Harvest notes\nStatus: blocked on the count.\n"), "blocked on the count")
        self.assertEqual(host_mod.handoff_state("The harvest notes are drafted.\nStatus: done\n"), "")
        self.assertEqual(host_mod.handoff_state("The harvest notes are drafted.\n"), "")


class QuietRead(unittest.TestCase):
    """A read the house already allows asks the person nothing."""
    def test_quiet(self):
        tmp = Path(tempfile.mkdtemp(prefix="dock-quiet-"))
        try:
            (tmp / ".claude").mkdir()
            (tmp / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": [
                "Bash(ls:*)", "Bash(cat:*)", "Bash(bash scripts/pad-write.sh:*)", "Bash(python3 -I engine/record.py read:*)"]}}))
            q = lambda kind, raw, leaves=False: host_mod.quiet_read({"kind": kind, "input": json.dumps(raw)}, leaves, str(tmp))
            self.assertTrue(q("read", {"file_path": str(tmp / "state.json")}))
            self.assertTrue(q("read", {"file_path": "bg/vega/status.md"}))
            self.assertTrue(q("search", {"pattern": "harvest"}))
            self.assertFalse(q("read", {"file_path": "/etc/hosts"}))                    # outside the house
            self.assertFalse(q("read", {"file_path": "../elsewhere/x.md"}))
            self.assertTrue(q("execute", {"command": "ls bg"}))
            self.assertTrue(q("execute", {"command": "python3 -I engine/record.py read ."}))
            self.assertFalse(q("execute", {"command": "find bg -mtime -2"}))           # not in the allowlist
            self.assertFalse(q("execute", {"command": "cat a > b"}))                   # a redirect
            self.assertFalse(q("execute", {"command": "ls; rm -rf bg"}))               # a join
            self.assertFalse(q("execute", {"command": "bash scripts/pad-write.sh x"})) # allowed, but it writes
            self.assertFalse(q("read", {"file_path": str(tmp / "a")}, leaves=True))    # never what leaves
            self.assertFalse(q("edit", {"file_path": str(tmp / "a")}))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_forms(self):
        self.assertEqual(host_mod.first_contact("Hello. My granddaughter told me to come here. What is this for?"), ["who"])
        self.assertEqual(host_mod.first_contact("Who sent you to me? I do not know what Cell Two is."), ["sent"])
        self.assertEqual(host_mod.first_contact("Which day should we meet?"), [])
        self.assertEqual(host_mod.act_proposal("Five said yes.\nShall I mark: Yes, send it today, for the harvest count? Yes?"),
                         ("Yes, send it today", "the harvest count"))
        self.assertIsNone(host_mod.act_proposal("Shall I mark Saturday?"))
        self.assertEqual(host_mod.resolve_card("Saturday morning", "the meeting day", DEAL)[0]["id"], "card-meet")
        two = DEAL + [dict(DEAL[1], id="card-walk", question="Which day for the long walk?")]
        self.assertEqual(host_mod.resolve_card("Saturday morning", "the long walk", two)[0]["id"], "card-walk")
        self.assertIsNone(host_mod.resolve_card("Saturday morning", "it", two))      # two fit alike: no ask
        self.assertIsNone(host_mod.resolve_card("Sunday", "the meeting day", DEAL))


class Terminal(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not on this computer")
    def test_stripper(self):
        r = subprocess.run(["node", str(HERE / "test_dock_terminal.mjs"), str(HUD / "dock.js")],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class AskCard(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not on this computer")
    def test_the_face_in_words(self):
        r = subprocess.run(["node", str(HERE / "test_dock_card.mjs"), str(HUD / "dock-card.js"), str(HUD / "strings.json")],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("dock card: all pass", r.stdout)


class Letter(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not on this computer")
    def test_only_the_agents_words(self):
        r = subprocess.run(["node", str(HERE / "test_dock_letter.mjs"), str(HUD / "dock.js")],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class LayeredVoice(unittest.TestCase):
    """The layered voice and voice mode, in headless muted Chrome on a phone's viewport, with the
    listener and the voice as stand-ins (test_dock_voice.mjs): nothing is ever played aloud."""
    @unittest.skipUnless(shutil.which("node") and os.path.exists(CHROME), "node or Chrome is not on this computer")
    def test_hold_listen_read_and_the_loop(self):
        r = subprocess.run(["node", str(HERE / "test_dock_voice.mjs")], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1500:])
        self.assertIn("dock voice: all pass", r.stdout)


class ByYourWords(unittest.TestCase):
    """A card the person asked for in their own words is answered by those words; nothing else is."""
    def conv(self, said):
        c = type("C", (), {})()
        c.events = [{"kind": "user", "text": said}]
        return c

    def tool(self, title, typ="card"):
        cmd = ("python3 -I engine/record.py append /h --actor agent:a --type " + typ +
               " --reason delegated --body '" + json.dumps({"title": title}) + "'")
        return {"kind": "execute", "input": json.dumps({"command": cmd})}

    def test_words(self):
        f = host_mod.asked_in_words
        said = self.conv("Please put this in my record: Water the beans by Friday.")
        self.assertEqual(f(self.tool("Water the beans by Friday"), said, False), "Water the beans by Friday")
        self.assertIsNone(f(self.tool("Sell the house"), said, False))              # not what was asked
        self.assertIsNone(f(self.tool("Water the beans by Friday", "commit"), said, False))  # only a card
        self.assertIsNone(f(self.tool("Water the beans by Friday"), said, True))      # never what leaves


class Character(unittest.TestCase):
    def test_default_and_empty(self):
        a = host_mod.Agent.__new__(host_mod.Agent)
        a.row = {}
        self.assertEqual(a.session_params("/x")["_meta"]["systemPrompt"]["append"], host_mod.DEFAULT_CHARACTER)
        a.row = {"character": ""}
        self.assertNotIn("_meta", a.session_params("/x"))
        a.row = {"character": "Be brief."}
        self.assertEqual(a.session_params("/x")["_meta"]["systemPrompt"]["append"], "Be brief.")

    def test_the_chief_of_staff(self):
        # the Talk's agent is the chief of staff: the skill named by its path, the four rules carried
        ch = host_mod.DEFAULT_CHARACTER
        self.assertIn(host_mod.CHIEF_OF_STAFF_SKILL, ch)
        self.assertTrue((Path(host_mod.__file__).resolve().parent.parent / host_mod.CHIEF_OF_STAFF_SKILL).is_file())
        for rule in ("Speak from the record", "One question at a time", "No figures unasked", "The cost before a worker"):
            self.assertIn(rule, ch)
        # a worker keeps the voice, not the office, and its brief says how it hands back and whom it asks
        self.assertNotIn("chief of staff", host_mod.WORKER_CHARACTER)
        for line in ("report in one handoff line", "ask the chief of staff, never the person",
                     "Never speak to the person unasked"):
            self.assertIn(line, host_mod.BODY_BRIEF)


class RoundThree(unittest.TestCase):
    """The agent knows its page, asks in words, and tells what it starts: items 1 to 8 on the host's side."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-three-"))
        cls.hq = cls.tmp / "home"
        (cls.hq / "record").mkdir(parents=True)
        (cls.tmp / "notes").mkdir()
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / ".hud-token").write_text("t0ken\n")
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(cls.tmp)}]}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_round_three(self):
        h = Host(self.hq)
        house = {"deal": HOUSE_DEAL, "owed": HOUSE_OWED, "today": TODAY, "person": "person:player", "person_name": "Ash"}
        n = 0
        def say(text, conv=None, **kw):
            r = h.call("POST", "/say", dict({"agent": "yours", "text": text, **({"conversation": conv} if conv else {})}, **house, **kw))
            return r
        try:
            # 1. the agent knows its own voice and its house
            r = say("Can I talk to you out loud?")
            conv = r["conversation"]
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertEqual(words_of(evs, r["turn"]), "Yes. Hold the microphone beside Send and speak; let go to send. "
                                                       "Turn on Voice mode at the top to go hands-free.")
            n += len(evs)
            r = say("What is Chain for?", conv)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertIn("what the whole is waiting on, and whether it is them", words_of(evs, r["turn"]))
            n += len(evs)
            # 8. one name: the house's, and the machine's never
            r = say("What were you told?", conv)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            told = words_of(evs, r["turn"])
            self.assertIn("Their name, as the house knows it: Ash. Use this name and no other", told)
            for want in ("Voice mode at the top", "the Ledger, the time and care", "Spaces, where they work"):
                self.assertIn(want, told)
            n += len(evs)

            # 2. a change to a page in the house: asked in words; the step a sentence; the raw step in `raw`
            r = say("Change the page, please.", conv)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            self.assertEqual(ask["question"], "May I add a page to your house, \u201cMap of the commons\u201d?")
            self.assertEqual(ask["title"], ask["question"])
            self.assertEqual(ask["step"], "It changes one page in your house. Nothing leaves this computer.")
            face = json.dumps({k: v for k, v in ask.items() if k != "raw"})
            for leak in ("t-one", ".md", "notes/", "file_path", "# Map"):
                self.assertNotIn(leak, face, "a file reached her screen: " + leak)
            self.assertIn("t-one.md", json.dumps(ask["raw"]))
            self.assertEqual(ask["preview"], "The commons, drawn from the record.")
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            # and one outside the house is said as outside, with no path
            q, step, _ = host_mod.plain_change({"kind": "edit", "input": json.dumps({"file_path": "/Users/player/notes/t-one.md"})},
                                               str(self.tmp), lambda k, **kw: host_mod.FIRST_WORDS[k].format(**kw))
            self.assertEqual(q, "May I change something on this computer, outside your house?")
            # a worker's change to an untitled page: asked by its task
            q, _, _ = host_mod.plain_change({"kind": "edit", "input": json.dumps({"file_path": "bg/vega/t-one.md", "content": "x"})},
                                            str(self.tmp), lambda k, **kw: host_mod.FIRST_WORDS[k].format(**kw), "draw the map of the commons")
            self.assertEqual(q, "May I keep my work for \u201cdraw the map of the commons\u201d in your house?")

            # 3. one Start card per proposal; after Start, told by name and says so in one line
            r = say("Have a worker draw the map of the commons.", conv)
            evs = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            wask = next(x for x in evs if x.get("kind") == "ask")["ask"]
            self.assertEqual((wask["kind"], wask["task"]), ("worker", "draw the map of the commons"))
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            n += len(evs)
            r = say("Have a worker draw the map of the commons.", conv)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            time.sleep(0.5)
            self.assertFalse(any(e.get("kind") == "ask" for e in evs), "a second Start card for the same task")
            n += len(evs)
            b = h.call("POST", "/body", {"task": wask["task"]})
            self.assertEqual(b["name"], "Vega")
            h.call("POST", "/answer", {"conversation": conv, "ask": wask["id"], "answer": "yes"})
            evs = h.events_until(conv, n, lambda e: "Vega has started on it." in "".join(x.get("text", "") for x in e if x.get("kind") == "agent"))
            n += len(evs)
            time.sleep(0.5)

            # 4. what it decides at her word: `decided` for a suggested choice only; the rest is told
            r = say("Rank what is waiting and decide what you can.", conv)
            evs = h.events_until(conv, n, lambda e: turn_ended(r["turn"])(e) and any(x.get("kind") == "decided" for x in e))
            dec = [e for e in evs if e.get("kind") == "decided"]
            self.assertEqual([(d["card_id"], d["option"], d["option_index"]) for d in dec], [("card-meet", "Saturday morning", 1)])
            n += len(evs)
            r = say("What were you told?", conv)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            told = words_of(evs, r["turn"])
            self.assertIn("You wrote 'Decided: Ask the moon'", told)
            self.assertIn('- "Saturday morning" for "Which day should Cell Two meet this month?"', told)
            n += len(evs)
            # a line that does not delegate decides nothing
            self.assertIsNone(host_mod.DELEGATE.search("What is waiting?"))
            self.assertTrue(host_mod.DELEGATE.search("Can you just decide some of these for me?"))

            # 5. her words that match an option: no Mark card; the page note says the page settles them
            page = {"line": "Cell Two asked for the harvest count.", "question": HOUSE_DEAL[0]["question"],
                    "options": HOUSE_DEAL[0]["options"], "recommendation": "Yes, send it today",
                    "settled": {"option": "Yes, send it today", "card": HOUSE_DEAL[0]["question"]}}
            r = say("Yes, send it today.", conv, page=page)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            time.sleep(0.5)
            self.assertFalse(any(e.get("kind") == "ask" for e in evs), "a second card for words the page settled")
            n += len(evs)
            self.assertIn("never propose a mark for those", host_mod.page_note(dict(page, settled=None)))
            self.assertEqual(host_mod.page_settled_by("yes", dict(page, settled=None)), {"yes send it today"})
            self.assertEqual(host_mod.page_settled_by("the weekend one", dict(page, settled=None)), set())

            # 6. two streamed messages never glued; words inside one message untouched
            r = say("glued", conv)
            evs = h.events_until(conv, n, turn_ended(r["turn"]))
            self.assertEqual(words_of(evs, r["turn"]), "It works.\n\nWhich day shall it be? Fine. Whenever you are ready. "
                                                       "U.S.A stays as it is, and so does e.g.")
            n += len(evs)
            # the one first, by the shared order
            self.assertIn('the first thing, by the order you and the page share, is "Bring the folding chairs"',
                          host_mod.page_note({"first": "Bring the folding chairs"}))
        finally:
            h.stop()

    def test_worker_reads(self):
        """Review 37: a worker's read of its brief (outside the house), of a house file and a search are answered
        yes by the house and never shown; its write outside its folder is the one plain ask, from the chief."""
        m = host_mod
        hq, cwd = str(self.hq), str(self.tmp)
        rd = lambda p: {"kind": "read", "input": json.dumps({"file_path": p})}
        brief = self.tmp.parent / (self.tmp.name + "-brief.md")
        brief.write_text("# How a background body works\n")
        try:
            self.assertEqual(m.worker_step(rd(str(brief)), False, cwd, "vega", hq), "ask")
            self.assertEqual(m.worker_step(rd(str(brief)), False, cwd, "vega", hq, [str(brief)]), "yes")
            self.assertEqual(m.worker_step(rd(str(self.hq / "holon.json")), False, cwd, "vega", hq), "yes")
            self.assertEqual(m.worker_step(rd("/etc/hosts"), False, cwd, "vega", hq), "ask")
            h = Host(self.hq)
            try:
                b = h.call("POST", "/body", {"task": "read the brief and note the bread", "brief_page": str(brief)})
                name, wconv = b["name"], b["conversation"]
                evs = h.events_until(wconv, 0, lambda e: any(x.get("kind") == "ask" for x in e), timeout=30)
                asks = [x["ask"] for x in evs if x.get("kind") == "ask"]
                self.assertEqual(len(asks), 1)
                self.assertEqual(asks[0]["kind"], "edit")
                self.assertTrue(asks[0]["question"].startswith(name + " would like to "), asks[0]["question"])
                h.call("POST", "/answer", {"conversation": wconv, "ask": asks[0]["id"], "answer": "not_this"})
                evs = h.events_until(wconv, 0, turn_ended(1), timeout=20)
                self.assertIn("brief=yes read=yes grep=yes write=no", words_of(evs, 1))
                self.assertEqual(len([x for x in evs if x.get("kind") == "ask"]), 1)
            finally:
                h.stop()
        finally:
            brief.unlink()
            for f in self.tmp.glob("bg"):
                shutil.rmtree(f, ignore_errors=True)

    def test_worker_yes_by_name(self):
        """"yes, Vega may look", said to the chief, answers the worker's open ask."""
        brief = self.tmp.parent / (self.tmp.name + "-brief-yes.md")
        brief.write_text("# How a background body works\n")
        try:
            h = Host(self.hq)
            try:
                b = h.call("POST", "/body", {"agent": "yours", "task": "read the brief and note the bread", "brief_page": str(brief)})
                name, wconv = b["name"], b["conversation"]
                evs = h.events_until(wconv, 0, lambda e: any(x.get("kind") == "ask" for x in e), timeout=30)
                ask = [x["ask"] for x in evs if x.get("kind") == "ask"][0]
                a = h.call("POST", "/say", {"agent": "yours", "text": "yes, " + name + " may look"})
                self.assertIn("answered", a, a)
                self.assertEqual((a["answered"]["ask"], a["answered"]["answer"], a["answered"]["worker"]), (ask["id"], "yes", name))
                h.events_until(wconv, 0, lambda e: any(x.get("kind") == "answered" and x.get("ask") == ask["id"] for x in e), timeout=20)
            finally:
                h.stop()
        finally:
            brief.unlink()
            for f in self.tmp.glob("bg"):
                shutil.rmtree(f, ignore_errors=True)

    def test_worker_yes_in_a_longer_line(self):
        """Reviews 41 and 43: "Yes. And answer your workers' small asks yourself from now on." answers the one open
        worker ask with the harness's allowing option at once (the row leaves "waiting on you"), and the rest of the
        line still goes to the chief; "..., and start it" starts the worker with no "Start it?" card."""
        m = host_mod
        self.assertTrue(m.said_start("Now have someone check whether the hall is free Sunday morning, and start it."))
        self.assertFalse(m.said_start("Have someone check the hall, but do not start it."))
        self.assertEqual(m.worker_proposal("The task, in your words: check the hall, and start it. About 5 minutes. Starting it."),
                         "check the hall")
        brief = self.tmp.parent / (self.tmp.name + "-brief-long.md")
        brief.write_text("# How a background body works\n")
        try:
            h = Host(self.hq)
            try:
                b = h.call("POST", "/body", {"agent": "yours", "task": "read the brief and note the bread", "brief_page": str(brief)})
                name, wconv = b["name"], b["conversation"]
                evs = h.events_until(wconv, 0, lambda e: any(x.get("kind") == "ask" for x in e), timeout=30)
                ask = [x["ask"] for x in evs if x.get("kind") == "ask"][0]
                a = h.call("POST", "/say", {"agent": "yours", "text": "Yes. And answer your workers' small asks yourself from now on."})
                self.assertIn("answered", a, a)
                self.assertEqual((a["answered"]["ask"], a["answered"]["answer"], a["answered"]["worker"]), (ask["id"], "yes", name))
                self.assertIn("turn", a, "the rest of the line did not go on to the chief")
                w = next(x for x in h.call("GET", "/status")["agents"] if (x.get("body") or {}).get("name") == name)
                self.assertNotEqual(w["worker"]["state"], "waiting")
                self.assertEqual(w["worker"]["answered"], "yes")
                evs = h.events_until(wconv, 0, turn_ended(1), timeout=20)
                self.assertIn("write=yes", words_of(evs, 1))
                # "..., and start it": no Start card; the worker starts, and she says so in one line
                r = h.call("POST", "/say", {"agent": "yours", "text": "Have a worker count the stars, and start it."})
                after = lambda e: e[next((i for i, x in enumerate(e) if x.get("kind") == "worker_started"), len(e)):]
                evs = h.events_until(r["conversation"], 0, lambda e: "has started on it." in "".join(
                    x.get("text", "") for x in after(e) if x.get("kind") == "agent"), timeout=30)
                self.assertFalse(any(x.get("kind") == "ask" and x["ask"].get("kind") == "worker"
                                     and x["ask"].get("task") == "count the stars" for x in evs), "Start it? was asked")
                st = h.call("GET", "/status")["agents"]
                self.assertTrue(any((x.get("body") or {}).get("task") == "count the stars" for x in st), "the worker did not start")
            finally:
                h.stop()
        finally:
            brief.unlink()
            for f in self.tmp.glob("bg"):
                shutil.rmtree(f, ignore_errors=True)

    def test_workers(self):
        # 9. the chief of staff answers for its workers; 10. the end is one line; 11. every event tagged
        h = Host(self.hq)
        try:
            r = h.call("POST", "/say", {"agent": "yours", "text": "Good morning", "deal": HOUSE_DEAL, "today": TODAY})
            chief = r["conversation"]
            h.events_until(chief, 0, turn_ended(r["turn"]))
            b = h.call("POST", "/body", {"task": "draft the notes for the harvest"})
            name, wconv = b["name"], b["conversation"]
            evs = h.events_until(wconv, 0, lambda e: any(x.get("kind") == "ask" for x in e), timeout=30)
            asks = [x["ask"] for x in evs if x.get("kind") == "ask"]
            self.assertEqual(len(asks), 1)
            ask = asks[0]
            self.assertEqual(ask["question"], name + " would like to add a page to your house, \u201cThe harvest notes\u201d. Let it?")
            self.assertEqual(ask["from_worker"], name)
            self.assertNotIn("allow_always", [o["kind"] for o in ask["options"]])
            self.assertNotIn("harvest.md", json.dumps({k: v for k, v in ask.items() if k != "raw"}))
            h.call("POST", "/answer", {"conversation": wconv, "ask": ask["id"], "answer": "yes"})
            evs = h.events_until(wconv, 0, lambda e: any(x.get("kind") == "turn_end" for x in e), timeout=30)
            self.assertEqual(sum(1 for x in evs if x.get("kind") == "ask"), 1, "a worker asked the person twice")
            said = words_of(evs, 1)
            for want in ("read=yes", "grep=yes", "status.md=yes", "handoff.md=yes", "DONE=yes", "out1=yes", "out2=no", "send=no"):
                self.assertIn(want, said)
            self.assertTrue(all(e.get("worker") == name for e in evs if e.get("kind") in ("agent", "ask")))
            # its end: a `done` event in the chief's conversation, and her one line
            evs = h.events_until(chief, 0, lambda e: "season" in "".join(
                x.get("text", "") for x in e if x.get("kind") == "agent"), timeout=30)
            done = next(e for e in evs if e.get("kind") == "done")
            self.assertEqual((done["worker"], done["line"], done["review_min"], done["go"]),
                             (name, "Drafted the harvest notes.", 4, {"handoff": name}))
            self.assertIn("The harvest notes are drafted. One thing would finish them: was it a crop from the ground",
                          "".join(x.get("text", "") for x in evs if x.get("kind") == "agent"))
            after = evs[evs.index(done):]
            self.assertTrue(all(e.get("agent") == "yours" and "worker" not in e for e in after if e.get("kind") == "agent"))
        finally:
            h.stop()
        self.assertEqual(host_mod.worker_step({"kind": "edit", "input": json.dumps({"file_path": "bg/vega/../x.md"})},
                                              False, str(self.tmp), "vega", str(self.hq)), "ask")
        self.assertEqual(host_mod.worker_step({"kind": "execute", "input": json.dumps({"command": "grep -r x /etc"})},
                                              False, str(self.tmp), "vega", str(self.hq)), "ask")
        self.assertEqual(host_mod.worker_step({"kind": "fetch"}, True, str(self.tmp), "vega", str(self.hq)), "out")

    def test_answer_in_words(self):
        # a conversational interface: every open ask answered by her next line in words
        tmp = Path(tempfile.mkdtemp(prefix="dock-words-"))
        try:
            hq = tmp / "home"
            (hq / "record").mkdir(parents=True)
            (hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
            (hq / ".hud-token").write_text("t0ken\n")
            (hq / "agents.json").write_text(json.dumps({"agents": [
                {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
                 "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(tmp)}]}))
            h = Host(hq)
            try:
                house = {"deal": HOUSE_DEAL, "today": TODAY}
                say = lambda text, conv=None: h.call("POST", "/say", dict({"agent": "yours", "text": text,
                                                                         **({"conversation": conv} if conv else {})}, **house))
                asks_of = lambda evs: [x["ask"] for x in evs if x.get("kind") == "ask"]
                # a note to keep: "Keep it"
                r = say("Can we go slowly?")
                conv, n = r["conversation"], 0
                evs = h.events_until(conv, n, lambda e: asks_of(e))
                k = asks_of(evs)[0]
                a = say("Keep it", conv)
                self.assertEqual({x: a["answered"][x] for x in ("ask", "answer", "kind")}, {"ask": k["id"], "answer": "yes", "kind": "keep"})
                self.assertEqual(a["answered"]["option"], "Keep it")
                evs = h.events_until(conv, n, turn_ended(r["turn"]))
                self.assertIn("I will keep to it.", words_of(evs, r["turn"]))
                self.assertTrue(any(e.get("kind") == "user" and e.get("answers") == k["id"] for e in evs))
                n += len(evs)
                # a line that answers nothing leaves the ask open and goes to the agent
                r = say("two changes", conv)
                evs = h.events_until(conv, n, lambda e: asks_of(e))
                first = asks_of(evs)[0]
                u = say("Tell me more about what you would change first, please.", conv)
                self.assertNotIn("answered", u)
                self.assertEqual(next(x for x in h.call("GET", "/status")["agents"] if x["id"] == "yours")["asks_open"], 1)
                a = say("No.", conv)
                self.assertEqual((a["answered"]["ask"], a["answered"]["answer"]), (first["id"], "not_this"))
                evs = h.events_until(conv, n, lambda e: len(asks_of(e)) >= 2)
                second = asks_of(evs)[1]
                a = say("yes please", conv)
                self.assertEqual((a["answered"]["ask"], a["answered"]["answer"]), (second["id"], "yes"))
                evs = h.events_until(conv, n, lambda e: "Both are settled." in "".join(x.get("text", "") for x in e if x.get("kind") == "agent"), timeout=30)
                n += len(evs)
                h.events_until(conv, n, turn_ended(u["turn"]), timeout=30)
                # a proposed mark: "not that"
                r = say("Please mark Saturday for the meeting.", conv)
                evs = h.events_until(conv, 0, lambda e: any(x["kind"] == "act" for x in asks_of(e)), timeout=30)
                act = [x for x in asks_of(evs) if x["kind"] == "act"][-1]
                a = say("Not that", conv)
                self.assertEqual((a["answered"]["kind"], a["answered"]["answer"], a["answered"]["mark"]), ("act", "not_this", "Saturday morning"))
                # a worker's Start: "Start it" starts it, and she says so by name
                r = say("Have a worker count the stars.", conv)
                evs = h.events_until(conv, 0, lambda e: any(x["kind"] == "worker" for x in asks_of(e)), timeout=30)
                a = say("Start it", conv)
                self.assertEqual((a["answered"]["kind"], a["answered"]["answer"], a["answered"]["task"]), ("worker", "yes", "count the stars"))
                h.events_until(conv, 0, lambda e: "has started on it." in "".join(x.get("text", "") for x in e if x.get("kind") == "agent"), timeout=30)
                st = h.call("GET", "/status")["agents"]
                self.assertTrue(any((x.get("body") or {}).get("task") == "count the stars" for x in st), "the worker did not start")
            finally:
                h.stop()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIn("never expecting a button", host_mod.DEFAULT_CHARACTER)

    def test_voice_and_name(self):
        # 7. the voice receives a feeling; 8. no name taken from the machine
        self.assertIn("never tell a feeling what to be", host_mod.VOICE)
        self.assertIn("Nervous is a fine way to arrive", host_mod.VOICE)
        self.assertIn("by no other name", host_mod.DEFAULT_CHARACTER)
        self.assertIn("never one taken from this computer, its account", host_mod.house_note([], [], "person:player", TODAY))
        skill = (Path(host_mod.__file__).resolve().parent.parent / host_mod.CHIEF_OF_STAFF_SKILL).read_text()
        for want in ("Decided: Saturday morning, for the meeting day.", "Never say you do not know your own page",
                     "never *\"there is no need to be nervous\"*", "Vega has started on it."):
            self.assertIn(want, skill)


class TrustLayer(unittest.TestCase):
    """The trust layer (DESIGN-TALK.md), the host's side (items 1 to 8): what the page needs to draw what
    is running, at the depth the person chooses."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-trust-"))
        cls.hq = cls.tmp / "home"
        (cls.hq / "record").mkdir(parents=True)
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / ".hud-token").write_text("t0ken\n")
        fake = [sys.executable, "-I", str(HERE / "fake_agent.py")]
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": fake, "cwd": str(cls.tmp)},
            {"id": "proxied", "of": "person:player", "kind": "guest", "actor": "agent:proxied",
             "command": fake, "cwd": str(cls.tmp), "proxy": "http://127.0.0.1:1"}]}))
        cls.usage = cls.tmp / "statusline-last.json"
        cls.usage.write_text(json.dumps({"rate_limits": {"five_hour": {"used_percentage": 3, "resets_at": 1793000000},
                                                         "seven_day": {"used_percentage": 64, "resets_at": 1793500000}},
                                         "cost": {"total_cost_usd": 999}}))
        cls.ledger = cls.tmp / "cost-ledger.jsonl"
        cls.ledger.write_text("")
        cls.vendors = cls.tmp / "vendors.json"
        cls.vendors.write_text(json.dumps({"vendors": {"anthropic": {"kind": "anthropic", "host": "api.anthropic.com"},
                                                       "local": {"kind": "openai", "host": "127.0.0.1"}}}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def host(self):
        return Host(self.hq, ["--usage-file", str(self.usage), "--cost-ledger", str(self.ledger),
                              "--vendors", str(self.vendors), "--routes", str(self.tmp / "no-routes.json")])

    def say(self, h, text, conv=None, agent="yours"):
        r = h.call("POST", "/say", {"agent": agent, "text": text, **({"conversation": conv} if conv else {})})
        return r["conversation"], r["turn"]

    def test_figures_turns_clock_notices(self):
        h = self.host()
        try:
            conv, t = self.say(h, "Good morning")
            evs = h.events_until(conv, 0, turn_ended(t))
            # 1, 8. the harness's figures, per agent, each real or null; the stand-in says it is one
            states = [e for e in evs if e.get("kind") == "state"]
            self.assertTrue(states and all(set(host_mod.FIGURE_KEYS) <= set(e["figures"]) for e in states))
            self.assertTrue(all("clock" in e for e in states))
            f = h.agent("yours")["figures"]
            self.assertEqual(f["model"], "stand-in-model-1")              # the turn's own model
            self.assertEqual(f["effort"], "high")
            self.assertEqual(f["mode"], "default")
            self.assertEqual(f["version"], "lionsberg-stand-in 0.1")
            self.assertTrue(f["stand_in"])
            self.assertEqual((f["week_pct"], f["five_hour_pct"]), (48.0, 12.0))   # the harness's own report wins
            self.assertRegex(f["week_resets"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertEqual(f["context_tokens"], 18000 + 2700 + 135)
            self.assertAlmostEqual(f["context_used_pct"], round(20835 * 100 / 200000, 1))
            self.assertEqual((f["tokens_in"], f["tokens_out"]), (2700, 135))
            self.assertAlmostEqual(f["cost_session"], 0.0133)
            self.assertAlmostEqual(f["cost_turn"], 0.0133)
            self.assertEqual(f["cache"]["write"], 200)
            self.assertAlmostEqual(f["cache"]["read_pct"], round(2460 * 100 / 2700, 1))
            # 2. the turn's accounting
            end = next(e for e in evs if e.get("kind") == "turn_end")
            for k in ("duration_ms", "tokens_in", "tokens_out", "cost", "tools", "left_computer", "left_known", "done_at"):
                self.assertIn(k, end)
            self.assertEqual((end["tokens_in"], end["tokens_out"], end["tools"]), (2700, 135, []))
            self.assertAlmostEqual(end["cost"], 0.0133)
            self.assertGreaterEqual(end["duration_ms"], 0)
            self.assertEqual((end["left_computer"], end["left_known"]), (False, False))    # no proxy in the path
            self.assertTrue(any(e.get("kind") == "figures" for e in evs))
            n = len(evs)
            conv, t = self.say(h, "Please write up my notes", conv)
            evs = h.events_until(conv, n, turn_ended(t), timeout=30)
            end = next(e for e in evs if e.get("kind") == "turn_end")
            self.assertEqual({x["name"]: x["count"] for x in end["tools"]}, {"Read": 2, "Grep": 1, "Bash": 1, "Edit": 1})
            self.assertAlmostEqual(end["cost"], 0.0143)                   # what this turn added to the sitting
            self.assertAlmostEqual(h.agent("yours")["figures"]["cost_session"], 0.0276)
            self.assertEqual(h.agent("yours")["figures"]["tokens_out"], 135 + 150)
            n += len(evs)
            conv, t = self.say(h, "Can you look it up", conv)
            evs = h.events_until(conv, n, turn_ended(t))
            end = next(e for e in evs if e.get("kind") == "turn_end")
            self.assertEqual((end["left_computer"], end["left_known"]), (True, True))      # a fetch left
            self.assertEqual(end["tools"], [{"name": "WebFetch", "count": 1}])
            n += len(evs)
            # 3. the thinking clock mid-turn, and the harness's thinking summaries as `thought`
            conv, t = self.say(h, "Tell me the long version", conv)
            time.sleep(1.0)
            clock = h.agent("yours")["clock"]
            self.assertEqual(clock["phase"], "thinking")
            self.assertGreaterEqual(clock["thinking_ms"], 600)
            self.assertGreaterEqual(clock["turn_ms"], clock["thinking_ms"])
            evs = h.events_until(conv, n, turn_ended(t), timeout=30)
            self.assertIsNone(h.agent("yours")["clock"])                  # between turns, no clock
            n += len(evs)
            conv, t = self.say(h, "Ponder it first", conv)
            evs = h.events_until(conv, n, turn_ended(t))
            self.assertEqual("".join(e["text"] for e in evs if e.get("kind") == "thought"),
                             "Weighing what she asked against the week.")
            n += len(evs)
            # 6. notices said plainly, with the figures that caused them
            conv, t = self.say(h, "We are near the edge", conv)
            evs = h.events_until(conv, n, turn_ended(t))
            hi = [e for e in evs if e.get("kind") == "notice"]
            self.assertEqual([e["notice"] for e in hi], ["context_high"])
            self.assertEqual(hi[0]["words"], "We are near the edge of what I can hold. Shall I fold the earlier talk now, or start fresh?")
            self.assertGreaterEqual(hi[0]["figures"]["context_used_pct"], 80)
            n += len(evs)
            conv, t = self.say(h, "Fold the talk", conv)
            evs = h.events_until(conv, n, turn_ended(t))
            folded = [e for e in evs if e.get("kind") == "notice"]
            self.assertEqual([e["notice"] for e in folded], ["compacted"])
            self.assertGreater(folded[0]["figures"]["tokens_before"], 170000)
            self.assertEqual(folded[0]["figures"]["tokens_after"], 9000)
            self.assertEqual(folded[0]["words"], "I folded our earlier talk into a summary to make room.")
            n += len(evs)
            conv, t = self.say(h, "Is the week spent", conv)
            evs = h.events_until(conv, n, turn_ended(t))
            spent = [e for e in evs if e.get("kind") == "notice"]
            self.assertEqual([e["notice"] for e in spent], ["usage_limit_open"])
            self.assertEqual(spent[0]["figures"]["kind"], "quota_exhausted")
            self.assertEqual(spent[0]["words"], "Your plan's use is spent for now. I cannot go on until it resets.")
            n += len(evs)
            # 6. an adapter restart under a conversation under way: picked up, and said
            kids = subprocess.run(["pgrep", "-P", str(h.proc.pid)], capture_output=True, text=True).stdout.split()
            for pid in kids:
                os.kill(int(pid), signal.SIGTERM)
            for _ in range(50):
                if h.agent("yours")["state"] == "asleep":
                    break
                time.sleep(0.1)
            conv, t = self.say(h, "Are you there", conv)
            evs = h.events_until(conv, n, turn_ended(t), timeout=30)
            self.assertIn("restarted", [e.get("notice") for e in evs if e.get("kind") == "notice"])
            f = h.agent("yours")["figures"]
            self.assertAlmostEqual(f["cost_session"], f["cost_turn"])     # a new process is a new sitting
            # 7. GET /figures: the whole block and every raw field the harness gave, behind the token
            self.assertEqual(h.get("/figures?agent=yours", token=False)[0], 403)
            self.assertEqual(h.get("/figures?agent=nobody")[0], 404)
            s, full = h.get("/figures?agent=yours")
            self.assertEqual(s, 200)
            self.assertEqual(full["figures"], h.agent("yours")["figures"])
            raw = full["raw"]
            self.assertEqual(raw["agent_info"]["title"], "The stand-in")
            self.assertEqual([o["id"] for o in raw["config_options"]], ["model", "effort"])
            self.assertEqual(raw["usage_update"]["cost"]["currency"], "USD")
            self.assertIn("unifiedWindows", raw["rate_limit"]["info"])
            self.assertEqual(raw["windows"]["source"], "rate_limit")
            self.assertIn("quota", raw["last_turn"])
            self.assertEqual(raw["compactions"], 1)
        finally:
            h.stop()

    def test_modes_asks_workers_and_routes(self):
        h = self.host()
        try:
            conv, t = self.say(h, "Good morning")
            evs = h.events_until(conv, 0, turn_ended(t))
            n = len(evs)
            # 5. the harness's own modes, in its own names; one asking about nothing is listed, never set
            s, m = h.get("/mode?agent=yours")
            self.assertEqual(s, 200)
            self.assertEqual(m["current"], "default")
            self.assertEqual([(x["id"], x["name"]) for x in m["modes"]],
                             [("default", "Manual"), ("acceptEdits", "Accept edits"), ("plan", "Plan"),
                              ("auto", "Auto"), ("bypassPermissions", "Bypass permissions")])
            self.assertEqual([x["face"] for x in m["modes"]], [True, True, True, True, False])
            self.assertTrue(all(x["words"] for x in m["modes"] if x["face"]))   # the harness's own ids carry the Talk's plain words
            self.assertNotIn("bypassPermissions", [x["id"] for x in h.agent("yours")["modes"]])
            self.assertEqual(h.call("POST", "/mode", {"agent": "yours", "mode": "acceptEdits"}), {"ok": True})
            self.assertEqual(h.agent("yours")["figures"]["mode"], "acceptEdits")
            # 5. an ask keeps the harness's own title and options under the plain face
            conv, t = self.say(h, "What about the costs", conv)
            ev = h.events_until(conv, n, lambda e: any(x.get("kind") == "ask" for x in e))
            ask = next(x["ask"] for x in ev if x.get("kind") == "ask")
            self.assertEqual(ask["raw"]["title"], "Send the costs to Cell Two")
            self.assertEqual([o["name"] for o in ask["raw"]["options"]], ["Allow once", "Always allow", "Reject"])
            self.assertIsNone(ask["for_kind"])                            # it leaves the computer: answered once
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            evs = h.events_until(conv, n, turn_ended(t))
            end = next(e for e in evs if e.get("kind") == "turn_end")
            self.assertFalse(end["left_computer"])                        # her no: nothing left
            n += len(evs)
            # 4. a worker's row, and its chief told when it changes
            b = h.call("POST", "/body", {"task": "Read the rooms."})
            h.events_until(b["conversation"], 0, turn_ended(1), timeout=30)
            for _ in range(30):
                w = h.agent(b["agent"])["worker"]
                if w["state"] == "done":
                    break
                time.sleep(0.1)
            self.assertEqual(set(w), {"task", "started", "elapsed_ms", "tokens", "state", "stopped", "last_tool", "estimate_min", "over", "answered"})
            self.assertFalse(w["stopped"])                               # a finish is not a stop
            self.assertEqual((w["task"], w["state"], w["estimate_min"], w["over"]), ("Read the rooms.", "done", 20, False))
            self.assertGreater(w["elapsed_ms"], 0)
            self.assertEqual(w["tokens"], 18000 + 2700 + 135)
            rows = h.events_until(conv, n, lambda e: any(x.get("kind") == "workers" for x in e), timeout=10)
            rows = next(x for x in rows if x.get("kind") == "workers")["workers"]
            self.assertEqual([(r["name"], r["task"]) for r in rows], [(b["name"], "Read the rooms.")])
            # 4. a worker stopped mid-task says "stopped", never "done", in its row
            b2 = h.call("POST", "/body", {"task": "Read the rooms slowly."})
            time.sleep(0.5)
            self.assertEqual(h.call("POST", "/stop", {"conversation": b2["conversation"]}), {"ok": True})
            w2 = h.agent(b2["agent"])["worker"]
            self.assertEqual((w2["state"], w2["stopped"], w2["over"]), ("stopped", True, False))
            # 2. what left, from the proxy's route lines in the turn's window
            pconv, pt = self.say(h, "Ponder it first", agent="proxied")
            stamp = datetime.now().astimezone().isoformat(timespec="seconds")
            with open(self.hq / "proxy-log.jsonl", "a") as fh:
                for vendor in ("anthropic", "local"):
                    fh.write(json.dumps({"type": "route", "ts": stamp, "body": {"route_id": "r-" + vendor, "vendor": vendor}}) + "\n")
            evs = h.events_until(pconv, 0, turn_ended(pt))
            end = next(e for e in evs if e.get("kind") == "turn_end")
            self.assertEqual((end["routes"], end["routes_away"], end["left_computer"], end["left_known"]), (2, 1, True, True))
        finally:
            h.stop()

    def test_forms(self):
        A = host_mod.Agent
        # 5. "Yes, for this kind" is the harness's own allow-for-session option, and absent when it offers none
        opts = [{"id": "once", "name": "Allow once", "kind": "allow_once"},
                {"id": "always", "name": "Yes, and do not ask again for this kind", "kind": "allow_always"},
                {"id": "no", "name": "No", "kind": "reject_once"}]
        ask = A._harness({"options": list(opts), "leaves": False}, {"title": "Bash command"}, opts)
        self.assertEqual(ask["for_kind"], {"id": "always", "name": "Yes, and do not ask again for this kind"})
        self.assertEqual(ask["raw"], {"title": "Bash command", "options": opts})
        self.assertIsNone(A._harness({"options": opts[:1] + opts[2:], "leaves": False}, {}, opts)["for_kind"])
        self.assertIsNone(A._harness({"options": list(opts), "leaves": True}, {}, opts)["for_kind"])
        # the Claude harness's own mode ids land where they mean (its words alone would mislead)
        pm = host_mod.plain_mode
        self.assertEqual(pm({"id": "default", "name": "Manual", "description": "Always ask before making changes"}), "everything")
        self.assertEqual(pm({"id": "acceptEdits", "name": "Accept edits", "description": "Automatically accept all file edits"}), "changes")
        self.assertEqual(pm({"id": "auto", "name": "Auto", "description": "Claude handles permission decisions"}), "outward")
        self.assertEqual(pm({"id": "bypassPermissions", "name": "Bypass permissions"}), "steward")
        # 1. the windows: the harness's report, else its status file; a fraction becomes a percentage
        w = host_mod.rate_windows({"rateLimitType": "five_hour", "utilization": 0.25, "resetsAt": 1793000000})
        self.assertEqual(w["five_hour"]["pct"], 25.0)
        self.assertNotIn("seven_day", w)
        self.assertEqual(host_mod.rate_windows({"status": "allowed"}), {})
        import types
        hostish = types.SimpleNamespace(usage_file=self.usage, ledger=host_mod.CostLedger(self.ledger),
                                        words=lambda k, **kw: "")
        a = A(hostish, {"id": "x"})
        f = a.figures()
        self.assertEqual(set(f), set(host_mod.FIGURE_KEYS))
        self.assertEqual((f["week_pct"], f["five_hour_pct"]), (64, 3))  # from the status file
        self.assertTrue(all(f[k] is None for k in host_mod.FIGURE_KEYS if k not in ("week_pct", "week_resets",
                                                                                    "five_hour_pct", "five_hour_resets")))
        hostish.usage_file = self.tmp / "absent.json"
        self.assertIsNone(a.figures()["week_pct"])                      # no source: null, never guessed
        # the cost ledger, by the session id, when the harness reported no cost
        sid = "0b7e0f3c-1111-4222-8333-944455556666"
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps({"ts": "2026-10-25T15:00:00-07:00", "session": sid, "cost_usd": 1.5}) + "\n")
            fh.write(json.dumps({"ts": "2026-10-25T15:05:00-07:00", "session": sid, "cost_usd": 2.25}) + "\n")
        a.conv = types.SimpleNamespace(acp=sid)
        self.assertEqual(a.figures()["cost_session"], 2.25)
        a.usage = {"cost": {"amount": 0.5, "currency": "USD"}}
        self.assertEqual(a.figures()["cost_session"], 0.5)             # the harness's own report wins


class ChainWatch(unittest.TestCase):
    """The chain's watch, items 1 to 5, with a short minute for the clock."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dock-chain-"))
        cls.hq = cls.tmp / "home"
        (cls.hq / "record").mkdir(parents=True)
        (cls.hq / "holon.json").write_text(json.dumps({"v": 1, "id": "h0me", "name": "Test Home", "kind": "person",
                                                       "keeper": "person:player"}) + "\n")
        (cls.hq / ".hud-token").write_text("t0ken\n")
        (cls.hq / "agents.json").write_text(json.dumps({"agents": [
            {"id": "yours", "name": "Polaris", "of": "person:player", "kind": "harness", "actor": "agent:player-agent",
             "command": [sys.executable, "-I", str(HERE / "fake_agent.py")], "cwd": str(cls.tmp)}]}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_forms(self):
        m = host_mod
        # 1. the box: "about {n} minutes" after the task's lead, else twenty
        said = ("At this week's pace a worker adds an hour or two. The task, in your words: count the stars. "
                "About 35 minutes; it writes only in its own folder. Start it?")
        self.assertEqual(m.worker_proposal(said), "count the stars")
        self.assertEqual(m.worker_estimate(said), 35)
        self.assertEqual(m.worker_estimate("The task, in your words: count the stars. Start it?"), 20)
        # 3. a dependency, by a worker's name, and the shape that lets it start
        names = ["Vega", "Rigel"]
        self.assertEqual(m.worker_depends("The task, in your words: seat them after Vega. Start it?", names), "Vega")
        self.assertEqual(m.worker_depends("The task, in your words: build using Rigel's list. Start it?", names), "Rigel")
        self.assertIsNone(m.worker_depends("The task, in your words: seat them after lunch. Start it?", names))
        self.assertEqual(m.worker_shape("x\nThe result's shape: a list of names, one per line.\nStart it?"),
                         "a list of names, one per line")
        self.assertIsNone(m.worker_shape("no shape here"))
        # 2. the three answers
        self.assertEqual(m.over_answer("Let it run: about 12 minutes more. It is close."), ("run", 12))
        self.assertEqual(m.over_answer("Split: only the first chapter."), ("split", "only the first chapter."))
        self.assertEqual(m.over_answer("Start another: count the moons, about 5 minutes."),
                         ("another", "count the moons, about 5 minutes."))
        self.assertIsNone(m.over_answer("I will think about it."))
        # 2. once per box, never twice in ten minutes (a fake clock: minute = 1 second)
        due = m.over_due
        self.assertFalse(due(20, 30, None, None, 1000, 1))       # 30 of 20: not past half again
        self.assertTrue(due(20, 31, None, None, 1000, 1))        # 31 of 20: past
        self.assertFalse(due(20, 40, 20, 1000, 2000, 1))         # this box already told
        self.assertFalse(due(30, 46, 20, 1000, 1005, 1))         # a new box, but five minutes since the last
        self.assertTrue(due(30, 46, 20, 1000, 1600, 1))          # a new box, ten minutes on
        # the half-hour look's quiet answer
        self.assertTrue(m.NOTHING_MOVED.fullmatch("Nothing moved."))
        self.assertFalse(m.NOTHING_MOVED.fullmatch("Moved: Rigel now builds against the shape."))
        # the box on the chain, by the house's defaults: over 10 cut when something waits on it; over 30 cut anywhere
        self.assertEqual(m.box_refusal(20, "line"), "on_chain")
        self.assertIsNone(m.box_refusal(20, None))
        self.assertIsNone(m.box_refusal(8, "depends"))
        self.assertEqual(m.box_refusal(45, None), "over_max")
        self.assertIsNone(m.box_refusal(45, None, dict(m.DEFAULT_BOX, box_max=60)))
        self.assertEqual(m.waited_on("x", names, "count them, then seat them", [], "count them"), "line")
        self.assertEqual(m.waited_on("x", names, "so", ["Count the stars by Friday"], "count the stars"), "house")
        self.assertEqual(m.waited_on("The task, in your words: seat after Vega. Start it?", names, "", [], "seat"), "depends")
        self.assertIsNone(m.waited_on("x", names, "count the stars", ["The hall"], "count the stars"))
        self.assertEqual(m.box_answer("Stages: read the letters, about 15 minutes; sort them, about 10 minutes; \u2026"),
                         ("stages", [{"task": "read the letters", "estimate_min": 15},
                                     {"task": "sort them", "estimate_min": 10}]))
        self.assertEqual(m.box_answer("Off the chain: hands back every 10 minutes."), ("off_chain", 10))
        self.assertIsNone(m.box_answer("Off the chain: hands back every 45 minutes."))
        self.assertIsNone(m.box_answer("Stages: read the letters; sort them, about 10 minutes."))
        # the chain's form: beside runs in parallel, after waits, a check the handback must pass; no marker, in order
        form = ("Stages: A, about 4 minutes, check `python3 -I check.py pass`; B, about 4 minutes, beside A; "
                "C, about 5 minutes, after A and B; D, about 3 minutes.")
        st = m.box_answer(form)[1]
        self.assertEqual(st, [{"task": "A", "estimate_min": 4, "check": "python3 -I check.py pass"},
                              {"task": "B", "estimate_min": 4, "beside": "A"},
                              {"task": "C", "estimate_min": 5, "after": ["A", "B"]},
                              {"task": "D", "estimate_min": 3}])
        self.assertEqual(m.stage_needs(st), [[], [], [0, 1], [0, 1, 2]])
        self.assertEqual(m.stage_needs([{"task": "x"}, {"task": "y", "beside": "nowhere"}]), [[], [0]])
        sd = m.silent_due
        self.assertFalse(sd(10, 1000, 1009, None, None, 1))      # nine minutes quiet: within its promise
        self.assertTrue(sd(10, 1000, 1011, None, None, 1))       # eleven: silent
        self.assertFalse(sd(10, 1000, 1030, 1000, 1011, 1))      # this silence already told
        self.assertFalse(sd(10, 1020, 1035, 1000, 1030, 1))      # a new silence, five minutes since the last

    def test_watch(self):
        h = Host(self.hq, ["--minute", "0.1", "--watch-every", "0.2"])
        kinds = lambda e, k: [x for x in e if x.get("kind") == k]
        try:
            # 3. a contract before a dependency: refused, then proposed with the result's shape
            r = h.call("POST", "/say", {"agent": "yours", "text": "Have a worker make the seating plan after Vega."})
            conv = r["conversation"]
            evs = h.events_until(conv, 0, lambda e: kinds(e, "ask"), timeout=30)
            ref = [x for x in kinds(evs, "notice") if x.get("notice") == "dependency_refused"]
            self.assertEqual([(x["worker"], x["task"]) for x in ref], [("Vega", "make the seating plan after Vega")])
            self.assertTrue(ref[0]["words"])
            ask = kinds(evs, "ask")[0]["ask"]
            self.assertEqual((ask["kind"], ask["task"], ask["shape"], ask["estimate_min"]),
                             ("worker", "make the seating plan after Vega", "a list of names, one per line", 5))
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            # 1. every worker carries its box; 2. the watch gives the chief of staff a turn for each past it
            ws = [h.call("POST", "/body", {"task": t, "estimate_min": 1})
                  for t in ("take your time and run", "take your time and split", "take your time, another")]
            names = [w["name"] for w in ws]
            evs = h.events_until(conv, 0, lambda e: len(kinds(e, "watch_move")) >= 3, timeout=30)
            over = [x for x in kinds(evs, "notice") if x.get("notice") == "worker_over"]
            self.assertEqual(sorted(x["worker"] for x in over), sorted(names))
            self.assertTrue(all(x["estimate_min"] == 1 and x["elapsed_min"] >= 1 and x["words"] for x in over))
            moves = {x["worker"]: x for x in kinds(evs, "watch_move")}
            self.assertEqual(moves[names[0]]["move"], "run")
            self.assertGreaterEqual(moves[names[0]]["estimate_min"], 60)
            self.assertEqual((moves[names[1]]["move"], moves[names[1]]["line"]),
                             ("split", "only the first chapter for " + names[1] + ". The rest can wait for the next box."))
            note = (self.tmp / "bg" / names[1].lower() / "task-note.md").read_text()
            self.assertIn("from the chief of staff: only the first chapter", note)
            self.assertEqual((moves[names[2]]["move"], moves[names[2]]["task"], moves[names[2]]["estimate_min"]),
                             ("another", "count the moons", 5))
            evs = h.events_until(conv, 0, lambda e: any(x["ask"]["task"] == "count the moons" for x in kinds(e, "ask")),
                                 timeout=10)
            moons = next(x["ask"] for x in kinds(evs, "ask") if x["ask"]["task"] == "count the moons")
            self.assertEqual((moons["kind"], moons["estimate_min"]), ("worker", 5))
            row = h.agent(ws[0]["agent"])["worker"]
            self.assertEqual((row["over"], row["estimate_min"] >= 60), (False, True))
            row = h.agent(ws[1]["agent"])["worker"]
            self.assertEqual((row["over"], row["estimate_min"]), (True, 1))
            # 4. the half-hour look: the chain shown; nothing said to the person when nothing moved
            evs = h.events_until(conv, 0, lambda e: kinds(e, "chain"), timeout=15)
            chain = kinds(evs, "chain")[0]
            self.assertEqual(sorted(x["name"] for x in chain["workers"]), sorted(names))
            self.assertEqual(set(chain["workers"][0]), {"name", "task", "elapsed_min", "estimate_min", "state", "waiting_on"})
            after = h.events_until(conv, chain["n"] + 1, lambda e: kinds(e, "turn_end"), timeout=15)
            self.assertEqual(kinds(after, "agent"), [], "the half-hour look spoke when nothing moved")
            # ... and its words when something moved (a worker waiting on something, by its status)
            (self.tmp / "bg" / names[0].lower()).mkdir(parents=True, exist_ok=True)
            (self.tmp / "bg" / names[0].lower() / "status.md").write_text("seating\nWaiting on: the guest list\n")
            evs = h.events_until(conv, chain["n"] + 1, lambda e: any("Moved:" in x.get("text", "") for x in kinds(e, "agent")),
                                 timeout=15)
            second = kinds(evs, "chain")[0]
            self.assertEqual(next(x["waiting_on"] for x in second["workers"] if x["name"] == names[0]), "the guest list")
            # once per box: the split worker kept its box and was told once
            evs = h.events_until(conv, 0, lambda e: any(x.get("n", -1) >= second["n"] for x in e), timeout=5)
            told = [x for x in kinds(evs, "notice") if x.get("notice") == "worker_over" and x["worker"] == names[1]]
            self.assertEqual(len(told), 1)
        finally:
            h.stop()

    def test_box_on_chain(self):
        """The box on the chain is small (skills/the-chief-of-staff rule 25): the long box refused and cut
        into stages; a study set off the chain, started, and its silence told once; an hour refused outright."""
        hq = self.tmp / "home-box"            # a house of its own: its bodies and talks never reach the other tests
        shutil.copytree(self.hq, hq, ignore=shutil.ignore_patterns(".agent-host*"))
        h = Host(hq, ["--minute", "0.1", "--watch-every", "0.2"])
        kinds = lambda e, k: [x for x in e if x.get("kind") == k]
        boxed = lambda e: [x for x in kinds(e, "notice") if x.get("notice") == "box_too_long"]
        try:
            # 1. a 20-minute box the person's line puts on the chain ("then"): no card, a turn, stages, one card
            r = h.call("POST", "/say", {"agent": "yours", "text": "Have a worker do a 20-minute count of the stars, then seat the guests."})
            conv = r["conversation"]
            task = "do a 20-minute count of the stars, then seat the guests"
            evs = h.events_until(conv, 0, lambda e: kinds(e, "ask"), timeout=30)
            ref = boxed(evs)
            self.assertEqual([(x["task"], x["estimate_min"], x["why"], x["waited_on"]) for x in ref],
                             [(task, 20, "on_chain", "line")])
            self.assertTrue(ref[0]["words"])
            asks = [x["ask"] for x in kinds(evs, "ask")]
            self.assertEqual(len(asks), 1)
            self.assertEqual((asks[0]["task"], asks[0]["estimate_min"], asks[0]["stages"]),
                             ("the first half of " + task, 5,
                              [{"task": "the first half of " + task, "estimate_min": 5},
                               {"task": "the second half of " + task, "estimate_min": 5}]))
            self.assertEqual(kinds(evs, "box_move")[0]["move"], "stages")
            h.call("POST", "/answer", {"conversation": conv, "ask": asks[0]["id"], "answer": "not_this"})
            seen = evs[-1]["n"] + 1
            # 2. a study on the chain ("before"): set off the chain, its card says so; started, the body carries it
            h.call("POST", "/say", {"conversation": conv, "agent": "yours",
                                    "text": "Have a worker do a 20-minute study of the old letters before the talk."})
            evs = h.events_until(conv, seen, lambda e: kinds(e, "ask"), timeout=30)
            study = "do a 20-minute study of the old letters before the talk"
            self.assertEqual([(x["task"], x["why"]) for x in boxed(evs)], [(study, "on_chain")])
            ask = kinds(evs, "ask")[0]["ask"]
            self.assertEqual((ask["task"], ask["estimate_min"], ask["off_chain"], ask["handback_every_min"]),
                             (study, 20, True, 5))
            self.assertNotIn("stages", ask)
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            seen = evs[-1]["n"] + 1
            w = h.call("POST", "/body", {"task": study})
            bodies = json.loads(h.bodies().read_text())["bodies"]
            body = next(b["body"] for b in bodies if b["id"] == w["agent"])
            self.assertEqual((body["off_chain"], body["handback_every_min"], body["estimate_min"]), (True, 5, 20))
            # ... and an off-chain worker that writes nothing to its status.md: told once
            q = h.call("POST", "/body", {"task": "take your time off the chain", "off_chain": True,
                                         "handback_every_min": 1, "estimate_min": 50})
            evs = h.events_until(conv, seen, lambda e: any(x.get("notice") == "worker_silent" and x["worker"] == q["name"]
                                                           for x in kinds(e, "notice")), timeout=15)
            silent = [x for x in kinds(evs, "notice") if x.get("notice") == "worker_silent" and x["worker"] == q["name"]]
            self.assertEqual((silent[0]["worker"], silent[0]["handback_every_min"]), (q["name"], 1))
            self.assertTrue(silent[0]["silent_min"] >= 1 and silent[0]["words"])
            time.sleep(2.5)                     # twenty-five minutes of the test's clock, nothing written
            evs = h.events_until(conv, seen, lambda e: any(x.get("n", -1) >= evs[-1]["n"] for x in e), timeout=5)
            self.assertEqual(len([x for x in kinds(evs, "notice") if x.get("notice") == "worker_silent"
                                  and x["worker"] == q["name"]]), 1)
            seen = evs[-1]["n"] + 1
            # 3. an hour and a half, nothing waiting on it: cut outright with the same notice, then stages
            h.call("POST", "/say", {"conversation": conv, "agent": "yours", "text": "Have a worker do a 90-minute sort of the archive."})
            evs = h.events_until(conv, seen, lambda e: kinds(e, "ask"), timeout=30)
            sort = "do a 90-minute sort of the archive"
            self.assertEqual([(x["task"], x["estimate_min"], x["why"], x["waited_on"]) for x in boxed(evs)],
                             [(sort, 90, "over_max", None)])
            asks = [x["ask"] for x in kinds(evs, "ask")]
            self.assertEqual([(a["task"], a["estimate_min"]) for a in asks], [("the first half of " + sort, 5)])
        finally:
            h.stop()

    def test_settings(self):
        """The box is the house's to set: house.json's "box" first, then the agents row, then the defaults."""
        m = host_mod
        self.assertEqual(m.box_settings({}, []), {"box_min": 5, "box_chain_max": 10, "box_max": 30, "handback_every_min": 5})
        self.assertEqual(m.box_settings({"box": {"box_chain_max": 12, "box_max": True}}, [{"box": {"box_max": 40, "box_min": 0}}]),
                         {"box_min": 5, "box_chain_max": 12, "box_max": 40, "handback_every_min": 5})
        self.assertEqual(m.box_settings({"box": {"box_max": 45}}, [{"box": {"box_max": 40}}])["box_max"], 45)
        hq = self.tmp / "home-settings"
        shutil.copytree(self.hq, hq, ignore=shutil.ignore_patterns(".agent-host*"))
        rows = json.loads((hq / "agents.json").read_text())
        rows["agents"][0]["box"] = {"handback_every_min": 7, "box_max": 40}
        (hq / "agents.json").write_text(json.dumps(rows))
        (hq / "house.json").write_text(json.dumps({"box": {"box_chain_max": 12, "box_max": 45}}))
        h = Host(hq, ["--minute", "0.1", "--watch-every", "0.2"])
        try:
            self.assertEqual(h.call("GET", "/status")["box"],
                             {"box_min": 5, "box_chain_max": 12, "box_max": 45, "handback_every_min": 7})
            (hq / "house.json").unlink()
            self.assertEqual(h.call("GET", "/status")["box"]["box_max"], 40)
        finally:
            h.stop()

    def test_stages(self):
        """The host runs the chain (rule 25): one Start; two stages side by side, the third after both with their
        handbacks; a failed check stops the chain and the notice fires once."""
        root = self.tmp / "chain"
        hq = root / "home"
        shutil.copytree(self.hq, hq, ignore=shutil.ignore_patterns(".agent-host*"))
        work = root / "work"
        (work / ".claude").mkdir(parents=True)
        (work / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(python3 -I check.py:*)"]}}))
        (work / "check.py").write_text("import sys\nprint('checked: ' + sys.argv[1])\nsys.exit(0 if sys.argv[1] == 'pass' else 3)\n")
        rows = json.loads((hq / "agents.json").read_text())
        rows["agents"][0]["cwd"] = str(work)
        (hq / "agents.json").write_text(json.dumps(rows))
        h = Host(hq, ["--minute", "0.1", "--watch-every", "60"])
        kinds = lambda e, k: [x for x in e if x.get("kind") == k]
        stages = lambda e, mv: [x for x in kinds(e, "stage") if x["move"] == mv]
        try:
            r = h.call("POST", "/say", {"agent": "yours", "text": "Have a worker build the map, then show it at the talk."})
            conv = r["conversation"]
            evs = h.events_until(conv, 0, lambda e: kinds(e, "ask"), timeout=30)
            ask = kinds(evs, "ask")[0]["ask"]
            self.assertEqual(ask["task"], "draw the hills")
            self.assertEqual([x["task"] for x in ask["stages"]], ["draw the hills", "draw the rivers", "join the map"])
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            seen = evs[-1]["n"] + 1
            w = h.call("POST", "/body", {"task": "draw the hills"})            # the one tap on Start
            self.assertEqual(len(w["started"]), 2)
            evs = h.events_until(conv, seen, lambda e: len(stages(e, "end")) >= 3, timeout=40)
            st = kinds(evs, "stage")
            self.assertEqual([(x["stage"], x["move"]) for x in st[:2]], [(1, "start"), (2, "start")])
            self.assertEqual(sorted((x["stage"], x["move"]) for x in st[2:4]), [(1, "end"), (2, "end")])
            self.assertEqual([(x["stage"], x["move"]) for x in st[4:]], [(3, "start"), (3, "end")])
            self.assertTrue(all(x["words"] and x["of"] == 3 for x in st))
            self.assertEqual(st[0]["check"], "python3 -I check.py pass")
            third = st[4]["worker"]
            given = (work / "bg" / third.lower() / "status.md").read_text()
            self.assertIn("Stage done: draw the hills.", given)
            self.assertIn("Stage done: draw the rivers.", given)
            self.assertIn("stage 3 of 3", given)
            evs = h.events_until(conv, seen, lambda e: kinds(e, "done"), timeout=20)
            self.assertEqual([x["worker"] for x in kinds(evs, "done")], [third])
            self.assertEqual([x for x in kinds(evs, "notice") if x.get("notice") == "stage_failed"], [])
            seen = evs[-1]["n"] + 1
            # a failed check stops the chain: the second stage never starts; one notice, and a turn
            h.call("POST", "/say", {"conversation": conv, "agent": "yours",
                                    "text": "Have a worker build the wall, then open the gate."})
            evs = h.events_until(conv, seen, lambda e: kinds(e, "ask"), timeout=30)
            ask = kinds(evs, "ask")[0]["ask"]
            self.assertEqual(ask["task"], "lay the stones")
            h.call("POST", "/answer", {"conversation": conv, "ask": ask["id"], "answer": "not_this"})
            seen = evs[-1]["n"] + 1
            h.call("POST", "/body", {"task": "lay the stones"})
            evs = h.events_until(conv, seen, lambda e: "shall I look" in "".join(x.get("text", "") for x in kinds(e, "agent")),
                                 timeout=40)
            failed = [x for x in kinds(evs, "notice") if x.get("notice") == "stage_failed"]
            self.assertEqual(len(failed), 1)
            self.assertEqual((failed[0]["stage"], failed[0]["task"], failed[0]["check"]),
                             (1, "lay the stones", "python3 -I check.py fail"))
            self.assertIn("checked: fail", failed[0]["last_lines"])
            self.assertTrue(failed[0]["words"])
            self.assertEqual([(x["stage"], x["move"]) for x in kinds(evs, "stage")], [(1, "start"), (1, "failed")])
            time.sleep(1.5)
            evs = h.events_until(conv, seen, lambda e: any(x.get("n", -1) >= evs[-1]["n"] for x in e), timeout=5)
            self.assertEqual(len([x for x in kinds(evs, "notice") if x.get("notice") == "stage_failed"]), 1)
            self.assertFalse(any(x["stage"] == 2 for x in kinds(evs, "stage")))
        finally:
            h.stop()


if __name__ == "__main__":
    unittest.main()
