# Keeping Your Agent Awake — Reaching It From Your Phone

*Your agent lives on one computer, yours. Your phone is a door into it. This page is how to keep that computer awake and reachable, what it costs, and what to do on the day the door will not open.*

A [[Player+]]'s [[Agent]] runs on their own machine. That is what keeps it yours: your memory, your [[The Record — How Your Holon Remembers|record]] and your words stay in your house, under your hand ([[Sovereignty]]). The price of that freedom is small and practical. When you reach for your agent from the bus, the kitchen or a walk, the computer at home has to be awake to answer.

## 1. What is actually running

- **One computer, yours.** A laptop or a desktop, at home, plugged in. Your agent's home, HQ, is on it, and so is your agent: a session of Claude Code, running in the window the **My Agent** icon opens.
- **Your agent on it.** Everything your agent does happens on that computer: reading, writing, keeping your record, dealing [[The Deal]].
- **Your phone is a door, never a home.** Nothing of your agent lives on the phone. The phone shows you the conversation and carries your words in. Put the phone down and nothing is lost; turn the computer off and the door opens onto nothing.

So three things must be true for the phone to reach your agent: **the computer is awake**, **its network is up**, and **your agent's session is running** on it.

What may sleep, and what may not:

| May sleep | May not sleep |
|---|---|
| The screen. Let it go dark after a few minutes; that costs nothing. | The computer itself, while you want to reach it. |
| You. | The network connection. |
| Your phone. | The window your agent runs in. Closing it ends the session. |

## 2. The settings, step by step

Do these once, on the computer, with your agent beside you. Your agent can walk you through each step and write every change, with how to undo it, in `setup-receipt.md` in HQ, the same receipt the install began.

### On a Mac

1. **Keep it awake on power.** Open **System Settings**, then **Battery** on a laptop or **Energy** on a desktop (the names move a little between versions of macOS; look for *Options* inside Battery). Turn on the switch that reads something like *Prevent automatic sleeping on power adapter when the display is off*. Leave **Wake for network access** on if you see it.
2. **Let the display sleep.** In **Lock Screen** settings, set the display to turn off after five or ten minutes when on power. A dark screen is fine; a sleeping computer is not.
3. **Keep it plugged in.** The settings above hold only on power. On battery, a Mac sleeps to save itself.
4. **The lid.** A Mac laptop sleeps when you close its lid, whatever the settings above say, unless it is on power **and** has an external display attached. So the simple way is the honest one: **leave the lid open**, let the screen go dark, and set the laptop somewhere cool. If you must close the lid with no display attached, there is an unsupported setting that overrides it, `sudo pmset -a disablesleep 1` (undo: `sudo pmset -a disablesleep 0`), and some small utilities do the same; use either only on power, on a hard surface, never in a bag, because a closed laptop that stays awake has nowhere to put its heat.

**The commands, for those who prefer them** (in Terminal):

- `pmset -g custom` shows your current settings. Copy what it prints into your receipt first, so you can put things back.
- `sudo pmset -c sleep 0` tells the Mac never to sleep on its own while on power (`-c` means "on charger"). `sudo pmset -c displaysleep 10` lets the screen sleep after ten minutes.
- `caffeinate -is` keeps the Mac awake for as long as that Terminal window stays open, and changes no setting at all. Press Control-C, or close the window, and the Mac returns to its usual habits. It is a good way to try this for a day before changing anything.

### On Windows

1. **Keep it awake on power.** Open **Settings**, then **System**, then **Power & battery** (on Windows 10, **Power & sleep**). Under screen and sleep, set **When plugged in, put my device to sleep after** to **Never**, and **turn off my screen after** to five or ten minutes.
2. **The lid.** Open **Control Panel**, then **Power Options**, then **Choose what closing the lid does**. Set **When I close the lid**, in the *Plugged in* column, to **Do nothing**. On Windows this works with no external display: the lid closes, the screen goes dark, and the computer keeps running. Keep it on a hard surface and out of a bag, for the same reason as on a Mac.
3. **The network adapter.** If the computer drops its Wi-Fi when idle, open **Device Manager**, find your network adapter, and on its **Power Management** tab clear *Allow the computer to turn off this device to save power*. A cable to your router, where you can run one, is steadier still.
4. **Updates.** Windows may restart itself to install updates, which ends your agent's session. In **Windows Update**, set your **active hours** to the hours you are most likely to reach for your phone.

