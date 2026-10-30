---
name: voice-mode
description: Sets up natural voice with your agent on an ordinary computer (a Mac with Apple silicon or Intel, or Windows; no newest chip required), on the person's yes and after saying what it costs: ears that turn speech into words (whisper.cpp or faster-whisper) and a warm mouth that reads the agent's words aloud (Kokoro first, Piper for a slower machine), both running on this computer's CPU, wired into the HUD with serve.py's --speech and --voice, tested without playing a sound, and reached from a phone through the phone door. Use when the person says "voice mode", "talk to me", "I want to speak with you", "read it aloud", "can I use this on a walk", or asks why the microphone does nothing on the phone.
license: MPL-2.0
---

# Voice mode

Voice is the shortest way between a person and their agent: a sentence spoken on a walk, an answer heard without looking down. It is also the easiest place to spend someone's afternoon and disk on the wrong thing. This skill sets up the best voice an ordinary computer can carry today, and leaves room to improve it later.

**Nothing is installed without the person's yes.** Before any install, say what it is, how much disk, and roughly how many minutes, in one short message, and wait.

## What the person should know first (say it in your own words, briefly)

- **The audio stays on this computer.** The ears and the mouth run here, on its own processor. A phone only records and plays; what it records goes to this computer over the private network, is turned into words, and is deleted. No recording and no reading-aloud enters the record; only words the person sends become their line.
- **Installing reaches the network once.** The programs and the model files are downloaded on the person's yes, from the places named below. After that, nothing about voice leaves the machine.
- **Voice, then words, then the card.** Every spoken word appears as text before it is sent, and every word read aloud is also on the page. Nothing is voice-only.
- **The earpiece rule.** When the person starts to speak, the agent's voice stops at once, and the microphone is closed while the agent's voice plays. On a speaker the room hears it too; earphones are the right default on a walk or among people.

## The parts, named honestly

**Ears (speech to words).** Pick one.

| | What it needs | Disk | Notes |
|---|---|---|---|
| **whisper.cpp** (MIT) | the `whisper-cli` program, a model file, and `ffmpeg` to read what a browser records | `base.en` model about 150 MB; `small.en` about 470 MB | Fast on any Apple silicon Mac and fine on Intel. On a Mac: `brew install whisper-cpp ffmpeg`. On Windows: the project's prebuilt release, or use faster-whisper. |
| **faster-whisper** (MIT) | Python 3.9 or newer; `python3 -m pip install faster-whisper` | packages about 200 MB; `base.en` model about 150 MB, fetched on first use | Reads a browser's audio itself (no `ffmpeg`). The easiest path on Windows. |

**Mouth (words to a warm voice).** Pick one; Kokoro first.

