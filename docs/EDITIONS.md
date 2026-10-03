# Free and Pro

## Status

Voice Dictate is one native macOS app with Free and Pro tiers. Version 3.0 was
released October 2, 2026; US availability was verified October 3, 2026.
[Download on the Mac App Store](https://apps.apple.com/us/app/voice-dictate-local-ai/id6814047582).
Pro artwork follows verified ownership in the app and running Dock, including
after relaunch and restore. Finder and the App Store listing retain the base icon.
The initial release excludes France.
This public repository contains
the Free Python core (3.0.0a1) and the compatible model catalog. Native packaging
and StoreKit purchase code are maintained privately.

The packaged app is available through the Mac App Store. Copy-only output
is the accepted baseline in both tiers. The Python source runtime can still
paste using Accessibility permission; that does not establish sandbox support.
Cross-app insertion may become Pro only after a compliant implementation is
verified. It is not included in the advertised initial paid feature set.

| Capability | Free source edition | Mac App Store Pro upgrade |
|---|---|---|
| Local verbatim dictation | Available | Included |
| Recording length | 5-30 seconds | Longer sessions, internally chunked for the model |
| Daily allowance | 5 minutes per UTC day, local Keychain counter | No daily allowance cap |
| Microphone selection, cancellation and Copy | Available | Included |
| First-use model download and offline inference | Available | Included |
| Polished English, original-language cleanup, developer modes | Not in Free | Included |
| Verified model-update catalog and rollback | Catalog published here; manager in native app | Same support as Free |
| Native packaged app and purchase/restore | Not part of the source core | Available through the Mac App Store |

Pricing is a USD $2.99 one-time non-consumable upgrade, not a subscription.
The app is free to download; Pro is an optional in-app purchase.
Storefront prices are loaded from the store, not hard-coded in UI.
The purchase unlocks the stated features; it does not promise all future paid
products or features forever.

Custom vocabulary, per-app profiles, history/search/export, batch transcription,
templates, and automation are outside this initial scope.
No account, advertising, usage server, or transcript collection is planned.
Necessary safety fixes and compatible model updates are not Pro gates.

The local daily quota reserves recording time before capture. It survives normal
relaunches and abrupt exits; cancelled recording time still counts. It is not
tamper-proof against modified source, deleted Keychain data, or advanced clock
manipulation. Users can modify the open-source edition under its license.

## Source and licensing

- This public repository remains Apache-2.0.
- The commercial app is developed in a separate private repository. New
  proprietary code must carry a clearly scoped license.
- Native source, purchase implementation, signing material, account details,
  and internal commercial release evidence do not belong in this public repository,
  its pull requests, issues, build logs, or attachments.
- The published v2 code and modes remain usable under Apache-2.0, including
  in earlier commits and releases. They have not become secret or proprietary.
- Distributions retain required licenses, attributions, and notices for reused
  code. Dependencies and each selected model revision require a release audit.

Open-source feature limits describe the maintained product, not an attempt to
prevent users from modifying Apache-licensed code.

## Model delivery

Ship the inference runtime with the app, not the multi-GB model weights. Download
weights only after showing the size and obtaining the user's download consent.
The update catalog specifies an immutable model revision, checksums,
runtime compatibility, audio support, and storage/memory requirements.

Offer opt-in automatic updates from that tested catalog. Do not automatically
choose the newest search result or arbitrary remote code. Stage and validate a
download before activation; keep the previous working model for rollback and
do not replace a model during recording/inference. Cached dictation must work
offline. New architectures can still require an app update.

## Source verification

See [Free preview checks](FREE_PREVIEW_CHECKS.md) for this repository's source
checks and [historical v2 checks](RELEASE_CHECKS.md) for the earlier release.
Neither certifies the native commercial app. Detailed commercial test records
and submission operations are maintained privately. Testing alone does not
establish App Store approval or availability.
