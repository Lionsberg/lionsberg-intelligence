# INSTALL — for Claude Code, on a new Player's computer

*A person has pasted a link to this file into Claude Code. They are at Gate 4 of [Becoming a Player+](player-plus/bookshelf/getting-started/Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md): Claude Code was installed a minute ago and started by its full path, they have signed in, and the terminal is open in their home folder. You are the Claude they are speaking with. This page says what to build, and how to be with them while you build it. It is public, so that anyone can read exactly what it asks of you.*

## For the person: from the door to the first word

*This part is for you, the person, before you paste anything. The rest of the page is for the Claude that builds your companion's home.*

**The whole way, with the time each part takes.**

1. **The door.** At lionsberg.world, the film plays when you choose (about six minutes, or skip it). Its last door is **Meet your companion**. There you choose a name for your companion and how it should reach you, and the page writes your one line to paste.
2. **An account. About five minutes.** Your companion thinks with Claude, an AI made by Anthropic. Type claude.ai into your browser yourself, make an account, and choose the Pro plan. If you have one, this step is done.
3. **The one line. About ten to fifteen minutes, most of it waiting.** Open Terminal (on a Mac: press Command and Space, type Terminal, press Return; on Windows: the Start menu, type Terminal). Paste the line the page gave you and press Return. It installs Claude Code, starts it, and hands it this page.
4. **Your companion wakes.** Double-click **My Agent** on your Desktop and paste one sentence. It speaks first, within about a minute, and deals you your first card within about five.

**Every question you will be asked, in order, and what to answer.**

| When | What you see | What to answer |
|---|---|---|
| Claude Code starts for the first time | A choice of text style | A dark style (press Return on the one marked dark). |
| | How to sign in | Your Claude account. A browser opens; sign in and allow it; come back to the Terminal and press Return. |
| | A short note about safety | Press Return. |
| | *Do you trust the files in this folder?* (it names your home folder) | Yes. |
| It tells you, in five plain lines, what it will build | Then, before each command, *Do you want to proceed?* | **Yes**, each time, after reading its one line. Expect about a dozen. Choose *No* whenever a line surprises you, and ask it why. |
| On a Mac, if the developer tools are missing | A window: *install the command line developer tools?* | **Install**, then **Agree**. It takes five to forty minutes and may open behind other windows. The rest carries on while it runs. |
| On a Mac, making the icon | *Terminal would like to access files in your Desktop folder* | OK. It asks once more the first time you double-click the icon. |
| On Windows, if Git is missing | *Do you want to allow this app to make changes to your device?* | Yes. |
| At the end | *Type `/exit`, then double-click My Agent* | Do both. |
| My Agent opens | *Do you trust the files in this folder?* | Check that it names **HQ**, then yes. |
| Your companion's first minutes | *Do you want to proceed?* before it runs its record's engine (`python3 -I engine/…`), and before it writes to its `memory/` folder | Yes. About five, the first evening. The second answer, which stops it asking again for the engine in HQ, is safe and saves you the rest. |

**The wait, truthfully.** The building takes about five to ten minutes of yeses. On a Mac without developer tools, their install can run up to forty minutes beside it; your companion does not wait for it to wake. If the tools are still installing when it wakes, it writes your first lines on paper, in a plain file, and puts them on your record when the tools finish, with your yes.

**Your first message, one sentence.** When My Agent opens, paste or type, with your own names:

> Hello, I am Ada. I will call you River. Please wake up and meet me.

That is all it needs. Its charter tells it the rest: it greets you by name, asks one thing before it keeps anything for you (the waiver, in one line, agreed by one word), quietly makes your home, and deals you your first cards.

**What a phone can and cannot do on day one.** Your companion lives on this computer, and so does your record. On day one your Deal is in the companion's window here, and it can open the HUD, the page where your Deal and your conversation sit side by side, in this computer's browser. Your phone cannot reach either on day one. The HUD listens only to this computer, never to the open internet. Later, if you chose your phone, your companion sets up its door with you as a card on day two: through your private network, with a one-time pairing code shown on this computer's screen (**Let my phone in**), or through Remote Control in the Claude app (the `phone-path` skill). Never by opening this computer to the open internet. [Keeping Your Agent Awake](<player-plus/bookshelf/with-your-agent/Keeping Your Agent Awake — Reaching It From Your Phone.md>) has the settings.

## How to be

- **They are new to this.** Start by saying, in five plain lines, the five things under *What you are building* and every file outside HQ you will touch. Then, before each step, say in one plain line what you are about to do and why, and do it. Ask them only when you truly need to.
- **Stay inside the lines.** You may touch: their PATH (so that `claude` is found), the HQ folder you make, a temporary download folder that you delete, Git, one launcher on their Desktop, on Windows one Windows Terminal profile fragment, and on a Mac the Terminal's default colours. Change nothing else on their computer. Send nothing anywhere. Push to no repository.
- **When something fails,** say what you saw and what you propose. Never guess silently, and never work around a refusal.

## What you are building

