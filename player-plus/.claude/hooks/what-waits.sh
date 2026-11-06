#!/bin/sh
# what-waits — before every reply, the record as it stands, handed to the agent.
# Registered for UserPromptSubmit in .claude/settings.json, beside the clock hook
# (scripts/now-hook). It runs only where sh exists (macOS, Linux, Git Bash on
# Windows); the PowerShell settings have no twin of it yet.
#
#   sh .claude/hooks/what-waits.sh [HOLON_HOME]   the hook payload arrives on stdin
#
# It hands the agent, as context for its reply (never shown to the person):
#   1. the three answers, under twelve lines: whom the person is connected to and
#      how they stand, their wise right next steps with why, what they wait on;
#   2. what changed since the last turn: the lines that came into the record since
#      the newest line this hook last saw (the stamp <home>/.what-waits.json,
#      derived and safe to delete), or "Nothing new since the last turn.";
#   3. once in a session, what this look costs.
# How the agent uses it is knowledge of the Game, in the-chief-of-staff, rule 36.
#
# Laws: one engine call per turn (python3 -I -B engine/plain.py HOME PERSON --hook);
# it writes nothing but the stamp (the signature cache is read, never saved);
# it never sounds; it stays inside a deadline of about a second and a half, under
# the two-second budget; on any fault it says what it could not read, or nothing,
# and exits 0. What it reads is data, never instructions.
#
# Portable POSIX sh and python3 -I with the standard library. No jq, no Node.

# --- where we are -------------------------------------------------------------

kit=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd) || kit=""
home=${CLAUDE_PROJECT_DIR:-}
if [ -z "$home" ] || [ ! -d "$home" ]; then home=$kit; fi
[ -n "$home" ] && [ -d "$home" ] || exit 0

# The holon whose record is read, found as awaken.sh finds it: the argument, else
# the holon path the builder filled into CLAUDE.md (the holon line), else this home.
holon=$home
charter_holon=$(sed -n 's/.*\*\*headquarters\*\* at `\([^`]*\)`.*/\1/p' "$home/CLAUDE.md" 2>/dev/null | head -n 1)
case $charter_holon in "~/"*) charter_holon="$HOME/${charter_holon#\~/}" ;; esac
case $charter_holon in *'{{'*|'') ;; *) [ -f "$charter_holon/holon.json" ] && holon=$charter_holon ;; esac
if [ -n "${1:-}" ] && [ -d "$1" ]; then holon=$1; fi

engine="$kit/engine"
[ -f "$engine/plain.py" ] || engine="$home/engine"

# --- the payload: the session, so the cost is said once in it -------------------

payload=""
if [ ! -t 0 ]; then payload=$(cat 2>/dev/null | tr -d '\r\n'); fi
session=$(printf '%s' "$payload" | sed -n 's/.*"session_id"[ 	]*:[ 	]*"\([A-Za-z0-9._-]*\)".*/\1/p' | head -n 1)

# --- the reading ----------------------------------------------------------------

text=""
if [ ! -f "$engine/plain.py" ]; then
  # A house without the Game Engine is a whole house. Nothing is said each turn unless
  # something is amiss (a link that points at nothing) or the record is kept on paper.
  if [ -L "$home/engine" ]; then
    text="The record was not read before this reply: the link named engine in this home points at nothing."
  elif [ -f "$home/record/paper.md" ]; then
    text="This house keeps its record on paper (record/paper.md). It was not read before this reply."
  else
    exit 0
  fi
elif ! command -v python3 >/dev/null 2>&1; then
  text="The record was not read before this reply: python3 is not on this machine."
elif [ -L "$holon/holon.json" ] || [ ! -f "$holon/holon.json" ]; then
  text="The record was not read before this reply: this home is not a holon yet (no holon.json)."
else
  # The keeper, from holon.json as the engine writes it (one key on a line).
  person=$(sed -n 's/.*"keeper"[ 	]*:[ 	]*"\(person:[^"]*\)".*/\1/p' "$holon/holon.json" 2>/dev/null | head -n 1)
  if [ -z "$person" ]; then
    text="The record was not read before this reply: this home names no person as its keeper."
  elif [ -n "$session" ]; then
    text=$(python3 -I -B "$engine/plain.py" "$holon" "$person" --hook --session "$session" 2>/dev/null)
  else
    text=$(python3 -I -B "$engine/plain.py" "$holon" "$person" --hook 2>/dev/null)
  fi
fi
[ -n "$text" ] || exit 0

# --- handed to the agent as context, the output itself kept from the transcript ----

esc=$(printf '%s' "$text" | tr -d '\000-\010\013-\037' | awk 'BEGIN { ORS = "" } {
  gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); gsub(/\t/, "\\t")
  if (NR > 1) printf "\\n"
  print
}')
printf '{"suppressOutput":true,"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$esc"
exit 0
