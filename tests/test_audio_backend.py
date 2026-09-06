import importlib.util
import os
import types
import unittest
import wave
from unittest.mock import Mock, patch

from voice_dictate import MLXBackend


@unittest.skipUnless(importlib.util.find_spec("numpy"), "Requires numpy")
class AudioBackendTests(unittest.TestCase):
    def test_digital_silence_never_reaches_inference(self):
        import numpy as np
        mlx = types.ModuleType("mlx_vlm")
        mlx.generate = Mock(side_effect=AssertionError("silence must not generate"))
        prompts = types.ModuleType("mlx_vlm.prompt_utils")
        prompts.apply_chat_template = Mock()
        with patch.dict("sys.modules", {"mlx_vlm": mlx, "mlx_vlm.prompt_utils": prompts}):
            self.assertEqual(MLXBackend("test").transcribe([np.zeros(16000)], "test"), "")
        mlx.generate.assert_not_called()

    def exercise(self, fail):
        import numpy as np
        paths = []

        def generate(*args, **kwargs):
            path = kwargs["audio"]
            paths.append(path)
            with wave.open(path) as recording:
                self.assertEqual(recording.getframerate(), 16000)
                self.assertEqual(recording.getnchannels(), 1)
                self.assertEqual(recording.getsampwidth(), 2)
                pcm = np.frombuffer(recording.readframes(3), dtype=np.int16)
                self.assertEqual(list(pcm), [-32767, 0, 32767])
            if fail:
                raise RuntimeError("inference failed")
            return types.SimpleNamespace(text="transcript")

        backend = MLXBackend("test-model")
        backend.model = types.SimpleNamespace(config={})
        backend.processor = Mock()
        mlx = types.ModuleType("mlx_vlm")
        mlx.generate = generate
        prompts = types.ModuleType("mlx_vlm.prompt_utils")
        prompts.apply_chat_template = Mock(return_value="prompt")
        with patch.dict("sys.modules", {"mlx_vlm": mlx, "mlx_vlm.prompt_utils": prompts}):
            if fail:
                with self.assertRaises(RuntimeError):
                    backend.transcribe([np.array([-2.0, 0, 2.0])], "test")
            else:
                self.assertEqual(backend.transcribe([np.array([-2.0, 0, 2.0])], "test"), "transcript")
        self.assertEqual(len(paths), 1)
        self.assertFalse(os.path.exists(paths[0]))

    def test_pcm_clipping_and_cleanup_on_success(self):
        self.exercise(False)

    def test_audio_cleanup_on_model_failure(self):
        self.exercise(True)
