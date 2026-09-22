# Contributing to Voice Dictate

Thanks for helping improve private, on-device dictation for macOS.

## Good first contributions

- Improve setup and permission diagnostics.
- Add support notes for specific macOS versions or Apple Silicon machines.
- Test alternate MLX speech-capable models and document tradeoffs.
- Improve verbatim recognition and technical-term preservation.
- Add packaging improvements that keep the app offline and telemetry-free.

This repository contains the Free edition. See [edition boundaries](docs/EDITIONS.md)
before proposing commercial features. Contributions here remain Apache-2.0;
do not submit private Pro source, purchase credentials, or signing material.
Keep internal commercial test logs, submission records, review contacts, account
screenshots, and local machine paths private too. This applies to PR descriptions,
issues, comments, CI output, and release attachments, not just source files.
Do not copy or merge the commercial repository wholesale into this one.

## Local checks

Run the lightweight checks before opening a pull request:

```bash
python -m unittest discover -s tests -p "test_*.py"
python tools/voice_dictate_doctor.py
python tools/check_public_boundary.py
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

Do not attach private audio, transcripts, receipts, or unredacted diagnostics.
Review paths and device names before posting. GitHub issues are public.
