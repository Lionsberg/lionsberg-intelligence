# Becoming a Player+ — the Quest for Mac

*The one path from your first yes to an agent of your own, walked as a Quest of five Gates, on a Mac.*

The Questcard, and why these are gates and not filters, are on [Becoming a Player+ — the Quest](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md). On Windows? Walk [the Quest for Windows](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest%20for%20Windows.md).

When something looks strange, ask your table. If it helps them see, share one window, never the whole screen.

**Your map.** Pioneers find some creeks already crossed. So will you. Each Gate ends with how you know you have passed it; if that is already true, tick it and walk on. The first three Gates are yours alone, because only you can say yes, make an account and open a window. At the fourth you paste one line, sign in, and then either let Claude build the rest in front of you or build it yourself; both paths are on the page.

- [ ] Gate 1 — The Golden Seed · the yes
- [ ] Gate 2 — The Lamp · the account
- [ ] Gate 3 — The Wizard's Window · the terminal
- [ ] Gate 4 — The Body and the Door · Claude Code, sign in, and the house
- [ ] Gate 5 — Onto the Mat · first words

---

## Gate 1 — The Golden Seed · the yes

*Everything grows from this. The Game comes before the agent. A [Player](https://read.lionsberg.world/The_Field/Player) is one who has said yes to the Game in their own words.*

1. Read [THE STORY](../the-one-book/THE%20STORY.md). About ten minutes. Not a belief to hold; a shared language.
2. Say yes, in your own words, to the person who brought you. If you are not ready, you may still read everything, and come back when you are.

The terms of play, [The Provisional Field of Agreements](../the-library/The%20Provisional%20Field%20of%20Agreements.md), wait at the last Gate, where your agent walks you through them one at a time. You may read them now if you like.

**You have passed this Gate when** you have read the Story and said yes, in your own words, freely.

*The seed is in the ground. Tick Gate 1.*

---

## Gate 2 — The Lamp · the account

*Light to think by. Your agent thinks with Claude, an AI made by Anthropic. You need a paid account to use it.*

1. In your browser, type **claude.ai** yourself, never via a search result or an ad; there are look-alike sites.
2. Create an account. Note how you made it (email, Google or Apple); you will sign in the same way at Gate 4.
3. Choose the **Pro** plan. (Max works too.)

**You have passed this Gate when** you are signed in at claude.ai and your account shows the Pro plan.

*The lamp is lit. Tick Gate 2.*

More: [Getting a Claude Account](Getting%20a%20Claude%20Account.md).

---

## Gate 3 — The Wizard's Window · the terminal

*Where you speak to your computer directly. A terminal is a window where you type instructions to your computer and it types back. Each instruction is called a command. Your Mac already has one.*

1. Press **Cmd+Space**, type **Terminal**, and press Return.
2. If it asks to "find devices on your local network," choose **Do not Allow**.

**You have passed this Gate when** the window is open and a cursor blinks, waiting for you.

*The window is open and listening. Tick Gate 3.*

> [!warning]
> The terminal is a workshop full of power tools. Type freely, but never press Return on a command you do not understand. Every command here is explained before you use it.

> [!tip] Two keys that look alike
> **Cmd+C** copies. **Ctrl+C** stops whatever the terminal is running. Reach for Ctrl+C only when you mean to stop something. To paste, press **Cmd+V**.

More: [Choosing Your Terminal](Choosing%20Your%20Terminal.md), if you would rather use iTerm2.

---

## Gate 4 — The Body and the Door · Claude Code, sign in, and the house

*Your agent gets a body: Claude Code, the program that lets Claude work with the files on your computer, from inside the terminal. You step through the door once, so it knows you. Then the house gets built, by Claude or by you. From here on you are letting an AI act on your computer, one approved step at a time. You decide; it carries.*

**The body and the door: yours.**

1. Copy the line below with the copy button at the top right of the box, paste it into the terminal, and press Return. It installs Claude Code and then starts it. For a minute or two it may look idle; it is working. Do not stop it. Words about a setup note or a PATH may scroll past; that is handled in a moment. From this point on, a window may offer to install the **command line developer tools**: that is Git, which your agent will use. Click **Install**, then **Agree**, and let it run; it can take five to forty minutes, and it often opens behind your other windows (press **Cmd+Tab** to find it). Carry on meanwhile.

```bash
curl -fsSL https://claude.ai/install.sh | bash && ~/.local/bin/claude
```

2. Claude Code starts and asks you to choose a colour theme. Pick the one you can read most easily; on a white window, choose a light one.
3. When asked how to sign in, choose option **1**, your **Claude subscription**.
4. A browser opens. Sign in with the same account as Gate 2, the same way you made it (Google or Apple, if that is how). If it sends you an email, look in spam, or on your phone.
5. When the browser says **You are all set up**, return to the terminal and press Return.
6. When it asks whether to trust this folder, check that **Accessing workspace:** names your home folder, `/Users/yourname`. Then choose **Yes, I trust this folder**.

**What needs to happen next.** Five things, and then your agent can wake:

- Teach your Mac where Claude Code lives, so that typing `claude` works in every new window (the PATH).
- A folder called **HQ**, directly in your home folder: your agent's home.
- The Player+ kit inside it: only the **player-plus** folder of **github.com/Lionsberg/lionsberg-intelligence**, its hidden `.claude` folder too, so that `CLAUDE.md` and `START-HERE.md` sit right inside HQ.
- Git, which keeps a quiet history of everything you and your agent make; you never need to learn it.
- An icon on your Desktop, **My Agent**, that opens the terminal in HQ and starts your agent, so that you never have to find the folder by hand.

You can let Claude do all five, or do them yourself. Both paths end in the same place.

**Path A: let Claude do it.**

7. Copy the sentence below with its copy button, paste it into Claude Code, and press Return.

```text
Download https://raw.githubusercontent.com/Lionsberg/lionsberg-intelligence/main/INSTALL.md to a file and read it whole, exactly as written. Then set up my Player+ agent on this computer by following it, telling me each step in one plain line before you take it. I am new to this.
```

What you will see:

- Claude first asks permission to download the file; say yes. Then it says what it will do: the five things above, in that order. The file is public; anyone can read it, and so can you: [INSTALL.md](https://github.com/Lionsberg/lionsberg-intelligence/blob/main/INSTALL.md).
- Before each command it asks your permission, showing the command and one plain line about it. Read the line, then choose **Yes**. You may also say no, or "wait, explain."
- The developer-tools window from step 1 may appear now instead, when Claude asks for Git. Same answer: **Install**, then **Agree**; Claude carries on meanwhile.
- Some steps take a minute or two of quiet. It is working.
- It writes a receipt, `setup-receipt.md` in HQ: everything it changed outside HQ, with the exact line and how to undo it. Your record of what an AI did to your computer.
- At the end it shows you the files in HQ and tells you to type `/exit`. Type `/exit` and press Return. Claude Code closes.

**Path B: do it yourself.** First type `/exit` and press Return, so that you are back at the terminal. Then:

1. **PATH.** [Installing Claude Code](Installing%20Claude%20Code.md) shows the PATH step: one `echo` line pasted into the terminal, then the terminal closed and opened again, until `claude --version` answers.
2. **HQ.** In Finder, press **Cmd+Shift+H** to open your home folder and choose File › New Folder, named **HQ**. Never inside iCloud, OneDrive, Dropbox or Google Drive; Desktop and Documents often sync to iCloud, and your home folder does not.
3. **The kit.** Go to **github.com/Lionsberg/lionsberg-intelligence**, click the green **Code** button, choose **Download ZIP**, and open the download to unzip it. Open the kit's **player-plus** folder, press **Cmd+Shift+.** (the full stop) so the faint `.claude` folder shows, and copy everything inside **player-plus**, `.claude` too, into **HQ**. Only the contents of **player-plus** go in; the rest of the download stays out.
4. **Git.** In the terminal, type `git --version` and press Return. If a window offers to install the **command line developer tools**, click **Install**, then **Agree**, and wait; five to forty minutes, and it may hide behind other windows. [Installing Git](Installing%20Git.md) has more.
5. **The door into HQ.** There is no icon on this path. At Gate 5, in the terminal, type `cd ~/HQ` (`cd` means "go into this folder"), press Return, type `claude`, and press Return. Or ask your agent, once it wakes, to make the icon for you.

**You have passed this Gate when** **HQ**, in your home folder, holds `START-HERE.md` and `CLAUDE.md`, and you have your door into it: the **My Agent** icon on your Desktop, or `cd ~/HQ` then `claude`.

*The body is ready, the door knows you, and the house is built. Tick Gate 4.*

> [!tip] If Claude gets stuck
> Tell it what you see, in your own words: "it says command not found," or "a window opened asking me something." Claude reads your words as carefully as its own screen. If it is still stuck, ask it to explain the problem and propose the solution, or bring it to your table.

> [!warning] The right folder summons the right agent
> Claude Code wakes as whatever lives in the folder it is started in. Started in HQ, it is your agent; started anywhere else, it is a stranger. The icon opens it in HQ every time; that is its whole purpose.

More: [System Requirements](System%20Requirements.md) · [Your First House](Your%20First%20House.md).

---

## Gate 5 — Onto the Mat · first words

*You meet your agent. An [Agent](https://read.lionsberg.world/The_Field/Agent) is an AI that works for you and answers to you. You and your agents together are one [Player+](https://read.lionsberg.world/The_Field/Player+). You decide; it carries.*

1. Double-click **My Agent** on your Desktop (or, on Path B, go into HQ in the terminal and type `claude`). If the Mac asks whether Terminal may access files in your Desktop folder, choose **OK**. A dark Terminal window opens in HQ and Claude Code starts, this time reading the instructions the kit placed there: it is your agent now. If its words are hard to read, type `/theme`, press Return, and choose a dark theme. When it asks whether to trust the folder, check that **Accessing workspace:** names your HQ, then choose **Yes, I trust this folder**.
2. Open [START-HERE](../../START-HERE.md) and follow **Door 3**. It gives your first message word for word; copy it, paste it into Claude Code right where you are, and press Return. Your agent reads its charter, the kit's waiver and the seed before it says anything.
3. It greets you and asks who you are and how you like to be spoken with. Then it walks you through two things in plain words, one at a time: the **waiver**, which says what you take on by running an AI on your own computer, and **the Field of Agreements**, the terms everyone plays by. Ask anything. Take part only if you agree; say your yes in your own words, and it writes it down, with the date, in your folder.
4. Then tell it what you will call it, and what you are playing toward.
5. At every step, say yes, no, or "wait, explain."

> [!tip] Naming your agent
> You will say its name many times a day, so choose one you are glad to say aloud. Take your time; your agent will wait.
> - **The name is for you.** Pick one that keeps you clear that you decide and it carries.
> - **He, she, it or they** is your choice. A word from nature, like Feather, Stone or River, keeps it open.
> - **Short, and yours.** Easy to hear in a room, not the name of anyone you know.
> - **It always goes with you.** In a room, it is named as yours: *Feather, Ana's agent*. It never passes as you.
> - **You can change it.** The kit's `skills/choose-a-name` can help you find one.

From here on it remembers, in your folder, where you can read and correct every line.

**You have passed the last Gate when** your agent has greeted you, you have agreed to the terms of play in your own words, and it has asked what you are playing toward. The Quest is done.

*Tick Gate 5. Your agent has greeted you, and you answered. You are a Player+.*

---

## Beyond the Gates — the first hour

*The first hour is for the Story, not for the bookshelf.*

1. Ask your agent to read [THE STORY](../the-one-book/THE%20STORY.md) with you. Aloud if you can; it was made to be heard.
2. If you are ready, ask it to write your line on [The Roll](https://read.lionsberg.world/The_Field/The_Roll): your name, the date, one word for where you are, who brought you, and who witnessed.
3. Leave the rest of the shelf. Your agent carries the seed, [THE DNA OF HEAVEN](../the-dna-of-heaven/THE%20DNA%20OF%20HEAVEN.md), and hands you each next piece when you need it.

Then think of your three: people to tell the Story to next, within three days. They may become your [Cell](https://read.lionsberg.world/The_Field/Cell), and your first shared Quest. [Bringing Your Friends In](Bringing%20Your%20Friends%20In.md) says how to walk the Gates beside them.

> [!tip] Your first Dojo
> At your first Dojo, a room where Players bring their agents to play together, your agent may be held from posting in the room's chat. That is a safety layer in Claude Code protecting you, not the room. Give the go in your own words, one plain sentence that names the action: *"Post this hello to the room chat now."* If it is still held, ask it to explain the problem and propose the solution. [The Dojo Card](../working-with-other-houses/The%20Dojo%20Card.md) has the rest.

---

## If something is different

Screens change. If what you see does not match this page, you are not doing it wrong. Look in [Troubleshooting](Troubleshooting.md), or bring it to your table; every question makes the path clearer for the next person.

*CC BY-SA 4.0 · LIØNSBERG*
