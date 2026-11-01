"""The Hand in the session (4.0 B2): a dealt card answered by the person's word in the session makes the line the HUD
makes for the same choice (its type, body and links), and it is never a line whose actor is the person (the-record,
rule 8). The skill's command is

    python3 -I engine/acts.py line ITEMS ID PERSON KEY --agent AGENT --consent WORDS [--text] [--why] [--option]

An act of a human_only type prints its draft for the person's own hand (the HUD, or their own append); any other act
prints the agent's own line, for the person, with their yes to the read-back in body.consent, and the `record.py
append` command from the holon's folder on. The fixtures are the HUD proof's (tests/test_one_card.py: items, HOLONS,
served_state), with its expectations; where node is on this machine, hud/act-map.js's actFor runs on the same dealt
cards and each line is compared field for field. The body fields that say whose words a line carries (`consent`, and
the `voice` a person's own say is marked with) are the writer's, so the comparison sets them aside.

The laws: (1) the session's line and the HUD's line are the same in type, body and links; (2) an act the reader may
not make prints a refusal with the rule's why, never a line; (3) an act that needs words, or the yes, given none,
prints what is needed and no line; (4) no printed line has a person as its actor; (5) the words are plain, with no
contractions. Its own module.

    python3 -I -m unittest discover -t . -s tests -p test_hand_in_session.py -v
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
HUD = ENGINE.parent / "hud"
KIT = ENGINE.parent
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

import acts  # noqa: E402
from tests import test_one_card as one  # noqa: E402  (its fixtures and the HUD's expectations; never its tests)

P, K, NOW, A, B = one.P, one.K, one.NOW, one.A, one.B
AG = "agent:helper"
YES = "Yes, write it"
WORDS = "My own words"                      # test_one_card's HARNESS: the words the person gives
WHOSE = ("consent", "voice")                # whose words a line carries: the writer's, set aside in the comparison
# What hud/act-map.js writes for these, as tests/test_one_card.py asserts it (each named by its test there),
# with (id, key, text, why, option, whose hand: "agent" for the agent's own line, "theirs" for a human_only act).
HUD_WRITES = [
    ("r1", "act.answer.accept", None, None, None, "theirs",
     {"type": "answer", "body": {"answer": "accept"}, "links": {"answers": ["r1"]}}),
    ("r1", "act.answer.decline", None, None, None, "theirs",
     {"type": "answer", "body": {"answer": "decline"}, "links": {"answers": ["r1"]}}),
    ("r1", "act.say", WORDS, None, "Offer something else", "agent",
     {"type": "say", "body": {"text": WORDS, "voice": "human-words"}, "links": {"anchored_to": ["r1"]}}),
    ("c-mine", "act.release", None, WORDS, None, "agent",
     {"type": "release", "body": {"commitment": "c-mine", "why": WORDS}, "links": {}}),
    ("d1", "act.ratify", None, None, None, "theirs", {"type": "ratify", "body": {}, "links": {"answers": ["d1"]}}),
    ("t1", "act.settle", None, None, None, "theirs",
     {"type": "settle", "body": {"text": "Where we meet"}, "links": {"anchored_to": ["t1"]}}),
    ("c-mine", "act.kept", None, None, None, "theirs", {"type": "kept", "body": {"commitment": "c-mine"}, "links": {}}),
]
OWN_WORDS = {"id": "c-mine", "kind": "commitment", "section": "owed", "holon": A, "question": "Is it on track?",
             "options": ["On track", "Renegotiate now, while there is float", "Release it"], "recommendation": "On track"}
UNTITLED = {"id": "t2", "kind": "thread", "section": "thread", "holon": B, "question": "Close this conversation?",
            "options": ["Reply now", "Settle it as it stands", "Hand it to someone else"],
            "recommendation": "Settle it as it stands"}

ACT_MAP = r"""
const [hud, ST, CARDS] = JSON.parse(process.argv[1]);
globalThis.document = { createElement: () => ({}), createTextNode: () => ({}) };
globalThis.localStorage = globalThis.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.location = { search: "", hostname: "127.0.0.1", hash: "" };
const map = await import(hud + "/act-map.js");
const out = {};
for (const dc of CARDS) {
  out[dc.id + "|" + dc.options.join("|")] = (dc.offers.options || []).map((o, i) => map.actFor(dc, i, o.needs_words ? "My own words" : null, ST));
}
console.log(JSON.stringify(out));
"""


def _items(tmp):
    """test_one_card's items, an untitled thread beside its thread, and the holons with their folders."""
    d = one.items()
    t2 = dict(d["threads"][0], id="t2")
    t2.pop("title", None)
    d["threads"].append(t2)
    d["holons"] = [dict(h, dir=str(Path(tmp) / h["id"])) for h in one.HOLONS]
    return d


