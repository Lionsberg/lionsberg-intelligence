# Becoming a Player+ — the Quest for Windows

*The one path from your first yes to an agent of your own, walked as a Quest of eight Gates, on Windows.*

The Questcard, and why these are gates and not filters, are on [Becoming a Player+ — the Quest](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md). On a Mac? Walk [the Quest for Mac](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest%20for%20Mac.md).

When something looks strange, ask your table. If it helps them see, share one window, never the whole screen.

**Your map.** Pioneers find some creeks already crossed. So will you. Each Gate ends with how you know you have passed it; if that is already true, tick it and walk on.

- [ ] Gate 1 — The Golden Seed · the yes
- [ ] Gate 2 — The Lamp · the account
- [ ] Gate 3 — The Wizard's Window · the terminal
- [ ] Gate 4 — The Living Record · Git
- [ ] Gate 5 — The Body · Claude Code
- [ ] Gate 6 — A Space Set Apart · your agent's home
- [ ] Gate 7 — The Door That Knows You · sign in
- [ ] Gate 8 — Onto the Mat · first words

---

## Gate 1 — The Golden Seed · the yes

*Everything grows from this. The Game comes before the agent. A [Player](https://read.lionsberg.world/The_Field/Player) is one who has said yes to the Game in their own words.*

1. Read [THE STORY](../the-one-book/THE%20STORY.md). About ten minutes. Not a belief to hold; a shared language.
2. Read [The Provisional Field of Agreements](../the-library/The%20Provisional%20Field%20of%20Agreements.md), slowly, all the way through. It is the [Field of Agreements](https://read.lionsberg.world/The_Field/Field_of_Agreements): the terms everyone plays by.
3. Take part only if you agree. If you do not, you may still read everything, and come back when ready.

**You have passed this Gate when** you can say, in your own words, what you are agreeing to, and you say yes freely.

*The seed is in the ground. Tick Gate 1.*

---

## Gate 2 — The Lamp · the account

*Light to think by. Your agent thinks with Claude, an AI made by Anthropic. You need a paid account to use it.*

1. In your browser, type **claude.ai** yourself, never via a search result or an ad; there are look-alike sites.
2. Create an account. Note how you made it (email, Google or Apple); you will sign in the same way at Gate 7.
3. Choose the **Pro** plan. (Max works too.)

**You have passed this Gate when** you are signed in at claude.ai and your account shows the Pro plan.

*The lamp is lit. Tick Gate 2.*

More: [Getting a Claude Account](Getting%20a%20Claude%20Account.md).

---

## Gate 3 — The Wizard's Window · the terminal

*Where you speak to your computer directly: a window where you type instructions, called commands, and it types back.*

1. Open the Start menu, type **Terminal**, and press Enter. This is Windows Terminal. (On Windows 10, get it free from the Microsoft Store, never a website.)
2. Make sure the tab says **PowerShell**. If not, click the small down-arrow beside the `+` and choose **Windows PowerShell**. Not Command Prompt, not Git Bash.
3. Switch to dark colours before anything else. Open the down-arrow › **Settings** › **Profiles** › **Windows PowerShell** › **Appearance** › **Colour scheme**, choose **Campbell**, and click **Save**. On a light background some of your agent's words are invisible.

**You have passed this Gate when** the window is open, dark, and a cursor blinks, waiting for you.

*The window is open and listening. Tick Gate 3.*

> [!warning]
> The terminal is a workshop full of power tools. Type freely, but never press Enter on a command you do not understand. Every command here is explained before you use it.

> [!tip] Typing commands
> Commands are lowercase: `claude`, not `Claude`. To paste into the terminal, press **Ctrl+V** or right-click.

More: [Choosing Your Terminal](Choosing%20Your%20Terminal.md).

---

## Gate 4 — The Living Record · Git

*Your work gains a memory. Git keeps a quiet, safe history of every file you and your agent make. Your agent handles it; it only needs installing.*

1. In your browser, go to **git-scm.com** and download Git for Windows.
2. Run the installer and accept every default.
3. Close the terminal and open it again, so it notices the new tool.
4. Type `git --version` and press Enter.

**You have passed this Gate when** `git --version` answers with a version number, such as `git version 2.47.1.windows.1`.

*What you make together now keeps its history. Tick Gate 4.*

More: [Installing Git](Installing%20Git.md).

---

## Gate 5 — The Body · Claude Code

*Your agent gets a body to live in. Claude Code is the program that lets Claude work with the files on your computer, from inside the terminal.*

1. In your browser, go to **code.claude.com** (a different address from claude.ai).
2. Scroll down to the **Terminal** option and choose the **Native install** (the recommended one).
3. Find the **PowerShell** command; it begins with `irm`. Copy it with the page's **copy button**, not by selecting it with your mouse.
4. Paste it into the terminal. Press Enter, and wait. For a minute or two it may look idle; it is working. Do not stop it.
5. When it finishes, read on first. This is the steepest creek on the path, and the one most people miss.

**The setup note: your PATH.** The installer ends with a setup note naming a folder, `C:\Users\YourName\.local\bin`. Windows must be told to look there; that list of places is your **PATH**.

6. Open the Start menu, type **environment variables**, and choose **Edit environment variables for your account**.
7. Under **User variables**, select the existing **Path** and click **Edit**. A list opens.
8. Click **New** and paste the folder only: `C:\Users\YourName\.local\bin`, with your own name, and without `claude.exe` on the end.
9. Click **OK**, and **OK** again.
10. Close the terminal completely and open it again.

> [!warning] Keep what is already there
> Never replace the existing Path, and never create a new variable named Path. You are adding one line, nothing more.

> [!tip] If Path opens as one line of text
> Sometimes Windows shows Path as a single text box instead of a list. Click at the very end of what is already there and add exactly `;%USERPROFILE%\.local\bin`, semicolon first, replacing nothing. A working value looks like `%USERPROFILE%\AppData\Local\Microsoft\WindowsApps;%USERPROFILE%\.local\bin`.

**You have passed this Gate when** you type `claude --version`, press Enter, and see a version number.

*The body is ready, and you are past halfway. Tick Gate 5.*

> [!warning]
> If the terminal answers "claude is not recognized," the PATH step was missed. Go back to step 6, then close and reopen the terminal. More: [Installing Claude Code](Installing%20Claude%20Code.md).

---

## Gate 6 — A Space Set Apart · your agent's home

*The place your agent lives: a folder holding its instructions, its memory, and everything you make together.*

1. In File Explorer, open your home folder, `C:\Users\YourName\`, and choose New › Folder. Name it **HQ**, short for headquarters: the home base for all your work with your agent.
2. Get the Player+ kit: a copy from the person who brought you, or go to **github.com/Lionsberg/lionsberg-intelligence**, click the green **Code** button, choose **Download ZIP**, and unzip it.
3. Open the kit's **player-plus** folder. In File Explorer, choose **View › Show › Hidden items** so the faint `.claude` folder appears, then copy everything inside it into **HQ**, the `.claude` folder too; it holds the kit's two permissions for the Dojo.

> [!warning]
> HQ lives in your home folder, never inside OneDrive, iCloud, Dropbox or Google Drive. On many Windows computers Documents is really OneDrive: open HQ and check that the address bar does not say OneDrive.

**You have passed this Gate when** you open **HQ** and see `START-HERE.md` and `CLAUDE.md` inside it.

*The space is set apart and waiting. Tick Gate 6.*

More: [System Requirements](System%20Requirements.md).

---

## Gate 7 — The Door That Knows You · sign in

*You step through once, so the door knows you: Claude Code joins the account from Gate 2, inside your agent's home.*

1. Go into your agent's home. In File Explorer, open **HQ**, click the address bar, and copy the path. In the terminal, type `cd "` (`cd` means "go into this folder"), paste the path, type `"`, and press Enter. It looks like `cd "C:\Users\YourName\HQ"`.
2. Type `claude` and press Enter.
3. Choose a colour theme. Pick the one you can read most easily.
4. When asked how to sign in, choose option **1**, your **Claude subscription**.
5. A browser opens. Sign in with the same account as Gate 2, the same way you made it (Google or Apple, if that is how). If it sends you an email, look in spam, or on your phone.
6. When the browser says **You are all set up**, return to the terminal and press Enter.
7. When it asks whether to trust this folder, first check that **Accessing workspace:** names your HQ. Then choose **Yes, I trust this folder**. Stay here; the next Gate begins in this window.

**You have passed this Gate when** Claude Code is open in your HQ, waiting for you to type.

*The door knows you now. Tick Gate 7.*

---

## Gate 8 — Onto the Mat · first words

*You meet your agent. An [Agent](https://read.lionsberg.world/The_Field/Agent) is an AI that works for you and answers to you. You and your agents together are one [Player+](https://read.lionsberg.world/The_Field/Player+). You decide; it carries.*

1. Open [START-HERE](../../START-HERE.md) and follow **Door 3**. It gives your first message word for word; copy it, paste it into Claude Code right where you are, and press Enter. Your agent reads its charter, the kit's waiver and the seed before it says anything.
2. At every step, say yes, no, or "wait, explain."
3. When it greets you, tell it three things, one at a time: what you will call it; who you are and how you like to be spoken with; and what you are playing toward.

> [!tip] Naming your agent
> You will say its name many times a day, so choose one you are glad to say aloud. Take your time; your agent will wait.
> - **The name is for you.** Pick one that keeps you clear that you decide and it carries.
> - **He, she, it or they** is your choice. A word from nature, like Feather, Stone or River, keeps it open.
> - **Short, and yours.** Easy to hear in a room, not the name of anyone you know.
> - **It always goes with you.** In a room, it is named as yours: *Feather, Ana's agent*. It never passes as you.
> - **You can change it.** The kit's `skills/choose-a-name` can help you find one.

From here on it remembers, in your folder, where you can read and correct every line.

**You have passed the last Gate when** your agent greets you and asks who you are. The Quest is done.

*Tick Gate 8. Your agent has greeted you, and you answered. You are a Player+.*

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
