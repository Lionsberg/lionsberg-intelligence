"""The living map's three sections of state.json (STATE.md `map`, `agreements`, `subscriptions`) and the HUD
view that reads them (hud/sightings.js): the state's shapes and their as_of, honest-empty, null-guards, the
owed Receipt rows reaching the state, the view served and registered, its words all in strings.json, and a
view that only reads."""
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
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
HUD = ENGINE.parent / "hud"
SERVE = HUD / "serve.py"
VIEW = HUD / "sightings.js"
CSS = HUD / "sightings.css"
sys.path.insert(0, str(ENGINE))
import engine   # noqa: E402
import holon    # noqa: E402
import record   # noqa: E402
import sightings  # noqa: E402
import owed as owed_mod  # noqa: E402
from gamecore import normalize, parse_time  # noqa: E402

A, B, C = "person:alice", "person:bob", "person:carol"
NOW = "2026-10-31T09:00:00-07:00"
STAMP = {"newest", "clock", "per_holon"}

# The DOM's and the language's own vocabulary, which a view cannot avoid writing: tag names, attribute and
# role names, typeof names, the slot and density names of the plug-in contract (shell.js), the view's own id
# and files, and one data token compared against the state, never shown (the kind whose open rows are marked).
DOM_WORDS = {"section", "table", "thead", "tbody", "button", "small", "span", "aria-label", "aria-pressed",
             "region", "object", "string", "number", "aside", "sightings", ".css", "./card.js", "./views-b.js",
             "\\u0000", "pain"}


def _source(path):
    s = Path(path).read_text(encoding="utf-8")
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", s)


def _literals(src):
    return [a or b or c for a, b, c in re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`]*)`', src)]


def _css_classes():
    out = set()
    for f in HUD.glob("*.css"):
        out |= set(re.findall(r"\.([A-Za-z_][\w-]*)", re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)))
    return out


def _strings():
    return json.loads((HUD / "strings.json").read_text(encoding="utf-8"))


class StateSections(unittest.TestCase):
    """build_state over the fixture HQ (a home and its first cell, with an Agreement and a Subscription Card)."""

    @classmethod
    def setUpClass(cls):
        src = ENGINE / "fixtures" / "hq"
        if not src.is_dir():
            raise unittest.SkipTest("no fixtures/hq beside the engine")
        cls.tmp = tempfile.mkdtemp(prefix="views-")
        cls.hq = os.path.join(cls.tmp, "hq")
        shutil.copytree(src, cls.hq, symlinks=True)
        cls.st = engine.build_state(cls.hq, now=NOW)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_three_sections_carry_as_of(self):
        for k in ("map", "agreements", "subscriptions"):
            self.assertIsInstance(self.st.get(k), dict, k)
            self.assertTrue(STAMP <= set(self.st[k]["as_of"]), k)
            self.assertEqual(set(self.st[k]["as_of"]["per_holon"]), {h["id"] for h in self.st["holons"]})

    def test_the_map_has_its_shape(self):
        m = self.st["map"]
        self.assertTrue({"by_place", "by_kind", "open", "pains_open", "scoreboard", "kinds", "retracted"} <= set(m))
        self.assertEqual(m["kinds"], list(sightings.NINE))
        rows = [r for kinds in m["by_place"].values() for rs in kinds.values() for r in rs]
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["paper"], sightings.paper(r))
            self.assertIn("life", r)
            self.assertEqual(r["open"], r["life"] not in sightings.ENDED)
        self.assertEqual(m["open"], sum(1 for r in rows if r["open"]))
        self.assertEqual(m["pains_open"], sum(1 for r in rows if r["open"] and r["kind"] == "pain"))
        self.assertIsInstance(m["scoreboard"], dict)

    def test_the_old_sightings_section_stays(self):
        for v in self.st["sightings"].values():
            self.assertTrue({"as_of", "new", "held", "elevated", "folded"} <= set(v))

    def test_agreements_with_their_clauses(self):
        rows = self.st["agreements"]["rows"]
        self.assertTrue(rows)
        for r in rows:
            self.assertTrue({"id", "holon", "state", "with", "sides", "crosses", "cadence", "clauses", "live"} <= set(r))
            self.assertIsInstance(r["clauses"], list)

    def test_subscriptions_with_what_is_due(self):
        s = self.st["subscriptions"]
        self.assertTrue(s["rows"])
        for r in s["rows"]:
            self.assertTrue({"source", "signals", "cadence", "surface", "bell", "basis"} <= set(r))
        per = self.st["subscriptions"]["as_of"]["per_holon"]
        for d in s["due"]:
            self.assertTrue({"source", "signal", "cadence", "last", "due_at", "overdue_s"} <= set(d))
            if d["source"] in per and per[d["source"]]:
                self.assertEqual(parse_time(d["last"]), parse_time(per[d["source"]]))   # last_seen is the holon's newest line

    def test_deterministic(self):
        again = engine.build_state(self.hq, now=NOW)
        for k in ("map", "agreements", "subscriptions"):
            a, b = dict(self.st[k]), dict(again[k])
            for x in (a, b):
                x["as_of"] = dict(x["as_of"], clock=None)
            self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True), k)


