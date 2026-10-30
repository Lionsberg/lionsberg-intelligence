#!/usr/bin/env python3
"""make_room_fixtures.py: the Room's sample states (DESIGN-ROOM §8.1).

Run:  python3 make_room_fixtures.py      (after make_fixtures.py; writes room-*.json beside it)

Builds on make_fixtures.base() and never edits it: each file here is the `fresh` state
with a room in one of its phases (before · door · work · close · after), under Open and
under Names hidden, with a guest from a second house, an agent offering from something it
read, a stale change the fold refused, and the lines themselves, so the Play by Play, the
Talk, the Ledger, the Turn and the Record have something true to show.

Fields here that engine/STATE.md does not yet carry are PROPOSALS. Each is named in `_proposed_c` in every file:

  lines                       the event lines the views reference, as written, each with
                              `verified` (signed · unsigned · missing_link); elided fields
                              left as {"elided": "<digest>"}
  rooms[id].purpose, phase, parts, current_part, play_by_play_keeper, links, big_ideas,
             line_meta {line: {part, proposed_by}}, curing_until, present[].state,
             present[].house ("second" for a guest from another house)
  tea.entries                 one per tea line: {line, holon, card, actor, ts, minutes,
                              energy, attention, witness: unwitnessed · keeper · supercell}
  tea.season                  {from, to, minutes, witnessed_minutes} for the wearer
  discernments.lines          the wearer's own discern lines {line, ts, verdict, about}
  turn.draft                  the four lines as drafts:
                              {kept, gap, next, flame: {text, status: draft}}
  hud.talk[room]              what the live store of DESIGN-ROOM §8.2 would carry: said
                              lines and whispers, never in the record

Times are fixture times (the shared clock is 2026-10-24 09:20, a Saturday morning).
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_fixtures as base_mod  # noqa: E402

hid = base_mod.hid
HOME, CELL, ROOM = base_mod.HOME, base_mod.CELL, base_mod.ROOM
ME, AG, STEWARD, MEMBER = base_mod.ME, base_mod.AG, base_mod.STEWARD, base_mod.MEMBER
NEIGHBOR_ = base_mod.NEIGHBOR
GUEST, ST_AG, GU_AG = "person:guest", "agent:steward-agent", "agent:guest-agent"
C, K = base_mod.C, base_mod.K
TZ = "-07:00"


def ts(hm, day="2026-10-24"):
    return f"{day}T{hm}:00{TZ}"


def sig(i):
    return "ssh-ed25519:" + hashlib.sha256(("sig" + i).encode()).hexdigest()[:64]


PREV = {}


def line(key, holon, actor, typ, body, at, links=None, for_=None, reason=None, verified="signed"):
    """One event line in the schema's shape (engine/SCHEMA.md), with the view's `verified`."""
    i = hid("fixture-line", key)
    prev = PREV.get((holon, actor), "")
    PREV[(holon, actor)] = i
    who_for = for_ or (actor if actor.startswith("person:") else ME)
    ln = {"v": 1, "id": i, "ts": at, "actor": actor, "for": who_for, "holon": holon, "type": typ,
          "body": dict(body, body_salt=hashlib.sha256(("salt" + key).encode()).hexdigest()[:32]),
          "links": links or {}, "audience": "holon",
          "reason": reason or ("human" if actor.startswith("person:") else "delegated"),
          "prev": prev, "sig": sig(i) if verified != "unsigned" else "", "verified": verified}
    return ln


C_COSTS, C_HALLASK, C_DRAFT = hid("card", "costs"), hid("card", "hall-ask"), hid("card", "plan-draft")
K_SOUP, K_COSTS = hid("commit", "soup"), hid("commit", "costs")
T_DAY = hid("thread", "day")
NOT_HELD = hid("line", "not-yet-arrived")


def room_lines():
    L = {}
    add = lambda k, *a, **kw: L.__setitem__(k, line(k, *a, **kw))
    add("posture", ROOM, STEWARD, "posture", {"posture": "open", "curing_days": 3}, ts("09:00"))
    add("aff-me", ROOM, ME, "affirm", {"agent": AG, "room": ROOM}, ts("09:01"))
    add("aff-st", ROOM, STEWARD, "affirm", {"agent": ST_AG, "room": ROOM}, ts("09:01"))
    add("aff-gu", ROOM, GUEST, "affirm", {"agent": GU_AG, "room": ROOM}, ts("09:02"))
    # part one: where we are
    add("weeks", ROOM, MEMBER, "settle", {"text": "We have four weeks before the autumn gathering."}, ts("09:06"),
        verified="unsigned")
    add("monday", ROOM, STEWARD, "decide", {"text": "Monday is the first test of the new plan."}, ts("09:10"))
    add("t-day", ROOM, MEMBER, "thread", {"title": "When on Monday"}, ts("09:10"), links={"anchored_to": [hid("fixture-line", "monday")]})
    add("t-day-1", ROOM, MEMBER, "say", {"text": "Morning or evening?"}, ts("09:11"), links={"anchored_to": [hid("fixture-line", "t-day")]})
    add("t-day-2", ROOM, GUEST, "say", {"text": "Evening suits those who work."}, ts("09:11"), links={"anchored_to": [hid("fixture-line", "t-day")]})
    add("t-day-3", ROOM, STEWARD, "settle", {"text": "Monday at seven, in the hall."}, ts("09:12"), links={"anchored_to": [hid("fixture-line", "t-day")]})
    # part two: the budget
    add("off-hall", ROOM, ST_AG, "say", {"text": "The hall costs the same on Thursday and on Saturday."}, ts("09:13"), for_=STEWARD)
    add("off-soup", ROOM, AG, "say", {"text": "Your costs sheet carries last year's soup figure, which may be low."}, ts("09:15"), for_=ME)
    add("off-free", ROOM, GU_AG, "say", {"text": "The commons calendar shows the hall free on the first Saturday."}, ts("09:16"),
        for_=GUEST, reason="untrusted")
    add("off-spent", ROOM, ST_AG, "say", {"text": "Last year the food money was spent by the second week."}, ts("09:16"), for_=STEWARD)
    add("off-chairs", ROOM, GU_AG, "say", {"text": "Chairs can be borrowed from the school at no cost."}, ts("09:17"), for_=GUEST)
    add("food", ROOM, GUEST, "settle", {"text": "We spend no more than last year on food."}, ts("09:17"))
    add("hallask", ROOM, STEWARD, "card", {"title": "Ask the hall about the first Saturday", "holder": MEMBER, "minutes": 20,
        "by": "2026-10-28", "kind": "activity", "stream": "Room"}, ts("09:18"), links={"anchored_to": [hid("fixture-line", "off-free")]})
    add("ask-costs", ROOM, STEWARD, "request", {"to": ME, "title": "Bring the costs for the first week", "by": "2026-10-29",
        "minutes": 60}, ts("09:19"))
    add("soup", ROOM, MEMBER, "commit", {"card": C["soup"], "by": "2026-10-24", "size": 30, "witness": STEWARD}, ts("09:19"))
    add("sight-step", ROOM, MEMBER, "sight", {"text": "The back step of the hall is loose.", "where": "the hall", "kind": "hazard"}, ts("09:14"))
    add("rfg-key", ROOM, MEMBER, "rfg", {"question": "May the room hold the hall key overnight?", "to": ROOM, "by": "2026-10-26"},
        ts("09:05"))
    add("draft-day", ROOM, ST_AG, "propose", {"text": "Hold the autumn gathering on the first Saturday.", "drafts": "decide"},
        ts("09:19"), for_=STEWARD)
    return L


def home_cell_lines():
    L = {}
    add = lambda k, *a, **kw: L.__setitem__(k, line(k, *a, **kw))
    add("tea-letters", CELL, ME, "tea", {"minutes": 40, "energy": 7, "attention": 8, "card": C["letters"]}, ts("18:10", "2026-10-21"))
    add("wit-letters", CELL, STEWARD, "witness", {"note": "The letters went out on Tuesday."}, ts("08:05", "2026-10-22"),
        links={"witnesses": [hid("fixture-line", "tea-letters")]})
    add("tea-day", CELL, ME, "tea", {"minutes": 25, "energy": 6, "attention": 9, "card": C["day"]}, ts("19:30", "2026-10-22"))
    add("tea-bread", CELL, ME, "tea", {"minutes": 30, "energy": 5, "attention": 6, "card": C["bread"]}, ts("07:50", "2026-10-24"))
    add("tea-seeds", HOME, ME, "tea", {"minutes": 20, "energy": 4, "attention": 5, "card": C["seeds"]}, ts("16:00", "2026-10-23"))
    add("kept-letters", CELL, ME, "kept", {"commitment": K["letters"], "note": "Sent to all four."}, ts("18:20", "2026-10-21"))
    add("commit-bread", CELL, ME, "commit", {"card": C["bread"], "by": "2026-10-31", "size": 30, "witness": STEWARD}, ts("08:00", "2026-10-22"))
    add("discern-1", HOME, ME, "discern", {"verdict": "corrected", "note": "a draft to Cell Two"}, ts("10:00", "2026-10-21"))
    add("discern-2", HOME, ME, "discern", {"verdict": "chosen", "note": "the Saturday suggestion"}, ts("09:00", "2026-10-22"))
    add("discern-3", HOME, ME, "discern", {"verdict": "chosen", "note": "the order of today's cards"}, ts("07:40", "2026-10-24"))
    add("discern-4", HOME, ME, "discern", {"verdict": "rated", "note": "a summary of the cell's week", "rating": 4}, ts("07:45", "2026-10-24"))
    add("turn-last", HOME, ME, "turn", {"span": "week", "depth": "weekly", "text": "Kept: the letters. Next: the gathering."},
        ts("19:00", "2026-10-18"))
    add("elevate-gate", CELL, STEWARD, "elevate", {"what": hid("fixture-line", "sight-gate"), "to": ROOM,
        "why": "Every garden on the lane shares the gate.", "witness": ME}, ts("12:00", "2026-10-23"))
    add("escalate-hall", CELL, STEWARD, "escalate", {"about": C["hall"], "to": ROOM, "blast_radius": "the whole gathering",
        "rung": 2, "by": "2026-10-30"}, ts("12:10", "2026-10-23"))
    add("chairs-ask", CELL, STEWARD, "request", {"to": ME, "title": "Bring two more chairs on Saturday", "by": "2026-10-31",
        "minutes": 10, "push": {"kind": "request", "by": "2026-10-31", "why_by": "the gathering is that morning", "size": 10,
        "blocks": [C["gathering"]], "critical": True, "who_waits": "two members of the cell", "blast": "the whole gathering; reversible",
        "cost_if_late": "the room sets out fewer chairs", "alternatives": "we borrow from the school", "asked": "this week, if you can",
        "expires": "2026-10-30"}}, ts("08:20"))
    add("gate-say", HOME, ME, "say", {"text": "Thank you for the gate."}, ts("08:30", "2026-10-24"),
        links={"answers": [NOT_HELD]}, verified="missing_link")
    return L


def room_state(phase="work", posture="open"):
    PREV.clear()
    st, _third = base_mod.base()
    st = copy.deepcopy(st)
    RL, HL = room_lines(), home_cell_lines()
    lid = lambda k: (RL.get(k) or HL.get(k))["id"]

    st["actors"] += [
        {"id": ST_AG, "kind": "agent", "for": STEWARD, "holons": [ROOM], "delegation": {"from": STEWARD, "scope": ["say", "card", "propose"],
         "holons": [ROOM], "until": "2026-12-21", "live": True}},
        {"id": GUEST, "kind": "person", "for": GUEST, "holons": [ROOM], "delegation": None},
        {"id": GU_AG, "kind": "agent", "for": GUEST, "holons": [ROOM], "delegation": {"from": GUEST, "scope": ["say"],
         "holons": [ROOM], "until": "2026-10-25", "live": True}},
    ]
    st["roles"][ROOM].update({GUEST: "guest", ST_AG: "agent", GU_AG: "agent"})
    st["cards"] += [
        {"id": C_COSTS, "holon": ROOM, "title": "Bring the costs for the first week", "kind": "activity", "stream": "Room",
         "holder": ME, "minutes": 60, "by": "2026-10-29", "stage": "should", "state": "open", "predecessors": [], "successors": [C_HALLASK],
         "serves": [], "audience": "holon", "ES": 0, "EF": 1, "LS": 1, "LF": 2, "TF": 1, "FF": 0, "critical": False,
         "system_critical": False, "variance_days": None},
        {"id": C_HALLASK, "holon": ROOM, "title": "Ask the hall about the first Saturday", "kind": "activity", "stream": "Room",
         "holder": MEMBER, "minutes": 20, "by": "2026-10-28", "stage": "will", "state": "taken", "predecessors": [C_COSTS],
         "successors": [], "serves": [C["gathering"]], "audience": "holon", "ES": 1, "EF": 2, "LS": 1, "LF": 2, "TF": 0, "FF": 0,
         "critical": True, "system_critical": True, "variance_days": None},
        {"id": C_DRAFT, "holon": ROOM, "title": "The draft plan for the first week", "kind": "draft", "stream": "Room",
         "holder": STEWARD, "minutes": 8, "by": "2026-10-26", "stage": "can", "state": "ready", "predecessors": [], "successors": [],
         "serves": [], "audience": "holon", "ES": 0, "EF": 1, "LS": 3, "LF": 4, "TF": 3, "FF": 0, "critical": False,
         "system_critical": False, "variance_days": None},
    ]
    st["commitments"] += [
        {"id": K_SOUP, "holon": ROOM, "card": C["soup"], "title": "Bring soup for the room", "keeper": MEMBER, "by": "2026-10-24",
         "size": 30, "witness": STEWARD, "conditions": "", "status": "open", "gap_days": None},
    ]
    st["commitments"][0]["status"] = "kept-unwitnessed"     # the gate: claimed, awaiting the witness (the middle ink)
    st["commitments"].append({"id": hid("commit", "bread-last"), "holon": CELL, "card": C["bread"], "title": "Bread to Cell Two",
                              "keeper": ME, "by": "2026-10-17", "size": 30, "witness": STEWARD, "conditions": "",
                              "status": "kept", "gap_days": 1})
    st["owed"]["entries"] += [
        {"kind": "request", "id": C_COSTS, "holon": ROOM, "title": "Bring the costs for the first week", "holder": ME, "status": "open",
         "due": "2026-10-29", "age_days": 0, "minutes": 60},
    ]
    st["threads"] += [{"id": T_DAY, "holon": ROOM, "anchored_to": lid("monday"), "title": "When on Monday", "lines": 3,
                       "last_actor": STEWARD, "last_ts": ts("09:12"), "settled": True, "to": []}]
    # threads to the wearer or her agent (the Threads view): urgency and stake are proposals
    for th in st["threads"]:
        if th["id"] == base_mod.T_SOUP:
            th.update(stake={"blocks": [C["soup"], C["gathering"]], "critical": True, "by": "2026-10-24", "holder": ME,
                             "urgency": "before noon, please", "minutes": 2})
    st["threads"].append({"id": hid("thread", "seeds"), "holon": HOME, "anchored_to": C["seeds"], "title": "Swap seeds on Sunday?",
                          "lines": 2, "last_actor": ME, "last_ts": ts("08:50"), "settled": False, "to": [NEIGHBOR_]})
    st["threads"].append({"id": hid("thread", "hall-key"), "holon": CELL, "anchored_to": C["hall"], "title": "Who keeps the hall key?",
                          "lines": 1, "last_actor": STEWARD, "last_ts": ts("08:35"), "settled": False, "to": [AG],
                          "stake": {"blocks": [C["hall"]], "critical": False, "by": "2026-10-28", "holder": AG,
                                    "urgency": "this week", "minutes": 5}})
    st["kept"]["learning"] = [{"id": hid("learn", "bread"), "holon": CELL, "actor": ME,
                               "text": "Ask for the hall key on Thursday, so Friday is free for baking.",
                               "about": hid("commit", "bread-last")}]
    st["kept"]["by_holon"][ROOM] = {"made": 1, "kept": 0, "kept_unwitnessed": 0, "broken": 0, "released": 0, "returned": 0,
                                    "open": 1, "share": None}
    # tea: the entries (proposal) and the season (proposal) beside STATE's totals
    st["tea"]["entries"] = [
        {"line": lid("tea-letters"), "holon": CELL, "card": C["letters"], "actor": ME, "ts": HL["tea-letters"]["ts"],
         "minutes": 40, "energy": 7, "attention": 8, "witness": "supercell"},
        {"line": lid("tea-day"), "holon": CELL, "card": C["day"], "actor": ME, "ts": HL["tea-day"]["ts"],
         "minutes": 25, "energy": 6, "attention": 9, "witness": "keeper"},
        {"line": lid("tea-bread"), "holon": CELL, "card": C["bread"], "actor": ME, "ts": HL["tea-bread"]["ts"],
         "minutes": 30, "energy": 5, "attention": 6, "witness": "unwitnessed"},
        {"line": lid("tea-seeds"), "holon": HOME, "card": C["seeds"], "actor": ME, "ts": HL["tea-seeds"]["ts"],
         "minutes": 20, "energy": 4, "attention": 5, "witness": "unwitnessed"},
        {"line": hid("fixture-line", "tea-visit"), "holon": CELL, "card": C["visit"], "actor": MEMBER, "ts": ts("17:00", "2026-10-23"),
         "minutes": 45, "energy": 6, "attention": 7, "witness": "unwitnessed"},
    ]
    st["tea"]["season"] = {"from": "2026-09-22", "to": "2026-12-21", "minutes": 840, "witnessed_minutes": 660}
    st["discernments"]["lines"] = [{"line": HL[k]["id"], "ts": HL[k]["ts"], "verdict": HL[k]["body"]["verdict"],
                                    "about": HL[k]["body"]["note"]} for k in ("discern-1", "discern-2", "discern-3", "discern-4")]
    st["turn"]["draft"] = {
        "kept": {"text": "The letters to the new members, a day early.", "status": "draft"},
        "gap": {"text": "The bread came a day late. Ask for the hall key on Thursday.", "status": "draft"},
        "next": {"text": "Choose the meeting day, so the hall can be booked.", "status": "draft"},
        "flame": {"text": "Thank the neighbour for the gate.", "status": "draft"},
    }
    st["turn"]["depth_due"] = "daily"

    # the room
    agreed = ["soup", "ask-costs", "hallask", "food", "monday", "weeks"]
    offered_keys = ["off-hall", "off-soup", "off-free", "off-spent", "off-chairs"]
    room = st["rooms"][ROOM]
    room.update({
        "purpose": "To choose what we do in our first week.",
        "phase": phase,
        "parts": [
            {"n": 1, "title": "Where we are", "question": "What do we have, and what is missing?", "minutes": 8,
             "started": ts("09:04"), "ended": ts("09:12")},
            {"n": 2, "title": "The budget", "question": "What can we spend, and on what?", "minutes": 20,
             "started": ts("09:12"), "ended": None},
            {"n": 3, "title": "Who carries what", "question": "Who will carry each thing, and by when?", "minutes": 15,
             "started": None, "ended": None},
            {"n": 4, "title": "What we commit to", "question": "What will each of us commit to before we close?", "minutes": 10,
             "started": None, "ended": None},
        ],
        "current_part": 2,
        "play_by_play_keeper": ST_AG,
        "links": [{"title": "The draft plan"}, {"title": "Last year's costs"}, {"title": "The hall's calendar"}],
        "big_ideas": [lid("monday"), lid("food"), lid("weeks")],
        "line_meta": {lid(k): {"part": (1 if k in ("weeks", "monday") else 2)} for k in agreed},
        "keeper": STEWARD,
        "opened": ts("09:00"),
        "curing_until": None,
        "present": [
            {"actor": STEWARD, "kind": "person", "for": STEWARD, "role": "keeper", "state": "speaking"},
            {"actor": ST_AG, "kind": "agent", "for": STEWARD, "role": "agent", "state": "keeping the Play by Play"},
            {"actor": ME, "kind": "person", "for": ME, "role": "member", "state": "here"},
            {"actor": AG, "kind": "agent", "for": ME, "role": "agent", "state": "listening"},
            {"actor": MEMBER, "kind": "person", "for": MEMBER, "role": "member", "state": "here"},
            {"actor": GUEST, "kind": "person", "for": GUEST, "role": "guest", "state": "here", "house": "second"},
            {"actor": GU_AG, "kind": "agent", "for": GUEST, "role": "agent", "state": "offering"},
        ],
        "posture": {"posture": posture, "curing_days": 3, "by": STEWARD, "agreed_by": [STEWARD, ME, MEMBER, GUEST]},
        "lines": [lid(k) for k in agreed],
        "offered": [{"line": lid("sight-step"), "by": MEMBER, "for": MEMBER, "reason": "human"}] + [{"line": lid(k), "by": RL[k]["actor"], "for": RL[k]["for"], "reason": RL[k]["reason"]} for k in offered_keys],
        "awaiting_yes": [lid("draft-day")],
        "agreed_by": {lid("food"): [GUEST], lid("monday"): [STEWARD], lid("weeks"): [MEMBER], lid("hallask"): [STEWARD],
                      lid("ask-costs"): [STEWARD], lid("soup"): [MEMBER]},
        "deal_open": {"actor": ME, "minutes_available": 12, "minutes_dealt": 11, "opening": "Here's the deal.", "cards": [
            {"n": 1, "section": "ready", "id": C_DRAFT, "holon": ROOM, "holon_name": "The Gathering",
             "question": "Read the draft plan before the room meets?", "options": ["Read it now", "I will read it Sunday", "Skip it"],
             "recommendation": "Read it now", "why": "About eight minutes, and the budget part leans on it.", "unlocks": "",
             "kind": "draft", "minutes": 8, "leverage": 3.0, "whole_waits": False},
            {"n": 2, "section": "owed", "id": C_COSTS, "holon": ROOM, "holon_name": "The Gathering",
             "question": "You said you would bring the costs. Still on?", "options": ["Yes, on track", "I need more time", "Pass it on"],
             "recommendation": None, "why": "The keeper will witness it.", "unlocks": "", "kind": "commitment", "minutes": 3,
             "leverage": 2.0, "whole_waits": False}],
            "question": "What did we miss that matters to you most?"},
        "deal_close": None,
    })
    room["closed"] = None
    st["holons"][2]["as_of"] = {"event": lid("draft-day"), "ts": ts("09:19"), "lines": 41}

    # the said lines and whispers: what the live store would carry (never in the record)
    st["hud"]["talk"] = {ROOM: [
        {"id": "said-1", "by": STEWARD, "for": STEWARD, "ts": ts("09:12"), "part": 2, "text": "The hall is the biggest cost, so I would start there."},
        {"id": "said-2", "by": MEMBER, "for": MEMBER, "ts": ts("09:14"), "part": 2, "text": "Last year we paid for the hall and the soup, and little else."},
        {"id": "said-3", "by": GUEST, "for": GUEST, "ts": ts("09:15"), "part": 2, "text": "In our house the hall was free in exchange for cleaning it."},
        {"id": "said-4", "by": ME, "for": ME, "ts": ts("09:18"), "part": 2, "text": "I can bring the costs, though not before Wednesday."},
        {"id": "whisper-1", "by": AG, "for": ME, "ts": ts("09:15"), "part": 2, "whisper": True, "to": [ST_AG],
         "text": "My person's sheet has last year's soup figure."},
        {"id": "whisper-2", "by": ST_AG, "for": STEWARD, "ts": ts("09:15"), "part": 2, "whisper": True, "to": [AG],
         "text": "Thank you. I will offer it if the keeper asks."},
    ]}

    # sightings, questions and ladders (STATE.md, added 2026-10-24 afternoon)
    sl = RL["sight-step"]
    st["sightings"] = {
        ROOM: {"as_of": ts("09:19"), "new": [{"id": sl["id"], "holon": ROOM, "kind": "hazard", "text": sl["body"]["text"],
               "where": "the hall", "actor": MEMBER, "ts": sl["ts"], "status": "new"}], "held": [], "elevated": [], "folded": []},
        CELL: {"as_of": ts("08:40"), "new": [], "held": [], "elevated": [{"id": hid("fixture-line", "sight-gate"), "holon": CELL,
               "kind": "defect", "text": "The lane gate does not latch.", "where": "the lane", "actor": NEIGHBOR_, "ts": ts("08:00", "2026-10-23"),
               "status": "elevated", "elevated": {"by": STEWARD, "to": ROOM, "why": "Every garden on the lane shares the gate.",
               "witness": ME, "line": HL["elevate-gate"]["id"], "ts": HL["elevate-gate"]["ts"]}}], "folded": []},
        HOME: {"as_of": None, "new": [], "held": [], "elevated": [], "folded": []}}
    rq = RL["rfg-key"]
    st["questions"] = [
        {"id": rq["id"], "type": "rfg", "from_holon": ROOM, "to": ROOM, "question": rq["body"]["question"], "about": None,
         "blast_radius": None, "rung": {"n": 2, "name": "cell"}, "holder": STEWARD, "by": "2026-10-26", "ts": rq["ts"],
         "asker": MEMBER, "state": "open", "closed_by": None, "next": None, "past": []},
        {"id": HL["escalate-hall"]["id"], "type": "escalate", "from_holon": CELL, "to": ROOM, "question": "Book the hall",
         "about": C["hall"], "blast_radius": "the whole gathering", "rung": {"n": 2, "name": "cell"}, "holder": STEWARD,
         "by": "2026-10-30", "ts": HL["escalate-hall"]["ts"], "asker": STEWARD, "state": "open", "closed_by": None, "next": None, "past": []}]
    st["ladders"] = {h: [{"n": 1, "name": "person", "remit": "", "days": 1}, {"n": 2, "name": "cell", "remit": "", "days": 7},
                         {"n": 3, "name": "council", "remit": "", "days": 14}, {"n": 4, "name": "body", "remit": "", "days": 30}]
                     for h in (HOME, CELL, ROOM)}
    # mail (DESIGN-MAIL §10.5): proposals, shown "Not computed yet" where absent
    ch = HL["chairs-ask"]
    st["mail"] = {"mailboxes": [{"actor": ME, "reachable": True, "last_read": ts("09:15")}], "items": [
        {"id": hid("mail", "chairs"), "message_id": "m-chairs", "line_id": ch["id"], "from_actor": STEWARD, "from_role": "the keeper",
         "from_house": "the cell", "for": ME, "holon": CELL, "card": C["chairs"], "push": ch["body"]["push"],
         "push_recomputed": {"blocks": [C["gathering"]], "critical": True, "calibration": {"by_held": 9, "of": 10}},
         "kind": "line", "verified": "verified", "carried": False, "read": False, "picked_up": False, "withdrawn": False,
         "arrived": ["mail", "pulled"], "question": "Will you bring two more chairs on Saturday?", "ts": ch["ts"]},
        {"id": hid("mail", "prose"), "message_id": "m-prose", "line_id": None, "from_actor": GUEST, "from_role": "a guest",
         "from_house": "a second house", "for": ME, "holon": ROOM, "card": None, "push": None, "push_recomputed": None,
         "kind": "prose", "verified": "unverified", "carried": True, "read": False, "picked_up": False, "withdrawn": False,
         "arrived": ["mail"], "question": "Could your cell lend us its long table for a week in November?",
         "proposed_line": {"type": "request", "title": "Lend the long table for a week in November", "reason": "untrusted"},
         "ts": ts("07:55")}]}
    st["badges"] = {"threads_and_mail": 3, "from_houses": 2, "as_of": ts("09:19")}
    st["transports"] = {"forge": {"beat_present_min": 5, "beat_away_min": 60, "last_pull": ts("09:15"), "next_pull": ts("09:20")},
                        "hook": {"armed": True, "last_at": ts("09:19")}, "room_stream": {"open_room": ROOM},
                        "mail": {"on": True, "last_read": ts("09:15")}, "phone_push": {"on": False}, "relay": {"on": False}}
    st["calibration"] = {"senders": {STEWARD: {"by_held": 9, "of": 10, "as_of": ts("09:19")}}, "own": {"by_held": 6, "of": 7}}
    lines = list(RL.values()) + list(HL.values())
    # a stale change refused by the fold (DESIGN-ROOM §4.4), shown, never counted
    st["invalid"] = [{"id": hid("fixture-line", "stale-edit"), "type": "supersede", "actor": GU_AG, "holon": ROOM,
                      "invalid_reason": "it changed a line that had changed since it was read; returned to its agent"}]

    if phase == "before":
        room.update(phase="before", present=[], opened=None, lines=[], offered=[], awaiting_yes=[], agreed_by={}, line_meta={},
                    big_ideas=[], current_part=None)
        for p in room["parts"]:
            p["started"] = p["ended"] = None
        st["hud"]["talk"] = {ROOM: []}
        lines = [l for l in lines if l["holon"] != ROOM] + [RL["posture"]]
    elif phase == "door":
        room["posture"]["agreed_by"] = [STEWARD, MEMBER, GUEST]
        room["present"] = [p for p in room["present"] if p["actor"] != AG]
        lines = [l for l in lines if l["id"] != RL["aff-me"]["id"]]
    elif phase == "close":
        room["current_part"] = 4
        for p in room["parts"]:
            p["started"] = p["started"] or ts("09:32")
            p["ended"] = p["ended"] or (ts("09:47") if p["n"] < 4 else None)
        room["parts"][1]["ended"] = ts("09:32")
        room["parts"][3]["started"] = ts("09:47")
        room["deal_close"] = {"actor": ME, "minutes_available": 2, "minutes_dealt": 1, "opening": "Here's the deal.", "cards": [
            {"n": 1, "section": "owed", "id": C_COSTS, "holon": ROOM, "holon_name": "The Gathering",
             "question": "Confirm: you bring the costs for the first week by Thursday.", "options": ["Confirm", "Change the day"],
             "recommendation": "Confirm", "why": "The keeper will witness it.", "unlocks": "", "kind": "commitment", "minutes": 1,
             "leverage": 2.0, "whole_waits": False}], "question": "What did we miss that matters to you most?"}
        st["hud"]["now"] = ts("09:50")
    elif phase == "after":
        room["closed"] = ts("10:00")
        room["curing_until"] = "2026-10-27"
        room["present"] = []
        room["current_part"] = None
        for p in room["parts"]:
            p["started"] = p["started"] or ts("09:32")
            p["ended"] = p["ended"] or ts("10:00")
        st["hud"]["talk"] = {ROOM: []}
        st["hud"]["now"] = ts("10:20")

    if posture == "names-hidden":
        # what the server serves a member under Names hidden: every other actor's name elided,
        # every signature still verifying (the id hashes the salted digests; engine/SCHEMA.md, Elision)
        def elide(v, salt):
            return {"elided": hashlib.sha256((salt + str(v)).encode()).hexdigest()}
        for ln in lines:
            if ln["holon"] != ROOM:
                continue
            for f in ("actor", "for"):
                if ln[f] not in (ME, AG):
                    ln[f] = elide(ln[f], ln["body"]["body_salt"])
            for f in ("to", "witness", "holder", "agent"):
                if isinstance(ln["body"].get(f), str) and ln["body"][f] not in (ME, AG):
                    ln["body"][f] = elide(ln["body"][f], ln["body"]["body_salt"])
            ln["elided"] = [f for f in ("actor", "for", "to", "witness", "holder", "agent")
                            if isinstance(ln.get(f), dict) or isinstance(ln["body"].get(f), dict)]
    st["lines"] = sorted(lines, key=lambda l: l["ts"], reverse=True)
    st["_proposed_c"] = ("Proposals, not yet in STATE.md: lines; rooms[id].purpose, phase, parts, current_part, "
                         "play_by_play_keeper, links, big_ideas, line_meta, curing_until, present[].state, present[].house; "
                         "tea.entries; tea.season; discernments.lines; turn.draft; hud.talk (the live store).")
    return st


def threads_quiet(st, keep=None):
    """Threads and Mail: the same morning with every word owed by the wearer
    given, except the thread `keep` (None: the rest state). Answers are her own `say` lines."""
    ours = {ME, AG}
    for th in st["threads"]:
        if th["id"] != keep and (th.get("stake") or {}).get("holder") in ours:
            th["settled"] = True
            th["stake"]["holder"] = None
    st["mail"]["items"] = []
    st["badges"] = {"threads_and_mail": 0, "from_houses": 0, "as_of": ts("09:19")}
    for ln in list(st["lines"]):
        to = (ln.get("body") or {}).get("to")
        if ln["holon"] != HOME and ln["actor"] not in ours and (ln.get("for") in ours or to in ours):
            st["lines"].append(line("answer-" + ln["id"][:8], ln["holon"], ME, "say", {"text": "Yes."}, ts("09:18"),
                                    links={"answers": [ln["id"]]}))
    return st


def variants():
    out = {
        "room-before": room_state("before"),
        "room-door": room_state("door"),
        "room-work": room_state("work"),
        "room-close": room_state("close"),
        "room-after": room_state("after"),
        "room-names-hidden": room_state("work", "names-hidden"),
    }
    out["threads-one"] = threads_quiet(room_state("work"), keep=base_mod.T_SOUP)
    out["threads-rest"] = threads_quiet(room_state("work"))
    out.update(shape_variants())
    for name, st in out.items():
        st["hud"]["fixture"] = name
        st["hud"]["layouts"] = [{"id": hid("layout", name), "actor": ME, "ts": ts("09:00"), "name": "room",
                                 "views": ["deal", "room"], "hidden": [], "holons": [], "type": "regular",
                                 "theme": "system", "density": "calm", "default": False}]
    return out


# ---------------------------------------------------------------------------- the one shape
# One shape only, with several parts (DESIGN-ROOM §10, a proposal): the lobby, the great room, the vote, the writing and reflection, under a participation
# posture agreed at the door, confirmed at the close, and a curing window afterwards. These states
# are the deal-rich house (Home, Cell Two, the Commons) with the Commons' circle of seven meeting in
# one room. The room's state is folded by engine/rooms.py from the lines below, so what the view
# shows is what the record says (one truth). The facilitator is the Commons' convener, never the
# wearer, except in room-shape-vote-facilitator.

ENGINE = HERE.parent.parent / "engine"
sys.path.insert(0, str(ENGINE))
import rooms as rooms_mod  # noqa: E402

COMMONS = base_mod.COMMONS
CONVENER, WEAVER = base_mod.CONVENER, base_mod.WEAVER
GARDENER = "person:gardener"
SHAPE_ROOM = hid("holon", "winter-market-circle")
CIRCLE = [CONVENER, WEAVER, STEWARD, MEMBER, NEIGHBOR_, GARDENER, ME]     # the circle of seven
SHAPE_CLOCK = {"lobby": "09:06", "great": "09:31", "vote": "09:41", "vote-facilitator": "09:41",
               "writing": "10:10", "reflect": "10:30", "close": "11:00"}
PROPOSALS = [   # (key, by, text): nine, made in the great room
    ("p-tables", WEAVER, "Lay the long tables in the barn for the market."),
    ("p-soup", STEWARD, "Keep a soup pot going all day, free for anyone."),
    ("p-seeds", GARDENER, "Run a seed swap at the barn door."),
    ("p-lend", AG, "Ask each house to lend one folding chair."),
    ("p-light", MEMBER, "String lanterns along the lane so the evening is safe."),
    ("p-kids", NEIGHBOR_, "Give the children a corner to make cards."),
    ("p-mend", CONVENER, "Set up a mending table for coats and tools."),
    ("p-music", WEAVER, "Ask the fiddlers to play at noon."),
    ("p-map", ME, "Draw a map of the stalls for the gate."),
]
VOTES = {   # who voted for what (three each); the market's top two are the tables and the lanterns
    WEAVER: ["p-tables", "p-light", "p-music"], STEWARD: ["p-tables", "p-soup", "p-light"],
    GARDENER: ["p-seeds", "p-tables", "p-light"], MEMBER: ["p-light", "p-tables", "p-kids"],
    NEIGHBOR_: ["p-kids", "p-light", "p-tables"], CONVENER: ["p-mend", "p-tables", "p-soup"],
    ME: ["p-tables", "p-map", "p-light"],
}


def shape_lines(stage, facilitator):
    """The circle's room, line by line, up to the stage asked for."""
    PREV.clear()
    L = []
    add = lambda k, *a, **kw: L.append(line("shape-" + k, *a, **kw))
    R = SHAPE_ROOM
    for i, p in enumerate(CIRCLE):
        if p == ME and stage == "lobby":
            add("join-me", R, ME, "join", {"role": "member"}, ts("09:04"))
            continue
        add("join-" + p, R, p, "join", {"role": "keeper" if p == CONVENER else "member"}, ts("09:0%d" % min(i, 3)))
    if stage != "lobby":
        add("aff-me", R, ME, "affirm", {"agent": AG, "room": R}, ts("09:05"))
    add("shape", R, CONVENER, "shape", {"shape": {
        "name": "the one shape", "parts": list(rooms_mod.SHAPE_PARTS), "facilitator": facilitator,
        "posture": "chatham-house", "cure_days": 3, "rule": {"choose": 3, "advance": 2, "minutes": 20}}}, ts("09:02"))
    for i, p in enumerate(CIRCLE):
        if p == ME and stage == "lobby":
            continue
        if stage == "lobby" and p in (GARDENER,):
            continue     # one more of the circle has not yet agreed either
        add("agree-" + p, R, p, "posture", {"posture": "chatham-house", "at": "open"}, ts("09:0%d" % (3 + min(i, 2))))
    if stage == "lobby":
        return L
    add("great", R, facilitator, "part", {"part": "great room"}, ts("09:10"))
    upto = 7 if stage == "great" else 9
    for n, (k, by, text) in enumerate(PROPOSALS[:upto]):
        add(k, R, by, "propose", {"text": text}, ts("09:%02d" % (12 + 2 * n)), for_=ME if by == AG else None)
    if stage == "great":
        return L
    add("vote", R, facilitator, "part", {"part": "the vote", "opens": ts("09:35"), "closes": ts("09:55"),
                                         "rule": {"choose": 3, "advance": 2, "minutes": 20}}, ts("09:35"))
    pid = {k: hid("fixture-line", "shape-" + k) for k, _, _ in PROPOSALS}
    voters = [WEAVER, STEWARD, GARDENER, MEMBER] if stage.startswith("vote") else list(VOTES)
    for n, v in enumerate(voters):
        add("v-" + v, R, v, "vote", {"choices": [pid[k] for k in VOTES[v]]}, ts("09:%02d" % (36 + n)))
    if stage.startswith("vote"):
        return L
    add("writing", R, facilitator, "part", {"part": "the writing"}, ts("09:56"))
    add("wu-tables", R, facilitator, "card", {"title": "Write up the long tables in the barn", "holder": WEAVER,
        "by": "2026-10-29", "minutes": 30, "kind": "draft"}, ts("09:58"), links={"serves": [pid["p-tables"]]})
    add("wu-light", R, facilitator, "card", {"title": "Write up the lanterns along the lane", "by": "2026-10-30",
        "minutes": 30, "kind": "draft"}, ts("09:59"), links={"serves": [pid["p-light"]]})
    add("wu-light-claim", R, ME, "claim", {"card": hid("fixture-line", "shape-wu-light")}, ts("10:02"))
    if stage == "writing":
        return L
    add("reflect", R, facilitator, "part", {"part": "reflection"}, ts("10:20"))
    for k, by, text, at in [("r-weaver", WEAVER, "The vote was quick, and nobody felt left out.", "10:22"),
                            ("r-steward", STEWARD, "I came in doubtful and leave with a part to play.", "10:23"),
                            ("r-member", MEMBER, "The lanterns matter more than I thought.", "10:25"),
                            ("r-gardener", GARDENER, "Next time, a few more minutes in the great room.", "10:26")]:
        add(k, R, by, "say", {"text": text}, ts(at))
    if stage == "reflect":
        return L
    add("r-me", R, ME, "say", {"text": "Good to choose two and carry them well."}, ts("10:28"))
    add("close", R, facilitator, "part", {"part": "close", "cure_until": "2026-10-27T10:40:00-07:00"}, ts("10:40"))
    for i, p in enumerate([CONVENER, WEAVER, STEWARD, MEMBER, GARDENER]):
        add("confirm-" + p, R, p, "posture", {"posture": "chatham-house", "at": "close",
            "cure_until": "2026-10-27T10:40:00-07:00"}, ts("10:%02d" % (41 + i)))
    add("narrow-gardener", R, GARDENER, "posture", {"withdraw": True, "posture": "off-the-record"}, ts("10:52"))
    return L


