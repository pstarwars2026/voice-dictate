# Voice Dictate Privacy

Updated September 19, 2026. This page describes the native Voice Dictate
macOS app being prepared for the Mac App Store. Free and Pro use the same
privacy approach. The packaged app is not yet available for purchase.

## Recordings and Transcripts

Dictation is processed on your Mac using a downloaded model. Voice Dictate
does not send recordings or transcripts to a speech service or developer
server. Temporary recordings stay inside the app's sandbox and are deleted
after processing or cancellation. Leftovers from an interrupted session are
removed at the next launch. Deletion is ordinary file deletion, not a secure
erase of storage or backups.

Transcripts remain in the app's memory until cleared or the app closes. The
app has no transcript history. Copy places text on the system clipboard;
other apps and system clipboard features may then access it.

## Local Settings and Allowance

The app stores microphone selection and model-update preferences locally.
Free usage accounting is stored in the local macOS Keychain and contains
dates, durations, and recording reservation identifiers, not audio or text.
It persists across app restarts and may remain after uninstalling the app.
Pro purchases remove the Free daily allowance.

## Network Connections and Purchases

Checking for compatible model updates contacts GitHub. Downloading model
files contacts Hugging Face and its download infrastructure. These services
receive ordinary network information, such as the requesting IP address.
They do not receive the recording or transcript from Voice Dictate.
Automatic model-update checks are off by default. After model installation,
transcription works without an internet connection.

Apple processes purchases and restores through StoreKit. Voice Dictate uses
Apple-verified purchase information to determine whether Pro is unlocked;
it does not receive your payment-card information.

Voice Dictate does not implement advertising, analytics, user accounts,
tracking, or a usage server. Apple may separately handle diagnostics or
purchase information according to your Apple settings and its policies.

## Permissions and Support

The app requests microphone access to record when you start a recording.
You can revoke it in macOS System Settings. The initial packaged version
uses Copy and does not request Accessibility access to type into other apps.

For questions, see [Support](SUPPORT.md). GitHub issues are public: do not
include private recordings, transcripts, passwords, payment details, or
other sensitive information in an issue.

The separate open-source Python preview has different installation and
output options, described in the [README](README.md). This policy does not
describe modified third-party builds.
