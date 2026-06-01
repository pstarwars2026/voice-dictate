# Voice Dictate

**Free, offline, on-device voice-to-text for macOS.** Hold a key, speak, release — polished text appears wherever your cursor is.

A private alternative to [Superwhisper](https://superwhisper.com) ($8/mo) and [Wispr Flow](https://wisprflow.com) ($15/mo) that runs 100% locally on your Mac.

https://github.com/user-attachments/assets/placeholder-demo.mp4

## Features

- 🎙️ **Hold-to-record** — Hold Right ⌘, speak, release. Text pastes instantly.
- 🧠 **Smart rephrasing** — Fixes grammar, removes filler words ("um", "uh", "like"), polishes output
- 🔒 **Fully offline** — No cloud, no API calls, no data leaves your machine
- 🌏 **Multilingual** — Speak Hindi, Hinglish, or 35+ languages → clean English output
- 💻 **Technical term preservation** — Keeps API names, function names, code keywords intact
- ⚡ **Apple Silicon optimized** — Runs on Metal GPU via MLX at ~37 tokens/sec
- 🪶 **Lightweight** — 0% CPU when idle, sits quietly in your menubar
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
Look for 🎙️ in your menubar:
- **🎙️** = Ready (hold hotkey to record)
- **🔴** = Recording
- **⚡** = Processing
- Click → **Test Record (5s)** for quick test without hotkey

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

Edit `voice_dictate.py` to customize the rephrasing prompt:

```python
# For raw transcription only (no rephrasing):
TRANSCRIBE_PROMPT = "Transcribe this audio exactly as spoken."

# For code-focused dictation:
TRANSCRIBE_PROMPT = "Transcribe this as a coding instruction. Preserve all technical terms."
```

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
Same issue — Accessibility permission is missing or granted to the wrong binary. Check `stderr` output for `"This process is not trusted"`:
```bash
cat /tmp/voicecode.err
```

### Model not loading
Ensure you have ~6 GB free RAM and ~5.5 GB free disk space.

### No audio recording
Check **Microphone** permission and that no other app is using the mic.

### Duplicate instances
Voice Dictate uses a PID lock — only one instance runs at a time. If it crashes, run:
```bash
rm -f /tmp/voice_dictate.pid
```

## Acknowledgments

- [Gemma 4](https://ai.google.dev/gemma) by Google — subject to [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
- [MLX](https://github.com/ml-explore/mlx) by Apple
- [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) by Prince Canuma
- [rumps](https://github.com/jaredks/rumps) by Jared Suttles

## License

Apache 2.0 — see [LICENSE](LICENSE)
