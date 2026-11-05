# INSTALL — for Claude, on a new Player's computer

*A person has pasted a link to this file into Claude. They are at Gate 4 of [Becoming a Player+](player-plus/bookshelf/getting-started/Becoming%20a%20Player%2B%20%E2%80%94%20the%20Quest.md). Most often they are in the **Code** tab of the Claude desktop app, in a local session opened on a new, empty folder named for their agent (or **My Agent**, if they have not chosen a name yet), inside a folder called **My Agents** in their home folder: that is **the app way**. Some came by **the terminal way**: Claude Code was installed a minute ago and started by its full path in a terminal, they have signed in, and the terminal is open in their home folder. You are the Claude they are speaking with. This page says what to build, and how to be with them while you build it. It is public, so that anyone can read exactly what it asks of you.*

## For the person: from the door to the first word

*This part is for you, the person, before you paste anything. The rest of the page is for the Claude that builds your companion's home.*

**The whole way, with the time each part takes.**

1. **The door.** At lionsberg.world, choose **Becoming a Player+**, which brings you to the Quest.
2. **An account. About five minutes.** Your companion thinks with Claude, an AI made by Anthropic. Type claude.ai into your browser yourself, make an account, and choose the Pro plan. If you have one, this step is done.
3. **The Claude app. About five minutes.** Download it from claude.ai/download, install it, open it, and sign in with the same account.
4. **The house. About ten minutes, most of it saying yes.** In the app's **Code** tab, make a folder named **My Agents** in your home folder, and inside it a new folder named for your companion; open that one, and paste the sentence the Quest gives you. Claude builds your companion's home there, and a folder named **HQ** beside My Agents for your work, saying each step before it takes it.
5. **Your companion wakes.** Start a new session on your companion's folder and send one sentence. It speaks first, within about a minute, and deals you your first card within about five.

**Every question you will be asked, in order, and what to answer.**

| When | What you see | What to answer |
|---|---|---|
| Before you paste | The row under the box where you type: the mode | **Manual**, which asks before each step. If it says anything else, click it and choose Manual. Do not choose Bypass permissions: it lets Claude act without asking you. |
| Claude starts | It asks to download this page | Yes. |
| By the terminal way, at the start | *What will you call your agent?* | The name you chose, or *not yet*: then the folder is **My Agent**, and you name your agent when it wakes. |
| It tells you, in five plain lines, what it will build | Then, before each command, a request to allow it | **Allow**, each time, after reading its one line. Expect about a dozen. Say no whenever a line surprises you, and ask it why. |
| On a Mac, if the developer tools are missing | A window: *install the command line developer tools?* | **Install**, then **Agree**. It takes five to forty minutes and may open behind other windows. The rest carries on while it runs. |
| On Windows, if Git is missing | *Do you want to allow this app to make changes to your device?* | Yes. |
| At the end | *Start a new session on your companion's folder* | Do it: a new session, the folder you opened at the start (the app keeps it in its list), and your first sentence. |
| Your companion's first minutes | A request to allow it to run its record's engine (`python3 -I engine/…`), and to write to its `memory/` folder | Allow. About five, the first evening. If it offers to stop asking for the engine in its folder, that is safe and saves you the rest. |

**The wait, truthfully.** The building takes about five to ten minutes of yeses. On a Mac without developer tools, their install can run up to forty minutes beside it; your companion does not wait for it to wake. If the tools are still installing when it wakes, it writes your first lines on paper, in a plain file, and puts them on your record when the tools finish, with your yes.

**Your first message, one sentence.** In your new session on your companion's folder, paste or type, with your own names:

> Hello, I am Ada. I will call you River. Please wake up and meet me.

That is all it needs. Its charter tells it the rest: it greets you by name, asks one thing before it keeps anything for you (the waiver, in one line, agreed by one word), quietly makes your home, and deals you your first cards.

