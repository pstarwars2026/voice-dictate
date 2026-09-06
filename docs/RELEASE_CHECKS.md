# Voice Dictate v2.0.0 verification

## Live results (2026-09-06 UTC)

Tested on Apple M4, 16 GB RAM, macOS 26.6.2, Python 3.13. Runtime:
MLX-VLM 0.6.17, MLX 0.32.2, Transformers 5.16.1, Jinja2 3.1.6.
Default model: mlx-community/gemma-4-e4b-it-4bit, revision
`475b9088d29754a3379866cf5aeb6b41acd313c2` (5.15 GB weights).

All final inference tests ran with `HF_HUB_OFFLINE=1` after downloading the model.
Generated speech fixtures used macOS Samantha (English) and Lekha (Hindi),
16 kHz mono PCM. These were real model calls on the app's worker thread.

| Fixture / mode | Observed result |
|---|---|
| English / Verbatim | Preserved the opening "Um" and the Python/unit-test instruction |
| English / Polished English | Removed "Um"; retained the instruction |
| English / Original | Removed "Um"; retained English wording |
| English / Developer | "Fix the Python function and add three unit tests." |
| Hindi / Verbatim | Preserved Hindi text |
| Hindi / Polished English | Translated the three-tests/report sentence into English |
| Hindi / Original | Preserved Hindi text with punctuation |
| Hindi / Developer | Translated into an English instruction |
| Digital silence | Empty output; no-signal guard bypasses generation |

Cached load: 14.8 seconds. Eight fixture calls: 2.35-5.67 seconds for
3.6-3.93 seconds of audio. This is a smoke test, not a statistically meaningful benchmark.

The running macOS app was then tested using its real pynput listener, Right Command
hotkey, Logitech BRIO input, MLX inference, and native Cmd+V into a disposable Cocoa
text window. Generated speech played through the Mac's speakers. The resulting text
was "I need to fix the Python function and add three unit tests."

- Real microphone-to-text insertion: passed.
- Previous clipboard contents restored: passed.
- Escape cancellation while recording: passed; no new text inserted.
- Escape cancellation during real inference: passed; no cancelled text inserted.
- Quit during real inference: passed; native termination waited 3.83 seconds for
  the worker future to complete, allowing temporary-audio cleanup to finish.
- System speaker volume was restored after the hardware test.

Live checks found and fixed a missing Jinja2 dependency, weak cleanup/translation
prompts, and model hallucination on a no-signal recording. Prompt examples were
removed and digital silence is rejected before inference. Early low-volume/F5
hardware attempts did not pass; the final physical test used Right Command and
audible speaker output. Low-volume/noisy-environment accuracy remains unverified.

## Automated checks

Run `python -m unittest discover -s tests -v` from the repository root.
30 tests pass locally. Core lifecycle tests use controlled model and microphone doubles. Backend tests
with numpy exercise WAV encoding and temporary-file removal with inference mocked.
On macOS, with rumps, pynput and sounddevice installed, native menu tests exercise
Cocoa construction, saved preferences, microphone refresh, and an isolated native
pasteboard. Global input hooks, recording and model execution are replaced.

CI runs Python 3.10 and 3.13 on Linux and macOS. Doctor JSON must parse successfully;
missing optional runtime/model dependencies are expected in the CI environment.

## Additional acceptance matrix

The live results above cover the main release path. The broader checks below remain
useful for regression testing and additional devices/apps; they are not all claimed
as physically verified. Automated tests do not establish speech accuracy or real
text insertion behavior.

- Run setup and start; verify model loading and permission guidance on a clean profile.
- Record short English and Hindi/Hinglish samples in each of the four modes.
- Verify Verbatim retains fillers and Original preserves language/code-switching.
- Check names, identifiers, paths, punctuation, numbers, and silent input manually.
- Hold the hotkey to the recording cap; check bounded recording and copy-only output
  when a modifier remains held. Release and record again.
- Cancel while recording and during inference; confirm no cancelled output is inserted.
- Try repeated hotkey presses during loading and inference; confirm no overlapping jobs.
- Unplug/reconnect a selected microphone; refresh devices and recover.
- Change mode/hotkey/output in the menu, restart, and verify persistence.
- Switch applications during inference; confirm copy-only fallback.
- Paste into a plain-text editor and a browser text field; test clipboard restoration
  with text and images. Copy something new during the restore delay and verify it survives.
- Test denied Accessibility with copy-only output and missing Input Monitoring guidance.
- Quit during inference and confirm the process exits after the current model call finishes.

Known limits: cancellation suppresses output but does not interrupt MLX inference;
focus checks identify applications, not fields; clipboard restore uses a fixed delay;
hard termination can leave temporary audio; model and performance benchmarks are pending.
