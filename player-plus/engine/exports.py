#!/usr/bin/env python3
"""exports.py — the plan as other tools and other eyes read it: MS Project XML, one HTML wall, CSV.

Standard library only. Pure functions over the schedule's result (`schedule.run`) and the folded
items; each returns a string and reads no file, no clock and no global. The same inputs give the
same bytes.

  mspdi(res, items, project_name='', calendar=None) -> str
      Microsoft Project XML (MSPDI). Every scheduled row is a Task: UID and ID in outline order,
      Name, Start, Finish, Duration (PT#H#M#S from the row's minutes), Milestone, OutlineLevel
      (the depth along `within`), Summary (1 for a unit), and a PredecessorLink per link
      (Type 0 FF · 1 FS · 2 SF · 3 SS; LinkLag in tenths of a minute, LagFormat 7 = days).
      Times: a working day opens at DAY_START and lasts the holder's minutes a day; a fractional
      day index is that share of the way through the day.
  wall_html(res, items, plan=None, title='The Wall', leveled=False) -> str
      One self-contained page (inline CSS and script; no external URL, no network): a column per
      ISO week by start (by the leveled start when `leveled` and `plan['chain']['leveled']` are
      given), a sticky per open card, coloured by state (critical · near · free), every
      predecessor link between two notes drawn as an SVG line. A click opens the card's detail in
      place, directly under its note; the ×, Escape, or a second click on the note closes it,
      and the scroll position is kept. Filters at the top: holder, unit, stream and state.
  csv_rows(res) -> str
      id, title, type, holder, within, start, finish, TF, critical; the header first.
"""
import csv
import datetime as dt
import html
import io
import json
import math
import re

ENGINE = 'exports.py'
DAY_START_MIN = 8 * 60          # 08:00, Microsoft Project's default calendar opens the day here
DEFAULT_MINUTES_PER_DAY = 480.0  # schedule.py's DEFAULT_MINUTES_PER_DAY (32 of the day's 96 quarter-hours)
DEFAULT_NEAR_DAYS = 3.0          # schedule.py's DEFAULT_NEAR_DAYS: near-critical is 0 < TF <= this
MSPDI_LINK_TYPE = {'FF': 0, 'FS': 1, 'SF': 2, 'SS': 3}   # the MSPDI schema's PredecessorLink/Type
MSPDI_LAG_DAYS = 7               # the MSPDI schema's LagFormat for days
REL_TYPES = ('FS', 'SS', 'FF', 'SF')
NONE_WORDS = ('', '—', '-', '–')
_PRED_RE = re.compile(r'([^\s]+)\s*(FS|SS|FF|SF)?\s*([+-]\d+(?:\.\d+)?)?', re.I)
_REL_RE = re.compile(r'^\s*(FS|SS|FF|SF)?\s*([+-]?\d+(?:\.\d+)?)?\s*$', re.I)
_XML_BAD = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]')


# ---------------------------------------------------------------- small readers (null-guarded)

def _field(item, key):
    if not isinstance(item, dict):
        return None
    v = item.get(key)
    if v is None and isinstance(item.get('body'), dict):
        v = item['body'].get(key)
    return v


def _id(x):
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        return None
    s = str(x).strip()
    return None if s in NONE_WORDS else s


def _num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, str):
        m = re.search(r'-?\d+(?:\.\d+)?', x)
        x = float(m.group(0)) if m else None
    if not isinstance(x, (int, float)):
        return None
    f = float(x)
    return None if f != f or f in (float('inf'), float('-inf')) else f


def _date(x):
    if not isinstance(x, str) or not x.strip():
        return None
    try:
        return dt.date.fromisoformat(x.strip()[:10])
    except ValueError:
        return None


def _out(x):
    if x is None:
        return None
    return int(round(x)) if abs(x - round(x)) < 1e-9 else round(x, 3)


def _ids(item, rel):
    out = []
    for src in (item.get('links'), item):
        if not isinstance(src, dict):
            continue
        for k in (rel, rel + 's'):
            v = src.get(k)
            if isinstance(v, (str, int)) and _id(v):
                out.append(_id(v))
            elif isinstance(v, (list, tuple)):
                out.extend(_id(x) for x in v if _id(x))
    return out