**What a phone can and cannot do on day one.** Your companion lives on this computer, and so does your record. On day one your Deal is in your conversation with it here, and it can open the HUD, the page where your Deal and your conversation sit side by side, in this computer's browser. Your phone cannot reach either on day one. The HUD listens only to this computer, never to the open internet. Later, if you chose your phone, your companion sets up its door with you as a card on day two: through your private network, with a one-time pairing code shown on this computer's screen (**Let my phone in**), or through Remote Control in the Claude app (the `phone-path` skill). Never by opening this computer to the open internet. [Keeping Your Agent Awake](<player-plus/bookshelf/with-your-agent/Keeping Your Agent Awake — Reaching It From Your Phone.md>) has the settings.

## How to be

- **They are new to this.** Start by saying, in five plain lines, the five things under *What you are building* and every file outside the agent's folder and HQ you will touch. Then, before each step, say in one plain line what you are about to do and why, and do it. Ask them only when you truly need to.
- **Stay inside the lines.** You may touch: the agent's folder and the `My Agents` folder that holds it, the HQ folder, a temporary download folder that you delete, and Git. By the terminal way only, also: their PATH (so that `claude` is found), one launcher on their Desktop, on Windows one Windows Terminal profile fragment, and on a Mac the Terminal's default colours. Change nothing else on their computer. Send nothing anywhere. Push to no repository.
- **When something fails,** say what you saw and what you propose. Never guess silently, and never work around a refusal.

## What you are building

Two folders, side by side in their home folder, never one inside the other:

- **The agent's home**: a folder named for their agent inside **My Agents** (`My Agents/River/`, or `My Agents/My Agent` until a name is chosen), holding the Player+ kit: the contents of this repository's `player-plus/` folder, so that `CLAUDE.md` and `START-HERE.md` sit at its top level, never inside a subfolder, with the hidden `.claude/` folder and `.gitignore` beside them. The agent lives here, and every session with it opens here.
- **HQ**: where their work will live, holding `projects/` and a short `README.md`, and never a `CLAUDE.md`. It is a place, not a person: the agent walks over to it. The kit's settings already let the agent reach `~/HQ`.

Git installed. A conformance sheet that shows the record's engine works on this computer. A receipt. And their door back in: by the app way, the agent's folder in the app's folder list, which the app keeps; by the terminal way, `claude` on their PATH and an icon on their Desktop, **My Agent**, that opens the terminal in the agent's folder and starts `claude`.

## The steps

