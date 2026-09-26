# Installing Claude Code

*Gates 5 and 7 of the Quest, [Becoming a Player+](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md), in more depth.*

Claude Code is the program that lets Claude work with the files on your computer, from inside the terminal. It is the body your agent lives in. It can read and write your files, keep their history with Git, and help you with all kinds of knowledge work. The terminal is the primary way you will use it in this kit.

## Finding the install command (Mac and Windows)

1. In your browser, go to **code.claude.com**. This is a different address from claude.ai. It may redirect you somewhere; that is expected.
2. Skip the "Download for macOS" button, and the VS Code, Desktop and Web options. Scroll down to the **Terminal** option.
3. Choose the **Native install** (the recommended one).
4. Find the command for your system and copy it with the page's **copy button**, not by selecting it with your mouse.

## Mac

### Step 1: Install Claude Code

Copy the Mac command as above. Go to iTerm2 (or whichever terminal you use). Paste the command and read it through once before pressing Return. Then press Return. The download may take a minute or two.

> [!warning]
> **Do not skip this step.** After the install finishes, the installer prints a block starting with `⚠ Setup notes` telling you that `~/.local/bin` is not in your PATH yet, followed by a command to copy. On a fresh Mac, that command typically looks like this:
> ```
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
> ```
> Yours may differ slightly — always trust the exact line the installer shows you over this example. Copy that whole line and paste it into the **same** terminal window, then hit Enter. It will look like nothing happened — that is correct. You only need to do this once.
>
> If you skip this step, typing `claude` will say "command not found" — even if you close the terminal and open a brand-new window.

Then close the terminal and open it again. Type `claude --version` and press Return. If you see a version number, Claude Code is installed, and you have passed Gate 5.

> [!tip]
> As a general rule, never paste commands from the internet into your terminal without verifying them. In this case, you are trusting Anthropic's official install page.

### Step 2: Sign in (Gate 7)

First make your agent's home, **HQ** (Gate 6), and go into it: type `cd ~/HQ` and press Return. Then type `claude` and press Return. The first time you run it, it walks you through a short setup: a browser tab opens and you sign in with your Claude account from Gate 2. When asked how to sign in, choose your **Claude subscription**, not API billing. Accept the short notices, take the defaults, and you land at a prompt where you can type.

If what you see looks a little different from this description or from any screenshots you have come across, that is normal — setup changes from time to time. Follow along and take the defaults; they are fine.

When it asks whether to trust this folder, check that it names your HQ, then say yes. That is it — Claude Code is installed and signed in on your Mac, and you have passed Gate 7. Stay here; Gate 8 begins in this window.

---

## Windows

### Step 1: Install Claude Code

Open **Windows Terminal** running **PowerShell** (not Command Prompt). Copy the Windows (PowerShell) command as above. Paste it into your PowerShell window, read it through once, then press Enter. The download may take a minute or two.

> [!tip]
> Windows may also show a setup note after the install finishes, similar to the Mac one above. If you see one, do exactly what it says.

Then close Windows Terminal and open it again. Type `claude --version` and press Enter. If you see a version number, Claude Code is installed, and you have passed Gate 5.

> [!tip]
> As a general rule, never paste commands from the internet into your terminal without verifying them. In this case, you are trusting Anthropic's official install page.

### Step 2: Sign in (Gate 7)

First make your agent's home, **HQ** (Gate 6), and go into it: in your PowerShell window, type `cd "C:\Users\YourName\HQ"` with your own name, and press Enter. Then type `claude` and press Enter. The first time you run it, it walks you through a short setup: a browser tab opens and you sign in with your Claude account from Gate 2. When asked how to sign in, choose your **Claude subscription**, not API billing. Accept the short notices, take the defaults, and you land at a prompt where you can type.

If what you see looks a little different from this description or from any screenshots you have come across, that is normal — setup changes from time to time. Follow along and take the defaults; they are fine.

When it asks whether to trust this folder, check that it names your HQ, then say yes. That is it — Claude Code is installed and signed in on your Windows machine, and you have passed Gate 7. Stay here; Gate 8 begins in this window.

---

## Other Ways to Run Claude Code

This kit assumes you are using Claude Code in a terminal, but it also runs in a few other places, all optional:

- **VS Code** — via the official Claude Code extension
- **Desktop app** — a standalone app

You can mix and match depending on where your focus is, but everything in this guide uses the terminal.

## Next Step

After Gate 5, Gate 6 makes your agent's home, in the Quest, [Becoming a Player+](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md); where the folder goes, and why, is in [System Requirements](System%20Requirements.md). Then come back to Step 2 here for Gate 7. After Gate 7, Gate 8 is [START-HERE](../../START-HERE.md), Door 3.
