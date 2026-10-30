#!/usr/bin/env python3
"""make_fixtures.py: writes the HUD's sample merged states (DESIGN §8.1, "fixtures first").

Run:  python3 make_fixtures.py      (writes the six JSON files beside this script)

Each file is what serve.py's GET /state returns: a state.json in engine/STATE.md's
shape (v 1), folded over three holons (a person's home, a cell, a room), plus the
server's own `hud` block (sources, layouts, the clock the fixture is set at).

Conditions: fresh · empty · stale (one holon last heard Tuesday) · unreadable
(the room's record could not be read) · names-hidden (the room's posture) ·
large (a layout event asking for large type) · invitation (a one-card Deal for a new
home) · deal-rich (three houses, a full hand of five and seven more ranked
behind it in deal.beyond.cards, so the next hand can be dealt).

Fields here that STATE.md does not yet carry (deal.briefing, deal.greeting,
deal.cards[].consequences) are proposals; a view reads them only where the brief needs them, and shows
"Not computed yet" when they are absent. Other views extend this script
(never hand-edit the JSON) so every fixture stays one truth.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-10-24T09:20:00-07:00"   # a Saturday morning


def hid(*parts):
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


HOME, CELL, ROOM = hid("holon", "home"), hid("holon", "cell-two"), hid("holon", "gathering")
ME, AG = "person:player", "agent:player-agent"
STEWARD, NEIGHBOR, MEMBER = "person:steward", "person:neighbor", "person:member"

C = {k: hid("card", k) for k in ["bread", "gate", "day", "hall", "letters", "chairs", "soup",
                                  "seeds", "visit", "gathering", "minutes"]}
K = {k: hid("commit", k) for k in ["bread", "gate", "letters", "chairs", "visit"]}
D_DAY = hid("decision", "day")
T_SOUP = hid("thread", "soup")


def line_id(holon, n):
    return hid("line", holon, str(n))


def story(holon, rows):
    """A card's story as record lines (engine/SCHEMA.md's event line), for the full card's
    "Its story" (card-full.js reads `cards[].lines`; serve.py's GET /card/<id> reads them in
    fixture mode). Each row: (id or None, ts, actor, type, body, links, signed). A sample: the
    signatures are marks, not keys; an unsigned row is at the paper floor."""
    out, prev = [], {}
    for n, (id_, ts, actor, typ, body, links, signed) in enumerate(rows):
        i = id_ or hid("story", holon, typ, ts, actor, str(n))
        out.append({"v": 1, "id": i, "ts": ts, "actor": actor, "for": actor if actor.startswith("person:") else ME,
                    "holon": holon, "type": typ, "body": body, "links": links or {}, "audience": "holon",
                    "reason": "human" if actor.startswith("person:") else "delegated", "prev": prev.get(actor, ""),
                    "sig": ("ssh-ed25519:" + hid("sig", i)[:43]) if signed else ""})
        prev[actor] = i
    return out


def card(key, holon, title, kind, stream, holder, minutes, by, state, ES, EF, LS, LF, crit=False, sysc=False,
         preds=(), succs=(), stage="will"):
    return {"id": C[key], "holon": holon, "title": title, "kind": kind, "stream": stream, "holder": holder,
            "minutes": minutes, "by": by, "stage": stage, "state": state,
            "predecessors": [C[p] for p in preds], "successors": [C[s] for s in succs], "serves": [],
            "audience": "holon", "ES": ES, "EF": EF, "LS": LS, "LF": LF, "TF": LS - ES, "FF": 0,
            "critical": crit, "system_critical": sysc, "variance_days": None}


def base():
    holons = [
        {"id": HOME, "name": "Home", "kind": "person", "keeper": ME,
         "as_of": {"event": line_id(HOME, 212), "ts": "2026-10-24T09:14:00-07:00", "lines": 212}},
        {"id": CELL, "name": "Cell Two", "kind": "cell", "keeper": STEWARD,
         "as_of": {"event": line_id(CELL, 88), "ts": "2026-10-24T08:40:00-07:00", "lines": 88}},
        {"id": ROOM, "name": "The Gathering", "kind": "room", "keeper": STEWARD,
         "as_of": {"event": line_id(ROOM, 41), "ts": "2026-10-24T09:02:00-07:00", "lines": 41}},
    ]
    cards = [
        card("bread", CELL, "Bring the bread to Saturday's gathering", "activity", "Gathering", ME, 30, "2026-10-31", "open", 2, 3, 5, 6),
        card("gate", HOME, "Fix the garden gate", "activity", "Garden", NEIGHBOR, 60, "2026-10-23", "delivered", 0, 1, 0, 1),
        card("day", CELL, "Choose the meeting day", "decision", "Gathering", ME, 5, "2026-10-27", "open", 0, 1, 0, 1, True, True, succs=["hall"]),
        card("hall", CELL, "Book the hall", "activity", "Gathering", STEWARD, 20, "2026-10-29", "ready", 1, 2, 1, 2, True, False, preds=["day"], succs=["gathering"]),
        card("gathering", CELL, "The autumn gathering", "milestone", "Gathering", STEWARD, 0, "2026-10-31", "ready", 6, 6, 6, 6, True, True, preds=["hall"]),
        card("letters", CELL, "Write to the new members", "activity", "Care", ME, 40, "2026-10-22", "kept", 0, 1, 2, 3, stage="did"),
        card("chairs", CELL, "Set out the chairs", "activity", "Gathering", MEMBER, 15, "2026-10-31", "taken", 5, 6, 5, 6),
        card("seeds", HOME, "Sort the seed packets", "activity", "Garden", ME, 20, "2026-11-02", "ready", 3, 4, 9, 10),
        card("visit", CELL, "Visit the neighbour who is unwell", "activity", "Care", MEMBER, 45, "2026-10-26", "taken", 0, 1, 1, 2),
        card("soup", ROOM, "Bring soup for the circle", "activity", "Room", MEMBER, 30, "2026-10-24", "open", 0, 1, 0, 1),
        card("minutes", ROOM, "Write down what the room decided", "review", "Room", ME, 10, "2026-10-24", "open", 0, 1, 1, 2),
    ]
    commitments = [
        {"id": K["gate"], "holon": HOME, "card": C["gate"], "title": "Fix the garden gate",
         "keeper": NEIGHBOR, "by": "2026-10-23", "size": 60, "witness": ME, "conditions": "", "status": "open", "gap_days": None},
        {"id": K["letters"], "holon": CELL, "card": C["letters"], "title": "Write to the new members",
         "keeper": ME, "by": "2026-10-22", "size": 40, "witness": STEWARD, "conditions": "", "status": "kept", "gap_days": -1},
        {"id": K["chairs"], "holon": CELL, "card": C["chairs"], "title": "Set out the chairs",
         "keeper": MEMBER, "by": "2026-10-31", "size": 15, "witness": ME, "conditions": "", "status": "open", "gap_days": None},
        {"id": K["visit"], "holon": CELL, "card": C["visit"], "title": "Visit the neighbour who is unwell",
         "keeper": MEMBER, "by": "2026-10-26", "size": 45, "witness": STEWARD, "conditions": "", "status": "open", "gap_days": None},
    ]
    deal_cards = [
        {"n": 1, "section": "owed", "id": C["bread"], "holon": CELL, "holon_name": "Cell Two",
         "question": "Will you bring the bread to Saturday's gathering?",
         "options": ["Yes, by Saturday", "Not this week", "Hand it on"],
         "recommendation": "Yes, by Saturday", "why": "You have Friday evening free, and three people are counting on it.",
         "unlocks": "The gathering's table", "kind": "request", "minutes": 5,
         "consequences": ["I will tell Cell Two you will bring the bread by Saturday.",
                          "I will tell Cell Two you cannot bring it this week.",
                          "I will ask Cell Two who else can bring it."], "leverage": 6.2, "whole_waits": False},
        {"n": 2, "section": "owed", "id": C["gate"], "holon": HOME, "holon_name": "Home",
         "question": "Your neighbour said she would fix the gate by Friday. Did she?",
         "options": ["She did", "Not yet", "I will ask her"],
         "recommendation": None, "why": "Her commitment was to you, so your word closes it.",
         "unlocks": "", "kind": "", "minutes": 3,
         "consequences": ["I will mark the gate as kept, with your word as its witness.",
                          "I will keep it open and ask again on Monday.",
                          "I will remind you to ask her this evening."], "leverage": 2.0, "whole_waits": False},
    ]
    third = {"n": 3, "section": "decision", "id": C["day"], "holon": CELL, "holon_name": "Cell Two",
             "question": "Which day should Cell Two meet this month?",
             "options": ["Thursday evening", "Saturday morning", "Ask the cell"],
             "recommendation": "Saturday morning", "why": "Five of the seven members said Saturday works.",
             "unlocks": "Booking the hall, then the gathering", "kind": "decide", "minutes": 5, "leverage": 12.4, "whole_waits": True}
    state = {
        "v": 1, "generated_at": NOW, "actor": ME, "calendar": "calendar-days",
        "holons": holons,
        "actors": [
            {"id": ME, "kind": "person", "for": ME, "holons": [HOME, CELL, ROOM], "delegation": None},
            {"id": AG, "kind": "agent", "for": ME, "holons": [HOME, CELL, ROOM],
             "delegation": {"from": ME, "scope": ["say", "card", "claim", "layout"], "holons": ["*"], "until": "2026-12-21", "live": True}},
            {"id": STEWARD, "kind": "person", "for": STEWARD, "holons": [CELL, ROOM], "delegation": None},
            {"id": NEIGHBOR, "kind": "person", "for": NEIGHBOR, "holons": [HOME], "delegation": None},
            {"id": MEMBER, "kind": "person", "for": MEMBER, "holons": [CELL, ROOM], "delegation": None},
        ],
        "cards": cards,
        "commitments": commitments,
        "threads": [{"id": T_SOUP, "holon": ROOM, "anchored_to": C["soup"], "title": "Who brings the soup",
                     "lines": 3, "last_actor": MEMBER, "last_ts": "2026-10-24T08:58:00-07:00", "settled": False, "to": [ME]}],
        "decisions": [{"id": D_DAY, "holon": CELL, "title": "Choose the meeting day", "holder": ME, "state": "open", "ratifier": STEWARD}],
        "sightings": [],
        "tea": {"by_actor": {ME: {"minutes": 840, "witnessed_minutes": 660}}, "by_holon": {CELL: {"minutes": 1290}},
                "by_card": {}, "by_stream": {}, "witness": {}, "convertible": False, "chain": []},
        "discernments": {"count": 4, "by_route": {}, "by_verdict": {"chosen": 2, "corrected": 1, "rated": 1}},
        "deal": {"actor": ME, "minutes_available": 15, "minutes_dealt": 8, "room": [ME],
                 "opening": "Here's the deal.", "cards": deal_cards,
                 "briefing": "Cell Two is waiting on your yes about the bread for Saturday, and the gate your neighbour said she would fix is a day past.",
                 "beyond": {"count": 2, "minutes": 35},
                 "question": "What did we miss that matters to you most?",
                 "rule": "near-critical minutes freed ÷ √(own minutes)",
                 "as_of": {HOME: line_id(HOME, 212), CELL: line_id(CELL, 88), ROOM: line_id(ROOM, 41)}},
        "owed": {"entries": [
            {"kind": "request", "id": C["bread"], "holon": CELL, "title": "Bring the bread to Saturday's gathering",
             "holder": ME, "status": "open", "due": "2026-10-31", "age_days": 2, "minutes": 30},
            {"kind": "claim", "id": C["gate"], "holon": HOME, "title": "Fix the garden gate",
             "holder": ME, "status": "open", "due": "2026-10-23", "age_days": 1, "minutes": 3},
            {"kind": "ratify", "id": D_DAY, "holon": CELL, "title": "Choose the meeting day",
             "holder": ME, "status": "open", "due": "2026-10-27", "age_days": 0, "minutes": 5},
            {"kind": "thread", "id": T_SOUP, "holon": ROOM, "title": "Who brings the soup",
             "holder": ME, "status": "open", "due": None, "age_days": 0, "minutes": 2},
            {"kind": "commitment", "id": K["chairs"], "holon": CELL, "title": "Set out the chairs",
             "holder": MEMBER, "status": "open", "due": "2026-10-31", "age_days": 3, "minutes": 15},
            {"kind": "commitment", "id": K["gate"], "holon": HOME, "title": "Fix the garden gate",
             "holder": NEIGHBOR, "status": "open", "due": "2026-10-23", "age_days": 1, "minutes": 60},
            {"kind": "request", "id": C["hall"], "holon": CELL, "title": "Book the hall",
             "holder": STEWARD, "status": "open", "due": "2026-10-29", "age_days": 0, "minutes": 20},
        ], "proposals": [
            {"kind": "request", "id": hid("proposal", "1"), "holon": HOME, "title": "Reply about the seed swap",
             "holder": ME, "status": "open", "due": None, "age_days": 0, "minutes": 5},
        ]},
        "kept": {"window": {"from": "2026-10-17", "to": "2026-10-24"},
                 "by_holon": {CELL: {"made": 8, "kept": 7, "kept_unwitnessed": 0, "broken": 1, "released": 0, "returned": 0, "open": 3, "share": 0.875}},
                 "by_actor": {ME: {"made": 4, "kept": 3, "kept_unwitnessed": 0, "broken": 0, "released": 0, "returned": 0, "open": 1, "share": 1.0}},
                 "commitments": [K["letters"]], "learning": []},
        "score": {CELL: {"earned": 120, "planned": 150, "minutes_done": 120, "minutes_total": 300, "spi": 0.8, "as_of": NOW}},
        "buffers": [{"milestone": C["gathering"], "holon": CELL, "size_days": 4, "consumed_days": 1, "chain_complete": 0.4, "signal": "calm"}],
        "load": [{"actor": ME, "date": "2026-10-24", "minutes": 45, "capacity": 120}],
        "path": {"critical": [C["day"], C["hall"], C["gathering"]], "system": [C["day"], C["gathering"]], "finish": "2026-10-31"},
        "turn": {"depth_due": "daily", "last_daily": "2026-10-23T21:00:00-07:00", "last_lunar": None,
                 "last_weekly": "2026-10-18T19:00:00-07:00", "last_seasonal": None, "next_weekly_due": "2026-10-25"},
        "invalid": [], "pending": [], "problems": [], "notes": [],
        "roles": {HOME: {ME: "keeper", NEIGHBOR: "member", AG: "agent"},
                  CELL: {STEWARD: "keeper", ME: "member", MEMBER: "member", AG: "agent"},
                  ROOM: {STEWARD: "keeper", ME: "member", MEMBER: "member", AG: "agent"}},
        "rooms": {ROOM: {"id": ROOM, "name": "The Gathering", "keeper": STEWARD,
                         "present": [{"actor": STEWARD, "kind": "person", "for": STEWARD, "role": "keeper"},
                                     {"actor": ME, "kind": "person", "for": ME, "role": "member"},
                                     {"actor": AG, "kind": "agent", "for": ME, "role": "agent"},
                                     {"actor": MEMBER, "kind": "person", "for": MEMBER, "role": "member"}],
                         "posture": {"posture": "open", "curing_days": 2, "by": STEWARD, "agreed_by": [STEWARD, ME, MEMBER]},
                         "lines": [line_id(ROOM, 41), line_id(ROOM, 40)], "offered": [], "awaiting_yes": [],
                         "agreed_by": {}, "opened": "2026-10-24T08:30:00-07:00", "closed": None,
                         "deal_open": None, "deal_close": None}},
        "_proposed": "This fixture carries only STATE.md v1 fields plus the server's hud block. Fields the HUD still needs are named as proposals where they are added.",
        "hud": {"v": 1, "mode": "fixture", "fixture": "fresh", "now": NOW, "served_at": NOW, "undo_ms": 5000,
                "sources": [
                    {"holon": HOME, "name": "Home", "path": ".", "readable": True, "heard": "2026-10-24T09:15:00-07:00"},
                    {"holon": CELL, "name": "Cell Two", "path": "cells/cell-two", "readable": True, "heard": "2026-10-24T09:15:00-07:00"},
                    {"holon": ROOM, "name": "The Gathering", "path": "cells/gathering", "readable": True, "heard": "2026-10-24T09:15:00-07:00"}],
                "layouts": [], "pending": []},
    }
    return state, third


def variants():
    fresh, third = base()
    out = {"fresh": fresh}

    s = copy.deepcopy(fresh)
    s["cards"] = [c for c in s["cards"] if c["state"] == "kept"]
    s["commitments"] = [k for k in s["commitments"] if k["status"] == "kept"]
    s["threads"], s["decisions"] = [], []
    s["deal"].update(cards=[], minutes_dealt=0, beyond={"count": 0, "minutes": 0}, briefing=None)
    s["owed"] = {"entries": [], "proposals": []}
    s["buffers"], s["path"] = [], {"critical": [], "system": [], "finish": None}
    out["empty"] = s

    s = copy.deepcopy(fresh)
    s["holons"][1]["as_of"] = {"event": line_id(CELL, 80), "ts": "2026-10-20T18:05:00-07:00", "lines": 80}
    s["hud"]["sources"][1]["heard"] = "2026-10-20T18:06:00-07:00"
    s["deal"]["cards"].append(copy.deepcopy(third))
    s["deal"]["minutes_dealt"] = 13
    s["deal"]["briefing"] = ("We need your decision on the meeting day, Cell Two is waiting on your yes about the bread, "
                             "and the gate is a day past.")
    # a long card your agent could carry (more than forty of its minutes): the Deal offers it to a body
    inv = hid("card", "invite-letter")
    s["cards"].append({**card("letters", CELL, "Draft the letter inviting the new members", "draft", "Care", ME, 20,
                              "2026-10-28", "ready", 1, 2, 3, 4), "id": inv, "agent_minutes": 75, "tokens_estimate": 180000})
    s["deal"]["cards"].append({"n": 4, "section": "ready", "kind": "", "id": inv, "holon": CELL, "holon_name": "Cell Two",
        "question": "Take the letter inviting the new members now?", "options": ["Take it now", "Hand it to someone else", "Not this week"],
        "recommendation": "Take it now", "why": "Your agent can draft it for you to read.", "unlocks": "", "minutes": 3,
        "leverage": 3.0, "whole_waits": False})
    out["stale"] = s

    s = copy.deepcopy(fresh)
    s["holons"] = s["holons"][:2]
    s["rooms"] = {}
    s["cards"] = [c for c in s["cards"] if c["holon"] != ROOM]
    s["threads"] = []
    s["owed"]["entries"] = [e for e in s["owed"]["entries"] if e["holon"] != ROOM]
    s["hud"]["sources"][2].update(readable="its saved state could not be parsed", heard=None)
    out["unreadable"] = s

    s = copy.deepcopy(fresh)
    s["rooms"][ROOM]["posture"]["posture"] = "names-hidden"
    s["deal"]["cards"].append({"n": 3, "section": "thread", "id": T_SOUP, "holon": ROOM, "holon_name": "The Gathering",
                               "question": "A member asked who brings the soup. Will you?",
                               "options": ["I will bring it", "Not this time", "Ask the room"],
                               "recommendation": None, "why": "The room meets at noon.",
                               "unlocks": "", "kind": "thread", "minutes": 2, "leverage": 1.5, "whole_waits": False})
    s["deal"]["minutes_dealt"] = 10
    s["deal"]["briefing"] = ("Cell Two is waiting on your yes about the bread, the gate is a day past, "
                             "and the room is asking who brings the soup.")
    out["names-hidden"] = s

    s = copy.deepcopy(fresh)
    s["deal"]["cards"].append(copy.deepcopy(third))
    s["deal"]["minutes_dealt"] = 13
    s["deal"]["briefing"] = ("We need your decision on the meeting day, Cell Two is waiting on your yes about the bread, "
                             "and the gate is a day past.")
    s["hud"]["layouts"] = [{"id": hid("layout", "large"), "actor": AG, "ts": "2026-10-24T09:10:00-07:00",
                            "name": "player", "views": ["deal", "commitments"], "hidden": [], "holons": [],
                            "type": "large", "theme": "system", "density": "calm", "default": True}]
    out["large"] = s

    # The invitation is a one-card Deal; a printed card answered in pencil is
    # the player's first line. A new home, nothing else held yet.
    s = copy.deepcopy(fresh)
    s["holons"] = s["holons"][:1]
    s["holons"][0]["as_of"] = {"event": line_id(HOME, 1), "ts": "2026-10-24T09:12:00-07:00", "lines": 1}
    s["cards"], s["commitments"], s["threads"], s["decisions"] = [], [], [], []
    s["owed"] = {"entries": [], "proposals": []}
    s["rooms"], s["buffers"], s["path"] = {}, [], {"critical": [], "system": [], "finish": None}
    s["roles"] = {HOME: {ME: "keeper", AG: "agent"}}
    s["deal"].update(minutes_dealt=2, beyond={"count": 0, "minutes": 0},
        greeting="I am your agent. A friend passed you the Flame, and I arrived today to help you keep your word.",
        briefing="One thing to begin, and it takes two minutes.",
        cards=[
        {"n": 1, "section": "ready", "kind": "", "id": hid("card", "invitation"), "holon": HOME, "holon_name": "Home",
         "question": "Would you like me to keep track of your commitments, and the commitments made to you?",
         "options": ["Yes, begin", "Tell me more first", "Not now"], "recommendation": "Yes, begin",
         "why": "It takes two minutes, and nothing leaves without your yes.", "unlocks": "", "minutes": 2,
         "consequences": ["I will begin with what you tell me, and ask before anything leaves.",
                          "I will tell you more, in a few plain lines.",
                          "I will wait until you ask."],
         "leverage": 1.0, "whole_waits": False}])
    s["hud"]["sources"] = s["hud"]["sources"][:1]
    out["invitation"] = s

    # The bar review (12): the Deal said "Your commitments are below" over nothing. A record the
    # engine has not dealt yet, with no open commitments: the line must not promise a "below".
    s = copy.deepcopy(fresh)
    s.pop("deal", None)
    s["commitments"] = [k for k in s["commitments"] if k["status"] != "open"]
    s["owed"] = {"entries": [], "proposals": []}
    out["undealt"] = s

    # Review 13: the dock's margin said a card was in the record while the Deal said nothing was
    # dealt. The agent has written a line the fold has not read yet (serve.py's record_newer).
    s = copy.deepcopy(out["undealt"])
    s["hud"]["record_newer"] = {"ts": "2026-10-24T09:19:00-07:00", "by_agent": True}
    out["agent-wrote"] = s

    # A chain-blocking card first: the decision the whole of Cell Two waits on, then the bread.
    s = copy.deepcopy(fresh)
    s["deal"]["cards"] = [copy.deepcopy(third), copy.deepcopy(fresh["deal"]["cards"][0])]
    # the gate is settled in this house, so nothing owed is left out of the deal (one first everywhere)
    s["owed"]["entries"] = [e for e in s["owed"]["entries"] if e["id"] not in (C["gate"], K["gate"])]
    s["cards"] = [dict(c, state="done") if c["id"] == C["gate"] else c for c in s["cards"]]
    s["deal"]["minutes_dealt"] = 10
    s["deal"]["briefing"] = ("Cell Two cannot book the hall until you choose the meeting day, "
                             "and it is waiting on your yes about the bread.")
    chain_lines = {
        C["day"]: story(CELL, [
            (C["day"], "2026-10-19T18:02:00-07:00", STEWARD, "card", {"title": "Choose the meeting day", "kind": "decision", "minutes": 5, "by": "2026-10-27"},
             {"successor": [C["hall"]]}, True),
            (None, "2026-10-21T09:30:00-07:00", MEMBER, "say", {"text": "Saturday morning works for me and for most of us."}, {"anchored_to": [C["day"]]}, True),
            (None, "2026-10-23T20:15:00-07:00", AG, "say", {"text": "Five of the seven members said Saturday works."}, {"anchored_to": [C["day"]]}, False)]),
        C["bread"]: story(CELL, [
            (C["bread"], "2026-10-22T10:00:00-07:00", STEWARD, "request", {"title": "Bring the bread to Saturday's gathering", "to": ME, "by": "2026-10-31", "size": 30}, {}, True),
            (None, "2026-10-22T10:05:00-07:00", STEWARD, "say", {"text": "Three of us are counting on the bread."}, {"anchored_to": [C["bread"]]}, True)]),
        C["hall"]: story(CELL, [
            (C["hall"], "2026-10-19T18:04:00-07:00", STEWARD, "card", {"title": "Book the hall", "minutes": 20, "by": "2026-10-29"},
             {"predecessor": [C["day"]], "successor": [C["gathering"]]}, True)]),
    }
    s["cards"] = [dict(c, lines=chain_lines[c["id"]]) if c["id"] in chain_lines else c for c in s["cards"]]
    out["deal-chain"] = s

    # Five known contradictions, each in the data that caused it, so a proof catches
    # any return: the gate is past its by-when though the plan gives it float (the Chain once
    # listed it "with days to spare"); the letters are done two days past their by-when with
    # float on the plan (the Board once said "two days past · two days to spare · Done"); the
    # bread was kept a day late inside a tally of three of three (the Turn); the deal is real;
    # and one said line arrives twice within thirty seconds (the Talk once showed it twice).
    s = copy.deepcopy(fresh)
    for c in s["cards"]:
        if c["id"] == C["gate"]:
            c.update(LS=2, LF=3, TF=2)
    s["commitments"].append({"id": K["bread"], "holon": CELL, "card": C["bread"], "title": "Bread to Cell Two",
        "keeper": ME, "by": "2026-10-17", "size": 30, "witness": STEWARD, "conditions": "", "status": "kept", "gap_days": 1})
    s["kept"]["commitments"] = [K["letters"], K["bread"]]
    said = {"by": STEWARD, "for": STEWARD, "room": ROOM, "text": "The hall is the biggest cost, so I would start there."}
    s["hud"]["talk"] = {ROOM: [dict(said, id="said-a", ts="2026-10-24T09:16:02-07:00"),
                               dict(said, id="said-b", ts="2026-10-24T09:16:09-07:00")]}
    out["truth"] = s

    out["deal-rich"] = deal_rich(fresh)

    for name, st in out.items():
        st["hud"]["fixture"] = name
    return out


# ---------------------------------------------------------------------------- deal-rich
# A house with real complexity, so a test can deal the next most important things. Three houses (home, Cell Two, the Commons); today's hand of five fills the
# fifteen minutes she has; seven more are ranked behind it in deal.beyond.cards, each with the
# item its kind demands (an owed entry, a decision, a thread, a question, a sighting, a card with
# its links), so every view reads one truth. The dealer's order of the rest: owed first (a
# request from the Commons, a body's handoff), then decisions (a ratify in the Commons, a
# question climbed to the home), then ready cards (two on the chain, one long enough to give to
# a body, one off it). Fitted to fifteen minutes the next hands hold 4, 1, 1, 1.

COMMONS = hid("holon", "commons")
CONVENER, WEAVER = "person:convener", "person:weaver"
R = {k: hid("card", "rich", k) for k in ["count", "day", "hall", "tables", "notes", "bread", "chairs", "lend",
                                         "welcome", "invite", "seeds", "gathering", "letters"]}
RK = {k: hid("commit", "rich", k) for k in ["notes", "bread", "hall", "chairs", "tables", "letters"]}
RD_DAY, RD_MARKET = hid("decision", "rich", "day"), hid("decision", "rich", "market")
RT = {k: hid("thread", "rich", k) for k in ["tables", "fire", "gate"]}
RQ_FIRE = hid("question", "rich", "fire")
RS_BRANCH = hid("sighting", "rich", "branch")
RH_BUDGET = hid("line", "rich", "handoff-budget")


def rcard(key, holon, title, kind, stream, holder, minutes, by, state, ES, EF, LS, LF, crit=False, sysc=False,
          preds=(), succs=(), stage="will", **extra):
    return {"id": R[key], "holon": holon, "title": title, "kind": kind, "stream": stream, "holder": holder,
            "minutes": minutes, "by": by, "stage": stage, "state": state,
            "predecessors": [R[p] for p in preds], "successors": [R[x] for x in succs], "serves": [],
            "audience": "holon", "ES": ES, "EF": EF, "LS": LS, "LF": LF, "TF": LS - ES, "FF": 0,
            "critical": crit, "system_critical": sysc, "variance_days": None, **extra}


def dcard(n, section, kind, id_, holon, question, options, rec, why, unlocks, minutes, leverage, whole=False, **extra):
    names = {HOME: "Home", CELL: "Cell Two", COMMONS: "The Commons"}
    return {"n": n, "section": section, "kind": kind, "id": id_, "holon": holon, "holon_name": names[holon],
            "question": question, "options": options, "recommendation": rec, "why": why, "unlocks": unlocks,
            "minutes": minutes, "leverage": leverage, "whole_waits": whole, **extra}


def deal_rich(fresh):
    s = copy.deepcopy(fresh)
    s["holons"] = [
        {"id": HOME, "name": "Home", "kind": "person", "keeper": ME,
         "as_of": {"event": line_id(HOME, 230), "ts": "2026-10-24T09:14:00-07:00", "lines": 230}},
        {"id": CELL, "name": "Cell Two", "kind": "cell", "keeper": STEWARD,
         "as_of": {"event": line_id(CELL, 96), "ts": "2026-10-24T08:40:00-07:00", "lines": 96}},
        {"id": COMMONS, "name": "The Commons", "kind": "body", "keeper": CONVENER,
         "as_of": {"event": line_id(COMMONS, 1840), "ts": "2026-10-24T07:55:00-07:00", "lines": 1840}},
    ]
    # the person's name and who brought them (serve.py's hud.person reads these): Cell Two's
    # steward witnessed the person's join there, and can be written to
    s["actors"] = [
        {"id": ME, "kind": "person", "for": ME, "holons": [HOME, CELL, COMMONS], "delegation": None,
         "name": "Player", "joined": {"witness": STEWARD, "holon": CELL}},
        {"id": AG, "kind": "agent", "for": ME, "holons": [HOME, CELL, COMMONS],
         "delegation": {"from": ME, "scope": ["say", "card", "claim", "layout"], "holons": ["*"], "until": "2026-12-21", "live": True}},
        {"id": STEWARD, "kind": "person", "for": STEWARD, "holons": [CELL, COMMONS], "delegation": None,
         "name": "Cell Two's steward", "reach": "mailto:steward@cell-two.example"},
        {"id": NEIGHBOR, "kind": "person", "for": NEIGHBOR, "holons": [HOME], "delegation": None},
        {"id": MEMBER, "kind": "person", "for": MEMBER, "holons": [CELL], "delegation": None},
        {"id": CONVENER, "kind": "person", "for": CONVENER, "holons": [COMMONS], "delegation": None},
        {"id": WEAVER, "kind": "person", "for": WEAVER, "holons": [COMMONS], "delegation": None},
    ]
    s["roles"] = {HOME: {ME: "keeper", NEIGHBOR: "member", AG: "agent"},
                  CELL: {STEWARD: "keeper", ME: "member", MEMBER: "member", AG: "agent"},
                  COMMONS: {CONVENER: "keeper", ME: "member", STEWARD: "member", WEAVER: "member", AG: "agent"}}
    s["rooms"] = {}

    # the chain to the autumn gathering: the long tables (the Commons, a day late) and the meeting
    # day then the hall (Cell Two) meet at the milestone; the welcome and the invitation feed it too
    s["cards"] = [
        rcard("count", CELL, "Send the harvest count to Cell Two", "activity", "Harvest", ME, 2, "2026-10-23", "open", 0, 1, 0, 1),
        rcard("day", CELL, "Choose the meeting day", "decision", "Gathering", ME, 3, "2026-10-26", "open", 0, 1, 0, 1, True, True, succs=["hall"]),
        rcard("hall", CELL, "Book the hall", "activity", "Gathering", STEWARD, 20, "2026-10-29", "ready", 1, 2, 1, 2, True, True,
              preds=["day"], succs=["gathering"]),
        rcard("tables", COMMONS, "Carry the long tables from the Commons", "activity", "Gathering", WEAVER, 60, "2026-10-23", "taken",
              0, 1, 0, 1, True, False, succs=["gathering"]),
        rcard("notes", CELL, "Write up the cell's harvest notes", "activity", "Harvest", ME, 30, "2026-10-27", "taken", 0, 1, 2, 3),
        rcard("bread", CELL, "Bring the bread to the autumn gathering", "activity", "Gathering", ME, 30, "2026-10-31", "taken", 5, 6, 6, 7),
        rcard("chairs", CELL, "Set out the chairs", "activity", "Gathering", MEMBER, 15, "2026-10-31", "taken", 5, 6, 6, 7),
        rcard("lend", COMMONS, "Lend your folding chairs to the Commons", "activity", "Winter market", ME, 3, "2026-10-26", "open", 0, 1, 1, 2),
        rcard("welcome", CELL, "Write the welcome for the autumn gathering", "draft", "Gathering", ME, 10, "2026-10-29", "ready",
              1, 2, 1, 2, True, False, succs=["gathering"]),
        rcard("invite", COMMONS, "Draft the invitation to the Commons", "draft", "Gathering", ME, 45, "2026-10-29", "ready",
              1, 2, 2, 3, True, False, succs=["gathering"], agent_minutes=75, tokens_estimate=180000),
        rcard("seeds", HOME, "Sort the seed packets", "activity", "Garden", ME, 15, "2026-11-02", "ready", 3, 4, 12, 13),
        rcard("gathering", CELL, "The autumn gathering", "milestone", "Gathering", STEWARD, 0, "2026-10-31", "ready", 6, 6, 6, 6, True, True,
              preds=["hall", "tables", "welcome", "invite"]),
        rcard("letters", CELL, "Write to the new members", "activity", "Care", ME, 40, "2026-10-22", "kept", 0, 1, 2, 3, stage="did"),
    ]
    rich_lines = {
        R["count"]: story(CELL, [
            (R["count"], "2026-10-20T08:10:00-07:00", STEWARD, "request",
             {"title": "Send the harvest count to Cell Two", "to": ME, "by": "2026-10-23", "size": 2}, {}, True),
            (None, "2026-10-20T08:12:00-07:00", STEWARD, "say", {"text": "I plan the gathering's table from the count."}, {"anchored_to": [R["count"]]}, True),
            (None, "2026-10-24T08:20:00-07:00", STEWARD, "say", {"text": "Still waiting on the count, when you have a minute."}, {"anchored_to": [R["count"]]}, True)]),
        R["day"]: story(CELL, [
            (R["day"], "2026-10-19T18:02:00-07:00", STEWARD, "card", {"title": "Choose the meeting day", "kind": "decision", "minutes": 3, "by": "2026-10-26"},
             {"successor": [R["hall"]]}, True),
            (RD_DAY, "2026-10-19T18:03:00-07:00", STEWARD, "decide", {"title": "Choose the meeting day", "to": ME}, {"answers": [R["day"]]}, True),
            (None, "2026-10-22T09:30:00-07:00", MEMBER, "say", {"text": "Saturday morning works for me and for most of us."}, {"anchored_to": [R["day"]]}, True),
            (None, "2026-10-23T20:15:00-07:00", AG, "say", {"text": "Five of the seven members said Saturday works."}, {"anchored_to": [R["day"]]}, False)]),
        R["hall"]: story(CELL, [
            (R["hall"], "2026-10-19T18:04:00-07:00", STEWARD, "card", {"title": "Book the hall", "minutes": 20, "by": "2026-10-29"},
             {"predecessor": [R["day"]], "successor": [R["gathering"]]}, True),
            (RK["hall"], "2026-10-19T18:06:00-07:00", STEWARD, "commit", {"card": R["hall"], "by": "2026-10-29", "size": 20, "witness": ME}, {}, True)]),
        R["tables"]: story(COMMONS, [
            (R["tables"], "2026-10-15T11:00:00-07:00", CONVENER, "card", {"title": "Carry the long tables from the Commons", "minutes": 60, "by": "2026-10-23"},
             {"successor": [R["gathering"]]}, True),
            (None, "2026-10-16T09:00:00-07:00", WEAVER, "claim", {"card": R["tables"]}, {}, True),
            (RK["tables"], "2026-10-16T09:02:00-07:00", WEAVER, "commit", {"card": R["tables"], "by": "2026-10-23", "size": 60, "witness": ME}, {}, True),
            (RT["tables"], "2026-10-23T19:40:00-07:00", WEAVER, "thread", {"title": "Who helps carry the long tables", "to": [ME]}, {"anchored_to": [R["tables"]]}, True),
            (None, "2026-10-24T07:50:00-07:00", WEAVER, "say", {"text": "Two more hands on Friday and they are in the hall by noon."}, {"anchored_to": [RT["tables"]]}, True)]),
        R["notes"]: story(CELL, [
            (R["notes"], "2026-10-18T17:00:00-07:00", STEWARD, "card", {"title": "Write up the cell's harvest notes", "minutes": 30, "by": "2026-10-27"}, {}, True),
            (None, "2026-10-20T19:00:00-07:00", ME, "claim", {"card": R["notes"]}, {}, False),
            (RK["notes"], "2026-10-20T19:01:00-07:00", ME, "commit", {"card": R["notes"], "by": "2026-10-27", "size": 30, "witness": STEWARD}, {}, False)]),
        R["letters"]: story(CELL, [
            (R["letters"], "2026-10-12T10:00:00-07:00", STEWARD, "card", {"title": "Write to the new members", "minutes": 40, "by": "2026-10-22"}, {}, True),
            (RK["letters"], "2026-10-13T08:00:00-07:00", ME, "commit", {"card": R["letters"], "by": "2026-10-22", "size": 40, "witness": STEWARD}, {}, True),
            (hid("story", "kept", "letters"), "2026-10-21T16:30:00-07:00", ME, "kept", {"note": "All four letters went out by hand."}, {"fulfils": [RK["letters"]]}, True),
            (None, "2026-10-22T09:00:00-07:00", STEWARD, "witness", {}, {"witnesses": [hid("story", "kept", "letters")]}, True)]),
        R["gathering"]: story(CELL, [
            (R["gathering"], "2026-10-12T09:00:00-07:00", STEWARD, "card", {"title": "The autumn gathering", "kind": "milestone", "by": "2026-10-31"}, {}, True),
            (RQ_FIRE, "2026-10-24T08:30:00-07:00", MEMBER, "rfg", {"question": "May Cell Two light the evening fire in your garden?", "about": R["gathering"]}, {}, True)]),
    }
    for c in s["cards"]:
        if c["id"] in rich_lines:
            c["lines"] = rich_lines[c["id"]]
        else:   # every card carries at least the line that made it
            c["lines"] = story(c["holon"], [(c["id"], "2026-10-18T12:00:00-07:00", STEWARD if c["holon"] == CELL else CONVENER if c["holon"] == COMMONS else ME,
                                              "card", {"title": c["title"], "minutes": c["minutes"], "by": c["by"]}, {}, c["holon"] != HOME)])
    k = lambda key, holon, card_key, title, keeper, by, size, witness, status="open", gap=None: {
        "id": RK[key], "holon": holon, "card": R[card_key], "title": title, "keeper": keeper, "by": by, "size": size,
        "witness": witness, "conditions": "", "status": status, "gap_days": gap}
    s["commitments"] = [
        k("notes", CELL, "notes", "Write up the cell's harvest notes", ME, "2026-10-27", 30, STEWARD),
        k("bread", CELL, "bread", "Bring the bread to the autumn gathering", ME, "2026-10-31", 30, STEWARD),
        k("hall", CELL, "hall", "Book the hall", STEWARD, "2026-10-29", 20, ME),
        k("chairs", CELL, "chairs", "Set out the chairs", MEMBER, "2026-10-31", 15, ME),
        k("tables", COMMONS, "tables", "Carry the long tables from the Commons", WEAVER, "2026-10-23", 60, ME),
        k("letters", CELL, "letters", "Write to the new members", ME, "2026-10-22", 40, STEWARD, "kept", -1),
    ]
    s["threads"] = [
        # her turn: the Commons asks about the long tables (dealt today)
        {"id": RT["tables"], "holon": COMMONS, "anchored_to": R["tables"], "title": "Who helps carry the long tables",
         "lines": 4, "last_actor": WEAVER, "last_ts": "2026-10-24T07:50:00-07:00", "settled": False, "to": [ME]},
        # from Cell Two to her agent, unread: the agent's turn, not hers
        {"id": RT["fire"], "holon": CELL, "anchored_to": R["hall"], "title": "Where the evening fire can go",
         "lines": 2, "last_actor": STEWARD, "last_ts": "2026-10-24T08:35:00-07:00", "settled": False, "to": [AG],
         "stake": {"holder": AG}},
        # she spoke last: the neighbour's turn (not dealt)
        {"id": RT["gate"], "holon": HOME, "anchored_to": None, "title": "The latch on the garden gate",
         "lines": 3, "last_actor": ME, "last_ts": "2026-10-23T18:10:00-07:00", "settled": False, "to": [NEIGHBOR]},
    ]
    s["decisions"] = [
        {"id": RD_DAY, "holon": CELL, "title": "Choose the meeting day", "holder": ME, "state": "open", "ratifier": STEWARD},
        {"id": RD_MARKET, "holon": COMMONS, "title": "Hold the winter market on the first Saturday of December",
         "holder": CONVENER, "state": "decided", "ratifier": ME, "decided": "The first Saturday of December, in the long barn.",
         "conditions_met": True},
    ]
    s["questions"] = [
        {"id": RQ_FIRE, "type": "rfg", "from_holon": CELL, "to": HOME, "question": "May Cell Two light the evening fire in your garden?",
         "about": R["gathering"], "blast_radius": "cell", "rung": {"n": 1, "name": "the keeper"}, "holder": ME,
         "by": "2026-10-30", "ts": "2026-10-24T08:30:00-07:00", "asker": MEMBER, "state": "open", "closed_by": None,
         "next": None, "past": False},
    ]
    s["sightings"] = {HOME: {"as_of": line_id(HOME, 229), "new": [
        {"id": RS_BRANCH, "holon": HOME, "kind": "hazard", "text": "A fallen branch across the lane by the garden gate",
         "where": "the lane", "actor": NEIGHBOR, "ts": "2026-10-24T07:40:00-07:00", "status": "new"}],
        "held": [], "elevated": [], "folded": []}}

    o = lambda kind, id_, holon, title, holder, due, age, minutes, **x: {
        "kind": kind, "id": id_, "holon": holon, "title": title, "holder": holder, "status": "open",
        "due": due, "age_days": age, "minutes": minutes, **x}
    s["owed"] = {"entries": [
        o("request", R["count"], CELL, "Send the harvest count to Cell Two", ME, "2026-10-23", 3, 2),
        o("decide", R["day"], CELL, "Choose the meeting day", ME, "2026-10-26", 1, 3),
        o("thread", RT["tables"], COMMONS, "Who helps carry the long tables", ME, None, 0, 5),
        o("commitment", RK["notes"], CELL, "Write up the cell's harvest notes", ME, "2026-10-27", 4, 3),
        o("request", R["lend"], COMMONS, "Lend your folding chairs to the Commons", ME, "2026-10-26", 0, 3),
        o("handoff", RH_BUDGET, HOME, "The gathering's budget, drafted", ME, None, 0, 5,
          body="the budget for the gathering", task="the gathering's budget", asks_yes=True),
        o("ratify", RD_MARKET, COMMONS, "Hold the winter market on the first Saturday of December", ME, "2026-10-28", 0, 3),
        o("commitment", RK["tables"], COMMONS, "Carry the long tables from the Commons", WEAVER, "2026-10-23", 1, 60),
        o("thread", RT["fire"], CELL, "Where the evening fire can go", AG, None, 0, 3),
        o("thread", RT["gate"], HOME, "The latch on the garden gate", NEIGHBOR, None, 1, 3),
    ], "proposals": []}

    today = [
        dcard(1, "owed", "request", R["count"], CELL, "Cell Two asked for the harvest count by Friday. Send it now?",
              ["Yes, send it today", "Not this week", "Hand it on"], "Yes, send it today",
              "The steward is waiting on it to plan the gathering's table.",
              "The gathering's table", 2, 9.0,
              consequences=["I will tell Cell Two the count is coming today.", "I will tell Cell Two it waits until next week.",
                            "I will ask Cell Two who else can send it."]),
        dcard(2, "owed", "commitment", RK["notes"], CELL, "You said you would write up the harvest notes by Tuesday. Is it on track?",
              ["On track for Tuesday", "I need until Thursday", "Release it"], "On track for Tuesday",
              "Tuesday is three days off, and Cell Two's steward is the witness.", "", 3, 2.0,
              consequences=["I will keep Tuesday in view and remind you on Monday.",
                            "I will ask the steward whether Thursday works.", "I will tell Cell Two it is free for someone else."]),
        dcard(3, "thread", "thread", RT["tables"], COMMONS, "The Commons asks who can help carry the long tables on Friday. Can you?",
              ["I can help on Friday", "Not this time", "Ask the Commons"], "I can help on Friday",
              "The tables are a day late, and the gathering needs them.", "The long tables, then the gathering", 5, 4.0),
        dcard(4, "decision", "decide", R["day"], CELL, "Which day should Cell Two meet this month?",
              ["Thursday evening", "Saturday morning", "Ask the cell"], "Saturday morning",
              "Five of the seven members said Saturday works.", "Booking the hall, then the gathering", 3, 12.4, True),
        dcard(5, "decision", "sighting", RS_BRANCH, HOME, "Pass this on to the circle? Your neighbour saw a fallen branch across the lane by the gate.",
              ["Pass it on", "Keep it here", "Not yet"],
              "Pass it on", "A branch across the lane is a danger to everyone who walks it.",
              "The safety of the lane", 2, 1.5),
    ]
    rest = [
        dcard(6, "owed", "request", R["lend"], COMMONS, "The Commons asks to borrow your folding chairs for the winter market. Lend them?",
              ["Yes, lend them", "Not this time", "Ask someone else"], "Yes, lend them",
              "They are asked for by Monday, and you are not using them.", "The winter market's seating", 3, 3.0,
              consequences=["I will tell the Commons the chairs are theirs for the market.", "I will tell the Commons not this time.",
                            "I will ask the Commons who else has chairs."]),
        dcard(7, "owed", "handoff", RH_BUDGET, HOME, "Your agent finished the budget for the gathering. Read what it found?",
              ["Read it now", "Put it in my Deal"], "Read it now", "It asks for your yes before the steward sees it.",
              "The steward's copy of the budget", 5, 1.0, eyebrow="HANDOFF · YOUR AGENT · REVIEW"),
        dcard(8, "decision", "ratify", RD_MARKET, COMMONS, "The Commons decided to hold the winter market on the first Saturday of December. Confirm it?",
              ["Confirm it", "Read the thread first", "Not yet"], "Confirm it",
              "What was decided is written, its conditions are met, and no one has spoken against it.", "The market's date", 3, 2.0),
        dcard(9, "decision", "question", RQ_FIRE, HOME, "A question for you: \"May Cell Two light the evening fire in your garden?\"",
              ["Yes, with the usual care", "Not this year", "Ask me after the gathering"], "Yes, with the usual care",
              "It was asked of you as keeper of your home, and the gathering plans around it.", "Cell Two's plan for the evening", 2, 1.5),
        dcard(10, "ready", "", R["welcome"], CELL, "Take the welcome for the autumn gathering now?",
              ["Take it now", "Hand it to someone else", "Not this week"], "Take it now",
              "The gathering waits on it, and it takes ten minutes.", "The autumn gathering", 10, 2.6),
        dcard(11, "ready", "", R["invite"], COMMONS, "Take the invitation to the Commons now?",
              ["Take it now", "Hand it to someone else", "Not this week"], "Take it now",
              "Your agent can draft it for you to read.", "The autumn gathering", 45, 1.4),
        dcard(12, "ready", "", R["seeds"], HOME, "Sort the seed packets now?",
              ["Take it now", "Not this week"], "Not this week", "It has room to wait until November.", "", 15, 0.4),
    ]
    s["deal"] = {"actor": ME, "minutes_available": 15, "minutes_dealt": 15, "room": [ME], "opening": "Here's the deal.",
                 "cards": today,
                 "briefing": ("The harvest count Cell Two asked for is a day past, and the whole of Cell Two "
                              "is waiting on the meeting day."),
                 "beyond": {"count": len(rest), "minutes": float(sum(c["minutes"] for c in rest)), "cards": rest},
                 "owed_to_you": [{"kind": "commitment", "id": RK["tables"], "holon": COMMONS,
                                  "title": "Carry the long tables from the Commons", "holder": WEAVER,
                                  "status": "open", "due": "2026-10-23"}],
                 "proposals": 0, "fewer": "as set",
                 "question": "What did we miss that matters to you most?",
                 "rule": fresh["deal"]["rule"],
                 "as_of": {HOME: line_id(HOME, 230), CELL: line_id(CELL, 96), COMMONS: line_id(COMMONS, 1840)}}
    s["kept"] = {"window": {"from": "2026-10-17", "to": "2026-10-24"},
                 "by_holon": {CELL: {"made": 8, "kept": 7, "kept_unwitnessed": 0, "broken": 1, "released": 0, "returned": 0, "open": 4, "share": 0.875}},
                 "by_actor": {ME: {"made": 3, "kept": 1, "kept_unwitnessed": 0, "broken": 0, "released": 0, "returned": 0, "open": 2, "share": 1.0}},
                 "commitments": [RK["letters"]], "learning": []}
    s["tea"] = {"by_actor": {ME: {"minutes": 840, "witnessed_minutes": 660}}, "by_holon": {CELL: {"minutes": 1290}, COMMONS: {"minutes": 4200}},
                "by_card": {}, "by_stream": {}, "witness": {}, "convertible": False, "chain": []}
    s["score"] = {CELL: {"earned": 40, "planned": 150, "minutes_done": 40, "minutes_total": 160, "spi": 0.27, "as_of": NOW}}
    # a day of the four eaten by the late tables, and a second by the day not yet chosen: Watch
    s["buffers"] = [{"milestone": R["gathering"], "holon": CELL, "size_days": 4, "consumed_days": 2, "chain_complete": 0.25, "signal": "watch"}]
    s["load"] = [{"actor": ME, "date": "2026-10-24", "minutes": 75, "capacity": 120}]
    s["path"] = {"critical": [R["tables"], R["day"], R["hall"], R["welcome"], R["invite"], R["gathering"]],
                 "system": [R["day"], R["hall"], R["gathering"]], "finish": "2026-10-31"}
    s["badges"] = {"threads_and_mail": 2, "from_houses": 2, "as_of": NOW, "source": "the carried store"}
    s["hud"]["sources"] = [
        {"holon": HOME, "name": "Home", "path": ".", "readable": True, "heard": "2026-10-24T09:15:00-07:00"},
        {"holon": CELL, "name": "Cell Two", "path": "cells/cell-two", "readable": True, "heard": "2026-10-24T09:15:00-07:00"},
        {"holon": COMMONS, "name": "The Commons", "path": "cells/the-commons", "readable": True, "heard": "2026-10-24T09:15:00-07:00"}]
    s["hud"].pop("talk", None)
    return s


if __name__ == "__main__":
    for name, st in variants().items():
        p = HERE / f"{name}.json"
        p.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", p.name)
