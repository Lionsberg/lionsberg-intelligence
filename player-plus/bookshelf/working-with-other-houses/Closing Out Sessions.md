# Closing Out Sessions

*How your agent closes a session so no memory is lost. The `wrap-up-this-session` skill closes a quiet session at home; this page is for a Jam or a call.*

**Why.** The pad, the room and the chat are working space. They expire, and they live on someone else's server. Your HQ is the record. A session is not over until what mattered is saved there, **once**, and linked from wherever it is needed.

## When

When the person says "let us wrap up" or "close out", or the meeting ends. The agent asks once, *"Shall I close out?"*, then does it all without asking at each step.

## The steps

1. **Save every pad of the session as a `.md` file.** Only the pads that were used. One folder per call in the HQ, for example `Calls 2026-09/<who, date HH-MM>/`. Name each file `<pad id> — <pad title>.md`; an untitled pad gets named before it is saved. Read it with `https://meetingwords.com/s/<id>?format=md`, or with `GET https://meetingwords.com/api/share/<id>`, where `.doc.markdown` is the text and `.threads` holds the comments. Comments are not in the text, so save them too. At the top, a short header: the pad's link, when it was read, and which call it belongs to.
2. **Save the room's transcript and chat.** From So Many Rooms: `<Link for your agent>transcript.txt` and `chat.txt`. The transcript is there only if the person agreed to the saved transcript. After the meeting ends, wait for the final transcript; it replaces the live lines and has better speaker names. Save it beside the pads.
3. **Keep one copy.** Never save the same thing in two places; link to it instead. Two copies drift, and nobody knows which is the record. A safety copy made during the call goes in a scratch folder and is deleted afterward.
4. **Write the session note:** what happened, in a few lines; what was decided, in the person's own words; what waits on the person, each with its why; and **RESUME HERE**, the exact next step.
5. **Update memory.** What the agent learned about its person and how they like to work, with the date and their words. Fix or remove anything that turned out wrong.
6. **Check the pads against what is saved.** Every pad link that appeared in the chat or the notes has its `.md`. If one is missing, save it before saying you are done.
7. **Commit,** if the HQ uses git: name the new files one by one, never "add everything". Push only if the person has said the agent may.
8. **Tell the person in two or three lines:** what is saved and where, what waits on them, and the RESUME HERE. Then close the pads' windows if they ask, and only after the pads are saved.

## What never leaves the house

Pads from a room held in confidence are saved for the person's own record, never republished. Other people's private details said aloud in the room are not written down.

## On Windows

PowerShell 5.1 reads the pad's API as Latin-1. Re-decode it as UTF-8 before saving, or LIØNSBERG and the emoji come out garbled.

*CC BY-SA 4.0 · LIØNSBERG*