def _parse_preds(s):
    if isinstance(s, (list, tuple)):
        s = ','.join(str(x) for x in s if isinstance(x, (str, int)))
    if not isinstance(s, str):
        return []
    out = []
    for p in re.split(r'[,;]', s):
        p = p.strip().strip('*`')
        if p and p not in NONE_WORDS:
            m = _PRED_RE.match(p)
            if m:
                out.append((m.group(1), (m.group(2) or 'FS').upper(), float(m.group(3) or 0)))
    return out


def _parse_rel(v):
    if isinstance(v, dict):
        t = str(v.get('type') or 'FS').upper()
        return (t if t in REL_TYPES else 'FS'), (_num(v.get('lag')) or 0.0)
    if isinstance(v, (list, tuple)) and v:
        t = str(v[0]).upper()
        return (t if t in REL_TYPES else 'FS'), (_num(v[1]) if len(v) > 1 and _num(v[1]) is not None else 0.0)
    if isinstance(v, str):
        m = _REL_RE.match(v)
        if m:
            return (m.group(1) or 'FS').upper(), float(m.group(2) or 0)
    return 'FS', 0.0


def links(items):
    """Every relationship the items name, read as schedule.py reads them: {(pred, succ): (type, lag)}
    from `links.predecessor` / `links.successor`, a `preds` string ('A, B SS+1') and a `rel` map
    (the typed forms win). Lags in working days."""
    pairs = {}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or _id(it.get('id')) is None:
            continue
        cid = _id(it.get('id'))
        for p in _ids(it, 'predecessor'):
            pairs.setdefault((p, cid), ('FS', 0.0))
        for s in _ids(it, 'successor'):
            pairs.setdefault((cid, s), ('FS', 0.0))
        for p, t, lag in _parse_preds(_field(it, 'preds')):
            pairs[(p, cid)] = (t, lag)
        r = _field(it, 'rel')
        if isinstance(r, dict):
            for p, v in r.items():
                if _id(p):
                    pairs[(_id(p), cid)] = _parse_rel(v)
    return {k: pairs[k] for k in sorted(pairs) if k[0] != k[1]}


def _rows(res):
    res = res if isinstance(res, dict) else {}
    return [r for r in (res.get('items') or []) if isinstance(r, dict) and _id(r.get('id'))]


def _by_item(items):
    out = {}
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and _id(it.get('id')) is not None:
            out.setdefault(_id(it.get('id')), it)
    return out


# ---------------------------------------------------------------- MSPDI

def _xml(s):
    s = _XML_BAD.sub('', '' if s is None else str(s))
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _mpd(calendar, holder):
    cal = calendar if isinstance(calendar, dict) else {}
    acts = cal.get('actors') if isinstance(cal.get('actors'), dict) else {}
    a = acts.get(holder or '') if isinstance(acts.get(holder or ''), dict) else {}
    for v in (a.get('minutes_per_day'), a.get('capacity')):
        if _num(v) is not None and _num(v) > 0:
            return _num(v)
    for v in (cal.get('minutes_per_day'), cal.get('minutes_per_actor_per_day')):
        if _num(v) is not None and _num(v) > 0:
            return _num(v)
    return DEFAULT_MINUTES_PER_DAY


def _stamp(d, minute_of_day):
    m = int(round(minute_of_day))
    return f'{d.isoformat()}T{m // 60:02d}:{m % 60:02d}:00'


def _duration(minutes):
    s = int(round((_num(minutes) or 0.0) * 60))
    s = max(s, 0)
    return f'PT{s // 3600}H{(s % 3600) // 60}M{s % 60}S'


def _outline(rows):
    """[(row, level)] depth-first along `within`; a within not held is read as the top."""
    by = {str(r['id']): r for r in rows}
    kids = {}
    tops = []
    for r in rows:
        w = _id(r.get('within'))
        (kids.setdefault(w, []) if w in by else tops).append(str(r['id']))

    def key(i):
        es = _num(by[i].get('ES'))
        return (es is None, es if es is not None else 0.0, i)

    order, seen = [], set()

    def walk(i, lvl):
        if i in seen:
            return
        seen.add(i)
        order.append((by[i], lvl))
        for k in sorted(kids.get(i, []), key=key):
            walk(k, lvl + 1)
    for t in sorted(tops, key=key):
        walk(t, 1)
    for i in sorted(by, key=key):        # anything a loop hid
        walk(i, 1)
    return order