class HonestEmpty(unittest.TestCase):
    """A home with nothing but its inception: the three sections exist, empty, in their own shapes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="views-empty-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        record.make_key(A, cls.kd)
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        cls.env = dict(os.environ)
        os.environ["LIONSBERG_KEY_DIR"] = cls.kd
        cls.st = engine.build_state(cls.hq, now=NOW)

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls.env)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_empty_in_shape(self):
        m = self.st["map"]
        self.assertEqual((m["by_place"], m["by_kind"], m["open"], m["pains_open"], m["scoreboard"]), ({}, {}, 0, 0, {}))
        self.assertEqual(self.st["agreements"]["rows"], [])
        self.assertEqual((self.st["subscriptions"]["rows"], self.st["subscriptions"]["due"]), ([], []))
        for k in ("map", "agreements", "subscriptions"):
            self.assertTrue(STAMP <= set(self.st[k]["as_of"]))
        self.assertFalse([n for n in self.st["notes"] if "could not" in n and ("map" in n or "Agreement" in n or "heard" in n)])


class NullGuards(unittest.TestCase):
    def test_views_on_nothing(self):
        t = dt.datetime.fromisoformat(NOW)
        for folded, lines, holons in (({}, None, []), ({}, [], None), ({"admitted": None}, [None, 3, "x"], [{}]),
                                      ({"sightings": [None, 1.5, "s"]}, [{"id": 7}], [{"id": None}])):
            m, ag, subs, notes = engine._views(folded, lines, A, holons or [], None, t)
            self.assertEqual(m["kinds"], list(sightings.NINE))
            self.assertIsInstance(m["by_place"], dict)
            self.assertIsInstance(ag["rows"], list)
            self.assertEqual(set(subs), {"rows", "due"})
            self.assertIsInstance(notes, list)
            json.dumps([m, ag, subs], sort_keys=True)

    def test_views_with_no_actor(self):
        m, ag, subs, notes = engine._views({}, [], "", [], {}, dt.datetime.fromisoformat(NOW))
        self.assertEqual(subs["rows"], [])

    def test_receipt_args_on_nothing(self):
        for f in (None, {}, {"admitted": None}, {"admitted": {"h": None}}, {"admitted": {"h": {"x": 1}}}):
            self.assertEqual(engine._receipt_args(f, "h"), (False, set()))
        f = {"admitted": {"home": {A: {}, "agent:a": {}}, "cell": {A: {}, C: {}}}}
        self.assertEqual(engine._receipt_args(f, "home"), (True, {A, "agent:a"}))
        self.assertEqual(engine._receipt_args(f, None), (False, set()))

    def test_an_empty_people_never_means_everyone(self):
        # owed.py reads an empty `people` as every sender; so the engine does not ask for receipts then
        items = {"cards": [{"id": "q1", "kind": "card", "holon": "cell", "title": "Bring the plan", "asked": "request",
                            "to": "person:p", "holder": "person:p", "state": "open", "actor": "person:k", "for": "person:k",
                            "ts": "2026-10-20T09:00:00-07:00", "audience": "holon"}]}
        now = "2026-10-22T09:00:00-07:00"
        rows = lambda **kw: [e for e in owed_mod.owed(items, now=now, home="home", **kw)["entries"] if e["kind"] == "receipt"]
        self.assertEqual(len(rows(receipts=True, people=set())), 1)          # what the guard keeps out
        asks, people = engine._receipt_args({}, "home")
        self.assertEqual(rows(receipts=asks, people=people), [])


class OwedReceipts(unittest.TestCase):
    """alice's home (bob a co-member) and a cell carol keeps (alice and bob admitted). Requests two days old, no
    Receipt: the state's owed, from alice's seat."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="views-receipt-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        for x in (A, B, C):
            record.make_key(x, cls.kd)
        pk = lambda x: record.pubkey_of(record.find_key(None, x, cls.kd))
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        holon.admit(cls.hq, A, B, pk(B), ts="2026-10-24T08:01:00-07:00", key_dir=cls.kd)
        cell = os.path.join(cls.hq, "cells", "one")
        os.makedirs(os.path.dirname(cell))
        holon.init(cell, "One", "cell", C, key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        holon.admit(cell, C, A, pk(A), ts="2026-10-24T09:01:00-07:00", key_dir=cls.kd)
        holon.admit(cell, C, B, pk(B), ts="2026-10-24T09:02:00-07:00", key_dir=cls.kd)
        ask = lambda who, to, title, m: record.append(cell, who, who, "request", {"to": to, "title": title},
                                                      ts="2026-10-29T09:%02d:00-07:00" % m, key_dir=cls.kd)["line"]["id"]
        cls.r_in = ask(C, A, "Bring the plan", 0)        # from another holon to alice
        cls.r_out = ask(A, C, "Bring the chairs", 1)     # alice's own, to another holon's person
        cls.r_co = ask(A, B, "Bring the bread", 2)       # alice's own, to a co-member of her home
        cls.r_co2 = ask(B, A, "Bring the salt", 3)       # a co-member's, to alice
        cls.env = dict(os.environ)
        os.environ["LIONSBERG_KEY_DIR"] = cls.kd
        cls.st = engine.build_state(cls.hq, actor=A, now=NOW)
        cls.mine = [e for e in cls.st["owed"]["entries"]]

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls.env)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rows(self, rid, kind=None):
        return [e for e in self.mine if e["id"] == rid and (kind is None or e["kind"] == kind)]

    def test_a_request_to_me_is_one_row_not_two(self):
        self.assertEqual([e["kind"] for e in self.rows(self.r_in)], ["request"])
        self.assertEqual([e["kind"] for e in self.rows(self.r_co2)], ["request"])

    def test_my_own_line_waits_on_a_receipt_from_its_addressee(self):
        got = self.rows(self.r_out, "receipt")
        self.assertEqual([(e["holder"], e["addressee"], e["status"], e["minutes"]) for e in got], [(A, C, "waiting", 1)])

    def test_the_people_rule_a_home_co_member_owes_no_receipt(self):
        self.assertEqual(self.rows(self.r_co, "receipt"), [])
        # without the home's people, the same line would wait on a Receipt from bob: the rule is what keeps it out
        folded, holons, lines, _p, _c = engine.read_hq(self.hq)
        folded.pop("_fold", None); folded.pop("_paper", None)
        loose = owed_mod.owed(normalize(folded), actor=A, now=NOW, holons=holons, receipts=True, home=holons[0]["id"])
        self.assertEqual([e["addressee"] for e in loose["entries"] if e["id"] == self.r_co and e["kind"] == "receipt"], [B])


