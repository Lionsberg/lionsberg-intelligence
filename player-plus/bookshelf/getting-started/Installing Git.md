# Installing Git

*Gate 4 of the Quest, [Becoming a Player+](Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md), in more depth.*

Git keeps a quiet, safe history of every file you and your agent make. It is required, and it only needs to be installed: your agent handles it for you from then on, and you never need to learn it.

The installation is different on Mac and Windows. Follow the section for your platform.

---

## Mac

On a Mac, Git comes with Apple's **Command Line Developer Tools**. They also bring other developer tools that Claude Code needs.

### Step 1: Ask your Mac which Git it has

In your terminal (iTerm2, from Gate 3), type this and press Return:

```
git --version
```

If you see a version number (like `git version 2.39.3`), Git is already installed. Skip to Step 3.

### Step 2: Install the Command Line Developer Tools

If a window offers to install the **Command Line Developer Tools**, click **Install**, then **Agree** to the license agreement.

If no window appears and you see an error instead, type this and press Return; the window will come:

```
xcode-select --install
```

> [!warning]
> This window often appears **behind** other windows and is easy to miss. If nothing seems to happen, check behind your open windows or look at your other displays.

> [!tip]
> Wait. It can take five to forty minutes, and the first time estimate is often wildly wrong: it may say 16 hours. The progress bar may also restart about two-thirds of the way through. This is normal.

### Step 3: Verify Git is installed

When the tools finish installing, type this and press Return:

```
git --version
```

You should see a version number (like `git version 2.39.3`). If you do, Git is ready, and you have passed Gate 4.

### Step 4 (Optional, not needed for the Quest): Install Homebrew and the GitHub CLI

Homebrew is a tool that makes it easy to install other tools on Mac. The GitHub CLI (`gh`) makes connecting to GitHub smoother.

To install Homebrew, paste this into Terminal as one single line:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It will ask for your Mac password — type it in (no characters will show as you type) and press Enter. Wait for it to finish.

Then install the GitHub CLI:

```
brew install gh
```

This is optional. It makes connecting to GitHub simpler, if you ever want that (see [GitHub Account Setup](GitHub%20Account%20Setup.md)).

---

## Windows

On Windows, you install Git for Windows. Its installer also bundles Git Bash, but that's just along for the ride — Claude Code itself runs in **PowerShell inside Windows Terminal**, not Git Bash.

### Step 1: Download Git for Windows

In your browser, go to **git-scm.com** and download Git for Windows.

### Step 2: Run the installer

Run the downloaded installer. **Accept the default options all the way through** — the defaults are fine.

### Step 3: Close the terminal and open it again

Close Windows Terminal and open it again, so it notices the new tool.

### Step 4: Verify the installation

Make sure you're on a **PowerShell** tab, and type:

```
git --version
```

You should see a version number (like `git version 2.39.3`). If Git isn't found, open a fresh PowerShell tab and try once more; if it still isn't found, the installer didn't finish — download and run it again.

> [!tip]
> Windows Terminal can host several kinds of tabs — PowerShell, Command Prompt, and the Git Bash that came along with the Git for Windows install. Use the **PowerShell** tab for everything in this guide, including running Claude Code.

---

## Next Step

Gate 5: [Installing Claude Code](Installing%20Claude%20Code.md). GitHub is optional, and can wait; [GitHub Account Setup](GitHub%20Account%20Setup.md) covers it when you want it.
