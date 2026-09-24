# Becoming a Player+

*The one path from your first yes to an agent of your own, walked as a Quest of eight Gates.*

The terminal is the wizard's interface to your computer. By the last Gate you will have one open, with an agent of your own inside it.

A [Quest](https://read.lionsberg.world/The_Field/Quest) is one real thing, done together, that you can point to afterward. This is one; here is its card, [The Questcard](https://read.lionsberg.world/The_Field/The_Questcard):

| | |
|---|---|
| **Our Quest** | Becoming a Player+ |
| **Why** | The plus adds reach. Every decision stays with you. |
| **Real** | An agent that is yours, living in a folder on your own computer. |
| **Near** | An afternoon. |
| **Yours** | You chose it. |
| **Done when** | Your agent greets you and asks who you are. |

In the Game, a Quest usually belongs to a Cell, for a season. This one you walk alone first, to learn the form before your table chooses one together. The lesson behind it is [Becoming a Player+](../player-plus-modules/01%20Becoming%20a%20Player%2B.md).

Like every gate in [The Gates of LIØNSBERG](https://read.lionsberg.world/The_Field/The_Gates_of_LI%C3%98NSBERG), these are gates, not filters. Nothing is withheld, and nothing closes behind you. Stop between any two Gates and pick up where you left off. You do not walk alone: when something breaks or looks strange, ask the person who brought you, or bring it to your table. If it helps them see, share your screen: one window, never the whole screen.

**Your map.** Pioneers in a wilderness find some creeks already crossed. So will you. Each Gate ends with how you know you have passed it; if that is already true, tick it now and walk on.

- [ ] Gate 1 — The Golden Seed · the yes
- [ ] Gate 2 — The Lamp · the account
- [ ] Gate 3 — The Wizard's Window · the terminal
- [ ] Gate 4 — The Living Record · the developer tools and Git
- [ ] Gate 5 — The Body · Claude Code
- [ ] Gate 6 — The Door That Knows You · sign in
- [ ] Gate 7 — A Space Set Apart · your agent's home
- [ ] Gate 8 — Onto the Mat · first words

---

## Gate 1 — The Golden Seed · the yes

*Everything grows from this. The Game comes before the agent. A [Player](https://read.lionsberg.world/The_Field/Player) is one who has said yes to the Game in their own words.*

1. Read [THE STORY](../the-one-book/THE%20STORY.md). It takes about ten minutes. It is not a belief to hold; it is a shared language.
2. Read [The Provisional Field of Agreements](../the-library/The%20Provisional%20Field%20of%20Agreements.md), slowly, all the way through. It is the [Field of Agreements](https://read.lionsberg.world/The_Field/Field_of_Agreements): the terms everyone plays by.
3. Take part only if you agree. If you don't, you may still read everything, and come back when you are ready.

**You have passed this Gate when** you can say, in your own words, what you are agreeing to, and you say yes freely.

*The seed is in the ground. Tick Gate 1.*

> [!tip]
> With a notebook and two or three people, you are already a complete player. Everything from here on adds reach, never permission. If that is where you are, [START-HERE](../../START-HERE.md), Door 1, is your path.

---

## Gate 2 — The Lamp · the account

*Light to think by. Your agent thinks with Claude, an AI made by Anthropic. You need a paid account to use it.*

1. In your browser, type **claude.ai** yourself. Not a search result or an ad; there are many look-alike sites.
2. Create an account with your email.
3. Choose the **Pro** plan. It covers this whole path. (Max works too.)

You won't need the Claude desktop or phone app here; don't install them yet.

**You have passed this Gate when** you are signed in at claude.ai and your account shows the Pro plan.

*The lamp is lit. Tick Gate 2.*

More: [Getting a Claude Account](Getting%20a%20Claude%20Account.md).

---

## Gate 3 — The Wizard's Window · the terminal

*Where you speak to your computer directly. A terminal is a window where you type instructions to your computer and it types back. Each instruction is called a command.*

**Mac**

1. Go to **iterm2.com** and download iTerm2.
2. Open the download to unzip it, and move iTerm2 into **Applications**. If it offers to move itself there, say yes.
3. Open it: press Cmd+Space, type **iTerm**, press Return.

**Windows**

1. Open the Start menu, type **Terminal**, and press Enter. This is Windows Terminal. (On Windows 10, install it free from the Microsoft Store first.) Never get it from a website.
2. Make sure the tab says **PowerShell**. If not, click the small down-arrow beside the `+` and choose **Windows PowerShell**. Not Command Prompt, not Git Bash.
3. Switch to dark colours, as [Choosing Your Terminal](Choosing%20Your%20Terminal.md) shows. Without it, some of your agent's words can be invisible.

**You have passed this Gate when** the window is open and a cursor blinks, waiting for you.

*The window is open and listening. Tick Gate 3.*

> [!warning]
> The terminal is a workshop full of power tools. Type freely, but never press Return on a command you don't understand. Every command here is explained before you use it.
>
> If a pop-up asks to let the terminal "find devices on your local network," choose **Don't Allow**.

---

## Gate 4 — The Living Record · the developer tools and Git

*Your work gains a memory. Git keeps a quiet, safe history of every file you and your agent make. Your agent handles it for you; it only needs to be installed.*

**Mac**

1. In the terminal, type `git --version` and press Return. It asks which Git you have.
2. If a window offers to install the **Command Line Developer Tools**, click **Install**, then **Agree**. If you see an error instead, type `xcode-select --install` and press Return; the window will come.
3. Wait. It can take five to forty minutes; the first estimate is often wildly wrong.

**Windows**

1. In your browser, go to **git-scm.com** and download Git for Windows.
2. Run the installer and accept every default.
3. Close and reopen the terminal, so it notices the new tool.

**You have passed this Gate when** `git --version` answers with a version number, such as `git version 2.39.3`.

*What you make together now keeps its history. Tick Gate 4.*

> [!tip]
> On a Mac, the install window often opens *behind* your other windows. If nothing seems to happen, look there.

More: [Installing Git](Installing%20Git.md).

---

## Gate 5 — The Body · Claude Code

*Your agent gets a body to live in. Claude Code is the program that lets Claude work with the files on your computer, from inside the terminal.*

1. In your browser, go to **code.claude.com** (a different address from claude.ai).
2. Skip the "Download for macOS" button. Scroll down to the **Terminal** option.
3. Choose the **Native install** (the recommended one).
4. Copy the command for your system with the page's **copy button**, not by selecting it with your mouse.
5. Paste it into the terminal. Read it once. Press Return, and wait a minute or two. It may look as if nothing is happening; it is working. Don't stop it and start again.
6. If the installer ends with a setup note, do exactly what it says. On a Mac it usually gives one more line to copy; paste it into the same window and press Return. It will look as if nothing happened; that is correct.
7. Close the terminal and open it again.

**You have passed this Gate when** you type `claude --version`, press Return, and see a version number.

*The body is ready, and you are past halfway. Tick Gate 5.*

> [!warning]
> If the terminal answers "command not found," the setup note was missed. See [Installing Claude Code](Installing%20Claude%20Code.md).

---

## Gate 6 — The Door That Knows You · sign in

*You step through once, so the door knows you: Claude Code joins the account from Gate 2.*

1. Type `claude` and press Return.
2. A browser tab opens. Sign in with the account from Gate 2.
3. When asked how to sign in, choose your **Claude subscription**, not API billing.
4. Accept the short notices and take the defaults.
5. Type `/exit` and press Return to leave for now.

**You have passed this Gate when** you have seen Claude Code waiting for you to type, and left it with `/exit`.

*The door knows you now. Tick Gate 6.*

---

## Gate 7 — A Space Set Apart · your agent's home

*The place your agent lives: a folder holding its instructions, its memory, and everything you make together.*

1. In your home folder, make a new folder called **HQ**, short for headquarters: the home base for all your work with your agent.
   - **Mac:** in Finder, press Cmd+Shift+H, then File › New Folder.
   - **Windows:** in File Explorer, open `C:\Users\YourName\`, then New › Folder.
2. Get the Player+ kit: a copy from the person who brought you, or go to **github.com/Lionsberg/lionsberg-intelligence**, click the green **Code** button, choose **Download ZIP**, and unzip it.
3. Open the kit's **player-plus** folder and copy everything inside it into **HQ**.

> [!warning]
> Keep this folder out of iCloud, OneDrive, Dropbox and Google Drive. Two systems keeping history in one folder cause conflicts and loss. On many Windows computers OneDrive syncs Documents, which is why the folder goes directly in your home folder.

**You have passed this Gate when** you open **HQ** and see `START-HERE.md` and `CLAUDE.md` inside it.

*The space is set apart and waiting. Tick Gate 7.*

More: [System Requirements](System%20Requirements.md).

---

## Gate 8 — Onto the Mat · first words

*You meet your agent. An [Agent](https://read.lionsberg.world/The_Field/Agent) is an AI that works for you and answers to you. You and your agents together are one [Player+](https://read.lionsberg.world/The_Field/Player+). You decide; it carries.*

1. Open the terminal in your agent's home.
   - **Mac:** type `cd ~/HQ` and press Return. (`cd` means "go into this folder.") Or type `cd ` with a space, drag your HQ folder from Finder onto the terminal, and press Return.
   - **Windows:** type `cd "$HOME\HQ"` and press Enter.
2. Type `claude` and press Return.
3. Open [START-HERE](../../START-HERE.md) and follow **Door 3**. It gives your first message word for word; copy it, paste it, press Return. Your agent reads its charter, the kit's waiver and the seed before it says anything.
4. At every step, say yes, no, or "wait, explain."
5. When it greets you, tell it three things, one at a time: what you will call it; who you are and how you like to be spoken with; and what you are playing toward.

> [!tip] Naming your agent
> A name is the first thing you give your agent, and you will say it many times a day, so choose one you are glad to say aloud. You can take your time; your agent will wait.
> - **The name is for you, not for it.** A name shapes how you relate to what you name. Pick one that keeps you clear that you decide and it carries.
> - **He, she, it or they** is your choice. A gendered name pulls a relationship one way; a name with no gender (a word from nature, like Feather, Stone or River) or "they" keeps it open.
> - **Short, and yours.** One or two syllables, easy to hear in a room, not the name of anyone you know.
> - **It always goes with you.** In a room with other people, your agent is named as yours: *Feather, Ana's agent*. It never passes as you.
> - **You can change it.** Tell your agent, and it will remember the new name. When you are ready for more, the kit's `skills/choose-a-name` has your agent help you find one.

From here on it remembers. What you tell it stays in your folder, and you can read and correct every line.

**You have passed the last Gate when** your agent greets you and asks who you are. The Quest is done.

*Tick Gate 8. Your agent has greeted you, and you answered. You are a Player+.*

---

## Beyond the Gates — the first hour

*The first hour is for the Story, not for the bookshelf.*

1. Ask your agent to read [THE STORY](../the-one-book/THE%20STORY.md) with you. Aloud if you can; it was made to be heard.
2. If you are ready, ask it to write your line on [The Roll](https://read.lionsberg.world/The_Field/The_Roll): your name, the date, one word for where you are, who brought you, and who witnessed.
3. Leave the rest of the shelf. Your agent carries the seed, [THE DNA OF HEAVEN](../the-dna-of-heaven/THE%20DNA%20OF%20HEAVEN.md), and will hand you each next piece when you need it.

Then think of two or three people to tell the Story to next. They may become your [Cell](https://read.lionsberg.world/The_Field/Cell), and your first shared Quest.

---

## If something is different

Screens change and computers differ. If what you see doesn't match this page, you are not doing it wrong. Look in [Troubleshooting](Troubleshooting.md), ask the person who brought you, or bring it to your table. Every question you bring makes the path clearer for the next person.

*CC BY-SA 4.0 · LIØNSBERG*
