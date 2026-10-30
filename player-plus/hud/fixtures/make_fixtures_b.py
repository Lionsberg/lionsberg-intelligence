#!/usr/bin/env python3
"""make_fixtures_b.py: one derived fixture for the Map, the Chain and the Board, `proposed-b.json`.

It reads fixtures/fresh.json (written by make_fixtures.py) and adds
ONLY the fields the Map, the Chain and the Board ask of the state and STATE.md v1 does not
yet carry, so the views can be seen with them. Every added field is listed in `_proposed`.
Fold this into make_fixtures.py when the fields land in STATE.md; until then this file is
the honest form: the six fixtures of (a) show "Not computed yet" where these are absent.

    python3 fixtures/make_fixtures_b.py
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

def main():
    st = json.loads((HERE / "fresh.json").read_text())
    home, cell, room = [h["id"] for h in st["holons"]]
    body = "b0d1e5c0ffee" + "0" * 52

    # 1. holons[].activity_7d: lines settled in the last seven days (DESIGN §4.4 turning; §8.4)
    activity = {home: 6, cell: 24, room: 0}
    for h in st["holons"]:
        h["activity_7d"] = activity.get(h["id"])
    # 2. a holon of kind `body` the wearer belongs to (so all three field sizes are seen)
    st["holons"].append({"id": body, "name": "The Commons", "kind": "body", "keeper": "person:steward",
                         "as_of": {"event": "e" * 64, "ts": "2026-10-23T17:30:00-07:00", "lines": 1840},
                         "baseline": None, "activity_7d": 60})
    st["roles"][body] = {"person:player": "member", "person:steward": "keeper"}
    st["hud"]["sources"].append({"holon": body, "name": "The Commons", "path": "cells/commons",
                                 "readable": True, "heard": "2026-10-24T09:15:00-07:00"})
    # 2b. a cell not heard from since Tuesday, quiet this week (the Map shows it dimmer and stiller)
    quiet = "c0115f17e" + "0" * 55
    st["holons"].append({"id": quiet, "name": "Cell Five", "kind": "cell", "keeper": "person:steward",
                         "as_of": {"event": "f" * 64, "ts": "2026-10-20T16:10:00-07:00", "lines": 57},
                         "baseline": None, "activity_7d": 2})
    st["roles"][quiet] = {"person:steward": "keeper", "person:player": "member", "person:member": "member", "person:neighbor": "member"}
    st["hud"]["sources"].append({"holon": quiet, "name": "Cell Five", "path": "cells/cell-five",
                                 "readable": True, "heard": "2026-10-20T16:10:00-07:00"})
    # 3. path.drum: the resource the chain moves at the pace of
    st["path"]["drum"] = {"actor": "person:steward", "holon": cell}
    # 4. kept.by_stream: commitments kept per stream, per holon (same tally shape as by_holon)
    st["kept"]["by_stream"] = {cell: {
        "Gathering": {"made": 4, "kept": 3, "kept_unwitnessed": 0, "broken": 1, "released": 0, "returned": 0, "open": 2, "share": 0.75},
        "Care": {"made": 2, "kept": 2, "kept_unwitnessed": 0, "broken": 0, "released": 0, "returned": 0, "open": 1, "share": 1.0}}}
    # 5. sightings in STATE's per-holon shape {as_of, new, held, elevated, folded} (the navigation layer)
    def row(n, holon, kind, text, actor, ts, status, **extra):
        r = {"id": f"s{n}" + "0" * 62, "holon": holon, "kind": kind, "text": text, "where": None,
             "actor": actor, "ts": ts, "status": status}
        r.update(extra)
        return r
    st["sightings"] = {
        cell: {"as_of": "2026-10-24T08:40:00-07:00",
               "new": [row(2, cell, "request", "Two families new to the valley need firewood", "person:player", "2026-10-23T16:00:00-07:00", "new")],
               "held": [row(6, cell, "blocked", "The hall key is with someone away until Monday", "person:member", "2026-10-24T07:50:00-07:00", "held",
                            held={"thread": None, "note": "Asked who else holds a key", "by": "person:steward"})],
               "elevated": [row(1, cell, "hazard", "The hall roof leaks over the east door", "person:member", "2026-10-24T08:05:00-07:00", "elevated",
                                elevated={"by": "person:steward", "to": body, "why": "The Commons keeps the hall", "witness": None, "line": None, "ts": "2026-10-24T08:30:00-07:00"})],
               "folded": []},
        home: {"as_of": "2026-10-24T09:14:00-07:00",
               "new": [row(3, home, "offer", "Spare apple crates by the gate", "person:neighbor", "2026-10-24T07:30:00-07:00", "new"),
                       row(7, home, "wonder", "The first frost came early this year", "person:player", "2026-10-24T06:40:00-07:00", "new")],
               "held": [], "elevated": [], "folded": []},
        body: {"as_of": "2026-10-23T17:30:00-07:00", "new": [],
               "held": [row(5, body, "question", "May children come to the work days", "person:member", "2026-10-22T09:00:00-07:00", "held",
                            held={"thread": None, "note": "Kept for the next council", "by": "person:steward"})],
               "elevated": [row(4, body, "defect", "The footbridge rail is loose", "person:steward", "2026-10-22T12:00:00-07:00", "elevated",
                                elevated={"by": "person:steward", "to": body, "why": "Safety", "witness": "person:member", "line": None, "ts": "2026-10-22T12:30:00-07:00"})],
               "folded": []},
        quiet: {"as_of": "2026-10-20T16:10:00-07:00",
                "new": [row(9, quiet, "witness", "Saw the seed boxes delivered to the barn", "person:member", "2026-10-20T15:00:00-07:00", "new")],
                "held": [], "elevated": [], "folded": []},
        room: {"as_of": "2026-10-24T09:02:00-07:00", "new": [], "held": [], "elevated": [],
               "folded": [row(8, room, "witness", "Saw the soup arrive", "person:member", "2026-10-24T09:00:00-07:00", "folded", folded_into="s3" + "0" * 62)]},
    }
    # 6. questions that climb (rfg and escalate), and the ladders they climb
    st["ladders"] = {h: [{"n": 1, "name": "person", "remit": "", "days": 1}, {"n": 2, "name": "cell", "remit": "", "days": 7},
                         {"n": 3, "name": "council", "remit": "", "days": 14}, {"n": 4, "name": "body", "remit": "", "days": 30}]
                     for h in (home, cell, room, body, quiet)}
    st["questions"] = [
        {"id": "q1" + "0" * 62, "type": "escalate", "from_holon": cell, "to": body,
         "question": "Who repairs the hall roof before the gathering", "about": "s1" + "0" * 62, "blast_radius": "cell",
         "rung": {"n": 4, "name": "body"}, "holder": "person:steward", "by": "2026-10-28", "ts": "2026-10-24T08:30:00-07:00",
         "asker": "person:member", "state": "climbed", "closed_by": None, "next": None, "past": [{"n": 2, "name": "cell"}]},
        {"id": "q2" + "0" * 62, "type": "rfg", "from_holon": home, "to": cell,
         "question": "Should the seed swap move to spring", "about": None, "blast_radius": "person",
         "rung": {"n": 2, "name": "cell"}, "holder": "person:steward", "by": "2026-10-30", "ts": "2026-10-23T10:00:00-07:00",
         "asker": "person:player", "state": "open", "closed_by": None, "next": {"n": 3, "name": "council"}, "past": []},
    ]
    st["hud"]["fixture"] = "proposed-b"
    st["_proposed"] = ("Derived from fresh.json by make_fixtures_b.py. Adds fields STATE.md v1 does not carry yet: "
                       "holons[].activity_7d; a holon of kind body; a cell last heard on Tuesday (Cell Five); path.drum {actor, holon}; kept.by_stream[holon][stream]; "
                       "sightings in the per-holon shape with kinds; questions and ladders (STATE.md now declares these three; the fixtures of (a) do not carry them yet).")
    (HERE / "proposed-b.json").write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    print("wrote fixtures/proposed-b.json")
    # the quiet morning: the same holons, nothing owed by the wearer, the chain kept by others
    # (the Map then lights nothing: DESIGN-THE-BAR line 1)
    q = json.loads(json.dumps(st))
    q["owed"]["entries"] = [e for e in q["owed"]["entries"] if e.get("holder") != q["actor"]]
    for c in q["cards"]:
        if c.get("holder") == q["actor"] and c.get("state") not in ("kept", "done"):
            c["state"] = "kept"
    q["deal"]["cards"] = []; q["deal"]["minutes_dealt"] = 0
    q["hud"]["fixture"] = "proposed-b-quiet"
    (HERE / "proposed-b-quiet.json").write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    print("wrote fixtures/proposed-b-quiet.json")

def chain_fixtures():
    """The Chain's three conditions, Calm, Watch and Act, derived from proposed-b.json. The road
    crosses two houses (Cell Two and The Commons) and meets one fixed date from a house not held.
    Proposed fields, read by chain.js and not yet in STATE.md v1: buffers[].trail (earlier fever
    points, oldest first) and path.external (fixed dates from houses not held)."""
    base = json.loads((HERE / "proposed-b.json").read_text())
    by_title = {c["title"]: c for c in base["cards"]}
    choose, book, gathering = by_title["Choose the meeting day"], by_title["Book the hall"], by_title["The autumn gathering"]
    cell, body = choose["holon"], "b0d1e5c0ffee" + "0" * 52
    roof_id, ready_id, ext_id = "r00f" + "0" * 60, "4ead1" + "0" * 59, "e8e7" + "0" * 60
    conditions = {
        # name: (roof state, roof by, roof TF, used, size, done, signal, trail, feeding buffer (used, size, done, signal))
        "calm": ("kept", "2026-10-23", None, 1, 4, 0.4, "green",
                 [("2026-10-17T09:00:00-07:00", 0.0, 0.1), ("2026-10-20T09:00:00-07:00", 0.1, 0.25)], (1, 6, 0.4, "green")),
        # the buffer whole while the next step has no slack of its own (the night test, step 7)
        "untouched": ("kept", "2026-10-23", None, 0, 4, 0.2, "green", [], (1, 6, 0.4, "green")),
        "watch": ("taken", "2026-10-25", -1, 2, 4, 0.3, "yellow",
                  [("2026-10-17T09:00:00-07:00", 0.0, 0.15), ("2026-10-20T09:00:00-07:00", 0.25, 0.25)], (1, 6, 0.2, "green")),
        # the spare days overrun by one: the milestone one day late, as its float and the headline say
        "act": ("taken", "2026-10-22", -2, 5, 4, 0.3, "red",
                [("2026-10-17T09:00:00-07:00", 0.25, 0.2), ("2026-10-20T09:00:00-07:00", 0.5, 0.25)], (2, 6, 0.2, "yellow")),
    }
    for name, (rstate, rby, rtf, used, size, done, signal, trail, feed) in conditions.items():
        st = json.loads(json.dumps(base))
        cards = {c["id"]: c for c in st["cards"]}
        roof = {"id": roof_id, "holon": body, "title": "Repair the hall roof", "kind": "activity", "stream": "The hall",
                "holder": "person:steward", "minutes": 240, "agent_minutes": None, "tokens_estimate": None, "by": rby,
                "stage": "did" if rstate == "kept" else "will", "state": rstate, "predecessors": [],
                "successors": [book["id"], ready_id], "serves": [], "audience": "holon",
                "ES": 0, "EF": 1, "LS": None if rtf is None else rtf, "LF": None if rtf is None else 1 + rtf,
                "TF": rtf, "FF": 0, "critical": rtf is not None, "system_critical": rtf is not None, "variance_days": None}
        ready = {"id": ready_id, "holon": body, "title": "The hall ready for winter", "kind": "milestone", "stream": "The hall",
                 "holder": "person:steward", "minutes": 0, "agent_minutes": None, "tokens_estimate": None, "by": "2026-11-15",
                 "stage": "will", "state": "ready", "predecessors": [roof_id], "successors": [], "serves": [], "audience": "holon",
                 "ES": 1, "EF": 1, "LS": 22, "LF": 22, "TF": 21, "FF": 21, "critical": False, "system_critical": False, "variance_days": None}
        st["cards"] += [roof, ready]
        b = cards[book["id"]]
        b["predecessors"] = [choose["id"], roof_id]
        if rtf is not None:
            b["ES"], b["EF"] = 1 - rtf, 2 - rtf
            b["TF"] = rtf
            # the buffer absorbs lateness until it is nearly spent: the milestone is late only in Act
            cards[gathering["id"]]["TF"] = -(used - size) if used > size else 0
            cards[choose["id"]]["TF"] = 0
        system = ([roof_id] if rtf is not None else []) + [choose["id"], book["id"], gathering["id"]]
        st["path"]["critical"] = sorted(set(st["path"]["critical"]) | set(system))
        st["path"]["system"] = system
        st["path"]["external"] = [{"id": ext_id, "title": "The parish opens the hall's bookings", "house": "The parish",
                                   "date": "2026-10-26", "before": book["id"]}]
        share = used / size
        st["buffers"] = [
            {"milestone": gathering["id"], "holon": cell, "title": gathering["title"], "type": "project",
             "size_days": size, "consumed_days": used, "consumed_share": share, "chain_complete": done, "signal": signal,
             "trail": [{"ts": ts, "consumed_share": c, "chain_complete": d} for ts, c, d in trail]},
            {"milestone": ready_id, "holon": body, "title": "The hall ready for winter", "type": "feeding",
             "size_days": feed[1], "consumed_days": feed[0], "consumed_share": feed[0] / feed[1], "chain_complete": feed[2], "signal": feed[3]},
        ]
        st["hud"]["fixture"] = "chain-" + name
        st["_proposed"] = base.get("_proposed", "") + " The Chain's conditions add buffers[].trail and path.external (proposed)."
        (HERE / f"chain-{name}.json").write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote fixtures/chain-{name}.json")


if __name__ == "__main__":
    main()
    chain_fixtures()