def _session(items_path, iid, person, key, text=None, why=None, option=None, agent=AG, consent=YES):
    """The skill's command, exactly."""
    cmd = [sys.executable, "-I", str(ENGINE / "acts.py"), "line", str(items_path), iid, person, key]
    for flag, v in (("--agent", agent), ("--consent", consent), ("--text", text), ("--why", why), ("--option", option)):
        if v is not None:
            cmd += [flag, v]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return out.returncode, json.loads(out.stdout) if out.stdout.strip() else None, out.stderr


def _three(line):
    """type, body and links, with the fields that say whose words they are set aside."""
    if not isinstance(line, dict):
        return None
    return {"type": line["type"], "body": {k: v for k, v in line["body"].items() if k not in WHOSE}, "links": line["links"]}


def _made(r):
    return r.get("line") or r.get("draft")


def _offered_card(card, folded):
    from gamecore import normalize
    import deal as deal_mod
    item = next(x for xs in folded.values() if isinstance(xs, list) for x in xs if isinstance(x, dict) and x.get("id") == card["id"])
    o = acts.offered(item, P, folded=deal_mod.acts_context(normalize(folded), one.HOLONS), now=NOW, card=card)
    o["options"] = acts.options_for(card, o)
    return json.loads(json.dumps(dict(card, offers=o)))


