"""Real Cocoa menu wiring with model, microphone and global input hooks replaced."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import Future
from unittest.mock import Mock, patch


@unittest.skipUnless(sys.platform == "darwin" and importlib.util.find_spec("rumps"),
                     "Requires macOS UI dependencies")
class NativeMenuTests(unittest.TestCase):
    def test_preferences_refresh_and_hotkey_delivery(self):
        import rumps
        from pynput import keyboard
        import voice_dictate
        from dictation_core import load_settings
        from AppKit import NSPasteboard, NSPasteboardTypeString

        class Backend:
            def __init__(self, model):
                pass

            def load(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            config = str(Path(root) / "settings.json")

            def inspect(app):
                try:
                    app.controller.future.result(timeout=2)
                    app.tick(None)
                    app.set_preference("mode", "verbatim")
                    self.assertEqual(load_settings(config).mode, "verbatim")
                    self.assertEqual(len(app.mode_menu), 1)
                    self.assertEqual(len(app.limit_menu), 2)
                    with patch.object(rumps, "alert") as alert:
                        app.set_preference("mode", "developer")
                        app.set_preference("max_seconds", 60)
                        self.assertEqual(alert.call_count, 2)
                    self.assertEqual(load_settings(config).mode, "verbatim")
                    self.assertEqual(load_settings(config).max_seconds, 30)
                    app.refresh_microphones(None)
                    self.assertEqual(len(app.microphone_menu), 2)
                    # Use an isolated native pasteboard; never alter the user's clipboard.
                    board = NSPasteboard.pasteboardWithUniqueName()
                    native = app.clipboard.clipboard
                    native.board = board
                    try:
                        native.write("previous")
                        snapshot = native.snapshot()
                        native.write("temporary transcript")
                        native.restore(snapshot)
                        self.assertEqual(board.stringForType_(NSPasteboardTypeString), "previous")
                    finally:
                        board.releaseGlobally()
                    app.clipboard.deliver = Mock(return_value="Copied")
                    app.held.add(keyboard.Key.cmd)
                    app.deliver("test", 42, app.controller.settings)
                    self.assertEqual(app.clipboard.deliver.call_args.args[2].output, "copy")
                    app.held.clear()
                    app.controller.start = Mock()
                    app.set_preference("hotkey", "cmd_l")
                    app.events.put(("press", keyboard.Key.cmd))
                    app.events.put(("release", keyboard.Key.cmd))
                    app.tick(None)
                    app.controller.start.assert_not_called()
                    pending = Future()
                    app.controller.future = pending
                    with patch.object(rumps, "quit_application") as terminate:
                        app.quit(None)
                        terminate.assert_not_called()
                        pending.set_result(None)
                        app.tick(None)
                        terminate.assert_called_once()
                finally:
                    app.timer.stop()
                    app.controller.close()
                    app.controller.executor.shutdown(wait=True)

            with patch("sys.argv", ["voice_dictate.py", "--config", config]), \
                    patch.object(voice_dictate, "MLXBackend", Backend), \
                    patch.object(voice_dictate, "ensure_single_instance", return_value=Mock()), \
                    patch("pynput.keyboard.Listener"), \
                    patch("sounddevice.query_devices", return_value=[]), \
                    patch.object(rumps.App, "run", inspect):
                voice_dictate.main()
