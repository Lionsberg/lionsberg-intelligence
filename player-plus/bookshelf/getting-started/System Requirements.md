# System Requirements

Here's what you need before you begin the Quest, [Becoming a Player+](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md), and where your agent's home goes at Gate 7.

## Your Computer

**Mac** — macOS 10.15 (Catalina) or later. Most Macs from 2015 onward will work fine.

**Windows** — Windows 10 or later. You'll use PowerShell running in Windows Terminal — see [Choosing Your Terminal](Choosing%20Your%20Terminal.md).

> [!tip]
> Linux works too, but this guide focuses on Mac and Windows since those are what most people use.

## Accounts You'll Create

- **A Claude account on the Pro plan** (Max works too) — sign up at claude.ai, typed into your browser yourself. Claude Code comes with it; [Getting a Claude Account](Getting%20a%20Claude%20Account.md) has more detail.
- **GitHub** — optional, and not needed to get started. It's free, and it's where your files can be backed up to the cloud later if you want that; the optional Git and GitHub section of this book covers it.

## Software You'll Install

- **A terminal** — iTerm2 on a Mac, Windows Terminal with PowerShell on Windows; both free. See [Choosing Your Terminal](Choosing%20Your%20Terminal.md).
- **Git** — free, and required; a Mac gets it with Apple's Command Line Developer Tools, Windows through Git for Windows. See [Installing Git](Installing%20Git.md).
- **Claude Code** — included with your plan; install instructions at code.claude.com, and in [Installing Claude Code](Installing%20Claude%20Code.md).
- **A Markdown editor**, later, when you want one — Typora ($15 one-time), MarkText (free), or [MeetingWords](https://meetingwords.com/); if you already use Obsidian or VS Code, they're fine too. See [Viewing Your Files](Viewing%20Your%20Files.md).

## Internet Connection

You need internet for setup, and whenever you're talking to your agent — Claude Code works over the internet. Your files themselves live on your own computer, though: you can read and edit them offline with your Markdown editor any time.

## Time

Allow an afternoon for the whole Quest; you may stop between any two Gates. On a Mac, the developer tools that bring Git can take five to forty minutes on their own.

## Important: Cloud Sync Folders

Your agent's folder must **not** be inside iCloud, OneDrive, Dropbox, or any other cloud-synced folder. Your agent keeps its own version history with git, and having two sync systems watching the same folder causes conflicts and data loss.

Your agent's home is a folder called **My Agents**, directly in your home folder:

- **Mac:** `~/My Agents/`
- **Windows:** `C:\Users\YourName\My Agents\`

> [!warning]
> On many Windows machines, OneDrive syncs your Documents folder by default — which is exactly why the folder goes directly in `C:\Users\YourName\`, not under Documents.

Your headquarters, where your projects and working files live, follows the same rule: keep it out of any cloud-synced folder. Your agent will ask where you keep your work at its first waking, and check this with you.
