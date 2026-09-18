# Security

- Passwords use Argon2 hashes. JWT access tokens expire, and refresh tokens are opaque values stored only as SHA-256 hashes.
- Refresh tokens rotate on use. Logout revokes the current refresh token. Every installation has a generated UUID device record; IMEI and hardware serials are not used.
- The backend uses a self-signed LAN TLS certificate. The app accepts it only when its SHA-256 DER fingerprint exactly matches `GOLDNEST_CERT_SHA256` supplied at build time.
- Keep `backend/certs/server.key`, `backend/.env`, databases, and runtime artifacts outside source control. Rotate the certificate fingerprint and rebuild the app whenever the certificate changes.
- HTTP is restricted to explicit debug builds using `ALLOW_INSECURE_HTTP=true`; release builds reject it.