class TrustReachesTheTriage(unittest.TestCase):
    """A sighting a line the fold lists as unverified would close stays open: triage is given the fold whole."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="views-trust-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        for x in (A, C):
            record.make_key(x, cls.kd)
        pk = lambda x: record.pubkey_of(record.find_key(None, x, cls.kd))
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        cell = os.path.join(cls.hq, "cells", "one")
        os.makedirs(os.path.dirname(cell))
        holon.init(cell, "One", "cell", C, key_dir=cls.kd, ts="2026-10-24T09:00:00-07:00")
        holon.admit(cell, C, A, pk(A), ts="2026-10-24T09:01:00-07:00", key_dir=cls.kd)
        cls.cell_id = record.holon_info(cell)["id"]
        cls.sid = record.append(cell, C, C, "sight", {"kind": "defect", "text": "The gate sticks", "where": "the gate"},
                                ts="2026-10-29T09:00:00-07:00", key_dir=cls.kd)["line"]["id"]
        cls.settle = record.append(cell, A, A, "settle", {"text": "fixed it"}, {"anchored_to": [cls.sid]},
                                   ts="2026-10-29T10:00:00-07:00", sign=False, key_dir=cls.kd)["line"]["id"]
        cls.env = dict(os.environ)
        os.environ["LIONSBERG_KEY_DIR"] = cls.kd

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls.env)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_state_keeps_it_open(self):
        st = engine.build_state(self.hq, actor=A, now=NOW)
        rows = [r for b in st["sightings"].values() for k in ("new", "held", "elevated", "folded") for r in b[k]]
        self.assertEqual([(r["id"], r["life"]) for r in rows], [(self.sid, "seen")])

    def test_the_deal_command_passes_the_fold_whole(self):
        seen = []
        real = engine.sightings_mod.triage

        def spy(items, *a, **kw):
            seen.append(isinstance(items, dict) and "trust" in items)
            return real(items, *a, **kw)
        engine.sightings_mod.triage = spy
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                engine.main(["deal", self.hq, "--actor", A, "--now", NOW, "--json"])
        finally:
            engine.sightings_mod.triage = real
        self.assertEqual(seen, [True])


class Served(unittest.TestCase):
    """serve.py serves the view, its stylesheet, the registration and the words, as it serves the Wall."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="views-serve-")
        cls.kd = os.path.join(cls.tmp, "keys")
        os.makedirs(cls.kd, mode=0o700)
        record.make_key(A, cls.kd)
        cls.hq = os.path.join(cls.tmp, "hq")
        holon.init(cls.hq, "Alice", "person", A, key_dir=cls.kd, ts="2026-10-24T08:00:00-07:00")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        env = dict(os.environ, HOME=cls.tmp, LIONSBERG_KEY_DIR=cls.kd)
        cls.log = open(os.path.join(cls.tmp, "serve.log"), "w")
        cls.srv = subprocess.Popen([sys.executable, "-I", str(SERVE), "--hq", cls.hq, "--actor", A,
                                    "--key", record.find_key(None, A, cls.kd), "--port", str(cls.port)],
                                   stdout=cls.log, stderr=cls.log, env=env, cwd=cls.tmp)
        for _ in range(100):
            try:
                cls.get("/strings.json")
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
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def get(cls, path):
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (cls.port, path), headers={"Host": "127.0.0.1:%d" % cls.port})
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, ""

    def test_the_view_and_its_stylesheet_are_served(self):
        s, body = self.get("/sightings.js")
        self.assertEqual(s, 200)
        self.assertEqual(body, VIEW.read_text(encoding="utf-8"))
        self.assertIn("export default function", body)
        s, body = self.get("/sightings.css")
        self.assertEqual((s, body), (200, CSS.read_text(encoding="utf-8")))

    def test_it_is_registered_as_the_wall_is(self):
        s, shell = self.get("/shell.js")
        self.assertEqual(s, 200)
        self.assertIn('sightings: "./sightings.js" };', shell)          # PLUGINS, at the end
        self.assertIn('bodies: "bodies", sightings: "sightings" };', shell)   # ROUTE_VIEWS, at the end
        self.assertIn('["record", "#/record"], ["sightings", "#/sightings"]];', shell)   # MORE_PLACES, at the end
        for wall in ('wall: "./wall.js"', 'wall: "wall"', '["wall", "#/wall"]'):
            self.assertIn(wall, shell)                                  # nothing else moved

    def test_every_word_it_asks_for_is_served(self):
        s, raw = self.get("/strings.json")
        self.assertEqual(s, 200)
        words = json.loads(raw)
        for k in ("places.sightings", "tabs.sightings", "view.sightings", "smap.map.title", "smap.ag.title", "smap.hear.title"):
            self.assertIn(k, words)
        src = _source(VIEW)
        for k in re.findall(r'\bt\(\s*"([^"]+)"', src):
            self.assertIn(k, words, k)
        for p in re.findall(r'\bword\(\s*"([^"]+\.)"', src):
            self.assertTrue(any(k.startswith(p) for k in words), p)
        for k in sightings.NINE:
            self.assertIn("sight.kind." + k, words)
        for k in sightings.PRECEDENCE:
            self.assertIn("smap.life." + k, words)