def mspdi(res, items, project_name='', calendar=None):
    """The plan as Microsoft Project XML (MSPDI). See the module docstring."""
    rows = _rows(res)
    dd = _date((res or {}).get('data_date')) if isinstance(res, dict) else None
    cal = calendar if isinstance(calendar, dict) else {}
    day_start = _num(cal.get('day_start_minute'))
    day_start = DAY_START_MIN if day_start is None else day_start
    order = _outline(rows)
    uid = {str(r['id']): n + 1 for n, (r, _) in enumerate(order)}
    pairs = links(items)
    preds = {}
    for (p, s), tl in pairs.items():
        if p in uid and s in uid:
            preds.setdefault(s, []).append((p, tl))
    home_mpd = _mpd(cal, None)
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<Project xmlns="http://schemas.microsoft.com/project">',
           f'<Name>{_xml(project_name)}</Name>',
           f'<Title>{_xml(project_name)}</Title>',
           '<ScheduleFromStart>1</ScheduleFromStart>']
    if dd:
        out.append(f'<StartDate>{_stamp(dd, day_start)}</StartDate>')
    out += [f'<MinutesPerDay>{int(round(home_mpd))}</MinutesPerDay>', '<Tasks>']
    for r, lvl in order:
        cid = str(r['id'])
        mpd = _mpd(cal, r.get('holder'))
        is_unit = r.get('type') == 'unit'
        is_ms = r.get('type') == 'milestone'
        title = r.get('title') or ''
        out.append('<Task>')
        out.append(f'<UID>{uid[cid]}</UID>')
        out.append(f'<ID>{uid[cid]}</ID>')
        out.append(f'<Name>{_xml(cid + (" — " + title if title else ""))}</Name>')
        out.append(f'<OutlineLevel>{lvl}</OutlineLevel>')
        start = finish = None
        es, ef = _num(r.get('ES')), _num(r.get('EF'))
        sd, fd = _date(r.get('start')), _date(r.get('finish'))
        if sd and es is not None:
            start = _stamp(sd, day_start + (es - math.floor(es + 1e-9)) * mpd)
        if ef is not None and fd:
            frac = ef - math.floor(ef + 1e-9)
            if is_ms:
                finish = start
            elif frac > 1e-9:
                finish = _stamp(fd, day_start + frac * mpd)
            else:   # a whole EF is the morning after the last day: the work ends at that day's close
                ld = _date(r.get('last_day')) or fd
                finish = _stamp(ld, day_start + mpd)
        if r.get('status') == 'complete':
            a, b = _date(r.get('actual_start')), _date(r.get('actual_finish'))
            start = start or (_stamp(a, day_start) if a else None)
            finish = finish or (_stamp(b, day_start + mpd) if b else None)
        if start:
            out.append(f'<Start>{start}</Start>')
        if finish:
            out.append(f'<Finish>{finish}</Finish>')
        out.append(f'<Duration>{_duration(0 if is_ms else r.get("minutes"))}</Duration>')
        out.append('<DurationFormat>7</DurationFormat>')
        out.append(f'<Milestone>{1 if is_ms else 0}</Milestone>')
        out.append(f'<Summary>{1 if is_unit else 0}</Summary>')
        out.append(f'<Critical>{1 if r.get("critical") else 0}</Critical>')
        pc = 100 if r.get('status') == 'complete' else int(round(_num(r.get('percent_complete')) or 0))
        out.append(f'<PercentComplete>{pc}</PercentComplete>')
        tf = _num(r.get('TF'))
        if tf is not None:
            out.append(f'<TotalSlack>{int(round(tf * mpd * 10))}</TotalSlack>')
        for p, (t, lag) in preds.get(cid, []):
            out.append('<PredecessorLink>'
                       f'<PredecessorUID>{uid[p]}</PredecessorUID>'
                       f'<Type>{MSPDI_LINK_TYPE.get(t, 1)}</Type>'
                       f'<LinkLag>{int(round(lag * _mpd(cal, None) * 10))}</LinkLag>'
                       f'<LagFormat>{MSPDI_LAG_DAYS}</LagFormat>'
                       '</PredecessorLink>')
        out.append('</Task>')
    out += ['</Tasks>', '</Project>', '']
    return '\n'.join(out)


# ---------------------------------------------------------------- CSV

CSV_FIELDS = ('id', 'title', 'type', 'holder', 'within', 'start', 'finish', 'TF', 'critical')


