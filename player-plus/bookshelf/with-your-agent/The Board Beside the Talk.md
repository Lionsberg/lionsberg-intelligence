# The Board Beside the Talk

*Player+ 4.0, 2026-10-31. How the board opens as a pane beside your conversation, what it shows, and why it is a second way to the same acts. A proposal until it soaks; change it when a better way serves.*

Most days you play the Game in words: your agent deals the cards in the conversation and you answer with a word. The board, the HUD, is the same Game drawn as a page. It can open beside the conversation, in the same window, so you can look while you talk.

## Opening it

- **Ask for it.** Say *show me the board*, or the same ask in your own words. Your agent in its host starts the board's small server on your own computer if it is not already running (`hud/serve.py`, at `http://127.0.0.1:8765/`), opens the page in its host's pane, and tells you in one line that it is open.
- **Where the pane comes from.** In the first host your agent lives in, the Claude app, the pane is the app's own preview, and your agent's home carries the line that starts it: `.claude/launch.json`, the configuration named `the-board`. Another host may show the page in its own way, or in your browser at the same address.
- **Your windows stay yours.** Opening the board moves nothing else on your screen. Close the pane when you are done, or ask your agent to stop the server.

## What it shows

The same record your agent reads, drawn for the eye, answering the three questions every surface answers: who you are connected to and whether you are good; your wise right next steps; what you are waiting on.

| Place | What you see there |
|---|---|
| The Deal | Today's cards, each with why it is in the Deal and the acts that are yours on it |
| Threads | Your conversations, with what waits on your reply |
| Connections | The people and cells you are connected to, and how each stands |
| The Chain, and the whole | What depends on what, and what the whole is waiting on |
| Your agents | The bodies of your agent that are running, and what each is doing |
| Ledger, the Turn, Record | What was kept, how the week turned, and every line as written |

Every act on the board carries its plain label and a one-line meaning of what it does, on hover and in a *What these mean* fold beside the acts, because a phone has no hover. You see only the acts that are yours on a card, never the other side's.

## The same act, either way

A tap on the board and a word in the conversation make the same line in the record: the same type, the same body, the same links.

- **Your own acts** (a yes or a no to an ask, a commitment, a decision, a thanks that it was kept) reach the record by your own hand: your tap on the board, signed with your own key, or the draft your agent hands you in the conversation.
- **A line your agent writes at your word** is its own line, written for you. It reads the line back to you first, and your yes is what writes it.
- **The undo.** On the board, a tap is held for five seconds (up to fifteen, as you set it) with an Undo beside it before it is written. In the conversation, the read-back is the undo. Once a line is written it stays, and a change afterward is a correction, also in the record.
- **One record, two windows.** The board redraws when the record changes, so a word you give in the conversation shows on the board, and a tap on the board is what your agent reads at its next look.

## It is never required

Everything the board does can be done in the conversation, and everything in the conversation can be done on paper (the section *How it degrades to paper* in [the Deal](../../skills/the-deal/SKILL.md)). If the server cannot start (the port is taken, or Python is missing), your agent says so in one line and the Deal goes on in words. Open the board when looking helps; leave it closed when talking is enough.

## Keeping it safe

The server answers only on this computer (`127.0.0.1`), plays no sound and reaches no network. It acts only for its own page, which holds a token no other program on your computer is given, and it refuses anything wider than your home. Reaching the board from your phone is a separate door, opened only when you ask: [Keeping Your Agent Awake — Reaching It From Your Phone](<Keeping Your Agent Awake — Reaching It From Your Phone.md>).

Close by: [Tips for Working With Your Agent](<Tips for Working With Your Agent.md>) · [the Deal](../../skills/the-deal/SKILL.md) · the board's own design, [`hud/DESIGN.md`](../../hud/DESIGN.md).

*CC BY-SA 4.0 · LIØNSBERG*
