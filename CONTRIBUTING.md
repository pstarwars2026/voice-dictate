# Contributing to Voice Dictate

Thanks for helping improve private, on-device dictation for macOS.

## Good first contributions

- Improve setup and permission diagnostics.
- Add support notes for specific macOS versions or Apple Silicon machines.
- Test alternate MLX speech-capable models and document tradeoffs.
- Improve technical-term preservation prompts for developer dictation.
- Add packaging improvements that keep the app offline and telemetry-free.

## Local checks

Run the lightweight checks before opening a pull request:

```bash
python -m unittest discover -s tests -p "test_*.py"
python tools/voice_dictate_doctor.py
```

The doctor does not load the model. It is meant to catch setup, Python, audio,
and macOS permission issues before a user has to download several GB of model
weights.

## Issue reports

Please include:

- macOS version and Mac model.
- Python version.
- The command you ran.
- Output from `python tools/voice_dictate_doctor.py --json`.
- Whether Microphone, Accessibility, and Input Monitoring permissions are granted
  to the exact Python binary shown by the doctor.

Do not attach private audio samples unless you intentionally want maintainers to
hear them. Voice Dictate is designed so audio stays on your machine.