0. **Look before you build.** Find which way they came. If your working folder sits inside a folder named `My Agents` directly inside their home folder, it is the app way: your working folder is the agent's home, and you build in it. If your working folder is their home folder itself, it is the terminal way: ask once what they will call their agent; if they have not chosen, the folder is `My Agent`, and a name they give later lives in their agent's memory, so the folder can keep its name. A name becomes the folder's name as it is, less any of `/ \ : * ? " < > | ' %` and any leading dot. If your working folder is anywhere else, say so plainly and ask them to open a new session on a folder for their agent inside `My Agents` in their home folder (the Quest shows how), then stop. If a folder named `HQ` in their home folder already holds a `CLAUDE.md`, an agent already lives there, built by an earlier kit: say so, point them to the moving note at https://raw.githubusercontent.com/Lionsberg/lionsberg-intelligence/main/player-plus/MOVING-THE-AGENT-OUT-OF-HQ.md, which their agent reads with them, and stop. If the agent's folder or HQ already holds files, do not stop: say what is already there and do only what is missing, so an interrupted run can be resumed. Check whether the computer is managed by an employer or school (Mac: `profiles status -type enrollment`; Windows: `(Get-CimInstance Win32_ComputerSystem).PartOfDomain` or `dsregcmd /status` showing AzureAdJoined YES). If it is, say honestly, before trying anything, that IT policy may block an install, and carry on. By the terminal way, `claude` is not yet on the PATH in this window (they started it by its full path), so call it by that path in every command here: Mac `~/.local/bin/claude`, Windows `& "$env:USERPROFILE\.local\bin\claude.exe"`; run `auth status` that way, and if it does not say logged in, ask them to finish signing in first. On Windows without Git, you have a PowerShell tool and no Bash: use the PowerShell forms below.

1. **PATH (the terminal way only).** Claude Code lives at `~/.local/bin/claude` (Mac) or `%USERPROFILE%\.local\bin\claude.exe` (Windows). Make sure that folder is on their PATH, so that typing `claude` works in every new window. By the app way, skip this step: the app carries its own Claude.
   - Windows, in PowerShell: `$p = [Environment]::GetEnvironmentVariable('PATH','User'); if ($p -notlike "*\.local\bin*") { $new = if ($p) { "$p;$env:USERPROFILE\.local\bin" } else { "$env:USERPROFILE\.local\bin" }; [Environment]::SetEnvironmentVariable('PATH', $new, 'User') }`
   - Mac: if `~/.zshrc` does not already contain it, append `export PATH="$HOME/.local/bin:$PATH"`.
   Then verify rather than trusting the edit. Mac: `zsh -lic 'command -v claude'` (a login shell re-reads `.zshrc`). Windows: a child process inherits this window's PATH and will not see the change, so check the record instead: `[Environment]::GetEnvironmentVariable('PATH','User') -like '*\.local\bin*'` and `Test-Path "$env:USERPROFILE\.local\bin\claude.exe"`, both true. Say whether it passed, and say plainly that only windows opened after this will find `claude` by name. The icon in step 7 does not depend on it.

2. **Find home.** Their home folder is `~` on a Mac and `%USERPROFILE%` (`$HOME` in PowerShell) on Windows. Use its path throughout, whatever the current folder is. `My Agents` and `HQ` both sit directly inside it, and neither ever goes inside OneDrive, iCloud, Dropbox or Google Drive: on Windows, `Documents` is often OneDrive, and on a Mac, Desktop and Documents often sync to iCloud, which is why both go in the home folder itself. By the terminal way, make `My Agents` and the agent's folder inside it now. By the app way, the agent's folder is your working folder; check that it is not inside a synced folder, and if it is, say so and ask them to make `My Agents` in the home folder instead. Below, `<name>` is the agent's folder name: by the app way, your working folder's own name. Then make `HQ` in the home folder, if it is not there, with a `projects/` folder holding a `README.md` of two plain lines (one folder here for each project you and your agent work on; start each with a wish, as `bookshelf/project-management/Writing the Wish.md` in the agent's folder explains), and a `README.md` in HQ of three plain lines: this is your HQ, where your work lives; your agent lives in its own folder in My Agents and walks over here to work; no `CLAUDE.md` goes in this folder. If either folder already holds files, step 0 applies: keep what is there and add only what is missing.

3. **Fetch the kit** into a temporary folder outside both folders. First find out whether `git` is usable without touching it: on a Mac run `xcode-select -p` (a path means the developer tools, and Git with them, are installed; an error means they are not, and any `git` command would open Apple's install window before you have explained it, so do not run one yet); on Windows run `Get-Command git -ErrorAction SilentlyContinue` (nothing printed means not usable; that is an answer, not an error). If Git is usable: `git clone --depth 1 https://github.com/Lionsberg/lionsberg-intelligence.git`. If it is not: download `https://github.com/Lionsberg/lionsberg-intelligence/archive/refs/heads/main.zip` and extract it with `tar -xf` (`tar` is on every Mac and on Windows 10 and later; macOS `unzip` fails on one file name in this archive). The extracted folder is named `lionsberg-intelligence-main`.

4. **Place it.** If this page was downloaded into the agent's folder, delete that copy first. Copy the *contents* of `player-plus/`, dotfiles included, into the agent's folder, never into HQ. The kit is in `<temp>/lionsberg-intelligence/player-plus` (from git) or `<temp>/lionsberg-intelligence-main/player-plus` (from the zip); `<kit>` below is that folder. Mac: `cp -R <kit>/. "$HOME/My Agents/<name>/"`. PowerShell: `Get-ChildItem "<kit>" -Force | Copy-Item -Destination "$HOME\My Agents\<name>" -Recurse -Force`. Then delete the temporary folder. The agent's folder keeps no git remote pointing at this repository; the kit's `MOVING-IN.md` says why.

