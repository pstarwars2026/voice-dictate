#!/usr/bin/env python3
"""Offline macOS dictation with serialized inference and persisted preferences."""

import argparse
import atexit
import fcntl
import os
from pathlib import Path
import queue
import tempfile
import time
import wave
from dataclasses import replace

from dictation_core import (
    ClipboardDelivery, DictationController, HOTKEYS, MODES, SAMPLE_RATE, VERSION,
    instance_lock_path, load_settings, save_settings, settings_path,
)
from usage_quota import DailyQuota, KeychainStore


class MLXBackend:
    def __init__(self, model_id):
        self.model_id = model_id

    def load(self):
        from mlx_vlm import load
        self.model, self.processor = load(self.model_id)

    def transcribe(self, blocks, prompt):
        import numpy as np
        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template

        audio = np.concatenate(blocks)
        # Reject absent signals before a generative model can invent a transcript.
        if not audio.size or float(np.max(np.abs(audio))) <= 1e-5:
            return ""
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        fd, path = tempfile.mkstemp(prefix="voice-dictate-", suffix=".wav")
        os.close(fd)
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(SAMPLE_RATE)
                output.writeframes(pcm.tobytes())
            formatted = apply_chat_template(
                self.processor, self.model.config, prompt, num_images=0, num_audios=1,
            )
            result = generate(self.model, self.processor, formatted,
                              audio=path, max_tokens=2048, verbose=False)
            return result.text if hasattr(result, "text") else str(result)
        finally:
            os.unlink(path)


