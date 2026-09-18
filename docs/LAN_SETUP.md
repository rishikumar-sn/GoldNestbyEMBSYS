# GoldNest LAN setup

The PC and Android phone must share a network. The backend listens on HTTPS port `8443`; the Flutter app stores the PC's IP address and port in device secure storage. The server certificate fingerprint is embedded in the Flutter build. Keep `server.key` on the backend PC.

## 1. Create the certificate

From `backend/`, generate a certificate for the PC's current LAN address. Add every hostname or IP address the phone will use:

```powershell
..\.venv\Scripts\python.exe scripts\generate_lan_certificate.py --host 192.168.29.121 --host localhost --host 127.0.0.1
```

The command prints the SHA-256 fingerprint. It will refuse to overwrite an existing certificate because that would invalidate the app's trust pin. If the PC address changes, generate a new certificate for the new address and rebuild the app with its new fingerprint. Never copy `server.key` to the phone or commit it.

For an existing certificate, run `..\.venv\Scripts\python.exe scripts\print_lan_fingerprint.py` from `backend/` to retrieve its pin again.

## 2. Start the backend

Set a unique secret outside source control, apply migrations, then start the API from `backend/`:

```powershell
$env:JWT_SECRET = '<a unique random secret>'
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

Run the model worker in another terminal when analysis jobs are needed:

```powershell
..\.venv\Scripts\python.exe -m app.workers.run
```

Create a user with `..\.venv\Scripts\python.exe -m app.cli create-user <username>`; it prompts for a password. Allow inbound TCP port `8443` in the PC firewall for the trusted local network.

## 3. Run the Android app

Use the fingerprint printed by the certificate generator:

```powershell
cd ..\mobile
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' run --dart-define=GOLDNEST_CERT_SHA256=<64-character-fingerprint>
```

To create a debug APK for installation, use `flutter build apk --debug` with the same `--dart-define`; the output is `mobile/build/app/outputs/flutter-apk/app-debug.apk`.

On the phone, open **Set server address**, enter the PC's IP address and port `8443`, and tap **Test connection**. A successful test confirms the certificate pin and `/api/v1/health` response. A worker status of `not_ready` means the API is reachable but the model worker is not running. Save the server, then sign in; login registers this app installation as a device. Changing the server address clears the saved session.

For explicit development-only HTTP testing, pass `--dart-define=ALLOW_INSECURE_HTTP=true` to a debug build. Release builds reject this mode. Normal builds require HTTPS and a valid certificate fingerprint.
