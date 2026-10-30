# System Requirements

Here is what you need before you begin the Quest, [Becoming a Player+](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md), and where your agent's home goes at Gate 4.

## Your Computer

**Mac** — macOS 13 (Ventura) or later.

**Windows** — Windows 10 or later. The Claude app runs on x64 and Arm computers. By the terminal way, you use PowerShell in Windows Terminal — see [Choosing Your Terminal](Choosing%20Your%20Terminal.md).

> [!tip]
> Linux works too, but this guide focuses on Mac and Windows since those are what most people use.

## Accounts You will Create

- **A Claude account on the Pro plan** (Max, Team and Enterprise work too; the free plan does not include Claude Code) — sign up at claude.ai, typed into your browser yourself. Claude Code comes with it; [Getting a Claude Account](Getting%20a%20Claude%20Account.md) has more detail.
- **GitHub** — optional, and not needed to get started. It is free, and it is where your files can be backed up to the cloud later if you want that; the optional Git and GitHub section of this book covers it.

## Software You will Install

- **The Claude app** — free to download at claude.ai/download; it carries Claude Code inside its Code tab. Only by the terminal way: a terminal, iTerm2 or Terminal on a Mac, Windows Terminal with PowerShell on Windows. See [Choosing Your Terminal](Choosing%20Your%20Terminal.md).
- **Git** — free; your agent uses it to keep a history of your work, and Claude installs it with you at Gate 4. A Mac gets it with Apple's Command Line Developer Tools, Windows through Git for Windows. See [Installing Git](Installing%20Git.md).
- **Claude Code** — included with your plan, and inside the Claude app; only the terminal way installs it on its own, as in [Installing Claude Code](Installing%20Claude%20Code.md).
- **A Markdown editor**, later, when you want one — Typora ($15 one-time), MarkText (free), or [MeetingWords](https://meetingwords.com/); if you already use Obsidian or VS Code, they are fine too. See [Viewing Your Files](Viewing%20Your%20Files.md).

## Internet Connection

You need internet for setup, and whenever you are talking to your agent — Claude Code works over the internet. Your files themselves live on your own computer, though: you can read and edit them offline with your Markdown editor any time.

## Time

Allow an hour or two for the whole Quest; you may stop between any two Gates. On a Mac, the developer tools that bring Git can take five to forty minutes on their own.

## Important: Cloud Sync Folders

Your agent's folder must **not** be inside iCloud, OneDrive, Dropbox, or any other cloud-synced folder. Your agent keeps its own version history with git, and having two sync systems watching the same folder causes conflicts and data loss.

Your agent's home is a folder called **HQ**, directly in your home folder:

- **Mac:** `~/HQ/`
- **Windows:** `C:\Users\YourName\HQ\`

> [!warning]
> On many Windows machines, OneDrive syncs your Documents folder by default — which is exactly why the folder goes directly in `C:\Users\YourName\`, not under Documents.

Your headquarters, where your projects and working files live, follows the same rule: keep it out of any cloud-synced folder. Your agent will ask where you keep your work at its first waking, and check this with you.
