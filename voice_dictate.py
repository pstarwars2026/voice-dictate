#!/usr/bin/env python3
"""
Voice Dictate — On-Device Voice-to-Text for macOS
===================================================
Hold a key, speak, release — polished text pastes wherever your cursor is.
Uses Gemma 4 E4B via MLX — fully offline, on-device, private.

Usage:
    python voice_dictate.py
    python voice_dictate.py --hotkey f5
    python voice_dictate.py --model mlx-community/gemma-4-e4b-it-4bit
"""

import os
import sys
import threading
import time
import wave
import tempfile
import fcntl
import atexit
import argparse

PIDFILE = os.path.join(tempfile.gettempdir(), "voice_dictate.pid")

def ensure_single_instance():
    """Exit if another instance is already running."""
    global _pidfile_handle
    _pidfile_handle = open(PIDFILE, "w")
    try:
        fcntl.flock(_pidfile_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _pidfile_handle.write(str(os.getpid()))
        _pidfile_handle.flush()
        atexit.register(_cleanup_pid)
    except IOError:
        print("⚠️  Voice Dictate is already running. Exiting.", flush=True)
        sys.exit(0)

def _cleanup_pid():
    try:
        fcntl.flock(_pidfile_handle, fcntl.LOCK_UN)
        _pidfile_handle.close()
        os.unlink(PIDFILE)
    except Exception:
        pass

# Set HF cache to user-default if not overridden
if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface")

import rumps
import pyperclip
import sounddevice as sd
import numpy as np
from pynput import keyboard

DEFAULT_MODEL = "mlx-community/gemma-4-e4b-it-4bit"
SAMPLE_RATE = 16000
MAX_RECORDING_SECS = 30

# ─── Global state ──────────────────────────────
_model = None
_processor = None
_recording = False
_audio_frames = []
_recording_lock = threading.Lock()
_stream = None
_model_id = DEFAULT_MODEL
_record_key = keyboard.Key.cmd_r
_record_key_name = "Right ⌘"


# ─── Model ─────────────────────────────────────

def load_model():
    global _model, _processor
    if _model is None:
        from mlx_vlm import load
        _model, _processor = load(_model_id)
    return _model, _processor


def preload_model_thread():
    try:
        t0 = time.time()
        load_model()
        dt = time.time() - t0
        app.title = "🎙️"
        app.menu["Status"].title = f"Ready — Hold {_record_key_name} to record ({dt:.1f}s load)"
        print(f"✅ Model loaded in {dt:.1f}s", flush=True)
    except Exception as e:
        app.menu["Status"].title = f"⚠️ Load failed: {e}"
        print(f"❌ Model load failed: {e}", flush=True)


# ─── Audio ─────────────────────────────────────

def _audio_callback(indata, frames, time_info, status):
    if _recording:
        _audio_frames.append(indata.copy())


def save_audio_to_wav(frames, sample_rate=SAMPLE_RATE):
    audio = np.concatenate(frames, axis=0)
    audio_int16 = (audio * 32767).astype(np.int16)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return tmp.name


# ─── Transcription ─────────────────────────────

TRANSCRIBE_PROMPT = (
    "Listen to this audio carefully. The speaker may have grammar mistakes, "
    "filler words, or speak in a mix of languages (e.g. English and Hindi). "
    "Your job is to: "
    "1. Transcribe what was said. "
    "2. Rephrase it into clear, natural, grammatically correct English. "
    "3. Remove all filler words (um, uh, like, you know, sort of, basically, okay so). "
    "4. Fix grammar mistakes while preserving the original meaning and intent. "
    "5. Use proper punctuation and capitalization. "
    "6. PRESERVE all technical terms exactly as spoken: API names, function names, "
    "variable names, library names, programming keywords, file paths, URLs, "
    "model names, framework names, and any code-related terminology. "
    "Never rephrase or simplify technical terms. "
    "Output ONLY the final polished English text. No explanations, no preamble."
)


def transcribe_and_paste(audio_path):
    try:
        app.title = "⚡"
        app.menu["Status"].title = "Processing..."
        print("⚡ Transcribing...", flush=True)

        model, processor = load_model()
        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template

        formatted = apply_chat_template(
            processor, model.config, TRANSCRIBE_PROMPT,
            num_images=0, num_audios=1
        )

        result = generate(
            model, processor, formatted,
            audio=audio_path,
            max_tokens=512, verbose=False
        )
        text = result.text if hasattr(result, "text") else str(result)
        text = text.strip()

        if text and text.lower() not in ("", "...", "the audio is not provided"):
            pyperclip.copy(" " + text)  # Leading space separates from previous text
            paste_into_active_app()
            short = text[:60] + ("..." if len(text) > 60 else "")
            app.menu["Status"].title = f"✅ {short}"
            print(f"📝 {text}", flush=True)
        else:
            app.menu["Status"].title = "⚠️ No speech detected"
            print("⚠️ No speech detected", flush=True)

    except Exception as e:
        app.menu["Status"].title = f"⚠️ {str(e)[:50]}"
        print(f"❌ Error: {e}", flush=True)
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass
        app.title = "🎙️"


def paste_into_active_app():
    from pynput.keyboard import Controller, Key
    kb = Controller()
    time.sleep(0.15)
    with kb.pressed(Key.cmd):
        kb.press("v")
        kb.release("v")


# ─── Hotkey listener ────────────────────────────

def on_press(key):
    global _recording, _audio_frames, _stream
    if key == _record_key and not _recording:
        with _recording_lock:
            _recording = True
            _audio_frames = []
        app.title = "🔴"
        app.menu["Status"].title = f"🔴 Recording... (release {_record_key_name} to stop)"
        print("🔴 Recording...", flush=True)
        _stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=_audio_callback,
        )
        _stream.start()