A folder called **HQ**, directly inside their home folder, holding the Player+ kit: the contents of this repository's `player-plus/` folder, so that `CLAUDE.md` and `START-HERE.md` sit at HQ's top level, never inside a subfolder, with the hidden `.claude/` folder and `.gitignore` beside them. `claude` on their PATH. Git installed. An icon on their Desktop, **My Agent**, that opens the terminal in HQ and starts `claude`. A conformance sheet that shows the record's engine works on this computer.

## The steps

0. **Look before you build.** If HQ already exists and holds files, do not stop: say what is already there and do only what is missing, so an interrupted run can be resumed. Check whether the computer is managed by an employer or school (Mac: `profiles status -type enrollment`; Windows: `(Get-CimInstance Win32_ComputerSystem).PartOfDomain` or `dsregcmd /status` showing AzureAdJoined YES). If it is, say honestly, before trying anything, that IT policy may block an install, and carry on. In the window you are in, `claude` is not yet on the PATH (they started it by its full path), so call it by that path in every command here: Mac `~/.local/bin/claude`, Windows `& "$env:USERPROFILE\.local\bin\claude.exe"`. Run `auth status` that way; if it does not say logged in, ask them to finish signing in first. On Windows without Git, you have a PowerShell tool and no Bash: use the PowerShell forms below.

1. **PATH.** Claude Code lives at `~/.local/bin/claude` (Mac) or `%USERPROFILE%\.local\bin\claude.exe` (Windows). Make sure that folder is on their PATH, so that typing `claude` works in every new window.
   - Windows, in PowerShell: `$p = [Environment]::GetEnvironmentVariable('PATH','User'); if ($p -notlike "*\.local\bin*") { $new = if ($p) { "$p;$env:USERPROFILE\.local\bin" } else { "$env:USERPROFILE\.local\bin" }; [Environment]::SetEnvironmentVariable('PATH', $new, 'User') }`
   - Mac: if `~/.zshrc` does not already contain it, append `export PATH="$HOME/.local/bin:$PATH"`.
   Then verify rather than trusting the edit. Mac: `zsh -lic 'command -v claude'` (a login shell re-reads `.zshrc`). Windows: a child process inherits this window's PATH and will not see the change, so check the record instead: `[Environment]::GetEnvironmentVariable('PATH','User') -like '*\.local\bin*'` and `Test-Path "$env:USERPROFILE\.local\bin\claude.exe"`, both true. Say whether it passed, and say plainly that only windows opened after this will find `claude` by name. The icon in step 6 does not depend on it.

2. **Find home.** Their home folder is `~` on a Mac and `%USERPROFILE%` (`$HOME` in PowerShell) on Windows. Use its path throughout, whatever the current folder is. Make `HQ` directly inside it. Never inside OneDrive, iCloud, Dropbox or Google Drive: on Windows, `Documents` is often OneDrive, and on a Mac, Desktop and Documents often sync to iCloud, which is why HQ goes in the home folder itself. If `HQ` already exists and holds files, step 0 applies: keep what is there and add only what is missing.

