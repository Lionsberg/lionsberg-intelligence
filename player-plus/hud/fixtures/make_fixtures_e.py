#!/usr/bin/env python3
"""make_fixtures_e.py: the fixtures for the Bodies view (DESIGN-BODIES.md).

It reads fixtures/fresh.json (written by make_fixtures.py) and adds
ONLY the fields the Bodies view asks of the state that STATE.md v1 does not yet carry:
`bodies`, `desk` and `cost` (DESIGN-BODIES §11.2, for the engine to fold), the server's
live block `hud.bodies_live` (§11.3, read by serve.py on the machine, never in the record),
and two proposed card fields for the launch sheet (`agent_minutes`, `tokens_estimate`). Every
added field is listed in `_proposed`. `cost` follows STATE.md's shape (day with its total, week,
ceiling, limits); the live block keeps its own reading of the plan's usage as the fallback. Fold these into make_fixtures.py when the engine lands
them; until then (a)'s fixtures show "Not computed yet" on the Bodies view.

One fixture per state of DESIGN-BODIES §2.5, plus a busy day and the honest absence:

    bodies-none        no clones: the prime alone, turning by its own lines
    bodies-three       three bodies at work while the person talks with the prime; one handoff waits
    bodies-well        all well: three bodies at work, nothing waits, the week under the person's line
    bodies-quiet       a body gone quiet, its process alive
    bodies-stale       a stale claim: the process gone, the claim still standing
    bodies-day         a handoff unreviewed for a day; a body past a day
    bodies-asleep      the prime asleep, read from the phone while the computer sleeps
    bodies-morning     the morning after: slept at 23:10, woke at 07:02
    bodies-unheld      no body holds the desk
    bodies-collision   two claims on the desk
    bodies-offline     the day's lines from what is held, with no live reading of the machine
    bodies-missing     the engine has not folded bodies yet: "Not computed yet."

    python3 fixtures/make_fixtures_e.py
"""
import copy
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DAY = "2026-10-24"
PRIME = "agent:player-agent"


def ts(hm, day=DAY):
    return f"{day}T{hm}:00-07:00"


def line_id(n):
    return f"{n:02x}" * 32


def body(name, actor, kind, state, task=None, first_word=None, claimed=None, newest=None,
         review_min=None, handoff=None, reviewed=None, cost=0, readers=0, age=0.0, flags=(),
         lines_30m=0, lines_1h=None, host="this machine", why=None, home=None, reviewed_at=None):
    b = {"name": name, "actor": actor, "kind": kind, "state": state, "task": task,
         "first_word": first_word, "brief": None if kind == "prime" else line_id(len(name)),
         "host": host, "claimed_at": claimed, "newest_line": newest, "review_min": review_min,
         "handoff": handoff, "reviewed": reviewed, "reviewed_at": reviewed_at, "cost_tokens": cost,
         "readers": readers, "affirmed_by": None if kind == "prime" else PRIME,
         "delegation_live": True, "age_hours": age, "flags": list(flags), "lines_30m": lines_30m,
         "holon": home}
    if lines_1h is not None:
        b["lines_1h"] = lines_1h
    if why:
        b["why"] = why
    return b


def live(actor, name, process, newest, writes):
    return {"actor": actor, "name": name, "process": process, "newest_write": newest,
            "writes_30m": writes, "markers": []}


def base():
    st = json.loads((HERE / "fresh.json").read_text())
    home = st["holons"][0]["id"]
    for c in st["cards"]:
        if c["title"] == "Write to the new members":
            c["agent_minutes"] = 120           # proposed: your agent's own estimate of its work
            c["tokens_estimate"] = 2000000     # proposed: and of its cost
            st["_launch_card"] = c["id"]
    st["_proposed"] = sorted(set(st.get("_proposed", [])) | {
        "bodies", "desk", "cost", "hud.bodies_live", "cards[].agent_minutes", "cards[].tokens_estimate"})
    return st, home


def prime(home, **kw):
    d = dict(name="the prime", actor=PRIME, kind="prime", state="working", task="the desk and The Deal",
             claimed=ts("07:02"), newest=ts("14:12"), cost=640000, age=7.2, lines_30m=3, lines_1h=6, home=home)
    d.update(kw)
    return body(**d)