| | What it needs | Disk | Notes |
|---|---|---|---|
| **Kokoro-82M** through **kokoro-onnx** | Python 3.10 or newer; `python3 -m pip install kokoro-onnx`; the files `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the kokoro-onnx releases | about 340 MB (an int8 model of about 90 MB exists, a little rougher) | The warmest open voice that runs on a CPU at this size. Weights Apache-2.0, the wrapper MIT. Its pronunciation uses espeak-ng (GPL-3.0), brought in by the package. Default voice `af_heart`. |
| **Piper** (`piper-tts`) | Python; `python3 -m pip install piper-tts`; one voice (`.onnx` and `.onnx.json`) | about 60 MB a voice | Very light and fast, even on an old laptop; a plainer voice. The program is GPL-3.0 since its move to the Open Home Foundation, and **each voice has its own licence** in its model card: read it before choosing one. |

**Which I would pick first, and why:** **Kokoro**, for the warmth of its voice, its permissive weights licence and a size an ordinary computer carries easily. **Piper** when the computer is old or slow, or when disk is short. Both run on the CPU; neither needs a graphics card or the newest chip. Measure the speed on this computer with the test below before promising anything about it.

## The contracts the HUD speaks (hud/serve.py)

- **`--speech CMD`**: CMD is run with the audio file's path as its **last argument**; whatever it prints on stdout is the words. The audio is written under the home's `.voice/` (0600) and deleted after.
- **`--voice CMD`**: CMD is split like a shell line (no shell is run) and the text is appended as its **last argument** (at most 4,000 characters). It writes a **new WAV file** and prints that file's path on the **last line of stdout**, exit 0, within 60 seconds. The server reads it only if it is a plain file written after the request began, under 20 MB, beginning `RIFF....WAVE`; then deletes it. It never plays anything itself.

The kit carries one wrapper per model under `hud/voice/`, each keeping its contract and each saying in one line what to install when its model is not there:

- `hud/voice/speech-whisper.sh`: whisper.cpp, else faster-whisper
- `hud/voice/voice-kokoro.sh`: Kokoro
- `hud/voice/voice-piper.sh`: Piper

They look for models under `~/.local/share/lionsberg/voice/` (or `LIONSBERG_VOICE_HOME`): `whisper/ggml-base.en.bin`, `kokoro/kokoro-v1.0.onnx` and `kokoro/voices-v1.0.bin`, `piper/en_US-lessac-medium.onnx` with its `.onnx.json`. Each script's header names the variables that move them.

## The steps

1. **Look before asking.** Read, without changing anything: the chip (`uname -m`; on Windows, `echo %PROCESSOR_ARCHITECTURE%`), the free disk, whether `python3 --version`, `ffmpeg -version`, `brew --version` (Mac) or `winget --version` (Windows) answer, and run each wrapper once with no model: its one line says what is missing.
2. **Ask once, with the cost.** For example: *"For voice I would install whisper.cpp with its base English model for your ears and Kokoro for my voice: about 500 MB in all and about ten minutes on a home connection, downloaded from Homebrew, Hugging Face and the kokoro-onnx releases. Everything runs on this computer afterwards. Shall I?"* Offer Piper instead when the machine is old or short of disk.
3. **On the yes, install** what was agreed, and only that. Model files go in the folders above. On a Mac, Homebrew for `whisper-cpp` and `ffmpeg`; `pip` into a virtual environment for Kokoro or Piper if the person keeps one (then point `KOKORO_PYTHON` or `PIPER` at it). On Windows, Python from python.org or `winget`, then `pip`; run the wrappers through Git for Windows' `sh` and set `KOKORO_PYTHON=python` and `WHISPER_PYTHON=python`.
4. **Test without a sound.** Never play audio aloud on the person's computer to check it. Make a sentence into a file, measure it, then hear it back with the ears:

   ```sh
   f=$(sh hud/voice/voice-kokoro.sh "Good morning. The Deal has three cards for you today.")
   python3 -c "import sys, wave; w = wave.open(sys.argv[1]); print(round(w.getnframes() / w.getframerate(), 1), 'seconds')" "$f"
   sh hud/voice/speech-whisper.sh "$f"
   rm -f "$f"
   ```

   Two to five seconds of audio, and the ears giving back the sentence, is a working voice. Time the first command too: that is how long the person will wait before the agent starts to speak.
5. **Wire it into the HUD.** Start the server with both commands, absolute paths so they work from any folder:

   ```sh
   python3 hud/serve.py --hq ~/your-house \
     --speech "sh $PWD/hud/voice/speech-whisper.sh" \
     --voice "sh $PWD/hud/voice/voice-kokoro.sh"
   ```

   `GET /voice/info` then answers `{"hear": true, "say": true}`, and the dock offers the microphone and the voice.
6. **The phone, if the person wants it.** Add `--phone`. The person opens the door from this computer's HUD; the phone's browser gives a page its microphone only over a secure connection, so the door speaks TLS with a certificate this computer makes for itself. The first time, the phone opens the plain address the HUD shows, compares the fingerprint on both screens, and trusts this computer once (the page walks through it for an iPhone and for Android); after that the door's `https` address with its pairing code is the way in. What trusting it means, and how to remove it: `hud/DESIGN-PHONE-DOOR.md`.
7. **Say what was done**, in two lines: what is installed and where, and how long a sentence takes to be heard and to be said on this computer.

## When it goes wrong

- **The microphone does nothing on the phone.** The page is not secure: the phone is on the plain address, or has not trusted this computer yet. Send the person to the trust page the HUD shows.
- **A wrapper prints its one line.** The model or program it names is not there; nothing else is wrong.
- **Her voice takes too long.** Long turns are read in full before playing; on a slow machine choose Piper, or keep the voice for short turns.
- **The words are wrong.** Try the `small.en` model for the ears (about 470 MB), on the person's yes.

## What this skill never does

It never installs without the person's yes; never plays sound on the computer to test; never sends audio or text to a service off the machine; never opens a port beyond the phone door's own; and never keeps a recording unless the person asked to keep it.
