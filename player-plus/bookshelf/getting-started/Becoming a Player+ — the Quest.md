# Becoming a Player+

*The one path from your first yes to an agent of your own, walked as a Quest of eight Gates.*

The terminal is the wizard's interface to your computer. By the last Gate you will have one open, and an agent of your own waiting inside it.

A [[Quest]] is one real thing, done together, that you can point to afterward. This page is one, and here is its card, [[The Questcard]]:

| | |
|---|---|
| **Our Quest** | Becoming a Player+ |
| **Why** | The plus adds reach. Every decision stays with you. |
| **Real** | An agent that is yours, living in a folder on your own computer. |
| **Near** | An afternoon. |
| **Yours** | You chose it. |
| **Done when** | Your agent greets you and asks who you are. |

In the Game, a Quest usually belongs to a Cell, for a season. This is the one a person walks alone first, so you learn the form before your table chooses its first shared one. The lesson behind it is [Becoming a Player+](../player-plus-modules/01%20Becoming%20a%20Player%2B.md).

Like every gate in [[The Gates of LIØNSBERG]], each of these is a gate and not a filter. Nothing is withheld from you, and nothing closes behind you. You may stop between any two Gates and pick up where you left off. You do not walk it alone: when something breaks or looks strange, ask the person who brought you, or bring it to your table.

---

## Gate 1 — The yes

*The Game comes before the agent. A [[Player]] is a person who has said yes to the Game in their own words.*

1. Read [THE STORY](../the-one-book/THE%20STORY.md). It takes about ten minutes. It is not a belief you are asked to hold; it is a shared language.
2. Read [The Provisional Field of Agreements](../the-library/The%20Provisional%20Field%20of%20Agreements.md), slowly, all the way through. It is the [[Field of Agreements]]: the terms everyone plays by.
3. Take part only if you agree. If you don't, you may still read everything, and come back whenever you are ready.

**You have passed this Gate when** you can say, in your own words, what you are agreeing to, and you say yes freely.

> [!tip]
> With a notebook and two or three people, you are already a complete player. Everything from here on adds reach, never permission. If that is where you are, [START-HERE](../../START-HERE.md), Door 1, is your path.

---

## Gate 2 — The account

*Your agent thinks with Claude, an AI made by Anthropic. You need a paid account to use it.*

1. In your browser, type **claude.ai** yourself. Don't follow a search result or an ad; there are many look-alike sites.
2. Create an account with your email.
3. Choose the **Pro** plan. It includes everything this path needs. (Max works too.)

Don't install the Claude desktop app or phone app yet. You won't need them here.

**You have passed this Gate when** you are signed in at claude.ai and your account shows the Pro plan.

More: [Getting a Claude Account](Getting%20a%20Claude%20Account.md).

---

## Gate 3 — The terminal

*A terminal is a window where you type instructions to your computer and it types back. Each instruction is called a command.*

**Mac**

1. Go to **iterm2.com** and download iTerm2.
2. Open the downloaded file to unzip it, and move iTerm2 into your **Applications** folder. If it offers to move itself there, say yes.
3. Open it: press Cmd+Space, type **iTerm**, press Return.

**Windows**

1. Open the Start menu, type **Terminal**, and press Enter. This is Windows Terminal. (On Windows 10, install it free from the Microsoft Store first.) Never get it from a website.
2. Make sure the tab says **PowerShell**. If not, click the small down-arrow beside the `+` and choose **Windows PowerShell**. Don't use Command Prompt, and don't use Git Bash.
3. Switch to dark colours, as [Choosing Your Terminal](Choosing%20Your%20Terminal.md) shows. Without this, some of your agent's words can be invisible.

**You have passed this Gate when** the window is open and a cursor blinks, waiting for you.

> [!warning]
> The terminal is a workshop full of power tools. Type in it as much as you like, but never press Return on a command you don't understand. Every command on this page is explained before you use it.
>
> If a pop-up asks to let the terminal "find devices on your local network," choose **Don't Allow**.

---

## Gate 4 — The developer tools and Git

*Git keeps a quiet, safe history of every file you and your agent make. Your agent handles it for you; it only needs to be installed.*

**Mac**

1. In the terminal, type `git --version` and press Return. This asks your computer which Git it has.
2. If a window offers to install the **Command Line Developer Tools**, click **Install**, then **Agree**. If no window appears and you see an error instead, type `xcode-select --install` and press Return; the window will come.
3. Wait. It can take five to forty minutes, and the first time estimate is often wildly wrong.

**Windows**

1. In your browser, go to **git-scm.com** and download Git for Windows.
2. Run the installer and accept every default.
3. Close the terminal and open it again, so it notices the new tool.