def heartbeat(last, slept=(), stopped=(), asleep=None):
    hb = {"last": last, "slept": [{"from": a, "to": b} for a, b in slept],
          "stopped": [{"from": a, "to": b} for a, b in stopped]}
    if asleep:
        hb["asleep"] = {"from": asleep}
    return hb


USAGE = {"five_hour": {"used_pct": 39, "resets_at": ts("15:30")},
         "seven_day": {"used_pct": 62, "resets_at": "2026-10-28T08:00:00-07:00"}, "as_of": ts("14:15")}


def desk(holder, since, claims=None, collision=False):
    return {"holder": holder, "since": since,
            "claims": claims if claims is not None else ([{"actor": holder, "at": since, "live": True}] if holder else []),
            "collision": collision}


def cost(by_body, sessions, by_model, unattributed=0, lines=1214, as_of=ts("14:16"), money=None, ceiling=None,
         week_tokens=None, limits=None):
    """STATE.md's `cost`: the day (with its total), the week's total, the ceiling, and the plan's
    limits as the engine reads them from the machine's status file (bodies.limits)."""
    total = sum(by_body.values()) + unattributed
    c = {"day": {"tokens": total, "by_body": by_body, "by_session": sessions, "by_model": by_model,
                 "unattributed": unattributed, "route_lines": lines, "as_of": as_of, "date": as_of[:10]},
         "ceiling": ceiling, "limits": limits}
    c["by_body"], c["by_session"], c["by_model"] = by_body, sessions, by_model
    if week_tokens is not None:
        c["week"] = {"tokens": week_tokens, "as_of": as_of}
    if money:
        c["day"]["money"] = money
    return c


def limits(seven, five, r7="2026-10-28T08:00:00-07:00", r5=None, as_of=None):
    return {"seven_day_used_pct": seven, "five_hour_used_pct": five,
            "resets_at": {"seven_day": r7, "five_hour": r5 or ts("15:30")}, "ceiling_pct": None,
            "source": "statusline-last.json", "as_of": as_of or ts("14:15")}


CEILING = {"day_tokens": 6000000, "seven_day_pct": 85, "set_by": "person:player"}


def write(name, st, now):
    st["hud"]["now"] = now
    st["hud"]["fixture"] = name
    (HERE / f"{name}.json").write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")
    print("wrote", name)


