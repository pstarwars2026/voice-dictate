# Voice Dictate

**Free, offline, on-device voice-to-text for macOS.** Hold a key, speak, release — polished text appears wherever your cursor is.

A private alternative to [Superwhisper](https://superwhisper.com) ($8/mo) and [Wispr Flow](https://wisprflow.com) ($15/mo) that runs 100% locally on your Mac.

## Features

- 🎙️ **Hold-to-record** — Hold Right ⌘, speak, release. Text is inserted after processing.
- 🧠 **Smart rephrasing** — Fixes grammar, removes filler words ("um", "uh", "like"), polishes output
- 🔒 **Fully offline** — No cloud, no API calls, no data leaves your machine
- 🌏 **Multilingual** — Speak Hindi, Hinglish, or 35+ languages → clean English output
- 💻 **Technical term preservation** — Keeps API names, function names, code keywords intact
- ⚡ **Apple Silicon optimized** — Runs on Metal GPU via MLX at ~37 tokens/sec
- 🪶 **Menubar controls** — Saved modes, hotkeys, microphone selection, and output preferences
- 🆓 **Free forever** — No subscription, no account, no telemetry

## How It Works

```
Hold ⌘R → 🎤 Record → Release → ⚡ Gemma 4 → 📋 Paste
```

One model ([Gemma 4 E4B](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit)) handles everything — speech recognition AND intelligent rephrasing in a single pass. No separate Whisper model needed.

## Requirements

- macOS on **Apple Silicon** (M1/M2/M3/M4)
- Python 3.10+
- ~6 GB RAM (for the model)
- ~5.5 GB disk (model downloads on first run)

## Install

```bash
# Clone
git clone https://github.com/pstarwars2026/voice-dictate.git
cd voice-dictate

# Setup (creates venv, installs deps)
chmod +x setup.sh
./setup.sh

# Run
./start.sh
```

## Usage

### Basic
```bash
./start.sh
```

Hold **Right ⌘**, speak, release. Text pastes where your cursor is.

### Custom Hotkey
```bash
./start.sh --hotkey f5       # F5 key
./start.sh --hotkey alt_r    # Right Option
./start.sh --hotkey ctrl_r   # Right Control
```

### Custom Model
```bash
./start.sh --model mlx-community/gemma-4-e4b-it-8bit  # 8-bit (more accurate, more RAM)
```

### Menubar
Look for **VD** in your menubar:
- **VD** = Ready
- **REC** = Recording; open the menu for elapsed audio time and input level
- **...** = Model loading or transcription
- **!** = Model load failed; use **Retry model load** after resolving the cause
- **Test Record (5s, copy only)** records without the hotkey and keeps output on the clipboard

Choose **Mode**, **Hotkey**, **Microphone**, **Output**, and **Recording limit**
from the menu. Changes are saved and apply to the next recording. Use **Refresh
devices** after connecting a microphone. A disconnected saved microphone produces
an error instead of silently switching devices.

### Dictation modes

| Mode | Behavior |
|---|---|
| Verbatim | Preserve spoken wording, filler words, and language(s) |
| Polished English | Translate when needed, remove fillers, improve grammar |
| Keep Original Language | Clean punctuation and fillers without translating |
| Developer | Produce English developer instructions while preserving identifiers and technical terms |

These are model instructions, not guarantees of perfect transcription. Review
important text before sending or executing it.

### Recording and cancellation

One model operation runs at a time. Recording is unavailable while the model loads
or processes audio. The default recording cap is 30 seconds, selectable up to 120.
Press **Escape** or choose **Cancel** to discard a recording or pending transcript.
Cancellation during inference suppresses output; the app waits for the current
model call to finish before accepting another recording.

### Clipboard and insertion

**Paste** inserts into the application active when recording began. If another app
is active when processing finishes, output is copied without pasting. This checks
the application, not the individual field or document; use **Copy only** for full
control over the destination. If a modifier key is still held, output is also copied
only to avoid modified paste shortcuts. Output is copied only while the app's menu is open.

**Restore clipboard after paste** preserves the previous pasteboard items, including
image and rich-text types, and restores them after 0.8 seconds only if the clipboard
has not changed. Paste dispatch cannot confirm that every app consumed the text;
disable restoration for slow apps or use copy-only output. Copy-only output and
failed paste attempts retain the transcript on the clipboard.

The app does not print transcripts or show transcript previews in its status menu.
Temporary audio is deleted after inference, including failures. Forced termination
or a system crash can leave a private temporary WAV file behind.

## Companion Project: Voice Dictate Doctor

Voice Dictate includes a lightweight diagnostics tool for setup and issue triage:

```bash
python tools/voice_dictate_doctor.py
python tools/voice_dictate_doctor.py --json
```

The doctor checks macOS, Apple Silicon, Python, installed dependencies, audio input,
clipboard helpers, model cache space, and the exact Python binary that needs
Accessibility and Input Monitoring permissions. It does not load the model or send
audio anywhere.

## macOS Permissions

On first run, macOS will ask for three permissions. **All three are required** for Voice Dictate to work:

1. **Microphone** — to record audio
2. **Accessibility** — to simulate Cmd+V paste into the active app
3. **Input Monitoring** — to capture the global hotkey

### ⚠️ Important: Add the correct Python binary

macOS permissions are tied to the **specific Python binary**, not the script. If you're using a venv, you must add the **real** Python executable (not the symlink).

Find it with:
```bash
readlink -f .venv/bin/python
# Example output: /opt/homebrew/bin/python3.12
```

Then in **System Settings → Privacy & Security**:
1. Go to **Accessibility** → click **+** → press **Cmd+Shift+G** → paste the path above → Add
2. Go to **Input Monitoring** → same steps
3. Make sure both toggles are ✅ **ON**
4. **Restart** Voice Dictate after granting permissions

## Performance

The figures below are historical observations from the initial implementation,
not benchmarks of this release. Hardware, dependencies and recording length affect results.

| State | CPU | RAM | GPU |
|-------|-----|-----|-----|
| Idle | 0% | ~6 GB | 0% |
| Recording | <1% | ~6 GB | 0% |
| Transcribing | ~50% | ~6 GB | ~80% (Metal) |

- **Cold start:** ~12 seconds (model loading)
- **Inference:** ~3-5 seconds per transcription
- **Model stays in memory** for instant subsequent recordings

## How It's Different

| | Voice Dictate | Superwhisper | Wispr Flow |
|---|---|---|---|
| **Price** | Free | $8/mo | $15/mo |
| **Privacy** | 100% offline | Cloud option | Cloud-based |
| **Rephrasing** | Built-in | Separate step | Built-in |
| **Translation** | Auto (35+ langs) | Limited | Limited |
| **Technical terms** | Preserved | Generic | Generic |
| **Open source** | ✅ | ❌ | ❌ |

## Configuration

Menu changes are saved atomically to
`~/Library/Application Support/Voice Dictate/settings.json` with owner-only file permissions.
Command-line options override saved settings for the current run. Add `--save`
to persist them; subsequent menu changes save the current effective preferences.

```bash
./start.sh --mode verbatim --hotkey f5 --save
./start.sh --mode developer --output copy
./start.sh --microphone "MacBook Pro Microphone" --max-seconds 60 --save
python voice_dictate.py --help
```

Use `--config /path/to/settings.json` for a separate profile. Invalid settings
produce an error without overwriting the file. Model selection remains a command-line
option; changing the model requires a restart. Prompt definitions live in
`dictation_core.py` for contributors implementing additional modes.

## Troubleshooting

### Run the doctor first
```bash
python tools/voice_dictate_doctor.py
```

If you open an issue, include:
```bash
python tools/voice_dictate_doctor.py --json
```

### "This process is not trusted"
The Python binary needs **Accessibility** and **Input Monitoring** permissions. See the [permissions section](#️-important-add-the-correct-python-binary) above. You must add the **real binary** (use `readlink -f .venv/bin/python`), not the symlink.

### Text goes to clipboard but doesn't paste
Check **Output** mode, Accessibility permission, whether you changed applications,
and whether a modifier key was still held when processing completed. Copy-only
fallbacks intentionally leave text on the clipboard for manual insertion.

### Model not loading
Ensure you have ~6 GB free RAM and ~5.5 GB free disk space.

### No audio recording
Check **Microphone** permission and that no other app is using the mic.

### Duplicate instances
Voice Dictate holds an OS file lock at
`~/Library/Application Support/Voice Dictate/instance.lock`. Only one instance runs
at a time. The OS releases the lock when the process exits; do not delete the lock
file while the app runs. Quit any older version before starting this release.

## Acknowledgments

- [Gemma 4](https://ai.google.dev/gemma) by Google — subject to [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
- [MLX](https://github.com/ml-explore/mlx) by Apple
- [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) by Prince Canuma
- [rumps](https://github.com/jaredks/rumps) by Jared Suttles

## License

Apache 2.0 — see [LICENSE](LICENSE)
