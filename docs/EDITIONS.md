# Free and Pro

## Status

Voice Dictate is one native macOS app with Free and Pro tiers, currently in
development and not available for purchase. This public repository contains
the Free Python core (3.0.0a1) and the compatible model catalog. Native packaging
and StoreKit purchase code are maintained privately.

The first packaged release will prioritize the Mac App Store. Copy-only output
is the accepted baseline in both tiers. The Python source runtime can still
paste using Accessibility permission; that does not establish sandbox support.
Cross-app insertion may become Pro only after a compliant implementation is
verified. It is not included in the advertised initial paid feature set.

| Capability | Free source edition | Planned packaged Pro upgrade |
|---|---|---|
| Local verbatim dictation | Available | Included |
| Recording length | 5-30 seconds | Longer sessions, internally chunked for the model |
| Daily allowance | 5 minutes per UTC day, local Keychain counter | No daily allowance cap |
| Hotkey, microphone, cancellation, clipboard safety | Available | Included |
| First-use model download and offline inference | Available | Included |
| Polished English, original-language cleanup, developer modes | Not in Free | Implemented in the native development app |
| Verified model-update catalog and rollback | Catalog published here; manager in native app | Same support as Free |
| Standalone installer and purchase/restore | Not shipped | In development |

Target pricing is a USD $2.99 one-time non-consumable upgrade, aligned with Svara,
not a subscription. This price has not been configured or published in App Store
Connect. Storefront prices will be shown from the store, not hard-coded in UI.
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

## Release gates

1. Validate Gemma audio inference in the packaged runtime on Apple Silicon.
2. Test sandboxed shortcuts and insertion before choosing App Store distribution.
   Do not promise cross-app paste if the sandbox prevents it.
3. Validate purchases, restore, offline ownership, pending/cancelled purchases,
   invalid verification, and refunds. Never unlock from an editable preference.
4. Test first download, interruption, corrupt weights, failed updates, and rollback.
5. Test real microphone input, cancellation, permissions, and destination apps.
6. Complete signing, privacy/model notices, packaging, and store metadata.

Planned bundle identifier: `com.pstarwars2026.voicedictate`.
Planned non-consumable product identifier: `com.pstarwars2026.voicedictate.pro`.
These names follow the owner's existing app convention; no Apple registration
or product configuration is claimed by documenting them here.

There is no new App Store submission or paid release at this stage.
