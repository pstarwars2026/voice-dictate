import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCTOR_PATH = ROOT / "tools" / "voice_dictate_doctor.py"

spec = importlib.util.spec_from_file_location("voice_dictate_doctor", DOCTOR_PATH)
doctor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = doctor
spec.loader.exec_module(doctor)


class VoiceDictateDoctorTests(unittest.TestCase):
    def test_status_labels(self):
        self.assertEqual(doctor.status(True), "ok")
        self.assertEqual(doctor.status(False), "fail")
        self.assertEqual(doctor.status(False, warning=True), "warn")

    def test_module_check_reports_missing_module(self):
        results = doctor.check_modules(["definitely_missing_voice_dictate_module"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "fail")
        self.assertIn("not found", results[0].detail)

    def test_run_checks_returns_named_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_audio = doctor.CheckResult("Audio input", "warn", "skipped")
            with mock.patch.object(doctor, "check_audio_input", return_value=fake_audio):
                results = doctor.run_checks(tmpdir)

        names = [result.name for result in results]

        self.assertIn("macOS", names)
        self.assertIn("Python", names)
        self.assertIn("Audio input", names)
        self.assertIn("macOS permission target", names)


if __name__ == "__main__":
    unittest.main()