5. **Git.** If the check in step 3 found Git, run `git --version` and move on. If Git is missing:
   - Windows: `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements`. Tell them first: Windows will ask whether to allow an app to make changes to the device; the answer is yes. By the app way, Git is usable after they quit and reopen the app; by the terminal way, in the next terminal window, which is the one the icon opens.
   - Mac: `xcode-select --install`. Tell them first: a window opens; click **Install**, then **Agree**; it can take five to forty minutes and may open behind other windows; you will carry on with the remaining steps while it runs.
   - If neither works, say so and move on. Git can come later, and their agent will help.

6. **The record.** The kit carries a small engine, in the agent's folder under `engine/`, that keeps their record: what they commit to and what others commit to them, one line at a time, on this computer. Their agent makes the record with them when it wakes. Everything stays on this computer: the agent runs here from its first minute, and their phone reaches it here later. Here you do two things, and each may be skipped without harm.
   - **Python.** The engine needs Python 3. On a Mac, Python comes with the same developer tools as Git: if `xcode-select -p` printed a path in step 3, or the install in step 5 has finished, run `python3 --version`; if the tools are still installing, skip this step and say that their agent will finish it. On Windows, run `Get-Command python -ErrorAction SilentlyContinue`; if it prints nothing, or `python --version` opens the Microsoft Store or prints nothing, Python is not installed: say so and skip this step. Do not install Python yourself. Without it the house works at the paper floor, and their agent will help them add it later.
   - **No keys.** Do not make a signing key. Their key and their agent's key are two keys, each named for its actor. Their agent makes their key silently with their home, on their first yes, and its own key, with their passphrase, when they first join a cell.
   - **Conformance.** Run `python3 -I "$HOME/My Agents/<name>/engine/conformance.py"` (Windows: `python -I "$HOME\My Agents\<name>\engine\conformance.py"`). It works in a temporary folder, writes nothing in either folder and sends nothing anywhere. Every check should read PASS except signing, which reads PAPER FLOOR because no key exists yet: that is not a failure, and the last line says so ("5 of 6 pass; signing at the paper floor"). If any line reads FAIL, say which, copy the sheet into the receipt, and carry on: their agent will see it.
   - **The proxy** (`engine/proxy.py`) is optional and stays off. Do not start it. If they ask about it, say that their agent can explain it and start it with them later. A session in the desktop app may not route through a custom proxy, so the proxy is for the terminal way.