def shape_state(stage, facilitator=CONVENER):
    st = copy.deepcopy(base_mod.variants()["deal-rich"])
    lines = shape_lines(stage, facilitator)
    now = ts(SHAPE_CLOCK[stage])
    room_h = {"id": SHAPE_ROOM, "name": "The Winter Market Circle", "kind": "room", "keeper": CONVENER,
              "as_of": {"event": lines[-1]["id"], "ts": lines[-1]["ts"], "lines": len(lines)}}
    st["holons"].append(room_h)
    for a in st["actors"]:
        if a["id"] in CIRCLE or a["id"] == AG:
            a["holons"] = sorted(set(a["holons"]) | {SHAPE_ROOM})
        if a["id"] == AG:
            a["delegation"]["scope"] = sorted(set(a["delegation"]["scope"]) | {"propose"})
    st["actors"].append({"id": GARDENER, "kind": "person", "for": GARDENER, "holons": [COMMONS, SHAPE_ROOM], "delegation": None})
    st["roles"][COMMONS][GARDENER] = "member"
    trust = {l["id"]: "signed" for l in lines}
    hs = [{"id": SHAPE_ROOM, "name": room_h["name"], "kind": "room", "keeper": CONVENER}]
    room = rooms_mod.rooms(lines, hs, ME, now=now, trust=trust)[SHAPE_ROOM]
    room["purpose"] = "To choose what the Commons makes ready for the winter market."
    st["rooms"] = {SHAPE_ROOM: room}
    st["roles"][SHAPE_ROOM] = rooms_mod.roles(lines, hs, trust=trust)[SHAPE_ROOM]
    # the write-ups are cards on the Table as well: one card, one truth
    for w in room["shape"]["writeups"]:
        st["cards"].append({"id": w["card"], "holon": SHAPE_ROOM, "title": w["title"], "kind": "draft", "stream": "Winter market",
                            "holder": w["holder"], "minutes": 30, "by": w["by"], "stage": "will",
                            "state": "taken" if w["holder"] else "ready", "predecessors": [], "successors": [],
                            "serves": [w["proposal"]], "audience": "holon", "ES": 0, "EF": 1, "LS": 3, "LF": 4, "TF": 3,
                            "FF": 0, "critical": False, "system_critical": False, "variance_days": None})
    st["lines"] = sorted(st.get("lines", []) + lines, key=lambda l: l["ts"], reverse=True)
    st["hud"]["now"] = now
    st["hud"]["sources"].append({"holon": SHAPE_ROOM, "name": room_h["name"], "path": "cells/winter-market-circle",
                                 "readable": True, "heard": now})
    st["hud"].pop("talk", None)
    st["_proposed_shape"] = ("rooms[id].shape is folded by engine/rooms.py (STATE.md, A room's shape; a proposal). "
                             "rooms[id].purpose is a proposal, as in the other room fixtures.")
    return st


def shape_variants():
    return {
        "room-shape-lobby": shape_state("lobby"),
        "room-shape-great": shape_state("great"),
        "room-shape-vote": shape_state("vote"),
        "room-shape-vote-facilitator": shape_state("vote-facilitator", facilitator=ME),
        "room-shape-writing": shape_state("writing"),
        "room-shape-reflect": shape_state("reflect"),
        "room-shape-close": shape_state("close"),
    }


if __name__ == "__main__":
    for name, st in variants().items():
        p = HERE / f"{name}.json"
        p.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", p.name)
