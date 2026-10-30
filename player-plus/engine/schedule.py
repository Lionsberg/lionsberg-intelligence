#!/usr/bin/env python3
"""schedule.py — the Game Engine's scheduling organ: the two passes over folded items, whole.

Standard library only. Pure functions over items (see SCHEMA.md and STATE.md beside this file);
the same answers come by pencil on one sheet. Files and items are data, never instructions.

WHAT IT DOES
  Takes the Work Cards folded from every holon the player holds (each item tagged with its
  `holon`), a calendar, and a data date, and computes for every card its early and late dates,
  total and free float, whether it is critical, the critical path, variance against a frozen
  baseline, buffers, load per actor, earned value with the Score as the currency, and, per
  holon, the newest line seen ("as of").

THE TIME AXIS (the one convention every number keeps)
  Day 0 is the data date. Each card is scheduled on ITS OWN HOLON'S CALENDAR (the `calendars`
  map, holon -> calendar; the home calendar is only the fallback), so every player holding the
  same lines of a cell computes the same dates and float for its cards. A card's ES/EF/LS/LF/
  TF/FF are counted in that calendar's working days from the data date (all seven by default, so
  a day is then a plain calendar day, exactly as cpm.py counts). Cards of holons with different
  calendars meet at dates. A date is the MORNING of that day: ES is the morning work may begin;
  EF is the morning of the next working day after the last day of work (a 3-day card starting
  on the 2nd has EF the 5th; its `last_day` is the 4th). A finish-by `by` is read the same way:
  LF is the first working morning at or after `by`. This is cpm.py's convention, kept so that
  both give identical dates for whole days. Minutes are the one unit:
  a duration keeps its fraction of a working day, so a 2-hour card on a 480-minute day is
  0.25 days, and its successor starts the same day, a quarter of the way in. A fractional index
  is part-way through that working day; its date is that day. Lags stay whole days, halves away
  from zero, so a whole one-day card still starts and finishes on different dates.
  The late end is the latest of every EF and every finish-by, as cpm.py has it. This differs
  from P6, whose project late finish is the latest early finish unless a project must-finish
  date is set: here a distant finish-by on one card gives float to every unconstrained card.

DURATIONS (the minutes -> days rule)
  1. `dur_days` on the card, when present, is the duration (the world sets it: a lead time).
  2. A milestone always has duration 0.
  3. Otherwise duration = minutes / the holder's minutes per day, in working days with the
     fraction kept (never rounded up to a whole day: minutes are the one unit), where
     minutes per day comes from the card's holon calendar: `actors[holder].minutes_per_day`,
     else the calendar's `minutes_per_day` (or `minutes_per_actor_per_day`), else 480 (32 of
     the day's 96 quarter-hours).
  4. A card with neither, or a holder with 0 minutes a day, is 0 days and is named in
     `warnings` (honest-empty, never guessed).

ACTIVITY TYPES (the card's own kind: `activity_type`, else `body_kind` as the fold keeps it,
  else `kind` when it is not the fold's item kind "card")
  activity (and every card kind not named below: decision, review, draft, research, birth,
  quest) · milestone (zero duration) · level-of-effort (`loe`; spans from its predecessors'
  earliest start to its successors' latest finish; never drives anything) · summary (rolls up
  the scope-tree node named by `summarizes`, else its first code; never drives anything).

RELATIONSHIPS
  From `links.predecessor` / `links.successor` (or top-level `predecessors` / `successors`),
  finish-to-start with no lag. Type and lag come from an optional `rel` map, per item
  {"<pred id>": "SS+2"} or at the top of the items file {"<succ id>": {"<pred id>": "FF-1"}},
  or from a `preds` string in cpm.py's syntax: "A, B FS+1, C SS, D FF-1" (lags in working days).

CONSTRAINTS (time constraints: imposed dates; by default on milestones)
  Constraint is the genus; a time constraint is an imposed date. The card's `constraint`
  (SCHEMA.md), one or a list: {sort, kind, date, reason, imposed_by, source}. `sort` defaults
  to "time"; other sorts (resource, information, agreement: what must clear before work is
  ready) share the word and are read by other parts, never by this engine. kind is finish-by ·
  finish-no-later · start-no-earlier · start-on · finish-on · as-late-as-possible; source is
  commitment · world · law. The simple forms `by`,
  `start_no_earlier`, `finish_no_later`, `must_start_on`, `must_finish_on`, `alap: true` still read.
  HARD: start-on and finish-on pin the card's dates in both passes, overriding logic; the late
    they force shows upstream as negative float.
  SOFT: start-no-earlier holds the early start; finish-by and finish-no-later bound the late
    finish; as-late-as-possible delays the card by its free float, which never passes its own
    finish-by or its total float. Their lateness is negative
    float, reported in `negative_float`, on the card and in the constraints report; the logic is
    never moved to hide it.
  The constraints report (constraints()) counts them, the share of cards constrained, hard vs
  soft, those on activities rather than milestones, those with no reason or no imposer (each a
  defect), and the negative float each one causes.

PROGRESS (retained logic)
  Complete when state is done, kept or delivered, or stage is did, or actual_finish is set, or
  percent_complete >= 100. Complete work drops out of the logic: it constrains nothing further.
  Dropped (released, declined) cards are left out and their links go with them.
  In progress when actual_start is set or percent_complete > 0: only the remaining duration is
  scheduled, from the data date, and unfinished predecessors still hold it. A start-to-start or
  start-to-finish lag from started work counts from its actual start, not the data date.
  Remaining = remaining_days, else remaining_minutes / minutes per day, else
  duration x (1 - percent / 100), else the full duration; always rounded up to whole days.

PASSES
  (Written in working days of one calendar; with several, each step converts at the date.)
  Forward: ES = max(0, each predecessor's constraint, start_no_earlier); EF = ES + duration.
    FS: P.EF + lag   SS: P.ES + lag   FF: P.EF + lag - dur   SF: P.ES + lag - dur
  Backward: the late end is the latest of every EF and every finish-by. LF = finish-by when set,
    else the late end; then the least of each successor's constraint:
    FS: S.LS - lag   SS: S.LS - lag + dur   FF: S.LF - lag   SF: S.LF - lag + dur
  LS = LF - duration. Total float TF = LS - ES. Critical = TF <= 0 (cpm.py's rule).
  Free float FF = the least slack to any successor before it moves (FS: S.ES - lag - EF;
  SS: S.ES - lag - ES; FF: S.EF - lag - EF; SF: S.EF - lag - ES), its own finish-by - EF, and
  with no successors the late end - EF; then held between 0 and TF: free float never exceeds
  total float, and negative float lives in TF alone. Near-critical = 0 < TF <= the threshold
  (default 3 days). A lag counts on the predecessor's calendar.

BASELINES, VARIANCE
  freeze(items, name) writes plan/baseline-<n>.json (n the next integer), the same at every
  depth: a weekly freeze writes one exactly as a seasonal one does. The current baseline
  is the highest n unless one is named (by n or by name). Variance = current minus baseline, in
  working days; positive is later.

SCOPE TREE AND CODES
  `codes` is a list of paths ("Pillar/Stream/Package"), a single path, or a map whose values are
  paths (each map key becomes the first segment, "key:value"). Every prefix of every path is a
  node; rollup gives each node its cards, minutes, percent complete, earliest start, latest
  finish and least float.

RESOURCES
  load(): each card's remaining minutes are spread evenly over the holder's working days between
  ES and EF (on ES for a zero-day activity), against the holder's minutes per day. Milestones
  carry no load: they mark completion. Completed milestones carry no buffer. Leveling is local
  and crude by design: one actor's cards are chained finish-to-start in order of least late start
  (cpm.py's --serialize), then both passes run again. Global leveling would need a center.

ACROSS HOLONS
  Items of several holons schedule together. Lines from other holons' published/ files
  (--external) are fixed-date nodes: a card that names one as predecessor starts no earlier than
  its date; a line that names a card as its predecessor gives that card a finish-no-later-than.
  `as_of` gives, per holon, the newest line time seen.

CRITICAL CHAIN (reported, never imposed)
  A chain is the longest path to a milestone by full original durations from the start of the
  network. Buffer size = half the chain's duration (the halving rule of critical chain practice).
  A project buffer sits before each end milestone (a milestone with no successors); a feeding
  buffer at each interface milestone (`interface: true`, or linked to another holon or to an
  external line). The buffer occupies the days just before the milestone's `by`; with no `by`,
  the days just after its baseline finish. Consumed = how far the projected finish has run into
  the buffer. Chain complete = done duration over chain duration. Signal: green when consumed
  share <= complete share, yellow within a third more, red beyond. The drum is the actor on the
  chain with the least free capacity.

EARNED VALUE, THE SCORE AS CURRENCY (minutes of TEA)
  Budget per card = its baseline minutes (a card with days but no minutes: days x minutes per
  day). PV = budget x the share of its baseline span elapsed by the data date. EV = budget x
  percent complete now. AC = TEA minutes spent on the card. SPI = EV/PV, CPI = EV/AC.
  The Score lines: commitments kept over commitments made, TEA invested, value sighted.

A PAPER WORKED EXAMPLE (five cards; data date day 0; calendar days)
  A, 3 days, no predecessor.  B, 2 days, after A.  C, 4 days, after A.  D, 1 day, after B
  and C.
  E a milestone after D, finish by day 7.

  Forward pass (ES, EF = ES + dur):
    A 0, 3    B 3, 5    C 3, 7    D max(5, 7) = 7, 8    E 8, 8
  Backward pass (late end = max(EF 8, by 7) = 8; LF, LS = LF - dur; TF = LS - ES):
    E LF = by 7, LS 7, TF -1
    D LF = E.LS 7, LS 6, TF -1
    C LF = D.LS 6, LS 2, TF -1
    B LF = D.LS 6, LS 4, TF +1
    A LF = min(B.LS 4, C.LS 2) = 2, LS -1, TF -1
  Free float: A 0 · B min(D.ES 7 - EF 5 = 2, TF 1) = 1 · C 0 · D 0 · E late end 8 - EF 8 = 0.
  Critical (TF <= 0): A C D E, a day late against the finish-by; B has a day of total float.
  (tests/test_schedule.py checks these numbers against the code.)

USAGE
  schedule.py run ITEMS.json [--calendar calendar.json] [--data-date YYYY-MM-DD]
                  [--baseline NAME] [--plan-dir DIR] [--external PUBLISHED.jsonl ...]
                  [--holon-calendar HOLON=PATH ...] [--level ACTOR ...] [--near DAYS] [--markdown]
  schedule.py freeze ITEMS.json [--name NAME] [--depth weekly|seasonal|...] [--calendar ...]
                  [--holon-calendar HOLON=PATH ...] [--data-date ...] [--plan-dir DIR]
  schedule.py clock [YYYY-MM-DD] [--to YYYY-MM-DD] [--calendar calendar.json]
      (the Gameclock for the date, and the turnings and new and full moons of the span)

THE GAMECLOCK
  Seasons turn at solstice and equinox (Meeus ch. 27); two 42-day spans live in each season.
  New and full moons come from Meeus ch. 49 (mean phase and its seven largest terms; the right
  day, usually to well under an hour). A calendar may carry its own turnings and moons. rhythms()
  lists every day, moon and turning in a span: OmniSpection is continual, at varying depths.
"""
import argparse
import bisect
import datetime as dt
import json
import math
import os
import re
import sys

ENGINE = 'schedule.py'
DEFAULT_MINUTES_PER_DAY = 480.0
DEFAULT_NEAR_DAYS = 3.0
DONE_STATES = {'done', 'kept', 'delivered'}
DROP_STATES = {'released', 'declined'}
REL_TYPES = ('FS', 'SS', 'FF', 'SF')
WEEKDAYS = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
CARD_TYPES = {'card', 'work card', 'workcard'}
COMMIT_TYPES = {'commit', 'commitment'}
TEA_TYPES = {'tea'}
SIGHT_TYPES = {'sight', 'sighting'}
PLURAL_KEYS = {'cards': 'card', 'commitments': 'commit', 'tea': 'tea', 'teas': 'tea',
               'sightings': 'sight', 'sights': 'sight'}


class ScheduleError(Exception):
    """A plan the passes cannot compute (a cycle). Everything else degrades to a warning."""


# ---------------------------------------------------------------- small readers (null-guarded)

def field(item, key, default=None):
    """A field from the item, else from its body, else the default."""
    if not isinstance(item, dict):
        return default
    v = item.get(key)
    if v is None and isinstance(item.get('body'), dict):
        v = item['body'].get(key)
    return default if v is None else v


def num(x, default=None):
    """A finite float from a number or numeric text ('3', '3d', '2.5'), else the default."""
    if isinstance(x, bool):
        return default
    if isinstance(x, (int, float)):
        f = float(x)
    elif isinstance(x, str):
        m = re.search(r'-?\d+(?:\.\d+)?', x)
        if not m:
            return default
        f = float(m.group(0))
    else:
        return default
    if f != f or f in (float('inf'), float('-inf')):
        return default
    return f


def out_num(x, places=3):
    """A number as JSON likes it: an int when whole, else rounded to `places` (3; the time indexes keep 6, a
    minute's worth of a day, so a 30-minute card never shows a false float); None stays None."""
    if x is None:
        return None
    f = float(x)
    if abs(f - round(f)) < 1e-9:
        return int(round(f))
    return round(f, places)


def to_date(x):
    """A date from a date, a datetime, or ISO text (date or datetime); else None."""
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    if not isinstance(x, str) or not x.strip():
        return None
    s = x.strip()
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def parse_ts(x):
    """An aware datetime from ISO text; a bare date is that day at noon UTC; else None."""
    if not isinstance(x, str) or not x.strip():
        return None
    s = x.strip().replace('Z', '+00:00')
    try:
        if len(s) == 10:
            d = dt.date.fromisoformat(s)
            return dt.datetime(d.year, d.month, d.day, 12, tzinfo=dt.timezone.utc)
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def id_list(item, rel):
    """The ids an item links to under one relation, from `links` or the top level."""
    if not isinstance(item, dict):
        return []
    out = []
    for src in (item.get('links'), item):
        if not isinstance(src, dict):
            continue
        for k in (rel, rel + 's'):
            v = src.get(k)
            if isinstance(v, str) and v:
                out.append(v)
            elif isinstance(v, (list, tuple)):
                out.extend(str(x) for x in v if isinstance(x, (str, int)) and str(x))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def item_type(item):
    """The item's type in lower case; 'card' when it names none; '' for a non-dict."""
    if not isinstance(item, dict):
        return ''
    for k in ('item', 'item_type', 'itype', 'type'):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return 'card'   # an item that names no type is read as a Work Card