7. **The door back in.**
   - **By the app way, there is nothing to make.** The app keeps the folders they have used in its folder list, so the agent's folder is there next time. Tell them so in one line.
   - **By the terminal way, make the icon:** **My Agent** on their Desktop, so that the agent's folder is one double-click away.
     - Windows, in PowerShell (prefer Windows Terminal when it is present):
       ```powershell
       $ws = New-Object -ComObject WScript.Shell
       $desk = [Environment]::GetFolderPath('Desktop')
       $s = $ws.CreateShortcut("$desk\My Agent.lnk")
       if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
         $s.TargetPath = (Get-Command wt.exe).Source
         $s.Arguments = "-d `"$HOME\My Agents\<name>`" powershell -NoExit -Command `"& '$HOME\.local\bin\claude.exe'`""
       } else {
         $s.TargetPath = "$PSHOME\powershell.exe"
         $s.Arguments = "-NoExit -Command `"Set-Location '$HOME\My Agents\<name>'; & '$HOME\.local\bin\claude.exe'`""
       }
       $s.WorkingDirectory = "$HOME\My Agents\<name>"
       $s.Save()
       ```
     - Mac: a `.command` file, which opens in Apple's Terminal when double-clicked. Set Terminal's default profile to a dark one first, because on a light background some of Claude's words are invisible. Tell them first: the Mac may ask whether Terminal may access files in the Desktop folder; the answer is OK, now and again when they first double-click the icon.
       ```bash
       defaults write com.apple.Terminal "Default Window Settings" -string Pro
       defaults write com.apple.Terminal "Startup Window Settings" -string Pro
       printf '#!/bin/zsh\nexport PATH="$HOME/.local/bin:$PATH"\ncd "$HOME/My Agents/<name>" && exec "$HOME/.local/bin/claude"\n' > ~/Desktop/"My Agent.command"
       chmod +x ~/Desktop/"My Agent.command"
       ```
     Tell them the icon opens a terminal in their agent's folder and starts their agent, every time. On Windows, also give Windows Terminal a profile of the same name, so the agent is in its dropdown too: write `%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\LIONSBERG\my-agent.json` containing `{"profiles": [{"name": "My Agent", "commandline": "powershell -NoExit -Command \"& '%USERPROFILE%\\.local\\bin\\claude.exe'\"", "startingDirectory": "%USERPROFILE%\\My Agents\\<name>", "colorScheme": "Campbell"}]}` (skip if Windows Terminal is not installed; remove by deleting the folder). Create the folder first, then write exactly these characters with your file tool, never through a quoted shell string, or the `\"` and `\\` escapes are eaten.

8. **The receipt.** Write `setup-receipt.md` in the agent's folder, in plain words: the date, which way they came, what was made inside the agent's folder and HQ, and **every file outside those two that was created or changed, with the exact line added and how to undo it** (Git, and how it was installed; by the terminal way also the PATH line or the user PATH entry, the Desktop icon, the Terminal fragment, and the Terminal default profile on a Mac). By the terminal way, run `doctor` by the full path, with a timeout of a minute; if it does not return, skip it, and put only its warnings, if any, at the end. If you ran conformance, put its last line in the receipt, and the whole sheet if anything failed. This is the person's record of what an AI did to their computer; keep it honest and short.

9. **Show, then hand over.** List the files in the agent's folder and point at `CLAUDE.md` and `START-HERE.md`. Point at `setup-receipt.md` too, and say in one line that HQ, beside My Agents, is where their work will live. Then say, in these words or your own:
   - **By the app way:** *Your agent's home is built, and this session was only the builder. If Git was installed just now on Windows, first quit the Claude app completely and open it again. Then start a new session: press Cmd+N on a Mac or Ctrl+N on Windows, or click + New in the sidebar. Under the box, check that it says Local, that the folder has your agent's name (if not, click the folder and choose it from the folders you have used, or Open folder…, then My Agents, then your agent's folder), and that the mode says Manual. Your agent wakes there, reading its own instructions. Your first message is one sentence, with your own names: Hello, I am Ada. I will call you River. Please wake up and meet me. It will greet you by name, ask one thing before it keeps anything for you, and deal you your first cards within minutes. Next time, the same: a new session on your agent's folder.*
   - **By the terminal way:** *Type `/exit`. Then double-click **My Agent** on your Desktop. When it asks whether to trust the folder, check that it names your agent's folder, and say yes. Your agent wakes there, reading its own instructions. If its words are hard to read on the dark window, type `/theme` and choose a dark theme. Your first message is one sentence, with your own names: Hello, I am Ada. I will call you River. Please wake up and meet me. It will greet you by name, ask one thing before it keeps anything for you, and deal you your first cards within minutes.*

## What you do not do

- You do not start their agent yourself, and you do not run `git init` in either folder; their agent does that with them when it wakes, in its own session.
- You do not read, copy or send anything from elsewhere on their computer.
- You do not edit the kit's files. If something in the kit looks wrong, tell them, and they can say so at https://github.com/Lionsberg/lionsberg-intelligence.

*Current best understanding, loosely held · improved each week. CC BY-SA 4.0 · LIØNSBERG*
