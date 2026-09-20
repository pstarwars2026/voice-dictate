# Voice Dictate

On-device dictation for Apple Silicon Macs, with Free and Pro in one macOS app.
Version 3.0 (build 4) and its one-time Pro upgrade were submitted together to
Apple on September 20, 2026. Both are **Waiting for Review**, not yet approved
or available for purchase. This repository contains the Apache-2.0 Free source core
and model catalog; the native commercial app is developed privately.

Build 4 passed the Pro icon checks and real Apple Sandbox restore/relaunch
follow-up, and replaced build 3 in the joint submission at 11:31 AM Pacific.
Verified Pro ownership changes the running Dock and in-app artwork;
Finder and the App Store listing retain the base app icon.

| Packaged app | Free | Pro |
|---|---|---|
| Price | Free | USD $2.99 one-time, no subscription |
| Recording duration | 30 seconds per recording | Longer recordings, 60-minute safety stop |
| Daily allowance | 5 minutes per UTC day | No daily quota |
| Verbatim dictation and Copy | Included | Included |
| Polished English, Original Language, Developer | Not included | Included |
| On-device model download and compatible updates | Included | Included |

Both tiers initially use Copy, not cross-app insertion. Storefront prices come
from Apple; USD $2.99 is configured for Pro, but the listing is not live yet. See
[Free and Pro](docs/EDITIONS.md) for scope, source boundaries, and status.
The submitted packaged build requires macOS 26.2 or newer on Apple
Silicon; the source runtime's compatibility depends on its installed libraries.
The first release excludes France and is set to release automatically after approval.

[Support](SUPPORT.md) | [Privacy](PRIVACY.md)

Apple's real Sandbox product lookup, no-charge Pro purchase, unlock, clean
quit/relaunch and Restore Purchases passed on September 20, 2026. This is separate
from local StoreKit simulation and does not establish public availability.

## Free source preview

**Source version: 3.0.0a1.** The instructions below run the Python menubar core,
not the packaged app or its purchase flow.

**Free, on-device voice dictation for Apple Silicon Macs.** Hold a key, speak,
and release to transcribe into your active application or copy to the clipboard.

