# Becoming a Player+ — the Quest for Mac

*The one path from your first yes to an agent of your own, walked as a Quest of eight Gates, on a Mac.*

The Questcard, and why these are gates and not filters, are on [Becoming a Player+ — the Quest](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md). On Windows? Walk [the Quest for Windows](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest%20for%20Windows.md).

When something looks strange, ask your table. If it helps them see, share one window, never the whole screen.

**Your map.** Pioneers find some creeks already crossed. So will you. Each Gate ends with how you know you have passed it; if that is already true, tick it and walk on.

- [ ] Gate 1 — The Golden Seed · the yes
- [ ] Gate 2 — The Lamp · the account
- [ ] Gate 3 — The Wizard's Window · the terminal
- [ ] Gate 4 — The Living Record · the developer tools and Git
- [ ] Gate 5 — The Body · Claude Code
- [ ] Gate 6 — A Space Set Apart · your agent's home
- [ ] Gate 7 — The Door That Knows You · sign in
- [ ] Gate 8 — Onto the Mat · first words

---

## Gate 1 — The Golden Seed · the yes

*Everything grows from this. The Game comes before the agent. A [Player](https://read.lionsberg.world/The_Field/Player) is one who has said yes to the Game in their own words.*

1. Read [THE STORY](../the-one-book/THE%20STORY.md). About ten minutes. Not a belief to hold; a shared language.
2. Read [The Provisional Field of Agreements](../the-library/The%20Provisional%20Field%20of%20Agreements.md), slowly, all the way through. It is the [Field of Agreements](https://read.lionsberg.world/The_Field/Field_of_Agreements): the terms everyone plays by.
3. Take part only if you agree. If you don't, you may still read everything, and come back when ready.

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

*Where you speak to your computer directly. A terminal is a window where you type instructions to your computer and it types back. Each instruction is called a command.*

1. Go to **iterm2.com** and download iTerm2.
2. Open the download to unzip it. If iTerm2 offers to move itself to **Applications**, say yes; otherwise drag it there yourself.
3. Open it: press Cmd+Space, type **iTerm**, press Return.
4. If it asks to "find devices on your local network," choose **Don't Allow**.

**You have passed this Gate when** the window is open and a cursor blinks, waiting for you.

*The window is open and listening. Tick Gate 3.*

> [!warning]
> The terminal is a workshop full of power tools. Type freely, but never press Return on a command you don't understand. Every command here is explained before you use it.

> [!tip] Two keys that look alike
> **Cmd+C** copies. **Ctrl+C** stops whatever the terminal is running. Reach for Ctrl+C only when you mean to stop something.

More: [Choosing Your Terminal](Choosing%20Your%20Terminal.md).

---

## Gate 4 — The Living Record · the developer tools and Git

*Your work gains a memory. Git keeps a quiet, safe history of every file you and your agent make. Your agent handles it; it only needs installing. On a Mac it comes with Apple's developer tools.*

1. In iTerm, type `git --version` and press Return. It asks which Git you have.
2. If a window offers to install the **command line developer tools**, click **Install**, then **Agree**. If you see an error instead, type `xcode-select --install` and press Return; the window will come.
3. Wait. It can take five to forty minutes; the first estimate is often wildly wrong. It can look idle; don't stop it.

This window may appear on its own earlier, whenever something asks for a developer tool. Say **Install** and let it run.

**You have passed this Gate when** `git --version` answers with a version number, such as `git version 2.39.3`.

*What you make together now keeps its history. Tick Gate 4.*

> [!tip] When the screen stops answering
> The install window often opens *behind* your other windows, and a waiting window can make everything else ignore your clicks. Press **Esc**. Press **Cmd+Tab** to find a hidden dialog. Swipe up with three fingers to see every open window at once.

More: [Installing Git](Installing%20Git.md).

---

## Gate 5 — The Body · Claude Code

*Your agent gets a body to live in. Claude Code is the program that lets Claude work with the files on your computer, from inside the terminal.*

1. In your browser, go to **code.claude.com** (a different address from claude.ai).
2. Skip the "Download for macOS" button. Scroll down to the **Terminal** option.
3. Choose the **Native install** (the recommended one).
4. Copy the command with the page's **copy button**, not by selecting it with your mouse.
5. Paste it into iTerm. Press Return, and wait. For a minute or two it may look idle; it is working. Don't stop it.
6. When it says **Installation complete**, read on before you do anything else. This is the crossing most people miss.

**The setup note.** Under "Installation complete" the installer prints a setup note. In it is one light-grey line that begins with `echo` and ends with `&& source ~/.zshrc`. It usually reads:

```
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

7. Copy that whole line from your own screen (or type it exactly, every mark), paste it into iTerm, and press Return. It will look as if nothing happened; that is correct.
8. Close iTerm completely (Cmd+Q) and open it again.

**You have passed this Gate when** you type `claude --version`, press Return, and see a version number.

*The body is ready, and you are past halfway. Tick Gate 5.*

> [!warning]
> If iTerm answers "command not found," the setup note was missed. Go back to step 7, then close and reopen iTerm. More: [Installing Claude Code](Installing%20Claude%20Code.md).

---

## Gate 6 — A Space Set Apart · your agent's home

*The place your agent lives: a folder holding its instructions, its memory, and everything you make together.*

1. In Finder, press Cmd+Shift+H to open your home folder, then choose File › New Folder. Name it **HQ**, short for headquarters: the home base for all your work with your agent.
2. Get the Player+ kit: a copy from the person who brought you, or go to **github.com/Lionsberg/lionsberg-intelligence**, click the green **Code** button, choose **Download ZIP**, and unzip it.
3. Open the kit's **player-plus** folder and copy everything inside it into **HQ**.

> [!warning]
> HQ lives in your home folder, never inside iCloud, OneDrive, Dropbox or Google Drive. Desktop and Documents often sync to iCloud; your home folder does not.

**You have passed this Gate when** you open **HQ** and see `START-HERE.md` and `CLAUDE.md` inside it.

*The space is set apart and waiting. Tick Gate 6.*

More: [System Requirements](System%20Requirements.md).

---

## Gate 7 — The Door That Knows You · sign in

*You step through once, so the door knows you: Claude Code joins the account from Gate 2, inside your agent's home.*

1. Go into your agent's home. In iTerm, type `cd` followed by a space. (`cd` means "go into this folder.") Then drag your **HQ** folder from Finder onto the iTerm window itself, not the desktop, and press Return. Or type `cd ~/HQ` and press Return.
2. Type `claude` and press Return.
3. Choose a colour theme. Pick the one you can read most easily.
4. When asked how to sign in, choose option **1**, your **Claude subscription**.
5. A browser opens. Sign in with the same account as Gate 2, the same way you made it (Google or Apple, if that is how). If it sends you an email, look in spam, or on your phone. Use the same email you paid with. If the browser that opens is not the one you use for Claude, go back to the terminal, press **c** to copy the sign-in link, and paste it into the browser where you are signed in.
6. When the browser says **You're all set up**, return to iTerm and press Return.
7. When it asks whether to trust this folder, first check that **Accessing workspace:** names your HQ. Then choose **Yes, I trust this folder**. Stay here; the next Gate begins in this window.

**You have passed this Gate when** Claude Code is open in your HQ, waiting for you to type.

*The door knows you now. Tick Gate 7.*

---

## Gate 8 — Onto the Mat · first words

*You meet your agent. An [Agent](https://read.lionsberg.world/The_Field/Agent) is an AI that works for you and answers to you. You and your agents together are one [Player+](https://read.lionsberg.world/The_Field/Player+). You decide; it carries.*

1. Open [START-HERE](../../START-HERE.md) and follow **Door 3**. It gives your first message word for word; copy it, paste it into Claude Code right where you are, and press Return. Your agent reads its charter, the kit's waiver and the seed before it says anything.
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

Then think of two or three people to tell the Story to next. They may become your [Cell](https://read.lionsberg.world/The_Field/Cell), and your first shared Quest.

---

## If something is different

Screens change. If what you see doesn't match this page, you are not doing it wrong. Look in [Troubleshooting](Troubleshooting.md), or bring it to your table; every question makes the path clearer for the next person.

*CC BY-SA 4.0 · LIØNSBERG*
