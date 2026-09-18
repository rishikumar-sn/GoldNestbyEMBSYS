# Phase 2 — security and device authentication

Status: PASS (17 September 2026)

Implemented Argon2 user passwords and CLI user creation, access JWTs, opaque refresh tokens stored only as SHA-256 hashes, atomic refresh rotation, logout, UUID installation registration on login, device lookup and revocation, and route guards. A 3072-bit RSA self-signed LAN certificate generator includes supplied IP/DNS SANs and prints the SHA-256 certificate fingerprint. The server requires a private `JWT_SECRET` before login. Certificate and key outputs are ignored by Git.

Validation: `pytest -q tests/test_auth.py` passed (3 tests) covering bad credentials, login, device registration, token storage, refresh rotation and old-token rejection, logout, unauthorized access, revocation, and certificate generation. Uvicorn was started with TLS on `https://127.0.0.1:18443`; `curl.exe -k` received `{"status":"ok"}`. `-k` was used only by this local startup smoke test; the mobile client must pin the certificate.

Known limitations: a revoked access JWT remains valid until its 15-minute expiry unless the device is revoked; device revocation is checked on every guarded request. No real LAN certificate has been generated for the phone's current PC IP yet.
