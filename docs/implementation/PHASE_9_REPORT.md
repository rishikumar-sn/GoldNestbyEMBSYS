# Phase 9 — Flutter foundation

Status: **PASS.**

Created the Android Flutter application in `mobile/` with a blue and white theme guided by the supplied IOB Gold Nest screenshots. The app uses the exact `embsys_logo.png` supplied from the reference project's branding assets on startup, login, and home. It bundles Roboto under the included Open Font License so the typography is consistent even when the Android device's system font changes. No IOB logo or bank-specific workflow was copied.

The foundation includes saved server host/port settings, a Test Connection action, an HTTPS client with exact SHA-256 certificate pinning, login against the existing FastAPI contract, automatic installation UUID and device registration, encrypted local token storage, refresh-token rotation, session restoration, logout, and navigation among login, settings, and signed-in home. Android has Internet permission; backup is disabled for stored credentials. Explicit HTTP mode is available only in debug builds.

## Validation

- `flutter analyze` — no issues.
- `flutter test` — **4 passed**, with the two opt-in live backend tests skipped in the default run.
- Live pinned-client test against an isolated LAN backend — health, readiness, login, device registration, refresh rotation, replay rejection, and logout passed.
- Wrong-pin live test — rejected the TLS connection as expected.
- PC LAN HTTPS check — `/api/v1/health` returned `ok`, and `/api/v1/ready` returned `ready` with the model worker running.
- Wireless Android device could reach the PC on `192.168.29.121:8443` over the LAN.
- Built and installed the debug APK on the connected RMX3853. On the phone, Test Connection reported **"Connected securely. Server and worker are ready."** The saved server address survived an app restart.
- On the phone, signed in against an isolated test backend, confirmed the returned device ID, restarted the app and restored the session through refresh, then signed out successfully. The phone's server setting was returned to port `8443` afterward.
- The final installed APK, including the bundled Roboto font, was visually checked on the phone. It is at `mobile/build/app/outputs/flutter-apk/app-debug.apk` and is pinned to the test certificate generated for the current PC LAN address.
- The Android project disables Kotlin incremental compilation because its source on `D:` and the Pub package cache on `C:` triggered a cross-drive path error during the first build. The subsequent builds passed.

## Scope

Camera capture, analysis submission, result display, and history are Phase 10. This phase establishes the secure client and navigation those screens will use.
