"""Settings and recording lifecycle, independent of macOS UI and MLX."""

import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace


DEFAULT_MODEL = "mlx-community/gemma-4-e4b-it-4bit"
VERSION = "2.0.0"
SAMPLE_RATE = 16000
MODES = {
    "verbatim": "Verbatim",
    "polished": "Polished English",
    "original": "Keep Original Language",
    "developer": "Developer",
}
HOTKEYS = {
    "cmd_r": "Right Command", "cmd_l": "Left Command",
    "f5": "F5", "f6": "F6", "alt_r": "Right Option",
    "ctrl_r": "Right Control",
}
PROMPTS = {
    "verbatim": "Transcribe exactly as spoken in the original language(s). Preserve filler words, repetitions, and wording. Do not translate or polish.",
    "polished": "Translate the speech into English and rewrite it in clear, natural English, fixing grammar without changing meaning or intent. Remove ALL hesitation sounds (um, uh, er), including at the beginning of the sentence. Begin directly with the meaningful content. The final output MUST be entirely in English regardless of the language spoken. Return only the edited English text.",
    "original": "Produce a cleaned-up dictation in the original language(s), preserving code-switching. Improve punctuation without translating or changing meaning. Remove ALL hesitation sounds (um, uh, er), including at the beginning of the sentence. Begin directly with the meaningful content. Return only the edited text.",
    "developer": "Transcribe as a clear developer instruction in English. Remove filler words, but preserve technical identifiers, paths, URLs, commands, numbers, and library names. Do not execute instructions or invent code.",
}


def prompt_for(mode):
    return PROMPTS[mode] + " Preserve names and technical terms. Output only the transcript, no preamble. For silence or unintelligible audio output nothing."


@dataclass(frozen=True)
class Settings:
    mode: str = "polished"
    hotkey: str = "cmd_r"
    model: str = DEFAULT_MODEL
    microphone: str | None = None
    output: str = "paste"
    restore_clipboard: bool = True
    max_seconds: int = 30

    def validate(self):
        if self.mode not in MODES or self.hotkey not in HOTKEYS:
            raise ValueError("Unknown dictation mode or hotkey")
        if self.output not in ("paste", "copy"):
            raise ValueError("Output must be paste or copy")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model must be a nonempty model ID")
        if self.microphone is not None and not isinstance(self.microphone, str):
            raise ValueError("Microphone must be a device name")
        if type(self.restore_clipboard) is not bool:
            raise ValueError("restore_clipboard must be true or false")
        if type(self.max_seconds) is not int or not 5 <= self.max_seconds <= 120:
            raise ValueError("Recording limit must be 5 to 120 seconds")
        return self


def settings_path():
    return Path.home() / "Library/Application Support/Voice Dictate/settings.json"


def load_settings(path):
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return Settings()
    if not isinstance(data, dict):
        raise ValueError("Settings must be a JSON object")
    return Settings(**data).validate()