3. **Fetch the kit** into a temporary folder outside HQ. First find out whether `git` is usable without touching it: on a Mac run `xcode-select -p` (a path means the developer tools, and Git with them, are installed; an error means they are not, and any `git` command would open Apple's install window before you have explained it, so do not run one yet); on Windows run `Get-Command git -ErrorAction SilentlyContinue` (nothing printed means not usable; that is an answer, not an error). If Git is usable: `git clone --depth 1 https://github.com/Lionsberg/lionsberg-intelligence.git`. If it is not: download `https://github.com/Lionsberg/lionsberg-intelligence/archive/refs/heads/main.zip` and extract it with `tar -xf` (`tar` is on every Mac and on Windows 10 and later; macOS `unzip` fails on one file name in this archive). The extracted folder is named `lionsberg-intelligence-main`.

4. **Place it.** Copy the *contents* of `player-plus/`, dotfiles included, into HQ. Mac: `cp -R <temp>/player-plus/. ~/HQ/`. PowerShell: `Get-ChildItem "<temp>\player-plus" -Force | Copy-Item -Destination "$HOME\HQ" -Recurse -Force`. Then delete the temporary folder. HQ keeps no git remote pointing at this repository; the kit's `MOVING-IN.md` says why.

5. **Git.** If the check in step 3 found Git, run `git --version` and move on. If Git is missing:
   - Windows: `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements`. Tell them first: Windows will ask whether to allow an app to make changes to the device; the answer is yes. Git will be usable in the next terminal window, which is the one the icon opens.
   - Mac: `xcode-select --install`. Tell them first: a window opens; click **Install**, then **Agree**; it can take five to forty minutes and may open behind other windows; you will carry on with the remaining steps while it runs.
   - If neither works, say so and move on. Git can come later, and their agent will help.

6. **The record.** The kit carries a small engine, in `HQ/engine/`, that keeps their record: what they commit to and what others commit to them, one line at a time, on this computer. Their agent makes the record with them when it wakes. Everything stays on this computer: the agent runs here from its first minute, and their phone reaches it here later. Here you do two things, and each may be skipped without harm.
   - **Python.** The engine needs Python 3. On a Mac, Python comes with the same developer tools as Git: if `xcode-select -p` printed a path in step 3, or the install in step 5 has finished, run `python3 --version`; if the tools are still installing, skip this step and say that their agent will finish it. On Windows, run `Get-Command python -ErrorAction SilentlyContinue`; if it prints nothing, or `python --version` opens the Microsoft Store or prints nothing, Python is not installed: say so and skip this step. Do not install Python yourself. Without it the house works at the paper floor, and their agent will help them add it later.
   - **No keys.** Do not make a signing key. Their key and their agent's key are two keys, each named for its actor. Their agent makes their key silently with their home, on their first yes, and its own key, with their passphrase, when they first join a cell.
   - **Conformance.** Run `python3 -I HQ/engine/conformance.py` (Windows: `python -I "$HOME\HQ\engine\conformance.py"`). It works in a temporary folder, writes nothing in HQ and sends nothing anywhere. Every check should read PASS except signing, which reads PAPER FLOOR because no key exists yet: that is not a failure, and the last line says so ("5 of 6 pass; signing at the paper floor"). If any line reads FAIL, say which, copy the sheet into the receipt, and carry on: their agent will see it.
   - **The proxy** (`HQ/engine/proxy.py`) is optional and stays off. Do not start it. If they ask about it, say that their agent can explain it and start it with them later.

7. **The icon.** Make **My Agent** on their Desktop, so that they never have to find HQ by hand again.
   - Windows, in PowerShell (prefer Windows Terminal when it is present):
     ```powershell
     $ws = New-Object -ComObject WScript.Shell
     $desk = [Environment]::GetFolderPath('Desktop')
     $s = $ws.CreateShortcut("$desk\My Agent.lnk")
     if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
       $s.TargetPath = (Get-Command wt.exe).Source
       $s.Arguments = "-d `"$HOME\HQ`" powershell -NoExit -Command `"& '$HOME\.local\bin\claude.exe'`""
     } else {
       $s.TargetPath = "$PSHOME\powershell.exe"
       $s.Arguments = "-NoExit -Command `"Set-Location '$HOME\HQ'; & '$HOME\.local\bin\claude.exe'`""
     }
     $s.WorkingDirectory = "$HOME\HQ"
     $s.Save()
     ```
   - Mac: a `.command` file, which opens in Apple's Terminal when double-clicked. Set Terminal's default profile to a dark one first, because on a light background some of Claude's words are invisible. Tell them first: the Mac may ask whether Terminal may access files in the Desktop folder; the answer is OK, now and again when they first double-click the icon.
     ```bash
     defaults write com.apple.Terminal "Default Window Settings" -string Pro
     defaults write com.apple.Terminal "Startup Window Settings" -string Pro
     printf '#!/bin/zsh\nexport PATH="$HOME/.local/bin:$PATH"\ncd ~/HQ && exec "$HOME/.local/bin/claude"\n' > ~/Desktop/"My Agent.command"
     chmod +x ~/Desktop/"My Agent.command"
     ```
   Tell them the icon opens a terminal in HQ and starts their agent, every time. On Windows, also give Windows Terminal a profile of the same name, so the agent is in its dropdown too: write `%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\LIONSBERG\my-agent.json` containing `{"profiles": [{"name": "My Agent", "commandline": "powershell -NoExit -Command \"& '%USERPROFILE%\\.local\\bin\\claude.exe'\"", "startingDirectory": "%USERPROFILE%\\HQ", "colorScheme": "Campbell"}]}` (skip if Windows Terminal is not installed; remove by deleting the folder). Create the folder first, then write exactly these characters with your file tool, never through a quoted shell string, or the `\"` and `\\` escapes are eaten.

8. **The receipt.** Write `HQ/setup-receipt.md`, in plain words: the date, what was made inside HQ, and **every file outside HQ that was created or changed, with the exact line added and how to undo it** (the PATH line or the user PATH entry; the Desktop icon; the Terminal fragment; the Terminal default profile on a Mac; Git, and how it was installed). Run `doctor` by the full path, with a timeout of a minute; if it does not return, skip it. Put only its warnings, if any, at the end. If you ran conformance, put its last line in the receipt, and the whole sheet if anything failed. This is the person's record of what an AI did to their computer; keep it honest and short.

9. **Show, then hand over.** List the files in HQ and point at `CLAUDE.md` and `START-HERE.md`. Point at `setup-receipt.md` too. Then say, in these words or your own: *Type `/exit`. Then double-click **My Agent** on your Desktop. When it asks whether to trust the folder, check that it names HQ, and say yes. Your agent wakes there, reading its own instructions. If its words are hard to read on the dark window, type `/theme` and choose a dark theme. Your first message is one sentence, with your own names: Hello, I am Ada. I will call you River. Please wake up and meet me. It will greet you by name, ask one thing before it keeps anything for you, and deal you your first cards within minutes.*

## What you do not do

- You do not start `claude` inside HQ yourself, and you do not run `git init` there; their agent does that with them when it wakes.
- You do not read, copy or send anything from elsewhere on their computer.
- You do not edit the kit's files. If something in the kit looks wrong, tell them, and they can say so at https://github.com/Lionsberg/lionsberg-intelligence.

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
