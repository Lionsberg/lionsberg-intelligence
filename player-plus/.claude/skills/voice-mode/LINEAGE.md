# Lineage — `voice-mode`

This skill travels alone, so it carries its own lineage, credits and licence. If you copy the folder, copy this file with it; if you make your own version, set `name`, `version` and `grows_from` to your own and move this one to the top of `lineage`.

```yaml
name: voice-mode
version: 0.1.0
grows_from: LIØNSBERG Player+ 3.7 (the Talk)
lineage:
  - "hud/serve.py, the layered voice: the --speech and --voice contracts, and the phone door that speaks TLS"
  - "hud/DESIGN-DOCK.md, the layered voice and the earpiece rule (voice, then words, then the card; nothing is voice-only)"
  - "hud/DESIGN-PHONE-DOOR.md (why a phone needs a secure page for its microphone, and what trusting this computer means)"
  - "the speech ruling (DESIGN-ROOM §1): what is said is said; only what a person agrees enters the record"
licence: MPL-2.0                          # LICENSE.md in this folder
credits:
  - "whisper.cpp (MIT) and faster-whisper (MIT), the ears"
  - "Kokoro-82M (Apache-2.0 weights) through kokoro-onnx (MIT), and Piper (GPL-3.0), the mouths"
needs: Claude Code with skills enabled; the kit's hud/serve.py and hud/voice/; installed at <agent home>/.claude/skills/voice-mode/
changes: 0.1.0 — first release: natural voice on an ordinary Mac or Windows computer, no newest chip required
thanks_to: "the open speech and voice projects named above"   # a practice, never a debt
```