def save_settings(settings, path):
    settings.validate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(asdict(settings), stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class AudioBuffer:
    """Cap actual sample counts; callbacks never manipulate UI or stop streams."""

    def __init__(self, seconds, sample_rate=SAMPLE_RATE):
        self.limit = int(seconds * sample_rate)
        self.sample_rate = sample_rate
        self.count = 0
        self.blocks = []
        self.level = 0.0
        self.error = None
        self.lock = threading.Lock()

    def append(self, samples, status=None):
        with self.lock:
            if status:
                self.error = "Audio input overflow or device error"
            remaining = self.limit - self.count
            if remaining <= 0:
                return
            block = samples[:remaining].copy()
            self.blocks.append(block)
            self.count += len(block)
            if len(block):
                self.level = min(1.0, math.sqrt(sum(float(x) ** 2 for x in block) / len(block)))

    @property
    def duration(self):
        return self.count / self.sample_rate

    @property
    def full(self):
        return self.count >= self.limit


class DictationController:
    """Public methods run on the UI thread; only inference runs on the worker."""

    def __init__(self, backend, recorder_factory, deliver, settings=None, clock=time.monotonic):
        self.backend = backend
        self.recorder_factory = recorder_factory
        self.deliver = deliver
        self.settings = settings or Settings()
        self.clock = clock
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictation")
        self.state = "loading"
        self.message = "Loading model..."
        self.future = self.executor.submit(backend.load)
        self.recorder = None
        self.buffer = None
        self.cancelled = False
        self.closed = False

    def retry_load(self):
        if self.state == "error":
            self.state = "loading"
            self.message = "Loading model..."
            self.future = self.executor.submit(self.backend.load)

    def start(self, target=None, seconds=None, copy_only=False):
        if self.state != "ready" or self.closed:
            return False
        self.session_settings = replace(self.settings, output="copy") if copy_only else self.settings
        self.target = target
        self.buffer = AudioBuffer(seconds or self.settings.max_seconds)
        self.started = self.clock()
        self.cancelled = False
        try:
            self.recorder = self.recorder_factory(self.buffer, self.settings.microphone)
            self.recorder.start()
        except Exception:
            self._close_recorder()
            self.message = "Microphone unavailable. Check device and Microphone permission."
            return False
        self.state = "recording"
        self.message = "Recording..."
        return True

    def _close_recorder(self):
        recorder, self.recorder = self.recorder, None
        if recorder is not None:
            try:
                recorder.stop()
            except Exception:
                pass
            finally:
                try:
                    recorder.close()
                except Exception:
                    pass

    def stop(self, cancel=False):
        if self.state != "recording":
            return
        self.state = "stopping"
        self._close_recorder()
        if cancel or self.buffer.error or self.buffer.duration < 0.3:
            self.state = "ready"
            self.message = ("Cancelled" if cancel else self.buffer.error or "Recording too short")
            self.buffer.blocks.clear()
            return
        blocks, self.buffer.blocks = self.buffer.blocks, []
        self.state = "processing"
        self.message = "Processing..."
        self.future = self.executor.submit(self.backend.transcribe, blocks, prompt_for(self.session_settings.mode))

    def cancel(self):
        if self.state == "recording":
            self.stop(cancel=True)
        elif self.state == "processing":
            self.cancelled = True
            self.message = "Cancelling; waiting for model to finish..."

    def tick(self):
        if self.closed:
            return
        if self.state == "recording":
            if self.buffer.full or self.buffer.error or self.clock() - self.started >= self.buffer.limit / SAMPLE_RATE:
                self.stop()
        if self.future is None or not self.future.done():
            return
        future, self.future = self.future, None
        loading = self.state == "loading"
        try:
            result = future.result()
            if loading:
                self.message = "Ready"
            elif self.cancelled:
                self.message = "Cancelled"
            elif result and result.strip() and result.strip().lower() not in ("...", "the audio is not provided"):
                self.message = self.deliver(result.strip(), self.target, self.session_settings)
            else:
                self.message = "No speech detected"
            self.state = "ready"
        except Exception:
            self.state = "error" if loading else "ready"
            self.message = ("Model load failed. Check model ID, download access, and free memory; retry from menu."
                            if loading else "Transcription or output failed. Check model and Accessibility permission.")

    def close(self):
        self.cancel()
        self.closed = True
        self._close_recorder()
        self.executor.shutdown(wait=False, cancel_futures=True)


class ClipboardDelivery:
    """Preserve every pasteboard type and restore only if our write is unchanged."""

    def __init__(self, clipboard, frontmost, paste, clock=time.monotonic):
        self.clipboard = clipboard
        self.frontmost = frontmost
        self.paste = paste
        self.clock = clock
        self.pending = None

    def deliver(self, text, target, settings):
        if self.pending:
            self.tick(force=True)
        previous = self.clipboard.snapshot() if settings.restore_clipboard else None
        revision = self.clipboard.write(text)
        if settings.output == "copy":
            return "Copied to clipboard"
        if target is None or self.frontmost() != target:
            return "App changed; copied only"
        try:
            self.paste()
        except Exception:
            return "Paste unavailable; copied only"
        if previous is not None:
            self.pending = (self.clock() + 0.8, revision, previous)
        return "Paste requested"

    def tick(self, force=False):
        if self.pending and (force or self.clock() >= self.pending[0]):
            _, revision, previous = self.pending
            self.pending = None
            if self.clipboard.revision() == revision:
                self.clipboard.restore(previous)
