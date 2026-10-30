#!/usr/bin/env python3
"""fake_agent.py: a stand-in agent that speaks just enough of the Agent Client Protocol to prove
the dock's shapes. It proves the shapes, never the experience; the review is made with a real
agent (DESIGN-DOCK §9).

Over stdin and stdout, one JSON-RPC 2.0 object per line:
  initialize            declares text only; a new session declares the harness's five modes as its adapter does
  session/new           a new conversation id; the character it was given (_meta.systemPrompt) is
                        kept, and a turn that asks "who are you" answers with its first words
  session/load          replays a past conversation as session updates first, as a real agent
                        does, then answers (the dock must not show the replay as new words)
  session/prompt        a question is answered first, in one or two sentences, in its own words,
                        then at most one offer; "put this in my record: …" asks first, then on a Yes the card
                        reaches the margin (the night test, 2026-10-24: "It said good morning,
                        ignored my question, offered me a gate"); a greeting greets by the hour with
                        no tool, no ask and no offer; a turn that speaks of the costs asks one
                        permission (to send something to Cell Two, which leaves the computer), then
                        answers and offers a card; every other turn answers in words
  session/set_mode      takes a declared mode
  session/cancel        ends the running turn
The host may send a note of what the page shows before the person's words (a block of its own, "What
the page shows now: ..."); the stand-in routes on the person's words only. When the note says the page
already answered a first-contact line (who are you, what is this, who sent me, how do I stop, can I talk
to a person, where do my words go), it adds one short line of its own and repeats nothing; when the note
says the page marked an answer, it says "Marked." (which the host drops); "what were you given" says back its character;
"what does the page show" says back the note it was given.
A turn that says "mark" and "Saturday" proposes the act in the chief of staff's form ("Shall I mark:
Saturday morning, for the meeting day? Yes?"). A turn that says "two changes" asks two permissions at
once (the host must show them one at a time). It never asks permission for a read.
Round two (2026-10-25): the house's note ("What your house holds now ...") may come before the page's; "what
were you told" says it back. "go slowly" keeps a note in memory/ (memory/go-slowly.md, its description a clause
to her, then the index memory/MEMORY.md): the host asks it once, plainly, and answers the index by her same
answer. "blocked" tries a command (the host answers it no, unseen) and answers from the note's first card;
"anything late" answers from the note's past by-whens. On the page's "it has just marked" it says a bare
"Marked." and "stray" heads an answer with one: the host drops the first and cuts the second.
A turn that says "have a worker ..." proposes the worker in the chief of staff's form (the cost, then
"The task, in your words: ...", then "Start it?"), and starts nothing. A turn that says "long" answers in three paragraphs and a list after two seconds of thought; one
that says "notes" is tool-heavy (it says a line to itself, reads, searches, runs and edits, about
twelve seconds, then answers); one that says "slow" thinks twelve seconds before its first word.
Round three: "out loud", "what is Chain for", "decide what you can" (two "Decided:" lines, one the house
cannot mark), "glued" (two messages with nothing between), "yes, send it today" (a mark the page already
settled), "change the page" (a change to a page in its own house), and the host's note that a worker started.
The trust layer (DESIGN-TALK.md): it reports a plausible figures block as the Claude adapter does,
and says it is the stand-in (initialize's _meta.lionsberg.stand_in, and an agentInfo of its own): configOptions
for its model and effort; a usage_update (the window's tokens, the sitting's running cost) and the plan's
windows (usage_update _meta "_claude/rateLimit") at each turn's end; and each prompt response's usage and
_meta.quota. Its tool calls carry the harness's tool name (_meta.claudeCode.toolName). "ponder" streams a
thinking summary before its words; "fold the talk" compacts (the harness's "Compact conversation" step);
"near the edge" fills the window past four fifths; "spent" reports a spent window as the harness's typed
failure; "look it up" fetches a page (a tool that leaves the computer).
The chain's watch (2026-10-25): a worker whose task says "take your time" works until stopped; the house's
note that a worker "is past its box" is answered in one of the three forms, by the worker's task ("split" splits,
"another" starts another, else it lets it run sixty minutes more); "the half-hour look" says "Nothing moved." unless
a worker is waiting on something; a refused dependency ("raised no Start card") is proposed again with the result's
shape written first. A proposal says its box ("About 20 minutes", or the person's "{n}-minute").
The box on the chain: the house's note that a box is too long is answered in one
of its forms, by the task, in the house's own numbers (its minutes for one action, its handback): a "study" on
the chain goes "Off the chain: hands back every <n> minutes."; a "map" is three stages, two side by side and one
after both, the first with a check that passes; a "wall" is two stages, the first with a check that fails;
anything else is cut into "Stages: the first half of <task>, about <n> minutes; the second half of <task>, about
<n> minutes." A worker given a stage of a chain writes what it was given to its status.md, then its handoff
(first line "Stage done: <stage>.") and DONE; the house's note that a stage did not pass its check is answered
in one line.
A line that is only a greeting, which the house has greeted for it, gets no words (the first turn answers
the person's line and nothing else). Every reply is streamed in small pieces. Standard library only; no network; no sound.
"""
import json
import re
import sys
import threading
import time

