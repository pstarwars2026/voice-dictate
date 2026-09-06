# Next release verification

## Automated checks

Run `python -m unittest discover -s tests -v` from the repository root.
Core lifecycle tests use controlled model and microphone doubles. Backend tests
with numpy exercise WAV encoding and temporary-file removal with inference mocked.
On macOS, with rumps, pynput and sounddevice installed, native menu tests exercise
Cocoa construction, saved preferences, microphone refresh, and an isolated native
pasteboard. Global input hooks, recording and model execution are replaced.

CI runs Python 3.10 and 3.13 on Linux and macOS. Doctor JSON must parse successfully;
missing optional runtime/model dependencies are expected in the CI environment.

## Live acceptance before release

These checks require a real Apple Silicon Mac, the model, and granted permissions.
Automated tests do not establish speech accuracy or real text insertion behavior.

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