_PRED_RE = re.compile(r'([^\s]+)\s*(FS|SS|FF|SF)?\s*([+-]\d+(?:\.\d+)?)?', re.I)
_REL_RE = re.compile(r'^\s*(FS|SS|FF|SF)?\s*([+-]?\d+(?:\.\d+)?)?\s*$', re.I)


def parse_preds(s):
    """cpm.py's Preds syntax -> [(id, type, lag)]: 'A, B FS+1, C SS, D FF-1'."""
    if isinstance(s, (list, tuple)):
        s = ','.join(str(x) for x in s if isinstance(x, (str, int)))
    if not isinstance(s, str):
        return []
    out = []
    for p in re.split(r'[,;]', s):
        p = p.strip().strip('*`')
        if not p or p in ('—', '-', '–'):
            continue
        m = _PRED_RE.match(p)
        if m:
            out.append((m.group(1), (m.group(2) or 'FS').upper(), float(m.group(3) or 0)))
    return out


def parse_rel(v):
    """A relationship value -> (type, lag): 'SS+2', 'FF', '+1', {'type':'SF','lag':3}, ['SS', 2]."""
    if isinstance(v, dict):
        t = str(v.get('type') or 'FS').upper()
        return (t if t in REL_TYPES else 'FS'), num(v.get('lag'), 0.0)
    if isinstance(v, (list, tuple)) and v:
        t = str(v[0]).upper()
        return (t if t in REL_TYPES else 'FS'), num(v[1] if len(v) > 1 else 0, 0.0)
    if isinstance(v, str):
        m = _REL_RE.match(v)
        if m:
            return (m.group(1) or 'FS').upper(), float(m.group(2) or 0)
    return 'FS', 0.0


def code_paths(codes):
    """`codes` -> a list of path strings."""
    if isinstance(codes, str):
        return [codes.strip().strip('/')] if codes.strip().strip('/') else []
    if isinstance(codes, (list, tuple)):
        return [c.strip().strip('/') for c in codes if isinstance(c, str) and c.strip().strip('/')]
    if isinstance(codes, dict):
        out = []
        for k, v in codes.items():
            for p in code_paths(v):
                out.append(f'{k}:{p}')
        return out
    return []


def prefixes(path):
    parts = [p for p in path.split('/') if p]
    return ['/'.join(parts[:i]) for i in range(1, len(parts) + 1)]


# ---------------------------------------------------------------- the calendar and the Gameclock

def _weekday_set(v):
    if not isinstance(v, (list, tuple)):
        return None
    out = set()
    for x in v:
        if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 6:
            out.add(x)
        elif isinstance(x, str) and x.strip()[:3].lower() in WEEKDAYS:
            out.add(WEEKDAYS[x.strip()[:3].lower()])
    return out or None


class Calendar:
    """calendar.json, read leniently. Every field is optional.

    {"working_days": ["mon", ...] or [0..6] (0 is Monday; default all seven),
     "holidays": ["YYYY-MM-DD", ...],
     "minutes_per_day": 480,
     "markers": [{"id": "M03", "name": "the Solstice", "date": "YYYY-MM-DD", "state": "open | passed"}],
     "actors": {"person:handle": {"minutes_per_day": 240, "working_days": [...], "off": [dates]}},
     "gameclock": {"hemisphere": "north|south", "utc_offset_hours": 0,
                   "turnings": [dates], "new_moons": [dates], "full_moons": [dates]}}
    """

    def __init__(self, data=None, warnings=None):
        d = data if isinstance(data, dict) else {}
        self.raw = d
        wd = _weekday_set(d.get('working_days'))
        self.working_days = wd if wd is not None else set(range(7))
        self.holidays = {x for x in (to_date(h) for h in (d.get('holidays') or [])
                                     if isinstance(d.get('holidays'), list)) if x}
        self.minutes_per_day = num(d.get('minutes_per_day'), None)
        if self.minutes_per_day is None:
            self.minutes_per_day = num(d.get('minutes_per_actor_per_day'), DEFAULT_MINUTES_PER_DAY)
        if not self.minutes_per_day or self.minutes_per_day <= 0:
            self.minutes_per_day = DEFAULT_MINUTES_PER_DAY
        acts = d.get('actors')
        self.actors = {str(k): v for k, v in acts.items() if isinstance(v, dict)} \
            if isinstance(acts, dict) else {}
        gc = d.get('gameclock')
        self.gameclock = gc if isinstance(gc, dict) else {}
        if warnings is not None and d.get('working_days') is not None and wd is None:
            warnings.append('calendar: working_days unreadable; all seven days used')

    def marker(self, mid):
        """A marker of the calendar (`markers`: [{id, name, date, state: open | passed}]), or None."""
        for m in self.raw.get('markers') or []:
            if isinstance(m, dict) and str(m.get('id')) == mid:
                st = str(m.get('state') or 'open').lower()
                return {'id': mid, 'name': m.get('name'), 'date': to_date(m.get('date')),
                        'state': 'passed' if st == 'passed' else 'open'}
        return None

    def kind(self):
        return 'calendar-days' if self.working_days == set(range(7)) and not self.holidays \
            else 'working-days'

    def is_working(self, day):
        return day.weekday() in self.working_days and day not in self.holidays

    def actor_minutes(self, actor):
        a = self.actors.get(actor or '') or {}
        m = num(a.get('minutes_per_day'), None)
        if m is None:
            m = num(a.get('capacity'), None)
        return m if m is not None and m >= 0 else self.minutes_per_day

    def actor_works(self, actor, day):
        """Whether the actor works on this day (their own days, else the holon's)."""
        a = self.actors.get(actor or '') or {}
        wd = _weekday_set(a.get('working_days'))
        off = {x for x in (to_date(o) for o in (a.get('off') or []) if isinstance(a.get('off'), list)) if x}
        if day in off or day in self.holidays:
            return False
        return day.weekday() in (wd if wd is not None else self.working_days)

    def capacity(self, actor, day):
        return self.actor_minutes(actor) if self.actor_works(actor, day) else 0.0


class Axis:
    """Working-day offsets from the data date, and back to dates (cpm.py's counting)."""

    LIMIT = 200 * 366

    def __init__(self, start, cal):
        self.start = start
        self.cal = cal
        self.fwd = [start]     # fwd[k]: the date of offset k (k >= 1 are working days)
        self.back = [start]    # back[k]: the date of offset -k

    def _grow(self, seq, step, n):
        while len(seq) <= n:
            d = seq[-1]
            for _ in range(self.LIMIT):
                d = d + dt.timedelta(step)
                if self.cal.is_working(d):
                    break
            else:
                raise ScheduleError('calendar has no working days')
            seq.append(d)

    def date_of(self, k):
        """The date of offset k: the working day the moment k lies in. A whole k is that day's
        morning, as cpm.py has it; a fraction is part-way through that day."""
        if k is None:
            return None
        k = int(math.floor(k + 1e-9))      # the day the moment lies in (a whole k is that morning)
        if k >= 0:
            self._grow(self.fwd, 1, k)
            return self.fwd[k]
        self._grow(self.back, -1, -k)
        return self.back[-k]

    def idx_of(self, day):
        """The offset of a date: working days in (start, day]; negative before the start."""
        if day is None:
            return None
        if day >= self.start:
            while self.fwd[-1] < day:
                self._grow(self.fwd, 1, len(self.fwd))
            return bisect.bisect_right(self.fwd, day, 1) - 1
        while self.back[-1] > day:
            self._grow(self.back, -1, len(self.back))
        return -sum(1 for x in self.back[1:] if x >= day)

    def exact(self, day):
        """The index of a working day (or of the start itself)."""
        if day >= self.start:
            while self.fwd[-1] < day:
                self._grow(self.fwd, 1, len(self.fwd))
            k = bisect.bisect_left(self.fwd, day, 1) if day > self.start else 0
            return k
        while self.back[-1] > day:
            self._grow(self.back, -1, len(self.back))
        return -self.back.index(day)

    def up(self, day):
        """The index of the first working morning at or after `day` (the start counts as one)."""
        if day is None:
            return None
        d = day
        for _ in range(self.LIMIT):
            if d == self.start or self.cal.is_working(d):
                return self.exact(d)
            d = d + dt.timedelta(1)
        raise ScheduleError('calendar has no working days')

    def last_day(self, ef, dur):
        """The last working day a card with this EF and duration occupies."""
        if ef is None or not dur or dur <= 0:
            return self.date_of(ef)
        return self.date_of(math.ceil(ef - 1e-9) - 1)


# Meeus, Astronomical Algorithms ch. 27: mean equinoxes and solstices (years 2000-3000, TT)
_MEEUS = {
    3: (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057),
    6: (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030),
    9: (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078),
    12: (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032),
}
_MEEUS_S = [(485, 324.96, 1934.136), (203, 337.23, 32964.467), (199, 342.08, 20.186),
            (182, 27.85, 445267.112), (156, 73.14, 45036.886), (136, 171.52, 22518.443),
            (77, 222.54, 65928.934), (74, 296.72, 3034.906), (70, 243.58, 9037.513),
            (58, 119.81, 33718.147), (52, 297.17, 150.678), (50, 21.02, 2281.226),
            (45, 247.54, 29929.562), (44, 325.15, 31555.956), (29, 60.93, 4443.417),
            (18, 155.12, 67555.328), (17, 288.79, 4562.452), (16, 198.04, 62894.029),
            (14, 199.76, 31436.921), (12, 95.39, 14577.848), (12, 287.11, 31931.756),
            (12, 320.81, 34777.259), (9, 227.73, 1222.114), (8, 15.45, 16859.074)]
_SEASON_NORTH = {3: 'Spring', 6: 'Summer', 9: 'Autumn', 12: 'Winter'}
_SEASON_SOUTH = {3: 'Autumn', 6: 'Winter', 9: 'Spring', 12: 'Summer'}


def turning_moment(year, month):
    """The UTC moment of the equinox or solstice in that month (3, 6, 9, 12), to a few minutes."""
    y = (year - 2000) / 1000.0
    a = _MEEUS[month]
    jde0 = a[0] + a[1] * y + a[2] * y ** 2 + a[3] * y ** 3 + a[4] * y ** 4
    t = (jde0 - 2451545.0) / 36525.0
    w = math.radians(35999.373 * t - 2.47)
    dl = 1 + 0.0334 * math.cos(w) + 0.0007 * math.cos(2 * w)
    s = sum(A * math.cos(math.radians(B + C * t)) for A, B, C in _MEEUS_S)
    jde = jde0 + 0.00001 * s / dl
    return dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc) + dt.timedelta(days=jde - 2451545.0)


def turnings(year, cal=None):
    """[(date, month)] of the four turnings of a year, in the calendar's local day."""
    gc = (cal if isinstance(cal, Calendar) else Calendar(cal)).gameclock
    off = num(gc.get('utc_offset_hours'), 0.0)
    out = []
    for m in (3, 6, 9, 12):
        t = turning_moment(year, m) + dt.timedelta(hours=off)
        out.append((t.date(), m))
    return out


# Meeus, Astronomical Algorithms ch. 49: new and full moons (mean phase plus the seven largest
# periodic terms; good to well under an hour, and the brief asks only for the right day)
def moon_moment(k):
    """The UTC moment of lunation k: an integer k is a new moon, k + 0.5 a full moon.

    k counts lunations from the new moon of 2000-01-06 (k = 0).
    """
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    E = 1 - 0.002516 * T - 0.0000074 * T ** 2
    M = math.radians(2.5534 + 29.10535670 * k - 0.0000014 * T ** 2)
    Mp = math.radians(201.5643 + 385.81693528 * k + 0.0107582 * T ** 2)
    F = math.radians(160.7108 + 390.67050284 * k - 0.0016118 * T ** 2)
    if abs(k - math.floor(k)) < 1e-9:
        c = (-0.40720 * math.sin(Mp) + 0.17241 * E * math.sin(M) + 0.01608 * math.sin(2 * Mp)
             + 0.01039 * math.sin(2 * F) + 0.00739 * E * math.sin(Mp - M)
             - 0.00514 * E * math.sin(Mp + M) + 0.00208 * E * E * math.sin(2 * M))
    else:
        c = (-0.40614 * math.sin(Mp) + 0.17302 * E * math.sin(M) + 0.01614 * math.sin(2 * Mp)
             + 0.01043 * math.sin(2 * F) + 0.00734 * E * math.sin(Mp - M)
             - 0.00515 * E * math.sin(Mp + M) + 0.00209 * E * E * math.sin(2 * M))
    return dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc) + dt.timedelta(days=jde + c - 2451545.0)


def _explicit(cal, key):
    """Dates the calendar carries under gameclock[key] (a list of dates), or None."""
    gc = (cal if isinstance(cal, Calendar) else Calendar(cal)).gameclock
    v = gc.get(key)
    if not isinstance(v, list):
        return None
    out = sorted({x for x in (to_date(d.get('date') if isinstance(d, dict) else d) for d in v) if x})
    return out or None


