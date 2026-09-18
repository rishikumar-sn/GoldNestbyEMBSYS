# Troubleshooting

`/ready` reports `not_ready`: start `python -m app.workers.run`, then check model paths and worker logs under `backend/runtime/logs`.

The phone rejects TLS: regenerate the certificate with the exact PC LAN IP in its SAN, rebuild the app with the printed fingerprint, and use that same IP in server settings.

The phone cannot connect: put both devices on the same LAN and allow TCP 8443 for private networks in Windows Defender Firewall.

Analysis stays queued: confirm the worker is running against the same `backend/.env` and SQLite database as the API.

Wireless ADB disconnects during installation: reconnect the device and install the smaller ABI-specific APK, for example `adb install -r mobile/build/app/outputs/flutter-apk/app-arm64-v8a-debug.apk`.
