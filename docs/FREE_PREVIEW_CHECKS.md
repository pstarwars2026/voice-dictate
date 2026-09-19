# Free 3.0.0a1 development checks

Date: 2026-09-19. This is not a release approval or a native app test.

## Verified locally

- 55 Python tests passed, including real Cocoa menu construction and isolated
  pasteboard operations. Model, input hooks, and microphone are mocked in these
  unit tests.
- Free exposes only Verbatim and accepts recording limits from 5 to 30 seconds.
  Configuration, menu changes, and controller overrides reject unsupported values.
- Legacy configurations are rejected without rewriting their contents. Free has
  separate preferences and shares the legacy process lock.
- Daily allowance tests cover 300-second exhaustion, partial final recordings,
  concurrent reservations, duplicate/stale settlement, midnight reset, clock
  rollback, storage failure, corrupted data, and cancellation.
- An isolated real Keychain item survived an abrupt child-process exit and two
  fresh launches: a 30-second reservation left 270 seconds. The exact test item
  was removed afterward; the production counter was never read or changed.
- Real cached Gemma E4B inference produced nonempty output for synthetic English
  and Hindi fixtures; digital silence produced empty output. Network was disabled
  through `HF_HUB_OFFLINE=1`. This does not measure transcription accuracy.
- Observed model load: 19.84 seconds; English inference: 6.20 seconds;
  Hindi inference: 3.06 seconds. These are one-machine smoke observations.

Run automated checks with:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/check_quota_restart.py
```

Run cached real inference on your own synthetic 16 kHz mono PCM fixtures with:

```sh
HF_HUB_OFFLINE=1 .venv/bin/python tools/check_inference.py /path/to/english.wav /path/to/hindi.wav
```

The smoke tool never prints or saves transcripts. Nonempty output alone is not
proof of accurate recognition. The historical v2 physical-microphone evidence
in RELEASE_CHECKS.md does not certify this new development edition.

## Not yet verified

New physical microphone/hotkey/insertion regression checks, a self-contained
native app, sandboxed Gemma inference, StoreKit purchases/refunds/restore,
automatic model updates, distribution signing, and App Store acceptance.