Voice Dictate uses [Gemma 4 E4B](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit)
through [MLX-VLM](https://github.com/Blaizzy/mlx-vlm). Model files download on first
use; transcription runs locally. There is no account requirement, paid API,
telemetry, or app-managed transcript history.

## Free source features

- Verbatim dictation in the original language(s), up to 30 seconds per recording
  and 5 minutes per UTC day, tracked locally in Keychain.
- Saved hotkey, microphone, output, clipboard, and recording-limit preferences.
- Serialized model loading/transcription and bounded recordings.
- Cancellation while recording or processing; cancelled output is never delivered.
- Recording timer and live input-level feedback in the menubar menu.
- Copy-only output, application-focus checks, and optional clipboard restoration.
- No transcript logging or transcript previews in the status menu.
- Setup diagnostics, tests for the recording lifecycle, and Linux/macOS CI.

## Requirements

- macOS on an Apple Silicon Mac.
- Python 3.10 or newer and a compatible MLX runtime.
- At least 6 GB of free disk space for the default model, plus Python dependencies.
- Enough free memory for the model and inference. The model download alone is
  approximately 5.15 GB; memory use grows with recording length.
- Internet access for initial dependency/model downloads. Cached model inference
  can run without internet access.

This is a Python menubar app. A signed standalone `.app` installer is not included
in this source edition. Automatic model-version updates are not implemented yet;
first-use download and cached offline inference are available today.

## Install

```bash
git clone https://github.com/pstarwars2026/voice-dictate.git
cd voice-dictate
./setup.sh
./start.sh
```

To update an existing checkout after quitting the old app:

```bash
git switch main
git pull --ff-only
./setup.sh
./start.sh
```

Keep any local changes before switching branches. Verify the installed source
version with `./start.sh --version`.

## Permissions

- **Microphone:** record speech.
- **Input Monitoring:** listen for the global hotkey.
- **Accessibility:** send the paste shortcut. Copy-only output does not need
  Accessibility for insertion.

In **System Settings > Privacy & Security**, grant permissions to the Python
executable used to run the app. The terminal or launcher may also appear in macOS
permission prompts. To find the real executable behind the virtualenv:

```bash
.venv/bin/python -c 'import os, sys; print(os.path.realpath(sys.executable))'
```

Use that path when adding Python to Accessibility and Input Monitoring, then
restart the app. Permissions can need revisiting after a Python upgrade.

## Everyday use

Wait for **VD** in the menubar, hold **Right Command**, speak, and release.
The app shows **REC** while recording and **...** while loading or transcribing.
Open the menu for the recording timer and input-level meter.

Free provides one mode:

| Mode | Intended output |
|---|---|
| Verbatim | Spoken wording, filler words, and original language(s) |

These are instructions to the model, not guarantees of exact recognition. Review
important text before sending it or executing dictated commands.

Use **Hotkey**, **Microphone**, **Output**, and **Recording limit** to customize the
app. Menu changes are saved and apply to the next recording. Use **Refresh devices**
after connecting a microphone. A disconnected selected microphone produces an
error instead of silently switching devices.

**Test Record (5s, copy only)** records without holding a key and leaves the result
on the clipboard for inspection.

### Recording and cancellation

The default recording limit is 30 seconds; menu choices are 15 and 30 seconds.
The command line accepts 5 to 30 seconds. Longer sessions are part of Pro
development, not this Free edition.
The cap applies to actual captured samples and elapsed time. Recording is unavailable
while the model is loading or processing another recording.

### Daily allowance

Free provides 5 minutes per UTC day, resetting at 00:00 UTC. The counter lives in
macOS Keychain, separately from preferences; restarting or deleting the settings
file does not refill it. Time is reserved before the microphone starts and unused
time is returned on a normal stop. Used time is rounded up to whole seconds.
Cancellation and failed transcription still count captured recording time.
A microphone that fails before capturing audio does not consume time.

Force-quitting or a crash can consume the full reserved clip (at most 30 seconds).
This conservative behavior prevents repeatedly quitting to erase usage. If fewer
than 30 seconds remain, the last recording is shortened to the available time.
Test Record uses the same allowance. Keychain errors stop new recordings rather
than silently granting more time; unlock Keychain and retry.

The counter contains only usage totals, timestamps, and a reservation identifier,
not audio or transcripts. It is not synchronized through iCloud by this app.
Clock rollback and time-zone changes do not grant another allowance. Deliberate
clock advances, removal of the Keychain item, or modified source can bypass local
limits. This is restart-resistant accounting, not tamper-proof DRM.

Press **Escape** or choose **Cancel** to discard a recording or pending transcript.
During inference, cancellation suppresses the result but waits for the current
model call to finish before accepting another recording. Quit also waits for an
in-flight model call to finish before the Python process fully exits.

### Clipboard and insertion

**Paste** checks the application active when recording began. If another app is
active when inference finishes, output is copied without pasting. Output is also
copied only when a modifier remains held or the app's menu is open.

This check identifies the application, not the field or document. Choose **Copy
only** when you want full control over the destination.

**Restore clipboard after paste** preserves the previous native pasteboard items,
including image and rich-text types, and restores them after 0.8 seconds only if
the clipboard has not changed. It never overwrites something newly copied during
that interval. Paste dispatch cannot confirm that every application consumed the
text; disable restoration for slow apps or choose copy-only output.

Copy-only output and failed paste attempts leave the transcript on the clipboard.

## Configuration

Preferences are written atomically to
`~/Library/Application Support/Voice Dictate Free/settings.json`, with owner-only file
permissions. CLI flags override saved settings for the current run; add `--save`
to persist them. A subsequent menu change saves the current effective preferences.

```bash
./start.sh --mode verbatim --hotkey f5 --save
./start.sh --output copy
./start.sh --microphone "MacBook Pro Microphone" --max-seconds 30 --save
./start.sh --model mlx-community/gemma-4-e4b-it-8bit
./start.sh --help
```

Use `--config /path/to/settings.json` for a separate profile. Invalid settings
produce an error without overwriting the file. Changing the model requires a
restart; alternate models must support MLX-VLM audio input.

Free uses a separate settings directory and never automatically rewrites your v2
preferences. Explicitly supplying a v2 config with a removed mode or a limit over
30 seconds gives an error without changing the file. The instance lock is shared
with v2 to prevent duplicate hotkey listeners across editions.

## Privacy

The application does not print transcripts or keep transcript history. Recordings
are temporarily written to private WAV files for inference and deleted afterward,
including on model errors. A system crash or forced termination can leave a
temporary WAV behind. Clipboard output remains available to other software with
clipboard access, just like manually copied text.

The first model download requires network access. To force cached operation after
setup, launch with `HF_HUB_OFFLINE=1 ./start.sh`.

Daily usage is stored locally in a Keychain item under service
`com.pstarwars2026.voicedictate.free-usage`. There is no usage server or account.

## Troubleshooting

Run the diagnostic companion tool using the same Python as the app:

```bash
.venv/bin/python tools/voice_dictate_doctor.py
.venv/bin/python tools/voice_dictate_doctor.py --json
```

Doctor checks the platform, Python, dependencies, audio devices, model-cache space,
and the Python path to grant permissions to. It does not load the model or certify
that permissions were actually granted. Review diagnostic paths/device names before
posting them in an issue; do not attach private audio.

- **Model fails to load:** check the model ID, first-download network access, and
  available memory/disk space. Use **Retry model load** after resolving the cause.
- **No recording:** check Microphone permission and the selected device. Reconnect
  and refresh a disconnected device, or select System default.
- **Hotkey does not work:** check Input Monitoring and restart the app. Use the
  five-second test recording to distinguish hotkey trouble from microphone trouble.
- **Copied but not pasted:** check Output mode, Accessibility permission, focus
  changes, held modifiers, and whether the menu was open.
- **Already running:** quit the existing app. The OS releases its instance lock on
  exit; do not delete `~/Library/Application Support/Voice Dictate/instance.lock`
  while a process is running. Quit pre-v2 instances before upgrading.

## Development and verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```

See [release verification](docs/RELEASE_CHECKS.md) for automated coverage, live
acceptance checks, and remaining limitations. See [contributing](CONTRIBUTING.md)
for issue reports and pull requests. Native UI tests require macOS and UI
dependencies; lifecycle tests run without downloading a model.

Current development-edition results are in
[Free preview checks](docs/FREE_PREVIEW_CHECKS.md). Historical v2 results below
must not be read as verification of a native Free/Pro product.

Historical v2 verification (not certification of this development preview):
v2 was exercised on an Apple M4 Mac with 16 GB RAM and macOS 26.6.2: all four
modes with generated English/Hindi speech, digital silence, real Logitech BRIO
microphone capture, Right Command activation, native text insertion, clipboard
restoration, and cancellation during recording and inference. Cached inference
ran with `HF_HUB_OFFLINE=1`.

In the final fixture run, 3.6-3.93 seconds of speech took 2.35-5.67 seconds to
process; cached model loading took 14.8 seconds. These are smoke-test observations
on one machine, not cross-device performance guarantees. They do not establish
accuracy for all accents, languages, noisy rooms, or destination applications.

## License and acknowledgments

Code in this public repository is [Apache-2.0](LICENSE). Gemma 4 is separately
provided under Google's [Apache-2.0 model license](https://ai.google.dev/gemma/apache_2).
Earlier published source remains available under its original license in Git
history; it is not a separate current product tier.

Built with Google's Gemma, Apple's [MLX](https://github.com/ml-explore/mlx),
[MLX-VLM](https://github.com/Blaizzy/mlx-vlm), and
[rumps](https://github.com/jaredks/rumps).
