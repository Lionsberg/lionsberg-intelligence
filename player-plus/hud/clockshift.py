#!/usr/bin/env python3
"""clockshift.py: move a sample state's clock to now, keeping every interval.

A fixture is a photograph of a house at one moment (its `generated_at`). Served days later, its
top line says a day that has passed, and a by-when that was "tomorrow" reads as late. With
`serve.py --fixture NAME --shift-clock` every ISO time in the fixture moves forward by the same
amount (now minus `generated_at`), so the sample behaves as a live house would: as of now, the
same things owed in the same order, the same days to spare. Nothing else changes. Tests never
use it; it exists for a person walking the sample. Standard library only.
"""
import datetime as _dt
import re

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse(s):
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fmt(d, like):
    out = d.isoformat(timespec="seconds")
    return out.replace("+00:00", "Z") if like.endswith("Z") else out


def shift(state, now=None):
    """Return a copy of `state` with every ISO time (and every bare date) moved by now - generated_at."""
    if not isinstance(state, dict):
        return state
    base = _parse(str(state.get("generated_at") or "")) if state.get("generated_at") else None
    if base is None:
        return state
    now = now or _dt.datetime.now(base.tzinfo)
    delta = now - base
    if abs(delta.total_seconds()) < 60:
        return state
    days = round(delta.total_seconds() / 86400)

    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str):
            if _ISO.match(x):
                d = _parse(x)
                return _fmt(d + delta, x) if d else x
            if _DAY.match(x):
                try:
                    return (_dt.date.fromisoformat(x) + _dt.timedelta(days=days)).isoformat()
                except ValueError:
                    return x
        return x

    # weekday words in the sample's own text ("by Tuesday", "Saturday morning") move with the dates,
    # so a card due Tuesday still says Tuesday when its date has moved to a Thursday
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    import re as _re
    pat = _re.compile(r"\b(" + "|".join(names) + r")\b")
    def shift_words(x):
        if isinstance(x, dict):
            return {k: shift_words(v) for k, v in x.items()}
        if isinstance(x, list):
            return [shift_words(v) for v in x]
        if isinstance(x, str) and not _ISO.match(x) and not _DAY.match(x):
            return pat.sub(lambda m: names[(names.index(m.group(1)) + days) % 7], x)
        return x
    out = shift_words(walk(state))
    out["_shifted"] = {"from": state.get("generated_at"), "by_seconds": int(delta.total_seconds())}
    return out
