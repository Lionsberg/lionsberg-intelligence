#!/usr/bin/env python3
"""test_strings.py: the strings gate (DESIGN-THE-BAR §5, lines 9 and 17).

    python3 -I hud/fixtures/test_strings.py

What reaches the screen speaks the person's language: no schema word (event, holon, float,
anchor, settle, engine, hash, process, forge, hook, tokens...) in any string or in the words
the fixtures deal, with "decision" and "milestone" allowed as a person's own words; no
"not computed" placeholder (a fact not computed is absent; the about sheet says why once); no
contraction but the opener. A {placeholder} is a slot, never a word, and is not read.

Keys owned by a view under rebuild are listed in PENDING
with their owner: they are reported, never silently passed, and a key that has become clean
must leave the list (so the list only shrinks). Then the truth proof (test_truth.mjs) runs in
headless muted Chrome when node and Chrome are here, and the Bodies room's proof
(test_bodies_room.mjs) and the full card's proof (test_card_full.mjs) after it. Standard library only; nothing leaves
this machine.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HUD = HERE.parent
SCHEMA = re.compile(r"\b(events?|holons?|float|anchor(s|ed)?|settle[ds]?|settling|engine|schema|hash(es)?|"
                    r"process(es)?|forge|hooks?|tokens?|payload|jsonl?)\b", re.I)
PLACEHOLDER = re.compile(r"\{\w+\}")
CONTRACTION = re.compile(r"\b[A-Za-z]+n't\b|\b(it|that|there|what|who)'s\b|\b(I|you|we|they)'(d|ll|re|ve|m)\b", re.I)
NOT_COMPUTED = re.compile(r"not computed", re.I)

# key prefix -> the builder rebuilding that view; reported, not passed
PENDING_OWNERS = {"map.": "the Map's builder", "dock.": "the dock's builder", "bodies.": "the Bodies rebuild",
                  "ledger.": "the Ledger's builder", "play.": "the Room's builder"}

# the fixtures this script's sibling writes (make_fixtures.py); others' fixtures are theirs
MINE = ["fresh", "empty", "stale", "unreadable", "names-hidden", "large", "invitation", "undealt", "agent-wrote", "deal-chain", "truth", "deal-rich"]
# the room's one shape (make_room_fixtures.py): its dealt words and its proposals' words are read too
SHAPE = ["room-shape-lobby", "room-shape-great", "room-shape-vote", "room-shape-vote-facilitator", "room-shape-writing",
         "room-shape-reflect", "room-shape-close"]


def visible(strings):
    """Every (key, text) a person could see: values of keys not starting with "_"."""
    for k, v in strings.items():
        if k.startswith("_") or "._" in k:
            continue
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str):
                yield k, PLACEHOLDER.sub(" ", x)


def pending(key):
    return next((o for p, o in PENDING_OWNERS.items() if key.startswith(p)), None)


class StringsGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strings = json.loads((HUD / "strings.json").read_text(encoding="utf-8"))

    def hits(self, pattern):
        mine, theirs = [], []
        for k, text in visible(self.strings):
            m = pattern.search(text)
            if m:
                (theirs if pending(k) else mine).append(f"{k}: {m.group(0)!r} in {text.strip()[:70]!r}")
        if theirs:
            print(f"\n  owed by builders under rebuild ({pattern.pattern[:24]}...):\n    " + "\n    ".join(theirs), file=sys.stderr)
        return mine

    def test_no_schema_word_reaches_the_screen(self):
        self.assertEqual(self.hits(SCHEMA), [])

    def test_no_not_computed_placeholder(self):
        self.assertEqual(self.hits(NOT_COMPUTED), [])

    def test_no_contraction_but_the_opener(self):
        bad = [f"{k}: {t!r}" for k, t in visible(self.strings)
               if CONTRACTION.search(t.replace("Here's the deal.", ""))]
        self.assertEqual(bad, [])

    def test_kind_words_only_decision_and_milestone(self):
        shown = {k: v for k, v in self.strings.items() if k.startswith("kind.") and v}
        self.assertEqual(sorted(shown), ["kind.decision", "kind.milestone"])

    def test_every_literal_key_exists(self):
        """No raw key ever reaches the screen (`[tabs.chain]` once did): every
        t("a.b") with a literal key, in every module of the ICE, names a key strings.json holds."""
        lit = re.compile(r'\bt\(\s*"([a-z_]+(?:\.[A-Za-z0-9_]+)+)"\s*[,)]')
        missing = []
        for f in sorted(HUD.glob("*.js")):
            for m in lit.finditer(f.read_text(encoding="utf-8")):
                if m.group(1) not in self.strings:
                    missing.append(f"{f.name}: {m.group(1)}")
        self.assertEqual(missing, [])

    def test_shape_words_in_fixtures(self):
        """The words the one shape puts on the screen from the record: proposals, write-ups, reflections."""
        bad = []
        for name in SHAPE:
            p = HERE / f"{name}.json"
            if not p.exists():
                bad.append(f"{name}.json missing: run make_room_fixtures.py")
                continue
            for room in json.loads(p.read_text(encoding="utf-8")).get("rooms", {}).values():
                sh = room.get("shape") or {}
                words = [x.get("text") for x in sh.get("proposals") or []] + [w.get("title") for w in sh.get("writeups") or []] \
                    + [r.get("text") for r in sh.get("reflections") or []] + [room.get("purpose")]
                for w in filter(None, words):
                    m = SCHEMA.search(w) or NOT_COMPUTED.search(w) or CONTRACTION.search(w)
                    if m:
                        bad.append(f"{name}: {m.group(0)!r} in {w[:70]!r}")
        self.assertEqual(bad, [])

    def test_dealt_words_in_fixtures(self):
        """The words the fixtures deal (questions, options, reasons, briefings, stakes, titles)."""
        bad = []
        for name in MINE:
            p = HERE / f"{name}.json"
            if not p.exists():
                bad.append(f"{name}.json missing: run make_fixtures.py")
                continue
            st = json.loads(p.read_text(encoding="utf-8"))
            d = st.get("deal") or {}
            words = [d.get("briefing"), d.get("greeting")]
            for c in (d.get("cards") or []) + ((d.get("beyond") or {}).get("cards") or []):   # the next hand too
                words += [c.get("question"), c.get("why"), c.get("unlocks"), *(c.get("options") or []), *(c.get("consequences") or [])]
            words += [c.get("title") for c in st.get("cards") or []]
            for w in filter(None, words):
                m = SCHEMA.search(w) or NOT_COMPUTED.search(w)
                if m:
                    bad.append(f"{name}: {m.group(0)!r} in {w[:70]!r}")
        self.assertEqual(bad, [])


class OneTruth(unittest.TestCase):
    """serve.py's fold_own: after an act, the served state carries it for every view."""
    def test_fold_own_marks_one_truth(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("serve_for_test", HUD / "serve.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        st = json.loads((HERE / "deal-chain.json").read_text(encoding="utf-8"))
        day = st["deal"]["cards"][0]["id"]
        title = next(c["title"] for c in st["cards"] if c["id"] == day).lower()
        mod.fold_own(st, [{"type": "decide", "links": {"answers": [day]}, "body": {}}], st["actor"])
        self.assertTrue(st["deal"]["cards"][0].get("answered"))
        self.assertIsNone(st["deal"]["briefing"])           # the opener never names an answered card
        left = [e for e in st["owed"]["entries"] if e["holder"] == st["actor"] and e["status"] != "done"]
        self.assertFalse(any(e["title"].lower() == title for e in left))   # the Map no longer lists it

    def test_waiting_sentences_share_one_list(self):
        """Threads' top sentence and its heading read the same open list; the Map and the Deal read
        the one order of what is owed (state.js), never two fields for one sentence."""
        th = (HUD / "threads.js").read_text(encoding="utf-8")
        self.assertTrue(re.search(r"topSentence\(C, open, theirs", th), "threads: the top sentence must read the open list")
        self.assertTrue(re.search(r'open\.length \? "threads\.head\.mine"', th), "threads: the heading must read the same open list")
        self.assertTrue("read.owedByStake" in (HUD / "map.js").read_text(encoding="utf-8"), "map: must read the one order")
        self.assertTrue("byStakeOrder" in (HUD / "deal.js").read_text(encoding="utf-8"), "deal: must read the one order")


class Truth(unittest.TestCase):
    def test_the_quiet_never_lies(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not here")
        r = subprocess.run([node, str(HERE / "test_truth.mjs")], capture_output=True, text=True, timeout=600)
        print(r.stdout[-2500:], file=sys.stderr)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])



class BodiesRoom(unittest.TestCase):
    def test_the_room(self):
        """The Bodies room (DESIGN-BODIES §13): the prime first and marked, a body chosen fills the
        page, the honest line for a body that cannot be reached, the dock's agent in place."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not here")
        r = subprocess.run([node, str(HERE / "test_bodies_room.mjs")], capture_output=True, text=True, timeout=600)
        print(r.stdout[-1500:], file=sys.stderr)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])

class CardFull(unittest.TestCase):
    def test_the_full_card(self):
        """The full card (card-full.js): opened from the Deal's first card on deal-rich and
        deal-chain it shows the face, where it stands, why it was dealt, its story and its id; no
        schema word and no gold inside; Escape closes it and focus returns; the Chain opens the
        same card with the same sections; the next hand's card opens too."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not here")
        r = subprocess.run([node, str(HERE / "test_card_full.mjs")], capture_output=True, text=True, timeout=600)
        print(r.stdout[-1500:], file=sys.stderr)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])


class TalkPlace(unittest.TestCase):
    def test_the_talk(self):
        """The Talk (DESIGN-TALK.md): Talk · Agents · More at the foot; the first question is the Deal's
        first card; an answer writes the Deal's act and the Deal's count agrees; "next", "who is working
        on what" and a worker by sentence answered here; the rest state; a return in one line with the
        earlier turns folded; the ten-minute offer once; one screen at 390 and 320; the stand-in answers."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not here")
        r = subprocess.run([node, str(HERE / "test_talk_place.mjs")], capture_output=True, text=True, timeout=600)
        print(r.stdout[-1500:], file=sys.stderr)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