**The commands, for those who prefer them** (in PowerShell, as yourself):

- `powercfg /change standby-timeout-ac 0` never sleeps on power; `powercfg /change monitor-timeout-ac 10` lets the screen sleep after ten minutes.
- `powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0`, then `powercfg /setactive SCHEME_CURRENT`, sets the lid to do nothing while plugged in.
- `powercfg /requests` shows what is keeping the computer awake right now; `powercfg /a` shows which kinds of sleep it has.

### On either

- **Your agent's window stays open.** Start your agent from **My Agent** and leave that window open. Minimizing it is fine; closing it ends the session. The [`phone-path`](../../skills/phone-path/SKILL.md) skill asks your agent to keep a session running so there is always one to find.
- **The private network starts on its own.** If your [[Cell]] uses a private network, set its app to start when the computer starts, and stay signed in on both the computer and the phone.
- **Check that it worked: the phone test.** Leave the computer alone for an hour, longer than it used to stay awake. Then, on your phone, with Wi-Fi turned off so you are truly away, reach your agent by one of the doors below and ask: *"When did this computer last sleep?"* It can read the answer from the computer itself (on a Mac, `pmset -g log`; on Windows, `powercfg /lastwake` and the system's event log). If it answers and has not slept, you are done.

## 3. What it costs

**Electricity.** A laptop idling with its screen dark draws a few watts to around fifteen; a desktop, a few tens of watts. As a rough guide, an awake laptop costs somewhere around one or two dollars a month at common household rates, and a desktop a few times that. These are estimates; your own machine and your own rates decide. It is about what a small lamp costs, left on.

**Wear.** A computer awake all day wears very little: no moving parts in most laptops, fans that rest when it is idle. The part that ages is a laptop's battery, held full on the charger day and night. If your computer offers *optimized charging* or a *charge limit* (on a Mac in the Battery settings; on Windows, often in the maker's own app), turn it on. Heat is the other enemy: keep the vents clear.

**Your attention.** An agent you can reach at any hour is a door you open, never a bell that rings for you. Let the computer sleep when you will not reach for it: at night, on a day of rest, in the hours you keep for the people in front of you ([[Spending Attention]]). On a Mac, `sudo pmset repeat sleep MTWRFSU 23:00:00 wakeorpoweron MTWRFSU 06:30:00` sleeps it each night and wakes it each morning (`pmset -g sched` shows the schedule; `sudo pmset repeat cancel` removes it). On Windows, sleep it by hand, or ask your agent to make a scheduled task with you.

**What you will see.** When the computer has slept, nothing is hidden. The ICE (the Integrated Creation Environment: the views of [[The HUD]], where your Deal and your conversation with your agent sit side by side) says so the next morning, once, in plain words: *slept at 23:10, woke at 07:02*. By noon it says only *awake*. From the phone, while the computer sleeps, it says *your computer is asleep, so your agent is resting*. A sleep you chose is a good night, never a failure.

## 4. The two doors from the phone

| | Through the ICE, on the private network | Remote Control, in the Claude app |
|---|---|---|
| **What it is** | Your own computer serves the ICE to your phone's browser, over the private network only. | The Claude app on your phone opens the session running on your computer. |
| **Where it works** | Wherever your phone is on the private network. | Anywhere your phone has a connection. |
| **The proxy** | Stays. Your words still go through your own proxy on the computer, which records where each request went. | Lost. Remote Control refuses any proxy, so nothing records where your words go. |
| **Setting it up** | Once, from the computer: **Let my phone in**, then a one-time code shown on the screen, which your phone presents. The phone gets a pass of its own, and you can **Let it go** at any time. | Once, as the [`phone-path`](../../skills/phone-path/SKILL.md) skill says: find your computer's name, then your agent's folder. |