def main():
    S, home = base()
    survey, rewrite, index = (f"{PRIME}.survey", f"{PRIME}.rewrite", f"{PRIME}.index")

    # ---------------------------------------------------------------- no clones
    st = copy.deepcopy(S)
    st["bodies"] = [prime(home)]
    st["desk"] = desk(PRIME, ts("07:02"))
    st["cost"] = cost({PRIME: 640000}, [{"session": "c-0702", "body": PRIME, "tokens": 640000, "first": ts("07:02"), "last": ts("14:12")}],
                      {"large model": 410000, "small model": 230000}, lines=212, ceiling=CEILING,
                      week_tokens=14200000, limits=limits(41, 12))
    st["hud"]["bodies_live"] = {"as_of": ts("14:16"), "host": "this machine",
                                "bodies": [], "desk": {"process": "alive", "since": ts("07:02")},
                                "heartbeat": heartbeat(ts("14:15"), slept=[(ts("23:10", "2026-10-23"), ts("07:02"))]),
                                "usage": USAGE}
    write("bodies-none", st, ts("14:16"))

    # ---------------------------------------------------------------- three at work (the busy day)
    handoff = line_id(0xa1)
    three = copy.deepcopy(S)
    three["bodies"] = [
        prime(home),
        body("Survey", survey, "clone", "working", "the reading on rooms",
             "I will read the five room products and bring back what each gives a room, with its source, by this evening.",
             ts("11:06"), ts("14:12"), cost=1400000, readers=30, age=3.2, lines_30m=2, home=home),
        body("Rewrite", rewrite, "clone", "working", "the welcome letter, plainer",
             "I will rewrite the welcome letter in plain words and keep every commitment it makes.",
             ts("09:40"), ts("13:06"), cost=380000, readers=4, age=4.6, lines_30m=0, home=home),
        body("Index", index, "clone", "handoff", "the seed packets, sorted by season",
             "I will sort the seed packet notes by season and say which are missing a date.",
             ts("08:10"), ts("13:58"), review_min=7, handoff=handoff, cost=520000, readers=6, age=6.1, home=home),
    ]
    three["lines"] = three.get("lines", []) + [{
        "id": handoff, "ts": ts("13:58"), "actor": index, "for": "person:player", "holon": home, "type": "body",
        "body": {"name": "Index", "state": "handoff", "task": "the seed packets, sorted by season", "review_min": 7},
        "links": {}, "audience": "holon", "reason": "agent", "verified": "signed"}]
    three["desk"] = desk(PRIME, ts("07:02"))
    three["cost"] = cost(
        {PRIME: 640000, survey: 1400000, rewrite: 380000, index: 520000},
        [{"session": "c-0702", "body": PRIME, "tokens": 520000, "first": ts("07:02"), "last": ts("12:30")},
         {"session": "c-1240", "body": PRIME, "tokens": 120000, "first": ts("12:40"), "last": ts("14:12")},
         {"session": "c-1106", "body": survey, "tokens": 1400000, "first": ts("11:06"), "last": ts("14:12")},
         {"session": "c-0940", "body": rewrite, "tokens": 380000, "first": ts("09:40"), "last": ts("13:06")},
         {"session": "c-0810", "body": index, "tokens": 520000, "first": ts("08:10"), "last": ts("13:58")}],
        {"large model": 1950000, "middle model": 760000, "small model": 230000}, unattributed=40000,
        money={"by_body": {PRIME: 1.9, survey: 4.2, rewrite: 1.1, index: 1.6}, "unit": "dollars"},
        ceiling=CEILING, week_tokens=21000000, limits=limits(62, 39))
    three["hud"]["bodies_live"] = {
        "as_of": ts("14:16"), "host": "this machine",
        "bodies": [live(survey, "survey", "alive", ts("14:15"), 9), live(rewrite, "rewrite", "alive", ts("13:06"), 0),
                   live(index, "index", "alive", ts("13:58"), 1)],
        "desk": {"process": "alive", "since": ts("07:02")},
        "heartbeat": heartbeat(ts("14:15"), slept=[(ts("23:10", "2026-10-23"), ts("07:02")), (ts("12:31"), ts("12:39"))]),
        "usage": USAGE}
    write("bodies-three", three, ts("14:16"))

    # ---------------------------------------------------------------- all well: three at work, nothing waits
    st = copy.deepcopy(three)
    for b in st["bodies"]:
        if b["name"] == "Index":
            b["state"] = "working"; b["handoff"] = None; b["review_min"] = None; b["newest_line"] = ts("14:09"); b["lines_30m"] = 1
        if b["name"] == "Rewrite":
            b["newest_line"] = ts("14:02"); b["lines_30m"] = 1
    st["hud"]["bodies_live"]["bodies"] = [live(survey, "survey", "alive", ts("14:15"), 9), live(rewrite, "rewrite", "alive", ts("14:02"), 2),
                                          live(index, "index", "alive", ts("14:09"), 4)]
    st["cost"]["limits"] = limits(36, 22)
    write("bodies-well", st, ts("14:16"))

    # ---------------------------------------------------------------- quiet
    st = copy.deepcopy(three)
    st["bodies"] = [b for b in st["bodies"] if b["name"] in ("the prime", "Rewrite")]
    st["bodies"][1]["newest_line"] = ts("13:06")
    st["hud"]["bodies_live"]["bodies"] = [live(rewrite, "rewrite", "alive", ts("13:06"), 0)]
    write("bodies-quiet", st, ts("14:16"))

    # ---------------------------------------------------------------- stale claim
    st = copy.deepcopy(three)
    for b in st["bodies"]:
        if b["name"] == "Survey":
            b["state"] = "stale"; b["flags"] = ["stale"]; b["newest_line"] = ts("11:42"); b["lines_30m"] = 0
            b["review_min"] = 5; b["handoff"] = line_id(0xb2)
    st["hud"]["bodies_live"]["bodies"][0] = live(survey, "survey", "gone", ts("11:42"), 0)
    st["hud"]["bodies_live"]["bodies"][0]["ended_at"] = ts("11:42")
    write("bodies-stale", st, ts("14:16"))

    # ---------------------------------------------------------------- a handoff a day old; a body past a day
    st = copy.deepcopy(three)
    for b in st["bodies"]:
        if b["name"] == "Index":
            b["newest_line"] = ts("13:58", "2026-10-23"); b["claimed_at"] = ts("08:10", "2026-10-23"); b["age_hours"] = 30.1
            b["flags"] = ["handoff_day"]
        if b["name"] == "Survey":
            b["claimed_at"] = ts("11:06", "2026-10-23"); b["age_hours"] = 27.2; b["flags"] = ["past_day"]
    st["lines"][-1]["ts"] = ts("13:58", "2026-10-23")
    write("bodies-day", st, ts("14:16"))

    # ---------------------------------------------------------------- the prime asleep (read from the phone)
    st = copy.deepcopy(three)
    late = "2026-10-24"
    for b in st["bodies"]:
        b["lines_30m"] = 0
        if b["kind"] == "prime":
            b["lines_1h"] = 0
    st["hud"]["bodies_live"]["heartbeat"] = heartbeat(ts("23:10", late), slept=[(ts("23:10", "2026-10-23"), ts("07:02"))], asleep=ts("23:10", late))
    for lb in st["hud"]["bodies_live"]["bodies"]:
        lb["writes_30m"] = 0
    write("bodies-asleep", st, "2026-10-25T06:40:00-07:00")

    # ---------------------------------------------------------------- the morning after
    st = copy.deepcopy(S)
    D2 = "2026-10-25"
    st["bodies"] = [prime(home, claimed=ts("07:02", D2), newest=ts("07:40", D2), age=0.7, cost=90000, lines_30m=1, lines_1h=2),
                    body("Survey", survey, "clone", "hold", "the reading on rooms",
                         "I will read the five room products and bring back what each gives a room, with its source, by this evening.",
                         ts("11:06"), ts("22:31"), cost=0, readers=0, age=20.7, home=home,
                         why="resumes Monday · waiting on the keeper's word")]
    st["desk"] = desk(PRIME, ts("22:40"))
    st["cost"] = cost({PRIME: 90000}, [{"session": "c-0702b", "body": PRIME, "tokens": 90000, "first": ts("07:02", D2), "last": ts("07:40", D2)}],
                      {"large model": 90000}, lines=40, as_of=ts("07:44", D2), ceiling=CEILING,
                      week_tokens=21300000, limits=limits(64, 3, r5=ts("12:00", D2), as_of=ts("07:43", D2)))
    st["hud"]["bodies_live"] = {"as_of": ts("07:44", D2), "host": "this machine",
                                "bodies": [live(survey, "survey", None, ts("22:31"), 0)],
                                "desk": {"process": "alive", "since": ts("22:40")},
                                "heartbeat": heartbeat(ts("07:43", D2), slept=[(ts("23:10"), ts("07:02", D2))]),
                                "usage": {"five_hour": {"used_pct": 3, "resets_at": ts("12:00", D2)},
                                          "seven_day": {"used_pct": 64, "resets_at": "2026-10-28T08:00:00-07:00"}, "as_of": ts("07:43", D2)}}
    st["bodies_closeout"] = {"at": ts("22:40"), "at_rest": True}
    write("bodies-morning", st, ts("07:44", D2))

    # ---------------------------------------------------------------- the desk unheld
    st = copy.deepcopy(three)
    st["desk"] = desk(None, None, claims=[])
    st["hud"]["bodies_live"]["desk"] = None
    write("bodies-unheld", st, ts("14:16"))

    # ---------------------------------------------------------------- two claims on the desk
    st = copy.deepcopy(three)
    st["desk"] = desk(PRIME, ts("07:02"), claims=[{"actor": PRIME, "at": ts("07:02"), "live": True},
                                                  {"actor": rewrite, "at": ts("13:20"), "live": True}], collision=True)
    write("bodies-collision", st, ts("14:16"))

    # ---------------------------------------------------------------- offline: no live reading
    st = copy.deepcopy(three)
    del st["hud"]["bodies_live"]
    write("bodies-offline", st, ts("14:16"))

    # ---------------------------------------------------------------- the engine has not folded bodies
    st = copy.deepcopy(S)
    write("bodies-missing", st, ts("14:16"))


if __name__ == "__main__":
    main()
