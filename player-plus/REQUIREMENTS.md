# What you need

Requirements and strong recommendations, in plain terms. If the "basics" lists feel comfortable, you are ready. The Quest, [Becoming a Player+](<bookshelf/getting-started/Becoming a Player+ — the Quest.md>), walks you through getting everything else, one Gate at a time.

## Computer basics

- A basic understanding of files and folders on your Windows or Mac computer: you can use File Explorer or Finder to move, copy, and delete files between folders, and you can download a zip file and find the files within it.
- You can copy and paste to and from the clipboard, between apps.

## Strongly recommended (please, really)

- **Backups.** Data on your computer is regularly backed up — in case of a lost or stolen computer, a virus, phishing, or an AI accident. And you have *tested restoring* from a backup: an untested backup is a hope, not a backup. (Mac: Time Machine plus any reputable cloud backup service. Windows: File History plus a cloud backup service.)
- **Secrets.** Passwords, keys, and other secret data live in a password manager or another purpose-built encryption tool — not in plain files, and never in the folders your agent works in.

## Claude account

A **Claude Pro** plan from Anthropic, which includes everything this path needs (Max works too). Claude Code, the tool your agent runs on, comes with it. Sign up at claude.ai, typed into your browser yourself. One person, one account: the terms of service say so, and a shared account also means a shared view of everyone's sessions.

## Computer intermediate

- You can use a **terminal** — a simple, chat-like program on your computer. If you never have, that is genuinely fine: it is less scary than it looks, and the Quest teaches it from zero.

## Git: required

Git keeps quiet, safe snapshots of everything you and your agent make, so nothing can ever be lost. You do not need to learn it; your agent handles it. It only needs to be installed, which the Quest does at Gate 4 (on a Mac, with Apple's developer tools, which can take five to forty minutes).

**One rule: keep your agent's home out of cloud-sync folders** — iCloud, OneDrive, Dropbox, Google Drive. Git and sync engines contend with each other and both lose. Your agent's home is a folder called **HQ**, directly in your home folder. On many Windows computers Documents is synced by OneDrive, which is why the folder does not go there. Keep your headquarters, where your projects live, out of sync folders too; your agent will check this with you.

## The two surfaces

You will work with your agent through two surfaces: a **chat surface** (where you talk) and a **review surface** (where you read and edit the markdown documents you make together).

### Chat surfaces

- **A terminal** — the recommended path, and the one the Quest sets up. Mac: **iTerm2** (free and open source; the built-in Terminal works too). Windows: **PowerShell** in **Windows Terminal**.
- **The Claude app on your phone**, through **Remote Control** (`/rc`) — the same session, continued from your phone. If you will reach your agent mostly from a phone, tell it so at the start: there is a chapter and a skill for that path (`bookshelf/your-house/The Phone Path.md`, `skills/phone-path`).
- *Other option, not recommended:* Claude Desktop (or Web/Mobile — all the same) natively. The problem is getting files in and out, via clunky git branches.
- *Other option:* skip Claude Code and use Claude Cowork. We think that is harder.

### Review surfaces

- **Typora** — https://typora.io — our current favorite. Inexpensive, one-time purchase.
- **MarkText** — https://marktext.me — free and open source, same live-preview style.
- **MeetingWords** — https://meetingwords.com — a shared pad made for people and agents working on the same document; also the surface for working with other houses. *(Disclosure: Peter Kaminski, author of the starter kit, runs MeetingWords. It is recommended because it is the best current understanding of what works, not as self-dealing. The kit uses the hosted service at meetingwords.com.)*
- **If you already use Obsidian or VS Code**, they are fine — keep them. The kit does not teach Obsidian, which is not the same as forbidding it.

The full treatment is `bookshelf/getting-started/Viewing Your Files.md`.

## Where to get help

When something breaks or looks strange, ask the person who brought you, or bring it to your table. The troubleshooting page, `bookshelf/getting-started/Troubleshooting.md`, covers the common snags.

Free and paid **PKAI workshops**, from the author of the starter kit, teach beyond this kit — and are a way to get set up with company rather than alone. Sign up for email updates at **https://peterkaminski.ai** to hear about workshops and new starter-kit releases.
