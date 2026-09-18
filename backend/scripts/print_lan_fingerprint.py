from __future__ import annotations

import argparse
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the SHA-256 pin for an existing LAN certificate")
    parser.add_argument("--cert", type=Path, default=Path(__file__).resolve().parents[1] / "certs/server.crt")
    args = parser.parse_args()
    certificate = x509.load_pem_x509_certificate(args.cert.read_bytes())
    print(certificate.fingerprint(hashes.SHA256()).hex())


if __name__ == "__main__":
    main()