def moons(date_from, date_to, cal=None):
    """[{kind: new_moon|full_moon, date}] between two dates (inclusive), in the calendar's local day.

    A calendar may carry its own `gameclock.new_moons` and `gameclock.full_moons` date lists (the
    paper floor, or a local almanac); within the span those lists replace the astronomy.
    """
    a, b = to_date(date_from), to_date(date_to)
    if not a or not b or b < a:
        return []
    cal = cal if isinstance(cal, Calendar) else Calendar(cal)
    off = num(cal.gameclock.get('utc_offset_hours'), 0.0)
    out = []
    for kind, key, half in (('new_moon', 'new_moons', 0.0), ('full_moon', 'full_moons', 0.5)):
        given = _explicit(cal, key)
        if given and given[0] <= a and given[-1] >= b:
            out.extend({'kind': kind, 'date': d.isoformat()} for d in given if a <= d <= b)
            continue
        if given:
            out.extend({'kind': kind, 'date': d.isoformat()} for d in given if a <= d <= b)
            seen = set(given)
        else:
            seen = set()
        k0 = math.floor((a.year + (a.timetuple().tm_yday - 1) / 365.25 - 2000) * 12.3685) - 1
        k = k0
        while True:
            d = (moon_moment(k + half) + dt.timedelta(hours=off)).date()
            if d > b:
                break
            if d >= a and not any(abs((d - s).days) <= 2 for s in seen):
                out.append({'kind': kind, 'date': d.isoformat()})
            k += 1
    out.sort(key=lambda r: (r['date'], r['kind']))
    return out


def turnings_between(date_from, date_to, cal=None):
    """[{kind: turning, date, season}] between two dates (inclusive)."""
    a, b = to_date(date_from), to_date(date_to)
    if not a or not b or b < a:
        return []
    cal = cal if isinstance(cal, Calendar) else Calendar(cal)
    names = _SEASON_SOUTH if str(cal.gameclock.get('hemisphere') or '').lower().startswith('s') \
        else _SEASON_NORTH
    given = _explicit(cal, 'turnings')
    if given:
        pts = [(d, _turning_month(d)) for d in given]
    else:
        pts = [p for y in range(a.year, b.year + 1) for p in turnings(y, cal)]
    return [{'kind': 'turning', 'date': d.isoformat(), 'season': names[m]}
            for d, m in sorted(pts) if a <= d <= b]


def _turning_month(d):
    """The turning month (3, 6, 9, 12) a given turning date stands for."""
    return min((3, 6, 9, 12), key=lambda m: min(abs(d.month - m), 12 - abs(d.month - m)))


RHYTHM_ORDER = {'day': 0, 'new_moon': 1, 'full_moon': 1, 'turning': 2}


def rhythms(date_from, date_to=None, cal=None):
    """Every rhythm that turns between two dates (inclusive): [{kind, date}], kind one of
    day · new_moon · full_moon · turning. Every day is a day; moons and turnings fall on theirs.
    With one date (or a calendar in the second place), the span is that one day.

    OmniSpection is continual, at varying depths: daily, at the new and the full moon, at each
    turning. This list is the clock those depths are read from; it imposes no depth itself.
    Sorted by date, the day first, then the moon, then the turning.
    """
    if isinstance(date_to, (dict, Calendar)) and cal is None:
        date_to, cal = None, date_to
    if date_to is None:
        date_to = date_from
    a, b = to_date(date_from), to_date(date_to)
    if not a or not b or b < a:
        return []
    if (b - a).days > 366 * 20:
        b = a + dt.timedelta(366 * 20)     # a guard; twenty years is the longest view taken
    out = [{'kind': 'day', 'date': (a + dt.timedelta(i)).isoformat()} for i in range((b - a).days + 1)]
    out += [{'kind': m['kind'], 'date': m['date']} for m in moons(a, b, cal)]
    out += [{'kind': 'turning', 'date': x['date'], 'season': x['season']} for x in turnings_between(a, b, cal)]
    out.sort(key=lambda r: (r['date'], RHYTHM_ORDER.get(r['kind'], 9)))
    return out


def gameclock(day=None, cal=None):
    """Where a date sits on the Gameclock: season, day of season, span, and the moons around it.

    A season runs from one turning (solstice or equinox) to the next. Two spans of 42 days live
    in it: span 1 is days 1-42, span 2 days 43-84; the few days left before the next turning
    belong to no span. OmniSpection is not a point in the season: it is continual, at varying
    depths (daily, each new and full moon, each turning); see rhythms(). Explicit `turnings`
    dates in the calendar replace the astronomy (the paper floor).
    """
    day = to_date(day) or dt.date.today()
    cal = cal if isinstance(cal, Calendar) else Calendar(cal)
    gc = cal.gameclock
    explicit = _explicit(cal, 'turnings') or []
    if len(explicit) >= 2 and explicit[0] <= day < explicit[-1]:
        pts = [(d, _turning_month(d)) for d in explicit]
    else:
        pts = []
        for y in (day.year - 1, day.year, day.year + 1):
            pts.extend(turnings(y, cal))
    pts.sort()
    cur = max((p for p in pts if p[0] <= day), default=pts[0])
    nxt = min((p for p in pts if p[0] > day), default=None)
    names = _SEASON_SOUTH if str(gc.get('hemisphere') or '').lower().startswith('s') else _SEASON_NORTH
    month = cur[1] if cur[1] in names else 3
    length = (nxt[0] - cur[0]).days if nxt else 91
    n = (day - cur[0]).days + 1
    span, s0, s1 = None, None, None
    for sp, lo, hi in ((1, 1, 42), (2, 43, 84)):
        if lo <= n <= hi:
            span, s0, s1 = sp, lo, hi
            break
    near = moons(day - dt.timedelta(31), day + dt.timedelta(31), cal)
    def last(kind):
        return max((m['date'] for m in near if m['kind'] == kind and m['date'] <= day.isoformat()), default=None)
    def nxt_m(kind):
        return min((m['date'] for m in near if m['kind'] == kind and m['date'] > day.isoformat()), default=None)
    return {
        'date': day.isoformat(),
        'season': names[month], 'season_year': cur[0].year,
        'season_start': cur[0].isoformat(), 'next_turning': nxt[0].isoformat() if nxt else None,
        'season_length': length, 'day_of_season': n,
        'span': span,
        'span_start': (cur[0] + dt.timedelta(s0 - 1)).isoformat() if s0 else None,
        'span_end': (cur[0] + dt.timedelta(s1 - 1)).isoformat() if s1 else None,
        'day_of_span': (n - s0 + 1) if s0 else None,
        'last_new_moon': last('new_moon'), 'next_new_moon': nxt_m('new_moon'),
        'last_full_moon': last('full_moon'), 'next_full_moon': nxt_m('full_moon'),
        'rule': 'season = turning to turning; two spans of 42 days; OmniSpection continual '
                '(daily, new and full moon, turning)',
    }


# ---------------------------------------------------------------- reading items

def split_items(data):
    """Folded items in any container -> (cards, commits, teas, sights, rel_map, as_of_hints).

    Accepts a list of items; {"items": [...]}; {"items": {id: item}}; a dict of lists keyed by
    kind ("cards", "commitments", ...); or a bare {id: item} map. Unknown kinds are ignored.
    """
    cards, commits, teas, sights = [], [], [], []
    rel_map, hints = {}, {}

    def put(it, forced=None):
        if not isinstance(it, dict):
            return
        t = forced or item_type(it)
        if t in CARD_TYPES:
            cards.append(it)
        elif t in COMMIT_TYPES:
            commits.append(it)
        elif t in TEA_TYPES:
            teas.append(it)
        elif t in SIGHT_TYPES:
            sights.append(it)
        if isinstance(it.get('commitments'), list):
            for c in it['commitments']:
                if isinstance(c, dict):
                    commits.append(dict(c, card=c.get('card') or it.get('id'),
                                        holon=c.get('holon') or it.get('holon')))

    def each(container, forced=None):
        if isinstance(container, list):
            for it in container:
                put(it, forced)
        elif isinstance(container, dict):
            for k, it in container.items():
                if isinstance(it, dict):
                    put(dict(it, id=it.get('id', k)), forced)

    if isinstance(data, list):
        each(data)
    elif isinstance(data, dict):
        known = False
        if 'items' in data:
            each(data['items'])
            known = True
        for key, forced in PLURAL_KEYS.items():
            if key in data and key != 'tea':
                each(data[key], forced)
                known = True
        if isinstance(data.get('tea'), list):
            each(data['tea'], 'tea')
            known = True
        if isinstance(data.get('rel'), dict):
            rel_map = data['rel']
            known = True
        if isinstance(data.get('as_of'), dict):
            for h, v in data['as_of'].items():
                ts = v.get('ts') if isinstance(v, dict) else v
                if isinstance(ts, str):
                    hints[str(h)] = ts
            known = True
        if isinstance(data.get('holons'), list):
            for h in data['holons']:
                if isinstance(h, dict) and h.get('id') and isinstance(h.get('as_of'), dict) \
                        and isinstance(h['as_of'].get('ts'), str):
                    hints[str(h['id'])] = h['as_of']['ts']
            known = True
        if not known:
            each(data)
    return cards, commits, teas, sights, rel_map, hints


def load_external(paths, warnings=None):
    """Published lines (JSONL) from other holons -> list of event dicts. Bad lines are skipped."""
    out = []
    for p in paths or []:
        try:
            with open(p, encoding='utf-8') as f:
                for n, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except ValueError:
                        if warnings is not None:
                            warnings.append(f'{p}:{n}: not a JSON line; skipped')
                        continue
                    if isinstance(ev, dict):
                        out.append(ev)
        except OSError as e:
            if warnings is not None:
                warnings.append(f'{p}: cannot read ({e.strerror})')
    return out


def _ext_date(ev):
    for k in ('by', 'date', 'finish', 'at', 'ef'):
        d = to_date(field(ev, k))
        if d:
            return d
    return None


# ---------------------------------------------------------------- the activity model

class Act:
    """One card as the passes see it. Dates are held as t, calendar days from the data date;
    the card's own working-day indexes (on its holon's calendar) are esi, efi, lsi, lfi."""

    __slots__ = ('id', 'item', 'title', 'kind', 'atype', 'holon', 'holder', 'minutes', 'dur',
                 'rem', 'pct', 'status', 'astart', 'afinish', 'asti', 'snet', 'fnlt', 'mso', 'mfo',
                 'alap', 'codes', 'preds', 'succs', 'ext_preds', 'need_by', 'interface',
                 'es', 'ef', 'ls', 'lf', 'esi', 'efi', 'lsi', 'lfi', 'lesi', 'tf', 'ff', 'sized',
                 'summarizes', 'system', 'cons', 'shift', 'cal', 'ax', 'driver', 'committed_by',
                 'within', 'kids')

    def __init__(self, cid, item):
        self.id = cid
        self.item = item
        self.preds, self.succs, self.ext_preds = [], [], []
        self.need_by = None
        self.cons = []
        self.system = False
        self.within, self.kids = None, []
        self.reset()

    def reset(self):
        self.es = self.ef = self.ls = self.lf = self.tf = self.ff = None
        self.esi = self.efi = self.lsi = self.lfi = None
        self.lesi = None     # the start the logic alone gives, before any time constraint
        self.shift = 0       # days an as-late-as-possible card was moved
        self.driver = None   # the predecessor that set the early start


ITEM_KINDS = CARD_TYPES | COMMIT_TYPES | TEA_TYPES | SIGHT_TYPES | {
    'thread', 'decision', 'request', 'offer', 'delegation', 'proposal', 'claim', 'discern', 'learn'}


