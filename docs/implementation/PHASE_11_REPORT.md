# Phase 11 — Android build and hardening

Status: PASS (18 September 2026).

Implemented release-signing hardening. Release builds now use `mobile/android/key.properties` only when the owner supplies it; the project no longer configures a release build to use the debug signing key. The private keystore configuration is ignored by Git, and [MOBILE_SETUP.md](../MOBILE_SETUP.md) documents creating a keystore and release APK.

Validation on Windows:

- `flutter analyze` — no issues.
- `flutter test` — 5 passed; 2 opt-in live-backend tests skipped by default.
- `flutter build apk --debug --split-per-abi --dart-define=GOLDNEST_CERT_SHA256=<current pin>` — passed.
- Installed `app-arm64-v8a-debug.apk` (86,734,154 bytes) on RMX3853 through wireless ADB — passed.
- Launched the installed app — passed; the saved signed-in session and configured pinned HTTPS server were visible.

The verified debug APK is `mobile/build/app/outputs/flutter-apk/app-arm64-v8a-debug.apk`. A release APK requires a user-owned signing key and was deliberately not built with debug credentials.