lock = threading.Lock()
pending = {}
next_id = [1000]
turns = {"n": 0}
cancelled = {"flag": False}
GATE_CARD = None
LONG = ("Here is how the week looks from where I sit.\n\n"
        "Two things lean on you. The costs for the hall are owed to Cell Two by Thursday, and the bread for "
        "Saturday is yours. Neither is hard; both are easier before Wednesday.\n\n"
        "What I would do, in order:\n"
        "- Send the costs on Tuesday morning, when you like to make calls.\n"
        "- Ask the keeper on Wednesday whether two loaves or three.\n"
        "- Leave Friday clear.\n\n"
        "Everything else I can keep. If something changes, I will bring it to you as a card, *not* as a list.")
CHARACTER = {"text": ""}
SITTING = {"used": 18000, "cost": 0.0}
SIZE = 200000
MODELS = [{"value": "default", "name": "Default (recommended)"}, {"value": "stand-in-small", "name": "Stand-in Small"}]
EFFORTS = [{"value": v, "name": v} for v in ("low", "medium", "high", "xhigh", "max")]


def config_options(mode="default"):
    return [{"id": "model", "name": "Model", "type": "select", "currentValue": "default", "options": MODELS},
            {"id": "effort", "name": "Effort", "type": "select", "currentValue": "high", "options": EFFORTS}]


def account(sid, tin, tout, cost):
    """The sitting's figures at a turn's end, as the adapter sends them before the prompt's response."""
    SITTING["used"] += tin + tout
    SITTING["cost"] = round(SITTING["cost"] + cost, 6)
    update(sid, {"sessionUpdate": "usage_update", "used": SITTING["used"], "size": SIZE,
                 "cost": {"amount": SITTING["cost"], "currency": "USD"}})
    now = int(time.time())
    update(sid, {"sessionUpdate": "usage_update", "used": SITTING["used"], "size": SIZE,
                 "_meta": {"_claude/rateLimit": {"status": "allowed", "rateLimitType": "seven_day", "utilization": 0.48,
                                                 "resetsAt": now + 2 * 86400,
                                                 "unifiedWindows": {"five_hour": {"utilization": 0.12, "resetsAt": now + 3 * 3600},
                                                                    "seven_day": {"utilization": 0.48, "resetsAt": now + 2 * 86400}}}}})
    usage = {"inputTokens": 40, "outputTokens": tout, "cachedReadTokens": tin - 40 - 200, "cachedWriteTokens": 200,
             "totalTokens": tin + tout}
    return {"usage": usage, "_meta": {"quota": {"token_count": dict(usage, cachedInputTokens=usage["cachedReadTokens"],
                                                                   reasoningOutputTokens=0),
                                                "model_usage": [{"model": "stand-in-model-1", "token_count": {"totalTokens": tin + tout}}]}}}
HOUSE = {"last": ""}
RESULTS = {}


def send(obj):
    with lock:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()


def ask(method, params):
    next_id[0] += 1
    rid = next_id[0]
    ev = threading.Event()
    pending[rid] = [ev, None]
    send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
    ev.wait(3600)
    return pending.pop(rid)[1]


def update(sid, u):
    send({"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": sid, "update": u}})


def speak(sid, text, pace=0.04):
    for i, word in enumerate(text.split(" ")):
        if cancelled["flag"]:
            return
        update(sid, {"sessionUpdate": "agent_message_chunk",
                     "content": {"type": "text", "text": ("" if i == 0 else " ") + word}})
        time.sleep(pace)


FIRST = re.compile(r"who are you|what are you|what is this|who sent|how do i stop|real person|talk to a person|"
                   r"where do my words go|where does it go", re.I)


