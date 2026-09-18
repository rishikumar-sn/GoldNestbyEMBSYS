# Mobile setup

Install Flutter 3.47 or later and Android SDK platform tools. Build with the SHA-256 fingerprint printed by `backend/scripts/generate_lan_certificate.py`:

```powershell
cd mobile
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' pub get
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' analyze
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' test
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' build apk --debug --dart-define=GOLDNEST_CERT_SHA256=<fingerprint>
```

For an ARM64 phone, use `build apk --debug --split-per-abi` and install `build/app/outputs/flutter-apk/app-arm64-v8a-debug.apk`. The installed app asks for the backend host and port, verifies the exact certificate fingerprint, and stores session tokens in Android Keystore-backed storage.

For release distribution, create a private Android signing key outside the repository:

```powershell
keytool -genkeypair -v -keystore $env:USERPROFILE\goldnest-release.jks -alias goldnest -keyalg RSA -keysize 4096 -validity 10000
```

Create `mobile/android/key.properties` with the following values. It is ignored by Git:

```properties
storeFile=C:\\Users\\<you>\\goldnest-release.jks
storePassword=<store-password>
keyAlias=goldnest
keyPassword=<key-password>
```

Then create a release APK using the certificate fingerprint:

```powershell
& 'D:\PROJECTS_BY_RISHI\flutter-sdk\bin\flutter.bat' build apk --release --dart-define=GOLDNEST_CERT_SHA256=<fingerprint>
```

The project does not fall back to the debug signing key for release builds. Release builds must use HTTPS and a valid pin.