**Use the ICE door when you can.** It keeps everything the computer keeps: the proxy, the record of where your words went, the cards and their asks. It is off until you turn it on, and it listens only on the private network, never on the open internet. If your house does not run the ICE yet, your agent can set it up with you when you are ready.

**The phone never reaches the HUD over the open internet.** The HUD on your computer listens only to that computer itself; nothing outside it can open the page. Your phone reaches it in one of two ways only: through your private network, by the door you open on the computer and the one-time pairing code it shows, or through Remote Control, which reaches the conversation, not the HUD. Do not forward a port on your router, and do not use a service that puts your computer on the open internet to get round this: your record is behind that door. On your first day, the phone does neither; its door is set up with your agent on day two, if you chose your phone.

**Use Remote Control when the ICE door cannot reach your computer**: away from the private network, or before you have set it up. It reaches the same agent on the same computer. It simply works without the record of where your words go.

**The button not to press.** In the Claude app there is a large **New Session** button. It does not open your agent. It starts a session on the provider's computer, with none of your files and no memory of you. *The New Session button is not your agent; find your computer's name instead.* If you ever find yourself somewhere that looks like your agent and does not remember you, stop there, and go back by your computer's name. [[The Phone Path]] says more.

## 5. The bad day

**The phone cannot find your computer.** Work down this list; each line takes a minute.

1. **Is it on, and on power?** If someone is home, ask them to look. A press of a key or a lifted lid wakes it.
2. **Did it restart?** An update or a power cut ends the session. Open **My Agent** again (or ask the person at home to double-click it).
3. **Is the network up?** If the home Wi-Fi dropped, the computer is awake and alone. Restart the router, or wait for it to return.
4. **Is the private network on, on both ends?** If the ICE door will not open, check the private network's app on the phone and on the computer. Then try Remote Control instead.
5. **Is it the right name?** In the Claude app, look for your computer's name, never the New Session button.

If none of it works, the computer is out of reach for today. Nothing is lost. Your record is on the computer, whole, and waits for you.

**What your agent does when it wakes.** It reads the record before it says anything. Then it tells you, in a line, what it missed: *"This computer slept from 23:10 to 07:02. Nothing you wrote in that time reached me; if you wrote, tell me again."* It will never pretend it heard what did not arrive. Then it deals: one [[The Deal|Deal]], sized to the minutes you have today, never a pile of everything that waited. What slipped while it slept is said plainly, and what can still be kept is put back in play ([[Commitment]]).

## 6. With a notebook

No computer needs to be awake for you to play. If the machine is off for a week, or you are somewhere no phone reaches, the Game goes on in your hand ([[Notebook form]] · [[Screens and paper]]).

- **Ask your agent to print the week's cards** the night before you leave. The printed Deal has a box for each answer; fill it with a pencil.
- **Keep your own sheet.** [[The Game Engine — By Pencil]] shows how to work your commitments, what is owed and what comes next, by hand, with the same answers the computer would give.
- **Bring it home.** When you are back, show your agent the cards or a photo of them, or read them aloud. It writes each line into your record as yours, and the paper you signed is kept.

A notebook is a complete player. The awake computer makes the Way faster; it was never the Way.

## The prompt

Give your agent these words, as they are:

> *Help me keep this computer awake so I can reach you from my phone. Show me each setting first and change nothing until I say. Write every change, and how to undo it, in my setup receipt. Then let us do the phone test together.*

---

*Read next: [[The Phone Path]] · [[Foreground and Background]] · [[The Deal]] · [[The Record — How Your Holon Remembers]] · in the Field, [[The HUD]], [[Screens and paper]] and [[Spending Attention]].*

*CC BY-SA 4.0 · LIØNSBERG*