def csv_rows(res):
    """The rows as CSV, in the schedule's order, the header first."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(CSV_FIELDS)
    for r in _rows(res):
        tf = _out(_num(r.get('TF')))
        w.writerow([str(r.get('id')), r.get('title') or '', r.get('type') or '', r.get('holder') or '',
                    r.get('within') or '', r.get('start') or '', r.get('finish') or '',
                    '' if tf is None else tf, 'true' if r.get('critical') else 'false'])
    return buf.getvalue()


# ---------------------------------------------------------------- the wall

def _leveled_map(plan):
    ch = plan.get('chain') if isinstance(plan, dict) else None
    lev = ch.get('leveled') if isinstance(ch, dict) else None
    out = {}
    if isinstance(lev, dict):
        for k, v in lev.items():
            if isinstance(v, dict):
                out[str(k)] = v
    elif isinstance(lev, list):
        for v in lev:
            if isinstance(v, dict) and _id(v.get('id') or v.get('card')):
                out[_id(v.get('id') or v.get('card'))] = v
    return out


def _monday(d):
    return d - dt.timedelta(days=d.weekday())


def _js_json(obj):
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return (s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


_CSS = """
:root { --bg:#f7f5f0; --ink:#1f1f1f; --muted:#5f5b53; --line:#d9d4c8; --col:#ffffff; --colalt:#f1eee6;
  --crit:#f6c9c4; --critb:#b3261e; --near:#fde7a9; --nearb:#a86b00; --free:#d9eed2; --freeb:#3d7a2c;
  --panel:#ffffff; --shadow:rgba(0,0,0,.18); --link:#7a746a; --linkcrit:#b3261e; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#17171a; --ink:#ece9e2; --muted:#a8a296; --line:#34333a; --col:#1f1f24; --colalt:#24242a;
  --crit:#5a2522; --critb:#ff8a80; --near:#55441a; --nearb:#ffcc66; --free:#22402a; --freeb:#8fd18a;
  --panel:#26262c; --shadow:rgba(0,0,0,.6); --link:#8d877c; --linkcrit:#ff8a80; } }
:root[data-theme="dark"] { --bg:#17171a; --ink:#ece9e2; --muted:#a8a296; --line:#34333a; --col:#1f1f24; --colalt:#24242a;
  --crit:#5a2522; --critb:#ff8a80; --near:#55441a; --nearb:#ffcc66; --free:#22402a; --freeb:#8fd18a;
  --panel:#26262c; --shadow:rgba(0,0,0,.6); --link:#8d877c; --linkcrit:#ff8a80; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:13px/1.35 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
header { padding:12px 16px 6px; }
h1 { font-size:17px; margin:0 0 2px; }
.sub { color:var(--muted); font-size:12px; margin:0 0 8px; }
.filters { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; font-size:12px; }
.filters label { display:flex; gap:4px; align-items:center; }
.filters select { font:inherit; color:var(--ink); background:var(--col); border:1px solid var(--line); border-radius:4px; padding:2px 4px; max-width:220px; }
.key span { display:inline-block; padding:1px 7px; margin-right:6px; border-radius:3px; border:1px solid var(--line); }
.key .crit { background:var(--crit); border-color:var(--critb); } .key .near { background:var(--near); border-color:var(--nearb); }
.key .free { background:var(--free); border-color:var(--freeb); }
.count { color:var(--muted); }
.scroller { overflow-x:auto; padding:0 16px 24px; }
.wall { position:relative; display:flex; gap:8px; align-items:flex-start; min-width:min-content; }
.col { width:208px; flex:0 0 208px; background:var(--col); border:1px solid var(--line); border-radius:6px; padding:6px; min-height:120px; }
.col:nth-child(even) { background:var(--colalt); }
.col h2 { font-size:11px; font-weight:600; color:var(--muted); margin:0 0 6px; }
.note { position:relative; z-index:1; padding:5px 6px; margin:0 0 6px; border-radius:3px; border:1px solid; cursor:pointer;
  box-shadow:1px 1px 3px var(--shadow); font-size:11px; overflow-wrap:anywhere; }
.note:focus-visible { outline:2px solid var(--ink); outline-offset:1px; }
.note.critical { background:var(--crit); border-color:var(--critb); border-width:2px; }
.note.near { background:var(--near); border-color:var(--nearb); }
.note.free { background:var(--free); border-color:var(--freeb); }
.note .id { font-weight:700; } .note .f { float:right; color:var(--muted); }
.note .t { display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.note .h { color:var(--muted); font-size:10px; margin-top:2px; }
.note.open { outline:2px solid var(--ink); }
.hidden { display:none !important; }
.panel { position:relative; z-index:2; background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:8px 28px 8px 8px;
  margin:-2px 0 8px; box-shadow:0 2px 8px var(--shadow); font-size:11px; overflow-wrap:anywhere; }
.panel h3 { font-size:12px; margin:0 0 4px; }
.panel dl { margin:0; display:grid; grid-template-columns:auto 1fr; gap:2px 8px; }
.panel dt { color:var(--muted); } .panel dd { margin:0; }
.panel .close { position:absolute; top:4px; right:4px; width:22px; height:22px; border:1px solid var(--line); border-radius:4px;
  background:var(--col); color:var(--ink); font:16px/18px sans-serif; cursor:pointer; padding:0; }
svg.links { position:absolute; left:0; top:0; pointer-events:none; overflow:visible; z-index:0; }
svg.links line { stroke:var(--link); stroke-width:1.2; opacity:.75; }
svg.links line.crit { stroke:var(--linkcrit); stroke-width:1.8; opacity:.9; }
@media print { .filters { display:none; } .scroller { overflow:visible; } }
"""

_JS = r"""
(function () {
  var data = JSON.parse(document.getElementById('wall-data').textContent);
  var wall = document.getElementById('wall'), svg = document.getElementById('links');
  var scroller = document.getElementById('scroller');
  var notes = {};
  Array.prototype.forEach.call(document.querySelectorAll('.note'), function (n) { notes[n.getAttribute('data-id')] = n; });
  function shown(n) { return n && !n.classList.contains('hidden'); }
  function draw() {
    var wr = wall.getBoundingClientRect();
    svg.setAttribute('width', wall.scrollWidth); svg.setAttribute('height', wall.scrollHeight);
    Array.prototype.forEach.call(svg.querySelectorAll('line'), function (l) {
      var a = notes[l.getAttribute('data-from')], b = notes[l.getAttribute('data-to')];
      if (!shown(a) || !shown(b)) { l.style.display = 'none'; return; }
      var ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      var x1 = ra.right - wr.left, y1 = ra.top + ra.height / 2 - wr.top;
      var x2 = rb.left - wr.left, y2 = rb.top + rb.height / 2 - wr.top;
      if (rb.left <= ra.left) { x1 = ra.left + ra.width / 2 - wr.left; y1 = ra.bottom - wr.top; x2 = rb.left + rb.width / 2 - wr.left; y2 = rb.top - wr.top; }
      l.setAttribute('x1', x1); l.setAttribute('y1', y1); l.setAttribute('x2', x2); l.setAttribute('y2', y2);
      l.style.display = '';
    });
  }
  function keep(fn) {
    var sx = window.scrollX, sy = window.scrollY, ox = scroller.scrollLeft;
    fn(); draw();
    window.scrollTo(sx, sy); scroller.scrollLeft = ox;
  }
  var openId = null;
  function closePanel() {
    var p = document.getElementById('panel');
    if (p) p.parentNode.removeChild(p);
    if (openId && notes[openId]) notes[openId].classList.remove('open');
    openId = null;
  }
  function row(dl, k, v) {
    var t = document.createElement('dt'); t.textContent = k;
    var d = document.createElement('dd'); d.textContent = (v === null || v === undefined || v === '') ? '—' : String(v);
    dl.appendChild(t); dl.appendChild(d);
  }
  function openPanel(id) {
    var c = data.cards[id], n = notes[id];
    var p = document.createElement('div'); p.id = 'panel'; p.className = 'panel'; p.setAttribute('role', 'dialog');
    p.setAttribute('aria-label', id);
    var x = document.createElement('button'); x.type = 'button'; x.className = 'close'; x.setAttribute('aria-label', 'Close'); x.textContent = '\u00d7';
    x.addEventListener('click', function (e) { e.stopPropagation(); keep(closePanel); });
    var h = document.createElement('h3'); h.textContent = id + ' \u00b7 ' + (c.title || '');
    var dl = document.createElement('dl');
    row(dl, 'holder', c.holder); row(dl, 'stage', c.stage); row(dl, 'state', c.state);
    row(dl, 'start', c.start); row(dl, 'finish', c.finish); row(dl, 'last day', c.last_day);
    row(dl, 'late start', c.late_start); row(dl, 'late finish', c.late_finish);
    row(dl, 'float', c.float); row(dl, 'free float', c.free_float);
    row(dl, 'preds', c.preds.join(', ')); row(dl, 'succs', c.succs.join(', ')); row(dl, 'within', c.within);
    p.appendChild(x); p.appendChild(h); p.appendChild(dl);
    p.addEventListener('click', function (e) { e.stopPropagation(); });
    n.parentNode.insertBefore(p, n.nextSibling);
    n.classList.add('open'); openId = id;
  }
  function toggle(id) {
    keep(function () { var was = openId; closePanel(); if (was !== id) openPanel(id); });
  }
  Object.keys(notes).forEach(function (id) {
    var n = notes[id];
    n.addEventListener('click', function () { toggle(id); });
    n.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(id); } });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && openId) keep(closePanel); });
  var sels = Array.prototype.slice.call(document.querySelectorAll('.filters select'));
  function apply() {
    keep(function () {
      var want = {}, shownN = 0;
      sels.forEach(function (s) { want[s.getAttribute('data-key')] = s.value; });
      Object.keys(notes).forEach(function (id) {
        var n = notes[id], ok = true;
        Object.keys(want).forEach(function (k) { if (want[k] !== '*' && n.getAttribute('data-' + k) !== want[k]) ok = false; });
        n.classList.toggle('hidden', !ok);
        if (ok) shownN++;
      });
      if (openId && !shown(notes[openId])) closePanel();
      document.getElementById('count').textContent = shownN + ' of ' + Object.keys(notes).length + ' open cards shown';
    });
  }
  sels.forEach(function (s) { s.addEventListener('change', apply); });
  window.addEventListener('resize', draw);
  draw();
})();
"""


def _state(tf, critical, near_critical, near):
    if critical or (tf is not None and tf <= 0):
        return 'critical'
    if near_critical or (tf is not None and 0 < tf <= near):
        return 'near'
    return 'free'


def wall_html(res, items, plan=None, title='The Wall', leveled=False, near=DEFAULT_NEAR_DAYS):
    """One self-contained HTML wall. See the module docstring."""
    rows = _rows(res)
    by_item = _by_item(items)
    lev = _leveled_map(plan) if leveled else {}
    near = _num(near)
    near = DEFAULT_NEAR_DAYS if near is None else near
    dd = _date(res.get('data_date')) if isinstance(res, dict) else None
    pairs = links(items)
    preds_of, succs_of = {}, {}
    for (p, s) in pairs:
        preds_of.setdefault(s, []).append(p)
        succs_of.setdefault(p, []).append(s)

    cards, no_lev, no_date = [], [], []
    for r in rows:
        if r.get('status') == 'complete' or r.get('type') in ('unit', 'summary'):
            continue
        cid = str(r['id'])
        it = by_item.get(cid) or {}
        tf, crit, nc = _num(r.get('TF')), bool(r.get('critical')), bool(r.get('near_critical'))
        start, finish = r.get('start'), r.get('finish')
        if leveled:
            lv = lev.get(cid)
            if lv and _date(lv.get('lev_start')):
                start, finish = lv.get('lev_start'), lv.get('lev_finish') or finish
                if _num(lv.get('lev_TF')) is not None:
                    tf, crit, nc = _num(lv.get('lev_TF')), False, False
            else:
                no_lev.append(cid)
        sd = _date(start)
        if sd is None:
            no_date.append(cid)
            continue
        state = _state(tf, crit, nc, near)
        cards.append({
            'id': cid, 'title': r.get('title') or '', 'holder': r.get('holder') or '',
            'within': r.get('within') or '', 'stream': _id(_field(it, 'stream')) or '',
            'stage': _id(_field(it, 'stage')) or '', 'state_word': _id(_field(it, 'state')) or '',
            'start': start, 'finish': finish, 'last_day': r.get('last_day'),
            'late_start': r.get('late_start'), 'late_finish': r.get('late_finish'),
            'float': _out(tf), 'free_float': _out(_num(r.get('FF'))), 'state': state,
            'week': _monday(sd), 'preds': sorted(preds_of.get(cid, [])), 'succs': sorted(succs_of.get(cid, [])),
        })
    cards.sort(key=lambda c: (c['week'], c['start'] or '', c['float'] if c['float'] is not None else float('inf'), c['id']))
    on_wall = {c['id'] for c in cards}

    weeks = []
    if cards:
        w, last = cards[0]['week'], max(c['week'] for c in cards)
        while w <= last:
            weeks.append(w)
            w += dt.timedelta(days=7)
    cols = []
    for w in weeks:
        y, n, _ = w.isocalendar()
        notes = []
        for c in (c for c in cards if c['week'] == w):
            f = '—' if c['float'] is None else c['float']
            notes.append(
                f'<div class="note {c["state"]}" tabindex="0" role="button" data-id="{html.escape(c["id"])}" '
                f'data-holder="{html.escape(c["holder"])}" data-unit="{html.escape(c["within"])}" '
                f'data-stream="{html.escape(c["stream"])}" data-state="{c["state"]}">'
                f'<span class="id">{html.escape(c["id"])}</span> <span class="f">f {html.escape(str(f))}</span>'
                f'<div class="t">{html.escape(c["title"])}</div>'
                f'<div class="h">{html.escape(c["holder"] or "—")} · {html.escape(c["start"] or "")}</div></div>')
        cols.append(f'<section class="col" data-week="{y}-W{n:02d}"><h2>{y}-W{n:02d} · from {w.isoformat()}</h2>'
                    f'{"".join(notes)}</section>')

    crit_ids = {c['id'] for c in cards if c['state'] == 'critical'}
    lines, undrawn = [], 0
    for (p, s) in pairs:
        if p in on_wall and s in on_wall:
            cls = ' class="crit"' if p in crit_ids and s in crit_ids else ''
            lines.append(f'<line{cls} data-from="{html.escape(p)}" data-to="{html.escape(s)}" x1="0" y1="0" x2="0" y2="0"></line>')
        else:
            undrawn += 1

    def options(key, label):
        vals = sorted({c[key] for c in cards})
        opts = ''.join(f'<option value="{html.escape(v)}">{html.escape(v or "(none)")}</option>' for v in vals)
        return (f'<label>{label} <select data-key="{"unit" if key == "within" else key}" aria-label="{label}">'
                f'<option value="*">all</option>{opts}</select></label>')

    data = {'cards': {c['id']: {k: c[k] for k in ('title', 'holder', 'stage', 'start', 'finish', 'last_day',
                                                     'late_start', 'late_finish', 'float', 'free_float', 'preds',
                                                     'succs', 'within')} | {'state': c['state_word']}
                      for c in cards}}
    notes_said = []
    if leveled and not lev:
        notes_said.append('no leveled dates were given: every card is at its logic start')
    elif no_lev:
        notes_said.append(f'{len(no_lev)} cards have no leveled start and stand at their logic start')
    if no_date:
        notes_said.append(f'{len(no_date)} open cards have no start and are not on the wall')
    if undrawn:
        notes_said.append(f'{undrawn} links touch a unit, a closed card or a card not on the wall, and are not drawn')
    basis = 'leveled start' if leveled else 'computed start (logic)'
    sub = (f'A column per ISO week by {basis}; a sticky per open card, coloured critical · near · free by float; '
           f'every link between two stickies drawn. Data date {dd.isoformat() if dd else "not given"}. '
           f'Click a sticky to open it in place; ×, Escape or a second click closes it.'
           + (' ' + '; '.join(notes_said) + '.' if notes_said else ''))
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{html.escape(title)}</title><style>{_CSS}</style></head><body>\n'
        f'<header><h1>{html.escape(title)}</h1><p class="sub">{html.escape(sub)}</p>'
        '<div class="filters">'
        f'{options("holder", "Holder")}{options("within", "Unit")}{options("stream", "Stream")}'
        '<label>State <select data-key="state" aria-label="State"><option value="*">all</option>'
        '<option value="critical">critical</option><option value="near">near</option><option value="free">free</option>'
        '</select></label>'
        '<span class="key"><span class="crit">critical</span><span class="near">near</span><span class="free">free</span></span>'
        f'<span class="count" id="count">{len(cards)} of {len(cards)} open cards shown</span></div></header>\n'
        f'<div class="scroller" id="scroller"><div class="wall" id="wall">'
        f'<svg class="links" id="links" aria-hidden="true">{"".join(lines)}</svg>{"".join(cols)}</div></div>\n'
        f'<script type="application/json" id="wall-data">{_js_json(data)}</script>\n'
        f'<script>{_JS}</script>\n</body></html>\n')
