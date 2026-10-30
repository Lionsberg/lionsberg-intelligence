#!/bin/sh
# voice-kokoro.sh: a warm mouth. serve.py's --voice contract: the text is the LAST argument; a new WAV
# file is written and its path printed on the last line of stdout, exit 0, within 60 seconds. It never
# plays the sound; the page that asked plays it. Runs on this computer's CPU only.
#   serve.py --voice "sh hud/voice/voice-kokoro.sh"
# Kokoro-82M (weights Apache-2.0) through kokoro-onnx (MIT). The setup: skills/voice-mode/SKILL.md.
#   LIONSBERG_VOICE_HOME   where the models live (default ~/.local/share/lionsberg/voice)
#   KOKORO_DIR             the folder holding kokoro-v1.0.onnx and voices-v1.0.bin (default $LIONSBERG_VOICE_HOME/kokoro)
#   KOKORO_VOICE           the voice (default af_heart)   KOKORO_SPEED  (default 1.0)
#   KOKORO_PYTHON          the Python that has kokoro-onnx (default python3)
for last in "$@"; do :; done
text="$last"
[ -n "$text" ] || { echo "voice-kokoro: give the words as the last argument" >&2; exit 2; }
home="${LIONSBERG_VOICE_HOME:-$HOME/.local/share/lionsberg/voice}"
dir="${KOKORO_DIR:-$home/kokoro}"
py="${KOKORO_PYTHON:-python3}"
if [ ! -f "$dir/kokoro-v1.0.onnx" ] || [ ! -f "$dir/voices-v1.0.bin" ] || ! "$py" -c "import kokoro_onnx" >/dev/null 2>&1; then
  echo "voice-kokoro: no Kokoro here yet; install with python3 -m pip install kokoro-onnx and put kokoro-v1.0.onnx and voices-v1.0.bin (about 340 MB) in $dir; see skills/voice-mode/SKILL.md" >&2
  exit 3
fi
out=$(mktemp "${TMPDIR:-/tmp}/her-voice-XXXXXX") || exit 1
rm -f "$out"
"$py" - "$dir" "${KOKORO_VOICE:-af_heart}" "${KOKORO_SPEED:-1.0}" "$out.wav" "$text" <<'PY' >&2 || exit 1
import sys, wave
import numpy as np
from kokoro_onnx import Kokoro
d, voice, speed, out, text = sys.argv[1:6]
samples, rate = Kokoro(f"{d}/kokoro-v1.0.onnx", f"{d}/voices-v1.0.bin").create(text, voice=voice, speed=float(speed), lang="en-us")
pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767).astype("<i2").tobytes()
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
PY
echo "$out.wav"
