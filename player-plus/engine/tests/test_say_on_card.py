"""Say it on the card (O1): the full card (hud/card-full.js) lets a person make a note on a card or ask on it.
One text box, two buttons, each a `say` anchored to the card through the shell's one act path (hud/shell.js
sayOnCard); every act says what it does, on hover and in a fold; Ask is not offered to the holder; the say
shows in the card's story once a new state is served, with whose words it is; a card that is finished or
taken back allows no act, and the acts go when a new state says so; the box empties only when the act is
written. Its own module: every card's tests live in their own file."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
HUD = ENGINE.parent / "hud"
FULL_CARD = HUD / "card-full.js"
SHELL = HUD / "shell.js"
A, B = "person:alice", "person:bob"

# Data tokens the edited code compares against the record and never shows (types.json `say` voice, the
# card's states, the pending act's statuses, the actor prefixes, a line's reason), and the DOM's and the
# language's words.
SAY_DATA = {"human-words", "agent-drafted", "agent", "under-mandate", "retracted", "ready", "open", "taken",
            "written", "kept-here", "person:", "agent:", "human", "textarea", "button", "aria-label", "object",
            "string", "function", "NFC", "details", "summary", "div", "ul", "li", "say", "ask", "did"}


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


def _region(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i)]


# A DOM just large enough for card.js's h() and the full card, with the browser globals state.js reads at
# load; the words come from strings.json through state.js's own t(). Each scenario draws the full card with
# its acts stubbed, presses what it names, and serves new states through the store (as the stream does).
CARD_DOM = """
class N { constructor(tag) { this.tag = tag; this.kids = []; this.attrs = {}; this.dataset = {}; this.className = ""; this.on = {}; this.value = ""; this.parent = null; }
  append(...k) { for (const x of k) { if (x === null || x === undefined) throw new Error("appended " + x); if (x instanceof N) x.parent = this; this.kids.push(x); } }
  before(x) { const p = this.parent; if (!p) return; x.parent = p; p.kids.splice(p.kids.indexOf(this), 0, x); }
  remove() { const p = this.parent; if (p) p.kids = p.kids.filter((k) => k !== this); this.parent = null; }
  get childNodes() { return this.kids; }
  setAttribute(k, v) { this.attrs[k] = v; } addEventListener(e, f) { this.on[e] = f; } focus() { this.focused = (this.focused || 0) + 1; }
  set textContent(v) { this.kids = v ? [new T(v)] : []; }
  get text() { return [...Object.values(this.attrs).filter((v) => typeof v === "string"), ...this.kids.map((k) => k.text)].join(" "); } }
class T { constructor(s) { this.s = String(s); } get text() { return this.s; } }
globalThis.Node = N;
globalThis.location = { search: "", hostname: "127.0.0.1", hash: "", href: "http://127.0.0.1/" };
const mem = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
globalThis.localStorage = mem(); globalThis.sessionStorage = mem();
globalThis.document = { createElement: (t) => new N(t), createTextNode: (s) => new T(s), querySelector: () => ({}), head: { append() {} }, documentElement: { dataset: {} } };
const [hud, words, lines, ME] = JSON.parse(process.argv[1]);
globalThis.fetch = async () => ({ ok: true, json: async () => words });
const S = await import(hud + "/state.js");
await S.loadStrings();
const m = await import(hud + "/card-full.js");
const tick = () => new Promise((r) => setTimeout(r, 5));
const find = (n, f, out = []) => { if (n instanceof N) { if (f(n)) out.push(n); n.kids.forEach((k) => find(k, f, out)); } return out; };
const said = (n) => n.kids.map((k) => k.text).join(" ");
const card = (id, state, extra) => ({ id, title: "A card", holon: "holon:cell", state, holder: "person:bob", lines: [], ...extra });
const base = () => ({ actor: ME, holons: [{ id: "holon:cell", name: "The cell" }], actors: [{ id: "agent:a", for: ME }],
  cards: [card("card:open", "open"), card("card:done", "done"), card("card:did", "taken", { stage: "did" }), card("card:gone", "retracted"),
          card("card:mine", "open", { holder: ME })] });