def ensure_single_instance():
    directory = instance_lock_path().parent
    directory.mkdir(parents=True, exist_ok=True)
    handle = open(instance_lock_path(), "a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise SystemExit("Voice Dictate is already running")
    # Keep the inode stable so concurrent launches always lock the same file.
    atexit.register(handle.close)
    return handle


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"Voice Dictate Free {VERSION}")
    parser.add_argument("--hotkey", choices=HOTKEYS)
    parser.add_argument("--model")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--output", choices=("paste", "copy"))
    parser.add_argument("--microphone", help="Exact input device name")
    parser.add_argument("--max-seconds", type=int, help="Recording limit, 5 to 30 seconds")
    parser.add_argument("--config", type=Path, default=settings_path())
    parser.add_argument("--save", action="store_true", help="Save command-line preferences")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        settings = load_settings(args.config)
        overrides = {key: value for key, value in vars(args).items()
                     if key not in ("config", "save") and value is not None}
        settings = replace(settings, **overrides).validate()
        if args.save:
            save_settings(settings, args.config)
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(f"Cannot read/save settings at {args.config}: {error}")

    instance_lock = ensure_single_instance()
    os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    import rumps
    import sounddevice as sd
    from pynput import keyboard
    from AppKit import (NSWorkspace, NSPasteboard, NSPasteboardItem,
                        NSPasteboardTypeString, NSEventTrackingRunLoopMode)
    from Foundation import NSData, NSRunLoop, NSRunLoopCommonModes

    keys = {
        "cmd_r": keyboard.Key.cmd_r, "cmd_l": keyboard.Key.cmd,
        "f5": keyboard.Key.f5, "f6": keyboard.Key.f6,
        "alt_r": keyboard.Key.alt_r, "ctrl_r": keyboard.Key.ctrl_r,
    }

    def frontmost():
        application = NSWorkspace.sharedWorkspace().frontmostApplication()
        return int(application.processIdentifier()) if application else None

    class Clipboard:
        def __init__(self):
            self.board = NSPasteboard.generalPasteboard()

        def snapshot(self):
            items = []
            for item in self.board.pasteboardItems() or []:
                contents = {}
                for kind in item.types():
                    data = item.dataForType_(kind)
                    if data is not None:
                        contents[str(kind)] = bytes(data)
                items.append(contents)
            return items

        def write(self, text):
            self.board.clearContents()
            if not self.board.setString_forType_(text, NSPasteboardTypeString):
                raise RuntimeError("Clipboard write failed")
            return self.revision()

        def revision(self):
            return int(self.board.changeCount())

        def restore(self, items):
            restored = []
            for contents in items:
                item = NSPasteboardItem.alloc().init()
                for kind, data in contents.items():
                    item.setData_forType_(NSData.dataWithBytes_length_(data, len(data)), kind)
                restored.append(item)
            self.board.clearContents()
            if restored:
                self.board.writeObjects_(restored)

    def paste():
        from ApplicationServices import AXIsProcessTrusted
        if not AXIsProcessTrusted():
            raise RuntimeError("Accessibility permission missing")
        controller = keyboard.Controller()
        with controller.pressed(keyboard.Key.cmd):
            controller.press("v")
            controller.release("v")

    def recorder_factory(buffer, microphone):
        device = None
        if microphone is not None:
            matches = [index for index, entry in enumerate(sd.query_devices())
                       if entry["name"] == microphone and entry["max_input_channels"] > 0]
            if not matches:
                raise RuntimeError("Saved microphone disconnected")
            device = matches[0]
        return sd.InputStream(
            device=device, samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            callback=lambda data, frames, timestamp, status: buffer.append(data[:, 0], status),
        )

    class VoiceDictateApp(rumps.App):
        def __init__(self):
            super().__init__("VD", quit_button=None)
            self.events = queue.SimpleQueue()
            self.held = set()
            self.active_key = None
            self.suppress_until = 0
            self.quitting = False
            self.clipboard = ClipboardDelivery(Clipboard(), frontmost, paste)
            self.controller = DictationController(
                MLXBackend(settings.model), recorder_factory, self.deliver, settings,
                quota=DailyQuota(KeychainStore(), settings_path().parent / "usage.lock"),
            )
            self.status_item = rumps.MenuItem("Loading model...")
            self.usage_item = rumps.MenuItem("Free: 30s per recording, 5min per day (UTC)")
            self.mode_menu = rumps.MenuItem("Mode")
            self.hotkey_menu = rumps.MenuItem("Hotkey")
            self.microphone_menu = rumps.MenuItem("Microphone")
            self.output_menu = rumps.MenuItem("Output")
            self.limit_menu = rumps.MenuItem("Recording limit")
            self.restore_item = rumps.MenuItem("Restore clipboard after paste", callback=self.toggle_restore)
            self.menu = [self.status_item, self.usage_item, None, self.mode_menu, self.hotkey_menu,
                         self.microphone_menu, self.output_menu, self.limit_menu, self.restore_item,
                         None, rumps.MenuItem("Test Record (5s, copy only)", callback=self.test_record),
                         rumps.MenuItem("Cancel", callback=lambda _: self.controller.cancel()),
                         rumps.MenuItem("Retry model load", callback=lambda _: self.controller.retry_load()),
                         rumps.MenuItem("Quit Voice Dictate", callback=self.quit)]
            self.preferences = []
            for menu, field, choices in (
                (self.mode_menu, "mode", MODES), (self.hotkey_menu, "hotkey", HOTKEYS),
                (self.output_menu, "output", {"paste": "Paste", "copy": "Copy only"}),
                (self.limit_menu, "max_seconds", {15: "15 seconds", 30: "30 seconds"}),
            ):
                for value, label in choices.items():
                    item = rumps.MenuItem(label, callback=lambda _, f=field, v=value: self.set_preference(f, v))
                    menu.add(item)
                    self.preferences.append((item, field, value))
            self.refresh_microphones(None)
            self.update_preferences()
            self.listener = keyboard.Listener(
                on_press=lambda key: self.events.put(("press", key)),
                on_release=lambda key: self.events.put(("release", key)),
            )
            self.listener.start()
            self.timer = rumps.Timer(self.tick, 0.05)
            self.timer.start()
            # rumps 0.4 registers only the default mode; keep limits and feedback live in menus.
            NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer._nstimer, NSRunLoopCommonModes)

        def update_preferences(self):
            for item, field, value in self.preferences:
                item.state = getattr(self.controller.settings, field) == value
            self.restore_item.state = self.controller.settings.restore_clipboard

        def set_preference(self, field, value):
            candidate = replace(self.controller.settings, **{field: value})
            try:
                save_settings(candidate, args.config)
            except (OSError, ValueError) as error:
                rumps.alert("Could not save preferences", str(error))
                return
            self.controller.settings = candidate
            self.update_preferences()

        def toggle_restore(self, _):
            self.set_preference("restore_clipboard", not self.controller.settings.restore_clipboard)

        def refresh_microphones(self, _):
            self.preferences = [row for row in self.preferences if row[1] != "microphone"]
            if len(self.microphone_menu):
                self.microphone_menu.clear()
            names = {None: "System default"}
            try:
                for device in sd.query_devices():
                    if device["max_input_channels"] > 0:
                        names[device["name"]] = device["name"]
            except Exception:
                self.controller.message = "Unable to list microphones"
            saved = self.controller.settings.microphone
            if saved and saved not in names:
                names[saved] = saved + " (disconnected)"
            for value, label in names.items():
                item = rumps.MenuItem(label, callback=lambda _, v=value: self.set_preference("microphone", v))
                self.microphone_menu.add(item)
                self.preferences.append((item, "microphone", value))
            self.microphone_menu.add(rumps.MenuItem("Refresh devices", callback=self.refresh_microphones))
            self.update_preferences()

        def test_record(self, _):
            self.controller.start(seconds=5, copy_only=True)

        def deliver(self, text, target, session_settings):
            modifiers = {keyboard.Key.cmd, keyboard.Key.cmd_r, keyboard.Key.shift,
                         keyboard.Key.shift_r, keyboard.Key.alt, keyboard.Key.alt_r,
                         keyboard.Key.ctrl, keyboard.Key.ctrl_r}
            if self.held & modifiers or NSRunLoop.currentRunLoop().currentMode() == NSEventTrackingRunLoopMode:
                session_settings = replace(session_settings, output="copy")
            # Synthetic Cmd+V must not start a new session when Left Command is the hotkey.
            self.suppress_until = time.monotonic() + 0.3
            return self.clipboard.deliver(text, target, session_settings)

        def tick(self, _):
            if self.quitting:
                if self.controller.future is not None and not self.controller.future.done():
                    self.status_item.title = "Quitting; waiting for model cleanup..."
                    return
                self.timer.stop()
                self.clipboard.tick(force=True)
                rumps.quit_application()
                return
            while not self.events.empty():
                event, key = self.events.get()
                if event == "release":
                    self.held.discard(key)
                    if key == self.active_key:
                        self.controller.stop()
                        self.active_key = None
                elif key not in self.held:
                    if time.monotonic() < self.suppress_until:
                        continue
                    self.held.add(key)
                    if key == keyboard.Key.esc:
                        self.controller.cancel()
                    elif key == keys[self.controller.settings.hotkey]:
                        if self.controller.start(target=frontmost()):
                            self.active_key = key
            self.controller.tick()
            self.clipboard.tick()
            remaining = self.controller.remaining_seconds
            if remaining is not None:
                self.usage_item.title = f"Free allowance: {remaining // 60}m {remaining % 60:02d}s unreserved (resets 00:00 UTC)"
            state = self.controller.state
            self.title = {"recording": "REC", "processing": "...", "loading": "...", "error": "!"}.get(state, "VD")
            if state == "recording":
                buffer = self.controller.buffer
                level = min(10, int(buffer.level * 50))
                self.status_item.title = f"Recording {buffer.duration:.1f}s  [{'|' * level}{'.' * (10 - level)}]"
            else:
                self.status_item.title = self.controller.message
            if not self.listener.running and state == "ready":
                self.status_item.title = "Hotkey listener stopped; check Input Monitoring and restart"

        def quit(self, _):
            if self.quitting:
                return
            self.quitting = True
            self.listener.stop()
            self.controller.close()
            self.tick(None)

    app = VoiceDictateApp()
    try:
        app.run()
    finally:
        app.controller.close()
        instance_lock.close()


if __name__ == "__main__":
    main()
