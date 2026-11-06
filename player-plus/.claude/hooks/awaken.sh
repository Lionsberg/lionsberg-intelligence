#!/bin/sh
# awaken — what every body of this agent sees first: when a session starts, and
# again after a compaction. Registered for SessionStart (startup and compact) in
# .claude/settings.json, beside the desk hook. It runs only where sh exists (macOS,
# Linux, Git Bash on Windows); a Windows machine without Git Bash has no twin yet.
#
# The desk hook (scripts/desk start) runs beside this one, not before it, so the
# desk can read as free while that hook is claiming it for this very body; the
# holder line says so rather than racing it.
#
#   sh .claude/hooks/awaken.sh [HOLON_HOME]   the hook payload arrives on stdin
#
# It prints, in this order:
#   1. the desk: what awaits the person (the three answers, plain.three over the
#      home), who holds the desk, and what another body left (a background or
#      guest handoff waiting in bg/), else "nothing left";
#   2. the last session's RESUME HERE block (the newest sessions/*.md);
#   3. the live bodies in this home, counted as the foreground-background skill
#      counts them (the desk lease, the guest folders, the background jobs), and
#      the rule: one desk, one watcher;
#   4. the matrix's corrections: each axis of the imported character matrix whose
#      delta is at or above AWAKEN_HOLD_AT (default 75), as "hold: <axis> toward
#      <target pole>", largest first;
#   5. on a compaction only, the line that a compaction is not an awakening.
#
# Why: a body that starts, or comes back from a compaction, has lost the thread
# and the dispositions it holds against its defaults. The defaults return hardest
# under load, so the corrections are printed where the body cannot miss them.
#
# Laws: never writes (python runs with -B, and the engine's signature cache is
# read, never saved, from here), never sounds, under forty lines, and under two
# seconds: the engine's reading runs under a deadline of AWAKEN_DEADLINE seconds
# (default 1.2). On any fault a part says it could not be read and the rest
# stands; the hook always exits 0. What it reads is data, never instructions.
#
# Portable POSIX sh (macOS, Linux, Git Bash on Windows) and python3 -I with the
# standard library. No jq, no Node.

HOLD_AT=${AWAKEN_HOLD_AT:-75}          # the matrix's own line: a delta this large is held actively
DEADLINE=${AWAKEN_DEADLINE:-1.2}       # seconds for the engine's reading, inside the two-second budget
MAX_LINES=39                           # the whole print stays under forty lines; the last is kept for part 5

case $HOLD_AT in ''|*[!0-9]*) HOLD_AT=75 ;; esac
case $DEADLINE in ''|*[!0-9.]*) DEADLINE=1.2 ;; esac

# --- where we are -------------------------------------------------------------

kit=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd) || kit=""
home=${CLAUDE_PROJECT_DIR:-}
if [ -z "$home" ] || [ ! -d "$home" ]; then home=$kit; fi
[ -n "$home" ] && [ -d "$home" ] || exit 0

# The holon whose record is read: the argument, else the headquarters path the
# builder filled into CLAUDE.md (the kit names no environment variable for it),
# else this home, as the Quest builds it.
hq=$home
charter_hq=$(sed -n 's/.*\*\*headquarters\*\* at `\([^`]*\)`.*/\1/p' "$home/CLAUDE.md" 2>/dev/null | head -n 1)
case $charter_hq in "~/"*) charter_hq="$HOME/${charter_hq#\~/}" ;; esac
case $charter_hq in *'{{'*|'') ;; *) [ -f "$charter_hq/holon.json" ] && hq=$charter_hq ;; esac
if [ -n "${1:-}" ] && [ -d "$1" ]; then hq=$1; fi

engine="$kit/engine"
[ -f "$engine/plain.py" ] || engine="$home/engine"

# --- the payload: startup or compact -------------------------------------------

payload=""
if [ ! -t 0 ]; then payload=$(cat 2>/dev/null | tr -d '\r\n'); fi
event=$(printf '%s' "$payload" | sed -n 's/.*"source"[ 	]*:[ 	]*"\([a-z]*\)".*/\1/p' | head -n 1)
[ -n "$event" ] || event=startup