class TheHandInTheSession(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folded = _items(cls.tmp.name)
        cls.items = Path(cls.tmp.name) / "items.json"
        cls.items.write_text(json.dumps(cls.folded), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # law 1 ------------------------------------------------------------------------------------------------

    def test_the_request_writes_the_huds_line(self):
        for iid, key, text, why, option, hand, want in HUD_WRITES:
            code, r, err = _session(self.items, iid, P, key, text, why, option)
            self.assertEqual(code, 0 if hand == "agent" else 1, (iid, key, err, r))
            self.assertEqual(_three(_made(r)), _three(want), (iid, key))       # type, body, links: field for field
            if hand == "agent":
                self.assertEqual((r["line"]["actor"], r["line"]["for"]), (AG, P))   # the agent's own line, for them
                self.assertEqual(r["line"]["body"]["consent"], YES)           # their yes to the read-back, on the line
                self.assertNotIn("voice", r["line"]["body"])                   # the fold computes whose words it is
            else:
                self.assertIsNone(r["line"])                                   # their own act: their own hand
                self.assertEqual(r["theirs"], acts.LINE_THEIRS)
                self.assertNotIn("actor", r["draft"])

    def test_the_append_writes_the_agents_line_in_the_holons_folder(self):
        code, r, _ = _session(self.items, "r1", P, "act.say", WORDS, option="Offer something else")
        self.assertEqual(code, 0)
        tail = r["append"]
        self.assertEqual(tail[0], str(Path(self.tmp.name) / B))               # the request's holon, from the fold
        arg = {tail[i]: tail[i + 1] for i in range(1, len(tail), 2)}
        self.assertEqual(set(arg), {"--actor", "--for", "--type", "--body", "--links", "--reason"})
        self.assertEqual((arg["--actor"], arg["--for"], arg["--type"], arg["--reason"]), (AG, P, "say", "human"))
        self.assertEqual(json.loads(arg["--body"]), r["line"]["body"])
        self.assertEqual(json.loads(arg["--links"]), r["line"]["links"])
        self.assertEqual(r["signed_for"]["consent"], YES)
        self.assertRegex(r["signed_for"]["consent_for"], r"^[0-9a-f]{64}$")   # what their own consent say names
        self.assertTrue(r["label"] and r["meaning"])                          # it says what it does, from acts.json
        bare = acts.line_for(self.folded["cards"][1], P, "act.say", folded={"cards": self.folded["cards"]},
                             agent=AG, consent=YES, text=WORDS)
        self.assertIsNone(bare["append"])                                      # no folder known: no command, said so
        self.assertIn(acts.LINE_NO_DIR, bare["said"])

    def test_an_options_own_words_and_an_untitled_settle(self):
        code, r, _ = _session(self.items, "c-mine", P, "act.say", option="On track")
        self.assertEqual((code, _three(r["line"])), (0, {"type": "say", "body": {"text": "On track"},
                                                         "links": {"anchored_to": ["c-mine"]}}))
        code, r, _ = _session(self.items, "t2", P, "act.settle", option="Settle it as it stands")
        self.assertEqual(_three(r["draft"]), {"type": "settle", "body": {"text": "Settle it as it stands"},
                                              "links": {"anchored_to": ["t2"]}})
        code, r, _ = _session(self.items, "r1", P, "act.say", option="Offer something else")
        self.assertEqual(r["needs"], ["body.text"])                            # this option opens a reply: their words

    def test_the_same_line_as_the_act_map_runs(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        st = one.served_state()
        cards = [c for c in st["deal"]["cards"] if c["id"] in ("r1", "c-mine", "d1", "t1")]
        self.assertEqual(sorted(c["id"] for c in cards), ["c-mine", "d1", "r1", "t1"])
        cards += [_offered_card(OWN_WORDS, self.folded), _offered_card(UNTITLED, self.folded)]
        out = subprocess.run([node, "--input-type=module", "-e", ACT_MAP, json.dumps([HUD.as_uri(), st, cards])],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        hud = json.loads(out.stdout)
        compared = set()
        for dc in cards:
            drawn = hud[dc["id"] + "|" + "|".join(dc["options"])]
            for i, row in enumerate(dc["offers"]["options"]):
                if not row["offered"] or not row["key"]:
                    self.assertIsNone(drawn[i], (dc["id"], row["option"]))    # it writes nothing, in either place
                    continue
                text = WORDS if row["fills"] == "body.text" else None
                why = WORDS if row["fills"] == "body.why" else None
                code, r, err = _session(self.items, dc["id"], P, row["key"], text, why, row["option"])
                self.assertIn(code, (0, 1), err)
                self.assertEqual(_three(_made(r)), _three(drawn[i]), (dc["id"], row["option"], r))
                compared.add((dc["id"], row["option"]))
        self.assertGreaterEqual(len(compared), 9)
        self.assertIn(("c-mine", "On track"), compared)
        self.assertIn(("t2", "Settle it as it stands"), compared)

    # law 2 ------------------------------------------------------------------------------------------------

    def test_an_act_not_the_readers_is_refused_with_why(self):
        o = acts.offered(self.folded["cards"][1], P, folded=self.folded, now=NOW)
        why = next(x["why"] for x in o["why_not"] if x["act"] == "act.request")
        cases = [("r1", P, "act.request", why, AG),                         # the rule's own why
                 ("c-mine", K, "act.kept", None, AG),                         # the committor's act, not the committee's
                 ("r1", "agent:helper", "act.say", acts.WHY["nobody"], AG),   # an agent is not the reader
                 ("r1", P, "act.no_such_act", acts.LINE_NOT_OFFERED, AG),
                 ("no-such-id", P, "act.say", acts.LINE_NO_ITEM, AG),
                 ("r1", P, "act.say", acts.LINE_NO_AGENT, P),                 # a person is not the agent that writes
                 ("r1", P, "act.say", acts.LINE_NO_AGENT, None)]
        for iid, person, key, want, agent in cases:
            code, r, _ = _session(self.items, iid, person, key, WORDS, WORDS, agent=agent)
            self.assertEqual(code, 1, (iid, key, r))
            self.assertIsNone(r["line"], (iid, key))
            self.assertNotIn("append", r)
            self.assertTrue(r["refused"], (iid, key))
            if want:
                self.assertEqual(r["refused"], want, (iid, key))

    # law 3 ------------------------------------------------------------------------------------------------

    def test_needs_words_or_the_yes_prints_what_is_needed_and_no_line(self):
        for iid, key, need, text, why, consent in (("r1", "act.say", "body.text", None, None, YES),
                                                   ("r1", "act.say.ask", "body.text", "   ", None, YES),   # blank is none
                                                   ("c-mine", "act.release", "body.why", WORDS, None, YES),
                                                   ("r1", "act.say", "body.consent", WORDS, None, None),
                                                   ("c-mine", "act.release", "body.consent", None, WORDS, " y ")):
            code, r, _ = _session(self.items, iid, P, key, text, why, consent=consent)
            self.assertEqual(code, 1, (iid, key))
            self.assertIsNone(r["line"])
            self.assertNotIn("append", r)
            self.assertEqual(r["needs"], [need], (iid, key))
            self.assertEqual(r["ask"], acts.LINE_NEEDS[need])

    def test_a_line_that_names_what_is_not_known_is_not_written(self):
        code, r, _ = _session(self.items, "d1", P, "act.elevate")      # no wider circle known for the home
        self.assertEqual((code, r["line"], r["needs"]), (1, None, ["body.to"]))
        self.assertIn("whom or where it goes to", r["ask"])

    # law 4 ------------------------------------------------------------------------------------------------

    def test_no_line_is_ever_the_persons(self):
        seen = 0
        for coll in ("cards", "commitments", "threads", "decisions", "sightings"):
            for item in self.folded[coll]:
                for person in (P, K):
                    keys = [a["key"] for a in acts.offered(item, person, folded=self.folded, now=NOW)["acts"]] + ["act.claim"]
                    for key in keys:
                        for agent in (AG, person, None):
                            r = acts.line_for(item, person, key, folded=self.folded, now=NOW, text=WORDS, why=WORDS,
                                              option="On track", agent=agent, consent=YES)
                            blob = json.dumps(r)
                            self.assertNotIn('"actor": "person:', blob, (item["id"], key, agent))
                            line = r.get("line")
                            if line:
                                seen += 1
                                self.assertTrue(line["actor"].startswith("agent:"))
                                self.assertFalse(acts._human_only(line["type"]), line["type"])   # their acts stay theirs
                                self.assertEqual(r["append"][r["append"].index("--actor") + 1], line["actor"])
        self.assertGreater(seen, 10)
        code, out, _ = _session(self.items, "d1", P, "act.ratify")
        self.assertNotIn('"actor": "person:', json.dumps(out))

    # null-guards and determinism ----------------------------------------------------------------------------

    def test_null_guards(self):
        req = self.folded["cards"][1]
        for item, actor, key in ((None, P, "act.say"), ({}, P, "act.say"), ({"id": 5}, P, "act.say"),
                                 (req, None, "act.answer.accept"), (req, P, None), (req, P, 3.5)):
            r = acts.line_for(item, actor, key, folded=self.folded, now=NOW, text=7, why=["x"], agent=AG, consent=YES)
            self.assertIsNone(r["line"], (item, actor, key))
            self.assertTrue(r.get("refused") or r.get("needs"))
        r = acts.line_for(req, P, "act.say", folded=None, agent=AG, consent={"x": 1}, text=WORDS)
        self.assertEqual(r["needs"], ["body.consent"])                       # no fold, no yes: honest, never a crash
        code, out, _ = _session(Path(self.tmp.name) / "missing.json", "r1", P, "act.say", WORDS)
        self.assertEqual((code, out), (2, None))

    def test_words_are_kept_in_nfc_and_the_output_is_deterministic(self):
        nfd = unicodedata.normalize("NFD", "Caf\u00e9 at noon")
        r = acts.line_for(self.folded["cards"][1], P, "act.say", folded=self.folded, now=NOW, text="  " + nfd + " ",
                          agent=AG, consent=nfd)
        self.assertEqual(r["line"]["body"]["text"], "Caf\u00e9 at noon")
        self.assertEqual(r["line"]["body"]["consent"], "Caf\u00e9 at noon")
        a = _session(self.items, "r1", P, "act.say", WORDS)[1]
        b = _session(self.items, "r1", P, "act.say", WORDS)[1]
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    # law 5 ------------------------------------------------------------------------------------------------

    def test_the_words_say_it_plainly(self):
        said = [acts.LINE_NO_ITEM, acts.LINE_NOT_OFFERED, acts.LINE_NO_AGENT, acts.LINE_THEIRS, acts.LINE_UNNAMED,
                acts.LINE_NO_DIR, acts.LINE_COUNTS] + list(acts.LINE_NEEDS.values()) + list(acts.FIELD_WORDS.values())
        deal = (KIT / "skills" / "the-deal" / "SKILL.md").read_text(encoding="utf-8")
        cos = (KIT / "skills" / "the-chief-of-staff" / "SKILL.md").read_text(encoding="utf-8")
        hand = deal.split("## The Hand in the session", 1)
        self.assertEqual(len(hand), 2, "the-deal names its section on the Hand in the session")
        section = hand[1].split("\n## ", 1)[0]
        rule = cos.split("The Hand in the session", 1)
        self.assertEqual(len(rule), 2, "the-chief-of-staff carries the rule")
        rule = rule[1].split("\n\n", 1)[0]
        said += [section, rule]
        contraction = re.compile(r"\b\w+(n't|'re|'ll|'ve|'m|'d)\b|\b(it|that|here|there|what|let|who)'s\b", re.I)
        for s in said:
            self.assertIsNone(contraction.search(s), s[:200])
        for s in (section, rule):
            self.assertNotRegex(s, r"\b(never|only|always)\b")               # knowledge of the Game, not a cage
        self.assertIn("python3 -I engine/acts.py line", section)            # the commands, exact
        self.assertIn("--agent agent:", section)
        self.assertIn("python3 -I engine/record.py append", section)
        self.assertIn("python3 -I engine/record.py fold", section)
        for ln in section.splitlines():
            if "record.py append" in ln or "acts.py line" in ln:
                self.assertNotIn("--actor person:", ln)                      # the session writes no line as the person
        self.assertIn("show me the board", rule)


if __name__ == "__main__":
    unittest.main()