def on_release(key):
    global _recording, _stream
    if key == _record_key and _recording:
        with _recording_lock:
            _recording = False
        if _stream:
            _stream.stop()
            _stream.close()
            _stream = None

        frames = list(_audio_frames)
        duration = len(frames) * 1024 / SAMPLE_RATE if frames else 0
        print(f"⏹️ Stopped. {duration:.1f}s recorded.", flush=True)

        if len(frames) > 5:  # At least ~0.3s of audio
            audio_path = save_audio_to_wav(frames)
            threading.Thread(
                target=transcribe_and_paste, args=(audio_path,), daemon=True
            ).start()
        else:
            app.title = "🎙️"
            app.menu["Status"].title = f"Ready — Hold {_record_key_name} to record"
            print("⚠️ Too short, skipped.", flush=True)


def start_hotkey_listener():
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()


# ─── Menubar App ───────────────────────────────

class VoiceDictateApp(rumps.App):
    def __init__(self):
        super().__init__("⏳", quit_button="Quit Voice Dictate")
        self.menu = [
            rumps.MenuItem("Status"),
            None,
            rumps.MenuItem("Test Record (5s)", callback=self.test_record),
        ]
        self.menu["Status"].title = "Loading model..."

    def test_record(self, _):
        """Quick 5-second test without needing the hotkey."""
        threading.Thread(target=self._do_test_record, daemon=True).start()

    def _do_test_record(self):
        self.title = "🔴"
        self.menu["Status"].title = "🔴 Test recording for 5s..."
        print("🔴 Test recording 5s...", flush=True)

        audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="int16")
        sd.wait()
        print("⏹️ Test recording done.", flush=True)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())

        transcribe_and_paste(tmp.name)


# ─── CLI ────────────────────────────────────────

HOTKEY_MAP = {
    "cmd_r": (keyboard.Key.cmd_r, "Right ⌘"),
    "cmd_l": (keyboard.Key.cmd, "Left ⌘"),
    "f5": (keyboard.Key.f5, "F5"),
    "f6": (keyboard.Key.f6, "F6"),
    "alt_r": (keyboard.Key.alt_r, "Right ⌥"),
    "ctrl_r": (keyboard.Key.ctrl_r, "Right ⌃"),
}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Voice Dictate — On-device voice-to-text for macOS"
    )
    parser.add_argument(
        "--hotkey", default="cmd_r",
        choices=HOTKEY_MAP.keys(),
        help="Recording hotkey (default: cmd_r)"
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"MLX model ID (default: {DEFAULT_MODEL})"
    )
    return parser.parse_args()


app = VoiceDictateApp()


if __name__ == "__main__":
    args = parse_args()

    _model_id = args.model
    _record_key, _record_key_name = HOTKEY_MAP[args.hotkey]

    ensure_single_instance()

    print("=" * 50)
    print("🎙️  Voice Dictate — Gemma 4 E4B on MLX")
    print(f"   Hold {_record_key_name} to record, release to paste")
    print("   Or use menubar → Test Record (5s)")
    print("=" * 50)
    print()

    start_hotkey_listener()
    threading.Thread(target=preload_model_thread, daemon=True).start()
    app.run()