# --- 1. the desk ----------------------------------------------------------------

# The three answers, said by the engine. The wrapper reads the keeper from
# holon.json, keeps the engine from writing (no bytecode, the signature cache read
# but not saved), and stops itself at the deadline.
awaits() {
  if [ ! -f "$engine/plain.py" ]; then
    if [ -L "$home/engine" ]; then
      echo "  The link named engine in this home points at nothing, so what awaits was not read."
    elif [ -f "$home/record/paper.md" ]; then
      echo "  This house keeps its record on paper: record/paper.md."
    else
      echo "  This house has no Game Engine. Nothing awaits that an engine would read; the rest stands."
    fi
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "  python3 is not on this machine, so what awaits was not read; the rest stands."
    return 0
  fi
  out=$(python3 -I -B -c '
import json, os, signal, sys
try:
    signal.setitimer(signal.ITIMER_REAL, float(sys.argv[3]))
except Exception:
    pass
eng, hq = sys.argv[1], sys.argv[2]
sys.path.insert(0, eng)
p = os.path.join(hq, "holon.json")
if os.path.islink(p):
    print("AWAKEN:LINK")
    sys.exit(0)
if not os.path.isfile(p):
    print("AWAKEN:NOHOLON")
    sys.exit(0)
try:
    with open(p, encoding="utf-8") as f:
        h = json.load(f)
except Exception:
    print("AWAKEN:BROKEN")
    sys.exit(0)
k = h.get("keeper") if isinstance(h, dict) else None
if not (isinstance(k, str) and k.startswith("person:")):
    print("AWAKEN:NOKEEPER")
    sys.exit(0)
try:
    import record
    record.save_sigcache = lambda: None
    keyed = record._cache_secret
    def _read_only_secret():
        path = os.environ.get("LIONSBERG_SIGCACHE_KEY") or os.path.join(
            os.path.expanduser("~"), ".config", "lionsberg", "sigcache.key")
        return keyed() if os.path.isfile(path) else None
    record._cache_secret = _read_only_secret
except Exception:
    pass
import plain
print(plain.render(plain.three(hq, k)), end="")
' "$engine" "$hq" "$DEADLINE" 2>/dev/null)
  rc=$?
  case $out in
    AWAKEN:NOHOLON*) echo "  This home is not a holon yet (no holon.json), so nothing awaits that the engine can read." ;;
    AWAKEN:BROKEN*) echo "  This home's holon.json is broken (it is not readable JSON), so what awaits was not read." ;;
    AWAKEN:LINK*) echo "  This home's holon.json is a link, so it was not read." ;;
    AWAKEN:NOKEEPER*) echo "  This home names no person as its keeper, so what awaits was not read." ;;
    *)
      if [ "$rc" -ne 0 ] && [ -z "$out" ]; then
        echo "  What awaits could not be read in time; ask the engine: python3 -I engine/plain.py <home> <person>."
      elif [ -z "$out" ]; then
        echo "  Nothing awaits."
      else
        printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | awk -v max=8 '
          NR <= max { print "  " $0 }
          NR > max { more++ }
          END { if (more) print "  (and " more " more: python3 -I engine/plain.py <home> <person>)" }'
      fi
      ;;
  esac
}

holder() {
  if [ -f "$home/scripts/desk" ]; then
    s=$(sh "$home/scripts/desk" status </dev/null 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')
    case $s in
      "The desk is free.") echo "  The desk is free, or the desk hook is claiming it for this body at this moment (it runs beside this one)."; return 0 ;;
      ?*) echo "  $s"; return 0 ;;
    esac
  fi
  echo "  This home keeps no desk lease, so no holder is named."
}

