import json
from pathlib import Path
import tempfile
import threading
import unittest
from dataclasses import replace
from unittest.mock import Mock

from dictation_core import (
    AudioBuffer, ClipboardDelivery, DictationController, Settings,
    MODES, instance_lock_path, load_settings, prompt_for, save_settings, settings_path,
)


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_private_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "nested/settings.json"
            settings = Settings(mode="verbatim", hotkey="f5", output="copy")
            save_settings(settings, path)
            self.assertEqual(load_settings(path), settings)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_bad_config_does_not_get_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "settings.json"
            path.write_text('{"mode": "unknown"}')
            with self.assertRaises(ValueError):
                load_settings(path)
            self.assertEqual(json.loads(path.read_text()), {"mode": "unknown"})

    def test_invalid_limits_and_types(self):
        for value in (0, 4, 31, 60, 120, 121, True, "30"):
            with self.assertRaises(ValueError):
                Settings(max_seconds=value).validate()

    def test_only_verbatim_is_available_in_free(self):
        self.assertEqual(set(MODES), {"verbatim"})
        for mode in ("polished", "original", "developer"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                Settings(mode=mode).validate()
            with self.assertRaises(KeyError):
                prompt_for(mode)

    def test_legacy_config_is_not_silently_downgraded(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "settings.json"
            original = '{"mode": "polished", "max_seconds": 120}'
            path.write_text(original)
            with self.assertRaises(ValueError):
                load_settings(path)
            self.assertEqual(path.read_text(), original)

    def test_free_settings_are_separate_but_instance_lock_is_shared(self):
        self.assertEqual(settings_path().parent.name, "Voice Dictate Free")
        self.assertEqual(instance_lock_path().parent.name, "Voice Dictate")

    def test_supported_recording_boundaries(self):
        for seconds in (5, 15, 30):
            self.assertEqual(Settings(max_seconds=seconds).validate().max_seconds, seconds)

    def test_missing_settings_use_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(load_settings(Path(root) / "missing"), Settings())


class FakeBackend:
    def __init__(self):
        self.release = threading.Event()
        self.release.set()
        self.load_error = False
        self.transcribe_error = False
        self.calls = []

    def load(self):
        if self.load_error:
            raise RuntimeError("load failed")

    def transcribe(self, blocks, prompt):
        self.calls.append((blocks, prompt))
        if not self.release.wait(2):
            raise RuntimeError("test synchronization timeout")
        if self.transcribe_error:
            raise RuntimeError("transcription failed")
        return "Test transcript"


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.recorder = Mock()
        self.factory = Mock(return_value=self.recorder)
        self.deliver = Mock(return_value="Copied")
        self.now = 0
        self.controller = DictationController(self.backend, self.factory, self.deliver, clock=lambda: self.now)
        self.addCleanup(self.cleanup)
        self.finish()

    def cleanup(self):
        self.backend.release.set()
        self.controller.close()
        self.controller.executor.shutdown(wait=True)

    def finish(self):
        try:
            future = self.controller.future
            if future is not None:
                future.result(timeout=2)
        except RuntimeError:
            pass
        self.controller.tick()

    def record(self):
        self.assertTrue(self.controller.start(target=42))
        self.controller.buffer.append([0.1] * 8000)

    def test_loading_blocks_recording(self):
        self.controller.state = "loading"
        self.assertFalse(self.controller.start())
        self.factory.assert_not_called()

    def test_repeated_start_and_stop_only_submit_once(self):
        self.record()
        self.assertFalse(self.controller.start())
        self.controller.stop()
        self.controller.stop()
        self.finish()
        self.assertEqual(len(self.backend.calls), 1)
        self.recorder.close.assert_called_once()
        self.deliver.assert_called_once()

    def test_cancel_processing_suppresses_output_and_blocks_new_job(self):
        self.backend.release.clear()
        self.record()
        self.controller.stop()
        self.controller.cancel()
        self.assertFalse(self.controller.start())
        self.backend.release.set()
        self.finish()
        self.deliver.assert_not_called()
        self.assertEqual(self.controller.state, "ready")

    def test_cancel_recording_cleans_stream(self):
        self.record()
        self.controller.cancel()
        self.recorder.close.assert_called_once()
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(self.controller.buffer.blocks, [])

    def test_auto_stop_uses_sample_count_and_clips_final_block(self):
        self.record()
        self.controller.buffer.append([0.1] * 500000)
        self.assertEqual(self.controller.buffer.count, 480000)
        self.controller.tick()
        self.finish()
        self.assertEqual(sum(len(b) for b in self.backend.calls[0][0]), 480000)

    def test_wall_clock_stops_stalled_device(self):
        self.record()
        self.now = 31
        self.controller.tick()
        self.finish()
        self.recorder.close.assert_called_once()

    def test_microphone_start_failure_is_recoverable(self):
        self.recorder.start.side_effect = RuntimeError("device missing")
        self.assertFalse(self.controller.start())
        self.assertEqual(self.controller.state, "ready")
        self.recorder.close.assert_called_once()
        self.recorder.start.side_effect = None
        self.assertTrue(self.controller.start())

    def test_overflow_discards_incomplete_audio(self):
        self.record()
        self.controller.buffer.append([0.1], status=True)
        self.controller.tick()
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(self.controller.state, "ready")

    def test_session_uses_settings_at_recording_start(self):
        self.controller.settings = Settings(output="copy")
        self.record()
        self.controller.settings = Settings(output="paste")
        self.controller.stop()
        self.finish()
        self.assertEqual(self.backend.calls[0][1], prompt_for("verbatim"))
        self.assertEqual(self.deliver.call_args.args[2].output, "copy")

    def test_recording_override_cannot_exceed_free_limit(self):
        for seconds in (0, -1, 31, 120, True, 5.5):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.controller.start(seconds=seconds)
        self.factory.assert_not_called()
        self.assertEqual(self.controller.state, "ready")

    def test_quota_failure_prevents_microphone_start(self):
        from usage_quota import QuotaError
        quota = Mock()
        quota.reserve.side_effect = QuotaError("Daily allowance used")
        self.controller.quota = quota
        self.assertFalse(self.controller.start())
        self.factory.assert_not_called()
        self.assertEqual(self.controller.message, "Daily allowance used")

    def test_quota_reserves_before_capture_and_charges_cancellation(self):
        quota = Mock()
        quota.reserve.return_value = ("token", 3, 0)
        quota.settle.return_value = 2
        self.controller.quota = quota
        self.factory.side_effect = lambda *args: self.assertEqual(quota.reserve.call_count, 1) or self.recorder
        self.record()
        self.assertEqual(self.controller.buffer.limit, 3 * 16000)
        self.now = 1
        self.controller.cancel()
        quota.settle.assert_called_once_with("token", 1)
        self.assertEqual(self.controller.remaining_seconds, 2)

    def test_quota_refunds_failed_microphone_start(self):
        quota = Mock()
        quota.reserve.return_value = ("token", 30, 270)
        self.controller.quota = quota
        self.recorder.start.side_effect = RuntimeError("microphone denied")
        self.assertFalse(self.controller.start())
        quota.settle.assert_called_once_with("token", 0)

    def test_short_recording_is_not_sent_to_model(self):
        self.controller.start()
        self.controller.buffer.append([0.1] * 100)
        self.controller.stop()
        self.assertEqual(self.backend.calls, [])

    def test_test_record_is_copy_only(self):
        self.controller.start(seconds=5, copy_only=True)
        self.controller.buffer.append([0.1] * 80000)
        self.controller.tick()
        self.finish()
        self.assertEqual(self.deliver.call_args.args[2].output, "copy")

    def test_transcription_failure_allows_retry(self):
        self.backend.transcribe_error = True
        self.record()
        self.controller.stop()
        self.finish()
        self.assertEqual(self.controller.state, "ready")
        self.deliver.assert_not_called()

    def test_model_load_can_be_retried(self):
        self.backend.load_error = True
        self.controller.state = "error"
        self.controller.retry_load()
        self.finish()
        self.assertEqual(self.controller.state, "error")
        self.backend.load_error = False
        self.controller.retry_load()
        self.finish()
        self.assertEqual(self.controller.state, "ready")


class ClipboardTests(unittest.TestCase):
    def setUp(self):
        self.clipboard = Mock()
        self.previous = [{"public.png": b"image", "public.utf8-plain-text": b"text"}]
        self.clipboard.snapshot.return_value = self.previous
        self.clipboard.write.return_value = 10
        self.clipboard.revision.return_value = 10
        self.frontmost = Mock(return_value=42)
        self.paste = Mock()
        self.delivery = ClipboardDelivery(self.clipboard, self.frontmost, self.paste, clock=lambda: 0)

    def test_restore_all_types_after_paste(self):
        self.delivery.deliver("hello", 42, Settings())
        self.delivery.tick()
        self.clipboard.restore.assert_not_called()
        self.delivery.tick(force=True)
        self.clipboard.restore.assert_called_once_with(self.previous)

    def test_new_clipboard_contents_are_not_overwritten(self):
        self.delivery.deliver("hello", 42, Settings())
        self.clipboard.revision.return_value = 11
        self.delivery.tick(force=True)
        self.clipboard.restore.assert_not_called()

    def test_focus_change_copies_without_paste(self):
        self.delivery.deliver("hello", 99, Settings())
        self.paste.assert_not_called()
        self.assertIsNone(self.delivery.pending)

    def test_copy_mode_retains_transcript(self):
        self.delivery.deliver("hello", 42, Settings(output="copy"))
        self.paste.assert_not_called()
        self.assertIsNone(self.delivery.pending)

    def test_failed_paste_retains_transcript(self):
        self.paste.side_effect = RuntimeError("permission")
        self.assertIn("copied only", self.delivery.deliver("hello", 42, Settings()))
        self.assertIsNone(self.delivery.pending)

    def test_restore_can_be_disabled(self):
        self.delivery.deliver("hello", 42, Settings(restore_clipboard=False))
        self.paste.assert_called_once()
        self.clipboard.snapshot.assert_not_called()
        self.assertIsNone(self.delivery.pending)


if __name__ == "__main__":
    unittest.main()