class TheViewsWords(unittest.TestCase):
    def test_no_words_in_code(self):
        keys = set(_strings())
        classes = _css_classes()
        bad = []
        for lit in sorted(set(_literals(_source(VIEW)))):
            if len(lit) <= 3 or lit in keys or lit in DOM_WORDS:
                continue
            if lit.endswith(".") and any(k.startswith(lit) for k in keys):
                continue
            if all(tok in classes for tok in lit.split()):
                continue
            bad.append(lit)
        self.assertEqual(bad, [])

    def test_it_only_reads(self):
        src = _source(VIEW)
        for never in ("ctx.act", "fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "Audio", ".play(",
                      "speechSynthesis", "<script", "http://", "https://", "ctx.say", "ctx.mail", "openPublish"):
            self.assertNotIn(never, src, never)

    def test_no_person_is_named(self):
        src = _source(VIEW)
        # the view never reads who proposed, agreed, sighted or committed; it names holons and kinds only
        for field in ("proposer", "agreed_by", "actor", "committee", "scoreboard", "set_by", "accepted_by", "resighted_by"):
            self.assertIsNone(re.search(r"\.%s\b" % field, src), field)
        words = " ".join(v for k, v in _strings().items() if k.startswith("smap.") and isinstance(v, str))
        self.assertIsNone(re.search(r"person:|agent:", words))

    def test_the_model_reads_the_state(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        st = {"map": {"kinds": list(sightings.NINE), "by_kind": {"pain": 1, "odd": 1, "defect": 2},
                      "by_place": {"the gate": {"pain": [{"id": "b", "kind": "pain", "weight": 1, "open": True}],
                                                "odd": [{"id": "c", "weight": 1, "open": False}]},
                                   "the hall": {"defect": [{"id": "d", "weight": 2, "open": True},
                                                           {"id": "e", "weight": 1, "open": True}]},
                                   "nowhere": {"defect": []}},
                      "open": 3, "pains_open": 1, "as_of": {"newest": NOW}}}
        js = ("import(%s).then((m) => { const a = m.mapModel(%s), b = m.mapModel(null), c = m.mapModel({map: 3});"
              " console.log(JSON.stringify([a, b, c])); });") % (json.dumps(VIEW.as_uri()), json.dumps(st))
        out = subprocess.run([node, "--input-type=module", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        a, b, c = json.loads(out.stdout)
        self.assertEqual(a["columns"], list(sightings.NINE) + ["odd"])
        self.assertEqual([p["place"] for p in a["places"]], ["the hall", "the gate"])   # heaviest first; an empty place is not drawn
        self.assertEqual((a["places"][0]["cells"]["defect"]["n"], a["places"][0]["cells"]["defect"]["weight"]), (2, 3))
        self.assertTrue(a["places"][1]["cells"]["pain"]["pain"])
        self.assertFalse(a["places"][1]["cells"]["odd"]["pain"])
        self.assertEqual((a["open"], a["pains"], a["asOf"]), (3, 1, NOW))
        for e in (b, c):
            self.assertEqual((e["columns"], e["places"], e["open"], e["pains"], e["asOf"]), ([], [], 0, 0, None))



# A DOM just large enough for card.js's h() and the view; the view is drawn to its text.
STUB_DOM = """
class N { constructor(tag) { this.tag = tag; this.kids = []; this.attrs = {}; this.dataset = {}; this.className = ""; this.on = {}; }
  append(...k) { for (const x of k) { if (x === null || x === undefined) throw new Error("appended " + x); this.kids.push(x); } }
  setAttribute(k, v) { this.attrs[k] = v; } addEventListener(e, f) { this.on[e] = f; }
  set textContent(v) { this.kids = v ? [new T(v)] : []; }
  get text() { return [...Object.values(this.attrs).filter((v) => typeof v === "string"), ...this.kids.map((k) => k.text)].join(" "); } }
class T { constructor(s) { this.s = String(s); } get text() { return this.s; } }
globalThis.Node = N;
globalThis.document = { createElement: (t) => new N(t), createTextNode: (s) => new T(s), querySelector: () => ({}), head: { append() {} } };
const [view, state, words] = JSON.parse(process.argv[1]);
const t = (k, v) => { let s = words[k]; if (s == null) return "[" + k + "]"; if (v) s = s.replace(/\\{(\\w+)\\}/g, (m, x) => (v[x] == null ? m : String(v[x]))); return s; };
const m = await import(view);
const find = (n, f, out = []) => { if (n instanceof N) { if (f(n)) out.push(n); n.kids.forEach((k) => find(k, f, out)); } return out; };
const draw = (st, slot) => {
  const el = new N("section"), v = m.default();
  v.mount(el, { state: st, t, slot, density: "full", read: { holonName: (s, id) => (((s && s.holons) || []).find((x) => x.id === id) || {}).name || "" },
    fmt: { number: (n) => String(n), short: (id) => String(id).slice(0, 4), by: (x) => String(x), asOf: (x) => String(x) } });
  const b = find(el, (n) => n.tag === "button")[0];
  if (b) b.on.click();
  const opened = el.text;
  if (b) find(el, (n) => n.tag === "button")[0].on.click();
  v.unmount();
  return [opened, el.text];
};
console.log(JSON.stringify({ full: draw(state, "full"), aside: draw(state, "aside"), empty: draw({}, "full"), odd: draw({ map: [], agreements: { rows: [null, 1] }, subscriptions: { rows: "x", due: 5 } }, "full") }));
"""


class TheViewDrawn(unittest.TestCase):
    """The view drawn in a stub DOM over the fixture's state: every panel, no missing word, a tap opens a cell."""

    def test_drawn(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        src = ENGINE / "fixtures" / "hq"
        if not src.is_dir():
            self.skipTest("no fixtures/hq beside the engine")
        tmp = tempfile.mkdtemp(prefix="views-drawn-")
        try:
            hq = os.path.join(tmp, "hq")
            shutil.copytree(src, hq, symlinks=True)
            st = json.loads(json.dumps(engine.build_state(hq, now=NOW), default=str))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(st["map"]["pains_open"], 1)
        self.assertIn(st["map"]["no_kind"], st["map"]["by_kind"])       # the fixture has a sighting with no kind
        note = "An engine sentence that is never shown."
        for r in st["agreements"]["rows"]:
            r["notes"] = [note]
        arg = json.dumps([VIEW.as_uri(), st, _strings()])
        out = subprocess.run([node, "--input-type=module", "-e", STUB_DOM, arg], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        r = json.loads(out.stdout)
        w = _strings()
        opened, closed = r["full"]
        for k in ("smap.map.title", "smap.ag.title", "smap.hear.title"):
            self.assertIn(w[k], opened)
        for text in (opened, closed, *r["aside"], *r["empty"], *r["odd"]):
            self.assertIsNone(re.search(r"\[(smap|sight|places|view)\.", text), text[:200])
        some = next(rs for kinds in st["map"]["by_place"].values() for rs in kinds.values() if rs)
        self.assertIn(some[0]["text"], opened)           # the tap listed the cell's sightings with their paper line
        self.assertNotIn(some[0]["text"], closed)        # and the same tap closed it
        self.assertIn(w["smap.see_all"], r["aside"][0])
        for k in ("smap.map.empty", "smap.ag.empty", "smap.hear.empty"):
            self.assertIn(w[k], r["empty"][0])
            self.assertIn(w[k], r["odd"][0])
        for actor in ("person:", "agent:"):
            self.assertNotIn(actor, opened)              # no person or agent named in the view
        self.assertIn(w["smap.no_kind"], opened)          # the engine's "(no kind)" is said in words
        for raw in (st["map"]["no_kind"], st["map"]["no_place"], note, st["map"]["as_of"]["newest"]):
            self.assertNotIn(raw, opened)                # nor raw, nor its sentences; "as of" is the shell's alone
        self.assertIn(w["smap.map.totals_one_pain"].replace("{open}", str(st["map"]["open"])), opened)
        self.assertIn(w["smap.ag.live"], opened)

    def test_the_place_column_keeps_its_words_whole(self):
        css = CSS.read_text(encoding="utf-8")
        rule = re.search(r"\.smap-table \.smap-place \{([^}]*)\}", css).group(1)
        self.assertNotIn("anywhere", rule)
        self.assertIn("min-width", rule)


if __name__ == "__main__":
    unittest.main()