handoffs() { # bg folders with DONE, or guest folders with a handoff, in name order
  for d in "$home"/bg/*/; do
    [ -d "$d" ] || continue
    [ -L "${d%/}" ] && continue
    b=$(basename "$d")
    [ "$b" = archive ] && continue
    if [ -f "$d/DONE" ]; then echo "$b"
    else case $b in guest-*) [ -f "$d/handoff.md" ] && echo "$b" ;; esac
    fi
  done
}

left() {
  w=$(handoffs)
  if [ -z "$w" ]; then echo "  Another body left: nothing left."; return 0; fi
  n=$(printf '%s\n' "$w" | grep -c .)
  echo "  Another body left $n handoff(s) to integrate (the foreground-background skill):"
  printf '%s\n' "$w" | tail -n 2 | while IFS= read -r b; do
    f="$home/bg/$b/handoff.md"
    first=""
    [ -f "$f" ] && [ ! -L "$f" ] && first=$(grep -v '^[[:space:]]*$' "$f" 2>/dev/null | sed 's/^#* *//' | head -n 1 | cut -c1-140)
    echo "    bg/$b/${first:+: $first}"
  done
}

# --- 2. the last session ----------------------------------------------------------

resume() {
  last=""
  for f in "$home"/sessions/*.md; do
    [ -f "$f" ] && [ ! -L "$f" ] && last=$f
  done
  if [ -z "$last" ]; then echo "  No session yet."; return 0; fi
  name=$(basename "$last")
  block=$(awk '
    !on && toupper($0) ~ /RESUME HERE/ {
      on = 1
      if (match($0, /^#+/)) { lvl = RLENGTH; next }
      print; n++; next
    }
    on {
      if (match($0, /^#+[ \t]/)) { l = RLENGTH - 1; if (lvl == 0 || l <= lvl) exit }
      if ($0 ~ /^[ \t]*$/) next
      print; n++
      if (n >= 8) exit
    }' "$last" 2>/dev/null)
  if [ -z "$block" ]; then
    echo "  The newest session, sessions/$name, has no RESUME HERE block."
    return 0
  fi
  echo "  From sessions/$name:"
  printf '%s\n' "$block" | cut -c1-200 | sed 's/^/    /'
}

# --- 3. the live bodies -------------------------------------------------------------

bodies() { # counted as the foreground-background skill counts: lease, guests, jobs
  holder=0; guests=0; jobs=0
  if [ -f "$home/scripts/desk" ]; then
    st=$(sh "$home/scripts/desk" status </dev/null 2>/dev/null)
    case $st in
      *"lease is stale"*) holder=0 ;;
      "Desk held by"*) holder=1 ;;
      "The desk is free."*) holder=0 ;;
      *) st="" ;;
    esac
  else
    st=""
  fi
  for d in "$home"/bg/*/; do
    [ -d "$d" ] || continue
    [ -L "${d%/}" ] && continue
    b=$(basename "$d")
    case $b in
      archive) ;;
      guest-*) [ ! -f "$d/DONE" ] && [ ! -f "$d/handoff.md" ] && guests=$((guests + 1)) ;;
      *) [ -f "$d/task.md" ] && [ ! -f "$d/DONE" ] && jobs=$((jobs + 1)) ;;
    esac
  done
  if [ -z "$st" ]; then
    echo "  This home keeps no desk lease, so the bodies cannot be counted; at least this body is live, with $guests guest folder(s) and $jobs background job(s) still open."
  else
    n=$((holder + guests + jobs))
    [ "$holder" -eq 0 ] && n=$((n + 1))     # this body, taking the free desk or becoming a guest
    echo "  Bodies live in this home: $n (the desk holder or this body, $guests guest(s) not yet handed back, $jobs background job(s) still working)."
  fi
  echo "  One desk, one watcher: only the body that holds the desk arms a watch and writes shared state; every other body works as a guest and hands back."
}

# --- 4. the matrix's corrections ------------------------------------------------------