def card_kind(item):
    """The Work Card's own kind. The fold keeps it as `body_kind` (its `kind` names the item,
    "card"); a hand-built card may carry it as `kind`. `activity_type` overrides both."""
    for k in ('activity_type', 'body_kind', 'card_kind'):
        v = field(item, k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    v = item.get('kind') if isinstance(item, dict) else None
    if isinstance(v, str) and v.strip() and v.strip().lower() not in ITEM_KINDS:
        return v.strip().lower()
    body = item.get('body') if isinstance(item, dict) else None
    v = body.get('kind') if isinstance(body, dict) else None
    if isinstance(v, str) and v.strip() and v.strip().lower() not in ITEM_KINDS:
        return v.strip().lower()
    return 'activity'


def _atype(item):
    k = card_kind(item)
    if k == 'milestone':
        return 'milestone'
    if k in ('loe', 'level-of-effort', 'level of effort', 'level_of_effort', 'hammock'):
        return 'loe'
    if k in ('summary', 'wbs summary', 'wbs-summary'):
        return 'summary'
    return 'activity'


def work_days(x):
    """A duration in working days, fractions kept (minutes are the one
    unit, and a card is never rounded up to a whole day). Held to six places."""
    return round(float(x), 6) if x and x > 0 else 0.0


def whole_lag(x):
    """Lags in whole days, halves away from zero."""
    return float(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


CONSTRAINT_KINDS = {
    'finish-by': 'finish-by', 'by': 'finish-by',
    'finish-no-later': 'finish-no-later', 'fnlt': 'finish-no-later', 'finish_no_later': 'finish-no-later',
    'start-no-earlier': 'start-no-earlier', 'snet': 'start-no-earlier', 'start_no_earlier': 'start-no-earlier',
    'start-on': 'start-on', 'mso': 'start-on', 'must_start_on': 'start-on', 'must-start-on': 'start-on',
    'finish-on': 'finish-on', 'mfo': 'finish-on', 'must_finish_on': 'finish-on', 'must-finish-on': 'finish-on',
    'as-late-as-possible': 'as-late-as-possible', 'alap': 'as-late-as-possible',
    'as_late_as_possible': 'as-late-as-possible',
}
HARD_KINDS = {'start-on', 'finish-on'}
CONSTRAINT_SOURCES = {'commitment', 'world', 'law'}
SIMPLE_FORMS = (('by', 'finish-by'), ('finish_no_later', 'finish-no-later'),
                ('start_no_earlier', 'start-no-earlier'), ('must_start_on', 'start-on'),
                ('must_finish_on', 'finish-on'))


def read_constraints(it, dd, warnings, cid):
    """A card's time constraints -> [{kind, date, off, hard, reason, imposed_by, source, form}].

    Constraint is the genus; a time constraint is an imposed date. The structured form
    (SCHEMA.md) is `constraint`: {sort, kind, date, reason, imposed_by, source}, or a list of
    them. `sort` defaults to "time"; other sorts (resource, information, agreement: what must
    clear before work is ready, the Field's look-ahead sense) share the word and are left to the
    parts that read them; this engine reads only the time sort. The simple forms `by`,
    `start_no_earlier`, `finish_no_later`, `must_start_on`, `must_finish_on` and `alap: true`
    are read too; they carry no reason and no imposer, so the report names them as defects. A
    simple form that repeats a structured one (same kind and date) counts once. `off` is calendar
    days from the data date.
    """
    out = []
    raw = field(it, 'constraint')
    for c in (raw if isinstance(raw, list) else [raw]):
        if c is None:
            continue
        if isinstance(c, str):
            c = {'kind': c}
        if not isinstance(c, dict):
            warnings.append(f'{cid}: constraint unreadable; ignored')
            continue
        if str(c.get('sort') or 'time').strip().lower() != 'time':
            continue                       # another sort of constraint: not this engine's to read
        k = CONSTRAINT_KINDS.get(str(c.get('kind') or c.get('type') or '').strip().lower())
        if not k:
            warnings.append(f'{cid}: constraint kind {c.get("kind") or c.get("type")!r} unknown; ignored')
            continue
        d = to_date(c.get('date'))
        out.append({'kind': k, 'date': d, 'off': (d - dd).days if d else None, 'hard': k in HARD_KINDS,
                    'reason': c.get('reason') if isinstance(c.get('reason'), str) and c['reason'].strip() else None,
                    'imposed_by': c.get('imposed_by') if isinstance(c.get('imposed_by'), str)
                    and c['imposed_by'].strip() else None,
                    'source': str(c['source']).lower() if isinstance(c.get('source'), str) else None,
                    'form': 'constraint', 'dated': d is not None or k == 'as-late-as-possible'})
    have = {(c['kind'], c['date']) for c in out}
    for key, k in SIMPLE_FORMS:
        d = to_date(field(it, key))
        if d and (k, d) not in have and not (k == 'finish-by' and ('finish-no-later', d) in have):
            out.append({'kind': k, 'date': d, 'off': (d - dd).days, 'hard': k in HARD_KINDS,
                        'reason': None, 'imposed_by': None, 'source': None, 'form': key, 'dated': True})
            have.add((k, d))
    if field(it, 'alap') is True and not any(c['kind'] == 'as-late-as-possible' for c in out):
        out.append({'kind': 'as-late-as-possible', 'date': None, 'off': None, 'hard': False,
                    'reason': None, 'imposed_by': None, 'source': None, 'form': 'alap', 'dated': True})
    return out


def _t2d(ax, t):
    return ax.start + dt.timedelta(days=int(math.floor(t + 1e-9)))


def _up(ax, t):
    """The card calendar's index of calendar moment t: a whole t is the first working morning
    at or after that day; a fraction on a working day keeps its place in the day; a fraction on
    a day off moves to the next working morning."""
    t = round(t, 6)
    base = math.floor(t + 1e-9)
    frac = t - base
    if frac > 1e-9:
        day = _t2d(ax, base)
        if day == ax.start or ax.cal.is_working(day):
            return round(ax.exact(day) + frac, 6)
    return ax.up(_t2d(ax, base))


def _T(ax, k):
    """Calendar moment t of the card calendar's working index k (whole days plus the fraction)."""
    k = round(k, 6)
    base = math.floor(k + 1e-9)
    frac = k - base
    return round((ax.date_of(base) - ax.start).days + (frac if frac > 1e-9 else 0.0), 6)


def constraints(acts):
    """The report on time constraints (imposed dates): how many, how hard, where, how founded,
    and what they cost.

    Hard (start-on, finish-on) pin dates in both passes; soft ones (finish-by, finish-no-later,
    start-no-earlier, as-late-as-possible) bound the logic and their lateness shows as negative
    float. Days are the card's own working days. Per constraint:
      negative_float_days  finish-by / finish-no-later: how far the card's early finish runs past
                           the date; start-on: how far the logic alone would start it after the
                           pinned date; finish-on: the same for its finish. start-no-earlier and
                           as-late-as-possible cause none.
      delay_days           how many days the constraint holds the card later than its logic
                           (start-no-earlier, start-on, finish-on; the shift of as-late-as-possible).
      defects              'no reason', 'no imposer', 'no date', 'source not commitment, world or law'.
      on_activity          true when the card is not a milestone (time constraints belong on
                           milestones by default; counted, not a defect).
    """
    rows = []
    cards = [a for a in acts.values() if a.status != 'dropped' and a.atype in ('activity', 'milestone')]
    for a in sorted(cards, key=lambda x: x.id):
        for c in a.cons:
            k, off = c['kind'], c['off']
            neg = delay = None
            live = a.esi is not None and a.lesi is not None
            if live and off is not None:
                u = _up(a.ax, off)
                if k in ('finish-by', 'finish-no-later'):
                    neg = max(0, a.efi - u)
                elif k == 'start-on':
                    neg, delay = max(0, a.lesi - u), max(0, u - a.lesi)
                elif k == 'finish-on':
                    lef = a.lesi + a.rem
                    neg, delay = max(0, lef - u), max(0, u - lef)
                elif k == 'start-no-earlier':
                    neg, delay = 0, max(0, u - a.lesi)
            if live and k == 'as-late-as-possible':
                neg, delay = 0, a.shift
            defects = []
            if not c['reason']:
                defects.append('no reason')
            if not c['imposed_by']:
                defects.append('no imposer')
            if not c['dated']:
                defects.append('no date')
            if c['source'] is not None and c['source'] not in CONSTRAINT_SOURCES:
                defects.append('source not commitment, world or law')
            if not c.get('applied', True):
                defects.append('an imposed date on a card: reported, never applied')
                delay = 0 if delay is not None else delay
            rows.append({'card': a.id, 'holon': a.holon, 'title': a.title, 'kind': k,
                         'date': c['date'].isoformat() if c['date'] else None,
                         'hard': c['hard'], 'on_activity': a.atype != 'milestone',
                         'reason': c['reason'], 'imposed_by': c['imposed_by'], 'source': c['source'],
                         'form': c['form'], 'status': a.status,
                         'negative_float_days': out_num(neg), 'delay_days': out_num(delay),
                         'TF': out_num(a.tf), 'defects': defects, 'applied': c.get('applied', True)})
    constrained = {r['card'] for r in rows}
    by_source, by_kind = {}, {}
    for r in rows:
        by_source[r['source'] or 'unstated'] = by_source.get(r['source'] or 'unstated', 0) + 1
        by_kind[r['kind']] = by_kind.get(r['kind'], 0) + 1
    return {
        'count': len(rows),
        'cards_constrained': len(constrained), 'cards': len(cards),
        'share_constrained': out_num(len(constrained) / len(cards)) if cards else None,
        'hard': sum(1 for r in rows if r['hard']), 'soft': sum(1 for r in rows if not r['hard']),
        'on_activities': sum(1 for r in rows if r['on_activity']),
        'no_reason': sum(1 for r in rows if 'no reason' in r['defects']),
        'no_imposer': sum(1 for r in rows if 'no imposer' in r['defects']),
        'defects': sum(len(r['defects']) for r in rows),
        'negative_float_days': out_num(sum(r['negative_float_days'] or 0 for r in rows)),
        'by_kind': dict(sorted(by_kind.items())), 'by_source': dict(sorted(by_source.items())),
        'not_applied': sum(1 for r in rows if not r['applied']),
        'items': rows,
        'rule': 'no imposed date on a Work Card: a time constraint on a card is reported and never applied; a milestone keeps '
                'only its finish-by as its marker\'s target, in the backward pass; lateness shows as negative float, never hidden',
    }


def build_acts(cards, place, dd, warnings):
    """Cards -> {id: Act} with durations, progress and time constraints read (not yet linked).

    `place(holon)` gives (Calendar, Axis) for the card's holon: its own calendar when one is
    known, else the home calendar.
    """
    acts = {}
    for it in cards:
        cid = it.get('id')
        if cid is None or str(cid) == '':
            warnings.append('a card without an id was skipped')
            continue
        cid = str(cid)
        if cid in acts:
            warnings.append(f'{cid}: held twice; the later item is used')
        a = Act(cid, it)
        a.title = str(field(it, 'title') or '')
        a.kind = card_kind(it)
        a.atype = _atype(it)
        a.holon = str(field(it, 'holon') or '')
        a.cal, a.ax = place(a.holon)
        h = field(it, 'holder')
        a.holder = str(h) if isinstance(h, (str, int)) and str(h) else None
        mpd = a.cal.actor_minutes(a.holder)
        minutes = None
        for k in ('minutes', 'size', 'min'):
            minutes = num(field(it, k), None)
            if minutes is not None:
                break
        dd_ = num(field(it, 'dur_days'), None)
        a.sized = True
        if a.atype == 'milestone':
            dur = 0.0
        elif dd_ is not None and dd_ >= 0:
            dur = work_days(dd_)
        elif minutes is not None and minutes > 0:
            if not mpd or mpd <= 0:
                dur = 0.0
                a.sized = False
                warnings.append(f'{cid}: the holder has 0 minutes a day; {out_num(minutes)} minutes cannot '
                                f'be placed, held as 0 days')
            else:
                dur = work_days(minutes / mpd)
        else:
            dur = 0.0
            if a.atype == 'activity':
                a.sized = False
                warnings.append(f'{cid}: no minutes and no dur_days; held as 0 days')
        a.dur = dur
        a.minutes = minutes if minutes is not None else (dur * mpd if dd_ is not None else 0.0)
        # progress
        state = str(field(it, 'state') or '').lower()
        stage = str(field(it, 'stage') or '').lower()
        a.astart = to_date(field(it, 'actual_start'))
        a.afinish = to_date(field(it, 'actual_finish'))
        a.asti = a.ax.up(a.astart) if a.astart else None
        pct = num(field(it, 'percent_complete'), None)
        if state in DROP_STATES:
            a.status = 'dropped'
        elif state in DONE_STATES or stage == 'did' or a.afinish or (pct is not None and pct >= 100):
            a.status = 'complete'
        elif a.astart or (pct is not None and pct > 0) or field(it, 'remaining_days') is not None \
                or field(it, 'remaining_minutes') is not None:
            a.status = 'in_progress'
        else:
            a.status = 'not_started'
        rem = dur
        rd, rm = num(field(it, 'remaining_days'), None), num(field(it, 'remaining_minutes'), None)
        if a.status == 'complete':
            rem = 0.0
        elif rd is not None and rd >= 0:
            rem = work_days(rd)
        elif rm is not None and rm >= 0 and mpd and mpd > 0:
            rem = work_days(rm / mpd)
        elif pct is not None and 0 < pct < 100:
            rem = work_days(dur * (1 - pct / 100.0))
        a.rem = rem
        if a.status == 'complete':
            a.pct = 100.0
        elif pct is not None:
            a.pct = max(0.0, min(100.0, pct))
        elif a.status == 'in_progress' and dur > 0:
            a.pct = max(0.0, min(100.0, 100.0 * (1 - rem / dur)))
        else:
            a.pct = 0.0
        # time constraints: the structured `constraint` (one or a list) and the simple forms
        a.cons = read_constraints(it, dd, warnings, cid)
        mk = field(it, 'marker')
        if isinstance(mk, str) and mk.strip():
            # a milestone names its marker; the marker's date lives in the calendar (`markers`), never on the card or in code
            m = a.cal.marker(mk.strip())
            if m is None:
                warnings.append(f'{cid}: marker {mk} is not in the calendar')
            elif a.atype != 'milestone':
                warnings.append(f'{cid}: names marker {mk} but is not a milestone; read as nothing')
            elif m['state'] == 'passed':
                warnings.append(f'{cid}: marker {mk} has passed; no work is measured against it')
            elif m['date']:
                a.cons.append({'kind': 'finish-by', 'date': m['date'], 'off': (m['date'] - dd).days, 'hard': False,
                               'reason': f'marker {mk}', 'imposed_by': None, 'source': 'marker', 'form': 'marker',
                               'dated': True})
        a.committed_by = [x for x in (field(it, 'committed_by') or []) if isinstance(x, dict) and x.get('due_by')]
        a.snet = a.fnlt = a.mso = a.mfo = None
        a.alap = False
        for c in a.cons:
            k, off = c['kind'], c['off']
            if k == 'as-late-as-possible':
                a.alap = True
            elif off is None:
                continue
            elif k == 'start-no-earlier':
                a.snet = off if a.snet is None else max(a.snet, off)
            elif k in ('finish-by', 'finish-no-later'):
                a.fnlt = off if a.fnlt is None else min(a.fnlt, off)
            elif k == 'start-on':
                if a.mso is not None and a.mso != off:
                    warnings.append(f'{cid}: two start-on dates; the first is kept')
                a.mso = off if a.mso is None else a.mso
            elif k == 'finish-on':
                if a.mfo is not None and a.mfo != off:
                    warnings.append(f'{cid}: two finish-on dates; the first is kept')
                a.mfo = off if a.mfo is None else a.mfo
        # Start and finish dates are calculated from the logic, never imposed. A time constraint on a Work
        # Card is REPORTED, never applied. A milestone keeps one thing: a finish-by (or a finish-on, read as a finish-by) as its marker's target, in the backward
        # pass alone. Start-on, finish-on and start-no-earlier are applied to no card; a received commitment's not-before enters only as
        # an external (engine.py), at the boundary. As-late-as-possible is a release rule, not a date, and is kept.
        for c in a.cons:
            c['applied'] = (c['kind'] == 'as-late-as-possible' or
                            (a.atype == 'milestone' and c['kind'] in ('finish-by', 'finish-no-later', 'finish-on')))
        if a.atype == 'milestone' and a.mfo is not None:
            a.fnlt = a.mfo if a.fnlt is None else min(a.fnlt, a.mfo)
        elif a.atype != 'milestone':
            a.fnlt = None
        a.snet = a.mso = a.mfo = None
        a.codes = code_paths(field(it, 'codes'))
        s = field(it, 'summarizes')
        a.summarizes = s.strip().strip('/') if isinstance(s, str) and s.strip() else \
            (a.codes[0] if a.codes else None)
        a.interface = bool(field(it, 'interface'))
        w = [x for x in id_list(it, 'within') if x != cid]
        a.within = w[0] if w else None
        if len(w) > 1:
            warnings.append(f'{cid}: within {len(w)} units; a card lies within exactly one, the first ({w[0]}) is kept')
        acts[cid] = a
    return acts


# ---------------------------------------------------------------- the holarchy (within)

def nest(acts, warnings):
    """Read `within`, the nesting edge: every card lies within one larger unit, and a card that
    holds others is a unit. A unit's dates are its children's (rolled up after the passes); a link
    to or from a unit is routed to its entries or exits (route_pairs). A within that names a card
    not yet held, or that would close a loop, is reported and read as none."""
    for a in acts.values():
        if a.within is None:
            continue
        if a.within not in acts:
            warnings.append(f'{a.id}: within {a.within} not yet replicated')
            continue
        seen, cur = {a.id}, a.within
        while cur is not None and cur in acts:
            if cur in seen:
                warnings.append(f'{a.id}: within {a.within} closes a loop; read as none')
                a.within = None
                break
            seen.add(cur)
            cur = acts[cur].within
    for a in acts.values():
        if a.within in acts:
            acts[a.within].kids.append(a.id)
    for a in acts.values():
        a.kids.sort()
        if a.kids:
            if a.atype in ('milestone', 'loe', 'summary'):
                warnings.append(f'{a.id}: a {a.atype} holds cards; read as a unit')
            a.atype = 'unit'


def _ancestors(acts, cid):
    out, cur = set(), acts[cid].within if cid in acts else None
    while cur in acts and cur not in out:
        out.add(cur)
        cur = acts[cur].within
    return out


def route_pairs(acts, pairs, warnings):
    """Route each link that touches a unit to the unit's own cards: a link from a unit leaves by
    its exits (the cards nothing inside it waits on) for FS and FF, by its entries for SS and SF;
    a link to a unit arrives at its entries (the cards that wait on nothing inside it) for FS and
    SS, at its exits for FF and SF. Nested units route all the way down. A link between a card and
    a unit that holds it is read as nothing."""
    def live(i):
        return i in acts and acts[i].status != 'dropped'
    inside = {}
    for (p, s) in pairs:
        if p in acts and s in acts and acts[p].within is not None and acts[p].within == acts[s].within:
            inside.setdefault(s, set()).add(p)        # s waits on a sibling
            inside.setdefault(('out', p), set()).add(s)

    def ends(u, side, stack=()):
        if u in stack:
            return []
        out = []
        for c in acts[u].kids:
            if not live(c):
                continue
            sib = inside.get(c if side == 'in' else ('out', c), set())
            if any(live(x) and acts[x].within == u for x in sib):
                continue
            out.extend(ends(c, side, stack + (u,)) if acts[c].atype == 'unit' else [c])
        return out

    routed = {}
    for (p, s), (t, lag) in pairs.items():
        ps = ends(p, 'out' if t in ('FS', 'FF') else 'in') if p in acts and acts[p].atype == 'unit' else [p]
        ss = ends(s, 'in' if t in ('FS', 'SS') else 'out') if s in acts and acts[s].atype == 'unit' else [s]
        if (p in acts and s in _ancestors(acts, p)) or (s in acts and p in _ancestors(acts, s)):
            warnings.append(f'{p} -> {s}: a link between a card and a unit that holds it; read as nothing')
            continue
        for x in ps:
            for y in ss:
                if x != y and (x, y) not in routed:
                    routed[(x, y)] = (t, lag)
    return routed


def holarchy(acts):
    """The holarchy report: the units, the cards at the top (within nothing held), every within
    not yet replicated, and every open end of the network (a card nothing comes before, or nothing
    comes after, once units are routed)."""
    live = [a for a in acts.values() if a.status != 'dropped']
    logic = [a for a in live if _logic(a)]
    return {
        'units': sorted(a.id for a in live if a.atype == 'unit'),
        'top': sorted(a.id for a in live if a.within is None),
        'within_not_held': sorted(a.id for a in live if a.within is not None and a.within not in acts),
        'open_ends': {'nothing_before': sorted(a.id for a in logic if not a.preds and not a.ext_preds),
                      'nothing_after': sorted(a.id for a in logic if not a.succs and a.need_by is None)},
        'rule': 'every card lies within one unit and has at least one card before and after it; '
                'an open end is reported, never filled by guess',
    }


def link_acts(acts, rel_map, ext, dd, warnings):
    """Read every relationship; tie external lines in as fixed-date nodes (dates as calendar days t)."""
    pairs = {}   # (pred, succ) -> (type, lag)

    def add(p, s, t='FS', lag=0.0, force=False):
        if (p, s) not in pairs or force:
            pairs[(p, s)] = (t, whole_lag(lag))

    def tday(d):
        return (d - dd).days if d else None

    for a in acts.values():
        it = a.item
        for p in id_list(it, 'predecessor'):
            add(p, a.id)
        for s in id_list(it, 'successor'):
            add(a.id, s)
        for p, t, lag in parse_preds(field(it, 'preds')):
            add(p, a.id, t, lag, True)
        r = field(it, 'rel')
        if isinstance(r, dict):
            for p, v in r.items():
                t, lag = parse_rel(v)
                add(str(p), a.id, t, lag, True)
    if isinstance(rel_map, dict):
        for s, m in rel_map.items():
            if isinstance(m, dict):
                for p, v in m.items():
                    t, lag = parse_rel(v)
                    add(str(p), str(s), t, lag, True)
    ext_by_id = {}
    for ev in ext:
        eid = ev.get('id')
        if isinstance(eid, str) and eid:
            ext_by_id[eid] = ev
    superseded = set()
    for ev in ext:
        superseded.update(id_list(ev, 'supersedes'))
    for eid in superseded:
        ext_by_id.pop(eid, None)
    for eid, ev in ext_by_id.items():
        d = _ext_date(ev)
        for p in id_list(ev, 'predecessor'):
            if p in acts:
                a = acts[p]
                a.interface = True
                if d:
                    a.need_by = tday(d) if a.need_by is None else min(a.need_by, tday(d))
        body = ev.get('body') if isinstance(ev.get('body'), dict) else {}
        for k in ('system_path', 'critical'):
            if isinstance(body.get(k), list):
                for cid in body[k]:
                    if isinstance(cid, str) and cid in acts:
                        acts[cid].system = True
    pairs = route_pairs(acts, pairs, warnings)
    for (p, s), (t, lag) in pairs.items():
        if s not in acts and p in acts and s in ext_by_id:
            a = acts[p]
            a.interface = True
            d = _ext_date(ext_by_id[s])
            if d:
                a.need_by = tday(d) if a.need_by is None else min(a.need_by, tday(d))
            continue
        if s not in acts:
            if p in acts:
                warnings.append(f'{p}: successor {s} not yet replicated')
            continue
        S = acts[s]
        if p not in acts:
            if p in ext_by_id:
                S.interface = True
                d = _ext_date(ext_by_id[p])
                if d:
                    S.ext_preds.append((p, tday(d), t, lag))
                else:
                    warnings.append(f'{s}: external predecessor {p} carries no date')
            else:
                warnings.append(f'{s}: predecessor {p} not yet replicated')
            continue
        P = acts[p]
        if 'dropped' in (P.status, S.status):
            continue
        P.succs.append((s, t, lag))
        S.preds.append((p, t, lag))
        if P.holon and S.holon and P.holon != S.holon:
            if P.atype == 'milestone':
                P.interface = True
            if S.atype == 'milestone':
                S.interface = True
    return ext_by_id


# ---------------------------------------------------------------- the two passes

def _logic(a):
    return a.status in ('not_started', 'in_progress') and a.atype in ('activity', 'milestone')


def topo(acts, ids):
    """Kahn's order over the logic acts; a cycle raises ScheduleError naming its members."""
    ids = list(ids)
    idset = set(ids)
    indeg = {i: 0 for i in ids}
    for i in ids:
        for p, _, _ in acts[i].preds:
            if p in idset:
                indeg[i] += 1
    ready = [i for i in ids if indeg[i] == 0]
    order = []
    while ready:
        i = ready.pop(0)
        order.append(i)
        for s, _, _ in acts[i].succs:
            if s in idset:
                indeg[s] -= 1
                if indeg[s] == 0:
                    ready.append(s)
    if len(order) < len(ids):
        raise ScheduleError('cycle through ' + ', '.join(sorted(i for i in ids if indeg[i] > 0)))
    return order


def passes(acts, extra=()):
    """Forward and backward pass over the remaining work; returns (order, late_end as day t).

    Each card's arithmetic runs on its own holon's calendar: its duration in that calendar's
    working days; a lag on its predecessor's calendar. Dates meet as calendar days, so cards of
    holons with different calendars schedule together. `extra` is a list of (pred, succ)
    finish-to-start ties added for leveling.
    """
    ids = [i for i, a in acts.items() if _logic(a)]
    for p, s in extra:
        if p in acts and s in acts:
            acts[p].succs.append((s, 'FS', 0.0))
            acts[s].preds.append((p, 'FS', 0.0))
    order = topo(acts, ids)
    live = set(ids)
    for i in order:
        x = acts[i]
        ax, d = x.ax, x.rem
        best, driver = 0, None
        for p, t, lag in x.preds:
            if p not in live:
                continue
            P = acts[p]
            pa = P.ax
            lag = int(lag)
            start = P.asti if (P.status == 'in_progress' and P.asti is not None) else P.esi
            if t == 'FS':
                c = _T(pa, P.efi + lag)
            elif t == 'SS':
                c = _T(pa, start + lag)
            elif t == 'FF':
                c = _T(ax, _up(ax, _T(pa, P.efi + lag)) - d)
            else:
                c = _T(ax, _up(ax, _T(pa, start + lag)) - d)
            if c > best:
                best, driver = c, p
        for eid, off, t, lag in x.ext_preds:
            if off is None:
                continue
            c = _T(ax, _up(ax, off) + int(lag) - (d if t in ('FF', 'SF') else 0))
            if c > best:
                best, driver = c, eid
        x.lesi = _up(ax, best)
        es_t = best if x.snet is None else max(best, x.snet)
        esi = _up(ax, es_t)
        if x.snet is not None and x.snet > best:
            driver = None
        if x.mso is not None:
            esi, driver = _up(ax, x.mso), None
        elif x.mfo is not None:
            esi, driver = _up(ax, x.mfo) - d, None
        x.esi, x.efi, x.driver = esi, round(esi + d, 6), driver
        x.es, x.ef = _T(ax, x.esi), _T(ax, x.efi)
    fins = [acts[i].ef for i in order]
    for i in order:
        for c in (acts[i].fnlt, acts[i].need_by):
            if c is not None:
                fins.append(c)
    late_end = max(fins) if fins else 0
    for i in reversed(order):
        x = acts[i]
        ax, d = x.ax, x.rem
        lfi = _up(ax, late_end)
        for c in (x.fnlt, x.need_by):
            if c is not None:
                lfi = min(lfi, _up(ax, c))
        for s, t, lag in x.succs:
            if s not in live:
                continue
            S = acts[s]
            lag = int(lag)
            lim = {'FS': _up(ax, S.ls) - lag, 'SS': _up(ax, S.ls) - lag + d,
                   'FF': _up(ax, S.lf) - lag, 'SF': _up(ax, S.lf) - lag + d}[t]
            lfi = min(lfi, lim)
        if x.mfo is not None:
            lfi = _up(ax, x.mfo)
        elif x.mso is not None:
            lfi = _up(ax, x.mso) + d
        x.lfi, x.lsi = lfi, round(lfi - d, 6)
        x.lf, x.ls = _T(ax, x.lfi), _T(ax, x.lsi)
        x.tf = round(x.lsi - x.esi, 6)
    for i in order:
        x = acts[i]
        ax, d = x.ax, x.rem
        lims, has_succ = [], False
        for s, t, lag in x.succs:
            if s not in live:
                continue
            S = acts[s]
            lag = int(lag)
            has_succ = True
            lims.append({'FS': _up(ax, S.es) - lag, 'SS': _up(ax, S.es) - lag + d,
                         'FF': _up(ax, S.ef) - lag, 'SF': _up(ax, S.ef) - lag + d}[t])
        for c in (x.fnlt, x.need_by):
            if c is not None:
                lims.append(_up(ax, c))
        if not has_succ:
            lims.append(_up(ax, late_end))
        raw = min(lims) - x.efi
        x.ff = round(max(0, min(raw, x.tf)), 6)   # never above total float; never below zero
    for i in order:
        x = acts[i]
        if x.alap and x.ff > 0 and x.mso is None and x.mfo is None:
            x.shift = x.ff                 # spends free float only, so never past its own constraints
            x.esi += x.ff
            x.efi += x.ff
            x.es, x.ef = _T(x.ax, x.esi), _T(x.ax, x.efi)
            x.tf -= x.ff
            x.ff = 0
    _side_types(acts, live)
    return order, late_end


def _side_types(acts, live):
    """Level-of-effort and summary cards take their dates from their neighbors or children."""
    def index(a):
        a.esi, a.efi = _up(a.ax, a.es), _up(a.ax, a.ef)
        a.lsi, a.lfi = _up(a.ax, a.ls), _up(a.ax, a.lf)
    for a in acts.values():
        if a.atype != 'loe' or a.status in ('complete', 'dropped'):
            continue
        P = [acts[p] for p, _, _ in a.preds if p in live]
        S = [acts[s] for s, _, _ in a.succs if s in live]
        a.es = min((x.es for x in P), default=0)
        a.ls = min((x.ls for x in P), default=a.es)
        a.ef = max((x.ef for x in S), default=max((x.ef for x in P), default=a.es))
        a.lf = max((x.lf for x in S), default=max((x.lf for x in P), default=a.ef))
        index(a)
        a.rem = a.efi - a.esi
        a.tf = min(a.lsi - a.esi, a.lfi - a.efi)
        a.ff = 0
    for a in acts.values():
        if a.atype != 'summary' or a.status == 'dropped' or not a.summarizes:
            continue
        node = a.summarizes
        kids = [x for x in acts.values() if x.atype in ('activity', 'milestone', 'loe')
                and x.status != 'dropped'
                and any(c == node or c.startswith(node + '/') for c in x.codes)]
        sched = [x for x in kids if x.es is not None]
        if sched:
            a.es = min(x.es for x in sched)
            a.ef = max(x.ef for x in sched)
            a.ls = min(x.ls for x in sched)
            a.lf = max(x.lf for x in sched)
            index(a)
            a.tf = min(x.tf for x in sched)
            a.rem = a.efi - a.esi
            a.ff = None
        mins = sum(x.minutes for x in kids)
        a.minutes = mins
        a.pct = (sum(x.minutes * x.pct for x in kids) / mins) if mins else \
            (100.0 * sum(1 for x in kids if x.status == 'complete') / len(kids) if kids else 0.0)
        if kids and all(x.status == 'complete' for x in kids):
            a.status = 'complete'

    def leaves(u, seen=()):
        out = []
        for c in acts[u].kids:
            if c in acts and c not in seen:
                x = acts[c]
                out.extend(leaves(c, seen + (u,)) if x.atype == 'unit' else [x])
        return out
    for a in acts.values():
        if a.atype != 'unit':
            continue
        kids = [x for x in leaves(a.id) if x.status != 'dropped' and x.atype in ('activity', 'milestone', 'loe')]
        sched = [x for x in kids if x.es is not None]
        a.minutes = sum(x.minutes for x in kids)
        a.pct = (sum(x.minutes * x.pct for x in kids) / a.minutes) if a.minutes else \
            (100.0 * sum(1 for x in kids if x.status == 'complete') / len(kids) if kids else 0.0)
        if kids and all(x.status == 'complete' for x in kids):
            a.status = 'complete'
        elif any(x.status in ('in_progress', 'complete') for x in kids):
            a.status = 'in_progress'
        elif kids:
            a.status = 'not_started'
        if sched:
            a.es, a.ef = min(x.es for x in sched), max(x.ef for x in sched)
            a.ls, a.lf = min(x.ls for x in sched), max(x.lf for x in sched)
            index(a)
            a.tf = min(x.tf for x in sched)
            a.rem = round(a.efi - a.esi, 6)
            a.ff = None
        else:
            a.rem = 0.0


def driving_path(acts, order):
    """Walk back from the latest finish along the predecessor that set each start."""
    if not order:
        return []
    pos = {i: k for k, i in enumerate(order)}
    end = max(order, key=lambda i: (acts[i].ef, pos[i]))
    path, cur = [end], acts[end]
    for _ in range(len(order)):
        if cur.driver is None or cur.driver not in acts:
            break
        path.append(cur.driver)
        cur = acts[cur.driver]
    return list(reversed(path))


# ---------------------------------------------------------------- public pieces

def level(acts, actor, holons=None):
    """Crude local leveling: the actor's own remaining cards chained by least late start.

    Returns the (pred, succ) ties to add; run passes() again with them. Only cards whose holder
    is the actor (and, when given, whose holon is in `holons`) are ever moved.
    """
    want = str(actor or '').lower()
    mine = [a for a in acts.values() if _logic(a) and a.rem > 0 and a.ls is not None
            and (a.holder or '').lower() == want and (not holons or a.holon in holons)]
    mine.sort(key=lambda a: (a.ls, a.es, a.id))
    return [(mine[k - 1].id, mine[k].id) for k in range(1, len(mine))]


def rollup(acts, dd):
    """Scope-tree roll-up by every prefix of every code path."""
    nodes = {}
    for a in acts.values():
        if a.atype in ('summary', 'loe', 'unit') or a.status == 'dropped':
            continue
        seen = set()
        for c in a.codes:
            for node in prefixes(c):
                if node in seen:
                    continue
                seen.add(node)
                n = nodes.setdefault(node, {'cards': [], 'minutes': 0.0, 'minutes_done': 0.0,
                                            'es': None, 'ef': None, 'tf': None, 'critical': 0,
                                            'complete': 0})
                n['cards'].append(a.id)
                n['minutes'] += a.minutes
                n['minutes_done'] += a.minutes * a.pct / 100.0
                if a.status == 'complete':
                    n['complete'] += 1
                if a.es is not None:
                    n['es'] = a.es if n['es'] is None else min(n['es'], a.es)
                    n['ef'] = a.ef if n['ef'] is None else max(n['ef'], a.ef)
                    n['tf'] = a.tf if n['tf'] is None else min(n['tf'], a.tf)
                    if a.tf <= 0:
                        n['critical'] += 1
    out = {}
    for node in sorted(nodes):
        n = nodes[node]
        cnt = len(n['cards'])
        out[node] = {
            'cards': n['cards'], 'count': cnt,
            'minutes': out_num(n['minutes']), 'minutes_done': out_num(n['minutes_done']),
            'percent_complete': out_num(100.0 * n['minutes_done'] / n['minutes']) if n['minutes']
            else out_num(100.0 * n['complete'] / cnt if cnt else 0),
            'start': (dd + dt.timedelta(n['es'])).isoformat() if n['es'] is not None else None,
            'finish': (dd + dt.timedelta(n['ef'])).isoformat() if n['ef'] is not None else None,
            'TF': out_num(n['tf']), 'critical_cards': n['critical'],
        }
    return out


def load(acts, home, dd):
    """Minutes committed per actor per working day against capacity (remaining work only).

    A card's remaining minutes are spread over the days its holder works (on the card's holon
    calendar) between ES and EF. Capacity per actor comes from the home calendar when it names
    the actor, else from the first holon calendar that does, else the home default.
    """
    days, where = {}, {}
    for a in acts.values():
        if not _logic(a) or not a.holder or a.es is None or a.atype == 'milestone':
            continue                       # a milestone marks completion; it carries no days of work
        if a.holder not in where and a.holder in a.cal.actors:
            where[a.holder] = a.cal
        rem_min = a.minutes * (1 - a.pct / 100.0)
        if rem_min <= 0:
            continue
        lo, hi = int(math.floor(a.es + 1e-9)), int(math.ceil(a.ef - 1e-9))
        span = [dd + dt.timedelta(k) for k in range(lo, max(hi, lo + 1))]
        work = [d for d in span if a.cal.actor_works(a.holder, d)] or span[:1]
        each = rem_min / len(work)
        for d in work:
            key = (a.holder, d)
            days[key] = days.get(key, 0.0) + each

    def cap_cal(actor):
        return home if actor in home.actors else where.get(actor, home)
    rows = []
    for (actor, d) in sorted(days):
        rows.append({'actor': actor, 'date': d.isoformat(), 'minutes': out_num(days[(actor, d)]),
                     'capacity': out_num(cap_cal(actor).capacity(actor, d))})
    by_actor = {}
    horizon = max((a.ef for a in acts.values() if _logic(a) and a.ef is not None), default=0)
    hz = [dd + dt.timedelta(k) for k in range(0, int(horizon) + 1)]
    for actor in sorted({r['actor'] for r in rows}):
        c = cap_cal(actor)
        mine = [r for r in rows if r['actor'] == actor]
        cap = sum(c.capacity(actor, d) for d in hz)
        used = sum(r['minutes'] for r in mine)
        by_actor[actor] = {
            'minutes_per_day': out_num(c.actor_minutes(actor)),
            'committed': out_num(used), 'capacity': out_num(cap), 'free': out_num(cap - used),
            'over_days': [r['date'] for r in mine if r['minutes'] > (r['capacity'] or 0) + 1e-9],
            'peak': out_num(max((r['minutes'] for r in mine), default=0)),
        }
    return rows, by_actor


def _static_chain(acts, target):
    """Longest path to `target` by full original durations (working days) from the network's start."""
    ids = [i for i, a in acts.items() if a.status != 'dropped' and a.atype in ('activity', 'milestone')]
    idset = set(ids)
    order = topo(acts, ids)
    es, ef = {}, {}
    for i in order:
        x = acts[i]
        e = 0.0
        for p, t, lag in x.preds:
            if p in idset:
                e = max(e, {'FS': ef[p] + lag, 'SS': es[p] + lag,
                            'FF': ef[p] + lag - x.dur, 'SF': es[p] + lag - x.dur}[t])
        es[i], ef[i] = e, e + x.dur
    if target not in ef:
        return [], 0.0
    chain, cur = [target], target
    for _ in range(len(order)):
        x = acts[cur]
        nxt = None
        for p, t, lag in x.preds:
            if p in idset:
                c = {'FS': ef[p] + lag, 'SS': es[p] + lag,
                     'FF': ef[p] + lag - x.dur, 'SF': es[p] + lag - x.dur}[t]
                if abs(c - es[cur]) < 1e-9:
                    nxt = p
                    break
        if nxt is None:
            break
        chain.append(nxt)
        cur = nxt
    chain.reverse()
    return chain, ef[target]


def buffers(acts, dd, base=None, load_by_actor=None):
    """Project buffers before end milestones and feeding buffers at interface milestones.

    Days are the milestone's own calendar working days.
    """
    base_items = (base or {}).get('items') if isinstance(base, dict) else None
    base_items = base_items if isinstance(base_items, dict) else {}
    out = []
    for m in sorted(acts.values(), key=lambda a: a.id):
        if m.atype != 'milestone' or m.status in ('dropped', 'complete'):
            continue
        live_succ = [s for s, _, _ in m.succs if s in acts and acts[s].status != 'dropped'
                     and acts[s].atype in ('activity', 'milestone')]
        is_end = not live_succ and m.need_by is None
        if not (is_end or m.interface):
            continue
        chain, length = _static_chain(acts, m.id)
        size = length / 2.0
        work = [acts[i] for i in chain if acts[i].dur > 0]
        total = sum(a.dur for a in work)
        done = sum(a.dur * a.pct / 100.0 for a in work)
        complete = done / total if total else (1.0 if m.status == 'complete' else 0.0)
        projected = m.efi if m.efi is not None else (0.0 if m.status == 'complete' else None)
        start, ref = None, None
        if m.fnlt is not None:
            start, ref = _up(m.ax, m.fnlt) - size, 'before the finish-by'
        elif m.id in base_items and to_date(base_items[m.id].get('ef')):
            start, ref = float(m.ax.up(to_date(base_items[m.id]['ef']))), 'after the baseline finish'
        consumed = None
        if size > 0 and start is not None and projected is not None:
            consumed = max(0.0, projected - start)
        share = consumed / size if consumed is not None and size > 0 else None
        if share is None:
            signal = None
        elif share <= complete + 1e-9:
            signal = 'green'
        elif share <= complete + 1 / 3.0:
            signal = 'yellow'
        else:
            signal = 'red'
        holders = sorted({acts[i].holder for i in chain if acts[i].holder and _logic(acts[i])})
        drum = None
        if load_by_actor:
            cands = [(load_by_actor[h]['free'], h) for h in holders if h in load_by_actor]
            if cands:
                f, h = min(cands)
                drum = {'actor': h, 'free_minutes': f}
        out.append({
            'milestone': m.id, 'holon': m.holon, 'title': m.title,
            'type': 'project' if is_end else 'feeding',
            'chain': chain, 'chain_days': out_num(length),
            'size_days': out_num(size), 'consumed_days': out_num(consumed),
            'consumed_share': out_num(share), 'chain_complete': out_num(complete),
            'signal': signal, 'placed': ref, 'drum': drum,
            'rule': 'size = half the chain; signal green when consumed share <= chain complete, '
                    'yellow within a third more, red beyond',
        })
    return out


def plan_dir_for(items_path):
    base = os.path.dirname(os.path.abspath(items_path)) if items_path and items_path != '-' else os.getcwd()
    return os.path.join(base, 'plan')


def list_baselines(plan_dir):
    out = []
    try:
        names = os.listdir(plan_dir)
    except OSError:
        return out
    for n in names:
        m = re.fullmatch(r'baseline-(\d+)\.json', n)
        if m:
            out.append((int(m.group(1)), os.path.join(plan_dir, n)))
    return sorted(out)


def load_baseline(plan_dir, name=None):
    """The named baseline (by n, 'baseline-n', a name, or a path); the newest when none is named."""
    if isinstance(name, str) and name.endswith('.json') and os.path.isfile(name):
        cands = [(0, name)]
    else:
        cands = list_baselines(plan_dir)
    picked = None
    if name is None or (isinstance(name, str) and name.endswith('.json')):
        picked = cands[-1] if cands else None
    else:
        key = str(name)
        mnum = re.fullmatch(r'(?:baseline-)?(\d+)', key)
        for n, p in reversed(cands):
            if mnum and n == int(mnum.group(1)):
                picked = (n, p)
                break
            try:
                with open(p, encoding='utf-8') as f:
                    if (json.load(f) or {}).get('name') == key:
                        picked = (n, p)
                        break
            except (OSError, ValueError):
                continue
    if not picked:
        return None
    try:
        with open(picked[1], encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault('n', picked[0])
    data['path'] = picked[1]
    return data


def variance(acts, base):
    """Current minus baseline in each card's working days, per card and per milestone (positive = later)."""
    if not isinstance(base, dict) or not isinstance(base.get('items'), dict):
        return None
    bi = base['items']
    items, miles = {}, {}
    for a in acts.values():
        if a.status == 'dropped' or a.atype in ('summary', 'unit'):
            continue
        b = bi.get(a.id)
        if not isinstance(b, dict):
            items[a.id] = {'status': 'new'}
            continue
        bs, bf = to_date(b.get('es')), to_date(b.get('ef'))
        if a.status == 'complete':
            cs = a.ax.up(a.astart) if a.astart else None
            cf = a.ax.up(a.afinish) if a.afinish else None
        else:
            cs, cf = a.esi, a.efi
        sv = (cs - a.ax.up(bs)) if (cs is not None and bs) else None
        fv = (cf - a.ax.up(bf)) if (cf is not None and bf) else None
        st = None if fv is None else ('late' if fv > 0 else 'early' if fv < 0 else 'on')
        row = {'start_days': out_num(sv), 'finish_days': out_num(fv), 'status': st,
               'baseline_finish': bf.isoformat() if bf else None}
        items[a.id] = row
        if a.atype == 'milestone':
            miles[a.id] = row
    removed = sorted(i for i in bi if i not in acts)
    return {'baseline': {'n': base.get('n'), 'name': base.get('name')},
            'items': items, 'milestones': miles, 'removed': removed}


def earned_value(acts, dd, base, teas):
    """PV, EV, AC in minutes of TEA against the named baseline; SPI and CPI; per holon too.

    PV spreads each card's budget evenly over its baseline span in calendar days. AC is null
    (and so CV and CPI) when no TEA is held for the cards in scope.
    """
    spent = {}
    for t in teas:
        c = field(t, 'card')
        m = num(field(t, 'minutes'), 0.0) or 0.0
        if isinstance(c, str) and c:
            spent[c] = spent.get(c, 0.0) + m
    bi = base.get('items') if isinstance(base, dict) and isinstance(base.get('items'), dict) else None
    per = {}

    def bucket(h):
        return per.setdefault(h or '', {'pv': 0.0, 'ev': 0.0, 'ac': 0.0, 'ac_known': False, 'bac': 0.0,
                                        'minutes_done': 0.0, 'minutes_total': 0.0})

    scope = set(bi) if bi is not None else {i for i, a in acts.items()
                                            if a.atype in ('activity', 'milestone')}
    for cid in sorted(scope):
        a = acts.get(cid)
        b = bi.get(cid) if bi is not None else None
        if a is not None and (a.status == 'dropped' or a.atype in ('summary', 'loe', 'unit')):
            continue
        holon = a.holon if a else str((b or {}).get('holon') or '')
        bud = num((b or {}).get('minutes'), None) if b is not None else None
        if bud is None:
            bud = a.minutes if a else 0.0
        bud = bud or 0.0
        k = bucket(holon)
        k['bac'] += bud
        k['minutes_total'] += bud
        pct = a.pct if a else 0.0
        k['ev'] += bud * pct / 100.0
        k['minutes_done'] += bud * pct / 100.0
        ac = spent.get(cid)
        if ac is None and a is not None:
            ac = num(field(a.item, 'tea_minutes'), None)
            if ac is None:
                ac = num(field(a.item, 'actual_minutes'), None)
        if ac is not None:
            k['ac'] += ac
            k['ac_known'] = True
        if b is not None:
            bs, bf = to_date(b.get('es')), to_date(b.get('ef'))
            if bs and bf:
                s0, f0 = (bs - dd).days, (bf - dd).days
                frac = (1.0 if f0 <= 0 else 0.0) if f0 <= s0 else max(0.0, min(1.0, (0 - s0) / (f0 - s0)))
                k['pv'] += bud * frac

    def shape(k):
        pv = k['pv'] if bi is not None else None
        ac = k['ac'] if k['ac_known'] else None
        spi = (k['ev'] / pv) if pv else None
        cpi = (k['ev'] / ac) if ac else None
        return {'PV': out_num(pv), 'EV': out_num(k['ev']), 'AC': out_num(ac),
                'BAC': out_num(k['bac']), 'SV': out_num(k['ev'] - pv) if pv is not None else None,
                'CV': out_num(k['ev'] - ac) if ac is not None else None,
                'SPI': out_num(spi) if spi is not None else None,
                'CPI': out_num(cpi) if cpi is not None else None,
                'EAC': out_num(k['bac'] / cpi) if cpi else None,
                'minutes_done': out_num(k['minutes_done']), 'minutes_total': out_num(k['minutes_total'])}

    tot = {'pv': 0.0, 'ev': 0.0, 'ac': 0.0, 'ac_known': False, 'bac': 0.0, 'minutes_done': 0.0,
           'minutes_total': 0.0}
    for k in per.values():
        for f in tot:
            tot[f] = (tot[f] or k[f]) if f == 'ac_known' else tot[f] + k[f]
    return shape(tot), {h: shape(k) for h, k in sorted(per.items())}, \
        {'baseline': {'n': base.get('n'), 'name': base.get('name')} if isinstance(base, dict) else None,
         'unit': 'minutes of TEA'}


def score_lines(commits, teas, sights, data_date):
    """Commitments kept over made, TEA invested, value sighted; overall and per holon."""
    per = {}

    def b(h):
        return per.setdefault(h or '', {'commitments_made': 0, 'commitments_kept': 0, 'kept_on_time': 0,
                                        'open_past_due': 0, 'tea_minutes': 0.0,
                                        'value_sighted': 0, 'value_sighted_sum': 0.0})
    for c in commits:
        h = str(field(c, 'holon') or '')
        k = b(h)
        status = str(field(c, 'status') or field(c, 'state') or '').lower()
        if status in ('released', 'returned'):
            continue
        k['commitments_made'] += 1
        kept_ts = field(c, 'kept_ts') or field(c, 'kept_at') or field(c, 'done_ts')
        by = to_date(field(c, 'by'))
        if status in ('kept', 'kept-unwitnessed', 'done', 'delivered') or kept_ts or field(c, 'kept') is True:
            k['commitments_kept'] += 1
            kd = to_date(kept_ts) if isinstance(kept_ts, str) else None
            if by and kd and kd <= by:
                k['kept_on_time'] += 1
        elif by and by < data_date:
            k['open_past_due'] += 1
    for t in teas:
        b(str(field(t, 'holon') or ''))['tea_minutes'] += num(field(t, 'minutes'), 0.0) or 0.0
    for s in sights:
        k = b(str(field(s, 'holon') or ''))
        k['value_sighted'] += 1
        k['value_sighted_sum'] += num(field(s, 'value'), 0.0) or 0.0
    tot = {'commitments_made': 0, 'commitments_kept': 0, 'kept_on_time': 0, 'open_past_due': 0,
           'tea_minutes': 0.0, 'value_sighted': 0, 'value_sighted_sum': 0.0}
    for k in per.values():
        for f in tot:
            tot[f] += k[f]

    def fin(k):
        o = {f: out_num(v) for f, v in k.items()}
        o['commitments_kept_share'] = out_num(k['commitments_kept'] / k['commitments_made']) if k['commitments_made'] else None
        return o
    return fin(tot), {h: fin(k) for h, k in sorted(per.items())}


def as_of(cards, commits, teas, sights, ext, hints):
    """Per holon, the newest line time seen (items' own times, published lines, the fold's hints)."""
    best = {}

    def see(h, ts):
        t = parse_ts(ts) if isinstance(ts, str) else None
        if not h or t is None:
            return
        if h not in best or t > best[h][0]:
            best[h] = (t, ts)
    for h, ts in (hints or {}).items():
        see(h, ts)
    for it in list(cards) + list(commits) + list(teas) + list(sights):
        h = str(field(it, 'holon') or '')
        for k in ('as_of', 'updated', 'last_ts', 'ts'):
            v = field(it, k)
            if isinstance(v, str):
                see(h, v)
    for ev in ext:
        see(str(ev.get('holon') or ''), ev.get('ts'))
    return {h: v[1] for h, v in sorted(best.items())}


# ---------------------------------------------------------------- the whole run

def _prepare(items, calendar, data_date, external, warnings, calendars=None):
    home = calendar if isinstance(calendar, Calendar) else Calendar(calendar, warnings)
    dd = to_date(data_date) or dt.date.today()
    hcals = {}
    if isinstance(calendars, dict):
        for h, c in calendars.items():
            if isinstance(c, (dict, Calendar)):
                hcals[str(h)] = c if isinstance(c, Calendar) else Calendar(c, warnings)
    cache = {}

    def place(holon):
        cal = hcals.get(holon, home)
        if id(cal) not in cache:
            cache[id(cal)] = (cal, Axis(dd, cal))
        return cache[id(cal)]
    cards, commits, teas, sights, rel_map, hints = split_items(items)
    ext = external if isinstance(external, list) else []
    acts = build_acts(cards, place, dd, warnings)
    nest(acts, warnings)
    ext_by_id = link_acts(acts, rel_map, ext, dd, warnings)
    return home, hcals, dd, acts, (cards, commits, teas, sights, hints), ext, ext_by_id


LIVE_COMMITMENT = (None, 'open', 'claimed')


def commitment_row(a, x, dd, me=None):
    """One commitment made on card a, in its full shape: who to whom, the due date, the card's
    computed finish (its last day of work), the buffer (due less that day, calendar days; negative is a
    commitment the network cannot keep) against the buffer the committor stated (minutes, read
    in the holder's working days), and its state. Only a live commitment is compared; a released,
    declined or retracted one is shown and never compared. `delivered` is the committor's word
    (state `claimed`); `kept` is the committee's."""
    due = to_date(x.get('due_by'))
    live = x.get('state') in LIVE_COMMITMENT
    sched = a.es is not None and a.ef is not None
    # the computed finish is the last day of work (a card done by the end of its due date keeps it): the day the work's
    # last moment lies in, on the card's own calendar; a zero-length card finishes on its own date
    fin = None
    if sched:
        fin = (a.ax.date_of(math.ceil(a.efi - 1e-9) - 1) if a.rem and a.rem > 0 and a.efi is not None
               else dd + dt.timedelta(days=int(math.floor(a.ef + 1e-9))))
    buf = (due - fin).days if (live and sched and due) else None
    mpd = a.cal.actor_minutes(a.holder) if a.cal else None
    stated = num(x.get('buffer'), None)
    stated_days = round(stated / mpd, 6) if (stated is not None and mpd) else None
    committor, committee = x.get('for'), x.get('committee')
    return {
        'commitment': x.get('commitment'), 'committor': committor, 'committee': committee,
        'direction': ('given' if me and committor == me else 'received' if me and committee == me else None),
        'delivered_by': a.id, 'due_by': x.get('due_by'),
        'state': {'claimed': 'delivered'}.get(x.get('state'), x.get('state') or 'open'),
        'computed_finish': fin.isoformat() if fin else None,
        'buffer_days': buf, 'stated_buffer_minutes': out_num(stated), 'stated_buffer_days': out_num(stated_days),
        'signal': (None if buf is None else 'cannot keep' if buf < 0 else
                   'inside its buffer' if stated_days is not None and buf < stated_days else 'safe'),
        'compared': buf is not None, 'as_of': dd.isoformat(),
    }


def _item_out(a, dd, near):
    def d(t):
        return (dd + dt.timedelta(days=int(math.floor(t + 1e-9)))).isoformat() if t is not None else None
    sched = a.es is not None
    last = None
    if sched and a.efi is not None:
        last = a.ax.date_of(math.ceil(a.efi - 1e-9) - 1).isoformat() if a.rem and a.rem > 0 else d(a.ef)
    return {
        'id': a.id, 'holon': a.holon, 'title': a.title, 'kind': a.kind, 'type': a.atype,
        'holder': a.holder, 'codes': a.codes, 'status': a.status,
        'within': a.within, 'holds': list(a.kids),
        'minutes': out_num(a.minutes), 'dur_days': out_num(a.dur), 'remaining_days': out_num(a.rem),
        'percent_complete': out_num(a.pct),
        'ES': out_num(a.esi, 6), 'EF': out_num(a.efi, 6), 'LS': out_num(a.lsi, 6), 'LF': out_num(a.lfi, 6),
        'TF': out_num(a.tf, 6), 'FF': out_num(a.ff, 6),
        'preds': [{'id': p, 'type': t, 'lag': out_num(lag)} for p, t, lag in a.preds],   # the logic as run: units routed
        'start': d(a.es) if sched else None, 'finish': d(a.ef) if sched else None,
        'late_start': d(a.ls) if sched else None, 'late_finish': d(a.lf) if sched else None,
        'last_day': last,
        'calendar': a.cal.kind(),
        'critical': bool(sched and a.tf is not None and a.tf <= 0 and a.atype != 'loe'),
        'near_critical': bool(sched and a.tf is not None and 0 < a.tf <= near),
        'system_critical': a.system,
        'actual_start': a.astart.isoformat() if a.astart else None,
        'actual_finish': a.afinish.isoformat() if a.afinish else None,
        'constraints': {k: v for k, v in (
            ('start_no_earlier', d(a.snet)), ('finish_no_later', d(a.fnlt)), ('need_by', d(a.need_by)),
            ('start_on', d(a.mso)), ('finish_on', d(a.mfo)),
            ('as_late_as_possible', True if a.alap else None)) if v is not None},
        'variance_days': None,
        # each commitment made on this card, compared with its computed finish (compared, never obeyed)
        'commitments': [commitment_row(a, x, dd) for x in getattr(a, 'committed_by', [])],
    }


def run(items, calendar=None, data_date=None, baseline=None, external=None, near=DEFAULT_NEAR_DAYS,
        level_actors=None, calendars=None, me=None):
    """The whole engine over folded items. Returns a JSON-ready dict (see the module docstring).

    `calendar` is the home calendar, the fallback. `calendars` maps holon id -> that holon's
    calendar (dict or Calendar); each card is scheduled on its own holon's calendar, so every
    player holding the same lines of a cell computes the same float for its cards.
    `baseline` is a loaded baseline dict (see load_baseline) or None. `external` is a list of
    published event dicts from other holons. `level_actors` lists actors whose cards are leveled.
    `me` is the reader's actor id: each commitment then says its direction (given or received).
    """
    warnings = []
    near = num(near, DEFAULT_NEAR_DAYS)
    home, hcals, dd, acts, (cards, commits, teas, sights, hints), ext, ext_by_id = \
        _prepare(items, calendar, data_date, external, warnings, calendars)
    ties = []
    leveled = None
    order, late_end = passes(acts)
    if level_actors:
        for actor in level_actors:
            ties.extend(level(acts, actor))
        before = {i: acts[i].ef for i in order}
        for a in acts.values():
            a.reset()
        order, late_end = passes(acts, ties)
        leveled = {'actors': list(level_actors), 'ties': [list(t) for t in ties],
                   'moved': sorted(i for i in order if (acts[i].ef or 0) != (before.get(i) or 0)),
                   'rule': "one actor's remaining cards chained finish-to-start by least late start; local only"}
    rows = {}
    for a in sorted(acts.values(), key=lambda x: (x.es if x.es is not None else float('inf'), x.id)):
        if a.status == 'dropped':
            continue
        rows[a.id] = _item_out(a, dd, near)
        for r in rows[a.id]['commitments']:
            r['direction'] = ('given' if me and r['committor'] == me else 'received' if me and r['committee'] == me else None)
    var = variance(acts, baseline)
    if var:
        for i, v in var['items'].items():
            if i in rows:
                rows[i]['variance_days'] = v.get('finish_days')
    crit = [i for i in order if acts[i].tf <= 0]
    load_rows, load_by_actor = load(acts, home, dd)
    bufs = buffers(acts, dd, baseline, load_by_actor)
    drum = None
    drums = [b['drum'] for b in bufs if b['type'] == 'project' and b['drum']]
    if drums:
        drum = min(drums, key=lambda x: (x['free_minutes'], x['actor']))
        drum = dict(drum, note='reported, never imposed')
    ev_all, ev_holon, ev_meta = earned_value(acts, dd, baseline, teas)
    sc_all, sc_holon = score_lines(commits, teas, sights, dd)
    seen = as_of(cards, commits, teas, sights, ext, hints)
    score = {}
    for h in sorted(set(ev_holon) | set(sc_holon)):
        e = ev_holon.get(h) or {}
        s = sc_holon.get(h) or {}
        score[h] = {'earned': e.get('EV'), 'planned': e.get('PV'), 'minutes_done': e.get('minutes_done'),
                    'minutes_total': e.get('minutes_total'), 'spi': e.get('SPI'), 'as_of': seen.get(h)}
        score[h].update({k: v for k, v in s.items()})
    finish = max((acts[i].ef for i in order), default=None)
    externals = []
    for eid, ev in sorted(ext_by_id.items()):
        d = _ext_date(ev)
        externals.append({'id': eid, 'holon': ev.get('holon'), 'type': ev.get('type'),
                          'title': field(ev, 'title'), 'date': d.isoformat() if d else None,
                          'ts': ev.get('ts')})
    kinds = {home.kind()} | {c.kind() for c in hcals.values()}
    return {
        'v': 1, 'engine': ENGINE,
        'data_date': dd.isoformat(),
        'calendar': 'working-days' if 'working-days' in kinds else 'calendar-days',
        'calendars': {h: c.kind() for h, c in sorted(hcals.items())},
        'gameclock': gameclock(dd, home),
        'items': list(rows.values()),
        'path': {'critical': crit, 'system': sorted(i for i, a in acts.items() if a.system),
                 'driving': driving_path(acts, order),
                 'near_critical': [i for i in order if 0 < acts[i].tf <= near],
                 'finish': (dd + dt.timedelta(days=int(finish))).isoformat() if finish is not None else None,
                 'finish_day': out_num(finish), 'late_end_day': out_num(late_end)},
        'negative_float': [i for i in order if acts[i].tf < 0],
        'constraints': constraints(acts),
        'baseline': {'n': baseline.get('n'), 'name': baseline.get('name'),
                     'path': baseline.get('path')} if isinstance(baseline, dict) else None,
        'variance': var,
        'rollup': rollup(acts, dd),
        'holarchy': holarchy(acts),
        'commitments': sorted((dict(r, holon=row['holon']) for row in rows.values() for r in row['commitments']),
                              key=lambda r: (r['buffer_days'] is None, r['buffer_days'] if r['buffer_days'] is not None else 0,
                                             r['commitment'] or '')),
        'buffers': bufs,
        'drum': drum,
        'load': load_rows,
        'load_by_actor': load_by_actor,
        'leveled': leveled,
        'ev': dict(ev_all, **ev_meta),
        'score': score,
        'score_lines': sc_all,
        'external': externals,
        'as_of': seen,
        'warnings': warnings,
    }


def schedule(items, calendar=None, data_date=None, **kw):
    """SCHEMA.md's name for the whole: schedule(items, calendar) -> the run's result."""
    return run(items, calendar, data_date, **kw)


def freeze(items, name, calendar=None, data_date=None, plan_dir='plan', calendars=None, depth=None):
    """Compute the schedule and write plan/baseline-<n>.json (n the next integer). Returns the path.

    The same at every depth: a weekly freeze writes a baseline exactly as a seasonal one does;
    `depth` (weekly, seasonal, ...) is recorded in the file, and names it when no name is given.
    """
    res = run(items, calendar, data_date, calendars=calendars)
    os.makedirs(plan_dir, exist_ok=True)
    have = list_baselines(plan_dir)
    n = (have[-1][0] + 1) if have else 1
    items_out = {}
    for r in res['items']:
        es = r['start'] or r['actual_start']
        ef = r['finish'] or r['actual_finish']
        items_out[r['id']] = {'title': r['title'], 'holon': r['holon'], 'kind': r['kind'],
                              'type': r['type'], 'holder': r['holder'], 'minutes': r['minutes'],
                              'dur_days': r['dur_days'], 'es': es, 'ef': ef,
                              'ls': r['late_start'], 'lf': r['late_finish'], 'TF': r['TF']}
    dep = str(depth) if isinstance(depth, str) and depth.strip() else None
    doc = {'v': 1, 'n': n, 'depth': dep,
           'name': str(name or (f'{dep}-{res["data_date"]}' if dep else f'baseline-{n}')),
           'data_date': res['data_date'],
           'calendar': res['calendar'], 'finish': res['path']['finish'], 'items': items_out}
    path = os.path.join(plan_dir, f'baseline-{n}.json')
    with open(path, 'x', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    return path


# ---------------------------------------------------------------- reading files, rendering

def read_json(path):
    if path == '-':
        return json.load(sys.stdin)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def markdown(res):
    """A readable rendering of a run's result."""
    L = [f"# Schedule as of {res['data_date']} ({res['calendar']})", '']
    gc = res.get('gameclock') or {}
    if gc:
        where = f"span {gc['span']}, day {gc['day_of_span']}" if gc.get('span') else 'between spans'
        L.append(f"Gameclock: {gc['season']} {gc['season_year']}, day {gc['day_of_season']} "
                 f"of {gc['season_length']}; {where}.")
        L.append('')
    L.append('| ID | Title | Holon | Dur | ES | EF | LS | LF | TF | FF | CP |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in res['items']:
        cp = '**' if r['critical'] else ('near' if r['near_critical'] else '')
        L.append(f"| {r['id'][:12]} | {(r['title'] or '')[:40]} | {(r['holon'] or '')[:10]} | "
                 f"{r['remaining_days'] if r['remaining_days'] is not None else ''} | "
                 f"{r['start'] or r['status']} | {r['finish'] or ''} | {r['late_start'] or ''} | "
                 f"{r['late_finish'] or ''} | {'' if r['TF'] is None else r['TF']} | "
                 f"{'' if r['FF'] is None else r['FF']} | {cp} |")
    p = res['path']
    L += ['', f"Finish: {p['finish']} (day {p['finish_day']}). Critical (TF <= 0): "
          f"{', '.join(p['critical']) or 'none'}.",
          f"Negative float: {', '.join(res['negative_float']) or 'none'}."]
    if res.get('baseline'):
        L.append(f"Baseline: {res['baseline']['name']} (n {res['baseline']['n']}).")
    cs = res.get('constraints') or {}
    if cs.get('count'):
        L += ['', f"Constraints: {cs['count']} on {cs['cards_constrained']} of {cs['cards']} cards "
              f"(share {cs['share_constrained']}); hard {cs['hard']}, soft {cs['soft']}; "
              f"on activities {cs['on_activities']}; no reason {cs['no_reason']}, no imposer "
              f"{cs['no_imposer']}; negative float caused {cs['negative_float_days']} days.",
              '', '| Card | Kind | Date | Hard | Source | Neg. float | Delay | Defects |',
              '|---|---|---|---|---|---|---|---|']
        for c in cs['items']:
            L.append(f"| {c['card'][:12]} | {c['kind']} | {c['date'] or ''} | {'yes' if c['hard'] else ''} | "
                     f"{c['source'] or ''} | {'' if c['negative_float_days'] is None else c['negative_float_days']} | "
                     f"{'' if c['delay_days'] is None else c['delay_days']} | {', '.join(c['defects'])} |")
    if res['buffers']:
        L += ['', '| Buffer | Milestone | Size | Consumed | Chain complete | Signal |', '|---|---|---|---|---|---|']
        for b in res['buffers']:
            L.append(f"| {b['type']} | {b['milestone'][:12]} | {b['size_days']} | {b['consumed_days']} | "
                     f"{b['chain_complete']} | {b['signal'] or ''} |")
    if res.get('drum'):
        L.append(f"\nDrum (reported, never imposed): {res['drum']['actor']}, "
                 f"{res['drum']['free_minutes']} free minutes.")
    if res['load_by_actor']:
        L += ['', '| Actor | Committed | Capacity | Free | Over on |', '|---|---|---|---|---|']
        for a, v in res['load_by_actor'].items():
            L.append(f"| {a} | {v['committed']} | {v['capacity']} | {v['free']} | "
                     f"{', '.join(v['over_days']) or ''} |")
    ev = {k: ('n/a' if v is None else v) for k, v in res['ev'].items()}
    L += ['', f"Earned value ({ev['unit']}): PV {ev['PV']} · EV {ev['EV']} · AC {ev['AC']} · "
          f"SPI {ev['SPI']} · CPI {ev['CPI']}" + ('' if res.get('baseline') else ' (no baseline named)') + '.']
    s = res['score_lines']
    L.append(f"Score: commitments kept {s['commitments_kept']} of {s['commitments_made']} · "
             f"TEA invested {s['tea_minutes']} min · value sighted {s['value_sighted']}.")
    if res['as_of']:
        L += ['', 'As of: ' + ' · '.join(f'{h} {t}' for h, t in res['as_of'].items())]
    if res['warnings']:
        L += ['', 'Warnings:'] + [f'- {w}' for w in res['warnings']]
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='schedule.py', description=__doc__.split('\n\n')[0],
                                 epilog='The rules are written out in the module docstring '
                                        '(python3 -c "import schedule; help(schedule)").',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    r = sub.add_parser('run', help='schedule the items and print JSON (or --markdown)')
    r.add_argument('items', help='folded items as JSON (state.json or a list of cards); - for stdin')
    r.add_argument('--calendar', help='calendar.json')
    r.add_argument('--data-date', help='YYYY-MM-DD (default: today)')
    r.add_argument('--baseline', help='baseline n or name (default: the newest in --plan-dir)')
    r.add_argument('--no-baseline', action='store_true', help='measure against no baseline')
    r.add_argument('--plan-dir', help="where baselines live (default: plan/ beside ITEMS)")
    r.add_argument('--external', nargs='*', action='extend', default=[],
                   help="other holons' published/*.jsonl")
    r.add_argument('--level', action='append', default=[], help="level one actor's cards (crude, local)")
    r.add_argument('--holon-calendar', action='append', default=[], metavar='HOLON=PATH',
                   help="a holon's own calendar.json; its cards are scheduled on it (the home calendar "
                        "is the fallback)")
    r.add_argument('--near', type=float, default=DEFAULT_NEAR_DAYS, help='near-critical threshold in days')
    r.add_argument('--markdown', action='store_true', help='print a readable table instead of JSON')
    f = sub.add_parser('freeze', help='write plan/baseline-<n>.json')
    f.add_argument('items')
    f.add_argument('--name', help='the baseline name (default: DEPTH-DATE, else baseline-N)')
    f.add_argument('--calendar')
    f.add_argument('--data-date')
    f.add_argument('--plan-dir')
    f.add_argument('--depth', help='the Turn depth this freeze belongs to (weekly, seasonal, ...)')
    f.add_argument('--holon-calendar', action='append', default=[], metavar='HOLON=PATH')
    c = sub.add_parser('clock', help='where a date sits on the Gameclock; the turnings and moons of a span')
    c.add_argument('date', nargs='?', help='YYYY-MM-DD (default: today)')
    c.add_argument('--to', help='list turnings and moons from DATE to this date (default: the season of DATE)')
    c.add_argument('--calendar')
    a = ap.parse_args(argv)
    try:
        cal = read_json(a.calendar) if getattr(a, 'calendar', None) else None
        if a.cmd == 'clock':
            c_ = Calendar(cal)
            g = gameclock(a.date, c_)
            lo = to_date(a.date) if a.to else to_date(g['season_start'])
            hi = to_date(a.to) if a.to else (to_date(g['next_turning']) or lo)
            print(json.dumps({'gameclock': g, 'from': lo.isoformat(), 'to': hi.isoformat(),
                              'turnings': turnings_between(lo, hi, c_), 'moons': moons(lo, hi, c_)},
                             ensure_ascii=False, indent=1))
            return 0
        hc = {}
        for spec in getattr(a, 'holon_calendar', None) or []:
            h, sep, path = spec.partition('=')
            if not sep or not h or not path:
                print(f'schedule.py: --holon-calendar wants HOLON=PATH, not {spec!r}', file=sys.stderr)
                return 2
            hc[h] = read_json(path)
        if a.cmd == 'freeze':
            pd = a.plan_dir or plan_dir_for(a.items)
            print(json.dumps({'baseline': freeze(read_json(a.items), a.name, cal, a.data_date, pd,
                                                 hc or None, a.depth)}))
            return 0
        if a.cmd == 'run':
            pd = a.plan_dir or plan_dir_for(a.items)
            base = None if a.no_baseline else load_baseline(pd, a.baseline)
            if a.baseline and base is None:
                print(f'schedule.py: no baseline {a.baseline!r} in {pd}', file=sys.stderr)
                return 2
            ext = load_external(a.external)
            res = run(read_json(a.items), cal, a.data_date, base, ext, a.near, a.level, hc or None)
            sys.stdout.write(markdown(res) if a.markdown else
                             json.dumps(res, ensure_ascii=False, indent=1) + '\n')
            return 0
    except ScheduleError as e:
        print(f'schedule.py: {e}', file=sys.stderr)
        return 1
    except (OSError, ValueError) as e:
        print(f'schedule.py: {e}', file=sys.stderr)
        return 2
    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