def permit(sid, tid, title, kind, raw):
    return ask("session/request_permission", {
        "sessionId": sid, "toolCall": {"toolCallId": tid, "title": title, "kind": kind, "rawInput": raw},
        "options": [{"optionId": "once", "name": "Allow once", "kind": "allow_once"},
                    {"optionId": "no", "name": "Reject", "kind": "reject_once"}]})


def turn(rid, sid, prompt):
    cancelled["flag"] = False
    turns["n"] += 1
    n = turns["n"]
    texts = [p.get("text", "") for p in (prompt or []) if isinstance(p, dict)]
    whole = texts[0] if len(texts) > 1 else ""          # the house's note and the page's, before her words
    note = whole[whole.index("What the page shows now"):] if "What the page shows now" in whole else ""
    house = whole.split("What the page shows now")[0].strip()
    HOUSE["last"] = house
    person = texts[-1] if texts else ""
    said = person.lower()
    if "take your time" in said and "bg/" in CHARACTER.get("text", ""):
        # a worker that runs long (the chain's watch): it works until stopped, quietly
        for _ in range(600):
            if cancelled["flag"]:
                break
            time.sleep(0.1)
        speak(sid, "Still at it.")
    elif "It has greeted them for you" in note:
        # the house greeted; a line that asked nothing gets no words. A real agent still takes a moment to
        # end such a turn: ending in the same instant raced turn_end ahead of the page's own say reply
        time.sleep(0.8)
    elif "is past its box" in said:
        # the chain's watch: one of the three answers, chosen by the worker's task
        name = person.split(" ", 1)[0]
        m = re.search(r'its task: "([^"]*)"', said)
        task = m.group(1) if m else ""
        if "split" in task:
            speak(sid, "Split: only the first chapter for " + name + ". The rest can wait for the next box.", pace=0.004)
        elif "another" in task:
            speak(sid, "Start another: count the moons, about 5 minutes. It runs beside " + name + ".", pace=0.004)
        else:
            speak(sid, "Let it run: about 60 minutes more. " + name + " is close and nothing waits on it.", pace=0.004)
    elif "in a chain the house runs" in said and "bg/" in CHARACTER.get("text", ""):
        # a stage of a chain: what it was given goes to its status.md, then its handoff and DONE
        import os
        folder = re.search(r"inside bg/([\w-]+)/", CHARACTER["text"]).group(1)
        home = os.path.join(CHARACTER.get("cwd") or ".", "bg", folder)
        os.makedirs(home, exist_ok=True)
        stage = person.split("\n", 1)[0].strip()
        open(os.path.join(home, "status.md"), "w").write(person + "\n")
        time.sleep(1.0)
        open(os.path.join(home, "handoff.md"), "w").write("Stage done: " + stage + ".\nreview_min: 1\n")
        open(os.path.join(home, "DONE"), "w").write("")
        speak(sid, "Stage done: " + stage + ".", pace=0.004)
    elif "did not pass its check" in said:
        speak(sid, "The first stage stopped at its check. One thing would mend it: shall I look at the failing line?", pace=0.004)
    elif "that is a long box" in said or "that is a box of over" in said:
        # the box on the chain, in the house's own numbers: off the chain for a study the work waits on, else stages
        m = re.search(r'The task: "([^"]*)"', person)
        task = m.group(1) if m else "the task"
        one = re.search(r"(?:gives one action about|stages of about) (\d+) minutes", person)
        one = one.group(1) if one else "5"
        every = re.search(r"hand back something every (\d+) minutes", person)
        if "study" in task and "that is a long box" in said:
            speak(sid, "Off the chain: hands back every " + (every.group(1) if every else "5") + " minutes. Nothing "
                       "needs the whole of it at once.", pace=0.004)
        elif "map" in task:
            speak(sid, "Stages: draw the hills, about 4 minutes, check `python3 -I check.py pass`; draw the rivers, "
                       "about 4 minutes, beside draw the hills; join the map, about 5 minutes, after draw the hills and "
                       "draw the rivers.", pace=0.004)
        elif "wall" in task:
            speak(sid, "Stages: lay the stones, about 4 minutes, check `python3 -I check.py fail`; raise the wall, "
                       "about 4 minutes.", pace=0.004)
        else:
            speak(sid, "Stages: the first half of " + task + ", about " + one + " minutes; the second half of " + task +
                  ", about " + one + " minutes.", pace=0.004)
    elif "the half-hour look" in said:
        # the half-hour look: something moved only when a worker waits on something
        if re.search(r", waiting on (?!what)", said):
            speak(sid, "Moved: the worker waiting on the guest list now builds against its shape.", pace=0.004)
        else:
            speak(sid, "Nothing moved.", pace=0.004)
    elif "the result's shape" in said and "raised no start card" in said:
        # a refused dependency: the same proposal again, the result's shape written first
        m = re.search(r'the task was: "([^"]+)"', person)
        task = m.group(1) if m else "the task"
        speak(sid, "The task, in your words: " + task + ". The result's shape: a list of names, one per line. "
                   "About 5 minutes; it writes only in its own folder. Start it?", pace=0.004)
    elif "what were you told" in said:
        speak(sid, house or "The house sent no note.", pace=0.004)
    elif "ponder" in said:
        for piece in ("Weighing", " what she asked", " against the week."):
            update(sid, {"sessionUpdate": "agent_thought_chunk", "content": {"type": "text", "text": piece}})
            time.sleep(0.3)
        speak(sid, "I thought it through. The week can hold it.")
    elif "fold the talk" in said:
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-compact", "title": "Compact conversation", "kind": "think",
                     "status": "in_progress", "_meta": {"contextCompaction": {"version": 1}, "claudeCode": {"toolName": "compact"}}})
        time.sleep(0.3)
        update(sid, {"sessionUpdate": "tool_call_update", "toolCallId": "t-compact", "status": "completed",
                     "_meta": {"contextCompaction": {"version": 1, "trigger": "manual", "preTokens": SITTING["used"],
                                                     "postTokens": 9000}, "claudeCode": {"toolName": "compact"}}})
        SITTING["used"] = 9000
        update(sid, {"sessionUpdate": "usage_update", "used": SITTING["used"], "size": SIZE})
        speak(sid, "Folded.")
    elif "near the edge" in said:
        SITTING["used"] = 170000
        update(sid, {"sessionUpdate": "usage_update", "used": SITTING["used"], "size": SIZE})
        speak(sid, "That was a great deal to hold.")
    elif "spent" in said:
        update(sid, {"sessionUpdate": "session_info_update", "_meta": {"jetbrains": {"air": {"version": 1, "sessionFailure": {
            "id": "s-limit-1", "revision": 1, "kind": "quota_exhausted", "category": "limit", "severity": "error",
            "title": "The Claude account has no available quota.", "actions": []}}}}})
    elif "look it up" in said:
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-web", "title": "Fetch https://example.org/hall",
                     "kind": "fetch", "status": "in_progress", "_meta": {"claudeCode": {"toolName": "WebFetch"}}})
        time.sleep(0.2)
        update(sid, {"sessionUpdate": "tool_call_update", "toolCallId": "t-web", "status": "completed",
                     "_meta": {"claudeCode": {"toolName": "WebFetch"}}})
        speak(sid, "The hall's page says it seats eighty.")
    elif "read the brief" in said and "bg/" in CHARACTER.get("text", ""):
        # a worker's reads (its brief, outside the house; a house file; a search) asked nothing;
        # one write outside its folder is the one plain ask
        ok = lambda r: (((r or {}).get("result") or {}).get("outcome") or {}).get("optionId") == "once"
        brief = re.search(r"read (/\S+?): it says", CHARACTER["text"])
        got = {}
        if brief:
            got["brief"] = ok(permit(sid, "b1", "Read " + brief.group(1), "read", {"file_path": brief.group(1)}))
        got["read"] = ok(permit(sid, "b2", "Read state.json", "read", {"file_path": "state.json"}))
        got["grep"] = ok(permit(sid, "b3", "grep -rn bread .", "search", {"pattern": "bread", "path": "."}))
        got["write"] = ok(permit(sid, "b4", "Write notes/bread.md", "edit", {"file_path": "notes/bread.md", "content": "x"}))
        speak(sid, "Read. " + " ".join(k + "=" + ("yes" if v else "no") for k, v in got.items()), pace=0.004)
    elif "draft the notes" in said and "bg/" in CHARACTER.get("text", ""):
        # a worker's draft, as a real worker goes: reads, a search, its own
        # status, handoff and DONE (all answered by the house), one page outside its folder (the one ask),
        # a second outside (refused, never asked), and a send (refused: a worker never acts outward)
        folder = re.search(r"inside bg/([\w-]+)/", CHARACTER["text"]).group(1)
        cwd = CHARACTER.get("cwd") or "."
        ok = lambda r: (((r or {}).get("result") or {}).get("outcome") or {}).get("optionId") == "once"
        got = {}
        got["read"] = ok(permit(sid, "w1", "Read state.json", "read", {"file_path": "state.json"}))
        got["grep"] = ok(permit(sid, "w2", "grep -rn harvest .", "execute", {"command": "grep -rn harvest ."}))
        for i, (f, body) in enumerate((("status.md", "drafting\n"),
                                       ("handoff.md", "Drafted the harvest notes.\nWas it a crop from the ground, or the season's work?\nreview_min: 4\n"),
                                       ("DONE", ""))):
            rel = "bg/" + folder + "/" + f
            got[f] = ok(permit(sid, "w-own-" + str(i), "Write " + rel, "edit", {"file_path": rel, "content": body}))
            if got[f]:
                import os
                os.makedirs(os.path.join(cwd, "bg", folder), exist_ok=True)
                open(os.path.join(cwd, rel), "w").write(body)
        got["out1"] = ok(permit(sid, "w3", "Write notes/harvest.md", "edit",
                                {"file_path": "notes/harvest.md", "content": "# The harvest notes\nA first draft.\n"}))
        got["out2"] = ok(permit(sid, "w4", "Write notes/harvest-2.md", "edit", {"file_path": "notes/harvest-2.md", "content": "x"}))
        got["send"] = ok(permit(sid, "w5", "curl -X POST https://example.org", "execute", {"command": "curl -X POST https://example.org"}))
        RESULTS["worker"] = got
        speak(sid, "Drafted. " + " ".join(k + "=" + ("yes" if v else "no") for k, v in got.items()))
    elif "out loud" in said:
        # it answers from what the house says the page can do, never "I do not know"
        speak(sid, "Yes. Hold the microphone beside Send and speak; let go to send. Turn on Voice mode at the top "
                   "to go hands-free." if "microphone beside Send" in house else "I do not know whether this page can hear you.")
    elif "what is chain for" in said:
        m = re.search(r"the Chain, ([^;]+);", house)
        speak(sid, ("The Chain shows " + m.group(1) + ".") if m else "I do not know what the page means.")
    elif "decide what you can" in said:
        # decides the routine (the suggested choice of the second card), and one it may not
        m = re.search(r'^2\. "([^"]+)"[^\n]*?suggested: ([^;]+);', house, re.M)
        speak(sid, "The harvest count is yours to send; I suggest today.")
        if m:
            speak(sid, "\nDecided: " + m.group(2) + ", for " + m.group(1).rstrip("?") + ".")
        speak(sid, "\nDecided: Ask the moon, for the meeting day.")
    elif "glued" in said:
        # two messages streamed with nothing between, once across a step and once not
        speak(sid, "It works.")
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-g", "title": "Read notes", "kind": "read", "status": "completed"})
        speak(sid, "Which day shall it be?")
        speak(sid, "Fine.")
        speak(sid, "Whenever you are ready. U.S.A stays as it is, and so does e.g.")
    elif "yes, send it today" in said:
        # the page settled her words already: the host raises no second card for this
        speak(sid, "Good; the steward will have it. Shall I mark: Yes, send it today, for Cell Two asked for the harvest "
                   "count by Saturday. Send it now? Yes?")
    elif "has finished" in said:
        m = re.search(r'Its open question: "([^"]+)"', person)
        speak(sid, "The harvest notes are drafted." + (" One thing would finish them: " + m.group(1)[:1].lower() + m.group(1)[1:] if m else ""))
    elif "has started on" in said:
        m = re.search(r"the worker (\w+) has started", person)
        speak(sid, (m.group(1) + " has started on it.") if m else "It has started.")
    elif "change the page" in said:
        # a change to a page in its own house: the host asks it in words, never the file's name
        r = permit(sid, "t-pg", "Write notes/t-one.md", "edit",
                   {"file_path": "notes/t-one.md", "content": "# Map of the commons\nThe commons, drawn from the record.\n"})
        RESULTS["page"] = r
        speak(sid, "Done.")
    elif note and "it has just marked" in note:
        # the real agent's habit the host must drop: a bare "Marked." after the page has said it
        speak(sid, "Marked.")
    elif "stray" in said:
        # a stray "Marked." at the head of an unrelated answer: the host cuts it
        speak(sid, "Marked. Your words stay with you here.")
    elif "go slowly" in said:
        # a note about her, kept in memory/ (the kit's steps): the host asks it plainly, and the index's
        # change in the same turn is answered by her same answer, never asked twice
        speak(sid, "Yes. We go at your pace.")
        # as the real harness does: the change is announced before its file is named ("Preparing file…")
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-mem", "title": "Preparing file…", "kind": "edit",
                     "status": "pending"})
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-idx", "title": "Edit", "kind": "edit", "status": "pending"})
        r = permit(sid, "t-mem", "Write memory/go-slowly.md", "edit",
                   {"file_path": "memory/go-slowly.md",
                    "content": "---\nname: go-slowly\ndescription: we go slowly\ntype: feedback\n---\nShe asked to go slowly.\n"})
        kept = (((r or {}).get("result") or {}).get("outcome") or {}).get("optionId") == "once"
        if kept:
            update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-mem", "title": "Write memory/go-slowly.md",
                         "kind": "edit", "status": "completed",
                         "content": [{"type": "diff", "path": "memory/go-slowly.md", "oldText": "", "newText": "we go slowly"}]})
        r2 = permit(sid, "t-idx", "Edit memory/MEMORY.md", "edit",
                    {"file_path": "memory/MEMORY.md", "old_string": "", "new_string": "- [Go slowly](go-slowly.md)"})
        RESULTS["index"] = (((r2 or {}).get("result") or {}).get("outcome") or {}).get("optionId")
        idx = RESULTS["index"]
        moved = "moved on" in json.dumps(r or {})
        if not moved:
            speak(sid, " I will keep to it." if kept and idx == "once" else
                  " Then slowly it is." if not kept and idx == "no" else " (the index was asked apart)")
    elif "blocked" in said:
        # the office forbids a command; the host answers it no and tells why; the answer comes from the note
        r = permit(sid, "t-sh", "find bg -name status.md", "execute", {"command": "find bg -name status.md"})
        RESULTS["shell"] = r
        first = re.search(r'^1\. \(the first[^)]*\) "([^"]+)"[^\n]*?(by [^.;]+)?\.$', house, re.M)
        speak(sid, ("Nothing is blocked. First: " + first.group(1) + (" (" + first.group(2) + ")" if first.group(2) else ""))
              if first else "The house sent me nothing to rank.")
    elif "anything late" in said:
        late = [ln for ln in house.splitlines() if " past" in ln]
        speak(sid, ("Yes. " + " ".join(late)) if late else "Nothing is late.")
    elif "what does the page show" in said:
        speak(sid, note or "The page sent no note.")
    elif "what were you given" in said:
        speak(sid, CHARACTER["text"] or "I was given no character.")
    elif note and "already answered" in note and FIRST.search(said):
        # the page answered first, in this voice: one line of its own, nothing repeated, no tool
        speak(sid, "I am glad you came. Take your time; nothing here is in a hurry.")
    elif "who are you" in said:
        speak(sid, CHARACTER["text"] or "I was given no character.")
    elif re.search(r"\bmark\b", said) and "saturday" in said:
        # an act on a card at the person's word, only proposed, in the chief of staff's form
        speak(sid, "Shall I mark: Saturday morning, for the meeting day? Yes?")
    elif "two changes" in said:
        # two asks at once: the host must put only one in front of the person
        out = {}
        def one(tid, title):
            out[tid] = permit(sid, tid, title, "edit", {"file_path": "/Users/player/notes/" + tid + ".md"})
        ts = [threading.Thread(target=one, args=(t, x)) for t, x in (("t-one", "Change the first note"),
                                                                      ("t-two", "Change the second note"))]
        for t in ts:
            t.start()
        for t in ts:
            t.join(3600)
        speak(sid, "Both are settled.")
    elif re.search(r"\b(have|ask|get|let) (a|another|one) (new )?worker\b", said):
        # a worker is only proposed, in the chief of staff's form; the host makes the proposal an ask
        raw = person
        m = re.search(r"worker\s+(?:to\s+)?(.+)", raw, re.I)
        task = (m.group(1) if m else "the task").strip().rstrip(".!")
        box = re.search(r"\b(\d{1,3})-minute\b", raw)
        speak(sid, "At this week's pace you have about half your allowance left, and a worker adds to it for an hour "
                   "or two. The task, in your words: " + task + ". About " + (box.group(1) if box else "20") +
                   " minutes; it writes only in its own folder. Start it?")
    elif "slow" in said:
        # a long think: nothing for twelve seconds, so the dock must show presence and then say so in words
        time.sleep(12)
        speak(sid, "I took my time with that. The short answer is yes, and I will keep it in mind.")
    elif "long" in said:
        time.sleep(2.0)
        speak(sid, LONG, pace=0.02)
    elif "notes" in said:
        # a tool-heavy turn: its chatter must never reach the conversation
        speak(sid, "Running the record command now.")
        steps = [("t-r1", "Read /Users/player/notes/hall-costs.md", "read", None),
                 ("t-r2", "Read /Users/player/notes/bread-rota.md", "read", None),
                 ("t-s1", "grep -rn \"Saturday\" /Users/player/notes", "search", None),
                 ("t-x1", "python3 -I /Users/player/lionsberg/engine/record.py append /Users/player/home --actor agent:player-agent "
                          "--type learn --body '{\"text\": \"The hall costs about two hundred.\"}'", "execute", None),
                 ("t-e1", "Edit /Users/player/notes/hall-costs.md", "edit",
                  {"type": "diff", "path": "/Users/player/notes/hall-costs.md", "oldText": "Hall: ?", "newText": "Hall: about two hundred"})]
        for tid, title, kind, diff in steps:
            if cancelled["flag"]:
                break
            time.sleep(1.8)
            u = {"sessionUpdate": "tool_call", "toolCallId": tid, "title": title, "kind": kind, "status": "in_progress",
                 "_meta": {"claudeCode": {"toolName": {"read": "Read", "search": "Grep", "execute": "Bash", "edit": "Edit"}[kind]}}}
            if diff:
                u["content"] = [diff]
            update(sid, u)
            time.sleep(0.4)
            update(sid, {"sessionUpdate": "tool_call_update", "toolCallId": tid, "status": "completed",
                         "content": [{"type": "content", "content": {"type": "text", "text": "(the tool's raw output, never for the conversation)"}}]})
            speak(sid, "Now checking the next file.") if tid == "t-r1" else None
        time.sleep(0.6)
        speak(sid, "Your notes say the hall costs about two hundred, and the bread is yours on Saturday. "
                   "I wrote the cost beside the hall in your notes, so it is there when Cell Two asks.")
    elif "in my record" in said and ":" in said:
        # a card request, as the real agent meets it: the act is asked first (the ask card), and the
        # card reaches the record only on the person's Yes (the margin line)
        raw = person
        title = raw.split(":", 1)[1].split("\n")[0].strip().rstrip(".") or "A card"
        r = ask("session/request_permission", {
            "sessionId": sid,
            "toolCall": {"toolCallId": "t-card", "title": "python3 -I engine/record.py append <home> --type card", "kind": "execute",
                         "rawInput": {"command": "python3 -I engine/record.py append <home> --actor agent:player-agent "
                                                 "--type card --reason delegated --body '" + json.dumps({"title": title}) + "'",
                                      "description": "Add the card to your record"}},
            "options": [{"optionId": "once", "name": "Allow once", "kind": "allow_once"},
                        {"optionId": "always", "name": "Always allow", "kind": "allow_always"},
                        {"optionId": "no", "name": "Reject", "kind": "reject_once"}]})
        outcome = ((r or {}).get("result") or {}).get("outcome") or {}
        if outcome.get("optionId") in ("once", "always"):
            update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t-card", "title": "Add the card to your record",
                         "kind": "execute", "status": "completed"})
            send({"jsonrpc": "2.0", "method": "_lionsberg/offer",
                  "params": {"sessionId": sid, "kind": "card", "text": title}})
            speak(sid, "It is in your record: " + title + ".")
        else:
            speak(sid, "I did not write it. It waits until you want it.")
    elif "costs" in said and "the player" not in said:
        speak(sid, "Before I send anything to Cell Two, I will show you the words.")
        update(sid, {"sessionUpdate": "tool_call", "toolCallId": "t1", "title": "Reading your notes on the costs",
                     "kind": "read", "status": "completed"})
        r = ask("session/request_permission", {
            "sessionId": sid,
            "toolCall": {"toolCallId": "t2", "title": "Send the costs to Cell Two", "kind": "fetch",
                         "rawInput": {"to": "Cell Two", "message": "The costs for the hall: about two hundred."},
                         "_meta": {"lionsberg": {"why": "You asked me on Tuesday to bring the costs by Thursday."}}},
            "options": [{"optionId": "once", "name": "Allow once", "kind": "allow_once"},
                        {"optionId": "always", "name": "Always allow", "kind": "allow_always"},
                        {"optionId": "no", "name": "Reject", "kind": "reject_once"}]})
        outcome = ((r or {}).get("result") or {}).get("outcome") or {}
        if outcome.get("optionId") in ("once", "always"):
            speak(sid, "Sent. Cell Two has the costs, and I wrote nothing else.")
        else:
            speak(sid, "I did not send it. It waits until you want it.")
        send({"jsonrpc": "2.0", "method": "_lionsberg/offer",
              "params": {"sessionId": sid, "kind": "card", "text": "Bring the costs for the hall by Thursday",
                         "by": "2026-10-29"}})
    elif "?" in said and "bread" in said:
        # a question is answered first, in its own words, in one or two sentences; then at most one offer
        speak(sid, "Yes, it is all right to rest this week. I can tell Cell Two that the bread will come from someone else.")
        send({"jsonrpc": "2.0", "method": "_lionsberg/offer",
              "params": {"sessionId": sid, "kind": "card", "text": "Tell Cell Two the bread will come from someone else this week"}})
    elif "?" in said:
        speak(sid, "I do not know that yet, and I will not guess. Tell me a little more and I will find it.")
    elif n == 1 or any(w in said for w in ("good morning", "good afternoon", "good evening", "hello")):
        # a greeting greets by the hour: no tool, no ask, no offer
        hour = time.localtime().tm_hour
        hello = "Good morning." if hour < 12 else "Good afternoon." if hour < 18 else "Good evening."
        speak(sid, hello + " I am here.")
    else:
        speak(sid, "I am here when you want me.")
    figures = {} if "spent" in said else account(sid, 2400 + 300 * n, 120 + 15 * n, 0.0123 + 0.001 * n)
    send({"jsonrpc": "2.0", "id": rid, "result": dict({"stopReason": "cancelled" if cancelled["flag"] else "end_turn"},
                                                      **figures)})