const draw = (st, id, acts) => m.renderFullCard({ state: st, t: S.t, fmt: S.fmt, read: S.read, openCard() {}, act() {} }, id, { acts });
let served = 0;
const serve = async (st) => { S.store.raw = { served: ++served }; S.store.state = st; S.setPref("type", "regular"); await tick(); };   // the store emits, as on the stream
const look = (f) => ({ boxes: find(f.el, (n) => n.tag === "textarea").length, folds: find(f.el, (n) => n.tag === "details").map((n) => n.text),
  buttons: find(f.el, (n) => n.tag === "button").map((b) => [said(b), b.attrs.title || null]) });
const press = (f, w) => find(f.el, (n) => n.tag === "button" && said(n) === w)[0].on.click();
const box = (f) => find(f.el, (n) => n.tag === "textarea")[0];
const out = {};
{
  const got = [];
  const f = draw(base(), "card:open", { claim() {}, done() {}, say: (c, l) => { got.push(["say", c.id, l]); }, ask: (c, l) => { got.push(["ask", c.id, l]); } });
  await f.load();
  out.main = { ...look(f), placeholder: box(f).attrs.placeholder, first: f.el.text };
  press(f, S.t("card.say")); out.main.emptyFocused = !!box(f).focused; out.main.emptyGot = got.length;
  box(f).value = "  A note on the plan  "; press(f, S.t("card.say")); out.main.cleared = box(f).value;
  box(f).value = "Who holds the budget?"; press(f, S.t("card.ask"));
  out.main.got = got;
  const st2 = base(); st2.lines = lines;
  await serve(st2);
  out.main.story = f.el.text; out.main.open2 = look(f);
  const st3 = base(); st3.lines = lines; st3.cards[0].state = "done";
  await serve(st3);
  out.main.over = look(f);
}
out.closed = {};
for (const id of ["card:done", "card:did", "card:gone"]) out.closed[id] = look(draw(base(), id, { claim() {}, done() {}, say() {}, ask() {} }));
out.mine = look(draw(base(), "card:mine", { claim() {}, done() {}, say() {}, ask() {} }));
{
  const got = [];
  const f = draw(base(), "card:open", { ask: (...a) => got.push(a.length) });
  press(f, S.t("card.ask"));
  out.old = { ...look(f), got };
}
{
  // the box empties only when the act is written: undone keeps the words, written empties it, a tap while one is held writes nothing
  let next = null, calls = 0;
  const f = draw(base(), "card:open", { say: () => { calls++; return next; } });
  const r = {};
  next = { done: Promise.resolve({ status: "undone" }) }; box(f).value = "Kept back"; press(f, S.t("card.say")); await tick(); r.undone = box(f).value;
  next = { done: Promise.resolve({ status: "refused" }) }; press(f, S.t("card.say")); await tick(); r.refused = box(f).value;
  next = { done: Promise.resolve({ status: "written" }) }; press(f, S.t("card.say")); await tick(); r.written = box(f).value;
  next = { done: new Promise(() => {}) }; box(f).value = "Held"; press(f, S.t("card.say")); press(f, S.t("card.say")); await tick(); r.held = box(f).value;
  r.calls = calls;
  out.undo = r;
}
out.lines = [m.sayLine({ id: "card:x" }, "Cafe\\u0301", null), m.sayLine({ id: "card:x" }, "Why?", "ask"), m.sayLine(null, "x"),
  m.sayLine({ id: "card:x" }, "   "), m.sayLine({ id: 3 }, "x"), m.sayLine({ id: "card:x" }, 7), m.sayLine({ id: "card:x" }, "x", "thank")];
