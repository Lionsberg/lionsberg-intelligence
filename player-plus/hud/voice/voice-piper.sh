#!/bin/sh
# voice-piper.sh: a light mouth for a slower computer. serve.py's --voice contract: the text is the LAST
# argument; a new WAV file is written and its path printed on the last line of stdout, exit 0, within 60
# seconds. It never plays the sound. Runs on this computer's CPU only.
#   serve.py --voice "sh hud/voice/voice-piper.sh"
# Piper (piper-tts; GPL-3.0 since its move to the Open Home Foundation; each voice has its own licence in
# its model card). The setup: skills/voice-mode/SKILL.md.
#   LIONSBERG_VOICE_HOME   where the models live (default ~/.local/share/lionsberg/voice)
#   PIPER_MODEL            a voice's .onnx file, its .onnx.json beside it (default $LIONSBERG_VOICE_HOME/piper/en_US-lessac-medium.onnx)
#   PIPER                  the piper program (default: piper on PATH, else python3 -m piper)
for last in "$@"; do :; done
text="$last"
[ -n "$text" ] || { echo "voice-piper: give the words as the last argument" >&2; exit 2; }
home="${LIONSBERG_VOICE_HOME:-$HOME/.local/share/lionsberg/voice}"
model="${PIPER_MODEL:-$home/piper/en_US-lessac-medium.onnx}"
if [ -n "$PIPER" ]; then run="$PIPER"
elif command -v piper >/dev/null 2>&1; then run="piper"
elif python3 -c "import piper" >/dev/null 2>&1; then run="python3 -m piper"
else run=""; fi
if [ -z "$run" ] || [ ! -f "$model" ] || [ ! -f "$model.json" ]; then
  echo "voice-piper: no Piper here yet; install with python3 -m pip install piper-tts and put a voice (.onnx and .onnx.json, about 60 MB) at $model; see skills/voice-mode/SKILL.md" >&2
  exit 3
fi
out=$(mktemp "${TMPDIR:-/tmp}/her-voice-XXXXXX") || exit 1
rm -f "$out"
printf '%s\n' "$text" | $run -m "$model" -f "$out.wav" >/dev/null 2>&1 || exit 1
echo "$out.wav"