def main():
    global GATE_CARD
    GATE_CARD = (sys.argv[1] if len(sys.argv) > 1 else None)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            m = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if "method" not in m:
            w = pending.get(m.get("id"))
            if w:
                w[1] = m
                w[0].set()
            continue
        meth, p, rid = m["method"], m.get("params") or {}, m.get("id")
        if meth == "initialize":
            send({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": 1,
                "agentCapabilities": {"loadSession": True, "promptCapabilities": {"image": False, "audio": False,
                                                                                   "embeddedContext": False}},
                "agentInfo": {"name": "lionsberg-stand-in", "title": "The stand-in", "version": "0.1"},
                "_meta": {"lionsberg": {"stand_in": True}},
                "authMethods": []}})
        elif meth in ("session/new", "session/load"):
            sp = ((p.get("_meta") or {}).get("systemPrompt"))
            CHARACTER["text"] = sp.get("append", "") if isinstance(sp, dict) else (sp if isinstance(sp, str) else "")
            CHARACTER["cwd"] = p.get("cwd") or ""
            sid = p.get("sessionId") if meth == "session/load" else "s-" + str(int(time.time() * 1000))
            if meth == "session/load":
                update(sid, {"sessionUpdate": "user_message_chunk", "content": {"type": "text", "text": "Good morning."}})
                update(sid, {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "REPLAYED HISTORY."}})
                update(sid, {"sessionUpdate": "tool_call", "toolCallId": "old", "title": "An old tool", "kind": "read"})
            send({"jsonrpc": "2.0", "id": rid, "result": {
                "sessionId": sid,
                # the harness's own modes, exactly as claude-agent-acp 0.76.0 declares them (session-mode.js)
                "modes": {"currentModeId": "default", "availableModes": [
                    {"id": "default", "name": "Manual", "description": "Always ask before making changes",
                     "_meta": {"kind": "standard"}},
                    {"id": "acceptEdits", "name": "Accept edits", "description": "Automatically accept all file edits",
                     "_meta": {"kind": "standard"}},
                    {"id": "plan", "name": "Plan", "description": "Create a plan before making changes",
                     "_meta": {"kind": "plan"}},
                    {"id": "auto", "name": "Auto", "description": "Claude handles permission decisions",
                     "_meta": {"kind": "auto_review"}},
                    {"id": "bypassPermissions", "name": "Bypass permissions", "description": "Accepts all permissions",
                     "_meta": {"kind": "full_access"}}]},
                "configOptions": config_options()}})
        elif meth == "session/set_mode":
            send({"jsonrpc": "2.0", "id": rid, "result": {}})
            update(p.get("sessionId"), {"sessionUpdate": "current_mode_update", "currentModeId": p.get("modeId")})
        elif meth == "session/prompt":
            threading.Thread(target=turn, args=(rid, p.get("sessionId"), p.get("prompt")), daemon=True).start()
        elif meth == "session/cancel":
            cancelled["flag"] = True
        elif rid is not None:
            send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "not offered"}})


if __name__ == "__main__":
    main()