console.log(JSON.stringify(out));
"""


class SayItOnTheCard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("no node on this machine")
        T0 = "2026-10-31T09:0%d:00-07:00"
        at = {"anchored_to": ["card:open"]}
        lines = [
            {"id": "l1", "type": "say", "actor": A, "ts": T0 % 1, "links": at, "body": {"text": "A note on the plan"}},
            {"id": "l2", "type": "say", "actor": A, "ts": T0 % 2, "links": at, "body": {"text": "Who holds the budget?", "intent": "ask", "voice": "human-words"}},
            {"id": "l3", "type": "say", "actor": "agent:a", "ts": T0 % 3, "links": at, "signed_for": True, "body": {"text": "A draft from the agent", "voice": "agent-drafted"}},
            {"id": "l4", "type": "say", "actor": B, "ts": T0 % 4, "links": at, "body": {"text": "Words from the holder", "voice": "human-words"}},
            {"id": "l5", "type": "say", "actor": "agent:a", "ts": T0 % 5, "links": at, "body": {"text": "The agent on its own"}},
            {"id": "l6", "type": "claim", "actor": A, "ts": T0 % 6, "body": {"card": "card:open"}},
            {"id": "l7", "type": "say", "actor": "agent:a", "ts": T0 % 7, "links": at, "body": {"text": "A draft no one signed", "voice": "agent-drafted"}},
        ]
        arg = json.dumps([HUD.as_uri(), _strings(), lines, A])
        out = subprocess.run([node, "--input-type=module", "-e", CARD_DOM, arg], capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            raise AssertionError(out.stderr)
        cls.r, cls.w = json.loads(out.stdout), _strings()

    def labels(self, look):
        return [b[0] for b in look["buttons"]]

    def test_two_acts_one_box(self):
        r, w = self.r["main"], self.w
        self.assertEqual((r["boxes"], r["placeholder"]), (1, w["card.say_placeholder"]))
        self.assertTrue(r["emptyFocused"])                 # no words: nothing written, the box asks for them
        self.assertEqual(r["emptyGot"], 0)
        self.assertEqual(r["cleared"], "")                 # a caller with no pending act: nothing to wait on
        link = {"anchored_to": ["card:open"]}
        self.assertEqual(r["got"], [
            ["say", "card:open", {"type": "say", "body": {"text": "A note on the plan", "voice": "human-words"}, "links": link}],
            ["ask", "card:open", {"type": "say", "body": {"text": "Who holds the budget?", "voice": "human-words", "intent": "ask"}, "links": link}]])

    def test_every_act_says_what_it_does(self):
        r, w = self.r["main"], self.w
        means = {"card.claim": "card.claim_means", "card.say": "card.say_means", "card.ask": "card.say_ask_means"}
        self.assertEqual(r["buttons"][:3], [[w[k], w[v]] for k, v in means.items()])   # the hover title on each
        self.assertEqual(len(r["folds"]), 1)
        self.assertIn(w["card.say_fold_title"], r["folds"][0])
        for k, v in means.items():
            self.assertIn(w["card.say_fold_line"].replace("{act}", w[k]).replace("{means}", w[v]), r["folds"][0])
        self.assertIn("cell", w["card.say_means"])                                        # who reads it, named
        mine = self.r["mine"]
        self.assertIn([w["card.done"], w["card.done_means"]], mine["buttons"])
        self.assertIn(w["card.say_fold_line"].replace("{act}", w["card.done"]).replace("{means}", w["card.done_means"]), mine["folds"][0])

    def test_ask_is_not_offered_to_the_holder(self):
        labels = self.labels(self.r["mine"])
        self.assertIn(self.w["card.say"], labels)
        self.assertIn(self.w["card.done"], labels)
        self.assertNotIn(self.w["card.ask"], labels)
        self.assertNotIn(self.w["card.claim"], labels)

    def test_none_on_a_finished_card(self):
        for id_, d in self.r["closed"].items():
            self.assertEqual((d["boxes"], d["folds"], d["buttons"] and [b for b in self.labels(d) if b in (self.w["card.say"], self.w["card.ask"], self.w["card.claim"], self.w["card.done"])]),
                             (0, [], []), id_)

    def test_the_acts_go_when_the_card_is_over(self):
        r, w = self.r["main"], self.w
        self.assertEqual(r["open2"]["boxes"], 1)            # a new state with the card still open keeps them
        over = r["over"]
        self.assertEqual((over["boxes"], over["folds"]), (0, []))
        for k in ("card.say", "card.ask", "card.claim"):
            self.assertNotIn(w[k], self.labels(over), k)

    def test_an_older_caller_still_asks(self):
        o, w = self.r["old"], self.w
        self.assertEqual((o["boxes"], o["got"]), (0, [1]))  # Ask alone: the shell's own sheet, as before
        self.assertEqual(o["buttons"][0], [w["card.ask"], w["card.say_ask_means"]])
        self.assertEqual(len(o["folds"]), 1)                # the fold beside any row of acts

    def test_the_box_empties_only_when_written(self):
        u = self.r["undo"]
        self.assertEqual((u["undone"], u["refused"], u["written"], u["held"], u["calls"]), ("Kept back", "Kept back", "", "Held", 4))

    def test_the_line(self):
        x = {"anchored_to": ["card:x"]}
        hw = "human-words"
        self.assertEqual(self.r["lines"], [
            {"type": "say", "body": {"text": "Café", "voice": hw}, "links": x},
            {"type": "say", "body": {"text": "Why?", "voice": hw, "intent": "ask"}, "links": x},
            None, None, None, None,
            {"type": "say", "body": {"text": "x", "voice": hw}, "links": x}])

    def test_the_story_says_whose_words(self):
        s, w = self.r["main"]["story"], self.w
        self.assertIn(w["card.full.did.say"].replace("{text}", "A note on the plan"), s)
        self.assertIn(w["card.full.did.ask"].replace("{text}", "Who holds the budget?"), s)
        count = lambda k: s.count(" · " + w[k])
        self.assertEqual(count("card.full.did.voice_mine_human"), 2)       # l1 with no voice reads as the fold reads it
        self.assertEqual(count("card.full.did.voice_mine_drafted"), 1)     # l3, signed at the person's word
        self.assertEqual(count("card.full.did.voice_theirs_human"), 1)
        self.assertEqual(count("card.full.did.voice_mine_agent"), 2)       # l5, and l7's unsupported claim
        self.assertEqual(sum(s.count(" · " + v) for k, v in w.items() if k.startswith("card.full.did.voice_")), 6)   # the claim reads none
        self.assertIsNone(re.search(r"\[(card|app|record)\.", s), s[:300])
        for raw in ("human-words", "agent-drafted", "person:", "agent:"):
            self.assertNotIn(raw, s)

    def test_no_words_in_code(self):
        keys, classes = set(_strings()), _css_classes()
        full, shell = _source(FULL_CARD), _source(SHELL)
        parts = [_region(full, "const VOICE_KEYS", "function section("), _region(full, "const actEls", "root.append(face);"),
                 _region(full, "let heard = []", "return { el: root"), _region(shell, "function sayOnCard(", "function openPublish(")]
        bad = []
        for lit in sorted({x for p in parts for x in _literals(p)}):
            if lit in keys or lit in SAY_DATA or (lit and all(tok in classes for tok in lit.split())) or re.fullmatch(r"\d*", lit):
                continue
            bad.append(lit)
        self.assertEqual(bad, [])
        for p in parts:
            for k in re.findall(r'\bt\(\s*"([^"]+)"', p) + [k for pair in re.findall(r'pill\("[^"]+", "([^"]+)", "([^"]+)"', p) for k in pair]:
                self.assertIn(k, keys, k)
        for k in [k for k in keys if k.startswith("card.say") or k.startswith("card.full.did.") or k in ("card.claim_means", "card.done_means")]:
            self.assertIsNone(re.search(r"\b[A-Za-z]+n't\b|person:|agent:", self.w[k]), k)

    def test_the_shell_writes_the_line_as_given(self):
        shell = _source(SHELL)
        say = _region(shell, "function sayOnCard(", "function askOnCard(")
        self.assertIn("return act(line.type, line.body, line.links, c.holon, { confirmed: true", say)
        ask = _region(shell, "function askOnCard(", "function openPublish(")
        self.assertEqual(ask.count('intent: "ask"'), 2)                 # the full card's line and the sheet's own
        self.assertIn("say: (c, line) => sayOnCard(c, line)", shell)
        self.assertIn("ask: (c, line) => askOnCard(c, line)", shell)


if __name__ == "__main__":
    unittest.main()