**You have passed this Gate when** `git --version` answers with a version number, such as `git version 2.39.3`.

> [!tip]
> On a Mac, the install window often opens *behind* your other windows. If nothing seems to happen, look behind them.

More: [Installing Git](Installing%20Git.md).

---

## Gate 5 — Claude Code

*Claude Code is the program that lets Claude work with the files on your computer, from inside the terminal. It is the body your agent lives in.*

1. In your browser, go to **code.claude.com**. This is a different address from claude.ai.
2. Skip the "Download for macOS" button. Scroll down to the **Terminal** option.
3. Choose the **Native install** (the recommended one).
4. Find the command for your system and copy it with the page's **copy button**, not by selecting it with your mouse.
5. Paste it into the terminal. Read it through once. Then press Return, and wait a minute or two.
6. If the installer prints a setup note when it finishes, do exactly what it says. On a Mac it usually gives you one more line to copy; paste it into the same window and press Return. It will look as if nothing happened, and that is correct.
7. Close the terminal and open it again.

**You have passed this Gate when** you type `claude --version`, press Return, and see a version number.

> [!warning]
> If the terminal answers "command not found," the setup note was missed. See [Installing Claude Code](Installing%20Claude%20Code.md).

---

## Gate 6 — Sign in

1. Type `claude` and press Return.
2. A browser tab opens. Sign in with the account from Gate 2.
3. When asked how to sign in, choose your **Claude subscription**, not API billing.
4. Accept the short notices and take the defaults.
5. Type `/exit` and press Return to leave for now.

**You have passed this Gate when** you have seen Claude Code waiting for you to type, and left it with `/exit`.

---

## Gate 7 — Your agent's home

*Your agent lives in a folder on your computer: its instructions, its memory, and everything you make together.*

1. In your home folder, make a new folder called **My Agents**.
   - **Mac:** in Finder, press Cmd+Shift+H, then File › New Folder.
   - **Windows:** in File Explorer, open `C:\Users\YourName\`, then New › Folder.
2. Get the Player+ kit. If the person who brought you gave you a copy, use it. Otherwise go to **github.com/Lionsberg/lionsberg-intelligence**, click the green **Code** button, choose **Download ZIP**, and unzip it.
3. Open the kit's **player-plus** folder and copy everything inside it into **My Agents**.

> [!warning]
> Keep this folder out of iCloud, OneDrive, Dropbox and Google Drive. Two systems keeping history in one folder cause conflicts and loss. On many Windows computers, Documents is synced by OneDrive, which is why the folder goes directly in your home folder.

**You have passed this Gate when** you open **My Agents** and see `START-HERE.md` and `CLAUDE.md` inside it.

More: [System Requirements](System%20Requirements.md).

---

## Gate 8 — First words

*An [[Agent]] is an AI that works for you and answers to you. You and your agents together are one [[Player+]]. You decide; it carries.*

1. Open the terminal in your agent's home.
   - **Mac:** type `cd ~/"My Agents"` and press Return. (`cd` means "go into this folder.")
   - **Windows:** type `cd "$HOME\My Agents"` and press Enter.
2. Type `claude` and press Return.
3. Open [START-HERE](../../START-HERE.md) and follow **Door 3**. It gives you your first message, word for word; copy it, paste it, press Return. Your agent reads its charter, the kit's waiver and the seed before it says anything.
4. At every step, say yes, no, or "wait, explain."
5. When it greets you and asks about you, tell it three things, one at a time: what you will call it; who you are and how you like to be spoken with; and what you are playing toward.

From here on it remembers. What you tell it stays in your folder, and you can read and correct every line.

**You have passed the last Gate when** your agent greets you and asks who you are. The Quest is done.

---

## Beyond the Gates — the first hour

*The first hour is for the Story, not for the bookshelf.*

1. Ask your agent to read [THE STORY](../the-one-book/THE%20STORY.md) with you. Aloud, if you can; it was made to be heard.
2. If you are ready, ask it to write your line on [[The Roll]]: your name, the date, one word for where you are, who brought you, and who witnessed.
3. Leave the rest of the shelf on the shelf. Your agent carries the seed, [THE DNA OF HEAVEN](../the-dna-of-heaven/THE%20DNA%20OF%20HEAVEN.md), and will hand you each next piece when you need it.

Then think of two or three people you would tell the Story to next. They may become your [[Cell]], and your first shared Quest.

---

## If something is different

Screens change, and computers differ. If what you see doesn't match this page, you are not doing it wrong. Look in [Troubleshooting](Troubleshooting.md), ask the person who brought you, or bring it to your table. Every question you bring makes the path clearer for the next person.

*CC BY-SA 4.0 · LIØNSBERG*
