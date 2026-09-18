# GoldNest

GoldNest is a local-network Android application and FastAPI backend for jewellery instance counting and type classification. The backend uses SQLite, local artifact storage, LAN TLS with certificate pinning, YOLOE segmentation, InSPyReNet fallback, and the supplied SigLIP2 model files.

## Quick start

1. Follow [backend setup](docs/BACKEND_SETUP.md) and [model setup](docs/MODEL_SETUP.md).
2. Generate a LAN certificate and build the app with its fingerprint using [LAN setup](docs/LAN_SETUP.md).
3. Follow [mobile setup](docs/MOBILE_SETUP.md) to build and install the Android APK.

The API contract is in [API.md](docs/API.md), and operational limits are in [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