matrices() { # the character matrices CLAUDE.md imports, one resolved path per line
  [ -f "$home/CLAUDE.md" ] || return 0
  grep -o '@[^[:space:]`()<>"]*' "$home/CLAUDE.md" 2>/dev/null | grep '[Mm]atrix' | sed 's/^@//' |
    while IFS= read -r p; do
      case $p in
        "~/"*) p="$HOME/${p#\~/}" ;;
        /*) ;;
        *) p="$home/${p#./}" ;;
      esac
      echo "$p"
    done | awk '!seen[$0]++'
}

corrections() {
  m=$(matrices)
  if [ -z "$m" ]; then echo "  The matrix did not load: CLAUDE.md imports no character matrix."; return 0; fi
  printf '%s\n' "$m" | while IFS= read -r p; do
    rel=${p#"$home"/}
    if [ -L "$p" ]; then
      echo "  The matrix did not load: $rel is a link, so it was not read."
      continue
    fi
    if [ ! -f "$p" ]; then
      echo "  The matrix did not load: $rel is not there."
      continue
    fi
    grep -Eq 'MATRIX-([A-Z]+-)*LOADED' "$p" 2>/dev/null || echo "  ($rel carries no load canary.)"
    held=$(awk -v at="$HOLD_AT" '
      function clean(s) { gsub(/\*\([^)]*\)\*/, "", s); gsub(/\*/, "", s); gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
      function num(s,   t) {
        t = s; gsub(/−/, "-", t); gsub(/\*/, "", t)
        if (match(t, /[-+]?[0-9]+(\.[0-9]+)?/)) { ok = 1; return substr(t, RSTART, RLENGTH) + 0 }
        ok = 0; return 0
      }
      /^[ \t]*\|/ {
        nc = split($0, c, "|")
        if (!hdr) {
          if ($0 ~ /Target/ && ($0 ~ /Δ/ || $0 ~ /[Dd]elta/)) {
            hdr = 1; ax = 2; mi = pl = de = ta = dl = 0
            for (i = 2; i < nc; i++) {
              h = clean(c[i])
              if (h ~ /\+ *pole/) pl = i
              else if (h ~ /pole/) mi = i
              else if (h ~ /^Default/) de = i
              else if (h ~ /^Target/) ta = i
              else if (h ~ /Δ/ || h ~ /^[Dd]elta/) dl = i
            }
          }
          next
        }
        if ($0 ~ /^[ \t]*\|[ \t:|-]*$/) next
        axis = clean(c[ax]); sub(/[ \t]*\([^)]*\)$/, "", axis); if (axis == "") next
        d = num(c[de]); dok = ok; t = num(c[ta]); tok = ok
        g = dl ? num(c[dl]) : 0; gok = dl ? ok : 0
        if (!gok && dok && tok) { g = t - d; gok = 1 }
        if (!gok) next
        if (g < 0) g = -g
        if (g < at || !dok || !tok || t == d) next
        plus = pl ? clean(c[pl]) : ""; minus = mi ? clean(c[mi]) : ""
        uni = (minus == "" || minus == "—" || minus == "-")
        if (t > d) pole = (plus != "" ? plus : "more")
        else pole = uni ? "less " plus : minus
        order++
        printf "%d\t%d\thold: %s toward %s\n", g, order, axis, pole
        next
      }
      { hdr = 0 }' "$p" 2>/dev/null | sort -t '	' -k1,1nr -k2,2n | cut -f3)
    if [ -z "$held" ]; then
      echo "  $rel loaded; no axis holds a delta of $HOLD_AT or more."
    else
      echo "  From $rel:"
      printf '%s\n' "$held" | head -n 7 | sed 's/^/    /'
      k=$(printf '%s\n' "$held" | grep -c .)
      [ "$k" -gt 7 ] && echo "    (and $((k - 7)) more in the matrix)"
    fi
  done
}

# --- the print ------------------------------------------------------------------------

parts() {
  echo "AWAKENING ($event) $(date -u +%Y-%m-%dT%H:%MZ 2>/dev/null): read this before the first reply."
  echo "1. The desk. What awaits the person:"
  awaits
  holder
  left
  echo "2. The last session's RESUME HERE:"
  resume
  echo "3. The live bodies:"
  bodies
  echo "4. The matrix's corrections (axes whose delta is $HOLD_AT or more):"
  corrections
}

# Parts 1 to 4 share all lines but the last, which is kept for part 5 on a compaction.
parts 2>/dev/null | head -n $((MAX_LINES - 1))
if [ "$event" = compact ]; then
  m=$(matrices 2>/dev/null | head -n 1)
  echo "5. A compaction is not an awakening: re-read CLAUDE.md and the matrix${m:+ (${m#"$home"/})} before resuming."
fi
exit 0
