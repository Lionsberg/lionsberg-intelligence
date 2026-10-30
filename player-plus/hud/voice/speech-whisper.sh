#!/bin/sh
# speech-whisper.sh: the ears. serve.py's --speech contract: the audio file's path is the LAST argument;
# the words are printed on stdout; nothing else is printed there. Runs on this computer only; the audio
# never leaves it. Plays nothing.
#   serve.py --speech "sh hud/voice/speech-whisper.sh"
# Engines, in order: whisper.cpp (whisper-cli, with ffmpeg to read what a browser records), then
# faster-whisper (Python; reads the browser's audio itself). The setup: skills/voice-mode/SKILL.md.
#   LIONSBERG_VOICE_HOME   where the models live (default ~/.local/share/lionsberg/voice)
#   WHISPER_MODEL          a whisper.cpp model file (default $LIONSBERG_VOICE_HOME/whisper/ggml-base.en.bin)
#   WHISPER_CLI            the whisper.cpp program (default: whisper-cli on PATH)
#   FASTER_WHISPER_MODEL   a faster-whisper model name or folder (default base.en)
#   WHISPER_PYTHON         the Python that has faster-whisper (default python3)
for last in "$@"; do :; done
audio="$last"
[ -n "$audio" ] && [ -f "$audio" ] || { echo "speech-whisper: give the audio file's path as the last argument" >&2; exit 2; }
home="${LIONSBERG_VOICE_HOME:-$HOME/.local/share/lionsberg/voice}"
model="${WHISPER_MODEL:-$home/whisper/ggml-base.en.bin}"
cli="${WHISPER_CLI:-$(command -v whisper-cli 2>/dev/null)}"
py="${WHISPER_PYTHON:-python3}"

if [ -n "$cli" ] && [ -x "$cli" ] && [ -f "$model" ] && command -v ffmpeg >/dev/null 2>&1; then
  wav=$(mktemp "${TMPDIR:-/tmp}/heard-XXXXXX") || exit 1
  trap 'rm -f "$wav" "$wav.wav"' EXIT
  ffmpeg -nostdin -loglevel error -y -i "$audio" -ar 16000 -ac 1 -c:a pcm_s16le -f wav "$wav.wav" || exit 1
  "$cli" -m "$model" -f "$wav.wav" -nt -np 2>/dev/null | sed -e 's/^[[:space:]]*//' -e '/^$/d' | tr '\n' ' ' | sed 's/[[:space:]]*$//'
  echo
  exit 0
fi

if "$py" -c "import faster_whisper" >/dev/null 2>&1; then
  exec "$py" - "$audio" "${FASTER_WHISPER_MODEL:-base.en}" <<'PY'
import sys
from faster_whisper import WhisperModel
audio, name = sys.argv[1], sys.argv[2]
segments, _ = WhisperModel(name, device="cpu", compute_type="int8").transcribe(audio, vad_filter=True)
print(" ".join(s.text.strip() for s in segments).strip())
PY
fi

echo "speech-whisper: no ears here yet; install whisper.cpp and ffmpeg with a model at $model (about 150 MB), or python3 -m pip install faster-whisper; see skills/voice-mode/SKILL.md" >&2
exit 3
